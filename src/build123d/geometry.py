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
import colorsys
import copy as copy_module
import itertools
import json
import logging
import warnings
from collections.abc import Callable, Iterable, Sequence
from math import degrees, log10, pi, prod, radians
from typing import TYPE_CHECKING, Any, Type, TypeAlias, cast, overload

import numpy as np
from typing_extensions import deprecated
import webcolors  # type: ignore
from OCP.Bnd import Bnd_Box, Bnd_OBB
from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.BRepGProp import BRepGProp, BRepGProp_Face  # used for mass calculation
from OCP.BRepTools import BRepTools
from OCP.Geom import Geom_BoundedSurface, Geom_ElementarySurface, Geom_Line, Geom_Plane
from OCP.GeomAPI import GeomAPI_IntCS, GeomAPI_IntSS, GeomAPI_ProjectPointOnSurf
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
from OCP.Quantity import Quantity_Color, Quantity_ColorRGBA, Quantity_TypeOfColor
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Shape, TopoDS_Vertex

from build123d.build_enums import Align, Align2DType, Align3DType, Extrinsic, Intrinsic

if TYPE_CHECKING:  # pragma: no cover
    from .topology import Edge, Face, Shape, Vertex

# Create a build123d logger to distinguish these logs from application logs.
# If the user doesn't configure logging, all build123d logs will be discarded.
logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")

TOLERANCE = 1e-6
TOL_DIGITS = abs(int(log10(TOLERANCE)))
TOL = 1e-2
DEG2RAD = pi / 180.0
RAD2DEG = 180 / pi
GEOM_KEY_DIGITS = TOL_DIGITS - 1


def _rounded_key(
    values: Iterable[float], digits: int = GEOM_KEY_DIGITS
) -> tuple[float, ...]:
    """Return a rounded tuple key for geometry equality and hashing."""
    return tuple(round(value, digits) for value in values)


def _canonical_quaternion_key(
    quaternion: gp_Quaternion, digits: int = GEOM_KEY_DIGITS
) -> tuple[float, ...]:
    """Return a rounded quaternion key with a canonical sign."""
    components = [quaternion.X(), quaternion.Y(), quaternion.Z(), quaternion.W()]
    for value in components:
        if abs(value) > TOLERANCE:
            if value < 0:
                components = [-component for component in components]
            break
    return _rounded_key(components, digits)


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
        vec (Vector |  Sequence(float) |  gp_Vec |  gp_Pnt |  gp_Dir |  gp_XYZ): vector
            representations

    Note that if no z value is provided it's assumed to be zero. If no values are provided
    the returned Vector has the value of 0, 0, 0.

    Attributes:
        wrapped (gp_Vec): the OCP vector object

    """

    # Note: Vector can't be made into a Sequence as NumPy attempts to be "helpful" by
    # auto-converting array-like objects (objects with __len__() and indexing) into NumPy
    # arrays during certain arithmetic operations.

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
    def __init__(self, v: gp_Vec | gp_Pnt | gp_Dir | gp_XYZ):  # pragma: no cover
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
        return iter((self.X, self.Y, self.Z))

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

    @deprecated(
        "to_tuple is deprecated and will be removed in a future version. "
        " Use 'tuple(Vector)' instead."
    )
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

    def get_signed_angle(self, vec: Vector, normal: Vector | None = None) -> float:
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

    def __and__(self, other: Axis | Location | Plane | VectorLike | Shape):
        """intersect vector with other &"""
        return self.intersect(other)

    def __format__(self, spec) -> str:
        """Format Vector"""

        def trim_float(x: float, precision: int) -> float:
            return round(x, precision) if abs(x) > TOLERANCE else 0.0

        last_char = spec[-1] if spec else None
        if last_char in ("f", "g"):
            if "." in spec:
                precision = int(spec[:-1].split(".")[-1])
            else:
                precision = 6 if last_char == "f" else 12

            x = trim_float(self.X, precision)
            y = trim_float(self.Y, precision)
            z = trim_float(self.Z, precision)

            return f"({x:{spec}}, {y:{spec}}, {z:{spec}})"

        return str(tuple(self))

    def __repr__(self) -> str:
        """Represent Vector"""
        return f"{type(self).__name__}{self:.13g}"

    def __str__(self) -> str:
        """Display Vector"""
        x, y, z = format(self, ".6g")[1:-1].split(", ")
        return f"{type(self).__name__}: (X={x}, Y={y}, Z={z})"

    def __eq__(self, other: object) -> bool:
        """Vectors equal operator =="""
        if not isinstance(other, Vector):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        """Hash of Vector"""
        return hash(self._key())

    def _key(self) -> tuple[float, ...]:
        """Canonical key used for equality and hashing."""
        return _rounded_key((self.X, self.Y, self.Z))

    def __round__(self, ndigits: int | None = None):
        return Vector(
            round(self.X, ndigits), round(self.Y, ndigits), round(self.Z, ndigits)
        )

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
            # to gp_Pnt to obey build123d transformation convention (in OCP.vectors do not
            # translate)
            pnt = self.to_pnt()
            pnt_t = pnt.Transformed(affine_transform.wrapped.Trsf())
            return_value = Vector(gp_Vec(pnt_t.XYZ()))
        else:
            # to gp_Dir for transformation of "direction vectors" (no translation or scaling)
            gp_dir = self.to_dir()
            dir_t = gp_dir.Transformed(affine_transform.wrapped.Trsf())
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
    def intersect(self, vector: VectorLike) -> Vector | None:
        """Find intersection of vector and vector"""

    @overload
    def intersect(self, location: Location) -> Vector | None:
        """Find intersection of vector and location"""

    @overload
    def intersect(self, axis: Axis) -> Vector | None:
        """Find intersection of vector and axis"""

    @overload
    def intersect(self, plane: Plane) -> Vector | None:
        """Find intersection of vector and plane"""

    @overload
    def intersect(self, shape: Shape) -> Shape | None:
        """Find intersection of vector and shape"""

    def intersect(self, *args, **kwargs):
        """Find intersection of vector and geometric object or shape"""
        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            return axis.intersect(self)

        if plane is not None:
            return plane.intersect(self)

        if vector is not None and self == vector:
            return vector

        if location is not None:
            return location.intersect(self)

        if shape is not None:
            return shape.intersect(self)

        return None


VectorLike: TypeAlias = (
    Vector | tuple[float, float] | tuple[float, float, float] | Sequence[float]
)
"""
VectorLike: Represents a position in space.

- `Vector`: A vector object from `build123d`.
- `tuple[float, float]`: A 2D coordinate (x, y).
- `tuple[float, float, float]`: A 3D coordinate (x, y, z).
- `Sequence[float]`: A general sequence of floats (e.g., for higher dimensions).
"""


class AxisMeta(type):
    """Axis meta class to enable class properties"""

    @property
    def X(cls) -> Axis:
        """X Axis"""
        return cls((0, 0, 0), (1, 0, 0))

    @property
    def Y(cls) -> Axis:
        """Y Axis"""
        return cls((0, 0, 0), (0, 1, 0))

    @property
    def Z(cls) -> Axis:
        """Z Axis"""
        return cls((0, 0, 0), (0, 0, 1))


class Axis(metaclass=AxisMeta):
    """Axis

    Axis defined by point and direction

    Args:
        origin (VectorLike): start point
        direction (VectorLike): direction
        edge (Edge): origin & direction defined by start of edge
        location (Location): location to convert to axis

    Attributes:
        position (Vector): the global position of the axis origin
        direction (Vector): the normalized direction vector
        wrapped (gp_Ax1): the OCP axis object
    """

    _dim = 1

    @overload
    def __init__(self, gp_ax1: gp_Ax1) -> None:
        """Axis: point and direction"""

    @overload
    def __init__(self, location: Location) -> None:
        """Axis from location"""

    @overload
    def __init__(self, origin: VectorLike, direction: VectorLike) -> None:
        """Axis: point and direction"""

    @overload
    def __init__(self, edge: Edge) -> None:
        """Axis: start of Edge"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # pylint: disable=too-many-branches, too-many-locals

        gp_ax1 = kwargs.pop("gp_ax1", None)
        origin = kwargs.pop("origin", None)
        direction = kwargs.pop("direction", None)
        edge = kwargs.pop("edge", None)
        location = kwargs.pop("location", None)

        # Handle unexpected kwargs
        if kwargs:
            raise ValueError(f"Unexpected argument(s): {', '.join(kwargs.keys())}")

        # Handle positional arguments
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, gp_Ax1):
                gp_ax1 = arg
            elif isinstance(arg, Location):
                location = arg
            elif hasattr(arg, "wrapped") and isinstance(arg.wrapped, TopoDS_Edge):
                edge = arg
            elif isinstance(arg, (Vector, tuple)):
                origin = arg
            else:
                raise ValueError(f"Unrecognized single argument: {arg}")
        elif len(args) == 2:
            origin, direction = args

        # Handle edge-based construction
        if edge is not None:
            if not (hasattr(edge, "wrapped") and isinstance(edge.wrapped, TopoDS_Edge)):
                raise ValueError(f"Invalid edge argument: {edge}")

            topods_edge: TopoDS_Edge = edge.wrapped  # type: ignore[annotation-unchecked]
            curve = BRep_Tool.Curve_s(topods_edge, float(), float())
            param_min, _ = BRep_Tool.Range_s(topods_edge)
            origin_pnt = gp_Pnt()
            tangent_vec = gp_Vec()
            curve.D1(param_min, origin_pnt, tangent_vec)
            origin = Vector(origin_pnt)
            direction = Vector(gp_Dir(tangent_vec))

        # Convert location to axis
        if location is not None:
            gp_ax1 = Axis.Z.located(location).wrapped

        # Construct self.wrapped from gp_ax1 or origin/direction
        if gp_ax1 is None:
            try:
                origin_vector = Vector(origin)
                direction_vector = Vector(direction)
                gp_ax1 = gp_Ax1(
                    origin_vector.to_pnt(),
                    gp_Dir(*tuple(direction_vector.normalized())),
                )
            except Exception as exc:
                raise ValueError("Invalid Axis parameters") from exc
        elif not isinstance(gp_ax1, gp_Ax1):
            raise ValueError(f"Invalid Axis parameter: {gp_ax1}")

        self._wrapped: gp_Ax1 = gp_ax1

    @property
    def wrapped(self):
        return self._wrapped

    @property
    def position(self) -> Vector:
        """The position or origin of the Axis"""
        return Vector(self.wrapped.Location())

    @position.setter
    def position(self, position: VectorLike):
        """Set the position or origin of the Axis"""
        self.wrapped.SetLocation(Vector(position).to_pnt())

    @property
    def direction(self) -> Vector:
        """The normalized direction of the Axis"""
        return Vector(self.wrapped.Direction())

    @direction.setter
    def direction(self, direction: VectorLike):
        """Set the direction of the Axis"""
        self.wrapped.SetDirection(Vector(direction).to_dir())

    @property
    def location(self) -> Location:
        """Return self as Location"""
        return Location(Plane(origin=self.position, z_dir=self.direction))

    def __copy__(self) -> Axis:
        """Return copy of self"""
        return Axis(self.position, self.direction)

    def __deepcopy__(self, _memo) -> Axis:
        """Return deepcopy of self"""
        return Axis(self.position, self.direction)

    def __hash__(self) -> int:
        """Hash of Axis"""
        return hash(self._key())

    def __format__(self, spec) -> str:
        """Format Axis"""
        last_char = spec[-1] if spec else None
        if last_char in ("f", "g"):
            return f"({self.position:{spec}}, {self.direction:{spec}})"

        return f"({tuple(self.position)}, {tuple(self.direction)})"

    def __repr__(self) -> str:
        """Represent Axis"""
        return f"{type(self).__name__}{self:.{TOL_DIGITS}g}"

    def __str__(self) -> str:
        """Display Axis"""
        return (
            f"{type(self).__name__}: "
            f"(position={self.position:.{TOL_DIGITS}g}, direction={self.direction:.{TOL_DIGITS}g})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Axis):
            return NotImplemented
        return self._key() == other._key()

    def _key(self) -> tuple[tuple[float, ...], tuple[float, ...]]:
        """Canonical key used for equality and hashing."""
        return (self.position._key(), self.direction._key())

    def located(self, new_location: Location):
        """relocates self to a new location possibly changing position and direction"""
        top_location = new_location.wrapped
        self_gp_ax1: gp_Ax1 = self.wrapped
        new_gp_ax1: gp_Ax1 = self_gp_ax1.Transformed(top_location.Transformation())
        return Axis(new_gp_ax1)

    @deprecated(
        "to_tuple is deprecated and will be removed in a future version. "
        " Use 'Plane(Axis)' instead."
    )
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

    def is_skew(self, other: Axis, tolerance: float = 1e-5) -> bool:
        """are axes skew

        Returns True if this axis and another axis are skew, meaning they are neither
        parallel nor coplanar. Two axes are skew if they do not lie in the same plane
        and never intersect.

        Mathematically, this means:

        - The axes are **not parallel** (the cross product of their direction vectors
          is nonzero).

        - The axes are **not coplanar** (the vector between their positions is not
          aligned with the plane spanned by their directions).

        If either condition is false (i.e., the axes are parallel or coplanar), they are
        not skew.

        Args:
            other (Axis): axis to compare to
            tolerance (float, optional): max deviation. Defaults to 1e-5.

        Returns:
            bool: axes are skew
        """
        if self.is_parallel(other, tolerance):
            # If parallel, check if they are coincident
            parallel_offset = (self.position - other.position).cross(self.direction)
            # True if distinct, False if coincident
            return parallel_offset.length > tolerance

        # Compute the determinant
        coplanarity = (self.position - other.position).dot(
            self.direction.cross(other.direction)
        )

        # If determinant is near zero, they are coplanar; otherwise, they are skew
        return abs(coplanarity) > tolerance

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
        return type(self)(self.wrapped.Reversed())

    def __neg__(self) -> Axis:
        """Flip direction operator -"""
        return self.reverse()

    def __and__(
        self, other: Axis | Location | Plane | VectorLike | Shape
    ) -> Vector | Location | Axis | None:
        """intersect vector with other &"""
        return self.intersect(other)

    @overload
    def intersect(self, vector: VectorLike) -> Vector | None:
        """Find intersection of axis and vector"""

    @overload
    def intersect(self, location: Location) -> Vector | Location | None:
        """Find intersection of axis and location"""

    @overload
    def intersect(self, axis: Axis) -> Vector | Axis | None:
        """Find intersection of axis and axis"""

    @overload
    def intersect(self, plane: Plane) -> Vector | Axis | None:
        """Find intersection of axis and plane"""

    @overload
    def intersect(self, shape: Shape) -> Shape | None:
        """Find intersection of axis and shape"""

    def intersect(self, *args, **kwargs):
        """Find intersection of axis and geometric object or shape"""
        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            if self.is_coaxial(axis):
                return self

            if self.is_skew(axis):
                return None

            # Extract points and directions to numpy arrays
            p1 = np.array([*self.position])
            d1 = np.array([*self.direction])
            p2 = np.array([*axis.position])
            d2 = np.array([*axis.direction])

            # Solve the system of equations to find the intersection
            system_of_equations = np.array([d1, -d2, np.cross(d1, d2)]).T
            origin_diff = p2 - p1
            t1, _, _ = np.linalg.lstsq(system_of_equations, origin_diff, rcond=None)[0]

            # Calculate the intersection point
            intersection_point = p1 + t1 * d1
            return Vector(*intersection_point)

        if plane is not None:
            return plane.intersect(self)

        if vector is not None:
            # Create a vector from the origin to the point
            vec_to_point = vector - self.position

            # Project the vector onto the direction of the axis
            projected_length = vec_to_point.dot(self.direction)
            projected_vec = self.direction * projected_length + self.position

            # Calculate the difference between the original vector and the projected vector
            if vector == projected_vec:
                return vector

        if location is not None:
            # Find the "direction" of the location
            location_dir = Plane(location).z_dir

            if self.intersect(location.position) is not None:
                # Is the location on the axis with the same direction?
                if location_dir == self.direction:
                    return location
                else:
                    return location.position

        if shape is not None:
            return shape.intersect(self)

        return None


class BoundBox:
    """A BoundingBox for a Shape"""

    @overload
    def __init__(self, bounding_box: Bnd_Box) -> None:
        """Construct a bounding box from a Bnd_Box"""

    @overload
    def __init__(
        self, shape: TopoDS_Shape, tolerance: float | None = None, optimal: bool = True
    ) -> None:
        """Construct a bounding box from a TopoDS_Shape"""

    def __init__(self, *args, **kwargs):
        bounding_box = kwargs.pop("bounding_box", None)
        shape = kwargs.pop("shape", None)
        tolerance = kwargs.pop("tolerance", None)
        optimal = kwargs.pop("optimal", True)

        # If any unexpected kwargs remain
        if kwargs:
            raise TypeError(f"Unexpected keyword arguments: {', '.join(kwargs)}")

        # Fill from positional args if not given via kwargs
        if args:
            if bounding_box is None and isinstance(args[0], Bnd_Box):
                bounding_box = args[0]
            elif isinstance(args[0], TopoDS_Shape):
                shape = args[0]
                if len(args) > 1:
                    if isinstance(args[1], float):
                        tolerance = args[1]
                    elif args[1]:
                        raise TypeError(
                            f"Second parameter must be a float or None not {args[1]}"
                        )
                if len(args) > 2:
                    if not isinstance(args[2], bool):
                        raise TypeError(f"Third parameter must be a bool not {args[2]}")
                    optimal = args[2]
            else:
                raise TypeError(f"Invalid positional arguments: {', '.join(args)}")

        if shape:
            BRepTools.Clean_s(shape)  # Remove mesh which may impact bbox

            tolerance = (
                TOL if tolerance is None else tolerance
            )  # tol = TOL (by default)
            bounding_box = Bnd_Box()

            if optimal:
                BRepBndLib.AddOptimal_s(shape, bounding_box)
            else:
                BRepBndLib.Add_s(shape, bounding_box, True)

        if bounding_box.IsVoid():
            x_min, y_min, z_min, x_max, y_max, z_max = (0.0,) * 6
        else:
            x_min, y_min, z_min, x_max, y_max, z_max = bounding_box.Get()
        self.wrapped = None if bounding_box.IsVoid() else bounding_box
        self.min = Vector(x_min, y_min, z_min)  #: location of minimum corner
        self.max = Vector(x_max, y_max, z_max)  #: location of maximum corner
        self.size = Vector(x_max - x_min, y_max - y_min, z_max - z_min)  #: overall size

    @property
    def measure(self) -> float:
        """Return the overall Lebesgue measure of the bounding box.

        - For 1D objects: length
        - For 2D objects: area
        - For 3D objects: volume
        """
        return prod([x for x in self.size if x > TOLERANCE])

    @property
    def diagonal(self) -> float:
        """body diagonal length (i.e. object maximum size)"""
        if self.wrapped is None:
            return 0.0
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
        obj: tuple[float, float, float] | Vector | BoundBox,
        tol: float | None = None,
    ) -> BoundBox:
        """Returns a modified (expanded) bounding box

        obj can be one of several things:
            1. a 3-tuple corresponding to x,y, and z amounts to add
            2. a vector, containing the x,y,z values to add
            3. another bounding box, where a new box will be created that
               encloses both.

        This bounding box is not changed.

        Args:
          obj: tuple[float, float, float] | Vector | BoundBox]:
          tol: float:  (Default value = None)

        Returns:

        """

        tol = TOL if tol is None else tol  # tol = TOL (by default)

        tmp = Bnd_Box()
        tmp.SetGap(tol)
        if self.wrapped is not None:
            tmp.Add(self.wrapped)

        if isinstance(obj, tuple):
            tmp.Update(*obj)
        elif isinstance(obj, Vector):
            tmp.Update(*obj)
        elif isinstance(obj, BoundBox) and obj.wrapped is not None:
            tmp.Add(obj.wrapped)

        return BoundBox(tmp)

    @staticmethod
    def find_outside_box_2d(bb1: BoundBox, bb2: BoundBox) -> BoundBox | None:
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
    def from_topo_ds(
        cls,
        shape: TopoDS_Shape,
        tolerance: float | None = None,
        optimal: bool = True,
    ) -> BoundBox:
        """Constructs a bounding box from a TopoDS_Shape

        Args:
            shape: TopoDS_Shape:
            tolerance: float:  (Default value = None)
            optimal: bool:  This algorithm builds precise bounding box (Default value = True)

        Returns:

        """
        return cls(shape, tolerance, optimal)

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

    def overlaps(self, other: BoundBox, tolerance: float = TOLERANCE) -> bool:
        """Check if this bounding box overlaps with another.

        Args:
            other: BoundBox to check overlap with
            tolerance: Distance tolerance for overlap detection

        Returns:
            True if bounding boxes overlap (share any volume), False otherwise
        """
        if self.wrapped is None or other.wrapped is None:
            return False
        return self.wrapped.Distance(other.wrapped) <= tolerance

    def to_align_offset(self, align: Align2DType | Align3DType) -> Vector:
        """Amount to move object to achieve the desired alignment"""
        return to_align_offset(self.min, self.max, align)


class Color:
    """
    Color object based on OCCT Quantity_ColorRGBA.

    Attributes:
        wrapped (Quantity_ColorRGBA): the OCP color object
    """

    @overload
    def __init__(self, color_like: ColorLike):
        """Color from ColorLike

        Args:
            color_like (ColorLike):
                name, ex: "red" or "#ff0000",
                name + alpha, ex: ("red", 0.5) or "#ff000080",
                rgb, ex: (1., 0., 0.),
                rgb + alpha, ex: (1., 0., 0., 0.5),
                hex, ex: 0xff0000,
                hex + alpha, ex: (0xff0000, 0x80),
                Color,
                Quantity_ColorRGBA
        """

    @overload
    def __init__(self, name: str, alpha: float = 1.0):
        """Color from name or hexadecimal string

        `CSS3 Color Names
            <https://en.wikipedia.org/wiki/Web_colors#Extended_colors>`

        `OCCT Color Names
            <https://dev.opencascade.org/doc/refman/html/_quantity___name_of_color_8hxx.html>`_

        Hexadecimal string may be RGB or RGBA format with leading "#"

        Args:
            name (str): color, e.g. "blue" or "#0000ff""
            alpha (float, optional): 0.0 <= alpha <= 1.0. Defaults to 1.0
        """

    @overload
    def __init__(self, red: float, green: float, blue: float, alpha: float = 1.0):
        """Color from sRGB and Alpha values

        Args:
            red (float): 0.0 <= red <= 1.0
            green (float): 0.0 <= green <= 1.0
            blue (float): 0.0 <= blue <= 1.0
            alpha (float, optional): 0.0 <= alpha <= 1.0. Defaults to 1.0
        """

    @overload
    def __init__(self, color_code: int, alpha: int = 0xFF):
        """Color from a hexadecimal color code with an optional alpha value

        Args:
            color_code (hexadecimal int): 0xRRGGBB
            alpha (hexadecimal int): 0x00 <= alpha as hex <= 0xFF
        """

    def __init__(self, *args, **kwargs):
        self.wrapped = None
        red, green, blue, alpha, name, color_code = (1.0, 1.0, 1.0, 1.0, None, None)
        default_rgb = (red, green, blue, alpha)

        # Conform inputs to complete color_like tuples
        # color_like does not use other kwargs or args, but benefits from conformity
        color_like = kwargs.get("color_like", None)
        if color_like is not None:
            args = (color_like,)

        if args:
            args = args[0] if isinstance(args[0], tuple) else args

        # Fills missing defaults from b if a is short
        def fill_defaults(a, b):
            return tuple(a[i] if i < len(a) else b[i] for i in range(len(b)))

        if args:
            if len(args) >= 3:
                red, green, blue, alpha = fill_defaults(args, default_rgb)
            else:
                match args[0]:
                    case Color():
                        self.wrapped = args[0].wrapped
                        return
                    case Quantity_ColorRGBA():
                        self.wrapped = args[0]
                        return
                    case str():
                        name, alpha = fill_defaults(args, (name, alpha))
                        name = name.strip()
                        if "#" in name:
                            # extract alpha from hex string
                            hex_a = format(int(alpha * 255), "x")
                            if len(name) == 5:
                                hex_a = name[4] * 2
                                name = name[:4]
                            elif len(name) == 9:
                                hex_a = name[7:9]
                                name = name[:7]
                            elif len(name) not in [4, 5, 7, 9]:
                                raise ValueError(
                                    f'"{name}" is not a valid hexadecimal color value.'
                                )
                            try:
                                if hex_a:
                                    alpha = int(hex_a, 16) / 0xFF
                            except ValueError as ex:
                                raise ValueError(
                                    f"Invald alpha hex string: {hex_a}"
                                ) from ex
                    case int():
                        color_code, alpha = fill_defaults(args, (color_code, alpha))
                    case float():
                        red, green, blue, alpha = fill_defaults(args, default_rgb)
                    case _:
                        raise TypeError(f"Unsupported color definition: {args}")

        # Replace positional values with kwargs unless from color_like
        if color_like is None:
            name = kwargs.get("name", name)
            color_code = kwargs.get("color_code", color_code)
            red = kwargs.get("red", red)
            green = kwargs.get("green", green)
            blue = kwargs.get("blue", blue)
            alpha = kwargs.get("alpha", alpha)

        if name:
            color_format = (name, alpha)
        elif color_code:
            color_format = (color_code, alpha)
        else:
            color_format = (red, green, blue, alpha)

        # Convert color_format to rgb
        match color_format:
            case (name, a) if isinstance(name, str) and isinstance(a, (float, int)):
                red, green, blue = Color._rgb_from_str(name)
                alpha = a
            case (hexa, a) if isinstance(hexa, int) and isinstance(a, (float, int)):
                red, green, blue = Color._rgb_from_int(hexa)
                if a != 1:
                    # alpha == 1 is special case as default, don't divide
                    alpha = a / 0xFF
            case (red, green, blue, alpha) if all(
                isinstance(c, (int, float)) for c in (red, green, blue, alpha)
            ):
                pass
            case _:
                raise TypeError(f"Unsupported color definition: {color_format}")

        if not self.wrapped:
            the_color = Quantity_Color(
                red, green, blue, Quantity_TypeOfColor.Quantity_TOC_sRGB
            )
            self.wrapped = Quantity_ColorRGBA(the_color, alpha)

    def __iter__(self):
        r, g, b = self.wrapped.GetRGB().Values(Quantity_TypeOfColor.Quantity_TOC_sRGB)
        rgb_tuple = (r, g, b, self.wrapped.Alpha())
        return (round(value, 7) for value in rgb_tuple)

    def __copy__(self) -> Color:
        """Return copy of self"""
        return Color(*tuple(self))

    def __deepcopy__(self, _memo) -> Color:
        """Return deepcopy of self"""
        return Color(*tuple(self))

    def __str__(self) -> str:
        """Generate string"""
        rgb = self.wrapped.GetRGB().Values(Quantity_TypeOfColor.Quantity_TOC_sRGB)
        try:
            name = webcolors.rgb_to_name([round(c * 255) for c in rgb])
            qualifier = "is"
        except ValueError:
            # This still uses OCCT X11 colors instead of css3
            quantity_color_enum = self.wrapped.GetRGB().Name()
            name = Quantity_Color.StringName_s(quantity_color_enum)
            qualifier = "near"
        return f"{type(self).__name__}: {str(tuple(self))} {qualifier} {name.upper()!r}"

    def __repr__(self) -> str:
        """Represent Color"""
        return f"{type(self).__name__}{str(tuple(self))}"

    @classmethod
    def categorical_set(
        cls,
        color_count: int,
        starting_hue: ColorLike | float = 0.0,
        alpha: float | Iterable[float] = 1.0,
    ) -> list[Color]:
        """Generate a palette of evenly spaced colors.

        Creates a list of visually distinct colors suitable for representing
        discrete categories (such as different parts, assemblies, or data
        series). Colors are evenly spaced around the hue circle and share
        consistent lightness and saturation levels, resulting in balanced
        perceptual contrast across all hues.

        Produces palettes similar in appearance to the **Tableau 10** and **D3
        Category10** color sets—both widely recognized standards in data
        visualization for their clarity and accessibility. These values have
        been empirically chosen to maintain consistent perceived brightness
        across hues while avoiding overly vivid or dark colors.

        Args:
            color_count (int): Number of colors to generate.
            starting_hue (ColorLike | float): Either a Color-like object or
                a hue value in the range [0.0, 1.0] that defines the starting color.
            alpha (float | Iterable[float]): Alpha value(s) for the colors. Can be a
                single float or an iterable of length `color_count`.

        Returns:
            list[Color]: List of generated colors.

        Raises:
            ValueError: If starting_hue is out of range or alpha length mismatch.
        """

        # --- Determine starting hue ---
        if isinstance(starting_hue, float):
            if not (0.0 <= starting_hue <= 1.0):
                raise ValueError("Starting hue must be within range 0.0–1.0")
        elif isinstance(starting_hue, int):
            if starting_hue < 0:
                raise ValueError("Starting color integer must be non-negative")
            rgb = tuple(Color(starting_hue))[:3]
            starting_hue = colorsys.rgb_to_hls(*rgb)[0]
        else:
            raise TypeError(
                "Starting hue must be a float in [0,1] or an integer color literal"
            )

        # --- Normalize alpha values ---
        if isinstance(alpha, (float, int)):
            alphas = [float(alpha)] * color_count
        else:
            alphas = list(alpha)
            if len(alphas) != color_count:
                raise ValueError("Number of alpha values must match color_count")

        # --- Generate color list ---
        hues = np.linspace(
            starting_hue, starting_hue + 1.0, color_count, endpoint=False
        )
        colors = [
            cls(*colorsys.hls_to_rgb(h % 1.0, 0.55, 0.9), a)
            for h, a in zip(hues, alphas)
        ]

        return colors

    @staticmethod
    def _rgb_from_int(triplet: int) -> tuple[float, float, float]:
        red, remainder = divmod(triplet, 256**2)
        green, blue = divmod(remainder, 256)
        return red / 255, green / 255, blue / 255

    @staticmethod
    def _rgb_from_str(name: str) -> tuple:
        if "#" not in name:
            try:
                # Use css3 color names by default
                triplet = webcolors.name_to_rgb(name)
            except ValueError as exc:
                # Fall back to OCCT/X11 color names
                color = Quantity_Color()
                exists = Quantity_Color.ColorFromName_s(name, color)
                if not exists:
                    raise ValueError(
                        f"{name!r} is not defined as a named color in CSS3 or OCCT/X11"
                    ) from exc
                return (color.Red(), color.Green(), color.Blue())
        else:
            triplet = webcolors.hex_to_rgb(name)
        return tuple(i / 255 for i in tuple(triplet))


ColorLike: TypeAlias = (
    str  # name, ex: "red"
    | tuple[str, float | int]  # name + alpha, ex: ("red", 0.5)
    | tuple[float | int, float | int, float | int]  # rgb, ex: (1, 0, 0)
    | tuple[
        float | int, float | int, float | int, float | int
    ]  # rgb + alpha, ex: (1, 0, 0, 0.5)
    | int  # hex, ex: 0xff0000
    | tuple[int, int]  # hex + alpha, ex: (0xff0000, 0x80)
    | Color
    | Quantity_ColorRGBA  # OCP color
)


class GeomEncoder(json.JSONEncoder):
    """
    A JSON encoder for build123d geometry objects.

    This class extends ``json.JSONEncoder`` to provide custom serialization for
    geometry objects such as Axis, Color, Location, Plane, and Vector. It converts
    each geometry object into a dictionary containing exactly one key that identifies
    the geometry type (e.g. ``"Axis"``, ``"Vector"``, etc.), paired with a tuple or
    list that represents the underlying data. Any other object types are handled by
    the standard encoder.

    The inverse decoding is performed by the ``geometry_hook`` static method, which
    expects the dictionary to have precisely one key from the known geometry types.
    It then uses a class registry (``CLASS_REGISTRY``) to look up and instantiate
    the appropriate class with the provided values.

    **Usage Example**::

        import json

        # Suppose we have some geometry objects:
        axis = Axis(position=(0, 0, 0), direction=(1, 0, 0))
        vector = Vector(0.0, 1.0, 2.0)

        data = {
            "my_axis": axis,
            "my_vector": vector
        }

        # Encode them to JSON:
        encoded_data = json.dumps(data, cls=GeomEncoder, indent=4)

        # Decode them back:
        decoded_data = json.loads(encoded_data, object_hook=GeomEncoder.geometry_hook)

    """

    def default(self, o):
        """Return a JSON-serializable representation of a known geometry object."""
        if isinstance(o, Axis):
            return {"Axis": (tuple(o.position), tuple(o.direction))}
        if isinstance(o, Color):
            return {"Color": tuple(o)}
        if isinstance(o, Location):
            tup = tuple(o)
            return {"Location": (tuple(tup[0]), tuple(tup[1]))}
        if isinstance(o, Plane):
            return {"Plane": (tuple(o.origin), tuple(o.x_dir), tuple(o.z_dir))}
        if isinstance(o, Vector):
            return {"Vector": tuple(o)}
        # Let the base class default method raise the TypeError
        return super().default(o)

    @staticmethod
    def geometry_hook(json_dict):
        """Convert dictionaries back into geometry objects for decoding."""
        if len(json_dict.items()) != 1:
            raise ValueError(f"Invalid geometry json object {json_dict}")
        for key, value in json_dict.items():
            return CLASS_REGISTRY[key](*value)


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

    @overload
    def __init__(self) -> None:
        """Location with no position or orientation"""

    @overload
    def __init__(self, location: Location) -> None:
        """Location from Location"""

    @overload
    def __init__(self, position: VectorLike, angle: float = 0) -> None:
        """Location from position and rotation around z-axis by optional angle"""

    @overload
    def __init__(
        self, position: VectorLike, orientation: RotationLike | None = None
    ) -> None:
        """Location from position and optional orientation (see Rotation class)"""

    @overload
    def __init__(
        self,
        position: VectorLike,
        orientation: RotationLike,
        ordering: Extrinsic | Intrinsic,
    ) -> None:
        """Location from position and optional orientation (see Rotation class).
        Orientation determined by optional ordering, defaults to Intrinsic.XYZ
        """

    @overload
    def __init__(self, plane: Plane) -> None:
        """Location from location of Plane."""

    @overload
    def __init__(self, plane: Plane, plane_offset: VectorLike) -> None:
        """Location from location of Plane translated by plane_offset"""

    @overload
    def __init__(self, top_loc: TopLoc_Location) -> None:
        """Location from low-level TopLoc_Location object"""

    @overload
    def __init__(self, gp_trsf: gp_Trsf) -> None:
        """Location from low-level gp_Trsf object"""

    @overload
    def __init__(
        self, position: VectorLike, direction: VectorLike, angle: float
    ) -> None:
        """Location from position and rotation around direction by angle"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # pylint: disable=too-many-branches, too-many-locals, too-many-statements

        self.location_index = 0

        position = kwargs.pop("position", None)
        orientation = kwargs.pop("orientation", None)
        direction = kwargs.pop("direction", None)
        ordering = kwargs.pop("ordering", None)
        angle = kwargs.pop("angle", None)
        plane = kwargs.pop("plane", None)
        location = kwargs.pop("location", None)
        top_loc = kwargs.pop("top_loc", None)
        gp_trsf = kwargs.pop("gp_trsf", None)

        # If any unexpected kwargs remain
        if kwargs:
            raise TypeError(f"Unexpected keyword arguments: {', '.join(kwargs)}")

        # Fill from positional args if not given via kwargs
        if args:
            if plane is None and isinstance(args[0], Plane):
                plane = args[0]
            elif location is None and isinstance(args[0], (Location, Rotation)):
                location = args[0]
            elif top_loc is None and isinstance(args[0], TopLoc_Location):
                top_loc = args[0]
            elif gp_trsf is None and isinstance(args[0], gp_Trsf):
                gp_trsf = args[0]
            elif isinstance(args[0], (Vector, Iterable)):
                position = Vector(args[0])  # type: ignore
                if len(args) > 1:
                    if isinstance(args[1], (Vector, Iterable)):
                        orientation = Vector(args[1])  # type: ignore
                    elif isinstance(args[1], (int, float)):
                        angle = args[1]
                if len(args) > 2:
                    if isinstance(args[1], (Vector, Iterable)) and isinstance(
                        args[2], (int, float)
                    ):
                        direction = Vector(args[1])  # type: ignore
                        angle = args[2]
                    elif isinstance(args[2], (Intrinsic, Extrinsic)):
                        ordering = args[2]
                    else:
                        raise TypeError(
                            f"Third parameter must be a float or order not {args[2]}"
                        )
            else:
                raise TypeError(f"Invalid positional arguments: {args}")

        # Construct transformation
        trsf = gp_Trsf()

        if isinstance(plane, Plane):
            cs = gp_Ax3(
                plane.origin.to_pnt(),
                plane.z_dir.to_dir(),
                plane.x_dir.to_dir(),
            )
            trsf.SetTransformation(cs)
            trsf.Invert()

        elif isinstance(gp_trsf, gp_Trsf):
            trsf = gp_trsf

        elif angle is not None:
            axis = gp_Ax1(
                gp_Pnt(0, 0, 0),
                Vector(direction).to_dir() if direction else gp_Dir(0, 0, 1),
            )
            trsf.SetRotation(axis, radians(angle))

        elif orientation is not None:
            angles = [radians(a) for a in orientation]
            rot_order = self._rot_order_dict.get(
                ordering, gp_EulerSequence.gp_Intrinsic_XYZ
            )
            quat = gp_Quaternion()
            quat.SetEulerAngles(rot_order, *angles)
            trsf.SetRotation(quat)

        if position:
            trsf.SetTranslationPart(Vector(position).wrapped)

        # Final assignment based on input
        if isinstance(location, Location):
            self._wrapped = location.wrapped
        elif isinstance(top_loc, TopLoc_Location):
            self._wrapped = top_loc
        else:
            self._wrapped = TopLoc_Location(trsf)

    @property
    def wrapped(self) -> TopLoc_Location:
        return self._wrapped

    @property
    def position(self) -> Vector:
        """Extract Position component of self

        Returns:
          Vector: Position part of Location

        """
        return Vector(tuple(self)[0])

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
        self._wrapped = TopLoc_Location(trsf_position * trsf_orientation)

    @property
    def orientation(self) -> Vector:
        """Extract orientation/rotation component of self

        Returns:
          Vector: orientation part of Location

        """
        return Vector(tuple(self)[1])

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
        self._wrapped = TopLoc_Location(trsf_position * trsf_orientation)

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

    def inverse(self) -> Location:
        """Inverted location"""
        return Location(self.wrapped.Inverted())

    def __copy__(self) -> Location:
        """Lib/copy.py shallow copy"""
        return Location(self.wrapped.Transformation())

    def __deepcopy__(self, _memo) -> Location:
        """Lib/copy.py deep copy"""
        return Location(self.wrapped.Transformation())

    @overload
    def __mul__(self, other: Location) -> Location: ...

    @overload
    def __mul__(self, other: Iterable[Location]) -> list[Location]: ...

    def __mul__(
        self, other: Location | Iterable[Location]
    ) -> Location | list[Location]:
        """Combine locations"""

        if isinstance(other, Location):
            return Location(self.wrapped * other.wrapped)

        try:
            others = list(other)
            if all(isinstance(o, Location) for o in others):
                return [Location(self.wrapped * loc.wrapped) for loc in others]
        except TypeError:  # not iterable
            pass
        return NotImplemented  # will try Shape.__rmul__ for shapes

    def __pow__(self, exponent: int) -> Location:
        return Location(self.wrapped.Powered(exponent))

    def __eq__(self, other: object) -> bool:
        """Compare Locations"""
        if not isinstance(other, Location):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        """Hash of Location"""
        return hash(self._key())

    def _key(self) -> tuple[tuple[float, ...], tuple[float, ...]]:
        """Canonical key used for equality and hashing."""
        quaternion = self.wrapped.Transformation().GetRotation()
        return (self.position._key(), _canonical_quaternion_key(quaternion))

    def __iter__(self):
        transformation = self.wrapped.Transformation()
        trans = transformation.TranslationPart()
        rot = transformation.GetRotation()
        rv_trans: Vector = Vector(trans)
        rv_rot = Vector(
            map(degrees, rot.GetEulerAngles(gp_EulerSequence.gp_Intrinsic_XYZ))
        )  # type: ignore[assignment]
        return iter((rv_trans, rv_rot))

    def __neg__(self) -> Location:
        """Flip the orientation without changing the position operator -"""
        return Location(-Plane(self))

    def __and__(
        self, other: Axis | Location | Plane | VectorLike | Shape
    ) -> Vector | Location | None:
        """intersect axis with other &"""
        return self.intersect(other)

    def center(self) -> Vector:
        """Return center of the location - useful for sorting"""
        return self.position

    def mirror(self, mirror_plane: Plane) -> Location:
        """
        Return a new Location mirrored across the given plane.

        This method reflects both the position and orientation of the current Location
        across the specified mirror_plane using affine vector mathematics.

        Due to the mathematical properties of reflection:
            - The true mirror of a right-handed coordinate system is a *left-handed* one.

        However, `build123d` requires all coordinate systems to be right-handed.
        Therefore, this implementation:
        - Reflects the X and Z directions across the mirror plane
        - Recomputes the Y direction as: `Y = X × Z`

        This ensures the resulting Location maintains a valid right-handed frame,
        while remaining as close as possible to the geometric mirror.

        Args:
            mirror_plane (Plane): The plane to mirror across.

        Returns:
            Location: A new mirrored Location that preserves right-handedness.
        """

        def mirror_dir(v: Vector, pln: Plane) -> Vector:
            return v - 2 * (v.dot(pln.z_dir)) * pln.z_dir

        # Mirror the location position
        to_plane = self.position - mirror_plane.origin
        distance = to_plane.dot(mirror_plane.z_dir)
        pos = self.position - 2 * distance * mirror_plane.z_dir

        # Mirror the orientation
        loc_plane = Plane(self)
        mx_dir = mirror_dir(loc_plane.x_dir, mirror_plane)
        mz_dir = mirror_dir(loc_plane.z_dir, mirror_plane)

        return Location(Plane(origin=pos, x_dir=mx_dir, z_dir=mz_dir))

    @deprecated(
        "to_axis is deprecated and will be removed in a future version. "
        " Use 'Axis(Location)' instead."
    )
    def to_axis(self) -> Axis:
        """Convert the location into an Axis"""
        return Axis.Z.located(self)

    @deprecated(
        "to_tuple is deprecated and will be removed in a future version. "
        " Use 'tuple(Location)' instead."
    )
    def to_tuple(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Convert the location to a translation, rotation tuple."""
        transformation = self.wrapped.Transformation()
        trans = transformation.TranslationPart()
        rot = transformation.GetRotation()

        rv_trans: tuple[float, float, float] = (trans.X(), trans.Y(), trans.Z())
        rv_rot: tuple[float, float, float] = tuple(
            degrees(a) for a in rot.GetEulerAngles(gp_EulerSequence.gp_Intrinsic_XYZ)
        )  # type: ignore[assignment]

        return rv_trans, rv_rot

    def __format__(self, spec) -> str:
        """Format Location"""
        last_char = spec[-1] if spec else None
        if last_char in ("f", "g"):
            return f"({self.position:{spec}}, {self.orientation:{spec}})"

        return f"({tuple(self.position)}, {tuple(self.orientation)})"

    def __repr__(self) -> str:
        """Represent Location"""
        return f"{type(self).__name__}{self:.{TOL_DIGITS}g}"

    def __str__(self) -> str:
        """Display Location"""
        return (
            f"{type(self).__name__}: "
            f"(position={self.position:.{TOL_DIGITS}g}, "
            f"orientation={self.orientation:.{TOL_DIGITS}g})"
        )

    @overload
    def intersect(self, vector: VectorLike) -> Vector | None:
        """Find intersection of location and vector"""

    @overload
    def intersect(self, location: Location) -> Vector | Location | None:
        """Find intersection of location and location"""

    @overload
    def intersect(self, axis: Axis) -> Vector | Location | None:
        """Find intersection of location and axis"""

    @overload
    def intersect(self, plane: Plane) -> Vector | Location | None:
        """Find intersection of location and plane"""

    @overload
    def intersect(self, shape: Shape) -> Shape | None:
        """Find intersection of location and shape"""

    def intersect(self, *args, **kwargs):
        """Find intersection of location and geometric object or shape"""
        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            return axis.intersect(self)

        if plane is not None:
            return plane.intersect(self)

        if vector is not None and self.position == vector:
            return vector

        if location is not None:
            if self == location:
                return self
            elif self.position == location.position:
                return self.position

        if shape is not None:
            return shape.intersect(self)

        return None


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
        warnings.warn("Use GeomEncoder instead", DeprecationWarning, stacklevel=2)
        if not isinstance(o, Location):
            raise TypeError("Only applies to Location objects")
        return {"Location": o.to_tuple()}

    @staticmethod
    def location_hook(obj) -> dict:
        """Convert Locations loaded from json to Location objects

        Example:
            read_json = json.load(infile, object_hook=LocationEncoder.location_hook)
        """
        warnings.warn("Use GeomEncoder instead", DeprecationWarning, stacklevel=2)
        if "Location" in obj:
            obj = Location(*[[float(f) for f in v] for v in obj["Location"]])
        return obj


class OrientedBoundBox:
    """
    An Oriented Bounding Box

    This class computes the oriented bounding box for a given build123d shape.
    It exposes properties such as the center, principal axis directions, the
    extents along these axes, and the full diagonal length of the box.

    Note: The axes of the oriented bounding box are arbitrary and may not be
    consistent across platforms or time.
    """

    def __init__(self, shape: Bnd_OBB | Shape):
        """
        Create an oriented bounding box from either a precomputed Bnd_OBB or
        a build123d Shape (which wraps a TopoDS_Shape).

        Args:
            shape (Bnd_OBB | Shape): Either a precomputed Bnd_OBB or a build123d shape
                from which to compute the oriented bounding box.
        """
        if isinstance(shape, Bnd_OBB):
            obb = shape
        elif hasattr(shape, "wrapped") and isinstance(shape.wrapped, TopoDS_Shape):
            obb = Bnd_OBB()
            # Compute the oriented bounding box for the shape.
            BRepBndLib.AddOBB_s(shape.wrapped, obb, True)
        else:
            raise TypeError(f"Expected Bnd_OBB or Shape, got {type(shape).__name__}")
        self._wrapped = obb

    @property
    def wrapped(self):
        return self._wrapped

    @property
    def corners(self) -> list[Vector]:
        """
        Compute and return the unique corner points of the oriented bounding box
        in the coordinate system defined by the OBB's plane.

        For degenerate shapes (e.g. a line or a planar face), only the unique
        points are returned. For 2D shapes the corners are returned in an order
        that allows a polygon to be directly created from them.

        Returns:
            list[Vector]: The unique corner points.
        """

        # Build a dictionary keyed by a tuple indicating if each axis is degenerate.
        orders = {
            # Straight line cases
            (True, True, False): [(1, 1, 1), (1, 1, -1)],
            (True, False, True): [(1, 1, 1), (1, -1, 1)],
            (False, True, True): [(1, 1, 1), (-1, 1, 1)],
            # Planar face cases
            (True, False, False): [(1, 1, 1), (1, 1, -1), (1, -1, -1), (1, -1, 1)],
            (False, True, False): [(1, 1, 1), (1, 1, -1), (-1, 1, -1), (-1, 1, 1)],
            (False, False, True): [(1, 1, 1), (1, -1, 1), (-1, -1, 1), (-1, 1, 1)],
            # 3D object case
            (False, False, False): list(itertools.product((-1, 1), (-1, 1), (-1, 1))),
        }
        hs = self.size * 0.5
        order = orders[(hs.X < TOLERANCE, hs.Y < TOLERANCE, hs.Z < TOLERANCE)]
        local_corners = [
            Vector(sx * hs.X, sy * hs.Y, sz * hs.Z) for sx, sy, sz in order
        ]
        corners = [self.plane.from_local_coords(c) for c in local_corners]

        return corners

    @property
    def diagonal(self) -> float:
        """
        The full length of the body diagonal of the oriented bounding box,
        which represents the maximum size of the object.

        Returns:
            float: The diagonal length.
        """
        return self.wrapped.SquareExtent() ** 0.5

    @property
    def location(self) -> Location:
        """
        The Location of the center of the oriented bounding box.

        Returns:
            Location: center location
        """
        return Location(self.plane)

    @property
    def plane(self) -> Plane:
        """
        The oriented coordinate system of the bounding box.

        Returns:
            Plane: The coordinate system defined by the center and primary
                   (X) and tertiary (Z) directions of the bounding box.
        """
        return Plane(
            origin=self.center(), x_dir=self.x_direction, z_dir=self.z_direction
        )

    @property
    def size(self) -> Vector:
        """
        The full extents of the bounding box along its primary axes.

        Returns:
            Vector: The oriented size (full dimensions) of the box.
        """
        return (
            Vector(self.wrapped.XHSize(), self.wrapped.YHSize(), self.wrapped.ZHSize())
            * 2.0
        )

    @property
    def x_direction(self) -> Vector:
        """
        The primary (X) direction of the oriented bounding box.

        Returns:
            Vector: The X direction as a unit vector.
        """
        x_direction_xyz = self.wrapped.XDirection()
        coords = [getattr(x_direction_xyz, attr)() for attr in ("X", "Y", "Z")]
        return Vector(*coords)

    @property
    def y_direction(self) -> Vector:
        """
        The secondary (Y) direction of the oriented bounding box.

        Returns:
            Vector: The Y direction as a unit vector.
        """
        y_direction_xyz = self.wrapped.YDirection()
        coords = [getattr(y_direction_xyz, attr)() for attr in ("X", "Y", "Z")]
        return Vector(*coords)

    @property
    def z_direction(self) -> Vector:
        """
        The tertiary (Z) direction of the oriented bounding box.

        Returns:
            Vector: The Z direction as a unit vector.
        """
        z_direction_xyz = self.wrapped.ZDirection()
        coords = [getattr(z_direction_xyz, attr)() for attr in ("X", "Y", "Z")]
        return Vector(*coords)

    def center(self) -> Vector:
        """
        Compute and return the center point of the oriented bounding box.

        Returns:
            Vector: The center point of the box.
        """
        center_xyz = self.wrapped.Center()
        coords = [getattr(center_xyz, attr)() for attr in ("X", "Y", "Z")]
        return Vector(*coords)

    def is_completely_inside(self, other: OrientedBoundBox) -> bool:
        """
        Determine whether the given oriented bounding box is entirely contained
        within this bounding box.

        This method checks that every point of 'other' lies strictly within the
        boundaries of this box, according to the tolerance criteria inherent to the
        underlying OCCT implementation.

        Args:
            other (OrientedBoundBox): The bounding box to test for containment.

        Raises:
            ValueError: If the 'other' bounding box has an uninitialized (null) underlying geometry.

        Returns:
            bool: True if 'other' is completely inside this bounding box; otherwise, False.
        """
        return self.wrapped.IsCompletelyInside(other.wrapped)

    def is_outside(self, point: Vector) -> bool:
        """
        Determine whether a given point lies entirely outside this oriented bounding box.

        A point is considered outside if it is neither inside the box nor on its surface,
        based on the criteria defined by the OCCT implementation.

        Args:
            point (Vector): The point to test.

        Raises:
            ValueError: If the point's underlying geometry is not set (null).

        Returns:
            bool: True if the point is completely outside the bounding box; otherwise, False.
        """
        return self.wrapped.IsOut(point.to_pnt())

    def __repr__(self) -> str:
        return (
            f"OrientedBoundBox(center={self.center()!r}, "
            f"size={self.size!r}, plane={self.plane!r})"
        )


class Rotation(Location):
    """Subclass of Location used only for object rotation

    Attributes:
        X (float): rotation in degrees about X axis
        Y (float): rotation in degrees about Y axis
        Z (float): rotation in degrees about Z axis
        optionally specify rotation ordering with Intrinsic or Extrinsic enums,
            defaults to Intrinsic.XYZ

    """

    @overload
    def __init__(
        self,
        rotation: RotationLike,
        ordering: Extrinsic | Intrinsic == Intrinsic.XYZ,  # type: ignore[valid-type]
    ):
        """Subclass of Location used only for object rotation
        ordering is for order of rotations in Intrinsic or Extrinsic enums"""

    @overload
    def __init__(
        self,
        X: float = 0,
        Y: float = 0,
        Z: float = 0,
        ordering: Extrinsic | Intrinsic = Intrinsic.XYZ,
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
                angles = tuple(vectors[0])
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

RotationLike: TypeAlias = Rotation | tuple[float, float, float]
"""
RotationLike: Represents a rotation.

- `Rotation`: A specialized `Location` with the orientation set.
- `tuple[float, float, float]`: Euler rotations about the X, Y, and Z axes.
"""


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
        x, y, z, v = 0, 0, 0, None

        # Handle args
        if args:
            if all(isinstance(v, (float, int)) for v in args):
                x, y, z = Vector(args)
            elif len(args) == 1:
                x, y, z = Vector(args[0])
            else:
                raise TypeError(f"Invalid inputs to Pos {args}")

        # Handle kwargs
        x = kwargs.pop("X", x)
        y = kwargs.pop("Y", y)
        z = kwargs.pop("Z", z)
        v = kwargs.pop("v", Vector(x, y, z))

        # Handle unexpected kwargs
        if kwargs:
            raise ValueError(f"Unexpected argument(s): {', '.join(kwargs.keys())}")

        if v is not None:
            x, y, z = v
        super().__init__(Vector(x, y, z))


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
    def __init__(self):  # pragma: no cover
        ...

    @overload
    def __init__(self, trsf: gp_GTrsf | gp_Trsf):  # pragma: no cover
        ...

    @overload
    def __init__(self, matrix: Sequence[Sequence[float]]):  # pragma: no cover
        ...

    def __init__(self, *args, **kwargs):
        default_matrix = None
        default_trsf = gp_GTrsf()

        # Handle args
        if args:
            if isinstance(args[0], gp_GTrsf):
                default_trsf = args[0]
            elif isinstance(args[0], gp_Trsf):
                default_trsf = gp_GTrsf(args[0])
            elif isinstance(args[0], Sequence):
                default_matrix = args[0]
            else:
                raise TypeError(f"{args[0]} is of an unexpected type")

        # Handle kwargs
        trsf = kwargs.pop("trsf", default_trsf)
        matrix = kwargs.pop("matrix", default_matrix)

        # Handle unexpected kwargs
        if kwargs:
            raise ValueError(f"Unexpected argument(s): {', '.join(kwargs.keys())}")

        # Validate matrix
        if matrix is not None:
            # Validate matrix size & 4x4 last row value
            valid_sizes = all(
                (isinstance(row, Sequence) and (len(row) == 4)) for row in matrix
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
            for i, row in enumerate(matrix[:3]):
                for j, element in enumerate(row):
                    if not isinstance(element, (int, float)):
                        raise TypeError("Only float or int are valid in the matrix")
                    trsf.SetValue(i + 1, j + 1, element)

        self.wrapped = trsf  #: the OCP transformation function

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
        row, col = row_col
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

    =========   ====== ======== ========
    Name        x_dir  y_dir    z_dir
    =========   ====== ======== ========
    XY           +x     +y       +z
    YZ           +y     +z       +x
    ZX           +z     +x       +y
    XZ           +x     +z       -y
    YX           +y     +x       -z
    ZY           +z     +y       -x
    front        +x     +z       -y
    back         -x     +z       +y
    left         -y     +z       -x
    right        +y     +z       +x
    top          +x     +y       +z
    bottom       +x     -y       -z
    isometric    +x+y   -x+y+z   +x+y-z
    =========   ====== ======== ========

    Args:
        gp_pln (gp_Pln): an OCCT plane object
        origin (tuple[float, float, float] | Vector): the origin in global coordinates
        x_dir (tuple[float, float, float] | Vector | None): an optional vector
            representing the X Direction. Defaults to None.
        y_dir (tuple[float, float, float] | Vector | None): optional Y direction.
            Mutually exclusive with z_dir. Requires x_dir.
        z_dir (tuple[float, float, float] | Vector | None): the normal direction
            for the plane. Defaults to (0, 0, 1).

    Attributes:
        origin (Vector): global position of local (0,0,0) point
        x_dir (Vector): x direction
        y_dir (Vector): y direction
        z_dir (Vector): z direction
        forward_transform (Matrix): forward location transformation matrix
        reverse_transform (Matrix): reverse location transformation matrix
        wrapped (gp_Pln): the OCP plane object

    Raises:
        ValueError: z_dir must be non null
        ValueError: y_dir must be non null
        ValueError: x_dir must be non null
        ValueError: the specified x_dir is not orthogonal to the provided normal
        ValueError: x_dir and y_dir must not be parallel
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
    def __init__(self, gp_pln: gp_Pln) -> None:
        """Return a plane from a OCCT gp_pln"""

    @overload
    def __init__(
        self,
        origin: VectorLike,
        x_dir: VectorLike | None = None,
        z_dir: VectorLike = (0, 0, 1),
    ) -> None:
        """Return a new plane at origin with x_dir and z_dir"""

    @overload
    def __init__(
        self,
        origin: VectorLike,
        x_dir: VectorLike,
        *,
        y_dir: VectorLike,
    ) -> None:
        """Return a new plane at origin with x_dir and y_dir"""

    @overload
    def __init__(self, face: Face, x_dir: VectorLike | None = None) -> None:
        """Return a plane extending the face.
        Note: for non planar face this will return the underlying work plane"""

    @overload
    def __init__(self, location: Location) -> None:
        """Return a plane aligned with a given location"""

    @overload
    def __init__(self, axis: Axis, x_dir: VectorLike | None = None) -> None:
        """Return a plane with the z_dir aligned with the axis and optional x_dir direction"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Create a plane from either an OCCT gp_pln, Face, Location, or coordinates"""

        type_error_message = "Expected gp_Pln, Face, Location, or VectorLike"

        passed_z_dir = "z_dir" in kwargs
        passed_y_dir = "y_dir" in kwargs

        arg_plane = kwargs.pop("gp_pln", None)
        arg_face = kwargs.pop("face", None)
        arg_location = kwargs.pop("location", None)
        arg_axis = kwargs.pop("axis", None)
        arg_origin = kwargs.pop("origin", None)
        arg_x_dir = kwargs.pop("x_dir", None)
        arg_y_dir = kwargs.pop("y_dir", None)
        arg_z_dir = kwargs.pop("z_dir", (0, 0, 1))

        if kwargs:
            raise TypeError(f"Unexpected keyword arguments: {', '.join(kwargs)}")

        if args:
            arg0 = args[0]
            if arg_plane is None and isinstance(arg0, gp_Pln):
                arg_plane = arg0
            elif (
                arg_face is None
                and hasattr(arg0, "wrapped")
                and isinstance(arg0.wrapped, TopoDS_Face)
            ):
                arg_face = arg0
                if arg_x_dir is None and len(args) > 1:
                    arg_x_dir = args[1]
            elif arg_location is None and isinstance(arg0, Location):
                arg_location = arg0
            elif arg_axis is None and isinstance(arg0, Axis):
                arg_axis = arg0
                if len(args) > 1:
                    try:
                        arg_x_dir = Vector(args[1])
                    except Exception as exc:
                        raise TypeError(type_error_message) from exc
            elif arg_origin is None:
                try:
                    arg_origin = Vector(arg0)
                    if arg_x_dir is None and len(args) > 1:
                        arg_x_dir = Vector(args[1]).normalized()
                    if len(args) > 2:
                        arg_z_dir = Vector(args[2]).normalized()
                except Exception as exc:
                    raise TypeError(type_error_message) from exc

        if arg_plane:
            assert isinstance(arg_plane, gp_Pln)
            self._wrapped = self._ensure_right_handed(arg_plane)
            return

        x_dir = None
        y_dir = None
        z_dir = None
        if arg_face:
            surface = BRep_Tool.Surface_s(arg_face.wrapped)
            if not arg_face.is_planar:
                raise ValueError("Planes can only be created from planar faces")
            properties = GProp_GProps()
            BRepGProp.SurfaceProperties_s(arg_face.wrapped, properties)
            origin = Vector(properties.CentreOfMass())

            if isinstance(surface, Geom_BoundedSurface):
                point = gp_Pnt()
                face_x_dir = gp_Vec()
                tangent_v = gp_Vec()
                surface.D1(0.5, 0.5, point, face_x_dir, tangent_v)
            else:
                assert isinstance(surface, Geom_ElementarySurface)  # for .Position()
                face_x_dir = gp_Vec(surface.Position().XDirection())

            x_dir = Vector(arg_x_dir) if arg_x_dir else Vector(face_x_dir)
            x_dir = round(Vector(x_dir), 14)
            z_dir = Plane.get_topods_face_normal(arg_face.wrapped)
            z_dir = round(Vector(z_dir), 14)
        elif arg_location:
            topo_face = BRepBuilderAPI_MakeFace(
                Plane.XY.wrapped, -1.0, 1.0, -1.0, 1.0
            ).Face()
            topo_face.Move(arg_location.wrapped)
            origin = arg_location.position
            surface = BRep_Tool.Surface_s(topo_face)
            assert isinstance(surface, Geom_ElementarySurface)  # for .Position()
            x_dir = Vector(surface.Position().XDirection())
            x_dir = round(Vector(x_dir), 14)
            z_dir = Plane.get_topods_face_normal(topo_face)
            z_dir = round(Vector(z_dir), 14)
        elif arg_axis:
            origin = arg_axis.position
            x_dir = Vector(arg_x_dir) if arg_x_dir is not None else None
            z_dir = arg_axis.direction
        elif arg_origin is not None:
            origin = Vector(arg_origin)
            x_dir = Vector(arg_x_dir) if arg_x_dir else None
            z_dir = Vector(arg_z_dir)
        else:
            raise TypeError(type_error_message)

        if passed_y_dir and passed_z_dir:
            raise TypeError("Specify either y_dir or z_dir, not both")

        if arg_y_dir is not None:
            if x_dir is None:
                raise ValueError("x_dir must be provided when y_dir is specified")
            if Vector(x_dir).length == 0.0:
                raise ValueError("x_dir must be non null")
            if Vector(arg_y_dir).length == 0.0:
                raise ValueError("y_dir must be non null")

            x_dir = Vector(x_dir).normalized()
            y_input = Vector(arg_y_dir).normalized()

            z_from_xy = x_dir.cross(y_input)
            if z_from_xy.length == 0.0:
                raise ValueError("x_dir and y_dir must not be parallel")

            z_dir = z_from_xy.normalized()
            y_dir = z_dir.cross(x_dir).normalized()
            x_dir = y_dir.cross(z_dir).normalized()
        else:
            if z_dir.length == 0.0:
                raise ValueError("z_dir must be non null")
            z_dir = z_dir.normalized()

            if x_dir is None:
                ax3 = gp_Ax3(origin.to_pnt(), z_dir.to_dir())
                x_dir = Vector(ax3.XDirection()).normalized()
            else:
                if Vector(x_dir).length == 0.0:
                    raise ValueError("x_dir must be non null")
                x_dir = Vector(x_dir).normalized()

        ax3 = gp_Ax3(origin.to_pnt(), z_dir.to_dir(), x_dir.to_dir())
        self._wrapped = self._ensure_right_handed(gp_Pln(ax3))

    @property
    def wrapped(self) -> gp_Pln:
        return self._wrapped

    @staticmethod
    def _ensure_right_handed(pln: gp_Pln):
        if pln.Position().Direct():
            return pln

        warnings.warn("Trying to set a left-handed plane", stacklevel=3)
        ax2 = gp_Ax2(pln.Location(), pln.Axis().Direction(), pln.XAxis().Direction())
        return gp_Pln(gp_Ax3(ax2))

    def offset(self, amount: float) -> Plane:
        """Move the Plane by amount in the direction of z_dir"""
        return Plane(
            origin=self.origin + self.z_dir * amount, x_dir=self.x_dir, z_dir=self.z_dir
        )

    def __copy__(self) -> Plane:
        """Return copy of self"""
        return Plane(gp_Pln(self.wrapped.Position()))

    def __deepcopy__(self, _memo) -> Plane:
        """Return deepcopy of self"""
        return Plane(gp_Pln(self.wrapped.Position()))

    def __eq__(self, other: object):
        """Are planes equal operator =="""
        if not isinstance(other, Plane):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        """Hash of Plane"""
        return hash(self._key())

    def _key(self) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
        """Canonical key used for equality and hashing."""
        return (self.origin._key(), self.x_dir._key(), self.z_dir._key())

    def __neg__(self) -> Plane:
        """Reverse z direction of plane operator -"""
        return Plane(self.origin, self.x_dir, -self.z_dir)

    @overload
    def __mul__(self, other: Location | Plane) -> Location: ...
    @overload
    def __mul__(self, other: Iterable[Location | Plane]) -> list[Location]: ...
    def __mul__(
        self, other: Location | Plane | Iterable[Location | Plane]
    ) -> Location | list[Location]:
        if isinstance(other, Location):
            return Location(self) * other
        if isinstance(other, Plane):
            return Location(self) * other.location
        try:
            others = list(other)
            if all(isinstance(other, Location | Plane) for other in others):
                return [
                    Location(self)
                    * (other.location if isinstance(other, Plane) else other)
                    for other in others
                ]
        except TypeError:  # not iterable
            pass
        return NotImplemented  # will try __rmul__ on other

    @overload
    def __rmul__(self, other: Location) -> Plane: ...
    @overload
    def __rmul__(self, other: Iterable[Location | Plane]) -> list[Plane]: ...
    def __rmul__(
        self, other: Location | Plane | Iterable[Location | Plane]
    ) -> Plane | list[Plane]:
        if isinstance(other, Location | Plane):
            return self.moved(other)
        try:
            return [self.moved(loc) for loc in all_location_like(other)]
        except NotAllLocationLikeError as e:
            raise TypeError(f"{type(self).__name__} cannot be multiplied by {e}")
        except TypeError:  # not iterable
            pass
        raise TypeError(
            f"{type(self).__name__} cannot be multiplied by {type(other).__name__}"
        )

    def __and__(self: Plane, other: Axis | Location | Plane | VectorLike | Shape):
        """intersect plane with other &"""
        return self.intersect(other)

    def __format__(self, spec) -> str:
        """Format Plane"""
        last_char = spec[-1] if spec else None
        if last_char in ("f", "g"):
            return f"({self.origin:{spec}}, {self.x_dir:{spec}}, {self.z_dir:{spec}})"

        return f"({tuple(self.origin)}, {tuple(self.x_dir)}, {tuple(self.z_dir)})"

    def __repr__(self) -> str:
        """Represent Plane"""
        return f"{type(self).__name__}{self:.{TOL_DIGITS}g}"

    def __str__(self) -> str:
        """Display Plane"""
        return (
            f"{type(self).__name__}: "
            f"(origin={self.origin:.{TOL_DIGITS}g}, "
            f"x_dir={self.x_dir:.{TOL_DIGITS}g}, "
            f"z_dir={self.z_dir:.{TOL_DIGITS}g})"
        )

    def reverse(self) -> Plane:
        """Reverse z direction of plane"""
        return -self

    @property
    def origin(self) -> Vector:
        """global position of local (0,0,0) point"""
        return Vector(self.wrapped.Location())

    @origin.setter
    def origin(self, value: VectorLike):
        """Set the Plane origin"""
        self.wrapped.SetLocation(Vector(value).to_pnt())

    @property
    def z_dir(self) -> Vector:
        return Vector(self.wrapped.Axis().Direction())

    @property
    def x_dir(self) -> Vector:
        return Vector(self.wrapped.XAxis().Direction())

    @x_dir.setter
    def x_dir(self, dir: VectorLike):
        ax2 = self.to_gp_ax2()
        ax2.SetXDirection(Vector(dir).to_dir())
        self.wrapped.SetPosition(gp_Ax3(ax2))

    @property
    def y_dir(self) -> Vector:
        return Vector(self.wrapped.YAxis().Direction())

    def shift_origin(self, locator: Axis | VectorLike | Vertex) -> Plane:
        """shift plane origin

        Creates a new plane with the origin moved within the plane to the point of intersection
        of the axis or at the given Vertex. The plane's x_dir and z_dir are unchanged.

        Args:
            locator (Axis | VectorLike | Vertex): Either Axis that intersects the new
                plane origin or Vertex within Plane.

        Raises:
            ValueError: Vertex isn't within plane
            ValueError: Point isn't within plane
            ValueError: Axis doesn't intersect plane

        Returns:
            Plane: plane with new origin

        """
        if hasattr(locator, "wrapped") and locator.wrapped is None:
            raise ValueError("Can't shift origin to empty locator")
        if hasattr(locator, "wrapped") and isinstance(locator.wrapped, TopoDS_Vertex):
            geom_point = BRep_Tool.Pnt_s(locator.wrapped)
            new_origin = Vector(geom_point.X(), geom_point.Y(), geom_point.Z())
            if not self.contains(new_origin):
                raise ValueError(f"{locator} is not located within plane")
        elif isinstance(locator, (tuple, Vector)):
            new_origin = Vector(locator)
            if not self.contains(locator):
                raise ValueError(f"{locator} is not located within plane")
        elif isinstance(locator, Axis):
            intersection = self.intersect(locator)
            if not isinstance(intersection, Vector):
                raise ValueError(f"{locator} doesn't intersect the plane")
            new_origin = intersection
        else:
            raise TypeError(f"Invalid locate type: {type(locator)}")
        return Plane(origin=new_origin, x_dir=self.x_dir, z_dir=self.z_dir)

    def rotated(
        self,
        rotation: VectorLike = (0, 0, 0),
        ordering: Extrinsic | Intrinsic | None = None,
    ) -> Plane:
        """Returns a copy of this plane, rotated about the specified axes

        The origin of the workplane is unaffected by the rotation.

        Rotations are done in order x, y, z. If you need a different order,
        specify ordering. e.g. Intrinsic.ZYX changes rotation to
        (z angle, y angle, x angle) and rotates in that order.

        Args:
            rotation (VectorLike, optional): (x angle, y angle, z angle).
                Defaults to (0, 0, 0)
            ordering (Intrinsic |  Extrinsic, optional): order of rotations in
                Intrinsic or Extrinsic rotation mode. Defaults to Intrinsic.XYZ

        Returns:
            Plane: a copy of this plane rotated as requested.
        """

        if ordering is None:
            ordering = Intrinsic.XYZ

        # Note: this is not a geometric Vector
        a1, a2, a3 = map(radians, Vector(rotation))
        quaternion = gp_Quaternion()
        quaternion.SetEulerAngles(Location._rot_order_dict[ordering], a1, a2, a3)
        trsf_rotation = gp_Trsf()
        trsf_rotation.SetRotation(quaternion)

        ax = self.to_gp_ax2().Transformed(trsf_rotation)
        ax.SetLocation(self.wrapped.Location())
        return Plane(gp_Pln(gp_Ax3(ax)))

    def moved(self, loc: Location | Plane) -> Plane:
        """Change the position & orientation of a copy of self by applying a relative location

        Args:
            loc (Location | Plane): relative change

        Returns:
            Plane: relocated plane
        """
        if isinstance(loc, Plane):
            loc = loc.location
        return Plane(self.location * loc)

    def move(self, loc: Location | Plane) -> Plane:
        """Change the position & orientation of self by applying a relative location

        Args:
            loc (Location | Plane): relative change

        Returns:
            Plane: relocated self
        """
        self._wrapped = self._ensure_right_handed(self.moved(loc).wrapped)
        return self

    @property
    def forward_transform(self):
        """forward location transformation matrix"""
        global_coord_system = gp_Ax3()
        local_coord_system = self.to_gp_ax3()
        forward_t = gp_Trsf()
        forward_t.SetTransformation(global_coord_system, local_coord_system)
        return Matrix(gp_GTrsf(forward_t))

    @property
    def reverse_transform(self):
        """reverse location transformation matrix"""
        global_coord_system = gp_Ax3()
        local_coord_system = self.to_gp_ax3()
        inverse_t = gp_Trsf()
        inverse_t.SetTransformation(local_coord_system, global_coord_system)
        return Matrix(gp_GTrsf(inverse_t))

    @property
    def location(self) -> Location:
        """Return Location representing the origin and z direction"""
        return Location(self)

    def to_gp_ax3(self) -> gp_Ax3:
        """Return gp_Ax3 version of the plane"""
        return self.wrapped.Position()

    def to_gp_ax2(self) -> gp_Ax2:
        """Return gp_Ax2 version of the plane"""
        return self.wrapped.Position().Ax2()

    def _to_from_local_coords(
        self, obj: VectorLike | Any | BoundBox, to_from: bool = True
    ):
        """_to_from_local_coords

        Reposition the object relative to this plane

        Args:
            obj (VectorLike |  Shape |  BoundBox): an object to reposition. Note that
            type Any refers to all topological classes.
            to_from (bool, optional): direction of transformation. Defaults to True (to).

        Raises:
            ValueError: Unsupported object type

        Returns:
            an object of the same type, but repositioned to local coordinates
        """

        transform_matrix = self.forward_transform if to_from else self.reverse_transform

        if isinstance(obj, (tuple, Vector)):
            return Vector(obj).transform(transform_matrix)
        if isinstance(obj, BoundBox):
            global_bottom_left = Vector(obj.min.X, obj.min.Y, obj.min.Z)
            global_top_right = Vector(obj.max.X, obj.max.Y, obj.max.Z)
            local_bottom_left = global_bottom_left.transform(transform_matrix)
            local_top_right = global_top_right.transform(transform_matrix)
            local_bbox = Bnd_Box(
                gp_Pnt(*local_bottom_left),
                gp_Pnt(*local_top_right),
            )
            return BoundBox(local_bbox)
        if hasattr(obj, "wrapped") and obj.wrapped is None:  # Empty shape
            raise ValueError("Cant's reposition empty object")
        if hasattr(obj, "wrapped") and isinstance(obj.wrapped, TopoDS_Shape):  # Shapes
            # return_value = obj.transform_shape(transform_matrix)
            downcast_lut: dict[
                TopAbs_ShapeEnum, Callable[[TopoDS_Shape], TopoDS_Shape]
            ] = {
                TopAbs_ShapeEnum.TopAbs_VERTEX: TopoDS.Vertex,
                TopAbs_ShapeEnum.TopAbs_EDGE: TopoDS.Edge,
                TopAbs_ShapeEnum.TopAbs_WIRE: TopoDS.Wire,
                TopAbs_ShapeEnum.TopAbs_FACE: TopoDS.Face,
                TopAbs_ShapeEnum.TopAbs_SHELL: TopoDS.Shell,
                TopAbs_ShapeEnum.TopAbs_SOLID: TopoDS.Solid,
                TopAbs_ShapeEnum.TopAbs_COMPOUND: TopoDS.Compound,
            }
            assert obj.wrapped is not None
            try:
                f_downcast = downcast_lut[obj.wrapped.ShapeType()]
            except KeyError as exc:
                raise ValueError(f"Unknown object type {obj}") from exc

            new_shape: Shape = copy_module.deepcopy(obj, None)  # type: ignore[arg-type]
            new_shape.wrapped = f_downcast(
                BRepBuilderAPI_Transform(
                    obj.wrapped, transform_matrix.wrapped.Trsf()
                ).Shape()
            )
            return new_shape
        raise ValueError(
            f"Unable to repositioned type {type(obj)} with respect to local coordinates"
        )

    def to_local_coords(self, obj: VectorLike | Any | BoundBox):
        """Reposition the object relative to this plane

        Args:
            obj: VectorLike |  Shape |  BoundBox an object to reposition. Note that
            type Any refers to all topological classes.

        Returns:
            an object of the same type, but repositioned to local coordinates

        """
        return self._to_from_local_coords(obj, True)

    def from_local_coords(self, obj: tuple | Vector | Any | BoundBox):
        """Reposition the object relative from this plane

        Args:
            obj: VectorLike |  Shape |  BoundBox an object to reposition. Note that
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

    def contains(self, obj: VectorLike | Axis, tolerance: float = TOLERANCE) -> bool:
        """contains

        Is this point or Axis fully contained in this plane?

        Args:
            obj (VectorLike | Axis): point or Axis to  evaluate
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
    def intersect(self, vector: VectorLike) -> Vector | None:
        """Find intersection of plane and vector"""

    @overload
    def intersect(self, location: Location) -> Vector | Location | None:
        """Find intersection of plane and location"""

    @overload
    def intersect(self, axis: Axis) -> Vector | Axis | None:
        """Find intersection of plane and axis"""

    @overload
    def intersect(self, plane: Plane) -> Axis | Plane | None:
        """Find intersection of plane and plane"""

    @overload
    def intersect(self, shape: Shape) -> Shape | None:
        """Find intersection of plane and shape"""

    def intersect(self, *args, **kwargs):
        """Find intersection of plane and geometric object or shape"""

        axis, plane, vector, location, shape = _parse_intersect_args(*args, **kwargs)

        if axis is not None:
            if self.contains(axis):
                return axis

            geom_line = Geom_Line(axis.wrapped)
            geom_plane = Geom_Plane(self.to_gp_ax3())

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

        if plane is not None:
            if self.contains(plane.origin) and self.z_dir == plane.z_dir:
                return self

            surface1 = Geom_Plane(self.wrapped)
            surface2 = Geom_Plane(plane.wrapped)
            intersector = GeomAPI_IntSS(surface1, surface2, TOLERANCE)
            if intersector.IsDone() and intersector.NbLines() > 0:
                # Get the intersection line (axis)
                intersection_line = intersector.Line(1)
                # Extract the axis from the intersection line
                axis = intersection_line.Position()
                return Axis(axis)

        if vector is not None and self.contains(vector):
            return vector

        if location is not None:
            pln = Plane(location)
            if self.contains(pln.origin):
                if self.z_dir == pln.z_dir:
                    return location
                else:
                    return pln.origin

        if shape is not None:
            return shape.intersect(self)

        return None


CLASS_REGISTRY = {
    "Axis": Axis,
    "Color": Color,
    "Location": Location,
    "Plane": Plane,
    "Vector": Vector,
}


def to_align_offset(
    min_point: VectorLike,
    max_point: VectorLike,
    align: Align2DType | Align3DType,
    center: VectorLike | None = None,
) -> Vector:
    """Amount to move object to achieve the desired alignment"""
    align_offset = []

    if center is None:
        center = (Vector(min_point) + Vector(max_point)) / 2

    if align is None or align is Align.NONE:
        return Vector(0, 0, 0)
    if align is Align.MIN:
        return -Vector(min_point)
    if align is Align.MAX:
        return -Vector(max_point)
    if align is Align.CENTER:
        return -Vector(center)

    for alignment, min_coord, max_coord, center_coord in zip(
        map(Align, align),
        min_point,
        max_point,
        center,
    ):
        if alignment == Align.MIN:
            align_offset.append(-min_coord)
        elif alignment == Align.CENTER:
            align_offset.append(-center_coord)
        elif alignment == Align.MAX:
            align_offset.append(-max_coord)
        elif alignment == Align.NONE:
            align_offset.append(0)
    return Vector(*align_offset)


class NotAllLocationLikeError(TypeError):
    def __init__(self, wrong_types: Iterable[Type[Any]]) -> None:
        super().__init__(", ".join(sorted(t.__name__ for t in set(wrong_types))))


def all_location_like(items: Iterable[Any]) -> list[Location | Plane]:
    """Returns the items as a list unless any of them is not an instance of `Location | Plane`.
    Otherwise raises `NotAllLocationLikeError`."""
    items = list(items)

    if wrong_types := set(
        cast(Type[Any], type(item))
        for item in items
        if not isinstance(item, Location | Plane)
    ):
        raise NotAllLocationLikeError(wrong_types)
    else:
        return items
