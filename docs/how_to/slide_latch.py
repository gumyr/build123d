"""
A slide latch: a bolt that slides in its housing on a linear joint

name: slide_latch.py
by:   Gumyr
date: November 15th 2026

desc:
    The linear joint example of the "Joints" how-to guide, written in builder
    and in algebra mode between pairs of ``# [name]`` markers that the page
    includes with ``literalinclude``. The two versions are checked against
    each other.

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

# [latch]
from build123d import *

with BuildPart() as latch_builder:
    # a box with rounded corners to start with
    Box(70, 30, 14)
    end = latch_builder.faces().sort_by(Axis.X)[-1]  # save the end with the hole
    fillet(latch_builder.edges().filter_by(Axis.Z), 2)
    fillet(latch_builder.edges().sort_by(Axis.Z)[-1], 1)
    # the screw tabs
    with BuildSketch(latch_builder.faces().sort_by(Axis.Z)[0]) as tabs:
        with Locations((-30, 0), (30, 0)):
            SlotOverall(50, 10, rotation=90)
        Rectangle(50, 30)
        fillet(tabs.vertices(Select.LAST), radius=2)
    extrude(amount=-2)
    with GridLocations(60, 40, 2, 2):
        Hole(2)
    # the hole the slide runs in, made from the end saved earlier
    with BuildSketch(end) as slide_hole:
        insert(end)
        offset(amount=-2)
        fillet(slide_hole.vertices(), 1)
    extrude(amount=-68, mode=Mode.SUBTRACT)
    # the slot the knob travels in
    with BuildSketch(latch_builder.faces().sort_by(Axis.Z)[-1]):
        SlotOverall(32, 8)
    extrude(amount=-2, mode=Mode.SUBTRACT)
    # the slide moves along the X axis, 12 mm each way
    LinearJoint("latch", axis=Axis.X, linear_range=(-12, 12))

with BuildPart() as slide_builder:
    # the slide is a little smaller than the hole
    with BuildSketch():
        insert(slide_hole.sketch)
        offset(amount=-0.25)
    # it is longer one way than the other
    extrude(amount=46)
    extrude(slide_builder.faces().sort_by(Axis.Z)[0], amount=20)
    # round off the ends
    fillet(slide_builder.edges().group_by(Axis.Z)[0], 1)
    fillet(slide_builder.edges().group_by(Axis.Z)[-1], 1)
    # the knob
    with BuildSketch() as knob:
        with Locations((12, 0)):
            SlotOverall(15, 4, rotation=90)
        Rectangle(12, 7, align=(Align.MIN, Align.CENTER))
        fillet(knob.vertices(Select.LAST), 1)
        split(bisect_by=Plane.XZ)
    revolve(axis=Axis.X)
    # the joint lies along the slide, turned so that the knob ends up on top
    RigidJoint("slide", joint_location=Location(-Plane.ZY))

latch, slide = latch_builder.part, slide_builder.part

# put the slide in the latch, at a position from -12 to 12
latch.joints["latch"].attach(slide.joints["slide"], position=12)
# [latch]

builder_latch, builder_slide = latch, slide

# [latch_algebra]
from build123d import *

# a box with rounded corners to start with
latch = Box(70, 30, 14)
end = latch.faces().sort_by(Axis.X)[-1]  # save the end with the hole
latch = fillet(latch.edges().filter_by(Axis.Z), 2)
latch = fillet(latch.edges().sort_by(Axis.Z)[-1], 1)
# the screw tabs
tabs = Pos(-30, 0) * SlotOverall(50, 10, rotation=90)
tabs += Pos(30, 0) * SlotOverall(50, 10, rotation=90)
tabs += Rectangle(50, 30)
tabs = fillet(tabs.vertices(Select.LAST), radius=2)
latch += extrude(Plane(latch.faces().sort_by(Axis.Z)[0]) * tabs, amount=-2)
latch -= GridLocations(60, 40, 2, 2) * Cylinder(2, 14)
# the hole the slide runs in, made from the end saved earlier
slide_hole = offset(end, amount=-2)
slide_hole = fillet(slide_hole.vertices(), 1)
latch -= extrude(slide_hole, amount=-68)
# the slot the knob travels in
top = Plane(latch.faces().sort_by(Axis.Z)[-1])
latch -= extrude(top * SlotOverall(32, 8), amount=-2)
# the slide moves along the X axis, 12 mm each way
LinearJoint("latch", latch, axis=Axis.X, linear_range=(-12, 12))

# the slide is a little smaller than the hole, and is drawn flat
profile = offset(Plane(end).to_local_coords(slide_hole), amount=-0.25)
# it is longer one way than the other
slide = extrude(profile, amount=46)
slide += extrude(slide.faces().sort_by(Axis.Z)[0], amount=20)
# round off the ends
slide = fillet(slide.edges().group_by(Axis.Z)[0], 1)
slide = fillet(slide.edges().group_by(Axis.Z)[-1], 1)
# the knob
knob = Pos(12, 0) * SlotOverall(15, 4, rotation=90)
knob += Rectangle(12, 7, align=(Align.MIN, Align.CENTER))
knob = fillet(knob.vertices(Select.LAST), 1)
slide += revolve(split(knob, bisect_by=Plane.XZ), Axis.X)
# the joint lies along the slide, turned so that the knob ends up on top
RigidJoint("slide", slide, Location(-Plane.ZY))

# put the slide in the latch, at a position from -12 to 12
latch.joints["latch"].attach(slide.joints["slide"], position=12)
# [latch_algebra]

for builder_made, algebra_made in ((builder_latch, latch), (builder_slide, slide)):
    assert abs(builder_made.volume - algebra_made.volume) < 1e-6
    assert (
        builder_made.bounding_box().min - algebra_made.bounding_box().min
    ).length < 1e-6
    assert (
        builder_made.bounding_box().max - algebra_made.bounding_box().max
    ).length < 1e-6
# the slide is inside the latch with its knob on top, pushed 12 toward +X
assert abs(slide.bounding_box().max.Z - 14) < 1e-6
assert abs(slide.bounding_box().max.X - 58) < 1e-6
# a position beyond the travel is refused
try:
    latch.joints["latch"].attach(slide.joints["slide"], position=20)
    raise AssertionError("a position outside the range should be refused")
except ValueError:
    pass
latch.joints["latch"].attach(slide.joints["slide"], position=12)
