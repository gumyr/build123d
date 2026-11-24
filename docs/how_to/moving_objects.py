"""
Moving and rotating objects documentation examples

name: moving_objects.py
by:   Gumyr
date: November 15th 2026

desc:
    Every code example of the "Moving and rotating objects" how-to guide
    lives here, between pairs of ``# [name]`` markers that the page includes
    with ``literalinclude``, and this script also renders the SVG images the
    page embeds. Each example is written in builder and in algebra mode and
    the two are checked against each other. Run it from its own directory;
    the images are written to ``assets/moving_objects``.

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

OUTPUT = Path("assets/moving_objects")
OUTPUT.mkdir(parents=True, exist_ok=True)

ISO_VIEW = (1, -1, 0.7)

# ---------------------------------------------------------------------------
# Rendering helpers: parallel projections written as SVG line drawings. Each
# picture shows the world axes and the object where it started in grey, and
# where it ends up in a second colour.
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


def moved_picture(
    before: Shape | None, after: Shape, label: str | None = None, axes: float = 30
) -> Panel:
    """A panel with the world axes, the object as it started and, picked out,
    the object as it ends up."""
    world = [Line((0, 0, 0), end) for end in ((axes, 0, 0), (0, axes, 0), (0, 0, axes))]
    scene = Compound(children=world + ([before] if before is not None else []))
    return seen(scene, ISO_VIEW, after, label=label, hidden=False)


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of an example make the same shape?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-6
        and abs(first.area - second.area) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


start = Box(30, 10, 5)  # the bar most examples move, as it is made at the origin

# ---------------------------------------------------------------------------
# move
# ---------------------------------------------------------------------------

# [move]
with BuildPart() as bar:
    with Locations((20, 30, 0)):
        Box(30, 10, 5)
# [move]

builder_result = bar.part

# [move_algebra]
bar = Pos(20, 30, 0) * Box(30, 10, 5)
# [move_algebra]

assert same(builder_result, bar)
assert (bar.center() - Vector(20, 30, 0)).length < 1e-6
write_layout([moved_picture(start, bar)], "move")

# ---------------------------------------------------------------------------
# turn about its own centre
# ---------------------------------------------------------------------------

# [turn]
with BuildPart() as bar:
    with Locations((20, 30, 0)):
        Box(30, 10, 5, rotation=(0, 0, 30))
# [turn]

builder_result = bar.part

# [turn_algebra]
bar = Pos(20, 30, 0) * Rot(Z=30) * Box(30, 10, 5)
# [turn_algebra]

assert same(builder_result, bar)
# turned where it stands: the centre is where it was put
assert (bar.center() - Vector(20, 30, 0)).length < 1e-6
write_layout([moved_picture(start, bar)], "turn")

# ---------------------------------------------------------------------------
# turn about an axis somewhere else
# ---------------------------------------------------------------------------

# [hinge]
with BuildPart() as lid:
    Box(30, 20, 2, align=Align.MIN)

hinge = Axis((0, 0, 0), (0, 1, 0))
opened = lid.part.rotate(hinge, -40)
# [hinge]

builder_result = opened

# [hinge_algebra]
lid = Box(30, 20, 2, align=Align.MIN)

hinge = Axis((0, 0, 0), (0, 1, 0))
opened = lid.rotate(hinge, -40)
# [hinge_algebra]

assert same(builder_result, opened)
# the lid is lifted about the edge that lies on the Y axis, and is not changed
assert opened.bounding_box().max.Z > 19 and lid.bounding_box().max.Z < 2 + 1e-6
write_layout([moved_picture(lid, opened, axes=25)], "hinge")

# ---------------------------------------------------------------------------
# turn then move, or move then turn
# ---------------------------------------------------------------------------

# [order]
with BuildPart() as turned_in_place:
    with Locations(Pos(40, 0, 0) * Rot(Z=30)):
        Box(30, 10, 5)

with BuildPart() as swung_round:
    with Locations(Rot(Z=30) * Pos(40, 0, 0)):
        Box(30, 10, 5)
# [order]

builder_results = turned_in_place.part, swung_round.part

# [order_algebra]
turned_in_place = Pos(40, 0, 0) * Rot(Z=30) * Box(30, 10, 5)
swung_round = Rot(Z=30) * Pos(40, 0, 0) * Box(30, 10, 5)
# [order_algebra]

assert same(builder_results[0], turned_in_place)
assert same(builder_results[1], swung_round)
assert (turned_in_place.center() - Vector(40, 0, 0)).length < 1e-6
assert (swung_round.center() - Vector(40, 0, 0).rotate(Axis.Z, 30)).length < 1e-6
write_layout(
    [
        moved_picture(start, turned_in_place, label="Pos * Rot * bar", axes=40),
        moved_picture(start, swung_round, label="Rot * Pos * bar", axes=40),
    ],
    "order",
)

# ---------------------------------------------------------------------------
# three angles at once
# ---------------------------------------------------------------------------

# [angles]
with BuildPart() as bar:
    Box(30, 10, 5, rotation=(90, 0, 45))
# [angles]

builder_result = bar.part

# [angles_algebra]
bar = Rot(90, 0, 45) * Box(30, 10, 5)
# [angles_algebra]

assert same(builder_result, bar)

# [angles_chain]
one_step = Rot(90, 30, 45) * Box(30, 10, 5)
three_steps = Rot(X=90) * Rot(Y=30) * Rot(Z=45) * Box(30, 10, 5)
# [angles_chain]

assert same(one_step, three_steps)
assert not same(one_step, Rot(Z=45) * Rot(Y=30) * Rot(X=90) * Box(30, 10, 5))
write_layout([moved_picture(start, bar)], "angles")

# ---------------------------------------------------------------------------
# at a rotated location
# ---------------------------------------------------------------------------

# [location]
left = Location((-20, 30, 0), (0, 0, -30))
right = Location((20, 30, 0), (0, 0, 30))

with BuildPart() as bars:
    with Locations(left, right):
        Box(30, 10, 5)
# [location]

builder_result = bars.part

# [location_algebra]
left = Location((-20, 30, 0), (0, 0, -30))
right = Location((20, 30, 0), (0, 0, 30))

bars = left * Box(30, 10, 5) + right * Box(30, 10, 5)
# [location_algebra]

assert same(builder_result, bars)
# a Location is a position and a rotation in one
assert same(right * Box(30, 10, 5), Pos(20, 30, 0) * Rot(Z=30) * Box(30, 10, 5))
write_layout([moved_picture(start, bars)], "location")

# ---------------------------------------------------------------------------
# at the vertices of a part
# ---------------------------------------------------------------------------

# [vertices]
with BuildPart() as plate:
    Box(60, 40, 10)
    top = plate.faces().sort_by(Axis.Z)[-1]
    with Locations(*top.vertices()):
        Cylinder(4, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
# [vertices]

builder_result = plate.part

# [vertices_algebra]
plate = Box(60, 40, 10)
top = plate.faces().sort_by(Axis.Z)[-1]
plate += [
    Pos(corner) * Cylinder(4, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for corner in top.vertices()
]
# [vertices_algebra]

assert same(builder_result, plate)
# a post stands on each of the four corners of the top
assert abs(plate.bounding_box().size.X - 68) < 1e-6
assert abs(plate.bounding_box().max.Z - 11) < 1e-6
posts = Compound(
    [
        Pos(corner) * Cylinder(4, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for corner in top.vertices()
    ]
)
write_layout([moved_picture(Box(60, 40, 10), posts, axes=20)], "vertices")

# ---------------------------------------------------------------------------
# copies round an axis
# ---------------------------------------------------------------------------

# [polar]
with BuildPart() as spokes:
    with PolarLocations(25, 6):
        Box(12, 4, 5)
# [polar]

builder_result = spokes.part

# [polar_algebra]
spokes = Part() + [place * Box(12, 4, 5) for place in PolarLocations(25, 6)]
# [polar_algebra]

assert same(builder_result, spokes) and len(spokes.solids()) == 6
write_layout([moved_picture(Box(12, 4, 5), spokes)], "polar")

# ---------------------------------------------------------------------------
# mirrored in a face
# ---------------------------------------------------------------------------

# [mirror]
with BuildPart() as pair:
    with BuildSketch() as outline:
        RegularPolygon(20, 5)
    extrude(amount=10)
    side = pair.faces().sort_by(Axis.Y)[0]
    mirror(about=Plane(side))
# [mirror]

builder_result = pair.part

# [mirror_algebra]
half = extrude(RegularPolygon(20, 5), amount=10)
side = half.faces().sort_by(Axis.Y)[0]
pair = half + mirror(half, about=Plane(side))
# [mirror_algebra]

assert same(builder_result, pair)
# two pentagons joined on the face they were mirrored in: twice the volume
assert abs(pair.volume - 2 * half.volume) < 1e-6 and len(pair.solids()) == 1
write_layout([moved_picture(half, pair - half, axes=25)], "mirror")

# ---------------------------------------------------------------------------
# something that is already in place
# ---------------------------------------------------------------------------

# [placed]
with BuildPart() as tooth:
    with Locations((0, 0, 20)):
        Box(6, 4, 8)

teeth = [Rot(X=angle) * tooth.part for angle in range(0, 360, 60)]
# [placed]

builder_result = Compound(teeth)

# [placed_algebra]
tooth = Pos(0, 0, 20) * Box(6, 4, 8)

teeth = [Rot(X=angle) * tooth for angle in range(0, 360, 60)]
# [placed_algebra]

assert same(builder_result, Compound(teeth))
# every tooth is still 20 from the X axis
assert all(abs(Vector(0, t.center().Y, t.center().Z).length - 20) < 1e-6 for t in teeth)

# [placed_wrong]
teeth = Plane.YZ * PolarLocations(0, 6) * tooth  # not what was wanted
# [placed_wrong]

# the teeth have been laid over onto Plane.YZ: they now sit out along X
assert all(abs(t.center().X - 20) < 1e-6 for t in teeth)
wrong = Compound(teeth)
right = Compound([Rot(X=angle) * tooth for angle in range(0, 360, 60)])
write_layout(
    [
        moved_picture(tooth, right, label="Rot(X=angle)"),
        moved_picture(tooth, wrong, label="Plane.YZ * PolarLocations"),
    ],
    "placed",
    gap_fraction=0.5,
)

# [spin]
spun = tooth.rotate(Axis(tooth.center(), (0, 0, 1)), 45)
# [spin]

assert (spun.center() - tooth.center()).length < 1e-6
