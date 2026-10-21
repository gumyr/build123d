"""
build123d topology

name: silhouette.py
by:   Gumyr
date: October 20, 2026

desc:
    The silhouette of a shape as seen along a direction or from an eye point,
    and what follows from it: the faces split along their contours and the
    fragments that face the viewer. Internal; the projection operations
    build on these.

    The contour of each face comes from the kernel's Contap_Contour, the
    engine behind its hidden-line removal, as exact points carrying their
    surface parameters, or as a line or circle on an analytic surface. The
    points are written onto the face through a UVFrame so that the edge lies
    on the surface exactly, which the kernel's own outline edges, fitted a
    few parts in ten thousand off a torus or a B-spline surface, do not.

license:

    Copyright 2026 Gumyr

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

from dataclasses import dataclass, field
from itertools import product
from math import pi

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepFeat import BRepFeat_SplitShape
from OCP.BRepTools import BRepTools
from OCP.BRepTopAdaptor import BRepTopAdaptor_TopolTool
from OCP.Contap import Contap_Contour, Contap_IType, Contap_Line
from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Vec
from OCP.TopAbs import TopAbs_State
from OCP.TopoDS import TopoDS_Face

from build123d.geometry import TOLERANCE, Matrix, Vector, VectorLike

from .history import ShapeHistory
from .one_d import Edge, Wire
from .shape_core import Shape, ShapeList, downcast
from .two_d import Face
from .utils import _topods_face_normal, _topods_face_position
from .uv_write import UVFrame


@dataclass(frozen=True)
class Viewer:
    """Where a shape is seen from: along a direction (parallel) or from an
    eye point (perspective).

    Args:
        direction (Vector | None): the viewing direction, from the viewer
            toward the shape. Parallel projection.
        eye (Vector | None): the eye point. Perspective projection; the
            direction at a point of the shape runs from the eye to it.
    """

    direction: Vector | None = None
    eye: Vector | None = None

    @classmethod
    def along(cls, direction: VectorLike) -> Viewer:
        """A parallel view along ``direction``."""
        return cls(direction=Vector(direction).normalized())

    @classmethod
    def at(cls, eye: VectorLike) -> Viewer:
        """A perspective view from ``eye``."""
        return cls(eye=Vector(eye))

    def __post_init__(self):
        if (self.direction is None) == (self.eye is None):
            raise ValueError("one of direction or eye must be given")

    def direction_at(self, point: VectorLike) -> Vector:
        """The viewing direction through ``point``, toward the shape."""
        if self.direction is not None:
            return self.direction
        assert self.eye is not None
        return (Vector(point) - self.eye).normalized()

    def contour(self) -> Contap_Contour:
        """The kernel's contour finder for this view."""
        if self.direction is not None:
            return Contap_Contour(gp_Vec(*self.direction))
        assert self.eye is not None
        return Contap_Contour(gp_Pnt(*self.eye))


@dataclass
class FaceContour:
    """A face of the shape with the contour edges that lie on it."""

    face: Face
    edges: ShapeList[Edge] = field(default_factory=ShapeList)


def contour_edges(face: Face, viewer: Viewer) -> ShapeList[Edge]:
    """The contour of ``face`` for the view, as edges on its surface.

    The contour is where the surface normal is perpendicular to the viewing
    direction. The kernel walks it as points with their (u, v) on the surface,
    already cut at the surface's seams and the face's boundary, or names the
    line or circle it is on an analytic surface. Walking lines are
    interpolated on the uv plane and written onto the face, so the edge's
    pcurve is the contour itself; lines and circles are built from the
    geometry, trimmed between the ends the kernel found.
    """
    adaptor = BRepAdaptor_Surface(face.wrapped)
    finder = viewer.contour()
    finder.Perform(adaptor, BRepTopAdaptor_TopolTool(adaptor))
    if finder.IsEmpty():
        return ShapeList()

    frame: UVFrame | None = None
    edges: ShapeList[Edge] = ShapeList()
    for index in range(1, finder.NbLines() + 1):
        line = finder.Line(index)
        kind = line.TypeContour()
        if kind == Contap_IType.Contap_Walking:
            if frame is None:
                frame = UVFrame(face, Matrix())
            uv_points = _walking_points(line)
            if len(uv_points) < 2:
                continue
            closed = (Vector(uv_points[0]) - Vector(uv_points[-1])).length < TOLERANCE
            if closed:
                uv_points.pop()
            if len(uv_points) < 2:
                continue
            edges.append(frame.write_edge(Edge.make_spline(uv_points, periodic=closed)))
        elif kind in (Contap_IType.Contap_Lin, Contap_IType.Contap_Circle):
            edges.extend(_analytic_edges(line, kind))
        # a Contap_Restriction runs along the face boundary: nothing to split
    return edges


def _walking_points(line: Contap_Line) -> list[VectorLike]:
    """The (u, v) points of a walking line on the uv plane, consecutive
    duplicates dropped."""
    points: list[Vector] = []
    for index in range(1, line.NbPnts() + 1):
        u, v = line.Point(index).Parameters()[-2:]
        point = Vector(u, v, 0)
        if not points or (point - points[-1]).length > TOLERANCE:
            points.append(point)
    return list(points)


def _analytic_edges(line: Contap_Line, kind: Contap_IType) -> list[Edge]:
    """A contour on a line or circle, between the ends the kernel found; a
    circle whose ends meet, or without ends, is whole."""
    parameters = sorted(
        line.Vertex(index).ParameterOnLine() for index in range(1, line.NbVertex() + 1)
    )
    span = parameters[-1] - parameters[0] if len(parameters) >= 2 else 0.0
    if kind == Contap_IType.Contap_Lin:
        if span < TOLERANCE:
            return []
        return [
            Edge(
                BRepBuilderAPI_MakeEdge(
                    line.Line(), parameters[0], parameters[-1]
                ).Edge()
            )
        ]
    circle = line.Circle()
    start = parameters[0] % (2 * pi) if parameters else 0.0
    if span < TOLERANCE or span >= 2 * pi - TOLERANCE:
        # A whole circle, as two arcs meeting where the kernel put its ends,
        # the surface's seam: a closed edge with no vertex there does not split
        return [
            Edge(BRepBuilderAPI_MakeEdge(circle, start, start + pi).Edge()),
            Edge(BRepBuilderAPI_MakeEdge(circle, start + pi, start + 2 * pi).Edge()),
        ]
    return [Edge(BRepBuilderAPI_MakeEdge(circle, start, start + span).Edge())]


def contours_by_face(shape: Shape, viewer: Viewer) -> list[FaceContour]:
    """Each face of ``shape`` with its contour edges.

    A face whose normal turns through the viewing direction but received no
    contour is a kernel failure the caller cannot recover from, and raises.

    Raises:
        RuntimeError: a face that should carry a contour has none
    """
    by_face = [FaceContour(face, contour_edges(face, viewer)) for face in shape.faces()]
    for index, entry in enumerate(by_face):
        if not entry.edges and _normal_turns_through(entry.face, viewer):
            raise RuntimeError(
                f"face {index} ({entry.face.geom_type.name}) turns through the "
                "viewing direction but the kernel found no contour on it"
            )
    return by_face


def _normal_turns_through(face: Face, viewer: Viewer, samples: int = 5) -> bool:
    """Does the face's normal change sign against the viewing direction
    across a grid of interior points?"""
    topods_face = face.wrapped
    assert isinstance(topods_face, TopoDS_Face)
    signs: set[bool] = set()
    steps = [(i + 0.5) / samples for i in range(samples)]
    for u, v in product(steps, steps):
        if not _uv_inside(topods_face, u, v):
            continue
        along = _topods_face_normal(topods_face, u, v).dot(
            viewer.direction_at(_topods_face_position(topods_face, u, v))
        )
        if abs(along) > TOLERANCE:
            signs.add(along > 0)
    return len(signs) == 2


def _uv_inside(face: TopoDS_Face, u: float, v: float) -> bool:
    """Is the normalized (u, v) point inside the face's trimmed region?"""
    u_min, u_max, v_min, v_max = BRepTools.UVBounds_s(face)
    classifier = BRepClass_FaceClassifier(
        face,
        gp_Pnt2d(u_min + u * (u_max - u_min), v_min + v * (v_max - v_min)),
        TOLERANCE,
    )
    return classifier.State() == TopAbs_State.TopAbs_IN


def _interior_uv(face: TopoDS_Face, samples: int = 7) -> tuple[float, float]:
    """A normalized (u, v) inside the face: its parametric centre when that
    is inside, else the first inside point of a grid.

    Raises:
        RuntimeError: no grid point lies inside the face
    """
    if _uv_inside(face, 0.5, 0.5):
        return 0.5, 0.5
    steps = [(i + 0.5) / samples for i in range(samples)]
    for u, v in product(steps, steps):
        if _uv_inside(face, u, v):
            return u, v
    raise RuntimeError("no interior point found on face")


def split_by_silhouette(shape: Shape, viewer: Viewer) -> tuple[Shape, ShapeHistory]:
    """``shape`` with each face split along its contour, and the record of
    which face became which fragments.

    A face with no contour is left as it is.
    """
    splitter = BRepFeat_SplitShape(shape.wrapped)
    added = 0
    for entry in contours_by_face(shape, viewer):
        # The kernel walks a contour in pieces that meet at interior points;
        # chained into wires they share those vertices, which the splitter
        # needs to carry a cut from one piece to the next
        for wire in Wire.combine(entry.edges):
            splitter.Add(wire.wrapped, entry.face.wrapped)
            added += 1
    if added == 0:
        return shape, ShapeHistory(before=[shape.wrapped])
    splitter.Build()
    result = downcast(splitter.Shape())
    history = ShapeHistory.from_algorithm(splitter, [shape.wrapped], result)
    return Shape.cast(result), history


def front_facing(faces: ShapeList[Face], viewer: Viewer) -> ShapeList[Face]:
    """The faces that look toward the viewer: the normal at an interior point
    has a component against the viewing direction."""
    kept: ShapeList[Face] = ShapeList()
    for face in faces:
        topods_face = face.wrapped
        assert isinstance(topods_face, TopoDS_Face)
        u, v = _interior_uv(topods_face)
        normal = _topods_face_normal(topods_face, u, v)
        point = _topods_face_position(topods_face, u, v)
        if normal.dot(viewer.direction_at(point)) < 0:
            kept.append(face)
    return kept
