"""
build123d topology

name: one_d.py
by:   Gumyr
date: January 07, 2025

desc:

This module defines the classes and methods for one-dimensional geometric entities in the build123d
CAD library. It focuses on `Edge` and `Wire`, representing essential topological elements like
curves and connected sequences of curves within a 3D model. These entities are pivotal for
constructing complex shapes, boundaries, and paths in CAD applications.

Key Features:
- **Edge Class**:
  - Represents curves such as lines, arcs, splines, and circles.
  - Supports advanced operations like trimming, offsetting, splitting, and projecting onto shapes.
  - Includes methods for geometric queries like finding tangent angles, normals, and intersection
    points.

- **Wire Class**:
  - Represents a connected sequence of edges forming a continuous path.
  - Supports operations such as closure, projection, and edge manipulation.

- **Mixin1D**:
  - Shared functionality for both `Edge` and `Wire` classes, enabling splitting, extrusion, and
    1D-specific operations.

This module integrates deeply with OpenCascade, leveraging its robust geometric and topological
operations. It provides utility functions to create, manipulate, and query 1D geometric entities,
ensuring precise and efficient workflows in 3D modeling tasks.

license:

    Copyright 2025 Gumyr

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

import copy
import warnings
from bisect import bisect_right
from collections.abc import Iterable, Sequence
from itertools import combinations
from math import atan2, ceil, copysign, cos, floor, inf, isclose, pi, radians
from typing import TYPE_CHECKING, Literal, overload
from typing import cast as tcast

import numpy as np
import OCP.TopAbs as ta
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve
from OCP.BRepAlgoAPI import (
    BRepAlgoAPI_Common,
    BRepAlgoAPI_Section,
    BRepAlgoAPI_Splitter,
)
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_DisconnectedWire,
    BRepBuilderAPI_EmptyWire,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeEdge2d,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_NonManifoldWire,
)
from OCP.BRepExtrema import BRepExtrema_DistShapeShape, BRepExtrema_SupportType
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet2d
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepLib import BRepLib, BRepLib_FindSurface
from OCP.BRepLProp import BRepLProp
from OCP.BRepOffset import BRepOffset_MakeOffset
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCP.BRepProj import BRepProj_Projection
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.Extrema import Extrema_ExtPC
from OCP.GC import (
    GC_MakeArcOfCircle,
    GC_MakeArcOfEllipse,
    GC_MakeArcOfParabola,
    GC_MakeArcOfHyperbola,
)
from OCP.GCPnts import (
    GCPnts_AbscissaPoint,
    GCPnts_QuasiUniformDeflection,
    GCPnts_TangentialDeflection,
    GCPnts_UniformDeflection,
)
from OCP.GProp import GProp_GProps
from OCP.Geom import (
    Geom_BezierCurve,
    Geom_BSplineCurve,
    Geom_ConicalSurface,
    Geom_CylindricalSurface,
    Geom_Line,
    Geom_Plane,
    Geom_Surface,
    Geom_TrimmedCurve,
)
from OCP.Geom2d import (
    Geom2d_CartesianPoint,
    Geom2d_Circle,
    Geom2d_Curve,
    Geom2d_Line,
    Geom2d_Point,
    Geom2d_TrimmedCurve,
)
from OCP.Geom2dAdaptor import Geom2dAdaptor_Curve
from OCP.Geom2dAPI import Geom2dAPI_InterCurveCurve
from OCP.Geom2dGcc import Geom2dGcc_Circ2d2TanRad, Geom2dGcc_QualifiedCurve
from OCP.GeomAbs import (
    GeomAbs_C0,
    GeomAbs_C1,
    GeomAbs_C2,
    GeomAbs_C3,
    GeomAbs_CN,
    GeomAbs_C1,
    GeomAbs_G1,
    GeomAbs_G2,
    GeomAbs_JoinType,
)
from OCP.GeomAdaptor import GeomAdaptor_Curve
from OCP.GeomAPI import (
    GeomAPI,
    GeomAPI_IntCS,
    GeomAPI_Interpolate,
    GeomAPI_PointsToBSpline,
    GeomAPI_ProjectPointOnCurve,
)
from OCP.GeomConvert import GeomConvert_CompCurveToBSplineCurve
from OCP.GeomFill import (
    GeomFill_CorrectedFrenet,
    GeomFill_Frenet,
    GeomFill_TrihedronLaw,
)
from OCP.GeomProjLib import GeomProjLib
from OCP.gp import (
    gp_Ax1,
    gp_Ax2,
    gp_Ax3,
    gp_Circ,
    gp_Circ2d,
    gp_Dir,
    gp_Dir2d,
    gp_Elips,
    gp_Parab,
    gp_Hypr,
    gp_Pln,
    gp_Pnt,
    gp_Pnt2d,
    gp_Trsf,
    gp_Vec,
)
from OCP.GProp import GProp_GProps
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_Wireframe
from OCP.Standard import (
    Standard_ConstructionError,
    Standard_Failure,
    Standard_NoSuchObject,
)
from OCP.TColgp import TColgp_Array1OfPnt, TColgp_Array1OfVec, TColgp_HArray1OfPnt
from OCP.TColStd import (
    TColStd_Array1OfReal,
    TColStd_HArray1OfBoolean,
    TColStd_HArray1OfReal,
)
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Compound,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Vertex,
    TopoDS_Wire,
)
from OCP.TopTools import (
    TopTools_HSequenceOfShape,
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_IndexedMapOfShape,
    TopTools_ListOfShape,
)
from scipy.optimize import minimize_scalar
from scipy.spatial import ConvexHull
from typing_extensions import Self

from build123d.build_enums import (
    AngularDirection,
    CenterOf,
    ContinuityLevel,
    FrameMethod,
    GeomType,
    Keep,
    Kind,
    Sagitta,
    Tangency,
    PositionMode,
    Side,
)
from build123d.geometry import (
    DEG2RAD,
    TOL_DIGITS,
    TOLERANCE,
    Axis,
    Color,
    Location,
    Plane,
    Vector,
    VectorLike,
    logger,
)

from .shape_core import (
    TOPODS,
    Shape,
    ShapeList,
    SkipClean,
    TrimmingTool,
    downcast,
    get_top_level_topods_shapes,
    shapetype,
    topods_dim,
    unwrap_topods_compound,
    _topods_bool_op,
)
from .utils import (
    _extrude_topods_shape,
    _make_topods_face_from_wires,
    isclose_b,
)
from .zero_d import Vertex, topo_explore_common_vertex
from .constrained_lines import (
    _make_2tan_rad_arcs,
    _make_2tan_on_arcs,
    _make_3tan_arcs,
    _make_tan_cen_arcs,
    _make_tan_on_rad_arcs,
    _make_tan_oriented_lines,
    _make_2tan_lines,
)

if TYPE_CHECKING:  # pragma: no cover
    from .composite import Compound, Curve, Part, Sketch  # pylint: disable=R0801
    from .three_d import Solid  # pylint: disable=R0801
    from .two_d import Face, Shell  # pylint: disable=R0801


class Mixin1D(Shape[TOPODS]):
    """Methods to add to the Edge and Wire classes"""

    # ---- Properties ----

    @property
    def _dim(self) -> int:
        """Dimension of Edges and Wires"""
        return 1

    @property
    def is_closed(self) -> bool:
        """Are the start and end points equal?"""
        if self._wrapped is None:
            raise ValueError("Can't determine if empty Edge or Wire is closed")
        return BRep_Tool.IsClosed_s(self.wrapped)

    @property
    def is_forward(self) -> bool:
        """Does the Edge/Wire loop forward or reverse"""
        if self._wrapped is None:
            raise ValueError("Can't determine direction of empty Edge or Wire")
        return self.wrapped.Orientation() == TopAbs_Orientation.TopAbs_FORWARD

    @property
    def is_interior(self) -> bool:
        """
        Check if the edge is an interior edge.

        An interior edge lies between surfaces that are part of the body (internal
        to the geometry) and does not form part of the exterior boundary.

        Returns:
            bool: True if the edge is an interior edge, False otherwise.
        """
        # Find the faces connected to this edge and offset them
        topods_face_pair = topo_explore_connected_faces(self)
        offset_face_pair = [
            offset_topods_face(f, self.length / 100) for f in topods_face_pair
        ]

        # Intersect the offset faces
        sectionor = BRepAlgoAPI_Section(
            offset_face_pair[0], offset_face_pair[1], PerformNow=False
        )
        sectionor.Build()
        face_intersection_result = sectionor.Shape()

        # If an edge was created the faces intersect and the edge is interior
        explorer = TopExp_Explorer(face_intersection_result, ta.TopAbs_EDGE)
        return explorer.More()

    @property
    def length(self) -> float:
        """Edge or Wire length"""
        props = GProp_GProps()
        BRepGProp.LinearProperties_s(self.wrapped, props)
        return props.Mass()

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
    def volume(self) -> float:
        """volume - the volume of this Edge or Wire, which is always zero"""
        return 0.0

    # ---- Class Methods ----

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Vertex | Edge | Wire:
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

    @classmethod
    def extrude(
        cls, obj: Shape, direction: VectorLike
    ) -> Edge | Face | Shell | Solid | Compound:
        """Unused - only here because Mixin1D is a subclass of Shape"""
        return NotImplemented

    # ---- Static Methods ----

    @staticmethod
    def _to_param(edge_wire: Mixin1D, value: float | VectorLike, name: str) -> float:
        """Convert a float or VectorLike into a curve parameter."""
        if isinstance(value, (int, float)):
            return float(value)
        try:
            point = Vector(value)
        except TypeError as exc:
            raise TypeError(
                f"{name} must be a float or VectorLike, not {value!r}"
            ) from exc
        return edge_wire.param_at_point(point)

    # ---- Instance Methods ----

    def __add__(
        self, other: None | Shape | Iterable[Shape]
    ) -> Edge | Wire | ShapeList[Edge]:
        """fuse shape to wire/edge operator +"""

        # Convert `other` to list of base topods objects and filter out None values
        if other is None:
            topods_summands = []
        else:
            topods_summands = [
                shape
                # for o in (other if isinstance(other, (list, tuple)) else [other])
                for o in ([other] if isinstance(other, Shape) else other)
                for shape in get_top_level_topods_shapes(o.wrapped if o else None)
            ]
        # If there is nothing to add return the original object
        if not topods_summands:
            return self

        if not all(topods_dim(summand) == 1 for summand in topods_summands):
            raise ValueError("Only shapes with the same dimension can be added")

        # Convert back to Edge/Wire objects now that it's safe to do so
        summands = ShapeList(
            [tcast(Edge | Wire, Mixin1D.cast(s)) for s in topods_summands]
        )
        summand_edges = [e for summand in summands for e in summand.edges()]

        if self._wrapped is None:  # an empty object
            if len(summands) == 1:
                sum_shape: Edge | Wire | ShapeList[Edge] = summands[0]
            else:
                try:
                    sum_shape = Wire(summand_edges)
                except Exception:
                    # pylint: disable=[no-member]
                    sum_shape = summands[0].fuse(*summands[1:])
                    if type(self).order == 4:
                        sum_shape = type(self)(sum_shape)  # type: ignore
        else:
            try:
                sum_shape = Wire(self.edges() + ShapeList(summand_edges))
            except Exception:
                sum_shape = self.fuse(*summands)

        if SkipClean.clean and not isinstance(sum_shape, list):
            sum_shape = sum_shape.clean()

        # If there is only one Edge, return that
        sum_shape = sum_shape.edge() if len(sum_shape.edges()) == 1 else sum_shape  # type: ignore

        return sum_shape

    def __matmul__(self, position: float) -> Vector:
        """Position on wire operator @"""
        return self.position_at(position)

    def __mod__(self, position: float) -> Vector:
        """Tangent on wire operator %"""
        return self.tangent_at(position)

    def __xor__(self, position: float) -> Location:
        """Location on wire operator ^"""
        return self.location_at(position)

    def center(self, center_of: CenterOf = CenterOf.GEOMETRY) -> Vector:
        """Center of object

        Return the center based on center_of

        Args:
            center_of (CenterOf, optional): centering option. Defaults to CenterOf.GEOMETRY.

        Returns:
            Vector: center
        """
        if self._wrapped is None:
            raise ValueError("Can't find center of empty edge/wire")

        if center_of == CenterOf.GEOMETRY:
            middle = self.position_at(0.5)
        elif center_of == CenterOf.MASS:
            properties = GProp_GProps()
            BRepGProp.LinearProperties_s(self.wrapped, properties)
            middle = Vector(properties.CentreOfMass())
        else:  # center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    def common_plane(
        self, *lines: Edge | Wire | None, tolerance: float = TOLERANCE
    ) -> None | Plane:
        """common_plane

        Find the plane containing all the edges/wires (including self). If there
        is no common plane return None. If the edges are coaxial, select one
        of the infinite number of valid planes.

        Args:
            lines (sequence of Edge | Wire): edges in common with self
            tolerance (float): amount lines can deviate from plane. Defaults to TOLERANCE.

        Returns:
            None |  Plane: Either the common plane or None
        """
        # pylint: disable=too-many-locals
        # Note: BRepLib_FindSurface is not helpful as it requires the
        # Edges to form a surface perimeter.
        points: list[Vector] = []
        all_lines: list[Edge | Wire] = [
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
                z_dir = Plane(as_axis[0]).x_dir
                result = Plane(origin, z_dir=z_dir)

        if result is None:  # not coaxial
            # Shorten any infinite lines (from converted Axis)
            normal_lines = list(filter(lambda line: line.length <= 1e50, all_lines))
            infinite_lines = filter(lambda line: line.length > 1e50, all_lines)
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
                c_plane = Plane(
                    origin=(sum(extremes, Vector(0, 0, 0)) / 3), z_dir=z_dir
                )
            except ValueError:
                # There is no valid common plane
                result = None
            else:
                # Are all of the points on the common plane
                common = all(c_plane.contains(p, tolerance) for p in points)
                result = c_plane if common else None

        if result is None:
            return result

        # Center the plane on the lines
        global_center = sum(
            [e.position_at(0.5) for e in all_lines], start=Vector(0, 0, 0)
        ) / len(all_lines)
        center_axis = Axis(global_center, result.z_dir)
        plane_origin = result.intersect(center_axis)
        assert isinstance(plane_origin, Vector)

        return result.shift_origin(plane_origin)

    def curvature_comb(
        self, count: int = 100, max_tooth_size: float | None = None
    ) -> ShapeList[Edge]:
        """
        Build a *curvature comb* for a planar (XY) 1D curve.

        A curvature comb is a set of short line segments (“teeth”) erected
        perpendicular to the curve that visualize the signed curvature κ(u).
        Tooth length is proportional to |κ| and the direction encodes the sign
        (left normal for κ>0, right normal for κ<0). This is useful for inspecting
        fairness and continuity (C0/C1/C2) of edges and wires.

        Args:
            count (int, optional): Number of uniformly spaced samples over the normalized
                parameter. Increase for a denser comb. Defaults to 100.
            max_tooth_size (float | None, optional): Maximum tooth height in model units.
                If None, set to 10% maximum curve dimension. Defaults to None.

        Raises:
            ValueError: Empty curve.
            ValueError: If the curve is not planar on `Plane.XY`.

        Returns:
            ShapeList[Edge]: A list of short `Edge` objects (lines) anchored on the curve
            and oriented along the left normal `n̂ = normalize(t) × +Z`.

        Notes:
            - On circles, κ = 1/R so tooth length is constant.
            - On straight segments, κ = 0 so no teeth are drawn.
            - At inflection points κ→0 and the tooth flips direction.
            - At C0 corners the tangent is discontinuous; nearby teeth may jump.
              C1 yields continuous direction; C2 yields continuous magnitude as well.

        Example:
            >>> comb = my_wire.curvature_comb(count=200, max_tooth_size=2.0)
            >>> show(my_wire, Curve(comb))

        """
        if self._wrapped is None:
            raise ValueError("Can't create curvature_comb for empty curve")
        pln = self.common_plane()
        if pln is None or not isclose(abs(pln.z_dir.Z), 1.0, abs_tol=TOLERANCE):
            raise ValueError("curvature_comb only works for curves on Plane.XY")

        # If periodic the first and last tooth would be the same so skip them
        u_values = np.linspace(0, 1, count, endpoint=not self.is_closed)

        # first pass: gather kappas for scaling
        kappas = []
        tangents, curvatures = [], []
        for u in u_values:
            tangent = self.derivative_at(u, 1)
            curvature = self.derivative_at(u, 2)
            tangents.append(tangent)
            curvatures.append(curvature)
            cross = tangent.cross(curvature)
            kappa = cross.length / (tangent.length**3 + TOLERANCE)
            # signed for XY:
            sign = 1.0 if cross.Z >= 0 else -1.0
            kappas.append(sign * kappa)

        # choose a scale so the tallest tooth is max_tooth_size
        max_kappa_size = max(TOLERANCE, max(abs(k) for k in kappas))
        curve_size = max(self.bounding_box().size)
        max_tooth_size = (
            max_tooth_size if max_tooth_size is not None else curve_size / 10
        )
        scale = max_tooth_size / max_kappa_size

        comb_edges = ShapeList[Edge]()
        for u, kappa, tangent in zip(u_values, kappas, tangents):
            # Avoid tiny teeth
            if abs(length := scale * kappa) < TOLERANCE:
                continue
            pnt_on_curve = self @ u
            # left normal in XY (principal normal direction for a planar curve)
            kappa_dir = tangent.normalized().cross(Vector(0, 0, 1))
            comb_edges.append(
                Edge.make_line(pnt_on_curve, pnt_on_curve + length * kappa_dir)
            )

        return comb_edges

    def derivative_at(
        self,
        position: float | VectorLike,
        order: int = 2,
        position_mode: PositionMode = PositionMode.PARAMETER,
    ) -> Vector:
        """Derivative At

        Generate a derivative along the underlying curve.

        Args:
            position (float | VectorLike): distance, parameter value or point
            order (int): derivative order. Defaults to 2
            position_mode (PositionMode, optional): position calculation mode. Defaults to
                PositionMode.PARAMETER.

        Raises:
            ValueError: position must be a float or a point

        Returns:
            Vector: position on the underlying curve
        """
        if isinstance(position, (float, int)):
            comp_curve, occt_param, closest_forward = self._occt_param_at(
                position, position_mode
            )
        else:
            try:
                point_on_curve = Vector(position)
            except Exception as exc:
                raise ValueError("position must be a float or a point") from exc
            if isinstance(self, Wire):
                closest = min(self.edges(), key=lambda e: e.distance_to(point_on_curve))
            else:
                closest = self
            u_value = closest.param_at_point(point_on_curve)
            comp_curve, occt_param, closest_forward = closest._occt_param_at(u_value)

        derivative_gp_vec = comp_curve.DN(occt_param, order)
        if derivative_gp_vec.Magnitude() == 0:
            return Vector(0, 0, 0)

        derivative = Vector(derivative_gp_vec)
        # Potentially flip the direction of the derivative
        if order % 2 == 1:
            if isinstance(self, Wire):
                edge_same_as_wire = closest_forward == self.is_forward
                derivative = derivative if edge_same_as_wire else -derivative
            else:
                derivative = derivative if self.is_forward else -derivative

        return derivative

    def end_point(self) -> Vector:
        """The end point of this edge.

        Note that circles may have identical start and end points.
        """
        curve = self.geom_adaptor()
        umax = curve.LastParameter() if self.is_forward else curve.FirstParameter()

        return Vector(curve.Value(umax))

    def _intersect(
        self,
        other: Shape | Vector | Location | Axis | Plane,
        tolerance: float = 1e-6,
        include_touched: bool = False,
    ) -> ShapeList | None:
        """Single-object intersection for Edge/Wire.

        Returns same-dimension overlap or crossing geometry:
        - 1D + 1D → Edge (collinear overlap) + Vertex (crossing)
        - 1D + Face/Solid/Compound → delegates to other._intersect(self)

        Args:
            other: Shape or geometry object to intersect with
            tolerance: tolerance for intersection detection
            include_touched: if True, include boundary contacts
                (only relevant when Solids are involved)
        """
        # Convert geometry objects to shapes
        if isinstance(other, Vector):
            other = Vertex(other)
        elif isinstance(other, Location):
            other = Vertex(other.position)
        elif isinstance(other, Axis):
            other = Edge(other)

        results: ShapeList = ShapeList()

        # Trim infinite edges before OCCT operations
        if isinstance(other, Edge) and other.is_infinite:
            bbox = self.bounding_box(optimal=False)
            other = other.trim_infinite(
                bbox.diagonal + (other.center() - bbox.center()).length
            )

        # 1D + Plane: run Section directly with OCP Face
        if isinstance(other, Plane):
            face: Shape = Shape(BRepBuilderAPI_MakeFace(other.wrapped).Face())
            section = self._bool_op_list((self,), (face,), BRepAlgoAPI_Section())
            results.extend(section.expand())

        # 1D + 1D: Common (collinear overlap) + Section (crossing vertices)
        elif isinstance(other, (Edge, Wire)):
            common = self._bool_op_list((self,), (other,), BRepAlgoAPI_Common())
            results.extend(common.expand())
            section = self._bool_op_list((self,), (other,), BRepAlgoAPI_Section())
            # Extract vertices from section (edges already in Common for wires)
            for shape in section:
                if isinstance(shape, Vertex) and not shape.is_null:
                    results.append(shape)

        # 1D + Vertex: point containment on edge
        elif isinstance(other, Vertex):
            if other.distance_to(self) <= tolerance:
                results.append(other)

        # Delegate to higher-order shapes (Face, Solid, etc.)
        else:
            result = other._intersect(self, tolerance, include_touched)
            if result:
                results.extend(result)

        return results if results else None

    def location_at(
        self,
        distance: float,
        position_mode: PositionMode = PositionMode.PARAMETER,
        frame_method: FrameMethod = FrameMethod.FRENET,
        x_dir: VectorLike | None = None,
    ) -> Location:
        """Locations along curve

        Generate a location along the underlying curve.

        Args:
            distance (float): distance or parameter value
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.
            frame_method (FrameMethod, optional): moving frame calculation method.
                The FRENET frame can “twist” or flip unexpectedly, especially near flat
                spots. The CORRECTED frame behaves more like a “camera dolly” or
                sweep profile would — it's smoother and more stable.
                Defaults to FrameMethod.FRENET.
            x_dir (VectorLike, optional): override the x_dir to help with plane
                creation along a 1D shape. Must be perpendicular to shapes tangent.
                Defaults to None.

        Returns:
            Location: A Location object representing local coordinate system
                at the specified distance.
        """
        curve = self.geom_adaptor()

        if not self.is_forward:
            if position_mode == PositionMode.PARAMETER:
                distance = 1 - distance
            else:
                distance = self.length - distance

        if isinstance(self, Wire):
            if frame_method == FrameMethod.CORRECTED:
                # BRep_CompCurve parameter
                param = self.param_at(distance / self.length)
            else:
                # A BRep_Curve parameter taken from a Edge based curve
                if position_mode == PositionMode.PARAMETER:
                    curve, param, _ = self._occt_param_at(
                        distance * self.length, PositionMode.LENGTH
                    )
                else:
                    curve, param, _ = self._occt_param_at(distance, PositionMode.LENGTH)

        else:  # Edge
            if position_mode == PositionMode.PARAMETER:
                param = self.param_at(distance)
            else:
                param = self.param_at(distance / self.length)
            curve = self.geom_adaptor()

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
        if x_dir is not None:
            try:

                transformation.SetTransformation(
                    gp_Ax3(pnt, gp_Dir(tangent.XYZ()), Vector(x_dir).to_dir()), gp_Ax3()
                )
            except Standard_ConstructionError as exc:
                raise ValueError(
                    f"Unable to create location with given x_dir {x_dir}. "
                    f"x_dir must be perpendicular to shape's tangent "
                    f"{tuple(Vector(tangent))}."
                ) from exc

        else:
            transformation.SetTransformation(
                gp_Ax3(pnt, gp_Dir(tangent.XYZ()), gp_Dir(normal.XYZ())), gp_Ax3()
            )
        loc = Location(TopLoc_Location(transformation))

        if self.is_forward:
            return loc
        return -loc

    def locations(
        self,
        distances: Iterable[float],
        position_mode: PositionMode = PositionMode.PARAMETER,
        frame_method: FrameMethod = FrameMethod.FRENET,
        x_dir: VectorLike | None = None,
    ) -> list[Location]:
        """Locations along curve

        Generate location along the curve

        Args:
            distances (Iterable[float]): distance or parameter values
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.
            frame_method (FrameMethod, optional): moving frame calculation method.
                Defaults to FrameMethod.FRENET.
            x_dir (VectorLike, optional): override the x_dir to help with plane
                creation along a 1D shape. Must be perpendicular to shapes tangent.
                Defaults to None.

        Returns:
            list[Location]: A list of Location objects representing local coordinate
                systems at the specified distances.
        """
        return [
            self.location_at(d, position_mode, frame_method, x_dir) for d in distances
        ]

    def normal(self) -> Vector:
        """Calculate the normal Vector. Only possible for planar curves.

        :return: normal vector

        Args:

        Returns:

        """
        if self._wrapped is None:
            raise ValueError("Can't find normal of empty edge/wire")

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

    def offset_2d(
        self,
        distance: float,
        kind: Kind = Kind.ARC,
        side: Side = Side.BOTH,
        closed: bool = True,
    ) -> Edge | Wire:
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
            # pylint: disable=[no-member]
            edges = [edge.trim(0.0, 0.5), edge.trim(0.5, 1.0)]
            topods_wire = Wire(edges).wrapped
        else:
            topods_wire = line.wrapped
        assert topods_wire is not None

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
            endpoints = (line.position_at(0), line.position_at(1))
            offset_edges = offset_wire.edges().filter_by(
                lambda e: (
                    e.geom_type == GeomType.CIRCLE
                    and any((e.arc_center - pt).length < TOLERANCE for pt in endpoints)
                ),
                reverse=True,
            )
            wires = edges_to_wires(offset_edges)
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
                offset_wire = Wire(
                    line.edges() + offset_wire.edges() + ShapeList([edge0, edge1])
                )

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

    def position_at(
        self, position: float, position_mode: PositionMode = PositionMode.PARAMETER
    ) -> Vector:
        """Position At

        Generate a position along the underlying Wire.

        Args:
            position (float): distance or parameter value
            position_mode (PositionMode, optional): position calculation mode. Defaults to
                PositionMode.PARAMETER.

        Returns:
            Vector: position on the underlying curve
        """
        # Find the TopoDS_Edge and parameter on that edge at given position
        edge_curve_adaptor, occt_edge_param, _ = self._occt_param_at(
            position, position_mode
        )

        return Vector(edge_curve_adaptor.Value(occt_edge_param))

    def positions(
        self,
        distances: Iterable[float] | None = None,
        position_mode: PositionMode = PositionMode.PARAMETER,
        deflection: float | None = None,
    ) -> list[Vector]:
        """Positions along curve

        Generate positions along the underlying curve

        Args:
            distances (Iterable[float] | None, optional): distance or parameter values.
                Defaults to None.
            position_mode (PositionMode, optional): position calculation mode only applies
                when using distances. Defaults to PositionMode.PARAMETER.
            deflection (float | None, optional): maximum deflection between the curve and
                the polygon that results from the computed points. Defaults to None.


        Returns:
            list[Vector]: positions along curve
        """
        if deflection is not None:
            curve: BRepAdaptor_Curve | BRepAdaptor_CompCurve = self.geom_adaptor()
            # GCPnts_UniformDeflection provides the best results but is limited
            if curve.Continuity() in (GeomAbs_C2, GeomAbs_C3, GeomAbs_CN):
                discretizer: (
                    GCPnts_UniformDeflection | GCPnts_QuasiUniformDeflection
                ) = GCPnts_UniformDeflection()
            else:
                discretizer = GCPnts_QuasiUniformDeflection()

            discretizer.Initialize(
                curve,
                deflection,
                curve.FirstParameter(),
                curve.LastParameter(),
            )
            if not discretizer.IsDone() or discretizer.NbPoints() == 0:
                raise RuntimeError("Deflection calculation failed")
            return [
                Vector(curve.Value(discretizer.Parameter(i + 1)))
                for i in range(discretizer.NbPoints())
            ]
        elif distances is not None:
            return [self.position_at(d, position_mode) for d in distances]
        else:
            raise ValueError("Either distances or deflection must be provided")

    def project(
        self, face: Face, direction: VectorLike, closest: bool = True
    ) -> Edge | Wire | ShapeList[Edge | Wire]:
        """Project onto a face along the specified direction

        Args:
          face: Face:
          direction: VectorLike:
          closest: bool:  (Default value = True)

        Returns:

        """
        if self._wrapped is None or not face:
            raise ValueError("Can't project an empty Edge or Wire onto empty Face")

        bldr = BRepProj_Projection(
            self.wrapped, face.wrapped, Vector(direction).to_dir()
        )
        shapes: TopoDS_Compound = bldr.Shape()

        # select the closest projection if requested
        return_value: Edge | Wire | ShapeList[Edge | Wire]

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
        look_at: VectorLike | None = None,
        focus: float | None = None,
    ) -> tuple[ShapeList[Edge], ShapeList[Edge]]:
        """project_to_viewport

        Project a shape onto a viewport returning visible and hidden Edges.

        Args:
            viewport_origin (VectorLike): location of viewport
            viewport_up (VectorLike, optional): direction of the viewport y axis.
                Defaults to (0, 0, 1).
            look_at (VectorLike, optional): point to look at.
                Defaults to None (center of shape).
            focus (float, optional): the focal length for perspective projection
                Defaults to None (orthographic projection)

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

        if self._wrapped is None:
            raise ValueError("Can't project empty edge/wire")

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
        projector = (
            HLRAlgo_Projector(camera_coordinate_system, focus)
            if focus
            else HLRAlgo_Projector(camera_coordinate_system)
        )

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

    def start_point(self) -> Vector:
        """The start point of this edge

        Note that circles may have identical start and end points.
        """
        curve = self.geom_adaptor()
        umin = curve.FirstParameter() if self.is_forward else curve.LastParameter()

        return Vector(curve.Value(umin))

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

    def tangent_at(
        self,
        position: float | VectorLike = 0.5,
        position_mode: PositionMode = PositionMode.PARAMETER,
    ) -> Vector:
        """tangent_at

        Find the tangent at a given position on the 1D shape where the position
        is either a float (or int) parameter or a point that lies on the shape.

        Args:
            position (float |  VectorLike): distance, parameter value, or
                point on shape. Defaults to 0.5.
            position_mode (PositionMode, optional): position calculation mode.
                Defaults to PositionMode.PARAMETER.

        Returns:
            Vector: tangent value
        """
        return self.derivative_at(position, 1, position_mode).normalized()


class Edge(Mixin1D[TopoDS_Edge]):
    """An Edge in build123d is a fundamental element in the topological data structure
    representing a one-dimensional geometric entity within a 3D model. It encapsulates
    information about a curve, which could be a line, arc, or other parametrically
    defined shape. Edge is crucial in for precise modeling and manipulation of curves,
    facilitating operations like filleting, chamfering, and Boolean operations. It
    serves as a building block for constructing complex structures, such as wires
    and faces."""

    # pylint: disable=too-many-public-methods

    order = 1.0
    # ---- Constructor ----

    def __init__(
        self,
        obj: TopoDS_Edge | Axis | None | None = None,
        label: str = "",
        color: Color | None = None,
        parent: Compound | None = None,
    ):
        """Build an Edge from an OCCT TopoDS_Shape/TopoDS_Edge

        Args:
            obj (TopoDS_Edge | Axis, optional): OCCT Edge or Axis.
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

    # ---- Properties ----

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

    # ---- Class Methods ----

    @classmethod
    def extrude(cls, obj: Vertex, direction: VectorLike) -> Edge:
        """extrude

        Extrude a Vertex into an Edge.

        Args:
            direction (VectorLike): direction and magnitude of extrusion

        Raises:
            ValueError: Unsupported class
            RuntimeError: Generated invalid result

        Returns:
            Edge: extruded shape
        """
        if not obj:
            raise ValueError("Can't extrude empty vertex")
        return Edge(TopoDS.Edge(_extrude_topods_shape(obj.wrapped, direction)))

    @classmethod
    def make_bezier(
        cls, *cntl_pnts: VectorLike, weights: list[float] | None = None
    ) -> Edge:
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

    @overload
    @classmethod
    def make_constrained_arcs(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_two: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        radius: float,
        sagitta: Sagitta = Sagitta.SHORT,
    ) -> ShapeList[Edge]:
        """
        Create all planar circular arcs of a given radius that are tangent/contacting
        the two provided objects on the XY plane.
        Args:
            tangency_one, tangency_two
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entities to be contacted/touched by the circle(s)
            radius (float): arc radius
            sagitta (LengthConstraint, optional): returned arc selector
                (i.e. either the short, long or both arcs). Defaults to
                LengthConstraint.SHORT.

        Returns:
            ShapeList[Edge]: tangent arcs
        """

    @overload
    @classmethod
    def make_constrained_arcs(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_two: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        center_on: Axis | Edge,
        sagitta: Sagitta = Sagitta.SHORT,
    ) -> ShapeList[Edge]:
        """
        Create all planar circular arcs whose circle is tangent to two objects and whose
        CENTER lies on a given locus (line/circle/curve) on the XY plane.

        Args:
            tangency_one, tangency_two
                (tuple[Axus | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entities to be contacted/touched by the circle(s)
            center_on (Axis | Edge): center must lie on this object
            sagitta (LengthConstraint, optional): returned arc selector
                (i.e. either the short, long or both arcs). Defaults to
                LengthConstraint.SHORT.

        Returns:
            ShapeList[Edge]: tangent arcs
        """

    @overload
    @classmethod
    def make_constrained_arcs(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_two: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_three: (
            tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike
        ),
        *,
        sagitta: Sagitta = Sagitta.SHORT,
    ) -> ShapeList[Edge]:
        """
        Create planar circular arc(s) on XY tangent to three provided objects.

        Args:
            tangency_one, tangency_two, tangency_three
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entities to be contacted/touched by the circle(s)
            sagitta (LengthConstraint, optional): returned arc selector
                (i.e. either the short, long or both arcs). Defaults to
                LengthConstraint.SHORT.

        Returns:
            ShapeList[Edge]: tangent arcs
        """

    @overload
    @classmethod
    def make_constrained_arcs(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        center: VectorLike,
    ) -> ShapeList[Edge]:
        """make_constrained_arcs

        Create planar circle(s) on XY whose center is fixed and that are tangent/contacting
        a single object.

        Args:
            tangency_one
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entity to be contacted/touched by the circle(s)
            center (VectorLike): center position

        Returns:
            ShapeList[Edge]: tangent arcs
        """

    @overload
    @classmethod
    def make_constrained_arcs(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        radius: float,
        center_on: Edge,
    ) -> ShapeList[Edge]:
        """make_constrained_arcs

        Create planar circle(s) on XY that:
        - are tangent/contacting a single object, and
        - have a fixed radius, and
        - have their CENTER constrained to lie on a given locus curve.

        Args:
            tangency_one
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entity to be contacted/touched by the circle(s)
            radius (float): arc radius
            center_on (Axis | Edge): center must lie on this object
            sagitta (LengthConstraint, optional): returned arc selector
                (i.e. either the short, long or both arcs). Defaults to
                LengthConstraint.SHORT.

        Returns:
            ShapeList[Edge]: tangent arcs
        """

    @classmethod
    def make_constrained_arcs(
        cls,
        *args,
        sagitta: Sagitta = Sagitta.SHORT,
        **kwargs,
    ) -> ShapeList[Edge]:

        tangency_one = args[0] if len(args) > 0 else None
        tangency_two = args[1] if len(args) > 1 else None
        tangency_three = args[2] if len(args) > 2 else None

        tangency_one = kwargs.pop("tangency_one", tangency_one)
        tangency_two = kwargs.pop("tangency_two", tangency_two)
        tangency_three = kwargs.pop("tangency_three", tangency_three)

        radius = kwargs.pop("radius", None)
        center = kwargs.pop("center", None)
        center_on = kwargs.pop("center_on", None)

        # Handle unexpected kwargs
        if kwargs:
            raise TypeError(f"Unexpected argument(s): {', '.join(kwargs.keys())}")

        tangency_args = [
            t for t in (tangency_one, tangency_two, tangency_three) if t is not None
        ]
        tangencies: list[tuple[Edge, Tangency] | Edge | Vector] = []
        for tangency_arg in tangency_args:
            if isinstance(tangency_arg, Axis):
                tangencies.append(Edge(tangency_arg))
                continue
            elif isinstance(tangency_arg, Edge):
                tangencies.append(tangency_arg)
                continue
            if isinstance(tangency_arg, tuple):
                if isinstance(tangency_arg[0], Axis):
                    tangencies.append(tuple(Edge(tangency_arg[0], tangency_arg[1])))
                    continue
                elif isinstance(tangency_arg[0], Edge):
                    tangencies.append(tangency_arg)
                    continue
            if isinstance(tangency_arg, Vertex):
                tangencies.append(Vector(tangency_arg) + tangency_arg.position)
                continue

            # if not Axes, Edges, constrained Edges or Vertex convert to Vectors
            try:
                tangencies.append(Vector(tangency_arg))
            except Exception as exc:
                raise TypeError(f"Invalid tangency: {tangency_arg!r}") from exc

        # # Sort the tangency inputs so points are always last
        tangencies = sorted(tangencies, key=lambda x: isinstance(x, Vector))

        tan_count = len(tangencies)
        if not (1 <= tan_count <= 3):
            raise TypeError("Provide 1 to 3 tangency targets.")

        # Radius sanity
        if radius is not None and radius <= 0:
            raise ValueError("radius must be > 0.0")

        if center_on is not None and isinstance(center_on, Axis):
            center_on = Edge(center_on)

        # --- decide problem kind ---
        if (
            tan_count == 2
            and radius is not None
            and center is None
            and center_on is None
        ):
            return _make_2tan_rad_arcs(
                *tangencies,
                radius=radius,
                sagitta=sagitta,
                edge_factory=cls,
            )
        if (
            tan_count == 2
            and center_on is not None
            and radius is None
            and center is None
        ):
            return _make_2tan_on_arcs(
                *tangencies,
                center_on=center_on,
                sagitta=sagitta,
                edge_factory=cls,
            )
        if tan_count == 3 and radius is None and center is None and center_on is None:
            return _make_3tan_arcs(*tangencies, sagitta=sagitta, edge_factory=cls)
        if (
            tan_count == 1
            and center is not None
            and radius is None
            and center_on is None
        ):
            return _make_tan_cen_arcs(*tangencies, center=center, edge_factory=cls)
        if tan_count == 1 and center_on is not None and radius is not None:
            return _make_tan_on_rad_arcs(
                *tangencies, center_on=center_on, radius=radius, edge_factory=cls
            )

        raise ValueError("Unsupported or ambiguous combination of constraints.")

    @overload
    @classmethod
    def make_constrained_lines(
        cls,
        tangency_one: tuple[Edge, Tangency] | Axis | Edge,
        tangency_two: tuple[Edge, Tangency] | Axis | Edge,
    ) -> ShapeList[Edge]:
        """
        Create all planar line(s) on the XY plane tangent to two provided curves.

        Args:
            tangency_one, tangency_two
                (tuple[Edge, Tangency] | Axis | Edge):
                Geometric entities to be contacted/touched by the line(s).

        Returns:
            ShapeList[Edge]: tangent lines
        """

    @overload
    @classmethod
    def make_constrained_lines(
        cls,
        tangency_one: tuple[Edge, Tangency] | Edge,
        tangency_two: Vector,
    ) -> ShapeList[Edge]:
        """
        Create all planar line(s) on the XY plane tangent to one curve and passing
        through a fixed point.

        Args:
            tangency_one
                (tuple[Edge, Tangency] | Edge):
                Geometric entity to be contacted/touched by the line(s).
            tangency_two (Vector):
                Fixed point through which the line(s) must pass.

        Returns:
            ShapeList[Edge]: tangent lines
        """

    @overload
    @classmethod
    def make_constrained_lines(
        cls,
        tangency_one: tuple[Edge, Tangency] | Edge,
        tangency_two: Axis,
        *,
        angle: float | None = None,
        direction: VectorLike | None = None,
    ) -> ShapeList[Edge]:
        """
        Create all planar line(s) on the XY plane tangent to one curve with a
        fixed orientation, defined either by an angle measured from a reference
        axis or by a direction vector.

        Args:
            tangency_one (Edge): edge that line will be tangent to
            tangency_two (Axis): reference axis from which the angle is measured
            angle : float, optional
                Line orientation in degrees (measured CCW from the X-axis).
            direction : VectorLike, optional
                Direction vector for the line (only X and Y components are used).
            Note: one of angle or direction must be provided

        Returns:
            ShapeList[Edge]: tangent lines
        """

    @classmethod
    def make_constrained_lines(cls, *args, **kwargs) -> ShapeList[Edge]:
        """
        Create planar line(s) on XY subject to tangency/contact constraints.

        Supported cases
        ---------------
        1. Tangent to two curves
        2. Tangent to one curve and passing through a given point
        """
        tangency_one = args[0] if len(args) > 0 else None
        tangency_two = args[1] if len(args) > 1 else None

        tangency_one = kwargs.pop("tangency_one", tangency_one)
        tangency_two = kwargs.pop("tangency_two", tangency_two)

        angle = kwargs.pop("angle", None)
        direction = kwargs.pop("direction", None)
        direction = Vector(direction) if direction is not None else None

        is_ref = angle is not None or direction is not None
        # Handle unexpected kwargs
        if kwargs:
            raise TypeError(f"Unexpected argument(s): {', '.join(kwargs.keys())}")

        tangency_args = [t for t in (tangency_one, tangency_two) if t is not None]
        if len(tangency_args) != 2:
            raise TypeError("Provide exactly 2 tangency targets.")

        tangencies: list[tuple[Edge, Tangency] | Axis | Edge | Vector] = []
        for i, tangency_arg in enumerate(tangency_args):
            if isinstance(tangency_arg, Axis):
                if i == 1 and is_ref:
                    tangencies.append(tangency_arg)
                else:
                    tangencies.append(Edge(tangency_arg))
                continue
            elif isinstance(tangency_arg, Edge):
                tangencies.append(tangency_arg)
                continue
            if isinstance(tangency_arg, tuple) and isinstance(tangency_arg[0], Edge):
                tangencies.append(tangency_arg)
                continue
            # Fallback: treat as a point
            try:
                tangencies.append(Vector(tangency_arg))
            except Exception as exc:
                raise TypeError(f"Invalid tangency: {tangency_arg!r}") from exc

        # Sort so Vector (point) | Axis is always last
        tangencies = sorted(tangencies, key=lambda x: isinstance(x, (Axis, Vector)))

        # --- decide problem kind ---
        if angle is not None or direction is not None:
            if isinstance(tangencies[0], tuple):
                assert isinstance(
                    tangencies[0][0], Edge
                ), "Internal error - 1st tangency must be Edge"
            else:
                assert isinstance(
                    tangencies[0], Edge
                ), "Internal error - 1st tangency must be Edge"
            if angle is not None:
                ang_rad = radians(angle)
            else:
                assert direction is not None
                ang_rad = atan2(direction.Y, direction.X)
            assert isinstance(
                tangencies[1], Axis
            ), "Internal error - 2nd tangency must be an Axis"
            return _make_tan_oriented_lines(
                tangencies[0], tangencies[1], ang_rad, edge_factory=cls
            )
        else:
            assert not isinstance(
                tangencies[0], (Axis, Vector)
            ), "Internal error - 1st tangency can't be an Axis | Vector"
            assert not isinstance(
                tangencies[1], Axis
            ), "Internal error - 2nd tangency can't be an Axis"

            return _make_2tan_lines(tangencies[0], tangencies[1], edge_factory=cls)

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
            # radians, apply correction
            a1 = (start_angle * DEG2RAD) - correction_angle
            a2 = (end_angle * DEG2RAD) - correction_angle

            if angular_direction == AngularDirection.COUNTER_CLOCKWISE:
                # ensure a2 > a1
                if a2 <= a1:
                    a2 += 2 * pi
                sense = True
                alpha1, alpha2 = a1, a2
            else:
                # CLOCKWISE: want decreasing angle
                if a2 >= a1:
                    a2 -= 2 * pi
                # make alpha1 < alpha2 by swapping and reversing sense
                sense = False
                alpha1, alpha2 = a2, a1

            ellipse_geom = GC_MakeArcOfEllipse(
                ellipse_gp, alpha1, alpha2, sense
            ).Value()
            ellipse = cls(BRepBuilderAPI_MakeEdge(ellipse_geom).Edge())

        return ellipse

    @classmethod
    def make_parabola(
        cls,
        focal_length: float,
        plane: Plane = Plane.XY,
        start_angle: float = 0.0,
        end_angle: float = 90.0,
        angular_direction: AngularDirection = AngularDirection.COUNTER_CLOCKWISE,
    ) -> Edge:
        """make parabola

        Makes an parabola centered at the origin of plane.

        Args:
            focal_length (float): focal length the parabola (distance from the vertex to focus along the x-axis of plane)
            plane (Plane, optional): base plane. Defaults to Plane.XY.
            start_angle (float, optional): Defaults to 0.0.
            end_angle (float, optional): Defaults to 90.0.
            angular_direction (AngularDirection, optional): arc direction.
                Defaults to AngularDirection.COUNTER_CLOCKWISE.

        Returns:
            Edge: full or partial parabola
        """
        parabola_gp = gp_Parab(plane.to_gp_ax2(), focal_length)

        parabola_geom = GC_MakeArcOfParabola(
            parabola_gp,
            start_angle * DEG2RAD,
            end_angle * DEG2RAD,
            angular_direction == AngularDirection.COUNTER_CLOCKWISE,
        ).Value()
        parabola = cls(BRepBuilderAPI_MakeEdge(parabola_geom).Edge())

        return parabola

    @classmethod
    def make_hyperbola(
        cls,
        x_radius: float,
        y_radius: float,
        plane: Plane = Plane.XY,
        start_angle: float = 360.0,
        end_angle: float = 360.0,
        angular_direction: AngularDirection = AngularDirection.COUNTER_CLOCKWISE,
    ) -> Edge:
        """make hyperbola

        Makes a hyperbola centered at the origin of plane.

        Args:
            x_radius (float): x radius of the hyperbola (along the x-axis of plane)
            y_radius (float): y radius of the hyperbola (along the y-axis of plane)
            plane (Plane, optional): base plane. Defaults to Plane.XY.
            start_angle (float, optional): Defaults to 360.0.
            end_angle (float, optional): Defaults to 360.0.
            angular_direction (AngularDirection, optional): arc direction.
                Defaults to AngularDirection.COUNTER_CLOCKWISE.

        Returns:
            Edge: full or partial hyperbola
        """
        ax1 = gp_Ax1(plane.origin.to_pnt(), plane.z_dir.to_dir())

        if y_radius > x_radius:
            # swap x and y radius and rotate by 90° afterwards to create an ellipse
            # with x_radius < y_radius
            correction_angle = 90.0 * DEG2RAD
            hyperbola_gp = gp_Hypr(plane.to_gp_ax2(), y_radius, x_radius).Rotated(
                ax1, correction_angle
            )
        else:
            correction_angle = 0.0
            hyperbola_gp = gp_Hypr(plane.to_gp_ax2(), x_radius, y_radius)

        if start_angle == end_angle:  # full hyperbola case
            hyperbola = cls(BRepBuilderAPI_MakeEdge(hyperbola_gp).Edge())
        else:  # arc case
            # take correction_angle into account
            hyperbola_geom = GC_MakeArcOfHyperbola(
                hyperbola_gp,
                start_angle * DEG2RAD - correction_angle,
                end_angle * DEG2RAD - correction_angle,
                angular_direction == AngularDirection.COUNTER_CLOCKWISE,
            ).Value()
            hyperbola = cls(BRepBuilderAPI_MakeEdge(hyperbola_geom).Edge())

        return hyperbola

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
        flip = Axis(first).is_opposite(Axis(second))
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
        tangents: list[VectorLike] | None = None,
        periodic: bool = False,
        parameters: list[float] | None = None,
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
        point_vectors = [Vector(point) for point in points]
        if tangents:
            tangent_vectors = tuple(Vector(v) for v in tangents)
        pnts = TColgp_HArray1OfPnt(1, len(point_vectors))
        for i, point in enumerate(point_vectors):
            pnts.SetValue(i + 1, point.to_pnt())

        if parameters is None:
            spline_builder = GeomAPI_Interpolate(pnts, periodic, tol)
        else:
            if len(parameters) != (len(point_vectors) + periodic):
                raise ValueError(
                    "There must be one parameter for each interpolation point "
                    "(plus one if periodic), or none specified. Parameter count: "
                    f"{len(parameters)}, point count: {len(point_vectors)}"
                )
            parameters_array = TColStd_HArray1OfReal(1, len(parameters))
            for p_index, p_value in enumerate(parameters):
                parameters_array.SetValue(p_index + 1, p_value)

            spline_builder = GeomAPI_Interpolate(pnts, parameters_array, periodic, tol)

        if tangents:
            if len(tangent_vectors) == 2 and len(point_vectors) != 2:
                # Specify only initial and final tangent:
                spline_builder.Load(
                    tangent_vectors[0].wrapped, tangent_vectors[1].wrapped, scale
                )
            else:
                if len(tangent_vectors) != len(point_vectors):
                    raise ValueError(
                        f"There must be one tangent for each interpolation point, "
                        f"or just two end point tangents. Tangent count: "
                        f"{len(tangent_vectors)}, point count: {len(point_vectors)}"
                    )

                # Specify a tangent for each interpolation point:
                tangents_array = TColgp_Array1OfVec(1, len(tangent_vectors))
                tangent_enabled_array = TColStd_HArray1OfBoolean(
                    1, len(tangent_vectors)
                )
                for t_index, t_value in enumerate(tangent_vectors):
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
        smoothing: tuple[float, float, float] | None = None,
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

    # ---- Instance Methods ----

    def close(self) -> Edge | Wire:
        """Close an Edge"""
        if not self.is_closed:
            return_value = Wire([self]).close()
        else:
            return_value = self

        return return_value

    def distribute_locations(
        self: Wire | Edge,
        count: int,
        start: float = 0.0,
        stop: float = 1.0,
        positions_only: bool = False,
    ) -> list[Location]:
        """Distribute Locations

        Distribute locations along edge or wire.

        Args:
          self: Wire:Edge:
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
                loc.orientation = Vector(0, 0, 0)

        return locations

    def _extend_spline(
        self,
        at_start: bool,
        geom_surface: Geom_Surface,
        extension_factor: float = 0.1,
    ):
        """Helper method to slightly extend an edge that is bound to a surface"""
        if self._wrapped is None:
            raise ValueError("Can't extend empty spline")
        if self.geom_type != GeomType.BSPLINE:
            raise TypeError("_extend_spline only works with splines")

        u_start: float = self.param_at(0)
        u_end: float = self.param_at(1)

        curve_original = tcast(
            Geom_BSplineCurve, BRep_Tool.Curve_s(self.wrapped, u_start, u_end)
        )
        n_poles = curve_original.NbPoles()
        poles = [curve_original.Pole(i + 1) for i in range(n_poles)]
        # Find position and tangent past end of spline to extend it
        ends = (-extension_factor, 1) if at_start else (0, 1 + extension_factor)
        if at_start:
            new_pole = self.position_at(-extension_factor).to_pnt()
            poles = [new_pole] + poles
        else:
            new_pole = self.position_at(1 + extension_factor).to_pnt()
            poles = poles + [new_pole]
        tangents: list[VectorLike] = [self.tangent_at(p) for p in ends]

        pnts: list[VectorLike] = [Vector(p) for p in poles]
        extended_edge = Edge.make_spline(pnts, tangents=tangents)
        assert extended_edge.wrapped is not None

        geom_curve = BRep_Tool.Curve_s(
            extended_edge.wrapped, extended_edge.param_at(0), extended_edge.param_at(1)
        )
        snapped_geom_curve = GeomProjLib.Project_s(geom_curve, geom_surface)
        if snapped_geom_curve is None:
            raise RuntimeError("Failed to snap extended edge to surface")

        # Build a new projected edge
        snapped_edge = Edge(BRepBuilderAPI_MakeEdge(snapped_geom_curve).Edge())

        return snapped_edge, snapped_geom_curve

    def find_intersection_points(
        self, other: Axis | Edge | None = None, tolerance: float = TOLERANCE
    ) -> ShapeList[Vector]:
        """find_intersection_points

        Determine the points where a 2D edge crosses itself or another 2D edge

        Args:
            other (Axis | Edge): curve to compare with
            tolerance (float, optional): the precision of computing the intersection points.
                 Defaults to TOLERANCE.

        Raises:
            ValueError: empty edge

        Returns:
            ShapeList[Vector]: list of intersection points
        """
        if self._wrapped is None:
            raise ValueError("Can't find intersections of empty edge")

        # Convert an Axis into an edge at least as large as self and Axis start point
        if isinstance(other, Axis):
            pos = tcast(Vector, other.position)
            self_bbox_w_edge = self.bounding_box().add(Vertex(pos).bounding_box())
            other = Edge.make_line(
                pos + other.direction * (-1 * self_bbox_w_edge.diagonal),
                pos + other.direction * self_bbox_w_edge.diagonal,
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
        if other is not None and other.wrapped is not None:
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
        u_values: list[float]

        if self.geom_type == GeomType.LINE:
            if self.tangent_angle_at(0) == angle:
                u_values = [0]
            else:
                u_values = []
        else:
            # Solve this problem geometrically by creating a tangent curve and finding intercepts
            periodic = int(self.is_closed)  # if closed don't include end point
            tan_pnts: list[VectorLike] = []
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
            intercept_pnts: list[Vector] = []
            for i in range(min_range, max_range + 1, 360):
                line = Edge.make_line((0, angle + i, 0), (100, angle + i, 0))
                intercept_pnts.extend(tan_curve.find_intersection_points(line))

            u_values = [p.X for p in intercept_pnts]

        return u_values

    def geom_adaptor(self) -> BRepAdaptor_Curve:
        """Return the Geom Curve from this Edge"""
        if self._wrapped is None:
            raise ValueError("Can't find adaptor for empty edge")
        return BRepAdaptor_Curve(self.wrapped)

    def geom_equal(
        self,
        other: Edge,
        tol: float = 1e-6,
        num_interpolation_points: int = 5,
    ) -> bool:
        """Compare two edges for geometric equality within tolerance.

        This compares the geometric properties of two edges, not their topological
        identity. Two independently created edges with the same geometry will
        return True.

        Args:
            other: Edge to compare with
            tol: Tolerance for numeric comparisons. Defaults to 1e-6.
            num_interpolation_points: Number of points to sample for unknown
                curve types. Defaults to 5.

        Returns:
            bool: True if edges are geometrically equal within tolerance
        """
        if not isinstance(other, Edge):
            return False

        # geom_type must match
        if self.geom_type != other.geom_type:
            return False

        # Common: start and end points
        if (self @ 0) != (other @ 0) or (self @ 1) != (other @ 1):
            return False

        ga1 = self.geom_adaptor()
        ga2 = other.geom_adaptor()

        match self.geom_type:
            case GeomType.LINE:
                # Line: fully defined by endpoints (already checked)
                return True

            case GeomType.CIRCLE:
                c1, c2 = ga1.Circle(), ga2.Circle()
                return (
                    abs(c1.Radius() - c2.Radius()) < tol
                    and Vector(c1.Location()) == Vector(c2.Location())
                    and Vector(c1.Axis().Direction()) == Vector(c2.Axis().Direction())
                )

            case GeomType.ELLIPSE:
                e1, e2 = ga1.Ellipse(), ga2.Ellipse()
                return (
                    abs(e1.MajorRadius() - e2.MajorRadius()) < tol
                    and abs(e1.MinorRadius() - e2.MinorRadius()) < tol
                    and Vector(e1.Location()) == Vector(e2.Location())
                    and Vector(e1.Axis().Direction()) == Vector(e2.Axis().Direction())
                )

            case GeomType.HYPERBOLA:
                h1, h2 = ga1.Hyperbola(), ga2.Hyperbola()
                return (
                    abs(h1.MajorRadius() - h2.MajorRadius()) < tol
                    and abs(h1.MinorRadius() - h2.MinorRadius()) < tol
                    and Vector(h1.Location()) == Vector(h2.Location())
                    and Vector(h1.Axis().Direction()) == Vector(h2.Axis().Direction())
                )

            case GeomType.PARABOLA:
                p1, p2 = ga1.Parabola(), ga2.Parabola()
                return (
                    abs(p1.Focal() - p2.Focal()) < tol
                    and Vector(p1.Location()) == Vector(p2.Location())
                    and Vector(p1.Axis().Direction()) == Vector(p2.Axis().Direction())
                )

            case GeomType.BEZIER:
                b1, b2 = ga1.Bezier(), ga2.Bezier()
                if b1.Degree() != b2.Degree() or b1.NbPoles() != b2.NbPoles():
                    return False
                for i in range(1, b1.NbPoles() + 1):
                    if Vector(b1.Pole(i)) != Vector(b2.Pole(i)):
                        return False
                    if b1.IsRational() and abs(b1.Weight(i) - b2.Weight(i)) >= tol:
                        return False
                return True

            case GeomType.BSPLINE:
                s1, s2 = ga1.BSpline(), ga2.BSpline()
                if s1.Degree() != s2.Degree():
                    return False
                if s1.IsPeriodic() != s2.IsPeriodic():
                    return False
                if s1.NbPoles() != s2.NbPoles() or s1.NbKnots() != s2.NbKnots():
                    return False
                for i in range(1, s1.NbPoles() + 1):
                    if Vector(s1.Pole(i)) != Vector(s2.Pole(i)):
                        return False
                    if s1.IsRational() and abs(s1.Weight(i) - s2.Weight(i)) >= tol:
                        return False
                for i in range(1, s1.NbKnots() + 1):
                    if abs(s1.Knot(i) - s2.Knot(i)) >= tol:
                        return False
                    if s1.Multiplicity(i) != s2.Multiplicity(i):
                        return False
                return True

            case GeomType.OFFSET:
                oc1, oc2 = ga1.OffsetCurve(), ga2.OffsetCurve()
                # Compare offset values and directions
                if abs(oc1.Offset() - oc2.Offset()) >= tol:
                    return False
                if Vector(oc1.Direction()) != Vector(oc2.Direction()):
                    return False
                # Compare basis curves (recursive)
                basis1 = Edge(BRepBuilderAPI_MakeEdge(oc1.BasisCurve()).Edge())
                basis2 = Edge(BRepBuilderAPI_MakeEdge(oc2.BasisCurve()).Edge())
                return basis1.geom_equal(basis2, tol)

            case _:  # pragma: no cover
                # I don't think, GeomAbs_OtherCurve can be created in Python
                # OTHER/unknown: compare sample points
                for i in range(1, num_interpolation_points + 1):
                    t = i / (num_interpolation_points + 1)
                    if (self @ t) != (other @ t):
                        return False
                return True

    def _occt_param_at(
        self, position: float, position_mode: PositionMode = PositionMode.PARAMETER
    ) -> tuple[BRepAdaptor_Curve, float, bool]:
        """
        Map a position on this edge to its underlying OCCT parameter.

        This returns the OCCT `BRepAdaptor_CompCurve` for the edge together with
        the corresponding (non-normalized) curve parameter at the given position.
        The interpretation of `position` depends on `position_mode`:

        - ``PositionMode.PARAMETER``: `position` is a normalized curve parameter in [0, 1].
        - ``PositionMode.DISTANCE``: `position` is an arc length distance along the edge.

        Edge orientation (`is_forward`) is taken into account so that positions are
        measured consistently along the geometric curve.

        Args:
            position (float): Position along the edge, either a normalized parameter
                (0-1) or a distance, depending on `position_mode`.
            position_mode (PositionMode, optional): How to interpret `position`.
                Defaults to ``PositionMode.PARAMETER``.

        Returns:
            tuple[BRepAdaptor_CompCurve, float, bool]: The curve adaptor for this edge,
            the corresponding OCCT curve parameter and is_forward.
        """
        comp_curve = self.geom_adaptor()
        length = GCPnts_AbscissaPoint.Length_s(comp_curve)

        if position_mode == PositionMode.PARAMETER:
            if not self.is_forward:
                position = 1 - position
            value = position
        else:
            if not self.is_forward:
                position = self.length - position
            value = position / self.length

        occt_param = GCPnts_AbscissaPoint(
            comp_curve, length * value, comp_curve.FirstParameter()
        ).Parameter()
        return comp_curve, occt_param, self.is_forward

    def param_at(self, position: float) -> float:
        """
        Map a normalized arc-length position to the underlying OCCT parameter.

        Returns the native OCCT curve parameter corresponding to the
        given normalized `position` (0.0 → start, 1.0 → end). For closed/periodic
        edges, OCCT may return a value **outside** the edge's nominal parameter
        range `[param_min, param_max]` (e.g., by adding/subtracting multiples of
        the period). If you require a value folded into the edge's range, apply a
        modulo with the parameter span.

        Args:
            position (float): Normalized arc-length position along the shape,
                where `0.0` is the start and `1.0` is the end. Values outside
                `[0.0, 1.0]` are not validated and yield OCCT-dependent results.

        Returns:
            float: OCCT parameter (for edges) **or** composite “edgeIndex + fraction”
            parameter (for wires), as described above.

        """

        curve = self.geom_adaptor()

        length = GCPnts_AbscissaPoint.Length_s(curve)
        return GCPnts_AbscissaPoint(
            curve, length * position, curve.FirstParameter()
        ).Parameter()

    def param_at_point(self, point: VectorLike) -> float:
        """
        Return the normalized parameter (∈ [0.0, 1.0]) of the location on this edge
        closest to `point`.

        This method always returns a **normalized** parameter across the edge's full
        OCCT parameter range, even though the underlying OCP/OCCT queries work in
        native (non-normalized) parameters. It is robust to several OCCT quirks:

        1) Vertex snap (fast path)
        If `point` coincides (within tolerance) with one of the edge's vertices,
        that vertex's OCCT parameter is used and normalized to [0, 1].
        Note: for a closed edge, a vertex may represent both start and end; the
        mapping is therefore ambiguous and either end may be chosen.

        2) Projection via GeomAPI_ProjectPointOnCurve
        The OCCT projector's `LowerDistanceParameter()` can legitimately return a
        value **outside** the edge's [param_min, param_max] (e.g., periodic curves
        or implementation behavior). The result is wrapped back into range using a
        modulo by the parameter span and then normalized to [0, 1]. The projected
        answer is accepted only if re-evaluating the 3D point at that normalized
        parameter is within tolerance of the input `point`.

        3) Fallback numeric search (robust path)
        If the projector fails the validation, a bounded 1D search is performed
        over [0, 1] using progressive subdivision and local minimization of the
        3D distance ‖edge(u) - point‖. The first minimum found under geometric
        resolution is returned.

        Args:
            point (VectorLike): A point expected to lie on this edge (within tolerance).

        Raises:
            ValueError: If `point` is not on the edge within tolerance.
            ValueError: Can't find param on empty edge
            RuntimeError: If no parameter can be found (e.g., extremely pathological
                curves or numerical failure).
        Returns:
            float: Normalized parameter in [0.0, 1.0] corresponding to the point's
            closest location on the edge.
        """
        if self._wrapped is None:
            raise ValueError("Can't find param on empty edge")

        pnt = Vector(point)
        # Extract the edge's end parameters
        param_min, param_max = BRep_Tool.Range_s(self.wrapped)
        param_range = param_max - param_min

        # Method 1: the point is a Vertex

        # Check to see if the point is a Vertex of the Edge
        # Note: on a closed edge a single point is ambiguous so the result
        # is undefined with respect to matching the "start" or "end".
        nearest_vertex = min(self.vertices(), key=lambda v: (Vector(v) - pnt).length)
        if (
            Vector(nearest_vertex) - pnt
        ).length <= TOLERANCE and nearest_vertex.wrapped is not None:
            param = BRep_Tool.Parameter_s(nearest_vertex.wrapped, self.wrapped)
            return (param - param_min) / param_range

        separation = self.distance_to(pnt)
        if not isclose_b(separation, 0, abs_tol=TOLERANCE):
            raise ValueError(f"point ({pnt}) is {separation} from edge")

        # Method 2: project the point onto the edge
        # There are known issues with the OCP methods for some
        # curves which may return negative values or incorrect values at
        # end points.

        # Extract the normalized parameter using OCCT GeomAPI_ProjectPointOnCurve
        curve = BRep_Tool.Curve_s(self.wrapped, float(), float())
        projector = GeomAPI_ProjectPointOnCurve(pnt.to_pnt(), curve)
        param = projector.LowerDistanceParameter()
        # Note that for some periodic curves the LowerDistanceParameter might
        # be outside the given range
        curve_adaptor = BRepAdaptor_Curve(self.wrapped)
        if curve_adaptor.IsPeriodic():
            u_value = ((param - param_min) % curve_adaptor.Period()) / param_range
        else:
            u_value = (param - param_min) / param_range
        # Validate that GeomAPI_ProjectPointOnCurve worked correctly
        if (self.position_at(u_value) - pnt).length < TOLERANCE:
            return u_value

        # Method 3: search the edge for the point
        # Note that this search takes about 1.3ms on a complex curve while the
        # OCP methods take about 0.4ms.

        # This algorithm finds the normalized [0, 1] parameter of a point on an edge
        # by minimizing the 3D distance between the edge and the given point.
        #
        # Because some edges (e.g., BSplines) can have multiple local minima in the
        # distance function, we subdivide the [0, 1] domain into 2^n intervals
        # (logarithmic refinement) and perform a bounded minimization in each subinterval.
        #
        # The first solution found with an error smaller than the geometric resolution
        # is returned. If no such minimum is found after all subdivisions, a runtime error
        # is raised.

        max_divisions = 10  # Logarithmic refinement depth

        for division in range(max_divisions):
            intervals = 2**division
            step = 1.0 / intervals

            for i in range(intervals):
                lo, hi = i * step, (i + 1) * step

                result = minimize_scalar(
                    lambda u: (self.position_at(u) - pnt).length,
                    bounds=(lo, hi),
                    method="bounded",
                    options={"xatol": TOLERANCE / 2},
                )

                # Early exit if we're below resolution limit
                if (
                    result.fun
                    < (
                        self @ (result.x + TOLERANCE) - self @ (result.x - TOLERANCE)
                    ).length
                ):
                    return round(float(result.x), TOL_DIGITS)

        raise RuntimeError("Unable to find parameter, Edge is too complex")

    def project_to_shape(
        self,
        target_object: Shape,
        direction: VectorLike | None = None,
        center: VectorLike | None = None,
    ) -> ShapeList[Edge]:
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
        projected_wires = Wire(self).project_to_shape(target_object, direction, center)
        return projected_wires.edges()

    def reversed(self, reconstruct: bool = False) -> Edge:
        """reversed

        Return a copy of self with the opposite orientation.

        Args:
            reconstruct (bool, optional): rebuild edge instead of setting OCCT flag.
                Defaults to False.

        Returns:
            Edge: reversed
        """
        if self._wrapped is None:
            raise ValueError("An empty edge can't be reversed")

        assert isinstance(self.wrapped, TopoDS_Edge)

        reversed_edge = copy.deepcopy(self)
        if reconstruct:
            first: float = self.param_at(0)
            last: float = self.param_at(1)
            curve = BRep_Tool.Curve_s(self.wrapped, first, last)
            first = curve.ReversedParameter(first)
            last = curve.ReversedParameter(last)
            topods_edge = BRepBuilderAPI_MakeEdge(curve.Reversed(), last, first).Edge()
            reversed_edge.wrapped = topods_edge
        else:
            reversed_edge.wrapped = TopoDS.Edge(self.wrapped.Reversed())
        return reversed_edge

    def to_axis(self) -> Axis:
        """Translate a linear Edge to an Axis"""
        warnings.warn(
            "to_axis is deprecated and will be removed in a future version. "
            "Use 'Axis(Edge)' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.geom_type != GeomType.LINE:
            raise ValueError(
                f"to_axis is only valid for linear Edges not {self.geom_type}"
            )
        return Axis(self.position_at(0), self.position_at(1) - self.position_at(0))

    def to_wire(self) -> Wire:
        """Edge as Wire"""
        warnings.warn(
            "to_wire is deprecated and will be removed in a future version. "
            "Use 'Wire(Edge)' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Wire([self])

    def trim(self, start: float | VectorLike, end: float | VectorLike) -> Edge:
        """_summary_

        Args:
            start (float | VectorLike): _description_
            end (float | VectorLike): _description_

        Raises:
            TypeError: _description_
            ValueError: _description_

        Returns:
            Edge: _description_
        """
        """trim

        Create a new edge by keeping only the section between start and end.

        Args:
            start (float | VectorLike): 0.0 <= start < 1.0 or point on edge
            end (float  | VectorLike): 0.0 < end <= 1.0 or point on edge

        Raises:
            TypeError: invalid input, must be float or VectorLike
            ValueError: can't trim empty edge

        Returns:
            Edge: trimmed edge
        """

        start_u = Mixin1D._to_param(self, start, "start")
        end_u = Mixin1D._to_param(self, end, "end")

        start_u, end_u = sorted([start_u, end_u])

        # if start_u >= end_u:
        #     raise ValueError(f"start ({start_u}) must be less than end ({end_u})")

        if self._wrapped is None:
            raise ValueError("Can't trim empty edge")

        self_copy = copy.deepcopy(self)
        assert self_copy.wrapped is not None

        new_curve = BRep_Tool.Curve_s(
            self_copy.wrapped, self.param_at(0), self.param_at(1)
        )
        parm_start = self.param_at(start_u)
        parm_end = self.param_at(end_u)
        trimmed_curve = Geom_TrimmedCurve(
            new_curve,
            parm_start,
            parm_end,
        )
        new_edge = BRepBuilderAPI_MakeEdge(trimmed_curve).Edge()
        return Edge(new_edge)

    def trim_to_length(self, start: float | VectorLike, length: float) -> Edge:
        """trim_to_length

        Create a new edge starting at the given normalized parameter of a
        given length.

        Args:
            start (float | VectorLike): 0.0 <= start < 1.0 or point on edge
            length (float): target length

        Raise:
            ValueError: can't trim empty edge

        Returns:
            Edge: trimmed edge
        """
        if self._wrapped is None:
            raise ValueError("Can't trim empty edge")

        start_u = Mixin1D._to_param(self, start, "start")

        self_copy = copy.deepcopy(self)
        assert self_copy.wrapped is not None

        new_curve = BRep_Tool.Curve_s(
            self_copy.wrapped, self.param_at(0), self.param_at(1)
        )

        # Create an adaptor for the curve
        adaptor_curve = GeomAdaptor_Curve(new_curve)

        # Find the parameter corresponding to the desired length
        parm_start = self.param_at(start_u)
        abscissa_point = GCPnts_AbscissaPoint(adaptor_curve, length, parm_start)

        # Get the parameter at the desired length
        parm_end = abscissa_point.Parameter()

        # Trim the curve to the desired length
        trimmed_curve = Geom_TrimmedCurve(new_curve, parm_start, parm_end)

        new_edge = BRepBuilderAPI_MakeEdge(trimmed_curve).Edge()
        return Edge(new_edge)

    def trim_to_other(
        self: Edge,
        other: Shape | Axis | Location | Plane | VectorLike,
    ) -> Edge | None:
        """Return the shortest Edge of self trimmed by other or None if they don't intersect"""

        other_obj = Vector(other) if isinstance(other, Sequence) else other

        # Find all of the possible intersections: vertices and edges
        intersections = self.intersect(other_obj)

        if not intersections:
            return None

        # Get the vertices from any edges and all of the other vertices
        intersection_pnts = intersections.vertices()

        # Trim to all of the intersection points
        self_trims = ShapeList([self.trim(0, pnt) for pnt in intersection_pnts])

        # Take the closest one
        shortest_trimmed_self = self_trims.sort_by(Edge.length)[0]

        return shortest_trimmed_self

    @property
    def is_infinite(self) -> bool:
        """Check if edge is infinite (LINE with length > 1e100)."""
        return self.geom_type == GeomType.LINE and self.length > 1e100

    def trim_infinite(self, half_length: float) -> Edge:
        """Trim an infinite line edge to a finite length.

        OCCT's boolean operations struggle with very long edges (length > 1e100).
        This method trims such edges to a reasonable size centered at edge.center().

        For non-infinite edges, returns self unchanged.

        Args:
            half_length: Half-length of the resulting edge

        Returns:
            Trimmed edge if infinite, otherwise self
        """
        if not self.is_infinite:
            return self

        origin = self.center()
        direction = (self.end_point() - self.start_point()).normalized()

        return Edge.make_line(
            origin - direction * half_length,
            origin + direction * half_length,
        )


class Wire(Mixin1D[TopoDS_Wire]):
    """A Wire in build123d is a topological entity representing a connected sequence
    of edges forming a continuous curve or path in 3D space. Wires are essential
    components in modeling complex objects, defining boundaries for surfaces or
    solids. They store information about the connectivity and order of edges,
    allowing precise definition of paths within a 3D model."""

    order = 1.5
    # ---- Constructor ----

    @overload
    def __init__(
        self,
        obj: TopoDS_Wire,
        label: str = "",
        color: Color | None = None,
        parent: Compound | None = None,
    ):
        """Build a wire from an OCCT TopoDS_Wire

        Args:
            obj (TopoDS_Wire, optional): OCCT Wire.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    @overload
    def __init__(
        self,
        edge: Edge,
        label: str = "",
        color: Color | None = None,
        parent: Compound | None = None,
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
        color: Color | None = None,
        parent: Compound | None = None,
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
        color: Color | None = None,
        parent: Compound | None = None,
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
        color: Color | None = None,
        parent: Compound | None = None,
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
            if isinstance(args[0], TopoDS_Wire):
                obj, label, color, parent = args[:4] + (None,) * (4 - l_a)
            elif isinstance(args[0], Edge):
                edge, label, color, parent = args[:4] + (None,) * (4 - l_a)
            elif isinstance(args[0], Wire):
                wire, label, color, parent = args[:4] + (None,) * (4 - l_a)
            elif (
                hasattr(args[0], "wrapped")
                and isinstance(args[0].wrapped, TopoDS_Compound)
                and topods_dim(args[0].wrapped) == 1
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

    # ---- Class Methods ----

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
            if edge.wrapped is not None:
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
    def combine(
        cls, wires: Iterable[Wire | Edge], tol: float = 1e-9
    ) -> ShapeList[Wire]:
        """combine

        Combine a list of wires and edges into a list of Wires.

        Args:
            wires (Iterable[Wire |  Edge]): unsorted
            tol (float, optional): tolerance. Defaults to 1e-9.

        Returns:
            ShapeList[Wire]: Wires
        """

        edges_in = TopTools_HSequenceOfShape()
        wires_out = TopTools_HSequenceOfShape()

        for edge in [e for w in wires for e in w.edges()]:
            if edge.wrapped is not None:
                edges_in.Append(edge.wrapped)

        ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

        wires = ShapeList()
        for i in range(wires_out.Length()):
            wires.append(Wire(tcast(TopoDS_Wire, downcast(wires_out.Value(i + 1)))))

        return wires

    @classmethod
    def extrude(cls, obj: Shape, direction: VectorLike) -> Wire:
        """extrude - invalid operation for Wire"""
        raise NotImplementedError("Wires can't be created by extrusion")

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
        edges = list(edges)
        fragments_per_edge = int(2 / tolerance)
        points_lookup = {}  # lookup from point index to edge/position on edge
        points = []  # convex hull point cloud

        # Create points along each edge and the lookup structure
        for edge_index, edge in enumerate(edges):
            for i in range(fragments_per_edge):
                param = i / (fragments_per_edge - 1)
                points.append(tuple(edge.position_at(param))[:2])
                points_lookup[edge_index * fragments_per_edge + i] = (edge_index, param)

        convex_hull = ConvexHull(points)

        # Filter the fragments
        connecting_edge_data = []
        trim_points: dict[int, list[int]] = {}
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
        for edge_index, start_end_pnts in trim_points.items():
            s_points = sorted(start_end_pnts)
            f_points = []
            for i in range(0, len(s_points) - 1, 2):
                if s_points[i] != s_points[i + 1]:
                    f_points.append(tuple(s_points[i : i + 2]))
            trim_data[edge_index] = f_points

        connecting_edges = [
            Edge.make_line(
                edges[line[0][0]] @ line[0][1], edges[line[1][0]] @ line[1][1]
            )
            for line in connecting_edge_data
        ]
        trimmed_edges = [
            edges[edge_index].trim(
                points_lookup[trim_pair[0]][1], points_lookup[trim_pair[1]][1]
            )
            for edge_index, trim_pairs in trim_data.items()
            for trim_pair in trim_pairs
        ]
        hull_wire = Wire(connecting_edges + trimmed_edges, sequenced=True)
        return hull_wire

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
        vectors = [Vector(v) for v in vertices]
        if (vectors[0] - vectors[-1]).length > TOLERANCE and close:
            vectors.append(vectors[0])

        wire_builder = BRepBuilderAPI_MakePolygon()
        for vertex in vectors:
            wire_builder.Add(vertex.to_pnt())

        return cls(wire_builder.Wire())

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

    # ---- Static Methods ----
    @staticmethod
    def order_chamfer_edges(
        reference_edge: Edge | None, edges: tuple[Edge, Edge]
    ) -> tuple[Edge, Edge]:
        """Order the edges of a chamfer relative to a reference Edge"""
        if reference_edge:
            edge1, edge2 = edges
            if edge1 == reference_edge:
                return edge1, edge2
            if edge2 == reference_edge:
                return edge2, edge1
            raise ValueError("reference edge not in edges")
        return edges

    # ---- Instance Methods ----

    def chamfer_2d(
        self,
        distance: float,
        distance2: float,
        vertices: Iterable[Vertex],
        edge: Edge | None = None,
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
        if self._wrapped is None:
            raise ValueError("Can't chamfer empty wire")

        reference_edge = edge

        # Create a face to chamfer
        unchamfered_face = _make_topods_face_from_wires(self.wrapped)
        chamfer_builder = BRepFilletAPI_MakeFillet2d(unchamfered_face)

        vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            unchamfered_face, ta.TopAbs_VERTEX, ta.TopAbs_EDGE, vertex_edge_map
        )

        for v in vertices:
            if not v:
                continue
            edge_list = vertex_edge_map.FindFromKey(v.wrapped)

            # Index or iterator access to OCP.TopTools.TopTools_ListOfShape is slow on M1 macs
            # Using First() and Last() to omit
            edges = (
                Edge(tcast(TopoDS_Edge, downcast(edge_list.First()))),
                Edge(tcast(TopoDS_Edge, downcast(edge_list.Last()))),
            )

            edge1, edge2 = Wire.order_chamfer_edges(reference_edge, edges)
            if edge1.wrapped is not None and edge2.wrapped is not None:
                chamfer_builder.AddChamfer(
                    TopoDS.Edge(edge1.wrapped),
                    TopoDS.Edge(edge2.wrapped),
                    distance,
                    distance2,
                )

        chamfer_builder.Build()
        chamfered_face = chamfer_builder.Shape()
        # Fix the shape
        shape_fix = ShapeFix_Shape(chamfered_face)
        shape_fix.Perform()
        chamfered_face = downcast(shape_fix.Shape())
        if not isinstance(chamfered_face, TopoDS_Face):
            raise RuntimeError("An internal error occured creating the chamfer")
        # Return the outer wire
        return Wire(BRepTools.OuterWire_s(chamfered_face))

    def close(self) -> Wire:
        """Close a Wire"""
        if not self.is_closed:
            edge = Edge.make_line(self.end_point(), self.start_point())
            return_value = Wire.combine((self, edge))[0]
        else:
            return_value = self

        return return_value

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this Shape"""
        # The WireExplorer is a tool to explore the edges of a wire in a connection order.
        explorer = BRepTools_WireExplorer(self.wrapped)

        edge_list: ShapeList[Edge] = ShapeList()
        while explorer.More():
            next_edge = Edge(explorer.Current())
            next_edge.topo_parent = (
                self if self.topo_parent is None else self.topo_parent
            )
            edge_list.append(next_edge)
            explorer.Next()
        return edge_list

    def fillet_2d(self, radius: float, vertices: Iterable[Vertex]) -> Wire:
        """fillet_2d

        Apply 2D fillet to a wire

        Args:
            radius (float):
            vertices (Iterable[Vertex]): vertices to fillet

        Raises:
            RuntimeError: Internal error
            ValueError: empty wire

        Returns:
            Wire: filleted wire
        """
        if self._wrapped is None:
            raise ValueError("Can't fillet an empty wire")

        # Create a face to fillet
        unfilleted_face = _make_topods_face_from_wires(self.wrapped)
        # Fillet the face
        fillet_builder = BRepFilletAPI_MakeFillet2d(unfilleted_face)
        for vertex in vertices:
            if vertex.wrapped is not None:
                fillet_builder.AddFillet(vertex.wrapped, radius)
        fillet_builder.Build()
        filleted_face = downcast(fillet_builder.Shape())
        if not isinstance(filleted_face, TopoDS_Face):
            raise RuntimeError("An internal error occured creating the fillet")
        # Return the outer wire
        return Wire(BRepTools.OuterWire_s(filleted_face))

    def fix_degenerate_edges(self, precision: float) -> Wire:
        """fix_degenerate_edges

        Fix a Wire that contains degenerate (very small) edges

        Args:
            precision (float): minimum value edge length

        Returns:
            Wire: fixed wire
        """
        if self._wrapped is None:
            raise ValueError("Can't fix an empty edge")

        sf_w = ShapeFix_Wireframe(self.wrapped)
        sf_w.SetPrecision(precision)
        sf_w.SetMaxTolerance(1e-6)
        sf_w.FixSmallEdges()
        sf_w.FixWireGaps()
        return Wire(tcast(TopoDS_Wire, downcast(sf_w.Shape())))

    def geom_adaptor(self) -> BRepAdaptor_CompCurve:
        """Return the Geom Comp Curve for this Wire"""
        if self._wrapped is None:
            raise ValueError("Can't get geom adaptor of empty wire")

        return BRepAdaptor_CompCurve(self.wrapped)

    def order_edges(self) -> ShapeList[Edge]:
        """Return the edges in self ordered by wire direction and orientation"""

        sorted_edges = self.edges().sort_by(self)
        ordered_edges = ShapeList([sorted_edges[0]])

        for edge in sorted_edges[1:]:
            last_edge = ordered_edges[-1]
            if abs(last_edge @ 1 - edge @ 0) < TOLERANCE:
                ordered_edges.append(edge)
            else:
                ordered_edges.append(edge.reversed())

        return ordered_edges

    def geom_equal(
        self,
        other: Wire,
        tol: float = 1e-6,
        num_interpolation_points: int = 5,
    ) -> bool:
        """Compare two wires for geometric equality within tolerance.

        This compares the geometric properties of two wires by comparing their
        constituent edges pairwise. Two independently created wires with the
        same geometry will return True.

        Args:
            other: Wire to compare with
            tol: Tolerance for numeric comparisons. Defaults to 1e-6.
            num_interpolation_points: Number of points to sample for unknown
                curve types. Defaults to 5.

        Returns:
            bool: True if wires are geometrically equal within tolerance
        """
        if not isinstance(other, Wire):
            return False

        # Use order_edges to ensure consistent edge ordering and orientation
        edges1 = self.order_edges()
        edges2 = other.order_edges()
        if len(edges1) != len(edges2):
            return False
        return all(
            e1.geom_equal(e2, tol, num_interpolation_points)
            for e1, e2 in zip(edges1, edges2)
        )

    def param_at(self, position: float) -> float:
        """
        Return the OCCT comp-curve parameter corresponding to the given wire position.
        This is *not* the edge composite parameter; it is the parameter of the wire’s
        BRepAdaptor_CompCurve.
        """
        curve = self.geom_adaptor()

        # Compute the correct target point along the wire
        target_pnt = self.position_at(position)

        # Project to comp-curve parameter
        extrema = Extrema_ExtPC(target_pnt.to_pnt(), curve)
        if not extrema.IsDone() or extrema.NbExt() == 0:
            raise RuntimeError("Failed to find point on curve")

        min_dist = float("inf")
        closest_pnt = None
        closest_param = None
        for i in range(1, extrema.NbExt() + 1):
            dist = extrema.SquareDistance(i)
            if dist < min_dist:
                min_dist = dist
                closest_pnt = extrema.Point(i).Value()
                closest_param = extrema.Point(i).Parameter()

        if (
            closest_pnt is None
            or (Vector(tcast(gp_Pnt, closest_pnt)) - target_pnt).length > TOLERANCE
        ):
            raise RuntimeError("Failed to find point on curve")

        return tcast(float, closest_param)

    def param_at_point(self, point: VectorLike) -> float:
        """
        Return the normalized wire parameter for the point closest to this wire.

        This method projects the given point onto the wire, finds the nearest edge,
        and accumulates arc lengths to determine the fractional position along the
        entire wire. The result is normalized to the interval [0.0, 1.0], where:

        - 0.0 corresponds to the start of the wire
        - 1.0 corresponds to the end of the wire

        Unlike the edge version of this method, the returned value is **not**
        an OCCT curve parameter, but a normalized parameter across the wire as a whole.

        Args:
            point (VectorLike): The point to project onto the wire.

        Raises:
            ValueError: Can't find point on empty wire

        Returns:
            float: Normalized parameter in [0.0, 1.0] representing the relative
            position of the projected point along the wire.
        """
        if self._wrapped is None:
            raise ValueError("Can't find point on empty wire")

        point_on_curve = Vector(point)
        vertex_on_curve = Vertex(point_on_curve)
        assert vertex_on_curve.wrapped is not None

        separation = self.distance_to(point)
        if not isclose_b(separation, 0, abs_tol=TOLERANCE):
            raise ValueError(f"point ({point}) is {separation} from wire")

        extrema = BRepExtrema_DistShapeShape(vertex_on_curve.wrapped, self.wrapped)
        extrema.Perform()
        if not extrema.IsDone() or extrema.NbSolution() == 0:
            raise ValueError("point is not on Wire")

        supp_type = extrema.SupportTypeShape2(1)

        if supp_type == BRepExtrema_SupportType.BRepExtrema_IsOnEdge:
            closest_topods_edge = tcast(
                TopoDS_Edge, downcast(extrema.SupportOnShape2(1))
            )
            closest_topods_edge_param = extrema.ParOnEdgeS2(1)[0]
        elif supp_type == BRepExtrema_SupportType.BRepExtrema_IsVertex:
            v_hit = tcast(TopoDS_Vertex, downcast(extrema.SupportOnShape2(1)))
            vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
            TopExp.MapShapesAndAncestors_s(
                self.wrapped, ta.TopAbs_VERTEX, ta.TopAbs_EDGE, vertex_edge_map
            )
            closest_topods_edge = tcast(
                TopoDS_Edge, downcast(vertex_edge_map.FindFromKey(v_hit).First())
            )
            closest_topods_edge_param = BRep_Tool.Parameter_s(
                v_hit, closest_topods_edge
            )

        curve_adaptor = BRepAdaptor_Curve(closest_topods_edge)
        param_min, param_max = BRep_Tool.Range_s(closest_topods_edge)
        if curve_adaptor.IsPeriodic():
            closest_topods_edge_param = (
                (closest_topods_edge_param - param_min) % curve_adaptor.Period()
            ) + param_min
        param_pair = (
            (param_min, closest_topods_edge_param)
            if closest_topods_edge.Orientation() == TopAbs_Orientation.TopAbs_FORWARD
            else (closest_topods_edge_param, param_max)
        )
        distance_along_wire = GCPnts_AbscissaPoint.Length_s(curve_adaptor, *param_pair)

        # Find all of the edges prior to the closest edge
        wire_explorer = BRepTools_WireExplorer(self.wrapped)
        while wire_explorer.More():
            topods_edge = wire_explorer.Current()
            # Skip degenerate edges
            if BRep_Tool.Degenerated_s(topods_edge):
                wire_explorer.Next()
                continue
            # Stop when we find the closest edge
            if topods_edge.IsEqual(closest_topods_edge):
                break
            # Add the length of the current edge to the running total
            distance_along_wire += GCPnts_AbscissaPoint.Length_s(
                BRepAdaptor_Curve(topods_edge)
            )
            wire_explorer.Next()

        return distance_along_wire / self.length

    def _occt_param_at(
        self, position: float, position_mode: PositionMode = PositionMode.PARAMETER
    ) -> tuple[BRepAdaptor_Curve, float, bool]:
        """
        Map a position along this wire to the underlying OCCT edge and curve parameter.

        Unlike the edge version, this method determines which constituent edge of the
        wire contains the requested position, then returns a curve adaptor for that
        edge together with the corresponding OCCT parameter.

        The interpretation of `position` depends on `position_mode`:

        - ``PositionMode.PARAMETER``: `position` is a normalized parameter in [0, 1]
        across the entire wire.
        - ``PositionMode.DISTANCE``: `position` is an arc length distance along the wire.

        Edge and wire orientation (`is_forward`) is respected so that positions are
        measured consistently along the wire.

        Args:
            position (float): Position along the wire, either a normalized parameter
                (0-1) or a distance, depending on `position_mode`.
            position_mode (PositionMode, optional): How to interpret `position`.
                Defaults to ``PositionMode.PARAMETER``.

        Returns:
            tuple[BRepAdaptor_Curve, float]: The curve adaptor for the specific edge
            at the given position, the corresponding OCCT parameter on that edge and
            if edge is_forward.
        """
        # Normalize to absolute distance along the wire
        if position_mode == PositionMode.PARAMETER:
            if not self.is_forward:
                position = 1.0 - position
            distance = position * self.length
        else:
            if not self.is_forward:
                position = self.length - position
            distance = position

        # Build ordered edges and cumulative lengths
        self_edges = self.edges()
        edge_lengths = [e.length for e in self_edges]
        cumulative_lengths = []
        total = 0.0
        for edge_length in edge_lengths:
            total += edge_length
            cumulative_lengths.append(total)

        # Clamp distance
        if distance <= 0.0:
            edge_idx = 0
            local_dist = 0.0
        elif distance >= total:
            edge_idx = len(self_edges) - 1
            local_dist = edge_lengths[edge_idx]
        else:
            edge_idx = bisect_right(cumulative_lengths, distance)
            prev_cum = cumulative_lengths[edge_idx - 1] if edge_idx > 0 else 0.0
            local_dist = distance - prev_cum

        target_edge = self_edges[edge_idx]

        # Convert local distance to edge fraction
        local_frac = (
            0.0 if target_edge.length == 0 else (local_dist / target_edge.length)
        )
        if not target_edge.is_forward:
            local_frac = 1 - local_frac

        # Use edge param_at to get native OCCT parameter
        occt_edge_param = target_edge.param_at(local_frac)

        edge_curve_adaptor = target_edge.geom_adaptor()
        return edge_curve_adaptor, occt_edge_param, target_edge.is_forward

    def project_to_shape(
        self,
        target_object: Shape,
        direction: VectorLike | None = None,
        center: VectorLike | None = None,
    ) -> ShapeList[Wire]:
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
        if self._wrapped is None or not target_object:
            raise ValueError("Can't project empty Wires or to empty Shapes")

        if direction is not None and center is None:
            direction_vector = Vector(direction).normalized()
            center_point = Vector()  # for typing, never used
        elif center is not None and direction is None:
            direction_vector = None
            center_point = Vector(center)
        else:
            raise ValueError("Provide exactly one of direction or center")

        # Project the wire on the target object
        if direction_vector is not None:
            projection_object = BRepProj_Projection(
                self.wrapped,
                target_object.wrapped,
                gp_Dir(*direction_vector),
            )
        else:
            projection_object = BRepProj_Projection(
                self.wrapped,
                target_object.wrapped,
                gp_Pnt(*center_point),
            )

        # Generate a list of the projected wires with aligned orientation
        output_wires: ShapeList[Wire] = ShapeList()
        target_orientation = self.wrapped.Orientation()
        while projection_object.More():
            projected_wire = projection_object.Current()
            if target_orientation == projected_wire.Orientation():
                output_wires.append(Wire(projected_wire))
            else:
                output_wires.append(
                    Wire(tcast(TopoDS_Wire, downcast(projected_wire.Reversed())))
                )
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
            output_wires = ShapeList([w[0] for w in output_wires_distances])

        # Clean the wires remove cases where projection artificially split edges
        cleaned_wires = ShapeList([w.clean() for w in output_wires])

        return cleaned_wires

    def stitch(self, other: Wire) -> Wire:
        """Attempt to stitch wires

        Args:
            other (Wire): wire to combine

        Raises:
            ValueError: Can't stitch empty wires

        Returns:
            Wire: stitched wires
        """
        if self._wrapped is None or not other:
            raise ValueError("Can't stitch empty wires")

        wire_builder = BRepBuilderAPI_MakeWire()
        wire_builder.Add(TopoDS.Wire(self.wrapped))
        wire_builder.Add(TopoDS.Wire(other.wrapped))
        wire_builder.Build()

        return self.__class__.cast(wire_builder.Wire())

    def _to_bspline(self) -> Edge:
        """
        Collapse this wire into a single BSpline edge (internal use).

        Concatenates the wire's constituent edges—**in topological order**—into one
        `Geom_BSplineCurve` using OCP/OCCT's `GeomConvert_CompCurveToBSplineCurve`.
        Degenerate edges are skipped. The resulting topology is a **single Edge**;
        former junctions between original edges become **internal spline knots**
        (C0 corners) but **not vertices**.

        ⚠️ Not intended for general user workflows. The loss of vertex boundaries
        can make downstream operations (e.g., splitting at vertices, continuity checks,
        feature recognition) surprising. This is primarily useful for internal tasks
        that benefit from a single-curve representation (e.g., length/abscissa queries
        or parameter mapping along the entire wire).

        Behavior & caveats:
        - Orientation and section order follow the wire's topological sequence.
        - Junctions with only C0 continuity are preserved as spline knots, not as
            topological vertices.
        - The returned edge's parameterization is that of the composite BSpline
            (not a normalized [0,1] wire parameter).
        - Failure to append any segment or to build the final edge raises an error.

        Raises:
            RuntimeError: If any segment cannot be appended to the composite spline
                or the final BSpline edge cannot be built.
            ValueError: Empty Wire

        Returns:
            Edge: A single edge whose geometry is `GeomType.BSPLINE`.
        """
        # Build a single Geom_BSplineCurve from the wire, in *topological order*
        builder = GeomConvert_CompCurveToBSplineCurve()
        if self._wrapped is None:
            raise ValueError("Can't convert an empty wire")
        wire_explorer = BRepTools_WireExplorer(self.wrapped)

        while wire_explorer.More():
            topods_edge = wire_explorer.Current()
            # Skip degenerate edges
            if BRep_Tool.Degenerated_s(topods_edge):
                wire_explorer.Next()
                continue
            param_min, param_max = BRep_Tool.Range_s(topods_edge)
            new_curve = BRep_Tool.Curve_s(topods_edge, float(), float())
            trimmed_curve = Geom_TrimmedCurve(new_curve, param_min, param_max)

            # Append this edge's trimmed curve into the composite spline.
            ok = builder.Add(trimmed_curve, TOLERANCE)
            if not ok:
                raise RuntimeError("Failed to build bspline.")
            wire_explorer.Next()

        edge_builder = BRepBuilderAPI_MakeEdge(builder.BSplineCurve())
        if not edge_builder.IsDone():
            raise RuntimeError("Failed to build bspline.")

        return Edge(edge_builder.Edge())

    def to_wire(self) -> Wire:
        """Return Wire - used as a pair with Edge.to_wire when self is Wire | Edge"""
        warnings.warn(
            "to_wire is deprecated and will be removed in a future version. "
            "Use 'Wire(Wire)' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self

    def trim(self: Wire, start: float | VectorLike, end: float | VectorLike) -> Wire:
        """Trim a wire between [start, end] normalized over total length.

        Args:
            start (float | VectorLike): normalized start position (0.0 to <1.0) or point
            end (float | VectorLike): normalized end position (>0.0 to 1.0) or point

        Returns:
            Wire: trimmed Wire
        """
        start_u = Mixin1D._to_param(self, start, "start")
        end_u = Mixin1D._to_param(self, end, "end")

        start_u, end_u = sorted([start_u, end_u])

        # Extract the edges in order
        ordered_edges = self.edges().sort_by(self)

        # If this is really just an edge, skip the complexity of a Wire
        if len(ordered_edges) == 1:
            return Wire([ordered_edges[0].trim(start_u, end_u)])

        total_length = self.length
        start_len = start_u * total_length
        end_len = end_u * total_length

        trimmed_edges = []
        cur_length = 0.0

        for edge in ordered_edges:
            edge_len = edge.length
            edge_start = cur_length
            edge_end = cur_length + edge_len
            cur_length = edge_end

            if edge_end <= start_len or edge_start >= end_len:
                continue  # skip

            if edge_start >= start_len and edge_end <= end_len:
                trimmed_edges.append(edge)  # keep whole Edge
            else:
                # Normalize trim points relative to this edge
                trim_start_len = max(start_len, edge_start)
                trim_end_len = min(end_len, edge_end)

                u0 = (trim_start_len - edge_start) / edge_len
                u1 = (trim_end_len - edge_start) / edge_len

                if abs(u1 - u0) > TOLERANCE:
                    trimmed_edges.append(edge.trim(u0, u1))

        return Wire(trimmed_edges)


def edges_to_wires(edges: Iterable[Edge], tol: float = 1e-6) -> ShapeList[Wire]:
    """Convert edges to a list of wires.

    Args:
      edges: Iterable[Edge]:
      tol: float:  (Default value = 1e-6)

    Returns:

    """

    edges_in = TopTools_HSequenceOfShape()
    wires_out = TopTools_HSequenceOfShape()

    for edge in edges:
        if edge.wrapped is not None:
            edges_in.Append(edge.wrapped)
    ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

    wires: ShapeList[Wire] = ShapeList()
    for i in range(wires_out.Length()):
        # wires.append(Wire(downcast(wires_out.Value(i + 1))))
        wires.append(Wire(TopoDS.Wire(wires_out.Value(i + 1))))

    return wires


def offset_topods_face(face: TopoDS_Face, amount: float) -> TopoDS_Shape:
    """Offset a topods_face"""
    offsetor = BRepOffset_MakeOffset()
    offsetor.Initialize(face, Offset=amount, Tol=TOLERANCE)
    offsetor.MakeOffsetShape()

    return offsetor.Shape()


def topo_explore_connected_edges(
    edge: Edge,
    parent: Shape | None = None,
    continuity: ContinuityLevel = ContinuityLevel.C0,
) -> ShapeList[Edge]:
    """
    Find edges connected to the given edge with at least the requested continuity.

    Args:
        edge: The reference edge to explore from.
        parent: Optional parent Shape. If None, uses edge.topo_parent.
        continuity: Minimum required continuity (C0/G0, C1/G1, C2/G2).

    Returns:
        ShapeList[Edge]: Connected edges meeting the continuity requirement.
    """
    continuity_map = {
        GeomAbs_C0: ContinuityLevel.C0,
        GeomAbs_G1: ContinuityLevel.C1,
        GeomAbs_C1: ContinuityLevel.C1,
        GeomAbs_G2: ContinuityLevel.C2,
        GeomAbs_C2: ContinuityLevel.C2,
    }
    parent = parent if parent is not None else edge.topo_parent
    if parent is None:
        raise ValueError("edge has no valid parent")
    if not edge:
        raise ValueError("edge is empty")
    given_topods_edge = edge.wrapped
    connected_edges = set()

    # Find all the TopoDS_Edges for this Shape
    topods_edges = [e.wrapped for e in parent.edges() if e.wrapped is not None]

    for topods_edge in topods_edges:
        # # Don't match with the given edge
        if given_topods_edge.IsSame(topods_edge):
            continue
        # If the edge shares a vertex with the given edge they are connected
        common_topods_vertex: Vertex | None = topo_explore_common_vertex(
            given_topods_edge, topods_edge
        )
        if (
            common_topods_vertex is not None
            and common_topods_vertex.wrapped is not None
        ):
            # shared_vertex is the TopoDS_Vertex common to edge1 and edge2
            u1 = BRep_Tool.Parameter_s(common_topods_vertex.wrapped, given_topods_edge)
            u2 = BRep_Tool.Parameter_s(common_topods_vertex.wrapped, topods_edge)

            # Build adaptors so OCCT can work on the curves
            curve1 = BRepAdaptor_Curve(given_topods_edge)
            curve2 = BRepAdaptor_Curve(topods_edge)

            # Get the GeomAbs_Shape enum continuity at the vertex
            actual_continuity = BRepLProp.Continuity_s(
                curve1, curve2, u1, u2, TOLERANCE, TOLERANCE
            )
            actual_level = continuity_map.get(actual_continuity, ContinuityLevel.C2)

            if actual_level >= continuity:
                connected_edges.add(topods_edge)

    return ShapeList(Edge(e) for e in connected_edges)


def topo_explore_connected_faces(
    edge: Edge, parent: Shape | None = None
) -> list[TopoDS_Face]:
    """Given an edge extracted from a Shape, return the topods_faces connected to it"""

    if not edge:
        raise ValueError("Can't explore from an empty edge")

    parent = parent if parent is not None else edge.topo_parent
    if not parent:
        raise ValueError("edge has no valid parent")

    # make a edge --> faces mapping
    edge_face_map = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(
        parent.wrapped, ta.TopAbs_EDGE, ta.TopAbs_FACE, edge_face_map
    )

    # Query the map and select only unique faces
    unique_face_map = TopTools_IndexedMapOfShape()
    unique_faces = []
    if edge_face_map.Contains(edge.wrapped):
        for face in edge_face_map.FindFromKey(edge.wrapped):
            unique_face_map.Add(face)
    for i in range(unique_face_map.Extent()):
        unique_faces.append(TopoDS.Face(unique_face_map(i + 1)))

    return unique_faces
