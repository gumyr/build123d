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
from math import radians, tan, isclose
from typing import Union, Iterable

from build123d.build_common import (
    Builder,
    LocationList,
    WorkplaneList,
    flatten_sequence,
    validate_inputs,
)
from build123d.build_enums import Keep, Kind, Mode, Side, Transition, GeomType
from build123d.build_line import BuildLine
from build123d.build_part import BuildPart
from build123d.build_sketch import BuildSketch
from build123d.geometry import (
    Axis,
    Location,
    Matrix,
    Plane,
    Rotation,
    RotationLike,
    Vector,
    VectorLike,
)
from build123d.objects_part import BasePartObject
from build123d.objects_sketch import BaseSketchObject
from build123d.objects_curve import BaseLineObject
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    GroupBy,
    Part,
    Shape,
    ShapeList,
    Sketch,
    Solid,
    Vertex,
    Wire,
)

logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")

#:TypeVar("AddType"): Type of objects which can be added to a builder
AddType = Union[Edge, Wire, Face, Solid, Compound, Builder]


def add(
    objects: Union[AddType, Iterable[AddType]],
    rotation: Union[float, RotationLike] = None,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Compound:
    """Generic Object: Add Object to Part or Sketch

    Add an object to a builder.

    BuildPart:
        Edges and Wires are added to pending_edges. Compounds of Face are added to
        pending_faces. Solids or Compounds of Solid are combined into the part.
    BuildSketch:
        Edges and Wires are added to pending_edges. Compounds of Face are added to sketch.
    BuildLine:
        Edges and Wires are added to line.

    Args:
        objects (Union[Edge, Wire, Face, Solid, Compound]  or Iterable of): objects to add
        rotation (Union[float, RotationLike], optional): rotation angle for sketch,
            rotation about each axis for part. Defaults to None.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
       mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """
    context: Builder = Builder._get_context(None)
    if context is None:
        raise RuntimeError("Add must have an active builder context")

    object_iter = objects if isinstance(objects, Iterable) else [objects]
    object_iter = [obj._obj if isinstance(obj, Builder) else obj for obj in object_iter]

    validate_inputs(context, "add", object_iter)

    if isinstance(context, BuildPart):
        if rotation is None:
            rotation = Rotation(0, 0, 0)
        elif isinstance(rotation, tuple):
            rotation = Rotation(*rotation)
        else:
            raise ValueError("Invalid rotation value")

        object_iter = [obj.moved(rotation) for obj in object_iter]
        new_edges = [obj for obj in object_iter if isinstance(obj, Edge)]
        new_wires = [obj for obj in object_iter if isinstance(obj, Wire)]
        new_faces = [obj for obj in object_iter if isinstance(obj, Face)]
        new_solids = [obj for obj in object_iter if isinstance(obj, Solid)]
        for compound in filter(lambda o: isinstance(o, Compound), object_iter):
            new_edges.extend(compound.get_type(Edge))
            new_wires.extend(compound.get_type(Wire))
            new_faces.extend(compound.get_type(Face))
            new_solids.extend(compound.get_type(Solid))
        for new_wire in new_wires:
            new_edges.extend(new_wire.edges())

        # Add the pending Edges in one group
        if not LocationList._get_context():
            raise RuntimeError("There is no active Locations context")
        located_edges = [
            edge.moved(location)
            for edge in new_edges
            for location in LocationList._get_context().locations
        ]
        context._add_to_pending(*located_edges)
        new_objects = located_edges

        # Add to pending Faces batched by workplane
        for workplane in WorkplaneList._get_context().workplanes:
            faces_per_workplane = []
            for location in LocationList._get_context().locations:
                for face in new_faces:
                    faces_per_workplane.append(face.moved(location))
            context._add_to_pending(*faces_per_workplane, face_plane=workplane)
            new_objects.extend(faces_per_workplane)

        # Add to context Solids
        located_solids = [
            solid.moved(location)
            for solid in new_solids
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*located_solids, clean=clean, mode=mode)
        new_objects.extend(located_solids)

    elif isinstance(context, BuildSketch):
        rotation_angle = rotation if isinstance(rotation, (int, float)) else 0.0
        new_objects = []
        for obj in object_iter:
            new_objects.extend(
                [
                    obj.rotate(Axis.Z, rotation_angle).moved(location)
                    for location in LocationList._get_context().local_locations
                ]
            )
        context._add_to_context(*new_objects, mode=mode)

    elif isinstance(context, BuildLine):
        rotation_angle = rotation if isinstance(rotation, (int, float)) else 0.0
        new_objects = []
        for obj in object_iter:
            new_objects.extend(
                [
                    obj.rotate(Axis.Z, rotation_angle).moved(location)
                    for location in LocationList._get_context().local_locations
                ]
            )
        context._add_to_context(*new_objects, mode=mode)

    else:
        raise RuntimeError(f"Builder {context.__class__.__name__} is unsupported")

    return Compound(new_objects)


def bounding_box(
    objects: Union[Shape, Iterable[Shape]] = None,
    mode: Mode = Mode.PRIVATE,
) -> Union[Sketch, Part]:
    """Generic Operation: Add Bounding Box

    Applies to: BuildSketch and BuildPart

    Add the 2D or 3D bounding boxes of the object sequence

    Args:
        objects (Shape or Iterable of): objects to create bbox for
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: Builder = Builder._get_context("bounding_box")

    if objects is None:
        if context is None or context is not None and context._obj is None:
            raise ValueError("objects must be provided")
        object_list = [context._obj]
    else:
        object_list = flatten_sequence(objects)

    validate_inputs(context, "bounding_box", object_list)

    if all([obj._dim == 2 for obj in object_list]):
        new_faces = []
        for obj in object_list:
            if isinstance(obj, Vertex):
                continue
            bbox = obj.bounding_box()
            vertices = [
                (bbox.min.X, bbox.min.Y),
                (bbox.min.X, bbox.max.Y),
                (bbox.max.X, bbox.max.Y),
                (bbox.max.X, bbox.min.Y),
                (bbox.min.X, bbox.min.Y),
            ]
            new_faces.append(Face(Wire.make_polygon([Vector(v) for v in vertices])))
        if context is not None:
            context._add_to_context(*new_faces, mode=mode)
        return Sketch(Compound(new_faces).wrapped)

    new_objects = []
    for obj in object_list:
        if isinstance(obj, Vertex):
            continue
        bbox = obj.bounding_box()
        new_objects.append(
            Solid.make_box(
                bbox.size.X,
                bbox.size.Y,
                bbox.size.Z,
                Plane((bbox.min.X, bbox.min.Y, bbox.min.Z)),
            )
        )
    if context is not None:
        context._add_to_context(*new_objects, mode=mode)
    return Part(Compound(new_objects).wrapped)


#:TypeVar("ChamferFilletType"): Type of objects which can be chamfered or filleted
ChamferFilletType = Union[Edge, Vertex]


def chamfer(
    objects: Union[ChamferFilletType, Iterable[ChamferFilletType]],
    length: float,
    length2: float = None,
    angle: float = None,
    reference: Union[Edge, Face] = None,
) -> Union[Sketch, Part]:
    """Generic Operation: chamfer

    Applies to 2 and 3 dimensional objects.

    Chamfer the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]  or Iterable of): edges or vertices to chamfer
        length (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.
        angle (float, optional): chamfer angle in degrees. Defaults to None.
        reference (Union[Edge,Face]): identifies the side where length is measured. Edge(s) must
            be part of the face. Vertex/Vertices must be part of edge

    Raises:
        ValueError: no objects provided
        ValueError: objects must be Edges
        ValueError: objects must be Vertices
        ValueError: Only one of length2 or angle should be provided
        ValueError: reference can only be used in conjunction with length2 or angle
    """
    context: Builder = Builder._get_context("chamfer")
    if length2 and angle:
        raise ValueError("Only one of length2 or angle should be provided")

    if angle:
        length2 = length * tan(radians(angle))

    if reference and not (length2 or angle):
        raise ValueError(
            "reference can only be used in conjunction with length2 or angle"
        )

    length2 = length if length2 is None else length2

    if (objects is None and context is None) or (
        objects is None and context is not None and context._obj is None
    ):
        raise ValueError("No objects provided")

    object_list = flatten_sequence(objects)

    validate_inputs(context, "chamfer", object_list)

    if context is not None:
        target = context._obj
    else:
        target = object_list[0].topo_parent
    if target is None:
        raise ValueError("Nothing to chamfer")

    if target._dim == 3:
        # Convert BasePartObject into Part so casting into Part during construction works
        target = Part(target.wrapped) if isinstance(target, BasePartObject) else target

        if not all([isinstance(obj, Edge) for obj in object_list]):
            raise ValueError("3D chamfer operation takes only Edges")
        new_part = target.chamfer(length, length2, list(object_list), reference)

        if context is not None:
            context._add_to_context(new_part, mode=Mode.REPLACE)
        return Part(Compound([new_part]).wrapped)

    if target._dim == 2:
        # Convert BaseSketchObject into Sketch so casting into Sketch during construction works
        target = (
            Sketch(target.wrapped) if isinstance(target, BaseSketchObject) else target
        )
        if not all([isinstance(obj, Vertex) for obj in object_list]):
            raise ValueError("2D chamfer operation takes only Vertices")
        new_faces = []
        for face in target.faces():
            vertices_in_face = [v for v in face.vertices() if v in object_list]
            if vertices_in_face:
                new_faces.append(
                    face.chamfer_2d(length, length2, vertices_in_face, reference)
                )
            else:
                new_faces.append(face)
        new_sketch = Sketch(Compound(new_faces).wrapped)

        if context is not None:
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
        return new_sketch

    if target._dim == 1:
        target = (
            Wire(target.wrapped)
            if isinstance(target, BaseLineObject)
            else target.wires()[0]
        )
        if not all([isinstance(obj, Vertex) for obj in object_list]):
            raise ValueError("1D fillet operation takes only Vertices")
        # Remove any end vertices as these can't be filleted
        if not target.is_closed:
            object_list = filter(
                lambda v: not (
                    isclose(
                        (Vector(*v.to_tuple()) - target.position_at(0)).length,
                        0.0,
                        abs_tol=1e-14,
                    )
                    or isclose(
                        (Vector(*v.to_tuple()) - target.position_at(1)).length,
                        0.0,
                        abs_tol=1e-14,
                    )
                ),
                object_list,
            )
        new_wire = target.chamfer_2d(length, length2, object_list, reference)
        if context is not None:
            context._add_to_context(new_wire, mode=Mode.REPLACE)
        return new_wire


def fillet(
    objects: Union[ChamferFilletType, Iterable[ChamferFilletType]],
    radius: float,
) -> Union[Sketch, Part, Curve]:
    """Generic Operation: fillet

    Applies to 2 and 3 dimensional objects.

    Fillet the given sequence of edges or vertices. Note that vertices on
    either end of an open line will be automatically skipped.

    Args:
        objects (Union[Edge,Vertex] or Iterable of): edges or vertices to fillet
        radius (float): fillet size - must be less than 1/2 local width

    Raises:
        ValueError: no objects provided
        ValueError: objects must be Edges
        ValueError: objects must be Vertices
        ValueError: nothing to fillet
    """
    context: Builder = Builder._get_context("fillet")
    if (objects is None and context is None) or (
        objects is None and context is not None and context._obj is None
    ):
        raise ValueError("No objects provided")

    object_list = flatten_sequence(objects)

    validate_inputs(context, "fillet", object_list)
    if context is not None:
        target = context._obj
    else:
        target = object_list[0].topo_parent
    if target is None:
        raise ValueError("Nothing to fillet")

    if target._dim == 3:
        # Convert BasePartObject in Part so casting into Part during construction works
        target = Part(target.wrapped) if isinstance(target, BasePartObject) else target

        if not all([isinstance(obj, Edge) for obj in object_list]):
            raise ValueError("3D fillet operation takes only Edges")
        new_part = target.fillet(radius, list(object_list))

        if context is not None:
            context._add_to_context(new_part, mode=Mode.REPLACE)
        return Part(Compound([new_part]).wrapped)

    if target._dim == 2:
        # Convert BaseSketchObject into Sketch so casting into Sketch during construction works
        target = (
            Sketch(target.wrapped) if isinstance(target, BaseSketchObject) else target
        )

        if not all([isinstance(obj, Vertex) for obj in object_list]):
            raise ValueError("2D fillet operation takes only Vertices")
        new_faces = []
        for face in target.faces():
            vertices_in_face = [v for v in face.vertices() if v in list(object_list)]
            if vertices_in_face:
                new_faces.append(face.fillet_2d(radius, vertices_in_face))
            else:
                new_faces.append(face)
        new_sketch = Sketch(Compound(new_faces).wrapped)

        if context is not None:
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
        return new_sketch

    if target._dim == 1:
        target = (
            Wire(target.wrapped)
            if isinstance(target, BaseLineObject)
            else target.wires()[0]
        )
        if not all([isinstance(obj, Vertex) for obj in object_list]):
            raise ValueError("1D fillet operation takes only Vertices")
        # Remove any end vertices as these can't be filleted
        if not target.is_closed:
            object_list = filter(
                lambda v: not (
                    isclose(
                        (Vector(*v.to_tuple()) - target.position_at(0)).length,
                        0.0,
                        abs_tol=1e-14,
                    )
                    or isclose(
                        (Vector(*v.to_tuple()) - target.position_at(1)).length,
                        0.0,
                        abs_tol=1e-14,
                    )
                ),
                object_list,
            )
        new_wire = target.fillet_2d(radius, object_list)
        if context is not None:
            context._add_to_context(new_wire, mode=Mode.REPLACE)
        return new_wire


#:TypeVar("MirrorType"): Type of objects which can be mirrored
MirrorType = Union[Edge, Wire, Face, Compound, Curve, Sketch, Part]


def mirror(
    objects: Union[MirrorType, Iterable[MirrorType]] = None,
    about: Plane = Plane.XZ,
    mode: Mode = Mode.ADD,
) -> Union[Curve, Sketch, Part, Compound]:
    """Generic Operation: mirror

    Applies to 1, 2, and 3 dimensional objects.

    Mirror a sequence of objects over the given plane.

    Args:
        objects (Union[Edge, Face,Compound]  or Iterable of): objects to mirror
        about (Plane, optional): reference plane. Defaults to "XZ".
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: missing objects
    """
    context: Builder = Builder._get_context("mirror")
    object_list = objects if isinstance(objects, Iterable) else [objects]

    if objects is None:
        if context is None or context is not None and context._obj is None:
            raise ValueError("objects must be provided")
        object_list = [context._obj]
    else:
        object_list = flatten_sequence(objects)

    validate_inputs(context, "mirror", object_list)

    mirrored = [copy.deepcopy(o).mirror(about) for o in object_list]

    if context is not None:
        context._add_to_context(*mirrored, mode=mode)

    mirrored_compound = Compound(mirrored)
    if all([obj._dim == 3 for obj in object_list]):
        return Part(mirrored_compound.wrapped)
    if all([obj._dim == 2 for obj in object_list]):
        return Sketch(mirrored_compound.wrapped)
    if all([obj._dim == 1 for obj in object_list]):
        return Curve(mirrored_compound.wrapped)
    return mirrored_compound


#:TypeVar("OffsetType"): Type of objects which can be offset
OffsetType = Union[Edge, Face, Solid, Compound]


def offset(
    objects: Union[OffsetType, Iterable[OffsetType]] = None,
    amount: float = 0,
    openings: Union[Face, list[Face]] = None,
    kind: Kind = Kind.ARC,
    side: Side = Side.BOTH,
    closed: bool = True,
    min_edge_length: float = None,
    mode: Mode = Mode.REPLACE,
) -> Union[Curve, Sketch, Part, Compound]:
    """Generic Operation: offset

    Applies to 1, 2, and 3 dimensional objects.

    Offset the given sequence of Edges, Faces, Compound of Faces, or Solids.
    The kind parameter controls the shape of the transitions. For Solid
    objects, the openings parameter allows selected faces to be open, like
    a hollow box with no lid.

    Args:
        objects (Union[Edge, Face, Solid, Compound]  or Iterable of): objects to offset
        amount (float): positive values external, negative internal
        openings (list[Face], optional), sequence of faces to open in part.
            Defaults to None.
        kind (Kind, optional): transition shape. Defaults to Kind.ARC.
        side (Side, optional): side to place offset. Defaults to Side.BOTH.
        closed (bool, optional): if Side!=BOTH, close the LEFT or RIGHT
            offset. Defaults to True.
        min_edge_length (float, optional): repair degenerate edges generated by offset
            by eliminating edges of minimum length in offset wire. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.REPLACE.

    Raises:
        ValueError: missing objects
        ValueError: Invalid object type
    """
    context: Builder = Builder._get_context("offset")

    if objects is None:
        if context is None or context is not None and context._obj is None:
            raise ValueError("objects must be provided")
        object_list = [context._obj]
    else:
        object_list = flatten_sequence(objects)

    validate_inputs(context, "offset", object_list)

    edges: list[Edge] = []
    faces: list[Face] = []
    solids: list[Solid] = []
    for obj in object_list:
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
        elif isinstance(obj, Wire):
            edges.extend(obj.edges())
        else:
            raise TypeError(f"Unsupported type {type(obj)} for {obj}")

    new_faces = []
    for face in faces:
        outer_wire = face.outer_wire().offset_2d(amount, kind=kind)
        if min_edge_length is not None:
            outer_wire = outer_wire.fix_degenerate_edges(min_edge_length)
        inner_wires = []
        for inner_wire in face.inner_wires():
            try:
                offset_wire = inner_wire.offset_2d(-amount, kind=kind)
                if min_edge_length is not None:
                    inner_wires.append(
                        offset_wire.fix_degenerate_edges(min_edge_length)
                    )
                else:
                    inner_wires.append(offset_wire)
            except:
                pass
        new_face = Face(outer_wire, inner_wires)
        if (new_face.normal_at() - face.normal_at()).length > 0.001:
            new_face = -new_face
        new_faces.append(new_face)
    if edges:
        if len(edges) == 1 and edges[0].geom_type == GeomType.LINE:
            new_wires = [
                Wire(
                    [
                        Edge.make_line(edges[0] @ 0.0, edges[0] @ 0.5),
                        Edge.make_line(edges[0] @ 0.5, edges[0] @ 1.0),
                    ]
                ).offset_2d(amount, kind=kind, side=side, closed=closed)
            ]
        else:
            new_wires = [
                Wire(edges).offset_2d(amount, kind=kind, side=side, closed=closed)
            ]
        if min_edge_length is not None:
            new_wires = [w.fix_degenerate_edges(min_edge_length) for w in new_wires]
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

    offset_compound = Compound(new_objects)
    if all([obj._dim == 3 for obj in object_list]):
        return Part(offset_compound.wrapped)
    if all([obj._dim == 2 for obj in object_list]):
        return Sketch(offset_compound.wrapped)
    if all([obj._dim == 1 for obj in object_list]):
        return Curve(offset_compound.wrapped)
    return offset_compound


#:TypeVar("ProjectType"): Type of objects which can be projected
ProjectType = Union[Edge, Face, Wire, Vector, Vertex]


def project(
    objects: Union[ProjectType, Iterable[ProjectType]] = None,
    workplane: Plane = None,
    target: Union[Solid, Compound, Part] = None,
    mode: Mode = Mode.ADD,
) -> Union[Curve, Sketch, Compound, ShapeList[Vector]]:
    """Generic Operation: project

    Applies to 0, 1, and 2 dimensional objects.

    Project the given objects or points onto a BuildLine or BuildSketch workplane in
    the direction of the normal of that workplane. When projecting onto a
    sketch a Face(s) are generated while Edges are generated for BuildLine.
    Will only use the first if BuildSketch has multiple active workplanes.
    In algebra mode a workplane must be provided and the output is either
    a Face, Curve, Sketch, Compound, or ShapeList[Vector].

    Note that only if mode is not Mode.PRIVATE only Faces can be projected into
    BuildSketch and Edge/Wires into BuildLine.

    Args:
        objects (Union[Edge, Face, Wire, VectorLike, Vertex] or Iterable of):
            objects or points to project
        workplane (Plane, optional): screen workplane
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: project doesn't accept group_by
        ValueError: Either a workplane must be provided or a builder must be active
        ValueError: Points and faces can only be projected in PRIVATE mode
        ValueError: Edges, wires and points can only be projected in PRIVATE mode
        RuntimeError: BuildPart doesn't have a project operation
    """
    context: Builder = Builder._get_context("project")

    if isinstance(objects, GroupBy):
        raise ValueError("project doesn't accept group_by, did you miss [n]?")

    if not objects and context is None:
        raise ValueError("No object to project")
    if not objects and context is not None and isinstance(context, BuildPart):
        object_list = context.pending_edges + context.pending_faces
        context.pending_edges = []
        context.pending_faces = []
        if len(context.pending_face_planes) > 0:
            workplane = context.pending_face_planes[0]
            context.pending_face_planes = []
        else:
            workplane = context.exit_workplanes[0]
    else:
        object_list = flatten_sequence(objects)

    # The size of the object determines the size of the target projection screen
    # as the screen is normal to the direction of parallel projection
    shape_list = [
        Vertex(*o.to_tuple()) if isinstance(o, Vector) else o for o in object_list
    ]
    object_size = Compound(children=shape_list).bounding_box().diagonal

    point_list = [o for o in object_list if isinstance(o, (Vector, Vertex))]
    point_list = [Vector(pnt) for pnt in point_list]
    face_list = [o for o in object_list if isinstance(o, Face)]
    line_list = [o for o in object_list if isinstance(o, (Edge, Wire))]

    if workplane is None:
        if context is None:
            raise ValueError(
                "Either a workplane must be provided or a builder must be active"
            )
        if isinstance(context, BuildLine):
            workplane = context.workplanes[0]
            if mode != Mode.PRIVATE and (face_list or point_list):
                raise ValueError(
                    "Points and faces can only be projected in PRIVATE mode"
                )
        elif isinstance(context, BuildSketch):
            workplane = context.workplanes[0]
            if mode != Mode.PRIVATE and (line_list or point_list):
                raise ValueError(
                    "Edges, wires and points can only be projected in PRIVATE mode"
                )

    # BuildLine and BuildSketch are from target to workplane while BuildPart is
    # from workplane to target so the projection direction needs to be flipped
    projection_flip = 1
    if context is not None and isinstance(context, BuildPart):
        if mode != Mode.PRIVATE and point_list:
            raise ValueError("Points can only be projected in PRIVATE mode")
        if target is None:
            target = context._obj
        projection_flip = -1
    else:
        target = Face.make_rect(3 * object_size, 3 * object_size, plane=workplane)

    validate_inputs(context, "project")

    projected_shapes = []
    obj: Shape
    for obj in face_list + line_list:
        obj_to_screen = (target.center() - obj.center()).normalized()
        if workplane.from_local_coords(obj_to_screen).Z < 0:
            projection_direction = -workplane.z_dir * projection_flip
        else:
            projection_direction = workplane.z_dir * projection_flip
        projection = obj.project_to_shape(target, projection_direction)
        if projection:
            if isinstance(context, BuildSketch):
                projected_shapes.extend(
                    [workplane.to_local_coords(p) for p in projection]
                )
            elif isinstance(context, BuildLine):
                projected_shapes.extend(projection)
            else:  # BuildPart
                projected_shapes.append(projection[0])

    projected_points = []
    for pnt in point_list:
        pnt_to_target = (workplane.origin - pnt).normalized()
        if workplane.from_local_coords(pnt_to_target).Z < 0:
            projection_axis = -Axis(pnt, workplane.z_dir * projection_flip)
        else:
            projection_axis = Axis(pnt, workplane.z_dir * projection_flip)
        projection = workplane.to_local_coords(workplane.intersect(projection_axis))
        if projection is not None:
            projected_points.append(projection)

    if context is not None:
        context._add_to_context(*projected_shapes, mode=mode)

    if projected_points:
        result = ShapeList(projected_points)
    else:
        result = Compound(projected_shapes)
        if all([obj._dim == 2 for obj in object_list]):
            result = Sketch(result.wrapped)
        elif all([obj._dim == 1 for obj in object_list]):
            result = Curve(result.wrapped)

    return result


def scale(
    objects: Union[Shape, Iterable[Shape]] = None,
    by: Union[float, tuple[float, float, float]] = 1,
    mode: Mode = Mode.REPLACE,
) -> Union[Curve, Sketch, Part, Compound]:
    """Generic Operation: scale

    Applies to 1, 2, and 3 dimensional objects.

    Scale a sequence of objects. Note that when scaling non-uniformly across
    the three axes, the type of the underlying object may change to bspline from
    line, circle, etc.

    Args:
        objects (Union[Edge, Face, Compound, Solid] or Iterable of): objects to scale
        by (Union[float, tuple[float, float, float]]): scale factor
        mode (Mode, optional): combination mode. Defaults to Mode.REPLACE.

    Raises:
        ValueError: missing objects
    """
    context: Builder = Builder._get_context("scale")

    if objects is None:
        if context is None or context is not None and context._obj is None:
            raise ValueError("objects must be provided")
        object_list = [context._obj]
    else:
        object_list = flatten_sequence(objects)

    validate_inputs(context, "scale", object_list)

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
    for obj in object_list:
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

    scale_compound = Compound(new_objects)
    if all([obj._dim == 3 for obj in object_list]):
        return Part(scale_compound.wrapped)
    if all([obj._dim == 2 for obj in object_list]):
        return Sketch(scale_compound.wrapped)
    if all([obj._dim == 1 for obj in object_list]):
        return Curve(scale_compound.wrapped)
    return scale_compound


#:TypeVar("SplitType"): Type of objects which can be offset
SplitType = Union[Edge, Wire, Face, Solid]


def split(
    objects: Union[SplitType, Iterable[SplitType]] = None,
    bisect_by: Plane = Plane.XZ,
    keep: Keep = Keep.TOP,
    mode: Mode = Mode.REPLACE,
):
    """Generic Operation: split

    Applies to 1, 2, and 3 dimensional objects.

    Bisect object with plane and keep either top, bottom or both.

    Args:
        objects (Union[Edge, Wire, Face, Solid] or Iterable of), objects to split
        bisect_by (Plane, optional): plane to segment part. Defaults to Plane.XZ.
        keep (Keep, optional): selector for which segment to keep. Defaults to Keep.TOP.
        mode (Mode, optional): combination mode. Defaults to Mode.REPLACE.

    Raises:
        ValueError: missing objects
    """
    context: Builder = Builder._get_context("split")

    if objects is None:
        if context is None or context is not None and context._obj is None:
            raise ValueError("objects must be provided")
        object_list = [context._obj]
    else:
        object_list = flatten_sequence(objects)

    validate_inputs(context, "split", object_list)

    new_objects = []
    for obj in object_list:
        new_objects.append(obj.split(bisect_by, keep))

    if context is not None:
        context._add_to_context(*new_objects, mode=mode)

    split_compound = Compound(new_objects)
    if all([obj._dim == 3 for obj in object_list]):
        return Part(split_compound.wrapped)
    if all([obj._dim == 2 for obj in object_list]):
        return Sketch(split_compound.wrapped)
    if all([obj._dim == 1 for obj in object_list]):
        return Curve(split_compound.wrapped)
    return split_compound


#:TypeVar("SweepType"): Type of objects which can be swept
SweepType = Union[Compound, Edge, Wire, Face, Solid]


def sweep(
    sections: Union[SweepType, Iterable[SweepType]] = None,
    path: Union[Curve, Edge, Wire, Iterable[Edge]] = None,
    multisection: bool = False,
    is_frenet: bool = False,
    transition: Transition = Transition.TRANSFORMED,
    normal: VectorLike = None,
    binormal: Union[Edge, Wire] = None,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Union[Part, Sketch]:
    """Generic Operation: sweep

    Sweep pending 1D or 2D objects along path.

    Args:
        sections (Union[Compound, Edge, Wire, Face, Solid]): cross sections to sweep into object
        path (Union[Curve, Edge, Wire], optional): path to follow.
            Defaults to context pending_edges.
        multisection (bool, optional): sweep multiple on path. Defaults to False.
        is_frenet (bool, optional): use frenet algorithm. Defaults to False.
        transition (Transition, optional): discontinuity handling option.
            Defaults to Transition.RIGHT.
        normal (VectorLike, optional): fixed normal. Defaults to None.
        binormal (Union[Edge, Wire], optional): guide rotation along path. Defaults to None.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination. Defaults to Mode.ADD.
    """
    context: Builder = Builder._get_context("sweep")

    section_list = (
        [*sections] if isinstance(sections, (list, tuple, filter)) else [sections]
    )
    section_list = [sec for sec in section_list if sec is not None]

    validate_inputs(context, "sweep", section_list)

    if path is None:
        if context is None or context is not None and not context.pending_edges:
            raise ValueError("path must be provided")
        path_wire = Wire(context.pending_edges)
        context.pending_edges = []
    else:
        if isinstance(path, Iterable):
            try:
                path_wire = Wire(path)
            except ValueError as err:
                raise ValueError("Unable to build path from edges") from err
        else:
            path_wire = Wire(path.edges()) if not isinstance(path, Wire) else path

    if not section_list:
        if (
            context is not None
            and isinstance(context, BuildPart)
            and context.pending_faces
        ):
            section_list = context.pending_faces
            context.pending_faces = []
            context.pending_face_planes = []
        else:
            raise ValueError("No sections provided")

    edge_list = []
    face_list = []
    for sec in section_list:
        if isinstance(sec, (Curve, Wire, Edge)):
            edge_list.extend(sec.edges())
        else:
            face_list.extend(sec.faces())

    # sweep to create solids
    new_solids = []
    if face_list:
        if binormal is None and normal is not None:
            binormal_mode = Vector(normal)
        elif isinstance(binormal, Edge):
            binormal_mode = Wire([binormal])
        else:
            binormal_mode = binormal
        if multisection:
            sections = [face.outer_wire() for face in face_list]
            new_solids = [
                Solid.sweep_multi(sections, path_wire, True, is_frenet, binormal_mode)
            ]
        else:
            new_solids = [
                Solid.sweep(
                    section=face,
                    path=path_wire,
                    make_solid=True,
                    is_frenet=is_frenet,
                    mode=binormal_mode,
                    transition=transition,
                )
                for face in face_list
            ]

    # sweep to create faces
    new_faces = []
    if edge_list:
        for sec in section_list:
            swept = Face.sweep(
                sec, path_wire, transition
            )  # Could generate a shell here
            new_faces.extend(swept.faces())

    if context is not None:
        context._add_to_context(*(new_solids + new_faces), clean=clean, mode=mode)
    elif clean:
        new_solids = [solid.clean() for solid in new_solids]
        new_faces = [face.clean() for face in new_faces]

    if new_solids:
        return Part(Compound(new_solids).wrapped)
    return Sketch(Compound(new_faces).wrapped)
