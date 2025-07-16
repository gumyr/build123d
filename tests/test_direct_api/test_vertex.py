"""
build123d imports

name: test_vertex.py
by:   Gumyr
date: January 22, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import unittest

from build123d.geometry import Axis, Vector
from build123d.topology import Vertex


class TestVertex(unittest.TestCase):
    """Test the extensions to the cadquery Vertex class"""

    def test_basic_vertex(self):
        v = Vertex()
        self.assertEqual(0, v.X)

        v = Vertex(1, 1, 1)
        self.assertEqual(1, v.X)
        self.assertEqual(Vector, type(v.center()))

        self.assertAlmostEqual(Vector(Vertex(Vector(1, 2, 3))), (1, 2, 3), 7)
        self.assertAlmostEqual(Vector(Vertex((4, 5, 6))), (4, 5, 6), 7)
        self.assertAlmostEqual(Vector(Vertex((7,))), (7, 0, 0), 7)
        self.assertAlmostEqual(Vector(Vertex((8, 9))), (8, 9, 0), 7)

    def test_vertex_volume(self):
        v = Vertex(1, 1, 1)
        self.assertAlmostEqual(v.volume, 0, 5)

    def test_vertex_add(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertAlmostEqual(Vector(test_vertex + (100, -40, 10)), (100, -40, 10), 7)
        self.assertAlmostEqual(
            Vector(test_vertex + Vector(100, -40, 10)), (100, -40, 10), 7
        )
        self.assertAlmostEqual(
            Vector(test_vertex + Vertex(100, -40, 10)),
            (100, -40, 10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex + [1, 2, 3]

    def test_vertex_sub(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertAlmostEqual(Vector(test_vertex - (100, -40, 10)), (-100, 40, -10), 7)
        self.assertAlmostEqual(
            Vector(test_vertex - Vector(100, -40, 10)), (-100, 40, -10), 7
        )
        self.assertAlmostEqual(
            Vector(test_vertex - Vertex(100, -40, 10)),
            (-100, 40, -10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex - [1, 2, 3]

    def test_vertex_str(self):
        self.assertEqual(str(Vertex(0, 0, 0)), "Vertex(0.0, 0.0, 0.0)")

    def test_vertex_to_vector(self):
        self.assertIsInstance(Vector(Vertex(0, 0, 0)), Vector)
        self.assertAlmostEqual(Vector(Vertex(0, 0, 0)), (0.0, 0.0, 0.0), 7)

    def test_vertex_init_error(self):
        with self.assertRaises(TypeError):
            Vertex(Axis.Z)
        with self.assertRaises(ValueError):
            Vertex(x=1)
        with self.assertRaises(TypeError):
            Vertex((Axis.X, Axis.Y, Axis.Z))

    def test_no_intersect(self):
        with self.assertRaises(NotImplementedError):
            Vertex(1, 2, 3) & Vertex(5, 6, 7)


if __name__ == "__main__":
    unittest.main()
