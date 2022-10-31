# system modules
import math
import unittest
from random import uniform
from OCP.gp import (
    gp_Vec,
    gp_Pnt,
    gp_Ax2,
    gp_Circ,
    gp_Elips,
    gp,
    gp_XYZ,
    gp_Trsf,
    gp_Ax1,
    gp_Dir,
)
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge

from build123d import *
from build123d import Shape, Matrix, BoundBox

# Direct API Functions
from build123d.direct_api import (
    downcast,
    edges_to_wires,
    fix,
    shapetype,
    sort_wires_by_build_order,
)

DEG2RAD = math.pi / 180
RAD2DEG = 180 / math.pi


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class TestCadObjects(unittest.TestCase):
    def _make_circle(self):

        circle = gp_Circ(gp_Ax2(gp_Pnt(1, 2, 3), gp.DZ_s()), 2.0)
        return Shape.cast(BRepBuilderAPI_MakeEdge(circle).Edge())

    def _make_ellipse(self):

        ellipse = gp_Elips(gp_Ax2(gp_Pnt(1, 2, 3), gp.DZ_s()), 4.0, 2.0)
        return Shape.cast(BRepBuilderAPI_MakeEdge(ellipse).Edge())

    def test_basic_bounding_box(self):
        v = Vertex(1, 1, 1)
        v2 = Vertex(2, 2, 2)
        self.assertEqual(BoundBox, type(v.bounding_box()))
        self.assertEqual(BoundBox, type(v2.bounding_box()))

        bb1 = v.bounding_box().add(v2.bounding_box())

        # OCC uses some approximations
        self.assertAlmostEqual(bb1.xlen, 1.0, 1)

        # Test adding to an existing bounding box
        v0 = Vertex(0, 0, 0)
        bb2 = v0.bounding_box().add(v.bounding_box())

        bb3 = bb1.add(bb2)
        self.assertTupleAlmostEquals((2, 2, 2), (bb3.xlen, bb3.ylen, bb3.zlen), 7)

        bb3 = bb2.add((3, 3, 3))
        self.assertTupleAlmostEquals((3, 3, 3), (bb3.xlen, bb3.ylen, bb3.zlen), 7)

        bb3 = bb2.add(Vector(3, 3, 3))
        self.assertTupleAlmostEquals((3, 3, 3), (bb3.xlen, bb3.ylen, bb3.zlen), 7)

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
        self.assertTupleAlmostEquals((2, 2, 1), (bb1.xlen, bb1.ylen, bb1.zlen), 1)

        bb2 = BoundBox._from_topo_ds(
            Solid.make_cylinder(0.5, 0.5).translate((0, 0, 0.1)).wrapped, optimal=False
        )
        self.assertTrue(bb2.is_inside(bb1))

    def test_edge_wrapper_center(self):
        e = self._make_circle()

        self.assertTupleAlmostEquals(
            (1.0, 2.0, 3.0), e.center(center_of=CenterOf.MASS).to_tuple(), 3
        )

    def test_edge_wrapper_ellipse_center(self):
        e = self._make_ellipse()
        w = Wire.make_wire([e])
        self.assertTupleAlmostEquals(
            (1.0, 2.0, 3.0), Face.make_from_wires(w).center().to_tuple(), 3
        )

    def test_edge_wrapper_make_circle(self):
        halfCircleEdge = Edge.make_circle(
            radius=10, pnt=(0, 0, 0), dir=(0, 0, 1), angle1=0, angle2=180
        )

        # self.assertTupleAlmostEquals((0.0, 5.0, 0.0), halfCircleEdge.centerOfBoundBox(0.0001).to_tuple(),3)
        self.assertTupleAlmostEquals(
            (10.0, 0.0, 0.0), halfCircleEdge.start_point().to_tuple(), 3
        )
        self.assertTupleAlmostEquals(
            (-10.0, 0.0, 0.0), halfCircleEdge.end_point().to_tuple(), 3
        )

    def test_edge_wrapper_make_tangent_arc(self):
        tangent_arc = Edge.make_tangent_arc(
            Vector(1, 1),  # starts at 1, 1
            Vector(0, 1),  # tangent at start of arc is in the +y direction
            Vector(2, 1),  # arc cureturn_valuees 180 degrees and ends at 2, 1
        )
        self.assertTupleAlmostEquals((1, 1, 0), tangent_arc.start_point().to_tuple(), 3)
        self.assertTupleAlmostEquals((2, 1, 0), tangent_arc.end_point().to_tuple(), 3)
        self.assertTupleAlmostEquals(
            (0, 1, 0), tangent_arc.tangent_at(location_param=0).to_tuple(), 3
        )
        self.assertTupleAlmostEquals(
            (1, 0, 0), tangent_arc.tangent_at(location_param=0.5).to_tuple(), 3
        )
        self.assertTupleAlmostEquals(
            (0, -1, 0), tangent_arc.tangent_at(location_param=1).to_tuple(), 3
        )

    def test_edge_wrapper_make_ellipse1(self):
        # Check x_radius > y_radius
        x_radius, y_radius = 20, 10
        angle1, angle2 = -75.0, 90.0
        arcEllipseEdge = Edge.make_ellipse(
            x_radius=x_radius,
            y_radius=y_radius,
            pnt=(0, 0, 0),
            dir=(0, 0, 1),
            angle1=angle1,
            angle2=angle2,
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
        self.assertTupleAlmostEquals(start, arcEllipseEdge.start_point().to_tuple(), 3)
        self.assertTupleAlmostEquals(end, arcEllipseEdge.end_point().to_tuple(), 3)

    def test_edge_wrapper_make_ellipse2(self):
        # Check x_radius < y_radius
        x_radius, y_radius = 10, 20
        angle1, angle2 = 0.0, 45.0
        arcEllipseEdge = Edge.make_ellipse(
            x_radius=x_radius,
            y_radius=y_radius,
            pnt=(0, 0, 0),
            dir=(0, 0, 1),
            angle1=angle1,
            angle2=angle2,
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
        self.assertTupleAlmostEquals(start, arcEllipseEdge.start_point().to_tuple(), 3)
        self.assertTupleAlmostEquals(end, arcEllipseEdge.end_point().to_tuple(), 3)

    def test_edge_wrapper_make_circle_with_ellipse(self):
        # Check x_radius == y_radius
        x_radius, y_radius = 20, 20
        angle1, angle2 = 15.0, 60.0
        arcEllipseEdge = Edge.make_ellipse(
            x_radius=x_radius,
            y_radius=y_radius,
            pnt=(0, 0, 0),
            dir=(0, 0, 1),
            angle1=angle1,
            angle2=angle2,
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
        self.assertTupleAlmostEquals(start, arcEllipseEdge.start_point().to_tuple(), 3)
        self.assertTupleAlmostEquals(end, arcEllipseEdge.end_point().to_tuple(), 3)

    def test_face_wrapper_make_rect(self):
        mplane = Face.make_rect(10, 10)

        self.assertTupleAlmostEquals((0.0, 0.0, 1.0), mplane.normal_at().to_tuple(), 3)

    def test_center_of_boundbox(self):
        pass

    def test_combined_center_of_boundbox(self):
        pass

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
    #     self.assertTupleAlmostEquals((0.0, 0.0, 0.25), s.val().center().to_tuple(), 3)

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
        mx.rotate_x(30 * DEG2RAD)
        matrix_almost_equal(mx, m_rotate_x_30)

        m_rotate_y_30 = [
            [root_3_over_2, 0, 1 / 2, 0],
            [0, 1, 0, 0],
            [-1 / 2, 0, root_3_over_2, 0],
            [0, 0, 0, 1],
        ]
        my = Matrix()
        my.rotate_y(30 * DEG2RAD)
        matrix_almost_equal(my, m_rotate_y_30)

        m_rotate_z_30 = [
            [root_3_over_2, -1 / 2, 0, 0],
            [1 / 2, root_3_over_2, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        mz = Matrix()
        mz.rotate_z(30 * DEG2RAD)
        matrix_almost_equal(mz, m_rotate_z_30)

        # Test matrix multipy vector
        v = Vector(1, 0, 0)
        self.assertTupleAlmostEquals(
            mz.multiply(v).to_tuple(), (root_3_over_2, 1 / 2, 0), 7
        )

        # Test matrix multipy matrix
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

    def test_translate(self):
        e = Edge.make_circle(2, (1, 2, 3))
        e2 = e.translate(Vector(0, 0, 1))

        self.assertTupleAlmostEquals(
            (1.0, 2.0, 4.0), e2.center(center_of=CenterOf.MASS).to_tuple(), 3
        )

    def test_vertices(self):
        e = Shape.cast(BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(1, 1, 0)).Edge())
        self.assertEqual(2, len(e.vertices()))

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

    def test_invalid_plane(self):
        # Test plane creation error handling
        with self.assertRaises(ValueError):
            Plane(origin=(0, 0, 0), x_dir=(0, 0, 0), z_dir=(0, 1, 1))
        with self.assertRaises(ValueError):
            Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 0))

    def test_plane_methods(self):
        # Test error checking
        p = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
        with self.assertRaises(ValueError):
            p.to_local_coords("box")

        # Test translation to local coordinates
        # local_box = Workplane(p.to_local_coords(Solid.make_box(1, 1, 1)))
        local_box = p.to_local_coords(Solid.make_box(1, 1, 1))
        # local_box_vertices = [(v.X, v.Y, v.Z) for v in local_box.vertices().vals()]
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
            Location([0, 0, 1])
        with self.assertRaises(TypeError):
            Location("xy_plane")

    def test_location_repr_and_str(self):
        self.assertEqual(
            repr(Location()), "(p=(0.00, 0.00, 0.00), o=(0.00, -0.00, 0.00))"
        )
        self.assertEqual(
            str(Location()),
            "Location: (position=(0.00, 0.00, 0.00), orientation=(0.00, -0.00, 0.00))",
        )

    def test_location_inverted(self):
        loc = Location(Plane.XZ)
        self.assertTupleAlmostEquals(
            loc.inverse().orientation.to_tuple(), (-math.pi / 2, 0, 0), 6
        )

    def test_edge_wrapper_radius(self):

        # get a radius from a simple circle
        e0 = Edge.make_circle(2.4)
        self.assertAlmostEqual(e0.radius(), 2.4)

        # radius of an arc
        e1 = Edge.make_circle(1.8, pnt=(5, 6, 7), dir=(1, 1, 1), angle1=20, angle2=30)
        self.assertAlmostEqual(e1.radius(), 1.8)

        # test value errors
        e2 = Edge.make_ellipse(10, 20)
        with self.assertRaises(ValueError):
            e2.radius()

        # radius from a wire
        w0 = Wire.make_circle(10, Vector(1, 2, 3), (-1, 0, 1))
        self.assertAlmostEqual(w0.radius(), 10)

        # radius from a wire with multiple edges
        rad = 2.3
        pnt = (7, 8, 9)
        direction = (1, 0.5, 0.1)
        w1 = Wire.make_wire(
            [
                Edge.make_circle(rad, pnt, direction, 0, 10),
                Edge.make_circle(rad, pnt, direction, 10, 25),
                Edge.make_circle(rad, pnt, direction, 25, 230),
            ]
        )
        self.assertAlmostEqual(w1.radius(), rad)

        # test value error from wire
        w2 = Wire.make_polygon(
            [
                Vector(-1, 0, 0),
                Vector(0, 1, 0),
                Vector(1, -1, 0),
            ]
        )
        with self.assertRaises(ValueError):
            w2.radius()

        # (I think) the radius of a wire is the radius of it's first edge.
        # Since this is stated in the docstring better make sure.
        no_rad = Wire.make_wire(
            [
                Edge.make_line(Vector(0, 0, 0), Vector(0, 1, 0)),
                Edge.make_circle(1.0, angle1=90, angle2=270),
            ]
        )
        with self.assertRaises(ValueError):
            no_rad.radius()
        yes_rad = Wire.make_wire(
            [
                Edge.make_circle(1.0, angle1=90, angle2=270),
                Edge.make_line(Vector(0, -1, 0), Vector(0, 1, 0)),
            ]
        )
        self.assertAlmostEqual(yes_rad.radius(), 1.0)
        many_rad = Wire.make_wire(
            [
                Edge.make_circle(1.0, angle1=0, angle2=180),
                Edge.make_circle(3.0, pnt=Vector(2, 0, 0), angle1=180, angle2=359),
            ]
        )
        self.assertAlmostEqual(many_rad.radius(), 1.0)


class TestVector(unittest.TestCase):
    """Test the Vector methods"""

    def test_vector_constructors(self):
        v1 = Vector(1, 2, 3)
        v2 = Vector((1, 2, 3))
        v3 = Vector(gp_Vec(1, 2, 3))
        v4 = Vector([1, 2, 3])
        v5 = Vector(gp_XYZ(1, 2, 3))

        for v in [v1, v2, v3, v4, v5]:
            self.assertTupleAlmostEquals((1, 2, 3), v.to_tuple(), 4)

        v6 = Vector((1, 2))
        v7 = Vector([1, 2])
        v8 = Vector(1, 2)

        for v in [v6, v7, v8]:
            self.assertTupleAlmostEquals((1, 2, 0), v.to_tuple(), 4)

        v9 = Vector()
        self.assertTupleAlmostEquals((0, 0, 0), v9.to_tuple(), 4)

        v9.X = 1.0
        v9.Y = 2.0
        v9.Z = 3.0
        self.assertTupleAlmostEquals((1, 2, 3), (v9.X, v9.Y, v9.Z), 4)

        with self.assertRaises(TypeError):
            Vector("vector")
        with self.assertRaises(TypeError):
            Vector(1, 2, 3, 4)

    def test_vector_rotate(self):
        """Validate vector rotate methods"""
        vector_x = Vector(1, 0, 1).rotate_x(45)
        vector_y = Vector(1, 2, 1).rotate_y(45)
        vector_z = Vector(-1, -1, 3).rotate_z(45)
        self.assertTupleAlmostEquals(
            vector_x.to_tuple(), (1, -math.sqrt(2) / 2, math.sqrt(2) / 2), 7
        )
        self.assertTupleAlmostEquals(vector_y.to_tuple(), (math.sqrt(2), 2, 0), 7)
        self.assertTupleAlmostEquals(vector_z.to_tuple(), (0, -math.sqrt(2), 3), 7)

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

    # def test_to_vertex(self):
    #     """Verify conversion of Vector to Vertex"""
    #     v = Vector(1, 2, 3).to_vertex()
    #     self.assertTrue(isinstance(v, Vertex))
    #     self.assertTupleAlmostEquals(v.to_tuple(), (1, 2, 3), 5)

    def test_dot(self):
        v1 = Vector(2, 2, 2)
        v2 = Vector(1, -1, 1)
        self.assertEqual(2.0, v1.dot(v2))

    def test_vector_add(self):
        result = Vector(1, 2, 0) + Vector(0, 0, 3)
        self.assertTupleAlmostEquals((1.0, 2.0, 3.0), result.to_tuple(), 3)

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
        self.assertTupleAlmostEquals(
            point.to_tuple(), (59 / 7, 55 / 7, 51 / 7), decimal_places
        )

        # test line projection
        vec = Vector(10, 10, 10)
        line = Vector(3, 4, 5)
        angle = vec.get_angle(line)

        vecLineProjection = vec.project_to_line(line)

        self.assertTupleAlmostEquals(
            vecLineProjection.normalized().to_tuple(),
            line.normalized().to_tuple(),
            decimal_places,
        )
        self.assertAlmostEqual(
            vec.length() * math.cos(angle), vecLineProjection.length(), decimal_places
        )

    def test_vector_not_implemented(self):
        v = Vector(1, 2, 3)
        with self.assertRaises(NotImplementedError):
            v.distance_to_line()
        with self.assertRaises(NotImplementedError):
            v.distance_to_plane()

    def test_vector_special_methods(self):
        v = Vector(1, 2, 3)
        self.assertEqual(repr(v), "Vector: (1.0, 2.0, 3.0)")
        self.assertEqual(str(v), "Vector: (1.0, 2.0, 3.0)")

    def test_vector_iter(self):
        self.assertEqual(sum([v for v in Vector(1, 2, 3)]), 6)


class TestMixin1D(unittest.TestCase):
    """Test the add in methods"""

    def test_position_at(self):
        self.assertTupleAlmostEquals(
            Edge.make_line((0, 0, 0), (1, 1, 1)).position_at(0.5).to_tuple(),
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

    def test_positions(self):
        e = Edge.make_line((0, 0, 0), (1, 1, 1))
        distances = [i / 4 for i in range(3)]
        pts = e.positions(distances)
        for i, position in enumerate(pts):
            self.assertTupleAlmostEquals(position.to_tuple(), (i / 4, i / 4, i / 4), 5)

    def test_tangent_at(self):
        self.assertTupleAlmostEquals(
            Edge.make_circle(1, angle1=0, angle2=90).tangent_at(1.0).to_tuple(),
            (-1, 0, 0),
            5,
        )
        tangent = (
            Edge.make_circle(1, angle1=0, angle2=90)
            .tangent_at(0.0, position_mode=PositionMode.PARAMETER)
            .to_tuple()
        )
        self.assertTrue(all([0.0 <= v <= 1.0 for v in tangent]))

    def test_normal(self):
        self.assertTupleAlmostEquals(
            Edge.make_circle(1, dir=(1, 0, 0), angle1=0, angle2=60).normal().to_tuple(),
            (1, 0, 0),
            5,
        )
        self.assertTupleAlmostEquals(
            Edge.make_ellipse(1, 0.5, dir=(1, 1, 0), angle1=0, angle2=90)
            .normal()
            .to_tuple(),
            (math.sqrt(2) / 2, math.sqrt(2) / 2, 0),
            5,
        )
        self.assertTupleAlmostEquals(
            Edge.make_spline(
                [
                    (1, 0),
                    (math.sqrt(2) / 2, math.sqrt(2) / 2),
                    (0, 1),
                ],
                tangents=((0, 1, 0), (-1, 0, 0)),
            )
            .normal()
            .to_tuple(),
            (0, 0, 1),
            5,
        )
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0, 0), (1, 1, 1)).normal()

    def test_center(self):
        c = Edge.make_circle(1, angle1=0, angle2=180)
        self.assertTupleAlmostEquals(
            c.center(center_of=CenterOf.GEOMETRY).to_tuple(), (0, 1, 0), 5
        )
        self.assertTupleAlmostEquals(
            c.center(center_of=CenterOf.MASS).to_tuple(),
            (0, 0.6366197723675814, 0),
            5,
        )
        self.assertTupleAlmostEquals(
            c.center(center_of=CenterOf.BOUNDING_BOX).to_tuple(), (0, 0.5, 0), 5
        )

    # TODO: Test after upgrade
    # def test_location_at(self):
    #     loc = Edge.make_circle(1, angle1=0, angle2=180).location_at(0.5)
    #     loc = Wire.make_circle(1, (0, 0, 0), (0, 0, 1)).location_at(0.25)
    #     self.assertTupleAlmostEquals(loc.position().to_tuple(), (0, 1, 0), 5)
    #     self.assertTupleAlmostEquals(loc.rotation().to_tuple(), (0, 0, 90), 5)
    def test_locations(self):
        pass

    def test_project(self):
        target = Face.make_rect(10, 10)
        source = Face.make_from_wires(Wire.make_circle(1, (0, 0, 1), (0, 0, 1)))
        shadow = source.project(target, d=(0, 0, -1))
        self.assertTupleAlmostEquals(shadow.center().to_tuple(), (0, 0, 0), 5)
        self.assertAlmostEqual(shadow.area(), math.pi, 5)


class TestMixin3D(unittest.TestCase):
    """Test that 3D add ins"""

    def test_chamfer(self):
        box = Solid.make_box(1, 1, 1)
        chamfer_box = box.chamfer(0.1, 0.2, box.edges().sort_by(Axis.Z)[-1:])
        self.assertAlmostEqual(chamfer_box.volume(), 1 - 0.01, 5)

    def test_shell(self):
        shell_box = Solid.make_box(1, 1, 1).shell([], thickness=-0.1)
        self.assertAlmostEqual(shell_box.volume(), 1 - 0.8**3, 5)
        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).shell([], thickness=0.1, kind=Kind.TANGENT)

    def test_is_inside(self):
        self.assertTrue(Solid.make_box(1, 1, 1).is_inside((0.5, 0.5, 0.5)))

    def test_dprism(self):
        # face
        f = Face.make_rect(0.5, 0.5)
        d = Solid.make_box(1, 1, 1, pnt=(-0.5, -0.5, 0)).dprism(
            None, [f], additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume(), 1 - 0.5**2, 5)

        # face with depth
        f = Face.make_rect(0.5, 0.5)
        d = Solid.make_box(1, 1, 1, pnt=(-0.5, -0.5, 0)).dprism(
            None, [f], depth=0.5, thru_all=False, additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume(), 1 - 0.5**3, 5)

        # face until
        f = Face.make_rect(0.5, 0.5)
        limit = Face.make_rect(1, 1, pnt=(0, 0, 0.5))
        d = Solid.make_box(1, 1, 1, pnt=(-0.5, -0.5, 0)).dprism(
            None, [f], up_to_face=limit, thru_all=False, additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume(), 1 - 0.5**3, 5)

        # wire
        w = Face.make_rect(0.5, 0.5).outer_wire()
        d = Solid.make_box(1, 1, 1, pnt=(-0.5, -0.5, 0)).dprism(
            None, [w], additive=False
        )
        self.assertTrue(d.is_valid())
        self.assertAlmostEqual(d.volume(), 1 - 0.5**2, 5)


class TestShape(unittest.TestCase):
    """Misc Shape tests"""

    def test_mirror(self):
        box_bb = Solid.make_box(1, 1, 1).mirror(Plane.XZ).bounding_box()
        self.assertAlmostEqual(box_bb.xmin, 0, 5)
        self.assertAlmostEqual(box_bb.xmax, 1, 5)
        self.assertAlmostEqual(box_bb.ymin, -1, 5)
        self.assertAlmostEqual(box_bb.ymax, 0, 5)

        box_bb = Solid.make_box(1, 1, 1).mirror().bounding_box()
        self.assertAlmostEqual(box_bb.zmin, -1, 5)
        self.assertAlmostEqual(box_bb.zmax, 0, 5)

    def test_compute_mass(self):
        with self.assertRaises(NotImplementedError):
            Shape.compute_mass(Vertex())

    def test_combined_center(self):
        objs = [Solid.make_box(1, 1, 1, pnt=(x, 0, 0)) for x in [-2, 1]]
        self.assertTupleAlmostEquals(
            Shape.combined_center(objs, center_of=CenterOf.MASS).to_tuple(),
            (0, 0.5, 0.5),
            5,
        )

        objs = [Solid.make_sphere(1, pnt=(x, 0, 0)) for x in [-2, 1]]
        self.assertTupleAlmostEquals(
            Shape.combined_center(objs, center_of=CenterOf.BOUNDING_BOX).to_tuple(),
            (-0.5, 0, 0),
            5,
        )
        with self.assertRaises(ValueError):
            Shape.combined_center(objs, center_of=CenterOf.GEOMETRY)

    def test_shape_type(self):
        self.assertEqual(Vertex().shape_type(), "Vertex")

    def test_scale(self):
        self.assertAlmostEqual(Solid.make_box(1, 1, 1).scale(2).volume(), 2**3, 5)

    def test_fuse(self):
        box1 = Solid.make_box(1, 1, 1)
        box2 = Solid.make_box(1, 1, 1, pnt=(1, 0, 0))
        combined = box1.fuse(box2, glue=True)
        self.assertTrue(combined.is_valid())
        self.assertAlmostEqual(combined.volume(), 2, 5)
        fuzzy = box1.fuse(box2, tol=1e-6)
        self.assertTrue(fuzzy.is_valid())
        self.assertAlmostEqual(fuzzy.volume(), 2, 5)

    def test_faces_intersected_by_line(self):
        box = Solid.make_box(1, 1, 1, pnt=(0, 0, 1))
        intersected_faces = box.faces_intersected_by_line((0, 0, 0), (0, 0, 1))
        self.assertTrue(box.faces().sort_by(sort_by=Axis.Z)[0] in intersected_faces)
        self.assertTrue(box.faces().sort_by(sort_by=Axis.Z)[-1] in intersected_faces)

        # This doesn't work?
        # intersected_faces = box.faces_intersected_by_line(
        #     (0, 0, 0), (0, 0, 1), direction=Direction.ALONG_AXIS
        # )
        # self.assertEqual(len(intersected_faces), 1)
        # self.assertTrue(box.faces().sort_by(sort_by=Axis.Z)[0] not in intersected_faces)
        # self.assertTrue(box.faces().sort_by(sort_by=Axis.Z)[-1] in intersected_faces)

    def test_split(self):
        box = Solid.make_box(1, 1, 1, pnt=(-0.5, 0, 0))
        halves = box.split(Face.make_rect(2, 2, normal=(1, 0, 0)))
        self.assertEqual(len(halves.solids()), 2)

    def test_distance(self):
        sphere1 = Solid.make_sphere(1, pnt=(-5, 0, 0))
        sphere2 = Solid.make_sphere(1, pnt=(5, 0, 0))
        self.assertAlmostEqual(sphere1.distance(sphere2), 8, 5)

    def test_distances(self):
        sphere1 = Solid.make_sphere(1, pnt=(-5, 0, 0))
        sphere2 = Solid.make_sphere(1, pnt=(5, 0, 0))
        sphere3 = Solid.make_sphere(1, pnt=(-5, 0, 5))
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
            invalid_object = box.fillet(0.75, box.edges())
            invalid_object.max_fillet(invalid_object.edges())

    def test_locate_bb(self):
        bounding_box = Solid.make_cone(1, 2, 1).bounding_box()
        relocated_bounding_box = Plane.XZ.from_local_coords(bounding_box)
        self.assertAlmostEqual(relocated_bounding_box.xmin, -2, 5)
        self.assertAlmostEqual(relocated_bounding_box.xmax, 2, 5)
        self.assertAlmostEqual(relocated_bounding_box.ymin, 0, 5)
        self.assertAlmostEqual(relocated_bounding_box.ymax, -1, 5)
        self.assertAlmostEqual(relocated_bounding_box.zmin, -2, 5)
        self.assertAlmostEqual(relocated_bounding_box.zmax, 2, 5)

    def test_is_equal(self):
        box = Solid.make_box(1, 1, 1)
        self.assertTrue(box.is_equal(box))

    def test_tessellate(self):
        box123 = Solid.make_box(1, 2, 3)
        verts, triangles = box123.tessellate(1e-6)
        self.assertEqual(len(verts), 24)
        self.assertEqual(len(triangles), 12)

    # def test_to_vtk_poly_data(self):

    #     from vtkmodules.vtkCommonDataModel import vtkPolyData

    #     f = Face.make_rect(2, 2)
    #     vtk = f.to_vtk_poly_data(normals=False)
    #     self.assertTrue(isinstance(vtk, vtkPolyData))
    #     self.assertEqual(vtk.GetNumberOfPolys(), 2)

    # def test_repr_javascript_(self):
    #     print(Shape._repr_javascript_(Face))

    def test_transformed(self):
        """Validate that transformed works the same as changing location"""
        rotation = (uniform(0, 360), uniform(0, 360), uniform(0, 360))
        offset = (uniform(0, 50), uniform(0, 50), uniform(0, 50))
        shape = Solid.make_box(1, 1, 1).transformed(rotation, offset)
        predicted_location = Location(offset) * Rotation(*rotation)
        located_shape = Solid.make_box(1, 1, 1).locate(predicted_location)
        intersect = shape.intersect(located_shape)
        self.assertAlmostEqual(intersect.volume(), 1, 5)


class TestShapeList(unittest.TestCase):
    """Test ShapeList functionality"""

    def test_filter_by(self):
        non_planar_faces = (
            Solid.make_cylinder(1, 1).faces().filter_by(GeomType.PLANE, reverse=True)
        )
        self.assertEqual(len(non_planar_faces), 1)
        self.assertAlmostEqual(non_planar_faces[0].area(), 2 * math.pi, 5)


class TestCompound(unittest.TestCase):
    def test_make_text(self):
        text = Compound.make_text("test", 10, 10)
        self.assertEqual(len(text.solids()), 4)

    def test_make_2d_text(self):
        arc = Edge.make_three_point_arc((-50, 0, 0), (0, 20, 0), (50, 0, 0))
        text = Compound.make_2d_text("test", 10, text_path=arc)
        self.assertEqual(len(text.faces()), 4)
        text = Compound.make_2d_text(
            "test", 10, halign=Halign.RIGHT, valign=Valign.TOP, text_path=arc
        )
        self.assertEqual(len(text.faces()), 4)

    def test_fuse(self):
        box1 = Solid.make_box(1, 1, 1)
        box2 = Solid.make_box(1, 1, 1, pnt=(1, 0, 0))
        combined = Compound.make_compound([box1]).fuse(box2, glue=True)
        self.assertTrue(combined.is_valid())
        self.assertAlmostEqual(combined.volume(), 2, 5)
        fuzzy = Compound.make_compound([box1]).fuse(box2, tol=1e-6)
        self.assertTrue(fuzzy.is_valid())
        self.assertAlmostEqual(fuzzy.volume(), 2, 5)

    # Doesn't work
    # def test_remove(self):
    #     box1 = Solid.make_box(1, 1, 1)
    #     box2 = Solid.make_box(1, 1, 1, pnt=(2, 0, 0))
    #     combined = Compound.make_compound([box1, box2])
    #     self.assertTrue(len(combined.remove(box2).solids()), 1)


class TestEdge(unittest.TestCase):
    def test_close(self):
        self.assertAlmostEqual(
            Edge.make_circle(1, angle2=180).close().length(), math.pi + 2, 5
        )
        self.assertAlmostEqual(Edge.make_circle(1).close().length(), 2 * math.pi, 5)

    def test_arc_center(self):
        self.assertTupleAlmostEquals(
            Edge.make_ellipse(2, 1).arc_center().to_tuple(), (0, 0, 0), 5
        )
        with self.assertRaises(ValueError):
            Edge.make_line((0, 0, 0), (0, 0, 1)).arc_center()

    def test_spline_with_parameters(self):
        spline = Edge.make_spline(
            points=[(0, 0, 0), (1, 1, 0), (2, 0, 0)], parameters=[0.0, 0.4, 1.0]
        )
        self.assertTupleAlmostEquals(spline.end_point().to_tuple(), (2, 0, 0), 5)
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
        self.assertTupleAlmostEquals(spline.end_point().to_tuple(), (3, 0, 0), 5)
        spline = Edge.make_spline_approx(
            [(0, 0), (1, 1), (2, 1), (3, 0)], smoothing=(1.0, 5.0, 10.0)
        )
        self.assertTupleAlmostEquals(spline.end_point().to_tuple(), (3, 0, 0), 5)

    # def test_distribute_locations(self):
    #     line = Edge.make_line((0, 0, 0), (10, 0, 0))
    #     locs = line.distribute_locations(3)
    #     self.assertTupleAlmostEquals(locs[0].position().to_tuple(), (0, 0, 0), 5)
    #     self.assertTupleAlmostEquals(locs[0].rotation().to_tuple(), (0, 0, 0), 5)


class TestFace(unittest.TestCase):
    def test_make_surface_from_curves(self):
        bottom_edge = Edge.make_circle(radius=1, angle2=90)
        top_edge = Edge.make_circle(radius=1, pnt=(0, 0, 1), angle2=90)
        curved = Face.make_surface_from_curves(bottom_edge, top_edge)
        self.assertTrue(curved.is_valid())
        self.assertAlmostEqual(curved.area(), math.pi / 2, 5)
        self.assertTupleAlmostEquals(
            curved.normal_at().to_tuple(), (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 5
        )

        bottom_wire = Wire.make_circle(1, center=(0, 0, 0), normal=(0, 0, 1))
        top_wire = Wire.make_circle(1, center=(0, 0, 1), normal=(0, 0, 1))
        curved = Face.make_surface_from_curves(bottom_wire, top_wire)
        self.assertTrue(curved.is_valid())
        self.assertAlmostEqual(curved.area(), 2 * math.pi, 5)

    def test_center(self):
        test_face = Face.make_from_wires(
            Wire.make_polygon([(0, 0), (1, 0), (1, 1), (0, 0)])
        )
        self.assertTupleAlmostEquals(
            test_face.center(center_of=CenterOf.MASS).to_tuple(), (2 / 3, 1 / 3, 0), 1
        )
        self.assertTupleAlmostEquals(
            test_face.center(center_of=CenterOf.BOUNDING_BOX).to_tuple(),
            (0.5, 0.5, 0),
            5,
        )

    def test_make_rect(self):
        test_face = Face.make_plane()
        self.assertTupleAlmostEquals(test_face.normal_at().to_tuple(), (0, 0, 1), 5)


class TestPlane(unittest.TestCase):
    """Plane with class properties"""

    def test_class_properties(self):
        """Validate
        Name        xDir    yDir    zDir
        =========== ======= ======= ======
        XY          +x      +y      +z
        YZ          +y      +z      +x
        ZX          +z      +x      +y
        XZ          +x      +z      -y
        YX          +y      +x      -z
        ZY          +z      +y      -x
        front       +x      +y      +z
        back        -x      +y      -z
        left        +z      +y      -x
        right       -z      +y      +x
        top         +x      -z      +y
        bottom      +x      +z      -y
        """
        planes = [
            (Plane.XY, (1, 0, 0), (0, 0, 1)),
            (Plane.YZ, (0, 1, 0), (1, 0, 0)),
            (Plane.ZX, (0, 0, 1), (0, 1, 0)),
            (Plane.XZ, (1, 0, 0), (0, -1, 0)),
            (Plane.YX, (0, 1, 0), (0, 0, -1)),
            (Plane.ZY, (0, 0, 1), (-1, 0, 0)),
            (Plane.front, (1, 0, 0), (0, 0, 1)),
            (Plane.back, (-1, 0, 0), (0, 0, -1)),
            (Plane.left, (0, 0, 1), (-1, 0, 0)),
            (Plane.right, (0, 0, -1), (1, 0, 0)),
            (Plane.top, (1, 0, 0), (0, 1, 0)),
            (Plane.bottom, (1, 0, 0), (0, -1, 0)),
        ]
        for plane, x_dir, z_dir in planes:
            self.assertTupleAlmostEquals(plane.x_dir.to_tuple(), x_dir, 5)
            self.assertTupleAlmostEquals(plane.z_dir.to_tuple(), z_dir, 5)

    def test_repr(self):
        self.assertEqual(
            repr(Plane.XY),
            "Plane(o=(0.00, 0.00, 0.00), x=(1.00, 0.00, 0.00), z=(0.00, 0.00, 1.00))",
        )

    def test_set_origin(self):
        offset_plane = Plane.XY
        offset_plane.set_origin2d(1, 1)
        self.assertTupleAlmostEquals(offset_plane.origin.to_tuple(), (1, 1, 0), 5)

    def test_rotated(self):
        rotated_plane = Plane.XY.rotated((45, 0, 0))
        self.assertTupleAlmostEquals(rotated_plane.x_dir.to_tuple(), (1, 0, 0), 5)
        self.assertTupleAlmostEquals(
            rotated_plane.z_dir.to_tuple(), (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 5
        )


class TestAxis(unittest.TestCase):
    """Test the Axis class"""

    def test_axis_from_occt(self):
        occt_axis = gp_Ax1(gp_Pnt(1, 1, 1), gp_Dir(0, 1, 0))
        test_axis = Axis.from_occt(occt_axis)
        self.assertTupleAlmostEquals(test_axis.position.to_tuple(), (1, 1, 1), 5)
        self.assertTupleAlmostEquals(test_axis.direction.to_tuple(), (0, 1, 0), 5)

    def test_axis_repr_and_str(self):
        self.assertEqual(repr(Axis.X), "((0.0, 0.0, 0.0),(1.0, 0.0, 0.0))")
        self.assertEqual(str(Axis.Y), "Axis: ((0.0, 0.0, 0.0),(0.0, 1.0, 0.0))")

    def test_axis_copy(self):
        x_copy = Axis.X.copy()
        self.assertTupleAlmostEquals(x_copy.position.to_tuple(), (0, 0, 0), 5)
        self.assertTupleAlmostEquals(x_copy.direction.to_tuple(), (1, 0, 0), 5)

    def test_axis_to_location(self):
        # TODO: Verify this is correct
        x_location = Axis.X.to_location()
        self.assertTrue(isinstance(x_location, Location))
        self.assertTupleAlmostEquals(x_location.position.to_tuple(), (0, 0, 0), 5)
        self.assertTupleAlmostEquals(
            x_location.orientation.to_tuple(), (-math.pi, -math.pi / 2, 0), 5
        )

    def test_axis_to_plane(self):
        x_plane = Axis.X.to_plane()
        self.assertTrue(isinstance(x_plane, Plane))
        self.assertTupleAlmostEquals(x_plane.origin.to_tuple(), (0, 0, 0), 5)
        self.assertTupleAlmostEquals(x_plane.z_dir.to_tuple(), (1, 0, 0), 5)

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

    def test_axis_reversed(self):
        self.assertTupleAlmostEquals(
            Axis.X.reversed().direction.to_tuple(), (-1, 0, 0), 5
        )


class TestSolid(unittest.TestCase):
    def test_extrude_with_taper(self):
        base = Face.make_rect(1, 1)
        pyramid = Solid.extrude_linear(base, normal=(0, 0, 1), taper=1)
        self.assertLess(
            pyramid.faces().sort_by(Axis.Z)[-1].area(),
            pyramid.faces().sort_by(Axis.Z)[0].area(),
        )

    def test_extrude_linear_with_rotation(self):
        # Face
        base = Face.make_rect(1, 1)
        twist = Solid.extrude_linear_with_rotation(
            base, center=(0, 0, 0), normal=(0, 0, 1), angle=45
        )
        self.assertAlmostEqual(twist.volume(), 1, 5)
        top = twist.faces().sort_by(Axis.Z)[-1].rotate(Axis.Z, 45)
        bottom = twist.faces().sort_by(Axis.Z)[0]
        self.assertAlmostEqual(top.translate((0, 0, -1)).intersect(bottom).area(), 1, 5)
        # Wire
        base = Wire.make_rect(1, 1)
        twist = Solid.extrude_linear_with_rotation(
            base, center=(0, 0, 0), normal=(0, 0, 1), angle=45
        )
        self.assertAlmostEqual(twist.volume(), 1, 5)
        top = twist.faces().sort_by(Axis.Z)[-1].rotate(Axis.Z, 45)
        bottom = twist.faces().sort_by(Axis.Z)[0]
        self.assertAlmostEqual(top.translate((0, 0, -1)).intersect(bottom).area(), 1, 5)


class ProjectionTests(unittest.TestCase):
    def test_flat_projection(self):

        sphere = Solid.make_sphere(50)
        projection_direction = Vector(0, -1, 0)
        planar_text_faces = (
            Compound.make_2d_text("Flat", 30, halign=Halign.CENTER)
            .rotate(Axis.X, 90)
            .faces()
        )
        projected_text_faces = [
            f.project_to_shape(sphere, projection_direction)[0]
            for f in planar_text_faces
        ]
        self.assertEqual(len(projected_text_faces), 4)

    def test_conical_projection(self):
        sphere = Solid.make_sphere(50)
        projection_center = Vector(0, 0, 0)
        planar_text_faces = (
            Compound.make_2d_text("Conical", 25, halign=Halign.CENTER)
            .rotate(Axis.X, 90)
            .translate((0, -60, 0))
            .faces()
        )

        projected_text_faces = [
            f.project_to_shape(sphere, center=projection_center)[0]
            for f in planar_text_faces
        ]
        self.assertEqual(len(projected_text_faces), 8)

    def test_projection_with_internal_points(self):
        sphere = Solid.make_sphere(50)
        f = Face.make_rect(10, 10).translate(Vector(0, 0, 60))
        pts = [Vector(x, y, 60) for x in [-5, 5] for y in [-5, 5]]
        projected_faces = f.project_to_shape(
            sphere, center=(0, 0, 0), internal_face_points=pts
        )
        self.assertEqual(len(projected_faces), 1)

    def test_text_projection(self):

        sphere = Solid.make_sphere(50)
        arch_path = (
            sphere.cut(
                Solid.make_cylinder(
                    80, 100, pnt=Vector(-50, 0, -70), dir=Vector(1, 0, 0)
                )
            )
            .edges()
            .sort_by(Axis.Z)[0]
        )

        projected_text = sphere.project_text(
            txt="fox",
            fontsize=14,
            depth=3,
            path=arch_path,
        )
        self.assertEqual(len(projected_text.solids()), 3)
        projected_text = sphere.project_text(
            txt="dog",
            fontsize=14,
            depth=0,
            path=arch_path,
        )
        self.assertEqual(len(projected_text.solids()), 0)
        self.assertEqual(len(projected_text.faces()), 3)

    def test_error_handling(self):
        sphere = Solid.make_sphere(50)
        f = Face.make_rect(10, 10)
        with self.assertRaises(ValueError):
            f.project_to_shape(sphere, center=None, direction=None)[0]
        w = Face.make_rect(10, 10).outer_wire()
        with self.assertRaises(ValueError):
            w.project_to_shape(sphere, center=None, direction=None)[0]


class VertexTests(unittest.TestCase):
    """Test the extensions to the cadquery Vertex class"""

    def test_basic_vertex(self):
        v = Vertex()
        self.assertEqual(0, v.X)

        v = Vertex(1, 1, 1)
        self.assertEqual(1, v.X)
        self.assertEqual(Vector, type(v.center()))

        with self.assertRaises(ValueError):
            Vertex(Vector())

    def test_vertex_add(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertTupleAlmostEquals(
            (test_vertex + (100, -40, 10)).to_tuple(), (100, -40, 10), 7
        )
        self.assertTupleAlmostEquals(
            (test_vertex + Vector(100, -40, 10)).to_tuple(), (100, -40, 10), 7
        )
        self.assertTupleAlmostEquals(
            (test_vertex + Vertex(100, -40, 10)).to_tuple(),
            (100, -40, 10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex + [1, 2, 3]

    def test_vertex_sub(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertTupleAlmostEquals(
            (test_vertex - (100, -40, 10)).to_tuple(), (-100, 40, -10), 7
        )
        self.assertTupleAlmostEquals(
            (test_vertex - Vector(100, -40, 10)).to_tuple(), (-100, 40, -10), 7
        )
        self.assertTupleAlmostEquals(
            (test_vertex - Vertex(100, -40, 10)).to_tuple(),
            (-100, 40, -10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex - [1, 2, 3]

    def test_vertex_str(self):
        self.assertEqual(str(Vertex(0, 0, 0)), "Vertex: (0.0, 0.0, 0.0)")

    def test_vertex_to_vector(self):
        self.assertIsInstance(Vertex(0, 0, 0).to_vector(), Vector)
        self.assertTupleAlmostEquals(
            Vertex(0, 0, 0).to_vector().to_tuple(), (0.0, 0.0, 0.0), 7
        )


class TestWire(unittest.TestCase):
    def test_ellipse_arc(self):
        full_ellipse = Wire.make_ellipse(2, 1)
        half_ellipse = Wire.make_ellipse(2, 1, angle1=0, angle2=180, closed=True)
        self.assertAlmostEqual(full_ellipse.area() / 2, half_ellipse.area(), 5)

    def test_conical_helix(self):
        helix = Wire.make_helix(1, 4, 1, normal=(-1, 0, 0), angle=10, lefthand=True)
        self.assertAlmostEqual(helix.length(), 34.102023034708374, 5)

    def test_stitch(self):
        half_ellipse1 = Wire.make_ellipse(2, 1, angle1=0, angle2=180, closed=False)
        half_ellipse2 = Wire.make_ellipse(2, 1, angle1=180, angle2=360, closed=False)
        ellipse = half_ellipse1.stitch(half_ellipse2)
        self.assertEqual(len(ellipse.wires()), 1)

    def test_fillet_2d(self):
        square = Wire.make_rect(1, 1)
        squaroid = square.fillet_2d(0.1, square.vertices())
        self.assertAlmostEqual(
            squaroid.length(), 4 * (1 - 2 * 0.1) + 2 * math.pi * 0.1, 5
        )

    def test_chamfer_2d(self):
        square = Wire.make_rect(1, 1)
        squaroid = square.chamfer_2d(0.1, square.vertices())
        self.assertAlmostEqual(
            squaroid.length(), 4 * (1 - 2 * 0.1 + 0.1 * math.sqrt(2)), 5
        )


class TestFunctions(unittest.TestCase):
    def test_edges_to_wires(self):
        square_edges = Face.make_rect(1, 1).edges()
        rectangle_edges = Face.make_rect(2, 1, pnt=(5, 0)).edges()
        wires = edges_to_wires(square_edges + rectangle_edges)
        self.assertEqual(len(wires), 2)
        self.assertAlmostEqual(wires[0].length(), 4, 5)
        self.assertAlmostEqual(wires[1].length(), 6, 5)


if __name__ == "__main__":
    unittest.main()
