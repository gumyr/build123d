"""
A bicycle tire with tread.

name: bicycle_tire.py
by:   Gumyr
date: May 20, 2025

desc:

    This example demonstrates how to model a realistic bicycle tire with a
    patterned tread using build123d. The key concept showcased here is the
    use of wrap_faces to project 2D planar geometry onto a curved 3D
    surface.

    The tire cross-section is defined using a series of Bezier curves and
    revolved to form the main tire body. A 2D tread pattern is created as a
    sketch on a plane and then wrapped onto the non-planar revolved surface
    using wrap_faces, following a path on the surface. The wrapped faces are
    then thickened into 3D solid nubs and copied around the tire using
    rotational placement.

    This technique is particularly useful for applying surface detail—such
    as grooves, logos, or textures—to curved or freeform geometries in a CAD
    model.

    Highlights:
    - Complex profile creation using multiple Bezier segments.
    - Surface wrapping of planar sketches using wrap_faces.
    - Solidification of surface features via thicken.
    - Circular duplication of solids using rotational transforms.

license:

    Copyright 2025 Gumyr

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

# [Code]
from build123d import *
from ocp_vscode import show

wheel_diameter = 740 * MM
block_height = 3 * MM  # how far the tread blocks stand out
tread_step = 2  # degrees from one row of tread blocks to the next

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

show(smooth_tire, tread)
# [End]
