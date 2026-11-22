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
from unittest.mock import MagicMock, patch, PropertyMock

from build123d.build_enums import (
    Align,
    AngularDirection,
    Convexity,
    GeomType,
    PositionMode,
    Transition,
)
from build123d.geometry import Axis, Color, Plane, Location, Pos, Rot, Vector
from build123d.objects_curve import CenterArc, EllipticalCenterArc, Line, Spline
from build123d.objects_sketch import Circle, Rectangle, RegularPolygon
from build123d.objects_part import Box, Cylinder
from build123d.operations_generic import sweep
from build123d.operations_generic import fillet
from build123d.operations_part import extrude
from build123d.topology import Curve, Edge, Face, Shell, Wire, Vertex
from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert, BRepBuilderAPI_Sewing


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

        # smoothing needs degree 6 for C2; a lower max_deg is raised to suit
        # rather than failing the approximation
        spline = Edge.make_spline_approx(
            [(i, (i % 3) * 1.5) for i in range(8)],
            smoothing=(1.0, 1.0, 1.0),
            max_deg=3,
        )
        self.assertAlmostEqual(spline.end_point(), (7, 1.5, 0), 5)

    def test_make_bspline(self):
        control_points = [(0, 0), (1, 1), (2, 0)]
        knots = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]

        spline = Edge.make_bspline(control_points, knots, degree=2)
        weighted_spline = Edge.make_bspline(
            control_points, knots, degree=2, weights=[1.0, 2.0, 1.0]
        )

        for edge in [spline, weighted_spline]:
            self.assertEqual(edge.geom_type, GeomType.BSPLINE)
            self.assertAlmostEqual(edge.start_point(), (0, 0, 0), 5)
            self.assertAlmostEqual(edge.end_point(), (2, 0, 0), 5)

        self.assertGreater((weighted_spline @ 0.5).Y, (spline @ 0.5).Y)

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

        spline = Spline([(0, 0), (10, 8), (20, 0), (30, -4)]).edge()
        l7 = spline.trim(0, (20, 0))
        self.assertAlmostEqual(l7 @ 1, (20, 0, 0), 6)

        line.wrapped = None
        with self.assertRaises(ValueError):
            line.trim(0.1, 0.9)

    def test_trim_invalid_parameter(self):
        line = Edge.make_line((-2, 0), (2, 0))
        with self.assertRaisesRegex(TypeError, "start must be a float or VectorLike"):
            line.trim("nowhere", 0.9)
        with self.assertRaisesRegex(TypeError, "end must be a float or VectorLike"):
            line.trim(0.1, object())

    def test_make_spline_failure(self):
        builder = MagicMock()
        builder.IsDone.return_value = False
        with patch(
            "build123d.topology.one_d.GeomAPI_Interpolate", return_value=builder
        ):
            with self.assertRaisesRegex(ValueError, "B-spline interpolation failed"):
                Edge.make_spline([(0, 0), (1, 1), (2, 0)])

    def test_make_spline_approx_failure(self):
        builder = MagicMock()
        builder.IsDone.return_value = False
        with patch(
            "build123d.topology.one_d.GeomAPI_PointsToBSpline", return_value=builder
        ):
            with self.assertRaisesRegex(ValueError, "B-spline approximation failed"):
                Edge.make_spline_approx([(0, 0), (1, 1), (2, 0)])

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

    def test_trim_to_length_reversed_edge(self):
        """A reversed edge is trimmed from its own start, in its own direction"""
        line = Edge.make_line((0, 0, 0), (10, 0, 0)).reversed()
        for start in (0.2, line.position_at(0.2)):
            with self.subTest(start=start):
                trimmed = line.trim_to_length(start, 3)
                self.assertAlmostEqual(trimmed.length, 3, 5)
                self.assertAlmostEqual(trimmed @ 0, (8, 0, 0), 5)
                self.assertAlmostEqual(trimmed @ 1, (5, 0, 0), 5)
                self.assertAlmostEqual(trimmed % 0, (-1, 0, 0), 5)

        arc = Edge.make_circle(10, start_angle=0, end_angle=90).reversed()
        trimmed = arc.trim_to_length(0.25, 5)
        self.assertAlmostEqual(trimmed.length, 5, 5)
        self.assertAlmostEqual(trimmed @ 0, arc.position_at(0.25), 5)
        self.assertAlmostEqual(trimmed % 0, arc.tangent_at(0.25), 5)

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
                self.assertTrue(result.is_empty)  # they don't intersect
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

    def test_mid_way_reversed_edges(self):
        # Issue #1038: the ends are paired by the way each edge runs, whether
        # that comes from how it was built or from a reversed orientation
        first = Edge.make_line((0, 0), (10, 0))
        second = Edge.make_line((1, 5), (9, 5))
        opposite = Edge.make_line((9, 5), (1, 5))
        for name, edges in {
            "same direction": (first, second),
            "built in opposite directions": (first, opposite),
            "second reversed": (first, second.reversed()),
            "second built opposite and reversed": (first, opposite.reversed()),
            "first reversed": (first.reversed(), second),
            "both reversed": (first.reversed(), second.reversed()),
        }.items():
            with self.subTest(name):
                mid = Edge.make_mid_way(*edges)
                self.assertAlmostEqual(mid.length, 9, 5)
                self.assertAlmostEqual(mid.position_at(0.5), (5, 2.5, 0), 5)
                ends = sorted((mid.position_at(0).X, mid.position_at(1).X))
                self.assertAlmostEqual(ends[0], 0.5, 5)
                self.assertAlmostEqual(ends[1], 9.5, 5)

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

    def test_param_at_point_reversed_edge(self):
        # Issue #726: the parameter of a point is the one position_at takes,
        # at the vertices and, without the rounding of the search, between them
        edges = {
            "line": Edge.make_line((0, 0), (10, 20)),
            "arc": Edge.make_three_point_arc((4, 3), (3, 5), (1, 5)),
            "spline": Edge.make_spline([(0, 0), (2, 3), (5, 1), (7, 4)]),
            "ellipse arc": Edge.make_ellipse(5, 2, start_angle=20, end_angle=200),
        }
        for name, forward_edge in edges.items():
            edge = forward_edge.reversed()
            self.assertFalse(edge.is_forward)
            for u_value in (0, 0.123456789, 0.5, 0.8, 1):
                with self.subTest(edge=name, u_value=u_value):
                    point = edge.position_at(u_value)
                    self.assertAlmostEqual(edge.param_at_point(point), u_value, 9)

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

    def test_convexity_of_creases(self):
        box = Box(10, 10, 10)
        self.assertTrue(all(e.convexity == Convexity.CONVEX for e in box.edges()))

        cross = extrude((Rectangle(8, 2) + Rectangle(2, 8)).face(), 2)
        concave = cross.edges().filter_by(Convexity.CONCAVE)
        self.assertEqual(len(concave), 4)
        self.assertTrue(all(e.is_interior for e in concave))
        self.assertEqual(len(cross.edges().filter_by(Convexity.CONVEX)), 32)
        # the re-entrant edges are the vertical ones nearest the axis
        self.assertTrue(
            all(abs(e.center().X) == 1 and abs(e.center().Y) == 1 for e in concave)
        )

    def test_convexity_moved(self):
        # A moved copy of an extracted solid still names the unmoved container as
        # its topo_parent; the faces have to be found by TShape, not Location
        cross = (Rectangle(8, 2) + Rectangle(2, 8)).face()
        moved = Pos(X=10) * extrude(cross, 2).solid()
        inside_edges = moved.edges().filter_by(Edge.is_interior)
        self.assertEqual(len(inside_edges), 4)
        self.assertTrue(all(e.center().X > 5 for e in inside_edges))

    def test_convexity_smooth(self):
        # a fillet meets the faces it blends into without a crease
        rounded = fillet(Box(10, 10, 10).edges(), 2)
        self.assertTrue(all(e.convexity == Convexity.SMOOTH for e in rounded.edges()))
        self.assertFalse(any(e.is_interior for e in rounded.edges()))
        # a seam has the same face on both sides
        seam = Cylinder(3, 5).edges().filter_by(GeomType.LINE)[0]
        self.assertEqual(seam.convexity, Convexity.SMOOTH)
        self.assertEqual(len(Cylinder(3, 5).edges().filter_by(Convexity.CONVEX)), 2)

    def test_convexity_saddle(self):
        # a wall twisting about its shared edge, from going down at one end to
        # going up at the other, is convex there and concave here
        plate = Face.make_rect(20, 5, Plane(origin=(0, -2.5, 0)))
        along = Edge.make_line((-10, 0, 0), (10, 0, 0))
        rim = Edge.make_spline(
            [
                (
                    x,
                    5 * math.cos(math.pi / 2 * x / 10),
                    5 * math.sin(math.pi / 2 * x / 10),
                )
                for x in range(-10, 11, 2)
            ]
        )
        wall = Face.make_surface_from_curves(along, rim)
        sewing = BRepBuilderAPI_Sewing(1e-6)
        sewing.Add(plate.wrapped)
        sewing.Add(wall.wrapped)
        sewing.Perform()
        shell = Shell(sewing.SewedShape())
        shared = [
            e
            for e in shell.edges()
            if e.geom_type == GeomType.LINE and abs(e.center().Y) < 1e-6
        ]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0].convexity, Convexity.SADDLE)

    def test_convexity_errors(self):
        with self.assertRaisesRegex(ValueError, "no valid parent"):
            Edge.make_line((0, 0), (1, 0)).convexity
        with self.assertRaisesRegex(ValueError, "one face only"):
            Face.make_rect(1, 1).edges()[0].is_interior

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

    def test_geom_adaptor(self):
        line = Edge.make_line((0, 0), (1, 0))
        line.wrapped = None
        with self.assertRaises(ValueError):
            line.geom_adaptor()


class TestEdgeToAnalytic(unittest.TestCase):
    """Edge.to_analytic: a BSPLINE that is a line, circle or ellipse becomes one"""

    @staticmethod
    def as_bspline(edge: Edge) -> Edge:
        """The same curve described as a BSPLINE, as the kernel often leaves it"""
        return Edge(BRepBuilderAPI_NurbsConvert(edge.wrapped, True).Shape())

    def assert_same_curve(self, analytic: Edge, edge: Edge, tolerance: float = 1e-9):
        """Same ends, same direction and no point of one off the other"""
        for u in (0, 1):
            self.assertLess((analytic @ u - edge @ u).length, tolerance)
        self.assertGreater((analytic % 0).dot(edge % 0), 0.99)
        for i in range(21):
            point = edge.position_at(i / 20, position_mode=PositionMode.PARAMETER)
            self.assertLess(analytic.distance_to(point), tolerance)

    def test_line(self):
        for edge in (
            self.as_bspline(Edge.make_line((0, 0, 1), (3, 4, 5))),
            Edge.make_spline([(0, 0), (1, 0), (3, 0)]),
            Edge.make_bezier((0, 0), (1, 0), (2, 0)),
        ):
            with self.subTest(geom_type=edge.geom_type):
                analytic = edge.to_analytic()
                self.assertEqual(analytic.geom_type, GeomType.LINE)
                self.assert_same_curve(analytic, edge)

    def test_circular_arc(self):
        # Angles chosen to cross zero, to exceed a half turn and to be short
        for start, end in ((20, 200), (300, 400), (0, 350), (10, 15)):
            arc = (
                Pos(3, 4, 5)
                * Rot(30, 40, 50)
                * Edge.make_circle(5, Plane.XY, start, end)
            )
            for edge in (self.as_bspline(arc), self.as_bspline(arc).reversed()):
                with self.subTest(start=start, end=end, forward=edge.is_forward):
                    analytic = edge.to_analytic()
                    self.assertEqual(analytic.geom_type, GeomType.CIRCLE)
                    self.assertAlmostEqual(analytic.radius, 5, 9)
                    self.assertAlmostEqual(analytic.length, arc.length, 9)
                    self.assert_same_curve(analytic, edge)

    def test_closed(self):
        for closed, geom_type in (
            (Edge.make_circle(5), GeomType.CIRCLE),
            (Edge.make_ellipse(5, 3), GeomType.ELLIPSE),
        ):
            for edge in (self.as_bspline(closed), self.as_bspline(closed).reversed()):
                with self.subTest(geom_type=geom_type, forward=edge.is_forward):
                    analytic = edge.to_analytic()
                    self.assertEqual(analytic.geom_type, geom_type)
                    self.assertTrue(analytic.is_closed)
                    self.assertAlmostEqual(analytic.length, closed.length, 9)
                    self.assert_same_curve(analytic, edge)
                    # A quarter of the way round tells the two directions apart;
                    # the other direction would be a whole diameter away
                    quarter = closed @ (0.25 if edge.is_forward else 0.75)
                    self.assertLess((analytic @ 0.25 - quarter).length, 0.1)

    def test_elliptical_arc(self):
        """Wherever the ellipse lies: the kernel's own recognition finds few that
        are not flat on Plane.XY"""
        tilted = Plane((7, 2, 3)).rotated((30, 40, 50))
        for plane in (Plane.XY, Plane.XZ, tilted):
            for start, end in ((10, 120), (200, 460)):
                arc = Edge.make_ellipse(5, 3, plane, start, end)
                for edge in (self.as_bspline(arc), self.as_bspline(arc).reversed()):
                    with self.subTest(
                        plane=plane, start=start, end=end, forward=edge.is_forward
                    ):
                        analytic = edge.to_analytic()
                        self.assertEqual(analytic.geom_type, GeomType.ELLIPSE)
                        self.assertAlmostEqual(analytic.length, arc.length, 6)
                        self.assert_same_curve(analytic, edge)

    def test_tolerance(self):
        """A spline through points of an arc is an arc only at a loose tolerance"""
        points = [(5 * math.cos(0.2 * i), 5 * math.sin(0.2 * i)) for i in range(8)]
        spline = Edge.make_spline(points)
        self.assertIs(spline.to_analytic(), spline)
        analytic = spline.to_analytic(tolerance=1e-3)
        self.assertEqual(analytic.geom_type, GeomType.CIRCLE)
        self.assert_same_curve(analytic, spline, 1e-3)

        points = [(5 * math.cos(0.2 * i), 3 * math.sin(0.2 * i)) for i in range(12)]
        spline = Edge.make_spline(points)
        self.assertIs(spline.to_analytic(), spline)
        analytic = spline.to_analytic(tolerance=1e-2)
        self.assertEqual(analytic.geom_type, GeomType.ELLIPSE)
        self.assert_same_curve(analytic, spline, 1e-2)

    def test_returned_unchanged(self):
        for edge in (
            Edge.make_spline([(0, 0), (1, 1), (3, 0), (4, 2)]),
            Edge.make_bezier((0, 0), (1, 2), (2, 0)),  # a parabola
            Edge.make_helix(2, 5, 3),  # not planar
            Edge.make_line((0, 0), (1, 1)),
            Edge.make_circle(2),
        ):
            with self.subTest(geom_type=edge.geom_type):
                self.assertIs(edge.to_analytic(), edge)

    def test_attributes_kept(self):
        edge = self.as_bspline(Edge.make_circle(5, Plane.XY, 20, 200))
        edge.label = "arc"
        edge.color = Color("red")
        analytic = edge.to_analytic()
        self.assertEqual(analytic.label, "arc")
        self.assertEqual(analytic.color, Color("red"))

    def test_empty(self):
        with self.assertRaises(ValueError):
            Edge().to_analytic()


class TestEdgeIsSubsetOf(unittest.TestCase):
    """Edge.is_subset_of: does one edge lie entirely on another?"""

    @staticmethod
    def as_bspline(edge: Edge) -> Edge:
        return Edge(BRepBuilderAPI_NurbsConvert(edge.wrapped, True).Shape())

    def check(self, cases):
        for name, (inner, outer, expected) in cases.items():
            with self.subTest(name):
                self.assertEqual(inner.is_subset_of(outer), expected)

    def test_lines(self):
        line = Edge.make_line
        base = line((0, 0), (4, 0))
        self.check(
            {
                "inside": (line((1, 0), (3, 0)), base, True),
                "a copy": (line((0, 0), (4, 0)), base, True),
                "the same edge": (base, base, True),
                "reversed": (line((3, 0), (1, 0)), base, True),
                "sharing an end": (line((2, 0), (4, 0)), base, True),
                "beyond the end": (line((2, 0), (5, 0)), base, False),
                "containing": (line((-1, 0), (5, 0)), base, False),
                "collinear, apart": (line((5, 0), (6, 0)), base, False),
                "parallel": (line((1, 0.1), (3, 0.1)), base, False),
                "crossing": (line((2, -1), (2, 1)), base, False),
                "skew": (line((1, 0, 0), (3, 0, 1)), base, False),
                "a straight spline": (
                    self.as_bspline(line((1, 0), (3, 0))),
                    base,
                    True,
                ),
                "in a straight spline": (
                    line((1, 0), (3, 0)),
                    self.as_bspline(base),
                    True,
                ),
            }
        )

    def test_circular_arcs(self):
        def arc(start, end, radius=5, plane=Plane.XY):
            return Edge.make_circle(radius, plane, start, end)

        quarter, circle = arc(0, 90), Edge.make_circle(5)
        turned = Edge.make_circle(5, Plane.XY.rotated((0, 0, 77)))
        flipped = Edge.make_circle(5, -Plane.XY, -90, 0)  # quarter, other normal
        self.check(
            {
                "inside": (arc(30, 60), quarter, True),
                "a copy": (arc(0, 90), quarter, True),
                "reversed": (arc(30, 60).reversed(), quarter, True),
                "beyond the end": (arc(30, 120), quarter, False),
                "the rest of the circle": (arc(90, 360), quarter, False),
                "in a full circle": (arc(30, 120), circle, True),
                "a full circle in an arc": (circle, arc(0, 350), False),
                "full circles, seams apart": (circle, turned, True),
                "across zero, in one across zero": (arc(350, 370), arc(300, 400), True),
                "across zero, in one that is not": (arc(350, 370), quarter, False),
                "past zero, in one across zero": (arc(10, 20), arc(300, 400), True),
                "before one across zero": (arc(280, 290), arc(300, 400), False),
                "normals opposed": (arc(30, 60), flipped, True),
                "normals opposed, outside": (arc(100, 120), flipped, False),
                "another radius": (arc(30, 60, 4), quarter, False),
                "another circle through the same ends": (
                    Edge.make_three_point_arc(quarter @ 0, (4, 4), quarter @ 1),
                    quarter,
                    False,
                ),
                "starting a hair before": (arc(-1e-9, 30), quarter, True),
                "another centre": (Pos(0.1) * arc(30, 60), quarter, False),
                "another plane": (Rot(X=5) * arc(30, 60), quarter, False),
                "a spline of an arc": (self.as_bspline(arc(30, 60)), quarter, True),
                "in a spline of an arc": (arc(30, 60), self.as_bspline(quarter), True),
                "moved together": (
                    Pos(3, 4, 5) * Rot(30, 40, 50) * arc(30, 60),
                    Pos(3, 4, 5) * Rot(30, 40, 50) * quarter,
                    True,
                ),
            }
        )

    def test_elliptical_arcs(self):
        def arc(start, end, minor=3):
            return Edge.make_ellipse(5, minor, Plane.XZ, start, end)

        quarter = arc(0, 90)
        whole = self.as_bspline(Edge.make_ellipse(5, 3, Plane.XZ))
        self.check(
            {
                "inside": (arc(30, 60), quarter, True),
                "reversed": (arc(30, 60).reversed(), quarter, True),
                "beyond the end": (arc(30, 120), quarter, False),
                "a spline of an arc": (self.as_bspline(arc(30, 60)), quarter, True),
                "in a spline of the ellipse": (arc(30, 60), whole, True),
                "another ellipse": (arc(30, 60, 2.9), quarter, False),
                "a circle": (Edge.make_circle(5, Plane.XZ, 30, 60), quarter, False),
            }
        )

    def test_sampled(self):
        """Pairs that are not both lines or both conics are compared by sampling"""
        points = [(0, 0), (1, 1), (3, 0), (4, 2), (6, 1)]
        spline = Edge.make_spline(points)
        piece = spline.trim(0.2, 0.7)
        quarter = Edge.make_circle(5, Plane.XY, 0, 90)
        helix = Edge.make_helix(2, 5, 3)
        self.check(
            {
                "a piece": (piece, spline, True),
                "a piece reversed": (piece.reversed(), spline, True),
                "a copy": (Edge.make_spline(points), spline, True),
                "the whole in a piece": (spline, piece, False),
                "pieces that overlap": (piece, spline.trim(0.5, 0.9), False),
                "another spline with the same ends": (
                    Edge.make_spline([(0, 0), (1, 1.2), (3, 0), (4, 2), (6, 1)]),
                    spline,
                    False,
                ),
                "a piece of a helix": (helix.trim(0.1, 0.4), helix, True),
                # Both ends of a chord lie on the curve, the rest of it does not
                "a chord of a spline": (
                    Edge.make_line(spline @ 0.2, spline @ 0.3),
                    spline,
                    False,
                ),
                "a chord of an arc": (
                    Edge.make_line(quarter @ 0, quarter @ 1),
                    quarter,
                    False,
                ),
            }
        )

    def test_tolerance(self):
        base = Edge.make_line((0, 0), (4, 0))
        near = Edge.make_line((1, 0.01), (3, 0.01))
        self.assertFalse(near.is_subset_of(base))
        self.assertTrue(near.is_subset_of(base, tolerance=0.02))

        spline = Edge.make_spline([(0, 0), (1, 1), (3, 0), (4, 2), (6, 1)])
        near = Pos(Y=0.001) * spline.trim(0.2, 0.7)
        self.assertFalse(near.is_subset_of(spline))
        self.assertTrue(near.is_subset_of(spline, tolerance=0.01))

    def test_other_bends_where_this_does_not(self):
        """A line through the ends and the middle of a wavy spline: sampling the
        line alone would find it on the spline"""
        wavy = Edge.make_spline([(0, 0), (0.5, 0.05), (1, 0), (1.5, -0.05), (2, 0)])
        line = Edge.make_line((0, 0), (2, 0))
        self.assertFalse(line.is_subset_of(wavy))
        self.assertFalse(line.is_subset_of(wavy, deflection=0.01))

    def test_closed_spline(self):
        points = [(0, 0), (2, 1), (3, 3), (0, 4), (-2, 2)]
        loop = Edge.make_spline(points, periodic=True)
        self.assertTrue(Edge.make_spline(points, periodic=True).is_subset_of(loop))
        self.assertTrue(loop.trim(0.2, 0.5).is_subset_of(loop))
        self.assertFalse(loop.is_subset_of(loop.trim(0.2, 0.5)))

    def test_empty(self):
        with self.assertRaises(ValueError):
            Edge().is_subset_of(Edge.make_line((0, 0), (1, 0)))
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0), (1, 0)).is_subset_of(Edge())


class TestEdgeMerge(unittest.TestCase):
    """Edge.merge: one edge in place of two on the same curve that touch"""

    @staticmethod
    def as_bspline(edge: Edge) -> Edge:
        return Edge(BRepBuilderAPI_NurbsConvert(edge.wrapped, True).Shape())

    def assert_merged(self, first: Edge, second: Edge, expected: Edge):
        """The merge is the expected edge: its kind, where it lies and its direction"""
        merged = first.merge(second)
        self.assertIsNotNone(merged)
        self.assertEqual(merged.geom_type, expected.geom_type)
        self.assertTrue(merged.is_valid)
        self.assertTrue(merged.is_subset_of(expected))
        self.assertTrue(expected.is_subset_of(merged))
        # It runs as the first edge does, where the first edge is
        along = merged.tangent_at(merged.param_at_point(first @ 0.5))
        self.assertGreater(along.dot(first % 0.5), 0.99)
        if not expected.is_closed:
            self.assertLess((merged @ 0 - expected @ 0).length, 1e-6)
            self.assertLess((merged @ 1 - expected @ 1).length, 1e-6)

    def test_lines(self):
        line = Edge.make_line
        base, whole = line((0, 0), (4, 0)), line((0, 0), (6, 0))
        cases = {
            "end to end": (base, line((4, 0), (6, 0)), whole),
            "the other reversed": (base, line((6, 0), (4, 0)), whole),
            "overlapping": (base, line((2, 0), (6, 0)), whole),
            "the other first": (line((4, 0), (6, 0)), base, whole),
            "this one reversed": (
                line((4, 0), (0, 0)),
                line((4, 0), (6, 0)),
                whole.reversed(),
            ),
            "a straight spline": (base, self.as_bspline(line((4, 0), (6, 0))), whole),
        }
        for name, (first, second, expected) in cases.items():
            with self.subTest(name):
                self.assert_merged(first, second, expected)

    def test_circular_arcs(self):
        def arc(start, end, plane=Plane.XY):
            return Edge.make_circle(5, plane, start, end)

        circle = Edge.make_circle(5)
        cases = {
            "end to end": (arc(0, 90), arc(90, 150), arc(0, 150)),
            "the other reversed": (arc(0, 90), arc(90, 150).reversed(), arc(0, 150)),
            "this one reversed": (
                arc(0, 90).reversed(),
                arc(90, 150),
                arc(0, 150).reversed(),
            ),
            "the other first": (arc(90, 150), arc(0, 90), arc(0, 150)),
            "overlapping": (arc(0, 90), arc(60, 150), arc(0, 150)),
            "across zero": (arc(300, 360), arc(0, 40), arc(300, 400)),
            "across zero, the other first": (arc(0, 40), arc(300, 360), arc(300, 400)),
            "one across zero": (arc(330, 390), arc(30, 80), arc(330, 440)),
            "normals opposed": (arc(0, 90), arc(-150, -90, -Plane.XY), arc(0, 150)),
            "a spline of an arc": (
                self.as_bspline(arc(0, 90)),
                arc(90, 150),
                arc(0, 150),
            ),
            "halves of a circle": (arc(0, 180), arc(180, 360), circle),
            "arcs through three points": (
                Edge.make_three_point_arc((5, 0), arc(0, 90) @ 0.5, (0, 5)),
                Edge.make_three_point_arc((0, 5), arc(90, 150) @ 0.5, arc(90, 150) @ 1),
                arc(0, 150),
            ),
            "overlapping round a circle": (arc(0, 200), arc(180, 380), circle),
        }
        for name, (first, second, expected) in cases.items():
            with self.subTest(name):
                self.assert_merged(first, second, expected)

    def test_elliptical_arcs(self):
        def arc(start, end):
            return Edge.make_ellipse(5, 3, Plane.XZ, start, end)

        self.assert_merged(arc(0, 90), arc(90, 150), arc(0, 150))
        self.assert_merged(self.as_bspline(arc(300, 360)), arc(0, 40), arc(300, 400))
        self.assert_merged(
            arc(0, 180), arc(180, 360), Edge.make_ellipse(5, 3, Plane.XZ)
        )

    def test_splines(self):
        spline = Edge.make_spline([(0, 0), (1, 1), (3, 0), (4, 2), (6, 1)])
        whole = spline.trim(0.1, 0.8)
        self.assert_merged(spline.trim(0.1, 0.5), spline.trim(0.5, 0.8), whole)
        self.assert_merged(spline.trim(0.1, 0.6), spline.trim(0.4, 0.8), whole)
        self.assert_merged(
            spline.trim(0.1, 0.5).reversed(), spline.trim(0.5, 0.8), whole.reversed()
        )

        loop = Edge.make_spline(
            [(0, 0), (2, 1), (3, 3), (0, 4), (-2, 2)], periodic=True
        )
        self.assert_merged(
            loop.trim(0.1, 0.5), loop.trim(0.5, 0.8), loop.trim(0.1, 0.8)
        )
        # Pieces either side of where the closed spline starts and ends
        merged = loop.trim(0.7, 1.0).merge(loop.trim(0.0, 0.2))
        self.assertAlmostEqual(merged.length, loop.length / 2, 6)
        self.assertLess((merged @ 0 - loop @ 0.7).length, 1e-6)
        self.assertLess((merged @ 1 - loop @ 0.2).length, 1e-6)

    def test_one_contains_the_other(self):
        """The larger edge is the result, turned round if it runs the other way"""
        base = Edge.make_line((0, 0), (4, 0))
        inside = Edge.make_line((1, 0), (3, 0))
        self.assertIs(base.merge(inside), base)
        self.assertIs(inside.merge(base), base)
        self.assertIs(base.merge(Edge.make_line((0, 0), (4, 0))), base)

        merged = Edge.make_line((3, 0), (1, 0)).merge(base)
        self.assertIsNot(merged, base)
        self.assertLess((merged @ 0 - Vector(4, 0)).length, 1e-6)
        self.assertLess((merged @ 1 - Vector(0, 0)).length, 1e-6)

        circle = Edge.make_circle(5)
        self.assertIs(Edge.make_circle(5, Plane.XY, 30, 60).merge(circle), circle)

    def test_not_merged(self):
        line = Edge.make_line
        base = line((0, 0), (4, 0))
        quarter = Edge.make_circle(5, Plane.XY, 0, 90)
        spline = Edge.make_spline([(0, 0), (1, 1), (3, 0), (4, 2), (6, 1)])
        cases = {
            "collinear lines apart": (base, line((5, 0), (6, 0))),
            "parallel lines": (base, line((0, 1), (4, 1))),
            "lines at a corner": (base, line((4, 0), (4, 2))),
            "lines that cross": (base, line((2, -1), (2, 1))),
            "arcs apart": (quarter, Edge.make_circle(5, Plane.XY, 100, 150)),
            "arcs of circles that touch": (
                quarter,
                Pos(10) * Edge.make_circle(5, Plane.XY, 180, 270),
            ),
            "an arc of a circle and of an ellipse": (
                Edge.make_ellipse(5, 3, Plane.XZ, 0, 90),
                Edge.make_circle(5, Plane.XZ, 90, 150),
            ),
            "spline pieces apart": (spline.trim(0.1, 0.4), spline.trim(0.5, 0.8)),
            # One curve, and they touch, but where it crosses itself
            "pieces of a spline that cross": (
                Edge.make_spline([(0, 0), (4, 4), (0, 4), (4, 0)]).trim(0.1, 0.3),
                Edge.make_spline([(0, 0), (4, 4), (0, 4), (4, 0)]).trim(0.7, 0.9),
            ),
            "a spline and a line leaving it": (
                spline,
                line(spline @ 1, (spline @ 1) + (spline % 1) * 2),
            ),
        }
        for name, (first, second) in cases.items():
            with self.subTest(name):
                self.assertIsNone(first.merge(second))

    def test_tolerance(self):
        base = Edge.make_line((0, 0), (4, 0))
        near = Edge.make_line((4.005, 0), (6, 0))
        self.assertIsNone(base.merge(near))
        merged = base.merge(near, tolerance=0.01)
        self.assertAlmostEqual(merged.length, 6, 5)

    def test_attributes_kept(self):
        arc = Edge.make_circle(5, Plane.XY, 0, 90)
        arc.label = "arc"
        arc.color = Color("red")
        merged = arc.merge(Edge.make_circle(5, Plane.XY, 90, 150))
        self.assertEqual(merged.label, "arc")
        self.assertEqual(merged.color, Color("red"))

    def test_empty(self):
        with self.assertRaises(ValueError):
            Edge().merge(Edge.make_line((0, 0), (1, 0)))
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0), (1, 0)).merge(Edge())


class TestEdgeParamAt(unittest.TestCase):
    """Edge.param_at regression tests (Issue #1095)."""

    def test_param_at_point_normalized_modes_match_and_raw_is_native(self):
        """Check normalized and native parameters on common curve types."""
        edges = {
            "line": Edge.make_line((0, 0, 0), (10, 0, 0)),
            "circle": Edge.make_circle(2),
            "ellipse": Edge.make_ellipse(5, 2, start_angle=30, end_angle=220),
            "spline": Edge.make_spline([(0, 0, 0), (2, 3, 0), (5, 1, 0), (7, 4, 0)]),
        }
        for name, edge in edges.items():
            point = edge.position_at(0.37)
            with self.subTest(edge=name):
                default = edge.param_at_point(point)
                normalized = edge.param_at_point(point, normalize=True)
                native = edge.param_at_point(point, normalize=False)
                evaluated = Vector(edge.geom_adaptor().Value(native))

                self.assertEqual(default, normalized)
                self.assertLess((evaluated - point).length, 1e-6)

    def test_param_at_point_native_endpoints_on_reversed_edges(self):
        """Check native parameters at both endpoints and edge orientations."""
        line = Edge.make_line((0, 0, 0), (10, 0, 0))
        for edge in (line, line.reversed()):
            for point in (edge.start_point(), edge.end_point()):
                with self.subTest(edge_forward=edge.is_forward, point=point):
                    default = edge.param_at_point(point)
                    normalized = edge.param_at_point(point, normalize=True)
                    native = edge.param_at_point(point, normalize=False)

                    self.assertEqual(default, normalized)
                    self.assertLess(
                        (Vector(edge.geom_adaptor().Value(native)) - point).length,
                        1e-6,
                    )

    def test_param_at_point_periodic_endpoint_uses_native_point(self):
        """Check a closed curve endpoint by its evaluated native point."""
        circle = Edge.make_circle(2)
        point = circle.start_point()

        native = circle.param_at_point(point, normalize=False)

        self.assertLess(
            (Vector(circle.geom_adaptor().Value(native)) - point).length, 1e-6
        )

    def test_param_at_point_projected_point_returns_native_parameter(self):
        """Check projection returns the native line parameter."""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        point = Vector(7, 1e-8, 0)

        normalized = edge.param_at_point(point, normalize=True)
        native = edge.param_at_point(point, normalize=False)

        self.assertAlmostEqual(normalized, 0.7, places=6)
        self.assertAlmostEqual(native, 7.0, places=6)
        self.assertLess(
            (Vector(edge.geom_adaptor().Value(native)) - point).length, 1e-6
        )

    def test_param_at_point_fallback_returns_native_parameter_in_both_modes(self):
        """Check fallback conversion after rejecting a plausible bad projection."""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0)).reversed()
        point = edge.position_at(0.7)
        projector = MagicMock()
        projector.LowerDistanceParameter.return_value = 9.0

        with patch(
            "build123d.topology.one_d.GeomAPI_ProjectPointOnCurve",
            return_value=projector,
        ):
            normalized = edge.param_at_point(point, normalize=True)
            native = edge.param_at_point(point, normalize=False)

        self.assertEqual(normalized, 0.7)
        self.assertAlmostEqual(native, 3.0, places=6)
        self.assertLess(
            (Vector(edge.geom_adaptor().Value(native)) - point).length, 1e-6
        )

    def test_param_at_point_normalize_preserves_errors(self):
        """Check empty-edge and off-curve errors in both modes."""
        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        edge.wrapped = None
        for normalize in (True, False):
            with self.subTest(normalize=normalize):
                with self.assertRaisesRegex(
                    ValueError, "Can't find param on empty edge"
                ):
                    edge.param_at_point((0, 0, 0), normalize=normalize)

        edge = Edge.make_line((0, 0, 0), (10, 0, 0))
        for normalize in (True, False):
            with self.subTest(normalize=normalize):
                with self.assertRaisesRegex(ValueError, "is .* from edge"):
                    edge.param_at_point((7, 1, 0), normalize=normalize)

    def test_param_at_point_search_fallback(self):
        """When the OCCT projection returns a bad parameter the minimization
        search takes over and still finds the point."""
        projector = MagicMock()
        projector.LowerDistanceParameter.return_value = 0.0
        edge = Edge.make_line((0, 0), (10, 0))
        with patch(
            "build123d.topology.one_d.GeomAPI_ProjectPointOnCurve",
            return_value=projector,
        ):
            self.assertAlmostEqual(edge.param_at_point((7, 0, 0)), 0.7, 6)

    def test_param_at_point_not_found(self):
        """Neither projection nor search converge."""
        projector = MagicMock()
        projector.LowerDistanceParameter.return_value = 0.0
        result = MagicMock()
        result.fun, result.x = 1e6, 0.0
        edge = Edge.make_line((0, 0), (10, 0))
        with (
            patch(
                "build123d.topology.one_d.GeomAPI_ProjectPointOnCurve",
                return_value=projector,
            ),
            patch("build123d.topology.one_d.minimize_scalar", return_value=result),
        ):
            with self.assertRaisesRegex(RuntimeError, "Edge is too complex"):
                edge.param_at_point((7, 0, 0))

    def test_param_at_reversed_edge(self):
        """param_at measures a reversed edge from its own start, like position_at"""
        for edge in (
            Edge.make_line((0, 0, 0), (10, 0, 0)),
            Edge.make_circle(10, start_angle=0, end_angle=90),
            Edge.make_spline([(0, 0, 0), (2, 3, 0), (5, 1, 0), (7, 4, 0)]),
        ):
            reversed_edge = edge.reversed()
            for position in (0.0, 0.25, 0.7, 1.0):
                with self.subTest(edge=edge.geom_type, position=position):
                    param = reversed_edge.param_at(position)
                    evaluated = Vector(reversed_edge.geom_adaptor().Value(param))
                    self.assertAlmostEqual(
                        evaluated, reversed_edge.position_at(position), 5
                    )
                    self.assertAlmostEqual(
                        param,
                        reversed_edge.param_at_point(
                            reversed_edge.position_at(position), normalize=False
                        ),
                        5,
                    )
        # The oriented ends are the curve's range the other way round
        line = Edge.make_line((0, 0, 0), (10, 0, 0)).reversed()
        self.assertAlmostEqual(line.param_at(0), 10, 5)
        self.assertAlmostEqual(line.param_at(1), 0, 5)

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
