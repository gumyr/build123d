"""
Part Operations

name: operations_part.py
by:   Gumyr
date: March 17th 2023

desc:
    This python module contains operations (functions) that work on Parts.

license:

    Copyright 2023 Gumyr

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
from typing import Union, Iterable
from build123d.build_enums import Mode, Until, Transition
from build123d.build_part import BuildPart
from build123d.geometry import Axis, Plane, Vector, VectorLike
from build123d.topology import (
    Compound,
    Edge,
    Face,
    Shell,
    Solid,
    Wire,
    Part,
    Sketch,
    Vertex,
)

from build123d.build_common import logger, WorkplaneList, validate_inputs


def extrude(
    to_extrude: Union[Face, Sketch] = None,
    amount: float = None,
    dir: VectorLike = None,
    until: Until = None,
    target: Union[Compound, Solid] = None,
    both: bool = False,
    taper: float = 0.0,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """Part Operation: extrude

    Extrude a sketch or face by an amount or until another object.

    Args:
        to_extrude (Union[Face, Sketch], optional): object to extrude. Defaults to None.
        amount (float, optional): distance to extrude, sign controls direction. Defaults to None.
        dir (VectorLike, optional): direction. Defaults to None.
        until (Until, optional): extrude limit. Defaults to None.
        target (Shape, optional): extrude until target. Defaults to None.
        both (bool, optional): extrude in both directions. Defaults to False.
        taper (float, optional): taper angle. Defaults to 0.0.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: No object to extrude
        ValueError: No target object

    Returns:
        Part: extruded object
    """
    context: BuildPart = BuildPart._get_context("extrude")
    validate_inputs(context, "extrude", to_extrude)

    to_extrude_faces: list[Face]

    if to_extrude is None:
        if context is not None and context.pending_faces:
            # Get pending faces and face planes
            to_extrude_faces = context.pending_faces
            face_planes = context.pending_face_planes
            context.pending_faces = []
            context.pending_face_planes = []
        else:
            raise ValueError("A face or sketch must be provided")
    else:
        # Get the faces from the face or sketch
        to_extrude_faces = (
            [*to_extrude]
            if isinstance(to_extrude, (tuple, list, filter))
            else to_extrude.faces()
        )
        face_planes = [Plane(face) for face in to_extrude_faces]

    new_solids: list[Solid] = []

    if dir is not None:
        # Override in the provided direction
        face_planes = [
            Plane(face.center(), face.center_location.x_axis.direction, Vector(dir))
            for face in to_extrude_faces
        ]

    if until is not None:
        if target is None and context is None:
            raise ValueError("A target object must be provided")
        if target is None:
            target = context.part

    logger.info(
        "%d face(s) to extrude on %d face plane(s)",
        len(to_extrude_faces),
        len(face_planes),
    )

    for face, plane in zip(to_extrude_faces, face_planes):
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
                        target_object=target,
                        direction=plane.z_dir * direction,
                        until=until,
                    )
                )

    if context is not None:
        context._add_to_context(*new_solids, clean=clean, mode=mode)
    else:
        if len(new_solids) > 1:
            new_solids = [new_solids.pop().fuse(*new_solids)]
        if clean:
            new_solids = [solid.clean() for solid in new_solids]

    return Part(Compound.make_compound(new_solids).wrapped)


def loft(
    sections: Union[Face, Iterable[Face]] = None,
    ruled: bool = False,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """Part Operation: loft

    Loft the pending sketches/faces, across all workplanes, into a solid.

    Args:
        sections (Face): slices to loft into object. If not provided, pending_faces
            will be used.
        ruled (bool, optional): discontiguous layer tangents. Defaults to False.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildPart = BuildPart._get_context("loft")

    section_list = (
        [*sections] if isinstance(sections, (list, tuple, filter)) else [sections]
    )
    validate_inputs(context, "loft", section_list)

    if all([s is None for s in section_list]):
        if context is None or (context is not None and not context.pending_faces):
            raise ValueError("No sections provided")
        loft_wires = [face.outer_wire() for face in context.pending_faces]
        context.pending_faces = []
        context.pending_face_planes = []
    else:
        loft_wires = [
            face.outer_wire() for section in section_list for face in section.faces()
        ]
    new_solid = Solid.make_loft(loft_wires, ruled)

    # Try to recover an invalid loft
    if not new_solid.is_valid():
        new_solid = Solid.make_solid(Shell.make_shell(new_solid.faces() + section_list))
        if clean:
            new_solid = new_solid.clean()
        if not new_solid.is_valid():
            raise RuntimeError("Failed to create valid loft")

    if context is not None:
        context._add_to_context(new_solid, clean=clean, mode=mode)
    elif clean:
        new_solid = new_solid.clean()

    return Part(Compound.make_compound([new_solid]).wrapped)


def project_workplane(
    origin: Union[VectorLike, Vertex],
    x_dir: Union[VectorLike, Vertex],
    projection_dir: VectorLike,
    distance: float,
) -> Plane:
    """Part Operation: project_workplane

    Return a plane to be used as a BuildSketch or BuildLine workplane
    with a known origin and x direction. The plane's origin will be
    the projection of the provided origin (in 3D space). The plane's
    x direction will be the projection of the provided x_dir (in 3D space).

    Args:
        origin (Union[VectorLike, Vertex]): origin in 3D space
        x_dir (Union[VectorLike, Vertex]): x direction in 3D space
        projection_dir (VectorLike): projection direction
        distance (float): distance from origin to workplane

    Raises:
        RuntimeError: Not suitable for BuildLine or BuildSketch
        ValueError: x_dir perpendicular to projection_dir

    Returns:
        Plane: workplane aligned for projection
    """
    context: BuildPart = BuildPart._get_context("project_workplane")

    if context is not None and not isinstance(context, BuildPart):
        raise RuntimeError(
            "projection_workplane can only be used from a BuildPart context or algebra"
        )

    origin = origin.to_vector() if isinstance(origin, Vertex) else Vector(origin)
    x_dir = (
        x_dir.to_vector().normalized()
        if isinstance(x_dir, Vertex)
        else Vector(x_dir).normalized()
    )
    projection_dir = Vector(projection_dir).normalized()

    # Create a preliminary workplane without x direction set
    workplane_origin = origin + projection_dir * distance
    workplane = Plane(workplane_origin, z_dir=projection_dir)

    # Project a point off the origin to find the projected x direction
    screen = Face.make_rect(1e9, 1e9, plane=workplane)
    x_dir_point_axis = Axis(origin + x_dir, projection_dir)
    projection = screen.find_intersection(x_dir_point_axis)
    if not projection:
        raise ValueError("x_dir perpendicular to projection_dir")

    # Set the workplane's x direction
    workplane_x_dir = projection[0][0] - workplane_origin
    workplane.x_dir = workplane_x_dir
    workplane._calc_transforms()

    return workplane


def revolve(
    profiles: Union[Face, Iterable[Face]] = None,
    axis: Axis = Axis.Z,
    revolution_arc: float = 360.0,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """Part Operation: Revolve

    Revolve the profile or pending sketches/face about the given axis.

    Args:
        profiles (Face, optional): 2D profile(s) to revolve.
        axis (Axis, optional): axis of rotation. Defaults to Axis.Z.
        revolution_arc (float, optional): angular size of revolution. Defaults to 360.0.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Invalid axis of revolution
    """
    context: BuildPart = BuildPart._get_context("revolve")

    profile_list = (
        [*profiles] if isinstance(profiles, (list, tuple, filter)) else [profiles]
    )
    validate_inputs(context, "revolve", profile_list)

    # Make sure we account for users specifying angles larger than 360 degrees, and
    # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
    angle = revolution_arc % 360.0
    angle = 360.0 if angle == 0 else angle

    if all([s is None for s in profile_list]):
        if context is None or (context is not None and not context.pending_faces):
            raise ValueError("No profiles provided")
        profile_list = context.pending_faces
        context.pending_faces = []
        context.pending_face_planes = []
    else:
        p_list = []
        for profile in profile_list:
            p_list.extend(profile.faces())
        profile_list = p_list

    for profile in profile_list:
        # axis origin must be on the same plane as profile
        face_plane = Plane(profile)
        if not face_plane.contains(axis.position):
            raise ValueError(
                "axis origin must be on the same plane as the face to revolve"
            )
        if not face_plane.contains(axis):
            raise ValueError("axis must be in the same plane as the face to revolve")

        new_solid = Solid.revolve(profile, angle, axis)

    if context is not None:
        context._add_to_context(new_solid, clean=clean, mode=mode)
    elif clean:
        new_solid = new_solid.clean()

    return Part(Compound.make_compound([new_solid]).wrapped)


def section(
    obj: Part = None,
    section_by: Union[Plane, Iterable[Plane]] = Plane.XZ,
    height: float = 0.0,
    clean: bool = True,
    mode: Mode = Mode.INTERSECT,
) -> Part:
    """Part Operation: section

    Slices current part at the given height by section_by or current workplane(s).

    Args:
        obj (Part, optional): object to section. Defaults to None.
        section_by (Plane, optional): plane(s) to section object.
            Defaults to None.
        height (float, optional): workplane offset. Defaults to 0.0.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """
    context: BuildPart = BuildPart._get_context("section")
    validate_inputs(context, "section", None)

    if context is not None and obj is None:
        max_size = context.part.bounding_box().diagonal
    else:
        max_size = obj.bounding_box().diagonal

    if section_by is not None:
        section_planes = (
            section_by if isinstance(section_by, Iterable) else [section_by]
        )
    elif context is not None:
        section_planes = WorkplaneList._get_context().workplanes
    else:
        raise ValueError("Plane(s) must be provide to section by")

    planes = [
        Face.make_rect(
            2 * max_size,
            2 * max_size,
            Plane(origin=plane.origin + plane.z_dir * height, z_dir=plane.z_dir),
        )
        for plane in section_planes
    ]

    if context is not None:
        context._add_to_context(*planes, faces_to_pending=False, clean=clean, mode=mode)
        result = planes
    else:
        result = [obj.intersect(plane) for plane in planes]
        if clean:
            result = [r.clean() for r in result]

    return Part(Compound.make_compound(result).wrapped)


#:TypeVar("SweepType"): Type of objects which can be swept
SweepType = Union[Edge, Wire, Face, Solid]


def sweep(
    sections: Union[SweepType, Iterable[SweepType]] = None,
    path: Union[Edge, Wire] = None,
    multisection: bool = False,
    is_frenet: bool = False,
    transition: Transition = Transition.TRANSFORMED,
    normal: VectorLike = None,
    binormal: Union[Edge, Wire] = None,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """Part Operation: sweep

    Sweep pending sketches/faces along path.

    Args:
        sections (Union[Face, Compound]): cross sections to sweep into object
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
    context: BuildPart = BuildPart._get_context("sweep")

    if path is None:
        path_wire = context.pending_edges_as_wire
        context.pending_edges = []
    else:
        path_wire = Wire.make_wire([path]) if isinstance(path, Edge) else path

    section_list = (
        [*sections] if isinstance(sections, (list, tuple, filter)) else [sections]
    )
    validate_inputs(context, "sweep", section_list)

    if all([s is None for s in section_list]):
        if context is None or (context is not None and not context.pending_faces):
            raise ValueError("No sections provided")
        section_list = context.pending_faces
        context.pending_faces = []
        context.pending_face_planes = []
    else:
        section_list = [face for section in sections for face in section.faces()]

    if binormal is None and normal is not None:
        binormal_mode = Vector(normal)
    elif isinstance(binormal, Edge):
        binormal_mode = Wire.make_wire([binormal])
    else:
        binormal_mode = binormal

    new_solids = []
    if multisection:
        sections = [section.outer_wire() for section in section_list]
        new_solid = Solid.sweep_multi(
            sections, path_wire, True, is_frenet, binormal_mode
        )
    else:
        for sec in section_list:
            new_solid = Solid.sweep(
                section=sec,
                path=path_wire,
                make_solid=True,
                is_frenet=is_frenet,
                mode=binormal_mode,
                transition=transition,
            )
    new_solids.append(new_solid)

    if context is not None:
        context._add_to_context(*new_solids, clean=clean, mode=mode)
    elif clean:
        new_solids = [solid.clean() for solid in new_solids]

    return Part(Compound.make_compound(new_solids).wrapped)
