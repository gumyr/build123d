"""
Sketch Operations

name: operations_sketch.py
by:   Gumyr
date: March 21th 2023

desc:
    This python module contains operations (functions) that work on
    planar Sketches.

license:

    Copyright 2022 Gumyr

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

from collections.abc import Iterable
from scipy.spatial import Voronoi
from typing import cast
from build123d.build_enums import Mode, SortBy, Transition
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    ShapeList,
    Shell,
    Wire,
    Sketch,
    topo_explore_connected_edges,
    topo_explore_common_vertex,
)
from build123d.geometry import Plane, Vector, TOLERANCE
from build123d.build_common import flatten_sequence, validate_inputs
from build123d.build_sketch import BuildSketch


def full_round(
    edge: Edge,
    invert: bool = False,
    voronoi_point_count: int = 100,
    mode: Mode = Mode.REPLACE,
) -> tuple[Sketch, Vector, float]:
    """Sketch Operation: full_round

    Given an edge from a Face/Sketch, modify the face by replacing the given edge with the
    arc of the Voronoi largest empty circle that will fit within the Face.  This
    "rounds off" the end of the object.

    Args:
        edge (Edge): target Edge to remove
        invert (bool, optional): make the arc concave instead of convex. Defaults to False.
        voronoi_point_count (int, optional): number of points along each edge
            used to create the voronoi vertices as potential locations for the
            center of the largest empty circle. Defaults to 100.
        mode (Mode, optional): combination mode. Defaults to Mode.REPLACE.

    Raises:
        ValueError: Invalid geometry

    Returns:
        Sketch: the modified shape

    """
    context: BuildSketch | None = BuildSketch._get_context("full_round")

    if not isinstance(edge, Edge):
        raise ValueError("A single Edge must be provided")
    validate_inputs(context, "full_round", edge)

    if edge.topo_parent is None:
        raise ValueError("edge must be extracted from shape")

    #
    # Generate a set of evenly spaced points along the given edge and the
    # edges connected to it and use them to generate the Voronoi vertices
    # as possible locations for the center of the largest empty circle
    # Note: full_round could be enhanced to handle the case of a face composed
    # of two edges.
    connected_edges = topo_explore_connected_edges(edge, edge.topo_parent)
    if len(connected_edges) != 2:
        raise ValueError("Invalid geometry - 3 or more edges required")

    edge_group = [edge] + connected_edges
    voronoi_edge_points = [
        v
        for e in edge_group
        for v in e.positions(
            [i / voronoi_point_count for i in range(voronoi_point_count + 1)]
        )
    ]
    numpy_style_pnts = [[p.X, p.Y] for p in voronoi_edge_points]
    voronoi_vertices = [Vector(*v) for v in Voronoi(numpy_style_pnts).vertices]

    #
    # Refine the largest empty circle center estimate by averaging the best
    # three candidates.  The minimum distance between the edges and this
    # center is the circle radius.
    best_three: list[tuple[float, int]] = [
        (float("inf"), int()),
        (float("inf"), int()),
        (float("inf"), int()),
    ]
    for i, v in enumerate(voronoi_vertices):
        distances = [edge.distance_to(v) for edge in edge_group]
        avg_distance = sum(distances) / 3
        difference = max(abs(d - avg_distance) for d in distances)

        # Prefer vertices with minimal difference
        if difference < best_three[-1][0]:
            best_three[-1] = (difference, i)
            best_three.sort(key=lambda x: x[0])

    # Refine by averaging the best three
    voronoi_circle_center = (
        sum((voronoi_vertices[i] for _, i in best_three), Vector(0, 0, 0)) / 3
    )

    # Determine where the connected edges intersect with the largest empty circle
    connected_edges_end_points = [
        e.distance_to_with_closest_points(voronoi_circle_center)[1]
        for e in connected_edges
    ]

    # Determine where the target edge intersects with the largest empty circle
    middle_edge_arc_point = edge.distance_to_with_closest_points(voronoi_circle_center)[
        1
    ]

    # Trim the connected edges to allow room for the circular feature
    origin = sum(connected_edges_end_points, Vector(0, 0, 0)) / 2
    x_dir = (connected_edges_end_points[1] - connected_edges_end_points[0]).normalized()
    to_arc_vec = origin - middle_edge_arc_point
    # Project `to_arc_vec` onto the plane perpendicular to `x_dir`
    z_dir = (to_arc_vec - x_dir * to_arc_vec.dot(x_dir)).normalized()

    split_pln = Plane(origin=origin, x_dir=x_dir, z_dir=z_dir)
    trimmed_connected_edges = [e.split(split_pln) for e in connected_edges]
    typed_trimmed_connected_edges = []
    for trimmed_edge in trimmed_connected_edges:
        if trimmed_edge is None:
            raise ValueError("Invalid geometry to create the end arc")
        assert isinstance(trimmed_edge, Edge)
        typed_trimmed_connected_edges.append(trimmed_edge)  # Make mypy happy

    # Flip the middle point if the user wants the concave solution
    if invert:
        middle_edge_arc_point = voronoi_circle_center * 2 - middle_edge_arc_point

    # Generate the new circular edge
    new_arc = Edge.make_three_point_arc(
        connected_edges_end_points[0],
        middle_edge_arc_point,
        connected_edges_end_points[1],
    )

    # Recover other edges
    other_edges = (
        edge.topo_parent.edges()
        - topo_explore_connected_edges(edge)
        - ShapeList([edge])
    )

    # Rebuild the face
    # Note that the longest wire must be the perimeter and others holes
    face_wires = Wire.combine(
        typed_trimmed_connected_edges + [new_arc] + other_edges
    ).sort_by(SortBy.LENGTH, reverse=True)
    pending_face = Face(face_wires[0], face_wires[1:])

    # Flip the face to match the original parent
    if edge.topo_parent.faces()[0].normal_at() != pending_face.normal_at():
        pending_face = -pending_face

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    # return Sketch(Compound([pending_face]).wrapped)
    return Sketch([pending_face])


def make_face(
    edges: Edge | Iterable[Edge] | None = None, mode: Mode = Mode.ADD
) -> Sketch:
    """Sketch Operation: make_face

    Create a face from the given perimeter edges.

    Args:
        edges (Edge): sequence of perimeter edges. Defaults to all
            sketch pending edges.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildSketch | None = BuildSketch._get_context("make_face")

    if edges is not None:
        outer_edges = flatten_sequence(edges)
    elif context is not None:
        outer_edges = context.pending_edges
    else:
        raise ValueError("No objects to create a face")
    if not outer_edges:
        raise ValueError("No objects to create a hull")
    validate_inputs(context, "make_face", outer_edges)

    pending_face = Face(Wire.combine(outer_edges)[0])
    if pending_face.normal_at().Z < 0:  # flip up-side-down faces
        pending_face = -pending_face

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    return Sketch(Compound([pending_face]).wrapped)


def make_hull(
    edges: Edge | Iterable[Edge] | None = None, mode: Mode = Mode.ADD
) -> Sketch:
    """Sketch Operation: make_hull

    Create a face from the convex hull of the given edges

    Args:
        edges (Edge, optional): sequence of edges to hull. Defaults to all
            sketch pending edges.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildSketch | None = BuildSketch._get_context("make_hull")

    if edges is not None:
        hull_edges = flatten_sequence(edges)
    elif context is not None:
        hull_edges = context.pending_edges
        if context.sketch_local is not None:
            hull_edges.extend(context.sketch_local.edges())
    else:
        raise ValueError("No objects to create a hull")
    if not hull_edges:
        raise ValueError("No objects to create a hull")

    validate_inputs(context, "make_hull", hull_edges)

    pending_face = Face(Wire.make_convex_hull(hull_edges))
    if pending_face.normal_at().Z < 0:  # flip up-side-down faces
        pending_face = -pending_face

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    return Sketch(Compound([pending_face]).wrapped)


def trace(
    lines: Curve | Edge | Wire | Iterable[Curve | Edge | Wire] | None = None,
    line_width: float = 1,
    mode: Mode = Mode.ADD,
) -> Sketch:
    """Sketch Operation: trace

    Convert edges, wires or pending edges into faces by sweeping a perpendicular line along them.

    Args:
        lines (Curve | Edge | Wire | Iterable[Curve | Edge | Wire]], optional): lines to
            trace. Defaults to sketch pending edges.
        line_width (float, optional): Defaults to 1.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: No objects to trace

    Returns:
        Sketch: Traced lines
    """
    context: BuildSketch | None = BuildSketch._get_context("trace")

    if lines is not None:
        trace_lines = flatten_sequence(lines)
        trace_edges = [e for l in trace_lines for e in l.edges()]
    elif context is not None:
        trace_edges = context.pending_edges
    else:
        raise ValueError("No objects to trace")

    # Group the edges into wires to allow for nice transitions
    trace_wires = Wire.combine(trace_edges)

    new_faces: list[Face] = []
    for to_trace in trace_wires:
        trace_pen = to_trace.perpendicular_line(line_width, 0)
        new_faces.extend(
            Shell.sweep(trace_pen, to_trace, transition=Transition.RIGHT).faces()
        )
    if context is not None:
        context._add_to_context(*new_faces, mode=mode)
        context.pending_edges = ShapeList()

    # pylint: disable=no-value-for-parameter
    combined_faces = Face.fuse(*new_faces) if len(new_faces) > 1 else new_faces[0]
    result = (
        Sketch(combined_faces)
        if isinstance(combined_faces, list)
        else Sketch(combined_faces.wrapped)
    )
    return result
