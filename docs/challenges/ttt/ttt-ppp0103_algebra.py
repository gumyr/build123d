"""
Too Tall Toby Party Pack 01-03 C Clamp Base
"""

from build123d import *
from bd_materials.materials.metals import aluminum
from ocp_vscode import show

# The C-shaped frame: a rounded rectangle with a rounded window, less the
# half to one side of the centre line
frame = RectangleRounded(34 * 2, 95, 18)
frame -= Pos(0, -2) * RectangleRounded((34 - 16) * 2, 95 - 18 - 14, 7)
frame -= Pos(-34 / 2, 0) * Rectangle(34, 95)
clamp = extrude(frame, amount=16)

# A round boss on each jaw, lying along Y at half the height of the frame
boss = Pos(0, 16 / 2) * Circle(16 / 2)
clamp += extrude(Plane.XZ.offset(-95 / 2) * boss, amount=18)
clamp += extrude(Plane.XZ.offset(95 / 2 - 14) * boss, amount=23)

# The countersunk hole, through the screw boss and on through the other jaw
hole_place = Plane.XZ.offset(95 / 2 + 9) * Pos(0, 16 / 2)
clamp -= hole_place * CounterSinkHole(
    5.5 / 2, 11.2 / 2, depth=95 + 9, counter_sink_angle=90
)

part = clamp
part.material = aluminum()  # 2700 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 96.13
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
