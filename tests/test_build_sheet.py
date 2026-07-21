"""

build123d BuildSheet tests

name: test_build_sheet.py
by:   Gumyr
date: July 21st 2026

desc: Unit tests for the build123d build_sheet module

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
from math import pi

from build123d import *


class TestBuildSheetBase(unittest.TestCase):
    def test_base_from_sketch(self):
        """A closed sketch region is auto-padded by thickness"""
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
        self.assertTrue(isinstance(bs.sheet, Part))
        self.assertAlmostEqual(bs.sheet.volume, 100 * 60 * 1, 5)

    def test_base_with_hole(self):
        """Mode.SUBTRACT sketch regions cut holes"""
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            with BuildSketch(mode=Mode.SUBTRACT):
                Circle(10)
        self.assertAlmostEqual(bs.sheet.volume, 100 * 60 - pi * 100, 4)

    def test_multiple_regions_fuse(self):
        with BuildSheet(thickness=2) as bs:
            with BuildSketch():
                Rectangle(20, 20)
                with Locations((30, 0)):
                    Rectangle(20, 20)
        self.assertAlmostEqual(bs.sheet.volume, 2 * 20 * 20 * 2, 5)

    def test_defaults(self):
        with BuildSheet(thickness=1.5) as bs:
            with BuildSketch():
                Rectangle(10, 10)
        self.assertAlmostEqual(bs.bend_radius, 1.5, 5)  # defaults to thickness
        self.assertAlmostEqual(bs.k_factor, 0.5, 5)

    def test_workplane_base(self):
        """Sketch on a non-XY workplane pads along that plane's normal"""
        with BuildSheet(Plane.XZ, thickness=1) as bs:
            with BuildSketch(Plane.XZ):
                Rectangle(10, 10)
        self.assertAlmostEqual(bs.sheet.volume, 100, 5)
        self.assertAlmostEqual(abs(bs.sheet.bounding_box().size.Y), 1, 5)

    def test_thickness_required(self):
        with self.assertRaises(TypeError):
            BuildSheet()  # thickness is keyword-required


if __name__ == "__main__":
    unittest.main()
