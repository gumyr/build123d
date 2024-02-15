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
from typing import Iterable, Union
from build123d.build_enums import Mode, SortBy
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    ShapeList,
    Wire,
    Sketch,
    topo_explore_connected_edges,
    topo_explore_common_vertex,
    TOLERANCE,
)
from build123d.geometry import Vector
from build123d.build_common import flatten_sequence, validate_inputs
from build123d.build_sketch import BuildSketch
from build123d.objects_curve import ThreePointArc
from scipy.spatial import Voronoi


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
        (Sketch, Vector, float): A tuple where the first value is the modified shape, the second the
        geometric center of the arc, and the third the radius of the arc

    """
    context: BuildSketch = BuildSketch._get_context("full_round")

    if not isinstance(edge, Edge):
        raise ValueError("A single Edge must be provided")
    validate_inputs(context, "full_round", edge)

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
    best_three = [(float("inf"), None), (float("inf"), None), (float("inf"), None)]

    for i, v in enumerate(voronoi_vertices):
        distances = [edge_group[i].distance_to(v) for i in range(3)]
        avg_distance = sum(distances) / 3
        differences = max(abs(dist - avg_distance) for dist in distances)

        # Check if this delta is among the three smallest and update best_three if so
        # Compare with the largest delta in the best three
        if differences < best_three[-1][0]:
            # Replace the last element with the new one
            best_three[-1] = (differences, i)
            # Sort the list to keep the smallest deltas first
            best_three.sort(key=lambda x: x[0])

    # Extract the indices of the best three and average them
    best_indices = [x[1] for x in best_three]
    voronoi_circle_center = sum(voronoi_vertices[i] for i in best_indices) / 3

    # Determine where the connected edges intersect with the largest empty circle
    connected_edges_end_points = [
        e.distance_to_with_closest_points(voronoi_circle_center)[1]
        for e in connected_edges
    ]
    middle_edge_arc_point = edge.distance_to_with_closest_points(voronoi_circle_center)[
        1
    ]
    if invert:
        middle_edge_arc_point = voronoi_circle_center * 2 - middle_edge_arc_point
    connected_edges_end_params = [
        e.param_at_point(connected_edges_end_points[i])
        for i, e in enumerate(connected_edges)
    ]
    for param in connected_edges_end_params:
        if not (0.0 < param < 1.0):
            raise ValueError("Invalid geometry to create the end arc")

    common_vertex_points = [
        Vector(topo_explore_common_vertex(edge, e)) for e in connected_edges
    ]
    common_vertex_params = [
        e.param_at_point(common_vertex_points[i]) for i, e in enumerate(connected_edges)
    ]

    # Trim the connected edges to end at the closest points to the circle center
    trimmed_connected_edges = [
        e.trim(*sorted([1.0 - common_vertex_params[i], connected_edges_end_params[i]]))
        for i, e in enumerate(connected_edges)
    ]
    # Record the position of the newly trimmed connected edges to build the arc
    # accurately
    trimmed_end_points = []
    for i in range(2):
        if (
            trimmed_connected_edges[i].position_at(0)
            - connected_edges[i].position_at(0)
        ).length < TOLERANCE:
            trimmed_end_points.append(trimmed_connected_edges[i].position_at(1))
        else:
            trimmed_end_points.append(trimmed_connected_edges[i].position_at(0))

    # Generate the new circular edge
    new_arc = Edge.make_three_point_arc(
        trimmed_end_points[0],
        middle_edge_arc_point,
        trimmed_end_points[1],
    )

    # Recover other edges
    other_edges = edge.topo_parent.edges() - topo_explore_connected_edges(edge) - [edge]

    # Rebuild the face
    # Note that the longest wire must be the perimeter and others holes
    face_wires = Wire.combine(
        trimmed_connected_edges + [new_arc] + other_edges
    ).sort_by(SortBy.LENGTH, reverse=True)
    pending_face = Face(face_wires[0], face_wires[1:])

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    # return Sketch(Compound([pending_face]).wrapped)
    return Sketch([pending_face]), new_arc.arc_center, new_arc.radius


def make_face(
    edges: Union[Edge, Iterable[Edge]] = None, mode: Mode = Mode.ADD
) -> Sketch:
    """Sketch Operation: make_face

    Create a face from the given perimeter edges.

    Args:
        edges (Edge): sequence of perimeter edges. Defaults to all
            sketch pending edges.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildSketch = BuildSketch._get_context("make_face")

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
    edges: Union[Edge, Iterable[Edge]] = None, mode: Mode = Mode.ADD
) -> Sketch:
    """Sketch Operation: make_hull

    Create a face from the convex hull of the given edges

    Args:
        edges (Edge, optional): sequence of edges to hull. Defaults to all
            sketch pending edges.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildSketch = BuildSketch._get_context("make_hull")

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
    lines: Union[Curve, Edge, Wire, Iterable[Union[Curve, Edge, Wire]]] = None,
    line_width: float = 1,
    mode: Mode = Mode.ADD,
) -> Sketch:
    """Sketch Operation: trace

    Convert edges, wires or pending edges into faces by sweeping a perpendicular line along them.

    Args:
        lines (Union[Curve, Edge, Wire, Iterable[Union[Curve, Edge, Wire]]], optional): lines to
            trace. Defaults to sketch pending edges.
        line_width (float, optional): Defaults to 1.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: No objects to trace

    Returns:
        Sketch: Traced lines
    """
    context: BuildSketch = BuildSketch._get_context("trace")

    if lines is not None:
        trace_lines = flatten_sequence(lines)
        trace_edges = [e for l in trace_lines for e in l.edges()]
    elif context is not None:
        trace_edges = context.pending_edges
    else:
        raise ValueError("No objects to trace")

    new_faces = []
    for edge in trace_edges:
        trace_pen = edge.perpendicular_line(line_width, 0)
        new_faces.extend(Face.sweep(trace_pen, edge).faces())
    if context is not None:
        context._add_to_context(*new_faces, mode=mode)
        context.pending_edges = ShapeList()

    combined_faces = Face.fuse(*new_faces) if len(new_faces) > 1 else new_faces[0]
    return Sketch(combined_faces.wrapped)
