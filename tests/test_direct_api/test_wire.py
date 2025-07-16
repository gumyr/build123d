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

import numpy as np
from build123d.build_enums import Side
from build123d.geometry import Axis, Color, Location
from build123d.objects_curve import Polyline, Spline
from build123d.objects_sketch import Circle, Rectangle, RegularPolygon
from build123d.topology import Edge, Face, Wire


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

    def test_chamfer_2d(self):
        square = Wire.make_rect(1, 1)
        squaroid = square.chamfer_2d(0.1, 0.1, square.vertices())
        self.assertAlmostEqual(
            squaroid.length, 4 * (1 - 2 * 0.1 + 0.1 * math.sqrt(2)), 5
        )

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

    # def test_fix_degenerate_edges(self):
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

        with self.assertRaises(ValueError):
            o.trim(0.75, 0.25)
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
        with self.assertRaises(ValueError):
            Wire(bob="fred")


if __name__ == "__main__":
    unittest.main()
