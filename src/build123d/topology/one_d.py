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
import itertools
import warnings
from collections.abc import Iterable
from itertools import combinations
from math import radians, inf, pi, cos, copysign, ceil, floor
from typing import Literal, overload, TYPE_CHECKING
from typing_extensions import Self
from numpy import ndarray
from scipy.optimize import minimize
from scipy.spatial import ConvexHull

import OCP.TopAbs as ta
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Splitter
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_DisconnectedWire,
    BRepBuilderAPI_EmptyWire,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_NonManifoldWire,
)
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet2d
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepLib import BRepLib, BRepLib_FindSurface
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCP.BRepProj import BRepProj_Projection
from OCP.BRepTools import BRepTools
from OCP.GC import GC_MakeArcOfCircle, GC_MakeArcOfEllipse
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.GProp import GProp_GProps
from OCP.Geom import (
    Geom_BezierCurve,
    Geom_ConicalSurface,
    Geom_CylindricalSurface,
    Geom_Plane,
    Geom_Surface,
    Geom_TrimmedCurve,
    Geom_Line,
)
from OCP.Geom2d import Geom2d_Curve, Geom2d_Line, Geom2d_TrimmedCurve
from OCP.Geom2dAPI import Geom2dAPI_InterCurveCurve
from OCP.GeomAPI import (
    GeomAPI_IntCS,
    GeomAPI_Interpolate,
    GeomAPI_PointsToBSpline,
    GeomAPI_ProjectPointOnCurve,
)
from OCP.GeomAbs import GeomAbs_JoinType
from OCP.GeomAdaptor import GeomAdaptor_Curve
from OCP.GeomFill import (
    GeomFill_CorrectedFrenet,
    GeomFill_Frenet,
    GeomFill_TrihedronLaw,
)
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_Wireframe
from OCP.Standard import Standard_Failure, Standard_NoSuchObject
from OCP.TColStd import (
    TColStd_Array1OfReal,
    TColStd_HArray1OfBoolean,
    TColStd_HArray1OfReal,
)
from OCP.TColgp import TColgp_Array1OfPnt, TColgp_Array1OfVec, TColgp_HArray1OfPnt
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import (
    TopTools_HSequenceOfShape,
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_ListOfShape,
)
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Compound,
    TopoDS_Edge,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Wire,
)
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
from build123d.build_enums import (
    AngularDirection,
    CenterOf,
    FrameMethod,
    GeomType,
    Keep,
    Kind,
    PositionMode,
    Side,
)
from build123d.geometry import (
    DEG2RAD,
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
    Shape,
    ShapeList,
    SkipClean,
    TrimmingTool,
    downcast,
    get_top_level_topods_shapes,
    shapetype,
    topods_dim,
    unwrap_topods_compound,
    _topods_entities,
)
from .utils import (
    _extrude_topods_shape,
    isclose_b,
    _make_topods_face_from_wires,
    _topods_bool_op,
)
from .zero_d import topo_explore_common_vertex, Vertex


if TYPE_CHECKING:  # pragma: no cover
    from .two_d import Face, Shell  # pylint: disable=R0801
    from .three_d import Solid  # pylint: disable=R0801
    from .composite import Compound, Curve, Sketch, Part  # pylint: disable=R0801


class Mixin1D(Shape):
    """Methods to add to the Edge and Wire classes"""

    # ---- Properties ----

    @property
    def _dim(self) -> int:
        """Dimension of Edges and Wires"""
        return 1

    @property
    def is_closed(self) -> bool:
        """Are the start and end points equal?"""
        if self.wrapped is None:
            raise ValueError("Can't determine if empty Edge or Wire is closed")
        return BRep_Tool.IsClosed_s(self.wrapped)

    @property
    def is_forward(self) -> bool:
        """Does the Edge/Wire loop forward or reverse"""
        if self.wrapped is None:
            raise ValueError("Can't determine direction of empty Edge or Wire")
        return self.wrapped.Orientation() == TopAbs_Orientation.TopAbs_FORWARD

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

    # ---- Instance Methods ----

    def __add__(
        self, other: None | Shape | Iterable[Shape]
    ) -> Edge | Wire | ShapeList[Edge]:
        """fuse shape to wire/edge operator +"""

        # Convert `other` to list of base topods objects and filter out None values
        if other is None:
            summands = []
        else:
            summands = [
                shape
                # for o in (other if isinstance(other, (list, tuple)) else [other])
                for o in ([other] if isinstance(other, Shape) else other)
                if o is not None
                for shape in get_top_level_topods_shapes(o.wrapped)
            ]
        # If there is nothing to add return the original object
        if not summands:
            return self

        if not all(topods_dim(summand) == 1 for summand in summands):
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
                sum_shape = Wire(self.edges() + ShapeList(summand_edges))
            except Exception:
                sum_shape = self.fuse(*summands)

        if SkipClean.clean and not isinstance(sum_shape, list):
            sum_shape = sum_shape.clean()

        # If there is only one Edge, return that
        sum_shape = sum_shape.edge() if len(sum_shape.edges()) == 1 else sum_shape

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
        if center_of == CenterOf.GEOMETRY:
            middle = self.position_at(0.5)
        elif center_of == CenterOf.MASS:
            properties = GProp_GProps()
            BRepGProp.LinearProperties_s(self.wrapped, properties)
            middle = Vector(properties.CentreOfMass())
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    def common_plane(self, *lines: Edge | Wire | None) -> None | Plane:
        """common_plane

        Find the plane containing all the edges/wires (including self). If there
        is no common plane return None. If the edges are coaxial, select one
        of the infinite number of valid planes.

        Args:
            lines (sequence of Edge | Wire): edges in common with self

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
                z_dir = as_axis[0].to_plane().x_dir
                c_plane = Plane(origin, z_dir=z_dir)
                result = c_plane.shift_origin((0, 0))

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
                c_plane = c_plane.shift_origin((0, 0))
            except ValueError:
                # There is no valid common plane
                result = None
            else:
                # Are all of the points on the common plane
                common = all(c_plane.contains(p) for p in points)
                result = c_plane if common else None

        return result

    def edge(self) -> Edge | None:
        """Return the Edge"""
        return Shape.get_single_shape(self, "Edge")

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this Shape"""
        edge_list = Shape.get_shape_list(self, "Edge")
        return edge_list.filter_by(
            lambda e: BRep_Tool.Degenerated_s(e.wrapped), reverse=True
        )

    def end_point(self) -> Vector:
        """The end point of this edge.

        Note that circles may have identical start and end points.
        """
        curve = self.geom_adaptor()
        umax = curve.LastParameter()

        return Vector(curve.Value(umax))

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
            edges_to_keep: list[list[int]] = [[], [], []]
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
                offset_wire = Wire(
                    line.edges() + offset_wire.edges() + ShapeList([edge0, edge1])
                )

        offset_edges = offset_wire.edges()
        return offset_edges[0] if len(offset_edges) == 1 else offset_wire

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
        if self.wrapped is None:
            raise ValueError("Can't project an empty Edge or Wire")

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

        def extract_edges(compound) -> list[TopoDS_Edge]:
            return [downcast(i) for i in _topods_entities(compound, "Edge")]

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

    @overload
    def split(
        self, tool: TrimmingTool, keep: Literal[Keep.TOP, Keep.BOTTOM]
    ) -> Self | list[Self] | None:
        """split and keep inside or outside"""

    @overload
    def split(self, tool: TrimmingTool, keep: Literal[Keep.ALL]) -> list[Self]:
        """split and return the unordered pieces"""

    @overload
    def split(self, tool: TrimmingTool, keep: Literal[Keep.BOTH]) -> tuple[
        Self | list[Self] | None,
        Self | list[Self] | None,
    ]:
        """split and keep inside and outside"""

    @overload
    def split(self, tool: TrimmingTool) -> Self | list[Self] | None:
        """split and keep inside (default)"""

    def split(self, tool: TrimmingTool, keep: Keep = Keep.TOP):
        """split

        Split this shape by the provided plane or face.

        Args:
            surface (Plane | Face): surface to segment shape
            keep (Keep, optional): which object(s) to save. Defaults to Keep.TOP.

        Returns:
            Shape: result of split
        Returns:
            Self | list[Self] | None,
            Tuple[Self | list[Self] | None]: The result of the split operation.

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

        # For speed the user may just want all the objects which they
        # can sort more efficiently then the generic algoritm below
        if keep == Keep.ALL:
            return ShapeList(
                self.__class__.cast(part)
                for part in get_top_level_topods_shapes(split_result)
            )

        if not isinstance(tool, Plane):
            # Get a TopoDS_Face to work with from the tool
            if isinstance(trim_tool, TopoDS_Shell):
                faceExplorer = TopExp_Explorer(trim_tool, ta.TopAbs_FACE)
                tool_face = TopoDS.Face_s(faceExplorer.Current())
            else:
                tool_face = trim_tool

            # Create a reference point off the +ve side of the tool
            surface_point = gp_Pnt()
            surface_normal = gp_Vec()
            u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(tool_face)
            BRepGProp_Face(tool_face).Normal(
                (u_min + u_max) / 2, (v_min + v_max) / 2, surface_point, surface_normal
            )
            normalized_surface_normal = Vector(
                surface_normal.X(), surface_normal.Y(), surface_normal.Z()
            ).normalized()
            surface_point = Vector(surface_point)
            ref_point = surface_point + normalized_surface_normal

            # Create a HalfSpace - Solidish object to determine top/bottom
            halfSpaceMaker = BRepPrimAPI_MakeHalfSpace(trim_tool, ref_point.to_pnt())
            tool_solid = halfSpaceMaker.Solid()

        tops: list[Shape] = []
        bottoms: list[Shape] = []
        properties = GProp_GProps()
        for part in get_top_level_topods_shapes(split_result):
            sub_shape = self.__class__.cast(part)
            if isinstance(tool, Plane):
                is_up = tool.to_local_coords(sub_shape).center().Z >= 0
            else:
                # Intersect self and the thickened tool
                is_up_obj = _topods_bool_op(
                    (part,), (tool_solid,), BRepAlgoAPI_Common()
                )
                # Check for valid intersections
                BRepGProp.LinearProperties_s(is_up_obj, properties)
                # Mass represents the total length for linear properties
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

    def start_point(self) -> Vector:
        """The start point of this edge

        Note that circles may have identical start and end points.
        """
        curve = self.geom_adaptor()
        umin = curve.FirstParameter()

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

    def vertex(self) -> Vertex | None:
        """Return the Vertex"""
        return Shape.get_single_shape(self, "Vertex")

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this Shape"""
        return Shape.get_shape_list(self, "Vertex")

    def wire(self) -> Wire | None:
        """Return the Wire"""
        return Shape.get_single_shape(self, "Wire")

    def wires(self) -> ShapeList[Wire]:
        """wires - all the wires in this Shape"""
        return Shape.get_shape_list(self, "Wire")


class Edge(Mixin1D, Shape[TopoDS_Edge]):
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
        return Edge(TopoDS.Edge_s(_extrude_topods_shape(obj.wrapped, direction)))

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

    def find_intersection_points(
        self, other: Axis | Edge | None = None, tolerance: float = TOLERANCE
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
        return BRepAdaptor_Curve(self.wrapped)

    def intersect(
        self, *to_intersect: Edge | Axis | Plane
    ) -> None | Vertex | Edge | ShapeList[Vertex | Edge]:
        """intersect Edge with Edge or Axis

        Args:
            other (Edge |  Axis): other object

        Returns:
            Shape |  None: Compound of vertices and/or edges
        """
        edges: list[Edge] = []
        planes: list[Plane] = []
        edges_common_to_planes: list[Edge] = []

        for obj in to_intersect:
            match obj:
                case Axis():
                    edges.append(Edge(obj))
                case Edge():
                    edges.append(obj)
                case Plane():
                    planes.append(obj)
                case _:
                    raise ValueError(f"Unknown object type: {type(obj)}")

        # Find any edge / edge intersection points
        points_sets: list[set[Vector]] = []
        # Find crossing points
        for edge_pair in combinations([self] + edges, 2):
            intersection_points = edge_pair[0].find_intersection_points(edge_pair[1])
            points_sets.append(set(intersection_points))

        # Find common end points
        self_end_points = set(Vector(v) for v in self.vertices())
        edge_end_points = set(Vector(v) for edge in edges for v in edge.vertices())
        common_end_points = set.intersection(self_end_points, edge_end_points)

        # Find any edge / plane intersection points & edges
        for edge, plane in itertools.product([self] + edges, planes):
            # Find point intersections
            geom_line = BRep_Tool.Curve_s(
                edge.wrapped, edge.param_at(0), edge.param_at(1)
            )
            geom_plane = Geom_Plane(plane.local_coord_system)
            intersection_calculator = GeomAPI_IntCS(geom_line, geom_plane)
            plane_intersection_points: list[Vector] = []
            if intersection_calculator.IsDone():
                plane_intersection_points = [
                    Vector(intersection_calculator.Point(i + 1))
                    for i in range(intersection_calculator.NbPoints())
                ]
            points_sets.append(set(plane_intersection_points))

            # Find edge intersections
            if all(
                plane.contains(v) for v in edge.positions(i / 7 for i in range(8))
            ):  # is a 2D edge
                edges_common_to_planes.append(edge)

        edges.extend(edges_common_to_planes)

        # Find the intersection of all sets
        common_points = set.intersection(*points_sets)
        common_vertices = [
            Vertex(pnt) for pnt in common_points.union(common_end_points)
        ]

        # Find Edge/Edge overlaps
        common_edges: list[Edge] = []
        if edges:
            common_edges = self._bool_op((self,), edges, BRepAlgoAPI_Common()).edges()

        if common_vertices or common_edges:
            # If there is just one vertex or edge return it
            if len(common_vertices) == 1 and len(common_edges) == 0:
                return common_vertices[0]
            if len(common_vertices) == 0 and len(common_edges) == 1:
                return common_edges[0]
            return ShapeList(common_vertices + common_edges)
        return None

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

    def project_to_shape(
        self,
        target_object: Shape,
        direction: VectorLike | None = None,
        center: VectorLike | None = None,
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

    def to_axis(self) -> Axis:
        """Translate a linear Edge to an Axis"""
        if self.geom_type != GeomType.LINE:
            raise ValueError(
                f"to_axis is only valid for linear Edges not {self.geom_type}"
            )
        return Axis(self.position_at(0), self.position_at(1) - self.position_at(0))

    def to_wire(self) -> Wire:
        """Edge as Wire"""
        return Wire([self])

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


class Wire(Mixin1D, Shape[TopoDS_Wire]):
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
            # elif isinstance(args[0], Curve):
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
            edges_in.Append(edge.wrapped)

        ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(edges_in, tol, False, wires_out)

        wires = ShapeList()
        for i in range(wires_out.Length()):
            wires.append(Wire(downcast(wires_out.Value(i + 1))))

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
                points.append(edge.position_at(param).to_tuple()[:2])
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
        reference_edge = edge

        # Create a face to chamfer
        unchamfered_face = _make_topods_face_from_wires(self.wrapped)
        chamfer_builder = BRepFilletAPI_MakeFillet2d(unchamfered_face)

        vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            unchamfered_face, ta.TopAbs_VERTEX, ta.TopAbs_EDGE, vertex_edge_map
        )

        for v in vertices:
            edge_list = vertex_edge_map.FindFromKey(v.wrapped)

            # Index or iterator access to OCP.TopTools.TopTools_ListOfShape is slow on M1 macs
            # Using First() and Last() to omit
            edges = (Edge(edge_list.First()), Edge(edge_list.Last()))

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

    def close(self) -> Wire:
        """Close a Wire"""
        if not self.is_closed:
            edge = Edge.make_line(self.end_point(), self.start_point())
            return_value = Wire.combine((self, edge))[0]
        else:
            return_value = self

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

    def geom_adaptor(self) -> BRepAdaptor_CompCurve:
        """Return the Geom Comp Curve for this Wire"""
        return BRepAdaptor_CompCurve(self.wrapped)

    def order_edges(self) -> ShapeList[Edge]:
        """Return the edges in self ordered by wire direction and orientation"""
        ordered_edges = [
            e if e.is_forward else e.reversed() for e in self.edges().sort_by(self)
        ]
        return ShapeList(ordered_edges)

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

    def project_to_shape(
        self,
        target_object: Shape,
        direction: VectorLike | None = None,
        center: VectorLike | None = None,
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
        if self.wrapped is None or target_object.wrapped is None:
            raise ValueError("Can't project empty Wires or to empty Shapes")

        if not (direction is None) ^ (center is None):
            raise ValueError("One of either direction or center must be provided")
        if direction is not None:
            direction_vector = Vector(direction).normalized()
            center_point = Vector()  # for typing, never used
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

        return self.__class__.cast(wire_builder.Wire())

    def to_wire(self) -> Wire:
        """Return Wire - used as a pair with Edge.to_wire when self is Wire | Edge"""
        return self

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

        trimmed_edges = []
        for u, v, edge in edges_uv_values:
            if v < start or u > end:  # Edge not needed
                continue

            if start <= u and v <= end:  # keep whole Edge
                trimmed_edges.append(edge)

            elif start >= u and end <= v:  # Wire trimmed to single Edge
                u_edge = edge.param_at_point(self.position_at(start))
                v_edge = edge.param_at_point(self.position_at(end))
                u_edge, v_edge = (
                    (v_edge, u_edge) if u_edge > v_edge else (u_edge, v_edge)
                )
                trimmed_edges.append(edge.trim(u_edge, v_edge))

            elif start <= u:  # keep start of Edge
                u_edge = edge.param_at_point(self.position_at(end))
                if u_edge != 0:
                    trimmed_edges.append(edge.trim(0, u_edge))

            else:  #  v <= end  keep end of Edge
                v_edge = edge.param_at_point(self.position_at(start))
                if v_edge != 1:
                    trimmed_edges.append(edge.trim(v_edge, 1))

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
        wires.append(Wire(TopoDS.Wire_s(wires_out.Value(i + 1))))

    return wires


def topo_explore_connected_edges(
    edge: Edge, parent: Shape | None = None
) -> ShapeList[Edge]:
    """Given an edge extracted from a Shape, return the edges connected to it"""

    parent = parent if parent is not None else edge.topo_parent
    if parent is None:
        raise ValueError("edge has no valid parent")
    given_topods_edge = edge.wrapped
    if given_topods_edge is None:
        raise ValueError("edge is empty")
    connected_edges = set()

    # Find all the TopoDS_Edges for this Shape
    topods_edges = [e.wrapped for e in parent.edges() if e.wrapped is not None]

    for topods_edge in topods_edges:
        # # Don't match with the given edge
        if given_topods_edge.IsSame(topods_edge):
            continue
        # If the edge shares a vertex with the given edge they are connected
        if topo_explore_common_vertex(given_topods_edge, topods_edge) is not None:
            connected_edges.add(topods_edge)

    return ShapeList(Edge(e) for e in connected_edges)
