"""
Too Tall Toby 23-T-24 Curved Support
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_vscode import show

# The profile of the bridge between the two bosses. Two of its arcs are
# fixed only by what they touch, so they are found with ConstrainedArcs.

# Construction lines: the top of the bridge falls at 8 degrees from the tall
# boss, and its far end lies flat at a height of 32
slope = PolarLine((55 / 2, 50), 100, -8)
flat = Line((0, 32), (125, 32))

# The R30 circle is tangent to the slope from below, with its centre
# 77 - 55 / 2 from the axis of the tall boss
circle_30 = ConstrainedArcs(
    slope,
    radius=30,
    center_on=Axis((77 - 55 / 2, 0), (0, 1)),
    selector=lambda arcs: arcs.sort_by(Axis.Y)[0],
).edge()

# The R66 arc is tangent to that circle and to the flat, from above
l3 = ConstrainedArcs(
    circle_30, flat, radius=66, selector=lambda arcs: arcs.sort_by(Axis.Y)[-1]
)

# Where the slope touches the R30 circle: 30 from its centre, square to the
# slope
touch = circle_30.arc_center + Vector(0, 0, 1).cross(slope % 0) * 30
l1 = Line((55 / 2, 50), touch)
l2 = RadiusArc(l1 @ 1, l3 @ 0, 30)
l4 = Polyline(l3 @ 1, (125, 32), (125, 0), (0, 0), (0, (l1 @ 0).Y), l1 @ 0)
profile = make_face([l1, l2, l3, l4])

# The two bosses, and the base between them as their hull
tall_boss = Circle(55 / 2)
short_boss = Pos(0, 125) * Circle(30 / 2)
base_hull = make_hull(tall_boss.edges() + short_boss.edges())
curved_support = extrude(tall_boss + short_boss, amount=32)
curved_support += extrude(tall_boss, amount=60)
curved_support += extrude(base_hull, amount=11)

# The bridge
curved_support += extrude(Plane.YZ * profile, amount=11 / 2, both=True)

# The holes
curved_support -= Hole(35 / 2, depth=60)
curved_support -= Pos(0, 125) * Hole(20 / 2, depth=32)

part = curved_support
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 1294
tolerance = 3
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
