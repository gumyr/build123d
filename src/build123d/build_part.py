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
from math import radians, tan
from typing import Union
from itertools import product

# from .occ_impl.geom import Vector, Matrix, Plane, Location, BoundBox
# from .occ_impl.shapes import (
#     Shape,
#     Vertex,
#     Edge,
#     Wire,
#     Face,
#     Shell,
#     Solid,
#     Compound,
#     VectorLike,
# )

from cadquery import (
    Edge,
    Face,
    Wire,
    Vector,
    Location,
    Vertex,
    Compound,
    Solid,
    Plane,
)
from cadquery.occ_impl.shapes import VectorLike
import cq_warehouse.extensions

from build123d.build_common import *


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
    def workplane_count(self) -> int:
        """Number of active workplanes"""
        return len(self.workplanes)

    @property
    def pending_faces_count(self) -> int:
        """Number of pending faces"""
        return len(self.pending_faces.values())

    @property
    def pending_edges_count(self) -> int:
        """Number of pending edges"""
        return len(self.pending_edges.values())

    @property
    def pending_location_count(self) -> int:
        """Number of current locations"""
        return len(self.locations)

    def __init__(
        self,
        workplane: Plane = Plane.named("XY"),
        mode: Mode = Mode.ADD,
    ):
        self.part: Compound = None
        self.workplanes: list[Plane] = [workplane]
        self.locations: list[Location] = [Location(workplane.origin)]
        self.pending_faces: dict[int : list[Face]] = {0: []}
        self.pending_edges: dict[int : list[Edge]] = {0: []}
        self.last_faces = []
        self.last_solids = []
        super().__init__(mode)

    def vertices(self, select: Select = Select.ALL) -> VertexList[Vertex]:
        """Return Vertices from Part

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            VertexList[Vertex]: Vertices extracted
        """
        vertex_list = []
        if select == Select.ALL:
            for edge in self.part.Edges():
                vertex_list.extend(edge.Vertices())
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return VertexList(set(vertex_list))

    def edges(self, select: Select = Select.ALL) -> ShapeList[Edge]:
        """Return Edges from Part

        Return either all or the edges created during the last operation.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: Edges extracted
        """
        if select == Select.ALL:
            edge_list = self.part.Edges()
        elif select == Select.LAST:
            edge_list = self.last_edges
        return ShapeList(edge_list)

    def faces(self, select: Select = Select.ALL) -> ShapeList[Face]:
        """Return Faces from Part

        Return either all or the faces created during the last operation.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Face]: Faces extracted
        """
        if select == Select.ALL:
            face_list = self.part.Faces()
        elif select == Select.LAST:
            face_list = self.last_edges
        return ShapeList(face_list)

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

    def _workplane(self, *workplanes: Plane, replace=True):
        """Create Workplane(s)

        Add a sequence of planes as workplanes possibly replacing existing workplanes.

        Args:
            workplanes (Plane): a sequence of planes to add as workplanes
            replace (bool, optional): replace existing workplanes. Defaults to True.
        """
        if replace:
            self.workplanes = []
        for plane in workplanes:
            self.workplanes.append(plane)

    def _add_to_pending(self, *objects: Union[Edge, Face]):
        """Add objects to BuildPart pending lists

        Args:
            objects (Union[Edge, Face]): sequence of objects to add
        """
        for obj in objects:
            for i, workplane in enumerate(self.workplanes):
                for loc in self.locations:
                    localized_obj = workplane.fromLocalCoords(obj.moved(loc))
                    if i in self.pending_faces:
                        if isinstance(obj, Face):
                            self.pending_faces[i].append(localized_obj)
                        else:
                            self.pending_edges[i].append(localized_obj)
                    else:
                        if isinstance(obj, Face):
                            self.pending_faces[i] = [localized_obj]
                        else:
                            self.pending_edges[i] = [localized_obj]

    def _get_and_clear_locations(self) -> list:
        """Return location and planes from current points and workplanes and clear locations."""
        location_planes = []
        for workplane in self.workplanes:
            location_planes.extend(
                [
                    ((Location(workplane) * location), workplane)
                    for location in self.locations
                ]
            )
        self.locations = [Location(Vector())]
        return location_planes

    def _add_to_context(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
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
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Raises:
            ValueError: Nothing to subtract from
            ValueError: Nothing to intersect with
            ValueError: Invalid mode
        """
        if mode != Mode.PRIVATE:
            # Sort the provided objects into edges, faces and solids
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_solids = [obj for obj in objects if isinstance(obj, Solid)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(compound.Faces())
                new_solids.extend(compound.Solids())
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            for compound in filter(lambda o: isinstance(o, Wire), objects):
                new_edges.extend(compound.Edges())

            pre_vertices = set() if self.part is None else set(self.part.Vertices())
            pre_edges = set() if self.part is None else set(self.part.Edges())
            pre_faces = set() if self.part is None else set(self.part.Faces())
            pre_solids = set() if self.part is None else set(self.part.Solids())

            if new_solids:
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
                        raise ValueError("Nothing to subtract from")
                    self.part = self.part.cut(*new_solids).clean()
                elif mode == Mode.INTERSECT:
                    if self.part is None:
                        raise ValueError("Nothing to intersect with")
                    self.part = self.part.intersect(*new_solids).clean()
                elif mode == Mode.REPLACE:
                    self.part = Compound.makeCompound(new_solids).clean()
                else:
                    raise ValueError(f"Invalid mode: {mode}")

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
        return cls._current.get(None)


#
# Operations
#


class ChamferPart(Compound):
    """Part Operation: Chamfer

    Chamfer the given sequence of edges.

    Args:
        edges (Edge): sequence of edges to chamfer
        length1 (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.
    """

    def __init__(self, *edges: Edge, length1: float, length2: float = None):
        new_part = BuildPart._get_context().part.chamfer(length1, length2, list(edges))
        # BuildPart.get_context().part = new_part
        BuildPart._get_context()._add_to_context(new_part, mode=Mode.REPLACE)
        super().__init__(new_part.wrapped)


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
        hole_depth = (
            BuildPart._get_context().part.BoundingBox().DiagonalLength
            if depth is None
            else depth
        )
        location_planes = BuildPart._get_context()._get_and_clear_locations()
        new_solids = [
            Solid.makeCylinder(
                radius, hole_depth, loc.position(), plane.zDir * -1.0
            ).fuse(
                Solid.makeCylinder(
                    counter_bore_radius,
                    counter_bore_depth,
                    loc.position(),
                    plane.zDir * -1.0,
                )
            )
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
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
        hole_depth = (
            BuildPart._get_context().part.BoundingBox().DiagonalLength
            if depth is None
            else depth
        )
        cone_height = counter_sink_radius / tan(radians(counter_sink_angle / 2.0))
        location_planes = BuildPart._get_context()._get_and_clear_locations()
        new_solids = [
            Solid.makeCylinder(
                radius, hole_depth, loc.position(), plane.zDir * -1.0
            ).fuse(
                Solid.makeCone(
                    counter_sink_radius,
                    0.0,
                    cone_height,
                    loc,
                    plane.zDir * -1.0,
                )
            )
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Extrude(Compound):
    """Part Operation: Extrude

    Extrude a sketch/face and combine with part.

    Args:
        until (Union[float, Until, Face]): depth of extrude or extrude limit
        both (bool, optional): extrude in both directions. Defaults to False.
        taper (float, optional): taper during extrusion. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        until: Union[float, Until, Face],
        both: bool = False,
        taper: float = None,
        mode: Mode = Mode.ADD,
    ):
        new_solids: list[Solid] = []
        for plane_index, faces in BuildPart._get_context().pending_faces.items():
            for face in faces:
                new_solids.append(
                    Solid.extrudeLinear(
                        face,
                        BuildPart._get_context().workplanes[plane_index].zDir * until,
                        0,
                    )
                )
                if both:
                    new_solids.append(
                        Solid.extrudeLinear(
                            face,
                            BuildPart._get_context().workplanes[plane_index].zDir
                            * until
                            * -1.0,
                            0,
                        )
                    )

        BuildPart._get_context().pending_faces = {0: []}
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class FilletPart(Compound):
    """Part Operation: Fillet

    Fillet the given sequence of edges.

    Args:
        edges (Edge): sequence of edges to fillet
        radius (float): fillet size - must be less than 1/2 local width
    """

    def __init__(self, *edges: Edge, radius: float):
        new_part = BuildPart._get_context().part.fillet(radius, list(edges))
        # BuildPart.get_context().part = new_part
        BuildPart._get_context()._add_to_context(new_part, mode=Mode.REPLACE)
        super().__init__(new_part.wrapped)


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
        hole_depth = (
            BuildPart._get_context().part.BoundingBox().DiagonalLength
            if depth is None
            else depth
        )
        location_planes = BuildPart._get_context()._get_and_clear_locations()
        new_solids = [
            Solid.makeCylinder(
                radius, hole_depth, loc.position(), plane.zDir * -1.0, 360
            )
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Loft(Solid):
    """Part Operation: Loft

    Loft the pending sketches/faces, across all workplanes, into a solid.

    Args:
        ruled (bool, optional): discontiguous layer tangents. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(self, ruled: bool = False, mode: Mode = Mode.ADD):

        loft_wires = []
        for i in range(len(BuildPart._get_context().workplanes)):
            for face in BuildPart._get_context().pending_faces[i]:
                loft_wires.append(face.outerWire())
        new_solid = Solid.makeLoft(loft_wires, ruled)

        BuildPart._get_context().pending_faces = {0: []}
        BuildPart._get_context()._add_to_context(new_solid, mode=mode)
        super().__init__(new_solid.wrapped)


class Revolve(Compound):
    """Part Operation: Revolve

    Revolve the pending sketches/faces about the given local axis.

    Args:
        revolution_arc (float, optional): angular size of revolution. Defaults to 360.0.
        axis_start (VectorLike, optional): axis start in local coordinates. Defaults to None.
        axis_end (VectorLike, optional): axis end in local coordinates. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        revolution_arc: float = 360.0,
        axis_start: VectorLike = None,
        axis_end: VectorLike = None,
        mode: Mode = Mode.ADD,
    ):
        # Make sure we account for users specifying angles larger than 360 degrees, and
        # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
        angle = revolution_arc % 360.0
        angle = 360.0 if angle == 0 else angle

        new_solids = []
        for i, workplane in enumerate(BuildPart._get_context().workplanes):
            axis = []
            if axis_start is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 0, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_start)))

            if axis_end is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 1, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_end)))

            for face in BuildPart._get_context().pending_faces[i]:
                new_solids.append(Solid.revolve(face, angle, *axis))

        BuildPart._get_context().pending_faces = {0: []}
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Section(Compound):
    """Part Operation: Section

    Slices current part at the given height from current workplane(s).

    Args:
        height (float, optional): workplane offset. Defaults to 0.0.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """

    def __init__(self, height: float = 0.0, mode: Mode = Mode.INTERSECT):
        planes = [
            Face.makePlane(basePnt=plane.origin + plane.zDir * height, dir=plane.zDir)
            for plane in BuildPart._get_context().workplanes
        ]

        BuildPart._get_context()._add_to_context(planes, mode=mode)
        super().__init__(Compound.makeCompound(planes).wrapped)


class Shell(Compound):
    """Part Operation: Shell

    Create a hollow shell from part with provided open faces.

    Args:
        faces (Face): sequence of faces to open
        thickness (float): thickness of shell - positive values shell outwards, negative inwards.
        kind (Kind, optional): edge construction option. Defaults to Kind.ARC.
        mode (Mode, optional): combination mode. Defaults to Mode.REPLACE.
    """

    def __init__(
        self,
        *faces: Face,
        thickness: float,
        kind: Kind = Kind.ARC,
        mode: Mode = Mode.REPLACE,
    ):
        new_part = BuildPart._get_context().part.shell(
            faces, thickness, kind=kind.name.lower()
        )
        BuildPart._get_context()._add_to_context(new_part, mode=mode)
        super().__init__(new_part.wrapped)


class Split(Compound):
    """Part Operation: Split

    Bisect part with plane and keep either top, bottom or both.

    Args:
        bisect_by (Plane, optional): plane to segment part. Defaults to Plane.named("XZ").
        keep (Keep, optional): selector for which segment to keep. Defaults to Keep.TOP.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """

    def __init__(
        self,
        bisect_by: Plane = Plane.named("XZ"),
        keep: Keep = Keep.TOP,
        mode: Mode = Mode.INTERSECT,
    ):
        max_size = BuildPart._get_context().BoundingBox().DiagonalLength

        def build_cutter(keep: Keep) -> Solid:
            cutter_center = (
                Vector(-max_size, -max_size, 0)
                if keep == Keep.TOP
                else Vector(-max_size, -max_size, -2 * max_size)
            )
            return bisect_by.fromLocalCoords(
                Solid.makeBox(2 * max_size, 2 * max_size, 2 * max_size).moved(
                    Location(cutter_center)
                )
            )

        cutters = []
        if keep == Keep.BOTH:
            cutters.append(build_cutter(Keep.TOP))
            cutters.append(build_cutter(Keep.BOTTOM))
        else:
            cutters.append(build_cutter(keep))

        BuildPart._get_context()._add_to_context(*cutters, mode=mode)
        super().__init__(BuildPart._get_context().part.wrapped)


class Sweep(Compound):
    """Part Operation: Sweep

    Sweep pending sketches/faces along path.

    Args:
        path (Union[Edge, Wire]): path to follow
        multisection (bool, optional): sweep multiple on path. Defaults to False.
        make_solid (bool, optional): create solid instead of face. Defaults to True.
        is_frenet (bool, optional): use freenet algorithm. Defaults to False.
        transition (Transition, optional): discontinuity handling option.
            Defaults to Transition.RIGHT.
        normal (VectorLike, optional): fixed normal. Defaults to None.
        binormal (Union[Edge, Wire], optional): guide rotation along path. Defaults to None.
        mode (Mode, optional): combination. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        path: Union[Edge, Wire],
        multisection: bool = False,
        make_solid: bool = True,
        is_frenet: bool = False,
        transition: Transition = Transition.RIGHT,
        normal: VectorLike = None,
        binormal: Union[Edge, Wire] = None,
        mode: Mode = Mode.ADD,
    ):
        path_wire = Wire.assembleEdges([path]) if isinstance(path, Edge) else path
        if binormal is None:
            binormal_mode = Vector(normal)
        elif isinstance(binormal, Edge):
            binormal_mode = Wire.assembleEdges([binormal])
        else:
            binormal_mode = binormal

        new_solids = []
        for i in range(BuildPart._get_context().workplane_count):
            if not multisection:
                for face in BuildPart._get_context().pending_faces[i]:
                    new_solids.append(
                        Solid.sweep(
                            face,
                            path_wire,
                            make_solid,
                            is_frenet,
                            binormal_mode,
                            transition,
                        )
                    )
            else:
                sections = [
                    face.outerWire()
                    for face in BuildPart._get_context().pending_faces[i]
                ]
                new_solids.append(
                    Solid.sweep_multi(
                        sections, path_wire, make_solid, is_frenet, binormal_mode
                    )
                )

        BuildPart._get_context().pending_faces = {0: []}
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Workplanes:
    """Part Operation: Workplanes

    Create workplanes from the given sequence of planes, optionally replacing existing
    workplanes.

    Args:
        planes (Plane): sequence of planes to use as workplanes.
        replace (bool, optional): replace existing workplanes. Defaults to True.
    """

    def __init__(self, *planes: Plane, replace=True):
        BuildPart._get_context()._workplane(*planes, replace=replace)


class WorkplanesFromFaces:
    """Part Operation: Workplanes from Faces

    Create workplanes from the given sequence of faces, optionally replacing existing
    workplanes. The workplane origin is aligned to the center of the face.

    Args:
        faces (Face): sequence of faces to convert to workplanes.
        replace (bool, optional): replace existing workplanes. Defaults to True.
    """

    def __init__(self, *faces: Face, replace=True):
        new_planes = [
            Plane(origin=face.Center(), normal=face.normalAt(face.Center()))
            for face in faces
        ]
        BuildPart._get_context()._workplane(*new_planes, replace=replace)


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
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart._get_context()._get_and_clear_locations()
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
                loc.position() + plane.fromLocalCoords(center_offset),
                plane.zDir,
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
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
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart._get_context()._get_and_clear_locations()
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
                loc.position() + plane.fromLocalCoords(center_offset),
                plane.zDir,
                arc_size,
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
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
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart._get_context()._get_and_clear_locations()
        center_offset = Vector(
            0 if centered[0] else radius,
            0 if centered[1] else radius,
            -height / 2 if centered[2] else 0,
        )
        new_solids = [
            Solid.makeCylinder(
                radius,
                height,
                loc.position() + plane.fromLocalCoords(center_offset),
                plane.zDir,
                arc_size,
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
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
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart._get_context()._get_and_clear_locations()
        center_offset = Vector(
            0 if centered[0] else radius,
            0 if centered[1] else radius,
            0 if centered[2] else radius,
        )
        new_solids = [
            Solid.makeSphere(
                radius,
                loc.position() + plane.fromLocalCoords(center_offset),
                plane.zDir,
                arc_size1,
                arc_size2,
                arc_size3,
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
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
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart._get_context()._get_and_clear_locations()
        center_offset = Vector(
            0 if centered[0] else major_radius,
            0 if centered[1] else major_radius,
            0 if centered[2] else minor_radius,
        )
        new_solids = [
            Solid.makeTorus(
                major_radius,
                minor_radius,
                loc.position() + plane.fromLocalCoords(center_offset),
                plane.zDir,
                major_arc_size,
                minor_arc_size,
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
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
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart._get_context()._get_and_clear_locations()
        new_solids = [
            Solid.makeWedge(
                dx, dy, dz, xmin, zmin, xmax, zmax, loc.position(), plane.zDir
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart._get_context()._add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)
