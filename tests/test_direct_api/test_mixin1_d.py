"""
build123d imports

name: test_mixin1_d.py
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

import copy
import math
import unittest
from unittest.mock import patch

import numpy as np

from build123d.build_enums import (
    CenterOf,
    FrameMethod,
    GeomType,
    Keep,
    PositionMode,
    Side,
    SortBy,
)
from build123d.geometry import Axis, Location, Plane, Rot, Vector, TOLERANCE
from build123d.objects_curve import CenterArc, Line, Polyline
from build123d.objects_part import Box, Cylinder
from build123d.operations_part import extrude
from build123d.operations_generic import fillet
from OCP.TopoDS import TopoDS
from build123d.topology import Compound, Edge, Face, Solid, Vertex, Wire


class TestMixin1D(unittest.TestCase):
    """Test the add in methods"""

    def test_position_at(self):
        self.assertAlmostEqual(
            Edge.make_line((0, 0, 0), (1, 1, 1)).position_at(0.5),
            (0.5, 0.5, 0.5),
            5,
        )
        # Not sure what PARAMETER mode returns - but it's in the ballpark
        point = Edge.make_line((0, 0, 0), (1, 1, 1)).position_at(
            0.5, position_mode=PositionMode.PARAMETER
        )
        self.assertTrue(all([0.0 < v < 1.0 for v in point]))

        wire = Wire([Edge.make_line((0, 0, 0), (10, 0, 0))])
        self.assertAlmostEqual(wire.position_at(0.3), (3, 0, 0), 5)
        self.assertAlmostEqual(
            wire.position_at(3, position_mode=PositionMode.LENGTH), (3, 0, 0), 5
        )
        self.assertAlmostEqual(wire.edge().position_at(0.3), (3, 0, 0), 5)
        self.assertAlmostEqual(
            wire.edge().position_at(3, position_mode=PositionMode.LENGTH), (3, 0, 0), 5
        )

        circle_wire = Wire(
            [
                Edge.make_circle(1, start_angle=0, end_angle=180),
                Edge.make_circle(1, start_angle=180, end_angle=360),
            ]
        )
        p1 = circle_wire.position_at(math.pi, position_mode=PositionMode.LENGTH)
        p2 = circle_wire.position_at(math.pi / circle_wire.length)
        self.assertAlmostEqual(p1, (-1, 0, 0), 14)
        self.assertAlmostEqual(p2, (-1, 0, 0), 14)
        self.assertAlmostEqual(p1, p2, 14)

        circle_edge = Edge.make_circle(1)
        p3 = circle_edge.position_at(math.pi, position_mode=PositionMode.LENGTH)
        p4 = circle_edge.position_at(math.pi / circle_edge.length)
        self.assertAlmostEqual(p3, (-1, 0, 0), 14)
        self.assertAlmostEqual(p4, (-1, 0, 0), 14)
        self.assertAlmostEqual(p3, p4, 14)

        circle = Wire(
            [
                Edge.make_circle(2, start_angle=0, end_angle=180),
                Edge.make_circle(2, start_angle=180, end_angle=360),
            ]
        )
        self.assertAlmostEqual(
            circle.position_at(0.5),
            (-2, 0, 0),
            5,
        )
        self.assertAlmostEqual(
            circle.position_at(2 * math.pi, position_mode=PositionMode.LENGTH),
            (-2, 0, 0),
            5,
        )

    def test_positions_with_distances(self):
        e = Edge.make_line((0, 0, 0), (1, 1, 1))
        distances = [i / 4 for i in range(3)]
        pts = e.positions(distances)
        for i, position in enumerate(pts):
            self.assertAlmostEqual(position, (i / 4, i / 4, i / 4), 5)

    def test_positions_deflection_line(self):
        """Deflection sampling on a straight line should yield exactly 2 points."""
        e = Edge.make_line((0, 0, 0), (10, 0, 0))
        pts = e.positions(deflection=0.1)

        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[0], (0, 0, 0), 7)
        self.assertAlmostEqual(pts[1], (10, 0, 0), 7)

    def test_positions_deflection_circle(self):
        """Deflection on a C2 curve (circle) should produce multiple points."""
        radius = 5
        e = Edge.make_circle(radius)

        pts = e.positions(deflection=0.1)

        # Should produce more than just two points
        self.assertGreater(len(pts), 2)

        # Endpoints should match curve endpoints
        first, last = pts[0], pts[-1]
        curve = e.geom_adaptor()
        p0 = Vector(curve.Value(curve.FirstParameter()))
        p1 = Vector(curve.Value(curve.LastParameter()))

        self.assertAlmostEqual(first, p0, 7)
        self.assertAlmostEqual(last, p1, 7)

    def test_positions_deflection_resolution(self):
        """Smaller deflection tolerance should produce more points."""
        e = Edge.make_circle(10)

        pts_coarse = e.positions(deflection=0.5)
        pts_fine = e.positions(deflection=0.05)

        self.assertGreater(len(pts_fine), len(pts_coarse))

    def test_positions_deflection_C0_curve(self):
        """C0 spline should use QuasiUniformDeflection and still succeed."""
        e = Polyline((0, 0), (1, 2), (2, 0))._to_bspline()  # C0
        pts = e.positions(deflection=0.1)

        self.assertGreater(len(pts), 2)

    def test_positions_missing_arguments(self):
        e = Edge.make_line((0, 0, 0), (1, 0, 0))
        with self.assertRaises(ValueError):
            e.positions()

    def test_positions_deflection_failure(self):
        e = Edge.make_circle(1.0)

        with patch("build123d.topology.one_d.GCPnts_UniformDeflection") as MockDefl:
            instance = MockDefl.return_value
            instance.IsDone.return_value = False
            instance.NbPoints.return_value = 0

            with self.assertRaises(RuntimeError):
                e.positions(deflection=0.1)

    def test_tangent_at(self):
        self.assertAlmostEqual(
            Edge.make_circle(1, start_angle=0, end_angle=90).tangent_at(1.0),
            (-1, 0, 0),
            5,
        )
        tangent = Edge.make_circle(1, start_angle=0, end_angle=90).tangent_at(
            0.0, position_mode=PositionMode.PARAMETER
        )
        self.assertTrue(all([0.0 <= v <= 1.0 for v in tangent]))

        self.assertAlmostEqual(
            Edge.make_circle(1, start_angle=0, end_angle=180).tangent_at(
                math.pi / 2, position_mode=PositionMode.LENGTH
            ),
            (-1, 0, 0),
            5,
        )

    def test_tangent_at_point(self):
        circle = Wire(
            [
                Edge.make_circle(1, start_angle=0, end_angle=180),
                Edge.make_circle(1, start_angle=180, end_angle=360),
            ]
        )
        pnt_on_circle = Vector(math.cos(math.pi / 4), math.sin(math.pi / 4))
        tan = circle.tangent_at(pnt_on_circle)
        self.assertAlmostEqual(tan, (-math.sqrt(2) / 2, math.sqrt(2) / 2), 5)

    def test_tangent_at_by_length(self):
        circle = Edge.make_circle(1)
        tan = circle.tangent_at(circle.length * 0.5, position_mode=PositionMode.LENGTH)
        self.assertAlmostEqual(tan, (0, -1), 5)

    def test_tangent_at_error(self):
        with self.assertRaises(ValueError):
            Edge.make_circle(1).tangent_at("start")

    def test_normal(self):
        self.assertAlmostEqual(
            Edge.make_circle(
                1, Plane(origin=(0, 0, 0), z_dir=(1, 0, 0)), start_angle=0, end_angle=60
            ).normal(),
            (1, 0, 0),
            5,
        )
        self.assertAlmostEqual(
            Edge.make_ellipse(
                1,
                0.5,
                Plane(origin=(0, 0, 0), z_dir=(1, 1, 0)),
                start_angle=0,
                end_angle=90,
            ).normal(),
            (math.sqrt(2) / 2, math.sqrt(2) / 2, 0),
            5,
        )
        self.assertAlmostEqual(
            Edge.make_spline(
                [
                    (1, 0),
                    (math.sqrt(2) / 2, math.sqrt(2) / 2),
                    (0, 1),
                ],
                tangents=((0, 1, 0), (-1, 0, 0)),
            ).normal(),
            (0, 0, 1),
            5,
        )
        line = Edge.make_line((0, 0, 0), (1, 1, 1))
        with self.assertRaises(ValueError):
            line.normal()
        line.wrapped = None
        with self.assertRaises(ValueError):
            line.normal()

    def test_center(self):
        c = Edge.make_circle(1, start_angle=0, end_angle=180)
        self.assertAlmostEqual(c.center(), (0, 1, 0), 5)
        self.assertAlmostEqual(
            c.center(CenterOf.MASS),
            (0, 0.6366197723675814, 0),
            5,
        )
        self.assertAlmostEqual(c.center(CenterOf.BOUNDING_BOX), (0, 0.5, 0), 5)
        c.wrapped = None
        with self.assertRaises(ValueError):
            c.center()

    def test_location_at(self):
        loc = Edge.make_circle(1).location_at(0.25)
        self.assertAlmostEqual(loc.position, (0, 1, 0), 5)
        self.assertAlmostEqual(loc.orientation, (0, -90, -90), 5)

        loc = Edge.make_circle(1).location_at(
            math.pi / 2, position_mode=PositionMode.LENGTH
        )
        self.assertAlmostEqual(loc.position, (0, 1, 0), 5)
        self.assertAlmostEqual(loc.orientation, (0, -90, -90), 5)

        path = Polyline((0, 0), (10, 0), (10, 10), (0, 10))
        loc = path.location_at(0.75)
        self.assertAlmostEqual(loc.position, (7.5, 10, 0), 5)
        self.assertAlmostEqual(loc.orientation, (0, -90, 180), 5)

        loc = path.location_at(0.75 * 30, position_mode=PositionMode.LENGTH)
        self.assertAlmostEqual(loc.position, (7.5, 10, 0), 5)
        self.assertAlmostEqual(loc.orientation, (0, -90, 180), 5)

    def test_location_at_x_dir(self):
        path = Polyline((-50, -40), (50, -40), (50, 40), (-50, 40), close=True)
        l1 = path.location_at(0)
        l2 = path.location_at(0, x_dir=(0, 1, 0))
        self.assertAlmostEqual(l1.position, l2.position, 5)
        self.assertAlmostEqual(l1.z_axis, l2.z_axis, 5)
        self.assertNotEqual(l1.x_axis, l2.x_axis, 5)
        self.assertAlmostEqual(l2.x_axis, Axis(path @ 0, (0, 1, 0)), 5)

        with self.assertRaises(ValueError):
            path.location_at(0, x_dir=(1, 0, 0))

    def test_locations(self):
        locs = Edge.make_circle(1).locations([i / 4 for i in range(4)])
        self.assertAlmostEqual(locs[0].position, (1, 0, 0), 5)
        self.assertAlmostEqual(locs[0].orientation, (-90, 0, -180), 5)
        self.assertAlmostEqual(locs[1].position, (0, 1, 0), 5)
        self.assertAlmostEqual(locs[1].orientation, (0, -90, -90), 5)
        self.assertAlmostEqual(locs[2].position, (-1, 0, 0), 5)
        self.assertAlmostEqual(locs[2].orientation, (90, 0, 0), 5)
        self.assertAlmostEqual(locs[3].position, (0, -1, 0), 5)
        self.assertAlmostEqual(locs[3].orientation, (0, 90, 90), 5)

    def test_wire_locations_numpy_batch_matches_scalar_frames(self):
        """The batch path returns scalar-equivalent frames with one traversal."""
        distances = np.array([1.0, 0.5, 0.0, 0.25, 0.5, 0.75])
        batched_wire = Wire(
            [
                Edge.make_line((0, 0, 0), (2, 0, 0)),
                Edge.make_line((2, 0, 0), (2, 3, 0)),
            ]
        )
        scalar_wire = Wire(
            [
                Edge.make_line((0, 0, 0), (2, 0, 0)),
                Edge.make_line((2, 0, 0), (2, 3, 0)),
            ]
        )

        with patch.object(batched_wire, "edges", wraps=batched_wire.edges) as edge_call:
            actual = batched_wire.locations(distances)

        expected = [scalar_wire.location_at(distance) for distance in distances]
        self.assertEqual(edge_call.call_count, 1)
        self.assertEqual(len(actual), len(expected))
        for actual_location, expected_location in zip(actual, expected):
            self.assertAlmostEqual(
                actual_location.position, expected_location.position, 10
            )
            self.assertAlmostEqual(
                actual_location.x_axis.direction, expected_location.x_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.y_axis.direction, expected_location.y_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.z_axis.direction, expected_location.z_axis.direction, 10
            )

    def test_wire_locations_numpy_batch_falls_back_for_other_inputs(self):
        """Unsupported arrays retain scalar behavior, and empty arrays skip geometry."""
        wire = Wire([Edge.make_line((0, 0, 0), (1, 0, 0))])
        with patch.object(wire, "edges", wraps=wire.edges) as edge_call:
            self.assertEqual(wire.locations(np.array([], dtype=np.float64)), [])
        self.assertEqual(edge_call.call_count, 0)

        for distances in (np.array([0.0, 1.5]), np.array([0.0, 1.0], dtype=np.float32)):
            with patch.object(
                wire, "location_at", wraps=wire.location_at
            ) as scalar_call:
                wire.locations(distances)
            self.assertEqual(scalar_call.call_count, distances.size)

        with self.assertRaises(IndexError):
            wire.locations(np.array([0.0, np.nan]))
        with self.assertRaises(ValueError):
            wire.locations(np.array([[0.0, 1.0]]))

        with patch.object(wire, "location_at", wraps=wire.location_at) as scalar_call:
            wire.locations(np.array([0.0, 1.0]), frame_method=FrameMethod.CORRECTED)
        self.assertEqual(scalar_call.call_count, 2)

        with patch.object(wire, "location_at", wraps=wire.location_at) as scalar_call:
            wire.locations(np.array([0.0, 1.0]), x_dir=(0, 1, 0))
        self.assertEqual(scalar_call.call_count, 2)

        class WireSubclass(Wire):
            pass

        class ArraySubclass(np.ndarray):
            pass

        subclass_wire = WireSubclass([Edge.make_line((0, 0, 0), (1, 0, 0))])
        subclass_array = np.array([0.0, 1.0]).view(ArraySubclass)
        with patch.object(
            subclass_wire, "location_at", wraps=subclass_wire.location_at
        ) as scalar_call:
            subclass_wire.locations(np.array([0.0, 1.0]))
        self.assertEqual(scalar_call.call_count, 2)

        with patch.object(wire, "location_at", wraps=wire.location_at) as scalar_call:
            wire.locations(subclass_array)
        self.assertEqual(scalar_call.call_count, 2)

        original_errors = np.geterr()
        original_callback = np.geterrcall()
        try:
            np.seterr(under="call")
            np.seterrcall(lambda *_: None)
            with patch.object(wire, "edges", wraps=wire.edges) as edge_call:
                wire.locations(np.array([0.0, 1.0]))
            self.assertEqual(edge_call.call_count, 2)
        finally:
            np.seterr(**original_errors)
            np.seterrcall(original_callback)

    def test_wire_locations_numpy_batch_preserves_length_and_placement(self):
        """The batch path matches scalar output in length mode and after placement."""

        def make_wire():
            return Wire(
                [
                    Edge.make_line((0, 0, 0), (2, 0, 0)),
                    Edge.make_line((2, 0, 0), (2, 3, 0)),
                ]
            ).located(Location((4, -2, 7), (10, 20, 30)))

        distances = np.array([3.0, 0.0, 5.0, 2.5, 1.0])
        actual = make_wire().locations(distances, position_mode=PositionMode.LENGTH)
        expected = [
            make_wire().location_at(distance, position_mode=PositionMode.LENGTH)
            for distance in distances
        ]
        for actual_location, expected_location in zip(actual, expected):
            self.assertAlmostEqual(
                actual_location.position, expected_location.position, 10
            )
            self.assertAlmostEqual(
                actual_location.x_axis.direction, expected_location.x_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.y_axis.direction, expected_location.y_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.z_axis.direction, expected_location.z_axis.direction, 10
            )

    def test_wire_locations_numpy_batch_keeps_generator_streaming(self):
        """A generator observes wire mutation between yielded distances."""
        wire = Wire([Edge.make_line((0, 0, 0), (1, 0, 0))])

        def distances():
            yield 0.0
            wire.move(Location((5, 0, 0)))
            yield 0.0

        locations = wire.locations(distances())
        self.assertAlmostEqual(locations[0].position, (0, 0, 0), 10)
        self.assertAlmostEqual(locations[1].position, (5, 0, 0), 10)

    def test_wire_locations_numpy_batch_handles_reversed_orientations(self):
        """The batch path matches scalar results for reversed wires and edges."""
        source = Wire.make_polygon([(0, 0), (2, 0), (2, 3), (0, 3)], close=True)
        reversed_wire = Wire(TopoDS.Wire(source.wrapped.Reversed()))
        reversed_edges_wire = Wire(
            [edge.reversed() for edge in source.edges()], sequenced=True
        )

        for batched_wire, scalar_wire in (
            (reversed_wire, Wire(TopoDS.Wire(source.wrapped.Reversed()))),
            (
                reversed_edges_wire,
                Wire([edge.reversed() for edge in source.edges()], sequenced=True),
            ),
        ):
            distances = np.array([1.0, 0.0, 0.4, 0.25, 0.75, 0.4])
            actual = batched_wire.locations(distances)
            expected = [scalar_wire.location_at(distance) for distance in distances]
            for actual_location, expected_location in zip(actual, expected):
                self.assertAlmostEqual(
                    actual_location.position, expected_location.position, 10
                )
                self.assertAlmostEqual(
                    actual_location.x_axis.direction,
                    expected_location.x_axis.direction,
                    10,
                )
                self.assertAlmostEqual(
                    actual_location.y_axis.direction,
                    expected_location.y_axis.direction,
                    10,
                )
                self.assertAlmostEqual(
                    actual_location.z_axis.direction,
                    expected_location.z_axis.direction,
                    10,
                )

        sharp_wire = Wire(
            [
                Edge.make_line((0, 0), (2, 0)),
                Edge.make_line((2, 0), (2, 1)),
            ],
            sequenced=True,
        )
        sharp_wire = Wire(TopoDS.Wire(sharp_wire.wrapped.Reversed()))
        boundary = np.float64(1.0 / 3.0)
        distances = np.array(
            [
                np.nextafter(boundary, 0.0),
                boundary,
                np.nextafter(boundary, 1.0),
            ]
        )
        actual = sharp_wire.locations(distances)
        expected = [sharp_wire.location_at(distance) for distance in distances]
        for actual_location, expected_location in zip(actual, expected):
            self.assertAlmostEqual(
                actual_location.position, expected_location.position, 10
            )
            self.assertAlmostEqual(
                actual_location.x_axis.direction, expected_location.x_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.y_axis.direction, expected_location.y_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.z_axis.direction, expected_location.z_axis.direction, 10
            )

    def test_wire_locations_numpy_batch_closed_curves_and_boundaries(self):
        """Circle frames match an analytic oracle and edge boundaries match scalar."""
        radius = 2.0
        circle = Wire.make_circle(radius)
        fractions = np.array(
            [0.0, np.nextafter(0.25, 0.0), 0.25, np.nextafter(0.25, 1.0), 0.5, 1.0]
        )
        locations = circle.locations(fractions)
        for fraction, location in zip(fractions, locations):
            angle = 2 * math.pi * fraction
            self.assertAlmostEqual(
                location.position,
                (radius * math.cos(angle), radius * math.sin(angle), 0),
                10,
            )
            self.assertAlmostEqual(
                location.x_axis.direction,
                (-math.cos(angle), -math.sin(angle), 0),
                10,
            )
            self.assertAlmostEqual(location.y_axis.direction, (0, 0, 1), 10)
            self.assertAlmostEqual(
                location.z_axis.direction,
                (-math.sin(angle), math.cos(angle), 0),
                10,
            )

        boundary_wire = Wire(
            [
                Edge.make_line((0, 0), (2, 0)),
                Edge.make_line((2, 0), (2, 3)),
            ]
        )
        boundary = 2 / boundary_wire.length
        boundary_samples = np.array(
            [
                np.nextafter(boundary, 0.0),
                boundary,
                np.nextafter(boundary, 1.0),
            ]
        )
        actual = boundary_wire.locations(boundary_samples)
        expected = [
            boundary_wire.location_at(distance) for distance in boundary_samples
        ]
        for actual_location, expected_location in zip(actual, expected):
            self.assertAlmostEqual(
                actual_location.position, expected_location.position, 10
            )
            self.assertAlmostEqual(
                actual_location.x_axis.direction, expected_location.x_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.y_axis.direction, expected_location.y_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.z_axis.direction, expected_location.z_axis.direction, 10
            )

        mixed_radius = Wire(
            [
                Edge.make_circle(2, start_angle=0, end_angle=180),
                Edge.make_line((-2, 0), (-1, 0)),
                Edge.make_circle(1, start_angle=180, end_angle=360),
                Edge.make_line((1, 0), (2, 0)),
            ],
            sequenced=True,
        )
        mixed_distances = np.array([0.0, 0.1, 0.4, 0.7, 0.9, 1.0])
        mixed_actual = mixed_radius.locations(mixed_distances)
        mixed_expected = [
            mixed_radius.location_at(distance) for distance in mixed_distances
        ]
        for actual_location, expected_location in zip(mixed_actual, mixed_expected):
            self.assertAlmostEqual(
                actual_location.position, expected_location.position, 10
            )
            self.assertAlmostEqual(
                actual_location.x_axis.direction, expected_location.x_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.y_axis.direction, expected_location.y_axis.direction, 10
            )
            self.assertAlmostEqual(
                actual_location.z_axis.direction, expected_location.z_axis.direction, 10
            )

    def test_location_at_corrected_frenet(self):
        # A polyline with sharp corners — problematic for classic Frenet
        path = Polyline((0, 0), (10, 0), (10, 10), (0, 10))

        # Request multiple locations along the curve
        locations = [
            path.location_at(t, frame_method=FrameMethod.CORRECTED)
            for t in [0.0, 0.25, 0.5, 0.75, 1.0]
        ]
        # Ensure all locations were created and have consistent orientation
        self.assertTrue(
            all(
                locations[0].x_axis.direction == l.x_axis.direction
                for l in locations[1:]
            )
        )

        # Check that Z-axis is approximately orthogonal to X-axis
        for loc in locations:
            self.assertLess(abs(loc.z_axis.direction.dot(loc.x_axis.direction)), 1e-6)

        # Check continuity of rotation (not flipping wildly)
        # Check angle between x_axes doesn't flip more than ~90 degrees
        angles = []
        for i in range(len(locations) - 1):
            a1 = locations[i].x_axis.direction
            a2 = locations[i + 1].x_axis.direction
            angle = a1.get_angle(a2)
            angles.append(angle)
        self.assertTrue(all(abs(angle) < 90 for angle in angles))

    def test_project(self):
        target = Face.make_rect(10, 10, Plane.XY.rotated((0, 45, 0)))
        circle = Edge.make_circle(1).locate(Location((0, 0, 10)))
        ellipse: Wire = circle.project(target, (0, 0, -1))
        bbox = ellipse.bounding_box()
        self.assertAlmostEqual(bbox.min, (-1, -1, -1), 5)
        self.assertAlmostEqual(bbox.max, (1, 1, 1), 5)
        circle.wrapped = None
        with self.assertRaises(ValueError):
            circle.project(target, (0, 0, -1))

    def test_project2(self):
        target = Cylinder(1, 10).faces().filter_by(GeomType.PLANE, reverse=True)[0]
        square = Wire.make_rect(1, 1, Plane.YZ).locate(Location((10, 0, 0)))
        projections: list[Wire] = square.project(
            target, direction=(-1, 0, 0), closest=False
        )
        self.assertEqual(len(projections), 2)

    def test_is_forward(self):
        plate = Box(10, 10, 1) - Cylinder(1, 1)
        hole_edges = plate.edges().filter_by(GeomType.CIRCLE)
        self.assertTrue(hole_edges.sort_by(Axis.Z)[-1].is_forward)
        self.assertFalse(hole_edges.sort_by(Axis.Z)[0].is_forward)
        e = Edge.make_line((0, 0), (1, 0))
        e.wrapped = None
        with self.assertRaises(ValueError):
            e.is_forward

    def test_offset_2d(self):
        base_wire = Wire.make_polygon([(0, 0), (1, 0), (1, 1)], close=False)
        corner = base_wire.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[-1]
        base_wire = base_wire.fillet_2d(0.4, [corner])
        offset_wire = base_wire.offset_2d(0.1, side=Side.LEFT)
        self.assertTrue(offset_wire.is_closed)
        self.assertEqual(len(offset_wire.edges().filter_by(GeomType.LINE)), 6)
        self.assertEqual(len(offset_wire.edges().filter_by(GeomType.CIRCLE)), 2)
        offset_wire_right = base_wire.offset_2d(0.1, side=Side.RIGHT)
        self.assertAlmostEqual(
            offset_wire_right.edges()
            .filter_by(GeomType.CIRCLE)
            .sort_by(SortBy.RADIUS)[-1]
            .radius,
            0.5,
            4,
        )
        h_perimeter = Compound.make_text("h", font_size=10).wire()
        with self.assertRaises(RuntimeError):
            h_perimeter.offset_2d(-1)

        # Test for returned Edge - can't find a way to do this
        # base_edge = Edge.make_circle(10, start_angle=40, end_angle=50)
        # self.assertTrue(isinstance(offset_edge, Edge))
        # offset_edge = base_edge.offset_2d(2, side=Side.RIGHT, closed=False)
        # self.assertTrue(offset_edge.geom_type == GeomType.CIRCLE)
        # self.assertAlmostEqual(offset_edge.radius, 12, 5)
        # base_edge = Edge.make_line((0, 1), (1, 10))
        # offset_edge = base_edge.offset_2d(2, side=Side.RIGHT, closed=False)
        # self.assertTrue(isinstance(offset_edge, Edge))
        # self.assertTrue(offset_edge.geom_type == GeomType.LINE)
        # self.assertAlmostEqual(offset_edge.position_at(0).X, 3)

    def test_offset_2d_sides_on_any_plane(self):
        # Left and right are those of the plane the wire was made on: the
        # inside of a left turn is on the left
        corner = Polyline((0, 0), (10, 0), (10, 8))
        tilted = Plane.XY.rotated((30, 20, 0)).offset(5)
        for plane in (Plane.XY, Plane.XZ, Plane.YZ, tilted):
            with self.subTest(plane=plane):
                placed = plane * corner
                left = placed.offset_2d(1, side=Side.LEFT, closed=False)
                right = placed.offset_2d(1, side=Side.RIGHT, closed=False)
                self.assertAlmostEqual(left.length, 16, 5)
                self.assertAlmostEqual(right.length, 16 + 2 + math.pi / 2, 5)
                for offset_wire in (left, right):
                    for vertex in offset_wire.vertices():
                        self.assertAlmostEqual(
                            plane.to_local_coords(Vector(vertex)).Z, 0, 5
                        )

    def test_offset_2d_closed_wire_sides(self):
        # Issue #739: a closed wire has an inside and an outside, which are its
        # left and right according to the way round it runs
        counter_clockwise = Polyline((0, 0), (10, 0), (10, 8), (0, 8), (0, 0))
        clockwise = Polyline((0, 0), (0, 8), (10, 8), (10, 0), (0, 0))
        inside, outside = 2 * (9.5 + 7.5), 2 * (10 + 8) + 0.5 * math.pi
        for plane in (Plane.XY, Plane.XZ):
            for wire, left, right in (
                (counter_clockwise, inside, outside),
                (clockwise, outside, inside),
            ):
                with self.subTest(plane=plane, left=left):
                    placed = plane * wire
                    self.assertAlmostEqual(
                        placed.offset_2d(0.25, side=Side.LEFT).length, left, 5
                    )
                    self.assertAlmostEqual(
                        placed.offset_2d(0.25, side=Side.RIGHT).length, right, 5
                    )

    def test_offset_2d_collapsed_side(self):
        # Issue #1091: beyond its radius an arc has no offset on the inside
        arc = CenterArc((0, 0), 5, 0, 90)
        outside = arc.offset_2d(8, side=Side.RIGHT, closed=False)
        self.assertAlmostEqual(outside.length, 13 * math.pi / 2, 5)
        with self.assertRaisesRegex(ValueError, "LEFT side"):
            arc.offset_2d(8, side=Side.LEFT, closed=False)

    def test_offset_2d_straight_line(self):
        # Issue #604: a straight line is offset in the plane it was made on
        on_xz = Plane.XZ * Line((0, 0), (10, 10))
        around = on_xz.offset_2d(1)
        self.assertAlmostEqual(around.length, 2 * 200**0.5 + 2 * math.pi, 5)
        self.assertAlmostEqual(around.bounding_box().size.Y, 0, 5)

        left = (Plane.XZ * Line((0, 0), (10, 0))).offset_2d(
            1, side=Side.LEFT, closed=False
        )
        self.assertAlmostEqual(left @ 0.5, (5, 0, 1), 5)

        # a line with nothing to say which plane it is in takes one
        in_space = Edge.make_line((0, 0, 0), (10, 0, 10))
        given = in_space.offset_2d(1, plane=Plane.XZ)
        self.assertAlmostEqual(given.bounding_box().size.Y, 0, 5)
        # without one the kernel picks the plane, as it always has
        either_side = [
            in_space.offset_2d(1, side=side, closed=False)
            for side in (Side.LEFT, Side.RIGHT)
        ]
        for side_line in either_side:
            self.assertAlmostEqual(side_line.length, in_space.length, 5)
        apart = (either_side[0] @ 0.5 - either_side[1] @ 0.5).length
        self.assertAlmostEqual(apart, 2, 5)

    def test_offset_2d_builder_failure(self):
        """Verify that OCCT offset failures are reported before reading Shape()."""
        with patch("build123d.topology.one_d.BRepOffsetAPI_MakeOffset") as builder:
            offset_builder = builder.return_value
            offset_builder.IsDone.return_value = False
            offset_builder.Shape.side_effect = ValueError("Null TopoDS_Shape object")

            with self.assertRaisesRegex(RuntimeError, "2D offset failed.*0.1"):
                Wire.make_rect(1, 1).offset_2d(0.1)

            offset_builder.Shape.assert_not_called()

    def test_common_plane(self):
        # Straight and circular lines
        l = Edge.make_line((0, 0, 0), (5, 0, 0))
        c = Edge.make_circle(2, Plane.XZ, -90, 90)
        common = l.common_plane(c)
        self.assertAlmostEqual(common.z_dir.X, 0, 5)
        self.assertAlmostEqual(abs(common.z_dir.Y), 1, 5)  # the direction isn't known
        self.assertAlmostEqual(common.z_dir.Z, 0, 5)

        # Co-axial straight lines
        l1 = Edge.make_line((0, 0), (1, 1))
        l2 = Edge.make_line((0.25, 0.25), (0.75, 0.75))
        common = l1.common_plane(l2)
        # the z_dir isn't know
        self.assertAlmostEqual(common.x_dir.Z, 0, 5)

        # Parallel lines
        l1 = Edge.make_line((0, 0), (1, 0))
        l2 = Edge.make_line((0, 1), (1, 1))
        common = l1.common_plane(l2)
        self.assertAlmostEqual(common.z_dir.X, 0, 5)
        self.assertAlmostEqual(common.z_dir.Y, 0, 5)
        self.assertAlmostEqual(abs(common.z_dir.Z), 1, 5)  # the direction isn't known

        # Many lines
        common = Edge.common_plane(*Wire.make_rect(10, 10).edges())
        self.assertAlmostEqual(common.z_dir.X, 0, 5)
        self.assertAlmostEqual(common.z_dir.Y, 0, 5)
        self.assertAlmostEqual(abs(common.z_dir.Z), 1, 5)  # the direction isn't known

        # Wire and Edges
        c = Wire.make_circle(1, Plane.YZ)
        lines = Wire.make_rect(2, 2, Plane.YZ).edges()
        common = c.common_plane(*lines)
        self.assertAlmostEqual(abs(common.z_dir.X), 1, 5)  # the direction isn't known
        self.assertAlmostEqual(common.z_dir.Y, 0, 5)
        self.assertAlmostEqual(common.z_dir.Z, 0, 5)

    def test_edge_volume(self):
        edge = Edge.make_line((0, 0), (1, 1))
        self.assertAlmostEqual(edge.volume, 0, 5)

    def test_edge_mass(self):
        edge = Edge.make_line((0, 0), (1, 1))
        self.assertAlmostEqual(edge.mass(), 0, 5)

    def test_wire_volume(self):
        wire = Wire.make_rect(1, 1)
        self.assertAlmostEqual(wire.volume, 0, 5)

    def test_wire_mass(self):
        wire = Wire.make_rect(1, 1)
        self.assertAlmostEqual(wire.mass(), 0, 5)

    def test_edges(self):
        box = Solid.make_box(1, 1, 1)
        top_x = box.faces().sort_by(Axis.Z)[-1].edges().sort_by(Axis.X)[-1]
        self.assertEqual(top_x.topo_parent, box)
        self.assertTrue(isinstance(top_x, Edge))
        self.assertAlmostEqual(top_x.center(), (1, 0.5, 1), 5)

    def test_edges_topo_parent(self):
        phone_case_plan = Face.make_rect(80, 150) - Face.make_rect(
            25, 25, Plane((-20, 55))
        )
        phone_case = extrude(phone_case_plan, 2)
        window_edges = phone_case.faces().sort_by(Axis.Z)[-1].inner_wires()[0].edges()
        for e in window_edges:
            self.assertEqual(e.topo_parent, phone_case)
        phone_case_f = fillet(window_edges, 1)
        self.assertLess(phone_case_f.volume, phone_case.volume)
        perimeter = phone_case_f.faces().sort_by(Axis.Z)[-1].outer_wire().edges()
        for e in perimeter:
            self.assertEqual(e.topo_parent, phone_case_f)
        phone_case_ff = fillet(perimeter, 1)
        self.assertLess(phone_case_ff.volume, phone_case_f.volume)

    def test_edges_topo_path(self):
        """An extracted shape records the whole route it was selected by, so
        an edge knows the face it was picked off as well as the solid."""
        box = Solid.make_box(1, 1, 1)
        face = box.faces().sort_by(Axis.X)[-1]
        edge = face.edges().sort_by(Axis.Y)[0]
        self.assertEqual(len(edge.topo_path), 2)
        self.assertEqual(edge.topo_parent, box)
        self.assertEqual(edge.topo_owner, face)
        self.assertEqual(face.topo_parent, box)
        self.assertEqual(face.topo_owner, box)

        vertex = edge.vertices()[0]
        self.assertEqual([type(s) for s in vertex.topo_path], [Solid, Face, Edge])
        self.assertEqual(vertex.topo_parent, box)
        self.assertEqual(vertex.topo_owner, edge)

    def test_topo_path_survives_copying(self):
        """Provenance points outside the copy, so it is carried by reference
        rather than duplicated along with the shape."""
        box = Solid.make_box(1, 1, 1)
        edge = box.faces().sort_by(Axis.X)[-1].edges()[0]
        for duplicate in (copy.copy(edge), copy.deepcopy(edge)):
            self.assertEqual(len(duplicate.topo_path), 2)
            self.assertTrue(
                all(a is b for a, b in zip(duplicate.topo_path, edge.topo_path))
            )

    def test_topo_parent_assignment_replaces_the_path(self):
        box = Solid.make_box(1, 1, 1)
        edge = box.faces().sort_by(Axis.X)[-1].edges()[0]
        edge.topo_parent = box
        self.assertEqual(edge.topo_path, (box,))
        self.assertEqual(edge.topo_owner, box)
        edge.topo_parent = None
        self.assertEqual(edge.topo_path, ())
        self.assertIsNone(edge.topo_owner)

    def test_is_closed(self):
        self.assertTrue(Edge.make_circle(1).is_closed)
        self.assertTrue(Face.make_rect(1, 1).outer_wire().is_closed)
        self.assertFalse(Edge.make_line((0, 0), (1, 0)).is_closed)
        e = Edge.make_circle(1)
        e.wrapped = None
        with self.assertRaises(ValueError):
            e.is_closed

    def test_add(self):
        e = Edge.make_line((0, 0), (1, 0))
        e_plus = e + None
        self.assertTrue(e.is_same(e_plus))

    def test_derivative_at(self):
        self.assertAlmostEqual(
            Edge.make_line((0, 0), (1, 0)).derivative_at((0, 0), 2), (0, 0, 0), 5
        )

    def test_project_to_viewport(self):
        line = Edge.make_line((0, 0), (1, 0))
        line.wrapped = None
        with self.assertRaises(ValueError):
            line.project_to_viewport((0, 0, 0))

    def test_split(self):
        # nothing to split leaves nothing on either side
        self.assertTrue(Edge().split(Plane.XZ.offset(0.5)).is_empty)
        top, bottom = Edge().split(Plane.XZ.offset(0.5), keep=Keep.BOTH)
        self.assertTrue(top.is_empty and bottom.is_empty)
        self.assertEqual(Edge().split(Plane.XZ.offset(0.5), keep=Keep.ALL), [])
        with self.assertRaisesRegex(ValueError, "empty tool"):
            Edge.make_line((0, 0), (1, 0)).split(Face())

    def test_extrude(self):
        pnt = Vertex(1, 0, 0)
        pnt.wrapped = None
        with self.assertRaises(ValueError):
            Edge.extrude(pnt, (0, 0, 1))


class TestCurvatureComb(unittest.TestCase):
    def test_raises_if_not_on_XY(self):
        line_xz = Polyline((0, 0, 0), (1, 0, 0), (0, 0, 1))
        with self.assertRaises(ValueError):
            _ = line_xz.curvature_comb()

    def test_empty_curve(self):
        c = CenterArc((0, 0), 1, 0, 360)
        c.wrapped = None
        with self.assertRaises(ValueError):
            c.curvature_comb()

    def test_circle_constant_height_and_count(self):
        radius = 5.0
        count = 64
        max_tooth = 2.0

        # A closed circle in the XY plane
        c = CenterArc((0, 0), radius, 0, 360)
        comb = c.curvature_comb(count=count, max_tooth_size=max_tooth)

        # For a closed curve, endpoint is excluded but the method still returns `count` samples.
        self.assertEqual(len(comb), count)

        # On a circle, kappa = 1/R => all teeth should have the same length = max_tooth
        lengths = [edge.length for edge in comb]
        self.assertTrue(all(abs(L - max_tooth) <= TOLERANCE for L in lengths))

        # Direction check: teeth should be radial (perpendicular to tangent),
        # i.e., aligned with (start_point - center). For Circle(...) center is (0,0,0).
        center = Vector(0, 0, 0)
        for edge in comb[:: max(1, len(comb) // 8)]:  # sample a few
            p0 = edge.position_at(0.0)
            p1 = edge.position_at(1.0)
            tooth_dir = (p1 - p0).normalized()
            radial = (p0 - center).normalized()
            # allow either direction (outward/inward), check colinearity
            cross_len = tooth_dir.cross(radial).length
            self.assertLessEqual(cross_len, 1e-3)

    def test_line_near_zero_teeth_and_count(self):
        # Straight segment in XY => curvature = 0 everywhere
        line = Line((0, 0), (10, 0))

        count = 25
        comb = line.curvature_comb(count=count, max_tooth_size=3.0)

        self.assertEqual(len(comb), 0)  # They are 0 length so skipped

    def test_open_arc_count_and_variation(self):
        # Open arc: teeth count == requested count; lengths not constant in general
        arc = CenterArc((0, 0), 5, 0, 180)  # open, CCW half-circle
        count = 40
        comb = arc.curvature_comb(count=count, max_tooth_size=1.0)
        self.assertEqual(len(comb), count)
        # For a circular arc, curvature is constant, so lengths should still be constant
        lengths = [e.length for e in comb]
        self.assertLessEqual(max(lengths) - min(lengths), 1e-6)


if __name__ == "__main__":
    unittest.main()
