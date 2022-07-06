"""
OK, fwiw, the reason translate() creates a copy is because the use of copy=True in Shape._apply_transform(): https://github.com/CadQuery/cadquery/blob/c9d3f1e693d8d3b59054c8f10027c46a55342b22/cadquery/occ_impl/shapes.py#L846.  I tried setting it to False and my original example passes.
Thanks.  Playing around a bit more, it seems like translate() makes the underlying TShapes unequal, but Shape.moved() preserves TShape.  This returns true, which could be useful:

x1 = cq.Workplane().box(3,4,5)
x2 = cq.Workplane(x1.findSolid().moved(cq.Location(cq.Vector(1,2,3),cq.Vector(4,5,6),7)))

f1 = x1.faces(">Z").val()
f2 = x2.faces(">Z").val()

f1.wrapped.TShape() == f2.wrapped.TShape()   <=== TRUE

@fpq473 - cadquery newbie
Thanks.  Playing around a bit more, it seems like translate() makes the underlying TShapes unequal, but Shape.moved() preserves TShape.  This returns true, which could be useful: x1 = cq.Workplane().box(3,4,5) x2 = cq.Workplane(x1.findSolid().moved(cq.Location(cq.Vector(1,2,3),cq.Vector(4,5,6),7)))  f1 = x1.faces(">Z").val() f2 = x2.faces(">Z").val()  f1.wrapped.TShape() == f2.wrapped.TShape()   <=== TRUE

"""

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

z_axis = (Vector(0, 0, 0), Vector(0, 0, 1))


def __matmul__custom(e: Union[Edge, Wire], p: float):
    return e.positionAt(p)


def __mod__custom(e: Union[Edge, Wire], p: float):
    return e.tangentAt(p)


Edge.__matmul__ = __matmul__custom
Edge.__mod__ = __mod__custom
Wire.__matmul__ = __matmul__custom
Wire.__mod__ = __mod__custom
line = Edge.makeLine(Vector(0, 0, 0), Vector(10, 0, 0))
# print(f"position of line at 1/2: {line @ 0.5=}")
# print(f"tangent of line at 1/2: {line % 0.5=}")


def by_x(obj: Shape) -> float:
    return obj.Center().x


def _by_x_shape(self) -> float:
    return self.Center().x


Shape.by_x = _by_x_shape


def by_y(obj: Shape) -> float:
    return obj.Center().y


def _by_y_shape(self) -> float:
    return self.Center().y


Shape.by_y = _by_y_shape


def by_z(obj: Shape) -> float:
    return obj.Center().z


def _by_z_shape(self) -> float:
    return self.Center().z


Shape.by_z = _by_z_shape


def by_length(obj: Union[Edge, Wire]) -> float:
    return obj.Length()


def _by_length_edge_or_wire(self) -> float:
    return self.Length()


Edge.by_length = _by_length_edge_or_wire
Wire.by_length = _by_length_edge_or_wire


def by_radius(obj: Union[Edge, Wire]) -> float:
    return obj.radius()


def _by_radius_edge_or_wire(self) -> float:
    return self.radius()


Edge.by_radius = _by_radius_edge_or_wire
Wire.by_radius = _by_radius_edge_or_wire


def by_area(obj: cq.Shape) -> float:
    return obj.Area()


def _by_area_shape(self) -> float:
    return self.Area()


Shape.by_area = _by_area_shape


class SortBy(Enum):
    NONE = auto()
    X = auto()
    Y = auto()
    Z = auto()
    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()


class Mode(Enum):
    """Combination Mode"""

    ADDITION = auto()
    SUBTRACTION = auto()
    INTERSECTION = auto()
    CONSTRUCTION = auto()


class Transition(Enum):
    RIGHT = auto()
    ROUND = auto()
    TRANSFORMED = auto()


class Font_Style(Enum):
    """Text Font Styles"""

    REGULAR = auto()
    BOLD = auto()
    ITALIC = auto()

    def legacy(font_style: "Font_Style") -> str:
        return {
            Font_Style.REGULAR: "regular",
            Font_Style.BOLD: "bold",
            Font_Style.ITALIC: "italic",
        }[font_style]


class Halign(Enum):
    """Horizontal Alignment"""

    CENTER = auto()
    LEFT = auto()
    RIGHT = auto()

    def legacy(halign: "Halign") -> str:
        return {
            Halign.LEFT: "left",
            Halign.RIGHT: "right",
            Halign.CENTER: "center",
        }[halign]


class Valign(Enum):
    """Vertical Alignment"""

    CENTER = auto()
    TOP = auto()
    BOTTOM = auto()

    def legacy(valign: "Valign") -> str:
        return {
            Valign.TOP: "top",
            Valign.BOTTOM: "bottom",
            Valign.CENTER: "center",
        }[valign]


class BuildAssembly:
    def add(self):
        pass


def _null(self):
    return self


Solid.null = _null
Compound.null = _null


class Until(Enum):
    NEXT = auto()
    LAST = auto()


class CqObject(Enum):
    EDGE = auto()
    FACE = auto()
    VERTEX = auto()


class Build3D:
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
        self.working_volume: Solid = None
        self.workplanes: list[Plane] = [workplane]
        self.pending_faces: dict[int : list[Face]] = {0: []}
        self.pending_edges: dict[int : list[Edge]] = {0: []}
        self.locations: dict[int : list[Location]] = {0: []}
        self.last_operation: dict[CqObject : list[Shape]] = {}
        # self.last_operation_edges: list[Edge] = []

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
            edges = self.working_volume.Edges()
        elif sort_by == SortBy.X:
            edges = sorted(
                self.working_volume.Edges(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            edges = sorted(
                self.working_volume.Edges(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            edges = sorted(
                self.working_volume.Edges(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.LENGTH:
            edges = sorted(
                self.working_volume.Edges(),
                key=lambda obj: obj.Length(),
                reverse=reverse,
            )
        elif sort_by == SortBy.RADIUS:
            edges = sorted(
                self.working_volume.Edges(),
                key=lambda obj: obj.radius(),
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            edges = sorted(
                self.working_volume.Edges(),
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")

        return edges

    def faces(self, sort_by: SortBy = SortBy.NONE, reverse: bool = False) -> list[Face]:
        if sort_by == SortBy.NONE:
            faces = self.working_volume.Faces()
        elif sort_by == SortBy.X:
            faces = sorted(
                self.working_volume.Faces(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            faces = sorted(
                self.working_volume.Faces(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            faces = sorted(
                self.working_volume.Faces(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.AREA:
            faces = sorted(
                self.working_volume.Faces(), key=lambda obj: obj.Area(), reverse=reverse
            )
        elif sort_by == SortBy.DISTANCE:
            faces = sorted(
                self.working_volume.Faces(),
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
            vertices = self.working_volume.Vertices()
        elif sort_by == SortBy.X:
            vertices = sorted(
                self.working_volume.Vertices(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            vertices = sorted(
                self.working_volume.Vertices(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            vertices = sorted(
                self.working_volume.Vertices(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            vertices = sorted(
                self.working_volume.Vertices(),
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

        before_vertices = (
            set()
            if self.working_volume is None
            else set(self.working_volume.Vertices())
        )
        before_edges = (
            set() if self.working_volume is None else set(self.working_volume.Edges())
        )
        before_faces = (
            set() if self.working_volume is None else set(self.working_volume.Faces())
        )

        if mode == Mode.ADDITION:
            if self.working_volume is None:
                if len(new_solids) == 1:
                    self.working_volume = new_solids[0]
                else:
                    self.working_volume = new_solids.pop().fuse(*new_solids)
            else:
                self.working_volume = self.working_volume.fuse(*new_solids).clean_op()
        elif mode == Mode.SUBTRACTION:
            if self.working_volume is None:
                raise ValueError("Nothing to subtract from")
            self.working_volume = self.working_volume.cut(*new_solids).clean_op()
        elif mode == Mode.INTERSECTION:
            if self.working_volume is None:
                raise ValueError("Nothing to intersect with")
            self.working_volume = self.working_volume.intersect(*new_solids).clean_op()

        self.last_operation[CqObject.VERTEX] = list(
            set(self.working_volume.Vertices()) - before_vertices
        )
        self.last_operation[CqObject.EDGE] = list(
            set(self.working_volume.Edges()) - before_edges
        )
        self.last_operation[CqObject.FACE] = list(
            set(self.working_volume.Faces()) - before_faces
        )

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
        self.working_volume = self.working_volume.fillet(radius, [e for e in edges])

    def chamfer(self, *edges: Sequence[Edge], length1: float, length2: float = None):
        self.working_volume = self.working_volume.chamfer(length1, length2, list(edges))


class Build2D:
    def __init__(self, parent: Build3D = None, mode: Mode = Mode.ADDITION):
        self.working_surface = Compound.makeCompound(())
        self.pending_edges: list[Edge] = []
        # self.tags: dict[str, Face] = {}
        self.parent = parent
        self.locations: list[Location] = []
        self.mode = mode

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        print(f"Exit: Area of generated Face: {self.working_surface.Area()}")
        if self.parent is not None:
            self.parent.add(self.working_surface, self.mode)

    def add(self, f: Face, mode: Mode = Mode.ADDITION):
        new_faces = self.place_face(f, mode)
        return new_faces if len(new_faces) > 1 else new_faces[0]

    def add(self, *objects: Union[Edge, Face], mode: Mode = Mode.ADDITION):
        new_faces = [obj for obj in objects if isinstance(obj, Face)]
        new_edges = [obj for obj in objects if isinstance(obj, Edge)]

        placed_faces = []
        for face in new_faces:
            placed_faces.extend(self.place_face(face, mode))

        placed_edges = []
        if not self.locations:
            self.locations = [Location(Vector())]
        for location in self.locations:
            placed_edges.extend([edge.moved(location) for edge in new_edges])
        self.pending_edges.extend(placed_edges)

        self.locations = []
        placed_objects = placed_faces + placed_edges
        return placed_objects[0] if len(placed_objects) == 1 else placed_objects

    def push_points(self, *pts: Sequence[Union[VectorLike, Location]]):
        new_locations = [
            Location(Vector(pt)) if not isinstance(pt, Location) else pt for pt in pts
        ]
        self.locations.extend(new_locations)
        return new_locations

    def assemble_edges(self, mode: Mode = Mode.ADDITION, tag: str = None) -> Face:
        pending_face = Face.makeFromWires(Wire.assembleEdges(self.pending_edges))
        self.add(pending_face, mode, tag)
        self.pending_edges = []
        # print(f"Area of generated Face: {pending_face.Area()}")
        return pending_face

    def hull_edges(self, mode: Mode = Mode.ADDITION, tag: str = None) -> Face:
        pending_face = find_hull(self.pending_edges)
        self.add(pending_face, mode, tag)
        self.pending_edges = []
        # print(f"Area of generated Face: {pending_face.Area()}")
        return pending_face

    def rect(
        self,
        width: float,
        height: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ) -> Face:
        """
        Construct a rectangular face.
        """

        new_faces = self.place_face(
            Face.makePlane(height, width).rotate(*z_axis, angle), mode
        )

        return new_faces if len(new_faces) > 1 else new_faces[0]

    def circle(self, radius: float, mode: Mode = Mode.ADDITION) -> Face:
        """
        Construct a circular face.
        """

        new_faces = self.place_face(
            Face.makeFromWires(Wire.makeCircle(radius, *z_axis)), mode
        )

        return new_faces if len(new_faces) > 1 else new_faces[0]

    def text(
        self,
        txt: str,
        fontsize: float,
        font: str = "Arial",
        font_path: str = None,
        font_style: Font_Style = Font_Style.REGULAR,
        halign: Halign = Halign.LEFT,
        valign: Valign = Valign.CENTER,
        path: Union[Edge, Wire] = None,
        position_on_path: float = 0.0,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
        tag: str = None,
    ) -> Compound:

        text_string = Compound.make2DText(
            txt,
            fontsize,
            font,
            font_path,
            Font_Style.legacy(font_style),
            Halign.legacy(halign),
            Valign.legacy(valign),
            position_on_path,
            path,
        ).rotate(Vector(), Vector(0, 0, 1), angle)

        new_faces = self.place_face(text_string, mode)

        return new_faces if len(new_faces) > 1 else new_faces[0]

    def place_face(self, face: Face, mode: Mode = Mode.ADDITION):

        if not self.locations:
            self.locations = [Location(Vector())]
        new_faces = [face.moved(location) for location in self.locations]

        if mode == Mode.ADDITION:
            self.working_surface = self.working_surface.fuse(*new_faces).clean()
        elif mode == Mode.SUBTRACTION:
            self.working_surface = self.working_surface.cut(*new_faces).clean()
        elif mode == Mode.INTERSECTION:
            self.working_surface = self.working_surface.intersect(*new_faces).clean()
        elif mode == Mode.CONSTRUCTION:
            pass
        else:
            raise ValueError(f"Invalid mode: {mode}")

        return new_faces


class Build1D:
    @property
    def working_line(self) -> Wire:
        return Wire.assembleEdges(self.edge_list)

    def __init__(self, parent: Build2D = None, mode: Mode = Mode.ADDITION):
        self.edge_list = []
        self.tags: dict[str, Edge] = {}
        self.parent = parent
        self.mode = mode

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.parent is not None:
            self.parent.add(*self.edge_list, mode=self.mode)

    def edges(self) -> list[Edge]:
        return self.edge_list

    def vertices(self) -> list[Vertex]:
        vertex_list = []
        for e in self.edge_list:
            vertex_list.extend(e.Vertices())
        return list(set(vertex_list))

    def polyline(
        self,
        *pts: VectorLike,
        mode: Mode = Mode.ADDITION,
    ) -> Union[Edge, Wire]:
        if len(pts) < 2:
            raise ValueError("polyline requires two or more pts")

        lines_pts = [Vector(p) for p in pts]

        new_edges = [
            Edge.makeLine(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]

        for e in new_edges:
            e.forConstruction = mode == Mode.CONSTRUCTION
        self.edge_list.extend(new_edges)

        line_segments = (
            new_edges[0] if len(new_edges) == 1 else Wire.assembleEdges(new_edges)
        )
        return line_segments

    def spline(
        self,
        *pts: VectorLike,
        tangents: Iterable[VectorLike] = None,
        tangent_scalars: Iterable[float] = None,
        periodic: bool = False,
        mode: Mode = Mode.ADDITION,
    ) -> Edge:

        spline_pts = [Vector(pt) for pt in pts]
        if tangents:
            spline_tangents = [Vector(tangent) for tangent in tangents]
        else:
            spline_tangents = None

        if tangents and not tangent_scalars:
            scalars = [1.0] * len(tangents)
        else:
            scalars = tangent_scalars

        spline = Edge.makeSpline(
            [p if isinstance(p, Vector) else Vector(*p) for p in spline_pts],
            tangents=[
                t * s if isinstance(t, Vector) else Vector(*t) * s
                for t, s in zip(spline_tangents, scalars)
            ]
            if spline_tangents
            else None,
            periodic=periodic,
            scale=tangent_scalars is None,
        )

        spline.forConstruction = mode == Mode.CONSTRUCTION
        self.edge_list.append(spline)
        return spline

    def center_arc(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float,
        mode: Mode = Mode.ADDITION,
    ) -> Edge:

        if abs(arc_size) >= 360:
            arc = Edge.makeCircle(
                radius,
                center,
                angle1=start_angle,
                angle2=start_angle,
                orientation=arc_size > 0,
            )
        else:
            p0 = center
            p1 = p0 + radius * Vector(
                cos(radians(start_angle)), sin(radians(start_angle))
            )
            p2 = p0 + radius * Vector(
                cos(radians(start_angle + arc_size / 2)),
                sin(radians(start_angle + arc_size / 2)),
            )
            p3 = p0 + radius * Vector(
                cos(radians(start_angle + arc_size)),
                sin(radians(start_angle + arc_size)),
            )
            arc = Edge.makeThreePointArc(p1, p2, p3)

        arc.forConstruction = mode == Mode.CONSTRUCTION
        self.edge_list.append(arc)
        return arc

    def three_point_arc(
        self,
        *pts: VectorLike,
        mode: Mode = Mode.ADDITION,
    ) -> Edge:

        arc_pts = [Vector(p) for p in pts]
        if len(arc_pts) != 3:
            raise ValueError("three_point_arc requires three points")

        arc = Edge.makeThreePointArc(*arc_pts)

        arc.forConstruction = mode == Mode.CONSTRUCTION
        self.edge_list.append(arc)
        return arc

    def tangent_arc(
        self,
        *pts: VectorLike,
        tangent: VectorLike,
        tangent_from_first: bool = True,
        mode: Mode = Mode.ADDITION,
    ):
        arc_pts = [Vector(p) for p in pts]
        if len(arc_pts) != 2:
            raise ValueError("tangent_arc requires two points")
        arc_tangent = Vector(tangent)

        point_indices = (0, -1) if tangent_from_first else (-1, 0)
        arc = Edge.makeTangentArc(
            arc_pts[point_indices[0]], arc_tangent, arc_pts[point_indices[1]]
        )

        arc.forConstruction = mode == Mode.CONSTRUCTION
        self.edge_list.append(arc)
        return arc

    def radius_arc(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        radius: float,
        mode: Mode = Mode.ADDITION,
    ) -> Edge:

        start = Vector(start_point)
        end = Vector(end_point)

        # Calculate the sagitta from the radius
        length = end.sub(start).Length / 2.0
        try:
            sagitta = abs(radius) - sqrt(radius**2 - length**2)
        except ValueError:
            raise ValueError("Arc radius is not large enough to reach the end point.")

        # Return a sagitta arc
        if radius > 0:
            return self.sagitta_arc(start, end, sagitta, mode=mode)
        else:
            return self.sagitta_arc(start, end, -sagitta, mode=mode)

    def sagitta_arc(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        sagitta: float,
        mode: Mode = Mode.ADDITION,
    ) -> Edge:

        start = Vector(start_point)
        end = Vector(end_point)
        mid_point = (end + start) * 0.5

        sagitta_vector = (end - start).normalized() * abs(sagitta)
        if sagitta > 0:
            sagitta_vector.x, sagitta_vector.y = (
                -sagitta_vector.y,
                sagitta_vector.x,
            )  # Rotate sagVector +90 deg
        else:
            sagitta_vector.x, sagitta_vector.y = (
                sagitta_vector.y,
                -sagitta_vector.x,
            )  # Rotate sagVector -90 deg

        sag_point = mid_point + sagitta_vector

        return self.three_point_arc(start, sag_point, end, mode=mode)

    def mirror_x(self, *edges: Edge) -> list[Edge]:

        mirrored_edges = Plane.named("XY").mirrorInPlane(edges, axis="X")
        self.edge_list.extend(mirrored_edges)
        return mirrored_edges[0] if len(mirrored_edges) == 1 else mirrored_edges

    def mirror_y(self, *edges: Edge) -> list[Edge]:

        mirrored_edges = Plane.named("XY").mirrorInPlane(edges, axis="Y")
        self.edge_list.extend(mirrored_edges)
        return mirrored_edges[0] if len(mirrored_edges) == 1 else mirrored_edges


# with Build2D() as f:
#     # Start with a central circle with a square quarter
#     c6 = f.circle(6)
#     print(f"{type(c6)=}, {c6.Center()=}")
#     f.push((3, 3))
#     r6 = f.rect(6, 6)
#     print(f"{type(r6)=}, {r6.Center()=}")
#     # Create some locations for the cutouts
#     polar_locations = [
#         Location(Vector(3, 0, 0).rotateZ(a), Vector(0, 0, 1), a)
#         for a in range(0, 360, 45)
#     ]
#     f.push(*polar_locations)
#     # Cutout a set of diamonds
#     with Build1D(parent=f, mode=Mode.SUBTRACTION) as e:
#         # Instantiate a simple line
#         l = e.polyline((0, 0), (1, 1))
#         print(f"Type of line: {type(l)}")
#         # Instantiate a polyline
#         m = e.polyline(l.endPoint(), (2, 0), (1, -1))
#         print(f"Type of polyline: {type(m)}")
#         # Create another line but don't assign a global to it
#         e.polyline(m.endPoint(), l.startPoint())
#         # Extract all of the vertices - two for each Edge
#         all_vertices = e.vertices()
#         print(f"Type of vertices: {type(all_vertices)}")
#         print(f"Total number of vertices: {len(all_vertices)}")
#         # Sort these vertices by Y value
#         corners_sorted_by_Y = sorted(all_vertices, key=lambda v: v.Y)
#         # Filter the sorted value to extract just those on the X axis
#         side_corners = list(filter(lambda v: abs(v.Y) < 1e-5, corners_sorted_by_Y))
#         print(f"Number of vertices after filter: {len(side_corners)}")
#         print("Corner vertices at X axis:")
#         for v in side_corners:
#             print(v.toTuple())

# with Build2D() as f2:
#     with Build1D(parent=f2) as c2:
#         pts = [Vector(10, 0, 0).rotateZ(a) for a in range(0, 360, 60)]
#         c2.polyline(*pts)
# print(f"{type(c2.face)=}")

# with Build3D() as s1:
#     with Build2D(s1) as f1:
#         f1.rect(10, 10)
#     box = s1.extrude(10)
#     s1.faces_to_workplanes(*box.Faces())
#     with Build2D(s1) as f2:
#         f2.circle(3)
#     s1.extrude(-1, mode=Mode.SUBTRACTION)
#     # edges_by_z = sorted(s1.edges(), key=by_z, reverse=True)[0:1]
#     # edges_by_z = s1.edges(sort_by=SortBy.Z, reverse=True)[0:1]
#     edges_by_z = s1.edges(SortBy.Z, reverse=True)[0:1]
#     # print(f"{edges_by_z}")
#     # top_circle = sorted(s1.last_operation_edges, key=by_z, reverse=True)[0]
#     # top_circle = filter(lambda f: abs(f.by_z() - 5) < 1e-5, s1.last_operation_edges)
#     # s1.fillet(*s1.last_operation[CqObject.EDGE], radius=0.2)
#     s1.fillet(*edges_by_z, radius=0.2)

# print(s1.solid.Volume())

with Build2D() as f1:
    f1.push_points((-5, -5), (-5, 5), (5, 5), (5, -5))
    # f1.rect(1, 1)
    f1.circle(1)
# faces = [f for list in s1.faces.values() for f in list]

with Build3D() as s2:
    with Build2D(s2) as f2:
        f2.push_points((4, 3))
        rect = f2.rect(6, 6)
    s2.revolve()

# with Build3D() as s2:
#     s2.push_points((-5, -5), (-5, 5), (5, 5), (5, -5))
#     with Build2D(s2) as f1:
#         f1.circle(1)


with Build3D() as s3:
    slice_count = 10
    for i in range(slice_count + 1):
        s3.workplane(Plane(origin=(0, 0, i * 3), normal=(0, 0, 1)))
        with Build2D(s3) as f3:
            f3.circle(10 * sin(i * pi / slice_count) + 5)
    s3.loft()

# s4 = Build3D()
# circles = [
#     Build2D().circle(10 * sin(i * pi / slice_count) + 5).translate(Vector(0, 0, 3 * i))
#     for i in range(slice_count + 1)
# ]
# for circle in circles:
#     s4.add(circle)
# vase = s4.loft()

s4 = Build3D()
for i in range(slice_count + 1):
    circle = (
        Build2D()
        .circle(10 * sin(i * pi / slice_count) + 5)
        .translate(Vector(0, 0, 3 * i))
    )
    s4.add(circle)
vase = s4.loft()

Edge.
object

with Build1D() as ml:
    l1 = ml.polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
    l2 = ml.polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
    ml.radius_arc(l1 @ 1, l2 @ 0, 0.0271)
    l3 = ml.polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
    ml.tangent_arc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
    l4 = ml.polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
    ml.sagitta_arc(l3 @ 1, l4 @ 0, 0.003)
    l5 = ml.polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
    ml.three_point_arc(l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0)
    l6 = ml.polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
    ml.spline(l5 @ 1, l6 @ 0, tangents=(l5 % 1, l6 % 0), tangent_scalars=(2, 2))
    l7 = ml.polyline((0.0692, 0.7808), (0.0000, 0.9167))
    ml.tangent_arc(l6 @ 1, l7 @ 0, tangent=l6 % 1)
    ml.mirror_y(*ml.edges())

# slice_count = 10
# # for i in range(slice_count + 1):
# #     s3.workplane(Plane(origin=(0, 0, i * 3), normal=(0, 0, 1)))
# for i in range(1, slice_count + 1):
#     s3.workplane(Plane(origin=(0, 0, i * 3), normal=(0, 0, 1)), replace=False)
#     # print(f"{s3.workplane_count=}")
#     # radii = iter(
#     #     [10 * sin(i * pi / slice_count) + 5 for i in range(0, slice_count + 1)]
#     # )
#     with Build2D(s3) as f3:
#         f3.circle(10 * sin(i * pi / slice_count) + 5)
#         # f3.circle(next(radii))
# s3.loft()


class ThreePointArc(Edge):
    @property
    def edge(self) -> Edge:
        return self.arc

    def __init__(self, context: Build1D, *pts: VectorLike):

        # def __init__(self, *pts: VectorLike):
        self.context = context
        self.points = [Vector(p) for p in pts]
        if len(self.points) != 3:
            raise ValueError("ThreePointArc requires three points")
        self.arc = Edge.makeThreePointArc(*self.points)
        if context is not None:
            context.edge_list.append(self.arc)

    # def __call__(self, context: Build1D) -> Edge:
    #     # def __call__(self) -> Edge:

    #     return self.arc


def three_point_arc(context: Build1D, *pts: VectorLike) -> Edge:
    points = [Vector(p) for p in pts]
    if len(points) != 3:
        raise ValueError("ThreePointArc requires three points")
    arc = Edge.makeThreePointArc(*points)
    if context is not None:
        context.edge_list.append(arc)
    return arc


with Build1D() as b1:
    three_point_arc(b1, (0, 0), (1, 0), (0, 1))
    a1 = three_point_arc(b1, (0, 0), (1, 0), (0, 1))
print(f"{type(a1)=}")

c1 = Build1D()
# e = ThreePointArc((0, 0), (1, 0), (0, 1))(c1)
e2 = ThreePointArc(c1, (0, 0), (1, 0), (0, 1)).edge
# print(type(e))
# print(e @ 1)
print(c1.edge_list)
print(type(e2))


if "show_object" in locals():
    # show_object(s2.pending_faces[0], "pending_face")
    # show_object(rect, name="rect")
    # show_object(f1.working_surface, name="working_surface")
    # # show_object(revolve, name="revolve")
    # show_object(s2.working_volume, name="s2")
    # show_object(s3.working_volume, name="s3")
    # show_object(s3.pending_faces[0], name="s3_faces")
    # # show_object(circles)
    # show_object(vase)
    show_object(ml.edge_list, name="maple")
    # show_object(f1.face_list)
    # show_object(s1.working_solid, name="s1")
    # show_object(s1.last_operation_edges, name="last edges")
    # show_object(s2.solid, name="s2")
    # show_object(f1.faces, name="f1")
    # show_object(rface, name="rface")
    # show_object(faces, name="circles")
    # show_object(bumps, name="bumps")
    # show_object(f.faces, name="f")
    # show_object(f2.faces, name="f2")
