"""

build123d BuildPart tests

name: build_part_tests.py
by:   Gumyr
date: July 28th 2022

desc: Unit tests for the build123d build_part module

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
from build123d import *


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class BuildPartTests(unittest.TestCase):
    """Test the BuildPart Builder derived class"""

    def test_select_vertices(self):
        """Test vertices()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.vertices()), 8)
            Box(5, 5, 20, centered=(True, True, False))
            self.assertEqual(len(test.vertices(Select.LAST)), 8)

    def test_select_edges(self):
        """Test edges()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.edges()), 12)
            Box(5, 5, 20, centered=(True, True, False))
            self.assertEqual(len(test.edges(Select.LAST)), 12)

    def test_select_faces(self):
        """Test faces()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.faces()), 6)
            WorkplanesFromFaces(test.faces().filter_by_axis(Axis.Z)[-1])
            with BuildSketch():
                Rectangle(5, 5)
            Extrude(5)
            self.assertEqual(len(test.faces()), 11)
            self.assertEqual(len(test.faces(Select.LAST)), 6)


if __name__ == "__main__":
    unittest.main()
