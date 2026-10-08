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

import io
import math
import os
import random
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
from build123d.topology.shape_core import TOLERANCE
import build123d.topology.one_d as one_d

from build123d.build_enums import GeomType, PositionMode, Side
from build123d.build_line import BuildLine
from build123d.geometry import Axis, Color, Location, Plane, Pos, Rot, Vector
from build123d.objects_curve import Curve, Line, JernArc, PolarLine, Polyline, Spline
from build123d.objects_sketch import Circle, Rectangle, RectangleRounded, RegularPolygon
from build123d.operations_generic import fillet
from build123d.exporters3d import export_brep, export_step
from build123d.importers import import_step
from build123d.topology import Compound, Edge, Face, Solid, Vertex, Wire
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_CompCurve
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_EmptyWire,
    BRepBuilderAPI_NonManifoldWire,
)
from OCP.gp import gp_Pnt
from OCP.TopoDS import TopoDS


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
        straight_wire = Wire(
            [
                Edge.make_line((0, 0), (1, 0)),
                Edge.make_line((1, 0), (2, 0)),
            ]
        )
        straight_vertex = straight_wire.vertices().sort_by_distance((1, 0, 0))[0]
        unmodified_wire = straight_wire.fillet_2d(0.1, [straight_vertex])
        self.assertAlmostEqual(unmodified_wire.length, straight_wire.length, 5)
        self.assertEqual(len(unmodified_wire.edges()), 2)
        square.wrapped = None
        with self.assertRaises(ValueError):
            square.fillet_2d(0.1, square.vertices())

    def test_fillet_non_planar(self):
        wire = Wire(
            [
                Edge.make_line((0, 0, 0), (1, 0, 0)),
                Edge.make_line((1, 0, 0), (1, 1, 0)),
                Edge.make_line((1, 1, 0), (0, 0, 1)),
            ]
        )
        with self.assertRaises(ValueError):
            wire.fillet_2d(0.1, wire.vertices()[1])

    def test_bad_vertex(self):
        rect = Face.make_rect(2, 2).wire()
        with self.assertRaises(ValueError):
            rect.fillet_2d(0.2, Vertex(0, 0, 0))

    def test_fillet_non_plane_xy(self):
        wire_loc: Wire = (Plane.XZ * Pos(1, 2) * Rectangle(2, 2)).wire()
        f_wire_loc = wire_loc.fillet_2d(0.2, wire_loc.vertices())
        self.assertEqual(len(f_wire_loc.edges().filter_by(GeomType.CIRCLE)), 4)

        wire_face: Wire = Face.make_rect(2, 2, plane=Plane.XZ).wire()
        f_wire_face = wire_face.fillet_2d(0.2, wire_face.vertices())
        self.assertEqual(len(f_wire_face.edges().filter_by(GeomType.CIRCLE)), 4)

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

        reversed_arc = Edge.make_circle(
            3, Plane((5, 3, 0)), start_angle=-90, end_angle=0
        ).reversed()
        explicit_reversed_wire = Wire(
            [
                Edge.make_line((0, 0), (5, 0)),
                reversed_arc,
                Edge.make_line((8, 3), (12, 3)),
            ]
        )
        trimmed_reversed_wire = explicit_reversed_wire.trim(0.2, 0.8)
        self.assertEqual(len(trimmed_reversed_wire.edges()), 3)
        self.assertAlmostEqual(trimmed_reversed_wire.length, 8.227433388230814, 5)
        self.assertAlmostEqual(trimmed_reversed_wire @ 0, (2.7424777960769386, 0, 0), 5)
        self.assertAlmostEqual(trimmed_reversed_wire @ 1, (9.257522203923063, 3, 0), 5)

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
        w = Wire(
            [
                Line((0, 0), (0, 1)),
                JernArc((0, 1), (0, 1), 1, -90).reversed(reconstruct=True),
            ]
        )
        self.assertAlmostEqual(w.tangent_at(0), (0, 1, 0), 6)
        self.assertAlmostEqual(w.tangent_at(1), (1, 0, 0), 6)

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

    def test_edges_of_branching_wire(self):
        line = Line((0, 0), (30, 0))
        star = line + Rot(Z=-120) * line + Rot(Z=120) * line
        self.assertIsInstance(star, Wire)
        self.assertEqual(len(star.edges()), 3)
        self.assertAlmostEqual(star.length, 90, 5)
        both = star + Rot(Z=60) * star
        self.assertEqual(len(both.edges()), 6)
        self.assertAlmostEqual(both.length, 180, 5)

    def test_edges_connection_order(self):
        edges = Wire.make_polygon([(0, 0), (1, 0), (1, 1), (0, 1)]).edges()
        self.assertEqual(len(edges), 4)
        for first, second in zip(edges, edges[1:]):
            self.assertAlmostEqual(first.end_point(), second.start_point(), 5)

    @staticmethod
    def _reversed_wires() -> dict[str, Wire]:
        """Wires the kernel marks as reversed, as those of a mirrored sketch are"""

        def flipped(wire: Wire) -> Wire:
            return Wire(TopoDS.Wire(wire.wrapped.Reversed()))

        mixed = Wire(
            [
                Edge.make_line((0, 0), (4, 0)),
                Edge.make_line((4, 3), (4, 0)),
                Edge.make_three_point_arc((4, 3), (3, 5), (1, 5)),
            ]
        )
        wires = {
            "open": flipped(Polyline((0, 0), (4, 0), (4, 3), (1, 5)).wire()),
            "open, edges in both directions": flipped(mixed),
            "single edge": flipped(Wire([Edge.make_line((0, 0), (4, 0))])),
            "mirrored rectangle": Rectangle(2, 2).mirror().wire(),
            "mirrored rounded rectangle": RectangleRounded(4, 3, 0.5)
            .mirror(Plane.YZ)
            .wire(),
            "outer wire of a flipped face": (-Rectangle(2, 2).face()).outer_wire(),
        }
        assert not any(wire.is_forward for wire in wires.values())
        return wires

    def test_param_at_point_reversed_wire(self):
        # Issue #1149: the parameter of a point is the one position_at takes
        for name, wire in self._reversed_wires().items():
            for u_value in (0.1, 0.3, 0.45, 0.625, 0.8, 0.95):
                with self.subTest(wire=name, u_value=u_value):
                    point = wire.position_at(u_value)
                    self.assertAlmostEqual(wire.param_at_point(point), u_value, 5)

        mirrored = Rectangle(2, 2).mirror().wire()
        self.assertAlmostEqual(
            mirrored @ mirrored.param_at_point((1, 0, 0)), (1, 0, 0), 5
        )

    def test_sort_by_reversed_wire(self):
        for name, wire in self._reversed_wires().items():
            with self.subTest(wire=name):
                sorted_edges = wire.edges().sort_by(wire)
                self.assertLess(sorted_edges[0].distance_to(wire @ 0.01), 1e-5)
                self.assertLess(sorted_edges[-1].distance_to(wire @ 0.99), 1e-5)

    def test_trim_reversed_wire(self):
        for name, wire in self._reversed_wires().items():
            for by_point in (False, True):
                with self.subTest(wire=name, by_point=by_point):
                    start, end = wire @ 0.2, wire @ 0.7
                    trimmed = wire.trim(start, end) if by_point else wire.trim(0.2, 0.7)
                    self.assertAlmostEqual(trimmed.length, wire.length / 2, 5)
                    self.assertAlmostEqual(trimmed @ 0, start, 5)
                    self.assertAlmostEqual(trimmed @ 1, end, 5)

    def test_order_edges_reversed_wire(self):
        # The edges stay in the kernel's order, each joined to the next
        for name, wire in self._reversed_wires().items():
            with self.subTest(wire=name):
                ordered_edges = wire.order_edges()
                for edge, kernel_edge in zip(ordered_edges, wire.edges()):
                    self.assertAlmostEqual(edge @ 0, kernel_edge @ 0, 5)
                    self.assertAlmostEqual(edge @ 1, kernel_edge @ 1, 5)
                for edge, next_edge in zip(ordered_edges, ordered_edges[1:]):
                    self.assertAlmostEqual(edge @ 1, next_edge @ 0, 5)

    def test_offset_2d_fits_splines_to_offset_curves(self):
        # Issue #1073: the kernel's own offset curves cannot be written to STEP
        ellipse = Wire([Edge.make_ellipse(50, 100)])
        for placement in (Location(), Location((5, 6, 7), (30, 0, 0))):
            with self.subTest(placement=placement):
                placed = placement * ellipse
                grown = placed.offset_2d(50)
                self.assertTrue(grown.is_valid)
                self.assertTrue(grown.is_closed)
                kinds = {edge.geom_type for edge in grown.edges()}
                self.assertNotIn(GeomType.OFFSET, kinds)
                self.assertIn(GeomType.BSPLINE, kinds)
                for edge in grown.edges():
                    for u_value in (0, 0.5, 1):
                        self.assertAlmostEqual(
                            placed.distance_to(edge @ u_value), 50, 5
                        )

        ring = Solid.extrude(Face(ellipse.offset_2d(50), [ellipse]), Vector(0, 0, 10))
        with tempfile.TemporaryDirectory() as tmp_dir:
            step_file = os.path.join(tmp_dir, "ring.step")
            export_step(ring, step_file)
            self.assertAlmostEqual(import_step(step_file).volume, ring.volume, 3)

    def test_offset_2d_without_curves_is_unchanged(self):
        grown = Wire.make_rect(10, 5).offset_2d(1)
        kinds = {edge.geom_type for edge in grown.edges()}
        self.assertEqual(kinds, {GeomType.LINE, GeomType.CIRCLE})

    def test_offset_2d_as_bspline(self):
        spline = Spline((0, 0), (2, 1), (4, 0))
        ellipse = Wire([Edge.make_ellipse(3, 2)])

        # The kernel's offset curves are kept on request
        for curve in (spline, ellipse):
            kept = curve.offset_2d(0.3, as_bspline=False)
            kinds = {edge.geom_type for edge in kept.edges()}
            self.assertIn(GeomType.OFFSET, kinds)
            self.assertNotIn(GeomType.BSPLINE, kinds)

        # Either way it is the same outline, wound the same way
        for curve in (spline, ellipse):
            fitted = Face(Wire(curve.offset_2d(0.3).edges()))
            kept = Face(Wire(curve.offset_2d(0.3, as_bspline=False).edges()))
            self.assertAlmostEqual(fitted.area, kept.area, 5)
            self.assertAlmostEqual(fitted.normal_at(), kept.normal_at(), 5)
            self.assertAlmostEqual(fitted.normal_at(), Vector(0, 0, 1), 5)

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


class TestWireFilletHelpers(unittest.TestCase):

    def test_analyze_wire_fillet_corner_missing_vertex(self):
        wire = Wire.make_rect(1, 1)
        vertex = Vertex((10, 10, 0))

        with self.assertRaises(ValueError) as ctx:
            one_d._analyze_wire_fillet_corner(wire, vertex)
        self.assertIn("Could not find shared vertex on wire", str(ctx.exception))

    def test_analyze_wire_fillet_corner_vertex_not_degree_two(self):
        wire = Wire.make_rect(1, 1)
        shared_vertex = wire.vertices()[0]
        mock_edges = MagicMock()
        mock_edges.filter_by.return_value = [MagicMock(), MagicMock(), MagicMock()]

        with (
            patch.object(wire, "edges", return_value=mock_edges),
            self.assertRaises(ValueError) as ctx,
        ):
            one_d._analyze_wire_fillet_corner(wire, shared_vertex)
        self.assertIn("Vertex must connect exactly two edges", str(ctx.exception))

    def test_solve_wire_fillet_corner_geom2dgcc_circ2d2tanrad_no_solution(self):
        wire = Wire.make_rect(1, 1)
        corner = one_d._analyze_wire_fillet_corner(wire, wire.vertices()[0])
        self.assertIsNone(
            one_d._solve_wire_fillet_corner_geom2dgcc_circ2d2tanrad(corner, 10)
        )

    def test_wire_fillet_corner_is_tangent_continuous_straight_wire(self):
        wire = Wire(
            [
                Edge.make_line((0, 0), (1, 0)),
                Edge.make_line((1, 0), (2, 0)),
            ]
        )
        corner = one_d._analyze_wire_fillet_corner(
            wire, wire.vertices().sort_by_distance((1, 0, 0))[0]
        )

        self.assertTrue(one_d._wire_fillet_corner_is_tangent_continuous(corner))

    def test_wire_fillet_corner_is_not_tangent_continuous_on_rounded_cut_tips(self):
        sketch = RectangleRounded(20, 10, 2)
        sketch -= [
            Location(e.arc_center) for e in sketch.edges().filter_by(GeomType.CIRCLE)
        ] * Circle(2)
        wire = sketch.wire()

        skipped_vertices = [(-10, -3, 0), (-10, 3, 0), (-8, 5, 0)]
        for point in skipped_vertices:
            with self.subTest(point=point):
                corner = one_d._analyze_wire_fillet_corner(
                    wire, wire.vertices().sort_by_distance(point)[0]
                )
                self.assertFalse(
                    one_d._wire_fillet_corner_is_tangent_continuous(corner)
                )

    def test_fillet_wire_corner_failure_when_solver_fails(self):
        wire = Wire.make_rect(1, 1)
        vertex = wire.vertices()[0]

        with patch(
            "build123d.topology.one_d._solve_wire_fillet_corner_geom2dgcc_circ2d2tanrad",
            return_value=None,
        ):
            with self.assertRaises(ValueError) as ctx:
                one_d._fillet_wire_corner(wire, vertex, 0.1)

        self.assertIn("Fillet algorithm failed", str(ctx.exception))

    def test_fillet_wire_corner_failure_when_closed_wire_becomes_open(self):
        wire = Wire.make_rect(1, 1)
        vertex = wire.vertices()[0]
        # Create an open wire to simulate a failed splice
        open_wire = Wire(wire.edges().sort_by(Axis.X)[:-1])

        with (
            patch(
                "build123d.topology.one_d._solve_wire_fillet_corner_geom2dgcc_circ2d2tanrad",
                return_value=MagicMock(),  # Return a dummy solution
            ),
            patch(
                "build123d.topology.one_d._splice_wire_fillet_corner",
                return_value=open_wire,
            ),
        ):
            with self.assertRaises(ValueError) as ctx:
                one_d._fillet_wire_corner(wire, vertex, 0.1)

        self.assertIn("Filleting failed to create a closed wire", str(ctx.exception))


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


class TestWireValidation(unittest.TestCase):
    """Guards on Wire operations that reject unusable input."""

    def setUp(self):
        self.wire = Wire(
            [
                Edge.make_line((0, 0), (10, 0)),
                Edge.make_line((10, 0), (10, 10)),
                Edge.make_line((10, 10), (0, 10)),
                Edge.make_line((0, 10), (0, 0)),
            ]
        )

    def test_make_wire_merges_coincident_vertices_deterministically(self):
        """#1492: neighbours whose ends coincide within tolerance but are not
        bit-identical must share the same vertex whatever the run or order"""
        for reverse in (False, True):
            edges = [
                Edge.make_line((0, 0, 0), (1e-20, 0, 10)),
                Edge.make_three_point_arc((0, 0, 10), (5, 0, 15), (10, 0, 10)),
                Edge.make_line((10, 0, 10), (10, 0, 0)),
                Edge.make_line((10, 0, 0), (0, 0, 0)),
            ]
            wire = Wire(edges[::-1] if reverse else edges)
            self.assertTrue(wire.is_closed)
            shared = [v for v in wire.vertices() if v.Z > 5 and v.X < 1]
            self.assertEqual(len(shared), 1)
            # the wire's vertex is the merge of the two, not either one picked
            # by memory address
            self.assertGreater(shared[0].X, 0)
            self.assertLess(shared[0].X, 1e-20)

    def test_make_wire_preserves_input_geometry(self):
        for order in ((0, 1, 2, 3), (0, 1, 3, 2), (0, 1, 3)):
            with self.subTest(order=order):
                edges = [
                    Edge.make_line((0, 0), (1, 0)),
                    Edge.make_line((1, 5e-8), (2, 0)),
                    Edge.make_line((2, 0), (3, 0)),
                    Edge.make_line((3, 0), (4, 0)),
                ]
                source = Compound(edges)
                before = io.BytesIO()
                export_brep(source, before)
                if len(order) == 3:
                    with self.assertRaisesRegex(ValueError, "disconnected"):
                        Wire(edges[i] for i in order)
                else:
                    wire = Wire(edges[i] for i in order)
                    self.assertEqual(len(wire.edges()), 4)
                after = io.BytesIO()
                export_brep(source, after)
                # BREP includes vertex coordinates, tolerances and parent topology.
                self.assertEqual(after.getvalue(), before.getvalue())

    def test_make_wire_exact_joins_with_different_tolerances(self):
        for located in (False, True):
            with self.subTest(located=located):
                first = Edge.make_line((0, 0), (1, 0))
                second = (
                    Edge.make_line((0, 0), (1, 0)).moved(Pos(X=1))
                    if located
                    else Edge.make_line((1, 0), (2, 0))
                )
                BRep_Builder().UpdateVertex(second.vertices()[0].wrapped, 5e-7)
                source = Compound([first, second])
                before = io.BytesIO()
                export_brep(source, before)
                wire = Wire([first, second])
                self.assertEqual(len(wire.vertices()), 3)
                joint = wire.vertices().sort_by(Axis.X)[1]
                self.assertEqual(tuple(joint), (1, 0, 0))
                self.assertAlmostEqual(BRep_Tool.Tolerance_s(joint.wrapped), 5e-7, 12)
                after = io.BytesIO()
                export_brep(source, after)
                self.assertEqual(after.getvalue(), before.getvalue())

    def test_make_wire_preserves_closure_tolerance(self):
        for gap in (1e-7, 1.5e-7, 2e-7, 2.1e-7):
            with self.subTest(gap=gap):
                wire = Wire(
                    [
                        Edge.make_line((0, 0), (1, 0)),
                        Edge.make_line((1, 0), (1, 1)),
                        Edge.make_line((1, 1), (0, gap)),
                    ]
                )
                self.assertEqual(wire.is_closed, gap <= 2e-7)
                if gap <= 2e-7:
                    self.assertEqual(len(wire.vertices()), 3)
                    self.assertTrue(Face(wire).is_valid)

    def test_make_wire_preserves_shared_topology(self):
        for original in (Wire.make_rect(1, 1), Wire.make_circle(1)):
            edges = original.edges()
            rebuilt = Wire(edges)
            self.assertTrue(rebuilt.is_closed)
            self.assertTrue(rebuilt.is_valid)
            self.assertEqual(len(rebuilt.vertices()), len(original.vertices()))
            for edge in edges:
                self.assertTrue(any(edge.is_same(other) for other in rebuilt.edges()))

    def test_make_wire_preserves_branching_input(self):
        edges = [
            Edge.make_line((0, 0), (1, 0)),
            Edge.make_line((1, 5e-8), (2, 0)),
            Edge.make_line((1, 0), (1, 1)),
        ]
        wire = Wire(edges)
        self.assertEqual(len(wire.edges()), 3)
        self.assertEqual(len(wire.vertices()), 4)

    def test_make_wire_sorts_out_of_order_edges(self):
        edges = [
            Edge.make_line((0, 0), (10, 0)),
            Edge.make_line((10, 10), (0, 10)),
            Edge.make_line((10, 0), (10, 10)),
            Edge.make_line((0, 10), (0, 0)),
        ]
        wire = Wire(edges)
        self.assertTrue(wire.is_closed)
        self.assertEqual(len(wire.edges()), 4)

    def test_make_wire_disconnected(self):
        with self.assertRaisesRegex(ValueError, "disconnected"):
            Wire([Edge.make_line((0, 0), (1, 0)), Edge.make_line((5, 5), (6, 5))])

    def test_make_wire_empty(self):
        builder = MagicMock()
        builder.IsDone.return_value = False
        builder.Error.return_value = BRepBuilderAPI_EmptyWire
        with patch(
            "build123d.topology.one_d.BRepBuilderAPI_MakeWire", return_value=builder
        ):
            with self.assertRaisesRegex(RuntimeError, "Wire is empty"):
                Wire([Edge.make_line((0, 0), (1, 0))])

    def test_make_wire_non_manifold(self):
        builder = MagicMock()
        builder.IsDone.return_value = False
        builder.Error.return_value = BRepBuilderAPI_NonManifoldWire
        with patch(
            "build123d.topology.one_d.BRepBuilderAPI_MakeWire", return_value=builder
        ):
            with self.assertWarnsRegex(UserWarning, "non manifold"):
                # _make_wire directly: the mocked builder's Wire() is not a
                # TopoDS_Wire so it can't be fed to the Wire constructor
                Wire._make_wire([Edge.make_line((0, 0), (1, 0))])

    def test_extrude_is_invalid(self):
        with self.assertRaisesRegex(ValueError, "can't be created by extrusion"):
            Wire.extrude(Edge.make_line((0, 0), (1, 0)), (0, 0, 1))

    def test_chamfer_2d_internal_error(self):
        """The chamfered shape isn't a face - simulated by a failing shape fix."""
        shape_fix = MagicMock()
        shape_fix.Shape.return_value = Edge.make_line((0, 0), (1, 0)).wrapped
        with patch("build123d.topology.one_d.ShapeFix_Shape", return_value=shape_fix):
            with self.assertRaisesRegex(RuntimeError, "internal error"):
                self.wire.chamfer_2d(
                    1, 1, [self.wire.vertices()[0]], self.wire.edges()[0]
                )

    def test_fillet_2d_vertex_not_on_wire(self):
        with self.assertRaisesRegex(ValueError, "Could not find fillet vertex"):
            self.wire.fillet_2d(1, [Vertex(100, 100, 0)])

    def test_param_at_point_no_extrema(self):
        extrema = MagicMock()
        extrema.IsDone.return_value = False
        extrema.NbSolution.return_value = 0
        with patch(
            "build123d.topology.one_d.BRepExtrema_DistShapeShape", return_value=extrema
        ):
            with self.assertRaisesRegex(ValueError, "point is not on Wire"):
                self.wire.param_at_point((5, 0, 0))

    def test_project_to_shape_empty_target(self):
        with self.assertRaisesRegex(ValueError, "Can't project empty Wires"):
            self.wire.project_to_shape([], direction=(0, 0, -1))

    def test_stitch_empty_wire(self):
        with self.assertRaisesRegex(ValueError, "Can't stitch empty wires"):
            self.wire.stitch(Wire())

    def test_to_bspline_add_failure(self):
        builder = MagicMock()
        builder.Add.return_value = False
        with patch(
            "build123d.topology.one_d.GeomConvert_CompCurveToBSplineCurve",
            return_value=builder,
        ):
            with self.assertRaisesRegex(RuntimeError, "Failed to build bspline"):
                self.wire._to_bspline()

    def test_to_bspline_edge_failure(self):
        edge_builder = MagicMock()
        edge_builder.IsDone.return_value = False
        with patch(
            "build123d.topology.one_d.BRepBuilderAPI_MakeEdge",
            return_value=edge_builder,
        ):
            with self.assertRaisesRegex(RuntimeError, "Failed to build bspline"):
                self.wire._to_bspline()


if __name__ == "__main__":
    unittest.main()
