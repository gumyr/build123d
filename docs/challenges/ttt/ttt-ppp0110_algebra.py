"""
Too Tall Toby Party Pack 01-10 Light Cap
"""

from build123d import *
from bd_materials.materials.plastics import abs_
from ocp_vscode import show

# Half of the cross section, which is used twice: revolved for the rounded
# ends and extruded for the middle

# The wall: the side is the tangent from the edge of the base to the R40
# dome, whose centre is 6 above the base, and the wall is 8 thick
dome = CenterArc((0, 6), 40, 0, 360)
tangent = ConstrainedLines(
    dome, (-84 / 2, 0), selector=lambda lines: lines.sort_by(Axis.Y)[-1]
)
l1 = Line((-84 / 2, 0), tangent @ 0)
l2 = TangentArc(l1 @ 1, (0, 46), tangent=l1 % 1)
l3 = offset([l1, l2], amount=-8, side=Side.RIGHT, closed=False)
l4 = Line(l1 @ 0, l3 @ 1)
l5 = Line(l3 @ 0, l2 @ 1)
wall = make_face([l1, l2, l5, l3, l4])

# The crown: solid from the flat ceiling, 16 below the top, up to the dome
l6 = Line(l2 @ 1, (0, 46 - 16))
l7 = PolarLine(l6 @ 1, l3, direction=(-1, 0))
l8 = TangentArc(l7 @ 1, l2 @ 1, tangent=(-1, 0), tangent_from_first=False)
crown = make_face([l6, l7, l8])

# The wall is square to the side, so its foot dips below the base
half_section = (wall + crown) & Rectangle(1000, 1000, align=(Align.CENTER, Align.MIN))

# One rounded end: the half section revolved, and the half of that which
# lies beyond the end of the middle section
light_cap = revolve(Plane.XZ * half_section, axis=Axis.Z)
light_cap = split(light_cap, bisect_by=Plane.XZ, keep=Keep.BOTTOM)

# Half of the middle section: the whole cross section, extruded
cross_section = half_section + mirror(half_section, about=Plane.YZ)
light_cap += extrude(Plane.XZ * cross_section, amount=50)

# The other half
light_cap += mirror(light_cap, about=Plane.XZ.offset(50))

# Round the two straight edges where the ceiling meets the walls
light_cap = fillet(
    light_cap.edges().filter_by(GeomType.LINE).filter_by(Axis.Y).group_by(Axis.Z)[-1],
    radius=8,
)

part = light_cap
part.material = abs_(density=1020)  # 1020 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 211.30
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
