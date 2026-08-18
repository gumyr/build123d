"""
build123d tests

name: test_constrained_lines.py
by:   Gumyr
date: October 8, 2025

desc:
    This python module contains tests for the build123d project.

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

import math

import pytest
from OCP.BRep import BRep_Tool
from OCP.gp import gp_Pnt2d

from build123d import Axis, Edge, Plane, Tangency, Vector
from build123d.build_enums import GeomType
from build123d.build_line import BuildLine
from build123d.geometry import TOLERANCE
from build123d.objects_curve import ConstrainedLines
from build123d.topology.constrained_lines import (
    _edge_from_line,
    _make_2tan_lines,
    _make_tan_oriented_lines,
)


@pytest.fixture
def unit_circle() -> Edge:
    """A simple unit circle centered at the origin on XY."""
    return Edge.make_circle(1.0, Plane.XY)


# ---------------------------------------------------------------------------
# utility tests
# ---------------------------------------------------------------------------


def test_edge_from_line():
    line = _edge_from_line(gp_Pnt2d(0, 0), gp_Pnt2d(1, 0))
    assert Edge(line).length == 1

    with pytest.raises(RuntimeError) as excinfo:
        _edge_from_line(gp_Pnt2d(0, 0), gp_Pnt2d(0, 0))
    assert "Failed to build edge from line contacts" in str(excinfo.value)


# ---------------------------------------------------------------------------
# _make_2tan_lines tests
# ---------------------------------------------------------------------------


def test_two_circles_tangents(unit_circle):
    """Tangent lines between two separated circles should yield four results."""
    c1 = unit_circle
    c2 = unit_circle.translate((3, 0, 0))  # displaced along X
    lines = _make_2tan_lines(c1, c2, edge_factory=Edge)
    # There should be 4 external/internal tangents
    assert len(lines) in (4, 2)
    for ln in lines:
        assert isinstance(ln, Edge)
        # Tangent lines should not intersect the circle interior
        dmin = c1.distance_to(ln)
        assert dmin >= -1e-6


def test_two_constrained_circles_tangents1(unit_circle):
    """Tangent lines between two separated circles should yield four results."""
    c1 = unit_circle
    c2 = unit_circle.translate((3, 0, 0))  # displaced along X
    lines = _make_2tan_lines((c1, Tangency.ENCLOSING), c2, edge_factory=Edge)
    # There should be 2 external/internal tangents
    assert len(lines) == 2
    for ln in lines:
        assert isinstance(ln, Edge)
        # Tangent lines should not intersect the circle interior
        dmin = c1.distance_to(ln)
        assert dmin >= -1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_two_constrained_circles_tangents2(unit_circle):
    """Tangent lines between two separated circles should yield four results."""
    c1 = unit_circle
    c2 = unit_circle.translate((3, 0, 0))  # displaced along X
    lines = _make_2tan_lines(
        (c1, Tangency.ENCLOSING), (c2, Tangency.ENCLOSING), edge_factory=Edge
    )
    # There should be 1 external/external tangents
    assert len(lines) == 1
    for ln in lines:
        assert isinstance(ln, Edge)
        # Tangent lines should not intersect the circle interior
        dmin = c1.distance_to(ln)
        assert dmin >= -1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_curve_and_point_tangent(unit_circle):
    """A line tangent to a circle and passing through a point should exist."""
    pt = Vector(2.0, 0.0)
    lines = _make_2tan_lines(unit_circle, pt, edge_factory=Edge)
    assert len(lines) == 2
    for ln in lines:
        # The line must pass through the given point (approximately)
        dist_to_point = ln.distance_to(pt)
        assert math.isclose(dist_to_point, 0.0, abs_tol=1e-6)
        # It should also touch the circle at exactly one point
        dist_to_circle = unit_circle.distance_to(ln)
        assert math.isclose(dist_to_circle, 0.0, abs_tol=TOLERANCE)
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_invalid_tangent_raises(unit_circle):
    """Non-intersecting degenerate input result in no output."""
    lines = _make_2tan_lines(unit_circle, unit_circle, edge_factory=Edge)
    assert len(lines) == 0

    with pytest.raises(RuntimeError) as excinfo:
        _make_2tan_lines(unit_circle, Vector(0, 0), edge_factory=Edge)
    assert "Unable to find common tangent line(s)" in str(excinfo.value)


# ---------------------------------------------------------------------------
# _make_tan_oriented_lines tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("angle_deg", [math.radians(30), -math.radians(30)])
def test_oriented_tangents_with_x_axis(unit_circle, angle_deg):
    """Lines tangent to a circle at ±30° from the X-axis."""
    lines = _make_tan_oriented_lines(unit_circle, Axis.X, angle_deg, edge_factory=Edge)
    assert all(isinstance(e, Edge) for e in lines)
    # The tangent lines should all intersect the X axis (red line)
    for ln in lines:
        p = ln.position_at(0.5)
        assert abs(p.Z) < 1e-9

    lines = _make_tan_oriented_lines(unit_circle, Axis.X, 0, edge_factory=Edge)
    assert len(lines) == 0

    lines = _make_tan_oriented_lines(
        unit_circle, Axis((0, -2), (1, 0)), 0, edge_factory=Edge
    )
    assert len(lines) == 0
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_oriented_tangents_with_y_axis(unit_circle):
    """Lines tangent to a circle and 30° from Y-axis should exist."""
    angle = math.radians(30)
    lines = _make_tan_oriented_lines(unit_circle, Axis.Y, angle, edge_factory=Edge)
    assert len(lines) >= 1
    # They should roughly touch the circle (tangent distance ≈ 0)
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_oriented_constrained_tangents_with_y_axis(unit_circle):
    angle = math.radians(30)
    lines = _make_tan_oriented_lines(
        (unit_circle, Tangency.ENCLOSING), Axis.Y, angle, edge_factory=Edge
    )
    assert len(lines) == 1
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_invalid_oriented_tangent_raises(unit_circle):
    """Non-intersecting degenerate input result in no output."""

    with pytest.raises(ValueError) as excinfo:
        _make_tan_oriented_lines(unit_circle, Axis.Z, 1, edge_factory=Edge)
    assert "reference Axis can't be perpendicular to Plane.XY" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        _make_tan_oriented_lines(
            unit_circle, Axis((1, 2, 3), (0, 0, -1)), 1, edge_factory=Edge
        )
    assert "reference Axis can't be perpendicular to Plane.XY" in str(excinfo.value)


def test_invalid_oriented_tangent(unit_circle):
    lines = _make_tan_oriented_lines(
        unit_circle, Axis((1, 0), (0, 1)), 0, edge_factory=Edge
    )
    assert len(lines) == 0

    lines = _make_tan_oriented_lines(
        unit_circle.translate((0, 1 + 1e-7)), Axis.X, 0, edge_factory=Edge
    )
    assert len(lines) == 0


def test_make_constrained_lines0(unit_circle):
    lines = Edge.make_constrained_lines(unit_circle, unit_circle.translate((3, 0, 0)))
    assert len(lines) == 4
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_make_constrained_lines1(unit_circle):
    lines = Edge.make_constrained_lines(unit_circle, (3, 0))
    assert len(lines) == 2
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_make_constrained_lines3(unit_circle):
    lines = Edge.make_constrained_lines(unit_circle, Axis.X, angle=30)
    assert len(lines) == 2
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
        assert abs((ln @ 1).Y) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_make_constrained_lines4(unit_circle):
    lines = Edge.make_constrained_lines(unit_circle, Axis.Y, angle=30)
    assert len(lines) == 2
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
        assert abs((ln @ 1).X) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_make_constrained_lines5(unit_circle):
    lines = Edge.make_constrained_lines(
        (unit_circle, Tangency.ENCLOSING), Axis.Y, angle=30
    )
    assert len(lines) == 1
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_make_constrained_lines6(unit_circle):
    lines = Edge.make_constrained_lines(
        (unit_circle, Tangency.ENCLOSING), Axis.Y, direction=(1, 1)
    )
    assert len(lines) == 1
    for ln in lines:
        assert unit_circle.distance_to(ln) < 1e-6
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in lines)


def test_make_constrained_lines_raises(unit_circle):
    with pytest.raises(TypeError) as excinfo:
        Edge.make_constrained_lines(unit_circle, Axis.Z, ref_angle=1)
    assert "Unexpected argument(s): ref_angle" in str(excinfo.value)

    with pytest.raises(TypeError) as excinfo:
        Edge.make_constrained_lines(unit_circle)
    assert "Provide exactly 2 tangency targets." in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        Edge.make_constrained_lines(Axis.X, Axis.Y)
    assert "Unable to find common tangent line(s)" in str(excinfo.value)

    with pytest.raises(TypeError) as excinfo:
        Edge.make_constrained_lines(unit_circle, ("three", 0))
    assert "Invalid tangency:" in str(excinfo.value)


def test_higher_level_constrained_lines(unit_circle):
    lines = ConstrainedLines(unit_circle, Axis.Y, direction=(1, 1))
    assert len(lines.edges()) == 2

    with BuildLine() as drawing:
        ConstrainedLines(
            unit_circle,
            Axis.Y,
            direction=(1, 1),
            selector=lambda l: l.sort_by(Axis.Y)[-1],
        )
    assert len(drawing.edges()) == 1

    with pytest.raises(ValueError) as excinfo:
        ConstrainedLines(
            unit_circle,
            Axis.Y,
            direction=(1, 1),
            selector=lambda l: l.filter_by(GeomType.CIRCLE),
        )
