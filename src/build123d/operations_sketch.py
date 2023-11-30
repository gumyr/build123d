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
from build123d.build_enums import Mode
from build123d.topology import Compound, Curve, Edge, Face, ShapeList, Wire, Sketch
from build123d.build_common import flatten_sequence, validate_inputs
from build123d.build_sketch import BuildSketch


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

    pending_face = Face.make_from_wires(Wire.combine(outer_edges)[0])
    if pending_face.normal_at().Z < 0:  # flip up-side-down faces
        pending_face = -pending_face

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    return Sketch(Compound.make_compound([pending_face]).wrapped)


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

    pending_face = Face.make_from_wires(Wire.make_convex_hull(hull_edges))
    if pending_face.normal_at().Z < 0:  # flip up-side-down faces
        pending_face = -pending_face

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    return Sketch(Compound.make_compound([pending_face]).wrapped)


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

    return Sketch(Compound.make_compound(new_faces).wrapped)
