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
import copy
import inspect
from math import sin, cos, radians, sqrt, copysign
from typing import Union, Iterable
from build123d.build_enums import AngularDirection, LengthMode, Mode, Select
from build123d.direct_api import (
    Axis,
    Edge,
    Wire,
    Vector,
    Compound,
    Location,
    VectorLike,
    ShapeList,
    Face,
    Plane,
)
from build123d.build_common import Builder, WorkplaneList, logger


class BuildLine(Builder):
    """BuildLine

    Create lines (objects with length but not area or volume) from edges or wires.

    BuildLine only works with a single workplane which is used to convert tuples
    as inputs to global coordinates. For example:

    .. code::

        with BuildLine(Plane.YZ) as radius_arc:
            RadiusArc((1, 2), (2, 1), 1)

    creates an arc from global points (0, 1, 2) to (0, 2, 1). Note that points
    entered as Vector(x, y, z) are considered global and are not localized.

    The workplane is also used to define planes parallel to the workplane that
    arcs are created on.

    Args:
        workplane (Union[Face, Plane, Location], optional): plane used when local
            coordinates are used and when creating arcs. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    @staticmethod
    def _tag() -> str:
        return "BuildLine"

    @property
    def _obj(self):
        return self.line

    @property
    def _obj_name(self):
        return "line"

    def __init__(
        self,
        workplane: Union[Face, Plane, Location] = Plane.XY,
        mode: Mode = Mode.ADD,
    ):
        self.initial_plane = workplane
        self.mode = mode
        self.line: Compound = None
        super().__init__(workplane, mode=mode)

    def faces(self, *args):
        """faces() not implemented"""
        raise NotImplementedError("faces() doesn't apply to BuildLine")

    def solids(self, *args):
        """solids() not implemented"""
        raise NotImplementedError("solids() doesn't apply to BuildLine")

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
            self.last_edges = ShapeList(new_edges)
            self.last_vertices = ShapeList(
                set(v for e in self.last_edges for v in e.vertices())
            )

    @classmethod
    def _get_context(cls, caller=None) -> "BuildLine":
        """Return the instance of the current builder"""
        logger.info(
            "Context requested by %s",
            type(inspect.currentframe().f_back.f_locals["self"]).__name__,
        )

        result = cls._current.get(None)
        if caller is not None and result is None:
            if hasattr(caller, "_applies_to"):
                raise RuntimeError(
                    f"No valid context found, use one of {caller._applies_to}"
                )
            raise RuntimeError("No valid context found")

        return result


#
# Operations
#


#
# Objects
#
class Bezier(Edge):
    """Line Object: Bezier Curve

    Create a rational (with weights) or non-rational bezier curve.  The first and last
    control points represent the start and end of the curve respectively.  If weights
    are provided, there must be one provided for each control point.

    Args:
        cntl_pnts (sequence[VectorLike]): points defining the curve
        weights (list[float], optional): control point weights list. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        *cntl_pnts: VectorLike,
        weights: list[float] = None,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        polls = WorkplaneList.localize(*cntl_pnts)
        curve = Edge.make_bezier(*polls, weights=weights)

        context._add_to_context(curve, mode=mode)
        super().__init__(curve.wrapped)


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

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        center_point = WorkplaneList.localize(center)
        circle_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])
        circle_workplane.origin = center_point
        arc_direction = (
            AngularDirection.COUNTER_CLOCKWISE
            if arc_size > 0
            else AngularDirection.CLOCKWISE
        )
        if abs(arc_size) >= 360:
            arc = Edge.make_circle(
                radius,
                circle_workplane,
                start_angle=start_angle,
                end_angle=start_angle,
                angular_direction=arc_direction,
            )
        else:
            points = []
            points.append(
                Vector(center)
                + radius * Vector(cos(radians(start_angle)), sin(radians(start_angle)))
            )
            points.append(
                Vector(center)
                + radius
                * Vector(
                    cos(radians(start_angle + arc_size / 2)),
                    sin(radians(start_angle + arc_size / 2)),
                )
            )
            points.append(
                Vector(center)
                + radius
                * Vector(
                    cos(radians(start_angle + arc_size)),
                    sin(radians(start_angle + arc_size)),
                )
            )
            points = WorkplaneList.localize(*points)
            arc = Edge.make_three_point_arc(*points)

        context._add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class EllipticalStartArc(Edge):
    """Line Object: Elliptical Start Arc

    Makes an arc of an ellipse from the start point.

    Args:
        start (VectorLike): initial point of arc
        end (VectorLike): final point of arc
        x_radius (float): semi-major radius
        y_radius (float): semi-minor radius
        rotation (float, optional): the angle from the x-axis of the plane to the x-axis
            of the ellipse. Defaults to 0.0.
        large_arc (bool, optional): True if the arc spans greater than 180 degrees.
            Defaults to True.
        sweep_flag (bool, optional): False if the line joining center to arc sweeps through
            decreasing angles, or True if it sweeps through increasing angles. Defaults to True.
        plane (Plane, optional): base plane. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        start: VectorLike,
        end: VectorLike,
        x_radius: float,
        y_radius: float,
        rotation: float = 0.0,
        large_arc: bool = False,
        sweep_flag: bool = True,
        plane: Plane = Plane.XY,
        mode: Mode = Mode.ADD,
    ) -> Edge:
        # Debugging incomplete
        raise RuntimeError("Implementation incomplete")

        # context: BuildLine = BuildLine._get_context(self)
        # context.validate_inputs(self)

        # # Calculate the ellipse parameters based on the SVG implementation here:
        # #   https://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes

        # self.start_pnt = Vector(start)
        # self.end_pnt = Vector(end)
        # # Eq. 5.1
        # self.mid_prime: Vector = ((self.start_pnt - self.end_pnt) * 0.5).rotate(
        #     Axis.Z, -rotation
        # )

        # # Eq. 5.2
        # self.center_scalar = (-1 if large_arc == sweep_flag else 1) * sqrt(
        #     (
        #         x_radius**2 * y_radius**2
        #         - x_radius**2 * (self.mid_prime.Y**2)
        #         - y_radius**2 * (self.mid_prime.X**2)
        #     )
        #     / (
        #         x_radius**2 * (self.mid_prime.Y**2)
        #         + y_radius**2 * (self.mid_prime.X**2)
        #     )
        # )
        # self.center_prime = (
        #     Vector(
        #         x_radius * self.mid_prime.Y / y_radius,
        #         -y_radius * self.mid_prime.X / x_radius,
        #     )
        #     * self.center_scalar
        # )

        # # Eq. 5.3
        # self.center_pnt: Vector = self.center_prime.rotate(Axis.Z, rotation) + (
        #     ((self.start_pnt + self.end_pnt) * 0.5)
        # )

        # plane.set_origin2d(self.center_pnt.X, self.center_pnt.Y)
        # plane = plane.rotated((0, 0, rotation))
        # self.start_angle = (
        #     plane.x_dir.get_signed_angle(self.start_pnt - self.center_pnt, plane.z_dir)
        #     + 360
        # ) % 360
        # self.end_angle = (
        #     plane.x_dir.get_signed_angle(self.end_pnt - self.center_pnt, plane.z_dir)
        #     + 360
        # ) % 360
        # self.angular_direction = (
        #     AngularDirection.COUNTER_CLOCKWISE
        #     if self.start_angle > self.end_angle
        #     else AngularDirection.CLOCKWISE
        # )

        # curve = Edge.make_ellipse(
        #     x_radius=x_radius,
        #     y_radius=y_radius,
        #     plane=plane,
        #     start_angle=self.start_angle,
        #     end_angle=self.end_angle,
        #     angular_direction=self.angular_direction,
        # )

        # context._add_to_context(curve, mode=mode)
        # super().__init__(curve.wrapped)

        # context: BuildLine = BuildLine._get_context(self)


class EllipticalCenterArc(Edge):
    """Line Object: Elliptical Center Arc

    Makes an arc of an ellipse from a center point.

    Args:
        center (VectorLike): ellipse center
        x_radius (float): x radius of the ellipse (along the x-axis of plane)
        y_radius (float): y radius of the ellipse (along the y-axis of plane)
        start_angle (float, optional): Defaults to 0.0.
        end_angle (float, optional): Defaults to 90.0.
        rotation (float, optional): amount to rotate arc. Defaults to 0.0.
        angular_direction (AngularDirection, optional): arc direction.
            Defaults to AngularDirection.COUNTER_CLOCKWISE.
        plane (Plane, optional): base plane. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        center: VectorLike,
        x_radius: float,
        y_radius: float,
        start_angle: float = 0.0,
        end_angle: float = 90.0,
        rotation: float = 0.0,
        angular_direction: AngularDirection = AngularDirection.COUNTER_CLOCKWISE,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        center_pnt = WorkplaneList.localize(center)
        ellipse_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])
        ellipse_workplane.origin = center_pnt
        curve = Edge.make_ellipse(
            x_radius=x_radius,
            y_radius=y_radius,
            plane=ellipse_workplane,
            start_angle=start_angle,
            end_angle=end_angle,
            angular_direction=angular_direction,
        ).rotate(
            Axis(ellipse_workplane.origin, ellipse_workplane.z_dir.to_dir()), rotation
        )

        context._add_to_context(curve, mode=mode)
        super().__init__(curve.wrapped)


class Helix(Wire):
    """Line Object: Helix

    Add a helix to the line.

    Args:
        pitch (float): distance between successive loops
        height (float): helix size
        radius (float): helix radius
        center (VectorLike, optional): center point. Defaults to (0, 0, 0).
        direction (VectorLike, optional): direction of central axis. Defaults to (0, 0, 1).
        cone_angle (float, optional): conical angle. Defaults to 0.
        lefthand (bool, optional): left handed helix. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        pitch: float,
        height: float,
        radius: float,
        center: VectorLike = (0, 0, 0),
        direction: VectorLike = (0, 0, 1),
        cone_angle: float = 0,
        lefthand: bool = False,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        center_pnt = WorkplaneList.localize(center)
        helix = Wire.make_helix(
            pitch, height, radius, center_pnt, direction, cone_angle, lefthand
        )
        context._add_to_context(*helix.edges(), mode=mode)
        super().__init__(helix.wrapped)


class JernArc(Edge):
    """JernArc

    Circular tangent arc with given radius and arc_size

    Args:
        start (VectorLike): start point
        tangent (VectorLike): tangent at start point
        radius (float): arc radius
        arc_size (float): arc size in degrees (negative to change direction)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        start: VectorLike,
        tangent: VectorLike,
        radius: float,
        arc_size: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        start = WorkplaneList.localize(start)
        self.start = start
        start_tangent = WorkplaneList.localize(tangent).normalized()
        jern_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])
        jern_workplane.origin = start

        arc_direction = copysign(1.0, arc_size)
        self.center_point = start + start_tangent.rotate(
            Axis(start, jern_workplane.z_dir), arc_direction * 90
        ) * abs(radius)
        self.end_of_arc = self.center_point + (start - self.center_point).rotate(
            Axis(start, jern_workplane.z_dir), arc_size
        )
        arc = Edge.make_tangent_arc(start, start_tangent, self.end_of_arc)

        context._add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class Line(Edge):
    """Line Object: Line

    Add a straight line defined by two end points.

    Args:
        pts (VectorLike): sequence of two points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Two point not provided
    """

    _applies_to = [BuildLine._tag()]

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADD):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        if len(pts) != 2:
            raise ValueError("Line requires two pts")
        pts = WorkplaneList.localize(*pts)

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
        angle (float): angle from the local "X" axis.
        length_mode (LengthMode, optional): length value specifies a diagonal, horizontal
            or vertical value. Defaults to LengthMode.DIAGONAL
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Either angle or direction must be provided
    """

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        start: VectorLike,
        length: float,
        angle: float = None,
        direction: VectorLike = None,
        length_mode: LengthMode = LengthMode.DIAGONAL,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        start = WorkplaneList.localize(start)
        if direction:
            direction = WorkplaneList.localize(direction)
            angle = Vector(1, 0, 0).get_angle(direction)
        elif angle:
            direction = (
                WorkplaneList._get_context()
                .workplanes[0]
                .x_dir.rotate(
                    Axis((0, 0, 0), WorkplaneList._get_context().workplanes[0].z_dir),
                    angle,
                )
            )
        else:
            raise ValueError("Either angle or direction must be provided")

        if length_mode == LengthMode.DIAGONAL:
            length_vector = direction * length
        elif length_mode == LengthMode.HORIZONTAL:
            length_vector = direction * (length / cos(radians(angle)))
        elif length_mode == LengthMode.VERTICAL:
            length_vector = direction * (length / sin(radians(angle)))

        new_edge = Edge.make_line(start, start + WorkplaneList.localize(length_vector))

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

    _applies_to = [BuildLine._tag()]

    def __init__(self, *pts: VectorLike, close: bool = False, mode: Mode = Mode.ADD):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        if len(pts) < 3:
            raise ValueError("polyline requires three or more pts")

        lines_pts = WorkplaneList.localize(*pts)

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

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        radius: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        start, end = WorkplaneList.localize(start_point, end_point)
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

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        sagitta: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        start, end = WorkplaneList.localize(start_point, end_point)
        mid_point = (end + start) * 0.5
        sagitta_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])
        sagitta_vector: Vector = (end - start).normalized() * abs(sagitta)
        sagitta_vector = sagitta_vector.rotate(
            Axis(sagitta_workplane.origin, sagitta_workplane.z_dir),
            90 if sagitta > 0 else -90,
        )

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

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        *pts: VectorLike,
        tangents: Iterable[VectorLike] = None,
        tangent_scalars: Iterable[float] = None,
        periodic: bool = False,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        spline_pts = WorkplaneList.localize(*pts)

        if tangents:
            spline_tangents = [
                WorkplaneList.localize(tangent).normalized() for tangent in tangents
            ]
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

    _applies_to = [BuildLine._tag()]

    def __init__(
        self,
        *pts: VectorLike,
        tangent: VectorLike,
        tangent_from_first: bool = True,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        if len(pts) != 2:
            raise ValueError("tangent_arc requires two points")
        arc_pts = WorkplaneList.localize(*pts)
        arc_tangent = WorkplaneList.localize(tangent).normalized()

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

    _applies_to = [BuildLine._tag()]

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADD):
        context: BuildLine = BuildLine._get_context(self)
        context.validate_inputs(self)

        if len(pts) != 3:
            raise ValueError("ThreePointArc requires three points")
        points = WorkplaneList.localize(*pts)
        arc = Edge.make_three_point_arc(*points)
        context._add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)
