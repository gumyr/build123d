"""

name: selector_example.py
by:   Gumyr
date: September 28th 2022

desc:

    This illustrates use of several selectors.

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
from build123d import *
from ocp_vscode import *

with BuildPart() as example:
    Cylinder(radius=10, height=3)
    with BuildSketch(example.faces().sort_by(Axis.Z)[-1]):
        RegularPolygon(radius=7, side_count=6)
        Circle(radius=4, mode=Mode.SUBTRACT)
    extrude(amount=-2, mode=Mode.SUBTRACT)
    visible, hidden = example.part.project_to_viewport((-100, 100, 100))
    exporter = ExportSVG(scale=6)
    exporter.add_layer("Visible")
    exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write("assets/selector_before.svg")

    fillet(
        example.edges()
        .filter_by(GeomType.CIRCLE)
        .sort_by(SortBy.RADIUS)[-2:]
        .sort_by(Axis.Z)[-1],
        radius=1,
    )

visible, hidden = example.part.project_to_viewport((-100, 100, 100))
exporter = ExportSVG(scale=6)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
exporter.add_shape(visible, layer="Visible")
exporter.add_shape(hidden, layer="Hidden")
exporter.write("assets/selector_after.svg")

show(example)
# [End]
