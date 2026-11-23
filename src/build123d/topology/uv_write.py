"""
build123d topology

name: uv_write.py
by:   Gumyr
date: September 19, 2026

desc:

    Write flat shapes into a face's parameter space.

    A planar Edge, Wire or Face drawn on Plane.XY is mapped into the (u, v)
    domain of a target face and rebuilt there as edges that carry a pcurve on
    the face's own surface. Nothing is fitted in 3D: the curves lie on the
    surface by construction, and the 3D curves are derived from them.

    A UVFrame is a flat coordinate system laid onto a face at a Location:
    the flat origin lands on the location's position and the flat x axis runs
    along its x direction. Behind the frame is a map from flat (x, y) to
    (u, v), of one of two kinds:

    * a Matrix, for surfaces whose development is affine. A plane's map is
      rigid; a cylinder's is the isometry that unrolls it, with u running at
      1/radius per unit of arc. Lines stay lines, circles and ellipses stay
      conics (with an SVD giving the image's axes), and every other curve is
      a B-spline whose poles are transformed, which is exact because B-splines
      are affinely invariant.
    * a callable, for anything else. A cone unrolls exactly into a sector
      about its apex, a sphere takes an azimuthal equidistant projection
      about the origin, and every other surface takes its exponential map:
      a flat point at bearing b and distance d lands d along the geodesic
      that leaves the origin at bearing b, found by integrating the geodesic
      equation. That is the same construction as the sphere's projection,
      and on a developable surface it is the exact unrolling. The image of
      a curve is interpolated through mapped samples and refined until its
      3D error is under a tolerance.

    The mapped shape is first laid out on the uv plane, Plane.XY with x as u
    and y as v, as a planar shape in its own right, and its edges are written
    with their curves there as pcurves. On a periodic surface a shape may
    lie across the seam, which is known exactly as a parameter line.

    A face across the seam is written the way the kernel leaves one after a
    boolean: as one face whose parameters start inside the surface's own
    range and run on past its end, on the surface trimmed to that range.
    The trimming matters. The bare surface says its parameter stops at the
    end of the period, and the kernel's booleans go wrong on a face that
    runs past it; the trimmed surface's bounds are the face's own.

    A face that goes exactly once round the surface, a band about a
    cylinder, meets itself along its two sides. It is written as the
    kernel's own whole-turn faces are: over the surface's own range, with
    the line where it meets itself moved onto the seam and written once, as
    a seam edge - one edge carrying two pcurves, at the start and at the end
    of the period, used forward and reversed in the same wire.

    A face spanning more than a whole turn may do so without meeting itself
    when it is sheared along the surface, as a helical band is, and is then
    cut along the seam into one face per period it reaches into, each moved
    into the surface's own range; the pieces meet along the seam, so once
    thickened they are best joined into one tool before a boolean with the
    target solid. A wire standing alone is cut at the seam too and gets a
    vertex where it crosses. A shape that would overlap itself once wrapped,
    or one surrounding a pole, is refused.

    The frame writes edges, wires and faces, and can punch an outline into
    the face it sits on.

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

from collections.abc import Callable
from functools import cache
from math import asin, atan2, ceil, cos, floor, hypot, pi, sin
from typing import TYPE_CHECKING, NamedTuple, TypeVar, cast

from scipy.integrate import solve_ivp

from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeVertex,
)
from OCP.BRepLib import BRepLib
from OCP.Geom import Geom_RectangularTrimmedSurface, Geom_Surface
from OCP.Geom2d import (
    Geom2d_BSplineCurve,
    Geom2d_Circle,
    Geom2d_Curve,
    Geom2d_Ellipse,
    Geom2d_Line,
    Geom2d_TrimmedCurve,
)
from OCP.Geom2dConvert import Geom2dConvert
from OCP.GeomAbs import GeomAbs_Shape
from OCP.GeomAPI import GeomAPI
from OCP.IntTools import IntTools_FClass2d
from OCP.gp import gp_Ax22d, gp_Dir2d, gp_Pln, gp_Pnt, gp_Pnt2d
from OCP.TopAbs import TopAbs_Orientation, TopAbs_State
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Vertex, TopoDS_Wire

from build123d.build_enums import GeomType, Keep
from build123d.geometry import TOLERANCE, Location, Matrix, Plane, Vector, VectorLike

from .one_d import Edge, Wire
from .shape_core import Shape, ShapeList
from .utils import _make_topods_face_from_wires

if TYPE_CHECKING:  # pragma: no cover
    from .two_d import Face

PointMap = Callable[[float, float], tuple[float, float]]
"""A map from flat (x, y) to the (u, v) parameters of a surface"""

_ORDERS = ((1, 0), (0, 1), (2, 0), (0, 2), (1, 1))
"""The (u, v) orders of a surface's derivatives S_u, S_v, S_uu, S_vv, S_uv"""

Period = tuple[Vector, float, float]
"""A periodic direction of a surface on the uv plane: its unit vector there,
where the surface's own range starts along it, and the period"""

Piece = TypeVar("Piece", Edge, "Face")
"""An edge or a face of a mapped shape on the uv plane"""

_ON_LINE = 1e-7
"""How close, in parameter, a mapped edge lies to a parameter line to be on it"""

_SAME_POINT = 1e-6
"""How close two ends of written edges are to share a vertex"""

_TOO_THIN = 2 * _SAME_POINT
"""How narrow a strip of a mapped face is, in parameter or on the surface, to
be too thin to cut off as a part of its own: its ends would share vertices"""


class _Run(NamedTuple):
    """An edge of a mapped outline, the way the outline runs along it"""

    edge: Edge
    backwards: bool
    """Whether the outline runs against the edge's own curve"""
    start: Vector
    end: Vector


class _VertexPool:
    """The vertices of a wire being written, one per point however many
    edges end there

    Edges written one by one each bring their own vertices, to be matched up
    by position afterwards. A seam edge is used twice in one wire and must
    stay the same edge, so the wire it is in is built with its vertices
    shared from the start.
    """

    def __init__(self) -> None:
        self._vertices: list[TopoDS_Vertex] = []

    def at(self, point: gp_Pnt) -> TopoDS_Vertex:
        """The vertex at a point, made if there is none there yet"""
        for vertex in self._vertices:
            if BRep_Tool.Pnt_s(vertex).Distance(point) < _SAME_POINT:
                self.cover(vertex, point)
                return vertex
        self._vertices.append(BRepBuilderAPI_MakeVertex(point).Vertex())
        return self._vertices[-1]

    @staticmethod
    def cover(vertex: TopoDS_Vertex, point: gp_Pnt) -> None:
        """Widen a vertex's tolerance to reach the end of an edge that ends
        a little off it"""
        distance = BRep_Tool.Pnt_s(vertex).Distance(point)
        if distance > 0.0:
            BRep_Builder().UpdateVertex(vertex, distance + TOLERANCE)


def _as_face(obj: TopoDS_Face) -> Face:
    """The kernel face wrapped. Faces are made through the class registry
    rather than by importing ``Face``, so that this module sits below two_d
    and ``Face.uv_frame`` can import it."""
    return cast("Face", Shape.cast(obj))


class UVFrame:
    """A flat coordinate system laid onto a face

    The frame writes planar shapes drawn on ``Plane.XY`` into the parameter
    space of ``face``, so that they lie on its surface exactly. ``mapping`` takes
    a flat (x, y) to the face's (u, v): a ``Matrix`` applied to
    ``Vector(x, y, 0)`` and read back as (u, v), for surfaces whose
    development is affine, or any callable for the rest.

    Most callers want :meth:`at` or :meth:`~topology.Face.uv_frame`, which
    choose the map from the face's geometry. The constructor is for a map of
    one's own, such as the unrolled frame of a sheet-metal bend or another
    projection onto a sphere. Seams are handled in parameter space, so any
    map takes part; a map must be continuous over the shape it writes.

    Args:
        face (Face): the face written onto
        mapping (Matrix | PointMap): flat (x, y) to (u, v)
        tolerance (float, optional): largest 3D error allowed when a curve's
            image has to be interpolated rather than mapped exactly. Defaults
            to 1e-4.
    """

    def __init__(
        self,
        face: Face,
        mapping: Matrix | PointMap,
        tolerance: float = 1e-4,
    ):
        if tolerance <= 0:
            raise ValueError("tolerance must be positive")
        self.face = face
        self.mapping = mapping
        self.tolerance = tolerance
        # the face's own surface and where the face places it; writing
        # happens on the surface, the placement is applied to the result
        self._location = TopLoc_Location()
        self._surface: Geom_Surface = BRep_Tool.Surface_s(face.wrapped, self._location)
        self._placement = Location(self._location)
        self._periods = _surface_periods(self._surface)

    # ---- construction ----

    @classmethod
    def at(cls, face: Face, location: Location, tolerance: float = 1e-4) -> UVFrame:
        """The frame of a face whose flat origin sits at a location

        The location's position is where the flat origin lands and its x
        direction, projected onto the surface, is where the flat x axis runs;
        flat y is the face normal crossed with x. The map is chosen from the
        face's geometry: exact for planes and cylinders, the exact unrolling
        for cones, an azimuthal equidistant projection for spheres, and the
        exponential map, integrated along geodesics, for everything else.

        Args:
            face (Face): the face written onto
            location (Location): where the flat origin lands, and which way
                flat x runs; ``face.location_at(u, v)`` is the usual source
            tolerance (float, optional): largest 3D error allowed for an
                interpolated image. Defaults to 1e-4.

        Returns:
            UVFrame: the frame
        """
        kind = face.geom_type
        if kind in (GeomType.PLANE, GeomType.CYLINDER):
            return cls(face, _affine_map(face, location), tolerance)
        if kind == GeomType.CONE:
            return cls(face, _cone_map(face, location), tolerance)
        if kind == GeomType.SPHERE:
            return cls(face, _sphere_map(face, location), tolerance)
        return cls(face, _geodesic_map(face, location, tolerance), tolerance)

    # ---- points ----

    def to_uv(self, x: float, y: float) -> Vector:
        """The parameters a flat point lands on

        Args:
            x (float): flat x
            y (float): flat y

        Returns:
            Vector: (u, v) on the face's surface, as a point of the uv plane
        """
        if isinstance(self.mapping, Matrix):
            return self.mapping.multiply(Vector(x, y, 0))
        return Vector(*self.mapping(x, y), 0)

    def lift(self, planar: Face) -> Face:
        """A planar face's image on the uv plane

        The face laid out where it lands in the surface's parameters, as a
        planar face on ``Plane.XY`` with x as u and y as v, before anything is
        written. A shape on that plane can be combined with the image of the
        face itself and written back through an identity frame, which is how
        a face is reshaped in its own parameter space.

        Args:
            planar (Face): a planar face on ``Plane.XY``

        Returns:
            Face: the image, on the uv plane
        """
        return self._lift_face(planar)

    # ---- writing ----

    def write_edge(self, edge: Edge) -> Edge:
        """The planar edge written onto the face

        The edge is written whole, moved by whole periods so that its middle
        lies in the surface's own parameter range; it is not cut at a seam.

        Args:
            edge (Edge): a planar edge on ``Plane.XY``

        Returns:
            Edge: an edge on the face's surface
        """
        written = self._write_edge(self._in_range(self._lift_edge(edge)))
        return written.moved(self._placement)

    def write_wire(self, wire: Wire) -> Wire:
        """The planar wire written onto the face, its vertices shared

        Edges are cut where they cross the surface's seam, and each piece is
        written inside the surface's own parameter range.

        Args:
            wire (Wire): a planar wire on ``Plane.XY``

        Raises:
            ValueError: the wire would overlap itself wrapped around the
                surface, or surrounds a pole

        Returns:
            Wire: a wire on the face's surface
        """
        lifted = self._lift_wire(wire)
        written = self._write_wire(lifted, self._seam_cutters(lifted))
        return written.moved(self._placement)

    def write_face(self, planar: Face) -> ShapeList[Face]:
        """The planar face written onto the face, holes included

        The result is on the target's own surface with the target's normal,
        so it combines with the target in booleans and thickens along the
        target's normal. The list holds one face - across the seam of a
        periodic surface or not, and all the way round one, where its two
        sides meet in a seam edge - unless the shape spans more than a whole
        turn, as a helical band can; that is cut along the seam into one
        face per period it reaches into.

        Args:
            planar (Face): a planar face on ``Plane.XY``

        Raises:
            ValueError: the shape would overlap itself wrapped around the
                surface, or surrounds a pole
            ValueError: the shape goes once round the surface but its two
                sides do not meet along their whole length, or it also lies
                across the surface's other seam

        Returns:
            ShapeList[Face]: faces on the target's surface
        """
        lifted = self._lift_face(planar)
        around = self._whole_turns(lifted)
        if around:
            lifted = self._fitted(planar, lifted, around[0])
            return ShapeList([self._write_around(lifted, around)])
        cutters = self._seam_cutters(lifted)  # refuses a shape that overlaps
        box = lifted.bounding_box()
        if any(
            (box.max - box.min).dot(axis) >= period - 1e-9
            for axis, _, period in self._periods
        ):
            pieces = [lifted]
            for cutter in cutters:
                pieces = [
                    part for piece in pieces for part in _split_all(piece, cutter)
                ]
            return ShapeList(
                self._write_face(self._in_range(piece)) for piece in pieces
            )
        lifted = self._from_range_start(lifted)
        return ShapeList([self._write_face(lifted, self._trimmed_to(lifted))])

    def punch(self, planar: Face) -> ShapeList[Face]:
        """The frame's face with a planar face's outline cut out of it

        Returns the punched face first. The planar face's own holes are
        material that survives inside the cut, so each comes back as a
        separate island face on the same surface.

        Only outlines lying wholly inside the face are handled; an outline
        crossing the face's boundary, its seam included, is not.

        Args:
            planar (Face): a planar face on ``Plane.XY`` to cut out

        Raises:
            ValueError: the outline crosses the surface's seam

        Returns:
            ShapeList[Face]: the punched face, then any islands
        """
        lifted = self._lift_face(planar)
        if len(self._pieces(lifted)) > 1:
            raise ValueError("an outline crossing the face's seam cannot be punched")
        lifted = self._in_range(lifted)
        # the face in its own frame, where the written wires are
        local = TopoDS.Face(self.face.wrapped.Located(TopLoc_Location()))
        maker = BRepBuilderAPI_MakeFace(local)
        # the outline becomes a hole: clockwise about the face normal
        maker.Add(self._oriented(lifted.outer_wire(), clockwise=True).wrapped)
        if not maker.IsDone():
            raise RuntimeError("could not build the punched face")
        punched = TopoDS.Face(maker.Face().Oriented(self.face.wrapped.Orientation()))
        islands = [
            self._write_face(_as_face(_make_topods_face_from_wires(island.wrapped)))
            for island in lifted.inner_wires()
        ]
        return ShapeList([_as_face(punched).moved(self._placement), *islands])

    # ---- the uv plane ----

    def _lift_edge(self, edge: Edge) -> Edge:
        """The planar edge's image laid on the uv plane

        Exact under a ``Matrix`` map: a line, a conic, or a B-spline with
        transformed poles. Otherwise interpolated through mapped samples and
        refined until it is within the tolerance in 3D.

        Raises:
            ValueError: the map jumps along the edge, as it does along the
                outline of a shape surrounding a pole of the face
            ValueError: the interpolated image cannot be brought within the
                tolerance
        """
        first, last = BRep_Tool.Range_s(edge.wrapped)
        curve = BRep_Tool.Curve_s(edge.wrapped, first, last)
        if isinstance(self.mapping, Matrix):
            image, first, last = _affine_image(
                GeomAPI.To2d_s(curve, gp_Pln()), first, last, self.mapping
            )
            exact = GeomAPI.To3d_s(image, gp_Pln())
            return Edge(BRepBuilderAPI_MakeEdge(exact, first, last).Edge())

        def uv_at(t: float) -> Vector:
            point = curve.Value(t)
            return self.to_uv(point.X(), point.Y())

        segments = 8
        for _ in range(8):
            params = [
                first + (last - first) * i / segments for i in range(segments + 1)
            ]
            uvs = [uv_at(t) for t in params]
            jumps = any(
                abs((b - a).dot(axis)) > period / 2
                for a, b in zip(uvs, uvs[1:])
                for axis, _, period in self._periods
            )
            lifted = Edge.make_spline(
                list[VectorLike](uvs), parameters=params, tol=1e-9
            )
            spline = BRep_Tool.Curve_s(lifted.wrapped, float(), float())
            # check midway between samples, in 3D
            error = max(
                (
                    self._point(uv_at(mid)) - self._point(Vector(spline.Value(mid)))
                ).length
                for mid in ((a + b) / 2 for a, b in zip(params, params[1:]))
            )
            if error <= self.tolerance and not jumps:
                return lifted
            segments *= 2
        if jumps:
            raise ValueError(
                "the map jumps along an edge of the shape: it surrounds a pole "
                "of the face, or reaches the far side of the surface"
            )
        raise ValueError(
            f"the image of an edge is still {error:.3g} from the mapped curve, "
            f"over the tolerance of {self.tolerance}"
        )

    def _lift_wire(self, wire: Wire) -> Wire:
        """The planar wire's image on the uv plane, traversed the same way"""
        edges = []
        for edge in wire.order_edges():
            lifted = self._lift_edge(edge)
            if edge.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED:
                lifted = Edge(TopoDS.Edge(lifted.wrapped.Reversed()))
            edges.append(lifted)
        return Wire(edges)

    def _lift_face(self, planar: Face) -> Face:
        """The planar face's image on the uv plane, holes included"""
        return _as_face(
            _make_topods_face_from_wires(
                self._lift_wire(planar.outer_wire()).wrapped,
                [self._lift_wire(wire).wrapped for wire in planar.inner_wires()],
            )
        )

    def _point(self, uv: Vector) -> Vector:
        """The point of the surface at a uv-plane point"""
        return Vector(self._surface.Value(uv.X, uv.Y))

    def _seam_cutters(self, lifted: Shape) -> list[Plane]:
        """Planes across the uv plane along the seam lines a mapped shape
        crosses: the parameter lines a whole number of periods from the start
        of the surface's range

        Raises:
            ValueError: the shape would overlap itself wrapped around the
                surface
        """
        box = lifted.bounding_box()
        cutters = []
        for axis, start, period in self._periods:
            low, high = box.min.dot(axis) - start, box.max.dot(axis) - start
            if high - low >= period - 1e-9 and _overlaps_wrapped(
                lifted, axis, period, high - low
            ):
                raise ValueError(
                    "the shape would overlap itself wrapped around the face: it "
                    "spans a whole turn or more where it is not sheared"
                )
            cutters += [
                Plane(axis * (start + k * period), z_dir=axis)
                for k in _periods_crossed(low, high, period)
            ]
        return cutters

    def _pieces(self, lifted: Face) -> list[Face]:
        """The mapped face split along every seam line that crosses it"""
        pieces = [lifted]
        for cutter in self._seam_cutters(lifted):
            pieces = [part for piece in pieces for part in _split_all(piece, cutter)]
        return pieces

    def _in_range(self, piece: Piece) -> Piece:
        """A mapped piece moved by whole periods into the surface's own
        parameter range

        The kernel keeps a periodic face's parameters in that range, and its
        booleans rewrite shared edges on that assumption; a piece written at
        negative u is valid on its own but comes back unorientable after one.
        A piece cut at every seam it crossed lies within one period, so any
        interior point says which.
        """
        centre = piece.center()
        shift = Vector()
        for axis, start, period in self._periods:
            shift += axis * (floor((centre.dot(axis) - start) / period) * period)
        return piece.moved(Location(-shift)) if shift.length else piece

    def _from_range_start(self, lifted: Face) -> Face:
        """A mapped face moved by whole periods so that it starts inside the
        surface's own parameter range

        Where the kernel puts a face that lies across a seam: its low side
        within the range, the rest running on past the end of it.
        """
        low = lifted.bounding_box().min
        shift = Vector()
        for axis, start, period in self._periods:
            # a face starting on the seam starts there: the box is a little
            # loose, and would otherwise put it a whole period away
            turns = floor((low.dot(axis) - start + _SAME_POINT) / period)
            shift += axis * (turns * period)
        return lifted.moved(Location(-shift)) if shift.length else lifted

    def _trimmed_to(self, lifted: Face) -> Geom_Surface:
        """The surface a mapped face is written on: the face's own, trimmed
        to the face's parameters in each direction the face runs past the
        end of the period, and untouched where it does not

        Trimmed, the surface's bounds reach as far as the face does. Left
        bare they stop at the end of the period, and a face written past
        them is valid but comes out of the kernel's booleans wrong.
        """
        box = lifted.bounding_box()
        past = {
            axis.X > 0.5: (box.min.dot(axis), box.max.dot(axis))
            for axis, start, period in self._periods
            if box.max.dot(axis) > start + period + 1e-9
        }
        if not past:
            return self._surface
        if len(past) == 2:
            return Geom_RectangularTrimmedSurface(
                self._surface, *past[True], *past[False]
            )
        ((along_u, (low, high)),) = past.items()
        return Geom_RectangularTrimmedSurface(self._surface, low, high, along_u)

    # ---- all the way round ----

    def _whole_turns(self, lifted: Face) -> list[Period]:
        """The periods a mapped face spans exactly: where it goes once round
        the surface and its two sides, a period apart, are the same curve

        Measured between the face's vertices, which the ends of two straight
        sides are, with the face's box - a little loose - to rule out an
        outline that bulges past them. A period apart means on the surface:
        the ends of the sides come near enough there to share the seam's
        vertices. In parameter that is nearer on a large surface than on a
        small one, where :meth:`_fitted` makes up the difference.

        The sides must share some length once one is moved a period onto the
        other. A face that only reaches the two lines, a helical band a
        period long or a diamond whose tips touch, or one whose sides lie
        apart along them, does not meet itself and is written like any other
        shape.
        """
        box = lifted.bounding_box()
        around = []
        for period in self._periods:
            axis, _, length = period
            along = [Vector(vertex).dot(axis) for vertex in lifted.vertices()]
            width = max(along) - min(along)
            if (
                # a whole period more or less is the same place on the surface
                abs(width - length) < length / 2
                and (box.max - box.min).dot(axis) <= width + _SAME_POINT
                and self._moved_on_surface(lifted, axis, max(along), width - length)
                < _SAME_POINT
                and any(
                    min(high, other_high) - max(low, other_low) > TOLERANCE
                    for low, high in _spans_on_line(lifted, axis, min(along))
                    for other_low, other_high in _spans_on_line(
                        lifted, axis, max(along)
                    )
                )
            ):
                around.append(period)
        return around

    def _fitted(self, planar: Face, lifted: Face, turn: Period) -> Face:
        """A mapped face that goes once round the surface, with its sides a
        period apart exactly

        Sides that meet on the surface can be further from a period apart in
        parameter than edges are told to lie along a line by, and on a small
        surface they are. The planar face is then lifted again through the
        map scaled along the turn about the face's low side, which moves
        nothing further on the surface than the sides were apart.
        """
        axis, _, length = turn
        along = [Vector(vertex).dot(axis) for vertex in lifted.vertices()]
        low, width = min(along), max(along) - min(along)
        if abs(width - length) <= _ON_LINE:
            return lifted
        scale = length / width
        scales = Vector(1, 1, 0) + axis * (scale - 1)
        offset = axis * (low * (1 - scale))
        fit = Matrix(
            [[scales.X, 0, 0, offset.X], [0, scales.Y, 0, offset.Y], [0, 0, 1, 0]]
        )
        fitted: Matrix | PointMap
        if isinstance(self.mapping, Matrix):
            fitted = fit.multiply(self.mapping)
        else:
            unfitted = self.mapping

            def fitted(x: float, y: float) -> tuple[float, float]:
                uv = fit.multiply(Vector(*unfitted(x, y), 0))
                return uv.X, uv.Y

        return UVFrame(self.face, fitted, self.tolerance)._lift_face(planar)

    def _write_around(self, lifted: Face, around: list[Period]) -> Face:
        """A mapped face that goes once round the surface, written as one
        face with a seam edge where its two sides meet

        The face is laid over the surface's own range: cut along the seam
        line, the part beyond it moved back a period. Its own two sides now
        lie on one line inside the range, where the face simply carries on,
        and the cut has become its sides, on the seam lines. The outlines of
        the parts are run together into the face's wires without their edges
        on that inner line, so nothing is fused and no curve is rebuilt.

        A face whose sides are already on the seam needs no cut, and nor does
        one whose sides are so nearly there that the part beyond the seam
        would be too thin to stand as one; that face is moved the last of
        the way, so that its sides are on the seam exactly.

        Raises:
            ValueError: the face goes round both ways, lies across the other
                seam, or its two sides do not meet along their whole length
        """
        if len(around) > 1:
            raise ValueError(
                "a shape going all the way round the face both ways cannot be written"
            )
        axis, start, period = around[0]
        sides = min(Vector(vertex).dot(axis) for vertex in lifted.vertices())
        # how far the sides are past the seam line nearest them
        past = sides - start - round((sides - start) / period) * period
        sides_on_seam = self._as_good_as_on_seam(lifted, axis, sides, past)
        if sides_on_seam:
            shift = axis * (sides - start)
        else:
            shift = axis * (floor((sides - start) / period) * period)
        box = lifted.bounding_box()
        for other, other_start, other_period in self._periods:
            if other.X == axis.X:
                continue
            low = box.min.dot(other)
            turns = floor((low - other_start + _SAME_POINT) / other_period)
            shift += other * (turns * other_period)
            if box.max.dot(other) - turns * other_period > (
                other_start + other_period + _SAME_POINT
            ):
                raise ValueError(
                    "a shape going all the way round the face one way and "
                    "lying across its seam the other cannot be written"
                )
        if shift.length:
            lifted = lifted.moved(Location(-shift))
            sides -= shift.dot(axis)

        seam_lines = (start, start + period)
        parts = [lifted]
        inner_line = None
        if not sides_on_seam:
            inner_line = sides
            cutter = Plane(axis * (start + period), z_dir=axis)
            parts = [
                (
                    part.moved(Location(-axis * period))
                    if part.center().dot(axis) > start + period
                    else part
                )
                for part in _split_all(lifted, cutter)
            ]

        # the outlines of the parts, each run anticlockwise, less the edges
        # on the line where the face carries on
        runs: list[_Run] = []
        dropped: dict[bool, list[tuple[float, float]]] = {True: [], False: []}
        across = Vector(axis.Y, axis.X, 0)  # the other parameter's direction
        for part in parts:
            for run in _outline_runs(part.outer_wire()):
                if inner_line is not None and _on_line(run.edge, axis, inner_line):
                    low, high = sorted((run.start.dot(across), run.end.dot(across)))
                    rising = run.end.dot(across) > run.start.dot(across)
                    dropped[rising].append((low, high))
                else:
                    runs.append(run)
        if not _same_spans(dropped[True], dropped[False]):
            raise ValueError(
                "the shape goes once round the face but its two sides do not "
                "meet along their whole length"
            )

        loops = _chained(runs)
        on_seam = [
            [
                next(
                    (line for line in seam_lines if _on_line(run.edge, axis, line)),
                    None,
                )
                for run in loop
            ]
            for loop in loops
        ]
        outer = [
            i for i, lines in enumerate(on_seam) if any(x is not None for x in lines)
        ]
        if len(outer) != 1 or any(
            _signed_area(loop) > 0 for i, loop in enumerate(loops) if i not in outer
        ):
            raise ValueError(
                "the shape goes once round the face but its two sides do not "
                "meet along their whole length"
            )

        pool = _VertexPool()
        seam = self._seam_edges(loops[outer[0]], on_seam[outer[0]], around[0], pool)
        maker = None
        for index, loop in sorted(
            enumerate(loops), key=lambda item: item[0] not in outer
        ):
            wire = self._write_loop(loop, on_seam[index], seam, pool)
            if maker is None:
                maker = BRepBuilderAPI_MakeFace(self._surface, wire, True)
            else:
                maker.Add(wire)
        assert maker is not None
        for part in parts:
            for inner in part.inner_wires():
                # a hole runs clockwise; one that touches the outline or
                # another hole shares the vertex there, as the pool sees to
                hole = [
                    _Run(run.edge, not run.backwards, run.end, run.start)
                    for run in reversed(_outline_runs(inner))
                ]
                off_seam: list[float | None] = [None] * len(hole)
                maker.Add(self._write_loop(hole, off_seam, seam, pool))
        if not maker.IsDone():
            raise RuntimeError("could not build the written face")
        face = TopoDS.Face(maker.Face().Oriented(self.face.wrapped.Orientation()))
        return _as_face(face).moved(self._placement)

    def _as_good_as_on_seam(
        self, lifted: Face, axis: Vector, sides: float, past: float
    ) -> bool:
        """Whether the sides of a face that goes once round the surface,
        ``past`` a seam line, are as good as on it: whether the strip between
        them and the seam is too thin to be cut off as a part of its own

        Too thin in parameter, where the cut is made, or on the surface,
        where the strip's corners would share vertices - and there at every
        end of a side, so that a face is never moved further on the surface
        than that to bring its sides onto the seam.
        """
        return (
            abs(past) <= _TOO_THIN
            or self._moved_on_surface(lifted, axis, sides, past) <= _TOO_THIN
        )

    def _moved_on_surface(
        self, lifted: Face, axis: Vector, line: float, distance: float
    ) -> float:
        """How far on the surface a move of ``distance`` in the parameter
        along ``axis`` takes the vertices of a mapped face on the line where
        that parameter is ``line``: the furthest any of them goes"""
        return max(
            (self._point(uv) - self._point(uv - axis * distance)).length
            for uv in map(Vector, lifted.vertices())
            if abs(uv.dot(axis) - line) <= _ON_LINE
        )

    def _seam_edges(
        self,
        loop: list[_Run],
        on_seam: list[float | None],
        turn: Period,
        pool: _VertexPool,
    ) -> list[tuple[float, float, TopoDS_Edge]]:
        """The seam edges of an outline whose sides lie on the seam lines,
        each with the span of the other parameter it covers

        A seam edge is one of the surface's iso-curves along the seam, built
        in the direction the other parameter increases, with two pcurves:
        first that of the side the outline runs up, where the edge is used
        forward, then that of the side it runs down, where it is reversed.
        The two sides need not be divided into edges alike, so the seam is
        divided wherever either is.

        Raises:
            ValueError: the two sides do not cover the same spans
        """
        axis, start, _ = turn
        along_u = axis.X > 0.5  # the seam is a line of constant u
        across = Vector(axis.Y, axis.X, 0)
        spans: dict[bool, list[tuple[float, float]]] = {True: [], False: []}
        side: dict[bool, set[float]] = {True: set(), False: set()}
        for run, line in zip(loop, on_seam):
            if line is None:
                continue
            low, high = sorted((run.start.dot(across), run.end.dot(across)))
            rising = run.end.dot(across) > run.start.dot(across)
            spans[rising].append((low, high))
            side[rising].add(line)
        if (
            not _same_spans(spans[True], spans[False])
            or len(side[True]) != 1
            or len(side[False]) != 1
        ):
            raise ValueError(
                "the shape goes once round the face but its two sides do not "
                "meet along their whole length"
            )
        (forward_line,), (reversed_line,) = side[True], side[False]
        breaks: list[float] = []
        for value in sorted(x for span in spans[True] + spans[False] for x in span):
            if not breaks or value - breaks[-1] > _ON_LINE:
                breaks.append(value)
        covered = _merged(spans[True])
        iso = self._surface.UIso(start) if along_u else self._surface.VIso(start)
        edges = []
        for low, high in zip(breaks, breaks[1:]):
            if not any(
                a - _ON_LINE <= low and high <= b + _ON_LINE for a, b in covered
            ):
                continue  # a gap in the sides, where the outline leaves the seam
            ends = [
                pool.at(
                    self._surface.Value(start, x)
                    if along_u
                    else self._surface.Value(x, start)
                )
                for x in (low, high)
            ]
            edge = BRepBuilderAPI_MakeEdge(iso, ends[0], ends[1], low, high).Edge()
            moved = BRep_Tool.Range_s(edge)[0] - low
            pcurves = [
                (
                    Geom2d_Line(gp_Pnt2d(line, -moved), gp_Dir2d(0.0, 1.0))
                    if along_u
                    else Geom2d_Line(gp_Pnt2d(-moved, line), gp_Dir2d(1.0, 0.0))
                )
                for line in (forward_line, reversed_line)
            ]
            BRep_Builder().UpdateEdge(
                edge,
                pcurves[0],
                pcurves[1],
                self._surface,
                TopLoc_Location(),
                TOLERANCE,
            )
            edges.append((low, high, edge))
        return edges

    def _write_loop(
        self,
        loop: list[_Run],
        on_seam: list[float | None],
        seam: list[tuple[float, float, TopoDS_Edge]],
        pool: _VertexPool,
    ) -> TopoDS_Wire:
        """A closed outline written as a wire with shared vertices, its runs
        along the seam lines taken from the seam edges"""
        builder = BRep_Builder()
        wire = TopoDS_Wire()
        builder.MakeWire(wire)
        for run, line in zip(loop, on_seam):
            if line is None:
                written = self._write_edge(run.edge, vertices=pool).wrapped
                builder.Add(wire, written.Reversed() if run.backwards else written)
                continue
            # the seam runs along the other parameter, whichever one that is
            first, last = (
                (run.start.Y, run.end.Y)
                if abs(run.start.X - run.end.X) < abs(run.start.Y - run.end.Y)
                else (run.start.X, run.end.X)
            )
            rising = last > first
            low, high = min(first, last), max(first, last)
            within = [
                edge
                for a, b, edge in seam
                if a >= low - _ON_LINE and b <= high + _ON_LINE
            ]
            for edge in within if rising else reversed(within):
                builder.Add(wire, edge if rising else edge.Reversed())
        wire.Closed(True)
        return wire

    # ---- the surface ----
    #
    # Written in the surface's own frame; the public methods place the
    # result with the face.

    def _write_edge(
        self,
        lifted: Edge,
        surface: Geom_Surface | None = None,
        vertices: _VertexPool | None = None,
    ) -> Edge:
        """A uv-plane edge written onto the surface, its curve the pcurve

        A span along one parameter is one of the surface's own iso-curves, a
        line along a cylinder's axis or a circle about it, and is built from
        that exactly; any other curve gets its 3D form from the kernel.
        ``surface`` is the face's surface trimmed, for a face across a seam.
        With ``vertices`` the edge ends on vertices from the pool, shared
        with the other edges that end there, rather than on its own.
        """
        surface = self._surface if surface is None else surface
        first, last = BRep_Tool.Range_s(lifted.wrapped)
        curve = BRep_Tool.Curve_s(lifted.wrapped, first, last)
        pcurve = GeomAPI.To2d_s(curve, gp_Pln())
        points = [pcurve.Value(first + (last - first) * i / 4) for i in range(5)]
        along_v = all(abs(p.X() - points[0].X()) < 1e-9 for p in points)
        along_u = all(abs(p.Y() - points[0].Y()) < 1e-9 for p in points)
        if along_v or along_u:
            u, v = points[0].X(), points[0].Y()
            if along_v:
                iso = surface.UIso(u)
                start, end = points[0].Y(), points[-1].Y()
            else:
                iso = surface.VIso(v)
                start, end = points[0].X(), points[-1].X()
            low, high = min(start, end), max(start, end)
            # a span a hair over a whole turn is the whole turn; the kernel
            # would wrap it back and leave an edge the length of the hair
            if iso.IsPeriodic() and 0 < high - low - iso.Period() <= _ON_LINE:
                high = low + iso.Period()
            if vertices is None:
                edge = BRepBuilderAPI_MakeEdge(iso, low, high).Edge()
            else:
                edge = BRepBuilderAPI_MakeEdge(
                    iso,
                    vertices.at(iso.Value(low)),
                    vertices.at(iso.Value(high)),
                    low,
                    high,
                ).Edge()
            # the iso-curve's parameter is the surface's other parameter, but
            # a periodic one may have been moved by whole periods into the
            # curve's own range; the pcurve follows the range the edge got
            shift = BRep_Tool.Range_s(edge)[0] - min(start, end)
            if along_v:
                pcurve = Geom2d_Line(gp_Pnt2d(u, -shift), gp_Dir2d(0.0, 1.0))
            else:
                pcurve = Geom2d_Line(gp_Pnt2d(-shift, v), gp_Dir2d(1.0, 0.0))
            BRep_Builder().UpdateEdge(
                edge, pcurve, surface, TopLoc_Location(), TOLERANCE
            )
            # built from low to high parameter, which may be against the lifted
            # edge's own direction
            return Edge(TopoDS.Edge(edge.Reversed()) if start > end else edge)
        if vertices is None:
            edge = BRepBuilderAPI_MakeEdge(pcurve, surface, first, last).Edge()
        else:
            ends = [
                vertices.at(surface.Value(point.X(), point.Y()))
                for point in (points[0], points[-1])
            ]
            edge = BRepBuilderAPI_MakeEdge(
                pcurve, surface, ends[0], ends[1], first, last
            ).Edge()
        if not BRepLib.BuildCurves3d_s(
            edge, min(self.tolerance, 1e-5), GeomAbs_Shape.GeomAbs_C1, 14, 0
        ):
            raise RuntimeError("could not build the 3D curve of a written edge")
        if vertices is not None:
            # the 3D curve is fitted, and ends within its tolerance of them;
            # over the range the edge got, which for a periodic pcurve the
            # kernel may have moved by whole periods
            first, last = BRep_Tool.Range_s(edge)
            fitted = BRep_Tool.Curve_s(edge, first, last)
            for vertex, parameter in zip(ends, (first, last)):
                vertices.cover(vertex, fitted.Value(parameter))
        return Edge(edge)

    def _write_wire(
        self,
        lifted: Wire,
        cutters: list[Plane] | None = None,
        surface: Geom_Surface | None = None,
    ) -> Wire:
        """A uv-plane wire written along its traversal

        With ``cutters`` the edges are cut along the seams and each piece is
        moved into the surface's own range, which a wire standing alone
        wants; a face's wires are written where they lie, on its ``surface``.
        """
        edges = []
        for edge in lifted.order_edges():
            backwards = edge.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
            pieces = [edge] if cutters is None else _edge_pieces(edge, cutters)
            for piece in reversed(pieces) if backwards else pieces:
                written = self._write_edge(
                    piece if cutters is None else self._in_range(piece), surface
                )
                if backwards:
                    written = Edge(TopoDS.Edge(written.wrapped.Reversed()))
                edges.append(written)
        return Wire(edges)

    def _oriented(
        self, lifted: Wire, clockwise: bool, surface: Geom_Surface | None = None
    ) -> Wire:
        """The wire written and turned to run the required way about the
        FORWARD face normal, whichever way the planar wire and the map run"""
        written = self._write_wire(lifted, surface=surface)
        if _is_clockwise(lifted) != clockwise:
            written = Wire(TopoDS.Wire(written.wrapped.Reversed()))
        return written

    def _write_face(self, lifted: Face, surface: Geom_Surface | None = None) -> Face:
        """A uv-plane face written onto the surface and placed with the
        target face, carrying its orientation so that its normal is the
        target's

        ``surface`` is the face's surface trimmed, for a face across a seam;
        the pcurves of its edges have to be on the surface it is built on.
        """
        surface = self._surface if surface is None else surface
        outer = self._oriented(lifted.outer_wire(), False, surface)
        maker = BRepBuilderAPI_MakeFace(surface, outer.wrapped, True)
        for inner in lifted.inner_wires():
            maker.Add(self._oriented(inner, True, surface).wrapped)
        if not maker.IsDone():
            raise RuntimeError("could not build the written face")
        face = TopoDS.Face(maker.Face().Oriented(self.face.wrapped.Orientation()))
        return _as_face(face).moved(self._placement)


# ---------------------------------------------------------------------------
# curves on the uv plane
# ---------------------------------------------------------------------------


def _is_clockwise(wire: Wire) -> bool:
    """Whether a closed wire on Plane.XY runs clockwise about z

    The wire bounds a face on the plane, whose normal is +z: run clockwise
    it is the boundary of a hole, and the face is everything outside of it,
    the point at infinity included.
    """
    face = BRepBuilderAPI_MakeFace(gp_Pln(), wire.wrapped, False).Face()
    classifier = IntTools_FClass2d(face, TOLERANCE)
    return classifier.PerformInfinitePoint() == TopAbs_State.TopAbs_IN


def _outline_runs(outline: Wire) -> list[_Run]:
    """A closed uv-plane wire as runs along its edges, anticlockwise"""
    runs = [
        _Run(
            edge,
            edge.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED,
            edge.position_at(0),
            edge.position_at(1),
        )
        for edge in outline.order_edges()
    ]
    if _is_clockwise(outline):
        runs = [
            _Run(run.edge, not run.backwards, run.end, run.start) for run in runs[::-1]
        ]
    return runs


def _on_line(edge: Edge, axis: Vector, value: float) -> bool:
    """Whether a uv-plane edge lies along the line where the parameter along
    ``axis`` is ``value``"""
    return all(
        abs(edge.position_at(i / 4).dot(axis) - value) < _ON_LINE for i in range(5)
    )


def _spans_on_line(
    shape: Shape, axis: Vector, value: float
) -> list[tuple[float, float]]:
    """The spans of the other parameter covered by a uv-plane shape's edges
    along the line where the parameter along ``axis`` is ``value``"""
    across = Vector(axis.Y, axis.X, 0)  # the other parameter's direction
    spans = []
    for edge in shape.edges():
        if _on_line(edge, axis, value):
            ends = edge.position_at(0).dot(across), edge.position_at(1).dot(across)
            spans.append((min(ends), max(ends)))
    return spans


def _merged(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Spans of a parameter joined where they touch"""
    merged: list[list[float]] = []
    for low, high in sorted(spans):
        if merged and low - merged[-1][1] <= _ON_LINE:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    return [(span[0], span[1]) for span in merged]


def _same_spans(
    one: list[tuple[float, float]], other: list[tuple[float, float]]
) -> bool:
    """Whether two sets of spans cover the same stretches of a parameter"""
    one, other = _merged(one), _merged(other)
    return len(one) == len(other) and all(
        abs(a - c) <= _SAME_POINT and abs(b - d) <= _SAME_POINT
        for (a, b), (c, d) in zip(one, other)
    )


def _chained(runs: list[_Run]) -> list[list[_Run]]:
    """Runs joined end to start into closed loops

    Raises:
        ValueError: a run has nothing to carry on to
    """
    remaining = list(runs)
    loops = []
    while remaining:
        loop = [remaining.pop(0)]
        while (loop[-1].end - loop[0].start).length > _SAME_POINT:
            following = next(
                (
                    run
                    for run in remaining
                    if (run.start - loop[-1].end).length <= _SAME_POINT
                ),
                None,
            )
            if following is None:
                raise ValueError(
                    "the shape goes once round the face but its two sides do "
                    "not meet along their whole length"
                )
            remaining.remove(following)
            loop.append(following)
        loops.append(loop)
    return loops


def _signed_area(loop: list[_Run]) -> float:
    """Twice the area a loop of runs encloses on the uv plane, positive when
    it runs anticlockwise; sampled, which is enough to tell which way"""
    points = [
        run.edge.position_at(
            1 - i / 8 if run.edge.position_at(0) != run.start else i / 8
        )
        for run in loop
        for i in range(8)
    ]
    return sum(a.X * b.Y - b.X * a.Y for a, b in zip(points, points[1:] + points[:1]))


def _surface_periods(surface: Geom_Surface) -> list[Period]:
    """The periodic directions of a surface on the uv plane"""
    u_start, _, v_start, _ = surface.Bounds()
    periods = []
    if surface.IsUPeriodic():
        periods.append((Vector(1, 0, 0), u_start, surface.UPeriod()))
    if surface.IsVPeriodic():
        periods.append((Vector(0, 1, 0), v_start, surface.VPeriod()))
    return periods


def _overlaps_wrapped(shape: Shape, axis: Vector, period: float, extent: float) -> bool:
    """Whether a uv-plane shape spanning ``extent`` along a periodic ``axis``
    would overlap itself once wrapped: whether it meets its own image, moved
    by any whole number of periods it spans, in more than isolated points

    A shape sheared along the axis, a helical band say, can span several
    periods and wrap without meeting itself. One wider than a period meets
    itself in a region, and one exactly a period wide along its own edge,
    which the kernel's seam cannot represent either.
    """
    for k in range(1, ceil(extent / period) + 1):
        common = shape & shape.moved(Location(axis * (k * period)))
        if any(edge.length > TOLERANCE for edge in common.edges()):
            return True
    return False


def _periods_crossed(low: float, high: float, period: float) -> list[int]:
    """The multiples of the period between two parameter values"""
    # touching a seam is not crossing it
    return [
        k
        for k in range(ceil(low / period), floor(high / period) + 1)
        if low + 1e-9 < k * period < high - 1e-9
    ]


def _split_all(shape: Piece, cutter: Plane) -> list[Piece]:
    """Every piece of a shape either side of a cutter, the shape itself when
    the cutter misses it"""
    pieces = shape.split(cutter, keep=Keep.ALL)
    return list(pieces) if pieces else [shape]


def _edge_pieces(edge: Edge, cutters: list[Plane]) -> list[Edge]:
    """An edge cut by the given planes, pieces in the edge's own direction"""
    pieces = [edge]
    for cutter in cutters:
        pieces = [part for piece in pieces for part in _split_all(piece, cutter)]
    if len(pieces) > 1:
        pieces.sort(key=lambda piece: edge.param_at_point(piece.position_at(0.5)))
    return pieces


def _affine_image(
    flat: Geom2d_Curve, first: float, last: float, map_: Matrix
) -> tuple[Geom2d_Curve, float, float]:
    """The exact image of a 2D curve span under an affine map, with the
    parameter range that covers the span

    Lines and conics stay analytic, with their range scaled or shifted to
    match; anything else becomes a B-spline with transformed poles, which
    keeps its parameters.
    """
    basis = flat
    if isinstance(basis, Geom2d_TrimmedCurve):
        basis = basis.BasisCurve()
    if isinstance(basis, Geom2d_Line):
        start = map_.multiply(Vector(basis.Location().X(), basis.Location().Y(), 0))
        # the linear part only, length included: a line's parameter is
        # distance along it, scaled by the map
        direction = Vector(basis.Direction().X(), basis.Direction().Y(), 0)
        direction = map_.multiply(direction) - map_.multiply(Vector())
        scale = direction.length
        line = Geom2d_Line(
            gp_Pnt2d(start.X, start.Y), gp_Dir2d(direction.X, direction.Y)
        )
        return line, first * scale, last * scale
    if isinstance(basis, Geom2d_Circle):
        return _conic_image(basis, map_, basis.Radius(), basis.Radius(), first, last)
    if isinstance(basis, Geom2d_Ellipse):
        return _conic_image(
            basis, map_, basis.MajorRadius(), basis.MinorRadius(), first, last
        )
    spline = Geom2dConvert.CurveToBSplineCurve_s(
        flat
        if isinstance(flat, Geom2d_BSplineCurve)
        else Geom2d_TrimmedCurve(flat, first, last)
    )
    for i in range(1, spline.NbPoles() + 1):
        pole = spline.Pole(i)
        image = map_.multiply(Vector(pole.X(), pole.Y(), 0))
        spline.SetPole(i, gp_Pnt2d(image.X, image.Y))
    return spline, first, last


def _conic_image(
    conic: Geom2d_Circle | Geom2d_Ellipse,
    map_: Matrix,
    major: float,
    minor: float,
    first: float,
    last: float,
) -> tuple[Geom2d_Curve, float, float]:
    """A circle or ellipse under an affine map is an ellipse (or circle)

    A point of the conic is ``centre + C @ (cos t, sin t)`` where C's columns
    are its axes scaled by its radii, so its image is ``centre' + L @ (cos t,
    sin t)`` with ``L = map @ C``. The SVD ``L = left @ diag(s) @ right``
    reads as: turn the unit circle by ``right`` (still a circle), stretch it
    by ``s`` along the axes (now an ellipse with semi-axes s), turn it by
    ``left``. So the singular values are the image's semi-axes, the columns
    of ``left`` its axis directions, and ``right`` says where the source
    angle t lands: at image angle t + rotation, or rotation - t when the map
    mirrors. The edge's range is shifted (and reversed) accordingly rather
    than the curve re-parameterised.
    """
    axes = conic.Position()
    centre = map_.multiply(Vector(axes.Location().X(), axes.Location().Y(), 0))
    x_dir = Vector(axes.XDirection().X(), axes.XDirection().Y(), 0) * major
    y_dir = Vector(axes.YDirection().X(), axes.YDirection().Y(), 0) * minor
    # the conic's own map from the unit circle, acting in the plane only, so
    # that the zero scale across the plane sorts last in the decomposition
    circle_to_conic = Matrix(
        [[x_dir.X, y_dir.X, 0, 0], [x_dir.Y, y_dir.Y, 0, 0], [0, 0, 0, 0]]
    )
    left, scales, right = map_.multiply(circle_to_conic).svd()
    # in-plane axes of the image; keep them right-handed about the plane
    handed = 1.0 if left[2, 2] > 0 else -1.0
    axis_x = Vector(left[0, 0], left[1, 0], 0)
    axis_y = Vector(left[0, 1], left[1, 1], 0) * handed
    image_axes = gp_Ax22d(
        gp_Pnt2d(centre.X, centre.Y),
        gp_Dir2d(axis_x.X, axis_x.Y),
        gp_Dir2d(axis_y.X, axis_y.Y),
    )
    image: Geom2d_Curve
    if abs(scales.X - scales.Y) < 1e-9 * scales.X:
        image = Geom2d_Circle(image_axes, scales.X)
    else:
        image = Geom2d_Ellipse(image_axes, scales.X, scales.Y)
    # the in-plane block of ``right``, with its second row flipped when the
    # second axis was, so that left @ diag @ right is unchanged
    r00, r01 = right[0, 0], right[0, 1]
    r10, r11 = right[1, 0] * handed, right[1, 1] * handed
    rotation = atan2(r10, r00)
    if r00 * r11 - r01 * r10 > 0:
        return image, first + rotation, last + rotation
    # mirrored: image angle is rotation - t. The reversed curve's point at p is
    # the image's at -p, so its parameter is t - rotation, and increases with t
    return image.Reversed(), first - rotation, last - rotation


# ---------------------------------------------------------------------------
# maps for each kind of surface
# ---------------------------------------------------------------------------


def _frame_directions(face: Face, location: Location) -> tuple[Vector, Vector, Vector]:
    """Origin, flat x direction and flat y direction in 3D, on the face"""
    origin = location.position
    normal = face.normal_at(origin)
    x_dir = location.x_axis.direction
    x_dir = (x_dir - normal * x_dir.dot(normal)).normalized()
    y_dir = normal.cross(x_dir)
    return origin, x_dir, y_dir


def _affine_map(face: Face, location: Location) -> Matrix:
    """The flat-to-uv map of a plane or cylinder as a Matrix

    The surface's u and v directions are orthogonal, so a flat direction's
    rate of change of u is its component along the u derivative divided by
    that derivative's squared length, and likewise for v. For a plane that
    is the identity in the plane's own axes; for a cylinder u runs at
    1/radius per unit of arc. Both are constant over the surface, so the map
    is the exact unrolling everywhere, not only at the origin.
    """
    origin, x_dir, y_dir = _frame_directions(face, location)
    u0, v0 = face.param_at_point(origin, normalize=False)
    d_u, d_v = (
        face.derivative_at(u0, v0, *order, normalize=False) for order in _ORDERS[:2]
    )
    d_u, d_v = d_u / d_u.dot(d_u), d_v / d_v.dot(d_v)
    return Matrix(
        [
            [x_dir.dot(d_u), y_dir.dot(d_u), 0, u0],
            [x_dir.dot(d_v), y_dir.dot(d_v), 0, v0],
            [0, 0, 1, 0],
        ]
    )


class _ConeSector(NamedTuple):
    """A cone unrolled into a sector about its apex, with a frame's flat axes
    laid in the sector's plane

    In OCCT's cone, u is the angle about the axis and v the distance along
    a generatrix from the reference circle of radius R at half-angle a. The
    radius at v is R + v sin(a), so the apex sits at v = -R / sin(a) and a
    point at v is |v - v_apex| from it; unrolled, it sits at that distance
    from the sector's centre at sector angle u |sin(a)|. sin(a) is negative
    when the cone narrows with increasing v, and then the apex lies at
    larger v.
    """

    scale: float
    """Sector angle per radian of u"""
    sign: float
    """+1 when the cone widens with increasing v, -1 when it narrows"""
    v_apex: float
    """The apex's v"""
    phi0: float
    """The sector angle of the frame's origin"""
    base: Vector
    """The frame's origin in the sector's plane, the apex at its centre"""
    sector_x: Vector
    """Flat x in the sector's plane"""
    sector_y: Vector
    """Flat y in the sector's plane"""


def _cone_sector(face: Face, location: Location) -> _ConeSector:
    """The sector a cone unrolls into, for the frame at a location"""
    cone = BRepAdaptor_Surface(face.wrapped).Cone()
    s = sin(cone.SemiAngle())
    sign = 1.0 if s > 0 else -1.0
    v_apex = -cone.RefRadius() / s
    scale = abs(s)

    origin, x_dir, y_dir = _frame_directions(face, location)
    u0, v0 = face.param_at_point(origin, normalize=False)
    rho0 = (v0 - v_apex) * sign  # distance from the apex
    phi0 = u0 * scale
    # flat axes in the sector plane, from the 3D directions' components
    # along the circumferential (u) and generatrix (v) directions
    d_u, d_v = (
        face.derivative_at(u0, v0, *order, normalize=False) for order in _ORDERS[:2]
    )
    e_u, e_v = d_u.normalized(), d_v.normalized()
    around = Vector(-sin(phi0), cos(phi0), 0)  # increasing u
    radial = Vector(cos(phi0), sin(phi0), 0) * sign  # increasing v
    return _ConeSector(
        scale,
        sign,
        v_apex,
        phi0,
        Vector(cos(phi0), sin(phi0), 0) * rho0,
        around * x_dir.dot(e_u) + radial * x_dir.dot(e_v),
        around * y_dir.dot(e_u) + radial * y_dir.dot(e_v),
    )


def _cone_map(face: Face, location: Location) -> PointMap:
    """The exact unrolling of a cone: a sector about the apex

    A flat point is placed in the sector's plane and read back as its angle
    about the apex, which gives u, and its distance from it, which gives v.
    """
    sector = _cone_sector(face, location)

    def to_uv(x: float, y: float) -> tuple[float, float]:
        q = sector.base + sector.sector_x * x + sector.sector_y * y
        # sector angle, continuous with the origin's
        phi = atan2(q.Y, q.X)
        phi += 2 * pi * round((sector.phi0 - phi) / (2 * pi))
        return phi / sector.scale, sector.v_apex + sector.sign * q.length

    return to_uv


def _cone_inverse_map(face: Face, location: Location) -> PointMap:
    """:func:`_cone_map` run backwards: (u, v) to the flat (x, y) of the
    frame at a location

    The unrolling is an isometry, so this lays the cone out flat exactly.
    A circle about the axis becomes an arc about the image of the apex,
    which is the image of any u at the apex's v, and a generatrix a line
    through it. u is taken as given rather than brought into one turn, so
    parameters a period apart land a sector apart, as successive turns of the
    cone rolled along the plane do.
    """
    sector = _cone_sector(face, location)

    def to_flat(u: float, v: float) -> tuple[float, float]:
        rho, phi = (v - sector.v_apex) * sector.sign, u * sector.scale
        q = Vector(cos(phi), sin(phi), 0) * rho - sector.base
        return q.dot(sector.sector_x), q.dot(sector.sector_y)

    return to_flat


def _sphere_map(face: Face, location: Location) -> PointMap:
    """Azimuthal equidistant projection about the location

    A flat point at distance d and bearing b is placed d along the great
    circle leaving the origin at bearing b. Lengths along rays from the
    origin are exact; a circle of radius d about the origin is scaled by
    sin(d/R) / (d/R). No map from a plane to a sphere preserves everything.
    """
    sphere = BRepAdaptor_Surface(face.wrapped).Sphere()
    radius = sphere.Radius()
    centre = Vector(sphere.Location())
    origin, x_dir, y_dir = _frame_directions(face, location)
    n0 = (origin - centre) / radius
    u0, _ = face.param_at_point(origin, normalize=False)
    position = sphere.Position()
    sphere_x = Vector(position.XDirection())
    sphere_y = Vector(position.YDirection())
    sphere_z = Vector(position.Direction())

    def to_uv(x: float, y: float) -> tuple[float, float]:
        d = hypot(x, y)
        if d < 1e-15:
            point = n0
        else:
            heading = (x_dir * x + y_dir * y) / d
            point = n0 * cos(d / radius) + heading * sin(d / radius)
        u = atan2(point.dot(sphere_y), point.dot(sphere_x))
        u += 2 * pi * round((u0 - u) / (2 * pi))
        v = asin(max(-1.0, min(1.0, point.dot(sphere_z))))
        return u, v

    return to_uv


def _geodesic_map(face: Face, location: Location, tolerance: float) -> PointMap:
    """The exponential map of a surface about the frame's origin

    A flat point at bearing b and distance d from the origin is placed d
    along the geodesic that leaves the origin in the tangent direction at
    bearing b. Lengths along rays from the origin are exact and directions
    at the origin are kept; away from it the surface's curvature distorts,
    as it must, since only developable surfaces flatten without distortion.
    On those, and on a sphere, this is the same map as the closed forms.

    The geodesic is integrated in parameter space: with S the surface, its
    first derivatives S_u, S_v and the second derivatives folded with the
    velocity into W = S_uu u'^2 + 2 S_uv u'v' + S_vv v'^2, a geodesic
    satisfies (u'', v'') = -(the components of W along S_u, S_v), the
    acceleration that keeps the velocity in the tangent plane. scipy's
    Dormand-Prince integrator does the stepping, with steps capped so that
    its error estimate stays trustworthy against the surface's features.

    Values are cached by flat point, since the sampled image of a curve
    revisits its points as it refines.
    """
    origin, x_dir, y_dir = _frame_directions(face, location)
    u0, v0 = face.param_at_point(origin, normalize=False)
    s_u0, s_v0 = (
        face.derivative_at(u0, v0, *order, normalize=False) for order in _ORDERS[:2]
    )
    # the tolerance is in 3D; the integrator's in parameters
    parameter_tolerance = tolerance / 10 / max(s_u0.length, s_v0.length)

    def derivatives(u: float, v: float) -> tuple[Vector, ...]:
        return tuple(
            face.derivative_at(u, v, *order, normalize=False) for order in _ORDERS
        )

    @cache
    def to_uv(x: float, y: float) -> tuple[float, float]:
        length = hypot(x, y)
        if length < 1e-15:
            return u0, v0
        heading = (x_dir * x + y_dir * y) / length
        return _geodesic_end(
            derivatives,
            (u0, v0),
            _components(s_u0, s_v0, heading),
            length,
            parameter_tolerance,
        )

    return to_uv


def _geodesic_end(
    derivatives: Callable[[float, float], tuple[Vector, ...]],
    start: tuple[float, float],
    velocity: tuple[float, float],
    length: float,
    tolerance: float,
) -> tuple[float, float]:
    """The parameters a geodesic reaches after ``length`` along a surface

    It leaves the parameters ``start`` with the parameter ``velocity`` of a
    unit tangent, on the surface whose ``derivatives`` at (u, v) are S_u,
    S_v, S_uu, S_vv and S_uv; :func:`_geodesic_map` has the equation.
    ``tolerance`` is the integrator's, in parameters.

    Raises:
        ValueError: the geodesic runs into a pole
    """

    def geodesic(_: float, state) -> list[float]:
        """The geodesic equation as a first order system in (u, v, u', v')"""
        u, v, d_u, d_v = state
        s_u, s_v, s_uu, s_vv, s_uv = derivatives(u, v)
        w = s_uu * (d_u * d_u) + s_uv * (2 * d_u * d_v) + s_vv * (d_v * d_v)
        acceleration = _components(s_u, s_v, w)
        return [d_u, d_v, -acceleration[0], -acceleration[1]]

    solution = solve_ivp(
        geodesic,
        (0.0, length),
        [*start, *velocity],
        method="RK45",
        rtol=1e-9,
        atol=tolerance,
        max_step=length / 8,
    )
    if not solution.success:
        raise ValueError("a geodesic from the frame's origin runs into a pole")
    return solution.y[0, -1], solution.y[1, -1]


def _components(s_u: Vector, s_v: Vector, vector: Vector) -> tuple[float, float]:
    """(a, b) such that a S_u + b S_v is the part of ``vector`` in the
    tangent plane spanned by the surface derivatives

    Raises:
        ValueError: the derivatives are parallel or one vanishes, as at a
            pole of the surface
    """
    e, f, g = s_u.dot(s_u), s_u.dot(s_v), s_v.dot(s_v)
    det = e * g - f * f
    if det <= 1e-16 * max(e, g) ** 2:
        raise ValueError("the frame's origin or a geodesic from it is at a pole")
    p, q = vector.dot(s_u), vector.dot(s_v)
    return (g * p - f * q) / det, (e * q - f * p) / det
