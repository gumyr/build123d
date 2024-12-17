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
# pylint: disable=too-many-lines
# other pylint warning to temp remove:
#   too-many-arguments, too-many-locals, too-many-public-methods,
#   too-many-statements, too-many-instance-attributes, too-many-branches
import copy
import inspect
import itertools
import os
import platform
import sys
import types
import warnings
from abc import ABC, ABCMeta, abstractmethod
from io import BytesIO
from itertools import combinations
from math import radians, inf, pi, sin, cos, tan, copysign, ceil, floor, isclose
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
    TYPE_CHECKING,
)
from typing import cast as tcast
from typing_extensions import Self, Literal, deprecated

from anytree import NodeMixin, PreOrderIter, RenderTree
from IPython.lib.pretty import pretty, PrettyPrinter
from numpy import ndarray
from scipy.optimize import minimize
from scipy.spatial import ConvexHull  # pylint:disable=no-name-in-module

import OCP.GeomAbs as ga  # Geometry type enum
import OCP.TopAbs as ta  # Topology type enum
from OCP.Aspect import Aspect_TOL_SOLID
from OCP.BOPAlgo import BOPAlgo_GlueEnum

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
    BRepAlgoAPI_Section,
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
    BRepBuilderAPI_MakeShell,
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
from OCP.BRepFeat import BRepFeat_MakeDPrism, BRepFeat_SplitShape
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
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.Geom import (
    Geom_BezierCurve,
    Geom_BezierSurface,
    Geom_ConicalSurface,
    Geom_CylindricalSurface,
    Geom_Plane,
    Geom_Surface,
    Geom_TrimmedCurve,
    Geom_Line,
)
from OCP.GeomAdaptor import GeomAdaptor_Curve
from OCP.Geom2d import Geom2d_Curve, Geom2d_Line, Geom2d_TrimmedCurve
from OCP.Geom2dAPI import Geom2dAPI_InterCurveCurve
from OCP.GeomAbs import GeomAbs_C0, GeomAbs_Intersection, GeomAbs_JoinType
from OCP.GeomAPI import (
    GeomAPI_Interpolate,
    GeomAPI_PointsToBSpline,
    GeomAPI_PointsToBSplineSurface,
    GeomAPI_ProjectPointOnSurf,
    GeomAPI_ProjectPointOnCurve,
)
from OCP.GeomFill import (
    GeomFill_CorrectedFrenet,
    GeomFill_Frenet,
    GeomFill_TrihedronLaw,
)
from OCP.GeomLib import GeomLib_IsPlanarSurface
from OCP.gp import (
    gp_Ax1,
    gp_Ax2,
    gp_Ax3,
    gp_Circ,
    gp_Dir,
    gp_Dir2d,
    gp_Elips,
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
from OCP.LocOpe import LocOpe_DPrism
from OCP.NCollection import NCollection_Utf8String
from OCP.Precision import Precision
from OCP.Prs3d import Prs3d_IsoAspect
from OCP.Quantity import Quantity_Color
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds, ShapeAnalysis_Curve
from OCP.ShapeCustom import ShapeCustom, ShapeCustom_RestrictionParameters
from OCP.ShapeFix import (
    ShapeFix_Face,
    ShapeFix_Shape,
    ShapeFix_Solid,
    ShapeFix_Wireframe,
)
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

# for catching exceptions
from OCP.Standard import (
    Standard_Failure,
    Standard_NoSuchObject,
    Standard_ConstructionError,
)
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
    TColStd_HArray2OfReal,
)
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum
from OCP.TopExp import TopExp, TopExp_Explorer  # Topology explorer
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
    TopoDS_Edge,
    TopoDS_Wire,
)
from OCP.TopTools import (
    TopTools_HSequenceOfShape,
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_ListOfShape,
    TopTools_SequenceOfShape,
)
from build123d.build_enums import (
    Align,
    AngularDirection,
    CenterOf,
    FontStyle,
    FrameMethod,
    GeomType,
    Keep,
    Kind,
    PositionMode,
    Side,
    SortBy,
    Transition,
    Until,
)
from build123d.geometry import (
    DEG2RAD,
    TOLERANCE,
    Axis,
    BoundBox,
    Color,
    Location,
    Matrix,
    Plane,
    Vector,
    VectorLike,
    logger,
)


@property
def _topods_compound_dim(self) -> int | None:
    """The dimension of the shapes within the Compound - None if inconsistent"""
    sub_dims = {s.dim for s in get_top_level_topods_shapes(self)}
    return sub_dims.pop() if len(sub_dims) == 1 else None


def _topods_face_normal_at(self, surface_point: gp_Pnt) -> Vector:
    """normal_at point on surface"""
    surface = BRep_Tool.Surface_s(self)

    # project point on surface
    projector = GeomAPI_ProjectPointOnSurf(surface_point, surface)
    u_val, v_val = projector.LowerDistanceParameters()

    gp_pnt = gp_Pnt()
    normal = gp_Vec()
    BRepGProp_Face(self).Normal(u_val, v_val, gp_pnt, normal)

    return Vector(normal).normalized()


def apply_ocp_monkey_patches() -> None:
    """Applies monkey patches to TopoDS classes."""
    TopoDS_Compound.dim = _topods_compound_dim
    TopoDS_Face.dim = 2
    TopoDS_Face.normal_at = _topods_face_normal_at
    TopoDS_Shape.dim = None
    TopoDS_Shell.dim = 2
    TopoDS_Solid.dim = 3
    TopoDS_Vertex.dim = 0
    TopoDS_Edge.dim = 1
    TopoDS_Wire.dim = 1


apply_ocp_monkey_patches()


HASH_CODE_MAX = 2147483647  # max 32bit signed int, required by OCC.Core.HashCode


Shapes = Literal["Vertex", "Edge", "Wire", "Face", "Shell", "Solid", "Compound"]

TrimmingTool = Union[Plane, "Shell", "Face"]


def tuplify(obj: Any, dim: int) -> tuple:
    """Create a size tuple"""
    if obj is None:
        result = None
    elif isinstance(obj, (tuple, list)):
        result = tuple(obj)
    else:
        result = tuple([obj] * dim)
    return result


class _ClassMethodProxy:
    """
    A proxy for dynamically binding a class method to different classes.

    This descriptor allows a class method defined in one class to be reused
    in other classes while ensuring that the `cls` parameter refers to the
    correct class (the class on which the method is being called). This avoids
    issues where the method would otherwise always reference the original
    defining class.

    Attributes:
        method (classmethod): The class method to be proxied.

    Methods:
        __get__(instance, owner):
            Dynamically binds the proxied method to the calling class (`owner`).

    Example:
        class Mixin1D:
            @classmethod
            def extrude(cls, shape, direction):
                print(f"extrude called on {cls.__name__}")

        class Mixin2D:
            extrude = ClassMethodProxy(Mixin1D.extrude)

        class Mixin3D:
            extrude = ClassMethodProxy(Mixin1D.extrude)

        # Usage
        Mixin2D.extrude(None, None)  # Output: extrude called on Mixin2D
        Mixin3D.extrude(None, None)  # Output: extrude called on Mixin3D
    """

    def __init__(self, method):
        self.method = method

    def __get__(self, instance, owner):
        # Bind the method dynamically as a class method of `owner`
        return types.MethodType(self.method.__func__, owner)


class Mixin1D:
    """Methods to add to the Edge and Wire classes"""

    def __add__(self, other: Union[list[Shape], Shape]) -> Self:
        """fuse shape to wire/edge operator +"""

        # Convert `other` to list of base topods objects and filter out None values
        summands = [
            shape
            for o in (other if isinstance(other, (list, tuple)) else [other])
            if o is not None
            for shape in get_top_level_topods_shapes(o.wrapped)
        ]
        # If there is nothing to add return the original object
        if not summands:
            return self

        if not all(summand.dim == 1 for summand in summands):
            raise ValueError("Only shapes with the same dimension can be added")

        # Convert back to Edge/Wire objects now that it's safe to do so
        summands = [Mixin1D.cast(s) for s in summands]
        summand_edges = [e for summand in summands for e in summand.edges()]
        if self.wrapped is None:  # an empty object
            if len(summands) == 1:
                sum_shape = summands[0]
            else:
                try:
                    sum_shape = Wire(summand_edges)
                except Exception:
                    sum_shape = summands[0].fuse(*summands[1:])
                    if type(self).order == 4:
                        sum_shape = type(self)(sum_shape)
        else:
            try:
                sum_shape = Wire(self.edges() + summand_edges)
            except Exception:
                sum_shape = self.fuse(*summands)

        if SkipClean.clean and not isinstance(sum_shape, list):
            sum_shape = sum_shape.clean()

        # If there is only one Edge, return that
        sum_shape = sum_shape.edge() if len(sum_shape.edges()) == 1 else sum_shape

        return sum_shape

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Self:
        "Returns the right type of wrapper, given a OCCT object"

        # Extend the lookup table with additional entries
        constructor_lut = {
            ta.TopAbs_VERTEX: Vertex,
            ta.TopAbs_EDGE: Edge,
            ta.TopAbs_WIRE: Wire,
        }

        shape_type = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        return constructor_lut[shape_type](downcast(obj))

    @overload
    def split(
        self, tool: TrimmingTool, keep: Literal[Keep.TOP, Keep.BOTTOM]
    ) -> Optional[Self] | Optional[list[Self]]:
        """split and keep inside or outside"""

    @overload
    def split(self, tool: TrimmingTool, keep: Literal[Keep.BOTH]) -> tuple[
        Optional[Self] | Optional[list[Self]],
        Optional[Self] | Optional[list[Self]],
    ]:
        """split and keep inside and outside"""

    @overload
    def split(self, tool: TrimmingTool) -> Optional[Self] | Optional[list[Self]]:
        """split and keep inside (default)"""

    def split(self, tool: TrimmingTool, keep: Keep = Keep.TOP):
        """split

        Split this shape by the provided plane or face.

        Args:
            surface (Union[Plane,Face]): surface to segment shape
            keep (Keep, optional): which object(s) to save. Defaults to Keep.TOP.

        Returns:
            Shape: result of split
        Returns:
            Optional[Self] | Optional[list[Self]],
            Tuple[Optional[Self] | Optional[list[Self]]]: The result of the split operation.

            - **Keep.TOP**: Returns the top as a `Self` or `list[Self]`, or `None`
              if no top is found.
            - **Keep.BOTTOM**: Returns the bottom as a `Self` or `list[Self]`, or `None`
              if no bottom is found.
            - **Keep.BOTH**: Returns a tuple `(inside, outside)` where each element is
              either a `Self` or `list[Self]`, or `None` if no corresponding part is found.
        """
        shape_list = TopTools_ListOfShape()
        shape_list.Append(self.wrapped)

        # Define the splitting tool
        trim_tool = (
            BRepBuilderAPI_MakeFace(tool.wrapped).Face()  # Plane to Face
            if isinstance(tool, Plane)
            else tool.wrapped
        )
        tool_list = TopTools_ListOfShape()
        tool_list.Append(trim_tool)

        # Create the splitter algorithm
        splitter = BRepAlgoAPI_Splitter()

        # Set the shape to be split and the splitting tool (plane face)
        splitter.SetArguments(shape_list)
        splitter.SetTools(tool_list)

        # Perform the splitting operation
        splitter.Build()

        split_result = downcast(splitter.Shape())
        # Remove unnecessary TopoDS_Compound around single shape
        if isinstance(split_result, TopoDS_Compound):
            split_result = unwrap_topods_compound(split_result, True)

        if not isinstance(tool, Plane):
            # Create solids from the surfaces for sorting by thickening
            offset_builder = BRepOffset_MakeOffset()
            offset_builder.Initialize(
                tool.wrapped,
                Offset=0.1,
                Tol=1.0e-5,
                Intersection=True,
                Join=GeomAbs_Intersection,
                Thickening=True,
            )
            offset_builder.MakeOffsetShape()
            try:
                tool_thickened = downcast(offset_builder.Shape())
            except StdFail_NotDone as err:
                raise RuntimeError("Error determining top/bottom") from err

        tops, bottoms = [], []
        properties = GProp_GProps()
        for part in get_top_level_topods_shapes(split_result):
            sub_shape = self.__class__.cast(part)
            if isinstance(tool, Plane):
                is_up = tool.to_local_coords(sub_shape).center().Z >= 0
            else:
                # Intersect self and the thickened tool
                is_up_obj = _topods_bool_op(
                    (part,), (tool_thickened,), BRepAlgoAPI_Common()
                )
                # Calculate volume of intersection
                BRepGProp.VolumeProperties_s(is_up_obj, properties)
                is_up = properties.Mass() >= TOLERANCE
            (tops if is_up else bottoms).append(sub_shape)

        top = None if not tops else tops[0] if len(tops) == 1 else tops
        bottom = None if not bottoms else bottoms[0] if len(bottoms) == 1 else bottoms

        if keep == Keep.BOTH:
            return (top, bottom)
        if keep == Keep.TOP:
            return top
        if keep == Keep.BOTTOM:
            return bottom
        return None

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this Shape"""
        return Shape.get_shape_list(self, "Vertex")

    def vertex(self) -> Vertex:
        """Return the Vertex"""
        return Shape.get_single_shape(self, "Vertex")

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this Shape"""
        edge_list = Shape.get_shape_list(self, "Edge")
        return edge_list.filter_by(
            lambda e: BRep_Tool.Degenerated_s(e.wrapped), reverse=True
        )

    def edge(self) -> Edge:
        """Return the Edge"""
        return Shape.get_single_shape(self, "Edge")

    def wires(self) -> ShapeList[Wire]:
        """wires - all the wires in this Shape"""
        return Shape.get_shape_list(self, "Wire")

    def wire(self) -> Wire:
        """Return the Wire"""
        return Shape.get_single_shape(self, "Wire")

    def start_point(self) -> Vector:
        """The start point of this edge

        Note that circles may have identical start and end points.
        """
        curve = self.geom_adaptor()
        umin = curve.FirstParameter()

        return Vector(curve.Value(umin))

    def end_point(self) -> Vector:
        """The end point of this edge.

        Note that circles may have identical start and end points.
        """
        curve = self.geom_adaptor()
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
        curve = self.geom_adaptor()

        length = GCPnts_AbscissaPoint.Length_s(curve)
        return GCPnts_AbscissaPoint(
            curve, length * distance, curve.FirstParameter()
        ).Parameter()

    def tangent_at(
        self,
        position: Union[float, VectorLike] = 0.5,
        position_mode: PositionMode = PositionMode.PARAMETER,
    ) -> Vector:
        """tangent_at

        Find the tangent at a given position on the 1D shape where the position
        is either a float (or int) parameter or a point that lies on the shape.

        Args:
            position (Union[float, VectorLike]): distance, parameter value, or
                point on shape. Defaults to 0.5.
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.

        Raises:
            ValueError: invalid position

        Returns:
            Vector: tangent value
        """

        if isinstance(position, (float, int)):
            curve = self.geom_adaptor()
            if position_mode == PositionMode.PARAMETER:
                parameter = self.param_at(position)
            else:
                parameter = self.param_at(position / self.length)
        else:
            try:
                pnt = Vector(position)
            except Exception as exc:
                raise ValueError("position must be a float or a point") from exc
            # GeomAPI_ProjectPointOnCurve only works with Edges so find
            # the closest Edge if the shape has multiple Edges.
            my_edges: list[Edge] = self.edges()
            distances = [(e.distance_to(pnt), i) for i, e in enumerate(my_edges)]
            sorted_distances = sorted(distances, key=lambda x: x[0])
            closest_edge = my_edges[sorted_distances[0][1]]
            # Get the extreme of the parameter values for this Edge
            first: float = closest_edge.param_at(0)
            last: float = closest_edge.param_at(1)
            # Extract the Geom_Curve from the Shape
            curve = BRep_Tool.Curve_s(closest_edge.wrapped, first, last)
            projector = GeomAPI_ProjectPointOnCurve(pnt.to_pnt(), curve)
            parameter = projector.LowerDistanceParameter()

        tmp = gp_Pnt()
        res = gp_Vec()
        curve.D1(parameter, tmp, res)

        return Vector(gp_Dir(res))

    def tangent_angle_at(
        self,
        location_param: float = 0.5,
        position_mode: PositionMode = PositionMode.PARAMETER,
        plane: Plane = Plane.XY,
    ) -> float:
        """tangent_angle_at

        Compute the tangent angle at the specified location

        Args:
            location_param (float, optional): distance or parameter value. Defaults to 0.5.
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.
            plane (Plane, optional): plane line was constructed on. Defaults to Plane.XY.

        Returns:
            float: angle in degrees between 0 and 360
        """
        tan_vector = self.tangent_at(location_param, position_mode)
        angle = (plane.x_dir.get_signed_angle(tan_vector, plane.z_dir) + 360) % 360.0
        return angle

    def normal(self) -> Vector:
        """Calculate the normal Vector. Only possible for planar curves.

        :return: normal vector

        Args:

        Returns:

        """

        curve = self.geom_adaptor()
        gtype = self.geom_type

        if gtype == GeomType.CIRCLE:
            circ = curve.Circle()
            return_value = Vector(circ.Axis().Direction())
        elif gtype == GeomType.ELLIPSE:
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

    def common_plane(self, *lines: Union[Edge, Wire]) -> Union[None, Plane]:
        """common_plane

        Find the plane containing all the edges/wires (including self). If there
        is no common plane return None. If the edges are coaxial, select one
        of the infinite number of valid planes.

        Args:
            lines (sequence of Union[Edge,Wire]): edges in common with self

        Returns:
            Union[None, Plane]: Either the common plane or None
        """
        # pylint: disable=too-many-locals
        # Note: BRepLib_FindSurface is not helpful as it requires the
        # Edges to form a surface perimeter.
        points: list[Vector] = []
        all_lines: list[Edge, Wire] = [
            line for line in [self, *lines] if line is not None
        ]
        if any(not isinstance(line, (Edge, Wire)) for line in all_lines):
            raise ValueError("Only Edges or Wires are valid")

        result = None
        # Are they all co-axial - if so, select one of the infinite planes
        all_edges: list[Edge] = [e for l in all_lines for e in l.edges()]
        if all(e.geom_type == GeomType.LINE for e in all_edges):
            as_axis = [Axis(e @ 0, e % 0) for e in all_edges]
            if all(a0.is_coaxial(a1) for a0, a1 in combinations(as_axis, 2)):
                origin = as_axis[0].position
                x_dir = as_axis[0].direction
                z_dir = as_axis[0].to_plane().x_dir
                c_plane = Plane(origin, z_dir=z_dir)
                result = c_plane.shift_origin((0, 0))

        if result is None:  # not coaxial
            # Shorten any infinite lines (from converted Axis)
            normal_lines = list(filter(lambda line: line.length <= 1e50, all_lines))
            infinite_lines = filter(lambda line: line.length > 1e50, all_lines)
            # shortened_lines = [
            #     l.trim(0.4999999999, 0.5000000001) for l in infinite_lines
            # ]
            shortened_lines = [l.trim_to_length(0.5, 10) for l in infinite_lines]
            all_lines = normal_lines + shortened_lines

            for line in all_lines:
                num_points = 2 if line.geom_type == GeomType.LINE else 8
                points.extend(
                    [line.position_at(i / (num_points - 1)) for i in range(num_points)]
                )
            points = list(set(points))  # unique points
            extreme_areas = {}
            for subset in combinations(points, 3):
                vector1 = subset[1] - subset[0]
                vector2 = subset[2] - subset[0]
                area = 0.5 * (vector1.cross(vector2).length)
                extreme_areas[area] = subset
            # The points that create the largest area make the most accurate plane
            extremes = extreme_areas[sorted(list(extreme_areas.keys()))[-1]]

            # Create a plane from these points
            x_dir = (extremes[1] - extremes[0]).normalized()
            z_dir = (extremes[2] - extremes[0]).cross(x_dir)
            try:
                c_plane = Plane(origin=(sum(extremes) / 3), z_dir=z_dir)
                c_plane = c_plane.shift_origin((0, 0))
            except ValueError:
                # There is no valid common plane
                result = None
            else:
                # Are all of the points on the common plane
                common = all(c_plane.contains(p) for p in points)
                result = c_plane if common else None

        return result

    @property
    def length(self) -> float:
        """Edge or Wire length"""
        return GCPnts_AbscissaPoint.Length_s(self.geom_adaptor())

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
        geom = self.geom_adaptor()
        try:
            circ = geom.Circle()
        except (Standard_NoSuchObject, Standard_Failure) as err:
            raise ValueError("Shape could not be reduced to a circle") from err
        return circ.Radius()

    @property
    def is_forward(self) -> bool:
        """Does the Edge/Wire loop forward or reverse"""
        return self.wrapped.Orientation() == TopAbs_Orientation.TopAbs_FORWARD

    @property
    def is_closed(self) -> bool:
        """Are the start and end points equal?"""
        return BRep_Tool.IsClosed_s(self.wrapped)

    @property
    def volume(self) -> float:
        """volume - the volume of this Edge or Wire, which is always zero"""
        return 0.0

    def position_at(
        self, distance: float, position_mode: PositionMode = PositionMode.PARAMETER
    ) -> Vector:
        """Position At

        Generate a position along the underlying curve.

        Args:
            distance (float): distance or parameter value
            position_mode (PositionMode, optional): position calculation mode. Defaults to
                PositionMode.PARAMETER.

        Returns:
            Vector: position on the underlying curve
        """
        curve = self.geom_adaptor()

        if position_mode == PositionMode.PARAMETER:
            param = self.param_at(distance)
        else:
            param = self.param_at(distance / self.length)

        return Vector(curve.Value(param))

    def positions(
        self,
        distances: Iterable[float],
        position_mode: PositionMode = PositionMode.PARAMETER,
    ) -> list[Vector]:
        """Positions along curve

        Generate positions along the underlying curve

        Args:
            distances (Iterable[float]): distance or parameter values
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.

        Returns:
            list[Vector]: positions along curve
        """
        return [self.position_at(d, position_mode) for d in distances]

    def location_at(
        self,
        distance: float,
        position_mode: PositionMode = PositionMode.PARAMETER,
        frame_method: FrameMethod = FrameMethod.FRENET,
        planar: bool = False,
    ) -> Location:
        """Locations along curve

        Generate a location along the underlying curve.

        Args:
            distance (float): distance or parameter value
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.
            frame_method (FrameMethod, optional): moving frame calculation method.
                Defaults to FrameMethod.FRENET.
            planar (bool, optional): planar mode. Defaults to False.

        Returns:
            Location: A Location object representing local coordinate system
                at the specified distance.
        """
        curve = self.geom_adaptor()

        if position_mode == PositionMode.PARAMETER:
            param = self.param_at(distance)
        else:
            param = self.param_at(distance / self.length)

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
        position_mode: PositionMode = PositionMode.PARAMETER,
        frame_method: FrameMethod = FrameMethod.FRENET,
        planar: bool = False,
    ) -> list[Location]:
        """Locations along curve

        Generate location along the curve

        Args:
            distances (Iterable[float]): distance or parameter values
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.
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

    def __matmul__(self: Union[Edge, Wire], position: float) -> Vector:
        """Position on wire operator @"""
        return self.position_at(position)

    def __mod__(self: Union[Edge, Wire], position: float) -> Vector:
        """Tangent on wire operator %"""
        return self.tangent_at(position)

    def __xor__(self: Union[Edge, Wire], position: float) -> Location:
        """Location on wire operator ^"""
        return self.location_at(position)

    def offset_2d(
        self,
        distance: float,
        kind: Kind = Kind.ARC,
        side: Side = Side.BOTH,
        closed: bool = True,
    ) -> Union[Edge, Wire]:
        """2d Offset

        Offsets a planar edge/wire

        Args:
            distance (float): distance from edge/wire to offset
            kind (Kind, optional): offset corner transition. Defaults to Kind.ARC.
            side (Side, optional): side to place offset. Defaults to Side.BOTH.
            closed (bool, optional): if Side!=BOTH, close the LEFT or RIGHT
                offset. Defaults to True.
        Raises:
            RuntimeError: Multiple Wires generated
            RuntimeError: Unexpected result type

        Returns:
            Wire: offset wire
        """
        # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        kind_dict = {
            Kind.ARC: GeomAbs_JoinType.GeomAbs_Arc,
            Kind.INTERSECTION: GeomAbs_JoinType.GeomAbs_Intersection,
            Kind.TANGENT: GeomAbs_JoinType.GeomAbs_Tangent,
        }
        line = self if isinstance(self, Wire) else Wire([self])

        # Avoiding a bug when the wire contains a single Edge
        if len(line.edges()) == 1:
            edge = line.edges()[0]
            edges = [edge.trim(0.0, 0.5), edge.trim(0.5, 1.0)]
            topods_wire = Wire(edges).wrapped
        else:
            topods_wire = line.wrapped

        offset_builder = BRepOffsetAPI_MakeOffset()
        offset_builder.Init(kind_dict[kind])
        # offset_builder.SetApprox(True)
        offset_builder.AddWire(topods_wire)
        offset_builder.Perform(distance)

        obj = downcast(offset_builder.Shape())
        if isinstance(obj, TopoDS_Compound):
            obj = unwrap_topods_compound(obj, fully=True)
        if isinstance(obj, TopoDS_Wire):
            offset_wire = Wire(obj)
        else:  # Likely multiple Wires were generated
            raise RuntimeError("Unexpected result type")

        if side != Side.BOTH:
            # Find and remove the end arcs
            offset_edges = offset_wire.edges()
            edges_to_keep = [[], [], []]
            i = 0
            for edge in offset_edges:
                if edge.geom_type == GeomType.CIRCLE and (
                    edge.arc_center == line.position_at(0)
                    or edge.arc_center == line.position_at(1)
                ):
                    i += 1
                else:
                    edges_to_keep[i].append(edge)
            edges_to_keep[0] += edges_to_keep[2]
            wires = [Wire(edges) for edges in edges_to_keep[0:2]]
            centers = [w.position_at(0.5) for w in wires]
            angles = [
                line.tangent_at(0).get_signed_angle(c - line.position_at(0))
                for c in centers
            ]
            if side == Side.LEFT:
                offset_wire = wires[int(angles[0] > angles[1])]
            else:
                offset_wire = wires[int(angles[0] <= angles[1])]

            if closed:
                self0 = line.position_at(0)
                self1 = line.position_at(1)
                end0 = offset_wire.position_at(0)
                end1 = offset_wire.position_at(1)
                if (self0 - end0).length - abs(distance) <= TOLERANCE:
                    edge0 = Edge.make_line(self0, end0)
                    edge1 = Edge.make_line(self1, end1)
                else:
                    edge0 = Edge.make_line(self0, end1)
                    edge1 = Edge.make_line(self1, end0)
                offset_wire = Wire(line.edges() + offset_wire.edges() + [edge0, edge1])

        offset_edges = offset_wire.edges()
        return offset_edges[0] if len(offset_edges) == 1 else offset_wire

    def perpendicular_line(
        self, length: float, u_value: float, plane: Plane = Plane.XY
    ) -> Edge:
        """perpendicular_line

        Create a line on the given plane perpendicular to and centered on beginning of self

        Args:
            length (float): line length
            u_value (float): position along line between 0.0 and 1.0
            plane (Plane, optional): plane containing perpendicular line. Defaults to Plane.XY.

        Returns:
            Edge: perpendicular line
        """
        start = self.position_at(u_value)
        local_plane = Plane(
            origin=start, x_dir=self.tangent_at(u_value), z_dir=plane.z_dir
        )
        line = Edge.make_line(
            start + local_plane.y_dir * length / 2,
            start - local_plane.y_dir * length / 2,
        )
        return line

    def project(
        self, face: Face, direction: VectorLike, closest: bool = True
    ) -> Union[Mixin1D, ShapeList[Mixin1D]]:
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
        shapes: TopoDS_Compound = bldr.Shape()

        # select the closest projection if requested
        return_value: Union[Mixin1D, list[Mixin1D]]

        if closest:
            dist_calc = BRepExtrema_DistShapeShape()
            dist_calc.LoadS1(self.wrapped)

            min_dist = inf

            # for shape in shapes:
            for shape in get_top_level_topods_shapes(shapes):
                dist_calc.LoadS2(shape)
                dist_calc.Perform()
                dist = dist_calc.Value()

                if dist < min_dist:
                    min_dist = dist
                    return_value = Mixin1D.cast(shape)

        else:
            return_value = ShapeList(
                Mixin1D.cast(shape) for shape in get_top_level_topods_shapes(shapes)
            )

        return return_value

    def project_to_viewport(
        self,
        viewport_origin: VectorLike,
        viewport_up: VectorLike = (0, 0, 1),
        look_at: VectorLike = None,
    ) -> tuple[ShapeList[Edge], ShapeList[Edge]]:
        """project_to_viewport

        Project a shape onto a viewport returning visible and hidden Edges.

        Args:
            viewport_origin (VectorLike): location of viewport
            viewport_up (VectorLike, optional): direction of the viewport y axis.
                Defaults to (0, 0, 1).
            look_at (VectorLike, optional): point to look at.
                Defaults to None (center of shape).

        Returns:
            tuple[ShapeList[Edge],ShapeList[Edge]]: visible & hidden Edges
        """

        def extract_edges(compound):
            edges = []  # List to store the extracted edges

            # Create a TopExp_Explorer to traverse the sub-shapes of the compound
            explorer = TopExp_Explorer(compound, TopAbs_ShapeEnum.TopAbs_EDGE)

            # Loop through the sub-shapes and extract edges
            while explorer.More():
                edge = downcast(explorer.Current())
                edges.append(edge)
                explorer.Next()

            return edges

        # Setup the projector
        hidden_line_removal = HLRBRep_Algo()
        hidden_line_removal.Add(self.wrapped)

        viewport_origin = Vector(viewport_origin)
        look_at = Vector(look_at) if look_at else self.center()
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
        for edges in [
            hlr_shapes.VCompound(),
            hlr_shapes.Rg1LineVCompound(),
            hlr_shapes.OutLineVCompound(),
        ]:
            if not edges.IsNull():
                visible_edges.extend(extract_edges(downcast(edges)))

        # Create the hidden edges
        hidden_edges = []
        for edges in [
            hlr_shapes.HCompound(),
            hlr_shapes.OutLineHCompound(),
            hlr_shapes.Rg1LineHCompound(),
        ]:
            if not edges.IsNull():
                hidden_edges.extend(extract_edges(downcast(edges)))

        # Fix the underlying geometry - otherwise we will get segfaults
        for edge in visible_edges:
            BRepLib.BuildCurves3d_s(edge, TOLERANCE)
        for edge in hidden_edges:
            BRepLib.BuildCurves3d_s(edge, TOLERANCE)

        # convert to native shape objects
        visible_edges = ShapeList(Edge(e) for e in visible_edges)
        hidden_edges = ShapeList(Edge(e) for e in hidden_edges)

        return (visible_edges, hidden_edges)

    @classmethod
    def extrude(
        cls, obj: Shape, direction: VectorLike
    ) -> Edge | Face | Shell | Solid | Compound:
        """extrude

        Extrude a Shape in the provided direction.
        * Vertices generate Edges
        * Edges generate Faces
        * Wires generate Shells
        * Faces generate Solids
        * Shells generate Compounds

        Args:
            direction (VectorLike): direction and magnitude of extrusion

        Raises:
            ValueError: Unsupported class
            RuntimeError: Generated invalid result

        Returns:
            Union[Edge, Face, Shell, Solid, Compound]: extruded shape
        """
        return cls.cast(_extrude_topods_shape(obj.wrapped, direction))


class Mixin2D:
    """Additional methods to add to Face and Shell class"""

    project_to_viewport = Mixin1D.project_to_viewport
    extrude = _ClassMethodProxy(Mixin1D.extrude)
    split = Mixin1D.split

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Self:
        "Returns the right type of wrapper, given a OCCT object"

        # define the shape lookup table for casting
        constructor_lut = {
            ta.TopAbs_VERTEX: Vertex,
            ta.TopAbs_EDGE: Edge,
            ta.TopAbs_WIRE: Wire,
            ta.TopAbs_FACE: Face,
            ta.TopAbs_SHELL: Shell,
        }

        shape_type = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        return constructor_lut[shape_type](downcast(obj))

    vertices = Mixin1D.vertices
    vertex = Mixin1D.vertex
    edges = Mixin1D.edges
    edge = Mixin1D.edge
    wires = Mixin1D.wires
    wire = Mixin1D.wire

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this Shape"""
        return Shape.get_shape_list(self, "Face")

    def face(self) -> Face:
        """Return the Face"""
        return Shape.get_single_shape(self, "Face")

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this Shape"""
        return Shape.get_shape_list(self, "Shell")

    def shell(self) -> Shell:
        """Return the Shell"""
        return Shape.get_single_shape(self, "Shell")

    def __neg__(self) -> Self:
        """Reverse normal operator -"""
        new_surface = copy.deepcopy(self)
        new_surface.wrapped = downcast(self.wrapped.Complemented())

        return new_surface

    def offset(self, amount: float) -> Self:
        """Return a copy of self moved along the normal by amount"""
        return copy.deepcopy(self).moved(Location(self.normal_at() * amount))


class Mixin3D:
    """Additional methods to add to 3D Shape classes"""

    project_to_viewport = Mixin1D.project_to_viewport
    extrude = _ClassMethodProxy(Mixin1D.extrude)
    split = Mixin1D.split

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Self:
        "Returns the right type of wrapper, given a OCCT object"

        # define the shape lookup table for casting
        constructor_lut = {
            ta.TopAbs_VERTEX: Vertex,
            ta.TopAbs_EDGE: Edge,
            ta.TopAbs_WIRE: Wire,
            ta.TopAbs_FACE: Face,
            ta.TopAbs_SHELL: Shell,
            ta.TopAbs_SOLID: Solid,
        }

        shape_type = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        return constructor_lut[shape_type](downcast(obj))

    vertices = Mixin1D.vertices
    vertex = Mixin1D.vertex
    edges = Mixin1D.edges
    edge = Mixin1D.edge
    wires = Mixin1D.wires
    wire = Mixin1D.wire
    faces = Mixin2D.faces
    face = Mixin2D.face
    shells = Mixin2D.shells
    shell = Mixin2D.shell

    def solids(self) -> ShapeList[Solid]:
        """solids - all the solids in this Shape"""
        return Shape.get_shape_list(self, "Solid")

    def solid(self) -> Solid:
        """Return the Solid"""
        return Shape.get_single_shape(self, "Solid")

    def fillet(self, radius: float, edge_list: Iterable[Edge]) -> Self:
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

        try:
            new_shape = self.__class__(fillet_builder.Shape())
            if not new_shape.is_valid():
                raise Standard_Failure
        except (StdFail_NotDone, Standard_Failure) as err:
            raise ValueError(
                f"Failed creating a fillet with radius of {radius}, try a smaller value"
                f" or use max_fillet() to find the largest valid fillet radius"
            ) from err

        return new_shape

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

            fillet_builder = BRepFilletAPI_MakeFillet(self.wrapped)

            for native_edge in native_edges:
                fillet_builder.Add(window_mid, native_edge)

            # Do these numbers work? - if not try with the smaller window
            try:
                new_shape = self.__class__(fillet_builder.Shape())
                if not new_shape.is_valid():
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

        native_edges = [e.wrapped for e in edge_list]

        # Unfortunately, MacOS doesn't support the StdFail_NotDone exception so platform
        # specific exceptions are required.
        if platform.system() == "Darwin":
            fillet_exception = Standard_Failure
        else:
            fillet_exception = StdFail_NotDone

        max_radius = __max_fillet(0.0, 2 * self.bounding_box().diagonal, 0)

        return max_radius

    def chamfer(
        self,
        length: float,
        length2: Optional[float],
        edge_list: Iterable[Edge],
        face: Face = None,
    ) -> Self:
        """Chamfer

        Chamfers the specified edges of this solid.

        Args:
            length (float): length > 0, the length (length) of the chamfer
            length2 (Optional[float]): length2 > 0, optional parameter for asymmetrical
                chamfer. Should be `None` if not required.
            edge_list (Iterable[Edge]): a list of Edge objects, which must belong to
                this solid
            face (Face): identifies the side where length is measured. The edge(s) must be
                part of the face

        Returns:
            Self:  Chamfered solid
        """
        if face:
            if any((edge for edge in edge_list if edge not in face.edges())):
                raise ValueError("Some edges are not part of the face")

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
            if face:
                topo_face = face.wrapped
            else:
                topo_face = edge_face_map.FindFromKey(native_edge).First()

            chamfer_builder.Add(
                distance1, distance2, native_edge, TopoDS.Face_s(topo_face)
            )  # NB: edge_face_map return a generic TopoDS_Shape

        try:
            new_shape = self.__class__(chamfer_builder.Shape())
            if not new_shape.is_valid():
                raise Standard_Failure
        except (StdFail_NotDone, Standard_Failure) as err:
            raise ValueError(
                "Failed creating a chamfer, try a smaller length value(s)"
            ) from err

        return new_shape

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
            calc_function = Shape.shape_properties_LUT[shapetype(self.wrapped)]
            if calc_function:
                calc_function(self.wrapped, properties)
                middle = Vector(properties.CentreOfMass())
            else:
                raise NotImplementedError
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    def hollow(
        self,
        faces: Optional[Iterable[Face]],
        thickness: float,
        tolerance: float = 0.0001,
        kind: Kind = Kind.ARC,
    ) -> Solid:
        """Hollow

        Return the outer shelled solid of self.

        Args:
            faces (Optional[Iterable[Face]]): faces to be removed,
            which must be part of the solid. Can be an empty list.
            thickness (float): shell thickness - positive shells outwards, negative
                shells inwards.
            tolerance (float, optional): modelling tolerance of the method. Defaults to 0.0001.
            kind (Kind, optional): intersection type. Defaults to Kind.ARC.

        Raises:
            ValueError: Kind.TANGENT not supported

        Returns:
            Solid: A hollow solid.
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
            openings (Optional[Iterable[Face]]): faces to be removed,
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

        try:
            offset_occt_solid = offset_builder.Shape()
        except (StdFail_NotDone, Standard_Failure) as err:
            raise RuntimeError(
                "offset Error, an alternative kind may resolve this error"
            ) from err

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
            faces = [Face(p[0], p[1:]) for p in sorted_profiles]
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
        parent (Compound, optional): assembly parent. Defaults to None.

    Attributes:
        wrapped (TopoDS_Shape): the OCP object
        label (str): user assigned label
        color (Color): object color
        joints (dict[str:Joint]): dictionary of joints bound to this object (Solid only)
        children (Shape): list of assembly children of this object (Compound only)
        topo_parent (Shape): assembly parent of this object

    """

    # pylint: disable=too-many-instance-attributes, too-many-public-methods

    _dim = None

    shape_LUT = {
        ta.TopAbs_VERTEX: "Vertex",
        ta.TopAbs_EDGE: "Edge",
        ta.TopAbs_WIRE: "Wire",
        ta.TopAbs_FACE: "Face",
        ta.TopAbs_SHELL: "Shell",
        ta.TopAbs_SOLID: "Solid",
        ta.TopAbs_COMPOUND: "Compound",
        ta.TopAbs_COMPSOLID: "CompSolid",
    }

    shape_properties_LUT = {
        ta.TopAbs_VERTEX: None,
        ta.TopAbs_EDGE: BRepGProp.LinearProperties_s,
        ta.TopAbs_WIRE: BRepGProp.LinearProperties_s,
        ta.TopAbs_FACE: BRepGProp.SurfaceProperties_s,
        ta.TopAbs_SHELL: BRepGProp.SurfaceProperties_s,
        ta.TopAbs_SOLID: BRepGProp.VolumeProperties_s,
        ta.TopAbs_COMPOUND: BRepGProp.VolumeProperties_s,
        ta.TopAbs_COMPSOLID: BRepGProp.VolumeProperties_s,
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
        ta.TopAbs_COMPSOLID: TopoDS.CompSolid_s,
    }

    geom_LUT_EDGE: Dict[ga.GeomAbs_CurveType, GeomType] = {
        ga.GeomAbs_Line: GeomType.LINE,
        ga.GeomAbs_Circle: GeomType.CIRCLE,
        ga.GeomAbs_Ellipse: GeomType.ELLIPSE,
        ga.GeomAbs_Hyperbola: GeomType.HYPERBOLA,
        ga.GeomAbs_Parabola: GeomType.PARABOLA,
        ga.GeomAbs_BezierCurve: GeomType.BEZIER,
        ga.GeomAbs_BSplineCurve: GeomType.BSPLINE,
        ga.GeomAbs_OffsetCurve: GeomType.OFFSET,
        ga.GeomAbs_OtherCurve: GeomType.OTHER,
    }
    geom_LUT_FACE: Dict[ga.GeomAbs_SurfaceType, GeomType] = {
        ga.GeomAbs_Plane: GeomType.PLANE,
        ga.GeomAbs_Cylinder: GeomType.CYLINDER,
        ga.GeomAbs_Cone: GeomType.CONE,
        ga.GeomAbs_Sphere: GeomType.SPHERE,
        ga.GeomAbs_Torus: GeomType.TORUS,
        ga.GeomAbs_BezierSurface: GeomType.BEZIER,
        ga.GeomAbs_BSplineSurface: GeomType.BSPLINE,
        ga.GeomAbs_SurfaceOfRevolution: GeomType.REVOLUTION,
        ga.GeomAbs_SurfaceOfExtrusion: GeomType.EXTRUSION,
        ga.GeomAbs_OffsetSurface: GeomType.OFFSET,
        ga.GeomAbs_OtherSurface: GeomType.OTHER,
    }
    _transModeDict = {
        Transition.TRANSFORMED: BRepBuilderAPI_Transformed,
        Transition.ROUND: BRepBuilderAPI_RoundCorner,
        Transition.RIGHT: BRepBuilderAPI_RightCorner,
    }

    def __init__(
        self,
        obj: TopoDS_Shape = None,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        self.wrapped = downcast(obj) if obj is not None else None
        self.for_construction = False
        self.label = label
        self._color = color

        # parent must be set following children as post install accesses children
        self.parent = parent

        # Extracted objects like Vertices and Edges may need to know where they came from
        self.topo_parent: Shape = None

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

    @property
    def color(self) -> Union[None, Color]:
        """Get the shape's color.  If it's None, get the color of the nearest
        ancestor, assign it to this Shape and return this value."""
        # Find the correct color for this node
        if self._color is None:
            # Find parent color
            current_node = self
            while current_node is not None:
                parent_color = current_node._color
                if parent_color is not None:
                    break
                current_node = current_node.parent
            node_color = parent_color
        else:
            node_color = self._color
        self._color = node_color  # Set the node's color for next time
        return node_color

    @property
    def is_planar_face(self) -> bool:
        """Is the shape a planar face even though its geom_type may not be PLANE"""
        if self.wrapped is None or not isinstance(self.wrapped, TopoDS_Face):
            return False
        surface = BRep_Tool.Surface_s(self.wrapped)
        is_face_planar = GeomLib_IsPlanarSurface(surface, TOLERANCE)
        return is_face_planar.IsPlanar()

    @color.setter
    def color(self, value):
        """Set the shape's color"""
        self._color = value

    def copy_attributes_to(self, target: Shape, exceptions: Iterable[str] = None):
        """Copy common object attributes to target

        Note that preset attributes of target will not be overridden.

        Args:
            target (Shape): object to gain attributes
            exceptions (Iterable[str], optional): attributes not to copy

        Raises:
            ValueError: invalid attribute
        """
        # Find common attributes and eliminate exceptions
        attrs1 = set(self.__dict__.keys())
        attrs2 = set(target.__dict__.keys())
        common_attrs = attrs1 & attrs2
        if exceptions is not None:
            common_attrs -= set(exceptions)

        for attr in common_attrs:
            # Copy the attribute only if the target's attribute not set
            if not getattr(target, attr):
                setattr(target, attr, getattr(self, attr))
            # Attach joints to the new part
            if attr == "joints":
                joint: Joint
                for joint in target.joints.values():
                    joint.parent = target

    @property
    def is_manifold(self) -> bool:
        """is_manifold

        Check if each edge in the given Shape has exactly two faces associated with it
        (skipping degenerate edges). If so, the shape is manifold.

        Returns:
            bool: is the shape manifold or water tight
        """
        # Extract one or more (if a Compound) shape from self
        shape_stack = get_top_level_topods_shapes(self.wrapped)
        results = []

        while shape_stack:
            shape = shape_stack.pop(0)

            result = True
            # Create an empty indexed data map to store the edges and their corresponding faces.
            shape_map = TopTools_IndexedDataMapOfShapeListOfShape()

            # Fill the map with edges and their associated faces in the given shape. Each edge in
            # the map is associated with a list of faces that share that edge.
            TopExp.MapShapesAndAncestors_s(
                # shape.wrapped, ta.TopAbs_EDGE, ta.TopAbs_FACE, shape_map
                shape,
                ta.TopAbs_EDGE,
                ta.TopAbs_FACE,
                shape_map,
            )

            # Iterate over the edges in the map and checks if each edge is non-degenerate and has
            # exactly two faces associated with it.
            for i in range(shape_map.Extent()):
                # Access each edge in the map sequentially
                edge = downcast(shape_map.FindKey(i + 1))

                vertex0 = TopoDS_Vertex()
                vertex1 = TopoDS_Vertex()

                # Extract the two vertices of the current edge and stores them in vertex0/1.
                TopExp.Vertices_s(edge, vertex0, vertex1)

                # Check if both vertices are null and if they are the same vertex. If so, the
                # edge is considered degenerate (i.e., has zero length), and it is skipped.
                if vertex0.IsNull() and vertex1.IsNull() and vertex0.IsSame(vertex1):
                    continue

                # Check if the current edge has exactly two faces associated with it. If not,
                # it means the edge is not shared by exactly two faces, indicating that the
                # shape is not manifold.
                if shape_map.FindFromIndex(i + 1).Extent() != 2:
                    result = False
                    break
            results.append(result)

        return all(results)

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

        obj_type = Shape.shape_LUT[shape.ShapeType()]
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
        # pylint: disable=cell-var-from-loop
        size_tuples_per_level = [
            list(filter(lambda ll: ll[0] == l, size_tuples))
            for l in range(root_node.height + 1)
        ]
        max_sizes_per_level = [
            max(4, max(l[1] for l in level)) for level in size_tuples_per_level
        ]
        level_sizes_per_level = [
            l + i * 4 for i, l in enumerate(reversed(max_sizes_per_level))
        ]
        tree_label_width = max(level_sizes_per_level) + 1

        # Build the tree line by line
        result = ""
        for pre, _fill, node in RenderTree(root_node):
            treestr = f"{pre}{node.label}".ljust(tree_label_width)
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
        # if isinstance(self, Compound) and self.children:
        if (
            self.wrapped is not None
            and isinstance(self.wrapped, TopoDS_Compound)
            and self.children
        ):
            show_center = False if show_center is None else show_center
            result = Shape._show_tree(self, show_center)
        else:
            tree = Shape._build_tree(
                self.wrapped, tree=[], limit=Shape.inverse_shape_LUT[limit_class]
            )
            show_center = True if show_center is None else show_center
            result = Shape._show_tree(tree[0], show_center)
        return result

    def __add__(self, other: Union[list[Shape], Shape]) -> Self:
        """fuse shape to self operator +"""
        # Convert `other` to list of base objects and filter out None values
        summands = [
            shape
            for o in (other if isinstance(other, (list, tuple)) else [other])
            if o is not None
            for shape in o.get_top_level_shapes()
        ]
        # If there is nothing to add return the original object
        if not summands:
            return self

        # Check that all dimensions are the same
        addend_dim = self._dim
        if addend_dim is None:
            raise ValueError("Dimensions of objects to add to are inconsistent")

        if not all(summand._dim == addend_dim for summand in summands):
            raise ValueError("Only shapes with the same dimension can be added")

        if self.wrapped is None:  # an empty object
            if len(summands) == 1:
                sum_shape = summands[0]
            else:
                sum_shape = summands[0].fuse(*summands[1:])
        else:
            sum_shape = self.fuse(*summands)

        if SkipClean.clean and not isinstance(sum_shape, list):
            sum_shape = sum_shape.clean()

        return sum_shape

    def __sub__(self, other: Union[Shape, Iterable[Shape]]) -> Self:
        """cut shape from self operator -"""

        if self.wrapped is None:
            raise ValueError("Cannot subtract shape from empty compound")

        # Convert `other` to list of base objects and filter out None values
        subtrahends = [
            shape
            for o in (other if isinstance(other, (list, tuple)) else [other])
            if o is not None
            for shape in o.get_top_level_shapes()
        ]
        # If there is nothing to subtract return the original object
        if not subtrahends:
            return self

        # Check that all dimensions are the same
        minuend_dim = self._dim
        if minuend_dim is None:
            raise ValueError("Dimensions of objects to subtract from are inconsistent")

        # Check that the operation is valid
        subtrahend_dims = [s._dim for s in subtrahends]
        if any(d < minuend_dim for d in subtrahend_dims):
            raise ValueError(
                f"Only shapes with equal or greater dimension can be subtracted: "
                f"not {type(self).__name__} ({minuend_dim}D) and "
                f"{type(other).__name__} ({min(subtrahend_dims)}D)"
            )

        # Do the actual cut operation
        difference = self.cut(*subtrahends)

        return difference

    def __and__(self, other: Shape) -> Self:
        """intersect shape with self operator &"""
        others = other if isinstance(other, (list, tuple)) else [other]

        if self.wrapped is None or (isinstance(other, Shape) and other.wrapped is None):
            raise ValueError("Cannot intersect shape with empty compound")
        new_shape = self.intersect(*others)

        if new_shape.wrapped is not None and SkipClean.clean:
            new_shape = new_shape.clean()

        return new_shape

    def __rmul__(self, other):
        """right multiply for positioning operator *"""
        if not (
            isinstance(other, (list, tuple))
            and all(isinstance(o, (Location, Plane)) for o in other)
        ):
            raise ValueError(
                "shapes can only be multiplied list of locations or planes"
            )
        return [loc * self for loc in other]

    @abstractmethod
    def center(self) -> Vector:
        """All of the derived classes from Shape need a center method"""

    def clean(self) -> Self:
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
        except Exception:
            warnings.warn(f"Unable to clean {self}", stacklevel=2)
        return self

    def fix(self) -> Self:
        """fix - try to fix shape if not valid"""
        if not self.is_valid():
            shape_copy: Shape = copy.deepcopy(self, None)
            shape_copy.wrapped = fix(self.wrapped)

            return shape_copy

        return self

    @classmethod
    @abstractmethod
    def cast(cls: Type[Self], obj: TopoDS_Shape) -> Self:
        """Returns the right type of wrapper, given a OCCT object"""

    @property
    def geom_type(self) -> GeomType:
        """Gets the underlying geometry type.

        Args:

        Returns:

        """

        shape: TopAbs_ShapeEnum = shapetype(self.wrapped)

        if shape == ta.TopAbs_EDGE:
            geom = Shape.geom_LUT_EDGE[BRepAdaptor_Curve(self.wrapped).GetType()]
        elif shape == ta.TopAbs_FACE:
            geom = Shape.geom_LUT_FACE[BRepAdaptor_Surface(self.wrapped).GetType()]
        else:
            geom = GeomType.OTHER

        return geom

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
        """Are shapes same operator =="""
        return self.is_same(other) if isinstance(other, Shape) else NotImplemented

    def is_valid(self) -> bool:
        """Returns True if no defect is detected on the shape S or any of its
        subshapes. See the OCCT docs on BRepCheck_Analyzer::IsValid for a full
        description of what is checked.

        Args:

        Returns:

        """
        chk = BRepCheck_Analyzer(self.wrapped)
        chk.SetParallel(True)
        return chk.IsValid()

    def bounding_box(self, tolerance: float = None, optimal: bool = True) -> BoundBox:
        """Create a bounding box for this Shape.

        Args:
            tolerance (float, optional): Defaults to None.

        Returns:
            BoundBox: A box sized to contain this Shape
        """
        return BoundBox.from_topo_ds(self.wrapped, tolerance=tolerance, optimal=optimal)

    def mirror(self, mirror_plane: Plane = None) -> Self:
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
        calc_function = Shape.shape_properties_LUT[shapetype(obj.wrapped)]

        if not calc_function:
            raise NotImplementedError

        calc_function(obj.wrapped, properties)
        return properties.Mass()

    def shape_type(self) -> Shapes:
        """Return the shape type string for this class"""
        return tcast(Shapes, Shape.shape_LUT[shapetype(self.wrapped)])

    def entities(self, topo_type: Shapes) -> list[TopoDS_Shape]:
        """Return all of the TopoDS sub entities of the given type"""
        return _topods_entities(self.wrapped, topo_type)

    def _entities_from(
        self, child_type: Shapes, parent_type: Shapes
    ) -> Dict[Shape, list[Shape]]:
        """This function is very slow on M1 macs and is currently unused"""
        res = TopTools_IndexedDataMapOfShapeListOfShape()

        TopExp.MapShapesAndAncestors_s(
            self.wrapped,
            Shape.inverse_shape_LUT[child_type],
            Shape.inverse_shape_LUT[parent_type],
            res,
        )

        out: Dict[Shape, list[Shape]] = {}
        for i in range(1, res.Extent() + 1):
            out[self.__class__.cast(res.FindKey(i))] = [
                self.__class__.cast(el) for el in res.FindFromIndex(i)
            ]

        return out

    def get_top_level_shapes(self) -> ShapeList[Shape]:
        """
        Retrieve the first level of child shapes from the shape.

        This method collects all the non-compound shapes directly contained in the
        current shape. If the wrapped shape is a `TopoDS_Compound`, it traverses
        its immediate children and collects all shapes that are not further nested
        compounds. Nested compounds are traversed to gather their non-compound elements
        without returning the nested compound itself.

        Returns:
            ShapeList[Shape]: A list of all first-level non-compound child shapes.

        Example:
            If the current shape is a compound containing both simple shapes
            (e.g., edges, vertices) and other compounds, the method returns a list
            of only the simple shapes directly contained at the top level.
        """
        return ShapeList(
            self.__class__.cast(s) for s in get_top_level_topods_shapes(self.wrapped)
        )

    @staticmethod
    def get_shape_list(shape: Shape, entity_type: str) -> ShapeList:
        """Helper to extract entities of a specific type from a shape."""
        if shape.wrapped is None:
            return ShapeList()
        shape_list = ShapeList(
            [shape.__class__.cast(i) for i in shape.entities(entity_type)]
        )
        for item in shape_list:
            item.topo_parent = shape
        return shape_list

    @staticmethod
    def get_single_shape(shape: Shape, entity_type: str) -> Shape:
        """Helper to extract a single entity of a specific type from a shape,
        with a warning if count != 1."""
        shape_list = Shape.get_shape_list(shape, entity_type)
        entity_count = len(shape_list)
        if entity_count != 1:
            warnings.warn(
                f"Found {entity_count} {entity_type.lower()}s, returning first",
                stacklevel=3,
            )
        return shape_list[0] if shape_list else None

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this Shape - subclasses may override"""
        return ShapeList()

    def vertex(self) -> Vertex:
        """Return the Vertex"""
        return None

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this Shape"""
        return ShapeList()

    def edge(self) -> Edge:
        """Return the Edge"""
        return None

    def wires(self) -> ShapeList[Wire]:
        """wires - all the wires in this Shape"""
        return ShapeList()

    def wire(self) -> Wire:
        """Return the Wire"""
        return None

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this Shape"""
        return ShapeList()

    def face(self) -> Face:
        """Return the Face"""
        return None

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this Shape"""
        return ShapeList()

    def shell(self) -> Shell:
        """Return the Shell"""
        return None

    def solids(self) -> ShapeList[Solid]:
        """solids - all the solids in this Shape"""
        return ShapeList()

    def solid(self) -> Solid:
        """Return the Solid"""
        return None

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this Shape"""
        return ShapeList()

    def compound(self) -> Compound:
        """Return the Compound"""
        return None

    @property
    def area(self) -> float:
        """area -the surface area of all faces in this Shape"""
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(self.wrapped, properties)

        return properties.Mass()

    def _apply_transform(self, transformation: gp_Trsf) -> Self:
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

    def rotate(self, axis: Axis, angle: float) -> Self:
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

    def translate(self, vector: VectorLike) -> Self:
        """Translates this shape through a transformation.

        Args:
          vector: VectorLike:

        Returns:

        """

        transformation = gp_Trsf()
        transformation.SetTranslation(Vector(vector).wrapped)

        return self._apply_transform(transformation)

    def scale(self, factor: float) -> Self:
        """Scales this shape through a transformation.

        Args:
          factor: float:

        Returns:

        """

        transformation = gp_Trsf()
        transformation.SetScale(gp_Pnt(), factor)

        return self._apply_transform(transformation)

    def __deepcopy__(self, memo) -> Self:
        """Return deepcopy of self"""
        # The wrapped object is a OCCT TopoDS_Shape which can't be pickled or copied
        # with the standard python copy/deepcopy, so create a deepcopy 'memo' with this
        # value already copied which causes deepcopy to skip it.
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        if self.wrapped is not None:
            memo[id(self.wrapped)] = downcast(BRepBuilderAPI_Copy(self.wrapped).Shape())
        for key, value in self.__dict__.items():
            setattr(result, key, copy.deepcopy(value, memo))
            if key == "joints":
                for joint in result.joints.values():
                    joint.parent = result
        return result

    def __copy__(self) -> Self:
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

    def copy(self) -> Self:
        """Here for backwards compatibility with cq-editor"""
        warnings.warn(
            "copy() will be deprecated - use copy.copy() or copy.deepcopy() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return copy.deepcopy(self, None)

    def transform_shape(self, t_matrix: Matrix) -> Self:
        """Apply affine transform without changing type

        Transforms a copy of this Shape by the provided 3D affine transformation matrix.
        Note that not all transformation are supported - primarily designed for translation
        and rotation.  See :transform_geometry: for more comprehensive transformations.

        Args:
            t_matrix (Matrix): affine transformation matrix

        Returns:
            Shape: copy of transformed shape with all objects keeping their type
        """
        transformed = downcast(
            BRepBuilderAPI_Transform(self.wrapped, t_matrix.wrapped.Trsf()).Shape()
        )
        new_shape = copy.deepcopy(self, None)
        new_shape.wrapped = transformed

        return new_shape

    def transform_geometry(self, t_matrix: Matrix) -> Self:
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
        transformed = downcast(
            BRepBuilderAPI_GTransform(self.wrapped, t_matrix.wrapped, True).Shape()
        )
        new_shape = copy.deepcopy(self, None)
        new_shape.wrapped = transformed

        return new_shape

    def locate(self, loc: Location) -> Self:
        """Apply a location in absolute sense to self

        Args:
          loc: Location:

        Returns:

        """

        self.wrapped.Location(loc.wrapped)

        return self

    def located(self, loc: Location) -> Self:
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

    def move(self, loc: Location) -> Self:
        """Apply a location in relative sense (i.e. update current location) to self

        Args:
          loc: Location:

        Returns:

        """

        self.wrapped.Move(loc.wrapped)

        return self

    def moved(self, loc: Location) -> Self:
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

    def relocate(self, loc: Location):
        """Change the location of self while keeping it geometrically similar

        Args:
            loc (Location): new location to set for self
        """
        if self.location != loc:
            old_ax = gp_Ax3()
            old_ax.Transform(self.location.wrapped.Transformation())

            new_ax = gp_Ax3()
            new_ax.Transform(loc.wrapped.Transformation())

            trsf = gp_Trsf()
            trsf.SetDisplacement(new_ax, old_ax)
            builder = BRepBuilderAPI_Transform(self.wrapped, trsf, True, True)

            self.wrapped = downcast(builder.Shape())
            self.wrapped.Location(loc.wrapped)

    def distance_to_with_closest_points(
        self, other: Union[Shape, VectorLike]
    ) -> tuple[float, Vector, Vector]:
        """Minimal distance between two shapes and the points on each shape"""

        if isinstance(other, Shape):
            topods_shape = other.wrapped
        else:
            vec = Vector(other)
            topods_shape = downcast(
                BRepBuilderAPI_MakeVertex(gp_Pnt(vec.X, vec.Y, vec.Z)).Vertex()
            )

        dist_calc = BRepExtrema_DistShapeShape()
        dist_calc.LoadS1(self.wrapped)
        dist_calc.LoadS2(topods_shape)
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
    ) -> Self | ShapeList[Self]:
        """Generic boolean operation

        Args:
          args: Iterable[Shape]:
          tools: Iterable[Shape]:
          operation: Union[BRepAlgoAPI_BooleanOperation:
          BRepAlgoAPI_Splitter]:

        Returns:

        """
        # Find the highest order class from all the inputs Solid > Vertex
        order_dict = {type(s): type(s).order for s in [self] + list(args) + list(tools)}
        highest_order = sorted(order_dict.items(), key=lambda item: item[1])[-1]

        # The base of the operation
        base = args[0] if isinstance(args, (list, tuple)) else args

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

        topo_result = downcast(operation.Shape())

        # Clean
        if SkipClean.clean:
            upgrader = ShapeUpgrade_UnifySameDomain(topo_result, True, True, True)
            upgrader.AllowInternalEdges(False)
            try:
                upgrader.Build()
                topo_result = downcast(upgrader.Shape())
            except Exception:
                warnings.warn("Boolean operation unable to clean", stacklevel=2)

        # Remove unnecessary TopoDS_Compound around single shape
        if isinstance(topo_result, TopoDS_Compound):
            topo_result = unwrap_topods_compound(topo_result, True)

        if isinstance(topo_result, TopoDS_Compound) and highest_order[1] != 4:
            results = ShapeList(
                highest_order[0].cast(s)
                for s in get_top_level_topods_shapes(topo_result)
            )
            for result in results:
                base.copy_attributes_to(result, ["wrapped", "_NodeMixin__children"])
            return results

        result = highest_order[0].cast(topo_result)
        base.copy_attributes_to(result, ["wrapped", "_NodeMixin__children"])

        return result

    def cut(self, *to_cut: Shape) -> Self | ShapeList[Self]:
        """Remove the positional arguments from this Shape.

        Args:
          *to_cut: Shape:

        Returns:
            Self | ShapeList[Self]: Resulting object may be of a different class than self
                or a ShapeList if multiple non-Compound object created
        """

        cut_op = BRepAlgoAPI_Cut()

        return self._bool_op((self,), to_cut, cut_op)

    def fuse(
        self, *to_fuse: Shape, glue: bool = False, tol: float = None
    ) -> Self | ShapeList[Self]:
        """fuse

        Fuse a sequence of shapes into a single shape.

        Args:
            to_fuse (sequence Shape): shapes to fuse
            glue (bool, optional): performance improvement for some shapes. Defaults to False.
            tol (float, optional): tolerance. Defaults to None.

        Returns:
            Self | ShapeList[Self]: Resulting object may be of a different class than self
                or a ShapeList if multiple non-Compound object created

        """

        fuse_op = BRepAlgoAPI_Fuse()
        if glue:
            fuse_op.SetGlue(BOPAlgo_GlueEnum.BOPAlgo_GlueShift)
        if tol:
            fuse_op.SetFuzzyValue(tol)

        return_value = self._bool_op((self,), to_fuse, fuse_op)

        return return_value

    def intersect(
        self, *to_intersect: Union[Shape, Axis, Plane]
    ) -> Self | ShapeList[Self]:
        """Intersection of the arguments and this shape

        Args:
            to_intersect (sequence of Union[Shape, Axis, Plane]): Shape(s) to
                intersect with

        Returns:
            Self | ShapeList[Self]: Resulting object may be of a different class than self
                or a ShapeList if multiple non-Compound object created
        """

        def _to_vertex(vec: Vector) -> Vertex:
            """Helper method to convert vector to shape"""
            return self.__class__.cast(
                downcast(
                    BRepBuilderAPI_MakeVertex(gp_Pnt(vec.X, vec.Y, vec.Z)).Vertex()
                )
            )

        def _to_edge(axis: Axis) -> Edge:
            """Helper method to convert axis to shape"""
            return self.__class__.cast(
                BRepBuilderAPI_MakeEdge(
                    Geom_Line(
                        axis.position.to_pnt(),
                        axis.direction.to_dir(),
                    )
                ).Edge()
            )

        def _to_face(plane: Plane) -> Face:
            """Helper method to convert plane to shape"""
            return self.__class__.cast(BRepBuilderAPI_MakeFace(plane.wrapped).Face())

        # Convert any geometry objects into their respective topology objects
        objs = []
        for obj in to_intersect:
            if isinstance(obj, Vector):
                objs.append(_to_vertex(obj))
            elif isinstance(obj, Axis):
                objs.append(_to_edge(obj))
            elif isinstance(obj, Plane):
                objs.append(_to_face(obj))
            elif isinstance(obj, Location):
                objs.append(_to_vertex(obj.position))
            else:
                objs.append(obj)

        # Find the shape intersections
        intersect_op = BRepAlgoAPI_Common()
        shape_intersections = self._bool_op((self,), objs, intersect_op)

        return shape_intersections

    def _ocp_section(
        self: Shape, other: Union[Vertex, Edge, Wire, Face]
    ) -> tuple[list[Vertex], list[Edge]]:
        """_ocp_section

        Create a BRepAlgoAPI_Section object

        The algorithm is to build a Section operation between arguments and tools.
        The result of Section operation consists of vertices and edges. The result
        of Section operation contains:
        - new vertices that are subjects of V/V, E/E, E/F, F/F interferences
        - vertices that are subjects of V/E, V/F interferences
        - new edges that are subjects of F/F interferences
        - edges that are Common Blocks


        Args:
            other (Union[Vertex, Edge, Wire, Face]): shape to section with

        Returns:
            tuple[list[Vertex], list[Edge]]: section results
        """
        try:
            section = BRepAlgoAPI_Section(other.geom_adaptor(), self.wrapped)
        except (TypeError, AttributeError):
            try:
                section = BRepAlgoAPI_Section(self.geom_adaptor(), other.wrapped)
            except (TypeError, AttributeError):
                return ([], [])

        # Perform the intersection calculation
        section.Build()

        # Get the resulting shapes from the intersection
        intersection_shape = section.Shape()

        vertices = []
        # Iterate through the intersection shape to find intersection points/edges
        explorer = TopExp_Explorer(intersection_shape, TopAbs_ShapeEnum.TopAbs_VERTEX)
        while explorer.More():
            vertices.append(self.__class__.cast(downcast(explorer.Current())))
            explorer.Next()
        edges = []
        explorer = TopExp_Explorer(intersection_shape, TopAbs_ShapeEnum.TopAbs_EDGE)
        while explorer.More():
            edges.append(self.__class__.cast(downcast(explorer.Current())))
            explorer.Next()

        return (vertices, edges)

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
                (
                    intersect_maker.Face(),
                    abs(distance),
                )
            )  # will sort all intersected faces by distance whatever the direction is

            intersect_maker.Next()

        faces_dist.sort(key=lambda x: x[1])
        faces = [face[0] for face in faces_dist]

        return ShapeList([self.__class__.cast(face) for face in faces])

    @overload
    def split_by_perimeter(
        self, perimeter: Union[Edge, Wire], keep: Literal[Keep.INSIDE, Keep.OUTSIDE]
    ) -> Optional[Face] | Optional[Shell] | Optional[ShapeList[Face]]:
        """split_by_perimeter and keep inside or outside"""

    @overload
    def split_by_perimeter(
        self, perimeter: Union[Edge, Wire], keep: Literal[Keep.BOTH]
    ) -> tuple[
        Optional[Face] | Optional[Shell] | Optional[ShapeList[Face]],
        Optional[Face] | Optional[Shell] | Optional[ShapeList[Face]],
    ]:
        """split_by_perimeter and keep inside and outside"""

    @overload
    def split_by_perimeter(
        self, perimeter: Union[Edge, Wire]
    ) -> Optional[Face] | Optional[Shell] | Optional[ShapeList[Face]]:
        """split_by_perimeter and keep inside (default)"""

    def split_by_perimeter(
        self, perimeter: Union[Edge, Wire], keep: Keep = Keep.INSIDE
    ):
        """split_by_perimeter

        Divide the faces of this object into those within the perimeter
        and those outside the perimeter.

        Note: this method may fail if the perimeter intersects shape edges.

        Args:
            perimeter (Union[Edge,Wire]): closed perimeter
            keep (Keep, optional): which object(s) to return. Defaults to Keep.INSIDE.

        Raises:
            ValueError: perimeter must be closed
            ValueError: keep must be one of Keep.INSIDE|OUTSIDE|BOTH

        Returns:
            Union[Optional[Shell], Optional[Face],
            Tuple[Optional[Shell], Optional[Face]]]: The result of the split operation.

            - **Keep.INSIDE**: Returns the inside part as a `Shell` or `Face`, or `None`
              if no inside part is found.
            - **Keep.OUTSIDE**: Returns the outside part as a `Shell` or `Face`, or `None`
              if no outside part is found.
            - **Keep.BOTH**: Returns a tuple `(inside, outside)` where each element is
              either a `Shell`, `Face`, or `None` if no corresponding part is found.

        """

        def get(los: TopTools_ListOfShape) -> list:
            """Return objects from TopTools_ListOfShape as list"""
            shapes = []
            for _ in range(los.Size()):
                first = los.First()
                if not first.IsNull():
                    shapes.append(self.__class__.cast(first))
                los.RemoveFirst()
            return shapes

        def process_sides(sides):
            """Process sides to determine if it should be None, a single element,
            a Shell, or a ShapeList."""
            if not sides:
                return None
            if len(sides) == 1:
                return sides[0]
            # Attempt to create a shell
            potential_shell = _sew_topods_faces([s.wrapped for s in sides])
            if isinstance(potential_shell, TopoDS_Shell):
                return self.__class__.cast(potential_shell)
            return ShapeList(sides)

        if keep not in {Keep.INSIDE, Keep.OUTSIDE, Keep.BOTH}:
            raise ValueError(
                "keep must be one of Keep.INSIDE, Keep.OUTSIDE, or Keep.BOTH"
            )

        # Process the perimeter
        if not perimeter.is_closed:
            raise ValueError("perimeter must be a closed Wire or Edge")
        perimeter_edges = TopTools_SequenceOfShape()
        for perimeter_edge in perimeter.edges():
            perimeter_edges.Append(perimeter_edge.wrapped)

        # Split the shells by the perimeter edges
        lefts: list[Shell] = []
        rights: list[Shell] = []
        for target_shell in self.shells():
            constructor = BRepFeat_SplitShape(target_shell.wrapped)
            constructor.Add(perimeter_edges)
            constructor.Build()
            lefts.extend(get(constructor.Left()))
            rights.extend(get(constructor.Right()))

        left = process_sides(lefts)
        right = process_sides(rights)

        # Is left or right the inside?
        perimeter_length = perimeter.length
        left_perimeter_length = sum(e.length for e in left.edges()) if left else 0
        right_perimeter_length = sum(e.length for e in right.edges()) if right else 0
        left_inside = abs(perimeter_length - left_perimeter_length) < abs(
            perimeter_length - right_perimeter_length
        )
        if keep == Keep.BOTH:
            return (left, right) if left_inside else (right, left)
        if keep == Keep.INSIDE:
            return left if left_inside else right
        # keep == Keep.OUTSIDE:
        return right if left_inside else left

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
            BRepMesh_IncrementalMesh(
                self.wrapped, tolerance, True, angular_tolerance, True
            )

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

    def to_arcs(self, tolerance: float = 1e-3) -> Face:
        """to_arcs

        Approximate planar face with arcs and straight line segments.

        Args:
            tolerance (float, optional): Approximation tolerance. Defaults to 1e-3.

        Returns:
            Face: approximated face
        """
        return self.__class__(BRepAlgo.ConvertFace_s(self.wrapped, tolerance))

    # def _repr_javascript_(self):
    #     """Jupyter 3D representation support"""

    #     from .jupyter_tools import display

    #     return display(self)._repr_javascript_()

    def transformed(
        self, rotate: VectorLike = (0, 0, 0), offset: VectorLike = (0, 0, 0)
    ) -> Self:
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

    def find_intersection_points(self, other: Axis) -> list[tuple[Vector, Vector]]:
        """Find point and normal at intersection

        Return both the point(s) and normal(s) of the intersection of the axis and the shape

        Args:
            axis (Axis): axis defining the intersection line

        Returns:
            list[tuple[Vector, Vector]]: Point and normal of intersection
        """
        oc_shape = self.wrapped

        intersection_line = gce_MakeLin(other.wrapped).Value()
        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(oc_shape, intersection_line, 0.0001)

        intersections = []
        while intersect_maker.More():
            inter_pt = intersect_maker.Pnt()
            # Calculate distance along axis
            distance = other.to_plane().to_local_coords(Vector(inter_pt)).Z
            intersections.append(
                (
                    intersect_maker.Face(),  # TopoDS_Face
                    Vector(inter_pt),
                    distance,
                )
            )
            intersect_maker.Next()

        intersections.sort(key=lambda x: x[2])
        intersecting_faces = [i[0] for i in intersections]
        intersecting_points = [i[1] for i in intersections]
        intersecting_normals = [
            f.normal_at(intersecting_points[i].to_pnt())
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
    ) -> ShapeList[Face]:
        """Projected Faces following the given path on Shape

        Project by positioning each face of to the shape along the path and
        projecting onto the surface.

        Note that projection may result in distortion depending on
        the shape at a position along the path.

        .. image:: projectText.png

        Args:
            faces (Union[list[Face], Compound]): faces to project
            path: Path on the Shape to follow
            start: Relative location on path to start the faces. Defaults to 0.

        Returns:
            The projected faces

        """
        # pylint: disable=too-many-locals
        path_length = path.length
        # The derived classes of Shape implement center
        shape_center = self.center()  # pylint: disable=no-member

        if (
            not isinstance(faces, (list, tuple))
            and faces.wrapped is not None
            and isinstance(faces.wrapped, TopoDS_Compound)
        ):
            faces = faces.faces()

        first_face_min_x = faces[0].bounding_box().min.X

        logger.debug("projecting %d face(s)", len(faces))

        # Position each face normal to the surface along the path and project to the surface
        projected_faces = []
        for face in faces:
            bbox = face.bounding_box()
            face_center_x = (bbox.min.X + bbox.max.X) / 2
            relative_position_on_wire = (
                start + (face_center_x - first_face_min_x) / path_length
            )
            path_position = path.position_at(relative_position_on_wire)
            path_tangent = path.tangent_at(relative_position_on_wire)
            projection_axis = Axis(path_position, shape_center - path_position)
            (surface_point, surface_normal) = self.find_intersection_points(
                projection_axis
            )[0]
            surface_normal_plane = Plane(
                origin=surface_point, x_dir=path_tangent, z_dir=surface_normal
            )
            projection_face: Face = surface_normal_plane.from_local_coords(
                face.moved(Location((-face_center_x, 0, 0)))
            )

            logger.debug("projecting face at %0.2f", relative_position_on_wire)
            projected_faces.append(
                projection_face.project_to_shape(self, surface_normal * -1)[0]
            )

        logger.debug("finished projecting '%d' faces", len(faces))

        return ShapeList(projected_faces)


class Comparable(metaclass=ABCMeta):
    """Abstract base class that requires comparison methods"""

    @abstractmethod
    def __lt__(self, other: Any) -> bool: ...

    @abstractmethod
    def __eq__(self, other: Any) -> bool: ...


# This TypeVar allows IDEs to see the type of objects within the ShapeList
T = TypeVar("T", bound=Union[Shape, Vector])
K = TypeVar("K", bound=Comparable)


class ShapePredicate(Protocol):
    """Predicate for shape filters"""

    def __call__(self, shape: Shape) -> bool: ...


class ShapeList(list[T]):
    """Subclass of list with custom filter and sort methods appropriate to CAD"""

    # pylint: disable=too-many-public-methods

    @property
    def first(self) -> T:
        """First element in the ShapeList"""
        return self[0]

    @property
    def last(self) -> T:
        """Last element in the ShapeList"""
        return self[-1]

    def center(self) -> Vector:
        """The average of the center of objects within the ShapeList"""
        return sum(o.center() for o in self) / len(self) if self else Vector(0, 0, 0)

    def filter_by(
        self,
        filter_by: Union[ShapePredicate, Axis, Plane, GeomType],
        reverse: bool = False,
        tolerance: float = 1e-5,
    ) -> ShapeList[T]:
        """filter by Axis, Plane, or GeomType

        Either:
        - filter objects of type planar Face or linear Edge by their normal or tangent
        (respectively) and sort the results by the given axis, or
        - filter the objects by the provided type. Note that not all types apply to all
        objects.

        Args:
            filter_by (Union[Axis,Plane,GeomType]): axis, plane, or geom type to filter
                and possibly sort by. Filtering by a plane returns faces/edges parallel
                to that plane.
            reverse (bool, optional): invert the geom type filter. Defaults to False.
            tolerance (float, optional): maximum deviation from axis. Defaults to 1e-5.

        Raises:
            ValueError: Invalid filter_by type

        Returns:
            ShapeList: filtered list of objects
        """

        # could be moved out maybe?
        def axis_parallel_predicate(axis: Axis, tolerance: float):
            def pred(shape: Shape):
                if shape.is_planar_face:
                    gp_pnt = gp_Pnt()
                    normal = gp_Vec()
                    u_val, _, v_val, _ = BRepTools.UVBounds_s(shape.wrapped)
                    BRepGProp_Face(shape.wrapped).Normal(u_val, v_val, gp_pnt, normal)
                    normal = Vector(normal).normalized()
                    shape_axis = Axis(shape.center(), normal)
                elif (
                    isinstance(shape.wrapped, TopoDS_Edge)
                    and shape.geom_type == GeomType.LINE
                ):
                    curve = shape.geom_adaptor()
                    umin = curve.FirstParameter()
                    tmp = gp_Pnt()
                    res = gp_Vec()
                    curve.D1(umin, tmp, res)
                    start_pos = Vector(tmp)
                    start_dir = Vector(gp_Dir(res))
                    shape_axis = Axis(start_pos, start_dir)
                else:
                    return False
                return axis.is_parallel(shape_axis, tolerance)

            return pred

        def plane_parallel_predicate(plane: Plane, tolerance: float):
            plane_axis = Axis(plane.origin, plane.z_dir)
            plane_xyz = plane.z_dir.wrapped.XYZ()

            def pred(shape: Shape):
                if shape.is_planar_face:
                    gp_pnt = gp_Pnt()
                    normal = gp_Vec()
                    u_val, _, v_val, _ = BRepTools.UVBounds_s(shape.wrapped)
                    BRepGProp_Face(shape.wrapped).Normal(u_val, v_val, gp_pnt, normal)
                    normal = Vector(normal).normalized()
                    shape_axis = Axis(shape.center(), normal)
                    # shape_axis = Axis(shape.center(), shape.normal_at(None))
                    return plane_axis.is_parallel(shape_axis, tolerance)
                if isinstance(shape.wrapped, TopoDS_Wire):
                    return all(pred(e) for e in shape.edges())
                if isinstance(shape.wrapped, TopoDS_Edge):
                    for curve in shape.wrapped.TShape().Curves():
                        if curve.IsCurve3D():
                            return ShapeAnalysis_Curve.IsPlanar_s(
                                curve.Curve3D(), plane_xyz, tolerance
                            )
                    return False
                return False

            return pred

        # convert input to callable predicate
        if callable(filter_by):
            predicate = filter_by
        elif isinstance(filter_by, Axis):
            predicate = axis_parallel_predicate(filter_by, tolerance=tolerance)
        elif isinstance(filter_by, Plane):
            predicate = plane_parallel_predicate(filter_by, tolerance=tolerance)
        elif isinstance(filter_by, GeomType):

            def predicate(obj):
                return obj.geom_type == filter_by

        else:
            raise ValueError(f"Unsupported filter_by predicate: {filter_by}")

        # final predicate is negated if `reverse=True`
        if reverse:

            def actual_predicate(shape):
                return not predicate(shape)

        else:
            actual_predicate = predicate

        return ShapeList(filter(actual_predicate, self))

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
        self,
        group_by: Union[Callable[[Shape], K], Axis, Edge, Wire, SortBy] = Axis.Z,
        reverse=False,
        tol_digits=6,
    ) -> GroupBy[T, K]:
        """group by

        Group objects by provided criteria and then sort the groups according to the criteria.
        Note that not all group_by criteria apply to all objects.

        Args:
            group_by (SortBy, optional): group and sort criteria. Defaults to Axis.Z.
            reverse (bool, optional): flip order of sort. Defaults to False.
            tol_digits (int, optional): Tolerance for building the group keys by
                round(key, tol_digits)

        Returns:
            GroupBy[K, ShapeList]: sorted list of ShapeLists
        """

        if isinstance(group_by, Axis):
            axis_as_location = group_by.location.inverse()

            def key_f(obj):
                return round(
                    (axis_as_location * Location(obj.center())).position.Z,
                    tol_digits,
                )

        elif hasattr(group_by, "wrapped") and isinstance(
            group_by.wrapped, (TopoDS_Edge, TopoDS_Wire)
        ):

            def key_f(obj):
                pnt1, _pnt2 = group_by.closest_points(obj.center())
                return round(group_by.param_at_point(pnt1), tol_digits)

        elif isinstance(group_by, SortBy):
            if group_by == SortBy.LENGTH:

                def key_f(obj):
                    return round(obj.length, tol_digits)

            elif group_by == SortBy.RADIUS:

                def key_f(obj):
                    return round(obj.radius, tol_digits)

            elif group_by == SortBy.DISTANCE:

                def key_f(obj):
                    return round(obj.center().length, tol_digits)

            elif group_by == SortBy.AREA:

                def key_f(obj):
                    return round(obj.area, tol_digits)

            elif group_by == SortBy.VOLUME:

                def key_f(obj):
                    return round(obj.volume, tol_digits)

        elif callable(group_by):
            key_f = group_by

        else:
            raise ValueError(f"Unsupported group_by function: {group_by}")

        return GroupBy(key_f, self, reverse=reverse)

    def sort_by(
        self, sort_by: Union[Axis, Edge, Wire, SortBy] = Axis.Z, reverse: bool = False
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
            axis_as_location = sort_by.location.inverse()
            objects = sorted(
                self,
                key=lambda o: (axis_as_location * Location(o.center())).position.Z,
                reverse=reverse,
            )
        elif hasattr(sort_by, "wrapped") and isinstance(
            sort_by.wrapped, (TopoDS_Edge, TopoDS_Wire)
        ):

            def u_of_closest_center(obj) -> float:
                """u-value of closest point between object center and sort_by"""
                pnt1, _pnt2 = sort_by.closest_points(obj.center())
                return sort_by.param_at_point(pnt1)

            # pylint: disable=unnecessary-lambda
            objects = sorted(
                self, key=lambda o: u_of_closest_center(o), reverse=reverse
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
        distances = sorted(
            [(obj.distance_to(other), obj) for obj in self],
            key=lambda obj: obj[0],
            reverse=reverse,
        )
        return ShapeList([obj[1] for obj in distances])

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this ShapeList"""
        return ShapeList([v for shape in self for v in shape.vertices()])

    def vertex(self) -> Vertex:
        """Return the Vertex"""
        vertices = self.vertices()
        vertex_count = len(vertices)
        if vertex_count != 1:
            warnings.warn(
                f"Found {vertex_count} vertices, returning first", stacklevel=2
            )
        return vertices[0]

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this ShapeList"""
        return ShapeList([e for shape in self for e in shape.edges()])

    def edge(self) -> Edge:
        """Return the Edge"""
        edges = self.edges()
        edge_count = len(edges)
        if edge_count != 1:
            warnings.warn(f"Found {edge_count} edges, returning first", stacklevel=2)
        return edges[0]

    def wires(self) -> ShapeList[Wire]:
        """wires - all the wires in this ShapeList"""
        return ShapeList([w for shape in self for w in shape.wires()])

    def wire(self) -> Wire:
        """Return the Wire"""
        wires = self.wires()
        wire_count = len(wires)
        if wire_count != 1:
            warnings.warn(f"Found {wire_count} wires, returning first", stacklevel=2)
        return wires[0]

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this ShapeList"""
        return ShapeList([f for shape in self for f in shape.faces()])

    def face(self) -> Face:
        """Return the Face"""
        faces = self.faces()
        face_count = len(faces)
        if face_count != 1:
            msg = f"Found {face_count} faces, returning first"
            warnings.warn(msg, stacklevel=2)
        return faces[0]

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this ShapeList"""
        return ShapeList([s for shape in self for s in shape.shells()])

    def shell(self) -> Shell:
        """Return the Shell"""
        shells = self.shells()
        shell_count = len(shells)
        if shell_count != 1:
            warnings.warn(f"Found {shell_count} shells, returning first", stacklevel=2)
        return shells[0]

    def solids(self) -> ShapeList[Solid]:
        """solids - all the solids in this ShapeList"""
        return ShapeList([s for shape in self for s in shape.solids()])

    def solid(self) -> Solid:
        """Return the Solid"""
        solids = self.solids()
        solid_count = len(solids)
        if solid_count != 1:
            warnings.warn(f"Found {solid_count} solids, returning first", stacklevel=2)
        return solids[0]

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this ShapeList"""
        return ShapeList([c for shape in self for c in shape.compounds()])

    def compound(self) -> Compound:
        """Return the Compound"""
        compounds = self.compounds()
        compound_count = len(compounds)
        if compound_count != 1:
            warnings.warn(
                f"Found {compound_count} compounds, returning first", stacklevel=2
            )
        return compounds[0]

    def __gt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort operator >"""
        return self.sort_by(sort_by)

    def __lt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Reverse sort operator <"""
        return self.sort_by(sort_by, reverse=True)

    def __rshift__(self, group_by: Union[Axis, SortBy] = Axis.Z):
        """Group and select largest group operator >>"""
        return self.group_by(group_by)[-1]

    def __lshift__(self, group_by: Union[Axis, SortBy] = Axis.Z):
        """Group and select smallest group operator <<"""
        return self.group_by(group_by)[0]

    def __or__(self, filter_by: Union[Axis, GeomType] = Axis.Z):
        """Filter by axis or geomtype operator |"""
        return self.filter_by(filter_by)

    def __eq__(self, other: object):
        """ShapeLists equality operator =="""
        return (
            set(self) == set(other) if isinstance(other, ShapeList) else NotImplemented
        )

    # Normally implementing __eq__ is enough, but ShapeList subclasses list,
    # which already implements __ne__, so we need to override it, too
    def __ne__(self, other: ShapeList):
        """ShapeLists inequality operator !="""
        return (
            set(self) != set(other) if isinstance(other, ShapeList) else NotImplemented
        )

    def __add__(self, other: ShapeList):
        """Combine two ShapeLists together operator +"""
        return ShapeList(list(self) + list(other))

    def __sub__(self, other: ShapeList) -> ShapeList:
        """Differences between two ShapeLists operator -"""
        # hash_other = [hash(o) for o in other]
        # hash_set = {hash(o): o for o in self if hash(o) not in hash_other}
        # return ShapeList(hash_set.values())
        return ShapeList(set(self) - set(other))

    def __and__(self, other: ShapeList):
        """Intersect two ShapeLists operator &"""
        return ShapeList(set(self) & set(other))

    @overload
    def __getitem__(self, key: int) -> T: ...

    @overload
    def __getitem__(self, key: slice) -> ShapeList[T]: ...

    def __getitem__(self, key: Union[int, slice]) -> Union[T, ShapeList[T]]:
        """Return slices of ShapeList as ShapeList"""
        if isinstance(key, slice):
            return_value = ShapeList(list(self).__getitem__(key))
        else:
            return_value = list(self).__getitem__(key)
        return return_value


class GroupBy(Generic[T, K]):
    """Result of a Shape.groupby operation. Groups can be accessed by index or key"""

    def __init__(
        self,
        key_f: Callable[[T], K],
        shapelist: Iterable[T],
        *,
        reverse: bool = False,
    ):
        # can't be a dict because K may not be hashable
        self.key_to_group_index: list[tuple[K, int]] = []
        self.groups: list[ShapeList[T]] = []
        self.key_f = key_f

        for i, (key, shapegroup) in enumerate(
            itertools.groupby(sorted(shapelist, key=key_f, reverse=reverse), key=key_f)
        ):
            self.groups.append(ShapeList(shapegroup))
            self.key_to_group_index.append((key, i))

    def __iter__(self):
        return iter(self.groups)

    def __len__(self):
        return len(self.groups)

    def __getitem__(self, key: int):
        return self.groups[key]

    def __str__(self):
        return pretty(self)

    def __repr__(self):
        return repr(ShapeList(self))

    def _repr_pretty_(self, printer: PrettyPrinter, cycle: bool = False) -> None:
        """
        Render a formatted representation of the object for pretty-printing in
        interactive environments.

        Args:
            printer (PrettyPrinter): The pretty printer instance handling the output.
            cycle (bool): Indicates if a reference cycle is detected to
                prevent infinite recursion.
        """
        if cycle:
            printer.text("(...)")
        else:
            with printer.group(1, "[", "]"):
                for idx, item in enumerate(self):
                    if idx:
                        printer.text(",")
                        printer.breakable()
                    printer.pretty(item)

    def group(self, key: K):
        """Select group by key"""
        for k, i in self.key_to_group_index:
            if key == k:
                return self.groups[i]
        raise KeyError(key)

    def group_for(self, shape: T):
        """Select group by shape"""
        return self.group(self.key_f(shape))


class Compound(Mixin3D, Shape):
    """A Compound in build123d is a topological entity representing a collection of
    geometric shapes grouped together within a single structure. It serves as a
    container for organizing diverse shapes like edges, faces, or solids. This
    hierarchical arrangement facilitates the construction of complex models by
    combining simpler shapes. Compound plays a pivotal role in managing the
    composition and structure of intricate 3D models in computer-aided design
    (CAD) applications, allowing engineers and designers to work with assemblies
    of shapes as unified entities for efficient modeling and analysis."""

    order = 4.0

    project_to_viewport = Mixin1D.project_to_viewport
    extrude = _ClassMethodProxy(Mixin1D.extrude)

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Self:
        "Returns the right type of wrapper, given a OCCT object"

        # define the shape lookup table for casting
        constructor_lut = {
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
        return constructor_lut[shape_type](downcast(obj))

    @property
    def _dim(self) -> Union[int, None]:
        """The dimension of the shapes within the Compound - None if inconsistent"""
        sub_dims = {s.dim for s in get_top_level_topods_shapes(self.wrapped)}
        return sub_dims.pop() if len(sub_dims) == 1 else None

    def __init__(
        self,
        obj: Optional[TopoDS_Compound | Iterable[Shape]] = None,
        label: str = "",
        color: Color = None,
        material: str = "",
        joints: dict[str, Joint] = None,
        parent: Compound = None,
        children: Sequence[Shape] = None,
    ):
        """Build a Compound from Shapes

        Args:
            obj (TopoDS_Compound | Iterable[Shape], optional): OCCT Compound or shapes
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            material (str, optional): tag for external tools. Defaults to ''.
            joints (dict[str, Joint], optional): names joints. Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
            children (Sequence[Shape], optional): assembly children. Defaults to None.
        """

        if isinstance(obj, Iterable):
            obj = _make_topods_compound_from_shapes([s.wrapped for s in obj])

        super().__init__(
            obj=obj,
            label=label,
            color=color,
            parent=parent,
        )
        self.material = "" if material is None else material
        self.joints = {} if joints is None else joints
        self.children = [] if children is None else children

    def __repr__(self):
        """Return Compound info as string"""
        if hasattr(self, "label") and hasattr(self, "children"):
            result = (
                f"{self.__class__.__name__} at {id(self):#x}, label({self.label}), "
                + f"#children({len(self.children)})"
            )
        else:
            result = f"{self.__class__.__name__} at {id(self):#x}"
        return result

    @property
    def volume(self) -> float:
        """volume - the volume of this Compound"""
        # when density == 1, mass == volume
        return sum(i.volume for i in [*self.get_type(Solid), *self.get_type(Shell)])

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
            calc_function = Shape.shape_properties_LUT[unwrapped_shapetype(self)]
            if calc_function:
                calc_function(self.wrapped, properties)
                middle = Vector(properties.CentreOfMass())
            else:
                raise NotImplementedError
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

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
            parent.wrapped = _make_topods_compound_from_shapes(
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
        parent.wrapped = _make_topods_compound_from_shapes(
            [c.wrapped for c in parent.children]
        )

    def _post_detach_children(self, children):
        """Method call before detaching `children`."""
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Removing children %s from %s", kids, self.label)
            self.wrapped = _make_topods_compound_from_shapes(
                [c.wrapped for c in self.children]
            )
        # else:
        #     logger.debug("Removing no children from %s", self.label)

    def _pre_attach_children(self, children):
        """Method call before attaching `children`."""
        if not all(isinstance(child, Shape) for child in children):
            raise ValueError("Each child must be of type Shape")

    def _post_attach_children(self, children: Iterable[Shape]):
        """Method call after attaching `children`."""
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Adding children %s to %s", kids, self.label)
            self.wrapped = _make_topods_compound_from_shapes(
                [c.wrapped for c in self.children]
            )
        # else:
        #     logger.debug("Adding no children to %s", self.label)

    def __add__(self, other: Shape | Sequence[Shape]) -> Compound:
        """Combine other to self `+` operator

        Note that if all of the objects are connected Edges/Wires the result
        will be a Wire, otherwise a Shape.
        """
        if self._dim == 1:
            curve = Curve() if self.wrapped is None else Curve(self.wrapped)
            self.copy_attributes_to(curve, ["wrapped", "_NodeMixin__children"])
            return curve + other

        summands = [
            shape
            for o in (other if isinstance(other, (list, tuple)) else [other])
            if o is not None
            for shape in o.get_top_level_shapes()
        ]
        # If there is nothing to add return the original object
        if not summands:
            return self

        summands = [s for s in self.get_top_level_shapes() + summands if s is not None]

        # Only fuse the parts if necessary
        if len(summands) <= 1:
            result: Shape = Compound(summands[0:1])
        else:
            fuse_op = BRepAlgoAPI_Fuse()
            fuse_op.SetFuzzyValue(TOLERANCE)
            self.copy_attributes_to(summands[0], ["wrapped", "_NodeMixin__children"])
            result = self._bool_op(summands[:1], summands[1:], fuse_op)
            if isinstance(result, list):
                result = Compound(result)
                self.copy_attributes_to(result, ["wrapped", "_NodeMixin__children"])

        if SkipClean.clean:
            result = result.clean()

        return result

    def __sub__(self, other: Shape | Sequence[Shape]) -> Compound:
        """Cut other to self `-` operator"""
        difference = Shape.__sub__(self, other)
        difference = Compound(
            difference if isinstance(difference, list) else [difference]
        )
        self.copy_attributes_to(difference, ["wrapped", "_NodeMixin__children"])

        return difference

    def __and__(self, other: Shape | Sequence[Shape]) -> Compound:
        """Intersect other to self `&` operator"""
        intersection = Shape.__and__(self, other)
        intersection = Compound(
            intersection if isinstance(intersection, list) else [intersection]
        )
        self.copy_attributes_to(intersection, ["wrapped", "_NodeMixin__children"])
        return intersection

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this Shape"""
        if self.wrapped is None:
            return ShapeList()
        if isinstance(self.wrapped, TopoDS_Compound):
            # pylint: disable=not-an-iterable
            sub_compounds = [c for c in self if isinstance(c.wrapped, TopoDS_Compound)]
            sub_compounds.append(self)
        else:
            sub_compounds = []
        return ShapeList(sub_compounds)

    def compound(self) -> Compound:
        """Return the Compound"""
        shape_list = self.compounds()
        entity_count = len(shape_list)
        if entity_count != 1:
            warnings.warn(
                f"Found {entity_count} compounds, returning first",
                stacklevel=2,
            )
        return shape_list[0] if shape_list else None

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
            tuple[bool, tuple[Shape, Shape], float]:
                do the object intersect, intersecting objects, volume of intersection
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
            bbox_intersection = children_bbox[child_index_pair[0]].intersect(
                children_bbox[child_index_pair[1]]
            )
            bbox_common_volume = (
                0.0 if isinstance(bbox_intersection, list) else bbox_intersection.volume
            )
            if bbox_common_volume > tolerance:
                obj_intersection = children[child_index_pair[0]].intersect(
                    children[child_index_pair[1]]
                )
                common_volume = (
                    0.0
                    if isinstance(obj_intersection, list)
                    else obj_intersection.volume
                )
                if common_volume > tolerance:
                    return (
                        True,
                        (children[child_index_pair[0]], children[child_index_pair[1]]),
                        common_volume,
                    )
        return (False, (), 0.0)

    @classmethod
    def make_text(
        cls,
        txt: str,
        font_size: float,
        font: str = "Arial",
        font_path: Optional[str] = None,
        font_style: FontStyle = FontStyle.REGULAR,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
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
            align (Union[Align, tuple[Align, Align]], optional): align min, center, or max
                of object. Defaults to (Align.CENTER, Align.CENTER).
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
        # pylint: disable=too-many-locals

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

        logger.info(
            "Creating text with font %s located at %s",
            font_t.FontName().ToCString(),
            font_t.FontPath(font_kind).ToCString(),
        )

        builder = Font_BRepTextBuilder()
        font_i = StdPrs_BRepFont(
            NCollection_Utf8String(font_t.FontName().ToCString()),
            font_kind,
            float(font_size),
        )
        text_flat = Compound(builder.Perform(font_i, NCollection_Utf8String(txt)))

        # Align the text from the bounding box
        align = tuplify(align, 2)
        text_flat = text_flat.translate(
            Vector(*text_flat.bounding_box().to_align_offset(align))
        )

        if text_path is not None:
            path_length = text_path.length
            text_flat = Compound([position_face(f) for f in text_flat.faces()])

        return text_flat

    @classmethod
    def make_triad(cls, axes_scale: float) -> Compound:
        """The coordinate system triad (X, Y, Z axes)"""
        x_axis = Edge.make_line((0, 0, 0), (axes_scale, 0, 0))
        y_axis = Edge.make_line((0, 0, 0), (0, axes_scale, 0))
        z_axis = Edge.make_line((0, 0, 0), (0, 0, axes_scale))
        arrow_arc = Edge.make_spline(
            [(0, 0, 0), (-axes_scale / 20, axes_scale / 30, 0)],
            [(-1, 0, 0), (-1, 1.5, 0)],
        )
        arrow = Wire([arrow_arc, copy.copy(arrow_arc).mirror(Plane.XZ)])
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
        triad = Curve(
            [
                x_axis,
                y_axis,
                z_axis,
                arrow.moved(Location(x_axis @ 1)),
                arrow.rotate(Axis.Z, 90).moved(Location(y_axis @ 1)),
                arrow.rotate(Axis.Y, -90).moved(Location(z_axis @ 1)),
                *x_label,
                *y_label,
                *z_label,
            ]
        )

        return triad

    def __iter__(self) -> Iterator[Shape]:
        """
        Iterate over subshapes.

        """

        iterator = TopoDS_Iterator(self.wrapped)

        while iterator.More():
            yield Compound.cast(iterator.Value())
            iterator.Next()

    def __len__(self) -> int:
        """Return the number of subshapes"""
        count = 0
        if self.wrapped is not None:
            for _ in self:
                count += 1
        return count

    def __bool__(self) -> bool:
        """
        Check if empty.
        """

        return TopoDS_Iterator(self.wrapped).More()

    def get_type(
        self,
        obj_type: Union[
            Type[Vertex], Type[Edge], Type[Face], Type[Shell], Type[Solid], Type[Wire]
        ],
    ) -> list[Union[Vertex, Edge, Face, Shell, Solid, Wire]]:
        """get_type

        Extract the objects of the given type from a Compound. Note that this
        isn't the same as Faces() etc. which will extract Faces from Solids.

        Args:
            obj_type (Union[Vertex, Edge, Face, Shell, Solid, Wire]): Object types to extract

        Returns:
            list[Union[Vertex, Edge, Face, Shell, Solid, Wire]]: Extracted objects
        """

        type_map = {
            Vertex: TopAbs_ShapeEnum.TopAbs_VERTEX,
            Edge: TopAbs_ShapeEnum.TopAbs_EDGE,
            Face: TopAbs_ShapeEnum.TopAbs_FACE,
            Shell: TopAbs_ShapeEnum.TopAbs_SHELL,
            Solid: TopAbs_ShapeEnum.TopAbs_SOLID,
            Wire: TopAbs_ShapeEnum.TopAbs_WIRE,
            Compound: TopAbs_ShapeEnum.TopAbs_COMPOUND,
        }
        results = []
        for comp in self.compounds():
            iterator = TopoDS_Iterator()
            iterator.Initialize(comp.wrapped)
            while iterator.More():
                child = iterator.Value()
                if child.ShapeType() == type_map[obj_type]:
                    results.append(obj_type(downcast(child)))
                iterator.Next()

        return results

    def unwrap(self, fully: bool = True) -> Union[Self, Shape]:
        """Strip unnecessary Compound wrappers

        Args:
            fully (bool, optional): return base shape without any Compound
                wrappers (otherwise one Compound is left). Defaults to True.

        Returns:
            Union[Self, Shape]: base shape
        """
        if len(self) == 1:
            single_element = next(iter(self))
            self.copy_attributes_to(single_element, ["wrapped", "_NodeMixin__children"])

            # If the single element is another Compound, unwrap it recursively
            if isinstance(single_element, Compound):
                # Unwrap recursively and copy attributes down
                unwrapped = single_element.unwrap(fully)
                if not fully:
                    unwrapped = type(self)(unwrapped.wrapped)
                self.copy_attributes_to(unwrapped, ["wrapped", "_NodeMixin__children"])
                return unwrapped

            return single_element if fully else self

        # If there are no elements or more than one element, return self
        return self


class Part(Compound):
    """A Compound containing 3D objects - aka Solids"""

    _dim = 3

    @property
    def _dim(self) -> int:
        return 3


class Sketch(Compound):
    """A Compound containing 2D objects - aka Faces"""

    _dim = 2

    @property
    def _dim(self) -> int:
        return 2


class Curve(Compound):
    """A Compound containing 1D objects - aka Edges"""

    _dim = 1

    @property
    def _dim(self) -> int:
        return 1

    __add__ = Mixin1D.__add__

    def __matmul__(self, position: float) -> Vector:
        """Position on curve operator @ - only works if continuous"""
        return Wire(self.edges()).position_at(position)

    def __mod__(self, position: float) -> Vector:
        """Tangent on wire operator % - only works if continuous"""
        return Wire(self.edges()).tangent_at(position)

    def __xor__(self, position: float) -> Location:
        """Location on wire operator ^ - only works if continuous"""
        return Wire(self.edges()).location_at(position)

    def wires(self) -> list[Wire]:
        """A list of wires created from the edges"""
        return Wire.combine(self.edges())


class Edge(Mixin1D, Shape):
    """An Edge in build123d is a fundamental element in the topological data structure
    representing a one-dimensional geometric entity within a 3D model. It encapsulates
    information about a curve, which could be a line, arc, or other parametrically
    defined shape. Edge is crucial in for precise modeling and manipulation of curves,
    facilitating operations like filleting, chamfering, and Boolean operations. It
    serves as a building block for constructing complex structures, such as wires
    and faces."""

    # pylint: disable=too-many-public-methods

    order = 1.0

    @property
    def _dim(self) -> int:
        return 1

    def __init__(
        self,
        obj: Optional[TopoDS_Shape | Axis] = None,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build an Edge from an OCCT TopoDS_Shape/TopoDS_Edge

        Args:
            obj (TopoDS_Shape | Axis, optional): OCCT Edge or Axis.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

        if isinstance(obj, Axis):
            obj = BRepBuilderAPI_MakeEdge(
                Geom_Line(
                    obj.position.to_pnt(),
                    obj.direction.to_dir(),
                )
            ).Edge()

        super().__init__(
            obj=obj,
            label=label,
            color=color,
            parent=parent,
        )

    def geom_adaptor(self) -> BRepAdaptor_Curve:
        """Return the Geom Curve from this Edge"""
        return BRepAdaptor_Curve(self.wrapped)

    def close(self) -> Union[Edge, Wire]:
        """Close an Edge"""
        if not self.is_closed:
            return_value = Wire([self]).close()
        else:
            return_value = self

        return return_value

    def to_wire(self) -> Wire:
        """Edge as Wire"""
        return Wire([self])

    @property
    def arc_center(self) -> Vector:
        """center of an underlying circle or ellipse geometry."""

        geom_type = self.geom_type
        geom_adaptor = self.geom_adaptor()

        if geom_type == GeomType.CIRCLE:
            return_value = Vector(geom_adaptor.Circle().Position().Location())
        elif geom_type == GeomType.ELLIPSE:
            return_value = Vector(geom_adaptor.Ellipse().Position().Location())
        else:
            raise ValueError(f"{geom_type} has no arc center")

        return return_value

    def find_tangent(
        self,
        angle: float,
    ) -> list[float]:
        """find_tangent

        Find the parameter values of self where the tangent is equal to angle.

        Args:
            angle (float): target angle in degrees

        Returns:
            list[float]: u values between 0.0 and 1.0
        """
        angle = angle % 360  # angle needs to always be positive 0..360

        if self.geom_type == GeomType.LINE:
            if self.tangent_angle_at(0) == angle:
                u_values = [0]
            else:
                u_values = []
        else:
            # Solve this problem geometrically by creating a tangent curve and finding intercepts
            periodic = int(self.is_closed)  # if closed don't include end point
            tan_pnts = []
            previous_tangent = None

            # When angles go from 360 to 0 a discontinuity is created so add 360 to these
            # values and intercept another line
            discontinuities = 0.0
            for i in range(101 - periodic):
                tangent = self.tangent_angle_at(i / 100) + discontinuities * 360
                if (
                    previous_tangent is not None
                    and abs(previous_tangent - tangent) > 300
                ):
                    discontinuities = copysign(1.0, previous_tangent - tangent)
                    tangent += 360 * discontinuities
                previous_tangent = tangent
                tan_pnts.append((i / 100, tangent))

            # Generate a first differential curve from the tangent points
            tan_curve = Edge.make_spline(tan_pnts)

            # Use the bounding box to find the min and max values
            tan_curve_bbox = tan_curve.bounding_box()
            min_range = 360 * (floor(tan_curve_bbox.min.Y / 360))
            max_range = 360 * (ceil(tan_curve_bbox.max.Y / 360))

            # Create a horizontal line for each 360 cycle and intercept it
            intercept_pnts = []
            for i in range(min_range, max_range + 1, 360):
                line = Edge.make_line((0, angle + i, 0), (100, angle + i, 0))
                intercept_pnts.extend(tan_curve.find_intersection_points(line))

            u_values = [p.X for p in intercept_pnts]

        return u_values

    def _intersect_with_edge(self, edge: Edge) -> tuple[list[Vertex], list[Edge]]:
        """find intersection vertices and edges"""

        # Find any intersection points
        vertex_intersections = [
            Vertex(pnt) for pnt in self.find_intersection_points(edge)
        ]

        # Find Edge/Edge overlaps
        intersect_op = BRepAlgoAPI_Common()
        edge_intersections = self._bool_op((self,), (edge,), intersect_op).edges()

        return vertex_intersections, edge_intersections

    def find_intersection_points(
        self, other: Axis | Edge = None, tolerance: float = TOLERANCE
    ) -> ShapeList[Vector]:
        """find_intersection_points

        Determine the points where a 2D edge crosses itself or another 2D edge

        Args:
            other (Axis | Edge): curve to compare with
            tolerance (float, optional): the precision of computing the intersection points.
                 Defaults to TOLERANCE.

        Returns:
            ShapeList[Vector]: list of intersection points
        """
        # Convert an Axis into an edge at least as large as self and Axis start point
        if isinstance(other, Axis):
            self_bbox_w_edge = self.bounding_box().add(
                Vertex(other.position).bounding_box()
            )
            other = Edge.make_line(
                other.position + other.direction * (-1 * self_bbox_w_edge.diagonal),
                other.position + other.direction * self_bbox_w_edge.diagonal,
            )
        # To determine the 2D plane to work on
        plane = self.common_plane(other)
        if plane is None:
            raise ValueError("All objects must be on the same plane")
        # Convert the plane into a Geom_Surface
        pln_shape = BRepBuilderAPI_MakeFace(plane.wrapped).Face()
        edge_surface = BRep_Tool.Surface_s(pln_shape)

        self_2d_curve: Geom2d_Curve = BRep_Tool.CurveOnPlane_s(
            self.wrapped,
            edge_surface,
            TopLoc_Location(),
            self.param_at(0),
            self.param_at(1),
        )
        if other is not None:
            edge_2d_curve: Geom2d_Curve = BRep_Tool.CurveOnPlane_s(
                other.wrapped,
                edge_surface,
                TopLoc_Location(),
                other.param_at(0),
                other.param_at(1),
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
        # Convert back to global coordinates
        crosses = [plane.from_local_coords(p) for p in crosses]

        # crosses may contain points beyond the ends of the edge so
        # .. filter those out
        valid_crosses = []
        for pnt in crosses:
            try:
                if other is not None:
                    if (
                        self.distance_to(pnt) <= TOLERANCE
                        and other.distance_to(pnt) <= TOLERANCE
                    ):
                        valid_crosses.append(pnt)
                else:
                    if self.distance_to(pnt) <= TOLERANCE:
                        valid_crosses.append(pnt)
            except ValueError:
                pass  # skip invalid points

        return ShapeList(valid_crosses)

    def intersect(
        self, *to_intersect: Edge | Axis
    ) -> Optional[Shape | ShapeList[Shape]]:
        """intersect Edge with Edge or Axis

        Args:
            other (Union[Edge, Axis]): other object

        Returns:
            Union[Shape, None]: Compound of vertices and/or edges
        """
        edges = [Edge(obj) if isinstance(obj, Axis) else obj for obj in to_intersect]
        if not all(isinstance(obj, Edge) for obj in edges):
            raise TypeError(
                "Only Edge or Axis instances are supported for intersection"
            )

        # Find any intersection points
        points_sets: list[set[Vector]] = []
        for edge_pair in combinations([self] + edges, 2):
            intersection_points = edge_pair[0].find_intersection_points(edge_pair[1])
            points_sets.append(set(intersection_points))

        # Find the intersection of all sets
        common_points = set.intersection(*points_sets)
        common_vertices = [Vertex(*pnt) for pnt in common_points]

        # Find Edge/Edge overlaps
        common_edges = self._bool_op((self,), edges, BRepAlgoAPI_Common()).edges()

        if common_vertices or common_edges:
            # If there is just one vertex or edge return it
            if len(common_vertices) == 1 and len(common_edges) == 0:
                return common_vertices[0]
            if len(common_vertices) == 0 and len(common_edges) == 1:
                return common_edges[0]
            return ShapeList(common_vertices + common_edges)
        return None

    def reversed(self) -> Edge:
        """Return a copy of self with the opposite orientation"""
        reversed_edge = copy.deepcopy(self)
        first: float = self.param_at(0)
        last: float = self.param_at(1)
        curve = BRep_Tool.Curve_s(self.wrapped, first, last)
        first = curve.ReversedParameter(first)
        last = curve.ReversedParameter(last)
        topods_edge = BRepBuilderAPI_MakeEdge(curve.Reversed(), last, first).Edge()
        reversed_edge.wrapped = topods_edge
        return reversed_edge

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
            raise ValueError(f"start ({start}) must be less than end ({end})")

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

    def trim_to_length(self, start: float, length: float) -> Edge:
        """trim_to_length

        Create a new edge starting at the given normalized parameter of a
        given length.

        Args:
            start (float): 0.0 <= start < 1.0
            length (float): target length

        Returns:
            Edge: trimmed edge
        """
        new_curve = BRep_Tool.Curve_s(
            copy.deepcopy(self).wrapped, self.param_at(0), self.param_at(1)
        )

        # Create an adaptor for the curve
        adaptor_curve = GeomAdaptor_Curve(new_curve)

        # Find the parameter corresponding to the desired length
        parm_start = self.param_at(start)
        abscissa_point = GCPnts_AbscissaPoint(adaptor_curve, length, parm_start)

        # Get the parameter at the desired length
        parm_end = abscissa_point.Parameter()

        # Trim the curve to the desired length
        trimmed_curve = Geom_TrimmedCurve(new_curve, parm_start, parm_end)

        new_edge = BRepBuilderAPI_MakeEdge(trimmed_curve).Edge()
        return Edge(new_edge)

    def param_at_point(self, point: VectorLike) -> float:
        """Normalized parameter at point along Edge"""

        # Note that this search algorithm would ideally be replaced with
        # an OCP based solution, something like that which is shown below.
        # However, there are known issues with the OCP methods for some
        # curves which may return negative values or incorrect values at
        # end points. Also note that this search takes about 1.5ms while
        # the OCP methods take about 0.4ms.
        #
        # curve = BRep_Tool.Curve_s(self.wrapped, float(), float())
        # param_min, param_max = BRep_Tool.Range_s(self.wrapped)
        # projector = GeomAPI_ProjectPointOnCurve(point.to_pnt(), curve)
        # param_value = projector.LowerDistanceParameter()
        # u_value = (param_value - param_min) / (param_max - param_min)

        point = Vector(point)

        if not isclose_b(self.distance_to(point), 0, abs_tol=TOLERANCE):
            raise ValueError(f"point ({point}) is not on edge")

        # Function to be minimized
        def func(param: ndarray) -> float:
            return (self.position_at(param[0]) - point).length

        # Find the u value that results in a point within tolerance of the target
        initial_guess = max(
            0.0, min(1.0, (point - self.position_at(0)).length / self.length)
        )
        result = minimize(
            func,
            x0=initial_guess,
            method="Nelder-Mead",
            bounds=[(0.0, 1.0)],
            tol=TOLERANCE,
        )
        u_value = float(result.x[0])
        return u_value

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
            ccw = angular_direction == AngularDirection.COUNTER_CLOCKWISE
            if ccw:
                start = radians(start_angle)
                end = radians(end_angle)
            else:
                start = radians(end_angle)
                end = radians(start_angle)
            circle_geom = GC_MakeArcOfCircle(circle_gp, start, end, ccw).Value()
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
        # pylint: disable=too-many-locals
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
        # pylint: disable=too-many-locals
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

        # Determine the length of the 2d line which will be wrapped around the surface
        line_sign = -1 if lefthand else 1
        line_dir = Vector(line_sign * 2 * pi, pitch).normalized()
        line_len = (height / line_dir.Y) / cos(radians(angle))

        # Create an infinite 2d line in the direction of the  helix
        helix_line = Geom2d_Line(gp_Pnt2d(0, 0), gp_Dir2d(line_dir.X, line_dir.Y))
        # Trim the line to the desired length
        helix_curve = Geom2d_TrimmedCurve(
            helix_line, 0, line_len, theAdjustPeriodic=True
        )

        # 3. Wrap the line around the surface
        edge_builder = BRepBuilderAPI_MakeEdge(helix_curve, geom_surf)
        topods_edge = edge_builder.Edge()

        # 4. Convert the edge made with 2d geometry to 3d
        BRepLib.BuildCurves3d_s(topods_edge, 1e-9, MaxSegment=2000)

        return cls(topods_edge)

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
        wire = Wire([self])
        projected_wires = wire.project_to_shape(target_object, direction, center)
        projected_edges = [w.edges()[0] for w in projected_wires]
        return projected_edges

    def to_axis(self) -> Axis:
        """Translate a linear Edge to an Axis"""
        if self.geom_type != GeomType.LINE:
            raise ValueError(
                f"to_axis is only valid for linear Edges not {self.geom_type}"
            )
        return Axis(self.position_at(0), self.position_at(1) - self.position_at(0))


class Face(Mixin2D, Shape):
    """A Face in build123d represents a 3D bounded surface within the topological data
    structure. It encapsulates geometric information, defining a face of a 3D shape.
    These faces are integral components of complex structures, such as solids and
    shells. Face enables precise modeling and manipulation of surfaces, supporting
    operations like trimming, filleting, and Boolean operations."""

    # pylint: disable=too-many-public-methods

    order = 2.0

    @property
    def _dim(self) -> int:
        return 2

    @overload
    def __init__(
        self,
        obj: TopoDS_Shape,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a Face from an OCCT TopoDS_Shape/TopoDS_Face

        Args:
            obj (TopoDS_Shape, optional): OCCT Face.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    @overload
    def __init__(
        self,
        outer_wire: Wire,
        inner_wires: Iterable[Wire] = None,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a planar Face from a boundary Wire with optional hole Wires.

        Args:
            outer_wire (Wire): closed perimeter wire
            inner_wires (Iterable[Wire], optional): holes. Defaults to None.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    def __init__(self, *args, **kwargs):
        outer_wire, inner_wires, obj, label, color, parent = (None,) * 6

        if args:
            l_a = len(args)
            if isinstance(args[0], TopoDS_Shape):
                obj, label, color, parent = args[:4] + (None,) * (4 - l_a)
            elif isinstance(args[0], Wire):
                outer_wire, inner_wires, label, color, parent = args[:5] + (None,) * (
                    5 - l_a
                )

        unknown_args = ", ".join(
            set(kwargs.keys()).difference(
                [
                    "outer_wire",
                    "inner_wires",
                    "obj",
                    "label",
                    "color",
                    "parent",
                ]
            )
        )
        if unknown_args:
            raise ValueError(f"Unexpected argument(s) {unknown_args}")

        obj = kwargs.get("obj", obj)
        outer_wire = kwargs.get("outer_wire", outer_wire)
        inner_wires = kwargs.get("inner_wires", inner_wires)
        label = kwargs.get("label", label)
        color = kwargs.get("color", color)
        parent = kwargs.get("parent", parent)

        if outer_wire is not None:
            inner_topods_wires = (
                [w.wrapped for w in inner_wires] if inner_wires is not None else []
            )
            obj = _make_topods_face_from_wires(outer_wire.wrapped, inner_topods_wires)

        super().__init__(
            obj=obj,
            label="" if label is None else label,
            color=color,
            parent=parent,
        )
        # Faces can optionally record the plane it was created on for later extrusion
        self.created_on: Plane = None

    @property
    def length(self) -> float:
        """length of planar face"""
        result = None
        if self.is_planar:
            # Reposition on Plane.XY
            flat_face = Plane(self).to_local_coords(self)
            face_vertices = flat_face.vertices().sort_by(Axis.X)
            result = face_vertices[-1].X - face_vertices[0].X
        return result

    @property
    def volume(self) -> float:
        """volume - the volume of this Face, which is always zero"""
        return 0.0

    @property
    def width(self) -> float:
        """width of planar face"""
        result = None
        if self.is_planar:
            # Reposition on Plane.XY
            flat_face = Plane(self).to_local_coords(self)
            face_vertices = flat_face.vertices().sort_by(Axis.Y)
            result = face_vertices[-1].Y - face_vertices[0].Y
        return result

    @property
    def geometry(self) -> str:
        """geometry of planar face"""
        result = None
        if self.is_planar:
            flat_face = Plane(self).to_local_coords(self)
            flat_face_edges = flat_face.edges()
            if all(e.geom_type == GeomType.LINE for e in flat_face_edges):
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
                        edge_directions[0].get_angle(edge_directions[1]) == 90
                        for edge_directions in edge_pair_directions
                    ):
                        result = "RECTANGLE"
                        if len(flat_face_edges.group_by(SortBy.LENGTH)) == 1:
                            result = "SQUARE"

        return result

    @property
    def center_location(self) -> Location:
        """Location at the center of face"""
        origin = self.position_at(0.5, 0.5)
        return Plane(origin, z_dir=self.normal_at(origin)).location

    @property
    def is_planar(self) -> bool:
        """Is the face planar even though its geom_type may not be PLANE"""
        return self.is_planar_face

    def geom_adaptor(self) -> Geom_Surface:
        """Return the Geom Surface for this Face"""
        return BRep_Tool.Surface_s(self.wrapped)

    def _uv_bounds(self) -> Tuple[float, float, float, float]:
        """Return the u min, u max, v min, v max values"""
        return BRepTools.UVBounds_s(self.wrapped)

    @overload
    def normal_at(self, surface_point: VectorLike = None) -> Vector:
        """normal_at point on surface

        Args:
            surface_point (VectorLike, optional): a point that lies on the surface where
                the normal. Defaults to the center (None).

        Returns:
            Vector: surface normal direction
        """

    @overload
    def normal_at(self, u: float, v: float) -> Vector:
        """normal_at u, v values on Face

        Args:
            u (float): the horizontal coordinate in the parameter space of the Face,
                between 0.0 and 1.0
            v (float): the vertical coordinate in the parameter space of the Face,
                between 0.0 and 1.0
                Defaults to the center (None/None)

        Raises:
            ValueError: Either neither or both u v values must be provided

        Returns:
            Vector: surface normal direction
        """

    def normal_at(self, *args, **kwargs) -> Vector:
        """normal_at

        Computes the normal vector at the desired location on the face.

        Args:
            surface_point (VectorLike, optional): a point that lies on the surface where the normal.
                Defaults to None.

        Returns:
            Vector: surface normal direction
        """
        surface_point, u, v = (None,) * 3

        if args:
            if isinstance(args[0], Sequence):
                surface_point = args[0]
            elif isinstance(args[0], (int, float)):
                u = args[0]
            if len(args) == 2 and isinstance(args[1], (int, float)):
                v = args[1]

        unknown_args = ", ".join(
            set(kwargs.keys()).difference(["surface_point", "u", "v"])
        )
        if unknown_args:
            raise ValueError(f"Unexpected argument(s) {unknown_args}")

        surface_point = kwargs.get("surface_point", surface_point)
        u = kwargs.get("u", u)
        v = kwargs.get("v", v)
        if surface_point is None and u is None and v is None:
            u, v = 0.5, 0.5
        elif surface_point is None and sum(i is None for i in [u, v]) == 1:
            raise ValueError("Both u & v values must be specified")

        # get the geometry
        surface = self.geom_adaptor()

        if surface_point is None:
            u_val0, u_val1, v_val0, v_val1 = self._uv_bounds()
            u_val = u * (u_val0 + u_val1)
            v_val = v * (v_val0 + v_val1)
        else:
            # project point on surface
            projector = GeomAPI_ProjectPointOnSurf(
                Vector(surface_point).to_pnt(), surface
            )

            u_val, v_val = projector.LowerDistanceParameters()

        gp_pnt = gp_Pnt()
        normal = gp_Vec()
        BRepGProp_Face(self.wrapped).Normal(u_val, v_val, gp_pnt, normal)

        return Vector(normal).normalized()

    def position_at(self, u: float, v: float) -> Vector:
        """position_at

        Computes a point on the Face given u, v coordinates.

        Args:
            u (float): the horizontal coordinate in the parameter space of the Face,
                between 0.0 and 1.0
            v (float): the vertical coordinate in the parameter space of the Face,
                between 0.0 and 1.0

        Returns:
            Vector: point on Face
        """
        u_val0, u_val1, v_val0, v_val1 = self._uv_bounds()
        u_val = u_val0 + u * (u_val1 - u_val0)
        v_val = v_val0 + v * (v_val1 - v_val0)

        gp_pnt = gp_Pnt()
        normal = gp_Vec()
        BRepGProp_Face(self.wrapped).Normal(u_val, v_val, gp_pnt, normal)

        return Vector(gp_pnt)

    def location_at(self, u: float, v: float, x_dir: VectorLike = None) -> Location:
        """Location at the u/v position of face"""
        origin = self.position_at(u, v)
        if x_dir is None:
            pln = Plane(origin, z_dir=self.normal_at(origin))
        else:
            pln = Plane(origin, x_dir=Vector(x_dir), z_dir=self.normal_at(origin))
        return Location(pln)

    def center(self, center_of=CenterOf.GEOMETRY) -> Vector:
        """Center of Face

        Return the center based on center_of

        Args:
            center_of (CenterOf, optional): centering option. Defaults to CenterOf.GEOMETRY.

        Returns:
            Vector: center
        """
        if (center_of == CenterOf.MASS) or (
            center_of == CenterOf.GEOMETRY and self.is_planar
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

    def inner_wires(self) -> ShapeList[Wire]:
        """Extract the inner or hole wires from this Face"""
        outer = self.outer_wire()

        return ShapeList([w for w in self.wires() if not w.is_same(outer)])

    def wire(self) -> Wire:
        """Return the outerwire, generate a warning if inner_wires present"""
        if self.inner_wires():
            warnings.warn(
                "Found holes, returning outer_wire",
                stacklevel=2,
            )
        return self.outer_wire()

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
            plane.wrapped, -width * 0.5, width * 0.5, -height * 0.5, height * 0.5
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
    def sew_faces(cls, faces: Iterable[Face]) -> ShapeList[ShapeList[Face]]:
        """sew faces

        Group contiguous faces and return them in a list of ShapeList

        Args:
            faces (Iterable[Face]): Faces to sew together

        Raises:
            RuntimeError: OCCT SewedShape generated unexpected output

        Returns:
            ShapeList[ShapeList[Face]]: grouped contiguous faces
        """
        # Sew the faces
        sewed_shape = _sew_topods_faces([f.wrapped for f in faces])
        top_level_shapes = get_top_level_topods_shapes(sewed_shape)
        sewn_faces = ShapeList()

        # For each of the top level shapes create a ShapeList of Face
        for top_level_shape in top_level_shapes:
            if isinstance(top_level_shape, TopoDS_Face):
                sewn_faces.append(ShapeList([Face(top_level_shape)]))
            elif isinstance(top_level_shape, TopoDS_Shell):
                sewn_faces.append(Shell(top_level_shape).faces())
            elif isinstance(top_level_shape, TopoDS_Solid):
                sewn_faces.append(
                    ShapeList(
                        Face(f) for f in _topods_entities(top_level_shape, "Face")
                    )
                )
            else:
                raise RuntimeError(
                    f"SewedShape returned a {type(top_level_shape)} which was unexpected"
                )

        return sewn_faces

    @classmethod
    def sweep(
        cls,
        profile: Union[Curve, Edge, Wire],
        path: Union[Curve, Edge, Wire],
        transition=Transition.TRANSFORMED,
    ) -> Face:
        """sweep

        Sweep a 1D profile along a 1D path. Both the profile and path must be composed
        of only 1 Edge.

        Args:
            profile (Union[Curve,Edge,Wire]): the object to sweep
            path (Union[Curve,Edge,Wire]): the path to follow when sweeping
            transition (Transition, optional): handling of profile orientation at C1 path
                discontinuities. Defaults to Transition.TRANSFORMED.

        Raises:
            ValueError: Only 1 Edge allowed in profile & path

        Returns:
            Face: resulting face, may be non-planar
        """
        # Note: BRepOffsetAPI_MakePipe is an option here
        # pipe_sweep = BRepOffsetAPI_MakePipe(path.wrapped, profile.wrapped)
        # pipe_sweep.Build()
        # return Face(pipe_sweep.Shape())

        if len(profile.edges()) != 1 or len(path.edges()) != 1:
            raise ValueError("Use Shell.sweep for multi Edge objects")
        profile = Wire([profile.edge()])
        path = Wire([path.edge()])
        builder = BRepOffsetAPI_MakePipeShell(path.wrapped)
        builder.Add(profile.wrapped, False, False)
        builder.SetTransitionMode(Shape._transModeDict[transition])
        builder.Build()
        result = Face(builder.Shape())
        if SkipClean.clean:
            result = result.clean()

        return result

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
        The first dimension correspond to points on the vertical direction in the parameter
        space of the face. The second dimension correspond to points on the horizontal
        direction in the parameter space of the face. The 2 dimensions are U,V dimensions
        of the parameter space of the face.

        Args:
            points (list[list[VectorLike]]): a 2D list of points, first dimension is V
                parameters second is U parameters.
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
    def make_bezier_surface(
        cls,
        points: list[list[VectorLike]],
        weights: list[list[float]] = None,
    ) -> Face:
        """make_bezier_surface

        Construct a Bézier surface from the provided 2d array of points.

        Args:
            points (list[list[VectorLike]]): a 2D list of control points
            weights (list[list[float]], optional): control point weights. Defaults to None.

        Raises:
            ValueError: Too few control points
            ValueError: Too many control points
            ValueError: A weight is required for each control point

        Returns:
            Face: a potentially non-planar face
        """
        if len(points) < 2 or len(points[0]) < 2:
            raise ValueError(
                "At least two control points must be provided (start, end)"
            )
        if len(points) > 25 or len(points[0]) > 25:
            raise ValueError("The maximum number of control points is 25")
        if weights and (
            len(points) != len(weights) or len(points[0]) != len(weights[0])
        ):
            raise ValueError("A weight must be provided for each control point")

        points_ = TColgp_HArray2OfPnt(1, len(points), 1, len(points[0]))
        for i, row in enumerate(points):
            for j, point in enumerate(row):
                points_.SetValue(i + 1, j + 1, Vector(point).to_pnt())

        if weights:
            weights_ = TColStd_HArray2OfReal(1, len(weights), 1, len(weights[0]))
            for i, row in enumerate(weights):
                for j, weight in enumerate(row):
                    weights_.SetValue(i + 1, j + 1, float(weight))
            bezier = Geom_BezierSurface(points_, weights_)
        else:
            bezier = Geom_BezierSurface(points_)

        return cls(BRepBuilderAPI_MakeFace(bezier, Precision.Confusion_s()).Face())

    @classmethod
    def make_surface(
        cls,
        exterior: Union[Wire, Iterable[Edge]],
        surface_points: Iterable[VectorLike] = None,
        interior_wires: Iterable[Wire] = None,
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
        # pylint: disable=too-many-branches
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
        elif isinstance(exterior, Iterable) and all(
            isinstance(o, Edge) for o in exterior
        ):
            outside_edges = exterior
        else:
            raise ValueError("exterior must be a Wire or list of Edges")

        for edge in outside_edges:
            surface.Add(edge.wrapped, GeomAbs_C0)

        try:
            surface.Build()
            surface_face = Face(surface.Shape())
        except (
            Standard_Failure,
            StdFail_NotDone,
            Standard_NoSuchObject,
            Standard_ConstructionError,
        ) as err:
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

    def chamfer_2d(
        self,
        distance: float,
        distance2: float,
        vertices: Iterable[Vertex],
        edge: Edge = None,
    ) -> Face:
        """Apply 2D chamfer to a face

        Args:
            distance (float): chamfer length
            distance2 (float): chamfer length
            vertices (Iterable[Vertex]): vertices to chamfer
            edge (Edge): identifies the side where length is measured. The vertices must be
                part of the edge

        Raises:
            ValueError: Cannot chamfer at this location
            ValueError: One or more vertices are not part of edge

        Returns:
            Face: face with a chamfered corner(s)

        """
        reference_edge = edge
        del edge

        chamfer_builder = BRepFilletAPI_MakeFillet2d(self.wrapped)

        vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            self.wrapped, ta.TopAbs_VERTEX, ta.TopAbs_EDGE, vertex_edge_map
        )

        for v in vertices:
            edges = vertex_edge_map.FindFromKey(v.wrapped)

            # Index or iterator access to OCP.TopTools.TopTools_ListOfShape is slow on M1 macs
            # Using First() and Last() to omit
            edges = [edges.First(), edges.Last()]

            # Need to wrap in b3d objects for comparison to work
            # ref.wrapped != edge.wrapped but ref == edge
            edges = [Mixin2D.cast(e) for e in edges]

            edge1, edge2 = Wire.order_chamfer_edges(reference_edge, edges)

            chamfer_builder.AddChamfer(
                TopoDS.Edge_s(edge1.wrapped),
                TopoDS.Edge_s(edge2.wrapped),
                distance,
                distance2,
            )

        chamfer_builder.Build()
        return self.__class__(chamfer_builder.Shape()).fix()

    def is_coplanar(self, plane: Plane) -> bool:
        """Is this planar face coplanar with the provided plane"""
        u_val0, _u_val1, v_val0, _v_val1 = self._uv_bounds()
        gp_pnt = gp_Pnt()
        normal = gp_Vec()
        BRepGProp_Face(self.wrapped).Normal(u_val0, v_val0, gp_pnt, normal)

        return (
            plane.contains(Vector(gp_pnt))
            and 1 - abs(plane.z_dir.dot(Vector(normal))) < TOLERANCE
        )

    def project_to_shape(
        self, target_object: Shape, direction: VectorLike
    ) -> ShapeList[Face | Shell]:
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

        Returns:
            ShapeList[Face]: Face(s) projected on target object ordered by distance
        """
        max_dimension = find_max_dimension([self, target_object])
        extruded_topods_self = _extrude_topods_shape(
            self.wrapped, Vector(direction) * max_dimension
        )

        intersected_shapes = ShapeList()
        if isinstance(target_object, Vertex):
            raise TypeError("projection to a vertex is not supported")
        if isinstance(target_object, Face):
            topods_shape = _topods_bool_op(
                (extruded_topods_self,), (target_object.wrapped,), BRepAlgoAPI_Common()
            )
            if not topods_shape.IsNull():
                intersected_shapes.append(Face(topods_shape))
        else:
            for target_shell in target_object.shells():
                topods_shape = _topods_bool_op(
                    (extruded_topods_self,),
                    (target_shell.wrapped,),
                    BRepAlgoAPI_Common(),
                )
                for topods_shell in get_top_level_topods_shapes(topods_shape):
                    intersected_shapes.append(Shell(topods_shell))

        intersected_shapes = intersected_shapes.sort_by(Axis(self.center(), direction))
        intersected_shapes = [
            s.face() if len(s.faces()) == 1 else s for s in intersected_shapes
        ]
        return intersected_shapes

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
        solid_classifier = BRepClass3d_SolidClassifier(self.wrapped)
        solid_classifier.Perform(gp_Pnt(*Vector(point).to_tuple()), tolerance)
        return solid_classifier.IsOnAFace()

        # surface = BRep_Tool.Surface_s(self.wrapped)
        # projector = GeomAPI_ProjectPointOnSurf(Vector(point).to_pnt(), surface)
        # return projector.LowerDistance() <= TOLERANCE


class Shell(Mixin2D, Shape):
    """A Shell is a fundamental component in build123d's topological data structure
    representing a connected set of faces forming a closed surface in 3D space. As
    part of a geometric model, it defines a watertight enclosure, commonly encountered
    in solid modeling. Shells group faces in a coherent manner, playing a crucial role
    in representing complex shapes with voids and surfaces. This hierarchical structure
    allows for efficient handling of surfaces within a model, supporting various
    operations and analyses."""

    order = 2.5

    @property
    def _dim(self) -> int:
        return 2

    def __init__(
        self,
        obj: Optional[TopoDS_Shape | Face | Iterable[Face]] = None,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a shell from an OCCT TopoDS_Shape/TopoDS_Shell

        Args:
            obj (TopoDS_Shape | Face | Iterable[Face], optional): OCCT Shell, Face or Faces.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

        if isinstance(obj, Iterable) and len(obj) == 1:
            obj = obj[0]

        if isinstance(obj, Face):
            builder = BRepBuilderAPI_MakeShell(
                BRepAdaptor_Surface(obj.wrapped).Surface().Surface()
            )
            obj = builder.Shape()
        elif isinstance(obj, Iterable):
            obj = _sew_topods_faces([f.wrapped for f in obj])

        super().__init__(
            obj=obj,
            label=label,
            color=color,
            parent=parent,
        )

    @property
    def volume(self) -> float:
        """volume - the volume of this Shell if manifold, otherwise zero"""
        if self.is_manifold:
            solid_shell = ShapeFix_Solid().SolidFromShell(self.wrapped)
            properties = GProp_GProps()
            calc_function = Shape.shape_properties_LUT[shapetype(solid_shell)]
            calc_function(solid_shell, properties)
            return properties.Mass()
        return 0.0

    def center(self) -> Vector:
        """Center of mass of the shell"""
        properties = GProp_GProps()
        BRepGProp.LinearProperties_s(self.wrapped, properties)
        return Vector(properties.CentreOfMass())

    @classmethod
    def sweep(
        cls,
        profile: Union[Curve, Edge, Wire],
        path: Union[Curve, Edge, Wire],
        transition=Transition.TRANSFORMED,
    ) -> Shell:
        """sweep

        Sweep a 1D profile along a 1D path

        Args:
            profile (Union[Curve, Edge, Wire]): the object to sweep
            path (Union[Curve, Edge, Wire]): the path to follow when sweeping
            transition (Transition, optional): handling of profile orientation at C1 path
                discontinuities. Defaults to Transition.TRANSFORMED.

        Returns:
            Shell: resulting Shell, may be non-planar
        """
        profile = Wire(profile.edges())
        path = Wire(Wire(path.edges()).order_edges())
        builder = BRepOffsetAPI_MakePipeShell(path.wrapped)
        builder.Add(profile.wrapped, False, False)
        builder.SetTransitionMode(Shape._transModeDict[transition])
        builder.Build()
        result = Shell(builder.Shape())
        if SkipClean.clean:
            result = result.clean()

        return result

    @classmethod
    def make_loft(
        cls, objs: Iterable[Union[Vertex, Wire]], ruled: bool = False
    ) -> Shell:
        """make loft

        Makes a loft from a list of wires and vertices. Vertices can appear only at the
        beginning or end of the list, but cannot appear consecutively within the list nor
        between wires. Wires may be closed or opened.

        Args:
            objs (list[Vertex, Wire]): wire perimeters or vertices
            ruled (bool, optional): stepped or smooth. Defaults to False (smooth).

        Raises:
            ValueError: Too few wires

        Returns:
            Shell: Lofted object
        """
        return cls(_make_loft(objs, False, ruled))


class Solid(Mixin3D, Shape):
    """A Solid in build123d represents a three-dimensional solid geometry
    in a topological structure. A solid is a closed and bounded volume, enclosing
    a region in 3D space. It comprises faces, edges, and vertices connected in a
    well-defined manner. Solid modeling operations, such as Boolean
    operations (union, intersection, and difference), are often performed on
    Solid objects to create or modify complex geometries."""

    order = 3.0

    @property
    def _dim(self) -> int:
        return 3

    def __init__(
        self,
        obj: TopoDS_Shape | Shell = None,
        label: str = "",
        color: Color = None,
        material: str = "",
        joints: dict[str, Joint] = None,
        parent: Compound = None,
    ):
        """Build a solid from an OCCT TopoDS_Shape/TopoDS_Solid

        Args:
            obj (TopoDS_Shape | Shell, optional): OCCT Solid or Shell.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            material (str, optional): tag for external tools. Defaults to ''.
            joints (dict[str, Joint], optional): names joints. Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

        if isinstance(obj, Shell):
            obj = Solid._make_solid(obj)

        super().__init__(
            obj=obj,
            # label="" if label is None else label,
            label=label,
            color=color,
            parent=parent,
        )
        self.material = "" if material is None else material
        self.joints = {} if joints is None else joints

    @property
    def volume(self) -> float:
        """volume - the volume of this Solid"""
        # when density == 1, mass == volume
        return Shape.compute_mass(self)

    @classmethod
    def _make_solid(cls, shell: Shell) -> TopoDS_Solid:
        """Create a Solid object from the surface shell"""
        return ShapeFix_Solid().SolidFromShell(shell.wrapped)

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
    def make_loft(
        cls, objs: Iterable[Union[Vertex, Wire]], ruled: bool = False
    ) -> Solid:
        """make loft

        Makes a loft from a list of wires and vertices. Vertices can appear only at the
        beginning or end of the list, but cannot appear consecutively within the list
        nor between wires.

        Args:
            objs (list[Vertex, Wire]): wire perimeters or vertices
            ruled (bool, optional): stepped or smooth. Defaults to False (smooth).

        Raises:
            ValueError: Too few wires

        Returns:
            Solid: Lofted object
        """
        return cls(_make_loft(objs, True, ruled))

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
    def extrude_taper(
        cls, profile: Face, direction: VectorLike, taper: float, flip_inner: bool = True
    ) -> Solid:
        """Extrude a cross section with a taper

        Extrude a cross section into a prismatic solid in the provided direction.

        Note that two difference algorithms are used. If direction aligns with
        the profile normal (which must be positive), the taper is positive and the profile
        contains no holes the OCP LocOpe_DPrism algorithm is used as it generates the most
        accurate results. Otherwise, a loft is created between the profile and the profile
        with a 2D offset set at the appropriate direction.

        Args:
            section (Face]): cross section
            normal (VectorLike): a vector along which to extrude the wires. The length
                of the vector controls the length of the extrusion.
            taper (float): taper angle in degrees.
            flip_inner (bool, optional): outer and inner geometry have opposite tapers to
                allow for part extraction when injection molding.

        Returns:
            Solid: extruded cross section
        """
        # pylint: disable=too-many-locals
        direction = Vector(direction)

        if (
            direction.normalized() == profile.normal_at()
            and Plane(profile).z_dir.Z > 0
            and taper > 0
            and not profile.inner_wires()
        ):
            prism_builder = LocOpe_DPrism(
                profile.wrapped,
                direction.length / cos(radians(taper)),
                radians(taper),
            )
            new_solid = Solid(prism_builder.Shape())
        else:
            # Determine the offset to get the taper
            offset_amt = -direction.length * tan(radians(taper))

            outer = profile.outer_wire()
            local_outer: Wire = Plane(profile).to_local_coords(outer)
            local_taper_outer = local_outer.offset_2d(
                offset_amt, kind=Kind.INTERSECTION
            )
            taper_outer = Plane(profile).from_local_coords(local_taper_outer)
            taper_outer.move(Location(direction))

            profile_wires = [profile.outer_wire()] + profile.inner_wires()

            taper_wires = []
            for i, wire in enumerate(profile_wires):
                flip = -1 if i > 0 and flip_inner else 1
                local: Wire = Plane(profile).to_local_coords(wire)
                local_taper = local.offset_2d(flip * offset_amt, kind=Kind.INTERSECTION)
                taper = Plane(profile).from_local_coords(local_taper)
                taper.move(Location(direction))
                taper_wires.append(taper)

            solids = [
                Solid.make_loft([p, t]) for p, t in zip(profile_wires, taper_wires)
            ]
            if len(solids) > 1:
                new_solid = solids[0].cut(*solids[1:])
            else:
                new_solid = solids[0]

        return new_solid

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
        # Though the signature may appear to be similar enough to extrude to merit
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
        straight_spine_w = Wire.combine([straight_spine_e])[0].wrapped

        # make an auxiliary spine
        pitch = 360.0 / angle * normal.length
        aux_spine_w = Wire(
            [Edge.make_helix(pitch, normal.length, 1, center=center, normal=normal)]
        ).wrapped

        # extrude the outer wire
        outer_solid = extrude_aux_spine(
            outer_wire.wrapped, straight_spine_w, aux_spine_w
        )

        # extrude inner wires
        inner_solids = [
            extrude_aux_spine(w.wrapped, straight_spine_w, aux_spine_w)
            for w in inner_wires
        ]

        # combine the inner solids into compound
        inner_comp = _make_topods_compound_from_shapes(inner_solids)

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
        if until in [Until.PREVIOUS, Until.FIRST]:
            direction *= -1
            until = Until.NEXT if until == Until.PREVIOUS else Until.LAST

        max_dimension = find_max_dimension([section, target_object])
        clipping_direction = (
            direction * max_dimension
            if until == Until.NEXT
            else -direction * max_dimension
        )
        direction_axis = Axis(section.center(), clipping_direction)
        # Create a linear extrusion to start
        extrusion = Solid.extrude(section, direction * max_dimension)

        # Project section onto the shape to generate faces that will clip the extrusion
        # and exclude the planar faces normal to the direction of extrusion and these
        # will have no volume when extruded
        faces = []
        for face in section.project_to_shape(target_object, direction):
            if isinstance(face, Face):
                faces.append(face)
            else:
                faces += face.faces()

        clip_faces = [
            f
            for f in faces
            if not (f.is_planar and f.normal_at().dot(direction) == 0.0)
        ]
        if not clip_faces:
            raise ValueError("provided face does not intersect target_object")

        # Create the objects that will clip the linear extrusion
        clipping_objects = [
            Solid.extrude(f, clipping_direction).fix() for f in clip_faces
        ]
        clipping_objects = [o for o in clipping_objects if o.volume > 1e-9]

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
                except Exception:
                    warnings.warn(
                        "clipping error - extrusion may be incorrect",
                        stacklevel=2,
                    )
        else:
            extrusion_parts = [extrusion.intersect(target_object)]
            for clipping_object in clipping_objects:
                try:
                    extrusion_parts.append(
                        extrusion.intersect(clipping_object)
                        .solids()
                        .sort_by(direction_axis)[0]
                    )
                except Exception:
                    warnings.warn(
                        "clipping error - extrusion may be incorrect",
                        stacklevel=2,
                    )
            extrusion = Solid.fuse(*extrusion_parts)

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
            section_face = Face(section, inner_wires)
        else:
            section_face = section

        revol_builder = BRepPrimAPI_MakeRevol(
            section_face.wrapped,
            axis.wrapped,
            angle * DEG2RAD,
            True,
        )

        return cls(revol_builder.Shape())

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

            builder.SetTransitionMode(Shape._transModeDict[transition])

            builder.Add(wire.wrapped, False, rotate)

            builder.Build()
            if make_solid:
                builder.MakeSolid()

            shapes.append(Mixin3D.cast(builder.Shape()))

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

    @classmethod
    def thicken(
        cls,
        surface: Face | Shell,
        depth: float,
        normal_override: Optional[VectorLike] = None,
    ) -> Solid:
        """Thicken Face or Shell

        Create a solid from a potentially non planar face or shell by thickening along
        the normals.

        .. image:: thickenFace.png

        Non-planar faces are thickened both towards and away from the center of the sphere.

        Args:
            depth (float): Amount to thicken face(s), can be positive or negative.
            normal_override (Vector, optional): Face only. The normal_override vector can be
                used to indicate which way is 'up', potentially flipping the face normal
                direction such that many faces with different normals all go in the same
                direction (direction need only be +/- 90 degrees from the face normal).
                Defaults to None.

        Raises:
            RuntimeError: Opencascade internal failures

        Returns:
            Solid: The resulting Solid object
        """
        # Check to see if the normal needs to be flipped
        adjusted_depth = depth
        if isinstance(surface, Face) and normal_override is not None:
            surface_center = surface.center()
            surface_normal = surface.normal_at(surface_center).normalized()
            if surface_normal.dot(Vector(normal_override).normalized()) < 0:
                adjusted_depth = -depth

        offset_builder = BRepOffset_MakeOffset()
        offset_builder.Initialize(
            surface.wrapped,
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
        offset_builder.MakeOffsetShape()
        try:
            result = Solid(offset_builder.Shape())
        except StdFail_NotDone as err:
            raise RuntimeError("Error applying thicken to given surface") from err

        return result


class Vertex(Shape):
    """A Vertex in build123d represents a zero-dimensional point in the topological
    data structure. It marks the endpoints of edges within a 3D model, defining precise
    locations in space. Vertices play a crucial role in defining the geometry of objects
    and the connectivity between edges, facilitating accurate representation and
    manipulation of 3D shapes. They hold coordinate information and are essential
    for constructing complex structures like wires, faces, and solids."""

    order = 0.0

    @property
    def _dim(self) -> int:
        return 0

    @overload
    def __init__(self):  # pragma: no cover
        """Default Vertext at the origin"""

    @overload
    def __init__(self, v: TopoDS_Vertex):  # pragma: no cover
        """Vertex from OCCT TopoDS_Vertex object"""

    @overload
    def __init__(self, X: float, Y: float, Z: float):  # pragma: no cover
        """Vertex from three float values"""

    @overload
    def __init__(self, v: Iterable[float]):
        """Vertex from Vector or other iterators"""

    @overload
    def __init__(self, v: tuple[float]):
        """Vertex from tuple of floats"""

    def __init__(self, *args, **kwargs):
        self.vertex_index = 0
        x, y, z, ocp_vx = 0, 0, 0, None

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
            if isinstance(first_arg, (tuple, Iterable)):
                try:
                    values = [float(value) for value in first_arg]
                except (TypeError, ValueError) as exc:
                    raise TypeError("Expected floats") from exc
                if len(values) < 3:
                    values += [0.0] * (3 - len(values))
                x, y, z = values
            elif isinstance(first_arg, TopoDS_Vertex):
                ocp_vx = first_arg
            else:
                raise TypeError("Expected floats, TopoDS_Vertex, or iterable")
        x = kwargs.get("X", x)
        y = kwargs.get("Y", y)
        z = kwargs.get("Z", z)
        ocp_vx = (
            downcast(BRepBuilderAPI_MakeVertex(gp_Pnt(x, y, z)).Vertex())
            if ocp_vx is None
            else ocp_vx
        )

        super().__init__(ocp_vx)
        self.X, self.Y, self.Z = self.to_tuple()

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Self:
        "Returns the right type of wrapper, given a OCCT object"

        # define the shape lookup table for casting
        constructor_lut = {
            ta.TopAbs_VERTEX: Vertex,
        }

        shape_type = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        return constructor_lut[shape_type](downcast(obj))

    @property
    def volume(self) -> float:
        """volume - the volume of this Vertex, which is always zero"""
        return 0.0

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this Shape"""
        return ShapeList((self,))  # Vertex is an iterable

    def vertex(self) -> Vertex:
        """Return the Vertex"""
        return self

    def to_tuple(self) -> tuple[float, float, float]:
        """Return vertex as three tuple of floats"""
        geom_point = BRep_Tool.Pnt_s(self.wrapped)
        return (geom_point.X(), geom_point.Y(), geom_point.Z())

    def center(self) -> Vector:
        """The center of a vertex is itself!"""
        return Vector(self)

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

    def __and__(self, *args, **kwargs):
        """intersect operator +"""
        raise NotImplementedError("Vertices can't be intersected")

    def __repr__(self) -> str:
        """To String

        Convert Vertex to String for display

        Returns:
            Vertex as String
        """
        return f"Vertex({self.X}, {self.Y}, {self.Z})"

    def __iter__(self):
        """Initialize to beginning"""
        self.vertex_index = 0
        return self

    def __next__(self):
        """return the next value"""
        if self.vertex_index == 0:
            self.vertex_index += 1
            value = self.X
        elif self.vertex_index == 1:
            self.vertex_index += 1
            value = self.Y
        elif self.vertex_index == 2:
            self.vertex_index += 1
            value = self.Z
        else:
            raise StopIteration
        return value

    def transform_shape(self, t_matrix: Matrix) -> Vertex:
        """Apply affine transform without changing type

        Transforms a copy of this Vertex by the provided 3D affine transformation matrix.
        Note that not all transformation are supported - primarily designed for translation
        and rotation.  See :transform_geometry: for more comprehensive transformations.

        Args:
            t_matrix (Matrix): affine transformation matrix

        Returns:
            Vertex: copy of transformed shape with all objects keeping their type
        """
        return Vertex(*t_matrix.multiply(Vector(self)))


class Wire(Mixin1D, Shape):
    """A Wire in build123d is a topological entity representing a connected sequence
    of edges forming a continuous curve or path in 3D space. Wires are essential
    components in modeling complex objects, defining boundaries for surfaces or
    solids. They store information about the connectivity and order of edges,
    allowing precise definition of paths within a 3D model."""

    order = 1.5

    @property
    def _dim(self) -> int:
        return 1

    @overload
    def __init__(
        self,
        obj: TopoDS_Shape,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a wire from an OCCT TopoDS_Wire

        Args:
            obj (TopoDS_Shape, optional): OCCT Wire.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    @overload
    def __init__(
        self,
        edge: Edge,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a Wire from an Edge

        Args:
            edge (Edge): Edge to convert to Wire
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    @overload
    def __init__(
        self,
        wire: Wire,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a Wire from an Wire - used when the input could be an Edge or Wire.

        Args:
            wire (Wire): Wire to convert to another Wire
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    @overload
    def __init__(
        self,
        wire: Curve,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a Wire from an Curve.

        Args:
            curve (Curve): Curve to convert to a Wire
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    @overload
    def __init__(
        self,
        edges: Iterable[Edge],
        sequenced: bool = False,
        label: str = "",
        color: Color = None,
        parent: Compound = None,
    ):
        """Build a wire from Edges

        Build a Wire from the provided unsorted Edges. If sequenced is True the
        Edges are placed in such that the end of the nth Edge is coincident with
        the n+1th Edge forming an unbroken sequence. Note that sequencing a list
        is relatively slow.

        Args:
            edges (Iterable[Edge]): Edges to assemble
            sequenced (bool, optional): arrange in order. Defaults to False.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    def __init__(self, *args, **kwargs):
        curve, edge, edges, wire, sequenced, obj, label, color, parent = (None,) * 9

        if args:
            l_a = len(args)
            if isinstance(args[0], TopoDS_Shape):
                obj, label, color, parent = args[:4] + (None,) * (4 - l_a)
            elif isinstance(args[0], Edge):
                edge, label, color, parent = args[:4] + (None,) * (4 - l_a)
            elif isinstance(args[0], Wire):
                wire, label, color, parent = args[:4] + (None,) * (4 - l_a)
            # elif isinstance(args[0], Curve):
            elif (
                hasattr(args[0], "wrapped")
                and isinstance(args[0].wrapped, TopoDS_Compound)
                and args[0].wrapped.dim == 1
            ):  # Curve
                curve, label, color, parent = args[:4] + (None,) * (4 - l_a)
            elif isinstance(args[0], Iterable):
                edges, sequenced, label, color, parent = args[:5] + (None,) * (5 - l_a)

        unknown_args = ", ".join(
            set(kwargs.keys()).difference(
                [
                    "curve",
                    "wire",
                    "edge",
                    "edges",
                    "sequenced",
                    "obj",
                    "label",
                    "color",
                    "parent",
                ]
            )
        )
        if unknown_args:
            raise ValueError(f"Unexpected argument(s) {unknown_args}")

        obj = kwargs.get("obj", obj)
        edge = kwargs.get("edge", edge)
        edges = kwargs.get("edges", edges)
        sequenced = kwargs.get("sequenced", sequenced)
        label = kwargs.get("label", label)
        color = kwargs.get("color", color)
        parent = kwargs.get("parent", parent)
        wire = kwargs.get("wire", wire)
        curve = kwargs.get("curve", curve)

        if edge is not None:
            edges = [edge]
        elif curve is not None:
            edges = curve.edges()
        if wire is not None:
            obj = wire.wrapped
        elif edges:
            obj = Wire._make_wire(edges, False if sequenced is None else sequenced)

        super().__init__(
            obj=obj,
            label="" if label is None else label,
            color=color,
            parent=parent,
        )

    def geom_adaptor(self) -> BRepAdaptor_CompCurve:
        """Return the Geom Comp Curve for this Wire"""
        return BRepAdaptor_CompCurve(self.wrapped)

    def close(self) -> Wire:
        """Close a Wire"""
        if not self.is_closed:
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
    ) -> ShapeList[Wire]:
        """combine

        Combine a list of wires and edges into a list of Wires.

        Args:
            wires (Iterable[Union[Wire, Edge]]): unsorted
            tol (float, optional): tolerance. Defaults to 1e-9.

        Returns:
            ShapeList[Wire]: Wires
        """

        edges_in = TopTools_HSequenceOfShape()
        wires_out = TopTools_HSequenceOfShape()

        for edge in [e for w in wires for e in w.edges()]:
            edges_in.Append(edge.wrapped)

        ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

        wires = ShapeList()
        for i in range(wires_out.Length()):
            wires.append(Wire(downcast(wires_out.Value(i + 1))))

        return wires

    def fix_degenerate_edges(self, precision: float) -> Wire:
        """fix_degenerate_edges

        Fix a Wire that contains degenerate (very small) edges

        Args:
            precision (float): minimum value edge length

        Returns:
            Wire: fixed wire
        """
        sf_w = ShapeFix_Wireframe(self.wrapped)
        sf_w.SetPrecision(precision)
        sf_w.SetMaxTolerance(1e-6)
        sf_w.FixSmallEdges()
        sf_w.FixWireGaps()
        return Wire(downcast(sf_w.Shape()))

    def param_at_point(self, point: VectorLike) -> float:
        """Parameter at point on Wire"""

        # OCP doesn't support this so this algorithm finds the edge that contains the
        # point, finds the u value/fractional distance of the point on that edge and
        # sums up the length of the edges from the start to the edge with the point.

        wire_length = self.length
        edge_list = self.edges()
        target = self.position_at(0)  # To start, find the edge at the beginning
        distance = 0.0  # distance along wire
        found = False

        while edge_list:
            # Find the edge closest to the target
            edge = sorted(edge_list, key=lambda e: e.distance_to(target))[0]
            edge_list.pop(edge_list.index(edge))

            # The edge might be flipped requiring the u value to be reversed
            edge_p0 = edge.position_at(0)
            edge_p1 = edge.position_at(1)
            flipped = (target - edge_p0).length > (target - edge_p1).length

            # Set the next start to "end" of the current edge
            target = edge_p0 if flipped else edge_p1

            # If this edge contain the point, get a fractional distance - otherwise the whole
            if edge.distance_to(point) <= TOLERANCE:
                found = True
                u_value = edge.param_at_point(point)
                if flipped:
                    distance += (1 - u_value) * edge.length
                else:
                    distance += u_value * edge.length
                break
            distance += edge.length

        if not found:
            raise ValueError(f"{point} not on wire")

        return distance / wire_length

    def trim(self: Wire, start: float, end: float) -> Wire:
        """trim

        Create a new wire by keeping only the section between start and end.

        Args:
            start (float): 0.0 <= start < 1.0
            end (float): 0.0 < end <= 1.0

        Raises:
            ValueError: start >= end

        Returns:
            Wire: trimmed wire
        """

        # pylint: disable=too-many-branches
        if start >= end:
            raise ValueError("start must be less than end")

        edges = self.edges()

        # If this is really just an edge, skip the complexity of a Wire
        if len(edges) == 1:
            return Wire([edges[0].trim(start, end)])

        # For each Edge determine the beginning and end wire parameters
        # Note that u, v values are parameters along the Wire
        edges_uv_values: list[tuple[float, float, Edge]] = []
        found_end_of_wire = False  # for finding ends of closed wires

        for edge in edges:
            u = self.param_at_point(edge.position_at(0))
            v = self.param_at_point(edge.position_at(1))
            if self.is_closed:  # Avoid two beginnings or ends
                u = (
                    1 - u
                    if found_end_of_wire and (isclose_b(u, 0) or isclose_b(u, 1))
                    else u
                )
                v = (
                    1 - v
                    if found_end_of_wire and (isclose_b(v, 0) or isclose_b(v, 1))
                    else v
                )
                found_end_of_wire = (
                    isclose_b(u, 0)
                    or isclose_b(u, 1)
                    or isclose_b(v, 0)
                    or isclose_b(v, 1)
                    or found_end_of_wire
                )

            # Edge might be reversed and require flipping parms
            u, v = (v, u) if u > v else (u, v)

            edges_uv_values.append((u, v, edge))

        new_edges = []
        for u, v, edge in edges_uv_values:
            if v < start or u > end:  # Edge not needed
                continue

            if start <= u and v <= end:  # keep whole Edge
                new_edges.append(edge)

            elif start >= u and end <= v:  # Wire trimmed to single Edge
                u_edge = edge.param_at_point(self.position_at(start))
                v_edge = edge.param_at_point(self.position_at(end))
                u_edge, v_edge = (
                    (v_edge, u_edge) if u_edge > v_edge else (u_edge, v_edge)
                )
                new_edges.append(edge.trim(u_edge, v_edge))

            elif start <= u:  # keep start of Edge
                u_edge = edge.param_at_point(self.position_at(end))
                if u_edge != 0:
                    new_edges.append(edge.trim(0, u_edge))

            else:  #  v <= end  keep end of Edge
                v_edge = edge.param_at_point(self.position_at(start))
                if v_edge != 1:
                    new_edges.append(edge.trim(v_edge, 1))

        return Wire(new_edges)

    def order_edges(self) -> ShapeList[Edge]:
        """Return the edges in self ordered by wire direction and orientation"""
        ordered_edges = [
            e if e.is_forward else e.reversed() for e in self.edges().sort_by(self)
        ]
        return ShapeList(ordered_edges)

    @classmethod
    def _make_wire(cls, edges: Iterable[Edge], sequenced: bool = False) -> TopoDS_Wire:
        """_make_wire

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
                next_edge = closest_to_end(Wire(placed_edges), unplaced_edges)
                next_edge_index = unplaced_edges.index(next_edge)
                placed_edges.append(unplaced_edges.pop(next_edge_index))

            edges = placed_edges

        wire_builder = BRepBuilderAPI_MakeWire()
        combined_edges = TopTools_ListOfShape()
        for edge in edges:
            combined_edges.Append(edge.wrapped)
        wire_builder.Add(combined_edges)

        wire_builder.Build()
        if not wire_builder.IsDone():
            if wire_builder.Error() == BRepBuilderAPI_NonManifoldWire:
                warnings.warn(
                    "Wire is non manifold (e.g. branching, self intersecting)",
                    stacklevel=2,
                )
            elif wire_builder.Error() == BRepBuilderAPI_EmptyWire:
                raise RuntimeError("Wire is empty")
            elif wire_builder.Error() == BRepBuilderAPI_DisconnectedWire:
                raise ValueError("Edges are disconnected")

        return wire_builder.Wire()

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
        return Wire([circle_edge])

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
            wire = Wire([ellipse_edge, line])
        else:
            wire = Wire([ellipse_edge])

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

    def fillet_2d(self, radius: float, vertices: Iterable[Vertex]) -> Wire:
        """fillet_2d

        Apply 2D fillet to a wire

        Args:
            radius (float):
            vertices (Iterable[Vertex]): vertices to fillet

        Returns:
            Wire: filleted wire
        """
        # Create a face to fillet
        unfilleted_face = _make_topods_face_from_wires(self.wrapped)
        # Fillet the face
        fillet_builder = BRepFilletAPI_MakeFillet2d(unfilleted_face)
        for vertex in vertices:
            fillet_builder.AddFillet(vertex.wrapped, radius)
        fillet_builder.Build()
        filleted_face = downcast(fillet_builder.Shape())
        # Return the outer wire
        return Wire(BRepTools.OuterWire_s(filleted_face))

    def chamfer_2d(
        self,
        distance: float,
        distance2: float,
        vertices: Iterable[Vertex],
        edge: Edge = None,
    ) -> Wire:
        """chamfer_2d

        Apply 2D chamfer to a wire

        Args:
            distance (float): chamfer length
            distance2 (float): chamfer length
            vertices (Iterable[Vertex]): vertices to chamfer
            edge (Edge): identifies the side where length is measured. The vertices must be
                part of the edge

        Returns:
            Wire: chamfered wire
        """
        reference_edge = edge
        del edge

        # Create a face to chamfer
        unchamfered_face = _make_topods_face_from_wires(self.wrapped)
        chamfer_builder = BRepFilletAPI_MakeFillet2d(unchamfered_face)

        vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            unchamfered_face, ta.TopAbs_VERTEX, ta.TopAbs_EDGE, vertex_edge_map
        )

        for v in vertices:
            edges = vertex_edge_map.FindFromKey(v.wrapped)

            # Index or iterator access to OCP.TopTools.TopTools_ListOfShape is slow on M1 macs
            # Using First() and Last() to omit
            edges = [edges.First(), edges.Last()]

            # Need to wrap in b3d objects for comparison to work
            # ref.wrapped != edge.wrapped but ref == edge
            edges = [Edge(e) for e in edges]

            edge1, edge2 = Wire.order_chamfer_edges(reference_edge, edges)

            chamfer_builder.AddChamfer(
                TopoDS.Edge_s(edge1.wrapped),
                TopoDS.Edge_s(edge2.wrapped),
                distance,
                distance2,
            )

        chamfer_builder.Build()
        chamfered_face = chamfer_builder.Shape()
        # Fix the shape
        shape_fix = ShapeFix_Shape(chamfered_face)
        shape_fix.Perform()
        chamfered_face = downcast(shape_fix.Shape())
        # Return the outer wire
        return Wire(BRepTools.OuterWire_s(chamfered_face))

    @staticmethod
    def order_chamfer_edges(reference_edge, edges) -> tuple[Edge, Edge]:
        """Order the edges of a chamfer relative to a reference Edge"""
        if reference_edge:
            if reference_edge not in edges:
                raise ValueError("One or more vertices are not part of edge")
            edge1 = reference_edge
            edge2 = [x for x in edges if x != reference_edge][0]
        else:
            edge1, edge2 = edges
        return edge1, edge2

    @classmethod
    def make_rect(
        cls,
        width: float,
        height: float,
        plane: Plane = Plane.XY,
    ) -> Wire:
        """Make Rectangle

        Make a Rectangle centered on center with the given normal

        Args:
            width (float): width (local x)
            height (float): height (local y)
            plane (Plane, optional): plane containing rectangle. Defaults to Plane.XY.

        Returns:
            Wire: The centered rectangle
        """
        corners_local = [
            (width / 2, height / 2),
            (width / 2, height / -2),
            (width / -2, height / -2),
            (width / -2, height / 2),
        ]
        corners_world = [plane.from_local_coords(c) for c in corners_local]
        return Wire.make_polygon(corners_world, close=True)

    @classmethod
    def make_convex_hull(cls, edges: Iterable[Edge], tolerance: float = 1e-3) -> Wire:
        """make_convex_hull

        Create a wire of minimum length enclosing all of the provided edges.

        Note that edges can't overlap each other.

        Args:
            edges (Iterable[Edge]): edges defining the convex hull
            tolerance (float): allowable error as a fraction of each edge length.
                Defaults to 1e-3.

        Raises:
            ValueError: edges overlap

        Returns:
            Wire: convex hull perimeter
        """
        # pylint: disable=too-many-branches, too-many-locals
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
                if edge0 not in trim_points:
                    trim_points[edge0] = [simplice[0]]
                else:
                    trim_points[edge0].append(simplice[0])
                if edge1 not in trim_points:
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
                if edge0 not in trim_points:
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
        hull_wire = Wire(connecting_edges + trimmed_edges, sequenced=True)
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
        # pylint: disable=too-many-branches
        if not (direction is None) ^ (center is None):
            raise ValueError("One of either direction or center must be provided")
        if direction is not None:
            direction_vector = Vector(direction).normalized()
            center_point = None
        else:
            direction_vector = None
            center_point = Vector(center)

        # Project the wire on the target object
        if direction_vector is not None:
            projection_object = BRepProj_Projection(
                self.wrapped,
                target_object.wrapped,
                gp_Dir(*direction_vector.to_tuple()),
            )
        else:
            projection_object = BRepProj_Projection(
                self.wrapped,
                target_object.wrapped,
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
                        (
                            output_wire,
                            (output_wire_center - center_point).length,
                        )
                    )

            output_wires_distances.sort(key=lambda x: x[1])
            logger.debug(
                "projected, filtered and sorted wire list is of length %d",
                len(output_wires_distances),
            )
            output_wires = [w[0] for w in output_wires_distances]

        return output_wires


class Joint(ABC):
    """Joint

    Abstract Base Joint class - used to join two components together

    Args:
        parent (Union[Solid, Compound]): object that joint to bound to

    Attributes:
        label (str): user assigned label
        parent (Shape): object joint is bound to
        connected_to (Joint): joint that is connect to this joint

    """

    def __init__(self, label: str, parent: Union[Solid, Compound]):
        self.label = label
        self.parent = parent
        self.connected_to: Joint = None

    def _connect_to(self, other: Joint, **kwargs):  # pragma: no cover
        """Connect Joint self by repositioning other"""

        if not isinstance(other, Joint):
            raise TypeError(f"other must of type Joint not {type(other)}")

        relative_location = self.relative_to(other, **kwargs)
        other.parent.locate(self.parent.location * relative_location)
        self.connected_to = other

    @abstractmethod
    def connect_to(self, other: Joint):
        """All derived classes must provide a connect_to method"""

    @abstractmethod
    def relative_to(self, other: Joint) -> Location:
        """Return relative location to another joint"""

    @property
    @abstractmethod
    def location(self) -> Location:
        """Location of joint"""

    @property
    @abstractmethod
    def symbol(self) -> Compound:
        """A CAD object positioned in global space to illustrate the joint"""


def _make_loft(
    objs: Iterable[Union[Vertex, Wire]],
    filled: bool,
    ruled: bool = False,
) -> TopoDS_Shape:
    """make loft

    Makes a loft from a list of wires and vertices. Vertices can appear only at the
    beginning or end of the list, but cannot appear consecutively within the list
    nor between wires.

    Args:
        wires (list[Wire]): section perimeters
        ruled (bool, optional): stepped or smooth. Defaults to False (smooth).

    Raises:
        ValueError: Too few wires

    Returns:
        TopoDS_Shape: Lofted object
    """
    if len(objs) < 2:
        raise ValueError("More than one wire is required")
    vertices = [obj for obj in objs if isinstance(obj.wrapped, TopoDS_Vertex)]
    vertex_count = len(vertices)

    if vertex_count > 2:
        raise ValueError("Only two vertices are allowed")

    if vertex_count == 1 and not (
        isinstance(objs[0].wrapped, TopoDS_Vertex)
        or isinstance(objs[-1].wrapped, TopoDS_Vertex)
    ):
        raise ValueError(
            "The vertex must be either at the beginning or end of the list"
        )

    if vertex_count == 2:
        if len(objs) == 2:
            raise ValueError(
                "You can't have only 2 vertices to loft; try adding some wires"
            )
        if not (
            isinstance(objs[0].wrapped, TopoDS_Vertex)
            and isinstance(objs[-1].wrapped, TopoDS_Vertex)
        ):
            raise ValueError(
                "The vertices must be at the beginning and end of the list"
            )

    loft_builder = BRepOffsetAPI_ThruSections(filled, ruled)

    for obj in objs:
        if isinstance(obj.wrapped, TopoDS_Vertex):
            loft_builder.AddVertex(obj.wrapped)
        elif isinstance(obj.wrapped, TopoDS_Wire):
            loft_builder.AddWire(obj.wrapped)

    loft_builder.Build()

    return loft_builder.Shape()


def downcast(obj: TopoDS_Shape) -> TopoDS_Shape:
    """Downcasts a TopoDS object to suitable specialized type

    Args:
      obj: TopoDS_Shape:

    Returns:

    """

    f_downcast: Any = Shape.downcast_LUT[shapetype(obj)]
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

    wires = ShapeList()
    for i in range(wires_out.Length()):
        wires.append(Wire(downcast(wires_out.Value(i + 1))))

    return wires


def fix(obj: TopoDS_Shape) -> TopoDS_Shape:
    """Fix a TopoDS object to suitable specialized type

    Args:
      obj: TopoDS_Shape:

    Returns:

    """

    shape_fix = ShapeFix_Shape(obj)
    shape_fix.Perform()

    return downcast(shape_fix.Shape())


def isclose_b(x: float, y: float, rel_tol=1e-9, abs_tol=1e-14) -> bool:
    """Determine whether two floating point numbers are close in value.
    Overridden abs_tol default for the math.isclose function.

    Args:
        x (float): First value to compare
        y (float): Second value to compare
        rel_tol (float, optional): Maximum difference for being considered "close",
            relative to the magnitude of the input values. Defaults to 1e-9.
        abs_tol (float, optional): Maximum difference for being considered "close",
            regardless of the magnitude of the input values. Defaults to 1e-14
            (unlike math.isclose which defaults to zero).

    Returns: True if a is close in value to b, and False otherwise.
    """
    return isclose(x, y, rel_tol=rel_tol, abs_tol=abs_tol)


def shapetype(obj: TopoDS_Shape) -> TopAbs_ShapeEnum:
    """Return TopoDS_Shape's TopAbs_ShapeEnum"""
    if obj.IsNull():
        raise ValueError("Null TopoDS_Shape object")

    return obj.ShapeType()


def unwrapped_shapetype(obj: Shape) -> TopAbs_ShapeEnum:
    """Return Shape's TopAbs_ShapeEnum"""
    if isinstance(obj.wrapped, TopoDS_Compound):
        shapetypes = set(shapetype(o.wrapped) for o in obj)
        if len(shapetypes) == 1:
            result = shapetypes.pop()
        else:
            result = shapetype(obj)
    else:
        result = shapetype(obj.wrapped)
    return result


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
    faces = Face(wire_list[0], wire_list[1:])

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


def delta(shapes_one: Iterable[Shape], shapes_two: Iterable[Shape]) -> list[Shape]:
    """Compare the OCCT objects of each list and return the differences"""
    occt_one = set(shape.wrapped for shape in shapes_one)
    occt_two = set(shape.wrapped for shape in shapes_two)
    occt_delta = list(occt_one - occt_two)

    all_shapes = []
    for shapes in [shapes_one, shapes_two]:
        all_shapes.extend(shapes if isinstance(shapes, list) else [*shapes])
    shape_delta = [shape for shape in all_shapes if shape.wrapped in occt_delta]
    return shape_delta


def new_edges(*objects: Shape, combined: Shape) -> ShapeList[Edge]:
    """new_edges

    Given a sequence of shapes and the combination of those shapes, find the newly added edges

    Args:
        objects (Shape): sequence of shapes
        combined (Shape): result of the combination of objects

    Returns:
        ShapeList[Edge]: new edges
    """
    # Create a list of combined object edges
    combined_topo_edges = TopTools_ListOfShape()
    for edge in combined.edges():
        combined_topo_edges.Append(edge.wrapped)

    # Create a list of original object edges
    original_topo_edges = TopTools_ListOfShape()
    for edge in [e for obj in objects for e in obj.edges()]:
        original_topo_edges.Append(edge.wrapped)

    # Cut the original edges from the combined edges
    operation = BRepAlgoAPI_Cut()
    operation.SetArguments(combined_topo_edges)
    operation.SetTools(original_topo_edges)
    operation.SetRunParallel(True)
    operation.Build()

    edges = []
    explorer = TopExp_Explorer(operation.Shape(), TopAbs_ShapeEnum.TopAbs_EDGE)
    while explorer.More():
        found_edge = combined.__class__.cast(downcast(explorer.Current()))
        found_edge.topo_parent = combined
        edges.append(found_edge)
        explorer.Next()

    return ShapeList(edges)


def topo_explore_connected_edges(edge: Edge, parent: Shape = None) -> ShapeList[Edge]:
    """Given an edge extracted from a Shape, return the edges connected to it"""

    parent = parent if parent is not None else edge.topo_parent
    given_topods_edge = edge.wrapped
    connected_edges = set()

    # Find all the TopoDS_Edges for this Shape
    topods_edges = ShapeList([e.wrapped for e in parent.edges()])

    for topods_edge in topods_edges:
        # # Don't match with the given edge
        if given_topods_edge.IsSame(topods_edge):
            continue
        # If the edge shares a vertex with the given edge they are connected
        if topo_explore_common_vertex(given_topods_edge, topods_edge) is not None:
            connected_edges.add(topods_edge)

    return ShapeList([Edge(e) for e in connected_edges])


def topo_explore_common_vertex(
    edge1: Edge | TopoDS_Edge, edge2: Edge | TopoDS_Edge
) -> Optional[Vertex]:
    """Given two edges, find the common vertex"""
    topods_edge1 = edge1 if isinstance(edge1, TopoDS_Edge) else edge1.wrapped
    topods_edge2 = edge2 if isinstance(edge2, TopoDS_Edge) else edge2.wrapped

    # Explore vertices of the first edge
    vert_exp = TopExp_Explorer(topods_edge1, ta.TopAbs_VERTEX)
    while vert_exp.More():
        vertex1 = vert_exp.Current()

        # Explore vertices of the second edge
        explorer2 = TopExp_Explorer(topods_edge2, ta.TopAbs_VERTEX)
        while explorer2.More():
            vertex2 = explorer2.Current()

            # Check if the vertices are the same
            if vertex1.IsSame(vertex2):
                return Vertex(downcast(vertex1))  # Common vertex found

            explorer2.Next()
        vert_exp.Next()

    return None  # No common vertex found


def unwrap_topods_compound(
    compound: TopoDS_Compound, fully: bool = True
) -> TopoDS_Compound | TopoDS_Shape:
    """Strip unnecessary Compound wrappers

    Args:
        compound (TopoDS_Compound): The TopoDS_Compound to unwrap.
        fully (bool, optional): return base shape without any TopoDS_Compound
            wrappers (otherwise one TopoDS_Compound is left). Defaults to True.

    Returns:
        TopoDS_Compound | TopoDS_Shape: base shape
    """
    if compound.NbChildren() == 1:
        iterator = TopoDS_Iterator(compound)
        single_element = downcast(iterator.Value())

        # If the single element is another TopoDS_Compound, unwrap it recursively
        if isinstance(single_element, TopoDS_Compound):
            return unwrap_topods_compound(single_element, fully)

        return single_element if fully else compound

    # If there are no elements or more than one element, return TopoDS_Compound
    return compound


def get_top_level_topods_shapes(topods_shape: TopoDS_Shape) -> ShapeList[TopoDS_Shape]:
    """
    Retrieve the first level of child shapes from the shape.

    This method collects all the non-compound shapes directly contained in the
    current shape. If the wrapped shape is a `TopoDS_Compound`, it traverses
    its immediate children and collects all shapes that are not further nested
    compounds. Nested compounds are traversed to gather their non-compound elements
    without returning the nested compound itself.

    Returns:
        ShapeList[TopoDS_Shape]: A list of all first-level non-compound child shapes.

    Example:
        If the current shape is a compound containing both simple shapes
        (e.g., edges, vertices) and other compounds, the method returns a list
        of only the simple shapes directly contained at the top level.
    """
    if topods_shape is None:
        return ShapeList()

    first_level_shapes = []
    stack = [topods_shape]

    while stack:
        current_shape = stack.pop()
        if isinstance(current_shape, TopoDS_Compound):
            iterator = TopoDS_Iterator()
            iterator.Initialize(current_shape)
            while iterator.More():
                child_shape = downcast(iterator.Value())
                if isinstance(child_shape, TopoDS_Compound):
                    # Traverse further into the compound
                    stack.append(child_shape)
                else:
                    # Add non-compound shape
                    first_level_shapes.append(child_shape)
                iterator.Next()
        else:
            first_level_shapes.append(current_shape)

    return ShapeList(first_level_shapes)


def _topods_bool_op(
    args: Iterable[TopoDS_Shape],
    tools: Iterable[TopoDS_Shape],
    operation: BRepAlgoAPI_BooleanOperation | BRepAlgoAPI_Splitter,
) -> TopoDS_Shape:
    """Generic boolean operation for TopoDS_Shapes

    Args:
        args: Iterable[TopoDS_Shape]:
        tools: Iterable[TopoDS_Shape]:
        operation: BRepAlgoAPI_BooleanOperation | BRepAlgoAPI_Splitter:

    Returns: TopoDS_Shape

    """

    arg = TopTools_ListOfShape()
    for obj in args:
        arg.Append(obj)

    tool = TopTools_ListOfShape()
    for obj in tools:
        tool.Append(obj)

    operation.SetArguments(arg)
    operation.SetTools(tool)

    operation.SetRunParallel(True)
    operation.Build()

    result = downcast(operation.Shape())
    # Remove unnecessary TopoDS_Compound around single shape
    if isinstance(result, TopoDS_Compound):
        result = unwrap_topods_compound(result, True)

    return result


def _make_topods_face_from_wires(
    outer_wire: TopoDS_Wire, inner_wires: Optional[Sequence[TopoDS_Wire]] = None
) -> TopoDS_Face:
    """_make_topods_face_from_wires

    Makes a planar face from one or more wires

    Args:
        outer_wire (TopoDS_Wire): closed perimeter wire
        inner_wires (Sequence[TopoDS_Wire], optional): holes. Defaults to None.

    Raises:
        ValueError: outer wire not closed
        ValueError: wires not planar
        ValueError: inner wire not closed
        ValueError: internal error

    Returns:
        TopoDS_Face: planar face potentially with holes
    """
    if inner_wires and not BRep_Tool.IsClosed_s(outer_wire):
        raise ValueError("Cannot build face(s): outer wire is not closed")
    inner_wires = inner_wires if inner_wires else []

    # check if wires are coplanar
    verification_compound = _make_topods_compound_from_shapes(
        [outer_wire] + inner_wires
    )
    if not BRepLib_FindSurface(verification_compound, OnlyPlane=True).Found():
        raise ValueError("Cannot build face(s): wires not planar")

    # fix outer wire
    sf_s = ShapeFix_Shape(outer_wire)
    sf_s.Perform()
    topo_wire = TopoDS.Wire_s(sf_s.Shape())

    face_builder = BRepBuilderAPI_MakeFace(topo_wire, True)

    for inner_wire in inner_wires:
        if not BRep_Tool.IsClosed_s(inner_wire):
            raise ValueError("Cannot build face(s): inner wire is not closed")
        face_builder.Add(inner_wire)

    face_builder.Build()

    if not face_builder.IsDone():
        raise ValueError(f"Cannot build face(s): {face_builder.Error()}")

    face = face_builder.Face()

    sf_f = ShapeFix_Face(face)
    sf_f.FixOrientation()
    sf_f.Perform()

    return downcast(sf_f.Result())


def _sew_topods_faces(faces: Sequence[TopoDS_Face]) -> TopoDS_Shape:
    """Sew faces into a shell if possible"""
    shell_builder = BRepBuilderAPI_Sewing()
    for face in faces:
        shell_builder.Add(face)
    shell_builder.Perform()
    return downcast(shell_builder.SewedShape())


def _make_topods_compound_from_shapes(
    occt_shapes: Sequence[TopoDS_Shape],
) -> TopoDS_Compound:
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


def find_max_dimension(shapes: Shape | Iterable[Shape]) -> float:
    """Return the maximum dimension of one or more shapes"""
    shapes = shapes if isinstance(shapes, Iterable) else [shapes]
    composite = _make_topods_compound_from_shapes([s.wrapped for s in shapes])
    bbox = BoundBox.from_topo_ds(composite, tolerance=TOLERANCE, optimal=True)
    return bbox.diagonal


def _topods_entities(shape: TopoDS_Shape, topo_type: Shapes) -> list[TopoDS_Shape]:
    """Return the TopoDS_Shapes of topo_type from this TopoDS_Shape"""
    out = {}  # using dict to prevent duplicates

    explorer = TopExp_Explorer(shape, Shape.inverse_shape_LUT[topo_type])

    while explorer.More():
        item = explorer.Current()
        out[item.HashCode(HASH_CODE_MAX)] = (
            item  # needed to avoid pseudo-duplicate entities
        )
        explorer.Next()

    return list(out.values())


def _extrude_topods_shape(obj: TopoDS_Shape, direction: VectorLike) -> TopoDS_Shape:
    """extrude

    Extrude a Shape in the provided direction.
    * Vertices generate Edges
    * Edges generate Faces
    * Wires generate Shells
    * Faces generate Solids
    * Shells generate Compounds

    Args:
        direction (VectorLike): direction and magnitude of extrusion

    Raises:
        ValueError: Unsupported class
        RuntimeError: Generated invalid result

    Returns:
        TopoDS_Shape: extruded shape
    """
    direction = Vector(direction)

    if obj is None or not isinstance(
        obj,
        (TopoDS_Vertex, TopoDS_Edge, TopoDS_Wire, TopoDS_Face, TopoDS_Shell),
    ):
        raise ValueError(f"extrude not supported for {type(obj)}")

    prism_builder = BRepPrimAPI_MakePrism(obj, direction.wrapped)
    extrusion = downcast(prism_builder.Shape())
    shape_type = extrusion.ShapeType()
    if shape_type == TopAbs_ShapeEnum.TopAbs_COMPSOLID:
        solids = []
        explorer = TopExp_Explorer(extrusion, TopAbs_ShapeEnum.TopAbs_SOLID)
        while explorer.More():
            solids.append(downcast(explorer.Current()))
            explorer.Next()
        extrusion = _make_topods_compound_from_shapes(solids)
    return extrusion


class SkipClean:
    """Skip clean context for use in operator driven code where clean=False wouldn't work"""

    clean = True

    def __enter__(self):
        SkipClean.clean = False

    def __exit__(self, exception_type, exception_value, traceback):
        SkipClean.clean = True
