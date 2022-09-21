"""

name: extrude.py
by:   Gumyr
date: September 20th 2022

desc:

    This example demonstrates multiple uses of Extrude cumulating in
    the design of a key cap.

license:

    Copyright 2022 Gumyr

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
from build123d import Plane

# Extrude pending face by amount
with BuildPart() as simple:
    with BuildSketch():
        Text("O", fontsize=10, halign=Halign.CENTER, valign=Valign.CENTER)
    Extrude(amount=5)

# Extrude pending face in both directions by amount
with BuildPart() as both:
    with BuildSketch():
        Text("O", fontsize=10, halign=Halign.CENTER, valign=Valign.CENTER)
    Extrude(amount=5, both=True)

# Extrude multiple pending faces on multiple faces
with BuildPart() as multiple:
    Box(10, 10, 10)
    with Workplanes(*multiple.faces()):
        with GridLocations(5, 5, 2, 2):
            with BuildSketch():
                Text("Ω", fontsize=3, halign=Halign.CENTER, valign=Valign.CENTER)
    Extrude(amount=1)

# Extrude provided face on multiple faces & subtract
with BuildSketch() as rect:
    Rectangle(7, 7)
with BuildPart() as single_multiple:
    Box(10, 10, 10)
    with Workplanes(*single_multiple.faces()):
        Extrude(rect.faces()[0], amount=-2, mode=Mode.SUBTRACT)

# Taper Extrude and Extrude to "next" while creating a 4U key cap
MM = 1
IN = 25.4 * MM
with BuildPart() as key_cap:
    # Start with the plan of the key cap and extrude it
    with BuildSketch() as plan:
        Rectangle(18 * MM, 18 * MM)
    Extrude(amount=6 * MM, taper=15)
    # Create a dished top
    with Locations((0, -3 * MM, 43 * MM)):
        Sphere(40 * MM, mode=Mode.SUBTRACT, rotation=(90, 0, 0))
    # Fillet all the edges except the bottom
    Fillet(
        *key_cap.edges().filter_by_position(
            Axis.Z, 0, 30 * MM, inclusive=(False, True)
        ),
        radius=1,
    )
    # Hollow out the key by subtracting a scaled version
    # ShellOffset(
    #     key_cap.faces().sort_by(SortBy.Z)[0], thickness=-0.5 * MM, mode=Mode.SUBTRACT
    # )
    Add(key_cap.part.scale(0.925), mode=Mode.SUBTRACT)
    # Recess the mount
    with Workplanes(Plane(origin=(0, 0, 0.005 * IN))):
        # Create the mount and ribs
        with BuildSketch():
            Rectangle(17.5 * MM, 0.5 * MM)
            Rectangle(0.5 * MM, 17.5 * MM)
            Circle(radius=0.217 * IN / 2)
            Rectangle(0.159 * IN, 0.047 * IN, mode=Mode.SUBTRACT)
            Rectangle(0.047 * IN, 0.159 * IN, mode=Mode.SUBTRACT)
    # Extrude the mount and ribs to the key cap underside
    Extrude(until=Until.NEXT)

if "show_object" in locals():
    show_object(simple.part.translate((-15, 0, 0)), name="simple pending extrude")
    show_object(both.part.translate((15, 0, 0)), name="simple both")
    show_object(multiple.part.translate((0, -20, 0)), name="multiple pending extrude")
    show_object(single_multiple.part.translate((0, 20, 0)), name="single multiple")
    show_object(key_cap.part, name="key cap", options={"alpha": 0.7})
