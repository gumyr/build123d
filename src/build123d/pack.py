"""
build123d Pack

name: pack.py
by:   fischman
date: November 9th 2023

desc:
    Utilities for arranging Shapes in a compact, non-overlapping 2D layout.
    The public ``pack`` function positions Shapes in Plane.XY, while the
    dependency-free rectangle-packing algorithm is implemented in pack_utils.

license:

    Copyright 2023 fischman

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

from collections.abc import Collection
from typing import cast

from build123d.geometry import Location, Pos
from build123d.pack_utils import _pack2d
from build123d.topology.shape_core import Shape


def pack(
    objects: Collection[Shape], padding: float, align_z: bool = False
) -> Collection[Shape]:
    """Pack objects in a squarish area in Plane.XY.

    Args:
        objects (Collection[Shape]): objects to arrange
        padding (float): space between objects
        align_z (bool, optional): align shape bottoms to Plane.XY. Defaults to False.

    Returns:
        Collection[Shape]: rearranged objects
    """

    bounding_boxes = {o: o.bounding_box().size + (padding, padding) for o in objects}
    translations = _pack2d(
        objects,
        width_fn=lambda o: bounding_boxes[cast(Shape, o)].X,
        length_fn=lambda o: bounding_boxes[cast(Shape, o)].Y,
    )
    translated = [
        Location((t[0] - o.bounding_box().min.X, t[1] - o.bounding_box().min.Y, 0))
        * Pos((0, 0, -o.bounding_box().min.Z if align_z else 0))
        * o
        for (o, t) in zip(objects, translations)
    ]

    # Assert the packing didn't cause any overlaps.
    def _overlapping(bb1, bb2):
        # Boundaries of the intersection of the two bounding boxes.
        min_x = max(bb1.min.X, bb2.min.X)
        min_y = max(bb1.min.Y, bb2.min.Y)
        max_x = min(bb1.max.X, bb2.max.X)
        max_y = min(bb1.max.Y, bb2.max.Y)
        return max_x > min_x and max_y > min_y

    bb = [t.bounding_box() for t in translated]
    for i, bb_i in enumerate(bb):
        for j, bb_j in enumerate(bb[i + 1 :]):
            assert not _overlapping(
                bb_i, bb_j
            ), f"Objects at indexes {i} and {j} overlap!"
    return translated
