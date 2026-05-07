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
import sys
import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from math import degrees
from typing import TYPE_CHECKING, Any, TypeVar
from typing import cast as tcast
from typing import overload

import OCP.TopAbs as ta
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepAlgo import BRepAlgo
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Section
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeWire,
)
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepFill import BRepFill
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet2d
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeFilling, BRepOffsetAPI_MakePipeShell
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCP.BRepTools import BRepTools, BRepTools_ReShape
from OCP.gce import gce_MakeLin
from OCP.Geom import (
    Geom_BezierSurface,
    Geom_BSplineCurve,
    Geom_OffsetSurface,
    Geom_RectangularTrimmedSurface,
    Geom_Surface,
    Geom_TrimmedCurve,
)
from OCP.GeomAbs import GeomAbs_C0, GeomAbs_CurveType, GeomAbs_G1, GeomAbs_G2
from OCP.GeomAdaptor import GeomAdaptor_Surface
from OCP.GeomAPI import (
    GeomAPI_ExtremaCurveCurve,
    GeomAPI_PointsToBSplineSurface,
    GeomAPI_ProjectPointOnSurf,
)
from OCP.GeomLib import GeomLib_IsPlanarSurface
from OCP.GeomProjLib import GeomProjLib
from OCP.gp import gp_Ax1, gp_Ax3, gp_Pln, gp_Pnt, gp_Vec
from OCP.GProp import GProp_GProps
from OCP.Precision import Precision
from OCP.ShapeFix import ShapeFix_Solid, ShapeFix_Wire
from OCP.Standard import (
    Standard_ConstructionError,
    Standard_Failure,
    Standard_NoSuchObject,
    Standard_TypeMismatch,
)
from OCP.StdFail import StdFail_NotDone
from OCP.TColgp import TColgp_Array1OfPnt, TColgp_HArray2OfPnt
from OCP.TColStd import (
    TColStd_Array1OfInteger,
    TColStd_Array1OfReal,
    TColStd_HArray2OfReal,
)
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Shape, TopoDS_Shell, TopoDS_Solid
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_ListOfShape
from ocp_gordon import interpolate_curve_network
from typing_extensions import Self, deprecated

from build123d.build_enums import (
    CenterOf,
    ContinuityLevel,
    GeomType,
    Keep,
    SortBy,
    Transition,
)
from build123d.geometry import (
    DEG2RAD,
    TOLERANCE,
    Axis,
    Color,
    Location,
    OrientedBoundBox,
    Plane,
    Vector,
    VectorLike,
)

from .one_d import Edge, Mixin1D, Wire
from .shape_core import (
    TOPODS,
    Shape,
    ShapeList,
    SkipClean,
    _sew_topods_faces,
    _topods_bool_op,
    _topods_entities,
    _topods_face_normal_at,
    downcast,
    get_top_level_topods_shapes,
    shapetype,
)
from .utils import (
    _extrude_topods_shape,
    _make_loft,
    _make_topods_face_from_wires,
    find_max_dimension,
)
from .zero_d import Vertex

if TYPE_CHECKING:  # pragma: no cover
    from .composite import Compound, Curve  # pylint: disable=R0801
    from .three_d import Solid  # pylint: disable=R0801

T = TypeVar("T", Edge, Wire, "Face")


class Mixin2D(ABC, Shape[TOPODS]):
    """Additional methods to add to Face and Shell class"""

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
        if self._wrapped is None:
            raise ValueError("Invalid Shape")
        new_surface = copy.deepcopy(self)
        new_surface.wrapped = tcast(TOPODS, downcast(self.wrapped.Complemented()))

        # As the surface has been modified, the parent is no longer valid
        new_surface.topo_parent = None

        return new_surface

    # def face(self) -> Face | None:
    #     """Return the Face"""
    #     return Shape.get_single_shape(self, "Face")

    # def faces(self) -> ShapeList[Face]:
    #     """faces - all the faces in this Shape"""
    #     return Shape.get_shape_list(self, "Face")

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
        if self._wrapped is None:
            return []

        intersection_line = gce_MakeLin(other.wrapped).Value()
        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(self.wrapped, intersection_line, tolerance)

        intersections = []
        while intersect_maker.More():
            inter_pt = intersect_maker.Pnt()
            # Calculate distance along axis
            distance = Plane(other).to_local_coords(Vector(inter_pt)).Z
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

    def _intersect(
        self,
        other: Shape | Vector | Location | Axis | Plane,
        tolerance: float = 1e-6,
        include_touched: bool = False,
    ) -> ShapeList | None:
        """Single-object intersection for Face/Shell.

        Returns same-dimension overlap or crossing geometry:
        - 2D + 2D → Face (coplanar overlap) + Edge (crossing curves)
        - 2D + Edge → Edge (on surface) + Vertex (piercing)
        - 2D + Solid/Compound → delegates to other._intersect(self)

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
        elif isinstance(other, Plane):
            other = Face(other)

        def filter_edges(
            section_edges: ShapeList[Edge], common_edges: ShapeList[Edge]
        ) -> ShapeList[Edge]:
            """Filter section edges, keeping only edges not on common face boundaries."""
            # Pre-compute bounding boxes for both sets (optimal=False for speed, filtering only)
            section_bboxes = [(e, e.bounding_box(optimal=False)) for e in section_edges]
            common_bboxes = [
                (ce, ce.bounding_box(optimal=False)) for ce in common_edges
            ]

            # Filter: remove section edges that coincide with common face boundaries
            filtered: ShapeList = ShapeList()
            for edge, edge_bbox in section_bboxes:
                is_common = any(
                    edge_bbox.overlaps(ce_bbox, tolerance)
                    and edge.distance_to(ce) <= tolerance
                    for ce, ce_bbox in common_bboxes
                )
                if not is_common:
                    filtered.append(edge)
            return filtered

        results: ShapeList = ShapeList()

        # Trim infinite edges before OCCT operations
        if isinstance(other, Edge) and other.is_infinite:
            bbox = self.bounding_box(optimal=False)
            other = other.trim_infinite(
                bbox.diagonal + (other.center() - bbox.center()).length
            )

        # 2D + 2D: Common (coplanar overlap) AND Section (crossing curves)
        if isinstance(other, (Face, Shell)):
            # Common for coplanar overlap
            common = self._bool_op_list((self,), (other,), BRepAlgoAPI_Common())
            common_faces = common.expand()
            results.extend(common_faces)

            # Section for crossing curves (only edges, not vertices)
            # Vertices from Section are boundary contacts (touch), not intersections
            section = self._bool_op_list((self,), (other,), BRepAlgoAPI_Section())
            section_edges = ShapeList(
                [s for s in section if isinstance(s, Edge)]
            ).expand()

            if not common_faces:
                # No coplanar overlap - all section edges are valid crossings
                results.extend(section_edges)
            else:
                # Filter out edges on common face boundaries
                # (Section returns boundary of overlap region which are not crossings)
                common_edges: ShapeList[Edge] = ShapeList()
                for face in common_faces:
                    common_edges.extend(face.edges())
                results.extend(filter_edges(section_edges, common_edges))

        # 2D + Edge: Section for intersection
        elif isinstance(other, (Edge, Wire)):
            section = self._bool_op_list((self,), (other,), BRepAlgoAPI_Section())
            results.extend(section)

        # 2D + Vertex: point containment on surface
        elif isinstance(other, Vertex):
            if other.distance_to(self) <= tolerance:
                results.append(other)

        # Delegate to higher-order shapes (Solid, etc.)
        else:
            result = other._intersect(self, tolerance, include_touched)
            if result:
                results.extend(result)

        # Add boundary contacts if requested
        if include_touched and isinstance(other, (Face, Shell)):
            found_faces = ShapeList(r for r in results if isinstance(r, Face))
            found_edges = ShapeList(r for r in results if isinstance(r, Edge))
            results.extend(self.touch(other, tolerance, found_faces, found_edges))

        return results if results else None

    def touch(
        self,
        other: Shape,
        tolerance: float = 1e-6,
        found_faces: ShapeList | None = None,
        found_edges: ShapeList | None = None,
    ) -> ShapeList:
        """Find boundary contacts between this 2D shape and another shape.

        Returns the highest-dimensional contact at each location, filtered to
        avoid returning lower-dimensional boundaries of higher-dimensional contacts.

        For Face/Shell:
        - Face + Face → Vertex (shared corner or crossing point without edge/face overlap)
        - Face + Edge/Vertex → no touch (intersect already returns dim 0)

        Args:
            other: Shape to find contacts with
            tolerance: tolerance for contact detection
            found_faces: pre-found faces to filter against (from Mixin3D.touch)
            found_edges: pre-found edges to filter against (from Mixin3D.touch)

        Returns:
            ShapeList of contact shapes (Vertex only for 2D+2D)
        """

        # Helper functions for common geometric checks
        def vertex_on_edges(v: Vertex, edges: Iterable[Edge]) -> bool:
            return any(v.distance_to(e) <= tolerance for e in edges)

        def vertex_on_faces(v: Vertex, faces: Iterable[Face]) -> bool:
            return any(v.distance_to(f) <= tolerance for f in faces)

        def is_duplicate(v: Vertex, vertices: Iterable[Vertex]) -> bool:
            vec = Vector(v)
            return any(vec == Vector(ov) for ov in vertices)

        results: ShapeList = ShapeList()

        if isinstance(other, (Face, Shell)):
            # Get intersect results to filter against if not provided (direct call)
            if found_faces is None:
                found_faces = ShapeList()
                found_edges = ShapeList()
                intersect_results = self._intersect(
                    other, tolerance, include_touched=False
                )
                if intersect_results:
                    for r in intersect_results:
                        if isinstance(r, Face):
                            found_faces.append(r)
                        elif isinstance(r, Edge):
                            found_edges.append(r)
            elif found_edges is None:  # for mypy
                found_edges = ShapeList()

            # Use BRepExtrema to find all contact points
            # (vertex-vertex, vertex-edge, vertex-face)
            found_vertices: ShapeList = ShapeList()
            extrema = BRepExtrema_DistShapeShape()
            extrema.SetDeflection(
                tolerance * 1e-3
            )  # Higher precision to avoid duplicate solutions
            extrema.LoadS1(self.wrapped)
            extrema.LoadS2(other.wrapped)
            extrema.Perform()
            if extrema.IsDone() and extrema.Value() <= tolerance:
                for i in range(1, extrema.NbSolution() + 1):
                    pnt1 = extrema.PointOnShape1(i)
                    pnt2 = extrema.PointOnShape2(i)
                    if pnt1.Distance(pnt2) > tolerance:
                        continue

                    new_vertex = Vertex(pnt1.X(), pnt1.Y(), pnt1.Z())

                    # Skip duplicates early (cheap check)
                    if is_duplicate(new_vertex, found_vertices):
                        continue

                    # Skip edge-edge intersections, but allow corner touches
                    if (
                        vertex_on_edges(new_vertex, self.edges())
                        and vertex_on_edges(new_vertex, other.edges())
                        and not is_duplicate(new_vertex, self.vertices())
                        and not is_duplicate(new_vertex, other.vertices())
                    ):
                        continue

                    # Filter: only keep vertices that are not boundaries of
                    # higher-dimensional contacts (faces or edges)
                    if not vertex_on_faces(
                        new_vertex, found_faces
                    ) and not vertex_on_edges(new_vertex, found_edges):
                        results.append(new_vertex)
                        found_vertices.append(new_vertex)

        # Face + Edge/Vertex: no touch (intersect already covers dim 0)
        # Delegate to other shapes (Compound iterates, others return empty)
        else:
            results.extend(other.touch(self, tolerance))

        return results

    @abstractmethod
    def location_at(self, *args: Any, **kwargs: Any) -> Location:
        """A location from a face or shell"""

    def offset(self, amount: float) -> Self:
        """Return a copy of self moved along the normal by amount"""
        return copy.deepcopy(self).moved(Location(self.normal_at() * amount))

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
        return Mixin1D.project_to_viewport(
            self, viewport_origin, viewport_up, look_at, focus
        )

    def _wrap_edge(
        self,
        planar_edge: Edge,
        surface_loc: Location,
        snap_to_face: bool = True,
        tolerance: float = 0.001,
    ) -> Edge:
        """_wrap_edge

        Helper method of wrap that handles wrapping edges on surfaces (Face or Shell).

        Args:
            planar_edge (Edge): edge to wrap around surface
            surface_loc (Location): location on surface to wrap
            snap_to_face (bool,optional): ensure wrapped edge is tight against surface.
                Defaults to True.
            tolerance (float, optional): maximum allowed length error during initial wrapping
                operation. Defaults to 0.001

        Raises:
            RuntimeError: wrapping over surface boundary, try difference surface_loc
        Returns:
            Edge: wrapped edge
        """

        def _intersect_surface_normal(
            point: Vector, direction: Vector
        ) -> tuple[Vector, Vector]:
            """Return the intersection point and normal of the closest surface face
            along direction"""
            axis = Axis(point, direction)
            faces = self.faces_intersected_by_axis(axis).sort_by(
                lambda f: f.distance_to(point)
            )
            face = faces[0]  # pylint: disable=no-member
            inter = face.find_intersection_points(axis)  # pylint: disable=no-member
            if not inter:
                raise RuntimeError(
                    "wrapping over surface boundary, try difference surface_loc"
                )
            return min(inter, key=lambda pair: abs(pair[0] - point))

        def _find_point_on_surface(
            current_point: Vector, normal: Vector, relative_position: Vector
        ) -> tuple[Vector, Vector]:
            """Project a 2D offset from a local surface frame onto the 3D surface"""
            local_plane = Plane(
                origin=current_point,
                x_dir=surface_x_direction,
                z_dir=normal,
            )
            world_point = local_plane.from_local_coords(relative_position)
            return _intersect_surface_normal(
                world_point, world_point - target_object_center
            )

        if self._wrapped is None:
            raise ValueError("Can't wrap around an empty face")

        # Initial setup
        target_object_center = self.center(CenterOf.BOUNDING_BOX)

        surface_x_direction = surface_loc.x_axis.direction

        planar_edge_length = planar_edge.length

        # Start adaptive refinement
        subdivisions = 3
        max_loops = 10
        loop_count = 0
        length_error = sys.float_info.max

        # Find the location on the surface to start
        if planar_edge.position_at(0).length > tolerance:
            # The start point isn't at the surface_loc so wrap a line to find it
            to_start_edge = Edge.make_line((0, 0), planar_edge @ 0)
            wrapped_to_start_edge = self._wrap_edge(
                to_start_edge, surface_loc, snap_to_face=True, tolerance=tolerance
            )
            start_pnt = wrapped_to_start_edge @ 1
            _, start_normal = _intersect_surface_normal(
                start_pnt, (start_pnt - target_object_center)
            )
        else:
            # The start point is at the surface location
            start_pnt = surface_loc.position
            start_normal = surface_loc.z_axis.direction

        while length_error > tolerance and loop_count < max_loops:
            # Seed the wrapped path
            wrapped_edge_points: list[VectorLike] = []
            current_point, current_normal = start_pnt, start_normal
            wrapped_edge_points.append(current_point)

            # Subdivide and propagate
            for div in range(1, subdivisions + int(not planar_edge.is_closed)):
                prev = planar_edge.position_at((div - 1) / subdivisions)
                curr = planar_edge.position_at(div / subdivisions)
                offset = curr - prev
                current_point, current_normal = _find_point_on_surface(
                    current_point, current_normal, offset
                )
                wrapped_edge_points.append(current_point)

            # Build and evaluate
            wrapped_edge = Edge.make_spline(
                wrapped_edge_points, periodic=planar_edge.is_closed
            )
            length_error = abs(planar_edge_length - wrapped_edge.length)

            subdivisions *= 2
            loop_count += 1

        if length_error > tolerance:
            raise RuntimeError(
                f"Length error of {length_error:.6f} exceeds tolerance {tolerance}"
            )
        if not wrapped_edge or not wrapped_edge.is_valid:
            raise RuntimeError("Wrapped edge is invalid")

        if not snap_to_face:
            return wrapped_edge

        # Project the curve onto the surface
        surface_handle = BRep_Tool.Surface_s(self.wrapped)
        first_param: float = wrapped_edge.param_at(0)
        last_param: float = wrapped_edge.param_at(1)
        curve_handle = BRep_Tool.Curve_s(wrapped_edge.wrapped, first_param, last_param)
        proj_curve_handle = GeomProjLib.Project_s(curve_handle, surface_handle)
        if proj_curve_handle is None:
            raise RuntimeError(
                "Projection failed, try setting `snap_to_face` to False."
            )

        # Build a new projected edge
        projected_edge = Edge(BRepBuilderAPI_MakeEdge(proj_curve_handle).Edge())

        return projected_edge


class Face(Mixin2D[TopoDS_Face]):
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
        obj: TopoDS_Face | Plane,
        label: str = "",
        color: Color | None = None,
        parent: Compound | None = None,
    ):
        """Build a Face from an OCCT TopoDS_Shape/TopoDS_Face

        Args:
            obj (TopoDS_Shape | Plane, optional): OCCT Face or Plane.
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
        obj: TopoDS_Face | Plane | None
        outer_wire, inner_wires, obj, label, color, parent = (None,) * 6

        if args:
            l_a = len(args)
            if isinstance(args[0], Plane):
                obj = args[0]
            elif isinstance(args[0], TopoDS_Shape):
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

        if isinstance(obj, Plane):
            obj = BRepBuilderAPI_MakeFace(obj.wrapped).Face()

        if outer_wire is not None:
            inner_topods_wires = (
                [w.wrapped for w in inner_wires] if inner_wires is not None else []
            )
            if any(
                not BRep_Tool.IsClosed_s(w)
                for w in [outer_wire.wrapped] + inner_topods_wires
            ):
                raise ValueError("Face can only be created with closed wires")
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
    def area_without_holes(self) -> float:
        """
        Calculate the total surface area of the face, including the areas of any holes.

        This property returns the overall area of the face as if the inner boundaries (holes)
        were filled in.

        Returns:
            float: The total surface area, including the area of holes. Returns 0.0 if
            the face is empty.
        """
        if self._wrapped is None:
            return 0.0

        return self.without_holes().area

    @property
    def axis_of_rotation(self) -> None | Axis:
        """Get the rotational axis of a cylinder or torus"""

        # Get the underlying geometric surface
        surf: Geom_Surface = self.geom_adaptor()

        # Unwrap trimmed and offset surfaces to get at the basis surface
        while isinstance(surf, (Geom_RectangularTrimmedSurface, Geom_OffsetSurface)):
            surf = surf.BasisSurface()

        # Get the geometry type from the geometric surface
        geom_type = Shape.geom_LUT_FACE[GeomAdaptor_Surface(surf).GetType()]

        # Determine the axis of rotation if there is one
        match geom_type:
            case GeomType.CONE:
                return Axis(
                    surf.Cone().Axis()  # type:ignore[attr-defined]
                )
            case GeomType.CYLINDER:
                return Axis(
                    surf.Cylinder().Axis()  # type:ignore[attr-defined]
                )
            case GeomType.SPHERE:
                ax3 = surf.Position()  # type:ignore[attr-defined]
                return Axis(gp_Ax1(ax3.Location(), ax3.Direction()))

            case GeomType.TORUS:
                return Axis(
                    surf.Torus().Axis()  # type:ignore[attr-defined]
                )
            case GeomType.REVOLUTION:
                return Axis(surf.Axis())  # type:ignore[attr-defined]
            case _:
                return None

    @property
    def axes_of_symmetry(self) -> list[Axis]:
        """Computes and returns the axes of symmetry for a planar face.

        The method determines potential symmetry axes by analyzing the face’s
        geometry:

        - It first validates that the face is non-empty and planar.

        - For faces with inner wires (holes), it computes the centroid of the
          holes and the face's overall center (COG).

            - If the holes' centroid significantly deviates from the COG (beyond
              a specified tolerance), the symmetry axis is taken along the line
              connecting these points; otherwise, each hole’s center is used to
              generate a candidate axis.

        - For faces without holes, candidate directions are derived by sampling
          midpoints along the outer wire's edges.

            - If curved edges are present, additional candidate directions are
              obtained from an oriented bounding box (OBB) constructed around the
              face.

        For each candidate direction, the face is split by a plane (defined
        using the candidate direction and the face’s normal).  The top half of the face
        is then mirrored across this plane, and if the area of the intersection between
        the mirrored half and the bottom half matches the bottom half’s area within a
        small tolerance, the direction is accepted as an axis of symmetry.

        Returns:
            list[Axis]: A list of Axis objects, each defined by the face's
                center and a direction vector, representing the symmetry axes of
                the face.

        Raises:
            ValueError: If the face or its underlying representation is empty.
            ValueError: If the face is not planar.
        """
        if self._wrapped is None:
            raise ValueError("Can't determine axes_of_symmetry of empty face")

        if not self.is_planar:
            raise ValueError("axes_of_symmetry only supports for planar faces")

        cog = self.center()
        normal = self.normal_at()
        shape_inner_wires = self.inner_wires()
        if shape_inner_wires:
            hole_faces = [Face(w) for w in shape_inner_wires]
            holes_centroid = Face.combined_center(hole_faces)
            # If the holes aren't centered on the cog the axis of symmetry must be
            # through the cog and hole centroid
            if abs(holes_centroid - cog) > TOLERANCE:
                cross_dirs = [(holes_centroid - cog).normalized()]
            else:
                # There may be an axis of symmetry through the center of the holes
                cross_dirs = [(f.center() - cog).normalized() for f in hole_faces]
        else:
            curved_edges = (
                self.outer_wire().edges().filter_by(GeomType.LINE, reverse=True)
            )
            shape_edges = self.outer_wire().edges()
            if curved_edges:
                obb = OrientedBoundBox(self)
                corners = obb.corners
                obb_edges = ShapeList(
                    [Edge.make_line(corners[i], corners[(i + 1) % 4]) for i in range(4)]
                )
                mid_points = [
                    e @ p for e in shape_edges + obb_edges for p in [0.0, 0.5, 1.0]
                ]
            else:
                mid_points = [e @ p for e in shape_edges for p in [0.0, 0.5, 1.0]]
            cross_dirs = [(mid_point - cog).normalized() for mid_point in mid_points]

        symmetry_dirs: set[Vector] = set()
        for cross_dir in cross_dirs:
            # Split the face by the potential axis and flip the top
            split_plane = Plane(
                origin=cog,
                x_dir=cross_dir,
                z_dir=cross_dir.cross(normal),
            )
            # Split by plane
            top, bottom = self.split(split_plane, keep=Keep.BOTH)

            if type(top) != type(bottom):  # exit early if not same
                continue

            if top is None or bottom is None:  # Impossible to actually happen?
                continue

            top_list = ShapeList(top if isinstance(top, list) else [top])
            bottom_list = ShapeList(bottom if isinstance(bottom, list) else [bottom])

            if len(top_list) != len(bottom_list):  # exit early unequal length
                continue

            bottom_list = bottom_list.sort_by(Axis(cog, cross_dir))
            top_flipped_list = ShapeList(
                f.mirror(split_plane) for f in top_list
            ).sort_by(Axis(cog, cross_dir))

            bottom_area = sum(f.area for f in bottom_list)
            for flipped_face, bottom_face in zip(top_flipped_list, bottom_list):
                intersection = flipped_face.intersect(bottom_face)
                if intersection is None:
                    intersect_area = -1.0
                    break
                intersect_area = sum(f.area for f in intersection.faces())

            if intersect_area == -1.0:
                continue

            # Are the top/bottom the same?
            if abs(intersect_area - bottom_area) < TOLERANCE:
                if not symmetry_dirs:
                    symmetry_dirs.add(cross_dir)
                else:
                    opposite = any(
                        d.dot(cross_dir) < -1 + TOLERANCE for d in symmetry_dirs
                    )
                    if not opposite:
                        symmetry_dirs.add(cross_dir)

        symmetry_axes = [Axis(cog, d) for d in symmetry_dirs]
        return symmetry_axes

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
    def _curvature_sign(self) -> float:
        """
        Compute the signed dot product between the face normal and the vector from the
        underlying geometry's reference point to the face center.

        For a cylinder, the reference is the cylinder's axis position.
        For a sphere, it is the sphere's center.
        For a torus, we derive a reference point on the central circle.

        Returns:
            float: The signed value; positive indicates convexity, negative indicates concavity.
                Returns 0 if the geometry type is unsupported.
        """
        if self.geom_type == GeomType.CYLINDER and not isinstance(
            self.geom_adaptor(), Geom_RectangularTrimmedSurface
        ):
            axis = self.axis_of_rotation
            if axis is None:
                raise ValueError("Can't find curvature of empty object")
            return self.normal_at().dot(self.center() - axis.position)

        if self.geom_type == GeomType.SPHERE:
            loc = self.location  # The sphere's center
            if loc is None:
                raise ValueError("Can't find curvature of empty object")
            return self.normal_at().dot(self.center() - loc.position)

        if self.geom_type == GeomType.TORUS:
            # Here we assume that for a torus the rotational axis can be converted to a plane,
            # and we then define the central (or core) circle using the first value of self.radii.
            axis = self.axis_of_rotation
            if axis is None or self.radii is None:
                raise ValueError("Can't find curvature of empty object")
            loc = Location(Plane(axis))
            axis_circle = Edge.make_circle(self.radii[0]).locate(loc)
            _, pnt_on_axis_circle, _ = axis_circle.distance_to_with_closest_points(
                self.center()
            )
            return self.normal_at().dot(self.center() - pnt_on_axis_circle)

        return 0.0

    @property
    def is_circular_convex(self) -> bool:
        """
        Determine whether a given face is convex relative to its underlying geometry
        for supported geometries: cylinder, sphere, torus.

        Returns:
            bool: True if convex; otherwise, False.
        """
        return self._curvature_sign > TOLERANCE

    @property
    def is_circular_concave(self) -> bool:
        """
        Determine whether a given face is concave relative to its underlying geometry
        for supported geometries: cylinder, sphere, torus.

        Returns:
            bool: True if concave; otherwise, False.
        """
        return self._curvature_sign < -TOLERANCE

    @property
    def is_planar(self) -> Plane | None:
        """Is the face planar even though its geom_type may not be PLANE - if so return Plane"""
        surface = BRep_Tool.Surface_s(self.wrapped)
        planar_searcher = GeomLib_IsPlanarSurface(surface, TOLERANCE)
        if not planar_searcher.IsPlanar():
            return None
        pln = planar_searcher.Plan()
        if not pln.Position().Direct():  # A left-handed plane was returned
            pln = gp_Pln(gp_Ax3(pln.Position().Ax2()))
        return Plane(pln)

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
    def radii(self) -> None | tuple[float, float]:
        """Return the major and minor radii of a torus otherwise None"""
        if self.geom_type == GeomType.TORUS:
            return (
                self.geom_adaptor().MajorRadius(),  # type:ignore[attr-defined]
                self.geom_adaptor().MinorRadius(),  # type:ignore[attr-defined]
            )

        return None

    @property
    def radius(self) -> None | float:
        """Return the radius of a cylinder or sphere, otherwise None"""
        if self.geom_type in [GeomType.CYLINDER, GeomType.SPHERE] and not isinstance(
            self.geom_adaptor(), Geom_RectangularTrimmedSurface
        ):
            return self.geom_adaptor().Radius()  # type:ignore[attr-defined]
        return None

    @property
    def semi_angle(self) -> None | float:
        """Return the semi angle of a cone, otherwise None"""
        if self.geom_type == GeomType.CONE and not isinstance(
            self.geom_adaptor(), Geom_RectangularTrimmedSurface
        ):
            return degrees(self.geom_adaptor().SemiAngle())  # type:ignore[attr-defined]
        return None

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
        if not obj:
            raise ValueError("Can't extrude empty object")
        return Face(TopoDS.Face(_extrude_topods_shape(obj.wrapped, direction)))

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
    def make_gordon_surface(
        cls,
        profiles: Iterable[VectorLike | Edge],
        guides: Iterable[VectorLike | Edge],
        tolerance: float = 3e-4,
    ) -> Face:
        """
        Constructs a Gordon surface from a network of profile and guide curves.

        Requirements:
        1. Profiles and guides may be defined as points or curves.
        2. Only the first or last profile or guide may be a point.
        3. At least one profile and one guide must be a non-point curve.
        4. Each profile must intersect with every guide.
        5. Both ends of every profile must lie on a guide.
        6. Both ends of every guide must lie on a profile.

        Args:
            profiles (Iterable[VectorLike | Edge]): Profiles defined as points or edges.
            guides (Iterable[VectorLike | Edge]): Guides defined as points or edges.
            tolerance (float, optional): Tolerance used for surface construction and
                intersection calculations.

        Raises:
            ValueError: input Edge cannot be empty.

        Returns:
            Face: the interpolated Gordon surface
        """

        def create_zero_length_bspline_curve(
            point: gp_Pnt, degree: int = 1
        ) -> Geom_BSplineCurve:
            control_points = TColgp_Array1OfPnt(1, 2)
            control_points.SetValue(1, point)
            control_points.SetValue(2, point)

            knots = TColStd_Array1OfReal(1, 2)
            knots.SetValue(1, 0.0)
            knots.SetValue(2, 1.0)

            multiplicities = TColStd_Array1OfInteger(1, 2)
            multiplicities.SetValue(1, degree + 1)
            multiplicities.SetValue(2, degree + 1)

            curve = Geom_BSplineCurve(control_points, knots, multiplicities, degree)
            return curve

        def to_geom_curve(shape: VectorLike | Edge):
            if isinstance(shape, (Vector, tuple, Sequence)):
                _shape = Vector(shape)
                single_point_curve = create_zero_length_bspline_curve(
                    gp_Pnt(_shape.wrapped.XYZ())
                )
                return single_point_curve

            if not shape:
                raise ValueError("input Edge cannot be empty")

            adaptor = BRepAdaptor_Curve(shape.wrapped)
            curve = BRep_Tool.Curve_s(shape.wrapped, 0, 1)
            if not (
                (adaptor.IsPeriodic() and adaptor.IsClosed())
                or adaptor.GetType() == GeomAbs_CurveType.GeomAbs_BSplineCurve
                or adaptor.GetType() == GeomAbs_CurveType.GeomAbs_BezierCurve
            ):
                curve = Geom_TrimmedCurve(
                    curve, adaptor.FirstParameter(), adaptor.LastParameter()
                )
            return curve

        ocp_profiles = [to_geom_curve(shape) for shape in profiles]
        ocp_guides = [to_geom_curve(shape) for shape in guides]

        gordon_bspline_surface = interpolate_curve_network(
            ocp_profiles, ocp_guides, tolerance=tolerance
        )

        return cls(
            BRepBuilderAPI_MakeFace(
                gordon_bspline_surface, Precision.Confusion_s()
            ).Face()
        )

    @classmethod
    @deprecated(
        "The 'make_plane' method is deprecated and will be removed in a future version."
    )
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
            if not edge:
                raise ValueError("exterior contains empty edges")
            surface.Add(edge.wrapped, GeomAbs_C0)

        try:
            surface.Build()
            surface_face = Face(surface.Shape())  # type:ignore[call-overload]
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
                surface.Add(gp_Pnt(*point))
            try:
                surface.Build()
                surface_face = Face(surface.Shape())  # type:ignore[call-overload]
            except StdFail_NotDone as err:
                raise RuntimeError(
                    "Error building non-planar face with provided surface_points"
                ) from err

        # Next, add wires that define interior holes - note these wires must be entirely interior
        if interior_wires:
            makeface_object = BRepBuilderAPI_MakeFace(surface_face.wrapped)
            for wire in interior_wires:
                if not wire:
                    raise ValueError("interior_wires contain an empty wire")
                makeface_object.Add(wire.wrapped)
            try:
                surface_face = Face(makeface_object.Face())
            except StdFail_NotDone as err:
                raise RuntimeError(
                    "Error adding interior hole in non-planar face with provided interior_wires"
                ) from err

        surface_face = surface_face.fix()
        if not surface_face.is_valid:
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
    def make_surface_patch(
        cls,
        edge_face_constraints: (
            Iterable[tuple[Edge, Face, ContinuityLevel]] | None
        ) = None,
        edge_constraints: Iterable[Edge] | None = None,
        point_constraints: Iterable[VectorLike] | None = None,
    ) -> Face:
        """make_surface_patch

        Create a potentially non-planar face patch bounded by exterior edges which can
        be optionally refined using support faces to ensure e.g. tangent surface
        continuity. Also can optionally refine the surface using surface points.

        Args:
            edge_face_constraints (list[tuple[Edge, Face, ContinuityLevel]], optional):
                Edges defining perimeter of face with adjacent support faces subject to
                ContinuityLevel. Defaults to None.
            edge_constraints (list[Edge], optional): Edges defining perimeter of face
                without adjacent support faces. Defaults to None.
            point_constraints (list[VectorLike], optional): Points on the surface that
                refine the shape. Defaults to None.

        Raises:
            RuntimeError: Error building non-planar face with provided constraints
            RuntimeError: Generated face is invalid

        Returns:
            Face: Potentially non-planar face
        """
        continuity_dict = {
            ContinuityLevel.C0: GeomAbs_C0,
            ContinuityLevel.C1: GeomAbs_G1,
            ContinuityLevel.C2: GeomAbs_G2,
        }
        patch = BRepOffsetAPI_MakeFilling()

        if edge_face_constraints:
            for constraint in edge_face_constraints:
                patch.Add(
                    constraint[0].wrapped,
                    constraint[1].wrapped,
                    continuity_dict[constraint[2]],
                )
        if edge_constraints:
            for edge in edge_constraints:
                patch.Add(edge.wrapped, continuity_dict[ContinuityLevel.C0])

        if point_constraints:
            for point in point_constraints:
                patch.Add(gp_Pnt(*point))

        try:
            patch.Build()
            result = cls(TopoDS.Face(patch.Shape()))
        except (
            Standard_Failure,
            StdFail_NotDone,
            Standard_NoSuchObject,
            Standard_ConstructionError,
        ) as err:
            raise RuntimeError(
                "Error building non-planar face with provided constraints"
            ) from err

        result = result.fix()
        if not result.is_valid or not result:
            raise RuntimeError("Non planar face is invalid")

        return result

    @classmethod
    def revolve(
        cls,
        profile: Edge,
        angle: float,
        axis: Axis,
    ) -> Face:
        """sweep

        Revolve an Edge around an axis.

        Args:
            profile (Edge): the object to sweep
            angle (float): the angle to revolve through
            axis (Axis): rotation Axis

        Returns:
            Face: resulting face
        """
        revol_builder = BRepPrimAPI_MakeRevol(
            profile.wrapped,
            axis.wrapped,
            angle * DEG2RAD,
            True,
        )

        return cls(revol_builder.Shape())  # type:ignore[call-overload]

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
                        Face(f)  # type:ignore[call-overload]
                        for f in _topods_entities(top_level_shape, "Face")
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
        profile_edge = profile.edge()
        path_edge = path.edge()
        assert profile_edge is not None
        assert path_edge is not None
        profile = Wire([profile_edge])
        path = Wire([path_edge])
        builder = BRepOffsetAPI_MakePipeShell(path.wrapped)
        builder.Add(profile.wrapped, False, False)
        builder.SetTransitionMode(Shape._transModeDict[transition])
        builder.Build()
        result = Face(builder.Shape())  # type:ignore[call-overload]
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
        center_point: Vector | gp_Pnt
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
            edges = (
                Edge(TopoDS.Edge(edge_list.First())),
                Edge(TopoDS.Edge(edge_list.Last())),
            )

            edge1, edge2 = Wire.order_chamfer_edges(reference_edge, edges)

            chamfer_builder.AddChamfer(
                TopoDS.Edge(edge1.wrapped),
                TopoDS.Edge(edge2.wrapped),
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
        vertices = [vertex for vertex in vertices if vertex.wrapped is not None]
        if not vertices:
            return self

        outer_wire = self.outer_wire()
        inner_wires = self.inner_wires()
        filleted_wires: list[Wire] = []

        for wire in [outer_wire, *inner_wires]:
            vertices_in_wire = [
                vertex
                for vertex in vertices
                if any(
                    wire_vertex.wrapped.IsSame(vertex.wrapped)
                    for wire_vertex in wire.vertices()
                )
            ]
            filleted_wires.append(
                wire.fillet_2d(radius, vertices_in_wire) if vertices_in_wire else wire
            )

        filleted_face = self.__class__(filleted_wires[0], filleted_wires[1:])
        if self.normal_at() != filleted_face.normal_at():
            filleted_face = -filleted_face  # pylint: disable=invalid-unary-operand-type

        return filleted_face

    def geom_adaptor(self) -> Geom_Surface:
        """Return the Geom Surface for this Face"""
        return BRep_Tool.Surface_s(self.wrapped)

    def inner_wires(self) -> ShapeList[Wire]:
        """Extract the inner or hole wires from this Face"""
        outer = self.outer_wire()
        inners = [w for w in self.wires() if not w.is_same(outer)]
        for w in inners:
            w.topo_parent = self if self.topo_parent is None else self.topo_parent
        return ShapeList(inners)

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
        solid_classifier.Perform(gp_Pnt(*Vector(point)), tolerance)
        return solid_classifier.IsOnAFace()

        # surface = BRep_Tool.Surface_s(self.wrapped)
        # projector = GeomAPI_ProjectPointOnSurf(Vector(point).to_pnt(), surface)
        # return projector.LowerDistance() <= TOLERANCE

    @overload
    def location_at(
        self,
        surface_point: VectorLike | None = None,
        *,
        x_dir: VectorLike | None = None,
    ) -> Location: ...

    @overload
    def location_at(
        self, u: float, v: float, *, x_dir: VectorLike | None = None
    ) -> Location: ...

    def location_at(self, *args, **kwargs) -> Location:
        """location_at

        Get the location (origin and orientation) on the surface of the face.

        This method supports two overloads:

        1. `location_at(u: float, v: float, *, x_dir: VectorLike | None = None) -> Location`
        - Specifies the point in normalized UV parameter space of the face.
        - `u` and `v` are floats between 0.0 and 1.0.
        - Optionally override the local X direction using `x_dir`.

        2. `location_at(surface_point: VectorLike, *, x_dir: VectorLike | None = None) -> Location`
        - Projects the given 3D point onto the face surface.
        - The point must be reasonably close to the face.
        - Optionally override the local X direction using `x_dir`.

        If no arguments are provided, the location at the center of the face
        (u=0.5, v=0.5) is returned.

        Args:
            u (float): Normalized horizontal surface parameter (optional).
            v (float): Normalized vertical surface parameter (optional).
            surface_point (VectorLike): A 3D point near the surface (optional).
            x_dir (VectorLike, optional): Direction for the local X axis. If not given,
                the tangent in the U direction is used.

        Returns:
            Location: A full 3D placement at the specified point on the face surface.

        Raises:
            ValueError: If only one of `u` or `v` is provided or invalid keyword args are passed.
        """
        surface_point, u, v = None, -1.0, -1.0

        if args:
            if isinstance(args[0], (Vector, Sequence)):
                surface_point = args[0]
            elif isinstance(args[0], (int, float)):
                u = args[0]
            if len(args) == 2 and isinstance(args[1], (int, float)):
                v = args[1]

        unknown_args = set(kwargs.keys()).difference(
            {"surface_point", "u", "v", "x_dir"}
        )
        if unknown_args:
            raise ValueError(f"Unexpected argument(s) {', '.join(unknown_args)}")

        surface_point = kwargs.get("surface_point", surface_point)
        u = kwargs.get("u", u)
        v = kwargs.get("v", v)
        user_x_dir = kwargs.get("x_dir", None)

        if surface_point is None and u < 0 and v < 0:
            u, v = 0.5, 0.5
        elif surface_point is None and (u < 0 or v < 0):
            raise ValueError("Both u & v values must be specified")

        geom_surface: Geom_Surface = self.geom_adaptor()
        u_min, u_max, v_min, v_max = self._uv_bounds()

        if surface_point is None:
            u_val = u_min + u * (u_max - u_min)
            v_val = v_min + v * (v_max - v_min)
        else:
            projector = GeomAPI_ProjectPointOnSurf(
                Vector(surface_point).to_pnt(), geom_surface
            )
            u_val, v_val = projector.LowerDistanceParameters()

        # Evaluate point and partials
        pnt = gp_Pnt()
        du = gp_Vec()
        dv = gp_Vec()
        geom_surface.D1(u_val, v_val, pnt, du, dv)

        origin = Vector(pnt)
        z_dir = Vector(du).cross(Vector(dv)).normalized()
        x_dir = (
            Vector(user_x_dir).normalized()
            if user_x_dir is not None
            else Vector(du).normalized()
        )

        return Location(Plane(origin=origin, x_dir=x_dir, z_dir=z_dir))

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
        # if not surface_face.is_valid:
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
            if isinstance(args[0], (Vector, Sequence)):
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
            u_val = u_val0 + u * (u_val1 - u_val0)
            v_val = v_val0 + v * (v_val1 - v_val0)
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
        outer = Wire(BRepTools.OuterWire_s(self.wrapped))
        outer.topo_parent = self if self.topo_parent is None else self.topo_parent
        return outer

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
                intersected_shapes.append(
                    Face(topods_shape)  # type:ignore[call-overload]
                )
        else:
            for target_shell in target_object.shells():
                topods_shape = _topods_bool_op(
                    (extruded_topods_self,),
                    (target_shell.wrapped,),
                    BRepAlgoAPI_Common(),
                )
                for topods_shell in get_top_level_topods_shapes(topods_shape):
                    intersected_shapes.append(Shell(TopoDS.Shell(topods_shell)))

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

    @deprecated(
        "The 'to_arcs' method is deprecated and will be removed in a future version."
    )
    def to_arcs(self, tolerance: float = 1e-3) -> Face:
        """to_arcs

        Approximate planar face with arcs and straight line segments.

        This is a utility used internally to convert or adapt a face for Boolean operations. Its
        purpose is not typically for general use, but rather as a helper within the Boolean kernel
        to ensure input faces are in a compatible and canonical form.

        Args:
            tolerance (float, optional): Approximation tolerance. Defaults to 1e-3.

        Returns:
            Face: approximated face
        """
        if self._wrapped is None:
            raise ValueError("Cannot approximate an empty shape")

        return self.__class__.cast(BRepAlgo.ConvertFace_s(self.wrapped, tolerance))

    def without_holes(self) -> Face:
        """without_holes

        Remove all of the holes from this face.

        Returns:
            Face: A new Face instance identical to the original but without any holes.
        """
        if self._wrapped is None:
            raise ValueError("Cannot remove holes from an empty face")

        if not (inner_wires := self.inner_wires()):
            return self

        holeless = copy.deepcopy(self)
        reshaper = BRepTools_ReShape()
        for hole_wire in inner_wires:
            reshaper.Remove(hole_wire.wrapped)
        modified_shape = downcast(reshaper.Apply(self._wrapped))
        # pylint: disable=attribute-defined-outside-init
        holeless.wrapped = TopoDS.Face(modified_shape)
        return holeless

    def wire(self) -> Wire:
        """Return the outerwire, generate a warning if inner_wires present"""
        if self.inner_wires():
            warnings.warn(
                "Found holes, returning outer_wire",
                stacklevel=2,
            )
        return self.outer_wire()

    @overload
    def wrap(
        self,
        planar_shape: Edge,
        surface_loc: Location,
        tolerance: float = 0.001,
        extension_factor: float = 0.1,
    ) -> Edge: ...
    @overload
    def wrap(
        self,
        planar_shape: Wire,
        surface_loc: Location,
        tolerance: float = 0.001,
        extension_factor: float = 0.1,
    ) -> Wire: ...
    @overload
    def wrap(
        self,
        planar_shape: Face,
        surface_loc: Location,
        tolerance: float = 0.001,
        extension_factor: float = 0.1,
    ) -> Face: ...

    def wrap(
        self,
        planar_shape: T,
        surface_loc: Location,
        tolerance: float = 0.001,
        extension_factor: float = 0.1,
    ) -> T:
        """wrap

        Wrap a planar 2D shape onto a 3D surface.

        This method conforms a 2D shape defined on the XY plane (Edge,
        Wire, or Face) to the curvature of a non-planar 3D Face (the
        target surface), starting at a specified surface location. The
        operation attempts to preserve the original edge lengths and
        shape as closely as possible while minimizing the geometric
        distortion that naturally arises when mapping flat geometry onto
        curved surfaces.

        The wrapping process follows the local orientation of the surface
        and progressively fits each edge along the curvature. To help
        ensure continuity, the first and last edges are extended and trimmed
        to close small gaps introduced by distortion. The final shape is tightly
        aligned to the surface geometry.

        This method is useful for applying flat features—such as
        decorative patterns, cutouts, or boundary outlines—onto curved or
        freeform surfaces while retaining their original proportions.

        Args:
            planar_shape (Edge | Wire | Face): flat shape to wrap around surface
            surface_loc (Location): location on surface to wrap
            tolerance (float, optional): maximum allowed error. Defaults to 0.001
            extension_factor (float, optional): amount to extend the wrapped first
                and last edges to allow them to cross. Defaults to 0.1

        Raises:
            ValueError: Invalid planar shape

        Returns:
            Edge | Wire | Face: wrapped shape

        """

        if isinstance(planar_shape, Edge):
            return self._wrap_edge(planar_shape, surface_loc, True, tolerance)
        if isinstance(planar_shape, Wire):
            return self._wrap_wire(
                planar_shape, surface_loc, tolerance, extension_factor
            )
        if isinstance(planar_shape, Face):
            return self._wrap_face(
                planar_shape, surface_loc, tolerance, extension_factor
            )
        raise TypeError(
            f"planar_shape must be of type Edge, Wire, Face not "
            f"{type(planar_shape)}"
        )

    def wrap_faces(
        self,
        faces: Iterable[Face],
        path: Wire | Edge,
        start: float = 0.0,
    ) -> ShapeList[Face]:
        """wrap_faces

        Wrap a sequence of 2D faces onto a 3D surface, aligned along a guiding path.

        This method places multiple planar `Face` objects (defined in the XY plane) onto a
        curved 3D surface (`self`), following a given path (Wire or Edge) that lies on or
        closely follows the surface. Each face is spaced along the path according to its
        original horizontal (X-axis) position, preserving the relative layout of the input
        faces.

        The wrapping process attempts to maintain the shape and size of each face while
        minimizing distortion. Each face is repositioned to the origin, then individually
        wrapped onto the surface starting at a specific point along the path. The face's
        new orientation is defined using the path's tangent direction and the surface normal
        at that point.

        This is particularly useful for placing a series of features—such as embossed logos,
        engraved labels, or patterned tiles—onto a freeform or cylindrical surface, aligned
        along a reference edge or curve.

        Args:
            faces (Iterable[Face]): An iterable of 2D planar faces to be wrapped.
            path (Wire | Edge): A curve on the target surface that defines the alignment
                direction. The X-position of each face is mapped to a relative position
                along this path.
            start (float, optional): The relative starting point on the path (between 0.0
                and 1.0) where the first face should be placed. Defaults to 0.0.

        Returns:
            ShapeList[Face]: A list of wrapped face objects, aligned and conformed to the
                surface.
        """
        path_length = path.length

        face_list = list(faces)
        first_face_min_x = face_list[0].bounding_box().min.X

        # Position each face at the origin and wrap onto surface
        wrapped_faces: ShapeList[Face] = ShapeList()
        for face in face_list:
            bbox = face.bounding_box()
            face_center_x = (bbox.min.X + bbox.max.X) / 2
            delta_x = face_center_x - first_face_min_x
            relative_position_on_wire = start + delta_x / path_length
            path_position = path.position_at(relative_position_on_wire)
            surface_location = Location(
                Plane(
                    path_position,
                    x_dir=path.tangent_at(relative_position_on_wire),
                    z_dir=self.normal_at(path_position),
                )
            )
            assert isinstance(face.position, Vector)
            face.position -= (delta_x, 0, 0)  # Shift back to origin
            wrapped_face = Face.wrap(self, face, surface_location)
            wrapped_faces.append(wrapped_face)

        return wrapped_faces

    def _uv_bounds(self) -> tuple[float, float, float, float]:
        """Return the u min, u max, v min, v max values"""
        return BRepTools.UVBounds_s(self.wrapped)

    def _wrap_face(
        self: Face,
        planar_face: Face,
        surface_loc: Location,
        tolerance: float = 0.001,
        extension_factor: float = 0.1,
    ) -> Face:
        """_wrap_face

        Helper method of wrap that handles wrapping faces on surfaces.

        Args:
            planar_face (Face): flat face to wrap around surface
            surface_loc (Location): location on surface to wrap
            tolerance (float, optional): maximum allowed error. Defaults to 0.001
            extension_factor (float, optional): amount to extend wrapped first
                and last edges to allow them to cross. Defaults to 0.1

        Returns:
            Face: wrapped face
        """
        wrapped_perimeter = self._wrap_wire(
            planar_face.outer_wire(), surface_loc, tolerance, extension_factor
        )
        wrapped_holes = [
            self._wrap_wire(w, surface_loc, tolerance, extension_factor)
            for w in planar_face.inner_wires()
        ]
        wrapped_face = Face.make_surface(
            wrapped_perimeter,
            surface_points=[surface_loc.position],
            interior_wires=wrapped_holes,
        )

        # Potentially flip the wrapped face to match the surface
        surface_normal = surface_loc.z_axis.direction
        wrapped_normal = wrapped_face.normal_at(surface_loc.position)
        if surface_normal.dot(wrapped_normal) < 0:  # are they opposite?
            wrapped_face = -wrapped_face  # pylint: disable=invalid-unary-operand-type
        return wrapped_face

    def _wrap_wire(
        self: Face,
        planar_wire: Wire,
        surface_loc: Location,
        tolerance: float = 0.001,
        extension_factor: float = 0.1,
    ) -> Wire:
        """_wrap_wire

        Helper method of wrap that handles wrapping wires on surfaces.

        Args:
            planar_wire (Wire): wire to wrap around surface
            surface_loc (Location): location on surface to wrap
            tolerance (float, optional): maximum allowed error. Defaults to 0.001
            extension_factor (float, optional): amount to extend wrapped first
                and last edges to allow them to cross. Defaults to 0.1

        Raises:
            RuntimeError: wrapped wire is not valid

        Returns:
            Wire: wrapped wire
        """
        #
        # Part 1: Preparation
        #
        surface_point = surface_loc.position
        surface_x_direction = surface_loc.x_axis.direction
        surface_geometry = BRep_Tool.Surface_s(self.wrapped)

        if len(planar_wire.edges()) == 1:
            planar_edge = planar_wire.edge()
            assert planar_edge is not None
            return Wire([self._wrap_edge(planar_edge, surface_loc, True, tolerance)])

        planar_edges = planar_wire.order_edges()
        wrapped_edges: list[Edge] = []

        # Need to keep track of the separation between adjacent edges
        first_start_point = None

        #
        # Part 2: Wrap the planar wires on the surface by creating a spline
        #         through points cast from the planar onto the surface.
        #
        # If the wire doesn't start at the origin, create an wrapped construction line
        # to get to the beginning of the first edge
        if planar_edges[0].position_at(0) == Vector(0, 0, 0):
            edge_surface_point = surface_point
            planar_edge_end_point = Vector(0, 0, 0)
        else:
            construction_line = Edge.make_line(
                Vector(0, 0, 0), planar_edges[0].position_at(0)
            )
            wrapped_construction_line: Edge = self._wrap_edge(
                construction_line, surface_loc, True, tolerance
            )
            edge_surface_point = wrapped_construction_line.position_at(1)
            planar_edge_end_point = planar_edges[0].position_at(0)
        edge_surface_location = Location(
            Plane(
                edge_surface_point,
                x_dir=surface_x_direction,
                z_dir=self.normal_at(edge_surface_point),
            )
        )

        # Wrap each edge and add them to the wire builder
        for planar_edge in planar_edges:
            local_planar_edge = planar_edge.translate(-planar_edge_end_point)
            wrapped_edge: Edge = self._wrap_edge(
                local_planar_edge, edge_surface_location, True, tolerance
            )
            edge_surface_point = wrapped_edge.position_at(1)
            edge_surface_location = Location(
                Plane(
                    edge_surface_point,
                    x_dir=surface_x_direction,
                    z_dir=self.normal_at(edge_surface_point),
                )
            )
            planar_edge_end_point = planar_edge.position_at(1)
            if first_start_point is None:
                first_start_point = wrapped_edge.position_at(0)
            wrapped_edges.append(wrapped_edge)

        # For open wires we're finished
        if not planar_wire.is_closed:
            return Wire(wrapped_edges)

        #
        # Part 3: The first and last edges likely don't meet at this point due to
        #         distortion caused by following the surface, so we'll need to join
        #         them.
        #

        # Extend the first and last edge so that they cross
        first_edge, first_curve = wrapped_edges[0]._extend_spline(
            True, surface_geometry, extension_factor
        )
        last_edge, last_curve = wrapped_edges[-1]._extend_spline(
            False, surface_geometry, extension_factor
        )

        # Trim the extended edges at their intersection point
        extrema = GeomAPI_ExtremaCurveCurve(first_curve, last_curve)
        if extrema.NbExtrema() < 1:
            raise RuntimeError(
                "Extended first/last edges do not intersect; increase extension."
            )
        param_first, param_last = extrema.Parameters(1)

        u_start_first: float = first_edge.param_at(0)
        u_end_first: float = first_edge.param_at(1)
        new_start = (param_first - u_start_first) / (u_end_first - u_start_first)
        trimmed_first = first_edge.trim(new_start, 1.0)

        u_start_last: float = last_edge.param_at(0)
        u_end_last: float = last_edge.param_at(1)
        new_end = (param_last - u_start_last) / (u_end_last - u_start_last)
        trimmed_last = last_edge.trim(0.0, new_end)

        # Replace the first and last edges with their modified versions
        wrapped_edges[0] = trimmed_first
        wrapped_edges[-1] = trimmed_last

        #
        # Part 4: Build a wire from the edges and fix it to close gaps
        #
        closing_error = (
            trimmed_first.position_at(0) - trimmed_last.position_at(1)
        ).length
        wire_builder = BRepBuilderAPI_MakeWire()
        combined_edges = TopTools_ListOfShape()
        for edge in wrapped_edges:
            combined_edges.Append(edge.wrapped)
        wire_builder.Add(combined_edges)
        wire_builder.Build()
        raw_wrapped_wire = wire_builder.Wire()
        wire_fixer = ShapeFix_Wire()
        wire_fixer.SetPrecision(2 * closing_error)  # enable fixing start/end gaps
        wire_fixer.Load(raw_wrapped_wire)
        wire_fixer.FixReorder()
        wire_fixer.FixConnected()
        wrapped_wire = Wire(wire_fixer.Wire())

        #
        # Part 5: Validate
        #
        if not wrapped_wire.is_valid:
            raise RuntimeError("wrapped wire is not valid")

        return wrapped_wire


class Shell(Mixin2D[TopoDS_Shell]):
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
            if not obj:
                raise ValueError("Can't create a Shell from empty Face")
            builder = BRep_Builder()
            shell = TopoDS_Shell()
            builder.MakeShell(shell)
            builder.Add(shell, obj.wrapped)
            obj = shell
        elif isinstance(obj, Iterable):
            try:
                obj = TopoDS.Shell(_sew_topods_faces([f.wrapped for f in obj]))
            except Standard_TypeMismatch as exc:
                raise TypeError("Unable to create Shell, invalid input type") from exc

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
            assert calc_function is not None
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
        return Shell(TopoDS.Shell(_extrude_topods_shape(obj.wrapped, direction)))

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
        return cls(TopoDS.Shell(_make_loft(objs, False, ruled)))

    @classmethod
    def revolve(
        cls,
        profile: Curve | Wire,
        angle: float,
        axis: Axis,
    ) -> Face:
        """sweep

        Revolve a 1D profile around an axis.

        Args:
            profile (Curve | Wire): the object to revolve
            angle (float): the angle to revolve through
            axis (Axis): rotation Axis

        Returns:
            Shell: resulting shell
        """
        profile = Wire(profile.edges())
        revol_builder = BRepPrimAPI_MakeRevol(
            profile.wrapped, axis.wrapped, angle * DEG2RAD, True
        )

        return cls(TopoDS.Shell(revol_builder.Shape()))

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
        result = Shell(TopoDS.Shell(builder.Shape()))
        if SkipClean.clean:
            result = result.clean()

        return result

    # ---- Instance Methods ----

    def center(self) -> Vector:
        """Center of mass of the shell"""
        properties = GProp_GProps()
        BRepGProp.LinearProperties_s(self.wrapped, properties)
        return Vector(properties.CentreOfMass())

    def location_at(
        self,
        surface_point: VectorLike,
        *,
        x_dir: VectorLike | None = None,
    ) -> Location:
        """location_at

        Get the location (origin and orientation) on the surface of the shell.

        Args:
            surface_point (VectorLike): A 3D point near the surface.
            x_dir (VectorLike, optional): Direction for the local X axis. If not given,
                the tangent in the U direction is used.

        Returns:
            Location: A full 3D placement at the specified point on the shell surface.
        """
        # Find the closest Face and get the location from it
        face = self.faces().sort_by(lambda f: f.distance_to(surface_point))[0]
        return face.location_at(surface_point, x_dir=x_dir)


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
