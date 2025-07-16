"""
build123d tests

name: test_oriented_bound_box.py
by:   Gumyr
date: February 4, 2025

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

import math
import re
import unittest

from build123d.geometry import Axis, Location, OrientedBoundBox, Plane, Pos, Rot, Vector
from build123d.topology import Edge, Face, Solid
from build123d.objects_part import Box
from build123d.objects_sketch import Polygon


class TestOrientedBoundBox(unittest.TestCase):
    def test_size_and_diagonal(self):
        # Create a unit cube (with one corner at the origin).
        cube = Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)

        # The size property multiplies half-sizes by 2. For a unit cube, expect (1, 1, 1).
        size = obb.size
        self.assertAlmostEqual(size.X, 1.0, places=6)
        self.assertAlmostEqual(size.Y, 1.0, places=6)
        self.assertAlmostEqual(size.Z, 1.0, places=6)

        # The full body diagonal should be sqrt(1^2+1^2+1^2) = sqrt(3).
        expected_diag = math.sqrt(3)
        self.assertAlmostEqual(obb.diagonal, expected_diag, places=6)

        obb.wrapped = None
        self.assertAlmostEqual(obb.diagonal, 0.0, places=6)

    def test_center(self):
        # For a cube made at the origin, the center should be at (0.5, 0.5, 0.5)
        cube = Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)
        center = obb.center()
        self.assertAlmostEqual(center.X, 0.5, places=6)
        self.assertAlmostEqual(center.Y, 0.5, places=6)
        self.assertAlmostEqual(center.Z, 0.5, places=6)

    def test_directions_are_unit_vectors(self):
        # Create a rotated cube so the direction vectors are non-trivial.
        cube = Rot(45, 45, 0) * Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)

        # Check that each primary direction is a unit vector.
        for direction in (obb.x_direction, obb.y_direction, obb.z_direction):
            self.assertAlmostEqual(direction.length, 1.0, places=6)

    def test_is_outside(self):
        # For a unit cube, test a point inside and a point clearly outside.
        cube = Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)

        # Use the cube's center as an "inside" test point.
        center = obb.center()
        self.assertFalse(obb.is_outside(center))

        # A point far away should be outside.
        outside_point = Vector(10, 10, 10)
        self.assertTrue(obb.is_outside(outside_point))

        outside_point._wrapped = None
        with self.assertRaises(ValueError):
            obb.is_outside(outside_point)

    def test_is_completely_inside(self):
        # Create a larger cube and a smaller cube that is centered within it.
        large_cube = Solid.make_box(2, 2, 2)
        small_cube = Solid.make_box(1, 1, 1)
        # Translate the small cube by (0.5, 0.5, 0.5) so its center is at (1,1,1),
        # which centers it within the 2x2x2 cube (whose center is also at (1,1,1)).
        small_cube = Pos(0.5, 0.5, 0.5) * small_cube

        large_obb = OrientedBoundBox(large_cube)
        small_obb = OrientedBoundBox(small_cube)

        # The small box should be completely inside the larger box.
        self.assertTrue(large_obb.is_completely_inside(small_obb))
        # Conversely, the larger box cannot be completely inside the smaller one.
        self.assertFalse(small_obb.is_completely_inside(large_obb))

        large_obb.wrapped = None
        with self.assertRaises(ValueError):
            small_obb.is_completely_inside(large_obb)

    def test_init_from_bnd_obb(self):
        # Test that constructing from an already computed Bnd_OBB works as expected.
        cube = Solid.make_box(1, 1, 1)
        obb1 = OrientedBoundBox(cube)
        # Create a new instance by passing the underlying wrapped object.
        obb2 = OrientedBoundBox(obb1.wrapped)

        # Compare diagonal, size, and center.
        self.assertAlmostEqual(obb1.diagonal, obb2.diagonal, places=6)
        size1 = obb1.size
        size2 = obb2.size
        self.assertAlmostEqual(size1.X, size2.X, places=6)
        self.assertAlmostEqual(size1.Y, size2.Y, places=6)
        self.assertAlmostEqual(size1.Z, size2.Z, places=6)
        center1 = obb1.center()
        center2 = obb2.center()
        self.assertAlmostEqual(center1.X, center2.X, places=6)
        self.assertAlmostEqual(center1.Y, center2.Y, places=6)
        self.assertAlmostEqual(center1.Z, center2.Z, places=6)

    def test_plane(self):
        # Note: Orientation of plan may not be consistent across platforms
        rect = Rot(Z=10) * Face.make_rect(1, 2)
        obb = rect.oriented_bounding_box()
        pln = obb.plane
        self.assertAlmostEqual(abs(pln.z_dir.dot(Vector(0, 0, 1))), 1.0, places=6)
        self.assertTrue(
            any(
                abs(d.dot(Vector(1, 0).rotate(Axis.Z, 10))) > 0.999
                for d in [pln.x_dir, pln.y_dir, pln.z_dir]
            )
        )

    def test_repr(self):
        # Create a simple unit cube OBB.
        obb = OrientedBoundBox(Solid.make_box(1, 1, 1))
        rep = repr(obb)

        # Check that the repr string contains expected substrings.
        self.assertIn("OrientedBoundBox(center=Vector(", rep)
        self.assertIn("size=Vector(", rep)
        self.assertIn("plane=Plane(", rep)

        # Use a regular expression to extract numbers.
        pattern = (
            r"OrientedBoundBox\(center=Vector\((?P<c0>[-\d\.]+), (?P<c1>[-\d\.]+), (?P<c2>[-\d\.]+)\), "
            r"size=Vector\((?P<s0>[-\d\.]+), (?P<s1>[-\d\.]+), (?P<s2>[-\d\.]+)\), "
            r"plane=Plane\(o=\((?P<o0>[-\d\.]+), (?P<o1>[-\d\.]+), (?P<o2>[-\d\.]+)\), "
            r"x=\((?P<x0>[-\d\.]+), (?P<x1>[-\d\.]+), (?P<x2>[-\d\.]+)\), "
            r"z=\((?P<z0>[-\d\.]+), (?P<z1>[-\d\.]+), (?P<z2>[-\d\.]+)\)\)\)"
        )
        m = re.match(pattern, rep)
        self.assertIsNotNone(
            m, "The __repr__ string did not match the expected format."
        )

        # Convert extracted strings to floats.
        center = Vector(
            float(m.group("c0")), float(m.group("c1")), float(m.group("c2"))
        )
        size = Vector(float(m.group("s0")), float(m.group("s1")), float(m.group("s2")))
        # For a unit cube, we expect the center to be (0.5, 0.5, 0.5)
        self.assertAlmostEqual(center.X, 0.5, places=6)
        self.assertAlmostEqual(center.Y, 0.5, places=6)
        self.assertAlmostEqual(center.Z, 0.5, places=6)
        # And the full size to be approximately (1, 1, 1) (floating-point values may vary slightly).
        self.assertAlmostEqual(size.X, 1.0, places=6)
        self.assertAlmostEqual(size.Y, 1.0, places=6)
        self.assertAlmostEqual(size.Z, 1.0, places=6)

    def test_rotated_cube_corners(self):
        # Create a cube of size 2x2x2 rotated by 45 degrees around each axis.
        rotated_cube = Rot(45, 45, 45) * Box(2, 2, 2)

        # Compute the oriented bounding box.
        obb = OrientedBoundBox(rotated_cube)
        corners = obb.corners

        # There should be eight unique corners.
        self.assertEqual(len(corners), 8)

        # The center of the cube should be at or near the origin.
        center = obb.center()

        # For a cube with full side lengths 2, the half-size is 1,
        # so the distance from the center to any corner is sqrt(1^2 + 1^2 + 1^2) = sqrt(3).
        expected_distance = math.sqrt(3)

        # Verify that each corner is at the expected distance from the center.
        for corner in corners:
            distance = (corner - center).length
            self.assertAlmostEqual(distance, expected_distance, places=6)

    def test_planar_face_corners(self):
        """
        Test that a planar face returns four unique corner points.
        """
        # Create a square face of size 2x2 (centered at the origin).
        face = Face.make_rect(2, 2)
        # Compute the oriented bounding box from the face.
        obb = OrientedBoundBox(face)
        corners = obb.corners

        # Convert each Vector to a tuple (rounded for tolerance reasons)
        unique_points = {
            (round(pt.X, 6), round(pt.Y, 6), round(pt.Z, 6)) for pt in corners
        }
        # For a planar (2D) face, we expect 4 unique corners.
        self.assertEqual(
            len(unique_points),
            4,
            f"Expected 4 unique corners for a planar face but got {len(unique_points)}",
        )
        # Check orientation
        for pln in [Plane.XY, Plane.XZ, Plane.YZ]:
            rect = Face.make_rect(1, 2, pln)
            obb = OrientedBoundBox(rect)
            corners = obb.corners
            poly = Polygon(*corners, align=None)
            self.assertAlmostEqual(rect.intersect(poly).area, rect.area, 5)

        for face in Box(1, 2, 3).faces():
            obb = OrientedBoundBox(face)
            corners = obb.corners
            poly = Polygon(*corners, align=None)
            self.assertAlmostEqual(face.intersect(poly).area, face.area, 5)

    def test_line_corners(self):
        """
        Test that a straight line returns two unique endpoints.
        """
        # Create a straight line from (0, 0, 0) to (1, 0, 0).
        line = Edge.make_line(Vector(0, 0, 0), Vector(1, 0, 0))
        # Compute the oriented bounding box from the line.
        obb = OrientedBoundBox(line)
        corners = obb.corners

        # Convert each Vector to a tuple (rounded for tolerance)
        unique_points = {
            (round(pt.X, 6), round(pt.Y, 6), round(pt.Z, 6)) for pt in corners
        }
        # For a line, we expect only 2 unique endpoints.
        self.assertEqual(
            len(unique_points),
            2,
            f"Expected 2 unique corners for a line but got {len(unique_points)}",
        )
        # Check orientation
        for end in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
            line = Edge.make_line((0, 0, 0), end)
            obb = OrientedBoundBox(line)
            corners = obb.corners
            self.assertEqual(len(corners), 2)
            self.assertTrue(Vector(end) in corners)

    def test_location(self):
        # Create a unit cube.
        cube = Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)

        # Get the location property (constructed from the plane).
        loc = obb.location

        # Check that loc is a Location instance.
        self.assertIsInstance(loc, Location)

        # Compare the location's origin with the oriented bounding box center.
        center = obb.center()
        self.assertAlmostEqual(loc.position.X, center.X, places=6)
        self.assertAlmostEqual(loc.position.Y, center.Y, places=6)
        self.assertAlmostEqual(loc.position.Z, center.Z, places=6)

        # Optionally, if the Location preserves the plane's orientation,
        # check that the x and z directions match those of the obb's plane.
        plane = obb.plane
        self.assertAlmostEqual(loc.x_axis.direction.X, plane.x_dir.X, places=6)
        self.assertAlmostEqual(loc.x_axis.direction.Y, plane.x_dir.Y, places=6)
        self.assertAlmostEqual(loc.x_axis.direction.Z, plane.x_dir.Z, places=6)

        self.assertAlmostEqual(loc.z_axis.direction.X, plane.z_dir.X, places=6)
        self.assertAlmostEqual(loc.z_axis.direction.Y, plane.z_dir.Y, places=6)
        self.assertAlmostEqual(loc.z_axis.direction.Z, plane.z_dir.Z, places=6)


if __name__ == "__main__":
    unittest.main()
