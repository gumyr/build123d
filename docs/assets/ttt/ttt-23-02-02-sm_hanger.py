"""
Creation of a complex sheet metal part

name: ttt-23-02-02_sm_hanger.py
by:   Gumyr
date: October 15, 2026

desc:
    This example implements the sheet metal part described in Too Tall Toby's
    sm_hanger CAD challenge.

    The part is built as one BuildSheet of 4 mm steel and thickened at the end.
    Half the base is sketched with its tab cutout, and the tab is flanged up from
    the cutout's edge and drilled. The leg is flanged down at 60° to the drawing's
    height, mitered to flare, and the foot flanged back under it, its length measured
    off the model. The slots are cut through as normal cuts, the half is mirrored,
    and the two wings are flanged down the long sides. Every dimension is the drawing's
    own.

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

from build123d import *
from ocp_vscode import show
from bd_materials.materials.metals import mild_steel

with BuildPart() as sm_hanger_builder:
    with BuildSheet(thickness=4 * MM, bend_radius=4 * MM) as sheet:
        # Create the top with a sketch that has the hole for the tab
        with BuildSketch() as base:
            Rectangle(170 / 2, 80, align=(Align.MIN, Align.CENTER))
            with Locations((40 / 2, 0)):
                Rectangle(30, 30, align=(Align.MIN, Align.CENTER), mode=Mode.SUBTRACT)
            fillet(base.vertices(Select.LAST).group_by(Axis.X)[-1], 7)

        # Create vertical tab
        hole_rim = sheet.face().inner_wires()[0].edges().sort_by(Axis.X)[0]
        flange(hole_rim, length=23, length_from=LengthFrom.INNER_SHARP, gaps=2)
        fillet(sheet.vertices().group_by(Axis.Z)[-1], 5)
        with Locations(Plane((0, 0, 80 - 65), z_dir=(1, 0, 0))):
            h = Hole(10 / 2)

        # From the end of the sheet, create a flange at 60° downward
        far_end = sheet.rims().sort_by(Axis.X)[-1]
        flange(
            far_end,
            angle=-60,
            length=65,
            length_mode=LengthMode.VERTICAL,
            length_from=LengthFrom.OUTER_SHARP,
            position=BendPosition.MATERIAL_OUTSIDE,
        )

        # Miter the new flange to make it flare out
        miter(sheet.rims().sort_by(Axis.X)[-1].vertices(), -26 / 2)

        # Create the foot as another flange
        far_end = sheet.rims().sort_by(Axis.X)[-1]
        flange(
            far_end,
            length=far_end.position_at(0).X - (170 / 2),
            angle=-120,
            position=BendPosition.MATERIAL_OUTSIDE,
            length_from=LengthFrom.OUTER_SHARP,
        )
        fillet(sheet.vertices().group_by(Axis.Z)[0].group_by(Axis.X)[0], 7)

        # Create notches
        with BuildPart(mode=Mode.SUBTRACT) as cutouts:
            with BuildSketch():
                SlotCenterPoint((170, 0), (154 / 2, 0), 20)
            extrude(amount=-65 / 2)  # clear the base but not the foot
            with BuildSketch():
                SlotCenterPoint((170, 0), (206 / 2, 0), 20)
            extrude(amount=-65)

        # Mirror to create the other half
        mirror(about=Plane.YZ)

        # Create the side flanges
        side_rims = [
            sheet.flats()
            .filter_by(Axis.Z)
            .sort_by(Axis.Z)[-1]
            .edges()
            .sort_by(Axis.Y)[i]
            for i in (0, -1)
        ]
        flange(
            side_rims,
            length=15,
            angle=-75,
            length_from=LengthFrom.TANGENT,
            gaps=(side_rims[0].length - 110) / 2,
        )
        fillet(sheet.flats(Select.LAST).vertices().group_by(Axis.Z)[0], 7)

    thicken()  # Parameters taken from BuildSheet

    sm_hanger_flat = sheet.sheet.unfold().flat

sm_hanger = sm_hanger_builder.part
sm_hanger.material = mild_steel()  # 7800 kg/m³

sm_hanger_flat.position -= sm_hanger_flat.center() + (0, 0, 65)
got_mass = sm_hanger.mass()
want_mass = 1028
tolerance = 10
diff_mass = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.1f} g")
assert diff_mass < tolerance, f"{got_mass=}, {want_mass=}, {diff_mass=}, {tolerance=}"

show(sm_hanger, sm_hanger_flat)
