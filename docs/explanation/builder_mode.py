"""
How builder mode works documentation examples

name: builder_mode.py
by:   Gumyr
date: November 16th 2026

desc:
    The code of the "How builder mode works" page, between pairs of
    ``# [name]`` markers that the page includes with ``literalinclude``,
    with checks of what the page says about each.

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
# pylint: disable=expression-not-assigned, pointless-statement

import os
import tempfile

from build123d import *

# ---------------------------------------------------------------------------
# a builder is a tool, not the object
# ---------------------------------------------------------------------------

# [tool]
with BuildPart() as example:
    with BuildSketch() as base:
        Rectangle(20, 20)
    extrude(amount=10)  # a block
    with BuildSketch(example.faces().sort_by(Axis.Z)[-1]) as bore:
        Circle(5)
    extrude(amount=-5, mode=Mode.SUBTRACT)  # with a hole in the top

result = example.part  # the part that was built
# [tool]

assert isinstance(result, Part) and not isinstance(example, Part)
assert abs(result.volume - (20 * 20 * 10 - Circle(5).area * 5)) < 1e-6

# ---------------------------------------------------------------------------
# objects find their builder
# ---------------------------------------------------------------------------

# [scope]
with BuildPart() as part_builder:
    Box(10, 10, 10)  # goes to part_builder
    with BuildSketch() as sketch_builder:
        Circle(2)  # goes to sketch_builder
# [scope]

assert len(part_builder.part.solids()) == 1 and len(sketch_builder.sketch.faces()) == 1

# [moved_wrong]
with BuildPart() as wrong:
    Cylinder(1, 2).moved(Location((1, 2, 3)))
# [moved_wrong]

# the cylinder went into the part where it was made; the moved copy was dropped
assert wrong.part.center().length < 1e-9

# [moved_right]
with BuildPart() as right:
    with Locations((1, 2, 3)):
        Cylinder(1, 2)
# [moved_right]

assert (right.part.center() - Vector(1, 2, 3)).length < 1e-9

# the same thing in ordinary Python, run in a scratch directory
home = os.getcwd()
with tempfile.TemporaryDirectory() as scratch:
    os.chdir(scratch)
    # [file_analogy]
    with open("test.txt", "w") as f:
        f.write("text").to_bytes(1, "big")
    # [file_analogy]
    with open("test.txt", "w") as f:
        discarded = f.write("text").to_bytes(1, "big")
    with open("test.txt") as f:
        written = f.read()
    os.chdir(home)

# the file has the text; what came after the write was worked out and dropped
assert written == "text" and discarded == b"\x04"

# ---------------------------------------------------------------------------
# algebra inside a builder
# ---------------------------------------------------------------------------

# [algebra_wrong]
with BuildSketch() as washer:
    ring = Circle(10) - Circle(5)
# [algebra_wrong]

# the variable holds a ring, but the sketch got both circles added: a disc
assert abs(ring.area - (Circle(10).area - Circle(5).area)) < 1e-6
assert abs(washer.sketch.area - Circle(10).area) < 1e-6

# [algebra_private]
with BuildSketch() as washer:
    ring = Circle(10, mode=Mode.PRIVATE) - Circle(5, mode=Mode.PRIVATE)
    insert(ring)
# [algebra_private]

assert abs(washer.sketch.area - ring.area) < 1e-6

# [algebra_builder]
with BuildSketch() as washer:
    Circle(10)
    Circle(5, mode=Mode.SUBTRACT)
# [algebra_builder]

assert abs(washer.sketch.area - ring.area) < 1e-6

# ---------------------------------------------------------------------------
# builders have modes too
# ---------------------------------------------------------------------------

# [builder_mode_sketch]
with BuildSketch() as plate:
    Rectangle(60, 40)
    with BuildSketch(Pos(15, 0), mode=Mode.SUBTRACT) as window:
        Rectangle(20, 10)
        Circle(8)
# [builder_mode_sketch]

# the window is built whole, a rectangle joined to a circle, and then cut out
assert len(window.sketch.faces()) == 1
assert abs(plate.sketch.area - (60 * 40 - window.sketch.area)) < 1e-6

# [builder_mode_part]
with BuildPart() as mould:
    Box(40, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildPart(Pos(0, 0, 4), mode=Mode.SUBTRACT) as plug:
        Cone(8, 14, 16, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Cylinder(3, 16, align=(Align.CENTER, Align.CENTER, Align.MIN))
# [builder_mode_part]

assert abs(mould.part.volume - (40 * 40 * 20 - plug.part.volume)) < 1e-6

# [builder_mode_private]
with BuildPart() as block:
    with BuildSketch(mode=Mode.PRIVATE) as guide:
        RegularPolygon(15, 6)
    waiting_after_guide = len(block.pending_faces)  # 0: the guide is kept out
    with BuildSketch() as base:
        Circle(20)
    waiting_after_base = len(block.pending_faces)  # 1: the base is waiting
    extrude(amount=5)
# [builder_mode_private]

assert (waiting_after_guide, waiting_after_base) == (0, 1)
assert abs(block.part.volume - Circle(20).area * 5) < 1e-6

# ---------------------------------------------------------------------------
# built locally, placed on exit
# ---------------------------------------------------------------------------

# [placement]
with BuildSketch(Plane.XZ) as profile:
    Circle(5)

profile.sketch_local  # the circle as drawn, flat on Plane.XY
profile.sketch  # the circle where it was put, standing in Plane.XZ
# [placement]

assert profile.sketch_local.bounding_box().size.Z < 1e-6
assert profile.sketch.bounding_box().size.Y < 1e-6

# [six_faces]
with BuildPart() as badges:
    Box(3, 3, 3)
    with BuildSketch(*badges.faces()):
        Rectangle(1, 2, rotation=45)
    extrude(amount=0.1)
# [six_faces]

assert abs(badges.part.volume - (27 + 6 * 2 * 0.1)) < 1e-6

# [locations_inside]
with BuildPart() as inside:
    with Locations((0, 10), (0, -10)):
        Box(1, 1, 1)
        with GridLocations(5, 5, 2, 2):
            Sphere(1)
        Cylinder(1, 1)
# [locations_inside]

assert abs(inside.part.bounding_box().size.Y - (20 + 5 + 2)) < 1e-6

# [locations_around]
with BuildPart() as model:
    with Locations((-20, 0), (20, 0)):
        with BuildSketch() as holes:
            Circle(3)
        extrude(amount=5)
# [locations_around]

# drawn once, placed twice
assert len(holes.sketch_local.faces()) == 1 and len(holes.sketch.faces()) == 2
assert len(model.part.solids()) == 2

# [locations_part]
with Locations((-10, 0), (10, 0)):
    with BuildPart() as placed_parts:
        Box(5, 5, 5)
# [locations_part]

assert (
    len(placed_parts.part_local.solids()) == 1 and len(placed_parts.part.solids()) == 2
)


# [function]
def knob(count: int) -> BuildPart:
    with GridLocations(0, 20, 1, count):
        with BuildPart() as builder:
            Box(100, 10, 5)
    return builder


with BuildPart() as knobs:
    for count in range(1, 4):
        with Locations((0, 0, 20 * count)):
            insert(knob(count))
# [function]

# three rows of 1, 2 and 3 boxes
assert len(knobs.part.solids()) == 6
assert sorted({round(solid.center().Z) for solid in knobs.part.solids()}) == [
    20,
    40,
    60,
]

# ---------------------------------------------------------------------------
# pending objects
# ---------------------------------------------------------------------------

# [pending]
with BuildPart() as pillow_block:
    with BuildSketch() as plan:
        Rectangle(80, 60)
        fillet(plan.vertices(), radius=10)
    waiting = len(pillow_block.pending_faces)  # 1: the sketch is waiting
    extrude(amount=20)
    left = len(pillow_block.pending_faces)  # 0: extrude used it
# [pending]

assert (waiting, left) == (1, 0)

# ---------------------------------------------------------------------------
# when the block ends
# ---------------------------------------------------------------------------

# [exit]
with BuildPart() as bracket_builder:
    bracket_builder.label = "bracket"
    bracket_builder.color = "steelblue"
    bracket_builder.material = "stainless"
    Box(20, 10, 5)

bracket_builder.part.label  # "bracket"
# [exit]

assert bracket_builder.part.label == "bracket"
assert bracket_builder.part.color == Color("steelblue")
assert bracket_builder.part.material is not None

# [exit_late]
bracket_builder.label = "late"  # too late: the part is already made
bracket_builder.part.label  # still "bracket"

bracket_builder.part.label = "renamed"  # change the part itself instead
# [exit_late]

assert bracket_builder.part.label == "renamed"
