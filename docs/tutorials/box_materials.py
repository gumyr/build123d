"""
Materials for the hinged box tutorial

name: box_materials.py
by:   Gumyr
date: November 12th 2026

desc:
    Every code example in the "Materials for the hinged box" tutorial lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. The tutorial carries on from "A hinged box", so this
    script first runs ``hinged_box.py``, which sits beside it, and takes the
    finished parts from it. The rendered pictures on the page are made from
    this script by ``box_materials_shots.py``.

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
import runpy
from pathlib import Path

# Carry on from the end of "A hinged box": run its script and take its parts.
with contextlib.redirect_stdout(io.StringIO()):
    hinged = runpy.run_path(str(Path(__file__).with_name("hinged_box.py")))
Unit, export_gltf = hinged["Unit"], hinged["export_gltf"]
box, lid = hinged["box"], hinged["lid"]
box_leaf, lid_leaf = hinged["box_leaf"], hinged["lid_leaf"]
hinged_box = hinged["hinged_box"]

# [materials]
from bd_materials import finishes, metals, wood

box.material = wood.walnut()
lid.material = wood.walnut()
hinged_box.material = metals.brass()
# [materials]

assert box.material.material.name == "Hardwood_WALNUT"
assert all(
    part.material.material.name == "Brass_C360_HALF_HARD"
    for part in hinged_box.children
    if part not in (box, lid)
)

# [finish]
brushed_brass = metals.brass(finish=finishes.brushed())
box_leaf.material = brushed_brass
lid_leaf.material = brushed_brass
# [finish]

assert box_leaf.material.finish.finish.name == "Brushed"

# [properties]
print(box.material.material)
# [properties]

# [one_property]
print(box.material.material.density)
print(box_leaf.material.finish.finish.name)
# [one_property]

assert box.material.material.density == 640

# [mass]
for part in hinged_box.children:
    print(f"{part.label:18}{part.material.material.name:22}{part.mass():7.1f} g")

print(f"{'whole box':40}{hinged_box.mass():7.1f} g")
print(f"{'':40}{hinged_box.mass(Unit.KG):7.3f} kg")
# [mass]

assert abs(hinged_box.mass() - sum(p.mass() for p in hinged_box.children)) < 1e-6
assert abs(hinged_box.mass() - 2083.5) < 0.1
assert abs(box.mass() - 1243.6) < 0.1 and abs(box_leaf.mass() - 113.1) < 0.1

# [export]
export_gltf(hinged_box, "hinged_box.glb", binary=True)
# [export]

exported = Path("hinged_box.glb")
assert exported.stat().st_size > 100_000
exported.unlink()  # nine megabytes that the docs folder does not need
