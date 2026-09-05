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
from dataclasses import dataclass

import OCP.GeomAbs as ga
import OCP.TopAbs as ta
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_GTransform,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Sewing,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt, gp_Vec
from OCP.ShapeFix import ShapeFix_Face, ShapeFix_Shape
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Wire,
)
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape

from build123d.build_enums import SheetSurface
from build123d.geometry import TOLERANCE, Location, Matrix, Plane, Vector

__all__ = ["SheetMetalParameters"]

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


def reference_radius(
    inside_radius: float,
    parameters: SheetMetalParameters,
    bend_angle: float,
) -> float:
    """Convert a physical inside radius to a reference-surface radius."""
    thickness = parameters.thickness
    if parameters.sheet_surface == SheetSurface.MID:
        offset = thickness / 2
    elif parameters.sheet_surface == SheetSurface.NEUTRAL:
        offset = (
            parameters.k_factor if bend_angle > 0 else 1 - parameters.k_factor
        ) * thickness
    elif parameters.sheet_surface == SheetSurface.INSIDE:
        offset = 0 if bend_angle > 0 else thickness
    else:
        offset = thickness if bend_angle > 0 else 0
    return max(inside_radius + offset, MIN_BEND_RADIUS)


def neutral_radius(
    source_radius: float,
    parameters: SheetMetalParameters,
    positive_bend: bool,
) -> float:
    """Return the neutral radius corresponding to a cylindrical reference face."""
    thickness = parameters.thickness
    k_factor = parameters.k_factor
    if parameters.sheet_surface == SheetSurface.NEUTRAL:
        normal_offset = 0.0
    elif parameters.sheet_surface == SheetSurface.MID:
        normal_offset = (0.5 - k_factor) * thickness
    elif parameters.sheet_surface == SheetSurface.INSIDE:
        normal_offset = -k_factor * thickness
    else:
        normal_offset = (1 - k_factor) * thickness

    # A positive bend's oriented normal points toward the cylinder axis, so a
    # signed normal offset changes its radius in the opposite direction.
    radial_offset = (-1 if positive_bend else 1) * normal_offset
    radius = source_radius + radial_offset
    if radius <= 0:
        raise ValueError("Sheet parameters produce a non-positive neutral radius")
    return radius


@dataclass
class _DevelopedFace:
    """A developed face and its source-edge provenance."""

    face: TopoDS_Face
    edges: dict[int, tuple[TopoDS_Edge, TopoDS_Edge]]


def _topods_entities(
    shape: TopoDS_Shape, shape_type: ta.TopAbs_ShapeEnum
) -> list[TopoDS_Shape]:
    """Return unique subshapes of the requested type."""
    entities: dict[int, TopoDS_Shape] = {}
    explorer = TopExp_Explorer(shape, shape_type)
    while explorer.More():
        entity = explorer.Current()
        entities[hash(entity)] = entity
        explorer.Next()
    return list(entities.values())


def _edge_position(edge: TopoDS_Edge, position: float) -> Vector:
    """Return a point at a normalized position along an edge."""
    adaptor = BRepAdaptor_Curve(edge)
    if edge.Orientation() == ta.TopAbs_REVERSED:
        position = 1.0 - position
    parameter = adaptor.FirstParameter() + position * (
        adaptor.LastParameter() - adaptor.FirstParameter()
    )
    return Vector(adaptor.Value(parameter))


def _face_position(face: TopoDS_Face, u: float, v: float) -> Vector:
    """Return a point at normalized UV coordinates on a face."""
    u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
    surface = BRep_Tool.Surface_s(face)
    return Vector(
        surface.Value(u_min + u * (u_max - u_min), v_min + v * (v_max - v_min))
    )


def _face_normal(face: TopoDS_Face, u: float = 0.5, v: float = 0.5) -> Vector:
    """Return the oriented normal at normalized UV coordinates."""
    u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
    point = gp_Pnt()
    normal = gp_Vec()
    BRepGProp_Face(face).Normal(
        u_min + u * (u_max - u_min),
        v_min + v * (v_max - v_min),
        point,
        normal,
    )
    return Vector(normal).normalized()


def _face_center(face: TopoDS_Face) -> Vector:
    """Return the face center of mass."""
    properties = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, properties)
    return Vector(properties.CentreOfMass())


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
    wire_builder = BRepBuilderAPI_MakeWire()
    wire_explorer = BRepTools_WireExplorer(source_wire)
    while wire_explorer.More():
        source_edge = TopoDS.Edge(wire_explorer.Current())
        uv_edge = _uv_topods_edge(source_face, source_edge, xy_surface)
        edge_map[hash(source_edge)] = (source_edge, uv_edge)
        wire_builder.Add(uv_edge)
        wire_explorer.Next()
    wire_builder.Build()
    if not wire_builder.IsDone():
        raise ValueError("Unable to assemble UV boundary edges")
    return wire_builder.Wire(), edge_map


def _edges_match(
    first: TopoDS_Edge, second: TopoDS_Edge, reverse: bool = False
) -> bool:
    """Compare edge geometry by sampling, optionally in reverse order."""
    return all(
        (
            _edge_position(first, position)
            - _edge_position(second, 1.0 - position if reverse else position)
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
        for wire in _topods_entities(source_face, ta.TopAbs_WIRE)
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
    available_edges = [
        TopoDS.Edge(edge) for edge in _topods_entities(uv_face, ta.TopAbs_EDGE)
    ]
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
        uv_start = _edge_position(uv_edge, 0)
        expected_start = Vector(radius * uv_start.X, uv_start.Y, uv_start.Z)
        if (_edge_position(scaled_edge, 0) - expected_start).length > TOLERANCE:
            scaled_edge = TopoDS.Edge(scaled_edge.Reversed())
        scaled_edges[source_key] = (source_edge, scaled_edge)
    return _DevelopedFace(scaled_face, scaled_edges)


def _is_positive_bend(face: TopoDS_Face) -> bool:
    """Return whether a cylindrical face bends toward its oriented normal."""
    cylinder = BRepAdaptor_Surface(face).Cylinder()
    axis = cylinder.Axis()
    surface_point = _face_position(face, 0.5, 0.5)
    axis_position = Vector(axis.Location())
    axis_direction = Vector(axis.Direction())
    axis_point = axis_position + axis_direction * (
        (surface_point - axis_position).dot(axis_direction)
    )
    return _face_normal(face).dot(surface_point - axis_point) < 0


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
                radius, sheet_parameters, _is_positive_bend(source_face)
            )
        result = _scale_developed_face(result, radius)
    return result


def _ordered_developed_edge_points(
    edge_record: tuple[TopoDS_Edge, TopoDS_Edge],
    reference_edge: TopoDS_Edge,
) -> tuple[Vector, Vector]:
    """Return developed endpoints ordered like a source edge occurrence."""
    source_edge, developed_edge = edge_record
    reference_start = _edge_position(reference_edge, 0)
    source_start = _edge_position(source_edge, 0)
    source_end = _edge_position(source_edge, 1)
    if (source_start - reference_start).length <= TOLERANCE:
        return _edge_position(developed_edge, 0), _edge_position(developed_edge, 1)
    if (source_end - reference_start).length <= TOLERANCE:
        return _edge_position(developed_edge, 1), _edge_position(developed_edge, 0)
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
    )


def _side_of_edge(face: TopoDS_Face, start: Vector, end: Vector) -> float:
    """Return the signed side of an edge containing the face's center."""
    tangent = (end - start).normalized()
    midpoint = (start + end) * 0.5
    return tangent.cross(_face_center(face) - midpoint).Z


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
        z_dir=_face_normal(child.face),
    )

    def candidate(parent_normal: Vector) -> _DevelopedFace:
        parent_frame = Plane(
            origin=parent_start,
            x_dir=parent_end - parent_start,
            z_dir=parent_normal,
        )
        placement = parent_frame.location * child_frame.location.inverse()
        return _move_developed_face(child, placement)

    placed = candidate(_face_normal(parent.face))
    placed_start, placed_end = _ordered_developed_edge_points(
        placed.edges[edge_key], shared_edge
    )
    parent_side = _side_of_edge(parent.face, parent_start, parent_end)
    child_side = _side_of_edge(placed.face, placed_start, placed_end)
    if parent_side * child_side >= 0:
        placed = candidate(-_face_normal(parent.face))
        placed_start, placed_end = _ordered_developed_edge_points(
            placed.edges[edge_key], shared_edge
        )

    if (placed_start - parent_start).length > TOLERANCE or (
        placed_end - parent_end
    ).length > TOLERANCE:
        raise ValueError("Unable to align adjacent developed faces")
    return placed


def _make_shell(faces: list[TopoDS_Face]) -> TopoDS_Shell:
    """Sew developed faces into one shell."""
    if len(faces) == 1:
        shell = TopoDS_Shell()
        builder = BRep_Builder()
        builder.MakeShell(shell)
        builder.Add(shell, faces[0])
        return shell

    sewing = BRepBuilderAPI_Sewing()
    for face in faces:
        sewing.Add(face)
    sewing.Perform()
    sewed = sewing.SewedShape()
    if sewed.ShapeType() != ta.TopAbs_SHELL:
        raise ValueError("Unfolding didn't produce one connected Shell")
    return TopoDS.Shell(sewed)


def _unfold_shell(
    shell: TopoDS_Shell,
    sheet_parameters: SheetMetalParameters | None,
) -> TopoDS_Shell:
    """Develop a planar/cylindrical shell onto the XY plane."""
    if sheet_parameters is not None and not isinstance(
        sheet_parameters, SheetMetalParameters
    ):
        raise TypeError("sheet_parameters must be a SheetMetalParameters")

    source_faces = [
        TopoDS.Face(face) for face in _topods_entities(shell, ta.TopAbs_FACE)
    ]
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
    edge_face_map = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shell, ta.TopAbs_EDGE, ta.TopAbs_FACE, edge_face_map)
    for raw_edge in _topods_entities(shell, ta.TopAbs_EDGE):
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

    def face_area(face: TopoDS_Face) -> float:
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, properties)
        return properties.Mass()

    root_key = hash(max(planar_faces, key=face_area))
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

    result = _make_shell([developed.face for developed in placed.values()])
    if not BRepCheck_Analyzer(result).IsValid():
        raise ValueError("Unfolding produced an invalid flat Shell")
    return result
