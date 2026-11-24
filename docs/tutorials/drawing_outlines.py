"""
Drawing outlines tutorial

name: drawing_outlines.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "Drawing outlines" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/drawing_outlines``.

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

from pathlib import Path

from build123d.topology import Shape

# [setup]
from build123d import *

width, reach = 14, 10
back_height, tip_height = 50, 12
thickness = 5
hole_radius, wire_radius = 2.5, 3
# [setup]

OUTPUT = Path("assets/drawing_outlines")
OUTPUT.mkdir(parents=True, exist_ok=True)


def render_lines(pieces: dict[str, Edge], name: str) -> None:
    """Write named lines and arcs, seen from above, with their names and ends."""
    edges = list(pieces.values())
    size = Compound(children=edges).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=8)
    exporter.add_layer("Lines", line_weight=0.6)
    exporter.add_layer("Ends", fill_color=0x000000, line_weight=0.1)
    exporter.add_layer(
        "Names", fill_color=0x3465A4, line_color=0x3465A4, line_weight=0.1
    )
    exporter.add_shape(edges, layer="Lines")
    for label, edge in pieces.items():
        for end in (edge @ 0, edge @ 1):
            exporter.add_shape(Pos(end.X, end.Y) * Circle(0.7), layer="Ends")
        tangent = edge % 0.5
        beside = (edge @ 0.5) + Vector(-tangent.Y, tangent.X) * 5  # left of travel
        exporter.add_shape(Pos(beside.X, beside.Y) * Text(label, 4.5), layer="Names")
    exporter.write(OUTPUT / f"hook_{name}.svg")


def render_sketch(sketch: Shape, name: str) -> None:
    """Write a sketch, seen from above, as a filled SVG drawing."""
    size = sketch.bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y))
    exporter.add_layer("Sketch", fill_color=0xC4D6E8, line_weight=0.4)
    exporter.add_shape(sketch.faces(), layer="Sketch")
    exporter.write(OUTPUT / f"hook_{name}.svg")


def render_part(part: Shape, name: str, viewpoint=(-70, -150, 120)) -> None:
    """Write a part, seen from above and to one side, as an SVG line drawing."""
    visible, hidden = part.drawing_view(viewpoint)
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y))
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Hidden", line_color=0x969696, line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(OUTPUT / f"hook_{name}.svg")


def size_of(shape: Shape) -> float:
    """A shape's volume, or its area, or the length of its edges."""
    if shape.solids():
        return shape.volume
    if shape.faces():
        return shape.area
    return sum(edge.length for edge in shape.edges())


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    return (
        abs(size_of(first) - size_of(second)) < 1e-6
        and (first.bounding_box().size - second.bounding_box().size).length < 1e-6
        and len(first.edges()) == len(second.edges())
    )


# ---------------------------------------------------------------------------
# Step 2: lines with names
# ---------------------------------------------------------------------------

# [named_builder]
with BuildLine() as outline:
    l1 = Line((0, 0), (0, 50))
    l2 = Line((0, 50), (14, 50))
    l3 = Line((14, 50), (14, 0))
# [named_builder]
builder_result = outline.line

# [named_algebra]
l1 = Line((0, 0), (0, 50))
l2 = Line((0, 50), (14, 50))
l3 = Line((14, 50), (14, 0))
# [named_algebra]

assert same(builder_result, Curve() + [l1, l2, l3])
render_lines({"l1": l1, "l2": l2, "l3": l3}, "named")

# ---------------------------------------------------------------------------
# Step 3: connect by position
# ---------------------------------------------------------------------------

# [connected_builder]
with BuildLine() as outline:
    l1 = Line((0, 0), (0, back_height))
    l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
    l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
# [connected_builder]
assert same(builder_result, outline.line)  # the same three lines as step 2

# [connected_algebra]
l1 = Line((0, 0), (0, back_height))
l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
# [connected_algebra]

assert same(builder_result, Curve() + [l1, l2, l3])

# ---------------------------------------------------------------------------
# Step 4: arcs that leave in the right direction
# ---------------------------------------------------------------------------

# [arcs_builder]
with BuildLine() as outline:
    l1 = Line((0, 0), (0, back_height))
    l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
    l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
    a1 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=reach, arc_size=180)
    l4 = Line(a1 @ 1, a1 @ 1 + (0, tip_height))
    l5 = Line(l4 @ 1, l4 @ 1 + (width, 0))
    l6 = Line(l5 @ 1, l5 @ 1 - (0, tip_height))
    a2 = JernArc(start=l6 @ 1, tangent=l6 % 1, radius=reach + width, arc_size=-180)
# [arcs_builder]
builder_result = outline.line

# [arcs_algebra]
l1 = Line((0, 0), (0, back_height))
l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
a1 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=reach, arc_size=180)
l4 = Line(a1 @ 1, a1 @ 1 + (0, tip_height))
l5 = Line(l4 @ 1, l4 @ 1 + (width, 0))
l6 = Line(l5 @ 1, l5 @ 1 - (0, tip_height))
a2 = JernArc(start=l6 @ 1, tangent=l6 % 1, radius=reach + width, arc_size=-180)
# [arcs_algebra]

pieces = {
    "l1": l1,
    "l2": l2,
    "l3": l3,
    "a1": a1,
    "l4": l4,
    "l5": l5,
    "l6": l6,
    "a2": a2,
}
assert same(builder_result, Curve() + list(pieces.values()))
assert (a2 @ 1 - l1 @ 0).length < 1e-6  # the outline closes
render_lines(pieces, "arcs")

# ---------------------------------------------------------------------------
# Step 5: close it into a face
# ---------------------------------------------------------------------------

# [face_builder]
with BuildSketch() as profile:
    with BuildLine() as outline:
        l1 = Line((0, 0), (0, back_height))
        l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
        l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
        a1 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=reach, arc_size=180)
        l4 = Line(a1 @ 1, a1 @ 1 + (0, tip_height))
        l5 = Line(l4 @ 1, l4 @ 1 + (width, 0))
        l6 = Line(l5 @ 1, l5 @ 1 - (0, tip_height))
        a2 = JernArc(start=l6 @ 1, tangent=l6 % 1, radius=reach + width, arc_size=-180)
    make_face()
    with Locations((width / 2, back_height - width / 2)):
        Circle(hole_radius, mode=Mode.SUBTRACT)
# [face_builder]
builder_result = profile.sketch

# [face_algebra]
l1 = Line((0, 0), (0, back_height))
l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
a1 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=reach, arc_size=180)
l4 = Line(a1 @ 1, a1 @ 1 + (0, tip_height))
l5 = Line(l4 @ 1, l4 @ 1 + (width, 0))
l6 = Line(l5 @ 1, l5 @ 1 - (0, tip_height))
a2 = JernArc(start=l6 @ 1, tangent=l6 % 1, radius=reach + width, arc_size=-180)

profile = make_face([l1, l2, l3, a1, l4, l5, l6, a2])
profile -= Pos(width / 2, back_height - width / 2) * Circle(hole_radius)
# [face_algebra]

assert same(builder_result, profile)
render_sketch(profile, "face")

# ---------------------------------------------------------------------------
# Step 6: extrude it
# ---------------------------------------------------------------------------

# [extrude_builder]
with BuildPart() as hook:
    with BuildSketch() as profile:
        with BuildLine() as outline:
            l1 = Line((0, 0), (0, back_height))
            l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
            l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
            a1 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=reach, arc_size=180)
            l4 = Line(a1 @ 1, a1 @ 1 + (0, tip_height))
            l5 = Line(l4 @ 1, l4 @ 1 + (width, 0))
            l6 = Line(l5 @ 1, l5 @ 1 - (0, tip_height))
            a2 = JernArc(
                start=l6 @ 1, tangent=l6 % 1, radius=reach + width, arc_size=-180
            )
        make_face()
        with Locations((width / 2, back_height - width / 2)):
            Circle(hole_radius, mode=Mode.SUBTRACT)
    extrude(amount=thickness)
# [extrude_builder]
builder_result = hook.part

# [extrude_algebra]
l1 = Line((0, 0), (0, back_height))
l2 = Line(l1 @ 1, l1 @ 1 + (width, 0))
l3 = Line(l2 @ 1, l2 @ 1 - (0, back_height))
a1 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=reach, arc_size=180)
l4 = Line(a1 @ 1, a1 @ 1 + (0, tip_height))
l5 = Line(l4 @ 1, l4 @ 1 + (width, 0))
l6 = Line(l5 @ 1, l5 @ 1 - (0, tip_height))
a2 = JernArc(start=l6 @ 1, tangent=l6 % 1, radius=reach + width, arc_size=-180)

profile = make_face([l1, l2, l3, a1, l4, l5, l6, a2])
profile -= Pos(width / 2, back_height - width / 2) * Circle(hole_radius)
hook = extrude(profile, amount=thickness)
# [extrude_algebra]

assert same(builder_result, hook)
render_part(hook, "extrude")

# ---------------------------------------------------------------------------
# Step 7: the same idea draws a path
# ---------------------------------------------------------------------------

# [sweep_builder]
with BuildPart() as wire_hook:
    with BuildLine() as path:
        p1 = Line((0, 0), (0, -back_height))
        p2 = JernArc(
            start=p1 @ 1, tangent=p1 % 1, radius=reach + width / 2, arc_size=180
        )
        p3 = Line(p2 @ 1, p2 @ 1 + (0, tip_height))
    with BuildSketch(Plane.XZ) as section:
        Circle(wire_radius)
    sweep()
# [sweep_builder]
builder_result = wire_hook.part

# [sweep_algebra]
p1 = Line((0, 0), (0, -back_height))
p2 = JernArc(start=p1 @ 1, tangent=p1 % 1, radius=reach + width / 2, arc_size=180)
p3 = Line(p2 @ 1, p2 @ 1 + (0, tip_height))
path = p1 + p2 + p3

section = Plane.XZ * Circle(wire_radius)
wire_hook = sweep(section, path=path)
# [sweep_algebra]

assert same(builder_result, wire_hook)
render_lines({"p1": p1, "p2": p2, "p3": p3}, "path")
render_part(wire_hook, "sweep")
