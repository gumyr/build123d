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

# Non-planar surface
with BuildPart() as non_planar:
    Cylinder(10, 20, rotation=(90, 0, 0), centered=(True, False, True))
    Box(10, 10, 10, centered=(True, True, False), mode=Mode.INTERSECT)
    Extrude(non_planar.part.faces().sort_by(Axis.Z)[0], amount=2, mode=Mode.REPLACE)

# Taper Extrude and Extrude to "next" while creating a Cherry MX key cap
# See: https://www.cherrymx.de/en/dev.html
with BuildPart() as key_cap:
    # Start with the plan of the key cap and extrude it
    with BuildSketch() as plan:
        Rectangle(18 * MM, 18 * MM)
    Extrude(amount=10 * MM, taper=15)
    # Create a dished top
    with Locations((0, -3 * MM, 47 * MM)):
        Sphere(40 * MM, mode=Mode.SUBTRACT, rotation=(90, 0, 0))
    # Fillet all the edges except the bottom
    Fillet(
        *key_cap.edges().filter_by_position(
            Axis.Z, 0, 30 * MM, inclusive=(False, True)
        ),
        radius=1 * MM,
    )
    # Hollow out the key by subtracting a scaled version
    Scale(by=(0.925, 0.925, 0.85), mode=Mode.SUBTRACT)

    # Add supporting ribs while leaving room for switch activation
    with Workplanes(Plane(origin=(0, 0, 4 * MM))):
        with BuildSketch():
            Rectangle(15 * MM, 0.5 * MM)
            Rectangle(0.5 * MM, 15 * MM)
            Circle(radius=5.51 * MM / 2)
    # Extrude the mount and ribs to the key cap underside
    Extrude(until=Until.NEXT)
    # Find the face on the bottom of the ribs to build onto
    rib_bottom = key_cap.faces().filter_by_position(Axis.Z, 4 * MM, 4 * MM)[0]
    # Add the switch socket
    with Workplanes(rib_bottom):
        with BuildSketch() as cruciform:
            Circle(radius=5.5 * MM / 2)
            Rectangle(4.1 * MM, 1.17 * MM, mode=Mode.SUBTRACT)
            Rectangle(1.17 * MM, 4.1 * MM, mode=Mode.SUBTRACT)
    Extrude(amount=3.5 * MM, mode=Mode.ADD)

if "show_object" in locals():
    show_object(
        simple.part.translate((-15, 0, 0)).wrapped, name="simple pending extrude"
    )
    show_object(both.part.translate((20, 10, 0)).wrapped, name="simple both")
    show_object(
        multiple.part.translate((0, -20, 0)).wrapped, name="multiple pending extrude"
    )
    show_object(non_planar.part.translate((20, -10, 0)).wrapped, name="non planar")
    show_object(key_cap.part.wrapped, name="key cap", options={"alpha": 0.7})
