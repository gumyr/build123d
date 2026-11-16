"""
Debugging a model documentation examples

name: debugging_examples.py
by:   Gumyr
date: November 15th 2026

desc:
    The code of the "Debugging a model" how-to guide, between pairs of
    ``# [name]`` markers that the page includes with ``literalinclude``.
    The bracket is the model in the page's screenshot. Nothing here needs a
    viewer: the lines of the page that call ``show`` are not in this script.

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

import io
import logging

from build123d import *

# ---------------------------------------------------------------------------
# the model being debugged
# ---------------------------------------------------------------------------

# [bracket]
length, width, height = 50, 25, 25
thickness = 3
bend_radius, fillet_radius = 5, 2
hole_diameter, slot_length = 5, 20

with BuildPart() as bracket:
    with BuildSketch() as sketch:
        with BuildLine() as profile:
            FilletPolyline(
                (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
            )
            offset(amount=thickness, side=Side.LEFT)
        make_face()
        mirror(about=Plane.YZ)
    extrude(amount=width / 2)
    mirror(about=Plane.XY)

    corners = bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[-1]
    fillet(corners, radius=fillet_radius)

    with Locations(bracket.faces().sort_by(Axis.X)[-1]):
        Hole(hole_diameter / 2)

    with BuildSketch(bracket.faces().sort_by(Axis.Y)[0]):
        SlotOverall(slot_length, hole_diameter)
    extrude(amount=-thickness, mode=Mode.SUBTRACT)
# [bracket]

# ---------------------------------------------------------------------------
# what a selection picked
# ---------------------------------------------------------------------------

# [selection]
len(corners)  # 4
[edge.geom_type for edge in corners]  # four LINEs
[edge.length for edge in corners]  # each 3 long: the thickness
[edge.center() for edge in corners]  # all at Y = 25: the tops of the two arms
# [selection]

assert len(corners) == 4
assert all(edge.geom_type == GeomType.LINE for edge in corners)
assert all(abs(edge.length - thickness) < 1e-6 for edge in corners)
assert all(abs(edge.center().Y - height) < 1e-6 for edge in corners)

# ---------------------------------------------------------------------------
# measure the result
# ---------------------------------------------------------------------------

# [measure]
part = bracket.part

part.bounding_box().size  # (50, 25, 25): as long, high and wide as intended
len(part.solids())  # 1: it is in one piece
part.volume  # about 6413
part.is_valid  # True
# [measure]

assert (part.bounding_box().size - Vector(length, height, width)).length < 1e-6
assert len(part.solids()) == 1 and part.is_valid
assert abs(part.volume - 6412.7) < 0.1

# ---------------------------------------------------------------------------
# print objects
# ---------------------------------------------------------------------------

# [printing]
plane = Plane.XY.offset(1)
print(f"{plane=}")
print(f"{plane.location=}")
print(part.bounding_box())
# [printing]

assert repr(plane) == "Plane((0, 0, 1), (1, 0, 0), (0, 0, 1))"
assert repr(plane.location) == "Location((0, 0, 1), (0, 0, 0))"

# [topology]
print(Box(1, 1, 1).show_topology(limit_class="Face"))
# [topology]

assert Box(1, 1, 1).show_topology(limit_class="Face").count("Face") == 6

# ---------------------------------------------------------------------------
# the log
# ---------------------------------------------------------------------------

captured = io.StringIO()
handler = logging.StreamHandler(captured)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logging.getLogger("build123d").addHandler(handler)
logging.getLogger("build123d").setLevel(logging.INFO)

# [logging]
with BuildPart() as plate:
    Box(80, 60, 10)
    with GridLocations(60, 40, 2, 2):
        Hole(3)
    chamfer(plate.edges().group_by(Axis.Z)[-1], 1)
# [logging]

logging.getLogger("build123d").removeHandler(handler)
logging.getLogger("build123d").setLevel(logging.NOTSET)
log = captured.getvalue()
# the lines the page shows
for expected in (
    "INFO: Entering BuildPart with mode=Mode.ADD",
    "INFO: Completed integrating 1 object(s) into part with Mode=Mode.ADD",
    "INFO: GridLocations is pushing 4 points",
    "INFO: Completed integrating 4 object(s) into part with Mode=Mode.SUBTRACT",
    "INFO: GridLocations is popping 4 points",
    "INFO: BuildPart context requested by chamfer",
    "INFO: Completed integrating 1 object(s) into part with Mode=Mode.REPLACE",
    "INFO: Exiting BuildPart",
):
    assert expected in log, expected
