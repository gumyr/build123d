"""

build123d BuildSketch tests

name: build_sketch_tests.py
by:   Gumyr
date: July 28th 2022

desc: Unit tests for the build123d build_sketch module

license:

    Copyright 2022 Gumyr

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
from math import pi, sqrt
from build123d import *


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class TestAlign(unittest.TestCase):
    def test_align(self):
        with BuildSketch() as align:
            Rectangle(1, 1, align=(Align.MIN, Align.MAX))
        bbox = align.sketch.bounding_box()
        self.assertGreaterEqual(bbox.min.X, 0)
        self.assertLessEqual(bbox.max.X, 1)
        self.assertGreaterEqual(bbox.min.Y, -1)
        self.assertLessEqual(bbox.max.Y, 0)


class TestBuildSketch(unittest.TestCase):
    """Test the BuildSketch Builder derived class"""

    def test_obj_name(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
        self.assertEqual(test._obj_name, "sketch")

    def test_select_vertices(self):
        """Test vertices()"""
        with BuildSketch() as test:
            Rectangle(10, 10)
            self.assertEqual(len(test.vertices()), 4)
            Rectangle(5, 20, align=(Align.CENTER, Align.MIN))
            self.assertEqual(len(test.vertices(Select.LAST)), 4)

    def test_select_edges(self):
        """Test edges()"""
        with BuildSketch() as test:
            Rectangle(10, 10)
            self.assertEqual(len(test.edges()), 4)
            Rectangle(5, 20, align=(Align.CENTER, Align.MIN))
            self.assertEqual(len(test.edges(Select.LAST)), 5)

    def test_select_faces(self):
        """Test faces()"""
        with BuildSketch() as test:
            Rectangle(10, 10)
            with Locations((0, 20)):
                Rectangle(5, 5)
            self.assertEqual(len(test.faces()), 2)
            self.assertEqual(len(test.faces(Select.LAST)), 1)

    def test_consolidate_edges(self):
        with BuildSketch() as test:
            with BuildLine():
                l1 = Line((0, 0), (10, 0))
                Line(l1 @ 1, (10, 10))
            self.assertTupleAlmostEquals(
                (test.consolidate_edges() @ 1).to_tuple(), (10, 10, 0), 5
            )

    def test_mode_intersect(self):
        with BuildSketch() as test:
            Circle(10)
            Rectangle(10, 10, align=(Align.MIN, Align.MIN), mode=Mode.INTERSECT)
        self.assertAlmostEqual(test.sketch.area, 25 * pi, 5)

    def test_mode_replace(self):
        with BuildSketch() as test:
            Circle(10)
            Rectangle(10, 10, align=(Align.MIN, Align.MIN), mode=Mode.REPLACE)
        self.assertAlmostEqual(test.sketch.area, 100, 5)


class TestBuildOnPlanes(unittest.TestCase):
    def test_plane_xz(self):
        with BuildSketch(Plane.XZ) as sketch_builder:
            with BuildLine(Plane.XZ) as line_builder:
                Polyline((0, 0), (0, 8), (2, 8), (2, 2), (6, 2), (6, 0), (0, 0))
            make_face()
        self.assertTrue(sketch_builder.sketch.faces()[0].is_coplanar(Plane.XZ))

        with BuildSketch(Plane.XZ) as sketch_builder:
            Rectangle(1, 1)
        self.assertTrue(sketch_builder.sketch.faces()[0].is_coplanar(Plane.XZ))

    def test_not_coplanar(self):
        with BuildSketch() as coplanar:
            add([Face.make_rect(1, 1, Plane.XY.offset(1))])
        self.assertTrue(coplanar.sketch.faces()[0].is_coplanar(Plane.XY))

        with BuildSketch() as coplanar:
            add([Face.make_rect(1, 1, Plane.XZ)])
        self.assertTrue(coplanar.sketch.faces()[0].is_coplanar(Plane.XY))

    def test_changing_geometry(self):
        with BuildSketch() as s:
            Rectangle(1, 2)
            scale(by=(2, 1, 0))
        self.assertAlmostEqual(s.sketch.area, 4, 5)


class TestUpSideDown(unittest.TestCase):
    def test_flip_face(self):
        f1 = Face(
            Wire.make_polygon([(1, 0), (1.5, 0.5), (1, 2), (3, 1), (2, 0), (1, 0)])
        )
        f1 = (
            fillet(f1.vertices()[2:4], 0.2)
            - Pos(1.8, 1.2, 0) * Rectangle(0.2, 0.4)
            - Pos(2, 0.5, 0) * Circle(0.2)
        ).faces()[0]
        self.assertTrue(f1.normal_at().Z < 0)  # Up-side-down

        f2 = Face(Wire.make_polygon([(1, 0), (1.5, -1), (2, -1), (2, 0), (1, 0)]))
        self.assertTrue(f2.normal_at().Z > 0)  # Right-side-up
        with BuildSketch() as flip_test:
            add(f1)
            add(f2)
        self.assertEqual(len(flip_test.faces()), 1)  # Face flip and combined

    def test_make_hull_flipped(self):
        with BuildSketch() as base_plan:
            Circle(55 / 2)
            with Locations((0, 125)):
                Circle(30 / 2)
            base_hull = make_hull(mode=Mode.PRIVATE)
        for face in base_hull.faces():
            self.assertTrue(face.normal_at().Z > 0)

    def test_make_face_flipped(self):
        wire = Wire.make_polygon([(0, 0), (1, 1), (2, 0)])
        sketch = make_face(wire.edges())
        self.assertTrue(sketch.faces()[0].normal_at().Z > 0)


class TestBuildSketchExceptions(unittest.TestCase):
    """Test exception handling"""

    def test_invalid_subtract(self):
        with self.assertRaises(RuntimeError):
            with BuildSketch():
                Circle(10, mode=Mode.SUBTRACT)

    def test_invalid_intersect(self):
        with self.assertRaises(RuntimeError):
            with BuildSketch():
                Circle(10, mode=Mode.INTERSECT)

    def test_invalid_selector(self):
        with self.assertRaises(NotImplementedError):
            with BuildSketch() as bs:
                Circle(1)
                bs.solids()


class TestBuildSketchObjects(unittest.TestCase):
    """Test the 2d sketch objects"""

    def test_circle(self):
        with BuildSketch() as test:
            c = Circle(20)
        self.assertEqual(c.radius, 20)
        self.assertEqual(c.align, (Align.CENTER, Align.CENTER))
        self.assertEqual(c.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi * 20**2, 5)
        self.assertEqual(c.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_ellipse(self):
        with BuildSketch() as test:
            e = Ellipse(20, 10)
        self.assertEqual(e.x_radius, 20)
        self.assertEqual(e.y_radius, 10)
        self.assertEqual(e.rotation, 0)
        self.assertEqual(e.align, (Align.CENTER, Align.CENTER))
        self.assertEqual(e.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi * 20 * 10, 5)
        self.assertEqual(e.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_polygon(self):
        with BuildSketch() as test:
            p = Polygon((0, 0), (1, 0), (0, 1), (0, 0))
        self.assertEqual(len(p.pts), 4)
        self.assertEqual(p.rotation, 0)
        self.assertEqual(p.align, (Align.CENTER, Align.CENTER))
        self.assertEqual(p.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, 0.5, 5)
        self.assertEqual(p.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_rectangle(self):
        with BuildSketch() as test:
            r = Rectangle(20, 10)
        self.assertEqual(r.width, 20)
        self.assertEqual(r.rectangle_height, 10)
        self.assertEqual(r.rotation, 0)
        self.assertEqual(r.align, (Align.CENTER, Align.CENTER))
        self.assertEqual(r.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, 20 * 10, 5)
        self.assertEqual(r.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_rectangle_rounded(self):
        with BuildSketch() as test:
            r = RectangleRounded(20, 10, 1)
        self.assertEqual(r.width, 20)
        self.assertEqual(r.rectangle_height, 10)
        self.assertEqual(r.rotation, 0)
        self.assertEqual(r.radius, 1)
        self.assertEqual(r.align, (Align.CENTER, Align.CENTER))
        self.assertEqual(r.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, 20 * 10 - 4 * 1**2 + pi * 1**2, 5)
        self.assertEqual(r.faces()[0].normal_at(), Vector(0, 0, 1))

        with self.assertRaises(ValueError):
            with BuildSketch() as test:
                r = RectangleRounded(20, 10, 5)
        with self.assertRaises(ValueError):
            with BuildSketch() as test:
                r = RectangleRounded(10, 20, 5)

    def test_regular_polygon(self):
        with BuildSketch() as test:
            r = RegularPolygon(2, 6)
        self.assertEqual(r.radius, 2)
        self.assertEqual(r.side_count, 6)
        self.assertEqual(r.rotation, 0)
        self.assertEqual(r.align, (Align.CENTER, Align.CENTER))
        self.assertEqual(r.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, (3 * sqrt(3) / 2) * 2**2, 5)
        self.assertTupleAlmostEquals(
            test.sketch.faces()[0].normal_at().to_tuple(), (0, 0, 1), 5
        )
        self.assertAlmostEqual(r.apothem, 2 * sqrt(3) / 2)

    def test_regular_polygon_minor_radius(self):
        with BuildSketch() as test:
            r = RegularPolygon(0.5, 3, False)
        self.assertAlmostEqual(r.radius, 1, 5)
        self.assertEqual(r.side_count, 3)
        self.assertEqual(r.rotation, 0)
        self.assertEqual(r.align, (Align.CENTER, Align.CENTER))
        self.assertEqual(r.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, (3 * sqrt(3) / 4) * (0.5 * 2) ** 2, 5)
        self.assertTupleAlmostEquals(
            test.sketch.faces()[0].normal_at().to_tuple(), (0, 0, 1), 5
        )

    def test_regular_polygon_align(self):
        with BuildSketch() as align:
            RegularPolygon(2, 5, align=(Align.MIN, Align.MAX))
        bbox = align.sketch.bounding_box()
        self.assertAlmostEqual(bbox.min.X, 0, 8)
        self.assertLessEqual(bbox.max.X, 4)
        self.assertGreaterEqual(bbox.min.Y, -4)
        self.assertLessEqual(bbox.max.Y, 1e-5)

        with BuildSketch() as align:
            RegularPolygon(2, 5, align=None)
        self.assertLessEqual(
            Vector(align.vertices().sort_by_distance(other=(0, 0, 0))[-1]).length, 2
        )

    def test_regular_polygon_matches_polar(self):
        for side_count in range(3, 10):
            with BuildSketch():
                regular_poly = RegularPolygon(1, side_count)
                poly_pts = [Vector(v) for v in regular_poly.vertices()]
                polar_pts = [p.position for p in PolarLocations(1, side_count)]
            for poly_pt, polar_pt in zip(poly_pts, polar_pts):
                self.assertTupleAlmostEquals(poly_pt.to_tuple(), polar_pt.to_tuple(), 5)

    def test_regular_polygon_min_sides(self):
        with self.assertRaises(ValueError):
            with BuildSketch():
                RegularPolygon(1, 2)

    def test_slot_arc(self):
        with BuildSketch() as test:
            with BuildLine(mode=Mode.PRIVATE) as l:
                RadiusArc((0, 0), (5, 0), radius=4)
            s = SlotArc(arc=l.edges()[0], height=1, rotation=45)
        self.assertEqual(type(s.arc), Edge)
        self.assertEqual(s.slot_height, 1)
        self.assertEqual(s.rotation, 45)
        self.assertEqual(s.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, 6.186450426893698, 5)
        self.assertEqual(s.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_slot_center_point(self):
        with BuildSketch() as test:
            s = SlotCenterPoint((0, 0), (2, 0), 2)
        self.assertTupleAlmostEquals(s.slot_center.to_tuple(), (0, 0, 0), 5)
        self.assertTupleAlmostEquals(s.point.to_tuple(), (2, 0, 0), 5)
        self.assertEqual(s.slot_height, 2)
        self.assertEqual(s.rotation, 0)
        self.assertEqual(s.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi + 4 * 2, 5)
        self.assertEqual(s.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_slot_center_to_center(self):
        with BuildSketch() as test:
            s = SlotCenterToCenter(4, 2)
        self.assertEqual(s.center_separation, 4)
        self.assertEqual(s.slot_height, 2)
        self.assertEqual(s.rotation, 0)
        self.assertEqual(s.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi + 4 * 2, 5)
        self.assertEqual(s.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_slot_overall(self):
        with BuildSketch() as test:
            s = SlotOverall(6, 2)
        self.assertEqual(s.width, 6)
        self.assertEqual(s.slot_height, 2)
        self.assertEqual(s.rotation, 0)
        self.assertEqual(s.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi + 4 * 2, 5)
        self.assertEqual(s.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_text(self):
        with BuildSketch() as test:
            t = Text("test", 2)
        self.assertEqual(t.txt, "test")
        self.assertEqual(t.font_size, 2)
        self.assertEqual(t.font, "Arial")
        self.assertIsNone(t.font_path)
        self.assertEqual(t.font_style, FontStyle.REGULAR)
        self.assertEqual(t.align, (Align.CENTER, Align.CENTER))
        self.assertIsNone(t.text_path)
        self.assertEqual(t.position_on_path, 0)
        self.assertEqual(t.rotation, 0)
        self.assertEqual(t.mode, Mode.ADD)
        self.assertEqual(len(test.sketch.faces()), 4)
        self.assertEqual(t.faces()[0].normal_at(), Vector(0, 0, 1))

    def test_trapezoid(self):
        with BuildSketch() as test:
            t = Trapezoid(6, 2, 63.434948823)
        self.assertEqual(t.width, 6)
        self.assertEqual(t.trapezoid_height, 2)
        self.assertEqual(t.left_side_angle, 63.434948823)
        self.assertEqual(t.right_side_angle, 63.434948823)
        self.assertEqual(t.rotation, 0)
        self.assertEqual(t.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, 2 * (6 + 4) / 2, 5)
        self.assertEqual(t.faces()[0].normal_at(), Vector(0, 0, 1))

        with self.assertRaises(ValueError):
            with BuildSketch() as test:
                Trapezoid(6, 2, 30)

        with self.assertRaises(ValueError):
            with BuildSketch() as test:
                Trapezoid(6, 2, 150)

        with BuildSketch() as test:
            t = Trapezoid(12, 8, 135, 90)
        self.assertEqual(t.width, 12)
        self.assertEqual(t.trapezoid_height, 8)
        self.assertEqual(t.left_side_angle, 135)
        self.assertEqual(t.right_side_angle, 90)
        self.assertAlmostEqual(test.sketch.area, 8 * (12 + 4) / 2, 5)

    def test_triangle(self):
        tri = Triangle(a=3, b=4, c=5)
        self.assertAlmostEqual(tri.area, (3 * 4) / 2, 5)
        tri = Triangle(c=5, C=90, a=3)
        self.assertAlmostEqual(tri.area, (3 * 4) / 2, 5)

        with self.assertRaises(ValueError):
            Triangle(A=90, B=45, C=45)
        with self.assertRaises(AssertionError):
            Triangle(a=10, b=4, c=4)

    def test_offset(self):
        """Test normal and error cases"""
        with BuildSketch() as test:
            Circle(10)
            offset(amount=1, objects=test.faces()[0])
        self.assertAlmostEqual(test.edges()[0].radius, 11)
        with self.assertRaises(RuntimeError):
            with BuildSketch() as test:
                offset(amount=1, objects=Location(Vector()))

    def test_add_multiple(self):
        """Test adding multiple items"""
        with BuildSketch() as test:
            with Locations((-10, 0), (10, 0)):
                Circle(1)
        self.assertAlmostEqual(sum([f.area for f in test.faces()]), 2 * pi, 5)

    def test_make_face(self):
        with self.assertRaises(ValueError):
            with BuildSketch():
                make_face()
        with self.assertRaises(ValueError):
            make_face()

    def test_make_hull(self):
        """Test hull from pending edges and passed edges"""
        with BuildSketch() as test:
            with BuildLine():
                CenterArc((0, 0), 1, 0, 360)
                CenterArc((1, 1.5), 0.5, 0, 360)
                Line((0.0, 2), (-1, 3.0))
            make_hull()
        self.assertAlmostEqual(test.sketch.area, 7.2582, 4)
        with BuildSketch() as test:
            with Locations((-10, 0)):
                Circle(10)
            with Locations((10, 0)):
                Circle(7)
            make_hull(test.edges())
        self.assertAlmostEqual(test.sketch.area, 577.8808, 4)
        with self.assertRaises(ValueError):
            with BuildSketch():
                make_hull()
        with self.assertRaises(ValueError):
            make_hull()

    def test_trace(self):
        with BuildSketch() as test:
            with BuildLine():
                Line((0, 0), (10, 0))
            trace(line_width=1)
        self.assertEqual(len(test.faces()), 1)
        self.assertAlmostEqual(test.sketch.area, 10, 5)

        with self.assertRaises(ValueError):
            trace()

        line = Polyline((0, 0), (10, 10), (20, 10))
        test = trace(line, 4)
        self.assertEqual(len(test.faces()), 3)
        test = trace(line, 4).clean()
        self.assertEqual(len(test.faces()), 1)

    def test_full_round(self):
        with BuildSketch() as test:
            trap = Trapezoid(0.5, 1, 90 - 8)
            full_round(test.edges().sort_by(Axis.Y)[-1])
        self.assertLess(test.face().area, trap.face().area)

        with self.assertRaises(ValueError):
            full_round(test.edges().sort_by(Axis.Y))

        with self.assertRaises(ValueError):
            full_round(trap.edges().sort_by(Axis.X)[-1])

        l1 = Edge.make_spline([(-1, 0), (1, 0)], tangents=((0, -8), (0, 8)), scale=True)
        l2 = Edge.make_line(l1 @ 0, l1 @ 1)
        face = Face(Wire([l1, l2]))
        with self.assertRaises(ValueError):
            full_round(face.edges()[0])

        positive, c1, r1 = full_round(trap.edges().sort_by(SortBy.LENGTH)[0])
        negative, c2, r2 = full_round(
            trap.edges().sort_by(SortBy.LENGTH)[0], invert=True
        )
        self.assertLess(negative.area, positive.area)
        self.assertAlmostEqual(r1, r2, 2)
        self.assertTupleAlmostEquals(tuple(c1), tuple(c2), 2)


if __name__ == "__main__":
    unittest.main(failfast=True)
