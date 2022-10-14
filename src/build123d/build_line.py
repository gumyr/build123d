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
import inspect
from math import sin, cos, radians, sqrt
from typing import Union, Iterable
from .build_enums import Select, Mode
from .direct_api import (
    Edge,
    Wire,
    Vector,
    Compound,
    Location,
    VectorLike,
    ShapeList,
    Face,
    Plane,
    PlaneLike,
)
from .build_common import Builder, logger, validate_inputs


class BuildLine(Builder):
    """BuildLine

    Create lines (objects with length but not area or volume) from edges or wires.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    @property
    def _obj(self):
        return self.line

    @property
    def _obj_name(self):
        return "line"

    def __init__(
        self,
        *workplanes: Union[Face, PlaneLike, Location],
        mode: Mode = Mode.ADD,
    ):
        self.initial_planes = workplanes
        self.mode = mode
        self.line: Compound = None
        # self.locations: list[Location] = [Location(Vector())]
        super().__init__(*workplanes, mode=mode)

    def faces(self):
        """Override the base Builder class definition of faces()"""
        return NotImplementedError("faces() doesn't apply to BuildLine")

    def wires(self, select: Select = Select.ALL) -> ShapeList[Wire]:
        """Return Wires from Line

        Return a list of wires created from the edges in either all or those created
        during the last operation.

        Args:
            select (Select, optional): Wire selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Wire]: Wires extracted
        """
        if select == Select.ALL:
            wire_list = Wire.combine(self.line.edges())
        elif select == Select.LAST:
            wire_list = Wire.combine(self.last_edges)
        return ShapeList(wire_list)

    def _add_to_context(self, *objects: Union[Edge, Wire], mode: Mode = Mode.ADD):
        """Add objects to BuildSketch instance

        Core method to interface with BuildLine instance. Input sequence of edges are
        combined with current line.

        Each operation generates a list of vertices and edges that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            objects (Edge): sequence of edges to add
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.
        """
        if mode != Mode.PRIVATE:
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            new_wires = [obj for obj in objects if isinstance(obj, Wire)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_edges.extend(compound.get_type(Edge))
                new_wires.extend(compound.get_type(Wire))
            for wire in new_wires:
                new_edges.extend(wire.edges())
            if new_edges:
                logger.debug(
                    "Add %d Edge(s) into line with Mode=%s", len(new_edges), mode
                )

            if mode == Mode.ADD:
                if self.line:
                    self.line = self.line.fuse(*new_edges)
                else:
                    self.line = Compound.make_compound(new_edges)
            elif mode == Mode.REPLACE:
                self.line = Compound.make_compound(new_edges)
            self.last_edges = new_edges
            self.last_vertices = list(
                set(v for e in self.last_edges for v in e.vertices())
            )

    @classmethod
    def _get_context(cls) -> "BuildLine":
        """Return the instance of the current builder"""
        logger.info(
            "Context requested by %s",
            type(inspect.currentframe().f_back.f_locals["self"]).__name__,
        )
        return cls._current.get(None)


#
# Operations
#


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
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)

        points = []
        if abs(arc_size) >= 360:
            arc = Edge.make_circle(
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
            arc = Edge.make_three_point_arc(*points)

        context._add_to_context(arc, mode=mode)
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
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
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
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        helix = Wire.make_helix(
            pitch, height, radius, Vector(center), Vector(direction), arc_size, lefhand
        )
        context._add_to_context(*helix.edges(), mode=mode)
        super().__init__(helix.wrapped)


class Line(Edge):
    """Line Object: Line

    Add a straight line defined by two end points.

    Args:
        pts (VectorLike): sequence of two points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Two point not provided
    """

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADD):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        if len(pts) != 2:
            raise ValueError("Line requires two pts")

        lines_pts = [Vector(p) for p in pts]

        new_edge = Edge.make_line(lines_pts[0], lines_pts[1])
        context._add_to_context(new_edge, mode=mode)
        super().__init__(new_edge.wrapped)


class PolarLine(Edge):
    """Line Object: Polar Line

    Add line defined by a start point, length and angle.

    Args:
        start (VectorLike): start point
        length (float): line length
        angle (float, optional): angle from +v X axis. Defaults to None.
        direction (VectorLike, optional): vector direction. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Either angle or direction must be provided
    """

    def __init__(
        self,
        start: VectorLike,
        length: float,
        angle: float = None,
        direction: VectorLike = None,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        if angle is not None:
            x_val = cos(radians(angle)) * length
            y_val = sin(radians(angle)) * length
            new_edge = Edge.make_line(
                Vector(start), Vector(start) + Vector(x_val, y_val, 0)
            )
        elif direction is not None:
            new_edge = Edge.make_line(
                Vector(start), Vector(start) + Vector(direction).normalized() * length
            )
        else:
            raise ValueError("Either angle or direction must be provided")

        context._add_to_context(new_edge, mode=mode)
        super().__init__(new_edge.wrapped)


class Polyline(Wire):
    """Line Object: Polyline

    Add a sequence of straight lines defined by successive point pairs.

    Args:
        pts (VectorLike): sequence of three or more points
        close (bool, optional): close by generating an extra Edge. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Three or more points not provided
    """

    def __init__(self, *pts: VectorLike, close: bool = False, mode: Mode = Mode.ADD):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)

        if len(pts) < 3:
            raise ValueError("polyline requires three or more pts")

        lines_pts = [Vector(p) for p in pts]

        new_edges = [
            Edge.make_line(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]
        if close and (new_edges[0] @ 0 - new_edges[-1] @ 1).length > 1e-5:
            new_edges.append(Edge.make_line(new_edges[-1] @ 1, new_edges[0] @ 0))

        context._add_to_context(*new_edges, mode=mode)
        super().__init__(Wire.combine(new_edges)[0].wrapped)


class RadiusArc(Edge):
    """Line Object: Radius Arc

    Add an arc defined by two end points and a radius

    Args:
        start_point (VectorLike): start
        end_point (VectorLike): end
        radius (float): radius
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Insufficient radius to connect end points
    """

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        radius: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        start = Vector(start_point)
        end = Vector(end_point)

        # Calculate the sagitta from the radius
        length = end.sub(start).length / 2.0
        try:
            sagitta = abs(radius) - sqrt(radius**2 - length**2)
        except ValueError as exception:
            raise ValueError(
                "Arc radius is not large enough to reach the end point."
            ) from exception

        # Return a sagitta arc
        if radius > 0:
            arc = SagittaArc(start, end, sagitta, mode=Mode.PRIVATE)
        else:
            arc = SagittaArc(start, end, -sagitta, mode=Mode.PRIVATE)

        context._add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class SagittaArc(Edge):
    """Line Object: Sagitta Arc

    Add an arc defined by two points and the height of the arc (sagitta).

    Args:
        start_point (VectorLike): start
        end_point (VectorLike): end
        sagitta (float): arc height
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        sagitta: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        start = Vector(start_point)
        end = Vector(end_point)
        mid_point = (end + start) * 0.5

        sagitta_vector = (end - start).normalized() * abs(sagitta)
        if sagitta > 0:
            sagitta_vector.X, sagitta_vector.Y = (
                -sagitta_vector.Y,
                sagitta_vector.X,
            )  # Rotate sagitta_vector +90 deg
        else:
            sagitta_vector.X, sagitta_vector.Y = (
                sagitta_vector.Y,
                -sagitta_vector.X,
            )  # Rotate sagitta_vector -90 deg

        sag_point = mid_point + sagitta_vector

        arc = ThreePointArc(start, sag_point, end, mode=Mode.PRIVATE)
        context._add_to_context(arc, mode=mode)
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
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *pts: VectorLike,
        tangents: Iterable[VectorLike] = None,
        tangent_scalars: Iterable[float] = None,
        periodic: bool = False,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        spline_pts = [Vector(pt) for pt in pts]
        if tangents:
            spline_tangents = [Vector(tangent) for tangent in tangents]
        else:
            spline_tangents = None

        if tangents and not tangent_scalars:
            scalars = [1.0] * len(tangents)
        else:
            scalars = tangent_scalars

        spline = Edge.make_spline(
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
        context._add_to_context(spline, mode=mode)
        super().__init__(spline.wrapped)


class TangentArc(Edge):
    """Line Object: Tangent Arc

    Add an arc defined by two points and a tangent.

    Args:
        pts (VectorLike): sequence of two points
        tangent (VectorLike): tangent to constrain arc
        tangent_from_first (bool, optional): apply tangent to first point. Note, applying
            tangent to end point will flip the orientation of the arc. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Two points are required
    """

    def __init__(
        self,
        *pts: VectorLike,
        tangent: VectorLike,
        tangent_from_first: bool = True,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        arc_pts = [Vector(p) for p in pts]
        if len(arc_pts) != 2:
            raise ValueError("tangent_arc requires two points")
        arc_tangent = Vector(tangent)

        point_indices = (0, -1) if tangent_from_first else (-1, 0)
        arc = Edge.make_tangent_arc(
            arc_pts[point_indices[0]], arc_tangent, arc_pts[point_indices[1]]
        )

        context._add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class ThreePointArc(Edge):
    """Line Object: Three Point Arc

    Add an arc generated by three points.

    Args:
        pts (VectorLike): sequence of three points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Three points must be provided
    """

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADD):
        context: BuildLine = BuildLine._get_context()
        validate_inputs(self, context)
        if len(pts) != 3:
            raise ValueError("ThreePointArc requires three points")
        points = [Vector(p) for p in pts]
        arc = Edge.make_three_point_arc(*points)
        context._add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)
