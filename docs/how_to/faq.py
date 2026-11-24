"""
Frequently asked questions documentation examples

name: faq.py
by:   Gumyr
date: November 15th 2026

desc:
    The code of the "Frequently asked questions" page, between pairs of
    ``# [name]`` markers that the page includes with ``literalinclude``.
    Each example is followed by checks of what the page says about it.

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

from build123d import *

box = Box(60, 40, 20)
top = box.faces().sort_by(Axis.Z)[-1]
bottom = box.faces().sort_by(Axis.Z)[0]

# ---------------------------------------------------------------------------
# the origin of a sketch on a face
# ---------------------------------------------------------------------------

# [face_origin]
on_top = Plane(top)  # origin at the centre of the face
at_corner = on_top.shift_origin(top.vertices().group_by(Axis.X)[0].sort_by(Axis.Y)[0])
# [face_origin]

assert (on_top.origin - top.center()).length < 1e-9
assert (at_corner.origin - Vector(-30, -20, 10)).length < 1e-9

# ---------------------------------------------------------------------------
# a sketch that comes out turned on a face
# ---------------------------------------------------------------------------

# [face_x_dir]
on_top = Plane(top, x_dir=(0, 1, 0))  # the sketch's X will run along world Y
slot = on_top * SlotOverall(20, 5)
# [face_x_dir]

assert abs(slot.bounding_box().size.Y - 20) < 1e-6

# ---------------------------------------------------------------------------
# which way extrude goes
# ---------------------------------------------------------------------------

# [extrude_direction]
boss = extrude(Plane(top) * Circle(5), amount=5)  # out of the top, upward
foot = extrude(Plane(bottom) * Circle(5), amount=5)  # out of the bottom, downward
pocket = extrude(Plane(top) * Circle(5), amount=-5)  # into the box
# [extrude_direction]

assert abs(boss.bounding_box().max.Z - 15) < 1e-6
assert abs(foot.bounding_box().min.Z + 15) < 1e-6
assert abs(pocket.bounding_box().min.Z - 5) < 1e-6

# ---------------------------------------------------------------------------
# a mirrored part in the wrong place
# ---------------------------------------------------------------------------

# [mirror_plane]
part = Pos(20, 10, 0) * Box(10, 10, 10)

mirror(part)  # in Plane.XZ, the default: lands at (20, -10, 0)
mirror(part, about=Plane.YZ)  # lands at (-20, 10, 0)
mirror(part, about=Plane(part.faces().sort_by(Axis.X)[0]))  # in its own left face
# [mirror_plane]

assert (mirror(part).center() - Vector(20, -10, 0)).length < 1e-9
assert (mirror(part, about=Plane.YZ).center() - Vector(-20, 10, 0)).length < 1e-9
own = mirror(part, about=Plane(part.faces().sort_by(Axis.X)[0]))
assert (own.center() - Vector(10, 10, 0)).length < 1e-9

# ---------------------------------------------------------------------------
# no current point
# ---------------------------------------------------------------------------

# [current_point]
l1 = Line((0, 0), (40, 0))
l2 = Line(l1 @ 1, l1 @ 1 + (0, 15))  # starts where l1 ended
l3 = Line(l2 @ 1, l1 @ 0)  # and back to where l1 began
# [current_point]

assert Wire([l1, l2, l3]).is_closed

# ---------------------------------------------------------------------------
# an outline that will not make a face
# ---------------------------------------------------------------------------

# [closed_outline]
open_outline = Polyline((0, 0), (10, 0), (10, 5))
closed_outline = Polyline((0, 0), (10, 0), (10, 5), close=True)

face = make_face(closed_outline)
# [closed_outline]

assert abs(face.area - 25) < 1e-9
try:
    make_face(open_outline)
    raise AssertionError("an open outline should be refused")
except ValueError as error:
    assert "closed" in str(error)

# ---------------------------------------------------------------------------
# a selection that returns nothing
# ---------------------------------------------------------------------------

# [selector_kinds]
rounded = fillet(Box(60, 40, 20).edges().filter_by(Axis.Z), 5)

rounded.edges().filter_by(Axis.Z)  # the 8 straight edges that run along Z
rounded.edges().filter_by(GeomType.CIRCLE)  # the 8 arcs of the rounded corners
rounded.faces().filter_by(GeomType.CIRCLE)  # nothing: a face is never a CIRCLE
rounded.faces().filter_by(GeomType.CYLINDER)  # the 4 rounded corners
# [selector_kinds]

assert len(rounded.edges().filter_by(Axis.Z)) == 8
assert len(rounded.edges().filter_by(GeomType.CIRCLE)) == 8
assert len(rounded.faces().filter_by(GeomType.CIRCLE)) == 0
assert len(rounded.faces().filter_by(GeomType.CYLINDER)) == 4

# ---------------------------------------------------------------------------
# what the last operation made
# ---------------------------------------------------------------------------

# [select_last]
with BuildPart() as block:
    Box(60, 40, 20)
    with Locations((0, 0, 10)):
        Cylinder(8, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    fillet(block.edges(Select.LAST).group_by(Axis.Z)[-1], 2)  # the boss's top rim
# [select_last]

assert block.part.is_valid and block.part.volume < 60 * 40 * 20 + Cylinder(8, 10).volume

# ---------------------------------------------------------------------------
# a fillet that fails
# ---------------------------------------------------------------------------

# [fillet_limit]
block = Box(60, 40, 20)

largest = block.max_fillet(block.edges(), max_iterations=30)  # just under 10
block = fillet(block.edges(), 8)
# [fillet_limit]

assert 9.5 < largest < 10
assert block.is_valid
try:
    fillet(Box(60, 40, 20).edges(), 12)
    raise AssertionError("a fillet wider than the part should be refused")
except ValueError as error:
    assert "max_fillet" in str(error)

# ---------------------------------------------------------------------------
# a part that moves when a joint is attached
# ---------------------------------------------------------------------------

# [attach_moves]
plate = Box(60, 40, 5)
RigidJoint("top", plate, Location((0, 0, 2.5)))

post = Cylinder(4, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
RigidJoint("base", post, Location((0, 0, 0)))

plate.joints["top"].attach(post.joints["base"])  # the plate stays; the post moves
# [attach_moves]

assert plate.location.position.length < 1e-9
assert (post.location.position - Vector(0, 0, 2.5)).length < 1e-9
