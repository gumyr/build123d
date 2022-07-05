from math import pi, sin, cos, radians, sqrt
from typing import Union, Iterable, Sequence, Callable
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
from build_sketch import BuildSketch
from build_part import BuildPart


class BuildLine:
    @property
    def working_line(self) -> Wire:
        return Wire.assembleEdges(self.edge_list)

    def __init__(self, mode: Mode = Mode.ADDITION):
        self.edge_list = []
        self.tags: dict[str, Edge] = {}
        self.mode = mode

    # def __enter__(self):
    #     if "context_stack" in globals():
    #         context_stack.append(self)
    #     else:
    #         globals()["context_stack"] = [self]
    #     return self
    def __enter__(self):
        context_stack.append(self)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # if self.parent is not None:
        #     self.parent.add(*self.edge_list, mode=self.mode)
        # if "context_stack" in globals():
        #     context_stack.pop()
        #     if context_stack:
        #         if isinstance(context_stack[-1], Build2D):
        #             for edge in self.edge_list:
        #                 Build2D.add_to_context(edge, mode=self.mode)
        #         elif isinstance(context_stack[-1], Build3D):
        #             for edge in self.edge_list:
        #                 Build3D.add_to_context(edge, mode=self.mode)

        #     if not context_stack:
        #         del globals()["context_stack"]

        context_stack.pop()
        if context_stack:
            if isinstance(context_stack[-1], BuildSketch):
                for edge in self.edge_list:
                    BuildSketch.add_to_context(edge, mode=self.mode)
            elif isinstance(context_stack[-1], BuildPart):
                for edge in self.edge_list:
                    BuildPart.add_to_context(edge, mode=self.mode)

    def edges(self) -> EdgeList:
        # return EdgeList(*self.edge_list)
        return self.edge_list

    def vertices(self) -> list[Vertex]:
        vertex_list = []
        for e in self.edge_list:
            vertex_list.extend(e.Vertices())
        return list(set(vertex_list))

    @staticmethod
    def add_to_context(*edges: Edge, mode: Mode = Mode.ADDITION):
        # if "context_stack" in globals() and mode != Mode.PRIVATE:
        #     if context_stack:  # Stack isn't empty
        if context_stack and mode != Mode.PRIVATE:
            # if context_stack:  # Stack isn't empty
            for edge in edges:
                edge.forConstruction = mode == Mode.CONSTRUCTION
                # if not isinstance(edge, Edge):
                # if not issubclass(type(edge),Edge):
                #     raise ValueError("Build1D.add only accepts edges")
                context_stack[-1].edge_list.append(edge)

    @staticmethod
    def get_context() -> "BuildLine":
        return context_stack[-1]


class Line(Edge):
    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) != 2:
            raise ValueError("Line requires two pts")

        lines_pts = [Vector(p) for p in pts]

        new_edge = Edge.makeLine(lines_pts[0], lines_pts[1])
        BuildLine.add_to_context(new_edge, mode=mode)
        super().__init__(new_edge.wrapped)


class Polyline(Wire):
    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) < 3:
            raise ValueError("polyline requires three or more pts")

        lines_pts = [Vector(p) for p in pts]

        new_edges = [
            Edge.makeLine(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]
        BuildLine.add_to_context(*new_edges, mode=mode)
        super().__init__(Wire.assembleEdges(new_edges).wrapped)


class Spline(Edge):
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


class CenterArc(Edge):
    def __init__(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float,
        mode: Mode = Mode.ADDITION,
    ):

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

        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class ThreePointArc(Edge):
    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) != 3:
            raise ValueError("ThreePointArc requires three points")
        points = [Vector(p) for p in pts]
        arc = Edge.makeThreePointArc(*points)
        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class TangentArc(Edge):
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


class RadiusArc(Edge):
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
        except ValueError:
            raise ValueError("Arc radius is not large enough to reach the end point.")

        # Return a sagitta arc
        if radius > 0:
            arc = SagittaArc(start, end, sagitta, mode=Mode.PRIVATE)
        else:
            arc = SagittaArc(start, end, -sagitta, mode=Mode.PRIVATE)

        BuildLine.add_to_context(arc, mode=mode)
        super().__init__(arc.wrapped)


class SagittaArc(Edge):
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


class Helix(Wire):
    def __init__(
        self,
        pitch: float,
        height: float,
        radius: float,
        center: VectorLike = (0, 0, 0),
        direction: VectorLike = (0, 0, 1),
        angle: float = 360,
        lefhand: bool = False,
        mode: Mode = Mode.ADDITION,
    ):
        helix = Wire.makeHelix(
            pitch, height, radius, Vector(center), Vector(direction), angle, lefhand
        )
        BuildLine.add_to_context(*helix.Edges(), mode=mode)
        super().__init__(helix.wrapped)


class Mirror:
    def __init__(self, *edges: Edge, axis: Axis = Axis.X, mode: Mode = Mode.ADDITION):
        mirrored_edges = Plane.named("XY").mirrorInPlane(edges, axis=axis.name)
        BuildLine.add_to_context(*mirrored_edges, mode=mode)
