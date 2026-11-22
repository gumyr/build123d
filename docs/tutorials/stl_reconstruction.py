"""
Rebuilding a part from an STL tutorial

name: stl_reconstruction.py
by:   Gumyr
date: November 12th 2026

desc:
    Every code example in the "Rebuilding a part from an STL" tutorial lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. The tutorial starts from an STL of the bracket of
    "Designing a Part", so this script first runs ``tutorial_design.py``,
    which sits beside it, and takes the bracket from it. The rendered
    pictures on the page are made from this script by
    ``stl_reconstruction_shots.py``. The files it writes on the way are
    removed again at the end.

license:

    Copyright 2026 Gumyr

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

import contextlib
import io
import re
import runpy
import types
from pathlib import Path

# Carry on from the end of "Designing a Part": run its script and take the
# bracket from it.
with contextlib.redirect_stdout(io.StringIO()):
    design = runpy.run_path(str(Path(__file__).with_name("tutorial_design.py")))
globals().update({k: v for k, v in design.items() if not k.startswith("_")})
DESIGNED = {
    name: design[name]
    for name in (
        "length width height thickness bend_radius fillet_radius "
        "hole_diameter slot_length"
    ).split()
}

# In builder mode the tutorial's ``bracket`` is the BuildPart, in algebra mode
# it is the part itself. Both of the one-line versions of step 1 are run.
bracket = types.SimpleNamespace(part=design["builder_result"])
# [stl_builder]
export_stl(bracket.part, "bracket.stl")
# [stl_builder]

bracket = design["bracket"]
# [stl_algebra]
export_stl(bracket, "bracket.stl")
# [stl_algebra]

# ---------------------------------------------------------------------------
# Step 2: read the mesh
# ---------------------------------------------------------------------------
# [mesh]
from build123d import *

mesh = Mesher().read("bracket.stl")[0]

print(len(mesh.faces()), "triangles")
print(mesh.bounding_box().size)
# [mesh]
assert len(mesh.faces()) > 1000
assert all(face.geom_type == GeomType.PLANE for face in mesh.faces()[:50])

# ---------------------------------------------------------------------------
# Step 3: cut it down by symmetry
# ---------------------------------------------------------------------------
# [quarter]
quarter = split(mesh, Plane.YZ)
quarter = split(quarter, Plane.XY)

print(len(quarter.faces()), "triangles")
# [quarter]
assert len(quarter.faces()) < len(mesh.faces()) / 3

# ---------------------------------------------------------------------------
# Step 4: keep the working piece
# ---------------------------------------------------------------------------
# [cache]
export_brep(quarter, "bracket_quarter.brep")
# [cache]

# [reload]
quarter = import_brep("bracket_quarter.brep")
# [reload]

# ---------------------------------------------------------------------------
# Step 5: detect the primitives
# ---------------------------------------------------------------------------
# [detect]
primitives, leftovers, code_lines = detect_primitives(quarter)

print(len(primitives), "primitives,", len(leftovers), "triangles left over")
# [detect]
kinds = sorted(face.geom_type.name for face in primitives)
assert kinds == ["CYLINDER"] * 2 + ["PLANE"] * 5, kinds
assert 0 < len(leftovers) < len(quarter.faces()) / 2

# ---------------------------------------------------------------------------
# Step 6: read the report
# ---------------------------------------------------------------------------
# [report]
print(*code_lines, sep="\n")
# [report]
report = "\n".join(code_lines)
for clue in (
    "Plane.XY.offset(12.5)",
    "Plane.YZ.offset(22)",
    "Plane.YZ.offset(25)",
    "Plane.ZX.offset(3)",
    "Circle(2).edge()",
):
    assert clue in report, clue
# The fitted radius of the hole differs in its last digits between platforms
hole_radius_found = float(re.search(r"Circle\((2\.[45]\d*)\)", report).group(1))
assert abs(hole_radius_found - 2.5) < 0.05, hole_radius_found

# ---------------------------------------------------------------------------
# Step 7: measure what was left over
# ---------------------------------------------------------------------------
# [leftovers]
bend = leftovers.filter_by_position(Axis.X, 20, 25).filter_by_position(Axis.Y, 0, 5)
print("bend:", Compound(bend).bounding_box().size)

slot = leftovers.filter_by_position(Axis.X, 5, 15).filter_by_position(Axis.Z, 0.1, 5)
print("slot:", Compound(slot).bounding_box().max)
# [leftovers]
bend_size = Compound(bend).bounding_box().size
assert abs(bend_size.X - 5) < 0.01 and abs(bend_size.Y - 5) < 0.01
slot_reach = Compound(slot).bounding_box().max
assert abs(slot_reach.X - 10) < 0.01 and abs(slot_reach.Z - 2.5) < 0.01, slot_reach

# ---------------------------------------------------------------------------
# Step 8: the dimensions
# ---------------------------------------------------------------------------
# [dimensions]
length, width, height = 50, 25, 25
thickness = 3
bend_radius, fillet_radius = 5, 2
hole_diameter, slot_length = 5, 20
# [dimensions]
RECOVERED = dict(
    length=length,
    width=width,
    height=height,
    thickness=thickness,
    bend_radius=bend_radius,
    fillet_radius=fillet_radius,
    hole_diameter=hole_diameter,
    slot_length=slot_length,
)
assert RECOVERED == DESIGNED

# ---------------------------------------------------------------------------
# Step 9: check the rebuilt part against the mesh
# ---------------------------------------------------------------------------
rebuilt = design["bracket"]
# [compare]
for name, shape in (("mesh", mesh), ("rebuilt", rebuilt)):
    size = shape.bounding_box().size
    print(
        f"{name:8}{shape.volume:8.1f} mm3   {size.X:.1f} x {size.Y:.1f} x {size.Z:.1f}"
    )
# [compare]
assert abs(mesh.volume - rebuilt.volume) / rebuilt.volume < 0.001
assert (mesh.bounding_box().size - rebuilt.bounding_box().size).length < 1e-6

# The files this script wrote are not wanted in the docs folder.
for written in ("bracket.stl", "bracket_quarter.brep"):
    Path(written).unlink()
