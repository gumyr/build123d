"""
Robust uniform shelling + conformal infill, shown as a cutaway

name: conformal_shell.py
by:   Joshua Gibbins (GibbinsJosh)
date: June 3, 2026

desc:
    Why implicits? Two things the B-rep kernel struggles with become trivial:

      1. SHELLING / OFFSET. Hollowing a curved solid to a uniform wall is a
         classic place B-rep `offset`/`shell` self-intersects -- especially in
         concave regions like the neck of this "peanut". As a field, a uniform
         shell of ANY geometry is just `abs(f) - thickness`, and it cannot fail.
      2. CONFORMAL INFILL. The cavity is filled with a gyroid that follows the
         curved wall exactly, because the infill is clipped by the same field.

    The peanut here is the union of two overlapping spheres, built directly as a
    signed-distance field. The identical shell/infill algebra works on a B-rep
    part too -- just replace `peanut` with `mesh_to_sdf(my_part)` (see
    gyroid_infill.py) to hollow and lattice an imported STEP/STL.

    The model is cut in half so the uniform wall and the infill are visible.

    Field algebra (signed-distance convention: f < 0 is solid):
        C     = peanut field
        shell = max(C, -t - C)            # solid wall band, thickness t
        infill= max(|gyroid| - w, C + t)  # gyroid in the cavity (deeper than t)
        solid = min(shell, infill)        # wall + infill
        cut   = max(solid, y)             # keep y <= 0 to reveal the section

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
wall = 1.6  # shell wall thickness (mm)
cell = 7.0  # gyroid infill unit-cell size (mm)
sheet = 0.6  # gyroid sheet half-thickness (field units)
resolution = 0.5  # marching-cubes grid spacing (mm)


def sphere(points: np.ndarray, center, radius: float) -> np.ndarray:
    """Signed-distance field of a sphere."""
    return np.linalg.norm(points - np.asarray(center), axis=1) - radius


def peanut(points: np.ndarray) -> np.ndarray:
    """Two overlapping spheres unioned into a peanut (note the concave neck)."""
    return np.minimum(sphere(points, (-8, 0, 0), 11), sphere(points, (8, 0, 0), 11))


def gyroid(points: np.ndarray) -> np.ndarray:
    """Gyroid TPMS scalar field."""
    s = 2.0 * np.pi / cell
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    return (
        np.sin(x * s) * np.cos(y * s)
        + np.sin(y * s) * np.cos(z * s)
        + np.sin(z * s) * np.cos(x * s)
    )


def hollow_part(points: np.ndarray) -> np.ndarray:
    """Uniform shell + conformal gyroid infill, cut in half for viewing."""
    c = peanut(points)
    shell = np.maximum(c, -wall - c)  # solid band -wall <= c <= 0
    infill = np.maximum(np.abs(gyroid(points)) - sheet, c + wall)  # in cavity
    solid = np.minimum(shell, infill)
    return np.maximum(solid, points[:, 1])  # keep the y <= 0 half


bounds = ((-20.0, -12.0, -12.0), (20.0, 1.0, 12.0))  # y clipped to the cut half

_, faces = implicit_stl(hollow_part, bounds, resolution, "conformal_shell.stl")
print(f"conformal_shell.stl written: {len(faces)} triangles")

if show is not None:
    # modes=[Render.FACES] hides the triangulation wireframe (the viewer draws
    # every mesh edge otherwise); default_facecolor overrides the magenta.
    show(
        import_stl("conformal_shell.stl"),
        modes=[Render.FACES],
        default_facecolor="#9fb4d4",
    )
