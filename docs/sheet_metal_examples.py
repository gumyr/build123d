"""

name: sheet_metal_examples.py
by:   Gumyr & Gabriel Jesus
date: July 21st 2026

desc:

    This is the build123d sheet metal tutorial python script. It is pulled
    into sphinx docs by tutorial_sheet_metal.rst, and is run as part of the
    docs example test suite to keep the tutorial code truthful.

license:

    Copyright 2026 Gumyr & Gabriel Jesus

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
from ocp_vscode import show

#
# ——————— Builder Mode ———————
#
with BuildPart() as box_part_builder:
    with BuildSheet(thickness=1, bend_radius=2) as box_builder:
        with BuildSketch() as bottom:
            Rectangle(100, 60)

        # Add flanges to the bottom
        flange(box_builder.edges(), length=20, gaps=3.1)

        # Trim the flanges
        chamfer(
            box_builder.faces().sort_by(Axis.Y)[-1].vertices().group_by(Axis.Z)[-1],
            10,
        )
        miter(
            box_builder.faces().sort_by(Axis.Y)[0].vertices().group_by(Axis.Z)[-1],
            20,
        )
        miter(
            box_builder.faces().sort_by(Axis.X)[0].vertices().group_by(Axis.Z)[-1],
            -20,
        )

        # Apply hems to the rims of the flanges
        rims = box_builder.edges().group_by(Axis.Z)[-1]
        hem(rims[0], hem_type=HemType.OPEN, width=6, opening=2)
        hem(rims[1], hem_type=HemType.TEARDROP, width=6, opening=1)
        hem(rims[2], hem_type=HemType.ROLLED, radius=1.5, roll_angle=270)
        hem(rims[3], hem_type=HemType.FLAT, width=6)

    box = thicken()

assert box_builder.sheet.is_valid
assert box_part_builder.part.is_valid

#
# ——————— Algebra Mode ———————
#
parms = SheetMetalParameters(
    thickness=1,
    bend_radius=2,
    k_factor=0.4,
    sheet_surface=SheetSurface.INSIDE,
)

# Create the bottom
box_shell = Rectangle(100, 60)

# Add flanges to the bottom
box_shell = flange(
    box_shell.edges(),
    length=20,
    radius=2,
    gaps=3.1,
    sheet_parameters=parms,
)

# Trim the flanges
box_shell = chamfer(
    box_shell.faces().sort_by(Axis.Y)[-1].vertices().group_by(Axis.Z)[-1], 10
)
box_shell = miter(
    box_shell.faces().sort_by(Axis.Y)[0].vertices().group_by(Axis.Z)[-1], 20
)
box_shell = miter(
    box_shell.faces().sort_by(Axis.X)[0].vertices().group_by(Axis.Z)[-1], -20
)


# Apply hems to the rims of the flanges
box_shell = hem(
    box_shell.edges().filter_by(Axis.X).group_by(Axis.Z)[-1].sort_by(Axis.Y)[-1],
    hem_type=HemType.OPEN,
    width=6,
    opening=2,
    sheet_parameters=parms,
)
box_shell = hem(
    box_shell.edges().filter_by(Axis.X).group_by(Axis.Z)[-1].sort_by(Axis.Y)[0],
    hem_type=HemType.TEARDROP,
    width=6,
    opening=1,
    radius=2,
    sheet_parameters=parms,
)
box_shell = hem(
    box_shell.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1].sort_by(Axis.X)[0],
    hem_type=HemType.ROLLED,
    radius=1.5,
    roll_angle=270,
    sheet_parameters=parms,
)
box_shell = hem(
    box_shell.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1].sort_by(Axis.X)[-1],
    hem_type=HemType.FLAT,
    width=6,
    sheet_parameters=parms,
)
box_algebra = thicken(box_shell, sheet_parameters=parms)
show(
    box_builder.sheet,
    box_builder.sheet.unfold(),
    box_part_builder.part,
    box_shell,
    box_algebra,
    names=[
        "box_builder.sheet",
        "unfolded",
        "box_part_builder.part",
        "box_shell",
        "box_algebra",
    ],
)
