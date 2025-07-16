"""
build123d imports

name: test_plane.py
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

# Always equal to any other object, to test that __eq__ cooperation is working
import copy
import math
import random
import unittest

import numpy as np
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from build123d.build_common import Locations
from build123d.build_enums import Align, GeomType, Mode
from build123d.build_part import BuildPart
from build123d.build_sketch import BuildSketch
from build123d.geometry import Axis, Location, Plane, Pos, Vector
from build123d.objects_part import Box, Cylinder
from build123d.objects_sketch import Circle, Rectangle
from build123d.operations_generic import fillet, add
from build123d.operations_part import extrude
from build123d.topology import Edge, Face, Solid, Vertex


class AlwaysEqual:
    def __eq__(self, other):
        return True


class TestPlane(unittest.TestCase):
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
            self.assertAlmostEqual(plane.x_dir, x_dir, 5)
            self.assertAlmostEqual(plane.z_dir, z_dir, 5)

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
            self.assertAlmostEqual(p.origin, o, 6)
            self.assertAlmostEqual(p.x_dir, x, 6)
            self.assertAlmostEqual(p.y_dir, y, 6)
            self.assertAlmostEqual(p.z_dir, z, 6)
        with self.assertRaises(TypeError):
            Plane()
        with self.assertRaises(TypeError):
            Plane(o, z_dir="up")
        with self.assertRaises(TypeError):
            Plane(o, forward="up")

        # rotated location around z
        loc = Location((0, 0, 0), (0, 0, 45))
        p_from_loc = Plane(loc)
        p_from_named_loc = Plane(location=loc)
        for p in [p_from_loc, p_from_named_loc]:
            self.assertAlmostEqual(p.origin, (0, 0, 0), 6)
            self.assertAlmostEqual(p.x_dir, (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6)
            self.assertAlmostEqual(p.y_dir, (-math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6)
            self.assertAlmostEqual(p.z_dir, (0, 0, 1), 6)
            self.assertAlmostEqual(loc.position, p.location.position, 6)
            self.assertAlmostEqual(loc.orientation, p.location.orientation, 6)

        # rotated location around x and origin <> (0,0,0)
        loc = Location((0, 2, -1), (45, 0, 0))
        p = Plane(loc)
        self.assertAlmostEqual(p.origin, (0, 2, -1), 6)
        self.assertAlmostEqual(p.x_dir, (1, 0, 0), 6)
        self.assertAlmostEqual(p.y_dir, (0, math.sqrt(2) / 2, math.sqrt(2) / 2), 6)
        self.assertAlmostEqual(p.z_dir, (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 6)
        self.assertAlmostEqual(loc.position, p.location.position, 6)
        self.assertAlmostEqual(loc.orientation, p.location.orientation, 6)

        # from a face
        f = Face.make_rect(1, 2).located(Location((1, 2, 3), (45, 0, 45)))
        p_from_face = Plane(f)
        p_from_named_face = Plane(face=f)
        plane_from_gp_pln = Plane(gp_pln=p_from_face.wrapped)
        p_deep_copy = copy.deepcopy(p_from_face)
        for p in [p_from_face, p_from_named_face, plane_from_gp_pln, p_deep_copy]:
            self.assertAlmostEqual(p.origin, (1, 2, 3), 6)
            self.assertAlmostEqual(p.x_dir, (math.sqrt(2) / 2, 0.5, 0.5), 6)
            self.assertAlmostEqual(p.y_dir, (-math.sqrt(2) / 2, 0.5, 0.5), 6)
            self.assertAlmostEqual(p.z_dir, (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 6)
            self.assertAlmostEqual(f.location.position, p.location.position, 6)
            self.assertAlmostEqual(f.location.orientation, p.location.orientation, 6)

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
            self.assertAlmostEqual(p.origin, (0, 0, 0), 6)
            self.assertAlmostEqual(p.x_dir, Vector(x).normalized(), 6)
            self.assertAlmostEqual(p.y_dir, Vector(y).normalized(), 6)
            self.assertAlmostEqual(p.z_dir, (0, 0, 1), 6)

        with self.assertRaises(TypeError):
            Plane(Edge.make_line((0, 0), (0, 1)))

        # can be instantiated from planar faces of surface types other than Geom_Plane
        # this loft creates the trapezoid faces of type Geom_BSplineSurface
        lofted_solid = Solid.make_loft(
            [
                Rectangle(3, 1).wire(),
                Pos(0, 0, 1) * Rectangle(1, 1).wire(),
            ]
        )

        expected = [
            # Trapezoid face, negative y coordinate
            (
                Axis.X.direction,  # plane x_dir
                Axis.Z.direction,  # plane y_dir
                -Axis.Y.direction,  # plane z_dir
            ),
            # Trapezoid face, positive y coordinate
            (
                -Axis.X.direction,
                Axis.Z.direction,
                Axis.Y.direction,
            ),
        ]
        # assert properties of the trapezoid faces
        for i, f in enumerate(lofted_solid.faces() | Plane.XZ > Axis.Y):
            p = Plane(f)
            f_props = GProp_GProps()
            BRepGProp.SurfaceProperties_s(f.wrapped, f_props)
            self.assertAlmostEqual(p.origin, Vector(f_props.CentreOfMass()), 6)
            self.assertAlmostEqual(p.x_dir, expected[i][0], 6)
            self.assertAlmostEqual(p.y_dir, expected[i][1], 6)
            self.assertAlmostEqual(p.z_dir, expected[i][2], 6)

    def test_plane_from_axis(self):
        origin = Vector(1, 2, 3)
        direction = Vector(0, 0, 1)
        axis = Axis(origin, direction)
        plane = Plane(axis)

        self.assertEqual(plane.origin, origin)
        self.assertTrue(plane.z_dir, direction.normalized())
        self.assertAlmostEqual(plane.x_dir.length, 1.0, places=12)
        self.assertAlmostEqual(plane.y_dir.length, 1.0, places=12)
        self.assertAlmostEqual(plane.z_dir.length, 1.0, places=12)

    def test_plane_from_axis_with_x_dir(self):
        origin = Vector(0, 0, 0)
        z_dir = Vector(0, 0, 1)
        x_dir = Vector(1, 0, 0)
        axis = Axis(origin, z_dir)
        plane = Plane(axis, x_dir)

        self.assertEqual(plane.origin, origin)
        self.assertEqual(plane.z_dir, z_dir.normalized())
        self.assertEqual(plane.x_dir, x_dir.normalized())
        self.assertEqual(plane.y_dir, z_dir.cross(x_dir).normalized())

    def test_plane_from_axis_with_kwargs(self):
        axis = Axis((0, 0, 0), (0, 1, 0))
        x_dir = Vector(1, 0, 0)
        plane = Plane(axis=axis, x_dir=x_dir)

        self.assertEqual(plane.z_dir, Vector(0, 1, 0))
        self.assertEqual(plane.x_dir, x_dir.normalized())

    def test_plane_from_axis_without_x_dir(self):
        axis = Axis((0, 0, 0), (1, 0, 0))
        plane = Plane(axis)

        self.assertEqual(plane.z_dir, Vector(1, 0, 0))
        self.assertAlmostEqual(plane.x_dir.length, 1.0, places=12)
        self.assertAlmostEqual(plane.y_dir.length, 1.0, places=12)
        self.assertGreater(plane.z_dir.cross(plane.x_dir).dot(plane.y_dir), 0.99)

    def test_plane_from_axis_invalid_x_dir(self):
        axis = Axis((0, 0, 0), (0, 0, 1))
        with self.assertRaises(ValueError):
            Plane(axis, x_dir=(0, 0, 0))
        with self.assertRaises(TypeError):
            Plane(axis, "front")

    def test_plane_neg(self):
        p = Plane(
            origin=(1, 2, 3),
            x_dir=Vector(1, 2, 3).normalized(),
            z_dir=Vector(4, 5, 6).normalized(),
        )
        p2 = -p
        self.assertAlmostEqual(p2.origin, p.origin, 6)
        self.assertAlmostEqual(p2.x_dir, p.x_dir, 6)
        self.assertAlmostEqual(p2.z_dir, -p.z_dir, 6)
        self.assertAlmostEqual(p2.y_dir, (-p.z_dir).cross(p.x_dir).normalized(), 6)
        p3 = p.reverse()
        self.assertAlmostEqual(p3.origin, p.origin, 6)
        self.assertAlmostEqual(p3.x_dir, p.x_dir, 6)
        self.assertAlmostEqual(p3.z_dir, -p.z_dir, 6)
        self.assertAlmostEqual(p3.y_dir, (-p.z_dir).cross(p.x_dir).normalized(), 6)

    def test_plane_mul(self):
        p = Plane(origin=(1, 2, 3), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
        p2 = p * Location((1, 2, -1), (0, 0, 45))
        self.assertAlmostEqual(p2.origin, (2, 4, 2), 6)
        self.assertAlmostEqual(p2.x_dir, (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6)
        self.assertAlmostEqual(p2.y_dir, (-math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 6)
        self.assertAlmostEqual(p2.z_dir, (0, 0, 1), 6)

        p2 = p * Location((1, 2, -1), (0, 45, 0))
        self.assertAlmostEqual(p2.origin, (2, 4, 2), 6)
        self.assertAlmostEqual(p2.x_dir, (math.sqrt(2) / 2, 0, -math.sqrt(2) / 2), 6)
        self.assertAlmostEqual(p2.y_dir, (0, 1, 0), 6)
        self.assertAlmostEqual(p2.z_dir, (math.sqrt(2) / 2, 0, math.sqrt(2) / 2), 6)

        p2 = p * Location((1, 2, -1), (45, 0, 0))
        self.assertAlmostEqual(p2.origin, (2, 4, 2), 6)
        self.assertAlmostEqual(p2.x_dir, (1, 0, 0), 6)
        self.assertAlmostEqual(p2.y_dir, (0, math.sqrt(2) / 2, math.sqrt(2) / 2), 6)
        self.assertAlmostEqual(p2.z_dir, (0, -math.sqrt(2) / 2, math.sqrt(2) / 2), 6)
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
            np.testing.assert_allclose(target_point, local_box_vertices[i], 1e-7)

    def test_localize_vertex(self):
        v_x, v_y, v_z = (random.random(), random.random(), random.random())
        vertex = Vertex(v_x, v_y, v_z)
        self.assertAlmostEqual(
            Plane.YZ.to_local_coords(Vector(vertex)), (v_y, v_z, v_x), 5
        )
        self.assertAlmostEqual(
            Vector(Plane.YZ.to_local_coords(vertex)), (v_y, v_z, v_x), 5
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
        self.assertAlmostEqual(pln.origin, (1, 2, 3), 5)

    def test_rotated(self):
        rotated_plane = Plane.XY.rotated((45, 0, 0))
        self.assertAlmostEqual(rotated_plane.x_dir, (1, 0, 0), 5)
        self.assertAlmostEqual(
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
        # __eq__ cooperation
        self.assertEqual(Plane.XY, AlwaysEqual())

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

    def test_set(self):
        p0 = Plane((0, 1, 2), (3, 4, 5), (6, 7, 8))
        for i in range(1, 8):
            for j in range(1, 8):
                for k in range(1, 8):
                    p1 = Plane(
                        (p0.origin.X + 1.0 / (10**i), p0.origin.Y, p0.origin.Z),
                        (p0.x_dir.X + 1.0 / (10**j), p0.x_dir.Y, p0.x_dir.Z),
                        (p0.z_dir.X + 1.0 / (10**k), p0.z_dir.Y, p0.z_dir.Z),
                    )
                    if p0 == p1:
                        self.assertEqual(len(set([p0, p1])), 1)
                    else:
                        self.assertEqual(len(set([p0, p1])), 2)

    def test_to_location(self):
        loc = Plane(origin=(1, 2, 3), x_dir=(0, 1, 0), z_dir=(0, 0, 1)).location
        self.assertAlmostEqual(loc.position, (1, 2, 3), 5)
        self.assertAlmostEqual(loc.orientation, (0, 0, 90), 5)

    def test_intersect(self):
        self.assertAlmostEqual(
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
        self.assertAlmostEqual(i, (1, 2, 0), 5)

        a = Axis((0, 0, 0), (1, 1, 0))
        i = Plane.XY & a
        self.assertTrue(isinstance(i, Axis))
        self.assertEqual(i, a)

        a = Axis((1, 2, -1), (0, 0, 1))
        i = Plane.XY & a
        self.assertTrue(isinstance(i, Vector))
        self.assertAlmostEqual(i, Vector(1, 2, 0), 5)

    def test_plane_origin_setter(self):
        pln = Plane.XY
        pln.origin = (1, 2, 3)
        ocp_origin = Vector(pln.wrapped.Location())
        self.assertAlmostEqual(ocp_origin, (1, 2, 3), 5)


if __name__ == "__main__":
    unittest.main()
