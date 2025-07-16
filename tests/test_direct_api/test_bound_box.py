"""
build123d imports

name: test_bound_box.py
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

from build123d.geometry import BoundBox, Vector
from build123d.topology import Solid, Vertex


class TestBoundBox(unittest.TestCase):
    def test_basic_bounding_box(self):
        v = Vertex(1, 1, 1)
        v2 = Vertex(2, 2, 2)
        self.assertEqual(BoundBox, type(v.bounding_box()))
        self.assertEqual(BoundBox, type(v2.bounding_box()))

        bb1 = v.bounding_box().add(v2.bounding_box())

        # OCC uses some approximations
        self.assertAlmostEqual(bb1.size.X, 1.0, 1)

        # Test adding to an existing bounding box
        v0 = Vertex(0, 0, 0)
        bb2 = v0.bounding_box().add(v.bounding_box())

        bb3 = bb1.add(bb2)
        self.assertAlmostEqual(bb3.size, (2, 2, 2), 7)

        bb3 = bb2.add((3, 3, 3))
        self.assertAlmostEqual(bb3.size, (3, 3, 3), 7)

        bb3 = bb2.add(Vector(3, 3, 3))
        self.assertAlmostEqual(bb3.size, (3, 3, 3), 7)

        # Test 2D bounding boxes
        bb1 = Vertex(1, 1, 0).bounding_box().add(Vertex(2, 2, 0).bounding_box())
        bb2 = Vertex(0, 0, 0).bounding_box().add(Vertex(3, 3, 0).bounding_box())
        bb3 = Vertex(0, 0, 0).bounding_box().add(Vertex(1.5, 1.5, 0).bounding_box())
        # Test that bb2 contains bb1
        self.assertEqual(bb2, BoundBox.find_outside_box_2d(bb1, bb2))
        self.assertEqual(bb2, BoundBox.find_outside_box_2d(bb2, bb1))
        # Test that neither bounding box contains the other
        self.assertIsNone(BoundBox.find_outside_box_2d(bb1, bb3))

        # Test creation of a bounding box from a shape - note the low accuracy comparison
        # as the box is a little larger than the shape
        bb1 = BoundBox.from_topo_ds(Solid.make_cylinder(1, 1).wrapped, optimal=False)
        self.assertAlmostEqual(bb1.size, (2, 2, 1), 1)

        bb2 = BoundBox.from_topo_ds(
            Solid.make_cylinder(0.5, 0.5).translate((0, 0, 0.1)).wrapped, optimal=False
        )
        self.assertTrue(bb2.is_inside(bb1))

    def test_bounding_box_repr(self):
        bb = Solid.make_box(1, 1, 1).bounding_box()
        self.assertEqual(
            repr(bb), "bbox: 0.0 <= x <= 1.0, 0.0 <= y <= 1.0, 0.0 <= z <= 1.0"
        )

    def test_center_of_boundbox(self):
        self.assertAlmostEqual(
            Solid.make_box(1, 1, 1).bounding_box().center(),
            (0.5, 0.5, 0.5),
            5,
        )

    def test_combined_center_of_boundbox(self):
        pass

    def test_clean_boundbox(self):
        s = Solid.make_sphere(3)
        self.assertAlmostEqual(s.bounding_box().size, (6, 6, 6), 5)
        s.mesh(1e-3)
        self.assertAlmostEqual(s.bounding_box().size, (6, 6, 6), 5)


if __name__ == "__main__":
    unittest.main()
