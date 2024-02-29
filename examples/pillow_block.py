"""

name: pillow_block.py
by:   Gumyr
date: July 14th 2022

desc:

    This example demonstrates placing holes in a part in a rectangular
    array.

license:

    Copyright 2022 Gumyr

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
from ocp_vscode import show

height, width, thickness, padding = 60, 80, 10, 12
screw_shaft_radius, screw_head_radius, screw_head_height = 1.5, 3, 3
bearing_axle_radius, bearing_radius, bearing_thickness = 4, 11, 7

# Build pillow block as an extruded sketch with counter bore holes
with BuildPart() as pillow_block:
    with BuildSketch() as plan:
        Rectangle(width, height)
        fillet(plan.vertices(), radius=5)
    extrude(amount=thickness)
    # with Locations((0, 0, thickness)):
    with Locations(pillow_block.faces().sort_by(Axis.Z)[-1]):
        CounterBoreHole(bearing_axle_radius, bearing_radius, bearing_thickness)
        with GridLocations(width - 2 * padding, height - 2 * padding, 2, 2):
            CounterBoreHole(screw_shaft_radius, screw_head_radius, screw_head_height)

# Render the part
show(pillow_block)
