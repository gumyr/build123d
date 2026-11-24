"""
A spiral ramp tutorial

name: spiral_ramp.py
by:   Gumyr
date: November 20th 2026

desc:
    Every code example in the "A spiral ramp" tutorial lives here, between
    pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. Each step is written twice, in builder and in algebra
    mode, and shows the whole part as it stands at that point; the two are
    checked against each other. The rendered pictures on the page are made
    from this script by ``spiral_ramp_shots.py``.

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

from math import asin, degrees, pi

from build123d.topology import Shape

# [setup]
from build123d import *

width = 10  # width of the channel
lip = 2  # height of the walls above the floor
wall = 1  # thickness of the floor and of the walls
radius = 100  # radius of the spiral, to the middle of the channel
pitch = 30  # how far the ramp climbs in one full turn
turns = 0.5  # how much of a turn the ramp makes
lift = 30  # height of the low end of the ramp above the ground
# [setup]


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-3
        and abs(first.area - second.area) < 1e-3
        and (box_1.min - box_2.min).length < 1e-4
        and (box_1.max - box_2.max).length < 1e-4
        and len(first.faces()) == len(second.faces())
    )


def floor_tilt(swept: Shape) -> float:
    """How far, in degrees, the floor of the channel leans toward the axis of
    the spiral half way along it; zero for a floor that is level across"""
    floor = swept.faces().group_by(Face.area)[-1].sort_by(Axis.Z)[-1]
    middle = floor.position_at(0.5, 0.5)
    outward = Vector(middle.X, middle.Y, 0).normalized()
    return degrees(asin(abs(floor.normal_at(middle).dot(outward))))


# ---------------------------------------------------------------------------
# Step 2: the section
# ---------------------------------------------------------------------------

# [section_builder]
with BuildSketch() as section:
    with BuildLine():
        Polyline((-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip))
        offset(amount=wall, side=Side.RIGHT)
    make_face()
# [section_builder]
builder_result = section.sketch

# [section_algebra]
outline = Polyline((-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip))
section = make_face(offset(outline, amount=wall, side=Side.RIGHT))
# [section_algebra]

assert same(builder_result, section)
assert len(section.faces()) == 1 and len(section.edges()) == 10
# the floor of the channel is at Y = 0 and the material is below and outside it
assert abs(section.bounding_box().min.Y + wall) < 1e-6
assert abs(section.bounding_box().size.X - (width + 2 * wall)) < 1e-6
flat_outline, flat_section = outline, section  # for the pictures

# ---------------------------------------------------------------------------
# Step 3: the path
# ---------------------------------------------------------------------------

# [path_builder]
with BuildPart() as ramp:
    with BuildLine():
        path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
    with BuildSketch(path.location_at(0)) as section:
        with BuildLine():
            Polyline(
                (-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip)
            )
            offset(amount=wall, side=Side.RIGHT)
        make_face()
# [path_builder]
builder_result = section.sketch

# [path_algebra]
outline = Polyline((-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip))
section = make_face(offset(outline, amount=wall, side=Side.RIGHT))

path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
section = path.location_at(0) * section
# [path_algebra]

assert same(builder_result, section)
assert (path @ 0 - Vector(radius, 0, lift)).length < 1e-6
assert abs((path @ 1).Z - (lift + pitch * turns)) < 1e-6
# the section stands across the start of the path: its normal is the tangent
assert (section.face().normal_at() - path % 0).length < 1e-6
climb = degrees(asin((path % 0).Z))  # the slope of the path
assert abs(climb - 2.73) < 0.01
placed_section = section  # for the pictures

# ---------------------------------------------------------------------------
# Step 4: the sweep
# ---------------------------------------------------------------------------

# [sweep_builder]
with BuildPart() as ramp:
    with BuildLine():
        path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
    with BuildSketch(path.location_at(0)) as section:
        with BuildLine():
            Polyline(
                (-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip)
            )
            offset(amount=wall, side=Side.RIGHT)
        make_face()
    sweep(is_frenet=True)
# [sweep_builder]
builder_result = ramp.part

# [sweep_algebra]
outline = Polyline((-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip))
section = make_face(offset(outline, amount=wall, side=Side.RIGHT))

path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
section = path.location_at(0) * section
ramp = sweep(section, path, is_frenet=True)
# [sweep_algebra]

assert same(builder_result, ramp)
assert ramp.is_valid and len(ramp.solids()) == 1 and len(ramp.faces()) == 12
# with is_frenet the floor is level across the channel; without it, it leans
assert floor_tilt(ramp) < 0.01
banked = sweep(section, path)
assert abs(floor_tilt(banked) - 4.33) < 0.05
swept = ramp  # the ramp before it has a base, for the pictures

# ---------------------------------------------------------------------------
# Step 5: the footprint
# ---------------------------------------------------------------------------

# [footprint_builder]
with BuildPart() as ramp:
    with BuildLine():
        path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
    with BuildSketch(path.location_at(0)) as section:
        with BuildLine():
            Polyline(
                (-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip)
            )
            offset(amount=wall, side=Side.RIGHT)
        make_face()
    sweep(is_frenet=True)

    with BuildSketch() as footprint:
        underside = ramp.faces().group_by(Face.area)[-1].sort_by(Axis.Z)[0]
        project_to_plane(underside, workplane=Plane.XY)
# [footprint_builder]
builder_result = footprint.sketch

# [footprint_algebra]
outline = Polyline((-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip))
section = make_face(offset(outline, amount=wall, side=Side.RIGHT))

path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
section = path.location_at(0) * section
ramp = sweep(section, path, is_frenet=True)

underside = ramp.faces().group_by(Face.area)[-1].sort_by(Axis.Z)[0]
footprint = project_to_plane(underside, Plane.XY)
# [footprint_algebra]

assert same(builder_result, footprint)
# two faces tie for the largest, the floor of the channel and the underside
assert len(ramp.faces().group_by(Face.area)[-1]) == 2
assert underside.normal_at(underside.center()).Z < -0.99
assert len(footprint.faces()) == 1 and len(footprint.edges()) == 4
# half a ring as wide as the channel, flat on the ground
ring = pi * ((radius + width / 2) ** 2 - (radius - width / 2) ** 2)
assert abs(footprint.area - turns * ring) < 0.01
assert abs(footprint.face().center().Z) < 1e-6

# ---------------------------------------------------------------------------
# Step 6: the base
# ---------------------------------------------------------------------------

# [base_builder]
with BuildPart() as ramp:
    with BuildLine():
        path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
    with BuildSketch(path.location_at(0)) as section:
        with BuildLine():
            Polyline(
                (-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip)
            )
            offset(amount=wall, side=Side.RIGHT)
        make_face()
    sweep(is_frenet=True)

    with BuildSketch() as footprint:
        underside = ramp.faces().group_by(Face.area)[-1].sort_by(Axis.Z)[0]
        project_to_plane(underside, workplane=Plane.XY)
    extrude(until=Until.NEXT)
# [base_builder]
builder_result = ramp.part

# [base_algebra]
outline = Polyline((-width / 2, lip), (-width / 2, 0), (width / 2, 0), (width / 2, lip))
section = make_face(offset(outline, amount=wall, side=Side.RIGHT))

path = Helix(pitch, pitch * turns, radius, center=(0, 0, lift))
section = path.location_at(0) * section
ramp = sweep(section, path, is_frenet=True)

underside = ramp.faces().group_by(Face.area)[-1].sort_by(Axis.Z)[0]
footprint = project_to_plane(underside, Plane.XY)
base = extrude(footprint, until=Until.NEXT, target=ramp)
ramp += base
# [base_algebra]

assert same(builder_result, ramp)
assert ramp.is_valid and len(ramp.solids()) == 1
assert base.is_valid and abs(base.bounding_box().min.Z) < 1e-6
# the base stops at the underside all the way along: it adds its whole volume
# to the ramp, and its top climbs with the ramp
assert abs(ramp.volume - (swept.volume + base.volume)) < 0.1
assert abs(base.bounding_box().max.Z - (lift + pitch * turns - wall)) < 0.1
