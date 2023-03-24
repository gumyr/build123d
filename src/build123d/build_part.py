"""
BuildPart

name: build_part.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build 3D parts.

TODO:
- add TwistExtrude, ProjectText

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

import sys
from typing import Union

from build123d.build_common import Builder, WorkplaneList, logger
from build123d.build_enums import Mode
from build123d.geometry import Location, Plane
from build123d.topology import Compound, Edge, Face, Part, Solid, Wire


class BuildPart(Builder):
    """BuildPart

    Create 3D parts (objects with the property of volume) from sketches or 3D objects.

    Args:
        workplane (Plane, optional): initial plane to work on. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    """

    @staticmethod
    def _tag() -> str:
        return "BuildPart"

    @property
    def _obj(self):
        return self.part

    @property
    def _obj_name(self):
        return "part"

    @property
    def pending_edges_as_wire(self) -> Wire:
        """Return a wire representation of the pending edges"""
        return Wire.combine(self.pending_edges)[0]

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.part: Compound = None
        self.initial_planes = workplanes
        self.pending_faces: list[Face] = []
        self.pending_face_planes: list[Plane] = []
        self.pending_planes: list[Plane] = []
        self.pending_edges: list[Edge] = []
        self.last_faces = []
        self.last_solids = []
        super().__init__(*workplanes, mode=mode)

    def _add_to_pending(self, *objects: Union[Edge, Face], face_plane: Plane = None):
        """Add objects to BuildPart pending lists

        Args:
            objects (Union[Edge, Face]): sequence of objects to add
        """
        new_faces = [o for o in objects if isinstance(o, Face)]
        for face in new_faces:
            logger.debug(
                "Adding Face to pending_faces at %s on pending_face_plane %s",
                face.location,
                face_plane,
            )
            self.pending_faces.append(face)
            self.pending_face_planes.append(face_plane)

        new_edges = [o for o in objects if isinstance(o, Edge)]
        for edge in new_edges:
            logger.debug(
                "Adding Edge to pending_edges at %s",
                edge.location,
            )
            self.pending_edges.append(edge)

    def _add_to_context(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        faces_to_pending: bool = True,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        """Add objects to BuildPart instance

        Core method to interface with BuildPart instance. Input sequence of objects is
        parsed into lists of edges, faces, and solids. Edges and faces are added to pending
        lists. Solids are combined with current part.

        Each operation generates a list of vertices, edges, faces, and solids that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of objects to add
            faces_to_pending (bool, optional): add faces to pending_faces. Default to True.
            clean (bool, optional): Remove extraneous internal structure. Defaults to True.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Raises:
            ValueError: Nothing to subtract from
            ValueError: Nothing to intersect with
            ValueError: Invalid mode
        """
        if mode != Mode.PRIVATE:
            new_faces, new_edges, new_solids = [], [], []
            for obj in objects:
                if isinstance(obj, Face):
                    new_faces.append(obj)
                elif isinstance(obj, Solid):
                    new_solids.append(obj)
                elif isinstance(obj, Edge):
                    new_edges.append(obj)
                elif isinstance(obj, Compound):
                    new_edges.extend(obj.get_type(Edge))
                    new_edges.extend([w.edges() for w in obj.get_type(Wire)])
                    new_faces.extend(obj.get_type(Face))
                    new_solids.extend(obj.get_type(Solid))
                elif not sys.exc_info()[1]:  # No exception is being processed
                    raise ValueError(
                        f"BuildPart doesn't accept {type(obj)}"
                        f" did you intend <keyword>={obj}?"
                    )
            if not faces_to_pending:
                new_solids.extend(new_faces)
                new_faces = []

            pre_vertices = set() if self.part is None else set(self.part.vertices())
            pre_edges = set() if self.part is None else set(self.part.edges())
            pre_faces = set() if self.part is None else set(self.part.faces())
            pre_solids = set() if self.part is None else set(self.part.solids())

            if new_solids:
                logger.debug(
                    "Attempting to integrate %d object(s) into part with Mode=%s",
                    len(new_solids),
                    mode,
                )

                if mode == Mode.ADD:
                    if self.part is None:
                        if len(new_solids) == 1:
                            self.part = new_solids[0]
                        else:
                            self.part = new_solids.pop().fuse(*new_solids)
                    else:
                        self.part = self.part.fuse(*new_solids)
                elif mode == Mode.SUBTRACT:
                    if self.part is None:
                        raise RuntimeError("Nothing to subtract from")
                    self.part = self.part.cut(*new_solids)
                elif mode == Mode.INTERSECT:
                    if self.part is None:
                        raise RuntimeError("Nothing to intersect with")
                    self.part = self.part.intersect(*new_solids)
                elif mode == Mode.REPLACE:
                    self.part = Compound.make_compound(list(new_solids))
                if clean:
                    self.part = self.part.clean()

                logger.info(
                    "Completed integrating %d object(s) into part with Mode=%s",
                    len(new_solids),
                    mode,
                )
            if self.part is not None:
                if isinstance(self.part, Compound):
                    self.part = Part(self.part.wrapped)
                else:
                    self.part = Part(Compound.make_compound(self.part.solids()).wrapped)

            post_vertices = set() if self.part is None else set(self.part.vertices())
            post_edges = set() if self.part is None else set(self.part.edges())
            post_faces = set() if self.part is None else set(self.part.faces())
            post_solids = set() if self.part is None else set(self.part.solids())
            self.last_vertices = list(post_vertices - pre_vertices)
            self.last_edges = list(post_edges - pre_edges)
            self.last_faces = list(post_faces - pre_faces)
            self.last_solids = list(post_solids - pre_solids)

            self._add_to_pending(*new_edges)
            for plane in WorkplaneList._get_context().workplanes:
                global_faces = [plane.from_local_coords(face) for face in new_faces]
                self._add_to_pending(*global_faces, face_plane=plane)
