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
    and y as v, as a planar shape in its own right. There it is split along
    the seams of a periodic surface, which are known exactly as parameter
    lines: the kernel's own faces stop at a seam and continue on the other
    side as another face, and the frame does the same. Each piece is moved by
    whole periods into the surface's own range and then written, its edges
    given the piece's curves as pcurves. So write_face returns one face per
    period the shape reaches into, and a wire gets a vertex where it
    crosses. A shape spanning a whole turn or more, or one surrounding a
    pole, is refused.
    Pieces from one shape meet along the seam, so once thickened they are
    best joined into one tool before a boolean with the target solid.

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
from math import asin, atan2, ceil, cos, floor, hypot, pi, sin

from scipy.integrate import solve_ivp

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace
from OCP.BRepLib import BRepLib
from OCP.BRepTools import BRepTools
from OCP.Geom import Geom_Curve, Geom_Surface
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
from OCP.gp import gp_Ax22d, gp_Dir2d, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Vec
from OCP.ShapeAnalysis import ShapeAnalysis_Surface
from OCP.TopAbs import TopAbs_Orientation
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

from build123d.build_enums import GeomType, Keep
from build123d.geometry import TOLERANCE, Location, Matrix, Plane, Vector, VectorLike

from .one_d import Edge, Wire
from .shape_core import Shape, ShapeList
from .two_d import Face

PointMap = Callable[[float, float], tuple[float, float]]
"""A map from flat (x, y) to the (u, v) parameters of a surface"""

Period = tuple[Vector, float, float]
"""A periodic direction of a surface on the uv plane: its unit vector there,
where the surface's own range starts along it, and the period"""


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
            return cls(face, _ConeMap(face, location), tolerance)
        if kind == GeomType.SPHERE:
            return cls(face, _sphere_map(face, location), tolerance)
        return cls(face, _GeodesicMap(face, location, tolerance), tolerance)

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
            ValueError: the wire spans a whole turn of the surface or more,
                or surrounds a pole

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
        target's normal. A shape that crosses the surface's seam is split
        there, so the list holds one face per period the shape reaches into;
        otherwise it holds one face.

        Args:
            planar (Face): a planar face on ``Plane.XY``

        Raises:
            ValueError: the shape spans a whole turn of the surface or more,
                or surrounds a pole

        Returns:
            ShapeList[Face]: faces on the target's surface
        """
        return ShapeList(
            self._write_face(self._in_range(piece))
            for piece in self._pieces(self._lift_face(planar))
        )

    def punch(self, planar: Face) -> list[Face]:
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
            list[Face]: the punched face, then any islands
        """
        lifted = self._lift_face(planar)
        if len(self._pieces(lifted)) > 1:
            raise ValueError("an outline crossing the face's seam cannot be punched")
        # the face in its own frame, where the written wires are
        local = TopoDS.Face(self.face.wrapped.Located(TopLoc_Location()))
        maker = BRepBuilderAPI_MakeFace(local)
        # the outline becomes a hole: clockwise about the face normal
        maker.Add(self._oriented(lifted.outer_wire(), clockwise=True).wrapped)
        punched = TopoDS.Face(maker.Face().Oriented(self.face.wrapped.Orientation()))
        islands = [self._write_face(Face(island)) for island in lifted.inner_wires()]
        return [Face(punched).moved(self._placement), *islands]

    # ---- the uv plane ----

    def _lift_edge(self, edge: Edge) -> Edge:
        """The planar edge's image laid on the uv plane

        Exact under a ``Matrix`` map: a line, a conic, or a B-spline with
        transformed poles. Otherwise interpolated through mapped samples and
        refined until it is within the tolerance in 3D.

        Raises:
            ValueError: the map jumps along the edge, as it does along the
                outline of a shape surrounding a pole of the face
        """
        curve, first, last = _edge_curve(edge)
        if isinstance(self.mapping, Matrix):
            image, first, last = _affine_image(
                GeomAPI.To2d_s(curve, gp_Pln()), first, last, self.mapping
            )
            exact = GeomAPI.To3d_s(image, gp_Pln())
            return Edge(BRepBuilderAPI_MakeEdge(exact, first, last).Edge())

        def uv_at(t: float) -> Vector:
            point = curve.Value(t)
            return self.to_uv(point.X(), point.Y())

        periods = self._periods()
        segments = 8
        for _ in range(8):
            params = [
                first + (last - first) * i / segments for i in range(segments + 1)
            ]
            uvs = [uv_at(t) for t in params]
            jumps = any(
                abs((b - a).dot(axis)) > period / 2
                for a, b in zip(uvs, uvs[1:])
                for axis, _, period in periods
            )
            lifted = Edge.make_spline(
                list[VectorLike](uvs), parameters=params, tol=1e-9
            )
            spline = _edge_curve(lifted)[0]
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
        return lifted

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
        return Face(
            self._lift_wire(planar.outer_wire()),
            [self._lift_wire(wire) for wire in planar.inner_wires()],
        )

    def _point(self, uv: Vector) -> Vector:
        """The point of the surface at a uv-plane point"""
        return Vector(self._surface.Value(uv.X, uv.Y))

    def _periods(self) -> list[Period]:
        """The periodic directions of the surface on the uv plane"""
        u_start, _, v_start, _ = self._surface.Bounds()
        periods = []
        if self._surface.IsUPeriodic():
            periods.append((Vector(1, 0, 0), u_start, self._surface.UPeriod()))
        if self._surface.IsVPeriodic():
            periods.append((Vector(0, 1, 0), v_start, self._surface.VPeriod()))
        return periods

    def _seam_cutters(self, lifted: Shape) -> list[Plane]:
        """Planes across the uv plane along the seam lines a mapped shape
        crosses: the parameter lines a whole number of periods from the start
        of the surface's range

        Raises:
            ValueError: the shape spans a whole turn of the surface or more
        """
        cutters = []
        for axis, start, period in self._periods():
            reached = [point.dot(axis) - start for point in _outline_samples(lifted)]
            cutters += [
                Plane(axis * (start + k * period), z_dir=axis)
                for k in _periods_crossed(min(reached), max(reached), period)
            ]
        return cutters

    def _pieces(self, lifted: Face) -> list[Face]:
        """The mapped face split along every seam line that crosses it"""
        pieces = [lifted]
        for cutter in self._seam_cutters(lifted):
            pieces = [part for piece in pieces for part in _split_all(piece, cutter)]
        return pieces

    def _in_range(self, piece):
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
        for axis, start, period in self._periods():
            shift += axis * (floor((centre.dot(axis) - start) / period) * period)
        return piece.moved(Location(-shift)) if shift.length else piece

    # ---- the surface ----
    #
    # Written in the surface's own frame; the public methods place the
    # result with the face.

    def _write_edge(self, lifted: Edge) -> Edge:
        """A uv-plane edge written onto the surface, its curve the pcurve"""
        curve, first, last = _edge_curve(lifted)
        pcurve = GeomAPI.To2d_s(curve, gp_Pln())
        edge = BRepBuilderAPI_MakeEdge(pcurve, self._surface, first, last).Edge()
        if not BRepLib.BuildCurves3d_s(
            edge, min(self.tolerance, 1e-5), GeomAbs_Shape.GeomAbs_C1, 14, 0
        ):
            raise RuntimeError("could not build the 3D curve of a written edge")
        return Edge(edge)

    def _write_wire(self, lifted: Wire, cutters: list[Plane] | None = None) -> Wire:
        """A uv-plane wire written along its traversal

        With ``cutters`` the edges are cut along the seams and each piece is
        moved into the surface's own range, which a wire standing alone
        wants; a face's wires come already cut and moved.
        """
        edges = []
        for edge in lifted.order_edges():
            backwards = edge.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
            pieces = [edge] if cutters is None else _edge_pieces(edge, cutters)
            for piece in reversed(pieces) if backwards else pieces:
                written = self._write_edge(
                    piece if cutters is None else self._in_range(piece)
                )
                if backwards:
                    written = Edge(TopoDS.Edge(written.wrapped.Reversed()))
                edges.append(written)
        return Wire(edges)

    def _oriented(self, lifted: Wire, clockwise: bool) -> Wire:
        """The wire written and turned to run the required way about the
        FORWARD face normal, whichever way the planar wire and the map run"""
        written = self._write_wire(lifted)
        if (_signed_area(lifted) < 0) != clockwise:
            written = Wire(TopoDS.Wire(written.wrapped.Reversed()))
        return written

    def _write_face(self, lifted: Face) -> Face:
        """A uv-plane face written onto the surface and placed with the
        target face, carrying its orientation so that its normal is the
        target's"""
        outer = self._oriented(lifted.outer_wire(), clockwise=False)
        maker = BRepBuilderAPI_MakeFace(self._surface, outer.wrapped, True)
        for inner in lifted.inner_wires():
            maker.Add(self._oriented(inner, clockwise=True).wrapped)
        if not maker.IsDone():
            raise RuntimeError("could not build the written face")
        face = TopoDS.Face(maker.Face().Oriented(self.face.wrapped.Orientation()))
        return Face(face).moved(self._placement)


# ---------------------------------------------------------------------------
# curves on the uv plane
# ---------------------------------------------------------------------------


def _edge_curve(edge: Edge) -> tuple[Geom_Curve, float, float]:
    """An edge's curve, in place, and its parameter range"""
    first, last = BRep_Tool.Range_s(edge.wrapped)
    return BRep_Tool.Curve_s(edge.wrapped, first, last), first, last


def _signed_area(wire: Wire, samples: int = 16) -> float:
    """The area a closed planar wire encloses, positive when it runs
    counter-clockwise about z, by Green's theorem over sampled points"""
    points = [
        edge.position_at(i / samples)
        for edge in wire.order_edges()
        for i in range(samples + 1)
    ]
    return 0.5 * sum(
        a.X * b.Y - b.X * a.Y for a, b in zip(points, points[1:] + points[:1])
    )


def _periods_crossed(low: float, high: float, period: float) -> list[int]:
    """The multiples of the period between two parameter values

    Raises:
        ValueError: the values are a period or more apart
    """
    if high - low >= period - 1e-9:
        raise ValueError(
            "the shape spans a whole turn of the face or more, and would "
            "overlap itself"
        )
    # touching a seam is not crossing it
    return [
        k
        for k in range(ceil(low / period), floor(high / period) + 1)
        if low + 1e-9 < k * period < high - 1e-9
    ]


def _outline_samples(shape: Shape) -> list[Vector]:
    """Points along a planar shape's edges, enough to bound its reach"""
    samples = [Vector(vertex.X, vertex.Y, 0) for vertex in shape.vertices()]
    for edge in shape.edges():
        samples += [edge.position_at(i / 8) for i in range(1, 8)]
    return samples


def _split_all(shape, cutter) -> list:
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
    # mirrored: image angle is rotation - t, so walk the reversed curve
    return image.Reversed(), rotation - last, rotation - first


# ---------------------------------------------------------------------------
# maps for each kind of surface
# ---------------------------------------------------------------------------


def _frame_axes(face: Face, location: Location) -> tuple[Vector, Vector, Vector]:
    """Origin, flat x direction and flat y direction in 3D, on the face"""
    origin = location.position
    normal = face.normal_at(origin)
    x_dir = location.x_axis.direction
    x_dir = (x_dir - normal * x_dir.dot(normal)).normalized()
    y_dir = normal.cross(x_dir)
    return origin, x_dir, y_dir


def _derivatives(face: Face, u: float, v: float) -> tuple[Vector, Vector]:
    """The surface's partial derivatives at (u, v)"""
    point, d_u, d_v = gp_Pnt(), gp_Vec(), gp_Vec()
    BRepAdaptor_Surface(face.wrapped).D1(u, v, point, d_u, d_v)
    return Vector(d_u), Vector(d_v)


def _project(face: Face, point: Vector) -> tuple[float, float]:
    """Parameters of a point on the face, within the face's own uv range"""
    location = TopLoc_Location()
    surface = BRep_Tool.Surface_s(face.wrapped, location)
    local = point.to_pnt().Transformed(location.Transformation().Inverted())
    uv = ShapeAnalysis_Surface(surface).ValueOfUV(local, TOLERANCE)
    u, v = uv.X(), uv.Y()
    if surface.IsUPeriodic():
        u_min, u_max, _, _ = BRepTools.UVBounds_s(face.wrapped)
        period = surface.UPeriod()
        u += period * round(((u_min + u_max) / 2 - u) / period)
    return u, v


def _affine_map(face: Face, location: Location) -> Matrix:
    """The flat-to-uv map of a plane or cylinder as a Matrix

    The surface's u and v directions are orthogonal, so a flat direction's
    rate of change of u is its component along the u derivative divided by
    that derivative's squared length, and likewise for v. For a plane that
    is the identity in the plane's own axes; for a cylinder u runs at
    1/radius per unit of arc. Both are constant over the surface, so the map
    is the exact unrolling everywhere, not only at the origin.
    """
    origin, x_dir, y_dir = _frame_axes(face, location)
    u0, v0 = _project(face, origin)
    d_u, d_v = _derivatives(face, u0, v0)
    d_u, d_v = d_u / d_u.dot(d_u), d_v / d_v.dot(d_v)
    return Matrix(
        [
            [x_dir.dot(d_u), y_dir.dot(d_u), 0, u0],
            [x_dir.dot(d_v), y_dir.dot(d_v), 0, v0],
            [0, 0, 1, 0],
        ]
    )


class _ConeMap:
    """The exact unrolling of a cone: a sector about the apex

    In OCCT's cone, u is the angle about the axis and v the distance along
    a generatrix from the reference circle of radius R at half-angle a. The
    radius at v is R + v sin(a), so the apex sits at v = -R / sin(a) and a
    point at v is |v - v_apex| from it; unrolled, it sits at that distance
    from the sector's centre at sector angle u |sin(a)|. sin(a) is negative
    when the cone narrows with increasing v, and then the apex lies at
    larger v.
    """

    def __init__(self, face: Face, location: Location):
        cone = BRepAdaptor_Surface(face.wrapped).Cone()
        s = sin(cone.SemiAngle())
        self.sign = 1.0 if s > 0 else -1.0
        self.v_apex = -cone.RefRadius() / s
        self.scale = abs(s)  # sector angle per radian of u

        origin, x_dir, y_dir = _frame_axes(face, location)
        u0, v0 = _project(face, origin)
        rho0 = (v0 - self.v_apex) * self.sign  # distance from the apex
        self.phi0 = u0 * self.scale
        # flat axes in the sector plane, from the 3D directions' components
        # along the circumferential (u) and generatrix (v) directions
        d_u, d_v = _derivatives(face, u0, v0)
        e_u, e_v = d_u.normalized(), d_v.normalized()
        around = Vector(-sin(self.phi0), cos(self.phi0), 0)  # increasing u
        radial = Vector(cos(self.phi0), sin(self.phi0), 0) * self.sign  # increasing v
        self.sector_x = around * x_dir.dot(e_u) + radial * x_dir.dot(e_v)
        self.sector_y = around * y_dir.dot(e_u) + radial * y_dir.dot(e_v)
        self.base = Vector(cos(self.phi0), sin(self.phi0), 0) * rho0

    def __call__(self, x: float, y: float) -> tuple[float, float]:
        q = self.base + self.sector_x * x + self.sector_y * y
        # sector angle, continuous with the origin's
        phi = atan2(q.Y, q.X)
        phi += 2 * pi * round((self.phi0 - phi) / (2 * pi))
        return phi / self.scale, self.v_apex + self.sign * q.length


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
    origin, x_dir, y_dir = _frame_axes(face, location)
    n0 = (origin - centre) / radius
    u0, _ = _project(face, origin)
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


class _GeodesicMap:
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

    def __init__(self, face: Face, location: Location, tolerance: float):
        self._surface = BRepAdaptor_Surface(face.wrapped)
        origin, self._x_dir, self._y_dir = _frame_axes(face, location)
        self._origin = _project(face, origin)
        s_u, s_v = self._derivatives(*self._origin)[:2]
        # the tolerance is in 3D; the integrator's in parameters
        self._tolerance = tolerance / 10 / max(s_u.length, s_v.length)
        self._cache: dict[tuple[float, float], tuple[float, float]] = {}

    def __call__(self, x: float, y: float) -> tuple[float, float]:
        key = (x, y)
        if key not in self._cache:
            self._cache[key] = self._integrate(x, y)
        return self._cache[key]

    def _integrate(self, x: float, y: float) -> tuple[float, float]:
        length = hypot(x, y)
        u, v = self._origin
        if length < 1e-15:
            return u, v
        heading = (self._x_dir * x + self._y_dir * y) / length
        s_u, s_v = self._derivatives(u, v)[:2]
        solution = solve_ivp(
            self._geodesic,
            (0.0, length),
            [u, v, *_components(s_u, s_v, heading)],
            method="RK45",
            rtol=1e-9,
            atol=self._tolerance,
            max_step=length / 8,
        )
        if not solution.success:
            raise ValueError("a geodesic from the frame's origin runs into a pole")
        return solution.y[0, -1], solution.y[1, -1]

    def _derivatives(self, u: float, v: float) -> list[Vector]:
        """S_u, S_v, S_uu, S_vv, S_uv at (u, v)"""
        vectors = [gp_Vec() for _ in range(5)]
        self._surface.D2(u, v, gp_Pnt(), *vectors)
        return [Vector(vector) for vector in vectors]

    def _geodesic(self, _: float, state) -> list[float]:
        """The geodesic equation as a first order system in (u, v, u', v')"""
        u, v, d_u, d_v = state
        s_u, s_v, s_uu, s_vv, s_uv = self._derivatives(u, v)
        w = s_uu * (d_u * d_u) + s_uv * (2 * d_u * d_v) + s_vv * (d_v * d_v)
        acceleration = _components(s_u, s_v, w)
        return [d_u, d_v, -acceleration[0], -acceleration[1]]


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
