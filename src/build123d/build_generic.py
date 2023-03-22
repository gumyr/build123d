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
import logging
from typing import Union

from build123d.build_common import Builder, LocationList, WorkplaneList, validate_inputs
from build123d.build_enums import Mode
from build123d.build_line import BuildLine
from build123d.build_part import BuildPart
from build123d.build_sketch import BuildSketch
from build123d.geometry import Axis, Rotation, RotationLike
from build123d.topology import Compound, Edge, Face, Solid, Wire

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
        if context is None:
            raise RuntimeError("Add must have an active builder context")
        validate_inputs(context, self, objects)

        if isinstance(context, BuildPart):
            if rotation is None:
                rotation = Rotation(0, 0, 0)
            elif isinstance(rotation, float):
                raise ValueError("Float values of rotation are not valid for BuildPart")
            elif isinstance(rotation, tuple):
                rotation = Rotation(*rotation)

            objects = [obj.moved(rotation) for obj in objects]
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
