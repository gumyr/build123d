"""
Placing sketches documentation examples

name: placing_sketches.py
by:   Gumyr
date: November 15th 2026

desc:
    Every code example of the "Placing sketches" how-to guide lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each example is written in builder and in algebra mode and the
    two are checked against each other. Run it from its own directory; the
    images are written to ``assets/placing_sketches``.

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
from build123d.topology import Shape

OUTPUT = Path("assets/placing_sketches")
OUTPUT.mkdir(parents=True, exist_ok=True)

ISO_VIEW = (1, -1, 0.7)

# ---------------------------------------------------------------------------
# Rendering helpers: parallel projections written as SVG line drawings with
# hidden lines dotted and the placed sketch picked out in a second colour,
# laid out as one or more labelled panels.
# ---------------------------------------------------------------------------

# a panel: visible edges, hidden edges, highlighted edges and a label, all
# drawn in the plane of the page
Panel = tuple[list[Edge], list[Edge], list[Edge], str | None]


def seen(
    scene: Shape,
    view: VectorLike,
    highlight: Shape | None = None,
    label: str | None = None,
    hidden: bool = True,
) -> Panel:
    """The scene seen from far away along view, hidden lines dotted, with the
    highlighted shape's edges picked out."""
    view = Vector(view).normalized()
    up = (0, 1, 0) if abs(view.Z) > 0.99 else (0, 0, 1)
    look_at = scene.center()
    visible, concealed = scene.drawing_view(look_at + view * 1000, up, look_at=look_at)
    picked: list[Edge] = []
    if highlight is not None:
        picked = list(
            highlight.drawing_view(look_at + view * 1000, up, look_at=look_at).visible
        )
    return list(visible), list(concealed) if hidden else [], picked, label


def flat(shape: Shape, label: str | None = None) -> Panel:
    """A planar result drawn as it lies on the page."""
    return list(shape.edges()), [], [], label


def write_layout(panels: list[Panel], name: str, gap_fraction: float = 0.15) -> None:
    """Lay the panels out side by side, label them, and write the SVG."""
    extents = [
        Compound(children=visible + concealed + picked).bounding_box()
        for visible, concealed, picked, _ in panels
    ]
    gap = gap_fraction * max(bb.size.X for bb in extents)
    font_size = 0.06 * max(max(bb.size.X, bb.size.Y) for bb in extents)

    layers: dict[str, list[Shape]] = {
        "Visible": [],
        "Hidden": [],
        "Result": [],
        "Text": [],
    }
    cursor = 0.0
    bottom = min(bb.min.Y for bb in extents)
    for (visible, concealed, picked, label), bb in zip(panels, extents):
        shift = Pos(cursor - bb.min.X, 0, 0)
        layers["Visible"] += [shift * edge for edge in visible]
        layers["Hidden"] += [shift * edge for edge in concealed]
        layers["Result"] += [shift * edge for edge in picked]
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
    svg.add_layer("Result", line_color=0x1E4FA3, line_weight=0.7)
    svg.add_layer("Text", fill_color="black", line_color=None)
    for layer, shapes in layers.items():
        if shapes:
            svg.add_shape(drawing_order(shapes), layer)
    svg.write(OUTPUT / f"{name}.svg")


def drawing_order(shapes: list[Shape]) -> list[Shape]:
    """Shapes sorted by where they lie, so the SVG comes out the same every
    run: a boolean hands its edges back in an order that depends on memory
    addresses, which would otherwise churn the committed images."""

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


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of an example make the same shape?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-6
        and abs(first.area - second.area) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


# ---------------------------------------------------------------------------
# on a standard plane
# ---------------------------------------------------------------------------

# [standard]
with BuildPart() as rib:
    with BuildSketch(Plane.XZ) as outline:
        Trapezoid(40, 20, 70)
    extrude(amount=3, both=True)
# [standard]

builder_result, builder_sketch = rib.part, outline.sketch

# [standard_algebra]
outline = Plane.XZ * Trapezoid(40, 20, 70)
rib = extrude(outline, amount=3, both=True)
# [standard_algebra]

assert same(builder_result, rib) and same(builder_sketch, outline)
# the sketch stands in the XZ plane: flat in Y, 20 tall in Z
assert (
    outline.bounding_box().size.Y < 1e-6
    and abs(outline.bounding_box().size.Z - 20) < 1e-6
)
write_layout([seen(rib, ISO_VIEW, outline, hidden=False)], "standard")

# ---------------------------------------------------------------------------
# raised or lowered
# ---------------------------------------------------------------------------

# [offset]
with BuildPart() as block:
    Box(60, 40, 20)
    with BuildSketch(Plane.XY.offset(10)) as boss:
        Circle(8)
    extrude(amount=6)
# [offset]

builder_result, builder_sketch = block.part, boss.sketch

# [offset_algebra]
block = Box(60, 40, 20)
boss = Plane.XY.offset(10) * Circle(8)
block += extrude(boss, amount=6)
# [offset_algebra]

assert same(builder_result, block) and same(builder_sketch, boss)
assert abs(boss.center().Z - 10) < 1e-6 and abs(block.bounding_box().max.Z - 16) < 1e-6
write_layout([seen(block, ISO_VIEW, boss, hidden=False)], "offset")

# ---------------------------------------------------------------------------
# on a face of the part
# ---------------------------------------------------------------------------

# [face]
with BuildPart() as block:
    Box(60, 40, 20)
    top = block.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(top) as boss:
        Circle(8)
    extrude(amount=6)
# [face]

builder_result, builder_sketch = block.part, boss.sketch

# [face_algebra]
block = Box(60, 40, 20)
top = block.faces().sort_by(Axis.Z)[-1]
boss = Plane(top) * Circle(8)
block += extrude(boss, amount=6)
# [face_algebra]

assert same(builder_result, block) and same(builder_sketch, boss)
# the origin of the sketch is the centre of the face
assert (boss.center() - top.center()).length < 1e-6
write_layout([seen(block, ISO_VIEW, boss, hidden=False)], "face")

# ---------------------------------------------------------------------------
# which way is X
# ---------------------------------------------------------------------------

# [x_dir]
with BuildPart() as console:
    with BuildSketch(Plane.XZ) as profile:
        Polygon((0, 0), (60, 0), (60, 10), (30, 25), (0, 25), align=None)
    extrude(amount=20, both=True)
    slope = console.faces().sort_by(Axis.Z)[-2]
    with BuildSketch(Plane(slope, x_dir=(0, 1, 0))) as window:
        SlotOverall(24, 6)
    extrude(amount=-2, mode=Mode.SUBTRACT)
# [x_dir]

builder_result, builder_sketch = console.part, window.sketch

# [x_dir_algebra]
profile = Plane.XZ * Polygon((0, 0), (60, 0), (60, 10), (30, 25), (0, 25), align=None)
console = extrude(profile, amount=20, both=True)
slope = console.faces().sort_by(Axis.Z)[-2]
window = Plane(slope, x_dir=(0, 1, 0)) * SlotOverall(24, 6)
console -= extrude(window, amount=-2)
# [x_dir_algebra]

assert same(builder_result, console) and same(builder_sketch, window)
# the slot runs across the console, along Y
assert abs(window.bounding_box().size.Y - 24) < 1e-6
# the same slot on the plane the face gives when it is left to choose
plain = extrude(profile, amount=20, both=True)
slope = plain.faces().sort_by(Axis.Z)[-2]
left_to_choose = Plane(slope) * SlotOverall(24, 6)
assert abs(left_to_choose.bounding_box().size.Y - 6) < 1e-6
write_layout(
    [
        seen(
            plain - extrude(left_to_choose, amount=-2),
            ISO_VIEW,
            left_to_choose,
            label="Plane(slope)",
            hidden=False,
        ),
        seen(console, ISO_VIEW, window, label="x_dir=(0, 1, 0)", hidden=False),
    ],
    "x_dir",
)

# ---------------------------------------------------------------------------
# with its origin at a corner
# ---------------------------------------------------------------------------

# [origin]
with BuildPart() as block:
    Box(60, 40, 20)
    top = block.faces().sort_by(Axis.Z)[-1]
    corner = top.vertices().group_by(Axis.X)[0].sort_by(Axis.Y)[0]
    with BuildSketch(Plane(top, x_dir=(1, 0, 0)).shift_origin(corner)) as pocket:
        Rectangle(15, 10, align=Align.MIN)
    extrude(amount=-4, mode=Mode.SUBTRACT)
# [origin]

builder_result, builder_sketch = block.part, pocket.sketch

# [origin_algebra]
block = Box(60, 40, 20)
top = block.faces().sort_by(Axis.Z)[-1]
corner = top.vertices().group_by(Axis.X)[0].sort_by(Axis.Y)[0]
pocket = Plane(top, x_dir=(1, 0, 0)).shift_origin(corner) * Rectangle(
    15, 10, align=Align.MIN
)
block -= extrude(pocket, amount=-4)
# [origin_algebra]

assert same(builder_result, block) and same(builder_sketch, pocket)
# the pocket starts exactly at the corner
assert (pocket.bounding_box().min - Vector(corner)).length < 1e-6
write_layout([seen(block, ISO_VIEW, pocket, hidden=False)], "origin")

# [origin_forms]
on_top = Plane(top, x_dir=(1, 0, 0))
at_vertex = on_top.shift_origin(corner)  # a vertex of the part
at_local = on_top.shift_origin((20, 10))  # x and y measured in the plane
at_global = on_top.shift_origin((20, 10, 10))  # a point in space, on the plane
at_axis = on_top.shift_origin(Axis((20, 10, 0), (0, 0, 1)))  # where an axis crosses
# [origin_forms]

assert (at_local.origin - at_global.origin).length < 1e-6
assert (at_axis.origin - at_global.origin).length < 1e-6

# ---------------------------------------------------------------------------
# features at the vertices of a face
# ---------------------------------------------------------------------------

# [vertices]
with BuildPart() as console:
    with BuildSketch(Plane.XZ) as profile:
        Polygon((0, 0), (60, 0), (60, 10), (30, 25), (0, 25), align=None)
    extrude(amount=20, both=True)
    slope = console.faces().sort_by(Axis.Z)[-2]
    on_slope = Plane(slope, x_dir=(0, 1, 0))
    lower_corners = slope.vertices().group_by(Axis.Z)[0]
    with BuildSketch(on_slope) as notches:
        with Locations(*[on_slope.to_local_coords(v) for v in lower_corners]):
            Circle(5)
    extrude(amount=-3, mode=Mode.SUBTRACT)
# [vertices]

builder_result, builder_sketch = console.part, notches.sketch

# [vertices_algebra]
profile = Plane.XZ * Polygon((0, 0), (60, 0), (60, 10), (30, 25), (0, 25), align=None)
console = extrude(profile, amount=20, both=True)
slope = console.faces().sort_by(Axis.Z)[-2]
on_slope = Plane(slope, x_dir=(0, 1, 0))
lower_corners = slope.vertices().group_by(Axis.Z)[0]
notches = [
    on_slope * Pos(on_slope.to_local_coords(v)) * Circle(5) for v in lower_corners
]
console -= [extrude(notch, amount=-3) for notch in notches]
# [vertices_algebra]

assert same(builder_result, console)
# each circle is centred on a corner of the sloping face
assert len(builder_sketch.faces()) == len(notches) == 2
for notch, corner in zip(notches, lower_corners):
    assert (notch.center() - Vector(corner)).length < 1e-6
write_layout([seen(console, ISO_VIEW, Compound(notches), hidden=False)], "vertices")

# ---------------------------------------------------------------------------
# tilted
# ---------------------------------------------------------------------------

# [tilted]
with BuildPart() as block:
    Box(60, 40, 20)
    with BuildSketch(Plane.XY.rotated((0, 25, 0))) as peg:
        Circle(6)
    extrude(amount=25)
# [tilted]

builder_result, builder_sketch = block.part, peg.sketch

# [tilted_algebra]
block = Box(60, 40, 20)
peg = Plane.XY.rotated((0, 25, 0)) * Circle(6)
block += extrude(peg, amount=25)
# [tilted_algebra]

assert same(builder_result, block) and same(builder_sketch, peg)
# the peg leans toward +X and comes out of the top of the block
assert block.bounding_box().max.Z > 20 and block.bounding_box().max.X < 30 + 1e-6
write_layout([seen(block, ISO_VIEW, peg)], "tilted")

# ---------------------------------------------------------------------------
# at a point along an edge
# ---------------------------------------------------------------------------

# [along]
with BuildPart() as handle:
    with BuildLine() as rail:
        Spline((0, 0, 0), (30, 10, 20), (60, 0, 25), tangents=((1, 0, 0), (1, 0, 0)))
    with BuildSketch(rail.line ^ 0) as section:
        Rectangle(8, 4)
    sweep()
# [along]

builder_result, builder_sketch = handle.part, section.sketch

# [along_algebra]
rail = Spline((0, 0, 0), (30, 10, 20), (60, 0, 25), tangents=((1, 0, 0), (1, 0, 0)))
section = (rail ^ 0) * Rectangle(8, 4)
handle = sweep(section, rail)
# [along_algebra]

assert same(builder_result, handle) and same(builder_sketch, section)
# the sketch stands across the rail at its start
assert abs(section.faces()[0].normal_at().dot(rail % 0)) > 1 - 1e-6
write_layout([seen(handle, ISO_VIEW, section, hidden=False)], "along")

# ---------------------------------------------------------------------------
# in several places at once
# ---------------------------------------------------------------------------

# [several]
with BuildPart() as block:
    Box(60, 40, 20)
    sides = block.faces().filter_by(Axis.Y)
    with BuildSketch(*sides) as bosses:
        Circle(6)
    extrude(amount=5)
# [several]

builder_result, builder_sketch = block.part, bosses.sketch

# [several_algebra]
block = Box(60, 40, 20)
sides = block.faces().filter_by(Axis.Y)
bosses = [Plane(side) * Circle(6) for side in sides]
block += [extrude(boss, amount=5) for boss in bosses]
# [several_algebra]

assert same(builder_result, block)
assert len(builder_sketch.faces()) == len(bosses) == 2
assert abs(block.bounding_box().size.Y - 50) < 1e-6
write_layout([seen(block, ISO_VIEW, Compound(bosses))], "several")
