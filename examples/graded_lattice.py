"""
Functionally graded lattice (spatially varying strut thickness)

name: graded_lattice.py
by:   Joshua Gibbins (GibbinsJosh)
date: June 3, 2026

desc:
    Why implicits? Because the *parameters* of a structure can be functions of
    position. Here a cubic strut lattice has a strut radius that grows linearly
    along Z -- thin and light at the top, thick and stiff at the bottom -- so
    the part can put material exactly where the loads are (functional grading,
    a core technique in additive manufacturing and lightweighting).

    There is no practical B-rep equivalent: you would have to model every strut
    individually at its own radius and union thousands of bodies. As a field it
    is one expression -- `radius` simply depends on `points[:, 2]` -- and the
    whole lattice is meshed in a single pass.

license: Apache-2.0 (see build123d/src/build123d/implicit.py)
"""

# [Code]
import numpy as np

from build123d import implicit_stl, import_stl

try:
    from ocp_vscode import Render, show
except ImportError:  # viewer is optional
    Render = show = None

# ---- Parameters ------------------------------------------------------------
size = (24.0, 24.0, 48.0)  # bar dimensions (mm)
cell = 8.0  # lattice unit-cell size (mm)
r_min = 0.6  # strut radius at the top  (mm)
r_max = 2.4  # strut radius at the bottom (mm)
resolution = 0.4  # marching-cubes grid spacing (mm)

half = np.array(size) / 2.0
bounds = ((-half[0], -half[1], -half[2]), (half[0], half[1], half[2]))


def _wrap(t: np.ndarray, period: float) -> np.ndarray:
    """Signed distance from t to the nearest multiple of `period`."""
    return (t + period / 2.0) % period - period / 2.0


def strut_radius(z: np.ndarray) -> np.ndarray:
    """Strut radius graded linearly from r_max (bottom) to r_min (top)."""
    frac = (z + half[2]) / size[2]  # 0 at bottom, 1 at top
    return r_max + (r_min - r_max) * frac


def graded_struts(points: np.ndarray) -> np.ndarray:
    """Cubic strut lattice whose radius varies with height."""
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    wx, wy, wz = _wrap(x, cell), _wrap(y, cell), _wrap(z, cell)
    radius = strut_radius(z)
    along_z = np.sqrt(wx * wx + wy * wy) - radius
    along_x = np.sqrt(wy * wy + wz * wz) - radius
    along_y = np.sqrt(wx * wx + wz * wz) - radius
    return np.minimum(np.minimum(along_x, along_y), along_z)


def box_sdf(points: np.ndarray) -> np.ndarray:
    """Signed-distance field of the axis-aligned bounding bar."""
    q = np.abs(points) - half
    outside = np.linalg.norm(np.maximum(q, 0.0), axis=1)
    inside = np.minimum(np.max(q, axis=1), 0.0)
    return outside + inside


def graded_field(points: np.ndarray) -> np.ndarray:
    """Graded lattice clipped to the bar: max(lattice, box)."""
    return np.maximum(graded_struts(points), box_sdf(points)).reshape(-1, 1)


_, faces = implicit_stl(graded_field, bounds, resolution, "graded_lattice.stl")
print(f"graded_lattice.stl written: {len(faces)} triangles")

if show is not None:
    # modes=[Render.FACES] hides the triangulation wireframe (the viewer draws
    # every mesh edge otherwise); default_facecolor overrides the magenta.
    show(
        import_stl("graded_lattice.stl"),
        modes=[Render.FACES],
        default_facecolor="#9fb4d4",
    )
