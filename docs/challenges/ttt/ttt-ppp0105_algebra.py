"""
Too Tall Toby Party Pack 01-05 Paste Sleeve
"""

from build123d import *
from bd_materials.materials.plastics import abs_
from ocp_vscode import show

flat_end = Plane.XY.offset(133 - 30)

# The outside of the tapered section: a loft from the round end to the flat
# end, each 3 larger all round than the opening
round_opening = SlotOverall(45, 38)
flat_opening = flat_end * SlotOverall(60, 4)
sleeve = loft([offset(round_opening, amount=3), offset(flat_opening, amount=3)])

# The inside: the same loft between the two openings, taken away
sleeve -= loft([round_opening, flat_opening])

# The lower section: the ring at the round end, extruded
sleeve += extrude(sleeve.faces().sort_by(Axis.Z)[0], amount=30)

part = sleeve
part.material = abs_(density=1020)  # 1020 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 57.08
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
