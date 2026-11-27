"""
Sheet metal documentation examples

name: sheet_metal_examples.py
by:   Gumyr
date: September 12th 2026

desc:
    Every code example in the Sheet Metal section of the documentation lives
    here, between pairs of ``# [name]`` markers that the pages include with
    ``literalinclude``, and this script also renders the SVG images those
    pages embed. Run it from its own directory; the images are written to
    ``../assets/sheet_metal``. Keeping the examples and their pictures in one
    executable file keeps both in step with the library.

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
from build123d.geometry import VectorLike
from build123d.topology import Shape, ShapeList

OUTPUT = Path("../assets/sheet_metal")
OUTPUT.mkdir(parents=True, exist_ok=True)

ISO_VIEW = (1, -1, 0.7)
TOP_VIEW = (0, 0, 1)
ALONG_Y = (0, -1, 0)  # a true profile of bends whose axis runs along Y

# ---------------------------------------------------------------------------
# Rendering helpers: parallel projections written as SVG line drawings with
# hidden lines dotted, laid out as one or more labelled panels.
# ---------------------------------------------------------------------------


PARAMETERS = SheetMetalParameters(thickness=1, bend_radius=2)

# a panel: visible edges, hidden edges, marker edges and a label, all drawn
# in the plane of the page
Panel = tuple[list[Edge], list[Edge], list[Edge], str | None]
Window = tuple[float, float, float, float]  # x min, x max, y min, y max


def clip(edges: list[Edge], window: Window | None) -> list[Edge]:
    """The parts of edges lying within window, or all of them without one."""
    if window is None:
        return list(edges)
    x_min, x_max, y_min, y_max = window
    box = Pos((x_min + x_max) / 2, (y_min + y_max) / 2, 0) * Box(
        x_max - x_min, y_max - y_min, 2
    )
    region = Compound(children=edges) & box
    return [] if region is None else list(region.edges())


def vertical(x: float, y_min: float, y_max: float) -> list[Edge]:
    """A reference line on the page, for a marker."""
    return [Edge.make_line((x, y_min), (x, y_max))]


def horizontal(y: float, x_min: float, x_max: float) -> list[Edge]:
    """A reference line across the page, for a marker."""
    return [Edge.make_line((x_min, y), (x_max, y))]


def projected(
    shape: Shape,
    view: VectorLike,
    label: str | None = None,
    hidden: bool = True,
    window: Window | None = None,
    marker: list[Edge] | None = None,
) -> Panel:
    """Shape seen from far away along view, hidden lines dotted."""
    view = Vector(view).normalized()
    up = (0, 1, 0) if abs(view.Z) > 0.99 else (0, 0, 1)
    visible, concealed = shape.drawing_view(view * 1000, up, look_at=(0, 0, 0))
    return (
        clip(list(visible), window),
        clip(list(concealed), window) if hidden else [],
        marker or [],
        label,
    )


def profile(
    sheet: Shell,
    label: str | None = None,
    window: Window | None = None,
    marker: list[Edge] | None = None,
) -> Panel:
    """A true profile of the thickened sheet, seen along a bend axis on Y."""
    solid = thicken(sheet, sheet_parameters=PARAMETERS)
    return projected(solid, ALONG_Y, label, hidden=False, window=window, marker=marker)


def drawn(flat: Shell, label: str | None = None, window: Window | None = None) -> Panel:
    """A flat pattern's own edges, seen from above, fold lines included."""
    return clip(list(flat.edges()), window), [], [], label


def write_layout(panels: list[Panel], name: str, gap_fraction: float = 0.15) -> None:
    """Lay the panels out side by side, label them, and write the SVG."""
    extents = [
        Compound(children=visible + concealed + marker).bounding_box()
        for visible, concealed, marker, _ in panels
    ]
    gap = gap_fraction * max(bb.size.X for bb in extents)
    font_size = 0.06 * max(max(bb.size.X, bb.size.Y) for bb in extents)

    layers: dict[str, list[Shape]] = {
        "Visible": [],
        "Hidden": [],
        "Marker": [],
        "Text": [],
    }
    cursor = 0.0
    bottom = min(bb.min.Y for bb in extents)
    for (visible, concealed, marker, label), bb in zip(panels, extents):
        shift = Pos(cursor - bb.min.X, 0, 0)
        layers["Visible"] += [shift * edge for edge in visible]
        layers["Hidden"] += [shift * edge for edge in concealed]
        layers["Marker"] += [shift * edge for edge in marker]
        if label:
            centre = cursor + bb.size.X / 2
            layers["Text"].append(
                Pos(centre, bottom - 1.5 * font_size) * Text(label, font_size)
            )
        cursor += bb.size.X + gap

    scene = Compound(children=[s for shapes in layers.values() for s in shapes])
    scale = 100 / max(scene.bounding_box().size.X, scene.bounding_box().size.Y)
    svg = ExportSVG(scale=scale, margin=5)
    svg.add_layer("Visible")
    svg.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
    svg.add_layer("Marker", line_color=0x1E4FA3, line_type=LineType.DASHED)
    svg.add_layer("Text", fill_color="black", line_color=None)
    for layer, shapes in layers.items():
        if shapes:
            svg.add_shape(drawing_order(shapes), layer)
    svg.write(OUTPUT / f"{name}.svg")


def drawing_order(shapes: list[Shape]) -> list[Shape]:
    """Shapes sorted by where they lie, so the SVG comes out the same every run.

    A boolean hands its edges back, and a Text its glyph faces, in an order
    that depends on memory addresses, which would otherwise churn the
    committed images without changing a pixel. Text is taken apart into its
    faces so they can be ordered too.
    """

    def key(shape: Shape) -> tuple:
        if isinstance(shape, Edge):
            ends = sorted(
                (round(shape.position_at(t).X, 4), round(shape.position_at(t).Y, 4))
                for t in (0.0, 1.0)
            )
            middle = shape.position_at(0.5)
            return (*ends, round(middle.X, 4), round(middle.Y, 4))
        centre = shape.center()
        return (round(centre.X, 4), round(centre.Y, 4), round(shape.area, 6))

    pieces = [
        piece
        for shape in shapes
        for piece in (shape.faces() if isinstance(shape, Compound) else [shape])
    ]
    return sorted(pieces, key=key)


def same_sheet(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of an example make the same sheet?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        len(first.faces()) == len(second.faces())
        and abs(first.area - second.area) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


def render(shape: Shape, name: str, view: VectorLike = ISO_VIEW) -> None:
    """A single unlabelled projection."""
    write_layout([projected(shape, view)], name)


# ---------------------------------------------------------------------------
# flange
# ---------------------------------------------------------------------------

# [flange_basic]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    flange(bracket.rims().sort_by(Axis.X)[-1], length=15)
# [flange_basic]

builder_sheet = bracket.sheet

# [flange_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=15, sheet_parameters=parameters
)
# [flange_basic_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "flange_basic")

# [flange_angle]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    # positive folds toward the face normal (+Z), negative away from it
    flange(bracket.rims().sort_by(Axis.X)[-1], length=15, angle=60)
    flange(bracket.rims().sort_by(Axis.X)[0], length=15, angle=-60)
# [flange_angle]

builder_sheet = bracket.sheet

# [flange_angle_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
# positive folds toward the face normal (+Z), negative away from it
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=15, angle=60, sheet_parameters=parameters
)
sheet = flange(
    sheet.rims().sort_by(Axis.X)[0], length=15, angle=-60, sheet_parameters=parameters
)
# [flange_angle_algebra]

assert same_sheet(builder_sheet, sheet)
write_layout([profile(bracket.sheet)], "flange_angle")

# [flange_gaps]
with BuildSheet(thickness=1, bend_radius=2) as tray:
    with BuildSketch():
        Rectangle(60, 40)
    # gaps leave the corners unbent so the four walls do not collide
    flange(tray.rims(), length=15, gaps=3.1)
# [flange_gaps]

builder_sheet = tray.sheet

# [flange_gaps_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
# gaps leave the corners unbent so the four walls do not collide
sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
# [flange_gaps_algebra]

assert same_sheet(builder_sheet, sheet)
render(tray.sheet, "flange_gaps")


# [flange_position]
def flanged_at(position: BendPosition) -> Shell:
    """A blank with one wall, its bend placed relative to the edge."""
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(60, 40)
        flange(bracket.rims().sort_by(Axis.X)[-1], length=15, position=position)
    return bracket.sheet


# [flange_position]


# [flange_position_algebra]
def flanged_at_algebra(position: BendPosition) -> Shell:
    """A blank with one wall, its bend placed relative to the edge."""
    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    return flange(
        blank.edges().sort_by(Axis.X)[-1],
        length=15,
        position=position,
        sheet_parameters=parameters,
    )


# [flange_position_algebra]

for position in BendPosition:
    assert same_sheet(flanged_at(position), flanged_at_algebra(position))
# close up on the bend, with the edge the face was drawn to marked at x = 30
write_layout(
    [
        profile(
            flanged_at(position),
            position.name,
            window=(18, 42, -3, 12),
            marker=vertical(30, -3, 12),
        )
        for position in BendPosition
    ],
    "flange_position",
)


# [flange_length]
def wall_measured(length_from: LengthFrom) -> Shell:
    """A 20 long wall, measured the way a drawing gives it."""
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(60, 40)
        flange(
            bracket.rims().sort_by(Axis.X)[-1],
            length=20,
            position=BendPosition.MATERIAL_OUTSIDE,
            length_from=length_from,
        )
    return bracket.sheet


# [flange_length]


# [flange_length_algebra]
def wall_measured_algebra(length_from: LengthFrom) -> Shell:
    """A 20 long wall, measured the way a drawing gives it."""
    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    return flange(
        blank.edges().sort_by(Axis.X)[-1],
        length=20,
        position=BendPosition.MATERIAL_OUTSIDE,
        length_from=length_from,
        sheet_parameters=parameters,
    )


# [flange_length_algebra]

for origin in LengthFrom:
    assert same_sheet(wall_measured(origin), wall_measured_algebra(origin))
write_layout(
    [
        profile(wall_measured(origin), origin.name, marker=vertical(30, -3, 22))
        for origin in LengthFrom
    ],
    "flange_length",
)


# [flange_length_mode]
def wall_sized(length_mode: LengthMode) -> Shell:
    """A 60 degree wall whose 20 is the side of its triangle the mode names."""
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(60, 40)
        flange(
            bracket.rims().sort_by(Axis.X)[-1],
            length=20,
            angle=60,
            position=BendPosition.MATERIAL_OUTSIDE,
            length_mode=length_mode,
            length_from=LengthFrom.OUTER_SHARP,
        )
    return bracket.sheet


# [flange_length_mode]


# [flange_length_mode_algebra]
def wall_sized_algebra(length_mode: LengthMode) -> Shell:
    """A 60 degree wall whose 20 is the side of its triangle the mode names."""
    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    return flange(
        blank.edges().sort_by(Axis.X)[-1],
        length=20,
        angle=60,
        position=BendPosition.MATERIAL_OUTSIDE,
        length_mode=length_mode,
        length_from=LengthFrom.OUTER_SHARP,
        sheet_parameters=parameters,
    )


# [flange_length_mode_algebra]

for mode in (LengthMode.DIAGONAL, LengthMode.VERTICAL, LengthMode.HORIZONTAL):
    assert same_sheet(wall_sized(mode), wall_sized_algebra(mode))
# the plate's outside face is at z = -1 and its corner on the edge at x = 30,
# so the wall's height is marked 20 above the face and its run 20 past the edge
write_layout(
    [
        profile(wall_sized(mode), mode.name, marker=marker)
        for mode, marker in (
            (LengthMode.DIAGONAL, None),
            (LengthMode.VERTICAL, horizontal(19, 30, 48)),
            (LengthMode.HORIZONTAL, vertical(50, -3, 22)),
        )
    ],
    "flange_length_mode",
)

# ---------------------------------------------------------------------------
# bend and jog
# ---------------------------------------------------------------------------

with BuildSheet(thickness=1, bend_radius=2) as blank:
    with BuildSketch():
        Rectangle(80, 40)
    split(blank.flats()[0], bisect_by=Plane.YZ.offset(20), keep=Keep.BOTH)
render(blank.sheet, "bend_before")

# [bend_basic]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(80, 40)
    # a fold line at x = 20: split the blank into two coplanar flats
    split(bracket.flats()[0], bisect_by=Plane.YZ.offset(20), keep=Keep.BOTH)
    # select the line through the flat that stays put; the other flat swings
    fold_line = bracket.flats().sort_by(Axis.X)[-1].fold_lines()[0]
    bend(fold_line, angle=90)
# [bend_basic]

builder_sheet = bracket.sheet

# [bend_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
# a fold line at x = 20: two coplanar flats joined into one sheet
halves = split(Rectangle(80, 40), bisect_by=Plane.YZ.offset(20), keep=Keep.BOTH)
blank = Shell(halves.faces())
# select the line through the flat that stays put; the other flat swings
fold_line = blank.flats().sort_by(Axis.X)[-1].fold_lines()[0]
sheet = bend(fold_line, angle=90, sheet_parameters=parameters)
# [bend_basic_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "bend_basic")


# [bend_side]
def held_by(side: int) -> Shell:
    """A blank split down the middle and bent 90 degrees, holding one flat."""
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(24, 16)
        split(bracket.flats()[0], bisect_by=Plane.YZ, keep=Keep.BOTH)
        # the line through the flat on this side: that flat stays, the other
        # rolls into the bend and swings
        held = bracket.flats().sort_by(Axis.X)[side]
        bend(held.fold_lines()[0], angle=90)
    return bracket.sheet


# [bend_side]


# [bend_side_algebra]
def held_by_algebra(side: int) -> Shell:
    """A blank split down the middle and bent 90 degrees, holding one flat."""
    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    halves = split(Rectangle(24, 16), bisect_by=Plane.YZ, keep=Keep.BOTH)
    blank = Shell(halves.faces())
    # the line through the flat on this side: that flat stays, the other
    # rolls into the bend and swings
    held = blank.flats().sort_by(Axis.X)[side]
    return bend(held.fold_lines()[0], angle=90, sheet_parameters=parameters)


# [bend_side_algebra]

for side in (0, -1):
    assert same_sheet(held_by(side), held_by_algebra(side))
# profiles of the two results, with the fold line marked at x = 0
write_layout(
    [
        profile(
            held_by(side), label, window=(-14, 14, -3, 12), marker=vertical(0, -3, 12)
        )
        for side, label in ((0, "held on the left"), (-1, "held on the right"))
    ],
    "bend_side",
)

# [jog_basic]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(80, 40)
    split(bracket.flats()[0], bisect_by=Plane.YZ.offset(20), keep=Keep.BOTH)
    fold_line = bracket.flats().sort_by(Axis.X)[-1].fold_lines()[0]
    # the far flat steps 10 toward the face normal and carries on parallel
    jog(fold_line, offset=10)
# [jog_basic]

builder_sheet = bracket.sheet

# [jog_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
halves = split(Rectangle(80, 40), bisect_by=Plane.YZ.offset(20), keep=Keep.BOTH)
blank = Shell(halves.faces())
fold_line = blank.flats().sort_by(Axis.X)[-1].fold_lines()[0]
# the far flat steps 10 toward the face normal and carries on parallel
sheet = jog(fold_line, offset=10, sheet_parameters=parameters)
# [jog_basic_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "jog_basic")

# the same jog with a shallower run, for the profile comparison
with BuildSheet(thickness=1, bend_radius=2) as shallow:
    with BuildSketch():
        Rectangle(80, 40)
    split(shallow.flats()[0], bisect_by=Plane.YZ.offset(20), keep=Keep.BOTH)
    jog(shallow.flats().sort_by(Axis.X)[-1].fold_lines()[0], offset=10, angle=45)
write_layout(
    [profile(bracket.sheet, "angle=90"), profile(shallow.sheet, "angle=45")],
    "jog_profile",
)

# [jog_rim]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    # from a free edge a jog is a stepped flange running on for length
    jog(bracket.rims().sort_by(Axis.X)[-1], offset=10, length=15)
# [jog_rim]

builder_sheet = bracket.sheet

# [jog_rim_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
# from a free edge a jog is a stepped flange running on for length
sheet = jog(
    blank.edges().sort_by(Axis.X)[-1], offset=10, length=15, sheet_parameters=parameters
)
# [jog_rim_algebra]

assert same_sheet(builder_sheet, sheet)
write_layout([profile(bracket.sheet, window=(20, 52, -3, 14))], "jog_rim")

# ---------------------------------------------------------------------------
# hem
# ---------------------------------------------------------------------------

# [hem_types]
with BuildSheet(thickness=1, bend_radius=2) as flat_hem:
    with BuildSketch():
        Rectangle(60, 40)
    hem(flat_hem.rims().sort_by(Axis.X)[-1], HemType.FLAT, width=8)

with BuildSheet(thickness=1, bend_radius=2) as open_hem:
    with BuildSketch():
        Rectangle(60, 40)
    hem(open_hem.rims().sort_by(Axis.X)[-1], HemType.OPEN, width=8, opening=2)

with BuildSheet(thickness=1, bend_radius=2) as teardrop_hem:
    with BuildSketch():
        Rectangle(60, 40)
    hem(teardrop_hem.rims().sort_by(Axis.X)[-1], HemType.TEARDROP, width=12, radius=3)

with BuildSheet(thickness=1, bend_radius=2) as rolled_hem:
    with BuildSketch():
        Rectangle(60, 40)
    hem(rolled_hem.rims().sort_by(Axis.X)[-1], HemType.ROLLED, radius=3, roll_angle=270)
# [hem_types]

builder_hems = [flat_hem.sheet, open_hem.sheet, teardrop_hem.sheet, rolled_hem.sheet]

# [hem_types_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
edge = Rectangle(60, 40).edges().sort_by(Axis.X)[-1]

flat = hem(edge, HemType.FLAT, width=8, sheet_parameters=parameters)
opened = hem(edge, HemType.OPEN, width=8, opening=2, sheet_parameters=parameters)
teardrop = hem(edge, HemType.TEARDROP, width=12, radius=3, sheet_parameters=parameters)
rolled = hem(
    edge, HemType.ROLLED, radius=3, roll_angle=270, sheet_parameters=parameters
)
# [hem_types_algebra]

for builder_hem, algebra_hem in zip(builder_hems, [flat, opened, teardrop, rolled]):
    assert same_sheet(builder_hem, algebra_hem)
hem_window = (12, 36, -4, 12)  # the hemmed end of the blank, curls included
write_layout(
    [
        profile(flat_hem.sheet, "FLAT", window=hem_window),
        profile(open_hem.sheet, "OPEN", window=hem_window),
        profile(teardrop_hem.sheet, "TEARDROP", window=hem_window),
        profile(rolled_hem.sheet, "ROLLED", window=hem_window),
    ],
    "hem_types",
)

# ---------------------------------------------------------------------------
# miter
# ---------------------------------------------------------------------------

# [miter_basic]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    flange(bracket.rims().sort_by(Axis.X)[-1], length=20)
    # the wall's two free corners, at the top of the flange
    wall = bracket.flats().sort_by(Axis.Z)[-1]
    miter(wall.vertices().group_by(Axis.Z)[-1], 30)
# [miter_basic]

builder_sheet = bracket.sheet

# [miter_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=20, sheet_parameters=parameters
)
wall = sheet.flats().sort_by(Axis.Z)[-1]
# the wall's two free corners, at the top of the flange
sheet = miter(wall.vertices().group_by(Axis.Z)[-1], 30)
# [miter_basic_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "miter_basic")

# [miter_through_bend]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    flange(bracket.rims().sort_by(Axis.X)[-1], length=20)
    wall = bracket.flats().sort_by(Axis.Z)[-1]
    # carry the cut through the bend to the fold line
    miter(wall.vertices().group_by(Axis.Z)[-1], 30, through_bend=True)
# [miter_through_bend]

builder_sheet = bracket.sheet

# [miter_through_bend_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=20, sheet_parameters=parameters
)
wall = sheet.flats().sort_by(Axis.Z)[-1]
# carry the cut through the bend to the fold line
sheet = miter(
    wall.vertices().group_by(Axis.Z)[-1],
    30,
    through_bend=True,
    sheet_parameters=parameters,
)
# [miter_through_bend_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "miter_through_bend")

# [miter_flare]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    flange(bracket.rims().sort_by(Axis.X)[-1], length=20)
    wall = bracket.flats().sort_by(Axis.Z)[-1]
    # a negative angle extends the sides instead of trimming them
    miter(wall.vertices().group_by(Axis.Z)[-1], -15, through_bend=True)
# [miter_flare]

builder_sheet = bracket.sheet

# [miter_flare_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=20, sheet_parameters=parameters
)
wall = sheet.flats().sort_by(Axis.Z)[-1]
# a negative angle extends the sides instead of trimming them
sheet = miter(
    wall.vertices().group_by(Axis.Z)[-1],
    -15,
    through_bend=True,
    sheet_parameters=parameters,
)
# [miter_flare_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "miter_flare")

# ---------------------------------------------------------------------------
# corner relief
# ---------------------------------------------------------------------------

# [corner_relief_basic]
with BuildSheet(thickness=1, bend_radius=2) as tray:
    with BuildSketch():
        Rectangle(60, 40)
    flange(tray.rims(), length=15, gaps=3.1)
    # the four corners of the base, where two bends meet
    base = tray.flats().sort_by(Axis.Z)[0]
    corner_relief(
        base.vertices().filter_by(Convexity.CONVEX), ReliefType.ROUND, radius=3
    )
# [corner_relief_basic]

builder_sheet = tray.sheet

# [corner_relief_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
# the four corners of the base, where two bends meet
base = sheet.flats().sort_by(Axis.Z)[0]
sheet = corner_relief(
    base.vertices().filter_by(Convexity.CONVEX),
    ReliefType.ROUND,
    radius=3,
    sheet_parameters=parameters,
)
# [corner_relief_basic_algebra]

assert same_sheet(builder_sheet, sheet)
render(tray.sheet, "corner_relief_basic")


# [corner_relief_types]
def relieved_blank(relief_type: ReliefType, **sizes) -> Shell:
    """The flat pattern of a tray with its four corners relieved."""
    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(60, 40)
        flange(tray.rims(), length=15, gaps=3.1)
        base = tray.flats().sort_by(Axis.Z)[0]
        corner_relief(base.vertices().filter_by(Convexity.CONVEX), relief_type, **sizes)
        return unfold(align=Align.MIN).flat


round_blank = relieved_blank(ReliefType.ROUND, radius=4)
square_blank = relieved_blank(ReliefType.SQUARE, size=8)
obround_blank = relieved_blank(ReliefType.OBROUND, length=12, width=5)
constant_blank = relieved_blank(ReliefType.CONSTANT_WIDTH, depth=6)
# [corner_relief_types]

builder_blanks = [round_blank, square_blank, obround_blank, constant_blank]


# [corner_relief_types_algebra]
def relieved_blank_algebra(relief_type: ReliefType, **sizes) -> Shell:
    """The flat pattern of a tray with its four corners relieved."""
    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
    base = sheet.flats().sort_by(Axis.Z)[0]
    sheet = corner_relief(
        base.vertices().filter_by(Convexity.CONVEX),
        relief_type,
        sheet_parameters=parameters,
        **sizes,
    )
    return unfold(sheet, sheet_parameters=parameters, align=Align.MIN).flat


round_blank = relieved_blank_algebra(ReliefType.ROUND, radius=4)
square_blank = relieved_blank_algebra(ReliefType.SQUARE, size=8)
obround_blank = relieved_blank_algebra(ReliefType.OBROUND, length=12, width=5)
constant_blank = relieved_blank_algebra(ReliefType.CONSTANT_WIDTH, depth=6)
# [corner_relief_types_algebra]

for builder_blank, algebra_blank in zip(
    builder_blanks, [round_blank, square_blank, obround_blank, constant_blank]
):
    assert same_sheet(builder_blank, algebra_blank)


def base_corner_window(blank: Shell, size: float = 26) -> Window:
    """A window around the upper-left corner of the 60 x 40 base on the blank."""
    extent = blank.bounding_box()
    corner_x = extent.min.X + (extent.size.X - 60) / 2
    corner_y = extent.max.Y - (extent.size.Y - 40) / 2
    return (
        corner_x - size / 2,
        corner_x + size / 2,
        corner_y - size / 2,
        corner_y + size / 2,
    )


write_layout(
    [
        drawn(round_blank, "ROUND", base_corner_window(round_blank)),
        drawn(square_blank, "SQUARE", base_corner_window(square_blank)),
        drawn(obround_blank, "OBROUND", base_corner_window(obround_blank)),
        drawn(constant_blank, "CONSTANT_WIDTH", base_corner_window(constant_blank)),
    ],
    "corner_relief_types",
)

# [corner_relief_offset]
GAP = 1.95  # the walls stop 0.05 short of each other's inside face
MITER = GAP * 2**0.5  # how far the cut between the two flanges runs


def closed_corner_blank(offset: float) -> Shell:
    """The flat pattern of a tray with closed corners, each relieved by a
    narrow slot ``offset`` along its miter line."""
    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(60, 40)
        flange(tray.rims(), length=15, gaps=-GAP)
        base = tray.flats().sort_by(Axis.Z)[0]
        corner_relief(
            base.vertices().filter_by(Convexity.CONVEX),
            ReliefType.OBROUND,
            length=1.6,
            width=0.5,
            offset=offset,
        )
        return unfold(align=Align.MIN).flat


at_the_corner = closed_corner_blank(0)
halfway = closed_corner_blank(MITER / 2)
at_the_end = closed_corner_blank(MITER)
# [corner_relief_offset]

builder_blanks = [at_the_corner, halfway, at_the_end]


# [corner_relief_offset_algebra]
def closed_corner_blank_algebra(offset: float) -> Shell:
    """The flat pattern of a tray with closed corners, each relieved by a
    narrow slot ``offset`` along its miter line."""
    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(blank.edges(), length=15, gaps=-GAP, sheet_parameters=parameters)
    base = sheet.flats().sort_by(Axis.Z)[0]
    sheet = corner_relief(
        base.vertices().filter_by(Convexity.CONVEX),
        ReliefType.OBROUND,
        length=1.6,
        width=0.5,
        offset=offset,
        sheet_parameters=parameters,
    )
    return unfold(sheet, sheet_parameters=parameters, align=Align.MIN).flat


at_the_corner = closed_corner_blank_algebra(0)
halfway = closed_corner_blank_algebra(MITER / 2)
at_the_end = closed_corner_blank_algebra(MITER)
# [corner_relief_offset_algebra]

for builder_blank, algebra_blank in zip(
    builder_blanks, [at_the_corner, halfway, at_the_end]
):
    assert same_sheet(builder_blank, algebra_blank)

write_layout(
    [
        drawn(at_the_corner, "offset=0", base_corner_window(at_the_corner, 9)),
        drawn(halfway, "offset=MITER / 2", base_corner_window(halfway, 9)),
        drawn(at_the_end, "offset=MITER", base_corner_window(at_the_end, 9)),
    ],
    "corner_relief_offset",
)

# ---------------------------------------------------------------------------
# bend relief
# ---------------------------------------------------------------------------

# [bend_relief_basic]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    # gaps stop the bend 8 short of each end, inside the sheet
    flange(bracket.rims().sort_by(Axis.X)[-1], length=15, gaps=8)
    bend_relief(bracket.bends(), ReliefType.SQUARE)
# [bend_relief_basic]

builder_sheet = bracket.sheet

# [bend_relief_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
# gaps stop the bend 8 short of each end, inside the sheet
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=15, gaps=8, sheet_parameters=parameters
)
sheet = bend_relief(sheet.bends(), ReliefType.SQUARE, sheet_parameters=parameters)
# [bend_relief_basic_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "bend_relief_basic")


# [bend_relief_types]
def relieved_bend(relief_type: ReliefType) -> Shell:
    """The flat pattern of a short flange with both bend ends relieved."""
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(60, 40)
        flange(bracket.rims().sort_by(Axis.X)[-1], length=15, gaps=8)
        bend_relief(bracket.bends(), relief_type)  # default shop-rule sizes
        return unfold(align=Align.MIN).flat


round_blank = relieved_bend(ReliefType.ROUND)
square_blank = relieved_bend(ReliefType.SQUARE)
obround_blank = relieved_bend(ReliefType.OBROUND)
# [bend_relief_types]

builder_blanks = [round_blank, square_blank, obround_blank]


# [bend_relief_types_algebra]
def relieved_bend_algebra(relief_type: ReliefType) -> Shell:
    """The flat pattern of a short flange with both bend ends relieved."""
    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(
        blank.edges().sort_by(Axis.X)[-1],
        length=15,
        gaps=8,
        sheet_parameters=parameters,
    )
    # default shop-rule sizes
    sheet = bend_relief(sheet.bends(), relief_type, sheet_parameters=parameters)
    return unfold(sheet, sheet_parameters=parameters, align=Align.MIN).flat


round_blank = relieved_bend_algebra(ReliefType.ROUND)
square_blank = relieved_bend_algebra(ReliefType.SQUARE)
obround_blank = relieved_bend_algebra(ReliefType.OBROUND)
# [bend_relief_types_algebra]

for builder_blank, algebra_blank in zip(
    builder_blanks, [round_blank, square_blank, obround_blank]
):
    assert same_sheet(builder_blank, algebra_blank)

# close up on the lower end of the bend, which the flat pattern puts at
# (60, 8): the fold line 30 past the blank's shift to the origin, the bend
# end 8 up for the gap
end_window = (48, 72, -4, 20)
write_layout(
    [
        drawn(round_blank, "ROUND", end_window),
        drawn(square_blank, "SQUARE", end_window),
        drawn(obround_blank, "OBROUND", end_window),
    ],
    "bend_relief_types",
)

# ---------------------------------------------------------------------------
# unfold
# ---------------------------------------------------------------------------

# [unfold_basic]
with BuildSheet(thickness=1, bend_radius=2) as tray:
    with BuildSketch():
        Rectangle(60, 40)
    flange(tray.rims(), length=15, gaps=3.1)
    base = tray.flats().sort_by(Axis.Z)[0]
    corner_relief(
        base.vertices().filter_by(Convexity.CONVEX), ReliefType.ROUND, radius=3
    )
    # the blank the tray is cut from, cornered on the origin
    flat_pattern = unfold(align=Align.MIN).flat
# [unfold_basic]

builder_flat_pattern = flat_pattern

# [unfold_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
base = sheet.flats().sort_by(Axis.Z)[0]
sheet = corner_relief(
    base.vertices().filter_by(Convexity.CONVEX),
    ReliefType.ROUND,
    radius=3,
    sheet_parameters=parameters,
)
# the blank the tray is cut from, cornered on the origin
flat_pattern = unfold(sheet, sheet_parameters=parameters, align=Align.MIN).flat
# [unfold_basic_algebra]

assert same_sheet(builder_flat_pattern, flat_pattern)
write_layout([drawn(flat_pattern)], "unfold_basic")

# ---------------------------------------------------------------------------
# holes and cutouts
# ---------------------------------------------------------------------------

# [cutout_face]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    flange(bracket.rims().sort_by(Axis.Y)[-1], length=20)
    # a sketch cutter trims the sheet face it lies on
    with GridLocations(20, 15, 2, 2):
        Circle(3, mode=Mode.SUBTRACT)  # holes in the base
    wall = bracket.flats().sort_by(Axis.Z)[-1]
    with Locations(Plane(wall)):
        Circle(4, mode=Mode.SUBTRACT)  # a hole in the wall
# [cutout_face]

builder_sheet = bracket.sheet

# [cutout_face_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(
    blank.edges().sort_by(Axis.Y)[-1], length=20, sheet_parameters=parameters
)
# a sketch cutter trims the sheet face it lies on
sheet -= [place * Circle(3) for place in GridLocations(20, 15, 2, 2)]  # the base
wall = sheet.flats().sort_by(Axis.Z)[-1]
sheet -= Plane(wall) * Circle(4)  # a hole in the wall
# [cutout_face_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "cutout_face")

# [cutout_solid]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    flange(bracket.rims().sort_by(Axis.X)[-1], length=20)
    # a solid cutter cuts every face it passes through, bend included
    with Locations((30, 0)):
        Box(12, 8, 60, mode=Mode.SUBTRACT)
# [cutout_solid]

builder_sheet = bracket.sheet

# [cutout_solid_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=20, sheet_parameters=parameters
)
# a solid cutter cuts every face it passes through, bend included
sheet -= Pos(30, 0) * Box(12, 8, 60)
# [cutout_solid_algebra]

assert same_sheet(builder_sheet, sheet)
render(bracket.sheet, "cutout_solid")

# ---------------------------------------------------------------------------
# thicken
# ---------------------------------------------------------------------------

# [thicken_basic]
with BuildPart() as bracket_part:
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(60, 40)
        flange(bracket.rims().sort_by(Axis.X)[-1], length=15)
    # the sheet and its parameters are pending input for thicken
    thicken()
# [thicken_basic]

builder_part = bracket_part.part

# [thicken_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=15, sheet_parameters=parameters
)
# the sheet and its parameters are given to thicken
part = thicken(sheet, sheet_parameters=parameters)
# [thicken_basic_algebra]

assert abs(builder_part.volume - part.volume) < 1e-6
render(bracket_part.part, "thicken_basic")

# ---------------------------------------------------------------------------
# sheet shells
# ---------------------------------------------------------------------------

# [sheet_shells_basic]
with BuildPart() as tray_part:
    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(60, 40)
        flange(tray.rims(), length=15, gaps=3.1)
    thicken()

# the solid, as an imported part would arrive, taken apart again
larger, smaller, thickness = sheet_shells(tray_part.part)
# [sheet_shells_basic]

builder_shells = (larger, smaller, thickness)

# [sheet_shells_basic_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
part = thicken(sheet, sheet_parameters=parameters)

# the solid, as an imported part would arrive, taken apart again
larger, smaller, thickness = sheet_shells(part)
# [sheet_shells_basic_algebra]

assert abs(builder_shells[2] - thickness) < 1e-6
assert abs(builder_shells[1].area - smaller.area) < 1e-6
render(smaller, "sheet_shells_basic")

# ---------------------------------------------------------------------------
# the landing page
# ---------------------------------------------------------------------------

# [index_tray]
with BuildPart() as tray_part:
    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.rims(), length=15, gaps=3.1)
        corners = tray.flats().sort_by(Axis.Z)[0].vertices()
        corner_relief(corners.filter_by(Convexity.CONVEX), ReliefType.ROUND, radius=3)
    thicken()
# [index_tray]

builder_part = tray_part.part

# [index_tray_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(100, 60)
sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
corners = sheet.flats().sort_by(Axis.Z)[0].vertices()
sheet = corner_relief(
    corners.filter_by(Convexity.CONVEX),
    ReliefType.ROUND,
    radius=3,
    sheet_parameters=parameters,
)
tray_part = thicken(sheet, sheet_parameters=parameters)
# [index_tray_algebra]

assert abs(builder_part.volume - tray_part.volume) < 1e-6

# ---------------------------------------------------------------------------
# recipes
# ---------------------------------------------------------------------------

# [recipe_tab]
with BuildSheet(thickness=1, bend_radius=1) as bracket:
    with BuildSketch():
        Rectangle(100, 60)
        SlotCenterToCenter(30, 8, mode=Mode.SUBTRACT)
    slot_edge = bracket.rims().filter_by(Axis.X).sort_by(Axis.Y)[1]
    flange(slot_edge, length=12, gaps=2)
# [recipe_tab]

builder_sheet = bracket.sheet

# [recipe_tab_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=1)
blank = Rectangle(100, 60) - SlotCenterToCenter(30, 8)
slot_edge = blank.edges().filter_by(Axis.X).sort_by(Axis.Y)[1]
sheet = flange(slot_edge, length=12, gaps=2, sheet_parameters=parameters)
# [recipe_tab_algebra]

assert same_sheet(builder_sheet, sheet)
# the tab is 26 wide in a 30 slot and stands 13 high, its bend included
tab = sheet.flats().sort_by(Axis.Z)[-1]
assert abs(tab.bounding_box().size.X - 26) < 1e-6
assert abs(sheet.bounding_box().max.Z - 13) < 1e-6

# [recipe_cut]
with BuildSheet(thickness=1, bend_radius=2) as tray:
    with BuildSketch():
        Rectangle(100, 60)
    flange(tray.rims().sort_by(Axis.X)[-1], length=20)
    with Locations((50, 0)):
        Box(20, 6, 60, mode=Mode.SUBTRACT)
# [recipe_cut]

builder_sheet = tray.sheet

# [recipe_cut_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(100, 60)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=20, sheet_parameters=parameters
)
sheet -= Pos(50, 0) * Box(20, 6, 60)
# [recipe_cut_algebra]

assert same_sheet(builder_sheet, sheet)

# [recipe_flare]
with BuildSheet(thickness=1, bend_radius=2) as leg:
    with BuildSketch():
        Rectangle(40, 20)
    flange(leg.rims().sort_by(Axis.X)[-1], length=30)
    wall = leg.flats().sort_by(Axis.Z)[-1]
    miter(wall.vertices().group_by(Axis.Z)[-1], -15, through_bend=True)
# [recipe_flare]

builder_sheet = leg.sheet

# [recipe_flare_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(40, 20)
sheet = flange(
    blank.edges().sort_by(Axis.X)[-1], length=30, sheet_parameters=parameters
)
wall = sheet.flats().sort_by(Axis.Z)[-1]
sheet = miter(
    wall.vertices().group_by(Axis.Z)[-1],
    -15,
    through_bend=True,
    sheet_parameters=parameters,
)
# [recipe_flare_algebra]

assert same_sheet(builder_sheet, sheet)
# the wall's free end is 38.2 wide on a 20 edge, and the bend widens to 22.1
wall = sheet.flats().sort_by(Axis.Z)[-1]
assert abs(wall.bounding_box().size.Y - 38.2) < 0.05
assert abs(sheet.bends()[0].bounding_box().size.Y - 22.1) < 0.05

# [recipe_narrow]
with BuildSheet(thickness=1, bend_radius=2) as plate:
    with BuildSketch():
        Rectangle(100, 60)
    flange(
        plate.rims().sort_by(Axis.X)[-1],
        length=15,
        gaps=(10, 30),
        position=BendPosition.MATERIAL_INSIDE,
    )
blank = unfold(plate.sheet, plate.sheet_parameters).flat
# [recipe_narrow]

builder_sheet, builder_blank = plate.sheet, blank

# [recipe_narrow_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
plate = flange(
    Rectangle(100, 60).edges().sort_by(Axis.X)[-1],
    length=15,
    gaps=(10, 30),
    position=BendPosition.MATERIAL_INSIDE,
    sheet_parameters=parameters,
)
blank = unfold(plate, parameters).flat
# [recipe_narrow_algebra]

assert same_sheet(builder_sheet, plate) and same_sheet(builder_blank, blank)
# the bend is 20 wide on a 60 edge
assert abs(plate.bends()[0].bounding_box().size.Y - 20) < 1e-6

# [recipe_corners]
with BuildSheet(thickness=1, bend_radius=2) as box:
    with BuildSketch():
        Rectangle(60, 40)
    flange(box.rims(), length=15, gaps=3.1)
    walls = box.flats().group_by(Axis.Z)[-1]
    miter(walls.vertices().group_by(Axis.Z)[-1], 45, through_bend=True)
# [recipe_corners]

builder_sheet = box.sheet

# [recipe_corners_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=2)
blank = Rectangle(60, 40)
sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
walls = sheet.flats().group_by(Axis.Z)[-1]
sheet = miter(
    walls.vertices().group_by(Axis.Z)[-1],
    45,
    through_bend=True,
    sheet_parameters=parameters,
)
# [recipe_corners_algebra]

assert same_sheet(builder_sheet, sheet)

# [recipe_channel]
with BuildPart() as channel_part:
    with BuildSheet(thickness=2, bend_radius=3) as channel:
        with BuildSketch():
            Rectangle(60, 100)
        flange(
            channel.rims().filter_by(Axis.Y),
            length=40,
            position=BendPosition.MATERIAL_OUTSIDE,
            length_from=LengthFrom.OUTER_SHARP,
        )
    thicken()
# [recipe_channel]

builder_part = channel_part.part

# [recipe_channel_algebra]
parameters = SheetMetalParameters(thickness=2, bend_radius=3)
channel = flange(
    Rectangle(60, 100).edges().filter_by(Axis.Y),
    length=40,
    position=BendPosition.MATERIAL_OUTSIDE,
    length_from=LengthFrom.OUTER_SHARP,
    sheet_parameters=parameters,
)
channel_part = thicken(channel, sheet_parameters=parameters)
# [recipe_channel_algebra]

assert abs(builder_part.volume - channel_part.volume) < 1e-6
# 60 x 100 x 40 outside, and a flat pattern 132.566 long
assert (channel_part.bounding_box().size - Vector(60, 100, 40)).length < 1e-6
assert abs(unfold(channel, parameters).flat.bounding_box().size.X - 132.566) < 1e-3

# [recipe_reuse]
with BuildSheet(thickness=1, bend_radius=2) as lug:
    with BuildSketch():
        Rectangle(20, 10)
    flange(lug.rims().sort_by(Axis.X)[-1], length=10)

with BuildSheet(thickness=1, bend_radius=2) as plate:
    with BuildSketch():
        Rectangle(60, 40)
    with Locations((20, 0)):
        insert(lug)
# [recipe_reuse]

# one connected sheet: the plate, the lug's bend and its wall
assert len(plate.sheet.faces()) == 3 and plate.sheet.is_valid

# ---------------------------------------------------------------------------
# the picture at the head of the section: an open enclosure base
# ---------------------------------------------------------------------------

with BuildPart() as enclosure_part:
    with BuildSheet(thickness=1.5, bend_radius=2) as enclosure:
        with BuildSketch():
            Rectangle(120, 80)
        flange(enclosure.rims(), length=25, gaps=3.5)
        base = enclosure.flats().sort_by(Axis.Z)[0]
        corner_relief(
            base.vertices().filter_by(Convexity.CONVEX), ReliefType.ROUND, radius=3
        )
        with GridLocations(90, 50, 2, 2):
            Circle(2, mode=Mode.SUBTRACT)  # mounting holes in the base
        with Locations((0, 40)):
            Box(20, 8, 20, mode=Mode.SUBTRACT)  # a slot across the +Y wall's bend
        long_rims = enclosure.rims().filter_by(Axis.X).group_by(Axis.Z)[-1]
        hem(long_rims, HemType.OPEN, width=6, opening=1.5)
    thicken()

render(enclosure_part.part, "hero")
