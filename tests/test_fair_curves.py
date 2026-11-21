# SPDX-License-Identifier: Apache-2.0
"""Public fair-curve factories and independent geometric constraints."""

from math import cos, degrees, inf, nan, nextafter, radians, sin
from unittest.mock import patch

import pytest
import OCP.FairCurve as faircurve

from build123d import Edge, GeomType, Plane, Vector
from build123d.geometry import TOLERANCE
from build123d.topology import one_d

FACTORIES = ("make_batten", "make_minimal_variation")


def _make(factory, **kwargs):
    return getattr(Edge, factory)((0, 0), (10, 0), 0.1, **kwargs)


def _close(actual, expected, tolerance=TOLERANCE):
    assert (Vector(actual) - Vector(expected)).length <= tolerance


@pytest.mark.parametrize("factory", FACTORIES)
def test_straight(factory):
    """Zero endpoint angles preserve the chord and forward direction."""
    edge = _make(factory)
    assert edge.is_valid
    assert edge.geom_type == GeomType.BSPLINE
    assert edge.length == pytest.approx(10, abs=TOLERANCE)
    _close(edge.start_point(), (0, 0, 0))
    _close(edge.end_point(), (10, 0, 0))
    _close(edge.tangent_at(0), (1, 0, 0))
    _close(edge.tangent_at(1), (1, 0, 0))


@pytest.mark.parametrize("factory", FACTORIES)
def test_directed_tangents(factory):
    """Endpoint tangents use chord-relative angles in degrees."""
    edge = getattr(Edge, factory)((2, 3), (8, 11), 0.1, 20, -15)
    chord = Vector(0.6, 0.8, 0)
    left = Vector(-0.8, 0.6, 0)
    for parameter, angle in ((0, 20), (1, -15)):
        expected = chord * cos(radians(angle)) + left * sin(radians(angle))
        _close(edge.tangent_at(parameter), expected)
    assert edge.is_valid
    _close(edge.start_point(), (2, 3, 0))
    _close(edge.end_point(), (8, 11, 0))


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize(
    "plane,x_direction,y_direction",
    (
        (
            Plane((3, -4, 7), x_dir=(0, 1, 0), z_dir=(1, 0, 0)),
            Vector(0, 1, 0),
            Vector(0, 0, 1),
        ),
        (Plane.XZ, Vector(1, 0, 0), Vector(0, 0, 1)),
    ),
    ids=("translated_rotated", "xz"),
)
def test_world_plane(factory, plane, x_direction, y_direction):
    """World points and directions survive plane conversion without a second transform."""
    start = plane.origin + x_direction * 2 + y_direction * 3
    end = start + x_direction * 6 + y_direction * 8
    edge = getattr(Edge, factory)(start, end, 0.1, 20, -15, plane=plane)
    _close(edge.start_point(), start)
    _close(edge.end_point(), end)
    chord = x_direction * 0.6 + y_direction * 0.8
    left = x_direction * -0.8 + y_direction * 0.6
    for parameter, angle in ((0, 20), (1, -15)):
        _close(
            edge.tangent_at(parameter),
            chord * cos(radians(angle)) + left * sin(radians(angle)),
        )
    for index in range(11):
        assert (
            abs((edge.position_at(index / 10) - plane.origin).dot(plane.z_dir))
            <= TOLERANCE
        )
    assert edge.is_valid


@pytest.mark.parametrize("factory", FACTORIES)
def test_reflection_and_reversal(factory):
    """Reflection negates angles; endpoint reversal exchanges them."""
    edge = _make(factory, start_angle=20, end_angle=-15)
    reflected = _make(factory, start_angle=-20, end_angle=15)
    reversed_edge = getattr(Edge, factory)((10, 0), (0, 0), 0.1, -15, 20)
    for index in range(11):
        parameter = index / 10
        point = edge.position_at(parameter)
        _close(reflected.position_at(parameter), (point.X, -point.Y, point.Z))
        _close(reversed_edge.position_at(1 - parameter), point)
    _close(reversed_edge.tangent_at(0), -edge.tangent_at(1))
    _close(reversed_edge.tangent_at(1), -edge.tangent_at(0))


@pytest.mark.parametrize("factory", FACTORIES)
def test_height_changes_curve(factory):
    """A changed strip height changes a nontrivial curve without a monotonicity claim."""
    thin = _make(factory, start_angle=20, end_angle=-15)
    thick = getattr(Edge, factory)((0, 0), (10, 0), 1, 20, -15)
    assert thin.is_valid and thick.is_valid
    assert (
        max(
            (thin.position_at(index / 10) - thick.position_at(index / 10)).length
            for index in range(1, 10)
        )
        > 1e-6
    )


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize(
    "kwargs",
    (
        {"height": 0},
        {"height": -1},
        {"height": inf},
        {"tolerance": 0},
        {"tolerance": -1},
        {"tolerance": nan},
        {"start_angle": inf},
        {"end_angle": nan},
        {"max_iterations": 0},
        {"max_iterations": -1},
        {"max_iterations": 1.5},
        {"max_iterations": True},
        {"start": (nan, 0)},
        {"end": (inf, 0)},
        {"end": (0, 0)},
        {"end": (TOLERANCE / 2, 0)},
        {"start": (0, 0, 2 * TOLERANCE)},
        {"end": (10, 0, -2 * TOLERANCE)},
    ),
)
def test_invalid_inputs(factory, kwargs):
    """Invalid geometry and solver controls fail before native solver construction."""
    arguments = {"start": (0, 0), "end": (10, 0), "height": 0.1}
    arguments.update(kwargs)
    with (
        patch.object(one_d, "FairCurve_Batten") as batten,
        patch.object(one_d, "FairCurve_MinimalVariation") as variation,
    ):
        with pytest.raises(ValueError):
            getattr(Edge, factory)(**arguments)
        batten.assert_not_called()
        variation.assert_not_called()


@pytest.mark.parametrize("factory", FACTORIES)
def test_true_not_converged_rejected(factory):
    """The observed one-iteration witness must fail before edge construction."""
    with patch.object(one_d, "BRepBuilderAPI_MakeEdge") as make_edge:
        with pytest.raises(ValueError, match="computation failed with status 1"):
            _make(
                factory,
                start_angle=degrees(0.35),
                end_angle=degrees(0.25),
                max_iterations=1,
                tolerance=1e-12,
            )
        make_edge.assert_not_called()


@pytest.mark.parametrize(
    "factory,native_name",
    zip(FACTORIES, ("FairCurve_Batten", "FairCurve_MinimalVariation")),
)
@pytest.mark.parametrize(
    "success,status_name",
    (
        (False, "FairCurve_OK"),
        (True, "FairCurve_InfiniteSliding"),
        (True, "FairCurve_NullHeight"),
    ),
)
def test_other_solver_failures(factory, native_name, success, status_name):
    """Neither a false Boolean nor an unsuccessful status permits an edge."""
    status = faircurve.FairCurve_AnalysisCode(int(getattr(faircurve, status_name)))
    with (
        patch.object(one_d, native_name) as solver_type,
        patch.object(one_d, "FairCurve_AnalysisCode", return_value=status),
        patch.object(one_d, "BRepBuilderAPI_MakeEdge") as make_edge,
    ):
        solver_type.return_value.Compute.return_value = success
        with pytest.raises(ValueError, match="computation failed"):
            _make(factory)
        make_edge.assert_not_called()
        solver_type.return_value.Curve.assert_not_called()


@pytest.mark.parametrize("factory", FACTORIES)
def test_fresh_status_preserves_constants(factory):
    """Output status storage stays independent across successful and failed calls."""
    names = (
        "FairCurve_OK",
        "FairCurve_NotConverged",
        "FairCurve_InfiniteSliding",
        "FairCurve_NullHeight",
    )
    constants = tuple(getattr(faircurve, name) for name in names)
    values = tuple(map(int, constants))
    statuses = []

    def fresh_status(value):
        status = faircurve.FairCurve_AnalysisCode(value)
        statuses.append(status)
        return status

    with patch.object(one_d, "FairCurve_AnalysisCode", side_effect=fresh_status):
        _make(factory)
        with pytest.raises(ValueError):
            _make(
                factory,
                start_angle=degrees(0.35),
                end_angle=degrees(0.25),
                max_iterations=1,
                tolerance=1e-12,
            )
        _make(factory)
    assert len(statuses) == 3
    assert len({id(status) for status in statuses}) == 3
    assert all(status is not constant for status in statuses for constant in constants)
    assert tuple(map(int, constants)) == values
    assert [int(status) for status in statuses] == [values[0], values[1], values[0]]


def test_existing_spline_controls():
    """Existing line and interpolation factories retain their public behavior."""
    line = Edge.make_line((0, 0), (10, 0))
    spline = Edge.make_spline([(0, 0), (5, 2), (10, 0)])
    assert line.is_valid and spline.is_valid
    assert line.length == pytest.approx(10)
    _close(spline.start_point(), (0, 0))
    _close(spline.end_point(), (10, 0))
    assert spline.position_at(0.5).Y > 1


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("name", ("start_angle", "end_angle"))
@pytest.mark.parametrize(
    "value", (nextafter(-180, -inf), nextafter(180, inf), -1e308, 1e308)
)
def test_outside_principal_angles(factory, name, value):
    """Reject angles outside the principal range before native solver construction."""
    with (
        patch.object(one_d, "FairCurve_Batten") as batten,
        patch.object(one_d, "FairCurve_MinimalVariation") as variation,
    ):
        with pytest.raises(ValueError, match="between -180 and 180"):
            _make(factory, **{name: value})
        batten.assert_not_called()
        variation.assert_not_called()


@pytest.mark.parametrize(
    "factory,native_name",
    zip(FACTORIES, ("FairCurve_Batten", "FairCurve_MinimalVariation")),
)
@pytest.mark.parametrize(
    "start_angle,end_angle", ((-180, -180), (-180, 180), (180, -180), (180, 180))
)
def test_principal_boundaries_reach_solver(
    factory, native_name, start_angle, end_angle
):
    """Accept inclusive boundary angles without requiring a difficult endpoint solve."""
    with patch.object(
        one_d, native_name, side_effect=RuntimeError("solver constructor reached")
    ) as constructor:
        with pytest.raises(RuntimeError, match="solver constructor reached"):
            _make(factory, start_angle=start_angle, end_angle=end_angle)
        constructor.assert_called_once()


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize(
    "changes",
    (
        {"start": (-1e308, 0), "end": (1e308, 0)},
        {"end": (1e200, 0)},
        {"end": (1e154, 1e154)},
        {"height": 1e308, "end": (1, 0)},
        {"height": 1e200, "end": (1e90, 0)},
        {"height": 1e308, "end": (1e-5, 0)},
        {"tolerance": 1e308, "end": (1, 0)},
        {"tolerance": 1e200, "end": (1e110, 0)},
        {"max_iterations": 10**100},
        {"max_iterations": 2147483648},
    ),
)
def test_unrepresentable_native_inputs(factory, changes):
    """Finite public values must not overflow known initial native arithmetic."""
    arguments = {"start": (0, 0), "end": (10, 0), "height": 0.1}
    arguments.update(changes)
    with (
        patch.object(one_d, "FairCurve_Batten") as batten,
        patch.object(one_d, "FairCurve_MinimalVariation") as variation,
    ):
        with pytest.raises(ValueError):
            getattr(Edge, factory)(**arguments)
        batten.assert_not_called()
        variation.assert_not_called()


@pytest.mark.parametrize("factory", FACTORIES)
def test_plane_local_overflow_rejected(factory):
    """Finite world points can overflow translation into plane coordinates."""
    plane = Plane(origin=(-1e308, 0, 0))
    with (
        patch.object(one_d, "FairCurve_Batten") as batten,
        patch.object(one_d, "FairCurve_MinimalVariation") as variation,
    ):
        with pytest.raises(ValueError, match="plane-local coordinates must be finite"):
            getattr(Edge, factory)((1e308, 0), (1e308, 1), 0.1, plane=plane)
        batten.assert_not_called()
        variation.assert_not_called()


@pytest.mark.parametrize("factory", FACTORIES)
def test_nonfinite_plane_result_rejected(factory):
    """A nonfinite local Z must not pass the plane-containment comparison."""
    with (
        patch.object(Plane, "to_local_coords", return_value=Vector(0, 0, nan)),
        patch.object(one_d, "FairCurve_Batten") as batten,
        patch.object(one_d, "FairCurve_MinimalVariation") as variation,
    ):
        with pytest.raises(ValueError, match="plane-local coordinates must be finite"):
            _make(factory)
        batten.assert_not_called()
        variation.assert_not_called()


@pytest.mark.parametrize(
    "factory,native_name",
    zip(FACTORIES, ("FairCurve_Batten", "FairCurve_MinimalVariation")),
)
@pytest.mark.parametrize(
    "changes",
    (
        {"height": 1e100, "end": (1e100, 0), "tolerance": 1e100},
        {"height": 1e-300, "end": (1e-5, 0), "tolerance": 1e300},
        {"height": 1e150, "end": (1e150, 0), "tolerance": 1e150},
        {"max_iterations": 2147483647},
    ),
)
def test_representable_native_inputs_reach_solver(factory, native_name, changes):
    """Accept derived finite controls and the native integer boundary without solving."""
    arguments = {"start": (0, 0), "end": (10, 0), "height": 0.1}
    arguments.update(changes)
    with patch.object(
        one_d, native_name, side_effect=RuntimeError("solver constructor reached")
    ) as constructor:
        with pytest.raises(RuntimeError, match="solver constructor reached"):
            getattr(Edge, factory)(**arguments)
        constructor.assert_called_once()
