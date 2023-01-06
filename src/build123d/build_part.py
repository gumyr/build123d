"""
BuildPart

name: build_part.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build 3D parts.

TODO:
- add TwistExtrude, ProjectText
- add centered to wedge

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
import inspect
from warnings import warn
from math import radians, tan, sqrt
from typing import Union, Iterable
from build123d.build_enums import Mode, Until, Select, Transition
from build123d.direct_api import (
    Edge,
    Wire,
    Vector,
    Solid,
    Compound,
    Location,
    VectorLike,
    ShapeList,
    Location,
    Face,
    Plane,
    Axis,
    Rotation,
    RotationLike,
    Shell,
)

from build123d.build_common import (
    Builder,
    logger,
    LocationList,
    WorkplaneList,
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
        return Wire.make_wire(self.pending_edges)

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

    def solids(self, select: Select = Select.ALL) -> ShapeList[Solid]:
        """Return Solids from Part

        Return either all or the solids created during the last operation.

        Args:
            select (Select, optional): Solid selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Solid]: Solids extracted
        """
        if select == Select.ALL:
            solid_list = self.part.solids()
        elif select == Select.LAST:
            solid_list = self.last_solids
        return ShapeList(solid_list)

    def _add_to_pending(self, *objects: Union[Edge, Face], face_plane: Plane = None):
        """Add objects to BuildPart pending lists

        Args:
            objects (Union[Edge, Face]): sequence of objects to add
        """
        new_faces = [o for o in objects if isinstance(o, Face)]
        for face in new_faces:
            logger.debug(
                "Adding Face to pending_faces at %s",
                face.location,
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
                else:
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
                        self.part = self.part.fuse(*new_solids).clean()
                elif mode == Mode.SUBTRACT:
                    if self.part is None:
                        raise RuntimeError("Nothing to subtract from")
                    self.part = self.part.cut(*new_solids).clean()
                elif mode == Mode.INTERSECT:
                    if self.part is None:
                        raise RuntimeError("Nothing to intersect with")
                    self.part = self.part.intersect(*new_solids).clean()
                elif mode == Mode.REPLACE:
                    self.part = Compound.make_compound(list(new_solids)).clean()

                logger.info(
                    "Completed integrating %d object(s) into part with Mode=%s",
                    len(new_solids),
                    mode,
                )

            post_vertices = set() if self.part is None else set(self.part.vertices())
            post_edges = set() if self.part is None else set(self.part.edges())
            post_faces = set() if self.part is None else set(self.part.faces())
            post_solids = set() if self.part is None else set(self.part.solids())
            self.last_vertices = list(post_vertices - pre_vertices)
            self.last_edges = list(post_edges - pre_edges)
            self.last_faces = list(post_faces - pre_faces)
            self.last_solids = list(post_solids - pre_solids)

            for plane in WorkplaneList._get_context().workplanes:
                global_faces = [plane.from_local_coords(face) for face in new_faces]
                global_edges = [plane.from_local_coords(edge) for edge in new_edges]
                self._add_to_pending(*global_edges)
                self._add_to_pending(*global_faces, face_plane=plane)

    @classmethod
    def _get_context(cls, caller=None) -> "BuildPart":
        """Return the instance of the current builder"""
        logger.info(
            "Context requested by %s",
            type(inspect.currentframe().f_back.f_locals["self"]).__name__,
        )

        result = cls._current.get(None)
        if caller is not None and result is None:
            if hasattr(caller, "_applies_to"):
                raise RuntimeError(
                    f"No valid context found, use one of {caller._applies_to}"
                )
            else:
                raise RuntimeError(f"No valid context found")

        return result


#
# Operations
#


class CounterBoreHole(Compound):
    """Part Operation: Counter Bore Hole

    Create a counter bore hole in part.

    Args:
        radius (float): hole size
        counter_bore_radius (float): counter bore size
        counter_bore_depth (float): counter bore depth
        depth (float, optional): hole depth - None implies through part. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        radius: float,
        counter_bore_radius: float,
        counter_bore_depth: float,
        depth: float = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        self.radius = radius
        self.counter_bore_radius = counter_bore_radius
        self.counter_bore_depth = counter_bore_depth
        self.depth = depth
        self.mode = mode

        new_solids = []
        for location in LocationList._get_context().locations:
            hole_depth = (
                context.part.fuse(Solid.make_box(1, 1, 1).locate(location))
                .bounding_box()
                .diagonal_length()
                if not depth
                else depth
            )
            new_solids.append(
                Solid.make_cylinder(
                    radius, hole_depth, Plane(origin=(0, 0, 0), z_dir=(0, 0, -1))
                )
                .fuse(
                    Solid.make_cylinder(
                        counter_bore_radius,
                        counter_bore_depth + hole_depth,
                        Plane((0, 0, -counter_bore_depth)),
                    )
                )
                .locate(location)
            )
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class CounterSinkHole(Compound):
    """Part Operation: Counter Sink Hole

    Create a counter sink hole in part.

    Args:
        radius (float): hole size
        counter_sink_radius (float): counter sink size
        depth (float, optional): hole depth - None implies through part. Defaults to None.
        counter_sink_angle (float, optional): cone angle. Defaults to 82.
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        radius: float,
        counter_sink_radius: float,
        depth: float = None,
        counter_sink_angle: float = 82,  # Common tip angle
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        self.radius = radius
        self.counter_sink_radius = counter_sink_radius
        self.depth = depth
        self.counter_sink_angle = counter_sink_angle
        self.mode = mode

        new_solids = []
        for location in LocationList._get_context().locations:
            hole_depth = (
                context.part.fuse(Solid.make_box(1, 1, 1).locate(location))
                .bounding_box()
                .diagonal_length()
                if not depth
                else depth
            )
            cone_height = counter_sink_radius / tan(radians(counter_sink_angle / 2.0))
            new_solids.append(
                Solid.make_cylinder(
                    radius, hole_depth, Plane(origin=(0, 0, 0), z_dir=(0, 0, -1))
                )
                .fuse(
                    Solid.make_cone(
                        counter_sink_radius,
                        0.0,
                        cone_height,
                        Plane(origin=(0, 0, 0), z_dir=(0, 0, -1)),
                    )
                )
                .fuse(Solid.make_cylinder(counter_sink_radius, hole_depth))
                .locate(location)
            )
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


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
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self, [to_extrude])

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

        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Hole(Compound):
    """Part Operation: Hole

    Create a hole in part.

    Args:
        radius (float): hole size
        depth (float, optional): hole depth - None implies through part. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        radius: float,
        depth: float = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        self.radius = radius
        self.depth = depth
        self.mode = mode

        # To ensure the hole will go all the way through the part when
        # no depth is specified, calculate depth based on the part and
        # hole location. In this case start the hole above the part
        # and go all the way through.
        new_solids = []
        for location in LocationList._get_context().locations:
            hole_depth = (
                2
                * context.part.fuse(Solid.make_box(1, 1, 1).locate(location))
                .bounding_box()
                .diagonal_length()
                if not depth
                else depth
            )
            hole_start = (0, 0, hole_depth / 2) if not depth else (0, 0, 0)
            new_solids.append(
                Solid.make_cylinder(
                    radius, hole_depth, Plane(origin=hole_start, z_dir=(0, 0, -1)), 360
                ).locate(location)
            )
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Loft(Solid):
    """Part Operation: Loft

    Loft the pending sketches/faces, across all workplanes, into a solid.

    Args:
        sections (Face): sequence of loft sections. If not provided, pending_faces
            will be used.
        ruled (bool, optional): discontiguous layer tangents. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(self, *sections: Face, ruled: bool = False, mode: Mode = Mode.ADD):

        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self, sections)

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
            ).clean()
            if not new_solid.isValid():
                raise RuntimeError("Failed to create valid loft")

        context._add_to_context(new_solid, mode=mode)
        super().__init__(new_solid.wrapped)


class Revolve(Compound):
    """Part Operation: Revolve

    Revolve the profile or pending sketches/face about the given axis.

    Args:
        profiles (Face, optional): sequence of 2D profile to revolve.
        axis (Axis): axis of rotation.
        revolution_arc (float, optional): angular size of revolution. Defaults to 360.0.
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
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self, profiles)

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
            face_plane = Plane(profile.to_pln())
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

        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Section(Compound):
    """Part Operation: Section

    Slices current part at the given height by section_by or current workplane(s).

    Args:
        section_by (Plane, optional): sequence of planes to section object.
            Defaults to None.
        height (float, optional): workplane offset. Defaults to 0.0.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        *section_by: Plane,
        height: float = 0.0,
        mode: Mode = Mode.INTERSECT,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        self.section_by = section_by
        self.height = height
        self.mode = mode

        max_size = context.part.bounding_box().diagonal_length()

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

        context._add_to_context(*planes, faces_to_pending=False, mode=mode)
        super().__init__(Compound.make_compound(planes).wrapped)


class Sweep(Compound):
    """Part Operation: Sweep

    Sweep pending sketches/faces along path.

    Args:
        sections (Union[Face, Compound]): sequence of sections to sweep
        path (Union[Edge, Wire], optional): path to follow.
            Defaults to context pending_edges.
        multisection (bool, optional): sweep multiple on path. Defaults to False.
        is_frenet (bool, optional): use freenet algorithm. Defaults to False.
        transition (Transition, optional): discontinuity handling option.
            Defaults to Transition.RIGHT.
        normal (VectorLike, optional): fixed normal. Defaults to None.
        binormal (Union[Edge, Wire], optional): guide rotation along path. Defaults to None.
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
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self, sections)

        self.sections = sections
        self.path = path
        self.multisection = multisection
        self.is_frenet = is_frenet
        self.transition = transition
        self.normal = normal
        self.binormal = binormal
        self.mode = mode

        if path is None:
            path_wire = context.pending_edges_as_wire
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

        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


#
# Objects
#


class Box(Compound):
    """Part Object: Box

    Create a box(es) and combine with part.

    Args:
        length (float): box size
        width (float): box size
        height (float): box size
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation

        self.length = length
        self.width = width
        self.height = height
        self.rotation = rotate
        self.centered = centered
        self.mode = mode

        center_offset = Vector(
            -length / 2 if centered[0] else 0,
            -width / 2 if centered[1] else 0,
            -height / 2 if centered[2] else 0,
        )
        new_solids = [
            Solid.make_box(length, width, height, Plane(center_offset)).locate(
                location * rotate
            )
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Cone(Compound):
    """Part Object: Cone

    Create a cone(s) and combine with part.

    Args:
        bottom_radius (float): cone size
        top_radius (float): top size, could be zero
        height (float): cone size
        arc_size (float, optional): angular size of cone. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        bottom_radius: float,
        top_radius: float,
        height: float,
        arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation

        self.bottom_radius = bottom_radius
        self.top_radius = top_radius
        self.height = height
        self.arc_size = arc_size
        self.rotation = rotate
        self.centered = centered
        self.mode = mode

        center_offset = Vector(
            0 if centered[0] else max(bottom_radius, top_radius),
            0 if centered[1] else max(bottom_radius, top_radius),
            -height / 2 if centered[2] else 0,
        )
        new_solids = [
            Solid.make_cone(
                bottom_radius,
                top_radius,
                height,
                Plane(center_offset),
                arc_size,
            ).locate(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Cylinder(Compound):
    """Part Object: Cylinder

    Create a cylinder(s) and combine with part.

    Args:
        radius (float): cylinder size
        height (float): cylinder size
        arc_size (float, optional): angular size of cone. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        radius: float,
        height: float,
        arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation

        self.radius = radius
        self.height = height
        self.arc_size = arc_size
        self.rotation = rotate
        self.centered = centered
        self.mode = mode

        center_offset = Vector(
            0 if centered[0] else radius,
            0 if centered[1] else radius,
            -height / 2 if centered[2] else 0,
        )
        new_solids = [
            Solid.make_cylinder(
                radius,
                height,
                Plane(center_offset),
                arc_size,
            ).locate(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Sphere(Compound):
    """Part Object: Sphere

    Create a sphere(s) and combine with part.

    Args:
        radius (float): sphere size
        arc_size1 (float, optional): angular size of sphere. Defaults to -90.
        arc_size2 (float, optional): angular size of sphere. Defaults to 90.
        arc_size3 (float, optional): angular size of sphere. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        radius: float,
        arc_size1: float = -90,
        arc_size2: float = 90,
        arc_size3: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation

        self.radius = radius
        self.arc_size1 = arc_size1
        self.arc_size2 = arc_size2
        self.arc_size3 = arc_size3
        self.rotation = rotate
        self.centered = centered
        self.mode = mode

        center_offset = Vector(
            0 if centered[0] else radius,
            0 if centered[1] else radius,
            0 if centered[2] else radius,
        )
        new_solids = [
            Solid.make_sphere(
                radius,
                Plane(origin=center_offset),
                arc_size1,
                arc_size2,
                arc_size3,
            ).locate(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Torus(Compound):
    """Part Object: Torus

    Create a torus(es) and combine with part.


    Args:
        major_radius (float): torus size
        minor_radius (float): torus size
        major_arc_size (float, optional): angular size of torus. Defaults to 0.
        minor_arc_size (float, optional): angular size or torus. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        major_radius: float,
        minor_radius: float,
        minor_start_angle: float = 0,
        minor_end_angle: float = 360,
        major_angle: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation

        self.major_radius = major_radius
        self.minor_radius = minor_radius
        self.minor_start_angle = minor_start_angle
        self.minor_end_angle = minor_end_angle
        self.major_angle = major_angle
        self.rotation = rotate
        self.centered = centered
        self.mode = mode

        center_offset = Vector(
            0 if centered[0] else major_radius + minor_radius,
            0 if centered[1] else major_radius + minor_radius,
            0 if centered[2] else minor_radius,
        )
        new_solids = [
            Solid.make_torus(
                major_radius,
                minor_radius,
                Plane(center_offset),
                minor_start_angle,
                minor_end_angle,
                major_angle,
            ).locate(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)


class Wedge(Compound):
    """Part Object: Wedge

    Create a wedge(s) and combine with part.

    Args:
        dx (float): distance along the X axis
        dy (float): distance along the Y axis
        dz (float): distance along the Z axis
        xmin (float): minimum X location
        zmin (float): minimum Z location
        xmax (float): maximum X location
        zmax (float): maximum Z location
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag()]

    def __init__(
        self,
        dx: float,
        dy: float,
        dz: float,
        xmin: float,
        zmin: float,
        xmax: float,
        zmax: float,
        rotation: RotationLike = (0, 0, 0),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context(self)
        context.validate_inputs(self)

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation

        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.xmin = xmin
        self.zmin = zmin
        self.xmax = xmax
        self.zmax = zmax
        self.rotation = rotate
        self.mode = mode

        new_solids = [
            Solid.make_wedge(dx, dy, dz, xmin, zmin, xmax, zmax).moved(
                location * rotate
            )
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.make_compound(new_solids).wrapped)
