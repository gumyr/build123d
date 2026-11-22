"""
Joints documentation examples

name: joints_examples.py
by:   Gumyr
date: November 15th 2026

desc:
    Every tested code example of the "Joints" how-to guide lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. It draws no pictures; the
    larger joint examples have scripts of their own.

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

# ---------------------------------------------------------------------------
# give a part a joint
# ---------------------------------------------------------------------------

# [bind]
with BuildPart() as plate:
    Box(100, 100, 10)
    RigidJoint("top", joint_location=Location((0, 0, 5)))
# [bind]

builder_joint = plate.part.joints["top"].location.position

# [bind_algebra]
plate = Box(100, 100, 10)
RigidJoint("top", plate, Location((0, 0, 5)))
# [bind_algebra]

assert list(plate.joints) == ["top"]
assert (plate.joints["top"].location.position - builder_joint).length < 1e-9

# [bind_free]
plate = Box(100, 100, 10)
top = RigidJoint("top", joint_location=Location((0, 0, 5)))  # free: no part yet

plate.joints["top"] = top  # bound to the plate, which stays the same object
# [bind_free]

assert list(plate.joints) == ["top"]

# [bind_plus]
plate = Box(100, 100, 10)
plate += RigidJoint("top", joint_location=Location((0, 0, 5)))  # a new plate
# [bind_plus]

assert list(plate.joints) == ["top"]

# ---------------------------------------------------------------------------
# a joint at every hole
# ---------------------------------------------------------------------------

# [bulk]
with BuildPart() as plate:
    Box(100, 100, 10)
    with Locations(plate.faces().sort_by(Axis.Z)[-1]):
        with GridLocations(60, 60, 2, 2):
            Hole(5)
            RigidJoint("mount")
# [bulk]

builder_plate = plate.part

# [bulk_algebra]
plate = Box(100, 100, 10)
holes = Plane(plate.faces().sort_by(Axis.Z)[-1]) * GridLocations(60, 60, 2, 2)
plate -= holes * Hole(5, depth=10)
plate += holes * RigidJoint("mount")
# [bulk_algebra]

assert abs(builder_plate.volume - plate.volume) < 1e-6
assert sorted(plate.joints) == sorted(builder_plate.joints)
assert sorted(plate.joints) == ["mount0", "mount1", "mount2", "mount3"]
for label, joint in plate.joints.items():
    assert (
        joint.location.position - builder_plate.joints[label].location.position
    ).length < 1e-9

# ---------------------------------------------------------------------------
# connect two parts
# ---------------------------------------------------------------------------

# [attach]
post = Cylinder(4, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
RigidJoint("base", post, Location((0, 0, 0)))

plate.joints["mount0"].attach(post.joints["base"])
# [attach]

# the plate has not moved; the post now stands on the first hole
assert (post.location.position - plate.joints["mount0"].location.position).length < 1e-9
assert abs(post.bounding_box().min.Z - 5) < 1e-6

# ---------------------------------------------------------------------------
# a joint that moves
# ---------------------------------------------------------------------------

# [hinge]
frame = Box(4, 4, 60, align=(Align.MAX, Align.CENTER, Align.MIN))
RevoluteJoint("hinge", frame, axis=Axis((0, 0, 0), (0, 0, 1)), angular_range=(0, 120))

door = Box(40, 2, 60, align=(Align.MIN, Align.CENTER, Align.MIN))
RigidJoint("hinge", door, Location((0, 0, 0)))

frame.joints["hinge"].attach(door.joints["hinge"], angle=60)
# [hinge]

# the door has swung 60 degrees about the Z axis
assert abs(door.bounding_box().size.X - (40 * 0.5 + 2 * 0.8660254)) < 1e-3
try:
    frame.joints["hinge"].attach(door.joints["hinge"], angle=150)
    raise AssertionError("an angle outside the range should be refused")
except ValueError:
    pass
