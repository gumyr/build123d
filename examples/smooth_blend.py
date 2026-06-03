"""
Smooth blending of solids (the smooth-minimum operator)

name: smooth_blend.py
by:   Joshua Gibbins (GibbinsJosh)
date: June 3, 2026

desc:
    Why implicits? Because a *field* can be combined with a smooth minimum, not
    just a hard boolean. Replacing min(a, b) (a sharp union) with a polynomial
    smooth-minimum blends two solids into one organic body with a fillet of a
    chosen radius -- everywhere they meet, at once.

    In traditional B-rep you would union the primitives and then chase the
    result with fillet operations on each resulting edge. At a multi-way
    junction (several bodies meeting at a point) those fillets are exactly where
    the kernel tends to fail or self-intersect. With a signed-distance field it
    is a single, unconditionally robust operation.

    This example renders the SAME cluster of spheres twice, side by side:
      left  -- hard union  (np.minimum): visible creases where spheres meet
      right -- smooth union (smin):       one organic blob, fillets for free

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
blend = 3.5  # blend radius of the smooth minimum (mm)
gap = 20.0  # half-distance between the two copies (mm)
resolution = 0.5  # marching-cubes grid spacing (mm)

# A cluster of overlapping spheres: (center, radius)
blobs = [
    ((0.0, 0.0, 0.0), 6.0),
    ((7.0, 2.0, 0.0), 5.0),
    ((3.0, 7.0, 1.0), 4.5),
    ((5.0, -4.0, 3.0), 5.0),
]


def sphere(points: np.ndarray, center, radius: float) -> np.ndarray:
    """Signed-distance field of a sphere."""
    return np.linalg.norm(points - np.asarray(center), axis=1) - radius


def smin(field_a: np.ndarray, field_b: np.ndarray, k: float) -> np.ndarray:
    """Polynomial smooth minimum: a soft union with a fillet of radius ~k."""
    h = np.clip(0.5 + 0.5 * (field_b - field_a) / k, 0.0, 1.0)
    return field_b * (1.0 - h) + field_a * h - k * h * (1.0 - h)


def cluster_hard(points: np.ndarray) -> np.ndarray:
    """Hard union (np.minimum) of the sphere cluster -- sharp creases."""
    dist = None
    for center, radius in blobs:
        s = sphere(points, center, radius)
        dist = s if dist is None else np.minimum(dist, s)
    return dist


def cluster_smooth(points: np.ndarray) -> np.ndarray:
    """Smooth union (smin) of the sphere cluster -- organic fillets."""
    dist = None
    for center, radius in blobs:
        s = sphere(points, center, radius)
        dist = s if dist is None else smin(dist, s, blend)
    return dist


def field(points: np.ndarray) -> np.ndarray:
    """Hard-union copy at x = -gap, smooth-union copy at x = +gap."""
    left = cluster_hard(points + np.array([gap, 0.0, 0.0]))
    right = cluster_smooth(points - np.array([gap, 0.0, 0.0]))
    return np.minimum(left, right).reshape(-1, 1)


bounds = ((-29.0, -12.0, -9.0), (35.0, 14.0, 11.0))

_, faces = implicit_stl(field, bounds, resolution, "smooth_blend.stl")
print(f"smooth_blend.stl written: {len(faces)} triangles")

if show is not None:
    # modes=[Render.FACES] hides the triangulation wireframe (the viewer draws
    # every mesh edge otherwise); default_facecolor overrides the magenta.
    show(
        import_stl("smooth_blend.stl"),
        modes=[Render.FACES],
        default_facecolor="#9fb4d4",
    )
