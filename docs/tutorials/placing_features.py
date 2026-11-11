"""
Placing features tutorial

name: placing_features.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "Placing features" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/placing_features``.

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

panel_width, panel_height, thickness = 170, 100, 3
corner_radius = 6
inset, mount_hole_radius = 8, 2.25
fan_spacing, fan_hole_spacing, fan_hole_radius = 80, 50, 2.2
vent_radius, vent_count = 19, 10
vent_length, vent_width, vent_lean = 16, 4, 30
# [setup]

OUTPUT = Path("assets/placing_features")
OUTPUT.mkdir(parents=True, exist_ok=True)


def render_sketch(sketch: Shape, name: str) -> None:
    """Write a sketch, seen from above, as a filled SVG drawing."""
    size = sketch.bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y))
    exporter.add_layer("Sketch", fill_color=0xC4D6E8, line_weight=0.4)
    exporter.add_shape(sketch.faces(), layer="Sketch")
    exporter.write(OUTPUT / f"panel_{name}.svg")


def render_part(part: Shape, name: str) -> None:
    """Write a part, seen from above and to one side, as an SVG line drawing."""
    visible, hidden = part.drawing_view((-90, -130, 110))
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y))
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Hidden", line_color=0x969696, line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(OUTPUT / f"panel_{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    measure = "area" if not first.solids() else "volume"
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(getattr(first, measure) - getattr(second, measure)) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
        and len(first.edges()) == len(second.edges())
    )


# ---------------------------------------------------------------------------
# Step 2: a list of places
# ---------------------------------------------------------------------------

# [places_builder]
with BuildSketch() as layout:
    RectangleRounded(panel_width, panel_height, radius=corner_radius)
    with Locations((-77, -42), (-77, 42), (77, -42), (77, 42)):
        Circle(mount_hole_radius, mode=Mode.SUBTRACT)
# [places_builder]
builder_result = layout.sketch

# [places_algebra]
layout = RectangleRounded(panel_width, panel_height, radius=corner_radius)
layout -= Locations((-77, -42), (-77, 42), (77, -42), (77, 42)) * Circle(
    mount_hole_radius
)
# [places_algebra]

assert same(builder_result, layout)
typed_result = layout
render_sketch(layout, "places")

# ---------------------------------------------------------------------------
# Step 3: a grid of places
# ---------------------------------------------------------------------------

# [grid_builder]
with BuildSketch() as layout:
    RectangleRounded(panel_width, panel_height, radius=corner_radius)
    with GridLocations(panel_width - 2 * inset, panel_height - 2 * inset, 2, 2):
        Circle(mount_hole_radius, mode=Mode.SUBTRACT)
# [grid_builder]
builder_result = layout.sketch

# [grid_algebra]
layout = RectangleRounded(panel_width, panel_height, radius=corner_radius)
layout -= GridLocations(
    panel_width - 2 * inset, panel_height - 2 * inset, 2, 2
) * Circle(mount_hole_radius)
# [grid_algebra]

assert same(builder_result, layout)
assert same(typed_result, layout)  # the same four holes as step 2

# ---------------------------------------------------------------------------
# Step 4: places round a circle
# ---------------------------------------------------------------------------

# [polar_builder]
with BuildSketch() as layout:
    RectangleRounded(panel_width, panel_height, radius=corner_radius)
    with GridLocations(panel_width - 2 * inset, panel_height - 2 * inset, 2, 2):
        Circle(mount_hole_radius, mode=Mode.SUBTRACT)
    with PolarLocations(vent_radius, vent_count):
        SlotOverall(vent_length, vent_width, mode=Mode.SUBTRACT)
# [polar_builder]
builder_result = layout.sketch

# [polar_algebra]
layout = RectangleRounded(panel_width, panel_height, radius=corner_radius)
layout -= GridLocations(
    panel_width - 2 * inset, panel_height - 2 * inset, 2, 2
) * Circle(mount_hole_radius)
layout -= PolarLocations(vent_radius, vent_count) * SlotOverall(vent_length, vent_width)
# [polar_algebra]

assert same(builder_result, layout)
render_sketch(layout, "polar")

# ---------------------------------------------------------------------------
# Step 5: a place has a direction
# ---------------------------------------------------------------------------

# [lean_builder]
with BuildSketch() as layout:
    RectangleRounded(panel_width, panel_height, radius=corner_radius)
    with GridLocations(panel_width - 2 * inset, panel_height - 2 * inset, 2, 2):
        Circle(mount_hole_radius, mode=Mode.SUBTRACT)
    with PolarLocations(vent_radius, vent_count):
        SlotOverall(vent_length, vent_width, rotation=vent_lean, mode=Mode.SUBTRACT)
# [lean_builder]
builder_result = layout.sketch

# [lean_algebra]
layout = RectangleRounded(panel_width, panel_height, radius=corner_radius)
layout -= GridLocations(
    panel_width - 2 * inset, panel_height - 2 * inset, 2, 2
) * Circle(mount_hole_radius)
layout -= PolarLocations(vent_radius, vent_count) * SlotOverall(
    vent_length, vent_width, rotation=vent_lean
)
# [lean_algebra]

assert same(builder_result, layout)
render_sketch(layout, "lean")

# ---------------------------------------------------------------------------
# Step 6: places within places
# ---------------------------------------------------------------------------

# [nested_builder]
with BuildSketch() as layout:
    RectangleRounded(panel_width, panel_height, radius=corner_radius)
    with GridLocations(panel_width - 2 * inset, panel_height - 2 * inset, 2, 2):
        Circle(mount_hole_radius, mode=Mode.SUBTRACT)
    with Locations((-fan_spacing / 2, 0), (fan_spacing / 2, 0)):
        with PolarLocations(vent_radius, vent_count):
            SlotOverall(vent_length, vent_width, rotation=vent_lean, mode=Mode.SUBTRACT)
        with GridLocations(fan_hole_spacing, fan_hole_spacing, 2, 2):
            Circle(fan_hole_radius, mode=Mode.SUBTRACT)
# [nested_builder]
builder_result = layout.sketch

# [nested_algebra]
layout = RectangleRounded(panel_width, panel_height, radius=corner_radius)
layout -= GridLocations(
    panel_width - 2 * inset, panel_height - 2 * inset, 2, 2
) * Circle(mount_hole_radius)

fans = Locations((-fan_spacing / 2, 0), (fan_spacing / 2, 0))
layout -= (
    fans
    * PolarLocations(vent_radius, vent_count)
    * SlotOverall(vent_length, vent_width, rotation=vent_lean)
)
layout -= (
    fans
    * GridLocations(fan_hole_spacing, fan_hole_spacing, 2, 2)
    * Circle(fan_hole_radius)
)
# [nested_algebra]

assert same(builder_result, layout)
render_sketch(layout, "nested")

# ---------------------------------------------------------------------------
# Step 7: extrude it
# ---------------------------------------------------------------------------

# [extrude_builder]
with BuildPart() as panel:
    with BuildSketch() as layout:
        RectangleRounded(panel_width, panel_height, radius=corner_radius)
        with GridLocations(panel_width - 2 * inset, panel_height - 2 * inset, 2, 2):
            Circle(mount_hole_radius, mode=Mode.SUBTRACT)
        with Locations((-fan_spacing / 2, 0), (fan_spacing / 2, 0)):
            with PolarLocations(vent_radius, vent_count):
                SlotOverall(
                    vent_length, vent_width, rotation=vent_lean, mode=Mode.SUBTRACT
                )
            with GridLocations(fan_hole_spacing, fan_hole_spacing, 2, 2):
                Circle(fan_hole_radius, mode=Mode.SUBTRACT)
    extrude(amount=thickness)
# [extrude_builder]
builder_result = panel.part

# [extrude_algebra]
layout = RectangleRounded(panel_width, panel_height, radius=corner_radius)
layout -= GridLocations(
    panel_width - 2 * inset, panel_height - 2 * inset, 2, 2
) * Circle(mount_hole_radius)

fans = Locations((-fan_spacing / 2, 0), (fan_spacing / 2, 0))
layout -= (
    fans
    * PolarLocations(vent_radius, vent_count)
    * SlotOverall(vent_length, vent_width, rotation=vent_lean)
)
layout -= (
    fans
    * GridLocations(fan_hole_spacing, fan_hole_spacing, 2, 2)
    * Circle(fan_hole_radius)
)

panel = extrude(layout, amount=thickness)
# [extrude_algebra]

assert same(builder_result, panel)
assert len(panel.solids()) == 1
render_part(panel, "extrude")

# ---------------------------------------------------------------------------
# Step 8: the sketch has a place too
# ---------------------------------------------------------------------------

# [plane_builder]
with BuildPart() as panel:
    with BuildSketch(Plane.XZ) as layout:
        RectangleRounded(panel_width, panel_height, radius=corner_radius)
        with GridLocations(panel_width - 2 * inset, panel_height - 2 * inset, 2, 2):
            Circle(mount_hole_radius, mode=Mode.SUBTRACT)
        with Locations((-fan_spacing / 2, 0), (fan_spacing / 2, 0)):
            with PolarLocations(vent_radius, vent_count):
                SlotOverall(
                    vent_length, vent_width, rotation=vent_lean, mode=Mode.SUBTRACT
                )
            with GridLocations(fan_hole_spacing, fan_hole_spacing, 2, 2):
                Circle(fan_hole_radius, mode=Mode.SUBTRACT)
    extrude(amount=thickness)
# [plane_builder]
builder_result = panel.part

# [plane_algebra]
layout = RectangleRounded(panel_width, panel_height, radius=corner_radius)
layout -= GridLocations(
    panel_width - 2 * inset, panel_height - 2 * inset, 2, 2
) * Circle(mount_hole_radius)

fans = Locations((-fan_spacing / 2, 0), (fan_spacing / 2, 0))
layout -= (
    fans
    * PolarLocations(vent_radius, vent_count)
    * SlotOverall(vent_length, vent_width, rotation=vent_lean)
)
layout -= (
    fans
    * GridLocations(fan_hole_spacing, fan_hole_spacing, 2, 2)
    * Circle(fan_hole_radius)
)

panel = extrude(Plane.XZ * layout, amount=thickness)
# [plane_algebra]

assert same(builder_result, panel)
assert len(panel.solids()) == 1
assert abs(panel.bounding_box().size.Z - panel_height) < 1e-6
render_part(panel, "plane")
