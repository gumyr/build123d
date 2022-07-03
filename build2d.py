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
from build3d import Build3D


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
