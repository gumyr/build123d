"""
build123d Pack

name: pack.py
by:   fischman
date: November 9th 2023

desc:
    Utility code for packing objects in a squarish 2D area.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Collection, Optional, cast

from build123d import Location, Shape, Pos


def _pack2d(
    objects: Collection[object],
    width_fn: Callable[[object], float],
    length_fn: Callable[[object], float],
) -> Collection[tuple[float, float]]:
    """Takes an iterable of objects to pack into a square(ish) 2D
    arrangement, and return a list of (x,y) locations to place each to
    achieve the packing.
    Based on https://codeincomplete.com/articles/bin-packing/ and
    implemented as a straight-forward port of
    https://github.com/jakesgordon/bin-packing/blob/master/js/packer.growing.js
    """

    @dataclass
    class _Node:
        used: bool = False
        x: float = 0
        y: float = 0
        w: float = 0
        h: float = 0
        down: Optional["_Node"] = None
        right: Optional["_Node"] = None

    def find_node(start, w, h):
        if start.used:
            return find_node(start.right, w, h) or find_node(start.down, w, h)
        if o[1] <= start.w and o[2] <= start.h:
            return start
        return None

    def split_node(node, w, h):
        assert not node.used
        node.used = True
        node.down = _Node(x=node.x, y=node.y + h, w=node.w, h=node.h - h)
        node.right = _Node(x=node.x + w, y=node.y, w=node.w - w, h=h)
        return node

    def grow_node(w, h):
        nonlocal root
        can_grow_down = w <= root.w
        can_grow_right = h <= root.h
        should_grow_right = can_grow_right and (root.h >= (root.w + w))
        should_grow_down = can_grow_down and (root.w >= (root.h + h))
        if should_grow_right:
            return grow_right(w, h)
        if should_grow_down:
            return grow_down(w, h)
        if can_grow_right:
            return grow_right(w, h)
        if can_grow_down:
            return grow_down(w, h)
        assert False, f"Failed to grow! root: {root}, w: {w}, h: {h}"

    def grow_right(w, h):
        nonlocal root
        root = _Node(
            used=True,
            x=0,
            y=0,
            w=root.w + w,
            h=root.h,
            down=root,
            right=_Node(x=root.w, w=w, h=root.h),
        )
        node = find_node(root, w, h)
        assert node, "Failed to grow right! root: {root}, w: {w}, h: {h}"
        return split_node(node, w, h)

    def grow_down(w, h):
        nonlocal root
        root = _Node(
            used=True,
            x=0,
            y=0,
            w=root.w,
            h=root.h + h,
            down=_Node(y=root.h, w=root.w, h=h),
            right=root,
        )
        node = find_node(root, w, h)
        assert node, "Failed to grow down! root: {root}, w: {w}, h: {h}"
        return split_node(node, w, h)

    assert len(objects) > 0
    sorted_objects = sorted(
        [(i, width_fn(o), length_fn(o)) for (i, o) in enumerate(objects)],
        key=lambda d: min(d[1], d[2]),
        reverse=True,
    )
    sorted_objects = sorted(sorted_objects, key=lambda d: max(d[1], d[2]), reverse=True)
    root = _Node(False, w=sorted_objects[0][1], h=sorted_objects[0][2])
    translations = []
    for o in sorted_objects:
        node = find_node(root, o[1], o[2])
        if node:
            node = split_node(node, o[1], o[2])
        else:
            node = grow_node(o[1], o[2])
        translations.append((o[0], node.x, node.y))
    return [(t[1], t[2]) for t in sorted(translations, key=lambda t: t[0])]


def pack(objects: Collection[Shape], padding: float, align_z: bool = False) -> Collection[Shape]:
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
        Location((t[0] - o.bounding_box().min.X, t[1] - o.bounding_box().min.Y, 0)) * Pos((0, 0, -o.bounding_box().min.Z if align_z else 0)) * o
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
