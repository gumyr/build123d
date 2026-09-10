"""Tests for the surface-native BuildSheet builder and operations."""

import unittest
from math import asin, degrees, pi, radians, sin, sqrt, tan
from unittest.mock import PropertyMock, patch

from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

from build123d import *
from build123d.operations_sheet import (
    _corner_mirror_plane,
    _flange_separation,
    MIN_BEND_RADIUS,
    _bisection,
    _hem_parameters,
    _outward_direction,
)
from build123d.sheet_utils import reference_radius
from build123d.topology import topo_explore_connected_faces


def right_edge(sheet: Shell) -> Edge:
    """Return the +X edge of an XY rectangular sheet."""
    return sheet.edges().filter_by(Axis.Y).sort_by(Axis.X)[-1]


def materialize(sheet_builder: BuildSheet) -> Part:
    """Thicken a completed BuildSheet through the Algebra API."""
    return thicken(
        sheet_builder.sheet,
        sheet_parameters=sheet_builder.sheet_parameters,
    )


class TestSheetMetalParameters(unittest.TestCase):
    def test_defaults_and_validation(self):
        parameters = SheetMetalParameters(thickness=1)
        self.assertIsNone(parameters.bend_radius)
        self.assertEqual(parameters.resolved_bend_radius, 1)
        self.assertEqual(parameters.k_factor, 0.5)
        self.assertEqual(parameters.sheet_surface, SheetSurface.INSIDE)

        parameters = SheetMetalParameters(thickness=1, bend_radius=2)
        self.assertEqual(parameters.resolved_bend_radius, 2)

        with self.assertRaises(ValueError):
            SheetMetalParameters(thickness=0)
        with self.assertRaises(ValueError):
            SheetMetalParameters(thickness=1, bend_radius=-1)
        with self.assertRaises(ValueError):
            SheetMetalParameters(thickness=1, k_factor=1.5)
        with self.assertRaises(TypeError):
            SheetMetalParameters(thickness=1, sheet_surface="inside")


class TestBuildSheetBase(unittest.TestCase):
    def test_accessors_and_pending_edges(self):
        builder = BuildSheet(thickness=1.5)
        self.assertEqual(builder.thickness, 1.5)
        self.assertIsNone(builder.pending_edges_as_wire)

        first = Shell(Face.make_rect(10, 10))
        builder.sheet = first
        self.assertTrue(builder.sheet.is_same(first))
        second = Shell(Face.make_rect(5, 5))
        builder._obj = second
        self.assertTrue(builder.sheet_local.is_same(second))

        builder._add_to_context(Edge.make_line((0, 0), (1, 0)))
        self.assertIsInstance(builder.pending_edges_as_wire, Wire)

    def test_bends_and_flats(self):
        """A sheet reads as flats joined by bends, so the two selectors say
        that directly rather than by filtering on geometry."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
            flange(builder.edges().filter_by(Axis.X), length=20)

            bends = builder.bends()
            flats = builder.flats()
            self.assertEqual(len(bends), 2)
            self.assertEqual(len(flats), 3)
            self.assertEqual(len(bends) + len(flats), len(builder.faces()))
            self.assertEqual(bends, builder.faces().filter_by(GeomType.CYLINDER))
            self.assertEqual(flats, builder.faces().filter_by(GeomType.PLANE))
            self.assertEqual(
                len(builder.bends(Select.LAST)) + len(builder.flats(Select.LAST)),
                len(builder.faces(Select.LAST)),
            )

    def test_sheet_invariant_errors(self):
        """The sheet invariant lives on Shell, for Builder and Algebra mode alike."""
        self.assertFalse(Shell.make_sheet([]))
        sphere = Solid.make_sphere(1).faces()[0]
        with self.assertRaisesRegex(ValueError, "planar and cylindrical"):
            Shell.make_sheet([sphere])

        cylinder = Solid.make_cylinder(1, 1).faces().filter_by(GeomType.CYLINDER)[0]
        with patch.object(Face, "radius", new_callable=PropertyMock, return_value=0):
            with self.assertRaisesRegex(ValueError, "positive radius"):
                Shell.make_sheet([cylinder])

        face = Face.make_rect(10, 10)
        with patch.object(
            Shell, "is_valid", new_callable=PropertyMock, return_value=False
        ):
            with self.assertRaisesRegex(ValueError, "invalid shell"):
                Shell.make_sheet([face])

        with patch(
            "build123d.topology.two_d.topo_explore_connected_faces",
            return_value=[face, face, face],
        ):
            with self.assertRaisesRegex(ValueError, "non-manifold"):
                Shell.make_sheet([face])

        with self.assertRaisesRegex(ValueError, "one connected shell"):
            Shell.make_sheet([face, Pos(50, 0) * Face.make_rect(10, 10)])

    def test_make_sheet_records_the_sewing(self):
        """A sheet made in Algebra mode knows what became of its faces."""
        base = Face.make_rect(20, 20)
        wall = Face.make_rect(
            20, 10, Plane(origin=(10, 0, 5), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        )
        sheet = Shell.make_sheet([base, wall])
        self.assertEqual(len(sheet.faces()), 2)
        sheet._history.with_inputs([base.wrapped], [wall.wrapped])
        self.assertEqual(len(sheet.faces(Select.LAST)), 1)
        self.assertAlmostEqual(sheet.faces(Select.LAST)[0].area, 200, 5)
        # a sewn shell is not the same object as its faces; the record joins them
        self.assertEqual(len(sheet.edges(Select.LAST)), 4)

    def test_cut_sheet(self):
        """Solids cut every face they pass through, faces only where coplanar."""
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(40, 20)
            flange(bs.edges().sort_by(Axis.X)[-1], length=10)
        sheet = bs.sheet
        pierced = sheet.cut_sheet(Cylinder(1, 40, rotation=(0, 90, 0)))
        self.assertTrue(pierced.is_valid)
        self.assertLess(pierced.area, sheet.area)
        self.assertEqual(len(pierced.bends()), 1)
        notched = sheet.cut_sheet(Pos(0, 5) * Face.make_rect(4, 4))
        self.assertAlmostEqual(notched.area, sheet.area - 16, 5)
        with self.assertRaisesRegex(ValueError, "coplanar"):
            sheet.cut_sheet(Pos(0, 0, 3) * Face.make_rect(4, 4))

    def test_context_modes_and_empty_inputs(self):
        builder = BuildSheet(thickness=1)
        face = Face.make_rect(10, 10)
        builder._add_to_context(None, mode=Mode.ADD)
        self.assertFalse(builder.sheet_local)
        builder._add_to_context(face, mode=Mode.PRIVATE)
        self.assertFalse(builder.sheet_local)
        with self.assertRaisesRegex(RuntimeError, "Nothing to subtract"):
            builder._add_to_context(face, mode=Mode.SUBTRACT)
        with self.assertRaisesRegex(ValueError, "Mode.INTERSECT"):
            builder._add_to_context(face, mode=Mode.INTERSECT)
        builder._add_to_context(face, mode=Mode.REPLACE)
        self.assertAlmostEqual(builder.sheet_local.area, 100, 5)
        with self.assertRaisesRegex(ValueError, "only as cutters"):
            builder._add_to_context(Solid.make_box(1, 1, 1))

    def test_an_empty_builder_publishes_nothing(self):
        """Before anything is built the output is None, as it is for every
        other Builder; the local shell is an empty Shell throughout."""
        with BuildSheet(thickness=1) as builder:
            self.assertIsNone(builder.sheet)
            self.assertFalse(builder.sheet_local)
        self.assertIsNone(builder.sheet)
        self.assertFalse(builder.sheet_local)

    def test_merge_coplanar_faces_leaves_non_face_fuse_result(self):
        faces = [Face.make_rect(10, 10), Pos(10, 0) * Face.make_rect(10, 10)]
        with patch.object(Face, "fuse", return_value=Compound(faces)):
            self.assertEqual(
                len(Shell.make_sheet(faces, merge_coplanar=True).faces()), 2
            )
        self.assertEqual(len(Shell.make_sheet(faces, merge_coplanar=True).faces()), 1)

    def test_base_from_sketch(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            self.assertIsInstance(bs.sheet_local, Shell)
            self.assertEqual(len(bs.sheet_local.faces()), 1)
            self.assertAlmostEqual(bs.sheet_local.area, 6000, 5)

        self.assertIsInstance(bs.sheet, Shell)
        self.assertAlmostEqual(materialize(bs).volume, 6000, 5)

    def test_base_with_hole(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            with BuildSketch(mode=Mode.SUBTRACT):
                Circle(10)

        expected_area = 100 * 60 - pi * 100
        self.assertAlmostEqual(bs.sheet.area, expected_area, 5)
        self.assertAlmostEqual(materialize(bs).volume, expected_area, 4)

    def test_touching_coplanar_sketches_merge(self):
        with BuildSheet(thickness=2) as bs:
            with BuildSketch():
                Rectangle(10, 10)
            with BuildSketch():
                with Locations((10, 0)):
                    Rectangle(10, 10)

        self.assertEqual(len(bs.sheet.faces()), 1)
        self.assertAlmostEqual(bs.sheet.area, 200, 5)
        self.assertAlmostEqual(materialize(bs).volume, 400, 5)

    def test_disconnected_addition_is_atomic(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(10, 10)
            original = bs.sheet_local
            with self.assertRaisesRegex(ValueError, "connected shell"):
                with BuildSketch():
                    with Locations((20, 0)):
                        Rectangle(10, 10)
            self.assertTrue(bs.sheet_local.is_same(original))
            self.assertAlmostEqual(bs.sheet_local.area, 100, 5)

    def test_defaults_and_invalid_parameters(self):
        with BuildSheet(thickness=1.5) as bs:
            with BuildSketch():
                Rectangle(10, 10)
        self.assertAlmostEqual(bs.bend_radius, 1.5, 5)
        self.assertAlmostEqual(bs.k_factor, 0.5, 5)
        self.assertEqual(bs.sheet_surface, SheetSurface.INSIDE)
        self.assertEqual(bs.sheet_parameters, SheetMetalParameters(thickness=1.5))

        custom = BuildSheet(thickness=1.5, bend_radius=2)
        self.assertEqual(
            custom.sheet_parameters,
            SheetMetalParameters(thickness=1.5, bend_radius=2),
        )
        self.assertEqual(custom.bend_radius, 2)

        with self.assertRaises(TypeError):
            BuildSheet()
        with self.assertRaises(ValueError):
            BuildSheet(thickness=0)
        with self.assertRaises(ValueError):
            BuildSheet(thickness=1, bend_radius=-1)
        with self.assertRaises(ValueError):
            BuildSheet(thickness=1, k_factor=1.5)
        with self.assertRaises(TypeError):
            BuildSheet(thickness=1, sheet_surface="inside")

    def test_workplane_placement(self):
        with BuildSheet(Plane.XZ, thickness=1) as bs:
            with BuildSketch():
                Rectangle(10, 10)

        self.assertAlmostEqual(bs.sheet_local.bounding_box().size.Z, 0, 5)
        self.assertAlmostEqual(bs.sheet.bounding_box().size.Y, 0, 5)
        material = materialize(bs)
        self.assertAlmostEqual(material.bounding_box().size.Y, 1, 5)
        self.assertAlmostEqual(material.volume, 100, 5)

    def test_reference_surface_offsets(self):
        expected_z = {
            SheetSurface.INSIDE: (-2, 0),
            SheetSurface.OUTSIDE: (0, 2),
            SheetSurface.MID: (-1, 1),
            SheetSurface.NEUTRAL: (-1.5, 0.5),
        }
        for sheet_surface, (min_z, max_z) in expected_z.items():
            with self.subTest(sheet_surface=sheet_surface):
                with BuildSheet(
                    thickness=2, sheet_surface=sheet_surface, k_factor=0.25
                ) as bs:
                    with BuildSketch():
                        Rectangle(10, 10)
                bbox = materialize(bs).bounding_box()
                self.assertAlmostEqual(bbox.min.Z, min_z, 5)
                self.assertAlmostEqual(bbox.max.Z, max_z, 5)

    def test_publishes_pending_sheet_to_build_part(self):
        with BuildPart() as parent:
            with BuildSheet(thickness=1) as bs:
                with BuildSketch():
                    Rectangle(10, 10)
            self.assertEqual(len(parent.pending_sheets), 1)
            pending_shell, pending_parameters = parent.pending_sheets[0]
            self.assertTrue(pending_shell.is_same(bs.sheet))
            self.assertEqual(pending_parameters, bs.sheet_parameters)
            self.assertFalse(parent.pending_faces)
            self.assertIsNone(parent.part)
            with self.assertRaisesRegex(ValueError, "amount isn't used"):
                thicken(amount=1)
            self.assertEqual(len(parent.pending_sheets), 1)
            with self.assertRaisesRegex(ValueError, "pending BuildSheet"):
                thicken(sheet_parameters=bs.sheet_parameters)
            self.assertEqual(len(parent.pending_sheets), 1)
            thicken()

        self.assertIsInstance(bs.sheet, Shell)
        self.assertAlmostEqual(parent.part.volume, 100, 5)
        self.assertFalse(parent.pending_sheets)

    def test_algebra_sheet_thicken_validation(self):
        sheet = Shell(Face.make_rect(10, 10))
        parameters = SheetMetalParameters(thickness=1)
        with self.assertRaisesRegex(ValueError, "empty sheet Shell"):
            thicken(Shell(), sheet_parameters=parameters)
        with self.assertRaisesRegex(ValueError, "amount isn't used"):
            thicken(sheet, amount=1, sheet_parameters=parameters)
        with self.assertRaisesRegex(TypeError, "SheetMetalParameters"):
            thicken(sheet, sheet_parameters="parameters")
        with self.assertRaisesRegex(ValueError, "normal_override and both"):
            thicken(sheet, both=True, sheet_parameters=parameters)
        with self.assertRaisesRegex(ValueError, "requires a sheet Shell"):
            thicken(Face.make_rect(10, 10), sheet_parameters=parameters)
        with self.assertRaisesRegex(ValueError, "amount must be provided"):
            thicken(Face.make_rect(10, 10))
        with self.assertRaisesRegex(ValueError, "face or sketch"):
            thicken(amount=1)
        with patch.object(
            Part, "is_valid", new_callable=PropertyMock, return_value=False
        ):
            with self.assertRaisesRegex(ValueError, "valid material"):
                thicken(sheet, sheet_parameters=parameters)


class TestInsert(unittest.TestCase):
    def test_insert_face(self):
        with BuildSheet(thickness=1) as bs:
            result = insert(Face.make_rect(10, 10))

        self.assertIsInstance(result, Compound)
        self.assertIsInstance(bs.sheet, Shell)
        self.assertAlmostEqual(bs.sheet.area, 100, 5)
        self.assertAlmostEqual(materialize(bs).volume, 100, 5)

    def test_insert_shell(self):
        reusable_sheet = Shell(Face.make_rect(10, 10))
        with BuildSheet(thickness=1) as bs:
            insert(reusable_sheet)

        self.assertEqual(len(bs.sheet.faces()), 1)
        self.assertAlmostEqual(materialize(bs).volume, 100, 5)

    def test_insert_build_sheet(self):
        with BuildSheet(thickness=1, sheet_surface=SheetSurface.NEUTRAL) as source:
            with BuildSketch():
                Rectangle(10, 10)

        with BuildSheet(thickness=1, sheet_surface=SheetSurface.NEUTRAL) as target:
            insert(source)

        self.assertAlmostEqual(target.sheet.area, source.sheet.area, 5)
        self.assertAlmostEqual(
            materialize(target).volume, materialize(source).volume, 5
        )

    def test_insert_uses_3d_rotation_and_locations(self):
        with BuildSheet(thickness=1) as bs:
            with Locations((0, 5, 0)):
                insert(Face.make_rect(10, 10), rotation=(90, 0, 0))

        bbox = bs.sheet.bounding_box()
        self.assertAlmostEqual(bbox.size.X, 10, 5)
        self.assertAlmostEqual(bbox.size.Y, 0, 5)
        self.assertAlmostEqual(bbox.size.Z, 10, 5)
        self.assertAlmostEqual(bbox.min.Y, 5, 5)
        self.assertAlmostEqual(materialize(bs).bounding_box().size.Y, 1, 5)

    def test_insert_rejects_solid_unless_subtracting(self):
        with BuildSheet(thickness=1):
            with self.assertRaisesRegex(ValueError, "only with Mode.SUBTRACT"):
                insert(Solid.make_box(1, 1, 1))

    def test_inserted_build_sheet_settings_must_match(self):
        with BuildSheet(thickness=1) as source:
            with BuildSketch():
                Rectangle(10, 10)

        with BuildSheet(thickness=2):
            with self.assertRaisesRegex(ValueError, "same sheet parameters"):
                insert(source)

        with BuildSheet(thickness=1, sheet_surface=SheetSurface.OUTSIDE):
            with self.assertRaisesRegex(ValueError, "same sheet parameters"):
                insert(source)

        with BuildSheet(
            thickness=1, sheet_surface=SheetSurface.NEUTRAL, k_factor=0.25
        ) as neutral_source:
            with BuildSketch():
                Rectangle(10, 10)
        with BuildSheet(thickness=1, sheet_surface=SheetSurface.NEUTRAL, k_factor=0.5):
            with self.assertRaisesRegex(ValueError, "same sheet parameters"):
                insert(neutral_source)

    def test_disconnected_insert_is_atomic(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(10, 10)
            original = bs.sheet_local
            disconnected = Face.make_rect(10, 10).translate((20, 0, 0))
            with self.assertRaisesRegex(ValueError, "connected shell"):
                insert(disconnected)
            self.assertTrue(bs.sheet_local.is_same(original))


class TestSolidCutters(unittest.TestCase):
    """Solids trim the reference shell, including across bends"""

    @staticmethod
    def flanged(cut=None):
        """A 100 x 60 base with one 20mm wall, optionally cut"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(
                bs.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1],
                length=20,
            )
            if cut is not None:
                cut(bs)
        return bs.sheet

    @staticmethod
    def bend_center(bs):
        return bs.faces().filter_by(GeomType.CYLINDER)[0].center()

    def assertSheetGeometry(self, sheet):
        """Trimming must not change the supporting surfaces"""
        self.assertIsInstance(sheet, Shell)
        self.assertTrue(sheet.is_valid)
        self.assertEqual(len(sheet.shells()), 1)
        for face in sheet.faces():
            self.assertIn(face.geom_type, (GeomType.PLANE, GeomType.CYLINDER))

    def test_solid_punches_a_hole(self):
        punch = Pos(0, 0, -5) * Cylinder(4, 20)
        sheet = self.flanged(lambda bs: insert(punch, mode=Mode.SUBTRACT))

        self.assertSheetGeometry(sheet)
        self.assertEqual(sum(len(f.inner_wires()) for f in sheet.faces()), 1)
        self.assertAlmostEqual(sheet.area, self.flanged().area - pi * 16, 3)

    def test_solid_cuts_across_a_bend(self):
        """The cut splits the cylindrical face and both halves stay cylinders"""
        notch = Box(6, 30, 30)
        before = self.flanged()
        sheet = self.flanged(
            lambda bs: insert(
                Pos(0, self.bend_center(bs).Y, self.bend_center(bs).Z) * notch,
                mode=Mode.SUBTRACT,
            )
        )

        self.assertSheetGeometry(sheet)
        self.assertEqual(len(sheet.faces()), len(before.faces()) + 1)
        self.assertEqual(
            len(sheet.faces().filter_by(GeomType.CYLINDER)),
            len(before.faces().filter_by(GeomType.CYLINDER)) + 1,
        )
        self.assertLess(sheet.area, before.area)

    def test_solid_relief_notch_at_a_bend_end(self):
        notch = Box(6, 30, 30)
        sheet = self.flanged(
            lambda bs: insert(
                Pos(50, self.bend_center(bs).Y, self.bend_center(bs).Z) * notch,
                mode=Mode.SUBTRACT,
            )
        )

        self.assertSheetGeometry(sheet)
        self.assertLess(sheet.area, self.flanged().area)

    def test_cut_may_not_sever_the_sheet(self):
        sever = Pos(0, 0, -5) * Box(2, 200, 200)
        with self.assertRaisesRegex(ValueError, "connected shell"):
            self.flanged(lambda bs: insert(sever, mode=Mode.SUBTRACT))

    def test_solid_and_face_cutters_together(self):
        punch = Pos(0, 0, -5) * Cylinder(4, 20)
        circle = Pos(30, 0) * Circle(3).face()
        sheet = self.flanged(lambda bs: insert([circle, punch], mode=Mode.SUBTRACT))

        self.assertSheetGeometry(sheet)
        self.assertEqual(sum(len(f.inner_wires()) for f in sheet.faces()), 2)

    def test_solid_cutter_survives_thickening(self):
        punch = Pos(0, 0, -5) * Cylinder(4, 20)
        with BuildPart() as bp:
            with BuildSheet(thickness=1, bend_radius=2) as bs:
                with BuildSketch():
                    Rectangle(100, 60)
                flange(
                    bs.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1],
                    length=20,
                )
                insert(punch, mode=Mode.SUBTRACT)
            thicken()

        self.assertTrue(bp.part.is_valid)
        self.assertEqual(len(bp.part.solids()), 1)

    def test_solid_needs_subtract_mode(self):
        punch = Pos(0, 0, -5) * Cylinder(4, 20)
        for mode in (Mode.ADD, Mode.REPLACE):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "only with Mode.SUBTRACT"):
                    self.flanged(lambda bs: insert(punch, mode=mode))

    def test_face_cutter_coplanar_with_a_folded_wall(self):
        circle = Circle(3).face()

        def cut(bs):
            wall = max(bs.faces().filter_by(GeomType.PLANE), key=lambda f: f.center().Z)
            insert(Plane(wall) * circle, mode=Mode.SUBTRACT)

        sheet = self.flanged(cut)
        self.assertSheetGeometry(sheet)
        self.assertEqual(sum(len(f.inner_wires()) for f in sheet.faces()), 1)

    def test_face_cutter_matching_no_sheet_face_is_reported(self):
        """Previously a silent no-op"""
        orphan = Plane.XZ * Circle(3).face()
        with self.assertRaisesRegex(ValueError, "must be coplanar"):
            self.flanged(lambda bs: insert(orphan, mode=Mode.SUBTRACT))

    def test_part_objects_cut_as_solids(self):
        """Hole and friends work in BuildSheet now that Solids can cut"""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            with GridLocations(50, 50, 2, 2):
                Hole(5)

        sheet = bs.sheet
        self.assertSheetGeometry(sheet)
        self.assertEqual(sum(len(f.inner_wires()) for f in sheet.faces()), 4)
        self.assertAlmostEqual(sheet.area, 100 * 60 - 4 * pi * 25, 5)

    def test_hole_through_a_flanged_sheet(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(
                bs.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1],
                length=20,
            )
            with GridLocations(50, 50, 2, 2):
                Hole(5)

        self.assertSheetGeometry(bs.sheet)
        self.assertEqual(sum(len(f.inner_wires()) for f in bs.sheet.faces()), 4)

    def test_part_object_needs_subtract_mode(self):
        with self.assertRaisesRegex(ValueError, "only as cutters"):
            with BuildSheet(thickness=1) as bs:
                with BuildSketch():
                    Rectangle(100, 60)
                Box(10, 10, 20)

    def test_hole_without_a_sheet_reports_missing_depth(self):
        with self.assertRaisesRegex(ValueError, "No depth provided"):
            with BuildSheet(thickness=1):
                Hole(5)

    def test_holes_survive_thickening(self):
        with BuildPart() as bp:
            with BuildSheet(thickness=1, bend_radius=2) as bs:
                with BuildSketch():
                    Rectangle(100, 60)
                with GridLocations(50, 50, 2, 2):
                    Hole(5)
            thicken()

        self.assertTrue(bp.part.is_valid)
        self.assertAlmostEqual(bp.part.volume, 100 * 60 - 4 * pi * 25, 3)

    def test_repeated_face_cutter_is_accepted(self):
        circle = Circle(3).face()
        sheet = self.flanged(lambda bs: insert([circle, circle], mode=Mode.SUBTRACT))
        self.assertEqual(sum(len(f.inner_wires()) for f in sheet.faces()), 1)


class TestThickenReferenceSurface(unittest.TestCase):
    """Material is one solid whatever surface the shell represents"""

    @staticmethod
    def flanged():
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(
                bs.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1],
                length=20,
            )
        return bs.sheet_local

    def test_every_reference_surface_gives_one_clean_solid(self):
        """MID and NEUTRAL used to fuse two thickened halves, which left the
        reference surface behind as interior faces"""
        sheet = self.flanged()
        counts = {}
        for surface in SheetSurface:
            with self.subTest(surface=surface):
                parameters = SheetMetalParameters(
                    thickness=1, bend_radius=2, sheet_surface=surface, k_factor=0.4
                )
                part = thicken(sheet, sheet_parameters=parameters)
                self.assertTrue(part.is_valid)
                self.assertEqual(len(part.solids()), 1)
                counts[surface] = len(part.faces())

        self.assertEqual(
            len(set(counts.values())),
            1,
            f"face counts differ by reference surface: {counts}",
        )

    def test_material_spans_the_reference_surface_for_mid(self):
        """A MID sheet carries half its thickness either side of the shell"""
        flat = Shell(Face.make_rect(100, 60))
        parameters = SheetMetalParameters(thickness=2, sheet_surface=SheetSurface.MID)
        box = thicken(flat, sheet_parameters=parameters).bounding_box()

        self.assertAlmostEqual(box.min.Z, -1, 5)
        self.assertAlmostEqual(box.max.Z, 1, 5)


class TestGenericOperations(unittest.TestCase):
    def test_chamfer_flange_vertices(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(bs.edges(), length=20, gaps=3.1)
            area_before = bs.sheet_local.area
            vertices = bs.faces().sort_by(Axis.Y).vertices().group_by(Axis.Z)[-1]
            result = chamfer(vertices, 10)

            self.assertIsInstance(result, Shell)
            self.assertLess(bs.sheet_local.area, area_before)
            self.assertTrue(bs.sheet_local.is_valid)
        self.assertTrue(materialize(bs).is_valid)

    def test_fillet_flange_vertices(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(bs.edges(), length=20, gaps=3.1)
            area_before = bs.sheet_local.area
            vertices = bs.faces().sort_by(Axis.Y).vertices().group_by(Axis.Z)[-1]
            result = fillet(vertices, 5)

            self.assertIsInstance(result, Shell)
            self.assertLess(bs.sheet_local.area, area_before)
            self.assertTrue(bs.sheet_local.is_valid)
        self.assertTrue(materialize(bs).is_valid)

    def test_algebra_chamfer_and_fillet_preserve_shell(self):
        for operation in (chamfer, fillet):
            with self.subTest(operation=operation.__name__):
                sheet = flange(
                    Rectangle(100, 60).edges(),
                    length=20,
                    radius=2,
                    gaps=3.1,
                    sheet_parameters=SheetMetalParameters(thickness=1),
                )
                vertices = (
                    sheet.faces().sort_by(Axis.Y)[-1].vertices().group_by(Axis.Z)[-1]
                )
                result = operation(vertices, 5)

                self.assertIsInstance(result, Shell)
                self.assertTrue(result.is_valid)
                self.assertLess(result.area, sheet.area)

    def test_algebra_chamfer_then_miter(self):
        sheet = flange(
            Rectangle(100, 60).edges(),
            length=20,
            radius=2,
            gaps=3.1,
            sheet_parameters=SheetMetalParameters(thickness=1),
        )
        sheet = chamfer(
            sheet.faces().sort_by(Axis.Y)[-1].vertices().group_by(Axis.Z)[-1],
            10,
        )
        result = miter(
            sheet.faces().sort_by(Axis.Y)[0].vertices().group_by(Axis.Z)[-1],
            20,
        )

        self.assertIsInstance(result, Shell)
        self.assertTrue(result.is_valid)

    def test_chamfer_and_fillet_reject_shared_vertices(self):
        for operation in (chamfer, fillet):
            with self.subTest(operation=operation.__name__):
                with BuildSheet(thickness=1, bend_radius=2) as bs:
                    with BuildSketch():
                        Rectangle(20, 10)
                    flange(right_edge(bs.sheet_local), length=5)
                    bend_vertex = (
                        bs.faces().filter_by(GeomType.CYLINDER)[0].vertices()[0]
                    )
                    with self.assertRaisesRegex(ValueError, "free boundary"):
                        operation(bend_vertex, 1)

    def test_mirror_preserves_sheet_normal(self):
        half = Face.make_rect(10, 10).translate((5, 0, 0))
        with BuildSheet(thickness=1) as bs:
            insert(half)
            result = mirror(half, about=Plane.YZ)

            self.assertIsInstance(result, Shell)
            self.assertAlmostEqual(result.area, 200, 5)
            self.assertGreater(result.face().normal_at().Z, 0)
        self.assertAlmostEqual(materialize(bs).volume, 200, 5)

    def test_split_sheet(self):
        for keep, expected_x in (
            (Keep.TOP, (0, 10)),
            (Keep.BOTTOM, (-10, 0)),
        ):
            with self.subTest(keep=keep):
                with BuildSheet(thickness=1) as bs:
                    with BuildSketch():
                        Rectangle(20, 10)
                    result = split(bisect_by=Plane.YZ, keep=keep)

                    self.assertIsInstance(result, Shell)
                    self.assertAlmostEqual(result.area, 100, 5)
                    self.assertAlmostEqual(
                        result.bounding_box().min.X, expected_x[0], 5
                    )
                    self.assertAlmostEqual(
                        result.bounding_box().max.X, expected_x[1], 5
                    )
                self.assertAlmostEqual(materialize(bs).volume, 100, 5)

    def test_split_sheet_validation_and_private_both(self):
        with BuildSheet(thickness=1) as builder:
            with BuildSketch():
                Rectangle(20, 10)
            face = builder.face()

            with self.assertRaisesRegex(ValueError, "Mode.REPLACE or Mode.PRIVATE"):
                split(face, bisect_by=Plane.YZ, mode=Mode.ADD)
            with self.assertRaisesRegex(ValueError, "only Face or Shell"):
                split(face.edges()[0], bisect_by=Plane.YZ)
            with self.assertRaisesRegex(ValueError, "current sheet"):
                split(Face.make_rect(5, 5), bisect_by=Plane.YZ)

            private_result = split(
                face,
                bisect_by=Plane.YZ,
                keep=Keep.BOTH,
                mode=Mode.PRIVATE,
            )
            self.assertIsInstance(private_result, Shell)
            self.assertAlmostEqual(private_result.area, face.area, 5)
            self.assertAlmostEqual(builder.sheet_local.area, face.area, 5)

            with patch.object(Face, "split", return_value=[face]):
                self.assertIsInstance(
                    split(face, bisect_by=Plane.YZ, mode=Mode.PRIVATE), Shell
                )
            with patch.object(Face, "split", return_value=Shell(face)):
                self.assertIsInstance(
                    split(face, bisect_by=Plane.YZ, mode=Mode.PRIVATE), Shell
                )
            with patch.object(Face, "split", return_value=None):
                with self.assertRaisesRegex(ValueError, "removed the entire sheet"):
                    split(face, bisect_by=Plane.YZ, mode=Mode.PRIVATE)


class TestFlange(unittest.TestCase):
    def test_outward_direction_handles_both_edge_orientations(self):
        face = Face.make_rect(20, 10)
        edges = list(face.edges())
        edges.append(edges[0].reversed())
        for edge in edges:
            outward, normal = _outward_direction(edge, face)
            self.assertFalse(
                face.is_inside(
                    edge.position_at(0.5) + outward * max(edge.length * 1e-5, 1e-5)
                )
            )
            self.assertAlmostEqual(normal.Z, 1, 6)

    def test_flange_surface_and_material(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            result = flange(right_edge(bs.sheet_local), length=10)
            self.assertIsInstance(result, Shell)
            self.assertEqual(len(result.faces().filter_by(GeomType.PLANE)), 2)
            self.assertEqual(len(result.faces().filter_by(GeomType.CYLINDER)), 1)

        sector = (pi / 4) * ((2 + 1) ** 2 - 2**2) * 60
        material = materialize(bs)
        self.assertAlmostEqual(material.volume, 6000 + sector + 600, 3)
        self.assertTrue(bs.sheet.is_valid)
        self.assertTrue(material.is_valid)
        bbox = material.bounding_box()
        self.assertAlmostEqual(bbox.max.Z, 12, 3)
        self.assertAlmostEqual(bbox.max.X, 53, 3)

    def test_positive_and_negative_direction(self):
        for angle in (90, -90):
            with self.subTest(angle=angle):
                with BuildSheet(thickness=1, bend_radius=2) as bs:
                    with BuildSketch():
                        Rectangle(20, 10)
                    flange(right_edge(bs.sheet_local), length=5, angle=angle)
                bbox = bs.sheet.bounding_box()
                if angle > 0:
                    self.assertGreater(bbox.max.Z, 0)
                    self.assertAlmostEqual(bbox.min.Z, 0, 5)
                else:
                    self.assertLess(bbox.min.Z, 0)
                    self.assertAlmostEqual(bbox.max.Z, 0, 5)

    def test_reference_surface_bend_radius(self):
        expected_positive = {
            SheetSurface.INSIDE: 2,
            SheetSurface.OUTSIDE: 3,
            SheetSurface.MID: 2.5,
            SheetSurface.NEUTRAL: 2.25,
        }
        expected_negative = {
            SheetSurface.INSIDE: 3,
            SheetSurface.OUTSIDE: 2,
            SheetSurface.MID: 2.5,
            SheetSurface.NEUTRAL: 2.75,
        }
        for angle, expected in ((90, expected_positive), (-90, expected_negative)):
            for sheet_surface, reference_radius in expected.items():
                with self.subTest(angle=angle, sheet_surface=sheet_surface):
                    with BuildSheet(
                        thickness=1,
                        bend_radius=2,
                        sheet_surface=sheet_surface,
                        k_factor=0.25,
                    ) as bs:
                        with BuildSketch():
                            Rectangle(20, 10)
                        flange(right_edge(bs.sheet_local), length=5, angle=angle)
                    cylinder = bs.sheet.faces().filter_by(GeomType.CYLINDER)[0]
                    self.assertAlmostEqual(cylinder.radius, reference_radius, 5)
                    self.assertTrue(materialize(bs).is_valid)

    def test_flange_gaps(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(right_edge(bs.sheet_local), length=10, gaps=(5, 10))

        trimmed = 60 - 5 - 10
        sector = (pi / 4) * ((2 + 1) ** 2 - 2**2) * trimmed
        self.assertAlmostEqual(materialize(bs).volume, 6000 + sector + 10 * trimmed, 3)

    def test_flange_multi_edge(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(
                bs.edges().filter_by(GeomType.LINE),
                length=10,
                gaps=3.1,
            )

        self.assertEqual(len(bs.sheet.faces().filter_by(GeomType.CYLINDER)), 4)
        self.assertEqual(len(bs.sheet.faces().filter_by(GeomType.PLANE)), 5)
        self.assertTrue(materialize(bs).is_valid)

    def test_errors(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(20, 20)
            edge = right_edge(bs.sheet_local)
            with self.assertRaises(ValueError):
                flange(edge, length=0)
            with self.assertRaises(ValueError):
                flange(edge, length=5, angle=0)
            with self.assertRaises(ValueError):
                flange(edge, length=5, angle=271)
            with self.assertRaises(ValueError):
                flange(edge, length=5, radius=-1)
            with self.assertRaises(ValueError):
                flange(edge, length=5, gaps=15)
            with self.assertRaisesRegex(ValueError, "pair of numbers"):
                flange(edge, length=5, gaps=(1,))
            with self.assertRaisesRegex(ValueError, "pair of numbers"):
                flange(edge, length=5, gaps=(1, "2"))
            with self.assertRaisesRegex(ValueError, "can't be negative"):
                flange(edge, length=5, gaps=(-1, 0))

        with self.assertRaises(ValueError):
            flange([], length=5, sheet_parameters=SheetMetalParameters(thickness=1))
        with BuildSheet(thickness=1) as circular:
            with BuildSketch():
                Circle(10)
            with self.assertRaises(ValueError):
                flange(circular.edges()[0], length=5)

    def test_algebra_flange(self):
        sheet = Rectangle(100, 60)
        parameters = SheetMetalParameters(
            thickness=1,
            bend_radius=2,
            k_factor=0.4,
            sheet_surface=SheetSurface.OUTSIDE,
        )
        result = flange(right_edge(sheet), length=10, sheet_parameters=parameters)
        self.assertIsInstance(result, Shell)
        self.assertEqual(len(result.faces().filter_by(GeomType.CYLINDER)), 1)
        self.assertAlmostEqual(
            result.faces().filter_by(GeomType.CYLINDER)[0].radius, 3, 5
        )
        self.assertTrue(result.is_valid)

        with self.assertRaisesRegex(ValueError, "required in Algebra mode"):
            flange(right_edge(sheet), length=5)

    def test_algebra_flange_targets_and_validation(self):
        parameters = SheetMetalParameters(thickness=1)
        face = Face.make_rect(20, 10)
        result = flange(
            right_edge(face), length=5, radius=2, sheet_parameters=parameters
        )
        self.assertIsInstance(result, Shell)

        with self.assertRaisesRegex(ValueError, "Face, Sketch, or Shell"):
            flange(
                Edge.make_line((0, 0), (0, 10)),
                length=5,
                radius=2,
                sheet_parameters=parameters,
            )
        with self.assertRaisesRegex(TypeError, "SheetMetalParameters"):
            flange(right_edge(face), length=5, sheet_parameters="parameters")
        with self.assertRaisesRegex(ValueError, "require Mode.ADD"):
            flange(
                right_edge(face),
                length=5,
                radius=2,
                sheet_parameters=parameters,
                mode=Mode.SUBTRACT,
            )

        shared_edge = next(
            edge
            for edge in result.edges().filter_by(GeomType.LINE)
            if len(topo_explore_connected_faces(edge, result)) == 2
        )
        with self.assertRaisesRegex(ValueError, "free sheet boundary"):
            flange(
                shared_edge,
                length=5,
                radius=2,
                sheet_parameters=parameters,
            )

    def test_builder_rejects_explicit_sheet_parameters(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(20, 20)
            with self.assertRaisesRegex(ValueError, "active BuildSheet"):
                flange(
                    right_edge(bs.sheet_local),
                    length=5,
                    sheet_parameters=SheetMetalParameters(thickness=1),
                )


class TestUnfoldOperation(unittest.TestCase):
    """The operation supplies the parameters the bare method leaves optional"""

    @staticmethod
    def flanged(k_factor=0.4):
        parameters = SheetMetalParameters(thickness=1, bend_radius=2, k_factor=k_factor)
        base = Rectangle(100, 60).face()
        sheet = flange(
            Shell([base]).edges().filter_by(Axis.X).sort_by(Axis.Y)[-1],
            length=20,
            sheet_parameters=parameters,
        )
        return sheet, parameters

    def test_matches_the_method_given_parameters(self):
        sheet, parameters = self.flanged()
        self.assertAlmostEqual(
            unfold(sheet, sheet_parameters=parameters).area,
            sheet.unfold(parameters).area,
            5,
        )

    def test_algebra_mode_requires_parameters(self):
        """Without them the method would develop at the geometric radius,
        giving a pattern that folds back to the wrong part"""
        sheet, _ = self.flanged()
        with self.assertRaisesRegex(ValueError, "required in Algebra mode"):
            unfold(sheet)

    def test_builder_mode_supplies_parameters(self):
        with BuildSheet(thickness=1, bend_radius=2, k_factor=0.4) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            flange(bs.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1], length=20)
            flat = unfold()

        sheet, parameters = self.flanged()
        self.assertAlmostEqual(flat.area, sheet.unfold(parameters).area, 5)

    def test_builder_mode_rejects_explicit_parameters(self):
        _, parameters = self.flanged()
        with self.assertRaisesRegex(ValueError, "supplied by the active"):
            with BuildSheet(thickness=1, bend_radius=2) as bs:
                with BuildSketch():
                    Rectangle(100, 60)
                unfold(sheet_parameters=parameters)

    def test_input_validation(self):
        _, parameters = self.flanged()
        with self.assertRaisesRegex(ValueError, "requires a sheet Shell"):
            unfold()
        with self.assertRaisesRegex(ValueError, "takes a sheet Shell"):
            unfold(Face.make_rect(10, 10), sheet_parameters=parameters)
        with self.assertRaisesRegex(ValueError, "empty sheet Shell"):
            unfold(Shell(), sheet_parameters=parameters)

    def test_flat_pattern_lands_on_plane_xy(self):
        """Each face is developed in the parameter space of a Plane.XY surface,
        so the pattern is built there rather than transformed there afterwards -
        the traversal root only sets connectivity order, not the result plane"""
        sheet, parameters = self.flanged()
        reference = unfold(sheet, sheet_parameters=parameters)

        placements = {
            "translated": Pos(500, 300, 200) * sheet,
            "rotated": Rot(30, 40, 50) * sheet,
            "both": Pos(10, 20, 30) * Rot(15, 25, 35) * sheet,
        }
        for label, placed in placements.items():
            with self.subTest(placement=label):
                flat = unfold(placed, sheet_parameters=parameters)
                box = flat.bounding_box()
                self.assertAlmostEqual(box.size.Z, 0, 5)
                self.assertAlmostEqual(box.min.Z, 0, 5)
                # the pattern is normalized, not left where the shell sat
                self.assertAlmostEqual(flat.area, reference.area, 5)
                self.assertAlmostEqual(box.min.X, reference.bounding_box().min.X, 5)

    def test_align_places_the_pattern_within_plane_xy(self):
        sheet, parameters = self.flanged()
        loose = unfold(sheet, sheet_parameters=parameters).bounding_box()

        cornered = unfold(
            sheet, sheet_parameters=parameters, align=Align.MIN
        ).bounding_box()
        self.assertAlmostEqual(cornered.min.X, 0, 5)
        self.assertAlmostEqual(cornered.min.Y, 0, 5)
        self.assertAlmostEqual(cornered.size.X, loose.size.X, 5)
        self.assertAlmostEqual(cornered.size.Y, loose.size.Y, 5)

        centred = unfold(
            sheet, sheet_parameters=parameters, align=Align.CENTER
        ).bounding_box()
        self.assertAlmostEqual(centred.center().X, 0, 5)
        self.assertAlmostEqual(centred.center().Y, 0, 5)

        mixed = unfold(
            sheet, sheet_parameters=parameters, align=(Align.MIN, Align.CENTER)
        ).bounding_box()
        self.assertAlmostEqual(mixed.min.X, 0, 5)
        self.assertAlmostEqual(mixed.center().Y, 0, 5)

    def test_align_defaults_to_leaving_the_pattern_in_place(self):
        """Align.NONE keeps the pattern registered with the source sheet"""
        sheet, parameters = self.flanged()
        default = unfold(sheet, sheet_parameters=parameters).bounding_box()
        explicit = unfold(
            sheet, sheet_parameters=parameters, align=Align.NONE
        ).bounding_box()
        as_none = unfold(sheet, sheet_parameters=parameters, align=None).bounding_box()

        for other in (explicit, as_none):
            self.assertAlmostEqual(other.min.X, default.min.X, 5)
            self.assertAlmostEqual(other.min.Y, default.min.Y, 5)
        self.assertNotAlmostEqual(default.min.X, 0, 5)

    def test_a_shell_of_bends_alone_cannot_be_unfolded(self):
        """The development is seeded from a planar face"""
        arc = Edge.make_circle(20, Plane.XY, 0, 120)
        rolled = Shell([Face.extrude(arc, (0, 0, 40))])
        _, parameters = self.flanged()
        with self.assertRaisesRegex(ValueError, "at least one planar face"):
            unfold(rolled, sheet_parameters=parameters)

    def test_a_flange_into_a_hole_unfolds_into_it(self):
        """A hole's flange folds inward, so it develops into the hole rather
        than back over the sheet - which the plate's centre of mass, sitting
        inside the hole, is no guide to."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
                with Locations((25, 0)):
                    Rectangle(25, 25, mode=Mode.SUBTRACT)
            hole = builder.flats().sort_by(Axis.Z)[0].inner_wires()[0]
            flange(hole.edges(), length=10, gaps=3.5)
            flat = unfold()

        plate = max(flat.faces(), key=lambda f: f.area)
        for face in flat.faces():
            if face.is_same(plate):
                continue
            box = face.bounding_box()
            self.assertGreaterEqual(box.min.X, 12.5 - 1e-6)
            self.assertLessEqual(box.max.X, 37.5 + 1e-6)
            self.assertGreaterEqual(box.min.Y, -12.5 - 1e-6)
            self.assertLessEqual(box.max.Y, 12.5 + 1e-6)

        part = thicken(builder.sheet_local, sheet_parameters=builder.sheet_parameters)
        self.assertAlmostEqual(part.volume, flat.area, 6)

    def test_flat_pattern_area_times_thickness_is_the_volume(self):
        """Exact only at k=0.5, where the neutral and mid surfaces coincide"""
        sheet, parameters = self.flanged(k_factor=0.5)
        self.assertAlmostEqual(
            thicken(sheet, sheet_parameters=parameters).volume,
            unfold(sheet, sheet_parameters=parameters).area * parameters.thickness,
            5,
        )


def precise_area(shape) -> float:
    """Area integrated to 1e-9; the default integrator loses ~1e-4 on B-spline
    bounded faces, which the rolled bend faces are."""
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape.wrapped, props, 1e-9)
    return props.Mass()


class TestBendOutline(unittest.TestCase):
    """The strip a bend consumes rolls up with whatever the blank's outline does
    across it, so folding is an isometry of the blank: the folded NEUTRAL shell
    has the blank's area, and unfolding any surface gives the blank back."""

    @staticmethod
    def outlines() -> dict[str, Sketch]:
        with BuildSketch() as plain:
            Rectangle(40, 40)
        with BuildSketch() as tapered:
            Polygon((-20, -20), (20, -20), (14, 20), (-14, 20), align=None)
        with BuildSketch() as rounded:
            Rectangle(40, 40)
            fillet(rounded.vertices().sort_by_distance((20, -20, 0))[0], 20)
        with BuildSketch() as notched:
            Rectangle(40, 40)
            with Locations((20, 0)):
                Circle(3, mode=Mode.SUBTRACT)
        with BuildSketch() as holed:
            Rectangle(40, 40)
            Circle(1, mode=Mode.SUBTRACT)
        return {
            "plain": plain.sketch,
            "tapered": tapered.sketch,
            "rounded": rounded.sketch,
            "notched": notched.sketch,
            "holed": holed.sketch,
        }

    @staticmethod
    def fold(blank: Sketch, angle: float, surface: SheetSurface) -> BuildSheet:
        with BuildSheet(
            thickness=1, bend_radius=2, k_factor=0.4, sheet_surface=surface
        ) as sheet:
            insert(blank, mode=Mode.REPLACE)
            split(sheet.faces()[0], bisect_by=Plane.XZ, keep=Keep.BOTH)
            fold_line = (
                sheet.faces()
                .sort_by(Axis.Y)[-1]
                .edges()
                .filter_by(Axis.X)
                .sort_by(Axis.Y)[0]
            )
            bend(fold_line, angle=angle, position=BendPosition.CENTER)
        return sheet

    def test_folding_is_an_isometry_of_the_blank(self):
        """Only the NEUTRAL surface bent toward its normal is the neutral fibre
        itself, so only there does the folded shell keep the blank's area."""
        for name, blank in self.outlines().items():
            with self.subTest(outline=name):
                sheet = self.fold(blank, 90, SheetSurface.NEUTRAL)
                self.assertTrue(sheet.sheet.is_valid)
                self.assertAlmostEqual(precise_area(sheet.sheet), blank.area, 6)

    def test_unfolding_returns_the_blank(self):
        """Every surface, both directions."""
        for name, blank in self.outlines().items():
            for surface in (SheetSurface.MID, SheetSurface.INSIDE):
                for angle in (90, -90):
                    with self.subTest(outline=name, surface=surface, angle=angle):
                        sheet = self.fold(blank, angle, surface)
                        self.assertTrue(sheet.sheet.is_valid)
                        flat = unfold(sheet.sheet, sheet.sheet_parameters)
                        self.assertAlmostEqual(precise_area(flat), blank.area, 6)

    def test_the_outline_lands_on_the_bend(self):
        holed = self.fold(self.outlines()["holed"], 90, SheetSurface.NEUTRAL).sheet
        # the hole was entirely inside the strip, so it is a hole in the bend
        (bend_face,) = holed.bends()
        self.assertEqual(len(bend_face.inner_wires()), 1)
        self.assertAlmostEqual(bend_face.inner_wires()[0].length, 2 * pi, 4)
        # a plain strip's bend keeps exact lines along the axis and arcs about it
        plain = self.fold(self.outlines()["plain"], 90, SheetSurface.NEUTRAL).sheet
        kinds = sorted(e.geom_type.name for e in plain.bends()[0].edges())
        self.assertEqual(kinds, ["CIRCLE", "CIRCLE", "LINE", "LINE"])
        # a tapered strip rolls into a bend whose ends are not arcs
        tapered = self.fold(self.outlines()["tapered"], 90, SheetSurface.NEUTRAL).sheet
        kinds = sorted(e.geom_type.name for e in tapered.bends()[0].edges())
        self.assertEqual(kinds, ["BSPLINE", "BSPLINE", "LINE", "LINE"])


class TestBendAllowance(unittest.TestCase):
    """What a bend takes out of the flat is the neutral arc, for every surface
    and both directions, and unfold gives exactly that back."""

    RADIUS, THICKNESS, K = 2, 3, 0.33

    def folded(self, surface: SheetSurface, angle: float) -> BuildSheet:
        with BuildSheet(
            thickness=self.THICKNESS,
            bend_radius=self.RADIUS,
            k_factor=self.K,
            sheet_surface=surface,
        ) as builder:
            with BuildSketch():
                Rectangle(40, 100)
            split(builder.faces()[0], bisect_by=Plane.XZ, keep=Keep.BOTH)
            fold_line = (
                builder.faces()
                .sort_by(Axis.Y)[-1]
                .edges()
                .filter_by(Axis.X)
                .sort_by(Axis.Y)[0]
            )
            bend(fold_line, angle=angle, position=BendPosition.CENTER)
        return builder

    def test_the_legs_share_what_the_allowance_leaves(self):
        allowance = (self.RADIUS + self.K * self.THICKNESS) * pi / 2
        for surface in SheetSurface:
            for angle in (90, -90):
                with self.subTest(surface=surface, angle=angle):
                    sheet = self.folded(surface, angle).sheet
                    legs = sheet.faces().filter_by(GeomType.PLANE)
                    self.assertEqual(len(legs), 2)
                    for leg in legs:
                        self.assertAlmostEqual(leg.area / 40, (100 - allowance) / 2, 6)
                    # the bend itself is drawn at the reference surface's radius
                    self.assertAlmostEqual(
                        sheet.bends()[0].radius,
                        reference_radius(self.RADIUS, sheet_parameters(surface), angle),
                        6,
                    )

    def test_the_blank_round_trips(self):
        for surface in SheetSurface:
            for angle in (90, -90):
                with self.subTest(surface=surface, angle=angle):
                    builder = self.folded(surface, angle)
                    flat = unfold(builder.sheet, builder.sheet_parameters)
                    self.assertAlmostEqual(flat.area, 40 * 100, 6)
                    self.assertAlmostEqual(flat.bounding_box().size.Y, 100, 6)


def sheet_parameters(surface: SheetSurface) -> SheetMetalParameters:
    """The parameters TestBendAllowance folds with."""
    return SheetMetalParameters(
        thickness=TestBendAllowance.THICKNESS,
        bend_radius=TestBendAllowance.RADIUS,
        k_factor=TestBendAllowance.K,
        sheet_surface=surface,
    )


class TestUnfold(unittest.TestCase):
    def test_geometric_and_neutral_axis_development(self):
        """All reference surfaces produce the same neutral development, and so
        do both bend directions: the neutral fibre is k*t from the inside of the
        bend whichever face that is."""
        for angle, neutral_radius in ((90, 2.25), (-90, 2.25)):
            expected_area = 100 + 50 + 10 * neutral_radius * pi / 2
            for sheet_surface in SheetSurface:
                with self.subTest(angle=angle, sheet_surface=sheet_surface):
                    parameters = SheetMetalParameters(
                        thickness=1,
                        k_factor=0.25,
                        sheet_surface=sheet_surface,
                    )
                    sheet = Rectangle(10, 10)
                    sheet = flange(
                        right_edge(sheet),
                        length=5,
                        angle=angle,
                        radius=2,
                        sheet_parameters=parameters,
                    )

                    geometric = sheet.unfold()
                    neutral = sheet.unfold(parameters)

                    self.assertTrue(geometric.is_valid)
                    self.assertTrue(neutral.is_valid)
                    self.assertAlmostEqual(geometric.area, sheet.area, 5)
                    self.assertAlmostEqual(neutral.area, expected_area, 5)
                    self.assertAlmostEqual(neutral.bounding_box().size.Z, 0, 5)

    def test_validation(self):
        with self.assertRaisesRegex(ValueError, "non-empty Shell"):
            Shell().unfold()
        with self.assertRaisesRegex(TypeError, "SheetMetalParameters"):
            Shell(Rectangle(10, 10).face()).unfold("parameters")
        with self.assertRaisesRegex(ValueError, "planes and cylinders"):
            Solid.make_sphere(10).shell().unfold()


class TestMiter(unittest.TestCase):
    @staticmethod
    def flange_rim(sheet: Shell) -> Edge:
        """Return the free rim of the single flange in the test sheet."""
        wall = sheet.faces().filter_by(GeomType.PLANE).sort_by(Axis.Z)[-1]
        return wall.edges().sort_by(Axis.Z)[-1]

    def test_positive_miter_trims_flange(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(20, 10)
            flange(right_edge(bs.sheet_local), length=5, gaps=1)
            area_before = bs.sheet_local.area
            rim = self.flange_rim(bs.sheet_local)
            result = miter(rim.vertices(), angle=10)

            self.assertIsInstance(result, Shell)
            expected_removed = 5**2 * tan(radians(10))
            self.assertAlmostEqual(area_before - result.area, expected_removed, 5)
            self.assertEqual(
                len(result.faces().filter_by(GeomType.CYLINDER)),
                1,
            )
            self.assertTrue(result.is_valid)
        material = materialize(bs)
        self.assertTrue(material.is_valid)
        self.assertEqual(len(material.solids()), 1)

    def test_negative_miter_extends_flange(self):
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(20, 10)
            flange(right_edge(bs.sheet_local), length=5, gaps=1)
            area_before = bs.sheet_local.area
            rim = self.flange_rim(bs.sheet_local)
            result = miter(rim.vertices(), angle=-10)

            expected_added = 5**2 * tan(radians(10))
            self.assertAlmostEqual(result.area - area_before, expected_added, 5)
            self.assertTrue(result.is_valid)

    def test_algebra_miter(self):
        parameters = SheetMetalParameters(thickness=1)
        sheet = Rectangle(20, 10)
        flanged = flange(
            right_edge(sheet),
            length=5,
            radius=2,
            gaps=1,
            sheet_parameters=parameters,
        )
        rim = self.flange_rim(flanged)
        result = miter(rim.vertices()[0], angle=10)

        self.assertIsInstance(result, Shell)
        self.assertLess(result.area, flanged.area)
        self.assertTrue(result.is_valid)

    @staticmethod
    def hole_walls(gaps: float = 3.5, length: float = 10) -> BuildSheet:
        """Four flanges folded into a square hole, each with an 18 long rim."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
                with Locations((25, 0)):
                    Rectangle(25, 25, mode=Mode.SUBTRACT)
            hole = builder.flats().sort_by(Axis.Z)[0].inner_wires()[0]
            flange(hole.edges(), length=length, gaps=gaps)
        return builder

    @staticmethod
    def hole_wall_faces(builder: BuildSheet) -> ShapeList[Face]:
        """The four walls around the hole."""
        return (
            builder.flats()
            .filter_by(Axis.Z, reverse=True)
            .sort_by_distance((25, 0, 0))[0:4]
        )

    def test_miters_that_pass_each_other_meet_instead(self):
        """A miter cuts back from the rim and leaves the bend edge alone, so
        taking more than the rim is long runs out of rim rather than flange -
        the two cuts meet inside it and what is left is a triangle."""
        for angle, apex in ((40, None), (45, 9.0), (60, 18 / (2 * tan(radians(60))))):
            with self.subTest(angle=angle):
                builder = self.hole_walls()
                with builder:
                    corners = (
                        self.hole_wall_faces(builder).vertices().group_by(Axis.Z)[-1]
                    )
                    miter(corners, angle)
                wall = self.hole_wall_faces(builder)[0]
                self.assertTrue(builder.sheet_local.is_valid)
                if apex is None:
                    self.assertEqual(len(wall.vertices()), 4)
                else:
                    self.assertEqual(len(wall.vertices()), 3)
                    self.assertAlmostEqual(wall.area, 18 * apex / 2, 6)

    def test_a_lone_miter_leaves_through_the_far_side(self):
        """With no miter at the other end the cut runs past the rim entirely
        and out through the side beyond it, which is a triangle as well."""
        builder = self.hole_walls()
        with builder:
            corner = self.hole_wall_faces(builder)[0].vertices().group_by(Axis.Z)[-1][0]
            miter(corner, 70)
        wall = self.hole_wall_faces(builder)[0]
        self.assertEqual(len(wall.vertices()), 3)
        self.assertAlmostEqual(wall.area, 18 * (18 / tan(radians(70))) / 2, 6)
        self.assertTrue(builder.sheet_local.is_valid)

    def test_a_triangular_flange_still_forms(self):
        builder = self.hole_walls()
        with builder:
            corners = self.hole_wall_faces(builder).vertices().group_by(Axis.Z)[-1]
            miter(corners, 45)
        parameters = builder.sheet_parameters
        part = thicken(builder.sheet_local, sheet_parameters=parameters)
        flat = unfold(builder.sheet_local, sheet_parameters=parameters)
        self.assertTrue(part.is_valid)
        self.assertAlmostEqual(part.volume, flat.area, 6)

    def test_through_bend_carries_the_cut_to_the_fold_line(self):
        """A mitered corner is one straight cut across the whole flange in the
        flat pattern, bend included - so the bend loses its own triangle and
        the wall becomes a trapezoid rather than losing a corner."""
        allowance = (2 + 0.5) * pi / 2  # neutral radius times a right angle
        slope = tan(radians(30))
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(60, 40)
            flange(builder.edges().filter_by(Axis.X).sort_by(Axis.Y)[0], length=15)
            rim = (
                builder.flats()
                .filter_by(Axis.Z, reverse=True)[0]
                .edges()
                .sort_by(Axis.Z)[-1]
            )
            miter(rim.vertices(), 30, through_bend=True)
        parameters = builder.sheet_parameters
        flat = unfold(builder.sheet_local, sheet_parameters=parameters)

        square = 2400 + 60 * allowance + 900  # base, bend and wall untrimmed
        per_end = (
            allowance**2 * slope / 2 + (allowance + (allowance + 15)) * 15 * slope / 2
        )
        self.assertAlmostEqual(square - flat.area, 2 * per_end, 5)
        part = thicken(builder.sheet_local, sheet_parameters=parameters)
        self.assertAlmostEqual(part.volume, flat.area, 3)

    def test_an_extending_miter_widens_the_bend(self):
        """A flared flange: the bend's far edge grows by the reach at each end,
        its fold line stays, and the wall meets it without a step."""
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(40, 20)
            flange(bs.edges().sort_by(Axis.X)[-1], length=10)
            wall = bs.flats().sort_by(Axis.Z)[-1]
            miter(wall.vertices().group_by(Axis.Z)[-1], -20, through_bend=True)
        self.assertTrue(bs.sheet.is_valid)
        bend = bs.bends()[0]
        allowance = (2 + 0.5) * pi / 2
        reach = allowance * tan(radians(20))
        lengths = sorted(e.length for e in bend.edges())
        self.assertAlmostEqual(lengths[-1], 20 + 2 * reach, 5)  # the far tangent
        self.assertAlmostEqual(lengths[-2], 20, 5)  # the fold line
        # the sides run across the bend on the reference surface, where the arc
        # is the surface's, and along it by the reach
        surface_arc = bend.radius * pi / 2
        for side in lengths[:2]:
            self.assertAlmostEqual(side, sqrt(surface_arc**2 + reach**2), 5)
        wall = bs.flats().sort_by(Axis.Z)[-1]
        self.assertEqual(len(wall.edges()), 4)  # no steps at the tangent
        # in the flat pattern the miter is one straight cut from rim to blank
        # edge: the cut across the bend and the cut across the wall line up
        flat = unfold(bs.sheet, bs.sheet_parameters)
        # (the bend's developed cut edges come back as splines, so no type filter)
        sloped = [
            e
            for e in flat.edges()
            if 1e-6 < abs((e % 0.5).dot(Vector(1, 0, 0))) < 1 - 1e-6
        ]
        self.assertEqual(len(sloped), 4)  # two per mitered end
        for edge in sloped:
            partners = [
                other
                for other in sloped
                if other is not edge and edge.distance_to(other) < 1e-6
            ]
            self.assertEqual(len(partners), 1)
            self.assertAlmostEqual((edge % 0.5).cross(partners[0] % 0.5).length, 0, 6)

    def test_without_through_bend_the_bend_is_untouched(self):
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(60, 40)
            flange(builder.edges().filter_by(Axis.X).sort_by(Axis.Y)[0], length=15)
            before = builder.bends()[0].area
            rim = (
                builder.flats()
                .filter_by(Axis.Z, reverse=True)[0]
                .edges()
                .sort_by(Axis.Z)[-1]
            )
            miter(rim.vertices(), 30)
        self.assertAlmostEqual(builder.bends()[0].area, before, 6)

    def test_mitered_bends_let_hole_flanges_meet(self):
        """Cut through the bends and four flanges folded into a hole come to a
        point at each corner, so the flat pattern no longer overlaps itself and
        needs no gap to hold them apart."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
                with Locations((25, 0)):
                    Rectangle(25, 25, mode=Mode.SUBTRACT)
            hole = builder.flats().sort_by(Axis.Z)[0].inner_wires()[0]
            flange(hole.edges(), length=6, gaps=0)
            walls = (
                builder.flats()
                .filter_by(Axis.Z, reverse=True)
                .sort_by_distance((25, 0, 0))[0:4]
            )
            miter(walls.vertices().group_by(Axis.Z)[-1], 45, through_bend=True)
            flat = unfold()

        self.assertTrue(builder.sheet_local.is_valid)
        pieces = sorted(flat.faces(), key=lambda f: -f.area)[1:]
        for index, first in enumerate(pieces):
            for second in pieces[index + 1 :]:
                common = first.intersect(second)
                shared = 0.0 if common is None else sum(f.area for f in common.faces())
                self.assertAlmostEqual(shared, 0.0, 6)

    def test_through_bend_needs_sheet_parameters_in_algebra_mode(self):
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(60, 40)
            flange(builder.edges().filter_by(Axis.X).sort_by(Axis.Y)[0], length=15)
        rim = self.flange_rim(builder.sheet_local)
        with self.assertRaisesRegex(ValueError, "sheet_parameters is required"):
            miter(rim.vertices()[0], 30, through_bend=True)

    def test_algebra_miter_rejects_vertices_from_different_shells(self):
        parameters = SheetMetalParameters(thickness=1)
        sheets = [
            flange(
                right_edge(Rectangle(20, 10)),
                length=5,
                radius=2,
                gaps=1,
                sheet_parameters=parameters,
            )
            for _ in range(2)
        ]
        vertices = [self.flange_rim(sheet).vertices()[0] for sheet in sheets]
        with self.assertRaisesRegex(ValueError, "same sheet Shell"):
            miter(vertices, angle=10)
        with self.assertRaisesRegex(ValueError, "belong to a sheet Shell"):
            miter(Vertex(0, 0, 0), angle=10)

    def test_validation(self):
        with self.assertRaisesRegex(ValueError, "at least one vertex"):
            miter([])
        with self.assertRaisesRegex(ValueError, "only Vertices"):
            miter(Edge.make_line((0, 0), (1, 0)))
        with BuildSheet(thickness=1, bend_radius=2) as bs:
            with BuildSketch():
                Rectangle(20, 10)
            flange(right_edge(bs.sheet_local), length=5, gaps=1)
            rim = self.flange_rim(bs.sheet_local)
            with self.assertRaisesRegex(ValueError, "strictly between"):
                miter(rim.vertices()[0], angle=90)
            base_vertex = bs.faces().sort_by(Axis.X)[0].vertices()[0]
            with self.assertRaisesRegex(ValueError, "free flange rim endpoint"):
                miter(base_vertex, angle=10)

            vertex = rim.vertices()[0]

            def hide_free_edges(edge, target):
                adjacent = topo_explore_connected_faces(edge, target)
                if len(adjacent) == 1 and any(
                    vertex.is_same(candidate) for candidate in edge.vertices()
                ):
                    return [adjacent[0], adjacent[0]]
                return adjacent

            with patch(
                "build123d.operations_sheet.topo_explore_connected_faces",
                side_effect=hide_free_edges,
            ):
                with self.assertRaisesRegex(ValueError, "free flange rim endpoint"):
                    miter(vertex, angle=10)


class TestHem(unittest.TestCase):
    def test_hem_types(self):
        cases = (
            (HemType.FLAT, {"width": 8}, 3),
            (HemType.OPEN, {"width": 8, "opening": 2}, 3),
            (HemType.ROLLED, {"radius": 3, "roll_angle": 270}, 2),
            (HemType.TEARDROP, {"width": 12, "radius": 3}, 3),
        )
        for hem_type, kwargs, face_count in cases:
            with self.subTest(hem_type=hem_type):
                with BuildSheet(thickness=1, bend_radius=2) as bs:
                    with BuildSketch():
                        Rectangle(100, 60)
                    result = hem(
                        right_edge(bs.sheet_local), hem_type=hem_type, **kwargs
                    )
                    self.assertIsInstance(result, Shell)
                self.assertEqual(len(bs.sheet.faces()), face_count)
                self.assertEqual(len(bs.sheet.faces().filter_by(GeomType.CYLINDER)), 1)
                self.assertTrue(bs.sheet.is_valid)
                material = materialize(bs)
                self.assertTrue(material.is_valid)
                self.assertGreater(material.volume, 6000)

    def test_open_and_rolled_material_volume(self):
        with BuildSheet(thickness=1) as open_hem:
            with BuildSketch():
                Rectangle(100, 60)
            hem(right_edge(open_hem.sheet_local), HemType.OPEN, width=8, opening=2)
        open_sector = (pi / 2) * (2**2 - 1**2) * 60
        self.assertAlmostEqual(
            materialize(open_hem).volume, 6000 + open_sector + 360, 3
        )

        with BuildSheet(thickness=1, bend_radius=3) as rolled_hem:
            with BuildSketch():
                Rectangle(100, 60)
            hem(right_edge(rolled_hem.sheet_local), HemType.ROLLED, roll_angle=270)
        rolled_sector = (radians(270) / 2) * ((3 + 1) ** 2 - 3**2) * 60
        self.assertAlmostEqual(materialize(rolled_hem).volume, 6000 + rolled_sector, 3)

    def test_algebra_hem(self):
        sheet = Shell(Face.make_rect(100, 60))
        result = hem(
            right_edge(sheet),
            HemType.OPEN,
            width=8,
            opening=2,
            sheet_parameters=SheetMetalParameters(thickness=1),
        )
        self.assertIsInstance(result, Shell)
        self.assertEqual(len(result.faces()), 3)

        rolled = hem(
            right_edge(sheet),
            HemType.ROLLED,
            roll_angle=270,
            sheet_parameters=SheetMetalParameters(thickness=1, bend_radius=3),
        )
        self.assertAlmostEqual(
            rolled.faces().filter_by(GeomType.CYLINDER)[0].radius, 3, 5
        )

        with self.assertRaisesRegex(ValueError, "required in Algebra mode"):
            hem(right_edge(sheet), HemType.OPEN, width=8, opening=2)

    def test_profile_parameter_validation(self):
        with BuildSheet(thickness=1) as bs:
            with BuildSketch():
                Rectangle(100, 60)
            edge = right_edge(bs.sheet_local)

            with self.assertRaisesRegex(ValueError, "only accepts width"):
                hem(edge, HemType.FLAT, width=8, opening=1)
            with self.assertRaisesRegex(ValueError, "positive opening"):
                hem(edge, HemType.OPEN, width=8)
            with self.assertRaisesRegex(ValueError, "positive opening"):
                hem(edge, HemType.OPEN, width=8, opening=0)
            with self.assertRaisesRegex(ValueError, "width and opening"):
                hem(edge, HemType.OPEN, width=8, opening=2, radius=1)
            with self.assertRaisesRegex(ValueError, "doesn't accept roll_angle"):
                hem(
                    edge,
                    HemType.TEARDROP,
                    width=12,
                    radius=3,
                    roll_angle=270,
                )
            with self.assertRaisesRegex(ValueError, "radius and roll_angle"):
                hem(edge, HemType.ROLLED, width=8)
            with self.assertRaisesRegex(ValueError, "width is required"):
                hem(edge, HemType.FLAT)
            with self.assertRaisesRegex(ValueError, "width is required"):
                hem(edge, HemType.OPEN, opening=2)
            with self.assertRaisesRegex(ValueError, "width is required"):
                hem(edge, HemType.TEARDROP, radius=3)
            with self.assertRaisesRegex(ValueError, "radius and roll_angle"):
                hem(edge, HemType.ROLLED, opening=1)

        with self.assertRaisesRegex(ValueError, "at least one edge"):
            hem([], HemType.FLAT, width=8, sheet_parameters=SheetMetalParameters(1))

    def test_unknown_hem_type(self):
        face = Face.make_rect(20, 10)
        with self.assertRaisesRegex(ValueError, "Unknown hem type"):
            hem(
                right_edge(face),
                "invalid",
                width=8,
                sheet_parameters=SheetMetalParameters(1),
            )


class TestHemParameters(unittest.TestCase):
    def test_flat_uses_minimum_radius(self):
        leg, bend_angle, bend_radius = _hem_parameters(
            HemType.FLAT, 1, 8, 0, None, None
        )
        self.assertAlmostEqual(leg, 8 - (1 + MIN_BEND_RADIUS), 6)
        self.assertAlmostEqual(bend_angle, 180, 6)
        self.assertAlmostEqual(bend_radius, MIN_BEND_RADIUS, 6)

    def test_open(self):
        leg, bend_angle, bend_radius = _hem_parameters(
            HemType.OPEN, 1, 8, 2, None, None
        )
        self.assertAlmostEqual(leg, 6, 6)
        self.assertAlmostEqual(bend_angle, 180, 6)
        self.assertAlmostEqual(bend_radius, 1, 6)

    def test_rolled_default_max_angle(self):
        leg, bend_angle, bend_radius = _hem_parameters(
            HemType.ROLLED, 1, None, 0, 3, None
        )
        self.assertAlmostEqual(leg, 0, 6)
        self.assertAlmostEqual(bend_angle, 270 + degrees(asin(3 / 4)), 6)
        self.assertAlmostEqual(bend_radius, 3, 6)

    def test_teardrop_residual(self):
        thickness, radius, width = 1.0, 3.0, 12.0
        leg, bend_angle, _ = _hem_parameters(
            HemType.TEARDROP, thickness, width, 0, radius, None
        )
        theta = radians(bend_angle - 180) / 2
        residual = leg - width + (radius + thickness) + thickness * sin(2 * theta)
        self.assertAlmostEqual(residual, 0, 6)

    def test_errors(self):
        with self.assertRaisesRegex(ValueError, "unexpected incorrect geometry"):
            _bisection(lambda value: value**2 + 1, -1, 1)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.OPEN, 1, 8, -1, None, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.OPEN, 1, None, 1, None, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.FLAT, 1, 0.5, 0, None, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.ROLLED, 1, None, 0, None, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.ROLLED, 1, None, 0, 3, 0)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.ROLLED, 1, None, 0, 3, 350)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.TEARDROP, 1, 12, 0, None, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.TEARDROP, 1, 12, -1, 3, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.TEARDROP, 1, None, 0, 3, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.TEARDROP, 1, 3, 0, 3, None)
        with self.assertRaises(ValueError):
            _hem_parameters(HemType.TEARDROP, 1, 8, 3, 3, None)
        with self.assertRaisesRegex(ValueError, "Unknown hem type"):
            _hem_parameters("invalid", 1, 8, 0, None, None)

        self.assertEqual(
            _hem_parameters(HemType.TEARDROP, 1, 8, 1, 3, None),
            (2, 270.0, 3),
        )
        self.assertEqual(
            _hem_parameters(HemType.TEARDROP, 1, 12, 6, 3, None),
            _hem_parameters(HemType.OPEN, 1, 8, 6, None, None),
        )
        leg, angle, radius = _hem_parameters(HemType.TEARDROP, 1, 12, 1, 3, None)
        self.assertGreater(leg, 0)
        self.assertGreater(angle, 180)
        self.assertEqual(radius, 3)


class TestExcludedOperations(unittest.TestCase):
    def test_make_brake_formed_not_available_in_build_sheet(self):
        with self.assertRaises(RuntimeError):
            with BuildSheet(thickness=1):
                with BuildLine():
                    Polyline((0, 0), (20, 0), (20, 15))
                make_brake_formed(thickness=1, station_widths=30)


class TestCornerRelief(unittest.TestCase):
    """Corner relief where two bends meet."""

    PARAMETERS = SheetMetalParameters(thickness=1, bend_radius=2)
    SCALE = 2 / 2.5  # reference radius over neutral radius, k = 0.5

    @classmethod
    def blank_removed(cls, before: Shell, after: Shell) -> float:
        """How much the blank loses - where a relief is laid out."""
        return (
            unfold(before, sheet_parameters=cls.PARAMETERS).area
            - unfold(after, sheet_parameters=cls.PARAMETERS).area
        )

    @staticmethod
    def two_flange_sheet() -> BuildSheet:
        """A base with two adjoining walls, so two bends share a corner."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
            edges = builder.edges().filter_by(GeomType.LINE)
            flange(
                [edges.sort_by(Axis.Y)[-1], edges.sort_by(Axis.X)[-1]],
                length=20,
            )
        return builder

    @staticmethod
    def shared_corner(sheet: Shell) -> Vertex:
        """The vertex where the two bends meet."""
        return min(
            sheet.vertices(),
            key=lambda vertex: (Vector(vertex) - Vector(50, 30, 0)).length,
        )

    def test_round_removes_three_quarters_of_a_circle(self):
        """A relief is laid out on the blank, so that is where it is a circle -
        three quarters of one, the fourth quadrant lying past both bends. On
        the sheet the parts that cross a bend read smaller, since the blank is
        longer than the surface it rolls onto."""
        sheet = self.two_flange_sheet().sheet_local
        result = corner_relief(
            self.shared_corner(sheet),
            ReliefType.ROUND,
            radius=3.0,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertIsInstance(result, Shell)
        self.assertTrue(result.is_valid)
        self.assertAlmostEqual(self.blank_removed(sheet, result), 0.75 * pi * 3**2, 5)
        quarter = pi * 3**2 / 4
        self.assertAlmostEqual(
            sheet.area - result.area, quarter * (1 + 2 * self.SCALE), 5
        )

    def test_square_removes_three_quarters_of_a_square(self):
        sheet = self.two_flange_sheet().sheet_local
        result = corner_relief(
            self.shared_corner(sheet),
            ReliefType.SQUARE,
            size=5.0,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertAlmostEqual(self.blank_removed(sheet, result), 0.75 * 5.0**2, 5)

    def test_relief_keeps_its_shape_on_the_blank(self):
        """A shape laid out on the blank comes out its own size there. These
        two sit symmetrically about the corner, so exactly three quarters of
        each lies on material - the fourth quadrant is past both bends."""
        sheet = self.two_flange_sheet().sheet_local
        corner = self.shared_corner(sheet)
        for relief_type, kwargs, area in (
            (ReliefType.ROUND, {"radius": 3.0}, pi * 3.0**2),
            (ReliefType.SQUARE, {"size": 5.0}, 5.0**2),
        ):
            with self.subTest(relief_type=relief_type):
                result = corner_relief(
                    corner, relief_type, **kwargs, sheet_parameters=self.PARAMETERS
                )
                self.assertAlmostEqual(
                    self.blank_removed(sheet, result), 0.75 * area, 4
                )

    def test_constant_width_continues_the_flange_gap(self):
        """Its width is measured from the part, not supplied, and the gap
        stays constant through the bends rather than pinching."""
        sheet = self.two_flange_sheet().sheet_local
        corner = self.shared_corner(sheet)
        result = corner_relief(
            corner,
            ReliefType.CONSTANT_WIDTH,
            depth=6.0,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertTrue(result.is_valid)

        # every flank lies in one of the two planes offset from the corner's
        # mirror plane by half the flange gap
        base = max(sheet.faces().filter_by(GeomType.PLANE), key=lambda f: f.area)
        parameters = self.two_flange_sheet().sheet_parameters
        _, normal = _corner_mirror_plane(sheet, base, Vector(corner), parameters)
        gap = _flange_separation(sheet, base, Vector(corner), parameters)
        flanks = 0
        for edge in result.edges():
            if len(topo_explore_connected_faces(edge, result)) != 1:
                continue
            if edge.distance_to(Vector(corner)) > 12:
                continue
            offsets = [
                (Vector(edge @ (index / 20)) - Vector(corner)).dot(normal)
                for index in range(21)
            ]
            if max(offsets) - min(offsets) > 1e-6:
                continue
            flanks += 1
            self.assertAlmostEqual(abs(offsets[0]), gap / 2, 6)
        self.assertEqual(flanks, 6)

    @staticmethod
    def gapped_sheet(gap: float) -> BuildSheet:
        """Four walls set back from each other, so every corner is open."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
            flange(builder.edges(), length=20, gaps=gap)
        return builder

    def test_round_relief_on_a_gapped_corner(self):
        """With gaps the flanges no longer meet, so the relief also has the
        two gap strips to miss. Compared against the closed form: three
        quarters of the circle less the part of each strip inside it."""
        for gap in (2.0, 3.1):
            with self.subTest(gap=gap):
                radius = 3.0
                sheet = self.gapped_sheet(gap).sheet_local
                corner = min(
                    sheet.faces().sort_by(Axis.Z)[0].vertices(),
                    key=lambda v: (Vector(v) - Vector(-50, -30, 0)).length,
                )
                result = corner_relief(
                    corner,
                    ReliefType.ROUND,
                    radius=radius,
                    sheet_parameters=self.PARAMETERS,
                )
                self.assertTrue(result.is_valid)

                reach = min(gap, radius)
                strip = (
                    reach * sqrt(radius**2 - reach**2)
                    + radius**2 * asin(reach / radius)
                ) / 2
                self.assertAlmostEqual(
                    self.blank_removed(sheet, result),
                    0.75 * pi * radius**2 - 2 * strip,
                    5,
                )

    @staticmethod
    def hole_sheet(gaps: float = 3.0) -> BuildSheet:
        """A plate with a flanged hole, so two bends meet at a corner the
        sheet wraps around rather than stops at."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
                Rectangle(40, 20, mode=Mode.SUBTRACT)
            hole = builder.flats().sort_by(Axis.Z)[0].inner_wires()[0].edges()
            flange(
                [hole.sort_by(Axis.X)[0], hole.sort_by(Axis.Y)[0]],
                length=15,
                gaps=gaps,
            )
        return builder

    @staticmethod
    def hole_corner(sheet: Shell) -> Vertex:
        """The corner of the hole where the two flanges meet."""
        base = sheet.flats().sort_by(Axis.Z)[0]
        return min(
            base.vertices(), key=lambda v: (Vector(v) - Vector(-20, -10, 0)).length
        )

    def test_relief_at_a_corner_the_sheet_wraps_around(self):
        """Around a hole the sheet fills three quadrants instead of one, and
        both bends unroll into the fourth, so the cut lands on one face."""
        for relief_type, kwargs, area in (
            (ReliefType.ROUND, {"radius": 1.5}, 0.75 * pi * 1.5**2),
            (ReliefType.SQUARE, {"size": 2.0}, 0.75 * 2.0**2),
        ):
            with self.subTest(relief_type=relief_type):
                sheet = self.hole_sheet().sheet_local
                corner = self.hole_corner(sheet)
                self.assertEqual(corner.convexity, Convexity.CONCAVE)
                result = corner_relief(
                    corner, relief_type, **kwargs, sheet_parameters=self.PARAMETERS
                )
                self.assertTrue(result.is_valid)
                self.assertAlmostEqual(sheet.area - result.area, area, 6)

    def test_a_wrapped_corner_relief_still_unfolds(self):
        """Cutting a face leaves the curves either side of the cut stopping a
        fraction of a micron apart - their shared vertex says otherwise, but
        developing the face walks the curves. A bend cut at both ends carries
        two such joins, so all four corners are relieved here rather than one.
        """
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
                with Locations((25, 0)):
                    Rectangle(25, 25, mode=Mode.SUBTRACT)
            hole = builder.flats().sort_by(Axis.Z)[0].inner_wires()[0]
            flange(hole.edges(), length=10, radius=1, gaps=0.5)
            miter(
                builder.flats()
                .filter_by(Axis.Z, reverse=True)
                .sort_by_distance((25, 0, 0))[0:4]
                .vertices()
                .group_by(Axis.Z)[-1],
                45,
                through_bend=True,
            )
            corners = (
                builder.flats()
                .sort_by(Axis.Z)[0]
                .vertices()
                .filter_by(Convexity.CONCAVE)
                .sort_by_distance((25, 0, 0))[0:4]
            )
            self.assertEqual(len(corners), 4)
            corner_relief(corners[0], ReliefType.ROUND, radius=1.0)
            corner_relief(corners[1], ReliefType.SQUARE, size=2.0)
            corner_relief(corners[2:4], ReliefType.OBROUND, length=4.0, width=2.0)
        parameters = builder.sheet_parameters
        part = thicken(builder.sheet_local, sheet_parameters=parameters)
        for sheet in (builder.sheet_local, builder.sheet):
            flat = sheet.unfold(parameters)
            self.assertTrue(flat.is_valid)
            self.assertAlmostEqual(part.volume, flat.area, 3)

    def test_a_wrapped_corner_relief_can_reach_past_the_gaps(self):
        """Both bends unroll into the quadrant past the corner, so a relief
        reaching past the gaps their flanges leave takes a bite out of each."""
        sheet = self.hole_sheet().sheet_local
        result = corner_relief(
            self.hole_corner(sheet),
            ReliefType.ROUND,
            radius=5,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertTrue(result.is_valid)
        before = sorted(f.area for f in sheet.faces().filter_by(GeomType.CYLINDER))
        after = sorted(f.area for f in result.faces().filter_by(GeomType.CYLINDER))
        for was, now in zip(before, after):
            self.assertLess(now, was - 1)
        flat = result.unfold(self.PARAMETERS)
        self.assertTrue(flat.is_valid)
        self.assertAlmostEqual(
            flat.area, thicken(result, sheet_parameters=self.PARAMETERS).volume, 3
        )
        with self.assertRaisesRegex(ValueError, "wraps around this corner"):
            corner_relief(
                self.hole_corner(sheet),
                ReliefType.CONSTANT_WIDTH,
                depth=2,
                sheet_parameters=self.PARAMETERS,
            )

    @staticmethod
    def mitered_hole_sheet() -> BuildSheet:
        """Four flanges folded into a hole and mitered through their bends,
        so they come to a point at each corner with no gap between them."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
                with Locations((25, 0)):
                    Rectangle(25, 25, mode=Mode.SUBTRACT)
            hole = builder.flats().sort_by(Axis.Z)[0].inner_wires()[0]
            flange(hole.edges(), length=6, gaps=0)
            walls = (
                builder.flats()
                .filter_by(Axis.Z, reverse=True)
                .sort_by_distance((25, 0, 0))[0:4]
            )
            miter(walls.vertices().group_by(Axis.Z)[-1], 45, through_bend=True)
        return builder

    def test_relief_across_a_mitered_wrapped_corner(self):
        """Mitering the bends brings them to a point together, so they meet
        along a seam in the blank rather than covering the same ground - and a
        relief can be divided between them along it. The blank is whole around
        such a corner, so the whole profile lands on material."""
        for radius in (1.0, 2.0, 3.0):
            with self.subTest(radius=radius):
                sheet = self.mitered_hole_sheet().sheet_local
                corner = min(
                    sheet.flats().sort_by(Axis.Z)[0].vertices(),
                    key=lambda v: (Vector(v) - Vector(12.5, -12.5, 0)).length,
                )
                result = corner_relief(
                    corner,
                    ReliefType.ROUND,
                    radius=radius,
                    sheet_parameters=self.PARAMETERS,
                )
                self.assertTrue(result.is_valid)
                # three quadrants of sheet plus one shared by the two bends
                self.assertAlmostEqual(
                    sheet.area - result.area,
                    pi * radius**2 * (0.75 + 0.25 * self.SCALE),
                    4,
                )

    def test_a_wrapped_corner_relief_survives_forming(self):
        builder = self.hole_sheet()
        with builder:
            corner_relief(
                self.hole_corner(builder.sheet_local), ReliefType.ROUND, radius=1.5
            )
        parameters = builder.sheet_parameters
        flat = unfold(builder.sheet_local, sheet_parameters=parameters)
        part = thicken(builder.sheet_local, sheet_parameters=parameters)
        self.assertAlmostEqual(part.volume, flat.area, 6)

    def test_corner_vertex_is_removed(self):
        """A relief that leaves the corner in place has not opened it."""
        sheet = self.two_flange_sheet().sheet_local
        corner = Vector(self.shared_corner(sheet))
        result = corner_relief(
            self.shared_corner(sheet),
            ReliefType.ROUND,
            radius=3.0,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertFalse(
            any((Vector(v) - corner).length < 1e-7 for v in result.vertices())
        )

    def test_builder_mode(self):
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
            edges = builder.edges().filter_by(GeomType.LINE)
            flange(
                [edges.sort_by(Axis.Y)[-1], edges.sort_by(Axis.X)[-1]],
                length=20,
            )
            before = builder.sheet_local.area
            corner = self.shared_corner(builder.sheet_local)
            corner_relief(corner, ReliefType.ROUND, radius=3.0)
        quarter = pi * 3**2 / 4
        self.assertAlmostEqual(
            before - builder.sheet_local.area, quarter * (1 + 2 * self.SCALE), 5
        )

    def test_requires_a_vertex(self):
        with self.assertRaisesRegex(ValueError, "at least one vertex"):
            corner_relief(sheet_parameters=self.PARAMETERS)

    def test_takes_only_vertices(self):
        sheet = self.two_flange_sheet().sheet_local
        with self.assertRaisesRegex(ValueError, "only Vertices"):
            corner_relief(
                sheet.edges()[0],
                ReliefType.ROUND,
                radius=3.0,
                sheet_parameters=self.PARAMETERS,
            )

    def test_parameters_are_checked_per_type(self):
        sheet = self.two_flange_sheet().sheet_local
        corner = self.shared_corner(sheet)
        with self.assertRaisesRegex(ValueError, "radius is required"):
            corner_relief(corner, ReliefType.ROUND, sheet_parameters=self.PARAMETERS)
        with self.assertRaisesRegex(ValueError, "must be positive"):
            corner_relief(
                corner, ReliefType.ROUND, radius=-1.0, sheet_parameters=self.PARAMETERS
            )
        with self.assertRaisesRegex(ValueError, "does not accept"):
            corner_relief(
                corner,
                ReliefType.SQUARE,
                size=5.0,
                depth=1.0,
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "length must exceed width"):
            corner_relief(
                corner,
                ReliefType.OBROUND,
                length=3.0,
                width=8.0,
                sheet_parameters=self.PARAMETERS,
            )

    def test_corner_must_have_two_bends(self):
        sheet = self.two_flange_sheet().sheet_local
        opposite = min(
            sheet.vertices(),
            key=lambda vertex: (Vector(vertex) - Vector(-50, -30, 0)).length,
        )
        with self.assertRaisesRegex(ValueError, "expected 2"):
            corner_relief(
                opposite, ReliefType.ROUND, radius=3.0, sheet_parameters=self.PARAMETERS
            )


class TestBendRelief(unittest.TestCase):
    """Relief where a bend ends inside the sheet."""

    PARAMETERS = SheetMetalParameters(thickness=1, bend_radius=2)
    SCALE = 2 / 2.5  # reference radius over neutral radius, k = 0.5

    @classmethod
    def blank_removed(cls, before: Shell, after: Shell) -> float:
        """How much the blank loses - where a relief is laid out."""
        return (
            unfold(before, sheet_parameters=cls.PARAMETERS).area
            - unfold(after, sheet_parameters=cls.PARAMETERS).area
        )

    @staticmethod
    def tab_sheet(gap: float = 2.0) -> BuildSheet:
        """Two walls held back from the ends of their edges, so all four
        bends stop inside the blank without meeting another bend."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
            flange(builder.edges().filter_by(Axis.X), length=20, gaps=gap)
        return builder

    @staticmethod
    def bends(sheet: Shell) -> ShapeList[Face]:
        """The bend faces of a sheet."""
        return sheet.faces().filter_by(GeomType.CYLINDER)

    def test_notches_reach_the_material_past_each_bend_end(self):
        """Four bend ends stop inside the blank, and each takes a notch of
        its own out of the face the sheet carries on into."""
        depth, width = 4.0, 1.5
        sheet = self.tab_sheet().sheet_local
        for relief_type, area in (
            (ReliefType.SQUARE, depth * width),
            (ReliefType.OBROUND, width * (depth - width / 2) + pi * width**2 / 8),
        ):
            with self.subTest(relief_type=relief_type):
                result = bend_relief(
                    self.bends(sheet),
                    relief_type,
                    depth=depth,
                    width=width,
                    sheet_parameters=self.PARAMETERS,
                )
                self.assertTrue(result.is_valid)
                self.assertAlmostEqual(sheet.area - result.area, 4 * area, 6)

    def test_round_is_a_hole_centred_on_the_end_of_the_fold_line(self):
        """A quarter of it lies past both the bend end and the fold line,
        where the blank has nothing to remove. It is a circle on the blank, so
        the quarter that crosses the bend reads smaller on the sheet."""
        radius = 1.5
        sheet = self.tab_sheet().sheet_local
        result = bend_relief(
            self.bends(sheet),
            ReliefType.ROUND,
            radius=radius,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertTrue(result.is_valid)
        self.assertAlmostEqual(
            self.blank_removed(sheet, result), 4 * 0.75 * pi * radius**2, 5
        )
        quarter = pi * radius**2 / 4
        self.assertAlmostEqual(
            sheet.area - result.area, 4 * quarter * (2 + self.SCALE), 6
        )

    def test_relief_survives_developing(self):
        """A relief cut in the flat pattern removes the same area folded."""
        sheet = self.tab_sheet().sheet_local
        for relief_type, kwargs in (
            (ReliefType.ROUND, {"radius": 1.5}),
            (ReliefType.SQUARE, {"depth": 3.0, "width": 1.5}),
            (ReliefType.OBROUND, {"depth": 3.0, "width": 1.5}),
        ):
            with self.subTest(relief_type=relief_type):
                result = bend_relief(
                    self.bends(sheet),
                    relief_type,
                    **kwargs,
                    sheet_parameters=self.PARAMETERS,
                )
                self.assertAlmostEqual(
                    sheet.area - result.area,
                    sheet.unfold().area - result.unfold().area,
                    6,
                )

    def test_sizes_default_to_the_bend_and_the_thickness(self):
        """The notch reaches a bend radius plus a thickness past the fold
        line and is one thickness wide."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
            flange(builder.edges().filter_by(Axis.X), length=20, gaps=2)
            before = builder.sheet_local.area
            bend_relief(self.bends(builder.sheet_local), ReliefType.SQUARE)
        removed = before - builder.sheet_local.area
        self.assertAlmostEqual(removed, 4 * (2 + 1) * 1, 6)

    def test_ends_that_reach_the_edge_of_the_blank_are_left_alone(self):
        """Without gaps the bends run the full width, so nothing needs
        relief and the selection acts as a filter rather than an error."""
        sheet = self.tab_sheet(gap=0).sheet_local
        result = bend_relief(
            self.bends(sheet),
            ReliefType.SQUARE,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertAlmostEqual(sheet.area, result.area, 9)

    def test_relief_on_a_flange_around_a_hole(self):
        """A fold line on the boundary of a hole has the sheet on the far side
        of it from the middle of the face, which is no guide to where the
        material is."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
                Rectangle(40, 20, mode=Mode.SUBTRACT)
            hole = builder.flats().sort_by(Axis.Z)[0].inner_wires()[0]
            flange(hole.edges().sort_by(Axis.X)[0], length=15, angle=45, gaps=3)
            before = builder.sheet_local.area
            bend_relief(builder.bends().sort_by(Face.length)[0], ReliefType.SQUARE)
        removed = before - builder.sheet_local.area
        self.assertAlmostEqual(removed, 2 * (2 + 1) * 1, 6)
        self.assertTrue(builder.sheet_local.is_valid)

    def test_overlapping_reliefs_are_a_corner(self):
        """Where two gapped flanges meet, the bend ends are close enough that
        their notches overlap and cut the corner of the sheet loose - one
        corner relief does the job of both."""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(100, 60)
            flange(builder.edges(), length=20, gaps=2)
            with self.assertRaisesRegex(ValueError, "separates part of the face"):
                bend_relief(self.bends(builder.sheet_local), ReliefType.SQUARE)

    def test_relief_wider_than_the_material_takes_the_corner_off(self):
        """A notch wider than the sheet past the bend end runs out through the
        edge of the blank, taking the corner with it."""
        sheet = self.tab_sheet(gap=2).sheet_local
        result = bend_relief(
            self.bends(sheet),
            ReliefType.SQUARE,
            depth=3,
            width=5,
            sheet_parameters=self.PARAMETERS,
        )
        self.assertTrue(result.is_valid)
        # four bend ends, each notch clipped to the 2 wide gap
        self.assertAlmostEqual(sheet.area - result.area, 4 * 3 * 2, 6)
        self.assertEqual(len(result.faces()), len(sheet.faces()))

    def test_input_validation(self):
        sheet = self.tab_sheet().sheet_local
        bends = self.bends(sheet)
        with self.assertRaisesRegex(ValueError, "at least one bend face"):
            bend_relief(sheet_parameters=self.PARAMETERS)
        with self.assertRaisesRegex(ValueError, "only Faces"):
            bend_relief(
                sheet.edges()[0],
                ReliefType.SQUARE,
                depth=3,
                width=1,
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "only cylindrical"):
            bend_relief(
                sheet.faces().filter_by(GeomType.PLANE)[0],
                ReliefType.SQUARE,
                depth=3,
                width=1,
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "use corner_relief"):
            bend_relief(
                bends,
                ReliefType.CONSTANT_WIDTH,
                depth=3,
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "does not accept radius"):
            bend_relief(
                bends, ReliefType.SQUARE, radius=2.0, sheet_parameters=self.PARAMETERS
            )
        with self.assertRaisesRegex(ValueError, "width must be positive"):
            bend_relief(
                bends,
                ReliefType.SQUARE,
                depth=3,
                width=-1,
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "half the width"):
            bend_relief(
                bends,
                ReliefType.OBROUND,
                depth=1,
                width=4,
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "sheet_parameters is required"):
            bend_relief(bends, ReliefType.SQUARE)


class TestBend(unittest.TestCase):
    """Folding a sheet along an edge it already carries."""

    PARAMETERS = SheetMetalParameters(
        thickness=1, bend_radius=1, sheet_surface=SheetSurface.NEUTRAL
    )
    ARC = pi / 2 * 1.5  # a 90 degree bend on the neutral surface, r=1, t=1

    @staticmethod
    def blank(cuts, width, depth=5.0) -> Shell:
        """A flat blank already divided along the lines it folds on.

        How a blank comes to carry those edges - imported with the outline, or
        marked on a sketch - is not this operation's business, so the tests
        sew one directly.
        """
        bounds = [0.0] + list(cuts) + [width]
        return Shell(
            [
                Face(
                    Plane.XY
                    * Pos(near, 0)
                    * Rectangle(
                        far - near, depth, align=(Align.MIN, Align.CENTER)
                    ).wire()
                )
                for near, far in zip(bounds, bounds[1:])
            ]
        )

    @classmethod
    def fold_line(cls, sheet: Shell, face: Face) -> Edge | None:
        """An edge of a face shared with a coplanar neighbour."""
        normal = face.normal_at(face.center())
        for edge in face.edges():
            beside = [
                Face(raw)
                for raw in topo_explore_connected_faces(edge, sheet)
                if raw is not None and not Face(raw).is_same(face)
            ]
            if (
                len(beside) == 1
                and beside[0].geom_type == GeomType.PLANE
                and normal.cross(beside[0].normal_at(beside[0].center())).length < 1e-7
            ):
                return edge
        return None

    @classmethod
    def leftmost_fold(cls, sheet: Shell) -> tuple:
        """The foldable face nearest the origin, and its fold line."""
        face = min(
            (
                f
                for f in sheet.faces().filter_by(GeomType.PLANE)
                if cls.fold_line(sheet, f)
            ),
            key=lambda f: f.center().X,
        )
        return face, cls.fold_line(sheet, face)

    def test_the_bend_takes_its_own_width_from_the_sheet(self):
        """The sheet keeps the length it was drawn with: the strip the bend
        rolls up is exactly its arc on the reference surface."""
        sheet = self.blank([5.0], 10.0)
        face, line = self.leftmost_fold(sheet)
        result = bend(line, angle=90, radius=1, sheet_parameters=self.PARAMETERS)
        self.assertTrue(result.is_valid)
        legs = sorted(
            f.area / 5 for f in result.faces() if f.geom_type == GeomType.PLANE
        )
        arcs = [f.area / 5 for f in result.faces() if f.geom_type == GeomType.CYLINDER]
        self.assertAlmostEqual(arcs[0], self.ARC, 6)
        self.assertAlmostEqual(legs[-1], 5.0, 6)
        self.assertAlmostEqual(legs[0], 5.0 - self.ARC, 6)
        self.assertAlmostEqual(result.area / 5, 10.0, 6)

    def test_the_face_the_edge_came_from_is_the_one_that_stays(self):
        """An edge lies between two faces; the one it was selected from is
        what says which side holds still, and nothing is inferred from which
        side happens to be bigger."""
        for keep, expected in (("near", 3.0), ("far", 7.0)):
            with self.subTest(keep=keep):
                sheet = self.blank([3.0], 10.0)
                chooser = min if keep == "near" else max
                face = chooser(sheet.faces(), key=lambda f: f.center().X)
                result = bend(
                    self.fold_line(sheet, face),
                    angle=90,
                    radius=1,
                    sheet_parameters=self.PARAMETERS,
                )
                flat = [
                    f
                    for f in result.faces()
                    if f.geom_type == GeomType.PLANE and abs(f.center().Z) < 1e-9
                ]
                self.assertEqual(len(flat), 1)
                self.assertAlmostEqual(flat[0].area / 5, expected, 6)

    def test_position_moves_the_bend_along_the_line(self):
        """Each position names a feature of the formed bend that lands on the
        line, which sets how far back its near tangent sits."""
        for position, setback in (
            (BendPosition.BEND_OUTSIDE, 0.0),
            (BendPosition.MATERIAL_INSIDE, 1.0 * tan(radians(45))),
            (BendPosition.CENTER, pi / 2 * 1.5 / 2),
            (BendPosition.MATERIAL_OUTSIDE, 2.0 * tan(radians(45))),
        ):
            with self.subTest(position=position):
                sheet = self.blank([5.0], 10.0)
                face, line = self.leftmost_fold(sheet)
                result = bend(
                    line,
                    angle=90,
                    radius=1,
                    position=position,
                    sheet_parameters=self.PARAMETERS,
                )
                fixed = [
                    f
                    for f in result.faces()
                    if f.geom_type == GeomType.PLANE and abs(f.center().Z) < 1e-9
                ]
                self.assertAlmostEqual(fixed[0].area / 5, 5.0 - setback, 6)
                self.assertAlmostEqual(result.area / 5, 10.0, 6)

    def test_folds_chain_and_carry_what_is_attached(self):
        """A fold leaves the sheet's remaining fold lines alone, so the next
        one has something to work with, and swings everything beyond it."""
        sheet = self.blank([8.0, 16.0, 24.0], 32.0)
        for angle in (90, -90, 90):
            face, line = self.leftmost_fold(sheet)
            sheet = bend(line, angle=angle, radius=1, sheet_parameters=self.PARAMETERS)
        self.assertTrue(sheet.is_valid)
        self.assertEqual(len(sheet.faces()), 7)
        self.assertAlmostEqual(sheet.area / 5, 32.0, 6)
        part = thicken(sheet, sheet_parameters=self.PARAMETERS)
        self.assertAlmostEqual(
            part.volume, sheet.unfold(sheet_parameters=self.PARAMETERS).area, 6
        )

    def test_input_validation(self):
        sheet = self.blank([5.0], 10.0)
        face, line = self.leftmost_fold(sheet)
        free = next(
            edge
            for edge in face.edges()
            if len(topo_explore_connected_faces(edge, sheet)) == 1
            and abs(edge.length - 5.0) < 1e-9
        )
        with self.assertRaisesRegex(ValueError, "requires a bend_line"):
            bend()
        with self.assertRaisesRegex(ValueError, "not selected through a face"):
            bend(
                Edge.make_line((5, -2.5, 0), (5, 2.5, 0)),
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "shared with exactly one other face"):
            bend(free, sheet_parameters=self.PARAMETERS)
        with self.assertRaisesRegex(ValueError, "non-zero"):
            bend(line, angle=0, sheet_parameters=self.PARAMETERS)
        with self.assertRaisesRegex(ValueError, "does not fit"):
            bend(line, angle=90, radius=4, sheet_parameters=self.PARAMETERS)
        with self.assertRaisesRegex(ValueError, "never meet"):
            bend(
                line,
                angle=180,
                position=BendPosition.MATERIAL_INSIDE,
                sheet_parameters=self.PARAMETERS,
            )
        with self.assertRaisesRegex(ValueError, "sheet_parameters is required"):
            bend(line)

    def test_the_face_is_found_through_a_wire_too(self):
        """The face is the innermost one on the route, however many steps the
        selection took to reach the edge."""
        sheet = self.blank([5.0], 10.0)
        face = min(sheet.faces(), key=lambda f: f.center().X)
        line = min(
            (
                edge
                for edge in face.outer_wire().edges()
                if len(topo_explore_connected_faces(edge, sheet)) == 2
            ),
            key=lambda edge: edge.length,
        )
        self.assertEqual([type(s) for s in line.topo_path], [Shell, Face, Wire])
        result = bend(line, angle=90, radius=1, sheet_parameters=self.PARAMETERS)
        flat = [
            f
            for f in result.faces()
            if f.geom_type == GeomType.PLANE and abs(f.center().Z) < 1e-9
        ]
        self.assertAlmostEqual(flat[0].area / 5, 5.0, 6)

    def test_an_edge_without_a_face_behind_it_is_reported(self):
        """Taken off the sheet rather than through a face, an edge says
        nothing about which side stays put - and the topology cannot say
        either, since both faces are equally its own. Selecting the same edge
        through a face is the answer, and it is no more work."""
        sheet = self.blank([5.0], 10.0)
        loose = min(
            (
                edge
                for edge in sheet.edges()
                if len(topo_explore_connected_faces(edge, sheet)) == 2
            ),
            key=lambda edge: edge.length,
        )
        self.assertFalse(any(isinstance(step, Face) for step in loose.topo_path))
        with self.assertRaisesRegex(ValueError, "not selected through a face"):
            bend(loose, sheet_parameters=self.PARAMETERS)

    def test_an_edge_of_a_bend_cannot_name_the_fixed_side(self):
        """The face on the route has to be flat to fold about."""
        sheet = self.blank([5.0], 10.0)
        _, line = self.leftmost_fold(sheet)
        folded = bend(line, angle=90, radius=1, sheet_parameters=self.PARAMETERS)
        cylinder = folded.faces().filter_by(GeomType.CYLINDER)[0]
        tangent = cylinder.edges().filter_by(GeomType.LINE)[0]
        with self.assertRaisesRegex(ValueError, "selected through a planar face"):
            bend(tangent, sheet_parameters=self.PARAMETERS)

    def test_a_bend_cannot_be_folded_again(self):
        sheet = self.blank([5.0], 10.0)
        face, line = self.leftmost_fold(sheet)
        folded = bend(line, angle=90, radius=1, sheet_parameters=self.PARAMETERS)
        base = min(folded.faces().filter_by(GeomType.PLANE), key=lambda f: f.center().X)
        tangent = next(
            edge
            for edge in base.edges()
            if len(topo_explore_connected_faces(edge, folded)) == 2
        )
        with self.assertRaisesRegex(ValueError, "already bent"):
            bend(tangent, sheet_parameters=self.PARAMETERS)


if __name__ == "__main__":
    unittest.main()
