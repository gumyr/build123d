"""

Dual Color Export to 3MF Format

name: dual_color_3mf.py
by:   Gumyr
date: August 13th 2023

desc: The 3MF mesh format supports multiple colors which can be used on
      multi-filament 3D printers. This example creates an tile pattern
      with an insert and background in different colors.

license:

    Copyright 2023 Gumyr

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
from build123d import *
from ocp_vscode import *


# Create a simple tile pattern
with BuildSketch() as inset_pattern:
    with BuildLine() as bl:
        Polyline((9, 9), (1, 5), (-0.5, 0))
        offset(amount=1, side=Side.LEFT)
    make_face()
    split(bisect_by=Plane(origin=(0, 0, 0), z_dir=(-1, 1, 0)))
    mirror(about=Plane(origin=(0, 0, 0), z_dir=(-1, 1, 0)))
    mirror(about=Plane.YZ)
    mirror(about=Plane.XZ)

# Create the background field object for the tile
with BuildPart() as outset_builder:
    with BuildSketch():
        Rectangle(20, 20)
        add(inset_pattern.sketch, mode=Mode.SUBTRACT)
    extrude(amount=1)

# Create the inset object for the tile
with BuildPart() as inset_builder:
    add(inset_pattern.sketch)
    extrude(amount=1)

# Assign colors to the tile parts
outset = outset_builder.part
outset.color = Color(0.137, 0.306, 0.439)  # Tealish
inset = inset_builder.part
inset.color = Color(0.980, 0.973, 0.749)  # Goldish

show(inset, outset)

# Export the tile with the units as CM
exporter = Mesher(unit=Unit.CM)
exporter.add_shape([inset, outset])
exporter.write("dual_color.3mf")
