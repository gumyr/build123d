"""
build123d tests

name: test_silhouette.py
by:   Gumyr
date: October 20, 2026

desc:
    Tests for the silhouette helpers: the contour of each face for a view,
    faces split along it, and the fragments that face the viewer.

license:

    Copyright 2026 Gumyr

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
from math import pi, sqrt
from unittest.mock import patch

from build123d.build_enums import GeomType
from build123d.geometry import Axis, Location, Plane, Pos, Rot, Vector
from build123d.objects_curve import Line, Spline
from build123d.objects_part import Box, Cone, Cylinder, Sphere, Torus
from build123d.topology import Compound, Edge, Wire
from build123d.objects_sketch import Circle, Ellipse
from build123d.operations_generic import fillet, scale
from build123d.operations_part import loft, revolve
from build123d.operations_sketch import make_face
from build123d.topology import Face, ShapeList, Vertex
from build123d.topology.silhouette import (
    Viewer,
    contour_edges,
    front_facing,
    silhouette_on_plane,
    split_by_silhouette,
    visible_curves,
    visible_faces,
    visible_regions,
)


def front_area(shape, viewer):
    split, _ = split_by_silhouette(shape, viewer)
    fragments = split.faces()
    assert all(fragment.is_valid for fragment in fragments)
    return sum(face.area for face in front_facing(fragments, viewer)), split


class TestViewer(unittest.TestCase):
    def test_one_of_direction_or_eye(self):
        with self.assertRaises(ValueError):
            Viewer()
        with self.assertRaises(ValueError):
            Viewer(direction=Vector(1, 0, 0), eye=Vector(0, 0, 0))

    def test_direction_at(self):
        along = Viewer.along((2, 0, 0))
        self.assertEqual(along.direction_at((5, 5, 5)), Vector(1, 0, 0))
        at = Viewer.at((0, 0, 10))
        self.assertEqual(at.direction_at((0, 0, 0)), Vector(0, 0, -1))


class TestContourEdges(unittest.TestCase):
    def test_sphere_gives_a_great_circle(self):
        face = Sphere(10).faces()[0]
        edges = contour_edges(face, Viewer.along((1, 0.3, 0.2)))
        self.assertAlmostEqual(sum(edge.length for edge in edges), 2 * pi * 10, 5)
        self.assertTrue(all(edge.geom_type == GeomType.CIRCLE for edge in edges))
        for edge in edges:
            self.assertLess(face.distance_to(edge.position_at(0.3)), 1e-6)

    def test_cylinder_gives_two_lines(self):
        side = Cylinder(5, 20).faces().filter_by(GeomType.CYLINDER)[0]
        edges = contour_edges(side, Viewer.along((1, 0.5, 0)))
        self.assertEqual(len(edges), 2)
        self.assertTrue(all(edge.geom_type == GeomType.LINE for edge in edges))
        self.assertTrue(all(abs(edge.length - 20) < 1e-6 for edge in edges))

    def test_torus_contour_lies_on_the_surface(self):
        """The kernel's own outline edges sit 4e-4 off a torus; the written
        contour is on it"""
        face = Torus(10, 3).faces()[0]
        edges = contour_edges(face, Viewer.along((1, 0, 0.4)))
        self.assertGreater(len(edges), 1)
        for edge in edges:
            for t in (0.1, 0.5, 0.9):
                self.assertLess(face.distance_to(edge.position_at(t)), 1e-5)

    def test_a_plane_has_no_contour(self):
        self.assertEqual(
            contour_edges(Face.make_rect(5, 5), Viewer.along((1, 1, 1))), []
        )


class TestSplitBySilhouette(unittest.TestCase):
    def test_sphere_splits_into_two_hemispheres(self):
        area, split = front_area(Sphere(10), Viewer.along((1, 0.3, 0.2)))
        self.assertEqual(len(split.faces()), 2)
        self.assertAlmostEqual(area, 2 * pi * 10**2, delta=0.01)

    def test_cylinder_seen_from_the_side(self):
        area, split = front_area(Cylinder(5, 20), Viewer.along((1, 0.5, 0)))
        self.assertEqual(len(split.faces()), 5)  # two caps and the side in two
        self.assertAlmostEqual(area, pi * 5 * 20, delta=0.01)  # half the side, no caps

    def test_cylinder_seen_obliquely_shows_a_cap(self):
        area, _ = front_area(
            Rot(30, 40, 0) * Cylinder(5, 20), Viewer.along((1, 0.5, 0))
        )
        self.assertGreater(area, pi * 5 * 20)
        self.assertLess(area, pi * 5 * 20 + pi * 5**2 + 1e-6)

    def test_torus(self):
        area, split = front_area(Torus(10, 3), Viewer.along((1, 0, 0.4)))
        self.assertEqual(len(split.faces()), 5)
        self.assertAlmostEqual(area, Torus(10, 3).area / 2, delta=0.01)

    def test_box_does_not_split(self):
        box = Box(10, 10, 10)
        viewer = Viewer.along((1, 1, 1))
        split, history = split_by_silhouette(box, viewer)
        self.assertEqual(len(split.faces()), 6)
        trace = history.trace([box.wrapped])
        self.assertTrue(all(trace.is_untouched(face.wrapped) for face in split.faces()))
        front = front_facing(split.faces(), viewer)
        self.assertEqual(len(front), 3)
        self.assertAlmostEqual(sum(face.area for face in front), 300, 5)

    def test_history_maps_each_face_to_its_fragments(self):
        sphere = Sphere(10)
        split, history = split_by_silhouette(sphere, Viewer.along((0, 0, 1)))
        fragments = history.modified(sphere.faces()[0].wrapped)
        self.assertEqual(len(fragments), 2)

    def test_sphere_with_a_hole(self):
        shape = Sphere(10) - Cylinder(3, 30)
        area, split = front_area(shape, Viewer.along((1, 0.3, 0.2)))
        self.assertEqual(len(split.faces()), 6)
        self.assertAlmostEqual(area, shape.area / 2, delta=0.01)

    def test_perspective(self):
        """From an eye at distance d the visible cap of a sphere of radius r
        has area 2 pi r^2 (1 - r / d)"""
        eye = Vector(30, 10, 5)
        area, _ = front_area(Sphere(10), Viewer.at(eye))
        self.assertAlmostEqual(area, 2 * pi * 100 * (1 - 10 / eye.length), delta=0.05)

    def test_cone_and_fillets(self):
        area, split = front_area(Cone(10, 3, 15), Viewer.along((1, 0.2, 0.1)))
        self.assertEqual(len(split.faces()), 5)
        self.assertGreater(area, 0)
        rounded = fillet(Box(10, 10, 10).edges().filter_by(Axis.Z), 2)
        area, split = front_area(rounded, Viewer.along((1, 0.4, 0.2)))
        self.assertEqual(len(split.faces()), 12)
        self.assertAlmostEqual(area, rounded.area / 2, delta=0.01)

    def test_moved_rotated_and_scaled_copies(self):
        viewer = Viewer.along((1, 0, 0.4))
        area, _ = front_area(Torus(10, 3), viewer)
        moved, _ = front_area(Pos(100, 50, 20) * Torus(10, 3), viewer)
        self.assertAlmostEqual(moved, area, delta=0.01)
        small, _ = front_area(scale(Torus(10, 3), 0.01), viewer)
        self.assertAlmostEqual(small, area * 1e-4, delta=1e-5)
        located, _ = front_area(Sphere(10).located(Location((5, 5, 5))), viewer)
        self.assertAlmostEqual(located, 2 * pi * 100, delta=0.01)

    def test_freeform_surfaces(self):
        """A loft and a revolved spline: the reference areas were integrated
        over a 400 by 400 uv grid"""
        shape = loft(
            [
                Circle(5).face(),
                Pos(0, 0, 10) * Ellipse(8, 4).face(),
                Pos(0, 0, 20) * Circle(3).face(),
            ]
        )
        area, split = front_area(shape, Viewer.along((1, 0.2, 0.3)))
        self.assertAlmostEqual(sum(f.area for f in split.faces()), shape.area, 4)
        self.assertAlmostEqual(area, 417.39, delta=0.2)

        profile = make_face(
            [
                Spline((0, 0), (8, 5), (6, 12), (9, 20)),
                Line((9, 20), (0, 20)),
                Line((0, 20), (0, 0)),
            ]
        )
        shape = revolve(Plane.XZ * profile, Axis.Z)
        area, split = front_area(shape, Viewer.along((1, 0.2, 0.3)))
        self.assertAlmostEqual(sum(f.area for f in split.faces()), shape.area, 4)
        self.assertAlmostEqual(area, 589.31, delta=0.2)

    def test_a_single_face_is_a_shape_too(self):
        dome = Face.make_surface_from_array_of_points(
            [
                [
                    Vector(x, y, 0.3 * x * x - 0.2 * y * y + 0.5 * x * y)
                    for y in range(-2, 3)
                ]
                for x in range(-2, 3)
            ]
        )
        area, split = front_area(dome, Viewer.along((1, 0, 0)))
        self.assertGreater(len(split.faces()), 1)
        self.assertGreater(area, 0)
        self.assertLess(area, dome.area)

    def test_a_missing_contour_is_reported(self):
        with patch(
            "build123d.topology.silhouette.contour_edges", return_value=ShapeList()
        ):
            with self.assertRaisesRegex(RuntimeError, "found no contour"):
                Sphere(10).faces()[0].silhouette_edges((1, 0, 0))

    def test_a_face_whose_contour_is_its_boundary_is_not_a_failure(self):
        """A fragment of a split shape meets the view along its edges, where
        the normal is perpendicular to it; that is not a contour and not a
        missing one"""
        viewer = Viewer.along((1, 0.3, 0.2))
        for shape in (Sphere(10), Torus(10, 3), Cone(10, 3, 15)):
            split, _ = split_by_silhouette(shape, viewer)
            for fragment in split.faces():
                self.assertEqual(fragment.silhouette_edges(viewer.direction), [])


class TestFaceSilhouetteEdges(unittest.TestCase):
    """Face.silhouette_edges, the public form"""

    def test_parallel_view(self):
        ball = Sphere(10).faces()[0]
        edges = ball.silhouette_edges((1, 0, 0))
        self.assertAlmostEqual(sum(e.length for e in edges), 2 * pi * 10, 4)
        self.assertTrue(all(abs(e.position_at(0.5).X) < 1e-6 for e in edges))
        side = Cylinder(5, 20).faces().filter_by(GeomType.CYLINDER)[0]
        lines = side.silhouette_edges((1, 0, 0))
        self.assertEqual([e.geom_type for e in lines], [GeomType.LINE, GeomType.LINE])
        self.assertAlmostEqual(sum(e.length for e in lines), 40, 5)
        # Seen along X the seam at +X is itself a silhouette line, and is left out
        self.assertEqual(len(side.silhouette_edges((0, 1, 0))), 1)
        self.assertEqual(Face.make_rect(5, 5).silhouette_edges((1, 1, 1)), [])

    def test_perspective_view(self):
        ball = Sphere(10).faces()[0]
        # Seen from nearby the silhouette is a smaller circle, nearer the eye
        near = ball.silhouette_edges(eye=(20, 0, 0))
        self.assertAlmostEqual(sum(e.length for e in near), 2 * pi * sqrt(75), 3)
        self.assertTrue(all(abs(e.position_at(0.5).X - 5) < 1e-6 for e in near))

    def test_one_of_direction_or_eye(self):
        ball = Sphere(10).faces()[0]
        with self.assertRaises(ValueError):
            ball.silhouette_edges()
        with self.assertRaises(ValueError):
            ball.silhouette_edges((1, 0, 0), eye=(20, 0, 0))


class TestFrontFacing(unittest.TestCase):
    def test_interior_point_of_a_ring(self):
        """The parametric centre of a ring is in its hole; the interior
        point is on the material"""
        ring = Face.make_rect(10, 10) - Face.make_rect(4, 4)
        self.assertEqual(
            len(front_facing(ShapeList([ring]), Viewer.along((0, 0, -1)))), 1
        )
        self.assertEqual(
            len(front_facing(ShapeList([ring]), Viewer.along((0, 0, 1)))), 0
        )

    def test_edge_on_faces_are_not_front_facing(self):
        faces = Box(10, 10, 10).faces()
        front = front_facing(faces, Viewer.along((0, 0, -1)))
        self.assertEqual(len(front), 1)
        self.assertAlmostEqual(front[0].center().Z, 5, 5)


class TestVisibility(unittest.TestCase):
    def test_visible_faces_of_a_box(self):
        front = visible_faces(Box(10, 10, 10), Viewer.along((1, 1, 1)))
        self.assertEqual(len(front), 3)
        for face in front:
            self.assertLess(face.normal_at().dot(Vector(1, 1, 1)), 0)

    def test_visible_regions_nearest_first(self):
        stepped = Box(20, 20, 2) + Pos(0, 0, 4) * Box(4, 20, 6)
        label = Face.make_rect(10, 10, Plane.XY.offset(20))
        regions = visible_regions(label, stepped, (0, 0, -1))
        self.assertEqual([round(f.area, 6) for f in regions], [40, 30, 30])
        self.assertEqual(round(regions[0].center().Z, 6), 7)
        self.assertEqual(visible_regions(label, stepped, (0, 0, 1)), [])

    def test_visible_curves(self):
        stepped = Box(20, 20, 2) + Pos(0, 0, 4) * Box(4, 20, 6)
        line = Wire([Edge.make_line((-5, 0, 20), (5, 0, 20))])
        wires = visible_curves(line, stepped, (0, 0, -1))
        self.assertEqual(sorted(round(w.length, 6) for w in wires), [3, 3, 4])
        self.assertEqual(visible_curves(line, stepped, (0, 0, 1)), [])

    def test_silhouette_on_plane(self):
        disc = silhouette_on_plane(Sphere(10), Plane.XY)
        self.assertEqual(len(disc), 1)
        self.assertAlmostEqual(disc[0].area, pi * 100, 3)
        self.assertAlmostEqual(disc[0].center().Z, 0, 6)
        # from either side of the plane
        below = silhouette_on_plane(Pos(0, 0, -30) * Sphere(10), Plane.XY)
        self.assertAlmostEqual(below[0].area, pi * 100, 3)
        self.assertAlmostEqual(below[0].center().Z, 0, 6)
        # a cone side-on: its silhouette lines coincide with its seam
        cone = silhouette_on_plane(Cone(10, 3, 15), Plane.XZ)
        self.assertAlmostEqual(sum(f.area for f in cone), (10 + 3) * 15, 3)
        # several bodies at once
        pillars = Compound([Pos(x, 0, 0) * Box(4, 4, 10) for x in (-7, 0, 7)])
        self.assertEqual(len(silhouette_on_plane(pillars, Plane.XY)), 3)
        # a plane has no silhouette
        self.assertEqual(silhouette_on_plane(Face.make_rect(5, 5), Plane.XY), [])


if __name__ == "__main__":
    unittest.main()
