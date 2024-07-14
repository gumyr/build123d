"""
build123d geometry

name: geometry.py
by:   Gumyr
date: March 2nd, 2023

desc:
    This python module contains geometric objects used by the topology.py
    module to form the build123d direct api.

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

# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error, too-many-lines
# other pylint warning to temp remove:
#   too-many-arguments, too-many-locals, too-many-public-methods,
#   too-many-statements, too-many-instance-attributes, too-many-branches
import copy
import json
import logging
import numpy as np

from math import degrees, pi, radians
from typing import (
    Any,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
    TypeVar,
)
from typing_extensions import deprecated

from OCP.Bnd import Bnd_Box, Bnd_OBB
from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepGProp import BRepGProp, BRepGProp_Face  # used for mass calculation
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.Geom import Geom_Line, Geom_Plane
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf, GeomAPI_IntCS, GeomAPI_IntSS
from OCP.gp import (
    gp_Ax1,
    gp_Ax2,
    gp_Ax3,
    gp_Dir,
    gp_EulerSequence,
    gp_GTrsf,
    gp_Lin,
    gp_Pln,
    gp_Pnt,
    gp_Quaternion,
    gp_Trsf,
    gp_Vec,
    gp_XYZ,
)

# properties used to store mass calculation result
from OCP.GProp import GProp_GProps
from OCP.Quantity import Quantity_Color, Quantity_ColorRGBA
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Face, TopoDS_Shape, TopoDS_Vertex

from build123d.build_enums import Align, Intrinsic, Extrinsic

# Create a build123d logger to distinguish these logs from application logs.
# If the user doesn't configure logging, all build123d logs will be discarded.
logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")

TOLERANCE = 1e-6
TOL = 1e-2
DEG2RAD = pi / 180.0
RAD2DEG = 180 / pi


def _parse_intersect_args(*args, **kwargs):
    axis, plane, vector, location, shape = (None,) * 5

    if args:
        if isinstance(args[0], Axis):
            axis = args[0]
        elif isinstance(args[0], Plane):
            plane = args[0]
        elif isinstance(args[0], Location):
            location = args[0]
        elif isinstance(args[0], (Vector, tuple)):
            vector = Vector(args[0])
        elif hasattr(args[0], "wrapped"):
            shape = args[0]
        else:
            raise ValueError(f"Unexpected argument type {type(args[0])}")

    unknown_args = ", ".join(
        set(kwargs.keys()).difference(["axis", "plane", "location", "vector", "shape"])
    )
    if unknown_args:
        raise ValueError(f"Unexpected argument(s) {unknown_args}")

    axis = kwargs.get("axis", axis)
    plane = kwargs.get("plane", plane)
    vector = kwargs.get("vector", vector)
    location = kwargs.get("location", location)
    shape = kwargs.get("shape", shape)

    return axis, plane, vector, location, shape


class Vector:
    """Create a 3-dimensional vector

    Args:
        x (float): x component
        y (float): y component
        z (float): z component
        vec (Union[Vector, Sequence(float), gp_Vec, gp_Pnt, gp_Dir, gp_XYZ]): vector representations

    Note that if no z value is provided it's assumed to be zero. If no values are provided
    the returned Vector has the value of 0, 0, 0.

    Attributes:
        wrapped (gp_Vec): the OCP vector object

    """

    # pylint: disable=too-many-public-methods
    _wrapped: gp_Vec
    _dim = 0

    @overload
    def __init__(self, X: float, Y: float, Z: float):  # pragma: no cover
        ...

    @overload
    def __init__(self, X: float, Y: float):  # pragma: no cover
        ...

    @overload
    def __init__(self, v: Vector):  # pragma: no cover
        ...

    @overload
    def __init__(self, v: Sequence[float]):  # pragma: no cover
        ...

    @overload
    def __init__(self, v: Union[gp_Vec, gp_Pnt, gp_Dir, gp_XYZ]):  # pragma: no cover
        ...

    @overload
    def __init__(self):  # pragma: no cover
        ...

    def __init__(self, *args, **kwargs):
        self.vector_index = 0
        x, y, z, ocp_vec = 0, 0, 0, None

        unknown_args = ", ".join(set(kwargs.keys()).difference(["v", "X", "Y", "Z"]))
        if unknown_args:
            raise ValueError(f"Unexpected argument(s) {unknown_args}")

        if args and all(isinstance(args[i], (int, float)) for i in range(len(args))):
            values = list(args)
            values += [0.0] * max(0, (3 - len(args)))
            x, y, z = values[0:3]
        elif len(args) == 1 or "v" in kwargs:
            first_arg = args[0] if args else None
            first_arg = kwargs.get("v", first_arg)  # override with kwarg
            if isinstance(first_arg, Vector):
                ocp_vec = gp_Vec(first_arg.wrapped.XYZ())
            elif hasattr(first_arg, "wrapped") and isinstance(
                first_arg.wrapped, TopoDS_Vertex
            ):
                geom_point = BRep_Tool.Pnt_s(first_arg.wrapped)
                ocp_vec = gp_Vec(geom_point.XYZ())
            elif isinstance(first_arg, (tuple, Iterable)):
                try:
                    values = [float(value) for value in first_arg]
                except (TypeError, ValueError) as exc:
                    raise TypeError("Expected floats") from exc
                if len(values) < 3:
                    values += [0.0] * (3 - len(values))
                ocp_vec = gp_Vec(*values[0:3])
            elif isinstance(first_arg, (gp_Vec, gp_Pnt, gp_Dir)):
                ocp_vec = gp_Vec(first_arg.XYZ())
            elif isinstance(first_arg, gp_XYZ):
                ocp_vec = gp_Vec(first_arg)
            else:
                raise TypeError("Expected floats, OCC gp_, or iterable")
        x = kwargs.get("X", x)
        y = kwargs.get("Y", y)
        z = kwargs.get("Z", z)
        ocp_vec = gp_Vec(x, y, z) if ocp_vec is None else ocp_vec

        self._wrapped = ocp_vec

    def __iter__(self):
        """Initialize to beginning"""
        self.vector_index = 0
        return self

    def __next__(self):
        """return the next value"""
        if self.vector_index == 0:
            self.vector_index += 1
            value = self.X
        elif self.vector_index == 1:
            self.vector_index += 1
            value = self.Y
        elif self.vector_index == 2:
            self.vector_index += 1
            value = self.Z
        else:
            raise StopIteration
        return value

    @property
    def X(self) -> float:
        """Get x value"""
        return self.wrapped.X()

    @X.setter
    def X(self, value: float) -> None:
        """Set x value"""
        self.wrapped.SetX(value)

    @property
    def Y(self) -> float:
        """Get y value"""
        return self.wrapped.Y()

    @Y.setter
    def Y(self, value: float) -> None:
        """Set y value"""
        self.wrapped.SetY(value)

    @property
    def Z(self) -> float:
        """Get z value"""
        return self.wrapped.Z()

    @Z.setter
    def Z(self, value: float) -> None:
        """Set z value"""
        self.wrapped.SetZ(value)

    @property
    def wrapped(self) -> gp_Vec:
        """OCCT object"""
        return self._wrapped

    def to_tuple(self) -> tuple[float, float, float]:
        """Return tuple equivalent"""
        return (self.X, self.Y, self.Z)

    @property
    def length(self) -> float:
        """Vector length"""
        return self.wrapped.Magnitude()

    def cross(self, vec: Vector) -> Vector:
        """Mathematical cross function"""
        return Vector(self.wrapped.Crossed(vec.wrapped))

    def dot(self, vec: Vector) -> float:
        """Mathematical dot function"""
        return self.wrapped.Dot(vec.wrapped)

    def sub(self, vec: VectorLike) -> Vector:
        """Mathematical subtraction function"""
        if isinstance(vec, Vector):
            result = Vector(self.wrapped.Subtracted(vec.wrapped))
        elif isinstance(vec, tuple):
            result = Vector(self.wrapped.Subtracted(Vector(vec).wrapped))
        else:
            raise ValueError("Only Vectors or tuples can be subtracted from Vectors")

        return result

    def __sub__(self, vec: VectorLike) -> Vector:
        """Mathematical subtraction operator -"""
        return self.sub(vec)

    def add(self, vec: VectorLike) -> Vector:
        """Mathematical addition function"""
        if isinstance(vec, Vector):
            result = Vector(self.wrapped.Added(vec.wrapped))
        elif isinstance(vec, tuple):
            result = Vector(self.wrapped.Added(Vector(vec).wrapped))
        else:
            raise ValueError("Only Vectors or tuples can be added to Vectors")

        return result

    def __add__(self, vec: VectorLike) -> Vector:
        """Mathematical addition operator +"""
        return self.add(vec)

    def __radd__(self, vec: Vector) -> Vector:
        """Mathematical reverse addition operator +"""
        vec = Vector(0, 0, 0) if vec == 0 else vec  # sum starts with 0
        return self.add(vec)

    def multiply(self, scale: float) -> Vector:
        """Mathematical multiply function"""
        return Vector(self.wrapped.Multiplied(scale))

    def __mul__(self, scale: float) -> Vector:
        """Mathematical multiply operator *"""
        return self.multiply(scale)

    def __truediv__(self, denom: float) -> Vector:
        """Mathematical division operator /"""
        return self.multiply(1.0 / denom)

    def __rmul__(self, scale: float) -> Vector:
        """Mathematical multiply operator *"""
        return self.multiply(scale)

    def normalized(self) -> Vector:
        """Scale to length of 1"""
        return Vector(self.wrapped.Normalized())

    def reverse(self) -> Vector:
        """Return a vector with the same magnitude but pointing in the opposite direction"""
        return self * -1.0

    def center(self) -> Vector:
        """center

        Returns:
          The center of myself is myself.
          Provided so that vectors, vertices, and other shapes all support a
          common interface, when center() is requested for all objects on the
          stack.

        """
        return self

    def get_angle(self, vec: Vector) -> float:
        """Unsigned angle between vectors"""
        return self.wrapped.Angle(vec.wrapped) * RAD2DEG

    def get_signed_angle(self, vec: Vector, normal: Vector = None) -> float:
        """Signed Angle Between Vectors

        Return the signed angle in degrees between two vectors with the given normal
        based on this math: angle = atan2((Va × Vb) ⋅ Vn, Va ⋅ Vb)

        Args:
            v (Vector): Second Vector
            normal (Vector, optional): normal direction. Defaults to None.

        Returns:
            float: Angle between vectors
        """
        if normal is None:
            gp_normal = gp_Vec(0, 0, -1)
        else:
            gp_normal = normal.wrapped
        return self.wrapped.AngleWithRef(vec.wrapped, gp_normal) * RAD2DEG

    def project_to_line(self, line: Vector) -> Vector:
        """Returns a new vector equal to the projection of this Vector onto the line
        represented by Vector <line>

        Args:
            line (Vector): project to this line

        Returns:
            Vector: Returns the projected vector.

        """
        line_length = line.length

        return line * (self.dot(line) / (line_length * line_length))

    def distance_to_plane(self, plane: Plane) -> float:
        """Minimum unsigned distance between vector and plane"""
        return plane.wrapped.Distance(self.to_pnt())

    def signed_distance_from_plane(self, plane: Plane) -> float:
        """Signed distance from plane to point vector."""
        return (self - plane.origin).dot(plane.z_dir)

    def project_to_plane(self, plane: Plane) -> Vector:
        """Vector is projected onto the plane provided as input.

        Args:
          args: Plane object

        Returns the projected vector.
          plane: Plane:

        Returns:

        """
        base = plane.origin
        normal = plane.z_dir

        return self - normal * (((self - base).dot(normal)) / normal.length**2)

    def __neg__(self) -> Vector:
        """Flip direction of vector operator -"""
        return self * -1

    def __abs__(self) -> float:
        """Vector length operator abs()"""
        return self.length

    def __and__(self: Plane, other: Union[Axis, Location, Plane, VectorLike, "Shape"]):
        """intersect vector with other &"""
        return self.intersect(other)

    def __repr__(self) -> str:
        """Display vector"""
        x = round(self.X, 13) if abs(self.X) > TOLERANCE else 0.0
        y = round(self.Y, 13) if abs(self.Y) > TOLERANCE else 0.0
        z = round(self.Z, 13) if abs(self.Z) > TOLERANCE else 0.0
        return f"Vector({x:.14g}, {y:.14g}, {z:.14g})"

    __str__ = __repr__

    def __eq__(self, other: Vector) -> bool:  # type: ignore[override]
        """Vectors equal operator =="""
        return self.wrapped.IsEqual(other.wrapped, 0.00001, 0.00001)

    def __hash__(self) -> int:
        """Hash of Vector"""
        return hash(self.X) + hash(self.Y) + hash(self.Z)

    def __copy__(self) -> Vector:
        """Return copy of self"""
        return Vector(self.X, self.Y, self.Z)

    def __deepcopy__(self, _memo) -> Vector:
        """Return deepcopy of self"""
        return Vector(self.X, self.Y, self.Z)

    def to_pnt(self) -> gp_Pnt:
        """Convert to OCCT gp_Pnt object"""
        return gp_Pnt(self.wrapped.XYZ())

    def to_dir(self) -> gp_Dir:
        """Convert to OCCT gp_Dir object"""
        return gp_Dir(self.wrapped.XYZ())

    def transform(self, affine_transform: Matrix, is_direction: bool = False) -> Vector:
        """Apply affine transformation

        Args:
            affine_transform (Matrix): affine transformation matrix
            is_direction (bool, optional): Should self be transformed as a vector or direction?
                Defaults to False (vector)

        Returns:
            Vector: transformed vector
        """
        if not is_direction:
            # to gp_Pnt to obey build123d transformation convention (in OCP.vectors do not translate)
            pnt = self.to_pnt()
            pnt_t = pnt.Transformed(affine_transform.wrapped.Trsf())
            return_value = Vector(gp_Vec(pnt_t.XYZ()))
        else:
            # to gp_Dir for transformation of "direction vectors" (no translation or scaling)
            dir = self.to_dir()
            dir_t = dir.Transformed(affine_transform.wrapped.Trsf())
            return_value = Vector(gp_Vec(dir_t.XYZ()))
        return return_value

    def rotate(self, axis: Axis, angle: float) -> Vector:
        """Rotate about axis

        Rotate about the given Axis by an angle in degrees

        Args:
            axis (Axis): Axis of rotation
            angle (float): angle in degrees

        Returns:
            Vector: rotated vector
        """
        return Vector(self.wrapped.Rotated(axis.wrapped, pi * angle / 180))

    @overload
    def intersect(self, vector: VectorLike) -> Union[Vector, None]:
        """Find intersection of vector and vector"""

    @overload
    def intersect(self, location: Location) -> Union[Vector, None]:
        """Find intersection of location and vector"""

    @overload
    def intersect(self, axis: Axis) -> Union[Vector, None]:
        """Find intersection of axis and vector"""

    @overload
    def intersect(self, plane: Plane) -> Union[Vector, None]:
        """Find intersection of plane and vector"""

    def intersect(self, *args, **kwargs):
        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            return axis.intersect(self)

        elif plane is not None:
            return plane.intersect(self)

        elif vector is not None and self == vector:
            return vector

        elif location is not None:
            return location.intersect(self)

        elif shape is not None:
            return shape.intersect(self)


#:TypeVar("VectorLike"): Tuple of float or Vector defining a position in space
VectorLike = Union[
    Vector, tuple[float, float], tuple[float, float, float], Iterable[float]
]


class AxisMeta(type):
    """Axis meta class to enable class properties"""

    @property
    def X(cls) -> Axis:
        """X Axis"""
        return Axis((0, 0, 0), (1, 0, 0))

    @property
    def Y(cls) -> Axis:
        """Y Axis"""
        return Axis((0, 0, 0), (0, 1, 0))

    @property
    def Z(cls) -> Axis:
        """Z Axis"""
        return Axis((0, 0, 0), (0, 0, 1))


class Axis(metaclass=AxisMeta):
    """Axis

    Axis defined by point and direction

    Args:
        origin (VectorLike): start point
        direction (VectorLike): direction
        edge (Edge): origin & direction defined by start of edge

    Attributes:
        position (Vector): the global position of the axis origin
        direction (Vector): the normalized direction vector
        wrapped (gp_Ax1): the OCP axis object
    """

    _dim = 1

    @property
    def location(self) -> Location:
        """Return self as Location"""
        return Location(Plane(origin=self.position, z_dir=self.direction))

    @overload
    def __init__(self, gp_ax1: gp_Ax1):  # pragma: no cover
        """Axis: point and direction"""

    @overload
    def __init__(self, origin: VectorLike, direction: VectorLike):  # pragma: no cover
        """Axis: point and direction"""

    @overload
    def __init__(self, edge: "Edge"):  # pragma: no cover
        """Axis: start of Edge"""

    def __init__(self, *args, **kwargs):
        gp_ax1, origin, direction = (None,) * 3
        if len(args) == 1:
            if type(args[0]).__name__ == "Edge":
                origin = args[0].position_at(0)
                direction = args[0].tangent_at(0)
            elif isinstance(args[0], gp_Ax1):
                gp_ax1 = args[0]
            else:
                origin = args[0]
        if len(args) == 2:
            origin = args[0]
            direction = args[1]

        origin = kwargs.get("origin", origin)
        direction = kwargs.get("direction", direction)
        gp_ax1 = kwargs.get("gp_ax1", gp_ax1)
        if "edge" in kwargs and type(kwargs["edge"]).__name__ == "Edge":
            origin = kwargs["edge"].position_at(0)
            direction = kwargs["edge"].tangent_at(0)

        unknown_args = ", ".join(
            set(kwargs.keys()).difference(["gp_ax1", "origin", "direction", "edge"])
        )
        if unknown_args:
            raise ValueError(f"Unexpected argument(s) {unknown_args}")

        if gp_ax1 is not None:
            self.wrapped = gp_ax1
        else:
            try:
                origin = Vector(origin)
                direction = Vector(direction)
            except TypeError as exc:
                raise ValueError("Invalid Axis parameters") from exc

            self.wrapped = gp_Ax1(
                Vector(origin).to_pnt(),
                gp_Dir(*Vector(direction).normalized().to_tuple()),
            )

        self.position = Vector(
            self.wrapped.Location().X(),
            self.wrapped.Location().Y(),
            self.wrapped.Location().Z(),
        )
        self.direction = Vector(
            self.wrapped.Direction().X(),
            self.wrapped.Direction().Y(),
            self.wrapped.Direction().Z(),
        )

    def __copy__(self) -> Axis:
        """Return copy of self"""
        return Axis(self.position, self.direction)

    def __deepcopy__(self, _memo) -> Axis:
        """Return deepcopy of self"""
        return Axis(self.position, self.direction)

    def __repr__(self) -> str:
        """Display self"""
        return f"({self.position.to_tuple()},{self.direction.to_tuple()})"

    def __str__(self) -> str:
        """Display self"""
        return f"Axis: ({self.position.to_tuple()},{self.direction.to_tuple()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Axis):
            return False
        return self.position == other.position and self.direction == other.direction

    def located(self, new_location: Location):
        """relocates self to a new location possibly changing position and direction"""
        new_gp_ax1 = self.wrapped.Transformed(new_location.wrapped.Transformation())
        return Axis(new_gp_ax1)

    def to_plane(self) -> Plane:
        """Return self as Plane"""
        return Plane(origin=self.position, z_dir=self.direction)

    def is_coaxial(
        self,
        other: Axis,
        angular_tolerance: float = 1e-5,
        linear_tolerance: float = 1e-5,
    ) -> bool:
        """are axes coaxial

        True if the angle between self and other is lower or equal to angular_tolerance and
        the distance between self and other is lower or equal to linear_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.
            linear_tolerance (float, optional): max linear deviation. Defaults to 1e-5.

        Returns:
            bool: axes are coaxial
        """
        return self.wrapped.IsCoaxial(
            other.wrapped, angular_tolerance * (pi / 180), linear_tolerance
        )

    def is_normal(self, other: Axis, angular_tolerance: float = 1e-5) -> bool:
        """are axes normal

        Returns True if the direction of this and another axis are normal to each other. That is,
        if the angle between the two axes is equal to 90° within the angular_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.

        Returns:
            bool: axes are normal
        """
        return self.wrapped.IsNormal(other.wrapped, angular_tolerance * (pi / 180))

    def is_opposite(self, other: Axis, angular_tolerance: float = 1e-5) -> bool:
        """are axes opposite

        Returns True if the direction of this and another axis are parallel with
        opposite orientation. That is, if the angle between the two axes is equal
        to 180° within the angular_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.

        Returns:
            bool: axes are opposite
        """
        return self.wrapped.IsOpposite(other.wrapped, angular_tolerance * (pi / 180))

    def is_parallel(self, other: Axis, angular_tolerance: float = 1e-5) -> bool:
        """are axes parallel

        Returns True if the direction of this and another axis are parallel with same
        orientation or opposite orientation. That is, if the angle between the two axes is
        equal to 0° or 180° within the angular_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.

        Returns:
            bool: axes are parallel
        """
        return self.wrapped.IsParallel(other.wrapped, angular_tolerance * (pi / 180))

    def angle_between(self, other: Axis) -> float:
        """calculate angle between axes

        Computes the angular value, in degrees, between the direction of self and other
        between 0° and 360°.

        Args:
            other (Axis): axis to compare to

        Returns:
            float: angle between axes
        """
        return self.wrapped.Angle(other.wrapped) * RAD2DEG

    def reverse(self) -> Axis:
        """Return a copy of self with the direction reversed"""
        return Axis(self.wrapped.Reversed())

    def __neg__(self) -> Axis:
        """Flip direction operator -"""
        return self.reverse()

    def __and__(self: Plane, other: Union[Axis, Location, Plane, VectorLike, "Shape"]):
        """intersect vector with other &"""
        return self.intersect(other)

    @overload
    def intersect(self, vector: VectorLike) -> Union[Vector, None]:
        """Find intersection of vector and axis"""

    @overload
    def intersect(self, location: Location) -> Union[Location, None]:
        """Find intersection of location and axis"""

    @overload
    def intersect(self, axis: Axis) -> Union[Axis, None]:
        """Find intersection of axis and axis"""

    @overload
    def intersect(self, plane: Plane) -> Union[Axis, None]:
        """Find intersection of plane and axis"""

    def intersect(self, *args, **kwargs):
        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            if self.is_coaxial(axis):
                return self
            else:
                # Extract points and directions to numpy arrays
                p1 = np.array([*self.position])
                d1 = np.array([*self.direction])
                p2 = np.array([*axis.position])
                d2 = np.array([*axis.direction])

                # Compute the cross product of directions
                cross_d1_d2 = np.cross(d1, d2)
                cross_d1_d2_norm = np.linalg.norm(cross_d1_d2)

                if cross_d1_d2_norm < TOLERANCE:
                    # The directions are parallel
                    return None

                # Solve the system of equations to find the intersection
                system_of_equations = np.array([d1, -d2, cross_d1_d2]).T
                origin_diff = p2 - p1
                try:
                    t1, t2, _ = np.linalg.solve(system_of_equations, origin_diff)
                except np.linalg.LinAlgError:
                    return None  # The lines do not intersect

                # Calculate the intersection point
                intersection_point = p1 + t1 * d1
                return Vector(*intersection_point)

        elif plane is not None:
            return plane.intersect(self)

        elif vector is not None:
            # Create a vector from the origin to the point
            vec_to_point: Vector = vector - self.position

            # Project the vector onto the direction of the axis
            projected_length = vec_to_point.dot(self.direction)
            projected_vec = self.direction * projected_length + self.position

            # Calculate the difference between the original vector and the projected vector
            if vector == projected_vec:
                return vector

        elif location is not None:
            # Find the "direction" of the location
            location_dir = Plane(location).z_dir

            # Is the location on the axis with the same direction?
            if (
                self.intersect(location.position) is not None
                and location_dir == self.direction
            ):
                return location

        elif shape is not None:
            return shape.intersect(self)


class BoundBox:
    """A BoundingBox for a Shape"""

    def __init__(self, bounding_box: Bnd_Box) -> None:
        self.wrapped: Bnd_Box = bounding_box
        x_min, y_min, z_min, x_max, y_max, z_max = bounding_box.Get()
        self.min = Vector(x_min, y_min, z_min)  #: location of minimum corner
        self.max = Vector(x_max, y_max, z_max)  #: location of maximum corner
        self.size = Vector(x_max - x_min, y_max - y_min, z_max - z_min)  #: overall size

    @property
    def diagonal(self) -> float:
        """body diagonal length (i.e. object maximum size)"""
        return self.wrapped.SquareExtent() ** 0.5

    def __repr__(self):
        """Display bounding box parameters"""
        return (
            f"bbox: {self.min.X} <= x <= {self.max.X}, {self.min.Y} <= y <= {self.max.Y}, "
            f"{self.min.Z} <= z <= {self.max.Z}"
        )

    def center(self) -> Vector:
        """Return center of the bounding box"""
        return (self.min + self.max) / 2

    def add(
        self,
        obj: Union[tuple[float, float, float], Vector, BoundBox],
        tol: float = None,
    ) -> BoundBox:
        """Returns a modified (expanded) bounding box

        obj can be one of several things:
            1. a 3-tuple corresponding to x,y, and z amounts to add
            2. a vector, containing the x,y,z values to add
            3. another bounding box, where a new box will be created that
               encloses both.

        This bounding box is not changed.

        Args:
          obj: Union[tuple[float:
          float:
          float]:
          Vector:
          BoundBox]:
          tol: float:  (Default value = None)

        Returns:

        """

        tol = TOL if tol is None else tol  # tol = TOL (by default)

        tmp = Bnd_Box()
        tmp.SetGap(tol)
        tmp.Add(self.wrapped)

        if isinstance(obj, tuple):
            tmp.Update(*obj)
        elif isinstance(obj, Vector):
            tmp.Update(*obj.to_tuple())
        elif isinstance(obj, BoundBox):
            tmp.Add(obj.wrapped)

        return BoundBox(tmp)

    @staticmethod
    def find_outside_box_2d(bb1: BoundBox, bb2: BoundBox) -> Optional[BoundBox]:
        """Compares bounding boxes

        Compares bounding boxes. Returns none if neither is inside the other.
        Returns the outer one if either is outside the other.

        BoundBox.is_inside works in 3d, but this is a 2d bounding box, so it
        doesn't work correctly plus, there was all kinds of rounding error in
        the built-in implementation i do not understand.

        Args:
          bb1: BoundBox:
          bb2: BoundBox:

        Returns:

        """

        if (
            bb1.min.X < bb2.min.X
            and bb1.max.X > bb2.max.X
            and bb1.min.Y < bb2.min.Y
            and bb1.max.Y > bb2.max.Y
        ):
            result = bb1
        elif (
            bb2.min.X < bb1.min.X
            and bb2.max.X > bb1.max.X
            and bb2.min.Y < bb1.min.Y
            and bb2.max.Y > bb1.max.Y
        ):
            result = bb2
        else:
            result = None
        return result

    @classmethod
    def _from_topo_ds(
        cls,
        shape: TopoDS_Shape,
        tolerance: float = None,
        optimal: bool = True,
        oriented: bool = False,
    ) -> BoundBox:
        """Constructs a bounding box from a TopoDS_Shape

        Args:
            shape: TopoDS_Shape:
            tolerance: float:  (Default value = None)
            optimal: bool:  This algorithm builds precise bounding box (Default value = True)

        Returns:

        """
        BRepTools.Clean_s(shape)  # Remove mesh which may impact bbox

        tolerance = TOL if tolerance is None else tolerance  # tol = TOL (by default)
        bbox = Bnd_Box()
        bbox_obb = Bnd_OBB()

        if optimal:
            # this is 'exact' but expensive
            if oriented:
                BRepBndLib.AddOBB_s(shape, bbox_obb, False, True, False)
            else:
                BRepBndLib.AddOptimal_s(shape, bbox)
        else:
            mesh = BRepMesh_IncrementalMesh(shape, tolerance, True)
            mesh.Perform()
            # this is adds +margin but is faster
            if oriented:
                BRepBndLib.AddOBB_s(shape, bbox_obb)
            else:
                BRepBndLib.Add_s(shape, bbox, True)

        return cls(bbox_obb) if oriented else cls(bbox)

    def is_inside(self, second_box: BoundBox) -> bool:
        """Is the provided bounding box inside this one?

        Args:
          b2: BoundBox:

        Returns:

        """
        return not (
            second_box.min.X > self.min.X
            and second_box.min.Y > self.min.Y
            and second_box.min.Z > self.min.Z
            and second_box.max.X < self.max.X
            and second_box.max.Y < self.max.Y
            and second_box.max.Z < self.max.Z
        )

    def to_align_offset(self, align: Tuple[float, float]) -> Tuple[float, float]:
        """Amount to move object to achieve the desired alignment"""
        align_offset = []
        for i in range(2):
            if align[i] == Align.MIN:
                align_offset.append(-self.min.to_tuple()[i])
            elif align[i] == Align.CENTER:
                align_offset.append(
                    -(self.min.to_tuple()[i] + self.max.to_tuple()[i]) / 2
                )
            elif align[i] == Align.MAX:
                align_offset.append(-self.max.to_tuple()[i])
        return align_offset


class Color:
    """
    Color object based on OCCT Quantity_ColorRGBA.

    Attributes:
        wrapped (Quantity_ColorRGBA): the OCP color object
    """

    @overload
    def __init__(self, q_color: Quantity_ColorRGBA):
        """Color from OCCT color object

        Args:
            name (Quantity_ColorRGBA): q_color
        """

    @overload
    def __init__(self, name: str, alpha: float = 1.0):
        """Color from name

        `OCCT Color Names
            <https://dev.opencascade.org/doc/refman/html/_quantity___name_of_color_8hxx.html>`_

        Args:
            name (str): color, e.g. "blue"
        """

    @overload
    def __init__(self, red: float, green: float, blue: float, alpha: float = 1.0):
        """Color from RGBA and Alpha values

        Args:
            red (float): 0.0 <= red <= 1.0
            green (float): 0.0 <= green <= 1.0
            blue (float): 0.0 <= blue <= 1.0
            alpha (float, optional): 0.0 <= alpha <= 1.0. Defaults to 0.0.
        """

    @overload
    def __init__(self, color_code: int, alpha: int = 0xFF):
        """Color from a hexidecimal color code with an optional alpha value

        Args:
            color_code (hexidecimal int): 0xRRGGBB
            alpha (hexidecimal int): 0x00 <= alpha as hex <= 0xFF
        """

    def __init__(self, *args, **kwargs):
        # pylint: disable=too-many-branches
        red, green, blue, alpha, name, color_code, q_color = (
            1.0,
            1.0,
            1.0,
            1.0,
            None,
            None,
            None,
        )

        if len(args) == 1 or len(args) == 2:
            if isinstance(args[0], Quantity_ColorRGBA):
                q_color = args[0]
            elif isinstance(args[0], int):
                color_code = args[0]
                alpha = args[1] if len(args) == 2 else 0xFF
            elif isinstance(args[0], str):
                name = args[0]
                if len(args) == 2:
                    alpha = args[1]
        elif len(args) >= 3:
            red, green, blue = args[0:3]
        if len(args) == 4:
            alpha = args[3]

        color_code = kwargs.get("color_code", color_code)
        red = kwargs.get("red", red)
        green = kwargs.get("green", green)
        blue = kwargs.get("blue", blue)
        if color_code is None:
            alpha = kwargs.get("alpha", alpha)
        else:
            alpha = kwargs.get("alpha", alpha)
            alpha = alpha / 255

        if color_code is not None and isinstance(color_code, int):
            red, remainder = divmod(color_code, 256**2)
            green, blue = divmod(remainder, 256)
            red = red / 255
            green = green / 255
            blue = blue / 255

        if q_color is not None:
            self.wrapped = q_color
        elif name:
            self.wrapped = Quantity_ColorRGBA()
            exists = Quantity_ColorRGBA.ColorFromName_s(args[0], self.wrapped)
            if not exists:
                raise ValueError(f"Unknown color name: {name}")
            self.wrapped.SetAlpha(alpha)
        else:
            self.wrapped = Quantity_ColorRGBA(red, green, blue, alpha)

        self.iter_index = 0

    def __iter__(self):
        """Initialize to beginning"""
        self.iter_index = 0
        return self

    def __next__(self):
        """return the next value"""
        rgb = self.wrapped.GetRGB()
        rgb_tuple = (rgb.Red(), rgb.Green(), rgb.Blue(), self.wrapped.Alpha())

        if self.iter_index > 3:
            raise StopIteration
        else:
            value = rgb_tuple[self.iter_index]
            self.iter_index += 1
        return value

    # @deprecated
    def to_tuple(self):
        """Value as tuple"""
        return tuple(self)

    def __copy__(self) -> Color:
        """Return copy of self"""
        return Color(*tuple(self))

    def __deepcopy__(self, _memo) -> Color:
        """Return deepcopy of self"""
        return Color(*tuple(self))

    def __str__(self) -> str:
        """Generate string"""
        quantity_color_enum = self.wrapped.GetRGB().Name()
        quantity_color_str = Quantity_Color.StringName_s(quantity_color_enum)
        return f"Color: {str(tuple(self))} ~ {quantity_color_str}"

    def __repr__(self) -> str:
        """Color repr"""
        return f"Color{str(tuple(self))}"


class Location:
    """Location in 3D space. Depending on usage can be absolute or relative.

    This class wraps the TopLoc_Location class from OCCT. It can be used to move Shape
    objects in both relative and absolute manner. It is the preferred type to locate objects
    in build123d.

    Attributes:
        wrapped (TopLoc_Location): the OCP location object

    """

    _rot_order_dict = {
        Intrinsic.XYZ: gp_EulerSequence.gp_Intrinsic_XYZ,
        Intrinsic.XZY: gp_EulerSequence.gp_Intrinsic_XZY,
        Intrinsic.YZX: gp_EulerSequence.gp_Intrinsic_YZX,
        Intrinsic.YXZ: gp_EulerSequence.gp_Intrinsic_YXZ,
        Intrinsic.ZXY: gp_EulerSequence.gp_Intrinsic_ZXY,
        Intrinsic.ZYX: gp_EulerSequence.gp_Intrinsic_ZYX,
        Intrinsic.XYX: gp_EulerSequence.gp_Intrinsic_XYX,
        Intrinsic.XZX: gp_EulerSequence.gp_Intrinsic_XZX,
        Intrinsic.YZY: gp_EulerSequence.gp_Intrinsic_YZY,
        Intrinsic.YXY: gp_EulerSequence.gp_Intrinsic_YXY,
        Intrinsic.ZXZ: gp_EulerSequence.gp_Intrinsic_ZXZ,
        Intrinsic.ZYZ: gp_EulerSequence.gp_Intrinsic_ZYZ,
        Extrinsic.XYZ: gp_EulerSequence.gp_Extrinsic_XYZ,
        Extrinsic.XZY: gp_EulerSequence.gp_Extrinsic_XZY,
        Extrinsic.YZX: gp_EulerSequence.gp_Extrinsic_YZX,
        Extrinsic.YXZ: gp_EulerSequence.gp_Extrinsic_YXZ,
        Extrinsic.ZXY: gp_EulerSequence.gp_Extrinsic_ZXY,
        Extrinsic.ZYX: gp_EulerSequence.gp_Extrinsic_ZYX,
        Extrinsic.XYX: gp_EulerSequence.gp_Extrinsic_XYX,
        Extrinsic.XZX: gp_EulerSequence.gp_Extrinsic_XZX,
        Extrinsic.YZY: gp_EulerSequence.gp_Extrinsic_YZY,
        Extrinsic.YXY: gp_EulerSequence.gp_Extrinsic_YXY,
        Extrinsic.ZXZ: gp_EulerSequence.gp_Extrinsic_ZXZ,
        Extrinsic.ZYZ: gp_EulerSequence.gp_Extrinsic_ZYZ,
    }

    @property
    def position(self) -> Vector:
        """Extract Position component of self

        Returns:
          Vector: Position part of Location

        """
        return Vector(self.to_tuple()[0])

    @position.setter
    def position(self, value: VectorLike):
        """Set the position component of this Location

        Args:
            value (VectorLike): New position
        """
        trsf_position = gp_Trsf()
        trsf_position.SetTranslationPart(Vector(value).wrapped)
        trsf_orientation = gp_Trsf()
        trsf_orientation.SetRotation(self.wrapped.Transformation().GetRotation())
        self.wrapped = TopLoc_Location(trsf_position * trsf_orientation)

    @property
    def orientation(self) -> Vector:
        """Extract orientation/rotation component of self

        Returns:
          Vector: orientation part of Location

        """
        return Vector(self.to_tuple()[1])

    @orientation.setter
    def orientation(self, rotation: VectorLike):
        """Set the orientation component of this Location

        Args:
            rotation (VectorLike): Intrinsic XYZ angles in degrees
        """

        ordering = Intrinsic.XYZ

        position_xyz = self.wrapped.Transformation().TranslationPart()
        trsf_position = gp_Trsf()
        trsf_position.SetTranslationPart(
            gp_Vec(position_xyz.X(), position_xyz.Y(), position_xyz.Z())
        )
        rotation = [radians(a) for a in rotation]
        quaternion = gp_Quaternion()
        quaternion.SetEulerAngles(self._rot_order_dict[ordering], *rotation)
        trsf_orientation = gp_Trsf()
        trsf_orientation.SetRotation(quaternion)
        self.wrapped = TopLoc_Location(trsf_position * trsf_orientation)

    @property
    def x_axis(self) -> Axis:
        """Default X axis when used as a plane"""
        plane = Plane(self)
        return Axis(plane.origin, plane.x_dir)

    @property
    def y_axis(self) -> Axis:
        """Default Y axis when used as a plane"""
        plane = Plane(self)
        return Axis(plane.origin, plane.y_dir)

    @property
    def z_axis(self) -> Axis:
        """Default Z axis when used as a plane"""
        plane = Plane(self)
        return Axis(plane.origin, plane.z_dir)

    @overload
    def __init__(self):  # pragma: no cover
        """Empty location with not rotation or translation with respect to the original location."""

    @overload
    def __init__(self, location: Location):  # pragma: no cover
        """Location with another given location."""

    @overload
    def __init__(self, translation: VectorLike, angle: float = 0):  # pragma: no cover
        """Location with translation with respect to the original location.
        If angle != 0 then the location includes a rotation around z-axis by angle"""

    @overload
    def __init__(
        self, translation: VectorLike, rotation: RotationLike = None
    ):  # pragma: no cover
        """Location with translation with respect to the original location.
        If rotation is not None then the location includes the rotation (see also Rotation class)
        """

    @overload
    def __init__(
        self,
        translation: VectorLike,
        rotation: RotationLike,
        ordering: Union[Extrinsic, Intrinsic],
    ):  # pragma: no cover
        """Location with translation with respect to the original location.
        If rotation is not None then the location includes the rotation (see also Rotation class)
        ordering defaults to Intrinsic.XYZ, but can also be set to Extrinsic
        """

    @overload
    def __init__(self, plane: Plane):  # pragma: no cover
        """Location corresponding to the location of the Plane."""

    @overload
    def __init__(self, plane: Plane, plane_offset: VectorLike):  # pragma: no cover
        """Location corresponding to the angular location of the Plane with
        translation plane_offset."""

    @overload
    def __init__(self, top_loc: TopLoc_Location):  # pragma: no cover
        """Location wrapping the low-level TopLoc_Location object t"""

    @overload
    def __init__(self, gp_trsf: gp_Trsf):  # pragma: no cover
        """Location wrapping the low-level gp_Trsf object t"""

    @overload
    def __init__(
        self, translation: VectorLike, direction: VectorLike, angle: float
    ):  # pragma: no cover
        """Location with translation t and rotation around direction by angle
        with respect to the original location."""

    def __init__(self, *args):
        # pylint: disable=too-many-branches
        transform = gp_Trsf()

        if len(args) == 0:
            pass

        elif len(args) == 1:
            translation = args[0]

            if isinstance(translation, (Vector, Iterable)):
                transform.SetTranslationPart(Vector(translation).wrapped)
            elif isinstance(translation, Plane):
                coordinate_system = gp_Ax3(
                    translation._origin.to_pnt(),
                    translation.z_dir.to_dir(),
                    translation.x_dir.to_dir(),
                )
                transform.SetTransformation(coordinate_system)
                transform.Invert()
            elif isinstance(args[0], Location):
                self.wrapped = translation.wrapped
                return
            elif isinstance(translation, TopLoc_Location):
                self.wrapped = translation
                return
            elif isinstance(translation, gp_Trsf):
                transform = translation
            else:
                raise TypeError("Unexpected parameters")

        elif len(args) == 2:
            ordering = Intrinsic.XYZ
            if isinstance(args[0], (Vector, Iterable)):
                if isinstance(args[1], (Vector, Iterable)):
                    rotation = [radians(a) for a in args[1]]
                    quaternion = gp_Quaternion()
                    quaternion.SetEulerAngles(self._rot_order_dict[ordering], *rotation)
                    transform.SetRotation(quaternion)
                elif isinstance(args[0], (Vector, tuple)) and isinstance(
                    args[1], (int, float)
                ):
                    angle = radians(args[1])
                    quaternion = gp_Quaternion()
                    quaternion.SetEulerAngles(
                        self._rot_order_dict[ordering], 0, 0, angle
                    )
                    transform.SetRotation(quaternion)

                # set translation part after setting rotation (if exists)
                transform.SetTranslationPart(Vector(args[0]).wrapped)
            else:
                translation, origin = args
                coordinate_system = gp_Ax3(
                    Vector(origin).to_pnt(),
                    translation.z_dir.to_dir(),
                    translation.x_dir.to_dir(),
                )
                transform.SetTransformation(coordinate_system)
                transform.Invert()
        elif len(args) == 3:
            if (
                isinstance(args[0], (Vector, Iterable))
                and isinstance(args[1], (Vector, Iterable))
                and isinstance(args[2], (int, float))
            ):
                translation, axis, angle = args
                transform.SetRotation(
                    gp_Ax1(Vector().to_pnt(), Vector(axis).to_dir()), angle * pi / 180.0
                )
            elif (
                isinstance(args[0], (Vector, Iterable))
                and isinstance(args[1], (Vector, Iterable))
                and isinstance(args[2], (Extrinsic, Intrinsic))
            ):
                translation = args[0]
                rotation = [radians(a) for a in args[1]]
                ordering = args[2]
                quaternion = gp_Quaternion()
                quaternion.SetEulerAngles(self._rot_order_dict[ordering], *rotation)
                transform.SetRotation(quaternion)
            else:
                raise TypeError("Unsupported argument types for Location")

            transform.SetTranslationPart(Vector(translation).wrapped)
        self.wrapped = TopLoc_Location(transform)

    def inverse(self) -> Location:
        """Inverted location"""
        return Location(self.wrapped.Inverted())

    def __copy__(self) -> Location:
        """Lib/copy.py shallow copy"""
        return Location(self.wrapped.Transformation())

    def __deepcopy__(self, _memo) -> Location:
        """Lib/copy.py deep copy"""
        return Location(self.wrapped.Transformation())

    T = TypeVar("T", bound=Union["Location", "Shape"])

    def __mul__(self, other: T) -> T:
        """Combine locations"""
        if hasattr(other, "wrapped") and not isinstance(
            other.wrapped, TopLoc_Location
        ):  # Shape
            result = other.moved(self)
        elif isinstance(other, Iterable) and all(
            isinstance(o, Location) for o in other
        ):
            result = [Location(self.wrapped * loc.wrapped) for loc in other]
        else:
            result = Location(self.wrapped * other.wrapped)
        return result

    def __pow__(self, exponent: int) -> Location:
        return Location(self.wrapped.Powered(exponent))

    def __eq__(self, other: Location) -> bool:
        """Compare Locations"""
        if not isinstance(other, Location):
            raise ValueError("other must be a Location")
        quaternion1 = gp_Quaternion()
        quaternion1.SetEulerAngles(
            gp_EulerSequence.gp_Intrinsic_XYZ,
            radians(self.orientation.X),
            radians(self.orientation.Y),
            radians(self.orientation.Z),
        )
        quaternion2 = gp_Quaternion()
        quaternion2.SetEulerAngles(
            gp_EulerSequence.gp_Intrinsic_XYZ,
            radians(other.orientation.X),
            radians(other.orientation.Y),
            radians(other.orientation.Z),
        )
        return self.position == other.position and quaternion1.IsEqual(quaternion2)

    def __neg__(self) -> Location:
        """Flip the orientation without changing the position operator -"""
        return Location(-Plane(self))

    def __and__(self: Plane, other: Union[Axis, Location, Plane, VectorLike, "Shape"]):
        """intersect axis with other &"""
        return self.intersect(other)

    def to_axis(self) -> Axis:
        """Convert the location into an Axis"""
        return Axis.Z.located(self)

    def to_tuple(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Convert the location to a translation, rotation tuple."""

        transformation = self.wrapped.Transformation()
        trans = transformation.TranslationPart()
        rot = transformation.GetRotation()

        rv_trans = (trans.X(), trans.Y(), trans.Z())
        rv_rot = [
            degrees(a) for a in rot.GetEulerAngles(gp_EulerSequence.gp_Intrinsic_XYZ)
        ]

        return rv_trans, tuple(rv_rot)

    def __repr__(self):
        """To String

        Convert Location to String for display

        Returns:
            Location as String
        """
        position_str = ", ".join((f"{v:.2f}" for v in self.to_tuple()[0]))
        orientation_str = ", ".join((f"{v:.2f}" for v in self.to_tuple()[1]))
        return f"(p=({position_str}), o=({orientation_str}))"

    def __str__(self):
        """To String

        Convert Location to String for display

        Returns:
            Location as String
        """
        position_str = ", ".join((f"{v:.2f}" for v in self.to_tuple()[0]))
        orientation_str = ", ".join((f"{v:.2f}" for v in self.to_tuple()[1]))
        return f"Location: (position=({position_str}), orientation=({orientation_str}))"

    @overload
    def intersect(self, vector: VectorLike) -> Union[Vector, None]:
        """Find intersection of vector and location"""

    @overload
    def intersect(self, location: Location) -> Union[Location, None]:
        """Find intersection of location and location"""

    @overload
    def intersect(self, axis: Axis) -> Union[Location, None]:
        """Find intersection of axis and location"""

    @overload
    def intersect(self, plane: Plane) -> Union[Location, None]:
        """Find intersection of plane and location"""

    def intersect(self, *args, **kwargs):
        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            return axis.intersect(self)

        elif plane is not None:
            return plane.intersect(self)

        elif vector is not None and self.position == vector:
            return vector

        elif location is not None and self == location:
            return self

        elif shape is not None:
            return shape.intersect(self)


class LocationEncoder(json.JSONEncoder):
    """Custom JSON Encoder for Location values

    Example:

    .. code::

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
        json_object = json.dumps(data_dict, indent=4, cls=LocationEncoder)
        with open("sample.json", "w") as outfile:
            outfile.write(json_object)
        with open("sample.json", "r") as infile:
            copy_data_dict = json.load(infile, object_hook=LocationEncoder.location_hook)

    """

    def default(self, o: Location) -> dict:
        """Return a serializable object"""
        if not isinstance(o, Location):
            raise TypeError("Only applies to Location objects")
        return {"Location": o.to_tuple()}

    @staticmethod
    def location_hook(obj) -> dict:
        """Convert Locations loaded from json to Location objects

        Example:
            read_json = json.load(infile, object_hook=LocationEncoder.location_hook)
        """
        if "Location" in obj:
            obj = Location(*[[float(f) for f in v] for v in obj["Location"]])
        return obj


class Rotation(Location):
    """Subclass of Location used only for object rotation

    Attributes:
        X (float): rotation in degrees about X axis
        Y (float): rotation in degrees about Y axis
        Z (float): rotation in degrees about Z axis
        optionally specify rotation ordering with Intrinsic or Extrinsic enums, defaults to Intrinsic.XYZ

    """

    @overload
    def __init__(
        self,
        rotation: RotationLike,
        ordering: Union[Extrinsic, Intrinsic] == Intrinsic.XYZ,
    ):
        """Subclass of Location used only for object rotation
        ordering is for order of rotations in Intrinsic or Extrinsic enums"""

    @overload
    def __init__(
        self,
        X: float = 0,
        Y: float = 0,
        Z: float = 0,
        ordering: Union[Extrinsic, Intrinsic] = Intrinsic.XYZ,
    ):
        """Subclass of Location used only for object rotation
        ordering is for order of rotations in Intrinsic or Extrinsic enums"""

    def __init__(self, *args, **kwargs):
        if not all(key in ("X", "Y", "Z", "rotation", "ordering") for key in kwargs):
            raise TypeError("Invalid key for Rotation")
        angles, rotations, orderings = [0, 0, 0], [], []
        if args:
            angles = list(filter(lambda item: isinstance(item, (int, float)), args))
            vectors = list(filter(lambda item: isinstance(item, Vector), args))
            tuples = list(filter(lambda item: isinstance(item, tuple), args))
            if tuples:
                angles = list(*tuples)
            if vectors:
                angles = vectors[0].to_tuple()
            if len(angles) < 3:
                angles.extend([0.0] * (3 - len(angles)))
            rotations = list(filter(lambda item: isinstance(item, Rotation), args))
            orderings = list(
                filter(lambda item: isinstance(item, (Extrinsic, Intrinsic)), args)
            )
        kwargs.setdefault("X", angles[0])
        kwargs.setdefault("Y", angles[1])
        kwargs.setdefault("Z", angles[2])
        kwargs.setdefault("ordering", orderings[0] if orderings else Intrinsic.XYZ)
        if rotations:
            super().__init__(rotations[0])
        else:
            super().__init__(
                (0, 0, 0), (kwargs["X"], kwargs["Y"], kwargs["Z"]), kwargs["ordering"]
            )


Rot = Rotation  # Short form for Algebra users who like compact notation

#:TypeVar("RotationLike"): Three tuple of angles about x, y, z or Rotation
RotationLike = Union[tuple[float, float, float], Rotation]


class Pos(Location):
    """A position only sub-class of Location"""

    @overload
    def __init__(self, v: VectorLike):
        """Position by VectorLike"""

    @overload
    def __init__(self, v: Iterable):
        """Position by Vertex"""

    @overload
    def __init__(self, X: float = 0, Y: float = 0, Z: float = 0):
        """Position by X, Y, Z"""

    def __init__(self, *args, **kwargs):
        position = [0, 0, 0]
        # VectorLike
        if len(args) == 1 and isinstance(args[0], (tuple, Vector)):
            position = list(args[0])
        # Vertex
        elif len(args) == 1 and isinstance(args[0], Iterable):
            position = list(args[0])
        # Values
        elif 1 <= len(args) <= 3 and all([isinstance(v, (float, int)) for v in args]):
            position = list(args) + [0] * (3 - len(args))

        unknown_args = ", ".join(set(kwargs.keys()).difference(["v", "X", "Y", "Z"]))
        if unknown_args:
            raise ValueError(f"Unexpected argument(s) {unknown_args}")

        if "X" in kwargs:
            position[0] = kwargs["X"]
        if "Y" in kwargs:
            position[1] = kwargs["Y"]
        if "Z" in kwargs:
            position[2] = kwargs["Z"]

        super().__init__(tuple(position))


class Matrix:
    """A 3d , 4x4 transformation matrix.

    Used to move geometry in space.

    The provided "matrix" parameter may be None, a gp_GTrsf, or a nested list of
    values.

    If given a nested list, it is expected to be of the form:

        [[m11, m12, m13, m14],
         [m21, m22, m23, m24],
         [m31, m32, m33, m34]]

    A fourth row may be given, but it is expected to be: [0.0, 0.0, 0.0, 1.0]
    since this is a transform matrix.

    Attributes:
        wrapped (gp_GTrsf): the OCP transformation function
    """

    @overload
    def __init__(self) -> None:  # pragma: no cover
        ...

    @overload
    def __init__(self, matrix: Union[gp_GTrsf, gp_Trsf]) -> None:  # pragma: no cover
        ...

    @overload
    def __init__(self, matrix: Sequence[Sequence[float]]) -> None:  # pragma: no cover
        ...

    def __init__(self, matrix=None):
        if matrix is None:
            self.wrapped = gp_GTrsf()
        elif isinstance(matrix, gp_GTrsf):
            self.wrapped = matrix
        elif isinstance(matrix, gp_Trsf):
            self.wrapped = gp_GTrsf(matrix)
        elif isinstance(matrix, (list, tuple)):
            # Validate matrix size & 4x4 last row value
            valid_sizes = all(
                (isinstance(row, (list, tuple)) and (len(row) == 4)) for row in matrix
            ) and len(matrix) in (3, 4)
            if not valid_sizes:
                raise TypeError(
                    f"Matrix constructor requires 2d list of 4x3 or 4x4, but got: {repr(matrix)}"
                )
            if (len(matrix) == 4) and (tuple(matrix[3]) != (0, 0, 0, 1)):
                raise ValueError(
                    f"Expected the last row to be [0,0,0,1], but got: {repr(matrix[3])}"
                )

            # Assign values to matrix
            self.wrapped = gp_GTrsf()
            for i, row in enumerate(matrix[:3]):
                for j, element in enumerate(row):
                    self.wrapped.SetValue(i + 1, j + 1, element)

        else:
            raise TypeError(f"Invalid param to matrix constructor: {matrix}")

    def rotate(self, axis: Axis, angle: float):
        """General rotate about axis"""
        new = gp_Trsf()
        new.SetRotation(axis.wrapped, angle)
        self.wrapped = self.wrapped * gp_GTrsf(new)

    def inverse(self) -> Matrix:
        """Invert Matrix"""
        return Matrix(self.wrapped.Inverted())

    @overload
    def multiply(self, other: Vector) -> Vector:  # pragma: no cover
        ...

    @overload
    def multiply(self, other: Matrix) -> Matrix:  # pragma: no cover
        ...

    def multiply(self, other):
        """Matrix multiplication"""
        if isinstance(other, Vector):
            return other.transform(self)

        return Matrix(self.wrapped.Multiplied(other.wrapped))

    def transposed_list(self) -> Sequence[float]:
        """Needed by the cqparts gltf exporter"""

        trsf = self.wrapped
        data = [[trsf.Value(i, j) for j in range(1, 5)] for i in range(1, 4)] + [
            [0.0, 0.0, 0.0, 1.0]
        ]

        return [data[j][i] for i in range(4) for j in range(4)]

    def __copy__(self) -> Matrix:
        """Return copy of self"""
        return Matrix(self.wrapped.Trsf())

    def __deepcopy__(self, _memo) -> Matrix:
        """Return deepcopy of self"""
        return Matrix(self.wrapped.Trsf())

    def __getitem__(self, row_col: tuple[int, int]) -> float:
        """Provide Matrix[r, c] syntax for accessing individual values. The row
        and column parameters start at zero, which is consistent with most
        python libraries, but is counter to gp_GTrsf(), which is 1-indexed.
        """
        if not isinstance(row_col, tuple) or (len(row_col) != 2):
            raise IndexError("Matrix subscript must provide (row, column)")
        (row, col) = row_col
        if not ((0 <= row <= 3) and (0 <= col <= 3)):
            raise IndexError(f"Out of bounds access into 4x4 matrix: {repr(row_col)}")
        if row < 3:
            return_value = self.wrapped.Value(row + 1, col + 1)
        else:
            # gp_GTrsf doesn't provide access to the 4th row because it has
            # an implied value as below:
            return_value = [0.0, 0.0, 0.0, 1.0][col]
        return return_value

    def __repr__(self) -> str:
        """
        Generate a valid python expression representing this Matrix
        """
        matrix_transposed = self.transposed_list()
        matrix_str = ",\n        ".join(str(matrix_transposed[i::4]) for i in range(4))
        return f"Matrix([{matrix_str}])"


class PlaneMeta(type):
    """Plane meta class to enable class properties"""

    @property
    def XY(cls) -> Plane:
        """XY Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, 0, 1))

    @property
    def YZ(cls) -> Plane:
        """YZ Plane"""
        return Plane((0, 0, 0), (0, 1, 0), (1, 0, 0))

    @property
    def ZX(cls) -> Plane:
        """ZX Plane"""
        return Plane((0, 0, 0), (0, 0, 1), (0, 1, 0))

    @property
    def XZ(cls) -> Plane:
        """XZ Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, -1, 0))

    @property
    def YX(cls) -> Plane:
        """YX Plane"""
        return Plane((0, 0, 0), (0, 1, 0), (0, 0, -1))

    @property
    def ZY(cls) -> Plane:
        """ZY Plane"""
        return Plane((0, 0, 0), (0, 0, 1), (-1, 0, 0))

    @property
    def front(cls) -> Plane:
        """Front Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, -1, 0))

    @property
    def back(cls) -> Plane:
        """Back Plane"""
        return Plane((0, 0, 0), (-1, 0, 0), (0, 1, 0))

    @property
    def left(cls) -> Plane:
        """Left Plane"""
        return Plane((0, 0, 0), (0, -1, 0), (-1, 0, 0))

    @property
    def right(cls) -> Plane:
        """Right Plane"""
        return Plane((0, 0, 0), (0, 1, 0), (1, 0, 0))

    @property
    def top(cls) -> Plane:
        """Top Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, 0, 1))

    @property
    def bottom(cls) -> Plane:
        """Bottom Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, 0, -1))

    @property
    def isometric(cls) -> Plane:
        """Isometric Plane"""
        return Plane(
            (0, 0, 0),
            (1 / 2**0.5, 1 / 2**0.5, 0),
            (1 / 3**0.5, -1 / 3**0.5, 1 / 3**0.5),
        )


class Plane(metaclass=PlaneMeta):
    """Plane

    A plane is positioned in space with a coordinate system such that the plane is defined by
    the origin, x_dir (X direction), y_dir (Y direction), and z_dir (Z direction) of this coordinate
    system, which is the "local coordinate system" of the plane. The z_dir is a vector normal to the
    plane. The coordinate system is right-handed.

    A plane allows the use of local 2D coordinates, which are later converted to
    global, 3d coordinates when the operations are complete.

    Planes can be created from faces as workplanes for feature creation on objects.

    =======   ====== ====== ======
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
    =======   ====== ====== ======

    Args:
        gp_pln (gp_Pln): an OCCT plane object
        origin (Union[tuple[float, float, float], Vector]): the origin in global coordinates
        x_dir (Union[tuple[float, float, float], Vector], optional): an optional vector
            representing the X Direction. Defaults to None.
        z_dir (Union[tuple[float, float, float], Vector], optional): the normal direction
            for the plane. Defaults to (0, 0, 1).

    Attributes:
        origin (Vector): global position of local (0,0,0) point
        x_dir (Vector): x direction
        y_dir (Vector): y direction
        z_dir (Vector): z direction
        local_coord_system (gp_Ax3): OCP coordinate system
        forward_transform (Matrix): forward location transformation matrix
        reverse_transform (Matrix): reverse location transformation matrix
        wrapped (gp_Pln): the OCP plane object

    Raises:
        ValueError: z_dir must be non null
        ValueError: x_dir must be non null
        ValueError: the specified x_dir is not orthogonal to the provided normal

    Returns:
        Plane: A plane

    """

    # pylint: disable=too-many-instance-attributes
    @staticmethod
    def get_topods_face_normal(face: TopoDS_Face) -> Vector:
        """Find the normal at the center of a TopoDS_Face"""
        gp_pnt = gp_Pnt()
        normal = gp_Vec()
        projector = GeomAPI_ProjectPointOnSurf(gp_pnt, BRep_Tool.Surface_s(face))
        u_val, v_val = projector.LowerDistanceParameters()
        BRepGProp_Face(face).Normal(u_val, v_val, gp_pnt, normal)
        return Vector(normal)

    @overload
    def __init__(self, gp_pln: gp_Pln):  # pragma: no cover
        """Return a plane from a OCCT gp_pln"""

    @overload
    def __init__(
        self, face: "Face", x_dir: Optional[VectorLike] = None
    ):  # pragma: no cover
        """Return a plane extending the face.
        Note: for non planar face this will return the underlying work plane"""

    @overload
    def __init__(self, location: Location):  # pragma: no cover
        """Return a plane aligned with a given location"""

    @overload
    def __init__(
        self,
        origin: VectorLike,
        x_dir: VectorLike = None,
        z_dir: VectorLike = (0, 0, 1),
    ):  # pragma: no cover
        """Return a new plane at origin with x_dir and z_dir"""

    def __init__(self, *args, **kwargs):
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Create a plane from either an OCCT gp_pln or coordinates"""

        def optarg(kwargs, name, args, index, default):
            if name in kwargs:
                return kwargs[name]
            if len(args) > index:
                return args[index]
            return default

        arg_plane = None
        arg_face = None
        arg_location = None
        arg_origin = None
        arg_x_dir = None
        arg_z_dir = (0, 0, 1)

        arg0 = args[0] if args else None
        type_error_message = "Expected gp_Pln, Face, Location, or VectorLike"

        if "gp_pln" in kwargs:
            arg_plane = kwargs["gp_pln"]
        elif isinstance(arg0, gp_Pln):
            arg_plane = arg0
        elif "face" in kwargs:
            arg_face = kwargs["face"]
            arg_x_dir = kwargs.get("x_dir", None)
        # Check for Face by using the OCCT class to avoid circular imports of the Face class
        elif hasattr(arg0, "wrapped") and isinstance(arg0.wrapped, TopoDS_Face):
            arg_face = arg0
            arg_x_dir = optarg(kwargs, "x_dir", args, 1, arg_x_dir)
        elif "location" in kwargs:
            arg_location = kwargs["location"]
        elif isinstance(arg0, Location):
            arg_location = arg0
        elif "origin" in kwargs:
            arg_origin = kwargs["origin"]
            arg_x_dir = kwargs.get("x_dir", arg_x_dir)
            arg_z_dir = kwargs.get("z_dir", arg_z_dir)
        else:
            try:
                arg_origin = Vector(arg0)
            except TypeError as exc:
                raise TypeError(type_error_message) from exc
            arg_x_dir = optarg(kwargs, "x_dir", args, 1, arg_x_dir)
            arg_z_dir = optarg(kwargs, "z_dir", args, 2, arg_z_dir)

        if arg_plane:
            self.wrapped = arg_plane
        elif arg_face:
            # Determine if face is planar
            surface = BRep_Tool.Surface_s(arg_face.wrapped)
            if not isinstance(surface, Geom_Plane):
                raise ValueError("Planes can only be created from planar faces")
            properties = GProp_GProps()
            BRepGProp.SurfaceProperties_s(arg_face.wrapped, properties)
            self._origin = Vector(properties.CentreOfMass())
            self.x_dir = (
                Vector(arg_x_dir)
                if arg_x_dir
                else Vector(
                    BRep_Tool.Surface_s(arg_face.wrapped).Position().XDirection()
                )
            )
            self.x_dir = Vector(round(i, 14) for i in self.x_dir)
            self.z_dir = Plane.get_topods_face_normal(arg_face.wrapped)
            self.z_dir = Vector(round(i, 14) for i in self.z_dir)
        elif arg_location:
            topo_face = BRepBuilderAPI_MakeFace(
                Plane.XY.wrapped, -1.0, 1.0, -1.0, 1.0
            ).Face()
            topo_face.Move(arg_location.wrapped)
            self._origin = arg_location.position
            self.x_dir = Vector(BRep_Tool.Surface_s(topo_face).Position().XDirection())
            self.x_dir = Vector(round(i, 14) for i in self.x_dir)
            self.z_dir = Plane.get_topods_face_normal(topo_face)
            self.z_dir = Vector(round(i, 14) for i in self.z_dir)
        elif arg_origin:
            self._origin = Vector(arg_origin)
            self.x_dir = Vector(arg_x_dir) if arg_x_dir else None
            self.z_dir = Vector(arg_z_dir)

        if hasattr(self, "wrapped"):
            self._origin = Vector(self.wrapped.Location())
            self.x_dir = Vector(self.wrapped.XAxis().Direction())
            self.y_dir = Vector(self.wrapped.YAxis().Direction())
            self.z_dir = Vector(self.wrapped.Axis().Direction())
        else:
            if self.z_dir.length == 0.0:
                raise ValueError("z_dir must be non null")
            self.z_dir = self.z_dir.normalized()

            if not self.x_dir:
                ax3 = gp_Ax3(self._origin.to_pnt(), self.z_dir.to_dir())
                self.x_dir = Vector(ax3.XDirection()).normalized()
            else:
                if Vector(self.x_dir).length == 0.0:
                    raise ValueError("x_dir must be non null")
                self.x_dir = Vector(self.x_dir).normalized()
            self.y_dir = self.z_dir.cross(self.x_dir).normalized()
            self.wrapped = gp_Pln(
                gp_Ax3(self._origin.to_pnt(), self.z_dir.to_dir(), self.x_dir.to_dir())
            )
        self.local_coord_system: gp_Ax3 = None
        self.reverse_transform: Matrix = None
        self.forward_transform: Matrix = None
        self.origin = self._origin  # set origin to calculate transformations

    def offset(self, amount: float) -> Plane:
        """Move the Plane by amount in the direction of z_dir"""
        return Plane(
            origin=self.origin + self.z_dir * amount, x_dir=self.x_dir, z_dir=self.z_dir
        )

    def _eq_iter(self, other: Plane):
        """Iterator to successively test equality

        Args:
            other: Plane to compare to

        Returns:
            Are planes equal
        """
        # equality tolerances
        eq_tolerance_origin = 1e-6
        eq_tolerance_dot = 1e-6

        yield isinstance(other, Plane)  # comparison is with another Plane
        # origins are the same
        yield abs(self._origin - other.origin) < eq_tolerance_origin
        # z-axis vectors are parallel (assumption: both are unit vectors)
        yield abs(self.z_dir.dot(other.z_dir) - 1) < eq_tolerance_dot
        # x-axis vectors are parallel (assumption: both are unit vectors)
        yield abs(self.x_dir.dot(other.x_dir) - 1) < eq_tolerance_dot

    def __copy__(self) -> Plane:
        """Return copy of self"""
        return Plane(gp_Pln(self.wrapped.Position()))

    def __deepcopy__(self, _memo) -> Plane:
        """Return deepcopy of self"""
        return Plane(gp_Pln(self.wrapped.Position()))

    def __eq__(self, other: Plane):
        """Are planes equal operator =="""
        return all(self._eq_iter(other))

    def __ne__(self, other: Plane):
        """Are planes not equal operator !+"""
        return not self.__eq__(other)

    def __neg__(self) -> Plane:
        """Reverse z direction of plane operator -"""
        return Plane(self.origin, self.x_dir, -self.z_dir)

    def __mul__(
        self, other: Union[Location, "Shape"]
    ) -> Union[Plane, List[Plane], "Shape"]:
        if isinstance(other, Location):
            result = Plane(self.location * other)
        elif (  # LocationList
            hasattr(other, "local_locations") and hasattr(other, "location_index")
        ) or (  # tuple of locations
            isinstance(other, (list, tuple))
            and all([isinstance(o, Location) for o in other])
        ):
            result = [self * loc for loc in other]
        elif hasattr(other, "wrapped") and not isinstance(other, Vector):  # Shape
            result = self.location * other

        else:
            raise TypeError(
                "Planes can only be multiplied with Locations or Shapes to relocate them"
            )
        return result

    def __and__(self: Plane, other: Union[Axis, Location, Plane, VectorLike, "Shape"]):
        """intersect plane with other &"""
        return self.intersect(other)

    def __repr__(self):
        """To String

        Convert Plane to String for display

        Returns:
            Plane as String
        """
        origin_str = ", ".join((f"{v:.2f}" for v in self._origin.to_tuple()))
        x_dir_str = ", ".join((f"{v:.2f}" for v in self.x_dir.to_tuple()))
        z_dir_str = ", ".join((f"{v:.2f}" for v in self.z_dir.to_tuple()))
        return f"Plane(o=({origin_str}), x=({x_dir_str}), z=({z_dir_str}))"

    def reverse(self) -> Plane:
        """Reverse z direction of plane"""
        return -self

    @property
    def origin(self) -> Vector:
        """Get the Plane origin"""
        return self._origin

    @origin.setter
    def origin(self, value):
        """Set the Plane origin"""
        self._origin = Vector(value)
        self._calc_transforms()
        self.wrapped = gp_Pln(
            gp_Ax3(self._origin.to_pnt(), self.z_dir.to_dir(), self.x_dir.to_dir())
        )

    def shift_origin(self, locator: Union[Axis, VectorLike, "Vertex"]) -> Plane:
        """shift plane origin

        Creates a new plane with the origin moved within the plane to the point of intersection
        of the axis or at the given Vertex. The plane's x_dir and z_dir are unchanged.

        Args:
            locator (Union[Axis, VectorLike, Vertex]): Either Axis that intersects the new
                plane origin or Vertex within Plane.

        Raises:
            ValueError: Vertex isn't within plane
            ValueError: Point isn't within plane
            ValueError: Axis doesn't intersect plane

        Returns:
            Plane: plane with new origin

        """
        if type(locator).__name__ == "Vertex":
            new_origin = tuple(locator)
            if not self.contains(new_origin):
                raise ValueError(f"{locator} is not located within plane")
        elif isinstance(locator, (tuple, Vector)):
            new_origin = Vector(locator)
            if not self.contains(locator):
                raise ValueError(f"{locator} is not located within plane")
        elif isinstance(locator, Axis):
            new_origin = self.intersect(locator)
            if new_origin is None:
                raise ValueError(f"{locator} doesn't intersect the plane")
        else:
            raise TypeError(f"Invalid locate type: {type(locator)}")
        return Plane(origin=new_origin, x_dir=self.x_dir, z_dir=self.z_dir)

    def rotated(
        self,
        rotation: VectorLike = (0, 0, 0),
        ordering: Union[Extrinsic, Intrinsic] = None,
    ) -> Plane:
        """Returns a copy of this plane, rotated about the specified axes

        Since the z axis is always normal the plane, rotating around Z will
        always produce a plane that is parallel to this one.

        The origin of the workplane is unaffected by the rotation.

        Rotations are done in order x, y, z. If you need a different order,
        manually chain together multiple rotate() commands.

        Args:
            rotation (VectorLike, optional): (xDegrees, yDegrees, zDegrees). Defaults to (0, 0, 0).
            ordering (Union[Intrinsic, Extrinsic], optional): order of rotations in Intrinsic or Extrinsic rotation mode, defaults to Intrinsic.XYZ

        Returns:
            Plane: a copy of this plane rotated as requested.
        """

        if ordering is None:
            ordering = Intrinsic.XYZ

        # Note: this is not a geometric Vector
        rotation = [radians(a) for a in rotation]
        quaternion = gp_Quaternion()
        quaternion.SetEulerAngles(Location._rot_order_dict[ordering], *rotation)
        trsf_rotation = gp_Trsf()
        trsf_rotation.SetRotation(quaternion)
        transformation = Matrix(gp_GTrsf(trsf_rotation))

        # Compute the new plane.
        new_x_dir = self.x_dir.transform(transformation)
        new_z_dir = self.z_dir.transform(transformation)

        return Plane(self._origin, new_x_dir, new_z_dir)

    def move(self, loc: Location) -> Plane:
        """Change the position & orientation of self by applying a relative location

        Args:
            loc (Location): relative change

        Returns:
            Plane: relocated plane
        """
        self_copy = copy.deepcopy(self)
        self_copy.wrapped.Transform(loc.wrapped.Transformation())
        return Plane(self_copy.wrapped)

    def _calc_transforms(self):
        """Computes transformation matrices to convert between local and global coordinates."""
        # reverse_transform is the forward transformation matrix from world to local coordinates
        # ok i will be really honest, i cannot understand exactly why this works
        # something bout the order of the translation and the rotation.
        # the double-inverting is strange, and I don't understand it.
        forward = Matrix()
        inverse = Matrix()

        forward_t = gp_Trsf()
        inverse_t = gp_Trsf()

        global_coord_system = gp_Ax3()
        local_coord_system = gp_Ax3(
            gp_Pnt(*self._origin.to_tuple()),
            gp_Dir(*self.z_dir.to_tuple()),
            gp_Dir(*self.x_dir.to_tuple()),
        )

        forward_t.SetTransformation(global_coord_system, local_coord_system)
        forward.wrapped = gp_GTrsf(forward_t)

        inverse_t.SetTransformation(local_coord_system, global_coord_system)
        inverse.wrapped = gp_GTrsf(inverse_t)

        self.local_coord_system: gp_Ax3 = local_coord_system
        self.reverse_transform: Matrix = inverse
        self.forward_transform: Matrix = forward

    @property
    def location(self) -> Location:
        """Return Location representing the origin and z direction"""
        return Location(self)

    def to_gp_ax2(self) -> gp_Ax2:
        """Return gp_Ax2 version of the plane"""
        axis = gp_Ax2()
        axis.SetAxis(gp_Ax1(self.origin.to_pnt(), self.z_dir.to_dir()))
        axis.SetXDirection(self.x_dir.to_dir())
        return axis

    def _to_from_local_coords(
        self, obj: Union[VectorLike, Any, BoundBox], to_from: bool = True
    ):
        """_to_from_local_coords

        Reposition the object relative to this plane

        Args:
            obj (Union[VectorLike, Shape, BoundBox]): an object to reposition. Note that
            type Any refers to all topological classes.
            to_from (bool, optional): direction of transformation. Defaults to True (to).

        Raises:
            ValueError: Unsupported object type

        Returns:
            an object of the same type, but repositioned to local coordinates
        """

        transform_matrix = self.forward_transform if to_from else self.reverse_transform

        if isinstance(obj, (tuple, Vector)):
            return_value = Vector(obj).transform(transform_matrix)
        elif isinstance(obj, BoundBox):
            global_bottom_left = Vector(obj.min.X, obj.min.Y, obj.min.Z)
            global_top_right = Vector(obj.max.X, obj.max.Y, obj.max.Z)
            local_bottom_left = global_bottom_left.transform(transform_matrix)
            local_top_right = global_top_right.transform(transform_matrix)
            local_bbox = Bnd_Box(
                gp_Pnt(*local_bottom_left.to_tuple()),
                gp_Pnt(*local_top_right.to_tuple()),
            )
            return_value = BoundBox(local_bbox)
        elif hasattr(obj, "wrapped"):  # Shapes
            return_value = obj.transform_shape(transform_matrix)
        else:
            raise ValueError(
                f"Unable to repositioned type {type(obj)} with respect to local coordinates"
            )
        return return_value

    def to_local_coords(self, obj: Union[VectorLike, Any, BoundBox]):
        """Reposition the object relative to this plane

        Args:
            obj: Union[VectorLike, Shape, BoundBox] an object to reposition. Note that
            type Any refers to all topological classes.

        Returns:
            an object of the same type, but repositioned to local coordinates

        """
        return self._to_from_local_coords(obj, True)

    def from_local_coords(self, obj: Union[tuple, Vector, Any, BoundBox]):
        """Reposition the object relative from this plane

        Args:
            obj: Union[VectorLike, Shape, BoundBox] an object to reposition. Note that
            type Any refers to all topological classes.

        Returns:
            an object of the same type, but repositioned to world coordinates

        """
        return self._to_from_local_coords(obj, False)

    def location_between(self, other: Plane) -> Location:
        """Return a location representing the translation from self to other"""

        transformation = gp_Trsf()
        transformation.SetTransformation(
            self.wrapped.Position(), other.wrapped.Position()
        )
        return Location(transformation)

    def contains(
        self, obj: Union[VectorLike, Axis], tolerance: float = TOLERANCE
    ) -> bool:
        """contains

        Is this point or Axis fully contained in this plane?

        Args:
            obj (Union[VectorLike,Axis]): point or Axis to  evaluate
            tolerance (float, optional): comparison tolerance. Defaults to TOLERANCE.

        Returns:
            bool: self contains point or Axis

        """
        if isinstance(obj, Axis):
            return_value = self.wrapped.Contains(
                gp_Lin(obj.position.to_pnt(), obj.direction.to_dir()),
                tolerance,
                tolerance,
            )
        else:
            return_value = self.wrapped.Contains(Vector(obj).to_pnt(), tolerance)
        return return_value

    @overload
    def intersect(self, vector: VectorLike) -> Union[Vector, None]:
        """Find intersection of vector and plane"""

    @overload
    def intersect(self, location: Location) -> Union[Location, None]:
        """Find intersection of location and plane"""

    @overload
    def intersect(self, axis: Axis) -> Union[Axis, Vector, None]:
        """Find intersection of axis and plane"""

    @overload
    def intersect(self, plane: Plane) -> Union[Axis, None]:
        """Find intersection of plane and plane"""

    @overload
    def intersect(self, shape: "Shape") -> Union["Shape", None]:
        """Find intersection of plane and shape"""

    def intersect(self, *args, **kwargs):

        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            if self.contains(axis):
                return axis
            else:
                geom_line = Geom_Line(axis.wrapped)
                geom_plane = Geom_Plane(self.local_coord_system)

                intersection_calculator = GeomAPI_IntCS(geom_line, geom_plane)

                if (
                    intersection_calculator.IsDone()
                    and intersection_calculator.NbPoints() == 1
                ):
                    # Get the intersection point
                    intersection_point = Vector(intersection_calculator.Point(1))
                else:
                    intersection_point = None

                return intersection_point

        elif plane is not None:
            surface1 = Geom_Plane(self.wrapped)
            surface2 = Geom_Plane(plane.wrapped)
            intersector = GeomAPI_IntSS(surface1, surface2, TOLERANCE)
            if intersector.IsDone() and intersector.NbLines() > 0:
                # Get the intersection line (axis)
                intersection_line = intersector.Line(1)
                # Extract the axis from the intersection line
                axis = intersection_line.Position()
                return Axis(axis)

        elif vector is not None and self.contains(vector):
            return vector

        elif location is not None:
            pln = Plane(location)
            if pln.origin == self.origin and pln.z_dir == self.z_dir:
                return location

        elif shape is not None:
            return shape.intersect(self)
