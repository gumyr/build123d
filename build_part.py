from math import pi, sin, cos, radians, sqrt
from typing import Union, Iterable, Sequence, Callable
from enum import Enum, auto
import cadquery as cq
from cadquery.hull import find_hull
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
    def pending_face_count(self) -> int:
        return len(self.pending_faces.values())

    @property
    def pending_edge_count(self) -> int:
        return len(self.pending_edges.values())

    @property
    def pending_location_count(self) -> int:
        return len(self.locations.values())

    def __init__(
        self,
        parent: BuildAssembly = None,
        mode: Mode = Mode.ADDITION,
        workplane: Plane = Plane.named("XY"),
    ):
        self.parent = parent
        self.part: Solid = None
        self.workplanes: list[Plane] = [workplane]
        self.pending_faces: dict[int : list[Face]] = {0: []}
        self.pending_edges: dict[int : list[Edge]] = {0: []}
        self.locations: dict[int : list[Location]] = {0: []}
        self.last_operation: dict[CqObject : list[Shape]] = {}

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def push_points(self, *pts: Union[VectorLike, Location]):
        new_locations = [
            Location(Vector(pt)) if not isinstance(pt, Location) else pt for pt in pts
        ]
        for i in range(len(self.workplanes)):
            self.locations[i].extend(new_locations)
        print(f"{len(self.locations[i])=}")
        return new_locations[0] if len(new_locations) == 1 else new_locations

    def add(self, obj: Union[Edge, Face], mode: Mode = Mode.ADDITION):
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

    def workplane(self, workplane: Plane = Plane.named("XY"), replace=True):
        if replace:
            self.workplanes = [workplane]
        else:
            self.workplanes.append(workplane)
            self.locations[len(self.workplanes) - 1] = [Location()]
        return workplane

    def faces_to_workplanes(self, *faces: Sequence[Face], replace=False):
        new_planes = []
        for face in faces:
            new_plane = Plane(origin=face.Center(), normal=face.normalAt(face.Center()))
            new_planes.append(new_plane)
            self.workplane(new_plane, replace)
        return new_planes[0] if len(new_planes) == 1 else new_planes

    def edges(self, sort_by: SortBy = SortBy.NONE, reverse: bool = False) -> list[Edge]:
        if sort_by == SortBy.NONE:
            edges = self.part.Edges()
        elif sort_by == SortBy.X:
            edges = sorted(
                self.part.Edges(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            edges = sorted(
                self.part.Edges(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            edges = sorted(
                self.part.Edges(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.LENGTH:
            edges = sorted(
                self.part.Edges(),
                key=lambda obj: obj.Length(),
                reverse=reverse,
            )
        elif sort_by == SortBy.RADIUS:
            edges = sorted(
                self.part.Edges(),
                key=lambda obj: obj.radius(),
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            edges = sorted(
                self.part.Edges(),
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")

        return edges

    def faces(self, sort_by: SortBy = SortBy.NONE, reverse: bool = False) -> list[Face]:
        if sort_by == SortBy.NONE:
            faces = self.part.Faces()
        elif sort_by == SortBy.X:
            faces = sorted(
                self.part.Faces(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            faces = sorted(
                self.part.Faces(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            faces = sorted(
                self.part.Faces(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.AREA:
            faces = sorted(
                self.part.Faces(), key=lambda obj: obj.Area(), reverse=reverse
            )
        elif sort_by == SortBy.DISTANCE:
            faces = sorted(
                self.part.Faces(),
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")
        return faces

    def vertices(
        self, sort_by: SortBy = SortBy.NONE, reverse: bool = False
    ) -> list[Vertex]:
        if sort_by == SortBy.NONE:
            vertices = self.part.Vertices()
        elif sort_by == SortBy.X:
            vertices = sorted(
                self.part.Vertices(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            vertices = sorted(
                self.part.Vertices(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            vertices = sorted(
                self.part.Vertices(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            vertices = sorted(
                self.part.Vertices(),
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")
        return vertices

    def place_solids(
        self,
        new_solids: list[Solid, Compound],
        mode: Mode = Mode.ADDITION,
        clean: bool = True,
    ):

        Solid.clean_op = Solid.clean if clean else Solid.null
        Compound.clean_op = Compound.clean if clean else Compound.null

        before_vertices = set() if self.part is None else set(self.part.Vertices())
        before_edges = set() if self.part is None else set(self.part.Edges())
        before_faces = set() if self.part is None else set(self.part.Faces())

        if mode == Mode.ADDITION:
            if self.part is None:
                if len(new_solids) == 1:
                    self.part = new_solids[0]
                else:
                    self.part = new_solids.pop().fuse(*new_solids)
            else:
                self.part = self.part.fuse(*new_solids).clean_op()
        elif mode == Mode.SUBTRACTION:
            if self.part is None:
                raise ValueError("Nothing to subtract from")
            self.part = self.part.cut(*new_solids).clean_op()
        elif mode == Mode.INTERSECTION:
            if self.part is None:
                raise ValueError("Nothing to intersect with")
            self.part = self.part.intersect(*new_solids).clean_op()

        self.last_operation[CqObject.VERTEX] = list(
            set(self.part.Vertices()) - before_vertices
        )
        self.last_operation[CqObject.EDGE] = list(set(self.part.Edges()) - before_edges)
        self.last_operation[CqObject.FACE] = list(set(self.part.Faces()) - before_faces)

    def extrude(
        self,
        until: Union[float, Until, Face],
        both: bool = False,
        taper: float = None,
        mode: Mode = Mode.ADDITION,
        clean: bool = True,
    ):

        new_solids: list[Solid] = []
        for plane_index, faces in self.pending_faces.items():
            for face in faces:
                new_solids.append(
                    Solid.extrudeLinear(
                        face, self.workplanes[plane_index].zDir * until, 0
                    )
                )
                if both:
                    new_solids.append(
                        Solid.extrudeLinear(
                            face,
                            self.workplanes[plane_index].zDir * until * -1.0,
                            0,
                        )
                    )

        self.place_solids(new_solids, mode, clean)

        return new_solids[0] if len(new_solids) == 1 else new_solids

    def revolve(
        self,
        angle_degrees: float = 360.0,
        axis_start: VectorLike = None,
        axis_end: VectorLike = None,
        mode: Mode = Mode.ADDITION,
        clean: bool = True,
    ):
        # Make sure we account for users specifying angles larger than 360 degrees, and
        # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
        angle = angle_degrees % 360.0
        angle = 360.0 if angle == 0 else angle

        new_solids = []
        for i, workplane in enumerate(self.workplanes):
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

            for face in self.pending_faces[i]:
                new_solids.append(Solid.revolve(face, angle, *axis))

        self.place_solids(new_solids, mode, clean)

        return new_solids[0] if len(new_solids) == 1 else new_solids

    def loft(self, ruled: bool = False, mode: Mode = Mode.ADDITION, clean: bool = True):

        loft_wires = []
        for i in range(len(self.workplanes)):
            for face in self.pending_faces[i]:
                loft_wires.append(face.outerWire())
        new_solid = Solid.makeLoft(loft_wires, ruled)
        self.place_solids([new_solid], mode, clean)

        return new_solid

    def sweep(
        self,
        path: Union[Edge, Wire],
        multisection: bool = False,
        make_solid: bool = True,
        is_frenet: bool = False,
        transition: Transition = Transition.RIGHT,
        normal: VectorLike = None,
        binormal: Union[Edge, Wire] = None,
        mode: Mode = Mode.ADDITION,
        clean: bool = True,
    ):

        path_wire = Wire.assembleEdges([path]) if isinstance(path, Edge) else path
        if binormal is None:
            binormal_mode = Vector(normal)
        elif isinstance(binormal, Edge):
            binormal_mode = Wire.assembleEdges([binormal])
        else:
            binormal_mode = binormal

        new_solids = []
        for i, workplane in enumerate(self.workplanes):
            if not multisection:
                for face in self.pending_faces[i]:
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
                    sections = [face.outerWire() for face in self.pending_faces[i]]
                    new_solids.append(
                        Solid.sweep_multi(
                            sections, path_wire, make_solid, is_frenet, binormal_mode
                        )
                    )

        self.place_solids(new_solids, mode, clean)

        return new_solids

    def fillet(self, *edges: Sequence[Edge], radius: float):
        self.part = self.part.fillet(radius, [e for e in edges])

    def chamfer(self, *edges: Sequence[Edge], length1: float, length2: float = None):
        self.part = self.part.chamfer(length1, length2, list(edges))
