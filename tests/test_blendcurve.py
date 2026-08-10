"""
build123d tests

name: test_blendcurve.py
by:   Gumyr
date: September 2, 2025

desc:
    This python module contains pytests for the build123d BlendCurve object.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import pytest

from build123d.objects_curve import BlendCurve, CenterArc, Spline, Line
from build123d.geometry import Vector, Pos, TOLERANCE
from build123d.build_enums import ContinuityLevel, GeomType


def _vclose(a: Vector, b: Vector, tol: float = TOLERANCE) -> bool:
    return (a - b).length <= tol


def _either_close(p: Vector, a: Vector, b: Vector, tol: float = TOLERANCE) -> bool:
    return _vclose(p, a, tol) or _vclose(p, b, tol)


def make_edges():
    """
    Arc + spline pair similar to the user demo:
      - arc radius 5, moved left a bit, reversed so the join uses the arc's 'end'
      - symmetric spline with a dip
    """
    m1 = Pos(-10, 3) * CenterArc((0, 0), 5, -10, 200).reversed()
    m2 = Pos(5, -13) * Spline((-3, 9), (0, 0), (3, 9))
    return m1, m2


def test_c0_positions_match_endpoints():
    m1, m2 = make_edges()

    # No end_points passed -> should auto-pick closest pair of vertices.
    bc = BlendCurve(m1, m2, continuity=ContinuityLevel.C0)

    # Start of connector must be one of m1's endpoints; end must be one of m2's endpoints.
    m1_p0, m1_p1 = m1.position_at(0), m1.position_at(1)
    m2_p0, m2_p1 = m2.position_at(0), m2.position_at(1)

    assert _either_close(bc.position_at(0), m1_p0, m1_p1)
    assert _either_close(bc.position_at(1), m2_p0, m2_p1)

    # Geometry type should be a line for C0.
    assert bc.geom_type == GeomType.LINE


@pytest.mark.parametrize("continuity", [ContinuityLevel.C1, ContinuityLevel.C2])
def test_c1_c2_tangent_matches_with_scalars(continuity):
    m1, m2 = make_edges()

    # Force a specific endpoint pairing to avoid ambiguity
    start_pt = m1.position_at(1)  # arc end
    end_pt = m2.position_at(0)  # spline start
    s0, s1 = 1.7, 0.8

    bc = BlendCurve(
        m1,
        m2,
        continuity=continuity,
        end_points=(start_pt, end_pt),
        tangent_scalars=(s0, s1),
    )

    # Positions must match exactly at the ends
    assert _vclose(bc.position_at(0), start_pt)
    assert _vclose(bc.position_at(1), end_pt)

    # First-derivative (tangent) must match inputs * scalars
    exp_d1_start = m1.derivative_at(1, 1) * s0
    exp_d1_end = m2.derivative_at(0, 1) * s1

    got_d1_start = bc.derivative_at(0, 1)
    got_d1_end = bc.derivative_at(1, 1)

    assert _vclose(got_d1_start, exp_d1_start)
    assert _vclose(got_d1_end, exp_d1_end)

    # C1/C2 connectors are Bezier curves
    assert bc.geom_type == GeomType.BEZIER

    if continuity == ContinuityLevel.C2:
        # Second derivative must also match at both ends
        exp_d2_start = m1.derivative_at(1, 2)
        exp_d2_end = m2.derivative_at(0, 2)

        got_d2_start = bc.derivative_at(0, 2)
        got_d2_end = bc.derivative_at(1, 2)

        assert _vclose(got_d2_start, exp_d2_start)
        assert _vclose(got_d2_end, exp_d2_end)


def test_auto_select_closest_endpoints_simple_lines():
    # Construct two simple lines with an unambiguous closest-endpoint pair
    a = Line((0, 0), (1, 0))
    b = Line((2, 0), (2, 1))

    bc = BlendCurve(a, b, continuity=ContinuityLevel.C0)

    assert _vclose(bc.position_at(0), a.position_at(1))  # (1,0)
    assert _vclose(bc.position_at(1), b.position_at(0))  # (2,0)


def test_invalid_tangent_scalars_raises():
    m1, m2 = make_edges()
    with pytest.raises(ValueError):
        BlendCurve(m1, m2, tangent_scalars=(1.0,), continuity=ContinuityLevel.C1)


def test_invalid_end_points_raises():
    m1, m2 = make_edges()
    bad_point = m1.position_at(0.5)  # not an endpoint
    with pytest.raises(ValueError):
        BlendCurve(
            m1,
            m2,
            continuity=ContinuityLevel.C1,
            end_points=(bad_point, m2.position_at(0)),
        )
