"""
build123d topology

name: three_d.py
by:   Gumyr
date: January 07, 2025

desc:

This module defines the `Solid` class and associated methods for creating, manipulating, and
querying three-dimensional solid geometries in the build123d CAD system. It provides powerful tools
for constructing complex 3D models, including operations such as extrusion, sweeping, filleting,
chamfering, and Boolean operations. The module integrates with OpenCascade to leverage its robust
geometric kernel for precise 3D modeling.

Key Features:
- **Solid Class**:
  - Represents closed, bounded 3D shapes with methods for volume calculation, bounding box
    computation, and validity checks.
  - Includes constructors for primitive solids (e.g., box, cylinder, cone, torus) and advanced
    operations like lofting, revolving, and sweeping profiles along paths.

- **Mixin3D**:
  - Adds shared methods for operations like filleting, chamfering, splitting, and hollowing solids.
  - Supports advanced workflows such as finding maximum fillet radii and extruding with rotation or
    taper.

- **Boolean Operations**:
  - Provides utilities for union, subtraction, and intersection of solids.

- **Thickening and Offsetting**:
  - Allows transformation of faces or shells into solids through thickening.

This module is essential for generating and manipulating complex 3D geometries in the build123d
library, offering a comprehensive API for CAD modeling.

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

from collections.abc import Iterable, Sequence
from math import radians, cos, tan
from typing import TYPE_CHECKING, Literal
from typing_extensions import Self

import OCP.TopAbs as ta
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Section
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepFeat import BRepFeat_MakeDPrism
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer, BRepFilletAPI_MakeFillet
from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Skin
from OCP.BRepOffsetAPI import (
    BRepOffsetAPI_DraftAngle,
    BRepOffsetAPI_MakePipeShell,
    BRepOffsetAPI_MakeThickSolid,
)
from OCP.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCone,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakeRevol,
    BRepPrimAPI_MakeSphere,
    BRepPrimAPI_MakeTorus,
    BRepPrimAPI_MakeWedge,
)
from OCP.GProp import GProp_GProps
from OCP.GeomAbs import GeomAbs_Intersection, GeomAbs_JoinType
from OCP.LocOpe import LocOpe_DPrism
from OCP.ShapeFix import ShapeFix_Solid
from OCP.Standard import Standard_Failure, Standard_TypeMismatch
from OCP.StdFail import StdFail_NotDone
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_ListOfShape
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Wire,
)
from OCP.gp import gp_Ax2, gp_Pnt
from build123d.build_enums import CenterOf, GeomType, Keep, Kind, Transition, Until
from build123d.geometry import (
    DEG2RAD,
    TOLERANCE,
    Axis,
    BoundBox,
    Color,
    Location,
    OrientedBoundBox,
    Plane,
    Vector,
    VectorLike,
)

from .one_d import Edge, Wire, Mixin1D
from .shape_core import (
    TOPODS,
    Shape,
    ShapeList,
    Joint,
    downcast,
    shapetype,
    _sew_topods_faces,
    get_top_level_topods_shapes,
    unwrap_topods_compound,
)

from .two_d import sort_wires_by_build_order, Mixin2D, Face, Shell
from .utils import (
    _extrude_topods_shape,
    find_max_dimension,
    _make_loft,
    _make_topods_compound_from_shapes,
)
from .zero_d import Vertex


if TYPE_CHECKING:  # pragma: no cover
    from .composite import Compound  # pylint: disable=R0801


class Mixin3D(Shape[TOPODS]):
    """Additional methods to add to 3D Shape classes"""

    find_intersection_points = Mixin2D.find_intersection_points

    # ---- Properties ----

    @property
    def _dim(self) -> int | None:
        """Dimension of Solids"""
        return 3

    # ---- Class Methods ----

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

    @classmethod
    def extrude(
        cls, obj: Shape, direction: VectorLike
    ) -> Edge | Face | Shell | Solid | Compound:
        """Unused - only here because Mixin1D is a subclass of Shape"""
        return NotImplemented

    # ---- Instance Methods ----

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
            assert calc_function is not None
            calc_function(self.wrapped, properties)
            middle = Vector(properties.CentreOfMass())
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    def chamfer(
        self,
        length: float,
        length2: float | None,
        edge_list: Iterable[Edge],
        face: Face | None = None,
    ) -> Self:
        """Chamfer

        Chamfers the specified edges of this solid.

        Args:
            length (float): length > 0, the length (length) of the chamfer
            length2 (Optional[float]): length2 > 0, optional parameter for asymmetrical
                chamfer. Should be `None` if not required.
            edge_list (Iterable[Edge]): a list of Edge objects, which must belong to
                this solid
            face (Face, optional): identifies the side where length is measured. The edge(s)
                must be part of the face

        Returns:
            Self:  Chamfered solid
        """
        edge_list = list(edge_list)
        if face:
            if any(edge for edge in edge_list if edge not in face.edges()):
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
            if not new_shape.is_valid:
                raise Standard_Failure
        except (StdFail_NotDone, Standard_Failure) as err:
            raise ValueError(
                "Failed creating a chamfer, try a smaller length value(s)"
            ) from err

        return new_shape

    def dprism(
        self,
        basis: Face | None,
        bounds: list[Face | Wire],
        depth: float | None = None,
        taper: float = 0,
        up_to_face: Face | None = None,
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

        shape: TopoDS_Shape | TopoDS_Solid = self.wrapped
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
            if not new_shape.is_valid:
                raise Standard_Failure
        except (StdFail_NotDone, Standard_Failure) as err:
            raise ValueError(
                f"Failed creating a fillet with radius of {radius}, try a smaller value"
                f" or use max_fillet() to find the largest valid fillet radius"
            ) from err

        return new_shape

    def hollow(
        self,
        faces: Iterable[Face] | None,
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
        faces = list(faces) if faces else []
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
            return_value = self.__class__.cast(shell_builder.Shape())

        else:  # if no faces provided a watertight solid will be constructed
            shell1 = self.__class__.cast(shell_builder.Shape()).shells()[0].wrapped
            shell2 = self.shells()[0].wrapped

            # s1 can be outer or inner shell depending on the thickness sign
            if thickness > 0:
                sol = BRepBuilderAPI_MakeSolid(shell1, shell2)
            else:
                sol = BRepBuilderAPI_MakeSolid(shell2, shell1)

            # fix needed for the orientations
            return_value = self.__class__.cast(sol.Shape()).fix()

        return return_value

    def intersect(
        self, *to_intersect: Shape | Vector | Location | Axis | Plane
    ) -> None | ShapeList[Vertex | Edge | Face | Solid]:
        """Intersect Solid with Shape or geometry object

        Args:
            to_intersect (Shape | Vector | Location | Axis | Plane): objects to intersect

        Returns:
            ShapeList[Vertex | Edge | Face | Solid] | None: ShapeList of vertices, edges,
                faces, and/or solids.
        """

        def to_vector(objs: Iterable) -> ShapeList:
            return ShapeList([Vector(v) if isinstance(v, Vertex) else v for v in objs])

        def to_vertex(objs: Iterable) -> ShapeList:
            return ShapeList([Vertex(v) if isinstance(v, Vector) else v for v in objs])

        def bool_op(
            args: Sequence,
            tools: Sequence,
            operation: BRepAlgoAPI_Common | BRepAlgoAPI_Section,
        ) -> ShapeList:
            # Wrap Shape._bool_op for corrected output
            intersections: Shape | ShapeList = Shape()._bool_op(args, tools, operation)
            if isinstance(intersections, ShapeList):
                return intersections or ShapeList()
            if isinstance(intersections, Shape) and not intersections.is_null:
                return ShapeList([intersections])
            return ShapeList()

        def filter_shapes_by_order(shapes: ShapeList, orders: list) -> ShapeList:
            # Remove lower order shapes from list which *appear* to be part of
            # a higher order shape using a lazy distance check
            # (sufficient for vertices, may be an issue for higher orders)
            order_groups = []
            for order in orders:
                order_groups.append(
                    ShapeList([s for s in shapes if isinstance(s, order)])
                )

            filtered_shapes = order_groups[-1]
            for i in range(len(order_groups) - 1):
                los = order_groups[i]
                his: list = sum(order_groups[i + 1 :], [])
                filtered_shapes.extend(
                    ShapeList(
                        lo
                        for lo in los
                        if all(lo.distance_to(hi) > TOLERANCE for hi in his)
                    )
                )

            return filtered_shapes

        common_set: ShapeList[Vertex | Edge | Face | Solid] = ShapeList([self])
        target: Shape
        for other in to_intersect:
            # Conform target type
            match other:
                case Axis():
                    # BRepAlgoAPI_Section seems happier if Edge isnt infinite
                    bbox = self.bounding_box()
                    dist = self.distance_to(other.position)
                    dist = dist if dist >= 1 else 1
                    target = Edge.make_line(
                        other.position - other.direction * bbox.diagonal * dist,
                        other.position + other.direction * bbox.diagonal * dist,
                    )
                case Plane():
                    target = Face(other)
                case Vector():
                    target = Vertex(other)
                case Location():
                    target = Vertex(other.position)
                case _ if issubclass(type(other), Shape):
                    target = other
                case _:
                    raise ValueError(f"Unsupported type to_intersect: {type(other)}")

            # Find common matches
            common: list[Vertex | Edge | Wire | Face | Shell | Solid] = []
            result: ShapeList | None
            for obj in common_set:
                match (obj, target):
                    case (_, Vertex() | Edge() | Wire() | Face() | Shell() | Solid()):
                        operation: BRepAlgoAPI_Section | BRepAlgoAPI_Common = (
                            BRepAlgoAPI_Section()
                        )
                        result = bool_op((obj,), (target,), operation)
                        if (
                            not isinstance(obj, Edge | Wire)
                            and not isinstance(target, (Edge | Wire))
                        ) or (isinstance(obj, Solid) or isinstance(target, Solid)):
                            # Face + Edge combinations may produce an intersection
                            # with Common but always with Section.
                            # No easy way to deduplicate
                            # Many Solid + Edge combinations need Common
                            operation = BRepAlgoAPI_Common()
                            result.extend(bool_op((obj,), (target,), operation))

                    case _ if issubclass(type(target), Shape):
                        result = target.intersect(obj)

                if result:
                    common.extend(result)

            if common:
                common_set = ShapeList()
                for shape in common:
                    if isinstance(shape, Wire):
                        common_set.extend(shape.edges())
                    elif isinstance(shape, Shell):
                        common_set.extend(shape.faces())
                    else:
                        common_set.append(shape)
                common_set = to_vertex(set(to_vector(common_set)))
                common_set = filter_shapes_by_order(
                    common_set, [Vertex, Edge, Face, Solid]
                )
            else:
                return None

        return ShapeList(common_set)

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
        solid_classifier.Perform(gp_Pnt(*Vector(point)), tolerance)

        return solid_classifier.State() == ta.TopAbs_IN or solid_classifier.IsOnAFace()

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
                if not new_shape.is_valid:
                    # raise fillet_exception
                    raise Standard_Failure
            # except fillet_exception:
            except (Standard_Failure, StdFail_NotDone):
                return __max_fillet(window_min, window_mid, current_iteration + 1)

            # These numbers work, are they close enough? - if not try larger window
            if window_mid - window_min <= tolerance:
                return_value = window_mid
            else:
                return_value = __max_fillet(
                    window_mid, window_max, current_iteration + 1
                )
            return return_value

        if not self.is_valid:
            raise ValueError("Invalid Shape")

        native_edges = [e.wrapped for e in edge_list]

        # Unfortunately, MacOS doesn't support the StdFail_NotDone exception so platform
        # specific exceptions are required.
        # if platform.system() == "Darwin":
        #     fillet_exception = Standard_Failure
        # else:
        #     fillet_exception = StdFail_NotDone

        max_radius = __max_fillet(0.0, 2 * self.bounding_box().diagonal, 0)

        return max_radius

    def offset_3d(
        self,
        openings: Iterable[Face] | None,
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
        openings = list(openings) if openings else []
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

        offset_solid = self.__class__.cast(offset_occt_solid)
        assert offset_solid.wrapped is not None

        # The Solid can be inverted, if so reverse
        if offset_solid.volume < 0:
            offset_solid.wrapped.Reverse()

        return offset_solid

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


class Solid(Mixin3D[TopoDS_Solid]):
    """A Solid in build123d represents a three-dimensional solid geometry
    in a topological structure. A solid is a closed and bounded volume, enclosing
    a region in 3D space. It comprises faces, edges, and vertices connected in a
    well-defined manner. Solid modeling operations, such as Boolean
    operations (union, intersection, and difference), are often performed on
    Solid objects to create or modify complex geometries."""

    order = 3.0
    # ---- Constructor ----

    def __init__(
        self,
        obj: TopoDS_Solid | Shell | None = None,
        label: str = "",
        color: Color | None = None,
        material: str = "",
        joints: dict[str, Joint] | None = None,
        parent: Compound | None = None,
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

    # ---- Properties ----

    @property
    def volume(self) -> float:
        """volume - the volume of this Solid"""
        # when density == 1, mass == volume
        return Shape.compute_mass(self)

    # ---- Class Methods ----

    @classmethod
    def _make_solid(cls, shell: Shell) -> TopoDS_Solid:
        """Create a Solid object from the surface shell"""
        return ShapeFix_Solid().SolidFromShell(shell.wrapped)

    @classmethod
    def _set_sweep_mode(
        cls,
        builder: BRepOffsetAPI_MakePipeShell,
        path: Wire | Edge,
        binormal: Vector | Wire | Edge,
    ) -> bool:
        rotate = False

        if isinstance(binormal, Vector):
            coordinate_system = gp_Ax2()
            coordinate_system.SetLocation(path.start_point().to_pnt())
            coordinate_system.SetDirection(binormal.to_dir())
            builder.SetMode(coordinate_system)
            rotate = True
        elif isinstance(binormal, (Wire, Edge)):
            builder.SetMode(Wire(binormal).wrapped, True)

        return rotate

    @classmethod
    def extrude(cls, obj: Face, direction: VectorLike) -> Solid:
        """extrude

        Extrude a Face into a Solid.

        Args:
            direction (VectorLike): direction and magnitude of extrusion

        Raises:
            ValueError: Unsupported class
            RuntimeError: Generated invalid result

        Returns:
            Edge: extruded shape
        """
        return Solid(TopoDS.Solid_s(_extrude_topods_shape(obj.wrapped, direction)))

    @classmethod
    def extrude_linear_with_rotation(
        cls,
        section: Face | Wire,
        center: VectorLike,
        normal: VectorLike,
        angle: float,
        inner_wires: list[Wire] | None = None,
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
        difference = BRepAlgoAPI_Cut(outer_solid, inner_comp).Shape()

        # convert to a TopoDS_Solid - might be wrapped in a TopoDS_Compound
        try:
            result = TopoDS.Solid_s(difference)
        except Standard_TypeMismatch:
            result = TopoDS.Solid_s(
                unwrap_topods_compound(TopoDS.Compound_s(difference), True)
            )

        return Solid(result)

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
            new_solid = Solid(TopoDS.Solid_s(prism_builder.Shape()))
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
                taper_wire: Wire = Plane(profile).from_local_coords(local_taper)
                taper_wire.move(Location(direction))
                taper_wires.append(taper_wire)

            solids = [
                Solid.make_loft([p, t]) for p, t in zip(profile_wires, taper_wires)
            ]
            if len(solids) > 1:
                complex_solid = solids[0].cut(*solids[1:])
                assert isinstance(complex_solid, Solid)  # Can't be a list
                new_solid = complex_solid
            else:
                new_solid = solids[0]

        return new_solid

    @classmethod
    def extrude_until(
        cls,
        profile: Face,
        target: Compound | Solid,
        direction: VectorLike,
        until: Until = Until.NEXT,
    ) -> Solid:
        """extrude_until

        Extrude `profile` in the provided `direction` until it encounters a
        bounding surface on the `target`. The termination surface is chosen
        according to the `until` option:

            * ``Until.NEXT`` — Extrude forward until the first intersecting surface.
            * ``Until.LAST`` — Extrude forward through all intersections, stopping at
            the farthest surface.
            * ``Until.PREVIOUS`` — Reverse the extrusion direction and stop at the
            first intersecting surface behind the profile.
            * ``Until.FIRST`` — Reverse the direction and stop at the farthest
            surface behind the profile.

        When ``Until.PREVIOUS`` or ``Until.FIRST`` are used, the extrusion
        direction is automatically inverted before execution.

        Note:
            The bounding surface on the target must be large enough to
            completely cover the extruded profile at the contact region.
            Partial overlaps may yield open or invalid solids.

        Args:
            profile (Face): The face to extrude.
            target (Union[Compound, Solid]): The object that limits the extrusion.
            direction (VectorLike): Extrusion direction.
            until (Until, optional): Surface selection mode controlling which
                intersection to stop at. Defaults to ``Until.NEXT``.

        Raises:
            ValueError: If the provided profile does not intersect the target.

        Returns:
            Solid: The extruded and limited solid.
        """
        direction = Vector(direction)
        if until in [Until.PREVIOUS, Until.FIRST]:
            direction *= -1
            until = Until.NEXT if until == Until.PREVIOUS else Until.LAST

        # 1: Create extrusion of length the maximum distance between profile and target
        max_dimension = find_max_dimension([profile, target])
        extrusion = Solid.extrude(profile, direction * max_dimension)

        # 2: Intersect the extrusion with the target to find the target's modified faces
        intersect_op = BRepAlgoAPI_Common(target.wrapped, extrusion.wrapped)
        intersect_op.Build()
        intersection = intersect_op.Shape()
        face_exp = TopExp_Explorer(intersection, ta.TopAbs_FACE)
        if not face_exp.More():
            raise ValueError("No intersection: extrusion does not contact target")

        # Find the faces from the intersection that originated on the target
        history = intersect_op.History()
        modified_target_faces = []
        face_explorer = TopExp_Explorer(target.wrapped, ta.TopAbs_FACE)
        while face_explorer.More():
            target_face = TopoDS.Face_s(face_explorer.Current())
            modified_los: TopTools_ListOfShape = history.Modified(target_face)
            while not modified_los.IsEmpty():
                modified_face = TopoDS.Face_s(modified_los.First())
                modified_los.RemoveFirst()
                modified_target_faces.append(modified_face)
            face_explorer.Next()

        # 3: Sew the resulting faces into shells - one for each surface the extrusion
        #    passes through and sort by distance from the profile
        sewed_shape = _sew_topods_faces(modified_target_faces)

        # From the sewed shape extract the shells and single faces
        top_level_shapes = get_top_level_topods_shapes(sewed_shape)
        modified_target_surfaces: ShapeList[Face | Shell] = ShapeList()

        # For each of the top level Shells and Faces
        for top_level_shape in top_level_shapes:
            if isinstance(top_level_shape, TopoDS_Face):
                modified_target_surfaces.append(Face(top_level_shape))
            elif isinstance(top_level_shape, TopoDS_Shell):
                modified_target_surfaces.append(Shell(top_level_shape))
            else:
                raise RuntimeError(f"Invalid sewn shape {type(top_level_shape)}")

        modified_target_surfaces = modified_target_surfaces.sort_by(
            lambda s: s.distance_to(profile)
        )
        limit = modified_target_surfaces[
            0 if until in [Until.NEXT, Until.PREVIOUS] else -1
        ]
        keep: Literal[Keep.TOP, Keep.BOTTOM] = (
            Keep.TOP if until in [Until.NEXT, Until.PREVIOUS] else Keep.BOTTOM
        )

        # 4: Split the extrusion by the appropriate shell
        clipped_extrusion = extrusion.split(limit, keep=keep)

        # 5: Return the appropriate type
        if clipped_extrusion is None:
            raise RuntimeError("Extrusion is None")  # None isn't an option here
        elif isinstance(clipped_extrusion, Solid):
            return clipped_extrusion
        else:
            #  isinstance(clipped_extrusion, list):
            return ShapeList(clipped_extrusion).sort_by(
                Axis(profile.center(), direction)
            )[0]

    @classmethod
    def from_bounding_box(cls, bbox: BoundBox | OrientedBoundBox) -> Solid:
        """A box of the same dimensions and location"""
        if isinstance(bbox, BoundBox):
            return Solid.make_box(*bbox.size).locate(Location(bbox.min))
        else:
            moved_plane: Plane = Plane(Location(-bbox.size / 2)).move(bbox.location)
            return Solid.make_box(
                bbox.size.X, bbox.size.Y, bbox.size.Z, plane=moved_plane
            )

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
            TopoDS.Solid_s(
                BRepPrimAPI_MakeBox(
                    plane.to_gp_ax2(),
                    length,
                    width,
                    height,
                ).Shape()
            )
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
            TopoDS.Solid_s(
                BRepPrimAPI_MakeCone(
                    plane.to_gp_ax2(),
                    base_radius,
                    top_radius,
                    height,
                    angle * DEG2RAD,
                ).Shape()
            )
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
            TopoDS.Solid_s(
                BRepPrimAPI_MakeCylinder(
                    plane.to_gp_ax2(),
                    radius,
                    height,
                    angle * DEG2RAD,
                ).Shape()
            )
        )

    @classmethod
    def make_loft(cls, objs: Iterable[Vertex | Wire], ruled: bool = False) -> Solid:
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
        return cls(TopoDS.Solid_s(_make_loft(objs, True, ruled)))

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
            TopoDS.Solid_s(
                BRepPrimAPI_MakeSphere(
                    plane.to_gp_ax2(),
                    radius,
                    angle1 * DEG2RAD,
                    angle2 * DEG2RAD,
                    angle3 * DEG2RAD,
                ).Shape()
            )
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
            TopoDS.Solid_s(
                BRepPrimAPI_MakeTorus(
                    plane.to_gp_ax2(),
                    major_radius,
                    minor_radius,
                    start_angle * DEG2RAD,
                    end_angle * DEG2RAD,
                    major_angle * DEG2RAD,
                ).Shape()
            )
        )

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
            TopoDS.Solid_s(
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
        )

    @classmethod
    def revolve(
        cls,
        section: Face | Wire,
        angle: float,
        axis: Axis,
        inner_wires: list[Wire] | None = None,
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

        return cls(TopoDS.Solid_s(revol_builder.Shape()))

    @classmethod
    def sweep(
        cls,
        section: Face | Wire,
        path: Wire | Edge,
        inner_wires: list[Wire] | None = None,
        make_solid: bool = True,
        is_frenet: bool = False,
        mode: Vector | Wire | Edge | None = None,
        transition: Transition = Transition.TRANSFORMED,
    ) -> Solid:
        """Sweep

        Sweep the given cross section into a prismatic solid along the provided path

        The is_frenet parameter controls how the profile orientation changes as it
        follows along the sweep path. If is_frenet is False, the orientation of the
        profile is kept consistent from point to point. The resulting shape has the
        minimum possible twisting. Unintuitively, when a profile is swept along a
        helix, this results in the orientation of the profile slowly creeping
        (rotating) as it follows the helix. Setting is_frenet to True prevents this.

        If is_frenet is True the orientation of the profile is based on the local
        curvature and tangency vectors of the path. This keeps the orientation of the
        profile consistent when sweeping along a helix (because the curvature vector of
        a straight helix always points to its axis). However, when path is not a helix,
        the resulting shape can have strange looking twists sometimes. For more
        information, see Frenet Serret formulas
        http://en.wikipedia.org/wiki/Frenet%E2%80%93Serret_formulas.

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

        shapes: list[Mixin3D[TopoDS_Shape]] = []
        for wire in [outer_wire] + inner_wires:
            builder = BRepOffsetAPI_MakePipeShell(Wire(path).wrapped)

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

        outer_shape, inner_shapes = shapes[0], shapes[1:]

        if inner_shapes:
            hollow_outer_shape = outer_shape.cut(*inner_shapes)
            assert isinstance(hollow_outer_shape, Solid)
            return hollow_outer_shape

        return outer_shape

    @classmethod
    def sweep_multi(
        cls,
        profiles: Iterable[Wire | Face],
        path: Wire | Edge,
        make_solid: bool = True,
        is_frenet: bool = False,
        binormal: Vector | Wire | Edge | None = None,
    ) -> Solid:
        """Multi section sweep

        Sweep through a sequence of profiles following a path.

        The is_frenet parameter controls how the profile orientation changes as it
        follows along the sweep path. If is_frenet is False, the orientation of the
        profile is kept consistent from point to point. The resulting shape has the
        minimum possible twisting. Unintuitively, when a profile is swept along a
        helix, this results in the orientation of the profile slowly creeping
        (rotating) as it follows the helix. Setting is_frenet to True prevents this.

        If is_frenet is True the orientation of the profile is based on the local
        curvature and tangency vectors of the path. This keeps the orientation of the
        profile consistent when sweeping along a helix (because the curvature vector of
        a straight helix always points to its axis). However, when path is not a helix,
        the resulting shape can have strange looking twists sometimes. For more
        information, see Frenet Serret formulas
        http://en.wikipedia.org/wiki/Frenet%E2%80%93Serret_formulas.

        Args:
            profiles (Iterable[Union[Wire, Face]]): list of profiles
            path (Union[Wire, Edge]): The wire to sweep the face resulting from the wires over
            make_solid (bool, optional): Solid or Shell. Defaults to True.
            is_frenet (bool, optional): Select frenet mode. Defaults to False.
            binormal (Union[Vector, Wire, Edge, None], optional): additional sweep mode parameters.
                Defaults to None.

        Returns:
            Solid: swept object
        """
        path_as_wire = Wire(path).wrapped

        builder = BRepOffsetAPI_MakePipeShell(path_as_wire)

        translate = False
        rotate = False

        if binormal:
            rotate = cls._set_sweep_mode(builder, path, binormal)
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

        return cls(TopoDS.Solid_s(builder.Shape()))

    @classmethod
    def thicken(
        cls,
        surface: Face | Shell,
        depth: float,
        normal_override: VectorLike | None = None,
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
            result = Solid(TopoDS.Solid_s(offset_builder.Shape()))
        except StdFail_NotDone as err:
            raise RuntimeError("Error applying thicken to given surface") from err

        return result

    def draft(self, faces: Iterable[Face], neutral_plane: Plane, angle: float) -> Solid:
        """Apply a draft angle to the given faces of the solid.

        Args:
            faces: Faces to which the draft should be applied.
            neutral_plane: Plane defining the neutral direction and position.
            angle: Draft angle in degrees.

        Returns:
            Solid with the specified draft angles applied.

        Raises:
            RuntimeError: If draft application fails on any face or during build.
        """
        valid_geom_types = {GeomType.PLANE, GeomType.CYLINDER, GeomType.CONE}
        for face in faces:
            if face.geom_type not in valid_geom_types:
                raise ValueError(
                    f"Face {face} has unsupported geometry type {face.geom_type.name}. "
                    "Only PLANAR, CYLINDRICAL, and CONICAL faces are supported."
                )

        draft_angle_builder = BRepOffsetAPI_DraftAngle(self.wrapped)

        for face in faces:
            draft_angle_builder.Add(
                face.wrapped,
                neutral_plane.z_dir.to_dir(),
                radians(angle),
                neutral_plane.wrapped,
                Flag=True,
            )
            if not draft_angle_builder.AddDone():
                raise DraftAngleError(
                    "Draft could not be added to a face.",
                    face=face,
                    problematic_shape=draft_angle_builder.ProblematicShape(),
                )

        try:
            draft_angle_builder.Build()
            result = Solid(TopoDS.Solid_s(draft_angle_builder.Shape()))
        except StdFail_NotDone as err:
            raise DraftAngleError(
                "Draft build failed on the given solid.",
                face=None,
                problematic_shape=draft_angle_builder.ProblematicShape(),
            ) from err
        return result


class DraftAngleError(RuntimeError):
    """Solid.draft custom exception"""

    def __init__(self, message, face=None, problematic_shape=None):
        super().__init__(message)
        self.face = face
        self.problematic_shape = problematic_shape
