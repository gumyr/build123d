"""
build123d topology

name: shape_core.py
by:   Gumyr
date: January 07, 2025

desc:

This module defines the foundational classes and methods for the build123d CAD library, enabling
detailed geometric operations and 3D modeling capabilities. It provides a hierarchy of classes
representing various geometric entities like vertices, edges, wires, faces, shells, solids, and
compounds. These classes are designed to work seamlessly with the OpenCascade Python bindings,
leveraging its robust CAD kernel.

Key Features:
- **Shape Base Class:** Implements core functionalities such as transformations (rotation,
  translation, scaling), geometric queries, and boolean operations (cut, fuse, intersect).
- **Custom Utilities:** Includes helper classes like `ShapeList` for advanced filtering, sorting,
  and grouping of shapes, and `GroupBy` for organizing shapes by specific criteria.
- **Type Safety:** Extensive use of Python typing features ensures clarity and correctness in type
  handling.
- **Advanced Geometry:** Supports operations like finding intersections, computing bounding boxes,
  projecting faces, and generating triangulated meshes.

The module is designed for extensibility, enabling developers to build complex 3D assemblies and
perform detailed CAD operations programmatically while maintaining a clean and structured API.

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
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from functools import reduce
from math import inf
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Literal,
    Optional,
    Protocol,
    SupportsIndex,
    TypeVar,
    Union,
)
from typing import cast as tcast
from typing import overload

import numpy as np
import OCP.GeomAbs as ga
import OCP.TopAbs as ta
from anytree import NodeMixin, RenderTree
from IPython.lib.pretty import RepresentationPrinter, pretty
from OCP.Bnd import Bnd_OBB
from OCP.BOPAlgo import BOPAlgo_GlueEnum
from OCP.BRep import BRep_TEdge, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.GeomAdaptor import GeomAdaptor_Curve
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
    BRepBuilderAPI_GTransform,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeVertex,
    BRepBuilderAPI_RightCorner,
    BRepBuilderAPI_RoundCorner,
    BRepBuilderAPI_Sewing,
    BRepBuilderAPI_Transform,
    BRepBuilderAPI_Transformed,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCP.BRepTools import BRepTools
from OCP.gce import gce_MakeLin
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.GeomLib import GeomLib_IsPlanarSurface
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec, gp_XYZ
from OCP.GProp import GProp_GProps
from OCP.ShapeAnalysis import ShapeAnalysis_Curve
from OCP.ShapeCustom import ShapeCustom, ShapeCustom_RestrictionParameters
from OCP.ShapeFix import ShapeFix_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.Standard import Standard_Failure
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Builder,
    TopoDS_Compound,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Iterator,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Vertex,
    TopoDS_Wire,
)
from OCP.TopTools import (
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_ListOfShape,
    TopTools_ShapeMapHasher,
)
from typing_extensions import Self

from bd_materials import FinishedMaterial, resolve as resolve_material

from build123d.build_constants import UNITS_PER_KILOGRAM, UNITS_PER_METER
from build123d.build_enums import CenterOf, GeomType, Keep, SortBy, Transition, Unit
from build123d.geometry import (
    DEG2RAD,
    TOLERANCE,
    Axis,
    BoundBox,
    Color,
    ColorLike,
    Location,
    Matrix,
    OrientedBoundBox,
    Plane,
    Vector,
    VectorLike,
    apply_location_like,
    logger,
)
from build123d.pack_utils import _pack2d

if TYPE_CHECKING:  # pragma: no cover
    from build123d.build_part import BuildPart  # pylint: disable=R0801

    from .composite import Compound  # pylint: disable=R0801
    from .one_d import Edge, Wire  # pylint: disable=R0801
    from .three_d import Solid  # pylint: disable=R0801
    from .two_d import Face, Shell  # pylint: disable=R0801
    from .zero_d import Vertex  # pylint: disable=R0801

Shapes = Literal["Vertex", "Edge", "Wire", "Face", "Shell", "Solid", "Compound"]
TrimmingTool = Union[Plane, "Shell", "Face"]
TOPODS = TypeVar("TOPODS", bound=TopoDS_Shape)
CalcFn = Callable[[TopoDS_Shape, GProp_GProps], None]
CompositeFactory = Callable[[Iterable["Shape"]], "Shape"]
ShapeConstructor = Callable[[Any], "Shape"]
GeometryConstructor = Callable[[Any], "Shape"]


class Shape(NodeMixin, Generic[TOPODS]):
    """Shape

    Base class for all CAD objects such as Edge, Face, Solid, etc.

    Args:
        obj (TopoDS_Shape, optional): OCCT object. Defaults to None.
        label (str, optional): Defaults to ''.
        color (ColorLike, optional): Defaults to None.
        parent (Compound, optional): assembly parent. Defaults to None.

    Attributes:
        wrapped (TopoDS_Shape): the OCP object
        label (str): user assigned label
        color (Color): object color
        joints (dict[str:Joint]): dictionary of joints bound to this object (Solid only)
        children (Shape): list of assembly children of this object (Compound only)
        topo_parent (Shape): assembly parent of this object

    """

    build123d_type: ClassVar[str] = "Shape"
    composite_factories: ClassVar[dict[int | None, CompositeFactory]] = {}
    shape_constructors: ClassVar[dict[TopAbs_ShapeEnum, ShapeConstructor]] = {}
    geometry_constructors: ClassVar[dict[type, GeometryConstructor]] = {}

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

    shape_properties_LUT: dict[TopAbs_ShapeEnum, CalcFn | None] = {
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
        ta.TopAbs_VERTEX: TopoDS.Vertex,
        ta.TopAbs_EDGE: TopoDS.Edge,
        ta.TopAbs_WIRE: TopoDS.Wire,
        ta.TopAbs_FACE: TopoDS.Face,
        ta.TopAbs_SHELL: TopoDS.Shell,
        ta.TopAbs_SOLID: TopoDS.Solid,
        ta.TopAbs_COMPOUND: TopoDS.Compound,
        ta.TopAbs_COMPSOLID: TopoDS.CompSolid,
    }

    geom_LUT_EDGE: dict[ga.GeomAbs_CurveType, GeomType] = {
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
    geom_LUT_FACE: dict[ga.GeomAbs_SurfaceType, GeomType] = {
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

    _color: Color | None
    _material: FinishedMaterial | None

    class _DisplayNode(NodeMixin):
        """Used to create anytree structures from TopoDS_Shapes"""

        def __init__(
            self,
            label: str = "",
            address: int | None = None,
            position: Vector | Location | None = None,
            parent: Shape._DisplayNode | None = None,
        ):
            self.label = label
            self.address = address
            self.position = position
            self.parent = parent
            self.children: list[Shape] = []

    _ordered_shapes = [
        TopAbs_ShapeEnum.TopAbs_COMPOUND,
        TopAbs_ShapeEnum.TopAbs_COMPSOLID,
        TopAbs_ShapeEnum.TopAbs_SOLID,
        TopAbs_ShapeEnum.TopAbs_SHELL,
        TopAbs_ShapeEnum.TopAbs_FACE,
        TopAbs_ShapeEnum.TopAbs_WIRE,
        TopAbs_ShapeEnum.TopAbs_EDGE,
        TopAbs_ShapeEnum.TopAbs_VERTEX,
    ]
    # ---- Constructor ----

    def __init__(
        self,
        obj: TopoDS_Shape | None = None,
        label: str = "",
        color: ColorLike | None = None,
        parent: Compound | None = None,
    ):
        self._wrapped: TOPODS | None = (
            tcast(Optional[TOPODS], downcast(obj)) if obj is not None else None
        )
        self.for_construction = False
        self.label = label
        self.color = color
        self._material = None

        # parent must be set following children as post install accesses children
        self.parent = parent

        # Extracted objects like Vertices and Edges may need to know where they came from
        self.topo_parent: Shape | None = None

    # ---- Properties ----

    @property
    def wrapped(self):
        """OCP TopoDS object"""
        assert self._wrapped
        return self._wrapped

    @wrapped.setter
    def wrapped(self, shape: TOPODS):
        self._wrapped = shape

    def __bool__(self):
        return self._wrapped is not None

    @property
    @abstractmethod
    def _dim(self) -> int | None:
        """Dimension of the object"""

    @property
    def area(self) -> float:
        """area -the surface area of all faces in this Shape"""
        if self._wrapped is None:
            return 0.0
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(self.wrapped, properties)

        return properties.Mass()

    @property
    def color(self) -> None | Color:
        """Get the shape's color.  If it's None, get the color of the nearest
        ancestor, assign it to this Shape and return this value."""
        # Find the correct color for this node
        if self._color is None:
            # Find parent color
            current_node: Compound | Shape | None = self
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

    @color.setter
    def color(self, value: ColorLike | None) -> None:
        """Set the shape's color"""
        self._color = Color(value) if value is not None else None

    @property
    def material(self) -> None | FinishedMaterial:
        """Get the shape's material.  If it's None, get the material of the nearest
        ancestor, assign it to this Shape and return this value."""
        # Find the correct material for this node
        node_material = None
        if self._material is None:
            # Find parent material
            current_node: Compound | Shape | None = self
            while current_node is not None:
                if current_node._material is not None:
                    node_material = current_node._material
                    break
                current_node = current_node.parent
        else:
            node_material = self._material
        self._material = node_material  # Set the node's material for next time
        return node_material

    @material.setter
    def material(self, value: FinishedMaterial | str | None) -> None:
        """Set the shape's material"""
        if value is None:
            self._material = None
        elif isinstance(value, FinishedMaterial):
            self._material = value
        elif isinstance(value, str):
            self._material = resolve_material(value)
        else:
            raise TypeError(
                f"Non supported type {type(value).__name__}, "
                "need FinishedMaterial, str or None"
            )

        if self._material is not None and self._material.pbr is not None:
            color = self._material.pbr.interpolate_color()
            if color:
                self.color = color

    @property
    def geom_type(self) -> GeomType:
        """Gets the underlying geometry type.

        Returns:
            GeomType: The geometry type of the shape

        """
        if self._wrapped is None:
            raise ValueError("Cannot determine geometry type of an empty shape")

        shape: TopAbs_ShapeEnum = shapetype(self.wrapped)

        if shape == ta.TopAbs_EDGE:
            geom = Shape.geom_LUT_EDGE[
                BRepAdaptor_Curve(tcast(TopoDS_Edge, self.wrapped)).GetType()
            ]
        elif shape == ta.TopAbs_FACE:
            geom = Shape.geom_LUT_FACE[
                BRepAdaptor_Surface(tcast(TopoDS_Face, self.wrapped)).GetType()
            ]
        else:
            geom = GeomType.OTHER

        return geom

    @property
    def is_manifold(self) -> bool:
        """is_manifold

        Check if each edge in the given Shape has exactly two faces associated with it
        (skipping degenerate edges). If so, the shape is manifold.

        Returns:
            bool: is the shape manifold or water tight
        """
        # Extract one or more (if a Compound) shape from self
        if self._wrapped is None:
            return False
        shape_stack = get_top_level_topods_shapes(self.wrapped)

        while shape_stack:
            shape = shape_stack.pop(0)

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
                edge = TopoDS.Edge(shape_map.FindKey(i + 1))

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
                    return False

        return True

    @property
    def is_null(self) -> bool:
        """Returns true if this shape is null. In other words, it references no
        underlying shape with the potential to be given a location and an
        orientation.
        """
        return self._wrapped is None or self.wrapped.IsNull()

    @property
    def is_valid(self) -> bool:
        """Returns True if no defect is detected on the shape S or any of its
        subshapes. See the OCCT docs on BRepCheck_Analyzer::IsValid for a full
        description of what is checked.
        """
        if self._wrapped is None:
            return True
        chk = BRepCheck_Analyzer(self.wrapped)
        chk.SetParallel(True)
        return chk.IsValid()

    @property
    def global_location(self) -> Location:
        """
        The location of this Shape relative to the global coordinate system.

        This property computes the composite transformation by traversing the
        hierarchy from the root of the assembly to this node, combining the
        location of each ancestor. It reflects the absolute position and
        orientation of the shape in world space, even when the shape is deeply
        nested within an assembly.

        Note:
            This is only meaningful when the Shape is part of an assembly tree
            where parent-child relationships define relative placements.
        """
        return reduce(lambda loc, n: loc * n.location, self.path, Location())

    @property
    def location(self) -> Location:
        """Get this Shape's Location"""
        if self._wrapped is None:
            raise ValueError("Can't find the location of an empty shape")
        return Location(self.wrapped.Location())

    @location.setter
    def location(self, value: Location):
        """Set Shape's Location to value"""
        if self.wrapped is not None:
            self.wrapped.Location(value.wrapped)

    @property
    def matrix_of_inertia(self) -> list[list[float]]:
        """
        Compute the inertia matrix (moment of inertia tensor) of the shape.

        The inertia matrix represents how the mass of the shape is distributed
        with respect to its reference frame. It is a 3×3 symmetric tensor that
        describes the resistance of the shape to rotational motion around
        different axes.

        Returns:
            list[list[float]]: A 3×3 nested list representing the inertia matrix.
            The elements of the matrix are given as:

            | Ixx  Ixy  Ixz |
            | Ixy  Iyy  Iyz |
            | Ixz  Iyz  Izz |

            where:
            - Ixx, Iyy, Izz are the moments of inertia about the X, Y, and Z axes.
            - Ixy, Ixz, Iyz are the products of inertia.

        Example:
            >>> obj = MyShape()
            >>> obj.matrix_of_inertia
            [[1000.0, 50.0, 0.0],
            [50.0, 1200.0, 0.0],
            [0.0, 0.0, 300.0]]

        Notes:
            - The inertia matrix is computed relative to the shape's center of mass.
            - It is commonly used in structural analysis, mechanical simulations,
              and physics-based motion calculations.
        """
        if self._wrapped is None:
            raise ValueError("Can't calculate matrix for empty shape")
        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(self.wrapped, properties)
        inertia_matrix = properties.MatrixOfInertia()
        matrix = []
        for i in range(3):
            matrix.append([inertia_matrix.Value(i + 1, j + 1) for j in range(3)])
        return matrix

    @property
    def orientation(self) -> Vector:
        """Get the orientation component of this Shape's Location"""
        if self._wrapped is None:
            raise ValueError("Can't find the orientation of an empty shape")
        return self.location.orientation

    @orientation.setter
    def orientation(self, rotations: VectorLike):
        """Set the orientation component of this Shape's Location to rotations"""
        loc = self.location
        if loc is not None:
            loc.orientation = Vector(rotations)
            self.location = loc

    @property
    def position(self) -> Vector:
        """Get the position component of this Shape's Location"""
        if self._wrapped is None or self.location is None:
            raise ValueError("Can't find the position of an empty shape")
        return self.location.position

    @position.setter
    def position(self, value: VectorLike):
        """Set the position component of this Shape's Location to value"""
        loc = self.location
        if loc is not None:
            loc.position = Vector(value)
            self.location = loc

    @property
    def principal_properties(self) -> list[tuple[Vector, float]]:
        """
        Compute the principal moments of inertia and their corresponding axes.

        Returns:
            list[tuple[Vector, float]]: A list of tuples, where each tuple contains:
            - A `Vector` representing the axis of inertia.
            - A `float` representing the moment of inertia for that axis.

        Example:
            >>> obj = MyShape()
            >>> obj.principal_properties
            [(Vector(1, 0, 0), 1200.0),
            (Vector(0, 1, 0), 1000.0),
            (Vector(0, 0, 1), 300.0)]
        """
        if self._wrapped is None:
            raise ValueError("Can't calculate properties for empty shape")

        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(self.wrapped, properties)
        principal_props = properties.PrincipalProperties()
        principal_moments = principal_props.Moments()
        return [
            (Vector(principal_props.FirstAxisOfInertia()), principal_moments[0]),
            (Vector(principal_props.SecondAxisOfInertia()), principal_moments[1]),
            (Vector(principal_props.ThirdAxisOfInertia()), principal_moments[2]),
        ]

    @property
    def shape_type(self) -> Shapes:
        """Return the shape type string for this class"""
        return tcast(Shapes, Shape.shape_LUT[shapetype(self.wrapped)])

    @property
    def static_moments(self) -> tuple[float, float, float]:
        """
        Compute the static moments (first moments of mass) of the shape.

        The static moments represent the weighted sum of the coordinates
        with respect to the mass distribution, providing insight into the
        center of mass and mass distribution of the shape.

        Returns:
            tuple[float, float, float]: The static moments (Mx, My, Mz),
            where:
            - Mx is the first moment of mass about the YZ plane.
            - My is the first moment of mass about the XZ plane.
            - Mz is the first moment of mass about the XY plane.

        Example:
            >>> obj = MyShape()
            >>> obj.static_moments
            (150.0, 200.0, 50.0)

        """
        if self._wrapped is None:
            raise ValueError("Can't calculate moments for empty shape")

        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(self.wrapped, properties)
        return properties.StaticMoments()

    # ---- Class Methods ----

    @classmethod
    def register_shape_constructor(
        cls, shape_type: TopAbs_ShapeEnum, constructor: ShapeConstructor
    ) -> None:
        """Register a wrapper class for a TopAbs type without importing it here.

        Each topology module registers the classes it defines as it is imported,
        so that :meth:`cast` can build any shape without shape_core needing to
        import classes that in turn import it.
        """
        cls.shape_constructors[shape_type] = constructor

    @classmethod
    def register_geometry_constructor(
        cls, geometry_type: type, constructor: GeometryConstructor
    ) -> None:
        """Register how a geometry class becomes a Shape, without importing it.

        Registered by whichever topology module defines the target class, since
        the lower modules cannot import the higher ones.
        """
        cls.geometry_constructors[geometry_type] = constructor

    @classmethod
    def as_shape(cls, obj: Shape | Vector | Location | Axis | Plane) -> Shape:
        """Return the Shape equivalent of a geometry object.

        Vector and Location become a Vertex, Axis an Edge and Plane a Face.
        A Shape is returned unchanged. Subclasses are honoured, so Pos and
        Rotation convert like the Location they derive from.

        The return type is what makes this usable in place of an isinstance
        chain: the chain narrowed the operand to a Shape for type checkers, and
        this has to do the same.
        """
        for geometry_type in type(obj).__mro__:
            constructor = cls.geometry_constructors.get(geometry_type)
            if constructor is not None:
                return constructor(obj)
        return tcast("Shape", obj)

    @classmethod
    def cast(cls, obj: TopoDS_Shape) -> Shape:
        """Returns the right type of wrapper, given a OCCT object"""

        try:
            constructor = cls.shape_constructors[shapetype(obj)]
        except KeyError as exc:
            raise ValueError(f"Unable to cast {obj.ShapeType()}") from exc
        # NB downcast is needed to handle TopoDS_Shape types
        return constructor(downcast(obj))

    @classmethod
    @abstractmethod
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
            Edge | Face | Shell | Solid | Compound: extruded shape
        """

    # ---- Static Methods ----

    @staticmethod
    def _build_tree(
        shape: TopoDS_Shape,
        tree: list[_DisplayNode],
        parent: _DisplayNode | None = None,
        limit: TopAbs_ShapeEnum = TopAbs_ShapeEnum.TopAbs_VERTEX,
        show_center: bool = True,
    ) -> list[_DisplayNode]:
        """Create an anytree copy of the TopoDS_Shape structure"""

        obj_type = Shape.shape_LUT[shape.ShapeType()]
        loc: Vector | Location
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
                    f"Center{node.position:.6g}"
                    if show_center
                    else f"Position{node.position:.6g}"
                )
            else:
                address = id(node)
                name = node.__class__.__name__.ljust(9)
                loc = (
                    f"Center{node.center():.6g}" if show_center else repr(node.location)
                )
            result += f"{treestr}{name}at {address:#x}, {loc}\n"
        return result

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
        objects = list(objects)
        if center_of == CenterOf.MASS:
            total_mass = sum(o.compute_volume() for o in objects)
            weighted_centers = [
                o.center(CenterOf.MASS).multiply(o.compute_volume()) for o in objects
            ]

            sum_wc = weighted_centers[0]
            for weighted_center in weighted_centers[1:]:
                sum_wc = sum_wc.add(weighted_center)
            middle = Vector(sum_wc.multiply(1.0 / total_mass))
        elif center_of == CenterOf.BOUNDING_BOX:
            total_mass = len(list(objects))

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

    @overload
    @staticmethod
    def get_shape_list(
        shape: Shape, entity_type: Literal["Vertex"]
    ) -> ShapeList[Vertex]: ...

    @overload
    @staticmethod
    def get_shape_list(
        shape: Shape, entity_type: Literal["Edge"]
    ) -> ShapeList[Edge]: ...

    @overload
    @staticmethod
    def get_shape_list(
        shape: Shape, entity_type: Literal["Wire"]
    ) -> ShapeList[Wire]: ...

    @overload
    @staticmethod
    def get_shape_list(
        shape: Shape, entity_type: Literal["Face"]
    ) -> ShapeList[Face]: ...

    @overload
    @staticmethod
    def get_shape_list(
        shape: Shape, entity_type: Literal["Shell"]
    ) -> ShapeList[Shell]: ...

    @overload
    @staticmethod
    def get_shape_list(
        shape: Shape, entity_type: Literal["Solid"]
    ) -> ShapeList[Solid]: ...

    @overload
    @staticmethod
    def get_shape_list(
        shape: Shape, entity_type: Literal["Compound"]
    ) -> ShapeList[Compound]: ...

    @staticmethod
    def get_shape_list(
        shape: Shape,
        entity_type: Literal[
            "Vertex", "Edge", "Wire", "Face", "Shell", "Solid", "Compound"
        ],
    ) -> ShapeList:
        """Helper to extract entities of a specific type from a shape."""
        if not shape:
            return ShapeList()
        shape_list = ShapeList(
            [shape.__class__.cast(i) for i in shape.entities(entity_type)]
        )
        for item in shape_list:
            item.topo_parent = shape if shape.topo_parent is None else shape.topo_parent
        return shape_list

    @overload
    @staticmethod
    def get_single_shape(shape: Shape, entity_type: Literal["Vertex"]) -> Vertex: ...

    @overload
    @staticmethod
    def get_single_shape(shape: Shape, entity_type: Literal["Edge"]) -> Edge: ...

    @overload
    @staticmethod
    def get_single_shape(shape: Shape, entity_type: Literal["Wire"]) -> Wire: ...

    @overload
    @staticmethod
    def get_single_shape(shape: Shape, entity_type: Literal["Face"]) -> Face: ...

    @overload
    @staticmethod
    def get_single_shape(shape: Shape, entity_type: Literal["Shell"]) -> Shell: ...

    @overload
    @staticmethod
    def get_single_shape(shape: Shape, entity_type: Literal["Solid"]) -> Solid: ...

    @overload
    @staticmethod
    def get_single_shape(
        shape: Shape, entity_type: Literal["Compound"]
    ) -> Compound: ...

    @staticmethod
    def get_single_shape(
        shape: Shape,
        entity_type: Literal[
            "Vertex", "Edge", "Wire", "Face", "Shell", "Solid", "Compound"
        ],
    ) -> Shape:
        """Return the single entity of the requested type.

        Raises:
            ValueError: if the number of matching entities is not exactly one.
        """
        shape_list = Shape.get_shape_list(shape, entity_type)
        entity_count = len(shape_list)
        if entity_count != 1:
            raise ValueError(
                f"Expected exactly one {entity_type.lower()}, found {entity_count}"
            )
        return shape_list[0]

    # ---- Instance Methods ----

    @classmethod
    def register_composite_factory(
        cls, dimension: int | None, factory: CompositeFactory
    ) -> None:
        """Register a composite constructor without importing it here."""

        cls.composite_factories[dimension] = factory

    @classmethod
    def make_composite(
        cls, shapes: Iterable[Shape], dimension: int | None = None
    ) -> Shape:
        """Build the registered composite for a dimension."""

        shape_list = ShapeList(shapes)
        if dimension is None and shape_list:
            dimensions = {shape._dim for shape in shape_list}
            dimension = dimensions.pop() if len(dimensions) == 1 else None
        factory = cls.composite_factories.get(dimension) or cls.composite_factories.get(
            None
        )
        if factory is None:
            raise RuntimeError("Composite factory is not registered")
        return factory(shape_list)

    @overload
    def __add__(self, other: None) -> Self: ...
    @overload
    def __add__(self, other: Shape | Iterable[Shape]) -> Self | Compound: ...
    def __add__(self, other):
        """fuse shape to self operator +"""
        # Convert `other` to list of base objects and filter out None values
        if other is None:
            summands = []
        else:
            summands = [
                shape
                # for o in (other if isinstance(other, (list, tuple)) else [other])
                for o in ([other] if isinstance(other, Shape) else other)
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

        if self._wrapped is None:  # an empty object
            if len(summands) == 1:
                sum_shape = summands[0]
            else:
                sum_shape = summands[0].fuse(*summands[1:])
        else:
            sum_shape = self.fuse(*summands)

        return sum_shape

    def __and__(self, other: Shape | Iterable[Shape]) -> None | Self | Compound:
        """intersect shape with self operator &"""
        others = other if isinstance(other, (list, tuple)) else [other]

        if not self or (isinstance(other, Shape) and not other):
            raise ValueError("Cannot intersect shape with empty compound")
        new_shape = self.intersect(*others)
        if isinstance(new_shape, list):
            if len(new_shape) == 1:
                new_shape = new_shape[0]
            else:
                new_shape = Shape.make_composite(new_shape)

        if new_shape is not None and new_shape.wrapped is not None and SkipClean.clean:
            new_shape = new_shape.clean()

        return new_shape

    def __copy__(self) -> Self:
        """Return shallow copy or reference of self

        Create an copy of this Shape that shares the underlying TopoDS_TShape.

        Used when there is a need for many objects with the same CAD structure but at
        different Locations, etc. - for examples fasteners in a larger assembly. By
        sharing the TopoDS_TShape, the memory size of such assemblies can be greatly reduced.

        Changes to the CAD structure of the base object will be reflected in all instances.
        """
        reference = copy.deepcopy(self)
        if self.wrapped is not None:
            assert (
                reference.wrapped is not None
            )  # Ensure mypy knows reference.wrapped is not None
            reference.wrapped.TShape(self.wrapped.TShape())
        return reference

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
            if key == "topo_parent":
                result.topo_parent = value
            else:
                setattr(result, key, copy.deepcopy(value, memo))
            if key == "joints":
                for joint in result.joints.values():
                    joint.parent = result
        return result

    def __eq__(self, other) -> bool:
        """Check if two shapes are the same.

        This method checks if the current shape is the same as the other shape.
        Two shapes are considered the same if they share the same TShape with
        the same Locations. Orientations may differ.

        Args:
            other (Shape): The shape to compare with.

        Returns:
            bool: True if the shapes are the same, False otherwise.
        """
        if isinstance(other, Shape):
            return self.is_same(other)
        return NotImplemented

    def __hash__(self) -> int:
        """Return hash code"""
        if self._wrapped is None:
            return 0
        return hash(self.wrapped)

    @overload
    def __rmul__(self, other: Plane | Location) -> Self: ...
    @overload
    def __rmul__(self, other: Iterable[Plane | Location]) -> list[Self]: ...
    def __rmul__(self, other: Plane | Location | Iterable[Plane | Location]):
        """right multiply for positioning operator *"""
        return apply_location_like(self, other)

    @overload
    def __sub__(self, other: None) -> Self: ...
    @overload
    def __sub__(self, other: Shape | Iterable[Shape]) -> Self | Compound: ...
    def __sub__(self, other):
        """cut shape from self operator -"""

        if self._wrapped is None:
            raise ValueError("Cannot subtract shape from empty compound")

        # Convert `other` to list of base objects and filter out None values
        if other is None:
            subtrahends = []
        else:
            subtrahends = [
                shape
                # for o in (other if isinstance(other, (list, tuple)) else [other])
                for o in ([other] if isinstance(other, Shape) else other)
                if o is not None
                for shape in o.get_top_level_shapes()
            ]
        # If there is nothing to subtract return the original object
        if not subtrahends:
            return self

        # Check that all dimensions are the same
        minuend_dim = self._dim
        if minuend_dim is None or any(s._dim is None for s in subtrahends):
            raise ValueError("Dimensions of objects to subtract from are inconsistent")

        # Check that the operation is valid
        subtrahend_dims = [s._dim for s in subtrahends if s._dim is not None]
        if any(d < minuend_dim for d in subtrahend_dims):
            raise ValueError(
                f"Only shapes with equal or greater dimension can be subtracted: "
                f"not {type(self).__name__} ({minuend_dim}D) and "
                f"{type(other).__name__} ({min(subtrahend_dims)}D)"
            )

        # Do the actual cut operation
        difference = self.cut(*subtrahends)

        return difference

    def compute_volume(self) -> float:
        """Calculates the volume of an object.

        Returns:
            float: the volume of the shape

        """
        if not self or shapetype(self.wrapped) == TopAbs_ShapeEnum.TopAbs_VERTEX:
            return 0.0

        properties = GProp_GProps()
        calc_function = Shape.shape_properties_LUT[shapetype(self.wrapped)]

        if calc_function is None:
            raise NotImplementedError

        calc_function(self.wrapped, properties)
        return properties.Mass()

    def compute_mass(
        self, mass_unit: Unit = Unit.G, length_unit: Unit = Unit.MM
    ) -> float:
        """Calculates the 'mass' of an object.

        Returns:
            float: the mass of the shape based on the material density

        """
        if not self:
            return 0.0

        # Use the `volume` property, not compute_volume(): it returns 0 for
        # Vertex/Edge/Wire/Face and, for a manifold Shell, the enclosed volume
        # (so a closed shell masses the same as the solid it bounds).
        volume = self.volume
        if volume == 0:
            return 0.0

        density_kg_m3 = None
        if isinstance(self.material, FinishedMaterial):
            density_kg_m3 = self.material.material.density  # kg/m^3

        if density_kg_m3 is None:
            raise ValueError("Shape's density is missing")

        if density_kg_m3 == 0:
            warnings.warn("Shape's density is 0")
            return 0.0

        # convert density (kg/m^3) into the active mass_unit / length_unit^3
        density = (
            density_kg_m3
            * UNITS_PER_KILOGRAM[mass_unit]
            / UNITS_PER_METER[length_unit] ** 3
        )

        return volume * density

    def bounding_box(
        self, tolerance: float | None = None, optimal: bool = True
    ) -> BoundBox:
        """Create a bounding box for this Shape.

        Args:
            tolerance (float, optional): Defaults to None.

        Returns:
            BoundBox: A box sized to contain this Shape
        """
        return BoundBox(self, tolerance=tolerance, optimal=optimal)

    # Actually creating the abstract method causes the subclass to pass center_of
    # even when not required - possibly this could be improved.
    # @abstractmethod
    # def center(self, center_of: CenterOf) -> Vector:
    #     """Compute the center with a specific type of calculation."""

    def clean(self) -> Self:
        """clean

        Remove internal edges

        Returns:
            Shape: Original object with extraneous internal edges removed
        """
        if self._wrapped is None:
            return self
        upgrader = ShapeUpgrade_UnifySameDomain(self.wrapped, True, True, True)
        upgrader.AllowInternalEdges(False)
        # upgrader.SetAngularTolerance(1e-5)
        # OCP binds each OCCT failure straight to Exception, so
        # Standard_ConstructionError is not a Standard_Failure and there is no
        # base class to name here. Cleaning is best effort anyway: on failure
        # the uncleaned shape is still usable.
        try:
            upgrader.Build()
            self.wrapped = tcast(TOPODS, downcast(upgrader.Shape()))
        except Exception:  # pylint: disable=broad-exception-caught
            warnings.warn(f"Unable to clean {self}", stacklevel=2)
        return self

    def closest_points(self, other: Shape | VectorLike) -> tuple[Vector, Vector]:
        """Points on two shapes where the distance between them is minimal"""
        return self.distance_to_with_closest_points(other)[1:3]

    def compound(self) -> Compound:
        """Return the Compound"""
        return Shape.get_single_shape(self, "Compound")

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this Shape"""
        return ShapeList()

    def copy_attributes_to(
        self, target: Shape, exceptions: Iterable[str] | None = None
    ):
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
            if attr == "joints":
                if not getattr(target, attr):
                    target.joints = copy.deepcopy(self.joints)
                for joint in target.joints.values():
                    joint.parent = target
            elif not getattr(target, attr):
                setattr(target, attr, getattr(self, attr))

    def cut(self, *to_cut: Shape) -> Self | Compound:
        """Remove the positional arguments from this Shape.

        Args:
          *to_cut: Shape:

        Returns:
            Self | Compound: Resulting object may be of a different class than self
        """

        cut_op = BRepAlgoAPI_Cut()

        return self._bool_op((self,), to_cut, cut_op)

    def distance(self, other: Shape) -> float:
        """Minimal distance between two shapes

        Args:
          other: Shape:

        Returns:

        """
        if self._wrapped is None or not other:
            raise ValueError("Cannot calculate distance to or from an empty shape")

        return BRepExtrema_DistShapeShape(self.wrapped, other.wrapped).Value()

    def distance_to(self, other: Shape | VectorLike) -> float:
        """Minimal distance between two shapes"""
        return self.distance_to_with_closest_points(other)[0]

    def distance_to_with_closest_points(
        self, other: Shape | VectorLike
    ) -> tuple[float, Vector, Vector]:
        """Minimal distance between two shapes and the points on each shape"""
        if self._wrapped is None or (isinstance(other, Shape) and not other):
            raise ValueError("Cannot calculate distance to or from an empty shape")

        if isinstance(other, Shape):
            topods_shape = tcast(TopoDS_Shape, other.wrapped)
        else:
            vec = Vector(other)
            topods_shape = BRepBuilderAPI_MakeVertex(
                gp_Pnt(vec.X, vec.Y, vec.Z)
            ).Vertex()

        dist_calc = BRepExtrema_DistShapeShape()
        dist_calc.LoadS1(self.wrapped)
        dist_calc.LoadS2(topods_shape)
        dist_calc.Perform()
        return (
            dist_calc.Value(),
            Vector(dist_calc.PointOnShape1(1)),
            Vector(dist_calc.PointOnShape2(1)),
        )

    def distances(self, *others: Shape) -> Iterator[float]:
        """Minimal distances to between self and other shapes

        Args:
          *others: Shape:

        Returns:

        """
        if self._wrapped is None:
            raise ValueError("Cannot calculate distance to or from an empty shape")

        dist_calc = BRepExtrema_DistShapeShape()
        dist_calc.LoadS1(self.wrapped)

        for other_shape in others:
            if not other_shape:
                raise ValueError("Cannot calculate distance to or from an empty shape")
            dist_calc.LoadS2(other_shape.wrapped)
            dist_calc.Perform()

            yield dist_calc.Value()

    def edge(self) -> Edge:
        """Return the Edge"""
        return Shape.get_single_shape(self, "Edge")

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this Shape - subclasses may override"""
        edge_list = Shape.get_shape_list(self, "Edge")
        return edge_list.filter_by(
            lambda e: BRep_Tool.Degenerated_s(e.wrapped), reverse=True
        )

    def entities(self, topo_type: Shapes) -> list[TopoDS_Shape]:
        """Return all of the TopoDS sub entities of the given type"""
        if self._wrapped is None:
            return []
        return _topods_entities(self.wrapped, topo_type)

    def face(self) -> Face:
        """Return the Face"""
        return Shape.get_single_shape(self, "Face")

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this Shape"""
        return Shape.get_shape_list(self, "Face")

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
        if self._wrapped is None:
            return ShapeList()

        line = gce_MakeLin(axis.wrapped).Value()

        intersect_maker = BRepIntCurveSurface_Inter()
        intersect_maker.Init(self.wrapped, line, tol)

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

    def fix(self) -> Self:
        """fix - try to fix shape if not valid"""
        if self._wrapped is None:
            return self
        if not self.is_valid:
            shape_copy: Shape = copy.deepcopy(self, None)
            shape_copy.wrapped = tcast(TOPODS, fix(self.wrapped))

            return shape_copy

        return self

    def fuse(
        self, *to_fuse: Shape, glue: bool = False, tol: float | None = None
    ) -> Self | Compound:
        """fuse

        Fuse a sequence of shapes into a single shape.

        Args:
            to_fuse (sequence Shape): shapes to fuse
            glue (bool, optional): performance improvement for some shapes. Defaults to False.
            tol (float, optional): tolerance. Defaults to None.

        Returns:
            Self | Compound: Resulting object may be of a different class than self

        """

        fuse_op = BRepAlgoAPI_Fuse()
        if glue:
            fuse_op.SetGlue(BOPAlgo_GlueEnum.BOPAlgo_GlueShift)
        if tol:
            fuse_op.SetFuzzyValue(tol)

        return_value = self._bool_op((self,), to_fuse, fuse_op)

        return return_value

    # def _entities_from(
    #     self, child_type: Shapes, parent_type: Shapes
    # ) -> Dict[Shape, list[Shape]]:
    #     """This function is very slow on M1 macs and is currently unused"""
    #     if self._wrapped is None:
    #         return {}

    #     res = TopTools_IndexedDataMapOfShapeListOfShape()

    #     TopExp.MapShapesAndAncestors_s(
    #         self.wrapped,
    #         Shape.inverse_shape_LUT[child_type],
    #         Shape.inverse_shape_LUT[parent_type],
    #         res,
    #     )

    #     out: Dict[Shape, list[Shape]] = {}
    #     for i in range(1, res.Extent() + 1):
    #         out[self.__class__.cast(res.FindKey(i))] = [
    #             self.__class__.cast(el) for el in res.FindFromIndex(i)
    #         ]

    #     return out

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
        if self._wrapped is None:
            return ShapeList()
        return ShapeList(
            self.__class__.cast(s) for s in get_top_level_topods_shapes(self.wrapped)
        )

    def intersect(
        self,
        *to_intersect: Shape | Vector | Location | Axis | Plane,
        tolerance: float = 1e-6,
        include_touched: bool = False,
    ) -> ShapeList | None:
        """Find where bodies/interiors meet (overlap or crossing geometry).

        This is the main entry point for intersection operations. Handles
        geometry conversion and delegates to subclass _intersect() implementations.

        Semantics:
            - Multiple arguments use AND (chaining): c.intersect(s1, s2) = c ∩ s1 ∩ s2
            - Compound arguments use OR (distribution): c.intersect(Compound([s1, s2]))
              = (c ∩ s1) ∪ (c ∩ s2)

        Args:
            to_intersect: Shape(s) or geometry objects to intersect with
            tolerance: tolerance for intersection detection
            include_touched: if True, include boundary contacts without interior
                overlap (only relevant when Solids are involved)

        Returns:
            ShapeList of intersection results, or None if no intersection
        """

        if not to_intersect:
            return None

        # Validate input types
        for obj in to_intersect:
            if not isinstance(obj, (Shape, Vector, Location, Axis, Plane)):
                raise ValueError(f"Unsupported type for intersect: {type(obj)}")

        # Chained iteration for AND semantics: c.intersect(s1, s2) = c ∩ s1 ∩ s2
        # Geometry objects (Vector, Location, Axis, Plane) are converted in _intersect
        common_set = ShapeList([self])
        for other in to_intersect:
            next_set: ShapeList = ShapeList()
            for obj in common_set:
                result = obj._intersect(other, tolerance, include_touched)
                if result:
                    next_set.extend(result.expand())
            if not next_set:
                return None  # AND semantics: if any step fails, no intersection
            common_set = ShapeList(set(next_set))  # deduplicate
        return common_set if common_set else None

    # pylint: disable=unused-argument
    def _intersect(
        self,
        other: Shape | Vector | Location | Axis | Plane,
        tolerance: float = 1e-6,
        include_touched: bool = False,
    ) -> ShapeList | None:
        """Single-object intersection implementation.

        Base implementation returns None. Subclasses (Vertex, Mixin1D, Mixin2D,
        Mixin3D, Compound) override this to provide actual intersection logic.

        Args:
            other: Shape or geometry object to intersect with
            tolerance: tolerance for intersection detection
            include_touched: if True, include boundary contacts

        Returns:
            ShapeList of intersection shapes, or None if no intersection
        """
        return None

    def touch(self, other: Shape, tolerance: float = 1e-6) -> ShapeList:
        """Find boundary contacts between this shape and another.

        Base implementation returns empty ShapeList. Subclasses (Mixin2D, Mixin3D,
        Compound) override this to provide actual touch detection.

        Args:
            other: Shape to find contacts with
            tolerance: tolerance for contact detection

        Returns:
            ShapeList of contact shapes (empty for base implementation)
        """
        return ShapeList()

    # pylint: enable=unused-argument

    def is_equal(self, other: Shape) -> bool:
        """Returns True if two shapes are equal, i.e. if they share the same
        TShape with the same Locations and Orientations. Also see
        :py:meth:`is_same`.

        Args:
          other: Shape:

        Returns:

        """
        if self._wrapped is None or not other:
            return False
        return self.wrapped.IsEqual(other.wrapped)

    def is_same(self, other: Shape) -> bool:
        """Returns True if other and this shape are same, i.e. if they share the
        same TShape with the same Locations. Orientations may differ. Also see
        :py:meth:`is_equal`

        Args:
          other: Shape:

        Returns:

        """
        if self._wrapped is None or not other:
            return False
        return self.wrapped.IsSame(other.wrapped)

    def locate(self, loc: Location) -> Self:
        """Apply a location in absolute sense to self

        Args:
          loc: Location:

        Returns:

        """
        if self._wrapped is None:
            raise ValueError("Cannot locate an empty shape")
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
        if self._wrapped is None:
            raise ValueError("Cannot locate an empty shape")
        shape_copy = copy.deepcopy(self, None)
        shape_copy.wrapped.Location(loc.wrapped)
        return shape_copy

    def mesh(self, tolerance: float, angular_tolerance: float = 0.1):
        """Generate triangulation if none exists.

        Args:
          tolerance: float:
          angular_tolerance: float:  (Default value = 0.1)

        Returns:

        """
        if self._wrapped is None:
            raise ValueError("Cannot mesh an empty shape")

        if not BRepTools.Triangulation_s(self.wrapped, tolerance):
            BRepMesh_IncrementalMesh(
                self.wrapped, tolerance, True, angular_tolerance, True
            )

    def mirror(self, mirror_plane: Plane | None = None) -> Self:
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

        if self._wrapped is None:
            return self
        transformation = gp_Trsf()
        transformation.SetMirror(
            gp_Ax2(mirror_plane.origin.to_pnt(), mirror_plane.z_dir.to_dir())
        )

        return self._apply_transform(transformation)

    def move(self, loc: Location) -> Self:
        """Apply a location in relative sense (i.e. update current location) to self

        Args:
          loc: Location:

        Returns:

        """
        if self._wrapped is None:
            raise ValueError("Cannot move an empty shape")

        self.wrapped.Move(loc.wrapped)

        return self

    def moved(self, loc: Location | Plane) -> Self:
        """moved

        Apply a location in relative sense (i.e. update current location) to a copy of self

        Args:
            loc (Location | Plane): new location relative to current location

        Returns:
            Shape: copy of Shape moved to relative location
        """
        if isinstance(loc, Plane):
            loc = loc.location
        if self._wrapped is None:
            raise ValueError("Cannot move an empty shape")
        shape_copy: Shape = copy.deepcopy(self, None)
        shape_copy.wrapped = tcast(TOPODS, downcast(self.wrapped.Moved(loc.wrapped)))
        return shape_copy

    def oriented_bounding_box(self) -> OrientedBoundBox:
        """Create an oriented bounding box for this Shape.

        Returns:
            OrientedBoundBox: A box oriented and sized to contain this Shape
        """
        if self._wrapped is None:
            return OrientedBoundBox(Bnd_OBB())
        return OrientedBoundBox(self)

    def project_faces(
        self,
        faces: list[Face] | Compound,
        path: Wire | Edge,
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
            surface_point, surface_normal = self.find_intersection_points(
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

    def radius_of_gyration(self, axis: Axis) -> float:
        """
        Compute the radius of gyration of the shape about a given axis.

        The radius of gyration represents the distance from the axis at which the entire
        mass of the shape could be concentrated without changing its moment of inertia.
        It provides insight into how mass is distributed relative to the axis and is
        useful in structural analysis, rotational dynamics, and mechanical simulations.

        Args:
            axis (Axis): The axis about which the radius of gyration is computed.
                        The axis should be defined in the same coordinate system
                        as the shape.

        Returns:
            float: The radius of gyration in the same units as the shape's dimensions.

        Example:
            >>> obj = MyShape()
            >>> axis = Axis((0, 0, 0), (0, 0, 1))
            >>> obj.radius_of_gyration(axis)
            5.47

        Notes:
            - The radius of gyration is computed based on the shape’s mass properties.
            - It is useful for evaluating structural stability and rotational behavior.
        """
        if self._wrapped is None:
            raise ValueError("Can't calculate radius of gyration for empty shape")

        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(self.wrapped, properties)
        return properties.RadiusOfGyration(axis.wrapped)

    def rotate(self, axis: Axis, angle: float, transform: bool = False) -> Self:
        """rotate a copy

        Rotates a shape around an axis.

        Args:
            axis (Axis): rotation Axis
            angle (float): angle to rotate, in degrees
            transform (bool): regenerate the shape instead of just changing its location.
                Defaults to False.

        Returns:
            a copy of the shape, rotated
        """
        if self._wrapped is None:  # For backwards compatibility
            return self

        transformation = gp_Trsf()
        transformation.SetRotation(axis.wrapped, angle * DEG2RAD)

        if transform:
            rotated_self = self._apply_transform(transformation)
        else:
            rotated_self = self.moved(Location(TopLoc_Location(transformation)))
        return rotated_self

    def scale(
        self,
        factor: float | tuple[float, float, float],
        about: VectorLike | None = None,
    ) -> Self:
        """Scale this shape about a point.

        Non-uniform scaling may change the underlying geometry type to splines.
        When ``about`` isn't provided, the shape is scaled about its location.

        Args:
            factor (float | tuple[float, float, float]): uniform scale factor or
                three scale factors for the X, Y and Z directions.
            about (VectorLike, optional): point to scale about. Defaults to the
                shape's location position.

        Returns:
            Shape: a copy of the scaled shape.
        """

        current_location = self.location
        assert current_location is not None
        about_point = current_location.position if about is None else Vector(about)

        if isinstance(factor, (int, float)):
            transformation = gp_Trsf()
            transformation.SetScale(about_point.to_pnt(), float(factor))
            return self._apply_transform(transformation)
        if (
            isinstance(factor, tuple)
            and len(factor) == 3
            and all(isinstance(scale, (int, float)) for scale in factor)
        ):
            scale_vector = Vector(factor)
            scale_matrix = Matrix(
                [
                    [
                        scale_vector.X,
                        0.0,
                        0.0,
                        about_point.X * (1 - scale_vector.X),
                    ],
                    [
                        0.0,
                        scale_vector.Y,
                        0.0,
                        about_point.Y * (1 - scale_vector.Y),
                    ],
                    [
                        0.0,
                        0.0,
                        scale_vector.Z,
                        about_point.Z * (1 - scale_vector.Z),
                    ],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )
            return self.transform_geometry(scale_matrix)
        raise ValueError("factor must be a float or a three tuple of float")

    def shell(self) -> Shell:
        """Return the Shell"""
        return Shape.get_single_shape(self, "Shell")

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this Shape"""
        return Shape.get_shape_list(self, "Shell")

    def show_topology(
        self,
        limit_class: Literal[
            "Compound", "Edge", "Face", "Shell", "Solid", "Vertex", "Wire"
        ] = "Vertex",
        show_center: bool | None = None,
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
        if (
            self.wrapped is not None
            and isinstance(self.wrapped, TopoDS_Compound)
            and self.children
        ):
            show_center = False if show_center is None else show_center
            result = Shape._show_tree(self, show_center)
        else:
            tree = Shape._build_tree(
                tcast(TopoDS_Shape, self.wrapped),
                tree=[],
                limit=Shape.inverse_shape_LUT[limit_class],
            )
            show_center = True if show_center is None else show_center
            result = Shape._show_tree(tree[0], show_center)
        return result

    def solid(self) -> Solid:
        """Return the Solid"""
        return Shape.get_single_shape(self, "Solid")

    def solids(self) -> ShapeList[Solid]:
        """solids - all the solids in this Shape"""
        return Shape.get_shape_list(self, "Solid")

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
    def split(
        self, tool: TrimmingTool, keep: Literal[Keep.INSIDE, Keep.OUTSIDE]
    ) -> None:
        """invalid split"""

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
        if self._wrapped is None or not tool:
            raise ValueError("Can't split an empty edge/wire/tool")

        if keep in [Keep.INSIDE, Keep.OUTSIDE]:
            raise ValueError(f"{keep} is invalid")

        shape_list = TopTools_ListOfShape()
        shape_list.Append(self.wrapped)

        # Define the splitting tool
        trim_tool = (
            BRepBuilderAPI_MakeFace(tool.wrapped).Face()  # gp_Pln to Face
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
        # can sort more efficiently then the generic algorithm below
        if keep == Keep.ALL:
            return ShapeList(
                self.__class__.cast(part)
                for part in get_top_level_topods_shapes(split_result)
            )

        if not isinstance(tool, Plane):
            # Get a TopoDS_Face to work with from the tool
            if isinstance(trim_tool, TopoDS_Shell):
                face_explorer = TopExp_Explorer(trim_tool, ta.TopAbs_FACE)
                tool_face = TopoDS.Face(face_explorer.Current())
            else:
                tool_face = trim_tool

            # Create a reference point off the +ve side of the tool
            surface_gppnt = gp_Pnt()
            surface_normal = gp_Vec()
            u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(tool_face)
            BRepGProp_Face(tool_face).Normal(
                (u_min + u_max) / 2, (v_min + v_max) / 2, surface_gppnt, surface_normal
            )
            normalized_surface_normal = Vector(
                surface_normal.X(), surface_normal.Y(), surface_normal.Z()
            ).normalized()
            surface_point = Vector(surface_gppnt)
            ref_point = surface_point + normalized_surface_normal

            # Create a HalfSpace - Solidish object to determine top/bottom
            # Note: BRepPrimAPI_MakeHalfSpace takes either a TopoDS_Shell or TopoDS_Face but the
            # mypy expects only a TopoDS_Shell here
            half_space_maker = BRepPrimAPI_MakeHalfSpace(trim_tool, ref_point.to_pnt())
            # type: ignore
            tool_solid = half_space_maker.Solid()

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
        # Keep.ALL returned earlier and INSIDE/OUTSIDE were rejected above, so
        # this is unreachable until a Keep value is added
        raise ValueError(f"Unsupported Keep value {keep}")  # pragma: no cover

    def tessellate(
        self, tolerance: float, angular_tolerance: float = 0.1
    ) -> tuple[list[Vector], list[tuple[int, int, int]]]:
        """General triangulated approximation"""
        if self._wrapped is None:
            raise ValueError("Cannot tessellate an empty shape")

        self.mesh(tolerance, angular_tolerance)

        vertices: list[Vector] = []
        triangles: list[tuple[int, int, int]] = []
        offset = 0

        for face in self.faces():
            assert face.wrapped is not None
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

    def tessellate_with_uvs(
        self,
        tolerance: float,
        angular_tolerance: float = 0.1,
        atlas_packing: bool = True,
        atlas_gutter: float = 0.0,
    ) -> tuple[
        list[Vector],
        list[tuple[int, int, int]],
        list[Vector],
        list[tuple[float, float]],
    ]:
        """Triangulated approximation with per-vertex normals and UV coordinates.

        Extracts UV coordinates from OpenCASCADE's surface parameterization for
        each face, normalizes them to [0, 1], and optionally packs all faces
        into a single UV atlas so textures can span the entire model.

        The UV mapping approach is ported from CascadeStudio's ShapeToMesh:
        arc-lengths of isoparametric curves are used to determine each face's
        physical aspect ratio, and a shelf-based bin packing algorithm arranges
        all faces into a single [0, 1] texture atlas.

        Args:
            tolerance: linear deflection for tessellation.
            angular_tolerance: angular deflection for tessellation. Default 0.1.
            atlas_packing: if True (default), pack per-face UVs into a single
                texture atlas.  If False, each face's UVs are independently
                normalized to [0, 1].
            atlas_gutter: fraction of the atlas (in normalized [0, 1] units) to
                reserve as an empty margin around every packed face. A non-zero
                value prevents neighbouring islands from bleeding into one
                another when the atlas is sampled with interpolation (useful for
                texture baking). Only used when ``atlas_packing`` is True.
                Defaults to 0.0.

        Returns:
            A 4-tuple of (vertices, triangles, normals, uvs) where:
            - vertices: list of Vector positions
            - triangles: list of (i0, i1, i2) index triples
            - normals: list of Vector per-vertex normals
            - uvs: list of (u, v) texture coordinates per vertex
        """
        if self._wrapped is None:
            raise ValueError("Cannot tessellate an empty shape")

        self.mesh(tolerance, angular_tolerance)

        all_vertices: list[Vector] = []
        all_triangles: list[tuple[int, int, int]] = []
        all_normals: list[Vector] = []
        all_uvs: list[tuple[float, float]] = []

        # Per-face UV data for atlas packing
        face_uv_ranges: list[dict] = []
        offset = 0

        for face in self.faces():
            assert face.wrapped is not None
            loc = TopLoc_Location()
            poly = BRep_Tool.Triangulation_s(face.wrapped, loc)
            if poly is None:
                continue
            trsf = loc.Transformation()
            is_reversed = (
                face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
            )
            reverse_factor = -1.0 if is_reversed else 1.0
            nb_nodes = poly.NbNodes()

            # Extract rotation matrix and translation for numpy bulk transform
            mat = trsf.VectorialPart()
            tr = trsf.TranslationPart()
            rot = np.array(
                [
                    [mat.Value(1, 1), mat.Value(1, 2), mat.Value(1, 3)],
                    [mat.Value(2, 1), mat.Value(2, 2), mat.Value(2, 3)],
                    [mat.Value(3, 1), mat.Value(3, 2), mat.Value(3, 3)],
                ]
            )
            trans = np.array([tr.X(), tr.Y(), tr.Z()])

            # Vertices — bulk extract via MapNodeArray + numpy transform
            node_arr = poly.MapNodeArray()
            coords = np.empty((nb_nodes, 3))
            for i in range(1, nb_nodes + 1):
                p = node_arr.Value(i)
                coords[i - 1] = (p.X(), p.Y(), p.Z())
            transformed = coords @ rot.T + trans
            all_vertices.extend(Vector(row[0], row[1], row[2]) for row in transformed)

            # Normals — bulk extract + numpy rotate (no translation)
            if not poly.HasNormals():
                poly.ComputeNormals()
            norm_coords = np.empty((nb_nodes, 3))
            for i in range(1, nb_nodes + 1):
                d = poly.Normal(i)
                norm_coords[i - 1] = (d.X(), d.Y(), d.Z())
            rotated_normals = norm_coords @ rot.T * reverse_factor
            all_normals.extend(
                Vector(row[0], row[1], row[2]) for row in rotated_normals
            )

            # UV coordinates — bulk extract via MapUVNodeArray + numpy normalize
            if poly.HasUVNodes():
                uv_arr = poly.MapUVNodeArray()
                uv_raw = np.empty((nb_nodes, 2))
                for i in range(1, nb_nodes + 1):
                    uv_pnt = uv_arr.Value(i)
                    uv_raw[i - 1] = (uv_pnt.X(), uv_pnt.Y())

                uv_min = uv_raw.min(axis=0)
                uv_max = uv_raw.max(axis=0)
                uv_range = uv_max - uv_min
                uv_range[uv_range < TOLERANCE] = 1.0

                # Compute arc-lengths of isoparametric curves for aspect ratio
                u_min, v_min = uv_min
                u_max, v_max = uv_max
                arc_w, arc_h = float(uv_range[0]), float(uv_range[1])
                try:
                    surface = BRep_Tool.Surface_s(face.wrapped)
                    u_center = (u_min + u_max) * 0.5
                    v_center = (v_min + v_max) * 0.5
                    viso = surface.VIso(v_center)
                    uiso = surface.UIso(u_center)
                    u_adaptor = GeomAdaptor_Curve(viso)
                    v_adaptor = GeomAdaptor_Curve(uiso)
                    arc_w = GCPnts_AbscissaPoint.Length_s(
                        u_adaptor, u_min, u_max, TOLERANCE
                    )
                    arc_h = GCPnts_AbscissaPoint.Length_s(
                        v_adaptor, v_min, v_max, TOLERANCE
                    )
                except Standard_Failure:
                    # Degenerate/unsupported surface parameterization — fall back
                    # to the raw UV-parameter extents computed above.
                    pass

                if arc_w < TOLERANCE:
                    arc_w = 1.0
                if arc_h < TOLERANCE:
                    arc_h = 1.0

                # Normalize UVs to [0, 1] per face (numpy vectorized)
                uv_norm = (uv_raw - uv_min) / uv_range
                if is_reversed:
                    uv_norm[:, 0] = 1.0 - uv_norm[:, 0]

                face_uv_ranges.append(
                    {
                        "start": len(all_uvs),
                        "count": nb_nodes,
                        "w": arc_w,
                        "h": arc_h,
                    }
                )
                all_uvs.extend((float(row[0]), float(row[1])) for row in uv_norm)
            else:
                all_uvs.extend((0.0, 0.0) for _ in range(nb_nodes))
                face_uv_ranges.append(
                    {
                        "start": len(all_uvs) - nb_nodes,
                        "count": nb_nodes,
                        "w": 1.0,
                        "h": 1.0,
                    }
                )

            # Triangles
            for t in poly.Triangles():
                n1, n2, n3 = t.Value(1), t.Value(2), t.Value(3)
                if is_reversed:
                    n1, n2 = n2, n1
                all_triangles.append(
                    (n1 + offset - 1, n2 + offset - 1, n3 + offset - 1)
                )

            offset += nb_nodes

        # Atlas packing: scale per-face UVs to world-space proportions and pack
        # them into a single [0, 1] texture atlas.
        if atlas_packing and face_uv_ranges:
            # Each face occupies a rectangle sized by its physical arc-lengths so
            # islands keep their real-world aspect ratios in the atlas.
            positions = _pack2d(
                face_uv_ranges,
                width_fn=lambda r: tcast(dict, r)["w"],
                length_fn=lambda r: tcast(dict, r)["h"],
            )

            # Normalize the overall packed extent into [0, 1].
            pack_w = max(x + r["w"] for (x, _), r in zip(positions, face_uv_ranges))
            pack_h = max(y + r["h"] for (_, y), r in zip(positions, face_uv_ranges))
            scale = max(pack_w, pack_h)
            if scale < TOLERANCE:
                scale = 1.0
            inv_scale = 1.0 / scale

            for (px, py), info in zip(positions, face_uv_ranges):
                start = info["start"]
                count = info["count"]
                # Island origin and size in normalized atlas space, inset on
                # every side by the requested gutter (clamped so it never
                # exceeds half the island).
                bw = info["w"] * inv_scale
                bh = info["h"] * inv_scale
                gutter_u = min(atlas_gutter, bw * 0.5)
                gutter_v = min(atlas_gutter, bh * 0.5)
                bx = px * inv_scale + gutter_u
                by = py * inv_scale + gutter_v
                bw -= 2.0 * gutter_u
                bh -= 2.0 * gutter_v
                for j in range(start, start + count):
                    u, v = all_uvs[j]
                    all_uvs[j] = (u * bw + bx, v * bh + by)

        return all_vertices, all_triangles, all_normals, all_uvs

    def to_splines(
        self, degree: int = 3, tolerance: float = 1e-3, nurbs: bool = False
    ) -> Self:
        """to_splines

        A shape-processing utility that forces all geometry in a shape to be converted into
        BSplines. It's useful when working with tools or export formats that require uniform
        geometry, or for downstream processing that only understands BSpline representations.

        Args:
            degree (int, optional): Maximum degree. Defaults to 3.
            tolerance (float, optional): Approximation tolerance. Defaults to 1e-3.
            nurbs (bool, optional): Use rational splines. Defaults to False.

        Returns:
            Self: Approximated shape
        """
        if self._wrapped is None:
            raise ValueError("Cannot approximate an empty shape")

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

        return self.__class__.cast(result)

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
        if self._wrapped is None:
            return self
        new_shape = copy.deepcopy(self, None)
        transformed = downcast(
            BRepBuilderAPI_GTransform(self.wrapped, t_matrix.wrapped, True).Shape()
        )
        new_shape.wrapped = tcast(TOPODS, transformed)

        return new_shape

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
        if self._wrapped is None:
            return self
        new_shape = copy.deepcopy(self, None)
        transformed = downcast(
            BRepBuilderAPI_Transform(self.wrapped, t_matrix.wrapped.Trsf()).Shape()
        )
        new_shape.wrapped = tcast(TOPODS, transformed)

        return new_shape

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

    def translate(self, vector: VectorLike, transform: bool = False) -> Self:
        """Translates this shape through a transformation.

        Args:
            vector (VectorLike): relative movement vector
            transform (bool): regenerate the shape instead of just changing its location
                Defaults to False.

        Returns:
            object with a relative move applied
        """
        if self._wrapped is None:  # For backwards compatibility
            return self

        transformation = gp_Trsf()
        transformation.SetTranslation(Vector(vector).wrapped)

        if transform:
            self_translated = self._apply_transform(transformation)
        else:
            self_translated = self.moved(Location(TopLoc_Location(transformation)))
        return self_translated

    def wire(self) -> Wire:
        """Return the Wire"""
        return Shape.get_single_shape(self, "Wire")

    def wires(self) -> ShapeList[Wire]:
        """wires - all the wires in this Shape"""
        return Shape.get_shape_list(self, "Wire")

    def _apply_transform(self, transformation: gp_Trsf) -> Self:
        """Private Apply Transform

        Apply the provided transformation matrix to a copy of Shape

        Args:
            transformation (gp_Trsf): transformation matrix

        Returns:
            Shape: copy of transformed Shape
        """
        if self._wrapped is None:
            return self
        shape_copy: Shape = copy.deepcopy(self, None)
        transformed_shape = BRepBuilderAPI_Transform(
            self.wrapped,
            transformation,
            True,
        ).Shape()
        shape_copy.wrapped = tcast(TOPODS, downcast(transformed_shape))
        return shape_copy

    def _bool_op(
        self,
        args: Iterable[Shape],
        tools: Iterable[Shape],
        operation: BRepAlgoAPI_BooleanOperation | BRepAlgoAPI_Splitter,
    ) -> Self | Compound:
        """Generic boolean operation

        Args:
          args: Iterable[Shape]:
          tools: Iterable[Shape]:
          operation: Union[BRepAlgoAPI_BooleanOperation:
          BRepAlgoAPI_Splitter]:

        Returns:
            Shape or Compound result

        """
        args = list(args)
        tools = list(tools)
        # Find the highest order class from all the inputs Solid > Vertex
        order_dict = {
            type(s): type(s).order
            for s in [self] + args + tools
            if hasattr(type(s), "order")
        }
        highest_order = sorted(order_dict.items(), key=lambda item: item[1])[-1]

        # The base of the operation
        base = args[0] if isinstance(args, (list, tuple)) else args

        arg = TopTools_ListOfShape()
        for obj in args:
            if obj._wrapped is not None:
                arg.Append(obj._wrapped)

        tool = TopTools_ListOfShape()
        for obj in tools:
            if obj._wrapped is not None:
                tool.Append(obj._wrapped)

        # Handle operations with "zero" shapes
        topo_result = None
        if isinstance(operation, BRepAlgoAPI_Cut):
            if tool.IsEmpty():
                if arg.Extent() == 1:
                    topo_result = arg.First()
                else:
                    topo_result = _make_topods_compound_from_shapes(arg)
        elif isinstance(operation, BRepAlgoAPI_Fuse):
            if tool.IsEmpty():
                if arg.Extent() == 1:
                    topo_result = arg.First()
                else:
                    topo_result = _make_topods_compound_from_shapes(arg)
            elif arg.IsEmpty():
                if tool.Extent() == 1:
                    topo_result = tool.First()
                else:
                    topo_result = _make_topods_compound_from_shapes(tool)
        elif isinstance(operation, BRepAlgoAPI_Common):
            if tool.IsEmpty() or arg.IsEmpty():
                return self.__class__()

        if topo_result is None:
            operation.SetArguments(arg)
            operation.SetTools(tool)

            operation.SetRunParallel(True)
            operation.Build()

            topo_result = downcast(operation.Shape())

        # Clean
        if SkipClean.clean:
            upgrader = ShapeUpgrade_UnifySameDomain(topo_result, True, True, True)
            upgrader.AllowInternalEdges(False)
            # see Shape.clean: OCP gives OCCT failures no common base class
            try:
                upgrader.Build()
                topo_result = downcast(upgrader.Shape())
            except Exception:  # pylint: disable=broad-exception-caught
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
            result = Shape.make_composite(results, highest_order[1])
            base.copy_attributes_to(result, ["wrapped", "_NodeMixin__children"])
            return result

        result = highest_order[0].cast(topo_result)
        base.copy_attributes_to(result, ["wrapped", "_NodeMixin__children"])

        return result

    def _bool_op_list(
        self,
        args: Iterable[Shape],
        tools: Iterable[Shape],
        operation: BRepAlgoAPI_BooleanOperation | BRepAlgoAPI_Splitter,
    ) -> ShapeList:
        """Generic boolean operation that always returns ShapeList.

        Wrapper around _bool_op that guarantees ShapeList return type,
        wrapping single results and returning empty ShapeList for null results.

        Args:
          args: Iterable[Shape]:
          tools: Iterable[Shape]:
          operation: Union[BRepAlgoAPI_BooleanOperation, BRepAlgoAPI_Splitter]:

        Returns:
            ShapeList (possibly empty)

        """
        result = self._bool_op(args, tools, operation)
        if result.is_null:
            return ShapeList()
        if isinstance(result.wrapped, TopoDS_Compound):
            return result.get_top_level_shapes()
        return ShapeList([result])

    def _ocp_section(
        self: Shape, other: Vertex | Edge | Wire | Face
    ) -> tuple[ShapeList[Vertex], ShapeList[Edge]]:
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
            tuple[ShapeList[Vertex], ShapeList[Edge]]: section results
        """
        if self._wrapped is None or not other:
            return (ShapeList(), ShapeList())

        section = BRepAlgoAPI_Section(self.wrapped, other.wrapped)
        section.SetRunParallel(True)
        section.Approximation(True)
        section.ComputePCurveOn1(True)
        section.ComputePCurveOn2(True)
        section.Build()

        # Get the resulting shapes from the intersection
        intersection_shape: TopoDS_Shape = section.Shape()

        vertices: list[Vertex] = []
        # Iterate through the intersection shape to find intersection points/edges
        explorer = TopExp_Explorer(intersection_shape, TopAbs_ShapeEnum.TopAbs_VERTEX)
        while explorer.More():
            vertices.append(self.__class__.cast(downcast(explorer.Current())))
            explorer.Next()
        edges: ShapeList[Edge] = ShapeList()
        explorer = TopExp_Explorer(intersection_shape, TopAbs_ShapeEnum.TopAbs_EDGE)
        while explorer.More():
            edges.append(self.__class__.cast(downcast(explorer.Current())))
            explorer.Next()

        return (ShapeList(set(vertices)), edges)

    def _repr_html_(self):
        """Jupyter 3D representation support"""

        # deferred so that importing build123d does not pull in jupyter_tools;
        # this goes away when jupyter_tools is removed
        # pylint: disable=import-outside-toplevel
        from build123d.jupyter_tools import shape_to_html, has_vtk

        if has_vtk:
            return shape_to_html(self)._repr_html_()
        return repr(self)

    def vertex(self) -> Vertex:
        """Return the Vertex"""
        return Shape.get_single_shape(self, "Vertex")

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this Shape"""
        return Shape.get_shape_list(self, "Vertex")


class Comparable(ABC):
    """Abstract base class that requires comparison methods"""

    # ---- Instance Methods ----

    @abstractmethod
    def __eq__(self, other: Any) -> bool: ...

    @abstractmethod
    def __lt__(self, other: Any) -> bool: ...


class SupportsLessThan(Protocol):
    """ShapeList comparison criteria"""

    def __lt__(self, other: Any) -> bool: ...


# This TypeVar allows IDEs to see the type of objects within the ShapeList
T = TypeVar("T", bound=Union[Shape, Vector])
# K = TypeVar("K", bound=Comparable)
K = TypeVar("K", bound=SupportsLessThan)


class GroupBy(Generic[T, K]):
    """Result of a Shape.groupby operation. Groups can be accessed by index or key"""

    # ---- Constructor ----

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

    # ---- Instance Methods ----

    def __getitem__(self, key: int):
        return self.groups[key]

    def __iter__(self):
        return iter(self.groups)

    def __len__(self):
        return len(self.groups)

    def __repr__(self):
        return repr(ShapeList(self))

    def __str__(self):
        return pretty(self)

    def group(self, key: K):
        """Select group by key"""
        for k, i in self.key_to_group_index:
            if key == k:
                return self.groups[i]
        raise KeyError(key)

    def group_for(self, shape: T):
        """Select group by shape"""
        return self.group(self.key_f(shape))

    def _repr_pretty_(
        self, printer: RepresentationPrinter, cycle: bool = False
    ) -> None:
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


def topo_distance_to(
    other: Shape | Iterable[Shape],
) -> Callable[[Shape], int | float]:
    """Return a key function that yields topological distance to ``other``.

    The returned callable is intended for use with :meth:`ShapeList.sort_by`
    and :meth:`ShapeList.group_by`. Distances are measured on the full topology
    of the shared ``topo_parent`` of the reference shape(s), not only within
    the ``ShapeList`` being sorted or grouped.

    The first-pass implementation supports homogeneous collections of:
    ``Vertex``, ``Edge``, ``Wire``, ``Face``, ``Shell``, and ``Solid``.

    Adjacency is defined by shared lower-order topology:
    - ``Face`` via shared ``Edge``
    - ``Edge``/``Wire`` via shared ``Vertex``
    - ``Shell``/``Solid`` via shared ``Face``
    - ``Vertex`` via shared ``Edge``

    Reference shapes have distance ``0``. Directly connected shapes have
    distance ``1``. Each additional intervening peer increases the distance
    by ``1``. Unreachable shapes return ``inf``.

    Args:
        other: reference shape or shapes

    Raises:
        ValueError: empty reference set, mixed shape types, unsupported
            shape type, missing ``topo_parent``, or multiple parents

    Returns:
        Callable[[Shape], int | float]: key function for sorting/grouping
    """
    sources = ShapeList([other]) if isinstance(other, Shape) else ShapeList(other)

    if not sources:
        raise ValueError("Cannot measure topological distance to an empty object")
    if not all(isinstance(shape, Shape) for shape in sources):
        raise ValueError("Topological distance requires Shape objects")

    # pylint: disable=no-member
    peer_type = sources[0].shape_type

    if any(shape.shape_type != peer_type for shape in sources):
        raise ValueError("Topological distance requires shapes of the same type")

    plural_lut = {
        "Vertex": "vertices",
        "Edge": "edges",
        "Wire": "wires",
        "Face": "faces",
        "Shell": "shells",
        "Solid": "solids",
    }
    connector_enum_lut = {
        "Edge": ta.TopAbs_VERTEX,
        "Wire": ta.TopAbs_VERTEX,
        "Face": ta.TopAbs_EDGE,
        "Shell": ta.TopAbs_FACE,
        "Solid": ta.TopAbs_FACE,
    }

    if peer_type not in plural_lut:
        raise ValueError(f"Topological distance is not supported for {peer_type}")

    parents = [shape.topo_parent for shape in sources]
    if any(parent is None for parent in parents):
        raise ValueError("Topological distance requires shapes with a topo_parent")
    valid_parents = tcast(list[Shape], parents)
    parent = valid_parents[0]
    if any(not parent.is_same(candidate) for candidate in valid_parents[1:]):
        raise ValueError("Topological distance requires a shared topo_parent")

    peers = tcast(ShapeList[Shape], getattr(parent, plural_lut[peer_type])())
    shape_hasher = TopTools_ShapeMapHasher()
    peer_lookup = {
        shape_hasher(peer.wrapped): peer for peer in peers if peer.wrapped is not None
    }

    if peer_type == "Vertex":
        vertex_neighbors: dict[Shape, set[Shape]] = {peer: set() for peer in peers}
        vertex_edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            parent.wrapped,
            ta.TopAbs_VERTEX,
            ta.TopAbs_EDGE,
            vertex_edge_map,
        )

        for index in range(vertex_edge_map.Extent()):
            vertex_wrapped = TopoDS.Vertex(vertex_edge_map.FindKey(index + 1))
            vertex_peer = peer_lookup.get(shape_hasher(vertex_wrapped))
            if vertex_peer is None:
                continue

            for edge_wrapped in vertex_edge_map.FindFromKey(vertex_wrapped):
                edge = TopoDS.Edge(edge_wrapped)
                vertex0 = TopoDS_Vertex()
                vertex1 = TopoDS_Vertex()
                TopExp.Vertices_s(edge, vertex0, vertex1)

                for neighbor_wrapped in (vertex0, vertex1):
                    neighbor = peer_lookup.get(shape_hasher(neighbor_wrapped))
                    if neighbor is not None and neighbor != vertex_peer:
                        vertex_neighbors[vertex_peer].add(neighbor)
    else:
        connector_peer_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(
            parent.wrapped,
            connector_enum_lut[peer_type],
            Shape.inverse_shape_LUT[peer_type],
            connector_peer_map,
        )

        peer_connectors: dict[Shape, list[TopoDS_Shape]] = {peer: [] for peer in peers}
        connector_to_peers: dict[TopoDS_Shape, list[Shape]] = {}

        for index in range(connector_peer_map.Extent()):
            connector = connector_peer_map.FindKey(index + 1)
            connected_peers = []
            for peer_wrapped in connector_peer_map.FindFromKey(connector):
                peer = peer_lookup.get(shape_hasher(peer_wrapped))
                if peer is None:
                    continue
                connected_peers.append(peer)
                peer_connectors[peer].append(connector)
            connector_to_peers[connector] = connected_peers

    distances: dict[Shape, int] = {}
    frontier: deque[Shape] = deque()
    for source in sources:
        if source in peers and source not in distances:
            distances[source] = 0
            frontier.append(source)

    while frontier:
        current = frontier.popleft()
        if peer_type == "Vertex":
            neighbors = vertex_neighbors[current]
        else:
            neighbors = {
                peer
                for connector in peer_connectors[current]
                for peer in connector_to_peers[connector]
                if peer != current
            }

        for neighbor in neighbors:
            if neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            frontier.append(neighbor)

    def key_f(obj: Shape) -> int | float:
        if not isinstance(obj, Shape):
            raise ValueError("Topological distance requires Shape objects")
        if obj.shape_type != peer_type:
            raise ValueError("Topological distance requires shapes of the same type")
        if obj.topo_parent is None:
            raise ValueError("Topological distance requires shapes with a topo_parent")
        if not parent.is_same(obj.topo_parent):
            raise ValueError("Topological distance requires a shared topo_parent")

        graph_distance = distances.get(obj, inf)
        return graph_distance

    return key_f


class ShapeList(list[T]):
    """Subclass of list with custom filter and sort methods appropriate to CAD"""

    build123d_type: ClassVar[str] = "ShapeList"

    # ---- Properties ----

    @property
    def first(self) -> T:
        """First element in the ShapeList"""
        return self[0]

    @property
    def last(self) -> T:
        """Last element in the ShapeList"""
        return self[-1]

    # ---- Instance Methods ----

    def __add__(self, other: Shape | Iterable[Shape]) -> ShapeList[T]:  # type: ignore
        """Return a new ShapeList that includes other"""
        if isinstance(other, (Vector, Shape)):
            return ShapeList(tcast(list[T], list(self) + [other]))
        if isinstance(other, Iterable) and all(
            isinstance(o, (Shape, Vector)) for o in other
        ):
            return ShapeList(list(self) + list(other))
        raise TypeError(f"Cannot add object of type {type(other)} to ShapeList")

    def __iadd__(self, other: Shape | Iterable[Shape]) -> Self:  # type: ignore
        """In-place addition to this ShapeList"""
        if isinstance(other, (Vector, Shape)):
            self.append(tcast(T, other))
        elif isinstance(other, Iterable) and all(
            isinstance(o, (Shape, Vector)) for o in other
        ):
            self.extend(other)
        else:
            raise TypeError(f"Cannot add object of type {type(other)} to ShapeList")
        return self

    def __and__(self, other: ShapeList) -> ShapeList[T]:
        """Intersect two ShapeLists operator &"""
        return ShapeList(set(self) & set(other))

    def __eq__(self, other: object) -> bool:
        """ShapeLists equality operator =="""
        return (
            set(self) == set(other)
            if isinstance(other, ShapeList)
            else NotImplemented  # type: ignore
        )

    @overload
    def __getitem__(self, key: SupportsIndex) -> T: ...

    @overload
    def __getitem__(self, key: slice) -> ShapeList[T]: ...

    def __getitem__(self, key: SupportsIndex | slice) -> T | ShapeList[T]:
        """Return slices of ShapeList as ShapeList"""
        if isinstance(key, slice):
            return ShapeList(list(self).__getitem__(key))
        return list(self).__getitem__(key)

    def __gt__(self, sort_by: Axis | SortBy = Axis.Z) -> ShapeList[T]:  # type: ignore
        """Sort operator >"""
        return self.sort_by(sort_by)

    def __lshift__(self, group_by: Axis | SortBy = Axis.Z) -> ShapeList[T]:
        """Group and select smallest group operator <<"""
        return self.group_by(group_by)[0]

    def __lt__(self, sort_by: Axis | SortBy = Axis.Z) -> ShapeList[T]:  # type: ignore
        """Reverse sort operator <"""
        return self.sort_by(sort_by, reverse=True)

    # Normally implementing __eq__ is enough, but ShapeList subclasses list,
    # which already implements __ne__, so we need to override it, too
    def __ne__(self, other: ShapeList) -> bool:  # type: ignore
        """ShapeLists inequality operator !="""
        return (
            set(self) != set(other) if isinstance(other, ShapeList) else NotImplemented
        )

    def __or__(self, filter_by: Axis | GeomType = Axis.Z) -> ShapeList[T]:
        """Filter by axis or geomtype operator |"""
        return self.filter_by(filter_by)

    def __rshift__(self, group_by: Axis | SortBy = Axis.Z) -> ShapeList[T]:
        """Group and select largest group operator >>"""
        return self.group_by(group_by)[-1]

    def __sub__(self, other: ShapeList) -> ShapeList[T]:
        """Differences between two ShapeLists operator -"""
        return ShapeList(set(self) - set(other))

    def expand(self) -> ShapeList:
        """Expand by dissolving compounds, wires, and shells, filtering nulls.

        Returns:
            ShapeList with compounds dissolved to children, wires to edges,
            shells to faces, and nulls filtered out
        """
        expanded: ShapeList = ShapeList()
        for shape in self:
            if isinstance(shape, Vector):
                expanded.append(shape)
            elif hasattr(shape, "wrapped"):
                if isinstance(shape.wrapped, TopoDS_Compound):
                    # Recursively expand nested compounds
                    expanded.extend(ShapeList(list(shape)).expand())
                elif isinstance(shape.wrapped, TopoDS_Shell):
                    expanded.extend(shape.faces())
                elif isinstance(shape.wrapped, TopoDS_Wire):
                    expanded.extend(shape.edges())
                elif not shape.is_null:
                    expanded.append(shape)
        return expanded

    def center(self) -> Vector:
        """The average of the center of objects within the ShapeList"""
        if not self:
            return Vector(0, 0, 0)

        total_center = sum((o.center() for o in self), Vector(0, 0, 0))
        return total_center / len(self)

    def compound(self) -> Compound:
        """Return the Compound"""
        compounds = self.compounds()
        compound_count = len(compounds)
        if compound_count != 1:
            raise ValueError(f"Expected exactly one compound, found {compound_count}")
        return compounds[0]

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this ShapeList"""
        return ShapeList([c for shape in self for c in shape.compounds()])  # type: ignore

    def edge(self) -> Edge:
        """Return the Edge"""
        edges = self.edges()
        edge_count = len(edges)
        if edge_count != 1:
            raise ValueError(f"Expected exactly one edge, found {edge_count}")
        return edges[0]

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this ShapeList"""
        return ShapeList([e for shape in self for e in shape.edges()])  # type: ignore

    def face(self) -> Face:
        """Return the Face"""
        faces = self.faces()
        face_count = len(faces)
        if face_count != 1:
            raise ValueError(f"Expected exactly one face, found {face_count}")
        return faces[0]

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this ShapeList"""
        return ShapeList([f for shape in self for f in shape.faces()])  # type: ignore

    def filter_by(
        self,
        filter_by: Callable[[T], bool] | Axis | Plane | GeomType | property,
        reverse: bool = False,
        tolerance: float = 1e-5,
    ) -> ShapeList[T]:
        """filter by

        Either:
        - filter objects of type planar Face or linear Edge by their normal or tangent
        (respectively) and sort the results by the given axis, or
        - filter the objects by the provided type. Note that not all types apply to all
        objects.

        Args:
            filter_by (Callable[[T], bool] | Axis | Plane | GeomType): function, axis,
                plane, or geom type to filter and possibly sort by. Filtering by a plane
                returns faces/edges parallel to that plane.
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
                if (
                    isinstance(shape.wrapped, TopoDS_Face)
                    and GeomLib_IsPlanarSurface(
                        BRep_Tool.Surface_s(shape.wrapped), TOLERANCE
                    ).IsPlanar()
                ):
                    gp_pnt = gp_Pnt()
                    surface_normal = gp_Vec()
                    u_val, _, v_val, _ = BRepTools.UVBounds_s(shape.wrapped)
                    BRepGProp_Face(shape.wrapped).Normal(
                        u_val, v_val, gp_pnt, surface_normal
                    )
                    normalized_surface_normal = Vector(
                        surface_normal.X(), surface_normal.Y(), surface_normal.Z()
                    ).normalized()
                    shape_axis = Axis(shape.center(), normalized_surface_normal)
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

            def pred(shape: Shape):

                if (
                    isinstance(shape.wrapped, TopoDS_Face)
                    and GeomLib_IsPlanarSurface(
                        BRep_Tool.Surface_s(shape.wrapped), TOLERANCE
                    ).IsPlanar()
                ):
                    gp_pnt: gp_Pnt = gp_Pnt()
                    surface_normal: gp_Vec = gp_Vec()
                    u_val, _, v_val, _ = BRepTools.UVBounds_s(shape.wrapped)
                    BRepGProp_Face(shape.wrapped).Normal(
                        u_val, v_val, gp_pnt, surface_normal
                    )
                    normalized_surface_normal = Vector(surface_normal).normalized()
                    shape_axis = Axis(shape.center(), normalized_surface_normal)
                    return plane_axis.is_parallel(shape_axis, tolerance)
                if isinstance(shape.wrapped, TopoDS_Wire):
                    return all(pred(e) for e in shape.edges())
                if isinstance(shape.wrapped, TopoDS_Edge):
                    if shape.location is None:
                        return False
                    plane_xyz = tcast(
                        gp_XYZ,
                        (
                            tcast(Plane, Location(shape.location).inverse() * plane)
                        ).z_dir.wrapped.XYZ(),
                    )
                    t_edge = tcast(BRep_TEdge, shape.wrapped.TShape())
                    for curve in t_edge.Curves():
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
        elif isinstance(filter_by, property):

            def predicate(obj):
                return filter_by.__get__(obj)  # pylint: disable=unnecessary-dunder-call

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
                <= Plane(axis).to_local_coords(o).center().Z
                <= maximum,
                self,
            )
        elif inclusive == (True, False):
            objects = filter(
                lambda o: minimum
                <= Plane(axis).to_local_coords(o).center().Z
                < maximum,
                self,
            )
        elif inclusive == (False, True):
            objects = filter(
                lambda o: minimum
                < Plane(axis).to_local_coords(o).center().Z
                <= maximum,
                self,
            )
        else:  # inclusive == (False, False):
            objects = filter(
                lambda o: minimum < Plane(axis).to_local_coords(o).center().Z < maximum,
                self,
            )

        return ShapeList(objects).sort_by(axis)

    def group_by(
        self,
        group_by: Callable[[T], K] | Axis | Edge | Wire | SortBy | property = Axis.Z,
        reverse: bool = False,
        tol_digits: int = 6,
    ) -> GroupBy[T, K]:
        """group by

        Group objects by provided criteria and then sort the groups according to the criteria.
        Note that not all group_by criteria apply to all objects.

        Args:
            group_by (Callable[[T], K] | Axis | Edge | Wire | SortBy | property,
                optional): group and sort criteria. Defaults to Axis.Z.
            reverse (bool, optional): flip order of sort. Defaults to False.
            tol_digits (int, optional): Tolerance for building the group keys by
                round(key, tol_digits)

        Returns:
            GroupBy[T, K]: sorted groups of ShapeLists
        """

        if isinstance(group_by, Axis):
            if group_by.wrapped is None:
                raise ValueError("Cannot group by an empty axis")
            assert group_by.location is not None
            axis_as_location = group_by.location.inverse()

            def key_f(obj):
                return round(
                    (axis_as_location * Location(obj.center())).position.Z,
                    tol_digits,
                )

        elif not group_by:
            raise ValueError("Cannot group by an empty object")

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

            def key_f(obj):
                val = group_by(obj)
                try:
                    return round(val, tol_digits)
                except TypeError:
                    return val

        elif isinstance(group_by, property):

            def key_f(obj):
                val = group_by.__get__(obj)  # pylint: disable=unnecessary-dunder-call
                try:
                    return round(val, tol_digits)
                except TypeError:
                    return val

        else:
            raise ValueError(f"Unsupported group_by function: {group_by}")

        # pylint: disable=possibly-used-before-assignment
        return GroupBy(key_f, self, reverse=reverse)

    def shell(self) -> Shell:
        """Return the Shell"""
        shells = self.shells()
        shell_count = len(shells)
        if shell_count != 1:
            raise ValueError(f"Expected exactly one shell, found {shell_count}")
        return shells[0]

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this ShapeList"""
        return ShapeList([s for shape in self for s in shape.shells()])  # type: ignore

    def solid(self) -> Solid:
        """Return the Solid"""
        solids = self.solids()
        solid_count = len(solids)
        if solid_count != 1:
            raise ValueError(f"Expected exactly one solid, found {solid_count}")
        return solids[0]

    def solids(self) -> ShapeList[Solid]:
        """solids - all the solids in this ShapeList"""
        return ShapeList([s for shape in self for s in shape.solids()])  # type: ignore

    def sort_by(
        self,
        sort_by: Callable[[T], K] | Axis | Edge | Wire | SortBy | property = Axis.Z,
        reverse: bool = False,
    ) -> ShapeList[T]:
        """sort by

        Sort objects by provided criteria. Note that not all sort_by criteria apply to all
        objects.

        Args:
            sort_by (Callable[[T], K] | Axis | Edge | Wire | SortBy | property,
                optional): sort criteria. Defaults to Axis.Z.
            reverse (bool, optional): flip order of sort. Defaults to False.

        Raises:
            ValueError: Cannot sort by an empty axis
            ValueError: Cannot sort by an empty object
            ValueError: Invalid sort_by criteria provided

        Returns:
            ShapeList: sorted list of objects
        """

        if callable(sort_by):
            # If a callable is provided, use it directly as the key
            objects = sorted(self, key=sort_by, reverse=reverse)

        elif isinstance(sort_by, property):
            objects = sorted(self, key=sort_by.__get__, reverse=reverse)

        elif isinstance(sort_by, Axis):
            if sort_by.wrapped is None:
                raise ValueError("Cannot sort by an empty axis")
            assert sort_by.location is not None
            axis_as_location = sort_by.location.inverse()
            objects = sorted(
                self,
                key=lambda o: tcast(
                    Location, (axis_as_location * Location(o.center()))
                ).position.Z,
                reverse=reverse,
            )
        elif not sort_by:
            raise ValueError("Cannot sort by an empty object")
        elif hasattr(sort_by, "wrapped") and isinstance(
            sort_by.wrapped, (TopoDS_Edge, TopoDS_Wire)
        ):

            def u_of_closest_center(obj) -> float:
                """u-value of closest point between object center and sort_by"""
                assert not isinstance(sort_by, SortBy)
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
                with_radius = [obj for obj in self if hasattr(obj, "radius")]
                objects = sorted(
                    with_radius,
                    key=lambda obj: obj.radius,  # type: ignore
                    reverse=reverse,
                )
            elif sort_by == SortBy.DISTANCE:
                objects = sorted(
                    self,
                    key=lambda obj: obj.center().length,
                    reverse=reverse,
                )
            elif sort_by == SortBy.AREA:
                with_area = [obj for obj in self if hasattr(obj, "area")]
                objects = sorted(
                    with_area,
                    key=lambda obj: obj.area,  # type: ignore
                    reverse=reverse,
                )
            elif sort_by == SortBy.VOLUME:
                with_volume = [obj for obj in self if hasattr(obj, "volume")]
                objects = sorted(
                    with_volume,
                    key=lambda obj: obj.volume,  # type: ignore
                    reverse=reverse,
                )
        else:
            raise ValueError("Invalid sort_by criteria provided")

        return ShapeList(objects)  # pylint: disable=possibly-used-before-assignment

    def sort_by_distance(
        self, other: Shape | VectorLike, reverse: bool = False
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
            [(obj.distance_to(other), obj) for obj in self],  # type: ignore
            key=lambda obj: obj[0],
            reverse=reverse,
        )
        return ShapeList([obj[1] for obj in distances])

    def vertex(self) -> Vertex:
        """Return the Vertex"""
        vertices = self.vertices()
        vertex_count = len(vertices)
        if vertex_count != 1:
            raise ValueError(f"Expected exactly one vertex, found {vertex_count}")
        return vertices[0]

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this ShapeList"""
        return ShapeList([v for shape in self for v in shape.vertices()])  # type: ignore

    def wire(self) -> Wire:
        """Return the Wire"""
        wires = self.wires()
        wire_count = len(wires)
        if wire_count != 1:
            raise ValueError(f"Expected exactly one wire, found {wire_count}")
        return wires[0]

    def wires(self) -> ShapeList[Wire]:
        """wires - all the wires in this ShapeList"""
        return ShapeList([w for shape in self for w in shape.wires()])  # type: ignore


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

    relative_axis: Axis
    relative_location: Location

    # ---- Constructor ----

    def __init__(self, label: str, parent: BuildPart | Solid | Compound):
        self.label = label
        self.parent = parent
        self.connected_to: Joint | None = None

    def _reparent(self, parent: Solid | Compound) -> None:
        """Bind this joint to a new parent without changing its location."""
        relative_to_new_parent = parent.location.inverse() * self.parent.location
        if hasattr(self, "relative_location"):
            self.relative_location = relative_to_new_parent * self.relative_location
        elif hasattr(self, "relative_axis"):
            self.relative_axis = self.relative_axis.located(relative_to_new_parent)
        else:  # pragma: no cover - all current concrete joints use one representation
            raise TypeError(f"Unsupported joint type {type(self).__name__}")
        self.parent = parent

    # ---- Properties ----

    @property
    @abstractmethod
    def location(self) -> Location:
        """Location of joint"""

    @property
    @abstractmethod
    def symbol(self) -> Compound:
        """A CAD object positioned in global space to illustrate the joint"""

    # ---- Instance Methods ----

    @abstractmethod
    def connect_to(self, *args, **kwargs):
        """All derived classes must provide a connect_to method"""

    @abstractmethod
    def relative_to(self, *args, **kwargs) -> Location:
        """Return relative location to another joint"""

    def _connect_to(self, other: Joint, **kwargs):  # pragma: no cover
        """Connect Joint self by repositioning other"""

        if not isinstance(other, Joint):
            raise TypeError(f"other must of type Joint not {type(other)}")
        if self.parent.location is None:
            raise ValueError("Parent location is not set")
        relative_location = self.relative_to(other, **kwargs)
        other.parent.locate(tcast(Location, self.parent.location * relative_location))
        self.connected_to = other


class SkipClean:
    """Skip clean context for use in operator driven code where clean=False wouldn't work"""

    clean = True
    # ---- Instance Methods ----

    def __enter__(self):
        SkipClean.clean = False

    def __exit__(self, exception_type, exception_value, traceback):
        SkipClean.clean = True


def _sew_topods_faces(faces: Iterable[TopoDS_Face]) -> TopoDS_Shape:
    """Sew faces into a shell if possible"""
    shell_builder = BRepBuilderAPI_Sewing()
    for face in faces:
        shell_builder.Add(face)
    shell_builder.Perform()
    return downcast(shell_builder.SewedShape())


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
    args = list(args)
    tools = list(tools)
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


def _topods_entities(shape: TopoDS_Shape, topo_type: Shapes) -> list[TopoDS_Shape]:
    """Return the TopoDS_Shapes of topo_type from this TopoDS_Shape"""
    out = {}  # using dict to prevent duplicates

    explorer = TopExp_Explorer(shape, Shape.inverse_shape_LUT[topo_type])

    while explorer.More():
        item = explorer.Current()
        out[hash(item)] = item  # needed to avoid pseudo-duplicate entities
        explorer.Next()

    return list(out.values())


def _topods_face_normal_at(face: TopoDS_Face, surface_point: gp_Pnt) -> Vector:
    """Find the normal at a point on surface"""
    surface = BRep_Tool.Surface_s(face)

    # project point on surface
    projector = GeomAPI_ProjectPointOnSurf(surface_point, surface)
    u_val, v_val = projector.LowerDistanceParameters()

    gp_pnt = gp_Pnt()
    normal = gp_Vec()
    BRepGProp_Face(face).Normal(u_val, v_val, gp_pnt, normal)

    return Vector(normal).normalized()


def downcast(obj: TopoDS_Shape) -> TopoDS_Shape:
    """Downcasts a TopoDS object to suitable specialized type

    Args:
      obj: TopoDS_Shape:

    Returns:

    """

    f_downcast: Any = Shape.downcast_LUT[shapetype(obj)]
    return_value = f_downcast(obj)

    return return_value


def fix(obj: TopoDS_Shape) -> TopoDS_Shape:
    """Fix a TopoDS object to suitable specialized type

    Args:
      obj: TopoDS_Shape:

    Returns:

    """

    shape_fix = ShapeFix_Shape(obj)
    shape_fix.Perform()

    return downcast(shape_fix.Shape())


def get_top_level_topods_shapes(
    topods_shape: TopoDS_Shape | None,
) -> list[TopoDS_Shape]:
    """
    Retrieve the first level of child shapes from the shape.

    This method collects all the non-compound shapes directly contained in the
    current shape. If the wrapped shape is a `TopoDS_Compound`, it traverses
    its immediate children and collects all shapes that are not further nested
    compounds. Nested compounds are traversed to gather their non-compound elements
    without returning the nested compound itself.

    Returns:
        list[TopoDS_Shape]: A list of all first-level non-compound child shapes.

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

    return first_level_shapes


def shapetype(obj: TopoDS_Shape | None) -> TopAbs_ShapeEnum:
    """Return TopoDS_Shape's TopAbs_ShapeEnum"""
    if obj is None or obj.IsNull():
        raise ValueError("Null TopoDS_Shape object")

    return obj.ShapeType()


def topods_dim(topods: TopoDS_Shape) -> int | None:
    """Return the dimension of this TopoDS_Shape"""
    shape_dim_map = {
        (TopoDS_Vertex,): 0,
        (TopoDS_Edge, TopoDS_Wire): 1,
        (TopoDS_Face, TopoDS_Shell): 2,
        (TopoDS_Solid,): 3,
    }

    for shape_types, dim in shape_dim_map.items():
        if isinstance(topods, shape_types):
            return dim

    if isinstance(topods, TopoDS_Compound):
        sub_dims = {topods_dim(s) for s in get_top_level_topods_shapes(topods)}
        return sub_dims.pop() if len(sub_dims) == 1 else None

    return None


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


def _make_topods_compound_from_shapes(
    occt_shapes: Iterable[TopoDS_Shape | None],
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
        if shape is not None:
            comp_builder.Add(comp, shape)

    return comp
