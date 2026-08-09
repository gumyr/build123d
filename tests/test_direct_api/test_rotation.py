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
from build123d.geometry import Rotation


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


if __name__ == "__main__":
    unittest.main()
