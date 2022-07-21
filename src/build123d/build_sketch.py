"""
BuildSketch

name: build_sketch.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build planar sketches.

TODO:
- add center to arrays
- bug: offset2D doesn't work on a Wire made from a single Edge

Instead of existing constraints how about constraints that return locations
on objects:
- two circles: c1, c2
- "line tangent to c1 & c2" : 4 locations on each circle
  - these would be construction geometry
  - user sorts to select the ones they want
  - uses these points to build geometry
  - how many constraints are currently implemented?

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
from math import pi, sin, cos, tan, radians, sqrt
from typing import Union
from itertools import product

# from .hull import find_hull
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
from cadquery.hull import find_hull
from cadquery import Edge, Face, Wire, Vector, Shape, Location, Vertex, Compound, Plane
from cadquery.occ_impl.shapes import VectorLike
import cq_warehouse.extensions

from build123d.build123d_common import *


class BuildSketch(Builder):
    """BuildSketch

    Create planar 2D sketches (objects with area but not volume) from faces or lines.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    @property
    def _obj(self) -> Compound:
        return self.sketch

    def __init__(self, mode: Mode = Mode.ADD):
        self.sketch = None
        self.pending_edges: list[Edge] = []
        self.locations: list[Location] = [Location(Vector())]
        self.last_faces = []
        super().__init__(mode)

    def vertices(self, select: Select = Select.ALL) -> VertexList[Vertex]:
        """Return Vertices from Sketch

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            VertexList[Vertex]: Vertices extracted
        """
        vertex_list = []
        if select == Select.ALL:
            for edge in self.sketch.Edges():
                vertex_list.extend(edge.Vertices())
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return VertexList(set(vertex_list))

    def edges(self, select: Select = Select.ALL) -> ShapeList[Edge]:
        """Return Edges from Sketch

        Return either all or the edges created during the last operation.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: Edges extracted
        """
        if select == Select.ALL:
            edge_list = self.sketch.Edges()
        elif select == Select.LAST:
            edge_list = self.last_edges
        return ShapeList(edge_list)

    def faces(self, select: Select = Select.ALL) -> ShapeList[Face]:
        """Return Faces from Sketch

        Return either all or the faces created during the last operation.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Face]: Faces extracted
        """
        if select == Select.ALL:
            face_list = self.sketch.Faces()
        elif select == Select.LAST:
            face_list = self.last_faces
        return ShapeList(face_list)

    def consolidate_edges(self) -> Union[Wire, list[Wire]]:
        """Unify pending edges into one or more Wires"""
        wires = Wire.combine(self.pending_edges)
        return wires if len(wires) > 1 else wires[0]

    def _add_to_context(
        self, *objects: Union[Edge, Wire, Face, Compound], mode: Mode = Mode.ADD
    ):
        """Add objects to BuildSketch instance

        Core method to interface with BuildSketch instance. Input sequence of objects is
        parsed into lists of edges and faces. Edges are added to pending
        lists. Faces are combined with current sketch.

        Each operation generates a list of vertices, edges, and faces that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            objects (Union[Edge, Wire, Face, Compound]): sequence of objects to add
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Raises:
            ValueError: Nothing to subtract from
            ValueError: Nothing to intersect with
            ValueError: Invalid mode
        """
        if mode != Mode.PRIVATE:
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(compound.Faces())
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            for compound in filter(lambda o: isinstance(o, Wire), objects):
                new_edges.extend(compound.Edges())

            pre_vertices = set() if self.sketch is None else set(self.sketch.Vertices())
            pre_edges = set() if self.sketch is None else set(self.sketch.Edges())
            pre_faces = set() if self.sketch is None else set(self.sketch.Faces())
            if mode == Mode.ADD:
                if self.sketch is None:
                    self.sketch = Compound.makeCompound(new_faces)
                else:
                    self.sketch = self.sketch.fuse(*new_faces).clean()
            elif mode == Mode.SUBTRACT:
                if self.sketch is None:
                    raise RuntimeError("No sketch to subtract from")
                self.sketch = self.sketch.cut(*new_faces).clean()
            elif mode == Mode.INTERSECT:
                if self.sketch is None:
                    raise RuntimeError("No sketch to intersect with")
                self.sketch = self.sketch.intersect(*new_faces).clean()
            elif mode == Mode.REPLACE:
                self.sketch = Compound.makeCompound(new_faces).clean()
            else:
                raise ValueError(f"Invalid mode: {mode}")

            post_vertices = set(self.sketch.Vertices())
            post_edges = set(self.sketch.Edges())
            post_faces = set(self.sketch.Faces())
            self.last_vertices = list(post_vertices - pre_vertices)
            self.last_edges = list(post_edges - pre_edges)
            self.last_faces = list(post_faces - pre_faces)

            self.pending_edges.extend(new_edges)

    @classmethod
    def _get_context(cls) -> "BuildSketch":
        """Return the instance of the current builder"""
        return cls._current.get(None)


#
# Operations
#


class BoundingBoxSketch(Compound):
    """Sketch Operation: Bounding Box

    Add the 2D bounding boxes of the object sequence to sketch

    Args:
        objects (Shape): sequence of objects
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Shape,
        mode: Mode = Mode.ADD,
    ):
        new_faces = []
        for obj in objects:
            if isinstance(obj, Vertex):
                continue
            bounding_box = obj.BoundingBox()
            vertices = [
                (bounding_box.xmin, bounding_box.ymin),
                (bounding_box.xmin, bounding_box.ymax),
                (bounding_box.xmax, bounding_box.ymax),
                (bounding_box.xmax, bounding_box.ymin),
                (bounding_box.xmin, bounding_box.ymin),
            ]
            new_faces.append(
                Face.makeFromWires(Wire.makePolygon([Vector(v) for v in vertices]))
            )
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class BuildFace:
    """Sketch Operation: Build Face

    Build a face from the given perimeter edges

    Args:
        edges (Edge): sequence of perimeter edges
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(self, *edges: Edge, mode: Mode = Mode.ADD):
        outer_edges = edges if edges else BuildSketch._get_context().pending_edges
        pending_face = Face.makeFromWires(Wire.combine(outer_edges)[0])
        BuildSketch._get_context()._add_to_context(pending_face, mode)
        BuildSketch._get_context().pending_edges = []


class BuildHull:
    """Sketch Operation: Build Hull

    Build a face from the hull of the given edges

    Args:
        edges (Edge): sequence of edges to hull
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(self, *edges: Edge, mode: Mode = Mode.ADD):
        hull_edges = edges if edges else BuildSketch._get_context().pending_edges
        pending_face = find_hull(hull_edges)
        BuildSketch._get_context()._add_to_context(pending_face, mode)
        BuildSketch._get_context().pending_edges = []


class ChamferSketch(Compound):
    """Sketch Operation: Chamfer

    Chamfer the given sequence of vertices

    Args:
        vertices (Vertex): sequence of vertices to chamfer
        length (float): chamfer length
    """

    def __init__(self, *vertices: Vertex, length: float):
        new_faces = []
        # for face in BuildSketch.get_context().sketch.Faces():
        for face in BuildSketch._get_context().faces():
            vertices_in_face = filter(lambda v: v in face.Vertices(), vertices)
            if vertices_in_face:
                new_faces.append(face.chamfer2D(length, vertices_in_face))
            else:
                new_faces.append(face)
        new_sketch = Compound.makeCompound(new_faces)
        # BuildSketch.get_context().sketch = new_sketch
        BuildSketch._get_context()._add_to_context(new_sketch, mode=Mode.REPLACE)
        super().__init__(new_sketch.wrapped)


class FilletSketch(Compound):
    """Sketch Operation: Fillet

    Fillet the given sequence of vertices

    Args:
        vertices (Vertex): sequence of vertices to fillet
        radius (float): fillet radius
    """

    def __init__(self, *vertices: Vertex, radius: float):
        new_faces = []
        # for face in BuildSketch.get_context().sketch.Faces():
        for face in BuildSketch._get_context().faces():
            vertices_in_face = filter(lambda v: v in face.Vertices(), vertices)
            if vertices_in_face:
                new_faces.append(face.fillet2D(radius, vertices_in_face))
            else:
                new_faces.append(face)
        new_sketch = Compound.makeCompound(new_faces)
        # BuildSketch.get_context().sketch = new_sketch
        BuildSketch._get_context()._add_to_context(new_sketch, mode=Mode.REPLACE)
        super().__init__(new_sketch.wrapped)


class HexArrayToSketch:
    """Sketch Operation: Hex Array

    Creates a hexagon array of points and pushes them to locations.

    Args:
        diagonal: tip to tip size of hexagon ( must be > 0)
        xCount: number of points ( > 0 )
        yCount: number of points ( > 0 )
        center: If True, the array will be centered around the workplane center.
            If False, the lower corner will be on the reference point and the array will
            extend in the positive x and y directions. Can also use a 2-tuple to specify
            centering along each axis.

    Raises:
        ValueError: Spacing and count must be > 0
    """

    def __init__(
        self,
        diagonal: float,
        xCount: int,
        yCount: int,
        center: Union[bool, tuple[bool, bool]] = True,
    ):
        xSpacing = 3 * diagonal / 4
        ySpacing = diagonal * sqrt(3) / 2
        if xSpacing <= 0 or ySpacing <= 0 or xCount < 1 or yCount < 1:
            raise ValueError("Spacing and count must be > 0 ")

        if isinstance(center, bool):
            center = (center, center)

        lpoints = []  # coordinates relative to bottom left point
        for x in range(0, xCount, 2):
            for y in range(yCount):
                lpoints.append(Vector(xSpacing * x, ySpacing * y + ySpacing / 2))
        for x in range(1, xCount, 2):
            for y in range(yCount):
                lpoints.append(Vector(xSpacing * x, ySpacing * y + ySpacing))

        # shift points down and left relative to origin if requested
        offset = Vector()
        if center[0]:
            offset += Vector(-xSpacing * (xCount - 1) * 0.5, 0)
        if center[1]:
            offset += Vector(0, -ySpacing * (yCount - 1) * 0.5)
        lpoints = [x + offset for x in lpoints]

        # convert to locations
        new_locations = [Location(pt) for pt in lpoints]

        BuildSketch._get_context().locations = new_locations


class MirrorToSketch:
    """Sketch Operation: Mirror

    Add the mirror of the provided sequence of faces about the given axis to sketch.

    Args:
        objects (Union[Face,Compound]): sequence of faces to mirror
        axis (Axis, optional): axis to mirror about. Defaults to Axis.X.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Union[Face, Compound],
        axis: Axis = Axis.X,
        mode: Mode = Mode.ADD,
    ):
        new_faces = [obj for obj in objects if isinstance(obj, Face)]
        for compound in filter(lambda o: isinstance(o, Compound), objects):
            new_faces.extend(compound.Faces())
        mirrored_faces = Plane.named("XY").mirrorInPlane(new_faces, axis=axis.name)
        BuildSketch._get_context()._add_to_context(*mirrored_faces, mode=mode)


class Offset(Compound):
    """Sketch Operation: Offset

    Offset the given sequence of Faces or Compound of Faces. The kind parameter
    controls the shape of the transitions.

    Args:
        amount (float): positive values external, negative internal
        kind (Kind, optional): transition shape. Defaults to Kind.ARC.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Only Compounds of Faces valid
    """

    def __init__(
        self,
        *objects: Union[Face, Compound],
        amount: float,
        kind: Kind = Kind.ARC,
        mode: Mode = Mode.ADD,
    ):
        faces = []
        for obj in objects:
            if isinstance(obj, Compound):
                faces.extend(obj.Faces())
            elif isinstance(obj, Face):
                faces.append(obj)
            else:
                raise ValueError("Only Faces or Compounds are valid input types")

        new_faces = []
        for face in faces:
            new_faces.append(
                Face.makeFromWires(
                    face.outerWire().offset2D(amount, kind=kind.name.lower())[0]
                )
            )
            BuildSketch._get_context()._add_to_context(face, mode=mode)

        super().__init__(Compound.makeCompound(new_faces).wrapped)


class PolarArrayToSketch:
    """Sketch Operation: Polar Array

    Push a polar array of locations to BuildSketch

    Args:
        radius (float): array radius
        start_angle (float): angle to first point from +ve X axis
        stop_angle (float): angle to last point from +ve X axis
        count (int): Number of points to push
        rotate (bool, optional): Align locations with arc tangents. Defaults to True.

    Raises:
        ValueError: Count must be greater than or equal to 1
    """

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

        angle_step = (stop_angle - start_angle) / count

        # Note: rotate==False==0 so the location orientation doesn't change
        new_locations = [
            Location(
                Vector(radius, 0).rotateZ(start_angle + angle_step * i),
                Vector(0, 0, 1),
                rotate * angle_step * i,
            )
            for i in range(count)
        ]

        BuildSketch._get_context().locations = new_locations


class PushPointsToSketch:
    """Sketch Operation: Push Points

    Push sequence of locations to BuildSketch

    Args:
        pts (Union[VectorLike, Location]): sequence of points to push
    """

    def __init__(self, *pts: Union[VectorLike, Location]):
        new_locations = [
            Location(Vector(pt)) if not isinstance(pt, Location) else pt for pt in pts
        ]
        BuildSketch._get_context().locations = new_locations


class RectangularArrayToSketch:
    """Sketch Operation: Rectangular Array

    Push a rectangular array of locations to BuildSketch

    Args:
        x_spacing (float): horizontal spacing
        y_spacing (float): vertical spacing
        x_count (int): number of horizontal points
        y_count (int): number of vertical points

    Raises:
        ValueError: Either x or y count must be greater than or equal to one.
    """

    def __init__(self, x_spacing: float, y_spacing: float, x_count: int, y_count: int):
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

        BuildSketch._get_context().locations = new_locations


#
# Objects
#
class AddToSketch(Compound):
    """Sketch Object: Add Object to Sketch

    Add an object to the sketch. Edges and Wires are added to pending_edges.
    Compounds of Face are added to sketch.

    Args:
        objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of objects to add
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Compound],
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        new_objects = []
        for obj in objects:
            new_objects.extend(
                [
                    obj.rotate(Vector(0, 0, 0), Vector(0, 0, 1), rotation).moved(
                        location
                    )
                    for location in BuildSketch._get_context().locations
                ]
            )
        for obj in new_objects:
            BuildSketch._get_context()._add_to_context(obj, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_objects).wrapped)


class Circle(Compound):
    """Sketch Object: Circle

    Add circle(s) to the sketch.

    Args:
        radius (float): circle size
        centered (tuple[bool, bool], optional): center options. Defaults to (True, True).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        radius: float,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
        center_offset = Vector(
            0 if centered[0] else radius,
            0 if centered[1] else radius,
        )
        face = Face.makeFromWires(Wire.makeCircle(radius, *z_axis)).moved(
            Location(center_offset)
        )
        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Ellipse(Compound):
    """Sketch Object: Ellipse

    Add ellipse(s) to sketch.

    Args:
        x_radius (float): horizontal radius
        y_radius (float): vertical radius
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        centered (tuple[bool, bool], optional): center options. Defaults to (True, True).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        x_radius: float,
        y_radius: float,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
        face = Face.makeFromWires(
            Wire.makeEllipse(
                x_radius,
                y_radius,
                Vector(),
                Vector(0, 0, 1),
                Vector(1, 0, 0),
                rotation_angle=rotation,
            )
        )
        bounding_box = face.BoundingBox()
        center_offset = Vector(
            0 if centered[0] else bounding_box.xlen / 2,
            0 if centered[1] else bounding_box.ylen / 2,
        )
        face = face.moved(Location(center_offset))

        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Polygon(Compound):
    """Sketch Object: Polygon

    Add polygon(s) defined by given sequence of points to sketch.

    Args:
        pts (VectorLike): sequence of points defining the vertices of polygon
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        centered (tuple[bool, bool], optional): center options. Defaults to (True, True).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *pts: VectorLike,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
        poly_pts = [Vector(p) for p in pts]
        face = Face.makeFromWires(Wire.makePolygon(poly_pts)).rotate(*z_axis, rotation)
        bounding_box = face.BoundingBox()
        center_offset = Vector(
            0 if centered[0] else bounding_box.xlen / 2,
            0 if centered[1] else bounding_box.ylen / 2,
        )
        face = face.moved(Location(center_offset))
        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Rectangle(Compound):
    """Sketch Object: Rectangle

    Add rectangle(s) to sketch.

    Args:
        width (float): horizontal size
        height (float): vertical size
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        centered (tuple[bool, bool], optional): center options. Defaults to (True, True).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
        face = Face.makePlane(height, width).rotate(*z_axis, rotation)
        bounding_box = face.BoundingBox()
        center_offset = Vector(
            0 if centered[0] else bounding_box.xlen / 2,
            0 if centered[1] else bounding_box.ylen / 2,
        )
        face = face.moved(Location(center_offset))

        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class RegularPolygon(Compound):
    """Sketch Object: Regular Polygon

    Add regular polygon(s) to sketch.

    Args:
        radius (float): distance from origin to vertices
        side_count (int): number of polygon sides
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        centered (tuple[bool, bool], optional): center options. Defaults to (True, True).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        radius: float,
        side_count: int,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
        pts = [
            Vector(
                radius * sin(i * 2 * pi / side_count),
                radius * cos(i * 2 * pi / side_count),
            )
            for i in range(side_count + 1)
        ]
        face = Face.makeFromWires(Wire.makePolygon(pts)).rotate(*z_axis, rotation)
        bounding_box = face.BoundingBox()
        center_offset = Vector(
            0 if centered[0] else bounding_box.xlen / 2,
            0 if centered[1] else bounding_box.ylen / 2,
        )
        face = face.moved(Location(center_offset))

        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotArc(Compound):
    """Sketch Object: Arc Slot

    Add slot(s) following an arc to sketch.

    Args:
        arc (Union[Edge, Wire]): center line of slot
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: arc defined by a single edge is currently unsupported
    """

    def __init__(
        self,
        arc: Union[Edge, Wire],
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        if isinstance(arc, Edge):
            raise ValueError("Bug - Edges aren't supported by offset")
        # arc_wire = arc if isinstance(arc, Wire) else Wire.assembleEdges([arc])
        face = Face.makeFromWires(arc.offset2D(height / 2)[0]).rotate(*z_axis, rotation)
        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotCenterPoint(Compound):
    """Sketch Object: Center Point Slot

    Add a slot(s) defined by the center of the slot and the center of one of the
    circular arcs at the end. The other end will be generated to create a symmetric
    slot.

    Args:
        center (VectorLike): slot center point
        point (VectorLike): slot center of arc point
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        center: VectorLike,
        point: VectorLike,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        center_v = Vector(center)
        point_v = Vector(point)
        half_line = point_v - center_v
        face = Face.makeFromWires(
            Wire.combine(
                [
                    Edge.makeLine(point_v, center_v),
                    Edge.makeLine(center_v, center_v - half_line),
                ]
            )[0].offset2D(height / 2)[0]
        ).rotate(*z_axis, rotation)
        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotCenterToCenter(Compound):
    """Sketch Object: Center to Center points Slot

    Add slot(s) defined by the distance between the center of the two
    end arcs.

    Args:
        center_separation (float): distance between two arc centers
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        center_separation: float,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        face = Face.makeFromWires(
            Wire.assembleEdges(
                [
                    Edge.makeLine(Vector(-center_separation / 2, 0, 0), Vector()),
                    Edge.makeLine(Vector(), Vector(+center_separation / 2, 0, 0)),
                ]
            ).offset2D(height / 2)[0]
        ).rotate(*z_axis, rotation)
        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class SlotOverall(Compound):
    """Sketch Object: Center to Center points Slot

    Add slot(s) defined by the overall with of the slot.

    Args:
        width (float): overall width of the slot
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        face = Face.makeFromWires(
            Wire.assembleEdges(
                [
                    Edge.makeLine(Vector(-width / 2 + height / 2, 0, 0), Vector()),
                    Edge.makeLine(Vector(), Vector(+width / 2 - height / 2, 0, 0)),
                ]
            ).offset2D(height / 2)[0]
        ).rotate(*z_axis, rotation)
        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Text(Compound):
    """Sketch Object: Text

    Add text(s) to the sketch.

    Args:
        txt (str): text to be rendered
        fontsize (float): size of the font in model units
        font (str, optional): font name. Defaults to "Arial".
        font_path (str, optional): system path to font library. Defaults to None.
        font_style (Font_Style, optional): style. Defaults to Font_Style.REGULAR.
        halign (Halign, optional): horizontal alignment. Defaults to Halign.LEFT.
        valign (Valign, optional): vertical alignment. Defaults to Valign.CENTER.
        path (Union[Edge, Wire], optional): path for text to follow. Defaults to None.
        position_on_path (float, optional): the relative location on path to position the
            text, values must be between 0.0 and 1.0. Defaults to 0.0.
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        txt: str,
        fontsize: float,
        font: str = "Arial",
        font_path: str = None,
        font_style: FontStyle = FontStyle.REGULAR,
        halign: Halign = Halign.LEFT,
        valign: Valign = Valign.CENTER,
        path: Union[Edge, Wire] = None,
        position_on_path: float = 0.0,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ) -> Compound:
        text_string = Compound.make2DText(
            txt,
            fontsize,
            font,
            font_path,
            font_style.name.lower(),
            halign.name.lower(),
            valign.name.lower(),
            position_on_path,
            path,
        ).rotate(Vector(), Vector(0, 0, 1), rotation)
        new_compounds = [
            text_string.moved(location)
            for location in BuildSketch._get_context().locations
        ]
        new_faces = [face for compound in new_compounds for face in compound]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)


class Trapezoid(Compound):
    """Sketch Object: Trapezoid

    Add trapezoid(s) to the sketch.

    Args:
        width (float): horizontal width
        height (float): vertical height
        left_side_angle (float): angle defining shape
        right_side_angle (float, optional): if not provided, the trapezoid will be symmetric.
            Defaults to None.
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        centered (tuple[bool, bool], optional): center options. Defaults to (True, True).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        width: float,
        height: float,
        left_side_angle: float,
        right_side_angle: float = None,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
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
        face = Face.makeFromWires(Wire.makePolygon(pts)).rotate(*z_axis, rotation)
        bounding_box = face.BoundingBox()
        center_offset = Vector(
            0 if centered[0] else bounding_box.xlen / 2,
            0 if centered[1] else bounding_box.ylen / 2,
        )
        face = face.moved(Location(center_offset))
        new_faces = [
            face.moved(location) for location in BuildSketch._get_context().locations
        ]
        for face in new_faces:
            BuildSketch._get_context()._add_to_context(face, mode=mode)
        BuildSketch._get_context().locations = [Location(Vector())]
        super().__init__(Compound.makeCompound(new_faces).wrapped)
