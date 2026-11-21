"""
A key cap tutorial

name: key_cap.py
by:   Gumyr
date: November 14th 2026

desc:
    Every code example in the "A key cap" tutorial lives here, between pairs
    of ``# [name]`` markers that the page includes with ``literalinclude``.
    Each step is written twice, in builder and in algebra mode, and shows the
    whole part as it stands at that point; the two are checked against each
    other. The key cap is the one of ``examples/key_cap.py``, a cap for a
    Cherry MX switch, reworked to use ``draft`` and ``offset``. The rendered
    pictures on the page are made from this script by ``key_cap_shots.py``.

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

from build123d.topology import Shape

# [setup]
from build123d import *

width, height = 18, 10
draft_angle = 15
dish_radius, dish_low, dish_shift = 40, 7, -3
wall = 1
edge_radius = 1
rib_height, rib_width = 4, 0.5
stem_radius, stem_length = 2.75, 3.5
cross_length, cross_width = 4.1, 1.17
# [setup]


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
with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(width, width)
    extrude(amount=height)
# [block_builder]
builder_result = key_cap.part

# [block_algebra]
plan = Rectangle(width, width)
key_cap = extrude(plan, amount=height)
# [block_algebra]

assert same(builder_result, key_cap)
assert abs(key_cap.volume - width * width * height) < 1e-6
block = key_cap  # each stage is kept for the pictures

# ---------------------------------------------------------------------------
# Step 3: draft the sides
# ---------------------------------------------------------------------------

# [draft_builder]
with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(width, width)
    extrude(amount=height)
    sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
    draft(sides, Plane.XY, draft_angle)
# [draft_builder]
builder_result = key_cap.part

# [draft_algebra]
plan = Rectangle(width, width)
key_cap = extrude(plan, amount=height)
sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
key_cap = draft(sides, Plane.XY, draft_angle)
# [draft_algebra]

assert same(builder_result, key_cap)
# draft gives exactly what a tapered extrude of the same sketch would have
assert same(key_cap, extrude(Rectangle(width, width), amount=height, taper=draft_angle))
top = key_cap.faces().sort_by(Axis.Z)[-1]
assert top.bounding_box().size.X < width
drafted = key_cap

# ---------------------------------------------------------------------------
# Step 4: dish the top
# ---------------------------------------------------------------------------

# [dish_builder]
with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(width, width)
    extrude(amount=height)
    sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
    draft(sides, Plane.XY, draft_angle)

    with Locations((0, dish_shift, dish_low + dish_radius)):
        Sphere(dish_radius, rotation=(90, 0, 0), mode=Mode.SUBTRACT)
# [dish_builder]
builder_result = key_cap.part

# [dish_algebra]
plan = Rectangle(width, width)
key_cap = extrude(plan, amount=height)
sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
key_cap = draft(sides, Plane.XY, draft_angle)

dish = Sphere(dish_radius, rotation=(90, 0, 0))
key_cap -= Pos(0, dish_shift, dish_low + dish_radius) * dish
# [dish_algebra]

assert same(builder_result, key_cap)
assert key_cap.is_valid and len(key_cap.solids()) == 1
assert (
    dish_low < key_cap.bounding_box().max.Z < height
)  # the corners stand above the dish
solid_cap = key_cap

# ---------------------------------------------------------------------------
# Step 5: hollow it
# ---------------------------------------------------------------------------

# [hollow_builder]
with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(width, width)
    extrude(amount=height)
    sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
    draft(sides, Plane.XY, draft_angle)

    with Locations((0, dish_shift, dish_low + dish_radius)):
        Sphere(dish_radius, rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    offset(amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
# [hollow_builder]
builder_result = key_cap.part

# [hollow_algebra]
plan = Rectangle(width, width)
key_cap = extrude(plan, amount=height)
sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
key_cap = draft(sides, Plane.XY, draft_angle)

dish = Sphere(dish_radius, rotation=(90, 0, 0))
key_cap -= Pos(0, dish_shift, dish_low + dish_radius) * dish

key_cap = offset(key_cap, amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
# [hollow_algebra]

assert same(builder_result, key_cap)
assert key_cap.is_valid and len(key_cap.solids()) == 1
assert key_cap.volume < solid_cap.volume / 2
assert len(key_cap.edges()) == 2 * len(
    solid_cap.edges()
)  # each edge has an inside partner
hollowed = key_cap

# ---------------------------------------------------------------------------
# Step 6: round the outside
# ---------------------------------------------------------------------------

# [round_builder]
with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(width, width)
    extrude(amount=height)
    sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
    draft(sides, Plane.XY, draft_angle)

    with Locations((0, dish_shift, dish_low + dish_radius)):
        Sphere(dish_radius, rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    offset(amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
    outside = key_cap.edges().filter_by(Convexity.CONVEX).group_by(Axis.Z)[1:]
    fillet(outside, radius=edge_radius)
# [round_builder]
builder_result = key_cap.part

# [round_algebra]
plan = Rectangle(width, width)
key_cap = extrude(plan, amount=height)
sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
key_cap = draft(sides, Plane.XY, draft_angle)

dish = Sphere(dish_radius, rotation=(90, 0, 0))
key_cap -= Pos(0, dish_shift, dish_low + dish_radius) * dish

key_cap = offset(key_cap, amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
outside = key_cap.edges().filter_by(Convexity.CONVEX).group_by(Axis.Z)[1:]
key_cap = fillet(outside, radius=edge_radius)
# [round_algebra]

assert same(builder_result, key_cap)
assert key_cap.is_valid and len(key_cap.solids()) == 1
# the convex edges above the bottom are the eight outside ones, and only those
assert sum(len(group) for group in outside) == 8
centers = [edge.center() for edge in solid_cap.edges()]
assert all(
    min((edge.center() - c).length for c in centers) < 1e-6
    for group in outside
    for edge in group
)
shell = key_cap

# ---------------------------------------------------------------------------
# Step 7: ribs that reach the top
# ---------------------------------------------------------------------------

# [ribs_builder]
with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(width, width)
    extrude(amount=height)
    sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
    draft(sides, Plane.XY, draft_angle)

    with Locations((0, dish_shift, dish_low + dish_radius)):
        Sphere(dish_radius, rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    offset(amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
    outside = key_cap.edges().filter_by(Convexity.CONVEX).group_by(Axis.Z)[1:]
    fillet(outside, radius=edge_radius)

    cavity = section(section_by=Plane.XY.offset(rib_height)).face().inner_wires()[0]
    inside = BoundBox(cavity).size
    with BuildSketch(Plane.XY.offset(rib_height)) as ribs:
        Rectangle(inside.X, rib_width)
        Rectangle(rib_width, inside.Y)
        Circle(stem_radius)
    extrude(until=Until.NEXT)
# [ribs_builder]
builder_result = key_cap.part

# [ribs_algebra]
plan = Rectangle(width, width)
key_cap = extrude(plan, amount=height)
sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
key_cap = draft(sides, Plane.XY, draft_angle)

dish = Sphere(dish_radius, rotation=(90, 0, 0))
key_cap -= Pos(0, dish_shift, dish_low + dish_radius) * dish

key_cap = offset(key_cap, amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
outside = key_cap.edges().filter_by(Convexity.CONVEX).group_by(Axis.Z)[1:]
key_cap = fillet(outside, radius=edge_radius)

cavity = section(key_cap, Plane.XY.offset(rib_height)).face().inner_wires()[0]
inside = BoundBox(cavity).size
ribs = (
    Rectangle(inside.X, rib_width)
    + Rectangle(rib_width, inside.Y)
    + Circle(stem_radius)
)
key_cap += extrude(Plane.XY.offset(rib_height) * ribs, until=Until.NEXT, target=key_cap)
# [ribs_algebra]

assert same(builder_result, key_cap)
assert key_cap.is_valid and len(key_cap.solids()) == 1
assert key_cap.volume > shell.volume
# the ribs end on the underside: nothing shows through the top or the walls
assert (key_cap.bounding_box().max - shell.bounding_box().max).length < 1e-6
assert abs((key_cap - shell).bounding_box().min.Z - rib_height) < 1e-6
ribbed = key_cap

# ---------------------------------------------------------------------------
# Step 8: the socket
# ---------------------------------------------------------------------------

# [socket_builder]
with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(width, width)
    extrude(amount=height)
    sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
    draft(sides, Plane.XY, draft_angle)

    with Locations((0, dish_shift, dish_low + dish_radius)):
        Sphere(dish_radius, rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    offset(amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
    outside = key_cap.edges().filter_by(Convexity.CONVEX).group_by(Axis.Z)[1:]
    fillet(outside, radius=edge_radius)

    cavity = section(section_by=Plane.XY.offset(rib_height)).face().inner_wires()[0]
    inside = BoundBox(cavity).size
    with BuildSketch(Plane.XY.offset(rib_height)) as ribs:
        Rectangle(inside.X, rib_width)
        Rectangle(rib_width, inside.Y)
        Circle(stem_radius)
    extrude(until=Until.NEXT)

    with BuildSketch(Plane.XY.offset(rib_height)) as socket:
        Circle(stem_radius)
        Rectangle(cross_length, cross_width, mode=Mode.SUBTRACT)
        Rectangle(cross_width, cross_length, mode=Mode.SUBTRACT)
    extrude(amount=-stem_length)
# [socket_builder]
builder_result = key_cap.part

# [socket_algebra]
plan = Rectangle(width, width)
key_cap = extrude(plan, amount=height)
sides = key_cap.faces().filter_by(Axis.Z, reverse=True)
key_cap = draft(sides, Plane.XY, draft_angle)

dish = Sphere(dish_radius, rotation=(90, 0, 0))
key_cap -= Pos(0, dish_shift, dish_low + dish_radius) * dish

key_cap = offset(key_cap, amount=-wall, openings=key_cap.faces().sort_by(Axis.Z)[0])
outside = key_cap.edges().filter_by(Convexity.CONVEX).group_by(Axis.Z)[1:]
key_cap = fillet(outside, radius=edge_radius)

cavity = section(key_cap, Plane.XY.offset(rib_height)).face().inner_wires()[0]
inside = BoundBox(cavity).size
ribs = (
    Rectangle(inside.X, rib_width)
    + Rectangle(rib_width, inside.Y)
    + Circle(stem_radius)
)
key_cap += extrude(Plane.XY.offset(rib_height) * ribs, until=Until.NEXT, target=key_cap)

socket = Circle(stem_radius)
socket -= Rectangle(cross_length, cross_width)
socket -= Rectangle(cross_width, cross_length)
key_cap += extrude(Plane.XY.offset(rib_height) * socket, amount=-stem_length)
# [socket_algebra]

assert same(builder_result, key_cap)
assert key_cap.is_valid and len(key_cap.solids()) == 1
assert abs(key_cap.bounding_box().min.Z) < 1e-6  # the stem stops short of the bottom
