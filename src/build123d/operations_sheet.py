"""
Sheet Metal Operations

name: operations_sheet.py
by:   Gumyr & Gabriel Jesus
date: July 21st 2026

desc:
    Surface-native sheet metal operations.

license:

    Copyright 2026 Gabriel Jesus

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

from math import asin, atan, cos, degrees, radians, sin, sqrt, tan
from typing import Literal, overload

from build123d.build_common import flatten_sequence, validate_inputs
from build123d.build_enums import GeomType, HemType, Mode, SheetSurface
from build123d.build_sheet import BuildSheet, SheetMetalParameters
from build123d.geometry import Axis, Vector
from build123d.topology import (
    Edge,
    Face,
    Shape,
    Shell,
    Sketch,
    Vertex,
    Wire,
    topo_explore_connected_faces,
)

MIN_BEND_RADIUS = 1e-3


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


def _reference_radius(
    inside_radius: float,
    thickness: float,
    sheet_surface: SheetSurface,
    k_factor: float,
    angle: float,
) -> float:
    """Convert a physical inside radius to the selected reference surface."""
    if sheet_surface == SheetSurface.MID:
        offset = thickness / 2
    elif sheet_surface == SheetSurface.NEUTRAL:
        offset = (k_factor if angle > 0 else 1 - k_factor) * thickness
    elif sheet_surface == SheetSurface.INSIDE:
        offset = 0 if angle > 0 else thickness
    else:
        offset = thickness if angle > 0 else 0
    return max(inside_radius + offset, MIN_BEND_RADIUS)


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
    thickness: float,
    inside_radius: float,
    angle: float,
    leg_length: float,
    sheet_surface: SheetSurface,
    k_factor: float,
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

    radius = _reference_radius(inside_radius, thickness, sheet_surface, k_factor, angle)
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
        radius: Physical inside bend radius. Defaults to the BuildSheet radius.
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
        radius = context.bend_radius if context is not None else parameters.thickness
    if radius < 0:
        raise ValueError("radius can't be negative")

    target = _target_shell(context, edge_list)
    additions = [
        face
        for edge in edge_list
        for face in _make_bend_faces(
            target,
            edge,
            parameters.thickness,
            radius,
            angle,
            length,
            parameters.sheet_surface,
            parameters.k_factor,
            gap_start,
            gap_end,
        )
    ]
    return _apply_faces(context, target, additions, mode)


def _miter_target(context: BuildSheet | None, vertices: list[Vertex]) -> Shell:
    """Resolve the shell containing vertices in Builder or Algebra mode."""
    if context is not None:
        return context.sheet_local
    parents = [vertex.topo_parent for vertex in vertices]
    if not all(isinstance(parent, Shell) for parent in parents):
        raise ValueError("miter vertices must belong to a sheet Shell")
    target = parents[0]
    if any(not target.is_same(parent) for parent in parents[1:]):
        raise ValueError("miter vertices must belong to the same sheet Shell")
    return target


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
    for (face, rim, bend, side), vertex in selections:
        face_selections.setdefault(face, []).append((rim, bend, side, vertex))

    replacements: dict[Face, dict[Vertex, Vector]] = {}
    for face, face_items in face_selections.items():
        replacements[face] = {}
        for rim, bend, side, vertex in face_items:
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
    if hem_type in (HemType.FLAT, HemType.OPEN):
        if opening < 0:
            raise ValueError("opening must be positive")
        if width is None:
            raise ValueError(f"width is required for {hem_type}")
        bend_radius = max(0.5 * opening, MIN_BEND_RADIUS)
        if width <= bend_radius + thickness:
            raise ValueError(
                "width must be greater than the bend width " "(bend radius + thickness)"
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
        radius = context.bend_radius if context is not None else None

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
            parameters.thickness,
            bend_radius,
            bend_angle,
            leg_length,
            parameters.sheet_surface,
            parameters.k_factor,
        )
    ]
    return _apply_faces(context, target, additions, mode)
