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


class BuildSketchTests(unittest.TestCase):
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
            Rectangle(5, 20, centered=(True, False))
            self.assertEqual(len(test.vertices(Select.LAST)), 4)

    def test_select_edges(self):
        """Test edges()"""
        with BuildSketch() as test:
            Rectangle(10, 10)
            self.assertEqual(len(test.edges()), 4)
            Rectangle(5, 20, centered=(True, False))
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
            Rectangle(10, 10, centered=(False, False), mode=Mode.INTERSECT)
        self.assertAlmostEqual(test.sketch.area, 25 * pi, 5)

    def test_mode_replace(self):
        with BuildSketch() as test:
            Circle(10)
            Rectangle(10, 10, centered=(False, False), mode=Mode.REPLACE)
        self.assertAlmostEqual(test.sketch.area, 100, 5)


class BuildSketchExceptions(unittest.TestCase):
    """Test exception handling"""

    def test_invalid_subtract(self):
        with self.assertRaises(RuntimeError):
            with BuildSketch():
                Circle(10, mode=Mode.SUBTRACT)

    def test_invalid_intersect(self):
        with self.assertRaises(RuntimeError):
            with BuildSketch():
                Circle(10, mode=Mode.INTERSECT)


class BuildSketchObjects(unittest.TestCase):
    """Test the 2d sketch objects"""

    def test_circle(self):
        with BuildSketch() as test:
            c = Circle(20)
        self.assertEqual(c.radius, 20)
        self.assertEqual(c.centered, (True, True))
        self.assertEqual(c.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi * 20**2, 5)

    def test_ellipse(self):
        with BuildSketch() as test:
            e = Ellipse(20, 10)
        self.assertEqual(e.x_radius, 20)
        self.assertEqual(e.y_radius, 10)
        self.assertEqual(e.rotation, 0)
        self.assertEqual(e.centered, (True, True))
        self.assertEqual(e.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi * 20 * 10, 5)

    def test_polygon(self):
        with BuildSketch() as test:
            p = Polygon((0, 0), (1, 0), (0, 1), (0, 0))
        self.assertEqual(len(p.pts), 4)
        self.assertEqual(p.rotation, 0)
        self.assertEqual(p.centered, (True, True))
        self.assertEqual(p.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, 0.5, 5)

    def test_rectangle(self):
        with BuildSketch() as test:
            r = Rectangle(20, 10)
        self.assertEqual(r.width, 20)
        self.assertEqual(r.rectangle_height, 10)
        self.assertEqual(r.rotation, 0)
        self.assertEqual(r.centered, (True, True))
        self.assertEqual(r.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, 20 * 10, 5)

    def test_regular_polygon(self):
        with BuildSketch() as test:
            r = RegularPolygon(2, 6)
        self.assertEqual(r.radius, 2)
        self.assertEqual(r.side_count, 6)
        self.assertEqual(r.rotation, 0)
        self.assertEqual(r.centered, (True, True))
        self.assertEqual(r.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, (3 * sqrt(3) / 2) * 2**2, 5)

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

    def test_slot_center_point(self):
        with BuildSketch() as test:
            s = SlotCenterPoint((0, 0), (2, 0), 2)
        self.assertTupleAlmostEquals(s.center.to_tuple(), (0, 0, 0), 5)
        self.assertTupleAlmostEquals(s.point.to_tuple(), (2, 0, 0), 5)
        self.assertEqual(s.slot_height, 2)
        self.assertEqual(s.rotation, 0)
        self.assertEqual(s.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi + 4 * 2, 5)

    def test_slot_center_to_center(self):
        with BuildSketch() as test:
            s = SlotCenterToCenter(4, 2)
        self.assertEqual(s.center_separation, 4)
        self.assertEqual(s.slot_height, 2)
        self.assertEqual(s.rotation, 0)
        self.assertEqual(s.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi + 4 * 2, 5)

    def test_slot_overall(self):
        with BuildSketch() as test:
            s = SlotOverall(6, 2)
        self.assertEqual(s.width, 6)
        self.assertEqual(s.slot_height, 2)
        self.assertEqual(s.rotation, 0)
        self.assertEqual(s.mode, Mode.ADD)
        self.assertAlmostEqual(test.sketch.area, pi + 4 * 2, 5)

    def test_text(self):
        with BuildSketch() as test:
            t = Text("test", 2)
        self.assertEqual(t.txt, "test")
        self.assertEqual(t.fontsize, 2)
        self.assertEqual(t.font, "Arial")
        self.assertIsNone(t.font_path)
        self.assertEqual(t.font_style, FontStyle.REGULAR)
        self.assertEqual(t.halign, Halign.LEFT)
        self.assertEqual(t.valign, Valign.CENTER)
        self.assertIsNone(t.text_path)
        self.assertEqual(t.position_on_path, 0)
        self.assertEqual(t.rotation, 0)
        self.assertEqual(t.mode, Mode.ADD)
        self.assertEqual(len(test.sketch.faces()), 4)

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

        with self.assertRaises(ValueError):
            with BuildSketch() as test:
                Trapezoid(6, 2, 30)

    def test_offset(self):
        """Test normal and error cases"""
        with BuildSketch() as test:
            Circle(10)
            Offset(test.faces()[0], amount=1)
        self.assertAlmostEqual(test.edges()[0].radius, 11)
        with self.assertRaises(RuntimeError):
            with BuildSketch() as test:
                Offset(Location(Vector()), amount=1)

    def test_add_multiple(self):
        """Test adding multiple items"""
        with BuildSketch() as test:
            with Locations((-10, 0), (10, 0)):
                Circle(1)
        self.assertAlmostEqual(sum([f.area for f in test.faces()]), 2 * pi, 5)

    def test_hull(self):
        """Test hull from pending edges and passed edges"""
        with BuildSketch() as test:
            with BuildLine():
                CenterArc((0, 0), 1, 0, 360)
                CenterArc((1, 1.5), 0.5, 0, 360)
                Line((0.0, 2), (-1, 3.0))
            MakeHull()
        self.assertAlmostEqual(test.sketch.area, 7.258175622249558, 5)
        with BuildSketch() as test:
            with Locations((-10, 0)):
                Circle(10)
            with Locations((10, 0)):
                Circle(7)
            MakeHull(*test.edges())
        self.assertAlmostEqual(test.sketch.area, 577.8808734698988, 5)


if __name__ == "__main__":
    unittest.main(failfast=True)
