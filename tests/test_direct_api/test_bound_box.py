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

from OCP.Bnd import Bnd_Box
from build123d.geometry import BoundBox, Vector
from build123d.topology import Solid, Vertex

from OCP.TopoDS import TopoDS_Shape


class TestBoundBox(unittest.TestCase):
    @staticmethod
    def _box(
        min_corner: tuple[float, float, float], max_corner: tuple[float, float, float]
    ):
        """Create an exact axis-aligned bounding box for predicate tests."""
        bounding_box = Bnd_Box()
        bounding_box.Update(*min_corner, *max_corner)
        return BoundBox(bounding_box)

    def test_constructor_errors(self):
        topo_ds = TopoDS_Shape()

        # Unexpected keywords
        with self.assertRaises(TypeError) as ctx:
            BoundBox(topo_ds, unexpected_kw="Unknown")
        self.assertEqual(
            "Unexpected keyword arguments: unexpected_kw", str(ctx.exception)
        )

        # Invalid first parameter
        topo_ds_str = "TopoDS_Shape"
        with self.assertRaises(TypeError) as ctx:
            BoundBox(topo_ds_str)
        self.assertEqual(
            f"Invalid positional arguments: {topo_ds_str}", str(ctx.exception)
        )

        # Second parameter not float
        tolerance_str = "tolerance_str"
        with self.assertRaises(TypeError) as ctx:
            BoundBox(topo_ds, tolerance_str)
        self.assertEqual(
            f"Second parameter must be a float or None not {tolerance_str}",
            str(ctx.exception),
        )

        # Third parameter not bool
        optimal_str = "optimal_str"
        with self.assertRaises(TypeError) as ctx:
            BoundBox(topo_ds, None, optimal_str)
        self.assertEqual(
            f"Third parameter must be a bool not {optimal_str}", str(ctx.exception)
        )

        # Invalid shape keyword
        with self.assertRaises(TypeError) as ctx:
            BoundBox(shape="not a shape")
        self.assertEqual(
            "Invalid argument for shape: not a shape", str(ctx.exception)
        )

    def test_shape_constructor(self):
        shape = Solid.make_box(1, 2, 3)

        expected = shape.bounding_box()
        for bbox in (BoundBox(shape), BoundBox(shape=shape)):
            self.assertAlmostEqual(bbox.min, expected.min, 7)
            self.assertAlmostEqual(bbox.max, expected.max, 7)

        expected_nonoptimal = shape.bounding_box(optimal=False)
        bbox_nonoptimal = BoundBox(shape, None, False)
        self.assertAlmostEqual(bbox_nonoptimal.min, expected_nonoptimal.min, 7)
        self.assertAlmostEqual(bbox_nonoptimal.max, expected_nonoptimal.max, 7)

    def test_empty_shape_constructor(self):
        empty_shape = Solid()
        expected = empty_shape.bounding_box()

        for bbox in (BoundBox(empty_shape), BoundBox(shape=empty_shape)):
            self.assertIsNone(bbox.wrapped)
            self.assertEqual(bbox.min, expected.min)
            self.assertEqual(bbox.max, expected.max)
            self.assertEqual(bbox.size, expected.size)

    def test_empty_box_predicates(self):
        empty = BoundBox(Solid())
        box = self._box((0, 0, 0), (1, 1, 1))

        self.assertFalse(empty.covers(box))
        self.assertFalse(empty.covered_by(box))
        self.assertFalse(empty.contains(box))
        self.assertFalse(empty.contains_properly(box))
        self.assertFalse(empty.within(box))
        self.assertFalse(empty.intersects(box))
        self.assertTrue(empty.disjoint(box))
        self.assertFalse(empty.touches(box))
        self.assertFalse(empty.overlaps(box))

    def test_basic_bounding_box(self):
        v = Vertex(1, 1, 1)
        v2 = Vertex(2, 2, 2)
        self.assertEqual(BoundBox, type(v.bounding_box()))
        self.assertEqual(BoundBox, type(v2.bounding_box()))

        bb1 = v.bounding_box().add(v2.bounding_box())

        # OCC uses some approximations
        self.assertAlmostEqual(bb1.size.X, 1.0, 1)
        self.assertAlmostEqual(bb1.measure, 1.0, 5)

        # Test adding to an existing bounding box
        v0 = Vertex(0, 0, 0)
        bb2 = v0.bounding_box().add(v.bounding_box())

        bb3 = bb1.add(bb2)
        self.assertAlmostEqual(bb3.size, (2, 2, 2), 7)
        self.assertAlmostEqual(bb3.measure, 8, 5)

        bb3 = bb2.add((3, 3, 3))
        self.assertAlmostEqual(bb3.size, (3, 3, 3), 7)

        bb3 = bb2.add(Vector(3, 3, 3))
        self.assertAlmostEqual(bb3.size, (3, 3, 3), 7)

        # Test 2D bounding boxes
        bb1 = Vertex(1, 1, 0).bounding_box().add(Vertex(2, 2, 0).bounding_box())
        bb2 = Vertex(0, 0, 0).bounding_box().add(Vertex(3, 3, 0).bounding_box())
        bb3 = Vertex(0, 0, 0).bounding_box().add(Vertex(1.5, 1.5, 0).bounding_box())
        self.assertAlmostEqual(bb2.measure, 9, 5)
        # Test that bb2 contains bb1
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(bb2, BoundBox.find_outside_box_2d(bb1, bb2))
            self.assertEqual(bb2, BoundBox.find_outside_box_2d(bb2, bb1))
        # Test that neither bounding box contains the other
        with self.assertWarns(DeprecationWarning):
            self.assertIsNone(BoundBox.find_outside_box_2d(bb1, bb3))

        # Test creation of a bounding box from a shape - note the low accuracy comparison
        # as the box is a little larger than the shape
        bb1 = BoundBox.from_topo_ds(Solid.make_cylinder(1, 1).wrapped, optimal=False)
        self.assertAlmostEqual(bb1.size, (2, 2, 1), 1)

        bb2 = BoundBox.from_topo_ds(
            Solid.make_cylinder(0.5, 0.5).translate((0, 0, 0.1)).wrapped, optimal=False
        )
        self.assertTrue(bb2.within(bb1))

    def test_spatial_predicates(self):
        outer = self._box((0, 0, 0), (3, 3, 3))
        inner = self._box((1, 1, 1), (2, 2, 2))
        partial = self._box((2, 2, 2), (4, 4, 4))
        touching = self._box((3, 0, 0), (4, 1, 1))
        disjoint = self._box((4, 0, 0), (5, 1, 1))
        boundary_face = self._box((0, 0, 0), (3, 3, 0))
        near = self._box((3 + 0.5e-6, 0, 0), (4, 1, 1))

        self.assertTrue(outer.covers(inner))
        self.assertTrue(inner.covered_by(outer))
        self.assertTrue(outer.contains(inner))
        self.assertTrue(inner.within(outer))
        self.assertTrue(outer.contains_properly(inner))
        self.assertTrue(outer.contains(outer))
        self.assertTrue(outer.within(outer))
        self.assertFalse(outer.contains_properly(outer))
        self.assertTrue(outer.covers(boundary_face))
        self.assertTrue(boundary_face.covered_by(outer))
        self.assertFalse(outer.contains(boundary_face))
        self.assertFalse(boundary_face.within(outer))

        self.assertTrue(outer.intersects(partial))
        self.assertTrue(outer.overlaps(partial))
        self.assertFalse(outer.overlaps(outer))
        self.assertFalse(outer.contains(partial))
        self.assertFalse(partial.contains(outer))

        self.assertTrue(outer.intersects(touching))
        self.assertTrue(outer.touches(touching))
        self.assertFalse(outer.overlaps(touching))
        self.assertTrue(outer.disjoint(disjoint))
        self.assertFalse(outer.intersects(disjoint))

        self.assertTrue(outer.intersects(near))
        self.assertFalse(outer.overlaps(near))
        self.assertTrue(outer.disjoint(near, tolerance=0.0))

        diagonal_near = self._box((3 + 0.8e-6, 3 + 0.8e-6, 0), (4, 4, 1))
        self.assertFalse(outer.intersects(diagonal_near))
        self.assertTrue(outer.disjoint(diagonal_near))

        with self.assertWarns(DeprecationWarning):
            self.assertTrue(inner.is_inside(outer))

    def test_lower_dimensional_predicates(self):
        outer_rectangle = self._box((0, 0, 0), (3, 3, 0))
        inner_rectangle = self._box((1, 1, 0), (2, 2, 0))
        partial_rectangle = self._box((2, 2, 0), (4, 4, 0))
        touching_rectangle = self._box((3, 0, 0), (4, 1, 0))
        parallel_rectangle = self._box((0, 0, 1), (3, 3, 1))

        self.assertTrue(outer_rectangle.contains(inner_rectangle))
        self.assertTrue(outer_rectangle.contains_properly(inner_rectangle))
        self.assertTrue(inner_rectangle.within(outer_rectangle))
        self.assertTrue(outer_rectangle.overlaps(partial_rectangle))
        self.assertTrue(outer_rectangle.touches(touching_rectangle))
        self.assertTrue(outer_rectangle.disjoint(parallel_rectangle))
        self.assertFalse(outer_rectangle.overlaps(parallel_rectangle))

        outer_line = self._box((0, 0, 0), (3, 0, 0))
        inner_line = self._box((1, 0, 0), (2, 0, 0))
        partial_line = self._box((2, 0, 0), (4, 0, 0))
        touching_line = self._box((3, 0, 0), (4, 0, 0))

        self.assertTrue(outer_line.contains(inner_line))
        self.assertTrue(outer_line.contains_properly(inner_line))
        self.assertTrue(outer_line.overlaps(partial_line))
        self.assertTrue(outer_line.touches(touching_line))

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
