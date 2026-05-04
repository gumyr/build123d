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
from collections.abc import Callable, Iterable, Iterator
from functools import reduce
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

import OCP.GeomAbs as ga
import OCP.TopAbs as ta
from anytree import NodeMixin, RenderTree
from IPython.lib.pretty import RepresentationPrinter, pretty
from OCP.Bnd import Bnd_Box, Bnd_OBB
from OCP.BOPAlgo import BOPAlgo_GlueEnum
from OCP.BRep import BRep_TEdge, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
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
from OCP.BRepFeat import BRepFeat_SplitShape
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCP.BRepTools import BRepTools
from OCP.gce import gce_MakeLin
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.GeomLib import GeomLib_IsPlanarSurface
from OCP.gp import gp_Ax1, gp_Ax2, gp_Ax3, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec, gp_XYZ
from OCP.GProp import GProp_GProps
from OCP.ShapeAnalysis import ShapeAnalysis_Curve
from OCP.ShapeCustom import ShapeCustom, ShapeCustom_RestrictionParameters
from OCP.ShapeFix import ShapeFix_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import (
    TopoDS,
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
    TopTools_SequenceOfShape,
)
from typing_extensions import Self, deprecated

from build123d.build_enums import CenterOf, GeomType, Keep, SortBy, Transition
from build123d.geometry import (
    DEG2RAD,
    TOLERANCE,
    Axis,
    BoundBox,
    Color,
    ColorLike,
    Location,
    Matrix,
    NotAllLocationLikeError,
    OrientedBoundBox,
    Plane,
    Vector,
    VectorLike,
    all_location_like,
    logger,
)

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

    composite_factories: ClassVar[dict[int | None, CompositeFactory]] = {}

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

        # parent must be set following children as post install accesses children
        self.parent = parent

        # Extracted objects like Vertices and Edges may need to know where they came from
        self.topo_parent: Shape | None = None

    # ---- Properties ----

    # pylint: disable=too-many-instance-attributes, too-many-public-methods

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
    @deprecated(
        "The 'is_planar_face' property is deprecated and will be removed in a future version."
        " Use 'Face.is_planar' instead"
    )
    def is_planar_face(self) -> bool:
        """Is the shape a planar face even though its geom_type may not be PLANE"""
        if self._wrapped is None or not isinstance(self.wrapped, TopoDS_Face):
            return False
        surface = BRep_Tool.Surface_s(self.wrapped)
        is_face_planar = GeomLib_IsPlanarSurface(surface, TOLERANCE)
        return is_face_planar.IsPlanar()

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
        if self.location is None:
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
    @abstractmethod
    def cast(cls: type[Self], obj: TopoDS_Shape) -> Self:
        """Returns the right type of wrapper, given a OCCT object"""

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
            total_mass = sum(Shape.compute_mass(o) for o in objects)
            weighted_centers = [
                o.center(CenterOf.MASS).multiply(Shape.compute_mass(o)) for o in objects
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

    @staticmethod
    def compute_mass(obj: Shape) -> float:
        """Calculates the 'mass' of an object.

        Args:
          obj: Compute the mass of this object
          obj: Shape:

        Returns:

        """
        if not obj:
            return 0.0

        properties = GProp_GProps()
        calc_function = Shape.shape_properties_LUT[shapetype(obj.wrapped)]

        if calc_function is None:
            raise NotImplementedError

        calc_function(obj.wrapped, properties)
        return properties.Mass()

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

    @staticmethod
    def get_single_shape(
        shape: Shape,
        entity_type: Literal[
            "Vertex", "Edge", "Wire", "Face", "Shell", "Solid", "Compound"
        ],
    ) -> Shape | None:
        """Helper to extract a single entity of a specific type from a shape,
        with a warning if count != 1."""
        shape_list = Shape.get_shape_list(shape, entity_type)
        entity_count = len(shape_list)
        if entity_count == 0:
            return None
        if entity_count > 1:
            warnings.warn(
                f"Found {entity_count} {entity_type.lower()}s, returning first",
                stacklevel=3,
            )
        return shape_list[0] if shape_list else None

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

    def __add__(self, other: None | Shape | Iterable[Shape]) -> Self | Compound:
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

        if SkipClean.clean and not isinstance(sum_shape, list):
            sum_shape = sum_shape.clean()

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
        if isinstance(other, Location | Plane):
            return self.moved(other)
        try:
            return [self.moved(loc) for loc in all_location_like(other)]
        except NotAllLocationLikeError as e:
            raise TypeError(f"{type(self).__name__} cannot be multiplied by {e}") from e
        except TypeError:  # not iterable
            pass
        raise TypeError(
            f"{type(self).__name__} cannot be multiplied by {type(other).__name__}"
        )

    def __sub__(self, other: None | Shape | Iterable[Shape]) -> Self | Compound:
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

    def bounding_box(
        self, tolerance: float | None = None, optimal: bool = True
    ) -> BoundBox:
        """Create a bounding box for this Shape.

        Args:
            tolerance (float, optional): Defaults to None.

        Returns:
            BoundBox: A box sized to contain this Shape
        """
        if self._wrapped is None:
            return BoundBox(Bnd_Box())
        tolerance = TOLERANCE if tolerance is None else tolerance
        return BoundBox.from_topo_ds(self.wrapped, tolerance=tolerance, optimal=optimal)

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
        try:
            upgrader.Build()
            self.wrapped = tcast(TOPODS, downcast(upgrader.Shape()))
        except Exception:
            warnings.warn(f"Unable to clean {self}", stacklevel=2)
        return self

    def closest_points(self, other: Shape | VectorLike) -> tuple[Vector, Vector]:
        """Points on two shapes where the distance between them is minimal"""
        return self.distance_to_with_closest_points(other)[1:3]

    def compound(self) -> Compound | None:
        """Return the Compound"""
        return None

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

    def edge(self) -> Edge | None:
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

    def face(self) -> Face | None:
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

    def relocate(self, loc: Location):
        """Change the location of self while keeping it geometrically similar

        Args:
            loc (Location): new location to set for self
        """
        warnings.warn(
            "The 'relocate' method is deprecated and will be removed in a future version."
            "Use move, moved, locate, or located instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if self._wrapped is None:
            raise ValueError("Cannot relocate an empty shape")

        if self.location != loc:
            old_ax = gp_Ax3()
            old_ax.Transform(self.location.wrapped.Transformation())

            new_ax = gp_Ax3()
            new_ax.Transform(loc.wrapped.Transformation())

            trsf = gp_Trsf()
            trsf.SetDisplacement(new_ax, old_ax)
            builder = BRepBuilderAPI_Transform(self.wrapped, trsf, True, True)

            self.wrapped = tcast(TOPODS, downcast(builder.Shape()))
            self.wrapped.Location(loc.wrapped)

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

    def scale(self, factor: float) -> Self:
        """Scales this shape through a transformation.

        Args:
          factor: float:

        Returns:

        """

        transformation = gp_Trsf()
        transformation.SetScale(gp_Pnt(), factor)

        return self._apply_transform(transformation)

    def shell(self) -> Shell | None:
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

    def solid(self) -> Solid | None:
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

    @overload
    def split_by_perimeter(
        self, perimeter: Edge | Wire, keep: Literal[Keep.INSIDE, Keep.OUTSIDE]
    ) -> Face | Shell | ShapeList[Face] | None:
        """split_by_perimeter and keep inside or outside"""

    @overload
    def split_by_perimeter(
        self, perimeter: Edge | Wire, keep: Literal[Keep.BOTH]
    ) -> tuple[
        Face | Shell | ShapeList[Face] | None,
        Face | Shell | ShapeList[Face] | None,
    ]:
        """split_by_perimeter and keep inside and outside"""

    @overload
    def split_by_perimeter(
        self, perimeter: Edge | Wire
    ) -> Face | Shell | ShapeList[Face] | None:
        """split_by_perimeter and keep inside (default)"""

    def split_by_perimeter(self, perimeter: Edge | Wire, keep: Keep = Keep.INSIDE):
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
            Union[Face | Shell | ShapeList[Face] | None,
            Tuple[Face | Shell | ShapeList[Face] | None]: The result of the split operation.

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
            # if not sides:
            #     return None
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

        if self._wrapped is None:
            raise ValueError("Cannot split an empty shape")

        # Process the perimeter
        if not perimeter.is_closed:
            raise ValueError("perimeter must be a closed Wire or Edge")
        perimeter_edges = TopTools_SequenceOfShape()
        for perimeter_edge in perimeter.edges():
            if not perimeter_edge:
                continue
            perimeter_edges.Append(perimeter_edge.wrapped)

        # Split the shells by the perimeter edges
        lefts: list[Shell] = []
        rights: list[Shell] = []
        for target_shell in self.shells():
            if not target_shell:
                continue
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

    def wire(self) -> Wire | None:
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
            if obj.wrapped is not None:
                arg.Append(obj.wrapped)

        tool = TopTools_ListOfShape()
        for obj in tools:
            if obj.wrapped is not None:
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

        from build123d.jupyter_tools import shape_to_html, HAS_VTK

        if HAS_VTK:
            return shape_to_html(self)._repr_html_()
        return repr(self)

    def vertex(self) -> Vertex | None:
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


class ShapePredicate(Protocol):
    """Predicate for shape filters"""

    # ---- Instance Methods ----

    def __call__(self, shape: Shape) -> bool: ...


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


class ShapeList(list[T]):
    """Subclass of list with custom filter and sort methods appropriate to CAD"""

    # ---- Properties ----

    # pylint: disable=too-many-public-methods

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
            warnings.warn(
                f"Found {compound_count} compounds, returning first", stacklevel=2
            )
        return compounds[0]

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this ShapeList"""
        return ShapeList([c for shape in self for c in shape.compounds()])  # type: ignore

    def edge(self) -> Edge:
        """Return the Edge"""
        edges = self.edges()
        edge_count = len(edges)
        if edge_count != 1:
            warnings.warn(f"Found {edge_count} edges, returning first", stacklevel=2)
        return edges[0]

    def edges(self) -> ShapeList[Edge]:
        """edges - all the edges in this ShapeList"""
        return ShapeList([e for shape in self for e in shape.edges()])  # type: ignore

    def face(self) -> Face:
        """Return the Face"""
        faces = self.faces()
        face_count = len(faces)
        if face_count != 1:
            msg = f"Found {face_count} faces, returning first"
            warnings.warn(msg, stacklevel=2)
        return faces[0]

    def faces(self) -> ShapeList[Face]:
        """faces - all the faces in this ShapeList"""
        return ShapeList([f for shape in self for f in shape.faces()])  # type: ignore

    def filter_by(
        self,
        filter_by: ShapePredicate | Axis | Plane | GeomType | property,
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
        group_by: (
            Callable[[Shape], K] | Axis | Edge | Wire | SortBy | property
        ) = Axis.Z,
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
            warnings.warn(f"Found {shell_count} shells, returning first", stacklevel=2)
        return shells[0]

    def shells(self) -> ShapeList[Shell]:
        """shells - all the shells in this ShapeList"""
        return ShapeList([s for shape in self for s in shape.shells()])  # type: ignore

    def solid(self) -> Solid:
        """Return the Solid"""
        solids = self.solids()
        solid_count = len(solids)
        if solid_count != 1:
            warnings.warn(f"Found {solid_count} solids, returning first", stacklevel=2)
        return solids[0]

    def solids(self) -> ShapeList[Solid]:
        """solids - all the solids in this ShapeList"""
        return ShapeList([s for shape in self for s in shape.solids()])  # type: ignore

    def sort_by(
        self,
        sort_by: Axis | Callable[[T], K] | Edge | Wire | SortBy | property = Axis.Z,
        reverse: bool = False,
    ) -> ShapeList[T]:
        """sort by

        Sort objects by provided criteria. Note that not all sort_by criteria apply to all
        objects.

        Args:
            sort_by (Axis | Callable[[T], K] | Edge | Wire | SortBy, optional): sort criteria.
               Defaults to Axis.Z.
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
            warnings.warn(
                f"Found {vertex_count} vertices, returning first", stacklevel=2
            )
        return vertices[0]

    def vertices(self) -> ShapeList[Vertex]:
        """vertices - all the vertices in this ShapeList"""
        return ShapeList([v for shape in self for v in shape.vertices()])  # type: ignore

    def wire(self) -> Wire:
        """Return the Wire"""
        wires = self.wires()
        wire_count = len(wires)
        if wire_count != 1:
            warnings.warn(f"Found {wire_count} wires, returning first", stacklevel=2)
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

    # ---- Constructor ----

    def __init__(self, label: str, parent: BuildPart | Solid | Compound):
        self.label = label
        self.parent = parent
        self.connected_to: Joint | None = None

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
