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
from build123d import *
from cadquery import exporters

svg_opts = {
    "width": 500,
    "height": 300,
    "marginLeft": 60,
    "marginTop": 30,
    "showAxes": False,
    "projectionDir": (1, 1, 0.7),
    "showHidden": False,
}
with BuildPart() as example:
    Cylinder(radius=10, height=3)
    with Workplanes(example.faces() >> Axis.Z):
        with BuildSketch():
            RegularPolygon(radius=7, side_count=6)
        Extrude(amount=-2, mode=Mode.SUBTRACT)
        with BuildSketch():
            Circle(radius=4)
        Extrude(amount=-2, mode=Mode.ADD)
        exporters.export(example.part, "selector_before.svg", opt=svg_opts)
    Fillet((example.edges() % GeomType.CIRCLE > SortBy.RADIUS)[-2:] >> Axis.Z, radius=1)
    exporters.export(example.part, "selector_after.svg", opt=svg_opts)

if "show_object" in locals():
    show_object(example.part, name="part")
