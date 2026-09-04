"""Tests for the surface-native BuildSheet builder and operations."""

import unittest
from math import asin, degrees, pi, radians, sin, tan
from unittest.mock import PropertyMock, patch

from build123d import *
from build123d.operations_sheet import (
    MIN_BEND_RADIUS,
    _bisection,
    _hem_parameters,
    _outward_direction,
)
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
        self.assertEqual(parameters.k_factor, 0.5)
        self.assertEqual(parameters.sheet_surface, SheetSurface.INSIDE)

        with self.assertRaises(ValueError):
            SheetMetalParameters(thickness=0)
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

    def test_result_face_normalization(self):
        face = Face.make_rect(10, 10)
        shell = Shell(face)
        self.assertEqual(BuildSheet._result_faces(face), [face])
        self.assertEqual(BuildSheet._result_faces(shell), list(shell.faces()))
        self.assertEqual(BuildSheet._result_faces([shell]), list(shell.faces()))

    def test_shell_validation_errors(self):
        self.assertFalse(BuildSheet._validated_shell([]))
        sphere = Solid.make_sphere(1).faces()[0]
        with self.assertRaisesRegex(ValueError, "planar and cylindrical"):
            BuildSheet._validated_shell([sphere])

        cylinder = Solid.make_cylinder(1, 1).faces().filter_by(GeomType.CYLINDER)[0]
        with patch.object(Face, "radius", new_callable=PropertyMock, return_value=0):
            with self.assertRaisesRegex(ValueError, "positive radius"):
                BuildSheet._validated_shell([cylinder])

        face = Face.make_rect(10, 10)
        with patch.object(
            Shell, "is_valid", new_callable=PropertyMock, return_value=False
        ):
            with self.assertRaisesRegex(ValueError, "invalid shell"):
                BuildSheet._validated_shell([face])

        with patch(
            "build123d.build_sheet.topo_explore_connected_faces",
            return_value=[face, face, face],
        ):
            with self.assertRaisesRegex(ValueError, "non-manifold"):
                BuildSheet._validated_shell([face])

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
        with self.assertRaisesRegex(ValueError, "only accepts"):
            builder._add_to_context(Solid.make_box(1, 1, 1))

    def test_merge_coplanar_faces_leaves_non_face_fuse_result(self):
        faces = [Face.make_rect(10, 10), Pos(10, 0) * Face.make_rect(10, 10)]
        with patch.object(Face, "fuse", return_value=Compound(faces)):
            self.assertEqual(BuildSheet._merge_coplanar_faces(faces), faces)

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

    def test_insert_rejects_solid(self):
        with BuildSheet(thickness=1):
            with self.assertRaisesRegex(ValueError, "Face, Sketch, or Shell"):
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
            k_factor=0.4,
            sheet_surface=SheetSurface.OUTSIDE,
        )
        result = flange(
            right_edge(sheet), length=10, radius=2, sheet_parameters=parameters
        )
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


class TestUnfold(unittest.TestCase):
    def test_geometric_and_neutral_axis_development(self):
        """All reference surfaces produce the same neutral development."""
        for angle, neutral_radius in ((90, 2.25), (-90, 2.75)):
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


if __name__ == "__main__":
    unittest.main()
