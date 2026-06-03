"""
Periodic strut lattice infill from analytic signed-distance fields

name: lattice_infill.py
by:   Joshua Gibbins (GibbinsJosh)
date: June 3, 2026

desc:
    Builds a repeating strut lattice purely from analytic signed-distance
    fields and clips it to a bounding shape, then meshes it with
    build123d.implicit.

    The lattice is a body-centred-cubic-style network: round struts running
    along X, Y and Z through every grid node (their union), produced by
    "folding" space into a single unit cell with a modulo and taking the
    distance to the cell axes. Clipping is just a field ``max`` against the
    container's signed-distance field.

    Two clip regions are shown:
      - an analytic sphere (fast, self-contained), used for the output, and
      - a commented ``mesh_to_sdf(...)`` line showing how to clip the same
        lattice to ANY build123d Solid or imported STEP/STL instead -- the
        reverse half of the bidirectional workflow.

    Field algebra (signed-distance convention: f < 0 is solid):
        lattice = min(strut_x, strut_y, strut_z)   # union of strut families
        part    = max(lattice, container_sdf)       # intersect with region

license: Apache-2.0 (see build123d/src/build123d/implicit.py)
"""

# [Code]
import numpy as np

from build123d import implicit_stl, import_stl

# from build123d import mesh_to_sdf, Cylinder  # for the reverse-clip variant

try:
    from ocp_vscode import Render, show
except ImportError:  # viewer is optional
    Render = show = None

# ---- Parameters ------------------------------------------------------------
cell = 6.0  # lattice unit-cell size (mm)
strut_r = 1.1  # strut radius (mm)
radius = 18.0  # radius of the spherical container (mm)
resolution = 0.35  # marching-cubes grid spacing (mm)

bounds = ((-radius, -radius, -radius), (radius, radius, radius))


def _wrap(t: np.ndarray, period: float) -> np.ndarray:
    """Signed distance from t to the nearest multiple of `period`."""
    return (t + period / 2.0) % period - period / 2.0


def strut_lattice(points: np.ndarray) -> np.ndarray:
    """Cubic strut lattice: round bars along X, Y, Z through every node."""
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    wx, wy, wz = _wrap(x, cell), _wrap(y, cell), _wrap(z, cell)
    along_z = np.sqrt(wx * wx + wy * wy) - strut_r
    along_x = np.sqrt(wy * wy + wz * wz) - strut_r
    along_y = np.sqrt(wx * wx + wz * wz) - strut_r
    return np.minimum(np.minimum(along_x, along_y), along_z).reshape(-1, 1)


# ---- Container field -------------------------------------------------------
# Analytic sphere SDF (fast). To clip to a real part instead, replace these two
# lines with, e.g.:
#     from build123d import mesh_to_sdf, Cylinder
#     container = mesh_to_sdf(Cylinder(radius=18, height=30))
#     bounds = container.bounds
def container(points: np.ndarray) -> np.ndarray:
    """Signed-distance field of the spherical bounding region."""
    return (np.linalg.norm(points, axis=1) - radius).reshape(-1, 1)


def lattice_field(points: np.ndarray) -> np.ndarray:
    """Strut lattice clipped to the container: max(lattice, container)."""
    return np.maximum(strut_lattice(points), container(points))


# ---- Mesh it ---------------------------------------------------------------
verts, faces = implicit_stl(
    lattice_field,
    bounds=bounds,
    resolution=resolution,
    file_path="lattice_infill.stl",
)
print(f"lattice_infill.stl written: {len(faces)} triangles")

# Preview by re-importing the mesh (fast). For a true B-rep Solid (boolean
# composition / STEP export) use instead:
#     from build123d import implicit_solid
#     part = implicit_solid(lattice_field, bounds=bounds, resolution=0.6)
if show is not None:
    # modes=[Render.FACES] hides the triangulation wireframe (the viewer draws
    # every mesh edge otherwise); default_facecolor overrides the magenta.
    show(
        import_stl("lattice_infill.stl"),
        modes=[Render.FACES],
        default_facecolor="#9fb4d4",
    )
