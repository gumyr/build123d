"""
build123d implicit fields

name: implicit.py
by:   Joshua Gibbins (GibbinsJosh)
date: June 3, 2026

desc:
    A bidirectional bridge between implicit/scalar fields and build123d B-rep
    solids:

        implicit field  --implicit_solid()-->  Solid          (marching cubes)
        Solid / STEP / STL  --mesh_to_sdf()-->  implicit field (signed distance)

    Both directions share the signed-distance convention for the scalar field:

        f < 0  -> interior
        f = 0  -> surface
        f > 0  -> exterior

    Because ``mesh_to_sdf`` returns a callable in exactly the form
    ``implicit_solid`` consumes, the workflow round-trips: a traditional B-rep
    part can be converted to a field, combined with analytic fields (TPMS
    lattices, blends, offsets, shells), and meshed back into a solid. This is
    the basis for implicit infill, lattice structures, and field-driven design.

    Public API:
        implicit_solid  -- evaluate a field on a grid -> watertight Solid
        implicit_mesh   -- same, but return raw (vertices, faces) arrays
        mesh_to_sdf     -- B-rep / mesh -> SignedDistanceField callable
        SignedDistanceField -- the callable returned by mesh_to_sdf

    Marching cubes is performed with VTK (already a build123d dependency, see
    vtk_tools.py); the signed-distance reconstruction is pure NumPy.

license:

    Copyright 2026 Joshua Gibbins

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

from __future__ import annotations

import os
import struct
import tempfile
from typing import Callable, Tuple, Union

import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkFiltersCore import vtkMarchingCubes
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
from OCP.StlAPI import StlAPI_Reader
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Shape

from build123d.importers import import_step, import_stl
from build123d.topology import Shape, Solid

__all__ = [
    "implicit_solid",
    "implicit_mesh",
    "implicit_stl",
    "mesh_to_sdf",
    "SignedDistanceField",
]

Bounds = Tuple[Tuple[float, float, float], Tuple[float, float, float]]
ImplicitFunc = Callable[[np.ndarray], np.ndarray]
MeshSource = Union[Shape, str, os.PathLike]


class SignedDistanceField:
    """A callable signed-distance field derived from a triangle mesh.

    Call it with an ``(N, 3)`` array of query points; it returns an ``(N, 1)``
    array of signed distances (negative inside, positive outside) -- the same
    convention :func:`implicit_solid` consumes, so an instance can be passed
    straight back in as ``func``.

    Args:
        triangles (np.ndarray): ``(F, 3, 3)`` array of triangle vertex coords.
        batch_size (int, optional): query points evaluated per chunk. Defaults
            to an automatic value that bounds peak memory.

    Attributes:
        bounds: ``((x0, y0, z0), (x1, y1, z1))`` tight bounding box of the
            source mesh, convenient for feeding ``implicit_solid(..., bounds=)``.
        triangles: ``(F, 3, 3)`` array of triangle vertex coordinates.
    """

    def __init__(self, triangles: np.ndarray, batch_size: int | None = None):
        self.triangles = triangles
        self._v0 = triangles[:, 0, :]
        self._v1 = triangles[:, 1, :]
        self._v2 = triangles[:, 2, :]
        lo = triangles.reshape(-1, 3).min(axis=0)
        hi = triangles.reshape(-1, 3).max(axis=0)
        self.bounds = (tuple(lo.tolist()), tuple(hi.tolist()))
        self._batch_size = batch_size

    def __call__(self, points: np.ndarray) -> np.ndarray:
        points = np.asarray(points, dtype=np.float64).reshape(-1, 3)
        n_tri = len(self._v0)
        # Keep the (batch x triangles x 3) broadcast within ~16M floats.
        batch = self._batch_size or max(1, 16_000_000 // max(n_tri, 1))
        out = np.empty(len(points), dtype=np.float64)
        for i in range(0, len(points), batch):
            out[i : i + batch] = _signed_distance_batch(
                points[i : i + batch], self._v0, self._v1, self._v2
            )
        return out.reshape((-1, 1))


def implicit_solid(
    func: ImplicitFunc,
    bounds: Bounds,
    resolution: float,
    *,
    level: float = 0.0,
    close_boundary: bool = True,
) -> Solid:
    """implicit_solid

    Evaluate an implicit function on a grid and return a watertight build123d
    Solid via marching cubes.

    Args:
        func (Callable): ``f(points) -> values`` where points is ``(N, 3)`` and
            values is ``(N,)`` or ``(N, 1)``. Negative = inside, positive =
            outside (signed-distance convention).
        bounds (tuple): ``((x0, y0, z0), (x1, y1, z1))`` axis-aligned box to
            sample within.
        resolution (float): grid spacing in model units. Smaller = finer mesh.
        level (float, optional): isosurface value to extract. Defaults to 0.0.
        close_boundary (bool, optional): if True (default), pad the sampling
            grid with an "outside" border so any surface reaching the bounding
            box is capped. Guarantees a watertight solid (required for correct
            volume and boolean operations) when the field is not already closed
            inside the bounds -- e.g. a TPMS lattice clipped to a box.

    Returns:
        Solid: a watertight solid built from the marching-cubes mesh.
    """
    verts, faces = _marching_cubes(func, bounds, resolution, level, close_boundary)
    return _mesh_to_solid(verts, faces)


def implicit_mesh(
    func: ImplicitFunc,
    bounds: Bounds,
    resolution: float,
    *,
    level: float = 0.0,
    close_boundary: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """implicit_mesh

    Return the raw marching-cubes ``(vertices, faces)`` arrays without
    converting to a Solid -- useful for inspection or alternative export
    pipelines. See :func:`implicit_solid` for argument semantics.

    Returns:
        tuple[np.ndarray, np.ndarray]: ``(vertices (V, 3), faces (F, 3))``.
    """
    return _marching_cubes(func, bounds, resolution, level, close_boundary)


def implicit_stl(
    func: ImplicitFunc,
    bounds: Bounds,
    resolution: float,
    file_path: str | os.PathLike,
    *,
    level: float = 0.0,
    close_boundary: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """implicit_stl

    Mesh an implicit field and write it straight to a binary STL file, skipping
    B-rep reconstruction. This is the fast, practical path for 3D-printable
    implicit geometry (infill, TPMS lattices, struts): for meshes with tens to
    hundreds of thousands of triangles it is orders of magnitude faster than
    :func:`implicit_solid`, which must sew every triangle into an OCC solid.

    Use :func:`implicit_solid` instead when you need a B-rep ``Solid`` for
    boolean composition with other CAD parts or for STEP export.

    Args:
        func, bounds, resolution, level, close_boundary: see
            :func:`implicit_solid`.
        file_path: destination ``.stl`` path.

    Returns:
        tuple[np.ndarray, np.ndarray]: the ``(vertices, faces)`` that were
        written, for any further inspection.
    """
    verts, faces = _marching_cubes(func, bounds, resolution, level, close_boundary)
    _write_binary_stl(os.fspath(file_path), verts, faces)
    return verts, faces


# ---- Reverse direction: B-rep / mesh -> signed-distance field --------------


def mesh_to_sdf(
    source: MeshSource,
    *,
    tolerance: float | None = None,
    angular_tolerance: float = 0.2,
    batch_size: int | None = None,
) -> SignedDistanceField:
    """mesh_to_sdf

    Convert a build123d solid / STEP / STL into a signed-distance field. This
    is the inverse of :func:`implicit_solid`: it turns traditional B-rep
    geometry into an implicit field callable that can be combined with analytic
    fields and re-meshed, so the workflow goes both ways.

    Args:
        source (Shape | str | PathLike): a build123d ``Shape`` / ``Solid``, or
            a path to a ``.step`` / ``.stp`` / ``.stl`` file.
        tolerance (float, optional): linear deflection for tessellating B-rep
            input. Defaults to ~0.1% of the bounding-box diagonal. Ignored for
            STL (already triangulated). Smaller = more faithful, slower.
        angular_tolerance (float, optional): angular deflection for
            tessellation, in radians. Defaults to 0.2.
        batch_size (int, optional): query points evaluated per chunk. Defaults
            to an automatic value that bounds peak memory.

    Returns:
        SignedDistanceField: call it with ``(N, 3)`` points to get signed
        distances (negative inside). Its ``.bounds`` attribute feeds straight
        into ``implicit_solid(..., bounds=sdf.bounds)``.

    Raises:
        ValueError: if the source produces no triangles or is an unsupported
            file type.

    Note:
        The field is reconstructed from a triangulation, so sharp edges and
        corners round off at the scale of ``tolerance`` / the meshing grid.
        B-rep -> field -> B-rep is therefore not bit-exact; choose a tolerance
        well below the smallest feature you need to preserve.

    Performance:
        Evaluation is ``O(n_points * n_triangles)``. It is cheap for low-poly
        inputs (e.g. a box) or sparse queries, but meshing the field of a
        densely tessellated part over a fine grid can be slow. Keep the input
        triangle count modest, or reuse the returned field for many queries.
    """
    triangles = _extract_triangles(source, tolerance, angular_tolerance)
    if len(triangles) == 0:
        raise ValueError("Mesh source produced no triangles")
    return SignedDistanceField(triangles, batch_size=batch_size)


def _extract_triangles(
    source: MeshSource,
    tolerance: float | None,
    angular_tolerance: float,
) -> np.ndarray:
    """Return an ``(F, 3, 3)`` array of triangle vertex coordinates."""
    shape = _as_shape(source)

    if tolerance is None:
        (x0, y0, z0), (x1, y1, z1) = _shape_bounds(shape)
        diag = float(np.linalg.norm([x1 - x0, y1 - y0, z1 - z0]))
        tolerance = max(diag * 1e-3, 1e-6)

    vertices, faces = shape.tessellate(tolerance, angular_tolerance)
    verts = np.array([(v.X, v.Y, v.Z) for v in vertices], dtype=np.float64)
    idx = np.array(faces, dtype=np.int64)
    return verts[idx]  # (F, 3, 3)


def _as_shape(source: MeshSource) -> Shape:
    if isinstance(source, Shape):
        return source
    if hasattr(source, "wrapped"):  # build123d object exposing an OCP shape
        return source  # type: ignore[return-value]
    path = os.fspath(source)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".step", ".stp"):
        return import_step(path)
    if ext == ".stl":
        return import_stl(path)
    raise ValueError(
        f"Unsupported mesh source '{path}': expected a build123d Shape or a "
        f".step/.stp/.stl file"
    )


def _shape_bounds(shape: Shape) -> Bounds:
    bb = shape.bounding_box()
    return (
        (bb.min.X, bb.min.Y, bb.min.Z),
        (bb.max.X, bb.max.Y, bb.max.Z),
    )


def _signed_distance_batch(p, v0, v1, v2):
    """Signed distance from each point in ``p`` (B, 3) to the triangle soup.

    Magnitude is the exact point-to-triangle distance (closest-feature
    algorithm, Ericson, Real-Time Collision Detection, sec. 5.1.5); sign comes
    from the generalized winding number (Jacobson et al. 2013), which is robust
    for watertight meshes regardless of triangle orientation.
    """
    p = p[:, None, :]  # (B, 1, 3)
    a, b, c = v0[None], v1[None], v2[None]  # (1, M, 3)

    ab = b - a
    ac = c - a
    ap = p - a
    d1 = np.sum(ab * ap, axis=2)
    d2 = np.sum(ac * ap, axis=2)
    bp = p - b
    d3 = np.sum(ab * bp, axis=2)
    d4 = np.sum(ac * bp, axis=2)
    cp = p - c
    d5 = np.sum(ab * cp, axis=2)
    d6 = np.sum(ac * cp, axis=2)

    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2

    # Barycentric (v, w) of the closest point, start with the face-interior case.
    denom = va + vb + vc
    inv = np.divide(1.0, denom, out=np.zeros_like(denom), where=denom != 0)
    v = vb * inv
    w = vc * inv

    def _safe(num, den):
        return np.divide(num, den, out=np.zeros_like(num), where=den != 0)

    # Edge BC: closest = b + t(c - b)  ->  v = 1 - t, w = t
    region_bc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    t_bc = _safe(d4 - d3, (d4 - d3) + (d5 - d6))
    v = np.where(region_bc, 1.0 - t_bc, v)
    w = np.where(region_bc, t_bc, w)

    # Edge AC: v = 0, w = d2 / (d2 - d6)
    region_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    w_ac = _safe(d2, d2 - d6)
    v = np.where(region_ac, 0.0, v)
    w = np.where(region_ac, w_ac, w)

    # Edge AB: v = d1 / (d1 - d3), w = 0
    region_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    v_ab = _safe(d1, d1 - d3)
    v = np.where(region_ab, v_ab, v)
    w = np.where(region_ab, 0.0, w)

    # Vertex regions (take precedence over edges).
    region_a = (d1 <= 0) & (d2 <= 0)
    region_b = (d3 >= 0) & (d4 <= d3)
    region_c = (d6 >= 0) & (d5 <= d6)
    v = np.where(region_a, 0.0, v)
    w = np.where(region_a, 0.0, w)
    v = np.where(region_b, 1.0, v)
    w = np.where(region_b, 0.0, w)
    v = np.where(region_c, 0.0, v)
    w = np.where(region_c, 1.0, w)

    closest = a + ab * v[..., None] + ac * w[..., None]  # (B, M, 3)
    dist2 = np.sum((p - closest) ** 2, axis=2)  # (B, M)
    unsigned = np.sqrt(dist2.min(axis=1))  # (B,)

    # Generalized winding number for the inside/outside sign.
    av = a - p
    bv = b - p
    cv = c - p
    la = np.linalg.norm(av, axis=2)
    lb = np.linalg.norm(bv, axis=2)
    lc = np.linalg.norm(cv, axis=2)
    num = np.sum(av * np.cross(bv, cv), axis=2)
    den = (
        la * lb * lc
        + np.sum(av * bv, axis=2) * lc
        + np.sum(av * cv, axis=2) * lb
        + np.sum(bv * cv, axis=2) * la
    )
    winding = np.sum(np.arctan2(num, den), axis=1) / (2.0 * np.pi)
    inside = np.abs(winding) > 0.5  # orientation-independent

    return np.where(inside, -unsigned, unsigned)


# ---- Marching cubes via VTK ------------------------------------------------


def _marching_cubes(
    func: ImplicitFunc,
    bounds: Bounds,
    resolution: float,
    level: float,
    close_boundary: bool,
) -> Tuple[np.ndarray, np.ndarray]:
    (x0, y0, z0), (x1, y1, z1) = bounds

    nx = max(int(np.ceil((x1 - x0) / resolution)), 2)
    ny = max(int(np.ceil((y1 - y0) / resolution)), 2)
    nz = max(int(np.ceil((z1 - z0) / resolution)), 2)

    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(y0, y1, ny)
    zs = np.linspace(z0, z1, nz)

    dx = (x1 - x0) / (nx - 1)
    dy = (y1 - y0) / (ny - 1)
    dz = (z1 - z0) / (nz - 1)

    grid = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1)
    points = grid.reshape(-1, 3)
    # vol[i, j, k] == func(xs[i], ys[j], zs[k])  (C-order reshape matches the
    # meshgrid 'ij' iteration order, where the last axis varies fastest).
    vol: np.ndarray = np.asarray(func(points), dtype=np.float64).reshape(nx, ny, nz)

    origin = (x0, y0, z0)
    if close_boundary:
        # Pad with one layer of "outside" (positive) values on every face so
        # marching cubes caps any surface that reaches the bounding box,
        # yielding a watertight mesh. The pad value must exceed `level`.
        pad_value = max(float(np.nanmax(vol)), level) + abs(level) + 1.0
        vol = np.pad(vol, 1, mode="constant", constant_values=pad_value)
        origin = (x0 - dx, y0 - dy, z0 - dz)

    dims = vol.shape  # (Nx, Ny, Nz) after optional padding

    image_data = vtkImageData()
    image_data.SetDimensions(*dims)
    image_data.SetOrigin(*origin)
    image_data.SetSpacing(dx, dy, dz)

    # VTK vtkImageData expects the scalar array flattened x-fastest (Fortran
    # order over (Nx, Ny, Nz)); a plain C-order ravel would transpose the field.
    vtk_arr = numpy_to_vtk(vol.ravel(order="F"), deep=True)
    vtk_arr.SetName("implicit")
    image_data.GetPointData().SetScalars(vtk_arr)

    mc = vtkMarchingCubes()
    mc.SetInputData(image_data)
    mc.SetValue(0, level)
    mc.ComputeNormalsOff()
    mc.Update()

    polydata = mc.GetOutput()
    if polydata.GetNumberOfCells() == 0:
        raise ValueError(
            "Marching cubes produced no triangles. Check that the isosurface "
            f"at level={level} intersects the bounds."
        )

    vtk_pts = vtk_to_numpy(polydata.GetPoints().GetData()).copy()
    n_cells = polydata.GetNumberOfCells()
    faces_list = []
    for i in range(n_cells):
        cell = polydata.GetCell(i)
        ids = cell.GetPointIds()
        faces_list.append([ids.GetId(j) for j in range(ids.GetNumberOfIds())])
    vtk_faces = np.array(faces_list, dtype=np.int64)

    # SDF convention: negative = inside. VTK marching cubes generates outward
    # normals for the "high" side, so flip winding to get correct orientation.
    vtk_faces = vtk_faces[:, ::-1]

    return vtk_pts, vtk_faces


# ---- Mesh -> build123d Solid via OCP sewing --------------------------------


def _mesh_to_solid(verts: np.ndarray, faces: np.ndarray) -> Solid:
    stl_path = os.path.join(tempfile.mkdtemp(), "_implicit.stl")
    _write_binary_stl(stl_path, verts, faces)

    reader = StlAPI_Reader()
    shape = TopoDS_Shape()
    reader.Read(shape, stl_path)

    sewing = BRepBuilderAPI_Sewing(1e-6)
    sewing.Add(shape)
    sewing.Perform()
    sewn = sewing.SewedShape()

    maker = BRepBuilderAPI_MakeSolid()
    if sewn.ShapeType() == TopAbs_SHELL:
        maker.Add(TopoDS.Shell(sewn))
    else:
        explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
        while explorer.More():
            maker.Add(TopoDS.Shell(explorer.Current()))
            explorer.Next()

    maker.Build()
    if not maker.IsDone():
        raise RuntimeError(
            "Failed to build solid from mesh -- mesh may not be watertight"
        )

    os.unlink(stl_path)
    return Solid(maker.Solid())


def _write_binary_stl(path: str, verts: np.ndarray, faces: np.ndarray) -> None:
    """Write a binary STL, fully vectorized (no per-triangle Python loop)."""
    tris = verts[faces].astype(np.float32)  # (F, 3, 3)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    normals = np.cross(v1 - v0, v2 - v0)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    np.divide(normals, lengths, out=normals, where=lengths != 0)

    n_tri = len(tris)
    record = np.dtype(
        [
            ("normal", "<3f4"),
            ("v0", "<3f4"),
            ("v1", "<3f4"),
            ("v2", "<3f4"),
            ("attr", "<u2"),
        ]
    )
    data = np.empty(n_tri, dtype=record)
    data["normal"] = normals.astype(np.float32)
    data["v0"] = v0
    data["v1"] = v1
    data["v2"] = v2
    data["attr"] = 0

    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", n_tri))
        f.write(data.tobytes())
