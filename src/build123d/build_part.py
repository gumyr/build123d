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
import inspect
import sys
from math import radians, tan
from typing import Union, Iterable
from build123d.build_enums import Mode, Until, Transition, Align
from build123d.geometry import (
    Axis,
    Location,
    Plane,
    Rotation,
    RotationLike,
    Vector,
    VectorLike,
)
from build123d.topology import Compound, Edge, Face, Shell, Solid, Wire, Part

from build123d.build_common import (
    Builder,
    logger,
    LocationList,
    WorkplaneList,
    validate_inputs,
)


class BuildPart(Builder):
    """BuildPart

    Create 3D parts (objects with the property of volume) from sketches or 3D objects.

    Args:
        workplane (Plane, optional): initial plane to work on. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    """

    @staticmethod
    def _tag() -> str:
        return BuildPart

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
        # self.pending_edge_planes: list[Plane] = []
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


#
# Operations
#


class Extrude(Compound):
    """Part Operation: Extrude

    Extrude a sketch/face and combine with part.

    Args:
        to_extrude (Face): working face, if not provided use pending_faces.
            Defaults to None.
        amount (float): distance to extrude, sign controls direction
            Defaults to None.
        until (Until): extrude limit
        both (bool, optional): extrude in both directions. Defaults to False.
        taper (float, optional): taper angle. Defaults to 0.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        to_extrude: Face = None,
        amount: float = None,
        until: Until = None,
        both: bool = False,
        taper: float = 0.0,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self, [to_extrude])

        self.to_extrude = to_extrude
        self.amount = amount
        self.until = until
        self.both = both
        self.taper = taper
        self.mode = mode

        new_solids: list[Solid] = []
        if not to_extrude and not context.pending_faces:
            raise ValueError("Either a face or a pending face must be provided")

        if to_extrude:
            list_context = LocationList._get_context()
            workplane_context = WorkplaneList._get_context()
            faces, face_planes = [], []
            for plane in workplane_context.workplanes:
                for location in list_context.local_locations:
                    faces.append(to_extrude.moved(location))
                    face_planes.append(plane)
        else:
            faces = context.pending_faces
            face_planes = context.pending_face_planes
            context.pending_faces = []
            context.pending_face_planes = []

        logger.info(
            "%d face(s) to extrude on %d face plane(s)",
            len(faces),
            len(face_planes),
        )

        for face, plane in zip(faces, face_planes):
            for direction in [1, -1] if both else [1]:
                if amount:
                    new_solids.append(
                        Solid.extrude_linear(
                            section=face,
                            normal=plane.z_dir * amount * direction,
                            taper=taper,
                        )
                    )
                else:
                    new_solids.append(
                        Solid.extrude_until(
                            section=face,
                            target_object=context.part,
                            direction=plane.z_dir * direction,
                            until=until,
                        )
                    )

        context._add_to_context(*new_solids, clean=clean, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Loft(Solid):
    """Part Operation: Loft

    Loft the pending sketches/faces, across all workplanes, into a solid.

    Args:
        sections (Face): sequence of loft sections. If not provided, pending_faces
            will be used.
        ruled (bool, optional): discontiguous layer tangents. Defaults to False.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        *sections: Face,
        ruled: bool = False,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self, sections)

        self.sections = sections
        self.ruled = ruled
        self.mode = mode

        if not sections:
            loft_wires = [face.outer_wire() for face in context.pending_faces]
            context.pending_faces = []
            context.pending_face_planes = []
        else:
            loft_wires = [section.outer_wire() for section in sections]
        new_solid = Solid.make_loft(loft_wires, ruled)

        # Try to recover an invalid loft
        if not new_solid.is_valid():
            new_solid = Solid.make_solid(
                Shell.make_shell(new_solid.faces() + list(sections))
            )
            if clean:
                new_solid = new_solid.clean()
            if not new_solid.is_valid():
                raise RuntimeError("Failed to create valid loft")

        context._add_to_context(new_solid, clean=clean, mode=mode)
        super().__init__(new_solid.wrapped)


class Revolve(Compound):
    """Part Operation: Revolve

    Revolve the profile or pending sketches/face about the given axis.

    Args:
        profiles (Face, optional): sequence of 2D profile to revolve.
        axis (Axis): axis of rotation.
        revolution_arc (float, optional): angular size of revolution. Defaults to 360.0.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Invalid axis of revolution
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        *profiles: Face,
        axis: Axis,
        revolution_arc: float = 360.0,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self, profiles)

        self.profiles = profiles
        self.axis = axis
        self.revolution_arc = revolution_arc
        self.mode = mode

        # Make sure we account for users specifying angles larger than 360 degrees, and
        # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
        angle = revolution_arc % 360.0
        angle = 360.0 if angle == 0 else angle

        if not profiles:
            profiles = context.pending_faces
            context.pending_faces = []
            context.pending_face_planes = []

        self.profiles = profiles
        self.axis = axis
        self.revolution_arc = revolution_arc
        self.mode = mode

        new_solids = []
        for profile in profiles:
            # axis origin must be on the same plane as profile
            face_plane = Plane(profile)
            if not face_plane.contains(axis.position):
                raise ValueError(
                    "axis origin must be on the same plane as the face to revolve"
                )
            if not face_plane.contains(axis):
                raise ValueError(
                    "axis must be in the same plane as the face to revolve"
                )

            new_solid = Solid.revolve(profile, angle, axis)
            new_solids.extend(
                [
                    new_solid.moved(location)
                    for location in LocationList._get_context().locations
                ]
            )

        context._add_to_context(*new_solids, clean=clean, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Section(Compound):
    """Part Operation: Section

    Slices current part at the given height by section_by or current workplane(s).

    Args:
        section_by (Plane, optional): sequence of planes to section object.
            Defaults to None.
        height (float, optional): workplane offset. Defaults to 0.0.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        *section_by: Plane,
        height: float = 0.0,
        clean: bool = True,
        mode: Mode = Mode.INTERSECT,
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.section_by = section_by
        self.section_height = height
        self.mode = mode

        max_size = context.part.bounding_box().diagonal

        section_planes = (
            section_by if section_by else WorkplaneList._get_context().workplanes
        )
        section_planes = (
            section_planes if isinstance(section_planes, Iterable) else [section_planes]
        )
        planes = [
            Face.make_rect(
                2 * max_size,
                2 * max_size,
                Plane(origin=plane.origin + plane.z_dir * height, z_dir=plane.z_dir),
            )
            for plane in section_planes
        ]

        context._add_to_context(*planes, faces_to_pending=False, clean=clean, mode=mode)
        super().__init__(Compound.make_compound(planes).wrapped)


class Sweep(Compound):
    """Part Operation: Sweep

    Sweep pending sketches/faces along path.

    Args:
        sections (Union[Face, Compound]): sequence of sections to sweep
        path (Union[Edge, Wire], optional): path to follow.
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

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        *sections: Union[Face, Compound],
        path: Union[Edge, Wire] = None,
        multisection: bool = False,
        is_frenet: bool = False,
        transition: Transition = Transition.TRANSFORMED,
        normal: VectorLike = None,
        binormal: Union[Edge, Wire] = None,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        validate_inputs(context, self, sections)

        self.sections = sections
        self.sweep_path = path
        self.multisection = multisection
        self.is_frenet = is_frenet
        self.transition = transition
        self.normal = normal
        self.binormal = binormal
        self.mode = mode

        if path is None:
            path_wire = context.pending_edges_as_wire
            context.pending_edges = []
        else:
            path_wire = Wire.make_wire([path]) if isinstance(path, Edge) else path

        if sections:
            section_list = sections
        else:
            section_list = context.pending_faces
            context.pending_faces = []
            context.pending_face_planes = []

        if binormal is None and normal is not None:
            binormal_mode = Vector(normal)
        elif isinstance(binormal, Edge):
            binormal_mode = Wire.make_wire([binormal])
        else:
            binormal_mode = binormal

        new_solids = []
        for location in LocationList._get_context().locations:
            if multisection:
                sections = [section.outer_wire() for section in section_list]
                new_solid = Solid.sweep_multi(
                    sections, path_wire, True, is_frenet, binormal_mode
                ).moved(location)
            else:
                for section in section_list:
                    new_solid = Solid.sweep(
                        section=section,
                        path=path_wire,
                        make_solid=True,
                        is_frenet=is_frenet,
                        mode=binormal_mode,
                        transition=transition,
                    ).moved(location)
            new_solids.append(new_solid)

        context._add_to_context(*new_solids, clean=clean, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)
