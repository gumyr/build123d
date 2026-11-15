"""
Sketching documentation examples

name: build_sketch.py
by:   Gumyr
date: November 15th 2026

desc:
    Every code example of the "Sketching" how-to guide lives here, between
    pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each example is written in builder and in algebra mode and the
    two are checked against each other. Run it from its own directory; the
    images are written to ``assets/build_sketch``.

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

OUTPUT = Path("assets/build_sketch")
OUTPUT.mkdir(parents=True, exist_ok=True)


def draw(
    name: str,
    sketch: Shape,
    construction: list[Shape] | None = None,
    before: Shape | None = None,
) -> None:
    """Write a picture of a sketch: its faces filled, construction geometry
    dashed, and, where given, the outline it was made from in grey."""
    construction = construction or []
    extras = [*construction, *([before] if before is not None else [])]
    everything = Compound(children=[sketch, *extras])
    size = max(everything.bounding_box().size.X, everything.bounding_box().size.Y)
    svg = ExportSVG(scale=100 / size, margin=5)
    svg.add_layer("Before", line_color=0x8A8A8A)
    svg.add_layer("Sketch", fill_color=0xD6E2F5, line_color=0x1E4FA3, line_weight=0.5)
    svg.add_layer("Construction", line_color=0x636363, line_type=LineType.ISO_DASH)
    if before is not None:
        svg.add_shape(list(before.edges()), "Before")
    svg.add_shape(list(sketch.faces()), "Sketch")
    if construction:
        svg.add_shape(
            [e for shape in construction for e in shape.edges()], "Construction"
        )
    svg.write(OUTPUT / f"{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of an example make the same sketch?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        len(first.faces()) == len(second.faces())
        and abs(first.area - second.area) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


# ---------------------------------------------------------------------------
# combine shapes
# ---------------------------------------------------------------------------

# [combine]
with BuildSketch() as plate:
    Rectangle(60, 40)
    with Locations((30, 0)):
        Circle(20)  # added to the rectangle
    Circle(10, mode=Mode.SUBTRACT)  # a hole
    Circle(45, mode=Mode.INTERSECT)  # keep only what lies inside this circle
# [combine]

builder_result = plate.sketch

# [combine_algebra]
plate = Rectangle(60, 40) + Pos(30, 0) * Circle(20)  # added to the rectangle
plate -= Circle(10)  # a hole
plate &= Circle(45)  # keep only what lies inside this circle
# [combine_algebra]

assert same(builder_result, plate)
assert len(plate.faces()) == 1 and len(plate.face().inner_wires()) == 1
draw("sketch_combine", plate, construction=[Circle(45)])

# ---------------------------------------------------------------------------
# position and align
# ---------------------------------------------------------------------------

# [position]
with BuildSketch() as panel:
    Rectangle(80, 50, align=Align.MIN)
    with Locations((40, 25)):
        Rectangle(30, 10, rotation=30, mode=Mode.SUBTRACT)
        with GridLocations(60, 30, 2, 2):
            Circle(3, mode=Mode.SUBTRACT)
# [position]

builder_result = panel.sketch

# [position_algebra]
panel = Rectangle(80, 50, align=Align.MIN)
panel -= Pos(40, 25) * Rectangle(30, 10, rotation=30)
panel -= [Pos(40, 25) * place * Circle(3) for place in GridLocations(60, 30, 2, 2)]
# [position_algebra]

assert same(builder_result, panel)
# the corner of the panel is at the origin and there are five openings
assert panel.bounding_box().min.length < 1e-6
assert len(panel.face().inner_wires()) == 5
draw("sketch_position", panel)

# ---------------------------------------------------------------------------
# an outline no object makes
# ---------------------------------------------------------------------------

# [outline]
with BuildSketch() as fin:
    with BuildLine() as edge:
        l1 = Line((0, 0), (40, 0))
        l2 = Line(l1 @ 1, l1 @ 1 + (0, 10))
        l3 = RadiusArc(l2 @ 1, (0, 30), 50)
        l4 = Line(l3 @ 1, l1 @ 0)
    make_face()
    with Locations((12, 12)):
        Circle(5, mode=Mode.SUBTRACT)
# [outline]

builder_result = fin.sketch

# [outline_algebra]
l1 = Line((0, 0), (40, 0))
l2 = Line(l1 @ 1, l1 @ 1 + (0, 10))
l3 = RadiusArc(l2 @ 1, (0, 30), 50)
l4 = Line(l3 @ 1, l1 @ 0)
fin = make_face(l1 + l2 + l3 + l4)
fin -= Pos(12, 12) * Circle(5)
# [outline_algebra]

assert same(builder_result, fin)
assert len(fin.face().inner_wires()) == 1
draw("sketch_outline", fin)

# ---------------------------------------------------------------------------
# round or bevel corners
# ---------------------------------------------------------------------------

# [corners]
with BuildSketch() as tab:
    Rectangle(40, 20)
    fillet(tab.vertices().group_by(Axis.X)[-1], radius=6)
    chamfer(tab.vertices().group_by(Axis.X)[0], length=4)
# [corners]

builder_result = tab.sketch

# [corners_algebra]
tab = Rectangle(40, 20)
tab = fillet(tab.vertices().group_by(Axis.X)[-1], radius=6)
tab = chamfer(tab.vertices().group_by(Axis.X)[0], length=4)
# [corners_algebra]

assert same(builder_result, tab)
assert len(tab.edges()) == 8 and len(tab.edges().filter_by(GeomType.CIRCLE)) == 2
draw("sketch_corners", tab, before=Rectangle(40, 20))

# ---------------------------------------------------------------------------
# grow, shrink, or make a frame
# ---------------------------------------------------------------------------

# [offset]
with BuildSketch() as gasket:
    SlotOverall(50, 20)
    offset(amount=-4, mode=Mode.SUBTRACT)
# [offset]

builder_result = gasket.sketch

# [offset_algebra]
outside = SlotOverall(50, 20)
gasket = outside - offset(outside, amount=-4)
# [offset_algebra]

assert same(builder_result, gasket)
# a frame 4 wide all the way round
assert len(gasket.face().inner_wires()) == 1
assert abs(gasket.face().inner_wires()[0].bounding_box().size.Y - 12) < 1e-6
draw("sketch_offset", gasket)

# ---------------------------------------------------------------------------
# draw half and mirror it
# ---------------------------------------------------------------------------

# [mirror]
with BuildSketch() as link:
    Rectangle(15, 6, align=(Align.MIN, Align.CENTER))
    with Locations((15, 0)):
        Circle(8)
        Circle(4, mode=Mode.SUBTRACT)
    mirror(about=Plane.YZ)
# [mirror]

builder_result = link.sketch

# [mirror_algebra]
half = Rectangle(15, 6, align=(Align.MIN, Align.CENTER)) + Pos(15, 0) * Circle(8)
half -= Pos(15, 0) * Circle(4)
link = half + mirror(half, about=Plane.YZ)
# [mirror_algebra]

assert same(builder_result, link)
assert len(link.faces()) == 1 and len(link.face().inner_wires()) == 2
draw("sketch_mirror", link, construction=[Line((0, -12), (0, 12))])

# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------

# [text]
with BuildSketch() as label:
    RectangleRounded(70, 20, 4)
    Text("build123d", 10, mode=Mode.SUBTRACT)
# [text]

builder_result = label.sketch

# [text_algebra]
label = RectangleRounded(70, 20, 4) - Text("build123d", 10)
# [text_algebra]

assert same(builder_result, label)
assert label.area < RectangleRounded(70, 20, 4).area
draw("sketch_text", label)

# ---------------------------------------------------------------------------
# construction geometry
# ---------------------------------------------------------------------------

# [construction]
with BuildSketch() as flange:
    Circle(30)
    bolt_circle = RegularPolygon(22, 6, mode=Mode.PRIVATE)
    with Locations(*bolt_circle.vertices()):
        Circle(3, mode=Mode.SUBTRACT)
# [construction]

builder_result = flange.sketch

# [construction_algebra]
bolt_circle = RegularPolygon(22, 6)
flange = Circle(30) - [Pos(corner) * Circle(3) for corner in bolt_circle.vertices()]
# [construction_algebra]

assert same(builder_result, flange)
# six holes, and no hexagon
assert len(flange.face().inner_wires()) == 6
draw("sketch_construction", flange, construction=[bolt_circle])

# ---------------------------------------------------------------------------
# start from a face of the part
# ---------------------------------------------------------------------------

# [from_face]
with BuildPart() as tray:
    Box(60, 40, 10)
    top = tray.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(top) as recess:
        insert(top)
        offset(amount=-4)
    extrude(amount=-6, mode=Mode.SUBTRACT)
# [from_face]

builder_result, builder_sketch = tray.part, recess.sketch

# [from_face_algebra]
tray = Box(60, 40, 10)
top = tray.faces().sort_by(Axis.Z)[-1]
recess = offset(top, amount=-4)
tray -= extrude(recess, amount=-6)
# [from_face_algebra]

assert abs(builder_result.volume - tray.volume) < 1e-6
assert abs(builder_sketch.area - recess.area) < 1e-6
# a recess 4 in from every side of the top, 6 deep
assert abs(tray.volume - (60 * 40 * 10 - 52 * 32 * 6)) < 60

# ---------------------------------------------------------------------------
# where a sketch ends up
# ---------------------------------------------------------------------------

# [local]
with GridLocations(20, 20, 2, 2):
    with BuildSketch() as pads:
        Rectangle(8, 4)

drawn = pads.sketch_local  # one rectangle, at the origin
placed = pads.sketch  # four rectangles, one at each place in the grid
# [local]

assert len(drawn.faces()) == 1 and len(placed.faces()) == 4
assert abs(drawn.bounding_box().size.X - 8) < 1e-6
assert abs(placed.bounding_box().size.X - 28) < 1e-6

# ---------------------------------------------------------------------------
# the pieces of a sketch
# ---------------------------------------------------------------------------

# [pieces]
with BuildSketch() as plate:
    Rectangle(60, 40)
    Circle(10, mode=Mode.SUBTRACT)

corners = plate.vertices()
hole = plate.edges().filter_by(GeomType.CIRCLE)
area = plate.sketch.area
# [pieces]

builder_result = len(corners), len(hole), area

# [pieces_algebra]
plate = Rectangle(60, 40) - Circle(10)

corners = plate.vertices()
hole = plate.edges().filter_by(GeomType.CIRCLE)
area = plate.area
# [pieces_algebra]

assert builder_result[:2] == (len(corners), len(hole))
assert abs(builder_result[2] - area) < 1e-6 and len(hole) == 1
