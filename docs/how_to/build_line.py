"""
Drawing lines and curves documentation examples

name: build_line.py
by:   Gumyr
date: November 15th 2026

desc:
    Every code example of the "Drawing lines and curves" how-to guide lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each example is written in builder and in algebra mode and the
    two are checked against each other. Run it from its own directory; the
    images are written to ``assets/build_line``.

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

OUTPUT = Path("assets/build_line")
OUTPUT.mkdir(parents=True, exist_ok=True)


def total(shape: Shape) -> float:
    """The length of all the edges of a shape."""
    return sum(edge.length for edge in shape.edges())


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of an example make the same lines?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        len(first.edges()) == len(second.edges())
        and abs(total(first) - total(second)) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


def draw(
    name: str,
    given: list[Shape],
    made: list[Shape],
    construction: list[Shape] | None = None,
    marks: list[Vector] | None = None,
) -> None:
    """Write a picture: what the example starts from in black, what the
    constraint makes in blue, construction geometry dashed, and a small
    circle at each marked point."""
    construction = construction or []
    everything = Compound(children=[*given, *made, *construction])
    size = max(everything.bounding_box().size.X, everything.bounding_box().size.Y)
    svg = ExportSVG(scale=100 / size, margin=5)
    svg.add_layer("Given")
    svg.add_layer("Made", line_color=0x1E4FA3, line_weight=0.7)
    svg.add_layer("Construction", line_color=0x636363, line_type=LineType.ISO_DASH)
    svg.add_layer("Marks", line_color=0x636363)
    for layer, shapes in (
        ("Construction", construction),
        ("Given", given),
        ("Made", made),
    ):
        if shapes:
            svg.add_shape(shapes, layer)
    for point in marks or []:
        svg.add_shape(Pos(point) * Circle(size / 80).edge(), "Marks")
    svg.write(OUTPUT / f"{name}.svg")


def draw_3d(name: str, scene: Shape, picked: Shape | None = None) -> None:
    """Write a picture of a 3D scene seen from the front right, hidden lines
    dotted, with the edges of one shape picked out in blue and the world
    axes drawn from the origin."""
    size = max(scene.bounding_box().size)
    world = [
        Line((0, 0, 0), end)
        for end in ((size / 3, 0, 0), (0, size / 3, 0), (0, 0, size / 3))
    ]
    whole = Compound(children=[scene, *world])
    look_at = whole.center()
    eye = look_at + Vector(1, -1, 0.7).normalized() * 1000
    visible, hidden = whole.drawing_view(eye, (0, 0, 1), look_at=look_at)
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


# ---------------------------------------------------------------------------
# connected lines and arcs
# ---------------------------------------------------------------------------

# [connect]
with BuildLine() as outline:
    l1 = Line((0, 0), (40, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, 15))
    l3 = RadiusArc(l2 @ 1, (0, 15), -30)
    l4 = Line(l3 @ 1, l1 @ 0)
# [connect]

builder_result = outline.line

# [connect_algebra]
l1 = Line((0, 0), (40, 0))
l2 = Line(l1 @ 1, l1 @ 1 + (0, 15))
l3 = RadiusArc(l2 @ 1, (0, 15), -30)
l4 = Line(l3 @ 1, l1 @ 0)
outline = l1 + l2 + l3 + l4
# [connect_algebra]

assert same(builder_result, outline)
assert Wire(outline.edges()).is_closed and len(outline.edges()) == 4
draw("lines_connect", [l1, l2, l4], [l3], marks=[l1 @ 0, l1 @ 1, l2 @ 1, l3 @ 1])

# ---------------------------------------------------------------------------
# half an outline, mirrored
# ---------------------------------------------------------------------------

# [mirror]
with BuildLine() as club:
    l0 = Line((0, -188), (76, -188))
    b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
    b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
    b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
    b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
    mirror(about=Plane.YZ)
# [mirror]

builder_result = club.line

# [mirror_algebra]
l0 = Line((0, -188), (76, -188))
b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
half = l0 + b0 + b1 + b2 + b3
club = half + mirror(half, about=Plane.YZ)
# [mirror_algebra]

# The same outline. In algebra mode ``+`` joins pieces that run on smoothly
# into one edge, so the two halves of the base and of the top lobe merge:
# eight edges where the builder keeps ten.
assert len(builder_result.edges()) == 10 and len(club.edges()) == 8
assert abs(total(builder_result) - total(club)) < 1e-5 * total(club)
assert (builder_result.bounding_box().size - club.bounding_box().size).length < 1e-6
draw("lines_mirror", list(half.edges()), list(mirror(half, about=Plane.YZ).edges()))

# ---------------------------------------------------------------------------
# an outline closed into a face
# ---------------------------------------------------------------------------

# [face]
with BuildSketch() as club_face:
    with BuildLine() as club:
        l0 = Line((0, -188), (76, -188))
        b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
        b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
        b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
        b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
        mirror(about=Plane.YZ)
    make_face()
# [face]

builder_result = club_face.sketch

# [face_algebra]
l0 = Line((0, -188), (76, -188))
b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
half = l0 + b0 + b1 + b2 + b3
club = half + mirror(half, about=Plane.YZ)
club_face = make_face(club)
# [face_algebra]

assert abs(builder_result.area - club_face.area) < 1e-3 * club_face.area
assert len(club_face.faces()) == 1

# [hull]
with BuildSketch() as link:
    with BuildLine() as ends:
        CenterArc((0, 0), 5, 0, 360)
        CenterArc((20, 0), 3, 0, 360)
    make_hull()
# [hull]

builder_result = link.sketch

# [hull_algebra]
ends = CenterArc((0, 0), 5, 0, 360) + CenterArc((20, 0), 3, 0, 360)
link = make_hull(ends.edges())
# [hull_algebra]

assert abs(builder_result.area - link.area) < 1e-6
# the hull wraps both circles
assert abs(link.bounding_box().size.X - 28) < 1e-6
draw("lines_hull", list(ends.edges()), list(link.edges()))

# ---------------------------------------------------------------------------
# a path for a sweep
# ---------------------------------------------------------------------------

# [path]
with BuildPart() as pipe:
    with BuildLine() as path:
        l1 = RadiusArc((0, 0), (10, 10), 20)
        l2 = Spline(l1 @ 1, (20, 30), (30, 30), tangents=(l1 % 1, (0, -1)))
        l3 = Line(l2 @ 1, (30, 0))
    with BuildSketch(path.line ^ 0) as section:
        Circle(1)
    sweep()
# [path]

builder_result = pipe.part

# [path_algebra]
l1 = RadiusArc((0, 0), (10, 10), 20)
l2 = Spline(l1 @ 1, (20, 30), (30, 30), tangents=(l1 % 1, (0, -1)))
l3 = Line(l2 @ 1, (30, 0))
path = l1 + l2 + l3
section = (path ^ 0) * Circle(1)
pipe = sweep(section, path)
# [path_algebra]

assert abs(builder_result.volume - pipe.volume) < 1e-6 and pipe.is_valid
draw_3d("lines_path", pipe, path)

# ---------------------------------------------------------------------------
# on another plane, and off the plane
# ---------------------------------------------------------------------------

# [plane]
with BuildLine(Plane.YZ) as upright:
    l1 = Line((0, 0), (20, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, 15))
    l3 = RadiusArc(l2 @ 1, (0, 15), -30)
# [plane]

builder_result, builder_local = upright.line, upright.line_local

# [plane_algebra]
l1 = Line((0, 0), (20, 0))
l2 = Line(l1 @ 1, l1 @ 1 + (0, 15))
l3 = RadiusArc(l2 @ 1, (0, 15), -30)
upright = Plane.YZ * (l1 + l2 + l3)
# [plane_algebra]

assert same(builder_result, upright)
# drawn flat, published standing in the YZ plane
assert builder_local.bounding_box().size.Z < 1e-6
assert upright.bounding_box().size.X < 1e-6 and upright.bounding_box().size.Z > 15
draw_3d("lines_plane", Compound(children=[l1 + l2 + l3]), upright)

# [space]
with BuildLine() as rail:
    l1 = Polyline((0, 0, 0), (20, 0, 0), (20, 15, 10))
    l2 = Spline(l1 @ 1, (10, 25, 15), (0, 20, 30), tangents=(l1 % 1, (-1, 0, 0)))
# [space]

builder_result = rail.line

# [space_algebra]
l1 = Polyline((0, 0, 0), (20, 0, 0), (20, 15, 10))
l2 = Spline(l1 @ 1, (10, 25, 15), (0, 20, 30), tangents=(l1 % 1, (-1, 0, 0)))
rail = l1 + l2
# [space_algebra]

assert same(builder_result, rail)
assert rail.bounding_box().size.Z > 29
draw_3d("lines_space", Compound(children=[Box(20, 25, 30, align=Align.MIN)]), rail)

# ---------------------------------------------------------------------------
# rounded and bevelled corners
# ---------------------------------------------------------------------------

# [corners]
with BuildLine() as tray:
    Polyline((0, 20), (0, 0), (40, 0), (40, 20))
    fillet(tray.vertices().group_by(Axis.Y)[0], radius=6)
# [corners]

builder_result = tray.line

# [corners_algebra]
tray = Polyline((0, 20), (0, 0), (40, 0), (40, 20))
tray = fillet(tray.vertices().group_by(Axis.Y)[0], radius=6)
# [corners_algebra]

assert same(builder_result, tray)
assert len(tray.edges()) == 5 and len(tray.edges().filter_by(GeomType.CIRCLE)) == 2

# [corners_polyline]
tray = FilletPolyline((0, 20), (0, 0), (40, 0), (40, 20), radius=6)
# [corners_polyline]

assert same(builder_result, tray)
draw(
    "lines_corners",
    list(tray.edges().filter_by(GeomType.LINE)),
    list(tray.edges().filter_by(GeomType.CIRCLE)),
)

# ---------------------------------------------------------------------------
# construction lines
# ---------------------------------------------------------------------------

# [construction]
with BuildLine() as slot:
    # construction: the centre line of the slot, and half its width across
    guide = PolarLine((0, 0), 40, 30, mode=Mode.PRIVATE)
    across = (guide % 0).rotate(Axis.Z, 90) * 6

    l1 = Line(guide @ 0 + across, guide @ 1 + across)
    l2 = ThreePointArc(l1 @ 1, guide @ 1 + (guide % 1) * 6, guide @ 1 - across)
    l3 = Line(l2 @ 1, guide @ 0 - across)
    l4 = ThreePointArc(l3 @ 1, guide @ 0 - (guide % 0) * 6, l1 @ 0)
# [construction]

builder_result = slot.line

# [construction_algebra]
# construction: the centre line of the slot, and half its width across
guide = PolarLine((0, 0), 40, 30)
across = (guide % 0).rotate(Axis.Z, 90) * 6

l1 = Line(guide @ 0 + across, guide @ 1 + across)
l2 = ThreePointArc(l1 @ 1, guide @ 1 + (guide % 1) * 6, guide @ 1 - across)
l3 = Line(l2 @ 1, guide @ 0 - across)
l4 = ThreePointArc(l3 @ 1, guide @ 0 - (guide % 0) * 6, l1 @ 0)
slot = l1 + l2 + l3 + l4
# [construction_algebra]

assert same(builder_result, slot)
# the guide is not part of the result, and the outline is closed
assert len(builder_result.edges()) == 4 and Wire(slot.edges()).is_closed
draw("lines_construction", [], [l1, l2, l3, l4], construction=[guide])

# ---------------------------------------------------------------------------
# the pieces of a line
# ---------------------------------------------------------------------------

# [pieces]
with BuildLine() as outline:
    l1 = Line((0, 0), (40, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, 15))
    l3 = RadiusArc(l2 @ 1, (0, 15), -30)
    l4 = Line(l3 @ 1, l1 @ 0)

arcs = outline.edges().filter_by(GeomType.CIRCLE)
corners = outline.vertices()
perimeter = outline.wire().length
# [pieces]

builder_result = len(arcs), len(corners), perimeter

# [pieces_algebra]
l1 = Line((0, 0), (40, 0))
l2 = Line(l1 @ 1, l1 @ 1 + (0, 15))
l3 = RadiusArc(l2 @ 1, (0, 15), -30)
l4 = Line(l3 @ 1, l1 @ 0)
outline = l1 + l2 + l3 + l4

arcs = outline.edges().filter_by(GeomType.CIRCLE)
corners = outline.vertices()
perimeter = outline.wire().length
# [pieces_algebra]

assert builder_result[:2] == (len(arcs), len(corners)) == (1, 4)
assert abs(builder_result[2] - perimeter) < 1e-6
