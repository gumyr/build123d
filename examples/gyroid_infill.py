"""
Gyroid TPMS infill inside a build123d part

name: gyroid_infill.py
by:   Joshua Gibbins (GibbinsJosh)
date: June 3, 2026

desc:
    Demonstrates the bidirectional implicit-field API (build123d.implicit):

      1. REVERSE  -- a traditional B-rep part (here a Box, but it could be any
         Solid or an imported STEP/STL) is converted into a signed-distance
         field with ``mesh_to_sdf``.
      2. FORWARD  -- that field is combined with an analytic gyroid field and
         meshed back into geometry with ``implicit_stl`` / ``implicit_solid``.

    The result is a gyroid triple-periodic-minimal-surface (TPMS) infill
    clipped to the part -- built by composing scalar fields and meshing once,
    so there are no fragile B-rep booleans on the lattice itself.

    Field algebra (signed-distance convention: f < 0 is solid):
        C      = mesh_to_sdf(container)          # the part as a field
        sheet  = |gyroid| - wall                 # thick the minimal surface
        infill = max(sheet, C)                   # clip the sheet inside C

    To turn this into a closed part with solid outer walls, union a wall band
    onto the infill (see the commented `skin` lines below).

license: Apache-2.0 (see build123d/src/build123d/implicit.py)
"""

# [Code]
import numpy as np

from build123d import Box, implicit_stl, import_stl, mesh_to_sdf

try:
    from ocp_vscode import Render, show
except ImportError:  # viewer is optional
    Render = show = None

# ---- Parameters ------------------------------------------------------------
size = (40.0, 40.0, 16.0)  # outer dimensions of the part (mm)
cell = 8.0  # gyroid unit-cell size / period (mm)
wall = 0.55  # gyroid sheet half-thickness (field units)
resolution = 0.4  # marching-cubes grid spacing (mm); smaller = finer

# ---- 1. REVERSE: part B-rep -> signed-distance field -----------------------
# Swap Box(*size) for mesh_to_sdf("my_part.step") to infill any imported part.
container = Box(*size)
csdf = mesh_to_sdf(container)


# ---- The analytic gyroid field --------------------------------------------
def gyroid(points: np.ndarray) -> np.ndarray:
    """Gyroid TPMS scalar field; the zero level set is the minimal surface."""
    s = 2.0 * np.pi / cell
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    g = (
        np.sin(x * s) * np.cos(y * s)
        + np.sin(y * s) * np.cos(z * s)
        + np.sin(z * s) * np.cos(x * s)
    )
    return g.reshape(-1, 1)


# ---- 2. FORWARD: compose fields, then mesh ---------------------------------
def part_field(points: np.ndarray) -> np.ndarray:
    """Gyroid sheet clipped to the container: max(|gyroid| - wall, C)."""
    c = csdf(points)
    infill = np.maximum(np.abs(gyroid(points)) - wall, c)  # sheet inside part
    # For a closed part with solid 1.6 mm walls, union a wall band instead:
    #     skin = np.maximum(c, -1.6 - c)   # solid band -1.6 <= c <= 0
    #     return np.minimum(skin, infill)
    return infill


# Fast path: mesh straight to a printable STL (recommended for lattices --
# hundreds of thousands of triangles in a couple of seconds).
verts, faces = implicit_stl(
    part_field,
    bounds=csdf.bounds,
    resolution=resolution,
    file_path="gyroid_infill.stl",
)
print(f"gyroid_infill.stl written: {len(faces)} triangles")

# Preview the result by re-importing the mesh (fast). If you need a true B-rep
# Solid for boolean composition or STEP export, use instead:
#     from build123d import implicit_solid
#     part = implicit_solid(part_field, bounds=csdf.bounds, resolution=0.7)
if show is not None:
    # modes=[Render.FACES] hides the triangulation wireframe (the viewer draws
    # every mesh edge otherwise); default_facecolor overrides the magenta.
    show(
        import_stl("gyroid_infill.stl"),
        modes=[Render.FACES],
        default_facecolor="#9fb4d4",
    )
