"""
Builder mode and algebra mode documentation examples

name: modes.py
by:   Gumyr
date: November 16th 2026

desc:
    The one part of the "Builder mode and algebra mode" page of Getting
    Started, written in both modes between pairs of ``# [name]`` markers
    that the page includes with ``literalinclude``. The two are checked
    against each other, and the script draws the page's picture, written to
    ``assets``. Run it from its own directory.

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

# pylint: disable=redefined-outer-name, wildcard-import, unused-wildcard-import

from pathlib import Path

from build123d import *

# [builder]
with BuildPart() as plate:
    with BuildSketch():
        RectangleRounded(80, 60, 8)
        Circle(12, mode=Mode.SUBTRACT)
        with GridLocations(60, 40, 2, 2):
            Circle(3, mode=Mode.SUBTRACT)
    extrude(amount=10)
# [builder]

builder_plate = plate.part

# [algebra]
outline = RectangleRounded(80, 60, 8)
outline -= Circle(12)
corners = GridLocations(60, 40, 2, 2)
outline -= corners * Circle(3)
plate = extrude(outline, amount=10)
# [algebra]

# the two are the same part
assert isinstance(builder_plate, Part) and isinstance(plate, Part)
assert abs(builder_plate.volume - plate.volume) < 1e-6
assert abs(builder_plate.area - plate.area) < 1e-6
assert (builder_plate.bounding_box().size - plate.bounding_box().size).length < 1e-6
assert len(plate.faces().filter_by(GeomType.CYLINDER)) == 9  # 5 holes, 4 corners

# [mixed]
with BuildPart() as mixed:
    with BuildSketch():
        RectangleRounded(80, 60, 8)
    extrude(amount=10)

finished = mixed.part - Cylinder(12, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
# [mixed]

assert abs(finished.volume - (builder_plate.volume + 4 * Circle(3).area * 10)) < 1e-6

# the picture
output = Path("assets")
output.mkdir(parents=True, exist_ok=True)
look_at = plate.center()
visible, hidden = plate.drawing_view(
    look_at + Vector(1, -1, 0.9) * 300, look_at=look_at
)
extent = max(*Compound(children=visible + hidden).bounding_box().size)
drawing = ExportSVG(scale=100 / extent, margin=5)
drawing.add_layer("Visible")
drawing.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
drawing.add_shape(visible, layer="Visible")
drawing.add_shape(hidden, layer="Hidden")
drawing.write(output / "modes_plate.svg")
