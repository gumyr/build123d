"""
Selecting and finishing tutorial

name: selecting_and_finishing.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "Selecting and finishing" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/selecting_and_finishing``.

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

length, width, base_height = 80, 50, 10
corner_radius, edge_chamfer = 8, 1.5
boss_radius, boss_height, bore_radius = 16, 22, 10
blend_radius = 4
hole_inset, hole_radius = 10, 2.75
counter_bore_radius, counter_bore_depth = 5, 5
# [setup]

OUTPUT = Path("assets/selecting_and_finishing")
OUTPUT.mkdir(parents=True, exist_ok=True)
VIEWPOINT = (-70, -150, 110)


def render_part(part: Shape, name: str, selected: list[Shape] | None = None) -> None:
    """Write a part as an SVG line drawing, with any selected edges or faces
    drawn over it in colour."""
    look_at = part.bounding_box().center()
    visible, hidden = part.drawing_view(VIEWPOINT, look_at=look_at)
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0x969696, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Selected", line_color=0xCC0000, line_weight=1.1)
    exporter.add_shape(hidden, layer="Hidden")
    exporter.add_shape(visible, layer="Visible")
    if selected:
        edges = [edge for shape in selected for edge in shape.edges()]
        chosen = Compound(children=edges).drawing_view(VIEWPOINT, look_at=look_at)
        exporter.add_shape(chosen.visible + chosen.hidden, layer="Selected")
    exporter.write(OUTPUT / f"pedestal_{name}.svg")


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
# Step 2: the block
# ---------------------------------------------------------------------------

# [block_builder]
with BuildPart() as pedestal:
    with BuildSketch() as outline:
        Rectangle(length, width)
    extrude(amount=base_height)
# [block_builder]
builder_result = pedestal.part

# [block_algebra]
pedestal = extrude(Rectangle(length, width), amount=base_height)
# [block_algebra]

assert same(builder_result, pedestal)
assert len(pedestal.solids()) == 1 and pedestal.is_valid
render_part(pedestal, "block")

# the next step's selection, drawn on the part as it stands now
previous = pedestal
chosen = pedestal.edges().filter_by(Axis.Z)

# ---------------------------------------------------------------------------
# Step 3: ask the part for its edges
# ---------------------------------------------------------------------------

# [corners_builder]
with BuildPart() as pedestal:
    with BuildSketch() as outline:
        Rectangle(length, width)
    extrude(amount=base_height)

    fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
# [corners_builder]
builder_result = pedestal.part

# [corners_algebra]
pedestal = extrude(Rectangle(length, width), amount=base_height)

pedestal = fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
# [corners_algebra]

assert same(builder_result, pedestal)
assert len(pedestal.solids()) == 1 and pedestal.is_valid
render_part(previous, "corners_selected", selected=chosen)
render_part(pedestal, "corners")

# the next step's selection, drawn on the part as it stands now
previous = pedestal
chosen = pedestal.edges().group_by(Axis.Z)[-1]

# ---------------------------------------------------------------------------
# Step 4: edges by height
# ---------------------------------------------------------------------------

# [top_edge_builder]
with BuildPart() as pedestal:
    with BuildSketch() as outline:
        Rectangle(length, width)
    extrude(amount=base_height)

    fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
    chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)
# [top_edge_builder]
builder_result = pedestal.part

# [top_edge_algebra]
pedestal = extrude(Rectangle(length, width), amount=base_height)

pedestal = fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
pedestal = chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)
# [top_edge_algebra]

assert same(builder_result, pedestal)
assert len(pedestal.solids()) == 1 and pedestal.is_valid
render_part(previous, "top_edge_selected", selected=chosen)
render_part(pedestal, "top_edge")

# the next step's selection, drawn on the part as it stands now
previous = pedestal
chosen = [pedestal.faces().sort_by(Axis.Z)[-1]]

# ---------------------------------------------------------------------------
# Step 5: a face to build on
# ---------------------------------------------------------------------------

# [boss_builder]
with BuildPart() as pedestal:
    with BuildSketch() as outline:
        Rectangle(length, width)
    extrude(amount=base_height)

    fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
    chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)

    top = pedestal.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(top) as boss:
        Circle(boss_radius)
    extrude(amount=boss_height)
# [boss_builder]
builder_result = pedestal.part

# [boss_algebra]
pedestal = extrude(Rectangle(length, width), amount=base_height)

pedestal = fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
pedestal = chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)

top = pedestal.faces().sort_by(Axis.Z)[-1]
pedestal += extrude(Plane(top) * Circle(boss_radius), amount=boss_height)
# [boss_algebra]

assert same(builder_result, pedestal)
assert len(pedestal.solids()) == 1 and pedestal.is_valid
render_part(previous, "boss_selected", selected=chosen)
render_part(pedestal, "boss")

# the next step's selection, drawn on the part as it stands now
previous = pedestal
chosen = [pedestal.edges(Select.LAST).sort_by(Axis.Z)[0]]

# ---------------------------------------------------------------------------
# Step 6: what was just made
# ---------------------------------------------------------------------------

# [blend_builder]
with BuildPart() as pedestal:
    with BuildSketch() as outline:
        Rectangle(length, width)
    extrude(amount=base_height)

    fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
    chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)

    top = pedestal.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(top) as boss:
        Circle(boss_radius)
    extrude(amount=boss_height)
    fillet(pedestal.edges(Select.LAST).sort_by(Axis.Z)[0], radius=blend_radius)
# [blend_builder]
builder_result = pedestal.part

# [blend_algebra]
pedestal = extrude(Rectangle(length, width), amount=base_height)

pedestal = fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
pedestal = chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)

top = pedestal.faces().sort_by(Axis.Z)[-1]
pedestal += extrude(Plane(top) * Circle(boss_radius), amount=boss_height)
pedestal = fillet(pedestal.edges(Select.LAST).sort_by(Axis.Z)[0], radius=blend_radius)
# [blend_algebra]

assert same(builder_result, pedestal)
assert len(pedestal.solids()) == 1 and pedestal.is_valid
render_part(previous, "blend_selected", selected=chosen)
render_part(pedestal, "blend")

# the next step's selection, drawn on the part as it stands now
previous = pedestal
chosen = [pedestal.faces().sort_by(Axis.Z)[-1], top]

# ---------------------------------------------------------------------------
# Step 7: holes on a face
# ---------------------------------------------------------------------------

# [holes_builder]
with BuildPart() as pedestal:
    with BuildSketch() as outline:
        Rectangle(length, width)
    extrude(amount=base_height)

    fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
    chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)

    top = pedestal.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(top) as boss:
        Circle(boss_radius)
    extrude(amount=boss_height)
    fillet(pedestal.edges(Select.LAST).sort_by(Axis.Z)[0], radius=blend_radius)

    with Locations(pedestal.faces().sort_by(Axis.Z)[-1]):
        Hole(bore_radius)
    with Locations(top):
        with GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2):
            CounterBoreHole(hole_radius, counter_bore_radius, counter_bore_depth)
# [holes_builder]
builder_result = pedestal.part

# [holes_algebra]
pedestal = extrude(Rectangle(length, width), amount=base_height)

pedestal = fillet(pedestal.edges().filter_by(Axis.Z), radius=corner_radius)
pedestal = chamfer(pedestal.edges().group_by(Axis.Z)[-1], length=edge_chamfer)

top = pedestal.faces().sort_by(Axis.Z)[-1]
pedestal += extrude(Plane(top) * Circle(boss_radius), amount=boss_height)
pedestal = fillet(pedestal.edges(Select.LAST).sort_by(Axis.Z)[0], radius=blend_radius)

rim = pedestal.faces().sort_by(Axis.Z)[-1]
pedestal -= Plane(rim) * Hole(bore_radius, depth=base_height + boss_height)
pedestal -= (
    Plane(top)
    * GridLocations(length - 2 * hole_inset, width - 2 * hole_inset, 2, 2)
    * CounterBoreHole(
        hole_radius, counter_bore_radius, counter_bore_depth, depth=base_height
    )
)
# [holes_algebra]

assert same(builder_result, pedestal)
assert len(pedestal.solids()) == 1 and pedestal.is_valid
render_part(previous, "holes_selected", selected=chosen)
render_part(pedestal, "holes")
