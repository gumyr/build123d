"""
build123d imports

name: test_shells.py
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

import math
import unittest

from build123d.build_enums import GeomType
from build123d.geometry import Plane, Rot, Vector
from build123d.objects_curve import JernArc, Polyline, Spline
from build123d.objects_sketch import Circle
from build123d.operations_generic import sweep
from build123d.topology import Shell, Solid, Wire


class TestShells(unittest.TestCase):
    def test_shell_init(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        self.assertTrue(box_shell.is_valid)

    def test_shell_init_single_face(self):
        face = Solid.make_cone(1, 0, 2).faces().filter_by(GeomType.CONE).first
        shell = Shell(face)
        self.assertTrue(shell.is_valid)

    def test_center(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        self.assertAlmostEqual(box_shell.center(), (0.5, 0.5, 0.5), 5)

    def test_manifold_shell_volume(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        self.assertAlmostEqual(box_shell.volume, 1, 5)

    def test_nonmanifold_shell_volume(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        nm_shell = Shell(box_faces)
        nm_shell -= nm_shell.faces()[0]
        self.assertAlmostEqual(nm_shell.volume, 0, 5)

    def test_constructor(self):
        with self.assertRaises(TypeError):
            Shell(foo="bar")

        x_section = Rot(90) * Spline((0, -5), (-3, -2), (-2, 0), (-3, 2), (0, 5))
        surface = sweep(x_section, Circle(5).wire())
        single_face = Shell(surface.face())
        self.assertTrue(single_face.is_valid)
        single_face = Shell(surface.faces())
        self.assertTrue(single_face.is_valid)

    def test_sweep(self):
        path_c1 = JernArc((0, 0), (-1, 0), 1, 180)
        path_e = path_c1.edge()
        path_c2 = JernArc((0, 0), (-1, 0), 1, 180) + JernArc((0, 0), (1, 0), 2, -90)
        path_w = path_c2.wire()
        section_e = Circle(0.5).edge()
        section_c2 = Polyline((0, 0), (0.1, 0), (0.2, 0.1))
        section_w = section_c2.wire()

        sweep_e_w = Shell.sweep((path_w ^ 0) * section_e, path_w)
        sweep_w_e = Shell.sweep((path_e ^ 0) * section_w, path_e)
        sweep_w_w = Shell.sweep((path_w ^ 0) * section_w, path_w)
        sweep_c2_c1 = Shell.sweep((path_c1 ^ 0) * section_c2, path_c1)
        sweep_c2_c2 = Shell.sweep((path_c2 ^ 0) * section_c2, path_c2)

        self.assertEqual(len(sweep_e_w.faces()), 2)
        self.assertEqual(len(sweep_w_e.faces()), 2)
        self.assertEqual(len(sweep_c2_c1.faces()), 2)
        self.assertEqual(len(sweep_w_w.faces()), 3)  # 3 with clean, 4 without
        self.assertEqual(len(sweep_c2_c2.faces()), 3)  # 3 with clean, 4 without

    def test_make_loft(self):
        r = 3
        h = 2
        loft = Shell.make_loft(
            [Wire.make_circle(r, Plane((0, 0, h))), Wire.make_circle(r)]
        )
        self.assertEqual(loft.volume, 0, "A shell has no volume")
        cylinder_area = 2 * math.pi * r * h
        self.assertAlmostEqual(loft.area, cylinder_area)

    def test_thicken(self):
        rect = Wire.make_rect(10, 5)
        shell: Shell = Shell.extrude(rect, Vector(0, 0, 3))
        thick = Solid.thicken(shell, 1)

        self.assertEqual(isinstance(thick, Solid), True)
        inner_vol = 3 * 10 * 5
        outer_vol = 3 * 12 * 7
        self.assertAlmostEqual(thick.volume, outer_vol - inner_vol)

    def test_location_at(self):
        shell = Solid.make_cylinder(1, 2).shell()
        top_center = shell.location_at((0, 0, 2))
        self.assertAlmostEqual(top_center.position, (0, 0, 2), 5)
        self.assertAlmostEqual(top_center.z_axis.direction, (0, 0, 1), 5)
        self.assertAlmostEqual(top_center.x_axis.direction, (1, 0, 0), 5)


if __name__ == "__main__":
    unittest.main()
