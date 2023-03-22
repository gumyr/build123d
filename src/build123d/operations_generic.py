"""
Generic Operations

name: operations_generic.py
by:   Gumyr
date: March 21th 2023

desc:
    This python module contains operations (functions) that work on combinations
    of Curves, Sketches and Parts.

license:

    Copyright 2022 Gumyr

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
import copy
import logging
from typing import Union
from build123d.build_enums import Mode, Kind, Keep
from build123d.geometry import (
    Location,
    Matrix,
    Plane,
    Vector,
)
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    Part,
    Plane,
    Matrix,
    Shape,
    Sketch,
    Solid,
    Vertex,
    Wire,
)

from build123d.build_common import Builder, validate_inputs

logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")


#
# Operations
#


def bounding_box(
    *objects: Shape,
    mode: Mode = Mode.ADD,
) -> Union[Sketch, Part]:
    """Generic Operation: Add Bounding Box

    Applies to: BuildSketch and BuildPart

    Add the 2D or 3D bounding boxes of the object sequence

    Args:
        objects (Shape): sequence of objects
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: Builder = Builder._get_context(None)
    validate_inputs(context, None, objects)

    if all([obj._dim == 2 for obj in objects]):
        new_faces = []
        for obj in objects:
            if isinstance(obj, Vertex):
                continue
            bounding_box = obj.bounding_box()
            vertices = [
                (bounding_box.min.X, bounding_box.min.Y),
                (bounding_box.min.X, bounding_box.max.Y),
                (bounding_box.max.X, bounding_box.max.Y),
                (bounding_box.max.X, bounding_box.min.Y),
                (bounding_box.min.X, bounding_box.min.Y),
            ]
            new_faces.append(
                Face.make_from_wires(Wire.make_polygon([Vector(v) for v in vertices]))
            )
        if context is not None:
            context._add_to_context(*new_faces, mode=mode)
        return Sketch(Compound.make_compound(new_faces).wrapped)
    else:
        new_objects = []
        for obj in objects:
            if isinstance(obj, Vertex):
                continue
            bounding_box = obj.bounding_box()
            new_objects.append(
                Solid.make_box(
                    bounding_box.size.X,
                    bounding_box.size.Y,
                    bounding_box.size.Z,
                    Plane((bounding_box.min.X, bounding_box.min.Y, bounding_box.min.Z)),
                )
            )
        if context is not None:
            context._add_to_context(*new_objects, mode=mode)
        return Part(Compound.make_compound(new_objects).wrapped)


def chamfer(
    *objects: Union[Edge, Vertex],
    length: float,
    length2: float = None,
    target: Union[Face, Sketch, Solid, Part] = None,
) -> Union[Sketch, Part]:
    """Generic Operation: chamfer

    Applies to 2 and 3 dimensional objects.

    Chamfer the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to chamfer
        length (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.
        target (Union[Face, Sketch, Solid, Part], optional): object to chamfer. Defaults to None.

    Raises:
        ValueError: objects must be Edges
        ValueError: objects must be Vertices
        ValueError: missing target object
    """
    context: Builder = Builder._get_context(None)
    validate_inputs(context, None, objects)

    if target is None:
        if context is None:
            raise ValueError("A target object must be provided")
        target = context._obj

    if target._dim == 3:
        if not all([isinstance(obj, Edge) for obj in objects]):
            raise ValueError("3D chamfer operation takes only Edges")
        new_part = target.chamfer(length, length2, list(objects))

        if context is not None:
            context._add_to_context(new_part, mode=Mode.REPLACE)
        return Part(Compound.make_compound([new_part]).wrapped)

    elif target._dim == 2:
        if not all([isinstance(obj, Vertex) for obj in objects]):
            raise ValueError("2D chamfer operation takes only Vertices")
        new_faces = []
        for face in target.faces():
            vertices_in_face = [v for v in face.vertices() if v in objects]
            if vertices_in_face:
                new_faces.append(face.chamfer_2d(length, vertices_in_face))
            else:
                new_faces.append(face)
        new_sketch = Sketch(Compound.make_compound(new_faces).wrapped)

        if context is not None:
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
        return new_sketch


def fillet(
    *objects: Union[Edge, Vertex],
    radius: float,
    target: Union[Face, Sketch, Solid, Part] = None,
) -> Union[Sketch, Part]:
    """Generic Operation: fillet

    Applies to 2 and 3 dimensional objects.

    Fillet the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to fillet
        radius (float): fillet size - must be less than 1/2 local width

    Raises:
        ValueError: objects must be Edges
        ValueError: objects must be Vertices
        ValueError: missing target object
    """
    context: Builder = Builder._get_context(None)
    validate_inputs(context, None, objects)

    if target is None:
        if context is None:
            raise ValueError("A target object must be provided")
        target = context._obj

    if target._dim == 3:
        if not all([isinstance(obj, Edge) for obj in objects]):
            raise ValueError("3D fillet operation takes only Edges")
        new_part = target.fillet(radius, list(objects))

        if context is not None:
            context._add_to_context(new_part, mode=Mode.REPLACE)
        return Part(Compound.make_compound([new_part]).wrapped)

    elif target._dim == 2:
        if not all([isinstance(obj, Vertex) for obj in objects]):
            raise ValueError("2D fillet operation takes only Vertices")
        new_faces = []
        for face in target.faces():
            vertices_in_face = [v for v in face.vertices() if v in objects]
            if vertices_in_face:
                new_faces.append(face.fillet_2d(radius, vertices_in_face))
            else:
                new_faces.append(face)
        new_sketch = Sketch(Compound.make_compound(new_faces).wrapped)

        if context is not None:
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
        return new_sketch


def mirror(
    *objects: Union[Edge, Wire, Face, Compound, Curve, Sketch, Part],
    about: Plane = Plane.XZ,
    mode: Mode = Mode.ADD,
) -> Union[Curve, Sketch, Part, Compound]:
    """Generic Operation: mirror

    Applies to 1, 2, and 3 dimensional objects.

    Mirror a sequence of objects over the given plane.

    Args:
        objects (Union[Edge, Face,Compound]): sequence of edges or faces to mirror
        about (Plane, optional): reference plane. Defaults to "XZ".
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: missing objects
    """
    context: Builder = Builder._get_context(None)
    validate_inputs(context, None, objects)

    if objects is None:
        if context is None:
            raise ValueError("objects must be provided")
        objects = [context._obj]

    mirrored = [copy.deepcopy(o).mirror(about) for o in objects]

    if context is not None:
        context._add_to_context(*mirrored, mode=mode)

    mirrored_compound = Compound.make_compound(mirrored)
    if all([obj._dim == 3 for obj in objects]):
        return Part(mirrored_compound.wrapped)
    elif all([obj._dim == 2 for obj in objects]):
        return Sketch(mirrored_compound.wrapped)
    elif all([obj._dim == 1 for obj in objects]):
        return Curve(mirrored_compound.wrapped)
    else:
        return mirrored_compound


def offset(
    *objects: Union[Edge, Face, Solid, Compound],
    amount: float,
    openings: Union[Face, list[Face]] = None,
    kind: Kind = Kind.ARC,
    mode: Mode = Mode.REPLACE,
) -> Union[Curve, Sketch, Part, Compound]:
    """Generic Operation: offset

    Applies to 1, 2, and 3 dimensional objects.

    Offset the given sequence of Edges, Faces, Compound of Faces, or Solids.
    The kind parameter controls the shape of the transitions. For Solid
    objects, the openings parameter allows selected faces to be open, like
    a hollow box with no lid.

    Args:
        objects: Union[Edge, Face, Solid, Compound], sequence of objects
        amount (float): positive values external, negative internal
        openings (list[Face], optional), sequence of faces to open in part.
            Defaults to None.
        kind (Kind, optional): transition shape. Defaults to Kind.ARC.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: missing objects
        ValueError: Invalid object type
    """
    context: Builder = Builder._get_context(None)
    validate_inputs(context, None, objects)

    if objects is None:
        if context is None:
            raise ValueError("objects must be provided")
        objects = [context._obj]

    edges: list[Edge] = []
    faces: list[Face] = []
    solids: list[Solid] = []
    for obj in objects:
        if isinstance(obj, Compound):
            edges.extend(obj.get_type(Edge))
            faces.extend(obj.get_type(Face))
            solids.extend(obj.get_type(Solid))
        elif isinstance(obj, Solid):
            solids.append(obj)
        elif isinstance(obj, Face):
            faces.append(obj)
        elif isinstance(obj, Edge):
            edges.append(obj)

    new_faces = []
    for face in faces:
        new_faces.append(
            Face.make_from_wires(face.outer_wire().offset_2d(amount, kind=kind)[0])
        )
    if edges:
        if len(edges) == 1 and edges[0].geom_type() == "LINE":
            new_wires = Wire.make_wire(
                [
                    Edge.make_line(edges[0] @ 0.0, edges[0] @ 0.5),
                    Edge.make_line(edges[0] @ 0.5, edges[0] @ 1.0),
                ]
            ).offset_2d(amount)
        else:
            new_wires = Wire.make_wire(edges).offset_2d(amount, kind=kind)
    else:
        new_wires = []

    if isinstance(openings, Face):
        openings = [openings]

    new_solids = []
    for solid in solids:
        if openings:
            openings_in_this_solid = [o for o in openings if o in solid.faces()]
        else:
            openings_in_this_solid = []
        new_solids.append(
            solid.offset_3d(openings_in_this_solid, amount, kind=kind).fix()
        )

    new_objects = new_wires + new_faces + new_solids
    if context is not None:
        context._add_to_context(*new_objects, mode=mode)

    offset_compound = Compound.make_compound(new_objects)
    if all([obj._dim == 3 for obj in objects]):
        return Part(offset_compound.wrapped)
    elif all([obj._dim == 2 for obj in objects]):
        return Sketch(offset_compound.wrapped)
    elif all([obj._dim == 1 for obj in objects]):
        return Curve(offset_compound.wrapped)
    else:
        return offset_compound


def scale(
    *objects: Shape,
    by: Union[float, tuple[float, float, float]],
    mode: Mode = Mode.REPLACE,
) -> Union[Curve, Sketch, Part, Compound]:
    """Generic Operation: scale

    Applies to 1, 2, and 3 dimensional objects.

    Scale a sequence of objects. Note that when scaling non-uniformly across
    the three axes, the type of the underlying object may change to bspline from
    line, circle, etc.

    Args:
        objects (Union[Edge, Face, Compound, Solid]): sequence of objects
        by (Union[float, tuple[float, float, float]]): scale factor
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: missing objects
    """
    context: Builder = Builder._get_context(None)
    validate_inputs(context, None, objects)

    if objects is None:
        if context is None:
            raise ValueError("objects must be provided")
        objects = [context._obj]

    if isinstance(by, (int, float)):
        factor = float(by)
    elif (
        isinstance(by, (tuple))
        and len(by) == 3
        and all(isinstance(s, (int, float)) for s in by)
    ):
        factor = Vector(by)
        scale_matrix = Matrix(
            [
                [factor.X, 0.0, 0.0, 0.0],
                [0.0, factor.Y, 0.0, 0.0],
                [0.0, 0.0, factor.Z, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
    else:
        raise ValueError("by must be a float or a three tuple of float")

    new_objects = []
    for obj in objects:
        current_location = obj.location
        obj_at_origin = obj.located(Location(Vector()))
        if isinstance(factor, float):
            new_object = obj_at_origin.scale(factor).locate(current_location)
        else:
            new_object = obj_at_origin.transform_geometry(scale_matrix).locate(
                current_location
            )
        new_objects.append(new_object)

    if context is not None:
        context._add_to_context(*new_objects, mode=mode)

    scale_compound = Compound.make_compound(new_objects)
    if all([obj._dim == 3 for obj in objects]):
        return Part(scale_compound.wrapped)
    elif all([obj._dim == 2 for obj in objects]):
        return Sketch(scale_compound.wrapped)
    elif all([obj._dim == 1 for obj in objects]):
        return Curve(scale_compound.wrapped)
    else:
        return scale_compound


def split(
    *objects: Union[Edge, Wire, Face, Solid],
    bisect_by: Plane = Plane.XZ,
    keep: Keep = Keep.TOP,
    mode: Mode = Mode.REPLACE,
):
    """Generic Operation: split

    Applies to 1, 2, and 3 dimensional objects.

    Bisect object with plane and keep either top, bottom or both.

    Args:
        objects (Union[Edge, Wire, Face, Solid]), objects to split
        bisect_by (Plane, optional): plane to segment part. Defaults to Plane.XZ.
        keep (Keep, optional): selector for which segment to keep. Defaults to Keep.TOP.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.

    Raises:
        ValueError: missing objects
    """

    def build_cutter(keep: Keep, max_size: float) -> Solid:
        cutter_center = (
            Vector(-max_size, -max_size, 0)
            if keep == Keep.TOP
            else Vector(-max_size, -max_size, -2 * max_size)
        )
        return bisect_by.from_local_coords(
            Solid.make_box(2 * max_size, 2 * max_size, 2 * max_size).locate(
                Location(cutter_center)
            )
        )

    context: Builder = Builder._get_context(None)
    validate_inputs(context, None, objects)

    if objects is None:
        if context is None:
            raise ValueError("objects must be provided")
        objects = [context._obj]

    new_objects = []
    for obj in objects:
        max_size = obj.bounding_box().diagonal

        cutters = []
        if keep == Keep.BOTH:
            cutters.append(build_cutter(Keep.TOP, max_size))
            cutters.append(build_cutter(Keep.BOTTOM, max_size))
        else:
            cutters.append(build_cutter(keep, max_size))
        new_objects.append(obj.intersect(*cutters))

    if context is not None:
        context._add_to_context(*new_objects, mode=mode)

    split_compound = Compound.make_compound(new_objects)
    if all([obj._dim == 3 for obj in objects]):
        return Part(split_compound.wrapped)
    elif all([obj._dim == 2 for obj in objects]):
        return Sketch(split_compound.wrapped)
    elif all([obj._dim == 1 for obj in objects]):
        return Curve(split_compound.wrapped)
    else:
        return split_compound
