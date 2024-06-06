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
    def location(self) -> Location:
        """Location of joint"""
        return self.parent.location * self.relative_location

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

        self.relative_location = to_part.location.inverse() * joint_location
        to_part.joints[label] = self
        super().__init__(label, to_part)

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
        return super()._connect_to(other, **kwargs)

    @overload
    def relative_to(self, other: BallJoint, *, angles: RotationLike = None):
        """RigidJoint relative to BallJoint"""

    @overload
    def relative_to(
        self, other: CylindricalJoint, *, position: float = None, angle: float = None
    ):
        """RigidJoint relative to CylindricalJoint"""

    @overload
    def relative_to(self, other: LinearJoint, *, position: float = None):
        """RigidJoint relative to LinearJoint"""

    @overload
    def relative_to(self, other: RevoluteJoint, *, angle: float = None):
        """RigidJoint relative to RevoluteJoint"""

    @overload
    def relative_to(self, other: RigidJoint):
        """Connect two RigidJoints together"""

    def relative_to(self, other: Joint, **kwargs) -> Location:
        """Relative location of RigidJoint to another Joint

        Args:
            other (RigidJoint): relative to joint
            angle (float, optional): angle in degrees. Defaults to range min.
            angles (RotationLike, optional): angles about axes in degrees. Defaults to
                range minimums.
            position (float, optional): linear position. Defaults to linear range min.

        Raises:
            TypeError: other must be of a type in: BallJoint, CylindricalJoint,
                LinearJoint, RevoluteJoint, RigidJoint.

        """
        if isinstance(other, RigidJoint):
            other_location = self.relative_location * other.relative_location.inverse()
        elif isinstance(other, RevoluteJoint):
            angle = None
            if kwargs:
                angle = kwargs["angle"] if "angle" in kwargs else angle
            other_location = other.relative_to(self, angle=angle).inverse()
        elif isinstance(other, LinearJoint):
            position = None
            if kwargs:
                position = kwargs["position"] if "position" in kwargs else position
            other_location = other.relative_to(self, position=position).inverse()
        elif isinstance(other, CylindricalJoint):
            angle, position = None, None
            if kwargs:
                angle = kwargs["angle"] if "angle" in kwargs else angle
                position = kwargs["position"] if "position" in kwargs else position
            other_location = other.relative_to(
                self, position=position, angle=angle
            ).inverse()
        elif isinstance(other, BallJoint):
            angles = None
            if kwargs:
                angles = kwargs["angles"] if "angles" in kwargs else angles
            other_location = other.relative_to(self, angles=angles).inverse()
        else:
            raise TypeError(
                "other must one of type "
                "BallJoint, CylindricalJoint, LinearJoint, RevoluteJoint, RigidJoint "
                f"not {type(other)}"
            )

        return other_location


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
        relative_axis (Axis): joint axis relative to bound part

    Raises:
        ValueError: angle_reference must be normal to axis
    """

    @property
    def location(self) -> Location:
        """Location of joint"""
        return self.parent.location * self.relative_axis.location

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing the axis of rotation as bound to part"""
        radius = self.parent.bounding_box().diagonal / 30

        return Compound(
            [
                Edge.make_line((0, 0, 0), (0, 0, radius * 10)),
                Edge.make_circle(radius),
                Edge.make_line((0, 0, 0), (radius, 0, 0)),
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

        self.angular_range = angular_range
        if angle_reference:
            if not axis.is_normal(Axis((0, 0, 0), angle_reference)):
                raise ValueError("angle_reference must be normal to axis")
            self.angle_reference = Vector(angle_reference)
        else:
            self.angle_reference = Plane(origin=(0, 0, 0), z_dir=axis.direction).x_dir
        self._angle = None
        self.relative_axis = axis.located(to_part.location.inverse())
        to_part.joints[label] = self
        super().__init__(label, to_part)

    def connect_to(self, other: RigidJoint, *, angle: float = None):
        """Connect RevoluteJoint and RigidJoint

        Args:
            other (RigidJoint): relative to joint
            angle (float, optional): angle in degrees. Defaults to range min.

        Returns:
            TypeError: other must of type RigidJoint
            ValueError: angle out of range
        """
        return super()._connect_to(other, angle=angle)

    def relative_to(
        self, other: RigidJoint, *, angle: float = None
    ):  # pylint: disable=arguments-differ
        """Relative location of RevoluteJoint to RigidJoint

        Args:
            other (RigidJoint): relative to joint
            angle (float, optional): angle in degrees. Defaults to range min.

        Raises:
            TypeError: other must of type RigidJoint
            ValueError: angle out of range
        """
        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        angle = self.angular_range[0] if angle is None else angle
        if angle < self.angular_range[0] or angle > self.angular_range[1]:
            raise ValueError(f"angle ({angle}) must in range of {self.angular_range}")
        self._angle = angle
        # Avoid strange rotations when angle is zero by using 360 instead
        angle = 360.0 if angle == 0.0 else angle
        return (
            self.relative_axis.location
            * Rotation(0, 0, angle)
            * other.relative_location.inverse()
        )


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
        relative_axis (Axis): joint axis relative to bound part

    """

    @property
    def location(self) -> Location:
        """Location of joint"""
        return self.parent.location * self.relative_axis.location

    @property
    def symbol(self) -> Compound:
        """A CAD symbol of the linear axis positioned relative to_part"""
        radius = (self.linear_range[1] - self.linear_range[0]) / 15
        return Compound(
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
        self.relative_axis = axis.located(to_part.location.inverse())
        self.angle = None
        to_part.joints[label]: dict[str, Joint] = self
        super().__init__(label, to_part)

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
        return super()._connect_to(other, **kwargs)

    @overload
    def relative_to(
        self, other: RigidJoint, *, position: float = None
    ):  # pylint: disable=arguments-differ
        """Relative location of LinearJoint to RigidJoint"""

    @overload
    def relative_to(
        self, other: RevoluteJoint, *, position: float = None, angle: float = None
    ):  # pylint: disable=arguments-differ
        """Relative location of LinearJoint to RevoluteJoint"""

    def relative_to(self, other, **kwargs):  # pylint: disable=arguments-differ
        """Relative location of LinearJoint to RevoluteJoint or RigidJoint

        Args:
            other (Joint): joint to connect to
            angle (float, optional): angle in degrees. Defaults to range min.
            position (float, optional): linear position. Defaults to linear range min.

        Raises:
            TypeError: other must be of type RevoluteJoint or RigidJoint
            ValueError: position out of range
            ValueError: angle out of range
        """

        # Parse the input parameters
        position, angle = None, None
        if kwargs:
            position = kwargs["position"] if "position" in kwargs else position
            angle = kwargs["angle"] if "angle" in kwargs else angle

        if not isinstance(other, (RigidJoint, RevoluteJoint)):
            raise TypeError(
                f"other must of type RigidJoint or RevoluteJoint not {type(other)}"
            )

        position = sum(self.linear_range) / 2 if position is None else position
        if not self.linear_range[0] <= position <= self.linear_range[1]:
            raise ValueError(
                f"position ({position}) must in range of {self.linear_range}"
            )
        self.position = position

        if isinstance(other, RevoluteJoint):
            other: RevoluteJoint
            angle = other.angular_range[0] if angle is None else angle
            if not other.angular_range[0] <= angle <= other.angular_range[1]:
                raise ValueError(
                    f"angle ({angle}) must in range of {other.angular_range}"
                )
            rotation = Location(
                Plane(
                    origin=(0, 0, 0),
                    x_dir=other.angle_reference.rotate(other.relative_axis, angle),
                    z_dir=other.relative_axis.direction,
                )
            )
        else:
            angle = 0.0
            rotation = Location()
        self.angle = angle
        joint_relative_position = (
            Location(
                self.relative_axis.position + self.relative_axis.direction * position,
            )
            * rotation
        )

        if isinstance(other, RevoluteJoint):
            other_relative_location = Location(other.relative_axis.position)
        else:
            other_relative_location = other.relative_location

        return joint_relative_position * other_relative_location.inverse()


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
        relative_axis (Axis): joint axis relative to bound part
        position (float): joint position
        angle (float): angle of joint

    Raises:
        ValueError: angle_reference must be normal to axis
    """

    # pylint: disable=too-many-instance-attributes

    @property
    def location(self) -> Location:
        """Location of joint"""
        return self.parent.location * self.relative_axis.location

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing the cylindrical axis as bound to part"""
        radius = (self.linear_range[1] - self.linear_range[0]) / 15
        return Compound(
            [
                Edge.make_line(
                    (0, 0, self.linear_range[0]), (0, 0, self.linear_range[1])
                ),
                Edge.make_circle(radius),
                Edge.make_line((0, 0, 0), (radius, 0, 0)),
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
        self.relative_axis = axis.located(to_part.location.inverse())
        self.position = None
        self.angle = None
        to_part.joints[label]: dict[str, Joint] = self
        super().__init__(label, to_part)

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
        return super()._connect_to(other, position=position, angle=angle)

    def relative_to(
        self, other: RigidJoint, *, position: float = None, angle: float = None
    ):  # pylint: disable=arguments-differ
        """Relative location of CylindricalJoint to RigidJoint

        Args:
            other (Joint): joint to connect to
            position (float, optional): linear position. Defaults to linear range min.
            angle (float, optional): angle in degrees. Defaults to range min.

        Raises:
            TypeError: other must be of type RigidJoint
            ValueError: position out of range
            ValueError: angle out of range
        """
        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        position = sum(self.linear_range) / 2 if position is None else position
        if not self.linear_range[0] <= position <= self.linear_range[1]:
            raise ValueError(
                f"position ({position}) must in range of {self.linear_range}"
            )
        self.position = position
        angle = sum(self.angular_range) / 2 if angle is None else angle
        if not self.angular_range[0] <= angle <= self.angular_range[1]:
            raise ValueError(f"angle ({angle}) must in range of {self.angular_range}")
        self.angle = angle

        joint_relative_position = Location(
            self.relative_axis.position + self.relative_axis.direction * position
        )
        joint_rotation = Location(
            Plane(
                origin=(0, 0, 0),
                x_dir=self.angle_reference.rotate(self.relative_axis, angle),
                z_dir=self.relative_axis.direction,
            )
        )

        return (
            joint_relative_position * joint_rotation * other.relative_location.inverse()
        )


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
    def location(self) -> Location:
        """Location of joint"""
        return self.parent.location * self.relative_location

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing joint as bound to part"""
        radius = self.parent.bounding_box().diagonal / 30
        circle_x = Edge.make_circle(radius, self.angle_reference)
        circle_y = Edge.make_circle(radius, self.angle_reference.rotated((90, 0, 0)))
        circle_z = Edge.make_circle(radius, self.angle_reference.rotated((0, 90, 0)))

        return Compound(
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
        angle_reference: Plane = Plane.XY,
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self)
        if to_part is None:
            if context is not None:
                to_part = context
            else:
                raise ValueError("Either specify to_part or place in BuildPart scope")

        self.relative_location = to_part.location.inverse() * joint_location
        to_part.joints[label] = self
        self.angular_range = angular_range
        self.angle_reference = angle_reference
        super().__init__(label, to_part)

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
        return super()._connect_to(other, angles=angles)

    def relative_to(
        self, other: RigidJoint, *, angles: RotationLike = None
    ):  # pylint: disable=arguments-differ
        """relative_to - BallJoint

        Return the relative location from this joint to the RigidJoint of another object

        Args:
            other (RigidJoint): joint to connect to
            angles (RotationLike, optional): angles about axes in degrees. Defaults to
                range minimums.

        Raises:
            TypeError: invalid other joint type
            ValueError: angles out of range
        """

        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        rotation = (
            Rotation(*[self.angular_range[i][0] for i in [0, 1, 2]])
            if angles is None
            else Rotation(*angles)
        ) * self.angle_reference.location

        for i, rotations in zip(
            [0, 1, 2],
            [rotation.orientation.X, rotation.orientation.Y, rotation.orientation.Z],
        ):
            if not self.angular_range[i][0] <= rotations <= self.angular_range[i][1]:
                raise ValueError(
                    f"angles ({angles}) must in range of {self.angular_range}"
                )

        return self.relative_location * rotation * other.relative_location.inverse()
