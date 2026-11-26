"""
Offsetting faces documentation examples

name: offsetting_faces.py
by:   Gumyr
date: November 23rd 2026

desc:
    Every code example of the "Offsetting a face on a curved surface" how-to
    guide lives here, between pairs of ``# [name]`` markers that the page
    includes with ``literalinclude``, and this script also renders the SVG
    images the page embeds. Each example is written in builder and in algebra
    mode and the two are checked against each other, as are the claims the
    page makes. Run it from its own directory; the images are written to
    ``assets/offsetting_faces``.

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

from math import pi
from pathlib import Path

from build123d import *
from build123d.geometry import VectorLike
from build123d.topology import Shape

OUTPUT = Path("assets/offsetting_faces")
OUTPUT.mkdir(parents=True, exist_ok=True)

VIEW = (0.4, -1, 0.5)

# ---------------------------------------------------------------------------
# Rendering helpers: parallel projections written as SVG line drawings with
# hidden lines dotted and the offset faces picked out in a second colour,
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
# growing a face
# ---------------------------------------------------------------------------

# [grow]
with BuildSketch() as flat:
    Rectangle(20, 10)

with BuildPart() as can:
    Cylinder(15, 30)
    side = can.faces().filter_by(GeomType.CYLINDER)[0]
    label = side.wrap(flat.sketch.face(), side.location_at(0.75, 0.5))
    offset(label, amount=2)
    thicken(amount=1)
# [grow]

builder_result = can.part

# [grow_algebra]
can = Cylinder(15, 30)
side = can.faces().filter_by(GeomType.CYLINDER)[0]
label = side.wrap(Rectangle(20, 10).face(), side.location_at(0.75, 0.5))
pad = offset(label, 2)
can += thicken(pad, amount=1)
# [grow_algebra]

assert same(builder_result, can)
# the pad is the label grown by 2 all round with rounded corners, measured
# on the surface: a cylinder unrolls, so its area is the flat pattern's
assert pad.face().geom_type == GeomType.CYLINDER
assert abs(pad.area - (24 * 14 - (4 - pi) * 2**2)) < 1e-4
write_layout([seen(can, VIEW, Compound([label, *pad.faces()]))], "grow")

# ---------------------------------------------------------------------------
# shrinking a face
# ---------------------------------------------------------------------------

# [shrink]
with BuildSketch() as flat:
    Rectangle(20, 10)

with BuildPart() as can:
    Cylinder(15, 30)
    side = can.faces().filter_by(GeomType.CYLINDER)[0]
    label = side.wrap(flat.sketch.face(), side.location_at(0.75, 0.5))
    offset(label, amount=-2)
    thicken(amount=-1, mode=Mode.SUBTRACT)
# [shrink]

builder_result = can.part

# [shrink_algebra]
can = Cylinder(15, 30)
side = can.faces().filter_by(GeomType.CYLINDER)[0]
label = side.wrap(Rectangle(20, 10).face(), side.location_at(0.75, 0.5))
window = offset(label, -2)
can -= thicken(window, amount=-1)
# [shrink_algebra]

assert same(builder_result, can)
assert abs(window.area - 16 * 6) < 1e-4
assert can.volume < Cylinder(15, 30).volume
write_layout([seen(can, VIEW, Compound([label, *window.faces()]))], "shrink")

# ---------------------------------------------------------------------------
# square corners
# ---------------------------------------------------------------------------

# [corners]
with BuildSketch() as flat:
    Rectangle(20, 10)

with BuildPart() as can:
    Cylinder(15, 30)
    side = can.faces().filter_by(GeomType.CYLINDER)[0]
    label = side.wrap(flat.sketch.face(), side.location_at(0.75, 0.5))
    offset(label, amount=2, kind=Kind.INTERSECTION)
    thicken(amount=1)
# [corners]

builder_result = can.part

# [corners_algebra]
can = Cylinder(15, 30)
side = can.faces().filter_by(GeomType.CYLINDER)[0]
label = side.wrap(Rectangle(20, 10).face(), side.location_at(0.75, 0.5))
square_pad = offset(label, 2, kind=Kind.INTERSECTION)
can += thicken(square_pad, amount=1)
# [corners_algebra]

assert same(builder_result, can)
assert abs(square_pad.area - 24 * 14) < 1e-4
plain_can = Cylinder(15, 30)
write_layout(
    [
        seen(plain_can, VIEW, Compound([label, *pad.faces()]), label="Kind.ARC"),
        seen(
            plain_can,
            VIEW,
            Compound([label, *square_pad.faces()]),
            label="Kind.INTERSECTION",
        ),
    ],
    "corners",
)

# ---------------------------------------------------------------------------
# a face that goes all the way round
# ---------------------------------------------------------------------------

# [round]
with BuildPart() as knob:
    Cone(12, 8, 20)
    side = knob.faces().filter_by(GeomType.CONE)[0]
    offset(side, amount=-4)
    thicken(amount=-1, mode=Mode.SUBTRACT)
# [round]

builder_result = knob.part

# [round_algebra]
knob = Cone(12, 8, 20)
side = knob.faces().filter_by(GeomType.CONE)[0]
band = offset(side, -4)
knob -= thicken(band, amount=-1)
# [round_algebra]

assert same(builder_result, knob)
# one face, still all the way round, 4 in from each rim along the slope
slope = (20**2 + (12 - 8) ** 2) ** 0.5
assert len(band.faces()) == 1
assert abs(band.area - pi * (12 + 8) * (slope - 2 * 4)) < 1e-4
write_layout([seen(knob, VIEW, hidden=False)], "round")

# ---------------------------------------------------------------------------
# on a sphere, or any other surface
# ---------------------------------------------------------------------------

# [sphere]
with BuildSketch() as flat:
    Rectangle(12, 8)

with BuildPart() as ball:
    Sphere(15)
    skin = ball.faces()[0]
    patch = skin.wrap(flat.sketch.face(), skin.location_at(0.75, 0.5))
    offset(patch, amount=2)
    thicken(amount=1)
# [sphere]

builder_result = ball.part

# [sphere_algebra]
ball = Sphere(15)
skin = ball.faces()[0]
patch = skin.wrap(Rectangle(12, 8).face(), skin.location_at(0.75, 0.5))
grown = offset(patch, 2)
ball += thicken(grown, amount=1)
# [sphere_algebra]

assert same(builder_result, ball)
assert grown.face().geom_type == GeomType.SPHERE
# only rounded corners can be made on a surface that does not unroll
try:
    offset(patch, 2, kind=Kind.INTERSECTION)
    raise AssertionError("mitred corners on a sphere should be refused")
except ValueError:
    pass
write_layout([seen(ball, VIEW, Compound([patch, *grown.faces()]))], "sphere")

# ---------------------------------------------------------------------------
# the parts of a face that a shrink parts
# ---------------------------------------------------------------------------

# [parts]
can = Cylinder(15, 30)
side = can.faces().filter_by(GeomType.CYLINDER)[0]
flat_bar = Pos(-8, 0) * Circle(4) + Rectangle(16, 1.5) + Pos(8, 0) * Circle(4)
bar = side.wrap(flat_bar.face(), side.location_at(0.75, 0.5))
islands = bar.offset_2d(-1)  # a list of faces: the bar has gone
# [parts]

assert len(islands) == 2
# each a disc of radius 3, and a little more where the bar joined it
assert all(0 < island.area - pi * 3**2 < 0.2 for island in islands)
write_layout([seen(can, VIEW, Compound([bar, *islands]))], "parts")
