"""
build123d NGSolve/Netgen Interoperability

name: ngsolve_interop.py
by:   build123d contributors
date: March 30th, 2026

desc:
    Provides interoperability between build123d and NGSolve/Netgen for
    finite element analysis. Transfers geometry via BREP interchange and
    propagates face labels as mesh boundary condition names using Netgen's
    faces.Nearest() API for geometric matching.

    Requires build123d's cadquery-ocp-novtk >= 7.9 and netgen-occt, which
    use separate pybind11 type namespaces and coexist in a single process
    on Python 3.10+.

    See: https://github.com/gumyr/build123d/issues/297

license:

    Copyright 2026 build123d contributors

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
import tempfile
import warnings
from typing import TYPE_CHECKING

from build123d.exporters3d import export_brep
from build123d.topology import Face, Shape

if TYPE_CHECKING:
    from netgen.occ import OCCGeometry
    from ngsolve import Mesh as NGMesh

__all__ = ["to_ngsolve_mesh"]


def _lazy_import_netgen():
    """Import netgen.occ, raising a helpful error if not installed."""
    try:
        from netgen.occ import OCCGeometry, gp_Pnt

        return OCCGeometry, gp_Pnt
    except ModuleNotFoundError:
        raise ImportError(
            "netgen is required for NGSolve interoperability but is not installed.\n"
            "Install it with:  pip install netgen-occt netgen-occt-devel\n"
            "See: https://ngsolve.org/  and  https://github.com/gumyr/build123d/issues/297"
        ) from None


def _lazy_import_ngsolve():
    """Import ngsolve, raising a helpful error if not installed."""
    try:
        import ngsolve

        return ngsolve
    except ModuleNotFoundError:
        raise ImportError(
            "ngsolve is required for NGSolve interoperability but is not installed.\n"
            "Install it with:  pip install ngsolve\n"
            "See: https://ngsolve.org/  and  https://github.com/gumyr/build123d/issues/297"
        ) from None


def _apply_face_labels(
    shape: Shape,
    ng_shape,
    gp_Pnt,
    face_labels: dict[Face, str] | None,
) -> None:
    """Apply build123d face labels to netgen shape faces using Nearest().

    Uses Netgen's ``faces.Nearest(gp_Pnt)`` API to find the corresponding
    netgen face for each build123d face by geometric center, then sets
    ``.name`` on it so the label propagates through meshing.

    Args:
        shape: The build123d Shape whose faces provide the labels.
        ng_shape: The netgen shape (from ``OCCGeometry(...).shape``).
        gp_Pnt: The netgen ``gp_Pnt`` constructor.
        face_labels: Optional dict mapping Face -> label string. If None,
            each face's ``.label`` attribute is used.
    """
    for f in shape.faces():
        if face_labels is not None:
            label = face_labels.get(f)
            if label is None:
                continue
        else:
            label = f.label if f.label else None
            if label is None:
                continue
        c = f.center()
        ng_shape.faces.Nearest(gp_Pnt(c.X, c.Y, c.Z)).name = label


def to_ngsolve_mesh(
    shape: Shape,
    face_labels: dict[Face, str] | None = None,
    maxh: float = 1.0,
    **mesh_kwargs,
) -> "NGMesh":
    """Convert a build123d Shape to an NGSolve Mesh with named boundaries.

    Transfers the geometry via BREP file interchange (direct shape passing is
    not possible because build123d and netgen use different pybind11 wrappers
    for OpenCASCADE types). Face labels are propagated to the netgen geometry
    using ``faces.Nearest(gp_Pnt).name`` before meshing, so they appear as
    boundary condition names in the resulting NGSolve mesh.

    Requires ``netgen`` and ``ngsolve`` packages to be installed. These are
    **not** hard dependencies of build123d — an ``ImportError`` with
    installation instructions is raised if they are missing.

    Args:
        shape: The build123d Shape to convert (Part, Solid, Compound, etc.).
        face_labels: Optional dictionary mapping build123d Face objects to
            label strings. These labels become NGSolve boundary condition
            names accessible via ``mesh.GetBoundaries()``. If not provided,
            each face's existing ``.label`` attribute is used; unlabeled
            faces get Netgen's default name.
        maxh: Maximum mesh element size passed to ``geo.GenerateMesh()``.
            Defaults to 1.0.
        **mesh_kwargs: Additional keyword arguments forwarded to
            ``OCCGeometry.GenerateMesh()`` (e.g. ``grading``, ``segmentsperedge``).

    Returns:
        ngsolve.Mesh: A ready-to-use NGSolve mesh with boundary condition
        names set from the face labels.

    Raises:
        ImportError: If ``netgen`` or ``ngsolve`` is not installed.

    Example:

    .. code-block:: python

        import build123d as bd
        from build123d import to_ngsolve_mesh
        import ngsolve as ngs

        # Build geometry
        part = bd.Cylinder(10, 20) - bd.Cylinder(5, 20)

        # Label faces for boundary conditions
        labels = {}
        for f in part.faces():
            if abs(f.center().Z) > 1:
                labels[f] = "ends"
            else:
                labels[f] = "walls"

        # Convert to NGSolve mesh
        mesh = to_ngsolve_mesh(part, face_labels=labels, maxh=2)
        print(mesh.GetBoundaries())

        # Use in a solve
        fes = ngs.H1(mesh, order=2, dirichlet="ends")
        u, v = fes.TnT()
        a = ngs.BilinearForm(ngs.grad(u) * ngs.grad(v) * ngs.dx).Assemble()
        f = ngs.LinearForm(1 * v * ngs.dx).Assemble()
        gfu = ngs.GridFunction(fes)
        gfu.vec.data = a.mat.Inverse(fes.FreeDofs()) * f.vec
    """
    OCCGeometry, gp_Pnt = _lazy_import_netgen()
    ngsolve = _lazy_import_ngsolve()

    if not shape.faces():
        warnings.warn(
            "Shape has no faces — the resulting mesh will have no boundaries.",
            category=UserWarning,
            stacklevel=2,
        )

    # Transfer geometry via BREP file interchange.
    # Use a TemporaryDirectory instead of NamedTemporaryFile to avoid
    # issues on Windows where the file can't be re-opened while the
    # handle is still open.
    with tempfile.TemporaryDirectory() as tmpdir:
        brep_path = os.path.join(tmpdir, "shape.brep")
        export_brep(shape, brep_path)
        geo = OCCGeometry(brep_path)

    # Apply face labels on the netgen shape using Nearest() matching,
    # then re-wrap in OCCGeometry so labels propagate through meshing.
    ng_shape = geo.shape
    _apply_face_labels(shape, ng_shape, gp_Pnt, face_labels)
    geo = OCCGeometry(ng_shape)

    # Generate the netgen mesh
    ngmesh = geo.GenerateMesh(maxh=maxh, **mesh_kwargs)

    return ngsolve.Mesh(ngmesh)
