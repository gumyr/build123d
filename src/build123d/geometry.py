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
# pylint: disable=no-name-in-module, import-error
# other pylint warning to temp remove:
#   too-many-arguments, too-many-locals, too-many-public-methods,
#   too-many-statements, too-many-instance-attributes, too-many-branches
import logging
from math import degrees, pi, radians
from typing import (
    Any,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from typing import overload

from typing_extensions import Literal

import OCP.GeomAbs as ga  # Geometry type enum
import OCP.TopAbs as ta  # Topology type enum
from OCP.Bnd import Bnd_Box, Bnd_OBB

# used for getting underlying geometry -- is this equivalent to brep adaptor?
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import (
    BRepAdaptor_Curve,
    BRepAdaptor_Surface,
)

from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace

from OCP.BRepGProp import BRepGProp, BRepGProp_Face  # used for mass calculation
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf

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

from OCP.Quantity import Quantity_ColorRGBA


from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Shape


# Create a build123d logger to distinguish these logs from application logs.
# If the user doesn't configure logging, all build123d logs will be discarded.
logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")

TOLERANCE = 1e-6
TOL = 1e-2
DEG2RAD = pi / 180.0
RAD2DEG = 180 / pi
HASH_CODE_MAX = 2147483647  # max 32bit signed int, required by OCC.Core.HashCode


shape_LUT = {
    ta.TopAbs_VERTEX: "Vertex",
    ta.TopAbs_EDGE: "Edge",
    ta.TopAbs_WIRE: "Wire",
    ta.TopAbs_FACE: "Face",
    ta.TopAbs_SHELL: "Shell",
    ta.TopAbs_SOLID: "Solid",
    ta.TopAbs_COMPOUND: "Compound",
}

shape_properties_LUT = {
    ta.TopAbs_VERTEX: None,
    ta.TopAbs_EDGE: BRepGProp.LinearProperties_s,
    ta.TopAbs_WIRE: BRepGProp.LinearProperties_s,
    ta.TopAbs_FACE: BRepGProp.SurfaceProperties_s,
    ta.TopAbs_SHELL: BRepGProp.SurfaceProperties_s,
    ta.TopAbs_SOLID: BRepGProp.VolumeProperties_s,
    ta.TopAbs_COMPOUND: BRepGProp.VolumeProperties_s,
}

inverse_shape_LUT = {v: k for k, v in shape_LUT.items()}

downcast_LUT = {
    ta.TopAbs_VERTEX: TopoDS.Vertex_s,
    ta.TopAbs_EDGE: TopoDS.Edge_s,
    ta.TopAbs_WIRE: TopoDS.Wire_s,
    ta.TopAbs_FACE: TopoDS.Face_s,
    ta.TopAbs_SHELL: TopoDS.Shell_s,
    ta.TopAbs_SOLID: TopoDS.Solid_s,
    ta.TopAbs_COMPOUND: TopoDS.Compound_s,
}
geom_LUT = {
    ta.TopAbs_VERTEX: "Vertex",
    ta.TopAbs_EDGE: BRepAdaptor_Curve,
    ta.TopAbs_WIRE: "Wire",
    ta.TopAbs_FACE: BRepAdaptor_Surface,
    ta.TopAbs_SHELL: "Shell",
    ta.TopAbs_SOLID: "Solid",
    ta.TopAbs_COMPOUND: "Compound",
}


geom_LUT_FACE = {
    ga.GeomAbs_Plane: "PLANE",
    ga.GeomAbs_Cylinder: "CYLINDER",
    ga.GeomAbs_Cone: "CONE",
    ga.GeomAbs_Sphere: "SPHERE",
    ga.GeomAbs_Torus: "TORUS",
    ga.GeomAbs_BezierSurface: "BEZIER",
    ga.GeomAbs_BSplineSurface: "BSPLINE",
    ga.GeomAbs_SurfaceOfRevolution: "REVOLUTION",
    ga.GeomAbs_SurfaceOfExtrusion: "EXTRUSION",
    ga.GeomAbs_OffsetSurface: "OFFSET",
    ga.GeomAbs_OtherSurface: "OTHER",
}

geom_LUT_EDGE = {
    ga.GeomAbs_Line: "LINE",
    ga.GeomAbs_Circle: "CIRCLE",
    ga.GeomAbs_Ellipse: "ELLIPSE",
    ga.GeomAbs_Hyperbola: "HYPERBOLA",
    ga.GeomAbs_Parabola: "PARABOLA",
    ga.GeomAbs_BezierCurve: "BEZIER",
    ga.GeomAbs_BSplineCurve: "BSPLINE",
    ga.GeomAbs_OffsetCurve: "OFFSET",
    ga.GeomAbs_OtherCurve: "OTHER",
}

Shapes = Literal["Vertex", "Edge", "Wire", "Face", "Shell", "Solid", "Compound"]
Geoms = Literal[
    "Vertex",
    "Wire",
    "Shell",
    "Solid",
    "Compound",
    "PLANE",
    "CYLINDER",
    "CONE",
    "SPHERE",
    "TORUS",
    "BEZIER",
    "BSPLINE",
    "REVOLUTION",
    "EXTRUSION",
    "OFFSET",
    "OTHER",
    "LINE",
    "CIRCLE",
    "ELLIPSE",
    "HYPERBOLA",
    "PARABOLA",
]


class Vector:
    """Create a 3-dimensional vector

    Args:
      args: a 3D vector, with x-y-z parts.

    you can either provide:
    * nothing (in which case the null vector is return)
    * a gp_Vec
    * a vector ( in which case it is copied )
    * a 3-tuple
    * a 2-tuple (z assumed to be 0)
    * three float values: x, y, and z
    * two float values: x,y

    Returns:

    """

    _wrapped: gp_Vec

    @overload
    def __init__(self, x: float, y: float, z: float):  # pragma: no cover
        ...

    @overload
    def __init__(self, x: float, y: float):  # pragma: no cover
        ...

    @overload
    def __init__(self, vec: Vector):  # pragma: no cover
        ...

    @overload
    def __init__(self, vec: Sequence[float]):  # pragma: no cover
        ...

    @overload
    def __init__(self, vec: Union[gp_Vec, gp_Pnt, gp_Dir, gp_XYZ]):  # pragma: no cover
        ...

    @overload
    def __init__(self):  # pragma: no cover
        ...

    def __init__(self, *args):
        self.vector_index = 0
        if len(args) == 3:
            f_v = gp_Vec(*args)
        elif len(args) == 2:
            f_v = gp_Vec(*args, 0)
        elif len(args) == 1:
            if isinstance(args[0], Vector):
                f_v = gp_Vec(args[0].wrapped.XYZ())
            elif isinstance(args[0], (tuple, list)):
                arg = args[0]
                if len(arg) == 3:
                    f_v = gp_Vec(*arg)
                elif len(arg) == 2:
                    f_v = gp_Vec(*arg, 0)
            elif isinstance(args[0], (gp_Vec, gp_Pnt, gp_Dir)):
                f_v = gp_Vec(args[0].XYZ())
            elif isinstance(args[0], gp_XYZ):
                f_v = gp_Vec(args[0])
            else:
                raise TypeError("Expected three floats, OCC gp_, or 3-tuple")
        elif len(args) == 0:
            f_v = gp_Vec(0, 0, 0)
        else:
            raise TypeError("Expected three floats, OCC gp_, or 3-tuple")

        self._wrapped = f_v

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

    def __sub__(self, vec: Vector) -> Vector:
        """Mathematical subtraction function"""
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

    def __add__(self, vec: Vector) -> Vector:
        """Mathematical addition function"""
        return self.add(vec)

    def multiply(self, scale: float) -> Vector:
        """Mathematical multiply function"""
        return Vector(self.wrapped.Multiplied(scale))

    def __mul__(self, scale: float) -> Vector:
        """Mathematical multiply function"""
        return self.multiply(scale)

    def __truediv__(self, denom: float) -> Vector:
        """Mathematical division function"""
        return self.multiply(1.0 / denom)

    def __rmul__(self, scale: float) -> Vector:
        """Mathematical multiply function"""
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

    def distance_to_plane(self):
        """Minimum distance between vector and plane"""
        raise NotImplementedError("Have not needed this yet, but OCCT supports it!")

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
        """Flip direction of vector"""
        return self * -1

    def __abs__(self) -> float:
        """Vector length"""
        return self.length

    def __repr__(self) -> str:
        """Display vector"""
        return "Vector: " + str((self.X, self.Y, self.Z))

    def __str__(self) -> str:
        """Display vector"""
        return "Vector: " + str((self.X, self.Y, self.Z))

    def __eq__(self, other: Vector) -> bool:  # type: ignore[override]
        """Vectors equal"""
        return self.wrapped.IsEqual(other.wrapped, 0.00001, 0.00001)

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

    def transform(self, affine_transform: Matrix) -> Vector:
        """Apply affine transformation"""
        # to gp_Pnt to obey cq transformation convention (in OCP.vectors do not translate)
        pnt = self.to_pnt()
        pnt_t = pnt.Transformed(affine_transform.wrapped.Trsf())

        return Vector(gp_Vec(pnt_t.XYZ()))

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


#:TypeVar("VectorLike"): Tuple of float or Vector defining a position in space
VectorLike = Union[Vector, tuple[float, float], tuple[float, float, float]]


class Axis:
    """Axis

    Axis defined by point and direction

    Args:
        origin (VectorLike): start point
        direction (VectorLike): direction
    """

    @classmethod
    @property
    def X(cls) -> Axis:
        """X Axis"""
        return Axis((0, 0, 0), (1, 0, 0))

    @classmethod
    @property
    def Y(cls) -> Axis:
        """Y Axis"""
        return Axis((0, 0, 0), (0, 1, 0))

    @classmethod
    @property
    def Z(cls) -> Axis:
        """Z Axis"""
        return Axis((0, 0, 0), (0, 0, 1))

    def __init__(self, origin: VectorLike, direction: VectorLike):
        self.wrapped = gp_Ax1(
            Vector(origin).to_pnt(), gp_Dir(*Vector(direction).normalized().to_tuple())
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

    @classmethod
    def from_occt(cls, axis: gp_Ax1) -> Axis:
        """Create an Axis instance from the occt object"""
        position = (
            axis.Location().X(),
            axis.Location().Y(),
            axis.Location().Z(),
        )
        direction = (
            axis.Direction().X(),
            axis.Direction().Y(),
            axis.Direction().Z(),
        )
        return Axis(position, direction)

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

    def located(self, new_location: Location):
        """relocates self to a new location possibly changing position and direction"""
        new_gp_ax1 = self.wrapped.Transformed(new_location.wrapped.Transformation())
        return Axis.from_occt(new_gp_ax1)

    def to_location(self) -> Location:
        """Return self as Location"""
        return Location(Plane(origin=self.position, z_dir=self.direction))

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
        return Axis.from_occt(self.wrapped.Reversed())

    def __neg__(self) -> Axis:
        """Return a copy of self with the direction reversed"""
        return self.reverse()


class BoundBox:
    """A BoundingBox for a Shape"""

    def __init__(self, bounding_box: Bnd_Box) -> None:
        self.wrapped: Bnd_Box = bounding_box
        x_min, y_min, z_min, x_max, y_max, z_max = bounding_box.Get()
        self.min = Vector(x_min, y_min, z_min)
        self.max = Vector(x_max, y_max, z_max)
        self.size = Vector(x_max - x_min, y_max - y_min, z_max - z_min)

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


class Color:
    """
    Color object based on OCCT Quantity_ColorRGBA.
    """

    @overload
    def __init__(self, name: str, alpha: float = 0.0):
        """Color from name

        `OCCT Color Names
            <https://dev.opencascade.org/doc/refman/html/_quantity___name_of_color_8hxx.html>`_

        Args:
            name (str): color, e.g. "blue"
        """

    @overload
    def __init__(self, red: float, green: float, blue: float, alpha: float = 0.0):
        """Color from RGBA and Alpha values

        Args:
            red (float): 0.0 <= red <= 1.0
            green (float): 0.0 <= green <= 1.0
            blue (float): 0.0 <= blue <= 1.0
            alpha (float, optional): 0.0 <= alpha <= 1.0. Defaults to 0.0.
        """

    def __init__(self, *args, **kwargs):
        red, green, blue, alpha, name = 1.0, 1.0, 1.0, 0.0, None
        if len(args) >= 1:
            if isinstance(args[0], str):
                name = args[0]
            else:
                red = args[0]
        if len(args) >= 2:
            if name:
                alpha = args[1]
            else:
                green = args[1]
        if len(args) >= 3:
            blue = args[2]
        if len(args) == 4:
            alpha = args[3]
        if kwargs.get("red"):
            red = kwargs.get("red")
        if kwargs.get("green"):
            green = kwargs.get("green")
        if kwargs.get("blue"):
            blue = kwargs.get("blue")
        if kwargs.get("alpha"):
            alpha = kwargs.get("alpha")

        if name:
            self.wrapped = Quantity_ColorRGBA()
            exists = Quantity_ColorRGBA.ColorFromName_s(args[0], self.wrapped)
            if not exists:
                raise ValueError(f"Unknown color name: {name}")
            self.wrapped.SetAlpha(alpha)
        else:
            self.wrapped = Quantity_ColorRGBA(red, green, blue, alpha)

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """
        Convert Color to RGB tuple.
        """
        alpha = self.wrapped.Alpha()
        rgb = self.wrapped.GetRGB()

        return (rgb.Red(), rgb.Green(), rgb.Blue(), alpha)


class Location:
    """Location in 3D space. Depending on usage can be absolute or relative.

    This class wraps the TopLoc_Location class from OCCT. It can be used to move Shape
    objects in both relative and absolute manner. It is the preferred type to locate objects
    in CQ.

    Args:

    Returns:

    """

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
        position_xyz = self.wrapped.Transformation().TranslationPart()
        trsf_position = gp_Trsf()
        trsf_position.SetTranslationPart(
            gp_Vec(position_xyz.X(), position_xyz.Y(), position_xyz.Z())
        )
        rotation = [radians(a) for a in rotation]
        quaternion = gp_Quaternion()
        quaternion.SetEulerAngles(gp_EulerSequence.gp_Intrinsic_XYZ, *rotation)
        trsf_orientation = gp_Trsf()
        trsf_orientation.SetRotation(quaternion)
        self.wrapped = TopLoc_Location(trsf_position * trsf_orientation)

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
        self, translation: VectorLike, axis: VectorLike, angle: float
    ):  # pragma: no cover
        """Location with translation t and rotation around axis by angle
        with respect to the original location."""

    def __init__(self, *args):
        transform = gp_Trsf()

        if len(args) == 0:
            pass

        elif len(args) == 1:
            translation = args[0]

            if isinstance(translation, (Vector, tuple)):
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
            if isinstance(args[0], (Vector, tuple)):
                if isinstance(args[1], (Vector, tuple)):
                    rotation = [radians(a) for a in args[1]]
                    quaternion = gp_Quaternion()
                    quaternion.SetEulerAngles(
                        gp_EulerSequence.gp_Intrinsic_XYZ, *rotation
                    )
                    transform.SetRotation(quaternion)
                elif isinstance(args[0], (Vector, tuple)) and isinstance(
                    args[1], (int, float)
                ):
                    angle = radians(args[1])
                    quaternion = gp_Quaternion()
                    quaternion.SetEulerAngles(
                        gp_EulerSequence.gp_Intrinsic_XYZ, 0, 0, angle
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
        else:
            translation, axis, angle = args
            transform.SetRotation(
                gp_Ax1(Vector().to_pnt(), Vector(axis).to_dir()), angle * pi / 180.0
            )
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

    def __mul__(self, other: Location) -> Location:
        """Combine locations"""
        return Location(self.wrapped * other.wrapped)

    def __pow__(self, exponent: int) -> Location:
        return Location(self.wrapped.Powered(exponent))

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


class Rotation(Location):
    """Subclass of Location used only for object rotation"""

    def __init__(self, about_x: float = 0, about_y: float = 0, about_z: float = 0):
        self.about_x = about_x
        self.about_y = about_y
        self.about_z = about_z

        quaternion = gp_Quaternion()
        quaternion.SetEulerAngles(
            gp_EulerSequence.gp_Intrinsic_XYZ,
            radians(about_x),
            radians(about_y),
            radians(about_z),
        )
        transformation = gp_Trsf()
        transformation.SetRotationPart(quaternion)
        super().__init__(transformation)


#:TypeVar("RotationLike"): Three tuple of angles about x, y, z or Rotation
RotationLike = Union[tuple[float, float, float], Rotation]


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

    Args:

    Returns:

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


class Plane:
    """Plane

    A plane is positioned in space with a coordinate system such that the plane is defined by
    the origin, x_dir (X direction), y_dir (Y direction), and z_dir (Z direction) of this coordinate
    system, which is the "local coordinate system" of the plane. The z_dir is a vector normal to the
    plane. The coordinate system is right-handed.

    A plane allows the use of local 2D coordinates, which are later converted to
    global, 3d coordinates when the operations are complete.

    Planes can be created from faces as workplanes for feature creation on objects.

    ======= ====== ====== ======
    Name    x_dir  y_dir  z_dir
    ======= ====== ====== ======
    XY      +x     +y     +z
    YZ      +y     +z     +x
    ZX      +z     +x     +y
    XZ      +x     +z     -y
    YX      +y     +x     -z
    ZY      +z     +y     -x
    front   +x     +y     +z
    back    -x     +y     -z
    left    +z     +y     -x
    right   -z     +y     +x
    top     +x     -z     +y
    bottom  +x     +z     -y
    ======= ====== ====== ======

    Args:
        gp_pln (gp_Pln): an OCCT plane object
        origin (Union[tuple[float, float, float], Vector]): the origin in global coordinates
        x_dir (Union[tuple[float, float, float], Vector], optional): an optional vector
            representing the X Direction. Defaults to None.
        z_dir (Union[tuple[float, float, float], Vector], optional): the normal direction
            for the plane. Defaults to (0, 0, 1).

    Raises:
        ValueError: z_dir must be non null
        ValueError: x_dir must be non null
        ValueError: the specified x_dir is not orthogonal to the provided normal

    Returns:
        Plane: A plane

    """

    @classmethod
    @property
    def XY(cls) -> Plane:
        """XY Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, 0, 1))

    @classmethod
    @property
    def YZ(cls) -> Plane:
        """YZ Plane"""
        return Plane((0, 0, 0), (0, 1, 0), (1, 0, 0))

    @classmethod
    @property
    def ZX(cls) -> Plane:
        """ZX Plane"""
        return Plane((0, 0, 0), (0, 0, 1), (0, 1, 0))

    @classmethod
    @property
    def XZ(cls) -> Plane:
        """XZ Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, -1, 0))

    @classmethod
    @property
    def YX(cls) -> Plane:
        """YX Plane"""
        return Plane((0, 0, 0), (0, 1, 0), (0, 0, -1))

    @classmethod
    @property
    def ZY(cls) -> Plane:
        """ZY Plane"""
        return Plane((0, 0, 0), (0, 0, 1), (-1, 0, 0))

    @classmethod
    @property
    def front(cls) -> Plane:
        """Front Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, 0, 1))

    @classmethod
    @property
    def back(cls) -> Plane:
        """Back Plane"""
        return Plane((0, 0, 0), (-1, 0, 0), (0, 0, -1))

    @classmethod
    @property
    def left(cls) -> Plane:
        """Left Plane"""
        return Plane((0, 0, 0), (0, 0, 1), (-1, 0, 0))

    @classmethod
    @property
    def right(cls) -> Plane:
        """Right Plane"""
        return Plane((0, 0, 0), (0, 0, -1), (1, 0, 0))

    @classmethod
    @property
    def top(cls) -> Plane:
        """Top Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, 1, 0))

    @classmethod
    @property
    def bottom(cls) -> Plane:
        """Bottom Plane"""
        return Plane((0, 0, 0), (1, 0, 0), (0, -1, 0))

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
    def __init__(self, face: "Face"):  # pragma: no cover
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
        """Create a plane from either an OCCT gp_pln or coordinates"""
        if args:
            if isinstance(args[0], gp_Pln):
                self.wrapped = args[0]
            # Check for Face by using the OCCT class to avoid circular imports of the Face class
            elif hasattr(args[0], "wrapped") and isinstance(
                args[0].wrapped,
                TopoDS_Face,
            ):
                properties = GProp_GProps()
                BRepGProp.SurfaceProperties_s(args[0].wrapped, properties)
                self._origin = Vector(properties.CentreOfMass())
                self.x_dir = Vector(
                    BRep_Tool.Surface_s(args[0].wrapped).Position().XDirection()
                )
                self.z_dir = Plane.get_topods_face_normal(args[0].wrapped)
            elif isinstance(args[0], Location):
                topo_face = BRepBuilderAPI_MakeFace(
                    Plane.XY.wrapped, -1.0, 1.0, -1.0, 1.0
                ).Face()
                topo_face.Move(args[0].wrapped)
                self._origin = args[0].position
                self.x_dir = Vector(
                    BRep_Tool.Surface_s(topo_face).Position().XDirection()
                )
                self.z_dir = Plane.get_topods_face_normal(topo_face)
            else:
                self._origin = Vector(args[0])
                self.x_dir = Vector(args[1]) if len(args) >= 2 else None
                self.z_dir = Vector(args[2]) if len(args) == 3 else Vector(0, 0, 1)
        if kwargs:
            if "gp_pln" in kwargs:
                self.wrapped = kwargs.get("gp_pln")
            self._origin = Vector(kwargs.get("origin", (0, 0, 0)))
            self.x_dir = kwargs.get("x_dir")
            self.x_dir = Vector(self.x_dir) if self.x_dir else None
            self.z_dir = Vector(kwargs.get("z_dir", (0, 0, 1)))
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
                ax3 = gp_Ax3(self.origin.to_pnt(), self.z_dir.to_dir())
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
        """Are planes equal"""
        return all(self._eq_iter(other))

    def __ne__(self, other: Plane):
        """Are planes not equal"""
        return not self.__eq__(other)

    def __neg__(self) -> Plane:
        """Reverse z direction of plane"""
        return Plane(self.origin, self.x_dir, -self.z_dir)

    def __mul__(self, location: Location) -> Plane:
        if not isinstance(location, Location):
            raise TypeError(
                "Planes can only be multiplied with Locations to relocate them"
            )
        return Plane(self.to_location() * location)

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

    @property
    def origin(self) -> Vector:
        """Get the Plane origin"""
        return self._origin

    @origin.setter
    def origin(self, value):
        """Set the Plane origin"""
        self._origin = Vector(value)
        self._calc_transforms()

    def set_origin2d(self, x: float, y: float) -> Plane:
        """Set a new origin in the plane itself

        Set a new origin in the plane itself. The plane's orientation and
        x_dir are unaffected.

        Args:
            x (float): offset in the x direction
            y (float): offset in the y direction

        Returns:
            None

            The new coordinates are specified in terms of the current 2D system.
            As an example:

            p = Plane.XY
            p.set_origin2d(2, 2)
            p.set_origin2d(2, 2)

            results in a plane with its origin at (x, y) = (4, 4) in global
            coordinates. Both operations were relative to local coordinates of the
            plane.

        """
        self._origin = self.from_local_coords((x, y))

    def rotated(self, rotation: VectorLike = (0, 0, 0)) -> Plane:
        """Returns a copy of this plane, rotated about the specified axes

        Since the z axis is always normal the plane, rotating around Z will
        always produce a plane that is parallel to this one.

        The origin of the workplane is unaffected by the rotation.

        Rotations are done in order x, y, z. If you need a different order,
        manually chain together multiple rotate() commands.

        Args:
            rotation (VectorLike, optional): (xDegrees, yDegrees, zDegrees). Defaults to (0, 0, 0).

        Returns:
            Plane: a copy of this plane rotated as requested.
        """
        # Note: this is not a geometric Vector
        rotation = [radians(a) for a in rotation]
        quaternion = gp_Quaternion()
        quaternion.SetEulerAngles(gp_EulerSequence.gp_Intrinsic_XYZ, *rotation)
        trsf_rotation = gp_Trsf()
        trsf_rotation.SetRotation(quaternion)
        transformation = Matrix(gp_GTrsf(trsf_rotation))

        # Compute the new plane.
        new_xdir = self.x_dir.transform(transformation)
        new_z_dir = self.z_dir.transform(transformation)

        return Plane(self._origin, new_xdir, new_z_dir)

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

    def to_location(self) -> Location:
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
