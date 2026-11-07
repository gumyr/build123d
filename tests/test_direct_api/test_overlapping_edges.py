"""
build123d imports

name: test_overlapping_edges.py
by:   Gumyr
date: November 7, 2026

desc:
    This python module contains tests for the build123d project: the subset
    test and merge of edges, and their use in drawing_view to remove
    overlapping edges.

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

import math
import unittest

from build123d.topology import one_d
from build123d.build_enums import GeomType
from build123d.geometry import Plane, Pos, Vector
from build123d.objects_part import Box
from build123d.operations_generic import fillet
from build123d.topology import Compound, Edge, Solid, Wire

TOL = 1e-5


def arc(radius, start, end, plane=Plane.XY):
    """Arc of a circle centred on the plane's origin, angles in degrees"""
    return Edge.make_circle(radius, plane, start_angle=start, end_angle=end)


class TestIsSubsetOfLines(unittest.TestCase):
    """Edge.is_subset_of for two lines"""

    def setUp(self):
        """A line along the x axis from 0 to 10"""
        self.line = Edge.make_line((0, 0), (10, 0))

    def test_inside(self):
        """A piece of a line is a subset of it"""
        self.assertTrue(Edge.make_line((2, 0), (5, 0)).is_subset_of(self.line))

    def test_container_is_not_a_subset(self):
        """A line is not a subset of a piece of it"""
        self.assertFalse(self.line.is_subset_of(Edge.make_line((2, 0), (5, 0))))

    def test_identical(self):
        """Identical lines are subsets of each other"""
        self.assertTrue(self.line.is_subset_of(Edge.make_line((0, 0), (10, 0))))

    def test_reversed(self):
        """Direction doesn't matter"""
        self.assertTrue(Edge.make_line((5, 0), (2, 0)).is_subset_of(self.line))
        self.assertTrue(self.line.is_subset_of(Edge.make_line((10, 0), (0, 0))))

    def test_sharing_an_end(self):
        """A piece that ends where the line ends is a subset"""
        self.assertTrue(Edge.make_line((0, 0), (4, 0)).is_subset_of(self.line))
        self.assertTrue(Edge.make_line((10, 0), (6, 0)).is_subset_of(self.line))

    def test_beyond_the_end(self):
        """A piece running past the end is not a subset"""
        self.assertFalse(Edge.make_line((8, 0), (12, 0)).is_subset_of(self.line))

    def test_collinear_but_apart(self):
        """A collinear line beyond the end is not a subset"""
        self.assertFalse(Edge.make_line((11, 0), (12, 0)).is_subset_of(self.line))

    def test_parallel_offset(self):
        """A parallel line off to the side is not a subset"""
        self.assertFalse(Edge.make_line((2, 1), (5, 1)).is_subset_of(self.line))

    def test_tolerance(self):
        """Deviations within tolerance are allowed"""
        near = Edge.make_line((2, 1e-7), (5, -1e-7))
        off = Edge.make_line((2, 1e-3), (5, 1e-3))
        self.assertTrue(near.is_subset_of(self.line))
        self.assertFalse(off.is_subset_of(self.line))
        self.assertTrue(off.is_subset_of(self.line, tolerance=1e-2))
        past = Edge.make_line((2, 0), (10.001, 0))
        self.assertFalse(past.is_subset_of(self.line))
        self.assertTrue(past.is_subset_of(self.line, tolerance=1e-2))

    def test_in_3d(self):
        """Lines in any direction"""
        line = Edge.make_line((0, 0, 0), (3, 4, 12))
        piece = Edge.make_line((0.6, 0.8, 2.4), (1.5, 2, 6))
        self.assertTrue(piece.is_subset_of(line))


class TestIsSubsetOfArcs(unittest.TestCase):
    """Edge.is_subset_of for two circular arcs"""

    def test_arc_of_full_circle(self):
        """An arc is a subset of its full circle, not the other way"""
        full = Edge.make_circle(2)
        self.assertTrue(arc(2, 30, 120).is_subset_of(full))
        self.assertFalse(full.is_subset_of(arc(2, 30, 120)))

    def test_full_circles(self):
        """Full circles are subsets of each other, either way round"""
        self.assertTrue(Edge.make_circle(2).is_subset_of(Edge.make_circle(2)))
        self.assertTrue(
            Edge.make_circle(2).is_subset_of(Edge.make_circle(2, Plane.XY.reverse()))
        )

    def test_inside_and_outside_the_range(self):
        """The angular range must lie within the other's"""
        container = arc(2, 30, 120)
        self.assertTrue(arc(2, 45, 90).is_subset_of(container))
        self.assertTrue(arc(2, 30, 120).is_subset_of(container))
        self.assertFalse(arc(2, 20, 90).is_subset_of(container))
        self.assertFalse(arc(2, 130, 150).is_subset_of(container))

    def test_wrap_around(self):
        """Ranges that pass through zero degrees"""
        container = arc(2, 300, 60)
        self.assertTrue(arc(2, 350, 20).is_subset_of(container))
        self.assertTrue(arc(2, 310, 340).is_subset_of(container))
        self.assertTrue(arc(2, 10, 50).is_subset_of(container))
        self.assertFalse(arc(2, 50, 70).is_subset_of(container))
        self.assertFalse(arc(2, 90, 280).is_subset_of(container))
        # an arc wrapping past zero inside an arc that doesn't
        self.assertFalse(arc(2, 350, 20).is_subset_of(arc(2, 10, 340)))

    def test_reversed(self):
        """Direction doesn't matter"""
        container = arc(2, 30, 120)
        piece = arc(2, 45, 90).reversed()
        self.assertTrue(piece.is_subset_of(container))
        self.assertTrue(arc(2, 45, 90).is_subset_of(container.reversed()))

    def test_opposite_plane_normal(self):
        """Arcs made on planes facing opposite ways"""
        # 0 to 30 degrees clockwise around +Z is 330 to 360 counter clockwise
        piece = arc(2, 0, 30, Plane.XY.reverse())
        self.assertTrue(piece.is_subset_of(arc(2, 300, 60)))
        self.assertTrue(piece.is_subset_of(arc(2, 320, 0)))
        self.assertFalse(piece.is_subset_of(arc(2, 0, 90)))

    def test_different_circles(self):
        """Centre, radius and plane must all match"""
        piece = arc(2, 45, 90)
        self.assertFalse(piece.is_subset_of(arc(2.1, 30, 120)))
        self.assertFalse(piece.is_subset_of(arc(2, 30, 120, Plane.XY.offset(1))))
        moved = Pos(0.5, 0, 0) * arc(2, 30, 120)
        self.assertFalse(piece.is_subset_of(moved))
        tilted = arc(2, 30, 120, Plane.XY.rotated((0, 10, 0)))
        self.assertFalse(piece.is_subset_of(tilted))

    def test_tolerance(self):
        """Deviations within tolerance are allowed"""
        container = arc(2, 30, 120)
        self.assertTrue(arc(2 + 1e-7, 45, 90).is_subset_of(container))
        self.assertFalse(arc(2 + 1e-3, 45, 90).is_subset_of(container))
        self.assertTrue(arc(2 + 1e-3, 45, 90).is_subset_of(container, tolerance=1e-2))


class TestIsSubsetOfSampled(unittest.TestCase):
    """Edge.is_subset_of where it falls back on sampling"""

    def test_spline_pieces(self):
        """A piece of a spline is a subset of it"""
        spline = Edge.make_spline([(0, 0), (1, 1), (2, 0), (3, 1)])
        self.assertTrue(spline.trim(0.2, 0.6).is_subset_of(spline))
        self.assertTrue(spline.trim(0.2, 0.6).reversed().is_subset_of(spline))
        self.assertFalse(spline.is_subset_of(spline.trim(0.2, 0.6)))

    def test_ellipse_arcs(self):
        """Ellipses, which have no analytic fast path"""
        ellipse = Edge.make_ellipse(4, 2)
        piece = Edge.make_ellipse(4, 2, start_angle=20, end_angle=80)
        self.assertEqual(piece.geom_type, GeomType.ELLIPSE)
        self.assertTrue(piece.is_subset_of(ellipse))
        self.assertFalse(Edge.make_ellipse(4, 2.1).is_subset_of(ellipse))

    def test_straight_bspline_and_line(self):
        """A straight BSPLINE and a line"""
        # a circle seen edge-on comes back from the kernel as a straight BSPLINE
        line = Edge.make_line((0, 0), (10, 0))
        straight = Edge.make_spline([(2, 0), (4, 0), (6, 0)])
        self.assertEqual(straight.geom_type, GeomType.BSPLINE)
        self.assertTrue(straight.is_subset_of(line))
        self.assertFalse(line.is_subset_of(straight))

    def test_arc_and_bspline(self):
        """A BSPLINE through points of a circle and the circle"""
        circle = Edge.make_circle(2)
        points = [arc(2, 20, 80) @ (i / 8) for i in range(9)]
        on_circle = Edge.make_spline(points)
        self.assertEqual(on_circle.geom_type, GeomType.BSPLINE)
        self.assertTrue(on_circle.is_subset_of(circle, tolerance=1e-3))

    def test_mismatched_types(self):
        """Different curves that meet are not subsets"""
        line = Edge.make_line((0, 0), (10, 0))
        self.assertFalse(arc(2, 0, 90).is_subset_of(line))
        self.assertFalse(Edge.make_line((0, 0), (1, 1)).is_subset_of(arc(2, 0, 90)))
        # a chord of an arc is close to it but not on it
        chord = Edge.make_line(arc(2, 0, 10) @ 0, arc(2, 0, 10) @ 1)
        self.assertFalse(chord.is_subset_of(arc(2, 0, 10)))

    def test_wires(self):
        """Wires on either side of the test"""
        wire = Wire.make_polygon([(0, 0), (5, 0), (5, 5)], close=False)
        self.assertTrue(Edge.make_line((1, 0), (4, 0)).is_subset_of(wire))
        self.assertTrue(Edge.make_line((5, 0), (5, 3)).is_subset_of(wire))
        self.assertFalse(Edge.make_line((1, 1), (4, 1)).is_subset_of(wire))
        self.assertTrue(wire.is_subset_of(wire))
        self.assertFalse(wire.is_subset_of(Edge.make_line((0, 0), (5, 0))))

    def test_empty(self):
        """Empty edges can't be compared"""
        line = Edge.make_line((0, 0), (1, 0))
        with self.assertRaises(ValueError):
            Edge().is_subset_of(line)
        with self.assertRaises(ValueError):
            line.is_subset_of(Edge())


class TestMergeLines(unittest.TestCase):
    """Edge.merge for two lines"""

    def assert_line(self, edge, start, end):
        """Check edge is a line from start to end"""
        self.assertIsNotNone(edge)
        self.assertEqual(edge.geom_type, GeomType.LINE)
        self.assertAlmostEqual(edge.start_point(), Vector(start), 6)
        self.assertAlmostEqual(edge.end_point(), Vector(end), 6)

    def test_end_to_end(self):
        """Lines meeting end to end become one"""
        merged = Edge.make_line((0, 0), (5, 0)).merge(Edge.make_line((5, 0), (9, 0)))
        self.assert_line(merged, (0, 0), (9, 0))

    def test_overlapping(self):
        """Overlapping lines become one"""
        merged = Edge.make_line((0, 0), (5, 0)).merge(Edge.make_line((3, 0), (8, 0)))
        self.assert_line(merged, (0, 0), (8, 0))

    def test_follows_own_direction(self):
        """The merged line runs the way the first does"""
        merged = Edge.make_line((5, 0), (0, 0)).merge(Edge.make_line((3, 0), (8, 0)))
        self.assert_line(merged, (8, 0), (0, 0))
        merged = Edge.make_line((0, 0), (5, 0)).merge(Edge.make_line((9, 0), (5, 0)))
        self.assert_line(merged, (0, 0), (9, 0))

    def test_subset_returns_container(self):
        """If one line holds the other, it is returned"""
        line = Edge.make_line((0, 0), (10, 0))
        piece = Edge.make_line((2, 0), (5, 0))
        self.assertIs(line.merge(piece), line)
        self.assertIs(piece.merge(line), line)

    def test_gap(self):
        """Lines with a gap between them are not merged"""
        self.assertIsNone(
            Edge.make_line((0, 0), (5, 0)).merge(Edge.make_line((6, 0), (9, 0)))
        )

    def test_not_collinear(self):
        """Lines that meet at an angle or are parallel are not merged"""
        line = Edge.make_line((0, 0), (5, 0))
        self.assertIsNone(line.merge(Edge.make_line((5, 0), (9, 1))))
        self.assertIsNone(line.merge(Edge.make_line((5, 0), (5, 5))))
        self.assertIsNone(line.merge(Edge.make_line((0, 1), (5, 1))))

    def test_tolerance(self):
        """A gap within tolerance counts as touching"""
        line = Edge.make_line((0, 0), (5, 0))
        self.assertIsNone(line.merge(Edge.make_line((5.001, 0), (9, 0))))
        merged = line.merge(Edge.make_line((5.001, 0), (9, 0)), tolerance=1e-2)
        self.assert_line(merged, (0, 0), (9, 0))

    def test_line_and_straight_bspline(self):
        """A line and a straight BSPLINE in line with it"""
        line = Edge.make_line((0, 0), (10, 0))
        straight = Edge.make_spline([(10, 0), (12, 0), (14, 0)])
        for merged in (line.merge(straight), straight.merge(line)):
            self.assertIsNotNone(merged)
            self.assertAlmostEqual(merged.length, 14, 6)
            self.assertTrue(line.is_subset_of(merged))
            self.assertTrue(straight.is_subset_of(merged))

    def test_empty(self):
        """Empty edges can't be merged"""
        line = Edge.make_line((0, 0), (1, 0))
        with self.assertRaises(ValueError):
            Edge().merge(line)
        with self.assertRaises(ValueError):
            line.merge(Edge())


class TestMergeArcs(unittest.TestCase):
    """Edge.merge for two circular arcs"""

    def test_end_to_end(self):
        """Arcs meeting end to end become one arc"""
        merged = arc(2, 0, 90).merge(arc(2, 90, 200))
        self.assertEqual(merged.geom_type, GeomType.CIRCLE)
        self.assertAlmostEqual(merged.length, 2 * math.radians(200), 6)
        self.assertAlmostEqual(merged.start_point(), arc(2, 0, 90) @ 0, 6)

    def test_overlapping(self):
        """Overlapping arcs become one arc"""
        merged = arc(2, 0, 120).merge(arc(2, 90, 200))
        self.assertAlmostEqual(merged.length, 2 * math.radians(200), 6)

    def test_into_full_circle(self):
        """Arcs that close the circle become the full circle"""
        merged = arc(2, 0, 200).merge(arc(2, 180, 360))
        self.assertTrue(merged.is_closed)
        self.assertAlmostEqual(merged.length, 4 * math.pi, 6)

    def test_wrap_around(self):
        """The merged arc may pass through zero degrees"""
        merged = arc(2, 300, 30).merge(arc(2, 20, 60))
        self.assertAlmostEqual(merged.length, 2 * math.radians(120), 6)
        self.assertAlmostEqual(merged.start_point(), arc(2, 300, 30) @ 0, 6)
        self.assertAlmostEqual(merged.end_point(), arc(2, 20, 60) @ 1, 6)

    def test_reversed_and_opposite_normal(self):
        """Arcs running opposite ways around the circle"""
        first = arc(2, 0, 90).reversed()
        # 0 to -60 degrees around +Z
        second = arc(2, 0, 60, Plane.XY.reverse())
        merged = first.merge(second)
        self.assertAlmostEqual(merged.length, 2 * math.radians(150), 6)
        # runs the way the first edge does: clockwise around +Z
        self.assertAlmostEqual(merged.start_point(), first.start_point(), 6)
        self.assertAlmostEqual(merged.end_point(), second.end_point(), 6)

    def test_subset_returns_container(self):
        """If one arc holds the other, it is returned"""
        container = arc(2, 0, 180)
        self.assertIs(container.merge(arc(2, 20, 80)), container)
        self.assertIs(arc(2, 20, 80).merge(container), container)

    def test_gap_and_different_circles(self):
        """Arcs with a gap or of different circles"""
        self.assertIsNone(arc(2, 0, 90).merge(arc(2, 100, 200)))
        self.assertIsNone(arc(2, 0, 90).merge(arc(3, 90, 200)))
        self.assertIsNone(arc(2, 0, 90).merge(arc(2, 90, 200, Plane.XY.offset(1))))

    def test_arc_and_line(self):
        """An arc and a line are not merged"""
        self.assertIsNone(arc(2, 0, 90).merge(Edge.make_line((2, 0), (5, 0))))


class TestMergeSampled(unittest.TestCase):
    """Edge.merge where it falls back on sampling"""

    def test_spline_pieces(self):
        """Pieces of a spline, meeting or overlapping, rejoin"""
        spline = Edge.make_spline([(0, 0), (1, 1), (2, 0), (3, 1)])
        for first, second in [(0, 0.5), (0.5, 1)], [(0, 0.6), (0.4, 1)]:
            merged = spline.trim(*first).merge(spline.trim(*second))
            self.assertIsNotNone(merged)
            self.assertAlmostEqual(merged.length, spline.length, 6)
            self.assertAlmostEqual(merged.start_point(), spline.start_point(), 6)

    def test_ellipse_arcs(self):
        """Arcs of an ellipse close into the full ellipse"""
        first = Edge.make_ellipse(4, 2, start_angle=0, end_angle=100)
        second = Edge.make_ellipse(4, 2, start_angle=100, end_angle=360)
        merged = first.merge(second)
        self.assertTrue(merged.is_closed)
        self.assertAlmostEqual(merged.length, Edge.make_ellipse(4, 2).length, 6)

    def test_ellipse_wrap_around(self):
        """Arcs of an ellipse merge across zero degrees"""
        first = Edge.make_ellipse(4, 2, start_angle=300, end_angle=30)
        second = Edge.make_ellipse(4, 2, start_angle=20, end_angle=60)
        whole = Edge.make_ellipse(4, 2, start_angle=300, end_angle=60)
        for merged in (first.merge(second), second.merge(first)):
            self.assertEqual(merged.geom_type, GeomType.ELLIPSE)
            self.assertAlmostEqual(merged.length, whole.length, 6)
            self.assertAlmostEqual(merged.start_point(), whole.start_point(), 6)
            self.assertAlmostEqual(merged.end_point(), whole.end_point(), 6)

    def test_different_curves(self):
        """Splines that meet but don't share a curve stay apart"""
        spline = Edge.make_spline([(0, 0), (1, 1), (2, 0)])
        other = Edge.make_spline([(2, 0), (3, -1), (4, 0)])
        self.assertIsNone(spline.merge(other))


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


if __name__ == "__main__":
    unittest.main()
