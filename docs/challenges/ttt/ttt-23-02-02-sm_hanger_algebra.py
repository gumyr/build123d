"""
Creation of a complex sheet metal part

name: ttt-23-02-02_sm_hanger.py
by:   Gumyr
date: October 15, 2026

desc:
    This example implements the sheet metal part described in Too Tall Toby's
    sm_hanger CAD challenge.

    The part is built as one sheet of 4 mm steel and thickened at the end.
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

parameters = SheetMetalParameters(thickness=4 * MM, bend_radius=4 * MM)

# Create the top with a sketch that has the hole for the tab
base = Rectangle(170 / 2, 80, align=(Align.MIN, Align.CENTER))
tab_hole = Pos(40 / 2, 0) * Rectangle(30, 30, align=(Align.MIN, Align.CENTER))
tab_hole = fillet(tab_hole.vertices().group_by(Axis.X)[-1], 7)
sheet = Shell((base - tab_hole).face())

# Create vertical tab
hole_rim = sheet.face().inner_wires()[0].edges().sort_by(Axis.X)[0]
sheet = flange(
    hole_rim,
    length=23,
    length_from=LengthFrom.INNER_SHARP,
    gaps=2,
    sheet_parameters=parameters,
)
sheet = fillet(sheet.vertices().group_by(Axis.Z)[-1], 5)
sheet -= Plane((0, 0, 80 - 65), z_dir=(1, 0, 0)) * Hole(10 / 2, depth=170)

# From the end of the sheet, create a flange at 60° downward
far_end = sheet.rims().sort_by(Axis.X)[-1]
sheet = flange(
    far_end,
    angle=-60,
    length=65,
    length_mode=LengthMode.VERTICAL,
    length_from=LengthFrom.OUTER_SHARP,
    position=BendPosition.MATERIAL_OUTSIDE,
    sheet_parameters=parameters,
)

# Miter the new flange to make it flare out
sheet = miter(
    sheet.rims().sort_by(Axis.X)[-1].vertices(), -26 / 2, sheet_parameters=parameters
)

# Create the foot as another flange
far_end = sheet.rims().sort_by(Axis.X)[-1]
sheet = flange(
    far_end,
    length=far_end.position_at(0).X - (170 / 2),
    angle=-120,
    position=BendPosition.MATERIAL_OUTSIDE,
    length_from=LengthFrom.OUTER_SHARP,
    sheet_parameters=parameters,
)
sheet = fillet(sheet.vertices().group_by(Axis.Z)[0].group_by(Axis.X)[0], 7)

# Create notches
cutouts = extrude(SlotCenterPoint((170, 0), (154 / 2, 0), 20), amount=-65 / 2)
cutouts += extrude(SlotCenterPoint((170, 0), (206 / 2, 0), 20), amount=-65)
sheet -= cutouts  # the first clears the base but not the foot

# Mirror to create the other half
sheet += mirror(sheet, about=Plane.YZ)

# Create the side flanges
side_rims = [
    sheet.flats().filter_by(Axis.Z).sort_by(Axis.Z)[-1].edges().sort_by(Axis.Y)[i]
    for i in (0, -1)
]
sheet = flange(
    side_rims,
    length=15,
    angle=-75,
    length_from=LengthFrom.TANGENT,
    gaps=(side_rims[0].length - 110) / 2,
    sheet_parameters=parameters,
)
# The two new flats are the only ones that face sideways
wings = sheet.flats().filter_by(lambda flat: abs(flat.normal_at().Y) > 0.5)
sheet = fillet(wings.vertices().group_by(Axis.Z)[0], 7)

sm_hanger = thicken(sheet, sheet_parameters=parameters)

# The flat pattern, with bend allowances from the sheet's parameters
sm_hanger_flat = unfold(sheet, parameters).flat
sm_hanger.material = mild_steel()  # 7800 kg/m³

sm_hanger_flat.position -= sm_hanger_flat.center() + (0, 0, 65)
got_mass = sm_hanger.mass()
want_mass = 1028
tolerance = 10
diff_mass = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.1f} g")
assert diff_mass < tolerance, f"{got_mass=}, {want_mass=}, {diff_mass=}, {tolerance=}"

show(sm_hanger, sm_hanger_flat)
