"""
TODO:
- add center to arrays
- make distribute a method of edge and wire
- ensure offset is a method of edge and wire
- if bb planar make face else make solid
"""
from math import pi, sin, cos, tan, radians, sqrt
from typing import Union, Iterable, Sequence, Callable, cast
from enum import Enum, auto
import cadquery as cq
from itertools import product, chain
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
from build_part import BuildPart


class BuildSketch:
    def __init__(self, mode: Mode = Mode.ADDITION):
        self.sketch = Compound.makeCompound(())
        self.pending_edges: list[Edge] = []
        self.locations: list[Location] = [Location(Vector())]
        self.mode = mode
        self.last_vertices = []
        self.last_edges = []
        self.last_faces = []

    def __enter__(self):
        context_stack.append(self)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        context_stack.pop()
        if context_stack:
            if isinstance(context_stack[-1], BuildPart):
                for edge in self.edge_list:
                    BuildPart.add_to_context(edge, mode=self.mode)

    def vertices(self, select: Select = Select.ALL) -> list[Vertex]:
        vertex_list = []
        if select == Select.ALL:
            for e in self.sketch.Edges():
                vertex_list.extend(e.Vertices())
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return list(set(vertex_list))

    def edges(self, select: Select = Select.ALL) -> list[Edge]:
        if select == Select.ALL:
            edge_list = self.sketch.Edges()
        elif select == Select.LAST:
            edge_list = self.last_edges
        return edge_list

    def faces(self, select: Select = Select.ALL) -> list[Face]:
        if select == Select.ALL:
            face_list = self.sketch.Faces()
        elif select == Select.LAST:
            face_list = self.last_edges
        return face_list

    def consolidate_edges(self) -> Wire:
        return Wire.combine(self.pending_edges)[0]

    @staticmethod
    def add_to_context(*objects: Union[Edge, Face], mode: Mode = Mode.ADDITION):
        if "context_stack" in globals() and mode != Mode.PRIVATE:
            if context_stack:  # Stack isn't empty
                new_faces = [obj for obj in objects if isinstance(obj, Face)]
                new_edges = [obj for obj in objects if isinstance(obj, Edge)]

                pre_vertices = list(set(context_stack[-1].sketch.Vertices()))
                pre_edges = list(set(context_stack[-1].sketch.Edges()))
                pre_faces = list(set(context_stack[-1].sketch.Faces()))
                if mode == Mode.ADDITION:
                    context_stack[-1].sketch = (
                        context_stack[-1].sketch.fuse(*new_faces).clean()
                    )
                elif mode == Mode.SUBTRACTION:
                    context_stack[-1].sketch = (
                        context_stack[-1].sketch.cut(*new_faces).clean()
                    )
                elif mode == Mode.INTERSECTION:
                    context_stack[-1].sketch = (
                        context_stack[-1].sketch.intersect(*new_faces).clean()
                    )
                elif mode == Mode.CONSTRUCTION or mode == Mode.PRIVATE:
                    pass
                else:
                    raise ValueError(f"Invalid mode: {mode}")

                post_vertices = list(set(context_stack[-1].sketch.Vertices()))
                post_edges = list(set(context_stack[-1].sketch.Edges()))
                post_faces = list(set(context_stack[-1].sketch.Faces()))
                context_stack[-1].last_vertices = [
                    v for v in post_vertices if v not in pre_vertices
                ]
                context_stack[-1].last_edges = [
                    e for e in post_edges if e not in pre_edges
                ]
                context_stack[-1].last_faces = [
                    f for f in post_faces if f not in pre_faces
                ]
                context_stack[-1].pending_edges.extend(new_edges)

    @staticmethod
    def get_context() -> "BuildSketch":
        return context_stack[-1]


class Add:
    def __init__(
        self, obj: Union[Edge, Wire, Face, Compound], mode: Mode = Mode.ADDITION
    ):
        edges = []
        if isinstance(obj, Edge):
            edges = [obj]
        elif isinstance(obj, Wire):
            edges = obj.Edges()
        faces = []
        if isinstance(obj, Face):
            faces = [obj]
        elif isinstance(obj, Compound):
            faces = obj.Faces()

        new_edges = [
            edge.moved(location)
            for edge in edges
            for location in BuildSketch.get_context().locations
        ]
        new_faces = [
            face.moved(location)
            for face in faces
            for location in BuildSketch.get_context().locations
        ]
        for obj in new_faces + new_edges:
            BuildSketch.add_to_context(obj, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class BoundingBoxSketch(Compound):
    def __init__(
        self,
        *objects: Shape,
        mode: Mode = Mode.ADDITION,
    ):
        new_faces = []
        for obj in objects:
            if isinstance(obj, Vertex):
                continue
            bb = obj.BoundingBox()
            vertices = [
                (bb.xmin, bb.ymin),
                (bb.xmin, bb.ymax),
                (bb.xmax, bb.ymax),
                (bb.xmax, bb.ymin),
                (bb.xmin, bb.ymin),
            ]
            new_faces.append(
                Face.makeFromWires(Wire.makePolygon([Vector(v) for v in vertices]))
            )
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class BuildFace:
    def __init__(self, *edges: Edge, mode: Mode = Mode.ADDITION):
        pending_face = Face.makeFromWires(Wire.combine(edges)[0])
        BuildSketch.get_context().add_to_context(pending_face, mode)
        BuildSketch.get_context().pending_edges = []


class BuildHull:
    def __init__(self, *edges: Edge, mode: Mode = Mode.ADDITION):
        pending_face = find_hull(edges)
        BuildSketch.get_context().add_to_context(pending_face, mode)
        BuildSketch.get_context().pending_edges = []


class PushPoints:
    def __init__(self, *pts: Union[VectorLike, Location]):
        new_locations = [
            Location(Vector(pt)) if not isinstance(pt, Location) else pt for pt in pts
        ]
        BuildSketch.get_context().locations = new_locations


class RectangularArray:
    def __init__(self, x_spacing: Real, y_spacing: Real, x_count: int, y_count: int):
        if x_count < 1 or y_count < 1:
            raise ValueError(
                f"At least 1 elements required, requested {x_count}, {y_count}"
            )

        new_locations = []
        offset = Vector((x_count - 1) * x_spacing, (y_count - 1) * y_spacing) * 0.5
        for i, j in product(range(x_count), range(y_count)):
            new_locations.append(
                Location(Vector(i * x_spacing, j * y_spacing) - offset)
            )

        BuildSketch.get_context().locations = new_locations


class PolarArray:
    def __init__(
        self,
        radius: float,
        start_angle: float,
        stop_angle: float,
        count: int,
        rotate: bool = True,
    ):
        if count < 1:
            raise ValueError(f"At least 1 elements required, requested {count}")

        x = radius * sin(radians(start_angle))
        y = radius * cos(radians(start_angle))

        if rotate:
            loc = Location(Vector(x, y), Vector(0, 0, 1), -start_angle)
        else:
            loc = Location(Vector(x, y))

        new_locations = [loc]
        angle = (stop_angle - start_angle) / (count - 1)
        for i in range(1, count):
            phi = start_angle + (angle * i)
            x = radius * sin(radians(phi))
            y = radius * cos(radians(phi))
            if rotate:
                loc = Location(Vector(x, y), Vector(0, 0, 1), -phi)
            else:
                loc = Location(Vector(x, y))
            new_locations.append(loc)

        BuildSketch.get_context().locations = new_locations


class FilletSketch(Compound):
    def __init__(self, *vertices: Vertex, radius: float):
        new_faces = []
        for face in BuildSketch.get_context().sketch.Faces():
            vertices_in_face = filter(lambda v: v in face.Vertices(), vertices)
            if vertices_in_face:
                new_faces.append(face.fillet2D(radius, vertices_in_face))
            else:
                new_faces.append(face)
        new_sketch = Compound.makeCompound(new_faces)
        BuildSketch.get_context().sketch = new_sketch
        super().__init__(new_sketch.wrapped)


class ChamferSketch(Compound):
    def __init__(self, *vertices: Vertex, length: float):
        new_faces = []
        for face in BuildSketch.get_context().sketch.Faces():
            vertices_in_face = filter(lambda v: v in face.Vertices(), vertices)
            if vertices_in_face:
                new_faces.append(face.chamfer2D(length, vertices_in_face))
            else:
                new_faces.append(face)
        new_sketch = Compound.makeCompound(new_faces)
        BuildSketch.get_context().sketch = new_sketch
        super().__init__(new_sketch.wrapped)


class Offset(Compound):
    def __init__(
        self, face: Union[Face, Compound], amount: float, mode: Mode = Mode.ADDITION
    ):
        perimeter = face.outerWire()
        face = Face.makeFromWires(perimeter.offset2D(perimeter))
        BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(face.wrapped))


class Rect(Compound):
    def __init__(
        self,
        width: float,
        height: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ):
        face = Face.makePlane(height, width).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Circle(Compound):
    def __init__(
        self,
        radius: float,
        mode: Mode = Mode.ADDITION,
    ):
        face = Face.makeFromWires(Wire.makeCircle(radius, *z_axis))
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Ellipse(Compound):
    def __init__(
        self,
        x_radius: float,
        y_radius: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ):
        face = Face.makeFromWires(
            Wire.makeEllipse(
                x_radius,
                y_radius,
                Vector(),
                Vector(0, 0, 1),
                Vector(1, 0, 0),
                rotation_angle=angle,
            )
        )
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Trapezoid(Compound):
    def __init__(
        self,
        width: float,
        height: float,
        left_side_angle: float,
        right_side_angle: float = None,
        angle: Real = 0,
        mode: Mode = Mode.ADDITION,
    ):
        """
        Construct a trapezoidal face.
        """

        pts = []
        pts.append(Vector(-width / 2, -height / 2))
        pts.append(Vector(width / 2, -height / 2))
        pts.append(
            Vector(-width / 2 + height / tan(radians(left_side_angle)), height / 2)
        )
        pts.append(
            Vector(
                width / 2
                - height
                / tan(
                    radians(right_side_angle)
                    if right_side_angle
                    else radians(left_side_angle)
                ),
                height / 2,
            )
        )
        pts.append(pts[0])
        face = Face.makeFromWires(Wire.makePolygon(pts)).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotCenterToCenter(Compound):
    def __init__(
        self,
        center_separation: float,
        height: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ):
        face = Face.makeFromWires(
            Wire.assembleEdges(
                [
                    Edge.makeLine(
                        Vector(-center_separation / 2, 0, 0),
                        Vector(+center_separation / 2, 0, 0),
                    )
                ]
            ).offset2D(height / 2)
        ).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotOverall(Compound):
    def __init__(
        self,
        width: float,
        height: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ):
        face = Face.makeFromWires(
            Wire.assembleEdges(
                [
                    Edge.makeLine(
                        Vector(-width / 2 + height / 2, 0, 0),
                        Vector(+width / 2 - height / 2, 0, 0),
                    )
                ]
            ).offset2D(height / 2)
        ).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotCenterPoint(Compound):
    def __init__(
        self,
        center: VectorLike,
        point: VectorLike,
        height: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ):
        face = Face.makeFromWires(
            Wire.assembleEdges(
                [
                    Edge.makeLine(
                        Vector(center) - (Vector(point) - Vector(center)),
                        Vector(point),
                    )
                ]
            ).offset2D(height / 2)
        ).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotArc(Compound):
    def __init__(
        self,
        arc: Union[Edge, Wire],
        height: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ):
        arc_wire = arc if isinstance(arc, Wire) else Wire.assembleEdges([arc])
        face = Face.makeFromWires(arc_wire.offset2D(height / 2)).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class RegularPolygon(Compound):
    def regularPolygon(
        self,
        radius: Real,
        side_count: int,
        angle: Real = 0,
        mode: Mode = Mode.ADDITION,
    ):
        pts = [
            Vector(
                radius * sin(i * 2 * pi / side_count),
                radius * cos(i * 2 * pi / side_count),
            )
            for i in range(side_count + 1)
        ]
        face = Face.makeFromWires(Wire.makePolygon(pts)).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Polygon(Compound):
    def __init__(
        self,
        *pts: VectorLike,
        angle: Real = 0,
        mode: Mode = Mode.ADDITION,
    ):
        poly_pts = [Vector(p) for p in pts]

        face = Face.makeFromWires(Wire.makePolygon(poly_pts)).rotate(*z_axis, angle)
        new_faces = [
            face.moved(location) for location in BuildSketch.get_context().locations
        ]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Text(Compound):
    def __init__(
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
        new_compounds = [
            text_string.moved(location)
            for location in BuildSketch.get_context().locations
        ]
        new_faces = [face for compound in new_compounds for face in compound]
        for face in new_faces:
            BuildSketch.add_to_context(face, mode=mode)
        BuildSketch.get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)
