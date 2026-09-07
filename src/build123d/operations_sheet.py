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
from math import acos, asin, atan, cos, degrees, pi, radians, sin, sqrt, tan
from typing import Literal, overload

import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.BRepFeat import BRepFeat_SplitShape
from OCP.BRepLib import BRepLib
from OCP.BRep import BRep_Tool
from OCP.Geom2d import Geom2d_Circle, Geom2d_Ellipse, Geom2d_Line
from OCP.Geom2dAPI import Geom2dAPI_ProjectPointOnCurve
from OCP.gp import gp_Ax22d, gp_Dir2d, gp_Pnt, gp_Pnt2d
from OCP.ShapeAnalysis import ShapeAnalysis_Surface
import OCP.TopAbs as ta
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

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
from build123d.geometry import Axis, Location, Plane, Vector
from build123d.sheet_utils import (
    MIN_BEND_RADIUS,
    SheetMetalParameters,
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
    part on it.

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
) -> Shell:
    """Angle the sides of planar flanges while leaving their bends unchanged.

    Each selected vertex must be an endpoint of a free flange rim. A positive
    angle trims the rim toward its other endpoint; a negative angle extends it.
    The angle is measured from the side perpendicular to the rim.

    Args:
        vertices: Free flange-rim endpoint or endpoints.
        angle: Signed miter angle in degrees. Must be strictly between -90 and
            90 degrees.

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

    target = _miter_target(context, vertex_list)
    selections = [(_miter_support(vertex, target), vertex) for vertex in vertex_list]
    face_selections: dict[Face, list[tuple[Edge, Edge, Edge, Vertex]]] = {}
    for (face, rim, fold, side), vertex in selections:
        face_selections.setdefault(face, []).append((rim, fold, side, vertex))

    replacements: dict[Face, dict[Vertex, Vector]] = {}
    for face, face_items in face_selections.items():
        replacements[face] = {}
        for rim, fold, side, vertex in face_items:
            other_rim_vertex = _other_vertex(rim, vertex)
            bend_vertex = _other_vertex(side, vertex)
            inward = (Vector(other_rim_vertex) - Vector(vertex)).normalized()
            rim_projection = Vector(vertex) + inward * (
                (Vector(bend_vertex) - Vector(vertex)).dot(inward)
            )
            flange_length = (Vector(bend_vertex) - rim_projection).length
            replacements[face][vertex] = rim_projection + inward * flange_length * tan(
                radians(angle)
            )

    new_faces: list[Face] = []
    for face in target.faces():
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
        new_face = Face(Wire.make_polygon(points), face.inner_wires())
        new_faces.append(_orient_face(new_face, face.normal_at(face.center())))

    result = BuildSheet._validated_shell(new_faces)
    if context is not None:
        context._add_to_context(*new_faces, mode=Mode.REPLACE)
        return context.sheet_local
    return result


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
) -> Shell: ...


@overload
def corner_relief(
    vertices: Vertex | list[Vertex] | None,
    relief_type: Literal[ReliefType.SQUARE],
    *,
    size: float,
) -> Shell: ...


@overload
def corner_relief(
    vertices: Vertex | list[Vertex] | None,
    relief_type: Literal[ReliefType.OBROUND],
    *,
    length: float,
    width: float,
) -> Shell: ...


@overload
def corner_relief(
    vertices: Vertex | list[Vertex] | None,
    relief_type: Literal[ReliefType.CONSTANT_WIDTH],
    *,
    depth: float,
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
        target = _cut_corner_relief(target, vertex, relief_type, profile, reach)

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
        cutter = _constant_width_cutter(shell, base, corner, depth)
        cut = shell.cut(cutter)
        result = cut if isinstance(cut, Shell) else Shell(cut.faces())
    elif profile is not None:
        frames = _corner_frames(shell, base, corner)
        result = _replace_relief_faces(shell, _trim_corner(frames, profile))
        _check_removed_area(shell, result, profile, _corner_empty_regions(frames))
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
        sheet_parameters: Material and reference-surface parameters. Needed in
            Algebra mode only when a size is left to default.

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

    parameters = (
        _resolve_sheet_parameters(context, sheet_parameters)
        if context is not None or sheet_parameters is not None
        else None
    )
    if parameters is None and any(supplied[name] is None for name in required):
        raise ValueError(
            "sheet_parameters is required in Algebra mode to size the relief"
        )

    target = _owning_shell(context, bend_list, "bend_relief faces")
    # every end is measured on the shell as given, before any of the cuts move
    # the faces around
    plans = []
    footprints = []
    values: dict[str, float]
    for cylinder in bend_list:
        for point, away, outward, bend_radius in _bend_ends(cylinder, target):
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
            footprints.append(
                _relief_footprint(point, away, outward, relief_type, values)
            )
    _check_reliefs_apart(footprints)

    for point, away, values in plans:
        target = _cut_bend_relief(target, point, away, relief_type, values)

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
# other. The base occupies the negative quadrant, each bend unrolls into its
# own, and the quadrant past both bends holds no material.
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

    def sub(self, first: float, last: float) -> "_FlatLine":
        """The part of this segment between two fractions."""
        return _FlatLine(self.point_at(first), self.point_at(last))

    def crossings(self, value: float, axis: int = 1) -> list[float]:
        """Fractions strictly inside the segment where coordinate == value."""
        first, last = self.start[axis], self.end[axis]
        if abs(last - first) < _RELIEF_TOLERANCE:
            return []
        fraction = (value - first) / (last - first)
        return (
            [fraction] if _RELIEF_TOLERANCE < fraction < 1 - _RELIEF_TOLERANCE else []
        )


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

    def sub(self, first: float, last: float) -> "_FlatArc":
        """The part of this arc between two fractions."""
        sweep = self.end_angle - self.start_angle
        return _FlatArc(
            self.center,
            self.radius,
            self.start_angle + first * sweep,
            self.start_angle + last * sweep,
        )

    def crossings(self, value: float, axis: int = 1) -> list[float]:
        """Fractions strictly inside the arc where coordinate == value."""
        offset = (value - self.center[axis]) / self.radius
        if abs(offset) > 1.0:
            return []
        clamped = max(-1.0, min(1.0, offset))
        # y = cy + r sin(t) and x = cx + r cos(t), so each axis has its own
        # pair of solutions
        base = asin(clamped) if axis == 1 else acos(clamped)
        partner = (pi - base) if axis == 1 else -base
        sweep = self.end_angle - self.start_angle
        found = []
        for angle in (base, partner):
            # every turn of the circle offers the same two solutions
            for turn in range(-2, 3):
                fraction = (angle + 2 * pi * turn - self.start_angle) / sweep
                if _RELIEF_TOLERANCE < fraction < 1 - _RELIEF_TOLERANCE:
                    found.append(fraction)
        return sorted(found)


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

    ``to_3d`` is supplied per surface type; everything else is derived from it
    by sampling, because the composed map is affine for both planar and
    cylindrical faces and an affine map is fixed by three points.
    """

    face: Face
    matrix: np.ndarray  # 2x2, flat -> uv
    offset: np.ndarray  # uv of flat (0, 0)
    gap: float = 0.0  # how far along its fold line this face starts

    def to_uv(self, x: float, y: float) -> gp_Pnt2d:
        """Flat-pattern point as a parameter-space point on this face."""
        u, v = self.matrix @ np.array([x, y]) + self.offset
        return gp_Pnt2d(u, v)

    def to_flat(self, point: gp_Pnt2d) -> np.ndarray:
        """Parameter-space point back in flat-pattern coordinates."""
        uv = np.array([point.X(), point.Y()]) - self.offset
        return np.linalg.solve(self.matrix, uv)

    @property
    def surface(self):
        """The face's underlying geometric surface."""
        return BRep_Tool.Surface_s(self.face.wrapped)

    def segment(self, seg) -> tuple:
        """A flat segment's exact image in this face's UV domain.

        Returns ``(curve2d, first, last, flipped)``. The affine development
        maps a line to a line and a circle to a conic, so no segment is
        approximated. ``flipped`` says the UV span runs against the segment's
        own direction, which happens when the development mirrors the face;
        the edge built from it must be reversed to keep a chain consistent.
        """
        if isinstance(seg, _FlatLine):
            start, end = self.to_uv(*seg.start), self.to_uv(*seg.end)
            direction = np.array([end.X() - start.X(), end.Y() - start.Y()])
            length = float(np.hypot(*direction))
            curve = Geom2d_Line(start, gp_Dir2d(*direction))
            return curve, 0.0, length, False

        curve = self.circle(seg.center[0], seg.center[1], seg.radius)
        first = _parameter_at(curve, self.to_uv(*seg.start))
        last = _parameter_at(curve, self.to_uv(*seg.end))
        # A mirroring development reverses the parameter sense, so the span
        # from first to last may be the complementary arc.
        middle = _parameter_at(curve, self.to_uv(*seg.point_at(0.5)))
        flipped = not _between(middle, first, last, curve)
        if flipped:
            first, last = last, first
        return curve, first, last, flipped

    def circle(self, cx: float, cy: float, radius: float):
        """The flat circle's exact image in this face's UV domain.

        A rigid development (a planar face) leaves a circle a circle; a
        cylindrical development scales one axis by 1/bend radius, which turns
        it into an ellipse.
        """
        center = self.to_uv(cx, cy)
        # singular values of the affine part give the conic's semi-axes
        left, scales, _ = np.linalg.svd(self.matrix)
        major, minor = radius * scales[0], radius * scales[1]
        if abs(major - minor) < _RELIEF_TOLERANCE:
            return Geom2d_Circle(
                gp_Ax22d(center, gp_Dir2d(left[0, 0], left[1, 0]), True), major
            )
        return Geom2d_Ellipse(
            gp_Ax22d(
                center,
                gp_Dir2d(left[0, 0], left[1, 0]),
                gp_Dir2d(left[0, 1], left[1, 1]),
            ),
            major,
            minor,
        )


def _frame_from_samples(face: Face, to_3d, gap: float = 0.0) -> _FlatFrame:
    """Fit the flat -> UV affine map by sampling three flat points."""
    inverter = ShapeAnalysis_Surface(BRep_Tool.Surface_s(face.wrapped))

    def uv_of(x: float, y: float) -> np.ndarray:
        point = inverter.ValueOfUV(to_3d(x, y), _RELIEF_TOLERANCE)
        return np.array([point.X(), point.Y()])

    origin = uv_of(0.0, 0.0)
    matrix = np.column_stack([uv_of(1.0, 0.0) - origin, uv_of(0.0, 1.0) - origin])
    return _FlatFrame(face=face, matrix=matrix, offset=origin, gap=gap)


def _bend_axis(
    cylinder: Face,
    tangent_start: Vector,
    along: Vector,
    plane_normal: Vector,
    sample: Vector | None = None,
):
    """The axis a bend curls about, and which way it turns.

    ``tangent_start`` fixes the axis and may be anywhere on the fold line -
    including the corner, which a flange gap leaves off the bend itself.
    ``sample`` must lie within the bend's own extent, since the turn direction
    is found by swinging it and asking whether it stays on the face.
    """
    radius = cylinder.radius
    if radius is None:
        raise ValueError("relief expects a cylindrical bend face")

    def off_axis(origin: Vector) -> float:
        # perpendicular distance only: the straight point-to-point distance
        # also carries the offset along the axis, which swamps the comparison
        spoke = cylinder.center() - origin
        return (spoke - along * spoke.dot(along)).length

    candidates = [
        tangent_start + plane_normal * radius,
        tangent_start - plane_normal * radius,
    ]
    origin = min(candidates, key=lambda o: abs(off_axis(o) - radius))
    axis = Axis(origin, along)
    probe = tangent_start if sample is None else sample
    return axis, _bend_sign(cylinder, axis, probe), radius


def _corner_frames(shell: Shell, base: Face, corner: Vector) -> dict:
    """Flat frames for the faces meeting at one corner of a planar face.

    All three share one flat coordinate system with its origin at ``corner``:
    ``x`` measures past the tangent line of one bend and ``y`` past the other,
    so the base sits in the negative quadrant and each bend unrolls into its
    own. The quadrant past both bends holds no material.

    Returns ``{(sign_x, sign_y): _FlatFrame}``.
    """
    plane_normal = base.normal_at(base.center())

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

    # each bend unrolls perpendicular to its own tangent line, away from the base
    unroll = {}
    for edge, cylinder in touching:
        along = (Vector(edge.position_at(1)) - Vector(edge.position_at(0))).normalized()
        outward = along.cross(plane_normal).normalized()
        if (base.center() - corner).dot(outward) > 0:
            outward = -outward
        unroll[cylinder] = (edge, along, outward)

    # x unrolls the first bend, y the second
    ordered = list(unroll)
    axis_dir = [unroll[cylinder][2] for cylinder in ordered]

    def base_to_3d(x: float, y: float) -> gp_Pnt:
        return gp_Pnt(*tuple(corner + axis_dir[0] * x + axis_dir[1] * y))

    frames = {(-1, -1): _frame_from_samples(base, base_to_3d)}

    for index, cylinder in enumerate(ordered):
        edge, along, outward = unroll[cylinder]
        # the fold edge lies within the bend even when a gap keeps the corner
        # outside it, so swing from there to find the turn direction
        bend_axis, sign, radius = _bend_axis(
            cylinder, corner, along, plane_normal, Vector(edge.position_at(0.5))
        )
        other = 1 - index

        def to_3d(
            x: float, y: float, _i=index, _o=other, _a=bend_axis, _s=sign, _r=radius
        ):
            past = (x, y)[_i]  # distance unrolled past this bend's tangent
            slide = (x, y)[_o]  # distance along the tangent line
            seed = corner + axis_dir[_o] * slide
            return gp_Pnt(*tuple(_rotate_about(seed, _a, _s * past / _r * 180 / pi)))

        # a flange gap holds the bend back from the corner; the nearer end of
        # its fold edge says by how much
        gap = min((Vector(edge.position_at(end)) - corner).length for end in (0.0, 1.0))
        quadrant = (1, -1) if index == 0 else (-1, 1)
        frames[quadrant] = _frame_from_samples(cylinder, to_3d, gap)

    return frames


def _rotate_about(point: Vector, axis: Axis, angle: float) -> Vector:
    """Rotate a point about an axis line.

    ``Vector.rotate`` uses only the axis *direction* - it swings the vector
    about a parallel line through the origin - so the point has to be brought
    to the axis first and put back afterwards.
    """
    return axis.position + (point - axis.position).rotate(axis, angle)


def _bend_sign(cylinder: Face, axis: Axis, start: Vector) -> float:
    """Which way around the axis the bend material actually lies."""
    for sign in (1.0, -1.0):
        if cylinder.distance_to(_rotate_about(start, axis, sign * 5.0)) < 1e-6:
            return sign
    raise ValueError("unable to determine bend direction")


# --------------------------------------------------------------------------
# trimming
# --------------------------------------------------------------------------


def _edge_from_pcurve(curve2d, first=None, last=None, *, surface):
    """Build an edge carrying only a pcurve, then give it a 3D curve."""
    if first is not None:
        maker = BRepBuilderAPI_MakeEdge(curve2d, surface, first, last)
    else:
        maker = BRepBuilderAPI_MakeEdge(curve2d, surface)
    edge = maker.Edge()
    BRepLib.BuildCurves3d_s(edge)
    return edge


def _profile_edges(frame: _FlatFrame, profile: list) -> list:
    """Map every segment of a flat profile onto one face as a pcurve edge.

    Every edge is oriented to follow the profile's own direction, so segments
    of different kinds join even where the development mirrors the face.
    """
    edges = []
    for seg in profile:
        curve, first, last, flipped = frame.segment(seg)
        edge = _edge_from_pcurve(curve, first, last, surface=frame.surface)
        edges.append(TopoDS.Edge(edge.Reversed()) if flipped else edge)
    return edges


def _parameter_at(curve2d, point: gp_Pnt2d) -> float:
    """Parameter on a UV curve nearest a UV point."""
    projector = Geom2dAPI_ProjectPointOnCurve(point, curve2d)
    return projector.LowerDistanceParameter()


def _split_face(face: Face, edges) -> Face:
    """Split a face with a chain of edges on it and keep the larger piece.

    The chain runs from boundary to boundary, so it divides the face without
    needing to be closed. BRepFeat_SplitShape returns a TopoDS_Shell holding
    the pieces rather than a face, so they are collected with an explorer.
    """
    chain = edges if isinstance(edges, list) else [edges]
    splitter = BRepFeat_SplitShape(face.wrapped)
    if len(chain) == 1:
        splitter.Add(chain[0], face.wrapped)
    else:
        # separate edges carry independent vertices; the splitter needs them
        # connected, so hand it a wire that shares them
        maker = BRepBuilderAPI_MakeWire()
        for member in chain:
            maker.Add(member)
        if not maker.IsDone():
            raise ValueError("profile run does not form a connected chain")
        wire = maker.Wire()
        BRepLib.BuildCurves3d_s(wire)
        splitter.Add(wire, face.wrapped)
    splitter.Build()
    if not splitter.IsDone() or splitter.Shape().IsNull():
        raise ValueError("unable to split face")

    pieces = []
    explorer = TopExp_Explorer(splitter.Shape(), ta.TopAbs_FACE)
    while explorer.More():
        pieces.append(Face(TopoDS.Face(explorer.Current())))
        explorer.Next()
    if len(pieces) != 2:
        raise ValueError(f"split produced {len(pieces)} face(s), expected 2")
    return max(pieces, key=lambda f: f.area)


def _gap_limits(frames: dict | None) -> dict:
    """How far short of the corner each bend starts, as a signed limit.

    A flange gap holds a bend back from the corner, leaving an empty strip
    between the fold line and where the bend actually begins. A bend's own gap
    measures along the axis it does *not* unroll into, so the strip it leaves
    is bounded on that axis. Returns ``{axis: limit}``, zero where there is no
    gap.
    """
    limits = {0: 0.0, 1: 0.0}
    for quadrant, frame in (frames or {}).items():
        if frame.gap > _RELIEF_TOLERANCE:
            limits[0 if quadrant[1] > 0 else 1] = -frame.gap
    return limits


def _split_profile_quadrants(profile: list, frames: dict | None = None) -> dict:
    """Divide a closed flat profile into runs, one per face it crosses.

    The two fold lines are the axes, so the base occupies the negative
    quadrant and each bend unrolls into its own. A flange gap holds a bend
    back from the corner, which puts an empty strip between the fold line and
    where the bend actually starts, so the profile is cut at those limits too
    and the runs over the strips are dropped - they have nothing to cut.

    Returns ``{(sign_x, sign_y): [segments]}``, keyed by the quadrant naming
    the face each run lands on. ``None`` keys a run over empty space.
    """
    limits = _gap_limits(frames)

    def where(point) -> tuple | None:
        """The quadrant naming the face under a point, or None for empty space."""
        across = (1 if point[0] > 0 else -1, 1 if point[1] > 0 else -1)
        if across == (1, 1):
            return None  # past both fold lines: no material
        if across == (1, -1) and point[1] > limits[1]:
            return None  # inside the gap that holds this bend back
        if across == (-1, 1) and point[0] > limits[0]:
            return None
        return across

    return _split_profile(profile, {0: (0.0, limits[0]), 1: (0.0, limits[1])}, where)


def _split_profile(profile: list, cuts: dict, where) -> dict:
    """Divide a closed flat profile into runs, one per region it crosses.

    ``cuts`` gives the coordinate values to break segments at, per axis, and
    ``where`` names the region a point falls in - or None where there is no
    material to cut. Consecutive pieces of one region are joined back up, so
    breaking at a line a region happens to span costs nothing.
    """
    divided = []
    for seg in profile:
        fractions = {0.0, 1.0}
        for axis, offsets in cuts.items():
            for offset in offsets:
                fractions.update(seg.crossings(offset, axis=axis))
        ordered = sorted(fractions)
        for first, last in zip(ordered, ordered[1:]):
            piece = seg.sub(first, last)
            divided.append((where(piece.point_at(0.5)), piece))

    runs: list = []
    for region, piece in divided:
        if runs and runs[-1][0] == region:
            runs[-1][1].append(piece)
        else:
            runs.append((region, [piece]))
    # the profile is closed, so a run split across the seam is one run
    if len(runs) > 1 and runs[0][0] == runs[-1][0]:
        runs[0][1][:0] = runs.pop()[1]

    grouped: dict = {}
    for region, chain in runs:
        if region is None:
            continue  # nothing to cut there
        if region in grouped:
            raise ValueError(f"profile visits region {region} more than once")
        grouped[region] = chain
    return grouped


# --------------------------------------------------------------------------
# guards
# --------------------------------------------------------------------------


def _flat_to_3d(frame: _FlatFrame, x: float, y: float) -> Vector:
    """A flat-pattern point as a 3D point on the frame's face."""
    uv = frame.to_uv(x, y)
    return Vector(frame.surface.Value(uv.X(), uv.Y()))


def _check_corner_detached(before: Shell, after: Shell, corner: Vector) -> None:
    """A corner relief must remove the corner.

    This is the guard that distinguishes a relief which opens the corner from
    one that merely nibbles at it. A profile closed *at* the corner still cuts
    faithfully - it reaches the boundary at both ends and removes exactly the
    area it covers - but both ends land on the same tangent line, so it takes
    a lens off an edge and leaves the corner vertex in place. Neither of the
    other two checks notices; this one does.
    """
    if any((Vector(v) - corner).length < _RELIEF_TOLERANCE for v in after.vertices()):
        raise ValueError(
            "the corner vertex survived the relief - the profile closes at or "
            "before the corner instead of opening through it"
        )
    if before.area - after.area <= _RELIEF_TOLERANCE:
        raise ValueError("the relief removed nothing")


def _check_run_reaches_boundary(
    frame: _FlatFrame, chain: list, tolerance: float = 1e-6
) -> None:
    """A run must enter and leave the face through its boundary.

    Catches a run that peters out inside a face. Note it does *not* catch a
    run whose two ends land on the same boundary edge - see
    ``_check_corner_detached``.
    """
    ends = {"start": chain[0].start, "end": chain[-1].end}
    for which, flat_point in ends.items():
        point = _flat_to_3d(frame, *flat_point)
        gap = min(edge.distance_to(point) for edge in frame.face.edges())
        if gap <= tolerance:
            continue
        kind = frame.face.geom_type.name.lower()
        if frame.face.distance_to(point) > tolerance:
            raise ValueError(
                f"run {which} runs {gap:.3g} off the {kind} face - the relief "
                "is bigger than the material around it"
            )
        raise ValueError(
            f"run {which} sits {gap:.3g} inside the {kind} face rather than "
            "on its boundary - the relief does not cut through"
        )


def _profile_area_on_material(profile: list, empty: list, samples: int = 2000) -> float:
    """Area of a profile that lies over material.

    Computed straight from the flat profile with no reference to the shell, so
    it is an independent expectation for what a trim should remove. ``empty``
    names the parts of the flat pattern holding no material, each an
    intersection of half planes.
    """
    points = [
        seg.point_at(index / samples) for seg in profile for index in range(samples)
    ]
    # a closed profile repeats its first point here, an open one is completed
    points.append(profile[-1].point_at(1.0))

    def shoelace(polygon) -> float:
        if len(polygon) < 3:
            return 0.0
        total = sum(
            polygon[i][0] * polygon[(i + 1) % len(polygon)][1]
            - polygon[(i + 1) % len(polygon)][0] * polygon[i][1]
            for i in range(len(polygon))
        )
        return abs(total) / 2

    def clip(polygon, axis: int, sign: int, offset: float = 0.0):
        """Keep the part of the polygon on one side of a line."""
        kept = []
        for index, here in enumerate(polygon):
            following = polygon[(index + 1) % len(polygon)]
            here_side = (here[axis] - offset) * sign
            next_side = (following[axis] - offset) * sign
            if here_side >= 0:
                kept.append(here)
            if (here_side >= 0) != (next_side >= 0):
                span = following[axis] - here[axis]
                fraction = (offset - here[axis]) / span
                kept.append(
                    (
                        here[0] + fraction * (following[0] - here[0]),
                        here[1] + fraction * (following[1] - here[1]),
                    )
                )
        return kept

    total = shoelace(points)
    for region in empty:
        piece = points
        for axis, sign, offset in region:
            piece = clip(piece, axis, sign, offset)
        total -= shoelace(piece)
    return total


def _corner_empty_regions(frames: dict) -> list:
    """The parts of a corner's flat pattern that hold no material.

    Nothing lies past both fold lines, and a flange gap leaves a strip empty
    between a fold line and where its bend actually starts.
    """
    limits = _gap_limits(frames)
    return [
        ((0, 1, 0.0), (1, 1, 0.0)),  # past both fold lines
        ((0, 1, 0.0), (1, 1, limits[1]), (1, -1, 0.0)),  # one bend's gap strip
        ((1, 1, 0.0), (0, 1, limits[0]), (0, -1, 0.0)),  # the other's
    ]


def _check_removed_area(
    before: Shell, after: Shell, profile: list, empty: list, tolerance: float = 1e-4
) -> None:
    """The trim must remove exactly the profile's area that sat on material.

    Catches a split that fails to follow the profile. It cannot catch a
    profile that is itself the wrong shape, since the cut then matches it
    exactly - see ``_check_corner_detached``.
    """
    removed = before.area - after.area
    expected = _profile_area_on_material(profile, empty)
    if abs(removed - expected) > tolerance:
        raise ValueError(
            f"relief removed {removed:.6f} but the profile covers "
            f"{expected:.6f} of material - the cut is incomplete"
        )


def _trim_corner(frames: dict, profile: list) -> dict:
    """Cut a corner relief spanning the faces that meet at a corner.

    ``frames`` maps each quadrant to the _FlatFrame of the face occupying it.
    Every run of the profile that lands on a face cuts that face's corner off;
    a run over the empty quadrant has nothing to cut and is ignored.
    """
    runs = _split_profile_quadrants(profile, frames)
    missing = set(runs) - set(frames)
    if len(missing) > 1:
        raise ValueError(f"profile covers unbacked quadrants {sorted(missing)}")
    # the quadrant past both bends holds no material
    return _trim_runs(frames, {q: c for q, c in runs.items() if q in frames})


def _trim_runs(frames: dict, runs: dict) -> dict:
    """Cut each run of a profile into the face it lands on.

    Returns ``{original face: trimmed face}``, ready to be swapped into the
    shell.
    """
    trimmed = {}
    for region, chain in runs.items():
        frame = frames[region]
        _check_run_reaches_boundary(frame, chain)
        trimmed[frame.face] = _split_face(frame.face, _profile_edges(frame, chain))
    return trimmed


def _between(value: float, first: float, last: float, curve) -> bool:
    """Is a parameter inside the periodic span from first to last?"""
    period = curve.Period() if curve.IsPeriodic() else None
    if period is None:
        return min(first, last) <= value <= max(first, last)
    span = (last - first) % period
    return ((value - first) % period) <= span


def _replace_relief_faces(shell: Shell, replacements: dict[Face, Face]) -> Shell:
    """Rebuild a shell with some faces swapped, then re-sew."""
    faces = []
    for face in shell.faces():
        match = next((v for k, v in replacements.items() if k.is_same(face)), None)
        faces.append(match if match is not None else face)
    return Shell(faces)


# --------------------------------------------------------------------------
# demonstration
# --------------------------------------------------------------------------


def _corner_mirror_plane(shell: Shell, base: Face, corner: Vector):
    """The plane that bisects a corner, as (origin, unit normal).

    Its normal is the bisector of the two tangent directions, so the two
    flanges sit symmetrically either side of it.
    """
    frames = _corner_frames(shell, base, corner)
    # the two unroll directions are the frames' flat axes; their difference
    # bisects the corner
    first = _flat_to_3d(frames[(-1, -1)], 1.0, 0.0) - corner
    second = _flat_to_3d(frames[(-1, -1)], 0.0, 1.0) - corner
    normal = (first.normalized() - second.normalized()).normalized()
    return corner, normal


def _corner_faces(shell: Shell, base: Face, corner: Vector) -> list:
    """The bends meeting at a corner and the walls they carry."""
    frames = _corner_frames(shell, base, corner)
    faces = [frames[quadrant].face for quadrant in ((-1, 1), (1, -1))]
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


def _flange_separation(shell: Shell, base: Face, corner: Vector) -> float:
    """The gap the two flanges leave at a corner, measured from the sheet.

    A constant width relief has to continue this gap, so its width is a
    property of the part rather than something a user should have to work out.
    Only meaningful when the two flange edges are parallel; anything else has
    no single separation to continue and is rejected.
    """
    # each bend carries a wall; that wall's free edge nearest the corner is
    # what bounds the gap
    walls = [
        f for f in _corner_faces(shell, base, corner) if f.geom_type.name == "PLANE"
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


def _constant_width_cutter(
    shell: Shell, base: Face, corner: Vector, depth: float
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
    width = _flange_separation(shell, base, corner)
    _, normal = _corner_mirror_plane(shell, base, corner)
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
        for face in _corner_faces(shell, base, corner)
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
    name: str, bend_radius: float, parameters: SheetMetalParameters | None
) -> float:
    """The conventional relief size, measured from the fold line."""
    assert parameters is not None  # the caller checks before asking
    if name in ("width", "radius"):
        # a hole is bounded by the sheet left past the bend end, which is
        # often only the gap the flange leaves, so it does not follow depth
        return parameters.thickness
    return bend_radius + parameters.thickness


def _fold_outward(face: Face, point: Vector, along: Vector) -> Vector:
    """The direction across a fold line that points away from a planar face."""
    outward = along.cross(face.normal_at(face.center())).normalized()
    return -outward if (face.center() - point).dot(outward) > 0 else outward


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

    Returns ``(point, away, outward, radius)`` per end: ``away`` points along
    the fold line out of the bend and ``outward`` across it, away from the face
    being relieved. An end that runs to the edge of the blank needs no relief
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
            outward = _fold_outward(plane, point, direction)
            probe = _bend_end_probe(point, direction, outward, step)
            if plane.distance_to(probe) < step / 2:
                found.append((point, outward))
        if len(found) > 1:
            raise ValueError(
                "this bend ends with material on both sides of the fold line, "
                "which needs the sheet ripped rather than notched"
            )
        if found:
            ends.append((found[0][0], direction, found[0][1], radius))
    return ends


def _relief_footprint(
    point: Vector,
    away: Vector,
    outward: Vector,
    relief_type: ReliefType,
    values: dict,
) -> tuple:
    """The patch of sheet a relief takes out, as ``(corners, axes)``.

    Every relief shape is convex, so the rectangle enclosing it is enough to
    tell two of them apart.
    """
    if relief_type is ReliefType.ROUND:
        radius = values["radius"]
        spans = ((-radius, radius), (-radius, radius))
    else:
        spans = ((0.0, values["width"]), (-values["depth"], 0.0))
    corners = [point + away * x + outward * y for x in spans[0] for y in spans[1]]
    return corners, (away, outward)


def _footprints_overlap(first: tuple, second: tuple) -> bool:
    """Do two relief footprints cover any of the same sheet?"""
    corners, axes = first
    others, other_axes = second
    normal = axes[0].cross(axes[1]).normalized()
    if any(
        abs((corner - corners[0]).dot(normal)) > _RELIEF_TOLERANCE for corner in others
    ):
        return False  # not even in the same plane
    for axis in (*axes, *other_axes):
        here = [corner.dot(axis) for corner in corners]
        there = [corner.dot(axis) for corner in others]
        if min(here) >= max(there) - _RELIEF_TOLERANCE:
            return False
        if min(there) >= max(here) - _RELIEF_TOLERANCE:
            return False
    return True


def _check_reliefs_apart(footprints: list) -> None:
    """Two reliefs cutting the same sheet cannot both be measured.

    Bend ends close enough for that are the two sides of one corner, and
    ``corner_relief`` opens a corner in a single cut.
    """
    for index, first in enumerate(footprints):
        for second in footprints[index + 1 :]:
            if _footprints_overlap(first, second):
                raise ValueError(
                    "these bends end close enough that their reliefs overlap - "
                    "they meet at a corner, which corner_relief opens in one cut"
                )


def _bend_end_frames(shell: Shell, point: Vector, away: Vector) -> tuple:
    """Flat frames for the two faces meeting at the end of a fold line.

    Both share one flat coordinate system with its origin on that end: ``x``
    runs along the line away from the bend and ``y`` past the line into the
    bend. Returns ``({"base": frame, "bend": frame}, probe, step)``.
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
    normal = base.normal_at(base.center())
    outward = _fold_outward(base, point, away)
    axis, sign, radius = _bend_axis(
        cylinder, point, away, normal, Vector(edge.position_at(0.5))
    )

    def base_to_3d(x: float, y: float) -> gp_Pnt:
        return gp_Pnt(*tuple(point + away * x + outward * y))

    def bend_to_3d(x: float, y: float) -> gp_Pnt:
        seed = point + away * x
        return gp_Pnt(*tuple(_rotate_about(seed, axis, sign * degrees(y / radius))))

    frames = {
        "base": _frame_from_samples(base, base_to_3d),
        "bend": _frame_from_samples(cylinder, bend_to_3d),
    }
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


def _split_profile_bend_end(profile: list) -> dict:
    """Divide a flat profile into the runs landing on each face at a bend end."""

    def where(point) -> str | None:
        if point[1] < 0:
            return "base"
        return "bend" if point[0] < 0 else None

    return _split_profile(profile, {0: (0.0,), 1: (0.0,)}, where)


def _cut_bend_relief(
    shell: Shell,
    point: Vector,
    away: Vector,
    relief_type: ReliefType,
    values: dict,
) -> Shell:
    """Notch one end of a fold line, by whichever route the shape needs."""
    frames, probe, step = _bend_end_frames(shell, point, away)

    if relief_type is ReliefType.ROUND:
        profile = _circle_profile(0.0, 0.0, values["radius"])
        runs = _split_profile_bend_end(profile)
        empty = [((0, 1, 0.0), (1, 1, 0.0))]  # past the end and past the line
    else:
        shape = (
            _bend_square_profile
            if relief_type is ReliefType.SQUARE
            else _bend_obround_profile
        )
        profile = shape(values["depth"], values["width"])
        # the notch is open along the fold line, so it is one run on one face
        runs = {"base": profile}
        empty = []

    result = _replace_relief_faces(shell, _trim_runs(frames, runs))
    _check_removed_area(shell, result, profile, empty)
    _check_bend_end_relieved(result, probe, step)
    return result


def _check_bend_end_relieved(after: Shell, probe: Vector, step: float) -> None:
    """The relief must take away the material past the end of the fold line.

    That material is the whole point of the cut, and a profile placed on the
    wrong side of the bend end removes its own area faithfully without ever
    touching it.
    """
    if after.distance_to(probe) < step / 2:
        raise ValueError(
            "the sheet still carries on past the end of the bend - the relief "
            "is on the wrong side of it"
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


def _fold_half(
    face: Face, origin: Vector, across: Vector, beyond: bool, complaint: str
) -> Face:
    """The part of a planar face on one side of a line through it."""
    plane = Plane(origin=tuple(origin), z_dir=tuple(across))
    piece = face.split(plane, keep=Keep.TOP if beyond else Keep.BOTTOM)
    if piece is None:
        faces: list[Face] = []
    elif isinstance(piece, Face):
        faces = [piece]
    else:
        faces = list(piece)
    if len(faces) != 1:
        raise ValueError(complaint)
    return faces[0]


def _fold_setback(
    position: BendPosition, angle: float, radius: float, thickness: float, arc: float
) -> float:
    """How far back from the bend line the bend's near tangent sits."""
    if position is BendPosition.BEND_OUTSIDE:
        return 0.0
    if position is BendPosition.CENTER:
        return arc / 2
    if abs(angle) >= 180:
        raise ValueError(
            f"{position} places a mould line on the bend line, and the faces "
            "of a 180 degree bend never meet to make one"
        )
    reach = tan(radians(abs(angle)) / 2)
    if position is BendPosition.MATERIAL_INSIDE:
        return radius * reach
    return (radius + thickness) * reach


def _tangent_edge(leg: Face, origin: Vector, across: Vector) -> Edge:
    """The straight edge of a leg lying on the line the bend starts from."""
    on_line = [
        edge
        for edge in leg.edges()
        if edge.geom_type == GeomType.LINE
        and all(
            abs((Vector(edge.position_at(end)) - origin).dot(across))
            < _RELIEF_TOLERANCE
            for end in (0.0, 1.0)
        )
    ]
    if len(on_line) != 1:
        raise ValueError(f"the bend meets the face along {len(on_line)} edges")
    return on_line[0]


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
    along = (Vector(bend_line.position_at(1)) - origin).normalized()
    across = _fold_outward(face, origin, along)

    surface_radius = reference_radius(radius, parameters, angle)
    arc = radians(abs(angle)) * surface_radius
    setback = _fold_setback(position, angle, radius, parameters.thickness, arc)
    near = origin - across * setback
    far = near + across * arc

    complaint = (
        f"the bend does not fit - it takes {arc:.4g} of sheet past the bend "
        f"line and {setback:.4g} before it"
    )
    fixed_leg = (
        face
        if setback < _RELIEF_TOLERANCE
        else _fold_half(face, near, across, False, complaint)
    )
    moving_leg = _fold_half(partner, far, across, True, complaint)
    tangent = _tangent_edge(fixed_leg, near, across)
    if abs(_tangent_edge(moving_leg, far, across).length - tangent.length) > 1e-6:
        raise ValueError(
            "the sheet is not the same width across the bend, so the strip it "
            "consumes does not roll into a cylinder"
        )

    bend_axis = Axis(
        Vector(tangent.position_at(0))
        + normal * surface_radius * (1 if angle > 0 else -1),
        across.cross(normal),
    )
    spin = Axis((0, 0, 0), bend_axis.direction)
    bend_face = _orient_face(
        Face.revolve(tangent, angle, bend_axis), normal.rotate(spin, angle / 2)
    )

    def folded(shape):
        """Slide a moving face up to the bend and swing it round."""
        return shape.translate(-across * arc).rotate(bend_axis, angle)

    faces = [fixed_leg, bend_face, folded(moving_leg)]
    for other in shell.faces():
        if other.is_same(face) or other.is_same(partner):
            continue
        faces.append(folded(other) if any(other.is_same(m) for m in moving) else other)
    return BuildSheet._validated_shell(faces)
