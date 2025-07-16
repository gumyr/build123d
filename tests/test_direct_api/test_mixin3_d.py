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
from unittest.mock import patch, PropertyMock

from build123d.build_enums import CenterOf, Kind
from build123d.geometry import Axis, Plane
from build123d.topology import Face, Shape, Solid


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
