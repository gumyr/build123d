"""
build123d imports

name: test_vector.py
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

# Always equal to any other object, to test that __eq__ cooperation is working
import copy
import math
import unittest

from OCP.gp import gp_Vec, gp_XYZ
from build123d.geometry import Axis, Location, Plane, Pos, Vector
from build123d.topology import Solid, Vertex


class AlwaysEqual:
    def __eq__(self, other):
        return True


class TestVector(unittest.TestCase):
    """Test the Vector methods"""

    def test_vector_constructors(self):
        v1 = Vector(1, 2, 3)
        v2 = Vector((1, 2, 3))
        v3 = Vector(gp_Vec(1, 2, 3))
        v4 = Vector([1, 2, 3])
        v5 = Vector(gp_XYZ(1, 2, 3))
        v5b = Vector(X=1, Y=2, Z=3)
        v5c = Vector(v=gp_XYZ(1, 2, 3))

        for v in [v1, v2, v3, v4, v5, v5b, v5c]:
            self.assertAlmostEqual(v, (1, 2, 3), 4)

        v6 = Vector((1, 2))
        v7 = Vector([1, 2])
        v8 = Vector(1, 2)
        v8b = Vector(X=1, Y=2)

        for v in [v6, v7, v8, v8b]:
            self.assertAlmostEqual(v, (1, 2, 0), 4)

        v9 = Vector()
        self.assertAlmostEqual(v9, (0, 0, 0), 4)

        v9.X = 1.0
        v9.Y = 2.0
        v9.Z = 3.0
        self.assertAlmostEqual(v9, (1, 2, 3), 4)
        self.assertAlmostEqual(Vector(1, 2, 3, 4), (1, 2, 3), 4)

        v10 = Vector(1)
        v11 = Vector((1,))
        v12 = Vector([1])
        v13 = Vector(X=1)
        for v in [v10, v11, v12, v13]:
            self.assertAlmostEqual(v, (1, 0, 0), 4)

        vertex = Vertex(0, 0, 0).moved(Pos(0, 0, 10))
        self.assertAlmostEqual(Vector(vertex), (0, 0, 10), 4)

        with self.assertRaises(TypeError):
            Vector("vector")
        with self.assertRaises(ValueError):
            Vector(x=1)

    def test_vector_rotate(self):
        """Validate vector rotate methods"""
        vector_x = Vector(1, 0, 1).rotate(Axis.X, 45)
        vector_y = Vector(1, 2, 1).rotate(Axis.Y, 45)
        vector_z = Vector(-1, -1, 3).rotate(Axis.Z, 45)
        self.assertAlmostEqual(vector_x, (1, -math.sqrt(2) / 2, math.sqrt(2) / 2), 7)
        self.assertAlmostEqual(vector_y, (math.sqrt(2), 2, 0), 7)
        self.assertAlmostEqual(vector_z, (0, -math.sqrt(2), 3), 7)

    def test_get_signed_angle(self):
        """Verify getSignedAngle calculations with and without a provided normal"""
        a = math.pi / 3
        v1 = Vector(1, 0, 0)
        v2 = Vector(math.cos(a), -math.sin(a), 0)
        d1 = v1.get_signed_angle(v2)
        d2 = v1.get_signed_angle(v2, Vector(0, 0, 1))
        self.assertAlmostEqual(d1, a * 180 / math.pi)
        self.assertAlmostEqual(d2, -a * 180 / math.pi)

    def test_center(self):
        v = Vector(1, 1, 1)
        self.assertAlmostEqual(v, v.center())

    def test_dot(self):
        v1 = Vector(2, 2, 2)
        v2 = Vector(1, -1, 1)
        self.assertEqual(2.0, v1.dot(v2))

    def test_vector_add(self):
        result = Vector(1, 2, 0) + Vector(0, 0, 3)
        self.assertAlmostEqual(result, (1.0, 2.0, 3.0), 3)

    def test_vector_operators(self):
        result = Vector(1, 1, 1) + Vector(2, 2, 2)
        self.assertEqual(Vector(3, 3, 3), result)

        result = Vector(1, 2, 3) - Vector(3, 2, 1)
        self.assertEqual(Vector(-2, 0, 2), result)

        result = Vector(1, 2, 3) * 2
        self.assertEqual(Vector(2, 4, 6), result)

        result = 3 * Vector(1, 2, 3)
        self.assertEqual(Vector(3, 6, 9), result)

        result = Vector(2, 4, 6) / 2
        self.assertEqual(Vector(1, 2, 3), result)

        self.assertEqual(Vector(-1, -1, -1), -Vector(1, 1, 1))

        self.assertEqual(0, abs(Vector(0, 0, 0)))
        self.assertEqual(1, abs(Vector(1, 0, 0)))
        self.assertEqual((1 + 4 + 9) ** 0.5, abs(Vector(1, 2, 3)))

    def test_vector_equals(self):
        a = Vector(1, 2, 3)
        b = Vector(1, 2, 3)
        c = Vector(1, 2, 3.000001)
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertEqual(a, AlwaysEqual())

    def test_vector_not_equal(self):
        a = Vector(1, 2, 3)
        b = Vector(3, 2, 1)
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, object())

    def test_vector_sets(self):
        # Check that equal and hash work the same way to enable sets
        a = Vector(1, 2, 3)
        for i in range(1, 8):
            v = Vector(a.X + 1.0 / (10**i), a.Y, a.Z)
            if v == a:
                self.assertEqual(len(set([a, v])), 1)
            else:
                self.assertEqual(len(set([a, v])), 2)

    def test_vector_distance(self):
        """
        Test line distance from plane.
        """
        v = Vector(1, 2, 3)

        self.assertAlmostEqual(1, v.signed_distance_from_plane(Plane.YZ))
        self.assertAlmostEqual(2, v.signed_distance_from_plane(Plane.ZX))
        self.assertAlmostEqual(3, v.signed_distance_from_plane(Plane.XY))
        self.assertAlmostEqual(-1, v.signed_distance_from_plane(Plane.ZY))
        self.assertAlmostEqual(-2, v.signed_distance_from_plane(Plane.XZ))
        self.assertAlmostEqual(-3, v.signed_distance_from_plane(Plane.YX))

        self.assertAlmostEqual(1, v.distance_to_plane(Plane.YZ))
        self.assertAlmostEqual(2, v.distance_to_plane(Plane.ZX))
        self.assertAlmostEqual(3, v.distance_to_plane(Plane.XY))
        self.assertAlmostEqual(1, v.distance_to_plane(Plane.ZY))
        self.assertAlmostEqual(2, v.distance_to_plane(Plane.XZ))
        self.assertAlmostEqual(3, v.distance_to_plane(Plane.YX))

    def test_vector_project(self):
        """
        Test line projection and plane projection methods of Vector
        """
        decimal_places = 9

        z_dir = Vector(1, 2, 3)
        base = Vector(5, 7, 9)
        x_dir = Vector(1, 0, 0)

        # test passing Plane object
        point = Vector(10, 11, 12).project_to_plane(Plane(base, x_dir, z_dir))
        self.assertAlmostEqual(point, (59 / 7, 55 / 7, 51 / 7), decimal_places)

        # test line projection
        vec = Vector(10, 10, 10)
        line = Vector(3, 4, 5)
        angle = math.radians(vec.get_angle(line))

        vecLineProjection = vec.project_to_line(line)

        self.assertAlmostEqual(
            vecLineProjection.normalized(),
            line.normalized(),
            decimal_places,
        )
        self.assertAlmostEqual(
            vec.length * math.cos(angle), vecLineProjection.length, decimal_places
        )

    def test_vector_not_implemented(self):
        pass

    def test_vector_special_methods(self):
        self.assertEqual(repr(Vector(1, 2, 3)), "Vector(1, 2, 3)")
        self.assertEqual(str(Vector(1, 2, 3)), "Vector(1, 2, 3)")
        self.assertEqual(
            str(Vector(9.99999999999999, -23.649999999999995, -7.37188088351e-15)),
            "Vector(10, -23.65, 0)",
        )

    def test_vector_iter(self):
        self.assertEqual(sum([v for v in Vector(1, 2, 3)]), 6)

    def test_reverse(self):
        self.assertAlmostEqual(Vector(1, 2, 3).reverse(), (-1, -2, -3), 7)

    def test_copy(self):
        v2 = copy.copy(Vector(1, 2, 3))
        v3 = copy.deepcopy(Vector(1, 2, 3))
        self.assertAlmostEqual(v2, (1, 2, 3), 7)
        self.assertAlmostEqual(v3, (1, 2, 3), 7)

    def test_radd(self):
        vectors = [Vector(1, 2, 3), Vector(4, 5, 6), Vector(7, 8, 9)]
        vector_sum = sum(vectors)
        self.assertAlmostEqual(vector_sum, (12, 15, 18), 5)

    def test_hash(self):
        vectors = [Vector(1, 2, 3), Vector(4, 5, 6), Vector(7, 8, 9), Vector(1, 2, 3)]
        unique_vectors = list(set(vectors))
        self.assertEqual(len(vectors), 4)
        self.assertEqual(len(unique_vectors), 3)

    def test_vector_transform(self):
        a = Vector(1, 2, 3)
        pxy = Plane.XY
        pxy_o1 = Plane.XY.offset(1)
        self.assertEqual(a.transform(pxy.forward_transform, is_direction=False), a)
        self.assertEqual(
            a.transform(pxy.forward_transform, is_direction=True), a.normalized()
        )
        self.assertEqual(
            a.transform(pxy_o1.forward_transform, is_direction=False), Vector(1, 2, 2)
        )
        self.assertEqual(
            a.transform(pxy_o1.forward_transform, is_direction=True), a.normalized()
        )
        self.assertEqual(
            a.transform(pxy_o1.reverse_transform, is_direction=False), Vector(1, 2, 4)
        )
        self.assertEqual(
            a.transform(pxy_o1.reverse_transform, is_direction=True), a.normalized()
        )

    def test_intersect(self):
        v1 = Vector(1, 2, 3)
        self.assertAlmostEqual(v1 & Vector(1, 2, 3), (1, 2, 3), 5)
        self.assertIsNone(v1 & Vector(0, 0, 0))

        self.assertAlmostEqual(v1 & Location((1, 2, 3)), (1, 2, 3), 5)
        self.assertIsNone(v1 & Location())

        self.assertAlmostEqual(v1 & Axis((1, 2, 3), (1, 0, 0)), (1, 2, 3), 5)
        self.assertIsNone(v1 & Axis.X)

        self.assertAlmostEqual(v1 & Plane((1, 2, 3)), (1, 2, 3), 5)
        self.assertIsNone(v1 & Plane.XY)

        self.assertAlmostEqual(
            Vector((v1 & Solid.make_box(2, 4, 5)).vertex()), (1, 2, 3), 5
        )
        self.assertIsNone(v1.intersect(Solid.make_box(0.5, 0.5, 0.5)))
        self.assertIsNone(
            Vertex(-10, -10, -10).intersect(Solid.make_box(0.5, 0.5, 0.5))
        )


if __name__ == "__main__":
    unittest.main()
