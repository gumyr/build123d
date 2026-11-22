"""
Designing a part tutorial

name: tutorial_design.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "Designing a Part" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and running it checks them. Each step is written
    twice, once in builder mode and once in algebra mode, and the two are
    checked against each other so that the tabs on the page cannot drift
    apart. The pictures on the page are not made here.

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

length, width, height = 50, 25, 25
thickness = 3
bend_radius, fillet_radius = 5, 2
hole_diameter, slot_length = 5, 20
# [setup]


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.area - second.area) < 1e-6
        and abs(first.volume - second.volume) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 5: create 2D profiles
# ---------------------------------------------------------------------------

# [profile_builder]
with BuildSketch() as sketch:
    with BuildLine() as profile:
        FilletPolyline(
            (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
        )
        offset(amount=thickness, side=Side.LEFT)
    make_face()
    mirror(about=Plane.YZ)
# [profile_builder]
builder_result = sketch.sketch

# [profile_algebra]
profile = FilletPolyline(
    (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
)
sketch = make_face(offset(profile, amount=thickness, side=Side.LEFT))
sketch += mirror(sketch, about=Plane.YZ)
# [profile_algebra]

assert same(builder_result, sketch)

# ---------------------------------------------------------------------------
# Step 6: extrude
# ---------------------------------------------------------------------------

# [extrude_builder]
with BuildPart() as bracket:
    with BuildSketch() as sketch:
        with BuildLine() as profile:
            FilletPolyline(
                (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
            )
            offset(amount=thickness, side=Side.LEFT)
        make_face()
        mirror(about=Plane.YZ)
    extrude(amount=width / 2)
    mirror(about=Plane.XY)
# [extrude_builder]
builder_result = bracket.part

# [extrude_algebra]
profile = FilletPolyline(
    (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
)
sketch = make_face(offset(profile, amount=thickness, side=Side.LEFT))
sketch += mirror(sketch, about=Plane.YZ)

bracket = extrude(sketch, amount=width / 2)
bracket += mirror(bracket, about=Plane.XY)
# [extrude_algebra]

assert same(builder_result, bracket)
assert len(bracket.solids()) == 1 and bracket.is_valid
size = bracket.bounding_box().size
assert abs(size.X - length) < 1e-6 and abs(size.Z - width) < 1e-6

# ---------------------------------------------------------------------------
# Step 9: fillets
# ---------------------------------------------------------------------------

# [fillet_builder]
with BuildPart() as bracket:
    with BuildSketch() as sketch:
        with BuildLine() as profile:
            FilletPolyline(
                (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
            )
            offset(amount=thickness, side=Side.LEFT)
        make_face()
        mirror(about=Plane.YZ)
    extrude(amount=width / 2)
    mirror(about=Plane.XY)

    corners = bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[-1]
    fillet(corners, radius=fillet_radius)
# [fillet_builder]
builder_result = bracket.part

# [fillet_algebra]
profile = FilletPolyline(
    (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
)
sketch = make_face(offset(profile, amount=thickness, side=Side.LEFT))
sketch += mirror(sketch, about=Plane.YZ)

bracket = extrude(sketch, amount=width / 2)
bracket += mirror(bracket, about=Plane.XY)

corners = bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[-1]
bracket = fillet(corners, radius=fillet_radius)
# [fillet_algebra]

assert same(builder_result, bracket)
assert len(bracket.solids()) == 1 and bracket.is_valid
assert len(corners) == 4

# ---------------------------------------------------------------------------
# Step 10: holes and a slot
# ---------------------------------------------------------------------------

# [holes_builder]
with BuildPart() as bracket:
    with BuildSketch() as sketch:
        with BuildLine() as profile:
            FilletPolyline(
                (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
            )
            offset(amount=thickness, side=Side.LEFT)
        make_face()
        mirror(about=Plane.YZ)
    extrude(amount=width / 2)
    mirror(about=Plane.XY)

    corners = bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[-1]
    fillet(corners, radius=fillet_radius)

    with Locations(bracket.faces().sort_by(Axis.X)[-1]):
        Hole(hole_diameter / 2)

    with BuildSketch(bracket.faces().sort_by(Axis.Y)[0]):
        SlotOverall(slot_length, hole_diameter)
    extrude(amount=-thickness, mode=Mode.SUBTRACT)
# [holes_builder]
builder_result = bracket.part

# [holes_algebra]
profile = FilletPolyline(
    (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
)
sketch = make_face(offset(profile, amount=thickness, side=Side.LEFT))
sketch += mirror(sketch, about=Plane.YZ)

bracket = extrude(sketch, amount=width / 2)
bracket += mirror(bracket, about=Plane.XY)

corners = bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[-1]
bracket = fillet(corners, radius=fillet_radius)

side = bracket.faces().sort_by(Axis.X)[-1]
bracket -= Plane(side) * Hole(hole_diameter / 2, depth=length)

front = bracket.faces().sort_by(Axis.Y)[0]
slot = Plane(front) * SlotOverall(slot_length, hole_diameter)
bracket -= extrude(slot, amount=-thickness)
# [holes_algebra]

assert same(builder_result, bracket)
assert len(bracket.solids()) == 1 and bracket.is_valid
