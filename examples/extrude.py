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
from ocp_vscode import *

# Extrude pending face by amount
with BuildPart() as simple:
    with BuildSketch():
        Text("O", font_size=10)
    extrude(amount=5)

# Extrude pending face in both directions by amount
with BuildPart() as both:
    with BuildSketch():
        Text("O", font_size=10)
    extrude(amount=5, both=True)

# Extrude multiple pending faces on multiple faces
with BuildPart() as multiple:
    Box(10, 10, 10)
    with BuildSketch(*multiple.faces()):
        with GridLocations(5, 5, 2, 2):
            Text("Ω", font_size=3)
    extrude(amount=1)

# Non-planar surface
with BuildPart() as non_planar:
    Cylinder(10, 20, rotation=(90, 0, 0), align=(Align.CENTER, Align.MIN, Align.CENTER))
    Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.INTERSECT)
    extrude(
        non_planar.part.faces().sort_by(Axis.Z)[0],
        amount=2,
        dir=(0, 0, 1),
        mode=Mode.REPLACE,
    )


rad, rev = 3, 25

# Extrude last
with BuildPart() as ex26:
    with BuildSketch() as ex26_sk:
        with Locations((0, rev)):
            Circle(rad)
    revolve(axis=Axis.X, revolution_arc=90)
    mirror(about=Plane.XZ)
    with BuildSketch() as ex26_sk2:
        Rectangle(rad, rev)
    ex26_target = ex26.part
    extrude(until=Until.LAST, clean=False, mode=Mode.REPLACE)

# Extrude next
with BuildPart() as ex27:
    with BuildSketch():
        with Locations((0, rev)):
            Circle(rad)
    revolve(axis=Axis.X, revolution_arc=90)
    with BuildSketch(Plane.XZ):
        with Locations((0, rev)):
            Circle(rad)
    revolve(axis=Axis.X, revolution_arc=150)
    with BuildSketch(Plane.XY.offset(-60)):
        Rectangle(rad, rev + 25)
    extrusion27 = extrude(until=Until.NEXT, mode=Mode.ADD)

# Extrude next both
# with BuildPart() as ex28:
#     Torus(25, 5, rotation=(0, 90, 0))
#     with BuildSketch():
#         Rectangle(rad, rev)
#     extrusion28 = extrude(until=Until.NEXT, both=True)

show_object(simple.part.translate((-15, 0, 0)).wrapped, name="simple pending extrude")
show_object(both.part.translate((20, 10, 0)).wrapped, name="simple both")
show_object(
    multiple.part.translate((0, -20, 0)).wrapped, name="multiple pending extrude"
)
show_object(non_planar.part.translate((20, -10, 0)).wrapped, name="non planar")
show_object(
    ex26_target.translate((-40, 0, 0)).wrapped,
    name="extrude until last target",
    options={"alpha": 0.8},
)
show_object(
    ex26.part.translate((-40, 0, 0)).wrapped,
    name="extrude until last",
)
show_object(
    ex27.part.rotate(Axis.Z, 90).translate((0, 50, 0)).wrapped,
    name="extrude until next target",
    options={"alpha": 0.8},
)
show_object(
    extrusion27.rotate(Axis.Z, 90).translate((0, 50, 0)).wrapped,
    name="extrude until next",
)
# show_object(
#     ex28.part.rotate(Axis.Z, -90).translate((0, -50, 0)).wrapped,
#     name="extrude until next both target",
#     options={"alpha": 0.8},
# )
# show_object(
#     extrusion28.rotate(Axis.Z, -90).translate((0, -50, 0)).wrapped,
#     name="extrude until next both",
# )
