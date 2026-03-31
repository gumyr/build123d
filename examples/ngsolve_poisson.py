"""
build123d -> NGSolve: Poisson solve with named boundary conditions.

Demonstrates the to_ngsolve_mesh() function which transfers build123d geometry
to NGSolve for finite element analysis, automatically propagating face labels
as mesh boundary condition names.

Requires: pip install ngsolve netgen-occt netgen-occt-devel
Requires: Python 3.12+ (for matching OCCT versions between cadquery-ocp and netgen-occt)

See: https://github.com/gumyr/build123d/issues/297
"""

import sys

import build123d as bd
from build123d import to_ngsolve_mesh

try:
    import ngsolve as ngs
except ImportError:
    print("ngsolve is not installed — skipping example.")
    print("Install with: pip install ngsolve netgen-occt netgen-occt-devel")
    sys.exit(0)

# 1. Build geometry in build123d — a hollow cylinder
part = bd.Cylinder(10, 20) - bd.Cylinder(5, 20)

# 2. Label faces for boundary conditions by geometric position
labels = {}
for f in part.faces():
    if abs(f.center().Z) > 1:
        labels[f] = "ends"
    else:
        labels[f] = "walls"

# 3. Convert to NGSolve mesh (handles BREP transfer + face matching in one call)
mesh = to_ngsolve_mesh(part, face_labels=labels, maxh=2)
print(f"Boundaries:  {mesh.GetBoundaries()}")

# 4. Solve Poisson equation: -Laplacian(u) = 1 with u=0 on "ends"
fes = ngs.H1(mesh, order=2, dirichlet="ends")
u, v = fes.TnT()
a = ngs.BilinearForm(ngs.grad(u) * ngs.grad(v) * ngs.dx).Assemble()
f = ngs.LinearForm(1 * v * ngs.dx).Assemble()
gfu = ngs.GridFunction(fes)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs()) * f.vec
print(f"DOFs:        {fes.ndof} ({sum(fes.FreeDofs())} free)")
print(f"Solution:    {min(gfu.vec):.4f} .. {max(gfu.vec):.4f}")
