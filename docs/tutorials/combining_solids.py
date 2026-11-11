"""
Combining solids tutorial

name: combining_solids.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "Combining solids" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/combining_solids``.

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

from OCP.BRepAdaptor import BRepAdaptor_Curve

from build123d.topology import Shape

# [setup]
from build123d import *

body_radius, height = 15, 20
flange_radius, flange_height = 18, 3
flute_radius, flute_count = 2.5, 12
dome_radius = 25
shaft_radius, shaft_flat, shaft_depth = 3, 4.5, 12

on_floor = (Align.CENTER, Align.CENTER, Align.MIN)
# [setup]

OUTPUT = Path("assets/combining_solids")
OUTPUT.mkdir(parents=True, exist_ok=True)
ABOVE = (-60, -110, 60)
BELOW = (-60, -110, -70)


def smooth(edges: list[Edge]) -> list[Edge]:
    """The view draws an ellipse seen at an angle, and the silhouette of a
    curved face, as a run of short straight lines. Put a smooth curve through
    the corners of each run so that the pictures do not look faceted."""
    result = []
    for edge in edges:
        if edge.geom_type != GeomType.BSPLINE:
            result.append(edge)
            continue
        curve = BRepAdaptor_Curve(edge.wrapped).BSpline()
        points = [Vector(curve.Pole(i)) for i in range(1, curve.NbPoles() + 1)]
        if curve.Degree() != 1 or len(points) < 4:
            result.append(edge)
        elif (points[0] - points[-1]).length < 1e-6:
            result.append(Spline(*points[:-1], periodic=True))
        else:
            result.append(Spline(*points))
    return result


def render_part(
    part: Shape,
    name: str,
    tools: list[Shape] | None = None,
    viewpoint: tuple[float, float, float] = ABOVE,
) -> None:
    """Write a part as an SVG line drawing. Any tools - the solids about to
    be combined with it - are drawn over it in colour."""
    everything = Compound(children=[part] + list(tools or []))
    look_at = everything.bounding_box().center()
    visible, hidden = part.drawing_view(viewpoint, look_at=look_at)
    drawn = list(visible) + list(hidden)
    tool_edges: list[Edge] = []
    for tool in tools or []:
        tool_edges.extend(tool.drawing_view(viewpoint, look_at=look_at).visible)
    size = Compound(children=drawn + tool_edges).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0x969696, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Tool", line_color=0xCC0000, line_weight=0.8)
    exporter.add_shape(smooth(hidden), layer="Hidden")
    exporter.add_shape(smooth(visible), layer="Visible")
    if tool_edges:
        exporter.add_shape(smooth(tool_edges), layer="Tool")
    exporter.write(OUTPUT / f"knob_{name}.svg")


def render_sketch(sketch: Shape, name: str) -> None:
    """Write a sketch as an SVG drawing, seen from above."""
    size = sketch.bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Sketch", fill_color=0xD9E6F2, line_weight=0.4)
    exporter.add_shape(sketch, layer="Sketch")
    exporter.write(OUTPUT / f"knob_{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 2: a primitive
# ---------------------------------------------------------------------------

# [body_builder]
with BuildPart() as knob:
    Cylinder(body_radius, height, align=on_floor)
# [body_builder]
builder_result = knob.part

# [body_algebra]
knob = Cylinder(body_radius, height, align=on_floor)
# [body_algebra]

assert same(builder_result, knob)
assert len(knob.solids()) == 1 and knob.is_valid
render_part(knob, "body")
previous = knob

# ---------------------------------------------------------------------------
# Step 3: add
# ---------------------------------------------------------------------------

# [add_builder]
with BuildPart() as knob:
    Cylinder(body_radius, height, align=on_floor)
    Cylinder(flange_radius, flange_height, align=on_floor)
# [add_builder]
builder_result = knob.part

# [add_algebra]
knob = Cylinder(body_radius, height, align=on_floor)
knob += Cylinder(flange_radius, flange_height, align=on_floor)
# [add_algebra]

assert same(builder_result, knob)
assert len(knob.solids()) == 1 and knob.is_valid
render_part(knob, "add")
previous = knob

# ---------------------------------------------------------------------------
# Step 4: subtract
# ---------------------------------------------------------------------------

# [subtract_builder]
with BuildPart() as knob:
    Cylinder(body_radius, height, align=on_floor)
    Cylinder(flange_radius, flange_height, align=on_floor)

    with Locations((0, 0, flange_height)):
        with PolarLocations(body_radius, flute_count):
            Cylinder(
                flute_radius,
                height - flange_height,
                align=on_floor,
                mode=Mode.SUBTRACT,
            )
# [subtract_builder]
builder_result = knob.part

# [subtract_algebra]
knob = Cylinder(body_radius, height, align=on_floor)
knob += Cylinder(flange_radius, flange_height, align=on_floor)

flutes = (
    Pos(Z=flange_height)
    * PolarLocations(body_radius, flute_count)
    * Cylinder(flute_radius, height - flange_height, align=on_floor)
)
knob -= flutes
# [subtract_algebra]

assert same(builder_result, knob)
assert len(knob.solids()) == 1 and knob.is_valid
render_part(previous, "subtract_tools", tools=flutes)
render_part(knob, "subtract")
previous = knob

# ---------------------------------------------------------------------------
# Step 5: intersect
# ---------------------------------------------------------------------------

# [intersect_builder]
with BuildPart() as knob:
    Cylinder(body_radius, height, align=on_floor)
    Cylinder(flange_radius, flange_height, align=on_floor)

    with Locations((0, 0, flange_height)):
        with PolarLocations(body_radius, flute_count):
            Cylinder(
                flute_radius,
                height - flange_height,
                align=on_floor,
                mode=Mode.SUBTRACT,
            )

    with Locations((0, 0, height - dome_radius)):
        Sphere(dome_radius, mode=Mode.INTERSECT)
# [intersect_builder]
builder_result = knob.part

# [intersect_algebra]
knob = Cylinder(body_radius, height, align=on_floor)
knob += Cylinder(flange_radius, flange_height, align=on_floor)

flutes = (
    Pos(Z=flange_height)
    * PolarLocations(body_radius, flute_count)
    * Cylinder(flute_radius, height - flange_height, align=on_floor)
)
knob -= flutes

knob &= Pos(Z=height - dome_radius) * Sphere(dome_radius)
# [intersect_algebra]

assert same(builder_result, knob)
assert len(knob.solids()) == 1 and knob.is_valid
render_part(
    previous,
    "intersect_tool",
    tools=[Pos(Z=height - dome_radius) * Sphere(dome_radius)],
)
render_part(knob, "intersect")
previous = knob

# ---------------------------------------------------------------------------
# Step 6: combine the tools first
# ---------------------------------------------------------------------------

# [cutter_builder]
with BuildPart() as cutter:
    Cylinder(shaft_radius, shaft_depth, align=on_floor)
    split(bisect_by=Plane.YZ.offset(shaft_flat - shaft_radius), keep=Keep.BOTTOM)

with BuildPart() as knob:
    Cylinder(body_radius, height, align=on_floor)
    Cylinder(flange_radius, flange_height, align=on_floor)

    with Locations((0, 0, flange_height)):
        with PolarLocations(body_radius, flute_count):
            Cylinder(
                flute_radius,
                height - flange_height,
                align=on_floor,
                mode=Mode.SUBTRACT,
            )

    with Locations((0, 0, height - dome_radius)):
        Sphere(dome_radius, mode=Mode.INTERSECT)

    insert(cutter.part, mode=Mode.SUBTRACT)
# [cutter_builder]
builder_result = knob.part
builder_cutter = cutter.part

# [cutter_algebra]
knob = Cylinder(body_radius, height, align=on_floor)
knob += Cylinder(flange_radius, flange_height, align=on_floor)

flutes = (
    Pos(Z=flange_height)
    * PolarLocations(body_radius, flute_count)
    * Cylinder(flute_radius, height - flange_height, align=on_floor)
)
knob -= flutes

knob &= Pos(Z=height - dome_radius) * Sphere(dome_radius)

cutter = split(
    Cylinder(shaft_radius, shaft_depth, align=on_floor),
    bisect_by=Plane.YZ.offset(shaft_flat - shaft_radius),
    keep=Keep.BOTTOM,
)
knob -= cutter
# [cutter_algebra]

assert same(builder_result, knob)
assert len(knob.solids()) == 1 and knob.is_valid
assert same(builder_cutter, cutter)
assert abs(cutter.bounding_box().max.X - (shaft_flat - shaft_radius)) < 1e-6
render_part(cutter, "cutter")
render_part(knob, "shaft", viewpoint=BELOW)
render_part(knob, "finished")
csg_knob = knob
previous = knob

# ---------------------------------------------------------------------------
# Step 7: the same knob, from a sketch
# ---------------------------------------------------------------------------

# [sketch_builder]
with BuildPart() as knob:
    with BuildSketch() as plan:
        Circle(body_radius)
        with PolarLocations(body_radius, flute_count):
            Circle(flute_radius, mode=Mode.SUBTRACT)
    extrude(amount=height)

    with BuildSketch() as foot:
        Circle(flange_radius)
    extrude(amount=flange_height)

    with Locations((0, 0, height - dome_radius)):
        Sphere(dome_radius, mode=Mode.INTERSECT)

    with BuildSketch() as shaft:
        Circle(shaft_radius)
        split(bisect_by=Plane.YZ.offset(shaft_flat - shaft_radius), keep=Keep.BOTTOM)
    extrude(amount=shaft_depth, mode=Mode.SUBTRACT)
# [sketch_builder]
builder_result = knob.part

# [sketch_algebra]
plan = Circle(body_radius)
plan -= PolarLocations(body_radius, flute_count) * Circle(flute_radius)
knob = extrude(plan, amount=height)
knob += extrude(Circle(flange_radius), amount=flange_height)

knob &= Pos(Z=height - dome_radius) * Sphere(dome_radius)

shaft = split(
    Circle(shaft_radius),
    bisect_by=Plane.YZ.offset(shaft_flat - shaft_radius),
    keep=Keep.BOTTOM,
)
knob -= extrude(shaft, amount=shaft_depth)
# [sketch_algebra]

assert same(builder_result, knob)
assert len(knob.solids()) == 1 and knob.is_valid
assert abs(knob.volume - csg_knob.volume) < 1e-3  # the same knob as step 6
assert abs(shaft.bounding_box().max.X - (shaft_flat - shaft_radius)) < 1e-6
render_sketch(plan, "plan")
render_sketch(shaft, "shaft_plan")
render_part(knob, "sketch")
previous = knob
