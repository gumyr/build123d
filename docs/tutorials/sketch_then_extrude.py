"""
Sketch, then extrude tutorial

name: sketch_then_extrude.py
by:   Gumyr
date: November 10th 2026

desc:
    Every code example in the "Sketch, then extrude" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/sketch_then_extrude``.

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

from pathlib import Path

from build123d.topology import Shape

# [setup]
from build123d import *

length, width, thickness = 80, 50, 4
corner_radius = 8
slot_length, slot_width, slot_spacing = 24, 6, 50
rim_width, rim_height = 3, 10
# [setup]

OUTPUT = Path("assets/sketch_then_extrude")
OUTPUT.mkdir(parents=True, exist_ok=True)


def render_sketch(sketch: Shape, name: str) -> None:
    """Write a sketch, seen from above, as a filled SVG drawing."""
    size = sketch.bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y))
    exporter.add_layer("Sketch", fill_color=0xC4D6E8, line_weight=0.4)
    exporter.add_shape(sketch.faces(), layer="Sketch")
    exporter.write(OUTPUT / f"plate_{name}.svg")


def render_part(part: Shape, name: str) -> None:
    """Write a part, seen from above and to one side, as an SVG line drawing."""
    visible, hidden = part.drawing_view((-90, -130, 110))
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y))
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Hidden", line_color=0x969696, line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(OUTPUT / f"plate_{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    measure = "area" if not first.solids() else "volume"
    return (
        abs(getattr(first, measure) - getattr(second, measure)) < 1e-6
        and (first.bounding_box().size - second.bounding_box().size).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 2: the outline
# ---------------------------------------------------------------------------

# [outline_builder]
with BuildSketch() as outline:
    RectangleRounded(length, width, radius=corner_radius)
# [outline_builder]
builder_result = outline.sketch

# [outline_algebra]
outline = RectangleRounded(length, width, radius=corner_radius)
# [outline_algebra]

assert same(builder_result, outline)
render_sketch(outline, "outline")

# ---------------------------------------------------------------------------
# Step 3: give it depth
# ---------------------------------------------------------------------------

# [extrude_builder]
with BuildPart() as plate:
    with BuildSketch() as outline:
        RectangleRounded(length, width, radius=corner_radius)
    extrude(amount=thickness)
# [extrude_builder]
builder_result = plate.part

# [extrude_algebra]
outline = RectangleRounded(length, width, radius=corner_radius)
plate = extrude(outline, amount=thickness)
# [extrude_algebra]

assert same(builder_result, plate)
render_part(plate, "extrude")

# ---------------------------------------------------------------------------
# Step 4: shape the sketch, not the solid
# ---------------------------------------------------------------------------

# [hexagon_builder]
with BuildPart() as plate:
    with BuildSketch() as outline:
        RectangleRounded(length, width, radius=corner_radius)
        RegularPolygon(radius=7, side_count=6, mode=Mode.SUBTRACT)
    extrude(amount=thickness)
# [hexagon_builder]
builder_result = plate.part
render_sketch(outline.sketch, "hexagon_sketch")

# [hexagon_algebra]
outline = RectangleRounded(length, width, radius=corner_radius)
outline -= RegularPolygon(radius=7, side_count=6)
plate = extrude(outline, amount=thickness)
# [hexagon_algebra]

assert same(builder_result, plate)
render_part(plate, "hexagon")

# ---------------------------------------------------------------------------
# Step 5: the same feature twice
# ---------------------------------------------------------------------------

# [slots_builder]
with BuildPart() as plate:
    with BuildSketch() as outline:
        RectangleRounded(length, width, radius=corner_radius)
        RegularPolygon(radius=7, side_count=6, mode=Mode.SUBTRACT)
        with Locations((-slot_spacing / 2, 0), (slot_spacing / 2, 0)):
            SlotOverall(slot_length, slot_width, rotation=90, mode=Mode.SUBTRACT)
    extrude(amount=thickness)
# [slots_builder]
builder_result = plate.part
render_sketch(outline.sketch, "slots_sketch")

# [slots_algebra]
outline = RectangleRounded(length, width, radius=corner_radius)
outline -= RegularPolygon(radius=7, side_count=6)
for x in (-slot_spacing / 2, slot_spacing / 2):
    outline -= Pos(x, 0) * SlotOverall(slot_length, slot_width, rotation=90)
plate = extrude(outline, amount=thickness)
# [slots_algebra]

assert same(builder_result, plate)
render_part(plate, "slots")

# ---------------------------------------------------------------------------
# Step 6: a second sketch for the rim
# ---------------------------------------------------------------------------

# [rim_builder]
with BuildPart() as plate:
    with BuildSketch() as outline:
        RectangleRounded(length, width, radius=corner_radius)
        RegularPolygon(radius=7, side_count=6, mode=Mode.SUBTRACT)
        with Locations((-slot_spacing / 2, 0), (slot_spacing / 2, 0)):
            SlotOverall(slot_length, slot_width, rotation=90, mode=Mode.SUBTRACT)
    extrude(amount=thickness)

    with BuildSketch() as rim:
        RectangleRounded(length, width, radius=corner_radius)
        offset(amount=-rim_width, mode=Mode.SUBTRACT)
    extrude(amount=rim_height)
# [rim_builder]
builder_result = plate.part
render_sketch(rim.sketch, "rim_sketch")

# [rim_algebra]
outline = RectangleRounded(length, width, radius=corner_radius)
outline -= RegularPolygon(radius=7, side_count=6)
for x in (-slot_spacing / 2, slot_spacing / 2):
    outline -= Pos(x, 0) * SlotOverall(slot_length, slot_width, rotation=90)
plate = extrude(outline, amount=thickness)

blank = RectangleRounded(length, width, radius=corner_radius)
rim = blank - offset(blank, amount=-rim_width)
plate += extrude(rim, amount=rim_height)
# [rim_algebra]

assert same(builder_result, plate)
render_part(plate, "rim")
