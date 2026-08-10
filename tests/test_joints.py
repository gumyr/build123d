"""
joints unittests

name: test_joints.py
by:   Gumyr
date: August 24, 2023

desc:
    This python module contains the unittests for the Joint base and
    derived classes.

license:

    Copyright 2023 Gumyr

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

import copy
import unittest

from build123d.build_enums import Align, CenterOf, GeomType
from build123d.build_common import Mode
from build123d.build_part import BuildPart
from build123d.build_sketch import BuildSketch
from build123d.geometry import Axis, Location, Plane, Rotation, Vector, VectorLike
from build123d.joints import (
    BallJoint,
    CylindricalJoint,
    LinearJoint,
    RevoluteJoint,
    RigidJoint,
)
from build123d.objects_part import Box, Cone, Cylinder, Sphere
from build123d.objects_sketch import Circle
from build123d.operations_part import extrude
from build123d.topology import Edge, Solid


class DirectApiTestCase(unittest.TestCase):
    def assertTupleAlmostEquals(
        self,
        first: tuple[float, ...],
        second: tuple[float, ...],
        places: int,
        msg: str = None,
    ):
        """Check Tuples"""
        self.assertEqual(len(second), len(first))
        for i, j in zip(second, first):
            self.assertAlmostEqual(i, j, places, msg=msg)

    def assertVectorAlmostEquals(
        self, first: Vector, second: VectorLike, places: int, msg: str = None
    ):
        second_vector = Vector(second)
        self.assertAlmostEqual(first.X, second_vector.X, places, msg=msg)
        self.assertAlmostEqual(first.Y, second_vector.Y, places, msg=msg)
        self.assertAlmostEqual(first.Z, second_vector.Z, places, msg=msg)


class TestRigidJoint(DirectApiTestCase):
    def test_rigid_joint(self):
        base = Solid.make_box(1, 1, 1)
        j1 = RigidJoint("top", base, Location(Vector(0.5, 0.5, 1)))
        fixed_top = Solid.make_box(1, 1, 1)
        j2 = RigidJoint("bottom", fixed_top, Location((0.5, 0.5, 0)))
        j1.connect_to(j2)
        bbox = fixed_top.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (0, 0, 1), 5)
        self.assertVectorAlmostEquals(bbox.max, (1, 1, 2), 5)

        self.assertVectorAlmostEquals(j2.symbol.location.position, (0.5, 0.5, 1), 6)
        self.assertVectorAlmostEquals(j2.symbol.location.orientation, (0, 0, 0), 6)

    def test_builder(self):
        with BuildPart() as test:
            Box(3, 3, 1)
            RigidJoint("test")
            Cylinder(1, 3)

        self.assertTrue(isinstance(test.part.joints["test"], RigidJoint))

    def test_no_to_part(self):
        with self.assertRaises(ValueError):
            RigidJoint("test")

    def test_error_handling(self):
        j1 = RigidJoint("one", Box(1, 1, 1))
        with self.assertRaises(TypeError):
            j1.connect_to(Solid.make_box(1, 1, 1))

        with self.assertRaises(TypeError):
            j1.relative_to(Solid.make_box(1, 1, 1))


class TestRevoluteJoint(DirectApiTestCase):
    def test_revolute_joint_with_angle_reference(self):
        revolute_base = Solid.make_cylinder(1, 1)
        j1 = RevoluteJoint(
            label="top",
            to_part=revolute_base,
            axis=Axis((0, 0, 1), (0, 0, 1)),
            angle_reference=(1, 0, 0),
            angular_range=(0, 180),
        )
        fixed_top = Solid.make_box(1, 0.5, 1)
        j2 = RigidJoint("bottom", fixed_top, Location((0.5, 0.25, 0)))

        j1.connect_to(j2, angle=90)
        bbox = fixed_top.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-0.25, -0.5, 1), 5)
        self.assertVectorAlmostEquals(bbox.max, (0.25, 0.5, 2), 5)

        self.assertVectorAlmostEquals(j2.symbol.location.position, (0, 0, 1), 6)
        self.assertVectorAlmostEquals(j2.symbol.location.orientation, (0, 0, 90), 6)
        self.assertEqual(len(j1.symbol.edges()), 3)

    def test_revolute_joint_absolute_locations(self):
        b1 = Box(10, 10, 1)
        b2 = Box(5, 5, 1)
        j1 = RigidJoint("j1", b1, Location((-4, -4, 0.5)))
        j2 = RevoluteJoint("j2", b2, Axis((2.5, 2.5, 0), (0, -1, 0)))

        j1.connect_to(j2, angle=0)

        self.assertVectorAlmostEquals(j1.location.position, j2.location.position, 5)
        self.assertVectorAlmostEquals(
            j1.location.orientation, j2.location.orientation, 5
        )

    def test_linear_revolute_joint(self):
        base = Box(10, 10, 2)
        arm = Box(2, 1, 2, align=(Align.CENTER, Align.CENTER, Align.MIN))

        base_top_edges = (
            base.edges().filter_by(Axis.X, tolerance=30).sort_by(Axis.Z)[-2:]
        )
        linear_axis = Axis(Edge.make_mid_way(*base_top_edges, 0.33))
        j1 = LinearJoint(
            "slot",
            base,
            axis=linear_axis,
            linear_range=(0, base_top_edges[0].length),
        )
        j2 = RevoluteJoint("pin", arm, axis=Axis.Z, angular_range=(0, 360))

        j1.connect_to(j2, position=6, angle=60)

        target_location = Rotation(0, 0, 60)
        target_location.position = linear_axis.position + linear_axis.direction * 6
        self.assertVectorAlmostEquals(target_location.position, j2.location.position, 5)
        self.assertVectorAlmostEquals(
            target_location.orientation, j2.location.orientation, 5
        )

    def test_revolute_joint_non_z_axis(self):
        base_part = Box(6, 4, 2)
        rotating_part = Cone(2, 1, 2)
        j1 = RevoluteJoint("j1", base_part, Axis((3, 0, 1), (0, -1, 0)))
        j2 = RigidJoint("j2", rotating_part, Location((-2, 0, -1), (90, 0, -90)))

        base_part.joints["j1"].connect_to(rotating_part.joints["j2"], angle=30)

        self.assertVectorAlmostEquals(base_part.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(base_part.location.orientation, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(
            rotating_part.location.position, (4.23, 0, 2.87), 2
        )
        self.assertVectorAlmostEquals(
            rotating_part.location.orientation, (0, -30, 0), 5
        )

        self.assertVectorAlmostEquals(j1.location.position, (3, 0, 1), 5)
        self.assertVectorAlmostEquals(j1.location.orientation, (90, 0, -90), 5)
        self.assertVectorAlmostEquals(j2.location.position, (3, 0, 1), 5)
        self.assertVectorAlmostEquals(j2.location.orientation, (90, 0, -60), 5)

    def test_revolute_joint_without_angle_reference(self):
        revolute_base = Solid.make_cylinder(1, 1)
        j1 = RevoluteJoint(
            label="top",
            to_part=revolute_base,
            axis=Axis((0, 0, 1), (0, 0, 1)),
        )
        self.assertVectorAlmostEquals(j1.angle_reference, (1, 0, 0), 5)

    def test_revolute_joint_error_bad_angle_reference(self):
        """Test that the angle_reference must be normal to the axis"""
        revolute_base = Solid.make_cylinder(1, 1)
        with self.assertRaises(ValueError):
            RevoluteJoint(
                "top",
                revolute_base,
                axis=Axis((0, 0, 1), (0, 0, 1)),
                angle_reference=(1, 0, 1),
            )

    def test_revolute_joint_error_bad_angle(self):
        """Test that the joint angle is within bounds"""
        revolute_base = Solid.make_cylinder(1, 1)
        j1 = RevoluteJoint("top", revolute_base, Axis.Z, angular_range=(0, 180))
        fixed_top = Solid.make_box(1, 0.5, 1)
        j2 = RigidJoint("bottom", fixed_top, Location((0.5, 0.25, 0)))
        with self.assertRaises(ValueError):
            j1.connect_to(j2, angle=270)

    def test_revolute_joint_error_bad_joint_type(self):
        """Test that the joint angle is within bounds"""
        revolute_base = Solid.make_cylinder(1, 1)
        j1 = RevoluteJoint("top", revolute_base, Axis.Z, (0, 180))
        fixed_top = Solid.make_box(1, 0.5, 1)
        j2 = RevoluteJoint("bottom", fixed_top, Axis.Z, (0, 180))
        with self.assertRaises(TypeError):
            j1.connect_to(j2, angle=0)

    def test_builder(self):
        with BuildPart() as test:
            Box(3, 3, 1)
            RevoluteJoint("test")
            Cylinder(1, 3)

        self.assertTrue(isinstance(test.part.joints["test"], RevoluteJoint))

    def test_no_to_part(self):
        with self.assertRaises(ValueError):
            RevoluteJoint("test")


class TestLinearJoint(DirectApiTestCase):
    def test_linear_rigid_joint(self):
        base = Solid.make_box(1, 1, 1)
        j1 = LinearJoint(
            "top", to_part=base, axis=Axis((0, 0.5, 1), (1, 0, 0)), linear_range=(0, 1)
        )
        fixed_top = Solid.make_box(1, 1, 1)
        j2 = RigidJoint("bottom", fixed_top, Location((0.5, 0.5, 0)))
        j1.connect_to(j2, position=0.25)
        bbox = fixed_top.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (-0.25, 0, 1), 5)
        self.assertVectorAlmostEquals(bbox.max, (0.75, 1, 2), 5)

        self.assertVectorAlmostEquals(j2.symbol.location.position, (0.25, 0.5, 1), 6)
        self.assertVectorAlmostEquals(j2.symbol.location.orientation, (0, 0, 0), 6)

    def test_linear_revolute_joint(self):
        linear_base = Solid.make_box(1, 1, 1)
        j1 = LinearJoint(
            label="top",
            to_part=linear_base,
            axis=Axis((0, 0.5, 1), (1, 0, 0)),
            linear_range=(0, 1),
        )
        revolute_top = Solid.make_box(1, 0.5, 1).locate(Location((-0.5, -0.25, 0)))
        j2 = RevoluteJoint(
            label="top",
            to_part=revolute_top,
            axis=Axis((0, 0, 0), (0, 0, 1)),
            angle_reference=(1, 0, 0),
            angular_range=(0, 180),
        )
        j1.connect_to(j2, position=0.25, angle=90)

        bbox = revolute_top.bounding_box()
        self.assertVectorAlmostEquals(bbox.min, (0, 0, 1), 5)
        self.assertVectorAlmostEquals(bbox.max, (0.5, 1, 2), 5)

        self.assertVectorAlmostEquals(j2.symbol.location.position, (0.25, 0.5, 1), 6)
        self.assertVectorAlmostEquals(j2.symbol.location.orientation, (0, 0, 90), 6)
        self.assertEqual(len(j1.symbol.edges()), 2)

        # Test invalid position
        with self.assertRaises(ValueError):
            j1.connect_to(j2, position=5, angle=90)

        # Test invalid angle
        with self.assertRaises(ValueError):
            j1.connect_to(j2, position=0.5, angle=270)

        # Test invalid joint
        with self.assertRaises(TypeError):
            j1.connect_to(Solid.make_box(1, 1, 1), position=0.5, angle=90)

    def test_builder(self):
        with BuildPart() as test:
            Box(3, 3, 1)
            LinearJoint("test")
            Cylinder(1, 3)

        self.assertTrue(isinstance(test.part.joints["test"], LinearJoint))

    def test_no_to_part(self):
        with self.assertRaises(ValueError):
            LinearJoint("test")

    def test_error_handling(self):
        j1 = LinearJoint("one", Box(1, 1, 1))
        with self.assertRaises(TypeError):
            j1.connect_to(Solid.make_box(1, 1, 1))

        with self.assertRaises(TypeError):
            j1.relative_to(Solid.make_box(1, 1, 1))


class TestCylindricalJoint(DirectApiTestCase):
    def test_cylindrical_joint(self):
        cylindrical_base = (
            Solid.make_box(1, 1, 1)
            .locate(Location((-0.5, -0.5, 0)))
            .cut(Solid.make_cylinder(0.3, 1))
        )
        j1 = CylindricalJoint(
            "base",
            cylindrical_base,
            Axis((0, 0, 1), (0, 0, -1)),
            angle_reference=(1, 0, 0),
            linear_range=(0, 1),
            angular_range=(0, 90),
        )
        dowel = Solid.make_cylinder(0.3, 1).cut(
            Solid.make_box(1, 1, 1).locate(Location((-0.5, 0, 0)))
        )
        j2 = RigidJoint("bottom", dowel, Location((0, 0, 0), (0, 0, 0)))
        j1.connect_to(j2, position=0.25, angle=90)
        dowel_bbox = dowel.bounding_box()
        self.assertVectorAlmostEquals(dowel_bbox.min, (0, -0.3, -0.25), 5)
        self.assertVectorAlmostEquals(dowel_bbox.max, (0.3, 0.3, 0.75), 5)

        self.assertVectorAlmostEquals(j1.symbol.location.position, (0, 0, 1), 6)
        self.assertVectorAlmostEquals(
            j1.symbol.location.orientation, (-180, 0, -180), 6
        )
        self.assertEqual(len(j1.symbol.edges()), 3)

        # Test invalid position
        with self.assertRaises(ValueError):
            j1.connect_to(j2, position=5, angle=90)

        # Test invalid angle
        with self.assertRaises(ValueError):
            j1.connect_to(j2, position=0.5, angle=270)

        # Test invalid joint
        with self.assertRaises(TypeError):
            j1.connect_to(Solid.make_box(1, 1, 1), position=0.5, angle=90)

    def test_cylindrical_joint_error_bad_angle_reference(self):
        """Test that the angle_reference must be normal to the axis"""
        with self.assertRaises(ValueError):
            CylindricalJoint(
                "base",
                Solid.make_box(1, 1, 1),
                Axis((0, 0, 1), (0, 0, -1)),
                angle_reference=(1, 0, 1),
                linear_range=(0, 1),
                angular_range=(0, 90),
            )

    def test_cylindrical_joint_error_bad_position_and_angle(self):
        """Test that the joint angle is within bounds"""

        j1 = CylindricalJoint(
            "base",
            Solid.make_box(1, 1, 1),
            Axis((0, 0, 1), (0, 0, -1)),
            linear_range=(0, 1),
            angular_range=(0, 90),
        )
        j2 = RigidJoint("bottom", Solid.make_cylinder(1, 1), Location((0.5, 0.25, 0)))
        with self.assertRaises(ValueError):
            j1.connect_to(j2, position=0.5, angle=270)

        with self.assertRaises(ValueError):
            j1.connect_to(j2, position=4, angle=30)

    def test_builder(self):
        with BuildPart() as test:
            Box(3, 3, 1)
            CylindricalJoint("test")
            Cylinder(1, 3)

        self.assertTrue(isinstance(test.part.joints["test"], CylindricalJoint))

    def test_no_to_part(self):
        with self.assertRaises(ValueError):
            CylindricalJoint("test")

    def test_error_handling(self):
        j1 = CylindricalJoint("one", Box(1, 1, 1))
        with self.assertRaises(TypeError):
            j1.connect_to(Solid.make_box(1, 1, 1))

        with self.assertRaises(TypeError):
            j1.relative_to(Solid.make_box(1, 1, 1))


class TestBallJoint(DirectApiTestCase):
    def test_ball_joint(self):
        socket_base = Solid.make_box(1, 1, 1).cut(
            Solid.make_sphere(0.3, Plane((0.5, 0.5, 1)))
        )
        j1 = BallJoint(
            "socket",
            socket_base,
            Location((0.5, 0.5, 1)),
            angular_range=((-45, 45), (-45, 45), (0, 360)),
        )
        ball_rod = Solid.make_cylinder(0.15, 2).fuse(
            Solid.make_sphere(0.3).locate(Location((0, 0, 2)))
        )
        j2 = RigidJoint("ball", ball_rod, Location((0, 0, 2), (180, 0, 0)))
        j1.connect_to(j2, angles=(45, 45, 0))
        self.assertVectorAlmostEquals(
            ball_rod.faces().filter_by(GeomType.PLANE)[0].center(CenterOf.GEOMETRY),
            (1.914213562373095, -0.5, 2),
            5,
        )

        self.assertVectorAlmostEquals(j1.symbol.location.position, (0.5, 0.5, 1), 6)
        self.assertVectorAlmostEquals(j1.symbol.location.orientation, (0, 0, 0), 6)

        with self.assertRaises(ValueError):
            j1.connect_to(j2, angles=(90, 45, 0))

        # Test invalid joint
        with self.assertRaises(TypeError):
            j1.connect_to(Solid.make_box(1, 1, 1), angles=(0, 0, 0))

    def test_builder(self):
        with BuildPart() as test:
            Box(3, 3, 1)
            BallJoint("test")
            Cylinder(1, 3)

        self.assertTrue(isinstance(test.part.joints["test"], BallJoint))

    def test_no_to_part(self):
        with self.assertRaises(ValueError):
            BallJoint("test")

    def test_error_handling(self):
        j1 = BallJoint("one", Box(1, 1, 1))
        with self.assertRaises(TypeError):
            j1.connect_to(Solid.make_box(1, 1, 1))

        with self.assertRaises(TypeError):
            j1.relative_to(Solid.make_box(1, 1, 1))


class TestJointOrder(DirectApiTestCase):
    def test_rigid_rigid(self):
        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = RigidJoint("two", Sphere(0.5))
        j1.connect_to(j2)
        self.assertVectorAlmostEquals(j1.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j2.parent.location.position, (1, 2, 3), 5)

        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = RigidJoint("two", Sphere(0.5))
        j2.connect_to(j1)
        self.assertVectorAlmostEquals(j2.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j1.parent.location.position, (-1, -2, -3), 5)

    def test_rigid_ball(self):
        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = BallJoint("two", Sphere(0.5))
        j1.connect_to(j2, angles=(0, 0, 0))
        self.assertVectorAlmostEquals(j1.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j2.parent.location.position, (1, 2, 3), 5)

        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = BallJoint("two", Sphere(0.5))
        j2.connect_to(j1, angles=(0, 0, 0))
        self.assertVectorAlmostEquals(j2.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j1.parent.location.position, (-1, -2, -3), 5)

    def test_rigid_cylindrical(self):
        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = CylindricalJoint("two", Sphere(0.5))
        j1.connect_to(j2, position=0, angle=0)
        self.assertVectorAlmostEquals(j1.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j2.parent.location.position, (1, 2, 3), 5)

        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = CylindricalJoint("two", Sphere(0.5))
        j2.connect_to(j1, position=0, angle=0)
        self.assertVectorAlmostEquals(j2.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j1.parent.location.position, (-1, -2, -3), 5)

    def test_rigid_linear(self):
        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = LinearJoint("two", Sphere(0.5))
        j1.connect_to(j2, position=0)
        self.assertVectorAlmostEquals(j1.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j2.parent.location.position, (1, 2, 3), 5)

        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = LinearJoint("two", Sphere(0.5))
        j2.connect_to(j1, position=0)
        self.assertVectorAlmostEquals(j2.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j1.parent.location.position, (-1, -2, -3), 5)

    def test_rigid_revolute(self):
        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = RevoluteJoint("two", Sphere(0.5))
        j1.connect_to(j2, angle=0)
        self.assertVectorAlmostEquals(j1.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j2.parent.location.position, (1, 2, 3), 5)

        j1 = RigidJoint("one", Box(1, 1, 1), joint_location=Location((1, 2, 3)))
        j2 = RevoluteJoint("two", Sphere(0.5))
        j2.connect_to(j1, angle=0)
        self.assertVectorAlmostEquals(j2.parent.location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(j1.parent.location.position, (-1, -2, -3), 5)


class TestJointCopy(DirectApiTestCase):
    def test_deepcopy(self):
        with BuildPart() as test:
            Box(3, 3, 1)
            RigidJoint("test")

        test_copy = copy.deepcopy(test.part, None)
        self.assertEqual(test_copy.joints["test"].parent, test_copy)


class TestJointPropagation(DirectApiTestCase):
    def test_algebra_mode(self):
        b = Box(2, 2, 2)
        RigidJoint("top", b, b.faces().sort_by(Axis.Z)[-1].location_at(0.5, 0.5))
        c = b - Cylinder(0.5, 2)
        self.assertVectorAlmostEquals(c.joints["top"].location.position, (0, 0, 1), 5)

    def test_builder_mode(self):
        with BuildPart() as base_builder:
            Box(6, 6, 6)
            top_face = base_builder.faces().sort_by(Axis.Z)[-1]
            RigidJoint("top", joint_location=top_face.location_at(0.5, 0.5))
            with BuildSketch(base_builder.faces()):
                Circle(2)
            extrude(amount=-1, mode=Mode.SUBTRACT)
        base = base_builder.part
        self.assertVectorAlmostEquals(
            base.joints["top"].location.position, (0, 0, 3), 5
        )


if __name__ == "__main__":
    unittest.main()
