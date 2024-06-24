"""
Curve Objects

name: objects_curve.py
by:   Gumyr
date: March 22nd 2023

desc:
    This python module contains objects (classes) that create 1D Curves.

license:

    Copyright 2023 Gumyr

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

from __future__ import annotations

import copy
import warnings
from math import copysign, cos, radians, sin, sqrt
from scipy.optimize import minimize
from typing import Iterable, Union

from build123d.build_common import WorkplaneList, flatten_sequence, validate_inputs
from build123d.build_enums import AngularDirection, GeomType, Keep, LengthMode, Mode
from build123d.build_line import BuildLine
from build123d.geometry import Axis, Plane, Vector, VectorLike, TOLERANCE
from build123d.topology import Edge, Face, Wire, Curve


class BaseLineObject(Wire):
    """BaseLineObject

    Base class for all BuildLine objects

    Args:
        curve (Union[Edge,Wire]): edge to create
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        curve: Union[Edge, Wire],
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self, log=False)

        if context is not None and isinstance(context, BuildLine):
            context._add_to_context(*curve.edges(), mode=mode)

        if isinstance(curve, Edge):
            super().__init__(Wire([curve]).wrapped)
        else:
            super().__init__(curve.wrapped)


class Bezier(BaseLineObject):
    """Line Object: Bezier Curve

    Create a rational (with weights) or non-rational bezier curve.  The first and last
    control points represent the start and end of the curve respectively.  If weights
    are provided, there must be one provided for each control point.

    Args:
        cntl_pnts (sequence[VectorLike]): points defining the curve
        weights (list[float], optional): control point weights list. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *cntl_pnts: VectorLike,
        weights: list[float] = None,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        cntl_pnts = flatten_sequence(*cntl_pnts)
        polls = WorkplaneList.localize(*cntl_pnts)
        curve = Edge.make_bezier(*polls, weights=weights)

        super().__init__(curve, mode=mode)


class CenterArc(BaseLineObject):
    """Line Object: Center Arc

    Add center arc to the line.

    Args:
        center (VectorLike): center point of arc
        radius (float): arc radius
        start_angle (float): arc staring angle
        arc_size (float): arc size
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        center_point = WorkplaneList.localize(center)
        if context is None:
            circle_workplane = Plane.XY
        else:
            circle_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])
        circle_workplane.origin = center_point
        arc_direction = (
            AngularDirection.COUNTER_CLOCKWISE
            if arc_size > 0
            else AngularDirection.CLOCKWISE
        )
        arc_size = (arc_size + 360.0) % 360.0
        end_angle = start_angle + arc_size
        start_angle = end_angle if arc_size == 360.0 else start_angle
        arc = Edge.make_circle(
            radius,
            circle_workplane,
            start_angle=start_angle,
            end_angle=end_angle,
            angular_direction=arc_direction,
        )

        super().__init__(arc, mode=mode)


class DoubleTangentArc(BaseLineObject):
    """Line Object: Double Tangent Arc

    Create an arc defined by a point/tangent pair and another line which the other end
    is tangent to.

    Contains a solver.

    Args:
        pnt (VectorLike): starting point of tangent arc
        tangent (VectorLike): tangent at starting point of tangent arc
        other (Union[Curve, Edge, Wire]): reference line
        keep (Keep, optional): selector for which arc to keep when two arcs are
            possible. The arc generated with TOP or BOTTOM depends on the geometry
            and isn't necessarily easy to predict. Defaults to Keep.TOP.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        RunTimeError: no double tangent arcs found
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        pnt: VectorLike,
        tangent: VectorLike,
        other: Union[Curve, Edge, Wire],
        keep: Keep = Keep.TOP,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        arc_pt = WorkplaneList.localize(pnt)
        arc_tangent = WorkplaneList.localize(tangent)
        if WorkplaneList._get_context() is not None:
            workplane = WorkplaneList._get_context().workplanes[0]
        else:
            workplane = Edge.make_line(arc_pt, arc_pt + arc_tangent).common_plane(
                *other.edges()
            )
            if workplane is None:
                raise ValueError("DoubleTangentArc only works on a single plane")
            workplane = -workplane  # Flip to help with TOP/BOTTOM
        rotation_axis = Axis((0, 0, 0), workplane.z_dir)
        # Protect against massive circles that are effectively straight lines
        max_size = 2 * other.bounding_box().add(arc_pt).diagonal

        # Function to be minimized - note radius is a numpy array
        def func(radius, perpendicular_bisector):
            center = arc_pt + perpendicular_bisector * radius[0]
            separation = other.distance_to(center)
            return abs(separation - radius)

        # Minimize the function using bounds and the tolerance value
        arc_centers = []
        for angle in [90, -90]:
            perpendicular_bisector = arc_tangent.rotate(rotation_axis, angle)
            result = minimize(
                func,
                x0=0.0,
                args=perpendicular_bisector,
                method="Nelder-Mead",
                bounds=[(0.0, max_size)],
                tol=TOLERANCE,
            )
            arc_radius = result.x[0]
            arc_center = arc_pt + perpendicular_bisector * arc_radius

            # Check for matching tangents
            circle = Edge.make_circle(
                arc_radius, Plane(arc_center, z_dir=rotation_axis.direction)
            )
            dist, p1, p2 = other.distance_to_with_closest_points(circle)
            if dist > TOLERANCE:  # If they aren't touching
                continue
            other_axis = Axis(p1, other.tangent_at(p1))
            circle_axis = Axis(p2, circle.tangent_at(p2))
            if other_axis.is_parallel(circle_axis):
                arc_centers.append(arc_center)

        if len(arc_centers) == 0:
            raise RuntimeError("No double tangent arcs found")

        # If there are multiple solutions, select the desired one
        if keep == Keep.TOP:
            arc_centers = arc_centers[0:1]
        elif keep == Keep.BOTTOM:
            arc_centers = arc_centers[-1:]

        with BuildLine() as double:
            for center in arc_centers:
                _, p1, _ = other.distance_to_with_closest_points(center)
                TangentArc(arc_pt, p1, tangent=arc_tangent)

        super().__init__(double.line, mode=mode)


class EllipticalStartArc(BaseLineObject):
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

    _applies_to = [BuildLine._tag]

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


class EllipticalCenterArc(BaseLineObject):
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

    _applies_to = [BuildLine._tag]

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
        validate_inputs(context, self)

        center_pnt = WorkplaneList.localize(center)
        if context is None:
            ellipse_workplane = Plane.XY
        else:
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

        super().__init__(curve, mode=mode)


class Helix(BaseLineObject):
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

    _applies_to = [BuildLine._tag]

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
        validate_inputs(context, self)

        center_pnt = WorkplaneList.localize(center)
        helix = Edge.make_helix(
            pitch, height, radius, center_pnt, direction, cone_angle, lefthand
        )
        super().__init__(helix, mode=mode)


class FilletPolyline(BaseLineObject):
    """Line Object: FilletPolyline

    Add a sequence of straight lines defined by successive points that
    are filleted to a given radius.

    Args:
        pts (Union[VectorLike, Iterable[VectorLike]]): sequence of two or more points
        radius (float): radius of filleted corners
        close (bool, optional): close by generating an extra Edge. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Two or more points not provided
        ValueError: radius must be positive
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: Union[VectorLike, Iterable[VectorLike]],
        radius: float,
        close: bool = False,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        pts = flatten_sequence(*pts)

        if len(pts) < 2:
            raise ValueError("FilletPolyline requires two or more pts")
        if radius <= 0:
            raise ValueError("radius must be positive")

        lines_pts = WorkplaneList.localize(*pts)

        # Create the polyline
        new_edges = [
            Edge.make_line(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]
        if close and (new_edges[0] @ 0 - new_edges[-1] @ 1).length > 1e-5:
            new_edges.append(Edge.make_line(new_edges[-1] @ 1, new_edges[0] @ 0))
        wire_of_lines = Wire(new_edges)

        # Create a list of vertices from wire_of_lines in the same order as
        # the original points so the resulting fillet edges are ordered
        ordered_vertices = []
        for pnts in lines_pts:
            distance = {
                v: (Vector(pnts) - Vector(*v)).length for v in wire_of_lines.vertices()
            }
            ordered_vertices.append(sorted(distance.items(), key=lambda x: x[1])[0][0])

        # Fillet the corners

        # Create a map of vertices to edges containing that vertex
        vertex_to_edges = {
            v: [e for e in wire_of_lines.edges() if v in e.vertices()]
            for v in ordered_vertices
        }

        # For each corner vertex create a new fillet Edge
        fillets = []
        for vertex, edges in vertex_to_edges.items():
            if len(edges) != 2:
                continue
            other_vertices = set(
                ve for e in edges for ve in e.vertices() if ve != vertex
            )
            third_edge = Edge.make_line(*[v.to_tuple() for v in other_vertices])
            fillet_face = Face(Wire(edges + [third_edge])).fillet_2d(radius, [vertex])
            fillets.append(fillet_face.edges().filter_by(GeomType.CIRCLE)[0])

        # Create the Edges that join the fillets
        if close:
            interior_edges = [
                Edge.make_line(fillets[i - 1] @ 1, fillets[i] @ 0)
                for i in range(len(fillets))
            ]
            end_edges = []
        else:
            interior_edges = [
                Edge.make_line(fillets[i] @ 1, f @ 0) for i, f in enumerate(fillets[1:])
            ]
            end_edges = [
                Edge.make_line(wire_of_lines @ 0, fillets[0] @ 0),
                Edge.make_line(fillets[-1] @ 1, wire_of_lines @ 1),
            ]

        new_wire = Wire(end_edges + interior_edges + fillets)

        super().__init__(new_wire, mode=mode)


class JernArc(BaseLineObject):
    """JernArc

    Circular tangent arc with given radius and arc_size

    Args:
        start (VectorLike): start point
        tangent (VectorLike): tangent at start point
        radius (float): arc radius
        arc_size (float): arc size in degrees (negative to change direction)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Attributes:
        start (Vector): start point
        end_of_arc (Vector): end point of arc
        center_point (Vector): center of arc
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start: VectorLike,
        tangent: VectorLike,
        radius: float,
        arc_size: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        start = WorkplaneList.localize(start)
        self.start = start
        if context is None:
            jern_workplane = Plane.XY
        else:
            jern_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])
        jern_workplane.origin = start
        start_tangent = Vector(tangent).transform(jern_workplane.reverse_transform, is_direction=True)

        arc_direction = copysign(1.0, arc_size)
        self.center_point = start + start_tangent.rotate(
            Axis(start, jern_workplane.z_dir), arc_direction * 90
        ) * abs(radius)
        self.end_of_arc = self.center_point + (start - self.center_point).rotate(
            Axis(start, jern_workplane.z_dir), arc_size
        )
        if abs(arc_size) >= 360:
            circle_plane = copy.copy(jern_workplane)
            circle_plane.origin = self.center_point
            circle_plane.x_dir = self.start - circle_plane.origin
            arc = Edge.make_circle(radius, circle_plane)
        else:
            arc = Edge.make_tangent_arc(start, start_tangent, self.end_of_arc)

        super().__init__(arc, mode=mode)


class Line(BaseLineObject):
    """Line Object: Line

    Add a straight line defined by two end points.

    Args:
        pts (Union[VectorLike, Iterable[VectorLike]]): sequence of two points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Two point not provided
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self, *pts: Union[VectorLike, Iterable[VectorLike]], mode: Mode = Mode.ADD
    ):
        pts = flatten_sequence(*pts)
        if len(pts) != 2:
            raise ValueError("Line requires two pts")

        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        pts = WorkplaneList.localize(*pts)

        lines_pts = [Vector(p) for p in pts]

        new_edge = Edge.make_line(lines_pts[0], lines_pts[1])
        super().__init__(new_edge, mode=mode)


class IntersectingLine(BaseLineObject):
    """Intersecting Line Object: Line

    Add a straight line that intersects another line at a given parameter and angle.

    Args:
        start (VectorLike): start point
        direction (VectorLike): direction to make line
        other (Edge): stop at the intersection of other
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start: VectorLike,
        direction: VectorLike,
        other: Union[Curve, Edge, Wire],
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        start = WorkplaneList.localize(start)
        direction = WorkplaneList.localize(direction).normalized()
        axis = Axis(start, direction)

        intersection_pnts = [
            i for edge in other.edges() for i in edge.find_intersection_points(axis)
        ]
        if not intersection_pnts:
            raise ValueError("No intersections found")

        distances = [(start - p).length for p in intersection_pnts]
        length = min(distances)
        new_edge = Edge.make_line(start, start + direction * length)
        super().__init__(new_edge, mode=mode)


class PolarLine(BaseLineObject):
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

    _applies_to = [BuildLine._tag]

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
        validate_inputs(context, self)

        start = WorkplaneList.localize(start)
        if context is None:
            polar_workplane = Plane.XY
        else:
            polar_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])

        if direction:
            direction = WorkplaneList.localize(direction)
            angle = Vector(1, 0, 0).get_angle(direction)
        elif angle is not None:
            direction = polar_workplane.x_dir.rotate(
                Axis((0, 0, 0), polar_workplane.z_dir),
                angle,
            )
        else:
            raise ValueError("Either angle or direction must be provided")

        if length_mode == LengthMode.DIAGONAL:
            length_vector = direction * length
        elif length_mode == LengthMode.HORIZONTAL:
            length_vector = direction * (length / cos(radians(angle)))
        elif length_mode == LengthMode.VERTICAL:
            length_vector = direction * (length / sin(radians(angle)))

        new_edge = Edge.make_line(start, start + length_vector)

        super().__init__(new_edge, mode=mode)


class Polyline(BaseLineObject):
    """Line Object: Polyline

    Add a sequence of straight lines defined by successive point pairs.

    Args:
        pts (Union[VectorLike, Iterable[VectorLike]]): sequence of two or more points
        close (bool, optional): close by generating an extra Edge. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Two or more points not provided
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: Union[VectorLike, Iterable[VectorLike]],
        close: bool = False,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        pts = flatten_sequence(*pts)
        if len(pts) < 2:
            raise ValueError("Polyline requires two or more pts")

        lines_pts = WorkplaneList.localize(*pts)

        new_edges = [
            Edge.make_line(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]
        if close and (new_edges[0] @ 0 - new_edges[-1] @ 1).length > 1e-5:
            new_edges.append(Edge.make_line(new_edges[-1] @ 1, new_edges[0] @ 0))

        super().__init__(Wire.combine(new_edges)[0], mode=mode)


class RadiusArc(BaseLineObject):
    """Line Object: Radius Arc

    Add an arc defined by two end points and a radius

    Args:
        start_point (VectorLike): start
        end_point (VectorLike): end
        radius (float): radius
        short_sagitta (bool): If True selects the short sagitta, else the
            long sagitta crossing the center. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Insufficient radius to connect end points
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        radius: float,
        short_sagitta: bool = True,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        start, end = WorkplaneList.localize(start_point, end_point)
        # Calculate the sagitta from the radius
        length = end.sub(start).length / 2.0
        try:
            if short_sagitta:
                sagitta = abs(radius) - sqrt(radius**2 - length**2)
            else:
                sagitta = -abs(radius) - sqrt(radius**2 - length**2)
        except ValueError as exception:
            raise ValueError(
                "Arc radius is not large enough to reach the end point."
            ) from exception

        # Return a sagitta arc
        if radius > 0:
            arc = SagittaArc(start, end, sagitta, mode=Mode.PRIVATE)
        else:
            arc = SagittaArc(start, end, -sagitta, mode=Mode.PRIVATE)

        super().__init__(arc, mode=mode)


class SagittaArc(BaseLineObject):
    """Line Object: Sagitta Arc

    Add an arc defined by two points and the height of the arc (sagitta).

    Args:
        start_point (VectorLike): start
        end_point (VectorLike): end
        sagitta (float): arc height
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        sagitta: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        start, end = WorkplaneList.localize(start_point, end_point)
        mid_point = (end + start) * 0.5
        if context is None:
            sagitta_workplane = Plane.XY
        else:
            sagitta_workplane = copy.copy(WorkplaneList._get_context().workplanes[0])
        sagitta_vector: Vector = (end - start).normalized() * abs(sagitta)
        sagitta_vector = sagitta_vector.rotate(
            Axis(sagitta_workplane.origin, sagitta_workplane.z_dir),
            90 if sagitta > 0 else -90,
        )

        sag_point = mid_point + sagitta_vector

        arc = ThreePointArc(start, sag_point, end, mode=Mode.PRIVATE)
        super().__init__(arc, mode=mode)


class Spline(BaseLineObject):
    """Line Object: Spline

    Add a spline through the provided points optionally constrained by tangents.

    Args:
        pts (Union[VectorLike, Iterable[VectorLike]]): sequence of two or more points
        tangents (Iterable[VectorLike], optional): tangents at end points. Defaults to None.
        tangent_scalars (Iterable[float], optional): change shape by amplifying tangent.
            Defaults to None.
        periodic (bool, optional): make the spline periodic. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: Union[VectorLike, Iterable[VectorLike]],
        tangents: Iterable[VectorLike] = None,
        tangent_scalars: Iterable[float] = None,
        periodic: bool = False,
        mode: Mode = Mode.ADD,
    ):
        pts = flatten_sequence(*pts)
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

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
            tangents=(
                [
                    t * s if isinstance(t, Vector) else Vector(*t) * s
                    for t, s in zip(spline_tangents, scalars)
                ]
                if spline_tangents
                else None
            ),
            periodic=periodic,
            scale=tangent_scalars is None,
        )
        super().__init__(spline, mode=mode)


class TangentArc(BaseLineObject):
    """Line Object: Tangent Arc

    Add an arc defined by two points and a tangent.

    Args:
        pts (Union[VectorLike, Iterable[VectorLike]]): sequence of two points
        tangent (VectorLike): tangent to constrain arc
        tangent_from_first (bool, optional): apply tangent to first point. Note, applying
            tangent to end point will flip the orientation of the arc. Defaults to True.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Two points are required
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: Union[VectorLike, Iterable[VectorLike]],
        tangent: VectorLike,
        tangent_from_first: bool = True,
        mode: Mode = Mode.ADD,
    ):
        pts = flatten_sequence(*pts)
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        if len(pts) != 2:
            raise ValueError("tangent_arc requires two points")
        arc_pts = WorkplaneList.localize(*pts)
        arc_tangent = WorkplaneList.localize(tangent).normalized()

        point_indices = (0, -1) if tangent_from_first else (-1, 0)
        arc = Edge.make_tangent_arc(
            arc_pts[point_indices[0]], arc_tangent, arc_pts[point_indices[1]]
        )

        super().__init__(arc, mode=mode)


class ThreePointArc(BaseLineObject):
    """Line Object: Three Point Arc

    Add an arc generated by three points.

    Args:
        pts (Union[VectorLike, Iterable[VectorLike]]): sequence of three points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Three points must be provided
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self, *pts: Union[VectorLike, Iterable[VectorLike]], mode: Mode = Mode.ADD
    ):
        context: BuildLine = BuildLine._get_context(self)
        validate_inputs(context, self)

        pts = flatten_sequence(*pts)
        if len(pts) != 3:
            raise ValueError("ThreePointArc requires three points")
        points = WorkplaneList.localize(*pts)
        arc = Edge.make_three_point_arc(*points)

        super().__init__(arc, mode=mode)
