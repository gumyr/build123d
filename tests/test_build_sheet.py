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

import copy
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


class TestFlange(unittest.TestCase):
    def test_flange_90(self):
        """90° flange from a bottom-face edge folds up, exact volume"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            flange(edge, length=10)
        sector = (pi / 4) * ((2 + 1) ** 2 - 2**2) * 60  # θ/2·((R+t)²−R²)·L, θ=π/2
        wall = 10 * 60 * 1
        self.assertAlmostEqual(bs.sheet.volume, 6000 + sector + wall, 3)
        self.assertTrue(bs.sheet.is_valid)
        # folds up (away from the bottom face) and outward
        bbox = bs.sheet.bounding_box()
        self.assertAlmostEqual(bbox.max.Z, 2 + 1 + 10, 3)  # radius+thickness+leg
        self.assertAlmostEqual(bbox.max.X, 50 + 2 + 1, 3)  # edge + radius + thickness

    def test_bend_faces_preserved(self):
        """The fused sheet must keep separate bend faces (no unification)"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            flange(edge, length=10)
        cylinders = bs.sheet.faces().filter_by(GeomType.CYLINDER)
        self.assertEqual(len(cylinders), 2)  # inner and outer bend surface
        face_count = len(bs.sheet.faces())
        cleaned = copy.copy(bs.sheet).clean()  # clean() mutates in place
        self.assertGreater(face_count, len(cleaned.faces()))

    def test_flange_returns_part(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(20, 20)
            result = flange(
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y)[0], length=5
            )
        self.assertTrue(isinstance(result, Part))

    def test_flange_gaps(self):
        """gap1/gap2 trim the bend from the edge ends"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            flange(edge, length=10, gap1=5, gap2=10)
        trimmed = 60 - 5 - 10
        sector = (pi / 4) * ((2 + 1) ** 2 - 2**2) * trimmed
        wall = 10 * trimmed * 1
        self.assertAlmostEqual(bs.sheet.volume, 6000 + sector + wall, 3)

    def test_flange_multi_edge(self):
        """All four edges of the bottom face fold up into a tray"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edges = bs.faces().sort_by(Axis.Z)[0].edges().filter_by(GeomType.LINE)
            flange(edges, length=10, gap1=3.1, gap2=3.1)
        self.assertEqual(len(edges), 4)
        sector_len = (100 - 6.2) + (100 - 6.2) + (60 - 6.2) + (60 - 6.2)
        sector = (pi / 4) * ((2 + 1) ** 2 - 2**2) * sector_len
        walls = 10 * sector_len * 1
        self.assertAlmostEqual(bs.sheet.volume, 6000 + sector + walls, 3)
        self.assertEqual(len(bs.sheet.faces().filter_by(GeomType.CYLINDER)), 8)

    def test_flange_gap_too_big(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(20, 20)
            with self.assertRaises(ValueError):
                flange(
                    bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y)[0],
                    length=5,
                    gap1=15,
                    gap2=15,
                )

    def test_material_inside(self):
        """MATERIAL_INSIDE: flange does not protrude past the original edge"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            flange(edge, length=10, bend_position=BendPosition.MATERIAL_INSIDE)
        bbox = bs.sheet.bounding_box()
        self.assertAlmostEqual(bbox.max.X, 50, 3)  # flush with original edge
        base_after_cut = 6000 - 60 * (2 + 1) * 1  # slab (radius+thickness)·t·L removed
        sector = (pi / 4) * ((2 + 1) ** 2 - 2**2) * 60
        wall = 10 * 60 * 1
        self.assertAlmostEqual(bs.sheet.volume, base_after_cut + sector + wall, 3)

    def test_thickness_outside(self):
        """THICKNESS_OUTSIDE: bend starts radius earlier than MATERIAL_OUTSIDE"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            flange(edge, length=10, bend_position=BendPosition.THICKNESS_OUTSIDE)
        bbox = bs.sheet.bounding_box()
        self.assertAlmostEqual(bbox.max.X, 50 + 1, 3)  # protrudes only by thickness


if __name__ == "__main__":
    unittest.main()
