"""
A sheet metal enclosure tutorial

name: sheet_metal_enclosure.py
by:   Gumyr
date: November 12th 2026

desc:
    Every code example in the "A sheet metal enclosure" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/sheet_metal_enclosure``.

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

length, width, wall_height = 120, 80, 25
thickness, bend_radius = 1.5, 2
corner_gap, relief_radius = 3.5, 3
hole_radius, hole_inset = 2, 15
slot_length, slot_width, slot_height = 20, 8, 10
hem_width, hem_opening = 6, 1.5
# [setup]

OUTPUT = Path("assets/sheet_metal_enclosure")
OUTPUT.mkdir(parents=True, exist_ok=True)


def render(shape: Shape, name: str, viewpoint=(-90, -150, 210)) -> None:
    """Write a sheet or a part as an SVG line drawing, seen from ``viewpoint``."""
    look_at = shape.bounding_box().center()
    visible, hidden = shape.drawing_view(Vector(viewpoint) + look_at, look_at=look_at)
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0xB0B0B0, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_shape(hidden, layer="Hidden")
    exporter.add_shape(visible, layer="Visible")
    exporter.write(OUTPUT / f"enclosure_{name}.svg")


def render_flat(flat: Shape, name: str) -> None:
    """Write a flat pattern, seen from above, fold lines included."""
    size = flat.bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_shape(flat.edges(), layer="Visible")
    exporter.write(OUTPUT / f"enclosure_{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same sheet?"""
    return (
        abs(first.area - second.area) < 1e-6
        and (first.bounding_box().size - second.bounding_box().size).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 2: the blank
# ---------------------------------------------------------------------------
# [blank_builder]
with BuildPart() as enclosure_part:
    with BuildSheet(thickness=thickness, bend_radius=bend_radius) as enclosure:
        with BuildSketch() as blank:
            Rectangle(length, width)
# [blank_builder]
builder_result = enclosure.sheet

# [blank_algebra]
parameters = SheetMetalParameters(thickness=thickness, bend_radius=bend_radius)
sheet = Shell(Rectangle(length, width))
# [blank_algebra]

assert same(builder_result, sheet) and len(sheet.rims()) == 4
render(sheet, "blank")

# ---------------------------------------------------------------------------
# Step 3: fold the walls
# ---------------------------------------------------------------------------
# [walls_builder]
with BuildPart() as enclosure_part:
    with BuildSheet(thickness=thickness, bend_radius=bend_radius) as enclosure:
        with BuildSketch() as blank:
            Rectangle(length, width)
        flange(enclosure.rims(), length=wall_height, gaps=corner_gap)
# [walls_builder]
builder_result = enclosure.sheet

# [walls_algebra]
parameters = SheetMetalParameters(thickness=thickness, bend_radius=bend_radius)
sheet = Shell(Rectangle(length, width))
sheet = flange(
    sheet.rims(), length=wall_height, gaps=corner_gap, sheet_parameters=parameters
)
# [walls_algebra]

assert same(builder_result, sheet)
render(sheet, "walls")

# ---------------------------------------------------------------------------
# Step 4: relieve the corners
# ---------------------------------------------------------------------------
# [relief_builder]
with BuildPart() as enclosure_part:
    with BuildSheet(thickness=thickness, bend_radius=bend_radius) as enclosure:
        with BuildSketch() as blank:
            Rectangle(length, width)
        flange(enclosure.rims(), length=wall_height, gaps=corner_gap)
        base = enclosure.flats().sort_by(Axis.Z)[0]
        corners = base.vertices().filter_by(Convexity.CONVEX)
        corner_relief(corners, ReliefType.ROUND, radius=relief_radius)
# [relief_builder]
builder_result = enclosure.sheet

# [relief_algebra]
parameters = SheetMetalParameters(thickness=thickness, bend_radius=bend_radius)
sheet = Shell(Rectangle(length, width))
sheet = flange(
    sheet.rims(), length=wall_height, gaps=corner_gap, sheet_parameters=parameters
)
base = sheet.flats().sort_by(Axis.Z)[0]
corners = base.vertices().filter_by(Convexity.CONVEX)
sheet = corner_relief(
    corners, ReliefType.ROUND, radius=relief_radius, sheet_parameters=parameters
)
# [relief_algebra]

assert same(builder_result, sheet)
render(sheet, "relief")

# ---------------------------------------------------------------------------
# Step 5: holes and a slot
# ---------------------------------------------------------------------------
# [cuts_builder]
with BuildPart() as enclosure_part:
    with BuildSheet(thickness=thickness, bend_radius=bend_radius) as enclosure:
        with BuildSketch() as blank:
            Rectangle(length, width)
        flange(enclosure.rims(), length=wall_height, gaps=corner_gap)
        base = enclosure.flats().sort_by(Axis.Z)[0]
        corners = base.vertices().filter_by(Convexity.CONVEX)
        corner_relief(corners, ReliefType.ROUND, radius=relief_radius)
        with GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2):
            Circle(hole_radius, mode=Mode.SUBTRACT)
        with Locations((0, width / 2)):
            Box(slot_length, slot_width, 2 * slot_height, mode=Mode.SUBTRACT)
# [cuts_builder]
builder_result = enclosure.sheet

# [cuts_algebra]
parameters = SheetMetalParameters(thickness=thickness, bend_radius=bend_radius)
sheet = Shell(Rectangle(length, width))
sheet = flange(
    sheet.rims(), length=wall_height, gaps=corner_gap, sheet_parameters=parameters
)
base = sheet.flats().sort_by(Axis.Z)[0]
corners = base.vertices().filter_by(Convexity.CONVEX)
sheet = corner_relief(
    corners, ReliefType.ROUND, radius=relief_radius, sheet_parameters=parameters
)
hole_places = GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2)
sheet -= hole_places * Circle(hole_radius)
sheet -= Pos(0, width / 2) * Box(slot_length, slot_width, 2 * slot_height)
# [cuts_algebra]

assert same(builder_result, sheet)
render(sheet, "cuts")

# ---------------------------------------------------------------------------
# Step 6: hem the rims
# ---------------------------------------------------------------------------
# [hem_builder]
with BuildPart() as enclosure_part:
    with BuildSheet(thickness=thickness, bend_radius=bend_radius) as enclosure:
        with BuildSketch() as blank:
            Rectangle(length, width)
        flange(enclosure.rims(), length=wall_height, gaps=corner_gap)
        base = enclosure.flats().sort_by(Axis.Z)[0]
        corners = base.vertices().filter_by(Convexity.CONVEX)
        corner_relief(corners, ReliefType.ROUND, radius=relief_radius)
        with GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2):
            Circle(hole_radius, mode=Mode.SUBTRACT)
        with Locations((0, width / 2)):
            Box(slot_length, slot_width, 2 * slot_height, mode=Mode.SUBTRACT)
        long_rims = enclosure.rims().filter_by(Axis.X).group_by(Axis.Z)[-1]
        hem(long_rims, HemType.OPEN, width=hem_width, opening=hem_opening)
# [hem_builder]
builder_result = enclosure.sheet

# [hem_algebra]
parameters = SheetMetalParameters(thickness=thickness, bend_radius=bend_radius)
sheet = Shell(Rectangle(length, width))
sheet = flange(
    sheet.rims(), length=wall_height, gaps=corner_gap, sheet_parameters=parameters
)
base = sheet.flats().sort_by(Axis.Z)[0]
corners = base.vertices().filter_by(Convexity.CONVEX)
sheet = corner_relief(
    corners, ReliefType.ROUND, radius=relief_radius, sheet_parameters=parameters
)
hole_places = GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2)
sheet -= hole_places * Circle(hole_radius)
sheet -= Pos(0, width / 2) * Box(slot_length, slot_width, 2 * slot_height)
long_rims = sheet.rims().filter_by(Axis.X).group_by(Axis.Z)[-1]
sheet = hem(
    long_rims,
    HemType.OPEN,
    width=hem_width,
    opening=hem_opening,
    sheet_parameters=parameters,
)
# [hem_algebra]

assert same(builder_result, sheet)
render(sheet, "hem")

# ---------------------------------------------------------------------------
# Step 7: thicken
# ---------------------------------------------------------------------------
# [thicken_builder]
with BuildPart() as enclosure_part:
    with BuildSheet(thickness=thickness, bend_radius=bend_radius) as enclosure:
        with BuildSketch() as blank:
            Rectangle(length, width)
        flange(enclosure.rims(), length=wall_height, gaps=corner_gap)
        base = enclosure.flats().sort_by(Axis.Z)[0]
        corners = base.vertices().filter_by(Convexity.CONVEX)
        corner_relief(corners, ReliefType.ROUND, radius=relief_radius)
        with GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2):
            Circle(hole_radius, mode=Mode.SUBTRACT)
        with Locations((0, width / 2)):
            Box(slot_length, slot_width, 2 * slot_height, mode=Mode.SUBTRACT)
        long_rims = enclosure.rims().filter_by(Axis.X).group_by(Axis.Z)[-1]
        hem(long_rims, HemType.OPEN, width=hem_width, opening=hem_opening)
    thicken()
# [thicken_builder]
builder_result = enclosure_part.part

# [thicken_algebra]
parameters = SheetMetalParameters(thickness=thickness, bend_radius=bend_radius)
sheet = Shell(Rectangle(length, width))
sheet = flange(
    sheet.rims(), length=wall_height, gaps=corner_gap, sheet_parameters=parameters
)
base = sheet.flats().sort_by(Axis.Z)[0]
corners = base.vertices().filter_by(Convexity.CONVEX)
sheet = corner_relief(
    corners, ReliefType.ROUND, radius=relief_radius, sheet_parameters=parameters
)
hole_places = GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2)
sheet -= hole_places * Circle(hole_radius)
sheet -= Pos(0, width / 2) * Box(slot_length, slot_width, 2 * slot_height)
long_rims = sheet.rims().filter_by(Axis.X).group_by(Axis.Z)[-1]
sheet = hem(
    long_rims,
    HemType.OPEN,
    width=hem_width,
    opening=hem_opening,
    sheet_parameters=parameters,
)
enclosure_part = thicken(sheet, sheet_parameters=parameters)
# [thicken_algebra]

assert abs(builder_result.volume - enclosure_part.volume) < 1e-6
assert enclosure_part.is_valid and len(enclosure_part.solids()) == 1
size_difference = (
    builder_result.bounding_box().size - enclosure_part.bounding_box().size
)
assert size_difference.length < 1e-6
render(enclosure_part, "thicken")

# ---------------------------------------------------------------------------
# Step 8: the flat pattern
# ---------------------------------------------------------------------------
# [flat_builder]
flat_pattern = unfold(enclosure.sheet, enclosure.sheet_parameters, align=Align.MIN).flat

exporter = ExportDXF()
exporter.add_shape(flat_pattern)
exporter.write("enclosure_flat_pattern.dxf")
# [flat_builder]
builder_flat = flat_pattern

# [flat_algebra]
flat_pattern = unfold(sheet, parameters, align=Align.MIN).flat

exporter = ExportDXF()
exporter.add_shape(flat_pattern)
exporter.write("enclosure_flat_pattern.dxf")
# [flat_algebra]

assert abs(builder_flat.area - flat_pattern.area) < 1e-6
assert abs(flat_pattern.bounding_box().size.Z) < 1e-6
render_flat(flat_pattern, "flat")


def pattern_size(k_factor=0.5, sheet_surface=SheetSurface.INSIDE):
    """The size of the flat pattern of the enclosure's walls and hems for a
    K-factor and a reference surface, to check what the page says of them."""
    material = SheetMetalParameters(
        thickness=thickness,
        bend_radius=bend_radius,
        k_factor=k_factor,
        sheet_surface=sheet_surface,
    )
    trial = Shell(Rectangle(length, width))
    trial = flange(
        trial.rims(), length=wall_height, gaps=corner_gap, sheet_parameters=material
    )
    rims = trial.rims().filter_by(Axis.X).group_by(Axis.Z)[-1]
    trial = hem(
        rims,
        HemType.OPEN,
        width=hem_width,
        opening=hem_opening,
        sheet_parameters=material,
    )
    return unfold(trial, material).flat.bounding_box().size


shown = flat_pattern.bounding_box().size
assert (round(shown.X, 1), round(shown.Y, 1)) == (178.6, 155.6)
assert (pattern_size() - shown).length < 1e-6
smaller = pattern_size(k_factor=0.33)
assert (round(smaller.X, 1), round(smaller.Y, 1)) == (177.8, 153.2)
for surface in SheetSurface:
    assert (pattern_size(sheet_surface=surface) - shown).length < 1e-6

# The DXF this script wrote is not wanted in the docs folder.
Path("enclosure_flat_pattern.dxf").unlink()
