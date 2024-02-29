"""

name: loft.py
by:   Gumyr
date: July 15th 2022

desc:

    This example demonstrates lofting a set of sketches, selecting
    the top and bottom by type, and shelling.

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

# [Code]

from math import pi, sin
from build123d import *
from ocp_vscode import show

with BuildPart() as art:
    slice_count = 10
    for i in range(slice_count + 1):
        with BuildSketch(Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))) as slice:
            Circle(10 * sin(i * pi / slice_count) + 5)
    loft()
    top_bottom = art.faces().filter_by(GeomType.PLANE)
    offset(openings=top_bottom, amount=0.5)

assert abs(art.part.volume - 1306.3405290344635) < 1e-3

show(art, names=["art"])
# [End]
