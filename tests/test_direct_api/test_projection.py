"""
build123d imports

name: test_projection.py
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

from build123d.build_enums import Align
from build123d.geometry import Axis, Plane, Pos, Vector
from build123d.objects_part import Box
from build123d.topology import Compound, Edge, Solid, Wire


class TestProjection(unittest.TestCase):
    def test_flat_projection(self):
        sphere = Solid.make_sphere(50)
        projection_direction = Vector(0, -1, 0)
        planar_text_faces = (
            Compound.make_text("Flat", 30, align=(Align.CENTER, Align.CENTER))
            .rotate(Axis.X, 90)
            .faces()
        )
        projected_text_faces = [
            f.project_to_shape(sphere, projection_direction)[0]
            for f in planar_text_faces
        ]
        self.assertEqual(len(projected_text_faces), 4)

    def test_multiple_output_wires(self):
        target = Box(10, 10, 4) - Pos((0, 0, 2)) * Box(5, 5, 2)
        circle = Wire.make_circle(3, Plane.XY.offset(10))
        projection = circle.project_to_shape(target, (0, 0, -1))
        bbox = projection[0].bounding_box()
        self.assertAlmostEqual(bbox.min, (-3, -3, 1), 2)
        self.assertAlmostEqual(bbox.max, (3, 3, 2), 2)
        bbox = projection[1].bounding_box()
        self.assertAlmostEqual(bbox.min, (-3, -3, -2), 2)
        self.assertAlmostEqual(bbox.max, (3, 3, -2), 2)

    def test_text_projection(self):
        sphere = Solid.make_sphere(50)
        arch_path = (
            sphere.cut(
                Solid.make_cylinder(
                    80, 100, Plane(origin=(-50, 0, -70), z_dir=(1, 0, 0))
                )
            )
            .edges()
            .sort_by(Axis.Z)[0]
        )

        projected_text = sphere.project_faces(
            faces=Compound.make_text("dog", font_size=14),
            path=arch_path,
            start=0.01,  # avoid a character spanning the sphere edge
        )
        self.assertEqual(len(projected_text.solids()), 0)
        self.assertEqual(len(projected_text.faces()), 3)

    def test_error_handling(self):
        sphere = Solid.make_sphere(50)
        circle = Wire.make_circle(1)
        with self.assertRaises(ValueError):
            circle.project_to_shape(sphere, center=None, direction=None)[0]

    def test_project_edge(self):
        projection = Edge.make_circle(1, Plane.XY.offset(-5)).project_to_shape(
            Solid.make_box(1, 1, 1), (0, 0, 1)
        )
        self.assertAlmostEqual(projection[0].position_at(1), (1, 0, 0), 5)
        self.assertAlmostEqual(projection[0].position_at(0), (0, 1, 0), 5)
        self.assertAlmostEqual(projection[0].arc_center, (0, 0, 0), 5)


if __name__ == "__main__":
    unittest.main()
