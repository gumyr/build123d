"""
Sheet metal documentation examples

name: sheet_metal_examples.py
by:   Gumyr
date: September 12th 2026

desc:
    Every code example in the Sheet Metal section of the documentation lives
    here, between pairs of ``# [name]`` markers that the pages include with
    ``literalinclude``, and this script also renders the SVG images those
    pages embed. Run it from the ``docs`` directory; the images are written to
    ``assets/sheet_metal``. Keeping the examples and their pictures in one
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

import os
import tempfile
from pathlib import Path

from build123d import *
from build123d.geometry import VectorLike
from build123d.topology import Shape, ShapeList

OUTPUT = Path("assets/sheet_metal")
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
    visible, concealed = shape.project_to_viewport(view * 1000, up, look_at=(0, 0, 0))
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
            svg.add_shape(shapes, layer)
    svg.write(OUTPUT / f"{name}.svg")


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
render(bracket.sheet, "flange_basic")

# [flange_angle]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(60, 40)
    # positive folds toward the face normal (+Z), negative away from it
    flange(bracket.rims().sort_by(Axis.X)[-1], length=15, angle=60)
    flange(bracket.rims().sort_by(Axis.X)[0], length=15, angle=-60)
# [flange_angle]
write_layout([profile(bracket.sheet)], "flange_angle")

# [flange_gaps]
with BuildSheet(thickness=1, bend_radius=2) as tray:
    with BuildSketch():
        Rectangle(60, 40)
    # gaps leave the corners unbent so the four walls do not collide
    flange(tray.rims(), length=15, gaps=3.1)
# [flange_gaps]
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
def wall_measured(length_mode: FlangeLength) -> Shell:
    """A 20 long wall, measured the way a drawing gives it."""
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(60, 40)
        flange(
            bracket.rims().sort_by(Axis.X)[-1],
            length=20,
            position=BendPosition.MATERIAL_OUTSIDE,
            length_mode=length_mode,
        )
    return bracket.sheet


# [flange_length]
write_layout(
    [
        profile(wall_measured(mode), mode.name, marker=vertical(30, -3, 22))
        for mode in FlangeLength
    ],
    "flange_length",
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
render(bracket.sheet, "bend_basic")

# [jog_basic]
with BuildSheet(thickness=1, bend_radius=2) as bracket:
    with BuildSketch():
        Rectangle(80, 40)
    split(bracket.flats()[0], bisect_by=Plane.YZ.offset(20), keep=Keep.BOTH)
    fold_line = bracket.flats().sort_by(Axis.X)[-1].fold_lines()[0]
    # the far flat steps 10 toward the face normal and carries on parallel
    jog(fold_line, offset=10)
# [jog_basic]
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
render(tray.sheet, "corner_relief_basic")


# [corner_relief_types]
def relieved_blank(relief_type: ReliefType, **sizes) -> Shell:
    """The flat pattern of a tray with its four corners relieved."""
    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(60, 40)
        flange(tray.rims(), length=15, gaps=3.1)
        base = tray.flats().sort_by(Axis.Z)[0]
        corner_relief(
            base.vertices().filter_by(Convexity.CONVEX), relief_type, **sizes
        )
        return unfold(align=Align.MIN)


round_blank = relieved_blank(ReliefType.ROUND, radius=4)
square_blank = relieved_blank(ReliefType.SQUARE, size=8)
obround_blank = relieved_blank(ReliefType.OBROUND, length=12, width=5)
constant_blank = relieved_blank(ReliefType.CONSTANT_WIDTH, depth=6)
# [corner_relief_types]


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
render(bracket.sheet, "bend_relief_basic")


# [bend_relief_types]
def relieved_bend(relief_type: ReliefType) -> Shell:
    """The flat pattern of a short flange with both bend ends relieved."""
    with BuildSheet(thickness=1, bend_radius=2) as bracket:
        with BuildSketch():
            Rectangle(60, 40)
        flange(bracket.rims().sort_by(Axis.X)[-1], length=15, gaps=8)
        bend_relief(bracket.bends(), relief_type)  # default shop-rule sizes
        return unfold(align=Align.MIN)


round_blank = relieved_bend(ReliefType.ROUND)
square_blank = relieved_bend(ReliefType.SQUARE)
obround_blank = relieved_bend(ReliefType.OBROUND)
# [bend_relief_types]

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
    flat_pattern = unfold(align=Align.MIN)
# [unfold_basic]
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
render(bracket_part.part, "thicken_basic")

# ---------------------------------------------------------------------------
# tutorial: an open enclosure base
# ---------------------------------------------------------------------------

with BuildPart() as enclosure_part:
    with BuildSheet(thickness=1.5, bend_radius=2) as enclosure:
        # [tutorial_1]
        with BuildSketch():
            Rectangle(120, 80)
        # [tutorial_1]
        step_1 = enclosure.sheet
        # [tutorial_2]
        flange(enclosure.rims(), length=25, gaps=3.5)
        # [tutorial_2]
        step_2 = enclosure.sheet
        # [tutorial_3]
        base = enclosure.flats().sort_by(Axis.Z)[0]
        corner_relief(
            base.vertices().filter_by(Convexity.CONVEX), ReliefType.ROUND, radius=3
        )
        # [tutorial_3]
        step_3 = enclosure.sheet
        # [tutorial_4]
        with GridLocations(90, 50, 2, 2):
            Circle(2, mode=Mode.SUBTRACT)  # mounting holes in the base
        with Locations((0, 40)):
            Box(20, 8, 20, mode=Mode.SUBTRACT)  # a slot across the +Y wall's bend
        # [tutorial_4]
        step_4 = enclosure.sheet
        # [tutorial_5]
        long_rims = enclosure.rims().filter_by(Axis.X).group_by(Axis.Z)[-1]
        hem(long_rims, HemType.OPEN, width=6, opening=1.5)
        # [tutorial_5]
        step_5 = enclosure.sheet
    # [tutorial_6]
    thicken()
    # [tutorial_6]

render(step_1, "tutorial_1")
render(step_2, "tutorial_2")
render(step_3, "tutorial_3")
render(step_4, "tutorial_4")
render(step_5, "tutorial_5")
render(enclosure_part.part, "tutorial_6")
render(enclosure_part.part, "hero")

# the DXF is written to a scratch directory so that running this script
# leaves nothing but the images behind
with tempfile.TemporaryDirectory() as scratch:
    docs_directory = os.getcwd()
    os.chdir(scratch)
    # [tutorial_7]
    flat_pattern = unfold(enclosure.sheet, enclosure.sheet_parameters, align=Align.MIN)
    exporter = ExportDXF()
    exporter.add_shape(flat_pattern)
    exporter.write("enclosure_flat_pattern.dxf")
    # [tutorial_7]
    os.chdir(docs_directory)
write_layout([drawn(flat_pattern)], "tutorial_7")
