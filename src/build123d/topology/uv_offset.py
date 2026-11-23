"""
build123d topology

name: uv_offset.py
by:   Gumyr
date: November 23, 2026

desc:

    Offset a face within its own surface.

    Growing or shrinking a face moves its boundary a distance along the
    surface, square to itself. On a plane that is the planar offset. On a
    surface that unrolls without distortion it is the planar offset too: the
    face is laid out flat, offset there, and written back through a UVFrame,
    so every kind of corner the planar offset makes is available and nothing
    is fitted in 3D.

    A plane and a cylinder unroll through an affine map of their parameters,
    which keeps lines as lines and conics as conics. A cone unrolls into a
    sector about its apex: its generators become lines through the apex and
    its parallels arcs about it, which are recognized as such, as is any
    other edge whose flat image is a line or an arc, so that the planar
    offset is given the same curves it would be given on a plane.

    A cylinder closes on itself, and its unrolling does not. The flat face
    is therefore laid out once for every turn its offset can reach, a period
    apart, and the copies are joined where they meet:

    * a face that goes all the way round has seam sides that are not part of
      its boundary; joined to its neighbours it is a strip without them, so
      only the real boundary is offset;
    * a face grown until it meets itself round the cylinder joins the copy of
      itself it meets, and becomes a strip as well.

    One period of a strip is kept and written as a face with a seam edge; of
    anything else one copy is kept and written where it lies, across the seam
    or not.

    A cone closes on itself too, and a turn of it is a turn about the apex,
    by the angle of its sector. The flat plane has only one whole circle
    about the apex to lay turns out in, so no more of a neighbouring turn is
    laid out than the offset can reach, and the work is refused when even
    that does not fit: round a cone too nearly flat, or too near its apex.
    The apex itself has no place in a face written through a UVFrame, and a
    face that reaches it, or an offset that would, is refused as well.

    The result is written onto the whole of the surface the face lies on, not
    the face's own, which may be trimmed to the face.

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

from math import asin, atan2, ceil, cos, degrees, hypot, pi, sin
from typing import TYPE_CHECKING, NamedTuple

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.Geom import Geom_RectangularTrimmedSurface
from OCP.GeomAbs import GeomAbs_JoinType
from OCP.Standard import Standard_ConstructionError, Standard_Failure
from OCP.StdFail import StdFail_NotDone
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

from build123d.build_enums import GeomType, Kind
from build123d.geometry import (
    TOLERANCE,
    Axis,
    Location,
    Matrix,
    Plane,
    Vector,
    VectorLike,
)

from .one_d import Edge, Wire, _offset_curves_to_bsplines
from .shape_core import Shape, ShapeList
from .utils import _make_topods_face_from_wires
from .uv_write import (
    Period,
    PointMap,
    UVFrame,
    _as_face,
    _cone_inverse_map,
    _cone_map,
    _cone_sector,
    _surface_periods,
)

if TYPE_CHECKING:  # pragma: no cover
    from .two_d import Face

_JOINS = {
    Kind.ARC: GeomAbs_JoinType.GeomAbs_Arc,
    Kind.INTERSECTION: GeomAbs_JoinType.GeomAbs_Intersection,
    Kind.TANGENT: GeomAbs_JoinType.GeomAbs_Tangent,
}
"""The kernel's name for each kind of corner"""

_NO_AREA = TOLERANCE
"""The area under which a flat face is no face: what is left of an outline
offset inwards until it closes on itself"""

_AT_START = 1e-6
"""How far before the start of a period a flat face may begin and still be
the copy that belongs to that period; a bounding box is a little loose"""

_SHORT_OF_A_CIRCLE = 1e-3
"""How far short of a whole circle about the apex, in radians, the flat work
on an unrolled cone has to stay, so that it does not meet itself there"""

_NEIGHBOUR = 0.05
"""The least of a neighbouring turn, in radians about the apex, laid out
beside a face that goes round a cone"""


def offset_face_2d(
    face: Face, amount: float, kind: Kind = Kind.ARC, tolerance: float = 1e-4
) -> ShapeList[Face]:
    """A face grown or shrunk within its own surface

    Args:
        face (Face): a planar, cylindrical or conical face
        amount (float): how far the boundary moves along the surface;
            positive grows the face, negative shrinks it
        kind (Kind, optional): the corners of the offset boundary. Defaults
            to Kind.ARC.
        tolerance (float, optional): largest 3D error allowed where a curve
            has to be interpolated. Defaults to 1e-4.

    Raises:
        ValueError: the face is on a surface that is not handled
        ValueError: nothing is left of the face
        ValueError: the face reaches the apex of its cone, or its offset
            would; or it goes round a cone too nearly flat, or too near the
            apex, for its offset to be laid out
        RuntimeError: the planar offset failed

    Returns:
        ShapeList[Face]: the faces of the result, more than one where
        shrinking parts the face
    """
    if face.geom_type in (GeomType.PLANE, GeomType.CYLINDER):
        route = _offset_affine
    elif face.geom_type == GeomType.CONE:
        route = _offset_cone
    else:
        raise ValueError(
            "only a planar, cylindrical or conical face can be offset within "
            "its surface"
        )
    if amount == 0:
        return ShapeList([face])
    pieces, frame = route(face, amount, kind, tolerance)
    if not pieces:
        raise ValueError("nothing is left of the face")
    return ShapeList(written for piece in pieces for written in frame.write_face(piece))


def _offset_affine(
    face: Face, amount: float, kind: Kind, tolerance: float
) -> tuple[list[Face], UVFrame]:
    """A planar or cylindrical face offset on its flat pattern: the flat
    faces of the result and the frame that writes them back

    The pattern is the face's outline in its parameters, scaled to lengths.
    """
    carrier, periods = _carrier(face)
    developed = face.uv_face
    middle = developed.bounding_box().center()
    lengths = [
        face.derivative_at(middle.X, middle.Y, *order, normalize=False).length
        for order in ((1, 0), (0, 1))
    ]
    # flat lengths to parameters and back; exact for lines and conics
    to_uv = Matrix([[1 / lengths[0], 0, 0, 0], [0, 1 / lengths[1], 0, 0], [0, 0, 1, 0]])
    to_flat = Matrix([[lengths[0], 0, 0, 0], [0, lengths[1], 0, 0], [0, 0, 1, 0]])
    flat = _upward(UVFrame(carrier, to_flat).lift(developed))

    if periods:
        axis, start, period = periods[0]
        scale = abs(axis.X * lengths[0] + axis.Y * lengths[1])
        pieces = _offset_round(
            flat, amount, kind, (axis, start * scale, period * scale)
        )
    else:
        pieces = _offset_flat(flat, amount, kind)
    return pieces, UVFrame(carrier, to_uv, tolerance)


def _carrier(face: Face) -> tuple[Face, list[Period]]:
    """A face over the whole of the surface a face lies on, placed and
    oriented as the face is, and that surface's periods

    A face offset outwards leaves its own bounds, and can leave those of its
    surface too when that is trimmed to it, as the surface of a face written
    across a seam is. The result is written onto this face instead.
    """
    location = TopLoc_Location()
    surface = BRep_Tool.Surface_s(face.wrapped, location)
    while isinstance(surface, Geom_RectangularTrimmedSurface):
        surface = surface.BasisSurface()
    whole = BRepBuilderAPI_MakeFace(surface, TOLERANCE).Face()
    placed = whole.Located(location).Oriented(face.wrapped.Orientation())
    return _as_face(TopoDS.Face(placed)), _surface_periods(surface)


# ---------------------------------------------------------------------------
# round a periodic surface
# ---------------------------------------------------------------------------


def _offset_round(flat: Face, amount: float, kind: Kind, turn: Period) -> list[Face]:
    """A flat face offset as the unrolling of a face on a surface that closes
    on itself along ``turn``, a period given in flat lengths: one period's
    worth of the result"""
    axis, start, length = turn
    reach = 1 + ceil(abs(amount) / length)
    turns = [Location(axis * (k * length)) for k in range(-reach, reach + 1)]

    box = flat.bounding_box()
    if (box.max - box.min).dot(axis) >= length - _AT_START:
        # all the way round, or as good as: its turns join into a strip, and
        # the sides where they join are not boundary
        sources = _joined([flat.moved(turn) for turn in turns])
        regions = [
            part for source in sources for part in _offset_flat(source, amount, kind)
        ]
    else:
        parts = _offset_flat(flat, amount, kind)
        # each part with its neighbours a turn away, joined where it has
        # grown into them
        regions = _joined([part.moved(turn) for part in parts for turn in turns])

    window = _window(regions, axis, start, length) if regions else None
    pieces: list[Face] = []
    for region in regions:
        box = region.bounding_box()
        low = box.min.dot(axis)
        if (box.max - box.min).dot(axis) >= length - _AT_START and _faces(
            region.intersect(region.moved(Location(axis * length)))
        ):
            # it meets itself a turn on: a strip, of which one period is kept
            assert window is not None
            pieces += _faces(region.intersect(window))
        elif start - _AT_START <= low < start + length - _AT_START:
            pieces.append(region)  # the copy that starts in the surface's range
    return pieces


def _window(regions: list[Face], axis: Vector, start: float, length: float) -> Face:
    """A flat rectangle over one period along ``axis`` from ``start``, tall
    enough across it to cover every region"""
    across = Vector(axis.Y, axis.X, 0)
    lows = [region.bounding_box().min.dot(across) for region in regions]
    highs = [region.bounding_box().max.dot(across) for region in regions]
    low, high = min(lows) - 1.0, max(highs) + 1.0
    corners = [
        axis * start + across * low,
        axis * (start + length) + across * low,
        axis * (start + length) + across * high,
        axis * start + across * high,
    ]
    return _region(Wire.make_polygon(corners, close=True))


# ---------------------------------------------------------------------------
# round a cone
# ---------------------------------------------------------------------------


class _Sector(NamedTuple):
    """The flat plane about the apex of an unrolled cone

    Angles are measured about the apex from the direction of the middle of
    the face, anticlockwise, so that the face lies either side of zero and a
    turn of the cone is ``turn`` further round.
    """

    apex: Vector
    centre: Vector
    """The unit direction from the apex to the middle of the face"""
    turn: float
    """The angle of the sector a whole turn of the cone unrolls into"""

    def angle(self, point: Vector) -> float:
        """The angle of a flat point about the apex"""
        offset = point - self.apex
        return atan2(self.centre.cross(offset).Z, self.centre.dot(offset))

    def wedge(self, low: float, high: float, radius: float) -> Face:
        """The flat face between two angles about the apex, reaching at
        least ``radius`` from it"""
        steps = max(1, ceil((high - low) / (pi / 6)))
        step = (high - low) / steps
        side = Vector(-self.centre.Y, self.centre.X, 0)
        reach = radius / cos(step / 2)  # the chords stay outside the radius
        rim = [
            self.apex
            + (self.centre * cos(low + i * step) + side * sin(low + i * step)) * reach
            for i in range(steps + 1)
        ]
        return _region(Wire.make_polygon([self.apex, *rim], close=True))

    def turned(self, flat: Face, turns: int) -> Face:
        """A flat face moved a number of turns of the cone about the apex"""
        return flat.rotate(Axis(self.apex, (0, 0, 1)), degrees(turns * self.turn))


def _offset_cone(
    face: Face, amount: float, kind: Kind, tolerance: float
) -> tuple[list[Face], UVFrame]:
    """A conical face offset on its flat pattern: the flat faces of the
    result and the frame that writes them back

    The pattern is the cone unrolled about its apex, with the middle of the
    face at the flat origin.

    Raises:
        ValueError: the face reaches the apex, or its offset would
        ValueError: the offset cannot be laid out about the apex
    """
    carrier, _ = _carrier(face)
    developed = face.uv_face
    box = developed.bounding_box()
    middle = box.center()
    origin = Vector(BRepAdaptor_Surface(face.wrapped).Value(middle.X, middle.Y))
    location = Location(
        Plane(
            origin=origin,
            x_dir=face.derivative_at(middle.X, middle.Y, 1, 0, normalize=False),
            z_dir=face.normal_at(origin),
        )
    )
    cone = _cone_sector(face, location)
    # how far from the apex the face's near and far ends are
    nearest, furthest = sorted(
        (v - cone.v_apex) * cone.sign for v in (box.min.Y, box.max.Y)
    )
    if nearest <= tolerance:
        raise ValueError(
            "a face that reaches the apex of its cone cannot be offset within it"
        )
    # the frame may give its origin a parameter whole turns from the face's
    u_origin = face.param_at_point(origin, normalize=False)[0]
    turns = round((middle.X - u_origin) / (2 * pi))
    if turns:
        developed = developed.moved(Location((-turns * 2 * pi, 0, 0)))

    to_flat = _cone_inverse_map(face, location)
    flat = _upward(_flattened(developed, to_flat, tolerance))
    apex = Vector(*to_flat(u_origin, cone.v_apex))
    sector = _Sector(apex, (Vector() - apex).normalized(), 2 * pi * cone.scale)

    # all the way round: a turn wide, measured where the cone is widest
    round_the_cone = (
        abs(box.max.X - box.min.X - 2 * pi) * cone.scale * furthest <= _AT_START
    )

    def at_the_apex(flats: list[Face]) -> bool:
        return any(flat.distance_to(apex) <= tolerance for flat in flats)

    if round_the_cone:
        pieces = _offset_round_cone(flat, amount, kind, sector, nearest)
    else:
        pieces = _offset_flat(flat, amount, kind)
        if not at_the_apex(pieces):
            pieces = _into_one_turn(pieces, sector)
    if at_the_apex(pieces):
        raise ValueError("the offset reaches the apex of the cone")
    return pieces, UVFrame(carrier, _cone_map(face, location), tolerance)


def _offset_round_cone(
    flat: Face, amount: float, kind: Kind, sector: _Sector, nearest: float
) -> list[Face]:
    """The unrolling of a face that goes all the way round a cone, offset:
    one turn's worth of the result

    The flat face is a turn wide, and its two straight sides are where it
    meets itself, not boundary. Enough of the turn either side is laid out
    beside it that the cut ends of those neighbours, which are offset as if
    they were boundary, are too far off to reach the turn that is kept.
    ``nearest`` is how near the apex the face comes.

    Raises:
        ValueError: the offset reaches too near the apex, or the neighbours
            do not fit about it
    """
    # the cut end of a neighbour reaches the kept turn within ``amount`` of
    # it; half as much again is allowed for
    ratio = 1.5 * abs(amount) / nearest
    if ratio >= 1:
        raise ValueError("the offset reaches too near the apex of the cone")
    spare = (2 * pi - _SHORT_OF_A_CIRCLE - sector.turn) / 2
    beside = max(asin(ratio), min(_NEIGHBOUR, spare))
    if beside > spare:
        raise ValueError(
            "the cone is too nearly flat for a face that goes round it to be "
            "offset by this much"
        )
    radius = _reach(sector.apex, [flat])
    half = sector.turn / 2
    strip = [flat]
    laid, turns = 0.0, 1
    while laid < beside:
        width = min(sector.turn, beside - laid)
        # the start of the turn after, and the end of the turn before
        for wedge, way in (
            (sector.wedge(-half, -half + width, radius), turns),
            (sector.wedge(half - width, half, radius), -turns),
        ):
            strip += [
                sector.turned(piece, way) for piece in _faces(flat.intersect(wedge))
            ]
        laid += width
        turns += 1
    regions = [
        part for source in _joined(strip) for part in _offset_flat(source, amount, kind)
    ]
    if not regions:
        return []
    window = sector.wedge(-half, half, _reach(sector.apex, regions))
    return [piece for region in regions for piece in _faces(region.intersect(window))]


def _into_one_turn(parts: list[Face], sector: _Sector) -> list[Face]:
    """The parts of an offset laid out about the apex, brought into the turn
    about the middle of the face

    Parts within half a turn of the middle are left as they are. One that
    reaches further has grown round the cone into the next turn, where its
    own neighbour is: it is cut along the rays half a turn either side of
    the middle and every turn beyond, each piece is brought back a whole
    number of turns, and the pieces are joined where they meet. A part that
    has met itself round the cone comes out a turn wide.

    Raises:
        ValueError: the parts reach all the way round the apex
    """
    reaches = [
        abs(sector.angle(edge.position_at(i / 16)))
        for part in parts
        for edge in part.outer_wire().edges()
        for i in range(17)
    ]
    half = sector.turn / 2
    if not reaches or max(reaches) < half - 1e-9:
        return parts
    if max(reaches) >= pi - _SHORT_OF_A_CIRCLE:
        raise ValueError("the cone is too nearly flat for this offset to be laid out")
    radius = _reach(sector.apex, parts)
    pieces: list[Face] = []
    beyond = ceil((max(reaches) - half) / sector.turn)
    for turns in range(-beyond, beyond + 1):
        low = max((turns - 0.5) * sector.turn, -pi + _SHORT_OF_A_CIRCLE / 2)
        high = min((turns + 0.5) * sector.turn, pi - _SHORT_OF_A_CIRCLE / 2)
        if low >= high:
            continue
        wedge = sector.wedge(low, high, radius)
        pieces += [
            sector.turned(piece, -turns)
            for part in parts
            for piece in _faces(part.intersect(wedge))
        ]
    return _joined(pieces)


def _reach(apex: Vector, flats: list[Face]) -> float:
    """A distance from the apex past the furthest of some flat faces"""
    furthest = 0.0
    for flat in flats:
        box = flat.bounding_box()
        furthest = max(
            furthest,
            *(
                hypot(x - apex.X, y - apex.Y)
                for x in (box.min.X, box.max.X)
                for y in (box.min.Y, box.max.Y)
            ),
        )
    return furthest + 1.0


def _flattened(developed: Face, to_flat: PointMap, tolerance: float) -> Face:
    """A face's outline in its parameters, a face on the uv plane, laid out
    flat through a map from (u, v) to flat (x, y)"""

    def flat_wire(wire: Wire) -> Wire:
        return Wire(
            [
                flat
                for edge in wire.order_edges()
                for flat in _flat_edges(edge, to_flat, tolerance)
            ]
        )

    return _as_face(
        _make_topods_face_from_wires(
            flat_wire(developed.outer_wire()).wrapped,
            [flat_wire(wire).wrapped for wire in developed.inner_wires()],
        )
    )


def _flat_edges(edge: Edge, to_flat: PointMap, tolerance: float) -> list[Edge]:
    """The flat image of one uv-plane edge

    A line where the image is straight to within the tolerance and an arc
    where it is circular - two arcs for a whole circle - so that the planar
    offset has lines and arcs to work with; otherwise a spline through
    mapped points, refined until it is within the tolerance.

    Raises:
        ValueError: the spline cannot be brought within the tolerance
    """

    def image(position: float) -> Vector:
        uv = edge.position_at(position)
        return Vector(*to_flat(uv.X, uv.Y))

    count = 16
    points = [image(i / count) for i in range(count + 1)]
    start, end = points[0], points[-1]
    closed = (end - start).length <= tolerance
    if not closed:
        chord = end - start
        if all(
            abs(chord.cross(point - start).Z) <= tolerance * chord.length
            for point in points
        ):
            return [Edge.make_line(start, end)]
    circle = _circle(start, points[count // 3], points[2 * count // 3])
    if circle is not None and all(
        abs((point - circle[0]).length - circle[1]) <= tolerance for point in points
    ):
        if closed:
            return [
                Edge.make_three_point_arc(start, points[4], points[8]),
                Edge.make_three_point_arc(points[8], points[12], start),
            ]
        return [Edge.make_three_point_arc(start, points[count // 2], end)]
    while True:
        spline = (
            Edge.make_spline(list[VectorLike](points[:-1]), periodic=True)
            if closed
            else Edge.make_spline(list[VectorLike](points))
        )
        error = max(spline.distance_to(image((i + 0.5) / count)) for i in range(count))
        if error <= tolerance:
            return [spline]
        if count >= 1024:
            raise ValueError(
                f"the flat image of an edge is still {error:.3g} from the edge, "
                f"over the tolerance of {tolerance}"
            )
        count *= 2
        points = [image(i / count) for i in range(count + 1)]


def _circle(
    first: Vector, second: Vector, third: Vector
) -> tuple[Vector, float] | None:
    """The centre and radius of the circle through three flat points, none
    when they are in a line"""
    one, other = second - first, third - first
    twice_area = one.cross(other).Z
    if abs(twice_area) <= 1e-12 * max(one.length, other.length) ** 2:
        return None
    centre = first + Vector(
        (other.Y * one.dot(one) - one.Y * other.dot(other)) / (2 * twice_area),
        (one.X * other.dot(other) - other.X * one.dot(one)) / (2 * twice_area),
        0,
    )
    return centre, (centre - first).length


# ---------------------------------------------------------------------------
# on the plane
# ---------------------------------------------------------------------------


def _offset_flat(flat: Face, amount: float, kind: Kind) -> list[Face]:
    """A face on Plane.XY grown or shrunk within the plane: every part of
    what is left, none when nothing is

    The outline moves outwards by ``amount`` and each hole's the other way,
    as the planar offset operation has them. An outline moved inwards can
    part into several, and a hole grown can cut the face in two.
    """
    regions = _enclosed(_offset_wire(flat.outer_wire(), amount, kind))
    holes = [
        hole
        for inner in flat.inner_wires()
        for hole in _enclosed(_offset_wire(inner, -amount, kind))
    ]
    if not holes:
        return regions
    return [part for region in regions for part in _faces(region.cut(*holes))]


def _enclosed(wires: list[Wire]) -> list[Face]:
    """The flat faces that the wires one closed wire was offset into enclose

    An outline moved outwards until it closes on itself, as that of a C does,
    comes back as the wire round the outside and another round the gap left
    in the middle: a wire inside another is the outline of a hole in it. The
    wires of one offset never cross, so a point of one says whether it is
    inside another.
    """
    loops = [_region(wire) for wire in wires]
    loops = sorted(
        (loop for loop in loops if loop.area > _NO_AREA),
        key=lambda loop: loop.area,
        reverse=True,
    )
    if len(loops) < 2:
        return loops
    points = [loop.vertices()[0].center() for loop in loops]
    # the larger loops each loop is inside, largest first
    around = [
        [outer for outer in range(inner) if loops[outer].is_inside(points[inner])]
        for inner in range(len(loops))
    ]
    enclosed: list[Face] = []
    for index, loop in enumerate(loops):
        if len(around[index]) % 2:
            continue  # the outline of a hole
        holes = [
            loops[inner]
            for inner in range(index + 1, len(loops))
            if around[inner] and around[inner][-1] == index
        ]
        enclosed += _faces(loop.cut(*holes)) if holes else [loop]
    return enclosed


def _offset_wire(wire: Wire, distance: float, kind: Kind) -> list[Wire]:
    """The closed wires a closed wire on Plane.XY becomes when what it
    encloses is grown by ``distance``, or shrunk for a negative one

    Shrinking can part the wire into several, or leave nothing. Growing can
    close the wire on itself, and it then comes back as the wire round the
    outside and one round each gap left inside.

    Raises:
        RuntimeError: the kernel could not offset the wire, or lost a gap
            the wire closed round
    """
    edges = list(wire.order_edges())
    if len(edges) == 1:
        # the kernel's offset goes wrong on a wire of a single edge
        wire = Wire([edges[0].trim(0.0, 0.5), edges[0].trim(0.5, 1.0)])
    offset_wires = _kernel_offset(wire, distance, kind)
    if offset_wires is None:
        # What a wire encloses reaches at least its area over its length
        # from the wire, and shrunk by less than that it cannot have gone
        if distance > 0 or _region(wire).area > -distance * wire.length:
            raise RuntimeError(f"2D offset failed with distance {distance}")
        return []  # shrunk to nothing
    if distance > 0 and kind != Kind.ARC:
        # With corners that are not arcs the kernel returns a wire that has
        # closed on itself without the gaps inside, as if it were solid
        rounded = _kernel_offset(wire, distance, Kind.ARC)
        if rounded is not None and len(rounded) != len(offset_wires):
            raise RuntimeError(
                f"2D offset with {kind} closes the outline on itself and loses "
                "the gap inside; Kind.ARC keeps it"
            )
    return offset_wires


def _kernel_offset(wire: Wire, distance: float, kind: Kind) -> list[Wire] | None:
    """The kernel's planar offset of a closed wire: the wires it returns,
    none when it does not manage

    The kernel fails to move inwards some arcs that a boolean has left, and
    moves the same arcs made again from three of their points, so a wire
    with arcs is tried both ways. It also fails on some large wires that it
    manages at an ordinary size, so what it fails on as it is is tried again
    scaled to one.
    """
    attempts = [wire]
    edges = list(wire.order_edges())
    if any(edge.geom_type == GeomType.CIRCLE for edge in edges):
        attempts.append(
            Wire(
                [
                    (
                        Edge.make_three_point_arc(
                            *(edge.position_at(along) for along in (0.0, 0.5, 1.0))
                        )
                        if edge.geom_type == GeomType.CIRCLE
                        else edge
                    )
                    for edge in edges
                ]
            )
        )
    for attempt in attempts:
        offset_wires = _kernel_try(attempt, distance, kind)
        if offset_wires is not None:
            return offset_wires
    ordinary = 10 / wire.bounding_box().diagonal
    for attempt in attempts:
        offset_wires = _kernel_try(
            attempt.scale(ordinary, (0, 0, 0)), distance * ordinary, kind
        )
        if offset_wires is not None:
            return [
                offset_wire.scale(1 / ordinary, (0, 0, 0))
                for offset_wire in offset_wires
            ]
    return None


def _kernel_try(wire: Wire, distance: float, kind: Kind) -> list[Wire] | None:
    """One call of the kernel's planar offset on a closed wire: the wires it
    returns, with any offset curves among them made B-splines, or none when
    it fails"""
    builder = BRepOffsetAPI_MakeOffset()
    builder.Init(_JOINS[kind])
    builder.AddWire(wire.wrapped)
    try:
        builder.Perform(distance)
        done = builder.IsDone() and not builder.Shape().IsNull()
    except (
        RuntimeError,
        Standard_Failure,
        Standard_ConstructionError,
        StdFail_NotDone,
    ):
        done = False
    if not done:
        return None
    offset_wires = []
    explorer = TopExp_Explorer(builder.Shape(), TopAbs_ShapeEnum.TopAbs_WIRE)
    while explorer.More():
        offset_wire = Wire(TopoDS.Wire(explorer.Current()))
        offset_wires.append(_offset_curves_to_bsplines(offset_wire))
        explorer.Next()
    return offset_wires


def _region(wire: Wire) -> Face:
    """The flat face a closed wire on Plane.XY encloses, facing up"""
    return _upward(_as_face(_make_topods_face_from_wires(wire.wrapped)))


def _upward(flat: Face) -> Face:
    """A face on Plane.XY turned to face up, so that it combines with the
    others in a boolean"""
    return flat if flat.normal_at(flat.center()).Z > 0 else -flat


def _faces(result: Shape | ShapeList) -> list[Face]:
    """The faces of whatever a boolean returned"""
    shapes = result if isinstance(result, list) else [result]
    return [face for shape in shapes for face in shape.faces()]


def _joined(flats: list[Face]) -> list[Face]:
    """Flat faces joined where they meet or overlap: the separate regions
    they cover"""
    if len(flats) < 2:
        return flats
    return _faces(flats[0].fuse(*flats[1:]))
