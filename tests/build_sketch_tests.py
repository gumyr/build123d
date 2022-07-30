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
from math import pi
from build123d import *
from cadquery import Solid


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class BuildSketchTests(unittest.TestCase):
    """Test the BuildSketch Builder derived class"""

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
            PushPoints((0, 20))
            Rectangle(5, 5)
            self.assertEqual(len(test.faces()), 2)
            self.assertEqual(len(test.faces(Select.LAST)), 1)

    def test_consolidate_edges(self):
        with BuildSketch() as test:
            with BuildLine():
                l1 = Line((0, 0), (10, 0))
                Line(l1 @ 1, (10, 10))
            self.assertTupleAlmostEquals(
                (test.consolidate_edges() @ 1).toTuple(), (10, 10, 0), 5
            )

    def test_mode_intersect(self):
        with BuildSketch() as test:
            Circle(10)
            Rectangle(10, 10, centered=(False, False), mode=Mode.INTERSECT)
        self.assertAlmostEqual(test.sketch.Area(), 25 * pi, 5)

    def test_mode_replace(self):
        with BuildSketch() as test:
            Circle(10)
            Rectangle(10, 10, centered=(False, False), mode=Mode.REPLACE)
        self.assertAlmostEqual(test.sketch.Area(), 100, 5)


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

    def test_objects(self):
        """This test should be broken up into individual items"""
        with BuildSketch() as test:
            Ellipse(20, 10)
            PushPoints((10, 5))
            Rectangle(20, 10)
            PolarArray(5, 0, 360, 6)
            RegularPolygon(1, 6, mode=Mode.SUBTRACT)
            RectangularArray(3, 3, 2, 2)
            SlotOverall(2, 1, rotation=30, mode=Mode.SUBTRACT)
            SlotCenterPoint((-10, 0), (-7, 0), 2, mode=Mode.SUBTRACT)
            PushPoints((10, 0))
            SlotCenterToCenter(5, 3, mode=Mode.SUBTRACT)
            PushPoints((0, 8))
            t = Trapezoid(5, 3, 35, mode=Mode.PRIVATE)
            Offset(t, amount=1, kind=Kind.TANGENT, mode=Mode.SUBTRACT)
            PushPoints((-8, 6))
            Circle(3, mode=Mode.SUBTRACT)
            with BuildLine(mode=Mode.PRIVATE) as wave:
                c = CenterArc((-10, -7), 2, 0, 45)
                RadiusArc(c @ 1, (-9, -4), 4)
            SlotArc(wave.line_as_wire, 2, mode=Mode.SUBTRACT)
            Polygon(
                (8, -6),
                (9, -7),
                (10, -7),
                (11, -6),
                (10, -5),
                (9, -5),
                (8, -6),
                mode=Mode.SUBTRACT,
            )
            PushPoints((18, 8))
            Text("Sketch", 3, halign=Halign.RIGHT, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(test.sketch.Area(), 533.8401466089292, 5)

    def test_offset(self):
        """Test normal and error cases"""
        with BuildSketch() as test:
            Circle(10)
            Offset(test.faces()[0], amount=1)
        self.assertAlmostEqual(test.edges()[0].radius(), 11)
        with self.assertRaises(ValueError):
            with BuildSketch() as test:
                Offset(Solid.makeBox(1, 1, 1), amount=1)

    def test_add_multiple(self):
        """Test adding multiple items"""
        with BuildSketch() as test:
            PushPoints((-10, 0), (10, 0))
            Circle(1)
        self.assertAlmostEqual(sum([f.Area() for f in test.faces()]), 2 * pi, 5)

    def test_hull(self):
        """Test hull from pending edges and passed edges"""
        with BuildSketch() as test:
            with BuildLine():
                CenterArc((0, 0), 1, 0, 360)
                CenterArc((1, 1.5), 0.5, 0, 360)
                Line((0.0, 2), (-1, 3.0))
            BuildHull()
        self.assertAlmostEqual(test.sketch.Area(), 7.258175622249558, 5)
        with BuildSketch() as test:
            PushPoints((-10, 0))
            Circle(10)
            PushPoints((10, 0))
            Circle(7)
            BuildHull(*test.edges())
        self.assertAlmostEqual(test.sketch.Area(), 577.8808734698988, 5)


if __name__ == "__main__":
    unittest.main()
