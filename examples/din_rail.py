"""

name: din_rail.py
by:   Gumyr
date: July 14th 2022

desc:
    A 35 x 7.5 mm top hat DIN rail made the way it is manufactured: as sheet
    metal. A flat strip is stepped down along both long edges, the slots are
    cut in its top, and the sheet is thickened into the part and unfolded
    into the blank it is formed from.

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

# [Code]

from build123d import *
from ocp_viewer import show

# 35 x 7.5 mm DIN rail dimensions
overall_width, top_width, height = 35, 27, 7.5
thickness, bend_radius = 1, 0.8
rail_length = 250
slot_width, slot_length, slot_pitch = 6.2, 15, 25

# The flat beyond each lower bend, which makes the rail its overall width
lip = (overall_width - top_width) / 2 - bend_radius

with BuildPart() as rail:
    with BuildSheet(thickness=thickness, bend_radius=bend_radius) as sheet:
        # The top of the rail, drawn to the outside of its walls
        with BuildSketch():
            Rectangle(rail_length, top_width)
        # Each long edge steps down to a lip level with the mounting surface
        jog(
            sheet.rims().filter_by(Axis.X),
            offset=-(height - thickness),
            length=lip,
            position=BendPosition.MATERIAL_OUTSIDE,
        )
        # A sketch object drawn in a sheet cuts the face it lies on
        with GridLocations(slot_pitch, 0, rail_length // slot_pitch - 1, 1):
            SlotOverall(slot_length, slot_width, mode=Mode.SUBTRACT)
    thicken()

# The strip the rail is formed from, slots included
blank = unfold(sheet.sheet, sheet.sheet_parameters).flat

show(rail, Pos(0, 2 * overall_width, 0) * blank, names=["rail", "blank"])
# [End]
