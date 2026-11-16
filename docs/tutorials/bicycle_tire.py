"""
A bicycle tire tutorial

name: bicycle_tire.py
by:   Gumyr
date: November 14th 2026

desc:
    Every code example in the "A bicycle tire" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. Each step is written twice, in builder and in algebra
    mode, and shows the whole model as it stands at that point; the two are
    checked against each other. The tire is the one of
    ``examples/bicycle_tire.py``. The rendered pictures on the page are made
    from this script by ``bicycle_tire_shots.py``.

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
from bd_materials.materials.plastics import rubber
from build123d import *

wheel_diameter = 740 * MM

# the tread on the road surface
block_height = 3 * MM  # how far the tread blocks stand out
tread_step = 2  # degrees from one row of tread blocks to the next

# the lettering on the sidewall
legend = "build123d 700x40C"
letter_height = 20 * MM
stroke_width = 2 * MM  # how wide the strokes of the letters are drawn
relief = 0.6 * MM  # how far the letters stand out from the sidewall
label_radius = 348 * MM  # the circle round the wheel that the lettering follows
label_offset = 25 * MM  # how far out from the middle of the wheel it is drawn
# [setup]


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?
    The volume of this tire is only reported to about one part in a hundred,
    so it is compared loosely and the bounding box exactly."""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-4 * max(first.volume, 1)
        and abs(first.area - second.area) < 1e-4 * first.area
        and (box_1.min - box_2.min).length < 1e-5
        and (box_1.max - box_2.max).length < 1e-5
    )


# ---------------------------------------------------------------------------
# Step 2: the tire
# ---------------------------------------------------------------------------

# [tire_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)
# [tire_builder]

builder_result = smooth_tire.part

# [tire_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)
# [tire_algebra]

assert same(builder_result, smooth_tire)
plain = smooth_tire


# ---------------------------------------------------------------------------
# Step 3: a tread pattern, flat
# ---------------------------------------------------------------------------

# [pattern_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)

# One unit of the tread
with BuildPart() as tread_unit:
    # The flat pattern: a slanted bar with two grooves, and its mirror image
    with BuildSketch(mode=Mode.PRIVATE) as tread_pattern:
        with Locations((1, 1)):
            Trapezoid(15, 12, 60, 120, align=Align.MIN)
        with Locations((1, 8)):
            with GridLocations(0, 5, 1, 2):
                Rectangle(50, 2, mode=Mode.SUBTRACT)
        mirror(about=Plane.XZ)
# [pattern_builder]

builder_result = tread_pattern.sketch

# [pattern_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)

# One unit of the tread
# The flat pattern: a slanted bar with two grooves, and its mirror image
tread_pattern = Pos(1, 1) * Trapezoid(15, 12, 60, 120, align=Align.MIN)
tread_pattern -= [Pos(1, y) * Rectangle(50, 2) for y in (5.5, 10.5)]
tread_pattern += mirror(tread_pattern, Plane.XZ)
# [pattern_algebra]

assert same(builder_result, tread_pattern)
assert len(tread_pattern.faces()) == 6


# ---------------------------------------------------------------------------
# Step 4: onto the road surface
# ---------------------------------------------------------------------------

# [wrap_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)

    # Where the tread goes: the road surface, and the line round its middle
    road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
    tread_path = section(section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
with BuildPart() as tread_unit:
    # The flat pattern: a slanted bar with two grooves, and its mirror image
    with BuildSketch(mode=Mode.PRIVATE) as tread_pattern:
        with Locations((1, 1)):
            Trapezoid(15, 12, 60, 120, align=Align.MIN)
        with Locations((1, 8)):
            with GridLocations(0, 5, 1, 2):
                Rectangle(50, 2, mode=Mode.SUBTRACT)
        mirror(about=Plane.XZ)

    # Wrap the flat pattern onto the road surface
    insert(road_surface.wrap_faces(tread_pattern.faces(), tread_path))
# [wrap_builder]

builder_result = Compound(tread_unit.pending_faces)

# [wrap_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)

# Where the tread goes: the road surface, and the line round its middle
road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
tread_path = section(smooth_tire, section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
# The flat pattern: a slanted bar with two grooves, and its mirror image
tread_pattern = Pos(1, 1) * Trapezoid(15, 12, 60, 120, align=Align.MIN)
tread_pattern -= [Pos(1, y) * Rectangle(50, 2) for y in (5.5, 10.5)]
tread_pattern += mirror(tread_pattern, Plane.XZ)

# Wrap the flat pattern onto the road surface
wrapped_pattern = road_surface.wrap_faces(tread_pattern.faces(), tread_path)
# [wrap_algebra]

assert same(builder_result, Compound(wrapped_pattern))
assert len(wrapped_pattern) == 6
# wrapping keeps the size of the pattern
assert abs(sum(f.area for f in wrapped_pattern) / tread_pattern.area - 1) < 0.005


# ---------------------------------------------------------------------------
# Step 5: blocks, all the way round
# ---------------------------------------------------------------------------

# [tread_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)

    # Where the tread goes: the road surface, and the line round its middle
    road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
    tread_path = section(section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
with BuildPart() as tread_unit:
    # The flat pattern: a slanted bar with two grooves, and its mirror image
    with BuildSketch(mode=Mode.PRIVATE) as tread_pattern:
        with Locations((1, 1)):
            Trapezoid(15, 12, 60, 120, align=Align.MIN)
        with Locations((1, 8)):
            with GridLocations(0, 5, 1, 2):
                Rectangle(50, 2, mode=Mode.SUBTRACT)
        mirror(about=Plane.XZ)

    # Wrap the flat pattern onto the road surface
    insert(road_surface.wrap_faces(tread_pattern.faces(), tread_path))

    # Thicken the wrapped faces into blocks
    thicken(amount=block_height)

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit.part for angle in range(0, 360, tread_step)]
# [tread_builder]

builder_result = tread_unit.part
builder_tread = tread

# [tread_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)

# Where the tread goes: the road surface, and the line round its middle
road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
tread_path = section(smooth_tire, section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
# The flat pattern: a slanted bar with two grooves, and its mirror image
tread_pattern = Pos(1, 1) * Trapezoid(15, 12, 60, 120, align=Align.MIN)
tread_pattern -= [Pos(1, y) * Rectangle(50, 2) for y in (5.5, 10.5)]
tread_pattern += mirror(tread_pattern, Plane.XZ)

# Wrap the flat pattern onto the road surface
wrapped_pattern = road_surface.wrap_faces(tread_pattern.faces(), tread_path)

# Thicken the wrapped faces into blocks
tread_unit = Part() + [thicken(face, amount=block_height) for face in wrapped_pattern]

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit for angle in range(0, 360, tread_step)]
# [tread_algebra]

assert same(builder_result, tread_unit)
assert len(builder_result.solids()) == 6
assert len(tread) == len(builder_tread) == 360 // tread_step
assert all(len(unit.solids()) == 6 for unit in tread)
# every unit is a copy of the one compared above, so the ends are enough
for unit, builder_unit in (
    (tread[0], builder_tread[0]),
    (tread[-1], builder_tread[-1]),
):
    assert same(builder_unit, unit)


# ---------------------------------------------------------------------------
# Step 6: the lettering, flat
# ---------------------------------------------------------------------------

# [label_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)

    # Where the tread goes: the road surface, and the line round its middle
    road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
    tread_path = section(section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
with BuildPart() as tread_unit:
    # The flat pattern: a slanted bar with two grooves, and its mirror image
    with BuildSketch(mode=Mode.PRIVATE) as tread_pattern:
        with Locations((1, 1)):
            Trapezoid(15, 12, 60, 120, align=Align.MIN)
        with Locations((1, 8)):
            with GridLocations(0, 5, 1, 2):
                Rectangle(50, 2, mode=Mode.SUBTRACT)
        mirror(about=Plane.XZ)

    # Wrap the flat pattern onto the road surface
    insert(road_surface.wrap_faces(tread_pattern.faces(), tread_path))

    # Thicken the wrapped faces into blocks
    thicken(amount=block_height)

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit.part for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
with BuildPart() as embossed_label:
    # The lettering is drawn flat, beside the wheel, along an arc
    with BuildLine() as path:
        CenterArc((0, 0), label_radius, 0, 90)
    with BuildSketch(Plane.ZY.offset(label_offset)) as label:
        Text(
            legend,
            letter_height,
            font="singleline",
            single_line_width=stroke_width,
            text_align=[TextAlign.CENTER, TextAlign.CENTER],
            path=path.edge().reversed(),
            position_on_path=0.5,
        )
# [label_builder]

builder_result = label.sketch

# [label_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)

# Where the tread goes: the road surface, and the line round its middle
road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
tread_path = section(smooth_tire, section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
# The flat pattern: a slanted bar with two grooves, and its mirror image
tread_pattern = Pos(1, 1) * Trapezoid(15, 12, 60, 120, align=Align.MIN)
tread_pattern -= [Pos(1, y) * Rectangle(50, 2) for y in (5.5, 10.5)]
tread_pattern += mirror(tread_pattern, Plane.XZ)

# Wrap the flat pattern onto the road surface
wrapped_pattern = road_surface.wrap_faces(tread_pattern.faces(), tread_path)

# Thicken the wrapped faces into blocks
tread_unit = Part() + [thicken(face, amount=block_height) for face in wrapped_pattern]

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
# The lettering is drawn flat, beside the wheel, along an arc
path = CenterArc((0, 0), label_radius, 0, 90)
label = Plane.ZY.offset(label_offset) * Text(
    legend,
    letter_height,
    font="singleline",
    single_line_width=stroke_width,
    text_align=[TextAlign.CENTER, TextAlign.CENTER],
    path=path.reversed(),
    position_on_path=0.5,
)
# [label_algebra]

assert same(builder_result, label)
assert len(label.faces()) == 17


# ---------------------------------------------------------------------------
# Step 7: onto the sidewall
# ---------------------------------------------------------------------------

# [project_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)

    # Where the tread goes: the road surface, and the line round its middle
    road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
    tread_path = section(section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
with BuildPart() as tread_unit:
    # The flat pattern: a slanted bar with two grooves, and its mirror image
    with BuildSketch(mode=Mode.PRIVATE) as tread_pattern:
        with Locations((1, 1)):
            Trapezoid(15, 12, 60, 120, align=Align.MIN)
        with Locations((1, 8)):
            with GridLocations(0, 5, 1, 2):
                Rectangle(50, 2, mode=Mode.SUBTRACT)
        mirror(about=Plane.XZ)

    # Wrap the flat pattern onto the road surface
    insert(road_surface.wrap_faces(tread_pattern.faces(), tread_path))

    # Thicken the wrapped faces into blocks
    thicken(amount=block_height)

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit.part for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
with BuildPart() as embossed_label:
    # The lettering is drawn flat, beside the wheel, along an arc
    with BuildLine() as path:
        CenterArc((0, 0), label_radius, 0, 90)
    with BuildSketch(Plane.ZY.offset(label_offset)) as label:
        Text(
            legend,
            letter_height,
            font="singleline",
            single_line_width=stroke_width,
            text_align=[TextAlign.CENTER, TextAlign.CENTER],
            path=path.edge().reversed(),
            position_on_path=0.5,
        )

    # Project it sideways onto the tire
    project_to_shape(target=smooth_tire.part, direction=(1, 0, 0), hit=Hit.NEAREST)
# [project_builder]

builder_result = Compound(embossed_label.pending_faces)

# [project_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)

# Where the tread goes: the road surface, and the line round its middle
road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
tread_path = section(smooth_tire, section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
# The flat pattern: a slanted bar with two grooves, and its mirror image
tread_pattern = Pos(1, 1) * Trapezoid(15, 12, 60, 120, align=Align.MIN)
tread_pattern -= [Pos(1, y) * Rectangle(50, 2) for y in (5.5, 10.5)]
tread_pattern += mirror(tread_pattern, Plane.XZ)

# Wrap the flat pattern onto the road surface
wrapped_pattern = road_surface.wrap_faces(tread_pattern.faces(), tread_path)

# Thicken the wrapped faces into blocks
tread_unit = Part() + [thicken(face, amount=block_height) for face in wrapped_pattern]

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
# The lettering is drawn flat, beside the wheel, along an arc
path = CenterArc((0, 0), label_radius, 0, 90)
label = Plane.ZY.offset(label_offset) * Text(
    legend,
    letter_height,
    font="singleline",
    single_line_width=stroke_width,
    text_align=[TextAlign.CENTER, TextAlign.CENTER],
    path=path.reversed(),
    position_on_path=0.5,
)

# Project it sideways onto the tire
letters = project_to_shape(label, smooth_tire, direction=(1, 0, 0), hit=Hit.NEAREST)
# [project_algebra]

assert same(builder_result, letters)
# every letter lands on two faces of the sidewall, and on the near side
assert len(letters.faces()) == 34
assert letters.bounding_box().max.X < 0


# ---------------------------------------------------------------------------
# Step 8: emboss
# ---------------------------------------------------------------------------

# [emboss_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)

    # Where the tread goes: the road surface, and the line round its middle
    road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
    tread_path = section(section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
with BuildPart() as tread_unit:
    # The flat pattern: a slanted bar with two grooves, and its mirror image
    with BuildSketch(mode=Mode.PRIVATE) as tread_pattern:
        with Locations((1, 1)):
            Trapezoid(15, 12, 60, 120, align=Align.MIN)
        with Locations((1, 8)):
            with GridLocations(0, 5, 1, 2):
                Rectangle(50, 2, mode=Mode.SUBTRACT)
        mirror(about=Plane.XZ)

    # Wrap the flat pattern onto the road surface
    insert(road_surface.wrap_faces(tread_pattern.faces(), tread_path))

    # Thicken the wrapped faces into blocks
    thicken(amount=block_height)

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit.part for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
with BuildPart() as embossed_label:
    # The lettering is drawn flat, beside the wheel, along an arc
    with BuildLine() as path:
        CenterArc((0, 0), label_radius, 0, 90)
    with BuildSketch(Plane.ZY.offset(label_offset)) as label:
        Text(
            legend,
            letter_height,
            font="singleline",
            single_line_width=stroke_width,
            text_align=[TextAlign.CENTER, TextAlign.CENTER],
            path=path.edge().reversed(),
            position_on_path=0.5,
        )

    # Project it sideways onto the tire
    project_to_shape(target=smooth_tire.part, direction=(1, 0, 0), hit=Hit.NEAREST)

    # Thicken the projected letters so they stand out from the sidewall
    thicken(amount=relief)
# [emboss_builder]

builder_result = embossed_label.part

# [emboss_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)

# Where the tread goes: the road surface, and the line round its middle
road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
tread_path = section(smooth_tire, section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
# The flat pattern: a slanted bar with two grooves, and its mirror image
tread_pattern = Pos(1, 1) * Trapezoid(15, 12, 60, 120, align=Align.MIN)
tread_pattern -= [Pos(1, y) * Rectangle(50, 2) for y in (5.5, 10.5)]
tread_pattern += mirror(tread_pattern, Plane.XZ)

# Wrap the flat pattern onto the road surface
wrapped_pattern = road_surface.wrap_faces(tread_pattern.faces(), tread_path)

# Thicken the wrapped faces into blocks
tread_unit = Part() + [thicken(face, amount=block_height) for face in wrapped_pattern]

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
# The lettering is drawn flat, beside the wheel, along an arc
path = CenterArc((0, 0), label_radius, 0, 90)
label = Plane.ZY.offset(label_offset) * Text(
    legend,
    letter_height,
    font="singleline",
    single_line_width=stroke_width,
    text_align=[TextAlign.CENTER, TextAlign.CENTER],
    path=path.reversed(),
    position_on_path=0.5,
)

# Project it sideways onto the tire
letters = project_to_shape(label, smooth_tire, direction=(1, 0, 0), hit=Hit.NEAREST)

# Thicken the projected letters so they stand out from the sidewall
embossed_label = Part() + [thicken(face, amount=relief) for face in letters.faces()]
# [emboss_algebra]

assert same(builder_result, embossed_label)
# the letters stand outward from the sidewall
assert embossed_label.bounding_box().min.X < letters.bounding_box().min.X - 0.9 * relief


# ---------------------------------------------------------------------------
# Step 9: the whole tire
# ---------------------------------------------------------------------------

# [whole_builder]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
with BuildPart() as smooth_tire:
    with BuildSketch(Pos(Y=-wheel_diameter / 2)) as tire_profile:
        with BuildLine() as build_profile:
            l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
            l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
            l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
            l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
            l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
            l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
            l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
            l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
            l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
            l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
            l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
            l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
            l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
            l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
            l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
            l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
            l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
            l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
            l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
            l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
            mirror(about=Plane.YZ)
        make_face()
    revolve(axis=Axis.X)

    # Where the tread goes: the road surface, and the line round its middle
    road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
    tread_path = section(section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
with BuildPart() as tread_unit:
    # The flat pattern: a slanted bar with two grooves, and its mirror image
    with BuildSketch(mode=Mode.PRIVATE) as tread_pattern:
        with Locations((1, 1)):
            Trapezoid(15, 12, 60, 120, align=Align.MIN)
        with Locations((1, 8)):
            with GridLocations(0, 5, 1, 2):
                Rectangle(50, 2, mode=Mode.SUBTRACT)
        mirror(about=Plane.XZ)

    # Wrap the flat pattern onto the road surface
    insert(road_surface.wrap_faces(tread_pattern.faces(), tread_path))

    # Thicken the wrapped faces into blocks
    thicken(amount=block_height)

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit.part for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
with BuildPart() as embossed_label:
    # The lettering is drawn flat, beside the wheel, along an arc
    with BuildLine() as path:
        CenterArc((0, 0), label_radius, 0, 90)
    with BuildSketch(Plane.ZY.offset(label_offset)) as label:
        Text(
            legend,
            letter_height,
            font="singleline",
            single_line_width=stroke_width,
            text_align=[TextAlign.CENTER, TextAlign.CENTER],
            path=path.edge().reversed(),
            position_on_path=0.5,
        )

    # Project it sideways onto the tire
    project_to_shape(target=smooth_tire.part, direction=(1, 0, 0), hit=Hit.NEAREST)

    # Thicken the projected letters so they stand out from the sidewall
    thicken(amount=relief)

# The whole tire: the parts are grouped, not fused
tire = Compound(children=tread + [smooth_tire.part, embossed_label.part])
tire.material = rubber()

# What the tread and lettering add
smooth_spin = max(moment for axis, moment in smooth_tire.part.principal_properties)
tire_spin = max(moment for axis, moment in tire.principal_properties)

print(f"mass {tire.mass():.0f} g")
print(f"volume +{tire.volume / smooth_tire.part.volume - 1:.1%}")
print(f"moment +{tire_spin / smooth_spin - 1:.1%}")
# [whole_builder]

# measuring the whole tire is slow, so it is done once for each mode
builder_gain = tire_spin / smooth_spin
builder_volume = tire.volume

# [whole_algebra]
# The tire: half of its cross-section is traced with Bezier curves,
# mirrored into a closed outline and revolved round the axle (the X axis)
l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
half_profile = Curve() + [l00, l01, l02, l03, l04, l05, l06, l07, l08, l09]
half_profile += [l10, l11, l12, l13, l14, l15, l16, l17, l18, l19]
tire_profile = make_face(half_profile + mirror(half_profile, Plane.YZ))
smooth_tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile, Axis.X)

# Where the tread goes: the road surface, and the line round its middle
road_surface = smooth_tire.faces().sort_by(Face.area)[-1]
tread_path = section(smooth_tire, section_by=Plane.YZ).edges().sort_by(Edge.length)[-1]

# One unit of the tread
# The flat pattern: a slanted bar with two grooves, and its mirror image
tread_pattern = Pos(1, 1) * Trapezoid(15, 12, 60, 120, align=Align.MIN)
tread_pattern -= [Pos(1, y) * Rectangle(50, 2) for y in (5.5, 10.5)]
tread_pattern += mirror(tread_pattern, Plane.XZ)

# Wrap the flat pattern onto the road surface
wrapped_pattern = road_surface.wrap_faces(tread_pattern.faces(), tread_path)

# Thicken the wrapped faces into blocks
tread_unit = Part() + [thicken(face, amount=block_height) for face in wrapped_pattern]

# Copy the unit all the way round the tire
tread = [Rot(X=angle) * tread_unit for angle in range(0, 360, tread_step)]

# The lettering on the sidewall
# The lettering is drawn flat, beside the wheel, along an arc
path = CenterArc((0, 0), label_radius, 0, 90)
label = Plane.ZY.offset(label_offset) * Text(
    legend,
    letter_height,
    font="singleline",
    single_line_width=stroke_width,
    text_align=[TextAlign.CENTER, TextAlign.CENTER],
    path=path.reversed(),
    position_on_path=0.5,
)

# Project it sideways onto the tire
letters = project_to_shape(label, smooth_tire, direction=(1, 0, 0), hit=Hit.NEAREST)

# Thicken the projected letters so they stand out from the sidewall
embossed_label = Part() + [thicken(face, amount=relief) for face in letters.faces()]

# The whole tire: the parts are grouped, not fused
tire = Compound(children=tread + [smooth_tire, embossed_label])
tire.material = rubber()

# What the tread and lettering add
smooth_spin = max(moment for axis, moment in smooth_tire.principal_properties)
tire_spin = max(moment for axis, moment in tire.principal_properties)

print(f"mass {tire.mass():.0f} g")
print(f"volume +{tire.volume / smooth_tire.volume - 1:.1%}")
print(f"moment +{tire_spin / smooth_spin - 1:.1%}")
# [whole_algebra]

algebra_volume = tire.volume
assert abs(builder_gain - tire_spin / smooth_spin) < 1e-4
# the volume counts the tread and the lettering as well as the tire
assert abs(algebra_volume - builder_volume) < 1e-3 * builder_volume
assert f"{tire.mass():.0f}" == "1177"
assert f"{algebra_volume / smooth_tire.volume - 1:.1%}" == "8.2%"
assert f"{tire_spin / smooth_spin - 1:.1%}" == "8.8%"
