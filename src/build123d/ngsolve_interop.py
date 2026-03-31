"""
build123d NGSolve/Netgen Interoperability

name: ngsolve_interop.py
by:   build123d contributors
date: March 30th, 2026

desc:
    Provides interoperability between build123d and NGSolve/Netgen for
    finite element analysis. Transfers geometry via BREP interchange and
    propagates face labels as mesh boundary condition names using geometric
    center matching.

    Requires Python 3.12+ where cadquery-ocp and netgen-occt both use
    OCCT 7.8.1, allowing coexistence in the same process.

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

import math
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
        from netgen.occ import OCCGeometry

        return OCCGeometry
    except ImportError:
        raise ImportError(
            "netgen is required for NGSolve interoperability but is not installed.\n"
            "Install it with:  pip install netgen-occt netgen-occt-devel\n"
            "Note: Python 3.12+ is required so that cadquery-ocp and netgen-occt\n"
            "both use matching OCCT versions (7.8.1+).\n"
            "See: https://ngsolve.org/  and  https://github.com/gumyr/build123d/issues/297"
        ) from None


def _lazy_import_ngsolve():
    """Import ngsolve, raising a helpful error if not installed."""
    try:
        import ngsolve

        return ngsolve
    except ImportError:
        raise ImportError(
            "ngsolve is required for NGSolve interoperability but is not installed.\n"
            "Install it with:  pip install ngsolve\n"
            "Note: Python 3.12+ is required so that cadquery-ocp and netgen-occt\n"
            "both use matching OCCT versions (7.8.1+).\n"
            "See: https://ngsolve.org/  and  https://github.com/gumyr/build123d/issues/297"
        ) from None


def _match_face_labels(
    b123d_faces: list[tuple[float, float, float, str]],
    ng_geo: "OCCGeometry",
) -> dict[int, str]:
    """Match NGSolve geometry face indices to build123d face labels.

    Uses nearest geometric center matching between build123d faces and
    netgen geometry faces.

    Args:
        b123d_faces: list of (cx, cy, cz, label) tuples from build123d
        ng_geo: netgen OCCGeometry object

    Returns:
        dict mapping netgen face index to label string
    """
    mapping = {}
    for ng_idx, ng_face in enumerate(ng_geo.shape.faces):
        nc = ng_face.center
        best_label = min(
            b123d_faces,
            key=lambda fm: math.sqrt(
                (nc.x - fm[0]) ** 2 + (nc.y - fm[1]) ** 2 + (nc.z - fm[2]) ** 2
            ),
        )[3]
        mapping[ng_idx] = best_label
    return mapping


def to_ngsolve_mesh(
    shape: Shape,
    face_labels: dict[Face, str] | None = None,
    maxh: float = 1.0,
    **mesh_kwargs,
) -> "NGMesh":
    """Convert a build123d Shape to an NGSolve Mesh with named boundaries.

    Transfers the geometry via BREP file interchange (direct shape passing is
    not possible because build123d and netgen use different pybind11 wrappers
    for OpenCASCADE types). Face labels are propagated by matching geometric
    centers between the build123d and netgen representations.

    Requires ``netgen`` and ``ngsolve`` packages to be installed. These are
    **not** hard dependencies of build123d — an ``ImportError`` with
    installation instructions is raised if they are missing.

    Args:
        shape: The build123d Shape to convert (Part, Solid, Compound, etc.).
        face_labels: Optional dictionary mapping build123d Face objects to
            label strings. These labels become NGSolve boundary condition
            names accessible via ``mesh.Boundaries()``. If not provided,
            each face's existing ``.label`` attribute is used; faces without
            a label are assigned ``"default"``.
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
    OCCGeometry = _lazy_import_netgen()
    ngsolve = _lazy_import_ngsolve()

    # Build the (cx, cy, cz, label) list from build123d faces
    b123d_faces = []
    for f in shape.faces():
        c = f.center()
        if face_labels is not None:
            label = face_labels.get(f, "default")
        else:
            label = f.label if f.label else "default"
        b123d_faces.append((c.X, c.Y, c.Z, label))

    if not b123d_faces:
        warnings.warn("Shape has no faces — the resulting mesh will have no boundaries.")

    # Transfer geometry via BREP file interchange
    with tempfile.NamedTemporaryFile(suffix=".brep", delete=True) as tmp:
        export_brep(shape, tmp.name)
        geo = OCCGeometry(tmp.name)

    # Generate the netgen mesh
    ngmesh = geo.GenerateMesh(maxh=maxh, **mesh_kwargs)

    # Propagate face labels by geometric center matching
    if b123d_faces:
        label_map = _match_face_labels(b123d_faces, geo)
        for ng_idx, label in label_map.items():
            ngmesh.SetBCName(ng_idx, label)

    return ngsolve.Mesh(ngmesh)
