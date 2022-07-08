"""
TODO:
- add Shell, TwistExtrude, ProjectText, Split, Hole(s),
- how about translate & rotate?
"""
from math import pi, sin, cos, radians, sqrt
from typing import Union, Iterable, Callable
from enum import Enum, auto
import cadquery as cq
from cadquery import (
    Edge,
    Face,
    Wire,
    Vector,
    Shape,
    Location,
    Vertex,
    Compound,
    Solid,
    Plane,
)
from cadquery.occ_impl.shapes import VectorLike, Real
import cq_warehouse.extensions
from build123d_common import *


class BuildPart:
    @property
    def workplane_count(self) -> int:
        return len(self.workplanes)

    @property
    def pending_faces_count(self) -> int:
        return len(self.pending_faces.values())

    @property
    def pending_edges_count(self) -> int:
        return len(self.pending_edges.values())

    @property
    def pending_solids_count(self) -> int:
        return len(self.pending_solids.values())

    @property
    def pending_location_count(self) -> int:
        return len(self.locations.values())

    def __init__(
        self,
        mode: Mode = Mode.ADDITION,
        workplane: Plane = Plane.named("XY"),
    ):
        self.part: Compound = None
        self.workplanes: list[Plane] = [workplane]
        self.pending_faces: dict[int : list[Face]] = {0: []}
        self.pending_edges: dict[int : list[Edge]] = {0: []}
        self.pending_solids: dict[int : list[Solid]] = {0: []}
        self.locations: dict[int : list[Location]] = {0: []}
        self.last_operation: dict[CqObject : list[Shape]] = {}
        self.mode = mode
        self.last_vertices = []
        self.last_edges = []
        self.last_faces = []
        self.last_solids = []

    def __enter__(self):
        context_stack.append(self)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def workplane(self, workplane: Plane = Plane.named("XY"), replace=True):
        if replace:
            self.workplanes = [workplane]
        else:
            self.workplanes.append(workplane)
            self.locations[len(self.workplanes) - 1] = [Location()]
        return workplane

    def faces_to_workplanes(self, *faces: Face, replace=False):
        new_planes = []
        for face in faces:
            new_plane = Plane(origin=face.Center(), normal=face.normalAt(face.Center()))
            new_planes.append(new_plane)
            self.workplane(new_plane, replace)
        return new_planes[0] if len(new_planes) == 1 else new_planes

    def vertices(self, select: Select = Select.ALL) -> list[Vertex]:
        vertex_list = []
        if select == Select.ALL:
            for e in self.part.Edges():
                vertex_list.extend(e.Vertices())
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return list(set(vertex_list))

    def edges(self, select: Select = Select.ALL) -> list[Edge]:
        if select == Select.ALL:
            edge_list = self.part.Edges()
        elif select == Select.LAST:
            edge_list = self.last_edges
        return edge_list

    def faces(self, select: Select = Select.ALL) -> list[Face]:
        if select == Select.ALL:
            face_list = self.part.Faces()
        elif select == Select.LAST:
            face_list = self.last_edges
        return face_list

    def solids(self, select: Select = Select.ALL) -> list[Solid]:
        if select == Select.ALL:
            solid_list = self.part.Solids()
        elif select == Select.LAST:
            solid_list = self.last_solids
        return solid_list

    @staticmethod
    def get_context() -> "BuildPart":
        return context_stack[-1]

    def add_to_pending(self, *objects: Union[Edge, Face]):
        for obj in objects:
            for i, workplane in enumerate(self.workplanes):
                # If no locations have been defined, add one to the workplane center
                if not self.locations[i]:
                    self.locations[i].append(Location(Vector()))
                for loc in self.locations[i]:
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

    def add_to_context(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        mode: Mode = Mode.ADDITION,
    ):
        if context_stack and mode != Mode.PRIVATE:
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
                if mode == Mode.ADDITION:
                    if self.part is None:
                        if len(new_solids) == 1:
                            self.part = new_solids[0]
                        else:
                            self.part = new_solids.pop().fuse(*new_solids)
                    else:
                        self.part = self.part.fuse(*new_solids).clean()
                elif mode == Mode.SUBTRACTION:
                    if self.part is None:
                        raise ValueError("Nothing to subtract from")
                    self.part = self.part.cut(*new_solids).clean()
                elif mode == Mode.INTERSECTION:
                    if self.part is None:
                        raise ValueError("Nothing to intersect with")
                    self.part = self.part.intersect(*new_solids).clean()
                elif mode == Mode.CONSTRUCTION:
                    pass
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

            self.add_to_pending(*new_edges)
            self.add_to_pending(*new_faces)


class AddPart(Compound):
    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        mode: Mode = Mode.ADDITION,
    ):
        new_faces = [obj for obj in objects if isinstance(obj, Face)]
        new_solids = [obj for obj in objects if isinstance(obj, Solid)]
        for compound in filter(lambda o: isinstance(o, Compound), objects):
            new_faces.extend(compound.Faces())
            new_solids.extend(compound.Solids())
        new_edges = [obj for obj in objects if isinstance(obj, Edge)]
        for compound in filter(lambda o: isinstance(o, Wire), objects):
            new_edges.extend(compound.Edges())

        # Add to pending faces and edges
        BuildPart.get_context().add_to_pending(new_faces)
        BuildPart.get_context().add_to_pending(new_edges)

        # Locate the solids to the predefined positions
        locations = [
            location for location in BuildPart.get_context().locations.values()
        ]
        # If no locations have been specified, use the origin
        if not locations:
            locations = [Location(Vector())]

        located_solids = [
            solid.moved(location) for solid in new_solids for location in locations
        ]
        BuildPart.get_context().add_to_context(*located_solids, mode=mode)
        super().__init__(Compound.makeCompound(located_solids).wrapped)


class Extrude(Compound):
    def __init__(
        self,
        until: Union[float, Until, Face],
        both: bool = False,
        taper: float = None,
        mode: Mode = Mode.ADDITION,
    ):

        new_solids: list[Solid] = []
        for plane_index, faces in BuildPart.get_context().pending_faces.items():
            for face in faces:
                new_solids.append(
                    Solid.extrudeLinear(
                        face,
                        BuildPart.get_context().workplanes[plane_index].zDir * until,
                        0,
                    )
                )
                if both:
                    new_solids.append(
                        Solid.extrudeLinear(
                            face,
                            BuildPart.get_context().workplanes[plane_index].zDir
                            * until
                            * -1.0,
                            0,
                        )
                    )

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Revolve(Compound):
    def __init__(
        self,
        angle_degrees: float = 360.0,
        axis_start: VectorLike = None,
        axis_end: VectorLike = None,
        mode: Mode = Mode.ADDITION,
    ):
        # Make sure we account for users specifying angles larger than 360 degrees, and
        # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
        angle = angle_degrees % 360.0
        angle = 360.0 if angle == 0 else angle

        new_solids = []
        for i, workplane in enumerate(BuildPart.get_context().workplanes):
            axis = []
            if axis_start is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 0, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_start)))

            if axis_end is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 1, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_end)))
            print(f"Revolve: {axis=}")

            for face in BuildPart.get_context().pending_faces[i]:
                new_solids.append(Solid.revolve(face, angle, *axis))

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Loft(Solid):
    def __init__(self, ruled: bool = False, mode: Mode = Mode.ADDITION):

        loft_wires = []
        for i in range(len(BuildPart.get_context().workplanes)):
            for face in BuildPart.get_context().pending_faces[i]:
                loft_wires.append(face.outerWire())
        new_solid = Solid.makeLoft(loft_wires, ruled)

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(new_solid, mode=mode)
        super().__init__(new_solid.wrapped)


class Sweep(Compound):
    def __init__(
        self,
        path: Union[Edge, Wire],
        multisection: bool = False,
        make_solid: bool = True,
        is_frenet: bool = False,
        transition: Transition = Transition.RIGHT,
        normal: VectorLike = None,
        binormal: Union[Edge, Wire] = None,
        mode: Mode = Mode.ADDITION,
    ):

        path_wire = Wire.assembleEdges([path]) if isinstance(path, Edge) else path
        if binormal is None:
            binormal_mode = Vector(normal)
        elif isinstance(binormal, Edge):
            binormal_mode = Wire.assembleEdges([binormal])
        else:
            binormal_mode = binormal

        new_solids = []
        for i, workplane in enumerate(BuildPart.get_context().workplanes):
            if not multisection:
                for face in BuildPart.get_context().pending_faces[i]:
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
                        for face in BuildPart.get_context().pending_faces[i]
                    ]
                    new_solids.append(
                        Solid.sweep_multi(
                            sections, path_wire, make_solid, is_frenet, binormal_mode
                        )
                    )

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class FilletPart(Compound):
    def __init__(self, *edges: Edge, radius: float):
        new_part = BuildPart.get_context().part.fillet(radius, list(edges))
        BuildPart.get_context().part = new_part
        super().__init__(new_part.wrapped)


class ChamferPart(Compound):
    def __init__(self, *edges: Edge, length1: float, length2: float = None):
        new_part = BuildPart.get_context().part.chamfer(length1, length2, list(edges))
        BuildPart.get_context().part = new_part
        super().__init__(new_part.wrapped)


class PushPointsPart:
    def __init__(self, *pts: Union[VectorLike, Location]):
        new_locations = [
            Location(Vector(pt)) if not isinstance(pt, Location) else pt for pt in pts
        ]
        for i in range(len(BuildPart.get_context().workplanes)):
            BuildPart.get_context().locations[i].extend(new_locations)
            print(f"{len(BuildPart.get_context().locations[i])=}")


class Box(Compound):
    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        mode: Mode = Mode.ADDITION,
    ):
        new_solids = []
        for i, workplane in enumerate(len(BuildPart.get_context().workplanes)):
            for location in BuildPart.get_context().locations[i]:
                new_solids.append(
                    Solid.makeBox(
                        length, width, height, location.position(), workplane.zDir
                    )
                )

        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Cone(Compound):
    def __init__(
        self,
        radius1: float,
        radius2: float,
        height: float,
        angle: float = 360,
        mode: Mode = Mode.ADDITION,
    ):

        new_solids = []
        for i, workplane in enumerate(len(BuildPart.get_context().workplanes)):
            for location in BuildPart.get_context().locations[i]:
                new_solids.append(
                    Solid.makeCone(
                        radius1,
                        radius2,
                        height,
                        location.position(),
                        workplane.zDir,
                        angle,
                    )
                )

        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Cylinder(Compound):
    def __init__(
        self,
        radius: float,
        height: float,
        angle: float = 360,
        mode: Mode = Mode.ADDITION,
    ):

        new_solids = []
        for i, workplane in enumerate(len(BuildPart.get_context().workplanes)):
            for location in BuildPart.get_context().locations[i]:
                new_solids.append(
                    Solid.makeCylinder(
                        radius, height, location.position(), workplane.zDir, angle
                    )
                )

        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Sphere(Compound):
    def __init__(
        self,
        radius: float,
        angle1: float = 0,
        angle2: float = 90,
        angle3: float = 360,
        mode: Mode = Mode.ADDITION,
    ):

        new_solids = []
        for i, workplane in enumerate(len(BuildPart.get_context().workplanes)):
            for location in BuildPart.get_context().locations[i]:
                new_solids.append(
                    Solid.makeSphere(
                        radius,
                        location.position(),
                        workplane.zDir,
                        angle1,
                        angle2,
                        angle3,
                    )
                )

        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Torus(Compound):
    def __init__(
        self,
        radius1: float,
        radius2: float,
        angle1: float = 0,
        angle2: float = 360,
        mode: Mode = Mode.ADDITION,
    ):
        new_solids = []
        for i, workplane in enumerate(len(BuildPart.get_context().workplanes)):
            for location in BuildPart.get_context().locations[i]:
                new_solids.append(
                    Solid.makeTorus(
                        radius1,
                        radius2,
                        location.position(),
                        workplane.zDir,
                        angle1,
                        angle2,
                    )
                )

        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Wedge(Compound):
    def __init__(
        self,
        dx: float,
        dy: float,
        dz: float,
        xmin: float,
        zmin: float,
        xmax: float,
        zmax: float,
        mode: Mode = Mode.ADDITION,
    ):

        new_solids = []
        for i, workplane in enumerate(len(BuildPart.get_context().workplanes)):
            for location in BuildPart.get_context().locations[i]:
                new_solids.append(
                    Solid.makeWedge(
                        dx,
                        dy,
                        dz,
                        xmin,
                        zmin,
                        xmax,
                        zmax,
                        location.position(),
                        workplane.zDir,
                    )
                )

        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)
