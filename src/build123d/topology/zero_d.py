"""
build123d topology

name: zero_d.py
by:   Gumyr
date: January 07, 2025

desc:

This module provides the foundational implementation for zero-dimensional geometry in the build123d
CAD system, focusing on the `Vertex` class and its related operations. A `Vertex` represents a
single point in 3D space, serving as the cornerstone for more complex geometric structures such as
edges, wires, and faces. It is directly integrated with the OpenCascade kernel, enabling precise
modeling and manipulation of 3D objects.

Key Features:
- **Vertex Class**:
  - Supports multiple constructors, including Cartesian coordinates, iterable inputs, and
    OpenCascade `TopoDS_Vertex` objects.
  - Offers robust arithmetic operations such as addition and subtraction with other vertices,
    vectors, or tuples.
  - Provides utility methods for transforming vertices, converting to tuples, and iterating over
    coordinate components.

- **Intersection Utilities**:
  - Includes `topo_explore_common_vertex`, a utility to identify shared vertices between edges,
    facilitating advanced topological queries.

- **Integration with Shape Hierarchy**:
  - Extends the `Shape` base class, inheriting essential features such as transformation matrices
    and bounding box computations.

This module plays a critical role in defining precise geometric points and their interactions,
serving as the building block for complex 3D models in the build123d library.

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

import itertools

from typing import ClassVar, overload, TYPE_CHECKING

from collections.abc import Iterable

import OCP.TopAbs as ta
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve2d
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepTools import BRepTools
from OCP.BRepTopAdaptor import BRepTopAdaptor_FClass2d
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Vertex, TopoDS_Edge
from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Vec2d
from build123d.geometry import (
    TOLERANCE,
    Matrix,
    Vector,
    VectorLike,
    Location,
    Axis,
    Plane,
)
from build123d.build_enums import Convexity, Keep, Unit
from .shape_core import Shape, ShapeList, TrimmingTool, downcast, find_same_topods

if TYPE_CHECKING:  # pragma: no cover
    from .one_d import Edge, Wire  # pylint: disable=R0801


class Vertex(Shape[TopoDS_Vertex]):
    """A Vertex in build123d represents a zero-dimensional point in the topological
    data structure. It marks the endpoints of edges within a 3D model, defining precise
    locations in space. Vertices play a crucial role in defining the geometry of objects
    and the connectivity between edges, facilitating accurate representation and
    manipulation of 3D shapes. They hold coordinate information and are essential
    for constructing complex structures like wires, faces, and solids."""

    build123d_type: ClassVar[str] = "Vertex"
    order = 0.0
    # ---- Constructor ----

    @overload
    def __init__(self):  # pragma: no cover
        """Default Vertext at the origin"""

    @overload
    def __init__(self, ocp_vx: TopoDS_Vertex):  # pragma: no cover
        """Vertex from OCCT TopoDS_Vertex object"""

    @overload
    def __init__(self, X: float, Y: float, Z: float):  # pragma: no cover
        """Vertex from three float values"""

    @overload
    def __init__(self, v: Iterable[float]):
        """Vertex from Vector or other iterators"""

    def __init__(self, *args, **kwargs):
        ocp_vx = kwargs.pop("ocp_vx", None)
        v = kwargs.pop("v", None)
        x = kwargs.pop("X", 0)
        y = kwargs.pop("Y", 0)
        z = kwargs.pop("Z", 0)

        # Handle unexpected kwargs
        if kwargs:
            raise ValueError(f"Unexpected argument(s): {', '.join(kwargs.keys())}")

        if args:
            if isinstance(args[0], TopoDS_Vertex):
                ocp_vx = args[0]
            elif isinstance(args[0], Iterable):
                v = args[0]
            else:
                x, y, z = args[:3] + (0,) * (3 - len(args))

        if v is not None:
            x, y, z = itertools.islice(itertools.chain(v, [0, 0, 0]), 3)

        ocp_vx = (
            downcast(BRepBuilderAPI_MakeVertex(gp_Pnt(x, y, z)).Vertex())
            if ocp_vx is None
            else ocp_vx
        )

        super().__init__(ocp_vx)

    # ---- Properties ----

    @property
    def _dim(self) -> int:
        return 0

    @property
    def volume(self) -> float:
        """volume - the volume of this Vertex, which is always zero"""
        return 0.0

    def mass(self, mass_unit: Unit = Unit.G, length_unit: Unit = Unit.MM) -> float:
        """mass - the mass of this Vertex, which is always zero"""
        del mass_unit, length_unit
        return 0.0

    @property
    def convexity(self) -> Convexity:
        """How the shape this vertex was selected from sits around it.

        Selected through a face, as ``face.vertices()`` or
        ``face.edges()[0].vertices()`` does, the vertex is a corner of that
        face: ``CONVEX`` at the corner of a plate, ``CONCAVE`` at the corner of
        a slot or the step in an L, ``SMOOTH`` where two edges meet in line.
        The corner is read in the face's own parameters, so a corner on a
        curved face classifies the same way as one on a flat face.

        Selected straight off a solid or shell, the vertex is classified by the
        edges meeting there: ``CONVEX`` where every crease is convex, as at the
        corner of a box, ``CONCAVE`` where every crease is concave, as at the
        bottom corner of a pocket, and ``SADDLE`` where both kinds meet, as at
        the inner corner of a step. Smooth edges do not count. See
        :class:`~build_enums.Convexity`.

        Raises:
            ValueError: the vertex has no ``topo_parent``, or its face or edges
                cannot be classified - a seam vertex has no single corner in
                its face's parameters, for instance
        """
        face = self._owning_face()
        if face is not None:
            return self._corner_convexity(face)
        return self._crease_convexity()

    def _owning_face(self) -> TopoDS_Face | None:
        """The innermost face this vertex was selected through, if any."""
        for step in reversed(self.topo_path):
            if step.wrapped is not None and step.wrapped.ShapeType() == ta.TopAbs_FACE:
                return TopoDS.Face(step.wrapped)
        return None

    def _face_tangents(self, face: TopoDS_Face) -> list[tuple[float, float]]:
        """Unit directions leading away from this vertex in the face's uv.

        The boundary is followed in parameter space rather than in three
        dimensions so that a corner on a curved face reads the same as one on
        a flat face.
        """
        here = BRep_Tool.Parameters_s(self.wrapped, face)
        seen: list[TopoDS_Edge] = []
        directions: list[tuple[float, float]] = []
        explorer = TopExp_Explorer(face, ta.TopAbs_EDGE)
        while explorer.More():
            edge = TopoDS.Edge(explorer.Current())
            explorer.Next()
            if any(edge.IsSame(other) for other in seen):
                continue  # a seam edge is met once per side
            seen.append(edge)
            curve = BRepAdaptor_Curve2d(edge, face)
            for param, sign in (
                (curve.FirstParameter(), 1.0),
                (curve.LastParameter(), -1.0),
            ):
                end = curve.Value(param)
                if (end.X() - here.X()) ** 2 + (end.Y() - here.Y()) ** 2 > TOLERANCE:
                    continue
                point, tangent = gp_Pnt2d(), gp_Vec2d()
                curve.D1(param, point, tangent)
                length = (tangent.X() ** 2 + tangent.Y() ** 2) ** 0.5
                if length > 0:
                    directions.append(
                        (sign * tangent.X() / length, sign * tangent.Y() / length)
                    )
        return directions

    def _corner_convexity(self, face: TopoDS_Face) -> Convexity:
        """Which way the face's boundary turns at this corner.

        The two edges leaving the vertex bound a wedge of less than half a
        turn, and their bisector points into it. Material there and the corner
        is convex; material on the other side and it is concave.
        """
        directions = self._face_tangents(face)
        if len(directions) != 2:
            raise ValueError(
                f"{len(directions)} edge end(s) meet this vertex on the face, "
                "expected 2 - a corner is where exactly two of them do"
            )
        (first_u, first_v), (second_u, second_v) = directions
        bisector = (first_u + second_u, first_v + second_v)
        span = (bisector[0] ** 2 + bisector[1] ** 2) ** 0.5
        if span < TOLERANCE:
            return Convexity.SMOOTH  # the boundary runs straight through

        u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
        step = 1e-4 * ((u_max - u_min) ** 2 + (v_max - v_min) ** 2) ** 0.5 / span
        here = BRep_Tool.Parameters_s(self.wrapped, face)
        probe = gp_Pnt2d(here.X() + bisector[0] * step, here.Y() + bisector[1] * step)
        inside = BRepTopAdaptor_FClass2d(face, TOLERANCE).Perform(probe) == ta.TopAbs_IN
        return Convexity.CONVEX if inside else Convexity.CONCAVE

    def _crease_convexity(self) -> Convexity:
        """Classify by the creases meeting at this vertex of a solid or shell."""
        parent = self.topo_parent
        if parent is None or parent.wrapped is None:
            raise ValueError(
                "this vertex was not selected from a shape, so there is nothing "
                "to classify it against - take it from a face or solid"
            )
        vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            parent.wrapped, ta.TopAbs_VERTEX, ta.TopAbs_EDGE, vertex_edge_map
        )
        own = find_same_topods(
            self.wrapped,
            (vertex_edge_map.FindKey(i + 1) for i in range(vertex_edge_map.Extent())),
        )
        if own is None:
            raise ValueError("this vertex is not part of its topo_parent")

        kinds: set[Convexity] = set()
        for topods_edge in vertex_edge_map.FindFromKey(own):
            edge = Shape.cast(topods_edge)
            edge.topo_path = self.topo_path
            kinds.add(edge.convexity)
        turning = kinds - {Convexity.SMOOTH}
        if not turning:
            return Convexity.SMOOTH
        if len(turning) == 1:
            return turning.pop()
        return Convexity.SADDLE

    @property
    def X(self) -> float:
        """The X coordinate of this Vertex, including its current Location."""
        return BRep_Tool.Pnt_s(self.wrapped).X()

    @property
    def Y(self) -> float:
        """The Y coordinate of this Vertex, including its current Location."""
        return BRep_Tool.Pnt_s(self.wrapped).Y()

    @property
    def Z(self) -> float:
        """The Z coordinate of this Vertex, including its current Location."""
        return BRep_Tool.Pnt_s(self.wrapped).Z()

    # ---- Class Methods ----

    @classmethod
    def extrude(cls, obj: Shape, direction: VectorLike) -> Vertex:
        """extrude - invalid operation for Vertex"""
        raise NotImplementedError("Vertices can't be created by extrusion")

    def _intersect(
        self,
        other: Shape | Vector | Location | Axis | Plane,
        tolerance: float = 1e-6,
        include_touched: bool = False,
    ) -> ShapeList | None:
        """Single-object intersection for Vertex.

        For a vertex (0D), intersection means the vertex lies on/in the other shape.

        Args:
            other: Shape or geometry object to intersect with
            tolerance: tolerance for intersection detection
            include_touched: if True, include boundary contacts
                (only relevant when Solids are involved)
        """
        # Convert geometry objects to Vertex
        if isinstance(other, Vector):
            other = Vertex(other)
        elif isinstance(other, Location):
            other = Vertex(other.position)
        elif isinstance(other, Axis):
            # Check if vertex lies on the axis
            return ShapeList([self]) if other.intersect(self.center()) else None
        elif isinstance(other, Plane):
            # Check if vertex lies on the plane
            return (
                ShapeList([self]) if other.contains(self.center(), tolerance) else None
            )

        if isinstance(other, Vertex):
            # Vertex + Vertex: check distance
            return ShapeList([self]) if self.distance_to(other) <= tolerance else None

        # Delegate to higher-dimensional shape (including Compound)
        return other._intersect(self, tolerance, include_touched)

    # ---- Instance Methods ----

    def __add__(  # type: ignore
        self, other: Vertex | Vector | tuple[float, float, float]
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

    def __and__(self, *args, **kwargs):
        """intersect operator +"""
        raise NotImplementedError("Vertices can't be intersected")

    def __iter__(self):
        """Initialize to beginning"""
        return iter((self.X, self.Y, self.Z))

    def __repr__(self) -> str:
        """To String

        Convert Vertex to String for display

        Returns:
            Vertex as String
        """
        return f"Vertex({self.X}, {self.Y}, {self.Z})"

    def __sub__(self, other: Vertex | Vector | tuple) -> Vertex:  # type: ignore
        """Subtract

        Subtract a Vertex with a Vertex, Vector or Tuple from self

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

    def center(self) -> Vector:
        """The center of a vertex is itself!"""
        return Vector(self)

    def split(self, tool: TrimmingTool, keep: Keep = Keep.TOP):
        """split - not implemented"""
        raise NotImplementedError("Vertices cannot be split.")

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

    def vertex(self) -> Vertex:
        """Return the Vertex"""
        return self

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this Shape"""
        return ShapeList((self,))  # Vertex is an iterable


def topo_explore_common_vertex(
    edge1: Edge | TopoDS_Edge, edge2: Edge | TopoDS_Edge
) -> Vertex | None:
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
                return Vertex(TopoDS.Vertex(vertex1))  # Common vertex found

            explorer2.Next()
        vert_exp.Next()

    return None  # No common vertex found


Shape.register_shape_constructor(ta.TopAbs_VERTEX, Vertex)
Shape.register_geometry_constructor(Vector, Vertex)
Shape.register_geometry_constructor(
    Location, lambda location: Vertex(location.position)
)
