"""
build123d implicit field tests

name: test_implicit.py
by:   Joshua Gibbins (GibbinsJosh)
date: June 3, 2026

desc: Unit tests for build123d.implicit -- the bidirectional bridge between
      implicit/scalar fields and B-rep solids (implicit_solid, implicit_mesh,
      implicit_stl, mesh_to_sdf, SignedDistanceField).

license: Apache-2.0 (see build123d/src/build123d/implicit.py)
"""

import math
import struct
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

import numpy as np

from build123d.exporters3d import export_step, export_stl
from build123d.implicit import (
    SignedDistanceField,
    implicit_mesh,
    implicit_solid,
    implicit_stl,
    mesh_to_sdf,
)
from build123d.importers import import_stl
from build123d.objects_part import Box
from build123d.topology import Solid


def sphere_sdf(radius=10.0, center=(0.0, 0.0, 0.0)):
    """Analytic signed-distance field of a sphere (negative inside)."""
    c = np.asarray(center, dtype=float)
    return lambda p: np.linalg.norm(p - c, axis=1) - radius


def is_watertight(faces):
    """True if every edge is shared by exactly two triangles."""
    edge_count = defaultdict(int)
    for tri in faces:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edge_count[(min(a, b), max(a, b))] += 1
    return all(count == 2 for count in edge_count.values())


class TestImplicitSolid(unittest.TestCase):
    """Forward direction: implicit field -> Solid."""

    def test_sphere_volume(self):
        solid = implicit_solid(sphere_sdf(10), ((-12,) * 3, (12,) * 3), 0.6)
        self.assertIsInstance(solid, Solid)
        # within ~4% of the analytic volume (marching-cubes discretisation)
        self.assertAlmostEqual(solid.volume, 4.0 / 3.0 * math.pi * 10**3, delta=180)

    def test_returns_valid_solid(self):
        solid = implicit_solid(sphere_sdf(8), ((-10,) * 3, (10,) * 3), 0.6)
        self.assertTrue(solid.is_valid)
        self.assertGreater(solid.volume, 0)

    def test_level_offset_grows_surface(self):
        bounds = ((-15,) * 3, (15,) * 3)
        small = implicit_solid(sphere_sdf(8), bounds, 0.8, level=0.0).volume
        big = implicit_solid(sphere_sdf(8), bounds, 0.8, level=3.0).volume
        self.assertGreater(big, small)  # level shifts the isosurface outward

    def test_close_boundary_caps_to_watertight(self):
        # A sphere larger than the box pokes through its faces; capping the
        # padded grid must close those openings into a watertight mesh.
        _, faces = implicit_mesh(
            sphere_sdf(10), ((-8,) * 3, (8,) * 3), 0.5, close_boundary=True
        )
        self.assertTrue(is_watertight(faces))

    def test_no_surface_raises(self):
        with self.assertRaises(ValueError):
            implicit_solid(lambda p: np.ones(len(p)), ((-1,) * 3, (1,) * 3), 0.5)


class TestImplicitMesh(unittest.TestCase):
    def test_array_shapes(self):
        verts, faces = implicit_mesh(sphere_sdf(10), ((-12,) * 3, (12,) * 3), 0.8)
        self.assertEqual(verts.ndim, 2)
        self.assertEqual(verts.shape[1], 3)
        self.assertEqual(faces.shape[1], 3)
        self.assertTrue(faces.max() < len(verts))  # indices reference vertices


class TestImplicitStl(unittest.TestCase):
    def test_writes_readable_stl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sphere.stl"
            _, faces = implicit_stl(sphere_sdf(10), ((-12,) * 3, (12,) * 3), 0.8, path)
            self.assertTrue(path.exists())
            # binary STL header stores the triangle count
            with open(path, "rb") as f:
                f.seek(80)
                n_tri = struct.unpack("<I", f.read(4))[0]
            self.assertEqual(n_tri, len(faces))
            # OCC can read it back
            self.assertGreater(import_stl(str(path)).area, 0)


class TestMeshToSdf(unittest.TestCase):
    """Reverse direction: Solid / STEP / STL -> signed-distance field."""

    def setUp(self):
        self.box = Box(20, 14, 8)
        self.sdf = mesh_to_sdf(self.box)

    def test_returns_field(self):
        self.assertIsInstance(self.sdf, SignedDistanceField)

    def test_call_returns_column(self):
        out = self.sdf(np.zeros((5, 3)))
        self.assertEqual(out.shape, (5, 1))

    def test_bounds_match_box(self):
        (x0, y0, z0), (x1, y1, z1) = self.sdf.bounds
        self.assertAlmostEqual(x0, -10, places=5)
        self.assertAlmostEqual(y0, -7, places=5)
        self.assertAlmostEqual(z0, -4, places=5)
        self.assertAlmostEqual(x1, 10, places=5)
        self.assertAlmostEqual(y1, 7, places=5)
        self.assertAlmostEqual(z1, 4, places=5)

    def test_sign_inside_outside(self):
        self.assertLess(self.sdf(np.array([[0, 0, 0]]))[0, 0], 0)  # inside
        self.assertGreater(self.sdf(np.array([[0, 0, 20]]))[0, 0], 0)  # outside

    def test_exact_distance(self):
        # Distances to the flat faces of the box are exact (no curvature error).
        vals = self.sdf(np.array([[0, 0, 0], [9, 0, 0], [11, 0, 0]])).ravel()
        self.assertAlmostEqual(vals[0], -4.0, places=3)  # center to nearest face
        self.assertAlmostEqual(vals[1], -1.0, places=3)  # 1 mm inside +x face
        self.assertAlmostEqual(vals[2], 1.0, places=3)  # 1 mm outside +x face

    def test_roundtrip_volume(self):
        # Solid -> field -> Solid reproduces the volume within discretisation.
        rebuilt = implicit_solid(self.sdf, bounds=self.sdf.bounds, resolution=0.5)
        self.assertAlmostEqual(
            rebuilt.volume, self.box.volume, delta=self.box.volume * 0.03
        )

    def test_offset_behaves_as_metric_sdf(self):
        # f + d erodes, f - d dilates: only true for a real distance field.
        eroded = implicit_solid(
            lambda p: self.sdf(p) + 2.0, bounds=self.sdf.bounds, resolution=0.7
        ).volume
        dilated = implicit_solid(
            lambda p: self.sdf(p) - 2.0,
            bounds=((-13, -10, -7), (13, 10, 7)),
            resolution=0.7,
        ).volume
        self.assertLess(eroded, self.box.volume)
        self.assertLess(self.box.volume, dilated)

    def test_step_file_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "box.step"
            export_step(self.box, str(path))
            sdf = mesh_to_sdf(str(path), tolerance=0.1)
            self.assertLess(sdf(np.array([[0, 0, 0]]))[0, 0], 0)

    def test_stl_file_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "box.stl"
            export_stl(self.box, str(path))
            sdf = mesh_to_sdf(str(path))
            self.assertLess(sdf(np.array([[0, 0, 0]]))[0, 0], 0)

    def test_unsupported_source_raises(self):
        with self.assertRaises(ValueError):
            mesh_to_sdf("not_a_mesh.obj")


if __name__ == "__main__":
    unittest.main()
