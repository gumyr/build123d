"""
build123d imports

name: test_edge.py
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
import numpy as np
import unittest

from itertools import product
from unittest.mock import patch, PropertyMock

from build123d.build_enums import (
    Align,
    AngularDirection,
    GeomType,
    PositionMode,
    Transition,
)
from build123d.geometry import Axis, Plane, Location, Vector
from build123d.objects_curve import CenterArc, EllipticalCenterArc, Line
from build123d.objects_sketch import Circle, Rectangle, RegularPolygon
from build123d.objects_part import Box
from build123d.operations_generic import sweep
from build123d.topology import Curve, Edge, Face, Wire, Vertex
from OCP.GeomProjLib import GeomProjLib


class TestEdge(unittest.TestCase):
    def test_close(self):
        self.assertAlmostEqual(
            Edge.make_circle(1, end_angle=180).close().length, math.pi + 2, 5
        )
        self.assertAlmostEqual(Edge.make_circle(1).close().length, 2 * math.pi, 5)

    def test_make_half_circle(self):
        half_circle = Edge.make_circle(radius=1, start_angle=0, end_angle=180)
        self.assertAlmostEqual(half_circle.start_point(), (1, 0, 0), 3)
        self.assertAlmostEqual(half_circle.end_point(), (-1, 0, 0), 3)

    def test_make_half_circle2(self):
        half_circle = Edge.make_circle(radius=1, start_angle=270, end_angle=90)
        self.assertAlmostEqual(half_circle.start_point(), (0, -1, 0), 3)
        self.assertAlmostEqual(half_circle.end_point(), (0, 1, 0), 3)

    def test_make_clockwise_half_circle(self):
        half_circle = Edge.make_circle(
            radius=1,
            start_angle=180,
            end_angle=0,
            angular_direction=AngularDirection.CLOCKWISE,
        )
        self.assertAlmostEqual(half_circle.end_point(), (1, 0, 0), 3)
        self.assertAlmostEqual(half_circle.start_point(), (-1, 0, 0), 3)

    def test_make_clockwise_half_circle2(self):
        half_circle = Edge.make_circle(
            radius=1,
            start_angle=90,
            end_angle=-90,
            angular_direction=AngularDirection.CLOCKWISE,
        )
        self.assertAlmostEqual(half_circle.start_point(), (0, 1, 0), 3)
        self.assertAlmostEqual(half_circle.end_point(), (0, -1, 0), 3)

    def test_arc_center(self):
        self.assertAlmostEqual(Edge.make_ellipse(2, 1).arc_center, (0, 0, 0), 5)
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0, 0), (0, 0, 1)).arc_center

    def test_spline_with_parameters(self):
        spline = Edge.make_spline(
            points=[(0, 0, 0), (1, 1, 0), (2, 0, 0)], parameters=[0.0, 0.4, 1.0]
        )
        self.assertAlmostEqual(spline.end_point(), (2, 0, 0), 5)
        with self.assertRaises(ValueError):
            Edge.make_spline(
                points=[(0, 0, 0), (1, 1, 0), (2, 0, 0)], parameters=[0.0, 1.0]
            )
        with self.assertRaises(ValueError):
            Edge.make_spline(
                points=[(0, 0, 0), (1, 1, 0), (2, 0, 0)], tangents=[(1, 1, 0)]
            )

    def test_spline_approx(self):
        spline = Edge.make_spline_approx([(0, 0), (1, 1), (2, 1), (3, 0)])
        self.assertAlmostEqual(spline.end_point(), (3, 0, 0), 5)
        spline = Edge.make_spline_approx(
            [(0, 0), (1, 1), (2, 1), (3, 0)], smoothing=(1.0, 5.0, 10.0)
        )
        self.assertAlmostEqual(spline.end_point(), (3, 0, 0), 5)

    def test_distribute_locations(self):
        line = Edge.make_line((0, 0, 0), (10, 0, 0))
        locs = line.distribute_locations(3)
        for i, x in enumerate([0, 5, 10]):
            self.assertAlmostEqual(locs[i].position, (x, 0, 0), 5)
        self.assertAlmostEqual(locs[0].orientation, (0, 90, 180), 5)

        locs = line.distribute_locations(3, positions_only=True)
        for i, x in enumerate([0, 5, 10]):
            self.assertAlmostEqual(locs[i].position, (x, 0, 0), 5)
        self.assertAlmostEqual(locs[0].orientation, (0, 0, 0), 5)

    def test_to_wire(self):
        edge = Edge.make_line((0, 0, 0), (1, 1, 1))
        for end in [0, 1]:
            self.assertAlmostEqual(
                edge.position_at(end),
                Wire(edge).position_at(end),
                5,
            )

    def test_arc_center2(self):
        edges = [
            Edge.make_circle(1, plane=Plane((1, 2, 3)), end_angle=30),
            Edge.make_ellipse(1, 0.5, plane=Plane((1, 2, 3)), end_angle=30),
        ]
        for edge in edges:
            self.assertAlmostEqual(edge.arc_center, (1, 2, 3), 5)
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0), (1, 1)).arc_center

    def test_find_intersection_points(self):
        circle = Edge.make_circle(1)
        line = Edge.make_line((0, -2), (0, 2))
        crosses = circle.find_intersection_points(line)
        for target, actual in zip([(0, 1, 0), (0, -1, 0)], crosses):
            self.assertAlmostEqual(actual, target, 5)

        with self.assertRaises(ValueError):
            circle.find_intersection_points(Edge.make_line((0, 0, -1), (0, 0, 1)))
        with self.assertRaises(ValueError):
            circle.find_intersection_points(Edge.make_line((0, 0, -1), (0, 0, 1)))

        self_intersect = Edge.make_spline([(-3, 2), (3, -2), (4, 0), (3, 2), (-3, -2)])
        self.assertAlmostEqual(
            self_intersect.find_intersection_points()[0],
            (-2.6861636507066047, 0, 0),
            5,
        )
        line = Edge.make_line((1, -2), (1, 2))
        crosses = line.find_intersection_points(Axis.X)
        self.assertAlmostEqual(crosses[0], (1, 0, 0), 5)

        with self.assertRaises(ValueError):
            line.find_intersection_points(Plane.YZ)

        circle.wrapped = None
        with self.assertRaises(ValueError):
            circle.find_intersection_points(line)

    # def test_intersections_tolerance(self):

    # Multiple operands not currently supported

    # r1 = ShapeList() + (PolarLocations(1, 4) * Edge.make_line((0, -1), (0, 1)))
    # l1 = Edge.make_line((1, 0), (2, 0))
    # i1 = l1.intersect(*r1)

    # r2 = Rectangle(2, 2).edges()
    # l2 = Pos(1) * Edge.make_line((0, 0), (1, 0))
    # i2 = l2.intersect(*r2)

    # self.assertEqual(len(i1.vertices()), len(i2.vertices()))

    def test_trim(self):
        line = Edge.make_line((-2, 0), (2, 0))
        self.assertAlmostEqual(line.trim(0.25, 0.75).position_at(0), (-1, 0, 0), 5)
        self.assertAlmostEqual(line.trim(0.25, 0.75).position_at(1), (1, 0, 0), 5)

        l1 = CenterArc((0, 0), 1, 0, 180)
        l2 = l1.trim(0, l1 @ 0.5)
        self.assertAlmostEqual(l2 @ 0, (1, 0, 0), 5)
        self.assertAlmostEqual(l2 @ 1, (0, 1, 0), 5)

        l3 = l1.trim((1, 0), (0, 1))
        self.assertAlmostEqual(l3 @ 0, (1, 0, 0), 5)
        self.assertAlmostEqual(l3 @ 1, (0, 1, 0), 5)

        l4 = l1.trim(0.5, (-1, 0))
        self.assertAlmostEqual(l4 @ 0, (0, 1, 0), 5)
        self.assertAlmostEqual(l4 @ 1, (-1, 0, 0), 5)

        l5 = l1.trim(0.5, Vertex(-1, 0))
        self.assertAlmostEqual(l5 @ 0, (0, 1, 0), 5)
        self.assertAlmostEqual(l5 @ 1, (-1, 0, 0), 5)

        line.wrapped = None
        with self.assertRaises(ValueError):
            line.trim(0.1, 0.9)

    def test_trim_to_length(self):

        e1 = Edge.make_line((0, 0), (10, 10))
        e1_trim = e1.trim_to_length(0.0, 10)
        self.assertAlmostEqual(e1_trim.length, 10, 5)

        e2 = Edge.make_circle(10, start_angle=0, end_angle=90)
        e2_trim = e2.trim_to_length(0.5, 1)
        self.assertAlmostEqual(e2_trim.length, 1, 5)
        self.assertAlmostEqual(
            e2_trim.position_at(0), Vector(10, 0, 0).rotate(Axis.Z, 45), 5
        )

        e3 = Edge.make_spline(
            [(0, 10, 0), (-4, 5, 2), (0, 0, 0)], tangents=[(-1, 0), (1, 0)]
        )
        e3_trim = e3.trim_to_length(0, 7)
        self.assertAlmostEqual(e3_trim.length, 7, 5)

        a4 = Axis((0, 0, 0), (1, 1, 1))
        e4_trim = Edge(a4).trim_to_length(0.5, 2)
        self.assertAlmostEqual(e4_trim.length, 2, 5)

        e5 = e1.trim_to_length((5, 5), 1)
        self.assertAlmostEqual(e5 @ 0, (5, 5), 5)
        self.assertAlmostEqual(e5.length, 1, 5)

        e1.wrapped = None
        with self.assertRaises(ValueError):
            e1.trim_to_length(0.1, 2)

    def test_trim_to_other(self):
        """Test trimming open and closed edges to all other objects"""

        base_edges = [
            CenterArc((0, 0), 1, 0, 180),
            CenterArc((0, 0), 1, 0, 360),
        ]
        others = [
            Line((0, 0), (1, 1)),
            CenterArc((0, 0), 1, 45, 90),
            Rectangle(1, 1, align=(Align.MAX, Align.MIN)).rotate(Axis.Z, -45).wire(),
            Rectangle(1, 1, align=(Align.MAX, Align.MIN)).rotate(Axis.Z, -45),
            Curve(
                Rectangle(1, 1, align=(Align.MAX, Align.MIN))
                .rotate(Axis.Z, -45)
                .edges()
            ),
            Box(1, 1, 1, align=(Align.MAX, Align.MIN, Align.CENTER)).rotate(
                Axis.Z, -45
            ),
            Axis((0, 0, 0), (1, 1, 0)),
            Location((math.sqrt(2) / 2, math.sqrt(2) / 2), (0, 0, 1)),
            Plane((0, 0, 0), (1, 1, 0), (-1, 1, 0)),
            Vector(1, 0).rotate(Axis.Z, 45),
            (math.sqrt(2) / 2, math.sqrt(2) / 2),
            (0, 2),
        ]
        for base, other in product(base_edges, others):
            result = base.trim_to_other(other)
            if other == others[-1]:
                self.assertIsNone(result)
            else:
                self.assertAlmostEqual(result.length, math.pi / 4, 5)

    def test_bezier(self):
        with self.assertRaises(ValueError):
            Edge.make_bezier((1, 1))
        cntl_pnts = [(1, 2, 3)] * 30
        with self.assertRaises(ValueError):
            Edge.make_bezier(*cntl_pnts)
        with self.assertRaises(ValueError):
            Edge.make_bezier((0, 0, 0), (1, 1, 1), weights=[1.0])

        bezier = Edge.make_bezier((0, 0), (0, 1), (1, 1), (1, 0))
        bbox = bezier.bounding_box()
        self.assertAlmostEqual(bbox.min, (0, 0, 0), 5)
        self.assertAlmostEqual(bbox.max, (1, 0.75, 0), 5)

    def test_mid_way(self):
        mid = Edge.make_mid_way(
            Edge.make_line((0, 0), (0, 1)), Edge.make_line((1, 0), (1, 1)), 0.25
        )
        self.assertAlmostEqual(mid.position_at(0), (0.25, 0, 0), 5)
        self.assertAlmostEqual(mid.position_at(1), (0.25, 1, 0), 5)

    def test_distribute_locations2(self):
        with self.assertRaises(ValueError):
            Edge.make_circle(1).distribute_locations(1)

        locs = Edge.make_circle(1).distribute_locations(5, positions_only=True)
        for i, loc in enumerate(locs):
            self.assertAlmostEqual(
                loc.position,
                Vector(1, 0, 0).rotate(Axis.Z, i * 90),
                5,
            )
            self.assertAlmostEqual(loc.orientation, (0, 0, 0), 5)

    def test_find_tangent(self):
        circle = Edge.make_circle(1)
        parm = circle.find_tangent(135)[0]
        self.assertAlmostEqual(
            circle @ parm, (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 5
        )
        line = Edge.make_line((0, 0), (1, 1))
        parm = line.find_tangent(45)[0]
        self.assertAlmostEqual(parm, 0, 5)
        parm = line.find_tangent(0)
        self.assertEqual(len(parm), 0)

    def test_param_at_point(self):
        u = Edge.make_circle(1).param_at_point((0, 1))
        self.assertAlmostEqual(u, 0.25, 5)

        u = 0.3
        edge = Edge.make_line((0, 0), (34, 56))
        pnt = edge.position_at(u)
        self.assertAlmostEqual(edge.param_at_point(pnt), u, 5)

        ca = CenterArc((0, 0), 1, -200, 220).edge()
        for u in [0.3, 1.0]:
            pnt = ca.position_at(u)
            self.assertAlmostEqual(ca.param_at_point(pnt), u, 5)

        ea = EllipticalCenterArc((15, 0), 10, 5, start_angle=90, arc_size=180).edge()
        for u in [0.3, 0.9]:
            pnt = ea.position_at(u)
            self.assertAlmostEqual(ea.param_at_point(pnt), u, 5)

        with self.assertRaises(ValueError):
            edge.param_at_point((-1, 1))

        ea.wrapped = None
        with self.assertRaises(ValueError):
            ea.param_at_point((15, 5))

    def test_param_at_point_bspline(self):
        # Define a complex spline with inflections and non-monotonic behavior
        curve = Edge.make_spline(
            [
                (-2, 0, 0),
                (-10, 1, 0),
                (0, 0, 0),
                (1, -2, 0),
                (2, 0, 0),
                (1, 1, 0),
            ]
        )

        # Sample N points along the curve using position_at and check that
        # param_at_point returns approximately the same param (inverted)
        N = 20
        for u in np.linspace(0.0, 1.0, N):
            p = curve.position_at(u)
            u_back = curve.param_at_point(p)
            self.assertAlmostEqual(u, u_back, delta=1e-6, msg=f"u={u}, u_back={u_back}")

    def test_conical_helix(self):
        helix = Edge.make_helix(1, 4, 1, normal=(-1, 0, 0), angle=10, lefthand=True)
        self.assertAlmostEqual(helix.bounding_box().min.X, -4, 5)

    def test_reverse(self):
        e1 = Edge.make_line((0, 0), (1, 1))
        self.assertAlmostEqual(e1 @ 0.1, (0.1, 0.1, 0), 5)
        self.assertAlmostEqual(e1.reversed() @ 0.1, (0.9, 0.9, 0), 5)

        e2 = Edge.make_circle(1, start_angle=0, end_angle=180)
        e2r = e2.reversed()
        self.assertAlmostEqual((e2 @ 0.1).X, -(e2r @ 0.1).X, 5)

        e2r = e2.reversed(reconstruct=True)
        self.assertAlmostEqual((e2 @ 0.1).X, -(e2r @ 0.1).X, 5)

        e2.wrapped = None
        with self.assertRaises(ValueError):
            e2.reversed()

    def test_init(self):
        with self.assertRaises(TypeError):
            Edge(direction=(1, 0, 0))

    def test_is_interior(self):
        path = RegularPolygon(5, 5).face().outer_wire()
        profile = path.location_at(0) * (Circle(0.6) & Rectangle(2, 1))
        target = sweep(profile, path, transition=Transition.RIGHT)
        inside_edges = target.edges().filter_by(lambda e: e.is_interior)
        self.assertEqual(len(inside_edges), 5)
        self.assertTrue(all(e.geom_type == GeomType.ELLIPSE for e in inside_edges))

    def test_position_at(self):
        line = Edge.make_line((1, 1), (2, 2))
        self.assertEqual(line @ 0, Vector(1, 1, 0))
        self.assertEqual(line @ 1, Vector(2, 2, 0))
        self.assertEqual(line.reversed() @ 0, Vector(2, 2, 0))
        self.assertEqual(line.reversed() @ 1, Vector(1, 1, 0))

        self.assertEqual(
            line.position_at(1, position_mode=PositionMode.LENGTH),
            Vector(1, 1) + Vector(math.sqrt(2) / 2, math.sqrt(2) / 2),
        )
        self.assertEqual(
            line.reversed().position_at(1, position_mode=PositionMode.LENGTH),
            Vector(2, 2) - Vector(math.sqrt(2) / 2, math.sqrt(2) / 2),
        )

    def test_tangent_at(self):
        arc = Edge.make_circle(1, start_angle=0, end_angle=180)
        self.assertEqual(arc % 0, Vector(0, 1, 0))
        self.assertEqual(arc % 1, Vector(0, -1, 0))
        self.assertEqual(arc.reversed() % 0, Vector(0, 1, 0))
        self.assertEqual(arc.reversed() % 1, Vector(0, -1, 0))
        self.assertEqual(arc.reversed() @ 0, Vector(-1, 0, 0))
        self.assertEqual(arc.reversed() @ 1, Vector(1, 0, 0))

        self.assertEqual(
            arc.tangent_at(math.pi, position_mode=PositionMode.LENGTH), Vector(0, -1, 0)
        )
        self.assertEqual(
            arc.reversed().tangent_at(math.pi / 2, position_mode=PositionMode.LENGTH),
            Vector(1, 0, 0),
        )

    def test_location_at(self):
        arc = Edge.make_circle(1, start_angle=0, end_angle=180)
        self.assertEqual(arc.location_at(0).position, Vector(1, 0, 0))
        self.assertEqual(arc.location_at(1).position, Vector(-1, 0, 0))
        self.assertEqual(arc.location_at(0).z_axis.direction, Vector(0, 1, 0))
        self.assertEqual(arc.location_at(1).z_axis.direction, Vector(0, -1, 0))

        self.assertEqual(arc.reversed().location_at(0).position, Vector(-1, 0, 0))
        self.assertEqual(arc.reversed().location_at(1).position, Vector(1, 0, 0))
        self.assertEqual(
            arc.reversed().location_at(0).z_axis.direction, Vector(0, 1, 0)
        )
        self.assertEqual(
            arc.reversed().location_at(1).z_axis.direction, Vector(0, -1, 0)
        )

        self.assertEqual(
            arc.location_at(math.pi, position_mode=PositionMode.LENGTH).position,
            Vector(-1, 0, 0),
        )
        self.assertEqual(
            arc.reversed()
            .location_at(math.pi, position_mode=PositionMode.LENGTH)
            .position,
            Vector(1, 0, 0),
        )

    def test_extend_spline(self):
        geom_surface = Face.make_rect(4, 4).geom_adaptor()
        with self.assertRaises(TypeError):
            Edge.make_line((0, 0), (1, 0))._extend_spline(True, geom_surface)
        spline = Edge.make_spline([(0, 0), (1,), (2, 0)])
        spline.wrapped = None
        with self.assertRaises(ValueError):
            spline._extend_spline(True, geom_surface)

    @patch.object(GeomProjLib, "Project_s", return_value=None)
    def test_extend_spline_failed_snap(self, mock_is_valid):
        geom_surface = Face.make_rect(4, 4).geom_adaptor()
        spline = Edge.make_spline([(0, 0), (1, 0), (2, 0)])
        with self.assertRaises(RuntimeError):
            spline._extend_spline(True, geom_surface)

    def test_geom_adaptor(self):
        line = Edge.make_line((0, 0), (1, 0))
        line.wrapped = None
        with self.assertRaises(ValueError):
            line.geom_adaptor()


class TestEdgeParamAt(unittest.TestCase):
    """Edge.param_at regression tests (Issue #1095)."""

    def test_param_at_line_midpoint(self):
        """
        On a straight line, arc length is linear in parameter.
        param_at(0.5) should correspond to the geometric midpoint.
        """
        edge = Edge.make_line(Vector(0, 0, 0), Vector(4, 0, 0))
        u = edge.param_at(0.5)
        mid = Vector(edge.geom_adaptor().Value(u))
        self.assertAlmostEqual(mid.X, 2.0, places=6)
        self.assertAlmostEqual(mid.Y, 0.0, places=6)
        self.assertAlmostEqual(mid.Z, 0.0, places=6)

    def test_param_at_arc_quarter_point(self):
        """
        Unit semicircle (0° → 180°). Arc-length quarter point is at 45°.
        """
        edge = Edge.make_circle(1.0, Plane.XY, 0, 180)
        u = edge.param_at(0.25)
        pt = Vector(edge.geom_adaptor().Value(u))
        expected_x = math.cos(math.radians(45))
        expected_y = math.sin(math.radians(45))
        self.assertAlmostEqual(pt.X, expected_x, places=5)
        self.assertAlmostEqual(pt.Y, expected_y, places=5)

    def test_param_at_ellipse_is_not_linear_in_parameter(self):
        """
        On an ellipse, a naive linear parameter map does NOT follow arc length.
        This test verifies param_at uses arc-length based mapping.
        """
        edge = Edge.make_ellipse(4.0, 2.0, Plane.XY, 0, 180)
        # Arc-length quarter point (0.25 of length)
        u_len = edge.param_at(0.25)
        pt_len = Vector(edge.geom_adaptor().Value(u_len))

        # Naive "parameter space" quarter (just interpolate between start/end)
        # Equivalent to assuming parameter == normalized length.
        u_naive = edge.geom_adaptor().FirstParameter() + 0.25 * (
            edge.geom_adaptor().LastParameter() - edge.geom_adaptor().FirstParameter()
        )
        pt_naive = Vector(edge.geom_adaptor().Value(u_naive))

        # These should differ measurably on an ellipse.
        self.assertGreater(
            (pt_len - pt_naive).length,
            1e-3,
            msg="Ellipse arc-length mapping appears linear in parameter (unexpected).",
        )

    def test_param_at_arc_endpoints_are_exact(self):
        """param_at(0.0) and param_at(1.0) must map to arc start/end."""
        edge = Edge.make_circle(3.0, Plane.XY, 30, 150)

        u0 = edge.param_at(0.0)
        u1 = edge.param_at(1.0)
        p0 = Vector(edge.geom_adaptor().Value(u0))
        p1 = Vector(edge.geom_adaptor().Value(u1))

        expected_start = Vector(
            3.0 * math.cos(math.radians(30)),
            3.0 * math.sin(math.radians(30)),
            0.0,
        )
        expected_end = Vector(
            3.0 * math.cos(math.radians(150)),
            3.0 * math.sin(math.radians(150)),
            0.0,
        )

        self.assertAlmostEqual(p0.X, expected_start.X, places=5)
        self.assertAlmostEqual(p0.Y, expected_start.Y, places=5)
        self.assertAlmostEqual(p1.X, expected_end.X, places=5)
        self.assertAlmostEqual(p1.Y, expected_end.Y, places=5)


if __name__ == "__main__":
    unittest.main()
