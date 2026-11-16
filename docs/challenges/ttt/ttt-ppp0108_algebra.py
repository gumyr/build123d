"""
Too Tall Toby Party Pack 01-08 Tie Plate
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_vscode import show

# The plate: half of it drawn and mirrored, then the holes
plate = Rectangle(188 / 2 - 33, 162, align=(Align.MIN, Align.CENTER))
plate += Pos(188 / 2 - 33, 0) * SlotOverall(190, 33 * 2, rotation=90)
plate += mirror(plate, about=Plane.YZ)
plate -= GridLocations(188 - 2 * 33, 190 - 2 * 33, 2, 2) * Circle(29 / 2)
plate -= Circle(84 / 2)
tie_plate = extrude(plate, amount=16)

# The two lugs. One is made from its side view intersected with its plan
# view, and mirrored.
side = Polyline(
    (222 / 2 + 14 - 40 - 40, 0),
    (222 / 2 + 14 - 40, -35 + 16),
    (222 / 2 + 14, -35 + 16),
    (222 / 2 + 14, -35 + 16 + 30),
    (222 / 2 + 14 - 40 - 40, -35 + 16 + 30),
    close=True,
)
side_view = make_face(side) - Pos(222 / 2, -35 + 16 + 14) * Circle(11 / 2)
lug = extrude(Plane.XZ * side_view, amount=20 / 2, both=True)
plan_view = Rectangle(40 + 40, 8, align=(Align.MIN, Align.CENTER))
plan_view += Pos(40, 0) * Rectangle(40, 20, align=(Align.MIN, Align.CENTER))
lug &= extrude(Pos(side @ 0) * plan_view, amount=30, both=True)
tie_plate += [lug, mirror(lug, about=Plane.YZ)]

part = tie_plate
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 3387.06
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
