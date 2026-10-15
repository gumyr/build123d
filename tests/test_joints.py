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

import pickle

from build123d.build_enums import Align, CenterOf, GeomType, Keep
from build123d.build_common import GridLocations, Locations, Mode, PolarLocations
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
from build123d.operations_generic import chamfer, fillet, mirror, offset, scale, split
from build123d.operations_part import draft, extrude
from build123d.topology import Compound, Edge, JointDict, Solid


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
        # a joint with no part and no builder is free
        self.assertIsNone(RigidJoint("test").parent)

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

    def test_revolute_joint_uses_angle_reference_when_connecting_to_rigid(self):
        p1 = Box(1, 1, 1)
        j1 = RevoluteJoint("j1", p1, Axis.Z, angle_reference=(1, 1, 0))
        p2 = Box(0.2, 0.2, 2)
        j2 = RigidJoint("j2", p2, Location())

        j1.connect_to(j2, angle=22.5)

        self.assertVectorAlmostEquals(p2.location.orientation, (0, 0, 67.5), 6)

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
        self.assertIsNone(RevoluteJoint("test").parent)


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
        self.assertIsNone(LinearJoint("test").parent)

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
        self.assertIsNone(CylindricalJoint("test").parent)

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
        self.assertIsNone(BallJoint("test").parent)

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

    def test_copy_keeps_the_connection_by_reference(self):
        # Copying a connected part must not copy the part it is connected to
        base = Box(10, 10, 2)
        arm = Box(2, 2, 10)
        RigidJoint("top", base, Location((0, 0, 1)))
        RigidJoint("bottom", arm, Location((0, 0, -5)))
        base.joints["top"].connect_to(arm.joints["bottom"])

        for name, base_copy in (
            ("deepcopy", copy.deepcopy(base)),
            ("moved", base.moved(Location((100, 0, 0)))),
            ("cut", base - Cylinder(0.5, 2)),
        ):
            with self.subTest(copy=name):
                joint = base_copy.joints["top"]
                self.assertIs(joint.parent, base_copy)
                self.assertIs(joint.connected_to, arm.joints["bottom"])
                self.assertIs(joint.connected_to.parent, arm)
                self.assertIsNot(
                    joint.relative_location, base.joints["top"].relative_location
                )


class TestJointPropagation(DirectApiTestCase):
    def test_algebra_mode(self):
        b = Box(2, 2, 2)
        RigidJoint("top", b, b.faces().sort_by(Axis.Z)[-1].location_at(0.5, 0.5))
        c = b - Cylinder(0.5, 2)
        self.assertVectorAlmostEquals(c.joints["top"].location.position, (0, 0, 1), 5)

    def test_located_part_keeps_joint_positions_through_booleans(self):
        # a boolean result sits at the identity; joints stay where they were
        part = Box(10, 10, 2).moved(Location((20, 0, 0)))
        RigidJoint("top", part, Location((22, 3, 1), (0, 30, 0)))
        tool = Cylinder(1, 5).moved(Location((20, 0, 0)))
        for name, result in (("cut", part - tool), ("fuse", part + tool)):
            with self.subTest(op=name):
                self.assertVectorAlmostEquals(result.location.position, (0, 0, 0), 5)
                self.assertVectorAlmostEquals(
                    result.joints["top"].location.position, (22, 3, 1), 5
                )
                self.assertVectorAlmostEquals(
                    result.joints["top"].location.orientation, (0, 30, 0), 5
                )

    def test_algebra_fuse_keeps_joints(self):
        # The left operand's joints survive a fuse whether the pieces overlap,
        # touch or are apart
        b = Box(2, 2, 2)
        RigidJoint("top", b, Location((0, 0, 1)))
        for name, other in (
            ("overlapping", Box(1, 1, 3)),
            ("touching", Box(1, 1, 1).moved(Location((0, 0, 1.5)))),
            ("apart", Box(1, 1, 1).moved(Location((50, 0, 0)))),
        ):
            with self.subTest(other=name):
                fused = b + other
                self.assertVectorAlmostEquals(
                    fused.joints["top"].location.position, (0, 0, 1), 5
                )
                self.assertIs(fused.joints["top"].parent, fused)

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


class TestJointPlacement(DirectApiTestCase):
    """Issue #1514: a joint made in a builder is placed with the part."""

    def test_builder_location_is_deprecated(self):
        with BuildPart() as builder:
            Box(1, 1, 1)
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(builder.location, Location())

    def test_builder_joints_can_be_assigned(self):
        # free joints made outside the builder; inside, a constructor binds
        free_a = RigidJoint(joint_location=Location((0, 0, 1)))
        free_b = RigidJoint(joint_location=Location((0, 0, -1)))
        with BuildPart() as builder:
            Box(2, 2, 2)
            builder.joints = {"a": free_a}
            self.assertIs(builder.joints["a"].parent, builder)
        self.assertIs(builder.part.joints["a"].parent, builder.part)
        builder.joints = {"b": free_b}
        self.assertEqual(list(builder.part.joints), ["b"])
        self.assertIs(builder.part.joints["b"].parent, builder.part)

    def test_builder_joints_are_the_placed_parts_joints(self):
        # While open, the builder's joints are the ones being defined; once it
        # has exited they are the placed part's, so both routes to a joint
        # give the same object in the frame the part is in
        plane = Plane.XZ.offset(10)
        with BuildPart(plane) as builder:
            Box(6, 6, 6)
            RigidJoint("top", joint_location=Location((0, 0, 3)))
            self.assertIs(builder.joints["top"].parent, builder)
        self.assertIs(builder.joints["top"], builder.part.joints["top"])
        self.assertIs(builder.joints["top"].parent, builder.part)
        self.assertVectorAlmostEquals(
            builder.joints["top"].location.position, (0, -13, 0), 5
        )

        peg = Box(1, 1, 2)
        RigidJoint("base", peg, Location((0, 0, -1)))
        builder.joints["top"].connect_to(peg.joints["base"])
        self.assertVectorAlmostEquals(peg.center(), (0, -14, 0), 5)

    def test_rigid_joint_follows_the_workplane(self):
        plane = Plane.XZ.offset(10)
        with BuildPart(plane) as builder:
            Box(6, 6, 6)
            top = builder.faces().sort_by(Axis.Z)[-1]
            RigidJoint("top", joint_location=top.location_at(0.5, 0.5))
        part = builder.part
        joint = part.joints["top"]
        expected = plane.location * Location((0, 0, 3))
        self.assertVectorAlmostEquals(joint.location.position, expected.position, 5)
        self.assertVectorAlmostEquals(
            joint.location.orientation, expected.orientation, 5
        )
        # the joint sits on the face it was made from, on the placed part: the
        # local top face, which Plane.XZ sends to the smallest world Y
        face = part.faces().sort_by(Axis.Y)[0]
        self.assertVectorAlmostEquals(joint.location.position, face.center(), 5)
        # and a part connected to it lands on that face
        peg = Box(1, 1, 2)
        RigidJoint("base", peg, Location((0, 0, -1)))
        joint.connect_to(peg.joints["base"])
        self.assertTrue(
            any((f.center() - face.center()).length < 1e-5 for f in peg.faces())
        )

    def test_revolute_joint_follows_the_workplane(self):
        plane = Plane.XZ.offset(10)
        axis = Axis((0, 0, 3), (1, 0, 0))
        with BuildPart(plane) as builder:
            Box(6, 6, 6)
            RevoluteJoint("hinge", axis=axis)
        joint = builder.part.joints["hinge"]
        expected = plane.location * axis.location
        self.assertVectorAlmostEquals(joint.location.position, expected.position, 5)
        self.assertVectorAlmostEquals(
            joint.location.orientation, expected.orientation, 5
        )

    def test_joint_follows_a_locations_context(self):
        with BuildPart():
            with Locations((20, 0, 0)):
                with BuildPart() as inner:
                    Box(2, 2, 2)
                    RigidJoint("j", joint_location=Location((0, 0, 1)))
        self.assertVectorAlmostEquals(
            inner.part.joints["j"].location.position, (20, 0, 1), 5
        )


class TestFreeJoints(DirectApiTestCase):
    """Joints made without a part, placed with * and bound by assignment or +."""

    def test_free_joint_has_its_own_location(self):
        free = RigidJoint(joint_location=Location((5, 0, 1)))
        self.assertIsNone(free.parent)
        self.assertEqual(free.label, "")
        self.assertVectorAlmostEquals(free.location.position, (5, 0, 1), 5)
        self.assertGreater(free.symbol.bounding_box().diagonal, 0)
        with self.assertRaisesRegex(ValueError, "free joint cannot be connected"):
            free.connect_to(RigidJoint(joint_location=Location()))

    def test_assignment_binds_a_joint_where_it_is(self):
        part = Box(2, 2, 2).moved(Location((5, 0, 0)))
        free = RigidJoint(joint_location=Location((5, 0, 1)))
        part.joints["lid"] = free
        self.assertIs(part.joints["lid"], free)
        self.assertEqual(free.label, "lid")
        self.assertIs(free.parent, part)
        self.assertVectorAlmostEquals(free.location.position, (5, 0, 1), 5)
        self.assertVectorAlmostEquals(free.relative_location.position, (0, 0, 1), 5)

        # a joint moves across from another part without moving in the world
        other = Box(2, 2, 2)
        other.joints["lid"] = free
        self.assertNotIn("lid", part.joints)
        self.assertIs(other.joints["lid"].parent, other)
        self.assertVectorAlmostEquals(free.location.position, (5, 0, 1), 5)

        del other.joints["lid"]
        self.assertIsNone(free.parent)
        self.assertVectorAlmostEquals(free.location.position, (5, 0, 1), 5)
        with self.assertRaises(TypeError):
            part.joints["bad"] = "not a joint"

    def test_joints_dict_methods_attach_and_free(self):
        part = Box(2, 2, 2)
        a, b = RigidJoint(), RigidJoint(joint_location=Location((0, 0, 1)))
        part.joints.update({"a": a}, b=b)
        self.assertEqual(sorted(part.joints), ["a", "b"])
        self.assertTrue(all(j.parent is part for j in (a, b)))
        self.assertIs(part.joints.setdefault("a", RigidJoint()), a)
        self.assertIs(part.joints.setdefault("d", RigidJoint()).parent, part)
        with self.assertRaises(TypeError):
            part.joints.setdefault("e")
        self.assertIs(part.joints.pop("a"), a)
        self.assertIsNone(a.parent)
        self.assertIsNone(part.joints.pop("a", None))
        with self.assertRaises(KeyError):
            part.joints.pop("a")
        label, popped = part.joints.popitem()
        self.assertEqual(label, "d")
        self.assertIsNone(popped.parent)
        part.joints |= {"c": RigidJoint()}
        part.joints.clear()
        self.assertIsNone(b.parent)
        self.assertEqual(part.joints, {})

    def test_plain_dict_joints_are_adopted_on_copy(self):
        # a part unpickled from an earlier version holds its joints in a dict
        part = Box(2, 2, 2)
        RigidJoint("top", part, Location((0, 0, 1)))
        object.__setattr__(part, "joints", dict(part.joints))
        copied = copy.deepcopy(part)
        self.assertIsInstance(copied.joints, JointDict)
        self.assertIs(copied.joints["top"].parent, copied)

    def test_multiplying_a_free_joint_places_copies(self):
        joint = RigidJoint("mount", joint_location=Location((0, 0, 1)))
        one = Location((1, 2, 3)) * joint
        self.assertIsNot(one, joint)
        self.assertEqual(one.label, "mount")
        self.assertVectorAlmostEquals(one.location.position, (1, 2, 4), 5)

        grid = GridLocations(60, 60, 2, 2) * joint
        self.assertEqual(
            [j.label for j in grid], ["mount0", "mount1", "mount2", "mount3"]
        )
        self.assertVectorAlmostEquals(grid[0].location.position, (-30, -30, 1), 5)
        self.assertVectorAlmostEquals(
            (Plane.XZ * RevoluteJoint(axis=Axis.Z)).relative_axis.direction,
            (0, -1, 0),
            5,
        )

        bound = Box(1, 1, 1)
        RigidJoint("top", bound, Location((0, 0, 0.5)))
        with self.assertRaisesRegex(ValueError, "bound to a part"):
            Location((1, 0, 0)) * bound.joints["top"]

    def test_adding_joints_binds_copies_to_the_result(self):
        plate = Box(100, 100, 10)
        top = plate.faces().sort_by(Axis.Z)[-1]
        mounts = Plane(top) * GridLocations(60, 60, 2, 2) * RigidJoint("mount")
        plated = plate + mounts
        self.assertEqual(
            sorted(plated.joints), ["mount0", "mount1", "mount2", "mount3"]
        )
        self.assertVectorAlmostEquals(
            plated.joints["mount0"].location.position, (-30, -30, 5), 5
        )
        self.assertTrue(all(j.parent is plated for j in plated.joints.values()))
        self.assertEqual(plate.joints, {})  # the operand is untouched
        self.assertIsNone(mounts[0].parent)

        mixed = plated + [Box(5, 5, 5).moved(Location((0, 0, 10))), RigidJoint("extra")]
        self.assertEqual(len(mixed.joints), 5)
        self.assertAlmostEqual(mixed.volume, 100 * 100 * 10 + 125, 5)
        solid = Solid.make_box(1, 1, 1) + RigidJoint("s", joint_location=Location())
        self.assertIsInstance(solid, Solid)
        self.assertIn("s", solid.joints)
        with self.assertRaisesRegex(ValueError, "needs a label"):
            plate + RigidJoint()
        # a 1D Compound sums to a Wire, which cannot hold joints
        with self.assertRaisesRegex(TypeError, "Wire"):
            Compound([Edge.make_line((0, 0, 0), (1, 0, 0))]) + [
                Edge.make_line((1, 0, 0), (1, 1, 0)),
                RigidJoint("x"),
            ]

    def test_copies_keep_the_joints_dict(self):
        plate = Box(10, 10, 2) + RigidJoint("top", joint_location=Location((0, 0, 1)))
        for name, copied in (
            ("deepcopy", copy.deepcopy(plate)),
            ("moved", plate.moved(Location((0, 0, 50)))),
            ("pickle", pickle.loads(pickle.dumps(plate))),
        ):
            with self.subTest(copy=name):
                self.assertIsInstance(copied.joints, JointDict)
                self.assertIs(copied.joints.owner, copied)
                self.assertIs(copied.joints["top"].parent, copied)
        self.assertVectorAlmostEquals(
            plate.moved(Location((0, 0, 50))).joints["top"].location.position,
            (0, 0, 51),
            5,
        )


class TestJointsInLocations(DirectApiTestCase):
    """A joint constructor inside a Locations context makes one joint per location."""

    def test_builder_grid_of_joints(self):
        with BuildPart() as builder:
            Box(100, 100, 10)
            with Locations(builder.faces().sort_by(Axis.Z)[-1]):
                with GridLocations(60, 60, 2, 2):
                    RigidJoint("mount")
        part = builder.part
        self.assertEqual(sorted(part.joints), ["mount0", "mount1", "mount2", "mount3"])
        self.assertVectorAlmostEquals(
            part.joints["mount0"].location.position, (-30, -30, 5), 5
        )
        self.assertTrue(all(j.parent is part for j in part.joints.values()))

    def test_polar_locations_rotate_the_axis(self):
        with BuildPart() as builder:
            Box(10, 10, 2)
            with PolarLocations(4, 3):
                RevoluteJoint("hinge", axis=Axis.X)
        directions = [
            builder.part.joints[f"hinge{i}"].relative_axis.direction for i in range(3)
        ]
        self.assertVectorAlmostEquals(directions[0], (1, 0, 0), 5)
        self.assertVectorAlmostEquals(directions[1], (-0.5, 0.866025, 0), 5)
        self.assertVectorAlmostEquals(directions[2], (-0.5, -0.866025, 0), 5)

    def test_label_sequence(self):
        with BuildPart() as builder:
            Box(10, 10, 2)
            with GridLocations(4, 0, 2, 1):
                RigidJoint(["left", "right"], joint_location=Location((0, 0, 1)))
            with self.assertRaisesRegex(ValueError, "3 labels .* 2 locations"):
                with GridLocations(4, 0, 2, 1):
                    RigidJoint(["a", "b", "c"])
            with self.assertRaisesRegex(ValueError, "needs a label"):
                RigidJoint()
        self.assertEqual(sorted(builder.part.joints), ["left", "right"])
        self.assertVectorAlmostEquals(
            builder.part.joints["left"].location.position, (-2, 0, 1), 5
        )

    def test_algebra_constructor_in_locations(self):
        part = Box(10, 10, 2)
        with GridLocations(4, 0, 2, 1):
            RigidJoint("p", part, Location((0, 0, 1)))
        self.assertEqual(sorted(part.joints), ["p0", "p1"])
        self.assertVectorAlmostEquals(part.joints["p1"].location.position, (2, 0, 1), 5)
        with self.assertRaisesRegex(ValueError, "single label"):
            RigidJoint(["a", "b"])


class TestJointTransforms(DirectApiTestCase):
    """Joints follow their part through the transforms baked into its geometry."""

    def jointed_part(self):
        part = Box(10, 10, 2).moved(Location((20, 0, 0)))
        RigidJoint("top", part, Location((22, 3, 1), (0, 30, 0)))
        RevoluteJoint(
            "hinge", part, axis=Axis((25, 0, 1), (1, 0, 0)), angle_reference=(0, 1, 0)
        )
        BallJoint("ball", part, Location((18, 0, 1)), angle_reference=Plane.XZ)
        CylindricalJoint(
            "screw", part, axis=Axis((20, -3, 1), (0, 0, 1)), angle_reference=(1, 0, 0)
        )
        return part

    def test_mirror_method(self):
        part = self.jointed_part()
        mirrored = part.mirror(Plane.YZ)
        self.assertAlmostEqual(mirrored.center().X, -20, 5)
        top = mirrored.joints["top"]
        self.assertIs(top.parent, mirrored)
        self.assertEqual(top.location, part.joints["top"].location.mirror(Plane.YZ))
        hinge = mirrored.joints["hinge"]
        self.assertVectorAlmostEquals(hinge.location.position, (-25, 0, 1), 5)
        self.assertVectorAlmostEquals(hinge.relative_axis.direction, (-1, 0, 0), 5)
        self.assertVectorAlmostEquals(hinge.angle_reference, (0, 1, 0), 5)
        self.assertVectorAlmostEquals(
            mirrored.joints["ball"].angle_reference.z_dir, (0, -1, 0), 5
        )
        screw = mirrored.joints["screw"]
        self.assertVectorAlmostEquals(screw.location.position, (-20, -3, 1), 5)
        self.assertVectorAlmostEquals(screw.angle_reference, (-1, 0, 0), 5)
        # the original is untouched
        self.assertVectorAlmostEquals(
            part.joints["top"].location.position, (22, 3, 1), 5
        )

    def test_mirror_operation(self):
        part = self.jointed_part()
        mirrored = mirror(part, Plane.YZ)
        self.assertEqual(sorted(mirrored.joints), ["ball", "hinge", "screw", "top"])
        self.assertVectorAlmostEquals(
            mirrored.joints["top"].location.position, (-22, 3, 1), 5
        )
        self.assertIs(mirrored.joints["top"].parent, mirrored)

        # a builder's joints are left alone by mirror (Mode.ADD would collide)
        with BuildPart() as builder:
            Box(10, 10, 2)
            RigidJoint("left", joint_location=Location((-3, 0, 1)))
            mirror(about=Plane.YZ)
        self.assertEqual(list(builder.part.joints), ["left"])

    def test_scale_and_transformed_rotation(self):
        # scale is about the part's location, (20, 0, 0)
        part = self.jointed_part()
        scaled = part.scale(2)
        self.assertVectorAlmostEquals(
            scaled.joints["top"].location.position, (24, 6, 2), 5
        )
        self.assertVectorAlmostEquals(
            scaled.joints["top"].location.orientation, (0, 30, 0), 5
        )
        self.assertVectorAlmostEquals(
            scaled.joints["hinge"].location.position, (30, 0, 2), 5
        )

        # regenerating the geometry gives the same joints as moving it
        moved = part.rotate(Axis.Z, 90)
        regenerated = part.rotate(Axis.Z, 90, transform=True)
        for label in ("top", "ball"):
            self.assertEqual(
                moved.joints[label].location, regenerated.joints[label].location
            )
        self.assertVectorAlmostEquals(
            regenerated.joints["hinge"].location.position,
            moved.joints["hinge"].location.position,
            5,
        )
        self.assertVectorAlmostEquals(
            Plane(regenerated.joints["hinge"].location).z_dir,
            Plane(moved.joints["hinge"].location).z_dir,
            5,
        )


class TestJointOperations(DirectApiTestCase):
    """Algebra-mode operations that rebuild a part keep its joints, label and color."""

    def jointed(self, as_solid: bool = False):
        part = Solid.make_box(10, 10, 4) if as_solid else Box(10, 10, 4)
        part = part.moved(Location((20, 0, 0)))
        part.label = "body"
        RigidJoint("top", part, Location((22, 3, 4), (0, 30, 0)))
        return part

    def check(self, result, where=(22, 3, 4)):
        if isinstance(result, (list, tuple)):
            result = result[0]
        self.assertEqual(result.label, "body")
        self.assertIs(result.joints["top"].parent, result)
        self.assertVectorAlmostEquals(result.joints["top"].location.position, where, 5)
        self.assertVectorAlmostEquals(
            result.joints["top"].location.orientation, (0, 30, 0), 5
        )

    def test_operations(self):
        cases = {
            "fillet": lambda p: fillet(p.edges().filter_by(Axis.Z), 1),
            "chamfer": lambda p: chamfer(p.edges().filter_by(Axis.Z), 1),
            "offset": lambda p: offset(p, 1),
            "offset opening": lambda p: offset(
                p, -1, openings=p.faces().sort_by(Axis.Z)[-1]
            ),
            "split": lambda p: split(p, Plane.XY),
            "split both": lambda p: split(p, Plane.XY, keep=Keep.BOTH),
            "draft": lambda p: draft(
                p.faces().filter_by(Axis.Z, reverse=True), Plane.XY, 5
            ),
        }
        for name, operation in cases.items():
            for as_solid in (False, True):
                with self.subTest(operation=name, solid=as_solid):
                    self.check(operation(self.jointed(as_solid)))

    def test_scale_operation(self):
        # scale is about the part's location, so the joint scales with the part
        self.check(scale(self.jointed(), 2), (24, 6, 8))

    def test_methods(self):
        cases = {
            "fillet": lambda p: p.fillet(1, p.edges().filter_by(Axis.Z)),
            "chamfer": lambda p: p.chamfer(1, None, p.edges().filter_by(Axis.Z)),
            "offset_3d": lambda p: p.offset_3d(None, 1),
            "hollow": lambda p: p.hollow([p.faces().sort_by(Axis.Z)[-1]], 1),
            "split": lambda p: p.split(Plane.XY),
            "split both": lambda p: p.split(Plane.XY, keep=Keep.BOTH),
            "split all": lambda p: p.split(Plane.XY, keep=Keep.ALL),
            "intersect": lambda p: p & Box(8, 8, 8).moved(Location((20, 0, 0))),
        }
        for name, method in cases.items():
            with self.subTest(method=name):
                self.check(method(self.jointed(as_solid=True)))
        solid = self.jointed(as_solid=True)
        self.check(
            solid.draft(solid.faces().filter_by(Axis.Z, reverse=True), Plane.XY, 5)
        )


class TestJointValidation(DirectApiTestCase):
    """Guards on the joint classes."""

    def test_ball_joint_angle_types(self):
        ball = BallJoint("ball", Solid.make_box(1, 1, 1), Location())
        rigid = RigidJoint("rigid", Solid.make_box(1, 1, 1), Location())
        for angles in (Rotation(0, 0, 0), (0, 0, 0), None):
            with self.subTest(angles=angles):
                self.assertEqual(ball.relative_to(rigid, angles=angles), Location())

    def test_ball_joint_invalid_angles(self):
        ball = BallJoint("ball", Solid.make_box(1, 1, 1), Location())
        rigid = RigidJoint("rigid", Solid.make_box(1, 1, 1), Location())
        with self.assertRaisesRegex(TypeError, "angles is of an unknown type"):
            ball.relative_to(rigid, angles="bogus")


if __name__ == "__main__":
    unittest.main()
