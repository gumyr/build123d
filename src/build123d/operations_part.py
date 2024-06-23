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
from build123d.build_enums import Mode, Until, Kind, Side
from build123d.build_part import BuildPart
from build123d.geometry import Axis, Plane, Vector, VectorLike
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    Shell,
    Solid,
    Wire,
    Part,
    Sketch,
    ShapeList,
    Vertex,
)

from build123d.build_common import (
    logger,
    WorkplaneList,
    flatten_sequence,
    validate_inputs,
)


def extrude(
    to_extrude: Union[Face, Sketch] = None,
    amount: float = None,
    dir: VectorLike = None,  # pylint: disable=redefined-builtin
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
    # pylint: disable=too-many-locals, too-many-branches
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
        face_planes = []
        for face in to_extrude_faces:
            try:
                plane = Plane(face)
            except ValueError:  # non-planar face
                plane = None
            if plane is not None:
                face_planes.append(plane)

    new_solids: list[Solid] = []

    if dir is not None:
        # Override in the provided direction
        face_planes = [
            Plane(face.center(), face.center_location.x_axis.direction, Vector(dir))
            for face in to_extrude_faces
        ]
    if len(face_planes) != len(to_extrude_faces):
        raise ValueError("dir must be provided when extruding non-planar faces")

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
                if taper == 0:
                    new_solids.append(
                        Solid.extrude(
                            face,
                            direction=plane.z_dir * amount * direction,
                        )
                    )
                else:
                    new_solids.append(
                        Solid.extrude_taper(
                            face,
                            direction=plane.z_dir * amount * direction,
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

    return Part(ShapeList(new_solids).solids())


def loft(
    sections: Union[Face, Sketch, Iterable[Union[Vertex, Face, Sketch]]] = None,
    ruled: bool = False,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """Part Operation: loft

    Loft the pending sketches/faces, across all workplanes, into a solid.

    Args:
        sections (Vertex, Face, Sketch): slices to loft into object. If not provided, pending_faces
            will be used. If vertices are to be used, a vertex can be the first, last, or
            first and last elements.
        ruled (bool, optional): discontiguous layer tangents. Defaults to False.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    context: BuildPart = BuildPart._get_context("loft")

    section_list = flatten_sequence(sections)
    validate_inputs(context, "loft", section_list)

    if all([s is None for s in section_list]):
        if context is None or (context is not None and not context.pending_faces):
            raise ValueError("No sections provided")
        loft_wires = [face.outer_wire() for face in context.pending_faces]
        context.pending_faces = []
        context.pending_face_planes = []
    else:
        if not any(isinstance(s, Vertex) for s in section_list):
            loft_wires = [
                face.outer_wire()
                for section in section_list
                for face in section.faces()
            ]
        elif any(isinstance(s, Vertex) for s in section_list) and any(
            isinstance(s, (Face, Sketch)) for s in section_list
        ):
            if any(isinstance(s, Vertex) for s in section_list[1:-1]):
                raise ValueError(
                    "Vertices must be the first, last, or first and last elements"
                )
            loft_wires = []
            for s in section_list:
                if isinstance(s, Vertex):
                    loft_wires.append(s)
                elif isinstance(s, Face):
                    loft_wires.append(s.outer_wire())
                elif isinstance(s, Sketch):
                    loft_wires.append(s.face().outer_wire())
        elif all(isinstance(s, Vertex) for s in section_list):
            raise ValueError(
                "At least one face/sketch is required if vertices are the first, last, or first and last elements"
            )

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

    return Part(Compound([new_solid]).wrapped)


def make_brake_formed(
    thickness: float,
    station_widths: Union[float, Iterable[float]],
    line: Union[Edge, Wire, Curve] = None,
    side: Side = Side.LEFT,
    kind: Kind = Kind.ARC,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """make_brake_formed

    Create a part typically formed with a sheet metal brake from a single outline.
    The line parameter describes how the material is to be bent. Either a single
    width value or a width value at each vertex or station is provided to control
    the width of the end part.  Note that if multiple values are provided there
    must be one for each vertex and that the resulting part is composed of linear
    segments.

    Args:
        thickness (float): sheet metal thickness
        station_widths (Union[float, Iterable[float]]): width of part at
            each vertex or a single value. Note that this width is perpendicular
            to the provided line/plane.
        line (Union[Edge, Wire, Curve], optional): outline of part. Defaults to None.
        side (Side, optional): offset direction. Defaults to Side.LEFT.
        kind (Kind, optional): offset intersection type. Defaults to Kind.ARC.
        clean (bool, optional): clean the resulting solid. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: invalid line type
        ValueError: not line provided
        ValueError: line not suitable
        ValueError: incorrect # of width values

    Returns:
        Part: sheet metal part
    """
    # pylint: disable=too-many-locals, too-many-branches
    context: BuildPart = BuildPart._get_context("make_brake_formed")
    validate_inputs(context, "make_brake_formed")

    if line is not None:
        if isinstance(line, Curve):
            line = line.wires()[0]
        elif not isinstance(line, (Edge, Wire)):
            raise ValueError("line must be either a Curve, Edge or Wire")
    elif context is not None and not context.pending_edges_as_wire is None:
        line = context.pending_edges_as_wire
    else:
        raise ValueError("A line must be provided")

    # Create the offset
    offset_line = line.offset_2d(distance=thickness, kind=kind, side=side, closed=True)
    offset_vertices = offset_line.vertices()

    try:
        plane = Plane(Face(offset_line))
    except Exception as exc:
        raise ValueError("line not suitable - probably straight") from exc

    # Make edge pairs
    station_edges = ShapeList()
    line_vertices = line.vertices()
    for vertex in line_vertices:
        others = offset_vertices.sort_by_distance(Vector(vertex.X, vertex.Y, vertex.Z))
        for other in others[1:]:
            if abs(Vector(*(vertex - other).to_tuple()).length - thickness) < 1e-2:
                station_edges.append(
                    Edge.make_line(vertex.to_tuple(), other.to_tuple())
                )
                break
    station_edges = station_edges.sort_by(line)

    if isinstance(station_widths, (float, int)):
        station_widths = [station_widths] * len(line_vertices)
    if len(station_widths) != len(line_vertices):
        raise ValueError(
            f"widths must either be a single number or an iterable with "
            f"a length of the # vertices in line ({len(line_vertices)})"
        )
    station_faces = [
        Face.extrude(obj=e, direction=plane.z_dir * w)
        for e, w in zip(station_edges, station_widths)
    ]
    sweep_paths = line.edges().sort_by(line)
    sections = []
    for i in range(len(station_faces) - 1):
        sections.append(
            Solid.sweep_multi(
                [station_faces[i], station_faces[i + 1]], path=sweep_paths[i]
            )
        )
    if len(sections) > 1:
        new_solid = sections.pop().fuse(*sections)
    else:
        new_solid = sections[0]

    if context is not None:
        context._add_to_context(new_solid, clean=clean, mode=mode)
    elif clean:
        new_solid = new_solid.clean()

    return Part(Compound([new_solid]).wrapped)


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

    origin = Vector(origin) if isinstance(origin, Vertex) else Vector(origin)
    x_dir = Vector(x_dir).normalized()
    projection_dir = Vector(projection_dir).normalized()

    # Create a preliminary workplane without x direction set
    workplane_origin = origin + projection_dir * distance
    workplane = Plane(workplane_origin, z_dir=projection_dir)

    # Project a point off the origin to find the projected x direction
    screen = Face.make_rect(1e9, 1e9, plane=workplane)
    x_dir_point_axis = Axis(origin + x_dir, projection_dir)
    projection = screen.find_intersection_points(x_dir_point_axis)
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
    Note that the most common use case is when the axis is in the same plane as the
    face to be revolved but this isn't required.

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

    profile_list = flatten_sequence(profiles)

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

    new_solids = [Solid.revolve(profile, angle, axis) for profile in profile_list]

    new_solid = Compound(new_solids)
    if context is not None:
        context._add_to_context(*new_solids, clean=clean, mode=mode)
    elif clean:
        new_solid = new_solid.clean()

    return Part(new_solid.wrapped)


def section(
    obj: Part = None,
    section_by: Union[Plane, Iterable[Plane]] = Plane.XZ,
    height: float = 0.0,
    clean: bool = True,
    mode: Mode = Mode.PRIVATE,
) -> Sketch:
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
    if obj is None:
        if context is not None and context._obj is not None:
            obj = context.part
        else:
            raise ValueError("obj must be provided")

    new_objects = [obj.intersect(plane) for plane in planes]

    if context is not None:
        context._add_to_context(
            *new_objects, faces_to_pending=False, clean=clean, mode=mode
        )
    else:
        if clean:
            new_objects = [r.clean() for r in new_objects]

    return Sketch(Compound(new_objects).wrapped)


def thicken(
    to_thicken: Union[Face, Sketch] = None,
    amount: float = None,
    normal_override: VectorLike = None,
    both: bool = False,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """Part Operation: thicken

    Create a solid(s) from a potentially non planar face(s) by thickening along the normals.

    Args:
        to_thicken (Union[Face, Sketch], optional): object to thicken. Defaults to None.
        amount (float, optional): distance to extrude, sign controls direction. Defaults to None.
        normal_override (Vector, optional): The normal_override vector can be used to
            indicate which way is 'up', potentially flipping the face normal direction
            such that many faces with different normals all go in the same direction
            (direction need only be +/- 90 degrees from the face normal). Defaults to None.
        both (bool, optional): thicken in both directions. Defaults to False.
        clean (bool, optional): Remove extraneous internal structure. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: No object to extrude
        ValueError: No target object

    Returns:
        Part: extruded object
    """
    context: BuildPart = BuildPart._get_context("thicken")
    validate_inputs(context, "thicken", to_thicken)

    to_thicken_faces: list[Face]

    if to_thicken is None:
        if context is not None and context.pending_faces:
            # Get pending faces and face planes
            to_thicken_faces = context.pending_faces
            context.pending_faces = []
            context.pending_face_planes = []
        else:
            raise ValueError("A face or sketch must be provided")
    else:
        # Get the faces from the face or sketch
        to_thicken_faces = (
            [*to_thicken]
            if isinstance(to_thicken, (tuple, list, filter))
            else to_thicken.faces()
        )

    new_solids: list[Solid] = []

    logger.info("%d face(s) to thicken", len(to_thicken_faces))

    for face in to_thicken_faces:
        normal_override = (
            normal_override if normal_override is not None else face.normal_at()
        )
        for direction in [1, -1] if both else [1]:
            new_solids.append(
                face.thicken(depth=amount, normal_override=normal_override * direction)
            )

    if context is not None:
        context._add_to_context(*new_solids, clean=clean, mode=mode)
    else:
        if len(new_solids) > 1:
            new_solids = [new_solids.pop().fuse(*new_solids)]
        if clean:
            new_solids = [solid.clean() for solid in new_solids]

    return Part(Compound(new_solids).wrapped)
