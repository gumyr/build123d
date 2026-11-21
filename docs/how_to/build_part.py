"""
Building parts documentation examples

name: build_part.py
by:   Gumyr
date: November 15th 2026

desc:
    Every code example of the "Building parts" how-to guide lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each example is written in builder and in algebra mode and the
    two are checked against each other. Run it from its own directory; the
    images are written to ``assets/build_part``.

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
from build123d.topology import Shape

OUTPUT = Path("assets/build_part")
OUTPUT.mkdir(parents=True, exist_ok=True)


def draw(name: str, part: Shape, picked: Shape | None = None) -> None:
    """Write a picture of a part seen from the front right, hidden lines
    dotted, with the edges of one shape picked out in blue."""
    look_at = part.center()
    eye = look_at + Vector(1, -1, 0.7).normalized() * 1000
    visible, hidden = part.drawing_view(eye, (0, 0, 1), look_at=look_at)
    chosen = []
    if picked is not None:
        chosen = list(picked.drawing_view(eye, (0, 0, 1), look_at=look_at).visible)
    everything = Compound(children=[*visible, *hidden, *chosen])
    extent = max(everything.bounding_box().size.X, everything.bounding_box().size.Y)
    svg = ExportSVG(scale=100 / extent, margin=5)
    svg.add_layer("Visible")
    svg.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
    svg.add_layer("Picked", line_color=0x1E4FA3, line_weight=0.7)
    svg.add_shape(list(visible), "Visible")
    if hidden:
        svg.add_shape(list(hidden), "Hidden")
    if chosen:
        svg.add_shape(chosen, "Picked")
    svg.write(OUTPUT / f"{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of an example make the same part?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        first.is_valid
        and second.is_valid
        and abs(first.volume - second.volume) < 1e-6
        and abs(first.area - second.area) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


# ---------------------------------------------------------------------------
# a sketch made solid
# ---------------------------------------------------------------------------

# [extrude]
with BuildPart() as plate:
    with BuildSketch() as outline:
        RectangleRounded(60, 40, 6)
        Circle(8, mode=Mode.SUBTRACT)
    extrude(amount=10)
# [extrude]

builder_result = plate.part

# [extrude_algebra]
outline = RectangleRounded(60, 40, 6) - Circle(8)
plate = extrude(outline, amount=10)
# [extrude_algebra]

assert same(builder_result, plate)
assert abs(plate.bounding_box().size.Z - 10) < 1e-6
draw("part_extrude", plate, outline)

# ---------------------------------------------------------------------------
# add, cut and trim with solids
# ---------------------------------------------------------------------------

# [combine]
with BuildPart() as block:
    Box(60, 40, 20)
    with Locations((0, 0, 10)):
        Cylinder(12, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))  # added
    Cylinder(6, 40, mode=Mode.SUBTRACT)  # a hole through both
    Sphere(36, mode=Mode.INTERSECT)  # keep only what lies inside this sphere
# [combine]

builder_result = block.part

# [combine_algebra]
block = Box(60, 40, 20)
block += Pos(0, 0, 10) * Cylinder(12, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
block -= Cylinder(6, 40)  # a hole through both
block &= Sphere(36)  # keep only what lies inside this sphere
# [combine_algebra]

assert same(builder_result, block)
assert len(block.solids()) == 1
draw("part_combine", block)

# ---------------------------------------------------------------------------
# build on a face of the part
# ---------------------------------------------------------------------------

# [on_face]
with BuildPart() as block:
    Box(60, 40, 20)
    with BuildSketch(block.faces().sort_by(Axis.Z)[-1]) as pad:
        Rectangle(30, 20)
    extrude(amount=5)
    with BuildSketch(block.faces().sort_by(Axis.Z)[-1]) as slot:
        SlotOverall(20, 6)
    extrude(amount=-8, mode=Mode.SUBTRACT)
# [on_face]

builder_result = block.part

# [on_face_algebra]
block = Box(60, 40, 20)
pad = Plane(block.faces().sort_by(Axis.Z)[-1]) * Rectangle(30, 20)
block += extrude(pad, amount=5)
slot = Plane(block.faces().sort_by(Axis.Z)[-1]) * SlotOverall(20, 6)
block -= extrude(slot, amount=-8)
# [on_face_algebra]

assert same(builder_result, block)
# a pad 5 high on the box, with a slot 8 deep in the top of the pad
assert abs(block.bounding_box().max.Z - 15) < 1e-6
draw("part_on_face", block, Compound(children=[pad, slot]))

# ---------------------------------------------------------------------------
# holes
# ---------------------------------------------------------------------------

# [holes]
with BuildPart() as plate:
    Box(80, 50, 10)
    with Locations(plate.faces().sort_by(Axis.Z)[-1]):
        Hole(8)
        with GridLocations(60, 30, 2, 2):
            CounterBoreHole(2.5, 5, 3)
# [holes]

builder_result = plate.part

# [holes_algebra]
plate = Box(80, 50, 10)
top = Plane(plate.faces().sort_by(Axis.Z)[-1])
plate -= top * Hole(8, depth=10)
plate -= [
    top * place * CounterBoreHole(2.5, 5, 3, depth=10)
    for place in GridLocations(60, 30, 2, 2)
]
# [holes_algebra]

assert same(builder_result, plate)
assert len(plate.faces().filter_by(GeomType.CYLINDER)) == 9
draw("part_holes", plate)

# ---------------------------------------------------------------------------
# round and bevel edges
# ---------------------------------------------------------------------------

# [edges]
with BuildPart() as block:
    Box(60, 40, 20)
    fillet(block.edges().filter_by(Axis.Z), radius=6)
    chamfer(block.edges().group_by(Axis.Z)[-1], length=2)
# [edges]

builder_result = block.part

# [edges_algebra]
block = Box(60, 40, 20)
block = fillet(block.edges().filter_by(Axis.Z), radius=6)
block = chamfer(block.edges().group_by(Axis.Z)[-1], length=2)
# [edges_algebra]

assert same(builder_result, block)
assert block.volume < 60 * 40 * 20
draw("part_edges", block)

# ---------------------------------------------------------------------------
# hollow, and cut open
# ---------------------------------------------------------------------------

# [hollow]
with BuildPart() as cup:
    Cylinder(20, 30)
    offset(amount=-3, openings=cup.faces().sort_by(Axis.Z)[-1])
    split(bisect_by=Plane.XZ)
# [hollow]

builder_result = cup.part

# [hollow_algebra]
cup = Cylinder(20, 30)
cup = offset(cup, amount=-3, openings=cup.faces().sort_by(Axis.Z)[-1])
cup = split(cup, bisect_by=Plane.XZ)
# [hollow_algebra]

assert same(builder_result, cup)
# half a cup with a wall 3 thick
assert abs(cup.bounding_box().size.Y - 20) < 1e-6
draw("part_hollow", cup)

# ---------------------------------------------------------------------------
# what is pending
# ---------------------------------------------------------------------------

# [pending]
with BuildPart() as funnel:
    with BuildSketch() as bottom:
        Circle(20)
    with BuildSketch(Plane.XY.offset(30)) as top:
        Rectangle(20, 20)
    loft()
# [pending]

builder_result = funnel.part

# [pending_algebra]
bottom = Circle(20)
top = Plane.XY.offset(30) * Rectangle(20, 20)
funnel = loft([bottom, top])
# [pending_algebra]

assert same(builder_result, funnel)
draw("part_pending", funnel, Compound(children=[bottom, top]))

# [pending_explicit]
with BuildPart() as funnel:
    with BuildSketch(mode=Mode.PRIVATE) as bottom:
        Circle(20)
    with BuildSketch(Plane.XY.offset(30), mode=Mode.PRIVATE) as top:
        Rectangle(20, 20)
    loft([bottom.sketch, top.sketch])
# [pending_explicit]

assert same(builder_result, funnel.part)

# ---------------------------------------------------------------------------
# one part as a tool on another
# ---------------------------------------------------------------------------

# [tool]
with BuildPart() as plug:
    Cone(8, 14, 16, align=(Align.CENTER, Align.CENTER, Align.MIN))

with BuildPart() as mould:
    Box(40, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with Locations((0, 0, 4)):
        insert(plug.part, mode=Mode.SUBTRACT)
# [tool]

builder_result = mould.part

# [tool_algebra]
plug = Cone(8, 14, 16, align=(Align.CENTER, Align.CENTER, Align.MIN))

mould = Box(40, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
mould -= Pos(0, 0, 4) * plug
# [tool_algebra]

assert same(builder_result, mould)

# [tool_nested]
with BuildPart() as mould:
    Box(40, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildPart(Pos(0, 0, 4), mode=Mode.SUBTRACT) as plug:
        Cone(8, 14, 16, align=(Align.CENTER, Align.CENTER, Align.MIN))
# [tool_nested]

assert same(mould.part, builder_result)
# the nested part is still there to be used: placed, and as it was built
assert abs(plug.part.bounding_box().min.Z - 4) < 1e-6
assert abs(plug.part_local.bounding_box().min.Z) < 1e-6
mould, plug = builder_result, plug.part_local
# the cavity is the plug, and the plug itself is not changed
assert abs(mould.volume - (40 * 40 * 20 - plug.volume)) < 1e-6
assert abs(plug.bounding_box().min.Z) < 1e-6
draw("part_tool", mould)

# ---------------------------------------------------------------------------
# the pieces of a part
# ---------------------------------------------------------------------------

# [pieces]
with BuildPart() as block:
    Box(60, 40, 20)
    Cylinder(6, 20, mode=Mode.SUBTRACT)

top = block.faces().sort_by(Axis.Z)[-1]
bore = block.faces().filter_by(GeomType.CYLINDER)
volume = block.part.volume
size = block.part.bounding_box().size
# [pieces]

builder_result = top.area, len(bore), volume, size

# [pieces_algebra]
block = Box(60, 40, 20) - Cylinder(6, 20)

top = block.faces().sort_by(Axis.Z)[-1]
bore = block.faces().filter_by(GeomType.CYLINDER)
volume = block.volume
size = block.bounding_box().size
# [pieces_algebra]

assert abs(builder_result[0] - top.area) < 1e-6 and builder_result[1] == len(bore) == 1
assert (
    abs(builder_result[2] - volume) < 1e-6 and (builder_result[3] - size).length < 1e-6
)

# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------

# [units]
length = 2 * IN
width = 30 * MM
plate = Box(length, width, 3 * MM)
# [units]

assert abs(plate.bounding_box().size.X - 50.8) < 1e-6
assert (MM, CM, M, IN) == (1, 10, 1000, 25.4)
assert abs(FT - 304.8) < 1e-9 and abs(THOU - 0.0254) < 1e-12
