"""
BuildSketch

name: build_sketch.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build planar sketches.

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
from __future__ import annotations

from typing import Union

from build123d.build_common import Builder, WorkplaneList, logger
from build123d.build_enums import Mode
from build123d.geometry import Location, Plane, Vector
from build123d.topology import Compound, Edge, Face, ShapeList, Sketch, Wire


class BuildSketch(Builder):
    """BuildSketch

    Create planar 2D sketches (objects with area but not volume) from faces or lines.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    @staticmethod
    def _tag() -> str:
        """The name of the builder"""
        return "BuildSketch"

    @property
    def _obj(self) -> Compound:
        """The builder's object"""
        return self.sketch_local

    @property
    def _obj_name(self):
        """The name of the builder's object"""
        return "sketch"

    @property
    def sketch(self):
        """The global version of the sketch - may contain multiple sketches"""
        workplanes = (
            self.exit_workplanes
            if self.exit_workplanes
            else WorkplaneList._get_context().workplanes
        )
        global_objs = []
        for plane in workplanes:
            for face in self.sketch_local.faces():
                global_objs.append(plane.from_local_coords(face))
        return Sketch(Compound.make_compound(global_objs).wrapped)

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.workplanes = workplanes
        self.mode = mode
        self.sketch_local: Compound = None
        self.pending_edges: ShapeList[Edge] = ShapeList()
        self.last_faces: ShapeList[Face] = ShapeList()
        super().__init__(*workplanes, mode=mode)

    def solids(self, *args):
        """solids() not implemented"""
        raise NotImplementedError("solids() doesn't apply to BuildSketch")

    def consolidate_edges(self) -> Union[Wire, list[Wire]]:
        """Unify pending edges into one or more Wires"""
        wires = Wire.combine(self.pending_edges)
        return wires if len(wires) > 1 else wires[0]

    def _add_to_context(
        self, *objects: Union[Edge, Wire, Face, Compound], mode: Mode = Mode.ADD
    ):
        """Add objects to BuildSketch instance

        Core method to interface with BuildSketch instance. Input sequence of objects is
        parsed into lists of edges and faces. Edges are added to pending
        lists. Faces are combined with current sketch.

        Each operation generates a list of vertices, edges, and faces that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            objects (Union[Edge, Wire, Face, Compound]): sequence of objects to add
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Raises:
            ValueError: Nothing to subtract from
            ValueError: Nothing to intersect with
            ValueError: Invalid mode
        """
        if mode != Mode.PRIVATE:
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            new_wires = [obj for obj in objects if isinstance(obj, Wire)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(compound.get_type(Face))
                new_edges.extend(compound.get_type(Edge))
                new_wires.extend(compound.get_type(Wire))

            # Align objects with Plane.XY if elevated
            for obj in new_faces + new_edges + new_wires:
                if obj.position.Z != 0.0:
                    logger.info("%s realigned to Sketch's Plane", type(obj).__name__)
                    obj.position = obj.position - Vector(0, 0, obj.position.Z)
                if isinstance(obj, Face) and not obj.is_coplanar(Plane.XY):
                    raise ValueError("Face not coplanar with sketch")

            pre_vertices = (
                set()
                if self.sketch_local is None
                else set(self.sketch_local.vertices())
            )
            pre_edges = (
                set() if self.sketch_local is None else set(self.sketch_local.edges())
            )
            pre_faces = (
                set() if self.sketch_local is None else set(self.sketch_local.faces())
            )
            if new_faces:
                logger.debug(
                    "Attempting to integrate %d Face(s) into sketch with Mode=%s",
                    len(new_faces),
                    mode,
                )
                if mode == Mode.ADD:
                    if self.sketch_local is None:
                        self.sketch_local = Compound.make_compound(new_faces)
                    else:
                        self.sketch_local = self.sketch_local.fuse(*new_faces).clean()
                elif mode == Mode.SUBTRACT:
                    if self.sketch_local is None:
                        raise RuntimeError("No sketch to subtract from")
                    self.sketch_local = self.sketch_local.cut(*new_faces).clean()
                elif mode == Mode.INTERSECT:
                    if self.sketch_local is None:
                        raise RuntimeError("No sketch to intersect with")
                    self.sketch_local = self.sketch_local.intersect(*new_faces).clean()
                elif mode == Mode.REPLACE:
                    self.sketch_local = Compound.make_compound(new_faces).clean()

                if self.sketch_local is not None:
                    if isinstance(self.sketch_local, Compound):
                        self.sketch_local = Sketch(self.sketch_local.wrapped)
                    else:
                        self.sketch_local = Sketch(
                            Compound.make_compound(self.sketch_local.faces()).wrapped
                        )

                logger.debug(
                    "Completed integrating %d Face(s) into sketch with Mode=%s",
                    len(new_faces),
                    mode,
                )

            post_vertices = (
                set()
                if self.sketch_local is None
                else set(self.sketch_local.vertices())
            )
            post_edges = (
                set() if self.sketch_local is None else set(self.sketch_local.edges())
            )
            post_faces = (
                set() if self.sketch_local is None else set(self.sketch_local.faces())
            )
            self.last_vertices = ShapeList(post_vertices - pre_vertices)
            self.last_edges = ShapeList(post_edges - pre_edges)
            self.last_faces = ShapeList(post_faces - pre_faces)

            self.pending_edges.extend(
                new_edges + [e for w in new_wires for e in w.edges()]
            )
