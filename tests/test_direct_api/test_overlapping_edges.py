"""
build123d imports

name: test_overlapping_edges.py
by:   Gumyr
date: November 7, 2026

desc:
    This python module contains tests for the build123d project: the removal
    of overlapping edges from drawing_view. Edge.is_subset_of and Edge.merge,
    which it is built on, are tested in test_edge.py.

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

import unittest

from build123d.build_enums import GeomType
from build123d.topology import one_d
from build123d.geometry import Pos
from build123d.objects_part import Box
from build123d.operations_generic import fillet
from build123d.topology import Compound, Edge, Solid, Wire

TOL = 1e-5


def raw_drawing_view(shape, *args, **kwargs):
    """drawing_view with the removal of overlapping edges switched off"""
    keep = one_d._drop_subset_edges, one_d._merge_edges
    one_d._drop_subset_edges = lambda edges, references, tolerance: edges
    one_d._merge_edges = lambda edges, tolerance: edges
    try:
        return shape.drawing_view(*args, **kwargs)
    finally:
        one_d._drop_subset_edges, one_d._merge_edges = keep


def covered(edges, others):
    """Does every point sampled along edges lie on one of others?"""
    return all(
        any(o.distance_to(e @ (i / 20)) <= TOL for o in others)
        for e in edges
        for i in range(21)
    )


def count_duplicates(edges, references=None):
    """How many edges lie entirely on another (on a reference if given)"""
    count = 0
    for i, edge in enumerate(edges):
        others = references if references is not None else edges[:i] + edges[i + 1 :]
        if others and covered([edge], others):
            count += 1
    return count


class TestDrawingViewOverlaps(unittest.TestCase):
    """The probe cases of issue #1569"""

    @classmethod
    def setUpClass(cls):
        """Views of each probe case, with and without overlap removal"""
        block = fillet(Box(40, 30, 10).edges(), 2)
        unfused = Compound([Box(10, 10, 10), Pos(10, 0, 0) * Box(10, 10, 10)])
        cls.cases = {
            "filleted block, top": (block, (0, 0, 100), (0, 1, 0)),
            "filleted block, front": (block, (0, -100, 0), (0, 0, 1)),
            "unfused compound, top": (unfused, (0, 0, 100), (0, 1, 0)),
            "unfused compound, front": (unfused, (0, -100, 0), (0, 0, 1)),
            "unfused compound, iso": (unfused, (-50, -60, 70), (0, 0, 1)),
            "box, top": (Box(10, 10, 10), (0, 0, 100), (0, 1, 0)),
        }
        cls.views = {
            name: (
                raw_drawing_view(shape, viewpoint, up, look_at=(0, 0, 0)),
                shape.drawing_view(viewpoint, up, look_at=(0, 0, 0)),
            )
            for name, (shape, viewpoint, up) in cls.cases.items()
        }

    def test_kernel_output_has_overlaps(self):
        """The kernel's own output has overlapping edges"""
        # Guards the tests below: the kernel does return overlapping edges
        for name in ("filleted block, top", "filleted block, front"):
            (visible, hidden), _ = self.views[name]
            self.assertGreater(count_duplicates(visible), 0, name)
            self.assertGreater(count_duplicates(hidden, visible), 0, name)
        (visible, _), _ = self.views["unfused compound, top"]
        self.assertGreater(count_duplicates(visible), 0)

    def test_no_duplicates(self):
        """No edge lies on another in any view"""
        for name, (_, (visible, hidden)) in self.views.items():
            with self.subTest(name):
                self.assertEqual(count_duplicates(visible), 0)
                self.assertEqual(count_duplicates(hidden), 0)
                self.assertEqual(count_duplicates(hidden, visible), 0)

    def test_drawn_geometry_unchanged(self):
        """The lines drawn are the same before and after"""
        for name, ((raw_vis, raw_hid), (visible, hidden)) in self.views.items():
            with self.subTest(name):
                self.assertTrue(covered(raw_vis, visible))
                self.assertTrue(covered(visible, raw_vis))
                self.assertTrue(covered(raw_hid, list(hidden) + list(visible)))
                self.assertTrue(covered(hidden, raw_hid))

    def test_counts(self):
        """Edge counts of each view"""
        expected = {
            "filleted block, top": (12, 0),
            "filleted block, front": (12, 0),
            "unfused compound, top": (5, 0),
            "unfused compound, front": (5, 0),
            "unfused compound, iso": (11, 5),
            "box, top": (4, 0),
        }
        for name, (_, (visible, hidden)) in self.views.items():
            with self.subTest(name):
                self.assertEqual((len(visible), len(hidden)), expected[name])

    def test_join_between_unfused_parts_drawn_once(self):
        """Where unfused parts meet, one edge"""
        _, (visible, _) = self.views["unfused compound, front"]
        # the view is drawn in its own plane: x to the right, y up
        join = Edge.make_line((5, -5), (5, 5))
        on_join = [e for e in visible if covered([e], [join])]
        self.assertEqual(len(on_join), 1)
        # the top and bottom lines run across both parts as one edge each
        self.assertEqual(
            sorted(round(e.length, 6) for e in visible), [10, 10, 10, 20, 20]
        )

    def test_split_edges_merged(self):
        """Edges split by hidden-line removal are rejoined"""
        # the kernel splits the circles of a cylinder at the silhouette
        cylinder = Solid.make_cylinder(2, 10)
        visible, hidden = cylinder.drawing_view((-20, 20, 20))
        raw_visible, raw_hidden = raw_drawing_view(cylinder, (-20, 20, 20))
        self.assertGreater(len(raw_visible), len(visible))
        self.assertEqual(len(visible), 4)
        self.assertEqual(len(hidden), 1)
        self.assertTrue(covered(raw_visible, visible))
        self.assertTrue(covered(raw_hidden, hidden))

    def test_every_drawing_view(self):
        """Every drawing_view implementation removes overlaps"""
        box = Solid.make_box(10, 10, 10)
        for shape in (box, box.faces().sort_by()[-1], box.edges()[0], Compound([box])):
            with self.subTest(type(shape).__name__):
                visible, hidden = shape.drawing_view((0, 0, 100), (0, 1, 0))
                self.assertEqual(count_duplicates(visible), 0)
                self.assertEqual(count_duplicates(hidden, visible), 0)

    def test_edges_are_analytic(self):
        """Straight and elliptical edges do not come back as splines"""
        # the kernel returns the sloping edges of this loft as straight splines
        tapered = Solid.loft([Wire.make_rect(10, 10), Pos(Z=10) * Wire.make_circle(4)])
        visible, hidden = tapered.drawing_view((0, 0, 100), (0, 1, 0))
        self.assertEqual(len(hidden), 0)
        kinds = [e.geom_type for e in visible]
        self.assertEqual(kinds.count(GeomType.LINE), 8)
        self.assertEqual(kinds.count(GeomType.ELLIPSE), 1)

        # a silhouette that is none of those stays a spline
        torus = Solid.make_torus(10, 3)
        visible, _ = torus.drawing_view((100, -100, 100))
        self.assertTrue(all(e.geom_type == GeomType.BSPLINE for e in visible))


if __name__ == "__main__":
    unittest.main()
