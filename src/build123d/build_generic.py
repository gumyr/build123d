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
from typing import Union
from build123d import (
    BuildLine,
    BuildSketch,
    BuildPart,
    Mode,
    RotationLike,
    Rotation,
    Axis,
    Builder,
    LocationList,
    Kind,
)
from cadquery import (
    Shape,
    Vertex,
    Plane,
    Compound,
    Edge,
    Wire,
    Face,
    Solid,
    Location,
    Vector,
)
import logging

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

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        rotation: Union[float, RotationLike] = None,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            rotation_value = (0, 0, 0) if rotation is None else rotation
            rotate = (
                Rotation(*rotation_value)
                if isinstance(rotation_value, tuple)
                else rotation
            )
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_solids = [
                obj.moved(rotate) for obj in objects if isinstance(obj, Solid)
            ]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(compound.get_type(Face))
                new_solids.extend(compound.get_type(Solid))
            new_objects = [obj for obj in objects if isinstance(obj, Edge)]
            for new_wires in filter(lambda o: isinstance(o, Wire), objects):
                new_objects.extend(new_wires.Edges())

            # Add to pending faces and edges
            context._add_to_pending(*new_faces)
            context._add_to_pending(*new_objects)

            # Can't use get_and_clear_locations because the solid needs to be
            # oriented to the workplane after being moved to a local location
            new_objects = [
                solid.moved(location)
                for solid in new_solids
                for location in LocationList._get_context().locations
            ]
            context.locations = [Location(Vector())]
            context._add_to_context(*new_objects, mode=mode)
        elif isinstance(context, (BuildLine, BuildSketch)):
            rotation_angle = rotation if isinstance(rotation, (int, float)) else 0.0
            new_objects = []
            for obj in objects:
                new_objects.extend(
                    [
                        obj.rotate(
                            Vector(0, 0, 0), Vector(0, 0, 1), rotation_angle
                        ).moved(location)
                        for location in LocationList._get_context().locations
                    ]
                )
            context._add_to_context(*new_objects, mode=mode)
        # elif isinstance(context, BuildLine):
        #     new_objects = [obj for obj in objects if isinstance(obj, Edge)]
        #     for new_wires in filter(lambda o: isinstance(o, Wire), objects):
        #         new_objects.extend(new_wires.Edges())
        #     context._add_to_context(*new_objects, mode=mode)
        else:
            raise RuntimeError(
                f"Add does not support builder {context.__class__.__name__}"
            )
        super().__init__(Compound.makeCompound(new_objects).wrapped)


#
# Operations
#


class BoundingBox(Compound):
    """Generic Operation: Add Bounding Box to Part or Sketch

    Add the 2D or 3D bounding boxes of the object sequence

    Args:
        objects (Shape): sequence of objects
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Shape,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            new_objects = []
            for obj in objects:
                if isinstance(obj, Vertex):
                    continue
                bounding_box = obj.BoundingBox()
                new_objects.append(
                    Solid.makeBox(
                        bounding_box.xlen,
                        bounding_box.ylen,
                        bounding_box.zlen,
                        pnt=(bounding_box.xmin, bounding_box.ymin, bounding_box.zmin),
                    )
                )
            context._add_to_context(*new_objects, mode=mode)
            super().__init__(Compound.makeCompound(new_objects).wrapped)

        elif isinstance(context, BuildSketch):
            new_faces = []
            for obj in objects:
                if isinstance(obj, Vertex):
                    continue
                bounding_box = obj.BoundingBox()
                vertices = [
                    (bounding_box.xmin, bounding_box.ymin),
                    (bounding_box.xmin, bounding_box.ymax),
                    (bounding_box.xmax, bounding_box.ymax),
                    (bounding_box.xmax, bounding_box.ymin),
                    (bounding_box.xmin, bounding_box.ymin),
                ]
                new_faces.append(
                    Face.makeFromWires(Wire.makePolygon([Vector(v) for v in vertices]))
                )
            for face in new_faces:
                context._add_to_context(face, mode=mode)
            super().__init__(Compound.makeCompound(new_faces).wrapped)

        else:
            raise RuntimeError(
                f"BoundingBox does not support builder {context.__class__.__name__}"
            )


class Chamfer(Compound):
    """Generic Operation: Chamfer for Part and Sketch

    Chamfer the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to chamfer
        length (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.
    """

    def __init__(
        self, *objects: Union[Edge, Vertex], length: float, length2: float = None
    ):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            new_part = context.part.chamfer(length, length2, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.Vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.chamfer2D(length, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Chamfer does not support builder {context.__class__.__name__}"
            )


class Fillet(Compound):
    """Generic Operation: Fillet for Part and Sketch

    Fillet the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to fillet
        radius (float): fillet size - must be less than 1/2 local width
    """

    def __init__(self, *objects: Union[Edge, Vertex], radius: float):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            new_part = context.part.fillet(radius, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.Vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.fillet2D(radius, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Fillet does not support builder {context.__class__.__name__}"
            )


class Mirror(Compound):
    """Generic Operation: Mirror

    Add the mirror of the provided sequence of faces about the given axis to Line or Sketch.

    Args:
        objects (Union[Edge, Face,Compound]): sequence of edges or faces to mirror
        axis (Axis, optional): axis to mirror about. Defaults to Axis.X.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Compound],
        axis: Axis = Axis.X,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()
        new_edges = [obj for obj in objects if isinstance(obj, Edge)]
        new_wires = [obj for obj in objects if isinstance(obj, Wire)]
        new_faces = [obj for obj in objects if isinstance(obj, Face)]
        # new_solids = [obj for obj in objects if isinstance(obj, Solid)]
        for compound in filter(lambda o: isinstance(o, Compound), objects):
            new_faces.extend(compound.Faces())
            # new_solids.extend(compound.Solids())

        mirrored_edges = Plane.named("XY").mirrorInPlane(new_edges, axis=axis.name)
        mirrored_wires = Plane.named("XY").mirrorInPlane(new_wires, axis=axis.name)
        mirrored_faces = Plane.named("XY").mirrorInPlane(new_faces, axis=axis.name)
        # mirrored_solids = Plane.named("XY").mirrorInPlane(new_solids, axis=axis.name)

        if isinstance(context, BuildLine):
            context._add_to_context(*mirrored_edges, mode=mode)
            context._add_to_context(*mirrored_wires, mode=mode)
        elif isinstance(context, BuildSketch):
            context._add_to_context(*mirrored_edges, mode=mode)
            context._add_to_context(*mirrored_wires, mode=mode)
            context._add_to_context(*mirrored_faces, mode=mode)
        # elif isinstance(context, BuildPart):
        #     context._add_to_context(*mirrored_edges, mode=mode)
        #     context._add_to_context(*mirrored_wires, mode=mode)
        #     context._add_to_context(*mirrored_faces, mode=mode)
        #     context._add_to_context(*mirrored_solids, mode=mode)
        else:
            raise RuntimeError(
                f"Mirror does not support builder {context.__class__.__name__}"
            )
        super().__init__(
            Compound.makeCompound(
                mirrored_edges + mirrored_wires + mirrored_faces
            ).wrapped
        )


class Offset(Compound):
    """Generic Operation: Offset

    Offset the given sequence of Edges, Faces or Compound of Faces. The kind parameter
    controls the shape of the transitions.

    Args:
        amount (float): positive values external, negative internal
        kind (Kind, optional): transition shape. Defaults to Kind.ARC.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Only Compounds of Faces valid
    """

    def __init__(
        self,
        *objects: Union[Edge, Face, Compound],
        amount: float,
        kind: Kind = Kind.ARC,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()

        faces = []
        edges = []
        for obj in objects:
            if isinstance(obj, Compound):
                faces.extend(obj.Faces())
            elif isinstance(obj, Face):
                faces.append(obj)
            elif isinstance(obj, Edge):
                edges.append(obj)
            else:
                raise ValueError("Only Edges, Faces or Compounds are valid input types")

        new_faces = []
        for face in faces:
            new_faces.append(
                Face.makeFromWires(
                    face.outerWire().offset2D(amount, kind=kind.name.lower())[0]
                )
            )
        if edges:
            new_wires = Wire.assembleEdges(edges).offset2D(
                amount, kind=kind.name.lower()
            )
        else:
            new_wires = []

        if isinstance(context, BuildLine):
            context._add_to_context(*new_wires, mode=mode)
        elif isinstance(context, BuildSketch):
            context._add_to_context(*new_faces, mode=mode)
            context._add_to_context(*new_wires, mode=mode)

        if new_faces and new_wires:
            new_object = Compound.makeCompound(new_wires).fuse(
                Compound.makeCompound(new_faces)
            )
        elif new_wires:
            new_object = Compound.makeCompound(new_wires)
        else:
            new_object = Compound.makeCompound(new_faces)

        super().__init__(Compound.makeCompound(new_object).wrapped)
