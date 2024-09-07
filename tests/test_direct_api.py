# system modules
import copy
import io
import json
import math
import os
import platform
import random
import re
from typing import Optional
import unittest
from random import uniform
from IPython.lib import pretty

from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import (
    gp,
    gp_Ax1,
    gp_Ax2,
    gp_Circ,
    gp_Dir,
    gp_Elips,
    gp_EulerSequence,
    gp_Pnt,
    gp_Quaternion,
    gp_Trsf,
    gp_Vec,
    gp_XYZ,
)

from build123d.build_common import GridLocations, Locations, PolarLocations
from build123d.build_enums import (
    Align,
    AngularDirection,
    CenterOf,
    Extrinsic,
    GeomType,
    Intrinsic,
    Keep,
    Kind,
    Mode,
    PositionMode,
    Side,
    SortBy,
    Until,
)

from build123d.build_part import BuildPart
from build123d.exporters3d import export_brep, export_step, export_stl
from build123d.operations_part import extrude
from build123d.operations_sketch import make_face
from build123d.operations_generic import fillet, add, sweep
from build123d.objects_part import Box, Cylinder
from build123d.objects_curve import JernArc, Polyline
from build123d.build_sketch import BuildSketch
from build123d.build_line import BuildLine
from build123d.objects_curve import Spline
from build123d.objects_sketch import Circle, Rectangle, RegularPolygon
from build123d.geometry import (
    Axis,
    BoundBox,
    Color,
    Location,
    LocationEncoder,
    Matrix,
    Pos,
    Rot,
    Rotation,
    Vector,
    VectorLike,
)
from build123d.importers import import_brep, import_step, import_stl
from build123d.mesher import Mesher
from build123d.topology import (
    Compound,
    Edge,
    Face,
    Plane,
    Shape,
    ShapeList,
    Shell,
    Solid,
    Vertex,
    Wire,
    edges_to_wires,
    polar,
    new_edges,
    delta,
)
from build123d.jupyter_tools import display

DEG2RAD = math.pi / 180
RAD2DEG = 180 / math.pi


class DirectApiTestCase(unittest.TestCase):
    def assertTupleAlmostEquals(
        self,
        first: tuple[float, ...],
        second: tuple[float, ...],
        places: int,
        msg: Optional[str] = None,
    ):
        """Check Tuples"""
        self.assertEqual(len(second), len(first))
        for i, j in zip(second, first):
            self.assertAlmostEqual(i, j, places, msg=msg)

    def assertVectorAlmostEquals(
        self, first: Vector, second: VectorLike, places: int, msg: Optional[str] = None
    ):
        second_vector = Vector(second)
        self.assertAlmostEqual(first.X, second_vector.X, places, msg=msg)
        self.assertAlmostEqual(first.Y, second_vector.Y, places, msg=msg)
        self.assertAlmostEqual(first.Z, second_vector.Z, places, msg=msg)


class TestAssembly(unittest.TestCase):
    @staticmethod
    def create_test_assembly() -> Compound:
        box = Solid.make_box(1, 1, 1)
        box.orientation = (45, 45, 0)
        box.label = "box"
        sphere = Solid.make_sphere(1)
        sphere.label = "sphere"
        sphere.position = (1, 2, 3)
        assembly = Compound(label="assembly", children=[box])
        sphere.parent = assembly
        return assembly

    def assertTopoEqual(self, actual_topo: str, expected_topo_lines: list[str]):
        actual_topo_lines = actual_topo.splitlines()
        self.assertEqual(len(actual_topo_lines), len(expected_topo_lines))
        for actual_line, expected_line in zip(actual_topo_lines, expected_topo_lines):
            start, end = re.split(r"at 0x[0-9a-f]+,", expected_line, 2, re.I)
            self.assertTrue(actual_line.startswith(start))
            self.assertTrue(actual_line.endswith(end))

    def test_attributes(self):
        box = Solid.make_box(1, 1, 1)
        box.label = "box"
        sphere = Solid.make_sphere(1)
        sphere.label = "sphere"
        assembly = Compound(label="assembly", children=[box])
        sphere.parent = assembly

        self.assertEqual(len(box.children), 0)
        self.assertEqual(box.label, "box")
        self.assertEqual(box.parent, assembly)
        self.assertEqual(sphere.parent, assembly)
        self.assertEqual(len(assembly.children), 2)

    def test_show_topology_compound(self):
        assembly = TestAssembly.create_test_assembly()
        expected = [
            "assembly   Compound at 0x7fced0fd1b50, Location(p=(0.00, 0.00, 0.00), o=(-0.00, 0.00, -0.00))",
            "├── box    Solid    at 0x7fced102d3a0, Location(p=(0.00, 0.00, 0.00), o=(45.00, 45.00, -0.00))",
            "└── sphere Solid    at 0x7fced0fd1f10, Location(p=(1.00, 2.00, 3.00), o=(-0.00, 0.00, -0.00))",
        ]
        self.assertTopoEqual(assembly.show_topology("Solid"), expected)

    def test_show_topology_shape_location(self):
        assembly = TestAssembly.create_test_assembly()
        expected = [
            "Solid        at 0x7f3754501530, Position(1.0, 2.0, 3.0)",
            "└── Shell    at 0x7f3754501a70, Position(1.0, 2.0, 3.0)",
            "    └── Face at 0x7f3754501030, Position(1.0, 2.0, 3.0)",
        ]
        self.assertTopoEqual(
            assembly.children[1].show_topology("Face", show_center=False), expected
        )

    def test_show_topology_shape(self):
        assembly = TestAssembly.create_test_assembly()
        expected = [
            "Solid        at 0x7f6279043ab0, Center(1.0, 2.0, 3.0)",
            "└── Shell    at 0x7f62790438f0, Center(1.0, 2.0, 3.0)",
            "    └── Face at 0x7f62790439f0, Center(1.0, 2.0, 3.0)",
        ]
        self.assertTopoEqual(assembly.children[1].show_topology("Face"), expected)

    def test_remove_child(self):
        assembly = TestAssembly.create_test_assembly()
        self.assertEqual(len(assembly.children), 2)
        assembly.children = list(assembly.children)[1:]
        self.assertEqual(len(assembly.children), 1)

    def test_do_children_intersect(self):
        (
            overlap,
            pair,
            distance,
        ) = TestAssembly.create_test_assembly().do_children_intersect()
        self.assertFalse(overlap)
        box = Solid.make_box(1, 1, 1)
        box.orientation = (45, 45, 0)
        box.label = "box"
        sphere = Solid.make_sphere(1)
        sphere.label = "sphere"
        sphere.position = (0, 0, 0)
        assembly = Compound(label="assembly", children=[box])
        sphere.parent = assembly
        overlap, pair, distance = assembly.do_children_intersect()
        self.assertTrue(overlap)


class TestAxis(DirectApiTestCase):
    """Test the Axis class"""

    def test_axis_init(self):
        test_axis = Axis((1, 2, 3), (0, 0, 1))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis((1, 2, 3), direction=(0, 0, 1))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(origin=(1, 2, 3), direction=(0, 0, 1))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(Edge.make_line((1, 2, 3), (1, 2, 4)))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(edge=Edge.make_line((1, 2, 3), (1, 2, 4)))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        with self.assertRaises(ValueError):
            Axis("one", "up")
        with self.assertRaises(ValueError):
            Axis(one="up")

    def test_axis_from_occt(self):
        occt_axis = gp_Ax1(gp_Pnt(1, 1, 1), gp_Dir(0, 1, 0))
        test_axis = Axis(occt_axis)
        self.assertVectorAlmostEquals(test_axis.position, (1, 1, 1), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 1, 0), 5)

    def test_axis_repr_and_str(self):
        self.assertEqual(repr(Axis.X), "((0.0, 0.0, 0.0),(1.0, 0.0, 0.0))")
        self.assertEqual(str(Axis.Y), "Axis: ((0.0, 0.0, 0.0),(0.0, 1.0, 0.0))")

    def test_axis_copy(self):
        x_copy = copy.copy(Axis.X)
        self.assertVectorAlmostEquals(x_copy.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_copy.direction, (1, 0, 0), 5)
        x_copy = copy.deepcopy(Axis.X)
        self.assertVectorAlmostEquals(x_copy.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_copy.direction, (1, 0, 0), 5)

    def test_axis_to_location(self):
        # TODO: Verify this is correct
        x_location = Axis.X.location
        self.assertTrue(isinstance(x_location, Location))
        self.assertVectorAlmostEquals(x_location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_location.orientation, (0, 90, 180), 5)

    def test_axis_located(self):
        y_axis = Axis.Z.located(Location((0, 0, 1), (-90, 0, 0)))
        self.assertVectorAlmostEquals(y_axis.position, (0, 0, 1), 5)
        self.assertVectorAlmostEquals(y_axis.direction, (0, 1, 0), 5)

    def test_axis_to_plane(self):
        x_plane = Axis.X.to_plane()
        self.assertTrue(isinstance(x_plane, Plane))
        self.assertVectorAlmostEquals(x_plane.origin, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_plane.z_dir, (1, 0, 0), 5)

    def test_axis_is_coaxial(self):
        self.assertTrue(Axis.X.is_coaxial(Axis((0, 0, 0), (1, 0, 0))))
        self.assertFalse(Axis.X.is_coaxial(Axis((0, 0, 1), (1, 0, 0))))
        self.assertFalse(Axis.X.is_coaxial(Axis((0, 0, 0), (0, 1, 0))))

    def test_axis_is_normal(self):
        self.assertTrue(Axis.X.is_normal(Axis.Y))
        self.assertFalse(Axis.X.is_normal(Axis.X))

    def test_axis_is_opposite(self):
        self.assertTrue(Axis.X.is_opposite(Axis((1, 1, 1), (-1, 0, 0))))
        self.assertFalse(Axis.X.is_opposite(Axis.X))

    def test_axis_is_parallel(self):
        self.assertTrue(Axis.X.is_parallel(Axis((1, 1, 1), (1, 0, 0))))
        self.assertFalse(Axis.X.is_parallel(Axis.Y))

    def test_axis_angle_between(self):
        self.assertAlmostEqual(Axis.X.angle_between(Axis.Y), 90, 5)
        self.assertAlmostEqual(
            Axis.X.angle_between(Axis((1, 1, 1), (-1, 0, 0))), 180, 5
        )

    def test_axis_reverse(self):
        self.assertVectorAlmostEquals(Axis.X.reverse().direction, (-1, 0, 0), 5)

    def test_axis_reverse_op(self):
        axis = -Axis.X
        self.assertVectorAlmostEquals(axis.direction, (-1, 0, 0), 5)

    def test_axis_as_edge(self):
        edge = Edge(Axis.X)
        self.assertTrue(isinstance(edge, Edge))
        common = (edge & Edge.make_line((0, 0, 0), (1, 0, 0))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

    def test_axis_intersect(self):
        common = (Axis.X.intersect(Edge.make_line((0, 0, 0), (1, 0, 0)))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

        common = (Axis.X & Edge.make_line((0, 0, 0), (1, 0, 0))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

        intersection = Axis.X & Axis((1, 0, 0), (0, 1, 0))
        self.assertVectorAlmostEquals(intersection, (1, 0, 0), 5)

        i = Axis.X & Axis((1, 0, 0), (1, 0, 0))
        self.assertEqual(i, Axis.X)

        intersection = Axis((1, 2, 3), (0, 0, 1)) & Plane.XY
        self.assertTupleAlmostEquals(intersection.to_tuple(), (1, 2, 0), 5)

        arc = Edge.make_circle(20, start_angle=0, end_angle=180)
        ax0 = Axis((-20, 30, 0), (4, -3, 0))
        intersections = arc.intersect(ax0).vertices().sort_by(Axis.X)
        self.assertTupleAlmostEquals(tuple(intersections[0]), (-5.6, 19.2, 0), 5)
        self.assertTupleAlmostEquals(tuple(intersections[1]), (20, 0, 0), 5)

        intersections = ax0.intersect(arc).vertices().sort_by(Axis.X)
        self.assertTupleAlmostEquals(tuple(intersections[0]), (-5.6, 19.2, 0), 5)
        self.assertTupleAlmostEquals(tuple(intersections[1]), (20, 0, 0), 5)

        i = Axis((0, 0, 1), (1, 1, 1)) & Vector(0.5, 0.5, 1.5)
        self.assertTrue(isinstance(i, Vector))
        self.assertVectorAlmostEquals(i, (0.5, 0.5, 1.5), 5)
        self.assertIsNone(Axis.Y & Vector(2, 0, 0))

        l = Edge.make_line((0, 0, 1), (0, 0, 2)) ^ 1
        i: Location = Axis.Z & l
        self.assertTrue(isinstance(i, Location))
        self.assertVectorAlmostEquals(i.position, l.position, 5)
        self.assertVectorAlmostEquals(i.orientation, l.orientation, 5)

        self.assertIsNone(Axis.Z & Edge.make_line((0, 0, 1), (1, 0, 0)).location_at(1))
        self.assertIsNone(Axis.Z & Edge.make_line((1, 0, 1), (1, 0, 2)).location_at(1))

        # TODO: uncomment when generalized edge to surface intersections are complete
        # non_planar = (
        #     Solid.make_cylinder(1, 10).faces().filter_by(GeomType.PLANE, reverse=True)
        # )
        # intersections = Axis((0, 0, 5), (1, 0, 0)) & non_planar

        # self.assertTrue(len(intersections.vertices(), 2))
        # self.assertTupleAlmostEquals(
        #     intersection.vertices()[0].to_tuple(), (-1, 0, 5), 5
        # )
        # self.assertTupleAlmostEquals(
        #     intersection.vertices()[1].to_tuple(), (1, 0, 5), 5
        # )

    def test_axis_equal(self):
        self.assertEqual(Axis.X, Axis.X)
        self.assertEqual(Axis.Y, Axis.Y)
        self.assertEqual(Axis.Z, Axis.Z)

    def test_axis_not_equal(self):
        self.assertNotEqual(Axis.X, Axis.Y)
        random_obj = object()
        self.assertNotEqual(Axis.X, random_obj)


class TestBoundBox(DirectApiTestCase):
    def test_basic_bounding_box(self):
        v = Vertex(1, 1, 1)
        v2 = Vertex(2, 2, 2)
        self.assertEqual(BoundBox, type(v.bounding_box()))
        self.assertEqual(BoundBox, type(v2.bounding_box()))

        bb1 = v.bounding_box().add(v2.bounding_box())

        # OCC uses some approximations
        self.assertAlmostEqual(bb1.size.X, 1.0, 1)

        # Test adding to an existing bounding box
        v0 = Vertex(0, 0, 0)
        bb2 = v0.bounding_box().add(v.bounding_box())

        bb3 = bb1.add(bb2)
        self.assertVectorAlmostEquals(bb3.size, (2, 2, 2), 7)

        bb3 = bb2.add((3, 3, 3))
        self.assertVectorAlmostEquals(bb3.size, (3, 3, 3), 7)

        bb3 = bb2.add(Vector(3, 3, 3))
        self.assertVectorAlmostEquals(bb3.size, (3, 3, 3), 7)

        # Test 2D bounding boxes
        bb1 = Vertex(1, 1, 0).bounding_box().add(Vertex(2, 2, 0).bounding_box())
        bb2 = Vertex(0, 0, 0).bounding_box().add(Vertex(3, 3, 0).bounding_box())
        bb3 = Vertex(0, 0, 0).bounding_box().add(Vertex(1.5, 1.5, 0).bounding_box())
        # Test that bb2 contains bb1
        self.assertEqual(bb2, BoundBox.find_outside_box_2d(bb1, bb2))
        self.assertEqual(bb2, BoundBox.find_outside_box_2d(bb2, bb1))
        # Test that neither bounding box contains the other
        self.assertIsNone(BoundBox.find_outside_box_2d(bb1, bb3))

        # Test creation of a bounding box from a shape - note the low accuracy comparison
        # as the box is a little larger than the shape
        bb1 = BoundBox._from_topo_ds(Solid.make_cylinder(1, 1).wrapped, optimal=False)
        self.assertVectorAlmostEquals(bb1.size, (2, 2, 1), 1)

        bb2 = BoundBox._from_topo_ds(
            Solid.make_cylinder(0.5, 0.5).translate((0, 0, 0.1)).wrapped, optimal=False
        )
        self.assertTrue(bb2.is_inside(bb1))

    def test_bounding_box_repr(self):
        bb = Solid.make_box(1, 1, 1).bounding_box()
        self.assertEqual(
            repr(bb), "bbox: 0.0 <= x <= 1.0, 0.0 <= y <= 1.0, 0.0 <= z <= 1.0"
        )

    def test_center_of_boundbox(self):
        self.assertVectorAlmostEquals(
            Solid.make_box(1, 1, 1).bounding_box().center(),
            (0.5, 0.5, 0.5),
            5,
        )

    def test_combined_center_of_boundbox(self):
        pass

    def test_clean_boundbox(self):
        s = Solid.make_sphere(3)
        self.assertVectorAlmostEquals(s.bounding_box().size, (6, 6, 6), 5)
        s.mesh(1e-3)
        self.assertVectorAlmostEquals(s.bounding_box().size, (6, 6, 6), 5)

    # def test_to_solid(self):
    #     bbox = Solid.make_sphere(1).bounding_box()
    #     self.assertVectorAlmostEquals(bbox.min, (-1, -1, -1), 5)
    #     self.assertVectorAlmostEquals(bbox.max, (1, 1, 1), 5)
    #     self.assertAlmostEqual(bbox.to_solid().volume, 2**3, 5)


class TestCadObjects(DirectApiTestCase):
    def _make_circle(self):
        circle = gp_Circ(gp_Ax2(gp_Pnt(1, 2, 3), gp.DZ_s()), 2.0)
        return Shape.cast(BRepBuilderAPI_MakeEdge(circle).Edge())

    def _make_ellipse(self):
        ellipse = gp_Elips(gp_Ax2(gp_Pnt(1, 2, 3), gp.DZ_s()), 4.0, 2.0)
        return Shape.cast(BRepBuilderAPI_MakeEdge(ellipse).Edge())

    def test_edge_wrapper_center(self):
        e = self._make_circle()

        self.assertVectorAlmostEquals(e.center(CenterOf.MASS), (1.0, 2.0, 3.0), 3)

    def test_edge_wrapper_ellipse_center(self):
        e = self._make_ellipse()
        w = Wire([e])
        self.assertVectorAlmostEquals(Face(w).center(), (1.0, 2.0, 3.0), 3)

    def test_edge_wrapper_make_circle(self):
        halfCircleEdge = Edge.make_circle(radius=10, start_angle=0, end_angle=180)

        # self.assertVectorAlmostEquals((0.0, 5.0, 0.0), halfCircleEdge.centerOfBoundBox(0.0001),3)
        self.assertVectorAlmostEquals(halfCircleEdge.start_point(), (10.0, 0.0, 0.0), 3)
        self.assertVectorAlmostEquals(halfCircleEdge.end_point(), (-10.0, 0.0, 0.0), 3)

    def test_edge_wrapper_make_tangent_arc(self):
        tangent_arc = Edge.make_tangent_arc(
            Vector(1, 1),  # starts at 1, 1
            Vector(0, 1),  # tangent at start of arc is in the +y direction
            Vector(2, 1),  # arc cureturn_values 180 degrees and ends at 2, 1
        )
        self.assertVectorAlmostEquals(tangent_arc.start_point(), (1, 1, 0), 3)
        self.assertVectorAlmostEquals(tangent_arc.end_point(), (2, 1, 0), 3)
        self.assertVectorAlmostEquals(tangent_arc.tangent_at(0), (0, 1, 0), 3)
        self.assertVectorAlmostEquals(tangent_arc.tangent_at(0.5), (1, 0, 0), 3)
        self.assertVectorAlmostEquals(tangent_arc.tangent_at(1), (0, -1, 0), 3)

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
            x_radius * math.cos(angle1 * DEG2RAD),
            y_radius * math.sin(angle1 * DEG2RAD),
            0.0,
        )
        end = (
            x_radius * math.cos(angle2 * DEG2RAD),
            y_radius * math.sin(angle2 * DEG2RAD),
            0.0,
        )
        self.assertVectorAlmostEquals(arcEllipseEdge.start_point(), start, 3)
        self.assertVectorAlmostEquals(arcEllipseEdge.end_point(), end, 3)

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
            x_radius * math.cos(angle1 * DEG2RAD),
            y_radius * math.sin(angle1 * DEG2RAD),
            0.0,
        )
        end = (
            x_radius * math.cos(angle2 * DEG2RAD),
            y_radius * math.sin(angle2 * DEG2RAD),
            0.0,
        )
        self.assertVectorAlmostEquals(arcEllipseEdge.start_point(), start, 3)
        self.assertVectorAlmostEquals(arcEllipseEdge.end_point(), end, 3)

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
            x_radius * math.cos(angle1 * DEG2RAD),
            y_radius * math.sin(angle1 * DEG2RAD),
            0.0,
        )
        end = (
            x_radius * math.cos(angle2 * DEG2RAD),
            y_radius * math.sin(angle2 * DEG2RAD),
            0.0,
        )
        self.assertVectorAlmostEquals(arcEllipseEdge.start_point(), start, 3)
        self.assertVectorAlmostEquals(arcEllipseEdge.end_point(), end, 3)

    def test_face_wrapper_make_rect(self):
        mplane = Face.make_rect(10, 10)

        self.assertVectorAlmostEquals(mplane.normal_at(), (0.0, 0.0, 1.0), 3)

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
    #     self.assertVectorAlmostEquals((0.0, 0.0, 0.25), s.val().center, 3)

    def test_translate(self):
        e = Edge.make_circle(2, Plane((1, 2, 3)))
        e2 = e.translate(Vector(0, 0, 1))

        self.assertVectorAlmostEquals(e2.center(CenterOf.MASS), (1.0, 2.0, 4.0), 3)

    def test_vertices(self):
        e = Shape.cast(BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(1, 1, 0)).Edge())
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


class TestColor(DirectApiTestCase):
    def test_name1(self):
        c = Color("blue")
        self.assertTupleAlmostEquals(tuple(c), (0, 0, 1, 1), 5)

    def test_name2(self):
        c = Color("blue", alpha=0.5)
        self.assertTupleAlmostEquals(tuple(c), (0, 0, 1, 0.5), 5)

    def test_name3(self):
        c = Color("blue", 0.5)
        self.assertTupleAlmostEquals(tuple(c), (0, 0, 1, 0.5), 5)

    def test_rgb0(self):
        c = Color(0.0, 1.0, 0.0)
        self.assertTupleAlmostEquals(tuple(c), (0, 1, 0, 1), 5)

    def test_rgba1(self):
        c = Color(1.0, 1.0, 0.0, 0.5)
        self.assertEqual(c.wrapped.GetRGB().Red(), 1.0)
        self.assertEqual(c.wrapped.GetRGB().Green(), 1.0)
        self.assertEqual(c.wrapped.GetRGB().Blue(), 0.0)
        self.assertEqual(c.wrapped.Alpha(), 0.5)

    def test_rgba2(self):
        c = Color(1.0, 1.0, 0.0, alpha=0.5)
        self.assertTupleAlmostEquals(tuple(c), (1, 1, 0, 0.5), 5)

    def test_rgba3(self):
        c = Color(red=0.1, green=0.2, blue=0.3, alpha=0.5)
        self.assertTupleAlmostEquals(tuple(c), (0.1, 0.2, 0.3, 0.5), 5)

    def test_bad_color_name(self):
        with self.assertRaises(ValueError):
            Color("build123d")

    def test_to_tuple(self):
        c = Color("blue", alpha=0.5)
        self.assertTupleAlmostEquals(tuple(c), (0, 0, 1, 0.5), 5)

    def test_hex(self):
        c = Color(0x996692)
        self.assertTupleAlmostEquals(
            tuple(c), (0x99 / 0xFF, 0x66 / 0xFF, 0x92 / 0xFF, 1), 5
        )

        c = Color(0x006692, 0x80)
        self.assertTupleAlmostEquals(
            tuple(c), (0, 0x66 / 0xFF, 0x92 / 0xFF, 0x80 / 0xFF), 5
        )

        c = Color(0x006692, alpha=0x80)
        self.assertTupleAlmostEquals(tuple(c), (0, 102 / 255, 146 / 255, 128 / 255), 5)

        c = Color(color_code=0x996692, alpha=0xCC)
        self.assertTupleAlmostEquals(
            tuple(c), (153 / 255, 102 / 255, 146 / 255, 204 / 255), 5
        )

        c = Color(0.0, 0.0, 1.0, 1.0)
        self.assertTupleAlmostEquals(tuple(c), (0, 0, 1, 1), 5)

        c = Color(0, 0, 1, 1)
        self.assertTupleAlmostEquals(tuple(c), (0, 0, 1, 1), 5)

    def test_copy(self):
        c = Color(0.1, 0.2, 0.3, alpha=0.4)
        c_copy = copy.copy(c)
        self.assertTupleAlmostEquals(tuple(c_copy), (0.1, 0.2, 0.3, 0.4), 5)

    def test_str_repr(self):
        c = Color(1, 0, 0)
        self.assertEqual(str(c), "Color: (1.0, 0.0, 0.0, 1.0) ~ RED")
        self.assertEqual(repr(c), "Color(1.0, 0.0, 0.0, 1.0)")


class TestCompound(DirectApiTestCase):
    def test_make_text(self):
        arc = Edge.make_three_point_arc((-50, 0, 0), (0, 20, 0), (50, 0, 0))
        text = Compound.make_text("test", 10, text_path=arc)
        self.assertEqual(len(text.faces()), 4)
        text = Compound.make_text(
            "test", 10, align=(Align.MAX, Align.MAX), text_path=arc
        )
        self.assertEqual(len(text.faces()), 4)

    def test_fuse(self):
        box1 = Solid.make_box(1, 1, 1)
        box2 = Solid.make_box(1, 1, 1, Plane((1, 0, 0)))
        combined = Compound([box1]).fuse(box2, glue=True)
        self.assertTrue(combined.is_valid())
        self.assertAlmostEqual(combined.volume, 2, 5)
        fuzzy = Compound([box1]).fuse(box2, tol=1e-6)
        self.assertTrue(fuzzy.is_valid())
        self.assertAlmostEqual(fuzzy.volume, 2, 5)

    def test_remove(self):
        box1 = Solid.make_box(1, 1, 1)
        box2 = Solid.make_box(1, 1, 1, Plane((2, 0, 0)))
        combined = Compound([box1, box2])
        self.assertTrue(len(combined._remove(box2).solids()), 1)

    def test_repr(self):
        simple = Compound([Solid.make_box(1, 1, 1)])
        simple_str = repr(simple).split("0x")[0] + repr(simple).split(", ")[1]
        self.assertEqual(simple_str, "Compound at label()")

        assembly = Compound([Solid.make_box(1, 1, 1)])
        assembly.children = [Solid.make_box(1, 1, 1)]
        assembly.label = "test"
        assembly_str = repr(assembly).split("0x")[0] + repr(assembly).split(", l")[1]
        self.assertEqual(assembly_str, "Compound at abel(test), #children(1)")

    def test_center(self):
        test_compound = Compound(
            [
                Solid.make_box(2, 2, 2).locate(Location((-1, -1, -1))),
                Solid.make_box(1, 1, 1).locate(Location((8.5, -0.5, -0.5))),
            ]
        )
        self.assertVectorAlmostEquals(test_compound.center(CenterOf.MASS), (1, 0, 0), 5)
        self.assertVectorAlmostEquals(
            test_compound.center(CenterOf.BOUNDING_BOX), (4.25, 0, 0), 5
        )
        with self.assertRaises(ValueError):
            test_compound.center(CenterOf.GEOMETRY)

    def test_triad(self):
        triad = Compound.make_triad(10)
        bbox = triad.bounding_box()
        self.assertGreater(bbox.min.X, -10 / 8)
        self.assertLess(bbox.min.X, 0)
        self.assertGreater(bbox.min.Y, -10 / 8)
        self.assertLess(bbox.min.Y, 0)
        self.assertGreater(bbox.min.Y, -10 / 8)
        self.assertAlmostEqual(bbox.min.Z, 0, 4)
        self.assertLess(bbox.size.Z, 12.5)
        self.assertEqual(triad.volume, 0)

    def test_volume(self):
        e = Edge.make_line((0, 0), (1, 1))
        self.assertAlmostEqual(e.volume, 0, 5)

        f = Face.make_rect(1, 1)
        self.assertAlmostEqual(f.volume, 0, 5)

        b = Solid.make_box(1, 1, 1)
        self.assertAlmostEqual(b.volume, 1, 5)

        bb = Box(1, 1, 1)
        self.assertAlmostEqual(bb.volume, 1, 5)

        c = Compound(children=[e, f, b, bb, b.translate((0, 5, 0))])
        self.assertAlmostEqual(c.volume, 3, 5)
        # N.B. b and bb overlap but still add to Compound volume

    def test_constructor(self):
        with self.assertRaises(ValueError):
            Compound(bob="fred")


class TestEdge(DirectApiTestCase):
    def test_close(self):
        self.assertAlmostEqual(
            Edge.make_circle(1, end_angle=180).close().length, math.pi + 2, 5
        )
        self.assertAlmostEqual(Edge.make_circle(1).close().length, 2 * math.pi, 5)

    def test_make_half_circle(self):
        half_circle = Edge.make_circle(radius=1, start_angle=0, end_angle=180)
        self.assertVectorAlmostEquals(half_circle.start_point(), (1, 0, 0), 3)
        self.assertVectorAlmostEquals(half_circle.end_point(), (-1, 0, 0), 3)

    def test_make_half_circle2(self):
        half_circle = Edge.make_circle(radius=1, start_angle=270, end_angle=90)
        self.assertVectorAlmostEquals(half_circle.start_point(), (0, -1, 0), 3)
        self.assertVectorAlmostEquals(half_circle.end_point(), (0, 1, 0), 3)

    def test_make_clockwise_half_circle(self):
        half_circle = Edge.make_circle(
            radius=1,
            start_angle=180,
            end_angle=0,
            angular_direction=AngularDirection.CLOCKWISE,
        )
        self.assertVectorAlmostEquals(half_circle.end_point(), (1, 0, 0), 3)
        self.assertVectorAlmostEquals(half_circle.start_point(), (-1, 0, 0), 3)

    def test_make_clockwise_half_circle2(self):
        half_circle = Edge.make_circle(
            radius=1,
            start_angle=90,
            end_angle=-90,
            angular_direction=AngularDirection.CLOCKWISE,
        )
        self.assertVectorAlmostEquals(half_circle.start_point(), (0, 1, 0), 3)
        self.assertVectorAlmostEquals(half_circle.end_point(), (0, -1, 0), 3)

    def test_arc_center(self):
        self.assertVectorAlmostEquals(Edge.make_ellipse(2, 1).arc_center, (0, 0, 0), 5)
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0, 0), (0, 0, 1)).arc_center

    def test_spline_with_parameters(self):
        spline = Edge.make_spline(
            points=[(0, 0, 0), (1, 1, 0), (2, 0, 0)], parameters=[0.0, 0.4, 1.0]
        )
        self.assertVectorAlmostEquals(spline.end_point(), (2, 0, 0), 5)
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
        self.assertVectorAlmostEquals(spline.end_point(), (3, 0, 0), 5)
        spline = Edge.make_spline_approx(
            [(0, 0), (1, 1), (2, 1), (3, 0)], smoothing=(1.0, 5.0, 10.0)
        )
        self.assertVectorAlmostEquals(spline.end_point(), (3, 0, 0), 5)

    def test_distribute_locations(self):
        line = Edge.make_line((0, 0, 0), (10, 0, 0))
        locs = line.distribute_locations(3)
        for i, x in enumerate([0, 5, 10]):
            self.assertVectorAlmostEquals(locs[i].position, (x, 0, 0), 5)
        self.assertVectorAlmostEquals(locs[0].orientation, (0, 90, 180), 5)

        locs = line.distribute_locations(3, positions_only=True)
        for i, x in enumerate([0, 5, 10]):
            self.assertVectorAlmostEquals(locs[i].position, (x, 0, 0), 5)
        self.assertVectorAlmostEquals(locs[0].orientation, (0, 0, 0), 5)

    def test_to_wire(self):
        edge = Edge.make_line((0, 0, 0), (1, 1, 1))
        for end in [0, 1]:
            self.assertVectorAlmostEquals(
                edge.position_at(end),
                edge.to_wire().position_at(end),
                5,
            )

    def test_arc_center2(self):
        edges = [
            Edge.make_circle(1, plane=Plane((1, 2, 3)), end_angle=30),
            Edge.make_ellipse(1, 0.5, plane=Plane((1, 2, 3)), end_angle=30),
        ]
        for edge in edges:
            self.assertVectorAlmostEquals(edge.arc_center, (1, 2, 3), 5)
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0), (1, 1)).arc_center

    def test_find_intersection_points(self):
        circle = Edge.make_circle(1)
        line = Edge.make_line((0, -2), (0, 2))
        crosses = circle.find_intersection_points(line)
        for target, actual in zip([(0, 1, 0), (0, -1, 0)], crosses):
            self.assertVectorAlmostEquals(actual, target, 5)

        with self.assertRaises(ValueError):
            circle.find_intersection_points(Edge.make_line((0, 0, -1), (0, 0, 1)))
        with self.assertRaises(ValueError):
            circle.find_intersection_points(Edge.make_line((0, 0, -1), (0, 0, 1)))

        self_intersect = Edge.make_spline([(-3, 2), (3, -2), (4, 0), (3, 2), (-3, -2)])
        self.assertVectorAlmostEquals(
            self_intersect.find_intersection_points()[0],
            (-2.6861636507066047, 0, 0),
            5,
        )
        line = Edge.make_line((1, -2), (1, 2))
        crosses = line.find_intersection_points(Axis.X)
        self.assertVectorAlmostEquals(crosses[0], (1, 0, 0), 5)

        with self.assertRaises(ValueError):
            line.find_intersection_points(Plane.YZ)

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
        self.assertVectorAlmostEquals(
            line.trim(0.25, 0.75).position_at(0), (-1, 0, 0), 5
        )
        self.assertVectorAlmostEquals(
            line.trim(0.25, 0.75).position_at(1), (1, 0, 0), 5
        )
        with self.assertRaises(ValueError):
            line.trim(0.75, 0.25)

    def test_trim_to_length(self):

        e1 = Edge.make_line((0, 0), (10, 10))
        e1_trim = e1.trim_to_length(0.0, 10)
        self.assertAlmostEqual(e1_trim.length, 10, 5)

        e2 = Edge.make_circle(10, start_angle=0, end_angle=90)
        e2_trim = e2.trim_to_length(0.5, 1)
        self.assertAlmostEqual(e2_trim.length, 1, 5)
        self.assertVectorAlmostEquals(
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
        self.assertVectorAlmostEquals(bbox.min, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(bbox.max, (1, 0.75, 0), 5)

    def test_mid_way(self):
        mid = Edge.make_mid_way(
            Edge.make_line((0, 0), (0, 1)), Edge.make_line((1, 0), (1, 1)), 0.25
        )
        self.assertVectorAlmostEquals(mid.position_at(0), (0.25, 0, 0), 5)
        self.assertVectorAlmostEquals(mid.position_at(1), (0.25, 1, 0), 5)

    def test_distribute_locations2(self):
        with self.assertRaises(ValueError):
            Edge.make_circle(1).distribute_locations(1)

        locs = Edge.make_circle(1).distribute_locations(5, positions_only=True)
        for i, loc in enumerate(locs):
            self.assertVectorAlmostEquals(
                loc.position,
                Vector(1, 0, 0).rotate(Axis.Z, i * 90).to_tuple(),
                5,
            )
            self.assertVectorAlmostEquals(loc.orientation, (0, 0, 0), 5)

    def test_find_tangent(self):
        circle = Edge.make_circle(1)
        parm = circle.find_tangent(135)[0]
        self.assertVectorAlmostEquals(
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

        with self.assertRaises(ValueError):
            edge.param_at_point((-1, 1))

    def test_conical_helix(self):
        helix = Edge.make_helix(1, 4, 1, normal=(-1, 0, 0), angle=10, lefthand=True)
        self.assertAlmostEqual(helix.bounding_box().min.X, -4, 5)

    def test_reverse(self):
        e1 = Edge.make_line((0, 0), (1, 1))
        self.assertVectorAlmostEquals(e1 @ 0.1, (0.1, 0.1, 0), 5)
        self.assertVectorAlmostEquals(e1.reversed() @ 0.1, (0.9, 0.9, 0), 5)

        e2 = Edge.make_circle(1, start_angle=0, end_angle=180)
        e2r = e2.reversed()
        self.assertAlmostEqual((e2 @ 0.1).X, -(e2r @ 0.1).X, 5)

    def test_init(self):
        with self.assertRaises(ValueError):
            Edge(direction=(1, 0, 0))


class TestFace(DirectApiTestCase):
    def test_make_surface_from_curves(self):
        bottom_edge = Edge.make_circle(radius=1, end_angle=90)
        top_edge = Edge.make_circle(radius=1, plane=Plane((0, 0, 1)), end_angle=90)
        curved = Face.make_surface_from_curves(bottom_edge, top_edge)
        self.assertTrue(curved.is_valid())
        self.assertAlmostEqual(curved.area, math.pi / 2, 5)
        self.assertVectorAlmostEquals(
            curved.normal_at(), (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 5
        )

        bottom_wire = Wire.make_circle(1)
        top_wire = Wire.make_circle(1, Plane((0, 0, 1)))
        curved = Face.make_surface_from_curves(bottom_wire, top_wire)
        self.assertTrue(curved.is_valid())
        self.assertAlmostEqual(curved.area, 2 * math.pi, 5)

    def test_center(self):
        test_face = Face(Wire.make_polygon([(0, 0), (1, 0), (1, 1), (0, 0)]))
        self.assertVectorAlmostEquals(
            test_face.center(CenterOf.MASS), (2 / 3, 1 / 3, 0), 1
        )
        self.assertVectorAlmostEquals(
            test_face.center(CenterOf.BOUNDING_BOX),
            (0.5, 0.5, 0),
            5,
        )

    def test_face_volume(self):
        rect = Face.make_rect(1, 1)
        self.assertAlmostEqual(rect.volume, 0, 5)

    def test_chamfer_2d(self):
        test_face = Face.make_rect(10, 10)
        test_face = test_face.chamfer_2d(
            distance=1, distance2=2, vertices=test_face.vertices()
        )
        self.assertAlmostEqual(test_face.area, 100 - 4 * 0.5 * 1 * 2)

    def test_chamfer_2d_reference(self):
        test_face = Face.make_rect(10, 10)
        edge = test_face.edges().sort_by(Axis.Y)[0]
        vertex = edge.vertices().sort_by(Axis.X)[0]
        test_face = test_face.chamfer_2d(
            distance=1, distance2=2, vertices=[vertex], edge=edge
        )
        self.assertAlmostEqual(test_face.area, 100 - 0.5 * 1 * 2)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.Y)[0].length, 9)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.X)[0].length, 8)

    def test_chamfer_2d_reference_inverted(self):
        test_face = Face.make_rect(10, 10)
        edge = test_face.edges().sort_by(Axis.Y)[0]
        vertex = edge.vertices().sort_by(Axis.X)[0]
        test_face = test_face.chamfer_2d(
            distance=2, distance2=1, vertices=[vertex], edge=edge
        )
        self.assertAlmostEqual(test_face.area, 100 - 0.5 * 1 * 2)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.Y)[0].length, 8)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.X)[0].length, 9)

    def test_chamfer_2d_error_checking(self):
        with self.assertRaises(ValueError):
            test_face = Face.make_rect(10, 10)
            edge = test_face.edges().sort_by(Axis.Y)[0]
            vertex = edge.vertices().sort_by(Axis.X)[0]
            other_edge = test_face.edges().sort_by(Axis.Y)[-1]
            test_face = test_face.chamfer_2d(
                distance=1, distance2=2, vertices=[vertex], edge=other_edge
            )

    def test_make_rect(self):
        test_face = Face.make_plane()
        self.assertVectorAlmostEquals(test_face.normal_at(), (0, 0, 1), 5)

    def test_length_width(self):
        test_face = Face.make_rect(8, 10, Plane.XZ)
        self.assertAlmostEqual(test_face.length, 8, 5)
        self.assertAlmostEqual(test_face.width, 10, 5)

    def test_geometry(self):
        box = Solid.make_box(1, 1, 2)
        self.assertEqual(box.faces().sort_by(Axis.Z).last.geometry, "SQUARE")
        self.assertEqual(box.faces().sort_by(Axis.Y).last.geometry, "RECTANGLE")
        with BuildPart() as test:
            with BuildSketch():
                RegularPolygon(1, 3)
            extrude(amount=1)
        self.assertEqual(test.faces().sort_by(Axis.Z).last.geometry, "POLYGON")

    def test_negate(self):
        square = Face.make_rect(1, 1)
        self.assertVectorAlmostEquals(square.normal_at(), (0, 0, 1), 5)
        flipped_square = -square
        self.assertVectorAlmostEquals(flipped_square.normal_at(), (0, 0, -1), 5)

    def test_offset(self):
        bbox = Face.make_rect(2, 2, Plane.XY).offset(5).bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-1, -1, 5), 5)
        self.assertVectorAlmostEquals(bbox.max, (1, 1, 5), 5)

    def test_make_from_wires(self):
        outer = Wire.make_circle(10)
        inners = [
            Wire.make_circle(1).locate(Location((-2, 2, 0))),
            Wire.make_circle(1).locate(Location((2, 2, 0))),
        ]
        happy = Face(outer, inners)
        self.assertAlmostEqual(happy.area, math.pi * (10**2 - 2), 5)

        outer = Edge.make_circle(10, end_angle=180).to_wire()
        with self.assertRaises(ValueError):
            Face(outer, inners)
        with self.assertRaises(ValueError):
            Face(Wire.make_circle(10, Plane.XZ), inners)

        outer = Wire.make_circle(10)
        inners = [
            Wire.make_circle(1).locate(Location((-2, 2, 0))),
            Edge.make_circle(1, end_angle=180).to_wire().locate(Location((2, 2, 0))),
        ]
        with self.assertRaises(ValueError):
            Face(outer, inners)

    def test_sew_faces(self):
        patches = [
            Face.make_rect(1, 1, Plane((x, y, z)))
            for x in range(2)
            for y in range(2)
            for z in range(3)
        ]
        random.shuffle(patches)
        sheets = Face.sew_faces(patches)
        self.assertEqual(len(sheets), 3)
        self.assertEqual(len(sheets[0]), 4)
        self.assertTrue(isinstance(sheets[0][0], Face))

    def test_surface_from_array_of_points(self):
        pnts = [
            [
                Vector(x, y, math.cos(math.pi * x / 10) + math.sin(math.pi * y / 10))
                for x in range(11)
            ]
            for y in range(11)
        ]
        surface = Face.make_surface_from_array_of_points(pnts)
        bbox = surface.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (0, 0, -1), 3)
        self.assertVectorAlmostEquals(bbox.max, (10, 10, 2), 2)

    def test_bezier_surface(self):
        points = [
            [
                (x, y, 2 if x == 0 and y == 0 else 1 if x == 0 or y == 0 else 0)
                for x in range(-1, 2)
            ]
            for y in range(-1, 2)
        ]
        surface = Face.make_bezier_surface(points)
        bbox = surface.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-1, -1, 0), 3)
        self.assertVectorAlmostEquals(bbox.max, (+1, +1, +1), 1)
        self.assertLess(bbox.max.Z, 1.0)

        weights = [
            [2 if x == 0 or y == 0 else 1 for x in range(-1, 2)] for y in range(-1, 2)
        ]
        surface = Face.make_bezier_surface(points, weights)
        bbox = surface.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-1, -1, 0), 3)
        self.assertGreater(bbox.max.Z, 1.0)

        too_many_points = [
            [
                (x, y, 2 if x == 0 and y == 0 else 1 if x == 0 or y == 0 else 0)
                for x in range(-1, 27)
            ]
            for y in range(-1, 27)
        ]

        with self.assertRaises(ValueError):
            Face.make_bezier_surface([[(0, 0)]])
        with self.assertRaises(ValueError):
            Face.make_bezier_surface(points, [[1, 1], [1, 1]])
        with self.assertRaises(ValueError):
            Face.make_bezier_surface(too_many_points)

    def test_thicken(self):
        pnts = [
            [
                Vector(x, y, math.cos(math.pi * x / 10) + math.sin(math.pi * y / 10))
                for x in range(11)
            ]
            for y in range(11)
        ]
        surface = Face.make_surface_from_array_of_points(pnts)
        solid = surface.thicken(1)
        self.assertAlmostEqual(solid.volume, 101.59, 2)

        square = Face.make_rect(10, 10)
        bbox = square.thicken(1, normal_override=(0, 0, -1)).bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-5, -5, -1), 5)
        self.assertVectorAlmostEquals(bbox.max, (5, 5, 0), 5)

    def test_make_holes(self):
        radius = 10
        circumference = 2 * math.pi * radius
        hex_diagonal = 4 * (circumference / 10) / 3
        cylinder = Solid.make_cylinder(radius, hex_diagonal * 5)
        cylinder_wall: Face = cylinder.faces().filter_by(GeomType.PLANE, reverse=True)[
            0
        ]
        with BuildSketch(Plane.XZ.offset(radius)) as hex:
            with Locations((0, hex_diagonal)):
                RegularPolygon(
                    hex_diagonal * 0.4, 6, align=(Align.CENTER, Align.CENTER)
                )
        hex_wire_vertical: Wire = hex.sketch.faces()[0].outer_wire()

        projected_wire: Wire = hex_wire_vertical.project_to_shape(
            target_object=cylinder, center=(0, 0, hex_wire_vertical.center().Z)
        )[0]
        projected_wires = [
            projected_wire.rotate(Axis.Z, -90 + i * 360 / 10).translate(
                (0, 0, (j + (i % 2) / 2) * hex_diagonal)
            )
            for i in range(5)
            for j in range(4 - i % 2)
        ]
        cylinder_walls_with_holes = cylinder_wall.make_holes(projected_wires)
        self.assertTrue(cylinder_walls_with_holes.is_valid())
        self.assertLess(cylinder_walls_with_holes.area, cylinder_wall.area)

    def test_is_inside(self):
        square = Face.make_rect(10, 10)
        self.assertTrue(square.is_inside((1, 1)))
        self.assertFalse(square.is_inside((20, 1)))

    def test_import_stl(self):
        torus = Solid.make_torus(10, 1)
        # exporter = Mesher()
        # exporter.add_shape(torus)
        # exporter.write("test_torus.stl")
        export_stl(torus, "test_torus.stl")
        imported_torus = import_stl("test_torus.stl")
        # The torus from stl is tessellated therefore the areas will only be close
        self.assertAlmostEqual(imported_torus.area, torus.area, 0)
        os.remove("test_torus.stl")

    def test_is_coplanar(self):
        square = Face.make_rect(1, 1, plane=Plane.XZ)
        self.assertTrue(square.is_coplanar(Plane.XZ))
        self.assertTrue((-square).is_coplanar(Plane.XZ))
        self.assertFalse(square.is_coplanar(Plane.XY))
        surface: Face = Solid.make_sphere(1).faces()[0]
        self.assertFalse(surface.is_coplanar(Plane.XY))

    def test_center_location(self):
        square = Face.make_rect(1, 1, plane=Plane.XZ)
        cl = square.center_location
        self.assertVectorAlmostEquals(cl.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(Plane(cl).z_dir, Plane.XZ.z_dir, 5)

    def test_position_at(self):
        square = Face.make_rect(2, 2, plane=Plane.XZ.offset(1))
        p = square.position_at(0.25, 0.75)
        self.assertVectorAlmostEquals(p, (-0.5, -1.0, 0.5), 5)

    def test_location_at(self):
        bottom = Box(1, 2, 3, align=Align.MIN).faces().filter_by(Axis.Z)[0]
        loc = bottom.location_at(0.5, 0.5)
        self.assertVectorAlmostEquals(loc.position, (0.5, 1, 0), 5)
        self.assertVectorAlmostEquals(loc.orientation, (-180, 0, -180), 5)

        front = Box(1, 2, 3, align=Align.MIN).faces().filter_by(Axis.X)[0]
        loc = front.location_at(0.5, 0.5, x_dir=(0, 0, 1))
        self.assertVectorAlmostEquals(loc.position, (0.0, 1.0, 1.5), 5)
        self.assertVectorAlmostEquals(loc.orientation, (0, -90, 0), 5)

    def test_make_surface(self):
        corners = [Vector(x, y) for x in [-50.5, 50.5] for y in [-24.5, 24.5]]
        net_exterior = Wire(
            [
                Edge.make_line(corners[3], corners[1]),
                Edge.make_line(corners[1], corners[0]),
                Edge.make_line(corners[0], corners[2]),
                Edge.make_three_point_arc(
                    corners[2],
                    (corners[2] + corners[3]) / 2 - Vector(0, 0, 3),
                    corners[3],
                ),
            ]
        )
        surface = Face.make_surface(
            net_exterior,
            surface_points=[Vector(0, 0, -5)],
        )
        hole_flat = Wire.make_circle(10)
        hole = hole_flat.project_to_shape(surface, (0, 0, -1))[0]
        surface = Face.make_surface(
            exterior=net_exterior,
            surface_points=[Vector(0, 0, -5)],
            interior_wires=[hole],
        )
        self.assertTrue(surface.is_valid())
        self.assertEqual(surface.geom_type, GeomType.BSPLINE)
        bbox = surface.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-50.5, -24.5, -5.113393280136395), 5)
        self.assertVectorAlmostEquals(bbox.max, (50.5, 24.5, 0), 5)

        # With no surface point
        surface = Face.make_surface(net_exterior)
        bbox = surface.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-50.5, -24.5, -3), 5)
        self.assertVectorAlmostEquals(bbox.max, (50.5, 24.5, 0), 5)

        # Exterior Edge
        surface = Face.make_surface([Edge.make_circle(50)], surface_points=[(0, 0, -5)])
        bbox = surface.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-50, -50, -5), 5)
        self.assertVectorAlmostEquals(bbox.max, (50, 50, 0), 5)

    def test_make_surface_error_checking(self):
        with self.assertRaises(ValueError):
            Face.make_surface(Edge.make_line((0, 0), (1, 0)))

        with self.assertRaises(RuntimeError):
            Face.make_surface([Edge.make_line((0, 0), (1, 0))])

        if platform.system() != "Darwin":
            with self.assertRaises(RuntimeError):
                Face.make_surface(
                    [Edge.make_circle(50)], surface_points=[(0, 0, -50), (0, 0, 50)]
                )

            with self.assertRaises(RuntimeError):
                Face.make_surface(
                    [Edge.make_circle(50)],
                    interior_wires=[Wire.make_circle(5, Plane.XZ)],
                )

    def test_sweep(self):
        edge = Edge.make_line((1, 0), (2, 0))
        path = Wire.make_circle(1)
        circle_with_hole = Face.sweep(edge, path)
        self.assertTrue(isinstance(circle_with_hole, Face))
        self.assertAlmostEqual(circle_with_hole.area, math.pi * (2**2 - 1**1), 5)
        with self.assertRaises(ValueError):
            Face.sweep(edge, Polyline((0, 0), (0.1, 0), (0.2, 0.1)))

    def test_to_arcs(self):
        with BuildSketch() as bs:
            with BuildLine() as bl:
                Polyline((0, 0), (1, 0), (1.5, 0.5), (2, 0), (2, 1), (0, 1), (0, 0))
                fillet(bl.vertices(), radius=0.1)
            make_face()
        smooth = bs.faces()[0]
        fragmented = smooth.to_arcs()
        self.assertLess(len(smooth.edges()), len(fragmented.edges()))

    def test_outer_wire(self):
        face = (Face.make_rect(1, 1) - Face.make_rect(0.5, 0.5)).face()
        self.assertAlmostEqual(face.outer_wire().length, 4, 5)

    def test_wire(self):
        face = (Face.make_rect(1, 1) - Face.make_rect(0.5, 0.5)).face()
        with self.assertWarns(UserWarning):
            outer = face.wire()
        self.assertAlmostEqual(outer.length, 4, 5)

    def test_constructor(self):
        with self.assertRaises(ValueError):
            Face(bob="fred")

    def test_normal_at(self):
        face = Face.make_rect(1, 1)
        self.assertVectorAlmostEquals(face.normal_at(0, 0), (0, 0, 1), 5)
        self.assertVectorAlmostEquals(
            face.normal_at(face.position_at(0, 0)), (0, 0, 1), 5
        )
        with self.assertRaises(ValueError):
            face.normal_at(0)
        with self.assertRaises(ValueError):
            face.normal_at(center=(0, 0))
        face = Cylinder(1, 1).faces().filter_by(GeomType.CYLINDER)[0]
        self.assertVectorAlmostEquals(face.normal_at(0, 1), (1, 0, 0), 5)


class TestFunctions(unittest.TestCase):
    def test_edges_to_wires(self):
        square_edges = Face.make_rect(1, 1).edges()
        rectangle_edges = Face.make_rect(2, 1, Plane((5, 0))).edges()
        wires = edges_to_wires(square_edges + rectangle_edges)
        self.assertEqual(len(wires), 2)
        self.assertAlmostEqual(wires[0].length, 4, 5)
        self.assertAlmostEqual(wires[1].length, 6, 5)

    def test_polar(self):
        pnt = polar(1, 30)
        self.assertAlmostEqual(pnt[0], math.sqrt(3) / 2, 5)
        self.assertAlmostEqual(pnt[1], 0.5, 5)

    def test_new_edges(self):
        c = Solid.make_cylinder(1, 5)
        s = Solid.make_sphere(2)
        s_minus_c = s - c
        seams = new_edges(c, s, combined=s_minus_c)
        self.assertEqual(len(seams), 1)
        self.assertAlmostEqual(seams[0].radius, 1, 5)

    def test_delta(self):
        cyl = Solid.make_cylinder(1, 5)
        sph = Solid.make_sphere(2)
        con = Solid.make_cone(2, 1, 2)
        plug = delta([cyl, sph, con], [sph, con])
        self.assertEqual(len(plug), 1)
        self.assertEqual(plug[0], cyl)

    def test_parse_intersect_args(self):

        with self.assertRaises(TypeError):
            Vector(1, 1, 1) & ("x", "y", "z")


class TestImportExport(DirectApiTestCase):
    def test_import_export(self):
        original_box = Solid.make_box(1, 1, 1)
        export_step(original_box, "test_box.step")
        step_box = import_step("test_box.step")
        self.assertTrue(step_box.is_valid())
        self.assertAlmostEqual(step_box.volume, 1, 5)
        export_brep(step_box, "test_box.brep")
        brep_box = import_brep("test_box.brep")
        self.assertTrue(brep_box.is_valid())
        self.assertAlmostEqual(brep_box.volume, 1, 5)
        os.remove("test_box.step")
        os.remove("test_box.brep")
        with self.assertRaises(FileNotFoundError):
            step_box = import_step("test_box.step")

    def test_import_stl(self):
        # export solid
        original_box = Solid.make_box(1, 2, 3)
        exporter = Mesher()
        exporter.add_shape(original_box)
        exporter.write("test.stl")

        # import as face
        stl_box = import_stl("test.stl")
        self.assertVectorAlmostEquals(stl_box.position, (0, 0, 0), 5)


class TestJupyter(DirectApiTestCase):
    def test_repr_javascript(self):
        shape = Solid.make_box(1, 1, 1)

        # Test no exception on rendering to js
        js1 = shape._repr_javascript_()

        assert "function render" in js1

    def test_display_error(self):
        with self.assertRaises(AttributeError):
            display(Vector())


class TestLocation(DirectApiTestCase):
    def test_location(self):
        loc0 = Location()
        T = loc0.wrapped.Transformation().TranslationPart()
        self.assertTupleAlmostEquals((T.X(), T.Y(), T.Z()), (0, 0, 0), 6)
        angle = loc0.wrapped.Transformation().GetRotation().GetRotationAngle() * RAD2DEG
        self.assertAlmostEqual(0, angle)

        # Tuple
        loc0 = Location((0, 0, 1))

        T = loc0.wrapped.Transformation().TranslationPart()
        self.assertTupleAlmostEquals((T.X(), T.Y(), T.Z()), (0, 0, 1), 6)

        # List
        loc0 = Location([0, 0, 1])

        T = loc0.wrapped.Transformation().TranslationPart()
        self.assertTupleAlmostEquals((T.X(), T.Y(), T.Z()), (0, 0, 1), 6)

        # Vector
        loc1 = Location(Vector(0, 0, 1))

        T = loc1.wrapped.Transformation().TranslationPart()
        self.assertTupleAlmostEquals((T.X(), T.Y(), T.Z()), (0, 0, 1), 6)

        # rotation + translation
        loc2 = Location(Vector(0, 0, 1), Vector(0, 0, 1), 45)

        angle = loc2.wrapped.Transformation().GetRotation().GetRotationAngle() * RAD2DEG
        self.assertAlmostEqual(45, angle)

        # gp_Trsf
        T = gp_Trsf()
        T.SetTranslation(gp_Vec(0, 0, 1))
        loc3 = Location(T)

        self.assertEqual(
            loc1.wrapped.Transformation().TranslationPart().Z(),
            loc3.wrapped.Transformation().TranslationPart().Z(),
        )

        # Test creation from the OCP.gp.gp_Trsf object
        loc4 = Location(gp_Trsf())
        self.assertTupleAlmostEquals(loc4.to_tuple()[0], (0, 0, 0), 7)
        self.assertTupleAlmostEquals(loc4.to_tuple()[1], (0, 0, 0), 7)

        # Test creation from Plane and Vector
        loc4 = Location(Plane.XY, (0, 0, 1))
        self.assertTupleAlmostEquals(loc4.to_tuple()[0], (0, 0, 1), 7)
        self.assertTupleAlmostEquals(loc4.to_tuple()[1], (0, 0, 0), 7)

        # Test composition
        loc4 = Location((0, 0, 0), Vector(0, 0, 1), 15)

        loc5 = loc1 * loc4
        loc6 = loc4 * loc4
        loc7 = loc4**2

        T = loc5.wrapped.Transformation().TranslationPart()
        self.assertTupleAlmostEquals((T.X(), T.Y(), T.Z()), (0, 0, 1), 6)

        angle5 = (
            loc5.wrapped.Transformation().GetRotation().GetRotationAngle() * RAD2DEG
        )
        self.assertAlmostEqual(15, angle5)

        angle6 = (
            loc6.wrapped.Transformation().GetRotation().GetRotationAngle() * RAD2DEG
        )
        self.assertAlmostEqual(30, angle6)

        angle7 = (
            loc7.wrapped.Transformation().GetRotation().GetRotationAngle() * RAD2DEG
        )
        self.assertAlmostEqual(30, angle7)

        # Test error handling on creation
        with self.assertRaises(TypeError):
            Location("xy_plane")

        # Test that the computed rotation matrix and intrinsic euler angles return the same

        about_x = uniform(-2 * math.pi, 2 * math.pi)
        about_y = uniform(-2 * math.pi, 2 * math.pi)
        about_z = uniform(-2 * math.pi, 2 * math.pi)

        rot_x = gp_Trsf()
        rot_x.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), about_x)
        rot_y = gp_Trsf()
        rot_y.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), about_y)
        rot_z = gp_Trsf()
        rot_z.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), about_z)
        loc1 = Location(rot_x * rot_y * rot_z)

        q = gp_Quaternion()
        q.SetEulerAngles(
            gp_EulerSequence.gp_Intrinsic_XYZ,
            about_x,
            about_y,
            about_z,
        )
        t = gp_Trsf()
        t.SetRotationPart(q)
        loc2 = Location(t)

        self.assertTupleAlmostEquals(loc1.to_tuple()[0], loc2.to_tuple()[0], 6)
        self.assertTupleAlmostEquals(loc1.to_tuple()[1], loc2.to_tuple()[1], 6)

        loc1 = Location((1, 2), 34)
        self.assertTupleAlmostEquals(loc1.to_tuple()[0], (1, 2, 0), 6)
        self.assertTupleAlmostEquals(loc1.to_tuple()[1], (0, 0, 34), 6)

        rot_angles = (-115.00, 35.00, -135.00)
        loc2 = Location((1, 2, 3), rot_angles)
        self.assertTupleAlmostEquals(loc2.to_tuple()[0], (1, 2, 3), 6)
        self.assertTupleAlmostEquals(loc2.to_tuple()[1], rot_angles, 6)

        loc3 = Location(loc2)
        self.assertTupleAlmostEquals(loc3.to_tuple()[0], (1, 2, 3), 6)
        self.assertTupleAlmostEquals(loc3.to_tuple()[1], rot_angles, 6)

    def test_location_parameters(self):
        loc = Location((10, 20, 30))
        self.assertVectorAlmostEquals(loc.position, (10, 20, 30), 5)

        loc = Location((10, 20, 30), (10, 20, 30))
        self.assertVectorAlmostEquals(loc.position, (10, 20, 30), 5)
        self.assertVectorAlmostEquals(loc.orientation, (10, 20, 30), 5)

        loc = Location((10, 20, 30), (10, 20, 30), Intrinsic.XYZ)
        self.assertVectorAlmostEquals(loc.position, (10, 20, 30), 5)
        self.assertVectorAlmostEquals(loc.orientation, (10, 20, 30), 5)

        loc = Location((10, 20, 30), (30, 20, 10), Extrinsic.ZYX)
        self.assertVectorAlmostEquals(loc.position, (10, 20, 30), 5)
        self.assertVectorAlmostEquals(loc.orientation, (10, 20, 30), 5)

        with self.assertRaises(TypeError):
            Location(x=10)

        with self.assertRaises(TypeError):
            Location((10, 20, 30), (30, 20, 10), (10, 20, 30))

        with self.assertRaises(TypeError):
            Location(Intrinsic.XYZ)

    def test_location_repr_and_str(self):
        self.assertEqual(
            repr(Location()), "(p=(0.00, 0.00, 0.00), o=(-0.00, 0.00, -0.00))"
        )
        self.assertEqual(
            str(Location()),
            "Location: (position=(0.00, 0.00, 0.00), orientation=(-0.00, 0.00, -0.00))",
        )
        loc = Location((1, 2, 3), (33, 45, 67))
        self.assertEqual(
            str(loc),
            "Location: (position=(1.00, 2.00, 3.00), orientation=(33.00, 45.00, 67.00))",
        )

    def test_location_inverted(self):
        loc = Location(Plane.XZ)
        self.assertVectorAlmostEquals(loc.inverse().orientation, (-90, 0, 0), 6)

    def test_set_position(self):
        loc = Location(Plane.XZ)
        loc.position = (1, 2, 3)
        self.assertVectorAlmostEquals(loc.position, (1, 2, 3), 6)
        self.assertVectorAlmostEquals(loc.orientation, (90, 0, 0), 6)

    def test_set_orientation(self):
        loc = Location((1, 2, 3), (90, 0, 0))
        loc.orientation = (-90, 0, 0)
        self.assertVectorAlmostEquals(loc.position, (1, 2, 3), 6)
        self.assertVectorAlmostEquals(loc.orientation, (-90, 0, 0), 6)

    def test_copy(self):
        loc1 = Location((1, 2, 3), (90, 45, 22.5))
        loc2 = copy.copy(loc1)
        loc3 = copy.deepcopy(loc1)
        self.assertVectorAlmostEquals(loc1.position, loc2.position.to_tuple(), 6)
        self.assertVectorAlmostEquals(loc1.orientation, loc2.orientation.to_tuple(), 6)
        self.assertVectorAlmostEquals(loc1.position, loc3.position.to_tuple(), 6)
        self.assertVectorAlmostEquals(loc1.orientation, loc3.orientation.to_tuple(), 6)

    def test_to_axis(self):
        axis = Location((1, 2, 3), (-90, 0, 0)).to_axis()
        self.assertVectorAlmostEquals(axis.position, (1, 2, 3), 6)
        self.assertVectorAlmostEquals(axis.direction, (0, 1, 0), 6)

    def test_eq(self):
        loc = Location((1, 2, 3), (4, 5, 6))
        diff_position = Location((10, 20, 30), (4, 5, 6))
        diff_orientation = Location((1, 2, 3), (40, 50, 60))
        same = Location((1, 2, 3), (4, 5, 6))

        self.assertEqual(loc, same)
        self.assertNotEqual(loc, diff_position)
        self.assertNotEqual(loc, diff_orientation)

    def test_neg(self):
        loc = Location((1, 2, 3), (0, 35, 127))
        n_loc = -loc
        self.assertVectorAlmostEquals(n_loc.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(n_loc.orientation, (180, -35, -127), 5)

    def test_mult_iterable(self):
        locs = Location((1, 2, 0)) * GridLocations(4, 4, 2, 1)
        self.assertVectorAlmostEquals(locs[0].position, (-1, 2, 0), 5)
        self.assertVectorAlmostEquals(locs[1].position, (3, 2, 0), 5)

    def test_as_json(self):
        data_dict = {
            "part1": {
                "joint_one": Location((1, 2, 3), (4, 5, 6)),
                "joint_two": Location((7, 8, 9), (10, 11, 12)),
            },
            "part2": {
                "joint_one": Location((13, 14, 15), (16, 17, 18)),
                "joint_two": Location((19, 20, 21), (22, 23, 24)),
            },
        }

        # Serializing json with custom Location encoder
        json_object = json.dumps(data_dict, indent=4, cls=LocationEncoder)

        # Writing to sample.json
        with open("sample.json", "w") as outfile:
            outfile.write(json_object)

        # Reading from sample.json
        with open("sample.json", "r") as infile:
            read_json = json.load(infile, object_hook=LocationEncoder.location_hook)

        # Validate locations
        for key, value in read_json.items():
            for k, v in value.items():
                if key == "part1" and k == "joint_one":
                    self.assertVectorAlmostEquals(v.position, (1, 2, 3), 5)
                elif key == "part1" and k == "joint_two":
                    self.assertVectorAlmostEquals(v.position, (7, 8, 9), 5)
                elif key == "part2" and k == "joint_one":
                    self.assertVectorAlmostEquals(v.position, (13, 14, 15), 5)
                elif key == "part2" and k == "joint_two":
                    self.assertVectorAlmostEquals(v.position, (19, 20, 21), 5)
                else:
                    self.assertTrue(False)
        os.remove("sample.json")

    def test_intersection(self):
        e = Edge.make_line((0, 0, 0), (1, 1, 1))
        l0 = e.location_at(0)
        l1 = e.location_at(1)
        self.assertIsNone(l0 & l1)
        self.assertEqual(l1 & l1, l1)

        i = l1 & Vector(1, 1, 1)
        self.assertTrue(isinstance(i, Vector))
        self.assertVectorAlmostEquals(i, (1, 1, 1), 5)

        i = l1 & Axis((0.5, 0.5, 0.5), (1, 1, 1))
        self.assertTrue(isinstance(i, Location))
        self.assertEqual(i, l1)

        p = Plane.XY.rotated((45, 0, 0)).shift_origin((1, 0, 0))
        l = Location((1, 0, 0), (1, 0, 0), 45)
        i = l & p
        self.assertTrue(isinstance(i, Location))
        self.assertVectorAlmostEquals(i.position, (1, 0, 0), 5)
        self.assertVectorAlmostEquals(i.orientation, l.orientation, 5)

        b = Solid.make_box(1, 1, 1)
        l = Location((0.5, 0.5, 0.5), (1, 0, 0), 45)
        i = (l & b).vertex()
        self.assertTrue(isinstance(i, Vertex))
        self.assertVectorAlmostEquals(Vector(i), (0.5, 0.5, 0.5), 5)


class TestMatrix(DirectApiTestCase):
    def test_matrix_creation_and_access(self):
        def matrix_vals(m):
            return [[m[r, c] for c in range(4)] for r in range(4)]

        # default constructor creates a 4x4 identity matrix
        m = Matrix()
        identity = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        self.assertEqual(identity, matrix_vals(m))

        vals4x4 = [
            [1.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 2.0],
            [0.0, 0.0, 1.0, 3.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        vals4x4_tuple = tuple(tuple(r) for r in vals4x4)

        # test constructor with 16-value input
        m = Matrix(vals4x4)
        self.assertEqual(vals4x4, matrix_vals(m))
        m = Matrix(vals4x4_tuple)
        self.assertEqual(vals4x4, matrix_vals(m))

        # test constructor with 12-value input (the last 4 are an implied
        # [0,0,0,1])
        m = Matrix(vals4x4[:3])
        self.assertEqual(vals4x4, matrix_vals(m))
        m = Matrix(vals4x4_tuple[:3])
        self.assertEqual(vals4x4, matrix_vals(m))

        # Test 16-value input with invalid values for the last 4
        invalid = [
            [1.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 2.0],
            [0.0, 0.0, 1.0, 3.0],
            [1.0, 2.0, 3.0, 4.0],
        ]
        with self.assertRaises(ValueError):
            Matrix(invalid)
        # Test input with invalid type
        with self.assertRaises(TypeError):
            Matrix("invalid")
        # Test input with invalid size / nested types
        with self.assertRaises(TypeError):
            Matrix([[1, 2, 3, 4], [1, 2, 3], [1, 2, 3, 4]])
        with self.assertRaises(TypeError):
            Matrix([1, 2, 3])

        # Invalid sub-type
        with self.assertRaises(TypeError):
            Matrix([[1, 2, 3, 4], "abc", [1, 2, 3, 4]])

        # test out-of-bounds access
        m = Matrix()
        with self.assertRaises(IndexError):
            m[0, 4]
        with self.assertRaises(IndexError):
            m[4, 0]
        with self.assertRaises(IndexError):
            m["ab"]

        # test __repr__ methods
        m = Matrix(vals4x4)
        mRepr = "Matrix([[1.0, 0.0, 0.0, 1.0],\n        [0.0, 1.0, 0.0, 2.0],\n        [0.0, 0.0, 1.0, 3.0],\n        [0.0, 0.0, 0.0, 1.0]])"
        self.assertEqual(repr(m), mRepr)
        self.assertEqual(str(eval(repr(m))), mRepr)

    def test_matrix_functionality(self):
        # Test rotate methods
        def matrix_almost_equal(m, target_matrix):
            for r, row in enumerate(target_matrix):
                for c, target_value in enumerate(row):
                    self.assertAlmostEqual(m[r, c], target_value)

        root_3_over_2 = math.sqrt(3) / 2
        m_rotate_x_30 = [
            [1, 0, 0, 0],
            [0, root_3_over_2, -1 / 2, 0],
            [0, 1 / 2, root_3_over_2, 0],
            [0, 0, 0, 1],
        ]
        mx = Matrix()
        mx.rotate(Axis.X, 30 * DEG2RAD)
        matrix_almost_equal(mx, m_rotate_x_30)

        m_rotate_y_30 = [
            [root_3_over_2, 0, 1 / 2, 0],
            [0, 1, 0, 0],
            [-1 / 2, 0, root_3_over_2, 0],
            [0, 0, 0, 1],
        ]
        my = Matrix()
        my.rotate(Axis.Y, 30 * DEG2RAD)
        matrix_almost_equal(my, m_rotate_y_30)

        m_rotate_z_30 = [
            [root_3_over_2, -1 / 2, 0, 0],
            [1 / 2, root_3_over_2, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        mz = Matrix()
        mz.rotate(Axis.Z, 30 * DEG2RAD)
        matrix_almost_equal(mz, m_rotate_z_30)

        # Test matrix multiply vector
        v = Vector(1, 0, 0)
        self.assertVectorAlmostEquals(mz.multiply(v), (root_3_over_2, 1 / 2, 0), 7)

        # Test matrix multiply matrix
        m_rotate_xy_30 = [
            [root_3_over_2, 0, 1 / 2, 0],
            [1 / 4, root_3_over_2, -root_3_over_2 / 2, 0],
            [-root_3_over_2 / 2, 1 / 2, 3 / 4, 0],
            [0, 0, 0, 1],
        ]
        mxy = mx.multiply(my)
        matrix_almost_equal(mxy, m_rotate_xy_30)

        # Test matrix inverse
        vals4x4 = [[1, 2, 3, 4], [5, 1, 6, 7], [8, 9, 1, 10], [0, 0, 0, 1]]
        vals4x4_invert = [
            [-53 / 144, 25 / 144, 1 / 16, -53 / 144],
            [43 / 144, -23 / 144, 1 / 16, -101 / 144],
            [37 / 144, 7 / 144, -1 / 16, -107 / 144],
            [0, 0, 0, 1],
        ]
        m = Matrix(vals4x4).inverse()
        matrix_almost_equal(m, vals4x4_invert)

        # Test matrix created from transfer function
        rot_x = gp_Trsf()
        θ = math.pi
        rot_x.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), θ)
        m = Matrix(rot_x)
        rot_x_matrix = [
            [1, 0, 0, 0],
            [0, math.cos(θ), -math.sin(θ), 0],
            [0, math.sin(θ), math.cos(θ), 0],
            [0, 0, 0, 1],
        ]
        matrix_almost_equal(m, rot_x_matrix)

        # Test copy
        m2 = copy.copy(m)
        matrix_almost_equal(m2, rot_x_matrix)
        m3 = copy.deepcopy(m)
        matrix_almost_equal(m3, rot_x_matrix)


class TestMixin1D(DirectApiTestCase):
    """Test the add in methods"""

    def test_position_at(self):
        self.assertVectorAlmostEquals(
            Edge.make_line((0, 0, 0), (1, 1, 1)).position_at(0.5),
            (0.5, 0.5, 0.5),
            5,
        )
        # Not sure what PARAMETER mode returns - but it's in the ballpark
        point = (
            Edge.make_line((0, 0, 0), (1, 1, 1))
            .position_at(0.5, position_mode=PositionMode.PARAMETER)
            .to_tuple()
        )
        self.assertTrue(all([0.0 < v < 1.0 for v in point]))

        wire = Wire([Edge.make_line((0, 0, 0), (10, 0, 0))])
        self.assertVectorAlmostEquals(wire.position_at(0.3), (3, 0, 0), 5)
        self.assertVectorAlmostEquals(
            wire.position_at(3, position_mode=PositionMode.LENGTH), (3, 0, 0), 5
        )
        self.assertVectorAlmostEquals(wire.edge().position_at(0.3), (3, 0, 0), 5)
        self.assertVectorAlmostEquals(
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
        self.assertVectorAlmostEquals(p1, (-1, 0, 0), 14)
        self.assertVectorAlmostEquals(p2, (-1, 0, 0), 14)
        self.assertVectorAlmostEquals(p1, p2, 14)

        circle_edge = Edge.make_circle(1)
        p3 = circle_edge.position_at(math.pi, position_mode=PositionMode.LENGTH)
        p4 = circle_edge.position_at(math.pi / circle_edge.length)
        self.assertVectorAlmostEquals(p3, (-1, 0, 0), 14)
        self.assertVectorAlmostEquals(p4, (-1, 0, 0), 14)
        self.assertVectorAlmostEquals(p3, p4, 14)

        circle = Wire(
            [
                Edge.make_circle(2, start_angle=0, end_angle=180),
                Edge.make_circle(2, start_angle=180, end_angle=360),
            ]
        )
        self.assertVectorAlmostEquals(
            circle.position_at(0.5),
            (-2, 0, 0),
            5,
        )
        self.assertVectorAlmostEquals(
            circle.position_at(2 * math.pi, position_mode=PositionMode.LENGTH),
            (-2, 0, 0),
            5,
        )

    def test_positions(self):
        e = Edge.make_line((0, 0, 0), (1, 1, 1))
        distances = [i / 4 for i in range(3)]
        pts = e.positions(distances)
        for i, position in enumerate(pts):
            self.assertVectorAlmostEquals(position, (i / 4, i / 4, i / 4), 5)

    def test_tangent_at(self):
        self.assertVectorAlmostEquals(
            Edge.make_circle(1, start_angle=0, end_angle=90).tangent_at(1.0),
            (-1, 0, 0),
            5,
        )
        tangent = (
            Edge.make_circle(1, start_angle=0, end_angle=90)
            .tangent_at(0.0, position_mode=PositionMode.PARAMETER)
            .to_tuple()
        )
        self.assertTrue(all([0.0 <= v <= 1.0 for v in tangent]))

        self.assertVectorAlmostEquals(
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
        self.assertVectorAlmostEquals(tan, (-math.sqrt(2) / 2, math.sqrt(2) / 2), 5)

    def test_tangent_at_by_length(self):
        circle = Edge.make_circle(1)
        tan = circle.tangent_at(circle.length * 0.5, position_mode=PositionMode.LENGTH)
        self.assertVectorAlmostEquals(tan, (0, -1), 5)

    def test_tangent_at_error(self):
        with self.assertRaises(ValueError):
            Edge.make_circle(1).tangent_at("start")

    def test_normal(self):
        self.assertVectorAlmostEquals(
            Edge.make_circle(
                1, Plane(origin=(0, 0, 0), z_dir=(1, 0, 0)), start_angle=0, end_angle=60
            ).normal(),
            (1, 0, 0),
            5,
        )
        self.assertVectorAlmostEquals(
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
        self.assertVectorAlmostEquals(
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
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0, 0), (1, 1, 1)).normal()

    def test_center(self):
        c = Edge.make_circle(1, start_angle=0, end_angle=180)
        self.assertVectorAlmostEquals(c.center(), (0, 1, 0), 5)
        self.assertVectorAlmostEquals(
            c.center(CenterOf.MASS),
            (0, 0.6366197723675814, 0),
            5,
        )
        self.assertVectorAlmostEquals(c.center(CenterOf.BOUNDING_BOX), (0, 0.5, 0), 5)

    def test_location_at(self):
        loc = Edge.make_circle(1).location_at(0.25)
        self.assertVectorAlmostEquals(loc.position, (0, 1, 0), 5)
        self.assertVectorAlmostEquals(loc.orientation, (0, -90, -90), 5)

        loc = Edge.make_circle(1).location_at(
            math.pi / 2, position_mode=PositionMode.LENGTH
        )
        self.assertVectorAlmostEquals(loc.position, (0, 1, 0), 5)
        self.assertVectorAlmostEquals(loc.orientation, (0, -90, -90), 5)

    def test_locations(self):
        locs = Edge.make_circle(1).locations([i / 4 for i in range(4)])
        self.assertVectorAlmostEquals(locs[0].position, (1, 0, 0), 5)
        self.assertVectorAlmostEquals(locs[0].orientation, (-90, 0, -180), 5)
        self.assertVectorAlmostEquals(locs[1].position, (0, 1, 0), 5)
        self.assertVectorAlmostEquals(locs[1].orientation, (0, -90, -90), 5)
        self.assertVectorAlmostEquals(locs[2].position, (-1, 0, 0), 5)
        self.assertVectorAlmostEquals(locs[2].orientation, (90, 0, 0), 5)
        self.assertVectorAlmostEquals(locs[3].position, (0, -1, 0), 5)
        self.assertVectorAlmostEquals(locs[3].orientation, (0, 90, 90), 5)

    def test_project(self):
        target = Face.make_rect(10, 10, Plane.XY.rotated((0, 45, 0)))
        circle = Edge.make_circle(1).locate(Location((0, 0, 10)))
        ellipse: Wire = circle.project(target, (0, 0, -1))
        bbox = ellipse.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-1, -1, -1), 5)
        self.assertVectorAlmostEquals(bbox.max, (1, 1, 1), 5)

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

    def test_wire_volume(self):
        wire = Wire.make_rect(1, 1)
        self.assertAlmostEqual(wire.volume, 0, 5)


class TestMixin3D(DirectApiTestCase):
    """Test that 3D add ins"""

    def test_chamfer(self):
        box = Solid.make_box(1, 1, 1)
        chamfer_box = box.chamfer(0.1, None, box.edges().sort_by(Axis.Z)[-1:])
        self.assertAlmostEqual(chamfer_box.volume, 1 - 0.005, 5)

    def test_chamfer_asym_length(self):
        box = Solid.make_box(1, 1, 1)
        chamfer_box = box.chamfer(0.1, 0.2, box.edges().sort_by(Axis.Z)[-1:])
        self.assertAlmostEqual(chamfer_box.volume, 1 - 0.01, 5)

    def test_chamfer_asym_length_with_face(self):
        box = Solid.make_box(1, 1, 1)
        face = box.faces().sort_by(Axis.Z)[0]
        edge = [face.edges().sort_by(Axis.Y)[0]]
        chamfer_box = box.chamfer(0.1, 0.2, edge, face=face)
        self.assertAlmostEqual(chamfer_box.volume, 1 - 0.01, 5)

    def test_chamfer_too_high_length(self):
        box = Solid.make_box(1, 1, 1)
        face = box.faces
        self.assertRaises(
            ValueError, box.chamfer, 2, None, box.edges().sort_by(Axis.Z)[-1:]
        )

    def test_chamfer_edge_not_part_of_face(self):
        box = Solid.make_box(1, 1, 1)
        edge = box.edges().sort_by(Axis.Z)[-1:]
        face = box.faces().sort_by(Axis.Z)[0]
        self.assertRaises(ValueError, box.chamfer, 0.1, None, edge, face=face)

    def test_hollow(self):
        shell_box = Solid.make_box(1, 1, 1).hollow([], thickness=-0.1)
        self.assertAlmostEqual(shell_box.volume, 1 - 0.8**3, 5)
        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).hollow([], thickness=0.1, kind=Kind.TANGENT)

    def test_is_inside(self):
        self.assertTrue(Solid.make_box(1, 1, 1).is_inside((0.5, 0.5, 0.5)))

    def test_dprism(self):
        # face
        f = Face.make_rect(0.5, 0.5)
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [f], additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume, 1 - 0.5**2, 5)

        # face with depth
        f = Face.make_rect(0.5, 0.5)
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [f], depth=0.5, thru_all=False, additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume, 1 - 0.5**3, 5)

        # face until
        f = Face.make_rect(0.5, 0.5)
        limit = Face.make_rect(1, 1, Plane((0, 0, 0.5)))
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [f], up_to_face=limit, thru_all=False, additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume, 1 - 0.5**3, 5)

        # wire
        w = Face.make_rect(0.5, 0.5).outer_wire()
        d = Solid.make_box(1, 1, 1, Plane((-0.5, -0.5, 0))).dprism(
            None, [w], additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume, 1 - 0.5**2, 5)

    def test_center(self):
        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).center(CenterOf.GEOMETRY)

        self.assertVectorAlmostEquals(
            Solid.make_box(1, 1, 1).center(CenterOf.BOUNDING_BOX),
            (0.5, 0.5, 0.5),
            5,
        )


class TestPlane(DirectApiTestCase):
    """Plane with class properties"""

    def test_class_properties(self):
        """Validate
        Name      x_dir  y_dir  z_dir
        =======   ====== ====== ======
        XY         +x     +y     +z
        YZ         +y     +z     +x
        ZX         +z     +x     +y
        XZ         +x     +z     -y
        YX         +y     +x     -z
        ZY         +z     +y     -x
        front      +x     +z     -y
        back       -x     +z     +y
        left       -y     +z     -x
        right      +y     +z     +x
        top        +x     +y     +z
        bottom     +x     -y     -z
        isometric  +x+y   -x+y+z +x+y-z
        """
        planes = [
            (Plane.XY, (1, 0, 0), (0, 0, 1)),
            (Plane.YZ, (0, 1, 0), (1, 0, 0)),
            (Plane.ZX, (0, 0, 1), (0, 1, 0)),
            (Plane.XZ, (1, 0, 0), (0, -1, 0)),
            (Plane.YX, (0, 1, 0), (0, 0, -1)),
            (Plane.ZY, (0, 0, 1), (-1, 0, 0)),
            (Plane.front, (1, 0, 0), (0, -1, 0)),
            (Plane.back, (-1, 0, 0), (0, 1, 0)),
            (Plane.left, (0, -1, 0), (-1, 0, 0)),
            (Plane.right, (0, 1, 0), (1, 0, 0)),
            (Plane.top, (1, 0, 0), (0, 0, 1)),
            (Plane.bottom, (1, 0, 0), (0, 0, -1)),
            (
                Plane.isometric,
                (1 / 2**0.5, 1 / 2**0.5, 0),
                (1 / 3**0.5, -1 / 3**0.5, 1 / 3**0.5),
            ),
        ]
        for plane, x_dir, z_dir in planes:
            self.assertVectorAlmostEquals(plane.x_dir, x_dir, 5)
            self.assertVectorAlmostEquals(plane.z_dir, z_dir, 5)

    def test_plane_init(self):
        # from origin
        o = (0, 0, 0)
        x = (1, 0, 0)
        y = (0, 1, 0)
        z = (0, 0, 1)
        planes = [
            Plane(o),
            Plane(o, x),
            Plane(o, x, z),
            Plane(o, x, z_dir=z),
            Plane(o, x_dir=x, z_dir=z),
            Plane(o, x_dir=x),
            Plane(o, z_dir=z),
            Plane(origin=o, x_dir=x, z_dir=z),
            Plane(origin=o, x_dir=x),
            Plane(origin=o, z_dir=z),
        ]
        for p in planes:
            self.assertVectorAlmostEquals(p.origin, o, 6)
            self.assertVectorAlmostEquals(p.x_dir, x, 6)
            self.assertVectorAlmostEquals(p.y_dir, y, 6)
            self.assertVectorAlmostEquals(p.z_dir, z, 6)
        with self.assertRaises(TypeError):
            Plane()
        with self.assertRaises(TypeError):
            Plane(o, z_dir="up")

        # rotated location around z
        loc = Location((0, 0, 0), (0, 0, 45))
        p_from_loc = Plane(loc)
        p_from_named_loc = Plane(location=loc)
        for p in [p_from_loc, p_from_named_loc]:
            self.assertVectorAlmostEquals(p.origin, (0, 0, 0), 6)
            self.assertVectorAlmostEquals(
                p.x_dir, (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6
            )
            self.assertVectorAlmostEquals(
                p.y_dir, (-math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6
            )
            self.assertVectorAlmostEquals(p.z_dir, (0, 0, 1), 6)
            self.assertVectorAlmostEquals(loc.position, p.location.position, 6)
            self.assertVectorAlmostEquals(loc.orientation, p.location.orientation, 6)

        # rotated location around x and origin <> (0,0,0)
        loc = Location((0, 2, -1), (45, 0, 0))
        p = Plane(loc)
        self.assertVectorAlmostEquals(p.origin, (0, 2, -1), 6)
        self.assertVectorAlmostEquals(p.x_dir, (1, 0, 0), 6)
        self.assertVectorAlmostEquals(
            p.y_dir, (0, math.sqrt(2) / 2, math.sqrt(2) / 2), 6
        )
        self.assertVectorAlmostEquals(
            p.z_dir, (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 6
        )
        self.assertVectorAlmostEquals(loc.position, p.location.position, 6)
        self.assertVectorAlmostEquals(loc.orientation, p.location.orientation, 6)

        # from a face
        f = Face.make_rect(1, 2).located(Location((1, 2, 3), (45, 0, 45)))
        p_from_face = Plane(f)
        p_from_named_face = Plane(face=f)
        plane_from_gp_pln = Plane(gp_pln=p_from_face.wrapped)
        p_deep_copy = copy.deepcopy(p_from_face)
        for p in [p_from_face, p_from_named_face, plane_from_gp_pln, p_deep_copy]:
            self.assertVectorAlmostEquals(p.origin, (1, 2, 3), 6)
            self.assertVectorAlmostEquals(p.x_dir, (math.sqrt(2) / 2, 0.5, 0.5), 6)
            self.assertVectorAlmostEquals(p.y_dir, (-math.sqrt(2) / 2, 0.5, 0.5), 6)
            self.assertVectorAlmostEquals(
                p.z_dir, (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 6
            )
            self.assertVectorAlmostEquals(f.location.position, p.location.position, 6)
            self.assertVectorAlmostEquals(
                f.location.orientation, p.location.orientation, 6
            )

        # from a face with x_dir
        f = Face.make_rect(1, 2)
        x = (1, 1)
        y = (-1, 1)
        planes = [
            Plane(f, x),
            Plane(f, x_dir=x),
            Plane(face=f, x_dir=x),
        ]
        for p in planes:
            self.assertVectorAlmostEquals(p.origin, (0, 0, 0), 6)
            self.assertVectorAlmostEquals(p.x_dir, Vector(x).normalized(), 6)
            self.assertVectorAlmostEquals(p.y_dir, Vector(y).normalized(), 6)
            self.assertVectorAlmostEquals(p.z_dir, (0, 0, 1), 6)

        with self.assertRaises(TypeError):
            Plane(Edge.make_line((0, 0), (0, 1)))

    def test_plane_neg(self):
        p = Plane(
            origin=(1, 2, 3),
            x_dir=Vector(1, 2, 3).normalized(),
            z_dir=Vector(4, 5, 6).normalized(),
        )
        p2 = -p
        self.assertVectorAlmostEquals(p2.origin, p.origin, 6)
        self.assertVectorAlmostEquals(p2.x_dir, p.x_dir, 6)
        self.assertVectorAlmostEquals(p2.z_dir, -p.z_dir, 6)
        self.assertVectorAlmostEquals(
            p2.y_dir, (-p.z_dir).cross(p.x_dir).normalized(), 6
        )
        p3 = p.reverse()
        self.assertVectorAlmostEquals(p3.origin, p.origin, 6)
        self.assertVectorAlmostEquals(p3.x_dir, p.x_dir, 6)
        self.assertVectorAlmostEquals(p3.z_dir, -p.z_dir, 6)
        self.assertVectorAlmostEquals(
            p3.y_dir, (-p.z_dir).cross(p.x_dir).normalized(), 6
        )

    def test_plane_mul(self):
        p = Plane(origin=(1, 2, 3), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
        p2 = p * Location((1, 2, -1), (0, 0, 45))
        self.assertVectorAlmostEquals(p2.origin, (2, 4, 2), 6)
        self.assertVectorAlmostEquals(
            p2.x_dir, (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6
        )
        self.assertVectorAlmostEquals(
            p2.y_dir, (-math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6
        )
        self.assertVectorAlmostEquals(p2.z_dir, (0, 0, 1), 6)

        p2 = p * Location((1, 2, -1), (0, 45, 0))
        self.assertVectorAlmostEquals(p2.origin, (2, 4, 2), 6)
        self.assertVectorAlmostEquals(
            p2.x_dir, (math.sqrt(2) / 2, 0, -math.sqrt(2) / 2), 6
        )
        self.assertVectorAlmostEquals(p2.y_dir, (0, 1, 0), 6)
        self.assertVectorAlmostEquals(
            p2.z_dir, (math.sqrt(2) / 2, 0, math.sqrt(2) / 2), 6
        )

        p2 = p * Location((1, 2, -1), (45, 0, 0))
        self.assertVectorAlmostEquals(p2.origin, (2, 4, 2), 6)
        self.assertVectorAlmostEquals(p2.x_dir, (1, 0, 0), 6)
        self.assertVectorAlmostEquals(
            p2.y_dir, (0, math.sqrt(2) / 2, math.sqrt(2) / 2), 6
        )
        self.assertVectorAlmostEquals(
            p2.z_dir, (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 6
        )
        with self.assertRaises(TypeError):
            p2 * Vector(1, 1, 1)

    def test_plane_methods(self):
        # Test error checking
        p = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
        with self.assertRaises(ValueError):
            p.to_local_coords("box")

        # Test translation to local coordinates
        local_box = p.to_local_coords(Solid.make_box(1, 1, 1))
        local_box_vertices = [(v.X, v.Y, v.Z) for v in local_box.vertices()]
        target_vertices = [
            (0, -1, 0),
            (0, 0, 0),
            (0, -1, 1),
            (0, 0, 1),
            (1, -1, 0),
            (1, 0, 0),
            (1, -1, 1),
            (1, 0, 1),
        ]
        for i, target_point in enumerate(target_vertices):
            self.assertTupleAlmostEquals(target_point, local_box_vertices[i], 7)

    def test_localize_vertex(self):
        vertex = Vertex(random.random(), random.random(), random.random())
        self.assertTupleAlmostEquals(
            Plane.YZ.to_local_coords(vertex).to_tuple(),
            Plane.YZ.to_local_coords(Vector(vertex)).to_tuple(),
            5,
        )

    def test_repr(self):
        self.assertEqual(
            repr(Plane.XY),
            "Plane(o=(0.00, 0.00, 0.00), x=(1.00, 0.00, 0.00), z=(0.00, 0.00, 1.00))",
        )

    def test_shift_origin_axis(self):
        cyl = Cylinder(1, 2, align=Align.MIN)
        top = cyl.faces().sort_by(Axis.Z)[-1]
        pln = Plane(top).shift_origin(Axis.Z)
        with BuildPart() as p:
            add(cyl)
            with BuildSketch(pln):
                with Locations((1, 1)):
                    Circle(0.5)
            extrude(amount=-2, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(p.part.volume, math.pi * (1**2 - 0.5**2) * 2, 5)

    def test_shift_origin_vertex(self):
        box = Box(1, 1, 1, align=Align.MIN)
        front = box.faces().sort_by(Axis.X)[-1]
        pln = Plane(front).shift_origin(
            front.vertices().group_by(Axis.Z)[-1].sort_by(Axis.Y)[-1]
        )
        with BuildPart() as p:
            add(box)
            with BuildSketch(pln):
                with Locations((-0.5, 0.5)):
                    Circle(0.5)
            extrude(amount=-1, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(p.part.volume, 1**3 - math.pi * (0.5**2) * 1, 5)

    def test_shift_origin_vector(self):
        with BuildPart() as p:
            Box(4, 4, 2)
            b = fillet(p.edges().filter_by(Axis.Z), 0.5)
            top = p.faces().sort_by(Axis.Z)[-1]
            ref = (
                top.edges()
                .filter_by(GeomType.CIRCLE)
                .group_by(Axis.X)[-1]
                .sort_by(Axis.Y)[0]
                .arc_center
            )
            pln = Plane(top, x_dir=(0, 1, 0)).shift_origin(ref)
            with BuildSketch(pln):
                with Locations((0.5, 0.5)):
                    Rectangle(2, 2, align=Align.MIN)
            extrude(amount=-1, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(p.part.volume, b.volume - 2**2 * 1, 5)

    def test_shift_origin_error(self):
        with self.assertRaises(ValueError):
            Plane.XY.shift_origin(Vertex(1, 1, 1))

        with self.assertRaises(ValueError):
            Plane.XY.shift_origin((1, 1, 1))

        with self.assertRaises(ValueError):
            Plane.XY.shift_origin(Axis((0, 0, 1), (0, 1, 0)))

        with self.assertRaises(TypeError):
            Plane.XY.shift_origin(Edge.make_line((0, 0), (1, 1)))

    def test_move(self):
        pln = Plane.XY.move(Location((1, 2, 3)))
        self.assertVectorAlmostEquals(pln.origin, (1, 2, 3), 5)

    def test_rotated(self):
        rotated_plane = Plane.XY.rotated((45, 0, 0))
        self.assertVectorAlmostEquals(rotated_plane.x_dir, (1, 0, 0), 5)
        self.assertVectorAlmostEquals(
            rotated_plane.z_dir, (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 5
        )

    def test_invalid_plane(self):
        # Test plane creation error handling
        with self.assertRaises(ValueError):
            Plane(origin=(0, 0, 0), x_dir=(0, 0, 0), z_dir=(0, 1, 1))
        with self.assertRaises(ValueError):
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 0))

    def test_plane_equal(self):
        # default orientation
        self.assertEqual(
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
        )
        # moved origin
        self.assertEqual(
            Plane(origin=(2, 1, -1), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            Plane(origin=(2, 1, -1), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
        )
        # moved x-axis
        self.assertEqual(
            Plane(origin=(0, 0, 0), x_dir=(1, 1, 0), z_dir=(0, 0, 1)),
            Plane(origin=(0, 0, 0), x_dir=(1, 1, 0), z_dir=(0, 0, 1)),
        )
        # moved z-axis
        self.assertEqual(
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 1)),
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 1)),
        )

    def test_plane_not_equal(self):
        # type difference
        for value in [None, 0, 1, "abc"]:
            self.assertNotEqual(
                Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1)), value
            )
        # origin difference
        self.assertNotEqual(
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            Plane(origin=(0, 0, 1), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
        )
        # x-axis difference
        self.assertNotEqual(
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            Plane(origin=(0, 0, 0), x_dir=(1, 1, 0), z_dir=(0, 0, 1)),
        )
        # z-axis difference
        self.assertNotEqual(
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 1)),
        )

    def test_to_location(self):
        loc = Plane(origin=(1, 2, 3), x_dir=(0, 1, 0), z_dir=(0, 0, 1)).location
        self.assertVectorAlmostEquals(loc.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(loc.orientation, (0, 0, 90), 5)

    def test_intersect(self):
        self.assertVectorAlmostEquals(
            Plane.XY.intersect(Axis((1, 2, 3), (0, 0, -1))), (1, 2, 0), 5
        )
        self.assertIsNone(Plane.XY.intersect(Axis((1, 2, 3), (0, 1, 0))))

        self.assertEqual(Plane.XY.intersect(Plane.XZ), Axis.X)

        self.assertIsNone(Plane.XY.intersect(Plane.XY.offset(1)))

        with self.assertRaises(ValueError):
            Plane.XY.intersect("Plane.XZ")

        with self.assertRaises(ValueError):
            Plane.XY.intersect(pln=Plane.XZ)

    def test_from_non_planar_face(self):
        flat = Face.make_rect(1, 1)
        pln = Plane(flat)
        self.assertTrue(isinstance(pln, Plane))
        cyl = (
            Solid.make_cylinder(1, 4).faces().filter_by(GeomType.PLANE, reverse=True)[0]
        )
        with self.assertRaises(ValueError):
            pln = Plane(cyl)

    def test_plane_intersect(self):
        section = Plane.XY.intersect(Solid.make_box(1, 2, 3, Plane.XY.offset(-1.5)))
        self.assertEqual(len(section.solids()), 0)
        self.assertEqual(len(section.faces()), 1)
        self.assertAlmostEqual(section.face().area, 2)

        section = Plane.XY & Solid.make_box(1, 2, 3, Plane.XY.offset(-1.5))
        self.assertEqual(len(section.solids()), 0)
        self.assertEqual(len(section.faces()), 1)
        self.assertAlmostEqual(section.face().area, 2)

        self.assertEqual(Plane.XY & Plane.XZ, Axis.X)
        # x_axis_as_edge = Plane.XY & Plane.XZ
        # common = (x_axis_as_edge.intersect(Edge.make_line((0, 0, 0), (1, 0, 0)))).edge()
        # self.assertAlmostEqual(common.length, 1, 5)

        i = Plane.XY & Vector(1, 2)
        self.assertTrue(isinstance(i, Vector))
        self.assertVectorAlmostEquals(i, (1, 2, 0), 5)

        a = Axis((0, 0, 0), (1, 1, 0))
        i = Plane.XY & a
        self.assertTrue(isinstance(i, Axis))
        self.assertEqual(i, a)

        a = Axis((1, 2, -1), (0, 0, 1))
        i = Plane.XY & a
        self.assertTrue(isinstance(i, Vector))
        self.assertVectorAlmostEquals(i, Vector(1, 2, 0), 5)

    def test_plane_origin_setter(self):
        pln = Plane.XY
        pln.origin = (1, 2, 3)
        ocp_origin = Vector(pln.wrapped.Location())
        self.assertVectorAlmostEquals(ocp_origin, (1, 2, 3), 5)


class TestProjection(DirectApiTestCase):
    def test_flat_projection(self):
        sphere = Solid.make_sphere(50)
        projection_direction = Vector(0, -1, 0)
        planar_text_faces = (
            Compound.make_text("Flat", 30, align=(Align.CENTER, Align.CENTER))
            .rotate(Axis.X, 90)
            .faces()
        )
        projected_text_faces = [
            f.project_to_shape(sphere, projection_direction)[0]
            for f in planar_text_faces
        ]
        self.assertEqual(len(projected_text_faces), 4)

    def test_multiple_output_wires(self):
        target = Box(10, 10, 4) - Pos((0, 0, 2)) * Box(5, 5, 2)
        circle = Wire.make_circle(3, Plane.XY.offset(10))
        projection = circle.project_to_shape(target, (0, 0, -1))
        bbox = projection[0].bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-3, -3, 1), 2)
        self.assertVectorAlmostEquals(bbox.max, (3, 3, 2), 2)
        bbox = projection[1].bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-3, -3, -2), 2)
        self.assertVectorAlmostEquals(bbox.max, (3, 3, -2), 2)

    def test_text_projection(self):
        sphere = Solid.make_sphere(50)
        arch_path = (
            sphere.cut(
                Solid.make_cylinder(
                    80, 100, Plane(origin=(-50, 0, -70), z_dir=(1, 0, 0))
                )
            )
            .edges()
            .sort_by(Axis.Z)[0]
        )

        projected_text = sphere.project_faces(
            faces=Compound.make_text("dog", font_size=14),
            path=arch_path,
        )
        self.assertEqual(len(projected_text.solids()), 0)
        self.assertEqual(len(projected_text.faces()), 3)

    def test_error_handling(self):
        sphere = Solid.make_sphere(50)
        circle = Wire.make_circle(1)
        with self.assertRaises(ValueError):
            circle.project_to_shape(sphere, center=None, direction=None)[0]

    def test_project_edge(self):
        projection = Edge.make_circle(1, Plane.XY.offset(-5)).project_to_shape(
            Solid.make_box(1, 1, 1), (0, 0, 1)
        )
        self.assertVectorAlmostEquals(projection[0].position_at(1), (1, 0, 0), 5)
        self.assertVectorAlmostEquals(projection[0].position_at(0), (0, 1, 0), 5)
        self.assertVectorAlmostEquals(projection[0].arc_center, (0, 0, 0), 5)

    def test_to_axis(self):
        with self.assertRaises(ValueError):
            Edge.make_circle(1, end_angle=30).to_axis()


class TestRotation(DirectApiTestCase):
    def test_rotation_parameters(self):
        r = Rotation(10, 20, 30)
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, 20, Z=30)
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, 20, Z=30, ordering=Intrinsic.XYZ)
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, Y=20, Z=30)
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        r = Rotation((10, 20, 30))
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        r = Rotation(10, 20, 30, Intrinsic.XYZ)
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        r = Rotation((30, 20, 10), Extrinsic.ZYX)
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        r = Rotation((30, 20, 10), ordering=Extrinsic.ZYX)
        self.assertVectorAlmostEquals(r.orientation, (10, 20, 30), 5)
        with self.assertRaises(TypeError):
            Rotation(x=10)


class TestShape(DirectApiTestCase):
    """Misc Shape tests"""

    def test_mirror(self):
        box_bb = Solid.make_box(1, 1, 1).mirror(Plane.XZ).bounding_box()
        self.assertAlmostEqual(box_bb.min.X, 0, 5)
        self.assertAlmostEqual(box_bb.max.X, 1, 5)
        self.assertAlmostEqual(box_bb.min.Y, -1, 5)
        self.assertAlmostEqual(box_bb.max.Y, 0, 5)

        box_bb = Solid.make_box(1, 1, 1).mirror().bounding_box()
        self.assertAlmostEqual(box_bb.min.Z, -1, 5)
        self.assertAlmostEqual(box_bb.max.Z, 0, 5)

    def test_compute_mass(self):
        with self.assertRaises(NotImplementedError):
            Shape.compute_mass(Vertex())

    def test_combined_center(self):
        objs = [Solid.make_box(1, 1, 1, Plane((x, 0, 0))) for x in [-2, 1]]
        self.assertVectorAlmostEquals(
            Shape.combined_center(objs, center_of=CenterOf.MASS),
            (0, 0.5, 0.5),
            5,
        )

        objs = [Solid.make_sphere(1, Plane((x, 0, 0))) for x in [-2, 1]]
        self.assertVectorAlmostEquals(
            Shape.combined_center(objs, center_of=CenterOf.BOUNDING_BOX),
            (-0.5, 0, 0),
            5,
        )
        with self.assertRaises(ValueError):
            Shape.combined_center(objs, center_of=CenterOf.GEOMETRY)

    def test_shape_type(self):
        self.assertEqual(Vertex().shape_type(), "Vertex")

    def test_scale(self):
        self.assertAlmostEqual(Solid.make_box(1, 1, 1).scale(2).volume, 2**3, 5)

    def test_fuse(self):
        box1 = Solid.make_box(1, 1, 1)
        box2 = Solid.make_box(1, 1, 1, Plane((1, 0, 0)))
        combined = box1.fuse(box2, glue=True)
        self.assertTrue(combined.is_valid())
        self.assertAlmostEqual(combined.volume, 2, 5)
        fuzzy = box1.fuse(box2, tol=1e-6)
        self.assertTrue(fuzzy.is_valid())
        self.assertAlmostEqual(fuzzy.volume, 2, 5)

    def test_faces_intersected_by_axis(self):
        box = Solid.make_box(1, 1, 1, Plane((0, 0, 1)))
        intersected_faces = box.faces_intersected_by_axis(Axis.Z)
        self.assertTrue(box.faces().sort_by(sort_by=Axis.Z)[0] in intersected_faces)
        self.assertTrue(box.faces().sort_by(sort_by=Axis.Z)[-1] in intersected_faces)

    def test_split(self):
        shape = Box(1, 1, 1) - Pos((0, 0, -0.25)) * Box(1, 0.5, 0.5)
        split_shape = shape.split(Plane.XY, keep=Keep.BOTTOM)
        self.assertEqual(len(split_shape.solids()), 2)
        self.assertAlmostEqual(split_shape.volume, 0.25, 5)
        self.assertTrue(isinstance(split_shape, Compound))
        split_shape = shape.split(Plane.XY, keep=Keep.TOP)
        self.assertEqual(len(split_shape.solids()), 1)
        self.assertTrue(isinstance(split_shape, Solid))
        self.assertAlmostEqual(split_shape.volume, 0.5, 5)

    def test_distance(self):
        sphere1 = Solid.make_sphere(1, Plane((-5, 0, 0)))
        sphere2 = Solid.make_sphere(1, Plane((5, 0, 0)))
        self.assertAlmostEqual(sphere1.distance(sphere2), 8, 5)

    def test_distances(self):
        sphere1 = Solid.make_sphere(1, Plane((-5, 0, 0)))
        sphere2 = Solid.make_sphere(1, Plane((5, 0, 0)))
        sphere3 = Solid.make_sphere(1, Plane((-5, 0, 5)))
        distances = [8, 3]
        for i, distance in enumerate(sphere1.distances(sphere2, sphere3)):
            self.assertAlmostEqual(distances[i], distance, 5)

    def test_max_fillet(self):
        test_solids = [Solid.make_box(10, 8, 2), Solid.make_cone(5, 3, 8)]
        max_values = [0.96, 3.84]
        for i, test_object in enumerate(test_solids):
            with self.subTest("solids" + str(i)):
                max = test_object.max_fillet(test_object.edges())
                self.assertAlmostEqual(max, max_values[i], 2)
        with self.assertRaises(RuntimeError):
            test_solids[0].max_fillet(
                test_solids[0].edges(), tolerance=1e-6, max_iterations=1
            )
        with self.assertRaises(ValueError):
            box = Solid.make_box(1, 1, 1)
            box.fillet(0.75, box.edges())
            # invalid_object = box.fillet(0.75, box.edges())
            # invalid_object.max_fillet(invalid_object.edges())

    def test_locate_bb(self):
        bounding_box = Solid.make_cone(1, 2, 1).bounding_box()
        relocated_bounding_box = Plane.XZ.from_local_coords(bounding_box)
        self.assertAlmostEqual(relocated_bounding_box.min.X, -2, 5)
        self.assertAlmostEqual(relocated_bounding_box.max.X, 2, 5)
        self.assertAlmostEqual(relocated_bounding_box.min.Y, 0, 5)
        self.assertAlmostEqual(relocated_bounding_box.max.Y, -1, 5)
        self.assertAlmostEqual(relocated_bounding_box.min.Z, -2, 5)
        self.assertAlmostEqual(relocated_bounding_box.max.Z, 2, 5)

    def test_is_equal(self):
        box = Solid.make_box(1, 1, 1)
        self.assertTrue(box.is_equal(box))

    def test_tessellate(self):
        box123 = Solid.make_box(1, 2, 3)
        verts, triangles = box123.tessellate(1e-6)
        self.assertEqual(len(verts), 24)
        self.assertEqual(len(triangles), 12)

    def test_transformed(self):
        """Validate that transformed works the same as changing location"""
        rotation = (uniform(0, 360), uniform(0, 360), uniform(0, 360))
        offset = (uniform(0, 50), uniform(0, 50), uniform(0, 50))
        shape = Solid.make_box(1, 1, 1).transformed(rotation, offset)
        predicted_location = Location(offset) * Rotation(*rotation)
        located_shape = Solid.make_box(1, 1, 1).locate(predicted_location)
        intersect = shape.intersect(located_shape)
        self.assertAlmostEqual(intersect.volume, 1, 5)

    def test_position_and_orientation(self):
        box = Solid.make_box(1, 1, 1).locate(Location((1, 2, 3), (10, 20, 30)))
        self.assertVectorAlmostEquals(box.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(box.orientation, (10, 20, 30), 5)

    def test_copy(self):
        with self.assertWarns(DeprecationWarning):
            Solid.make_box(1, 1, 1).copy()

    def test_distance_to_with_closest_points(self):
        s0 = Solid.make_sphere(1).locate(Location((0, 2.1, 0)))
        s1 = Solid.make_sphere(1)
        distance, pnt0, pnt1 = s0.distance_to_with_closest_points(s1)
        self.assertAlmostEqual(distance, 0.1, 5)
        self.assertVectorAlmostEquals(pnt0, (0, 1.1, 0), 5)
        self.assertVectorAlmostEquals(pnt1, (0, 1, 0), 5)

    def test_closest_points(self):
        c0 = Edge.make_circle(1).locate(Location((0, 2.1, 0)))
        c1 = Edge.make_circle(1)
        closest = c0.closest_points(c1)
        self.assertVectorAlmostEquals(closest[0], c0.position_at(0.75).to_tuple(), 5)
        self.assertVectorAlmostEquals(closest[1], c1.position_at(0.25).to_tuple(), 5)

    def test_distance_to(self):
        c0 = Edge.make_circle(1).locate(Location((0, 2.1, 0)))
        c1 = Edge.make_circle(1)
        distance = c0.distance_to(c1)
        self.assertAlmostEqual(distance, 0.1, 5)

    def test_intersection(self):
        box = Solid.make_box(1, 1, 1)
        intersections = (
            box.intersect(Axis((0.5, 0.5, 4), (0, 0, -1))).vertices().sort_by(Axis.Z)
        )
        self.assertVectorAlmostEquals(intersections[0], (0.5, 0.5, 0), 5)
        self.assertVectorAlmostEquals(intersections[1], (0.5, 0.5, 1), 5)

    def test_clean_error(self):
        """Note that this test is here to alert build123d to changes in bad OCCT clean behavior
        with spheres or hemispheres. The extra edge in a sphere seems to be the cause of this.
        """
        sphere = Solid.make_sphere(1)
        divider = Solid.make_box(0.1, 3, 3, Plane(origin=(-0.05, -1.5, -1.5)))
        positive_half, negative_half = [s.clean() for s in sphere.cut(divider).solids()]
        self.assertGreater(abs(positive_half.volume - negative_half.volume), 0, 1)

    def test_relocate(self):
        box = Solid.make_box(10, 10, 10).move(Location((20, -5, -5)))
        cylinder = Solid.make_cylinder(2, 50).move(Location((0, 0, 0), (0, 90, 0)))

        box_with_hole = box.cut(cylinder)
        box_with_hole.relocate(box.location)

        self.assertEqual(box.location, box_with_hole.location)

        bbox1 = box.bounding_box()
        bbox2 = box_with_hole.bounding_box()
        self.assertVectorAlmostEquals(bbox1.min, bbox2.min, 5)
        self.assertVectorAlmostEquals(bbox1.max, bbox2.max, 5)

    def test_project_to_viewport(self):
        # Basic test
        box = Solid.make_box(10, 10, 10)
        visible, hidden = box.project_to_viewport((-20, 20, 20))
        self.assertEqual(len(visible), 9)
        self.assertEqual(len(hidden), 3)

        # Contour edges
        cyl = Solid.make_cylinder(2, 10)
        visible, hidden = cyl.project_to_viewport((-20, 20, 20))
        # Note that some edges are broken into two
        self.assertEqual(len(visible), 6)
        self.assertEqual(len(hidden), 2)

        # Hidden contour edges
        hole = box - cyl
        visible, hidden = hole.project_to_viewport((-20, 20, 20))
        self.assertEqual(len(visible), 13)
        self.assertEqual(len(hidden), 6)

        # Outline edges
        sphere = Solid.make_sphere(5)
        visible, hidden = sphere.project_to_viewport((-20, 20, 20))
        self.assertEqual(len(visible), 1)
        self.assertEqual(len(hidden), 0)

    def test_vertex(self):
        v = Edge.make_circle(1).vertex()
        self.assertTrue(isinstance(v, Vertex))
        with self.assertWarns(UserWarning):
            Wire.make_rect(1, 1).vertex()

    def test_edge(self):
        e = Edge.make_circle(1).edge()
        self.assertTrue(isinstance(e, Edge))
        with self.assertWarns(UserWarning):
            Wire.make_rect(1, 1).edge()

    def test_wire(self):
        w = Wire.make_circle(1).wire()
        self.assertTrue(isinstance(w, Wire))
        with self.assertWarns(UserWarning):
            Solid.make_box(1, 1, 1).wire()

    def test_compound(self):
        c = Compound.make_text("hello", 10)
        self.assertTrue(isinstance(c, Compound))
        c2 = Compound.make_text("world", 10)
        with self.assertWarns(UserWarning):
            Compound(children=[c, c2]).compound()

    def test_face(self):
        f = Face.make_rect(1, 1)
        self.assertTrue(isinstance(f, Face))
        with self.assertWarns(UserWarning):
            Solid.make_box(1, 1, 1).face()

    def test_shell(self):
        s = Solid.make_sphere(1).shell()
        self.assertTrue(isinstance(s, Shell))
        with self.assertWarns(UserWarning):
            extrude(Compound.make_text("two", 10), amount=5).shell()

    def test_solid(self):
        s = Solid.make_sphere(1).solid()
        self.assertTrue(isinstance(s, Solid))
        with self.assertWarns(UserWarning):
            Solid.make_sphere(1).split(Plane.XY, keep=Keep.BOTH).solid()

    def test_manifold(self):
        self.assertTrue(Solid.make_box(1, 1, 1).is_manifold)
        self.assertTrue(Solid.make_box(1, 1, 1).shell().is_manifold)
        self.assertFalse(
            Solid.make_box(1, 1, 1)
            .shell()
            .cut(Solid.make_box(0.5, 0.5, 0.5))
            .is_manifold
        )
        self.assertTrue(
            Compound(
                children=[Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)]
            ).is_manifold
        )

    def test_inherit_color(self):
        # Create some objects and assign colors to them
        b = Box(1, 1, 1).locate(Pos(2, 2, 0))
        b.color = Color("blue")  # Blue
        c = Cylinder(1, 1).locate(Pos(-2, 2, 0))
        a = Compound(children=[b, c])
        a.color = Color(0, 1, 0)
        # Check that assigned colors stay and iheritance works
        self.assertTupleAlmostEquals(tuple(a.color), (0, 1, 0, 1), 5)
        self.assertTupleAlmostEquals(tuple(b.color), (0, 0, 1, 1), 5)

    def test_ocp_section(self):
        # Vertex
        verts, edges = Vertex(1, 2, 0)._ocp_section(Vertex(1, 2, 0))
        self.assertListEqual(verts, [])  # ?
        self.assertListEqual(edges, [])

        verts, edges = Vertex(1, 2, 0)._ocp_section(Edge.make_line((0, 0), (2, 4)))
        self.assertListEqual(verts, [])  # ?
        self.assertListEqual(edges, [])

        verts, edges = Vertex(1, 2, 0)._ocp_section(Face.make_rect(5, 5))
        self.assertTupleAlmostEquals(tuple(verts[0]), (1, 2, 0), 5)
        self.assertListEqual(edges, [])

        verts, edges = Vertex(1, 2, 0)._ocp_section(Face.make_plane(Plane.XY))
        self.assertTupleAlmostEquals(tuple(verts[0]), (1, 2, 0), 5)
        self.assertListEqual(edges, [])

        # spline = Spline((-10, 10, -10), (-10, -5, -5), (20, 0, 5))
        # cylinder = Pos(Z=-10) * extrude(Circle(5), 20)
        # cylinder2 = (Rot((0, 90, 0)) * cylinder).face()
        # pln = Plane.XY
        # box1 = Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # box2 = Pos(Z=-10) * box1

        # # vertices, edges = ocp_section(spline, Face.make_rect(1e6, 1e6, pln))
        # vertices1, edges1 = spline.ocp_section(Face.make_plane(pln))
        # print(vertices1, edges1)

        # vertices2, edges2 = cylinder.ocp_section(Face.make_plane(pln))
        # print(vertices2, edges2)

        # vertices3, edges3 = cylinder2.ocp_section(Face.make_plane(pln))
        # print(vertices3, edges3)

        # # vertices4, edges4 = cylinder2.ocp_section(cylinder)

        # vertices5, edges5 = box1.ocp_section(Face.make_plane(pln))
        # print(vertices5, edges5)

        # vertices6, edges6 = box1.ocp_section(box2.faces().sort_by(Axis.Z)[-1])


class TestShapeList(DirectApiTestCase):
    """Test ShapeList functionality"""

    def assertDunderStrEqual(self, actual: str, expected_lines: list[str]):
        actual_lines = actual.splitlines()
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            start, end = re.split(r"at 0x[0-9a-f]+", expected_line, 2, re.I)
            self.assertTrue(actual_line.startswith(start))
            self.assertTrue(actual_line.endswith(end))

    def assertDunderReprEqual(self, actual: str, expected: str):
        splitter = r"at 0x[0-9a-f]+"
        actual_split_list = re.split(splitter, actual, 0, re.I)
        expected_split_list = re.split(splitter, expected, 0, re.I)
        for actual_split, expected_split in zip(actual_split_list, expected_split_list):
            self.assertEqual(actual_split, expected_split)

    def test_sort_by(self):
        faces = Solid.make_box(1, 2, 3).faces() < SortBy.AREA
        self.assertAlmostEqual(faces[-1].area, 2, 5)

    def test_filter_by_geomtype(self):
        non_planar_faces = (
            Solid.make_cylinder(1, 1).faces().filter_by(GeomType.PLANE, reverse=True)
        )
        self.assertEqual(len(non_planar_faces), 1)
        self.assertAlmostEqual(non_planar_faces[0].area, 2 * math.pi, 5)

        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).faces().filter_by("True")

    def test_filter_by_axis(self):
        box = Solid.make_box(1, 1, 1)
        self.assertEqual(len(box.faces().filter_by(Axis.X)), 2)
        self.assertEqual(len(box.edges().filter_by(Axis.X)), 4)
        self.assertEqual(len(box.vertices().filter_by(Axis.X)), 0)

    def test_filter_by_callable_predicate(self):
        boxes = [Solid.make_box(1, 1, 1) for _ in range(3)]
        boxes[0].label = "A"
        boxes[1].label = "A"
        boxes[2].label = "B"
        shapelist = ShapeList(boxes)

        self.assertEqual(len(shapelist.filter_by(lambda s: s.label == "A")), 2)
        self.assertEqual(len(shapelist.filter_by(lambda s: s.label == "B")), 1)

    def test_first_last(self):
        vertices = (
            Solid.make_box(1, 1, 1).vertices().sort_by(Axis((0, 0, 0), (1, 1, 1)))
        )
        self.assertVectorAlmostEquals(vertices.last, (1, 1, 1), 5)
        self.assertVectorAlmostEquals(vertices.first, (0, 0, 0), 5)

    def test_group_by(self):
        vertices = Solid.make_box(1, 1, 1).vertices().group_by(Axis.Z)
        self.assertEqual(len(vertices[0]), 4)

        edges = Solid.make_box(1, 1, 1).edges().group_by(SortBy.LENGTH)
        self.assertEqual(len(edges[0]), 12)

        edges = (
            Solid.make_cone(2, 1, 2)
            .edges()
            .filter_by(GeomType.CIRCLE)
            .group_by(SortBy.RADIUS)
        )
        self.assertEqual(len(edges[0]), 1)

        edges = (Solid.make_cone(2, 1, 2).edges() | GeomType.CIRCLE) << SortBy.RADIUS
        self.assertAlmostEqual(edges[0].length, 2 * math.pi, 5)

        vertices = Solid.make_box(1, 1, 1).vertices().group_by(SortBy.DISTANCE)
        self.assertVectorAlmostEquals(vertices[-1][0], (1, 1, 1), 5)

        box = Solid.make_box(1, 1, 2)
        self.assertEqual(len(box.faces().group_by(SortBy.AREA)[0]), 2)
        self.assertEqual(len(box.faces().group_by(SortBy.AREA)[1]), 4)

        with BuildPart() as boxes:
            with GridLocations(10, 10, 3, 3):
                Box(1, 1, 1)
            with PolarLocations(100, 10):
                Box(1, 1, 2)
        self.assertEqual(len(boxes.solids().group_by(SortBy.VOLUME)[-1]), 10)
        self.assertEqual(len((boxes.solids()) << SortBy.VOLUME), 9)

        with self.assertRaises(ValueError):
            boxes.solids().group_by("AREA")

    def test_group_by_callable_predicate(self):
        boxesA = [Solid.make_box(1, 1, 1) for _ in range(3)]
        boxesB = [Solid.make_box(1, 1, 1) for _ in range(2)]
        for box in boxesA:
            box.label = "A"
        for box in boxesB:
            box.label = "B"
        boxNoLabel = Solid.make_box(1, 1, 1)

        shapelist = ShapeList(boxesA + boxesB + [boxNoLabel])
        result = shapelist.group_by(lambda shape: shape.label)

        self.assertEqual([len(group) for group in result], [1, 3, 2])

    def test_group_by_retrieve_groups(self):
        boxesA = [Solid.make_box(1, 1, 1) for _ in range(3)]
        boxesB = [Solid.make_box(1, 1, 1) for _ in range(2)]
        for box in boxesA:
            box.label = "A"
        for box in boxesB:
            box.label = "B"
        boxNoLabel = Solid.make_box(1, 1, 1)

        shapelist = ShapeList(boxesA + boxesB + [boxNoLabel])
        result = shapelist.group_by(lambda shape: shape.label)

        self.assertEqual(len(result.group("")), 1)
        self.assertEqual(len(result.group("A")), 3)
        self.assertEqual(len(result.group("B")), 2)
        self.assertEqual(result.group(""), result[0])
        self.assertEqual(result.group("A"), result[1])
        self.assertEqual(result.group("B"), result[2])
        self.assertEqual(result.group_for(boxesA[0]), result.group_for(boxesA[0]))
        self.assertNotEqual(result.group_for(boxesA[0]), result.group_for(boxesB[0]))
        with self.assertRaises(KeyError):
            result.group("C")

    def test_group_by_str_repr(self):
        nonagon = RegularPolygon(5, 9)

        expected = [
            "[[<build123d.topology.Edge at 0x1277f6e1cd0>],",
            " [<build123d.topology.Edge at 0x1277f6e1c10>,",
            "  <build123d.topology.Edge at 0x1277fd8a090>],",
            " [<build123d.topology.Edge at 0x1277f75d690>,",
            "  <build123d.topology.Edge at 0x127760d9310>],",
            " [<build123d.topology.Edge at 0x12777261f90>,",
            "  <build123d.topology.Edge at 0x1277f6bd2d0>],",
            " [<build123d.topology.Edge at 0x1276fbb0590>,",
            "  <build123d.topology.Edge at 0x1277fec6d90>]]",
        ]

        self.assertDunderStrEqual(str(nonagon.edges().group_by(Axis.X)), expected)

        expected_repr = (
            "[[<build123d.topology.Edge object at 0x000001277FEC6D90>],"
            " [<build123d.topology.Edge object at 0x000001277F6BCC10>,"
            " <build123d.topology.Edge object at 0x000001277EC3D5D0>],"
            " [<build123d.topology.Edge object at 0x000001277F6BEA90>,"
            " <build123d.topology.Edge object at 0x000001276FCB2310>],"
            " [<build123d.topology.Edge object at 0x000001277F6D10D0>,"
            " <build123d.topology.Edge object at 0x000001276FBAAD10>],"
            " [<build123d.topology.Edge object at 0x000001277FC86F90>,"
            " <build123d.topology.Edge object at 0x000001277F6E1CD0>]]"
        )
        self.assertDunderReprEqual(
            repr(nonagon.edges().group_by(Axis.X)), expected_repr
        )

        f = io.StringIO()
        p = pretty.PrettyPrinter(f)
        nonagon.edges().group_by(Axis.X)._repr_pretty_(p, cycle=True)
        self.assertEqual(f.getvalue(), "(...)")

    def test_distance(self):
        with BuildPart() as box:
            Box(1, 2, 3)
        obj = (-0.2, 0.1, 0.5)
        edges = box.edges().sort_by_distance(obj)
        distances = [Vertex(*obj).distance_to(edge) for edge in edges]
        self.assertTrue(
            all([distances[i] >= distances[i - 1] for i in range(1, len(edges))])
        )

    def test_distance_reverse(self):
        with BuildPart() as box:
            Box(1, 2, 3)
        obj = (-0.2, 0.1, 0.5)
        edges = box.edges().sort_by_distance(obj, reverse=True)
        distances = [Vertex(*obj).distance_to(edge) for edge in edges]
        self.assertTrue(
            all([distances[i] <= distances[i - 1] for i in range(1, len(edges))])
        )

    def test_distance_equal(self):
        with BuildPart() as box:
            Box(1, 1, 1)
        self.assertEqual(len(box.edges().sort_by_distance((0, 0, 0))), 12)

    def test_vertices(self):
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        self.assertEqual(len(sl.vertices()), 8)

    def test_vertex(self):
        sl = ShapeList([Edge.make_circle(1)])
        self.assertTupleAlmostEquals(sl.vertex().to_tuple(), (1, 0, 0), 5)
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        with self.assertWarns(UserWarning):
            sl.vertex()

    def test_edges(self):
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        self.assertEqual(len(sl.edges()), 8)

    def test_edge(self):
        sl = ShapeList([Edge.make_circle(1)])
        self.assertAlmostEqual(sl.edge().length, 2 * 1 * math.pi, 5)
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        with self.assertWarns(UserWarning):
            sl.edge()

    def test_wires(self):
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        self.assertEqual(len(sl.wires()), 2)

    def test_wire(self):
        sl = ShapeList([Wire.make_circle(1)])
        self.assertAlmostEqual(sl.wire().length, 2 * 1 * math.pi, 5)
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        with self.assertWarns(UserWarning):
            sl.wire()

    def test_faces(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        self.assertEqual(len(sl.faces()), 9)

    def test_face(self):
        sl = ShapeList(
            [Vertex(1, 1, 1), Edge.make_line((0, 0), (1, 1)), Face.make_rect(2, 1)]
        )
        self.assertAlmostEqual(sl.face().area, 2 * 1, 5)
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.face()

    def test_shells(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        self.assertEqual(len(sl.shells()), 2)

    def test_shell(self):
        sl = ShapeList([Vertex(1, 1, 1), Solid.make_box(1, 1, 1)])
        self.assertAlmostEqual(sl.shell().area, 6 * 1 * 1, 5)
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.shell()

    def test_solids(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        self.assertEqual(len(sl.solids()), 2)

    def test_solid(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.solid()
        sl = ShapeList([Solid.make_box(1, 2, 3), Vertex(1, 1, 1)])
        self.assertAlmostEqual(sl.solid().volume, 1 * 2 * 3, 5)

    def test_compounds(self):
        sl = ShapeList([Box(1, 1, 1), Cylinder(1, 1)])
        self.assertEqual(len(sl.compounds()), 2)

    def test_compound(self):
        sl = ShapeList([Box(1, 1, 1), Cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.compound()
        sl = ShapeList([Box(1, 2, 3), Vertex(1, 1, 1)])
        self.assertAlmostEqual(sl.compound().volume, 1 * 2 * 3, 5)


class TestShells(DirectApiTestCase):
    def test_shell_init(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        self.assertTrue(box_shell.is_valid())

    def test_center(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        self.assertVectorAlmostEquals(box_shell.center(), (0.5, 0.5, 0.5), 5)

    def test_manifold_shell_volume(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        self.assertAlmostEqual(box_shell.volume, 1, 5)

    def test_nonmanifold_shell_volume(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        nm_shell = Shell(box_faces)
        nm_shell -= nm_shell.faces()[0]
        self.assertAlmostEqual(nm_shell.volume, 0, 5)

    def test_constructor(self):
        with self.assertRaises(ValueError):
            Shell(bob="fred")

        x_section = Rot(90) * Spline((0, -5), (-3, -2), (-2, 0), (-3, 2), (0, 5))
        surface = sweep(x_section, Circle(5).wire())
        single_face = Shell(surface.face())
        self.assertTrue(single_face.is_valid())
        single_face = Shell(surface.faces())
        self.assertTrue(single_face.is_valid())

    def test_sweep(self):
        path_c1 = JernArc((0, 0), (-1, 0), 1, 180)
        path_e = path_c1.edge()
        path_c2 = JernArc((0, 0), (-1, 0), 1, 180) + JernArc((0, 0), (1, 0), 2, -90)
        path_w = path_c2.wire()
        section_e = Circle(0.5).edge()
        section_c2 = Polyline((0, 0), (0.1, 0), (0.2, 0.1))
        section_w = section_c2.wire()

        sweep_e_w = Shell.sweep((path_w ^ 0) * section_e, path_w)
        sweep_w_e = Shell.sweep((path_e ^ 0) * section_w, path_e)
        sweep_w_w = Shell.sweep((path_w ^ 0) * section_w, path_w)
        sweep_c2_c1 = Shell.sweep((path_c1 ^ 0) * section_c2, path_c1)
        sweep_c2_c2 = Shell.sweep((path_c2 ^ 0) * section_c2, path_c2)

        self.assertEqual(len(sweep_e_w.faces()), 2)
        self.assertEqual(len(sweep_w_e.faces()), 2)
        self.assertEqual(len(sweep_c2_c1.faces()), 2)
        self.assertEqual(len(sweep_w_w.faces()), 4)
        self.assertEqual(len(sweep_c2_c2.faces()), 4)


class TestSolid(DirectApiTestCase):
    def test_make_solid(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        box = Solid(box_shell)
        self.assertAlmostEqual(box.area, 6, 5)
        self.assertAlmostEqual(box.volume, 1, 5)
        self.assertTrue(box.is_valid())

    def test_extrude(self):
        v = Edge.extrude(Vertex(1, 1, 1), (0, 0, 1))
        self.assertAlmostEqual(v.length, 1, 5)

        e = Face.extrude(Edge.make_line((2, 1), (2, 0)), (0, 0, 1))
        self.assertAlmostEqual(e.area, 1, 5)

        w = Shell.extrude(
            Wire([Edge.make_line((1, 1), (0, 2)), Edge.make_line((1, 1), (1, 0))]),
            (0, 0, 1),
        )
        self.assertAlmostEqual(w.area, 1 + math.sqrt(2), 5)

        f = Solid.extrude(Face.make_rect(1, 1), (0, 0, 1))
        self.assertAlmostEqual(f.volume, 1, 5)

        s = Compound.extrude(
            Shell(
                Solid.make_box(1, 1, 1)
                .locate(Location((-2, 1, 0)))
                .faces()
                .sort_by(Axis((0, 0, 0), (1, 1, 1)))[-2:]
            ),
            (0.1, 0.1, 0.1),
        )
        self.assertAlmostEqual(s.volume, 0.2, 5)

        with self.assertRaises(ValueError):
            Solid.extrude(Solid.make_box(1, 1, 1), (0, 0, 1))

    def test_extrude_taper(self):
        a = 1
        rect = Face.make_rect(a, a)
        flipped = -rect
        for direction in [Vector(0, 0, 2), Vector(0, 0, -2)]:
            for taper in [10, -10]:
                offset_amt = -direction.length * math.tan(math.radians(taper))
                for face in [rect, flipped]:
                    with self.subTest(
                        f"{direction=}, {taper=}, flipped={face==flipped}"
                    ):
                        taper_solid = Solid.extrude_taper(face, direction, taper)
                        # V = 1/3 × h × (a² + b² + ab)
                        h = Vector(direction).length
                        b = a + 2 * offset_amt
                        v = h * (a**2 + b**2 + a * b) / 3
                        self.assertAlmostEqual(taper_solid.volume, v, 5)
                        bbox = taper_solid.bounding_box()
                        size = max(1, b) / 2
                        if direction.Z > 0:
                            self.assertVectorAlmostEquals(
                                bbox.min, (-size, -size, 0), 1
                            )
                            self.assertVectorAlmostEquals(bbox.max, (size, size, h), 1)
                        else:
                            self.assertVectorAlmostEquals(
                                bbox.min, (-size, -size, -h), 1
                            )
                            self.assertVectorAlmostEquals(bbox.max, (size, size, 0), 1)

    def test_extrude_taper_with_hole(self):
        rect_hole = Face.make_rect(1, 1).make_holes([Wire.make_circle(0.25)])
        direction = Vector(0, 0, 0.5)
        taper = 10
        taper_solid = Solid.extrude_taper(rect_hole, direction, taper)
        offset_amt = -direction.length * math.tan(math.radians(taper))
        hole = taper_solid.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
        self.assertAlmostEqual(hole.radius, 0.25 - offset_amt, 5)

    def test_extrude_taper_with_hole_flipped(self):
        rect_hole = Face.make_rect(1, 1).make_holes([Wire.make_circle(0.25)])
        direction = Vector(0, 0, 1)
        taper = 10
        taper_solid_t = Solid.extrude_taper(rect_hole, direction, taper, True)
        taper_solid_f = Solid.extrude_taper(rect_hole, direction, taper, False)
        hole_t = taper_solid_t.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
        hole_f = taper_solid_f.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
        self.assertGreater(hole_t.radius, hole_f.radius)

    def test_extrude_taper_oblique(self):
        rect = Face.make_rect(2, 1)
        rect_hole = rect.make_holes([Wire.make_circle(0.25)])
        o_rect_hole = rect_hole.moved(Location((0, 0, 0), (1, 0.1, 0), 77))
        taper0 = Solid.extrude_taper(rect_hole, (0, 0, 1), 5)
        taper1 = Solid.extrude_taper(o_rect_hole, o_rect_hole.normal_at(), 5)
        self.assertAlmostEqual(taper0.volume, taper1.volume, 5)

    def test_extrude_linear_with_rotation(self):
        # Face
        base = Face.make_rect(1, 1)
        twist = Solid.extrude_linear_with_rotation(
            base, center=(0, 0, 0), normal=(0, 0, 1), angle=45
        )
        self.assertAlmostEqual(twist.volume, 1, 5)
        top = twist.faces().sort_by(Axis.Z)[-1].rotate(Axis.Z, 45)
        bottom = twist.faces().sort_by(Axis.Z)[0]
        self.assertAlmostEqual(top.translate((0, 0, -1)).intersect(bottom).area, 1, 5)
        # Wire
        base = Wire.make_rect(1, 1)
        twist = Solid.extrude_linear_with_rotation(
            base, center=(0, 0, 0), normal=(0, 0, 1), angle=45
        )
        self.assertAlmostEqual(twist.volume, 1, 5)
        top = twist.faces().sort_by(Axis.Z)[-1].rotate(Axis.Z, 45)
        bottom = twist.faces().sort_by(Axis.Z)[0]
        self.assertAlmostEqual(top.translate((0, 0, -1)).intersect(bottom).area, 1, 5)

    def test_make_loft(self):
        loft = Solid.make_loft(
            [Wire.make_rect(2, 2), Wire.make_circle(1, Plane((0, 0, 1)))]
        )
        self.assertAlmostEqual(loft.volume, (4 + math.pi) / 2, 1)

        with self.assertRaises(ValueError):
            Solid.make_loft([Wire.make_rect(1, 1)])

    def test_extrude_until(self):
        square = Face.make_rect(1, 1)
        box = Solid.make_box(4, 4, 1, Plane((-2, -2, 3)))
        extrusion = Solid.extrude_until(square, box, (0, 0, 1), Until.LAST)
        self.assertAlmostEqual(extrusion.volume, 4, 5)

    def test_sweep(self):
        path = Edge.make_spline([(0, 0), (3, 5), (7, -2)])
        section = Wire.make_circle(1, Plane(path @ 0, z_dir=path % 0))
        area = Face(section).area
        swept = Solid.sweep(section, path)
        self.assertAlmostEqual(swept.volume, path.length * area, 0)

    def test_hollow_sweep(self):
        path = Edge.make_line((0, 0, 0), (0, 0, 5))
        section = (Rectangle(1, 1) - Rectangle(0.1, 0.1)).faces()[0]
        swept = Solid.sweep(section, path)
        self.assertAlmostEqual(swept.volume, 5 * (1 - 0.1**2), 5)

    def test_constructor(self):
        with self.assertRaises(ValueError):
            Solid(bob="fred")


class TestVector(DirectApiTestCase):
    """Test the Vector methods"""

    def test_vector_constructors(self):
        v1 = Vector(1, 2, 3)
        v2 = Vector((1, 2, 3))
        v3 = Vector(gp_Vec(1, 2, 3))
        v4 = Vector([1, 2, 3])
        v5 = Vector(gp_XYZ(1, 2, 3))
        v5b = Vector(X=1, Y=2, Z=3)
        v5c = Vector(v=gp_XYZ(1, 2, 3))

        for v in [v1, v2, v3, v4, v5, v5b, v5c]:
            self.assertVectorAlmostEquals(v, (1, 2, 3), 4)

        v6 = Vector((1, 2))
        v7 = Vector([1, 2])
        v8 = Vector(1, 2)
        v8b = Vector(X=1, Y=2)

        for v in [v6, v7, v8, v8b]:
            self.assertVectorAlmostEquals(v, (1, 2, 0), 4)

        v9 = Vector()
        self.assertVectorAlmostEquals(v9, (0, 0, 0), 4)

        v9.X = 1.0
        v9.Y = 2.0
        v9.Z = 3.0
        self.assertVectorAlmostEquals(v9, (1, 2, 3), 4)
        self.assertVectorAlmostEquals(Vector(1, 2, 3, 4), (1, 2, 3), 4)

        v10 = Vector(1)
        v11 = Vector((1,))
        v12 = Vector([1])
        v13 = Vector(X=1)
        for v in [v10, v11, v12, v13]:
            self.assertVectorAlmostEquals(v, (1, 0, 0), 4)

        vertex = Vertex(0, 0, 0).moved(Pos(0, 0, 10))
        self.assertVectorAlmostEquals(Vector(vertex), (0, 0, 10), 4)

        with self.assertRaises(TypeError):
            Vector("vector")
        with self.assertRaises(ValueError):
            Vector(x=1)

    def test_vector_rotate(self):
        """Validate vector rotate methods"""
        vector_x = Vector(1, 0, 1).rotate(Axis.X, 45)
        vector_y = Vector(1, 2, 1).rotate(Axis.Y, 45)
        vector_z = Vector(-1, -1, 3).rotate(Axis.Z, 45)
        self.assertVectorAlmostEquals(
            vector_x, (1, -math.sqrt(2) / 2, math.sqrt(2) / 2), 7
        )
        self.assertVectorAlmostEquals(vector_y, (math.sqrt(2), 2, 0), 7)
        self.assertVectorAlmostEquals(vector_z, (0, -math.sqrt(2), 3), 7)

    def test_get_signed_angle(self):
        """Verify getSignedAngle calculations with and without a provided normal"""
        a = math.pi / 3
        v1 = Vector(1, 0, 0)
        v2 = Vector(math.cos(a), -math.sin(a), 0)
        d1 = v1.get_signed_angle(v2)
        d2 = v1.get_signed_angle(v2, Vector(0, 0, 1))
        self.assertAlmostEqual(d1, a * 180 / math.pi)
        self.assertAlmostEqual(d2, -a * 180 / math.pi)

    def test_center(self):
        v = Vector(1, 1, 1)
        self.assertAlmostEqual(v, v.center())

    def test_dot(self):
        v1 = Vector(2, 2, 2)
        v2 = Vector(1, -1, 1)
        self.assertEqual(2.0, v1.dot(v2))

    def test_vector_add(self):
        result = Vector(1, 2, 0) + Vector(0, 0, 3)
        self.assertVectorAlmostEquals(result, (1.0, 2.0, 3.0), 3)

    def test_vector_operators(self):
        result = Vector(1, 1, 1) + Vector(2, 2, 2)
        self.assertEqual(Vector(3, 3, 3), result)

        result = Vector(1, 2, 3) - Vector(3, 2, 1)
        self.assertEqual(Vector(-2, 0, 2), result)

        result = Vector(1, 2, 3) * 2
        self.assertEqual(Vector(2, 4, 6), result)

        result = 3 * Vector(1, 2, 3)
        self.assertEqual(Vector(3, 6, 9), result)

        result = Vector(2, 4, 6) / 2
        self.assertEqual(Vector(1, 2, 3), result)

        self.assertEqual(Vector(-1, -1, -1), -Vector(1, 1, 1))

        self.assertEqual(0, abs(Vector(0, 0, 0)))
        self.assertEqual(1, abs(Vector(1, 0, 0)))
        self.assertEqual((1 + 4 + 9) ** 0.5, abs(Vector(1, 2, 3)))

    def test_vector_equals(self):
        a = Vector(1, 2, 3)
        b = Vector(1, 2, 3)
        c = Vector(1, 2, 3.000001)
        self.assertEqual(a, b)
        self.assertEqual(a, c)

    def test_vector_distance(self):
        """
        Test line distance from plane.
        """
        v = Vector(1, 2, 3)

        self.assertAlmostEqual(1, v.signed_distance_from_plane(Plane.YZ))
        self.assertAlmostEqual(2, v.signed_distance_from_plane(Plane.ZX))
        self.assertAlmostEqual(3, v.signed_distance_from_plane(Plane.XY))
        self.assertAlmostEqual(-1, v.signed_distance_from_plane(Plane.ZY))
        self.assertAlmostEqual(-2, v.signed_distance_from_plane(Plane.XZ))
        self.assertAlmostEqual(-3, v.signed_distance_from_plane(Plane.YX))

        self.assertAlmostEqual(1, v.distance_to_plane(Plane.YZ))
        self.assertAlmostEqual(2, v.distance_to_plane(Plane.ZX))
        self.assertAlmostEqual(3, v.distance_to_plane(Plane.XY))
        self.assertAlmostEqual(1, v.distance_to_plane(Plane.ZY))
        self.assertAlmostEqual(2, v.distance_to_plane(Plane.XZ))
        self.assertAlmostEqual(3, v.distance_to_plane(Plane.YX))

    def test_vector_project(self):
        """
        Test line projection and plane projection methods of Vector
        """
        decimal_places = 9

        z_dir = Vector(1, 2, 3)
        base = Vector(5, 7, 9)
        x_dir = Vector(1, 0, 0)

        # test passing Plane object
        point = Vector(10, 11, 12).project_to_plane(Plane(base, x_dir, z_dir))
        self.assertVectorAlmostEquals(point, (59 / 7, 55 / 7, 51 / 7), decimal_places)

        # test line projection
        vec = Vector(10, 10, 10)
        line = Vector(3, 4, 5)
        angle = vec.get_angle(line) * DEG2RAD

        vecLineProjection = vec.project_to_line(line)

        self.assertVectorAlmostEquals(
            vecLineProjection.normalized(),
            line.normalized(),
            decimal_places,
        )
        self.assertAlmostEqual(
            vec.length * math.cos(angle), vecLineProjection.length, decimal_places
        )

    def test_vector_not_implemented(self):
        pass

    def test_vector_special_methods(self):
        self.assertEqual(repr(Vector(1, 2, 3)), "Vector(1, 2, 3)")
        self.assertEqual(str(Vector(1, 2, 3)), "Vector(1, 2, 3)")
        self.assertEqual(
            str(Vector(9.99999999999999, -23.649999999999995, -7.37188088351e-15)),
            "Vector(10, -23.65, 0)",
        )

    def test_vector_iter(self):
        self.assertEqual(sum([v for v in Vector(1, 2, 3)]), 6)

    def test_reverse(self):
        self.assertVectorAlmostEquals(Vector(1, 2, 3).reverse(), (-1, -2, -3), 7)

    def test_copy(self):
        v2 = copy.copy(Vector(1, 2, 3))
        v3 = copy.deepcopy(Vector(1, 2, 3))
        self.assertVectorAlmostEquals(v2, (1, 2, 3), 7)
        self.assertVectorAlmostEquals(v3, (1, 2, 3), 7)

    def test_radd(self):
        vectors = [Vector(1, 2, 3), Vector(4, 5, 6), Vector(7, 8, 9)]
        vector_sum = sum(vectors)
        self.assertVectorAlmostEquals(vector_sum, (12, 15, 18), 5)

    def test_hash(self):
        vectors = [Vector(1, 2, 3), Vector(4, 5, 6), Vector(7, 8, 9), Vector(1, 2, 3)]
        unique_vectors = list(set(vectors))
        self.assertEqual(len(vectors), 4)
        self.assertEqual(len(unique_vectors), 3)

    def test_vector_transform(self):
        a = Vector(1, 2, 3)
        pxy = Plane.XY
        pxy_o1 = Plane.XY.offset(1)
        self.assertEqual(a.transform(pxy.forward_transform, is_direction=False), a)
        self.assertEqual(
            a.transform(pxy.forward_transform, is_direction=True), a.normalized()
        )
        self.assertEqual(
            a.transform(pxy_o1.forward_transform, is_direction=False), Vector(1, 2, 2)
        )
        self.assertEqual(
            a.transform(pxy_o1.forward_transform, is_direction=True), a.normalized()
        )
        self.assertEqual(
            a.transform(pxy_o1.reverse_transform, is_direction=False), Vector(1, 2, 4)
        )
        self.assertEqual(
            a.transform(pxy_o1.reverse_transform, is_direction=True), a.normalized()
        )

    def test_intersect(self):
        v1 = Vector(1, 2, 3)
        self.assertVectorAlmostEquals(v1 & Vector(1, 2, 3), (1, 2, 3), 5)
        self.assertIsNone(v1 & Vector(0, 0, 0))

        self.assertVectorAlmostEquals(v1 & Location((1, 2, 3)), (1, 2, 3), 5)
        self.assertIsNone(v1 & Location())

        self.assertVectorAlmostEquals(v1 & Axis((1, 2, 3), (1, 0, 0)), (1, 2, 3), 5)
        self.assertIsNone(v1 & Axis.X)

        self.assertVectorAlmostEquals(v1 & Plane((1, 2, 3)), (1, 2, 3), 5)
        self.assertIsNone(v1 & Plane.XY)

        self.assertVectorAlmostEquals(
            (v1 & Solid.make_box(2, 4, 5)).vertex(), (1, 2, 3), 5
        )
        self.assertTrue(
            len(v1.intersect(Solid.make_box(0.5, 0.5, 0.5)).vertices()) == 0
        )


class TestVectorLike(DirectApiTestCase):
    """Test typedef"""

    def test_axis_from_vertex(self):
        axis = Axis(Vertex(1, 2, 3), Vertex(0, 0, 1))
        self.assertVectorAlmostEquals(axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(axis.direction, (0, 0, 1), 5)

    def test_axis_from_vector(self):
        axis = Axis(Vector(1, 2, 3), Vector(0, 0, 1))
        self.assertVectorAlmostEquals(axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(axis.direction, (0, 0, 1), 5)

    def test_axis_from_tuple(self):
        axis = Axis((1, 2, 3), (0, 0, 1))
        self.assertVectorAlmostEquals(axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(axis.direction, (0, 0, 1), 5)


class TestVertex(DirectApiTestCase):
    """Test the extensions to the cadquery Vertex class"""

    def test_basic_vertex(self):
        v = Vertex()
        self.assertEqual(0, v.X)

        v = Vertex(1, 1, 1)
        self.assertEqual(1, v.X)
        self.assertEqual(Vector, type(v.center()))

        self.assertVectorAlmostEquals(Vector(Vertex(Vector(1, 2, 3))), (1, 2, 3), 7)
        self.assertVectorAlmostEquals(Vector(Vertex((4, 5, 6))), (4, 5, 6), 7)
        self.assertVectorAlmostEquals(Vector(Vertex((7,))), (7, 0, 0), 7)
        self.assertVectorAlmostEquals(Vector(Vertex((8, 9))), (8, 9, 0), 7)

    def test_vertex_volume(self):
        v = Vertex(1, 1, 1)
        self.assertAlmostEqual(v.volume, 0, 5)

    def test_vertex_add(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertVectorAlmostEquals(
            Vector(test_vertex + (100, -40, 10)), (100, -40, 10), 7
        )
        self.assertVectorAlmostEquals(
            Vector(test_vertex + Vector(100, -40, 10)), (100, -40, 10), 7
        )
        self.assertVectorAlmostEquals(
            Vector(test_vertex + Vertex(100, -40, 10)),
            (100, -40, 10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex + [1, 2, 3]

    def test_vertex_sub(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertVectorAlmostEquals(
            Vector(test_vertex - (100, -40, 10)), (-100, 40, -10), 7
        )
        self.assertVectorAlmostEquals(
            Vector(test_vertex - Vector(100, -40, 10)), (-100, 40, -10), 7
        )
        self.assertVectorAlmostEquals(
            Vector(test_vertex - Vertex(100, -40, 10)),
            (-100, 40, -10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex - [1, 2, 3]

    def test_vertex_str(self):
        self.assertEqual(str(Vertex(0, 0, 0)), "Vertex: (0.0, 0.0, 0.0)")

    def test_vertex_to_vector(self):
        self.assertIsInstance(Vector(Vertex(0, 0, 0)), Vector)
        self.assertVectorAlmostEquals(Vector(Vertex(0, 0, 0)), (0.0, 0.0, 0.0), 7)

    def test_vertex_init_error(self):
        with self.assertRaises(TypeError):
            Vertex(Axis.Z)
        with self.assertRaises(ValueError):
            Vertex(x=1)
        with self.assertRaises(TypeError):
            Vertex((Axis.X, Axis.Y, Axis.Z))

    def test_no_intersect(self):
        with self.assertRaises(NotImplementedError):
            Vertex(1, 2, 3) & Vertex(5, 6, 7)


class TestWire(DirectApiTestCase):
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
        self.assertVectorAlmostEquals(spline @ 0.5, half @ 0, 4)
        self.assertVectorAlmostEquals(spline @ 1, half @ 1, 4)

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
        self.assertFalse(all(e.is_forward for e in w1.edges()))
        self.assertTrue(all(e.is_forward for e in ordered_edges))
        self.assertVectorAlmostEquals(ordered_edges[0] @ 0, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(ordered_edges[1] @ 0, (1, 0, 0), 5)
        self.assertVectorAlmostEquals(ordered_edges[2] @ 0, (1, 1, 0), 5)

    def test_constructor(self):
        e0 = Edge.make_line((0, 0), (1, 0))
        e1 = Edge.make_line((1, 0), (1, 1))
        w0 = Wire.make_circle(1)
        w1 = Wire(e0)
        self.assertTrue(w1.is_valid())
        w2 = Wire([e0])
        self.assertAlmostEqual(w2.length, 1, 5)
        self.assertTrue(w2.is_valid())
        w3 = Wire([e0, e1])
        self.assertTrue(w3.is_valid())
        self.assertAlmostEqual(w3.length, 2, 5)
        w4 = Wire(w0.wrapped)
        self.assertTrue(w4.is_valid())
        w5 = Wire(obj=w0.wrapped)
        self.assertTrue(w5.is_valid())
        w6 = Wire(obj=w0.wrapped, label="w6", color=Color("red"))
        self.assertTrue(w6.is_valid())
        self.assertEqual(w6.label, "w6")
        self.assertTupleAlmostEquals(tuple(w6.color), (1.0, 0.0, 0.0, 1.0), 5)
        w7 = Wire(w6)
        self.assertTrue(w7.is_valid())
        c0 = Polyline((0, 0), (1, 0), (1, 1))
        w8 = Wire(c0)
        self.assertTrue(w8.is_valid())
        with self.assertRaises(ValueError):
            Wire(bob="fred")


if __name__ == "__main__":
    unittest.main()
