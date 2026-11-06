"""
build123d topology

name: silhouette.py
by:   Gumyr
date: October 20, 2026

desc:
    The silhouette of a shape as seen along a direction or from an eye point,
    and what follows from it: the faces split along their contours, the
    fragments that face the viewer, and the shadows faces and curves cast on
    a plane. Internal; the projection operations build on these.

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

from dataclasses import dataclass
from math import pi
from typing import TYPE_CHECKING, cast

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace
from OCP.BRepFeat import BRepFeat_SplitShape
from OCP.BRepTopAdaptor import BRepTopAdaptor_TopolTool
from OCP.Contap import Contap_Contour, Contap_IType, Contap_Line
from OCP.Geom import Geom_Plane
from OCP.GeomProjLib import GeomProjLib
from OCP.collections import List_TopoDS_Shape
from OCP.gp import gp_Ax3, gp_Dir, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Vec
from OCP.Standard import Standard_Failure
from OCP.StdFail import StdFail_NotDone
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Shell, TopoDS_Vertex

from build123d.build_enums import GeomType
from build123d.geometry import (
    TOLERANCE,
    Axis,
    Location,
    Matrix,
    Plane,
    Vector,
    VectorLike,
)

from .history import ShapeHistory
from .one_d import Edge, Wire
from .shape_core import (
    Shape,
    ShapeList,
    _sew_topods_faces,
    _topods_entities,
    downcast,
    get_top_level_topods_shapes,
)
from .utils import (
    _extrude_topods_shape,
    _make_topods_compound_from_shapes,
    find_max_dimension,
)
from .uv_write import UVFrame
from .zero_d import Vertex

if TYPE_CHECKING:  # pragma: no cover
    from .two_d import Face, Shell


def _as_face(obj: TopoDS_Face) -> Face:
    """The kernel face wrapped. Faces are made through the class registry
    rather than by importing ``Face``, so that this module sits below two_d
    and the Face methods built on it can import it."""
    return cast("Face", Shape.cast(obj))


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


def silhouette_edges(face: Face, viewer: Viewer) -> ShapeList[Edge]:
    """The silhouette of ``face`` for the view: its contour edges, less any
    running along an edge the face already has.

    A face whose normal turns through the viewing direction but received no
    contour is a kernel failure the caller cannot recover from, and raises.

    Raises:
        RuntimeError: a face that should carry a contour has none
    """
    edges = _off_the_boundary(face, contour_edges(face, viewer))
    if not edges and _normal_turns_through(face, viewer):
        raise RuntimeError(
            f"a {face.geom_type.name} face turns through the viewing direction "
            "but the kernel found no contour on it"
        )
    return edges


def _off_the_boundary(face: Face, edges: ShapeList[Edge]) -> ShapeList[Edge]:
    """The contour edges that do not run along an edge the face already has,
    as a cone's silhouette lines do when its side was built in halves; the
    splitter has nothing to do there and mishandles the coincidence."""
    boundary = face.edges()
    kept: ShapeList[Edge] = ShapeList()
    for edge in edges:
        on_boundary = all(
            min(bound.distance_to(edge.position_at(t)) for bound in boundary)
            < TOLERANCE
            for t in (0.0, 0.5, 1.0)
        )
        if not on_boundary:
            kept.append(edge)
    return kept


_GRAZING = 1e-3
"""A normal this nearly perpendicular to the view is taken as perpendicular"""


def _normal_turns_through(face: Face, viewer: Viewer) -> bool:
    """Does the face's normal change sign against the viewing direction?

    Tested at the points the kernel itself samples the surface at, chosen
    from its type, degree and knots and the points Contap_Contour starts
    walking a contour from, together with the face's own vertices, edge
    midpoints and interior point. A planar face never turns.
    """
    if face.is_planar is not None:
        return False
    signs: set[bool] = set()

    def note(normal: Vector, point: Vector) -> None:
        # Along an edge that is itself the contour the normal is perpendicular
        # to the view, up to the noise of the surface's evaluation, which on a
        # B-spline fit runs well past the modelling tolerance
        along = normal.dot(viewer.direction_at(point))
        if abs(along) > _GRAZING:
            signs.add(along > 0)

    anchors = [face.interior_point()] + [
        edge.position_at(t) for edge in face.edges() for t in (0.0, 0.5, 1.0)
    ]
    # A degenerate edge is a pole of the surface, where it has no normal; the
    # kernel evaluates one there anyway, pointing wherever its limit went, so
    # an anchor on a pole says nothing about the face
    poles = [Vector(v) for edge in _degenerate_edges(face) for v in edge.vertices()]
    for point in anchors:
        if any((point - pole).length < TOLERANCE for pole in poles):
            continue
        note(face.normal_at(point), point)
    u_min, u_max, v_min, v_max = face._uv_bounds()
    sampler = BRepTopAdaptor_TopolTool(BRepAdaptor_Surface(face.wrapped))
    sampler.ComputeSamplePoints()
    uv_sample, _ = gp_Pnt2d(), gp_Pnt()
    for index in range(1, sampler.NbSamples() + 1):
        sampler.SamplePoint(index, uv_sample, _)
        u = (uv_sample.X() - u_min) / (u_max - u_min)
        v = (uv_sample.Y() - v_min) / (v_max - v_min)
        if face.is_inside(u, v):
            note(face.normal_at(u, v), face.position_at(u, v))
    return len(signs) == 2


def _degenerate_edges(face: Face) -> list[Edge]:
    """The face's degenerate edges, each a side of its surface collapsed to a
    point, as at a sphere's pole. ``Face.edges`` leaves them out."""
    found: list[Edge] = []
    explorer = TopExp_Explorer(face.wrapped, TopAbs_EDGE)
    while explorer.More():
        topods_edge = TopoDS.Edge(explorer.Current())
        if BRep_Tool.Degenerated_s(topods_edge):
            found.append(Edge(topods_edge))
        explorer.Next()
    return found


def split_by_silhouette(shape: Shape, viewer: Viewer) -> tuple[Shape, ShapeHistory]:
    """``shape`` with each face split along its contour, and the record of
    which face became which fragments.

    A face with no contour is left as it is.
    """
    splitter = BRepFeat_SplitShape(shape.wrapped)
    added = 0
    for face in shape.faces():
        # The kernel walks a contour in pieces that meet at interior points;
        # chained into wires they share those vertices, which the splitter
        # needs to carry a cut from one piece to the next
        for wire in Wire.combine(silhouette_edges(face, viewer)):
            splitter.Add(wire.wrapped, face.wrapped)
            added += 1
    if added == 0:
        return shape, ShapeHistory(before=[shape.wrapped])
    splitter.Build()
    result = downcast(splitter.Shape())
    history = ShapeHistory.from_algorithm(splitter, [shape.wrapped], result)
    return Shape.cast(result), history


def front_facing(faces: ShapeList[Face], viewer: Viewer) -> ShapeList[Face]:
    """The faces that look toward the viewer: the normal at an interior point
    has a component against the viewing direction. A face seen edge-on, its
    normal perpendicular to the view but for noise, looks neither way."""
    kept: ShapeList[Face] = ShapeList()
    for face in faces:
        point = face.interior_point()
        if face.normal_at(point).dot(viewer.direction_at(point)) < -_GRAZING:
            kept.append(face)
    return kept


def visible_faces(shape: Shape, viewer: Viewer) -> ShapeList[Face]:
    """The faces of ``shape``, split along its silhouette, that look toward
    the viewer; the surfaces a viewer could see, before one hides another."""
    split, _ = split_by_silhouette(shape, viewer)
    return front_facing(split.faces(), viewer)


def _edge_on(face: Face, direction: VectorLike) -> bool:
    """Whether a face casts no shadow along a direction.

    Only a surface swept along the direction has its normal perpendicular to
    it everywhere: a plane containing the direction, a cylinder with its axis
    along it, or a linear extrusion swept along it. Every other surface tilts
    somewhere and casts a shadow there, so it is never edge-on; a free-form
    surface is at most edge-on within tolerance, which is not worth chasing.
    """
    if face.is_empty:
        return False
    direction = Vector(direction).normalized()
    plane = face.is_planar
    if plane is not None:
        return abs(plane.z_dir.dot(direction)) < TOLERANCE
    if face.geom_type == GeomType.CYLINDER:
        axis = face.axis_of_rotation
        assert axis is not None
        along = axis.direction
    elif face.geom_type == GeomType.EXTRUSION:
        swept = face.extrusion_direction
        assert swept is not None
        along = swept
    else:
        return False
    return along.cross(direction).length < TOLERANCE


def _project_profile_by_extrusion(
    profile: Face, target: Shape, direction: VectorLike, keep_edge_on: bool = False
) -> ShapeList[Face | Shell]:
    """The regions of a target's surface that a profile covers when swept along a
    direction, nearest first.

    The profile is extruded far enough to pass right through the target and the
    extrusion is intersected with the target. The faces of the result that came
    from the target, whether the boolean rebuilt them or left them untouched
    inside the column, are sewn into the surfaces the column passes through, one
    Face or Shell each, and ordered by distance along ``direction`` from the
    profile. This is the core of :meth:`Face.project_to_shape`.

    The boolean is run directly rather than through :meth:`Shape.intersect`,
    whose ``UnifySameDomain`` clean could merge a target fragment into a coplanar
    face of the extrusion before the fragment is attributed.

    A target face lying along the direction, inside the column or on its wall,
    survives the boolean but has no area for a projection to land on, and
    sewing joins the surfaces on either side of it into one region. Such faces
    are dropped unless ``keep_edge_on`` asks for them: an extrusion stopping at
    a stepped surface needs the risers to make a surface that cuts it.

    Args:
        profile (Face): the face swept along the direction
        target (Shape): the shape whose surface is sampled
        direction (VectorLike): the sweep direction; only surfaces ahead of the
            profile are found
        keep_edge_on (bool, optional): keep the target faces lying along the
            direction. Defaults to False.

    Raises:
        TypeError: the target is a Vertex
        RuntimeError: sewing returned something other than faces and shells

    Returns:
        ShapeList[Face | Shell]: the surfaces met, nearest first; empty when the
        column misses the target
    """
    if isinstance(target, Vertex):
        raise TypeError("projection to a vertex is not supported")
    direction = Vector(direction)
    max_dimension = find_max_dimension([profile, target])
    extrusion = _extrude_topods_shape(profile.wrapped, direction * max_dimension)

    arguments, tools = List_TopoDS_Shape(), List_TopoDS_Shape()
    arguments.Append(target.wrapped)
    tools.Append(extrusion)
    operation = BRepAlgoAPI_Common()
    operation.SetArguments(arguments)
    operation.SetTools(tools)
    operation.SetRunParallel(True)
    operation.Build()
    result = operation.Shape()
    if result.IsNull():
        return ShapeList()

    history = ShapeHistory.from_boolean(
        operation, before=[target.wrapped], brought=[extrusion]
    )
    trace = history.trace([target.wrapped])
    target_faces = [
        TopoDS.Face(face)
        for face in _topods_entities(result, "Face")
        if (trace.is_modified(face) or trace.is_untouched(face))
        and (keep_edge_on or not _edge_on(_as_face(TopoDS.Face(face)), direction))
    ]
    if not target_faces:
        return ShapeList()

    # Sewing can hand back a vertex or edge of a face as a free sub-shape
    # beside the faces and shells; those carry no surface and are dropped
    regions: ShapeList[Face | Shell] = ShapeList()
    for region in get_top_level_topods_shapes(_sew_topods_faces(target_faces)):
        if isinstance(region, (TopoDS_Face, TopoDS_Shell)):
            regions.append(cast("Face | Shell", Shape.cast(region)))
        elif not isinstance(region, (TopoDS_Vertex, TopoDS_Edge)):
            raise RuntimeError(f"Invalid sewn shape {type(region)}")
    return regions.sort_by(Axis(profile.center(), direction))


def _as_one_shape(faces: ShapeList[Face]) -> Shape:
    """The faces bundled as a single shape, for operations that take one"""
    return Shape.cast(_make_topods_compound_from_shapes([f.wrapped for f in faces]))


def _shadows(faces: ShapeList[Face], direction: Vector, reach: float) -> list[Shape]:
    """The volume behind each face along the direction, as far as ``reach``:
    what the face hides from a viewer looking along the direction."""
    return [
        Shape.cast(_extrude_topods_shape(face.wrapped, direction * reach))
        for face in faces
    ]


def visible_regions(
    profile: Face, target: Shape, direction: VectorLike
) -> ShapeList[Face]:
    """The parts of ``target``'s surface that ``profile`` covers and that a
    viewer behind the profile, looking along ``direction``, sees.

    The target is split along its silhouette and only the faces looking back
    at the viewer are projected onto; of the regions found, each loses what
    lies in the shadow another casts along the direction. Nearest first.
    """
    viewer = Viewer.along(direction)
    assert viewer.direction is not None
    front = visible_faces(target, viewer)
    if not front:
        return ShapeList()
    regions = _project_profile_by_extrusion(
        profile, _as_one_shape(front), viewer.direction
    )
    faces = ShapeList(face for region in regions for face in region.faces())
    reach = find_max_dimension([profile, target])
    shadows = _shadows(faces, viewer.direction, reach)
    kept: ShapeList[Face] = ShapeList()
    for index, face in enumerate(faces):
        others = [shadow for other, shadow in enumerate(shadows) if other != index]
        remain: Shape = face.cut(*others) if others else face
        kept.extend(piece for piece in remain.faces() if piece.area > TOLERANCE)
    return kept.sort_by(Axis(profile.center(), viewer.direction))


def visible_curves(
    curve: Wire, target: Shape, direction: VectorLike
) -> ShapeList[Wire]:
    """The projection of ``curve`` onto the parts of ``target`` a viewer
    behind the curve, looking along ``direction``, sees.

    The curve is projected onto the faces of the target that look back at
    the viewer, and each piece loses what lies in the shadow of any other
    such face.
    """
    viewer = Viewer.along(direction)
    assert viewer.direction is not None
    front = visible_faces(target, viewer)
    if not front:
        return ShapeList()
    # The kernel projects a curve both ways along the direction; only what
    # lies ahead of the curve is in view
    pieces = [
        piece
        for piece in curve.project_to_shape(
            _as_one_shape(front), direction=viewer.direction
        )
        if (piece.center() - curve.center()).dot(viewer.direction) >= 0
    ]
    reach = find_max_dimension([curve, target])
    shadows = _shadows(front, viewer.direction, reach)
    kept_edges: list[Edge] = []
    for edge in (edge for piece in pieces for edge in piece.edges()):
        middle = edge.position_at(0.5)
        distances = [face.distance_to(middle) for face in front]
        host = distances.index(min(distances))
        others = [shadow for index, shadow in enumerate(shadows) if index != host]
        remain: Shape = edge.cut(*others) if others else edge
        kept_edges.extend(piece for piece in remain.edges() if piece.length > TOLERANCE)
    return ShapeList(Wire.combine(kept_edges)) if kept_edges else ShapeList()


def silhouette_on_plane(shape: Shape, plane: Plane) -> ShapeList[Face]:
    """The silhouette of ``shape`` on ``plane``, seen from the shape's side:
    the faces that look toward the plane, projected onto it and fused.

    Returns:
        ShapeList[Face]: planar faces lying in ``plane``, holes included
    """
    above = plane.to_local_coords(shape.center()).Z > 0
    direction = -plane.z_dir if above else plane.z_dir
    front = visible_faces(shape, Viewer.along(direction))
    if not front:
        return ShapeList()
    # Project onto a screen behind the whole shape, so that no part of it is
    # already past the plane, and move the result back onto the plane
    footprint = plane.to_local_coords(shape).bounding_box(optimal=False)
    depth = footprint.min.Z - 1 if above else footprint.max.Z + 1
    half_width, half_height = footprint.size.X + 0.5, footprint.size.Y + 0.5
    screen = plane.from_local_coords(
        _as_face(
            BRepBuilderAPI_MakeFace(
                gp_Pln(), -half_width, half_width, -half_height, half_height
            ).Face()
        ).moved(Location((footprint.center().X, footprint.center().Y, depth)))
    )
    flat = [
        face
        for fragment in front
        for region in _project_profile_by_extrusion(fragment, screen, direction)
        for face in region.faces()
    ]
    if not flat:
        return ShapeList()
    union = flat[0].fuse(*flat[1:]).clean() if len(flat) > 1 else flat[0]
    return union.moved(Location(plane.z_dir * -depth)).faces()


def face_shadow(face: Face, screen: Face, direction: Vector) -> ShapeList[Face]:
    """The shadow a face casts on a screen along a direction.

    A curved face can fold back on itself along the direction, in which case
    sweeping it as one piece self-intersects and yields nothing. The face is
    split along its silhouette, where its normal turns through the direction,
    each fragment is swept onto the screen, and the shadows are fused. Unlike
    a body, a lone face has no hidden side: every fragment casts a shadow,
    except one edge-on to the direction, which has no area to cast.
    """
    if face.is_planar is not None:
        fragments: list[Face] = [face]
    else:
        pieces, _ = split_by_silhouette(face, Viewer.along(direction))
        fragments = list(pieces.faces())
    shadows = [
        piece
        for fragment in fragments
        if not _edge_on(fragment, direction)
        for piece in fragment.project_to_shape(screen, direction).faces()
    ]
    if len(shadows) > 1:
        return shadows[0].fuse(*shadows[1:]).clean().faces()
    return ShapeList(shadows)


def _ordered_in_plane(local: Vector) -> tuple[float, float]:
    """Sort key placing points along a plane's x then y direction, with noise
    below the tolerance ignored."""
    return (
        round(local.X / TOLERANCE) * TOLERANCE,
        round(local.Y / TOLERANCE) * TOLERANCE,
    )


def curve_shadow(edge: Edge, plane: Plane, direction: Vector) -> list[Edge]:
    """The shadow an edge casts on a plane along a direction.

    The curve itself is projected onto the plane, so a shadow that crosses
    itself is no obstacle. A planar curve whose plane contains the direction
    is edge-on and would retrace itself on the plane; its shadow is the
    segment spanning its extent across the direction. A curve parallel to
    the direction casts no shadow.
    """
    curve_plane = edge.common_plane()
    if curve_plane is not None and abs(curve_plane.z_dir.dot(direction)) < TOLERANCE:
        across = curve_plane.z_dir.cross(direction).normalized()
        frame = Plane(edge.position_at(0), x_dir=across, z_dir=direction)
        extent = frame.to_local_coords(edge).bounding_box(optimal=True)
        if extent.size.X < TOLERANCE:
            return []
        edge = Edge.make_line(
            frame.from_local_coords(Vector(extent.min.X, 0, 0)),
            frame.from_local_coords(Vector(extent.max.X, 0, 0)),
        )
    first, last = BRep_Tool.Range_s(edge.wrapped)
    curve = BRep_Tool.Curve_s(edge.wrapped, first, last)
    geom_plane = Geom_Plane(
        gp_Ax3(gp_Pnt(*plane.origin), gp_Dir(*plane.z_dir), gp_Dir(*plane.x_dir))
    )
    shadow_curve = GeomProjLib.ProjectOnPlane_s(
        curve, geom_plane, gp_Dir(*direction), True
    )
    try:
        shadow = Edge(BRepBuilderAPI_MakeEdge(shadow_curve, first, last).Edge())
    except (Standard_Failure, StdFail_NotDone):
        return []  # the curve collapsed to a point
    if shadow.length < TOLERANCE:
        return []
    if shadow.geom_type == GeomType.LINE:
        # Collinear shadows only fuse into one when they run the same way, so
        # every line runs along the plane's x then y direction
        ends = [shadow.position_at(0), shadow.position_at(1)]
        ends.sort(key=lambda pnt: _ordered_in_plane(plane.to_local_coords(pnt)))
        shadow = Edge.make_line(*ends)
    return [shadow]
