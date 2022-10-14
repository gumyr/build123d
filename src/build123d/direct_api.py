from __future__ import annotations
import math
import logging
import sys
import copy
from typing import (
    Optional,
    Tuple,
    Union,
    Iterable,
    List,
    Sequence,
    Iterator,
    Dict,
    Any,
    overload,
    TypeVar,
    cast as tcast,
)
from .build_enums import (
    Select,
    Kind,
    Keep,
    Mode,
    Transition,
    FontStyle,
    Halign,
    Valign,
    Until,
    SortBy,
    GeomType,
)
from typing_extensions import Literal
from io import BytesIO

from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersCore import vtkTriangleFilter, vtkPolyDataNormals


# from .geom import Vector, VectorLike, BoundBox, Location, Matrix, Axis
# from .shapes import Plane

from OCP.StdFail import StdFail_NotDone
from OCP.Standard import Standard_NoSuchObject
from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Skin


from OCP.Precision import Precision

from OCP.gp import (
    gp_Vec,
    gp_Pnt,
    gp_Ax1,
    gp_Ax2,
    gp_Ax3,
    gp_Dir,
    gp_Circ,
    gp_Trsf,
    gp_Pln,
    gp_Pnt2d,
    gp_Dir2d,
    gp_Elips,
)

# Array of points (used for B-spline construction):
from OCP.TColgp import TColgp_HArray1OfPnt, TColgp_HArray2OfPnt

# Array of vectors (used for B-spline interpolation):
from OCP.TColgp import TColgp_Array1OfVec

# Array of booleans (used for B-spline interpolation):
from OCP.TColStd import TColStd_HArray1OfBoolean

# Array of floats (used for B-spline interpolation):
from OCP.TColStd import TColStd_HArray1OfReal

from OCP.BRepAdaptor import (
    BRepAdaptor_Curve,
    BRepAdaptor_CompCurve,
    BRepAdaptor_Surface,
    # BRepAdaptor_HCurve,
    # BRepAdaptor_HCompCurve,
)

from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeVertex,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Sewing,
    BRepBuilderAPI_Copy,
    BRepBuilderAPI_GTransform,
    BRepBuilderAPI_Transform,
    BRepBuilderAPI_Transformed,
    BRepBuilderAPI_RightCorner,
    BRepBuilderAPI_RoundCorner,
    BRepBuilderAPI_MakeSolid,
)

# properties used to store mass calculation result
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp_Face, BRepGProp  # used for mass calculation

from OCP.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCone,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakeTorus,
    BRepPrimAPI_MakeWedge,
    BRepPrimAPI_MakePrism,
    BRepPrimAPI_MakeRevol,
    BRepPrimAPI_MakeSphere,
)
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter

from OCP.TopExp import TopExp_Explorer  # Topology explorer

# used for getting underlying geometry -- is this equivalent to brep adaptor?
from OCP.BRep import BRep_Tool, BRep_Builder

from OCP.TopoDS import (
    TopoDS,
    TopoDS_Shape,
    TopoDS_Builder,
    TopoDS_Compound,
    TopoDS_Iterator,
    TopoDS_Wire,
    TopoDS_Face,
    TopoDS_Edge,
    TopoDS_Vertex,
    TopoDS_Solid,
    TopoDS_Shell,
    TopoDS_CompSolid,
)

from OCP.GC import GC_MakeArcOfCircle, GC_MakeArcOfEllipse  # geometry construction
from OCP.GCE2d import GCE2d_MakeSegment
from OCP.gce import gce_MakeLin, gce_MakeDir
from OCP.GeomAPI import (
    GeomAPI_Interpolate,
    GeomAPI_ProjectPointOnSurf,
    GeomAPI_PointsToBSpline,
    GeomAPI_PointsToBSplineSurface,
)

from OCP.BRepFill import BRepFill

from OCP.BRepAlgoAPI import (
    BRepAlgoAPI_Common,
    BRepAlgoAPI_Fuse,
    BRepAlgoAPI_Cut,
    BRepAlgoAPI_BooleanOperation,
    BRepAlgoAPI_Splitter,
)

from OCP.Geom import (
    Geom_ConicalSurface,
    Geom_CylindricalSurface,
    Geom_Surface,
    Geom_Plane,
)
from OCP.Geom2d import Geom2d_Line

from OCP.BRepLib import BRepLib, BRepLib_FindSurface

from OCP.BRepOffsetAPI import (
    BRepOffsetAPI_ThruSections,
    BRepOffsetAPI_MakePipeShell,
    BRepOffsetAPI_MakeThickSolid,
    BRepOffsetAPI_MakeOffset,
)

from OCP.BRepFilletAPI import (
    BRepFilletAPI_MakeChamfer,
    BRepFilletAPI_MakeFillet,
    BRepFilletAPI_MakeFillet2d,
)

from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_ListOfShape

from OCP.TopExp import TopExp

from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_Solid, ShapeFix_Face

from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs

from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer

from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

from OCP.BRepTools import BRepTools

from OCP.LocOpe import LocOpe_DPrism

from OCP.BRepCheck import BRepCheck_Analyzer

from OCP.Font import (
    Font_FontMgr,
    Font_FA_Regular,
    Font_FA_Italic,
    Font_FA_Bold,
    Font_SystemFont,
)

from OCP.StdPrs import StdPrs_BRepFont, StdPrs_BRepTextBuilder as Font_BRepTextBuilder

from OCP.NCollection import NCollection_Utf8String

from OCP.BRepFeat import BRepFeat_MakeDPrism

from OCP.BRepClass3d import BRepClass3d_SolidClassifier

from OCP.TCollection import TCollection_AsciiString

from OCP.TopLoc import TopLoc_Location

from OCP.GeomAbs import (
    GeomAbs_Shape,
    GeomAbs_C0,
    GeomAbs_Intersection,
    GeomAbs_JoinType,
)
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeFilling
from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Mode

from OCP.BOPAlgo import BOPAlgo_GlueEnum

from OCP.IFSelect import IFSelect_ReturnStatus

from OCP.TopAbs import TopAbs_ShapeEnum, TopAbs_Orientation

from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCP.TopTools import TopTools_HSequenceOfShape

from OCP.GCPnts import GCPnts_AbscissaPoint

from OCP.GeomFill import (
    GeomFill_Frenet,
    GeomFill_CorrectedFrenet,
    GeomFill_TrihedronLaw,
)

from OCP.BRepProj import BRepProj_Projection
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

from OCP.IVtkOCC import IVtkOCC_Shape, IVtkOCC_ShapeMesher
from OCP.IVtkVTK import IVtkVTK_ShapeData

# for catching exceptions
from OCP.Standard import Standard_NoSuchObject, Standard_Failure

from OCP.Interface import Interface_Static

from OCP.gp import (
    gp_Vec,
    gp_Ax1,
    gp_Ax3,
    gp_Pnt,
    gp_Dir,
    gp_Pln,
    gp_Trsf,
    gp_GTrsf,
    gp_XYZ,
    gp_EulerSequence,
    gp,
)
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopoDS import TopoDS_Shape
from OCP.TopLoc import TopLoc_Location

from math import pi, sqrt, inf

import warnings

TOLERANCE = 1e-6
TOL = 1e-2
DEG2RAD = 2 * pi / 360.0
HASH_CODE_MAX = 2147483647  # max 32bit signed int, required by OCC.Core.HashCode

import OCP.TopAbs as ta  # Topology type enum

shape_LUT = {
    ta.TopAbs_VERTEX: "Vertex",
    ta.TopAbs_EDGE: "Edge",
    ta.TopAbs_WIRE: "Wire",
    ta.TopAbs_FACE: "Face",
    ta.TopAbs_SHELL: "Shell",
    ta.TopAbs_SOLID: "Solid",
    ta.TopAbs_COMPSOLID: "CompSolid",
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
    ta.TopAbs_COMPSOLID: TopoDS.CompSolid_s,
    ta.TopAbs_COMPOUND: TopoDS.Compound_s,
}

geom_LUT = {
    ta.TopAbs_VERTEX: "Vertex",
    ta.TopAbs_EDGE: BRepAdaptor_Curve,
    ta.TopAbs_WIRE: "Wire",
    ta.TopAbs_FACE: BRepAdaptor_Surface,
    ta.TopAbs_SHELL: "Shell",
    ta.TopAbs_SOLID: "Solid",
    ta.TopAbs_SOLID: "CompSolid",
    ta.TopAbs_COMPOUND: "Compound",
}

import OCP.GeomAbs as ga  # Geometry type enum

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

Shapes = Literal[
    "Vertex", "Edge", "Wire", "Face", "Shell", "Solid", "CompSolid", "Compound"
]
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
    def __init__(self, X: float, Y: float, Z: float) -> None:
        ...

    @overload
    def __init__(self, X: float, Y: float) -> None:
        ...

    @overload
    def __init__(self, v: Vector) -> None:
        ...

    @overload
    def __init__(self, v: Sequence[float]) -> None:
        ...

    @overload
    def __init__(self, v: Union[gp_Vec, gp_Pnt, gp_Dir, gp_XYZ]) -> None:
        ...

    @overload
    def __init__(self) -> None:
        ...

    def __init__(self, *args):
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

    @property
    def X(self) -> float:
        return self.wrapped.X()

    @X.setter
    def X(self, value: float) -> None:
        self.wrapped.SetX(value)

    @property
    def Y(self) -> float:
        return self.wrapped.Y()

    @Y.setter
    def Y(self, value: float) -> None:
        self.wrapped.SetY(value)

    @property
    def Z(self) -> float:
        return self.wrapped.Z()

    @Z.setter
    def Z(self, value: float) -> None:
        self.wrapped.SetZ(value)

    @property
    def length(self) -> float:
        return self.wrapped.Magnitude()

    @property
    def wrapped(self) -> gp_Vec:
        return self._wrapped

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.X, self.Y, self.Z)

    def cross(self, v: Vector) -> Vector:
        return Vector(self.wrapped.Crossed(v.wrapped))

    def dot(self, v: Vector) -> float:
        return self.wrapped.Dot(v.wrapped)

    def sub(self, v: Vector) -> Vector:
        return Vector(self.wrapped.Subtracted(v.wrapped))

    def __sub__(self, v: Vector) -> Vector:
        return self.sub(v)

    def add(self, v: Vector) -> Vector:
        return Vector(self.wrapped.Added(v.wrapped))

    def __add__(self, v: Vector) -> Vector:
        return self.add(v)

    def multiply(self, scale: float) -> Vector:
        """

        Args:
          scale: float:

        Returns:


        """
        return Vector(self.wrapped.Multiplied(scale))

    def __mul__(self, scale: float) -> Vector:
        return self.multiply(scale)

    def __truediv__(self, denom: float) -> Vector:
        return self.multiply(1.0 / denom)

    def __rmul__(self, scale: float) -> Vector:
        return self.multiply(scale)

    def normalized(self) -> Vector:
        return Vector(self.wrapped.Normalized())

    def center(self) -> Vector:
        """

        Args:

        Returns:
          The center of myself is myself.
          Provided so that vectors, vertices, and other shapes all support a
          common interface, when center() is requested for all objects on the
          stack.

        """
        return self

    def get_angle(self, v: Vector) -> float:
        return self.wrapped.Angle(v.wrapped)

    def get_signed_angle(self, v: Vector, normal: Vector = None) -> float:
        """Signed Angle Between Vectors

        Return the signed angle in RADIANS between two vectors with the given normal
        based on this math: angle = atan2((Va × Vb) ⋅ Vn, Va ⋅ Vb)

        Args:
          v: Second Vector
          normal: Vector
          v: Vector:
          normal: Vector:  (Default value = None)

        Returns:
          Angle between vectors

        """
        if normal is None:
            gp_normal = gp_Vec(0, 0, -1)
        else:
            gp_normal = normal.wrapped
        return self.wrapped.AngleWithRef(v.wrapped, gp_normal)

    def distance_to_line(self):
        raise NotImplementedError("Have not needed this yet, but OCCT supports it!")

    def project_to_line(self, line: Vector) -> Vector:
        """Returns a new vector equal to the projection of this Vector onto the line
        represented by Vector <line>

        Args:
          args: Vector

        Returns the projected vector.
          line: Vector:

        Returns:

        """
        line_length = line.length

        return line * (self.dot(line) / (line_length * line_length))

    def distance_to_plane(self):
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
        return self * -1

    def __abs__(self) -> float:
        return self.length

    def __repr__(self) -> str:
        return "Vector: " + str((self.X, self.Y, self.Z))

    def __str__(self) -> str:
        return "Vector: " + str((self.X, self.Y, self.Z))

    def __eq__(self, other: Vector) -> bool:  # type: ignore[override]
        return self.wrapped.IsEqual(other.wrapped, 0.00001, 0.00001)

    def to_pnt(self) -> gp_Pnt:

        return gp_Pnt(self.wrapped.XYZ())

    def to_dir(self) -> gp_Dir:

        return gp_Dir(self.wrapped.XYZ())

    def transform(self, t: Matrix) -> Vector:

        # to gp_Pnt to obey cq transformation convention (in OCP.vectors do not translate)
        pnt = self.to_pnt()
        pnt_t = pnt.Transformed(t.wrapped.Trsf())

        return Vector(gp_Vec(pnt_t.XYZ()))

    def rotate_x(self, angle: float) -> Vector:
        """Rotate Vector about X-Axis

        Args:
          angle: Angle in degrees
          angle: float:

        Returns:
          : Rotated Vector

        """
        return Vector(
            gp_Vec(self.X, self.Y, self.Z).Rotated(gp.OX_s(), math.pi * angle / 180)
        )

    def rotate_y(self, angle: float) -> Vector:
        """Rotate Vector about Y-Axis

        Args:
          angle: Angle in degrees
          angle: float:

        Returns:
          : Rotated Vector

        """
        return Vector(
            gp_Vec(self.X, self.Y, self.Z).Rotated(gp.OY_s(), math.pi * angle / 180)
        )

    def rotate_z(self, angle: float) -> Vector:
        """Rotate Vector about Z-Axis

        Args:
          angle: Angle in degrees
          angle: float:

        Returns:
          : Rotated Vector

        """
        return Vector(
            gp_Vec(self.X, self.Y, self.Z).Rotated(gp.OZ_s(), math.pi * angle / 180)
        )

    # def to_vertex(self) -> Vertex:
    #     """Convert to Vector to Vertex

    #     Args:

    #     Returns:
    #       : Vertex equivalent of Vector

    #     """
    #     return Vertex.makeVertex(*self.to_tuple())


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

    def __repr__(self) -> str:
        return f"({self.position.to_tuple()},{self.direction.to_tuple()})"

    def __str__(self) -> str:
        return f"Axis: ({self.position.to_tuple()},{self.direction.to_tuple()})"

    def copy(self) -> Axis:
        """Return copy of self"""
        # Doesn't support sub-classing
        return Axis(self.position, self.direction)

    def to_location(self) -> Location:
        """Return self as Location"""
        return Location(Plane(origin=self.position, normal=self.direction))

    def to_plane(self) -> Plane:
        """Return self as Plane"""
        return Plane(origin=self.position, normal=self.direction)

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
            other.wrapped, angular_tolerance * (math.pi / 180), linear_tolerance
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
        return self.wrapped.IsNormal(other.wrapped, angular_tolerance * (math.pi / 180))

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
        return self.wrapped.IsOpposite(
            other.wrapped, angular_tolerance * (math.pi / 180)
        )

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
        return self.wrapped.IsParallel(
            other.wrapped, angular_tolerance * (math.pi / 180)
        )

    def angle_between(self, other: Axis) -> float:
        """calculate angle between axes

        Computes the angular value, in degrees, between the direction of self and other
        between 0° and 360°.

        Args:
            other (Axis): axis to compare to

        Returns:
            float: angle between axes
        """
        return self.wrapped.Angle(other.wrapped) * 180 / math.pi

    def reversed(self) -> Axis:
        """Return a copy of self with the direction reversed"""
        return Axis.from_occt(self.wrapped.Reversed())


class BoundBox:
    """A BoundingBox for an object or set of objects. Wraps the OCP one"""

    wrapped: Bnd_Box

    xmin: float
    xmax: float
    xlen: float

    ymin: float
    ymax: float
    ylen: float

    zmin: float
    zmax: float
    zlen: float

    center: Vector
    diagonal_length: float

    def __init__(self, bb: Bnd_Box) -> None:
        self.wrapped = bb
        x_min, y_min, z_min, x_max, y_max, z_max = bb.Get()

        self.xmin = x_min
        self.xmax = x_max
        self.xlen = x_max - x_min
        self.ymin = y_min
        self.ymax = y_max
        self.ylen = y_max - y_min
        self.zmin = z_min
        self.zmax = z_max
        self.zlen = z_max - z_min

        self.center = Vector(
            (x_max + x_min) / 2, (y_max + y_min) / 2, (z_max + z_min) / 2
        )

        self.diagonal_length = self.wrapped.SquareExtent() ** 0.5

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
            bb1.xmin < bb2.xmin
            and bb1.xmax > bb2.xmax
            and bb1.ymin < bb2.ymin
            and bb1.ymax > bb2.ymax
        ):
            return bb1

        if (
            bb2.xmin < bb1.xmin
            and bb2.xmax > bb1.xmax
            and bb2.ymin < bb1.ymin
            and bb2.ymax > bb1.ymax
        ):
            return bb2

        return None

    @classmethod
    def _from_topo_ds(
        cls: Type[BoundBox],
        shape: TopoDS_Shape,
        tol: float = None,
        optimal: bool = True,
    ):
        """Constructs a bounding box from a TopoDS_Shape

        Args:
          cls: Type[BoundBox]:
          shape: TopoDS_Shape:
          tol: float:  (Default value = None)
          optimal: bool:  (Default value = True)

        Returns:

        """
        tol = TOL if tol is None else tol  # tol = TOL (by default)
        bbox = Bnd_Box()

        if optimal:
            BRepBndLib.AddOptimal_s(
                shape, bbox
            )  # this is 'exact' but expensive - not yet wrapped by PythonOCC
        else:
            mesh = BRepMesh_IncrementalMesh(shape, tol, True)
            mesh.Perform()
            # this is adds +margin but is faster
            BRepBndLib.Add_s(shape, bbox, True)

        return cls(bbox)

    def is_inside(self, b2: BoundBox) -> bool:
        """Is the provided bounding box inside this one?

        Args:
          b2: BoundBox:

        Returns:

        """
        if (
            b2.xmin > self.xmin
            and b2.ymin > self.ymin
            and b2.zmin > self.zmin
            and b2.xmax < self.xmax
            and b2.ymax < self.ymax
            and b2.zmax < self.zmax
        ):
            return True
        else:
            return False


class Location:
    """Location in 3D space. Depending on usage can be absolute or relative.

    This class wraps the TopLoc_Location class from OCCT. It can be used to move Shape
    objects in both relative and absolute manner. It is the preferred type to locate objects
    in CQ.

    Args:

    Returns:

    """

    @overload
    def __init__(self) -> None:
        """Empty location with not rotation or translation with respect to the original location."""
        ...

    @overload
    def __init__(self, t: VectorLike) -> None:
        """Location with translation t with respect to the original location."""
        ...

    @overload
    def __init__(self, t: Plane) -> None:
        """Location corresponding to the location of the Plane t."""
        ...

    @overload
    def __init__(self, t: Plane, v: VectorLike) -> None:
        """Location corresponding to the angular location of the Plane t with translation v."""
        ...

    @overload
    def __init__(self, t: TopLoc_Location) -> None:
        """Location wrapping the low-level TopLoc_Location object t"""
        ...

    @overload
    def __init__(self, t: gp_Trsf) -> None:
        """Location wrapping the low-level gp_Trsf object t"""
        ...

    @overload
    def __init__(self, t: VectorLike, ax: VectorLike, angle: float) -> None:
        """Location with translation t and rotation around ax by angle
        with respect to the original location."""
        ...

    def __init__(self, *args):

        transform = gp_Trsf()

        if len(args) == 0:
            pass
        elif len(args) == 1:
            t = args[0]

            if isinstance(t, (Vector, tuple)):
                transform.SetTranslationPart(Vector(t).wrapped)
            elif isinstance(t, Plane):
                cs = gp_Ax3(t.origin.to_pnt(), t.z_dir.to_dir(), t.x_dir.to_dir())
                transform.SetTransformation(cs)
                transform.Invert()
            elif isinstance(t, TopLoc_Location):
                self.wrapped = t
                return
            elif isinstance(t, gp_Trsf):
                transform = t
            else:
                raise TypeError("Unexpected parameters")
        elif len(args) == 2:
            t, v = args
            cs = gp_Ax3(Vector(v).to_pnt(), t.z_dir.to_dir(), t.x_dir.to_dir())
            transform.SetTransformation(cs)
            transform.Invert()
        else:
            t, ax, angle = args
            transform.SetRotation(
                gp_Ax1(Vector().to_pnt(), Vector(ax).to_dir()), angle * math.pi / 180.0
            )
            transform.SetTranslationPart(Vector(t).wrapped)

        self.wrapped = TopLoc_Location(transform)

    def __repr__(self):
        position_str = ",".join((f"{v:.2f}" for v in self.to_tuple()[0]))
        orientation_str = ",".join((f"{180*v/pi:.2f}" for v in self.to_tuple()[1]))
        return f"Location(p=({position_str}), o=({orientation_str})"

    @property
    def inverse(self) -> Location:

        return Location(self.wrapped.Inverted())

    def __mul__(self, other: Location) -> Location:

        return Location(self.wrapped * other.wrapped)

    def __pow__(self, exponent: int) -> Location:

        return Location(self.wrapped.Powered(exponent))

    def to_tuple(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Convert the location to a translation, rotation tuple."""

        t = self.wrapped.Transformation()
        trans = t.TranslationPart()
        rot = t.GetRotation()

        rv_trans = (trans.X(), trans.Y(), trans.Z())
        rv_rot = rot.GetEulerAngles(gp_EulerSequence.gp_Extrinsic_XYZ)

        return rv_trans, rv_rot

    def __repr__(self: Plane):
        """To String

        Convert Location to String for display

        Returns:
            Location as String
        """
        position_str = ",".join((f"{v:.2f}" for v in self.to_tuple()[0]))
        orientation_str = ",".join((f"{180*v/math.pi:.2f}" for v in self.to_tuple()[1]))
        return f"Location(p=({position_str}), o=({orientation_str}))"

    def position(self):
        """Extract Position component

        Args:

        Returns:
          Vector: Position part of Location

        """
        return Vector(self.to_tuple()[0])

    def rotation(self):
        """Extract Rotation component

        Args:

        Returns:
          Vector: Rotation part of Location

        """
        return Vector(self.to_tuple()[1])


class Rotation(Location):
    """Subclass of Location used only for object rotation"""

    def __init__(self, about_x: float = 0, about_y: float = 0, about_z: float = 0):
        self.about_x = about_x
        self.about_y = about_y
        self.about_z = about_z

        # Compute rotation matrix.
        rot_x = gp_Trsf()
        rot_x.SetRotation(
            gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.radians(about_x)
        )
        rot_y = gp_Trsf()
        rot_y.SetRotation(
            gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.radians(about_y)
        )
        rot_z = gp_Trsf()
        rot_z.SetRotation(
            gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(about_z)
        )
        super().__init__(Location(rot_x * rot_y * rot_z).wrapped)


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

    wrapped: gp_GTrsf

    @overload
    def __init__(self) -> None:
        ...

    @overload
    def __init__(self, matrix: Union[gp_GTrsf, gp_Trsf]) -> None:
        ...

    @overload
    def __init__(self, matrix: Sequence[Sequence[float]]) -> None:
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
                    "Matrix constructor requires 2d list of 4x3 or 4x4, but got: {!r}".format(
                        matrix
                    )
                )
            elif (len(matrix) == 4) and (tuple(matrix[3]) != (0, 0, 0, 1)):
                raise ValueError(
                    "Expected the last row to be [0,0,0,1], but got: {!r}".format(
                        matrix[3]
                    )
                )

            # Assign values to matrix
            self.wrapped = gp_GTrsf()
            [
                self.wrapped.SetValue(i + 1, j + 1, e)
                for i, row in enumerate(matrix[:3])
                for j, e in enumerate(row)
            ]

        else:
            raise TypeError("Invalid param to matrix constructor: {}".format(matrix))

    def rotate_x(self, angle: float):

        self._rotate(gp.OX_s(), angle)

    def rotate_y(self, angle: float):

        self._rotate(gp.OY_s(), angle)

    def rotate_z(self, angle: float):

        self._rotate(gp.OZ_s(), angle)

    def _rotate(self, direction: gp_Ax1, angle: float):

        new = gp_Trsf()
        new.SetRotation(direction, angle)

        self.wrapped = self.wrapped * gp_GTrsf(new)

    def inverse(self) -> Matrix:

        return Matrix(self.wrapped.Inverted())

    @overload
    def multiply(self, other: Vector) -> Vector:
        ...

    @overload
    def multiply(self, other: Matrix) -> Matrix:
        ...

    def multiply(self, other):

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

    def __getitem__(self, rc: tuple[int, int]) -> float:
        """Provide Matrix[r, c] syntax for accessing individual values. The row
        and column parameters start at zero, which is consistent with most
        python libraries, but is counter to gp_GTrsf(), which is 1-indexed.
        """
        if not isinstance(rc, tuple) or (len(rc) != 2):
            raise IndexError("Matrix subscript must provide (row, column)")
        (r, c) = rc
        if (0 <= r <= 3) and (0 <= c <= 3):
            if r < 3:
                return self.wrapped.Value(r + 1, c + 1)
            else:
                # gp_GTrsf doesn't provide access to the 4th row because it has
                # an implied value as below:
                return [0.0, 0.0, 0.0, 1.0][c]
        else:
            raise IndexError("Out of bounds access into 4x4 matrix: {!r}".format(rc))

    def __repr__(self) -> str:
        """
        Generate a valid python expression representing this Matrix
        """
        matrix_transposed = self.transposed_list()
        matrix_str = ",\n        ".join(str(matrix_transposed[i::4]) for i in range(4))
        return f"Matrix([{matrix_str}])"


class Mixin1D:
    def _bounds(self) -> Tuple[float, float]:

        curve = self._geom_adaptor()
        return curve.FirstParameter(), curve.LastParameter()

    def start_point(self) -> Vector:
        """:return: a vector representing the start point of this edge

        Note, circles may have the start and end points the same

        Args:

        Returns:

        """

        curve = self._geom_adaptor()
        umin = curve.FirstParameter()

        return Vector(curve.Value(umin))

    def end_point(self) -> Vector:
        """:return: a vector representing the end point of this edge.

        Note, circles may have the start and end points the same

        Args:

        Returns:

        """

        curve = self._geom_adaptor()
        umax = curve.LastParameter()

        return Vector(curve.Value(umax))

    def param_at(self, d: float) -> float:
        """Compute parameter value at the specified normalized distance.

        Args:
          d: normalized distance [0, 1]
          d: float:

        Returns:
          parameter value

        """

        curve = self._geom_adaptor()

        l = GCPnts_AbscissaPoint.Length_s(curve)
        return GCPnts_AbscissaPoint(curve, l * d, curve.FirstParameter()).Parameter()

    def tangent_at(
        self,
        location_param: float = 0.5,
        mode: Literal["length", "parameter"] = "length",
    ) -> Vector:
        """Compute tangent vector at the specified location.

        Args:
          location_param: distance or parameter value (default: 0.5)
          mode: position calculation mode (default: parameter)
          location_param: float:  (Default value = 0.5)
          mode: Literal["length":
          "parameter"]:  (Default value = "length")

        Returns:
          tangent vector

        """

        curve = self._geom_adaptor()

        tmp = gp_Pnt()
        res = gp_Vec()

        if mode == "length":
            param = self.param_at(location_param)
        else:
            param = location_param

        curve.D1(param, tmp, res)

        return Vector(gp_Dir(res))

    def normal(self) -> Vector:
        """Calculate the normal Vector. Only possible for planar curves.

        :return: normal vector

        Args:

        Returns:

        """

        curve = self._geom_adaptor()
        gtype = self.geom_type()

        if gtype == "CIRCLE":
            circ = curve.Circle()
            return_value = Vector(circ.Axis().Direction())
        elif gtype == "ELLIPSE":
            ell = curve.Ellipse()
            return_value = Vector(ell.Axis().Direction())
        else:
            fs = BRepLib_FindSurface(self.wrapped, OnlyPlane=True)
            surf = fs.Surface()

            if isinstance(surf, Geom_Plane):
                pln = surf.Pln()
                return_value = Vector(pln.Axis().Direction())
            else:
                raise ValueError("Normal not defined")

        return return_value

    def center(self) -> Vector:

        properties = GProp_GProps()
        BRepGProp.LinearProperties_s(self.wrapped, properties)

        return Vector(properties.CentreOfMass())

    def length(self) -> float:

        return GCPnts_AbscissaPoint.Length_s(self._geom_adaptor())

    def radius(self) -> float:
        """Calculate the radius.

        Note that when applied to a Wire, the radius is simply the radius of the first edge.

        Args:

        Returns:
          radius

        Raises:
          ValueError: if kernel can not reduce the shape to a circular edge

        """
        geom = self._geom_adaptor()
        try:
            circ = geom.Circle()
        except (Standard_NoSuchObject, Standard_Failure) as e:
            raise ValueError("Shape could not be reduced to a circle") from e
        return circ.Radius()

    def is_closed(self) -> bool:

        return BRep_Tool.IsClosed_s(self.wrapped)

    def position_at(
        self,
        d: float,
        mode: Literal["length", "parameter"] = "length",
    ) -> Vector:
        """Generate a position along the underlying curve.

        Args:
          d: distance or parameter value
          mode: position calculation mode (default: length)
          d: float:
          mode: Literal["length":
          "parameter"]:  (Default value = "length")

        Returns:
          A Vector on the underlying curve located at the specified d value.

        """

        curve = self._geom_adaptor()

        if mode == "length":
            param = self.param_at(d)
        else:
            param = d

        return Vector(curve.Value(param))

    def positions(
        self,
        ds: Iterable[float],
        mode: Literal["length", "parameter"] = "length",
    ) -> list[Vector]:
        """Generate positions along the underlying curve

        Args:
          ds: distance or parameter values
          mode: position calculation mode (default: length)
          ds: Iterable[float]:
          mode: Literal["length":
          "parameter"]:  (Default value = "length")

        Returns:
          A list of Vector objects.

        """

        return [self.position_at(d, mode) for d in ds]

    def location_at(
        self,
        d: float,
        mode: Literal["length", "parameter"] = "length",
        frame: Literal["frenet", "corrected"] = "frenet",
        planar: bool = False,
    ) -> Location:
        """Generate a location along the underlying curve.

        Args:
          d: distance or parameter value
          mode: position calculation mode (default: length)
          frame: moving frame calculation method (default: frenet)
          planar: planar mode
          d: float:
          mode: Literal["length":
          "parameter"]:  (Default value = "length")
          frame: Literal["frenet":
          "corrected"]:  (Default value = "frenet")
          planar: bool:  (Default value = False)

        Returns:
          A Location object representing local coordinate system at the specified distance.

        """

        curve, curveh = self._geom_adaptor_h()

        if mode == "length":
            param = self.param_at(d)
        else:
            param = d

        law: GeomFill_TrihedronLaw
        if frame == "frenet":
            law = GeomFill_Frenet()
        else:
            law = GeomFill_CorrectedFrenet()

        law.SetCurve(curveh)

        tangent, normal, binormal = gp_Vec(), gp_Vec(), gp_Vec()

        law.D0(param, tangent, normal, binormal)
        pnt = curve.Value(param)

        t = gp_Trsf()
        if planar:
            t.SetTransformation(
                gp_Ax3(pnt, gp_Dir(0, 0, 1), gp_Dir(normal.XYZ())), gp_Ax3()
            )
        else:
            t.SetTransformation(
                gp_Ax3(pnt, gp_Dir(tangent.XYZ()), gp_Dir(normal.XYZ())), gp_Ax3()
            )

        return Location(TopLoc_Location(t))

    def locations(
        self,
        ds: Iterable[float],
        mode: Literal["length", "parameter"] = "length",
        frame: Literal["frenet", "corrected"] = "frenet",
        planar: bool = False,
    ) -> list[Location]:
        """Generate location along the curve

        Args:
          ds: distance or parameter values
          mode: position calculation mode (default: length)
          frame: moving frame calculation method (default: frenet)
          planar: planar mode
          ds: Iterable[float]:
          mode: Literal["length":
          "parameter"]:  (Default value = "length")
          frame: Literal["frenet":
          "corrected"]:  (Default value = "frenet")
          planar: bool:  (Default value = False)

        Returns:
          A list of Location objects representing local coordinate systems at the specified distances.

        """

        return [self.location_at(d, mode, frame, planar) for d in ds]

    def __matmul__(wire_edge: Union[Edge, Wire], position: float):
        return wire_edge.position_at(position)

    def __mod__(wire_edge: Union[Edge, Wire], position: float):
        return wire_edge.tangent_at(position)

    def project(
        self, face: Face, d: VectorLike, closest: bool = True
    ) -> Union[Mixin1D, list[Mixin1D]]:
        """Project onto a face along the specified direction

        Args:
          face: Face:
          d: VectorLike:
          closest: bool:  (Default value = True)

        Returns:

        """

        bldr = BRepProj_Projection(self.wrapped, face.wrapped, Vector(d).to_dir())
        shapes = Compound(bldr.Shape())

        # select the closest projection if requested
        return_value: Union[Mixin1D, list[Mixin1D]]

        if closest:

            dist_calc = BRepExtrema_DistShapeShape()
            dist_calc.LoadS1(self.wrapped)

            min_dist = inf

            for el in shapes:
                dist_calc.LoadS2(el.wrapped)
                dist_calc.Perform()
                dist = dist_calc.Value()

                if dist < min_dist:
                    min_dist = dist
                    return_value = tcast(Mixin1D, el)

        else:
            return_value = [tcast(Mixin1D, el) for el in shapes]

        return return_value


class Mixin3D:
    def fillet(self: Any, radius: float, edge_list: Iterable[Edge]) -> Any:
        """Fillets the specified edges of this solid.

        Args:
          radius: float > 0, the radius of the fillet
          edge_list: a list of Edge objects, which must belong to this solid
          self: Any:
          radius: float:
          edge_list: Iterable[Edge]:

        Returns:
          Filleted solid

        """
        native_edges = [e.wrapped for e in edge_list]

        fillet_builder = BRepFilletAPI_MakeFillet(self.wrapped)

        for e in native_edges:
            fillet_builder.Add(radius, e)

        return self.__class__(fillet_builder.Shape())

    def chamfer(
        self: Any, length: float, length2: Optional[float], edge_list: Iterable[Edge]
    ) -> Any:
        """Chamfers the specified edges of this solid.

        Args:
          length: length > 0, the length (length) of the chamfer
          length2: length2 > 0, optional parameter for asymmetrical chamfer. Should be `None` if not required.
          edge_list: a list of Edge objects, which must belong to this solid
          self: Any:
          length: float:
          length2: Optional[float]:
          edge_list: Iterable[Edge]:

        Returns:
          Chamfered solid

        """
        native_edges = [e.wrapped for e in edge_list]

        # make a edge --> faces mapping
        edge_face_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            self.wrapped, ta.TopAbs_EDGE, ta.TopAbs_FACE, edge_face_map
        )

        # note: we prefer 'length' word to 'radius' as opposed to FreeCAD's API
        chamfer_builder = BRepFilletAPI_MakeChamfer(self.wrapped)

        if length2:
            d1 = length
            d2 = length2
        else:
            d1 = length
            d2 = length

        for e in native_edges:
            face = edge_face_map.FindFromKey(e).First()
            chamfer_builder.Add(
                d1, d2, e, TopoDS.Face_s(face)
            )  # NB: edge_face_map return a generic TopoDS_Shape
        return self.__class__(chamfer_builder.Shape())

    def shell(
        self: Any,
        face_list: Optional[Iterable[Face]],
        thickness: float,
        tolerance: float = 0.0001,
        kind: Literal["arc", "intersection"] = "arc",
    ) -> Any:
        """Make a shelled solid of self.

        Args:
          face_list: List of faces to be removed, which must be part of the solid. Can
        be an empty list.
          thickness: Floating point thickness. Positive shells outwards, negative
        shells inwards.
          tolerance: Modelling tolerance of the method, default=0.0001.
          self: Any:
          face_list: Optional[Iterable[Face]]:
          thickness: float:
          tolerance: float:  (Default value = 0.0001)
          kind: Literal["arc":
          "intersection"]:  (Default value = "arc")

        Returns:
          A shelled solid.

        """

        kind_dict = {
            "arc": GeomAbs_JoinType.GeomAbs_Arc,
            "intersection": GeomAbs_JoinType.GeomAbs_Intersection,
        }

        occ_faces_list = TopTools_ListOfShape()
        shell_builder = BRepOffsetAPI_MakeThickSolid()

        if face_list:
            for f in face_list:
                occ_faces_list.Append(f.wrapped)

        shell_builder.MakeThickSolidByJoin(
            self.wrapped,
            occ_faces_list,
            thickness,
            tolerance,
            Intersection=True,
            Join=kind_dict[kind],
        )
        shell_builder.Build()

        if face_list:
            return_value = self.__class__(shell_builder.Shape())

        else:  # if no faces provided a watertight solid will be constructed
            s1 = self.__class__(shell_builder.Shape()).shells()[0].wrapped
            s2 = self.shells()[0].wrapped

            # s1 can be outer or inner shell depending on the thickness sign
            if thickness > 0:
                sol = BRepBuilderAPI_MakeSolid(s1, s2)
            else:
                sol = BRepBuilderAPI_MakeSolid(s2, s1)

            # fix needed for the orientations
            return_value = self.__class__(sol.Shape()).fix()

        return return_value

    def is_inside(self, point: VectorLike, tolerance: float = 1.0e-6) -> bool:
        """Returns whether or not the point is inside a solid or compound
        object within the specified tolerance.

        Args:
          point: tuple or Vector representing 3D point to be tested
          tolerance: tolerance for inside determination, default=1.0e-6
          point: VectorLike:
          tolerance: float:  (Default value = 1.0e-6)

        Returns:
          bool indicating whether or not point is within solid

        """
        if isinstance(point, Vector):
            point = point.to_tuple()

        solid_classifier = BRepClass3d_SolidClassifier(self.wrapped)
        solid_classifier.Perform(gp_Pnt(*point), tolerance)

        return solid_classifier.State() == ta.TopAbs_IN or solid_classifier.IsOnAFace()

    def dprism_from_wires(
        self,
        basis: Optional[Face],
        profiles: list[Wire],
        depth: float = None,
        taper: float = 0,
        up_to_face: Face = None,
        thru_all: bool = True,
        additive: bool = True,
    ) -> Solid:
        """Make a prismatic feature (additive or subtractive)

        Args:
          basis: face to perform the operation on
          profiles: list of profiles
          depth: depth of the cut or extrusion
          taper: float:  (Default value = 0)
          up_to_face: a face to extrude until
          thru_all: cut thru_all
          additive: bool:  (Default value = True)

        Returns:
          a Solid object

        """

        sorted_profiles = sort_wires_by_build_order(profiles)
        faces = [Face.make_from_wires(p[0], p[1:]) for p in sorted_profiles]

        return self.dprism(basis, faces, depth, taper, up_to_face, thru_all, additive)

    def dprism(
        self,
        basis: Optional[Face],
        faces: list[Face],
        depth: float = None,
        taper: float = 0,
        up_to_face: Face = None,
        thru_all: bool = True,
        additive: bool = True,
    ) -> Solid:

        shape: Union[TopoDS_Shape, TopoDS_Solid] = self.wrapped
        for face in faces:
            feat = BRepFeat_MakeDPrism(
                shape,
                face.wrapped,
                basis.wrapped if basis else TopoDS_Face(),
                taper * DEG2RAD,
                additive,
                False,
            )

            if up_to_face is not None:
                feat.Perform(up_to_face.wrapped)
            elif thru_all or depth is None:
                feat.PerformThruAll()
            else:
                feat.Perform(depth)

            shape = feat.Shape()

        return self.__class__(shape)


class Shape:
    """Represents a shape in the system. Wraps TopoDS_Shape."""

    def __init__(self, obj: TopoDS_Shape):
        self.wrapped = downcast(obj)

        self.for_construction = False
        # Helps identify this solid through the use of an ID
        self.label = ""

    def clean(self) -> Shape:
        """clean - remove internal edges

        Args:
          self: Shape:

        Returns:

        """
        # Try BRepTools.RemoveInternals here
        upgrader = ShapeUpgrade_UnifySameDomain(self.wrapped, True, True, True)
        upgrader.AllowInternalEdges(False)
        # upgrader.SetAngularTolerance(1e-5)
        upgrader.Build()
        self.wrapped = downcast(upgrader.Shape())
        return self

    def fix(self: Shape) -> Shape:
        """fix - try to fix shape if not valid

        Args:
          self: Shape:

        Returns:

        """
        if not self.is_valid():
            shape_copy: Shape = self.copy()
            shape_copy.wrapped = fix(self.wrapped)

            return shape_copy

        return self

    @classmethod
    def cast(cls, obj: TopoDS_Shape, for_construction: bool = False) -> Shape:
        "Returns the right type of wrapper, given a OCCT object"

        tr = None

        # define the shape lookup table for casting
        constructor__lut = {
            ta.TopAbs_VERTEX: Vertex,
            ta.TopAbs_EDGE: Edge,
            ta.TopAbs_WIRE: Wire,
            ta.TopAbs_FACE: Face,
            ta.TopAbs_SHELL: Shell,
            ta.TopAbs_SOLID: Solid,
            ta.TopAbs_COMPOUND: Compound,
        }

        t = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        tr = constructor__lut[t](downcast(obj))
        tr.for_construction = for_construction

        return tr

    def export_stl(
        self,
        file_name: str,
        tolerance: float = 1e-3,
        angular_tolerance: float = 0.1,
        ascii: bool = False,
    ) -> bool:
        """Exports a shape to a specified STL file.

        Args:
          file_name: The path and file name to write the STL output to.
          tolerance: A linear deflection setting which limits the distance between a curve and its tessellation.
        Setting this value too low will result in large meshes that can consume computing resources.
        Setting the value too high can result in meshes with a level of detail that is too low.
        Default is 1e-3, which is a good starting point for a range of cases.
          angular_tolerance: Angular deflection setting which limits the angle between subsequent segments in a polyline. Default is 0.1.
          ascii: Export the file as ASCII (True) or binary (False) STL format.  Default is binary.
          file_name: str:
          tolerance: float:  (Default value = 1e-3)
          angular_tolerance: float:  (Default value = 0.1)
          ascii: bool:  (Default value = False)

        Returns:

        """

        mesh = BRepMesh_IncrementalMesh(
            self.wrapped, tolerance, True, angular_tolerance
        )
        mesh.Perform()

        writer = StlAPI_Writer()

        if ascii:
            writer.ASCIIMode = True
        else:
            writer.ASCIIMode = False

        return writer.Write(self.wrapped, file_name)

    def export_step(self, file_name: str, **kwargs) -> IFSelect_ReturnStatus:
        """Export this shape to a STEP file.

        kwargs is used to provide optional keyword arguments to configure the exporter.

        Args:
          file_name: Path and filename for writing.
          write_pcurves(boolean): Enable or disable writing parametric curves to the STEP file. Default True.

        If False, writes STEP file without pcurves. This decreases the size of the resulting STEP file.
          precision_mode(int): Controls the uncertainty value for STEP entities. Specify -1, 0, or 1. Default 0.
        See OCCT documentation.
          file_name: str:
          **kwargs:

        Returns:

        """

        # Handle the extra settings for the STEP export
        pcurves = 1
        if "write_pcurves" in kwargs and not kwargs["write_pcurves"]:
            pcurves = 0
        precision_mode = kwargs["precision_mode"] if "precision_mode" in kwargs else 0

        writer = STEPControl_Writer()
        Interface_Static.SetIVal_s("write.surfacecurve.mode", pcurves)
        Interface_Static.SetIVal_s("write.precision.mode", precision_mode)
        writer.Transfer(self.wrapped, STEPControl_AsIs)

        return writer.Write(file_name)

    def export_brep(self, f: Union[str, BytesIO]) -> bool:
        """Export this shape to a BREP file

        Args:
          f: Union[str, BytesIO]:

        Returns:

        """

        return_value = BRepTools.Write_s(self.wrapped, f)

        return True if return_value is None else return_value

    @classmethod
    def import_brep(cls, f: Union[str, BytesIO]) -> Shape:
        """Import shape from a BREP file

        Args:
          f: Union[str, BytesIO]:

        Returns:

        """
        s = TopoDS_Shape()
        builder = BRep_Builder()

        BRepTools.Read_s(s, f, builder)

        if s.IsNull():
            raise ValueError(f"Could not import {f}")

        return cls.cast(s)

    def geom_type(self) -> Geoms:
        """Gets the underlying geometry type.

        Implementations can return any values desired, but the values the user
        uses in type filters should correspond to these.

        As an example, if a user does::

            CQ(object).faces("%mytype")

        The expectation is that the geom_type attribute will return 'mytype'

        The return values depend on the type of the shape:

        | Vertex:  always Vertex
        | Edge:   LINE, ARC, CIRCLE, SPLINE
        | Face:   PLANE, SPHERE, CONE
        | Solid:  Solid
        | Shell:  Shell
        | Compound: Compound
        | Wire:   Wire

        Args:

        Returns:
          A string according to the geometry type

        """

        tr: Any = geom_LUT[shapetype(self.wrapped)]

        if isinstance(tr, str):
            return_value = tr
        elif tr is BRepAdaptor_Curve:
            return_value = geom_LUT_EDGE[tr(self.wrapped).GetType()]
        else:
            return_value = geom_LUT_FACE[tr(self.wrapped).GetType()]

        return tcast(Geoms, return_value)

    def hash_code(self) -> int:
        """Returns a hashed value denoting this shape. It is computed from the
        TShape and the Location. The Orientation is not used.

        Args:

        Returns:

        """
        return self.wrapped.HashCode(HASH_CODE_MAX)

    def is_null(self) -> bool:
        """Returns true if this shape is null. In other words, it references no
        underlying shape with the potential to be given a location and an
        orientation.

        Args:

        Returns:

        """
        return self.wrapped.IsNull()

    def is_same(self, other: Shape) -> bool:
        """Returns True if other and this shape are same, i.e. if they share the
        same TShape with the same Locations. Orientations may differ. Also see
        :py:meth:`is_equal`

        Args:
          other: Shape:

        Returns:

        """
        return self.wrapped.IsSame(other.wrapped)

    def is_equal(self, other: Shape) -> bool:
        """Returns True if two shapes are equal, i.e. if they share the same
        TShape with the same Locations and Orientations. Also see
        :py:meth:`is_same`.

        Args:
          other: Shape:

        Returns:

        """
        return self.wrapped.IsEqual(other.wrapped)

    def is_valid(self) -> bool:
        """Returns True if no defect is detected on the shape S or any of its
        subshapes. See the OCCT docs on BRepCheck_Analyzer::IsValid for a full
        description of what is checked.

        Args:

        Returns:

        """
        return BRepCheck_Analyzer(self.wrapped).IsValid()

    def bounding_box(
        self, tolerance: float = None
    ) -> BoundBox:  # need to implement that in GEOM
        """
        Create a bounding box for this Shape.

        :param tolerance: Tolerance value passed to :py:class:`BoundBox`
        :returns: A :py:class:`BoundBox` object for this Shape
        """
        return BoundBox._from_topo_ds(self.wrapped, tol=tolerance)

    def mirror(
        self,
        mirrorPlane: Union[
            Literal["XY", "YX", "XZ", "ZX", "YZ", "ZY"], VectorLike
        ] = "XY",
        basePointVector: VectorLike = (0, 0, 0),
    ) -> Shape:
        """
        Applies a mirror transform to this Shape. Does not duplicate objects
        about the plane.

        Args:
          mirror_plane: The direction of the plane to mirror about - one of 'XY', 'XZ' or 'YZ'
          base_point_vector: The origin of the plane to mirror about
        Returns:
          The mirrored shape
        """
        if isinstance(mirrorPlane, str):
            if mirrorPlane == "XY" or mirrorPlane == "YX":
                mirrorPlaneNormalVector = gp_Dir(0, 0, 1)
            elif mirrorPlane == "XZ" or mirrorPlane == "ZX":
                mirrorPlaneNormalVector = gp_Dir(0, 1, 0)
            elif mirrorPlane == "YZ" or mirrorPlane == "ZY":
                mirrorPlaneNormalVector = gp_Dir(1, 0, 0)
        else:
            if isinstance(mirrorPlane, tuple):
                mirrorPlaneNormalVector = gp_Dir(*mirrorPlane)
            elif isinstance(mirrorPlane, Vector):
                mirrorPlaneNormalVector = mirrorPlane.toDir()

        if isinstance(basePointVector, tuple):
            basePointVector = Vector(basePointVector)

        T = gp_Trsf()
        T.SetMirror(
            gp_Ax2(gp_Pnt(*basePointVector.to_tuple()), mirrorPlaneNormalVector)
        )

        return self._apply_transform(T)

    @staticmethod
    def _center_of_mass(shape: Shape) -> Vector:

        properties = GProp_GProps()
        BRepGProp.volumeProperties_s(shape.wrapped, properties)

        return Vector(properties.CentreOfMass())

    def center(self) -> Vector:
        """

        Args:

        Returns:
          The point of the center of mass of this Shape

        """

        return Shape.center_of_mass(self)

    def center_of_bound_box(self, tolerance: float = None) -> Vector:
        """

        Args:
          tolerance: Tolerance passed to the :py:meth:`bounding_box` method
          tolerance: float:  (Default value = None)

        Returns:
          center of the bounding box of this shape

        """
        return self.bounding_box(tolerance=tolerance).center

    @staticmethod
    def combined_center(objects: Iterable[Shape]) -> Vector:
        """Calculates the center of mass of multiple objects.

        Args:
          objects: A list of objects with mass
          objects: Iterable[Shape]:

        Returns:

        """
        total_mass = sum(Shape.compute_mass(o) for o in objects)
        weighted_centers = [
            Shape.center_of_mass(o).multiply(Shape.compute_mass(o)) for o in objects
        ]

        sum_wc = weighted_centers[0]
        for wc in weighted_centers[1:]:
            sum_wc = sum_wc.add(wc)

        return Vector(sum_wc.multiply(1.0 / total_mass))

    @staticmethod
    def compute_mass(obj: Shape) -> float:
        """Calculates the 'mass' of an object.

        Args:
          obj: Compute the mass of this object
          obj: Shape:

        Returns:

        """
        properties = GProp_GProps()
        calc_function = shape_properties_LUT[shapetype(obj.wrapped)]

        if calc_function:
            calc_function(obj.wrapped, properties)
            return properties.Mass()
        else:
            raise NotImplementedError

    @staticmethod
    def center_of_mass(obj: Shape) -> Vector:
        """Calculates the center of 'mass' of an object.

        Args:
          obj: Compute the center of mass of this object
          obj: Shape:

        Returns:

        """
        properties = GProp_GProps()
        calc_function = shape_properties_LUT[shapetype(obj.wrapped)]

        if calc_function:
            calc_function(obj.wrapped, properties)
            return Vector(properties.CentreOfMass())
        else:
            raise NotImplementedError

    @staticmethod
    def combined_center_of_bound_box(objects: list[Shape]) -> Vector:
        """Calculates the center of a bounding box of multiple objects.

        Args:
          objects: A list of objects
          objects: list[Shape]:

        Returns:

        """
        total_mass = len(objects)

        weighted_centers = []
        for o in objects:
            weighted_centers.append(BoundBox._from_topo_ds(o.wrapped).center)

        sum_wc = weighted_centers[0]
        for wc in weighted_centers[1:]:
            sum_wc = sum_wc.add(wc)

        return Vector(sum_wc.multiply(1.0 / total_mass))

    def closed(self) -> bool:
        """

        Args:

        Returns:
          The closedness flag

        """
        return self.wrapped.closed()

    def shape_type(self) -> Shapes:
        return tcast(Shapes, shape_LUT[shapetype(self.wrapped)])

    def _entities(self, topo_type: Shapes) -> list[TopoDS_Shape]:

        out = {}  # using dict to prevent duplicates

        explorer = TopExp_Explorer(self.wrapped, inverse_shape_LUT[topo_type])

        while explorer.More():
            item = explorer.Current()
            out[
                item.HashCode(HASH_CODE_MAX)
            ] = item  # needed to avoid pseudo-duplicate entities
            explorer.Next()

        return list(out.values())

    def _entities_from(
        self, child_type: Shapes, parent_type: Shapes
    ) -> Dict[Shape, list[Shape]]:

        res = TopTools_IndexedDataMapOfShapeListOfShape()

        TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            self.wrapped,
            inverse_shape_LUT[child_type],
            inverse_shape_LUT[parent_type],
            res,
        )

        out: Dict[Shape, list[Shape]] = {}
        for i in range(1, res.Extent() + 1):
            out[Shape.cast(res.FindKey(i))] = [
                Shape.cast(el) for el in res.FindFromIndex(i)
            ]

        return out

    def vertices(self) -> ShapeList["Vertex"]:
        """

        Args:

        Returns:
          All the vertices in this Shape

        """

        return ShapeList([Vertex(i) for i in self._entities(Vertex.__name__)])

    def edges(self) -> ShapeList["Edge"]:
        """

        Args:

        Returns:
          All the edges in this Shape

        """

        return ShapeList(
            [
                Edge(i)
                for i in self._entities(Edge.__name__)
                if not BRep_Tool.Degenerated_s(TopoDS.Edge_s(i))
            ]
        )

    def compounds(self) -> ShapeList["Compound"]:
        """

        Args:

        Returns:
          All the compounds in this Shape

        """

        return ShapeList([Compound(i) for i in self._entities(Compound.__name__)])

    def wires(self) -> ShapeList["Wire"]:
        """

        Args:

        Returns:
          All the wires in this Shape

        """

        return ShapeList([Wire(i) for i in self._entities(Wire.__name__)])

    def faces(self) -> ShapeList["Face"]:
        """

        Args:

        Returns:
          All the faces in this Shape

        """

        return ShapeList([Face(i) for i in self._entities(Face.__name__)])

    def shells(self) -> ShapeList["Shell"]:
        """

        Args:

        Returns:
          All the shells in this Shape

        """

        return ShapeList([Shell(i) for i in self._entities(Shell.__name__)])

    def solids(self) -> ShapeList["Solid"]:
        """

        Args:

        Returns:
          All the solids in this Shape

        """

        return ShapeList([Solid(i) for i in self._entities(Solid.__name__)])

    def area(self) -> float:
        """

        Args:

        Returns:
          The surface area of all faces in this Shape

        """
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(self.wrapped, properties)

        return properties.Mass()

    def volume(self) -> float:
        """

        Args:

        Returns:
          The volume of this Shape

        """
        # when density == 1, mass == volume
        return Shape.compute_mass(self)

    def _apply_transform(self: Shape, tr: gp_Trsf) -> Shape:
        """_apply_transform

        Apply the provided transformation matrix to a copy of Shape

        Args:
          tr(gp_Trsf): transformation matrix
          self: Shape:
          tr: gp_Trsf:

        Returns:
          Shape: copy of transformed Shape

        """
        shape_copy: Shape = self.copy()
        transformed_shape = BRepBuilderAPI_Transform(
            shape_copy.wrapped, tr, True
        ).Shape()
        shape_copy.wrapped = downcast(transformed_shape)
        return shape_copy

    def rotate(
        self, start_vector: VectorLike, end_vector: VectorLike, angle_degrees: float
    ) -> Shape:
        """Rotates a shape around an axis.

        Args:
          start_vector(either a 3-tuple or a Vector): start point of rotation axis
          end_vector(either a 3-tuple or a Vector): end point of rotation axis
          angle_degrees: angle to rotate, in degrees
          start_vector: VectorLike:
          end_vector: VectorLike:
          angle_degrees: float:

        Returns:
          a copy of the shape, rotated

        """
        if type(start_vector) == tuple:
            start_vector = Vector(start_vector)

        if type(end_vector) == tuple:
            end_vector = Vector(end_vector)

        tr = gp_Trsf()
        tr.SetRotation(
            gp_Ax1(
                Vector(start_vector).to_pnt(),
                (Vector(end_vector) - Vector(start_vector)).to_dir(),
            ),
            angle_degrees * DEG2RAD,
        )

        return self._apply_transform(tr)

    def translate(self, vector: VectorLike) -> Shape:
        """Translates this shape through a transformation.

        Args:
          vector: VectorLike:

        Returns:

        """

        t = gp_Trsf()
        t.SetTranslation(Vector(vector).wrapped)

        return self._apply_transform(t)

    def scale(self, factor: float) -> Shape:
        """Scales this shape through a transformation.

        Args:
          factor: float:

        Returns:

        """

        t = gp_Trsf()
        t.SetScale(gp_Pnt(), factor)

        return self._apply_transform(t)

    def copy(self: Shape) -> Shape:
        """Creates a new object that is a copy of this object.

        Args:
          self: Shape:

        Returns:

        """
        # The wrapped object is a OCCT TopoDS_Shape which can't be pickled or copied
        # with the standard python copy/deepcopy, so create a deepcopy 'memo' with this
        # value already copied which causes deepcopy to skip it.
        memo = {id(self.wrapped): downcast(BRepBuilderAPI_Copy(self.wrapped).Shape())}
        copy_of_shape = copy.deepcopy(self, memo)
        return copy_of_shape

    def transform_shape(self, t_matrix: Matrix) -> Shape:
        """Transforms this Shape by t_matrix. Also see :py:meth:`transform_geometry`.

        Args:
          t_matrix: The transformation matrix
          t_matrix: Matrix:

        Returns:
          a copy of the object, transformed by the provided matrix,
          with all objects keeping their type

        """

        r = Shape.cast(
            BRepBuilderAPI_Transform(self.wrapped, t_matrix.wrapped.Trsf()).Shape()
        )
        r.for_construction = self.for_construction

        return r

    def transform_geometry(self, t_matrix: Matrix) -> Shape:
        """Transforms this shape by t_matrix.

        WARNING: transform_geometry will sometimes convert lines and circles to
        splines, but it also has the ability to handle skew and stretching
        transformations.

        If your transformation is only translation and rotation, it is safer to
        use :py:meth:`transform_shape`, which doesn't change the underlying type
        of the geometry, but cannot handle skew transformations.

        Args:
          t_matrix: The transformation matrix
          t_matrix: Matrix:

        Returns:
          a copy of the object, but with geometry transformed instead
          of just rotated.

        """
        r = Shape.cast(
            BRepBuilderAPI_GTransform(self.wrapped, t_matrix.wrapped, True).Shape()
        )
        r.for_construction = self.for_construction

        return r

    def location(self) -> Location:
        return Location(self.wrapped.Location())

    def locate(self, loc: Location) -> Shape:
        """Apply a location in absolute sense to self

        Args:
          loc: Location:

        Returns:

        """

        self.wrapped.Location(loc.wrapped)

        return self

    def located(self: Shape, loc: Location) -> Shape:
        """located

        Apply a location in absolute sense to a copy of self

        Args:
          loc(Location): new absolute location
          self: Shape:
          loc: Location:

        Returns:
          Shape: copy of Shape at location

        """
        shape_copy: Shape = self.copy()
        shape_copy.wrapped.Location(loc.wrapped)
        return shape_copy

    def move(self, loc: Location) -> Shape:
        """Apply a location in relative sense (i.e. update current location) to self

        Args:
          loc: Location:

        Returns:

        """

        self.wrapped.Move(loc.wrapped)

        return self

    def moved(self: Shape, loc: Location) -> Shape:
        """moved

        Apply a location in relative sense (i.e. update current location) to a copy of self

        Args:
          loc(Location): new location relative to current location
          self: Shape:
          loc: Location:

        Returns:
          Shape: copy of Shape moved to relative location

        """
        shape_copy: Shape = self.copy()
        shape_copy.wrapped = downcast(shape_copy.wrapped.Moved(loc.wrapped))
        return shape_copy

    def __hash__(self) -> int:

        return self.hash_code()

    def __eq__(self, other) -> bool:

        return self.is_same(other) if isinstance(other, Shape) else False

    def _bool_op(
        self,
        args: Iterable[Shape],
        tools: Iterable[Shape],
        op: Union[BRepAlgoAPI_BooleanOperation, BRepAlgoAPI_Splitter],
    ) -> Shape:
        """Generic boolean operation

        Args:
          args: Iterable[Shape]:
          tools: Iterable[Shape]:
          op: Union[BRepAlgoAPI_BooleanOperation:
          BRepAlgoAPI_Splitter]:

        Returns:

        """

        arg = TopTools_ListOfShape()
        for obj in args:
            arg.Append(obj.wrapped)

        tool = TopTools_ListOfShape()
        for obj in tools:
            tool.Append(obj.wrapped)

        op.SetArguments(arg)
        op.SetTools(tool)

        op.SetRunParallel(True)
        op.Build()

        return Shape.cast(op.Shape())

    def cut(self, *toCut: Shape) -> Shape:
        """Remove the positional arguments from this Shape.

        Args:
          *toCut: Shape:

        Returns:

        """

        cut_op = BRepAlgoAPI_Cut()

        return self._bool_op((self,), toCut, cut_op)

    def fuse(self, *toFuse: Shape, glue: bool = False, tol: float = None) -> Shape:
        """Fuse the positional arguments with this Shape.

        Args:
          glue: Sets the glue option for the algorithm, which allows
        increasing performance of the intersection of the input shapes
          tol: Additional tolerance
          *toFuse: Shape:
          glue: bool:  (Default value = False)
          tol: float:  (Default value = None)

        Returns:

        """

        fuse_op = BRepAlgoAPI_Fuse()
        if glue:
            fuse_op.SetGlue(BOPAlgo_GlueEnum.BOPAlgo_GlueShift)
        if tol:
            fuse_op.SetFuzzyValue(tol)

        return_value = self._bool_op((self,), toFuse, fuse_op)

        return return_value

    def intersect(self, *toIntersect: Shape) -> Shape:
        """Intersection of the positional arguments and this Shape.

        Args:
          *toIntersect: Shape:

        Returns:

        """

        intersect_op = BRepAlgoAPI_Common()

        return self._bool_op((self,), toIntersect, intersect_op)

    def faces_intersected_by_line(
        self,
        point: VectorLike,
        axis: VectorLike,
        tol: float = 1e-4,
        direction: Literal["AlongAxis", "Opposite"] = None,
    ):
        """Computes the intersections between the provided line and the faces of this Shape

        :point: Base point for defining a line
        :axis: Axis on which the line rest
        :tol: Intersection tolerance
        :direction: Valid values : "AlongAxis", "Opposite", if specified will ignore all faces that are not in the specified direction
        including the face where the :point: lies if it is the case

        Args:
          point: VectorLike:
          axis: VectorLike:
          tol: float:  (Default value = 1e-4)
          direction: Literal["AlongAxis":
          "Opposite"]:  (Default value = None)

        Returns:
          A list of intersected faces sorted by distance from :point:

        """

        oc_point = (
            gp_Pnt(*point.to_tuple()) if isinstance(point, Vector) else gp_Pnt(*point)
        )
        oc_axis = (
            gp_Dir(Vector(axis).wrapped)
            if not isinstance(axis, Vector)
            else gp_Dir(axis.wrapped)
        )

        line = gce_MakeLin(oc_point, oc_axis).Value()
        shape = self.wrapped

        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(shape, line, tol)

        faces_dist = []  # using a list instead of a dictionary to be able to sort it
        while intersect_maker.More():
            inter_pt = intersect_maker.Pnt()
            inter_dir_mk = gce_MakeDir(oc_point, inter_pt)

            distance = oc_point.SquareDistance(inter_pt)

            # inter_dir is not done when `oc_point` and `oc_axis` have the same coord
            if inter_dir_mk.IsDone():
                inter_dir: Any = inter_dir_mk.Value()
            else:
                inter_dir = None

            if direction == "AlongAxis":
                if (
                    inter_dir is not None
                    and not inter_dir.IsOpposite(oc_axis, tol)
                    and distance > tol
                ):
                    faces_dist.append((intersect_maker.Face(), distance))

            elif direction == "Opposite":
                if (
                    inter_dir is not None
                    and inter_dir.IsOpposite(oc_axis, tol)
                    and distance > tol
                ):
                    faces_dist.append((intersect_maker.Face(), distance))

            elif direction is None:
                faces_dist.append(
                    (intersect_maker.Face(), abs(distance))
                )  # will sort all intersected faces by distance whatever the direction is
            else:
                raise ValueError(
                    "Invalid direction specification.\nValid specification are 'AlongAxis' and 'Opposite'."
                )

            intersect_maker.Next()

        faces_dist.sort(key=lambda x: x[1])
        faces = [face[0] for face in faces_dist]

        return [Face(face) for face in faces]

    def split(self, *splitters: Shape) -> Shape:
        """Split this shape with the positional arguments.

        Args:
          *splitters: Shape:

        Returns:

        """

        split_op = BRepAlgoAPI_Splitter()

        return self._bool_op((self,), splitters, split_op)

    def distance(self, other: Shape) -> float:
        """Minimal distance between two shapes

        Args:
          other: Shape:

        Returns:

        """

        return BRepExtrema_DistShapeShape(self.wrapped, other.wrapped).Value()

    def distances(self, *others: Shape) -> Iterator[float]:
        """Minimal distances to between self and other shapes

        Args:
          *others: Shape:

        Returns:

        """

        dist_calc = BRepExtrema_DistShapeShape()
        dist_calc.LoadS1(self.wrapped)

        for s in others:
            dist_calc.LoadS2(s.wrapped)
            dist_calc.Perform()

            yield dist_calc.Value()

    def mesh(self, tolerance: float, angular_tolerance: float = 0.1):
        """Generate triangulation if none exists.

        Args:
          tolerance: float:
          angular_tolerance: float:  (Default value = 0.1)

        Returns:

        """

        if not BRepTools.Triangulation_s(self.wrapped, tolerance):
            BRepMesh_IncrementalMesh(self.wrapped, tolerance, True, angular_tolerance)

    def tessellate(
        self, tolerance: float, angular_tolerance: float = 0.1
    ) -> Tuple[list[Vector], list[Tuple[int, int, int]]]:

        self.mesh(tolerance, angular_tolerance)

        vertices: list[Vector] = []
        triangles: list[Tuple[int, int, int]] = []
        offset = 0

        for f in self.faces():

            loc = TopLoc_Location()
            poly = BRep_Tool.Triangulation_s(f.wrapped, loc)
            trsf = loc.Transformation()
            reverse = (
                True
                if f.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
                else False
            )

            # add vertices
            vertices += [
                Vector(v.x(), v.y(), v.z())
                for v in (v.Transformed(trsf) for v in poly.Nodes())
            ]

            # add triangles
            triangles += [
                (
                    t.Value(1) + offset - 1,
                    t.Value(3) + offset - 1,
                    t.Value(2) + offset - 1,
                )
                if reverse
                else (
                    t.Value(1) + offset - 1,
                    t.Value(2) + offset - 1,
                    t.Value(3) + offset - 1,
                )
                for t in poly.Triangles()
            ]

            offset += poly.NbNodes()

        return vertices, triangles

    def to_vtk_poly_data(
        self, tolerance: float, angular_tolerance: float = 0.1, normals: bool = True
    ) -> vtkPolyData:
        """Convert shape to vtkPolyData

        Args:
          tolerance: float:
          angular_tolerance: float:  (Default value = 0.1)
          normals: bool:  (Default value = True)

        Returns:

        """

        vtk_shape = IVtkOCC_Shape(self.wrapped)
        shape_data = IVtkVTK_ShapeData()
        shape_mesher = IVtkOCC_ShapeMesher(
            tolerance, angular_tolerance, theNbUIsos=0, theNbVIsos=0
        )

        shape_mesher.Build(vtk_shape, shape_data)

        return_value = shape_data.getVtkPolyData()

        # convert to triangles and split edges
        t_filter = vtkTriangleFilter()
        t_filter.SetInputData(return_value)
        t_filter.Update()

        return_value = t_filter.GetOutput()

        # compute normals
        if normals:
            n_filter = vtkPolyDataNormals()
            n_filter.SetComputePointNormals(True)
            n_filter.SetComputeCellNormals(True)
            n_filter.SetFeatureAngle(360)
            n_filter.SetInputData(return_value)
            n_filter.Update()

            return_value = n_filter.GetOutput()

        return return_value

    def _repr_javascript_(self):
        """Jupyter 3D representation support"""

        from .jupyter_tools import display

        return display(self)._repr_javascript_()

    def transformed(
        self, rotate: VectorLike = (0, 0, 0), offset: VectorLike = (0, 0, 0)
    ) -> Shape:
        """Transform Shape

        Rotate and translate the Shape by the three angles (in degrees) and offset.
        Functions exactly like the Workplane.transformed() method but for Shapes.

        Args:
          rotate(VectorLike): 3-tuple of angles to rotate, in degrees. Defaults to (0, 0, 0).
          offset(VectorLike): 3-tuple to offset. Defaults to (0, 0, 0).
          rotate: VectorLike:  (Default value = (0)
          0:
          0):
          offset: VectorLike:  (Default value = (0)

        Returns:
          Shape: transformed object

        """

        # Convert to a Vector of radians
        rotate_vector = Vector(rotate).multiply(math.pi / 180.0)
        # Compute rotation matrix.
        t_rx = gp_Trsf()
        t_rx.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), rotate_vector.X)
        t_ry = gp_Trsf()
        t_ry.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), rotate_vector.Y)
        t_rz = gp_Trsf()
        t_rz.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), rotate_vector.Z)
        t_o = gp_Trsf()
        t_o.SetTranslation(Vector(offset).wrapped)
        return self._apply_transform(t_o * t_rx * t_ry * t_rz)

    def find_intersection(
        self, point: Vector, direction: Vector
    ) -> list[tuple[Vector, Vector]]:
        """Find point and normal at intersection

        Return both the point(s) and normal(s) of the intersection of the line and the shape

        Args:
          point: point on intersecting line
          direction: direction of intersecting line
          point: Vector:
          direction: Vector:

        Returns:
          Point and normal of intersection

        """
        oc_point = gp_Pnt(*point.to_tuple())
        oc_axis = gp_Dir(*direction.to_tuple())
        oc_shape = self.wrapped

        intersection_line = gce_MakeLin(oc_point, oc_axis).Value()
        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(oc_shape, intersection_line, 0.0001)

        intersections = []
        while intersect_maker.More():
            inter_pt = intersect_maker.Pnt()
            distance = oc_point.Distance(inter_pt)
            intersections.append(
                (Face(intersect_maker.Face()), Vector(inter_pt), distance)
            )
            intersect_maker.Next()

        intersections.sort(key=lambda x: x[2])
        intersecting_faces = [i[0] for i in intersections]
        intersecting_points = [i[1] for i in intersections]
        intersecting_normals = [
            f.normal_at(intersecting_points[i]).normalized()
            for i, f in enumerate(intersecting_faces)
        ]
        result = []
        for i in range(len(intersecting_points)):
            result.append((intersecting_points[i], intersecting_normals[i]))

        return result

    def project_text(
        self,
        txt: str,
        fontsize: float,
        depth: float,
        path: Union[Wire, Edge],
        font: str = "Arial",
        font_path: str = None,
        kind: Literal["regular", "bold", "italic"] = "regular",
        valign: Literal["center", "top", "bottom"] = "center",
        start: float = 0,
    ) -> Compound:
        """Projected 3D text following the given path on Shape

        Create 3D text using projection by positioning each face of
        the planar text normal to the shape along the path and projecting
        onto the surface. If depth is not zero, the resulting face is
        thickened to the provided depth.

        Note that projection may result in text distortion depending on
        the shape at a position along the path.

        .. image:: project_text.png

        Args:
          txt: Text to be rendered
          fontsize: Size of the font in model units
          depth: Thickness of text, 0 returns a Face object
          path: Path on the Shape to follow
          font: Font name. Defaults to "Arial".
          font_path: Path to font file. Defaults to None.
          kind: Font type - one of "regular", "bold", "italic". Defaults to "regular".
          valign: Vertical Alignment - one of "center", "top", "bottom". Defaults to "center".
          start: Relative location on path to start the text. Defaults to 0.
          txt: str:
          fontsize: float:
          depth: float:
          path: Union[Wire:
          Edge]:
          font: str:  (Default value = "Arial")
          font_path: str:  (Default value = None)
          kind: Literal["regular":
          "bold":
          "italic"]:  (Default value = "regular")
          valign: Literal["center":
          "top":
          "bottom"]:  (Default value = "center")
          start: float:  (Default value = 0)

        Returns:
          : The projected text

        """

        path_length = path.length()
        shape_center = self.center()

        # Create text faces
        text_faces = Compound.make2DText(
            txt, fontsize, font, font_path, kind, "left", valign, start
        ).faces()

        logging.debug(f"projecting text sting '{txt}' as {len(text_faces)} face(s)")

        # Position each text face normal to the surface along the path and project to the surface
        projected_faces = []
        for text_face in text_faces:
            bbox = text_face.bounding_box()
            face_center_x = (bbox.xmin + bbox.xmax) / 2
            relative_position_on_wire = start + face_center_x / path_length
            path_position = path.position_at(relative_position_on_wire)
            path_tangent = path.tangent_at(relative_position_on_wire)
            (surface_point, surface_normal) = self.find_intersection(
                path_position,
                path_position - shape_center,
            )[0]
            surface_normal_plane = Plane(
                origin=surface_point, x_dir=path_tangent, normal=surface_normal
            )
            projection_face = text_face.translate(
                (-face_center_x, 0, 0)
            ).transform_shape(surface_normal_plane.rG)
            logging.debug(f"projecting face at {relative_position_on_wire=:0.2f}")
            projected_faces.append(
                projection_face.project_to_shape(self, surface_normal * -1)[0]
            )

        # Assume that the user just want faces if depth is zero
        if depth == 0:
            projected_text = projected_faces
        else:
            projected_text = [
                f.thicken(depth, f.center() - shape_center) for f in projected_faces
            ]

        logging.debug(f"finished projecting text sting '{txt}'")

        return Compound.make_compound(projected_text)

    def emboss_text(
        self,
        txt: str,
        fontsize: float,
        depth: float,
        path: Union[Wire, Edge],
        font: str = "Arial",
        font_path: str = None,
        kind: Literal["regular", "bold", "italic"] = "regular",
        valign: Literal["center", "top", "bottom"] = "center",
        start: float = 0,
        tolerance: float = 0.1,
    ) -> Compound:
        """Embossed 3D text following the given path on Shape

        Create 3D text by embossing each face of the planar text onto
        the shape along the path. If depth is not zero, the resulting
        face is thickened to the provided depth.

        .. image:: emboss_text.png

        Args:
          txt: Text to be rendered
          fontsize: Size of the font in model units
          depth: Thickness of text, 0 returns a Face object
          path: Path on the Shape to follow
          font: Font name. Defaults to "Arial".
          font_path: Path to font file. Defaults to None.
          kind: Font type - one of "regular", "bold", "italic". Defaults to "regular".
          valign: Vertical Alignment - one of "center", "top", "bottom". Defaults to "center".
          start: Relative location on path to start the text. Defaults to 0.
          txt: str:
          fontsize: float:
          depth: float:
          path: Union[Wire:
          Edge]:
          font: str:  (Default value = "Arial")
          font_path: str:  (Default value = None)
          kind: Literal["regular":
          "bold":
          "italic"]:  (Default value = "regular")
          valign: Literal["center":
          "top":
          "bottom"]:  (Default value = "center")
          start: float:  (Default value = 0)
          tolerance: float:  (Default value = 0.1)

        Returns:
          : The embossed text

        """

        path_length = path.length()
        shape_center = self.center()

        text_faces = Compound.make2DText(
            txt, fontsize, font, font_path, kind, "left", valign, start
        ).faces()

        logging.debug(f"embossing text sting '{txt}' as {len(text_faces)} face(s)")

        # Determine the distance along the path to position the face and emboss around shape
        embossed_faces = []
        for text_face in text_faces:
            bbox = text_face.bounding_box()
            face_center_x = (bbox.xmin + bbox.xmax) / 2
            relative_position_on_wire = start + face_center_x / path_length
            path_position = path.position_at(relative_position_on_wire)
            path_tangent = path.tangent_at(relative_position_on_wire)
            logging.debug(f"embossing face at {relative_position_on_wire=:0.2f}")
            embossed_faces.append(
                text_face.translate((-face_center_x, 0, 0)).emboss_to_shape(
                    self, path_position, path_tangent, tolerance=tolerance
                )
            )

        # Assume that the user just want faces if depth is zero
        if depth == 0:
            embossed_text = embossed_faces
        else:
            embossed_text = [
                f.thicken(depth, f.center() - shape_center) for f in embossed_faces
            ]

        logging.debug(f"finished embossing text sting '{txt}'")

        return Compound.make_compound(embossed_text)

    def make_finger_joint_faces(
        self: Shape,
        finger_joint_edges: list[Edge],
        material_thickness: float,
        target_finger_width: float,
        kerf_width: float = 0.0,
    ) -> list[Face]:
        """make_finger_joint_faces

        Extract faces from the given Shape (Solid or Compound) and create faces with finger
        joints cut into the given edges.

        Args:
          self(Shape): the base shape defining the finger jointed object
          finger_joint_edges(list[Edge]): the edges to convert to finger joints
          material_thickness(float): thickness of the notch from edge
          target_finger_width(float): approximate with of notch - actual finger width
        will be calculated such that there are an integer number of fingers on Edge
          kerf_width(float): Extra size to add (or subtract) to account
        for the kerf of the laser cutter. Defaults to 0.0.
          self: Shape:
          finger_joint_edges: list[Edge]:
          material_thickness: float:
          target_finger_width: float:
          kerf_width: float:  (Default value = 0.0)

        Returns:
          list[Face]: faces with finger joint cut into selected edges

        Raises:
          ValueError: provide Edge is not shared by two faces

        """
        # Store the faces for modification
        working_faces = self.faces()
        working_face_areas = [f.area() for f in working_faces]

        # Build relationship between vertices, edges and faces
        edge_adjacency = {}  # faces that share this edge (2)
        edge_vertex_adjacency = {}  # faces that share this vertex
        for common_edge in finger_joint_edges:
            adjacent_face_indices = [
                i for i, face in enumerate(working_faces) if common_edge in face.edges()
            ]
            if adjacent_face_indices:
                if len(adjacent_face_indices) != 2:
                    raise ValueError("Edge is invalid")
                edge_adjacency[common_edge] = adjacent_face_indices
            for v in common_edge.vertices():
                if v in edge_vertex_adjacency:
                    edge_vertex_adjacency[v].update(adjacent_face_indices)
                else:
                    edge_vertex_adjacency[v] = set(adjacent_face_indices)

        # External edges need tabs cut from the face while internal edges need extended tabs.
        # faces that aren't perpendicular need the tab depth to be calculated based on the
        # angle between the faces. To facilitate this, calculate the angle between faces
        # and determine if this is an internal corner.
        finger_depths = {}
        external_corners = {}
        for common_edge, adjacent_face_indices in edge_adjacency.items():
            face_centers = [working_faces[i].center() for i in adjacent_face_indices]
            face_normals = [
                working_faces[i].normal_at(working_faces[i].center())
                for i in adjacent_face_indices
            ]
            internal_edge_reference_plane = Plane(
                origin=face_centers[0], normal=face_normals[0]
            )
            localized_opposite_center = internal_edge_reference_plane.to_local_coords(
                face_centers[1]
            )
            external_corners[common_edge] = localized_opposite_center.z < 0
            corner_angle = abs(
                face_normals[0].getSignedAngle(
                    face_normals[1], common_edge.tangent_at(0)
                )
            )
            finger_depths[common_edge] = material_thickness * max(
                math.sin(corner_angle),
                (
                    math.sin(corner_angle)
                    + (math.cos(corner_angle) - 1)
                    * math.tan(math.pi / 2 - corner_angle)
                ),
            )

        # To avoid missing internal corners with open boxes, determine which vertices
        # are adjacent to the open face(s)
        vertices_with_internal_edge = {}
        for e in finger_joint_edges:
            for v in e.vertices():
                if v in vertices_with_internal_edge:
                    vertices_with_internal_edge[v] = (
                        vertices_with_internal_edge[v] or not external_corners[e]
                    )
                else:
                    vertices_with_internal_edge[v] = not external_corners[e]
        open_internal_vertices = {}
        for i, f in enumerate(working_faces):
            for v in f.vertices():
                if vertices_with_internal_edge[v]:
                    if i not in edge_vertex_adjacency[v]:
                        if v in open_internal_vertices:
                            open_internal_vertices[v].add(i)
                        else:
                            open_internal_vertices[v] = set([i])

        # Keep track of the numbers of fingers/notches in the corners
        corner_face_counter = {}

        # Make complimentary tabs in faces adjacent to common edges
        for common_edge, adjacent_face_indices in edge_adjacency.items():
            # For cosmetic reasons, try to be consistent in the notch pattern
            # by using the face area as the selection factor
            primary_face_index = adjacent_face_indices[0]
            secondary_face_index = adjacent_face_indices[1]
            if (
                working_face_areas[primary_face_index]
                > working_face_areas[secondary_face_index]
            ):
                primary_face_index, secondary_face_index = (
                    secondary_face_index,
                    primary_face_index,
                )

            for i in [primary_face_index, secondary_face_index]:
                working_faces[i] = working_faces[i].make_finger_joints(
                    common_edge,
                    finger_depths[common_edge],
                    target_finger_width,
                    corner_face_counter,
                    open_internal_vertices,
                    align_to_bottom=i == primary_face_index,
                    external_corner=external_corners[common_edge],
                    face_index=i,
                )

        # Determine which faces have tabs
        tabbed_face_indices = set(
            i for face_list in edge_adjacency.values() for i in face_list
        )
        tabbed_faces = [working_faces[i] for i in tabbed_face_indices]

        # If kerf compensation is requested, increase the outer and decrease inner sizes
        if kerf_width != 0.0:
            tabbed_faces = [
                Face.make_from_wires(
                    f.outer_wire().offset_2d(kerf_width / 2)[0],
                    [i.offset_2d(-kerf_width / 2)[0] for i in f.inner_wires()],
                )
                for f in tabbed_faces
            ]

        return tabbed_faces

    def max_fillet(
        self: Shape,
        edge_list: Iterable[Edge],
        tolerance=0.1,
        max_iterations: int = 10,
    ) -> float:
        """Find Maximum Fillet Size

        Find the largest fillet radius for the given Shape and edges with a
        recursive binary search.

        Args:
          edge_list(Iterable[Edge]): a list of Edge objects, which must belong to this solid
          tolerance(float, optional): maximum error from actual value. Defaults to 0.1.
          max_iterations(int): maximum number of recursive iterations. Defaults to 10.
          self: Shape:
          edge_list: Iterable[Edge]:
          max_iterations: int:  (Default value = 10)

        Returns:
          float: maximum fillet radius
          As an example:
          float: maximum fillet radius
          As an example:
          max_fillet_radius = my_shape.max_fillet(shape_edges)
          or:
          float: maximum fillet radius
          As an example:
          max_fillet_radius = my_shape.max_fillet(shape_edges)
          or:
          max_fillet_radius = my_shape.max_fillet(shape_edges, tolerance=0.5, max_iterations=8)

        Raises:
          RuntimeError: failed to find the max value
          ValueError: the provided Shape is invalid

        """

        def __max_fillet(window_min: float, window_max: float, current_iteration: int):
            window_mid = (window_min + window_max) / 2

            if current_iteration == max_iterations:
                raise RuntimeError(
                    f"Failed to find the max value within {tolerance} in {max_iterations}"
                )

            # Do these numbers work? - if not try with the smaller window
            try:
                if not self.fillet(window_mid, edge_list).is_valid():
                    raise StdFail_NotDone
            except StdFail_NotDone:
                return __max_fillet(window_min, window_mid, current_iteration + 1)

            # These numbers work, are they close enough? - if not try larger window
            if window_mid - window_min <= tolerance:
                return window_mid
            else:
                return __max_fillet(window_mid, window_max, current_iteration + 1)

        if not self.is_valid():
            raise ValueError("Invalid Shape")
        max_radius = __max_fillet(0.0, 2 * self.bounding_box().DiagonalLength, 0)

        return max_radius


class ShapeList(list):
    """Subclass of list with custom filter and sort methods appropriate to CAD"""

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()

    def filter_by_axis(self, axis: Axis, tolerance=1e-5):
        """filter by axis

        Filter objects of type planar Face or linear Edge by their normal or tangent
        (respectively) and sort the results by the given axis.

        Args:
            axis (Axis): axis to filter and sort by
            tolerance (_type_, optional): maximum deviation from axis. Defaults to 1e-5.

        Returns:
            ShapeList: sublist of Faces or Edges
        """

        planar_faces = filter(
            lambda o: isinstance(o, Face) and o.geom_type() == "PLANE", self
        )
        linear_edges = filter(
            lambda o: isinstance(o, Edge) and o.geom_type() == "LINE", self
        )

        result = list(
            filter(
                lambda o: axis.is_parallel(
                    Axis(o.center(), o.normal_at(None)), tolerance
                ),
                planar_faces,
            )
        )
        result.extend(
            list(
                filter(
                    lambda o: axis.is_parallel(
                        Axis(o.position_at(0), o.tangent_at(0)), tolerance
                    ),
                    linear_edges,
                )
            )
        )

        return ShapeList(result).sort_by(axis)

    def filter_by_position(
        self,
        axis: Axis,
        minimum: float,
        maximum: float,
        inclusive: tuple[bool, bool] = (True, True),
    ):
        """filter by position

        Filter and sort objects by the position of their centers along given axis.
        min and max values can be inclusive or exclusive depending on the inclusive tuple.

        Args:
            axis (Axis): axis to sort by
            minimum (float): minimum value
            maximum (float): maximum value
            inclusive (tuple[bool, bool], optional): include min,max values.
                Defaults to (True, True).

        Returns:
            ShapeList: filtered object list
        """
        if inclusive == (True, True):
            objects = filter(
                lambda o: minimum
                <= axis.to_plane().to_local_coords(o).center().Z
                <= maximum,
                self,
            )
        elif inclusive == (True, False):
            objects = filter(
                lambda o: minimum
                <= axis.to_plane().to_local_coords(o).center().Z
                < maximum,
                self,
            )
        elif inclusive == (False, True):
            objects = filter(
                lambda o: minimum
                < axis.to_plane().to_local_coords(o).center().Z
                <= maximum,
                self,
            )
        elif inclusive == (False, False):
            objects = filter(
                lambda o: minimum
                < axis.to_plane().to_local_coords(o).center().Z
                < maximum,
                self,
            )

        return ShapeList(objects).sort_by(axis)

    def filter_by_type(
        self,
        geom_type: GeomType,
    ):
        """filter by type

        Filter the objects by the provided type. Note that not all types apply to all
        objects.

        Args:
            type (Type): type to sort by

        Returns:
            ShapeList: filtered list of objects
        """
        result = filter(lambda o: o.geom_type() == geom_type.name, self)
        return ShapeList(result)

    def sort_by(self, sort_by: Union[Axis, SortBy] = Axis.Z, reverse: bool = False):
        """sort by

        Sort objects by provided criteria. Note that not all sort_by criteria apply to all
        objects.

        Args:
            sort_by (SortBy, optional): sort criteria. Defaults to SortBy.Z.
            reverse (bool, optional): flip order of sort. Defaults to False.

        Returns:
            ShapeList: sorted list of objects
        """
        if isinstance(sort_by, Axis):
            objects = sorted(
                self,
                key=lambda o: sort_by.to_plane().to_local_coords(o).center().Z,
                reverse=reverse,
            )

        elif isinstance(sort_by, SortBy):
            if sort_by == SortBy.LENGTH:
                objects = sorted(
                    self,
                    key=lambda obj: obj.length(),
                    reverse=reverse,
                )
            elif sort_by == SortBy.RADIUS:
                objects = sorted(
                    self,
                    key=lambda obj: obj.radius(),
                    reverse=reverse,
                )
            elif sort_by == SortBy.DISTANCE:
                objects = sorted(
                    self,
                    key=lambda obj: obj.center().length,
                    reverse=reverse,
                )
            elif sort_by == SortBy.AREA:
                objects = sorted(
                    self,
                    key=lambda obj: obj.area(),
                    reverse=reverse,
                )
            elif sort_by == SortBy.VOLUME:
                objects = sorted(
                    self,
                    key=lambda obj: obj.volume(),
                    reverse=reverse,
                )
        else:
            raise ValueError(f"Sort by {type(sort_by)} unsupported")

        return ShapeList(objects)

    def __gt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort operator"""
        return self.sort_by(sort_by)

    def __lt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Reverse sort operator"""
        return self.sort_by(sort_by, reverse=True)

    def __rshift__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort and select largest element operator"""
        return self.sort_by(sort_by)[-1]

    def __lshift__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort and select smallest element operator"""
        return self.sort_by(sort_by)[0]

    def __or__(self, axis: Axis = Axis.Z):
        """Filter by axis operator"""
        return self.filter_by_axis(axis)

    def __mod__(self, geom_type: GeomType):
        """Filter by geometry type operator"""
        return self.filter_by_type(geom_type)

    def __getitem__(self, key):
        """Return slices of ShapeList as ShapeList"""
        if isinstance(key, slice):
            return ShapeList(list(self).__getitem__(key))
        else:
            return list(self).__getitem__(key)


class Plane:
    """A 2D coordinate system in space

    A 2D coordinate system in space, with the x-y axes on the plane, and a
    particular point as the origin.

    A plane allows the use of 2D coordinates, which are later converted to
    global, 3d coordinates when the operations are complete.

    Frequently, it is not necessary to create work planes, as they can be
    created automatically from faces.

    Args:

    Returns:

    """

    x_dir: Vector
    y_dir: Vector
    z_dir: Vector
    _origin: Vector

    lcs: gp_Ax3
    r_g: Matrix
    f_g: Matrix

    # equality tolerances
    _eq_tolerance_origin = 1e-6
    _eq_tolerance_dot = 1e-6

    @classmethod
    def named(cls: Type[Plane], std_name: str, origin=(0, 0, 0)) -> Plane:
        """Create a predefined Plane based on the conventional names.

                Args:
                  std_name(string): one of (xy|yz|zx|xz|yx|zy|front|back|left|right|top|bottom)
                  origin(3-tuple of the origin of the new plane, in global coordinates.

        Available named planes are as follows. Direction references refer to
        the global directions.

        =========== ======= ======= ======
        Name        x_dir    y_dir    z_dir
        =========== ======= ======= ======
        xy          +x      +y      +z
        yz          +y      +z      +x
        zx          +z      +x      +y
        xz          +x      +z      -y
        yx          +y      +x      -z
        zy          +z      +y      -x
        front       +x      +y      +z
        back        -x      +y      -z
        left        +z      +y      -x
        right       -z      +y      +x
        top         +x      -z      +y
        bottom      +x      +z      -y
        =========== ======= ======= ======, optional): the desired origin, specified in global coordinates (Default value = (0)
                  cls: Type[Plane]:
                  std_name: str:
                  0:
                  0):

                Returns:

        """

        named_planes = {
            # origin, x_dir, normal
            "XY": Plane(origin, (1, 0, 0), (0, 0, 1)),
            "YZ": Plane(origin, (0, 1, 0), (1, 0, 0)),
            "ZX": Plane(origin, (0, 0, 1), (0, 1, 0)),
            "XZ": Plane(origin, (1, 0, 0), (0, -1, 0)),
            "YX": Plane(origin, (0, 1, 0), (0, 0, -1)),
            "ZY": Plane(origin, (0, 0, 1), (-1, 0, 0)),
            "front": Plane(origin, (1, 0, 0), (0, 0, 1)),
            "back": Plane(origin, (-1, 0, 0), (0, 0, -1)),
            "left": Plane(origin, (0, 0, 1), (-1, 0, 0)),
            "right": Plane(origin, (0, 0, -1), (1, 0, 0)),
            "top": Plane(origin, (1, 0, 0), (0, 1, 0)),
            "bottom": Plane(origin, (1, 0, 0), (0, -1, 0)),
        }

        try:
            return named_planes[std_name]
        except KeyError:
            raise ValueError("Supported names are {}".format(list(named_planes.keys())))

    @classmethod
    def XY(cls, origin=(0, 0, 0), x_dir=Vector(1, 0, 0)):
        plane = Plane.named("XY", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def YZ(cls, origin=(0, 0, 0), x_dir=Vector(0, 1, 0)):
        plane = Plane.named("YZ", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def ZX(cls, origin=(0, 0, 0), x_dir=Vector(0, 0, 1)):
        plane = Plane.named("ZX", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def XZ(cls, origin=(0, 0, 0), x_dir=Vector(1, 0, 0)):
        plane = Plane.named("XZ", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def YX(cls, origin=(0, 0, 0), x_dir=Vector(0, 1, 0)):
        plane = Plane.named("YX", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def ZY(cls, origin=(0, 0, 0), x_dir=Vector(0, 0, 1)):
        plane = Plane.named("ZY", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def front(cls, origin=(0, 0, 0), x_dir=Vector(1, 0, 0)):
        plane = Plane.named("front", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def back(cls, origin=(0, 0, 0), x_dir=Vector(-1, 0, 0)):
        plane = Plane.named("back", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def left(cls, origin=(0, 0, 0), x_dir=Vector(0, 0, 1)):
        plane = Plane.named("left", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def right(cls, origin=(0, 0, 0), x_dir=Vector(0, 0, -1)):
        plane = Plane.named("right", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def top(cls, origin=(0, 0, 0), x_dir=Vector(1, 0, 0)):
        plane = Plane.named("top", origin)
        plane._set_plane_dir(x_dir)
        return plane

    @classmethod
    def bottom(cls, origin=(0, 0, 0), x_dir=Vector(1, 0, 0)):
        plane = Plane.named("bottom", origin)
        plane._set_plane_dir(x_dir)
        return plane

    def __init__(
        self,
        origin: Union[tuple[float, float, float], Vector],
        x_dir: Union[tuple[float, float, float], Vector] = None,
        normal: Union[tuple[float, float, float], Vector] = (0, 0, 1),
    ):
        """
        Create a Plane with an arbitrary orientation

        :param origin: the origin in global coordinates
        :param x_dir: an optional vector representing the xDirection.
        :param normal: the normal direction for the plane
        :raises ValueError: if the specified x_dir is not orthogonal to the provided normal
        """
        z_dir = Vector(normal)
        if z_dir.length == 0.0:
            raise ValueError("normal should be non null")

        self.z_dir = z_dir.normalized()

        if x_dir is None:
            ax3 = gp_Ax3(Vector(origin).to_pnt(), Vector(normal).to_dir())
            x_dir = Vector(ax3.XDirection())
        else:
            x_dir = Vector(x_dir)
            if x_dir.length == 0.0:
                raise ValueError("x_dir should be non null")
        self._set_plane_dir(x_dir)
        self.origin = Vector(origin)

    def __repr__(self):
        origin_str = ",".join((f"{v:.2f}" for v in self.origin.to_tuple()))
        x_dir_str = ",".join((f"{v:.2f}" for v in self.x_dir.to_tuple()))
        z_dir_str = ",".join((f"{v:.2f}" for v in self.z_dir.to_tuple()))
        return f"Plane(o=({origin_str}), x=({x_dir_str}), z=({z_dir_str})"

    def _eq_iter(self, other):
        """Iterator to successively test equality

        Args:
          other:

        Returns:

        """
        cls = type(self)
        yield isinstance(other, Plane)  # comparison is with another Plane
        # origins are the same
        yield abs(self.origin - other.origin) < cls._eq_tolerance_origin
        # z-axis vectors are parallel (assumption: both are unit vectors)
        yield abs(self.z_dir.dot(other.z_dir) - 1) < cls._eq_tolerance_dot
        # x-axis vectors are parallel (assumption: both are unit vectors)
        yield abs(self.x_dir.dot(other.x_dir) - 1) < cls._eq_tolerance_dot

    def __eq__(self, other):
        return all(self._eq_iter(other))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self: Plane):
        """To String

        Convert Plane to String for display

        Returns:
            Plane as String
        """
        origin_str = ",".join((f"{v:.2f}" for v in self.origin.to_tuple()))
        x_dir_str = ",".join((f"{v:.2f}" for v in self.x_dir.to_tuple()))
        z_dir_str = ",".join((f"{v:.2f}" for v in self.z_dir.to_tuple()))
        return f"Plane(o=({origin_str}), x=({x_dir_str}), z=({z_dir_str})"

    @property
    def origin(self) -> Vector:
        return self._origin

    @origin.setter
    def origin(self, value):
        self._origin = Vector(value)
        self._calc_transforms()

    def set_origin2d(self, x, y):
        """Set a new origin in the plane itself

        Set a new origin in the plane itself. The plane's orientation and
        xDrection are unaffected.

        Args:
          float: x: offset in the x direction
          float: y: offset in the y direction
          x:
          y:

        Returns:
          void

          The new coordinates are specified in terms of the current 2D system.
          As an example:

          p = Plane.xy()
          p.set_origin2d(2, 2)
          p.set_origin2d(2, 2)

          results in a plane with its origin at (x, y) = (4, 4) in global
          coordinates. Both operations were relative to local coordinates of the
          plane.

        """
        self.origin = self.to_world_coords((x, y))

    def to_local_coords(self, obj: Union[VectorLike, Shape, BoundBox]):
        """Reposition the object relative to this plane

        Args:
          obj: an object, vector, or bounding box to convert
          obj: Union[VectorLike:
          Shape:
          BoundBox]:

        Returns:
          : an object of the same type, but repositioned to local coordinates

        """
        return self._to_from_local_coords(obj, True)

    def to_world_coords(self, tuple_point) -> Vector:
        """Convert a point in local coordinates to global coordinates

        Args:
          tuple_point(a 2 or three tuple of float. The third value is taken to be zero if not supplied.): point in local coordinates to convert.

        Returns:
          a Vector in global coordinates

        """
        if isinstance(tuple_point, Vector):
            v = tuple_point
        elif len(tuple_point) == 2:
            v = Vector(tuple_point[0], tuple_point[1], 0)
        else:
            v = Vector(tuple_point)
        return v.transform(self.r_g)

    def rotated(self, rotate=(0, 0, 0)):
        """Returns a copy of this plane, rotated about the specified axes

        Since the z axis is always normal the plane, rotating around Z will
        always produce a plane that is parallel to this one.

        The origin of the workplane is unaffected by the rotation.

        Rotations are done in order x, y, z. If you need a different order,
        manually chain together multiple rotate() commands.

        Args:
          rotate: Vector [xDegrees, yDegrees, zDegrees] (Default value = (0)
          0:
          0):

        Returns:
          a copy of this plane rotated as requested.

        """
        # NB: this is not a geometric Vector
        rotate = Vector(rotate)
        # Convert to radians.
        rotate = rotate.multiply(math.pi / 180.0)

        # Compute rotation matrix.
        t1 = gp_Trsf()
        t1.SetRotation(
            gp_Ax1(gp_Pnt(*(0, 0, 0)), gp_Dir(*self.x_dir.to_tuple())), rotate.X
        )
        t2 = gp_Trsf()
        t2.SetRotation(
            gp_Ax1(gp_Pnt(*(0, 0, 0)), gp_Dir(*self.y_dir.to_tuple())), rotate.Y
        )
        t3 = gp_Trsf()
        t3.SetRotation(
            gp_Ax1(gp_Pnt(*(0, 0, 0)), gp_Dir(*self.z_dir.to_tuple())), rotate.Z
        )
        t = Matrix(gp_GTrsf(t1 * t2 * t3))

        # Compute the new plane.
        new_xdir = self.x_dir.transform(t)
        new_z_dir = self.z_dir.transform(t)

        return Plane(self.origin, new_xdir, new_z_dir)

    def mirror_in_plane(self, list_of_shapes, axis="X"):

        local_coord_system = gp_Ax3(
            self.origin.to_pnt(), self.z_dir.to_dir(), self.x_dir.to_dir()
        )
        t = gp_Trsf()

        if axis == "X":
            t.SetMirror(gp_Ax1(self.origin.to_pnt(), local_coord_system.XDirection()))
        elif axis == "Y":
            t.SetMirror(gp_Ax1(self.origin.to_pnt(), local_coord_system.YDirection()))
        else:
            raise NotImplementedError

        result_wires = []
        for w in list_of_shapes:
            mirrored = w.transformShape(Matrix(t))

            # attempt stitching of the wires
            result_wires.append(mirrored)

        return result_wires

    def _set_plane_dir(self, x_dir):
        """Set the vectors parallel to the plane, i.e. x_dir and y_dir

        Args:
          x_dir:

        Returns:

        """
        x_dir = Vector(x_dir)
        self.x_dir = x_dir.normalized()
        self.y_dir = self.z_dir.cross(self.x_dir).normalized()

    def _calc_transforms(self):
        """Computes transformation matrices to convert between coordinates

        Computes transformation matrices to convert between local and global
        coordinates.

        Args:

        Returns:

        """
        # r is the forward transformation matrix from world to local coordinates
        # ok i will be really honest, i cannot understand exactly why this works
        # something bout the order of the translation and the rotation.
        # the double-inverting is strange, and I don't understand it.
        forward = Matrix()
        inverse = Matrix()

        forward_t = gp_Trsf()
        inverse_t = gp_Trsf()

        global_coord_system = gp_Ax3()
        local_coord_system = gp_Ax3(
            gp_Pnt(*self.origin.to_tuple()),
            gp_Dir(*self.z_dir.to_tuple()),
            gp_Dir(*self.x_dir.to_tuple()),
        )

        forward_t.SetTransformation(global_coord_system, local_coord_system)
        forward.wrapped = gp_GTrsf(forward_t)

        inverse_t.SetTransformation(local_coord_system, global_coord_system)
        inverse.wrapped = gp_GTrsf(inverse_t)

        self.lcs = local_coord_system
        self.r_g = inverse
        self.f_g = forward

    @property
    def location(self) -> Location:

        return Location(self)

    def to_pln(self) -> gp_Pln:

        return gp_Pln(
            gp_Ax3(self.origin.to_pnt(), self.z_dir.to_dir(), self.x_dir.to_dir())
        )

    def _to_from_local_coords(
        self, obj: Union[VectorLike, Shape, BoundBox], to: bool = True
    ):
        """Reposition the object relative to this plane

        Args:
          obj: an object, vector, or bounding box to convert
          to: convert `to` or from local coordinates. Defaults to True.
          obj: Union[VectorLike:
          Shape:
          BoundBox]:
          to: bool:  (Default value = True)

        Returns:
          : an object of the same type, but repositioned to local coordinates

        """
        # from .shapes import Shape

        transform_matrix = self.f_g if to else self.r_g

        if isinstance(obj, (tuple, Vector)):
            return Vector(obj).transform(transform_matrix)
        elif isinstance(obj, Shape):
            return obj.transform_shape(transform_matrix)
        elif isinstance(obj, BoundBox):
            global_bottom_left = Vector(obj.xmin, obj.ymin, obj.zmin)
            global_top_right = Vector(obj.xmax, obj.ymax, obj.zmax)
            local_bottom_left = global_bottom_left.transform(transform_matrix)
            local_top_right = global_top_right.transform(transform_matrix)
            local_bbox = Bnd_Box(
                gp_Pnt(*local_bottom_left.to_tuple()),
                gp_Pnt(*local_top_right.to_tuple()),
            )
            return BoundBox(local_bbox)
        else:
            raise ValueError(
                f"Unable to repositioned type {type(obj)} with respect to local coordinates"
            )

    def from_local_coords(self, obj: Union[tuple, Vector, Shape, BoundBox]):
        """Reposition the object relative from this plane

        Args:
          obj: an object, vector, or bounding box to convert
          obj: Union[tuple:
          Vector:
          Shape:
          BoundBox]:

        Returns:
          : an object of the same type, but repositioned to world coordinates

        """
        return self._to_from_local_coords(obj, False)


#:TypeVar("PlaneLike"): Named Plane (e.g. "XY") or Plane
PlaneLike = Union[str, Plane]


class Compound(Shape, Mixin3D):
    """a collection of disconnected solids"""

    @staticmethod
    def _make_compound(list_of_shapes: Iterable[TopoDS_Shape]) -> TopoDS_Compound:

        comp = TopoDS_Compound()
        comp_builder = TopoDS_Builder()
        comp_builder.MakeCompound(comp)

        for s in list_of_shapes:
            comp_builder.Add(comp, s)

        return comp

    def remove(self, shape: Shape):
        """Remove the specified shape.

        Args:
          shape: Shape:

        Returns:

        """

        comp_builder = TopoDS_Builder()
        comp_builder.Remove(self.wrapped, shape.wrapped)

    @classmethod
    def make_compound(cls, list_of_shapes: Iterable[Shape]) -> Compound:
        """Create a compound out of a list of shapes

        Args:
          list_of_shapes: Iterable[Shape]:

        Returns:

        """

        return cls(cls._make_compound((s.wrapped for s in list_of_shapes)))

    @classmethod
    def make_text(
        cls,
        text: str,
        size: float,
        height: float,
        font: str = "Arial",
        font_path: str = None,
        kind: Literal["regular", "bold", "italic"] = "regular",
        halign: Literal["center", "left", "right"] = "center",
        valign: Literal["center", "top", "bottom"] = "center",
        position: Plane = Plane.XY(),
    ) -> Shape:
        """Create a 3D text

        Args:
          text: str:
          size: float:
          height: float:
          font: str:  (Default value = "Arial")
          font_path: str:  (Default value = None)
          kind: Literal["regular":
          "bold":
          "italic"]:  (Default value = "regular")
          halign: Literal["center":
          "left":
          "right"]:  (Default value = "center")
          valign: Literal["center":
          "top":
          "bottom"]:  (Default value = "center")
          position: Plane:  (Default value = Plane.XY())

        Returns:

        """

        font_kind = {
            "regular": Font_FA_Regular,
            "bold": Font_FA_Bold,
            "italic": Font_FA_Italic,
        }[kind]

        mgr = Font_FontMgr.GetInstance_s()

        if font_path and mgr.CheckFont(TCollection_AsciiString(font_path).ToCString()):
            font_t = Font_SystemFont(TCollection_AsciiString(font_path))
            font_t.SetFontPath(font_kind, TCollection_AsciiString(font_path))
            mgr.RegisterFont(font_t, True)

        else:
            font_t = mgr.FindFont(TCollection_AsciiString(font), font_kind)

        builder = Font_BRepTextBuilder()
        font_i = StdPrs_BRepFont(
            NCollection_Utf8String(font_t.FontName().ToCString()),
            font_kind,
            float(size),
        )
        text_flat = Shape(builder.Perform(font_i, NCollection_Utf8String(text)))

        bb = text_flat.bounding_box()

        t = Vector()

        if halign == "center":
            t.X = -bb.xlen / 2
        elif halign == "right":
            t.X = -bb.xlen

        if valign == "center":
            t.Y = -bb.ylen / 2
        elif valign == "top":
            t.Y = -bb.ylen

        text_flat = text_flat.translate(t)

        if height != 0:
            vec_normal = text_flat.faces()[0].normal_at() * height

            text_3d = BRepPrimAPI_MakePrism(text_flat.wrapped, vec_normal.wrapped)
            return_value = cls(text_3d.Shape()).transform_shape(position.rG)
        else:
            return_value = text_flat.transform_shape(position.rG)

        return return_value

    @classmethod
    def make_2d_text(
        cls,
        txt: str,
        fontsize: float,
        font: str = "Arial",
        font_path: Optional[str] = None,
        font_style: Literal["regular", "bold", "italic"] = "regular",
        halign: Literal["center", "left", "right"] = "left",
        valign: Literal["center", "top", "bottom"] = "center",
        position_on_path: float = 0.0,
        text_path: Union["Edge", "Wire"] = None,
    ) -> "Compound":
        """
        2D Text that optionally follows a path.

        The text that is created can be combined as with other sketch features by specifying
        a mode or rotated by the given angle.  In addition, edges have been previously created
        with arc or segment, the text will follow the path defined by these edges. The start
        parameter can be used to shift the text along the path to achieve precise positioning.

        Args:
            txt: text to be rendered
            fontsize: size of the font in model units
            font: font name
            fontPath: path to font file
            fontStyle: one of ["regular", "bold", "italic"]. Defaults to "regular".
            halign: horizontal alignment, one of ["center", "left", "right"].
                Defaults to "left".
            valign: vertical alignment, one of ["center", "top", "bottom"].
                Defaults to "center".
            positionOnPath: the relative location on path to position the text, between 0.0 and 1.0.
                Defaults to 0.0.
            textPath: a path for the text to follows. Defaults to None - linear text.

        Returns:
            a Compound object containing multiple Faces representing the text

        Examples::

            fox = cq.Compound.make2DText(
                txt="The quick brown fox jumped over the lazy dog",
                fontsize=10,
                positionOnPath=0.1,
                textPath=jump_edge,
            )

        """

        def position_face(orig_face: "Face") -> "Face":
            """
            Reposition a face to the provided path

            Local coordinates are used to calculate the position of the face
            relative to the path. Global coordinates to position the face.
            """
            bbox = orig_face.bounding_box()
            face_bottom_center = Vector((bbox.xmin + bbox.xmax) / 2, 0, 0)
            relative_position_on_wire = (
                position_on_path + face_bottom_center.X / path_length
            )
            wire_tangent = text_path.tangent_at(relative_position_on_wire)
            wire_angle = -180 * Vector(1, 0, 0).get_signed_angle(wire_tangent) / math.pi
            wire_position = text_path.position_at(relative_position_on_wire)

            return orig_face.translate(wire_position - face_bottom_center).rotate(
                wire_position,
                wire_position + Vector(0, 0, 1),
                wire_angle,
            )

        font_kind = {
            "regular": Font_FA_Regular,
            "bold": Font_FA_Bold,
            "italic": Font_FA_Italic,
        }[font_style]

        mgr = Font_FontMgr.GetInstance_s()

        if font_path and mgr.CheckFont(TCollection_AsciiString(font_path).ToCString()):
            font_t = Font_SystemFont(TCollection_AsciiString(font_path))
            font_t.SetFontPath(font_kind, TCollection_AsciiString(font_path))
            mgr.RegisterFont(font_t, True)

        else:
            font_t = mgr.FindFont(TCollection_AsciiString(font), font_kind)

        builder = Font_BRepTextBuilder()
        font_i = StdPrs_BRepFont(
            NCollection_Utf8String(font_t.FontName().ToCString()),
            font_kind,
            float(fontsize),
        )
        text_flat = Compound(builder.Perform(font_i, NCollection_Utf8String(txt)))

        bb = text_flat.bounding_box()

        t = Vector()

        if halign == "center":
            t.X = -bb.xlen / 2
        elif halign == "right":
            t.X = -bb.xlen

        if valign == "center":
            t.Y = -bb.ylen / 2
        elif valign == "top":
            t.Y = -bb.ylen

        text_flat = text_flat.translate(t)

        if text_path is not None:
            path_length = text_path.length()
            text_flat = Compound.make_compound(
                [position_face(f) for f in text_flat.faces()]
            )

        return text_flat

    def __iter__(self) -> Iterator[Shape]:
        """
        Iterate over subshapes.

        """

        it = TopoDS_Iterator(self.wrapped)

        while it.More():
            yield Shape.cast(it.Value())
            it.Next()

    def __bool__(self) -> bool:
        """
        Check if empty.
        """

        return TopoDS_Iterator(self.wrapped).More()

    def cut(self, *toCut: Shape) -> Compound:
        """Remove a shape from another one

        Args:
          *toCut: Shape:

        Returns:

        """

        cut_op = BRepAlgoAPI_Cut()

        return tcast(Compound, self._bool_op(self, toCut, cut_op))

    def fuse(self, *toFuse: Shape, glue: bool = False, tol: float = None) -> Compound:
        """Fuse shapes together

        Args:
          *toFuse: Shape:
          glue: bool:  (Default value = False)
          tol: float:  (Default value = None)

        Returns:

        """

        fuse_op = BRepAlgoAPI_Fuse()
        if glue:
            fuse_op.SetGlue(BOPAlgo_GlueEnum.BOPAlgo_GlueShift)
        if tol:
            fuse_op.SetFuzzyValue(tol)

        args = tuple(self) + toFuse

        if len(args) <= 1:
            return_value: Shape = args[0]
        else:
            return_value = self._bool_op(args[:1], args[1:], fuse_op)

        # fuse_op.RefineEdges()
        # fuse_op.FuseEdges()

        return tcast(Compound, return_value)

    def intersect(self, *toIntersect: Shape) -> Compound:
        """Construct shape intersection

        Args:
          *toIntersect: Shape:

        Returns:

        """

        intersect_op = BRepAlgoAPI_Common()

        return tcast(Compound, self._bool_op(self, toIntersect, intersect_op))

    def get_type(
        self: Compound, obj_type: Union[Edge, Wire, Face, Solid]
    ) -> list[Union[Edge, Wire, Face, Solid]]:
        """get_type

        Extract the objects of the given type from a Compound. Note that this
        isn't the same as Faces() etc. which will extract Faces from Solids.

        Args:
            obj_type (Union[Edge, Face, Solid]): Object types to extract

        Returns:
            list[Union[Edge, Face, Solid]]: Extracted objects
        """
        iterator = TopoDS_Iterator()
        iterator.Initialize(self.wrapped)

        type_map = {
            Edge: TopAbs_ShapeEnum.TopAbs_EDGE,
            Wire: TopAbs_ShapeEnum.TopAbs_WIRE,
            Face: TopAbs_ShapeEnum.TopAbs_FACE,
            Solid: TopAbs_ShapeEnum.TopAbs_SOLID,
        }
        results = []
        while iterator.More():
            child = iterator.Value()
            if child.ShapeType() == type_map[obj_type]:
                results.append(obj_type(child))
            iterator.Next()

        return results


class Edge(Shape, Mixin1D):
    """A trimmed curve that represents the border of a face"""

    def _geom_adaptor(self) -> BRepAdaptor_Curve:
        """ """

        return BRepAdaptor_Curve(self.wrapped)

    def _geom_adaptor_h(self) -> Tuple[BRepAdaptor_Curve, BRepAdaptor_Curve]:
        """ """

        curve = self._geom_adaptor()

        return curve, BRepAdaptor_Curve(curve)

    def close(self) -> Union[Edge, Wire]:
        """Close an Edge"""
        return_value: Union[Wire, Edge]

        if not self.is_closed():
            return_value = Wire.assemble_edges((self,)).close()
        else:
            return_value = self

        return return_value

    def arc_center(self) -> Vector:
        """center of an underlying circle or ellipse geometry."""

        g = self.geom_type()
        a = self._geom_adaptor()

        if g == "CIRCLE":
            return_value = Vector(a.Circle().Position().Location())
        elif g == "ELLIPSE":
            return_value = Vector(a.Ellipse().Position().Location())
        else:
            raise ValueError(f"{g} has no arc center")

        return return_value

    @classmethod
    def make_circle(
        cls,
        radius: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
        angle1: float = 360.0,
        angle2: float = 360,
        orientation=True,
    ) -> Edge:
        pnt = Vector(pnt)
        dir = Vector(dir)

        circle_gp = gp_Circ(gp_Ax2(pnt.to_pnt(), dir.to_dir()), radius)

        if angle1 == angle2:  # full circle case
            return cls(BRepBuilderAPI_MakeEdge(circle_gp).Edge())
        else:  # arc case
            circle_geom = GC_MakeArcOfCircle(
                circle_gp, angle1 * DEG2RAD, angle2 * DEG2RAD, orientation
            ).Value()
            return cls(BRepBuilderAPI_MakeEdge(circle_geom).Edge())

    @classmethod
    def make_ellipse(
        cls,
        x_radius: float,
        y_radius: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
        xdir: VectorLike = Vector(1, 0, 0),
        angle1: float = 360.0,
        angle2: float = 360.0,
        sense: Literal[-1, 1] = 1,
    ) -> Edge:
        """Makes an Ellipse centered at the provided point, having normal in the provided direction.

        Args:
          cls: param x_radius: x radius of the ellipse (along the x-axis of plane the ellipse should lie in)
          y_radius: y radius of the ellipse (along the y-axis of plane the ellipse should lie in)
          pnt: vector representing the center of the ellipse
          dir: vector representing the direction of the plane the ellipse should lie in
          angle1: start angle of arc
          angle2: end angle of arc (angle2 == angle1 return closed ellipse = default)
          sense: clockwise (-1) or counter clockwise (1)
          x_radius: float:
          y_radius: float:
          pnt: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):
          xdir: VectorLike:  (Default value = Vector(1)
          angle1: float:  (Default value = 360.0)
          angle2: float:  (Default value = 360.0)
          sense: Literal[-1:
          1]:  (Default value = 1)

        Returns:
          an Edge

        """

        pnt_p = Vector(pnt).to_pnt()
        dir_d = Vector(dir).to_dir()
        xdir_d = Vector(xdir).to_dir()

        ax1 = gp_Ax1(pnt_p, dir_d)
        ax2 = gp_Ax2(pnt_p, dir_d, xdir_d)

        if y_radius > x_radius:
            # swap x and y radius and rotate by 90° afterwards to create an ellipse with x_radius < y_radius
            correction_angle = 90.0 * DEG2RAD
            ellipse_gp = gp_Elips(ax2, y_radius, x_radius).Rotated(
                ax1, correction_angle
            )
        else:
            correction_angle = 0.0
            ellipse_gp = gp_Elips(ax2, x_radius, y_radius)

        if angle1 == angle2:  # full ellipse case
            ellipse = cls(BRepBuilderAPI_MakeEdge(ellipse_gp).Edge())
        else:  # arc case
            # take correction_angle into account
            ellipse_geom = GC_MakeArcOfEllipse(
                ellipse_gp,
                angle1 * DEG2RAD - correction_angle,
                angle2 * DEG2RAD - correction_angle,
                sense == 1,
            ).Value()
            ellipse = cls(BRepBuilderAPI_MakeEdge(ellipse_geom).Edge())

        return ellipse

    @classmethod
    def make_spline(
        cls,
        list_of_vector: list[Vector],
        tangents: Sequence[Vector] = None,
        periodic: bool = False,
        parameters: Sequence[float] = None,
        scale: bool = True,
        tol: float = 1e-6,
    ) -> Edge:
        """Interpolate a spline through the provided points.

        Args:
          list_of_vector: a list of Vectors that represent the points
          tangents: tuple of Vectors specifying start and finish tangent
          periodic: creation of periodic curves
          parameters: the value of the parameter at each interpolation point. (The interpolated
        curve is represented as a vector-valued function of a scalar parameter.) If periodic ==
        True, then len(parameters) must be len(intepolation points) + 1, otherwise len(parameters)
        must be equal to len(interpolation points).
          scale: whether to scale the specified tangent vectors before interpolating. Each
        tangent is scaled, so it's length is equal to the derivative of the Lagrange interpolated
        curve. I.e., set this to True, if you want to use only the direction of the tangent
        vectors specified by ``tangents``, but not their magnitude.
          tol: tolerance of the algorithm (consult OCC documentation). Used to check that the
        specified points are not too close to each other, and that tangent vectors are not too
        short. (In either case interpolation may fail.)
          list_of_vector: list[Vector]:
          tangents: Sequence[Vector]:  (Default value = None)
          periodic: bool:  (Default value = False)
          parameters: Sequence[float]:  (Default value = None)
          scale: bool:  (Default value = True)
          tol: float:  (Default value = 1e-6)

        Returns:
          an Edge

        """
        pnts = TColgp_HArray1OfPnt(1, len(list_of_vector))
        for ix, v in enumerate(list_of_vector):
            pnts.SetValue(ix + 1, v.to_pnt())

        if parameters is None:
            spline_builder = GeomAPI_Interpolate(pnts, periodic, tol)
        else:
            if len(parameters) != (len(list_of_vector) + periodic):
                raise ValueError(
                    "There must be one parameter for each interpolation point "
                    "(plus one if periodic), or none specified. Parameter count: "
                    f"{len(parameters)}, point count: {len(list_of_vector)}"
                )
            parameters_array = TColStd_HArray1OfReal(1, len(parameters))
            for p_index, p_value in enumerate(parameters):
                parameters_array.SetValue(p_index + 1, p_value)

            spline_builder = GeomAPI_Interpolate(pnts, parameters_array, periodic, tol)

        if tangents:
            if len(tangents) == 2 and len(list_of_vector) != 2:
                # Specify only initial and final tangent:
                t1, t2 = tangents
                spline_builder.Load(t1.wrapped, t2.wrapped, scale)
            else:
                if len(tangents) != len(list_of_vector):
                    raise ValueError(
                        f"There must be one tangent for each interpolation point, "
                        f"or just two end point tangents. Tangent count: "
                        f"{len(tangents)}, point count: {len(list_of_vector)}"
                    )

                # Specify a tangent for each interpolation point:
                tangents_array = TColgp_Array1OfVec(1, len(tangents))
                tangent_enabled_array = TColStd_HArray1OfBoolean(1, len(tangents))
                for t_index, t_value in enumerate(tangents):
                    tangent_enabled_array.SetValue(t_index + 1, t_value is not None)
                    tangent_vec = t_value if t_value is not None else Vector()
                    tangents_array.SetValue(t_index + 1, tangent_vec.wrapped)

                spline_builder.Load(tangents_array, tangent_enabled_array, scale)

        spline_builder.Perform()
        if not spline_builder.IsDone():
            raise ValueError("B-spline interpolation failed")

        spline_geom = spline_builder.Curve()

        return cls(BRepBuilderAPI_MakeEdge(spline_geom).Edge())

    @classmethod
    def make_spline_approx(
        cls,
        list_of_vector: list[Vector],
        tol: float = 1e-3,
        smoothing: Tuple[float, float, float] = None,
        min_deg: int = 1,
        max_deg: int = 6,
    ) -> Edge:
        """Approximate a spline through the provided points.

        Args:
          list_of_vector: a list of Vectors that represent the points
          tol: tolerance of the algorithm (consult OCC documentation).
          smoothing: optional tuple of 3 weights use for variational smoothing (default: None)
          min_deg: minimum spline degree. Enforced only when smoothing is None (default: 1)
          max_deg: maximum spline degree (default: 6)
          list_of_vector: list[Vector]:
          tol: float:  (Default value = 1e-3)
          smoothing: Tuple[float:
          float:
          float]:  (Default value = None)
          min_deg: int:  (Default value = 1)
          max_deg: int:  (Default value = 6)

        Returns:
          an Edge

        """
        pnts = TColgp_HArray1OfPnt(1, len(list_of_vector))
        for ix, v in enumerate(list_of_vector):
            pnts.SetValue(ix + 1, v.to_pnt())

        if smoothing:
            spline_builder = GeomAPI_PointsToBSpline(
                pnts, *smoothing, DegMax=max_deg, Tol3D=tol
            )
        else:
            spline_builder = GeomAPI_PointsToBSpline(
                pnts, DegMin=min_deg, DegMax=max_deg, Tol3D=tol
            )

        if not spline_builder.IsDone():
            raise ValueError("B-spline approximation failed")

        spline_geom = spline_builder.Curve()

        return cls(BRepBuilderAPI_MakeEdge(spline_geom).Edge())

    @classmethod
    def make_three_point_arc(
        cls, v1: VectorLike, v2: VectorLike, v3: VectorLike
    ) -> Edge:
        """Makes a three point arc through the provided points

        Args:
          cls: param v1: start vector
          v2: middle vector
          v3: end vector
          v1: VectorLike:
          v2: VectorLike:
          v3: VectorLike:

        Returns:
          an edge object through the three points

        """
        circle_geom = GC_MakeArcOfCircle(
            Vector(v1).to_pnt(), Vector(v2).to_pnt(), Vector(v3).to_pnt()
        ).Value()

        return cls(BRepBuilderAPI_MakeEdge(circle_geom).Edge())

    @classmethod
    def make_tangent_arc(cls, v1: VectorLike, v2: VectorLike, v3: VectorLike) -> Edge:
        """Makes a tangent arc from point v1, in the direction of v2 and ends at
        v3.

        Args:
          cls: param v1: start vector
          v2: tangent vector
          v3: end vector
          v1: VectorLike:
          v2: VectorLike:
          v3: VectorLike:

        Returns:
          an edge

        """
        circle_geom = GC_MakeArcOfCircle(
            Vector(v1).to_pnt(), Vector(v2).wrapped, Vector(v3).to_pnt()
        ).Value()

        return cls(BRepBuilderAPI_MakeEdge(circle_geom).Edge())

    @classmethod
    def make_line(cls, v1: VectorLike, v2: VectorLike) -> Edge:
        """Create a line between two points

        Args:
          v1: Vector that represents the first point
          v2: Vector that represents the second point
          v1: VectorLike:
          v2: VectorLike:

        Returns:
          A linear edge between the two provided points

        """
        return cls(
            BRepBuilderAPI_MakeEdge(Vector(v1).to_pnt(), Vector(v2).to_pnt()).Edge()
        )

    def distribute_locations(
        self: Union[Wire, Edge],
        count: int,
        start: float = 0.0,
        stop: float = 1.0,
        positions_only: bool = False,
    ) -> list[Location]:
        """Distribute Locations

        Distribute locations along edge or wire.

        Args:
          count(int): Number of locations to generate
          start(float): position along Edge|Wire to start. Defaults to 0.0.
          stop(float): position along Edge|Wire to end. Defaults to 1.0.
          positions_only(bool): only generate position not orientation. Defaults to False.
          self: Union[Wire:
          Edge]:
          count: int:
          start: float:  (Default value = 0.0)
          stop: float:  (Default value = 1.0)
          positions_only: bool:  (Default value = False)

        Returns:
          list[Location]: locations distributed along Edge|Wire

        Raises:
          ValueError: count must be two or greater

        """
        if count < 2:
            raise ValueError("count must be two or greater")

        t_values = [start + i * (stop - start) / (count - 1) for i in range(count)]

        locations = []
        if positions_only:
            locations.extend(Location(v) for v in self.positions(t_values))
        else:
            locations.extend(self.locations(t_values, planar=True))
        return locations

    def project_to_shape(
        self,
        target_object: Shape,
        direction: VectorLike = None,
        center: VectorLike = None,
    ) -> list[Edge]:
        """Project Edge

        Project an Edge onto a Shape generating new wires on the surfaces of the object
        one and only one of `direction` or `center` must be provided. Note that one or
        more wires may be generated depending on the topology of the target object and
        location/direction of projection.

        To avoid flipping the normal of a face built with the projected wire the orientation
        of the output wires are forced to be the same as self.

        Args:
          target_object: Object to project onto
          direction: Parallel projection direction. Defaults to None.
          center: Conical center of projection. Defaults to None.
          target_object: Shape:
          direction: VectorLike:  (Default value = None)
          center: VectorLike:  (Default value = None)

        Returns:
          : Projected Edge(s)

        Raises:
          ValueError: Only one of direction or center must be provided

        """
        wire = Wire.assemble_edges([self])
        projected_wires = wire.project_to_shape(target_object, direction, center)
        projected_edges = [w.edges()[0] for w in projected_wires]
        return projected_edges

    def emboss_to_shape(
        self,
        target_object: Shape,
        surface_point: VectorLike,
        surface_x_direction: VectorLike,
        tolerance: float = 0.01,
    ) -> Edge:
        """Emboss Edge on target object

        Emboss an Edge on the XY plane onto a Shape while maintaining
        original edge dimensions where possible.

        Args:
          target_object: Object to emboss onto
          surface_point: Point on target object to start embossing
          surface_x_direction: Direction of x-Axis on target object
          tolerance: maximum allowed error in embossed edge length
          target_object: Shape:
          surface_point: VectorLike:
          surface_x_direction: VectorLike:
          tolerance: float:  (Default value = 0.01)

        Returns:
          : Embossed edge

        """

        # Algorithm - piecewise approximation of points on surface -> generate spline:
        # - successively increasing the number of points to emboss
        #     - create local plane at current point given surface normal and surface x direction
        #     - create new approximate point on local plane from next planar point
        #     - get global position of next approximate point
        #     - using current normal and next approximate point find next surface intersection point and normal
        # - create spline from points
        # - measure length of spline
        # - repeat with more points unless within target tolerance

        def find_point_on_surface(
            current_surface_point: Vector,
            current_surface_normal: Vector,
            planar_relative_position: Vector,
        ) -> Vector:
            """Given a 2D relative position from a surface point, find the closest point on the surface.

            Args:
              current_surface_point: Vector:
              current_surface_normal: Vector:
              planar_relative_position: Vector:

            Returns:

            """
            segment_plane = Plane(
                origin=current_surface_point,
                x_dir=surface_x_direction,
                normal=current_surface_normal,
            )
            target_point = segment_plane.to_world_coords(
                planar_relative_position.to_tuple()
            )
            (next_surface_point, next_surface_normal) = target_object.find_intersection(
                point=target_point, direction=target_point - target_object_center
            )[0]
            return (next_surface_point, next_surface_normal)

        surface_x_direction = Vector(surface_x_direction)

        planar_edge_length = self.length()
        planar_edge_closed = self.is_closed()
        target_object_center = target_object.center()
        loop_count = 0
        subdivisions = 2
        length_error = sys.float_info.max

        while length_error > tolerance and loop_count < 8:

            # Initialize the algorithm by priming it with the start of Edge self
            surface_origin = Vector(surface_point)
            (
                surface_origin_point,
                surface_origin_normal,
            ) = target_object.find_intersection(
                point=surface_origin,
                direction=surface_origin - target_object_center,
            )[
                0
            ]
            planar_relative_position = self.position_at(0)
            (current_surface_point, current_surface_normal) = find_point_on_surface(
                surface_origin_point,
                surface_origin_normal,
                planar_relative_position,
            )
            embossed_edge_points = [current_surface_point]

            # Loop through all of the subdivisions calculating surface points
            for div in range(1, subdivisions + 1):
                planar_relative_position = self.position_at(
                    div / subdivisions
                ) - self.position_at((div - 1) / subdivisions)
                (current_surface_point, current_surface_normal) = find_point_on_surface(
                    current_surface_point,
                    current_surface_normal,
                    planar_relative_position,
                )
                embossed_edge_points.append(current_surface_point)

            # Create a spline through the points and determine length difference from target
            embossed_edge = Edge.make_spline(
                embossed_edge_points, periodic=planar_edge_closed
            )
            length_error = planar_edge_length - embossed_edge.length()
            loop_count = loop_count + 1
            subdivisions = subdivisions * 2

        if length_error > tolerance:
            raise RuntimeError(
                f"length error of {length_error} exceeds requested tolerance {tolerance}"
            )
        if not embossed_edge.is_valid():
            raise RuntimeError("embossed edge invalid")

        return embossed_edge


class Face(Shape):
    """a bounded surface that represents part of the boundary of a solid"""

    def _geom_adaptor(self) -> Geom_Surface:
        """ """
        return BRep_Tool.Surface_s(self.wrapped)

    def _uv_bounds(self) -> Tuple[float, float, float, float]:

        return BRepTools.UVBounds_s(self.wrapped)

    def normal_at(self, location_vector: Vector = None) -> Vector:
        """Computes the normal vector at the desired location on the face.

        Args:
          location_vector(ation_vector: a vector that lies on the surface.): the location to compute the normal at. If none, the center of the face is used.
          location_vector: Vector:  (Default value = None)

        Returns:
          a  vector representing the direction

        """
        # get the geometry
        surface = self._geom_adaptor()

        if location_vector is None:
            u0, u1, v0, v1 = self._uv_bounds()
            u = 0.5 * (u0 + u1)
            v = 0.5 * (v0 + v1)
        else:
            # project point on surface
            projector = GeomAPI_ProjectPointOnSurf(location_vector.to_pnt(), surface)

            u, v = projector.LowerDistanceParameters()

        p = gp_Pnt()
        vn = gp_Vec()
        BRepGProp_Face(self.wrapped).Normal(u, v, p, vn)

        return Vector(vn)

    def center(self) -> Vector:

        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(self.wrapped, properties)

        return Vector(properties.CentreOfMass())

    def outer_wire(self) -> Wire:

        return Wire(BRepTools.OuterWire_s(self.wrapped))

    def inner_wires(self) -> list[Wire]:

        outer = self.outer_wire()

        return [w for w in self.wires() if not w.is_same(outer)]

    @classmethod
    def make_n_sided_surface(
        cls,
        edges: Iterable[Union[Edge, Wire]],
        constraints: Iterable[Union[Edge, Wire, VectorLike, gp_Pnt]],
        continuity: GeomAbs_Shape = GeomAbs_C0,
        degree: int = 3,
        nb_pts_on_cur: int = 15,
        nb_iter: int = 2,
        anisotropy: bool = False,
        tol2d: float = 0.00001,
        tol3d: float = 0.0001,
        tol_ang: float = 0.01,
        tol_curv: float = 0.1,
        max_deg: int = 8,
        max_segments: int = 9,
    ) -> Face:
        """Returns a surface enclosed by a closed polygon defined by 'edges' and going through 'points'.

        Args:
          constraints: type points: list of constraints (points or edges)
          edges: type edges: list of Edge
          continuity(OCC.Core.GeomAbs continuity condition): GeomAbs_C0
          Degree(Integer >= 2): 3 (OCCT default)
          NbPtsOnCur(Integer >= 15): 15 (OCCT default)
          NbIter: 2 (OCCT default)
          Anisotropie(Boolean): False (OCCT default)
          edges: Iterable[Union[Edge:
          Wire]]:
          constraints: Iterable[Union[Edge:
          Wire:
          VectorLike:
          gp_Pnt]]:
          continuity: GeomAbs_Shape:  (Default value = GeomAbs_C0)
          degree: int:  (Default value = 3)
          nb_pts_on_cur: int:  (Default value = 15)
          nb_iter: int:  (Default value = 2)
          anisotropy: bool:  (Default value = False)
          tol2d: float:  (Default value = 0.00001)
          tol3d: float:  (Default value = 0.0001)
          tol_ang: float:  (Default value = 0.01)
          tol_curv: float:  (Default value = 0.1)
          max_deg: int:  (Default value = 8)
          max_segments: int:  (Default value = 9)

        Returns:

        """

        n_sided = BRepOffsetAPI_MakeFilling(
            degree,
            nb_pts_on_cur,
            nb_iter,
            anisotropy,
            tol2d,
            tol3d,
            tol_ang,
            tol_curv,
            max_deg,
            max_segments,
        )

        # outer edges
        for el in edges:
            if isinstance(el, Edge):
                n_sided.Add(el.wrapped, continuity)
            else:
                for el_edge in el.edges():
                    n_sided.Add(el_edge.wrapped, continuity)

        # (inner) constraints
        for c in constraints:
            if isinstance(c, gp_Pnt):
                n_sided.Add(c)
            elif isinstance(c, Vector):
                n_sided.Add(c.to_pnt())
            elif isinstance(c, tuple):
                n_sided.Add(Vector(c).to_pnt())
            elif isinstance(c, Edge):
                n_sided.Add(c.wrapped, GeomAbs_C0, False)
            elif isinstance(c, Wire):
                for e in c.edges():
                    n_sided.Add(e.wrapped, GeomAbs_C0, False)
            else:
                raise ValueError(f"Invalid constraint {c}")

        # build, fix and return
        n_sided.Build()

        face = n_sided.Shape()

        return Face(face).fix()

    @classmethod
    def make_plane(
        cls,
        length: float = None,
        width: float = None,
        base_pnt: VectorLike = (0, 0, 0),
        dir: VectorLike = (0, 0, 1),
    ) -> Face:
        base_pnt = Vector(base_pnt)
        dir = Vector(dir)

        pln_geom = gp_Pln(base_pnt.to_pnt(), dir.to_dir())

        if length and width:
            pln_shape = BRepBuilderAPI_MakeFace(
                pln_geom, -width * 0.5, width * 0.5, -length * 0.5, length * 0.5
            ).Face()
        else:
            pln_shape = BRepBuilderAPI_MakeFace(pln_geom).Face()

        return cls(pln_shape)

    @overload
    @classmethod
    def make_ruled_surface(cls, edge_or_wire1: Edge, edge_or_wire2: Edge) -> Face:
        ...

    @overload
    @classmethod
    def make_ruled_surface(cls, edge_or_wire1: Wire, edge_or_wire2: Wire) -> Face:
        ...

    @classmethod
    def make_ruled_surface(cls, edge_or_wire1, edge_or_wire2):
        """'make_ruled_surface(Edge|Wire,Edge|Wire) -- Make a ruled surface
        Create a ruled surface out of two edges or wires. If wires are used then
        these must have the same number of edges

        Args:
          edge_or_wire1:
          edge_or_wire2:

        Returns:

        """

        if isinstance(edge_or_wire1, Wire):
            return cls.cast(
                BRepFill.Shell_s(edge_or_wire1.wrapped, edge_or_wire2.wrapped)
            )
        else:
            return cls.cast(
                BRepFill.Face_s(edge_or_wire1.wrapped, edge_or_wire2.wrapped)
            )

    @classmethod
    def make_from_wires(cls, outer_wire: Wire, inner_wires: list[Wire] = []) -> Face:
        """Makes a planar face from one or more wires

        Args:
          outer_wire: Wire:
          inner_wires: list[Wire]:  (Default value = [])

        Returns:

        """

        if inner_wires and not outer_wire.is_closed():
            raise ValueError("Cannot build face(s): outer wire is not closed")

        # check if wires are coplanar
        ws = Compound.make_compound([outer_wire] + inner_wires)
        if not BRepLib_FindSurface(ws.wrapped, OnlyPlane=True).Found():
            raise ValueError("Cannot build face(s): wires not planar")

        # fix outer wire
        sf_s = ShapeFix_Shape(outer_wire.wrapped)
        sf_s.Perform()
        wo = TopoDS.Wire_s(sf_s.Shape())

        face_builder = BRepBuilderAPI_MakeFace(wo, True)

        for w in inner_wires:
            if not w.is_closed():
                raise ValueError("Cannot build face(s): inner wire is not closed")
            face_builder.Add(w.wrapped)

        face_builder.Build()

        if not face_builder.IsDone():
            raise ValueError(f"Cannot build face(s): {face_builder.Error()}")

        face = face_builder.Face()

        sf_f = ShapeFix_Face(face)
        sf_f.FixOrientation()
        sf_f.Perform()

        return cls(sf_f.Result())

    @classmethod
    def make_spline_approx(
        cls,
        points: list[list[Vector]],
        tol: float = 1e-2,
        smoothing: Tuple[float, float, float] = None,
        min_deg: int = 1,
        max_deg: int = 3,
    ) -> Face:
        """Approximate a spline surface through the provided points.

        Args:
          points: a 2D list of Vectors that represent the points
          tol: tolerance of the algorithm (consult OCC documentation).
          smoothing: optional tuple of 3 weights use for variational smoothing (default: None)
          min_deg: minimum spline degree. Enforced only when smoothing is None (default: 1)
          max_deg: maximum spline degree (default: 6)
          points: list[list[Vector]]:
          tol: float:  (Default value = 1e-2)
          smoothing: Tuple[float:
          float:
          float]:  (Default value = None)
          min_deg: int:  (Default value = 1)
          max_deg: int:  (Default value = 3)

        Returns:
          an Face

        """
        points_ = TColgp_HArray2OfPnt(1, len(points), 1, len(points[0]))

        for i, vi in enumerate(points):
            for j, v in enumerate(vi):
                points_.SetValue(i + 1, j + 1, v.to_pnt())

        if smoothing:
            spline_builder = GeomAPI_PointsToBSplineSurface(
                points_, *smoothing, DegMax=max_deg, Tol3D=tol
            )
        else:
            spline_builder = GeomAPI_PointsToBSplineSurface(
                points_, DegMin=min_deg, DegMax=max_deg, Tol3D=tol
            )

        if not spline_builder.IsDone():
            raise ValueError("B-spline approximation failed")

        spline_geom = spline_builder.Surface()

        return cls(BRepBuilderAPI_MakeFace(spline_geom, Precision.Confusion_s()).Face())

    def fillet_2d(self, radius: float, vertices: Iterable[Vertex]) -> Face:
        """Apply 2D fillet to a face

        Args:
          radius: float:
          vertices: Iterable[Vertex]:

        Returns:

        """

        fillet_builder = BRepFilletAPI_MakeFillet2d(self.wrapped)

        for v in vertices:
            fillet_builder.AddFillet(v.wrapped, radius)

        fillet_builder.Build()

        return self.__class__(fillet_builder.Shape())

    def chamfer_2d(self, d: float, vertices: Iterable[Vertex]) -> Face:
        """Apply 2D chamfer to a face

        Args:
          d: float:
          vertices: Iterable[Vertex]:

        Returns:

        """

        chamfer_builder = BRepFilletAPI_MakeFillet2d(self.wrapped)
        edge_map = self._entities_from(Vertex.__name__, Edge.__name__)

        for v in vertices:
            edges = edge_map[v]
            if len(edges) < 2:
                raise ValueError("Cannot chamfer at this location")

            e1, e2 = edges

            chamfer_builder.AddChamfer(
                TopoDS.Edge_s(e1.wrapped), TopoDS.Edge_s(e2.wrapped), d, d
            )

        chamfer_builder.Build()

        return self.__class__(chamfer_builder.Shape()).fix()

    def to_pln(self) -> gp_Pln:
        """Convert this face to a gp_Pln.

        Note the Location of the resulting plane may not equal the center of this face,
        however the resulting plane will still contain the center of this face.

        Args:

        Returns:

        """

        adaptor = BRepAdaptor_Surface(self.wrapped)
        return adaptor.Plane()

    def thicken(self, depth: float, direction: Vector = None) -> Solid:
        """Thicken Face

        Create a solid from a potentially non planar face by thickening along the normals.

        .. image:: thickenFace.png

        Non-planar faces are thickened both towards and away from the center of the sphere.

        Args:
          depth: Amount to thicken face(s), can be positive or negative.
          direction: The direction vector can be used to
        indicate which way is 'up', potentially flipping the face normal direction
        such that many faces with different normals all go in the same direction
        (direction need only be +/- 90 degrees from the face normal). Defaults to None.
          depth: float:
          direction: Vector:  (Default value = None)

        Returns:
          : The resulting Solid object

        Raises:
          RuntimeError: Opencascade internal failures

        """

        # Check to see if the normal needs to be flipped
        adjusted_depth = depth
        if direction is not None:
            face_center = self.center()
            face_normal = self.normal_at(face_center).normalized()
            if face_normal.dot(direction.normalized()) < 0:
                adjusted_depth = -depth

        solid = BRepOffset_MakeOffset()
        solid.Initialize(
            self.wrapped,
            Offset=adjusted_depth,
            Tol=1.0e-5,
            Mode=BRepOffset_Skin,
            # BRepOffset_RectoVerso - which describes the offset of a given surface shell along both
            # sides of the surface but doesn't seem to work
            Intersection=True,
            SelfInter=False,
            Join=GeomAbs_Intersection,  # Could be GeomAbs_Arc,GeomAbs_Tangent,GeomAbs_Intersection
            Thickening=True,
            RemoveIntEdges=True,
        )
        solid.MakeOffsetShape()
        try:
            result = Solid(solid.Shape())
        except StdFail_NotDone as e:
            raise RuntimeError("Error applying thicken to given Face") from e

        return result.clean()

    @classmethod
    def construct_on(cls, f: Face, outer: Wire, *inner: Wire) -> Face:

        bldr = BRepBuilderAPI_MakeFace(f._geom_adaptor(), outer.wrapped)

        for w in inner:
            bldr.Add(TopoDS.Wire_s(w.wrapped.Reversed()))

        return cls(bldr.Face()).fix()

    def project(self, other: Face, d: VectorLike) -> Face:

        outer_p = tcast(Wire, self.outer_wire().project(other, d))
        inner_p = (tcast(Wire, w.project(other, d)) for w in self.inner_wires())

        return self.construct_on(other, outer_p, *inner_p)

    def project_to_shape(
        self,
        target_object: Shape,
        direction: VectorLike = None,
        center: VectorLike = None,
        internal_face_points: list[Vector] = [],
    ) -> list[Face]:
        """Project Face to target Object

        Project a Face onto a Shape generating new Face(s) on the surfaces of the object
        one and only one of `direction` or `center` must be provided.

        The two types of projections are illustrated below:

        .. image:: flatProjection.png
            :alt: flatProjection

        .. image:: conicalProjection.png
            :alt: conicalProjection

        Note that an array of faces is returned as the projection might result in faces
        on the "front" and "back" of the object (or even more if there are intermediate
        surfaces in the projection path). faces "behind" the projection are not
        returned.

        To help refine the resulting face, a list of planar points can be passed to
        augment the surface definition. For example, when projecting a circle onto a
        sphere, a circle will result which will get converted to a planar circle face.
        If no points are provided, a single center point will be generated and used for
        this purpose.

        Args:
          target_object: Object to project onto
          direction: Parallel projection direction
          center: Conical center of projection
          internal_face_points: Points refining shape
          target_object: Shape:
          direction: VectorLike:  (Default value = None)
          center: VectorLike:  (Default value = None)
          internal_face_points: list[Vector]:  (Default value = [])

        Returns:
          Face(s) projected on target object

        Raises:
          ValueError: Only one of direction or center must be provided

        """

        # There are four phase to creation of the projected face:
        # 1- extract the outer wire and project
        # 2- extract the inner wires and project
        # 3- extract surface points within the outer wire
        # 4- build a non planar face

        if not (direction is None) ^ (center is None):
            raise ValueError("One of either direction or center must be provided")
        if direction is not None:
            direction_vector = Vector(direction)
            center_point = None
        else:
            direction_vector = None
            center_point = Vector(center)

        # Phase 1 - outer wire
        planar_outer_wire = self.outer_wire()
        planar_outer_wire_orientation = planar_outer_wire.wrapped.Orientation()
        projected_outer_wires = planar_outer_wire.project_to_shape(
            target_object, direction_vector, center_point
        )
        logging.debug(
            f"projecting outerwire resulted in {len(projected_outer_wires)} wires"
        )
        # Phase 2 - inner wires
        planar_inner_wire_list = [
            w
            if w.wrapped.Orientation() != planar_outer_wire_orientation
            else Wire(w.wrapped.Reversed())
            for w in self.inner_wires()
        ]
        # Project inner wires on to potentially multiple surfaces
        projected_inner_wire_list = [
            w.project_to_shape(target_object, direction_vector, center_point)
            for w in planar_inner_wire_list
        ]
        # Need to transpose this list so it's organized by surface then inner wires
        projected_inner_wire_list = [list(x) for x in zip(*projected_inner_wire_list)]

        for i in range(len(planar_inner_wire_list)):
            logging.debug(
                f"projecting innerwire resulted in {len(projected_inner_wire_list[i])} wires"
            )
        # Ensure the length of the list is the same as that of the outer wires
        projected_inner_wire_list.extend(
            [
                []
                for _ in range(
                    len(projected_outer_wires) - len(projected_inner_wire_list)
                )
            ]
        )

        # Phase 3 - Find points on the surface by projecting a "grid" composed of internal_face_points

        # Not sure if it's always a good idea to add an internal central point so the next
        # two lines of code can be easily removed without impacting the rest
        if not internal_face_points:
            internal_face_points = [planar_outer_wire.center()]

        if not internal_face_points:
            projected_grid_points = []
        else:
            if len(internal_face_points) == 1:
                planar_grid = Edge.make_line(
                    planar_outer_wire.position_at(0), internal_face_points[0]
                )
            else:
                planar_grid = Wire.make_polygon(
                    [Vector(v) for v in internal_face_points]
                )
            projected_grids = planar_grid.project_to_shape(
                target_object, direction_vector, center_point
            )
            projected_grid_points = [
                [Vector(*v.to_tuple()) for v in grid.vertices()]
                for grid in projected_grids
            ]
        logging.debug(
            f"projecting grid resulted in {len(projected_grid_points)} points"
        )

        # Phase 4 - Build the faces
        projected_faces = [
            ow.make_non_planar_face(
                surface_points=projected_grid_points[i],
                interior_wires=projected_inner_wire_list[i],
            )
            for i, ow in enumerate(projected_outer_wires)
        ]

        return projected_faces

    def emboss_to_shape(
        self,
        target_object: Shape,
        surface_point: VectorLike,
        surface_x_direction: VectorLike,
        internal_face_points: list[Vector] = None,
        tolerance: float = 0.01,
    ) -> Face:
        """Emboss Face on target object

        Emboss a Face on the XY plane onto a Shape while maintaining
        original face dimensions where possible.

        Unlike projection, a single Face is returned. The internal_face_points
        parameter works as with projection.

        Args:
          target_object: Object to emboss onto
          surface_point: Point on target object to start embossing
          surface_x_direction: Direction of x-Axis on target object
          internal_face_points: Surface refinement points. Defaults to None.
          tolerance: maximum allowed error in embossed wire length. Defaults to 0.01.
          target_object: Shape:
          surface_point: VectorLike:
          surface_x_direction: VectorLike:
          internal_face_points: list[Vector]:  (Default value = None)
          tolerance: float:  (Default value = 0.01)

        Returns:
          Face: Embossed face

        """
        # There are four phase to creation of the projected face:
        # 1- extract the outer wire and project
        # 2- extract the inner wires and project
        # 3- extract surface points within the outer wire
        # 4- build a non planar face

        # Phase 1 - outer wire
        planar_outer_wire = self.outer_wire()
        planar_outer_wire_orientation = planar_outer_wire.wrapped.Orientation()
        embossed_outer_wire = planar_outer_wire.emboss_to_shape(
            target_object, surface_point, surface_x_direction, tolerance
        )

        # Phase 2 - inner wires
        planar_inner_wires = [
            w
            if w.wrapped.Orientation() != planar_outer_wire_orientation
            else Wire(w.wrapped.Reversed())
            for w in self.inner_wires()
        ]
        embossed_inner_wires = [
            w.emboss_to_shape(
                target_object, surface_point, surface_x_direction, tolerance
            )
            for w in planar_inner_wires
        ]

        # Phase 3 - Find points on the surface by projecting a "grid" composed of internal_face_points

        # Not sure if it's always a good idea to add an internal central point so the next
        # two lines of code can be easily removed without impacting the rest
        if not internal_face_points:
            internal_face_points = [planar_outer_wire.center()]

        if not internal_face_points:
            embossed_surface_points = []
        else:
            if len(internal_face_points) == 1:
                planar_grid = Edge.make_line(
                    planar_outer_wire.position_at(0), internal_face_points[0]
                )
            else:
                planar_grid = Wire.make_polygon(
                    [Vector(v) for v in internal_face_points]
                )

            embossed_grid = planar_grid.emboss_to_shape(
                target_object, surface_point, surface_x_direction, tolerance
            )
            embossed_surface_points = [
                Vector(*v.to_tuple()) for v in embossed_grid.vertices()
            ]

        # Phase 4 - Build the faces
        embossed_face = embossed_outer_wire.make_non_planar_face(
            surface_points=embossed_surface_points, interior_wires=embossed_inner_wires
        )

        return embossed_face

    def make_holes(self, interior_wires: list[Wire]) -> Face:
        """Make Holes in Face

        Create holes in the Face 'self' from interior_wires which must be entirely interior.
        Note that making holes in faces is more efficient than using boolean operations
        with solid object. Also note that OCCT core may fail unless the orientation of the wire
        is correct - use ``Wire(forward_wire.wrapped.Reversed())`` to reverse a wire.

        Example:

            For example, make a series of slots on the curved walls of a cylinder.

        .. code-block:: python

            cylinder = Workplane("XY").cylinder(100, 50, centered=(True, True, False))
            cylinder_wall = cylinder.faces("not %Plane").val()
            path = cylinder.section(50).edges().val()
            slot_wire = Workplane("XY").slot2D(60, 10, angle=90).wires().val()
            embossed_slot_wire = slot_wire.emboss_to_shape(
                target_object=cylinder.val(),
                surface_point=path.position_at(0),
                surface_x_direction=path.tangent_at(0),
            )
            embossed_slot_wires = [
                embossed_slot_wire.rotate((0, 0, 0), (0, 0, 1), a) for a in range(90, 271, 20)
            ]
            cylinder_wall_with_holes = cylinder_wall.make_holes(embossed_slot_wires)

        .. image:: slotted_cylinder.png

        Args:
          interior_wires: a list of hole outline wires
          interior_wires: list[Wire]:

        Returns:
          Face: 'self' with holes

        Raises:
          RuntimeError: adding interior hole in non-planar face with provided interior_wires
          RuntimeError: resulting face is not valid

        """
        # Add wires that define interior holes - note these wires must be entirely interior
        makeface_object = BRepBuilderAPI_MakeFace(self.wrapped)
        for w in interior_wires:
            makeface_object.Add(w.wrapped)
        try:
            surface_face = Face(makeface_object.Face())
        except StdFail_NotDone as e:
            raise RuntimeError(
                "Error adding interior hole in non-planar face with provided interior_wires"
            ) from e

        surface_face = surface_face.fix()
        # if not surface_face.is_valid():
        #     raise RuntimeError("non planar face is invalid")

        return surface_face

    def is_inside(self, point: VectorLike, tolerance: float = 1.0e-6) -> bool:
        """Point inside Face

        Returns whether or not the point is inside a Face within the specified tolerance.
        Points on the edge of the Face are considered inside.

        Args:
          point(VectorLike): tuple or Vector representing 3D point to be tested
          tolerance(float): tolerance for inside determination. Defaults to 1.0e-6.
          point: VectorLike:
          tolerance: float:  (Default value = 1.0e-6)

        Returns:
          bool: indicating whether or not point is within Face

        """
        return Compound.make_compound([self]).is_inside(point, tolerance)

    def make_finger_joints(
        self: Face,
        finger_joint_edge: Edge,
        finger_depth: float,
        target_finger_width: float,
        corner_face_counter: dict,
        open_internal_vertices: dict,
        align_to_bottom: bool = True,
        external_corner: bool = True,
        face_index: int = 0,
    ) -> Face:
        """make_finger_joints

        Given a Face and an Edge, create finger joints by cutting notches.

        Args:
          self(Face): Face to modify
          finger_joint_edge(Edge): Edge of Face to modify
          finger_depth(float): thickness of the notch from edge
          target_finger_width(float): approximate with of notch - actual finger width
        will be calculated such that there are an integer number of fingers on Edge
          corner_face_counter(dict): the set of faces associated with every corner
          open_internal_vertices(dict): is a vertex part an opening?
          align_to_bottom(bool): start with a finger or notch. Defaults to True.
          external_corner(bool): cut from external corners, add to internal corners.
        Defaults to True.
          face_index(int): the index of the current face. Defaults to 0.
          self: Face:
          finger_joint_edge: Edge:
          finger_depth: float:
          target_finger_width: float:
          corner_face_counter: dict:
          open_internal_vertices: dict:
          align_to_bottom: bool:  (Default value = True)
          external_corner: bool:  (Default value = True)
          face_index: int:  (Default value = 0)

        Returns:
          Face: the Face with notches on one edge

        """
        edge_length = finger_joint_edge.length()
        finger_count = round(edge_length / target_finger_width)
        finger_width = edge_length / (finger_count)
        face_center = self.center()

        edge_origin = finger_joint_edge.position_at(0)
        edge_tangent = finger_joint_edge.tangent_at(0)
        edge_plane = Plane(
            origin=edge_origin,
            x_dir=edge_tangent,
            normal=edge_tangent.cross((face_center - edge_origin).normalized()),
        )
        # Need to determine the vertex that corresponds to the position_at(0) point
        end_vertex_index = int(
            edge_origin == finger_joint_edge.vertices()[0].to_vector()
        )
        start_vertex_index = (end_vertex_index + 1) % 2
        start_vertex = finger_joint_edge.vertices()[start_vertex_index]
        end_vertex = finger_joint_edge.vertices()[end_vertex_index]
        if start_vertex.to_vector() != edge_origin:
            raise RuntimeError("Error in determining start_vertex")

        if align_to_bottom and finger_count % 2 == 0:
            finger_offset = -finger_width / 2
            tab_count = finger_count // 2
        elif align_to_bottom and finger_count % 2 == 1:
            finger_offset = 0
            tab_count = (finger_count + 1) // 2
        elif not align_to_bottom and finger_count % 2 == 0:
            finger_offset = +finger_width / 2
            tab_count = finger_count // 2
        elif not align_to_bottom and finger_count % 2 == 1:
            finger_offset = 0
            tab_count = finger_count // 2

        # Calculate the positions of the cutouts (for external corners) or extra tabs
        # (for internal corners)
        x_offset = (tab_count - 1) * finger_width - edge_length / 2 + finger_offset
        finger_positions = [
            Vector(i * 2 * finger_width - x_offset, 0, 0) for i in range(tab_count)
        ]

        # Align the Face to the given Edge
        face_local = edge_plane.to_local_coords(self)

        # Note that Face.make_plane doesn't work here as a rectangle creator
        # as it is inconsistent as to what is the x direction.
        finger = Face.make_from_wires(
            Wire.make_rect(
                finger_width,
                2 * finger_depth,
                center=Vector(),
                x_dir=Vector(1, 0, 0),
                normal=face_local.normal_at(Vector()) * -1,
            ),
            [],
        )
        start_part_finger = Face.make_from_wires(
            Wire.make_rect(
                finger_width - finger_depth,
                2 * finger_depth,
                center=Vector(finger_depth / 2, 0, 0),
                x_dir=Vector(1, 0, 0),
                normal=face_local.normal_at(Vector()) * -1,
            ),
            [],
        )
        end_part_finger = start_part_finger.translate((-finger_depth, 0, 0))

        # Logging strings
        tab_type = {finger: "whole", start_part_finger: "start", end_part_finger: "end"}
        vertex_type = {True: "start", False: "end"}

        def len_corner_face_counter(corner: Vertex) -> int:
            return (
                len(corner_face_counter[corner]) if corner in corner_face_counter else 0
            )

        for position in finger_positions:
            # Is this a corner?, if so which one
            if position.X == finger_width / 2:
                corner = start_vertex
                part_finger = start_part_finger
            elif position.X == edge_length - finger_width / 2:
                corner = end_vertex
                part_finger = end_part_finger
            else:
                corner = None

            Face.operation = Face.cut if external_corner else Face.fuse

            if corner is not None:
                # To avoid missing corners (or extra inside corners) check to see if
                # the corner is already notched
                if (
                    face_local.is_inside(position)
                    and external_corner
                    or not face_local.is_inside(position)
                    and not external_corner
                ):
                    if corner in corner_face_counter:
                        corner_face_counter[corner].add(face_index)
                    else:
                        corner_face_counter[corner] = set([face_index])
                if external_corner:
                    tab = finger if len_corner_face_counter(corner) < 3 else part_finger
                else:
                    # tab = part_finger if len_corner_face_counter(corner) < 3 else finger
                    if corner in open_internal_vertices:
                        tab = finger
                    else:
                        tab = (
                            part_finger
                            if len_corner_face_counter(corner) < 3
                            else finger
                        )

                # Modify the face
                face_local = face_local.operation(tab.translate(position))

                logging.debug(
                    f"Corner {corner}, vertex={vertex_type[corner==start_vertex]}, "
                    f"{len_corner_face_counter(corner)=}, normal={self.normal_at(face_center)}, tab={tab_type[tab]}, "
                    f"{face_local.intersect(tab.translate(position)).area()=:.0f}, {tab.area()/2=:.0f}"
                )
            else:
                face_local = face_local.operation(finger.translate(position))

            # Need to clean and revert the generated Compound back to a Face
            face_local = face_local.clean().faces()[0]

        # Relocate the face back to its original position
        new_face = edge_plane.fromLocalCoords(face_local)

        return new_face


class Shell(Shape):
    """the outer boundary of a surface"""

    @classmethod
    def make_shell(cls, list_of_faces: Iterable[Face]) -> Shell:

        shell_builder = BRepBuilderAPI_Sewing()

        for face in list_of_faces:
            shell_builder.Add(face.wrapped)

        shell_builder.Perform()
        s = shell_builder.SewedShape()

        return cls(s)


class Solid(Shape, Mixin3D):
    """a single solid"""

    @staticmethod
    def is_solid(obj: Shape) -> bool:
        """Returns true if the object is a solid, false otherwise

        Args:
          obj: Shape:

        Returns:

        """
        if hasattr(obj, "shape_type"):
            if obj.shape_type == Solid or (
                obj.shape_type == Compound and len(obj.solids()) > 0
            ):
                return True
        return False

    @classmethod
    def make_solid(cls, shell: Shell) -> Solid:

        return cls(ShapeFix_Solid().SolidFromShell(shell.wrapped))

    @classmethod
    def make_box(
        cls,
        length: float,
        width: float,
        height: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
    ) -> Solid:
        """make_box(length,width,height,[pnt,dir]) -- Make a box located in pnt with the dimensions (length,width,height)
        By default pnt=Vector(0,0,0) and dir=Vector(0,0,1)'

        Args:
          length: float:
          width: float:
          height: float:
          pnt: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):

        Returns:

        """
        return cls(
            BRepPrimAPI_MakeBox(
                gp_Ax2(Vector(pnt).to_pnt(), Vector(dir).to_dir()),
                length,
                width,
                height,
            ).Shape()
        )

    @classmethod
    def make_cone(
        cls,
        radius1: float,
        radius2: float,
        height: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
        angle_degrees: float = 360,
    ) -> Solid:
        """Make a cone with given radii and height
        By default pnt=Vector(0,0,0),
        dir=Vector(0,0,1) and angle=360'

        Args:
          radius1: float:
          radius2: float:
          height: float:
          pnt: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):
          angle_degrees: float:  (Default value = 360)

        Returns:

        """
        return cls(
            BRepPrimAPI_MakeCone(
                gp_Ax2(Vector(pnt).to_pnt(), Vector(dir).to_dir()),
                radius1,
                radius2,
                height,
                angle_degrees * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def make_cylinder(
        cls,
        radius: float,
        height: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
        angle_degrees: float = 360,
    ) -> Solid:
        """make_cylinder(radius,height,[pnt,dir,angle]) --
        Make a cylinder with a given radius and height
        By default pnt=Vector(0,0,0),dir=Vector(0,0,1) and angle=360'

        Args:
          radius: float:
          height: float:
          pnt: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):
          angle_degrees: float:  (Default value = 360)

        Returns:

        """
        return cls(
            BRepPrimAPI_MakeCylinder(
                gp_Ax2(Vector(pnt).to_pnt(), Vector(dir).to_dir()),
                radius,
                height,
                angle_degrees * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def make_torus(
        cls,
        radius1: float,
        radius2: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
        angle_degrees1: float = 0,
        angle_degrees2: float = 360,
    ) -> Solid:
        """make_torus(radius1,radius2,[pnt,dir,angle1,angle2,angle]) --
        Make a torus with a given radii and angles
        By default pnt=Vector(0,0,0),dir=Vector(0,0,1),angle1=0
        ,angle1=360 and angle=360'

        Args:
          radius1: float:
          radius2: float:
          pnt: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):
          angle_degrees1: float:  (Default value = 0)
          angle_degrees2: float:  (Default value = 360)

        Returns:

        """
        return cls(
            BRepPrimAPI_MakeTorus(
                gp_Ax2(Vector(pnt).to_pnt(), Vector(dir).to_dir()),
                radius1,
                radius2,
                angle_degrees1 * DEG2RAD,
                angle_degrees2 * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def make_loft(cls, list_of_wire: list[Wire], ruled: bool = False) -> Solid:
        """makes a loft from a list of wires
        The wires will be converted into faces when possible-- it is presumed that nobody ever actually
        wants to make an infinitely thin shell for a real FreeCADPart.

        Args:
          list_of_wire: list[Wire]:
          ruled: bool:  (Default value = False)

        Returns:

        """
        # the True flag requests building a solid instead of a shell.
        if len(list_of_wire) < 2:
            raise ValueError("More than one wire is required")
        loft_builder = BRepOffsetAPI_ThruSections(True, ruled)

        for w in list_of_wire:
            loft_builder.AddWire(w.wrapped)

        loft_builder.Build()

        return cls(loft_builder.Shape())

    @classmethod
    def make_wedge(
        cls,
        dx: float,
        dy: float,
        dz: float,
        xmin: float,
        zmin: float,
        xmax: float,
        zmax: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
    ) -> Solid:
        """Make a wedge located in pnt
        By default pnt=Vector(0,0,0) and dir=Vector(0,0,1)

        Args:
          dx: float:
          dy: float:
          dz: float:
          xmin: float:
          zmin: float:
          xmax: float:
          zmax: float:
          pnt: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):

        Returns:

        """

        return cls(
            BRepPrimAPI_MakeWedge(
                gp_Ax2(Vector(pnt).to_pnt(), Vector(dir).to_dir()),
                dx,
                dy,
                dz,
                xmin,
                zmin,
                xmax,
                zmax,
            ).Solid()
        )

    @classmethod
    def make_sphere(
        cls,
        radius: float,
        pnt: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
        angle_degrees1: float = 0,
        angle_degrees2: float = 90,
        angle_degrees3: float = 360,
    ) -> Shape:
        """Make a sphere with a given radius
        By default pnt=Vector(0,0,0), dir=Vector(0,0,1), angle1=0, angle2=90 and angle3=360

        Args:
          radius: float:
          pnt: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):
          angle_degrees1: float:  (Default value = 0)
          angle_degrees2: float:  (Default value = 90)
          angle_degrees3: float:  (Default value = 360)

        Returns:

        """
        return cls(
            BRepPrimAPI_MakeSphere(
                gp_Ax2(Vector(pnt).to_pnt(), Vector(dir).to_dir()),
                radius,
                angle_degrees1 * DEG2RAD,
                angle_degrees2 * DEG2RAD,
                angle_degrees3 * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def _extrude_aux_spine(
        cls, wire: TopoDS_Wire, spine: TopoDS_Wire, aux_spine: TopoDS_Wire
    ) -> TopoDS_Shape:
        """Helper function for extrude_linear_with_rotation

        Args:
          wire: TopoDS_Wire:
          spine: TopoDS_Wire:
          aux_spine: TopoDS_Wire:

        Returns:

        """
        extrude_builder = BRepOffsetAPI_MakePipeShell(spine)
        extrude_builder.SetMode(aux_spine, False)  # auxiliary spine
        extrude_builder.Add(wire)
        extrude_builder.Build()
        extrude_builder.MakeSolid()
        return extrude_builder.Shape()

    @classmethod
    def extrude_linear_with_rotation(
        cls,
        face: Face,
        vec_center: VectorLike,
        vec_normal: VectorLike,
        angle_degrees: float,
    ) -> Solid:
        """Extrude with Rotation

        Creates a 'twisted prism' by extruding, while simultaneously rotating around the
        extrusion vector.

        Args:
          face: Face
          vec_center: VectorLike: the center point about which to rotate
          vec_normal: VectorLike: a vector along which to extrude the wires
          angle_degrees: float: the angle to rotate through while extruding

        Returns:
          a Solid object
        """

        return cls.extrude_linear_with_rotation(
            face.outer_wire(), face.inner_wires(), vec_center, vec_normal, angle_degrees
        )

    @classmethod
    def extrude_linear(
        cls,
        face: Face,
        vec_normal: VectorLike,
        taper: float = 0,
    ) -> Solid:
        """Extrude a Face into a prismatic solid in the provided direction

        Args:
          face: the Face to extrude
          vec_normal: a vector along which to extrude the wires
          taper: taper angle, default=0

        Returns:
          a Solid object
        """
        if taper == 0:
            prism_builder: Any = BRepPrimAPI_MakePrism(
                face.wrapped, Vector(vec_normal).wrapped, True
            )
        else:
            face_normal = face.normal_at()
            d = 1 if vec_normal.get_angle(face_normal) < 90 * DEG2RAD else -1
            prism_builder = LocOpe_DPrism(
                face.wrapped, d * vec_normal.length, d * taper * DEG2RAD
            )

        return cls(prism_builder.Shape())

    @classmethod
    def revolve(
        cls,
        face: Face,
        angle_degrees: float,
        axis_start: VectorLike,
        axis_end: VectorLike,
    ) -> Solid:
        """Revolve Face

        Revolve a Face about the given Axis by the given angle.

        Args:
            face (Face): the Face to revolve
            angle_degrees (float): the angle to revolve through.
            axis_start (VectorLike): the start point of the axis of rotation
            axis_end (VectorLike): the end point of the axis of rotation

        Returns:
            Solid: the revolved face
        """
        v1 = Vector(axis_start)
        v2 = Vector(axis_end)
        v2 = v2 - v1
        revol_builder = BRepPrimAPI_MakeRevol(
            face.wrapped,
            gp_Ax1(v1.to_pnt(), v2.to_dir()),
            angle_degrees * DEG2RAD,
            True,
        )

        return cls(revol_builder.Shape())

    _transModeDict = {
        "transformed": BRepBuilderAPI_Transformed,
        "round": BRepBuilderAPI_RoundCorner,
        "right": BRepBuilderAPI_RightCorner,
    }

    @classmethod
    def _set_sweep_mode(
        cls,
        builder: BRepOffsetAPI_MakePipeShell,
        path: Union[Wire, Edge],
        mode: Union[Vector, Wire, Edge],
    ) -> bool:

        rotate = False

        if isinstance(mode, Vector):
            ax = gp_Ax2()
            ax.SetLocation(path.start_point().to_pnt())
            ax.SetDirection(mode.to_dir())
            builder.SetMode(ax)
            rotate = True
        elif isinstance(mode, (Wire, Edge)):
            builder.SetMode(cls._to_wire(mode).wrapped, True)

        return rotate

    @staticmethod
    def _to_wire(p: Union[Edge, Wire]) -> Wire:

        if isinstance(p, Edge):
            return_value = Wire.assemble_edges(
                [
                    p,
                ]
            )
        else:
            return_value = p

        return return_value

    @classmethod
    def sweep(
        cls,
        face: Face,
        path: Union[Wire, Edge],
        make_solid: bool = True,
        is_frenet: bool = False,
        mode: Union[Vector, Wire, Edge, None] = None,
        transition_mode: Literal["transformed", "round", "right"] = "transformed",
    ) -> Solid:
        """Sweep

        Sweep the given Face into a prismatic solid along the provided path

        Args:
          face: the Face to sweep
          path: The wire to sweep the face resulting from the wires over
          make_solid: return Solid or Shell (Default value = True)
          is_frenet: Frenet mode (Default value = False)
          mode: additional sweep mode parameters.
          transition_mode: handling of profile orientation at C1 path discontinuities.
            Possible values are {'transformed','round', 'right'} (default: 'right').

        Returns:
          a Solid object
        """

        return face.outer_wire().sweep(
            face.inner_wires(),
            path,
            make_solid,
            is_frenet,
            mode,
            transition_mode,
        )

    @classmethod
    def sweep_multi(
        cls,
        profiles: Iterable[Union[Wire, Face]],
        path: Union[Wire, Edge],
        make_solid: bool = True,
        is_frenet: bool = False,
        mode: Union[Vector, Wire, Edge, None] = None,
    ) -> Solid:
        """Multi section sweep. Only single outer profile per section is allowed.

        Args:
          profiles: list of profiles
          path: The wire to sweep the face resulting from the wires over
          mode: additional sweep mode parameters.
          profiles: Iterable[Union[Wire:
          Face]]:
          path: Union[Wire:
          Edge]:
          make_solid: bool:  (Default value = True)
          is_frenet: bool:  (Default value = False)
          mode: Union[Vector:
          Wire:
          Edge:
          None]:  (Default value = None)

        Returns:
          a Solid object

        """
        if isinstance(path, Edge):
            w = Wire.assemble_edges(
                [
                    path,
                ]
            ).wrapped
        else:
            w = path.wrapped

        builder = BRepOffsetAPI_MakePipeShell(w)

        translate = False
        rotate = False

        if mode:
            rotate = cls._set_sweep_mode(builder, path, mode)
        else:
            builder.SetMode(is_frenet)

        for p in profiles:
            w = p.wrapped if isinstance(p, Wire) else p.outer_wire().wrapped
            builder.Add(w, translate, rotate)

        builder.Build()

        if make_solid:
            builder.MakeSolid()

        return cls(builder.Shape())


class Vertex(Shape):
    """A Single Point in Space"""

    def __init__(self, obj: TopoDS_Shape, for_construction: bool = False):
        """
        Create a vertex
        """
        super(Vertex, self).__init__(obj)

        self.for_construction = for_construction
        self.X, self.Y, self.Z = self.to_tuple()

    def to_tuple(self) -> Tuple[float, float, float]:

        geom_point = BRep_Tool.Pnt_s(self.wrapped)
        return (geom_point.X(), geom_point.Y(), geom_point.Z())

    def center(self) -> Vector:
        """The center of a vertex is itself!"""
        return Vector(self.to_tuple())

    @classmethod
    def make_vertex(cls, x: float, y: float, z: float) -> Vertex:

        return cls(BRepBuilderAPI_MakeVertex(gp_Pnt(x, y, z)).Vertex())

    def __add__(
        self, other: Union[Vertex, Vector, Tuple[float, float, float]]
    ) -> Vertex:
        """Add

        Add to a Vertex with a Vertex, Vector or Tuple

        Args:
            other: Value to add

        Raises:
            TypeError: other not in [Tuple,Vector,Vertex]

        Returns:
            Result

        Example:
            part.faces(">z").vertices("<y and <x").val() + (0, 0, 15)

            which creates a new Vertex 15mm above one extracted from a part. One can add or
            subtract a cadquery ``Vertex``, ``Vector`` or ``tuple`` of float values to a
            Vertex with the provided extensions.
        """
        if isinstance(other, Vertex):
            new_vertex = Vertex.make_vertex(
                self.X + other.X, self.Y + other.Y, self.Z + other.Z
            )
        elif isinstance(other, (Vector, tuple)):
            new_other = Vector(other)
            new_vertex = Vertex.make_vertex(
                self.X + new_other.X, self.Y + new_other.X, self.Z + new_other.Z
            )
        else:
            raise TypeError(
                "Vertex addition only supports Vertex,Vector or tuple(float,float,float) as input"
            )
        return new_vertex

    def __sub__(self, other: Union[Vertex, Vector, tuple]) -> Vertex:
        """Subtract

        Substract a Vertex with a Vertex, Vector or Tuple from self

        Args:
            other: Value to add

        Raises:
            TypeError: other not in [Tuple,Vector,Vertex]

        Returns:
            Result

        Example:
            part.faces(">z").vertices("<y and <x").val() - Vector(10, 0, 0)
        """
        if isinstance(other, Vertex):
            new_vertex = Vertex.make_vertex(
                self.X - other.X, self.Y - other.Y, self.Z - other.Z
            )
        elif isinstance(other, (Vector, tuple)):
            new_other = Vector(other)
            new_vertex = Vertex.make_vertex(
                self.X - new_other.X, self.Y - new_other.Y, self.Z - new_other.Z
            )
        else:
            raise TypeError(
                "Vertex subtraction only supports Vertex,Vector or tuple(float,float,float) as input"
            )
        return new_vertex

    def __repr__(self) -> str:
        """To String

        Convert Vertex to String for display

        Returns:
            Vertex as String
        """
        return f"Vertex: ({self.X}, {self.Y}, {self.Z})"

    def to_vector(self) -> Vector:
        """To Vector

        Convert a Vertex to Vector

        Args:

        Returns:
          : Vector representation of Vertex

        """
        return Vector(self.to_tuple())


class Wire(Shape, Mixin1D):
    """A series of connected, ordered edges, that typically bounds a Face"""

    def _geom_adaptor(self) -> BRepAdaptor_CompCurve:
        """ """

        return BRepAdaptor_CompCurve(self.wrapped)

    def _geom_adaptor_h(self) -> Tuple[BRepAdaptor_CompCurve, BRepAdaptor_CompCurve]:
        """ """

        curve = self._geom_adaptor()

        return curve, BRepAdaptor_CompCurve(curve)

    def close(self) -> Wire:
        """Close a Wire"""

        if not self.is_closed():
            e = Edge.make_line(self.end_point(), self.start_point())
            return_value = Wire.combine((self, e))[0]
        else:
            return_value = self

        return return_value

    @classmethod
    def combine(
        cls, list_of_wires: Iterable[Union[Wire, Edge]], tol: float = 1e-9
    ) -> list[Wire]:
        """Attempt to combine a list of wires and edges into a new wire.

        Args:
          cls: param list_of_wires:
          tol: default 1e-9
          list_of_wires: Iterable[Union[Wire:
          Edge]]:
          tol: float:  (Default value = 1e-9)

        Returns:
          list[Wire]

        """

        edges_in = TopTools_HSequenceOfShape()
        wires_out = TopTools_HSequenceOfShape()

        for e in Compound.make_compound(list_of_wires).edges():
            edges_in.Append(e.wrapped)

        ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

        return [cls(el) for el in wires_out]

    @classmethod
    def assemble_edges(cls, list_of_edges: Iterable[Edge]) -> Wire:
        """Attempts to build a wire that consists of the edges in the provided list

        Args:
          cls: param list_of_edges: a list of Edge objects. The edges are not to be consecutive.
          list_of_edges: Iterable[Edge]:

        Returns:
          a wire with the edges assembled
          :BRepBuilderAPI_MakeWire::Error() values
          :BRepBuilderAPI_WireDone = 0
          :BRepBuilderAPI_EmptyWire = 1
          :BRepBuilderAPI_DisconnectedWire = 2
          :BRepBuilderAPI_NonManifoldWire = 3

        """
        wire_builder = BRepBuilderAPI_MakeWire()

        occ_edges_list = TopTools_ListOfShape()
        for e in list_of_edges:
            occ_edges_list.Append(e.wrapped)
        wire_builder.Add(occ_edges_list)

        wire_builder.Build()

        if not wire_builder.IsDone():
            w = (
                "BRepBuilderAPI_MakeWire::Error(): returns the construction status. BRepBuilderAPI_WireDone if the wire is built, or another value of the BRepBuilderAPI_WireError enumeration indicating why the construction failed = "
                + str(wire_builder.Error())
            )
            warnings.warn(w)

        return cls(wire_builder.Wire())

    @classmethod
    def make_circle(cls, radius: float, center: VectorLike, normal: VectorLike) -> Wire:
        """Makes a Circle centered at the provided point, having normal in the provided direction

        Args:
          radius: floating point radius of the circle, must be > 0
          center: vector representing the center of the circle
          normal: vector representing the direction of the plane the circle should lie in
          radius: float:
          center: VectorLike:
          normal: VectorLike:

        Returns:

        """

        circle_edge = Edge.make_circle(radius, center, normal)
        w = cls.assemble_edges([circle_edge])
        return w

    @classmethod
    def make_ellipse(
        cls,
        x_radius: float,
        y_radius: float,
        center: VectorLike,
        normal: VectorLike,
        x_dir: VectorLike,
        angle1: float = 360.0,
        angle2: float = 360.0,
        rotation_angle: float = 0.0,
        closed: bool = True,
    ) -> Wire:
        """Makes an Ellipse centered at the provided point, having normal in the provided direction

        Args:
          x_radius: floating point major radius of the ellipse (x-axis), must be > 0
          y_radius: floating point minor radius of the ellipse (y-axis), must be > 0
          center: vector representing the center of the circle
          normal: vector representing the direction of the plane the circle should lie in
          angle1: start angle of arc
          angle2: end angle of arc
          rotation_angle: angle to rotate the created ellipse / arc
          x_radius: float:
          y_radius: float:
          center: VectorLike:
          normal: VectorLike:
          x_dir: VectorLike:
          angle1: float:  (Default value = 360.0)
          angle2: float:  (Default value = 360.0)
          rotation_angle: float:  (Default value = 0.0)
          closed: bool:  (Default value = True)

        Returns:
          Wire

        """

        ellipse_edge = Edge.make_ellipse(
            x_radius, y_radius, center, normal, x_dir, angle1, angle2
        )

        if angle1 != angle2 and closed:
            line = Edge.make_line(ellipse_edge.end_point(), ellipse_edge.start_point())
            w = cls.assemble_edges([ellipse_edge, line])
        else:
            w = cls.assemble_edges([ellipse_edge])

        if rotation_angle != 0.0:
            w = w.rotate(center, Vector(center) + Vector(normal), rotation_angle)

        return w

    @classmethod
    def make_polygon(
        cls,
        list_of_vertices: Iterable[VectorLike],
        for_construction: bool = False,
    ) -> Wire:
        # convert list of tuples into Vectors.
        wire_builder = BRepBuilderAPI_MakePolygon()

        for v in list_of_vertices:
            wire_builder.Add(Vector(v).to_pnt())

        w = cls(wire_builder.Wire())
        w.for_construction = for_construction

        return w

    @classmethod
    def make_helix(
        cls,
        pitch: float,
        height: float,
        radius: float,
        center: VectorLike = Vector(0, 0, 0),
        dir: VectorLike = Vector(0, 0, 1),
        angle: float = 360.0,
        lefthand: bool = False,
    ) -> Wire:
        """Make a helix with a given pitch, height and radius
        By default a cylindrical surface is used to create the helix. If
        the fourth parameter is set (the apex given in degree) a conical surface is used instead'

        Args:
          pitch: float:
          height: float:
          radius: float:
          center: VectorLike:  (Default value = Vector(0)
          0:
          0):
          dir: VectorLike:  (Default value = Vector(0)
          1):
          angle: float:  (Default value = 360.0)
          lefthand: bool:  (Default value = False)

        Returns:

        """

        # 1. build underlying cylindrical/conical surface
        if angle == 360.0:
            geom_surf: Geom_Surface = Geom_CylindricalSurface(
                gp_Ax3(Vector(center).to_pnt(), Vector(dir).to_dir()), radius
            )
        else:
            geom_surf = Geom_ConicalSurface(
                gp_Ax3(Vector(center).to_pnt(), Vector(dir).to_dir()),
                angle * DEG2RAD,
                radius,
            )

        # 2. construct an segment in the u,v domain
        if lefthand:
            geom_line = Geom2d_Line(gp_Pnt2d(0.0, 0.0), gp_Dir2d(-2 * pi, pitch))
        else:
            geom_line = Geom2d_Line(gp_Pnt2d(0.0, 0.0), gp_Dir2d(2 * pi, pitch))

        # 3. put it together into a wire
        n_turns = height / pitch
        u_start = geom_line.Value(0.0)
        u_stop = geom_line.Value(n_turns * sqrt((2 * pi) ** 2 + pitch**2))
        geom_seg = GCE2d_MakeSegment(u_start, u_stop).Value()

        e = BRepBuilderAPI_MakeEdge(geom_seg, geom_surf).Edge()

        # 4. Convert to wire and fix building 3d geom from 2d geom
        w = BRepBuilderAPI_MakeWire(e).Wire()
        BRepLib.BuildCurves3d_s(w, 1e-6, MaxSegment=2000)  # NB: preliminary values

        return cls(w)

    def stitch(self, other: Wire) -> Wire:
        """Attempt to stich wires

        Args:
          other: Wire:

        Returns:

        """

        wire_builder = BRepBuilderAPI_MakeWire()
        wire_builder.Add(TopoDS.Wire_s(self.wrapped))
        wire_builder.Add(TopoDS.Wire_s(other.wrapped))
        wire_builder.Build()

        return self.__class__(wire_builder.Wire())

    def offset_2d(
        self, d: float, kind: Literal["arc", "intersection", "tangent"] = "arc"
    ) -> list[Wire]:
        """Offsets a planar wire

        Args:
          d: float:
          kind: Literal["arc":
          "intersection":
          "tangent"]:  (Default value = "arc")

        Returns:

        """

        kind_dict = {
            "arc": GeomAbs_JoinType.GeomAbs_Arc,
            "intersection": GeomAbs_JoinType.GeomAbs_Intersection,
            "tangent": GeomAbs_JoinType.GeomAbs_Tangent,
        }

        offset = BRepOffsetAPI_MakeOffset()
        offset.Init(kind_dict[kind])
        offset.AddWire(self.wrapped)
        offset.Perform(d)

        obj = downcast(offset.Shape())

        if isinstance(obj, TopoDS_Compound):
            return_value = [self.__class__(el.wrapped) for el in Compound(obj)]
        else:
            return_value = [self.__class__(obj)]

        return return_value

    def fillet_2d(self, radius: float, vertices: Iterable[Vertex]) -> Wire:
        """Apply 2D fillet to a wire

        Args:
          radius: float:
          vertices: Iterable[Vertex]:

        Returns:

        """

        f = Face.make_from_wires(self)

        return f.fillet_2d(radius, vertices).outer_wire()

    def chamfer_2d(self, d: float, vertices: Iterable[Vertex]) -> Wire:
        """Apply 2D chamfer to a wire

        Args:
          d: float:
          vertices: Iterable[Vertex]:

        Returns:

        """

        f = Face.make_from_wires(self)

        return f.chamfer_2d(d, vertices).outer_wire()

    def make_rect(
        width: float,
        height: float,
        center: Vector,
        normal: Vector,
        x_dir: Vector = None,
    ) -> Wire:
        """Make Rectangle

        Make a Rectangle centered on center with the given normal

        Args:
          width(float): width (local x)
          height(float): height (local y)
          center(Vector): rectangle center point
          normal(Vector): rectangle normal
          x_dir(Vector): x direction. Defaults to None.
          width: float:
          height: float:
          center: Vector:
          normal: Vector:
          x_dir: Vector:  (Default value = None)

        Returns:
          Wire: The centered rectangle

        """
        corners_local = [
            (width / 2, height / 2),
            (width / 2, -height / 2),
            (-width / 2, -height / 2),
            (-width / 2, height / 2),
            (width / 2, height / 2),
        ]
        if x_dir is None:
            user_plane = Plane(origin=center, normal=normal)
        else:
            user_plane = Plane(origin=center, x_dir=x_dir, normal=normal)
        corners_world = [user_plane.to_world_coords(c) for c in corners_local]
        return Wire.make_polygon(corners_world)

    def make_non_planar_face(
        self,
        surface_points: list[Vector] = None,
        interior_wires: list[Wire] = None,
    ) -> Face:
        """Create Non-Planar Face with perimeter Wire

        Create a potentially non-planar face bounded by exterior Wire,
        optionally refined by surface_points with optional holes defined by
        interior_wires.

        The **surface_points** parameter can be used to refine the resulting Face. If no
        points are provided a single central point will be used to help avoid the
        creation of a planar face.

        Args:
          surface_points: Points on the surface that refine the shape. Defaults to None.
          interior_wires: Hole(s) in the face. Defaults to None.
          surface_points: list[Vector]:  (Default value = None)
          interior_wires: list[Wire]:  (Default value = None)

        Returns:
          : Non planar face

        Raises:
          RuntimeError: Opencascade core exceptions building face

        """
        return make_non_planar_face(self, surface_points, interior_wires)

    def project_to_shape(
        self,
        target_object: Shape,
        direction: VectorLike = None,
        center: VectorLike = None,
    ) -> list[Wire]:
        """Project Wire

        Project a Wire onto a Shape generating new wires on the surfaces of the object
        one and only one of `direction` or `center` must be provided. Note that one or
        more wires may be generated depending on the topology of the target object and
        location/direction of projection.

        To avoid flipping the normal of a face built with the projected wire the orientation
        of the output wires are forced to be the same as self.

        Args:
          target_object: Object to project onto
          direction: Parallel projection direction. Defaults to None.
          center: Conical center of projection. Defaults to None.
          target_object: Shape:
          direction: VectorLike:  (Default value = None)
          center: VectorLike:  (Default value = None)

        Returns:
          : Projected wire(s)

        Raises:
          ValueError: Only one of direction or center must be provided

        """
        if not (direction is None) ^ (center is None):
            raise ValueError("One of either direction or center must be provided")
        if direction is not None:
            direction_vector = Vector(direction).normalized()
            center_point = None
        else:
            direction_vector = None
            center_point = Vector(center)

        # Project the wire on the target object
        if not direction_vector is None:
            projection_object = BRepProj_Projection(
                self.wrapped,
                Shape.cast(target_object.wrapped).wrapped,
                gp_Dir(*direction_vector.to_tuple()),
            )
        else:
            projection_object = BRepProj_Projection(
                self.wrapped,
                Shape.cast(target_object.wrapped).wrapped,
                gp_Pnt(*center_point.to_tuple()),
            )

        # Generate a list of the projected wires with aligned orientation
        output_wires = []
        target_orientation = self.wrapped.Orientation()
        while projection_object.More():
            projected_wire = projection_object.Current()
            if target_orientation == projected_wire.Orientation():
                output_wires.append(Wire(projected_wire))
            else:
                output_wires.append(Wire(projected_wire.Reversed()))
            projection_object.Next()

        logging.debug(f"wire generated {len(output_wires)} projected wires")

        # BRepProj_Projection is inconsistent in the order that it returns projected
        # wires, sometimes front first and sometimes back - so sort this out by sorting
        # by distance from the original planar wire
        if len(output_wires) > 1:
            output_wires_distances = []
            planar_wire_center = self.center()
            for output_wire in output_wires:
                output_wire_center = output_wire.center()
                if direction_vector is not None:
                    output_wire_direction = (
                        output_wire_center - planar_wire_center
                    ).normalized()
                    if output_wire_direction.dot(direction_vector) >= 0:
                        output_wires_distances.append(
                            (
                                output_wire,
                                (output_wire_center - planar_wire_center).length,
                            )
                        )
                else:
                    output_wires_distances.append(
                        (output_wire, (output_wire_center - center_point).length)
                    )

            output_wires_distances.sort(key=lambda x: x[1])
            logging.debug(
                f"projected, filtered and sorted wire list is of length {len(output_wires_distances)}"
            )
            output_wires = [w[0] for w in output_wires_distances]

        return output_wires

    def emboss_to_shape(
        self,
        target_object: Shape,
        surface_point: VectorLike,
        surface_x_direction: VectorLike,
        tolerance: float = 0.01,
    ) -> Wire:
        """Emboss Wire on target object

        Emboss an Wire on the XY plane onto a Shape while maintaining
        original wire dimensions where possible.

        .. image:: embossWire.png

        The embossed wire can be used to build features as:

        .. image:: embossFeature.png

        with the `sweep() <https://cadquery.readthedocs.io/en/latest/_modules/cadquery/occ_impl/shapes.html#Solid.sweep>`_ method.

        Args:
          target_object: Object to emboss onto
          surface_point: Point on target object to start embossing
          surface_x_direction: Direction of x-Axis on target object
          tolerance: maximum allowed error in embossed wire length. Defaults to 0.01.
          target_object: Shape:
          surface_point: VectorLike:
          surface_x_direction: VectorLike:
          tolerance: float:  (Default value = 0.01)

        Returns:
          : Embossed wire

        Raises:
          RuntimeError: Embosses wire is invalid

        """
        import warnings

        # planar_edges = self.edges()
        planar_edges = self.sorted_edges()
        for i, planar_edge in enumerate(planar_edges[:-1]):
            if (
                planar_edge.position_at(1) - planar_edges[i + 1].position_at(0)
            ).length > tolerance:
                warnings.warn(
                    "edges in provided wire are not sequential - emboss may fail"
                )
                logging.warning(
                    "edges in provided wire are not sequential - emboss may fail"
                )
        planar_closed = self.is_closed()
        logging.debug(f"embossing wire with {len(planar_edges)} edges")
        edges_in = TopTools_HSequenceOfShape()
        wires_out = TopTools_HSequenceOfShape()

        # Need to keep track of the separation between adjacent edges
        first_start_point = None
        last_end_point = None
        edge_separatons = []
        surface_point = Vector(surface_point)
        surface_x_direction = Vector(surface_x_direction)

        # If the wire doesn't start at the origin, create an embossed construction line to get
        # to the beginning of the first edge
        if planar_edges[0].position_at(0) == Vector(0, 0, 0):
            edge_surface_point = surface_point
            planar_edge_end_point = Vector(0, 0, 0)
        else:
            construction_line = Edge.make_line(
                Vector(0, 0, 0), planar_edges[0].position_at(0)
            )
            embossed_construction_line = construction_line.emboss_to_shape(
                target_object, surface_point, surface_x_direction, tolerance
            )
            edge_surface_point = embossed_construction_line.position_at(1)
            planar_edge_end_point = planar_edges[0].position_at(0)

        # Emboss each edge and add them to the wire builder
        for planar_edge in planar_edges:
            local_planar_edge = planar_edge.translate(-planar_edge_end_point)
            embossed_edge = local_planar_edge.emboss_to_shape(
                target_object, edge_surface_point, surface_x_direction, tolerance
            )
            edge_surface_point = embossed_edge.position_at(1)
            planar_edge_end_point = planar_edge.position_at(1)
            if first_start_point is None:
                first_start_point = embossed_edge.position_at(0)
                first_edge = embossed_edge
            edges_in.Append(embossed_edge.wrapped)
            if last_end_point is not None:
                edge_separatons.append(
                    (embossed_edge.position_at(0) - last_end_point).length
                )
            last_end_point = embossed_edge.position_at(1)

        # Set the tolerance of edge connection to more than the worst case edge separation
        # max_edge_separation = max(edge_separatons)
        closure_gap = (last_end_point - first_start_point).length
        logging.debug(f"embossed wire closure gap {closure_gap:0.3f}")
        if planar_closed and closure_gap > tolerance:
            logging.debug(f"closing gap in embossed wire of size {closure_gap}")
            gap_edge = Edge.make_spline(
                [last_end_point, first_start_point],
                tangents=[embossed_edge.tangent_at(1), first_edge.tangent_at(0)],
            )
            edges_in.Append(gap_edge.wrapped)

        ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(
            edges_in,
            tolerance,
            False,
            wires_out,
        )
        # Note: wires_out is an OCP.TopTools.TopTools_HSequenceOfShape not a simple list
        embossed_wires = [w for w in wires_out]
        embossed_wire = Wire(embossed_wires[0])

        if planar_closed and not embossed_wire.is_closed():
            embossed_wire.close()
            logging.debug(
                f"embossed wire was not closed, did fixing succeed: {embossed_wire.is_closed()}"
            )

        embossed_wire = embossed_wire.fix()

        if not embossed_wire.is_valid():
            raise RuntimeError("embossed wire is not valid")

        return embossed_wire

    def sorted_edges(self, tolerance: float = 1e-5):
        """edges sorted by position

        Extract the edges from the wire and sort them such that the end of one
        edge is within tolerance of the start of the next edge

        Args:
          tolerance(float): Max separation between sequential edges.
        Defaults to 1e-5.
          tolerance: float:  (Default value = 1e-5)

        Returns:
          Edge: edges sorted by position

        Raises:
          ValueError: Wire is disjointed

        """
        unsorted_edges = self.edges()
        sorted_edges = [unsorted_edges.pop(0)]
        while unsorted_edges:
            found = False
            for i in range(len(unsorted_edges)):
                if (
                    sorted_edges[-1].position_at(1) - unsorted_edges[i].position_at(0)
                ).length < tolerance:
                    sorted_edges.append(unsorted_edges.pop(i))
                    found = True
                    break
            if not found:
                raise ValueError("Edge segments are separated by tolerance or more")

        return sorted_edges

    def extrude_linear(
        self,
        inner_wires: list[Wire],
        vec_normal: VectorLike,
        taper: float = 0,
    ) -> Solid:
        """Extrude self and the list of inner wires into a prismatic solid in
        the provided direction

        Args:
          inner_wires: a list of inner wires
          vec_normal: a vector along which to extrude the wires
          taper: taper angle, default=0

        Returns:
          a Solid object

          The wires must not intersect

          Extruding wires is very non-trivial.  Nested wires imply very different geometry, and
          there are many geometries that are invalid. In general, the following conditions must be met:

          * all wires must be closed
          * there cannot be any intersecting or self-intersecting wires
          * wires must be listed from outside in
          * more than one levels of nesting is not supported reliably

          This method will attempt to sort the wires, but there is much work remaining to make this method
          reliable.

        """

        if taper == 0:
            face = Face.make_from_wires(self, inner_wires)
        else:
            face = Face.make_from_wires(self)

        return Face.extrude_linear(face, vec_normal, taper)

    def extrude_linear_with_rotation(
        self,
        inner_wires: list[Wire],
        vec_center: VectorLike,
        vec_normal: VectorLike,
        angle_degrees: float,
    ) -> Solid:
        """Extrude with Rotation

        Creates a 'twisted prism' by extruding, while simultaneously rotating around the extrusion vector.

        Though the signature may appear to be similar enough to extrude_linear to merit combining them, the
        construction methods used here are different enough that they should be separate.

        At a high level, the steps followed are:
        (1) accept a set of wires
        (2) create another set of wires like this one, but which are transformed and rotated
        (3) create a ruledSurface between the sets of wires
        (4) create a shell and compute the resulting object

        Args:
          inner_wires: list[Wire]: a list of inner wires
          vec_center: VectorLike: the center point about which to rotate
          vec_normal: VectorLike: a vector along which to extrude the wires
          angle_degrees: float: the angle to rotate through while extruding

        Returns:
          a Solid object

        """
        # make straight spine
        straight_spine_e = Edge.make_line(vec_center, vec_center.add(vec_normal))
        straight_spine_w = Wire.combine(
            [
                straight_spine_e,
            ]
        )[0].wrapped

        # make an auxiliary spine
        pitch = 360.0 / angle_degrees * vec_normal.length
        radius = 1
        aux_spine_w = Wire.make_helix(
            pitch, vec_normal.length, radius, center=vec_center, dir=vec_normal
        ).wrapped

        # extrude the outer wire
        outer_solid = Solid._extrude_aux_spine(
            self.wrapped, straight_spine_w, aux_spine_w
        )

        # extrude inner wires
        inner_solids = [
            Solid._extrude_aux_spine(w.wrapped, straight_spine_w, aux_spine_w)
            for w in inner_wires
        ]

        # combine the inner solids into compound
        inner_comp = Compound._make_compound(inner_solids)

        # subtract from the outer solid
        return Solid(BRepAlgoAPI_Cut(outer_solid, inner_comp).Shape())

    def revolve(
        self,
        inner_wires: list[Wire],
        angle_degrees: float,
        axis_start: VectorLike,
        axis_end: VectorLike,
    ) -> Solid:
        """Revolve the list of wires into a solid in the provided direction

        Args:
          inner_wires: a list of inner wires
          angle_degrees(float, anything less than 360 degrees will leave the shape open): the angle to revolve through.
          axis_start(tuple, a two tuple): the start point of the axis of rotation
          axis_end(tuple, a two tuple): the end point of the axis of rotation

        Returns:
          a Solid object

          The wires must not intersect

          * all wires must be closed
          * there cannot be any intersecting or self-intersecting wires
          * wires must be listed from outside in
          * more than one levels of nesting is not supported reliably
          * the wire(s) that you're revolving cannot be centered

          This method will attempt to sort the wires, but there is much work remaining to make this method
          reliable.

        """
        face = Face.make_from_wires(self, inner_wires)

        return Face.revolve(face, angle_degrees, axis_start, axis_end)

    def sweep(
        self,
        inner_wires: list[Wire],
        path: Union[Wire, Edge],
        make_solid: bool = True,
        is_frenet: bool = False,
        mode: Union[Vector, Wire, Edge, None] = None,
        transition_mode: Literal["transformed", "round", "right"] = "transformed",
    ) -> Shape:
        """Sweep

        Sweep self and the list of inner wires into a prismatic solid along the provided path

        Args:
          inner_wires: a list of inner wires
          path: The wire to sweep the face resulting from the wires over
          make_solid: return Solid or Shell (Default value = True)
          is_frenet: Frenet mode (Default value = False)
          mode: additional sweep mode parameters.
          transition_mode: handling of profile orientation at C1 path discontinuities.
            Possible values are {'transformed','round', 'right'} (default: 'right').

        Returns:
          a Solid object
        """
        p = Solid._to_wire(path)

        shapes = []
        for w in [self] + inner_wires:
            builder = BRepOffsetAPI_MakePipeShell(p.wrapped)

            translate = False
            rotate = False

            # handle sweep mode
            if mode:
                rotate = Solid._set_sweep_mode(builder, path, mode)
            else:
                builder.SetMode(is_frenet)

            builder.SetTransitionMode(Solid._transModeDict[transition_mode])

            builder.Add(w.wrapped, translate, rotate)

            builder.Build()
            if make_solid:
                builder.MakeSolid()

            shapes.append(Shape.cast(builder.Shape()))

        return_value, inner_shapes = shapes[0], shapes[1:]

        if inner_shapes:
            return_value = return_value.cut(*inner_shapes)

        return return_value


def downcast(obj: TopoDS_Shape) -> TopoDS_Shape:
    """Downcasts a TopoDS object to suitable specialized type

    Args:
      obj: TopoDS_Shape:

    Returns:

    """

    f_downcast: Any = downcast_LUT[shapetype(obj)]
    return_value = f_downcast(obj)

    return return_value


def edges_to_wires(edges: Iterable[Edge], tol: float = 1e-6) -> list[Wire]:
    """Convert edges to a list of wires.

    Args:
      edges: Iterable[Edge]:
      tol: float:  (Default value = 1e-6)

    Returns:

    """

    edges_in = TopTools_HSequenceOfShape()
    wires_out = TopTools_HSequenceOfShape()

    for e in edges:
        edges_in.Append(e.wrapped)
    ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

    return [Wire(el) for el in wires_out]


def fix(obj: TopoDS_Shape) -> TopoDS_Shape:
    """Fix a TopoDS object to suitable specialized type

    Args:
      obj: TopoDS_Shape:

    Returns:

    """

    sf = ShapeFix_Shape(obj)
    sf.Perform()

    return downcast(sf.Shape())


def make_non_planar_face(
    exterior: Union[Wire, list[Edge]],
    surface_points: list[VectorLike] = None,
    interior_wires: list[Wire] = None,
) -> Face:
    """Create Non-Planar Face

    Create a potentially non-planar face bounded by exterior (wire or edges),
    optionally refined by surface_points with optional holes defined by
    interior_wires.

    Args:
      exterior: Perimeter of face
      surface_points: Points on the surface that refine the shape. Defaults to None.
      interior_wires: Hole(s) in the face. Defaults to None.
      exterior: Union[Wire:
      list[Edge]]:
      surface_points: list[VectorLike]:  (Default value = None)
      interior_wires: list[Wire]:  (Default value = None)

    Returns:
      : Non planar face

    Raises:
      RuntimeError: Opencascade core exceptions building face

    """

    if surface_points:
        surface_points = [Vector(p) for p in surface_points]
    else:
        surface_points = None

    # First, create the non-planar surface
    surface = BRepOffsetAPI_MakeFilling(
        Degree=3,  # the order of energy criterion to minimize for computing the deformation of the surface
        NbPtsOnCur=15,  # average number of points for discretisation of the edges
        NbIter=2,
        Anisotropie=False,
        Tol2d=0.00001,  # the maximum distance allowed between the support surface and the constraints
        Tol3d=0.0001,  # the maximum distance allowed between the support surface and the constraints
        TolAng=0.01,  # the maximum angle allowed between the normal of the surface and the constraints
        TolCurv=0.1,  # the maximum difference of curvature allowed between the surface and the constraint
        MaxDeg=8,  # the highest degree which the polynomial defining the filling surface can have
        MaxSegments=9,  # the greatest number of segments which the filling surface can have
    )
    if isinstance(exterior, Wire):
        outside_edges = exterior.edges()
    else:
        outside_edges = exterior
    for edge in outside_edges:
        surface.Add(edge.wrapped, GeomAbs_C0)

    try:
        surface.Build()
        surface_face = Face(surface.Shape())
    except (StdFail_NotDone, Standard_NoSuchObject) as e:
        raise RuntimeError(
            "Error building non-planar face with provided exterior"
        ) from e
    if surface_points:
        for pt in surface_points:
            surface.Add(gp_Pnt(*pt.to_tuple()))
        try:
            surface.Build()
            surface_face = Face(surface.Shape())
        except StdFail_NotDone as e:
            raise RuntimeError(
                "Error building non-planar face with provided surface_points"
            ) from e

    # Next, add wires that define interior holes - note these wires must be entirely interior
    if interior_wires:
        makeface_object = BRepBuilderAPI_MakeFace(surface_face.wrapped)
        for w in interior_wires:
            makeface_object.Add(w.wrapped)
        try:
            surface_face = Face(makeface_object.Face())
        except StdFail_NotDone as e:
            raise RuntimeError(
                "Error adding interior hole in non-planar face with provided interior_wires"
            ) from e

    surface_face = surface_face.fix()
    if not surface_face.is_valid():
        raise RuntimeError("non planar face is invalid")

    return surface_face


def shapetype(obj: TopoDS_Shape) -> TopAbs_ShapeEnum:

    if obj.IsNull():
        raise ValueError("Null TopoDS_Shape object")

    return obj.ShapeType()


def sort_wires_by_build_order(wire_list: list[Wire]) -> list[list[Wire]]:
    """Tries to determine how wires should be combined into faces.

    Assume:
        The wires make up one or more faces, which could have 'holes'
        Outer wires are listed ahead of inner wires
        there are no wires inside wires inside wires
        ( IE, islands -- we can deal with that later on )
        none of the wires are construction wires

    Compute:
        one or more sets of wires, with the outer wire listed first, and inner
        ones

    Returns, list of lists.

    Args:
      wire_list: list[Wire]:

    Returns:

    """

    # check if we have something to sort at all
    if len(wire_list) < 2:
        return [
            wire_list,
        ]

    # make a Face, NB: this might return a compound of faces
    faces = Face.make_from_wires(wire_list[0], wire_list[1:])

    return_value = []
    for face in faces.faces():
        return_value.append(
            [
                face.outer_wire(),
            ]
            + face.inner_wires()
        )

    return return_value


def wires_to_faces(wire_list: list[Wire]) -> list[Face]:
    """Convert wires to a list of faces.

    Args:
      wire_list: list[Wire]:

    Returns:

    """

    return Face.make_from_wires(wire_list[0], wire_list[1:]).faces()
