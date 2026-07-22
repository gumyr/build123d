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
from math import asin, degrees, pi, radians, sin

from build123d import *
from build123d.operations_sheet import _hem_parameters


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

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            BuildSheet(thickness=0)
        with self.assertRaises(ValueError):
            BuildSheet(thickness=1, bend_radius=-1)
        with self.assertRaises(ValueError):
            BuildSheet(thickness=1, k_factor=1.5)


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


class TestFlangeErrors(unittest.TestCase):
    def _base(self):
        bs = BuildSheet(thickness=1)
        with bs:
            with BuildSketch():
                Rectangle(20, 20)
        return bs

    def test_bad_length(self):
        bs = self._base()
        edge = bs.faces().sort_by(Axis.Z)[0].edges()[0]
        with self.assertRaises(ValueError):
            flange(edge, length=0, thickness=1)

    def test_bad_angle(self):
        bs = self._base()
        edge = bs.faces().sort_by(Axis.Z)[0].edges()[0]
        with self.assertRaises(ValueError):
            flange(edge, length=5, angle=0, thickness=1)
        with self.assertRaises(ValueError):
            flange(edge, length=5, angle=271, thickness=1)

    def test_bad_radius(self):
        bs = self._base()
        edge = bs.faces().sort_by(Axis.Z)[0].edges()[0]
        with self.assertRaises(ValueError):
            flange(edge, length=5, radius=-1, thickness=1)

    def test_no_edges(self):
        with self.assertRaises(ValueError):
            flange([], length=5, thickness=1)

    def test_non_linear_edge(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Circle(10)
            with self.assertRaises(ValueError):
                flange(bs.faces().sort_by(Axis.Z)[0].edges()[0], length=5)

    def test_thickness_required_in_algebra(self):
        part = extrude(Rectangle(20, 20), 1)
        edge = part.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y)[0]
        with self.assertRaises(ValueError):
            flange(edge, length=5)


class TestFlangeAlgebra(unittest.TestCase):
    def test_algebra_flange(self):
        """flange works without a BuildSheet context"""
        sheet = extrude(Rectangle(100, 60), 1)
        edge = (
            sheet.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
        )
        result = flange(edge, length=10, radius=2, thickness=1)
        sector = (pi / 4) * ((2 + 1) ** 2 - 2**2) * 60
        self.assertAlmostEqual(result.volume, 6000 + sector + 600, 3)
        self.assertEqual(len(result.faces().filter_by(GeomType.CYLINDER)), 2)


class TestHem(unittest.TestCase):
    @staticmethod
    def _sheet_with_edge():
        bs = BuildSheet(thickness=1)
        with bs:
            with BuildSketch():
                Rectangle(100, 60)
        edge = (
            bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
        )
        return bs, edge

    def test_flat_hem_volume(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            hem(edge, hem_type=HemType.FLAT, width=8)
        # flat: radius=0, angle=180, leg = width - (0 + t) = 7
        sector = (pi / 2) * (1**2 - 0**2) * 60  # θ/2·((R+t)²−R²)·L, θ=π
        wall = 7 * 60 * 1
        self.assertAlmostEqual(bs.sheet.volume, 6000 + sector + wall, 3)
        self.assertTrue(bs.sheet.is_valid)

    def test_open_hem(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            hem(edge, hem_type=HemType.OPEN, width=8, opening=2)
        # open: radius=1, angle=180, leg = 8 - (1+1) = 6
        sector = (pi / 2) * (2**2 - 1**2) * 60
        wall = 6 * 60 * 1
        self.assertAlmostEqual(bs.sheet.volume, 6000 + sector + wall, 3)

    def test_rolled_hem(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            hem(edge, hem_type=HemType.ROLLED, radius=3, roll_angle=270)
        sector = (radians(270) / 2) * ((3 + 1) ** 2 - 3**2) * 60
        self.assertAlmostEqual(bs.sheet.volume, 6000 + sector, 3)
        self.assertTrue(bs.sheet.is_valid)

    def test_teardrop_hem_valid(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            hem(edge, hem_type=HemType.TEARDROP, width=12, radius=3)
        self.assertTrue(bs.sheet.is_valid)
        self.assertGreater(bs.sheet.volume, 6000)

    def test_rolled_hem_radius_from_context(self):
        with BuildSheet(thickness=1, bend_radius=3) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                bs.faces().sort_by(Axis.Z)[0].edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            hem(edge, hem_type=HemType.ROLLED, roll_angle=270)
        sector = (radians(270) / 2) * ((3 + 1) ** 2 - 3**2) * 60
        self.assertAlmostEqual(bs.sheet.volume, 6000 + sector, 3)


class TestHemParameters(unittest.TestCase):
    """Numeric tests of the parameter generators (FreeCAD SheetMetalHem.py)"""

    def test_flat(self):
        leg, bend_angle, bend_radius = _hem_parameters(HemType.FLAT, 1, 8, 0, None, None)
        self.assertAlmostEqual(leg, 7, 6)
        self.assertAlmostEqual(bend_angle, 180, 6)
        self.assertAlmostEqual(bend_radius, 0, 6)

    def test_open(self):
        leg, bend_angle, bend_radius = _hem_parameters(HemType.OPEN, 1, 8, 2, None, None)
        self.assertAlmostEqual(leg, 6, 6)
        self.assertAlmostEqual(bend_radius, 1, 6)

    def test_rolled_default_max_angle(self):
        leg, bend_angle, bend_radius = _hem_parameters(
            HemType.ROLLED, 1, None, 0, 3, None
        )
        self.assertAlmostEqual(leg, 0, 6)
        self.assertAlmostEqual(bend_angle, 270 + degrees(asin(3 / 4)), 6)

    def test_teardrop_residual(self):
        """The teardrop leg satisfies FreeCAD's closure equation"""
        t, r, width = 1.0, 3.0, 12.0
        leg, bend_angle, bend_radius = _hem_parameters(
            HemType.TEARDROP, t, width, 0, r, None
        )
        theta = radians(bend_angle - 180) / 2
        residual = leg - width + (r + t) + t * sin(2 * theta)
        self.assertAlmostEqual(residual, 0, 6)

    def test_errors(self):
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.OPEN, 1, 8, -1, None, None)  # negative opening
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.FLAT, 1, 0.5, 0, None, None)  # width too small
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.ROLLED, 1, None, 0, 3, 350)  # roll angle > max
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.TEARDROP, 1, 3, 0, 3, None)  # width < 2(R+t)


class TestMakeBrakeFormedInBuildSheet(unittest.TestCase):
    def test_open_profile_base(self):
        """A BuildLine profile feeds make_brake_formed inside BuildSheet"""
        with BuildSheet(thickness=1) as bs:
            with BuildLine():
                FilletPolyline((0, 0), (20, 0), (20, 15), radius=2)
            make_brake_formed(thickness=1, station_widths=30)
        self.assertTrue(bs.sheet.is_valid)
        self.assertGreater(bs.sheet.volume, 0)
        # bend cylinders stay distinct from flats (forced SkipClean)
        self.assertGreaterEqual(
            len(bs.sheet.faces().filter_by(GeomType.CYLINDER)), 2
        )
        face_count = len(bs.sheet.faces())
        cleaned = copy.copy(bs.sheet)
        cleaned.clean()
        self.assertGreaterEqual(face_count, len(cleaned.faces()))


class TestFlangeExtends(unittest.TestCase):
    def _flange_volume(self, **kwargs):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10, gap1=10, gap2=10, **kwargs)
        return sheet.sheet.volume

    def test_extends_widen_wall_only(self):
        # base 6000 + sector over 40 (gapped) + wall 50 x 10 x 1
        sector = radians(90) / 2 * ((2 + 1) ** 2 - 2**2) * 40
        self.assertAlmostEqual(
            self._flange_volume(extend1=5, extend2=5), 6000 + sector + 500, places=3
        )

    def test_sector_unchanged_by_extends(self):
        # extends add exactly the extra wall material: 2 * (5 x 10 x 1)
        plain = self._flange_volume()
        extended = self._flange_volume(extend1=5, extend2=5)
        self.assertAlmostEqual(extended - plain, 100, places=3)

    def test_negative_extend_rejected(self):
        with self.assertRaises(ValueError):
            self._flange_volume(extend1=-1)


class TestReliefType(unittest.TestCase):
    def test_members(self):
        self.assertEqual(len(ReliefType), 2)
        self.assertEqual(repr(ReliefType.RECTANGLE), "<ReliefType.RECTANGLE>")
        self.assertEqual(repr(ReliefType.ROUND), "<ReliefType.ROUND>")


class TestFlangeMiter(unittest.TestCase):
    SECTOR_60 = radians(90) / 2 * ((2 + 1) ** 2 - 2**2) * 60

    def _flange_volume(self, **kwargs):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10, **kwargs)
        return sheet.sheet.volume

    def test_positive_miters_cut_trapezoid(self):
        # wall = 60x10 minus two 45-degree triangles (10*10/2 each)
        vol = self._flange_volume(miter_angle1=45, miter_angle2=45)
        self.assertAlmostEqual(vol, 6000 + self.SECTOR_60 + 500, places=3)

    def test_negative_miters_widen(self):
        vol = self._flange_volume(miter_angle1=-45, miter_angle2=-45)
        self.assertAlmostEqual(vol, 6000 + self.SECTOR_60 + 700, places=3)

    def test_degenerate_tip_rejected(self):
        # wall width 20 (gaps), 45+45 over length 10 consumes it entirely
        with self.assertRaises(ValueError):
            self._flange_volume(gap1=20, gap2=20, miter_angle1=45, miter_angle2=45)

    def test_angle_range(self):
        with self.assertRaises(ValueError):
            self._flange_volume(miter_angle1=90)
        with self.assertRaises(ValueError):
            self._flange_volume(miter_angle2=-95)


class TestFlangeRelief(unittest.TestCase):
    SECTOR_40 = radians(90) / 2 * ((2 + 1) ** 2 - 2**2) * 40

    def _flange_volume(self, **kwargs):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10, **kwargs)
        return sheet.sheet.volume

    def test_rectangle_relief_volume(self):
        # two notches of 2 x 3 x thickness cut from the base sheet
        vol = self._flange_volume(
            gap1=10, gap2=10, relief=ReliefType.RECTANGLE, relief_size=(2, 3)
        )
        self.assertAlmostEqual(vol, 6000 - 12 + self.SECTOR_40 + 400, places=3)

    def test_relief_default_size(self):
        # defaults to (0.7*t, 0.7*t) -> two notches of 0.49
        vol = self._flange_volume(gap1=10, gap2=10, relief=ReliefType.RECTANGLE)
        self.assertAlmostEqual(vol, 6000 - 0.98 + self.SECTOR_40 + 400, places=3)

    def test_relief_only_at_gapped_end(self):
        sector_50 = radians(90) / 2 * ((2 + 1) ** 2 - 2**2) * 50
        vol = self._flange_volume(
            gap1=10, relief=ReliefType.RECTANGLE, relief_size=(2, 3)
        )
        self.assertAlmostEqual(vol, 6000 - 6 + sector_50 + 500, places=3)

    def test_relief_inside_bend_extra_notch(self):
        # MATERIAL_INSIDE: slab 40x3x1 cut, plus 2 notches (2x3x1) plus
        # 2 offset bands (2x3x1) clearing alongside the shifted wall
        vol = self._flange_volume(
            gap1=10, gap2=10,
            relief=ReliefType.RECTANGLE, relief_size=(2, 3),
            bend_position=BendPosition.MATERIAL_INSIDE,
        )
        self.assertAlmostEqual(
            vol, 6000 - 120 - 12 - 12 + self.SECTOR_40 + 400, places=3
        )

    def test_relief_fan_faces_preserved(self):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10, gap1=10, gap2=10,
                   relief=ReliefType.RECTANGLE, relief_size=(2, 3))
        raw_count = len(sheet.sheet.faces())
        cleaned = copy.copy(sheet.sheet).clean()
        self.assertGreater(raw_count, len(cleaned.faces()))

    def test_relief_errors(self):
        with self.assertRaises(ValueError):  # no gapped end
            self._flange_volume(relief=ReliefType.RECTANGLE)
        with self.assertRaises(ValueError):  # width exceeds the gap
            self._flange_volume(gap1=1, relief=ReliefType.RECTANGLE,
                                relief_size=(2, 3))
        with self.assertRaises(ValueError):  # non-positive size
            self._flange_volume(gap1=10, relief=ReliefType.RECTANGLE,
                                relief_size=(0, 3))
        with self.assertRaises(ValueError):  # relief_size without relief
            self._flange_volume(gap1=10, relief_size=(2, 3))


class TestFlangeRoundRelief(unittest.TestCase):
    SECTOR_40 = radians(90) / 2 * ((2 + 1) ** 2 - 2**2) * 40

    def _flange_volume(self, relief_size):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10, gap1=10, gap2=10,
                   relief=ReliefType.ROUND, relief_size=relief_size)
        return sheet.sheet.volume

    def test_round_relief_volume(self):
        # notch area = w*(d - w/2) + pi*(w/2)^2/2 with w=2, d=3 -> 4 + pi/2
        notches = 2 * (4 + pi / 2)
        self.assertAlmostEqual(
            self._flange_volume((2, 3)),
            6000 - notches + self.SECTOR_40 + 400, places=3,
        )

    def test_round_relief_semicircle_degenerate(self):
        # depth == width/2 -> pure semicircle, area pi/2 each
        self.assertAlmostEqual(
            self._flange_volume((2, 1)),
            6000 - pi + self.SECTOR_40 + 400, places=3,
        )


class TestFlangeNewParamsAlgebra(unittest.TestCase):
    def test_algebra_extends_miter_relief(self):
        """extends, miters and reliefs work without a BuildSheet context"""
        sheet = extrude(Rectangle(100, 60), 1)
        edge = (
            sheet.faces().sort_by(Axis.Z)[0]
            .edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
        )
        result = flange(
            edge, length=10, thickness=1, radius=2,
            gap1=5, gap2=5, extend1=2, miter_angle2=-20,
            relief=ReliefType.ROUND, relief_size=(2, 2),
        )
        self.assertTrue(result.is_valid)
        self.assertGreater(result.volume, 6000)


class TestBuildSheetRegisteredOps(unittest.TestCase):
    """Standard operations registered for BuildSheet preserve bend faces."""

    SECTOR_60 = radians(90) / 2 * ((2 + 1) ** 2 - 2**2) * 60
    BASE_WITH_FLANGE = 6000 + SECTOR_60 + 600  # full-width flange, length 10

    @staticmethod
    def _fan_faces_preserved(part):
        cleaned = copy.copy(part).clean()
        return len(part.faces()) > len(cleaned.faces())

    def test_extrude_subtract(self):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10)
            with BuildSketch(Plane.XY.offset(1), mode=Mode.PRIVATE) as hole:
                Circle(5)
            extrude(hole.sketch, amount=-1, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(
            sheet.sheet.volume, self.BASE_WITH_FLANGE - 25 * pi, places=3
        )
        self.assertTrue(self._fan_faces_preserved(sheet.sheet))

    def test_extrude_without_sketch_raises_value_error(self):
        with BuildSheet(thickness=1) as sheet:
            with BuildSketch():
                Rectangle(10, 10)
            with self.assertRaises(ValueError):
                extrude(amount=5)

    def test_fillet(self):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10)
            corners = sheet.edges().filter_by(Axis.Z).group_by(Axis.X)[-1]
            fillet(corners, radius=5)
        removed = 2 * (25 - 25 * pi / 4)
        self.assertAlmostEqual(
            sheet.sheet.volume, self.BASE_WITH_FLANGE - removed, places=3
        )
        self.assertTrue(self._fan_faces_preserved(sheet.sheet))

    def test_chamfer(self):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10)
            corners = sheet.edges().filter_by(Axis.Z).group_by(Axis.X)[-1]
            chamfer(corners, length=2)
        self.assertAlmostEqual(
            sheet.sheet.volume, self.BASE_WITH_FLANGE - 4, places=3
        )

    def test_add(self):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(100, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[0]
            )
            flange(edge, length=10)
            box = Solid.make_box(10, 10, 10).locate(Location((10, -5, 1)))
            add(box)
        self.assertAlmostEqual(
            sheet.sheet.volume, self.BASE_WITH_FLANGE + 1000, places=3
        )

    def test_mirror(self):
        with BuildSheet(thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                with Locations((25, 0)):
                    Rectangle(50, 60)
            edge = (
                sheet.faces().sort_by(Axis.Z)[0]
                .edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]
            )
            flange(edge, length=10)
            mirror(about=Plane.YZ)
        half = 3000 + self.SECTOR_60 + 600
        self.assertAlmostEqual(sheet.sheet.volume, 2 * half, places=3)
        self.assertTrue(self._fan_faces_preserved(sheet.sheet))


if __name__ == "__main__":
    unittest.main()
