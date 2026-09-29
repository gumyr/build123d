"""
build123d topology

name: utils.py
by:   Gumyr
date: January 07, 2025

desc:

This module provides utility functions and helper classes for the build123d CAD library, enabling
advanced geometric operations and facilitating the use of the OpenCascade CAD kernel. It complements
the core library by offering reusable and modular tools for manipulating shapes, performing Boolean
operations, and validating geometry.

Key Features:
- **Geometric Utilities**:
  - `polar`: Converts polar coordinates to Cartesian.
  - `tuplify`: Normalizes inputs into consistent tuples.
  - `find_max_dimension`: Computes the maximum bounding dimension of shapes.

- **Shape Creation**:
  - `_make_loft`: Creates lofted shapes from wires and vertices.
  - `_make_topods_compound_from_shapes`: Constructs compounds from multiple shapes.
  - `_make_topods_face_from_wires`: Generates planar faces with optional holes.

- **Boolean Operations**:
  - `new_edges`: Identifies newly created edges from combined shapes.

- **Enhanced Math**:
  - `isclose_b`: Overrides `math.isclose` with a stricter absolute tolerance.

This module is a critical component of build123d, supporting complex CAD workflows and geometric
transformations while maintaining a clean, extensible API.

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

from math import radians, sin, cos, isclose
from typing import Any, TYPE_CHECKING

from collections.abc import Iterable

from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepTools import BRepTools
from OCP.BRepLib import BRepLib_FindSurface
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt, gp_Vec
from OCP.ShapeFix import ShapeFix_Face, ShapeFix_Shape
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.collections import List_TopoDS_Shape
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Compound,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Vertex,
    TopoDS_Edge,
    TopoDS_Wire,
)
from build123d.geometry import TOLERANCE, BoundBox, Vector, VectorLike

from .shape_core import (
    Shape,
    ShapeList,
    downcast,
    shapetype,
    _make_topods_compound_from_shapes,
    _sew_topods_faces,
    _topods_face_normal_at,
)

if TYPE_CHECKING:  # pragma: no cover
    from .zero_d import Vertex  # pylint: disable=R0801
    from .one_d import Edge, Wire  # pylint: disable=R0801


def _topods_face_position(face: TopoDS_Face, u: float, v: float) -> Vector:
    """The point of a face at normalized (u, v), each from 0 to 1 across the
    face's own parameter range."""
    u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
    surface = BRep_Tool.Surface_s(face)
    return Vector(
        surface.Value(u_min + u * (u_max - u_min), v_min + v * (v_max - v_min))
    )


def _topods_face_normal(face: TopoDS_Face, u: float = 0.5, v: float = 0.5) -> Vector:
    """The unit normal of a face at normalized (u, v), with the face's own
    orientation: reversed faces point the other way from their surface."""
    u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
    point, normal = gp_Pnt(), gp_Vec()
    BRepGProp_Face(face).Normal(
        u_min + u * (u_max - u_min), v_min + v * (v_max - v_min), point, normal
    )
    return Vector(normal).normalized()


def _topods_face_center(face: TopoDS_Face) -> Vector:
    """The centre of mass of a face's area."""
    properties = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, properties)
    return Vector(properties.CentreOfMass())


def _topods_point_on_face(
    face: TopoDS_Face, point: VectorLike, tolerance: float = TOLERANCE
) -> bool:
    """Whether a point lies on a face, its boundary included, within a
    tolerance."""
    classifier = BRepClass3d_SolidClassifier(face)
    classifier.Perform(gp_Pnt(*Vector(point)), tolerance)
    return classifier.IsOnAFace()


def _make_topods_shell(faces: Iterable[TopoDS_Face]) -> TopoDS_Shell:
    """One shell from faces: a single face held in a shell of its own, or
    several sewn together.

    Raises:
        ValueError: no faces, or faces that do not sew into one shell
    """
    faces = list(faces)
    if not faces:
        raise ValueError("a shell needs at least one face")
    if len(faces) == 1:
        shell = TopoDS_Shell()
        builder = BRep_Builder()
        builder.MakeShell(shell)
        builder.Add(shell, faces[0])
        return shell
    sewn = _sew_topods_faces(faces)
    if not isinstance(sewn, TopoDS_Shell):
        raise ValueError("the faces do not sew into one connected shell")
    return sewn


def _topods_material_side(face: TopoDS_Face, edge: TopoDS_Edge) -> Vector:
    """The direction into a face's material across one of its edges.

    A valid face keeps its material on the left of every wire as it walks
    it, holes included, so the face's normal crossed with the edge's tangent,
    both taken at the edge's middle and the tangent as the face walks the
    edge, points into the material. The edge is read as it occurs in the
    face, whatever orientation, or moved copy, of it was given.

    Raises:
        ValueError: the edge is not an edge of the face
    """
    occurrence = None
    explorer = TopExp_Explorer(face, TopAbs_ShapeEnum.TopAbs_EDGE)
    while explorer.More():
        if explorer.Current().IsSame(edge):
            occurrence = TopoDS.Edge(explorer.Current())
            break
        if occurrence is None and explorer.Current().IsPartner(edge):
            occurrence = TopoDS.Edge(explorer.Current())
        explorer.Next()
    if occurrence is None:
        raise ValueError("the edge is not an edge of the face")
    curve = BRepAdaptor_Curve(occurrence)
    point, tangent = gp_Pnt(), gp_Vec()
    curve.D1((curve.FirstParameter() + curve.LastParameter()) / 2, point, tangent)
    if occurrence.Orientation() == TopAbs_Orientation.TopAbs_REVERSED:
        tangent.Reverse()
    return _topods_face_normal_at(face, point).cross(Vector(tangent).normalized())


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


def _make_loft(
    objs: Iterable[Vertex | Wire],
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
    objs = list(objs)  # To determine its length
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


def _make_topods_face_from_wires(
    outer_wire: TopoDS_Wire, inner_wires: Iterable[TopoDS_Wire] | None = None
) -> TopoDS_Face:
    """_make_topods_face_from_wires

    Makes a planar face from one or more wires

    Args:
        outer_wire (TopoDS_Wire): closed perimeter wire
        inner_wires (Iterable[TopoDS_Wire], optional): holes. Defaults to None.

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
    inner_wires = list(inner_wires) if inner_wires else []

    # check if wires are coplanar
    verification_compound = _make_topods_compound_from_shapes(
        [outer_wire] + inner_wires
    )
    if not BRepLib_FindSurface(verification_compound, OnlyPlane=True).Found():
        raise ValueError("Cannot build face(s): wires not planar")

    # fix outer wire
    sf_s = ShapeFix_Shape(outer_wire)
    sf_s.Perform()
    topo_wire = TopoDS.Wire(sf_s.Shape())

    face_builder = BRepBuilderAPI_MakeFace(topo_wire, True)

    for inner_wire in inner_wires:
        if not BRep_Tool.IsClosed_s(inner_wire):
            raise ValueError("Cannot build face(s): inner wire is not closed")
        sf_s = ShapeFix_Shape(inner_wire)
        sf_s.Perform()
        fixed_inner_wire = TopoDS.Wire(sf_s.Shape())
        face_builder.Add(fixed_inner_wire)

    face_builder.Build()

    if not face_builder.IsDone():
        raise ValueError(f"Cannot build face(s): {face_builder.Error()}")

    face = face_builder.Face()

    sf_f = ShapeFix_Face(face)
    sf_f.FixOrientation()
    sf_f.Perform()

    return TopoDS.Face(sf_f.Result())


def delta(shapes_one: Iterable[Shape], shapes_two: Iterable[Shape]) -> list[Shape]:
    """Compare the OCCT objects of each list and return the differences"""
    shapes_one = list(shapes_one)
    shapes_two = list(shapes_two)
    occt_one = {shape.wrapped for shape in shapes_one}
    occt_two = {shape.wrapped for shape in shapes_two}
    occt_delta = list(occt_one - occt_two)

    all_shapes = []
    for shapes in [shapes_one, shapes_two]:
        all_shapes.extend(shapes if isinstance(shapes, list) else [*shapes])
    shape_delta = [shape for shape in all_shapes if shape.wrapped in occt_delta]
    return shape_delta


def find_max_dimension(shapes: Shape | Iterable[Shape]) -> float:
    """Return the maximum dimension of one or more shapes"""
    shapes = shapes if isinstance(shapes, Iterable) else [shapes]
    composite = _make_topods_compound_from_shapes([s.wrapped for s in shapes])
    bbox = BoundBox.from_topo_ds(composite, tolerance=TOLERANCE, optimal=True)
    return bbox.diagonal


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
    combined_topo_edges = List_TopoDS_Shape()
    for edge in combined.edges():
        if edge.wrapped is not None:
            combined_topo_edges.Append(edge.wrapped)

    # Create a list of original object edges
    original_topo_edges = List_TopoDS_Shape()
    for edge in [e for obj in objects for e in obj.edges()]:
        if edge.wrapped is not None:
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


def polar(length: float, angle: float) -> tuple[float, float]:
    """Convert polar coordinates into cartesian coordinates"""
    return (length * cos(radians(angle)), length * sin(radians(angle)))


def tuplify(obj: Any, dim: int) -> tuple | None:
    """Create a size tuple"""
    if obj is None:
        result = None
    elif isinstance(obj, (tuple, list)):
        result = tuple(obj)
    else:
        result = tuple([obj] * dim)
    return result


def unwrapped_shapetype(obj: Shape) -> TopAbs_ShapeEnum:
    """Return Shape's TopAbs_ShapeEnum"""
    if isinstance(obj.wrapped, TopoDS_Compound):
        shapetypes = {shapetype(o.wrapped) for o in obj}
        if len(shapetypes) == 1:
            result = shapetypes.pop()
        else:
            result = shapetype(obj.wrapped)
    else:
        result = shapetype(obj.wrapped)
    return result
