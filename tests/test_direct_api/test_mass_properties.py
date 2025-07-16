"""
build123d tests

name: test_mass_properties.py
by:   Gumyr
date: January 28, 2025

desc:
    This python module contains tests for shape properties.

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
from build123d.objects_part import Box, Cylinder, Sphere
from build123d.geometry import Align, Axis
from build123d import Sphere, Align, Axis
from math import pi


class TestMassProperties(unittest.TestCase):

    def test_sphere(self):
        r = 2  # Sphere radius
        sphere = Sphere(r)

        # Expected mass properties
        volume = (4 / 3) * pi * r**3
        expected_static_moments = (0, 0, 0)  # COM at (0,0,0)
        expected_inertia = (2 / 5) * volume * r**2  # Ixx = Iyy = Izz

        # Test static moments (should be zero if centered at origin)
        self.assertAlmostEqual(
            sphere.static_moments[0], expected_static_moments[0], places=5
        )
        self.assertAlmostEqual(
            sphere.static_moments[1], expected_static_moments[1], places=5
        )
        self.assertAlmostEqual(
            sphere.static_moments[2], expected_static_moments[2], places=5
        )

        # Test matrix of inertia (diagonal and equal for a sphere)
        inertia_matrix = sphere.matrix_of_inertia
        self.assertAlmostEqual(inertia_matrix[0][0], expected_inertia, places=5)
        self.assertAlmostEqual(inertia_matrix[1][1], expected_inertia, places=5)
        self.assertAlmostEqual(inertia_matrix[2][2], expected_inertia, places=5)

        # Test principal properties (should match matrix of inertia)
        principal_axes, principal_moments = zip(*sphere.principal_properties)
        self.assertAlmostEqual(principal_moments[0], expected_inertia, places=5)
        self.assertAlmostEqual(principal_moments[1], expected_inertia, places=5)
        self.assertAlmostEqual(principal_moments[2], expected_inertia, places=5)

        # Test radius of gyration (should be sqrt(2/5) * r)
        expected_radius_of_gyration = (2 / 5) ** 0.5 * r
        self.assertAlmostEqual(
            sphere.radius_of_gyration(Axis.X), expected_radius_of_gyration, places=5
        )

    def test_cube(self):
        side = 2
        cube = Box(side, side, side, align=Align.CENTER)

        # Expected values
        volume = side**3
        expected_static_moments = (0, 0, 0)  # Centered
        expected_inertia = (1 / 6) * volume * side**2  # Ixx = Iyy = Izz

        # Test inertia matrix (should be diagonal)
        inertia_matrix = cube.matrix_of_inertia
        self.assertAlmostEqual(inertia_matrix[0][0], expected_inertia, places=5)
        self.assertAlmostEqual(inertia_matrix[1][1], expected_inertia, places=5)
        self.assertAlmostEqual(inertia_matrix[2][2], expected_inertia, places=5)

        # Test principal moments (should be equal)
        principal_axes, principal_moments = zip(*cube.principal_properties)
        self.assertAlmostEqual(principal_moments[0], expected_inertia, places=5)
        self.assertAlmostEqual(principal_moments[1], expected_inertia, places=5)
        self.assertAlmostEqual(principal_moments[2], expected_inertia, places=5)

        # Test radius of gyration (should be sqrt(1/6) * side)
        expected_radius_of_gyration = (1 / 6) ** 0.5 * side
        self.assertAlmostEqual(
            cube.radius_of_gyration(Axis.X), expected_radius_of_gyration, places=5
        )

    def test_cylinder(self):
        r, h = 2, 5
        cylinder = Cylinder(r, h, align=Align.CENTER)

        # Expected values
        volume = pi * r**2 * h
        expected_inertia_xx = (1 / 12) * volume * (3 * r**2 + h**2)  # Ixx = Iyy
        expected_inertia_zz = (1 / 2) * volume * r**2  # Iz about Z-axis

        # Test principal moments (should align with Z)
        principal_axes, principal_moments = zip(*cylinder.principal_properties)
        self.assertAlmostEqual(principal_moments[0], expected_inertia_xx, places=5)
        self.assertAlmostEqual(principal_moments[1], expected_inertia_xx, places=5)
        self.assertAlmostEqual(principal_moments[2], expected_inertia_zz, places=5)

        # Test radius of gyration (should be sqrt(I/m))
        expected_radius_x = (expected_inertia_xx / volume) ** 0.5
        expected_radius_z = (expected_inertia_zz / volume) ** 0.5
        self.assertAlmostEqual(
            cylinder.radius_of_gyration(Axis.X), expected_radius_x, places=5
        )
        self.assertAlmostEqual(
            cylinder.radius_of_gyration(Axis.Z), expected_radius_z, places=5
        )


if __name__ == "__main__":
    unittest.main()
