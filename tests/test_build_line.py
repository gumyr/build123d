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


class NestedLine(BaseLineObject):
    """Composite line used to verify nested curve-object isolation."""

    def __init__(self, mode=Mode.ADD, fail=False):
        self.caller_seen = BuildLine._get_context(log=False)
        with BuildLine() as internal_builder:
            self.child = Polyline((0, 0), (1, 0), (1, 1))
            self.builder_after_child = BuildLine._get_context(log=False)
        self.internal_builder = internal_builder
        if fail:
            raise RuntimeError("nested line failure")
        super().__init__(internal_builder.wire(), mode=mode)
        self.finished = True

    def _publish_to_context(self, construction):
        assert self.finished
        super()._publish_to_context(construction)


class BuildLineTests(unittest.TestCase):
    """Test the BuildLine Builder derived class"""

    def test_base_curve_object_firewall(self):
        with BuildLine() as outer_builder:
            nested = NestedLine()

        self.assertIsNone(nested.caller_seen)
        self.assertIs(nested.builder_after_child, nested.internal_builder)
        self.assertEqual(len(nested.internal_builder.edges()), 2)
        self.assertEqual(len(outer_builder.edges()), 2)

    def test_private_curve_not_published(self):
        with BuildLine() as outer_builder:
            Line((0, 0), (1, 0))
            NestedLine(mode=Mode.PRIVATE)

        self.assertEqual(len(outer_builder.edges()), 1)

    def test_failed_curve_not_published(self):
        with BuildLine() as outer_builder:
            Line((0, 0), (1, 0))
            with self.assertRaisesRegex(RuntimeError, "nested line failure"):
                NestedLine(fail=True)

        self.assertEqual(len(outer_builder.edges()), 1)

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
        self.assertAlmostEqual(roller_coaster.wires()[0].length, 678.9785865257071, 5)

    def test_bezier(self):
        pts = [(0, 0), (20, 20), (40, 0), (0, -40), (-60, 0), (0, 100), (100, 0)]
        wts = [1.0, 1.0, 2.0, 3.0, 4.0, 2.0, 1.0]
        with BuildLine() as bz:
            b1 = Bezier(*pts, weights=wts)
        self.assertAlmostEqual(bz.wires()[0].length, 225.98661946375782, 5)
        self.assertTrue(isinstance(b1, Edge))

    def test_bspline(self):
        control_points = [(0, 0), (1, 1), (2, 0)]
        knots = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]

        with BuildLine() as bl:
            spline = BSpline(control_points, knots, degree=2)

        self.assertTrue(isinstance(spline, Edge))
        self.assertEqual(spline.geom_type, GeomType.BSPLINE)
        self.assertEqual(len(bl.edges()), 1)
        self.assertAlmostEqual(bl.edge().start_point(), (0, 0, 0), 5)
        self.assertAlmostEqual(bl.edge().end_point(), (2, 0, 0), 5)

        with self.assertRaises(ValueError):
            BSpline(control_points, knots=[], degree=2)

    def test_double_tangent_arc(self):
        l1 = Line((10, 0), (30, 20))
        l2 = DoubleTangentArc((0, 5), (1, 0), l1)
        _, p1, p2 = l1.distance_to_with_closest_points(l2)
        self.assertAlmostEqual(p1, p2, 5)
        self.assertAlmostEqual(l1.tangent_at(p1), l2.tangent_at(p2), 5)

        l3 = Line((10, 0), (20, -10))
        l4 = DoubleTangentArc((0, 0), (1, 0), l3)
        _, p1, p2 = l3.distance_to_with_closest_points(l4)
        self.assertAlmostEqual(p1, p2, 5)
        self.assertAlmostEqual(l3.tangent_at(p1), l4.tangent_at(p2), 5)

        with BuildLine() as test:
            l5 = Polyline((20, -10), (10, 0), (20, 10))
            l6 = DoubleTangentArc((0, 0), (1, 0), l5, keep=Keep.BOTTOM)
        _, p1, p2 = l5.distance_to_with_closest_points(l6)
        self.assertAlmostEqual(p1, p2, 5)
        self.assertAlmostEqual(l5.tangent_at(p1), l6.tangent_at(p2) * -1, 5)

        # l7 = Spline((15, 5), (5, 0), (15, -5), tangents=[(-1, 0), (1, 0)])
        # l8 = DoubleTangentArc((0, 0, 0), (1, 0, 0), l7, keep=Keep.BOTH)
        # self.assertEqual(len(l8.edges()), 2)

        l9 = EllipticalCenterArc((15, 0), 10, 5, start_angle=90, arc_size=180)
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
        with BuildLine(Plane.XZ) as bl:
            a = EllipticalStartArc((1, 1), (0, 1), 3, 1, 90, major_axis_dir=(1, 1))
        self.assertAlmostEqual(a.arc_center, (-1.2360679775, -0.7888543819998, 0), 5)
        self.assertAlmostEqual(
            bl.line.edge().arc_center, (-1.2360679775, 0, -0.7888543819998), 5
        )

        a = EllipticalStartArc((1, 1), Vector(0, 1), 3, 1, 90, major_axis_dir=(1, 1))
        self.assertAlmostEqual(a.arc_center, (-1.2360679775, -0.7888543819998, 0), 5)
        self.assertTrue(isinstance(a, Edge))

        b = EllipticalStartArc((0, 1), (-1, 0), 5, 1, 180, start_angle=90)
        self.assertAlmostEqual(b.arc_center, (0, 0), 5)
        self.assertAlmostEqual(b @ 1, (0, -1), 5)

        with self.assertRaisesRegex(ValueError, "start_angle or major_axis_dir"):
            EllipticalStartArc((0, 0), (1, 0), 5, 3, 90)

        c = EllipticalStartArc((1, 1), (0, 1), 3, 1, -45, start_angle=45)
        self.assertGreater(5, c.length)

    def test_elliptical_center_arc(self):
        with BuildLine() as el:
            EllipticalCenterArc((0, 0), 10, 5, 0, arc_size=180)
        bbox = el.line.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)

        e1 = EllipticalCenterArc((0, 0), 10, 5, 0, arc_size=180)
        bbox = e1.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)
        self.assertTrue(isinstance(e1, Edge))

    def test_elliptical_center_arc_limits(self):
        l1 = Line((0, 0), (0, 2))
        e1 = EllipticalCenterArc((0, 0), 2, 1, 0, arc_size=l1)
        self.assertAlmostEqual(e1 @ 1, (0, 1, 0), 5)

        l2 = Line((0, 0), (0, -2))
        e2 = EllipticalCenterArc((0, 0), 2, 1, 0, arc_size=l2)
        self.assertAlmostEqual(e2 @ 1, (0, -1, 0), 5)

        with self.assertRaises(ValueError):
            EllipticalCenterArc((0, 0), 2, 1, 0, arc_size=(0, 5))

    def test_parabolic_center_arc(self):
        # General conic section equation: (1+K)x^2-2Rx+y^2=0
        # parabola (K = -1) => -2Rx+y^2=0
        center = (0, 0)
        C = 1
        R = 1 / C
        focal_length = R / 2
        with BuildLine() as el:
            ParabolicCenterArc(
                center,
                focal_length,
                0,
                arc_size=90,
                rotation=0,
                mode=Mode.ADD,
            )
        bbox = el.line.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)

        e1 = ParabolicCenterArc(
            center,
            focal_length,
            0,
            arc_size=90,
            rotation=0,
            mode=Mode.ADD,
        )
        bbox = e1.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)
        self.assertTrue(isinstance(e1, Edge))

    def test_parabolic_center_arc_limits(self):
        l1 = Line((0, 1), (5, 1))
        e1 = ParabolicCenterArc((0, 0), 0.5, 0, arc_size=l1)
        self.assertAlmostEqual(e1 @ 1, (0.5, 1, 0), 5)

        l2 = Line((1, -2), (1, 2))
        e2 = ParabolicCenterArc((0, 0), 0.5, 0, arc_size=l2)
        self.assertAlmostEqual(e2 @ 1, (1, 2**0.5, 0), 5)

        with self.assertRaises(ValueError):
            ParabolicCenterArc((0, 0), 0.5, 0, arc_size=(0, 5))

    def test_parabolic_center_arc_arc_size(self):
        e1 = ParabolicCenterArc((0, 0), 0.5, 0, arc_size=90)
        self.assertAlmostEqual(e1 @ 0, (0, 0, 0), 5)
        self.assertAlmostEqual(e1 @ 1, (1.23370055, 1.57079633, 0), 5)

        e2 = ParabolicCenterArc((0, 0), 0.5, 0, arc_size=-90)
        self.assertAlmostEqual(e2 @ 0, (1.23370055, -1.57079633, 0), 5)
        self.assertAlmostEqual(e2 @ 1, (0, 0, 0), 5)

    def test_hyperbolic_center_arc(self):
        # General conic section equation: (1+K)x^2-2Rx+y^2=0
        # hyperbola (K < -1)
        center = (0, 0)
        C = 1
        R = 1 / C
        K = -2  # => -(x^2)-2Rx+y^2=0
        a, b = R / (-K - 1), R / sqrt(-K - 1)
        with BuildLine() as el:
            HyperbolicCenterArc(
                center,
                b,
                a,
                0,
                arc_size=90,
                rotation=0,
                mode=Mode.ADD,
            )
        bbox = el.line.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)

        e1 = HyperbolicCenterArc(
            center,
            b,
            a,
            0,
            arc_size=90,
            rotation=0,
            mode=Mode.ADD,
        )
        bbox = e1.bounding_box()
        self.assertGreaterEqual(bbox.min.X, -10)
        self.assertGreaterEqual(bbox.min.Y, 0)
        self.assertLessEqual(bbox.max.X, 10)
        self.assertLessEqual(bbox.max.Y, 5)
        self.assertTrue(isinstance(e1, Edge))

    def test_hyperbolic_center_arc_limits(self):
        l1 = Line((0, 1), (10, 1))
        e1 = HyperbolicCenterArc((0, 0), 2, 1, 0, arc_size=l1)
        self.assertAlmostEqual(e1 @ 1, (8**0.5, 1, 0), 4)

        l2 = Line((3, -2), (3, 2))
        e2 = HyperbolicCenterArc((0, 0), 2, 1, 0, arc_size=l2)
        self.assertAlmostEqual(e2 @ 1, (3, 5**0.5 / 2, 0), 4)

        with self.assertRaises(ValueError):
            HyperbolicCenterArc((0, 0), 2, 1, 0, arc_size=(0, 5))

    def test_hyperbolic_center_arc_arc_size(self):
        e1 = HyperbolicCenterArc((0, 0), 2, 1, 0, arc_size=90)
        self.assertAlmostEqual(e1 @ 0, (2, 0, 0), 5)
        self.assertAlmostEqual(e1 @ 1, (5.01835696, 2.3012989, 0), 5)

        e2 = HyperbolicCenterArc((0, 0), 2, 1, 0, arc_size=-90)
        self.assertAlmostEqual(e2 @ 0, (5.01835696, -2.3012989, 0), 5)
        self.assertAlmostEqual(e2 @ 1, (2, 0, 0), 5)

    def test_filletpolyline(self):
        with BuildLine(Plane.YZ):
            p = FilletPolyline(
                (0, 0, 0), (0, 10, 2), (0, 10, 10), (5, 20, 10), radius=2
            )
        self.assertEqual(len(p.edges()), 5)
        self.assertEqual(len(p.edges().filter_by(GeomType.CIRCLE)), 2)
        self.assertEqual(len(p.edges().filter_by(GeomType.LINE)), 3)

        with BuildLine(Plane.YZ):
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (0, 10),
                radius=(1, 2, 3, 0),
                close=True,
            )
        self.assertEqual(len(p.edges().filter_by(GeomType.CIRCLE)), 3)
        self.assertEqual(len(p.edges().filter_by(GeomType.LINE)), 4)

        with self.assertRaises(ValueError):
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (0, 10),
                radius=(1, 2, 3, 4),
                close=False,
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

        # test filletpolyline curr_fillet None
        # Middle corner radius = 0 → curr_fillet is None
        with BuildLine():
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (20, 10),
                radius=(0, 1),  # middle corner is sharp
                close=False,
            )
        # 1 circular fillet, 3 line fillets
        assert len(p.edges().filter_by(GeomType.CIRCLE)) == 1

        # test filletpolyline next_fillet None:
        # Second corner is sharp (radius 0) → next_fillet is None
        with BuildLine():
            p = FilletPolyline(
                (0, 0),
                (10, 0),
                (10, 10),
                (0, 10),
                radius=(1, 0),  # next_fillet is None at last interior corner
                close=False,
            )
        assert len(p.edges()) > 0

        # test FilletPolyline with a user closed shape
        l1 = FilletPolyline(
            (0, 0), (2, 6), (0, 5), (-2, 6), (0, 0), radius=(0, 0.1, 0, 0)
        )
        assert all(
            sum(v in e.vertices() for e in l1.edges()) == 2 for v in l1.vertices()
        )
        assert len(l1.edges().filter_by(GeomType.CIRCLE)) == 1

    def test_intersecting_line(self):
        with BuildLine():
            l1 = Line((0, 0), (10, 0))
            l2 = IntersectingLine((5, 10), (0, -1), l1)
        self.assertAlmostEqual(l2.length, 10, 5)

        l3 = Line((0, 0), (10, 10))
        l4 = IntersectingLine((0, 10), (1, -1), l3)
        self.assertAlmostEqual(l4 @ 1, (5, 5, 0), 5)
        self.assertTrue(isinstance(l4, Edge))

        with self.assertRaises(ValueError):
            IntersectingLine((0, 10), (1, 1), l3)

    def test_jern_arc(self):
        with BuildLine() as jern:
            j1 = JernArc((1, 0), (0, 1), 1, 90)
        self.assertAlmostEqual(jern.line @ 1, (0, 1, 0), 5)
        self.assertAlmostEqual(j1.radius, 1)
        self.assertAlmostEqual(j1.length, pi / 2)

        with BuildLine(Plane.XY.offset(1)) as offset_l:
            off1 = JernArc((1, 0), (0, 1), 1, 90)
        self.assertAlmostEqual(offset_l.line @ 1, (0, 1, 1), 5)
        self.assertAlmostEqual(off1.radius, 1)
        self.assertAlmostEqual(off1.length, pi / 2)

        with BuildLine(Plane.isometric) as iso_l:
            iso1 = JernArc((0, 0), (0, 1), 1, 180)
        self.assertAlmostEqual(iso_l.line @ 1, (-sqrt(2), -sqrt(2), 0), 5)
        self.assertAlmostEqual(iso1.radius, 1)
        self.assertAlmostEqual(iso1.length, pi)

        with BuildLine(Plane.YZ) as jern_arc_vector:
            jv1 = JernArc(start=(5, 4), tangent=(0, 1), radius=1, arc_size=90)
        self.assertAlmostEqual(jv1 @ 1, (4, 5, 0), 5)
        self.assertAlmostEqual(jern_arc_vector.line @ 1, (0, 4, 5), 5)
        self.assertAlmostEqual(jv1.radius, 1)
        self.assertAlmostEqual(jv1.length, pi / 2)

        with BuildLine() as full_l:
            l1 = JernArc(start=(0, 0, 0), tangent=(1, 0, 0), radius=1, arc_size=360)
            l2 = JernArc(start=(0, 0, 0), tangent=(1, 0, 0), radius=1, arc_size=300)
        self.assertTrue(l1.is_closed)
        self.assertFalse(l2.is_closed)
        circle_face = Face(Wire([l1]))
        self.assertAlmostEqual(circle_face.area, pi, 5)
        self.assertAlmostEqual(circle_face.center(), (0, 1, 0), 5)
        self.assertAlmostEqual(Vector(l1.vertex()), l2.start, 5)

        l1 = JernArc((0, 0), (1, 0), 1, 90)
        self.assertAlmostEqual(l1 @ 1, (1, 1, 0), 5)
        self.assertTrue(isinstance(l1, Edge))

        vertical = JernArc((0, 0, 0), (0, 0, 1), 1, 90)
        self.assertAlmostEqual(vertical % 0, (0, 0, 1), 5)
        self.assertAlmostEqual(vertical.radius, 1, 5)

        with BuildLine() as vertical_builder:
            vertical_builder_arc = JernArc((0, 0, 0), (0, 0, 1), 1, 90)
        self.assertAlmostEqual(vertical_builder_arc % 0, (0, 0, 1), 5)
        self.assertAlmostEqual(vertical_builder.line % 0, (0, 0, 1), 5)

        diagonal = JernArc((0, 0, 0), (1, 0, 1), 1, 90)
        self.assertAlmostEqual(diagonal % 0, Vector(1, 0, 1).normalized(), 5)
        self.assertAlmostEqual(diagonal.radius, 1, 5)

        vertical_full = JernArc((0, 0, 0), (0, 0, 1), 1, 360)
        self.assertTrue(vertical_full.is_closed)
        self.assertAlmostEqual(vertical_full.radius, 1, 5)

    def test_jern_arc_limits(self):
        l1 = Line((1, 0), (2, 1))
        j1 = JernArc((1, 0), (0, 1), 1, l1)
        self.assertAlmostEqual(j1 @ 1, (2, 1, 0), 5)

        l2 = Line((1, 0), (0, 1))
        j2 = JernArc((1, 0), (0, 1), 1, l2)
        self.assertAlmostEqual(j2 @ 1, (0, 1, 0), 5)

        with self.assertRaises(ValueError):
            JernArc((1, 0), (0, 1), 1, (5, 0))

    def test_polar_line(self):
        """Test 2D and 3D polar lines"""
        with BuildLine():
            a1 = PolarLine((0, 0), sqrt(2), 45)
            d1 = PolarLine((0, 0), sqrt(2), direction=(1, 1))
        self.assertAlmostEqual(a1 @ 1, (1, 1, 0), 5)
        self.assertAlmostEqual(a1 @ 1, d1 @ 1, 5)
        self.assertTrue(isinstance(a1, Edge))
        self.assertTrue(isinstance(d1, Edge))

        with BuildLine():
            a2 = PolarLine((0, 0), 1, 30)
            d2 = PolarLine((0, 0), 1, direction=(sqrt(3), 1))
        self.assertAlmostEqual(a2 @ 1, (sqrt(3) / 2, 0.5, 0), 5)
        self.assertAlmostEqual(a2 @ 1, d2 @ 1, 5)

        with BuildLine():
            a3 = PolarLine((0, 0), 1, 150)
            d3 = PolarLine((0, 0), 1, direction=(-sqrt(3), 1))
        self.assertAlmostEqual(a3 @ 1, (-sqrt(3) / 2, 0.5, 0), 5)
        self.assertAlmostEqual(a3 @ 1, d3 @ 1, 5)

        with BuildLine():
            a4 = PolarLine((0, 0), 1, angle=30, length_mode=LengthMode.HORIZONTAL)
            d4 = PolarLine(
                (0, 0), 1, direction=(sqrt(3), 1), length_mode=LengthMode.HORIZONTAL
            )
        self.assertAlmostEqual(a4 @ 1, (1, 1 / sqrt(3), 0), 5)
        self.assertAlmostEqual(a4 @ 1, d4 @ 1, 5)

        with BuildLine(Plane.XZ) as polar_builder:
            a5 = PolarLine((0, 0), 1, angle=30, length_mode=LengthMode.VERTICAL)
            d5 = PolarLine(
                (0, 0), 1, direction=(sqrt(3), 1), length_mode=LengthMode.VERTICAL
            )
        self.assertAlmostEqual(a5 @ 1, (sqrt(3), 1, 0), 5)
        self.assertAlmostEqual(a5 @ 1, d5 @ 1, 5)
        self.assertAlmostEqual(polar_builder.line.edges()[0] @ 1, (sqrt(3), 0, 1), 5)

        with self.assertRaises(ValueError):
            PolarLine((0, 0), 1)

    def test_polar_line_limits(self):
        limits = [
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
            Location((sqrt(2) / 2, sqrt(2) / 2), (0, 0, 1)),
            Plane((0, 0, 0), (1, 1, 0), (-1, 1, 0)),
            Vector(1, 0).rotate(Axis.Z, 45),
            (sqrt(2) / 2, sqrt(2) / 2),
        ]

        for limit in limits:
            with self.subTest(f"Limit type: {type(limit)}"):
                polar_line = PolarLine((sqrt(2), 0), length=limit, angle=135)
                self.assertAlmostEqual(polar_line.length, 1, 5)

        with self.assertRaises(ValueError):
            PolarLine((sqrt(2), 0), length=(0, 2), angle=135)

        with self.assertRaises(ValueError):
            PolarLine((sqrt(2), 0), length=Line((3, 0), (3, 1)), angle=135)

        # Check for the "behind" case
        with self.assertRaises(ValueError):
            PolarLine((1, 0), length=Plane.YZ, angle=45)

    def test_spline(self):
        """Test spline with no tangents"""
        with BuildLine() as test:
            s1 = Spline((0, 0), (1, 1), (2, 0))
        self.assertAlmostEqual(test.edges()[0] @ 1, (2, 0, 0), 5)
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
        self.assertAlmostEqual(arc.edges()[0] @ 1, (-10, 0, 0), 5)
        with BuildLine() as arc:
            CenterArc((0, 0), 10, 0, 360)
        self.assertAlmostEqual(arc.edges()[0] @ 0, arc.edges()[0] @ 1, 5)
        with BuildLine(Plane.XZ) as arc:
            CenterArc((0, 0), 10, 0, 360)
        self.assertTrue(Face(arc.line.wires()[0]).is_coplanar(Plane.XZ))

        with BuildLine(Plane.XZ) as arc:
            CenterArc((-100, 0), 100, -45, 90)
        self.assertAlmostEqual(arc.line.edges()[0] @ 0.5, (0, 0, 0), 5)

        arc = CenterArc((-100, 0), 100, 0, 360)
        self.assertTrue(Face(Wire([arc])).is_coplanar(Plane.XY))
        self.assertAlmostEqual(arc.bounding_box().max, (0, 100, 0), 5)
        self.assertTrue(isinstance(arc, Edge))

    def test_center_arc_limits(self):
        l1 = Line((1, 0), (2, 1))
        c1 = CenterArc((1, 0), 1, 0, l1)
        self.assertAlmostEqual(c1.length, pi / 4, 5)
        self.assertAlmostEqual(c1 % 0, (0, 1, 0), 5)

        l2 = Line((1, 0), (2, -1))
        c2 = CenterArc((1, 0), 1, 0, l2)
        self.assertAlmostEqual(c2.length, pi / 4, 5)
        self.assertAlmostEqual(c2 % 0, (0, -1, 0), 5)

        with self.assertRaises(ValueError):
            CenterArc((1, 0), 1, 0, (5, 0))

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
