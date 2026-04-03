"""
build123d imports

name: test_wire.py
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
import random
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
from build123d.topology.shape_core import TOLERANCE

from build123d.build_enums import GeomType, PositionMode, Side
from build123d.build_line import BuildLine
from build123d.geometry import Axis, Color, Location, Plane, Vector
from build123d.objects_curve import Curve, Line, PolarLine, Polyline, Spline
from build123d.objects_sketch import Circle, Rectangle, RegularPolygon
from build123d.operations_generic import fillet
from build123d.topology import Edge, Face, Wire
from OCP.BRepAdaptor import BRepAdaptor_CompCurve
from OCP.gp import gp_Pnt


class TestWire(unittest.TestCase):
    def test_ellipse_arc(self):
        full_ellipse = Wire.make_ellipse(2, 1)
        half_ellipse = Wire.make_ellipse(
            2, 1, start_angle=0, end_angle=180, closed=True
        )
        self.assertAlmostEqual(full_ellipse.area / 2, half_ellipse.area, 5)

    def test_stitch(self):
        half_ellipse1 = Wire.make_ellipse(
            2, 1, start_angle=0, end_angle=180, closed=False
        )
        half_ellipse2 = Wire.make_ellipse(
            2, 1, start_angle=180, end_angle=360, closed=False
        )
        ellipse = half_ellipse1.stitch(half_ellipse2)
        self.assertEqual(len(ellipse.wires()), 1)

    def test_fillet_2d(self):
        square = Wire.make_rect(1, 1)
        squaroid = square.fillet_2d(0.1, square.vertices())
        self.assertAlmostEqual(
            squaroid.length, 4 * (1 - 2 * 0.1) + 2 * math.pi * 0.1, 5
        )
        square.wrapped = None
        with self.assertRaises(ValueError):
            square.fillet_2d(0.1, square.vertices())

    def test_chamfer_2d(self):
        square = Wire.make_rect(1, 1)
        squaroid = square.chamfer_2d(0.1, 0.1, square.vertices())
        self.assertAlmostEqual(
            squaroid.length, 4 * (1 - 2 * 0.1 + 0.1 * math.sqrt(2)), 5
        )
        verts = square.vertices()
        verts[0].wrapped = None
        three_corners = square.chamfer_2d(0.1, 0.1, verts)
        self.assertEqual(len(three_corners.edges()), 7)

        square.wrapped = None
        with self.assertRaises(ValueError):
            square.chamfer_2d(0.1, 0.1, square.vertices())

    def test_close(self):
        t = Polyline((0, 0), (1, 0), (0, 1), close=True)
        self.assertIs(t, t.close())

    def test_chamfer_2d_edge(self):
        square = Wire.make_rect(1, 1)
        edge = square.edges().sort_by(Axis.Y)[0]
        vertex = edge.vertices().sort_by(Axis.X)[0]
        square = square.chamfer_2d(
            distance=0.1, distance2=0.2, vertices=[vertex], edge=edge
        )
        self.assertAlmostEqual(square.edges().sort_by(Axis.Y)[0].length, 0.9)

    def test_make_convex_hull(self):
        # overlapping_edges = [
        #     Edge.make_circle(10, end_angle=60),
        #     Edge.make_circle(10, start_angle=30, end_angle=90),
        #     Edge.make_line((-10, 10), (10, -10)),
        # ]
        # with self.assertRaises(ValueError):
        #     Wire.make_convex_hull(overlapping_edges)

        adjoining_edges = [
            Edge.make_circle(10, end_angle=45),
            Edge.make_circle(10, start_angle=315, end_angle=360),
            Edge.make_line((-10, 10), (-10, -10)),
        ]
        hull_wire = Wire.make_convex_hull(adjoining_edges)
        self.assertAlmostEqual(Face(hull_wire).area, 319.9612, 4)

    def test_fix_degenerate_edges(self):
        e0 = Edge.make_line((0, 0), (1, 0))
        e1 = Edge.make_line((2, 0), (1, 0))

        w = Wire([e0, e1])
        w.wrapped = None
        with self.assertRaises(ValueError):
            w.fix_degenerate_edges(0.1)

    #     # Can't find a way to create one
    #     edge0 = Edge.make_line((0, 0, 0), (1, 0, 0))
    #     edge1 = Edge.make_line(edge0 @ 0, edge0 @ 0 + Vector(0, 1, 0))
    #     edge1a = edge1.trim(0, 1e-7)
    #     edge1b = edge1.trim(1e-7, 1.0)
    #     edge2 = Edge.make_line(edge1 @ 1, edge1 @ 1 + Vector(1, 1, 0))
    #     wire = Wire([edge0, edge1a, edge1b, edge2])
    #     fixed_wire = wire.fix_degenerate_edges(1e-6)
    #     self.assertEqual(len(fixed_wire.edges()), 2)

    def test_trim(self):
        e0 = Edge.make_line((0, 0), (1, 0))
        e1 = Edge.make_line((2, 0), (1, 0))
        e2 = Edge.make_line((2, 0), (3, 0))
        w1 = Wire([e0, e1, e2])
        t1 = w1.trim(0.2, 0.9).move(Location((0, 0.1, 0)))
        self.assertAlmostEqual(t1.length, 2.1, 5)

        e = Edge.make_three_point_arc((0, -20), (5, 0), (0, 20))
        # Three edges are created 0->0.5->0.75->1.0
        o = e.offset_2d(10, side=Side.RIGHT, closed=False)
        t2 = o.trim(0.1, 0.9)
        self.assertAlmostEqual(t2.length, o.length * 0.8, 5)

        t3 = o.trim(0.5, 1.0)
        self.assertAlmostEqual(t3.length, o.length * 0.5, 5)

        t4 = o.trim(0.5, 0.75)
        self.assertAlmostEqual(t4.length, o.length * 0.25, 5)

        w0 = Polyline((0, 0), (0, 1), (1, 1), (1, 0))
        w2 = w0.trim(0, (0.5, 1))
        self.assertAlmostEqual(w2 @ 1, (0.5, 1), 5)

        spline = Spline(
            (0, 0, 0),
            (0, 10, 0),
            tangents=((0, 0, 1), (0, 0, -1)),
            tangent_scalars=(2, 2),
        )
        half = spline.trim(0.5, 1)
        self.assertAlmostEqual(spline @ 0.5, half @ 0, 4)
        self.assertAlmostEqual(spline @ 1, half @ 1, 4)

        w = Rectangle(3, 1).wire()
        t5 = w.trim(0, 0.5)
        self.assertAlmostEqual(t5.length, 4, 5)
        t6 = w.trim(0.5, 1)
        self.assertAlmostEqual(t6.length, 4, 5)

        p = RegularPolygon(10, 20).wire()
        t7 = p.trim(0.1, 0.2)
        self.assertAlmostEqual(p.length * 0.1, t7.length, 5)

        c = Circle(10).wire()
        t8 = c.trim(0.4, 0.9)
        self.assertAlmostEqual(c.length * 0.5, t8.length, 5)

    def test_param_at_point(self):
        e = Edge.make_three_point_arc((0, -20), (5, 0), (0, 20))
        # Three edges are created 0->0.5->0.75->1.0
        o = e.offset_2d(10, side=Side.RIGHT, closed=False)

        e0 = Edge.make_line((0, 0), (1, 0))
        e1 = Edge.make_line((2, 0), (1, 0))
        e2 = Edge.make_line((2, 0), (3, 0))
        w1 = Wire([e0, e1, e2])
        for wire in [o, w1]:
            u_value = random.random()
            position = wire.position_at(u_value)
            self.assertAlmostEqual(wire.param_at_point(position), u_value, 4)

        with self.assertRaises(ValueError):
            o.param_at_point((-1, 1))

        with self.assertRaises(ValueError):
            w1.param_at_point((20, 20, 20))

        w1.wrapped = None
        with self.assertRaises(ValueError):
            w1.param_at_point((0, 0))

    def test_param_at_point_reversed_edges(self):
        with BuildLine(Plane.YZ) as wing_line:
            l1 = Line((0, 65), (80 / 2 + 1.526 * 4, 65))
            PolarLine(
                l1 @ 1, 20.371288916, direction=Vector(0, 1, 0).rotate(Axis.X, -75)
            )
            fillet(wing_line.vertices(), 7)

        w = wing_line.wire()
        params = [w.param_at_point(w @ (i / 20)) for i in range(21)]
        self.assertTrue(params == sorted(params))
        for i, param in enumerate(params):
            self.assertAlmostEqual(param, i / 20, 6)

    def test_tangent_at_reversed_edges(self):
        with BuildLine(Plane.YZ) as wing_line:
            l1 = Line((0, 65), (80 / 2 + 1.526 * 4, 65))
            PolarLine(
                l1 @ 1, 20.371288916, direction=Vector(0, 1, 0).rotate(Axis.X, -75)
            )
            fillet(wing_line.vertices(), 7)

        w = wing_line.wire()
        self.assertAlmostEqual(
            w.tangent_at(0), (0, -0.2588190451025, 0.9659258262891), 6
        )
        self.assertAlmostEqual(w.tangent_at(1), (0, -1, 0), 6)

    def test_order_edges(self):
        w1 = Wire(
            [
                Edge.make_line((0, 0), (1, 0)),
                Edge.make_line((1, 1), (1, 0)),
                Edge.make_line((0, 1), (1, 1)),
            ]
        )
        ordered_edges = w1.order_edges()
        self.assertAlmostEqual(ordered_edges[0] @ 0, (0, 0, 0), 5)
        self.assertAlmostEqual(ordered_edges[1] @ 0, (1, 0, 0), 5)
        self.assertAlmostEqual(ordered_edges[2] @ 0, (1, 1, 0), 5)

    def test_geom_adaptor(self):
        w = Polyline((0, 0), (1, 0), (1, 1))
        self.assertTrue(isinstance(w.geom_adaptor(), BRepAdaptor_CompCurve))
        w.wrapped = None
        with self.assertRaises(ValueError):
            w.geom_adaptor()

    def test_constructor(self):
        e0 = Edge.make_line((0, 0), (1, 0))
        e1 = Edge.make_line((1, 0), (1, 1))
        w0 = Wire.make_circle(1)
        w1 = Wire(e0)
        self.assertTrue(w1.is_valid)
        w2 = Wire([e0])
        self.assertAlmostEqual(w2.length, 1, 5)
        self.assertTrue(w2.is_valid)
        w3 = Wire([e0, e1])
        self.assertTrue(w3.is_valid)
        self.assertAlmostEqual(w3.length, 2, 5)
        w4 = Wire(w0.wrapped)
        self.assertTrue(w4.is_valid)
        w5 = Wire(obj=w0.wrapped)
        self.assertTrue(w5.is_valid)
        w6 = Wire(obj=w0.wrapped, label="w6", color=Color("red"))
        self.assertTrue(w6.is_valid)
        self.assertEqual(w6.label, "w6")
        np.testing.assert_allclose(tuple(w6.color), (1.0, 0.0, 0.0, 1.0), 1e-5)
        w7 = Wire(w6)
        self.assertTrue(w7.is_valid)
        c0 = Polyline((0, 0), (1, 0), (1, 1))
        w8 = Wire(c0)
        self.assertTrue(w8.is_valid)
        w9 = Wire(Curve([e0, e1]))
        self.assertTrue(w9.is_valid)
        with self.assertRaises(ValueError):
            Wire(bob="fred")


class TestWireToBSpline(unittest.TestCase):
    def setUp(self):
        # A simple rectilinear, multi-segment wire:
        # p0 ── p1
        #       │
        #       p2 ── p3
        self.p0 = Vector(0, 0, 0)
        self.p1 = Vector(20, 0, 0)
        self.p2 = Vector(20, 10, 0)
        self.p3 = Vector(35, 10, 0)

        e01 = Edge.make_line(self.p0, self.p1)
        e12 = Edge.make_line(self.p1, self.p2)
        e23 = Edge.make_line(self.p2, self.p3)

        self.wire = Wire([e01, e12, e23])

    def test_to_bspline_basic_properties(self):
        bs = self.wire._to_bspline()

        # 1) Type/geom check
        self.assertIsInstance(bs, Edge)
        self.assertEqual(bs.geom_type, GeomType.BSPLINE)

        # 2) Endpoint preservation
        self.assertLess((Vector(bs.vertices()[0]) - self.p0).length, TOLERANCE)
        self.assertLess((Vector(bs.vertices()[-1]) - self.p3).length, TOLERANCE)

        # 3) Length preservation (within numerical tolerance)
        self.assertAlmostEqual(bs.length, self.wire.length, delta=1e-6)

        # 4) Topology collapse: single edge has only 2 vertices (start/end)
        self.assertEqual(len(bs.vertices()), 2)

        # 5) The composite BSpline should pass through former junctions
        for junction in (self.p1, self.p2):
            self.assertLess(bs.distance_to(junction), 1e-6)

        # 6) Normalized parameter increases along former junctions
        u_p1 = bs.param_at_point(self.p1)
        u_p2 = bs.param_at_point(self.p2)
        self.assertGreater(u_p1, 0.0)
        self.assertLess(u_p2, 1.0)
        self.assertLess(u_p1, u_p2)

        # 7) Re-evaluating at those parameters should be close to the junctions
        self.assertLess((bs.position_at(u_p1) - self.p1).length, 1e-6)
        self.assertLess((bs.position_at(u_p2) - self.p2).length, 1e-6)

        w = self.wire
        w.wrapped = None
        with self.assertRaises(ValueError):
            w._to_bspline()

    def test_to_bspline_orientation(self):
        # Ensure the BSpline follows the wire's topological order
        bs = self.wire._to_bspline()

        # Start ~ p0, end ~ p3
        self.assertLess((bs.position_at(0.0) - self.p0).length, 1e-6)
        self.assertLess((bs.position_at(1.0) - self.p3).length, 1e-6)

        # Parameters at interior points should sit between 0 and 1
        u0 = bs.param_at_point(self.p1)
        u1 = bs.param_at_point(self.p2)
        self.assertTrue(0.0 < u0 < 1.0)
        self.assertTrue(0.0 < u1 < 1.0)


class TestWireParamAtLengthMode(unittest.TestCase):
    """
    Regression test for Issue #1095: PositionMode.LENGTH is incorrect on
    some composite wires due to non-linear distance→parameter mapping.
    """

    def _make_two_arc_wire(self):
        """
        Composite wire from two semicircular arcs with different radii.
        Total length = 3π. The arc-length midpoint (position=0.5) falls
        into the second arc at 25% of its length.

        Expected midpoint:
          (1 - sqrt(2), sqrt(2), 0)
        """
        arc1 = Edge.make_circle(
            1.0, Plane.XY, 0, 180
        )  # center (0,0), from (1,0) to (-1,0)

        # arc2: radius 2, center shifted to (1,0), spans 180° → 360°
        arc2 = Edge.make_circle(2.0, Plane.XY, 180, 360)
        arc2 = arc2.moved(Location(Vector(1, 0, 0)))

        wire = Wire([arc1, arc2])
        return wire

    def test_wire_two_arcs_midpoint(self):
        wire = self._make_two_arc_wire()
        pt = wire.position_at(0.5, position_mode=PositionMode.PARAMETER)

        expected_x = 1.0 - math.sqrt(2)  # ≈ -0.4142
        expected_y = -math.sqrt(2)  # ≈  -1.4142
        expected_z = 0.0

        tol = 1e-4
        self.assertAlmostEqual(pt.X, expected_x, delta=tol)
        self.assertAlmostEqual(pt.Y, expected_y, delta=tol)
        self.assertAlmostEqual(pt.Z, expected_z, delta=tol)


class TestWireParamAtExceptions(unittest.TestCase):
    def test_param_at_raises_when_no_extrema(self):
        wire = Wire([Edge.make_line((0, 0), (1, 0))])

        # Mock Extrema_ExtPC to simulate NbExt() == 0
        mock_extrema = MagicMock()
        mock_extrema.IsDone.return_value = True
        mock_extrema.NbExt.return_value = 0

        with patch("build123d.topology.one_d.Extrema_ExtPC", return_value=mock_extrema):
            with self.assertRaises(RuntimeError) as ctx:
                wire.param_at(0.5)
            self.assertIn("Failed to find point on curve", str(ctx.exception))

    def test_param_at_raises_when_projection_too_far(self):
        wire = Wire([Edge.make_line((0, 0), (1, 0))])

        # Mock Extrema_ExtPC to return a point far from the target
        mock_extrema = MagicMock()
        mock_extrema.IsDone.return_value = True
        mock_extrema.NbExt.return_value = 1

        # Return a point far away and a dummy parameter
        mock_point = MagicMock()
        mock_point.Value.return_value = gp_Pnt(1000, 1000, 0)
        mock_point.Parameter.return_value = 0.123
        mock_extrema.Point.return_value = mock_point
        mock_extrema.SquareDistance.return_value = 1000.0 * 1000.0

        with patch("build123d.topology.one_d.Extrema_ExtPC", return_value=mock_extrema):
            with self.assertRaises(RuntimeError) as ctx:
                wire.param_at(0.5)
            self.assertIn("Failed to find point on curve", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
