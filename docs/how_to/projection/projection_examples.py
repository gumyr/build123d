"""
Projection documentation examples

name: projection_examples.py
by:   Gumyr
date: October 20th 2026

desc:
    Every code example in the Projection section of the documentation lives
    here, between pairs of ``# [name]`` markers that the pages include with
    ``literalinclude``, and this script also renders the SVG images those
    pages embed. Run it from its own directory; the images are written to
    ``../assets/projection``. Keeping the examples and their pictures in one
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
from build123d.topology import Shape

OUTPUT = Path("../assets/projection")
OUTPUT.mkdir(parents=True, exist_ok=True)

ISO_VIEW = (1, -1, 0.7)

# ---------------------------------------------------------------------------
# Rendering helpers: parallel projections written as SVG line drawings with
# hidden lines dotted and a result picked out in a second colour, laid out
# as one or more labelled panels.
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


# ---------------------------------------------------------------------------
# onto a plane
# ---------------------------------------------------------------------------
# [plane_faces]
housing = Box(40, 30, 20) - Pos(0, 0, 10) * Cylinder(8, 20)
with BuildSketch() as top_view:
    top = housing.faces().sort_by(Axis.Z)[-1]
    project_to_plane(top, Plane.XY)  # the top, hole included
# [plane_faces]

builder_top_view = top_view.sketch

# [plane_faces_algebra]
housing = Box(40, 30, 20) - Pos(0, 0, 10) * Cylinder(8, 20)
top_view = project_to_plane(housing.faces().sort_by(Axis.Z)[-1], Plane.XY)
# [plane_faces_algebra]

assert abs(builder_top_view.area - top_view.area) < 1e-6

# [plane_silhouette]
with BuildPart() as knob:
    Cylinder(10, 6)
    with Locations((0, 0, 3)):
        Sphere(8)
    with BuildSketch() as footprint:
        project_to_plane(workplane=Plane.XY)  # the part's silhouette, holes included
        Rectangle(4, 30, mode=Mode.SUBTRACT)  # enhance the sketch
    extrude(amount=20, both=True, mode=Mode.INTERSECT)  # and modify the part with it
# [plane_silhouette]

# [plane_silhouette_algebra]
knob = Cylinder(10, 6) + Pos(Z=3) * Sphere(8)
footprint = project_to_plane(knob, Plane.XY)  # the solid casts its silhouette
footprint -= Rectangle(4, 30)  # enhance the sketch
knob &= extrude(footprint, 20, both=True)  # and modify the part with it
# [plane_silhouette_algebra]

# [plane_edges]
with BuildLine() as outline:
    top = housing.faces().sort_by(Axis.Z)[-1]
    project_to_plane(top, Plane.XY)  # a face gives its edges
    corners = project_to_plane(housing.vertices(), Plane.XY)  # returned, not drawn
# [plane_edges]

# [plane_edges_algebra]
top = housing.faces().sort_by(Axis.Z)[-1]
outline = project_to_plane(top.edges(), Plane.XY)  # edges give a Curve
corners = project_to_plane(housing.vertices(), Plane.XY)  # points, as positions
# [plane_edges_algebra]

# [plane_side]
with BuildSketch(Plane.XZ) as side_view:
    project_to_plane(housing, Plane.XZ)  # the side view, standing in XZ
# [plane_side]

builder_side_view = side_view.sketch_local

# [plane_side_algebra]
side_view = project_to_plane(housing, workplane=Plane.XZ)  # in XZ coordinates
points = project_to_plane([Vertex(5, 5, 5), (10, 0, 20)], workplane=Plane.XZ)
# [plane_side_algebra]

assert abs(builder_side_view.area - side_view.area) < 1e-6
assert (
    builder_side_view.bounding_box().size - side_view.bounding_box().size
).length < 1e-6

write_layout(
    [
        seen(housing, ISO_VIEW, label="housing"),
        flat(top_view, label="top face onto the sketch"),
    ],
    "plane_faces",
)
# the knob before the cut, for the picture only
plain_knob = Cylinder(10, 6) + Pos(0, 0, 3) * Sphere(8)
write_layout(
    [
        seen(plain_knob, ISO_VIEW, label="knob"),
        flat(footprint, label="silhouette, slotted"),
        seen(knob, ISO_VIEW, label="knob cut by the sketch"),
    ],
    "plane_silhouette",
)

# ---------------------------------------------------------------------------
# onto a shape
# ---------------------------------------------------------------------------

# [shape_emboss]
with BuildPart() as badge:
    Cylinder(20, 4)
    fillet(badge.edges().sort_by(Axis.Z)[-1], 3)
    with BuildSketch(Plane.XY.offset(10)):
        Text("b3d", 12)
    project_to_shape(direction=(0, 0, -1), hit=Hit.NEAREST)  # onto the domed top
    extrude(amount=-0.5, mode=Mode.SUBTRACT)  # and are engraved into it
# [shape_emboss]

# [shape_emboss_algebra]
blank = Cylinder(20, 4)
blank = fillet(blank.edges().sort_by(Axis.Z)[-1], 3)
letters = Plane.XY.offset(10) * Text("b3d", 12)
on_top = project_to_shape(letters, blank, direction=(0, 0, -1), hit=Hit.NEAREST)
engraved = blank - extrude(on_top, amount=-0.5)  # and are engraved into it
# [shape_emboss_algebra]

assert abs(badge.part.volume - engraved.volume) < 1e-4 * engraved.volume
assert engraved.volume < blank.volume

# [shape_hits]
with BuildPart() as stepped_part:
    Box(40, 40, 4)
    with Locations((0, 0, 8)):
        Box(8, 40, 12)
    with BuildSketch(Plane.XY.offset(30), mode=Mode.PRIVATE) as label:
        Rectangle(24, 24)
    every_surface = project_to_shape(
        label.sketch, direction=(0, 0, -1), mode=Mode.PRIVATE
    )
    in_sight = project_to_shape(
        label.sketch, direction=(0, 0, -1), hit=Hit.VISIBLE, mode=Mode.PRIVATE
    )
# [shape_hits]

builder_hits = every_surface.area, in_sight.area

# [shape_hits_algebra]
stepped = Box(40, 40, 4) + Pos(0, 0, 8) * Box(8, 40, 12)
label = Plane.XY.offset(30) * Rectangle(24, 24)
every_surface = project_to_shape(label, target=stepped, direction=(0, 0, -1))
in_sight = project_to_shape(
    label, target=stepped, direction=(0, 0, -1), hit=Hit.VISIBLE
)
# [shape_hits_algebra]

assert abs(builder_hits[0] - every_surface.area) < 1e-6
assert abs(builder_hits[1] - in_sight.area) < 1e-6
assert in_sight.area < every_surface.area

# [shape_curve]
with BuildPart() as drum_part:
    Cylinder(15, 40)
    with BuildLine() as guide:
        Line((-30, -20), (30, 20))
    on_drum = project_to_shape(direction=(0, 0, -1), hit=Hit.NEAREST)
# [shape_curve]

builder_on_drum = on_drum

# [shape_curve_algebra]
drum = Cylinder(15, 40)
guide = Line((-30, -20), (30, 20))
on_drum = project_to_shape(guide, drum, direction=(0, 0, -1), hit=Hit.NEAREST)
# [shape_curve_algebra]

assert len(builder_on_drum.edges()) == len(on_drum.edges())
assert (
    abs(
        sum(e.length for e in builder_on_drum.edges())
        - sum(e.length for e in on_drum.edges())
    )
    < 1e-6
)

# [index_badge]
with BuildPart() as simple_badge:
    Cylinder(20, 4)
    with BuildSketch(Plane.XY.offset(10)):
        Text("b3d", 12)
    project_to_shape(direction=(0, 0, -1), hit=Hit.NEAREST)  # onto the top
    extrude(amount=-0.5, mode=Mode.SUBTRACT)
# [index_badge]

builder_simple_badge = simple_badge.part

# [index_badge_algebra]
simple_badge = Cylinder(20, 4)
letters = Plane.XY.offset(10) * Text("b3d", 12)
on_top = project_to_shape(letters, simple_badge, direction=(0, 0, -1), hit=Hit.NEAREST)
simple_badge -= extrude(on_top, amount=-0.5)
# [index_badge_algebra]

assert (
    abs(builder_simple_badge.volume - simple_badge.volume) < 1e-4 * simple_badge.volume
)
assert simple_badge.volume < Cylinder(20, 4).volume

# the pictures of the hit options are rendered by projection_shots.py
write_layout([seen(badge.part, ISO_VIEW, label="engraved badge")], "shape_emboss")
write_layout([seen(drum, ISO_VIEW, on_drum, label="line onto a drum")], "shape_curve")

# ---------------------------------------------------------------------------
# a drawing view
# ---------------------------------------------------------------------------

# [view_basic]
bracket = Box(40, 20, 30) - Pos(0, 0, 10) * Box(30, 30, 20) - Cylinder(4, 40)
visible, hidden = bracket.drawing_view((100, -60, 70))
front = bracket.drawing_view((0, -100, 0), look_at=(0, 0, 0))
# [view_basic]

# [view_export]
drawing = ExportSVG(scale=2)
drawing.add_layer("Visible")
drawing.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
drawing.add_shape(visible, "Visible")
drawing.add_shape(hidden, "Hidden")
drawing.write("bracket_view.svg")
# [view_export]

write_layout(
    [
        seen(bracket, (100, -60, 70), label="drawing_view((100, -60, 70))"),
        seen(bracket, (0, -100, 0), label="front"),
    ],
    "view_basic",
)

# ---------------------------------------------------------------------------
# faces along a path
# ---------------------------------------------------------------------------

# [faces_wrap]
can = Cylinder(15, 30)
side = can.faces().filter_by(GeomType.CYLINDER)[0]
ring = Edge.make_circle(15)  # on the side at mid-height, read counterclockwise
label_on_can = side.wrap_faces(Compound.make_text("WRAP", 8).faces(), ring, start=0.75)
# [faces_wrap]

# [faces_project]
block = fillet(Box(40, 40, 20).edges().filter_by(Axis.Z), 10)
rim = block.faces().sort_by(Axis.Z)[-1].outer_wire()  # round the top
corner_path = rim.moved(Pos(Z=-10))  # the same way round, halfway down the sides
label_round_corner = block.project_faces(
    Compound.make_text("CORNER", 8).faces(), corner_path, start=0.325
)
# [faces_project]

write_layout(
    [
        seen(can, ISO_VIEW, Compound(label_on_can), label="wrap_faces on one face"),
        seen(
            block,
            ISO_VIEW,
            Compound(label_round_corner),
            label="project_faces round a corner",
        ),
    ],
    "faces",
)
