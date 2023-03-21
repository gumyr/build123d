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
from build123d.build_enums import Mode
from build123d.topology import Compound, Edge, Face, ShapeList, Wire, Sketch
from build123d.build_common import validate_inputs
from build123d.build_sketch import BuildSketch


def make_face(*edges: Edge, mode: Mode = Mode.ADD) -> Sketch:
    """Sketch Operation: make_face

    Create a face from the given perimeter edges.

    Args:
        edges (Edge): sequence of perimeter edges
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildSketch = BuildSketch._get_context(None)
    validate_inputs(context, None, edges)

    if edges is None:
        if context is None:
            raise ValueError("No objects to create a convex hull")
        outer_edges = context.pending_edges
    else:
        outer_edges = list(edges)

    pending_face = Face.make_from_wires(Wire.combine(outer_edges)[0])

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    return Sketch(Compound.make_compound([pending_face]).wrapped)


def make_hull(*edges: Edge, mode: Mode = Mode.ADD) -> Sketch:
    """Sketch Operation: make_hull

    Create a face from the convex hull of the given edges

    Args:
        edges (Edge, optional): sequence of edges to hull. Defaults to all
            pending and sketch edges.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildSketch = BuildSketch._get_context(None)
    validate_inputs(context, None, edges)

    if edges is None:
        if context is None:
            raise ValueError("No objects to create a convex hull")
        hull_edges = context.pending_edges.extend(context.sketch_local.edges())
    else:
        hull_edges = list(edges)

    pending_face = Face.make_from_wires(Wire.make_convex_hull(hull_edges))

    if context is not None:
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()

    return Sketch(Compound.make_compound([pending_face]).wrapped)
