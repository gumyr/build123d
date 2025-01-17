"""
build123d topology

name: two_d.py
by:   Gumyr
date: January 07, 2025

desc:

This module provides classes and methods for two-dimensional geometric entities in the build123d CAD
library, focusing on the `Face` and `Shell` classes. These entities form the building blocks for
creating and manipulating complex 2D surfaces and 3D shells, enabling precise modeling for CAD
applications.

Key Features:
- **Mixin2D**:
  - Adds shared functionality to `Face` and `Shell` classes, such as splitting, extrusion, and
    projection operations.

- **Face Class**:
  - Represents a 3D bounded surface with advanced features like trimming, offsetting, and Boolean
    operations.
  - Provides utilities for creating faces from wires, arrays of points, Bézier surfaces, and ruled
    surfaces.
  - Enables geometry queries like normal vectors, surface centers, and planarity checks.

- **Shell Class**:
  - Represents a collection of connected faces forming a closed surface.
  - Supports operations like lofting and sweeping profiles along paths.

- **Utilities**:
  - Includes methods for sorting wires into buildable faces and creating holes within faces
    efficiently.

The module integrates deeply with OpenCascade to leverage its powerful CAD kernel, offering robust
and extensible tools for surface and shell creation, manipulation, and analysis.

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
from typing import Any, Tuple, Union, overload, TYPE_CHECKING

from collections.abc import Iterable, Sequence

import OCP.TopAbs as ta
from OCP.BRep import BRep_Tool, BRep_Builder
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgo import BRepAlgo
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeShell
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepFill import BRepFill
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet2d
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeFilling, BRepOffsetAPI_MakePipeShell
from OCP.BRepTools import BRepTools
from OCP.GProp import GProp_GProps
from OCP.Geom import Geom_BezierSurface, Geom_Surface
from OCP.GeomAPI import GeomAPI_PointsToBSplineSurface, GeomAPI_ProjectPointOnSurf
from OCP.GeomAbs import GeomAbs_C0
from OCP.Precision import Precision
from OCP.ShapeFix import ShapeFix_Solid
from OCP.Standard import (
    Standard_Failure,
    Standard_NoSuchObject,
    Standard_ConstructionError,
)
from OCP.StdFail import StdFail_NotDone
from OCP.TColStd import TColStd_HArray2OfReal
from OCP.TColgp import TColgp_HArray2OfPnt
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Shape, TopoDS_Shell, TopoDS_Solid
from OCP.gce import gce_MakeLin
from OCP.gp import gp_Pnt, gp_Vec
from build123d.build_enums import CenterOf, GeomType, SortBy, Transition
from build123d.geometry import (
    TOLERANCE,
    Axis,
    Color,
    Location,
    Plane,
    Vector,
    VectorLike,
)
from typing_extensions import Self

from .one_d import Mixin1D, Edge, Wire
from .shape_core import (
    Shape,
    ShapeList,
    SkipClean,
    downcast,
    get_top_level_topods_shapes,
    _sew_topods_faces,
    shapetype,
    _topods_entities,
    _topods_face_normal_at,
)
from .utils import (
    _extrude_topods_shape,
    find_max_dimension,
    _make_loft,
    _make_topods_face_from_wires,
    _topods_bool_op,
)
from .zero_d import Vertex


if TYPE_CHECKING:  # pragma: no cover
    from .three_d import Solid  # pylint: disable=R0801
    from .composite import Compound, Curve, Sketch, Part  # pylint: disable=R0801


class Mixin2D(Shape):
    """Additional methods to add to Face and Shell class"""

    project_to_viewport = Mixin1D.project_to_viewport
    split = Mixin1D.split

    vertices = Mixin1D.vertices
    vertex = Mixin1D.vertex
    edges = Mixin1D.edges
    edge = Mixin1D.edge
    wires = Mixin1D.wires
    # ---- Properties ----

    @property
    def _dim(self) -> int:
        """Dimension of Faces and Shells"""
        return 2

    # ---- Class Methods ----

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Vertex | Edge | Wire | Face | Shell:
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

    @classmethod
    def extrude(
        cls, obj: Shape, direction: VectorLike
    ) -> Edge | Face | Shell | Solid | Compound:
        """Unused - only here because Mixin1D is a subclass of Shape"""
        return NotImplemented

    # ---- Instance Methods ----

    def __neg__(self) -> Self:
        """Reverse normal operator -"""
        if self.wrapped is None:
            raise ValueError("Invalid Shape")
        new_surface = copy.deepcopy(self)
        new_surface.wrapped = downcast(self.wrapped.Complemented())

        return new_surface

    def face(self) -> Face | None:
        """Return the Face"""
        return Shape.get_single_shape(self, "Face")

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this Shape"""
        return Shape.get_shape_list(self, "Face")

    def find_intersection_points(
        self, other: Axis, tolerance: float = TOLERANCE
    ) -> list[tuple[Vector, Vector]]:
        """Find point and normal at intersection

        Return both the point(s) and normal(s) of the intersection of the axis and the shape

        Args:
            axis (Axis): axis defining the intersection line

        Returns:
            list[tuple[Vector, Vector]]: Point and normal of intersection
        """
        if self.wrapped is None:
            return []

        intersection_line = gce_MakeLin(other.wrapped).Value()
        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(self.wrapped, intersection_line, tolerance)

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
            _topods_face_normal_at(f, intersecting_points[i].to_pnt())
            for i, f in enumerate(intersecting_faces)
        ]
        result = []
        for pnt, normal in zip(intersecting_points, intersecting_normals):
            result.append((pnt, normal))

        return result

    def offset(self, amount: float) -> Self:
        """Return a copy of self moved along the normal by amount"""
        return copy.deepcopy(self).moved(Location(self.normal_at() * amount))

    def shell(self) -> Shell | None:
        """Return the Shell"""
        return Shape.get_single_shape(self, "Shell")

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this Shape"""
        return Shape.get_shape_list(self, "Shell")


class Face(Mixin2D, Shape[TopoDS_Face]):
    """A Face in build123d represents a 3D bounded surface within the topological data
    structure. It encapsulates geometric information, defining a face of a 3D shape.
    These faces are integral components of complex structures, such as solids and
    shells. Face enables precise modeling and manipulation of surfaces, supporting
    operations like trimming, filleting, and Boolean operations."""

    # pylint: disable=too-many-public-methods

    order = 2.0
    # ---- Constructor ----

    @overload
    def __init__(
        self,
        obj: TopoDS_Face,
        label: str = "",
        color: Color | None = None,
        parent: Compound | None = None,
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
        inner_wires: Iterable[Wire] | None = None,
        label: str = "",
        color: Color | None = None,
        parent: Compound | None = None,
    ):
        """Build a planar Face from a boundary Wire with optional hole Wires.

        Args:
            outer_wire (Wire): closed perimeter wire
            inner_wires (Iterable[Wire], optional): holes. Defaults to None.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """

    def __init__(self, *args: Any, **kwargs: Any):
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
        self.created_on: Plane | None = None

    # ---- Properties ----

    @property
    def center_location(self) -> Location:
        """Location at the center of face"""
        origin = self.position_at(0.5, 0.5)
        return Plane(origin, z_dir=self.normal_at(origin)).location

    @property
    def geometry(self) -> None | str:
        """geometry of planar face"""
        result = None
        if self.is_planar:
            flat_face: Face = Plane(self).to_local_coords(self)
            flat_face_edges = flat_face.edges()
            if all(e.geom_type == GeomType.LINE for e in flat_face_edges):
                flat_face_vertices = flat_face.vertices()
                result = "POLYGON"
                if len(flat_face_edges) == 4:
                    edge_pairs: list[list[Edge]] = []
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
    def is_planar(self) -> bool:
        """Is the face planar even though its geom_type may not be PLANE"""
        return self.is_planar_face

    @property
    def length(self) -> None | float:
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
    def width(self) -> None | float:
        """width of planar face"""
        result = None
        if self.is_planar:
            # Reposition on Plane.XY
            flat_face = Plane(self).to_local_coords(self)
            face_vertices = flat_face.vertices().sort_by(Axis.Y)
            result = face_vertices[-1].Y - face_vertices[0].Y
        return result

    # ---- Class Methods ----

    @classmethod
    def extrude(cls, obj: Edge, direction: VectorLike) -> Face:
        """extrude

        Extrude an Edge into a Face.

        Args:
            direction (VectorLike): direction and magnitude of extrusion

        Raises:
            ValueError: Unsupported class
            RuntimeError: Generated invalid result

        Returns:
            Face: extruded shape
        """
        return Face(TopoDS.Face_s(_extrude_topods_shape(obj.wrapped, direction)))

    @classmethod
    def make_bezier_surface(
        cls,
        points: list[list[VectorLike]],
        weights: list[list[float]] | None = None,
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
        for i, row_points in enumerate(points):
            for j, point in enumerate(row_points):
                points_.SetValue(i + 1, j + 1, Vector(point).to_pnt())

        if weights:
            weights_ = TColStd_HArray2OfReal(1, len(weights), 1, len(weights[0]))
            for i, row_weights in enumerate(weights):
                for j, weight in enumerate(row_weights):
                    weights_.SetValue(i + 1, j + 1, float(weight))
            bezier = Geom_BezierSurface(points_, weights_)
        else:
            bezier = Geom_BezierSurface(points_)

        return cls(BRepBuilderAPI_MakeFace(bezier, Precision.Confusion_s()).Face())

    @classmethod
    def make_plane(
        cls,
        plane: Plane = Plane.XY,
    ) -> Face:
        """Create a unlimited size Face aligned with plane"""
        pln_shape = BRepBuilderAPI_MakeFace(plane.wrapped).Face()
        return cls(pln_shape)

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
    def make_surface(
        cls,
        exterior: Wire | Iterable[Edge],
        surface_points: Iterable[VectorLike] | None = None,
        interior_wires: Iterable[Wire] | None = None,
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
        exterior = list(exterior) if isinstance(exterior, Iterable) else exterior
        # pylint: disable=too-many-branches
        if surface_points:
            surface_point_vectors = [Vector(p) for p in surface_points]
        else:
            surface_point_vectors = None

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
            outside_edges = ShapeList(exterior)
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
        if surface_point_vectors:
            for point in surface_point_vectors:
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

    @classmethod
    def make_surface_from_array_of_points(
        cls,
        points: list[list[VectorLike]],
        tol: float = 1e-2,
        smoothing: tuple[float, float, float] | None = None,
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
    def make_surface_from_curves(cls, *args, **kwargs) -> Face:
        """make_surface_from_curves

        Create a ruled surface out of two edges or two wires. If wires are used then
        these must have the same number of edges.

        Args:
            curve1 (Union[Edge,Wire]): side of surface
            curve2 (Union[Edge,Wire]): opposite side of surface

        Returns:
            Face: potentially non planar surface
        """
        curve1, curve2 = None, None
        if args:
            if len(args) != 2 or type(args[0]) is not type(args[1]):
                raise TypeError(
                    "Both curves must be of the same type (both Edge or both Wire)."
                )
            curve1, curve2 = args

        curve1 = kwargs.pop("edge1", curve1)
        curve2 = kwargs.pop("edge2", curve2)
        curve1 = kwargs.pop("wire1", curve1)
        curve2 = kwargs.pop("wire2", curve2)

        # Handle unexpected kwargs
        if kwargs:
            raise ValueError(f"Unexpected argument(s): {', '.join(kwargs.keys())}")

        if not isinstance(curve1, (Edge, Wire)) or not isinstance(curve2, (Edge, Wire)):
            raise TypeError(
                "Both curves must be of the same type (both Edge or both Wire)."
            )

        if isinstance(curve1, Wire):
            return_value = cls.cast(BRepFill.Shell_s(curve1.wrapped, curve2.wrapped))
        else:
            return_value = cls.cast(BRepFill.Face_s(curve1.wrapped, curve2.wrapped))
        return return_value

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
        # Sew the faces
        sewed_shape = _sew_topods_faces([f.wrapped for f in faces])
        top_level_shapes = get_top_level_topods_shapes(sewed_shape)
        sewn_faces: list[ShapeList] = []

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
        profile: Curve | Edge | Wire,
        path: Curve | Edge | Wire,
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

    # ---- Instance Methods ----

    def center(self, center_of: CenterOf = CenterOf.GEOMETRY) -> Vector:
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

    def chamfer_2d(
        self,
        distance: float,
        distance2: float,
        vertices: Iterable[Vertex],
        edge: Edge | None = None,
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

        chamfer_builder = BRepFilletAPI_MakeFillet2d(self.wrapped)

        vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            self.wrapped, ta.TopAbs_VERTEX, ta.TopAbs_EDGE, vertex_edge_map
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
        return self.__class__.cast(chamfer_builder.Shape()).fix()

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

        return self.__class__.cast(fillet_builder.Shape())

    def geom_adaptor(self) -> Geom_Surface:
        """Return the Geom Surface for this Face"""
        return BRep_Tool.Surface_s(self.wrapped)

    def inner_wires(self) -> ShapeList[Wire]:
        """Extract the inner or hole wires from this Face"""
        outer = self.outer_wire()

        return ShapeList([w for w in self.wires() if not w.is_same(outer)])

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

    def location_at(
        self, u: float, v: float, x_dir: VectorLike | None = None
    ) -> Location:
        """Location at the u/v position of face"""
        origin = self.position_at(u, v)
        if x_dir is None:
            pln = Plane(origin, z_dir=self.normal_at(origin))
        else:
            pln = Plane(origin, x_dir=Vector(x_dir), z_dir=self.normal_at(origin))
        return Location(pln)

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

    @overload
    def normal_at(self, surface_point: VectorLike | None = None) -> Vector:
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
        surface_point, u, v = None, -1.0, -1.0

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
        if surface_point is None and u < 0 and v < 0:
            u, v = 0.5, 0.5
        elif surface_point is None and sum(i == -1.0 for i in [u, v]) == 1:
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

    def outer_wire(self) -> Wire:
        """Extract the perimeter wire from this Face"""
        return Wire(BRepTools.OuterWire_s(self.wrapped))

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

        intersected_shapes: ShapeList[Face | Shell] = ShapeList()
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
        projected_shapes: ShapeList[Face | Shell] = ShapeList()
        for shape in intersected_shapes:
            if len(shape.faces()) == 1:
                shape_face = shape.face()
                if shape_face is not None:
                    projected_shapes.append(shape_face)
            else:
                projected_shapes.append(shape)
        return projected_shapes

    def to_arcs(self, tolerance: float = 1e-3) -> Face:
        """to_arcs

        Approximate planar face with arcs and straight line segments.

        Args:
            tolerance (float, optional): Approximation tolerance. Defaults to 1e-3.

        Returns:
            Face: approximated face
        """
        if self.wrapped is None:
            raise ValueError("Cannot approximate an empty shape")

        return self.__class__.cast(BRepAlgo.ConvertFace_s(self.wrapped, tolerance))

    def wire(self) -> Wire:
        """Return the outerwire, generate a warning if inner_wires present"""
        if self.inner_wires():
            warnings.warn(
                "Found holes, returning outer_wire",
                stacklevel=2,
            )
        return self.outer_wire()

    def _uv_bounds(self) -> tuple[float, float, float, float]:
        """Return the u min, u max, v min, v max values"""
        return BRepTools.UVBounds_s(self.wrapped)


class Shell(Mixin2D, Shape[TopoDS_Shell]):
    """A Shell is a fundamental component in build123d's topological data structure
    representing a connected set of faces forming a closed surface in 3D space. As
    part of a geometric model, it defines a watertight enclosure, commonly encountered
    in solid modeling. Shells group faces in a coherent manner, playing a crucial role
    in representing complex shapes with voids and surfaces. This hierarchical structure
    allows for efficient handling of surfaces within a model, supporting various
    operations and analyses."""

    order = 2.5
    # ---- Constructor ----

    def __init__(
        self,
        obj: TopoDS_Shell | Face | Iterable[Face] | None = None,
        label: str = "",
        color: Color | None = None,
        parent: Compound | None = None,
    ):
        """Build a shell from an OCCT TopoDS_Shape/TopoDS_Shell

        Args:
            obj (TopoDS_Shape | Face | Iterable[Face], optional): OCCT Shell, Face or Faces.
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
        """
        obj = list(obj) if isinstance(obj, Iterable) else obj
        if isinstance(obj, Iterable) and len(obj_list := list(obj)) == 1:
            obj = obj_list[0]

        if isinstance(obj, Face):
            assert isinstance(obj.wrapped, TopoDS_Face)
            builder = BRep_Builder()
            shell = TopoDS_Shell()
            builder.MakeShell(shell)
            builder.Add(shell, obj.wrapped)
            obj = shell
        elif isinstance(obj, Iterable):
            obj = _sew_topods_faces([f.wrapped for f in obj])

        super().__init__(
            obj=obj,
            label=label,
            color=color,
            parent=parent,
        )

    # ---- Properties ----

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

    # ---- Class Methods ----

    @classmethod
    def extrude(cls, obj: Wire, direction: VectorLike) -> Shell:
        """extrude

        Extrude a Wire into a Shell.

        Args:
            direction (VectorLike): direction and magnitude of extrusion

        Raises:
            ValueError: Unsupported class
            RuntimeError: Generated invalid result

        Returns:
            Edge: extruded shape
        """
        return Shell(TopoDS.Shell_s(_extrude_topods_shape(obj.wrapped, direction)))

    @classmethod
    def make_loft(cls, objs: Iterable[Vertex | Wire], ruled: bool = False) -> Shell:
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

    @classmethod
    def sweep(
        cls,
        profile: Curve | Edge | Wire,
        path: Curve | Edge | Wire,
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

    # ---- Instance Methods ----

    def center(self) -> Vector:
        """Center of mass of the shell"""
        properties = GProp_GProps()
        BRepGProp.LinearProperties_s(self.wrapped, properties)
        return Vector(properties.CentreOfMass())


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
