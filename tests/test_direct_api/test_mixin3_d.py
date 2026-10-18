"""
build123d imports

name: test_mixin3_d.py
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
from unittest.mock import Mock, patch, PropertyMock

from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.ChFiDS import ChFiDS_ErrorStatus
from OCP.Standard import Standard_Failure
from OCP.StdFail import StdFail_NotDone
from OCP.TopoDS import TopoDS

from build123d.build_enums import CenterOf, GeomType, Kind
from build123d.build_part import BuildPart
from build123d.geometry import Axis, Plane, Pos
from build123d.objects_part import Box, Cylinder
from build123d.objects_sketch import RectangleRounded
from build123d.operations_generic import fillet
from build123d.operations_part import extrude
from build123d.topology import Compound, Edge, Face, Part, Shape, Solid

# A failed fillet is StdFail_NotDone on Linux and Windows and Standard_Failure
# on macOS; the two are unrelated classes in OCP, and Mixin3D.fillet catches both
KERNEL_FAILURES = (StdFail_NotDone, Standard_Failure)


class TestFilletFailures(unittest.TestCase):
    """Identify the rejected selection without losing the kernel's failure."""

    advice = (
        ", try a smaller value or use max_fillet() to find the largest valid"
        " fillet radius"
    )
    plate_message = (
        "Failed creating a fillet with radius of 3 on 8 of 12 edges "
        "(no starting solution: [1] at (-10, 0, 1), [3] at (-10, 0, -1), "
        "[5] at (10, 0, 1), [7] at (10, 0, -1), [8] at (0, -10, -1), "
        "[9] at (0, -10, 1), [10] at (0, 10, -1), [11] at (0, 10, 1))" + advice
    )

    def test_plate(self):
        """Box, Solid and Part share the same diagnostic path."""
        box = Box(20, 20, 2)
        for shape in (box, box.solid(), Part(box.wrapped)):
            with self.subTest(shape=type(shape).__name__):
                with self.assertRaises(ValueError) as caught:
                    shape.fillet(3, shape.edges())
                self.assertEqual(str(caught.exception), self.plate_message)
                self.assertIsInstance(caught.exception.__cause__, KERNEL_FAILURES)

    def test_operation(self):
        """The fillet operation reports the same edges in algebra and builder mode."""
        with self.subTest(mode="algebra"):
            with self.assertRaises(ValueError) as caught:
                fillet(Box(20, 20, 2).edges(), radius=3)
            self.assertEqual(str(caught.exception), self.plate_message)
        with self.subTest(mode="builder"):
            with BuildPart() as plate:
                Box(20, 20, 2)
                with self.assertRaises(ValueError) as caught:
                    fillet(plate.edges(), radius=3)
            self.assertEqual(str(caught.exception), self.plate_message)

    def test_tangent_chain(self):
        """Unselected tangent edges are counted, with a point on a curved selection."""
        rounded = extrude(RectangleRounded(20, 10, 3), 2)
        top_edges = rounded.edges().group_by(Axis.Z)[-1]
        for selection, details in (
            (
                top_edges.filter_by(GeomType.LINE)[:1],
                "1 of 1 edges (no starting solution: [0] at (-10, 0, 2), "
                "7 additional tangent edges)",
            ),
            (
                top_edges.filter_by(GeomType.CIRCLE)[:1],
                "1 of 1 edges (no starting solution: [0] at (-9.12132, -4.12132, 2), "
                "7 additional tangent edges)",
            ),
            (
                top_edges[:7],
                "7 of 7 edges (no starting solution: [0] at (-10, 0, 2), "
                "[1] at (-9.12132, -4.12132, 2), [2] at (0, -5, 2), "
                "[3] at (9.12132, -4.12132, 2), [4] at (10, 0, 2), "
                "[5] at (9.12132, 4.12132, 2), [6] at (0, 5, 2), "
                "1 additional tangent edge)",
            ),
        ):
            with self.subTest(details=details):
                with self.assertRaises(ValueError) as caught:
                    rounded.fillet(3, selection)
                self.assertEqual(
                    str(caught.exception),
                    "Failed creating a fillet with radius of 3 on "
                    + details
                    + self.advice,
                )

    def test_plain_message(self):
        """Failures not traced to a selected contour keep the plain message."""
        cube = Box(10, 10, 10)
        # The only faulty stripe here lies past NbContours() and has no spine
        notched = Box(20, 20, 12) - Pos(7, 7, 4) * Box(12, 12, 12)
        for shape, radius, edges in (
            (cube, 6, cube.edges()),
            (notched, 0.5, notched.edges()[::2]),
        ):
            with self.subTest(radius=radius):
                with self.assertRaises(ValueError) as caught:
                    shape.fillet(radius, edges)
                self.assertEqual(
                    str(caught.exception),
                    f"Failed creating a fillet with radius of {radius}" + self.advice,
                )

    def test_generator_duplicates_and_reversed_edges(self):
        """Indices follow the iterable, including repeated and reversed selections."""
        plate = Box(20, 20, 2)
        edges = plate.edges()
        reversed_edge = Edge(TopoDS.Edge(edges[1].wrapped.Reversed()))
        self.assertTrue(edges[1].is_same(reversed_edge))
        self.assertFalse(edges[1].is_equal(reversed_edge))
        selection = (edge for edge in [edges[3], edges[0], reversed_edge, edges[1]])
        with self.assertRaises(ValueError) as caught:
            plate.fillet(3, selection)
        self.assertEqual(
            str(caught.exception),
            "Failed creating a fillet with radius of 3 on 3 of 4 edges "
            "(no starting solution: [0] at (-10, 0, -1), "
            "[2] at (-10, 0, 1), [3] at (-10, 0, 1))" + self.advice,
        )

    def test_diagnostic_readback_failure(self):
        """Any readback failure gives the plain message and keeps the original cause."""
        plate = Box(20, 20, 2)
        for method in (
            "NbFaultyContours",
            "FaultyContour",
            "StripeStatus",
            "NbEdges",
            "Edge",
        ):
            with self.subTest(method=method):
                builder = Mock(wraps=BRepFilletAPI_MakeFillet(plate.wrapped))
                getattr(builder, method).side_effect = RuntimeError("readback failed")
                with patch(
                    "build123d.topology.three_d.BRepFilletAPI_MakeFillet",
                    return_value=builder,
                ):
                    with self.assertRaises(ValueError) as caught:
                        plate.fillet(3, plate.edges())
                self.assertEqual(
                    str(caught.exception),
                    "Failed creating a fillet with radius of 3" + self.advice,
                )
                self.assertIsInstance(caught.exception.__cause__, KERNEL_FAILURES)

    def test_group_failure_reasons(self):
        """Different kernel statuses form separate readable groups in caller order."""
        plate = Box(20, 20, 2)
        builder = Mock(wraps=BRepFilletAPI_MakeFillet(plate.wrapped))
        builder.StripeStatus.side_effect = [
            ChFiDS_ErrorStatus.ChFiDS_StartsolFailure,
            ChFiDS_ErrorStatus.ChFiDS_WalkingFailure,
            ChFiDS_ErrorStatus.ChFiDS_TwistedSurface,
            ChFiDS_ErrorStatus.ChFiDS_Error,
        ] * 2
        with patch(
            "build123d.topology.three_d.BRepFilletAPI_MakeFillet", return_value=builder
        ):
            with self.assertRaises(ValueError) as caught:
                plate.fillet(3, plate.edges())
        self.assertEqual(
            str(caught.exception),
            "Failed creating a fillet with radius of 3 on 8 of 12 edges "
            "(no starting solution: [1] at (-10, 0, 1), [8] at (0, -10, -1); "
            "walking failure: [3] at (-10, 0, -1), [9] at (0, -10, 1); "
            "twisted surface: [5] at (10, 0, 1), [10] at (0, 10, -1); "
            "error: [7] at (10, 0, -1), [11] at (0, 10, 1))" + self.advice,
        )


class TestMixin3D(unittest.TestCase):
    """Test that 3D add ins"""

    def test_chamfer(self):
        box = Solid.make_box(1, 1, 1)
        chamfer_box = box.chamfer(0.1, None, box.edges().sort_by(Axis.Z)[-1:])
        self.assertAlmostEqual(chamfer_box.volume, 1 - 0.005, 5)

    def test_chamfer_asym_length(self):
        box = Solid.make_box(1, 1, 1)
        chamfer_box = box.chamfer(0.1, 0.2, box.edges().sort_by(Axis.Z)[-1:])
        self.assertAlmostEqual(chamfer_box.volume, 1 - 0.01, 5)

    def test_chamfer_asym_length_with_face(self):
        box = Solid.make_box(1, 1, 1)
        face = box.faces().sort_by(Axis.Z)[0]
        edge = [face.edges().sort_by(Axis.Y)[0]]
        chamfer_box = box.chamfer(0.1, 0.2, edge, face=face)
        self.assertAlmostEqual(chamfer_box.volume, 1 - 0.01, 5)

    def test_chamfer_object_instance_returns_topology(self):
        box = Box(1, 1, 1)
        chamfer_box = box.chamfer(0.1, None, box.edges().sort_by(Axis.Z)[-1:])

        self.assertIsInstance(chamfer_box, Solid)
        self.assertTrue(chamfer_box.is_valid)

    def test_fillet_object_instance_returns_topology(self):
        box = Box(1, 1, 1)
        fillet_box = box.fillet(0.1, box.edges().sort_by(Axis.Z)[-1:])
        cylinder = Cylinder(1, 1)
        fillet_cylinder = cylinder.fillet(0.1, cylinder.edges().sort_by(Axis.Z)[0:1])

        self.assertIsInstance(fillet_box, Solid)
        self.assertTrue(fillet_box.is_valid)
        self.assertIsInstance(fillet_cylinder, Solid)
        self.assertTrue(fillet_cylinder.is_valid)

    def test_max_fillet_object_instance(self):
        box = Box(1, 1, 1)
        max_radius = box.max_fillet(box.edges().sort_by(Axis.Z)[-1:])

        self.assertGreater(max_radius, 0)

    def test_make_3d_result_compound(self):
        compound = Compound(
            [
                Solid.make_box(1, 1, 1),
                Solid.make_box(1, 1, 1).translate((2, 0, 0)),
            ]
        )

        result = Solid._make_3d_result(compound.wrapped)

        self.assertIsInstance(result, Part)
        self.assertEqual(len(result.solids()), 2)
        self.assertTrue(result.is_valid)

    def test_chamfer_too_high_length(self):
        box = Solid.make_box(1, 1, 1)
        face = box.faces
        self.assertRaises(
            ValueError, box.chamfer, 2, None, box.edges().sort_by(Axis.Z)[-1:]
        )

    def test_chamfer_edge_not_part_of_face(self):
        box = Solid.make_box(1, 1, 1)
        edge = box.edges().sort_by(Axis.Z)[-1:]
        face = box.faces().sort_by(Axis.Z)[0]
        self.assertRaises(ValueError, box.chamfer, 0.1, None, edge, face=face)

    @patch.object(Shape, "is_valid", new_callable=PropertyMock, return_value=False)
    def test_chamfer_invalid_shape_raises_error(self, mock_is_valid):
        box = Solid.make_box(1, 1, 1)

        # Assert that ValueError is raised
        with self.assertRaises(ValueError) as chamfer_context:
            max = box.chamfer(0.1, None, box.edges())

        # Check the error message
        self.assertEqual(
            str(chamfer_context.exception),
            "Failed creating a chamfer, try a smaller length value(s)",
        )

        # Verify is_valid was called
        mock_is_valid.assert_called_once()

    def test_hollow(self):
        shell_box = Solid.make_box(1, 1, 1).hollow([], thickness=-0.1)
        self.assertAlmostEqual(shell_box.volume, 1 - 0.8**3, 5)

        shell_box = Solid.make_box(1, 1, 1)
        shell_box = shell_box.hollow(
            shell_box.faces().filter_by(Axis.Z), thickness=0.1, kind=Kind.INTERSECTION
        )
        self.assertAlmostEqual(shell_box.volume, 1 * 1.2**2 - 1**3, 5)

        shell_box = Solid.make_box(1, 1, 1).hollow(
            [], thickness=0.1, kind=Kind.INTERSECTION
        )
        self.assertAlmostEqual(shell_box.volume, 1.2**3 - 1**3, 5)

        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).hollow([], thickness=0.1, kind=Kind.TANGENT)

    def test_is_inside(self):
        self.assertTrue(Solid.make_box(1, 1, 1).is_inside((0.5, 0.5, 0.5)))

    def test_dprism(self):
        # face
        f = Face.make_rect(0.5, 0.5)
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [f], additive=False
        )
        self.assertTrue(d.is_valid)
        self.assertAlmostEqual(d.volume, 1 - 0.5**2, 5)

        # face with depth
        f = Face.make_rect(0.5, 0.5)
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [f], depth=0.5, thru_all=False, additive=False
        )
        self.assertTrue(d.is_valid)
        self.assertAlmostEqual(d.volume, 1 - 0.5**3, 5)

        # face until
        f = Face.make_rect(0.5, 0.5)
        limit = Face.make_rect(1, 1, Plane((0, 0, 0.5)))
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [f], up_to_face=limit, thru_all=False, additive=False
        )
        self.assertTrue(d.is_valid)
        self.assertAlmostEqual(d.volume, 1 - 0.5**3, 5)

        # wire
        w = Face.make_rect(0.5, 0.5).outer_wire()
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [w], additive=False
        )
        self.assertTrue(d.is_valid)
        self.assertAlmostEqual(d.volume, 1 - 0.5**2, 5)

    def test_center(self):
        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).center(CenterOf.GEOMETRY)

        self.assertAlmostEqual(
            Solid.make_box(1, 1, 1).center(CenterOf.BOUNDING_BOX),
            (0.5, 0.5, 0.5),
            5,
        )


if __name__ == "__main__":
    unittest.main()
