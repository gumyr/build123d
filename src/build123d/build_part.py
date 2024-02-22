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

from typing import Union

from build123d.build_common import Builder, logger
from build123d.build_enums import Mode
from build123d.geometry import Location, Plane
from build123d.topology import Edge, Face, Joint, Part, Solid, Wire


class BuildPart(Builder):
    """BuildPart

    The BuildPart class is another subclass of Builder for building parts
    (objects with the property of volume) from sketches or 3D objects.
    It has an _obj property that returns the current part being built, and
    several pending lists for storing faces, edges, and planes that will be
    integrated into the final part later. The class overrides the _add_to_pending
    method of Builder.

    Args:
        workplanes (Plane, optional): initial plane to work on. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _tag = "BuildPart"  # Alternate for __class__.__name__
    _obj_name = "part"  # Name of primary instance variable
    _shape = Solid  # Type of shapes being constructed
    _sub_class = Part  # Class of part/_obj

    @property
    def _obj(self) -> Part:
        return self.part

    @_obj.setter
    def _obj(self, value: Part) -> None:
        self.part = value

    @property
    def pending_edges_as_wire(self) -> Wire:
        """Return a wire representation of the pending edges"""
        return Wire.combine(self.pending_edges)[0]

    @property
    def location(self) -> Location:
        """Builder's location"""
        return self.part.location if self.part is not None else Location()

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.joints: dict[str, Joint] = {}
        self.part: Part = None
        self.pending_faces: list[Face] = []
        self.pending_face_planes: list[Plane] = []
        self.pending_planes: list[Plane] = []
        self.pending_edges: list[Edge] = []
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

    def _exit_extras(self):
        """Transfer joints on exit"""
        if self.joints:
            self.part.joints = self.joints
            for joint in self.part.joints.values():
                joint.parent = self.part
