"""
Beyond extrude tutorial

name: beyond_extrude.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "Beyond extrude" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/beyond_extrude``.

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

base_length, base_width = 120, 60
hood_height = 50
collar_radius, collar_height = 25, 30
collar_top = hood_height + collar_height
barb, barb_length = 2, 10
wall = 2
skirt_height = 6
ear_offset, ear_radius, screw_radius = 7, 9, 2.75
# [setup]

OUTPUT = Path("assets/beyond_extrude")
OUTPUT.mkdir(parents=True, exist_ok=True)
VIEWPOINT = (-70, -150, 110)


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
    selected: list[Shape] | None = None,
) -> None:
    """Write a part as an SVG line drawing, with any selected sketches or
    faces drawn over it in colour."""
    look_at = part.bounding_box().center()
    visible, hidden = part.drawing_view(VIEWPOINT, look_at=look_at)
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0x969696, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Selected", line_color=0xCC0000, line_weight=1.1)
    exporter.add_shape(smooth(hidden), layer="Hidden")
    exporter.add_shape(smooth(visible), layer="Visible")
    if selected:
        # straight lines stay straight in the view, so trace each edge finely
        traced = [
            Polyline(*[edge @ (i / 96) for i in range(97)])
            for shape in selected
            for edge in shape.edges()
        ]
        chosen = Compound(children=traced).drawing_view(VIEWPOINT, look_at=look_at)
        exporter.add_shape(chosen.visible + chosen.hidden, layer="Selected")
    exporter.write(OUTPUT / f"adapter_{name}.svg")


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
# Step 2: loft, from one shape to another
# ---------------------------------------------------------------------------

# [loft_builder]
with BuildPart() as adapter:
    with BuildSketch() as base:
        Ellipse(base_length / 2, base_width / 2)
    with BuildSketch(Plane.XY.offset(hood_height)) as neck:
        Circle(collar_radius)
    loft()
# [loft_builder]
builder_result = adapter.part

# [loft_algebra]
base = Ellipse(base_length / 2, base_width / 2)
neck = Plane.XY.offset(hood_height) * Circle(collar_radius)
adapter = loft([base, neck])
# [loft_algebra]

assert same(builder_result, adapter)
assert len(adapter.solids()) == 1 and adapter.is_valid
render_part(adapter, "loft", selected=[base, neck])

# ---------------------------------------------------------------------------
# Step 3: revolve, turn a profile round an axis
# ---------------------------------------------------------------------------

# [revolve_builder]
with BuildPart() as adapter:
    with BuildSketch() as base:
        Ellipse(base_length / 2, base_width / 2)
    with BuildSketch(Plane.XY.offset(hood_height)) as neck:
        Circle(collar_radius)
    loft()

    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            Polyline(
                (0, hood_height),
                (collar_radius, hood_height),
                (collar_radius, collar_top - barb_length),
                (collar_radius + barb, collar_top - barb_length),
                (collar_radius, collar_top),
                (0, collar_top),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z)
# [revolve_builder]
builder_result = adapter.part

# [revolve_algebra]
base = Ellipse(base_length / 2, base_width / 2)
neck = Plane.XY.offset(hood_height) * Circle(collar_radius)
adapter = loft([base, neck])

profile = Plane.XZ * make_face(
    Polyline(
        (0, hood_height),
        (collar_radius, hood_height),
        (collar_radius, collar_top - barb_length),
        (collar_radius + barb, collar_top - barb_length),
        (collar_radius, collar_top),
        (0, collar_top),
        close=True,
    )
)
adapter += revolve(profile, axis=Axis.Z)
# [revolve_algebra]

assert same(builder_result, adapter)
assert len(adapter.solids()) == 1 and adapter.is_valid
render_part(adapter, "revolve", selected=[profile])

# ---------------------------------------------------------------------------
# Step 4: hollow it out
# ---------------------------------------------------------------------------

# [hollow_builder]
with BuildPart() as adapter:
    with BuildSketch() as base:
        Ellipse(base_length / 2, base_width / 2)
    with BuildSketch(Plane.XY.offset(hood_height)) as neck:
        Circle(collar_radius)
    loft()

    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            Polyline(
                (0, hood_height),
                (collar_radius, hood_height),
                (collar_radius, collar_top - barb_length),
                (collar_radius + barb, collar_top - barb_length),
                (collar_radius, collar_top),
                (0, collar_top),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z)

    ends = adapter.faces().sort_by(Axis.Z)
    offset(amount=-wall, openings=[ends[0], ends[-1]])
# [hollow_builder]
builder_result = adapter.part

# [hollow_algebra]
base = Ellipse(base_length / 2, base_width / 2)
neck = Plane.XY.offset(hood_height) * Circle(collar_radius)
adapter = loft([base, neck])

profile = Plane.XZ * make_face(
    Polyline(
        (0, hood_height),
        (collar_radius, hood_height),
        (collar_radius, collar_top - barb_length),
        (collar_radius + barb, collar_top - barb_length),
        (collar_radius, collar_top),
        (0, collar_top),
        close=True,
    )
)
adapter += revolve(profile, axis=Axis.Z)

ends = adapter.faces().sort_by(Axis.Z)
adapter = offset(adapter, amount=-wall, openings=[ends[0], ends[-1]])
# [hollow_algebra]

assert same(builder_result, adapter)
assert len(adapter.solids()) == 1 and adapter.is_valid
render_part(adapter, "hollow")

# ---------------------------------------------------------------------------
# Step 5: extrude a face
# ---------------------------------------------------------------------------

# [skirt_builder]
with BuildPart() as adapter:
    with BuildSketch() as base:
        Ellipse(base_length / 2, base_width / 2)
    with BuildSketch(Plane.XY.offset(hood_height)) as neck:
        Circle(collar_radius)
    loft()

    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            Polyline(
                (0, hood_height),
                (collar_radius, hood_height),
                (collar_radius, collar_top - barb_length),
                (collar_radius + barb, collar_top - barb_length),
                (collar_radius, collar_top),
                (0, collar_top),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z)

    ends = adapter.faces().sort_by(Axis.Z)
    offset(amount=-wall, openings=[ends[0], ends[-1]])

    rim = adapter.faces().sort_by(Axis.Z)[0]
    extrude(rim, amount=skirt_height)
# [skirt_builder]
builder_result = adapter.part

# [skirt_algebra]
base = Ellipse(base_length / 2, base_width / 2)
neck = Plane.XY.offset(hood_height) * Circle(collar_radius)
adapter = loft([base, neck])

profile = Plane.XZ * make_face(
    Polyline(
        (0, hood_height),
        (collar_radius, hood_height),
        (collar_radius, collar_top - barb_length),
        (collar_radius + barb, collar_top - barb_length),
        (collar_radius, collar_top),
        (0, collar_top),
        close=True,
    )
)
adapter += revolve(profile, axis=Axis.Z)

ends = adapter.faces().sort_by(Axis.Z)
adapter = offset(adapter, amount=-wall, openings=[ends[0], ends[-1]])

rim = adapter.faces().sort_by(Axis.Z)[0]
adapter += extrude(rim, amount=skirt_height)
# [skirt_algebra]

assert same(builder_result, adapter)
assert len(adapter.solids()) == 1 and adapter.is_valid
render_part(adapter, "skirt", selected=[rim])

# ---------------------------------------------------------------------------
# Step 6: mirror, draw one side only
# ---------------------------------------------------------------------------

# [mirror_builder]
with BuildPart() as adapter:
    with BuildSketch() as base:
        Ellipse(base_length / 2, base_width / 2)
    with BuildSketch(Plane.XY.offset(hood_height)) as neck:
        Circle(collar_radius)
    loft()

    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            Polyline(
                (0, hood_height),
                (collar_radius, hood_height),
                (collar_radius, collar_top - barb_length),
                (collar_radius + barb, collar_top - barb_length),
                (collar_radius, collar_top),
                (0, collar_top),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z)

    ends = adapter.faces().sort_by(Axis.Z)
    offset(amount=-wall, openings=[ends[0], ends[-1]])

    rim = adapter.faces().sort_by(Axis.Z)[0]
    extrude(rim, amount=skirt_height)

    with BuildSketch(Plane.XY.offset(-skirt_height)) as ears:
        with Locations((base_length / 2 + ear_offset, 0)):
            Circle(ear_radius)
            Circle(screw_radius, mode=Mode.SUBTRACT)
        mirror(about=Plane.YZ)
        Ellipse(base_length / 2, base_width / 2, mode=Mode.SUBTRACT)
    extrude(amount=skirt_height)
# [mirror_builder]
builder_result = adapter.part

# [mirror_algebra]
base = Ellipse(base_length / 2, base_width / 2)
neck = Plane.XY.offset(hood_height) * Circle(collar_radius)
adapter = loft([base, neck])

profile = Plane.XZ * make_face(
    Polyline(
        (0, hood_height),
        (collar_radius, hood_height),
        (collar_radius, collar_top - barb_length),
        (collar_radius + barb, collar_top - barb_length),
        (collar_radius, collar_top),
        (0, collar_top),
        close=True,
    )
)
adapter += revolve(profile, axis=Axis.Z)

ends = adapter.faces().sort_by(Axis.Z)
adapter = offset(adapter, amount=-wall, openings=[ends[0], ends[-1]])

rim = adapter.faces().sort_by(Axis.Z)[0]
adapter += extrude(rim, amount=skirt_height)

ear = Pos(base_length / 2 + ear_offset, 0) * (Circle(ear_radius) - Circle(screw_radius))
ears = ear + mirror(ear, about=Plane.YZ) - base
adapter += extrude(Plane.XY.offset(-skirt_height) * ears, amount=skirt_height)
# [mirror_algebra]

assert same(builder_result, adapter)
assert len(adapter.solids()) == 1 and adapter.is_valid
render_part(adapter, "mirror", selected=[ear])
render_part(adapter, "finished")

# ---------------------------------------------------------------------------
# Step 7: split, to look inside
# ---------------------------------------------------------------------------

# [split_builder]
with BuildPart() as adapter:
    with BuildSketch() as base:
        Ellipse(base_length / 2, base_width / 2)
    with BuildSketch(Plane.XY.offset(hood_height)) as neck:
        Circle(collar_radius)
    loft()

    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            Polyline(
                (0, hood_height),
                (collar_radius, hood_height),
                (collar_radius, collar_top - barb_length),
                (collar_radius + barb, collar_top - barb_length),
                (collar_radius, collar_top),
                (0, collar_top),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z)

    ends = adapter.faces().sort_by(Axis.Z)
    offset(amount=-wall, openings=[ends[0], ends[-1]])

    rim = adapter.faces().sort_by(Axis.Z)[0]
    extrude(rim, amount=skirt_height)

    with BuildSketch(Plane.XY.offset(-skirt_height)) as ears:
        with Locations((base_length / 2 + ear_offset, 0)):
            Circle(ear_radius)
            Circle(screw_radius, mode=Mode.SUBTRACT)
        mirror(about=Plane.YZ)
        Ellipse(base_length / 2, base_width / 2, mode=Mode.SUBTRACT)
    extrude(amount=skirt_height)

back_half = split(adapter.part, bisect_by=Plane.XZ, keep=Keep.BOTTOM)
# [split_builder]
builder_result = adapter.part
builder_back_half = back_half

# [split_algebra]
base = Ellipse(base_length / 2, base_width / 2)
neck = Plane.XY.offset(hood_height) * Circle(collar_radius)
adapter = loft([base, neck])

profile = Plane.XZ * make_face(
    Polyline(
        (0, hood_height),
        (collar_radius, hood_height),
        (collar_radius, collar_top - barb_length),
        (collar_radius + barb, collar_top - barb_length),
        (collar_radius, collar_top),
        (0, collar_top),
        close=True,
    )
)
adapter += revolve(profile, axis=Axis.Z)

ends = adapter.faces().sort_by(Axis.Z)
adapter = offset(adapter, amount=-wall, openings=[ends[0], ends[-1]])

rim = adapter.faces().sort_by(Axis.Z)[0]
adapter += extrude(rim, amount=skirt_height)

ear = Pos(base_length / 2 + ear_offset, 0) * (Circle(ear_radius) - Circle(screw_radius))
ears = ear + mirror(ear, about=Plane.YZ) - base
adapter += extrude(Plane.XY.offset(-skirt_height) * ears, amount=skirt_height)

back_half = split(adapter, bisect_by=Plane.XZ, keep=Keep.BOTTOM)
# [split_algebra]

assert same(builder_result, adapter)
assert len(adapter.solids()) == 1 and adapter.is_valid
assert abs(builder_back_half.volume - back_half.volume) < 1e-2
assert len(builder_back_half.faces()) == len(back_half.faces())
assert abs(back_half.bounding_box().min.Y) < 1e-6  # the half behind the XZ plane
render_part(back_half, "split")
