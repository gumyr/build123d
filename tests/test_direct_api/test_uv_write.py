"""
build123d imports

name: test_uv_write.py
by:   Gumyr
date: September 19, 2026

desc:
    Tests for UVFrame: writing planar shapes into a face's parameter space.

license:

    Copyright 2026 Gumyr

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
import unittest

from build123d.build_enums import Align, GeomType
from build123d.geometry import Axis, Matrix, Pos, Vector
from build123d.objects_part import Box, Cone, Cylinder, Sphere, Torus
from build123d.objects_sketch import Circle, Polygon, Rectangle, Text
from build123d.topology import Edge, Face, Solid, UVFrame, Wire
from build123d.topology.uv_write import _affine_map, _GeodesicMap, _sphere_map

from OCP.BRep import BRep_Tool
from OCP.Geom2d import Geom2d_BSplineCurve, Geom2d_Ellipse, Geom2d_Line


def numeric_length(shape, samples: int = 2000) -> float:
    """Arc length by dense sampling, independent of GProp"""
    points = [shape.position_at(i / samples) for i in range(samples + 1)]
    return sum((b - a).length for a, b in zip(points, points[1:]))


def surface_gap(shape, surface: Face, samples: int = 100) -> float:
    """Largest distance from sampled points of the shape's edges to the surface"""
    return max(
        surface.distance_to(edge.position_at(i / samples))
        for edge in shape.edges()
        for i in range(samples + 1)
    )


def star() -> Face:
    """A ten-pointed outline with a hole, the shape the wrap tests use"""
    points = [
        (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
        for i in range(10)
        for r, a in [((1, 3)[i % 2], -18 + 36 * i)]
    ]
    return (Polygon(*points, align=Align.NONE) - Circle(0.5)).face()


class TestCylinderFrame(unittest.TestCase):
    """A cylinder's map is the isometry that unrolls it: everything is exact"""

    def setUp(self):
        self.surface = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        self.frame = self.surface.uv_frame(
            self.surface.location_at(0.5, 0.5, x_dir=(1, 0, 0))
        )

    def test_map_is_the_unrolling(self):
        self.assertIsInstance(self.frame.mapping, Matrix)
        # one unit of flat x is 1/radius of u; flat y is v
        step = self.frame.to_uv(1, 2) - self.frame.to_uv(0, 0)
        self.assertAlmostEqual(abs(step.X), 1 / 5, 9)
        self.assertAlmostEqual(abs(step.Y), 2, 9)

    def test_curve_images_stay_analytic(self):
        line = Edge.make_line((0, 0), (3, 3))
        circle = Circle(1).edge().moved(Pos(1, 2))
        ellipse = Edge.make_ellipse(2, 1, start_angle=30, end_angle=300)
        spline = Edge.make_spline([(0, 0), (1, 1), (2, -1), (3, 0)])

        # the written edge's pcurve on the surface is the image
        def pcurve(edge):
            written = self.frame.write_edge(edge)
            first, last = BRep_Tool.Range_s(written.wrapped)
            return BRep_Tool.CurveOnSurface_s(
                written.wrapped, self.surface.wrapped, first, last
            )

        self.assertIsInstance(pcurve(line), Geom2d_Line)
        self.assertIsInstance(pcurve(circle), Geom2d_Ellipse)
        self.assertIsInstance(pcurve(ellipse), Geom2d_Ellipse)
        self.assertIsInstance(pcurve(spline), Geom2d_BSplineCurve)

    def test_edges_keep_their_length_and_lie_on_the_surface(self):
        for name, edge in (
            ("line", Edge.make_line((0, 0), (3, 3))),
            ("circle", Circle(1).edge().moved(Pos(1, 2))),
            ("arc", Edge.make_three_point_arc((0, 0), (1, 1), (2, 0))),
            ("ellipse", Edge.make_ellipse(2, 1, start_angle=30, end_angle=300)),
            ("spline", Edge.make_spline([(0, 0), (1, 1), (2, -1), (3, 0)])),
        ):
            with self.subTest(edge=name):
                written = self.frame.write_edge(edge)
                self.assertTrue(written.is_valid)
                self.assertAlmostEqual(
                    numeric_length(written), numeric_length(edge), delta=1e-4
                )
                self.assertLess(surface_gap(written, self.surface), 1e-5)

    def test_closed_wire_closes_exactly(self):
        outline = star().outer_wire()
        written = self.frame.write_wire(outline)
        self.assertTrue(written.is_valid)
        self.assertTrue(written.is_closed)
        self.assertAlmostEqual(
            numeric_length(written), numeric_length(outline), delta=1e-4
        )
        self.assertAlmostEqual(
            (written.position_at(0) - written.position_at(1)).length, 0, 9
        )

    def test_face_with_hole_keeps_its_area_and_normal(self):
        planar = star()
        (written,) = self.frame.write_face(planar)
        self.assertTrue(written.is_valid)
        self.assertEqual(len(written.wires()), 2)
        self.assertAlmostEqual(written.area, planar.area, 5)
        centre = written.center()
        self.assertGreater(
            written.normal_at(centre).dot(self.surface.normal_at(centre)), 0.999
        )

    def test_text_faces_are_oriented_correctly(self):
        for planar in Text("ab", 4).faces():
            (written,) = self.frame.write_face(planar)
            self.assertTrue(written.is_valid)
            self.assertAlmostEqual(written.area, planar.area, 5)
            self.assertGreater(written.area, 0)

    def test_frame_may_run_along_the_axis(self):
        frame = self.surface.uv_frame(
            self.surface.location_at(0.5, 0.5, x_dir=(0, 0, 1))
        )
        planar = Rectangle(6, 2).face()
        (written,) = frame.write_face(planar)
        self.assertTrue(written.is_valid)
        self.assertAlmostEqual(written.area, planar.area, 5)
        # the long side now runs along z
        size = written.bounding_box().size
        self.assertAlmostEqual(size.Z, 6, 5)

    def test_crossing_the_seam_splits_the_face(self):
        """A shape across the seam comes back in one piece per period, each
        inside the surface's own parameter range, and the pieces survive the
        booleans the kernel does along the seam"""
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        planar = star()
        pieces = frame.write_face(planar)
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(piece.is_valid for piece in pieces))
        self.assertAlmostEqual(sum(piece.area for piece in pieces), planar.area, 5)
        for piece in pieces:
            u_min, u_max, _, _ = piece._uv_bounds()
            self.assertGreaterEqual(u_min, -1e-9)
            self.assertLessEqual(u_max, 2 * math.pi + 1e-9)
        # thickened pieces meet along the seam; joined first they make one
        # tool that fuses into or cuts from the cylinder cleanly
        cylinder = Cylinder(5, 10)
        raised = [Solid.thicken(piece, 0.5) for piece in pieces]
        fused = cylinder.fuse(raised[0].fuse(raised[1]))
        self.assertTrue(fused.is_valid)
        self.assertAlmostEqual(
            fused.volume, cylinder.volume + planar.area * 0.5, delta=0.5
        )
        sunk = [Solid.thicken(piece, -0.5) for piece in pieces]
        cut = cylinder.cut(sunk[0].fuse(sunk[1]))
        self.assertTrue(cut.is_valid)
        self.assertAlmostEqual(
            cut.volume, cylinder.volume - planar.area * 0.5, delta=0.5
        )

    def test_crossing_the_seam_cuts_a_wire(self):
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        outline = Rectangle(8, 3).face().outer_wire()
        written = frame.write_wire(outline)
        self.assertTrue(written.is_valid)
        self.assertTrue(written.is_closed)
        # the two long sides are cut where they cross the seam
        self.assertEqual(len(written.edges()), 6)
        self.assertAlmostEqual(
            numeric_length(written), numeric_length(outline), delta=1e-4
        )

    def test_a_full_turn_is_refused(self):
        with self.assertRaisesRegex(ValueError, "whole turn"):
            self.frame.write_face(Rectangle(35, 2).face())  # circumference is 31.4

    def test_punch_across_the_seam_is_refused(self):
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        with self.assertRaisesRegex(ValueError, "seam"):
            frame.punch(Circle(1.5).face())

    def test_most_of_the_way_round(self):
        planar = (Rectangle(25, 4) - Circle(1)).face()  # 80% of the circumference
        (written,) = self.frame.write_face(planar)
        self.assertTrue(written.is_valid)
        self.assertAlmostEqual(written.area, planar.area, 5)

    def test_written_faces_work_in_booleans(self):
        cylinder = Cylinder(5, 10)
        letters = [self.frame.write_face(f)[0] for f in Text("Hi", 4).faces()]
        raised = [Solid.thicken(f, 0.5) for f in letters]
        embossed = cylinder.fuse(*raised)
        self.assertTrue(embossed.is_valid)
        self.assertGreater(embossed.volume, cylinder.volume)
        sunk = [Solid.thicken(f, -0.5) for f in letters]
        engraved = cylinder.cut(*sunk)
        self.assertTrue(engraved.is_valid)
        self.assertLess(engraved.volume, cylinder.volume)

    def test_punch(self):
        disc = Circle(1.5).face()
        (punched,) = self.frame.punch(disc)
        self.assertTrue(punched.is_valid)
        self.assertEqual(len(punched.wires()), 2)
        self.assertAlmostEqual(punched.area, self.surface.area - disc.area, 4)

        ring = (Circle(1.5) - Circle(0.5)).face()
        punched, island = self.frame.punch(ring)
        self.assertTrue(punched.is_valid and island.is_valid)
        self.assertAlmostEqual(punched.area, self.surface.area - math.pi * 1.5**2, 4)
        self.assertAlmostEqual(island.area, math.pi * 0.5**2, 4)


class TestPlaneFrame(unittest.TestCase):
    def test_plane_is_rigid(self):
        surface = Box(10, 10, 2).faces().sort_by(Axis.Z)[-1]
        frame = surface.uv_frame(surface.location_at(0.5, 0.5, x_dir=(1, 0, 0)))
        planar = star()
        (written,) = frame.write_face(planar)
        self.assertTrue(written.is_valid)
        self.assertTrue(written.is_planar)
        self.assertAlmostEqual(written.area, planar.area, 6)
        self.assertAlmostEqual(written.center().Z, 1, 6)


class TestConeFrame(unittest.TestCase):
    """A cone unrolls exactly, through a non-affine map"""

    def setUp(self):
        self.surface = Cone(5, 2, 10).faces().filter_by(GeomType.CONE)[0]
        self.frame = self.surface.uv_frame(
            self.surface.location_at(0.5, 0.5, x_dir=(1, 0, 0))
        )

    def test_map_is_a_callable(self):
        self.assertNotIsInstance(self.frame.mapping, Matrix)
        self.assertTrue(callable(self.frame.mapping))

    def test_lengths_and_area_are_kept(self):
        line = Edge.make_line((0, 0), (3, 3))
        written = self.frame.write_edge(line)
        self.assertAlmostEqual(
            numeric_length(written), numeric_length(line), delta=1e-4
        )
        self.assertLess(surface_gap(written, self.surface), 1e-4)

        planar = star()
        (written_face,) = self.frame.write_face(planar)
        self.assertTrue(written_face.is_valid)
        self.assertAlmostEqual(written_face.area, planar.area, delta=1e-3)

    def test_closed_wire_closes(self):
        written = self.frame.write_wire(star().outer_wire())
        self.assertTrue(written.is_closed)
        self.assertAlmostEqual(
            (written.position_at(0) - written.position_at(1)).length, 0, 9
        )

    def test_crossing_the_seam(self):
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        planar = Rectangle(6, 2).face()
        pieces = frame.write_face(planar)
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(piece.is_valid for piece in pieces))
        self.assertAlmostEqual(sum(piece.area for piece in pieces), planar.area, 3)


class TestSphereFrame(unittest.TestCase):
    """Azimuthal equidistant: rays from the origin are exact, rings shrink"""

    def setUp(self):
        self.surface = Sphere(5).face()
        self.frame = self.surface.uv_frame(
            self.surface.location_at(0.5, 0.5, x_dir=(1, 0, 0))
        )

    def test_rays_are_exact_and_rings_shrink(self):
        ray = Edge.make_line((0, 0), (4, 0))
        self.assertAlmostEqual(numeric_length(self.frame.write_edge(ray)), 4, 4)
        ring = Circle(4).edge()
        expected = 2 * math.pi * 5 * math.sin(4 / 5)
        self.assertAlmostEqual(numeric_length(self.frame.write_edge(ring)), expected, 3)

    def test_face_is_valid_and_on_the_surface(self):
        (written,) = self.frame.write_face(star())
        self.assertTrue(written.is_valid)
        self.assertLess(surface_gap(written, self.surface), 1e-4)

    def test_crossing_the_seam_splits_along_the_meridian(self):
        """The split is done in parameter space, so it works the same on a
        sphere as on a cylinder although the seam's flat pre-image is curved"""
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        planar = Rectangle(4, 2).face()
        pieces = frame.write_face(planar)
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(piece.is_valid for piece in pieces))
        for piece in pieces:
            u_min, u_max, _, _ = piece._uv_bounds()
            self.assertGreaterEqual(u_min, -1e-9)
            self.assertLessEqual(u_max, 2 * math.pi + 1e-9)
        self.assertTrue(all(Solid.thicken(piece, 0.3).is_valid for piece in pieces))

    def test_covering_a_pole_is_refused(self):
        frame = self.surface.uv_frame(
            self.surface.location_at(0.5, 0.5, x_dir=(1, 0, 0))
        )
        # a quarter of the great circle from the equator reaches the pole
        with self.assertRaisesRegex(ValueError, "pole"):
            frame.write_face(Rectangle(4, 2 * 5 * math.pi / 2 + 2).face())
        # a ring around the pole likewise
        with self.assertRaisesRegex(ValueError, "pole"):
            frame.write_face((Pos(0, 5 * math.pi / 2) * (Circle(3) - Circle(1))).face())
        # and stopping short of the pole is fine
        (written,) = frame.write_face(Rectangle(4, 2 * 5 * math.pi / 2 - 1).face())
        self.assertTrue(written.is_valid)


class TestGeodesicFrame(unittest.TestCase):
    """The exponential map, integrated along geodesics, for the surfaces
    with no closed form"""

    @staticmethod
    def wavy() -> Face:
        points = [
            [(i * 4, j * 4, 2 * math.sin(i) * math.cos(j)) for j in range(6)]
            for i in range(6)
        ]
        return Face.make_surface_from_array_of_points(points)

    def test_agrees_with_the_closed_forms(self):
        """On a sphere it is the azimuthal equidistant projection, on a
        cylinder the unrolling"""
        sphere = Sphere(5).face()
        location = sphere.location_at(0.3, 0.6, x_dir=(1, 0, 0))
        geodesic = _GeodesicMap(sphere, location, 1e-4)
        closed_form = _sphere_map(sphere, location)
        cylinder = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        location = cylinder.location_at(0.3, 0.6, x_dir=(0, 0, 1))
        unrolled = _GeodesicMap(cylinder, location, 1e-4)
        affine = _affine_map(cylinder, location)
        for x, y in [(1, 0), (0, 1), (-2, 1.5), (3, -3), (0.1, 4)]:
            with self.subTest(x=x, y=y):
                self.assertAlmostEqual(geodesic(x, y)[0], closed_form(x, y)[0], 6)
                self.assertAlmostEqual(geodesic(x, y)[1], closed_form(x, y)[1], 6)
                image = affine.multiply(Vector(x, y, 0))
                self.assertAlmostEqual(unrolled(x, y)[0], image.X, 9)
                self.assertAlmostEqual(unrolled(x, y)[1], image.Y, 9)

    def test_torus(self):
        torus = Torus(10, 3).face()
        frame = torus.uv_frame(torus.location_at(0.5, 0.5, x_dir=(0, 0, 1)))
        ray = frame.write_edge(Edge.make_line((0, 0), (4, 0)))
        self.assertAlmostEqual(numeric_length(ray), 4, 5)
        self.assertLess(surface_gap(ray, torus), 1e-4)
        outline = Rectangle(3, 2).face().outer_wire()
        written = frame.write_wire(outline)
        self.assertTrue(written.is_closed)
        (face,) = frame.write_face(star())
        self.assertTrue(face.is_valid)
        self.assertLess(surface_gap(face, torus), 1e-4)
        self.assertTrue(Solid.thicken(face, 0.3).is_valid)

    def test_torus_seams_split_the_shape(self):
        torus = Torus(10, 3).face()
        frame = torus.uv_frame(torus.location_at(0.0, 0.5, x_dir=(0, 0, 1)))
        pieces = frame.write_face(Rectangle(4, 2).face())
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(piece.is_valid for piece in pieces))
        for piece in pieces:
            u_min, u_max, _, _ = piece._uv_bounds()
            self.assertGreaterEqual(u_min, -1e-9)
            self.assertLessEqual(u_max, 2 * math.pi + 1e-9)

    def test_free_form_surface(self):
        surface = self.wavy()
        self.assertEqual(surface.geom_type, GeomType.BSPLINE)
        frame = surface.uv_frame(surface.location_at(0.5, 0.5, x_dir=(1, 0, 0)))
        (face,) = frame.write_face(star())
        self.assertTrue(face.is_valid)
        self.assertLess(surface_gap(face, surface), 1e-4)
        self.assertTrue(Solid.thicken(face, 0.5).is_valid)
        # rays from the origin keep their length
        ray = frame.write_edge(Edge.make_line((0, 0), (0, 3)))
        self.assertAlmostEqual(numeric_length(ray), 3, 4)

    def test_poles_are_refused(self):
        sphere = Sphere(5).face()
        at_pole = _GeodesicMap(
            sphere, sphere.location_at(0.5, 1.0, x_dir=(1, 0, 0)), 1e-4
        )
        with self.assertRaisesRegex(ValueError, "pole"):
            at_pole(1.0, 0.0)
        # a geodesic from the equator straight up runs into the pole
        from_equator = _GeodesicMap(
            sphere, sphere.location_at(0.5, 0.5, x_dir=(1, 0, 0)), 1e-4
        )
        with self.assertRaisesRegex(ValueError, "pole"):
            from_equator(0.0, 5 * math.pi / 2)


class TestFrameConstruction(unittest.TestCase):
    def test_at_and_uv_frame_agree(self):
        surface = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        location = surface.location_at(0.3, 0.7, x_dir=(1, 0, 0))
        direct = UVFrame.at(surface, location)
        method = surface.uv_frame(location)
        self.assertLess((direct.to_uv(1, 1) - method.to_uv(1, 1)).length, 1e-9)

    def test_a_map_of_ones_own(self):
        """The constructor takes any map; here the cylinder's, written by hand"""
        surface = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        by_hand = UVFrame(
            surface, Matrix([[0.2, 0, 0, math.pi], [0, 1, 0, 5], [0, 0, 1, 0]])
        )
        planar = Rectangle(4, 2).face()
        (written,) = by_hand.write_face(planar)
        self.assertTrue(written.is_valid)
        self.assertAlmostEqual(written.area, planar.area, 5)
        # and a callable, the same map spelled out
        as_callable = UVFrame(surface, lambda x, y: (0.2 * x + math.pi, y + 5))
        (written,) = as_callable.write_face(planar)
        self.assertAlmostEqual(written.area, planar.area, 3)

    def test_refusals(self):
        surface = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        with self.assertRaisesRegex(ValueError, "tolerance"):
            UVFrame(surface, Matrix(), tolerance=0)

    def test_any_map_can_cross_the_seam(self):
        """Seams are split in parameter space, so a bare callable takes part"""
        surface = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        on_the_seam = UVFrame(surface, lambda x, y: (0.2 * x, y + 5))
        (written,) = on_the_seam.write_face((Pos(2, 0) * Rectangle(2, 2)).face())
        self.assertTrue(written.is_valid)
        pieces = on_the_seam.write_face(Rectangle(4, 2).face())
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(piece.is_valid for piece in pieces))
        for piece in pieces:
            u_min, u_max, _, _ = piece._uv_bounds()
            self.assertGreaterEqual(u_min, -1e-9)
            self.assertLessEqual(u_max, 2 * math.pi + 1e-9)

    def test_a_torus_map_of_ones_own_splits_both_seams(self):
        """A surface periodic in both directions is cut along both seams"""
        torus = Torus(10, 3).face()
        # parameter lines as flat axes, scaled by the radii at the origin;
        # the origin sits on both seams so the shape straddles both
        by_hand = UVFrame(torus, lambda x, y: (x / 13, y / 3))
        pieces = by_hand.write_face(Rectangle(4, 2).face())
        self.assertEqual(len(pieces), 4)
        self.assertTrue(all(piece.is_valid for piece in pieces))
        for piece in pieces:
            u_min, u_max, v_min, v_max = piece._uv_bounds()
            self.assertGreaterEqual(min(u_min, v_min), -1e-9)
            self.assertLessEqual(max(u_max, v_max), 2 * math.pi + 1e-9)


if __name__ == "__main__":
    unittest.main()
