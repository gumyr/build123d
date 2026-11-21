"""
A pipe with a flange on each end, placed with rigid joints

name: rigid_joints_pipe.py
by:   Gumyr
date: November 15th 2026

desc:
    The rigid joint example of the "Joints" how-to guide, written in builder
    and in algebra mode between pairs of ``# [name]`` markers that the page
    includes with ``literalinclude``. The two versions are checked against
    each other. The picture on the page is made from this script by
    ``joints_shots.py``.

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

# [pipe]
import copy

from build123d import *

pipe_radius, wall = 50, 4

# A simple flange: a disc with bolt holes and a neck, bored for the pipe.
# It stands on its mating face, with the neck uppermost.
with BuildPart() as flange_builder:
    Cylinder(90, 12, align=(Align.CENTER, Align.CENTER, Align.MIN))
    Cylinder(60, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
    Cylinder(
        pipe_radius - wall,
        30,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
        mode=Mode.SUBTRACT,
    )
    with PolarLocations(75, 8):
        Cylinder(
            5, 12, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT
        )
    # where the pipe is welded on: the end of the neck, facing back down it
    RigidJoint("pipe", joint_location=Location((0, 0, 30), (180, 0, 0)))
    # where the next flange bolts on: the mating face, facing outward
    RigidJoint("face", joint_location=Location((0, 0, 0), (180, 0, 0)))

flange_inlet = flange_builder.part
flange_outlet = copy.copy(flange_inlet)

with BuildPart() as pipe_builder:
    # the pipe: a ring swept along an arc
    with BuildLine():
        path = TangentArc((0, 0, 0), (600, 0, 300), tangent=(1, 0, 0))
    with BuildSketch(Plane(origin=path @ 0, z_dir=path % 0)):
        Circle(pipe_radius)
        Circle(pipe_radius - wall, mode=Mode.SUBTRACT)
    sweep()

    # a joint at each end, facing out of the pipe
    RigidJoint(label="inlet", joint_location=-path.location_at(0))
    RigidJoint(label="outlet", joint_location=path.location_at(1))

pipe = pipe_builder.part

# place the flanges on the ends of the pipe
pipe.joints["inlet"].attach(flange_inlet.joints["pipe"])
pipe.joints["outlet"].attach(flange_outlet.joints["pipe"])
# [pipe]

builder_pipe, builder_inlet, builder_outlet = pipe, flange_inlet, flange_outlet

# [pipe_algebra]
import copy

from build123d import *

pipe_radius, wall = 50, 4
on_face = (Align.CENTER, Align.CENTER, Align.MIN)

# A simple flange: a disc with bolt holes and a neck, bored for the pipe.
# It stands on its mating face, with the neck uppermost.
flange_inlet = Cylinder(90, 12, align=on_face) + Cylinder(60, 30, align=on_face)
flange_inlet -= Cylinder(pipe_radius - wall, 30, align=on_face)
flange_inlet -= PolarLocations(75, 8) * Cylinder(5, 12, align=on_face)
# where the pipe is welded on: the end of the neck, facing back down it
RigidJoint("pipe", flange_inlet, Location((0, 0, 30), (180, 0, 0)))
# where the next flange bolts on: the mating face, facing outward
RigidJoint("face", flange_inlet, Location((0, 0, 0), (180, 0, 0)))

flange_outlet = copy.copy(flange_inlet)

# the pipe: a ring swept along an arc
path = TangentArc((0, 0, 0), (600, 0, 300), tangent=(1, 0, 0))
ring = Circle(pipe_radius) - Circle(pipe_radius - wall)
pipe = sweep(Plane(origin=path @ 0, z_dir=path % 0) * ring, path)

# a joint at each end, facing out of the pipe
RigidJoint("inlet", pipe, -path.location_at(0))
RigidJoint("outlet", pipe, path.location_at(1))

# place the flanges on the ends of the pipe
pipe.joints["inlet"].attach(flange_inlet.joints["pipe"])
pipe.joints["outlet"].attach(flange_outlet.joints["pipe"])
# [pipe_algebra]

for builder_made, algebra_made in (
    (builder_pipe, pipe),
    (builder_inlet, flange_inlet),
    (builder_outlet, flange_outlet),
):
    assert abs(builder_made.volume - algebra_made.volume) < 1e-6
    assert (
        builder_made.bounding_box().min - algebra_made.bounding_box().min
    ).length < 1e-6
    assert (
        builder_made.bounding_box().max - algebra_made.bounding_box().max
    ).length < 1e-6
# each flange is on its end of the pipe, neck toward the pipe and face outward
assert flange_inlet.bounding_box().min.X < -29 and flange_inlet.bounding_box().max.X < 1
assert (flange_outlet.center() - path @ 1).length < 30
assert (flange_outlet.joints["face"].location.position - path @ 1).length > 29
# the pipe has not moved
assert (pipe.joints["inlet"].location.position - path @ 0).length < 1e-9
