"""
BuildLine

name: build_line.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build lines in three dimensional space.

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
from math import sin, cos, radians, sqrt
from typing import Union, Iterable
from cadquery import (
    Edge,
    Wire,
    Vector,
    Vertex,
    Plane,
)
from cadquery.occ_impl.shapes import VectorLike
import cq_warehouse.extensions
from build123d_common import *
from build_sketch import BuildSketch
from build_part import BuildPart


class BuildLine:
    """BuildLine

    Create lines (objects with length but not area or volume) from edges or wires.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    @property
    def line_as_wire(self) -> Union[Wire, list[Wire]]:
        """Unify edges into one or more Wires"""
        wires = Wire.combine(self.line)
        return wires if len(wires) > 1 else wires[0]

    def __init__(self, mode: Mode = Mode.ADDITION):
        self.line = []
        self.tags: dict[str, Edge] = {}
        self.mode = mode
        self.last_vertices = []
        self.last_edges = []

    def __enter__(self):
        """Upon entering BuildLine, add current BuildLine instance to context stack"""
        context_stack.append(self)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting BuildLine, transfer sketch to parent BuildSketch | BuildPart if available"""
        context_stack.pop()
        if context_stack:
            if isinstance(context_stack[-1], BuildSketch):
                BuildSketch.get_context().add_to_context(*self.line, mode=self.mode)
            elif isinstance(context_stack[-1], BuildPart):
                BuildPart.get_context().add_to_context(*self.line, mode=self.mode)

    def vertices(self, select: Select = Select.ALL) -> list[Vertex]:
        """Return Vertices from Line

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            VertexList[Vertex]: Vertices extracted
        """
        if select == Select.ALL:
            vertex_list = []
            for edge in self.line:
                vertex_list.extend(edge.Vertices())
            vertex_list = list(set(vertex_list))
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return vertex_list

    def edges(self, select: Select = Select.ALL) -> list[Edge]:
        """Return Edges from Line

        Return either all or the edges created during the last operation.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: Edges extracted
        """
        if select == Select.ALL:
            edge_list = self.line
        elif select == Select.LAST:
            edge_list = self.last_edges
        return edge_list

    @staticmethod
    def add_to_context(*edges: Edge, mode: Mode = Mode.ADDITION):
        """Add objects to BuildSketch instance

        Core method to interface with BuildLine instance. Input sequence of edges are
        combined with current line.

        Each operation generates a list of vertices and edges that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            edges (Edge): sequence of edges to add
            mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
        """
        if context_stack and mode != Mode.PRIVATE:
            for edge in edges:
                edge.forConstruction = mode == Mode.CONSTRUCTION
                context_stack[-1].line.append(edge)
            context_stack[-1].last_edges = edges
            context_stack[-1].last_vertices = list(
                set(v for e in edges for v in e.Vertices())
            )

    @staticmethod
    def get_context() -> "BuildLine":
        """Return the current BuildLine instance. Used by Object and Operation
        classes to refer to the current context."""
        return context_stack[-1]


#
# Operations
#
class MirrorToLine:
    """Line Operation: Mirror

    Add the mirror of the provided sequence of edges about the given axis to line.

    Args:
        edges (Edge): sequence of edges to mirror
        axis (Axis, optional): axis to mirror about. Defaults to Axis.X.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(self, *edges: Edge, axis: Axis = Axis.X, mode: Mode = Mode.ADDITION):
        mirrored_edges = Plane.named("XY").mirrorInPlane(edges, axis=axis.name)
        BuildLine.add_to_context(*mirrored_edges, mode=mode)


#
# Objects
#
class CenterArc(Edge):
    """Line Object: Center Arc

    Add center arc to the line.

    Args:
        center (VectorLike): center point of arc
        radius (float): arc radius
        start_angle (float): arc staring angle
        arc_size (float): arc size
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float,
        mode: Mode = Mode.ADDITION,
    ):
        points = []
        if abs(arc_size) >= 360:
            arc = Edge.makeCircle(
                radius,
                center,
                angle1=start_angle,
                angle2=start_angle,
                orientation=arc_size > 0,
            )
        else:

            center_point = Vector(center)
            points.append(
                center_point
                + radius * Vector(cos(radians(start_angle)), sin(radians(start_angle)))
            )
            points.append(
                center_point
                + radius
                * Vector(
                    cos(radians(start_angle + arc_size / 2)),
                    sin(radians(start_angle + arc_size / 2)),
                )
            )
            points.append(
                center_point
                + radius
                * Vector(
                    cos(radians(start_angle + arc_size)),
                    sin(radians(start_angle + arc_size)),
                )
            )
            arc = Edge.makeThreePointArc(*points)

        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class Helix(Wire):
    """Line Object: Helix

    Add a helix to the line.

    Args:
        pitch (float): distance between successive loops
        height (float): helix size
        radius (float): helix radius
        center (VectorLike, optional): center point. Defaults to (0, 0, 0).
        direction (VectorLike, optional): direction of central axis. Defaults to (0, 0, 1).
        arc_size (float, optional): rotational angle. Defaults to 360.
        lefhand (bool, optional): left handed helix. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        pitch: float,
        height: float,
        radius: float,
        center: VectorLike = (0, 0, 0),
        direction: VectorLike = (0, 0, 1),
        arc_size: float = 360,
        lefhand: bool = False,
        mode: Mode = Mode.ADDITION,
    ):
        helix = Wire.makeHelix(
            pitch, height, radius, Vector(center), Vector(direction), arc_size, lefhand
        )
        BuildLine.add_to_context(*helix.Edges(), mode=mode)
        super().__init__(helix.wrapped)


class Line(Edge):
    """Line Object: Line

    Add a straight line defined by two end points.

    Args:
        pts (VectorLike): sequence of two points
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.

    Raises:
        ValueError: Two point not provided
    """

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) != 2:
            raise ValueError("Line requires two pts")

        lines_pts = [Vector(p) for p in pts]

        new_edge = Edge.makeLine(lines_pts[0], lines_pts[1])
        BuildLine.add_to_context(new_edge, mode=mode)
        super().__init__(new_edge.wrapped)


class PolarLine(Edge):
    """Line Object: Polar Line

    Add line defined by a start point, length and angle.

    Args:
        start (VectorLike): start point
        length (float): line length
        angle (float, optional): angle from +v X axis. Defaults to None.
        direction (VectorLike, optional): vector direction. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.

    Raises:
        ValueError: Either angle or direction must be provided
    """

    def __init__(
        self,
        start: VectorLike,
        length: float,
        angle: float = None,
        direction: VectorLike = None,
        mode: Mode = Mode.ADDITION,
    ):
        if angle is not None:
            x = cos(radians(angle)) * length
            y = sin(radians(angle)) * length
            new_edge = Edge.makeLine(Vector(start), Vector(start) + Vector(x, y, 0))
        elif direction is not None:
            new_edge = Edge.makeLine(
                Vector(start), Vector(start) + Vector(direction).normalized() * length
            )
        else:
            raise ValueError("Either angle or direction must be provided")

        BuildLine.add_to_context(new_edge, mode=mode)
        super().__init__(new_edge.wrapped)


class Polyline(Wire):
    """Line Object: Polyline

    Add a sequence of straight lines defined by successive point pairs.

    Args:
        pts (VectorLike): sequence of three or more points
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.

    Raises:
        ValueError: Three or more points not provided
    """

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) < 3:
            raise ValueError("polyline requires three or more pts")

        lines_pts = [Vector(p) for p in pts]

        new_edges = [
            Edge.makeLine(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]
        BuildLine.add_to_context(*new_edges, mode=mode)
        super().__init__(Wire.combine(new_edges)[0].wrapped)


class RadiusArc(Edge):
    """Line Object: Radius Arc

    Add an arc defined by two end points and a radius

    Args:
        start_point (VectorLike): start
        end_point (VectorLike): end
        radius (float): radius
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.

    Raises:
        ValueError: Insufficient radius to connect end points
    """

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        radius: float,
        mode: Mode = Mode.ADDITION,
    ):
        start = Vector(start_point)
        end = Vector(end_point)

        # Calculate the sagitta from the radius
        length = end.sub(start).Length / 2.0
        try:
            sagitta = abs(radius) - sqrt(radius**2 - length**2)
        except ValueError as e:
            raise ValueError(
                "Arc radius is not large enough to reach the end point."
            ) from e

        # Return a sagitta arc
        if radius > 0:
            arc = SagittaArc(start, end, sagitta, mode=Mode.PRIVATE)
        else:
            arc = SagittaArc(start, end, -sagitta, mode=Mode.PRIVATE)

        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class SagittaArc(Edge):
    """Line Object: Sagitta Arc

    Add an arc defined by two points and the height of the arc (sagitta).

    Args:
        start_point (VectorLike): start
        end_point (VectorLike): end
        sagitta (float): arc height
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        sagitta: float,
        mode: Mode = Mode.ADDITION,
    ):
        start = Vector(start_point)
        end = Vector(end_point)
        mid_point = (end + start) * 0.5

        sagitta_vector = (end - start).normalized() * abs(sagitta)
        if sagitta > 0:
            sagitta_vector.x, sagitta_vector.y = (
                -sagitta_vector.y,
                sagitta_vector.x,
            )  # Rotate sagitta_vector +90 deg
        else:
            sagitta_vector.x, sagitta_vector.y = (
                sagitta_vector.y,
                -sagitta_vector.x,
            )  # Rotate sagitta_vector -90 deg

        sag_point = mid_point + sagitta_vector

        arc = ThreePointArc(start, sag_point, end, mode=Mode.PRIVATE)
        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class Spline(Edge):
    """Line Object: Spline

    Add a spline through the provided points optionally constrained by tangents.

    Args:
        pts (VectorLike): sequence of two or more points
        tangents (Iterable[VectorLike], optional): tangents at end points. Defaults to None.
        tangent_scalars (Iterable[float], optional): change shape by amplifying tangent.
            Defaults to None.
        periodic (bool, optional): make the spline periodic. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        *pts: VectorLike,
        tangents: Iterable[VectorLike] = None,
        tangent_scalars: Iterable[float] = None,
        periodic: bool = False,
        mode: Mode = Mode.ADDITION,
    ):
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
        BuildLine.add_to_context(spline, mode=mode)
        super().__init__(spline.wrapped)


class TangentArc(Edge):
    """Line Object: Tangent Arc

    Add an arc defined by two points and a tangent.

    Args:
        pts (VectorLike): sequence of two points
        tangent (VectorLike): tanget to constrain arc
        tangent_from_first (bool, optional): apply tangent to first point. Note, applying
            tangent to end point will flip the orientation of the arc. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.

    Raises:
        ValueError: Two points are required
    """

    def __init__(
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

        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class ThreePointArc(Edge):
    """Line Object: Three Point Arc

    Add an arc generated by three points.

    Args:
        pts (VectorLike): sequence of three points
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.

    Raises:
        ValueError: Three points must be provided
    """

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) != 3:
            raise ValueError("ThreePointArc requires three points")
        points = [Vector(p) for p in pts]
        arc = Edge.makeThreePointArc(*points)
        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)
