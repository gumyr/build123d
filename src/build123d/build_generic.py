"""
BuildGeneric

name: build_generic.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library of generic classes used by other
    build123d builders.

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
from build123d.direct_api import (
    Edge,
    Wire,
    Vector,
    Compound,
    Location,
    VectorLike,
    ShapeList,
    Face,
    Plane,
    Matrix,
    Rotation,
    RotationLike,
    Shape,
    Vertex,
    Solid,
    Axis,
)
from build123d import (
    BuildLine,
    BuildSketch,
    BuildPart,
    Builder,
    LocationList,
    WorkplaneList,
)

logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")


#
# Objects
#


class Add(Compound):
    """Generic Object: Add Object to Part or Sketch

    Add an object to the builder.

    if BuildPart:
        Edges and Wires are added to pending_edges. Compounds of Face are added to
        pending_faces. Solids or Compounds of Solid are combined into the part.
    elif BuildSketch:
        Edges and Wires are added to pending_edges. Compounds of Face are added to sketch.
    elif BuildLine:
        Edges and Wires are added to line.

    Args:
        objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of objects to add
        rotation (Union[float, RotationLike], optional): rotation angle for sketch,
            rotation about each axis for part. Defaults to None.
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag(), BuildLine._tag()]

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        rotation: Union[float, RotationLike] = None,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if isinstance(context, BuildPart):
            rotation_value = (0, 0, 0) if rotation is None else rotation
            rotate = (
                Rotation(*rotation_value)
                if isinstance(rotation_value, tuple)
                else rotation
            )
            objects = [obj.moved(rotate) for obj in objects]
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            new_wires = [obj for obj in objects if isinstance(obj, Wire)]
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_solids = [obj for obj in objects if isinstance(obj, Solid)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_edges.extend(compound.get_type(Edge))
                new_wires.extend(compound.get_type(Wire))
                new_faces.extend(compound.get_type(Face))
                new_solids.extend(compound.get_type(Solid))
            for new_wire in new_wires:
                new_edges.extend(new_wire.edges())

            # Add the pending Edges in one group
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
            context._add_to_context(*located_solids, mode=mode)
            new_objects.extend(located_solids)

        elif isinstance(context, (BuildLine, BuildSketch)):
            rotation_angle = rotation if isinstance(rotation, (int, float)) else 0.0
            new_objects = []
            for obj in objects:
                new_objects.extend(
                    [
                        obj.rotate(Axis.Z, rotation_angle).moved(location)
                        for location in LocationList._get_context().local_locations
                    ]
                )
            context._add_to_context(*new_objects, mode=mode)

        super().__init__(Compound.make_compound(new_objects).wrapped)


#
# Operations
#


class BoundingBox(Compound):
    """Generic Operation: Add Bounding Box

    Applies to: BuildSketch and BuildPart

    Add the 2D or 3D bounding boxes of the object sequence

    Args:
        objects (Shape): sequence of objects
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag()]

    def __init__(
        self,
        *objects: Shape,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if isinstance(context, BuildPart):
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
                        Plane(
                            (bounding_box.min.X, bounding_box.min.Y, bounding_box.min.Z)
                        ),
                    )
                )
            context._add_to_context(*new_objects, mode=mode)
            super().__init__(Compound.make_compound(new_objects).wrapped)

        elif isinstance(context, BuildSketch):
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
                    Face.make_from_wires(
                        Wire.make_polygon([Vector(v) for v in vertices])
                    )
                )
            for face in new_faces:
                context._add_to_context(face, mode=mode)
            super().__init__(Compound.make_compound(new_faces).wrapped)


class Chamfer(Compound):
    """Generic Operation: Chamfer

    Applies to: BuildSketch and BuildPart

    Chamfer the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to chamfer
        length (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.

    Raises:
        ValueError: objects must be Edges
        ValueError: objects must be Vertices
        RuntimeError: Builder not supported
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag()]

    def __init__(
        self, *objects: Union[Edge, Vertex], length: float, length2: float = None
    ):
        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if isinstance(context, BuildPart):
            if not all([isinstance(obj, Edge) for obj in objects]):
                raise ValueError("BuildPart Chamfer operation takes only Edges")
            new_part = context.part.chamfer(length, length2, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            if not all([isinstance(obj, Vertex) for obj in objects]):
                raise ValueError("BuildSketch Chamfer operation takes only Vertices")
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.chamfer_2d(length, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.make_compound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)


class Fillet(Compound):
    """Generic Operation: Fillet

    Applies to: BuildSketch and BuildPart

    Fillet the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to fillet
        radius (float): fillet size - must be less than 1/2 local width

    Raises:
        ValueError: objects must be Edges
        ValueError: objects must be Vertices
        RuntimeError: Builder not supported
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag()]

    def __init__(self, *objects: Union[Edge, Vertex], radius: float):
        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if isinstance(context, BuildPart):
            if not all([isinstance(obj, Edge) for obj in objects]):
                raise ValueError("BuildPart Fillet operation takes only Edges")
            new_part = context.part.fillet(radius, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            if not all([isinstance(obj, Vertex) for obj in objects]):
                raise ValueError("BuildSketch Fillet operation takes only Vertices")
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.fillet_2d(radius, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.make_compound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)


class Mirror(Compound):
    """Generic Operation: Mirror

    Applies to: BuildLine, BuildSketch, and BuildPart

    Mirror a sequence of objects over the given plane.

    Args:
        objects (Union[Edge, Face,Compound]): sequence of edges or faces to mirror
        about (Plane, optional): reference plane. Defaults to "XZ".
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag(), BuildLine._tag()]

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Compound],
        about: Plane = Plane.XZ,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if not objects:
            objects = [context._obj]

        self.objects = objects
        self.about = about
        self.mode = mode

        mirrored = [copy.deepcopy(o).mirror(about) for o in objects]

        context._add_to_context(*mirrored, mode=mode)
        super().__init__(Compound.make_compound(mirrored).wrapped)


class Offset(Compound):
    """Generic Operation: Offset

    Applies to: BuildLine, BuildSketch, and BuildPart

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
        ValueError: Invalid object type
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag(), BuildLine._tag()]

    def __init__(
        self,
        *objects: Union[Edge, Face, Solid, Compound],
        amount: float,
        openings: Union[Face, list[Face]] = None,
        kind: Kind = Kind.ARC,
        mode: Mode = Mode.REPLACE,
    ):
        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if not objects:
            objects = [context._obj]

        self.objects = objects
        self.amount = amount
        self.openings = openings
        self.kind = kind
        self.mode = mode

        edges = []
        faces = []
        edges = []
        solids = []
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
            if len(edges) == 1:
                raise ValueError("At least two edges are required")
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
        context._add_to_context(*new_objects, mode=mode)
        super().__init__(Compound.make_compound(new_objects).wrapped)


class Scale(Compound):
    """Generic Operation: Scale

    Applies to: BuildLine, BuildSketch, and BuildPart

    Scale a sequence of objects.

    Args:
        objects (Union[Edge, Face, Compound, Solid]): sequence of objects
        by (Union[float, tuple[float, float, float]]): scale factor
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag(), BuildLine._tag()]

    def __init__(
        self,
        *objects: Shape,
        by: Union[float, tuple[float, float, float]],
        mode: Mode = Mode.REPLACE,
    ):
        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if not objects:
            objects = [context._obj]

        self.objects = objects
        self.by = by
        self.mode = mode

        if isinstance(by, (int, float)):
            factor = Vector(by, by, by)
        elif (
            isinstance(by, (tuple))
            and len(by) == 3
            and all(isinstance(s, (int, float)) for s in by)
        ):
            factor = Vector(by)
        else:
            raise ValueError("by must be a float or a three tuple of float")

        scale_matrix = Matrix(
            [
                [factor.X, 0.0, 0.0, 0.0],
                [0.0, factor.Y, 0.0, 0.0],
                [0.0, 0.0, factor.Z, 0.0],
                [0.0, 0.0, 00.0, 1.0],
            ]
        )
        new_objects = []
        for obj in objects:
            current_location = obj.location
            obj_at_origin = obj.located(Location(Vector()))
            new_objects.append(
                obj_at_origin.transform_geometry(scale_matrix).locate(current_location)
            )

        context._add_to_context(*new_objects, mode=mode)

        super().__init__(Compound.make_compound(new_objects).wrapped)


class Split(Compound):
    """Generic Operation: Split

    Applies to: BuildLine, BuildSketch, and BuildPart

    Bisect object with plane and keep either top, bottom or both.

    Args:
        objects (Union[Edge, Wire, Face, Solid]), objects to split
        bisect_by (Plane, optional): plane to segment part. Defaults to Plane.XZ.
        keep (Keep, optional): selector for which segment to keep. Defaults to Keep.TOP.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """

    _applies_to = [BuildPart._tag(), BuildSketch._tag(), BuildLine._tag()]

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid],
        bisect_by: Plane = Plane.XZ,
        keep: Keep = Keep.TOP,
        mode: Mode = Mode.REPLACE,
    ):
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

        context: Builder = Builder._get_context(self)
        context.validate_inputs(self, objects)

        if not objects:
            objects = [context._obj]

        self.objects = objects
        self.bisect_by = bisect_by
        self.keep = keep
        self.mode = mode

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

        context._add_to_context(*new_objects, mode=mode)
        super().__init__(Compound.make_compound(new_objects).wrapped)
