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
from typing import Union, Iterable, List
from OCP.gp import gp_Pln, gp_Lin
from build123d.build_common import (
    Edge,
    Face,
    Wire,
    Vector,
    Compound,
    Solid,
    Plane,
    Shell,
    VectorLike,
    Builder,
    Mode,
    PlaneLike,
    Select,
    ShapeList,
    Until,
    Axis,
    Transition,
    RotationLike,
    logger,
    validate_inputs,
    Rotation,
    LocationList,
    WorkplaneList,
)


class BuildPart(Builder):
    """BuildPart

    Create 3D parts (objects with the property of volume) from sketches or 3D objects.

    Args:
        workplane (Plane, optional): initial plane to work on. Defaults to Plane.named("XY").
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    """

    @property
    def _obj(self):
        return self.part

    @property
    def _obj_name(self):
        return "part"

    @property
    def pending_edges_as_wire(self) -> Wire:
        """Return a wire representation of the pending edges"""
        return Wire.assembleEdges(self.pending_edges)

    def __init__(
        self,
        workplane: PlaneLike = Plane.named("XY"),
        mode: Mode = Mode.ADD,
    ):
        self.part: Compound = None
        initial_plane = (
            workplane if isinstance(workplane, Plane) else Plane.named(workplane)
        )
        self.initial_plane = initial_plane
        self.pending_faces: list[Face] = []
        self.pending_face_planes: list[Plane] = []
        self.pending_edges: list[Edge] = []
        self.pending_edge_planes: list[Plane] = []
        self.last_faces = []
        self.last_solids = []
        super().__init__(mode, initial_plane)

    def solids(self, select: Select = Select.ALL) -> ShapeList[Solid]:
        """Return Solids from Part

        Return either all or the solids created during the last operation.

        Args:
            select (Select, optional): Solid selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Solid]: Solids extracted
        """
        if select == Select.ALL:
            solid_list = self.part.Solids()
        elif select == Select.LAST:
            solid_list = self.last_solids
        return ShapeList(solid_list)

    def _add_to_pending(self, *objects: Union[Edge, Face]):
        """Add objects to BuildPart pending lists

        Args:
            objects (Union[Edge, Face]): sequence of objects to add
        """
        location_context = LocationList._get_context()
        for obj in objects:
            for loc, plane in zip(location_context.locations, location_context.planes):
                localized_obj = obj.moved(loc)
                if isinstance(obj, Face):
                    logger.debug(
                        "Adding localized Face to pending_faces at %s",
                        localized_obj.location(),
                    )
                    self.pending_faces.append(localized_obj)
                    self.pending_face_planes.append(plane)
                else:
                    logger.debug(
                        "Adding localized Edge to pending_edges at %s",
                        localized_obj.location(),
                    )
                    self.pending_edges.append(localized_obj)
                    self.pending_edge_planes.append(plane)

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
                    new_edges.extend([w.Edges() for w in obj.get_type(Wire)])
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

            pre_vertices = set() if self.part is None else set(self.part.Vertices())
            pre_edges = set() if self.part is None else set(self.part.Edges())
            pre_faces = set() if self.part is None else set(self.part.Faces())
            pre_solids = set() if self.part is None else set(self.part.Solids())

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
                    self.part = Compound.makeCompound(list(new_solids)).clean()

                logger.info(
                    "Completed integrating %d object(s) into part with Mode=%s",
                    len(new_solids),
                    mode,
                )

            post_vertices = set() if self.part is None else set(self.part.Vertices())
            post_edges = set() if self.part is None else set(self.part.Edges())
            post_faces = set() if self.part is None else set(self.part.Faces())
            post_solids = set() if self.part is None else set(self.part.Solids())
            self.last_vertices = list(post_vertices - pre_vertices)
            self.last_edges = list(post_edges - pre_edges)
            self.last_faces = list(post_faces - pre_faces)
            self.last_solids = list(post_solids - pre_solids)

            self._add_to_pending(*new_edges)
            self._add_to_pending(*new_faces)

    @classmethod
    def _get_context(cls) -> "BuildPart":
        """Return the instance of the current builder"""
        logger.info(
            "Context requested by %s",
            type(inspect.currentframe().f_back.f_locals["self"]).__name__,
        )
        return cls._current.get(None)


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

    def __init__(
        self,
        radius: float,
        counter_bore_radius: float,
        counter_bore_depth: float,
        depth: float = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

        self.radius = radius
        self.counter_bore_radius = counter_bore_radius
        self.counter_bore_depth = counter_bore_depth
        self.depth = depth
        self.mode = mode

        new_solids = []
        for location in LocationList._get_context().locations:
            hole_depth = (
                context.part.fuse(Solid.makeBox(1, 1, 1).locate(location))
                .BoundingBox()
                .DiagonalLength
                if not depth
                else depth
            )
            new_solids.append(
                Solid.makeCylinder(radius, hole_depth, (0, 0, 0), (0, 0, -1))
                .fuse(
                    Solid.makeCylinder(
                        counter_bore_radius,
                        counter_bore_depth + hole_depth,
                        (0, 0, -counter_bore_depth),
                        (0, 0, 1),
                    )
                )
                .locate(location)
            )
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


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

    def __init__(
        self,
        radius: float,
        counter_sink_radius: float,
        depth: float = None,
        counter_sink_angle: float = 82,  # Common tip angle
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

        self.radius = radius
        self.counter_sink_radius = counter_sink_radius
        self.depth = depth
        self.counter_sink_angle = counter_sink_angle
        self.mode = mode

        for location in LocationList._get_context().locations:
            hole_depth = (
                context.part.fuse(Solid.makeBox(1, 1, 1).locate(location))
                .BoundingBox()
                .DiagonalLength
                if not depth
                else depth
            )
            cone_height = counter_sink_radius / tan(radians(counter_sink_angle / 2.0))
            new_solids = [
                Solid.makeCylinder(radius, hole_depth, (0, 0, 0), (0, 0, -1))
                .fuse(
                    Solid.makeCone(
                        counter_sink_radius,
                        0.0,
                        cone_height,
                        (0, 0, 0),
                        (0, 0, -1),
                    )
                )
                .fuse(
                    Solid.makeCylinder(
                        counter_sink_radius, hole_depth, (0, 0, 0), (0, 0, 1)
                    )
                )
                .locate(location)
            ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


def _compute_exposed_faces(faces: List[Face], dir: Vector, taper: float = 0) -> List[Face]:
    """Compute (sub-)faces that do not fall within the extrusion of another face

    Thinking of extrusion as a beam of light and faces casting shadows, we return
    the illuminated, or exposed, faces.

    These faces are touched first when extruding in the given direction, assuming the
    source is far in the opposite direction.

    """
    vecNormal = dir.normalized()
    bbox = Compound.makeCompound(faces).BoundingBox()
    max_dimension = bbox.DiagonalLength

    # In coordinates where extrusion is along +Z
    rotation = Plane((0, 0, 0), normal=vecNormal).location.inverse
    rotated_bboxes = [face.moved(rotation).BoundingBox() for face in faces]

    extruded_faces: List[Solid] = [
        Solid.extrudeLinear(face, vecNormal * max_dimension, taper)
        for face in faces
    ]

    if taper == 0:
        ground = Face.makePlane(
            max_dimension,
            max_dimension,
            bbox.center,
            vecNormal,
        )
        shadows = [None] * len(faces)

        def might_intersect(i, j) -> bool:
            """
            Fast guess of whether faces[i] intersects extruded_faces[j]

            When in doubt, return TRUE.  Do not return FALSE incorrectly.

            """
            if ((rotated_bboxes[i].xmax <= rotated_bboxes[j].xmin) or
                (rotated_bboxes[i].xmin >= rotated_bboxes[j].xmax) or
                (rotated_bboxes[i].ymax <= rotated_bboxes[j].ymin) or
                (rotated_bboxes[i].ymin >= rotated_bboxes[j].ymax) or
                (rotated_bboxes[i].zmax <= rotated_bboxes[j].zmin)):
                return False
            if shadows[i] is None:
                shadows[i] = faces[i].project(ground, vecNormal)
            if shadows[j] is None:
                shadows[j] = faces[j].project(ground, vecNormal)
            if shadows[i].intersect(shadows[j]).Area() == 0:
                return False
            return True
    else:
        # TODO: Optimizations for tapered extrusions.

        def might_intersect(i, j) -> bool:
            """
            Fast guess of whether faces[i] intersects extruded_faces[j]

            When in doubt, return TRUE.  Do not return FALSE incorrectly.

            """
            if rotated_bboxes[i].zmax <= rotated_bboxes[j].zmin:
                return False
            return True

    trimmed_faces = []
    for i in range(len(faces)):
        # Cutting solids out of a face can be slow, so use might_intersect() to avoid
        # cutting away solids that are known not to intersect.
        to_cut = [
            extruded_faces[j]
            for j in range(len(faces))
            if i != j and might_intersect(i, j)
        ]
        if to_cut:
            trimmed_face = faces[i].cut(*to_cut)
            trimmed_faces.extend(trimmed_face.Faces())
        else:
            trimmed_face = faces[i]
            trimmed_faces.append(trimmed_face)

    return [face for face in trimmed_faces if face.Area() > 0]


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

    def __init__(
        self,
        to_extrude: Face = None,
        amount: float = None,
        until: Until = None,
        both: bool = False,
        taper: float = 0.0,
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context, [to_extrude])

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
            faces = [to_extrude.moved(loc) for loc in list_context.locations]
            face_planes = list_context.planes
        else:
            faces = context.pending_faces
            face_planes = context.pending_face_planes
            context.pending_faces = []
            context.pending_face_planes = []

        if until:
            # Determine the maximum dimensions of faces and part
            if len(faces) > 1:
                f_bb = Face.fuse(*faces).BoundingBox()
            else:
                f_bb = faces[0].BoundingBox()
            p_bb = context.part.BoundingBox()
            scene_xlen = max(f_bb.xmax, p_bb.xmax) - min(f_bb.xmin, p_bb.xmin)
            scene_ylen = max(f_bb.ymax, p_bb.ymax) - min(f_bb.ymin, p_bb.ymin)
            scene_zlen = max(f_bb.zmax, p_bb.zmax) - min(f_bb.zmin, p_bb.zmin)
            max_dimension = sqrt(scene_xlen**2 + scene_ylen**2 + scene_zlen**2)
            # Extract faces for later use
            part_faces = context.part.Faces()

        for face, plane in zip(faces, face_planes):
            for direction in [1, -1] if both else [1]:
                if amount:
                    new_solids.append(
                        Solid.extrudeLinear(
                            face,
                            plane.zDir * amount * direction,
                            taper,
                        )
                    )
                else:
                    # Extrude the face into a solid
                    extruded_face = Solid.extrudeLinear(
                        face, plane.zDir * max_dimension, taper
                    )
                    # Intersect the part's faces with this extruded solid
                    trim_faces_raw = [pf.intersect(extruded_face) for pf in part_faces]
                    # Extract Faces from any Compounds
                    trim_faces = []
                    for face in trim_faces_raw:
                        if isinstance(face, Face):
                            trim_faces.append(face)
                        elif isinstance(face, Compound):
                            trim_faces.extend(face.Faces())
                    # Remove faces with a normal perpendicular to the direction of extrusion
                    # as these will have no volume.
                    trim_faces = [
                        f
                        for f in trim_faces
                        if f.normalAt(f.Center()).dot(plane.zDir) != 0.0
                    ]

                    # Refine the trim faces to just where the extrusion should stop
                    if until == Until.NEXT:
                        trim_faces = _compute_exposed_faces(trim_faces, plane.zDir, taper)
                    else:
                        trim_faces = _compute_exposed_faces(trim_faces, -plane.zDir, -taper)

                    # Extrude the part faces back towards the face
                    trim_objects = [
                        Solid.extrudeLinear(
                            f, plane.zDir * max_dimension * -1.0, -taper
                        )
                        for f in trim_faces
                    ]
                    for trim_object, trim_face in zip(trim_objects, trim_faces):
                        if not trim_object.isValid():
                            warn(
                                message=f"Part face with area {trim_face.Area()} "
                                f"creates an invalid extrusion",
                                category=Warning,
                            )

                    # Fuse all the trim objects into one
                    if len(trim_objects) > 1:
                        trim_object = Solid.fuse(*trim_objects)
                    else:
                        trim_object = trim_objects[0]

                    # Finally, intersect the face extrusion with the trim extrusion
                    new_object = extruded_face.intersect(trim_object)
                    new_solids.append(new_object)

        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Hole(Compound):
    """Part Operation: Hole

    Create a hole in part.

    Args:
        radius (float): hole size
        depth (float, optional): hole depth - None implies through part. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT.
    """

    def __init__(
        self,
        radius: float,
        depth: float = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

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
                * context.part.fuse(Solid.makeBox(1, 1, 1).locate(location))
                .BoundingBox()
                .DiagonalLength
                if not depth
                else depth
            )
            hole_start = (0, 0, hole_depth / 2) if not depth else (0, 0, 0)
            new_solids.append(
                Solid.makeCylinder(
                    radius, hole_depth, hole_start, (0, 0, -1), 360
                ).locate(location)
            )
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Loft(Solid):
    """Part Operation: Loft

    Loft the pending sketches/faces, across all workplanes, into a solid.

    Args:
        sections (Face): sequence of loft sections. If not provided, pending_faces
            will be used.
        ruled (bool, optional): discontiguous layer tangents. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(self, *sections: Face, ruled: bool = False, mode: Mode = Mode.ADD):

        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context, sections)

        self.sections = sections
        self.ruled = ruled
        self.mode = mode

        if not sections:
            loft_wires = [face.outerWire() for face in context.pending_faces]
            context.pending_faces = []
        else:
            loft_wires = [section.outerWire() for section in sections]
        new_solid = Solid.makeLoft(loft_wires, ruled)

        # Try to recover an invalid loft
        if not new_solid.isValid():
            new_solid = Solid.makeSolid(
                Shell.makeShell(new_solid.Faces() + list(sections))
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

    def __init__(
        self,
        *profiles: Face,
        axis: Axis,
        revolution_arc: float = 360.0,
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context, profiles)

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

        self.profiles = profiles
        self.axis = axis
        self.revolution_arc = revolution_arc
        self.mode = mode

        new_solids = []
        for profile in profiles:
            # axis origin must be on the same plane as profile
            face_occt_pln = gp_Pln(
                profile.Center().toPnt(), profile.normalAt(profile.Center()).toDir()
            )
            if not face_occt_pln.Contains(axis.position.toPnt(), 1e-5):
                raise ValueError(
                    "axis origin must be on the same plane as the face to revolve"
                )
            if not face_occt_pln.Contains(
                gp_Lin(axis.position.toPnt(), axis.direction.toDir()), 1e-5, 1e-5
            ):
                raise ValueError(
                    "axis must be in the same plane as the face to revolve"
                )

            new_solid = Solid.revolve(
                profile,
                angle,
                axis.position,
                axis.position + axis.direction,
            )
            new_solids.extend(
                [
                    new_solid.moved(location)
                    for location in LocationList._get_context().locations
                ]
            )

        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Section(Compound):
    """Part Operation: Section

    Slices current part at the given height by section_by or current workplane(s).

    Args:
        section_by (Plane, optional): sequence of planes to section object.
            Defaults to None.
        height (float, optional): workplane offset. Defaults to 0.0.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """

    def __init__(
        self,
        *section_by: PlaneLike,
        height: float = 0.0,
        mode: Mode = Mode.INTERSECT,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

        self.section_by = section_by
        self.height = height
        self.mode = mode

        max_size = context.part.BoundingBox().DiagonalLength

        section_planes = (
            section_by if section_by else WorkplaneList._get_context().workplanes
        )
        section_planes = (
            section_planes if isinstance(section_planes, Iterable) else [section_planes]
        )
        # If the user provided named planes, convert
        section_planes = [
            section_plane
            if isinstance(section_plane, Plane)
            else Plane.named(section_plane)
            for section_plane in section_planes
        ]
        planes = [
            Face.makePlane(
                2 * max_size,
                2 * max_size,
                basePnt=plane.origin + plane.zDir * height,
                dir=plane.zDir,
            )
            for plane in section_planes
        ]

        context._add_to_context(*planes, faces_to_pending=False, mode=mode)
        super().__init__(Compound.makeCompound(planes).wrapped)


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
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context, sections)

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
            path_wire = Wire.assembleEdges([path]) if isinstance(path, Edge) else path

        if sections:
            section_list = sections
        else:
            section_list = context.pending_faces
            context.pending_faces = []

        if binormal is None and normal is not None:
            binormal_mode = Vector(normal)
        elif isinstance(binormal, Edge):
            binormal_mode = Wire.assembleEdges([binormal])
        else:
            binormal_mode = binormal

        new_solids = []
        for location in LocationList._get_context().locations:
            if multisection:
                sections = [section.outerWire() for section in section_list]
                new_solid = Solid.sweep_multi(
                    sections, path_wire, True, is_frenet, binormal_mode
                ).moved(location)
            else:
                for section in section_list:
                    new_solid = Solid.sweep(
                        section,
                        path_wire,
                        True,  # make solid
                        is_frenet,
                        binormal_mode,
                        transition.name.lower(),
                    ).moved(location)
            new_solids.append(new_solid)

        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


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

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

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
            Solid.makeBox(
                length,
                width,
                height,
                center_offset,
                Vector(0, 0, 1),
            ).moved(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


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
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

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
            Solid.makeCone(
                bottom_radius,
                top_radius,
                height,
                center_offset,
                Vector(0, 0, 1),
                arc_size,
            ).moved(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


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

    def __init__(
        self,
        radius: float,
        height: float,
        arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

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
            Solid.makeCylinder(
                radius,
                height,
                center_offset,
                Vector(0, 0, 1),
                arc_size,
            ).moved(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


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
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

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
            Solid.makeSphere(
                radius,
                center_offset,
                (0, 0, 1),
                arc_size1,
                arc_size2,
                arc_size3,
            ).moved(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Torus(Compound):
    """Part Object: Torus

    Create a torus(es) and combine with part.


    Args:
        major_radius (float): torus size
        minor_radius (float): torus size
        major_arc_size (float, optional): angular size or torus. Defaults to 0.
        minor_arc_size (float, optional): angular size or torus. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        major_radius: float,
        minor_radius: float,
        major_arc_size: float = 0,
        minor_arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation

        self.major_radius = major_radius
        self.minor_radius = minor_radius
        self.major_arc_size = major_arc_size
        self.minor_arc_size = minor_arc_size
        self.rotation = rotate
        self.centered = centered
        self.mode = mode

        center_offset = Vector(
            0 if centered[0] else major_radius,
            0 if centered[1] else major_radius,
            0 if centered[2] else minor_radius,
        )
        new_solids = [
            Solid.makeTorus(
                major_radius,
                minor_radius,
                center_offset,
                Vector(0, 0, 1),
                major_arc_size,
                minor_arc_size,
            ).moved(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


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
        context: BuildPart = BuildPart._get_context()
        validate_inputs(self, context)

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
            Solid.makeWedge(dx, dy, dz, xmin, zmin, xmax, zmax).moved(location * rotate)
            for location in LocationList._get_context().locations
        ]
        context._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)
