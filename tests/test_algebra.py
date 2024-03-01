import math
import unittest
import pytest
from build123d import *
from build123d.topology import Shape


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class ObjectTests(unittest.TestCase):
    """Test adding objects"""

    # Solid

    def test_box(self):
        b = Solid.make_box(1, 2, 3)

        self.assertTrue(isinstance(b, Shape))

        self.assertTupleAlmostEquals(b.center(), (0.5, 1.0, 1.5), 6)
        self.assertTupleAlmostEquals(b.bounding_box().min, (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(b.bounding_box().max, (1.0, 2.0, 3.0), 6)

    # Parts

    def test_box_min(self):
        b = Box(1, 2, 3, align=(Align.MIN, Align.MIN, Align.MIN))

        self.assertTrue(isinstance(b, Part))
        self.assertTrue(isinstance(b, Shape))

        self.assertTupleAlmostEquals(b.center(), (0.5, 1.0, 1.5), 6)
        self.assertTupleAlmostEquals(b.bounding_box().min, (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(b.bounding_box().max, (1.0, 2.0, 3.0), 6)

    def test_box_center(self):
        b = Box(1, 2, 3, align=(Align.CENTER, Align.CENTER, Align.CENTER))

        self.assertTrue(isinstance(b, Part))
        self.assertTrue(isinstance(b, Shape))

        self.assertTupleAlmostEquals(b.center(), (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(b.bounding_box().min, (-0.5, -1.0, -1.5), 6)
        self.assertTupleAlmostEquals(b.bounding_box().max, (0.5, 1.0, 1.5), 6)

    def test_box_max(self):
        b = Box(1, 2, 3, align=(Align.MAX, Align.MAX, Align.MAX))

        self.assertTrue(isinstance(b, Part))
        self.assertTrue(isinstance(b, Shape))

        self.assertTupleAlmostEquals(b.center(), (-0.5, -1.0, -1.5), 6)
        self.assertTupleAlmostEquals(b.bounding_box().min, (-1.0, -2.0, -3.0), 6)
        self.assertTupleAlmostEquals(b.bounding_box().max, (0.0, 0.0, 0.0), 6)

    def test_cylinder_(self):
        s = Cylinder(1, 2)
        self.assertTupleAlmostEquals(s.center(), (0, 0, 0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-1.0, -1.0, -1.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (1.0, 1.0, 1.0), 3)

    def test_cylinder_min(self):
        s = Cylinder(1, 2, align=(Align.MIN, Align.MIN, Align.MIN))
        self.assertTupleAlmostEquals(s.center(), (1, 1, 1), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (0.0, 0.0, 0.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (2.0, 2.0, 2.0), 3)

    def test_cylinder_max(self):
        s = Cylinder(1, 2, align=(Align.MAX, Align.MAX, Align.MAX))
        self.assertTupleAlmostEquals(s.center(), (-1, -1, -1), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-2.0, -2.0, -2.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.0, 0.0, 0.0), 3)

    def test_cylinder_90(self):
        s = Cylinder(1, 2, 90)
        self.assertTupleAlmostEquals(s.center(), (-0.07558681, -0.07558681, 0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-0.5, -0.5, -1.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.5, 0.5, 1.0), 3)

    def test_cylinder_90_min(self):
        s = Cylinder(1, 2, 90, align=Align.MIN)
        self.assertTupleAlmostEquals(s.center(), (0.424413, 0.424413, 1.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (0.0, 0.0, 0.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (1.0, 1.0, 2.0), 3)

    def test_cylinder_90_max(self):
        s = Cylinder(1, 2, 90, align=Align.MAX)
        self.assertTupleAlmostEquals(s.center(), (-0.575586, -0.575586, -1), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-1.0, -1.0, -2.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.0, 0.0, 0.0), 3)

    def test_cone(self):
        s = Cone(1, 0.1, 1)
        self.assertTupleAlmostEquals(s.center(), (0.0, 0.0, -0.2229729), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-1.0, -1.0, -0.5), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (1.0, 1.0, 0.5), 3)

    def test_cone_90(self):
        s = Cone(1, 0.1, 1, 90)
        self.assertTupleAlmostEquals(s.center(), (-0.1814033, -0.1814033, -0.22297), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-0.5, -0.5, -0.5), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.5, 0.5, 0.5), 3)

    def test_cone0(self):
        s = Cone(1, 0, 2)
        self.assertTupleAlmostEquals(s.center(), (0.0, 0.0, -0.5), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-1.0, -1.0, -1.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (1.0, 1.0, 1.0), 3)

    def test_cone0_min(self):
        s = Cone(1, 0, 2, align=(Align.MIN, Align.MIN, Align.MIN))
        self.assertTupleAlmostEquals(s.center(), (1.0, 1.0, 0.5), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (0.0, 0.0, 0.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (2.0, 2.0, 2.0), 3)

    def test_cone0_max(self):
        s = Cone(1, 0, 2, align=Align.MAX)
        self.assertTupleAlmostEquals(s.center(), (-1.0, -1.0, -1.5), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-2.0, -2.0, -2.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.0, 0.0, 0.0), 3)

    def test_sphere(self):
        s = Sphere(1)
        self.assertTupleAlmostEquals(s.center(), (0.0, 0.0, 0.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-1.0, -1.0, -1.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (1.0, 1.0, 1.0), 3)

    def test_sphere_45_90(self):
        s = Sphere(1, arc_size2=45, arc_size3=90)
        self.assertTupleAlmostEquals(s.center(), (-0.1169322, -0.1169322, 0.0966823), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-0.5, -0.5, -0.853553), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.5, 0.5, 0.853553), 3)

    def test_sphere_45_90_min(self):
        s = Sphere(1, arc_size2=45, arc_size3=90, align=Align.MIN)
        self.assertTupleAlmostEquals(s.center(), (0.383068, 0.383068, 0.950235), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (0.0, 0.0, 0.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (1.0, 1.0, 1.707106), 3)

    def test_sphere_45_90_max(self):
        s = Sphere(
            1, arc_size2=45, arc_size3=90, align=(Align.MAX, Align.MAX, Align.MAX)
        )
        self.assertTupleAlmostEquals(s.center(), (-0.616932, -0.616932, -0.756871), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-1.0, -1.0, -1.707106), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.0, 0.0, 0.0), 3)

    def test_torus_(self):
        s = Torus(1, 0.2)
        self.assertTupleAlmostEquals(s.center(), (0.0, 0.0, 0.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-1.2, -1.2, -0.2), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (1.2, 1.2, 0.2), 3)

    def test_torus_min(self):
        s = Torus(1, 0.2, align=(Align.MIN, Align.MIN, Align.MIN))
        self.assertTupleAlmostEquals(s.center(), (1.2, 1.2, 0.2), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (0.0, 0.0, 0.0), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (2.4, 2.4, 0.4), 3)

    def test_torus_max(self):
        s = Torus(1, 0.2, align=Align.MAX)
        self.assertTupleAlmostEquals(s.center(), (-1.2, -1.2, -0.2), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-2.4, -2.4, -0.4), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.0, 0.0, 0.0), 3)

    def test_wedge(self):
        s = Wedge(1, 1, 1, 0.1, 0.1, 0.5, 0.5)
        self.assertTupleAlmostEquals(s.center(), (-0.073076, -0.134615, -0.073077), 3)
        self.assertTupleAlmostEquals(s.bounding_box().min, (-0.5, -0.5, -0.5), 3)
        self.assertTupleAlmostEquals(s.bounding_box().max, (0.5, 0.5, 0.5), 3)

    def test_hole(self):
        obj = Box(10, 10, 10)
        obj -= Hole(3, 10)
        self.assertAlmostEqual(obj.volume, 10**3 - 10 * math.pi * 3**2, 4)

    def test_hole_error(self):
        obj = Box(10, 10, 10)
        with self.assertRaises(ValueError):
            obj -= Hole(3)

    def test_counter_bore_hole(self):
        obj = Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MAX))
        obj -= CounterBoreHole(
            radius=3, depth=3, counter_bore_radius=4, counter_bore_depth=2
        )
        self.assertAlmostEqual(
            obj.volume, 10**3 - 2 * math.pi * 4**2 - 1 * math.pi * 3**2, 4
        )

    def test_counter_bore_hole_error(self):
        obj = Box(10, 10, 10)
        with self.assertRaises(ValueError):
            obj -= CounterBoreHole(3, 6, 2)

    def test_counter_sink_hole(self):
        obj = Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MAX))
        obj -= CounterSinkHole(radius=3, counter_sink_radius=6, depth=3)
        self.assertAlmostEqual(obj.volume, 747.9311207661184, 4)

    def test_counter_sink_hole_error(self):
        obj = Box(10, 10, 10)
        with self.assertRaises(ValueError):
            obj -= CounterSinkHole(3, 6)

    # Face

    def test_rect(self):
        r = Face.make_rect(2, 1)

        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-1.0, -0.5, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (1.0, 0.5, 0.0), 6)

    # Sketch

    def test_rect_min(self):
        r = Rectangle(1, 2, align=(Align.MIN, Align.MIN))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.5, 1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (1.0, 2.0, 0.0), 6)

    def test_rect_center(self):
        r = Rectangle(1, 2, align=(Align.CENTER, Align.CENTER))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-0.5, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (0.5, 1.0, 0.0), 6)

    def test_rect_max(self):
        r = Rectangle(1, 2, align=Align.MAX)

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (-0.5, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-1.0, -2.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (0.0, 0.0, 0.0), 6)

    def test_circle_min(self):
        r = Circle(1, align=(Align.MIN, Align.MIN))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (1.0, 1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (2.0, 2.0, 0.0), 6)

    def test_circle_center(self):
        r = Circle(1, align=(Align.CENTER, Align.CENTER))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-1.0, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (1.0, 1.0, 0.0), 6)

    def test_circle_max(self):
        r = Circle(1, align=Align.MAX)

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (-1.0, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-2.0, -2.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (0.0, 0.0, 0.0), 6)

    def test_ellipse_min(self):
        r = Ellipse(1, 2, align=(Align.MIN, Align.MIN))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (1.0, 2.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (2.0, 4.0, 0.0), 6)

    def test_ellipse_center(self):
        r = Ellipse(1, 2, align=(Align.CENTER, Align.CENTER))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-1.0, -2.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (1.0, 2.0, 0.0), 6)

    def test_ellipse_max(self):
        r = Ellipse(1, 2, align=Align.MAX)

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (-1.0, -2.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-2.0, -4.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (0.0, 0.0, 0.0), 6)

    # further sketches are tested via context mode

    # Curve

    def test_edge(self):
        e = Edge.make_line((1, 2), (4, 4))

        self.assertTrue(isinstance(e, Shape))

        self.assertTupleAlmostEquals(e.center(), (2.5, 3.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 0, (1.0, 2.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 1, (4.0, 4.0, 0.0), 6)

    def test_line(self):
        e = Line((1, 2), (4, 4))

        self.assertTrue(isinstance(e, Shape))

        self.assertTupleAlmostEquals(e.center(), (2.5, 3.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 0, (1.0, 2.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 1, (4.0, 4.0, 0.0), 6)

    # further curves are tested via context mode


class AlgebraTests(unittest.TestCase):
    # Part

    def test_part_plus(self):
        box = Box(1, 2, 3)
        cylinder = Cylinder(0.2, 5)
        last_edges = box.edges()
        result = box + cylinder
        self.assertEqual(len(result.edges() - last_edges), 6)
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .first.center(CenterOf.MASS),
            (0, 0, -2.5),
            6,
        )
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .last.center(CenterOf.MASS),
            (0, 0, 2.5),
            6,
        )
        self.assertTupleAlmostEquals(result.bounding_box().min, (-0.5, -1.0, -2.5), 6)
        self.assertTupleAlmostEquals(result.bounding_box().max, (0.5, 1.0, 2.5), 6)

    def test_part_minus(self):
        box = Box(1, 2, 3)
        cylinder = Cylinder(0.2, 5)
        last_edges = box.edges()
        result = box - cylinder
        self.assertEqual(len(result.edges() - last_edges), 3)
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .first.center(CenterOf.MASS),
            (0, 0, -1.5),
            6,
        )
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .last.center(CenterOf.MASS),
            (0, 0, 1.5),
            6,
        )
        self.assertTupleAlmostEquals(result.bounding_box().min, (-0.5, -1.0, -1.5), 6)
        self.assertTupleAlmostEquals(result.bounding_box().max, (0.5, 1.0, 1.5), 6)

    def test_part_and(self):
        box = Box(1, 2, 3)
        cylinder = Cylinder(0.2, 5)
        last_edges = box.edges()
        result = box & cylinder
        self.assertEqual(len(result.edges() - last_edges), 3)
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .first.center(CenterOf.MASS),
            (0, 0, -1.5),
            6,
        )
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .last.center(CenterOf.MASS),
            (0, 0, 1.5),
            6,
        )
        self.assertTupleAlmostEquals(result.bounding_box().min, (-0.2, -0.2, -1.5), 6)
        self.assertTupleAlmostEquals(result.bounding_box().max, (0.2, 0.2, 1.5), 6)

    # Sketch

    def test_sketch_plus(self):
        rect = Rectangle(1, 2)
        circle = Circle(0.6)
        last_edges = rect.edges()
        result = rect + circle
        self.assertEqual(len(result.edges()), 8)
        self.assertEqual(len(result.edges() - last_edges), 6)
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .first.center(CenterOf.BOUNDING_BOX),
            (0.55, 0, 0),
            6,
        )
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .last.center(CenterOf.BOUNDING_BOX),
            (-0.55, 0, 0),
            6,
        )
        self.assertTupleAlmostEquals(result.bounding_box().min, (-0.6, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(result.bounding_box().max, (0.6, 1.0, 0.0), 6)

    def test_sketch_minus(self):
        rect = Rectangle(1, 2)
        circle = Circle(0.2)
        last_edges = rect.edges()
        result = rect - circle
        self.assertEqual(len(result.edges()), 5)
        self.assertEqual(len(result.edges() - last_edges), 1)
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .first.center(CenterOf.BOUNDING_BOX),
            (0, 0, 0),
            3,
        )
        self.assertTupleAlmostEquals(result.bounding_box().min, (-0.5, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(result.bounding_box().max, (0.5, 1.0, 0.0), 6)

    def test_sketch_minus_2(self):
        rect = Rectangle(1, 2)
        circle = Circle(0.7)
        last_edges = rect.edges()
        result = rect - circle
        self.assertEqual(len(result.edges()), 8)
        self.assertEqual(len(result.edges() - last_edges), 6)
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .first.center(CenterOf.BOUNDING_BOX),
            (0.0, -0.5949, 0.0),
            3,
        )
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .last.center(CenterOf.BOUNDING_BOX),
            (0.0, 0.5949, 0.0),
            3,
        )
        self.assertTupleAlmostEquals(result.bounding_box().min, (-0.5, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(result.bounding_box().max, (0.5, 1.0, 0.0), 6)

    def test_sketch_and(self):
        rect = Rectangle(1, 2)
        circle = Circle(0.4)
        last_edges = rect.edges()
        result = rect & circle
        self.assertEqual(len(result.edges()), 1)
        self.assertEqual(len(result.edges() - last_edges), 1)
        self.assertTupleAlmostEquals(
            result.edges()
            .sort_by()
            .filter_by(GeomType.CIRCLE)
            .first.center(CenterOf.BOUNDING_BOX),
            (0, 0, 0),
            3,
        )
        self.assertTupleAlmostEquals(result.bounding_box().min, (-0.4, -0.4, 0.0), 3)
        self.assertTupleAlmostEquals(result.bounding_box().max, (0.4, 0.4, 0.0), 3)

    # Curve
    def test_curve_plus(self):
        l1 = Polyline((0, 0), (1, 0), (1, 1))
        l2 = Line((1, 1), (0, 0))
        l = l1 + l2
        w = Wire(l)
        self.assertTrue(w.is_closed)
        self.assertTupleAlmostEquals(
            w.center(CenterOf.MASS), (0.6464466094067263, 0.35355339059327373, 0.0), 6
        )

    def test_curve_minus(self):
        l1 = Line((0, 0), (1, 1))
        l2 = Line((0.25, 0.25), (0.75, 0.75))
        l = l1 - l2
        vertices = l.vertices().sort_by(Axis.X)
        self.assertEqual(len(vertices), 4)
        self.assertTupleAlmostEquals(vertices[0], (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[1], (0.25, 0.25, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[2], (0.75, 0.75, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[3], (1.0, 1.0, 0.0), 6)

    def test_curve_and(self):
        l1 = Line((0, 0), (1, 1))
        l2 = Line((0.25, 0.25), (0.75, 0.75))
        l = l1 & l2
        vertices = l.vertices().sort_by(Axis.X)
        self.assertEqual(len(vertices), 2)
        self.assertTupleAlmostEquals(vertices[0], l2 @ 0, 6)
        self.assertTupleAlmostEquals(vertices[1], l2 @ 1, 6)

    def test_curve_operators(self):
        l1 = CenterArc((0, 0), 1, 0, 180)
        l2 = CenterArc((2, 0), 1, 0, -180)
        l = Curve() + [l1, l2]
        self.assertTupleAlmostEquals(l @ 0.25, Vector(2.0, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(l % 0.25, Vector(-1.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals((l ^ 0.25).position, l @ 0.25, 6)
        self.assertTupleAlmostEquals(
            (l ^ 0.25).orientation, Vector(0.0, -90.0, 90.0), 6
        )

    # Part + - & Empty

    def test_empty_plus_part(self):
        b = Box(1, 2, 3)
        r = Part() + b
        self.assertEqual(b.wrapped, r.wrapped)

    def test_part_plus_empty(self):
        b = Box(1, 2, 3)
        r = b + Part()
        self.assertEqual(b.wrapped, r.wrapped)

    def test_empty_minus_part(self):
        b = Box(1, 2, 3)
        with self.assertRaises(ValueError):
            r = Part() - b

    def test_part_minus_empty(self):
        b = Box(1, 2, 3)
        r = b - Part()
        self.assertEqual(b.wrapped, r.wrapped)

    def test_empty_and_part(self):
        b = Box(1, 2, 3)
        with self.assertRaises(ValueError):
            r = Part() & b

    def test_part_and_empty(self):
        b = Box(1, 2, 3)
        with self.assertRaises(ValueError):
            r = b & Part()

    # Sketch + - & Empty

    def test_empty_plus_sketch(self):
        b = Rectangle(1, 2)
        r = Sketch() + b
        self.assertEqual(b.wrapped, r.wrapped)

    def test_sketch_plus_empty(self):
        b = Rectangle(1, 2)
        r = b + Sketch()
        self.assertEqual(b.wrapped, r.wrapped)

    def test_empty_minus_sketch(self):
        b = Rectangle(1, 2)
        with self.assertRaises(ValueError):
            r = Sketch() - b

    def test_sketch_minus_empty(self):
        b = Rectangle(1, 2)
        r = b - Sketch()
        self.assertEqual(b.wrapped, r.wrapped)

    def test_empty_and_sketch(self):
        b = Rectangle(1, 3)
        with self.assertRaises(ValueError):
            r = Sketch() & b

    def test_sketch_and_empty(self):
        b = Rectangle(1, 2)
        with self.assertRaises(ValueError):
            r = b & Sketch()

    def test_1d_2d_minus(self):
        line = Line((0, 0), (1, 1))
        rectangle = Rectangle(1, 1)
        r = line - rectangle
        vertices = r.vertices()
        self.assertEqual(len(vertices), 2)
        self.assertTupleAlmostEquals(vertices[0], (0.5, 0.5, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[1], (1.0, 1.0, 0.0), 6)

    def test_1d_3d_minus(self):
        line = Line((0, 0), (1, 1))
        box = Box(1, 1, 1)
        r = line - box
        vertices = r.vertices()
        self.assertEqual(len(vertices), 2)
        self.assertTupleAlmostEquals(vertices[0], (0.5, 0.5, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[1], (1.0, 1.0, 0.0), 6)

    def test_2d_3d_minus(self):
        rectangle = Pos(0.5, 0, 0) * Rectangle(1, 1)
        box = Box(1, 1, 1)
        r = rectangle - box
        vertices = r.vertices()
        self.assertEqual(len(vertices), 4)
        self.assertTupleAlmostEquals(vertices[0], (0.5, -0.5, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[1], (0.5, 0.5, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[2], (1.0, 0.5, 0.0), 6)
        self.assertTupleAlmostEquals(vertices[3], (1.0, -0.5, 0.0), 6)

    def test_3d_2d_minus(self):
        box = Box(1, 1, 1)
        rectangle = Rectangle(1, 1)
        with self.assertRaises(ValueError):
            _ = box - rectangle

    def test_3d_1d_minus(self):
        box = Box(1, 1, 1)
        line = Line((0, 0), (1, 1))
        with self.assertRaises(ValueError):
            _ = box - line

    def test_2d_1d_minus(self):
        rectangle = Rectangle(1, 1)
        line = Line((0, 0), (1, 1))
        with self.assertRaises(ValueError):
            _ = rectangle - line


class LocationTests(unittest.TestCase):
    def test_wheel(self):
        plane = Plane.ZX

        cyl = Cylinder(1, 0.5)
        box = Box(0.3, 0.3, 0.5)

        p = plane * cyl

        for loc in PolarLocations(0.7, 10):
            p -= plane * loc * box

        front_faces = p.faces().sort_by(Axis.Y).first
        wires = front_faces.wires().sort_by(SortBy.DISTANCE, 1)[1:]
        centers = [wire.center(CenterOf.MASS) for wire in wires]

        self.assertEqual(len(p.edges()), 123)
        self.assertTupleAlmostEquals([c.length for c in centers], [0.7433034] * 10, 6)
        self.assertTupleAlmostEquals(p.bounding_box().min, (-1.0, -0.25, -1.0), 6)
        self.assertTupleAlmostEquals(p.bounding_box().max, (1.0, 0.25, 1.0), 6)

    def test_wheels(self):
        plane = Plane.ZX
        rotations = [Rot(Y=a) for a in (0, 45, 90, 135)]

        s = Sketch()
        for i, outer_loc in enumerate(GridLocations(3, 3, 2, 2)):
            # on plane, located to grid position, and finally rotated
            c_plane = plane * outer_loc * rotations[i]
            s += c_plane * Circle(1)

            for loc in PolarLocations(0.8, (i + 3) * 2):
                # Use polar locations on c_plane
                s -= c_plane * loc * Rectangle(0.1, 0.3)

        nested = [g.sort_by(Axis.X) for g in s.faces().group_by()]
        faces = [item for s in nested for item in s]  # flatten

        self.assertEqual(len(s.faces()), 4)
        self.assertListEqual([len(f.edges()) for f in s.faces()], [25, 33, 41, 49])
        self.assertTupleAlmostEquals(
            faces[0].normal_at(faces[0].center()), (0.0, 1.0, 0.0), 6
        )
        self.assertTupleAlmostEquals(
            faces[1].normal_at(faces[1].center()),
            (0.0, math.sqrt(2) / 2, math.sqrt(2) / 2),
            6,
        )
        self.assertTupleAlmostEquals(
            faces[2].normal_at(faces[2].center()), (0.0, 0.0, 1.0), 6
        )
        self.assertTupleAlmostEquals(
            faces[3].normal_at(faces[3].center()),
            (0.0, -math.sqrt(2) / 2, math.sqrt(2) / 2),
            6,
        )


class OperationsTests(unittest.TestCase):
    def test_fillet_3d(self):
        b = Box(1, 2, 3)
        c = fillet(b.edges(), radius=0.2)

        self.assertAlmostEqual(b.volume, 6.0, 6)
        self.assertAlmostEqual(c.volume, 5.804696, 4)

    def test_fillet_2d(self):
        r = Rectangle(1, 2)
        c = fillet(r.vertices(), radius=0.2)

        self.assertAlmostEqual(r.area, 2.0, 6)
        self.assertAlmostEqual(c.area, 1.965663, 4)

    def test_chamfer_3d(self):
        b = Box(1, 2, 3)
        c = chamfer(b.edges(), length=0.2)

        self.assertAlmostEqual(b.volume, 6.0, 6)
        self.assertAlmostEqual(c.volume, 5.56266, 4)

    def test_chamfer_2d(self):
        r = Rectangle(1, 2)
        c = chamfer(r.vertices(), length=0.2)

        self.assertAlmostEqual(r.area, 2.0, 6)
        self.assertAlmostEqual(c.area, 1.92, 4)

    def test_extrude(self):
        s = Circle(1)
        p = extrude(s, amount=1)
        p = chamfer(p.edges().filter_by(GeomType.CIRCLE), 0.3)
        self.assertEqual(len(p.edges().filter_by(GeomType.CIRCLE)), 4)

    def test_extrude_both(self):
        s = Circle(1)
        p = extrude(s, amount=1, both=True)
        self.assertAlmostEqual(p.bounding_box().size.Z, 2, 4)


class RightMultipleTests(unittest.TestCase):
    def test_rmul(self):
        c = [Location((1, 2, 3))] * Circle(1)
        self.assertTupleAlmostEquals(c[0].position, (1, 2, 3), 6)

    def test_rmul_error(self):
        with self.assertRaises(ValueError):
            [Vector(1, 2, 3)] * Circle(1)


if __name__ == "__main__":
    unittest.main()
