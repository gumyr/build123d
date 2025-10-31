"""

build123d BuildLine tests

name: build_line_tests.py
by:   Gumyr
date: July 27th 2022

desc: Unit tests for the build123d build_line module

license:

    Copyright 2022 Gumyr

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

import unittest
from math import sqrt, pi
from build123d import *


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class BuildLineTests(unittest.TestCase):
    """Test the BuildLine Builder derived class"""

    def test_basic_functions(self):
        """Test creating a line and returning properties and methods"""
        with BuildLine() as test:
            l1 = Line((0, 0), (1, 1))
            TangentArc((1, 1), (2, 0), tangent=l1 % 1)
            self.assertEqual(len(test.vertices()), 3)
            self.assertEqual(len(test.edges()), 2)
            self.assertEqual(len(test.vertices(Select.LAST)), 2)
            self.assertEqual(len(test.edges(Select.LAST)), 1)
            self.assertEqual(len(test.edges(Select.ALL)), 2)

    def test_canadian_flag(self):
        """Test many of the features by creating a Canadian flag maple leaf"""
        with BuildSketch() as leaf:
            with BuildLine() as outline:
                l1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
                l2 = Polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
                RadiusArc(l1 @ 1, l2 @ 0, 0.0271)
                l3 = Polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
                TangentArc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
                l4 = Polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
                SagittaArc(l3 @ 1, l4 @ 0, 0.003)
                l5 = Polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
                ThreePointArc(
                    l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0
                )
                l6 = Polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
                Spline(
                    l5 @ 1, l6 @ 0, tangents=(l5 % 1, l6 % 0), tangent_scalars=(2, 2)
                )
                l7 = Line((0.0692, 0.7808), (0.0000, 0.9167))
                TangentArc(l6 @ 1, l7 @ 0, tangent=l6 % 1)
                mirror(outline.edges(), Plane.YZ)
            make_face(leaf.pending_edges)
        self.assertAlmostEqual(leaf.sketch.area, 0.2741600685288115, 5)

    def test_three_d(self):
        """Test 3D lines with a helix"""
        with BuildLine() as roller_coaster:
            powerup = Spline(
                (0, 0, 0),
                (50, 0, 50),
                (100, 0, 0),
                tangents=((1, 0, 0), (1, 0, 0)),
                tangent_scalars=(0.5, 2),
            )
            corner = RadiusArc(powerup @ 1, (100, 60, 0), -30)
            screw = Helix(75, 150, 15, center=(75, 40, 15), direction=(-1, 0, 0))
            Spline(corner @ 1, screw @ 0, tangents=(corner % 1, screw % 0))
            Spline(
                screw @ 1,
                (-100, 30, 10),
                powerup @ 0,
                tangents=(screw % 1, powerup % 0),
            )
        self.assertAlmostEqual(roller_coaster.wires()[0].length, 678.983628932414, 5)

    def test_bezier(self):
        pts = [(0, 0), (20, 20), (40, 0), (0, -40), (-60, 0), (0, 100), (100, 0)]
        wts = [1.0, 1.0, 2.0, 3.0, 4.0, 2.0, 1.0]
        with BuildLine() as bz:
            b1 = Bezier(*pts, weights=wts)
        self.assertAlmostEqual(bz.wires()[0].length, 225.86389406824566, 5)
        self.assertTrue(isinstance(b1, Edge))

    def test_double_tangent_arc(self):
        l1 = Line((10, 0), (30, 20))
        l2 = DoubleTangentArc((0, 5), (1, 0), l1)
        _, p1, p2 = l1.distance_to_with_closest_points(l2)
        self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
        self.assertTupleAlmostEquals(
            tuple(l1.tangent_at(p1)), tuple(l2.tangent_at(p2)), 5
        )

        l3 = Line((10, 0), (20, -10))
        l4 = DoubleTangentArc((0, 0), (1, 0), l3)
        _, p1, p2 = l3.distance_to_with_closest_points(l4)
        self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
        self.assertTupleAlmostEquals(
            tuple(l3.tangent_at(p1)), tuple(l4.tangent_at(p2)), 5
        )

        with BuildLine() as test:
            l5 = Polyline((20, -10), (10, 0), (20, 10))
            l6 = DoubleTangentArc((0, 0), (1, 0), l5, keep=Keep.BOTTOM)
        _, p1, p2 = l5.distance_to_with_closest_points(l6)
        self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
        self.assertTupleAlmostEquals(
            tuple(l5.tangent_at(p1)), tuple(l6.tangent_at(p2) * -1), 5
        )

        # l7 = Spline((15, 5), (5, 0), (15, -5), tangents=[(-1, 0), (1, 0)])
        # l8 = DoubleTangentArc((0, 0, 0), (1, 0, 0), l7, keep=Keep.BOTH)
        # self.assertEqual(len(l8.edges()), 2)

        l9 = EllipticalCenterArc((15, 0), 10, 5, start_angle=90, end_angle=270)
        # l10 = DoubleTangentArc((0, 0, 0), (1, 0, 0), l9, keep=Keep.BOTH)
        # self.assertEqual(len(l10.edges()), 2)
        # self.assertTrue(isinstance(l10, Edge))
        with self.assertRaises(ValueError):
            l10 = DoubleTangentArc((0, 0, 0), (1, 0, 0), l9, keep=Keep.BOTH)

        with self.assertRaises(ValueError):
            DoubleTangentArc((0, 0, 0), (0, 0, 1), l9)

        l11 = Line((10, 0), (20, 0))
        with self.assertRaises(RuntimeError):
            DoubleTangentArc((0, 0, 0), (1, 0, 0), l11)

    def test_elliptical_start_arc(self):
        with self.assertRaises(RuntimeError):
            with BuildLine():
                EllipticalStartArc((1, 0), (0, 0.5), 1, 0.5, 0)

    def test_elliptical_center_arc(self):
        with BuildLine() as el:
            EllipticalCenterArc((0, 0), 10, 5, 0, 180)
        bbox = el.line.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)

        e1 = EllipticalCenterArc((0, 0), 10, 5, 0, 180)
        bbox = e1.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)
        self.assertTrue(isinstance(e1, Edge))

    def test_filletpolyline(self):
        with BuildLine(Plane.YZ):
            p = FilletPolyline(
                (0, 0, 0), (0, 10, 2), (0, 10, 10), (5, 20, 10), radius=2
            )
        self.assertEqual(len(p.edges()), 5)
        self.assertEqual(len(p.edges().filter_by(GeomType.CIRCLE)), 2)
        self.assertEqual(len(p.edges().filter_by(GeomType.LINE)), 3)

        with self.assertRaises(ValueError):
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (0, 10),
                radius=(1, 2, 3, 0),
                close=True,
            )

        with self.assertRaises(ValueError):
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (0, 10),
                radius=-1,
                close=True,
            )

        with self.assertRaises(ValueError):
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (0, 10),
                radius=(1, 2),
                close=True,
            )

        with BuildLine(Plane.YZ):
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (0, 10),
                radius=(1, 2, 3, 4),
                close=True,
            )
        self.assertEqual(len(p.edges()), 8)
        self.assertEqual(len(p.edges().filter_by(GeomType.CIRCLE)), 4)
        self.assertEqual(len(p.edges().filter_by(GeomType.LINE)), 4)

        with BuildLine(Plane.YZ):
            p = FilletPolyline(
                (0, 0, 0), (0, 0, 10), (10, 2, 10), (10, 0, 0), radius=2, close=True
            )
        self.assertEqual(len(p.edges()), 8)
        self.assertEqual(len(p.edges().filter_by(GeomType.CIRCLE)), 4)
        self.assertEqual(len(p.edges().filter_by(GeomType.LINE)), 4)
        self.assertTrue(isinstance(p, Wire))

        with self.assertRaises(ValueError):
            FilletPolyline((0, 0), radius=0.1)
        with self.assertRaises(ValueError):
            FilletPolyline((0, 0), (1, 0), (1, 1), radius=-1)

    def test_intersecting_line(self):
        with BuildLine():
            l1 = Line((0, 0), (10, 0))
            l2 = IntersectingLine((5, 10), (0, -1), l1)
        self.assertAlmostEqual(l2.length, 10, 5)

        l3 = Line((0, 0), (10, 10))
        l4 = IntersectingLine((0, 10), (1, -1), l3)
        self.assertTupleAlmostEquals(l4 @ 1, (5, 5, 0), 5)
        self.assertTrue(isinstance(l4, Edge))

        with self.assertRaises(ValueError):
            IntersectingLine((0, 10), (1, 1), l3)

    def test_jern_arc(self):
        with BuildLine() as jern:
            j1 = JernArc((1, 0), (0, 1), 1, 90)
        self.assertTupleAlmostEquals(jern.line @ 1, (0, 1, 0), 5)
        self.assertAlmostEqual(j1.radius, 1)
        self.assertAlmostEqual(j1.length, pi / 2)

        with BuildLine(Plane.XY.offset(1)) as offset_l:
            off1 = JernArc((1, 0), (0, 1), 1, 90)
        self.assertTupleAlmostEquals(offset_l.line @ 1, (0, 1, 1), 5)
        self.assertAlmostEqual(off1.radius, 1)
        self.assertAlmostEqual(off1.length, pi / 2)

        plane_iso = Plane(origin=(0, 0, 0), x_dir=(1, 1, 0), z_dir=(1, -1, 1))
        with BuildLine(plane_iso) as iso_l:
            iso1 = JernArc((0, 0), (0, 1), 1, 180)
        self.assertTupleAlmostEquals(iso_l.line @ 1, (-sqrt(2), -sqrt(2), 0), 5)
        self.assertAlmostEqual(iso1.radius, 1)
        self.assertAlmostEqual(iso1.length, pi)

        with BuildLine() as full_l:
            l1 = JernArc(start=(0, 0, 0), tangent=(1, 0, 0), radius=1, arc_size=360)
            l2 = JernArc(start=(0, 0, 0), tangent=(1, 0, 0), radius=1, arc_size=300)
        self.assertTrue(l1.is_closed)
        self.assertFalse(l2.is_closed)
        circle_face = Face(Wire([l1]))
        self.assertAlmostEqual(circle_face.area, pi, 5)
        self.assertTupleAlmostEquals(circle_face.center(), (0, 1, 0), 5)
        self.assertTupleAlmostEquals(l1.vertex(), l2.start, 5)

        l1 = JernArc((0, 0), (1, 0), 1, 90)
        self.assertTupleAlmostEquals(l1 @ 1, (1, 1, 0), 5)
        self.assertTrue(isinstance(l1, Edge))

    def test_polar_line(self):
        """Test 2D and 3D polar lines"""
        with BuildLine():
            a1 = PolarLine((0, 0), sqrt(2), 45)
            d1 = PolarLine((0, 0), sqrt(2), direction=(1, 1))
        self.assertTupleAlmostEquals(a1 @ 1, (1, 1, 0), 5)
        self.assertTupleAlmostEquals(a1 @ 1, d1 @ 1, 5)
        self.assertTrue(isinstance(a1, Edge))
        self.assertTrue(isinstance(d1, Edge))

        with BuildLine():
            a2 = PolarLine((0, 0), 1, 30)
            d2 = PolarLine((0, 0), 1, direction=(sqrt(3), 1))
        self.assertTupleAlmostEquals(a2 @ 1, (sqrt(3) / 2, 0.5, 0), 5)
        self.assertTupleAlmostEquals(a2 @ 1, d2 @ 1, 5)

        with BuildLine():
            a3 = PolarLine((0, 0), 1, 150)
            d3 = PolarLine((0, 0), 1, direction=(-sqrt(3), 1))
        self.assertTupleAlmostEquals(a3 @ 1, (-sqrt(3) / 2, 0.5, 0), 5)
        self.assertTupleAlmostEquals(a3 @ 1, d3 @ 1, 5)

        with BuildLine():
            a4 = PolarLine((0, 0), 1, angle=30, length_mode=LengthMode.HORIZONTAL)
            d4 = PolarLine(
                (0, 0), 1, direction=(sqrt(3), 1), length_mode=LengthMode.HORIZONTAL
            )
        self.assertTupleAlmostEquals(a4 @ 1, (1, 1 / sqrt(3), 0), 5)
        self.assertTupleAlmostEquals(a4 @ 1, d4 @ 1, 5)

        with BuildLine(Plane.XZ):
            a5 = PolarLine((0, 0), 1, angle=30, length_mode=LengthMode.VERTICAL)
            d5 = PolarLine(
                (0, 0), 1, direction=(sqrt(3), 1), length_mode=LengthMode.VERTICAL
            )
        self.assertTupleAlmostEquals(a5 @ 1, (sqrt(3), 0, 1), 5)
        self.assertTupleAlmostEquals(a5 @ 1, d5 @ 1, 5)

        with self.assertRaises(ValueError):
            PolarLine((0, 0), 1)

    def test_spline(self):
        """Test spline with no tangents"""
        with BuildLine() as test:
            s1 = Spline((0, 0), (1, 1), (2, 0))
        self.assertTupleAlmostEquals(test.edges()[0] @ 1, (2, 0, 0), 5)
        self.assertTrue(isinstance(s1, Edge))

    def test_radius_arc(self):
        """Test center arc as arc and circle"""
        with BuildSketch() as s:
            c = Circle(10)

        e = c.edges()[0]
        r = e.radius
        p1, p2 = e @ 0.3, e @ 0.9

        with BuildLine() as l:
            arc1 = RadiusArc(p1, p2, r)
            self.assertAlmostEqual(arc1.length, 2 * r * pi * 0.4, 6)
            self.assertAlmostEqual(arc1.bounding_box().max.X, c.bounding_box().max.X)

            arc2 = RadiusArc(p1, p2, r, short_sagitta=False)
            self.assertAlmostEqual(arc2.length, 2 * r * pi * 0.6, 6)
            self.assertAlmostEqual(arc2.bounding_box().min.X, c.bounding_box().min.X)

            arc3 = RadiusArc(p1, p2, -r)
            self.assertAlmostEqual(arc3.length, 2 * r * pi * 0.4, 6)
            self.assertGreater(arc3.bounding_box().min.X, c.bounding_box().min.X)
            self.assertLess(arc3.bounding_box().min.X, c.bounding_box().max.X)

            arc4 = RadiusArc(p1, p2, -r, short_sagitta=False)
            self.assertAlmostEqual(arc4.length, 2 * r * pi * 0.6, 6)
            self.assertGreater(arc4.bounding_box().max.X, c.bounding_box().max.X)

        self.assertTrue(isinstance(arc1, Edge))

    def test_sagitta_arc(self):
        l1 = SagittaArc((0, 0), (1, 0), 0.1)
        self.assertAlmostEqual((l1 @ 0.5).Y, 0.1, 5)
        self.assertTrue(isinstance(l1, Edge))

    def test_center_arc(self):
        """Test center arc as arc and circle"""
        with BuildLine() as arc:
            CenterArc((0, 0), 10, 0, 180)
        self.assertTupleAlmostEquals(arc.edges()[0] @ 1, (-10, 0, 0), 5)
        with BuildLine() as arc:
            CenterArc((0, 0), 10, 0, 360)
        self.assertTupleAlmostEquals(arc.edges()[0] @ 0, arc.edges()[0] @ 1, 5)
        with BuildLine(Plane.XZ) as arc:
            CenterArc((0, 0), 10, 0, 360)
        self.assertTrue(Face(arc.wires()[0]).is_coplanar(Plane.XZ))

        with BuildLine(Plane.XZ) as arc:
            CenterArc((-100, 0), 100, -45, 90)
        self.assertTupleAlmostEquals(arc.edges()[0] @ 0.5, (0, 0, 0), 5)

        arc = CenterArc((-100, 0), 100, 0, 360)
        self.assertTrue(Face(Wire([arc])).is_coplanar(Plane.XY))
        self.assertTupleAlmostEquals(arc.bounding_box().max, (0, 100, 0), 5)
        self.assertTrue(isinstance(arc, Edge))

    def test_polyline(self):
        """Test edge generation and close"""
        with BuildLine() as test:
            p1 = Polyline((0, 0), (1, 0), (1, 1), (0, 1), close=True)
        self.assertAlmostEqual(
            (test.edges()[0] @ 0 - test.edges()[-1] @ 1).length, 0, 5
        )
        self.assertEqual(len(test.edges()), 4)
        self.assertAlmostEqual(test.wires()[0].length, 4)
        self.assertTrue(isinstance(p1, Wire))

    def test_polyline_with_list(self):
        """Test edge generation and close"""
        with BuildLine() as test:
            Polyline((0, 0), [(1, 0), (1, 1)], (0, 1), close=True)
        self.assertAlmostEqual(
            (test.edges()[0] @ 0 - test.edges()[-1] @ 1).length, 0, 5
        )
        self.assertEqual(len(test.edges()), 4)
        self.assertAlmostEqual(test.wires()[0].length, 4)

    def test_point_arc_tangent_line(self):
        """Test tangent line between point and arc

        Considerations:
        - Should produce a GeomType.LINE located on and tangent to arc
        - Should start on point
        - Lines should always have equal length as long as point is same distance
        - LEFT lines should always end on end arc left of midline (angle > 0)
        - Arc should be GeomType.CIRCLE
        - Point and arc must be coplanar
        - Cannot make tangent from point inside arc
        """
        # Test line properties in algebra mode
        point = (0, 0)
        separation = 10
        end_point = (0, separation)
        end_r = 5
        end_arc = CenterArc(end_point, end_r, 0, 360)

        lines = []
        for side in [Side.LEFT, Side.RIGHT]:
            l1 = PointArcTangentLine(point, end_arc, side=side)
            self.assertEqual(l1.geom_type, GeomType.LINE)

            self.assertTupleAlmostEquals(tuple(point), tuple(l1 @ 0), 5)

            _, p1, p2 = end_arc.distance_to_with_closest_points(l1 @ 1)
            self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
            self.assertAlmostEqual(
                end_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
            )
            lines.append(l1)

        self.assertAlmostEqual(lines[0].length, lines[1].length, 5)

        # Test in off-axis builder mode at multiple angles and compare to prev result
        workplane = Plane.XY.rotated((45, 45, 45))
        with BuildLine(workplane):
            end_center = workplane.from_local_coords(end_point)
            point_arc = CenterArc(end_center, separation, 0, 360)
            end_arc = CenterArc(end_center, end_r, 0, 360)

            points = [1, 2, 3, 5, 7, 11, 13]
            for point in points:
                start_point = point_arc @ (point / 16)
                mid_vector = end_center - start_point
                mid_perp = mid_vector.cross(workplane.z_dir)
                for side in [Side.LEFT, Side.RIGHT]:
                    l2 = PointArcTangentLine(start_point, end_arc, side=side)
                    self.assertAlmostEqual(lines[0].length, l2.length, 5)

                    # Check side
                    coincident_dir = mid_perp.dot(l2 @ 1 - end_center)
                    if side == Side.LEFT:
                        self.assertLess(coincident_dir, 0)

                    elif side == Side.RIGHT:
                        self.assertGreater(coincident_dir, 0)

        # Error Handling
        bad_type = Line((0, 0), (0, 10))
        with self.assertRaises(ValueError):
            PointArcTangentLine(start_point, bad_type)

        with self.assertRaises(ValueError):
            PointArcTangentLine(start_point, CenterArc((0, 1, 1), end_r, 0, 360))

        with self.assertRaises(ValueError):
            PointArcTangentLine(start_point, CenterArc((0, 1), end_r, 0, 360))

    def test_point_arc_tangent_arc(self):
        """Test tangent arc between point and arc

        Considerations:
        - Should produce a GeomType.CIRCLE located on and tangent to arc
        - Should start on point tangent to direction
        - LEFT lines should always end on end arc left of midline (angle > 0)
        - Tangent should be GeomType.CIRCLE
        - Point and arc must be coplanar
        - Cannot make tangent arc from point/direction already tangent with arc
        - (Due to minimizer limit) Cannot make tangent with very large radius
        """
        # Test line properties in algebra mode
        start_point = (0, 0)
        direction = (0, 1)
        separation = 10
        end_point = (0, separation)
        end_r = 5
        end_arc = CenterArc(end_point, end_r, 0, 360)
        lines = []
        for side in [Side.LEFT, Side.RIGHT]:
            l1 = PointArcTangentArc(start_point, direction, end_arc, side=side)
            self.assertEqual(l1.geom_type, GeomType.CIRCLE)

            self.assertTupleAlmostEquals(tuple(start_point), tuple(l1 @ 0), 5)
            self.assertAlmostEqual(Vector(direction).cross(l1 % 0).length, 0, 5)

            _, p1, p2 = end_arc.distance_to_with_closest_points(l1 @ 1)
            self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
            self.assertAlmostEqual(
                end_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
            )
            lines.append(l1)

        # Test in off-axis builder mode at multiple angles and compare to prev result
        workplane = Plane.XY.rotated((45, 45, 45))
        with BuildLine(workplane):
            end_center = workplane.from_local_coords(end_point)
            end_arc = CenterArc(end_center, end_r, 0, 360)

            # Assortment of points in different regimes
            flip = separation * 2
            value = flip - end_r
            points = [
                start_point,
                (end_r - 0.1, 0),
                (-end_r - 0.1, 0),
                (end_r + 0.1, flip),
                (-end_r + 0.1, flip),
                (0, flip),
                (flip, flip),
                (-flip, -flip),
                (value, -value),
                (-value, value),
            ]
            for point in points:
                mid_vector = end_center - point
                mid_perp = mid_vector.cross(workplane.z_dir)
                centers = {}
                for side in [Side.LEFT, Side.RIGHT]:
                    l2 = PointArcTangentArc(point, direction, end_arc, side=side)

                    centers[side] = l2.center()
                    if point == start_point:
                        self.assertAlmostEqual(lines[0].length, l2.length, 5)

                # Rudimentary side check. Somewhat surprised this works
                center_dif = centers[Side.RIGHT] - centers[Side.LEFT]
                self.assertGreater(mid_perp.dot(center_dif), 0)

        # Error Handling
        end_arc = CenterArc(end_point, end_r, 0, 360)

        # GeomType
        bad_type = Line((0, 0), (0, 10))
        with self.assertRaises(ValueError):
            PointArcTangentArc(start_point, direction, bad_type)

        # Coplanar
        with self.assertRaises(ValueError):
            arc = CenterArc((0, 1, 1), end_r, 0, 360)
            PointArcTangentArc(start_point, direction, arc)

        # Positional
        with self.assertRaises(ValueError):
            PointArcTangentArc((end_r, 0), direction, end_arc, side=Side.RIGHT)

        with self.assertRaises(RuntimeError):
            PointArcTangentArc(
                (end_r - 0.00001, 0), direction, end_arc, side=Side.RIGHT
            )

    def test_arc_arc_tangent_line(self):
        """Test tangent line between arcs

        Considerations:
        - Should produce a GeomType.LINE located on and tangent to arcs
        - INSIDE arcs cross midline of arc centers
        - INSIDE lines should always have equal length as long as arcs are same distance
        - OUTSIDE lines should always have equal length as long as arcs are same distance
        - LEFT lines should always start on start arc left of midline (angle > 0)
        - Tangent should be GeomType.CIRCLE
        - Arcs must be coplanar
        - Cannot make tangent for concentric arcs
        - Cannot make INSIDE tangent from overlapping or tangent arcs
        """
        # Test line properties in algebra mode
        start_r = 2
        end_r = 5
        separation = 10
        start_point = (0, 0)
        end_point = (0, separation)

        start_arc = CenterArc(start_point, start_r, 0, 360)
        end_arc = CenterArc(end_point, end_r, 0, 360)
        lines = []
        for keep in [Keep.INSIDE, Keep.OUTSIDE]:
            for side in [Side.LEFT, Side.RIGHT]:
                l1 = ArcArcTangentLine(start_arc, end_arc, side=side, keep=keep)
                self.assertEqual(l1.geom_type, GeomType.LINE)

                # Check coincidence, tangency with each arc
                _, p1, p2 = start_arc.distance_to_with_closest_points(l1 @ 0)
                self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
                self.assertAlmostEqual(
                    start_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
                )
                _, p1, p2 = end_arc.distance_to_with_closest_points(l1 @ 1)
                self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
                self.assertAlmostEqual(
                    end_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
                )
                lines.append(l1)

            self.assertAlmostEqual(lines[-2].length, lines[-1].length, 5)

        # Test in off-axis builder mode at multiple angles and compare to prev result
        workplane = Plane.XY.rotated((45, 45, 45))
        with BuildLine(workplane):
            end_center = workplane.from_local_coords(end_point)
            point_arc = CenterArc(end_center, separation, 0, 360)
            end_arc = CenterArc(end_center, end_r, 0, 360)

            points = [1, 2, 3, 5, 7, 11, 13]
            for point in points:
                start_center = point_arc @ (point / 16)
                start_arc = CenterArc(start_center, start_r, 0, 360)
                midline = Line(start_center, end_center)
                mid_vector = end_center - start_center
                mid_perp = mid_vector.cross(workplane.z_dir)
                for keep in [Keep.INSIDE, Keep.OUTSIDE]:
                    for side in [Side.LEFT, Side.RIGHT]:
                        l2 = ArcArcTangentLine(start_arc, end_arc, side=side, keep=keep)

                        # Check length and cross/does not cross midline
                        d1 = midline.distance_to(l2)
                        if keep == Keep.INSIDE:
                            self.assertAlmostEqual(d1, 0, 5)
                            self.assertAlmostEqual(lines[0].length, l2.length, 5)

                        elif keep == Keep.OUTSIDE:
                            self.assertNotAlmostEqual(d1, 0, 5)
                            self.assertAlmostEqual(lines[2].length, l2.length, 5)

                        # Check side of midline
                        _, _, p2 = start_arc.distance_to_with_closest_points(l2)
                        coincident_dir = mid_perp.dot(p2 - start_center)
                        if side == Side.LEFT:
                            self.assertLess(coincident_dir, 0)

                        elif side == Side.RIGHT:
                            self.assertGreater(coincident_dir, 0)

        ## Error Handling
        start_arc = CenterArc(start_point, start_r, 0, 360)
        end_arc = CenterArc(end_point, end_r, 0, 360)

        # GeomType
        bad_type = Line((0, 0), (0, 10))
        with self.assertRaises(ValueError):
            ArcArcTangentLine(start_arc, bad_type)

        with self.assertRaises(ValueError):
            ArcArcTangentLine(bad_type, end_arc)

        # Coplanar
        with self.assertRaises(ValueError):
            ArcArcTangentLine(CenterArc((0, 0, 1), 5, 0, 360), end_arc)

        # Position conditions
        with self.assertRaises(ValueError):
            ArcArcTangentLine(CenterArc(end_point, start_r, 0, 360), end_arc)

        with self.assertRaises(ValueError):
            arc = CenterArc(start_point, separation - end_r, 0, 360)
            ArcArcTangentLine(arc, end_arc, keep=Keep.INSIDE)

        with self.assertRaises(ValueError):
            arc = CenterArc(start_point, separation - end_r + 1, 0, 360)
            ArcArcTangentLine(arc, end_arc, keep=Keep.INSIDE)

    def test_arc_arc_tangent_arc(self):
        """Test tangent arc between arcs

        Considerations:
        - Should produce a GeomType.CIRCLE located on and tangent to arcs
        - Tangent arcs that share a side have arc centers on the same side of the midline
        - LEFT arcs have centers to left of midline (for (INSIDE, *) case, non overlapping))
        - Mirrored arcs should always have equal length as long as arcs are same distance
        - Tangent should be GeomType.CIRCLE
        - Arcs must be coplanar
        - Cannot make tangent for concentric arcs
        """

        # Test line properties in algebra mode
        start_r = 2
        end_r = 5
        separation = 10
        start_point = (0, 0)
        end_point = (0, separation)

        start_arc = CenterArc(start_point, start_r, 0, 360)
        end_arc = CenterArc(end_point, end_r, 0, 360)
        radius = 15
        lines = []
        for keep_placement in [Keep.INSIDE, Keep.OUTSIDE]:
            keep = (keep_placement, Keep.OUTSIDE)
            for side in [Side.LEFT, Side.RIGHT]:
                l1 = ArcArcTangentArc(start_arc, end_arc, radius, side=side, keep=keep)
                self.assertEqual(l1.geom_type, GeomType.CIRCLE)
                self.assertAlmostEqual(l1.radius, radius)

                # Check coincidence, tangency with each arc
                _, p1, p2 = start_arc.distance_to_with_closest_points(l1)
                self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
                self.assertAlmostEqual(
                    start_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
                )
                _, p1, p2 = end_arc.distance_to_with_closest_points(l1)
                self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
                self.assertAlmostEqual(
                    end_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
                )
                lines.append(l1)

            self.assertAlmostEqual(lines[-2].length, lines[-1].length, 5)

        # Test in off-axis builder mode at multiple angles and compare to prev result
        workplane = Plane.XY.rotated((45, 45, 45))
        with BuildLine(workplane):
            end_center = workplane.from_local_coords(end_point)
            point_arc = CenterArc(end_center, separation, 0, 360)
            end_arc = CenterArc(end_center, end_r, 0, 360)

            points = [1, 2, 3, 5, 7, 11, 13]
            for point in points:
                start_center = point_arc @ (point / 16)
                start_arc = CenterArc(point_arc @ (point / 16), start_r, 0, 360)
                mid_vector = end_center - start_center
                mid_perp = mid_vector.cross(workplane.z_dir)
                for keep_placement in [Keep.INSIDE, Keep.OUTSIDE]:
                    keep = (keep_placement, Keep.OUTSIDE)
                    for side in [Side.LEFT, Side.RIGHT]:
                        l2 = ArcArcTangentArc(
                            start_arc, end_arc, radius, side=side, keep=keep
                        )
                        # Check length against algebraic length
                        if keep_placement == Keep.OUTSIDE:
                            self.assertAlmostEqual(lines[2].length, l2.length, 5)
                            side_sign = 1
                        elif keep_placement == Keep.INSIDE:
                            self.assertAlmostEqual(lines[0].length, l2.length, 5)
                            side_sign = -1

                        # Check side of midline
                        _, _, p2 = start_arc.distance_to_with_closest_points(l2)
                        coincident_dir = mid_perp.dot(p2 - start_center)
                        center_dir = mid_perp.dot(l2.arc_center - start_center)
                        if side == Side.LEFT:
                            self.assertLess(side_sign * coincident_dir, 0)
                            self.assertLess(center_dir, 0)
                        elif side == Side.RIGHT:
                            self.assertGreater(side_sign * coincident_dir, 0)
                            self.assertGreater(center_dir, 0)

        # Verify arc is tangent for a reversed start arc
        c1 = CenterArc((0, 80), 40, 0, -180)
        c2 = CenterArc((80, 0), 40, 90, 180)
        keep = (Keep.OUTSIDE, Keep.OUTSIDE)
        arc = ArcArcTangentArc(c1, c2, 25, side=Side.RIGHT, keep=keep)
        _, _, point = c1.distance_to_with_closest_points(arc)
        self.assertAlmostEqual(
            c1.tangent_at(point).cross(arc.tangent_at(point)).length, 0, 5
        )

        ## Error Handling
        start_arc = CenterArc(start_point, start_r, 0, 360)
        end_arc = CenterArc(end_point, end_r, 0, 360)

        # GeomType
        bad_type = Line((0, 0), (0, 10))
        with self.assertRaises(ValueError):
            ArcArcTangentArc(start_arc, bad_type, radius)

        with self.assertRaises(ValueError):
            ArcArcTangentArc(bad_type, end_arc, radius)

        # Keep.BOTH
        with self.assertRaises(ValueError):
            ArcArcTangentArc(bad_type, end_arc, radius, keep=(Keep.BOTH, Keep.OUTSIDE))

        # Coplanar
        with self.assertRaises(ValueError):
            ArcArcTangentArc(CenterArc((0, 0, 1), 5, 0, 360), end_arc, radius)

        # Coincidence (already tangent)
        with self.assertRaises(ValueError):
            ArcArcTangentArc(start_arc, CenterArc((0, 2 * start_r), start_r, 0, 360), 3)

        with self.assertRaises(ValueError):
            ArcArcTangentArc(start_arc, CenterArc(start_point, start_r, 0, 360), 3)

        with self.assertRaises(ValueError):
            ArcArcTangentArc(
                start_arc, CenterArc((0, end_r - start_r), end_r, 0, 360), 3
            )

        ## Spot check all conditions
        r1, r2 = 3, 8
        start_center = (0, 0)
        start_arc = CenterArc(start_center, r1, 0, 360)

        end_y = {
            "no_overlap": (r1 + r2) * 1.1,
            "partial_overlap": (r1 + r2) / 2,
            "full_overlap": (r2 - r1) * 0.9,
        }

        # Test matrix:
        # (separation, keep pair, [min_limit, max_limit])
        # actual limit will be (separation + min_limit) / 2
        cases = [
            (end_y["no_overlap"], (Keep.INSIDE, Keep.INSIDE), [r1 - r2, None]),
            (end_y["no_overlap"], (Keep.OUTSIDE, Keep.INSIDE), [-r1 + r2, None]),
            (end_y["no_overlap"], (Keep.INSIDE, Keep.OUTSIDE), [r1 + r2, None]),
            (end_y["no_overlap"], (Keep.OUTSIDE, Keep.OUTSIDE), [-r1 - r2, None]),
            (end_y["partial_overlap"], (Keep.INSIDE, Keep.INSIDE), [None, r1 - r2]),
            (end_y["partial_overlap"], (Keep.OUTSIDE, Keep.INSIDE), [None, -r1 + r2]),
            (end_y["partial_overlap"], (Keep.BOTH, Keep.INSIDE), [None, r1 + r2]),
            (end_y["partial_overlap"], (Keep.INSIDE, Keep.OUTSIDE), [r1 + r2, None]),
            (end_y["partial_overlap"], (Keep.OUTSIDE, Keep.OUTSIDE), [None, None]),
            (end_y["full_overlap"], (Keep.INSIDE, Keep.INSIDE), [r1 + r2, r1 + r2]),
            (end_y["full_overlap"], (Keep.OUTSIDE, Keep.INSIDE), [-r1 + r2, -r1 + r2]),
        ]

        # Check min and max radii, tangency
        for case in cases:
            end_center = (0, case[0])
            end_arc = CenterArc(end_center, r2, 0, 360)

            flip_max = -1 if case[1] == (Keep.BOTH, Keep.INSIDE) else 1
            flip_min = -1 if case[0] == end_y["full_overlap"] else 1

            min_r = 0 if case[2][0] is None else (flip_min * case[0] + case[2][0]) / 2
            max_r = 1e6 if case[2][1] is None else (flip_max * case[0] + case[2][1]) / 2

            print(case[1], min_r, max_r, case[0])
            print(min_r + 0.01, min_r * 0.99, max_r - 0.01, max_r + 0.01)
            print((case[0] - 1 * (r1 + r2)) / 2)

            # Greater than min
            l1 = ArcArcTangentArc(start_arc, end_arc, min_r + 0.01, keep=case[1])
            _, p1, p2 = start_arc.distance_to_with_closest_points(l1)
            self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
            self.assertAlmostEqual(
                start_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
            )
            _, p1, p2 = end_arc.distance_to_with_closest_points(l1)
            self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
            self.assertAlmostEqual(
                end_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
            )

            # Less than max
            l1 = ArcArcTangentArc(start_arc, end_arc, max_r - 0.01, keep=case[1])
            _, p1, p2 = start_arc.distance_to_with_closest_points(l1)
            self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
            self.assertAlmostEqual(
                start_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
            )
            _, p1, p2 = end_arc.distance_to_with_closest_points(l1)
            self.assertTupleAlmostEquals(tuple(p1), tuple(p2), 5)
            self.assertAlmostEqual(
                end_arc.tangent_at(p1).cross(l1.tangent_at(p2)).length, 0, 5
            )

            # Less than min
            with self.assertRaises(ValueError):
                ArcArcTangentArc(start_arc, end_arc, min_r * 0.99, keep=case[1])

            # Greater than max
            if max_r != 1e6:
                with self.assertRaises(ValueError):
                    ArcArcTangentArc(start_arc, end_arc, max_r + 0.01, keep=case[1])

    def test_line_with_list(self):
        """Test line with a list of points"""
        l = Line([(0, 0), (10, 0)])
        self.assertAlmostEqual(l.length, 10, 5)

    def test_wires_select_last(self):
        with BuildLine() as test:
            Line((0, 0), (0, 1))
            Polyline((1, 0), (1, 1), (0, 1), (0, 0))
        self.assertAlmostEqual(test.wires(Select.LAST)[0].length, 3, 5)

    def test_error_conditions(self):
        """Test error handling"""
        with self.assertRaises(ValueError):
            with BuildLine():
                Line((0, 0))  # Need two points
        with self.assertRaises(ValueError):
            with BuildLine():
                Polyline((0, 0))  # Need two points
        with self.assertRaises(ValueError):
            with BuildLine():
                RadiusArc((0, 0), (1, 0), 0.1)  # Radius too small
        with self.assertRaises(ValueError):
            with BuildLine():
                TangentArc((0, 0), tangent=(1, 1))  # Need two points
        with self.assertRaises(ValueError):
            with BuildLine():
                ThreePointArc((0, 0), (1, 1))  # Need three points
        with self.assertRaises(NotImplementedError):
            with BuildLine() as bl:
                Line((0, 0), (1, 1))
                bl.faces()
        with self.assertRaises(NotImplementedError):
            with BuildLine() as bl:
                Line((0, 0), (1, 1))
                bl.solids()

    def test_obj_name(self):
        with BuildLine() as test:
            self.assertEqual(test._obj_name, "line")


if __name__ == "__main__":
    unittest.main()
