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
import warnings

from typing import overload, TYPE_CHECKING

from collections.abc import Iterable
from typing_extensions import Self

import OCP.TopAbs as ta
from OCP.BRep import BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Shape, TopoDS_Vertex, TopoDS_Edge
from OCP.gp import gp_Pnt
from build123d.geometry import Matrix, Vector, VectorLike, Location, Axis, Plane
from build123d.build_enums import Keep
from .shape_core import Shape, ShapeList, TrimmingTool, downcast, shapetype


if TYPE_CHECKING:  # pragma: no cover
    from .one_d import Edge, Wire  # pylint: disable=R0801


class Vertex(Shape[TopoDS_Vertex]):
    """A Vertex in build123d represents a zero-dimensional point in the topological
    data structure. It marks the endpoints of edges within a 3D model, defining precise
    locations in space. Vertices play a crucial role in defining the geometry of objects
    and the connectivity between edges, facilitating accurate representation and
    manipulation of 3D shapes. They hold coordinate information and are essential
    for constructing complex structures like wires, faces, and solids."""

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
        self.vertex_index = 0

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
        pnt = BRep_Tool.Pnt_s(self.wrapped)
        self.X, self.Y, self.Z = pnt.X(), pnt.Y(), pnt.Z()

    # ---- Properties ----

    @property
    def _dim(self) -> int:
        return 0

    @property
    def volume(self) -> float:
        """volume - the volume of this Vertex, which is always zero"""
        return 0.0

    # ---- Class Methods ----

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Self:
        "Returns the right type of wrapper, given a OCCT object"

        # define the shape lookup table for casting
        constructor_lut = {
            ta.TopAbs_VERTEX: Vertex,
        }

        shape_type = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        return constructor_lut[shape_type](TopoDS.Vertex(obj))

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
            if other.intersect(self.center()):
                return ShapeList([self])
            return None
        elif isinstance(other, Plane):
            # Check if vertex lies on the plane
            if other.contains(self.center(), tolerance):
                return ShapeList([self])
            return None

        if isinstance(other, Vertex):
            # Vertex + Vertex: check distance
            if self.distance_to(other) <= tolerance:
                return ShapeList([self])
            return None

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

    def to_tuple(self) -> tuple[float, float, float]:
        """Return vertex as three tuple of floats"""
        warnings.warn(
            "to_tuple is deprecated and will be removed in a future version. "
            "Use 'tuple(Vertex)' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        geom_point = BRep_Tool.Pnt_s(self.wrapped)
        return (geom_point.X(), geom_point.Y(), geom_point.Z())

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

    if topods_edge1 is None or topods_edge2 is None:
        raise ValueError("edge is empty")

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
