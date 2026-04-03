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
from typing import cast

from collections.abc import Iterable
from build123d.build_enums import GeomType, Mode, Until, Kind, Side
from build123d.build_part import BuildPart
from build123d.geometry import Axis, Plane, Vector, VectorLike
from build123d.topology import (
    Compound,
    Curve,
    DraftAngleError,
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


def draft(
    faces: Face | Iterable[Face],
    neutral_plane: Plane,
    angle: float,
) -> Part:
    """Part Operation: draft

    Apply a draft angle to the given faces of the part

    Args:
        faces: Faces to which the draft should be applied.
        neutral_plane: Plane defining the neutral direction and position.
        angle: Draft angle in degrees.
    """
    context: BuildPart | None = BuildPart._get_context("draft")

    face_list: ShapeList[Face] = flatten_sequence(faces)
    assert all(isinstance(f, Face) for f in face_list), "all faces must be of type Face"
    validate_inputs(context, "draft", face_list)

    valid_geom_types = {GeomType.PLANE, GeomType.CYLINDER, GeomType.CONE}
    unsupported = [f for f in face_list if f.geom_type not in valid_geom_types]
    if unsupported:
        raise ValueError(
            f"Draft not supported on face(s) with geometry: "
            f"{', '.join(set(f.geom_type.name for f in unsupported))}"
        )

    # Check that all the faces are associated with the same Solid
    topo_parents = set(f.topo_parent for f in face_list if f.topo_parent is not None)
    if len(topo_parents) != 1:
        raise ValueError("All faces must share the same topological parent (a Solid)")
    parent_solids = next(iter(topo_parents)).solids()
    if len(parent_solids) != 1:
        raise ValueError("Topological parent must be a single Solid")

    # Create the drafted solid
    try:
        new_solid = parent_solids[0].draft(face_list, neutral_plane, angle)
    except DraftAngleError as err:
        raise DraftAngleError(
            f"Draft operation failed. "
            f"Use `err.face` and `err.problematic_shape` for more information.",
            face=err.face,
            problematic_shape=err.problematic_shape,
        ) from err

    if context is not None:
        context._add_to_context(new_solid, clean=False, mode=Mode.REPLACE)

    return Part(Compound([new_solid]).wrapped)


def extrude(
    to_extrude: Face | Sketch | None = None,
    amount: float | None = None,
    dir: VectorLike | None = None,  # pylint: disable=redefined-builtin
    until: Until | None = None,
    target: Compound | Solid | None = None,
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
    context: BuildPart | None = BuildPart._get_context("extrude")
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

    logger.info(
        "%d face(s) to extrude on %d face plane(s)",
        len(to_extrude_faces),
        len(face_planes),
    )

    for face, plane in zip(to_extrude_faces, face_planes):
        for direction in [1, -1] if both else [1]:
            if amount is not None:
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
                if until is None:
                    raise ValueError("Either amount or until must be provided")
                if target is None:
                    if context is None:
                        raise ValueError("A target object must be provided")
                    target_object = context.part
                else:
                    target_object = target
                if target_object is None:
                    raise ValueError("No target object provided")

                new_solids.append(
                    Solid.extrude_until(
                        face,
                        target=target_object,
                        direction=plane.z_dir * direction,
                        until=until,
                    )
                )

    if both and len(new_solids) > 1:
        fused_solids = new_solids.pop().fuse(*new_solids)
        new_solids = fused_solids if isinstance(fused_solids, list) else [fused_solids]
    if clean:
        new_solids = [solid.clean() for solid in new_solids]

    if context is not None:
        context._add_to_context(*new_solids, clean=clean, mode=mode)

    return Part(ShapeList(new_solids).solids())


def loft(
    sections: Face | Sketch | Iterable[Vertex | Face | Sketch] | None = None,
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

    def normalize_list_of_lists(lst):
        lengths = {len(sub) for sub in lst}
        if lengths <= {0}:
            return []
        if lengths == {1}:
            return [sub[0] for sub in lst]
        if len(lengths) > 1:
            raise ValueError("The number of holes in the sections must be the same")
        if max(lengths) > 1:
            raise ValueError(
                f"loft supports a maximum of 1 hole per section but one or more section "
                f"has {max(lengths)} hole - loft the perimeter and holes separately and "
                f"subtract the holes"
            )

    context: BuildPart | None = BuildPart._get_context("loft")

    section_list = flatten_sequence(sections)
    validate_inputs(context, "loft", section_list)

    # If no explicit sections provided, use pending_faces from context
    if all(s is None for s in section_list):
        if context is None or not context.pending_faces:
            raise ValueError("No sections provided")
        input_sections = context.pending_faces
        context.pending_faces = []
        context.pending_face_planes = []
    else:
        input_sections = section_list

    # Validate Vertex placement
    if any(isinstance(s, Vertex) for s in input_sections):
        if not isinstance(input_sections[0], Vertex) and not isinstance(
            input_sections[-1], Vertex
        ):
            raise ValueError(
                "Vertices must be the first, last, or first and last elements"
            )
        if any(isinstance(s, Vertex) for s in input_sections[1:-1]):
            raise ValueError(
                "Vertices must be the first, last, or first and last elements"
            )

    # Normalize all input into loft_sections: each is either a Vertex or a Wire
    loft_sections = []
    hole_candidates = []
    for s in input_sections:
        if isinstance(s, Vertex):
            loft_sections.append(s)
        else:
            for face in s.faces():
                loft_sections.append(face.outer_wire())
                hole_candidates.append(face.inner_wires())

    holes = normalize_list_of_lists(hole_candidates)

    # Perform lofts
    new_solid = Solid.make_loft(loft_sections, ruled)
    if holes:
        # Since the holes are interior a Solid will be generated here
        new_solid = cast(Solid, new_solid.cut(Solid.make_loft(holes, ruled)))

    # Try to recover an invalid loft - untestable code
    if not new_solid.is_valid:
        try:
            recovery_faces = new_solid.faces() + [
                s for s in loft_sections if isinstance(s, Face)
            ]
            new_solid = Solid(Shell(recovery_faces))
            if clean:
                new_solid = new_solid.clean()
            if not new_solid.is_valid:
                raise ValueError("Recovery failed")
        except Exception as e:
            raise RuntimeError("Failed to create valid loft") from e

    if context is not None:
        context._add_to_context(new_solid, clean=clean, mode=mode)
    elif clean:
        new_solid = new_solid.clean()

    return Part(Compound([new_solid]).wrapped)


def make_brake_formed(
    thickness: float,
    station_widths: float | Iterable[float],
    line: Edge | Wire | Curve | None = None,
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
    context: BuildPart | None = BuildPart._get_context("make_brake_formed")
    validate_inputs(context, "make_brake_formed")

    if line is not None:
        if isinstance(line, Curve):
            line = line.wires()[0]
        elif not isinstance(line, (Edge, Wire)):
            raise ValueError("line must be either a Curve, Edge or Wire")
    elif context is not None and context.pending_edges_as_wire is not None:
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
    station_edges: ShapeList[Edge] = ShapeList()
    line_vertices = line.vertices()

    if isinstance(station_widths, (float, int)):
        station_widths_list = [station_widths] * len(line_vertices)
    elif isinstance(station_widths, Iterable):
        station_widths_list = list(station_widths)
    else:
        raise TypeError("station_widths must be either a single number or an iterable")

    for vertex in line_vertices:
        others = offset_vertices.sort_by_distance(Vector(vertex))
        for other in others[1:]:
            if abs(Vector((vertex - other)).length - thickness) < 1e-2:
                station_edges.append(Edge.make_line(vertex, other))
                break
    station_edges = station_edges.sort_by(line)

    if len(station_widths_list) != len(line_vertices):
        raise ValueError(
            f"widths must either be a single number or an iterable with "
            f"a length of the # vertices in line ({len(line_vertices)})"
        )
    station_faces = [
        Face.extrude(obj=e, direction=plane.z_dir * w)
        for e, w in zip(station_edges, station_widths_list)
    ]
    sweep_paths = line.edges().sort_by(line)
    sections: list[Solid] = []
    for i in range(len(station_faces) - 1):
        sections.append(
            Solid.sweep_multi(
                [station_faces[i], station_faces[i + 1]], path=sweep_paths[i]
            )
        )
    if len(sections) > 1:
        new_solid = cast(Part, Part.fuse(*sections))
    else:
        new_solid = sections[0]

    if context is not None:
        context._add_to_context(new_solid, clean=clean, mode=mode)
        context.pending_edges = ShapeList()
    elif clean:
        new_solid = new_solid.clean()

    return Part(Compound([new_solid]).wrapped)


def project_workplane(
    origin: VectorLike | Vertex,
    x_dir: VectorLike | Vertex,
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
    context: BuildPart | None = BuildPart._get_context("project_workplane")

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
    profiles: Face | Iterable[Face] | None = None,
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
    context: BuildPart | None = BuildPart._get_context("revolve")

    profile_list = flatten_sequence(profiles)

    validate_inputs(context, "revolve", profile_list)

    # Make sure we account for users specifying angles larger than 360 degrees, and
    # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
    sign = 1 if revolution_arc >= 0 else -1
    angle = revolution_arc % (sign * 360.0)
    angle = sign * 360.0 if angle == 0 else angle

    if all([s is None for s in profile_list]):
        if context is None or (context is not None and not context.pending_faces):
            raise ValueError("No profiles provided")
        profile_faces = context.pending_faces
        context.pending_faces = []
        context.pending_face_planes = []
    else:
        profile_faces = profile_list.faces()

    new_solids = [Solid.revolve(profile, angle, axis) for profile in profile_faces]

    new_solid = Compound(new_solids)
    if context is not None:
        context._add_to_context(*new_solids, clean=clean, mode=mode)
    elif clean:
        new_solid = new_solid.clean()

    return Part(new_solid.wrapped)


def section(
    obj: Part | None = None,
    section_by: Plane | Iterable[Plane] = Plane.XZ,
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
    context: BuildPart | None = BuildPart._get_context("section")
    validate_inputs(context, "section", None)

    if obj is not None:
        to_section = obj
    elif context is not None and context.part is not None:
        to_section = context.part
    else:
        raise ValueError("No object to section")

    bbox = to_section.bounding_box(optimal=False)
    max_size = max(abs(v) for v in list(bbox.min) + list(bbox.max)) + bbox.diagonal

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

    new_objects: list[Face | Shell] = []
    for plane in planes:
        intersection = to_section.intersect(plane)
        if isinstance(intersection, ShapeList):
            new_objects.extend(intersection)
        elif intersection is not None:
            new_objects.append(intersection)

    if context is not None:
        context._add_to_context(
            *new_objects, faces_to_pending=False, clean=clean, mode=mode
        )
    else:
        if clean:
            new_objects = [r.clean() for r in new_objects]

    return Sketch(Compound(new_objects).wrapped)


def thicken(
    to_thicken: Face | Sketch | None = None,
    amount: float | None = None,
    normal_override: VectorLike | None = None,
    both: bool = False,
    clean: bool = True,
    mode: Mode = Mode.ADD,
) -> Part:
    """Part Operation: thicken

    Create a solid(s) from a potentially non planar face(s) by thickening along the normals.

    Args:
        to_thicken (Union[Face, Sketch], optional): object to thicken. Defaults to None.
        amount (float): distance to extrude, sign controls direction.
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
    context: BuildPart | None = BuildPart._get_context("thicken")
    validate_inputs(context, "thicken", to_thicken)

    to_thicken_faces: list[Face]

    if amount is None:
        raise ValueError("An amount must be provided")

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
        face_normal = (
            normal_override if normal_override is not None else face.normal_at()
        )
        for direction in [1, -1] if both else [1]:
            new_solids.append(
                Solid.thicken(
                    face, depth=amount, normal_override=Vector(face_normal) * direction
                )
            )

    if context is not None:
        context._add_to_context(*new_solids, clean=clean, mode=mode)
    else:
        if len(new_solids) > 1:
            new_solids = [cast(Part, Part.fuse(*new_solids))]
        if clean:
            new_solids = [solid.clean() for solid in new_solids]

    return Part(Compound(new_solids).wrapped)
