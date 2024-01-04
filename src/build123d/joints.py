"""
build123d joints

name: joints.py
by:   Gumyr
date: August 24, 2023

desc:
    This python module contains all of the Joint derived classes.

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
from __future__ import annotations

from math import inf
from typing import Union, overload

from build123d.build_common import validate_inputs
from build123d.build_enums import Align
from build123d.build_part import BuildPart
from build123d.geometry import (
    Axis,
    Location,
    Plane,
    Rotation,
    RotationLike,
    Vector,
    VectorLike,
)
from build123d.topology import Compound, Edge, Joint, Solid


def check_angle(angle: float, angular_range: tuple[float, float]):
    """Check that a value is within an angular range
    Args:
        angle (float): value to check
        angular_range (tuple[float, float]): range to check
    """
    if angle is not None and not angular_range[0] <= angle <= angular_range[1]:
        raise ValueError(f"angle == {angle}, but must be in range {angular_range}")


def check_position(position: float, linear_range: tuple[float, float]):
    """Check that a position is within a linear range
    Args:
        position (float): value to check
        linear_range (tuple[float, float]): range to check
    """
    if position is not None and not linear_range[0] <= position <= linear_range[1]:
        raise ValueError(f"position == {position}, but must be in range {linear_range}")


class RigidJoint(Joint):
    """RigidJoint

    A rigid joint fixes two components to one another.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound], optional): object to attach joint to
        joint_location (Location): global location of joint

    Attributes:
        relative_location (Location): joint location relative to bound object

    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol (XYZ indicator) as bound to part"""
        size = self.parent.bounding_box().diagonal / 12
        return Compound.make_triad(axes_scale=size).locate(self.location)

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound] = None,
        joint_location: Location = Location(),
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self)
        if to_part is None:
            if context is not None:
                to_part = context
            else:
                raise ValueError("Either specify to_part or place in BuildPart scope")

        to_part.joints[label] = self
        super().__init__(label, to_part)

        # to be assigned after super().__init__
        self.relative_location = to_part.location.inverse() * joint_location

    @overload
    def connect_to(self, other: BallJoint, *, angles: RotationLike = None, **kwargs):
        """Connect RigidJoint and BallJoint"""

    @overload
    def connect_to(
        self, other: CylindricalJoint, *, position: float = None, angle: float = None
    ):
        """Connect RigidJoint and CylindricalJoint"""

    @overload
    def connect_to(self, other: LinearJoint, *, position: float = None):
        """Connect RigidJoint and LinearJoint"""

    @overload
    def connect_to(self, other: RevoluteJoint, *, angle: float = None):
        """Connect RigidJoint and RevoluteJoint"""

    @overload
    def connect_to(self, other: RigidJoint):
        """Connect two RigidJoints together"""

    def connect_to(self, other: Joint, **kwargs):
        """Connect the RigidJoint to another Joint

        Args:
            other (Joint): joint to connect to
            angle (float, optional): angle in degrees. Defaults to range min.
            angles (RotationLike, optional): angles about axes in degrees. Defaults to
                range minimums.
            position (float, optional): linear position. Defaults to linear range min.

        """
        self.check_compatibility(other)

        if isinstance(other, BallJoint) and kwargs.get("angles") is not None:
            for angle, angular_range in zip(kwargs.get("angles"), other.angular_range):
                check_angle(angle, angular_range)
        else:
            if isinstance(other, (RevoluteJoint, CylindricalJoint)):
                check_angle(kwargs.get("angle"), other.angular_range)
            if isinstance(other, (CylindricalJoint, LinearJoint)):
                check_position(kwargs.get("position"), other.linear_range)

        t_angles = [0, 0, 0]

        if kwargs.get("angle") is not None:
            t_angles = [0, 0, -kwargs["angle"]]
        elif kwargs.get("angles") is not None:
            t_angles = [-kwargs["angles"][i] for i in (0, 1, 2)]

        t_position = (0, 0, 0)
        if kwargs.get("position") is not None:
            t_position = (0, 0, -kwargs["position"])

        transformation = Location(t_position, t_angles)

        return super()._connect_to(other, transformation=transformation)


class RevoluteJoint(Joint):
    """RevoluteJoint

    Component rotates around axis like a hinge.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound], optional): object to attach joint to
        axis (Axis): axis of rotation
        angle_reference (VectorLike, optional): direction normal to axis defining where
            angles will be measured from. Defaults to None.
        range (tuple[float, float], optional): (min,max) angle of joint. Defaults to (0, 360).

    Attributes:
        angle (float): angle of joint
        angle_reference (Vector): reference for angular positions
        angular_range (tuple[float,float]): min and max angular position of joint
        relative_location (Location): joint location relative to bound object

    Raises:
        ValueError: angle_reference must be normal to axis
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing the axis of rotation as bound to part"""
        radius = self.parent.bounding_box().diagonal / 30

        return Compound.make_compound(
            [
                Edge.make_line((0, 0, 0), (0, 0, radius * 10)),
                Edge.make_circle(radius),
            ]
        ).move(self.location)

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound] = None,
        axis: Axis = Axis.Z,
        angle_reference: VectorLike = None,
        angular_range: tuple[float, float] = (0, 360),
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self)
        if to_part is None:
            if context is not None:
                to_part = context
            else:
                raise ValueError("Either specify to_part or place in BuildPart scope")

        self.axis = axis
        self.angular_range = angular_range
        if angle_reference:
            if not axis.is_normal(Axis((0, 0, 0), angle_reference)):
                raise ValueError("angle_reference must be normal to axis")
            self.angle_reference = Vector(angle_reference)
        else:
            self.angle_reference = Plane(origin=(0, 0, 0), z_dir=axis.direction).x_dir
        self.angle = None
        to_part.joints[label] = self
        super().__init__(label, to_part)

        # to be assigned after super().__init__
        self.relative_location = to_part.location.inverse() * (
            Plane(
                self.axis.position,
                x_dir=self.angle_reference,
                z_dir=self.axis.direction,
            ).location
        )

    def connect_to(self, other: RigidJoint, *, angle: float = None):
        """Connect RevoluteJoint and RigidJoint

        Args:
            other (RigidJoint): relative to joint
            angle (float, optional): angle in degrees. Defaults to range min.

        Returns:
            TypeError: other must of type RigidJoint
            ValueError: angle out of range
        """
        self.check_compatibility(other)
        check_angle(angle, self.angular_range)

        t_angle = (0, 0, self.angular_range[0]) if angle is None else (0, 0, angle)

        transformation = Rotation(t_angle)
        self.angle = t_angle

        return super()._connect_to(other, transformation=transformation)


class LinearJoint(Joint):
    """LinearJoint

    Component moves along a single axis.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound], optional): object to attach joint to
        axis (Axis): axis of linear motion
        range (tuple[float, float], optional): (min,max) position of joint.
            Defaults to (0, inf).

    Attributes:
        axis (Axis): joint axis
        angle (float): angle of joint
        linear_range (tuple[float,float]): min and max positional values
        position (float): joint position
        relative_location (Location): joint location relative to bound object
        angle_reference (VectorLike, optional): direction normal to axis defining where
            angles will be measured from. Defaults to None.
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol of the linear axis positioned relative to_part"""
        radius = (self.linear_range[1] - self.linear_range[0]) / 15
        return Compound.make_compound(
            [
                Edge.make_line(
                    (0, 0, self.linear_range[0]), (0, 0, self.linear_range[1])
                ),
                Edge.make_circle(radius),
            ]
        ).move(self.location)

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound] = None,
        axis: Axis = Axis.Z,
        linear_range: tuple[float, float] = (0, inf),
        angle_reference: VectorLike = None,
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self)
        if to_part is None:
            if context is not None:
                to_part = context
            else:
                raise ValueError("Either specify to_part or place in BuildPart scope")

        self.axis = axis
        self.linear_range = linear_range
        self.position = None
        if angle_reference:
            if not axis.is_normal(Axis((0, 0, 0), angle_reference)):
                raise ValueError("z_reference must be normal to axis")
            self.angle_reference = Vector(angle_reference)
        else:
            # choose x-direction as the reference for the other joints z-axis
            self.angle_reference = Plane(origin=(0, 0, 0), z_dir=axis.direction).x_dir
        self.angle = None
        to_part.joints[label]: dict[str, Joint] = self
        super().__init__(label, to_part)

        # to be assigned after super().__init__
        self.relative_location = to_part.location.inverse() * (
            Plane(
                self.axis.position,
                x_dir=self.angle_reference,
                z_dir=self.axis.direction,
            ).location
        )

    @overload
    def connect_to(
        self, other: RevoluteJoint, *, position: float = None, angle: float = None
    ):
        """Connect LinearJoint and RevoluteJoint"""

    @overload
    def connect_to(self, other: RigidJoint, *, position: float = None):
        """Connect LinearJoint and RigidJoint"""

    def connect_to(self, other: Joint, **kwargs):
        """Connect LinearJoint to another Joint

        Args:
            other (Joint): joint to connect to
            angle (float, optional): angle in degrees. Defaults to range min.
            position (float, optional): linear position. Defaults to linear range min.

        Raises:
            TypeError: other must be of type RevoluteJoint or RigidJoint
            ValueError: position out of range
            ValueError: angle out of range
        """
        self.check_compatibility(other)
        check_position(kwargs.get("position"), self.linear_range)

        t_angle = (0, 0, 0)
        if isinstance(other, RevoluteJoint):
            if kwargs.get("angle") is None:
                t_angle = (0, 0, -other.angular_range[0])
            else:
                check_angle(kwargs.get("angle"), other.angular_range)
                t_angle = (0, 0, -kwargs.get("angle"))

        t_position = (
            (0, 0, 0)
            if kwargs.get("position") is None
            else (0, 0, kwargs.get("position"))
        )

        transformation = Location(t_position, t_angle)
        return super()._connect_to(other, transformation=transformation)


class CylindricalJoint(Joint):
    """CylindricalJoint

    Component rotates around and moves along a single axis like a screw.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound], optional): object to attach joint to
        axis (Axis): axis of rotation and linear motion
        angle_reference (VectorLike, optional): direction normal to axis defining where
            angles will be measured from. Defaults to None.
        linear_range (tuple[float, float], optional): (min,max) position of joint.
            Defaults to (0, inf).
        angular_range (tuple[float, float], optional): (min,max) angle of joint.
            Defaults to (0, 360).

    Attributes:
        axis (Axis): joint axis
        linear_position (float): linear joint position
        rotational_position (float): revolute joint angle in degrees
        angle_reference (Vector): reference for angular positions
        angular_range (tuple[float,float]): min and max angular position of joint
        linear_range (tuple[float,float]): min and max positional values
        relative_location (Location): joint location relative to bound object
        position (float): joint position
        angle (float): angle of joint

    Raises:
        ValueError: angle_reference must be normal to axis
    """
    # pylint: disable=too-many-instance-attributes

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing the cylindrical axis as bound to part"""
        radius = (self.linear_range[1] - self.linear_range[0]) / 15
        return Compound.make_compound(
            [
                Edge.make_line(
                    (0, 0, self.linear_range[0]), (0, 0, self.linear_range[1])
                ),
                Edge.make_circle(radius),
            ]
        ).move(self.location)

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound] = None,
        axis: Axis = Axis.Z,
        angle_reference: VectorLike = None,
        linear_range: tuple[float, float] = (0, inf),
        angular_range: tuple[float, float] = (0, 360),
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self)
        if to_part is None:
            if context is not None:
                to_part = context
            else:
                raise ValueError("Either specify to_part or place in BuildPart scope")

        self.axis = axis
        self.linear_position = None
        self.rotational_position = None
        if angle_reference:
            if not axis.is_normal(Axis((0, 0, 0), angle_reference)):
                raise ValueError("angle_reference must be normal to axis")
            self.angle_reference = Vector(angle_reference)
        else:
            self.angle_reference = Plane(origin=(0, 0, 0), z_dir=axis.direction).x_dir
        self.angular_range = angular_range
        self.linear_range = linear_range
        self.position = None
        self.angle = None
        to_part.joints[label]: dict[str, Joint] = self
        super().__init__(label, to_part)

        # to be assigned after super().__init__
        self.relative_location = to_part.location.inverse() * (
            Plane(
                self.axis.position,
                x_dir=self.angle_reference,
                z_dir=self.axis.direction,
            ).location
        )

    def connect_to(
        self, other: RigidJoint, *, position: float = None, angle: float = None
    ):
        """Connect CylindricalJoint and RigidJoint"

        Args:
            other (Joint): joint to connect to
            position (float, optional): linear position. Defaults to linear range min.
            angle (float, optional): angle in degrees. Defaults to range min.

        Raises:
            TypeError: other must be of type RigidJoint
            ValueError: position out of range
            ValueError: angle out of range
        """
        self.check_compatibility(other)
        check_position(position, self.linear_range)
        check_angle(angle, self.angular_range)

        t_angle = (0, 0, self.angular_range[0]) if angle is None else (0, 0, angle)
        t_position = (
            (0, 0, self.linear_range[0]) if position is None else (0, 0, position)
        )

        transformation = Location(t_position, t_angle)
        return super()._connect_to(other, transformation=transformation)


class BallJoint(Joint):
    """BallJoint

    A component rotates around all 3 axes using a gimbal system (3 nested rotations).

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound], optional): object to attach joint to
        joint_location (Location): global location of joint
        angular_range
            (tuple[ tuple[float, float], tuple[float, float], tuple[float, float] ], optional):
            X, Y, Z angle (min, max) pairs. Defaults to ((0, 360), (0, 360), (0, 360)).
        angle_reference (Plane, optional): plane relative to part defining zero degrees of
            rotation. Defaults to Plane.XY.

    Attributes:
        relative_location (Location): joint location relative to bound part
        angular_range
            (tuple[ tuple[float, float], tuple[float, float], tuple[float, float] ]):
            X, Y, Z angle (min, max) pairs.
        angle_reference (Plane): plane relative to part defining zero degrees of

    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing joint as bound to part"""
        radius = self.parent.bounding_box().diagonal / 30
        circle_x = Edge.make_circle(radius, self.angle_reference)
        circle_y = Edge.make_circle(radius, self.angle_reference.rotated((90, 0, 0)))
        circle_z = Edge.make_circle(radius, self.angle_reference.rotated((0, 90, 0)))

        return Compound.make_compound(
            [
                circle_x,
                circle_y,
                circle_z,
                Compound.make_text(
                    "X", radius / 5, align=(Align.CENTER, Align.CENTER)
                ).locate(circle_x.location_at(0.125) * Rotation(90, 0, 0)),
                Compound.make_text(
                    "Y", radius / 5, align=(Align.CENTER, Align.CENTER)
                ).locate(circle_y.location_at(0.625) * Rotation(90, 0, 0)),
                Compound.make_text(
                    "Z", radius / 5, align=(Align.CENTER, Align.CENTER)
                ).locate(circle_z.location_at(0.125) * Rotation(90, 0, 0)),
            ]
        ).move(self.location)

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound] = None,
        joint_location: Location = Location(),
        angular_range: tuple[
            tuple[float, float], tuple[float, float], tuple[float, float]
        ] = ((0, 360), (0, 360), (0, 360)),
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self)
        if to_part is None:
            if context is not None:
                to_part = context
            else:
                raise ValueError("Either specify to_part or place in BuildPart scope")

        to_part.joints[label] = self
        self.angular_range = angular_range
        # for BallJoints the angle_reference is the actual joint location
        self.angle_reference = Plane.XY
        super().__init__(label, to_part)

        # to be assigned after super().__init__
        self.relative_location = to_part.location.inverse() * joint_location

    def connect_to(self, other: RigidJoint, *, angles: RotationLike = None):
        """Connect BallJoint and RigidJoint

        Args:
            other (RigidJoint): joint to connect to
            angles (RotationLike, optional): angles about axes in degrees. Defaults to
                range minimums.

        Raises:
            TypeError: invalid other joint type
            ValueError: angles out of range
        """
        self.check_compatibility(other)
        for angle, angular_range in zip(angles, self.angular_range):
            check_angle(angle, angular_range)

        transformation = (
            Rotation(*[self.angular_range[i][0] for i in [0, 1, 2]])
            if angles is None
            else Rotation(*angles)
        ) * self.angle_reference.location

        return super()._connect_to(other, transformation=transformation)
