"""
A lid for the enclosure tutorial

name: sheet_metal_lid.py
by:   Gumyr
date: November 12th 2026

desc:
    Every code example in the "A lid for the enclosure" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. The tutorial carries on from "A sheet metal enclosure", so this
    script first runs ``sheet_metal_enclosure.py``, which sits beside it, and
    takes the base from it. Each step is written twice, once in builder mode
    and once in algebra mode, and the two are checked against each other. Run
    it from its own directory; the images are written to
    ``assets/sheet_metal_lid``.

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

import contextlib
import io
import runpy
import types
from pathlib import Path

from build123d.topology import Shape

# Carry on from the end of "A sheet metal enclosure": run its script and take
# its names from it.
with contextlib.redirect_stdout(io.StringIO()):
    made = runpy.run_path(str(Path(__file__).with_name("sheet_metal_enclosure.py")))
globals().update({k: v for k, v in made.items() if not k.startswith("_")})
BASE = made["enclosure_part"]  # the thickened base, a Part

# [setup]
lid_thickness, lid_bend_radius = 1.5, 1
plate_length, plate_width = 118, 70
step_height, lip_width = 4, 5
tab_length, tab_gap = 12, 20
tab_miter = 30
lead_in_height, lead_in_angle = 8, 20
# [setup]

OUTPUT = Path("assets/sheet_metal_lid")
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
    exporter.write(OUTPUT / f"lid_{name}.svg")


def render_flat(flat: Shape, name: str) -> None:
    """Write a flat pattern, seen from above, fold lines included."""
    size = flat.bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_shape(flat.edges(), layer="Visible")
    exporter.write(OUTPUT / f"lid_{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same sheet?"""
    return (
        abs(first.area - second.area) < 1e-6
        and (first.bounding_box().size - second.bounding_box().size).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 2: the plate
# ---------------------------------------------------------------------------
# [plate_builder]
with BuildPart() as lid_part:
    with BuildSheet(thickness=lid_thickness, bend_radius=lid_bend_radius) as lid:
        with BuildSketch() as plate:
            Rectangle(plate_length, plate_width)
# [plate_builder]
builder_result = lid.sheet

# [plate_algebra]
lid_material = SheetMetalParameters(
    thickness=lid_thickness, bend_radius=lid_bend_radius
)
lid = Shell(Rectangle(plate_length, plate_width))
# [plate_algebra]

assert same(builder_result, lid)
render(lid, "plate")

# ---------------------------------------------------------------------------
# Step 3: stepped lips
# ---------------------------------------------------------------------------
# [lips_builder]
with BuildPart() as lid_part:
    with BuildSheet(thickness=lid_thickness, bend_radius=lid_bend_radius) as lid:
        with BuildSketch() as plate:
            Rectangle(plate_length, plate_width)
        jog(lid.rims().filter_by(Axis.X), offset=step_height, length=lip_width)
# [lips_builder]
builder_result = lid.sheet

# [lips_algebra]
lid_material = SheetMetalParameters(
    thickness=lid_thickness, bend_radius=lid_bend_radius
)
lid = Shell(Rectangle(plate_length, plate_width))
lid = jog(
    lid.rims().filter_by(Axis.X),
    offset=step_height,
    length=lip_width,
    sheet_parameters=lid_material,
)
# [lips_algebra]

assert same(builder_result, lid)
render(lid, "lips")

# ---------------------------------------------------------------------------
# Step 4: tabs
# ---------------------------------------------------------------------------
# [tabs_builder]
with BuildPart() as lid_part:
    with BuildSheet(thickness=lid_thickness, bend_radius=lid_bend_radius) as lid:
        with BuildSketch() as plate:
            Rectangle(plate_length, plate_width)
        jog(lid.rims().filter_by(Axis.X), offset=step_height, length=lip_width)
        ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
        flange(ends, length=tab_length, angle=-90, gaps=tab_gap)
# [tabs_builder]
builder_result = lid.sheet

# [tabs_algebra]
lid_material = SheetMetalParameters(
    thickness=lid_thickness, bend_radius=lid_bend_radius
)
lid = Shell(Rectangle(plate_length, plate_width))
lid = jog(
    lid.rims().filter_by(Axis.X),
    offset=step_height,
    length=lip_width,
    sheet_parameters=lid_material,
)
ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
lid = flange(
    ends, length=tab_length, angle=-90, gaps=tab_gap, sheet_parameters=lid_material
)
# [tabs_algebra]

assert same(builder_result, lid)
render(lid, "tabs", viewpoint=(-90, -150, -160))

# ---------------------------------------------------------------------------
# Step 5: relieve the bends
# ---------------------------------------------------------------------------
# [relief_builder]
with BuildPart() as lid_part:
    with BuildSheet(thickness=lid_thickness, bend_radius=lid_bend_radius) as lid:
        with BuildSketch() as plate:
            Rectangle(plate_length, plate_width)
        jog(lid.rims().filter_by(Axis.X), offset=step_height, length=lip_width)
        ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
        flange(ends, length=tab_length, angle=-90, gaps=tab_gap)
        bend_relief(lid.bends().filter_by(Axis.Y), ReliefType.OBROUND)
# [relief_builder]
builder_result = lid.sheet

# [relief_algebra]
lid_material = SheetMetalParameters(
    thickness=lid_thickness, bend_radius=lid_bend_radius
)
lid = Shell(Rectangle(plate_length, plate_width))
lid = jog(
    lid.rims().filter_by(Axis.X),
    offset=step_height,
    length=lip_width,
    sheet_parameters=lid_material,
)
ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
lid = flange(
    ends, length=tab_length, angle=-90, gaps=tab_gap, sheet_parameters=lid_material
)
lid = bend_relief(
    lid.bends().filter_by(Axis.Y), ReliefType.OBROUND, sheet_parameters=lid_material
)
# [relief_algebra]

assert same(builder_result, lid)
render(lid, "relief", viewpoint=(-90, -150, -160))

# ---------------------------------------------------------------------------
# Step 6: trim the corners of the tabs
# ---------------------------------------------------------------------------
# [miter_builder]
with BuildPart() as lid_part:
    with BuildSheet(thickness=lid_thickness, bend_radius=lid_bend_radius) as lid:
        with BuildSketch() as plate:
            Rectangle(plate_length, plate_width)
        jog(lid.rims().filter_by(Axis.X), offset=step_height, length=lip_width)
        ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
        flange(ends, length=tab_length, angle=-90, gaps=tab_gap)
        bend_relief(lid.bends().filter_by(Axis.Y), ReliefType.OBROUND)
        tabs = lid.flats().filter_by(Axis.X)
        miter(tabs.vertices().group_by(Axis.Z)[0], tab_miter)
# [miter_builder]
builder_result = lid.sheet

# [miter_algebra]
lid_material = SheetMetalParameters(
    thickness=lid_thickness, bend_radius=lid_bend_radius
)
lid = Shell(Rectangle(plate_length, plate_width))
lid = jog(
    lid.rims().filter_by(Axis.X),
    offset=step_height,
    length=lip_width,
    sheet_parameters=lid_material,
)
ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
lid = flange(
    ends, length=tab_length, angle=-90, gaps=tab_gap, sheet_parameters=lid_material
)
lid = bend_relief(
    lid.bends().filter_by(Axis.Y), ReliefType.OBROUND, sheet_parameters=lid_material
)
tabs = lid.flats().filter_by(Axis.X)
lid = miter(
    tabs.vertices().group_by(Axis.Z)[0], tab_miter, sheet_parameters=lid_material
)
# [miter_algebra]

assert same(builder_result, lid)
render(lid, "miter", viewpoint=(-90, -150, -160))

# ---------------------------------------------------------------------------
# Step 7: bend a lead-in
# ---------------------------------------------------------------------------
# [lead_in_builder]
with BuildPart() as lid_part:
    with BuildSheet(thickness=lid_thickness, bend_radius=lid_bend_radius) as lid:
        with BuildSketch() as plate:
            Rectangle(plate_length, plate_width)
        jog(lid.rims().filter_by(Axis.X), offset=step_height, length=lip_width)
        ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
        flange(ends, length=tab_length, angle=-90, gaps=tab_gap)
        bend_relief(lid.bends().filter_by(Axis.Y), ReliefType.OBROUND)
        tabs = lid.flats().filter_by(Axis.X)
        miter(tabs.vertices().group_by(Axis.Z)[0], tab_miter)
        split(bisect_by=Plane.XY.offset(-lead_in_height), keep=Keep.BOTH)
        for upper in lid.flats().filter_by(Axis.X).group_by(Axis.Z)[-1]:
            bend(upper.fold_lines()[0], angle=-lead_in_angle)
# [lead_in_builder]
builder_result = lid.sheet

# [lead_in_algebra]
lid_material = SheetMetalParameters(
    thickness=lid_thickness, bend_radius=lid_bend_radius
)
lid = Shell(Rectangle(plate_length, plate_width))
lid = jog(
    lid.rims().filter_by(Axis.X),
    offset=step_height,
    length=lip_width,
    sheet_parameters=lid_material,
)
ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
lid = flange(
    ends, length=tab_length, angle=-90, gaps=tab_gap, sheet_parameters=lid_material
)
lid = bend_relief(
    lid.bends().filter_by(Axis.Y), ReliefType.OBROUND, sheet_parameters=lid_material
)
tabs = lid.flats().filter_by(Axis.X)
lid = miter(
    tabs.vertices().group_by(Axis.Z)[0], tab_miter, sheet_parameters=lid_material
)
pieces = split(lid, bisect_by=Plane.XY.offset(-lead_in_height), keep=Keep.BOTH)
lid = Shell(pieces.faces())
for side in (0, -1):
    uppers = lid.flats().filter_by(Axis.X).group_by(Axis.Z)[-1]
    fold_line = uppers.sort_by(Axis.X)[side].fold_lines()[0]
    lid = bend(fold_line, angle=-lead_in_angle, sheet_parameters=lid_material)
# [lead_in_algebra]

assert same(builder_result, lid)
render(lid, "lead_in", viewpoint=(-90, -150, -160))

# ---------------------------------------------------------------------------
# Step 8: thicken
# ---------------------------------------------------------------------------
# [thicken_builder]
with BuildPart() as lid_part:
    with BuildSheet(thickness=lid_thickness, bend_radius=lid_bend_radius) as lid:
        with BuildSketch() as plate:
            Rectangle(plate_length, plate_width)
        jog(lid.rims().filter_by(Axis.X), offset=step_height, length=lip_width)
        ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
        flange(ends, length=tab_length, angle=-90, gaps=tab_gap)
        bend_relief(lid.bends().filter_by(Axis.Y), ReliefType.OBROUND)
        tabs = lid.flats().filter_by(Axis.X)
        miter(tabs.vertices().group_by(Axis.Z)[0], tab_miter)
        split(bisect_by=Plane.XY.offset(-lead_in_height), keep=Keep.BOTH)
        for upper in lid.flats().filter_by(Axis.X).group_by(Axis.Z)[-1]:
            bend(upper.fold_lines()[0], angle=-lead_in_angle)
    thicken()
# [thicken_builder]
builder_result = lid_part.part
builder_lid, builder_sheet = lid_part, lid

# [thicken_algebra]
lid_material = SheetMetalParameters(
    thickness=lid_thickness, bend_radius=lid_bend_radius
)
lid = Shell(Rectangle(plate_length, plate_width))
lid = jog(
    lid.rims().filter_by(Axis.X),
    offset=step_height,
    length=lip_width,
    sheet_parameters=lid_material,
)
ends = lid.rims().filter_by(Axis.Y).group_by(Axis.Z)[0]
lid = flange(
    ends, length=tab_length, angle=-90, gaps=tab_gap, sheet_parameters=lid_material
)
lid = bend_relief(
    lid.bends().filter_by(Axis.Y), ReliefType.OBROUND, sheet_parameters=lid_material
)
tabs = lid.flats().filter_by(Axis.X)
lid = miter(
    tabs.vertices().group_by(Axis.Z)[0], tab_miter, sheet_parameters=lid_material
)
pieces = split(lid, bisect_by=Plane.XY.offset(-lead_in_height), keep=Keep.BOTH)
lid = Shell(pieces.faces())
for side in (0, -1):
    uppers = lid.flats().filter_by(Axis.X).group_by(Axis.Z)[-1]
    fold_line = uppers.sort_by(Axis.X)[side].fold_lines()[0]
    lid = bend(fold_line, angle=-lead_in_angle, sheet_parameters=lid_material)
lid_part = thicken(lid, sheet_parameters=lid_material)
# [thicken_algebra]

assert abs(builder_result.volume - lid_part.volume) < 1e-6
assert lid_part.is_valid and len(lid_part.solids()) == 1
algebra_sheet = lid
render(lid_part, "thicken")
render(lid_part, "underside", viewpoint=(-90, -150, -160))

# ---------------------------------------------------------------------------
# Step 9: put the lid on
# ---------------------------------------------------------------------------
enclosure_part = types.SimpleNamespace(part=BASE)
lid_part = builder_lid
# [fit_builder]
base = enclosure_part.part
lift = base.bounding_box().max.Z - (step_height - lid_thickness)
fitted_lid = Pos(0, 0, lift) * lid_part.part

box = Compound(label="enclosure", children=[base, fitted_lid])
print(box.do_children_intersect()[0])
# [fit_builder]
builder_box = box

enclosure_part = BASE
lid_part = thicken(lid, sheet_parameters=lid_material)
# [fit_algebra]
base = enclosure_part
lift = base.bounding_box().max.Z - (step_height - lid_thickness)
fitted_lid = Pos(0, 0, lift) * lid_part

box = Compound(label="enclosure", children=[base, fitted_lid])
print(box.do_children_intersect()[0])
# [fit_algebra]

assert box.do_children_intersect()[0] is False
assert builder_box.do_children_intersect()[0] is False
fitted, body = fitted_lid.bounding_box(), base.bounding_box()
assert abs(fitted.size.Y - body.size.Y) < 1e-6  # the lips are flush with the walls
assert fitted.size.X < body.size.X - 2 * thickness  # the tabs are inside the walls


def render_pair(name, cut=None, viewpoint=(-90, -150, 130)):
    """The base and the lid together, optionally with the front cut away."""
    shapes = [base, fitted_lid]
    if cut is not None:
        shapes = [shape & cut for shape in shapes]
    scene = Compound(children=shapes)
    look_at = scene.bounding_box().center()
    visible, hidden = scene.drawing_view(Vector(viewpoint) + look_at, look_at=look_at)
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0xB0B0B0, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_shape(hidden, layer="Hidden")
    exporter.add_shape(visible, layer="Visible")
    exporter.write(OUTPUT / f"lid_{name}.svg")


render_pair("fitted")
render_pair("section", cut=Pos(100, 0, 0) * Box(200, 300, 300), viewpoint=(-200, 0, 20))

# ---------------------------------------------------------------------------
# Step 10: the flat pattern
# ---------------------------------------------------------------------------
lid = builder_sheet
# [flat_builder]
lid_pattern = unfold(lid.sheet, lid.sheet_parameters, align=Align.MIN).flat
# [flat_builder]
builder_pattern = lid_pattern

lid = algebra_sheet
# [flat_algebra]
lid_pattern = unfold(lid, lid_material, align=Align.MIN).flat
# [flat_algebra]
assert abs(builder_pattern.area - lid_pattern.area) < 1e-6
assert abs(lid_pattern.bounding_box().size.Z) < 1e-6
render_flat(lid_pattern, "flat")
