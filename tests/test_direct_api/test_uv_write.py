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

from build123d.build_common import GridLocations
from build123d.build_enums import Align, GeomType
from build123d.geometry import Axis, Location, Matrix, Pos, Rot, Vector
from build123d.objects_curve import Polyline
from build123d.objects_part import Box, Cone, Cylinder, Sphere, Torus
from build123d.objects_sketch import Circle, Polygon, Rectangle, SlotOverall, Text
from build123d.topology import Edge, Face, Shell, Solid, UVFrame, Vertex, Wire
from build123d.topology.uv_write import (
    _affine_map,
    _cone_inverse_map,
    _geodesic_map,
    _sphere_map,
)

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

    def test_iso_curves_are_written_exactly(self):
        """A span along one parameter is the surface's own line or circle,
        not an approximation of it, and its direction is kept"""
        written = self.frame.write_face(Rectangle(4, 6).face())[0]
        self.assertEqual(
            sorted(e.geom_type.name for e in written.edges()),
            ["CIRCLE", "CIRCLE", "LINE", "LINE"],
        )
        self.assertTrue(written.is_valid)
        self.assertAlmostEqual(written.area, 24, 6)
        # a rectangle with a hole keeps its outline exact and its hole approximate
        written = self.frame.write_face((Rectangle(4, 6) - Circle(1)).face())[0]
        self.assertTrue(written.is_valid)
        self.assertEqual(len(written.edges().filter_by(GeomType.BSPLINE)), 1)
        self.assertAlmostEqual(written.area, 24 - math.pi, 6)
        # a sphere's meridians are circles parameterised below zero; a map
        # along the parameter lines puts two on a rectangle across the equator
        sphere = Sphere(5).face()
        frame = UVFrame(sphere, lambda x, y: (x / 5 + 1, y / 5))
        (written,) = frame.write_face(Rectangle(4, 2).face())
        self.assertTrue(written.is_valid)
        self.assertEqual(len(written.edges().filter_by(GeomType.CIRCLE)), 4)

    def test_conics_with_indirect_axes(self):
        """A circle whose own axis system is left-handed, as a slot's end arcs
        are, is mirrored by its image's parameterisation but not in shape"""
        for planar in (
            SlotOverall(12, 4).face(),
            (Rot(Z=30) * SlotOverall(12, 4)).face(),
        ):
            with self.subTest(rotated=planar.center().X != 0):
                for frame in (self.frame, Face.make_rect(50, 50).uv_frame(Location())):
                    written = frame.write_face(planar)
                    self.assertAlmostEqual(sum(f.area for f in written), planar.area, 6)

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

    def assert_runs_past_the_seam(self, face: Face):
        """The face starts inside the surface's own range and runs on past
        the end of it, as the kernel's own faces across a seam do"""
        u_min, u_max, _, _ = face._uv_bounds()
        self.assertGreaterEqual(u_min, -1e-9)
        self.assertLess(u_min, 2 * math.pi)
        self.assertGreater(u_max, 2 * math.pi)

    def test_crossing_the_seam_is_one_face(self):
        """A shape across the seam comes back whole, and survives the
        booleans the kernel does along the seam"""
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        planar = star()
        (written,) = frame.write_face(planar)
        self.assertTrue(written.is_valid)
        self.assertAlmostEqual(written.area, planar.area, 5)
        self.assert_runs_past_the_seam(written)
        # as a tool it fuses into or cuts from the cylinder cleanly
        cylinder = Cylinder(5, 10)
        fused = cylinder.fuse(Solid.thicken(written, 0.5))
        self.assertTrue(fused.is_valid)
        self.assertAlmostEqual(
            fused.volume, cylinder.volume + planar.area * 0.5, delta=0.5
        )
        cut = cylinder.cut(Solid.thicken(written, -0.5))
        self.assertTrue(cut.is_valid)
        self.assertAlmostEqual(
            cut.volume, cylinder.volume - planar.area * 0.5, delta=0.5
        )
        # and on the surface itself it comes out of the face it was written on
        remainder = self.surface.cut(written)
        self.assertTrue(remainder.is_valid)
        self.assertAlmostEqual(
            remainder.area, self.surface.area - planar.area, delta=1e-3
        )
        # as does a smaller one, also across the seam, out of it
        disc = Circle(1).face()
        (small,) = frame.write_face(disc)
        holed = written.cut(small)
        self.assertTrue(holed.is_valid)
        self.assertAlmostEqual(holed.area, (planar - disc).area, delta=1e-3)

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

    def test_barely_crossing_the_seam(self):
        """A curved outline reaching just past the seam, with no vertex near
        its extreme, is still seen to cross it"""
        u0 = self.frame.to_uv(0, 0).X
        per_unit = self.frame.to_uv(1, 0).X - u0
        for poke in (0.05, 0.005):
            with self.subTest(poke=poke):
                x = (2 * math.pi - u0) / per_unit - 3 + poke
                planar = Pos(x, 0) * Rot(Z=11) * Circle(3).face()
                (written,) = self.frame.write_face(planar)
                self.assertTrue(written.is_valid)
                self.assertAlmostEqual(written.area, planar.area, 5)
                self.assert_runs_past_the_seam(written)

    def assert_goes_round(self, written: Face, seam_edges: int = 1):
        """One valid face over the surface's own range, its two sides one
        seam edge used twice"""
        self.assertTrue(written.is_valid)
        seams = [
            edge
            for edge in written.edges()
            if BRep_Tool.IsClosed_s(edge.wrapped, written.wrapped)
        ]
        self.assertEqual(len(seams), seam_edges)
        u_min, u_max, _, _ = written._uv_bounds()
        self.assertAlmostEqual(u_min, 0, 6)
        self.assertAlmostEqual(u_max, 2 * math.pi, 6)

    def test_a_whole_turn_gets_a_seam_edge(self):
        """A band going exactly once round is one face, as the kernel's own
        are, wherever round the cylinder the frame sits, and takes part in
        booleans as a tool and on the surface"""
        cylinder = Cylinder(5, 10)
        turn = 10 * math.pi
        bands = {
            "plain": Rectangle(turn, 2).face(),
            "holes": (
                Rectangle(turn, 4) - GridLocations(8, 0, 3, 1) * Circle(1)
            ).face(),
            # a hole across the line where the band meets itself
            "notched": (
                Rectangle(turn, 4)
                - Pos(turn / 2, 0) * Circle(1)
                - Pos(-turn / 2, 0) * Circle(1)
            ).face(),
        }
        for where in (0.5, 0.2):  # the band's sides on the seam, and away from it
            frame = self.surface.uv_frame(
                self.surface.location_at(where, 0.5, x_dir=(1, 0, 0))
            )
            for name, band in bands.items():
                with self.subTest(where=where, band=name):
                    (written,) = frame.write_face(band)
                    # sides on the seam, the notches cut it in two
                    on_the_seam = where == 0.5 and name == "notched"
                    self.assert_goes_round(written, 2 if on_the_seam else 1)
                    self.assertAlmostEqual(written.area, band.area, 5)
                    raised = cylinder.fuse(Solid.thicken(written, 0.5))
                    self.assertTrue(raised.is_valid)
                    # a layer on a radius 5 cylinder is wider outside than in
                    self.assertAlmostEqual(
                        raised.volume,
                        cylinder.volume + band.area * (5.5**2 - 5**2) / 10,
                        delta=0.01,
                    )
                    sunk = cylinder.cut(Solid.thicken(written, -0.5))
                    self.assertTrue(sunk.is_valid)
                    self.assertAlmostEqual(
                        sunk.volume,
                        cylinder.volume - band.area * (5**2 - 4.5**2) / 10,
                        delta=0.01,
                    )
                    rest = self.surface.cut(written)
                    rest_area = sum(face.area for face in rest.faces())
                    self.assertAlmostEqual(rest_area, self.surface.area - band.area, 4)

    def test_a_whole_turn_keeps_its_curves(self):
        """Moving the band's sides onto the seam cuts its outline there and
        nothing else: a curved edge is still the curve that was drawn"""
        turn = 10 * math.pi
        top = Edge.make_spline(
            [(turn / 2, 2), (turn / 4, 3.5), (0, 1), (-turn / 4, 3.5), (-turn / 2, 2)],
            tangents=[(-1, 0), (-1, 0)],
        )
        band = Face(
            Wire(
                [
                    Edge.make_line((-turn / 2, -2), (turn / 2, -2)),
                    Edge.make_line((turn / 2, -2), (turn / 2, 2)),
                    top,
                    Edge.make_line((-turn / 2, 2), (-turn / 2, -2)),
                ]
            )
        )
        frame = self.surface.uv_frame(
            self.surface.location_at(0.2, 0.5, x_dir=(1, 0, 0))
        )
        (written,) = frame.write_face(band)
        self.assert_goes_round(written)
        pieces = written.edges().filter_by(GeomType.BSPLINE)
        self.assertEqual(len(pieces), 2)  # cut where it crosses the seam
        self.assertAlmostEqual(
            sum(numeric_length(piece) for piece in pieces),
            numeric_length(top),
            delta=1e-4,
        )
        for i in range(21):
            flat = top.position_at(i / 20)
            on_surface = frame._point(frame.to_uv(flat.X, flat.Y))
            exact = Vertex(on_surface).moved(frame._placement)
            self.assertLess(min(piece.distance_to(exact) for piece in pieces), 1e-4)

    def test_a_whole_turn_with_sides_nearly_on_the_seam(self):
        """Sides too near the seam for the strip past it to be cut off are
        taken as on it, in parameter and, on a small cylinder, on the surface;
        a little further off the face is cut as usual"""
        for radius in (0.5, 5, 100):
            surface = Cylinder(radius, 10).faces().filter_by(GeomType.CYLINDER)[0]
            band = Rectangle(
                2 * math.pi * radius, 2, align=(Align.MIN, Align.CENTER)
            ).face()
            for offset in (5e-8, 5e-7, 1.5e-6, 1e-5):
                for past in (offset, -offset):
                    with self.subTest(radius=radius, past=past):
                        to_uv = Matrix(
                            [[1 / radius, 0, 0, past], [0, 1, 0, 5], [0, 0, 1, 0]]
                        )
                        (written,) = UVFrame(surface, to_uv).write_face(band)
                        self.assert_goes_round(written)
                        self.assertAlmostEqual(written.area, band.area, 5)

    def test_a_whole_turn_a_hair_too_wide(self):
        """Sides on the seam and a hair over a period apart: the edges that
        go round are written as whole turns, not wrapped back to the hair"""
        cylinder = Cylinder(5, 10)
        to_uv = Matrix([[1 / 5, 0, 0, 0], [0, 1, 0, 5], [0, 0, 1, 0]])
        for excess in (1e-9, 5e-8):
            width = 5 * (2 * math.pi + excess)
            plain = Rectangle(width, 4, align=(Align.MIN, Align.CENTER))
            notched = plain - Pos(0, 0) * Circle(0.5) - Pos(width, 0) * Circle(0.5)
            for seam_edges, band in ((1, plain.face()), (2, notched.face())):
                with self.subTest(excess=excess, seam_edges=seam_edges):
                    (written,) = UVFrame(self.surface, to_uv).write_face(band)
                    self.assert_goes_round(written, seam_edges)
                    self.assertAlmostEqual(written.area, band.area, 5)
                    sunk = cylinder.cut(Solid.thicken(written, -0.5))
                    self.assertTrue(sunk.is_valid)

    def test_a_whole_turn_with_a_hole_touching_the_seam(self):
        """A hole that touches the seam at a point shares its vertex there
        with the seam edges, whichever side of the seam it is on and
        wherever the band's own sides are; one across the seam parts it"""
        cylinder = Cylinder(5, 10)
        turn = 10 * math.pi
        band = Rectangle(turn, 4, align=(Align.MIN, Align.CENTER))
        seam_x = (2 * math.pi - 1) * 5  # the seam's flat x with the sides at u = 1
        tip = Polygon((0, 0), (1, 1), (2, 0), (1, -1), align=None)
        cases = {
            "disc before the seam": (1.0, band - Pos(seam_x - 1, 0) * Circle(1)),
            "disc beyond the seam": (1.0, band - Pos(seam_x + 1, 0) * Circle(1)),
            "disc across the seam": (1.0, band - Pos(seam_x, 0) * Circle(1)),
            "tip before the seam": (1.0, band - Pos(seam_x - 2, 0) * tip),
            "tip beyond the seam": (1.0, band - Pos(seam_x, 0) * tip),
            "disc at a side on the seam": (0.0, band - Pos(1, 0) * Circle(1)),
            "disc at the other side": (0.0, band - Pos(turn - 1, 0) * Circle(1)),
        }
        for name, (sides, sketch) in cases.items():
            with self.subTest(case=name):
                planar = sketch.face()
                to_uv = Matrix([[1 / 5, 0, 0, sides], [0, 1, 0, 5], [0, 0, 1, 0]])
                (written,) = UVFrame(self.surface, to_uv).write_face(planar)
                self.assert_goes_round(written, 2)  # the seam divided at the touch
                self.assertAlmostEqual(written.area, planar.area, 5)
                sunk = cylinder.cut(Solid.thicken(written, -0.5))
                self.assertTrue(sunk.is_valid)
                self.assertAlmostEqual(
                    sunk.volume,
                    cylinder.volume - planar.area * (5**2 - 4.5**2) / 10,
                    delta=0.01,
                )

    def test_a_whole_turn_on_a_small_cylinder(self):
        """Sides that meet on a small cylinder are further from a period
        apart in parameter than on a large one, and the face is fitted to the
        period, through a map of either kind"""
        cylinder = Cylinder(0.5, 10)
        surface = cylinder.faces().filter_by(GeomType.CYLINDER)[0]
        maps = {
            "matrix": Matrix([[2, 0, 0, 1.0], [0, 1, 0, 5], [0, 0, 1, 0]]),
            "callable": lambda x, y: (2 * x + 1.0, y + 5),
        }
        for excess in (-1e-6, -2e-7, 1e-6):  # under 1e-6 on the surface
            band = Rectangle(
                0.5 * (2 * math.pi + excess), 2, align=(Align.MIN, Align.CENTER)
            ).face()
            for name, to_uv in maps.items():
                with self.subTest(excess=excess, map=name):
                    (written,) = UVFrame(surface, to_uv).write_face(band)
                    self.assert_goes_round(written)
                    self.assertAlmostEqual(written.area, band.area, 5)
                    sunk = cylinder.cut(Solid.thicken(written, -0.05))
                    self.assertTrue(sunk.is_valid)

    def test_a_whole_turn_is_measured_on_the_surface(self):
        """Sides a period apart in parameter, near enough, are too far apart
        on a large cylinder to share vertices, and are not taken as meeting"""
        short = 2 * math.pi - 5e-8

        def written_on(radius: float, turn: float) -> Face:
            surface = Cylinder(radius, 10).faces().filter_by(GeomType.CYLINDER)[0]
            band = Rectangle(radius * turn, 2, align=(Align.MIN, Align.CENTER))
            to_uv = Matrix([[1 / radius, 0, 0, 1.0], [0, 1, 0, 5], [0, 0, 1, 0]])
            (written,) = UVFrame(surface, to_uv).write_face(band.face())
            return written

        for radius, seam_edges in ((5, 1), (100, 0)):
            with self.subTest(radius=radius):
                written = written_on(radius, short)
                self.assertTrue(written.is_valid)
                seams = [
                    edge
                    for edge in written.edges()
                    if BRep_Tool.IsClosed_s(edge.wrapped, written.wrapped)
                ]
                self.assertEqual(len(seams), seam_edges)
        # as much too wide, it overlaps itself
        with self.assertRaisesRegex(ValueError, "whole turn"):
            written_on(100, 2 * math.pi + 5e-8)

    def test_a_whole_turn_whose_sides_do_not_meet(self):
        """A notch in one side only leaves an edge with nothing opposite"""
        turn = 10 * math.pi
        lopsided = (Rectangle(turn, 4) - Pos(turn / 2, 0) * Circle(1)).face()
        with self.assertRaisesRegex(ValueError, "do not meet"):
            self.frame.write_face(lopsided)

    def test_a_period_wide_without_sides_is_not_a_whole_turn(self):
        """A shape a period wide whose sides share no length, or that has
        none along the two lines to share, is written like any other"""
        turn = 10 * math.pi
        shapes = {
            "helical band": Polyline(
                (0, 0), (3, 0), (turn, 4), (turn - 3, 4), close=True
            ),
            "diamond": Polyline(
                (-turn / 2, 0), (0, -2), (turn / 2, 0), (0, 2), close=True
            ),
            # a side along one of the lines only, the tip touching it
            "wedge": Polyline((0, -2), (turn, 0), (0, 2), close=True),
            # sides along both lines, apart and touching at a point
            "apart": Polyline((0, 0), (0, 1), (turn, 3), (turn, 2), close=True),
            "touching": Polyline((0, 0), (0, 1), (turn, 2), (turn, 1), close=True),
        }
        for where in (0.5, 0.2):
            frame = self.surface.uv_frame(
                self.surface.location_at(where, 0.5, x_dir=(1, 0, 0))
            )
            for name, outline in shapes.items():
                with self.subTest(where=where, shape=name):
                    planar = Face(outline)
                    pieces = frame.write_face(planar)
                    self.assertTrue(all(piece.is_valid for piece in pieces))
                    self.assertAlmostEqual(
                        sum(piece.area for piece in pieces), planar.area, 5
                    )

    def test_more_than_a_turn_is_refused(self):
        with self.assertRaisesRegex(ValueError, "whole turn"):
            self.frame.write_face(Rectangle(35, 2).face())  # circumference is 31.4
        # a sheared band that is wider than a turn still overlaps itself
        wide = Face(Polyline((0, 0), (33, 0), (43, 4), (10, 4), close=True))
        with self.assertRaisesRegex(ValueError, "whole turn"):
            self.frame.write_face(wide)

    def test_a_sheared_band_may_span_more_than_a_turn(self):
        """A helical band spans well over a turn in u without overlapping
        itself, so it is cut at every seam it crosses and written whole"""
        band = Face(Polyline((0, 0), (3, 0), (43, 4), (40, 4), close=True))
        pieces = self.frame.write_face(band)
        # 43 units of x is 1.37 turns: from the frame's origin half way round,
        # that crosses the seam once
        self.assertEqual(len(pieces), 2)
        self.assertAlmostEqual(sum(p.area for p in pieces), band.area, 4)
        for piece in pieces:
            self.assertTrue(piece.is_valid)
            u_min, u_max, _, _ = piece._uv_bounds()
            self.assertGreaterEqual(u_min, -1e-9)
            self.assertLessEqual(u_max, 2 * math.pi + 1e-9)
        # the pieces sew into one open shell
        self.assertEqual(len(Shell(pieces).faces()), 2)

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

    def test_punch_beyond_the_seam(self):
        """An outline wholly on the far side of the seam, without crossing
        it, is punched inside the surface's own parameter range"""
        frame = self.surface.uv_frame(
            self.surface.location_at(0.03, 0.5, x_dir=(0, 0, 1))
        )
        for y in (4, -4):  # either side of the seam, around the cylinder
            with self.subTest(y=y):
                ring = Pos(0, y) * (Circle(1) - Circle(0.4)).face()
                punched, island = frame.punch(ring)
                self.assertTrue(punched.is_valid and island.is_valid)
                self.assertAlmostEqual(punched.area, self.surface.area - math.pi, 4)
                self.assertAlmostEqual(island.area, math.pi * 0.4**2, 4)


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
        (written,) = frame.write_face(planar)
        self.assertTrue(written.is_valid)
        self.assertAlmostEqual(written.area, planar.area, 3)
        self.assertGreater(written._uv_bounds()[1], 2 * math.pi)
        self.assertTrue(Solid.thicken(written, 0.3).is_valid)

    def test_a_closed_edge_across_the_seam_is_written_as_two(self):
        """The kernel projects a closed curve that crosses a cone's seam
        onto the cone wrongly, which a boolean between two faces of the cone
        has to do. Written as two edges, a round face or a round hole takes
        part in one correctly; at 135 and 315 degrees one edge does not"""
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        square = Rectangle(4, 4).face().outer_wire()
        for turn in (0, 135, 315):
            with self.subTest(turn=turn):
                round_wire = Rot(Z=turn) * Circle(0.8).face().outer_wire()
                (big,) = frame.write_face(Rot(Z=turn) * Circle(1.0).face())
                (small,) = frame.write_face(Face(round_wire))
                (plate,) = frame.write_face(Face(square, [round_wire]))
                self.assertEqual(len(big.edges()), 2)
                self.assertEqual(len(plate.edges()), 6)
                self.assertTrue(big.is_valid and plate.is_valid)
                self.assertAlmostEqual(big.area, math.pi, 3)
                ring_area, big_area = big.area - small.area, big.area
                self.assertAlmostEqual(big.cut(small).area, ring_area, 3)
                self.assertAlmostEqual(plate.cut(big).area, 16 - big_area, 3)
        # clear of the seam a circle stays one edge, and so it does across
        # the seam of a cylinder, where the kernel has no such trouble
        (clear,) = self.frame.write_face(Circle(1.0).face())
        self.assertEqual(len(clear.edges()), 1)
        cylinder = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        across = cylinder.uv_frame(cylinder.location_at(0.0, 0.5, x_dir=(0, 1, 0)))
        (on_cylinder,) = across.write_face(Circle(1.0).face())
        self.assertEqual(len(on_cylinder.edges()), 1)

    def test_the_whole_face_goes_flat_and_back(self):
        """The cone's own face, unrolled into its sector by the inverse map,
        is written back all the way round as one face with a seam edge"""
        cone = Cone(5, 2, 10)
        for where in (0.5, 0.2):
            with self.subTest(where=where):
                location = self.surface.location_at(where, 0.5, x_dir=(1, 0, 0))
                to_flat = _cone_inverse_map(self.surface, location)
                _, _, v_min, v_max = self.surface._uv_bounds()
                rims = [
                    [to_flat(u, v) for u in (0.0, math.pi, 2 * math.pi)]
                    for v in (v_min, v_max)
                ]
                sector = Face(
                    Wire(
                        [
                            Edge.make_three_point_arc(*rims[0]),
                            Edge.make_line(rims[0][2], rims[1][2]),
                            Edge.make_three_point_arc(*rims[1][::-1]),
                            Edge.make_line(rims[1][0], rims[0][0]),
                        ]
                    )
                )
                self.assertAlmostEqual(sector.area, self.surface.area, 5)
                (written,) = self.surface.uv_frame(location).write_face(sector)
                self.assertTrue(written.is_valid)
                self.assertAlmostEqual(written.area, self.surface.area, 4)
                seams = [
                    edge
                    for edge in written.edges()
                    if BRep_Tool.IsClosed_s(edge.wrapped, written.wrapped)
                ]
                self.assertEqual(len(seams), 1)
                # it covers the cone's face exactly
                self.assertEqual(len(self.surface.cut(written).faces()), 0)
                sunk = cone.cut(Solid.thicken(written, -0.3))
                self.assertTrue(sunk.is_valid)
                self.assertLess(sunk.volume, cone.volume)

    def test_inverse_map_undoes_the_map(self):
        """Widening and narrowing cones, wherever and however the frame sits"""
        for radii in ((5, 2), (2, 5)):
            surface = (
                (Pos(3, -2, 4) * Rot(20, 30, 40) * Cone(*radii, 10))
                .faces()
                .filter_by(GeomType.CONE)[0]
            )
            location = surface.location_at(0.3, 0.6, x_dir=(1, 1, 0))
            frame = surface.uv_frame(location)
            to_flat = _cone_inverse_map(surface, location)
            for x, y in ((0, 0), (2, 1), (-3, 2), (1.5, -2.5)):
                with self.subTest(radii=radii, flat=(x, y)):
                    u, v = frame.mapping(x, y)
                    back = to_flat(u, v)
                    self.assertAlmostEqual(back[0], x, 9)
                    self.assertAlmostEqual(back[1], y, 9)

    def test_inverse_map_lays_the_rim_on_an_arc(self):
        """A circle about the axis unrolls to an arc of its own length about
        the image of the apex"""
        location = self.surface.location_at(0.5, 0.5, x_dir=(1, 0, 0))
        to_flat = _cone_inverse_map(self.surface, location)
        slant = math.hypot(10, 5 - 2)
        v_apex = 2 * slant / (5 - 2) + slant  # past the narrow rim, from the wide one
        apex = Vector(*to_flat(0.0, v_apex))
        rim = [Vector(*to_flat(u, 0.0)) for u in (0.0, 1.0, 2.0)]
        distance = 5 * slant / (5 - 2)  # the wide rim's distance from the apex
        for point in rim:
            self.assertAlmostEqual((point - apex).length, distance, 9)
        # one radian of the rim is its radius long, and so is its arc
        turned = (rim[0] - apex).get_angle(rim[1] - apex)
        self.assertAlmostEqual(math.radians(turned) * distance, 5, 9)


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

    def test_crossing_the_seam(self):
        """The seam is met in parameter space, so it works the same on a
        sphere as on a cylinder although the seam's flat pre-image is curved"""
        frame = self.surface.uv_frame(
            self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0))
        )
        planar = Rectangle(4, 2).face()
        (written,) = frame.write_face(planar)
        self.assertTrue(written.is_valid)
        u_min, u_max, _, _ = written._uv_bounds()
        self.assertGreaterEqual(u_min, -1e-9)
        self.assertGreater(u_max, 2 * math.pi)
        self.assertTrue(Solid.thicken(written, 0.3).is_valid)

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
        geodesic = _geodesic_map(sphere, location, 1e-4)
        closed_form = _sphere_map(sphere, location)
        cylinder = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        location = cylinder.location_at(0.3, 0.6, x_dir=(0, 0, 1))
        unrolled = _geodesic_map(cylinder, location, 1e-4)
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

    def test_across_a_torus_seam(self):
        torus = Torus(10, 3).face()
        frame = torus.uv_frame(torus.location_at(0.0, 0.5, x_dir=(0, 0, 1)))
        (written,) = frame.write_face(Rectangle(4, 2).face())
        self.assertTrue(written.is_valid)
        u_min, u_max, _, _ = written._uv_bounds()
        self.assertGreaterEqual(u_min, -1e-9)
        self.assertGreater(u_max, 2 * math.pi)

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
        at_pole = _geodesic_map(
            sphere, sphere.location_at(0.5, 1.0, x_dir=(1, 0, 0)), 1e-4
        )
        with self.assertRaisesRegex(ValueError, "pole"):
            at_pole(1.0, 0.0)
        # a geodesic from the equator straight up runs into the pole
        from_equator = _geodesic_map(
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
        # an interpolated image that cannot be brought within the tolerance
        sphere = Sphere(5).face()
        frame = sphere.uv_frame(sphere.location_at(0.3, 0.6), tolerance=1e-15)
        with self.assertRaisesRegex(ValueError, "over the tolerance"):
            frame.write_edge(Edge.make_circle(2))

    def test_any_map_can_cross_the_seam(self):
        """Seams are met in parameter space, so a bare callable takes part"""
        surface = Cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        on_the_seam = UVFrame(surface, lambda x, y: (0.2 * x, y + 5))
        (written,) = on_the_seam.write_face((Pos(2, 0) * Rectangle(2, 2)).face())
        self.assertTrue(written.is_valid)
        (across,) = on_the_seam.write_face(Rectangle(4, 2).face())
        self.assertTrue(across.is_valid)
        u_min, u_max, _, _ = across._uv_bounds()
        self.assertGreaterEqual(u_min, -1e-9)
        self.assertGreater(u_max, 2 * math.pi)

    def test_whole_turns_on_a_sphere_and_a_torus(self):
        """Round a sphere's equator, and round a torus either way: the seam
        edge runs along whichever parameter the shape goes round"""
        ball = Sphere(5)
        equator = Rectangle(10 * math.pi, 3, align=(Align.MIN, Align.CENTER)).face()
        cases = [(ball, lambda x, y: (x / 5 + 1.0, y / 5), equator, 0.5)]
        ring = Torus(10, 3)
        long_way = Rectangle(26 * math.pi, 3, align=(Align.MIN, Align.CENTER)).face()
        short_way = Rectangle(4, 6 * math.pi, align=(Align.CENTER, Align.MIN)).face()
        cases += [
            (ring, lambda x, y: (x / 13 + 0.7, y / 3 + 2.0), long_way, 0.3),
            (ring, lambda x, y: (x / 13 + 2.0, y / 3 + 0.7), short_way, 0.3),
        ]
        for index, (solid, mapping, planar, depth) in enumerate(cases):
            with self.subTest(case=index):
                surface = solid.faces()[0]
                (written,) = UVFrame(surface, mapping).write_face(planar)
                self.assertTrue(written.is_valid)
                seams = [
                    edge
                    for edge in written.edges()
                    if BRep_Tool.IsClosed_s(edge.wrapped, written.wrapped)
                ]
                self.assertEqual(len(seams), 1)
                sunk = solid.cut(Solid.thicken(written, -depth))
                self.assertTrue(sunk.is_valid)
                self.assertAlmostEqual(
                    sunk.volume, solid.volume - written.area * depth, delta=8
                )
        # round the long way and across the seam the other way is not written
        across = UVFrame(ring.faces()[0], lambda x, y: (x / 13 + 0.7, y / 3))
        with self.assertRaisesRegex(ValueError, "across its seam the other"):
            across.write_face(long_way)

    def test_a_torus_map_of_ones_own_crosses_both_seams(self):
        """A surface periodic in both directions can be crossed in both at
        once, and the face still thickens

        The thickened face is not cut into the torus here: on Intel macOS
        the kernel crashes in that boolean.
        """
        torus = Torus(10, 3).face()
        # parameter lines as flat axes, scaled by the radii at the origin;
        # the origin sits on both seams so the shape straddles both
        by_hand = UVFrame(torus, lambda x, y: (x / 13, y / 3))
        (written,) = by_hand.write_face(Rectangle(4, 2).face())
        self.assertTrue(written.is_valid)
        u_min, u_max, v_min, v_max = written._uv_bounds()
        self.assertGreaterEqual(min(u_min, v_min), -1e-9)
        self.assertGreater(min(u_max, v_max), 2 * math.pi)
        sunk = Solid.thicken(written, -0.5)
        self.assertTrue(sunk.is_valid)
        self.assertAlmostEqual(sunk.volume, written.area * 0.5, delta=0.5)


if __name__ == "__main__":
    unittest.main()
