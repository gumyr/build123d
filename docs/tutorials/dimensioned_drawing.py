"""
From a drawing to a sketch tutorial

name: dimensioned_drawing.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "From a drawing to a sketch" tutorial lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/dimensioned_drawing``.

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

overall_width, overall_height = 81, 57
lobe_height, lobe_chamfer = 32, 7
hole_diameter, hole_from_left, hole_from_bottom = 14, 14, 14
slope_angle = 10
top_radius, top_flat, top_chamfer = 19, 29, 5
side_height = 24
foot_drop, foot_inset = 19, 29
neck_radius, neck_fillet = 29, 5

left, right = -hole_from_left, overall_width - hole_from_left
lobe_bottom, lobe_top = -hole_from_bottom, lobe_height - hole_from_bottom
bottom = lobe_bottom - foot_drop
top = bottom + overall_height
# [setup]

OUTPUT = Path("assets/dimensioned_drawing")
OUTPUT.mkdir(parents=True, exist_ok=True)

STEPS: list[tuple] = []  # pictures, drawn at the end


def picture(
    name: str, done: dict, new: dict, construction: dict, places: dict | None = None
) -> None:
    """Remember one step's lines; they are drawn once the outline is known.

    ``places`` puts a name at a chosen point where the default, beside the
    middle of its line, would collide with something.
    """
    STEPS.append((name, dict(done), dict(new), dict(construction), places or {}))


def edges_of(pieces: dict) -> list[Edge]:
    """Every edge of the named lines and arcs."""
    return [edge for piece in pieces.values() for edge in piece.edges()]


def render_lines(
    name: str, done: dict, new: dict, construction: dict, places: dict, ghost
) -> None:
    """Write one step: the finished outline faintly, and the lines on top."""
    exporter = ExportSVG(scale=1.6, margin=8)
    exporter.add_layer("Ghost", line_color=0xD0D0D0, line_weight=0.3)
    exporter.add_layer(
        "Construction",
        line_color=0x3465A4,
        line_weight=0.3,
        line_type=LineType.ISO_DASH_SPACE,
    )
    exporter.add_layer("Done", line_weight=0.6)
    exporter.add_layer("New", line_color=0xCC0000, line_weight=0.8)
    exporter.add_layer("Ends", fill_color=0x000000, line_weight=0.1)
    exporter.add_layer(
        "Names", fill_color=0x3465A4, line_color=0x3465A4, line_weight=0.1
    )
    exporter.add_layer(
        "NewNames", fill_color=0xCC0000, line_color=0xCC0000, line_weight=0.1
    )
    exporter.add_shape(ghost, layer="Ghost")
    if construction:
        exporter.add_shape(edges_of(construction), layer="Construction")
    if done:
        exporter.add_shape(edges_of(done), layer="Done")
    if new:
        exporter.add_shape(edges_of(new), layer="New")
    for pieces, layer in ((construction, "Names"), (new, "NewNames")):
        for label, piece in pieces.items():
            edge = piece.edges().sort_by(Edge.length)[-1]
            tangent = edge % 0.5
            beside = (edge @ 0.5) + Vector(tangent.Y, -tangent.X) * 3.5
            beside = Vector(places.get(label, beside))
            text = Text(label, 3.2)
            exporter.add_shape(Pos(beside.X, beside.Y) * text, layer=layer)
    for piece in new.values():
        for end in (piece @ 0, piece @ 1):
            exporter.add_shape(Pos(end.X, end.Y) * Circle(0.6), layer="Ends")
    exporter.write(OUTPUT / f"lever_{name}.svg")


def render_choice(chosen: Edge, other: Edge, references: list, name: str) -> None:
    """Write a close-up of two candidate arcs, each shown as its whole circle."""
    exporter = ExportSVG(scale=6, margin=8)
    exporter.add_layer(
        "Construction",
        line_color=0x3465A4,
        line_weight=0.3,
        line_type=LineType.ISO_DASH_SPACE,
    )
    exporter.add_layer("Other", line_color=0x969696, line_weight=0.5)
    exporter.add_layer("Chosen", line_color=0xCC0000, line_weight=0.8)
    exporter.add_layer(
        "OtherName", fill_color=0x707070, line_color=0x707070, line_weight=0.1
    )
    exporter.add_layer(
        "ChosenName", fill_color=0xCC0000, line_color=0xCC0000, line_weight=0.1
    )
    exporter.add_shape(references, layer="Construction")
    for arc, layer, label in ((other, "Other", "[-1]"), (chosen, "Chosen", "[0]")):
        center = arc.arc_center
        circle = Pos(center.X, center.Y) * CenterArc((0, 0), arc.radius, 0, 360)
        exporter.add_shape(circle, layer=layer)
        exporter.add_shape(
            Pos(center.X, center.Y) * Text(label, 2), layer=f"{layer}Name"
        )
    exporter.write(OUTPUT / f"lever_{name}.svg")


def render_sketch(sketch: Shape, name: str) -> None:
    """Write a sketch, seen from above, as a filled SVG drawing."""
    exporter = ExportSVG(scale=1.6, margin=8)
    exporter.add_layer("Sketch", fill_color=0xC4D6E8, line_weight=0.4)
    exporter.add_shape(sketch.faces(), layer="Sketch")
    exporter.write(OUTPUT / f"lever_{name}.svg")


def size_of(shape: Shape) -> float:
    """A shape's area, or the length of its edges."""
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
# Step 3: start where the drawing is complete
# ---------------------------------------------------------------------------

# [known_builder]
with BuildLine() as outline:
    top_right = Polyline(
        (right - top_flat, top),
        (right - top_chamfer, top),
        (right, top - top_chamfer),
        (right, top - side_height),
    )
    slant = Line(top_right @ 1, (right - foot_inset, bottom))
# [known_builder]
builder_result = outline.line

# [known_algebra]
top_right = Polyline(
    (right - top_flat, top),
    (right - top_chamfer, top),
    (right, top - top_chamfer),
    (right, top - side_height),
)
slant = Line(top_right @ 1, (right - foot_inset, bottom))
# [known_algebra]

assert same(builder_result, Curve() + [top_right, slant])
picture("known", {}, {"top_right": top_right, "slant": slant}, {})

# ---------------------------------------------------------------------------
# Step 4: an arc tangent to a line and through a point
# ---------------------------------------------------------------------------

# [top_arc_builder]
with BuildLine() as outline:
    top_right = Polyline(
        (right - top_flat, top),
        (right - top_chamfer, top),
        (right, top - top_chamfer),
        (right, top - side_height),
    )
    slant = Line(top_right @ 1, (right - foot_inset, bottom))

    c_slope = PolarLine((0, lobe_top), 50, -slope_angle, mode=Mode.PRIVATE)
    top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)
# [top_arc_builder]
builder_result = outline.line

# [top_arc_algebra]
top_right = Polyline(
    (right - top_flat, top),
    (right - top_chamfer, top),
    (right, top - top_chamfer),
    (right, top - side_height),
)
slant = Line(top_right @ 1, (right - foot_inset, bottom))

c_slope = PolarLine((0, lobe_top), 50, -slope_angle)
top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)
# [top_arc_algebra]

assert same(builder_result, Curve() + [top_right, slant, top_arc])
assert (top_arc @ 1 - top_right @ 0).length < 1e-6  # the arc ends on the flat
assert abs((top_arc % 0).cross(c_slope % 0).length) < 1e-6  # and starts tangent
picture(
    "top_arc",
    {"top_right": top_right, "slant": slant},
    {"top_arc": top_arc},
    {"c_slope": c_slope},
    {"top_arc": (27, 25), "c_slope": (44, 5)},
)

# ---------------------------------------------------------------------------
# Step 5: a line that runs until it meets something
# ---------------------------------------------------------------------------

# [foot_builder]
with BuildLine() as outline:
    top_right = Polyline(
        (right - top_flat, top),
        (right - top_chamfer, top),
        (right, top - top_chamfer),
        (right, top - side_height),
    )
    slant = Line(top_right @ 1, (right - foot_inset, bottom))

    c_slope = PolarLine((0, lobe_top), 50, -slope_angle, mode=Mode.PRIVATE)
    top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

    c_base = Line((left, lobe_bottom), (right, lobe_bottom), mode=Mode.PRIVATE)
    neck_center = slant.intersect(c_base)[0]
    c_neck = CenterArc(neck_center, neck_radius, 180, 50, mode=Mode.PRIVATE)
    foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))
# [foot_builder]
builder_result = outline.line

# [foot_algebra]
top_right = Polyline(
    (right - top_flat, top),
    (right - top_chamfer, top),
    (right, top - top_chamfer),
    (right, top - side_height),
)
slant = Line(top_right @ 1, (right - foot_inset, bottom))

c_slope = PolarLine((0, lobe_top), 50, -slope_angle)
top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

c_base = Line((left, lobe_bottom), (right, lobe_bottom))
neck_center = slant.intersect(c_base)[0]
c_neck = CenterArc(neck_center, neck_radius, 180, 50)
foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))
# [foot_algebra]

assert same(builder_result, Curve() + [top_right, slant, top_arc, foot])
assert abs((foot @ 1 - Vector(neck_center)).length - neck_radius) < 1e-6
picture(
    "foot",
    {"top_right": top_right, "slant": slant, "top_arc": top_arc},
    {"foot": foot},
    {"c_base": c_base, "c_neck": c_neck},
    {"c_base": (50, -10), "c_neck": (19, -27), "foot": (35, -37)},
)

# ---------------------------------------------------------------------------
# Step 6: an arc tangent to two things, and a choice
# ---------------------------------------------------------------------------

candidates = ConstrainedArcs(c_neck, c_base, radius=neck_fillet)
assert len(candidates.edges()) == 2

# [neck_builder]
with BuildLine() as outline:
    top_right = Polyline(
        (right - top_flat, top),
        (right - top_chamfer, top),
        (right, top - top_chamfer),
        (right, top - side_height),
    )
    slant = Line(top_right @ 1, (right - foot_inset, bottom))

    c_slope = PolarLine((0, lobe_top), 50, -slope_angle, mode=Mode.PRIVATE)
    top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

    c_base = Line((left, lobe_bottom), (right, lobe_bottom), mode=Mode.PRIVATE)
    neck_center = slant.intersect(c_base)[0]
    c_neck = CenterArc(neck_center, neck_radius, 180, 50, mode=Mode.PRIVATE)
    foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))

    small_arc = ConstrainedArcs(
        c_neck,
        c_base,
        radius=neck_fillet,
        selector=lambda arcs: arcs.sort_by(Axis.X)[0],
    )
    neck = insert(c_neck.trim(foot @ 1, small_arc @ 0))
# [neck_builder]
builder_result = outline.line

# [neck_algebra]
top_right = Polyline(
    (right - top_flat, top),
    (right - top_chamfer, top),
    (right, top - top_chamfer),
    (right, top - side_height),
)
slant = Line(top_right @ 1, (right - foot_inset, bottom))

c_slope = PolarLine((0, lobe_top), 50, -slope_angle)
top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

c_base = Line((left, lobe_bottom), (right, lobe_bottom))
neck_center = slant.intersect(c_base)[0]
c_neck = CenterArc(neck_center, neck_radius, 180, 50)
foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))

small_arc = ConstrainedArcs(
    c_neck,
    c_base,
    radius=neck_fillet,
    selector=lambda arcs: arcs.sort_by(Axis.X)[0],
)
neck = c_neck.trim(foot @ 1, small_arc @ 0)
# [neck_algebra]

assert same(
    builder_result, Curve() + [top_right, slant, top_arc, foot, small_arc, neck]
)
so_far = {"top_right": top_right, "slant": slant, "top_arc": top_arc, "foot": foot}
by_x = candidates.edges().sort_by(Axis.X)
nearby = [
    Line((10, lobe_bottom), (42, lobe_bottom)),
    c_neck.trim(c_neck @ 0, c_neck @ 0.45),
]
render_choice(by_x[0], by_x[-1], nearby, "candidates")
picture(
    "neck",
    so_far,
    {"small_arc": small_arc, "neck": neck},
    {"c_base": c_base, "c_neck": c_neck},
    {
        "small_arc": (14, -22),
        "neck": (20, -29),
        "c_base": (50, -10),
        "c_neck": (25, -39),
    },
)

# ---------------------------------------------------------------------------
# Step 7: close the outline
# ---------------------------------------------------------------------------

# [lobe_builder]
with BuildLine() as outline:
    top_right = Polyline(
        (right - top_flat, top),
        (right - top_chamfer, top),
        (right, top - top_chamfer),
        (right, top - side_height),
    )
    slant = Line(top_right @ 1, (right - foot_inset, bottom))

    c_slope = PolarLine((0, lobe_top), 50, -slope_angle, mode=Mode.PRIVATE)
    top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

    c_base = Line((left, lobe_bottom), (right, lobe_bottom), mode=Mode.PRIVATE)
    neck_center = slant.intersect(c_base)[0]
    c_neck = CenterArc(neck_center, neck_radius, 180, 50, mode=Mode.PRIVATE)
    foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))

    small_arc = ConstrainedArcs(
        c_neck,
        c_base,
        radius=neck_fillet,
        selector=lambda arcs: arcs.sort_by(Axis.X)[0],
    )
    neck = insert(c_neck.trim(foot @ 1, small_arc @ 0))

    lobe = Polyline(
        small_arc @ 1,
        (left + lobe_chamfer, lobe_bottom),
        (left, lobe_bottom + lobe_chamfer),
        (left, lobe_top - lobe_chamfer),
        (left + lobe_chamfer, lobe_top),
        (0, lobe_top),
        top_arc @ 0,
    )
# [lobe_builder]
builder_result = outline.line

# [lobe_algebra]
top_right = Polyline(
    (right - top_flat, top),
    (right - top_chamfer, top),
    (right, top - top_chamfer),
    (right, top - side_height),
)
slant = Line(top_right @ 1, (right - foot_inset, bottom))

c_slope = PolarLine((0, lobe_top), 50, -slope_angle)
top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

c_base = Line((left, lobe_bottom), (right, lobe_bottom))
neck_center = slant.intersect(c_base)[0]
c_neck = CenterArc(neck_center, neck_radius, 180, 50)
foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))

small_arc = ConstrainedArcs(
    c_neck,
    c_base,
    radius=neck_fillet,
    selector=lambda arcs: arcs.sort_by(Axis.X)[0],
)
neck = c_neck.trim(foot @ 1, small_arc @ 0)

lobe = Polyline(
    small_arc @ 1,
    (left + lobe_chamfer, lobe_bottom),
    (left, lobe_bottom + lobe_chamfer),
    (left, lobe_top - lobe_chamfer),
    (left + lobe_chamfer, lobe_top),
    (0, lobe_top),
    top_arc @ 0,
)
# [lobe_algebra]

pieces = {
    "top_right": top_right,
    "slant": slant,
    "top_arc": top_arc,
    "foot": foot,
    "small_arc": small_arc,
    "neck": neck,
    "lobe": lobe,
}
assert same(builder_result, Curve() + list(pieces.values()))
picture("lobe", {k: v for k, v in pieces.items() if k != "lobe"}, {"lobe": lobe}, {})

# ---------------------------------------------------------------------------
# Step 8: make the face and check it
# ---------------------------------------------------------------------------

# [face_builder]
with BuildSketch() as lever:
    with BuildLine() as outline:
        top_right = Polyline(
            (right - top_flat, top),
            (right - top_chamfer, top),
            (right, top - top_chamfer),
            (right, top - side_height),
        )
        slant = Line(top_right @ 1, (right - foot_inset, bottom))

        c_slope = PolarLine((0, lobe_top), 50, -slope_angle, mode=Mode.PRIVATE)
        top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

        c_base = Line((left, lobe_bottom), (right, lobe_bottom), mode=Mode.PRIVATE)
        neck_center = slant.intersect(c_base)[0]
        c_neck = CenterArc(neck_center, neck_radius, 180, 50, mode=Mode.PRIVATE)
        foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))

        small_arc = ConstrainedArcs(
            c_neck,
            c_base,
            radius=neck_fillet,
            selector=lambda arcs: arcs.sort_by(Axis.X)[0],
        )
        neck = insert(c_neck.trim(foot @ 1, small_arc @ 0))

        lobe = Polyline(
            small_arc @ 1,
            (left + lobe_chamfer, lobe_bottom),
            (left, lobe_bottom + lobe_chamfer),
            (left, lobe_top - lobe_chamfer),
            (left + lobe_chamfer, lobe_top),
            (0, lobe_top),
            top_arc @ 0,
        )
    make_face()
    Circle(hole_diameter / 2, mode=Mode.SUBTRACT)

print(BoundBox(lever.sketch).size)
# [face_builder]
builder_result = lever.sketch

# [face_algebra]
top_right = Polyline(
    (right - top_flat, top),
    (right - top_chamfer, top),
    (right, top - top_chamfer),
    (right, top - side_height),
)
slant = Line(top_right @ 1, (right - foot_inset, bottom))

c_slope = PolarLine((0, lobe_top), 50, -slope_angle)
top_arc = ConstrainedArcs(c_slope, top_right @ 0, radius=top_radius)

c_base = Line((left, lobe_bottom), (right, lobe_bottom))
neck_center = slant.intersect(c_base)[0]
c_neck = CenterArc(neck_center, neck_radius, 180, 50)
foot = PolarLine(slant @ 1, length=c_neck, direction=(-1, 0))

small_arc = ConstrainedArcs(
    c_neck,
    c_base,
    radius=neck_fillet,
    selector=lambda arcs: arcs.sort_by(Axis.X)[0],
)
neck = c_neck.trim(foot @ 1, small_arc @ 0)

lobe = Polyline(
    small_arc @ 1,
    (left + lobe_chamfer, lobe_bottom),
    (left, lobe_bottom + lobe_chamfer),
    (left, lobe_top - lobe_chamfer),
    (left + lobe_chamfer, lobe_top),
    (0, lobe_top),
    top_arc @ 0,
)

lever = make_face([top_right, slant, top_arc, foot, small_arc, neck, lobe])
lever -= Circle(hole_diameter / 2)

print(BoundBox(lever).size)
# [face_algebra]

assert same(builder_result, lever)
size = lever.bounding_box().size
assert abs(size.X - overall_width) < 1e-6 and abs(size.Y - overall_height) < 1e-6
render_sketch(lever, "face")

ghost = lever.edges()
for step in STEPS:
    render_lines(*step, ghost)
