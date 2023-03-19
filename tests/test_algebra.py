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

    @pytest.mark.skip(reason="not implemented yet")
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
        r = b & Part()
        self.assertIsNone(r.wrapped)

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
        r = b & Sketch()
        self.assertIsNone(r.wrapped)


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
        rotations = [Rot(y=a) for a in (0, 45, 90, 135)]

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
