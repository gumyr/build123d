"""
build123d.topology package

name: __init__.py
by:   Gumyr
date: January 07, 2025

desc:
    This package contains modules for representing and manipulating 3D geometric shapes,
    including operations on vertices, edges, faces, solids, and composites.
    The package provides foundational classes to work with 3D objects, and methods to
    manipulate and analyze those objects.

license:

    Copyright 2025 Gumyr

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

from .shape_core import (
    Shape,
    Comparable,
    ShapePredicate,
    GroupBy,
    ShapeList,
    Joint,
    SkipClean,
    BoundBox,
    downcast,
    fix,
    unwrap_topods_compound,
)
from .utils import (
    tuplify,
    isclose_b,
    polar,
    delta,
    new_edges,
    find_max_dimension,
)
from .zero_d import Vertex, topo_explore_common_vertex
from .one_d import (
    Edge,
    Wire,
    Mixin1D,
    edges_to_wires,
    topo_explore_connected_edges,
    offset_topods_face,
    topo_explore_connected_faces,
)
from .two_d import Face, Shell, Mixin2D, sort_wires_by_build_order
from .three_d import Solid, Mixin3D, DraftAngleError
from .composite import Compound, Curve, Sketch, Part

__all__ = [
    "Shape",
    "Comparable",
    "DraftAngleError",
    "ShapePredicate",
    "GroupBy",
    "ShapeList",
    "Joint",
    "SkipClean",
    "BoundBox",
    "downcast",
    "fix",
    "unwrap_topods_compound",
    "tuplify",
    "isclose_b",
    "polar",
    "delta",
    "new_edges",
    "find_max_dimension",
    "Vertex",
    "topo_explore_common_vertex",
    "Edge",
    "Wire",
    "edges_to_wires",
    "offset_topods_face",
    "topo_explore_connected_edges",
    "topo_explore_connected_faces",
    "Face",
    "Shell",
    "sort_wires_by_build_order",
    "Solid",
    "Compound",
    "Curve",
    "Sketch",
    "Part",
]
