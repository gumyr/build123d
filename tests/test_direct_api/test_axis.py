"""
build123d imports

name: test_axis.py
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
import unittest

import numpy as np
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt
from build123d.geometry import Axis, Location, Plane, Vector
from build123d.topology import Edge, Vertex


class AlwaysEqual:
    def __eq__(self, other):
        return True


class TestAxis(unittest.TestCase):
    """Test the Axis class"""

    def test_axis_init(self):
        test_axis = Axis((1, 2, 3), (0, 0, 1))
        self.assertAlmostEqual(test_axis.position, (1, 2, 3), 5)
        self.assertAlmostEqual(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis((1, 2, 3), direction=(0, 0, 1))
        self.assertAlmostEqual(test_axis.position, (1, 2, 3), 5)
        self.assertAlmostEqual(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(origin=(1, 2, 3), direction=(0, 0, 1))
        self.assertAlmostEqual(test_axis.position, (1, 2, 3), 5)
        self.assertAlmostEqual(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(Edge.make_line((1, 2, 3), (1, 2, 4)))
        self.assertAlmostEqual(test_axis.position, (1, 2, 3), 5)
        self.assertAlmostEqual(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(edge=Edge.make_line((1, 2, 3), (1, 2, 4)))
        self.assertAlmostEqual(test_axis.position, (1, 2, 3), 5)
        self.assertAlmostEqual(test_axis.direction, (0, 0, 1), 5)

        with self.assertRaises(ValueError):
            Axis("one")
        with self.assertRaises(ValueError):
            Axis("one", "up")
        with self.assertRaises(ValueError):
            Axis(one="up")
        with self.assertRaises(ValueError):
            bad_edge = Edge()
            bad_edge.wrapped = Vertex(0, 1, 2).wrapped
            Axis(edge=bad_edge)
        with self.assertRaises(ValueError):
            Axis(gp_ax1=Edge.make_line((0, 0), (1, 0)))

    def test_axis_from_occt(self):
        occt_axis = gp_Ax1(gp_Pnt(1, 1, 1), gp_Dir(0, 1, 0))
        test_axis = Axis(occt_axis)
        self.assertAlmostEqual(test_axis.position, (1, 1, 1), 5)
        self.assertAlmostEqual(test_axis.direction, (0, 1, 0), 5)

    def test_axis_repr_and_str(self):
        self.assertEqual(repr(Axis.X), "((0.0, 0.0, 0.0),(1.0, 0.0, 0.0))")
        self.assertEqual(str(Axis.Y), "Axis: ((0.0, 0.0, 0.0),(0.0, 1.0, 0.0))")

    def test_axis_copy(self):
        x_copy = copy.copy(Axis.X)
        self.assertAlmostEqual(x_copy.position, (0, 0, 0), 5)
        self.assertAlmostEqual(x_copy.direction, (1, 0, 0), 5)
        x_copy = copy.deepcopy(Axis.X)
        self.assertAlmostEqual(x_copy.position, (0, 0, 0), 5)
        self.assertAlmostEqual(x_copy.direction, (1, 0, 0), 5)

    def test_axis_to_location(self):
        # TODO: Verify this is correct
        x_location = Axis.X.location
        self.assertTrue(isinstance(x_location, Location))
        self.assertAlmostEqual(x_location.position, (0, 0, 0), 5)
        self.assertAlmostEqual(x_location.orientation, (0, 90, 180), 5)

    def test_axis_located(self):
        y_axis = Axis.Z.located(Location((0, 0, 1), (-90, 0, 0)))
        self.assertAlmostEqual(y_axis.position, (0, 0, 1), 5)
        self.assertAlmostEqual(y_axis.direction, (0, 1, 0), 5)

    def test_from_location(self):
        axis = Axis(Location((1, 2, 3), (-90, 0, 0)))
        self.assertAlmostEqual(axis.position, (1, 2, 3), 6)
        self.assertAlmostEqual(axis.direction, (0, 1, 0), 6)

    # def test_axis_to_plane(self):
    #     x_plane = Axis.X.to_plane()
    #     self.assertTrue(isinstance(x_plane, Plane))
    #     self.assertAlmostEqual(x_plane.origin, (0, 0, 0), 5)
    #     self.assertAlmostEqual(x_plane.z_dir, (1, 0, 0), 5)

    def test_axis_is_coaxial(self):
        self.assertTrue(Axis.X.is_coaxial(Axis((0, 0, 0), (1, 0, 0))))
        self.assertFalse(Axis.X.is_coaxial(Axis((0, 0, 1), (1, 0, 0))))
        self.assertFalse(Axis.X.is_coaxial(Axis((0, 0, 0), (0, 1, 0))))

    def test_axis_is_normal(self):
        self.assertTrue(Axis.X.is_normal(Axis.Y))
        self.assertFalse(Axis.X.is_normal(Axis.X))

    def test_axis_is_opposite(self):
        self.assertTrue(Axis.X.is_opposite(Axis((1, 1, 1), (-1, 0, 0))))
        self.assertFalse(Axis.X.is_opposite(Axis.X))

    def test_axis_is_parallel(self):
        self.assertTrue(Axis.X.is_parallel(Axis((1, 1, 1), (1, 0, 0))))
        self.assertFalse(Axis.X.is_parallel(Axis.Y))

    def test_axis_is_skew(self):
        self.assertTrue(Axis.X.is_skew(Axis((0, 1, 1), (0, 0, 1))))
        self.assertFalse(Axis.X.is_skew(Axis.Y))

    def test_axis_is_skew(self):
        # Skew Axes
        self.assertTrue(Axis.X.is_skew(Axis((0, 1, 1), (0, 0, 1))))

        # Perpendicular but intersecting
        self.assertFalse(Axis.X.is_skew(Axis.Y))

        # Parallel coincident axes
        self.assertFalse(Axis.X.is_skew(Axis.X))

        # Parallel but distinct axes
        self.assertTrue(Axis.X.is_skew(Axis((0, 1, 0), (1, 0, 0))))

        # Coplanar but not intersecting
        self.assertTrue(Axis((0, 0, 0), (1, 1, 0)).is_skew(Axis((0, 1, 0), (1, 1, 0))))

    def test_axis_angle_between(self):
        self.assertAlmostEqual(Axis.X.angle_between(Axis.Y), 90, 5)
        self.assertAlmostEqual(
            Axis.X.angle_between(Axis((1, 1, 1), (-1, 0, 0))), 180, 5
        )

    def test_axis_reverse(self):
        self.assertAlmostEqual(Axis.X.reverse().direction, (-1, 0, 0), 5)

    def test_axis_reverse_op(self):
        axis = -Axis.X
        self.assertAlmostEqual(axis.direction, (-1, 0, 0), 5)

    def test_axis_as_edge(self):
        edge = Edge(Axis.X)
        self.assertTrue(isinstance(edge, Edge))
        common = (edge & Edge.make_line((0, 0, 0), (1, 0, 0))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

    def test_axis_intersect(self):
        common = (Axis.X.intersect(Edge.make_line((0, 0, 0), (1, 0, 0)))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

        common = (Axis.X & Edge.make_line((0, 0, 0), (1, 0, 0))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

        intersection = Axis.X & Axis((1, 0, 0), (0, 1, 0))
        self.assertAlmostEqual(intersection, (1, 0, 0), 5)

        i = Axis.X & Axis((1, 0, 0), (1, 0, 0))
        self.assertEqual(i, Axis.X)

        # Skew case
        self.assertIsNone(Axis.X.intersect(Axis((0, 1, 1), (0, 0, 1))))

        intersection = Axis((1, 2, 3), (0, 0, 1)) & Plane.XY
        self.assertAlmostEqual(intersection, (1, 2, 0), 5)

        arc = Edge.make_circle(20, start_angle=0, end_angle=180)
        ax0 = Axis((-20, 30, 0), (4, -3, 0))
        intersections = arc.intersect(ax0).vertices().sort_by(Axis.X)
        np.testing.assert_allclose(tuple(intersections[0]), (-5.6, 19.2, 0), 1e-5)
        np.testing.assert_allclose(tuple(intersections[1]), (20, 0, 0), 1e-5)

        intersections = ax0.intersect(arc).vertices().sort_by(Axis.X)
        np.testing.assert_allclose(tuple(intersections[0]), (-5.6, 19.2, 0), 1e-5)
        np.testing.assert_allclose(tuple(intersections[1]), (20, 0, 0), 1e-5)

        i = Axis((0, 0, 1), (1, 1, 1)) & Vector(0.5, 0.5, 1.5)
        self.assertTrue(isinstance(i, Vector))
        self.assertAlmostEqual(i, (0.5, 0.5, 1.5), 5)
        self.assertIsNone(Axis.Y & Vector(2, 0, 0))

        l = Edge.make_line((0, 0, 1), (0, 0, 2)) ^ 1
        i: Location = Axis.Z & l
        self.assertTrue(isinstance(i, Location))
        self.assertAlmostEqual(i.position, l.position, 5)
        self.assertAlmostEqual(i.orientation, l.orientation, 5)

        self.assertIsNone(Axis.Z & Edge.make_line((0, 0, 1), (1, 0, 0)).location_at(1))
        self.assertIsNone(Axis.Z & Edge.make_line((1, 0, 1), (1, 0, 2)).location_at(1))

        # TODO: uncomment when generalized edge to surface intersections are complete
        # non_planar = (
        #     Solid.make_cylinder(1, 10).faces().filter_by(GeomType.PLANE, reverse=True)
        # )
        # intersections = Axis((0, 0, 5), (1, 0, 0)) & non_planar

        # self.assertTrue(len(intersections.vertices(), 2))
        # np.testing.assert_allclose(
        #     intersection.vertices()[0], (-1, 0, 5), 5
        # )
        # np.testing.assert_allclose(
        #     intersection.vertices()[1], (1, 0, 5), 5
        # )

    def test_axis_equal(self):
        self.assertEqual(Axis.X, Axis.X)
        self.assertEqual(Axis.Y, Axis.Y)
        self.assertEqual(Axis.Z, Axis.Z)
        self.assertEqual(Axis.X, AlwaysEqual())

    def test_axis_not_equal(self):
        self.assertNotEqual(Axis.X, Axis.Y)
        random_obj = object()
        self.assertNotEqual(Axis.X, random_obj)

    def test_set(self):
        a0 = Axis((0, 1, 2), (3, 4, 5))
        for i in range(1, 8):
            for j in range(1, 8):
                a1 = Axis(
                    (a0.position.X + 1.0 / (10**i), a0.position.Y, a0.position.Z),
                    (a0.direction.X + 1.0 / (10**j), a0.direction.Y, a0.direction.Z),
                )
                if a0 == a1:
                    self.assertEqual(len(set([a0, a1])), 1)
                else:
                    self.assertEqual(len(set([a0, a1])), 2)

    def test_position_property(self):
        axis = Axis.X
        axis.position = 1, 2, 3
        self.assertAlmostEqual(axis.position, (1, 2, 3))

        axis.position += 1, 2, 3
        self.assertAlmostEqual(axis.position, (2, 4, 6))

        self.assertAlmostEqual(Axis(axis.wrapped).position, (2, 4, 6))

    def test_direction_property(self):
        axis = Axis.X
        axis.direction = 1, 2, 3
        self.assertAlmostEqual(axis.direction, Vector(1, 2, 3).normalized())

        axis.direction += 5, 3, 1
        expected = (Vector(1, 2, 3).normalized() + Vector(5, 3, 1)).normalized()
        self.assertAlmostEqual(axis.direction, expected)

        self.assertAlmostEqual(Axis(axis.wrapped).direction, expected)


if __name__ == "__main__":
    unittest.main()
