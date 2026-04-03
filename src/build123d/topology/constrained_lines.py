"""
build123d topology

name: constrained_lines.py
by:   Gumyr
date: September 07, 2025

desc:

This module generates lines and arcs that are constrained against other objects.

license:

    Copyright 2025 Gumyr

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

from math import atan2, cos, isnan, sin
from typing import overload, TYPE_CHECKING, Callable, TypeVar
from typing import cast as tcast

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex
from OCP.BRepLib import BRepLib
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.Geom import Geom_Curve, Geom_Plane
from OCP.Geom2d import (
    Geom2d_CartesianPoint,
    Geom2d_Circle,
    Geom2d_Curve,
    Geom2d_Line,
    Geom2d_Point,
    Geom2d_TrimmedCurve,
)
from OCP.Geom2dAdaptor import Geom2dAdaptor_Curve
from OCP.Geom2dAPI import Geom2dAPI_ProjectPointOnCurve, Geom2dAPI_InterCurveCurve
from OCP.Geom2dGcc import (
    Geom2dGcc_Circ2d2TanOn,
    Geom2dGcc_Circ2d2TanRad,
    Geom2dGcc_Circ2d3Tan,
    Geom2dGcc_Circ2dTanCen,
    Geom2dGcc_Circ2dTanOnRad,
    Geom2dGcc_Lin2dTanObl,
    Geom2dGcc_Lin2d2Tan,
    Geom2dGcc_QualifiedCurve,
)
from OCP.GeomAPI import GeomAPI
from OCP.gp import (
    gp_Ax2d,
    gp_Ax3,
    gp_Circ2d,
    gp_Dir,
    gp_Dir2d,
    gp_Lin2d,
    gp_Pln,
    gp_Pnt,
    gp_Pnt2d,
)
from OCP.IntAna2d import IntAna2d_AnaIntersection
from OCP.Standard import Standard_ConstructionError, Standard_Failure
from OCP.TopoDS import TopoDS_Edge, TopoDS_Vertex

from build123d.build_enums import Sagitta, Tangency
from build123d.geometry import Axis, TOLERANCE, Vector, VectorLike
from .zero_d import Vertex
from .shape_core import ShapeList

if TYPE_CHECKING:
    from build123d.topology.one_d import Edge  # pragma: no cover

TWrap = TypeVar("TWrap")  # whatever the factory returns (Edge or a subclass)

# Reuse a single XY plane for 3D->2D projection and for 2D-edge building
_pln_xy = gp_Pln(gp_Ax3(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0)))
_surf_xy = Geom_Plane(_pln_xy)


# ---------------------------
# Normalization utilities
# ---------------------------
def _norm_on_period(u: float, first: float, period: float) -> float:
    """Map parameter u into [first, first+per)."""
    return (u - first) % period + first


def _forward_delta(u1: float, u2: float, first: float, period: float) -> float:
    """
    Forward (positive) delta from u1 to u2 on a periodic domain anchored at
    'first'.
    """
    u1n = _norm_on_period(u1, first, period)
    u2n = _norm_on_period(u2, first, period)
    delta = u2n - u1n
    if delta < 0.0:
        delta += period
    return delta


# ---------------------------
# Core helpers
# ---------------------------
def _edge_to_qualified_2d(
    edge: TopoDS_Edge, position_constaint: Tangency
) -> tuple[Geom2dGcc_QualifiedCurve, Geom2d_Curve, float, float, Geom2dAdaptor_Curve]:
    """Convert a TopoDS_Edge into 2d curve & extract properties"""

    # 1) Underlying curve + range (also retrieve location to be safe)
    hcurve3d = BRep_Tool.Curve_s(edge, float(), float())
    first, last = BRep_Tool.Range_s(edge)

    # 2) Convert to 2D on Plane.XY (Z-up frame at origin)
    hcurve2d = GeomAPI.To2d_s(hcurve3d, _pln_xy)  # -> Handle_Geom2d_Curve

    # 3) Wrap in an adaptor using the same parametric range
    adapt2d = Geom2dAdaptor_Curve(hcurve2d, first, last)

    # 4) Create the qualified curve (unqualified is fine here)
    qcurve = Geom2dGcc_QualifiedCurve(adapt2d, position_constaint.value)
    return qcurve, hcurve2d, first, last, adapt2d


def _edge_from_circle(h2d_circle: Geom2d_Circle, u1: float, u2: float) -> TopoDS_Edge:
    """Build a 3D edge on XY from a trimmed 2D circle segment [u1, u2]."""
    arc2d = Geom2d_TrimmedCurve(h2d_circle, u1, u2, True)  # sense=True
    circle_edge = BRepBuilderAPI_MakeEdge(arc2d, _surf_xy).Edge()
    BRepLib.BuildCurves3d_s(circle_edge)

    return circle_edge


def _param_in_trim(
    u: float | None, first: float | None, last: float | None, h2d: Geom2d_Curve | None
) -> bool:
    """Normalize (if periodic) then test [first, last] with tolerance."""
    if u is None or first is None or last is None or h2d is None:  # for typing
        raise TypeError("Invalid parameters to _param_in_trim")
    u = _norm_on_period(u, first, h2d.Period()) if h2d.IsPeriodic() else u
    return (u >= first - TOLERANCE) and (u <= last + TOLERANCE)


@overload
def _as_gcc_arg(
    obj: Edge, constaint: Tangency
) -> tuple[
    Geom2dGcc_QualifiedCurve, Geom2d_Curve | None, float | None, float | None, bool
]: ...
@overload
def _as_gcc_arg(
    obj: Vector, constaint: Tangency
) -> tuple[Geom2d_CartesianPoint, None, None, None, bool]: ...


def _as_gcc_arg(obj: Edge | Vector, constaint: Tangency) -> tuple[
    Geom2dGcc_QualifiedCurve | Geom2d_CartesianPoint,
    Geom2d_Curve | None,
    float | None,
    float | None,
    bool,
]:
    """
    Normalize input to a GCC argument.
    Returns: (q_obj, h2d, first, last, is_edge)
    - Edge -> (QualifiedCurve, h2d, first, last, True)
    - Vector -> (CartesianPoint, None, None, None, False)
    """
    if not obj:
        raise TypeError("Can't create a qualified curve from empty edge")

    if isinstance(obj.wrapped, TopoDS_Edge):
        return _edge_to_qualified_2d(obj.wrapped, constaint)[0:4] + (True,)

    gp_pnt = gp_Pnt2d(obj.X, obj.Y)
    return Geom2d_CartesianPoint(gp_pnt), None, None, None, False


def _two_arc_edges_from_params(
    circ: gp_Circ2d, u1: float, u2: float
) -> list[TopoDS_Edge]:
    """
    Given two parameters on a circle, return both the forward (minor)
    and complementary (major) arcs as TopoDS_Edge(s).
    Uses centralized normalization utilities.
    """
    h2d_circle = Geom2d_Circle(circ)
    period = h2d_circle.Period()  # usually 2*pi

    # Minor (forward) span
    d = _forward_delta(u1, u2, 0.0, period)  # anchor at 0 for circle convenience
    u1n = _norm_on_period(u1, 0.0, period)
    u2n = _norm_on_period(u2, 0.0, period)

    # Guard degeneracy
    if d <= TOLERANCE or abs(period - d) <= TOLERANCE:
        return ShapeList()

    minor = _edge_from_circle(h2d_circle, u1n, u1n + d)
    major = _edge_from_circle(h2d_circle, u2n, u2n + (period - d))
    return [minor, major]


def _edge_from_line(
    p1: gp_Pnt2d,
    p2: gp_Pnt2d,
) -> TopoDS_Edge:
    """
    Build a finite Edge from two 2D contact points.

    Parameters
    ----------
    p1, p2 : gp_Pnt2d
        Endpoints of the line segment (in 2D).
    edge_factory : type[Edge], optional
        Factory for building the Edge subtype (defaults to Edge).

    Returns
    -------
    TopoDS_Edge
        Finite line segment between the two points.
    """
    v1 = BRepBuilderAPI_MakeVertex(gp_Pnt(p1.X(), p1.Y(), 0)).Vertex()
    v2 = BRepBuilderAPI_MakeVertex(gp_Pnt(p2.X(), p2.Y(), 0)).Vertex()

    mk_edge = BRepBuilderAPI_MakeEdge(v1, v2)
    if not mk_edge.IsDone():
        raise RuntimeError("Failed to build edge from line contacts")
    return mk_edge.Edge()


def _gp_lin2d_from_axis(ax: Axis) -> gp_Lin2d:
    """Build a 2D reference line from an Axis (XY plane)."""
    p = gp_Pnt2d(ax.position.X, ax.position.Y)
    d = gp_Dir2d(ax.direction.X, ax.direction.Y)
    return gp_Lin2d(gp_Ax2d(p, d))


def _qstr(q) -> str:  # pragma: no cover
    """Debugging facility that works with OCP's GccEnt enum values"""
    try:
        from OCP.GccEnt import GccEnt_enclosed, GccEnt_enclosing, GccEnt_outside

        try:
            from OCP.GccEnt import GccEnt_unqualified
        except ImportError:
            # Some OCCT versions name this 'noqualifier'
            from OCP.GccEnt import GccEnt_noqualifier as GccEnt_unqualified
        mapping = {
            GccEnt_enclosed: "enclosed",
            GccEnt_enclosing: "enclosing",
            GccEnt_outside: "outside",
            GccEnt_unqualified: "unqualified",
        }
        return mapping.get(q, f"unknown({int(q)})")
    except Exception:
        # Fallback if enums aren't importable for any reason
        return str(int(q))


def _make_2tan_rad_arcs(
    *tangencies: tuple[Edge, Tangency] | Edge | Vector,  # 2
    radius: float,
    sagitta: Sagitta = Sagitta.SHORT,
    edge_factory: Callable[[TopoDS_Edge], Edge],
) -> ShapeList[Edge]:
    """
    Create all planar circular arcs of a given radius that are tangent/contacting
    the two provided objects on the XY plane.

    Inputs must be coplanar with ``Plane.XY``. Non-coplanar edges are not supported.

    Args:
        tangencies (tuple[Edge, PositionConstraint] | Edge | Vertex | VectorLike:
            Geometric entity to be contacted/touched by the circle(s)
        radius (float): Circle radius for all candidate solutions.

    Raises:
        ValueError: Invalid input
        ValueError: Invalid curve
        RuntimeError: no valid circle solutions found

    Returns:
        ShapeList[Edge]: A list of planar circular edges (on XY) representing both
            the minor and major arcs between the two tangency points for every valid
            circle solution.

    """

    # Unpack optional per-edge qualifiers (default UNQUALIFIED)
    tangent_tuples = [
        t if isinstance(t, tuple) else (t, Tangency.UNQUALIFIED) for t in tangencies
    ]

    # Build inputs for GCC
    results = [_as_gcc_arg(*t) for t in tangent_tuples]
    q_o: tuple[Geom2dGcc_QualifiedCurve, Geom2dGcc_QualifiedCurve]
    q_o, h_e, e_first, e_last, is_edge = map(tuple, zip(*results))

    gcc = Geom2dGcc_Circ2d2TanRad(*q_o, radius, TOLERANCE)
    if not gcc.IsDone() or gcc.NbSolutions() == 0:
        raise RuntimeError("Unable to find a tangent arc")

    def _ok(i: int, u: float) -> bool:
        """Does the given parameter value lie within the edge range?"""
        return (
            True if not is_edge[i] else _param_in_trim(u, e_first[i], e_last[i], h_e[i])
        )

    # ---------------------------
    # Solutions
    # ---------------------------
    solutions: list[TopoDS_Edge] = []
    for i in range(1, gcc.NbSolutions() + 1):
        circ: gp_Circ2d = gcc.ThisSolution(i)

        # Tangency on curve 1
        p1 = gp_Pnt2d()
        u_circ1, u_arg1 = gcc.Tangency1(i, p1)
        if not _ok(0, u_arg1):
            continue

        # Tangency on curve 2
        p2 = gp_Pnt2d()
        u_circ2, u_arg2 = gcc.Tangency2(i, p2)
        if not _ok(1, u_arg2):
            continue

        # qual1 = GccEnt_Position(int())
        # qual2 = GccEnt_Position(int())
        # gcc.WhichQualifier(i, qual1, qual2)  # returns two GccEnt_Position values
        # print(
        #     f"Solution {i}: "
        #     f"arg1={_qstr(qual1)}, arg2={_qstr(qual2)} | "
        #     f"u_circ=({u_circ1:.6g}, {u_circ2:.6g}) "
        #     f"u_arg=({u_arg1:.6g}, {u_arg2:.6g})"
        # )

        # Build BOTH sagitta arcs and select by LengthConstraint
        if sagitta == Sagitta.BOTH:
            solutions.extend(_two_arc_edges_from_params(circ, u_circ1, u_circ2))
        else:
            arcs = _two_arc_edges_from_params(circ, u_circ1, u_circ2)
            arcs = sorted(
                arcs, key=lambda e: GCPnts_AbscissaPoint.Length_s(BRepAdaptor_Curve(e))
            )
            solutions.append(arcs[sagitta.value])
    return ShapeList([edge_factory(e) for e in solutions])


def _make_2tan_on_arcs(
    *tangencies: tuple[Edge, Tangency] | Edge | Vector,  # 2
    center_on: Edge,
    sagitta: Sagitta = Sagitta.SHORT,
    edge_factory: Callable[[TopoDS_Edge], Edge],
) -> ShapeList[Edge]:
    """
    Create all planar circular arcs whose circle is tangent to two objects and whose
    CENTER lies on a given locus (line/circle/curve) on the XY plane.

    Notes
    -----
    - `center_on` is treated as a **center locus** (not a tangency target).
    """

    # Unpack optional per-edge qualifiers (default UNQUALIFIED)
    tangent_tuples = [
        t if isinstance(t, tuple) else (t, Tangency.UNQUALIFIED)
        for t in list(tangencies) + [center_on]
    ]

    # Build inputs for GCC
    results = [_as_gcc_arg(*t) for t in tangent_tuples]
    q_o: tuple[
        Geom2dGcc_QualifiedCurve, Geom2dGcc_QualifiedCurve, Geom2dGcc_QualifiedCurve
    ]
    q_o, h_e, e_first, e_last, is_edge = map(tuple, zip(*results))
    adapt_on = Geom2dAdaptor_Curve(h_e[2], e_first[2], e_last[2])

    # Provide initial middle guess parameters for all of the edges
    guesses: list[float] = [
        (e_last[i] - e_first[i]) / 2 + e_first[i]
        for i in range(len(tangent_tuples))
        if is_edge[i]
    ]

    if sum(is_edge) > 1:
        gcc = Geom2dGcc_Circ2d2TanOn(q_o[0], q_o[1], adapt_on, TOLERANCE, *guesses)
    else:
        assert isinstance(q_o[0], Geom2d_Point)
        assert isinstance(q_o[1], Geom2d_Point)
        gcc = Geom2dGcc_Circ2d2TanOn(q_o[0], q_o[1], adapt_on, TOLERANCE)

    if not gcc.IsDone() or gcc.NbSolutions() == 0:
        raise RuntimeError("Unable to find a tangent arc with center_on constraint")

    def _ok(i: int, u: float) -> bool:
        """Does the given parameter value lie within the edge range?"""
        return (
            True if not is_edge[i] else _param_in_trim(u, e_first[i], e_last[i], h_e[i])
        )

    # ---------------------------
    # Solutions
    # ---------------------------
    solutions: list[TopoDS_Edge] = []
    for i in range(1, gcc.NbSolutions() + 1):
        circ: gp_Circ2d = gcc.ThisSolution(i)

        # Tangency on curve 1
        p1 = gp_Pnt2d()
        u_circ1, u_arg1 = gcc.Tangency1(i, p1)
        if not _ok(0, u_arg1):
            continue

        # Tangency on curve 2
        p2 = gp_Pnt2d()
        u_circ2, u_arg2 = gcc.Tangency2(i, p2)
        if not _ok(1, u_arg2):
            continue

        # Build sagitta arc(s) and select by LengthConstraint
        if sagitta == Sagitta.BOTH:
            solutions.extend(_two_arc_edges_from_params(circ, u_circ1, u_circ2))
        else:
            arcs = _two_arc_edges_from_params(circ, u_circ1, u_circ2)
            arcs = sorted(
                arcs, key=lambda e: GCPnts_AbscissaPoint.Length_s(BRepAdaptor_Curve(e))
            )
            solutions.append(arcs[sagitta.value])

    return ShapeList([edge_factory(e) for e in solutions])


def _make_3tan_arcs(
    *tangencies: tuple[Edge, Tangency] | Edge | Vector,  # 3
    sagitta: Sagitta = Sagitta.SHORT,
    edge_factory: Callable[[TopoDS_Edge], Edge],
) -> ShapeList[Edge]:
    """
    Create planar circular arc(s) on XY tangent to three provided objects.

    The circle is determined by the three tangency constraints; the returned arc(s)
    are trimmed between the two tangency points corresponding to `tangencies[0]` and
    `tangencies[1]`. Use `sagitta` to select the shorter/longer (or both) arc.
    Inputs must be representable on Plane.XY.
    """

    # Unpack optional per-edge qualifiers (default UNQUALIFIED)
    tangent_tuples = [
        t if isinstance(t, tuple) else (t, Tangency.UNQUALIFIED) for t in tangencies
    ]

    # Build inputs for GCC
    results = [_as_gcc_arg(*t) for t in tangent_tuples]
    q_o: tuple[
        Geom2dGcc_QualifiedCurve, Geom2dGcc_QualifiedCurve, Geom2dGcc_QualifiedCurve
    ]
    q_o, h_e, e_first, e_last, is_edge = map(tuple, zip(*results))

    # Provide initial middle guess parameters for all of the edges
    guesses: tuple[float, float, float] = tuple(
        [(e_last[i] - e_first[i]) / 2 + e_first[i] for i in range(3)]
    )

    # Generate all valid circles tangent to the 3 inputs
    msg = "Unable to find a circle tangent to all three objects"
    try:
        gcc = Geom2dGcc_Circ2d3Tan(*q_o, TOLERANCE, *guesses)
    except (Standard_ConstructionError, Standard_Failure) as con_err:
        raise RuntimeError(msg) from con_err
    if not gcc.IsDone() or gcc.NbSolutions() == 0:
        raise RuntimeError(msg)

    def _ok(i: int, u: float) -> bool:
        """Does the given parameter value lie within the edge range?"""
        return (
            True if not is_edge[i] else _param_in_trim(u, e_first[i], e_last[i], h_e[i])
        )

    # ---------------------------
    # Enumerate solutions
    # ---------------------------
    out_topos: list[TopoDS_Edge] = []
    for i in range(1, gcc.NbSolutions() + 1):
        circ: gp_Circ2d = gcc.ThisSolution(i)

        # Look at all of the solutions
        # h2d_circle = Geom2d_Circle(circ)
        # arc2d = Geom2d_TrimmedCurve(h2d_circle, 0, 2 * pi, True)
        # out_topos.append(BRepBuilderAPI_MakeEdge(arc2d, _surf_xy).Edge())
        # continue

        # Tangency on curve 1 (arc endpoint A)
        p1 = gp_Pnt2d()
        u_circ1, u_arg1 = gcc.Tangency1(i, p1)
        if not _ok(0, u_arg1):
            continue

        # Tangency on curve 2 (arc endpoint B)
        p2 = gp_Pnt2d()
        u_circ2, u_arg2 = gcc.Tangency2(i, p2)
        if not _ok(1, u_arg2):
            continue

        # Tangency on curve 3 (validates circle; does not define arc endpoints)
        p3 = gp_Pnt2d()
        _u_circ3, u_arg3 = gcc.Tangency3(i, p3)
        if not _ok(2, u_arg3):
            continue

        # Build arc(s) between u_circ1 and u_circ2 per LengthConstraint
        if sagitta == Sagitta.BOTH:
            out_topos.extend(_two_arc_edges_from_params(circ, u_circ1, u_circ2))
        else:
            arcs = _two_arc_edges_from_params(circ, u_circ1, u_circ2)
            arcs = sorted(
                arcs,
                key=lambda e: GCPnts_AbscissaPoint.Length_s(BRepAdaptor_Curve(e)),
            )
            out_topos.append(arcs[sagitta.value])

    return ShapeList([edge_factory(e) for e in out_topos])


def _make_tan_cen_arcs(
    tangency: tuple[Edge, Tangency] | Edge | Vector,
    *,
    center: VectorLike | Vertex,
    edge_factory: Callable[[TopoDS_Edge], Edge],
) -> ShapeList[Edge]:
    """
    Create planar circle(s) on XY whose center is fixed and that are tangent/contacting
    a single object.

    Notes
    -----
    - With a **fixed center** and a single tangency constraint, the natural geometric
      result is a full circle; there are no second endpoints to define an arc span.
      This routine therefore returns closed circular edges (full 2π trims).
    - If the tangency target is a point (Vertex/VectorLike), the circle is the one
      centered at `center` and passing through that point (built directly).
    """

    # Unpack optional qualifier on the tangency arg (edges only)
    if isinstance(tangency, tuple):
        object_one, obj1_qual = tangency
    else:
        object_one, obj1_qual = tangency, Tangency.UNQUALIFIED

    # ---------------------------
    # Build fixed center (gp_Pnt2d)
    # ---------------------------
    if isinstance(center, Vertex):
        loc_xyz = center.position if center.position is not None else Vector(0, 0)
        base = Vector(center)
        c2d = gp_Pnt2d(base.X + loc_xyz.X, base.Y + loc_xyz.Y)
    else:
        v = Vector(center)
        c2d = gp_Pnt2d(v.X, v.Y)

    # ---------------------------
    # Tangency input
    # ---------------------------
    q_o1, h_e1, e1_first, e1_last, is_edge1 = _as_gcc_arg(object_one, obj1_qual)

    solutions_topo: list[TopoDS_Edge] = []

    # Case A: tangency target is a point -> circle passes through that point
    if not is_edge1 and isinstance(q_o1, Geom2d_CartesianPoint):
        p = q_o1.Pnt2d()
        # radius = distance(center, point)
        dx, dy = p.X() - c2d.X(), p.Y() - c2d.Y()
        r = (dx * dx + dy * dy) ** 0.5
        if r <= TOLERANCE:
            # Center coincides with point: no valid circle
            return ShapeList([])
        # Build full circle
        circ = gp_Circ2d(gp_Ax2d(c2d, gp_Dir2d(1.0, 0.0)), r)
        h2d = Geom2d_Circle(circ)
        per = h2d.Period()
        solutions_topo.append(_edge_from_circle(h2d, 0.0, per))

    else:
        assert isinstance(q_o1, Geom2dGcc_QualifiedCurve)
        # Case B: tangency target is a curve/edge (qualified curve)
        gcc = Geom2dGcc_Circ2dTanCen(q_o1, Geom2d_CartesianPoint(c2d), TOLERANCE)
        assert (
            gcc.IsDone() and gcc.NbSolutions() > 0
        ), "Unexpected: GCC failed to return a tangent circle"

        for i in range(1, gcc.NbSolutions() + 1):
            circ = gcc.ThisSolution(i)  # gp_Circ2d

            # Validate tangency lies on trimmed span if the target is an Edge
            p1 = gp_Pnt2d()
            _u_on_circ, u_on_arg = gcc.Tangency1(i, p1)
            if is_edge1 and not _param_in_trim(u_on_arg, e1_first, e1_last, h_e1):
                continue

            # Emit full circle (2π trim)
            h2d = Geom2d_Circle(circ)
            per = h2d.Period()
            solutions_topo.append(_edge_from_circle(h2d, 0.0, per))

    return ShapeList([edge_factory(e) for e in solutions_topo])


def _make_tan_on_rad_arcs(
    tangency: tuple[Edge, Tangency] | Edge | Vector,
    *,
    center_on: Edge,
    radius: float,
    edge_factory: Callable[[TopoDS_Edge], Edge],
) -> ShapeList[Edge]:
    """
    Create planar circle(s) on XY that:
      - are tangent/contacting a single object, and
      - have a fixed radius, and
      - have their CENTER constrained to lie on a given locus curve.

    Notes
    -----
    - The center locus must be a 2D curve (line/circle/any Geom2d curve) — i.e. an Edge
      after projection to XY.
    - With only one tangency, the natural geometric result is a full circle; arc cropping
      would require an additional endpoint constraint. This routine therefore returns
      closed circular edges (2π trims) for each valid solution.
    """

    # --- unpack optional qualifier on the tangency arg (edges only) ---
    if isinstance(tangency, tuple):
        object_one, obj1_qual = tangency
    else:
        object_one, obj1_qual = tangency, Tangency.UNQUALIFIED

    # --- build tangency input (point/edge) ---
    q_o1, h_e1, e1_first, e1_last, is_edge1 = _as_gcc_arg(object_one, obj1_qual)

    # --- center locus ('center_on') must be a curve; ignore any qualifier there ---
    on_obj = center_on[0] if isinstance(center_on, tuple) else center_on
    if not isinstance(on_obj.wrapped, TopoDS_Edge):
        raise TypeError("center_on must be an Edge (line/circle/curve) for TanOnRad.")

    # Project the center locus Edge to 2D (XY)
    _, h_on2d, on_first, on_last, adapt_on = _edge_to_qualified_2d(
        on_obj.wrapped, Tangency.UNQUALIFIED
    )
    gcc = Geom2dGcc_Circ2dTanOnRad(q_o1, adapt_on, radius, TOLERANCE)

    if not gcc.IsDone() or gcc.NbSolutions() == 0:
        raise RuntimeError("Unable to find circle(s) for TanOnRad constraints")

    def _ok1(u: float) -> bool:
        return True if not is_edge1 else _param_in_trim(u, e1_first, e1_last, h_e1)

    # --- enumerate solutions; emit full circles (2π trims) ---
    out_topos: list[TopoDS_Edge] = []
    for i in range(1, gcc.NbSolutions() + 1):
        circ: gp_Circ2d = gcc.ThisSolution(i)

        # Validate tangency lies on trimmed span when the target is an Edge
        p = gp_Pnt2d()
        _u_on_circ, u_on_arg = gcc.Tangency1(i, p)
        if not _ok1(u_on_arg):
            continue

        # Center must lie on the trimmed center_on curve segment
        center2d = circ.Location()  # gp_Pnt2d

        # Project center onto the (trimmed) 2D locus
        proj = Geom2dAPI_ProjectPointOnCurve(center2d, h_on2d)
        u_on = tcast(float, proj.Parameter(1))

        # Respect the trimmed interval (handles periodic curves too)
        if not _param_in_trim(u_on, on_first, on_last, h_on2d):
            continue

        h2d = Geom2d_Circle(circ)
        per = h2d.Period()
        out_topos.append(_edge_from_circle(h2d, 0.0, per))

    return ShapeList([edge_factory(e) for e in out_topos])


# -----------------------------------------------------------------------------
# Line solvers (siblings of constrained arcs)
# -----------------------------------------------------------------------------


def _make_2tan_lines(
    tangency1: tuple[Edge, Tangency] | Edge,
    tangency2: tuple[Edge, Tangency] | Edge | Vector,
    *,
    edge_factory: Callable[[TopoDS_Edge], Edge],
) -> ShapeList[Edge]:
    """
    Construct line(s) tangent to two curves.

    Parameters
    ----------
    curve1, curve2 : Edge
        Target curves.

    Returns
    -------
    ShapeList[Edge]
        Finite tangent line(s).
    """
    if isinstance(tangency1, tuple):
        object_one, obj1_qual = tangency1
    else:
        object_one, obj1_qual = tangency1, Tangency.UNQUALIFIED
    q1, c1, _, _, _ = _as_gcc_arg(object_one, obj1_qual)

    if isinstance(tangency2, Vector):
        pnt_2d = gp_Pnt2d(tangency2.X, tangency2.Y)
        gcc = Geom2dGcc_Lin2d2Tan(q1, pnt_2d, TOLERANCE)
    else:
        if isinstance(tangency2, tuple):
            object_two, obj2_qual = tangency2
        else:
            object_two, obj2_qual = tangency2, Tangency.UNQUALIFIED
        q2, c2, _, _, _ = _as_gcc_arg(object_two, obj2_qual)
        gcc = Geom2dGcc_Lin2d2Tan(q1, q2, TOLERANCE)

    if not gcc.IsDone() or gcc.NbSolutions() == 0:
        raise RuntimeError("Unable to find common tangent line(s)")

    out_edges: list[TopoDS_Edge] = []
    for i in range(1, gcc.NbSolutions() + 1):
        lin2d = Geom2d_Line(gcc.ThisSolution(i))

        # Two tangency points - Note Tangency1/Tangency2 can use different
        # indices for the same line
        inter_cc = Geom2dAPI_InterCurveCurve(lin2d, c1)
        pt1 = inter_cc.Point(1)  # There will always be one tangent intersection

        if isinstance(tangency2, Vector):
            pt2 = gp_Pnt2d(tangency2.X, tangency2.Y)
        else:
            inter_cc = Geom2dAPI_InterCurveCurve(lin2d, c2)
            pt2 = inter_cc.Point(1)

        # Skip degenerate lines
        separation = pt1.Distance(pt2)
        if isnan(separation) or separation < TOLERANCE:
            continue

        out_edges.append(_edge_from_line(pt1, pt2))
    return ShapeList([edge_factory(e) for e in out_edges])


def _make_tan_oriented_lines(
    tangency: tuple[Edge, Tangency] | Edge,
    reference: Axis,
    angle: float,  # radians; absolute angle offset from `reference`
    *,
    edge_factory: Callable[[TopoDS_Edge], Edge],
) -> ShapeList[Edge]:
    """
    Construct line(s) tangent to a curve and forming a given angle with a
    reference line (Axis) per Geom2dGcc_Lin2dTanObl. Trimmed between:
    - the tangency point on the curve, and
    - the intersection with the reference line.
    """
    if isinstance(tangency, tuple):
        object_one, obj1_qual = tangency
    else:
        object_one, obj1_qual = tangency, Tangency.UNQUALIFIED

    if abs(abs(reference.direction.Z) - 1) < TOLERANCE:
        raise ValueError("reference Axis can't be perpendicular to Plane.XY")

    q_curve, _, _, _, _ = _as_gcc_arg(object_one, obj1_qual)

    # reference axis direction (2D angle in radians)
    ref_dir = reference.direction
    theta_ref = atan2(ref_dir.Y, ref_dir.X)

    # total absolute angle
    theta_abs = theta_ref + angle

    dir2d = gp_Dir2d(cos(theta_abs), sin(theta_abs))

    # Reference axis as gp_Lin2d
    ref_lin = _gp_lin2d_from_axis(reference)

    # Note that is seems impossible for Geom2dGcc_Lin2dTanObl to provide no solutions
    gcc = Geom2dGcc_Lin2dTanObl(q_curve, ref_lin, TOLERANCE, angle)

    out: list[TopoDS_Edge] = []
    for i in range(1, gcc.NbSolutions() + 1):
        # Tangency on the curve
        p_tan = gp_Pnt2d()
        gcc.Tangency1(i, p_tan)

        tan_line = gp_Lin2d(p_tan, dir2d)

        # Intersect with reference axis
        # Note: Intersection2 doesn't seem reliable
        inter = IntAna2d_AnaIntersection(tan_line, ref_lin)
        if not inter.IsDone() or inter.NbPoints() == 0:
            continue
        p_isect = inter.Point(1).Value()

        # Skip degenerate lines
        separation = p_tan.Distance(p_isect)
        if isnan(separation) or separation < TOLERANCE:
            continue

        out.append(_edge_from_line(p_tan, p_isect))

    return ShapeList([edge_factory(e) for e in out])
