import unittest
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
        self.assertTupleAlmostEquals(b.bounding_box().max, (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(b.bounding_box().min, (-1.0, -2.0, -3.0), 6)

    # Sketch

    def test_rect(self):
        r = Face.make_rect(1, 2)

        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-1.0, -0.5, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (1.0, 0.5, 0.0), 6)

    def test_rect_min(self):
        r = Rectangle(1, 2, align=(Align.MIN, Align.MIN, Align.MIN))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.5, 1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (1.0, 2.0, 0.0), 6)

    def test_rect_center(self):
        r = Rectangle(1, 2, align=(Align.CENTER, Align.CENTER, Align.CENTER))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (0.0, 0.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-0.5, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (0.5, 1.0, 0.0), 6)

    def test_rect_max(self):
        r = Rectangle(1, 2, align=(Align.MAX, Align.MAX, Align.MAX))

        self.assertTrue(isinstance(r, Sketch))
        self.assertTrue(isinstance(r, Shape))

        self.assertTupleAlmostEquals(r.center(), (-0.5, -1.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().min, (-1.0, -2.0, 0.0), 6)
        self.assertTupleAlmostEquals(r.bounding_box().max, (0.0, 0.0, 0.0), 6)

    # Curve

    def test_edge(self):
        e = Edge.make_line((1, 2), (4, 4))

        self.assertTrue(isinstance(e, Shape))

        self.assertTupleAlmostEquals(e.center(), (2.5, 3.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 0, (1.0, 2.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 1, (4.0, 4.0, 0.0), 6)

    # not impelemented yet
    def test_line(self):
        e = Line((1, 2), (4, 4))

        self.assertTrue(isinstance(e, Shape))

        self.assertTupleAlmostEquals(e.center(), (2.5, 3.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 0, (1.0, 2.0, 0.0), 6)
        self.assertTupleAlmostEquals(e @ 1, (4.0, 4.0, 0.0), 6)


class AlgebraTests(unittest.TestCase):
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
