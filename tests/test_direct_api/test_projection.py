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
from build123d.geometry import Axis, Location, Plane, Pos, Vector
from build123d.objects_part import Box
from build123d.topology import Compound, Edge, Face, Solid, Wire


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

    def test_project_clean_wire(self):
        """Verify that the projected edge result is one edge - wire was cleaned"""
        radii, width, opening_angle = (45, 30), 25, 80
        center_arc = Edge.make_ellipse(
            *radii,
            start_angle=270 + opening_angle / 2,
            end_angle=270 - opening_angle / 2,
        )
        center_surface = -Face.extrude(center_arc, (0, 0, 2 * width)).moved(
            Location((0, 0, -width), (0, 0, 180))
        )
        tip_center_loc = center_surface.location_at(center_arc @ 1, x_dir=(1, 0, 0))
        normal_at_tip_center = tip_center_loc.z_axis.direction

        planar_tip_arc = Edge.make_circle(
            width / 2, start_angle=270, end_angle=450
        ).locate(tip_center_loc)
        tip_arc = planar_tip_arc.project_to_shape(
            center_surface, -normal_at_tip_center
        )[0]
        self.assertTrue(isinstance(tip_arc, Edge))
        self.assertAlmostEqual(tip_arc @ 0, planar_tip_arc @ 0, 5)
        self.assertAlmostEqual(tip_arc @ 1, planar_tip_arc @ 1, 5)


if __name__ == "__main__":
    unittest.main()


class TestProjectionCore(unittest.TestCase):
    """Face.project_to_shape and Solid.extrude_until share one extrusion core"""

    def test_onto_one_face_of_a_box(self):
        source = Face.make_rect(4, 4, Plane.XY.offset(10))
        projected = source.project_to_shape(Box(10, 10, 2), (0, 0, -1))
        self.assertEqual(len(projected), 2)  # top and bottom faces
        self.assertIsInstance(projected[0], Face)
        self.assertAlmostEqual(projected[0].area, 16, 5)
        self.assertAlmostEqual(projected[0].center().Z, 1, 5)
        self.assertAlmostEqual(projected[1].center().Z, -1, 5)

    def test_onto_a_sphere_front_first(self):
        source = Face.make_rect(10, 10, Plane.XY.offset(60))
        projected = source.project_to_shape(Solid.make_sphere(50), (0, 0, -1))
        self.assertEqual(len(projected), 2)
        self.assertGreater(projected[0].center().Z, 0)
        self.assertLess(projected[1].center().Z, 0)
        self.assertGreater(projected[0].area, 100)  # curved, so larger than flat

    def test_through_a_stack_of_plates_in_order(self):
        plates = Compound([Pos(Z=z) * Box(20, 20, 1) for z in (0, -5, -10)])
        source = Face.make_rect(4, 4, Plane.XY.offset(5))
        projected = source.project_to_shape(plates, (0, 0, -1))
        heights = [face.center().Z for face in projected]
        self.assertEqual(len(heights), 6)
        self.assertEqual(heights, sorted(heights, reverse=True))

    def test_onto_a_face_target(self):
        source = Face.make_rect(4, 4, Plane.XY.offset(3))
        projected = source.project_to_shape(Face.make_rect(10, 10), (0, 0, -1))
        self.assertEqual(len(projected), 1)
        self.assertAlmostEqual(projected[0].area, 16, 5)

    def test_a_column_that_misses_gives_nothing(self):
        source = Face.make_rect(4, 4, Plane.XY.offset(3)).moved(Location((100, 0, 0)))
        self.assertEqual(source.project_to_shape(Box(10, 10, 2), (0, 0, -1)), [])

    def test_sorting_is_along_the_direction(self):
        """A slanted plate passing close by the profile outside the column is
        nearer in distance, but the flat plate is met first along the column"""
        slanted = Plane((0, 0, -10)).rotated((0, 70, 0)) * Face.make_rect(60, 60)
        flat = Pos(Z=-5) * Face.make_rect(40, 40)
        source = Face.make_rect(2, 2)
        self.assertLess(source.distance_to(slanted), source.distance_to(flat))
        projected = source.project_to_shape(Compound([slanted, flat]), (0, 0, -1))
        self.assertEqual(len(projected), 2)
        self.assertAlmostEqual(projected[0].center().Z, -5, 5)
        self.assertLess(projected[1].center().Z, -7)

    def test_free_vertices_from_sewing_are_ignored(self):
        """Sewing the target fragments of a glyph on a sphere hands back one
        of the glyph's vertices as a free sub-shape beside the two faces"""
        sphere = Solid.make_sphere(50)
        arch_path = (
            sphere.cut(
                Solid.make_cylinder(80, 100, Plane.YZ).locate(Location((-50, 0, -70)))
            )
            .edges()
            .sort_by(Axis.Z)[0]
        )
        text = Compound.make_text("'t", 15, align=(Align.MIN, Align.CENTER))
        projected = sphere.project_faces(text, path=arch_path)
        self.assertEqual(len(projected), 2)  # one region per glyph
        for flat, curved in zip(text.faces(), projected):
            self.assertAlmostEqual(curved.area / flat.area, 1, delta=0.05)
