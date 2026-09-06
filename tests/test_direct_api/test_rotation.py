"""
build123d imports

name: test_rotation.py
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

from build123d.build_enums import Extrinsic, Intrinsic
from build123d.geometry import Axis, Rotation


class TestRotation(unittest.TestCase):
    def test_rotation_parameters(self):
        r = Rotation(10, 20, 30)
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, 20, Z=30)
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, 20, Z=30, ordering=Intrinsic.XYZ)
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, Y=20, Z=30)
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        r = Rotation((10, 20, 30))
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, 20, 30, Intrinsic.XYZ)
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        r = Rotation((30, 20, 10), Extrinsic.ZYX)
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        r = Rotation((30, 20, 10), ordering=Extrinsic.ZYX)
        self.assertAlmostEqual(r.orientation, (10, 20, 30), 5)
        with self.assertRaises(TypeError):
            Rotation(x=10)


class TestRotationValidation(unittest.TestCase):
    """Every rejection path of the Rotation constructor"""

    def test_too_many_positional_arguments(self):
        cases = {
            "axis-angle": (Axis.Z, 45, "extra"),
            "RotationLike": ((10, 20, 30), Intrinsic.XYZ, "extra"),
            "Euler-angle": (10, 20, 30, Intrinsic.XYZ, "extra"),
        }
        for kind, args in cases.items():
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(TypeError, "Too many arguments"):
                    Rotation(*args)

    def test_invalid_first_positional_argument(self):
        with self.assertRaisesRegex(TypeError, "Invalid positional arguments"):
            Rotation("not a rotation")

    def test_axis_angle_type_checks(self):
        with self.assertRaisesRegex(TypeError, "Axis must be an Axis"):
            Rotation(axis="not an axis", angle=45)
        with self.assertRaisesRegex(TypeError, "Angle must be an int or float"):
            Rotation(axis=Axis.Z, angle="45")

    def test_rotation_like_conflicts_with_euler_angles(self):
        with self.assertRaisesRegex(TypeError, "ambiguous"):
            Rotation(rotation=(10, 20, 30), X=45)

    def test_ordering_must_be_an_enum(self):
        with self.assertRaisesRegex(TypeError, "Extrinsic or Intrinsic"):
            Rotation(rotation=(10, 20, 30), ordering="XYZ")
        with self.assertRaisesRegex(TypeError, "Extrinsic or Intrinsic"):
            Rotation(X=10, ordering="XYZ")

    def test_euler_angles_must_be_numbers(self):
        with self.assertRaisesRegex(TypeError, "Euler angles must be"):
            Rotation(rotation=("a", "b", "c"))
        with self.assertRaisesRegex(TypeError, "Euler angles must be"):
            Rotation(X="a")

    def test_rotation_like_must_be_a_supported_type(self):
        with self.assertRaisesRegex(TypeError, "rotation must be a Rotation"):
            Rotation(rotation=object())


if __name__ == "__main__":
    unittest.main()
