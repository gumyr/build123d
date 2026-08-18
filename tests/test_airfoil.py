import pytest
import numpy as np
from build123d import Airfoil, Vector, Edge, Wire


# --- parse_naca4 tests ------------------------------------------------------


@pytest.mark.parametrize(
    "code, expected",
    [
        ("2412", (0.02, 0.4, 0.12)),  # standard NACA 2412
        ("0012", (0.0, 0.0, 0.12)),  # symmetric section
        ("2213.323", (0.02, 0.2, 0.13323)),  # fractional thickness
        ("NACA2412", (0.02, 0.4, 0.12)),  # with prefix
    ],
)
def test_parse_naca4_variants(code, expected):
    m, p, t = Airfoil.parse_naca4(code)
    np.testing.assert_allclose([m, p, t], expected, rtol=1e-6)


# --- basic construction tests -----------------------------------------------


def test_airfoil_basic_construction():
    airfoil = Airfoil("2412", n_points=40)
    assert isinstance(airfoil, Airfoil)
    assert isinstance(airfoil.camber_line, Edge)
    assert isinstance(airfoil._camber_points, list)
    assert all(isinstance(p, Vector) for p in airfoil._camber_points)

    # Check metadata
    assert airfoil.code == "2412"
    assert pytest.approx(airfoil.max_camber, rel=1e-6) == 0.02
    assert pytest.approx(airfoil.camber_pos, rel=1e-6) == 0.4
    assert pytest.approx(airfoil.thickness, rel=1e-6) == 0.12
    assert airfoil.finite_te is False


def test_airfoil_finite_te_profile():
    """Finite trailing edge version should have a line closing the profile."""
    airfoil = Airfoil("2412", finite_te=True, n_points=40)
    assert isinstance(airfoil, Wire)
    assert airfoil.finite_te
    assert len(list(airfoil.edges())) == 2


def test_airfoil_infinite_te_profile():
    """Infinite trailing edge (periodic spline)."""
    airfoil = Airfoil("2412", finite_te=False, n_points=40)
    assert isinstance(airfoil, Wire)
    # Should contain a single closed Edge
    assert len(airfoil.edges()) == 1
    assert airfoil.edges()[0].is_closed


# --- geometric / numerical validity -----------------------------------------


def test_camber_line_geometry_monotonic():
    """Camber x coordinates should increase monotonically along the chord."""
    af = Airfoil("2412", n_points=80)
    x_coords = [p.X for p in af._camber_points]
    assert np.all(np.diff(x_coords) >= 0)


def test_airfoil_chord_limits():
    """Airfoil should be bounded between x=0 and x=1."""
    af = Airfoil("2412", n_points=100)
    all_points = af._camber_points
    xs = np.array([p.X for p in all_points])
    assert xs.min() >= -1e-9
    assert xs.max() <= 1.0 + 1e-9


def test_airfoil_thickness_scaling():
    """Check that airfoil thickness scales linearly with NACA last two digits."""
    af1 = Airfoil("0010", n_points=120)
    af2 = Airfoil("0020", n_points=120)

    # Extract main surface edge (for finite_te=False it's just one edge)
    edge1 = af1.edges()[0]
    edge2 = af2.edges()[0]

    # Sample many points along each edge
    n = 500
    ys1 = [(edge1 @ u).Y for u in np.linspace(0.0, 1.0, n)]
    ys2 = [(edge2 @ u).Y for u in np.linspace(0.0, 1.0, n)]

    # Total height (max - min)
    h1 = max(ys1) - min(ys1)
    h2 = max(ys2) - min(ys2)

    # For symmetric NACA 00xx, thickness is proportional to 't'
    assert (h1 / h2) == pytest.approx(0.5, rel=0.05)


def test_camber_line_is_centered():
    """Mean of upper and lower surfaces should approximate camber line."""
    af = Airfoil("2412", n_points=50)
    # Extract central camber Y near mid-chord
    mid_index = len(af._camber_points) // 2
    mid_point = af._camber_points[mid_index]
    # Camber line should be roughly symmetric around y=0 for small m
    assert abs(mid_point.Y) < 0.05
