"""
build123d topology

name: kernel.py
by:   Gumyr
date: September 10, 2026

desc:
    Helpers for the kernel's own containers, with no dependency on the rest
    of build123d so that any module in the topology package can use them.

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

from OCP.TopoDS import TopoDS_Shape
from OCP.TopTools import TopTools_ListOfShape


def list_shapes(shapes: TopTools_ListOfShape) -> list[TopoDS_Shape]:
    """A kernel list as a Python list.

    Iterating a ``TopTools_ListOfShape`` through its Python protocol costs
    over a millisecond per list, even an empty one; popping a copy of it
    from the front costs microseconds.
    """
    found: list[TopoDS_Shape] = []
    remaining = TopTools_ListOfShape()
    remaining.Assign(shapes)
    while not remaining.IsEmpty():
        found.append(remaining.First())
        remaining.RemoveFirst()
    return found
