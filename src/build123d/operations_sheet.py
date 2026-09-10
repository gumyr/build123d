"""
Sheet Metal Operations

name: operations_sheet.py
by:   Gumyr & Gabriel Jesus
date: July 21st 2026

desc:
    Surface-native sheet metal operations.

license:

    Copyright 2026 Gumyr & Gabriel Jesus

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, atan, atan2, cos, degrees, pi, radians, sin, sqrt, tan
from typing import Literal, overload

import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_GTransform,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeWire,
)
from OCP.BRepLib import BRepLib
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.BRepTopAdaptor import BRepTopAdaptor_FClass2d
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.Geom2d import (
    Geom2d_Circle,
    Geom2d_Curve,
    Geom2d_Ellipse,
    Geom2d_Line,
    Geom2d_TrimmedCurve,
)
from OCP.Geom2dAdaptor import Geom2dAdaptor_Curve
from OCP.Geom2dInt import Geom2dInt_GInter
from OCP.Geom import Geom_CylindricalSurface, Geom_Plane, Geom_Surface
from OCP.GeomProjLib import GeomProjLib
from OCP.ShapeFix import ShapeFix_Face
from OCP.gp import gp_Ax3, gp_Ax22d, gp_Dir2d, gp_Pln, gp_Pnt, gp_Pnt2d
import OCP.TopAbs as ta
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Vertex,
    TopoDS_Wire,
)

from build123d.build_common import flatten_sequence, validate_inputs
from build123d.build_enums import (
    Align,
    BendPosition,
    ReliefType,
    GeomType,
    HemType,
    Keep,
    Mode,
)
from build123d.build_sheet import BuildSheet
from build123d.geometry import Matrix, TOLERANCE, Axis, Location, Plane, Vector
from build123d.sheet_utils import (
    MIN_BEND_RADIUS,
    SheetMetalParameters,
    is_positive_bend,
    _topods_entities,
    _uv_topods_face_with_map,
    bend_allowance,
    neutral_radius,
    reference_radius,
)
from build123d.topology import (
    Edge,
    Face,
    Shape,
    Shell,
    Sketch,
    Solid,
    Vertex,
    Wire,
    topo_explore_connected_faces,
)


def _orient_face(face: Face, desired_normal: Vector) -> Face:
    """Orient a face so its normal agrees with the sheet inside direction."""
    return (
        -face
        if face.normal_at(face.center()).dot(desired_normal.normalized()) < 0
        else face
    )


def _support_face(edge: Edge, target: Shell) -> Face:
    """Return the single sheet face adjacent to a free boundary edge."""
    if edge.geom_type != GeomType.LINE:
        raise ValueError("flange/hem edges must be linear")
    adjacent = [Face(face) for face in topo_explore_connected_faces(edge, target)]
    if len(adjacent) != 1:
        raise ValueError(
            "Selected edge must be a free sheet boundary with exactly one "
            f"adjacent face, found {len(adjacent)}"
        )
    return adjacent[0]


def _outward_direction(edge: Edge, support: Face) -> tuple[Vector, Vector]:
    """Return the outward in-plane direction and oriented support normal."""
    p0, p1 = edge.position_at(0), edge.position_at(1)
    tangent = (p1 - p0).normalized()
    normal = support.normal_at(edge.position_at(0.5)).normalized()
    outward = tangent.cross(normal).normalized()
    probe_distance = max(edge.length * 1e-5, 1e-5)
    if support.is_inside(edge.position_at(0.5) + outward * probe_distance):
        outward = -outward
    return outward, normal


def _target_shell(context: BuildSheet | None, edges: list[Edge]) -> Shell:
    """Resolve a Face, Sketch, or Shell target for Builder or Algebra mode."""
    if context is not None:
        return context.sheet_local
    parent: Shape | None = edges[0].topo_parent
    if isinstance(parent, Shell):
        return parent
    if isinstance(parent, Face):
        return Shell(parent)
    if isinstance(parent, Sketch):
        return BuildSheet._validated_shell(list(parent.faces()))
    raise ValueError("edges must belong to a sheet Face, Sketch, or Shell")


def _resolve_sheet_parameters(
    context: BuildSheet | None,
    supplied: SheetMetalParameters | None,
) -> SheetMetalParameters:
    """Resolve sheet parameters from Builder or Algebra mode."""
    if context is not None:
        if supplied is not None:
            raise ValueError(
                "sheet_parameters is supplied by the active BuildSheet context"
            )
        return context.sheet_parameters
    if supplied is None:
        raise ValueError("sheet_parameters is required in Algebra mode")
    if not isinstance(supplied, SheetMetalParameters):
        raise TypeError("sheet_parameters must be a SheetMetalParameters")
    return supplied


def _make_bend_faces(
    target: Shell,
    edge: Edge,
    inside_radius: float,
    angle: float,
    leg_length: float,
    sheet_parameters: SheetMetalParameters,
    gap_start: float = 0,
    gap_end: float = 0,
) -> list[Face]:
    """Create the cylindrical bend and optional planar leg faces."""
    support = _support_face(edge, target)
    outward, normal = _outward_direction(edge, support)

    p0, p1 = edge.position_at(0), edge.position_at(1)
    tangent = (p1 - p0).normalized()
    if gap_start + gap_end >= edge.length:
        raise ValueError("gaps leave no bend width on the edge")
    p0 += tangent * gap_start
    p1 -= tangent * gap_end
    bend_edge = Edge.make_line(p0, p1)

    radius = reference_radius(
        inside_radius,
        sheet_parameters,
        angle,
    )
    bend_axis = Axis(
        p0 + normal * radius * (1 if angle > 0 else -1), outward.cross(normal)
    )
    direction_axis = Axis((0, 0, 0), bend_axis.direction)

    bend_face = Face.revolve(bend_edge, angle, bend_axis)
    bend_normal = normal.rotate(direction_axis, angle / 2)
    bend_face = _orient_face(bend_face, bend_normal)
    result = [bend_face]

    if leg_length > 0:
        end_edge = bend_edge.rotate(bend_axis, angle)
        leg_direction = outward.rotate(direction_axis, angle)
        leg_normal = normal.rotate(direction_axis, angle)
        leg_face = _orient_face(
            Face.extrude(end_edge, leg_direction * leg_length), leg_normal
        )
        result.append(leg_face)

    return result


def _apply_faces(
    context: BuildSheet | None,
    target: Shell,
    additions: list[Face],
    mode: Mode,
) -> Shell:
    """Sew surface additions into a BuildSheet or Algebra-mode shell."""
    if mode != Mode.ADD:
        raise ValueError("sheet metal operations currently require Mode.ADD")
    if context is not None:
        context._add_to_context(*additions, mode=mode)
        return context.sheet_local
    return BuildSheet._validated_shell(list(target.faces()) + additions)


def flange(
    edges: Edge | list[Edge] | None = None,
    length: float = 0,
    angle: float = 90,
    radius: float | None = None,
    gaps: float | tuple[float, float] = 0,
    sheet_parameters: SheetMetalParameters | None = None,
    mode: Mode = Mode.ADD,
) -> Shell:
    """Create cylindrical bends and planar flanges from free sheet edges.

    Positive angles fold toward the adjacent face normal; negative angles fold
    toward its opposite side. ``radius`` is the physical inside bend radius.

    Args:
        edges: Linear free boundary edge or edges.
        length: Planar flange length measured from the bend tangent.
        angle: Signed bend angle in degrees. Defaults to 90.
        radius: Physical inside bend radius. Defaults to the bend radius in
            ``sheet_parameters``.
        gaps: Trim at the bend ends. A scalar applies to both ends; a tuple
            specifies ``(edge start, edge end)``. Defaults to 0.
        sheet_parameters: Material and reference-surface parameters. Required
            in Algebra mode and supplied by ``BuildSheet`` in Builder mode.
        mode: Builder combination mode. Only Mode.ADD is currently supported.

    Returns:
        The updated reference Shell.
    """
    context: BuildSheet | None = BuildSheet._get_context("flange")
    edge_list = list(flatten_sequence(edges))
    validate_inputs(context, "flange", edge_list)

    if not edge_list:
        raise ValueError("flange requires at least one edge")
    if length <= 0:
        raise ValueError("length must be positive")
    if angle == 0 or abs(angle) > 270:
        raise ValueError("angle must be in [-270, 270] degrees and non-zero")
    if isinstance(gaps, (int, float)):
        gap_start = gap_end = float(gaps)
    elif (
        isinstance(gaps, tuple)
        and len(gaps) == 2
        and all(isinstance(gap, (int, float)) for gap in gaps)
    ):
        gap_start, gap_end = map(float, gaps)
    else:
        raise ValueError("gaps must be a number or a pair of numbers")
    if gap_start < 0 or gap_end < 0:
        raise ValueError("gaps can't be negative")
    parameters = _resolve_sheet_parameters(context, sheet_parameters)
    if radius is None:
        radius = parameters.resolved_bend_radius
    if radius < 0:
        raise ValueError("radius can't be negative")

    target = _target_shell(context, edge_list)
    additions = [
        face
        for edge in edge_list
        for face in _make_bend_faces(
            target,
            edge,
            radius,
            angle,
            length,
            parameters,
            gap_start,
            gap_end,
        )
    ]
    return _apply_faces(context, target, additions, mode)


def _owning_shell(context: BuildSheet | None, shapes: list, what: str) -> Shell:
    """Resolve the shell some shapes belong to, in Builder or Algebra mode."""
    if context is not None:
        return context.sheet_local
    parents = [shape.topo_parent for shape in shapes]
    sheet_parents = [parent for parent in parents if isinstance(parent, Shell)]
    if not sheet_parents or len(sheet_parents) != len(parents):
        raise ValueError(f"{what} must belong to a sheet Shell")
    target = sheet_parents[0]
    if any(not target.is_same(parent) for parent in sheet_parents[1:]):
        raise ValueError(f"{what} must belong to the same sheet Shell")
    return target


def bend(
    bend_line: Edge | None = None,
    angle: float = 90,
    radius: float | None = None,
    position: BendPosition = BendPosition.BEND_OUTSIDE,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell:
    """Fold existing sheet material along a line.

    Where ``flange`` adds a wall beyond a free edge, ``bend`` folds material
    that is already there. ``bend_line`` is a straight edge on the boundary of
    a planar face, shared with the coplanar face beyond it. That face stays put
    along with everything attached to it, and everything on the far side of the
    line swings through ``angle``.

    An edge lies between two faces, so which of them stays put is the one thing
    the line alone cannot say. The way it was selected answers it: an edge
    picked off a face records that face on its ``topo_path``, so
    ``sheet.faces().sort_by(Axis.X)[-1].edges().sort_by(Axis.Y)[0]`` names both
    the fold line and the side that holds still. An edge taken straight off the
    sheet is refused rather than guessed at, since both of its faces are
    equally its own.

    The bend takes a strip of the sheet with it as it rolls up, and
    ``position`` says where that strip sits: ``BEND_OUTSIDE`` puts all of it
    past the line, leaving the fixed face untouched, while ``CENTER`` straddles
    the line and the two mould line positions place the corner of the formed
    part on it. Whatever the blank's outline does across that strip - a taper,
    a corner round, a notch, a hole - rolls into the bend with it, so the strip
    need not be the same width at both ends and ``unfold`` gives the blank back.

    Sizes are measured on the reference surface, as everywhere else in
    ``BuildSheet``, so the sheet is the reference surface of the part you get
    rather than the blank it is cut from - ``unfold`` reports that.

    Args:
        bend_line: Straight edge of the face that stays where it is, shared
            with a coplanar face, and selected through that face.
        angle: Signed bend angle in degrees. Positive folds toward the face
            normal. Defaults to 90.
        radius: Physical inside bend radius. Defaults to the bend radius in
            ``sheet_parameters``.
        position: Where the bend sits relative to the line. Defaults to
            ``BEND_OUTSIDE``.
        sheet_parameters: Material and reference-surface parameters. Required
            in Algebra mode and supplied by ``BuildSheet`` in Builder mode.

    Returns:
        The updated reference Shell.
    """
    context: BuildSheet | None = BuildSheet._get_context("bend")
    validate_inputs(context, "bend", [bend_line] if bend_line is not None else [])

    if bend_line is None:
        raise ValueError("bend requires a bend_line")
    if not isinstance(bend_line, Edge) or bend_line.geom_type != GeomType.LINE:
        raise ValueError("bend_line must be a straight Edge")
    fixed_face = _selected_face(bend_line)
    if fixed_face.geom_type != GeomType.PLANE:
        raise ValueError("bend_line must be selected through a planar face")
    if angle == 0 or abs(angle) > 270:
        raise ValueError("angle must be in [-270, 270] degrees and non-zero")

    parameters = _resolve_sheet_parameters(context, sheet_parameters)
    if radius is None:
        radius = parameters.resolved_bend_radius
    if radius < 0:
        raise ValueError("radius can't be negative")

    target = _owning_shell(context, [fixed_face], "the face bend_line came from")
    face = next((f for f in target.faces() if f.is_same(fixed_face)), None)
    if face is None:
        raise ValueError(
            "the face bend_line was selected from is not part of the sheet "
            "being bent"
        )

    result = _fold(target, face, bend_line, angle, radius, position, parameters)

    if context is not None:
        context._add_to_context(*result.faces(), mode=Mode.REPLACE)
        return context.sheet_local
    return result


def _miter_target(context: BuildSheet | None, vertices: list[Vertex]) -> Shell:
    """Resolve the shell containing vertices in Builder or Algebra mode."""
    return _owning_shell(context, vertices, "miter vertices")


def _contains_vertex(edge: Edge, vertex: Vertex) -> bool:
    """Return whether edge contains vertex as a topological endpoint."""
    return any(vertex.is_same(candidate) for candidate in edge.vertices())


def _other_vertex(edge: Edge, vertex: Vertex) -> Vertex:
    """Return the endpoint of edge opposite vertex."""
    return next(
        candidate for candidate in edge.vertices() if not vertex.is_same(candidate)
    )


def _miter_support(vertex: Vertex, target: Shell) -> tuple[Face, Edge, Edge, Edge]:
    """Find the flange face, rim, bend junction, and side for a rim vertex."""
    candidates: list[tuple[Face, Edge, Edge, Edge]] = []
    for face in target.faces().filter_by(GeomType.PLANE):
        if not any(vertex.is_same(candidate) for candidate in face.vertices()):
            continue

        bend_edges = []
        for edge in face.edges().filter_by(GeomType.LINE):
            adjacent = [
                Face(candidate)
                for candidate in topo_explore_connected_faces(edge, target)
            ]
            if len(adjacent) == 2 and any(
                candidate.geom_type == GeomType.CYLINDER and not candidate.is_same(face)
                for candidate in adjacent
            ):
                bend_edges.append(edge)

        for bend_edge in bend_edges:
            bend_direction = (
                bend_edge.position_at(1) - bend_edge.position_at(0)
            ).normalized()
            for rim_edge in face.edges().filter_by(GeomType.LINE):
                if not _contains_vertex(rim_edge, vertex):
                    continue
                if len(topo_explore_connected_faces(rim_edge, target)) != 1:
                    continue
                rim_direction = (
                    rim_edge.position_at(1) - rim_edge.position_at(0)
                ).normalized()
                if abs(abs(bend_direction.dot(rim_direction)) - 1) > 1e-6:
                    continue

                for side_edge in face.edges().filter_by(GeomType.LINE):
                    if side_edge.is_same(rim_edge) or not _contains_vertex(
                        side_edge, vertex
                    ):
                        continue
                    other = _other_vertex(side_edge, vertex)
                    if any(
                        other.is_same(bend_vertex)
                        for bend_vertex in bend_edge.vertices()
                    ):
                        candidates.append((face, rim_edge, bend_edge, side_edge))

    if len(candidates) != 1:
        raise ValueError(
            "Each miter vertex must identify exactly one free flange rim endpoint"
        )
    return candidates[0]


def miter(
    vertices: Vertex | list[Vertex] | None = None,
    angle: float = 0,
    through_bend: bool = False,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell:
    """Angle the sides of planar flanges.

    Each selected vertex must be an endpoint of a free flange rim. A positive
    angle trims the rim toward its other endpoint; a negative angle extends it.
    The angle is measured from the side perpendicular to the rim.

    By default the cut stops at the bend, leaving it square-ended.
    ``through_bend`` carries it on to the fold line instead, which is what a
    mitered corner is in the flat pattern: one straight cut from the rim to the
    edge of the blank. A trimming miter narrows the bend to match the flange
    and an extending one widens it. The angle is held in the flat pattern
    rather than on the reference surface, since that is where a miter is laid
    out - so the cut is slightly skewed on the formed bend by however far the
    neutral axis sits from the reference surface.

    Args:
        vertices: Free flange-rim endpoint or endpoints.
        angle: Signed miter angle in degrees. Must be strictly between -90 and
            90 degrees.
        through_bend: Carry the cut through the bend to the fold line. Defaults
            to False.
        sheet_parameters: Material and reference-surface parameters. Needed for
            ``through_bend`` in Algebra mode; supplied by ``BuildSheet`` in
            Builder mode.

    Returns:
        The updated reference Shell.
    """
    context: BuildSheet | None = BuildSheet._get_context("miter")
    vertex_list = list(flatten_sequence(vertices))
    validate_inputs(context, "miter", vertex_list)

    if not vertex_list:
        raise ValueError("miter requires at least one vertex")
    if not all(isinstance(vertex, Vertex) for vertex in vertex_list):
        raise ValueError("miter takes only Vertices")
    if not isinstance(angle, (int, float)) or not -90 < angle < 90:
        raise ValueError("angle must be strictly between -90 and 90 degrees")
    parameters = (
        _resolve_sheet_parameters(context, sheet_parameters) if through_bend else None
    )

    target = _miter_target(context, vertex_list)
    selections = [(_miter_support(vertex, target), vertex) for vertex in vertex_list]
    face_selections: dict[Face, list[tuple[Edge, Edge, Edge, Vertex]]] = {}
    for (face, rim, fold, side), vertex in selections:
        face_selections.setdefault(face, []).append((rim, fold, side, vertex))

    slope = tan(radians(angle))
    replacements: dict[Face, dict[Vertex, Vector]] = {}
    bend_cuts: list = []
    for face, face_items in face_selections.items():
        replacements[face] = {}
        cuts: list[_MiterCut] = []
        for rim, fold, side, vertex in face_items:
            other_rim_vertex = _other_vertex(rim, vertex)
            bend_vertex = _other_vertex(side, vertex)
            inward = (Vector(other_rim_vertex) - Vector(vertex)).normalized()
            rim_projection = Vector(vertex) + inward * (
                (Vector(bend_vertex) - Vector(vertex)).dot(inward)
            )
            flange_length = (Vector(bend_vertex) - rim_projection).length
            anchor = Vector(bend_vertex)
            reach = 0.0
            if parameters is not None:
                cylinder, allowance = _bend_beyond(target, fold, parameters)
                reach = allowance * slope
                anchor = anchor + inward * reach
                replacements[face][bend_vertex] = anchor
                bend_cuts.append(
                    _bend_miter_cut(
                        target,
                        cylinder,
                        Vector(bend_vertex),
                        inward,
                        reach,
                        allowance,
                        parameters,
                    )
                )
            moved = rim_projection + inward * (flange_length * slope + reach)
            replacements[face][vertex] = moved
            cuts.append(_MiterCut(rim, vertex, other_rim_vertex, anchor, moved, inward))
        _meet_crossing_miters(face, cuts, replacements[face])

    remodelled_bends = _remodel_mitered_bends(bend_cuts)

    new_faces: list[Face] = []
    for face in target.faces():
        swapped = next(
            (trim for bend, trim in remodelled_bends if bend.is_same(face)), None
        )
        if swapped is not None:
            new_faces.append(swapped)
            continue
        if face not in replacements:
            new_faces.append(face)
            continue
        points = []
        for edge in face.outer_wire().order_edges():
            point = edge.position_at(0)
            replacement = next(
                (
                    new_point
                    for vertex, new_point in replacements[face].items()
                    if (Vector(vertex) - point).length < 1e-7
                ),
                point,
            )
            points.append(replacement)
        # two miters that meet inside the flange land on the same point, and
        # the rim between them is gone
        points = [
            point
            for index, point in enumerate(points)
            if (point - points[index - 1]).length > TOLERANCE
        ]
        new_face = Face(Wire.make_polygon(points), face.inner_wires())
        new_faces.append(_orient_face(new_face, face.normal_at(face.center())))

    result = BuildSheet._validated_shell(new_faces)
    if context is not None:
        context._add_to_context(*new_faces, mode=Mode.REPLACE)
        return context.sheet_local
    return result


def _bend_beyond(
    shell: Shell, fold: Edge, parameters: SheetMetalParameters
) -> tuple[Face, float]:
    """The bend a flange folds about, and how wide it develops.

    That width is the bend allowance: the arc the reference surface carries,
    scaled to the neutral axis, which is where a flat pattern is measured and
    so where a miter's angle has to hold.
    """
    bends = [
        Face(face)
        for face in topo_explore_connected_faces(fold, shell)
        if face is not None and Face(face).geom_type == GeomType.CYLINDER
    ]
    if len(bends) != 1:
        raise ValueError(
            "miter through_bend needs the flange to meet a single bend along "
            f"its base, and {len(bends)} were found"
        )
    cylinder = bends[0]
    if cylinder.radius is None or cylinder.width is None:
        raise ValueError("miter through_bend expects a cylindrical bend")
    neutral = neutral_radius(
        cylinder.radius, parameters, is_positive_bend(cylinder.wrapped)
    )
    return cylinder, cylinder.width * neutral / cylinder.radius


def _bend_miter_cut(
    shell: Shell,
    cylinder: Face,
    corner: Vector,
    inward: Vector,
    reach: float,
    allowance: float,
    parameters: SheetMetalParameters,
) -> tuple[Face, _FlatFrame, float, float]:
    """Where a miter's cut continues across the bend, in the bend's flat frame.

    A straight line in the flat pattern is not a plane section of the formed
    bend, so the cut is laid out in the bend's own developed frame: it runs
    from the fold-line corner to the far tangent ``reach`` further along it,
    with ``reach`` negative for a miter that extends the flange.
    """
    tangents = [edge for edge in cylinder.edges() if edge.geom_type == GeomType.LINE]
    fold = max(tangents, key=lambda edge: edge.distance_to(corner))
    ends = [Vector(fold.position_at(end)) for end in (0.0, 1.0)]
    frames, _, _ = _bend_end_frames(
        shell, min(ends, key=lambda point: (point - corner).length), -inward, parameters
    )
    # the frame is in developed units, so the far tangent sits one bend
    # allowance across it
    return cylinder, frames[1], reach, allowance


def _remodel_mitered_bends(cuts: list) -> list[tuple[Face, Face]]:
    """Apply every miter that reaches a bend, one after another."""
    remodelled: list[list] = []
    for cylinder, frame, reach, allowance in cuts:
        entry = next((item for item in remodelled if item[0].is_same(cylinder)), None)
        if entry is None:
            entry = [cylinder, cylinder]
            remodelled.append(entry)
        entry[1] = _remodel_bend(entry[1], frame, reach, allowance)
    return [(pair[0], pair[1]) for pair in remodelled]


def _remodel_bend(
    cylinder: Face, frame: _FlatFrame, reach: float, allowance: float
) -> Face:
    """A bend with one end re-cut along a miter, in its development.

    The cut runs from the fold-line corner to the far tangent ``reach`` further
    along it, so the material between it and the bend's old end is a triangle
    in the development: taken off the bend when the miter trims the flange, and
    added to it when the miter extends the flange, so the bend widens to meet
    the wider wall. The development is a planar face in the surface's
    parameters, the triangle is drawn there through the bend's frame, the
    boolean is planar, and the result goes back onto the cylinder the way a
    fold's strip does.
    """
    if abs(reach) < _RELIEF_TOLERANCE:
        return cylinder
    developed = Face(_uv_topods_face_with_map(cylinder.wrapped)[0])
    corners = [
        frame.to_uv(0.0, 0.0),
        frame.to_uv(0.0, allowance),
        frame.to_uv(-reach, allowance),
    ]
    # the same way up as the development, or the fuse leaves them as two faces
    triangle = _orient_face(
        Face(Wire.make_polygon([Vector(c.X(), c.Y(), 0.0) for c in corners])),
        developed.normal_at(developed.center()),
    )
    reshaped = developed.cut(triangle) if reach > 0 else developed.fuse(triangle)
    pieces = [reshaped] if isinstance(reshaped, Face) else list(reshaped.faces())
    if len(pieces) != 1:
        raise ValueError("the miter cuts the bend into pieces")
    surface = BRep_Tool.Surface_s(cylinder.wrapped)
    return _orient_face(
        _face_onto_surface(pieces[0].wrapped, surface),
        cylinder.normal_at(cylinder.center()),
    )


@dataclass(frozen=True)
class _MiterCut:
    """One miter: where its cut line runs and how far along the rim it eats."""

    rim: Edge
    vertex: Vertex
    far_vertex: Vertex  # the other end of the rim
    anchor: Vector  # the bend end of the cut, which does not move
    moved: Vector  # where the rim end of the cut goes
    inward: Vector  # along the rim, away from this end

    @property
    def direction(self) -> Vector:
        """Which way the cut runs, from the bend toward the rim."""
        return (self.moved - self.anchor).normalized()

    @property
    def travel(self) -> float:
        """How much of the rim this miter takes."""
        return (self.moved - Vector(self.vertex)).dot(self.inward)


def _meet_crossing_miters(
    face: Face, cuts: list[_MiterCut], replacements: dict
) -> None:
    """Send a miter that eats past the rim to where its cut really ends.

    Miters cut back from the ends of a rim and leave the bend edge alone, so
    taking more than the rim is long does not run out of flange - it runs out
    of rim. Two such cuts meet each other inside the flange; a lone one leaves
    through the far side. Either way what is left is a triangle, which is a
    perfectly good flange.
    """
    paired: set[int] = set()
    for index, first in enumerate(cuts):
        if index in paired:
            continue  # already met by the miter at the other end of its rim
        found = next(
            (
                other
                for other in range(index + 1, len(cuts))
                if cuts[other].rim.is_same(first.rim)
            ),
            None,
        )
        if found is not None:
            partner = cuts[found]
            paired.add(found)
            if first.travel + partner.travel <= first.rim.length + TOLERANCE:
                continue
            meeting = _lines_meet(
                face, first.anchor, first.direction, partner.anchor, partner.direction
            )
            replacements[first.vertex] = meeting
            replacements[partner.vertex] = meeting
        elif first.travel > first.rim.length + TOLERANCE:  # a lone miter
            # the cut passes the far end of the rim and leaves through the
            # side beyond it, taking the whole rim with it
            far_side = next(
                edge
                for edge in face.edges()
                if not edge.is_same(first.rim)
                and _contains_vertex(edge, first.far_vertex)
            )
            start = Vector(far_side.position_at(0))
            meeting = _lines_meet(
                face,
                first.anchor,
                first.direction,
                start,
                (Vector(far_side.position_at(1)) - start).normalized(),
            )
            replacements[first.vertex] = meeting
            replacements[first.far_vertex] = meeting


def _lines_meet(
    face: Face, origin: Vector, heading: Vector, other: Vector, other_heading: Vector
) -> Vector:
    """Where two lines in a face's plane cross."""
    normal = face.normal_at(face.center())
    denominator = heading.cross(other_heading).dot(normal)
    if abs(denominator) < TOLERANCE:  # pragma: no cover - miters always cross
        raise ValueError("the miter cuts on this flange run parallel")
    along = (other - origin).cross(other_heading).dot(normal)
    return origin + heading * (along / denominator)


def _bisection(func, lower: float, upper: float, eps: float = 1.0e-9) -> float:
    """Return a root of ``func`` in the inclusive interval."""
    f_lower, f_upper = func(lower), func(upper)
    if f_lower * f_upper > 0:
        raise ValueError("Teardrop hem has unexpected incorrect geometry")
    mid = 0.5 * (lower + upper)
    previous = mid + 2 * eps
    while abs(mid - previous) >= eps:
        previous = mid
        f_mid = func(mid)
        if f_lower * f_mid < 0:
            upper = mid
        else:
            lower, f_lower = mid, f_mid
        mid = 0.5 * (lower + upper)
    return mid


def _hem_parameters(
    hem_type: HemType,
    thickness: float,
    width: float | None,
    opening: float,
    radius: float | None,
    roll_angle: float | None,
) -> tuple[float, float, float]:
    """Return ``(leg_length, bend_angle, physical_inside_radius)``."""
    # a flat dispatch over HemType - one return per hem type reads better than
    # accumulating into a single exit
    # pylint: disable=too-many-return-statements
    if hem_type in (HemType.FLAT, HemType.OPEN):
        if opening < 0:
            raise ValueError("opening must be positive")
        if width is None:
            raise ValueError(f"width is required for {hem_type}")
        bend_radius = max(0.5 * opening, MIN_BEND_RADIUS)
        if width <= bend_radius + thickness:
            raise ValueError(
                "width must be greater than the bend width (bend radius + thickness)"
            )
        return width - (bend_radius + thickness), 180.0, bend_radius

    if hem_type == HemType.ROLLED:
        if radius is None or radius <= 0:
            raise ValueError("a positive radius is required for a rolled hem")
        max_roll_angle = 270.0 + degrees(asin(radius / (radius + thickness)))
        if roll_angle is None:
            return 0.0, max_roll_angle, radius
        if roll_angle <= 0:
            raise ValueError("roll_angle must be strictly positive")
        if roll_angle > max_roll_angle:
            raise ValueError(
                f"roll_angle must not exceed physical maximum ({max_roll_angle}°)"
            )
        return 0.0, roll_angle, radius

    if hem_type == HemType.TEARDROP:
        if radius is None or radius <= 0:
            raise ValueError("a positive radius is required for a teardrop hem")
        if opening < 0:
            raise ValueError("opening must be positive")
        if width is None:
            raise ValueError("width is required for a teardrop hem")
        bend_width = radius + thickness
        if width < 2 * bend_width:
            raise ValueError(
                "width must be greater or equal than twice the bend width "
                "(bend radius + thickness)"
            )
        if width == 2 * bend_width:
            if opening >= radius:
                raise ValueError("opening must be smaller than bend radius")
            return radius - opening, 270.0, radius

        def equation(leg: float) -> float:
            return leg - width + bend_width + thickness * sin(2 * atan(radius / leg))

        leg = _bisection(equation, width - bend_width - thickness, width - bend_width)
        if opening == 0.0:
            theta = atan(radius / leg)
            return leg, 180.0 + 2 * degrees(theta), radius
        if opening == 2 * radius:
            return _hem_parameters(
                HemType.OPEN,
                thickness,
                width - bend_width,
                opening,
                None,
                None,
            )
        theta = atan(
            (leg - sqrt(leg**2 - 2.0 * radius * opening + opening**2)) / opening
        )
        leg_length = opening * (cos(2 * theta) - 1) / sin(2 * theta) + leg
        return leg_length, 180.0 + 2 * degrees(theta), radius

    raise ValueError(f"Unknown hem type {hem_type}")


@overload
def hem(
    edges: Edge | list[Edge] | None = None,
    hem_type: Literal[HemType.FLAT] = HemType.FLAT,
    *,
    width: float,
    sheet_parameters: SheetMetalParameters | None = None,
    mode: Mode = Mode.ADD,
) -> Shell: ...


@overload
def hem(
    edges: Edge | list[Edge] | None,
    hem_type: Literal[HemType.OPEN],
    *,
    width: float,
    opening: float,
    sheet_parameters: SheetMetalParameters | None = None,
    mode: Mode = Mode.ADD,
) -> Shell: ...


@overload
def hem(
    edges: Edge | list[Edge] | None,
    hem_type: Literal[HemType.TEARDROP],
    *,
    width: float,
    radius: float | None = None,
    opening: float = 0,
    sheet_parameters: SheetMetalParameters | None = None,
    mode: Mode = Mode.ADD,
) -> Shell: ...


@overload
def hem(
    edges: Edge | list[Edge] | None,
    hem_type: Literal[HemType.ROLLED],
    *,
    radius: float | None = None,
    roll_angle: float | None = None,
    sheet_parameters: SheetMetalParameters | None = None,
    mode: Mode = Mode.ADD,
) -> Shell: ...


def hem(
    edges: Edge | list[Edge] | None = None,
    hem_type: HemType = HemType.FLAT,
    *,
    width: float | None = None,
    opening: float | None = None,
    radius: float | None = None,
    roll_angle: float | None = None,
    sheet_parameters: SheetMetalParameters | None = None,
    mode: Mode = Mode.ADD,
) -> Shell:
    """Create a flat, open, teardrop, or rolled surface hem.

    The selected ``hem_type`` determines which profile parameters apply:

    * ``FLAT`` requires ``width``.
    * ``OPEN`` requires ``width`` and a positive ``opening``.
    * ``TEARDROP`` requires ``width`` and accepts ``radius`` and ``opening``.
    * ``ROLLED`` accepts ``radius`` and ``roll_angle``.

    An omitted ``radius`` uses the default bend radius in ``sheet_parameters``.
    ``sheet_parameters`` is required in Algebra mode and obtained from the
    active ``BuildSheet`` in Builder mode.
    """
    context: BuildSheet | None = BuildSheet._get_context("hem")
    edge_list = list(flatten_sequence(edges))
    validate_inputs(context, "hem", edge_list)

    if not edge_list:
        raise ValueError("hem requires at least one edge")
    if hem_type == HemType.FLAT:
        if width is None:
            raise ValueError("width is required for HemType.FLAT")
        if opening is not None or radius is not None or roll_angle is not None:
            raise ValueError("HemType.FLAT only accepts width")
        profile_opening = 0.0
    elif hem_type == HemType.OPEN:
        if width is None:
            raise ValueError("width is required for HemType.OPEN")
        if opening is None or opening <= 0:
            raise ValueError("a positive opening is required for HemType.OPEN")
        if radius is not None or roll_angle is not None:
            raise ValueError("HemType.OPEN only accepts width and opening")
        profile_opening = opening
    elif hem_type == HemType.TEARDROP:
        if width is None:
            raise ValueError("width is required for HemType.TEARDROP")
        if roll_angle is not None:
            raise ValueError("HemType.TEARDROP doesn't accept roll_angle")
        profile_opening = 0.0 if opening is None else opening
    elif hem_type == HemType.ROLLED:
        if width is not None or opening is not None:
            raise ValueError("HemType.ROLLED only accepts radius and roll_angle")
        profile_opening = 0.0
    else:
        raise ValueError(f"Unknown hem type {hem_type}")

    parameters = _resolve_sheet_parameters(context, sheet_parameters)
    if radius is None:
        radius = parameters.resolved_bend_radius

    leg_length, bend_angle, bend_radius = _hem_parameters(
        hem_type,
        parameters.thickness,
        width,
        profile_opening,
        radius,
        roll_angle,
    )
    target = _target_shell(context, edge_list)
    additions = [
        face
        for edge in edge_list
        for face in _make_bend_faces(
            target,
            edge,
            bend_radius,
            bend_angle,
            leg_length,
            parameters,
        )
    ]
    return _apply_faces(context, target, additions, mode)


def unfold(
    sheet: Shell | None = None,
    sheet_parameters: SheetMetalParameters | None = None,
    align: Align | tuple[Align, Align] | None = Align.NONE,
) -> Shell:
    """Sheet Operation: unfold

    Develop a sheet metal reference shell into its flat pattern on ``Plane.XY``
    - the blank the folded part is cut from.

    Each bend is developed at its neutral radius, derived from the thickness,
    K-factor and reference surface. :meth:`~topology.Shell.unfold` defaults to
    the geometric radius of each bend when given no parameters, which produces
    a pattern that will not fold back to the requested part; this operation
    requires the parameters instead, taking them from an enclosing
    ``BuildSheet`` when there is one.

    The pattern is always built on ``Plane.XY``; ``align`` places it within
    that plane. The default, ``Align.NONE``, leaves it where the development
    put it, which keeps it registered with the source sheet. ``Align.MIN``
    puts the pattern's lower-left corner on the origin, which is usually what
    a nesting or cutting workflow wants.

    Args:
        sheet (Shell, optional): reference shell to develop. Defaults to the
            shell of the active ``BuildSheet``.
        sheet_parameters (SheetMetalParameters, optional): material and
            reference-surface parameters. Required in Algebra mode and supplied
            by ``BuildSheet`` in Builder mode.
        align (Align | tuple[Align, Align], optional): align MIN, CENTER or MAX
            of the pattern within Plane.XY. Defaults to Align.NONE.

    Raises:
        ValueError: no sheet Shell to unfold
        ValueError: sheet_parameters is required in Algebra mode
        ValueError: sheet_parameters is supplied by the active BuildSheet

    Returns:
        Shell: the flat pattern
    """
    context: BuildSheet | None = BuildSheet._get_context("unfold")
    validate_inputs(context, "unfold", [sheet] if sheet is not None else None)

    if sheet is None:
        if context is None:
            raise ValueError("unfold requires a sheet Shell")
        sheet = context.sheet_local
    if not isinstance(sheet, Shell):
        raise ValueError("unfold takes a sheet Shell")
    if not sheet.faces():
        raise ValueError("Can't unfold an empty sheet Shell")

    flat = sheet.unfold(_resolve_sheet_parameters(context, sheet_parameters))
    return flat.moved(Location(flat.bounding_box().to_align_offset(align)))


@overload
def corner_relief(
    vertices: Vertex | list[Vertex] | None = None,
    relief_type: Literal[ReliefType.ROUND] = ReliefType.ROUND,
    *,
    radius: float,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell: ...


@overload
def corner_relief(
    vertices: Vertex | list[Vertex] | None,
    relief_type: Literal[ReliefType.SQUARE],
    *,
    size: float,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell: ...


@overload
def corner_relief(
    vertices: Vertex | list[Vertex] | None,
    relief_type: Literal[ReliefType.OBROUND],
    *,
    length: float,
    width: float,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell: ...


@overload
def corner_relief(
    vertices: Vertex | list[Vertex] | None,
    relief_type: Literal[ReliefType.CONSTANT_WIDTH],
    *,
    depth: float,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell: ...


def corner_relief(
    vertices: Vertex | list[Vertex] | None = None,
    relief_type: ReliefType = ReliefType.ROUND,
    *,
    radius: float | None = None,
    size: float | None = None,
    length: float | None = None,
    width: float | None = None,
    depth: float | None = None,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell:
    """Cut corner relief where two bends meet.

    Each selected vertex must be a corner of a planar face with a bend on both
    sides of it. The relief opens that corner so the two flanges do not collide
    when the sheet is formed.

    The selected ``relief_type`` determines which parameters apply:

    * ``ROUND`` requires ``radius``.
    * ``SQUARE`` requires ``size``.
    * ``OBROUND`` requires ``length`` and ``width``.
    * ``CONSTANT_WIDTH`` requires ``depth``. Its width is measured from the
      part - it is the gap the flanges already leave - so that the separation
      carries on unchanged through the relief. It is only defined where the two
      flange edges are parallel.

    The first three are cut in the flat pattern and keep their shape on the
    developed blank. ``CONSTANT_WIDTH`` is defined by the formed part instead.

    Args:
        vertices: Corner vertex or vertices to relieve.
        relief_type: Shape of the relief. Defaults to ``ROUND``.
        radius: Circle radius for ``ROUND``.
        size: Side length for ``SQUARE``.
        length: Overall length along the diagonal for ``OBROUND``.
        width: Slot width for ``OBROUND``.
        depth: Distance the relief reaches into the sheet for
            ``CONSTANT_WIDTH``.
        sheet_parameters: Material and reference-surface parameters. Required
            in Algebra mode and supplied by ``BuildSheet`` in Builder mode -
            a relief is laid out on the blank, so its shape depends on where
            the neutral axis lies.

    Returns:
        The updated reference Shell.
    """
    context: BuildSheet | None = BuildSheet._get_context("corner_relief")
    # flatten_sequence(None) yields [None], so drop those before counting
    vertex_list = [
        vertex for vertex in flatten_sequence(vertices) if vertex is not None
    ]
    validate_inputs(context, "corner_relief", vertex_list)

    if not vertex_list:
        raise ValueError("corner_relief requires at least one vertex")
    if not all(isinstance(vertex, Vertex) for vertex in vertex_list):
        raise ValueError("corner_relief takes only Vertices")

    parameters = _resolve_sheet_parameters(context, sheet_parameters)
    supplied = {
        "radius": radius,
        "size": size,
        "length": length,
        "width": width,
        "depth": depth,
    }
    required = {
        ReliefType.ROUND: ("radius",),
        ReliefType.SQUARE: ("size",),
        ReliefType.OBROUND: ("length", "width"),
        ReliefType.CONSTANT_WIDTH: ("depth",),
    }[relief_type]

    def measurement(name: str) -> float:
        """The named parameter, checked as supplied and positive."""
        value = supplied[name]
        if value is None:
            raise ValueError(f"{name} is required for {relief_type}")
        if value <= 0:
            raise ValueError(f"{name} must be positive")
        return value

    values = {name: measurement(name) for name in required}
    extra = sorted(
        n for n, v in supplied.items() if v is not None and n not in required
    )
    if extra:
        raise ValueError(
            f"{relief_type} does not accept {', '.join(extra)} - "
            f"it takes {', '.join(required)}"
        )

    profile: list | None = None
    reach = 0.0
    if relief_type is ReliefType.ROUND:
        profile = _round_relief_profile(values["radius"])
    elif relief_type is ReliefType.SQUARE:
        profile = _square_relief_profile(values["size"])
    elif relief_type is ReliefType.OBROUND:
        if values["width"] >= values["length"]:
            raise ValueError("length must exceed width")
        profile = _obround_relief_profile(values["length"], values["width"])
    else:
        reach = values["depth"]

    target = _miter_target(context, vertex_list)
    for vertex in vertex_list:
        target = _cut_corner_relief(
            target, vertex, relief_type, profile, reach, parameters
        )

    if context is not None:
        context._add_to_context(*target.faces(), mode=Mode.REPLACE)
        return context.sheet_local
    return target


def _cut_corner_relief(
    shell: Shell,
    vertex: Vertex,
    relief_type: ReliefType,
    profile: list | None,
    depth: float,
    parameters: SheetMetalParameters,
) -> Shell:
    """Cut one corner, by whichever route the relief type is defined in."""
    corner = Vector(vertex)
    touching = [
        face
        for face in shell.faces()
        if face.geom_type == GeomType.PLANE
        and face.distance_to(corner) < _RELIEF_TOLERANCE
    ]
    if not touching:
        raise ValueError("corner_relief vertices must be a corner of a planar face")
    base = max(touching, key=lambda face: face.area)

    if relief_type is ReliefType.CONSTANT_WIDTH:
        cutter = _constant_width_cutter(shell, base, corner, depth, parameters)
        cut = shell.cut(cutter)
        result = cut if isinstance(cut, Shell) else Shell(cut.faces())
    elif profile is not None:
        frames, _ = _corner_frames(shell, base, corner, parameters)
        result = _replace_relief_faces(shell, _trim_faces(frames, profile))
    else:
        raise ValueError(f"no profile built for {relief_type}")

    _check_corner_detached(shell, result, corner)
    return result


@overload
def bend_relief(
    bends: Face | list[Face] | None = None,
    relief_type: Literal[ReliefType.ROUND] = ReliefType.ROUND,
    *,
    radius: float | None = None,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell: ...


@overload
def bend_relief(
    bends: Face | list[Face] | None,
    relief_type: Literal[ReliefType.SQUARE, ReliefType.OBROUND],
    *,
    depth: float | None = None,
    width: float | None = None,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell: ...


def bend_relief(
    bends: Face | list[Face] | None = None,
    relief_type: ReliefType = ReliefType.ROUND,
    *,
    radius: float | None = None,
    depth: float | None = None,
    width: float | None = None,
    sheet_parameters: SheetMetalParameters | None = None,
) -> Shell:
    """Cut relief where a bend ends inside the sheet.

    A bend that stops short of the edge of the blank leaves a corner where the
    sheet has to fold on one side of the fold line and stay flat on the other,
    which tears when it is formed. The relief notches the face the material
    carries on into, so the fold line ends on a free edge instead. Both ends of
    every selected bend are relieved; an end that already runs to the edge of
    the blank needs nothing and is left alone, so a selection may be used as a
    filter.

    Sizes left out follow the usual shop rule, measured from the fold line: the
    relief reaches the bend radius plus one thickness into the sheet and is one
    thickness wide.

    The selected ``relief_type`` determines which parameters apply:

    * ``ROUND`` accepts ``radius``. It is a hole centred on the end of the fold
      line, so it shortens the bend as well as notching the sheet beside it,
      and its radius has to fit the sheet left past the bend end. It defaults
      to one thickness rather than to the reach the notches use.
    * ``SQUARE`` and ``OBROUND`` accept ``depth`` and ``width``. Both cut only
      into the face beside the bend and differ in whether the far end is
      square-cornered or rounded.

    ``CONSTANT_WIDTH`` continues the gap two flanges leave and so is only
    defined where two of them meet - see ``corner_relief``.

    Args:
        bends: Cylindrical bend face or faces to relieve.
        relief_type: Shape of the relief. Defaults to ``ROUND``.
        radius: Hole radius for ``ROUND``.
        depth: How far past the fold line the relief reaches, for ``SQUARE``
            and ``OBROUND``.
        width: Width along the fold line, for ``SQUARE`` and ``OBROUND``.
        sheet_parameters: Material and reference-surface parameters. Required
            in Algebra mode and supplied by ``BuildSheet`` in Builder mode.

    Returns:
        The updated reference Shell.
    """
    context: BuildSheet | None = BuildSheet._get_context("bend_relief")
    # flatten_sequence(None) yields [None], so drop those before counting
    bend_list = [bend for bend in flatten_sequence(bends) if bend is not None]
    validate_inputs(context, "bend_relief", bend_list)

    if not bend_list:
        raise ValueError("bend_relief requires at least one bend face")
    if not all(isinstance(bend, Face) for bend in bend_list):
        raise ValueError("bend_relief takes only Faces")
    if any(bend.geom_type != GeomType.CYLINDER for bend in bend_list):
        raise ValueError("bend_relief takes only cylindrical bend faces")

    supplied = {"radius": radius, "depth": depth, "width": width}
    required = {
        ReliefType.ROUND: ("radius",),
        ReliefType.SQUARE: ("depth", "width"),
        ReliefType.OBROUND: ("depth", "width"),
    }.get(relief_type)
    if required is None:
        raise ValueError(
            f"{relief_type} is only defined where two flanges meet - "
            "use corner_relief"
        )
    extra = sorted(
        n for n, v in supplied.items() if v is not None and n not in required
    )
    if extra:
        raise ValueError(
            f"{relief_type} does not accept {', '.join(extra)} - "
            f"it takes {', '.join(required)}"
        )
    for name in required:
        value = supplied[name]
        if value is not None and value <= 0:
            raise ValueError(f"{name} must be positive")

    parameters = _resolve_sheet_parameters(context, sheet_parameters)

    target = _owning_shell(context, bend_list, "bend_relief faces")
    # every end is measured on the shell as given, before any of the cuts move
    # the faces around
    plans = []
    values: dict[str, float]
    for cylinder in bend_list:
        for point, away, bend_radius in _bend_ends(cylinder, target):
            values = {}
            for name in required:
                given = supplied[name]
                values[name] = (
                    given
                    if given is not None
                    else _relief_default(name, bend_radius, parameters)
                )
            if (
                relief_type is ReliefType.OBROUND
                and values["depth"] <= values["width"] / 2
            ):
                raise ValueError("depth must exceed half the width")
            plans.append((point, away, values))

    for point, away, values in plans:
        target = _cut_bend_relief(target, point, away, relief_type, values, parameters)

    if context is not None:
        context._add_to_context(*target.faces(), mode=Mode.REPLACE)
        return context.sheet_local
    return target


# ---------------------------------------------------------------------------
# corner relief
#
# A relief is cut in the flat blank before forming, so its boundary is a curve
# that was a circle, slot or rectangle when the sheet was flat. A prismatic 3D
# cutter cannot reproduce that curve once the profile reaches a bend: past the
# bend tangent it runs parallel to the wall and slices a channel instead of a
# hole. These helpers cut in the developed pattern instead, trimming each
# affected face inside its own UV domain. Every sheet face is planar or
# cylindrical, so each has an isometric development and the map from
# flat-pattern coordinates to a face's UV domain is affine; an affine image of
# a circle is a conic, so profiles stay exact - no BSpline approximation.
#
# Flat-pattern coordinates at a corner put the origin on the corner vertex,
# with x measuring the distance past one bend's tangent line and y past the
# other. Which part of the profile lands on which face is not worked out from
# those coordinates: the profile is clipped against each face's own boundary,
# so a bend held back by a flange gap, mitered, or wrapped around a hole
# corner gets exactly the part of the profile that lies on it.
#
# CONSTANT_WIDTH is the exception and is cut in 3D - see
# _constant_width_cutter for why.
# ---------------------------------------------------------------------------

_RELIEF_TOLERANCE = 1e-7


@dataclass(frozen=True)
class _FlatLine:
    """A straight run of a flat-pattern profile."""

    start: tuple[float, float]
    end: tuple[float, float]

    def point_at(self, fraction: float) -> tuple[float, float]:
        """A point along the segment, 0 at the start and 1 at the end."""
        (x0, y0), (x1, y1) = self.start, self.end
        return (x0 + fraction * (x1 - x0), y0 + fraction * (y1 - y0))


@dataclass(frozen=True)
class _FlatArc:
    """A circular arc of a flat-pattern profile, counter-clockwise."""

    center: tuple[float, float]
    radius: float
    start_angle: float  # radians
    end_angle: float  # radians, greater than start_angle

    def point_at(self, fraction: float) -> tuple[float, float]:
        """A point along the arc, 0 at the start and 1 at the end."""
        angle = self.start_angle + fraction * (self.end_angle - self.start_angle)
        return (
            self.center[0] + self.radius * cos(angle),
            self.center[1] + self.radius * sin(angle),
        )

    @property
    def start(self) -> tuple[float, float]:
        """First point of the arc."""
        return self.point_at(0.0)

    @property
    def end(self) -> tuple[float, float]:
        """Last point of the arc."""
        return self.point_at(1.0)


def _circle_profile(cx: float, cy: float, radius: float) -> list:
    """A closed circle as four quarter arcs."""
    quarters = [(0, pi / 2), (pi / 2, pi), (pi, 3 * pi / 2), (3 * pi / 2, 2 * pi)]
    return [_FlatArc((cx, cy), radius, a, b) for a, b in quarters]


def _rectangle_profile(cx: float, cy: float, width: float, height: float) -> list:
    """A closed axis-aligned rectangle as four lines."""
    half_w, half_h = width / 2, height / 2
    corners = [
        (cx - half_w, cy - half_h),
        (cx + half_w, cy - half_h),
        (cx + half_w, cy + half_h),
        (cx - half_w, cy + half_h),
    ]
    return [_FlatLine(corners[i], corners[(i + 1) % 4]) for i in range(len(corners))]


def _obround_profile(cx: float, cy: float, length: float, height: float) -> list:
    """A closed slot: two straight flanks joined by semicircular ends.

    Mixes both segment kinds, which is what every relief shape but ROUND
    needs.
    """
    radius = height / 2
    flank = (length - height) / 2
    profile: list = [
        _FlatLine((cx - flank, cy - radius), (cx + flank, cy - radius)),
        _FlatArc((cx + flank, cy), radius, -pi / 2, pi / 2),
        _FlatLine((cx + flank, cy + radius), (cx - flank, cy + radius)),
        _FlatArc((cx - flank, cy), radius, pi / 2, 3 * pi / 2),
    ]
    return profile


def _rotate_profile(profile: list, angle: float, about=(0.0, 0.0)) -> list:
    """Turn a flat profile about a point, angle in radians."""

    def spin(point):
        dx, dy = point[0] - about[0], point[1] - about[1]
        return (
            about[0] + dx * cos(angle) - dy * sin(angle),
            about[1] + dx * sin(angle) + dy * cos(angle),
        )

    turned: list = []
    for seg in profile:
        if isinstance(seg, _FlatLine):
            turned.append(_FlatLine(spin(seg.start), spin(seg.end)))
        else:
            turned.append(
                _FlatArc(
                    spin(seg.center),
                    seg.radius,
                    seg.start_angle + angle,
                    seg.end_angle + angle,
                )
            )
    return turned


@dataclass
class _FlatFrame:
    """Maps flat-pattern coordinates into one face's UV domain.

    The map is affine for both planar and cylindrical faces, so a flat line
    is a line in UV and a flat circle is a conic - nothing is approximated.
    """

    face: Face
    matrix: np.ndarray  # 2x2, flat -> uv
    offset: np.ndarray  # uv of flat (0, 0)

    def to_uv(self, x: float, y: float) -> gp_Pnt2d:
        """Flat-pattern point as a parameter-space point on this face."""
        u, v = self.matrix @ np.array([x, y]) + self.offset
        return gp_Pnt2d(u, v)

    @property
    def surface(self):
        """The face's underlying geometric surface."""
        return BRep_Tool.Surface_s(self.face.wrapped)

    def segment(self, seg) -> tuple:
        """A flat segment's exact image in this face's UV domain.

        Returns ``(curve2d, first, last, flipped)`` with ``first < last``.
        ``flipped`` says the curve's parameter runs against the segment's own
        direction, which happens when the development mirrors the face.
        """
        if isinstance(seg, _FlatLine):
            start, end = self.to_uv(*seg.start), self.to_uv(*seg.end)
            direction = np.array([end.X() - start.X(), end.Y() - start.Y()])
            length = float(np.hypot(*direction))
            curve = Geom2d_Line(start, gp_Dir2d(*direction))
            return curve, 0.0, length, False

        curve = self.circle(seg.center[0], seg.center[1], seg.radius)
        first, last, middle = (
            self.conic_parameter(angle)
            for angle in (
                seg.start_angle,
                seg.end_angle,
                (seg.start_angle + seg.end_angle) / 2,
            )
        )
        # a mirroring development reverses the parameter sense, and then the
        # span from first to last is the complementary arc
        flipped = not _between(middle, first, last, curve)
        if flipped:
            first, last = last, first
        if last < first:
            last += curve.Period()
        return curve, first, last, flipped

    def conic_parameter(self, angle: float) -> float:
        """Where a flat circle's point at an angle lands on its conic image.

        The affine part factors as a rotation, a scaling along the conic's
        axes and another rotation; the first rotation is all that moves the
        angle, since the scaling is what the conic's own parameter absorbs.
        """
        _, _, right = np.linalg.svd(self.matrix)
        turned = right @ np.array([cos(angle), sin(angle)])
        return atan2(turned[1], turned[0]) % (2 * pi)

    def circle(self, cx: float, cy: float, radius: float):
        """The flat circle's exact image in this face's UV domain.

        A rigid development (a planar face) leaves a circle a circle; a
        cylindrical development scales one axis by 1/bend radius, which turns
        it into an ellipse.
        """
        center = self.to_uv(cx, cy)
        # singular values of the affine part give the conic's semi-axes, and
        # the left factor their directions - a mirrored pair where the
        # development mirrors the face, which the axis system carries
        left, scales, _ = np.linalg.svd(self.matrix)
        axes = gp_Ax22d(
            center,
            gp_Dir2d(left[0, 0], left[1, 0]),
            gp_Dir2d(left[0, 1], left[1, 1]),
        )
        major, minor = radius * scales[0], radius * scales[1]
        if abs(major - minor) < _RELIEF_TOLERANCE:
            return Geom2d_Circle(axes, major)
        return Geom2d_Ellipse(axes, major, minor)


def _plane_frame(face: Face, origin: Vector, axes: tuple[Vector, Vector]) -> _FlatFrame:
    """The frame of a planar face whose flat point (x, y) lies at
    ``origin + axes[0] * x + axes[1] * y``.

    A plane's parameters are distances along its own two directions, so the
    map is read straight off them.
    """
    position = BRepAdaptor_Surface(face.wrapped).Plane().Position()
    base = Vector(position.Location())
    directions = [Vector(position.XDirection()), Vector(position.YDirection())]
    matrix = np.array(
        [[axis.dot(direction) for axis in axes] for direction in directions]
    )
    offset = np.array([(origin - base).dot(direction) for direction in directions])
    return _FlatFrame(face=face, matrix=matrix, offset=offset)


def _cylinder_frame(
    face: Face, corner: Vector, unroll: int, slide: Vector, rolling: float
) -> _FlatFrame:
    """The frame of a bend face unrolled flat about a fold line.

    ``corner`` is a point on the fold line, ``slide`` runs along it, and the
    flat axis numbered ``unroll`` measures past it into the bend while the
    other measures along it. A cylinder's ``u`` is the angle about its axis
    and ``v`` the distance along it, so the fold line is a line of constant
    ``u`` and the bend spans from there to the face's other ``u`` bound, at
    ``rolling`` units of blank per radian.
    """
    position = BRepAdaptor_Surface(face.wrapped).Cylinder().Position()
    axis = Vector(position.Direction())
    spoke = corner - Vector(position.Location())
    v_corner = spoke.dot(axis)
    radial = spoke - axis * v_corner
    u_corner = atan2(
        radial.dot(Vector(position.YDirection())),
        radial.dot(Vector(position.XDirection())),
    )
    # the face may be parameterised any number of turns from where atan2 lands
    u_min, u_max, _, _ = BRepTools.UVBounds_s(face.wrapped)
    u_corner += 2 * pi * round(((u_min + u_max) / 2 - u_corner) / (2 * pi))
    sign = 1.0 if abs(u_corner - u_min) < abs(u_corner - u_max) else -1.0

    matrix = np.zeros((2, 2))
    matrix[0, unroll] = sign / rolling
    matrix[1, 1 - unroll] = slide.dot(axis)
    return _FlatFrame(face=face, matrix=matrix, offset=np.array([u_corner, v_corner]))


def _corner_frames(
    shell: Shell, base: Face, corner: Vector, parameters: SheetMetalParameters
) -> tuple[list[_FlatFrame], bool]:
    """Flat frames for the faces meeting at one corner of a planar face.

    All three share one flat coordinate system with its origin at ``corner``:
    ``x`` measures past the tangent line of one bend and ``y`` past the other.
    Returns the base's frame followed by the two bends', and whether the
    sheet wraps around the corner rather than stopping at it.
    """
    # The two bends whose tangent lines cross at this corner. They are found
    # by line rather than by adjacency, because a flange gap pulls a bend back
    # from the corner without moving the line it folds about - the corner is
    # still where the two fold lines meet.
    touching = []
    for edge in base.edges():
        others = [
            Face(f)
            for f in topo_explore_connected_faces(edge, shell)
            if f is not None and not Face(f).is_same(base)
        ]
        bends = [f for f in others if f.geom_type.name == "CYLINDER"]
        if not bends:
            continue
        start = Vector(edge.position_at(0))
        along = (Vector(edge.position_at(1)) - start).normalized()
        offset = corner - start
        if (offset - along * offset.dot(along)).length > _RELIEF_TOLERANCE:
            continue  # the corner is not on this fold line
        touching.append((edge, bends[0]))
    if len(touching) != 2:
        raise ValueError(
            f"{len(touching)} fold line(s) pass through this corner, expected 2"
        )

    # each bend unrolls perpendicular to its own tangent line, away from the
    # base: x unrolls the first bend and y the second
    axis_dir = [_fold_outward(base, edge) for edge, _ in touching]
    frames = [_plane_frame(base, corner, (axis_dir[0], axis_dir[1]))]
    for index, (_, cylinder) in enumerate(touching):
        # measured on the neutral axis, so the flat coordinates are those of
        # the blank rather than of the reference surface
        radius = cylinder.radius
        if radius is None:
            raise ValueError("relief expects a cylindrical bend face")
        rolling = neutral_radius(radius, parameters, is_positive_bend(cylinder.wrapped))
        frames.append(
            _cylinder_frame(cylinder, corner, index, axis_dir[1 - index], rolling)
        )
    return frames, _corner_is_concave(base, corner, axis_dir)


def _corner_is_concave(base: Face, corner: Vector, axis_dir: list) -> bool:
    """Does the sheet wrap around this corner rather than stop at it?

    Told apart by the quadrant past one fold line but not the other. At a
    corner the sheet stops at, that quadrant holds a bend; at one it wraps
    around, the sheet is still there and both bends unroll into the quadrant
    past both lines instead.
    """
    step = max(min(direction.length for direction in axis_dir) * 1e-5, 1e-5)
    return base.is_inside(corner + (axis_dir[0] - axis_dir[1]) * step)


# --------------------------------------------------------------------------
# trimming
#
# A profile is cut into each face it crosses inside that face's parameter
# space. Its exact image there is intersected with the face's boundary
# curves, the pieces that land inside the face become new boundary edges, and
# the boundary between where such a piece enters and where it leaves is
# dropped. Nothing is intersected in 3D. Every edge has to carry a 3D curve,
# so the new edges are given one approximated from their exact pcurve, and
# they carry the tolerance of that approximation - but the topology was
# settled before it was made.
#
# A profile runs with the material it removes on its left, so which side of
# a cut to keep is a matter of orientation rather than of area.
# --------------------------------------------------------------------------

_CLIP_TOLERANCE = 1e-9  # in parameter space, where every curve is exact


@dataclass
class _Bound:
    """One edge of a face's boundary, as walked with the material on the left."""

    edge: TopoDS_Edge  # oriented as it is walked
    curve: Geom2d_Curve  # its pcurve on the face
    first: float
    last: float

    @property
    def walk(self) -> tuple[float, float]:
        """Parameters at the start and end of the walk along this edge."""
        if self.edge.Orientation() == ta.TopAbs_REVERSED:
            return self.last, self.first
        return self.first, self.last

    def position(self, parameter: float) -> float:
        """How far along the walk a parameter lies, from 0 to 1."""
        start, end = self.walk
        return (parameter - start) / (end - start)

    def vertex(self, parameter: float) -> TopoDS_Vertex:
        """The vertex at a parameter, the edge's own where it has one."""
        start, end = self.walk
        if abs(parameter - start) < _RELIEF_TOLERANCE:
            return TopExp.FirstVertex_s(self.edge, True)
        if abs(parameter - end) < _RELIEF_TOLERANCE:
            return TopExp.LastVertex_s(self.edge, True)
        vertex = TopoDS_Vertex()
        BRep_Builder().MakeVertex(
            vertex,
            BRepAdaptor_Curve(self.edge).Value(parameter),
            max(TOLERANCE, 2 * BRep_Tool.Tolerance_s(self.edge)),
        )
        return vertex

    def part(
        self, start: float, end: float, first: TopoDS_Vertex, last: TopoDS_Vertex
    ) -> list[TopoDS_Edge]:
        """The stretch of this edge walked from one parameter to another.

        The whole edge is itself; a part is an empty copy of it - the same
        curves, and so the same geometry its neighbour across the edge sees -
        cut down to the range.
        """
        if abs(end - start) < _RELIEF_TOLERANCE:
            return []
        walk = self.walk
        if abs(start - walk[0]) < _RELIEF_TOLERANCE:
            if abs(end - walk[1]) < _RELIEF_TOLERANCE:
                return [self.edge]
        part = TopoDS.Edge(self.edge.EmptyCopied().Oriented(ta.TopAbs_FORWARD))
        builder = BRep_Builder()
        builder.Range(part, min(start, end), max(start, end))
        low, high = (first, last) if start < end else (last, first)
        builder.Add(part, low.Oriented(ta.TopAbs_FORWARD))
        builder.Add(part, high.Oriented(ta.TopAbs_REVERSED))
        return [TopoDS.Edge(part.Oriented(self.edge.Orientation()))]


def _face_bounds(face: TopoDS_Face) -> list[tuple[TopoDS_Wire, list[_Bound]]]:
    """Every wire of a FORWARD face, with its edges in walking order."""
    wires = []
    explorer = TopExp_Explorer(face, ta.TopAbs_WIRE)
    while explorer.More():
        wire = TopoDS.Wire(explorer.Current())
        bounds = []
        walker = BRepTools_WireExplorer(wire, face)
        while walker.More():
            edge = walker.Current()
            adaptor = BRepAdaptor_Curve2d(edge, face)
            bounds.append(
                _Bound(
                    edge,
                    adaptor.Curve(),
                    adaptor.FirstParameter(),
                    adaptor.LastParameter(),
                )
            )
            walker.Next()
        wires.append((wire, bounds))
        explorer.Next()
    return wires


@dataclass(frozen=True)
class _Hit:
    """Where a profile meets a face's boundary."""

    wire: int
    bound: int
    parameter: float


@dataclass
class _Piece:
    """A stretch of a profile's image in one face's parameter space.

    ``flipped`` says the profile runs this curve from ``last`` to ``first``.
    ``hits`` are where its start and end, in the profile's order, meet the
    boundary - None where they do not.
    """

    curve: Geom2d_Curve
    first: float
    last: float
    flipped: bool
    hits: tuple

    def reversed(self) -> "_Piece":
        """This piece run the other way."""
        return _Piece(
            self.curve, self.first, self.last, not self.flipped, self.hits[::-1]
        )

    @property
    def start(self) -> float:
        """Parameter at the profile's start of this piece."""
        return self.last if self.flipped else self.first

    @property
    def end(self) -> float:
        """Parameter at the profile's end of this piece."""
        return self.first if self.flipped else self.last


def _clip_profile(
    frame: _FlatFrame, face: TopoDS_Face, bounds: list, profile: list, closed: bool
) -> list[list[_Piece]]:
    """The runs of a profile that lie inside a face, in its parameter space.

    Every segment is broken where it crosses the boundary, and each piece is
    inside or outside as a whole. Consecutive inside pieces make a run.
    """
    classifier = BRepTopAdaptor_FClass2d(face, _CLIP_TOLERANCE)
    boundary = [
        (
            (wire_index, bound_index),
            Geom2dAdaptor_Curve(
                Geom2d_TrimmedCurve(bound.curve, bound.first, bound.last)
            ),
        )
        for wire_index, (_, wire) in enumerate(bounds)
        for bound_index, bound in enumerate(wire)
    ]

    ordered: list[tuple[bool, _Piece]] = []
    for seg in profile:
        curve, first, last, flipped = frame.segment(seg)
        span = Geom2dAdaptor_Curve(Geom2d_TrimmedCurve(curve, first, last))
        hits: dict[float, _Hit] = {}
        for where, edge_curve in boundary:
            crossings = Geom2dInt_GInter(
                span, edge_curve, _CLIP_TOLERANCE, _CLIP_TOLERANCE
            )
            for index in range(1, crossings.NbPoints() + 1):
                point = crossings.Point(index)
                found = point.ParamOnFirst()
                if curve.IsPeriodic():  # reported within one turn of the origin
                    found += curve.Period() * round((first - found) / curve.Period())
                    if found < first - _CLIP_TOLERANCE:
                        found += curve.Period()
                # a crossing at a vertex is reported by both edges there
                if any(abs(found - known) < _CLIP_TOLERANCE for known in hits):
                    continue
                hits[found] = _Hit(*where, point.ParamOnSecond())

        breaks = [
            first,
            *sorted(p for p in hits if first + 1e-7 < p < last - 1e-7),
            last,
        ]
        pieces = []
        for lower, upper in zip(breaks, breaks[1:]):
            inside = (
                classifier.Perform(curve.Value((lower + upper) / 2)) == ta.TopAbs_IN
            )
            ends = tuple(
                next((hit for at, hit in hits.items() if abs(at - p) < 1e-7), None)
                for p in (lower, upper)
            )
            pieces.append(
                (
                    inside,
                    _Piece(curve, lower, upper, flipped, ends[:: -1 if flipped else 1]),
                )
            )
        ordered.extend(reversed(pieces) if flipped else pieces)

    runs: list[list[_Piece]] = []
    current: list[_Piece] = []
    for inside, piece in ordered:
        if inside:
            current.append(piece)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    # a closed profile's first and last pieces adjoin
    if closed and len(runs) > 1 and ordered[0][0] and ordered[-1][0]:
        runs[0] = runs.pop() + runs[0]
    return runs


def _trim_face(
    frame: _FlatFrame, face: Face, profile: list, closed: bool = True
) -> Face:
    """Cut a flat profile out of one face, in its own parameter space.

    The profile runs with the material it removes on its left. A face is
    handled FORWARD, where that puts its own material on the left of its
    boundary too, and given its orientation back afterwards.
    """
    forward = TopoDS.Face(face.wrapped.Oriented(ta.TopAbs_FORWARD))
    bounds = _face_bounds(forward)
    runs = _clip_profile(frame, forward, bounds, profile, closed)
    if not runs:
        return face
    # the development may mirror the face, and then the removed material is
    # on the profile's right in parameter space
    if np.linalg.det(frame.matrix) < 0:
        runs = [[piece.reversed() for piece in reversed(run)] for run in runs]
    for run in runs:
        start, end = run[0].hits[0], run[-1].hits[1]
        if start is None or end is None:
            raise ValueError(
                "the profile lies inside the face"
                if closed
                else "the cut does not reach the boundary of the face"
            )
        if start.wire != end.wire:
            raise ValueError(
                "the profile crosses from one boundary of the face to another"
            )

    rebuilt = _rebuild_face(forward, bounds, runs)
    return Face(TopoDS.Face(rebuilt.Oriented(face.wrapped.Orientation())))


def _rebuild_face(face: TopoDS_Face, bounds: list, runs: list) -> TopoDS_Face:
    """A face with its boundary re-routed along some runs of a profile.

    Walking a wire with the material on the left, a run's start is where the
    walk leaves what is kept and its end is where the walk comes back to it,
    so the boundary is kept from each run's end to the next run's start and
    the runs themselves are walked backwards in between.
    """
    location = TopLoc_Location()
    surface = BRep_Tool.Surface_s(face, location)
    tolerance = BRep_Tool.Tolerance_s(face)
    builder = BRep_Builder()

    def point_of(curve, parameter: float) -> gp_Pnt:
        uv = curve.Value(parameter)
        return surface.Value(uv.X(), uv.Y()).Transformed(location.Transformation())

    def run_edges(run: list, first: TopoDS_Vertex, last: TopoDS_Vertex) -> list:
        """The run as edges, walked backwards from ``last`` to ``first``."""
        vertices = [first]
        for piece in run[:-1]:
            vertex = TopoDS_Vertex()
            builder.MakeVertex(vertex, point_of(piece.curve, piece.end), TOLERANCE)
            vertices.append(vertex)
        vertices.append(last)
        edges = []
        for piece, start, end in zip(run, vertices, vertices[1:]):
            low, high = (end, start) if piece.flipped else (start, end)
            edge = TopoDS_Edge()
            builder.MakeEdge(edge)
            builder.UpdateEdge(edge, piece.curve, surface, location, tolerance)
            builder.Range(edge, piece.first, piece.last)
            builder.Add(edge, low.Oriented(ta.TopAbs_FORWARD))
            builder.Add(edge, high.Oriented(ta.TopAbs_REVERSED))
            BRepLib.BuildCurves3d_s(edge)
            # walked backwards, so against the profile's own direction
            edges.append(
                TopoDS.Edge(
                    edge.Oriented(
                        ta.TopAbs_FORWARD if piece.flipped else ta.TopAbs_REVERSED
                    )
                )
            )
        return list(reversed(edges))

    rebuilt = TopoDS_Face()
    builder.MakeFace(rebuilt, surface, location, tolerance)
    for wire_index, (wire, wire_bounds) in enumerate(bounds):
        here = [run for run in runs if run[0].hits[0].wire == wire_index]
        if not here:
            builder.Add(rebuilt, wire)
            continue

        # every hit on this wire in walking order, with its vertex made once
        stops = []
        for run in here:
            for hit, kind in ((run[0].hits[0], "start"), (run[-1].hits[1], "end")):
                bound = wire_bounds[hit.bound]
                stops.append(
                    (
                        (hit.bound, bound.position(hit.parameter)),
                        kind,
                        run,
                        hit,
                        bound.vertex(hit.parameter),
                    )
                )
        stops.sort(key=lambda stop: stop[0])
        count = len(wire_bounds)

        # follow the boundary from each run's start to the next run's end,
        # then that run backwards to its own start, until the loop closes
        starts = {index for index, stop in enumerate(stops) if stop[1] == "start"}
        loops = []
        while starts:
            new_wire = TopoDS_Wire()
            builder.MakeWire(new_wire)
            opening = cursor = starts.pop()
            while True:
                _, _, _, hit, vertex = stops[cursor]
                _, next_kind, ending, next_hit, next_vertex = stops[
                    (cursor + 1) % len(stops)
                ]
                if next_kind != "end":
                    raise ValueError("the profile runs cross each other on the face")
                leaving = wire_bounds[hit.bound]
                arriving = wire_bounds[next_hit.bound]
                if hit.bound == next_hit.bound and (
                    leaving.position(hit.parameter)
                    <= arriving.position(next_hit.parameter)
                ):
                    edges = leaving.part(
                        hit.parameter, next_hit.parameter, vertex, next_vertex
                    )
                else:
                    edges = leaving.part(
                        hit.parameter,
                        leaving.walk[1],
                        vertex,
                        leaving.vertex(leaving.walk[1]),
                    )
                    between = (hit.bound + 1) % count
                    while between != next_hit.bound:
                        edges.append(wire_bounds[between].edge)
                        between = (between + 1) % count
                    edges += arriving.part(
                        arriving.walk[0],
                        next_hit.parameter,
                        arriving.vertex(arriving.walk[0]),
                        next_vertex,
                    )
                cursor = next(
                    index
                    for index, stop in enumerate(stops)
                    if stop[2] is ending and stop[1] == "start"
                )
                for edge in edges + run_edges(ending, stops[cursor][4], next_vertex):
                    builder.Add(new_wire, edge)
                if cursor == opening:
                    break
                starts.remove(cursor)
            loops.append(new_wire)
        if len(loops) > 1:
            raise ValueError("the cut separates part of the face from the rest")
        builder.Add(rebuilt, loops[0])
    return rebuilt


def _trim_faces(frames: list, profile: list, closed: bool = True) -> dict:
    """Cut a profile into every face it crosses, as ``{face: trimmed face}``."""
    trimmed = {}
    for frame in frames:
        result = _trim_face(frame, frame.face, profile, closed)
        if result is not frame.face:
            trimmed[frame.face] = result
    return trimmed


def _between(value: float, first: float, last: float, curve) -> bool:
    """Is a parameter inside the periodic span from first to last?"""
    period = curve.Period() if curve.IsPeriodic() else None
    if period is None:
        return min(first, last) <= value <= max(first, last)
    span = (last - first) % period
    return ((value - first) % period) <= span


# --------------------------------------------------------------------------
# guards
# --------------------------------------------------------------------------


def _flat_to_3d(frame: _FlatFrame, x: float, y: float) -> Vector:
    """A flat-pattern point as a 3D point on the frame's face."""
    uv = frame.to_uv(x, y)
    return Vector(frame.surface.Value(uv.X(), uv.Y()))


def _check_corner_detached(before: Shell, after: Shell, corner: Vector) -> None:
    """A corner relief must remove the corner.

    A profile closed at or before the corner still cuts faithfully - it takes
    a lens off an edge - but leaves the corner vertex in place.
    """
    if any((Vector(v) - corner).length < _RELIEF_TOLERANCE for v in after.vertices()):
        raise ValueError(
            "the corner vertex survived the relief - the profile closes at or "
            "before the corner instead of opening through it"
        )
    if before.area - after.area <= _RELIEF_TOLERANCE:
        raise ValueError("the relief removed nothing")


def _replace_relief_faces(shell: Shell, replacements: dict[Face, Face]) -> Shell:
    """Rebuild a shell with some faces swapped, then re-sew."""
    faces = []
    for face in shell.faces():
        match = next((v for k, v in replacements.items() if k.is_same(face)), None)
        faces.append(match if match is not None else face)
    return Shell(faces)


def _corner_mirror_plane(
    shell: Shell, base: Face, corner: Vector, parameters: SheetMetalParameters
):
    """The plane that bisects a corner, as (origin, unit normal).

    Its normal is the bisector of the two tangent directions, so the two
    flanges sit symmetrically either side of it.
    """
    frames, _ = _corner_frames(shell, base, corner, parameters)
    # the two unroll directions are the frames' flat axes; their difference
    # bisects the corner
    first = _flat_to_3d(frames[0], 1.0, 0.0) - corner
    second = _flat_to_3d(frames[0], 0.0, 1.0) - corner
    normal = (first.normalized() - second.normalized()).normalized()
    return corner, normal


def _corner_faces(
    shell: Shell, base: Face, corner: Vector, parameters: SheetMetalParameters
) -> list:
    """The bends meeting at a corner and the walls they carry."""
    frames, wrapped = _corner_frames(shell, base, corner, parameters)
    if wrapped:
        raise ValueError(
            "the sheet wraps around this corner, so its flanges have no single "
            "gap to carry through - a constant width relief is not defined here"
        )
    faces = [frame.face for frame in frames[1:]]
    for cylinder in list(faces):
        neighbours = {
            Face(f)
            for edge in cylinder.edges()
            for f in topo_explore_connected_faces(edge, shell)
            if f is not None
        }
        faces.extend(
            f for f in neighbours if f.geom_type.name == "PLANE" and not f.is_same(base)
        )
    return faces


def _flange_separation(
    shell: Shell, base: Face, corner: Vector, parameters: SheetMetalParameters
) -> float:
    """The gap the two flanges leave at a corner, measured from the sheet.

    A constant width relief has to continue this gap, so its width is a
    property of the part rather than something a user should have to work out.
    Only meaningful when the two flange edges are parallel; anything else has
    no single separation to continue and is rejected.
    """
    # each bend carries a wall; that wall's free edge nearest the corner is
    # what bounds the gap
    walls = [
        f
        for f in _corner_faces(shell, base, corner, parameters)
        if f.geom_type.name == "PLANE"
    ]
    if len(walls) != 2:
        raise ValueError(f"corner carries {len(walls)} wall(s), expected 2")

    edges = []
    for wall in walls:
        free = [
            e for e in wall.edges() if len(topo_explore_connected_faces(e, shell)) == 1
        ]
        if not free:
            raise ValueError("flange wall has no free edge")
        edges.append(min(free, key=lambda e: e.distance_to(corner)))

    directions = [(Vector(e @ 1) - Vector(e @ 0)).normalized() for e in edges]
    if directions[0].cross(directions[1]).length > 1e-6:
        raise ValueError(
            "flange edges at this corner are not parallel, so the gap between "
            "them is not constant - a constant width relief is not defined here"
        )
    return edges[0].distance_to(edges[1])


def _round_relief_profile(radius: float) -> list:
    """A circular corner relief, centred on the corner."""
    return _circle_profile(0.0, 0.0, radius)


def _square_relief_profile(size: float) -> list:
    """A square corner relief, aligned with the two bend lines."""
    return _rectangle_profile(0.0, 0.0, size, size)


def _obround_relief_profile(length: float, width: float) -> list:
    """A slotted corner relief lying on the diagonal between the two bends."""
    return _rotate_profile(_obround_profile(0.0, 0.0, length, width), pi / 4)


def _constant_width_cutter(  # pylint: disable=too-many-locals
    shell: Shell,
    base: Face,
    corner: Vector,
    depth: float,
    parameters: SheetMetalParameters,
) -> Solid:
    """A solid that cuts a constant width relief at a corner.

    Unlike the other relief shapes this one is not a flat-pattern feature. It
    is defined by the formed part - the gap between the two flanges has to
    carry on unchanged through the corner - and that gap is the distance
    between two planes parallel to the corner's mirror plane. Cutting with a
    solid bounded by those planes reproduces it exactly, and OCCT builds the
    pcurves: an ellipse across each bend and a line across each planar face.

    Drawing the same relief on the blank does not work. A flank that is
    straight in the developed pattern is not at a constant distance from the
    mirror plane once formed, so the gap pinches through the bends.
    """
    width = _flange_separation(shell, base, corner, parameters)
    _, normal = _corner_mirror_plane(shell, base, corner, parameters)
    up = base.normal_at(base.center())

    # in the base plane, along the mirror plane, pointing away from the base
    along = up.cross(normal).normalized()
    if (base.center() - corner).dot(along) > 0:
        along = -along

    # The rounded end pulls the cut back by its own radius, so the slot has to
    # reach the far side of the corner plus that radius. Falling short leaves a
    # wedge of each bend behind, which shows up as a step along the relief.
    reach = max(
        (Vector(vertex) - corner).dot(along)
        for face in _corner_faces(shell, base, corner, parameters)
        for vertex in face.vertices()
    )
    overshoot = reach + width / 2 + _RELIEF_TOLERANCE

    span = shell.bounding_box().diagonal
    length = depth + overshoot
    body_plane = Plane(
        origin=tuple(corner + along * (overshoot - length / 2) - up * span),
        z_dir=tuple(up),
        x_dir=tuple(along),
    )
    body = Solid.extrude(
        Face.make_rect(width, length, body_plane.rotated((0, 0, 90))),
        up * 2 * span,
    )
    cap_plane = Plane(
        origin=tuple(corner - along * depth - up * span),
        z_dir=tuple(up),
        x_dir=tuple(along),
    )
    cap = Solid.make_cylinder(width / 2, 2 * span, cap_plane)
    return body.fuse(cap).clean()


# --------------------------------------------------------------------------
# bend relief
#
# A bend relief goes where a fold line stops inside the material. In the flat
# blank that end is a reflex corner: the sheet on one side of the line has to
# fold while the sheet beyond the end has to stay flat, and forming it tears.
# The relief notches the face the material carries on into, so the line ends
# on a free edge instead.
#
# Flat-pattern coordinates at a bend end put the origin on the end of the fold
# line, with x running along the line away from the bend and y past the line
# into the bend. The face being relieved occupies y < 0, the bend unrolls into
# x < 0 < y, and the quadrant past both holds no material. A notch that stays
# in y < 0 is cut as an open chain across that one face; a round relief is a
# hole centred on the end of the line, so it reaches into the bend as well and
# is trimmed in the developed pattern the way a corner relief is.
# --------------------------------------------------------------------------

_RELIEF_PROBE = 1e-3  # fraction of the local size used when testing for material


def _relief_default(
    name: str, bend_radius: float, parameters: SheetMetalParameters
) -> float:
    """The conventional relief size, measured from the fold line."""
    if name in ("width", "radius"):
        # a hole is bounded by the sheet left past the bend end, which is
        # often only the gap the flange leaves, so it does not follow depth
        return parameters.thickness
    return bend_radius + parameters.thickness


def _fold_outward(face: Face, fold: Edge) -> Vector:
    """The direction across a fold line that points away from a planar face.

    Found by stepping off the line, the way ``flange`` finds it, rather than by
    asking which side of it the face's centre lies on. A centre says nothing
    useful about a fold line bounding a hole, where it sits inside the hole and
    the material is on the far side of the line from it.
    """
    start = Vector(fold.position_at(0))
    along = (Vector(fold.position_at(1)) - start).normalized()
    middle = fold.position_at(0.5)
    outward = along.cross(face.normal_at(middle)).normalized()
    probe = middle + outward * max(fold.length * 1e-5, 1e-5)
    return -outward if face.is_inside(probe) else outward


def _bend_end_probe(
    point: Vector, away: Vector, outward: Vector, step: float
) -> Vector:
    """A point just past a bend end and just inside the face beside it.

    It is on material exactly when the sheet carries on past the end of the
    fold line, which is what makes that end need relief - and once relieved,
    it is the material the notch has to have taken away.
    """
    return point + away * step - outward * step


def _bend_folds(cylinder: Face, shell: Shell) -> list:
    """The fold lines of a bend, each with the planar face it joins."""
    folds = []
    for edge in cylinder.edges():
        if edge.geom_type != GeomType.LINE:
            continue
        planes = [
            Face(face)
            for face in topo_explore_connected_faces(edge, shell)
            if face is not None and Face(face).geom_type == GeomType.PLANE
        ]
        if len(planes) == 1:
            folds.append((edge, planes[0]))
    if not folds:
        raise ValueError("bend_relief expects a bend joined to a planar face")
    return folds


def _bend_ends(cylinder: Face, shell: Shell) -> list:
    """Each end of a bend that stops inside material.

    Returns ``(point, away, radius)`` per end, ``away`` pointing along the
    fold line out of the bend. An end that runs to the edge of the blank needs no relief
    and is left out. An end with material on both sides of the line calls for
    the sheet to be ripped rather than notched, which is not a cut this
    operation can make.
    """
    radius = cylinder.radius
    if radius is None:
        raise ValueError("bend_relief takes only cylindrical bend faces")
    folds = _bend_folds(cylinder, shell)
    first = folds[0][0]
    along = (Vector(first.position_at(1)) - Vector(first.position_at(0))).normalized()
    step = _RELIEF_PROBE * min(first.length, radius)
    middle = cylinder.center()

    ends = []
    for direction in (along, -along):
        found = []
        for edge, plane in folds:
            corners = [Vector(edge.position_at(end)) for end in (0.0, 1.0)]
            reach = [(corner - middle).dot(direction) for corner in corners]
            point = corners[0] if reach[0] > reach[1] else corners[1]
            outward = _fold_outward(plane, edge)
            probe = _bend_end_probe(point, direction, outward, step)
            if plane.distance_to(probe) < step / 2:
                found.append(point)
        if len(found) > 1:
            raise ValueError(
                "this bend ends with material on both sides of the fold line, "
                "which needs the sheet ripped rather than notched"
            )
        if found:
            ends.append((found[0], direction, radius))
    return ends


def _bend_end_frames(
    shell: Shell, point: Vector, away: Vector, parameters: SheetMetalParameters
) -> tuple:
    """Flat frames for the two faces meeting at the end of a fold line.

    Both share one flat coordinate system with its origin on that end: ``x``
    runs along the line away from the bend and ``y`` past the line into the
    bend. Returns ``([base frame, bend frame], probe, step)``.
    """
    fold = None
    for edge in shell.edges():
        if edge.geom_type != GeomType.LINE:
            continue
        corners = [Vector(edge.position_at(end)) for end in (0.0, 1.0)]
        if min((corner - point).length for corner in corners) > _RELIEF_TOLERANCE:
            continue
        heading = (corners[1] - corners[0]).normalized()
        if abs(heading.dot(away)) < 1 - _RELIEF_TOLERANCE:
            continue  # a fold line crossing this one, not the one ending here
        neighbours = [
            Face(face)
            for face in topo_explore_connected_faces(edge, shell)
            if face is not None
        ]
        planes = [f for f in neighbours if f.geom_type == GeomType.PLANE]
        bends = [f for f in neighbours if f.geom_type == GeomType.CYLINDER]
        if len(planes) == 1 and len(bends) == 1:
            fold = (edge, planes[0], bends[0])
            break
    if fold is None:
        raise ValueError("no fold line ends at this point")

    edge, base, cylinder = fold
    outward = _fold_outward(base, edge)
    radius = cylinder.radius
    if radius is None:
        raise ValueError("relief expects a cylindrical bend face")
    # measured on the neutral axis, so the flat coordinates are the blank's
    rolling = neutral_radius(radius, parameters, is_positive_bend(cylinder.wrapped))
    frames = [
        _plane_frame(base, point, (away, outward)),
        _cylinder_frame(cylinder, point, 1, away, rolling),
    ]
    step = _RELIEF_PROBE * min(edge.length, radius)
    return frames, _bend_end_probe(point, away, outward, step), step


def _bend_square_profile(depth: float, width: float) -> list:
    """A square-cornered notch, open along the fold line."""
    return [
        _FlatLine((0.0, 0.0), (0.0, -depth)),
        _FlatLine((0.0, -depth), (width, -depth)),
        _FlatLine((width, -depth), (width, 0.0)),
    ]


def _bend_obround_profile(depth: float, width: float) -> list:
    """A round-ended notch, open along the fold line."""
    radius = width / 2
    flank = depth - radius
    return [
        _FlatLine((0.0, 0.0), (0.0, -flank)),
        _FlatArc((radius, -flank), radius, pi, 2 * pi),
        _FlatLine((width, -flank), (width, 0.0)),
    ]


def _cut_bend_relief(
    shell: Shell,
    point: Vector,
    away: Vector,
    relief_type: ReliefType,
    values: dict,
    parameters: SheetMetalParameters,
) -> Shell:
    """Notch one end of a fold line, by whichever route the shape needs."""
    frames, probe, step = _bend_end_frames(shell, point, away, parameters)

    if relief_type is ReliefType.ROUND:
        profile = _circle_profile(0.0, 0.0, values["radius"])
    else:
        shape = (
            _bend_square_profile
            if relief_type is ReliefType.SQUARE
            else _bend_obround_profile
        )
        profile = shape(values["depth"], values["width"])

    # a notch is open along the fold line, so it lands on the base alone; a
    # round relief is a hole centred on the end of the line and reaches into
    # the bend as well
    result = _replace_relief_faces(
        shell, _trim_faces(frames, profile, closed=relief_type is ReliefType.ROUND)
    )
    _check_bend_end_relieved(result, probe, step)
    return result


def _check_bend_end_relieved(after: Shell, probe: Vector, step: float) -> None:
    """The relief must take away the material past the end of the fold line.

    That material is the whole point of the cut. A profile placed on the
    wrong side of the bend end never touches it, and one overlapping a notch
    already cut there has edges over empty space, which the split ignores.
    """
    if after.distance_to(probe) < step / 2:
        raise ValueError(
            "the sheet still carries on past the end of the bend - the relief "
            "did not cut it away"
        )


# --------------------------------------------------------------------------
# folding
#
# A fold runs along an edge the sheet already has, between two coplanar faces.
# That edge is what makes the operation unambiguous: naming one of the faces
# beside it says which side of the sheet stays put, with no rule about halves
# or handedness in between. How a flat blank comes to carry such an edge -
# imported with the outline, or marked on a sketch - is a separate question.
#
# The bend takes a strip of the sheet with it as it rolls up, as wide as its
# own arc on the reference surface, so the sheet keeps the length it was drawn
# with. How much blank that turns into is a question for unfold.
# --------------------------------------------------------------------------


def _selected_face(bend_line: Edge) -> Face:
    """The face a bend line was selected through.

    An edge lies between two faces, and the route it was selected by is what
    says which of them was meant: the innermost face of its ``topo_path``,
    whether the edge came off that face or off one of its wires. A route that
    never passed through a face leaves nothing to go on, and the topology
    cannot make up the difference - both faces are equally the edge's own.
    """
    for step in reversed(bend_line.topo_path):
        if isinstance(step, Face):
            return step
    raise ValueError(
        "bend_line was not selected through a face, so which side of it stays "
        "put is unknown - take the edge from the face that stays, as in "
        "sheet.faces()[0].edges()[0]"
    )


def _reachable_faces(shell: Shell, seeds: list, blocked: Face) -> list:
    """Faces reached from ``seeds`` without passing through ``blocked``."""
    found = list(seeds)
    frontier = list(seeds)
    while frontier:
        current = frontier.pop()
        for edge in current.edges():
            for raw in topo_explore_connected_faces(edge, shell):
                if raw is None:
                    continue
                neighbour = Face(raw)
                if neighbour.is_same(blocked):
                    continue
                if any(neighbour.is_same(seen) for seen in found):
                    continue
                found.append(neighbour)
                frontier.append(neighbour)
    return found


def _fold_partner(shell: Shell, face: Face, bend_line: Edge) -> Face:
    """The coplanar face on the other side of a bend line."""
    beside = [
        Face(raw)
        for raw in topo_explore_connected_faces(bend_line, shell)
        if raw is not None
    ]
    beyond = [other for other in beside if not other.is_same(face)]
    if len(beyond) != 1:
        raise ValueError(
            "bend_line must be shared with exactly one other face, and "
            f"{len(beyond)} were found"
        )
    partner = beyond[0]
    if partner.geom_type != GeomType.PLANE:
        raise ValueError("the face across bend_line is already bent, not flat")
    normal, other_normal = (f.normal_at(f.center()) for f in (face, partner))
    if normal.cross(other_normal).length > _RELIEF_TOLERANCE:
        raise ValueError("the face across bend_line is not coplanar with it")
    return partner


def _fold_moving_faces(shell: Shell, face: Face, partner: Face) -> list:
    """Everything that swings with the far side of a bend line."""
    moving = _reachable_faces(shell, [partner], face)
    staying = _reachable_faces(shell, [face], partner)
    if any(near.is_same(far) for near in staying for far in moving):
        raise ValueError(
            "material reaches around the bend line to both sides, so the fold "
            "would tear it rather than carry it"
        )
    return moving


def _fold_pieces(
    face: Face, origin: Vector, across: Vector, beyond: bool
) -> list[Face]:
    """The parts of a planar face on one side of a line through it."""
    plane = Plane(origin=tuple(origin), z_dir=tuple(across))
    piece = face.split(plane, keep=Keep.TOP if beyond else Keep.BOTTOM)
    if piece is None:
        return []
    if isinstance(piece, Face):
        return [piece]
    return [p for p in piece if isinstance(p, Face)]


def _bent_edge(
    flat: Geom2d_Curve, first: float, last: float, surface: Geom_Surface
) -> TopoDS_Edge:
    """An edge on a cylinder from its curve in the cylinder's parameters.

    A segment along one parameter is one of the cylinder's own iso-curves - a
    line along the axis or an arc about it - and is built from that, so the
    bend's fold lines and rims stay exact lines and circles whatever form the
    flat curve arrived in. Any other curve, a slanted end or a hole, gets its
    3D form from the kernel.
    """
    points = [flat.Value(first + (last - first) * step / 4) for step in range(5)]
    iso = None
    if all(abs(pt.X() - points[0].X()) < _RELIEF_TOLERANCE for pt in points):
        # constant angle: a line along the axis
        iso = (
            surface.UIso(points[0].X()),
            Geom2d_Line(gp_Pnt2d(points[0].X(), 0.0), gp_Dir2d(0.0, 1.0)),
            sorted((points[0].Y(), points[-1].Y())),
        )
    elif all(abs(pt.Y() - points[0].Y()) < _RELIEF_TOLERANCE for pt in points):
        # constant height: an arc about the axis
        iso = (
            surface.VIso(points[0].Y()),
            Geom2d_Line(gp_Pnt2d(0.0, points[0].Y()), gp_Dir2d(1.0, 0.0)),
            sorted((points[0].X(), points[-1].X())),
        )
    if iso is not None:
        curve3d, pcurve, (low, high) = iso
        edge = BRepBuilderAPI_MakeEdge(curve3d, low, high).Edge()
        BRep_Builder().UpdateEdge(edge, pcurve, surface, TopLoc_Location(), TOLERANCE)
        return edge
    edge = BRepBuilderAPI_MakeEdge(
        Geom2d_TrimmedCurve(flat, first, last), surface
    ).Edge()
    BRepLib.BuildCurves3d_s(edge)
    return edge


def _face_onto_surface(uv_face: TopoDS_Face, surface: Geom_Surface) -> Face:
    """The face whose outline in ``surface``'s parameters is ``uv_face``.

    The inverse of the development ``unfold`` makes: a planar face drawn in the
    XY plane, holes and all, becomes the face with that outline on the surface.
    Each edge's curve is read in the XY plane's own coordinates - a projection
    that is exact for a curve lying in the plane - and carried over as the
    pcurve on the surface.
    """
    xy_plane = Geom_Plane(gp_Pln())

    def onto(wire: TopoDS_Wire) -> TopoDS_Wire:
        maker = BRepBuilderAPI_MakeWire()
        explorer = BRepTools_WireExplorer(wire)
        while explorer.More():
            edge = explorer.Current()
            first, last = BRep_Tool.Range_s(edge)
            curve3d = BRep_Tool.Curve_s(edge, first, last)
            flat = GeomProjLib.Curve2d_s(curve3d, first, last, xy_plane)
            maker.Add(_bent_edge(flat, first, last, surface))
            explorer.Next()
        return maker.Wire()

    face_maker = BRepBuilderAPI_MakeFace(
        surface, onto(BRepTools.OuterWire_s(uv_face)), True
    )
    for wire in _topods_entities(uv_face, ta.TopAbs_WIRE):
        if not wire.IsSame(BRepTools.OuterWire_s(uv_face)):
            face_maker.Add(onto(TopoDS.Wire(wire)))
    # the parameter map may mirror the outline, and then the holes run the
    # wrong way round for the face MakeFace settled on; the kernel puts that right
    fixer = ShapeFix_Face(face_maker.Face())
    fixer.Perform()
    fixer.FixOrientation()
    return Face(fixer.Face())


def _wrap_strip(
    strip: Face,
    near: Vector,
    across: Vector,
    normal: Vector,
    angle: float,
    surface_radius: float,
    allowance: float,
) -> Face:
    """Roll a flat strip of the blank onto the bend's cylinder, exactly.

    A face on a surface is its outline in the surface's parameters, and a
    planar strip's parameters are flat distances. Rolling it is the affine
    change from those to the cylinder's: distance past the near line becomes
    angle about the axis, at ``angle / allowance`` per unit of blank, and
    distance along the line becomes distance along the axis. So the strip is
    moved into the frame of the roll, scaled, and given the cylinder as its
    surface with its outline kept - the reverse of what ``unfold`` does to a
    bend. Holes, notches, tapers and corner rounds come with it.
    """
    sign = 1.0 if angle > 0 else -1.0
    along = (across.cross(normal) * sign).normalized()  # the cylinder's axis
    spoke = (-normal * sign).normalized()  # from the axis to the near line
    axis_point = near + normal * (surface_radius * sign)
    surface = Geom_CylindricalSurface(
        gp_Ax3(axis_point.to_pnt(), along.to_dir(), spoke.to_dir()), surface_radius
    )
    # the strip in the frame of the roll: x past the near line, y along it
    frame = Plane(origin=near, x_dir=across, z_dir=across.cross(along))
    flat = frame.to_local_coords(strip)
    # distance past the near line becomes angle about the axis
    turn = radians(abs(angle)) / allowance
    to_angle = Matrix(
        [
            [turn, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    in_parameters = BRepBuilderAPI_GTransform(flat.wrapped, to_angle.wrapped, True)
    return _face_onto_surface(TopoDS.Face(in_parameters.Shape()), surface)


def _fold_setback(
    position: BendPosition,
    angle: float,
    radius: float,
    thickness: float,
    allowance: float,
) -> float:
    """How far back from the bend line the bend's near tangent sits."""
    if position is BendPosition.BEND_OUTSIDE:
        return 0.0
    if position is BendPosition.CENTER:
        return allowance / 2
    if abs(angle) >= 180:
        raise ValueError(
            f"{position} places a mould line on the bend line, and the faces "
            "of a 180 degree bend never meet to make one"
        )
    reach = tan(radians(abs(angle)) / 2)
    if position is BendPosition.MATERIAL_INSIDE:
        return radius * reach
    return (radius + thickness) * reach


def _fold(
    shell: Shell,
    face: Face,
    bend_line: Edge,
    angle: float,
    radius: float,
    position: BendPosition,
    parameters: SheetMetalParameters,
) -> Shell:
    """Fold a shell along an edge of one of its planar faces."""
    partner = _fold_partner(shell, face, bend_line)
    moving = _fold_moving_faces(shell, face, partner)

    normal = face.normal_at(face.center())
    origin = Vector(bend_line.position_at(0))
    across = _fold_outward(face, bend_line)

    # The bend face is drawn at the reference surface's radius, but the flat it
    # consumes is the bend allowance, the arc of the neutral fibre
    surface_radius = reference_radius(radius, parameters, angle)
    allowance = bend_allowance(radius, angle, parameters)
    setback = _fold_setback(position, angle, radius, parameters.thickness, allowance)
    near = origin - across * setback
    far = near + across * allowance

    complaint = (
        f"the bend does not fit - it takes {allowance:.4g} of sheet past the bend "
        f"line and {setback:.4g} before it"
    )
    # The legs are what lies before the near line and beyond the far one; the
    # strip between them is what rolls into the bend, with whatever the blank's
    # outline does there - holes, notches, tapers - rolling with it
    starts_on_line = setback < _RELIEF_TOLERANCE
    fixed_legs = [face] if starts_on_line else _fold_pieces(face, near, across, False)
    strip_pieces = (
        [] if starts_on_line else _fold_pieces(face, near, across, True)
    ) + _fold_pieces(partner, far, across, False)
    moving_legs = _fold_pieces(partner, far, across, True)
    if not fixed_legs or not moving_legs or not strip_pieces:
        raise ValueError(complaint)
    strip = (
        strip_pieces[0].fuse(*strip_pieces[1:])
        if len(strip_pieces) > 1
        else strip_pieces[0]
    )
    strips = [strip] if isinstance(strip, Face) else list(strip.faces())

    bend_axis = Axis(
        near + normal * surface_radius * (1 if angle > 0 else -1),
        across.cross(normal),
    )
    spin = Axis((0, 0, 0), bend_axis.direction)
    inside = normal.rotate(spin, angle / 2)
    bend_faces = [
        _orient_face(
            _wrap_strip(piece, near, across, normal, angle, surface_radius, allowance),
            inside,
        )
        for piece in strips
    ]

    def folded(shape):
        """Slide a moving face up to the bend and swing it round."""
        return shape.translate(-across * allowance).rotate(bend_axis, angle)

    faces = fixed_legs + bend_faces + [folded(leg) for leg in moving_legs]
    for other in shell.faces():
        if other.is_same(face) or other.is_same(partner):
            continue
        faces.append(folded(other) if any(other.is_same(m) for m in moving) else other)
    return BuildSheet._validated_shell(faces)
