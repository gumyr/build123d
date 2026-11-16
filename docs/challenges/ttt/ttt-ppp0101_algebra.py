"""
Too Tall Toby Party Pack 01-01 Bearing Bracket
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_viewer import show

# The base plate, with its slot
base = Rectangle(115, 50) - Pos(5 / 2, 0) * SlotOverall(90, 12)
bracket = extrude(base, amount=15)

# One upright: a slot on end, of which the half above the plate is kept
upright_profile = Pos(-115 / 2 + 26, 15) * SlotOverall(
    42 + 2 * 26 + 12, 2 * 26, rotation=90
)
upright = extrude(Plane.XZ.offset(50 / 2) * upright_profile, amount=-12)
bracket = split(bracket + upright, bisect_by=Plane.XY)

# Blend the upright into the plate
bracket = fillet(bracket.edges().filter_by(Axis.Y).group_by(Axis.X)[-2], 9)

# The bearing seat, on the outer face of the upright
seat_plane = Plane(upright.faces().sort_by(Axis.Y)[0])
bracket -= (
    seat_plane * Pos(42 / 2 + 6, 0) * CounterBoreHole(24 / 2, 34 / 2, 4, depth=12)
)

# The other upright
bracket += mirror(bracket, about=Plane.XZ)

# Round the four upright corners of the part. A fillet of these edges
# would run on round the tops of the uprights, which are tangent to them,
# so the part is intersected with a rounded outline instead.
bracket &= extrude(RectangleRounded(115, 50, 6), amount=80)

# The V groove along the underside
l1 = Line((0, 0), (18 / 2, 0))
l2 = PolarLine(l1 @ 1, 8, 60, length_mode=LengthMode.VERTICAL)
l3 = Line(l2 @ 1, (0, 8))
half_groove = [l1, l2, l3]
groove = make_face(half_groove + [mirror(line, Plane.YZ) for line in half_groove])
bracket -= extrude(Plane.YZ * groove, amount=115 / 2, both=True)

part = bracket
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 797.15
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
