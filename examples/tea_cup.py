"""

name: tea_cup.py
by:   Gumyr
date: March 27th 2023

desc: This example demonstrates the creation of non-planar objects.

license:

    Copyright 2023 Gumyr

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
from build123d import *

wall_thickness = 3 * MM
fillet_radius = wall_thickness * 0.49

with BuildPart() as tea_cup:
    # Create the bowl of the cup as a revolved cross section
    with BuildSketch(Plane.XZ) as bowl_section:
        with BuildLine():
            # Start & end points with control tangents
            s = Spline(
                (30 * MM, 10 * MM),
                (69 * MM, 105 * MM),
                tangents=((1, 0.5), (0.7, 1)),
                tangent_scalars=(1.75, 1),
            )
            # Lines to finish creating ½ the bowl shape
            Polyline(s @ 0, s @ 0 + (10 * MM, -10 * MM), (0, 0), (0, (s @ 1).Y), s @ 1)
        make_face()  # Create a filled 2D shape
    revolve(axis=Axis.Z)
    # Hollow out the bowl with openings on the top and bottom
    offset(amount=-wall_thickness, openings=tea_cup.faces().filter_by(GeomType.PLANE))
    # Add a bottom to the bowl
    with Locations((0, 0, (s @ 0).Y)):
        Cylinder(radius=(s @ 0).X, height=wall_thickness)
    # Smooth out all the edges
    fillet(tea_cup.edges(), radius=fillet_radius)

    # Determine where the handle contacts the bowl
    handle_intersections = [
        tea_cup.part.find_intersection(
            Axis(origin=(0, 0, vertical_offset), direction=(1, 0, 0))
        )[-1][0]
        for vertical_offset in [35 * MM, 80 * MM]
    ]
    # Create a path for handle creation
    with BuildLine(Plane.XZ) as handle_path:
        path_spline = Spline(
            handle_intersections[0] - (wall_thickness / 2, 0),
            handle_intersections[0] + (35 * MM, 30 * MM),
            handle_intersections[0] + (40 * MM, 60 * MM),
            handle_intersections[1] - (wall_thickness / 2, 0),
            tangents=((1, 1.25), (-0.2, -1)),
        )
    # Align the cross section to the beginning of the path
    with BuildSketch(
        Plane(origin=path_spline @ 0, z_dir=path_spline % 0)
    ) as handle_cross_section:
        RectangleRounded(wall_thickness, 8 * MM, fillet_radius)
    sweep()  # Sweep handle cross section along path

assert abs(tea_cup.part.volume - 130326) < 1

if "show_object" in locals():
    show_object(tea_cup.part, name="tea cup")
