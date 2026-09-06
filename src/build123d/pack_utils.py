"""
build123d Pack Utilities

name: pack_utils.py
by:   fischman
date: November 9th 2023

desc:
    Dependency-free helpers for packing rectangular objects into a compact,
    square-ish two-dimensional layout. These utilities are kept separate from
    the Shape-aware packing API to allow use by topology code without creating
    an import cycle.

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

from collections.abc import Callable, Collection
from dataclasses import dataclass


def _pack2d(
    objects: Collection[object],
    width_fn: Callable[[object], float],
    length_fn: Callable[[object], float],
) -> Collection[tuple[float, float]]:
    """Pack objects into a square-ish two-dimensional arrangement.

    The returned locations correspond to the input order. This implementation is
    based on https://codeincomplete.com/articles/bin-packing/ and a port of
    https://github.com/jakesgordon/bin-packing/blob/master/js/packer.growing.js.
    """

    @dataclass
    class _Node:
        used: bool = False
        x: float = 0
        y: float = 0
        w: float = 0
        h: float = 0
        down: "_Node" | None = None
        right: "_Node" | None = None

    def find_node(start, w, h):
        if start.used:
            return find_node(start.right, w, h) or find_node(start.down, w, h)
        if w <= start.w and h <= start.h:
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
        raise RuntimeError(f"Failed to grow! root: {root}, w: {w}, h: {h}")

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
        assert node, f"Failed to grow right! root: {root}, w: {w}, h: {h}"
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
        assert node, f"Failed to grow down! root: {root}, w: {w}, h: {h}"
        return split_node(node, w, h)

    if not objects:
        raise ValueError("no objects to pack")
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
