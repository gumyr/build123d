"""
Materials how-to examples

name: materials.py
by:   Gumyr
date: November 12th 2026

desc:
    The code examples of the Materials how-to guide, between pairs of
    ``# [name]`` markers that the page includes with ``literalinclude``.

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

# [assign]
from build123d import *
from bd_materials import finishes, metals, plastics, wood

plate = Box(100, 60, 5)
plate.material = metals.aluminum()
# [assign]

# [by_name]
plate.material = "Titanium"
print(plate.material.material.name)
# [by_name]
assert plate.material.material.name == "Titanium_GR5_ANNEALED"
plate.material = metals.aluminum()

# [finish]
plate.material = metals.aluminum(finish=finishes.brushed())
print(plate.material.finish.finish.name)
# [finish]
plate.material = metals.aluminum()

# [properties]
print(plate.material.material)
# [properties]

# [ranges]
stiffness = plate.material.material.modulus_of_elasticity
print(stiffness)
print(stiffness.min, stiffness.max)
print(stiffness.value_at(0.5))
# [ranges]
assert (stiffness.min, stiffness.max, stiffness.value_at(0.5)) == (66, 70, 68.0)

# [units]
from bd_materials.core import PROPERTY_UNITS

print(PROPERTY_UNITS["density"])
print(PROPERTY_UNITS["modulus_of_elasticity"])
# [units]
assert PROPERTY_UNITS["density"] == "kg/m³"

# [mass]
print(plate.volume)
print(plate.mass())
print(plate.mass(Unit.KG))
# [mass]
assert abs(plate.mass() - 81.0) < 1e-6 and abs(plate.mass(Unit.KG) - 0.081) < 1e-9

# [mass_inches]
print(f"{plate.mass(Unit.LB, Unit.IN):.1f}")
# [mass_inches]
assert abs(plate.mass(Unit.LB, Unit.IN) - 2926.31) < 0.01

# [no_material]
try:
    Box(10, 10, 10).mass()
except ValueError as error:
    print(error)
# [no_material]

# [assembly]
knob = Pos(0, 0, 10) * Cylinder(10, 15)
knob.material = wood.oak()
bolt = Pos(30, 0, 5) * Cylinder(3, 20)

panel = Compound(label="panel", children=[plate, knob, bolt])
panel.material = metals.stainless()

print(bolt.material.material.name)
print(f"{panel.mass():.1f}")
# [assembly]
assert bolt.material.material.name.startswith("Stainless")
assert abs(panel.mass() - (plate.mass() + knob.mass() + bolt.mass())) < 1e-6

# [pbr]
print(plate.material.pbr)
print(plate.color)
# [pbr]

# [custom]
blend = plastics.custom_plastic("recycled blend", density=1100)
cube = Box(10, 10, 10)
cube.material = blend
print(f"{cube.mass():.1f}")
# [custom]
assert abs(cube.mass() - 1.1) < 1e-6
