"""
Sheet Metal Utilities

name: sheet_utils.py
by:   Gumyr
date: September 3rd 2026

desc:
    This module defines shared sheet-metal parameters, calculations, and
    low-level surface development utilities.

license:

    Copyright 2026 Gumyr

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

from collections import deque
from dataclasses import dataclass, field
from math import degrees, radians
from typing import TYPE_CHECKING, Generic, NamedTuple, TypeVar

import OCP.GeomAbs as ga
import OCP.TopAbs as ta
from OCP.collections import (
    IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
)
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_GTransform,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_Sewing,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.ShapeExtend import ShapeExtend_WireData
from OCP.ShapeFix import ShapeFix_Face, ShapeFix_Shape, ShapeFix_Wire
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shell,
    TopoDS_Wire,
)

from build123d.build_enums import GeomType, SheetSurface
from build123d.geometry import TOLERANCE, Location, Matrix, Plane, Vector
from build123d.topology.one_d import Edge
from build123d.topology.shape_core import _topods_area, _topods_entities, downcast
from build123d.topology.utils import (
    _topods_face_normal,
    _topods_face_position,
    _topods_material_side,
)

if TYPE_CHECKING:
    from build123d.topology.two_d import Face, Shell

__all__ = ["FaceMap", "SheetMetalParameters", "UnfoldOutput", "UnfoldedFace"]

T = TypeVar("T")


class FaceMap(dict[int, T], Generic[T]):
    """A dict looked up by Face.

    The key is the face's underlying kernel shape, so a face found again with
    ``faces()`` matches the entry made for it, wherever the shell has been
    moved to and whichever way the face is oriented. An operation that
    rebuilds faces - a boolean, ``clean``, ``mirror``, ``scale`` - gives them
    new kernel shapes, so look faces up before doing any of that. Iterating
    the map gives the keys; iterate ``values()`` for the entries.
    """

    @staticmethod
    def key(face: Face) -> int:
        """The key a face is stored under"""
        return hash(face.wrapped.Located(TopLoc_Location()))

    def __getitem__(self, face: Face) -> T:  # type: ignore[override]
        return super().__getitem__(self.key(face))

    def __setitem__(self, face: Face, value: T) -> None:  # type: ignore[override]
        super().__setitem__(self.key(face), value)

    def __contains__(self, face: object) -> bool:
        try:
            return super().__contains__(self.key(face))  # type: ignore[arg-type]
        except AttributeError:
            return False

    def get(self, face: Face, default=None):  # type: ignore[override]
        """The entry for a face, or ``default`` when it has none"""
        return super().get(self.key(face), default)


@dataclass(frozen=True)
class UnfoldedFace:
    """What a face of a flat pattern developed from.

    A flat is developed as it is, and only ``sheet_face`` says anything. A
    bend is a cylinder developed into a strip, and the rest describes the
    bend the press brake has to put back: the angle, the inside radius, the
    neutral radius the strip's width was taken at, the bend line through the
    middle of the strip, and which way the sheet folds as the blank lies on
    ``Plane.XY``.

    Args:
        sheet_face (Face): the face of the folded sheet, in 3D, that this face
            of the pattern is the development of
        is_bend (bool): the sheet face is a cylinder
        angle (float): bend angle in degrees. 0 for a flat.
        inside_radius (float): physical inside radius of the bend. 0 for a flat.
        neutral_radius (float): the radius the bend was developed at. 0 for
            a flat.
        bend_line (Edge | None): the centre line of the strip, on the flat
            pattern. None for a flat.
        up (bool): the bend folds toward +Z of the flat pattern. False for a
            flat.
    """

    sheet_face: Face
    is_bend: bool
    angle: float = 0.0
    inside_radius: float = 0.0
    neutral_radius: float = 0.0
    bend_line: Edge | None = None
    up: bool = False


class UnfoldOutput(NamedTuple):
    """What unfolding a sheet gives back: the flat pattern and, for each of
    its faces, what it developed from.

    ``flat, face_map = sheet.unfold(parameters)`` unpacks it, and the fields
    are there by name too.

    Args:
        flat (Shell): the flat pattern on ``Plane.XY``
        face_map (FaceMap[UnfoldedFace]): looked up by a face of ``flat``
    """

    flat: Shell
    face_map: FaceMap[UnfoldedFace]


# The smallest inside radius a bend is modelled with. A fold with no gap, such
# as a flat hem, would otherwise have an inside radius of zero and legs lying
# on one another, which neither a surface nor a solid can represent. See the
# hem documentation for what this looks like on the finished part.
MIN_BEND_RADIUS = 1e-3


@dataclass(frozen=True)
class SheetMetalParameters:
    """Parameters relating a reference shell to its physical material.

    Args:
        thickness: Sheet material thickness.
        bend_radius: Default physical inside bend radius. When omitted, the
            sheet thickness is used.
        k_factor: Neutral-axis position from the locally concave material
            surface, from 0 to 1. Defaults to 0.5.
        sheet_surface: Reference surface represented by the shell. Defaults to
            ``SheetSurface.INSIDE``.
    """

    thickness: float
    bend_radius: float | None = None
    k_factor: float = 0.5
    sheet_surface: SheetSurface = SheetSurface.INSIDE

    def __post_init__(self):
        """Validate sheet-metal parameters."""
        if self.thickness <= 0:
            raise ValueError("thickness must be positive")
        if self.bend_radius is not None and self.bend_radius < 0:
            raise ValueError("bend_radius can't be negative")
        if not 0.0 <= self.k_factor <= 1.0:
            raise ValueError("k_factor must be between 0 and 1")
        if not isinstance(self.sheet_surface, SheetSurface):
            raise TypeError("sheet_surface must be a SheetSurface")

    @property
    def resolved_bend_radius(self) -> float:
        """Default inside bend radius, using thickness when unspecified."""
        return self.thickness if self.bend_radius is None else self.bend_radius


def material_offsets(parameters: SheetMetalParameters) -> tuple[float, float]:
    """Return signed inside and outside offsets from a reference shell."""
    thickness = parameters.thickness
    if parameters.sheet_surface == SheetSurface.INSIDE:
        return 0.0, -thickness
    if parameters.sheet_surface == SheetSurface.OUTSIDE:
        return thickness, 0.0
    if parameters.sheet_surface == SheetSurface.MID:
        return thickness / 2, -thickness / 2
    return (
        parameters.k_factor * thickness,
        -(1 - parameters.k_factor) * thickness,
    )


def surface_offset(parameters: SheetMetalParameters, positive_bend: bool) -> float:
    """How far the reference surface sits from the inside face of a bend.

    The inside of a bend is the face of the sheet nearer the bend's axis, which
    is one face for a positive bend and the other for a negative one. The
    reference surface is a fixed layer of the sheet, so its distance from the
    inside face depends on which way the sheet is bent: the ``NEUTRAL`` surface
    sits k·t from the inside of a positive bend and (1 - k)·t from the inside
    of a negative one.
    """
    thickness = parameters.thickness
    if parameters.sheet_surface == SheetSurface.MID:
        return thickness / 2
    if parameters.sheet_surface == SheetSurface.NEUTRAL:
        k_factor = parameters.k_factor
        return (k_factor if positive_bend else 1 - k_factor) * thickness
    if parameters.sheet_surface == SheetSurface.INSIDE:
        return 0.0 if positive_bend else thickness
    return thickness if positive_bend else 0.0


def reference_radius(
    inside_radius: float,
    parameters: SheetMetalParameters,
    bend_angle: float,
) -> float:
    """Convert a physical inside radius to a reference-surface radius."""
    offset = surface_offset(parameters, bend_angle > 0)
    return max(inside_radius + offset, MIN_BEND_RADIUS)


def neutral_radius(
    source_radius: float,
    parameters: SheetMetalParameters,
    positive_bend: bool,
) -> float:
    """The neutral radius of a bend, from the radius of its reference face.

    The neutral fibre - the layer of the sheet whose length a bend leaves
    unchanged - lies k·t from the inside face whichever way the sheet is bent,
    since the k-factor is defined from the compressed side. The reference face
    is a fixed layer of the sheet, so the neutral fibre is found from it by
    going back to the inside face first.
    """
    inside_radius = source_radius - surface_offset(parameters, positive_bend)
    radius = inside_radius + parameters.k_factor * parameters.thickness
    if radius <= 0:
        raise ValueError("Sheet parameters produce a non-positive neutral radius")
    return radius


def bend_allowance(
    inside_radius: float, bend_angle: float, parameters: SheetMetalParameters
) -> float:
    """The length of flat sheet a bend consumes: the arc of its neutral fibre.

    This is what ``bend`` takes out of the blank and what ``unfold`` gives
    back, and it does not depend on which surface the shell is drawn at.
    """
    neutral = inside_radius + parameters.k_factor * parameters.thickness
    return radians(abs(bend_angle)) * neutral


@dataclass
class _DevelopedFace:
    """A developed face, its source-edge provenance and where it was placed.

    ``placement`` takes the face from the frame it was developed in, where a
    cylinder's x is the arc length around it and y the distance along it, to
    where it lies in the flat pattern.
    """

    face: TopoDS_Face
    edges: dict[int, tuple[TopoDS_Edge, TopoDS_Edge]]
    placement: Location = field(default_factory=Location)


def _uv_topods_edge(
    source_face: TopoDS_Face,
    source_edge: TopoDS_Edge,
    xy_surface=None,
) -> TopoDS_Edge:
    """Create a planar edge from an edge's pcurve on a source face."""
    if xy_surface is None:
        xy_face = BRepBuilderAPI_MakeFace(Plane.XY.wrapped).Face()
        xy_surface = BRep_Tool.Surface_s(xy_face)

    first, last = BRep_Tool.Range_s(source_edge, source_face)
    pcurve = BRep_Tool.CurveOnSurface_s(source_edge, source_face, first, last)
    edge_builder = BRepBuilderAPI_MakeEdge(pcurve, xy_surface, first, last)
    if not edge_builder.IsDone():  # pragma: no cover
        raise ValueError("Unable to convert pcurve to a planar edge")

    uv_edge = edge_builder.Edge()
    if source_edge.Orientation() == ta.TopAbs_REVERSED:
        uv_edge = TopoDS.Edge(uv_edge.Reversed())
    return uv_edge


def _make_uv_wire(
    source_face: TopoDS_Face,
    source_wire: TopoDS_Wire,
    xy_surface,
) -> tuple[TopoDS_Wire, dict[int, tuple[TopoDS_Edge, TopoDS_Edge]]]:
    """Develop a source wire into UV space and record edge provenance."""
    edge_map: dict[int, tuple[TopoDS_Edge, TopoDS_Edge]] = {}
    boundary = ShapeExtend_WireData()
    wire_explorer = BRepTools_WireExplorer(source_wire)
    while wire_explorer.More():
        source_edge = TopoDS.Edge(wire_explorer.Current())
        uv_edge = _uv_topods_edge(source_face, source_edge, xy_surface)
        edge_map[hash(source_edge)] = (source_edge, uv_edge)
        boundary.Add(uv_edge)
        wire_explorer.Next()

    # Each edge carries its pcurve trimmed to its own parameters, and where a
    # face has been cut the two curves either side of the cut can stop a
    # fraction of a micron apart - the vertex they share says otherwise, but
    # the curves are what gets walked here. Assembling through ShapeFix closes
    # those hairlines; a plain wire builder refuses them.
    fixer = ShapeFix_Wire()
    fixer.Load(boundary)
    fixer.SetPrecision(TOLERANCE)
    fixer.SetMaxTolerance(TOLERANCE * 100)
    fixer.FixReorder()
    fixer.FixConnected()
    fixer.FixClosed()
    wire = fixer.Wire()
    if wire.IsNull():
        raise ValueError("Unable to assemble UV boundary edges")
    return wire, edge_map


def _edges_match(
    first: TopoDS_Edge, second: TopoDS_Edge, reverse: bool = False
) -> bool:
    """Compare edge geometry by sampling, optionally in reverse order."""
    return all(
        (
            Edge(first).position_at(position)
            - Edge(second).position_at(1.0 - position if reverse else position)
        ).length
        <= TOLERANCE
        for position in (0.0, 0.25, 0.5, 0.75, 1.0)
    )


def _uv_topods_face_with_map(
    source_face: TopoDS_Face,
) -> tuple[TopoDS_Face, dict[int, tuple[TopoDS_Edge, TopoDS_Edge]]]:
    """Create a planar UV face and map source edges to its assembled edges."""
    xy_face = BRepBuilderAPI_MakeFace(Plane.XY.wrapped).Face()
    xy_surface = BRep_Tool.Surface_s(xy_face)

    source_outer = BRepTools.OuterWire_s(source_face)
    outer_wire, preliminary_map = _make_uv_wire(source_face, source_outer, xy_surface)
    source_wires = [
        TopoDS.Wire(wire)
        for wire in _topods_entities(source_face, "Wire")
        if not wire.IsSame(source_outer)
    ]
    inner_wires: list[TopoDS_Wire] = []
    for source_wire in source_wires:
        inner_wire, inner_map = _make_uv_wire(source_face, source_wire, xy_surface)
        inner_wires.append(inner_wire)
        preliminary_map.update(inner_map)

    outer_fixer = ShapeFix_Shape(outer_wire)
    outer_fixer.Perform()
    face_builder = BRepBuilderAPI_MakeFace(TopoDS.Wire(outer_fixer.Shape()), True)
    for inner_wire in inner_wires:
        inner_fixer = ShapeFix_Shape(inner_wire)
        inner_fixer.Perform()
        face_builder.Add(TopoDS.Wire(inner_fixer.Shape()))
    face_builder.Build()
    if not face_builder.IsDone():
        raise ValueError("Unable to assemble UV face")
    face_fixer = ShapeFix_Face(face_builder.Face())
    face_fixer.FixOrientation()
    face_fixer.Perform()
    uv_face = TopoDS.Face(face_fixer.Result())

    actual_map: dict[int, tuple[TopoDS_Edge, TopoDS_Edge]] = {}
    available_edges = [TopoDS.Edge(edge) for edge in _topods_entities(uv_face, "Edge")]
    for source_key, (source_edge, preliminary_edge) in preliminary_map.items():
        matches: list[tuple[TopoDS_Edge, bool]] = []
        for candidate in available_edges:
            if _edges_match(candidate, preliminary_edge):
                matches.append((candidate, False))
            elif _edges_match(candidate, preliminary_edge, reverse=True):
                matches.append((candidate, True))
        if len(matches) != 1:
            raise ValueError(
                "Expected exactly one assembled UV edge for each source edge, "
                f"found {len(matches)}"
            )
        actual_edge, reverse = matches[0]
        actual_map[source_key] = (
            source_edge,
            TopoDS.Edge(actual_edge.Reversed()) if reverse else actual_edge,
        )
        available_edges.remove(actual_edge)

    return uv_face, actual_map


def _scale_developed_face(developed: _DevelopedFace, radius: float) -> _DevelopedFace:
    """Scale a cylindrical UV face into a metric development."""
    scale_matrix = Matrix(
        [
            [radius, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    transformer = BRepBuilderAPI_GTransform(developed.face, scale_matrix.wrapped, True)
    scaled_face = TopoDS.Face(transformer.Shape())
    scaled_edges: dict[int, tuple[TopoDS_Edge, TopoDS_Edge]] = {}
    for source_key, (source_edge, uv_edge) in developed.edges.items():
        modified = transformer.Modified(uv_edge)
        if modified.Size() != 1:
            raise ValueError(
                "Expected exactly one scaled edge for each UV edge, "
                f"found {modified.Size()}"
            )
        scaled_edge = TopoDS.Edge(modified.First())
        uv_start = Edge(uv_edge).position_at(0)
        expected_start = Vector(radius * uv_start.X, uv_start.Y, uv_start.Z)
        if (Edge(scaled_edge).position_at(0) - expected_start).length > TOLERANCE:
            scaled_edge = TopoDS.Edge(scaled_edge.Reversed())
        scaled_edges[source_key] = (source_edge, scaled_edge)
    return _DevelopedFace(scaled_face, scaled_edges, developed.placement)


def is_positive_bend(face: TopoDS_Face) -> bool:
    """Return whether a cylindrical face bends toward its oriented normal."""
    cylinder = BRepAdaptor_Surface(face).Cylinder()
    axis = cylinder.Axis()
    surface_point = _topods_face_position(face, 0.5, 0.5)
    axis_position = Vector(axis.Location())
    axis_direction = Vector(axis.Direction())
    axis_point = axis_position + axis_direction * (
        (surface_point - axis_position).dot(axis_direction)
    )
    return _topods_face_normal(face).dot(surface_point - axis_point) < 0


def _develop_face(
    source_face: TopoDS_Face,
    sheet_parameters: SheetMetalParameters | None,
) -> _DevelopedFace:
    """Create a metric XY development of a planar or cylindrical source face."""
    flat_face, edge_map = _uv_topods_face_with_map(source_face)
    result = _DevelopedFace(flat_face, edge_map)
    adaptor = BRepAdaptor_Surface(source_face)
    if adaptor.GetType() == ga.GeomAbs_Cylinder:
        radius = adaptor.Cylinder().Radius()
        if sheet_parameters is not None:
            radius = neutral_radius(
                radius, sheet_parameters, is_positive_bend(source_face)
            )
        result = _scale_developed_face(result, radius)
    return result


def _ordered_developed_edge_points(
    edge_record: tuple[TopoDS_Edge, TopoDS_Edge],
    reference_edge: TopoDS_Edge,
) -> tuple[Vector, Vector]:
    """Return developed endpoints ordered like a source edge occurrence."""
    source_edge, developed_edge = edge_record
    reference_start = Edge(reference_edge).position_at(0)
    source_start = Edge(source_edge).position_at(0)
    source_end = Edge(source_edge).position_at(1)
    if (source_start - reference_start).length <= TOLERANCE:
        return Edge(developed_edge).position_at(0), Edge(developed_edge).position_at(1)
    if (source_end - reference_start).length <= TOLERANCE:
        return Edge(developed_edge).position_at(1), Edge(developed_edge).position_at(0)
    raise ValueError("Unable to associate shared-edge endpoints")


def _move_developed_face(
    developed: _DevelopedFace, placement: Location
) -> _DevelopedFace:
    """Rigidly place a developed face and all of its mapped edges."""
    return _DevelopedFace(
        TopoDS.Face(developed.face.Moved(placement.wrapped)),
        {
            source_key: (
                source_edge,
                TopoDS.Edge(developed_edge.Moved(placement.wrapped)),
            )
            for source_key, (source_edge, developed_edge) in developed.edges.items()
        },
        placement * developed.placement,
    )


def _place_adjacent_developed_face(
    parent: _DevelopedFace,
    child: _DevelopedFace,
    shared_edge: TopoDS_Edge,
) -> _DevelopedFace:
    """Place a child against its parent along their shared source edge."""
    edge_key = hash(shared_edge)
    try:
        parent_edge_record = parent.edges[edge_key]
        child_edge_record = child.edges[edge_key]
    except KeyError as exc:
        raise ValueError(
            "A shared source edge is missing from a developed-face map"
        ) from exc

    parent_start, parent_end = _ordered_developed_edge_points(
        parent_edge_record, shared_edge
    )
    child_start, child_end = _ordered_developed_edge_points(
        child_edge_record, shared_edge
    )
    child_frame = Plane(
        origin=child_start,
        x_dir=child_end - child_start,
        z_dir=_topods_face_normal(child.face),
    )

    def candidate(parent_normal: Vector) -> _DevelopedFace:
        parent_frame = Plane(
            origin=parent_start,
            x_dir=parent_end - parent_start,
            z_dir=parent_normal,
        )
        placement = parent_frame.location * child_frame.location.inverse()
        return _move_developed_face(child, placement)

    placed = candidate(_topods_face_normal(parent.face))
    placed_start, placed_end = _ordered_developed_edge_points(
        placed.edges[edge_key], shared_edge
    )
    # the child belongs on the far side of the shared edge from the parent
    parent_side = _topods_material_side(parent.face, parent_edge_record[1])
    child_side = _topods_material_side(placed.face, placed.edges[edge_key][1])
    if parent_side.dot(child_side) >= 0:
        placed = candidate(-_topods_face_normal(parent.face))
        placed_start, placed_end = _ordered_developed_edge_points(
            placed.edges[edge_key], shared_edge
        )

    if (placed_start - parent_start).length > TOLERANCE or (
        placed_end - parent_end
    ).length > TOLERANCE:
        raise ValueError("Unable to align adjacent developed faces")
    return placed


def _sew_developed_faces(
    faces: list[TopoDS_Face],
) -> tuple[TopoDS_Shell, list[TopoDS_Face]]:
    """Sew the placed developments into the flat shell.

    Sewing rebuilds the faces it joins, so the faces of the shell are not the
    faces given. The second result is the face of the shell each given face
    became, in the order given.
    """
    if len(faces) == 1:
        shell = TopoDS_Shell()
        builder = BRep_Builder()
        builder.MakeShell(shell)
        builder.Add(shell, faces[0])
        return shell, faces
    sewing = BRepBuilderAPI_Sewing(TOLERANCE)
    for face in faces:
        sewing.Add(face)
    sewing.Perform()
    sewn = downcast(sewing.SewedShape())
    if not isinstance(sewn, TopoDS_Shell):
        raise ValueError("the faces do not sew into one connected shell")
    return sewn, [
        TopoDS.Face(sewing.Modified(face)) if sewing.IsModified(face) else face
        for face in faces
    ]


def _folds_up(sheet_face: Face, placed: _DevelopedFace) -> bool:
    """Does a bend fold toward +Z as its development lies in the flat pattern?

    The development keeps, for every edge, which way the edge runs and which
    side of it the material is on, so the two together give a handedness
    that is the same on the cylinder and on the flat. On the cylinder it is
    read against the direction toward the axis, the side the sheet folds
    to; on the flat it is read against +Z. The bend folds up when they agree.
    """
    records = list(placed.edges.values())
    for record in records:
        if Edge(record[0]).geom_type == GeomType.LINE:
            break
    else:
        record = records[0]
    source_edge, developed_edge = record
    source_start = Edge(source_edge).position_at(0)
    source_end = Edge(source_edge).position_at(1)
    developed_start, developed_end = _ordered_developed_edge_points(record, source_edge)
    source_hand = (source_end - source_start).cross(
        _topods_material_side(sheet_face.wrapped, source_edge)
    )
    flat_hand = (developed_end - developed_start).cross(
        _topods_material_side(placed.face, developed_edge)
    )

    axis = sheet_face.axis_of_rotation
    assert axis is not None  # a cylinder always has one
    edge_middle = (source_start + source_end) / 2
    axis_point = axis.position + axis.direction * (
        (edge_middle - axis.position).dot(axis.direction)
    )
    return (source_hand.dot(axis_point - edge_middle) > 0) == (flat_hand.Z > 0)


def _unfolded_face(
    source_face: TopoDS_Face,
    placed: _DevelopedFace,
    sheet_parameters: SheetMetalParameters | None,
) -> UnfoldedFace:
    """The record of a face of the flat pattern: a flat as it is, a bend with
    its angle, radii, bend line and direction."""
    # pylint: disable=import-outside-toplevel
    from build123d.topology.two_d import Face

    sheet_face = Face(source_face)
    if sheet_face.geom_type != GeomType.CYLINDER:
        return UnfoldedFace(sheet_face=sheet_face, is_bend=False)

    radius = sheet_face.radius
    assert radius is not None  # a cylinder always has one
    positive = is_positive_bend(source_face)
    if sheet_parameters is None:
        inside_radius = neutral = radius
    else:
        inside_radius = radius - surface_offset(sheet_parameters, positive)
        neutral = neutral_radius(radius, sheet_parameters, positive)

    # the strip was developed with x the arc length at the development radius
    # and y the distance along the bend, then placed; its centre line is the
    # mid-angle line of the cylinder, clipped to the strip where its ends are
    # not square
    u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(source_face)
    x_middle = neutral * (u_min + u_max) / 2
    bend_line = Edge.make_line((x_middle, v_min, 0), (x_middle, v_max, 0)).moved(
        placed.placement
    )
    clipped = bend_line.intersect(Face(placed.face))
    pieces = clipped.edges() if clipped is not None else []
    if len(pieces) == 1:
        bend_line = pieces[0]

    return UnfoldedFace(
        sheet_face=sheet_face,
        is_bend=True,
        angle=degrees(u_max - u_min),
        inside_radius=inside_radius,
        neutral_radius=neutral,
        bend_line=bend_line,
        up=_folds_up(sheet_face, placed),
    )


def _unfold_shell(
    shell: TopoDS_Shell,
    sheet_parameters: SheetMetalParameters | None,
) -> tuple[TopoDS_Shell, FaceMap[UnfoldedFace]]:
    """Develop a planar/cylindrical shell onto the XY plane.

    Returns the flat shell and, for each of its faces, what it developed
    from.
    """
    if sheet_parameters is not None and not isinstance(
        sheet_parameters, SheetMetalParameters
    ):
        raise TypeError("sheet_parameters must be a SheetMetalParameters")

    source_faces = [TopoDS.Face(face) for face in _topods_entities(shell, "Face")]
    if not source_faces:
        raise ValueError("unfold requires a non-empty Shell")
    supported_types = (ga.GeomAbs_Plane, ga.GeomAbs_Cylinder)
    if not all(
        BRepAdaptor_Surface(face).GetType() in supported_types for face in source_faces
    ):
        raise ValueError("unfold only supports planes and cylinders")

    planar_faces = [
        face
        for face in source_faces
        if BRepAdaptor_Surface(face).GetType() == ga.GeomAbs_Plane
    ]
    if not planar_faces:
        raise ValueError("unfold requires at least one planar face")

    faces_by_key = {hash(face): face for face in source_faces}
    adjacency: dict[int, list[tuple[int, TopoDS_Edge]]] = {
        key: [] for key in faces_by_key
    }
    edge_face_map = (
        IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    )
    TopExp.MapShapesAndAncestors_s(shell, ta.TopAbs_EDGE, ta.TopAbs_FACE, edge_face_map)
    for raw_edge in _topods_entities(shell, "Edge"):
        edge = TopoDS.Edge(raw_edge)
        connected_by_key: dict[int, TopoDS_Face] = {}
        if edge_face_map.Contains(edge):
            for connected_shape in edge_face_map.FindFromKey(edge):
                face = TopoDS.Face(connected_shape)
                connected_by_key[hash(face)] = face
        connected_faces = list(connected_by_key.values())
        if len(connected_faces) > 2:
            raise ValueError("unfold doesn't support non-manifold edges")
        if len(connected_faces) == 2:
            first_key, second_key = (hash(face) for face in connected_faces)
            adjacency[first_key].append((second_key, edge))
            adjacency[second_key].append((first_key, edge))

    developments = {
        key: _develop_face(face, sheet_parameters) for key, face in faces_by_key.items()
    }

    root_key = hash(max(planar_faces, key=_topods_area))
    placed = {root_key: developments[root_key]}
    queue = deque([root_key])
    while queue:
        parent_key = queue.popleft()
        for child_key, shared_edge in adjacency[parent_key]:
            if child_key not in placed:
                placed[child_key] = _place_adjacent_developed_face(
                    placed[parent_key], developments[child_key], shared_edge
                )
                queue.append(child_key)
                continue

            edge_key = hash(shared_edge)
            parent_points = _ordered_developed_edge_points(
                placed[parent_key].edges[edge_key], shared_edge
            )
            child_points = _ordered_developed_edge_points(
                placed[child_key].edges[edge_key], shared_edge
            )
            if any(
                (parent_point - child_point).length > TOLERANCE
                for parent_point, child_point in zip(parent_points, child_points)
            ):
                raise ValueError(
                    "The sheet contains a cycle that requires a cut before unfolding"
                )

    if len(placed) != len(source_faces):
        raise ValueError("The Shell contains disconnected face groups")

    keys = list(placed)
    result, flat_faces = _sew_developed_faces([placed[key].face for key in keys])
    if not BRepCheck_Analyzer(result).IsValid():
        raise ValueError("Unfolding produced an invalid flat Shell")

    # pylint: disable=import-outside-toplevel
    from build123d.topology.two_d import Face

    records: FaceMap[UnfoldedFace] = FaceMap()
    for key, flat_face in zip(keys, flat_faces):
        records[Face(flat_face)] = _unfolded_face(
            faces_by_key[key], placed[key], sheet_parameters
        )
    return result, records
