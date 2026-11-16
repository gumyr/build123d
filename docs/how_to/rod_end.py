"""
A rod end: a ball held in a socket by a ball joint

name: rod_end.py
by:   Gumyr
date: November 15th 2026

desc:
    The ball joint example of the "Joints" how-to guide, written in builder
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

# [rod_end]
from build123d import *

inner_radius = 15.89 / 2  # of the socket
inner_gap = 0.2  # between the socket and the ball
shaft_radius = 2.5

with BuildPart() as rod_end_builder:
    # the outer shape: a disc drawn out to a neck, turned about the neck
    with BuildSketch():
        Circle(22.25 / 2)
        with Locations((0, -12)):
            Rectangle(8, 1)
        make_hull()
        split(bisect_by=Plane.YZ)
    revolve(axis=Axis.Y)
    # trimmed to thickness, with chamfered rims
    with BuildSketch(Plane.YZ) as trim:
        Rectangle(25, 8, align=(Align.MIN, Align.CENTER))
        Rectangle(9, 10, align=(Align.MIN, Align.CENTER))
        chamfer(trim.vertices(), 0.5)
    revolve(axis=Axis.Z, mode=Mode.INTERSECT)
    # the shaft
    Cylinder(
        shaft_radius,
        30,
        rotation=(90, 0, 0),
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    # the socket
    Sphere(inner_radius, mode=Mode.SUBTRACT)
    # the ball joint, at the centre of the socket, with the tilt it allows
    BallJoint(
        "socket",
        joint_location=Location(),
        angular_range=((-14, 14), (-14, 14), (-180, 180)),
    )

with BuildPart() as ball_builder:
    Sphere(inner_radius - inner_gap)
    Box(50, 50, 13, mode=Mode.INTERSECT)
    Hole(4)
    RigidJoint("ball", joint_location=Location())

rod_end, ball = rod_end_builder.part, ball_builder.part
ball.color = Color("aliceblue")

rod_end.joints["socket"].attach(ball.joints["ball"], angles=(5, 10, 0))
# [rod_end]

builder_rod_end, builder_ball = rod_end, ball

# [rod_end_algebra]
from build123d import *

inner_radius = 15.89 / 2  # of the socket
inner_gap = 0.2  # between the socket and the ball
shaft_radius = 2.5

# the outer shape: a disc drawn out to a neck, turned about the neck
outline = make_hull((Circle(22.25 / 2) + Pos(0, -12) * Rectangle(8, 1)).edges())
rod_end = revolve(split(outline, bisect_by=Plane.YZ), Axis.Y)
# trimmed to thickness, with chamfered rims
trim = Rectangle(25, 8, align=(Align.MIN, Align.CENTER))
trim += Rectangle(9, 10, align=(Align.MIN, Align.CENTER))
trim = chamfer(trim.vertices(), 0.5)
rod_end &= revolve(Plane.YZ * trim, Axis.Z)
# the shaft
rod_end += Cylinder(
    shaft_radius,
    30,
    rotation=(90, 0, 0),
    align=(Align.CENTER, Align.CENTER, Align.MIN),
)
# the socket
rod_end -= Sphere(inner_radius)
# the ball joint, at the centre of the socket, with the tilt it allows
BallJoint(
    "socket",
    rod_end,
    Location(),
    angular_range=((-14, 14), (-14, 14), (-180, 180)),
)

ball = Sphere(inner_radius - inner_gap) & Box(50, 50, 13)
ball -= Cylinder(4, 13)
ball.color = Color("aliceblue")
RigidJoint("ball", ball, Location())

rod_end.joints["socket"].attach(ball.joints["ball"], angles=(5, 10, 0))
# [rod_end_algebra]

for builder_made, algebra_made in ((builder_rod_end, rod_end), (builder_ball, ball)):
    # the hull is computed from slightly different edges in the two modes
    assert abs(builder_made.volume - algebra_made.volume) < 1e-5 * algebra_made.volume
    assert (
        builder_made.bounding_box().size - algebra_made.bounding_box().size
    ).length < 1e-5
# the ball is tilted in the socket and still centred on it
assert ball.center().length < 1e-6
assert tuple(round(angle) for angle in ball.orientation) != (0, 0, 0)
# a tilt beyond the range the joint allows is refused
try:
    rod_end.joints["socket"].attach(ball.joints["ball"], angles=(20, 0, 0))
    raise AssertionError("a tilt outside the range should be refused")
except ValueError:
    pass
