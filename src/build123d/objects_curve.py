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

import copy as copy_module
import warnings
import numpy as np
import sympy  # type: ignore
from collections.abc import Callable, Iterable, Sequence
from itertools import product
from math import atan2, copysign, cos, degrees, radians, sin, sqrt
from scipy.optimize import minimize
from typing import overload, Literal

from build123d.build_common import WorkplaneList, flatten_sequence, validate_inputs
from build123d.build_enums import (
    AngularDirection,
    ContinuityLevel,
    GeomType,
    LengthMode,
    Keep,
    Mode,
    Sagitta,
    Tangency,
    Side,
)
from build123d.build_line import BuildLine
from build123d.geometry import Axis, Location, Plane, Vector, VectorLike, TOLERANCE
from build123d.topology import Curve, Edge, Face, Vertex, Wire
from build123d.topology.shape_core import Shape, ShapeList


def _add_curve_to_context(curve: Edge | Wire | Curve, mode: Mode):
    """Helper function to add a curve to the context.

    Args:
        curve (Edge | Wire | Curve): curve to add to the context (either a Wire or an Edge)
        mode (Mode): combination mode
    """
    context: BuildLine | None = BuildLine._get_context(log=False)

    if context is not None and isinstance(context, BuildLine):
        if isinstance(curve, Edge):
            context._add_to_context(curve, mode=mode)
        elif isinstance(curve, (Curve, Wire)):
            context._add_to_context(*curve.edges(), mode=mode)


class BaseCurveObject(Curve):
    """BaseCurveObject specialized for Curve.

    Args:
        curve (Wire): wire to create
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(self, curve: Curve, mode: Mode = Mode.ADD):
        # Use the helper function to handle adding the curve to the context
        _add_curve_to_context(curve, mode)
        if curve.wrapped is not None:
            super().__init__(curve.wrapped)


class BaseLineObject(Wire):
    """BaseLineObject specialized for Wire.

    Args:
        curve (Wire): wire to create
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(self, curve: Wire, mode: Mode = Mode.ADD):
        # Use the helper function to handle adding the curve to the context
        _add_curve_to_context(curve, mode)
        if curve.wrapped is not None:
            super().__init__(curve.wrapped)


class BaseEdgeObject(Edge):
    """BaseEdgeObject specialized for Edge.

    Args:
        curve (Edge): edge to create
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(self, curve: Edge, mode: Mode = Mode.ADD):
        # Use the helper function to handle adding the curve to the context
        _add_curve_to_context(curve, mode)
        super().__init__(curve.wrapped)


class Airfoil(BaseLineObject):
    """
    Create an airfoil described by a 4-digit (or fractional) NACA airfoil
    (e.g. '2412' or '2213.323').

    The NACA four-digit wing sections define the airfoil_code by:
    - First digit describing maximum camber as percentage of the chord.
    - Second digit describing the distance of maximum camber from the airfoil leading edge
    in tenths of the chord.
    - Last two digits describing maximum thickness of the airfoil as percent of the chord.

    Args:
        airfoil_code : str
            The NACA 4-digit (or fractional) airfoil code (e.g. '2213.323').
        n_points : int
            Number of points per upper/lower surface.
        finite_te : bool
            If True, enforces a finite trailing edge (default False).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    """

    _applies_to = [BuildLine._tag]

    @staticmethod
    def parse_naca4(value: str | float) -> tuple[float, float, float]:
        """
        Parse NACA 4-digit (or fractional) airfoil code into parameters.
        """
        s = str(value).replace("NACA", "").strip()
        if "." in s:
            int_part, frac_part = s.split(".", 1)
            m = int(int_part[0]) / 100
            p = int(int_part[1]) / 10
            t = float(f"{int(int_part[2:]):02}.{frac_part}") / 100
        else:
            m = int(s[0]) / 100
            p = int(s[1]) / 10
            t = int(s[2:]) / 100
        return m, p, t

    def __init__(
        self,
        airfoil_code: str,
        n_points: int = 50,
        finite_te: bool = False,
        mode: Mode = Mode.ADD,
    ):

        # Airfoil thickness distribution equation:
        #
        # yₜ=5t[0.2969√x-0.1260x-0.3516x²+0.2843x³-0.1015x⁴]
        #
        # where:
        # - x is the distance along the chord (0 at the leading edge, 1 at the trailing edge),
        # - t is the maximum thickness as a fraction of the chord (e.g. 0.12 for a NACA 2412),
        # - yₜ gives the half-thickness at each chordwise location.

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        m, p, t = Airfoil.parse_naca4(airfoil_code)

        # Cosine-spaced x values for better nose resolution
        beta = np.linspace(0.0, np.pi, n_points)
        x = (1 - np.cos(beta)) / 2

        # Thickness distribution
        a0, a1, a2, a3 = 0.2969, -0.1260, -0.3516, 0.2843
        a4 = -0.1015 if finite_te else -0.1036
        yt = 5 * t * (a0 * np.sqrt(x) + a1 * x + a2 * x**2 + a3 * x**3 + a4 * x**4)

        # Camber line and slope
        if m == 0 or p == 0 or p == 1:
            yc = np.zeros_like(x)
            dyc_dx = np.zeros_like(x)
        else:
            yc = np.empty_like(x)
            dyc_dx = np.empty_like(x)
            mask = x < p
            yc[mask] = m / p**2 * (2 * p * x[mask] - x[mask] ** 2)
            yc[~mask] = (
                m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x[~mask] - x[~mask] ** 2)
            )
            dyc_dx[mask] = 2 * m / p**2 * (p - x[mask])
            dyc_dx[~mask] = 2 * m / (1 - p) ** 2 * (p - x[~mask])

        theta = np.arctan(dyc_dx)
        self._camber_points = [Vector(xi, yi) for xi, yi in zip(x, yc)]

        # Upper and lower surfaces
        xu = x - yt * np.sin(theta)
        yu = yc + yt * np.cos(theta)
        xl = x + yt * np.sin(theta)
        yl = yc - yt * np.cos(theta)

        upper_pnts = [Vector(x, y) for x, y in zip(xu, yu)]
        lower_pnts = [Vector(x, y) for x, y in zip(xl, yl)]
        unique_points: list[
            Vector | tuple[float, float] | tuple[float, float, float]
        ] = list(dict.fromkeys(upper_pnts[::-1] + lower_pnts))
        surface = Edge.make_spline(unique_points, periodic=not finite_te)  # type: ignore[arg-type]
        if finite_te:
            trailing_edge = Edge.make_line(surface @ 0, surface @ 1)
            airfoil_profile = Wire([surface, trailing_edge])
        else:
            airfoil_profile = Wire([surface])

        super().__init__(airfoil_profile, mode=mode)

        # Store metadata
        self.code: str = airfoil_code  #: NACA code string (e.g. "2412")
        self.max_camber: float = m  #: Maximum camber as fraction of chord
        self.camber_pos: float = p  #: Chordwise position of max camber (0–1)
        self.thickness: float = t  #: Maximum thickness as fraction of chord
        self.finite_te: bool = finite_te  #: If True, trailing edge is finite

    @property
    def camber_line(self) -> Edge:
        """Camber line of the airfoil as an Edge."""
        return Edge.make_spline(self._camber_points)  # type: ignore[arg-type]


class Bezier(BaseEdgeObject):
    """Line Object: Bezier Curve

    Create a non-rational bezier curve defined by a sequence of points and include optional
    weights to create a rational bezier curve. The number of weights must match the number
    of control points.

    Args:
        cntl_pnts (sequence[VectorLike]): points defining the curve
        weights (list[float], optional): control point weights. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *cntl_pnts: VectorLike,
        weights: list[float] | None = None,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        cntl_pnt_list = flatten_sequence(*cntl_pnts)
        polls = WorkplaneList.localize(*cntl_pnt_list)
        curve = Edge.make_bezier(*polls, weights=weights)

        super().__init__(curve, mode=mode)


class BlendCurve(BaseEdgeObject):
    """Line Object: BlendCurve

    Create a smooth Bézier-based transition curve between two existing edges.

    The blend is constructed as a cubic (C1) or quintic (C2) Bézier curve
    whose control points are determined from the position, first derivative,
    and (for C2) second derivative of the input curves at the chosen endpoints.
    Optional scalar multipliers can be applied to the endpoint tangents to
    control the "tension" of the blend.

    Args:
        curve0 (Edge): First curve to blend from.
        curve1 (Edge): Second curve to blend to.
        continuity (ContinuityLevel, optional):
            Desired geometric continuity at the join:
            - ContinuityLevel.C0: position match only (straight line)
            - ContinuityLevel.C1: match position and tangent direction (cubic Bézier)
            - ContinuityLevel.C2: match position, tangent, and curvature (quintic Bézier)
            Defaults to ContinuityLevel.C2.
        end_points (tuple[VectorLike, VectorLike] | None, optional):
            Pair of points specifying the connection points on `curve0` and `curve1`.
            Each must coincide (within TOLERANCE) with the start or end of the
            respective curve. If None, the closest pair of endpoints is chosen.
            Defaults to None.
        tangent_scalars (tuple[float, float] | None, optional):
            Scalar multipliers applied to the first derivatives at the start
            of `curve0` and the end of `curve1` before computing control points.
            Useful for adjusting the pull/tension of the blend without altering
            the base curves. Defaults to (1.0, 1.0).
        mode (Mode, optional): Boolean operation mode when used in a
            BuildLine context. Defaults to Mode.ADD.

    Raises:
        ValueError: `tangent_scalars` must be a pair of float values.
        ValueError: If specified `end_points` are not coincident with the start
            or end of their respective curves.

    Example:
        >>> blend = BlendCurve(curve_a, curve_b, ContinuityLevel.C1, tangent_scalars=(1.2, 0.8))
        >>> show(blend)
    """

    def __init__(
        self,
        curve0: Edge,
        curve1: Edge,
        continuity: ContinuityLevel = ContinuityLevel.C2,
        end_points: tuple[VectorLike, VectorLike] | None = None,
        tangent_scalars: tuple[float, float] | None = None,
        mode: Mode = Mode.ADD,
    ):
        #
        # Process the inputs

        tan_scalars = (1.0, 1.0) if tangent_scalars is None else tangent_scalars
        if len(tan_scalars) != 2:
            raise ValueError("tangent_scalars must be a (start, end) pair")

        # Find the vertices that will be connected using closest if None
        end_pnts = (
            min(
                product(curve0.vertices(), curve1.vertices()),
                key=lambda pair: pair[0].distance_to(pair[1]),
            )
            if end_points is None
            else end_points
        )

        # Find the Edge parameter that matches the end points
        curves: tuple[Edge, Edge] = (curve0, curve1)
        end_params = [0, 0]
        for i, end_pnt in enumerate(end_pnts):
            curve_start_pnt = curves[i].position_at(0)
            curve_end_pnt = curves[i].position_at(1)
            given_end_pnt = Vector(end_pnt)
            if (given_end_pnt - curve_start_pnt).length < TOLERANCE:
                end_params[i] = 0
            elif (given_end_pnt - curve_end_pnt).length < TOLERANCE:
                end_params[i] = 1
            else:
                raise ValueError(
                    "end_points must be at either the start or end of a curve"
                )

        #
        # Bézier endpoint derivative constraints (degree n=5 case)
        #
        # For a degree-n Bézier curve:
        #   B(t)   = Σ_{i=0}^n binom(n,i) (1-t)^(n-i) t^i  P_i
        #   B'(t)  = n(P_1 - P_0) at t=0
        #            n(P_n - P_{n-1}) at t=1
        #   B''(t) = n(n-1)(P_2 - 2P_1 + P_0) at t=0
        #            n(n-1)(P_{n-2} - 2P_{n-1} + P_n) at t=1
        #
        # Matching a desired start derivative D0 and curvature vector K0:
        #   P1 = P0 + (1/n) * D0
        #   P2 = P0 + (2/n) * D0 + (1/(n*(n-1))) * K0
        #
        # Matching a desired end derivative D1 and curvature vector K1:
        #   P_{n-1} = P_n - (1/n) * D1
        #   P_{n-2} = P_n - (2/n) * D1 + (1/(n*(n-1))) * K1
        #
        # For n=5 specifically:
        #   P1 = P0 + D0 / 5
        #   P2 = P0 + (2*D0)/5 + K0/20
        #   P4 = P5 - D1 / 5
        #   P3 = P5 - (2*D1)/5 + K1/20
        #
        # D0, D1 are first derivatives at endpoints (can be scaled for tension).
        # K0, K1 are second derivatives at endpoints (for C² continuity).
        # Works in any dimension; P_i are vectors in ℝ² or ℝ³.

        #
        # | Math symbol | Meaning in code            | Python name  |
        # | ----------- | -------------------------- | ------------ |
        # | P_0         | start position             | start_pos    |
        # | P_1         | 1st control pt after start | ctrl_pnt1    |
        # | P_2         | 2nd control pt after start | ctrl_pnt2    |
        # | P_{n-2}     | 2nd control pt before end  | ctrl_pnt3    |
        # | P_{n-1}     | 1st control pt before end  | ctrl_pnt4    |
        # | P_n         | end position               | end_pos      |
        # | D_0         | derivative at start        | start_deriv  |
        # | D_1         | derivative at end          | end_deriv    |
        # | K_0         | curvature vec at start     | start_curv   |
        # | K_1         | curvature vec at end       | end_curv     |

        start_pos = curve0.position_at(end_params[0])
        end_pos = curve1.position_at(end_params[1])

        # Note: derivative_at(..,1) is being used instead of tangent_at as
        # derivate_at isn't normalized which allows for a natural "speed" to be used
        # if no scalar is provided.
        start_deriv = curve0.derivative_at(end_params[0], 1) * tan_scalars[0]
        end_deriv = curve1.derivative_at(end_params[1], 1) * tan_scalars[1]

        if continuity == ContinuityLevel.C0:
            joining_curve = Line(start_pos, end_pos)
        elif continuity == ContinuityLevel.C1:
            cntl_pnt1 = start_pos + start_deriv / 3
            cntl_pnt4 = end_pos - end_deriv / 3
            cntl_pnts = [start_pos, cntl_pnt1, cntl_pnt4, end_pos]  # degree-3 Bézier
            joining_curve = Bezier(*cntl_pnts)
        else:  # C2
            start_curv = curve0.derivative_at(end_params[0], 2)
            end_curv = curve1.derivative_at(end_params[1], 2)
            cntl_pnt1 = start_pos + start_deriv / 5
            cntl_pnt2 = start_pos + (2 * start_deriv) / 5 + start_curv / 20
            cntl_pnt4 = end_pos - end_deriv / 5
            cntl_pnt3 = end_pos - (2 * end_deriv) / 5 + end_curv / 20
            cntl_pnts = [
                start_pos,
                cntl_pnt1,
                cntl_pnt2,
                cntl_pnt3,
                cntl_pnt4,
                end_pos,
            ]  # degree-5 Bézier
            joining_curve = Bezier(*cntl_pnts)

        super().__init__(joining_curve, mode=mode)


class CenterArc(BaseEdgeObject):
    """Line Object: Center Arc

    Create a circular arc defined by a center point and radius.

    Args:
        center (VectorLike): center point of arc
        radius (float): arc radius
        start_angle (float): arc starting angle from x-axis
        arc_size (float | Shape | Axis | Location | Plane | VectorLike): angular size
            of arc or an arc limit.

            When a limit object is provided instead of a numeric angular size, CenterArc
            constructs the valid arc(s) from the given start point, trims them at their
            first intersection with the limit, and returns the one requiring the shortest
            travel from the start. Therefore, one can only generate arcs < 180° using a limit.
            If neither valid arc intersects the limit, a ValueError is raised.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        center: VectorLike,
        radius: float,
        start_angle: float,
        arc_size: float | Shape | Axis | Location | Plane | VectorLike,
        mode: Mode = Mode.ADD,
    ) -> None:
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        center_point = WorkplaneList.localize(center)
        if context is None:
            circle_workplane = Plane.XY
        else:
            circle_workplane = copy_module.copy(
                WorkplaneList._get_context().workplanes[0]
            )
        circle_workplane.origin = center_point

        arc_factor = Vector(arc_size) if isinstance(arc_size, Sequence) else arc_size

        if isinstance(arc_factor, (int, float)):
            arc_direction = (
                AngularDirection.COUNTER_CLOCKWISE
                if arc_factor > 0
                else AngularDirection.CLOCKWISE
            )
            normalized_arc_size = (arc_factor + 360.0) % 360.0
            end_angle = start_angle + normalized_arc_size
            start_angle = end_angle if normalized_arc_size == 360.0 else start_angle

            arc = Edge.make_circle(
                radius,
                circle_workplane,
                start_angle=start_angle,
                end_angle=end_angle,
                angular_direction=arc_direction,
            )
        else:
            start_radius_vector = (
                circle_workplane.x_dir.rotate(
                    Axis((0, 0, 0), circle_workplane.z_dir), start_angle
                )
                * radius
            )

            circle_plane = copy_module.copy(circle_workplane)
            circle_plane.origin = center_point
            circle_plane.x_dir = start_radius_vector

            arc = Edge.make_circle(radius, circle_plane)
            arc2 = arc.reversed(reconstruct=True)

            trimmed_arc = arc.trim_to_other(arc_factor)
            trimmed_arc2 = arc2.trim_to_other(arc_factor)

            if trimmed_arc is None and trimmed_arc2 is None:
                raise ValueError(f"CenterArc doesn't intersect arc limit {arc_size}")

            arc = ShapeList(
                [a for a in [trimmed_arc, trimmed_arc2] if a is not None]
            ).sort_by(Edge.length)[0]

        super().__init__(arc, mode=mode)


class ConstrainedArcs(BaseCurveObject):
    """Line Object: Arc(s) constrained by other geometric objects.

    The result is always a Curve containing one or more Edges. If you need
    to access Edge-specific properties or methods (such as ``arc_center``),
    extract the edge or edges first::

        result = ConstrainedArcs(...)
        arc = result.edge()           # extract the Edge
        center = arc.arc_center       # now Edge methods are available

    Note that in Builder mode the ``selector`` parameter must be provided or
    all results will be combined into the BuildLine context. In Algebra mode
    the selector can be applied as a parameter or in the normal way to the
    ConstrainedArcs object. The content of the selector is the same in both cases.

    Examples:
        An arc built from three edge constraints.

        Algebra::

            l4 = PolarLine((0, 0), 4, 60)
            l5 = PolarLine((0, 0), 4, 40)
            a3 = CenterArc((0, 0), 4, 0, 90)
            ex_a3 = (
                ConstrainedArcs(l4, l5, a3, sagitta=Sagitta.BOTH).edges().sort_by(Edge.length)[0]
            )

        Builder::

            with BuildLine() as arc_ex3:
                l4 = PolarLine((0, 0), 4, 60)
                l5 = PolarLine((0, 0), 4, 40)
                a3 = CenterArc((0, 0), 4, 0, 90)
                ex_a3 = ConstrainedArcs(
                    l4,
                    l5,
                    a3,
                    sagitta=Sagitta.BOTH,
                    selector=lambda arcs: arcs.sort_by(Edge.length)[0],
                )

    """

    _applies_to = [BuildLine._tag]

    @overload
    def __init__(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_two: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        radius: float,
        sagitta: Sagitta = Sagitta.SHORT,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda arcs: arcs,
        mode: Mode = Mode.ADD,
    ):
        """
        Create all planar circular arcs of a given radius that are tangent/contacting
        the two provided objects on the XY plane.

        Args:
            tangency_one, tangency_two
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entities to be contacted/touched by the circle(s)
            radius (float): arc radius
            sagitta (LengthConstraint, optional): returned arc selector
                (i.e. either the short, long or both arcs). Defaults to
                LengthConstraint.SHORT.
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda arcs: arcs.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Example:
            Accept all results (default behaviour)::

                a1 = CenterArc((-5, 0), 4, 0, 360)
                a2 = CenterArc((5, 0), 3, 0, 360)
                arcs = ConstrainedArcs(a1, a2, radius=10, selector=lambda arcs: arcs)
        """

    @overload
    def __init__(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_two: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        center_on: Axis | Edge,
        sagitta: Sagitta = Sagitta.SHORT,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda arcs: arcs,
        mode: Mode = Mode.ADD,
    ):
        """
        Create all planar circular arcs whose circle is tangent to two objects and whose
        CENTER lies on a given locus (line/circle/curve) on the XY plane.

        Args:
            tangency_one, tangency_two
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entities to be contacted/touched by the circle(s)
            center_on (Axis | Edge): center must lie on this object
            sagitta (LengthConstraint, optional): returned arc selector
                (i.e. either the short, long or both arcs). Defaults to
                LengthConstraint.SHORT.
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda arcs: arcs.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Example:
            Pick just the first result::

                l2 = PolarLine((0, 0), 4, -20, length_mode=LengthMode.HORIZONTAL)
                l3 = Line((4, -2), (4, 2))
                arcs = ConstrainedArcs(
                    l2, l3, center_on=Axis((3, 0), (0, 1)), selector=lambda arcs: arcs[0]
                )
        """

    @overload
    def __init__(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_two: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        tangency_three: (
            tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike
        ),
        *,
        sagitta: Sagitta = Sagitta.SHORT,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda arcs: arcs,
        mode: Mode = Mode.ADD,
    ):
        """
        Create planar circular arc(s) on XY tangent to three provided objects.

        Args:
            tangency_one, tangency_two, tangency_three
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entities to be contacted/touched by the circle(s)
            sagitta (LengthConstraint, optional): returned arc selector
                (i.e. either the short, long or both arcs). Defaults to
                LengthConstraint.SHORT.
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda arcs: arcs.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Example:
            Pick the shortest one::

                l4 = PolarLine((0, 0), 4, 60)
                l5 = PolarLine((0, 0), 4, 40)
                a3 = CenterArc((0, 0), 4, 0, 90)
                arcs = ConstrainedArcs(
                    l4, l5, a3, sagitta=Sagitta.BOTH,
                    selector=lambda arcs: arcs.sort_by(Edge.length)[0]
                )

        """

    @overload
    def __init__(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        center: VectorLike,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda arcs: arcs,
        mode: Mode = Mode.ADD,
    ):
        """
        Create planar circle(s) on XY whose center is fixed and that are tangent/contacting
        a single object.

        Args:
            tangency_one
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entity to be contacted/touched by the circle(s)
            center (VectorLike): center position
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda arcs: arcs.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.


        Example:
            Pick the only result::

                arcs = ConstrainedArcs(Axis.Y, center=(-2, 1), selector=lambda arcs: arcs[0])

        """

    @overload
    def __init__(
        cls,
        tangency_one: tuple[Axis | Edge, Tangency] | Axis | Edge | Vertex | VectorLike,
        *,
        radius: float,
        center_on: Edge,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda arcs: arcs,
        mode: Mode = Mode.ADD,
    ):
        """

        Create planar circle(s) on XY that:
        - are tangent/contacting a single object, and
        - have a fixed radius, and
        - have their CENTER constrained to lie on a given locus curve.

        Args:
            tangency_one
                (tuple[Axis | Edge, PositionConstraint] | Axis | Edge | Vertex | VectorLike):
                Geometric entity to be contacted/touched by the circle(s)
            radius (float): arc radius
            center_on (Axis | Edge): center must lie on this object
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda arcs: arcs.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Example:
            There is only one result so a selector isn't helpful::

                l6 = PolarLine((0, 0), 5, -20)
                l7 = Line((3, -2), (3, 2))
                arcs = ConstrainedArcs(l6, radius=1, center_on=l7)

        """

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        selector = kwargs.pop("selector", lambda arcs: arcs)
        mode = kwargs.pop("mode", Mode.ADD)

        arcs = Edge.make_constrained_arcs(*args, **kwargs)

        # Apply the user's selector (or the default)
        selected_arcs = selector(arcs)
        if selected_arcs is None or not selected_arcs:
            raise ValueError("selector must return an Edge or list of Edges, not None")

        selected_arcs = (
            [selected_arcs] if isinstance(selected_arcs, Edge) else selected_arcs
        )
        curve = Curve(selected_arcs)
        super().__init__(curve, mode=mode)


class ConstrainedLines(BaseCurveObject):
    """Line Object: Lines(s) constrained by other geometric objects.

    The result is always a Curve containing one or more Edges. If you need
    to access Edge-specific properties or methods (such as ``length``),
    extract the edge or edges first::

        result = ConstrainedLines(...)
        lines = result.edges()      # extract the Edges
        length = lines[1].length    # now Edge methods are available

    Note that in Builder mode the ``selector`` parameter must be provided or
    all results will be combined into the BuildLine context. In Algebra mode
    the selector can be applied as a parameter or in the normal way to the
    ConstrainedArcs object. The content of the selector is the same in both cases.
    """

    _applies_to = [BuildLine._tag]

    @overload
    def __init__(
        self,
        tangency_one: tuple[Edge, Tangency] | Axis | Edge,
        tangency_two: tuple[Edge, Tangency] | Axis | Edge,
        *,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda lines: lines,
        mode: Mode = Mode.ADD,
    ):
        """
        Create all planar line(s) on the XY plane tangent to two provided curves.

        Args:
            tangency_one, tangency_two
                (tuple[Edge, Tangency] | Axis | Edge):
                Geometric entities to be contacted/touched by the line(s).
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda lines: lines.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Example:
            Accept all results (default behaviour)::

                a1 = CenterArc((-5, 0), 4, 0, 360)
                a2 = CenterArc((5, 0), 3, 0, 360)
                lines = ConstrainedLines(a1, a2, selector=lambda lines: lines)
        """

    @overload
    def __init__(
        self,
        tangency_one: tuple[Edge, Tangency] | Edge,
        tangency_two: VectorLike,
        *,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda lines: lines,
        mode: Mode = Mode.ADD,
    ):
        """
        Create all planar line(s) on the XY plane tangent to one curve and passing
        through a fixed point.

        Args:
            tangency_one
                (tuple[Edge, Tangency] | Edge):
                Geometric entity to be contacted/touched by the line(s).
            tangency_two (VectorLike):
                Fixed point through which the line(s) must pass.
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda lines: lines.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Example:
            Pick just the first result::

                a1 = CenterArc((-5, 0), 4, 0, 360)
                lines = ConstrainedLines(a1, (0, 6), selector=lambda lines: lines[0])
        """

    @overload
    def __init__(
        self,
        tangency_one: tuple[Edge, Tangency] | Edge,
        tangency_two: Axis,
        *,
        angle: float | None = None,
        direction: VectorLike | None = None,
        selector: Callable[
            [ShapeList[Edge]], Edge | ShapeList[Edge]
        ] = lambda lines: lines,
        mode: Mode = Mode.ADD,
    ):
        """
        Create all planar line(s) on the XY plane tangent to one curve with a
        fixed orientation, defined either by an angle measured from a reference
        axis or by a direction vector.

        Args:
            tangency_one (Edge): edge that line will be tangent to
            tangency_two (Axis): reference axis from which the angle is measured
            angle : float, optional
                Line orientation in degrees (measured CCW from the X-axis).
            direction : VectorLike, optional
                Direction vector for the line (only X and Y components are used).
            Note: one of angle or direction must be provided
            selector (Callable, optional): typically a lambda which chooses one or more of the
                results. Defaults to lambda lines: lines.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Example:
            Pick the arc whose midpoint is closest to a given point::

                a1 = CenterArc((-5, 0), 4, 0, 360)
                lines = ConstrainedLines(
                    a1,
                    Axis.Y,
                    angle=30,
                    selector=lambda lines: lines.sort_by_distance((0, 0))[0],
                )
        """

    def __init__(self, *args, **kwargs) -> None:
        """
        Create planar line(s) on XY subject to tangency/contact constraints.

        Supported cases
        ---------------
        1. Tangent to two curves
        2. Tangent to one curve and passing through a given point
        """
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        selector = kwargs.pop("selector", lambda lines: lines)
        mode = kwargs.pop("mode", Mode.ADD)

        lines = Edge.make_constrained_lines(*args, **kwargs)

        # Apply the user's selector (or the default)
        selected_lines = selector(lines)
        if selected_lines is None or not selected_lines:
            raise ValueError("selector must return an Edge or list of Edges, not None")

        selected_lines = (
            [selected_lines] if isinstance(selected_lines, Edge) else selected_lines
        )
        curve = Curve(selected_lines)
        super().__init__(curve, mode=mode)


class DoubleTangentArc(BaseEdgeObject):
    """Line Object: Double Tangent Arc

    Create a circular arc defined by a point/tangent pair and another line find a tangent to.

    The arc specified with TOP or BOTTOM depends on the geometry and isn't predictable.

    Contains a solver.

    Args:
        pnt (VectorLike): start point
        tangent (VectorLike): tangent at start point
        other (Curve | Edge | Wire): line object to tangent
        keep (Keep, optional): specify which arc if more than one, TOP or BOTTOM.
            Defaults to Keep.TOP
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        RunTimeError: no double tangent arcs found
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        pnt: VectorLike,
        tangent: VectorLike,
        other: Curve | Edge | Wire,
        keep: Keep = Keep.TOP,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        if keep not in [Keep.TOP, Keep.BOTTOM]:
            raise ValueError(f"Only the TOP or BOTTOM options are supported not {keep}")

        arc_pt = WorkplaneList.localize(pnt)
        arc_tangent = WorkplaneList.localize(tangent).normalized()
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
        max_size = 10 * other.bounding_box().add(arc_pt).diagonal

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
            if other_axis.is_parallel(circle_axis, 0.05):
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

        double_edge = double.edge()
        assert isinstance(double_edge, Edge)
        super().__init__(double_edge, mode=mode)


class EllipticalCenterArc(BaseEdgeObject):
    """Line Object: Elliptical Center Arc

    Create an elliptical arc defined by a center point, x- and y- radii.

    Args:
        center (VectorLike): ellipse center
        x_radius (float): x radius of the ellipse (along the x-axis of plane)
        y_radius (float): y radius of the ellipse (along the y-axis of plane)
        start_angle (float, optional): arc start angle from x-axis.
            Defaults to 0.0
        end_angle (float | None): arc end angle from x-axis.
            Defaults to None
        arc_size (float | Shape | Axis | Location | Plane | VectorLike): angular size
            of arc (negative to change direction) or an arc limit.

            When a limit object is provided instead of a numeric angular size,
            EllipticalCenterArc constructs the valid arc(s) from the given start
            point, trims them at their first intersection with the limit, and
            returns the one requiring the shortest travel from the start.
            Therefore, one can only generate arcs < 180° using a limit. If
            neither valid arc intersects the limit, a ValueError is raised.
        rotation (float, optional): angle to rotate arc. Defaults to 0.0
        angular_direction (AngularDirection | None): arc direction.
            Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        center: VectorLike,
        x_radius: float,
        y_radius: float,
        start_angle: float = 0.0,
        end_angle: float | None = None,
        *,
        arc_size: float | Shape | Axis | Location | Plane | VectorLike = 90.0,
        rotation: float = 0.0,
        angular_direction: AngularDirection | None = None,
        mode: Mode = Mode.ADD,
    ) -> None:
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        deprecated_parameter = False
        if end_angle is not None:
            deprecated_parameter = True
            end_a = end_angle
            warnings.warn(
                "The 'end_angle' parameter is deprecated and will be removed in a future version."
                " Use 'arc_size' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if angular_direction is not None:
            deprecated_parameter = True
            direction = angular_direction
            warnings.warn(
                "The 'angular_direction' parameter is deprecated and will be removed in a future version."
                " Use 'arc_size' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        center_pnt = WorkplaneList.localize(center)
        if context is None:
            ellipse_workplane = Plane.XY
        else:
            ellipse_workplane = copy_module.copy(
                WorkplaneList._get_context().workplanes[0]
            )
        ellipse_workplane.origin = center_pnt

        rotate_axis = Axis(ellipse_workplane.origin, ellipse_workplane.z_dir.to_dir())
        arc_factor = Vector(arc_size) if isinstance(arc_size, Sequence) else arc_size

        if deprecated_parameter:
            if not isinstance(arc_factor, (int, float)):
                raise ValueError(
                    "EllipticalCenterArc limit arc_size can't be used with deprecated "
                    "'end_angle' or 'angular_direction' parameters"
                )

            curve = Edge.make_ellipse(
                x_radius=x_radius,
                y_radius=y_radius,
                plane=ellipse_workplane,
                start_angle=start_angle,
                end_angle=end_a,
                angular_direction=direction,
            ).rotate(rotate_axis, rotation)

        elif isinstance(arc_factor, (int, float)):
            end_a = start_angle + arc_factor
            direction = (
                AngularDirection.COUNTER_CLOCKWISE
                if arc_factor >= 0
                else AngularDirection.CLOCKWISE
            )

            curve = Edge.make_ellipse(
                x_radius=x_radius,
                y_radius=y_radius,
                plane=ellipse_workplane,
                start_angle=start_angle,
                end_angle=end_a,
                angular_direction=direction,
            ).rotate(rotate_axis, rotation)

        else:
            curve = Edge.make_ellipse(
                x_radius=x_radius,
                y_radius=y_radius,
                plane=ellipse_workplane,
            ).rotate(rotate_axis, rotation)

            trimmed_curve = curve.trim_to_other(arc_factor)
            trimmed_curve2 = curve.reversed(reconstruct=True).trim_to_other(arc_factor)

            if trimmed_curve is None and trimmed_curve2 is None:
                raise ValueError(
                    f"EllipticalCenterArc doesn't intersect arc limit {arc_size}"
                )

            curve = ShapeList(
                [a for a in [trimmed_curve, trimmed_curve2] if a is not None]
            ).sort_by(Edge.length)[0]

        super().__init__(curve, mode=mode)


class EllipticalStartArc(BaseEdgeObject):
    """Line Object: EllipticalStartArc

    Create a circular arc defined by a start point/tangent pair, radius and arc size.

    Args:
        start_pnt (VectorLike): start point
        start_tangent (VectorLike): tangent at start point
        x_radius (float): x radius of the ellipse (along the x-axis of plane)
        y_radius (float): y radius of the ellipse (along the y-axis of plane)
        arc_size (float): angular size of arc (negative to change direction)
        start_angle (float): angular position of the start point
        major_axis_dir (VectorLike): direction of ellipse x-axis
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Note:
        One of start_angle or major_axis_dir must be provided.
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start_pnt: VectorLike,
        start_tangent: VectorLike,
        x_radius: float,
        y_radius: float,
        arc_size: float,
        *,
        start_angle: float | None = None,
        major_axis_dir: VectorLike | None = None,
        mode: Mode = Mode.ADD,
    ):
        def proj_to_plane(v: Vector, n: Vector) -> Vector:
            n = n.normalized()
            return v - n * v.dot(n)

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        start_pnt = WorkplaneList.localize(start_pnt)

        # Use current workplane (or XY) as the plane basis
        if context is None:
            workplane = Plane.XY
        else:
            workplane = copy_module.copy(WorkplaneList._get_context().workplanes[0])
        workplane.origin = start_pnt

        # Tangent: if 2D, treat as local and de-localize to global
        if isinstance(start_tangent, tuple) and len(start_tangent) == 2:
            start_tangent = (
                Vector(start_tangent)
                .transform(workplane.reverse_transform, is_direction=True)
                .normalized()
            )
        else:
            start_tangent = Vector(start_tangent).normalized()

        pln_normal = workplane.z_dir
        if start_angle is not None:
            start_angle_rad = radians(start_angle)
            pln_tangent = proj_to_plane(start_tangent, pln_normal).normalized()

            a_radius = -x_radius * sin(start_angle_rad)
            b_radius = y_radius * cos(start_angle_rad)

            x_dir = (
                a_radius * pln_tangent - b_radius * (pln_normal.cross(pln_tangent))
            ) / (a_radius * a_radius + b_radius * b_radius)
            pln_x_dir = x_dir.normalized()
            pln_y_dir = pln_normal.cross(pln_x_dir)

            pln_origin = (
                start_pnt
                - pln_x_dir * (x_radius * cos(start_angle_rad))
                - pln_y_dir * (y_radius * sin(start_angle_rad))
            )
        elif major_axis_dir is not None:
            # Work in the workplane's normal
            pln_x_dir = proj_to_plane(Vector(major_axis_dir), pln_normal).normalized()
            pln_y_dir = pln_normal.cross(pln_x_dir)

            pln_tangent = proj_to_plane(start_tangent, pln_normal)
            pln_x_radius = pln_tangent.dot(pln_x_dir)
            pln_y_radius = pln_tangent.dot(pln_y_dir)

            start_angle_rad = atan2(
                -(pln_x_radius / x_radius), (pln_y_radius / y_radius)
            )
            pln_origin = (
                start_pnt
                - pln_x_dir * (x_radius * cos(start_angle_rad))
                - pln_y_dir * (y_radius * sin(start_angle_rad))
            )
            start_angle = degrees(start_angle_rad)
        else:
            raise ValueError("Either start_angle or major_axis_dir must be provided")

        pln = Plane(pln_origin, x_dir=pln_x_dir, z_dir=pln_normal)
        end_angle = start_angle + arc_size

        direction = (
            AngularDirection.COUNTER_CLOCKWISE
            if arc_size >= 0
            else AngularDirection.CLOCKWISE
        )
        arc = Edge.make_ellipse(
            x_radius, y_radius, pln, start_angle, end_angle, direction
        )
        super().__init__(arc, mode=mode)


class ParabolicCenterArc(BaseEdgeObject):
    """Line Object: Parabolic Center Arc

    Create a parabolic arc defined by a vertex point and focal length (distance from focus to vertex).

    Args:
        vertex (VectorLike): parabola vertex
        focal_length (float): focal length the parabola (distance from the vertex to focus along the x-axis of plane)
        start_angle (float, optional): arc start angle.
            Defaults to 0.0
        end_angle (float, optional): arc end angle.
            Defaults to 90.0
        rotation (float, optional): angle to rotate arc. Defaults to 0.0
        angular_direction (AngularDirection, optional): arc direction.
            Defaults to AngularDirection.COUNTER_CLOCKWISE
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        vertex: VectorLike,
        focal_length: float,
        start_angle: float = 0.0,
        end_angle: float = 90.0,
        rotation: float = 0.0,
        angular_direction: AngularDirection = AngularDirection.COUNTER_CLOCKWISE,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        vertex_pnt = WorkplaneList.localize(vertex)
        if context is None:
            parabola_workplane = Plane.XY
        else:
            parabola_workplane = copy_module.copy(
                WorkplaneList._get_context().workplanes[0]
            )
        parabola_workplane.origin = vertex_pnt
        curve = Edge.make_parabola(
            focal_length=focal_length,
            plane=parabola_workplane,
            start_angle=start_angle,
            end_angle=end_angle,
            angular_direction=angular_direction,
        ).rotate(
            Axis(parabola_workplane.origin, parabola_workplane.z_dir.to_dir()), rotation
        )

        super().__init__(curve, mode=mode)


class HyperbolicCenterArc(BaseEdgeObject):
    """Line Object: Hyperbolic Center Arc

    Create a hyperbolic arc defined by a center point and focal length (distance from focus to vertex).

    Args:
        center (VectorLike): hyperbola center
        x_radius (float): x radius of the ellipse (along the x-axis of plane)
        y_radius (float): y radius of the ellipse (along the y-axis of plane)
        start_angle (float, optional): arc start angle from x-axis.
            Defaults to 0.0
        end_angle (float, optional): arc end angle from x-axis.
            Defaults to 90.0
        rotation (float, optional): angle to rotate arc. Defaults to 0.0
        angular_direction (AngularDirection, optional): arc direction.
            Defaults to AngularDirection.COUNTER_CLOCKWISE
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
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
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        center_pnt = WorkplaneList.localize(center)
        if context is None:
            hyperbola_workplane = Plane.XY
        else:
            hyperbola_workplane = copy_module.copy(
                WorkplaneList._get_context().workplanes[0]
            )
        hyperbola_workplane.origin = center_pnt
        curve = Edge.make_hyperbola(
            x_radius=x_radius,
            y_radius=y_radius,
            plane=hyperbola_workplane,
            start_angle=start_angle,
            end_angle=end_angle,
            angular_direction=angular_direction,
        ).rotate(
            Axis(hyperbola_workplane.origin, hyperbola_workplane.z_dir.to_dir()),
            rotation,
        )

        super().__init__(curve, mode=mode)


class Helix(BaseEdgeObject):
    """Line Object: Helix

    Create a helix defined by pitch, height, and radius. The helix may have a taper
    defined by cone_angle.

    If cone_angle is not 0, radius is the initial helix radius at center. cone_angle > 0
    increases the final radius. cone_angle < 0 decreases the final radius.

    Args:
        pitch (float): distance between loops
        height (float): helix height
        radius (float): helix radius
        center (VectorLike, optional): center point. Defaults to (0, 0, 0)
        direction (VectorLike, optional): direction of central axis. Defaults to (0, 0, 1)
        cone_angle (float, optional): conical angle from direction.
            Defaults to 0
        lefthand (bool, optional): left handed helix. Defaults to False
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
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
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        center_pnt = WorkplaneList.localize(center)
        helix = Edge.make_helix(
            pitch, height, radius, center_pnt, direction, cone_angle, lefthand
        )
        super().__init__(helix, mode=mode)


class FilletPolyline(BaseLineObject):
    """Line Object: Fillet Polyline
    Create a sequence of straight lines defined by successive points that are filleted
    to a given radius.

    Args:
        pts (VectorLike | Iterable[VectorLike]): sequence of two or more points
        radius (float | Iterable[float]): radius to fillet at each vertex or a single value for all vertices.
            A radius of 0 will create a sharp corner (vertex without fillet).

        close (bool, optional): close end points with extra Edge and corner fillets.
            Defaults to False

        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Two or more points not provided
        ValueError: radius must be non-negative
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: VectorLike | Iterable[VectorLike],
        radius: float | Iterable[float],
        close: bool = False,
        mode: Mode = Mode.ADD,
    ):

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)
        points = flatten_sequence(*pts)

        if len(points) < 2:
            raise ValueError("FilletPolyline requires two or more pts")

        if isinstance(radius, (int, float)):
            radius_list = [radius] * len(points)  # Single radius for all points

        else:
            radius_list = list(radius)
            if len(radius_list) != len(points) - int(not close) * 2:
                raise ValueError(
                    f"radius list length ({len(radius_list)}) must match angle count ({ len(points) - int(not close) * 2})"
                )

        for r in radius_list:
            if r < 0:
                raise ValueError(f"radius {r} must be non-negative")

        lines_pts = WorkplaneList.localize(*points)
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
        ordered_vertices: list[Vertex] = []

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

        # For each corner vertex create a new fillet Edge (or keep as vertex if radius is 0)
        fillets: list[None | Edge] = []

        for i, (vertex, edges) in enumerate(vertex_to_edges.items()):
            if len(edges) != 2:
                continue
            current_radius = radius_list[i - int(not close)]

            if current_radius == 0:
                # For 0 radius, store the vertex as a marker for a sharp corner
                fillets.append(None)

            else:
                other_vertices = {
                    ve for e in edges for ve in e.vertices() if ve != vertex
                }
                third_edge = Edge.make_line(*[v for v in other_vertices])
                fillet_face = Face(Wire(edges + [third_edge])).fillet_2d(
                    current_radius, [vertex]
                )
                fillets.append(fillet_face.edges().filter_by(GeomType.CIRCLE)[0])

        # Create the Edges that join the fillets
        if close:
            interior_edges = []

            for i in range(len(fillets)):
                prev_fillet = fillets[i - 1]
                curr_fillet = fillets[i]
                prev_idx = i - 1
                curr_idx = i
                # Determine start and end points
                if prev_fillet is None:
                    start_pt: Vertex | Vector = ordered_vertices[prev_idx]
                else:
                    start_pt = prev_fillet @ 1

                if curr_fillet is None:
                    end_pt: Vertex | Vector = ordered_vertices[curr_idx]
                else:
                    end_pt = curr_fillet @ 0
                interior_edges.append(Edge.make_line(start_pt, end_pt))

            end_edges = []

        else:
            interior_edges = []
            for i in range(len(fillets) - 1):
                next_fillet = fillets[i + 1]
                curr_fillet = fillets[i]
                curr_idx = i
                next_idx = i + 1
                # Determine start and end points
                if curr_fillet is None:
                    start_pt = ordered_vertices[
                        curr_idx + 1
                    ]  # +1 because first vertex has no fillet
                else:
                    start_pt = curr_fillet @ 1

                if next_fillet is None:
                    end_pt = ordered_vertices[next_idx + 1]
                else:
                    end_pt = next_fillet @ 0
                interior_edges.append(Edge.make_line(start_pt, end_pt))

            # Handle end edges
            if fillets[0] is None:
                start_edge = Edge.make_line(wire_of_lines @ 0, ordered_vertices[1])
            else:
                start_edge = Edge.make_line(wire_of_lines @ 0, fillets[0] @ 0)

            if fillets[-1] is None:
                end_edge = Edge.make_line(ordered_vertices[-2], wire_of_lines @ 1)
            else:
                end_edge = Edge.make_line(fillets[-1] @ 1, wire_of_lines @ 1)
            end_edges = [start_edge, end_edge]

        # Filter out None values from fillets (these are 0-radius corners)
        actual_fillets = [f for f in fillets if f is not None]
        new_wire = Wire(end_edges + interior_edges + actual_fillets)

        super().__init__(new_wire, mode=mode)


class JernArc(BaseEdgeObject):
    """Line Object: Jern Arc

    Create a circular arc defined by a start point/tangent pair, radius and arc size or arc limit.

    Args:
        start (VectorLike): start point
        tangent (VectorLike): tangent at start point
        radius (float): arc radius
        arc_size (float | Shape | Axis | Location | Plane | VectorLike): angular size
            of arc (negative to change direction) or an arc limit.

            When a limit object is provided instead of a numeric angular size, JernArc
            constructs the valid tangent arc(s) from the given start point and tangent,
            trims them at their first intersection with the limit, and returns the one
            requiring the shortest travel from the start. If neither valid arc intersects
            the limit, a ValueError is raised.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

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
        arc_size: float | Shape | Axis | Location | Plane | VectorLike,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        start = WorkplaneList.localize(start)
        self.start = start
        if context is None:
            jern_workplane = Plane.XY
        else:
            jern_workplane = copy_module.copy(
                WorkplaneList._get_context().workplanes[0]
            )
        jern_workplane.origin = start

        if isinstance(tangent, tuple) and len(tangent) == 2:
            # de-localize to global tangent if supplied tangent is a 2-tuple
            start_tangent = (
                Vector(tangent)
                .transform(jern_workplane.reverse_transform, is_direction=True)
                .normalized()
            )
        else:
            start_tangent = Vector(tangent).normalized()

        arc_factor = Vector(arc_size) if isinstance(arc_size, Sequence) else arc_size
        if isinstance(arc_factor, (int, float)):
            arc_direction = copysign(1.0, arc_factor)
            arc_untrimed_size = arc_factor
        else:
            arc_direction = 1
            arc_untrimed_size = 360

        center_point = start + start_tangent.rotate(
            Axis(start, jern_workplane.z_dir), arc_direction * 90
        ) * abs(radius)
        end_of_arc = center_point + (start - center_point).rotate(
            Axis(start, jern_workplane.z_dir), arc_untrimed_size
        )
        if abs(arc_untrimed_size) >= 360:
            circle_plane = copy_module.copy(jern_workplane)
            circle_plane.origin = center_point
            circle_plane.x_dir = self.start - circle_plane.origin
            arc = Edge.make_circle(radius, circle_plane)
            center_point2 = start + start_tangent.rotate(
                Axis(start, jern_workplane.z_dir), -arc_direction * 90
            ) * abs(radius)
            circle_plane2 = copy_module.copy(jern_workplane)
            circle_plane2.origin = center_point2
            circle_plane2.x_dir = self.start - circle_plane2.origin
            arc2 = Edge.make_circle(radius, circle_plane2)
            if arc2.tangent_at(0).dot(start_tangent) < 0:
                arc2 = arc2.reversed(reconstruct=True)

        else:
            arc = Edge.make_tangent_arc(start, start_tangent, end_of_arc)

        if not isinstance(arc_factor, (int, float)):
            trimmed_arc = arc.trim_to_other(arc_factor)
            trimmed_arc2 = arc2.trim_to_other(arc_factor)

            if trimmed_arc is None and trimmed_arc2 is None:
                raise ValueError(f"JernArc doesn't intersect arc limit {arc_size}")

            arc = ShapeList(
                [a for a in [trimmed_arc, trimmed_arc2] if a is not None]
            ).sort_by(Edge.length)[0]

        self.center_point = arc.arc_center
        self.end_of_arc = arc.position_at(1)

        super().__init__(arc, mode=mode)


class Line(BaseEdgeObject):
    """Line Object: Line

    Create a straight line defined by two points.

    Args:
        pts (VectorLike | Iterable[VectorLike]): sequence of two points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Two point not provided
    """

    _applies_to = [BuildLine._tag]

    def __init__(self, *pts: VectorLike | Iterable[VectorLike], mode: Mode = Mode.ADD):
        points = flatten_sequence(*pts)
        if len(points) != 2:
            raise ValueError("Line requires two pts")

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        points_localized = WorkplaneList.localize(*points)

        lines_pts = [Vector(p) for p in points_localized]

        new_edge = Edge.make_line(lines_pts[0], lines_pts[1])
        super().__init__(new_edge, mode=mode)


class IntersectingLine(BaseEdgeObject):
    """Intersecting Line Object: Line

    Create a straight line defined by a point/direction pair and another line to intersect.

    Args:
        start (VectorLike): start point
        direction (VectorLike): direction to make line
        other (Edge): line object to intersect
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start: VectorLike,
        direction: VectorLike,
        other: Curve | Edge | Wire,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
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


class PolarLine(BaseEdgeObject):
    """Line Object: Polar Line

    Create a straight line defined by a start point, length, and angle.
    The length can specify the DIAGONAL, HORIZONTAL, or VERTICAL component of the triangle
    defined by the angle.

    Alternatively, the length parameter can contain a limit to the length of the line
    in the form of another object. If the PolarLine doesn't contact the limit an error
    will be generated.

    Example:

        p = PolarLine(start=(2, 0), length=Axis.Y, angle=135)

    Args:
        start (VectorLike): start point
        length (float | Shape | Axis | Location | Plane | VectorLike): line length (float) or
            limit limit
        angle (float, optional): angle from the local x-axis
        direction (VectorLike, optional): vector direction to determine angle
        length_mode (LengthMode, optional): how length defines the line.
            Defaults to LengthMode.DIAGONAL
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Either angle or direction must be provided
        ValueError: Polar line doesn't intersect length limit

    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start: VectorLike,
        length: float | Shape | Axis | Location | Plane | VectorLike,
        angle: float | None = None,
        direction: VectorLike | None = None,
        length_mode: LengthMode = LengthMode.DIAGONAL,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        start = WorkplaneList.localize(start)
        if context is None:
            polar_workplane = Plane.XY
        else:
            polar_workplane = copy_module.copy(
                WorkplaneList._get_context().workplanes[0]
            )

        if direction is not None:
            direction_localized = WorkplaneList.localize(direction).normalized()
            angle = Vector(1, 0, 0).get_angle(direction_localized)
        elif angle is not None:
            direction_localized = polar_workplane.x_dir.rotate(
                Axis((0, 0, 0), polar_workplane.z_dir),
                angle,
            )
        else:
            raise ValueError("Either angle or direction must be provided")

        length_factor = Vector(length) if isinstance(length, Sequence) else length
        match length_factor:
            case float() | int():
                if length_mode == LengthMode.DIAGONAL:
                    length_vector = direction_localized * length_factor
                elif length_mode == LengthMode.HORIZONTAL:
                    length_vector = direction_localized * abs(
                        length_factor / cos(radians(angle))
                    )
                elif length_mode == LengthMode.VERTICAL:
                    length_vector = direction_localized * abs(
                        length_factor / sin(radians(angle))
                    )
                new_edge = Edge.make_line(start, start + length_vector)
            case Shape():
                max_length = length_factor.bounding_box().add(start).diagonal
                long_edge = Edge.make_line(
                    start, start + direction_localized * max_length
                )
                trimmed_edge = long_edge.trim_to_other(length_factor)
                if trimmed_edge is None:
                    raise ValueError(
                        f"Polar line doesn't intersect length limit {length}"
                    )
                new_edge = trimmed_edge
            case Axis() | Plane() | Location() | Vector():
                polar_axis = Axis(start, direction_localized)
                contact = polar_axis.intersect(length_factor)
                # Check for a contact point and ensure it isn't behind the start point
                if (
                    isinstance(contact, Vector)
                    and (contact - start).dot(direction_localized) > TOLERANCE
                ):
                    new_edge = Edge.make_line(start, contact)
                else:
                    raise ValueError(
                        f"Polar line doesn't intersect length limit {length}"
                    )

        super().__init__(new_edge, mode=mode)


class Polyline(BaseLineObject):
    """Line Object: Polyline

    Create a sequence of straight lines defined by successive points.

    Args:
        pts (VectorLike | Iterable[VectorLike]): sequence of two or more points
        close (bool, optional): close by generating an extra Edge. Defaults to False
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Two or more points not provided
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: VectorLike | Iterable[VectorLike],
        close: bool = False,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        points = flatten_sequence(*pts)
        if len(points) < 2:
            raise ValueError("Polyline requires two or more pts")

        lines_pts = WorkplaneList.localize(*points)

        new_edges = [
            Edge.make_line(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]
        if close and (new_edges[0] @ 0 - new_edges[-1] @ 1).length > 1e-5:
            new_edges.append(Edge.make_line(new_edges[-1] @ 1, new_edges[0] @ 0))

        super().__init__(Wire.combine(new_edges)[0], mode=mode)


class RadiusArc(BaseEdgeObject):
    """Line Object: Radius Arc

    Create a circular arc defined by two points and a radius.

    Args:
        start_point (VectorLike): start point
        end_point (VectorLike): end point
        radius (float): arc radius
        short_sagitta (bool): If True selects the short sagitta (height of arc from
            chord), else the long sagitta crossing the center. Defaults to True
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

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
        context: BuildLine | None = BuildLine._get_context(self)
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

        arc_edge = arc.edge()
        assert isinstance(arc_edge, Edge)
        super().__init__(arc_edge, mode=mode)


class SagittaArc(BaseEdgeObject):
    """Line Object: Sagitta Arc

    Create a circular arc defined by two points and the sagitta (height of the arc from chord).

    Args:
        start_point (VectorLike): start point
        end_point (VectorLike): end point
        sagitta (float): arc height from chord between points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start_point: VectorLike,
        end_point: VectorLike,
        sagitta: float,
        mode: Mode = Mode.ADD,
    ):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        start, end = WorkplaneList.localize(start_point, end_point)
        mid_point = (end + start) * 0.5
        if context is None:
            sagitta_workplane = Plane.XY
        else:
            sagitta_workplane = copy_module.copy(
                WorkplaneList._get_context().workplanes[0]
            )
        sagitta_vector: Vector = (end - start).normalized() * abs(sagitta)
        sagitta_vector = sagitta_vector.rotate(
            Axis(sagitta_workplane.origin, sagitta_workplane.z_dir),
            90 if sagitta > 0 else -90,
        )

        sag_point = mid_point + sagitta_vector

        arc = ThreePointArc(start, sag_point, end, mode=Mode.PRIVATE)
        arc_edge = arc.edge()
        assert isinstance(arc_edge, Edge)
        super().__init__(arc_edge, mode=mode)


class Spline(BaseEdgeObject):
    """Line Object: Spline

    Create a spline defined by a sequence of points, optionally constrained by tangents.
    Tangents and tangent scalars must have length of 2 for only the end points or a length
    of the number of points.

    Args:
        pts (VectorLike | Iterable[VectorLike]): sequence of two or more points
        tangents (Iterable[VectorLike], optional): tangent directions. Defaults to None
        tangent_scalars (Iterable[float], optional): tangent scales. Defaults to None
        periodic (bool, optional): make the spline periodic (closed). Defaults to False
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: VectorLike | Iterable[VectorLike],
        tangents: Iterable[VectorLike] | None = None,
        tangent_scalars: Iterable[float] | None = None,
        periodic: bool = False,
        mode: Mode = Mode.ADD,
    ):
        points = flatten_sequence(*pts)
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        spline_pts = WorkplaneList.localize(*points)

        if tangents:
            spline_tangents = [
                WorkplaneList.localize(tangent).normalized() for tangent in tangents
            ]
        else:
            spline_tangents = None

        if tangents is not None and tangent_scalars is None:
            scalars = [1.0] * len(list(tangents))
        else:
            scalars = list(tangent_scalars) if tangent_scalars is not None else []

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


class TangentArc(BaseEdgeObject):
    """Line Object: Tangent Arc

    Create a circular arc defined by two points and a tangent.

    Args:
        pts (VectorLike | Iterable[VectorLike]): sequence of two points
        tangent (VectorLike): tangent to constrain arc
        tangent_from_first (bool, optional): apply tangent to first point. Applying
            tangent to end point will flip the orientation of the arc. Defaults to True
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Two points are required
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        *pts: VectorLike | Iterable[VectorLike],
        tangent: VectorLike,
        tangent_from_first: bool = True,
        mode: Mode = Mode.ADD,
    ):
        points = flatten_sequence(*pts)
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        if len(points) != 2:
            raise ValueError("tangent_arc requires two points")
        arc_pts = WorkplaneList.localize(*points)
        arc_tangent = WorkplaneList.localize(tangent).normalized()

        point_indices = (0, -1) if tangent_from_first else (-1, 0)
        arc = Edge.make_tangent_arc(
            arc_pts[point_indices[0]], arc_tangent, arc_pts[point_indices[1]]
        )

        super().__init__(arc, mode=mode)


class ThreePointArc(BaseEdgeObject):
    """Line Object: Three Point Arc

    Create a circular arc defined by three points.

    Args:
        pts (VectorLike | Iterable[VectorLike]): sequence of three points
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Three points must be provided
    """

    _applies_to = [BuildLine._tag]

    def __init__(self, *pts: VectorLike | Iterable[VectorLike], mode: Mode = Mode.ADD):
        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        points = flatten_sequence(*pts)
        if len(points) != 3:
            raise ValueError("ThreePointArc requires three points")
        points_localized = WorkplaneList.localize(*points)
        arc = Edge.make_three_point_arc(*points_localized)

        super().__init__(arc, mode=mode)


class PointArcTangentLine(BaseEdgeObject):
    """Line Object: Point Arc Tangent Line

    Create a straight, tangent line from a point to a circular arc.

    Args:
        point (VectorLike): intersection point for tangent
        arc (Curve | Edge | Wire): circular arc to tangent, must be GeomType.CIRCLE
        side (Side, optional): side of arcs to place tangent arc center, LEFT or RIGHT.
            Defaults to Side.LEFT
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        point: VectorLike,
        arc: Curve | Edge | Wire,
        side: Side = Side.LEFT,
        mode: Mode = Mode.ADD,
    ):
        warnings.warn(
            "The 'PointArcTangentLine' object is deprecated and will be removed in a future version."
            " Use ConstrainedLines instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        side_sign = {
            Side.LEFT: -1,
            Side.RIGHT: 1,
        }

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        if arc.geom_type != GeomType.CIRCLE:
            raise ValueError("Arc must have GeomType.CIRCLE.")

        tangent_point = WorkplaneList.localize(point)
        if context is None:
            # Making the plane validates points and arc are coplanar
            coplane = Edge.make_line(tangent_point, arc.arc_center).common_plane(arc)
            if coplane is None:
                raise ValueError("PointArcTangentLine only works on a single plane.")

            workplane = Plane(coplane.origin, z_dir=arc.normal())
        else:
            workplane = copy_module.copy(WorkplaneList._get_context().workplanes[0])

        arc_center = arc.arc_center
        radius = arc.radius
        midline = tangent_point - arc_center

        if midline.length <= radius:
            raise ValueError("Cannot find tangent for point on or inside arc.")

        # Find angle phi between midline and x
        # and angle theta between midplane length and radius
        # add the resulting angles with a sign on theta to pick a direction
        # This angle is the tangent location around the circle from x
        phi = midline.get_signed_angle(workplane.x_dir)
        other_leg = sqrt(midline.length**2 - radius**2)
        theta = WorkplaneList.localize((radius, other_leg)).get_signed_angle(
            workplane.x_dir
        )
        angle = side_sign[side] * theta + phi
        intersect = (
            WorkplaneList.localize(
                (radius * cos(radians(angle)), radius * sin(radians(angle)))
            )
            + arc_center
        )

        tangent = Edge.make_line(tangent_point, intersect)
        super().__init__(tangent, mode)


class PointArcTangentArc(BaseEdgeObject):
    """Line Object: Point Arc Tangent Arc

    Create an arc defined by a point/tangent pair and another line which the other end
    is tangent to.

    Args:
        point (VectorLike): starting point of tangent arc
        direction (VectorLike): direction at starting point of tangent arc
        arc (Union[Curve, Edge, Wire]): ending arc, must be GeomType.CIRCLE
        side (Side, optional): select which arc to keep Defaults to Side.LEFT
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Arc must have GeomType.CIRCLE
        ValueError: Point is already tangent to arc
        RuntimeError: No tangent arc found
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        point: VectorLike,
        direction: VectorLike,
        arc: Curve | Edge | Wire,
        side: Side = Side.LEFT,
        mode: Mode = Mode.ADD,
    ):
        warnings.warn(
            "The 'PointArcTangentArc' object is deprecated and will be removed in a future version."
            " Use ConstrainedArcs instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        if arc.geom_type != GeomType.CIRCLE:
            raise ValueError("Arc must have GeomType.CIRCLE")

        arc_point = WorkplaneList.localize(point)
        wp_tangent = WorkplaneList.localize(direction).normalized()

        if context is None:
            # Making the plane validates point, tangent, and arc are coplanar
            coplane = Edge.make_line(arc_point, arc_point + wp_tangent).common_plane(
                arc
            )
            if coplane is None:
                raise ValueError("PointArcTangentArc only works on a single plane.")

            workplane = Plane(coplane.origin, z_dir=arc.normal())
        else:
            workplane = copy_module.copy(WorkplaneList._get_context().workplanes[0])

        arc_tangent = (
            Vector(direction)
            .transform(workplane.reverse_transform, is_direction=True)
            .normalized()
        )

        midline = arc_point - arc.arc_center
        if midline.length == arc.radius:
            raise ValueError("Cannot find tangent for point on arc.")

        if midline.length <= arc.radius:
            raise NotImplementedError("Point inside arc not yet implemented.")

        # Determine where arc_point is located relative to arc
        # ref forms a bisecting line parallel to arc tangent with same distance from arc
        # center as arc point in direction of arc tangent
        tangent_perp = arc_tangent.cross(workplane.z_dir)
        ref_scale = (arc.arc_center - arc_point).dot(-arc_tangent)
        ref = ref_scale * arc_tangent + arc.arc_center
        ref_to_point = (arc_point - ref).dot(tangent_perp)

        keep_sign = -1 if side == Side.LEFT else 1
        # Tangent radius to infinity (and beyond)
        if keep_sign * ref_to_point == arc.radius:
            raise ValueError("Point is already tangent to arc, use tangent line.")

        # Use magnitude and sign of ref to arc point along with keep to determine
        #   which "side" angle the arc center will be on
        # - the arc center is the same side if the point is further from ref than arc radius
        # - minimize type determines near or far side arc to minimize to
        side_sign = 1 if ref_to_point < 0 else -1
        if abs(ref_to_point) < arc.radius:
            # point/tangent pointing inside arc, both arcs near
            arc_type = 1
            angle = keep_sign * -90
            if ref_scale > 1:
                angle = -angle
        else:
            # point/tangent pointing outside arc, one near arc one far
            angle = side_sign * -90
            if side == side.LEFT:
                arc_type = -side_sign
            else:
                arc_type = side_sign

        # Protect against massive circles that are effectively straight lines
        max_size = 1000 * arc.bounding_box().add(arc_point).diagonal

        # Function to be minimized - note radius is a numpy array
        def func(radius, perpendicular_bisector, minimize_type):
            center = arc_point + perpendicular_bisector * radius[0]
            separation = (arc.arc_center - center).length - arc.radius

            if minimize_type == 1:
                # near side arc
                target = abs(separation - radius)
            elif minimize_type == -1:
                # far side arc
                target = abs(separation - radius + arc.radius * 2)
            return target

        # Find arc center by minimizing func result
        rotation_axis = Axis(workplane.origin, workplane.z_dir)
        perpendicular_bisector = arc_tangent.rotate(rotation_axis, angle)
        result = minimize(
            func,
            x0=0,
            args=(perpendicular_bisector, arc_type),
            method="Nelder-Mead",
            bounds=[(0.0, max_size)],
            tol=TOLERANCE,
        )
        tangent_radius = result.x[0]
        tangent_center = arc_point + perpendicular_bisector * tangent_radius

        # Check if minimizer hit max size
        if tangent_radius == max_size:
            raise RuntimeError("Arc radius very large. Can tangent line be used?")

        # dir needs to be flipped for far arc
        tangent_normal = (arc.arc_center - tangent_center).normalized()
        tangent_dir = arc_type * tangent_normal.cross(workplane.z_dir)
        tangent_point = tangent_radius * tangent_normal + tangent_center

        # Sanity Checks
        # Confirm tangent point is on arc
        if abs(arc.radius - (tangent_point - arc.arc_center).length) > TOLERANCE:
            raise RuntimeError("No tangent arc found, no tangent point found.")

        # Confirm new tangent point is colinear with point tangent on arc
        arc_dir = arc.tangent_at(tangent_point)
        if tangent_dir.cross(arc_dir).length > TOLERANCE:
            raise RuntimeError("No tangent arc found, found tangent out of tolerance.")

        arc = TangentArc(arc_point, tangent_point, tangent=arc_tangent)
        super().__init__(arc, mode=mode)


class ArcArcTangentLine(BaseEdgeObject):
    """Line Object: Arc Arc Tangent Line

    Create a straight line tangent to two arcs.

    Args:
        start_arc (Curve | Edge | Wire): starting arc, must be GeomType.CIRCLE
        end_arc (Curve | Edge | Wire): ending arc, must be GeomType.CIRCLE
        side (Side): side of arcs to place tangent arc center, LEFT or RIGHT.
            Defaults to Side.LEFT
        keep (Keep): which tangent arc to keep, INSIDE or OUTSIDE.
            Defaults to Keep.INSIDE
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start_arc: Curve | Edge | Wire,
        end_arc: Curve | Edge | Wire,
        side: Side = Side.LEFT,
        keep: Keep = Keep.INSIDE,
        mode: Mode = Mode.ADD,
    ):
        warnings.warn(
            "The 'ArcArcTangentLine' object is deprecated and will be removed in a future version."
            " Use ConstrainedLines instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        if start_arc.geom_type != GeomType.CIRCLE:
            raise ValueError("Start arc must have GeomType.CIRCLE.")

        if end_arc.geom_type != GeomType.CIRCLE:
            raise ValueError("End arc must have GeomType.CIRCLE.")

        if context is None:
            # Making the plane validates start arc and end arc are coplanar
            coplane = start_arc.common_plane(end_arc)
            if coplane is None:
                raise ValueError("ArcArcTangentLine only works on a single plane.")

            workplane = Plane(coplane.origin, z_dir=start_arc.normal())
        else:
            workplane = copy_module.copy(WorkplaneList._get_context().workplanes[0])

        side_sign = 1 if side == Side.LEFT else -1
        arcs = [start_arc, end_arc]
        points = [arc.arc_center for arc in arcs]
        radii = [arc.radius for arc in arcs]
        midline = points[1] - points[0]

        if midline.length <= abs(radii[1] - radii[0]):
            raise ValueError("Cannot find tangent when one arc contains the other.")

        if keep == Keep.INSIDE:
            if midline.length < sum(radii):
                raise ValueError("Cannot find INSIDE tangent for overlapping arcs.")

            if midline.length == sum(radii):
                raise ValueError("Cannot find INSIDE tangent for tangent arcs.")

        # Method:
        # https://en.wikipedia.org/wiki/Tangent_lines_to_circles#Tangent_lines_to_two_circles
        # - angle to point on circle of tangent incidence is theta + phi
        # - phi is angle between x axis and midline
        # - OUTSIDE theta is angle formed by triangle legs (midline.length) and (r0 - r1)
        # - INSIDE theta is angle formed by triangle legs (midline.length) and (r0 + r1)
        # - INSIDE theta for arc1 is 180 from theta for arc0

        phi = midline.get_signed_angle(workplane.x_dir)
        radius = radii[0] + radii[1] if keep == Keep.INSIDE else radii[0] - radii[1]
        other_leg = sqrt(midline.length**2 - radius**2)
        theta = WorkplaneList.localize((radius, other_leg)).get_signed_angle(
            workplane.x_dir
        )
        angle = side_sign * theta + phi

        intersect = []
        for i in range(len(arcs)):
            angle = i * 180 + angle if keep == Keep.INSIDE else angle
            intersect.append(
                WorkplaneList.localize(
                    (radii[i] * cos(radians(angle)), radii[i] * sin(radians(angle)))
                )
                + points[i]
            )

        tangent = Edge.make_line(intersect[0], intersect[1])
        super().__init__(tangent, mode)


class ArcArcTangentArc(BaseEdgeObject):
    """Line Object: Arc Arc Tangent Arc

    Create an arc tangent to two arcs and a radius.

    keep specifies tangent arc position with a Keep pair: (placement, type)

    - placement: start_arc is tangent INSIDE or OUTSIDE the tangent arc. BOTH is a
      special case for overlapping arcs with type INSIDE
    - type: tangent arc is INSIDE or OUTSIDE start_arc and end_arc

    Args:
        start_arc (Curve | Edge | Wire): starting arc, must be GeomType.CIRCLE
        end_arc (Curve | Edge | Wire): ending arc, must be GeomType.CIRCLE
        radius (float): radius of tangent arc
        side (Side): side of arcs to place tangent arc center, LEFT or RIGHT.
            Defaults to Side.LEFT
        keep (Keep | tuple[Keep, Keep]): which tangent arc to keep, INSIDE or OUTSIDE.
            Defaults to (Keep.INSIDE, Keep.INSIDE)
        short_sagitta (bool): If True selects the short sagitta (height of arc from
            chord), else the long sagitta crossing the center. Defaults to True
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildLine._tag]

    def __init__(
        self,
        start_arc: Curve | Edge | Wire,
        end_arc: Curve | Edge | Wire,
        radius: float,
        side: Side = Side.LEFT,
        keep: Keep | tuple[Keep, Keep] = (Keep.INSIDE, Keep.INSIDE),
        short_sagitta: bool = True,
        mode: Mode = Mode.ADD,
    ):
        warnings.warn(
            "The 'ArcArcTangentArc' object is deprecated and will be removed in a future version."
            " Use ConstrainedArcs instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        keep_placement, keep_type = (keep, keep) if isinstance(keep, Keep) else keep

        context: BuildLine | None = BuildLine._get_context(self)
        validate_inputs(context, self)

        if keep_placement == Keep.BOTH and keep_type != Keep.INSIDE:
            raise ValueError(
                "Keep.BOTH can only be used in configuration: (Keep.BOTH, Keep.INSIDE)"
            )

        if start_arc.geom_type != GeomType.CIRCLE:
            raise ValueError("Start arc must have GeomType.CIRCLE.")

        if end_arc.geom_type != GeomType.CIRCLE:
            raise ValueError("End arc must have GeomType.CIRCLE.")

        if context is None:
            # Making the plane validates start arc and end arc are coplanar
            coplane = start_arc.common_plane(end_arc)
            if coplane is None:
                raise ValueError("ArcArcTangentArc only works on a single plane.")

            workplane = Plane(coplane.origin, z_dir=start_arc.normal())
        else:
            workplane = copy_module.copy(WorkplaneList._get_context().workplanes[0])

        arcs = [start_arc, end_arc]
        points = [arc.arc_center for arc in arcs]
        radii = [arc.radius for arc in arcs]
        side_sign = 1 if side == Side.LEFT else -1
        keep_sign = 1 if keep_placement == Keep.OUTSIDE else -1
        r_sign = 1 if radii[0] < radii[1] else -1

        # Make a normal vector for sorting intersections
        midline = points[1] - points[0]
        normal = side_sign * midline.cross(workplane.z_dir)

        if midline.length < TOLERANCE:
            raise ValueError("Cannot find tangent for concentric arcs.")

        if abs(midline.length - sum(radii)) < TOLERANCE and keep_type == Keep.INSIDE:
            raise ValueError(
                "Cannot find tangent type Keep.INSIDE for non-overlapping arcs "
                "already tangent."
            )

        if (
            abs(midline.length - abs(radii[0] - radii[1])) < TOLERANCE
            and keep_placement == Keep.INSIDE
        ):
            raise ValueError(
                "Cannot find tangent placement Keep.INSIDE for completely "
                "overlapping arcs already tangent."
            )

        # Set following parameters based on overlap condition and keep configuration
        min_radius = 0.0
        max_radius = None
        x_sign = [1, 1]
        pick_index = 0
        if midline.length > abs(radii[0] - radii[1]) and keep_type == Keep.OUTSIDE:
            # No full overlap, placed externally
            ref_radii = [keep_sign * radii[0] + radius, keep_sign * radii[1] + radius]
            x_sign = [keep_sign, keep_sign]
            min_radius = (midline.length - keep_sign * (radii[0] + radii[1])) / 2
            min_radius = 0 if min_radius < 0 else min_radius

        elif midline.length > radii[0] + radii[1] and keep_type == Keep.INSIDE:
            # No overlap, placed inside
            ref_radii = [
                abs(radii[0] + keep_sign * radius),
                abs(radii[1] - keep_sign * radius),
            ]
            x_sign = [1, -1] if keep_placement == Keep.OUTSIDE else [-1, 1]
            min_radius = (midline.length - keep_sign * (radii[0] - radii[1])) / 2

        elif midline.length <= abs(radii[0] - radii[1]):
            # Full Overlap
            pick_index = -1
            if keep_placement == Keep.OUTSIDE:
                # External tangent to start
                ref_radii = [radii[0] + r_sign * radius, radii[1] - r_sign * radius]
                min_radius = (
                    -midline.length - r_sign * radii[0] + r_sign * radii[1]
                ) / 2
                max_radius = (
                    midline.length - r_sign * radii[0] + r_sign * radii[1]
                ) / 2

            elif keep_placement == Keep.INSIDE:
                # Internal tangent to start
                ref_radii = [abs(radii[0] - radius), abs(radii[1] - radius)]
                min_radius = (-midline.length + radii[0] + radii[1]) / 2
                max_radius = (midline.length + radii[0] + radii[1]) / 2
                if radii[0] < radii[1]:
                    x_sign = [-1, 1]
                else:
                    x_sign = [1, -1]
        else:
            # Partial Overlap
            pick_index = -1
            if keep_placement == Keep.BOTH:
                # Internal tangent to both
                ref_radii = [abs(radii[0] - radius), abs(radii[1] - radius)]
                max_radius = (-midline.length + radii[0] + radii[1]) / 2

            elif keep_placement == Keep.OUTSIDE:
                # External tangent to start
                ref_radii = [radii[0] + r_sign * radius, radii[1] - r_sign * radius]
                max_radius = (
                    midline.length - r_sign * radii[0] + r_sign * radii[1]
                ) / 2

            elif keep_placement == Keep.INSIDE:
                # Internal tangent to start
                ref_radii = [radii[0] - r_sign * radius, radii[1] + r_sign * radius]
                max_radius = (
                    midline.length + r_sign * radii[0] - r_sign * radii[1]
                ) / 2

        if min_radius >= radius:
            raise ValueError(
                f"The arc radius is too small. Should be greater than {min_radius}."
            )

        if max_radius is not None and max_radius <= radius:
            raise ValueError(
                f"The arc radius is too large. Should be less than {max_radius}."
            )

        # Method:
        # https://www.youtube.com/watch?v=-STj2SSv6TU
        # For (*, OUTSIDE) Not completely overlapping
        # - the centerpoint of the inner arc is found by the intersection of the
        #   arcs made by adding the inner radius to the point radii
        # - the centerpoint of the outer arc is found by the intersection of the
        #   arcs made by subtracting the outer radius from the point radii
        # - then it's a matter of finding the points where the connecting lines
        #   intersect the point circles
        # Other placements and types vary construction radii
        local = [workplane.to_local_coords(p) for p in points]
        ref_circles = [
            sympy.Circle(sympy.Point(local[i].X, local[i].Y), ref_radii[i])
            for i in range(len(arcs))
        ]

        ref_intersections = ShapeList(
            [
                workplane.from_local_coords(
                    Vector(float(sympy.N(p.x)), float(sympy.N(p.y)))
                )
                for p in sympy.intersection(*ref_circles)
            ]
        )
        arc_center = ref_intersections.sort_by(Axis(points[0], normal))[pick_index]

        # x_sign determines if tangent is near side or far side of circle
        intersect = [
            points[i]
            + x_sign[i] * radii[i] * (Vector(arc_center) - points[i]).normalized()
            for i in range(len(arcs))
        ]

        if side == Side.LEFT:
            intersect.reverse()

        arc = RadiusArc(
            intersect[0],
            intersect[1],
            radius=radius,
            short_sagitta=short_sagitta,
            mode=Mode.PRIVATE,
        )

        # Check and flip arc if not tangent
        start_circle = CenterArc(
            start_arc.arc_center, start_arc.radius, 0, 360, mode=Mode.PRIVATE
        )
        _, _, point = start_circle.distance_to_with_closest_points(arc)
        if (
            start_circle.tangent_at(point).cross(arc.tangent_at(point)).length
            > TOLERANCE
        ):
            arc = RadiusArc(
                intersect[0],
                intersect[1],
                radius=-radius,
                short_sagitta=short_sagitta,
                mode=Mode.PRIVATE,
            )

        super().__init__(arc, mode)
