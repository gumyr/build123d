from math import pi, sin, cos, radians, sqrt
from typing import Union, Iterable, Sequence, Callable
from enum import Enum, auto
from abc import ABC, abstractmethod
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
from build2d import Build2D
from build3d import Build3D


class Build1D:
    @property
    def working_line(self) -> Wire:
        return Wire.assembleEdges(self.edge_list)

    def __init__(self, mode: Mode = Mode.ADDITION):
        self.edge_list = []
        self.tags: dict[str, Edge] = {}
        self.mode = mode

    def __enter__(self):
        if "context_stack" in globals():
            context_stack.append(self)
        else:
            globals()["context_stack"] = [self]
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # if self.parent is not None:
        #     self.parent.add(*self.edge_list, mode=self.mode)
        if "context_stack" in globals():
            context_stack.pop()
            if context_stack:
                context_stack[-1].add(*self.edge_list, mode=self.mode)

    def edges(self) -> list[Edge]:
        return self.edge_list

    def vertices(self) -> list[Vertex]:
        vertex_list = []
        for e in self.edge_list:
            vertex_list.extend(e.Vertices())
        return list(set(vertex_list))


class Build1DObject(ABC):
    @property
    @abstractmethod
    def object(self):
        """Each derived class must provide the created object"""
        return NotImplementedError

    @staticmethod
    def add(*edges: Edge, mode: Mode = Mode.ADDITION):
        if "context_stack" in globals():
            if context_stack:  # Stack isn't empty
                for edge in edges:
                    edge.forConstruction = mode == Mode.CONSTRUCTION
                    if not isinstance(edge, Edge):
                        raise ValueError("Build1D.add only accepts edges")
                    context_stack[-1].edge_list.append(edge)
        print(f"{context_stack[-1].edge_list=}")


class Polyline(Build1DObject):
    @property
    def object(self) -> Union[Edge, Wire]:
        if len(self.new_edges) == 1:
            return self.new_edges[0]
        else:
            return Wire.assembleEdges(self.new_edges)

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) < 2:
            raise ValueError("polyline requires two or more pts")

        lines_pts = [Vector(p) for p in pts]

        self.new_edges = [
            Edge.makeLine(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]
        Build1DObject.add(*self.new_edges, mode=mode)


class Spline(Build1DObject):
    @property
    def object(self) -> Edge:
        return self.spline

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

        self.spline = Edge.makeSpline(
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

        Build1DObject.add(self.spline, mode=mode)


class CenterArc(Build1DObject):
    @property
    def object(self) -> Edge:
        return self.arc

    def __init__(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float,
        mode: Mode = Mode.ADDITION,
    ):

        if abs(arc_size) >= 360:
            self.arc = Edge.makeCircle(
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
            self.arc = Edge.makeThreePointArc(p1, p2, p3)

        Build1DObject.add(self.arc, mode=mode)


class ThreePointArc(Build1DObject):
    @property
    def object(self) -> Edge:
        return self.arc

    def __init__(self, *pts: VectorLike, mode: Mode = Mode.ADDITION):
        if len(pts) != 3:
            raise ValueError("ThreePointArc requires three points")
        points = [Vector(p) for p in pts]
        self.arc = Edge.makeThreePointArc(*points)
        Build1DObject.add(self.arc, mode=mode)


class TangentArc(Build1DObject):
    @property
    def object(self) -> Edge:
        return self.arc

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
        self.arc = Edge.makeTangentArc(
            arc_pts[point_indices[0]], arc_tangent, arc_pts[point_indices[1]]
        )

        Build1DObject.add(self.arc, mode=mode)


class RadiusArc(Build1DObject):
    @property
    def object(self) -> Edge:
        return self.arc

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
            self.arc = SagittaArc(start, end, sagitta, mode=mode).object
        else:
            self.arc = SagittaArc(start, end, -sagitta, mode=mode).object


class SagittaArc(Build1DObject):
    @property
    def object(self) -> Edge:
        return self.arc

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

        self.arc = ThreePointArc(start, sag_point, end, mode=mode).object


class MirrorX(Build1DObject):
    @property
    def object(self) -> Union[Edge, list[Edge]]:
        return (
            self.mirrored_edges[0]
            if len(self.mirrored_edges) == 1
            else self.mirrored_edges
        )

    def __init__(self, *edges: Edge, mode: Mode = Mode.ADDITION):
        self.mirrored_edges = Plane.named("XY").mirrorInPlane(edges, axis="X")
        Build1DObject.add(*self.mirrored_edges, mode=mode)


class MirrorY(Build1DObject):
    @property
    def object(self) -> Union[Edge, list[Edge]]:
        return (
            self.mirrored_edges[0]
            if len(self.mirrored_edges) == 1
            else self.mirrored_edges
        )

    def __init__(self, *edges: Edge, mode: Mode = Mode.ADDITION):
        self.mirrored_edges = Plane.named("XY").mirrorInPlane(edges, axis="Y")
        Build1DObject.add(*self.mirrored_edges, mode=mode)
