"""

name: twist_extrude.py
by:   KilowattSynthesis
date: 2026-06-03

desc:

    This example demonstrates using Solid.extrude_linear_with_rotation to
    create a 'twisted prism' - a hexagonal cross section extruded upward
    while simultaneously rotating 72 degrees (1/5 of a full turn).

license:

    Copyright 2026 KilowattSynthesis

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

from ocp_vscode import show

from build123d import *

hex_sketch = RegularPolygon(radius=1, side_count=6)

twist_extrude = Solid.extrude_linear_with_rotation(
    section=hex_sketch.face(),
    center=(0, 0),
    normal=(0, 0, 5),  # extrusion direction and distance
    angle=360 / 5,  # 72 degrees of rotation over the extrusion height
)

show(twist_extrude)
