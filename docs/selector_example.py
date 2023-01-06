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

# SVG Export options
svg_opts = {"pixel_scale": 50, "show_axes": False, "show_hidden": True}

with BuildPart() as example:
    Cylinder(radius=10, height=3)
    with BuildSketch(example.faces().sort_by(Axis.Z)[-1]):
        RegularPolygon(radius=7, side_count=6)
        Circle(radius=4, mode=Mode.SUBTRACT)
    Extrude(amount=-2, mode=Mode.SUBTRACT)
    example.part.export_svg(
        "selector_before.svg", (-100, 100, 150), (0, 0, 1), svg_opts=svg_opts
    )
    Fillet(
        example.edges()
        .filter_by(GeomType.CIRCLE)
        .sort_by(SortBy.RADIUS)[-2:]
        .sort_by(Axis.Z)[-1],
        radius=1,
    )
    example.part.export_svg(
        "selector_after.svg", (-100, 100, 150), (0, 0, 1), svg_opts=svg_opts
    )

if "show_object" in locals():
    show_object(example.part.wrapped, name="part")
