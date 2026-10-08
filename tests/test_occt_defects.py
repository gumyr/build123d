"""
build123d tests tracking OpenCascade defects

name: test_occt_defects.py
by:   build123d contributors
date: October 8th 2026

desc:
    One test per open issue labelled `occt`, each a minimal reproduction that
    asserts the correct result. The tests of defects still present in the
    kernel are marked as expected failures; a strict xfail turns into a test
    failure as soon as a new OCCT release fixes the defect, so the issue can be
    closed and the mark removed. Issues whose defect no longer reproduces are
    ordinary tests guarding against a regression.

license:

    Copyright 2026 build123d contributors

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

import math
import re
import tempfile
import unittest
from math import cos, radians, sin, tan
from pathlib import Path

import pytest

from build123d import (
    Align,
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    CenterArc,
    Circle,
    Cylinder,
    Edge,
    Ellipse,
    Face,
    FrameMethod,
    GeomType,
    Helix,
    JernArc,
    Kind,
    Line,
    Location,
    Locations,
    Mode,
    Plane,
    PolarLocations,
    Polyline,
    Pos,
    Rectangle,
    RectangleRounded,
    RegularPolygon,
    Rot,
    Side,
    SlotOverall,
    Solid,
    Sphere,
    Spline,
    Vector,
    add,
    export_step,
    extrude,
    fillet,
    import_step,
    loft,
    make_face,
    make_hull,
    mirror,
    offset,
    revolve,
    sweep,
)


def occt_defect(issue: int, summary: str):
    """Mark a test as failing because of the OpenCascade defect behind an issue"""
    return pytest.mark.xfail(
        reason=f"build123d #{issue}: {summary}", strict=True, raises=BaseException
    )


class TestBooleanSeams(unittest.TestCase):
    """UnifySameDomain after a boolean damages seam-split periodic faces"""

    @occt_defect(1428, "clean() deletes the sphere cap crossed by the seam")
    def test_sphere_minus_box_keeps_all_caps(self):
        caps = Sphere(5) - Box(8, 8, 8)
        self.assertEqual(len(caps.solids()), 6)
        self.assertAlmostEqual(caps.volume, 87.9646, 3)

    @occt_defect(590, "box minus a sphere crossing its seam is invalid")
    def test_box_minus_sphere_dimple(self):
        dimpled = Box(2, 2, 2) - Pos(-1.5) * Sphere(1)
        self.assertTrue(dimpled.is_valid)
        cap_volume = math.pi * 0.5**2 * (3 - 0.5) / 3
        self.assertAlmostEqual(dimpled.volume, 8 - cap_volume, 3)

    @occt_defect(1271, "fusing a bump near the seam of a sphere loses the bump")
    def test_sphere_bump_fuse(self):
        hemisphere = Sphere(
            40, arc_size1=0, arc_size2=90, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        lat, lon = radians(80), radians(12.4)
        bump = Pos(
            39 * sin(lat) * cos(lon), 39 * sin(lat) * sin(lon), 39 * cos(lat)
        ) * Sphere(3)
        bumped = bump + hemisphere
        self.assertTrue(bumped.is_valid)
        self.assertGreater(bumped.volume, hemisphere.volume)

    @occt_defect(1123, "a hole through an extruded arc shell is incomplete")
    def test_hole_through_cylindrical_shell(self):
        inner = CenterArc((0, 0), 50, -30, 60)
        outer = CenterArc((0, 0), 60, -30, 60)
        profile = make_face(
            [inner, outer, Line(inner @ 0, outer @ 0), Line(inner @ 1, outer @ 1)]
        )
        shell = extrude(profile, amount=50)
        tool = Location((50, 0, 25), (0, 90, 0)) * Cylinder(10, 100)
        holed = shell - tool
        self.assertTrue(holed.is_valid)
        self.assertAlmostEqual(shell.volume - holed.volume, math.pi * 10**2 * 10, 0)

    @occt_defect(1363, "a radial hole through a revolved body is invalid")
    def test_radial_hole_through_revolved_body(self):
        base = revolve(Plane.XZ * Rectangle(6, 20, align=Align.MIN), axis=Axis.Z)
        outer = revolve(
            Plane.XZ * Pos(0, 1) * Rectangle(9, 18, align=Align.MIN), axis=Axis.Z
        )
        inner = revolve(
            Plane.XZ * Pos(6, 1) * Rectangle(3, 18, align=Align.MIN),
            axis=Axis((-25, 0, 0), (0, 0, 1)),
        )
        model = base + (outer - inner)
        # the tool's seam lies in the body's seam plane; Rot(X=-90) works
        tool = Pos(0, 0, 10) * Rot(Y=90) * Cylinder(2, 20)
        holed = model - tool
        self.assertTrue(holed.is_valid)
        self.assertGreater(model.volume - holed.volume, 1)

    @occt_defect(902, "mirroring a revolved part creates ghost geometry")
    def test_mirror_of_revolved_part(self):
        with BuildPart() as part:
            with BuildSketch(Plane.YZ) as profile:
                with BuildLine():
                    JernArc((0, 0), (1, 0), 40, 90)
                    Line((0, 46), (42, 46))
                make_hull()
            with BuildSketch(Plane.YZ) as section:
                arc = profile.edges().sort_by(Axis.Y)[:-1].sort_by(Axis.X)[1:]
                make_face(offset(arc, amount=8, side=Side.LEFT))
                Rectangle(46, 16, align=Align.MIN)
                add(profile, mode=Mode.INTERSECT)
            extrude(section.sketch, amount=50)
            fillet(
                part.faces()
                .filter_by(Plane.XY)
                .sort_by(Axis.Y)[0]
                .edges()
                .sort_by(Axis.Y)[-1],
                8,
            )
            revolve(part.faces().sort_by(Axis.X)[0], axis=Axis.Z, revolution_arc=90)
            mirror(about=Plane.YZ.offset(50))
            half_volume = part.part.volume
            mirror(about=Plane.XZ)
        self.assertTrue(part.part.is_valid)
        self.assertAlmostEqual(part.part.volume, 2 * half_volume, 3)


class TestBooleanClassification(unittest.TestCase):
    """Booleans that silently return the wrong operand"""

    @occt_defect(1332, "cutting a helical groove returns an empty shape")
    def test_helical_groove_cut(self):
        pitch, height, radius, depth = 2.0, 10.0, 8.0, 1.0
        path = Helix(
            pitch=pitch, height=height + 2 * pitch, radius=radius, center=(0, 0, -pitch)
        )
        start = path @ 0
        section_plane = Plane(
            origin=start,
            x_dir=Vector(start.X, start.Y, 0).normalized(),
            z_dir=path % 0,
        )
        groove = make_face(
            Polyline([(0.05, -pitch / 4), (0.05, pitch / 4), (-depth, 0)], close=True)
        )
        tool = sweep(section_plane * groove, path=path, is_frenet=True)
        cylinder = Cylinder(
            radius=radius, height=height, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        grooved = cylinder - tool
        self.assertGreater(grooved.volume, 0)
        self.assertLess(grooved.volume, cylinder.volume - 1)

    @occt_defect(1390, "fusing lofts with internally tangent bases loses faces")
    def test_fuse_tangent_lofts(self):
        def elbow(x0: float, x1: float, radius: float) -> Solid:
            path = Spline(
                (x0, 0, 0),
                (x1, 0, 40),
                tangents=((0, 0, 1), (1 if x1 >= x0 else -1, 0, 0)),
            )
            return loft([path.location_at(i / 10) * Circle(radius) for i in range(11)])

        small, large = elbow(-10, -30, 10), elbow(0, 40, 20)
        fused = small + large
        self.assertTrue(fused.is_valid)
        self.assertTrue(fused.is_manifold)
        self.assertGreater(fused.volume, large.volume + 1)

    @occt_defect(1464, "a cut by a plane through an edge of a ruled face is a no-op")
    def test_cut_through_edge_of_ruled_face(self):
        length, width, height = 200, 250, 30
        slope = Polyline(
            (-width / 2, height / 2),
            (-width / 2, -height / 3),
            (-width / 8, height / 2),
            close=True,
        )
        slope_end = Polyline(
            (-width / 2, height / 2),
            (-width / 2, height / 3),
            (-width / 8, height / 2),
            close=True,
        )
        ramp = Polyline(
            (-width / 2, height),
            (-width / 2, height / 6),
            (-width / 8, height / 2),
            (-width / 8, height),
            close=True,
        )

        def tool(start, end, x_start, x_end):
            return loft(
                [
                    make_face(Plane.YZ.offset(x_start) * start),
                    make_face(Plane.YZ.offset(x_end) * end),
                ]
            )

        sloped = (
            Box(length, width, height)
            - tool(slope, slope_end, -width / 2, -width / 20)
            - tool(slope, slope_end, width / 2, width / 20)
        )
        ramped = sloped - tool(ramp, ramp, -width, width)
        self.assertLess(ramped.volume, sloped.volume - 1)


class TestThickSolid(unittest.TestCase):
    """MakeThickSolid fails or returns its input on lofted solids"""

    @occt_defect(1351, "a loft between a profile and its offset cannot be hollowed")
    def test_loft_of_offset_profile(self):
        profile = RectangleRounded(73.2, 41.2, 7)
        lofted = loft([offset(profile, -1).face(), (Pos(Z=40) * profile).face()])
        hollow = offset(lofted, -1, openings=lofted.faces().filter_by(Axis.Z))
        self.assertTrue(hollow.is_valid)
        self.assertLess(hollow.volume, lofted.volume)

    @occt_defect(545, "a loft between two slots is returned un-hollowed or invalid")
    def test_loft_of_slots(self):
        lofted = loft([SlotOverall(10, 6).face(), Pos(Z=4) * SlotOverall(6, 4).face()])
        hollow = offset(lofted, -0.5, openings=lofted.faces().sort_by(Axis.Z)[-1])
        self.assertTrue(hollow.is_valid)
        self.assertLess(hollow.volume, lofted.volume / 2)

    @occt_defect(1469, "a loft with rounded corners open at both ends is invalid")
    def test_loft_of_rounded_hexagons(self):
        lofted = loft(
            [
                fillet(RegularPolygon(20, 6).vertices(), 4),
                Pos(Z=30) * fillet(RegularPolygon(12, 6).vertices(), 3),
            ]
        )
        hollow = offset(lofted, -2, openings=lofted.faces().filter_by(Axis.Z))
        self.assertTrue(hollow.is_valid)
        self.assertLess(hollow.volume, lofted.volume / 2)


class TestOffset2D(unittest.TestCase):
    @occt_defect(568, "an outward intersection offset fails at a sharp reflex vertex")
    def test_outward_offset_of_star(self):
        with BuildSketch() as star:
            with PolarLocations(0, 3, 0, 180):
                Rectangle(100, 1)
        face = star.sketch.face()
        outward = offset(face, 0.5359, kind=Kind.INTERSECTION)
        self.assertTrue(outward.is_valid)
        self.assertEqual(len(outward.faces()), 1)


class TestFillet(unittest.TestCase):
    @occt_defect(955, "two interior edges filleted together give an invalid shape")
    def test_two_interior_edges_together(self):
        back_angle, front_angle = 87, 72
        outline = [
            (21, 0),
            (21 - 80 / tan(radians(back_angle)), 80),
            (-21 + 80 / tan(radians(front_angle)), 80),
            (-21, 10),
            (-21, 0),
            (21, 0),
        ]
        rotation = 90 - back_angle
        pocket = (
            -5 - 42.5 * tan(radians(rotation)),
            42.5 - 21 * tan(radians(rotation)),
        )
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    Polyline(outline)
                make_face()
                with Locations(pocket):
                    Rectangle(42, 65, rotation=rotation, mode=Mode.SUBTRACT)
            extrude(amount=61, both=True)
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    Polyline(outline)
                make_face()
                with Locations(pocket):
                    Rectangle(42, 65, rotation=rotation, mode=Mode.INTERSECT)
            extrude(amount=21, both=True)
        edges = (
            part.part.edges()
            .filter_by(Edge.is_interior)
            .filter_by(Axis.X, tolerance=10)
            .sort_by(Edge.length)[-2:]
        )
        filleted = fillet(edges, 5)
        self.assertTrue(filleted.is_valid)

    @occt_defect(1011, "a fillet spreads over the whole tangent edge chain")
    def test_single_edge_of_tangent_chain(self):
        with BuildPart() as plate:
            with BuildSketch():
                RectangleRounded(80, 150, 10)
                with Locations((-20, 55)):
                    RectangleRounded(25, 25, 2, mode=Mode.SUBTRACT)
            extrude(amount=2)
            face_count = len(plate.part.faces())
            hole = plate.part.faces().sort_by(Axis.Z)[-1].inner_wires()[0]
            fillet(hole.edges().filter_by(GeomType.LINE)[0], 1)
        self.assertEqual(len(plate.part.faces()), face_count + 1)


class TestSweep(unittest.TestCase):
    @occt_defect(1474, "a sweep with a binormal is invalid on OCCT 8.0.1")
    def test_sweep_with_binormal(self):
        path = Line((0, 0, 0), (0, 0, 30))
        binormal = Line((6, 0, 0), (6, 0, 30))
        swept = Solid.sweep_multi(Rectangle(6, 6), path, binormal=binormal)
        self.assertTrue(swept.is_valid)
        self.assertAlmostEqual(swept.volume, 6 * 6 * 30, 3)


class TestStepExport(unittest.TestCase):
    @occt_defect(745, "the STEP writer drops every face that uses an offset curve")
    def test_offset_curves_survive_a_round_trip(self):
        outline = Ellipse(3, 2).face().outer_wire().offset_2d(0.5, as_bspline=False)
        self.assertTrue(all(e.geom_type == GeomType.OFFSET for e in outline.edges()))
        prism = extrude(Face(outline), 1)
        with tempfile.TemporaryDirectory() as tmp:
            step_file = Path(tmp) / "offset_curves.step"
            export_step(prism, step_file)
            imported = import_step(step_file)
        self.assertEqual(len(imported.faces()), len(prism.faces()))
        self.assertAlmostEqual(imported.volume, prism.volume, 3)

    @occt_defect(693, "a reversed face is written with a FACE_BOUND of .F.")
    def test_face_bounds_are_written_forward(self):
        with BuildPart() as puck:
            with BuildSketch():
                Circle(11.15)
            extrude(amount=19, both=True)
            fillet(puck.edges().filter_by(GeomType.CIRCLE), 0.5)
        with tempfile.TemporaryDirectory() as tmp:
            step_file = Path(tmp) / "puck.step"
            export_step(puck.part, step_file)
            bounds = re.findall(
                r"FACE_BOUND\('',#\d+,\.(T|F)\.\)", step_file.read_text()
            )
        self.assertNotIn("F", bounds)


class TestFixedUpstream(unittest.TestCase):
    """Issues whose defect no longer reproduces with the current kernel"""

    def test_corrected_frame_on_polyline(self):
        """build123d #903: GeomFill_CorrectedFrenet hung until OCCT 7.9.2"""
        path = Polyline((-10, -70, 0), (0, -70, 0), (0, -70, -20), (0, -60, -20))
        location = path.location_at(0.5, frame_method=FrameMethod.CORRECTED)
        self.assertAlmostEqual(location.position.Y, -70, 3)

    def test_negative_extrude_fuse(self):
        """build123d #980: UnifySameDomain looped forever until OCCT 7.9"""
        slot_depth, slot_width, platform_depth, key_depth = 23.5, 3.5, 3, 4
        with BuildPart() as clip:

            def slots():
                with Locations((-6.5 - slot_depth, -10, 0)):
                    SlotOverall(
                        17, slot_width, rotation=90, align=(Align.CENTER, Align.MAX)
                    )
                    SlotOverall(8.5, slot_width, align=(Align.MIN, Align.CENTER))

            with BuildSketch():
                slots()
            extrude(amount=-(platform_depth + key_depth))
            with BuildSketch():
                slots()
                with Locations((-6.5, 0, 0)):
                    Rectangle(1, 35, align=(Align.MIN, Align.CENTER))
                make_hull()
            extrude(amount=platform_depth)
        self.assertTrue(clip.part.is_valid)

    def test_helical_sweep_fuse(self):
        """build123d #1064: a helical sweep fused with a filleted disc"""
        helix = Helix(30, 40, 10)
        coil = sweep(Plane(helix @ 0, z_dir=helix % 0) * Circle(1), helix)
        disc = fillet(extrude(Plane.XY.offset(-1.098) * Circle(12), 2).edges(), 0.9)
        fused = coil + disc
        self.assertTrue(fused.is_valid)
        self.assertTrue(fused.is_manifold)
        overlap = (coil & disc).volume
        self.assertAlmostEqual(fused.volume, coil.volume + disc.volume - overlap, 2)


if __name__ == "__main__":
    unittest.main()
