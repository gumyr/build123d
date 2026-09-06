"""

build123d BuildPart tests

name: build_part_tests.py
by:   Gumyr
date: July 28th 2022

desc: Unit tests for the build123d build_part module

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
from abc import ABC, abstractmethod
from math import pi, sin
from unittest.mock import MagicMock, patch, PropertyMock

from build123d import *
from build123d import LocationList


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class NestedPart(BasePartObject):
    """Composite part used to verify nested BasePartObject isolation."""

    def __init__(self, mode=Mode.ADD, fail=False):
        self.caller_seen = BuildPart._get_context(log=False)
        with BuildPart() as internal_builder:
            self.child = Box(2, 2, 2)
            self.builder_after_child = BuildPart._get_context(log=False)
        self.internal_builder = internal_builder
        if fail:
            raise RuntimeError("nested part failure")
        super().__init__(internal_builder.part, mode=mode)
        self.finished = True

    def _publish_to_context(self, construction):
        assert self.finished
        super()._publish_to_context(construction)


class AbstractPart(ABC, BasePartObject):
    """Exercise ABCMeta compatibility with BaseObjectMeta."""

    @abstractmethod
    def part_kind(self):
        """Identify the concrete part type."""


class ConcretePart(AbstractPart):
    def __init__(self):
        super().__init__(Solid.make_box(1, 1, 1))

    def part_kind(self):
        return "concrete"


class JointedPart(BasePartObject):
    """Custom part with joints created before BasePartObject initialization."""

    def __init__(self, part, rotation=(0, 0, 0), align=None):
        RigidJoint("rigid", part, Location((0, 0, -1)))
        RevoluteJoint("revolute", part, Axis.Z)
        super().__init__(part, rotation=rotation, align=align)


class TestAlign(unittest.TestCase):
    def test_align(self):
        with BuildPart() as max:
            Box(1, 1, 1, align=(Align.MIN, Align.CENTER, Align.MAX))
        bbox = max.part.bounding_box()
        self.assertGreaterEqual(bbox.min.X, 0)
        self.assertLessEqual(bbox.max.X, 1)
        self.assertGreaterEqual(bbox.min.Y, -0.5)
        self.assertLessEqual(bbox.max.Y, 0.5)
        self.assertGreaterEqual(bbox.min.Z, -1)
        self.assertLessEqual(bbox.max.Z, 0)


class TestBasePartObjectFirewall(unittest.TestCase):
    def test_abstract_base_compatibility(self):
        with BuildPart() as builder:
            part = ConcretePart()

        self.assertEqual(part.part_kind(), "concrete")
        self.assertAlmostEqual(builder.part.volume, 1)

    def test_nested_part_publication(self):
        with BuildPart() as outer_builder:
            with Locations((5, 0, 0)):
                nested = NestedPart()

        self.assertIsNone(nested.caller_seen)
        self.assertIs(nested.builder_after_child, nested.internal_builder)
        self.assertAlmostEqual(nested.internal_builder.part.volume, 8)
        self.assertAlmostEqual(outer_builder.part.volume, 8)
        self.assertAlmostEqual(outer_builder.part.center().X, 5)
        self.assertEqual(len(outer_builder.solids()), 1)

    def test_caller_locations_do_not_replicate_nested_parts(self):
        with BuildPart() as outer_builder:
            with Locations((-5, 0, 0), (5, 0, 0)):
                nested = NestedPart()

        self.assertAlmostEqual(nested.internal_builder.part.volume, 8)
        self.assertEqual(len(outer_builder.solids()), 2)
        self.assertEqual(
            [solid.center().X for solid in outer_builder.solids().sort_by(Axis.X)],
            [-5, 5],
        )

    def test_private_part_not_published(self):
        with BuildPart() as outer_builder:
            Box(1, 1, 1)
            NestedPart(mode=Mode.PRIVATE)

        self.assertAlmostEqual(outer_builder.part.volume, 1)

    def test_failed_part_not_published(self):
        with BuildPart() as outer_builder:
            Box(1, 1, 1)
            with self.assertRaisesRegex(RuntimeError, "nested part failure"):
                NestedPart(fail=True)

        self.assertAlmostEqual(outer_builder.part.volume, 1)

    def test_inherited_joints_are_reparented(self):
        custom_part = JointedPart(Cylinder(2, 2))

        self.assertIs(custom_part.joints["rigid"].parent, custom_part)
        self.assertIs(custom_part.joints["revolute"].parent, custom_part)

        target = Box(1, 1, 1)
        RigidJoint("target", target, Location((10, 0, 0)))
        target.joints["target"].connect_to(custom_part.joints["rigid"])
        self.assertTupleAlmostEquals((10, 0, 1), custom_part.location.position, 5)

    def test_inherited_joints_follow_bare_solid_alignment(self):
        custom_part = JointedPart(
            Solid.make_box(2, 4, 6),
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )

        self.assertIs(custom_part.joints["rigid"].parent, custom_part)
        self.assertTupleAlmostEquals(
            (-1, -2, -4), custom_part.joints["rigid"].location.position, 5
        )

    def test_inherited_joints_follow_bare_solid_rotation(self):
        part = Solid.make_cylinder(2, 2, Plane(origin=(0, 0, -1)))
        custom_part = JointedPart(part, rotation=(0, 90, 0))

        self.assertIs(custom_part.joints["rigid"].parent, custom_part)
        self.assertTupleAlmostEquals(
            (-1, 0, 0), custom_part.joints["rigid"].location.position, 5
        )
        self.assertTupleAlmostEquals(
            (1, 0, 0), custom_part.joints["revolute"].relative_axis.direction, 5
        )


class TestMakeBrakeFormed(unittest.TestCase):
    def test_make_brake_formed(self):
        with BuildPart() as bp:
            with BuildLine() as bl:
                Polyline((0, 0), (5, 6), (10, 1))
                fillet(bl.vertices(), 1)
            make_brake_formed(thickness=0.5, station_widths=[1, 2, 3, 4])
        self.assertTrue(bp.part.volume > 0)
        self.assertAlmostEqual(bp.part.bounding_box().max.Z, 4, 2)
        self.assertEqual(len(bp.faces().filter_by(GeomType.PLANE, reverse=True)), 3)

        outline = FilletPolyline((0, 0), (5, 6), (10, 1), radius=1)
        sheet_metal = make_brake_formed(thickness=0.5, station_widths=1, line=outline)
        self.assertAlmostEqual(sheet_metal.bounding_box().max.Z, 1, 2)

    def test_curve_line(self):
        with BuildLine() as bl:
            FilletPolyline((0, 0), (5, 6), (10, 1), radius=1)
        sheet_metal = make_brake_formed(thickness=0.5, station_widths=1, line=bl.line)
        self.assertGreater(sheet_metal.volume, 0)

    def test_single_section(self):
        arc = Edge.make_circle(5, start_angle=0, end_angle=60)
        sheet_metal = make_brake_formed(thickness=0.5, station_widths=1, line=arc)
        self.assertGreater(sheet_metal.volume, 0)

    def test_invalid_line_type(self):
        with self.assertRaisesRegex(ValueError, "either a Curve, Edge or Wire"):
            make_brake_formed(thickness=0.5, station_widths=1, line=Vertex(0, 0, 0))

    def test_no_line(self):
        with self.assertRaisesRegex(ValueError, "A line must be provided"):
            make_brake_formed(thickness=0.5, station_widths=1)

    def test_unsuitable_line(self):
        outline = FilletPolyline((0, 0), (5, 6), (10, 1), radius=1)
        with patch(
            "build123d.operations_part.Plane", side_effect=ValueError("not planar")
        ):
            with self.assertRaisesRegex(ValueError, "line not suitable"):
                make_brake_formed(thickness=0.5, station_widths=1, line=outline)

    def test_invalid_station_widths_type(self):
        outline = FilletPolyline((0, 0), (5, 6), (10, 1), radius=1)
        with self.assertRaisesRegex(TypeError, "single number or an iterable"):
            make_brake_formed(thickness=0.5, station_widths=object(), line=outline)

    def test_wrong_number_of_station_widths(self):
        outline = FilletPolyline((0, 0), (5, 6), (10, 1), radius=1)
        with self.assertRaisesRegex(ValueError, r"# vertices in line \(4\)"):
            make_brake_formed(thickness=0.5, station_widths=[1, 2], line=outline)


class TestPartOperationDraft(unittest.TestCase):

    def setUp(self):
        self.box = Box(10, 10, 10).solid()
        self.sides = self.box.faces().filter_by(Axis.Z, reverse=True)
        self.bottom_face = self.box.faces().sort_by(Axis.Z)[0]
        self.neutral_plane = Plane(self.bottom_face)

    def test_successful_draft(self):
        """Test that a draft operation completes successfully"""
        result = draft(self.sides, self.neutral_plane, 5)
        self.assertIsInstance(result, Part)
        self.assertLess(self.box.volume, result.volume)

        with BuildPart() as draft_box:
            Box(10, 10, 10)
            draft(
                draft_box.faces().filter_by(Axis.Z, reverse=True),
                Plane.XY.offset(-5),
                5,
            )
        self.assertLess(draft_box.part.volume, 1000)

    def test_invalid_face_type(self):
        """Test that a ValueError is raised for unsupported face types"""
        torus = Torus(5, 1).solid()
        with self.assertRaises(ValueError) as cm:
            draft([torus.faces()[0]], self.neutral_plane, 5)

    def test_faces_from_multiple_solids(self):
        """Test that using faces from different solids raises an error"""
        box2 = Box(5, 5, 5).solid()
        mixed = [self.sides[0], box2.faces()[0]]
        with self.assertRaises(ValueError) as cm:
            draft(mixed, self.neutral_plane, 5)
        self.assertIn("same topological parent", str(cm.exception))

    def test_faces_from_multiple_parts(self):
        """Test that using faces from different solids raises an error"""
        box2 = Box(5, 5, 5).solid()
        part: Part = Part() + [self.box, Pos(X=10) * box2]
        mixed = [part.faces().sort_by(Axis.X)[0], part.faces().sort_by(Axis.X)[-1]]
        with self.assertRaises(ValueError) as cm:
            draft(mixed, self.neutral_plane, 5)

    def test_bad_draft_faces(self):
        with self.assertRaises(DraftAngleError):
            draft(self.bottom_face, self.neutral_plane, 10)

    @patch("build123d.topology.three_d.BRepOffsetAPI_DraftAngle")
    def test_draftangleerror_from_solid_draft(self, mock_draft_angle):
        """Simulate a failure in AddDone and catch DraftAngleError"""
        mock_builder = MagicMock()
        mock_builder.AddDone.return_value = False
        mock_builder.ProblematicShape.return_value = "ShapeX"
        mock_draft_angle.return_value = mock_builder

        with self.assertRaises(DraftAngleError) as cm:
            draft(self.sides, self.neutral_plane, 5)


class TestBuildPart(unittest.TestCase):
    """Test the BuildPart Builder derived class"""

    def test_obj_name(self):
        with BuildPart() as test:
            pass
        self.assertEqual(test._obj_name, "part")

    def test_invalid_add_to_context_input(self):
        with self.assertRaises(ValueError):
            with BuildPart() as test:
                test._add_to_context(*[4, 4])

    def test_select_vertices(self):
        """Test vertices()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.vertices()), 8)
            Box(5, 5, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        self.assertEqual(len(test.vertices(Select.LAST)), 8)

    def test_select_edges(self):
        """Test edges()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.edges()), 12)
            Box(5, 5, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        self.assertEqual(len(test.edges(Select.LAST)), 12)

    def test_select_faces(self):
        """Test faces()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.faces()), 6)
            with BuildSketch(test.faces().filter_by(Axis.Z)[-1]):
                Rectangle(5, 5)
            extrude(amount=5)
        self.assertEqual(len(test.faces()), 11)
        self.assertEqual(len(test.faces(Select.LAST)), 6)

    def test_select_solids(self):
        """Test faces()"""
        with BuildPart() as test:
            for i in [5, 10]:
                with Locations((3 * i, 0, 0)):
                    Box(10, 10, i)
            Box(20, 5, 5)
        self.assertEqual(len(test.solids()), 2)
        self.assertEqual(len(test.solids(Select.LAST)), 1)

    def test_mode_add_multiple(self):
        with BuildPart() as test:
            with PolarLocations(30, 5):
                Box(20, 20, 20)
        self.assertAlmostEqual(len(test.solids()), 5)

    def test_mode_subtract(self):
        with BuildPart() as test:
            Box(20, 20, 20)
            Sphere(10, mode=Mode.SUBTRACT)
        self.assertTrue(isinstance(test._obj, Compound))
        self.assertAlmostEqual(test.part.volume, 8000 - (4000 / 3) * pi, 5)

    def test_mode_intersect(self):
        """Note that a negative volume is created"""
        with BuildPart() as test:
            Box(20, 20, 20)
            Sphere(10, mode=Mode.INTERSECT)
        self.assertAlmostEqual(abs(test.part.volume), (4000 / 3) * pi, 5)

    def test_mode_replace(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            Sphere(10, mode=Mode.REPLACE)
        self.assertAlmostEqual(test.part.volume, (4000 / 3) * pi, 5)

    def test_add_pending_faces(self):
        with BuildPart() as test:
            Box(100, 100, 100)
            with BuildSketch(*test.faces()):
                with PolarLocations(10, 5):
                    Circle(2)
        self.assertEqual(len(test.pending_faces), 30)
        # self.assertEqual(sum([len(s.faces()) for s in test.pending_faces]), 30)

    def test_add_pending_edges(self):
        with BuildPart() as test:
            Box(100, 100, 100)
            with BuildLine():
                CenterArc((0, 0), 5, 0, 180)
        self.assertEqual(len(test.pending_edges), 1)

    def test_add_pending_location_count(self):
        with BuildPart() as test:
            with PolarLocations(30, 5):
                self.assertEqual(len(LocationList._get_context().locations), 5)

    def test_named_plane(self):
        with BuildPart(Plane.YZ) as test:
            self.assertTupleAlmostEquals(
                Plane.XY.z_dir,
                (0, 0, 1),
                5,
            )
            self.assertTupleAlmostEquals(
                Plane(test.output_placements[0]).z_dir, (1, 0, 0), 5
            )

    def test_part_transfer_on_exit(self):
        with BuildPart(Plane.XY) as test:
            Box(1, 1, 1)
            with BuildPart(Plane.XY.offset(1)):
                Box(1, 1, 1)
        self.assertAlmostEqual(test.part.volume, 2, 5)


class TestBuildPartExceptions(unittest.TestCase):
    """Test exception handling"""

    def test_invalid_subtract(self):
        with self.assertRaises(RuntimeError):
            with BuildPart():
                Sphere(10, mode=Mode.SUBTRACT)

    def test_invalid_intersect(self):
        with self.assertRaises(RuntimeError):
            with BuildPart():
                Sphere(10, mode=Mode.INTERSECT)


class TestCounterBoreHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterBoreHole(2, 3, 1, 5)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 4 * pi - 9 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterBoreHole(2, 3, 1)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 9 * pi - 9 * pi, 5)

    def test_through_hole_offset_part(self):
        with BuildPart() as test:
            with Locations((0, 0, -100)):
                Box(10, 10, 10)
            CounterBoreHole(2, 3, 1)

        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 10 * pi, 5)


class TestCounterSinkHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterSinkHole(2, 4, 5)
        self.assertLess(test.part.volume, 1000, 5)
        self.assertGreater(test.part.volume, 1000 - 16 * 5 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterSinkHole(2, 4)
        self.assertLess(test.part.volume, 1000, 5)
        self.assertGreater(test.part.volume, 1000 - 16 * 10 * pi, 5)

    def test_through_hole_offset_part(self):
        with BuildPart() as test:
            with Locations((0, 0, -100)):
                Box(10, 10, 10)
            CounterSinkHole(2, 4)

        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 10 * pi, 5)


class TestCylinder(unittest.TestCase):
    def test_simple_cylinder(self):
        with BuildPart() as test:
            Cylinder(2, 10)
        self.assertAlmostEqual(test.part.volume, pi * 2**2 * 10, 5)


class TestExtrude(unittest.TestCase):
    def test_no_faces(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                extrude(amount=1)

    def test_extrude_with_face_input(self):
        with BuildPart() as test:
            with BuildSketch() as f:
                Rectangle(5, 5)
            extrude(*f.sketch.faces(), amount=2.5, both=True)
        self.assertAlmostEqual(test.part.volume, 125, 5)

    def test_extrude_both(self):
        with BuildPart() as test:
            with BuildSketch():
                Rectangle(5, 5)
            extrude(amount=2.5, both=True)
        self.assertAlmostEqual(test.part.volume, 125, 5)

    def test_extrude_until(self):
        with BuildPart() as test:
            Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
            scale(by=(0.8, 0.8, 0.8), mode=Mode.SUBTRACT)
            with BuildSketch():
                Rectangle(1, 1)
            extrude(until=Until.NEXT)
        self.assertAlmostEqual(test.part.volume, 10**3 - 8**3 + 1**2 * 8, 5)

    def test_extrude_until2(self):
        target = Box(10, 5, 5) - Pos(X=2.5) * Cylinder(0.5, 5)
        pln = Plane((7, 0, 7), z_dir=(-1, 0, -1))
        profile = (pln * Circle(1)).face()
        extrusion = extrude(profile, dir=pln.z_dir, until=Until.NEXT, target=target)
        self.assertLess(extrusion.bounding_box().min.Z, 2.5)

    def test_extrude_until3(self):
        with BuildPart() as p:
            with BuildSketch(Plane.XZ):
                Rectangle(8, 8, align=Align.MIN)
                with Locations((1, 1)):
                    Rectangle(7, 7, align=Align.MIN, mode=Mode.SUBTRACT)
            extrude(amount=2, both=True)
            with BuildSketch(
                Plane((-2, 0, -2), x_dir=(0, 1, 0), z_dir=(1, 0, 1))
            ) as profile:
                Rectangle(4, 1)
            extrude(until=Until.NEXT)

        self.assertAlmostEqual(p.part.volume, 72.313, 2)

    def test_extrude_until_errors(self):
        with self.assertRaises(ValueError):
            extrude(
                Rectangle(1, 1),
                until=Until.NEXT,
                dir=(0, 0, 1),
                target=Pos(Z=-10) * Box(1, 1, 1),
            )

    def test_extrude_until_invalid_sewn_shape(self):
        profile = Face.make_rect(1, 1)
        target = Box(2, 2, 2)
        direction = Vector(0, 0, 1)

        bad_shape = Box(1, 1, 1).wrapped  # not a Face or Shell → forces RuntimeError

        with patch(
            "build123d.topology.three_d.get_top_level_topods_shapes",
            return_value=[bad_shape],
        ):
            with self.assertRaises(RuntimeError):
                extrude(profile, dir=direction, until=Until.NEXT, target=target)

    def test_extrude_until_invalid_split(self):
        profile = Face.make_rect(1, 1)
        target = Box(2, 2, 2)
        direction = Vector(0, 0, 1)

        with patch("build123d.topology.three_d.Solid.split", return_value=None):
            with self.assertRaises(RuntimeError):
                extrude(profile, dir=direction, until=Until.NEXT, target=target)

    def test_extrude_face(self):
        with BuildPart(Plane.XZ) as box:
            with BuildSketch(Plane.XZ, mode=Mode.PRIVATE) as square:
                Rectangle(10, 10, align=(Align.CENTER, Align.MIN))
            extrude(square.sketch, amount=10)
        self.assertAlmostEqual(box.part.volume, 10**3, 5)

    def test_extrude_non_planar_face(self):
        cyl = Cylinder(1, 2)
        npf = cyl.split(Plane.XZ).faces().filter_by(GeomType.PLANE, reverse=True)[0]
        test_solid = extrude(npf, amount=3, dir=(0, 1, 0))
        self.assertAlmostEqual(test_solid.volume, 2 * 2 * 3, 5)

    def test_non_planar_face_without_dir(self):
        side = Cylinder(1, 2).faces().filter_by(GeomType.CYLINDER)[0]
        with self.assertRaisesRegex(ValueError, "dir must be provided"):
            extrude(side, amount=0.5)

    def test_no_amount_or_until(self):
        with self.assertRaisesRegex(ValueError, "Either amount or until"):
            extrude(Rectangle(1, 1).face())

    def test_until_without_target(self):
        with self.assertRaisesRegex(ValueError, "A target object must be provided"):
            extrude(Rectangle(1, 1).face(), until=Until.NEXT)

    def test_until_with_empty_context(self):
        with self.assertRaisesRegex(ValueError, "No target object provided"):
            with BuildPart():
                with BuildSketch():
                    Rectangle(1, 1)
                extrude(until=Until.NEXT)


class TestHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                Hole(2, 5)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 5 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                Hole(2)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 10 * pi, 5)

    def test_through_hole_offset_part(self):
        with BuildPart() as test:
            with Locations((0, 0, 100)):
                Box(10, 10, 10)
            hole = Hole(2, mode=Mode.ADD)

        hole_bbox = hole.bounding_box()
        self.assertLessEqual(hole_bbox.min.Z, 95)
        self.assertGreaterEqual(hole_bbox.max.Z, 105)
        self.assertEqual(len(test.part.solids()), 1)


class TestLoft(unittest.TestCase):
    def test_simple_loft(self):
        with BuildPart() as test:
            slice_count = 10
            for i in range(slice_count + 1):
                with BuildSketch(Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))):
                    Circle(10 * sin(i * pi / slice_count) + 5)
            loft()
        self.assertLess(test.part.volume, 225 * pi * 30, 5)
        self.assertGreater(test.part.volume, 25 * pi * 30, 5)

        sections = [
            Face(
                Wire(
                    [
                        Edge.make_circle(10 * sin(i * pi / slice_count) + 5).moved(
                            Location(Vector(0, 0, i * 3))
                        )
                    ]
                )
            )
            for i in range(slice_count + 1)
        ]
        with BuildPart() as test:
            loft(sections)
        self.assertLess(test.part.volume, 225 * pi * 30, 5)
        self.assertGreater(test.part.volume, 25 * pi * 30, 5)

    def test_loft_vertex(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, 3)
            with BuildSketch() as s:
                Rectangle(1, 1)
            loft(sections=[s.sketch, v1], ruled=True)
        self.assertAlmostEqual(test.part.volume, 1, 5)

    def test_loft_vertices(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, 3)
            v2 = Vertex(0, 0, -3)
            with BuildSketch() as s:
                Rectangle(1, 1)
            loft(sections=[v2, s.sketch, v1], ruled=True)
        self.assertAlmostEqual(test.part.volume, 2, 5)

    def test_loft_vertex_face(self):
        v1 = Vertex(0, 0, 3)
        r = Rectangle(1, 1)
        test = loft(sections=[r.face(), v1], ruled=True)
        self.assertAlmostEqual(test.volume, 1, 5)

    def test_loft_invalid_vertex(self):
        lower_section = Face.make_rect(10, 10) - Face.make_rect(8, 8)
        upper_section = Pos(Z=5) * lower_section
        with self.assertRaises(ValueError):
            loft([lower_section, Vertex(0, 0, 2.5), upper_section])

    def test_loft_no_sections_assert(self):
        with BuildPart() as test:
            with self.assertRaises(ValueError):
                loft(sections=[None])

    def test_loft_all_vertices_assert(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, -1)
            v2 = Vertex(0, 0, 2)
            with self.assertRaises(ValueError):
                loft(sections=[v1, v2])

    def test_loft_vertex_middle_assert(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, -1)
            v2 = Vertex(0, 0, 2)
            with BuildSketch() as s:
                Circle(1)
            with self.assertRaises(ValueError):
                loft(sections=[v1, v2, s.sketch])

    def test_loft_with_hole(self):
        lower_section = Face.make_rect(10, 10) - Face.make_rect(8, 8)
        upper_section = Pos(Z=5) * lower_section
        loft_with_hole = loft([lower_section, upper_section])
        self.assertAlmostEqual(loft_with_hole.volume, 10 * 10 * 5 - 8 * 8 * 5, 5)

    def test_loft_with_two_holes(self):
        lower_section = Text("B", font_size=10)
        upper_section = Pos(Z=5) * lower_section
        loft_with_holes = loft([lower_section, upper_section])
        self.assertTrue(loft_with_holes.is_valid)
        self.assertGreater(loft_with_holes.volume, 0)

    def test_loft_with_inconsistent_holes(self):
        lower_section = Text("B", font_size=10)
        upper_section = Pos(Z=5) * Face.make_rect(10, 10)
        with self.assertRaises(ValueError):
            loft([lower_section, upper_section])

    @patch.object(Solid, "is_valid", new_callable=PropertyMock, return_value=False)
    def test_loft_invalid_recovery(self, mock_is_valid):
        section = Face.make_rect(2, 2)
        with self.assertRaisesRegex(RuntimeError, "Failed to create valid loft"):
            loft([section, Pos(Z=1) * section])
        mock_is_valid.assert_called_once()

    @patch("build123d.operations_part.Shell")
    @patch("build123d.operations_part.Solid")
    @patch.object(
        Solid, "is_valid", new_callable=PropertyMock, side_effect=[False, False]
    )
    def test_loft_recovery_remains_invalid(
        self, mock_is_valid, mock_solid_class, mock_shell
    ):
        section = Face.make_rect(2, 2)
        fallback_solid = Solid.make_box(2, 2, 1)
        mock_solid_class.make_loft.return_value = fallback_solid
        mock_solid_class.return_value = fallback_solid

        with patch.object(
            fallback_solid, "clean", wraps=fallback_solid.clean
        ) as mock_clean:
            with self.assertRaisesRegex(RuntimeError, "Failed to create valid loft"):
                loft([section, Pos(Z=1) * section])

        mock_shell.assert_called_once()
        mock_solid_class.assert_called_once()
        self.assertEqual(mock_is_valid.call_count, 2)
        mock_clean.assert_called_once()


class TestProjectWorkplane(unittest.TestCase):
    def test_invalid_context(self):
        with self.assertRaisesRegex(RuntimeError, "only be used from a BuildPart"):
            with BuildSketch():
                project_workplane((0, 0, 0), (1, 0, 0), (0, 0, 1), 10)

    def test_x_dir_perpendicular_to_projection_dir(self):
        screen = MagicMock()
        screen.find_intersection_points.return_value = []
        with patch("build123d.operations_part.Face") as mock_face:
            mock_face.make_rect.return_value = screen
            with self.assertRaisesRegex(ValueError, "x_dir perpendicular"):
                project_workplane((0, 0, 0), (1, 0, 0), (0, 0, 1), 10)


class TestRevolve(unittest.TestCase):
    def test_simple_revolve(self):
        with BuildPart() as test:
            with BuildSketch():
                with BuildLine():
                    l1 = Line((0, 0), (12, 0))
                    l2 = RadiusArc(l1 @ 1, (15, 20), 50)
                    l3 = Spline(
                        l2 @ 1, (22, 40), (20, 50), tangents=(l2 % 1, (-0.75, 1))
                    )
                    l4 = RadiusArc(l3 @ 1, l3 @ 1 + Vector(0, 5), 5)
                    l5 = Spline(
                        l4 @ 1,
                        l4 @ 1 + Vector(2.5, 2.5),
                        l4 @ 1 + Vector(0, 5),
                        tangents=(l4 % 1, (-1, 0)),
                    )
                    Polyline(
                        l5 @ 1,
                        l5 @ 1 + Vector(0, 1),
                        (0, (l5 @ 1).Y + 1),
                        l1 @ 0,
                    )
                make_face()
            revolve(axis=Axis.Y)
        self.assertLess(test.part.volume, 22**2 * pi * 50, 5)
        self.assertGreater(test.part.volume, 144 * pi * 50, 5)

    def test_revolve_with_axis(self):
        with BuildPart() as test:
            with BuildSketch():
                with BuildLine():
                    l1 = Line((0, 0), (0, 12))
                    l2 = RadiusArc(l1 @ 1, (20, 10), 50)
                    l3 = Line(l2 @ 1, (20, 0))
                    l4 = Line(l3 @ 1, l1 @ 0)
                make_face()
            revolve(axis=Axis.X)
        self.assertLess(test.part.volume, 244 * pi * 20, 5)
        self.assertGreater(test.part.volume, 100 * pi * 20, 5)

    def test_revolve_size(self):
        """Verify revolution result matches revolution_arc size and direction"""
        ax = Axis.X
        profile = RegularPolygon(10, 4, align=(Align.CENTER, Align.MIN))
        full_volume = revolve(profile, ax, 360).volume
        sizes = [30, 90, 150, 180, 200, 360, 500, 720, 750]
        sizes = [x * -1 for x in sizes[::-1]] + [0] + sizes
        for size in sizes:
            solid = revolve(profile, axis=ax, revolution_arc=size)

            # Create a rotation edge and and the start tangent normal to the profile
            edge = Edge.make_circle(
                1,
                Plane.YZ,
                0,
                size % 360,
                (
                    AngularDirection.COUNTER_CLOCKWISE
                    if size > 0
                    else AngularDirection.CLOCKWISE
                ),
            )
            sign = (edge % 0).Z

            expected = size % (sign * 360)
            expected = sign * 360 if expected == 0 else expected
            result = edge.length / edge.radius / pi * 180 * sign

            self.assertAlmostEqual(solid.volume, full_volume * abs(expected) / 360)
            self.assertAlmostEqual(expected, result)

    # Invalid test
    # def test_invalid_axis_origin(self):
    #     with BuildPart():
    #         with BuildSketch():
    #             Rectangle(1, 1, align=(Align.MIN, Align.MIN))
    #         with self.assertRaises(ValueError):
    #             revolve(axis=Axis((1, 1, 1), (0, 1, 0)))

    # Invalid test
    # def test_invalid_axis_direction(self):
    #     with BuildPart():
    #         with BuildSketch():
    #             Rectangle(1, 1, align=(Align.MIN, Align.MIN))
    #         with self.assertRaises(ValueError):
    #             revolve(axis=Axis.Z)

    def test_no_profiles(self):
        with self.assertRaisesRegex(ValueError, "No profiles provided"):
            revolve()

        with self.assertRaisesRegex(ValueError, "No profiles provided"):
            with BuildPart():
                revolve()


class TestSection(unittest.TestCase):
    def test_circle(self):
        with BuildPart() as test:
            Sphere(10)
            s = section()
        self.assertAlmostEqual(s.area, 100 * pi, 5)

    def test_custom_plane(self):
        with BuildPart() as test:
            Sphere(10)
            s = section(section_by=Plane.XZ)
        self.assertAlmostEqual(s.area, 100 * pi, 5)

    def test_moved_object(self):
        sec = section(Pos(-100, 100) * Sphere(10), Plane.XY)
        self.assertEqual(len(sec.faces()), 1)
        self.assertAlmostEqual(sec.face().edge().radius, 10, 5)
        self.assertAlmostEqual(sec.face().center(), (-100, 100, 0), 5)

    def test_default_plane_from_context(self):
        with BuildPart() as bp:
            Sphere(10)
            s = section(section_by=None)
        self.assertAlmostEqual(s.area, 100 * pi, 5)

    def test_no_object(self):
        with self.assertRaisesRegex(ValueError, "No object to section"):
            section()

    def test_no_section_planes(self):
        with self.assertRaisesRegex(ValueError, "Plane\\(s\\) must be provide"):
            section(Sphere(1), section_by=None)


class TestSplit(unittest.TestCase):
    def test_split(self):
        with BuildPart() as test:
            Sphere(10)
            split(keep=Keep.TOP)
        self.assertAlmostEqual(test.part.volume, (2 / 3) * 1000 * pi, 5)

    def test_split_both(self):
        with BuildPart() as test:
            Sphere(10)
            split(keep=Keep.BOTH)
        self.assertEqual(len(test.solids()), 2)

    def test_custom_plane(self):
        with BuildPart() as test:
            Sphere(10)
            split(bisect_by=Plane.YZ, keep=Keep.TOP)
        self.assertAlmostEqual(test.part.volume, (2 / 3) * 1000 * pi, 5)

    def test_wrapped_object(self):
        obj = Box(1, 1, 1)
        obj = fillet(obj.edges().group_by(Axis.Z)[-1], 0.1)
        right = split(obj, bisect_by=Plane.YZ, keep=Keep.TOP)
        self.assertLess(right.volume, obj.volume)

    def test_no_objects(self):
        with self.assertRaisesRegex(ValueError, "objects must be provided"):
            split()


class TestThicken(unittest.TestCase):
    def test_thicken(self):
        with BuildPart() as bp:
            with BuildSketch():
                RectangleRounded(10, 10, 1)
            thicken(amount=1)
        self.assertAlmostEqual(bp.part.bounding_box().max.Z, 1, 5)

        non_planar = Sphere(1).faces()[0]
        outer_sphere = thicken(non_planar, amount=0.1)
        self.assertAlmostEqual(outer_sphere.volume, (4 / 3) * pi * (1.1**3 - 1**3), 5)

        wire = JernArc((0, -2), (-1, 0), 1, -180) + JernArc((0, 0), (1, 0), 2, -90)

        surface = sweep((wire ^ 0) * RadiusArc((0, 0), (0, -1), 1), wire)
        part = thicken(surface, 0.4)
        self.assertAlmostEqual(part.volume, 2.241583787221904, 5)

        part = thicken(
            sweep((wire ^ 0) * RadiusArc((0, 0), (0, -1), 1), wire), 0.4, both=True
        )
        self.assertAlmostEqual(part.volume, 4.711747154435256, 5)

    def test_no_amount(self):
        with self.assertRaisesRegex(ValueError, "An amount must be provided"):
            thicken(Rectangle(1, 1).face())

    def test_no_face(self):
        with self.assertRaisesRegex(ValueError, "A face or sketch must be provided"):
            thicken(amount=1)


class TestTorus(unittest.TestCase):
    def test_simple_torus(self):
        with BuildPart() as test:
            Torus(100, 10)
        self.assertAlmostEqual(test.part.volume, pi * 100 * 2 * pi * 100, 5)


class TestWedge(unittest.TestCase):
    def test_simple_wedge(self):
        wedge = Wedge(1, 1, 1, 0, 0, 2, 5)
        self.assertAlmostEqual(wedge.volume, 4.833333333333334, 5)

    def test_invalid_wedge(self):
        with self.assertRaises(ValueError):
            Wedge(0, 1, 1, 0, 0, 2, 5)

        with self.assertRaises(ValueError):
            Wedge(1, 0, 1, 0, 0, 2, 5)

        with self.assertRaises(ValueError):
            Wedge(1, 1, 0, 0, 0, 2, 5)


class TestConvexPolyhedron(unittest.TestCase):
    def test_convex_polyhedron(self):
        with BuildPart() as test:
            Box(30, 20, 20)
            Box(20, 30, 20)
            Box(20, 20, 30)
            with Locations((10, 0, 0)):
                Box(40, 23, 23)
            ConvexPolyhedron(test.vertices())
        self.assertAlmostEqual(test.part.volume, 33876.66666666667, 5)
        self.assertEqual(len(test.faces()), 26)


if __name__ == "__main__":
    unittest.main()
