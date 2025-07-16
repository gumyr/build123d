"""
build123d imports

name: test_cad_objects.py
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
import unittest

from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import gp, gp_Ax2, gp_Circ, gp_Elips, gp_Pnt
from build123d.build_enums import CenterOf
from build123d.geometry import Plane, Vector
from build123d.topology import Edge, Face, Wire


class TestCadObjects(unittest.TestCase):
    def _make_circle(self):
        circle = gp_Circ(gp_Ax2(gp_Pnt(1, 2, 3), gp.DZ_s()), 2.0)
        return Edge.cast(BRepBuilderAPI_MakeEdge(circle).Edge())

    def _make_ellipse(self):
        ellipse = gp_Elips(gp_Ax2(gp_Pnt(1, 2, 3), gp.DZ_s()), 4.0, 2.0)
        return Edge.cast(BRepBuilderAPI_MakeEdge(ellipse).Edge())

    def test_edge_wrapper_center(self):
        e = self._make_circle()

        self.assertAlmostEqual(e.center(CenterOf.MASS), (1.0, 2.0, 3.0), 3)

    def test_edge_wrapper_ellipse_center(self):
        e = self._make_ellipse()
        w = Wire([e])
        self.assertAlmostEqual(Face(w).center(), (1.0, 2.0, 3.0), 3)

    def test_edge_wrapper_make_circle(self):
        halfCircleEdge = Edge.make_circle(radius=10, start_angle=0, end_angle=180)

        # np.testing.assert_allclose((0.0, 5.0, 0.0), halfCircleEdge.centerOfBoundBox(0.0001),1e-3)
        self.assertAlmostEqual(halfCircleEdge.start_point(), (10.0, 0.0, 0.0), 3)
        self.assertAlmostEqual(halfCircleEdge.end_point(), (-10.0, 0.0, 0.0), 3)

    def test_edge_wrapper_make_tangent_arc(self):
        tangent_arc = Edge.make_tangent_arc(
            Vector(1, 1),  # starts at 1, 1
            Vector(0, 1),  # tangent at start of arc is in the +y direction
            Vector(2, 1),  # arc cureturn_values 180 degrees and ends at 2, 1
        )
        self.assertAlmostEqual(tangent_arc.start_point(), (1, 1, 0), 3)
        self.assertAlmostEqual(tangent_arc.end_point(), (2, 1, 0), 3)
        self.assertAlmostEqual(tangent_arc.tangent_at(0), (0, 1, 0), 3)
        self.assertAlmostEqual(tangent_arc.tangent_at(0.5), (1, 0, 0), 3)
        self.assertAlmostEqual(tangent_arc.tangent_at(1), (0, -1, 0), 3)

    def test_edge_wrapper_make_ellipse1(self):
        # Check x_radius > y_radius
        x_radius, y_radius = 20, 10
        angle1, angle2 = -75.0, 90.0
        arcEllipseEdge = Edge.make_ellipse(
            x_radius=x_radius,
            y_radius=y_radius,
            plane=Plane.XY,
            start_angle=angle1,
            end_angle=angle2,
        )

        start = (
            x_radius * math.cos(math.radians(angle1)),
            y_radius * math.sin(math.radians(angle1)),
            0.0,
        )
        end = (
            x_radius * math.cos(math.radians(angle2)),
            y_radius * math.sin(math.radians(angle2)),
            0.0,
        )
        self.assertAlmostEqual(arcEllipseEdge.start_point(), start, 3)
        self.assertAlmostEqual(arcEllipseEdge.end_point(), end, 3)

    def test_edge_wrapper_make_ellipse2(self):
        # Check x_radius < y_radius
        x_radius, y_radius = 10, 20
        angle1, angle2 = 0.0, 45.0
        arcEllipseEdge = Edge.make_ellipse(
            x_radius=x_radius,
            y_radius=y_radius,
            plane=Plane.XY,
            start_angle=angle1,
            end_angle=angle2,
        )

        start = (
            x_radius * math.cos(math.radians(angle1)),
            y_radius * math.sin(math.radians(angle1)),
            0.0,
        )
        end = (
            x_radius * math.cos(math.radians(angle2)),
            y_radius * math.sin(math.radians(angle2)),
            0.0,
        )
        self.assertAlmostEqual(arcEllipseEdge.start_point(), start, 3)
        self.assertAlmostEqual(arcEllipseEdge.end_point(), end, 3)

    def test_edge_wrapper_make_circle_with_ellipse(self):
        # Check x_radius == y_radius
        x_radius, y_radius = 20, 20
        angle1, angle2 = 15.0, 60.0
        arcEllipseEdge = Edge.make_ellipse(
            x_radius=x_radius,
            y_radius=y_radius,
            plane=Plane.XY,
            start_angle=angle1,
            end_angle=angle2,
        )

        start = (
            x_radius * math.cos(math.radians(angle1)),
            y_radius * math.sin(math.radians(angle1)),
            0.0,
        )
        end = (
            x_radius * math.cos(math.radians(angle2)),
            y_radius * math.sin(math.radians(angle2)),
            0.0,
        )
        self.assertAlmostEqual(arcEllipseEdge.start_point(), start, 3)
        self.assertAlmostEqual(arcEllipseEdge.end_point(), end, 3)

    def test_face_wrapper_make_rect(self):
        mplane = Face.make_rect(10, 10)

        self.assertAlmostEqual(mplane.normal_at(), (0.0, 0.0, 1.0), 3)

    # def testCompoundcenter(self):
    #     """
    #     Tests whether or not a proper weighted center can be found for a compound
    #     """

    #     def cylinders(self, radius, height):

    #         c = Solid.make_cylinder(radius, height, Vector())

    #         # Combine all the cylinders into a single compound
    #         r = self.eachpoint(lambda loc: c.located(loc), True).combinesolids()

    #         return r

    #     Workplane.cyl = cylinders

    #     # Now test. here we want weird workplane to see if the objects are transformed right
    #     s = (
    #         Workplane("XY")
    #         .rect(2.0, 3.0, for_construction=true)
    #         .vertices()
    #         .cyl(0.25, 0.5)
    #     )

    #     self.assertEqual(4, len(s.val().solids()))
    #     np.testing.assert_allclose((0.0, 0.0, 0.25), s.val().center, 1e-3)

    def test_translate(self):
        e = Edge.make_circle(2, Plane((1, 2, 3)))
        e2 = e.translate(Vector(0, 0, 1))

        self.assertAlmostEqual(e2.center(CenterOf.MASS), (1.0, 2.0, 4.0), 3)

    def test_vertices(self):
        e = Edge.cast(BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(1, 1, 0)).Edge())
        self.assertEqual(2, len(e.vertices()))

    def test_edge_wrapper_radius(self):
        # get a radius from a simple circle
        e0 = Edge.make_circle(2.4)
        self.assertAlmostEqual(e0.radius, 2.4)

        # radius of an arc
        e1 = Edge.make_circle(
            1.8, Plane(origin=(5, 6, 7), z_dir=(1, 1, 1)), start_angle=20, end_angle=30
        )
        self.assertAlmostEqual(e1.radius, 1.8)

        # test value errors
        e2 = Edge.make_ellipse(10, 20)
        with self.assertRaises(ValueError):
            e2.radius

        # radius from a wire
        w0 = Wire.make_circle(10, Plane(origin=(1, 2, 3), z_dir=(-1, 0, 1)))
        self.assertAlmostEqual(w0.radius, 10)

        # radius from a wire with multiple edges
        rad = 2.3
        plane = Plane(origin=(7, 8, 0), z_dir=(1, 0.5, 0.1))
        w1 = Wire(
            [
                Edge.make_circle(rad, plane, 0, 10),
                Edge.make_circle(rad, plane, 10, 25),
                Edge.make_circle(rad, plane, 25, 230),
            ]
        )
        self.assertAlmostEqual(w1.radius, rad)

        # test value error from wire
        w2 = Wire.make_polygon(
            [
                Vector(-1, 0, 0),
                Vector(0, 1, 0),
                Vector(1, -1, 0),
            ]
        )
        with self.assertRaises(ValueError):
            w2.radius

        # (I think) the radius of a wire is the radius of it's first edge.
        # Since this is stated in the docstring better make sure.
        no_rad = Wire(
            [
                Edge.make_line(Vector(0, 0, 0), Vector(0, 1, 0)),
                Edge.make_circle(1.0, start_angle=90, end_angle=270),
            ]
        )
        with self.assertRaises(ValueError):
            no_rad.radius
        yes_rad = Wire(
            [
                Edge.make_circle(1.0, start_angle=90, end_angle=270),
                Edge.make_line(Vector(0, -1, 0), Vector(0, 1, 0)),
            ]
        )
        self.assertAlmostEqual(yes_rad.radius, 1.0)
        many_rad = Wire(
            [
                Edge.make_circle(1.0, start_angle=0, end_angle=180),
                Edge.make_circle(3.0, Plane((2, 0, 0)), start_angle=180, end_angle=359),
            ]
        )
        self.assertAlmostEqual(many_rad.radius, 1.0)


if __name__ == "__main__":
    unittest.main()
