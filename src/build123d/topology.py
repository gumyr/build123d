"""
build123d topology

name: topology.py
by:   Gumyr
date: Oct 14, 2022

desc:
    This python module is a CAD library based on OpenCascade containing
    the base Shape class and all of its derived classes.

license:

    Copyright 2022 Gumyr

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
import copy
import io as StringIO
import logging
import os
import platform
import sys
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from io import BytesIO
from itertools import combinations
from math import degrees, radians, inf, pi, sqrt, sin, cos
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple, Type, TypeVar, Union
from typing import cast as tcast
from typing import overload
import xml.etree.cElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

import ezdxf
from anytree import NodeMixin, PreOrderIter, RenderTree
from scipy.spatial import ConvexHull
from typing_extensions import Literal
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersCore import vtkPolyDataNormals, vtkTriangleFilter

import OCP.GeomAbs as ga  # Geometry type enum
import OCP.TopAbs as ta  # Topology type enum
from OCP.Aspect import Aspect_TOL_SOLID
from OCP.BOPAlgo import BOPAlgo_GlueEnum

# used for getting underlying geometry -- is this equivalent to brep adaptor?
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import (
    BRepAdaptor_CompCurve,
    BRepAdaptor_Curve,
    BRepAdaptor_Surface,
)
from OCP.BRepAlgo import BRepAlgo
from OCP.BRepAlgoAPI import (
    BRepAlgoAPI_BooleanOperation,
    BRepAlgoAPI_Common,
    BRepAlgoAPI_Cut,
    BRepAlgoAPI_Fuse,
    BRepAlgoAPI_Splitter,
)
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_Copy,
    BRepBuilderAPI_DisconnectedWire,
    BRepBuilderAPI_EmptyWire,
    BRepBuilderAPI_GTransform,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeSolid,
    BRepBuilderAPI_MakeVertex,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_NonManifoldWire,
    BRepBuilderAPI_RightCorner,
    BRepBuilderAPI_RoundCorner,
    BRepBuilderAPI_Sewing,
    BRepBuilderAPI_Transform,
    BRepBuilderAPI_Transformed,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepFeat import BRepFeat_MakeDPrism
from OCP.BRepFill import BRepFill
from OCP.BRepFilletAPI import (
    BRepFilletAPI_MakeChamfer,
    BRepFilletAPI_MakeFillet,
    BRepFilletAPI_MakeFillet2d,
)
from OCP.BRepGProp import BRepGProp, BRepGProp_Face  # used for mass calculation
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
from OCP.BRepLib import BRepLib, BRepLib_FindSurface
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Skin
from OCP.BRepOffsetAPI import (
    BRepOffsetAPI_MakeFilling,
    BRepOffsetAPI_MakeOffset,
    BRepOffsetAPI_MakePipeShell,
    BRepOffsetAPI_MakeThickSolid,
    BRepOffsetAPI_ThruSections,
)
from OCP.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCone,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakePrism,
    BRepPrimAPI_MakeRevol,
    BRepPrimAPI_MakeSphere,
    BRepPrimAPI_MakeTorus,
    BRepPrimAPI_MakeWedge,
)
from OCP.BRepProj import BRepProj_Projection
from OCP.BRepTools import BRepTools
from OCP.Font import (
    Font_FA_Bold,
    Font_FA_Italic,
    Font_FA_Regular,
    Font_FontMgr,
    Font_SystemFont,
)
from OCP.GC import GC_MakeArcOfCircle, GC_MakeArcOfEllipse  # geometry construction
from OCP.gce import gce_MakeLin
from OCP.GCE2d import GCE2d_MakeSegment
from OCP.GCPnts import GCPnts_AbscissaPoint, GCPnts_QuasiUniformDeflection
from OCP.Geom import (
    Geom_BezierCurve,
    Geom_ConicalSurface,
    Geom_CylindricalSurface,
    Geom_Plane,
    Geom_Surface,
    Geom_TrimmedCurve,
)
from OCP.Geom2d import Geom2d_Curve, Geom2d_Line
from OCP.Geom2dAPI import Geom2dAPI_InterCurveCurve
from OCP.GeomAbs import GeomAbs_C0, GeomAbs_Intersection, GeomAbs_JoinType
from OCP.GeomAPI import (
    GeomAPI_Interpolate,
    GeomAPI_PointsToBSpline,
    GeomAPI_PointsToBSplineSurface,
    GeomAPI_ProjectPointOnSurf,
)
from OCP.GeomConvert import GeomConvert
from OCP.GeomFill import (
    GeomFill_CorrectedFrenet,
    GeomFill_Frenet,
    GeomFill_TrihedronLaw,
)
from OCP.gp import (
    gp_Ax1,
    gp_Ax2,
    gp_Ax3,
    gp_Circ,
    gp_Dir,
    gp_Dir2d,
    gp_Elips,
    gp_Pln,
    gp_Pnt,
    gp_Pnt2d,
    gp_Trsf,
    gp_Vec,
)

# properties used to store mass calculation result
from OCP.GProp import GProp_GProps
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.Interface import Interface_Static
from OCP.IVtkOCC import IVtkOCC_Shape, IVtkOCC_ShapeMesher
from OCP.IVtkVTK import IVtkVTK_ShapeData
from OCP.LocOpe import LocOpe_DPrism
from OCP.NCollection import NCollection_Utf8String
from OCP.Precision import Precision
from OCP.Prs3d import Prs3d_IsoAspect
from OCP.Quantity import Quantity_Color
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCP.ShapeCustom import ShapeCustom, ShapeCustom_RestrictionParameters
from OCP.ShapeFix import ShapeFix_Face, ShapeFix_Shape, ShapeFix_Solid
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

# for catching exceptions
from OCP.Standard import Standard_Failure, Standard_NoSuchObject
from OCP.StdFail import StdFail_NotDone
from OCP.StdPrs import StdPrs_BRepFont
from OCP.StdPrs import StdPrs_BRepTextBuilder as Font_BRepTextBuilder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.StlAPI import StlAPI_Writer

# Array of vectors (used for B-spline interpolation):
# Array of points (used for B-spline construction):
from OCP.TColgp import (
    TColgp_Array1OfPnt,
    TColgp_Array1OfVec,
    TColgp_HArray1OfPnt,
    TColgp_HArray2OfPnt,
)
from OCP.TCollection import TCollection_AsciiString

# Array of floats (used for B-spline interpolation):
# Array of booleans (used for B-spline interpolation):
from OCP.TColStd import (
    TColStd_Array1OfReal,
    TColStd_HArray1OfBoolean,
    TColStd_HArray1OfReal,
)
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer  # Topology explorer
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Builder,
    TopoDS_Compound,
    TopoDS_Face,
    TopoDS_Iterator,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Vertex,
    TopoDS_Wire,
)
from OCP.TopTools import (
    TopTools_HSequenceOfShape,
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_ListOfShape,
)
from build123d.build_enums import (
    Align,
    AngularDirection,
    ApproxOption,
    CenterOf,
    FontStyle,
    FrameMethod,
    GeomType,
    Kind,
    PositionMode,
    SortBy,
    Transition,
    Unit,
    Until,
)
from build123d.geometry import (
    Axis,
    BoundBox,
    Color,
    Location,
    Matrix,
    Plane,
    Rotation,
    RotationLike,
    Vector,
    VectorLike,
)

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


class Mixin1D:
    """Methods to add to the Edge and Wire classes"""

    def start_point(self) -> Vector:
        """The start point of this edge

        Note that circles may have identical start and end points.
        """
        curve = self._geom_adaptor()
        umin = curve.FirstParameter()

        return Vector(curve.Value(umin))

    def end_point(self) -> Vector:
        """The end point of this edge.

        Note that circles may have identical start and end points.
        """
        curve = self._geom_adaptor()
        umax = curve.LastParameter()

        return Vector(curve.Value(umax))

    def param_at(self, distance: float) -> float:
        """Parameter along a curve

        Compute parameter value at the specified normalized distance.

        Args:
            d (float): normalized distance (0.0 >= d >= 1.0)

        Returns:
            float: parameter value
        """
        curve = self._geom_adaptor()

        length = GCPnts_AbscissaPoint.Length_s(curve)
        return GCPnts_AbscissaPoint(
            curve, length * distance, curve.FirstParameter()
        ).Parameter()

    def tangent_at(
        self,
        location_param: float = 0.5,
        position_mode: PositionMode = PositionMode.LENGTH,
    ) -> Vector:
        """Tangent At

        Compute tangent vector at the specified location.

        Args:
            location_param (float, optional): distance or parameter value. Defaults to 0.5.
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.LENGTH.

        Returns:
            Vector: Tangent
        """
        curve = self._geom_adaptor()

        tmp = gp_Pnt()
        res = gp_Vec()

        if position_mode == PositionMode.LENGTH:
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
            find_surface = BRepLib_FindSurface(self.wrapped, OnlyPlane=True)
            surf = find_surface.Surface()

            if isinstance(surf, Geom_Plane):
                pln = surf.Pln()
                return_value = Vector(pln.Axis().Direction())
            else:
                raise ValueError("Normal not defined")

        return return_value

    def center(self, center_of: CenterOf = CenterOf.GEOMETRY) -> Vector:
        """Center of object

        Return the center based on center_of

        Args:
            center_of (CenterOf, optional): centering option. Defaults to CenterOf.GEOMETRY.

        Returns:
            Vector: center
        """
        if center_of == CenterOf.GEOMETRY:
            middle = self.position_at(0.5)
        elif center_of == CenterOf.MASS:
            properties = GProp_GProps()
            BRepGProp.LinearProperties_s(self.wrapped, properties)
            middle = Vector(properties.CentreOfMass())
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    @property
    def length(self) -> float:
        """Edge or Wire length"""
        return GCPnts_AbscissaPoint.Length_s(self._geom_adaptor())

    @property
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
        except (Standard_NoSuchObject, Standard_Failure) as err:
            raise ValueError("Shape could not be reduced to a circle") from err
        return circ.Radius()

    def is_closed(self) -> bool:
        """Are the start and end points equal?"""
        return BRep_Tool.IsClosed_s(self.wrapped)

    def position_at(
        self, distance: float, position_mode: PositionMode = PositionMode.LENGTH
    ) -> Vector:
        """Position At

        Generate a position along the underlying curve.

        Args:
            distance (float): distance or parameter value
            position_mode (PositionMode, optional): position calculation mode. Defaults to
                PositionMode.LENGTH.

        Returns:
            Vector: position on the underlying curve
        """
        curve = self._geom_adaptor()

        if position_mode == PositionMode.LENGTH:
            param = self.param_at(distance)
        else:
            param = distance

        return Vector(curve.Value(param))

    def positions(
        self,
        distances: Iterable[float],
        position_mode: PositionMode = PositionMode.LENGTH,
    ) -> list[Vector]:
        """Positions along curve

        Generate positions along the underlying curve

        Args:
            distances (Iterable[float]): distance or parameter values
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.LENGTH.

        Returns:
            list[Vector]: positions along curve
        """
        return [self.position_at(d, position_mode) for d in distances]

    def location_at(
        self,
        distance: float,
        position_mode: PositionMode = PositionMode.LENGTH,
        frame_method: FrameMethod = FrameMethod.FRENET,
        planar: bool = False,
    ) -> Location:
        """Locations along curve

        Generate a location along the underlying curve.

        Args:
            distance (float): distance or parameter value
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.LENGTH.
            frame_method (FrameMethod, optional): moving frame calculation method.
                Defaults to FrameMethod.FRENET.
            planar (bool, optional): planar mode. Defaults to False.

        Returns:
            Location: A Location object representing local coordinate system
                at the specified distance.
        """
        curve = self._geom_adaptor()

        if position_mode == PositionMode.LENGTH:
            param = self.param_at(distance)
        else:
            param = distance

        law: GeomFill_TrihedronLaw
        if frame_method == FrameMethod.FRENET:
            law = GeomFill_Frenet()
        else:
            law = GeomFill_CorrectedFrenet()

        law.SetCurve(curve)

        tangent, normal, binormal = gp_Vec(), gp_Vec(), gp_Vec()

        law.D0(param, tangent, normal, binormal)
        pnt = curve.Value(param)

        transformation = gp_Trsf()
        if planar:
            transformation.SetTransformation(
                gp_Ax3(pnt, gp_Dir(0, 0, 1), gp_Dir(normal.XYZ())), gp_Ax3()
            )
        else:
            transformation.SetTransformation(
                gp_Ax3(pnt, gp_Dir(tangent.XYZ()), gp_Dir(normal.XYZ())), gp_Ax3()
            )

        return Location(TopLoc_Location(transformation))

    def locations(
        self,
        distances: Iterable[float],
        position_mode: PositionMode = PositionMode.LENGTH,
        frame_method: FrameMethod = FrameMethod.FRENET,
        planar: bool = False,
    ) -> list[Location]:
        """Locations along curve

        Generate location along the curve

        Args:
            distances (Iterable[float]): distance or parameter values
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.LENGTH.
            frame_method (FrameMethod, optional): moving frame calculation method.
                Defaults to FrameMethod.FRENET.
            planar (bool, optional): planar mode. Defaults to False.

        Returns:
            list[Location]: A list of Location objects representing local coordinate
                systems at the specified distances.
        """
        return [
            self.location_at(d, position_mode, frame_method, planar) for d in distances
        ]

    def __matmul__(self: Union[Edge, Wire], position: float):
        """Position on wire operator"""
        return self.position_at(position)

    def __mod__(self: Union[Edge, Wire], position: float):
        """Tangent on wire operator"""
        return self.tangent_at(position)

    def project(
        self, face: Face, direction: VectorLike, closest: bool = True
    ) -> Union[Mixin1D, list[Mixin1D]]:
        """Project onto a face along the specified direction

        Args:
          face: Face:
          direction: VectorLike:
          closest: bool:  (Default value = True)

        Returns:

        """

        bldr = BRepProj_Projection(
            self.wrapped, face.wrapped, Vector(direction).to_dir()
        )
        shapes = Compound(bldr.Shape())

        # select the closest projection if requested
        return_value: Union[Mixin1D, list[Mixin1D]]

        if closest:
            dist_calc = BRepExtrema_DistShapeShape()
            dist_calc.LoadS1(self.wrapped)

            min_dist = inf

            for shape in shapes:
                dist_calc.LoadS2(shape.wrapped)
                dist_calc.Perform()
                dist = dist_calc.Value()

                if dist < min_dist:
                    min_dist = dist
                    return_value = tcast(Mixin1D, shape)

        else:
            return_value = [tcast(Mixin1D, shape) for shape in shapes]

        return return_value


class Mixin3D:
    """Additional methods to add to 3D Shape classes"""

    def fillet(self, radius: float, edge_list: Iterable[Edge]):
        """Fillet

        Fillets the specified edges of this solid.

        Args:
            radius (float): float > 0, the radius of the fillet
            edge_list (Iterable[Edge]): a list of Edge objects, which must belong to this solid

        Returns:
            Any: Filleted solid
        """
        native_edges = [e.wrapped for e in edge_list]

        fillet_builder = BRepFilletAPI_MakeFillet(self.wrapped)

        for native_edge in native_edges:
            fillet_builder.Add(radius, native_edge)

        return self.__class__(fillet_builder.Shape())

    def max_fillet(
        self,
        edge_list: Iterable[Edge],
        tolerance=0.1,
        max_iterations: int = 10,
    ) -> float:
        """Find Maximum Fillet Size

        Find the largest fillet radius for the given Shape and edges with a
        recursive binary search.

        Example:

              max_fillet_radius = my_shape.max_fillet(shape_edges)
              max_fillet_radius = my_shape.max_fillet(shape_edges, tolerance=0.5, max_iterations=8)


        Args:
            edge_list (Iterable[Edge]): a sequence of Edge objects, which must belong to this solid
            tolerance (float, optional): maximum error from actual value. Defaults to 0.1.
            max_iterations (int, optional): maximum number of recursive iterations. Defaults to 10.

        Raises:
            RuntimeError: failed to find the max value
            ValueError: the provided Shape is invalid

        Returns:
            float: maximum fillet radius
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
                    raise fillet_exception
            except fillet_exception:
                return __max_fillet(window_min, window_mid, current_iteration + 1)

            # These numbers work, are they close enough? - if not try larger window
            if window_mid - window_min <= tolerance:
                return_value = window_mid
            else:
                return_value = __max_fillet(
                    window_mid, window_max, current_iteration + 1
                )
            return return_value

        if not self.is_valid():
            raise ValueError("Invalid Shape")

        # Unfortunately, MacOS doesn't support the StdFail_NotDone exception so platform
        # specific exceptions are required.
        if platform.system() == "Darwin":
            fillet_exception = Standard_Failure
        else:
            fillet_exception = StdFail_NotDone

        max_radius = __max_fillet(0.0, 2 * self.bounding_box().diagonal, 0)

        return max_radius

    def chamfer(
        self, length: float, length2: Optional[float], edge_list: Iterable[Edge]
    ):
        """Chamfer

        Chamfers the specified edges of this solid.

        Args:
            length (float): length > 0, the length (length) of the chamfer
            length2 (Optional[float]): length2 > 0, optional parameter for asymmetrical
                chamfer. Should be `None` if not required.
            edge_list (Iterable[Edge]): a list of Edge objects, which must belong to
                this solid

        Returns:
            Any:  Chamfered solid
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
            distance1 = length
            distance2 = length2
        else:
            distance1 = length
            distance2 = length

        for native_edge in native_edges:
            face = edge_face_map.FindFromKey(native_edge).First()
            chamfer_builder.Add(
                distance1, distance2, native_edge, TopoDS.Face_s(face)
            )  # NB: edge_face_map return a generic TopoDS_Shape
        return self.__class__(chamfer_builder.Shape())

    def center(self, center_of: CenterOf = CenterOf.MASS) -> Vector:
        """Return center of object

        Find center of object

        Args:
            center_of (CenterOf, optional): center option. Defaults to CenterOf.MASS.

        Raises:
            ValueError: Center of GEOMETRY is not supported for this object
            NotImplementedError: Unable to calculate center of mass of this object

        Returns:
            Vector: center
        """
        if center_of == CenterOf.GEOMETRY:
            raise ValueError("Center of GEOMETRY is not supported for this object")
        if center_of == CenterOf.MASS:
            properties = GProp_GProps()
            calc_function = shape_properties_LUT[shapetype(self.wrapped)]
            if calc_function:
                calc_function(self.wrapped, properties)
                middle = Vector(properties.CentreOfMass())
            else:
                raise NotImplementedError
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    def shell(
        self,
        faces: Optional[Iterable[Face]],
        thickness: float,
        tolerance: float = 0.0001,
        kind: Kind = Kind.ARC,
    ) -> Solid:
        """Shell

        Make a shelled solid of self.

        Args:
            faces (Optional[Iterable[Face]]): List of faces to be removed,
            which must be part of the solid. Can be an empty list.
            thickness (float): shell thickness - positive shells outwards, negative
                shells inwards.
            tolerance (float, optional): modelling tolerance of the method. Defaults to 0.0001.
            kind (Kind, optional): intersection type. Defaults to Kind.ARC.

        Raises:
            ValueError: Kind.TANGENT not supported

        Returns:
            Solid: A shelled solid.
        """
        if kind == Kind.TANGENT:
            raise ValueError("Kind.TANGENT not supported")

        kind_dict = {
            Kind.ARC: GeomAbs_JoinType.GeomAbs_Arc,
            Kind.INTERSECTION: GeomAbs_JoinType.GeomAbs_Intersection,
        }

        occ_faces_list = TopTools_ListOfShape()
        for face in faces:
            occ_faces_list.Append(face.wrapped)

        shell_builder = BRepOffsetAPI_MakeThickSolid()
        shell_builder.MakeThickSolidByJoin(
            self.wrapped,
            occ_faces_list,
            thickness,
            tolerance,
            Intersection=True,
            Join=kind_dict[kind],
        )
        shell_builder.Build()

        if faces:
            return_value = self.__class__(shell_builder.Shape())

        else:  # if no faces provided a watertight solid will be constructed
            shell1 = self.__class__(shell_builder.Shape()).shells()[0].wrapped
            shell2 = self.shells()[0].wrapped

            # s1 can be outer or inner shell depending on the thickness sign
            if thickness > 0:
                sol = BRepBuilderAPI_MakeSolid(shell1, shell2)
            else:
                sol = BRepBuilderAPI_MakeSolid(shell2, shell1)

            # fix needed for the orientations
            return_value = self.__class__(sol.Shape()).fix()

        return return_value

    def offset_3d(
        self,
        openings: Optional[Iterable[Face]],
        thickness: float,
        tolerance: float = 0.0001,
        kind: Kind = Kind.ARC,
    ) -> Solid:
        """Shell

        Make an offset solid of self.

        Args:
            openings (Optional[Iterable[Face]]): List of faces to be removed,
                which must be part of the solid. Can be an empty list.
            thickness (float): offset amount - positive offset outwards, negative inwards
            tolerance (float, optional): modelling tolerance of the method. Defaults to 0.0001.
            kind (Kind, optional): intersection type. Defaults to Kind.ARC.

        Raises:
            ValueError: Kind.TANGENT not supported

        Returns:
            Solid: A shelled solid.
        """
        if kind == Kind.TANGENT:
            raise ValueError("Kind.TANGENT not supported")

        kind_dict = {
            Kind.ARC: GeomAbs_JoinType.GeomAbs_Arc,
            Kind.INTERSECTION: GeomAbs_JoinType.GeomAbs_Intersection,
            Kind.TANGENT: GeomAbs_JoinType.GeomAbs_Tangent,
        }

        occ_faces_list = TopTools_ListOfShape()
        for face in openings:
            occ_faces_list.Append(face.wrapped)

        offset_builder = BRepOffsetAPI_MakeThickSolid()
        offset_builder.MakeThickSolidByJoin(
            self.wrapped,
            occ_faces_list,
            thickness,
            tolerance,
            Intersection=True,
            RemoveIntEdges=True,
            Join=kind_dict[kind],
        )
        offset_builder.Build()

        offset_occt_solid = offset_builder.Shape()
        offset_solid = self.__class__(offset_occt_solid)

        # The Solid can be inverted, if so reverse
        if offset_solid.volume < 0:
            offset_solid.wrapped.Reverse()

        return offset_solid

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
        solid_classifier = BRepClass3d_SolidClassifier(self.wrapped)
        solid_classifier.Perform(gp_Pnt(*Vector(point).to_tuple()), tolerance)

        return solid_classifier.State() == ta.TopAbs_IN or solid_classifier.IsOnAFace()

    def dprism(
        self,
        basis: Optional[Face],
        bounds: list[Union[Face, Wire]],
        depth: float = None,
        taper: float = 0,
        up_to_face: Face = None,
        thru_all: bool = True,
        additive: bool = True,
    ) -> Solid:
        """dprism

        Make a prismatic feature (additive or subtractive)

        Args:
            basis (Optional[Face]): face to perform the operation on
            bounds (list[Union[Face,Wire]]): list of profiles
            depth (float, optional): depth of the cut or extrusion. Defaults to None.
            taper (float, optional): in degrees. Defaults to 0.
            up_to_face (Face, optional): a face to extrude until. Defaults to None.
            thru_all (bool, optional): cut thru_all. Defaults to True.
            additive (bool, optional): Defaults to True.

        Returns:
            Solid: prismatic feature
        """
        if isinstance(bounds[0], Wire):
            sorted_profiles = sort_wires_by_build_order(bounds)
            faces = [Face.make_from_wires(p[0], p[1:]) for p in sorted_profiles]
        else:
            faces = bounds

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


class Shape(NodeMixin):
    """Shape

    Base class for all CAD objects such as Edge, Face, Solid, etc.

    Args:
        obj (TopoDS_Shape, optional): OCCT object. Defaults to None.
        label (str, optional): Defaults to ''.
        color (Color, optional): Defaults to None.
        material (str, optional): tag for external tools. Defaults to ''.
        joints (dict[str, Joint], optional): names joints - only valid for Solid
            and Compound objects. Defaults to None.
        parent (Compound, optional): assembly parent. Defaults to None.
        children (list[Shape], optional): assembly children - only valid for Compounds.
            Defaults to None.
    """

    def __init__(
        self,
        obj: TopoDS_Shape = None,
        label: str = "",
        color: Color = None,
        material: str = "",
        joints: dict[str, Joint] = None,
        parent: Compound = None,
        children: list[Shape] = None,
    ):
        self.wrapped = downcast(obj) if obj else None
        self.for_construction = False
        self.label = label
        self.color = color
        self.material = material

        # Bind joints to Solid
        if isinstance(self, Solid):
            self.joints = joints if joints else {}

        # Bind joints and children to Compounds (other Shapes can't have children)
        if isinstance(self, Compound):
            self.joints = joints if joints else {}
            self.children = children if children else []

        # parent must be set following children as post install accesses children
        self.parent = parent

    @property
    def location(self) -> Location:
        """Get this Shape's Location"""
        return Location(self.wrapped.Location())

    @location.setter
    def location(self, value: Location):
        """Set Shape's Location to value"""
        self.wrapped.Location(value.wrapped)

    @property
    def position(self) -> Vector:
        """Get the position component of this Shape's Location"""
        return self.location.position

    @position.setter
    def position(self, value: VectorLike):
        """Set the position component of this Shape's Location to value"""
        loc = self.location
        loc.position = value
        self.location = loc

    @property
    def orientation(self) -> Vector:
        """Get the orientation component of this Shape's Location"""
        return self.location.orientation

    @orientation.setter
    def orientation(self, rotations: VectorLike):
        """Set the orientation component of this Shape's Location to rotations"""
        loc = self.location
        loc.orientation = rotations
        self.location = loc

    class _DisplayNode(NodeMixin):
        """Used to create anytree structures from TopoDS_Shapes"""

        def __init__(
            self,
            label: str = "",
            address: int = None,
            position: Union[Vector, Location] = None,
            parent: Shape._DisplayNode = None,
        ):
            self.label = label
            self.address = address
            self.position = position
            self.parent = parent
            self.children = []

    _ordered_shapes = [
        TopAbs_ShapeEnum.TopAbs_COMPOUND,
        TopAbs_ShapeEnum.TopAbs_SOLID,
        TopAbs_ShapeEnum.TopAbs_SHELL,
        TopAbs_ShapeEnum.TopAbs_FACE,
        TopAbs_ShapeEnum.TopAbs_WIRE,
        TopAbs_ShapeEnum.TopAbs_EDGE,
        TopAbs_ShapeEnum.TopAbs_VERTEX,
    ]

    @staticmethod
    def _build_tree(
        shape: TopoDS_Shape,
        tree: list[_DisplayNode],
        parent: _DisplayNode = None,
        limit: TopAbs_ShapeEnum = TopAbs_ShapeEnum.TopAbs_VERTEX,
        show_center: bool = True,
    ) -> list[_DisplayNode]:
        """Create an anytree copy of the TopoDS_Shape structure"""

        obj_type = shape_LUT[shape.ShapeType()]
        if show_center:
            loc = Shape(shape).bounding_box().center()
        else:
            loc = Location(shape.Location())
        tree.append(Shape._DisplayNode(obj_type, id(shape), loc, parent))
        iterator = TopoDS_Iterator()
        iterator.Initialize(shape)
        parent_node = tree[-1]
        while iterator.More():
            child = iterator.Value()
            if Shape._ordered_shapes.index(
                child.ShapeType()
            ) <= Shape._ordered_shapes.index(limit):
                Shape._build_tree(child, tree, parent_node, limit)
            iterator.Next()
        return tree

    @staticmethod
    def _show_tree(root_node, show_center: bool) -> str:
        """Display an assembly or TopoDS_Shape anytree structure"""

        # Calculate the size of the tree labels
        size_tuples = [(node.height, len(node.label)) for node in root_node.descendants]
        size_tuples.append((root_node.height, len(root_node.label)))
        size_tuples_per_level = [
            list(filter(lambda ll: ll[0] == l, size_tuples))
            for l in range(root_node.height + 1)
        ]
        max_sizes_per_level = [
            max(4, max([l[1] for l in level])) for level in size_tuples_per_level
        ]
        level_sizes_per_level = [
            l + i * 4 for i, l in enumerate(reversed(max_sizes_per_level))
        ]
        tree_label_width = max(level_sizes_per_level) + 1

        # Build the tree line by line
        result = ""
        for pre, _fill, node in RenderTree(root_node):
            treestr = ("%s%s" % (pre, node.label)).ljust(tree_label_width)
            if hasattr(root_node, "address"):
                address = node.address
                name = ""
                loc = (
                    "Center" + str(node.position.to_tuple())
                    if show_center
                    else "Position" + str(node.position.to_tuple())
                )
            else:
                address = id(node)
                name = node.__class__.__name__.ljust(9)
                loc = (
                    "Center" + str(node.center().to_tuple())
                    if show_center
                    else "Location" + repr(node.location)
                )
            result += f"{treestr}{name}at {address:#x}, {loc}\n"
        return result

    def show_topology(
        self,
        limit_class: Literal[
            "Compound", "Edge", "Face", "Shell", "Solid", "Vertex", "Wire"
        ] = "Vertex",
        show_center: bool = None,
    ) -> str:
        """Display internal topology

        Display the internal structure of a Compound 'assembly' or Shape. Example:

        .. code::

            >>> c1.show_topology()

            c1 is the root         Compound at 0x7f4a4cafafa0, Location(...))
            ├──                    Solid    at 0x7f4a4cafafd0, Location(...))
            ├── c2 is 1st compound Compound at 0x7f4a4cafaee0, Location(...))
            │   ├──                Solid    at 0x7f4a4cafad00, Location(...))
            │   └──                Solid    at 0x7f4a11a52790, Location(...))
            └── c3 is 2nd          Compound at 0x7f4a4cafad60, Location(...))
                ├──                Solid    at 0x7f4a11a52700, Location(...))
                └──                Solid    at 0x7f4a11a58550, Location(...))

        Args:
            limit_class: type of displayed leaf node. Defaults to 'Vertex'.
            show_center (bool, optional): If None, shows the Location of Compound 'assemblies'
                and the bounding box center of Shapes. True or False forces the display.
                Defaults to None.

        Returns:
            str: tree representation of internal structure
        """

        if isinstance(self, Compound) and self.children:
            show_center = False if show_center is None else show_center
            result = Shape._show_tree(self, show_center)
        else:
            tree = Shape._build_tree(
                self.wrapped, tree=[], limit=inverse_shape_LUT[limit_class]
            )
            show_center = True if show_center is None else show_center
            result = Shape._show_tree(tree[0], show_center)
        return result

    def clean(self) -> Shape:
        """clean

        Remove internal edges

        Returns:
            Shape: Original object with extraneous internal edges removed
        """
        upgrader = ShapeUpgrade_UnifySameDomain(self.wrapped, True, True, True)
        upgrader.AllowInternalEdges(False)
        # upgrader.SetAngularTolerance(1e-5)
        try:
            upgrader.Build()
            self.wrapped = downcast(upgrader.Shape())
        except:
            warnings.warn(f"Unable to clean {self}")
        return self

    def fix(self) -> Shape:
        """fix - try to fix shape if not valid"""
        if not self.is_valid():
            shape_copy: Shape = copy.deepcopy(self, None)
            shape_copy.wrapped = fix(self.wrapped)

            return shape_copy

        return self

    @classmethod
    def cast(cls, obj: TopoDS_Shape, for_construction: bool = False) -> Shape:
        "Returns the right type of wrapper, given a OCCT object"

        new_shape = None

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

        shape_type = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        new_shape = constructor__lut[shape_type](downcast(obj))
        new_shape.for_construction = for_construction

        return new_shape

    def export_stl(
        self,
        file_name: str,
        tolerance: float = 1e-3,
        angular_tolerance: float = 0.1,
        ascii_format: bool = False,
    ) -> bool:
        """Export STL

        Exports a shape to a specified STL file.

        Args:
            file_name (str): The path and file name to write the STL output to.
            tolerance (float, optional): A linear deflection setting which limits the distance
                between a curve and its tessellation. Setting this value too low will result in
                large meshes that can consume computing resources. Setting the value too high can
                result in meshes with a level of detail that is too low. The default is a good
                starting point for a range of cases. Defaults to 1e-3.
            angular_tolerance (float, optional): Angular deflection setting which limits the angle
                between subsequent segments in a polyline. Defaults to 0.1.
            ascii_format (bool, optional): Export the file as ASCII (True) or binary (False)
                STL format. Defaults to False (binary).

        Returns:
            bool: Success
        """
        mesh = BRepMesh_IncrementalMesh(
            self.wrapped, tolerance, True, angular_tolerance
        )
        mesh.Perform()

        writer = StlAPI_Writer()

        if ascii_format:
            writer.ASCIIMode = True
        else:
            writer.ASCIIMode = False

        return writer.Write(self.wrapped, file_name)

    def export_3mf(
        self, file_name: str, tolerance: float, angular_tolerance: float, unit: Unit
    ):
        """export_3mf

        Exports a shape to a specified 3MF file.

        Args:
            file_name (str): name of 3mf file
            tolerance (float): linear tolerance for tesselation
            angular_tolerance (float): angular tolerance for tesselation
            unit (Unit): model unit
        """
        tmfw = ThreeMF(self, tolerance, angular_tolerance, unit)
        with open(file_name, "wb") as three_mf_file:
            tmfw.write_3mf(three_mf_file)

    def export_step(self, file_name: str, **kwargs) -> IFSelect_ReturnStatus:
        """Export this shape to a STEP file.

        kwargs is used to provide optional keyword arguments to configure the exporter.

        Args:
            file_name (str): Path and filename for writing.
            kwargs: used to provide optional keyword arguments to configure the exporter.

        Returns:
            IFSelect_ReturnStatus: OCCT return status
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

    def export_brep(self, file: Union[str, BytesIO]) -> bool:
        """Export this shape to a BREP file

        Args:
            file: Union[str, BytesIO]:

        Returns:

        """

        return_value = BRepTools.Write_s(self.wrapped, file)

        return True if return_value is None else return_value

    def export_svg(
        self,
        file_name: str,
        viewport_origin: VectorLike,
        viewport_up: VectorLike = (0, 0, 1),
        look_at: VectorLike = None,
        svg_opts: dict = None,
    ):
        """Export shape to SVG file

        Export self to an SVG file with the provided options

        Args:
            file_name (str): file name
            svg_opts (dict, optional): options dictionary. Defaults to None.

        SVG Options - e.g. svg_opts = {"pixel_scale":50}:

        Other Parameters:
            width (int): Viewport width in pixels. Defaults to 240.
            height (int): Viewport width in pixels. Defaults to 240.
            pixel_scale (float): Pixels per CAD unit.
                Defaults to None (calculated based on width & height).
            units (str): SVG document units. Defaults to "mm".
            margin_left (int): Defaults to 20.
            margin_top (int): Defaults to 20.
            show_axes (bool): Display an axis indicator. Defaults to True.
            axes_scale (float): Length of axis indicator in global units. Defaults to 1.0.
            stroke_width (float): Width of visible edges.
                Defaults to None (calculated based on unit_scale).
            stroke_color (tuple[int]): Visible stroke color. Defaults to RGB(0, 0, 0).
            hidden_color (tuple[int]): Hidden stroke color. Defaults to RBG(160, 160, 160).
            show_hidden (bool): Display hidden lines. Defaults to True.

        """
        svg = SVG.get_svg(self, viewport_origin, viewport_up, look_at, svg_opts)
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(svg)

    def export_dxf(
        self,
        fname: str,
        approx_option: ApproxOption = ApproxOption.NONE,
        tolerance: float = 1e-3,
        unit: Unit = Unit.MILLIMETER,
    ):
        """export_dxf

        Export shape to DXF. Works with 2D sections.

        Args:
            fname (str): output filename.
            approx (ApproxOption, optional): Approximation strategy. NONE means no approximation is
                applied. SPLINE results in all splines being approximated as cubic splines.
                ARC results in all curves being approximated as arcs and straight segments.
                Defaults to Approximation.NONE.
            tolerance (float, optional): Approximation tolerance. Defaults to 1e-3.
        """
        dxf = ezdxf.new()
        msp = dxf.modelspace()
        if unit == Unit.MILLIMETER:
            dxf.units = ezdxf.units.MM
        elif unit == Unit.CENTIMETER:
            dxf.units = ezdxf.units.CM
        elif unit == Unit.INCH:
            dxf.units = ezdxf.units.IN
        elif unit == Unit.FOOT:
            dxf.units = ezdxf.units.FT
        else:
            raise ValueError("unit not supported")

        plane = Plane(self.location)

        if approx_option == ApproxOption.SPLINE:
            edges = [
                e.to_splines() if e.geom_type() == "BSPLINE" else e
                for e in self.edges()
            ]

        elif approx_option == ApproxOption.ARC:
            edges = []

            # this is needed to handle free wires
            for wire in self.wires():
                edges.extend(Face.make_from_wires(wire).to_arcs(tolerance).edges())

        else:
            edges = self.edges()

        dxf_converters = {
            "LINE": DXF._dxf_line,
            "CIRCLE": DXF._dxf_circle,
            "ELLIPSE": DXF._dxf_ellipse,
            "BSPLINE": DXF._dxf_spline,
        }

        for edge in edges:
            conv = dxf_converters.get(edge.geom_type(), DXF._dxf_spline)
            conv(edge, msp, plane)

        dxf.saveas(fname)

    def geom_type(self) -> Geoms:
        """Gets the underlying geometry type.

        Implementations can return any values desired, but the values the user
        uses in type filters should correspond to these.

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

        topo_abs: Any = geom_LUT[shapetype(self.wrapped)]

        if isinstance(topo_abs, str):
            return_value = topo_abs
        elif topo_abs is BRepAdaptor_Curve:
            return_value = geom_LUT_EDGE[topo_abs(self.wrapped).GetType()]
        else:
            return_value = geom_LUT_FACE[topo_abs(self.wrapped).GetType()]

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

    def __eq__(self, other) -> bool:
        """Are shapes same?"""
        return self.is_same(other) if isinstance(other, Shape) else False

    def is_valid(self) -> bool:
        """Returns True if no defect is detected on the shape S or any of its
        subshapes. See the OCCT docs on BRepCheck_Analyzer::IsValid for a full
        description of what is checked.

        Args:

        Returns:

        """
        return BRepCheck_Analyzer(self.wrapped).IsValid()

    def bounding_box(self, tolerance: float = None) -> BoundBox:
        """Create a bounding box for this Shape.

        Args:
            tolerance (float, optional): Defaults to None.

        Returns:
            BoundBox: A box sized to contain this Shape
        """
        return BoundBox._from_topo_ds(self.wrapped, tolerance=tolerance)

    def mirror(self, mirror_plane: Plane = None) -> Shape:
        """
        Applies a mirror transform to this Shape. Does not duplicate objects
        about the plane.

        Args:
          mirror_plane (Plane): The plane to mirror about. Defaults to Plane.XY
        Returns:
          The mirrored shape
        """
        if not mirror_plane:
            mirror_plane = Plane.XY

        transformation = gp_Trsf()
        transformation.SetMirror(
            gp_Ax2(mirror_plane.origin.to_pnt(), mirror_plane.z_dir.to_dir())
        )

        return self._apply_transform(transformation)

    @staticmethod
    def combined_center(
        objects: Iterable[Shape], center_of: CenterOf = CenterOf.MASS
    ) -> Vector:
        """combined center

        Calculates the center of a multiple objects.

        Args:
            objects (Iterable[Shape]): list of objects
            center_of (CenterOf, optional): centering option. Defaults to CenterOf.MASS.

        Raises:
            ValueError: CenterOf.GEOMETRY not implemented

        Returns:
            Vector: center of multiple objects
        """
        if center_of == CenterOf.MASS:
            total_mass = sum(Shape.compute_mass(o) for o in objects)
            weighted_centers = [
                o.center(CenterOf.MASS).multiply(Shape.compute_mass(o)) for o in objects
            ]

            sum_wc = weighted_centers[0]
            for weighted_center in weighted_centers[1:]:
                sum_wc = sum_wc.add(weighted_center)
            middle = Vector(sum_wc.multiply(1.0 / total_mass))
        elif center_of == CenterOf.BOUNDING_BOX:
            total_mass = len(objects)

            weighted_centers = []
            for obj in objects:
                weighted_centers.append(obj.bounding_box().center())

            sum_wc = weighted_centers[0]
            for weighted_center in weighted_centers[1:]:
                sum_wc = sum_wc.add(weighted_center)

            middle = Vector(sum_wc.multiply(1.0 / total_mass))
        else:
            raise ValueError("CenterOf.GEOMETRY not implemented")

        return middle

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

        if not calc_function:
            raise NotImplementedError

        calc_function(obj.wrapped, properties)
        return properties.Mass()

    def shape_type(self) -> Shapes:
        """Return the shape type string for this class"""
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

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this Shape"""
        return ShapeList([Vertex(downcast(i)) for i in self._entities(Vertex.__name__)])

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this Shape"""
        return ShapeList(
            [
                Edge(i)
                for i in self._entities(Edge.__name__)
                if not BRep_Tool.Degenerated_s(TopoDS.Edge_s(i))
            ]
        )

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this Shape"""
        return ShapeList([Compound(i) for i in self._entities(Compound.__name__)])

    def wires(self) -> ShapeList[Wire]:
        """wires - all the wires in this Shape"""

        return ShapeList([Wire(i) for i in self._entities(Wire.__name__)])

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this Shape"""
        return ShapeList([Face(i) for i in self._entities(Face.__name__)])

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this Shape"""
        return ShapeList([Shell(i) for i in self._entities(Shell.__name__)])

    def solids(self) -> ShapeList[Solid]:
        """solids - all the solids in this Shape"""
        return ShapeList([Solid(i) for i in self._entities(Solid.__name__)])

    @property
    def area(self) -> float:
        """area -the surface area of all faces in this Shape"""
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(self.wrapped, properties)

        return properties.Mass()

    @property
    def volume(self) -> float:
        """volume - the volume of this Shape"""
        # when density == 1, mass == volume
        return Shape.compute_mass(self)

    def _apply_transform(self, transformation: gp_Trsf) -> Shape:
        """Private Apply Transform

        Apply the provided transformation matrix to a copy of Shape

        Args:
            transformation (gp_Trsf): transformation matrix

        Returns:
            Shape: copy of transformed Shape
        """
        shape_copy: Shape = copy.deepcopy(self, None)
        transformed_shape = BRepBuilderAPI_Transform(
            shape_copy.wrapped, transformation, True
        ).Shape()
        shape_copy.wrapped = downcast(transformed_shape)
        return shape_copy

    def rotate(self, axis: Axis, angle: float) -> Shape:
        """rotate a copy

        Rotates a shape around an axis.

        Args:
            axis (Axis): rotation Axis
            angle (float): angle to rotate, in degrees

        Returns:
            a copy of the shape, rotated
        """
        transformation = gp_Trsf()
        transformation.SetRotation(axis.wrapped, angle * DEG2RAD)

        return self._apply_transform(transformation)

    def translate(self, vector: VectorLike) -> Shape:
        """Translates this shape through a transformation.

        Args:
          vector: VectorLike:

        Returns:

        """

        transformation = gp_Trsf()
        transformation.SetTranslation(Vector(vector).wrapped)

        return self._apply_transform(transformation)

    def scale(self, factor: float) -> Shape:
        """Scales this shape through a transformation.

        Args:
          factor: float:

        Returns:

        """

        transformation = gp_Trsf()
        transformation.SetScale(gp_Pnt(), factor)

        return self._apply_transform(transformation)

    def __deepcopy__(self, memo) -> Shape:
        """Return deepcopy of self"""
        # The wrapped object is a OCCT TopoDS_Shape which can't be pickled or copied
        # with the standard python copy/deepcopy, so create a deepcopy 'memo' with this
        # value already copied which causes deepcopy to skip it.
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        memo[id(self.wrapped)] = downcast(BRepBuilderAPI_Copy(self.wrapped).Shape())
        for key, value in self.__dict__.items():
            setattr(result, key, copy.deepcopy(value, memo))
        return result

    def __copy__(self) -> Shape:
        """Return shallow copy or reference of self

        Create an copy of this Shape that shares the underlying TopoDS_TShape.

        Used when there is a need for many objects with the same CAD structure but at
        different Locations, etc. - for examples fasteners in a larger assembly. By
        sharing the TopoDS_TShape, the memory size of such assemblies can be greatly reduced.

        Changes to the CAD structure of the base object will be reflected in all instances.
        """
        reference = copy.deepcopy(self)
        reference.wrapped.TShape(self.wrapped.TShape())
        return reference

    def copy(self) -> Shape:
        """Here for backwards compatibility with cq-editor"""
        warnings.warn(
            "copy() will be deprecated - use copy.copy() or copy.deepcopy() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return copy.deepcopy(self, None)

    def transform_shape(self, t_matrix: Matrix) -> Shape:
        """Apply affine transform without changing type

        Transforms a copy of this Shape by the provided 3D affine transformation matrix.
        Note that not all transformation are supported - primarily designed for translation
        and rotation.  See :transform_geometry: for more comprehensive transformations.

        Args:
            t_matrix (Matrix): affine transformation matrix

        Returns:
            Shape: copy of transformed shape with all objects keeping their type
        """
        transformed = Shape.cast(
            BRepBuilderAPI_Transform(self.wrapped, t_matrix.wrapped.Trsf()).Shape()
        )
        new_shape = copy.deepcopy(self, None)
        new_shape.wrapped = transformed.wrapped

        return new_shape

    def transform_geometry(self, t_matrix: Matrix) -> Shape:
        """Apply affine transform

        WARNING: transform_geometry will sometimes convert lines and circles to
        splines, but it also has the ability to handle skew and stretching
        transformations.

        If your transformation is only translation and rotation, it is safer to
        use :py:meth:`transform_shape`, which doesn't change the underlying type
        of the geometry, but cannot handle skew transformations.

        Args:
            t_matrix (Matrix): affine transformation matrix

        Returns:
            Shape: a copy of the object, but with geometry transformed
        """
        transformed = Shape.cast(
            BRepBuilderAPI_GTransform(self.wrapped, t_matrix.wrapped, True).Shape()
        )
        new_shape = copy.deepcopy(self, None)
        new_shape.wrapped = transformed.wrapped

        return new_shape

    def locate(self, loc: Location) -> Shape:
        """Apply a location in absolute sense to self

        Args:
          loc: Location:

        Returns:

        """

        self.wrapped.Location(loc.wrapped)

        return self

    def located(self, loc: Location) -> Shape:
        """located

        Apply a location in absolute sense to a copy of self

        Args:
            loc (Location): new absolute location

        Returns:
            Shape: copy of Shape at location
        """
        shape_copy: Shape = copy.deepcopy(self, None)
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

    def moved(self, loc: Location) -> Shape:
        """moved

        Apply a location in relative sense (i.e. update current location) to a copy of self

        Args:
            loc (Location): new location relative to current location

        Returns:
            Shape: copy of Shape moved to relative location
        """
        shape_copy: Shape = copy.deepcopy(self, None)
        shape_copy.wrapped = downcast(shape_copy.wrapped.Moved(loc.wrapped))
        return shape_copy

    def distance_to_with_closest_points(
        self, other: Union[Shape, VectorLike]
    ) -> tuple[float, Vector, Vector]:
        """Minimal distance between two shapes and the points on each shape"""
        other = other if isinstance(other, Shape) else Vertex(other)
        dist_calc = BRepExtrema_DistShapeShape()
        dist_calc.LoadS1(self.wrapped)
        dist_calc.LoadS2(other.wrapped)
        dist_calc.Perform()
        return (
            dist_calc.Value(),
            Vector(dist_calc.PointOnShape1(1)),
            Vector(dist_calc.PointOnShape2(1)),
        )

    def distance_to(self, other: Union[Shape, VectorLike]) -> float:
        """Minimal distance between two shapes"""
        return self.distance_to_with_closest_points(other)[0]

    def closest_points(self, other: Union[Shape, VectorLike]) -> tuple[Vector, Vector]:
        """Points on two shapes where the distance between them is minimal"""
        return tuple(self.distance_to_with_closest_points(other)[1:])

    def __hash__(self) -> int:
        """Return has code"""
        return self.hash_code()

    def _bool_op(
        self,
        args: Iterable[Shape],
        tools: Iterable[Shape],
        operation: Union[BRepAlgoAPI_BooleanOperation, BRepAlgoAPI_Splitter],
    ) -> Shape:
        """Generic boolean operation

        Args:
          args: Iterable[Shape]:
          tools: Iterable[Shape]:
          operation: Union[BRepAlgoAPI_BooleanOperation:
          BRepAlgoAPI_Splitter]:

        Returns:

        """

        arg = TopTools_ListOfShape()
        for obj in args:
            arg.Append(obj.wrapped)

        tool = TopTools_ListOfShape()
        for obj in tools:
            tool.Append(obj.wrapped)

        operation.SetArguments(arg)
        operation.SetTools(tool)

        operation.SetRunParallel(True)
        operation.Build()

        return Shape.cast(operation.Shape())

    def cut(self, *to_cut: Shape) -> Shape:
        """Remove the positional arguments from this Shape.

        Args:
          *to_cut: Shape:

        Returns:

        """

        cut_op = BRepAlgoAPI_Cut()

        return self._bool_op((self,), to_cut, cut_op)

    def fuse(self, *to_fuse: Shape, glue: bool = False, tol: float = None) -> Shape:
        """fuse

        Fuse a sequence of shapes into a single shape.

        Args:
            to_fuse (sequence Shape): shapes to fuse
            glue (bool, optional): performance improvement for some shapes. Defaults to False.
            tol (float, optional): tolerarance. Defaults to None.

        Returns:
            Shape: fused shape
        """

        fuse_op = BRepAlgoAPI_Fuse()
        if glue:
            fuse_op.SetGlue(BOPAlgo_GlueEnum.BOPAlgo_GlueShift)
        if tol:
            fuse_op.SetFuzzyValue(tol)

        return_value = self._bool_op((self,), to_fuse, fuse_op)

        return return_value

    def intersect(self, *to_intersect: Shape) -> Shape:
        """Intersection of the positional arguments and this Shape.

        Args:
            toIntersect (sequence of Shape): shape to intersect

        Returns:

        """

        intersect_op = BRepAlgoAPI_Common()

        return self._bool_op((self,), to_intersect, intersect_op)

    def faces_intersected_by_axis(
        self,
        axis: Axis,
        tol: float = 1e-4,
    ) -> ShapeList[Face]:
        """Line Intersection

        Computes the intersections between the provided axis and the faces of this Shape

        Args:
            axis (Axis): Axis on which the intersection line rests
            tol (float, optional): Intersection tolerance. Defaults to 1e-4.

        Returns:
            list[Face]: A list of intersected faces sorted by distance from axis.position
        """
        line = gce_MakeLin(axis.wrapped).Value()
        shape = self.wrapped

        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(shape, line, tol)

        faces_dist = []  # using a list instead of a dictionary to be able to sort it
        while intersect_maker.More():
            inter_pt = intersect_maker.Pnt()

            distance = axis.position.to_pnt().SquareDistance(inter_pt)

            faces_dist.append(
                (intersect_maker.Face(), abs(distance))
            )  # will sort all intersected faces by distance whatever the direction is

            intersect_maker.Next()

        faces_dist.sort(key=lambda x: x[1])
        faces = [face[0] for face in faces_dist]

        return ShapeList([Face(face) for face in faces])

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

        for other_shape in others:
            dist_calc.LoadS2(other_shape.wrapped)
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
        """General triangulated approximation"""
        self.mesh(tolerance, angular_tolerance)

        vertices: list[Vector] = []
        triangles: list[Tuple[int, int, int]] = []
        offset = 0

        for face in self.faces():
            loc = TopLoc_Location()
            poly = BRep_Tool.Triangulation_s(face.wrapped, loc)
            trsf = loc.Transformation()
            reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED

            # add vertices
            vertices += [
                Vector(v.X(), v.Y(), v.Z())
                for v in (
                    poly.Node(i).Transformed(trsf) for i in range(1, poly.NbNodes() + 1)
                )
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

    def to_splines(
        self, degree: int = 3, tolerance: float = 1e-3, nurbs: bool = False
    ) -> T:
        """to_splines

        Approximate shape with b-splines of the specified degree.

        Args:
            degree (int, optional): Maximum degree. Defaults to 3.
            tolerance (float, optional): Approximation tolerance. Defaults to 1e-3.
            nurbs (bool, optional): Use rational splines. Defaults to False.

        Returns:
            T: _description_
        """
        params = ShapeCustom_RestrictionParameters()

        result = ShapeCustom.BSplineRestriction_s(
            self.wrapped,
            tolerance,  # 3D tolerance
            tolerance,  # 2D tolerance
            degree,
            1,  # dummy value, degree is leading
            ga.GeomAbs_C0,
            ga.GeomAbs_C0,
            True,  # set degree to be leading
            not nurbs,
            params,
        )

        return self.__class__(result)

    def to_vtk_poly_data(
        self,
        tolerance: float = None,
        angular_tolerance: float = None,
        normals: bool = False,
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
        shape_mesher = IVtkOCC_ShapeMesher()

        drawer = vtk_shape.Attributes()
        drawer.SetUIsoAspect(Prs3d_IsoAspect(Quantity_Color(), Aspect_TOL_SOLID, 1, 0))
        drawer.SetVIsoAspect(Prs3d_IsoAspect(Quantity_Color(), Aspect_TOL_SOLID, 1, 0))

        if tolerance:
            drawer.SetDeviationCoefficient(tolerance)

        if angular_tolerance:
            drawer.SetDeviationAngle(angular_tolerance)

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

    def to_arcs(self, tolerance: float = 1e-3) -> Face:
        """to_arcs

        Approximate planar face with arcs and straight line segments.

        Args:
            tolerance (float, optional): Approximation tolerance. Defaults to 1e-3.

        Returns:
            Face: approximated face
        """
        return self.__class__(BRepAlgo.ConvertFace_s(self.wrapped, tolerance))

    def _repr_javascript_(self):
        """Jupyter 3D representation support"""

        from .jupyter_tools import display

        return display(self)._repr_javascript_()

    def transformed(
        self, rotate: VectorLike = (0, 0, 0), offset: VectorLike = (0, 0, 0)
    ) -> Shape:
        """Transform Shape

        Rotate and translate the Shape by the three angles (in degrees) and offset.

        Args:
            rotate (VectorLike, optional): 3-tuple of angles to rotate, in degrees.
                Defaults to (0, 0, 0).
            offset (VectorLike, optional): 3-tuple to offset. Defaults to (0, 0, 0).

        Returns:
            Shape: transformed object

        """
        # Convert to a Vector of radians
        rotate_vector = Vector(rotate).multiply(DEG2RAD)
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

    def find_intersection(self, axis: Axis) -> list[tuple[Vector, Vector]]:
        """Find point and normal at intersection

        Return both the point(s) and normal(s) of the intersection of the axis and the shape

        Args:
            axis (Axis): axis defining the intersection line

        Returns:
            list[tuple[Vector, Vector]]: Point and normal of intersection
        """
        oc_shape = self.wrapped

        intersection_line = gce_MakeLin(axis.wrapped).Value()
        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(oc_shape, intersection_line, 0.0001)

        intersections = []
        while intersect_maker.More():
            inter_pt = intersect_maker.Pnt()
            distance = axis.position.to_pnt().Distance(inter_pt)
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
        for pnt, normal in zip(intersecting_points, intersecting_normals):
            result.append((pnt, normal))

        return result

    def project_faces(
        self,
        faces: Union[list[Face], Compound],
        path: Union[Wire, Edge],
        start: float = 0,
    ) -> Compound:
        """Projected 3D text following the given path on Shape

        Create 3D text using projection by positioning each face of
        the planar text normal to the shape along the path and projecting
        onto the surface. If depth is not zero, the resulting face is
        thickened to the provided depth.

        Note that projection may result in text distortion depending on
        the shape at a position along the path.

        .. image:: projectText.png

        Args:
            faces (Union[list[Face], Compound]): faces to project
            path: Path on the Shape to follow
            start: Relative location on path to start the text. Defaults to 0.

        Returns:
            The projected faces either as 2D or 3D

        """
        path_length = path.length
        # The derived classes of Shape implement center
        shape_center = self.center()  # pylint: disable=no-member

        if isinstance(faces, Compound):
            faces = faces.faces()

        logger.debug("projecting %d face(s)", len(faces))

        # Position each text face normal to the surface along the path and project to the surface
        projected_faces = []
        for face in faces:
            bbox = face.bounding_box()
            face_center_x = (bbox.min.X + bbox.max.X) / 2
            relative_position_on_wire = start + face_center_x / path_length
            path_position = path.position_at(relative_position_on_wire)
            path_tangent = path.tangent_at(relative_position_on_wire)
            (surface_point, surface_normal) = self.find_intersection(
                Axis(path_position, path_position - shape_center)
            )[0]
            surface_normal_plane = Plane(
                origin=surface_point, x_dir=path_tangent, z_dir=surface_normal
            )
            projection_face: Face = face.translate(
                (-face_center_x, 0, 0)
            ).transform_shape(surface_normal_plane.reverse_transform)
            logger.debug("projecting face at %0.2f", relative_position_on_wire)
            projected_faces.append(
                projection_face.project_to_shape(self, surface_normal * -1)[0]
            )

        logger.debug("finished projecting '%d' faces", len(faces))

        return Compound.make_compound(projected_faces)


# This TypeVar allows IDEs to see the type of objects within the ShapeList
T = TypeVar("T", bound=Union[Shape, Vector])


class ShapeList(list[T]):
    """Subclass of list with custom filter and sort methods appropriate to CAD"""

    @property
    def first(self) -> T:
        """First element in the ShapeList"""
        return self[0]

    @property
    def last(self) -> T:
        """Last element in the ShapeList"""
        return self[-1]

    def filter_by(
        self,
        filter_by: Union[Axis, GeomType],
        reverse: bool = False,
        tolerance: float = 1e-5,
    ) -> ShapeList[T]:
        """filter by Axis or GeomType

        Either:
        - filter objects of type planar Face or linear Edge by their normal or tangent
        (respectively) and sort the results by the given axis, or
        - filter the objects by the provided type. Note that not all types apply to all
        objects.

        Args:
            filter_by (Union[Axis,GeomType]): axis or geom type to filter and possibly sort by
            reverse (bool, optional): invert the geom type filter. Defaults to False.
            tolerance (float, optional): maximum deviation from axis. Defaults to 1e-5.

        Raises:
            ValueError: Invalid filter_by type

        Returns:
            ShapeList: filtered list of objects
        """
        if isinstance(filter_by, Axis):
            planar_faces = filter(
                lambda o: isinstance(o, Face) and o.geom_type() == "PLANE", self
            )
            linear_edges = filter(
                lambda o: isinstance(o, Edge) and o.geom_type() == "LINE", self
            )

            result = list(
                filter(
                    lambda o: filter_by.is_parallel(
                        Axis(o.center(), o.normal_at(None)), tolerance
                    ),
                    planar_faces,
                )
            )
            result.extend(
                list(
                    filter(
                        lambda o: filter_by.is_parallel(
                            Axis(o.position_at(0), o.tangent_at(0)), tolerance
                        ),
                        linear_edges,
                    )
                )
            )
            return_value = ShapeList(result).sort_by(filter_by)

        elif isinstance(filter_by, GeomType):
            if reverse:
                return_value = ShapeList(
                    filter(lambda o: o.geom_type() != filter_by.name, self)
                )
            else:
                return_value = ShapeList(
                    filter(lambda o: o.geom_type() == filter_by.name, self)
                )
        else:
            raise ValueError(f"Unable to filter_by type {type(filter_by)}")

        return return_value

    def filter_by_position(
        self,
        axis: Axis,
        minimum: float,
        maximum: float,
        inclusive: tuple[bool, bool] = (True, True),
    ) -> ShapeList[T]:
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

    def group_by(
        self, group_by: Union[Axis, SortBy] = Axis.Z, reverse=False, tol_digits=6
    ) -> list[ShapeList[T]]:
        """group by

        Group objects by provided criteria and then sort the groups according to the criteria.
        Note that not all group_by criteria apply to all objects.

        Args:
            group_by (SortBy, optional): group and sort criteria. Defaults to Axis.Z.
            reverse (bool, optional): flip order of sort. Defaults to False.
            tol_digits (int, optional): Tolerance for building the group keys by
                round(key, tol_digits)

        Returns:
            List[ShapeList]: sorted list of ShapeLists
        """
        groups = {}
        for obj in self:
            if isinstance(group_by, Axis):
                key = group_by.to_plane().to_local_coords(obj).center().Z

            elif isinstance(group_by, SortBy):
                if group_by == SortBy.LENGTH:
                    key = obj.length

                elif group_by == SortBy.RADIUS:
                    key = obj.radius

                elif group_by == SortBy.DISTANCE:
                    key = obj.center().length

                elif group_by == SortBy.AREA:
                    key = obj.area

                elif group_by == SortBy.VOLUME:
                    key = obj.volume

            else:
                raise ValueError(f"Group by {type(group_by)} unsupported")

            key = round(key, tol_digits)

            if groups.get(key) is None:
                groups[key] = [obj]
            else:
                groups[key].append(obj)

        return [
            ShapeList(el[1])
            for el in sorted(groups.items(), key=lambda o: o[0], reverse=reverse)
        ]

    def sort_by(
        self, sort_by: Union[Axis, SortBy] = Axis.Z, reverse: bool = False
    ) -> ShapeList[T]:
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
                    key=lambda obj: obj.length,
                    reverse=reverse,
                )
            elif sort_by == SortBy.RADIUS:
                objects = sorted(
                    self,
                    key=lambda obj: obj.radius,
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
                    key=lambda obj: obj.area,
                    reverse=reverse,
                )
            elif sort_by == SortBy.VOLUME:
                objects = sorted(
                    self,
                    key=lambda obj: obj.volume,
                    reverse=reverse,
                )

        return ShapeList(objects)

    def sort_by_distance(
        self, other: Union[Shape, VectorLike], reverse: bool = False
    ) -> ShapeList[T]:
        """Sort by distance

        Sort by minimal distance between objects and other

        Args:
            other (Union[Shape,VectorLike]): reference object
            reverse (bool, optional): flip order of sort. Defaults to False.

        Returns:
            ShapeList: Sorted shapes
        """
        other = other if isinstance(other, Shape) else Vertex(other)
        distances = {other.distance_to(obj): obj for obj in self}
        return ShapeList(
            distances[key] for key in sorted(distances.keys(), reverse=reverse)
        )

    def __gt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort operator"""
        return self.sort_by(sort_by)

    def __lt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Reverse sort operator"""
        return self.sort_by(sort_by, reverse=True)

    def __rshift__(self, group_by: Union[Axis, SortBy] = Axis.Z):
        """Group and select largest group operator"""
        return self.group_by(group_by)[-1]

    def __lshift__(self, group_by: Union[Axis, SortBy] = Axis.Z):
        """Group and select smallest group operator"""
        return self.group_by(group_by)[0]

    def __or__(self, filter_by: Union[Axis, GeomType] = Axis.Z):
        """Filter by axis or geomtype operator"""
        return self.filter_by(filter_by)

    def __add__(self, other: ShapeList):
        """Combine two ShapeLists together"""
        return ShapeList(list(self) + list(other))

    def __getitem__(self, key):
        """Return slices of ShapeList as ShapeList"""
        if isinstance(key, slice):
            return_value = ShapeList(list(self).__getitem__(key))
        else:
            return_value = list(self).__getitem__(key)
        return return_value


class Compound(Shape, Mixin3D):
    """Compound

    A collection of Shapes

    """

    def __repr__(self):
        """Return Compound info as string"""
        if hasattr(self, "label") and hasattr(self, "children"):
            result = (
                f"Compound at {id(self):#x}, label({self.label}), "
                + f"#children({len(self.children)})"
            )
        else:
            result = f"Compound at {id(self):#x}"
        return result

    @staticmethod
    def _make_compound(occt_shapes: Iterable[TopoDS_Shape]) -> TopoDS_Compound:
        """Create an OCCT TopoDS_Compound

        Create an OCCT TopoDS_Compound object from an iterable of TopoDS_Shape objects

        Args:
            occt_shapes (Iterable[TopoDS_Shape]): OCCT shapes

        Returns:
            TopoDS_Compound: OCCT compound
        """
        comp = TopoDS_Compound()
        comp_builder = TopoDS_Builder()
        comp_builder.MakeCompound(comp)

        for shape in occt_shapes:
            comp_builder.Add(comp, shape)

        return comp

    def center(self, center_of: CenterOf = CenterOf.MASS) -> Vector:
        """Return center of object

        Find center of object

        Args:
            center_of (CenterOf, optional): center option. Defaults to CenterOf.MASS.

        Raises:
            ValueError: Center of GEOMETRY is not supported for this object
            NotImplementedError: Unable to calculate center of mass of this object

        Returns:
            Vector: center
        """
        if center_of == CenterOf.GEOMETRY:
            raise ValueError("Center of GEOMETRY is not supported for this object")
        if center_of == CenterOf.MASS:
            properties = GProp_GProps()
            calc_function = shape_properties_LUT[shapetype(self.wrapped)]
            if calc_function:
                calc_function(self.wrapped, properties)
                middle = Vector(properties.CentreOfMass())
            else:
                raise NotImplementedError
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    @classmethod
    def make_compound(cls, shapes: Iterable[Shape]) -> Compound:
        """Create a compound out of a list of shapes
        Args:
          shapes: Iterable[Shape]:
        Returns:
        """
        return cls(cls._make_compound((s.wrapped for s in shapes)))

    def _remove(self, shape: Shape) -> Compound:
        """Return self with the specified shape removed.

        Args:
          shape: Shape:
        """
        comp_builder = TopoDS_Builder()
        comp_builder.Remove(self.wrapped, shape.wrapped)
        return self

    def _post_detach(self, parent: Compound):
        """Method call after detaching from `parent`."""
        logger.debug("Removing parent of %s (%s)", self.label, parent.label)
        if parent.children:
            parent.wrapped = Compound._make_compound(
                [c.wrapped for c in parent.children]
            )
        else:
            parent.wrapped = None

    def _pre_attach(self, parent: Compound):
        """Method call before attaching to `parent`."""
        if not isinstance(parent, Compound):
            raise ValueError("`parent` must be of type Compound")

    def _post_attach(self, parent: Compound):
        """Method call after attaching to `parent`."""
        logger.debug("Updated parent of %s to %s", self.label, parent.label)
        parent.wrapped = Compound._make_compound([c.wrapped for c in parent.children])

    def _post_detach_children(self, children):
        """Method call before detaching `children`."""
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Removing children %s from %s", kids, self.label)
            self.wrapped = Compound._make_compound([c.wrapped for c in self.children])
        # else:
        #     logger.debug("Removing no children from %s", self.label)

    def _pre_attach_children(self, children):
        """Method call before attaching `children`."""
        if not all([isinstance(child, Shape) for child in children]):
            raise ValueError("Each child must be of type Shape")

    def _post_attach_children(self, children: Iterable[Shape]):
        """Method call after attaching `children`."""
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Adding children %s to %s", kids, self.label)
            self.wrapped = Compound._make_compound([c.wrapped for c in self.children])
        # else:
        #     logger.debug("Adding no children to %s", self.label)

    def do_children_intersect(
        self, include_parent: bool = False, tolerance: float = 1e-5
    ) -> tuple[bool, tuple[Shape, Shape], float]:
        """Do Children Intersect

        Determine if any of the child objects within a Compound/assembly intersect by
        intersecting each of the shapes with each other and checking for
        a common volume.

        Args:
            include_parent (bool, optional): check parent for intersections. Defaults to False.
            tolerance (float, optional): maximum allowable volume difference. Defaults to 1e-5.

        Returns:
            bool: do the object intersect
        """
        children: list[Shape] = list(PreOrderIter(self))
        if not include_parent:
            children.pop(0)  # remove parent
        # children_bbox = [child.bounding_box().to_solid() for child in children]
        children_bbox = [
            Solid.from_bounding_box(child.bounding_box()) for child in children
        ]
        child_index_pairs = [
            tuple(map(int, comb))
            for comb in combinations(list(range(len(children))), 2)
        ]
        for child_index_pair in child_index_pairs:
            # First check for bounding box intersections ..
            # .. then confirm with actual object intersections which could be complex
            bbox_common_volume = (
                children_bbox[child_index_pair[0]]
                .intersect(children_bbox[child_index_pair[1]])
                .volume
            )
            if bbox_common_volume > tolerance:
                common_volume = (
                    children[child_index_pair[0]]
                    .intersect(children[child_index_pair[1]])
                    .volume
                )
                if common_volume > tolerance:
                    return (
                        True,
                        (children[child_index_pair[0]], children[child_index_pair[1]]),
                        common_volume,
                    )
        return (False, (None, None), None)

    @classmethod
    def make_text(
        cls,
        txt: str,
        font_size: float,
        font: str = "Arial",
        font_path: Optional[str] = None,
        font_style: FontStyle = FontStyle.REGULAR,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        position_on_path: float = 0.0,
        text_path: Union[Edge, Wire] = None,
    ) -> "Compound":
        """2D Text that optionally follows a path.

        The text that is created can be combined as with other sketch features by specifying
        a mode or rotated by the given angle.  In addition, edges have been previously created
        with arc or segment, the text will follow the path defined by these edges. The start
        parameter can be used to shift the text along the path to achieve precise positioning.

        Args:
            txt: text to be rendered
            font_size: size of the font in model units
            font: font name
            font_path: path to font file
            font_style: text style. Defaults to FontStyle.REGULAR.
            align (tuple[Align, Align], optional): align min, center, or max of object.
                Defaults to (Align.CENTER, Align.CENTER).
            position_on_path: the relative location on path to position the text,
                between 0.0 and 1.0. Defaults to 0.0.
            text_path: a path for the text to follows. Defaults to None - linear text.

        Returns:
            a Compound object containing multiple Faces representing the text

        Examples::

            fox = Compound.make_text(
                txt="The quick brown fox jumped over the lazy dog",
                font_size=10,
                position_on_path=0.1,
                text_path=jump_edge,
            )

        """

        def position_face(orig_face: "Face") -> "Face":
            """
            Reposition a face to the provided path

            Local coordinates are used to calculate the position of the face
            relative to the path. Global coordinates to position the face.
            """
            bbox = orig_face.bounding_box()
            face_bottom_center = Vector((bbox.min.X + bbox.max.X) / 2, 0, 0)
            relative_position_on_wire = (
                position_on_path + face_bottom_center.X / path_length
            )
            wire_tangent = text_path.tangent_at(relative_position_on_wire)
            wire_angle = Vector(1, 0, 0).get_signed_angle(wire_tangent)
            wire_position = text_path.position_at(relative_position_on_wire)

            return orig_face.translate(wire_position - face_bottom_center).rotate(
                Axis(wire_position, (0, 0, 1)),
                -wire_angle,
            )

        if sys.platform.startswith("linux"):
            os.environ["FONTCONFIG_FILE"] = "/etc/fonts/fonts.conf"
            os.environ["FONTCONFIG_PATH"] = "/etc/fonts/"

        font_kind = {
            FontStyle.REGULAR: Font_FA_Regular,
            FontStyle.BOLD: Font_FA_Bold,
            FontStyle.ITALIC: Font_FA_Italic,
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
            float(font_size),
        )
        text_flat = Compound(builder.Perform(font_i, NCollection_Utf8String(txt)))

        # Align the text from the bounding box
        bbox = text_flat.bounding_box()
        align_offset = []
        for i in range(2):
            if align[i] == Align.MIN:
                align_offset.append(-bbox.min.to_tuple()[i])
            elif align[i] == Align.CENTER:
                align_offset.append(
                    -(bbox.min.to_tuple()[i] + bbox.max.to_tuple()[i]) / 2
                )
            elif align[i] == Align.MAX:
                align_offset.append(-bbox.max.to_tuple()[i])
        text_flat = text_flat.translate(Vector(*align_offset))

        if text_path is not None:
            path_length = text_path.length
            text_flat = Compound.make_compound(
                [position_face(f) for f in text_flat.faces()]
            )

        return text_flat

    def __iter__(self) -> Iterator[Shape]:
        """
        Iterate over subshapes.

        """

        iterator = TopoDS_Iterator(self.wrapped)

        while iterator.More():
            yield Shape.cast(iterator.Value())
            iterator.Next()

    def __bool__(self) -> bool:
        """
        Check if empty.
        """

        return TopoDS_Iterator(self.wrapped).More()

    def cut(self, *to_cut: Shape) -> Compound:
        """Remove a shape from another one

        Args:
          *to_cut: Shape:

        Returns:

        """

        cut_op = BRepAlgoAPI_Cut()

        return tcast(Compound, self._bool_op(self, to_cut, cut_op))

    def fuse(self, *to_fuse: Shape, glue: bool = False, tol: float = None) -> Compound:
        """Fuse shapes together

        Args:
          *to_fuse: Shape:
          glue: bool:  (Default value = False)
          tol: float:  (Default value = None)

        Returns:

        """

        fuse_op = BRepAlgoAPI_Fuse()
        if glue:
            fuse_op.SetGlue(BOPAlgo_GlueEnum.BOPAlgo_GlueShift)
        if tol:
            fuse_op.SetFuzzyValue(tol)

        args = tuple(self) + to_fuse

        if len(args) <= 1:
            return_value: Shape = args[0]
        else:
            return_value = self._bool_op(args[:1], args[1:], fuse_op)

        # fuse_op.RefineEdges()
        # fuse_op.FuseEdges()

        return tcast(Compound, return_value)

    def intersect(self, *to_intersect: Shape) -> Compound:
        """Construct shape intersection

        Args:
          *to_intersect: Shape:

        Returns:

        """

        intersect_op = BRepAlgoAPI_Common()

        return tcast(Compound, self._bool_op(self, to_intersect, intersect_op))

    def get_type(
        self,
        obj_type: Union[Type[Edge], Type[Face], Type[Shell], Type[Solid], Type[Wire]],
    ) -> list[Union[Edge, Face, Shell, Solid, Wire]]:
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
            Face: TopAbs_ShapeEnum.TopAbs_FACE,
            Shell: TopAbs_ShapeEnum.TopAbs_SHELL,
            Solid: TopAbs_ShapeEnum.TopAbs_SOLID,
            Wire: TopAbs_ShapeEnum.TopAbs_WIRE,
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

    def close(self) -> Union[Edge, Wire]:
        """Close an Edge"""
        if not self.is_closed():
            return_value = Wire.make_wire([self]).close()
        else:
            return_value = self

        return return_value

    def to_wire(self) -> Wire:
        """Edge as Wire"""
        return Wire.make_wire([self])

    @property
    def arc_center(self) -> Vector:
        """center of an underlying circle or ellipse geometry."""

        geom_type = self.geom_type()
        geom_adaptor = self._geom_adaptor()

        if geom_type == "CIRCLE":
            return_value = Vector(geom_adaptor.Circle().Position().Location())
        elif geom_type == "ELLIPSE":
            return_value = Vector(geom_adaptor.Ellipse().Position().Location())
        else:
            raise ValueError(f"{geom_type} has no arc center")

        return return_value

    def intersections(
        self, plane: Plane, edge: Edge = None, tolerance: float = TOLERANCE
    ) -> list[Vector]:
        """intersections

        Determine the points where a 2D edge crosses itself or another 2D edge

        Args:
            plane (Plane): plane containing edge(s)
            edge (Edge): curve to compare with
            tolerance (float, optional): defines the precision of computing the intersection points.
                 Defaults to TOLERANCE.

        Returns:
            list[Vector]: list of intersection points
        """
        # This will be updated by Geom_Surface to the edge location but isn't otherwise used
        edge_location = TopLoc_Location()

        # Check if self is on the plane
        if not all([plane.contains(self.position_at(i / 7)) for i in range(8)]):
            raise ValueError("self must be a 2D edge on the given plane")

        edge_surface: Geom_Surface = Face.make_plane(plane)._geom_adaptor()

        self_2d_curve: Geom2d_Curve = BRep_Tool.CurveOnPlane_s(
            self.wrapped,
            edge_surface,
            edge_location,
            self.param_at(0),
            self.param_at(1),
        )
        if edge:
            # Check if edge is on the plane
            if not all([plane.contains(edge.position_at(i / 7)) for i in range(8)]):
                raise ValueError("edge must be a 2D edge on the given plane")

            edge_2d_curve: Geom2d_Curve = BRep_Tool.CurveOnPlane_s(
                edge.wrapped,
                edge_surface,
                edge_location,
                edge.param_at(0),
                edge.param_at(1),
            )
            intersector = Geom2dAPI_InterCurveCurve(
                self_2d_curve, edge_2d_curve, tolerance
            )
        else:
            intersector = Geom2dAPI_InterCurveCurve(self_2d_curve, tolerance)

        crosses = [
            Vector(intersector.Point(i + 1).X(), intersector.Point(i + 1).Y())
            for i in range(intersector.NbPoints())
        ]
        return crosses

    def trim(self, start: float, end: float) -> Edge:
        """trim

        Create a new edge by keeping only the section between start and end.

        Args:
            start (float): 0.0 <= start < 1.0
            end (float): 0.0 < end <= 1.0

        Raises:
            ValueError: start >= end

        Returns:
            Edge: trimmed edge
        """
        if start >= end:
            raise ValueError("start must be less than end")

        new_curve = BRep_Tool.Curve_s(
            copy.deepcopy(self).wrapped, self.param_at(0), self.param_at(1)
        )
        parm_start = self.param_at(start)
        parm_end = self.param_at(end)
        trimmed_curve = Geom_TrimmedCurve(
            new_curve,
            parm_start,
            parm_end,
        )
        new_edge = BRepBuilderAPI_MakeEdge(trimmed_curve).Edge()
        return Edge(new_edge)

    # def overlaps(self, other: Edge, tolerance: float = 1e-4) -> bool:
    #     """overlaps

    #     Check to determine if self and other overlap

    #     Args:
    #         other (Edge): edge to check against
    #         tolerance (float, optional): min distance between edges. Defaults to 1e-4.

    #     Returns:
    #         bool: edges are within tolerance of each other
    #     """
    #     analyzer = ShapeAnalysis_Edge()
    #     return analyzer.CheckOverlapping(
    #         # self.wrapped, other.wrapped, tolerance, 2*tolerance
    #         self.wrapped, other.wrapped, tolerance, domain_distance
    #     )

    @classmethod
    def make_bezier(cls, *cntl_pnts: VectorLike, weights: list[float] = None) -> Edge:
        """make_bezier

        Create a rational (with weights) or non-rational bezier curve.  The first and last
        control points represent the start and end of the curve respectively.  If weights
        are provided, there must be one provided for each control point.

        Args:
            cntl_pnts (sequence[VectorLike]): points defining the curve
            weights (list[float], optional): control point weights list. Defaults to None.

        Raises:
            ValueError: Too few control points
            ValueError: Too many control points
            ValueError: A weight is required for each control point

        Returns:
            Edge: bezier curve
        """
        if len(cntl_pnts) < 2:
            raise ValueError(
                "At least two control points must be provided (start, end)"
            )
        if len(cntl_pnts) > 25:
            raise ValueError("The maximum number of control points is 25")
        if weights:
            if len(cntl_pnts) != len(weights):
                raise ValueError("A weight must be provided for each control point")

        cntl_gp_pnts = [Vector(cntl_pnt).to_pnt() for cntl_pnt in cntl_pnts]

        # The poles are stored in an OCCT Array object
        poles = TColgp_Array1OfPnt(1, len(cntl_gp_pnts))
        for i, cntl_gp_pnt in enumerate(cntl_gp_pnts):
            poles.SetValue(i + 1, cntl_gp_pnt)

        if weights:
            pole_weights = TColStd_Array1OfReal(1, len(weights))
            for i, weight in enumerate(weights):
                pole_weights.SetValue(i + 1, float(weight))
            bezier_curve = Geom_BezierCurve(poles, pole_weights)
        else:
            bezier_curve = Geom_BezierCurve(poles)

        return cls(BRepBuilderAPI_MakeEdge(bezier_curve).Edge())

    @classmethod
    def make_circle(
        cls,
        radius: float,
        plane: Plane = Plane.XY,
        start_angle: float = 360.0,
        end_angle: float = 360,
        angular_direction: AngularDirection = AngularDirection.COUNTER_CLOCKWISE,
    ) -> Edge:
        """make circle

        Create a circle centered on the origin of plane

        Args:
            radius (float): circle radius
            plane (Plane, optional): base plane. Defaults to Plane.XY.
            start_angle (float, optional): start of arc angle. Defaults to 360.0.
            end_angle (float, optional): end of arc angle. Defaults to 360.
            angular_direction (AngularDirection, optional): arc direction.
                Defaults to AngularDirection.COUNTER_CLOCKWISE.

        Returns:
            Edge: full or partial circle
        """
        circle_gp = gp_Circ(plane.to_gp_ax2(), radius)

        if start_angle == end_angle:  # full circle case
            return_value = cls(BRepBuilderAPI_MakeEdge(circle_gp).Edge())
        else:  # arc case
            circle_geom = GC_MakeArcOfCircle(
                circle_gp,
                start_angle * DEG2RAD,
                end_angle * DEG2RAD,
                angular_direction == AngularDirection.COUNTER_CLOCKWISE,
            ).Value()
            return_value = cls(BRepBuilderAPI_MakeEdge(circle_geom).Edge())
        return return_value

    @classmethod
    def make_ellipse(
        cls,
        x_radius: float,
        y_radius: float,
        plane: Plane = Plane.XY,
        start_angle: float = 360.0,
        end_angle: float = 360.0,
        angular_direction: AngularDirection = AngularDirection.COUNTER_CLOCKWISE,
    ) -> Edge:
        """make ellipse

        Makes an ellipse centered at the origin of plane.

        Args:
            x_radius (float): x radius of the ellipse (along the x-axis of plane)
            y_radius (float): y radius of the ellipse (along the y-axis of plane)
            plane (Plane, optional): base plane. Defaults to Plane.XY.
            start_angle (float, optional): Defaults to 360.0.
            end_angle (float, optional): Defaults to 360.0.
            angular_direction (AngularDirection, optional): arc direction.
                Defaults to AngularDirection.COUNTER_CLOCKWISE.

        Returns:
            Edge: full or partial ellipse
        """
        ax1 = gp_Ax1(plane.origin.to_pnt(), plane.z_dir.to_dir())

        if y_radius > x_radius:
            # swap x and y radius and rotate by 90° afterwards to create an ellipse
            # with x_radius < y_radius
            correction_angle = 90.0 * DEG2RAD
            ellipse_gp = gp_Elips(plane.to_gp_ax2(), y_radius, x_radius).Rotated(
                ax1, correction_angle
            )
        else:
            correction_angle = 0.0
            ellipse_gp = gp_Elips(plane.to_gp_ax2(), x_radius, y_radius)

        if start_angle == end_angle:  # full ellipse case
            ellipse = cls(BRepBuilderAPI_MakeEdge(ellipse_gp).Edge())
        else:  # arc case
            # take correction_angle into account
            ellipse_geom = GC_MakeArcOfEllipse(
                ellipse_gp,
                start_angle * DEG2RAD - correction_angle,
                end_angle * DEG2RAD - correction_angle,
                angular_direction == AngularDirection.COUNTER_CLOCKWISE,
            ).Value()
            ellipse = cls(BRepBuilderAPI_MakeEdge(ellipse_geom).Edge())

        return ellipse

    @classmethod
    def make_mid_way(cls, first: Edge, second: Edge, middle: float = 0.5) -> Edge:
        """make line between edges

        Create a new linear Edge between the two provided Edges. If the Edges are parallel
        but in the opposite directions one Edge is flipped such that the mid way Edge isn't
        truncated.

        Args:
            first (Edge): first reference Edge
            second (Edge): second reference Edge
            middle (float, optional): factional distance between Edges. Defaults to 0.5.

        Returns:
            Edge: linear Edge between two Edges
        """
        flip = first.to_axis().is_opposite(second.to_axis())
        pnts = [
            Edge.make_line(
                first.position_at(i), second.position_at(1 - i if flip else i)
            ).position_at(middle)
            for i in [0, 1]
        ]
        return Edge.make_line(*pnts)

    @classmethod
    def make_spline(
        cls,
        points: list[VectorLike],
        tangents: list[VectorLike] = None,
        periodic: bool = False,
        parameters: list[float] = None,
        scale: bool = True,
        tol: float = 1e-6,
    ) -> Edge:
        """Spline

        Interpolate a spline through the provided points.

        Args:
            points (list[VectorLike]):  the points defining the spline
            tangents (list[VectorLike], optional): start and finish tangent.
                Defaults to None.
            periodic (bool, optional): creation of periodic curves. Defaults to False.
            parameters (list[float], optional): the value of the parameter at each
                interpolation point. (The interpolated curve is represented as a vector-valued
                function of a scalar parameter.) If periodic == True, then len(parameters)
                must be len(interpolation points) + 1, otherwise len(parameters)
                must be equal to len(interpolation points). Defaults to None.
            scale (bool, optional): whether to scale the specified tangent vectors before
                interpolating. Each tangent is scaled, so it's length is equal to the derivative
                of the Lagrange interpolated curve. I.e., set this to True, if you want to use
                only the direction of the tangent vectors specified by `tangents` , but not
                their magnitude. Defaults to True.
            tol (float, optional): tolerance of the algorithm (consult OCC documentation).
                Used to check that the specified points are not too close to each other, and
                that tangent vectors are not too short. (In either case interpolation may fail.).
                Defaults to 1e-6.

        Raises:
            ValueError: Parameter for each interpolation point
            ValueError: Tangent for each interpolation point
            ValueError: B-spline interpolation failed

        Returns:
            Edge: the spline
        """
        points = [Vector(point) for point in points]
        if tangents:
            tangents = tuple(Vector(v) for v in tangents)
        pnts = TColgp_HArray1OfPnt(1, len(points))
        for i, point in enumerate(points):
            pnts.SetValue(i + 1, point.to_pnt())

        if parameters is None:
            spline_builder = GeomAPI_Interpolate(pnts, periodic, tol)
        else:
            if len(parameters) != (len(points) + periodic):
                raise ValueError(
                    "There must be one parameter for each interpolation point "
                    "(plus one if periodic), or none specified. Parameter count: "
                    f"{len(parameters)}, point count: {len(points)}"
                )
            parameters_array = TColStd_HArray1OfReal(1, len(parameters))
            for p_index, p_value in enumerate(parameters):
                parameters_array.SetValue(p_index + 1, p_value)

            spline_builder = GeomAPI_Interpolate(pnts, parameters_array, periodic, tol)

        if tangents:
            if len(tangents) == 2 and len(points) != 2:
                # Specify only initial and final tangent:
                spline_builder.Load(tangents[0].wrapped, tangents[1].wrapped, scale)
            else:
                if len(tangents) != len(points):
                    raise ValueError(
                        f"There must be one tangent for each interpolation point, "
                        f"or just two end point tangents. Tangent count: "
                        f"{len(tangents)}, point count: {len(points)}"
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
        points: list[VectorLike],
        tol: float = 1e-3,
        smoothing: Tuple[float, float, float] = None,
        min_deg: int = 1,
        max_deg: int = 6,
    ) -> Edge:
        """make_spline_approx

        Approximate a spline through the provided points.

        Args:
            points (list[Vector]):
            tol (float, optional): tolerance of the algorithm. Defaults to 1e-3.
            smoothing (Tuple[float, float, float], optional): optional tuple of 3 weights
                use for variational smoothing. Defaults to None.
            min_deg (int, optional): minimum spline degree. Enforced only when smoothing
                is None. Defaults to 1.
            max_deg (int, optional): maximum spline degree. Defaults to 6.

        Raises:
            ValueError: B-spline approximation failed

        Returns:
            Edge: spline
        """
        pnts = TColgp_HArray1OfPnt(1, len(points))
        for i, point in enumerate(points):
            pnts.SetValue(i + 1, Vector(point).to_pnt())

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
        cls, point1: VectorLike, point2: VectorLike, point3: VectorLike
    ) -> Edge:
        """Three Point Arc

        Makes a three point arc through the provided points

        Args:
            point1 (VectorLike): start point
            point2 (VectorLike): middle point
            point3 (VectorLike): end point

        Returns:
            Edge: a circular arc through the three points
        """
        circle_geom = GC_MakeArcOfCircle(
            Vector(point1).to_pnt(), Vector(point2).to_pnt(), Vector(point3).to_pnt()
        ).Value()

        return cls(BRepBuilderAPI_MakeEdge(circle_geom).Edge())

    @classmethod
    def make_tangent_arc(
        cls, start: VectorLike, tangent: VectorLike, end: VectorLike
    ) -> Edge:
        """Tangent Arc

        Makes a tangent arc from point start, in the direction of tangent and ends at end.

        Args:
            start (VectorLike): start point
            tangent (VectorLike): start tangent
            end (VectorLike): end point

        Returns:
            Edge: circular arc
        """
        circle_geom = GC_MakeArcOfCircle(
            Vector(start).to_pnt(), Vector(tangent).wrapped, Vector(end).to_pnt()
        ).Value()

        return cls(BRepBuilderAPI_MakeEdge(circle_geom).Edge())

    @classmethod
    def make_line(cls, point1: VectorLike, point2: VectorLike) -> Edge:
        """Create a line between two points

        Args:
          point1: VectorLike: that represents the first point
          point2: VectorLike: that represents the second point

        Returns:
          A linear edge between the two provided points

        """
        return cls(
            BRepBuilderAPI_MakeEdge(
                Vector(point1).to_pnt(), Vector(point2).to_pnt()
            ).Edge()
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
          self: Union[Wire:Edge]:
          count(int): Number of locations to generate
          start(float): position along Edge|Wire to start. Defaults to 0.0.
          stop(float): position along Edge|Wire to end. Defaults to 1.0.
          positions_only(bool): only generate position not orientation. Defaults to False.

        Returns:
          list[Location]: locations distributed along Edge|Wire

        Raises:
          ValueError: count must be two or greater

        """
        if count < 2:
            raise ValueError("count must be two or greater")

        t_values = [start + i * (stop - start) / (count - 1) for i in range(count)]

        locations = self.locations(t_values)
        if positions_only:
            for loc in locations:
                loc.orientation = (0, 0, 0)

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
        wire = Wire.make_wire([self])
        projected_wires = wire.project_to_shape(target_object, direction, center)
        projected_edges = [w.edges()[0] for w in projected_wires]
        return projected_edges

    def to_axis(self) -> Axis:
        """Translate a linear Edge to an Axis"""
        if self.geom_type() != "LINE":
            raise ValueError("to_axis is only valid for linear Edges")
        return Axis(self.position_at(0), self.position_at(1) - self.position_at(0))


class Face(Shape):
    """a bounded surface that represents part of the boundary of a solid"""

    @property
    def length(self) -> float:
        """experimental length calculation"""
        result = None
        if self.geom_type() == "PLANE":
            # Reposition on Plane.XY
            flat_face = Plane(self).to_local_coords(self)
            face_vertices = flat_face.vertices().sort_by(Axis.X)
            result = face_vertices[-1].X - face_vertices[0].X
        return result

    @property
    def width(self) -> float:
        """experimental width calculation"""
        result = None
        if self.geom_type() == "PLANE":
            # Reposition on Plane.XY
            flat_face = Plane(self).to_local_coords(self)
            face_vertices = flat_face.vertices().sort_by(Axis.Y)
            result = face_vertices[-1].Y - face_vertices[0].Y
        return result

    @property
    def geometry(self) -> str:
        """experimental geometry type"""
        result = None
        if self.geom_type() == "PLANE":
            flat_face = Plane(self).to_local_coords(self)
            flat_face_edges = flat_face.edges()
            if all([e.geom_type() == "LINE" for e in flat_face_edges]):
                flat_face_vertices = flat_face.vertices()
                result = "POLYGON"
                if len(flat_face_edges) == 4:
                    edge_pairs = []
                    for vertex in flat_face_vertices:
                        edge_pairs.append(
                            [e for e in flat_face_edges if vertex in e.vertices()]
                        )
                        edge_pair_directions = [
                            [edge.tangent_at(0) for edge in pair] for pair in edge_pairs
                        ]
                    if all(
                        [
                            edge_directions[0].get_angle(edge_directions[1]) == 90
                            for edge_directions in edge_pair_directions
                        ]
                    ):
                        result = "RECTANGLE"
                        if len(flat_face_edges.group_by(SortBy.LENGTH)) == 1:
                            result = "SQUARE"

        return result

    def _geom_adaptor(self) -> Geom_Surface:
        """ """
        return BRep_Tool.Surface_s(self.wrapped)

    def _uv_bounds(self) -> Tuple[float, float, float, float]:
        return BRepTools.UVBounds_s(self.wrapped)

    def __neg__(self) -> Face:
        """Return a copy of self with the normal reversed"""
        new_face = copy.deepcopy(self)
        new_face.wrapped = downcast(self.wrapped.Complemented())
        return new_face

    def offset(self, amount: float) -> Face:
        """Return a copy of self moved along the normal by amount"""
        return copy.deepcopy(self).moved(Location(self.normal_at() * amount))

    def normal_at(self, surface_point: VectorLike = None) -> Vector:
        """normal_at

        Computes the normal vector at the desired location on the face.

        Args:
            surface_point (VectorLike, optional): a point that lies on the surface where the normal.
                Defaults to None.

        Returns:
            Vector: surface normal direction
        """
        # get the geometry
        surface = self._geom_adaptor()

        if surface_point is None:
            u_val0, u_val1, v_val0, v_val1 = self._uv_bounds()
            u_val = 0.5 * (u_val0 + u_val1)
            v_val = 0.5 * (v_val0 + v_val1)
        else:
            # project point on surface
            projector = GeomAPI_ProjectPointOnSurf(
                Vector(surface_point).to_pnt(), surface
            )

            u_val, v_val = projector.LowerDistanceParameters()

        gp_pnt = gp_Pnt()
        normal = gp_Vec()
        BRepGProp_Face(self.wrapped).Normal(u_val, v_val, gp_pnt, normal)

        return Vector(normal)

    def center(self, center_of=CenterOf.GEOMETRY):
        """Center of Face

        Return the center based on center_of

        Args:
            center_of (CenterOf, optional): centering option. Defaults to CenterOf.GEOMETRY.

        Returns:
            Vector: center
        """
        if (center_of == CenterOf.MASS) or (
            center_of == CenterOf.GEOMETRY and self.geom_type() == "PLANE"
        ):
            properties = GProp_GProps()
            BRepGProp.SurfaceProperties_s(self.wrapped, properties)
            center_point = properties.CentreOfMass()

        elif center_of == CenterOf.BOUNDING_BOX:
            center_point = self.bounding_box().center()

        elif center_of == CenterOf.GEOMETRY:
            u_val0, u_val1, v_val0, v_val1 = self._uv_bounds()
            u_val = 0.5 * (u_val0 + u_val1)
            v_val = 0.5 * (v_val0 + v_val1)

            center_point = gp_Pnt()
            normal = gp_Vec()
            BRepGProp_Face(self.wrapped).Normal(u_val, v_val, center_point, normal)

        return Vector(center_point)

    def outer_wire(self) -> Wire:
        """Extract the perimeter wire from this Face"""
        return Wire(BRepTools.OuterWire_s(self.wrapped))

    def inner_wires(self) -> list[Wire]:
        """Extract the inner or hole wires from this Face"""
        outer = self.outer_wire()

        return [w for w in self.wires() if not w.is_same(outer)]

    @classmethod
    def make_rect(cls, width: float, height: float, plane: Plane = Plane.XY) -> Face:
        """make_rect

        Make a Rectangle centered on center with the given normal

        Args:
            width (float, optional): width (local x).
            height (float, optional): height (local y).
            plane (Plane, optional): base plane. Defaults to Plane.XY.

        Returns:
            Face: The centered rectangle
        """
        pln_shape = BRepBuilderAPI_MakeFace(
            plane.wrapped, -height * 0.5, height * 0.5, -width * 0.5, width * 0.5
        ).Face()

        return cls(pln_shape)

    @classmethod
    def make_plane(
        cls,
        plane: Plane = Plane.XY,
    ) -> Face:
        """Create a unlimited size Face aligned with plane"""
        pln_shape = BRepBuilderAPI_MakeFace(plane.wrapped).Face()
        return cls(pln_shape)

    @overload
    @classmethod
    def make_surface_from_curves(
        cls, edge1: Edge, edge2: Edge
    ) -> Face:  # pragma: no cover
        ...

    @overload
    @classmethod
    def make_surface_from_curves(
        cls, wire1: Wire, wire2: Wire
    ) -> Face:  # pragma: no cover
        ...

    @classmethod
    def make_surface_from_curves(
        cls, curve1: Union[Edge, Wire], curve2: Union[Edge, Wire]
    ) -> Face:
        """make_surface_from_curves

        Create a ruled surface out of two edges or two wires. If wires are used then
        these must have the same number of edges.

        Args:
            curve1 (Union[Edge,Wire]): side of surface
            curve2 (Union[Edge,Wire]): opposite side of surface

        Returns:
            Face: potentially non planar surface
        """
        if isinstance(curve1, Wire):
            return_value = cls.cast(BRepFill.Shell_s(curve1.wrapped, curve2.wrapped))
        else:
            return_value = cls.cast(BRepFill.Face_s(curve1.wrapped, curve2.wrapped))
        return return_value

    @classmethod
    def make_from_wires(cls, outer_wire: Wire, inner_wires: list[Wire] = None) -> Face:
        """make_from_wires

        Makes a planar face from one or more wires

        Args:
            outer_wire (Wire): closed perimeter wire
            inner_wires (list[Wire], optional): holes. Defaults to None.

        Raises:
            ValueError: outer wire not closed
            ValueError: wires not planar
            ValueError: inner wire not closed
            ValueError: internal error

        Returns:
            Face: planar face potentially with holes
        """
        if inner_wires and not outer_wire.is_closed():
            raise ValueError("Cannot build face(s): outer wire is not closed")
        inner_wires = inner_wires if inner_wires else []

        # check if wires are coplanar
        verification_compound = Compound.make_compound([outer_wire] + inner_wires)
        if not BRepLib_FindSurface(
            verification_compound.wrapped, OnlyPlane=True
        ).Found():
            raise ValueError("Cannot build face(s): wires not planar")

        # fix outer wire
        sf_s = ShapeFix_Shape(outer_wire.wrapped)
        sf_s.Perform()
        topo_wire = TopoDS.Wire_s(sf_s.Shape())

        face_builder = BRepBuilderAPI_MakeFace(topo_wire, True)

        for inner_wire in inner_wires:
            if not inner_wire.is_closed():
                raise ValueError("Cannot build face(s): inner wire is not closed")
            face_builder.Add(inner_wire.wrapped)

        face_builder.Build()

        if not face_builder.IsDone():
            raise ValueError(f"Cannot build face(s): {face_builder.Error()}")

        face = face_builder.Face()

        sf_f = ShapeFix_Face(face)
        sf_f.FixOrientation()
        sf_f.Perform()

        return cls(sf_f.Result())

    @classmethod
    def sew_faces(cls, faces: Iterable[Face]) -> list[ShapeList[Face]]:
        """sew faces

        Group contiguous faces and return them in a list of ShapeList

        Args:
            faces (Iterable[Face]): Faces to sew together

        Raises:
            RuntimeError: OCCT SewedShape generated unexpected output

        Returns:
            list[ShapeList[Face]]: grouped contiguous faces
        """
        # Create the shell build
        shell_builder = BRepBuilderAPI_Sewing()
        # Add the given faces to it
        for face in faces:
            shell_builder.Add(face.wrapped)
        # Attempt to sew the faces into a contiguous shell
        shell_builder.Perform()
        # Extract the sewed shape - a face, a shell, a solid or a compound
        sewed_shape = downcast(shell_builder.SewedShape())

        # Create a list of ShapeList of Faces
        if isinstance(sewed_shape, TopoDS_Face):
            sewn_faces = [ShapeList([Face(sewed_shape)])]
        elif isinstance(sewed_shape, TopoDS_Shell):
            sewn_faces = [Shell(sewed_shape).faces()]
        elif isinstance(sewed_shape, TopoDS_Compound):
            sewn_faces = []
            for face in Compound(sewed_shape).get_type(Face):
                sewn_faces.append(ShapeList([face]))
            for shell in Compound(sewed_shape).get_type(Shell):
                sewn_faces.append(shell.faces())
        elif isinstance(sewed_shape, TopoDS_Solid):
            sewn_faces = [Solid(sewed_shape).faces()]
        else:
            raise RuntimeError(
                f"SewedShape returned a {type(sewed_shape)} which was unexpected"
            )

        return sewn_faces

    @classmethod
    def make_surface_from_array_of_points(
        cls,
        points: list[list[VectorLike]],
        tol: float = 1e-2,
        smoothing: Tuple[float, float, float] = None,
        min_deg: int = 1,
        max_deg: int = 3,
    ) -> Face:
        """make_surface_from_array_of_points

        Approximate a spline surface through the provided 2d array of points.

        Args:
            points (list[list[VectorLike]]): a 2D list of points
            tol (float, optional): tolerance of the algorithm. Defaults to 1e-2.
            smoothing (Tuple[float, float, float], optional): optional tuple of
                3 weights use for variational smoothing. Defaults to None.
            min_deg (int, optional): minimum spline degree. Enforced only when
                smoothing is None. Defaults to 1.
            max_deg (int, optional): maximum spline degree. Defaults to 3.

        Raises:
            ValueError: B-spline approximation failed

        Returns:
            Face: a potentially non-planar face defined by points
        """
        points_ = TColgp_HArray2OfPnt(1, len(points), 1, len(points[0]))

        for i, point_row in enumerate(points):
            for j, point in enumerate(point_row):
                points_.SetValue(i + 1, j + 1, Vector(point).to_pnt())

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

    @classmethod
    def make_surface(
        cls,
        exterior: Union[Wire, list[Edge]],
        surface_points: list[VectorLike] = None,
        interior_wires: list[Wire] = None,
    ) -> Face:
        """Create Non-Planar Face

        Create a potentially non-planar face bounded by exterior (wire or edges),
        optionally refined by surface_points with optional holes defined by
        interior_wires.

        Args:
            exterior (Union[Wire, list[Edge]]): Perimeter of face
            surface_points (list[VectorLike], optional): Points on the surface that
                refine the shape. Defaults to None.
            interior_wires (list[Wire], optional): Hole(s) in the face. Defaults to None.

        Raises:
            RuntimeError: Internal error building face
            RuntimeError: Error building non-planar face with provided surface_points
            RuntimeError: Error adding interior hole
            RuntimeError: Generated face is invalid

        Returns:
            Face: Potentially non-planar face
        """
        if surface_points:
            surface_points = [Vector(p) for p in surface_points]
        else:
            surface_points = None

        # First, create the non-planar surface
        surface = BRepOffsetAPI_MakeFilling(
            # order of energy criterion to minimize for computing the deformation of the surface
            Degree=3,
            # average number of points for discretisation of the edges
            NbPtsOnCur=15,
            NbIter=2,
            Anisotropie=False,
            # the maximum distance allowed between the support surface and the constraints
            Tol2d=0.00001,
            # the maximum distance allowed between the support surface and the constraints
            Tol3d=0.0001,
            # the maximum angle allowed between the normal of the surface and the constraints
            TolAng=0.01,
            # the maximum difference of curvature allowed between the surface and the constraint
            TolCurv=0.1,
            # the highest degree which the polynomial defining the filling surface can have
            MaxDeg=8,
            # the greatest number of segments which the filling surface can have
            MaxSegments=9,
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
        except (StdFail_NotDone, Standard_NoSuchObject) as err:
            raise RuntimeError(
                "Error building non-planar face with provided exterior"
            ) from err
        if surface_points:
            for point in surface_points:
                surface.Add(gp_Pnt(*point.to_tuple()))
            try:
                surface.Build()
                surface_face = Face(surface.Shape())
            except StdFail_NotDone as err:
                raise RuntimeError(
                    "Error building non-planar face with provided surface_points"
                ) from err

        # Next, add wires that define interior holes - note these wires must be entirely interior
        if interior_wires:
            makeface_object = BRepBuilderAPI_MakeFace(surface_face.wrapped)
            for wire in interior_wires:
                makeface_object.Add(wire.wrapped)
            try:
                surface_face = Face(makeface_object.Face())
            except StdFail_NotDone as err:
                raise RuntimeError(
                    "Error adding interior hole in non-planar face with provided interior_wires"
                ) from err

        surface_face = surface_face.fix()
        if not surface_face.is_valid():
            raise RuntimeError("non planar face is invalid")

        return surface_face

    def fillet_2d(self, radius: float, vertices: Iterable[Vertex]) -> Face:
        """Apply 2D fillet to a face

        Args:
          radius: float:
          vertices: Iterable[Vertex]:

        Returns:

        """

        fillet_builder = BRepFilletAPI_MakeFillet2d(self.wrapped)

        for vertex in vertices:
            fillet_builder.AddFillet(vertex.wrapped, radius)

        fillet_builder.Build()

        return self.__class__(fillet_builder.Shape())

    def chamfer_2d(self, distance: float, vertices: Iterable[Vertex]) -> Face:
        """Apply 2D chamfer to a face

        Args:
          distance: float:
          vertices: Iterable[Vertex]:

        Returns:

        """

        chamfer_builder = BRepFilletAPI_MakeFillet2d(self.wrapped)
        edge_map = self._entities_from(Vertex.__name__, Edge.__name__)

        for vertex in vertices:
            edges = edge_map[vertex]
            if len(edges) < 2:
                raise ValueError("Cannot chamfer at this location")

            edge1, edge2 = edges

            chamfer_builder.AddChamfer(
                TopoDS.Edge_s(edge1.wrapped),
                TopoDS.Edge_s(edge2.wrapped),
                distance,
                distance,
            )

        chamfer_builder.Build()

        return self.__class__(chamfer_builder.Shape()).fix()

    def is_coplanar(self, plane: Plane) -> bool:
        """Is this planar face coplanar with the provided plane"""
        return all(
            [
                plane.contains(pnt)
                for pnt in self.outer_wire().positions([i / 7 for i in range(8)])
            ]
        )

    def thicken(self, depth: float, normal_override: VectorLike = None) -> Solid:
        """Thicken Face

        Create a solid from a potentially non planar face by thickening along the normals.

        .. image:: thickenFace.png

        Non-planar faces are thickened both towards and away from the center of the sphere.

        Args:
            depth (float): Amount to thicken face(s), can be positive or negative.
            normal_override (Vector, optional): The normal_override vector can be used to
                indicate which way is 'up', potentially flipping the face normal direction
                such that many faces with different normals all go in the same direction
                (direction need only be +/- 90 degrees from the face normal). Defaults to None.

        Raises:
            RuntimeError: Opencascade internal failures

        Returns:
            Solid: The resulting Solid object
        """
        # Check to see if the normal needs to be flipped
        adjusted_depth = depth
        if normal_override is not None:
            face_center = self.center()
            face_normal = self.normal_at(face_center).normalized()
            if face_normal.dot(Vector(normal_override).normalized()) < 0:
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
        except StdFail_NotDone as err:
            raise RuntimeError("Error applying thicken to given Face") from err

        return result.clean()

    def project_to_shape(
        self, target_object: Shape, direction: VectorLike, taper: float = 0
    ) -> ShapeList[Face]:
        """Project Face to target Object

        Project a Face onto a Shape generating new Face(s) on the surfaces of the object.

        A projection with no taper is illustrated below:

        .. image:: flatProjection.png
            :alt: flatProjection

        Note that an array of faces is returned as the projection might result in faces
        on the "front" and "back" of the object (or even more if there are intermediate
        surfaces in the projection path). faces "behind" the projection are not
        returned.

        Args:
            target_object (Shape): Object to project onto
            direction (VectorLike): projection direction
            taper (float, optional): taper angle. Defaults to 0.

        Returns:
            ShapeList[Face]: Face(s) projected on target object ordered by distance
        """
        max_dimension = (
            Compound.make_compound([self, target_object]).bounding_box().diagonal
        )
        face_extruded = Solid.extrude_linear(
            self, Vector(direction) * max_dimension, taper=taper
        )
        intersected_faces = ShapeList()
        for target_face in target_object.faces():
            intersected_faces.extend(face_extruded.intersect(target_face).faces())

        return intersected_faces.sort_by(Axis(self.center(), direction))

    def make_holes(self, interior_wires: list[Wire]) -> Face:
        """Make Holes in Face

        Create holes in the Face 'self' from interior_wires which must be entirely interior.
        Note that making holes in faces is more efficient than using boolean operations
        with solid object. Also note that OCCT core may fail unless the orientation of the wire
        is correct - use `Wire(forward_wire.wrapped.Reversed())` to reverse a wire.

        Example:

            For example, make a series of slots on the curved walls of a cylinder.

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
        for interior_wire in interior_wires:
            makeface_object.Add(interior_wire.wrapped)
        try:
            surface_face = Face(makeface_object.Face())
        except StdFail_NotDone as err:
            raise RuntimeError(
                "Error adding interior hole in non-planar face with provided interior_wires"
            ) from err

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


class Shell(Shape):
    """the outer boundary of a surface"""

    @classmethod
    def make_shell(cls, faces: Iterable[Face]) -> Shell:
        """Create a Shell from provided faces"""
        shell_builder = BRepBuilderAPI_Sewing()

        for face in faces:
            shell_builder.Add(face.wrapped)

        shell_builder.Perform()
        shape = shell_builder.SewedShape()

        return cls(shape)

    def center(self) -> Vector:
        """Center of mass of the shell"""
        properties = GProp_GProps()
        BRepGProp.LinearProperties_s(self.wrapped, properties)
        return Vector(properties.CentreOfMass())


class Solid(Shape, Mixin3D):
    """a single solid"""

    @classmethod
    def make_solid(cls, shell: Shell) -> Solid:
        """Create a Solid object from the surface shell"""
        return cls(ShapeFix_Solid().SolidFromShell(shell.wrapped))

    @classmethod
    def from_bounding_box(cls, bbox: BoundBox) -> Solid:
        """A box of the same dimensions and location"""
        return Solid.make_box(*bbox.size).locate(Location(bbox.min))

    @classmethod
    def make_box(
        cls, length: float, width: float, height: float, plane: Plane = Plane.XY
    ) -> Solid:
        """make box

        Make a box at the origin of plane extending in positive direction of each axis.

        Args:
            length (float):
            width (float):
            height (float):
            plane (Plane, optional): base plane. Defaults to Plane.XY.

        Returns:
            Solid: Box
        """
        return cls(
            BRepPrimAPI_MakeBox(
                plane.to_gp_ax2(),
                length,
                width,
                height,
            ).Shape()
        )

    @classmethod
    def make_cone(
        cls,
        base_radius: float,
        top_radius: float,
        height: float,
        plane: Plane = Plane.XY,
        angle: float = 360,
    ) -> Solid:
        """make cone

        Make a cone with given radii and height

        Args:
            base_radius (float):
            top_radius (float):
            height (float):
            plane (Plane): base plane. Defaults to Plane.XY.
            angle (float, optional): arc size. Defaults to 360.

        Returns:
            Solid: Full or partial cone
        """
        return cls(
            BRepPrimAPI_MakeCone(
                plane.to_gp_ax2(),
                base_radius,
                top_radius,
                height,
                angle * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def make_cylinder(
        cls,
        radius: float,
        height: float,
        plane: Plane = Plane.XY,
        angle: float = 360,
    ) -> Solid:
        """make cylinder

        Make a cylinder with a given radius and height with the base center on plane origin.

        Args:
            radius (float):
            height (float):
            plane (Plane): base plane. Defaults to Plane.XY.
            angle (float, optional): arc size. Defaults to 360.

        Returns:
            Solid: Full or partial cylinder
        """
        return cls(
            BRepPrimAPI_MakeCylinder(
                plane.to_gp_ax2(),
                radius,
                height,
                angle * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def make_torus(
        cls,
        major_radius: float,
        minor_radius: float,
        plane: Plane = Plane.XY,
        start_angle: float = 0,
        end_angle: float = 360,
        major_angle: float = 360,
    ) -> Solid:
        """make torus

        Make a torus with a given radii and angles

        Args:
            major_radius (float):
            minor_radius (float):
            plane (Plane): base plane. Defaults to Plane.XY.
            start_angle (float, optional): start major arc. Defaults to 0.
            end_angle (float, optional): end major arc. Defaults to 360.

        Returns:
            Solid: Full or partial torus
        """
        return cls(
            BRepPrimAPI_MakeTorus(
                plane.to_gp_ax2(),
                major_radius,
                minor_radius,
                start_angle * DEG2RAD,
                end_angle * DEG2RAD,
                major_angle * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def make_loft(cls, wires: list[Wire], ruled: bool = False) -> Solid:
        """make loft

        Makes a loft from a list of wires.

        Args:
            wires (list[Wire]): section perimeters
            ruled (bool, optional): stepped or smooth. Defaults to False (smooth).

        Raises:
            ValueError: Too few wires

        Returns:
            Solid: Lofted object
        """
        # the True flag requests building a solid instead of a shell.
        if len(wires) < 2:
            raise ValueError("More than one wire is required")
        loft_builder = BRepOffsetAPI_ThruSections(True, ruled)

        for wire in wires:
            loft_builder.AddWire(wire.wrapped)

        loft_builder.Build()

        return cls(loft_builder.Shape())

    @classmethod
    def make_wedge(
        cls,
        delta_x: float,
        delta_y: float,
        delta_z: float,
        min_x: float,
        min_z: float,
        max_x: float,
        max_z: float,
        plane: Plane = Plane.XY,
    ) -> Solid:
        """Make a wedge

        Args:
            delta_x (float):
            delta_y (float):
            delta_z (float):
            min_x (float):
            min_z (float):
            max_x (float):
            max_z (float):
            plane (Plane): base plane. Defaults to Plane.XY.

        Returns:
            Solid: wedge
        """
        return cls(
            BRepPrimAPI_MakeWedge(
                plane.to_gp_ax2(),
                delta_x,
                delta_y,
                delta_z,
                min_x,
                min_z,
                max_x,
                max_z,
            ).Solid()
        )

    @classmethod
    def make_sphere(
        cls,
        radius: float,
        plane: Plane = Plane.XY,
        angle1: float = -90,
        angle2: float = 90,
        angle3: float = 360,
    ) -> Solid:
        """Sphere

        Make a full or partial sphere - with a given radius center on the origin or plane.

        Args:
            radius (float):
            plane (Plane): base plane. Defaults to Plane.XY.
            angle1 (float, optional): Defaults to -90.
            angle2 (float, optional): Defaults to 90.
            angle3 (float, optional): Defaults to 360.

        Returns:
            Solid: sphere
        """
        return cls(
            BRepPrimAPI_MakeSphere(
                plane.to_gp_ax2(),
                radius,
                angle1 * DEG2RAD,
                angle2 * DEG2RAD,
                angle3 * DEG2RAD,
            ).Shape()
        )

    @classmethod
    def extrude_linear(
        cls,
        section: Union[Face, Wire],
        normal: VectorLike,
        inner_wires: list[Wire] = None,
        taper: float = 0,
    ) -> Solid:
        """Extrude a cross section

        Extrude a cross section into a prismatic solid in the provided direction.
        The wires must not intersect.

        Extruding wires is very non-trivial.  Nested wires imply very different geometry, and
        there are many geometries that are invalid. In general, the following conditions
        must be met:

        * all wires must be closed
        * there cannot be any intersecting or self-intersecting wires
        * wires must be listed from outside in
        * more than one levels of nesting is not supported reliably

        Args:
            section (Union[Face,Wire]): cross section
            normal (VectorLike): a vector along which to extrude the wires. The length
                of the vector controls the length of the extrusion.
            inner_wires (list[Wire], optional): holes - only used if section is a Wire.
                Defaults to None.
            taper (float, optional): taper angle. Defaults to 0.

        Returns:
            Solid: extruded cross section
        """
        inner_wires = inner_wires if inner_wires else []
        normal = Vector(normal)
        if isinstance(section, Wire):
            # TODO: Should the normal of this face be forced to align with the extrusion normal?
            section_face = Face.make_from_wires(section, inner_wires)
        else:
            section_face = section

        if taper == 0:
            prism_builder: Any = BRepPrimAPI_MakePrism(
                section_face.wrapped, normal.wrapped, True
            )
        else:
            face_normal = section_face.normal_at()
            direction = 1 if normal.get_angle(face_normal) < 90 else -1
            prism_builder = LocOpe_DPrism(
                section_face.wrapped,
                direction * normal.length,
                direction * taper * DEG2RAD,
            )

        return cls(prism_builder.Shape())

    @classmethod
    def extrude_linear_with_rotation(
        cls,
        section: Union[Face, Wire],
        center: VectorLike,
        normal: VectorLike,
        angle: float,
        inner_wires: list[Wire] = None,
    ) -> Solid:
        """Extrude with Rotation

        Creates a 'twisted prism' by extruding, while simultaneously rotating around the
        extrusion vector.

        Args:
            section (Union[Face,Wire]): cross section
            vec_center (VectorLike): the center point about which to rotate
            vec_normal (VectorLike): a vector along which to extrude the wires
            angle (float): the angle to rotate through while extruding
            inner_wires (list[Wire], optional): holes - only used if section is of type Wire.
                Defaults to None.

        Returns:
            Solid: extruded object
        """
        # Though the signature may appear to be similar enough to extrude_linear to merit
        # combining them, the construction methods used here are different enough that they
        # should be separate.

        # At a high level, the steps followed are:
        # (1) accept a set of wires
        # (2) create another set of wires like this one, but which are transformed and rotated
        # (3) create a ruledSurface between the sets of wires
        # (4) create a shell and compute the resulting object

        inner_wires = inner_wires if inner_wires else []
        center = Vector(center)
        normal = Vector(normal)

        def extrude_aux_spine(
            wire: TopoDS_Wire, spine: TopoDS_Wire, aux_spine: TopoDS_Wire
        ) -> TopoDS_Shape:
            """Helper function"""
            extrude_builder = BRepOffsetAPI_MakePipeShell(spine)
            extrude_builder.SetMode(aux_spine, False)  # auxiliary spine
            extrude_builder.Add(wire)
            extrude_builder.Build()
            extrude_builder.MakeSolid()
            return extrude_builder.Shape()

        if isinstance(section, Face):
            outer_wire = section.outer_wire()
            inner_wires = section.inner_wires()
        else:
            outer_wire = section

        # make straight spine
        straight_spine_e = Edge.make_line(center, center.add(normal))
        straight_spine_w = Wire.combine(
            [
                straight_spine_e,
            ]
        )[0].wrapped

        # make an auxiliary spine
        pitch = 360.0 / angle * normal.length
        aux_spine_w = Wire.make_helix(
            pitch, normal.length, 1, center=center, normal=normal
        ).wrapped

        # extrude the outer wire
        outer_solid = extrude_aux_spine(
            outer_wire.wrapped, straight_spine_w, aux_spine_w
        )

        # extrude inner wires
        inner_solids = [
            Shape(extrude_aux_spine(w.wrapped, straight_spine_w, aux_spine_w))
            for w in inner_wires
        ]

        # combine the inner solids into compound
        inner_comp = Compound.make_compound(inner_solids).wrapped

        # subtract from the outer solid
        return Solid(BRepAlgoAPI_Cut(outer_solid, inner_comp).Shape())

    @classmethod
    def extrude_until(
        cls,
        section: Face,
        target_object: Union[Compound, Solid],
        direction: VectorLike,
        until: Until = Until.NEXT,
    ) -> Union[Compound, Solid]:
        """extrude_until

        Extrude section in provided direction until it encounters either the
        NEXT or LAST surface of target_object. Note that the bounding surface
        must be larger than the extruded face where they contact.

        Args:
            section (Face): Face to extrude
            target_object (Union[Compound, Solid]): object to limit extrusion
            direction (VectorLike): extrusion direction
            until (Until, optional): surface to limit extrusion. Defaults to Until.NEXT.

        Raises:
            ValueError: provided face does not intersect target_object

        Returns:
            Union[Compound, Solid]: extruded Face
        """
        direction = Vector(direction)

        max_dimension = (
            Compound.make_compound([section, target_object]).bounding_box().diagonal
        )
        clipping_direction = (
            direction * max_dimension
            if until == Until.NEXT
            else -direction * max_dimension
        )
        direction_axis = Axis(section.center(), clipping_direction)
        # Create a linear extrusion to start
        extrusion = Solid.extrude_linear(section, direction * max_dimension)

        # Project section onto the shape to generate faces that will clip the extrusion
        # and exclude the planar faces normal to the direction of extrusion and these
        # will have no volume when extruded
        clip_faces = [
            f
            for f in section.project_to_shape(target_object, direction)
            if not (f.geom_type() == "PLANE" and f.normal_at().dot(direction) == 0.0)
        ]
        if not clip_faces:
            raise ValueError("provided face does not intersect target_object")

        # Create the objects that will clip the linear extrusion
        clipping_objects = [
            Solid.extrude_linear(f, clipping_direction).fix() for f in clip_faces
        ]

        if until == Until.NEXT:
            extrusion = extrusion.cut(target_object)
            for clipping_object in clipping_objects:
                # It's possible for clipping faces to self intersect when they are extruded
                # thus they could be non manifold which results failed boolean operations
                #  - so skip these objects
                try:
                    extrusion = (
                        extrusion.cut(clipping_object)
                        .solids()
                        .sort_by(direction_axis)[0]
                    )
                except:
                    warnings.warn("clipping error - extrusion may be incorrect")
        else:
            extrusion_parts = [extrusion.intersect(target_object)]
            for clipping_object in clipping_objects:
                try:
                    extrusion_parts.append(
                        extrusion.intersect(clipping_object)
                        .solids()
                        .sort_by(direction_axis)[0]
                    )
                except:
                    warnings.warn("clipping error - extrusion may be incorrect")
            extrusion = Shape.fuse(*extrusion_parts)

        return extrusion

    @classmethod
    def revolve(
        cls,
        section: Union[Face, Wire],
        angle: float,
        axis: Axis,
        inner_wires: list[Wire] = None,
    ) -> Solid:
        """Revolve

        Revolve a cross section about the given Axis by the given angle.

        Args:
            section (Union[Face,Wire]): cross section
            angle (float): the angle to revolve through
            axis (Axis): rotation Axis
            inner_wires (list[Wire], optional): holes - only used if section is of type Wire.
                Defaults to [].

        Returns:
            Solid: the revolved cross section
        """
        inner_wires = inner_wires if inner_wires else []
        if isinstance(section, Wire):
            section_face = Face.make_from_wires(section, inner_wires)
        else:
            section_face = section

        revol_builder = BRepPrimAPI_MakeRevol(
            section_face.wrapped,
            axis.wrapped,
            angle * DEG2RAD,
            True,
        )

        return cls(revol_builder.Shape())

    _transModeDict = {
        Transition.TRANSFORMED: BRepBuilderAPI_Transformed,
        Transition.ROUND: BRepBuilderAPI_RoundCorner,
        Transition.RIGHT: BRepBuilderAPI_RightCorner,
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
            coordinate_system = gp_Ax2()
            coordinate_system.SetLocation(path.start_point().to_pnt())
            coordinate_system.SetDirection(mode.to_dir())
            builder.SetMode(coordinate_system)
            rotate = True
        elif isinstance(mode, (Wire, Edge)):
            builder.SetMode(mode.to_wire().wrapped, True)

        return rotate

    @classmethod
    def sweep(
        cls,
        section: Union[Face, Wire],
        path: Union[Wire, Edge],
        inner_wires: list[Wire] = None,
        make_solid: bool = True,
        is_frenet: bool = False,
        mode: Union[Vector, Wire, Edge, None] = None,
        transition: Transition = Transition.TRANSFORMED,
    ) -> Solid:
        """Sweep

        Sweep the given cross section into a prismatic solid along the provided path

        Args:
            section (Union[Face, Wire]): cross section to sweep
            path (Union[Wire, Edge]): sweep path
            inner_wires (list[Wire]): holes - only used if section is a wire
            make_solid (bool, optional): return Solid or Shell. Defaults to True.
            is_frenet (bool, optional): Frenet mode. Defaults to False.
            mode (Union[Vector, Wire, Edge, None], optional): additional sweep
                mode parameters. Defaults to None.
            transition (Transition, optional): handling of profile orientation at C1 path
                discontinuities. Defaults to Transition.TRANSFORMED.

        Returns:
            Solid: the swept cross section
        """
        if isinstance(section, Face):
            outer_wire = section.outer_wire()
            inner_wires = section.inner_wires()
        else:
            outer_wire = section
            inner_wires = inner_wires if inner_wires else []

        shapes = []
        for wire in [outer_wire] + inner_wires:
            builder = BRepOffsetAPI_MakePipeShell(path.to_wire().wrapped)

            rotate = False

            # handle sweep mode
            if mode:
                rotate = Solid._set_sweep_mode(builder, path, mode)
            else:
                builder.SetMode(is_frenet)

            builder.SetTransitionMode(Solid._transModeDict[transition])

            builder.Add(wire.wrapped, False, rotate)

            builder.Build()
            if make_solid:
                builder.MakeSolid()

            shapes.append(Shape.cast(builder.Shape()))

        return_value, inner_shapes = shapes[0], shapes[1:]

        if inner_shapes:
            return_value = return_value.cut(*inner_shapes)

        return return_value

    @classmethod
    def sweep_multi(
        cls,
        profiles: Iterable[Union[Wire, Face]],
        path: Union[Wire, Edge],
        make_solid: bool = True,
        is_frenet: bool = False,
        mode: Union[Vector, Wire, Edge, None] = None,
    ) -> Solid:
        """Multi section sweep

        Sweep through a sequence of profiles following a path.

        Args:
            profiles (Iterable[Union[Wire, Face]]): list of profiles
            path (Union[Wire, Edge]): The wire to sweep the face resulting from the wires over
            make_solid (bool, optional): Solid or Shell. Defaults to True.
            is_frenet (bool, optional): Select frenet mode. Defaults to False.
            mode (Union[Vector, Wire, Edge, None], optional): additional sweep mode parameters.
                Defaults to None.

        Returns:
            Solid: swept object
        """
        path_as_wire = path.to_wire().wrapped

        builder = BRepOffsetAPI_MakePipeShell(path_as_wire)

        translate = False
        rotate = False

        if mode:
            rotate = cls._set_sweep_mode(builder, path, mode)
        else:
            builder.SetMode(is_frenet)

        for profile in profiles:
            path_as_wire = (
                profile.wrapped
                if isinstance(profile, Wire)
                else profile.outer_wire().wrapped
            )
            builder.Add(path_as_wire, translate, rotate)

        builder.Build()

        if make_solid:
            builder.MakeSolid()

        return cls(builder.Shape())


class Vertex(Shape):
    """A Single Point in Space"""

    @overload
    def __init__(self):  # pragma: no cover
        """Default Vertext at the origin"""

    @overload
    def __init__(self, obj: TopoDS_Vertex):  # pragma: no cover
        """Vertex from OCCT TopoDS_Vertex object"""

    @overload
    def __init__(self, X: float, Y: float, Z: float):  # pragma: no cover
        """Vertex from three float values"""

    @overload
    def __init__(self, values: Iterable[float]):
        """Vertex from Vector or other iterators"""

    @overload
    def __init__(self, values: tuple[float]):
        """Vertex from tuple of floats"""

    def __init__(self, *args):
        if len(args) == 0:
            self.wrapped = downcast(
                BRepBuilderAPI_MakeVertex(gp_Pnt(0.0, 0.0, 0.0)).Vertex()
            )
        elif len(args) == 1 and isinstance(args[0], TopoDS_Vertex):
            self.wrapped = args[0]
        elif len(args) == 1 and isinstance(args[0], (Iterable, tuple)):
            values = [float(value) for value in args[0]]
            if len(values) < 3:
                values += [0.0] * (3 - len(values))
            self.wrapped = downcast(BRepBuilderAPI_MakeVertex(gp_Pnt(*values)).Vertex())
        elif len(args) == 3 and all(isinstance(v, (int, float)) for v in args):
            self.wrapped = downcast(
                BRepBuilderAPI_MakeVertex(gp_Pnt(args[0], args[1], args[2])).Vertex()
            )
        else:
            raise ValueError(
                "Invalid Vertex - expected three floats or OCC TopoDS_Vertex"
            )
        self.X, self.Y, self.Z = self.to_tuple()
        super().__init__(self.wrapped)

    def to_tuple(self) -> tuple[float, float, float]:
        """Return vertex as three tuple of floats"""
        geom_point = BRep_Tool.Pnt_s(self.wrapped)
        return (geom_point.X(), geom_point.Y(), geom_point.Z())

    def center(self) -> Vector:
        """The center of a vertex is itself!"""
        return Vector(self.to_tuple())

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

            which creates a new Vertex 15 above one extracted from a part. One can add or
            subtract a `Vertex` , `Vector` or `tuple` of float values to a Vertex.
        """
        if isinstance(other, Vertex):
            new_vertex = Vertex(self.X + other.X, self.Y + other.Y, self.Z + other.Z)
        elif isinstance(other, (Vector, tuple)):
            new_other = Vector(other)
            new_vertex = Vertex(
                self.X + new_other.X, self.Y + new_other.Y, self.Z + new_other.Z
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
            new_vertex = Vertex(self.X - other.X, self.Y - other.Y, self.Z - other.Z)
        elif isinstance(other, (Vector, tuple)):
            new_other = Vector(other)
            new_vertex = Vertex(
                self.X - new_other.X, self.Y - new_other.Y, self.Z - new_other.Z
            )
        else:
            raise TypeError(
                "Vertex subtraction only supports Vertex,Vector or tuple(float,float,float)"
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

        Returns:
            Vector: representation of Vertex
        """
        return Vector(self.to_tuple())


class Wire(Shape, Mixin1D):
    """A series of connected, ordered edges, that typically bounds a Face"""

    def _geom_adaptor(self) -> BRepAdaptor_CompCurve:
        """ """
        return BRepAdaptor_CompCurve(self.wrapped)

    def close(self) -> Wire:
        """Close a Wire"""

        if not self.is_closed():
            edge = Edge.make_line(self.end_point(), self.start_point())
            return_value = Wire.combine((self, edge))[0]
        else:
            return_value = self

        return return_value

    def to_wire(self) -> Wire:
        """Return Wire - used as a pair with Edge.to_wire when self is Wire | Edge"""
        return self

    @classmethod
    def combine(
        cls, wires: Iterable[Union[Wire, Edge]], tol: float = 1e-9
    ) -> list[Wire]:
        """Attempt to combine a list of wires and edges into a new wire.

        Args:
          cls: param list_of_wires:
          tol: default 1e-9
          wires: Iterable[Union[Wire:
          Edge]]:
          tol: float:  (Default value = 1e-9)

        Returns:
          list[Wire]

        """

        edges_in = TopTools_HSequenceOfShape()
        wires_out = TopTools_HSequenceOfShape()

        for edge in Compound.make_compound(wires).edges():
            edges_in.Append(edge.wrapped)

        ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

        return [cls(wire) for wire in wires_out]

    @classmethod
    def make_wire(cls, edges: Iterable[Edge], sequenced: bool = False) -> Wire:
        """make_wire

        Build a Wire from the provided unsorted Edges. If sequenced is True the
        Edges are placed in such that the end of the nth Edge is coincident with
        the n+1th Edge forming an unbroken sequence. Note that sequencing a list
        is relatively slow.

        Args:
            edges (Iterable[Edge]): Edges to assemble
            sequenced (bool, optional): arrange in order. Defaults to False.

        Raises:
            ValueError: Edges are disconnected and can't be sequenced.
            RuntimeError: Wire is empty

        Returns:
            Wire: assembled edges
        """

        def closest_to_end(current: Wire, unplaced_edges: list[Edge]) -> Edge:
            """Return the Edge closest to the end of last_edge"""
            target_point = current.position_at(1)

            sorted_edges = sorted(
                unplaced_edges,
                key=lambda e: min(
                    (target_point - e.position_at(0)).length,
                    (target_point - e.position_at(1)).length,
                ),
            )
            return sorted_edges[0]

        edges = list(edges)
        if sequenced:
            placed_edges = [edges.pop(0)]
            unplaced_edges = edges

            while unplaced_edges:
                next_edge = closest_to_end(Wire.make_wire(placed_edges), unplaced_edges)
                next_edge_index = unplaced_edges.index(next_edge)
                placed_edges.append(unplaced_edges.pop(next_edge_index))

            edges = placed_edges

        wire_builder = BRepBuilderAPI_MakeWire()
        for edge in edges:
            wire_builder.Add(edge.wrapped)
            if sequenced and wire_builder.Error() == BRepBuilderAPI_DisconnectedWire:
                raise ValueError("Edges are disconnected")

        wire_builder.Build()
        if not wire_builder.IsDone():
            if wire_builder.Error() == BRepBuilderAPI_NonManifoldWire:
                warnings.warn("Wire is non manifold")
            elif wire_builder.Error() == BRepBuilderAPI_EmptyWire:
                raise RuntimeError("Wire is empty")

        return cls(wire_builder.Wire())

    @classmethod
    def make_circle(cls, radius: float, plane: Plane = Plane.XY) -> Wire:
        """make_circle

        Makes a circle centered at the origin of plane

        Args:
            radius (float): circle radius
            plane (Plane): base plane. Defaults to Plane.XY

        Returns:
            Wire: a circle
        """
        circle_edge = Edge.make_circle(radius, plane=plane)
        return cls.make_wire([circle_edge])

    @classmethod
    def make_ellipse(
        cls,
        x_radius: float,
        y_radius: float,
        plane: Plane = Plane.XY,
        start_angle: float = 360.0,
        end_angle: float = 360.0,
        angular_direction: AngularDirection = AngularDirection.COUNTER_CLOCKWISE,
        closed: bool = True,
    ) -> Wire:
        """make ellipse

        Makes an ellipse centered at the origin of plane.

        Args:
            x_radius (float): x radius of the ellipse (along the x-axis of plane)
            y_radius (float): y radius of the ellipse (along the y-axis of plane)
            plane (Plane, optional): base plane. Defaults to Plane.XY.
            start_angle (float, optional): _description_. Defaults to 360.0.
            end_angle (float, optional): _description_. Defaults to 360.0.
            angular_direction (AngularDirection, optional): arc direction.
                Defaults to AngularDirection.COUNTER_CLOCKWISE.
            closed (bool, optional): close the arc. Defaults to True.

        Returns:
            Wire: an ellipse
        """
        ellipse_edge = Edge.make_ellipse(
            x_radius, y_radius, plane, start_angle, end_angle, angular_direction
        )

        if start_angle != end_angle and closed:
            line = Edge.make_line(ellipse_edge.end_point(), ellipse_edge.start_point())
            wire = cls.make_wire([ellipse_edge, line])
        else:
            wire = cls.make_wire([ellipse_edge])

        return wire

    @classmethod
    def make_polygon(cls, vertices: Iterable[VectorLike], close: bool = True) -> Wire:
        """make_polygon

        Create an irregular polygon by defining vertices

        Args:
            vertices (Iterable[VectorLike]):
            close (bool, optional): close the polygon. Defaults to True.

        Returns:
            Wire: an irregular polygon
        """
        vertices = [Vector(v) for v in vertices]
        if (vertices[0] - vertices[-1]).length > TOLERANCE and close:
            vertices.append(vertices[0])

        wire_builder = BRepBuilderAPI_MakePolygon()
        for vertex in vertices:
            wire_builder.Add(vertex.to_pnt())

        return cls(wire_builder.Wire())

    @classmethod
    def make_helix(
        cls,
        pitch: float,
        height: float,
        radius: float,
        center: VectorLike = (0, 0, 0),
        normal: VectorLike = (0, 0, 1),
        angle: float = 0.0,
        lefthand: bool = False,
    ) -> Wire:
        """make_helix

        Make a helix with a given pitch, height and radius. By default a cylindrical surface is
        used to create the helix. If the :angle: is set (the apex given in degree) a conical
        surface is used instead.

        Args:
            pitch (float): distance per revolution along normal
            height (float): total height
            radius (float):
            center (VectorLike, optional): Defaults to (0, 0, 0).
            normal (VectorLike, optional): Defaults to (0, 0, 1).
            angle (float, optional): conical angle. Defaults to 0.0.
            lefthand (bool, optional): Defaults to False.

        Returns:
            Wire: helix
        """
        # 1. build underlying cylindrical/conical surface
        if angle == 0.0:
            geom_surf: Geom_Surface = Geom_CylindricalSurface(
                gp_Ax3(Vector(center).to_pnt(), Vector(normal).to_dir()), radius
            )
        else:
            geom_surf = Geom_ConicalSurface(
                gp_Ax3(Vector(center).to_pnt(), Vector(normal).to_dir()),
                angle * DEG2RAD,
                radius,
            )

        # 2. construct an segment in the u,v domain
        if lefthand:
            geom_line = Geom2d_Line(gp_Pnt2d(0.0, 0.0), gp_Dir2d(-2 * pi, pitch))
        else:
            geom_line = Geom2d_Line(gp_Pnt2d(0.0, 0.0), gp_Dir2d(2 * pi, pitch))

        # 3. put it together into a wire
        u_start = geom_line.Value(0.0)
        u_stop = geom_line.Value((height / pitch) * sqrt((2 * pi) ** 2 + pitch**2))
        geom_seg = GCE2d_MakeSegment(u_start, u_stop).Value()

        topo_edge = BRepBuilderAPI_MakeEdge(geom_seg, geom_surf).Edge()

        # 4. Convert to wire and fix building 3d geom from 2d geom
        wire = BRepBuilderAPI_MakeWire(topo_edge).Wire()
        BRepLib.BuildCurves3d_s(wire, 1e-6, MaxSegment=2000)  # NB: preliminary values

        return cls(wire)

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

    def offset_2d(self, distance: float, kind: Kind = Kind.ARC) -> list[Wire]:
        """Wire Offset

        Offsets a planar wire

        Args:
            distance (float): distance from wire to offset
            kind (Kind, optional): offset corner transition. Defaults to Kind.ARC.

        Returns:
            list[Wire]: offset wires
        """
        kind_dict = {
            Kind.ARC: GeomAbs_JoinType.GeomAbs_Arc,
            Kind.INTERSECTION: GeomAbs_JoinType.GeomAbs_Intersection,
            Kind.TANGENT: GeomAbs_JoinType.GeomAbs_Tangent,
        }

        offset = BRepOffsetAPI_MakeOffset()
        offset.Init(kind_dict[kind])
        offset.AddWire(self.wrapped)
        offset.Perform(distance)

        obj = downcast(offset.Shape())

        if isinstance(obj, TopoDS_Compound):
            return_value = [self.__class__(el.wrapped) for el in Compound(obj)]
        else:
            return_value = [self.__class__(obj)]

        return return_value

    def fillet_2d(self, radius: float, vertices: Iterable[Vertex]) -> Wire:
        """fillet_2d

        Apply 2D fillet to a wire

        Args:
            radius (float):
            vertices (Iterable[Vertex]): vertices to fillet

        Returns:
            Wire: filleted wire
        """
        return Face.make_from_wires(self).fillet_2d(radius, vertices).outer_wire()

    def chamfer_2d(self, distance: float, vertices: Iterable[Vertex]) -> Wire:
        """chamfer_2d

        Apply 2D chamfer to a wire

        Args:
            distance (float): chamfer length
            vertices (Iterable[Vertex]): vertices to chamfer

        Returns:
            Wire: chamfered wire
        """
        return Face.make_from_wires(self).chamfer_2d(distance, vertices).outer_wire()

    @classmethod
    def make_rect(
        cls,
        width: float,
        height: float,
        pnt: VectorLike = (0, 0, 0),
        normal: VectorLike = (0, 0, 1),
    ) -> Wire:
        """Make Rectangle

        Make a Rectangle centered on center with the given normal

        Args:
            width (float): width (local x)
            height (float): height (local y)
            pnt (Vector): rectangle center point
            normal (Vector): rectangle normal

        Returns:
            Wire: The centered rectangle
        """
        corners_local = [
            (width / 2, height / 2),
            (width / 2, height / -2),
            (width / -2, height / -2),
            (width / -2, height / 2),
        ]
        user_plane = Plane(origin=Vector(pnt), z_dir=Vector(normal))
        corners_world = [user_plane.from_local_coords(c) for c in corners_local]
        return Wire.make_polygon(corners_world, close=True)

    @classmethod
    def make_convex_hull(cls, edges: Iterable[Edge], tolerance: float = 1e-3) -> Wire:
        """make_convex_hull

        Create a wire of minimum length enclosing all of the provided edges.

        Note that edges can't overlap each other.

        Args:
            edges (Iterable[Edge]): edges defining the convex hull

        Raises:
            ValueError: edges overlap
        Returns:
            Wire: convex hull perimeter
        """
        # Algorithm:
        # 1) create a cloud of points along all edges
        # 2) create a convex hull which returns facets/simplices as pairs of point indices
        # 3) find facets that are within an edge but not adjacent and store trim and
        #    new connecting edge data
        # 4) find facets between edges and store trim and new connecting edge data
        # 5) post process the trim data to remove duplicates and store in pairs
        # 6) create  connecting edges
        # 7) create trim edges from the original edges and the trim data
        # 8) return a wire version of all the edges

        # Possible enhancement: The accuracy of the result could be improved and the
        # execution time reduced by adaptively placing more points around where the
        # connecting edges contact the arc.

        # if any(
        #     [
        #         edge_pair[0].overlaps(edge_pair[1])
        #         for edge_pair in combinations(edges, 2)
        #     ]
        # ):
        #     raise ValueError("edges overlap")

        fragments_per_edge = int(2 / tolerance)
        points_lookup = {}  # lookup from point index to edge/position on edge
        points = []  # convex hull point cloud

        # Create points along each edge and the lookup structure
        for edge_index, edge in enumerate(edges):
            for i in range(fragments_per_edge):
                param = i / (fragments_per_edge - 1)
                points.append(edge.position_at(param).to_tuple()[:2])
                points_lookup[edge_index * fragments_per_edge + i] = (edge_index, param)

        convex_hull = ConvexHull(points)

        # Filter the fragments
        connecting_edge_data = []
        trim_points = {}
        for simplice in convex_hull.simplices:
            edge0 = points_lookup[simplice[0]][0]
            edge1 = points_lookup[simplice[1]][0]
            # Look for connecting edges between edges
            if edge0 != edge1:
                if not edge0 in trim_points:
                    trim_points[edge0] = [simplice[0]]
                else:
                    trim_points[edge0].append(simplice[0])
                if not edge1 in trim_points:
                    trim_points[edge1] = [simplice[1]]
                else:
                    trim_points[edge1].append(simplice[1])
                connecting_edge_data.append(
                    (
                        (edge0, points_lookup[simplice[0]][1], simplice[0]),
                        (edge1, points_lookup[simplice[1]][1], simplice[1]),
                    )
                )
            # Look for connecting edges within an edge
            elif abs(simplice[0] - simplice[1]) != 1:
                start_pnt = min(simplice.tolist())
                end_pnt = max(simplice.tolist())
                if not edge0 in trim_points:
                    trim_points[edge0] = [start_pnt, end_pnt]
                else:
                    trim_points[edge0].extend([start_pnt, end_pnt])
                connecting_edge_data.append(
                    (
                        (edge0, points_lookup[start_pnt][1], start_pnt),
                        (edge0, points_lookup[end_pnt][1], end_pnt),
                    )
                )

        trim_data = {}
        for edge, points in trim_points.items():
            s_points = sorted(points)
            f_points = []
            for i in range(0, len(s_points) - 1, 2):
                if s_points[i] != s_points[i + 1]:
                    f_points.append(tuple(s_points[i : i + 2]))
            trim_data[edge] = f_points

        connecting_edges = [
            Edge.make_line(
                edges[line[0][0]] @ line[0][1], edges[line[1][0]] @ line[1][1]
            )
            for line in connecting_edge_data
        ]
        trimmed_edges = [
            edges[edge].trim(
                points_lookup[trim_pair[0]][1], points_lookup[trim_pair[1]][1]
            )
            for edge, trim_pairs in trim_data.items()
            for trim_pair in trim_pairs
        ]
        hull_wire = Wire.make_wire(connecting_edges + trimmed_edges, sequenced=True)
        return hull_wire

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

        logger.debug("wire generated %d projected wires", len(output_wires))

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
            logger.debug(
                "projected, filtered and sorted wire list is of length %d",
                len(output_wires_distances),
            )
            output_wires = [w[0] for w in output_wires_distances]

        return output_wires


class DXF:
    """DXF file import and export functionality"""

    CURVE_TOLERANCE = 1e-9

    @staticmethod
    def _dxf_line(edge: Edge, msp: ezdxf.layouts.Modelspace, _plane: Plane):
        msp.add_line(
            edge.start_point().to_tuple(),
            edge.end_point().to_tuple(),
        )

    @staticmethod
    def _dxf_circle(edge: Edge, msp: ezdxf.layouts.Modelspace, _plane: Plane):
        geom = edge._geom_adaptor()
        circ = geom.Circle()

        radius = circ.Radius()
        center_location = circ.Location()

        circle_direction_y = circ.YAxis().Direction()
        circle_direction_z = circ.Axis().Direction()

        phi = circle_direction_y.AngleWithRef(gp_Dir(0, 1, 0), circle_direction_z)

        if circle_direction_z.XYZ().Z() > 0:
            angle1 = degrees(geom.FirstParameter() - phi)
            angle2 = degrees(geom.LastParameter() - phi)
        else:
            angle1 = -degrees(geom.LastParameter() - phi) + 180
            angle2 = -degrees(geom.FirstParameter() - phi) + 180

        if edge.is_closed():
            msp.add_circle(
                (center_location.X(), center_location.Y(), center_location.Z()), radius
            )
        else:
            msp.add_arc(
                (center_location.X(), center_location.Y(), center_location.Z()),
                radius,
                angle1,
                angle2,
            )

    @staticmethod
    def _dxf_ellipse(edge: Edge, msp: ezdxf.layouts.Modelspace, _plane: Plane):
        geom = edge._geom_adaptor()
        ellipse = geom.Ellipse()

        radius_minor = ellipse.MinorRadius()
        radius_major = ellipse.MajorRadius()

        center_location = ellipse.Location()
        ellipse_direction_x = ellipse.XAxis().Direction()
        xax = radius_major * ellipse_direction_x.XYZ()

        msp.add_ellipse(
            (center_location.X(), center_location.Y(), center_location.Z()),
            (xax.X(), xax.Y(), xax.Z()),
            radius_minor / radius_major,
            geom.FirstParameter(),
            geom.LastParameter(),
        )

    @staticmethod
    def _dxf_spline(edge: Edge, msp: ezdxf.layouts.Modelspace, plane: Plane):
        adaptor = edge._geom_adaptor()
        curve = GeomConvert.CurveToBSplineCurve_s(adaptor.Curve().Curve())

        spline = GeomConvert.SplitBSplineCurve_s(
            curve,
            adaptor.FirstParameter(),
            adaptor.LastParameter(),
            DXF.CURVE_TOLERANCE,
        )

        # need to apply the transform on the geometry level
        spline.Transform(plane.forward_transform.wrapped.Trsf())

        order = spline.Degree() + 1
        knots = list(spline.KnotSequence())
        poles = [(p.X(), p.Y(), p.Z()) for p in spline.Poles()]
        weights = (
            [spline.Weight(i) for i in range(1, spline.NbPoles() + 1)]
            if spline.IsRational()
            else None
        )

        if spline.IsPeriodic():
            pad = spline.NbKnots() - spline.LastUKnotIndex()
            poles += poles[:pad]

        dxf_spline = ezdxf.math.BSpline(poles, order, knots, weights)

        msp.add_spline().apply_construction_tool(dxf_spline)


class SVG:
    """SVG file import and export functionality"""

    _DISCRETIZATION_TOLERANCE = 1e-3

    _SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <svg
    xmlns:svg="http://www.w3.org/2000/svg"
    xmlns="http://www.w3.org/2000/svg"
    width="%(width)s"
    height="%(height)s"
    >
        <g transform="scale(%(unit_scale)s, -%(unit_scale)s)   translate(%(x_translate)s,%(y_translate)s)" stroke-width="%(stroke_width)s"  fill="none">
        <!-- hidden lines -->
        <g  stroke="rgb(%(hidden_color)s)" fill="none" stroke-dasharray="%(stroke_width)s,%(stroke_width)s" >
    %(hidden_content)s
        </g>

        <!-- solid lines -->
        <g  stroke="rgb(%(stroke_color)s)" fill="none">
    %(visible_content)s
        </g>
        </g>
    </svg>
    """

    _PATHTEMPLATE = '\t\t\t<path d="%s" />\n'

    @classmethod
    def make_svg_edge(cls, edge: Edge):
        """Creates an SVG edge from a OCCT edge"""

        memory_file = StringIO.StringIO()

        curve = edge._geom_adaptor()  # adapt the edge into curve
        start = curve.FirstParameter()
        end = curve.LastParameter()

        points = GCPnts_QuasiUniformDeflection(
            curve, SVG._DISCRETIZATION_TOLERANCE, start, end
        )

        if points.IsDone():
            point_it = (points.Value(i + 1) for i in range(points.NbPoints()))

            gp_pnt = next(point_it)
            memory_file.write(f"M{gp_pnt.X()},{gp_pnt.Y()} ")

            for gp_pnt in point_it:
                memory_file.write(f"L{gp_pnt.X()},{gp_pnt.Y()} ")

        return memory_file.getvalue()

    @classmethod
    def get_paths(cls, visible_shapes: list[Shape], hidden_shapes: list[Shape]):
        """Collects the visible and hidden edges from the object"""

        hidden_paths = []
        visible_paths = []

        for shape in visible_shapes:
            for edge in shape.edges():
                visible_paths.append(SVG.make_svg_edge(edge))

        for shape in hidden_shapes:
            for edge in shape.edges():
                hidden_paths.append(SVG.make_svg_edge(edge))

        return (hidden_paths, visible_paths)

    @classmethod
    def axes(cls, axes_scale: float) -> Compound:
        """The X, Y, Z axis object"""
        x_axis = Edge.make_line((0, 0, 0), (axes_scale, 0, 0))
        y_axis = Edge.make_line((0, 0, 0), (0, axes_scale, 0))
        z_axis = Edge.make_line((0, 0, 0), (0, 0, axes_scale))
        arrow_arc = Edge.make_spline(
            [(0, 0, 0), (-axes_scale / 20, axes_scale / 30, 0)],
            [(-1, 0, 0), (-1, 1.5, 0)],
        )
        arrow = arrow_arc.fuse(copy.copy(arrow_arc).mirror(Plane.XZ))
        x_label = (
            Compound.make_text(
                "X", font_size=axes_scale / 4, align=(Align.MIN, Align.CENTER)
            )
            .move(Location(x_axis @ 1))
            .edges()
        )
        y_label = (
            Compound.make_text(
                "Y", font_size=axes_scale / 4, align=(Align.MIN, Align.CENTER)
            )
            .rotate(Axis.Z, 90)
            .move(Location(y_axis @ 1))
            .edges()
        )
        z_label = (
            Compound.make_text(
                "Z", font_size=axes_scale / 4, align=(Align.CENTER, Align.MIN)
            )
            .rotate(Axis.Y, 90)
            .rotate(Axis.X, 90)
            .move(Location(z_axis @ 1))
            .edges()
        )
        axes = Edge.fuse(
            x_axis,
            y_axis,
            z_axis,
            arrow.moved(Location(x_axis @ 1)),
            arrow.rotate(Axis.Z, 90).moved(Location(y_axis @ 1)),
            arrow.rotate(Axis.Y, -90).moved(Location(z_axis @ 1)),
            *x_label,
            *y_label,
            *z_label,
        )
        return axes

    @classmethod
    def get_svg(
        cls,
        shape: Shape,
        viewport_origin: VectorLike,
        viewport_up: VectorLike = (0, 0, 1),
        look_at: VectorLike = None,
        svg_opts: dict = None,
    ) -> str:
        """get_svg

        Translate a shape to SVG text.

        Args:
            shape (Shape): target object
            viewport_origin (VectorLike): location of viewport
            viewport_up (VectorLike, optional): direction of the viewport y axis.
                Defaults to (0, 0, 1).
            look_at (VectorLike, optional): point to look at.
                Defaults to None (center of shape).

        SVG Options - e.g. svg_opts = {"pixel_scale":50}:

        Other Parameters:
            width (int): Viewport width in pixels. Defaults to 240.
            height (int): Viewport width in pixels. Defaults to 240.
            pixel_scale (float): Pixels per CAD unit.
                Defaults to None (calculated based on width & height).
            units (str): SVG document units. Defaults to "mm".
            margin_left (int): Defaults to 20.
            margin_top (int): Defaults to 20.
            show_axes (bool): Display an axis indicator. Defaults to True.
            axes_scale (float): Length of axis indicator in global units.
                Defaults to 1.0.
            stroke_width (float): Width of visible edges.
                Defaults to None (calculated based on unit_scale).
            stroke_color (tuple[int]): Visible stroke color. Defaults to RGB(0, 0, 0).
            hidden_color (tuple[int]): Hidden stroke color. Defaults to RBG(160, 160, 160).
            show_hidden (bool): Display hidden lines. Defaults to True.

        Returns:
            str: SVG text string
        """
        # Available options and their defaults
        defaults = {
            "width": 240,
            "height": 240,
            "pixel_scale": None,
            "units": "mm",
            "margin_left": 20,
            "margin_top": 20,
            "show_axes": True,
            "axes_scale": 1.0,
            "stroke_width": None,  # calculated based on unit_scale
            "stroke_color": (0, 0, 0),  # RGB 0-255
            "hidden_color": (160, 160, 160),  # RGB 0-255
            "show_hidden": True,
        }

        if svg_opts:
            defaults.update(svg_opts)

        width = float(defaults["width"])
        height = float(defaults["height"])
        margin_left = float(defaults["margin_left"])
        margin_top = float(defaults["margin_top"])
        show_axes = bool(defaults["show_axes"])
        stroke_color = tuple(defaults["stroke_color"])
        hidden_color = tuple(defaults["hidden_color"])
        show_hidden = bool(defaults["show_hidden"])

        # Setup the projector
        hidden_line_removal = HLRBRep_Algo()
        hidden_line_removal.Add(shape.wrapped)
        if show_axes:
            hidden_line_removal.Add(SVG.axes(defaults["axes_scale"]).wrapped)

        viewport_origin = Vector(viewport_origin)
        look_at = Vector(look_at) if look_at else shape.center()
        projection_dir: Vector = (viewport_origin - look_at).normalized()
        viewport_up = Vector(viewport_up).normalized()
        camera_coordinate_system = gp_Ax2()
        camera_coordinate_system.SetAxis(
            gp_Ax1(viewport_origin.to_pnt(), projection_dir.to_dir())
        )
        camera_coordinate_system.SetYDirection(viewport_up.to_dir())
        projector = HLRAlgo_Projector(camera_coordinate_system)

        hidden_line_removal.Projector(projector)
        hidden_line_removal.Update()
        hidden_line_removal.Hide()

        hlr_shapes = HLRBRep_HLRToShape(hidden_line_removal)

        # Create the visible edges
        visible_edges = []
        visible_sharp_edges = hlr_shapes.VCompound()
        if not visible_sharp_edges.IsNull():
            visible_edges.append(visible_sharp_edges)

        visible_smooth_edges = hlr_shapes.Rg1LineVCompound()
        if not visible_smooth_edges.IsNull():
            visible_edges.append(visible_smooth_edges)

        visible_contour_edges = hlr_shapes.OutLineVCompound()
        if not visible_contour_edges.IsNull():
            visible_edges.append(visible_contour_edges)

        # print("Visible Edges")
        # for edge_compound in visible_edges:
        #     for edge in Compound(edge_compound).edges():
        #         print(type(edge), edge.geom_type())
        # topo_abs: Any = geom_LUT[shapetype(edge)]
        # print(downcast(edge).GetType())
        # geom_LUT_EDGE[topo_abs(self.wrapped).GetType()]

        # Create the hidden edges
        hidden_edges = []
        hidden_sharp_edges = hlr_shapes.HCompound()
        if not hidden_sharp_edges.IsNull():
            hidden_edges.append(hidden_sharp_edges)

        hidden_contour_edges = hlr_shapes.OutLineHCompound()
        if not hidden_contour_edges.IsNull():
            hidden_edges.append(hidden_contour_edges)

        # Fix the underlying geometry - otherwise we will get segfaults
        for edge in visible_edges:
            BRepLib.BuildCurves3d_s(edge, TOLERANCE)
        for edge in hidden_edges:
            BRepLib.BuildCurves3d_s(edge, TOLERANCE)

        # convert to native shape objects
        visible_edges = list(map(Shape, visible_edges))
        hidden_edges = list(map(Shape, hidden_edges))
        (hidden_paths, visible_paths) = SVG.get_paths(visible_edges, hidden_edges)

        # get bounding box -- these are all in 2D space
        b_box = Compound.make_compound(hidden_edges + visible_edges).bounding_box()
        # width pixels for x, height pixels for y
        if defaults["pixel_scale"]:
            unit_scale = defaults["pixel_scale"]
            width = int(unit_scale * b_box.size.X + 2 * defaults["margin_left"])
            height = int(unit_scale * b_box.size.Y + 2 * defaults["margin_left"])
        else:
            unit_scale = min(width / b_box.size.X * 0.75, height / b_box.size.Y * 0.75)
        # compute amount to translate-- move the top left into view
        (x_translate, y_translate) = (
            (0 - b_box.min.X) + margin_left / unit_scale,
            (0 - b_box.max.Y) - margin_top / unit_scale,
        )

        # If the user did not specify a stroke width, calculate it based on the unit scale
        if defaults["stroke_width"]:
            stroke_width = float(defaults["stroke_width"])
        else:
            stroke_width = 1.0 / unit_scale

        # compute paths
        hidden_content = ""

        # Prevent hidden paths from being added if the user disabled them
        if show_hidden:
            for paths in hidden_paths:
                hidden_content += SVG._PATHTEMPLATE % paths

        visible_content = ""
        for paths in visible_paths:
            visible_content += SVG._PATHTEMPLATE % paths

        svg = SVG._SVG_TEMPLATE % (
            {
                "unit_scale": str(unit_scale),
                "stroke_width": str(stroke_width),
                "stroke_color": ",".join([str(x) for x in stroke_color]),
                "hidden_color": ",".join([str(x) for x in hidden_color]),
                "hidden_content": hidden_content,
                "visible_content": visible_content,
                "x_translate": str(x_translate),
                "y_translate": str(y_translate),
                "width": str(width),
                "height": str(height),
                "text_box_y": str(height - 30),
                "uom": defaults["units"],
            }
        )

        return svg


class ThreeMF:
    class CONTENT_TYPES(object):
        MODEL = "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"
        RELATION = "application/vnd.openxmlformats-package.relationships+xml"

    class SCHEMAS(object):
        CONTENT_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
        RELATION = "http://schemas.openxmlformats.org/package/2006/relationships"
        CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
        MODEL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"

    def __init__(
        self,
        shape: Shape,
        tolerance: float,
        angular_tolerance: float,
        unit: Unit = Unit.MILLIMETER,
    ):
        """
        Initialize the writer.
        Used to write the given Shape to a 3MF file.
        """
        self.unit = unit.name.lower()

        if isinstance(shape, Compound):
            shapes = list(shape)
        else:
            shapes = [shape]

        tessellations = [s.tessellate(tolerance, angular_tolerance) for s in shapes]
        # Remove shapes that did not tesselate
        self.tessellations = [t for t in tessellations if all(t)]

    def write_3mf(self, file_name: str):
        """
        Write to the given file.
        """

        try:
            import zlib

            compression = ZIP_DEFLATED
        except ImportError:
            compression = ZIP_STORED

        with ZipFile(file_name, "w", compression) as zf:
            zf.writestr("_rels/.rels", self._write_relationships())
            zf.writestr("[Content_Types].xml", self._write_content_types())
            zf.writestr("3D/3dmodel.model", self._write_3d())

    def _write_3d(self) -> str:
        no_meshes = len(self.tessellations)

        model = ET.Element(
            "model",
            {
                "xml:lang": "en-US",
                "xmlns": ThreeMF.SCHEMAS.CORE,
            },
            unit=self.unit,
        )

        # Add meta data
        ET.SubElement(
            model, "metadata", name="Application"
        ).text = "Build123d 3MF Exporter"
        ET.SubElement(
            model, "metadata", name="CreationDate"
        ).text = datetime.now().isoformat()

        resources = ET.SubElement(model, "resources")

        # Add all meshes to resources
        for i, tessellation in enumerate(self.tessellations):
            self._add_mesh(resources, str(i), tessellation)

        # Create a component of all meshes
        comp_object = ET.SubElement(
            resources,
            "object",
            id=str(no_meshes),
            name=f"Build123d Component",
            type="model",
        )
        components = ET.SubElement(comp_object, "components")

        # Add all meshes to the component
        for i in range(no_meshes):
            ET.SubElement(
                components,
                "component",
                objectid=str(i),
            )

        # Add the component to the build
        build = ET.SubElement(model, "build")
        ET.SubElement(build, "item", objectid=str(no_meshes))

        return ET.tostring(model, xml_declaration=True, encoding="utf-8")

    def _add_mesh(
        self,
        to: ET.Element,
        id: str,
        tessellation: tuple[list[Vector], list[tuple[int, int, int]]],
    ):
        object = ET.SubElement(
            to, "object", id=id, name=f"CadQuery Shape {id}", type="model"
        )
        mesh = ET.SubElement(object, "mesh")

        # add vertices
        vertices = ET.SubElement(mesh, "vertices")
        for v in tessellation[0]:
            ET.SubElement(vertices, "vertex", x=str(v.X), y=str(v.Y), z=str(v.Z))

        # add triangles
        volume = ET.SubElement(mesh, "triangles")
        for t in tessellation[1]:
            ET.SubElement(volume, "triangle", v1=str(t[0]), v2=str(t[1]), v3=str(t[2]))

    def _write_content_types(self) -> str:
        root = ET.Element("Types")
        root.set("xmlns", ThreeMF.SCHEMAS.CONTENT_TYPES)
        ET.SubElement(
            root,
            "Override",
            PartName="/3D/3dmodel.model",
            ContentType=ThreeMF.CONTENT_TYPES.MODEL,
        )
        ET.SubElement(
            root,
            "Override",
            PartName="/_rels/.rels",
            ContentType=ThreeMF.CONTENT_TYPES.RELATION,
        )

        return ET.tostring(root, xml_declaration=True, encoding="utf-8")

    def _write_relationships(self) -> str:
        root = ET.Element("Relationships")
        root.set("xmlns", ThreeMF.SCHEMAS.RELATION)
        ET.SubElement(
            root,
            "Relationship",
            Target="/3D/3dmodel.model",
            Id="rel-1",
            Type=ThreeMF.SCHEMAS.MODEL,
            TargetMode="Internal",
        )

        return ET.tostring(root, xml_declaration=True, encoding="utf-8")


class Joint(ABC):
    """Joint

    Abstract Base Joint class - used to join two components together

    Args:
        parent (Union[Solid, Compound]): object that joint to bound to
    """

    def __init__(self, label: str, parent: Union[Solid, Compound]):
        self.label = label
        self.parent = parent
        self.connected_to: Joint = None

    def connect_to(self, other: Joint, *args, **kwargs):  # pragma: no cover
        """Connect Joint self by repositioning other"""

        if not isinstance(other, Joint):
            raise TypeError(f"other must of type Joint not {type(other)}")

        relative_location = None
        try:
            relative_location = self.relative_to(other, *args, **kwargs)
        except TypeError:
            relative_location = other.relative_to(self, *args, **kwargs).inverse()

        other.parent.locate(self.parent.location * relative_location)

        self.connected_to = other

    @abstractmethod
    def relative_to(self, other: Joint, *args, **kwargs) -> Location:
        """Return relative location to another joint"""
        return NotImplementedError

    @property
    @abstractmethod
    def symbol(self) -> Compound:  # pragma: no cover
        """A CAD object positioned in global space to illustrate the joint"""
        return NotImplementedError


class RigidJoint(Joint):
    """RigidJoint

    A rigid joint fixes two components to one another.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        joint_location (Location): global location of joint
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol (XYZ indicator) as bound to part"""
        size = self.parent.bounding_box().diagonal / 12
        return SVG.axes(axes_scale=size).locate(
            self.parent.location * self.relative_location
        )

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound],
        joint_location: Location = Location(),
    ):
        self.relative_location = to_part.location.inverse() * joint_location
        to_part.joints[label] = self
        super().__init__(label, to_part)

    def relative_to(self, other: Joint, **kwargs) -> Location:
        """relative_to

        Return the relative position to move the other.

        Args:
            other (RigidJoint): joint to connect to
        """
        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        return self.relative_location * other.relative_location.inverse()


class RevoluteJoint(Joint):
    """RevoluteJoint

    Component rotates around axis like a hinge.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        axis (Axis): axis of rotation
        angle_reference (VectorLike, optional): direction normal to axis defining where
            angles will be measured from. Defaults to None.
        range (tuple[float, float], optional): (min,max) angle or joint. Defaults to (0, 360).

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
        ).move(self.parent.location * self.relative_axis.to_location())

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound],
        axis: Axis = Axis.Z,
        angle_reference: VectorLike = None,
        angular_range: tuple[float, float] = (0, 360),
    ):
        self.angular_range = angular_range
        if angle_reference:
            if not axis.is_normal(Axis((0, 0, 0), angle_reference)):
                raise ValueError("angle_reference must be normal to axis")
            self.angle_reference = Vector(angle_reference)
        else:
            self.angle_reference = Plane(origin=(0, 0, 0), z_dir=axis.direction).x_dir
        self.angle = None
        self.relative_axis = axis.located(to_part.location.inverse())
        to_part.joints[label] = self
        super().__init__(label, to_part)

    def relative_to(
        self, other: Joint, angle: float = None
    ):  # pylint: disable=arguments-differ
        """relative_to

        Return the relative location from this joint to the RigidJoint of another object
        - a hinge joint.

        Args:
            other (RigidJoint): joint to connect to
            angle (float, optional): angle within angular range. Defaults to minimum.

        Raises:
            TypeError: other must of type RigidJoint
            ValueError: angle out of range
        """
        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        angle = self.angular_range[0] if angle is None else angle
        if angle < self.angular_range[0] or angle > self.angular_range[1]:
            raise ValueError(f"angle ({angle}) must in range of {self.angular_range}")
        self.angle = angle
        # Avoid strange rotations when angle is zero by using 360 instead
        angle = 360.0 if angle == 0.0 else angle
        rotation = Location(
            Plane(
                origin=(0, 0, 0),
                x_dir=self.angle_reference.rotate(Axis.Z, angle),
                z_dir=(0, 0, 1),
            )
        )
        return (
            self.relative_axis.to_location()
            * rotation
            * other.relative_location.inverse()
        )


class LinearJoint(Joint):
    """LinearJoint

    Component moves along a single axis.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        axis (Axis): axis of linear motion
        range (tuple[float, float], optional): (min,max) position of joint.
            Defaults to (0, inf).
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
        ).move(self.parent.location * self.relative_axis.to_location())

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound],
        axis: Axis = Axis.Z,
        linear_range: tuple[float, float] = (0, inf),
    ):
        self.axis = axis
        self.linear_range = linear_range
        self.position = None
        self.relative_axis = axis.located(to_part.location.inverse())
        self.angle = None
        to_part.joints[label]: dict[str, Joint] = self
        super().__init__(label, to_part)

    @overload
    def relative_to(
        self, other: RigidJoint, position: float = None
    ):  # pylint: disable=arguments-differ
        """relative_to - RigidJoint

        Return the relative location from this joint to the RigidJoint of another object
        - a slider joint.

        Args:
            other (RigidJoint): joint to connect to
            position (float, optional): position within joint range. Defaults to middle.
        """

    @overload
    def relative_to(
        self, other: RevoluteJoint, position: float = None, angle: float = None
    ):  # pylint: disable=arguments-differ
        """relative_to - RevoluteJoint

        Return the relative location from this joint to the RevoluteJoint of another object
        - a pin slot joint.

        Args:
            other (RigidJoint): joint to connect to
            position (float, optional): position within joint range. Defaults to middle.
            angle (float, optional): angle within angular range. Defaults to minimum.
        """

    def relative_to(self, *args, **kwargs):  # pylint: disable=arguments-differ
        """Return the relative position of other to linear joint defined by self"""

        # Parse the input parameters
        other, position, angle = None, None, None
        if args:
            other = args[0]
            position = args[1] if len(args) >= 2 else position
            angle = args[2] if len(args) == 3 else angle

        if kwargs:
            other = kwargs["other"] if "other" in kwargs else other
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
        to_part (Union[Solid, Compound]): object to attach joint to
        axis (Axis): axis of rotation and linear motion
        angle_reference (VectorLike, optional): direction normal to axis defining where
            angles will be measured from. Defaults to None.
        linear_range (tuple[float, float], optional): (min,max) position of joint.
            Defaults to (0, inf).
        angular_range (tuple[float, float], optional): (min,max) angle of joint.
            Defaults to (0, 360).

    Raises:
        ValueError: angle_reference must be normal to axis
    """

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
        ).move(self.parent.location * self.relative_axis.to_location())

    # @property
    # def axis_location(self) -> Location:
    #     """Current global location of joint axis"""
    #     return self.parent.location * self.relative_axis.to_location()

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound],
        axis: Axis = Axis.Z,
        angle_reference: VectorLike = None,
        linear_range: tuple[float, float] = (0, inf),
        angular_range: tuple[float, float] = (0, 360),
    ):
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

    def relative_to(
        self, other: RigidJoint, position: float = None, angle: float = None
    ):  # pylint: disable=arguments-differ
        """relative_to - CylindricalJoint

        Return the relative location from this joint to the RigidJoint of another object
        - a sliding and rotating joint.

        Args:
            other (RigidJoint): joint to connect to
            position (float, optional): position within joint linear range. Defaults to middle.
            angle (float, optional): angle within rotational range.
                Defaults to angular_range minimum.

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
        to_part (Union[Solid, Compound]): object to attach joint to
        joint_location (Location): global location of joint
        angular_range
            (tuple[ tuple[float, float], tuple[float, float], tuple[float, float] ], optional):
            X, Y, Z angle (min, max) pairs. Defaults to ((0, 360), (0, 360), (0, 360)).
        angle_reference (Plane, optional): plane relative to part defining zero degrees of
            rotation. Defaults to Plane.XY.
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
        ).move(self.parent.location * self.relative_location)

    def __init__(
        self,
        label: str,
        to_part: Union[Solid, Compound],
        joint_location: Location = Location(),
        angular_range: tuple[
            tuple[float, float], tuple[float, float], tuple[float, float]
        ] = ((0, 360), (0, 360), (0, 360)),
        angle_reference: Plane = Plane.XY,
    ):
        """_summary_

        _extended_summary_

        Args:
            label (str): _description_
            to_part (Union[Solid, Compound]): _description_
            joint_location (Location, optional): _description_. Defaults to Location().
            angular_range
                (tuple[ tuple[float, float], tuple[float, float], tuple[float, float] ], optional):
                _description_. Defaults to ((0, 360), (0, 360), (0, 360)).
            angle_reference (Plane, optional): _description_. Defaults to Plane.XY.
        """
        self.relative_location = to_part.location.inverse() * joint_location
        to_part.joints[label] = self
        self.angular_range = angular_range
        self.angle_reference = angle_reference
        super().__init__(label, to_part)

    def relative_to(
        self, other: RigidJoint, angles: RotationLike = None
    ):  # pylint: disable=arguments-differ
        """relative_to - CylindricalJoint

        Return the relative location from this joint to the RigidJoint of another object

        Args:
            other (RigidJoint): joint to connect to
            angles (RotationLike, optional): orientation of other's parent relative to
                self. Defaults to the minimums of the angle ranges.

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
        ) * self.angle_reference.to_location()

        for i, rotations in zip(
            [0, 1, 2],
            [rotation.orientation.X, rotation.orientation.Y, rotation.orientation.Z],
        ):
            if not self.angular_range[i][0] <= rotations <= self.angular_range[i][1]:
                raise ValueError(
                    f"angles ({angles}) must in range of {self.angular_range}"
                )

        return self.relative_location * rotation * other.relative_location.inverse()


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

    for edge in edges:
        edges_in.Append(edge.wrapped)
    ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

    return [Wire(el) for el in wires_out]


def fix(obj: TopoDS_Shape) -> TopoDS_Shape:
    """Fix a TopoDS object to suitable specialized type

    Args:
      obj: TopoDS_Shape:

    Returns:

    """

    shape_fix = ShapeFix_Shape(obj)
    shape_fix.Perform()

    return downcast(shape_fix.Shape())


def shapetype(obj: TopoDS_Shape) -> TopAbs_ShapeEnum:
    """Return TopoDS_Shape's TopAbs_ShapeEnum"""
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


def polar(length: float, angle: float) -> tuple[float, float]:
    """Convert polar coordinates into cartesian coordinates"""
    return (length * cos(radians(angle)), length * sin(radians(angle)))
