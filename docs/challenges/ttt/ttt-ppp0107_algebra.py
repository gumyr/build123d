"""
Too Tall Toby Party Pack 01-07 Flanged Hub
"""

from build123d import *
from bd_materials.materials.metals import aluminum
from ocp_viewer import show

# The plane the rib is drawn on: it starts as the ceiling of the pocket,
# facing down, is moved out to the wall of the bore, tilted 45 degrees
# about its own y direction (which points along -Y), and set back
rib_plane = Plane(origin=(0, 0, 18), x_dir=(1, 0, 0), z_dir=(0, 0, -1))
rib_plane.origin = rib_plane.origin + Vector(20 / 2, 0, 0)
rib_plane = rib_plane.rotated((0, -45, 0))
rib_plane = rib_plane.offset(-25 + 3 + 0.10)

# Three steps: the flange, the body and the neck
hub = extrude(Circle(130 / 2), amount=8)
hub += extrude(Plane.XY.offset(8) * Circle(84 / 2), amount=25 - 8)
hub += extrude(Plane.XY.offset(25) * Circle(35 / 2), amount=52 - 25)

# The pocket underneath and the bore through the neck
hub -= extrude(Circle(73 / 2), amount=18)
hub -= extrude(Plane.XY.offset(52) * Circle(20 / 2), amount=-52)

# Round the circular edges between the top and bottom pairs, all but the
# smallest
hub = fillet(
    hub.edges()
    .filter_by(GeomType.CIRCLE)
    .sort_by(Axis.Z)[2:-2]
    .sort_by(Edge.radius)[1:],
    3,
)

# One rib: a tapered bar, trimmed to what lies above the body and outside
# the neck, then placed three times round the axis
rib_section = rib_plane * Rectangle((73 - 35) / 2 * 1.414 + 5, 3)
rib = extrude(rib_section, amount=15, taper=-20 / 2)
rib = split(rib, bisect_by=Plane.XY.offset(25))
rib = split(rib, bisect_by=Plane.YZ.offset(35 / 2 - 1))
hub += PolarLocations(0, 3) * rib

# Six counterbored holes in the flange
hub -= (
    Pos(Z=8)
    * PolarLocations(107.95 / 2, 6)
    * CounterBoreHole(6 / 2, 13 / 2, 4, depth=8)
)

part = hub
part.material = aluminum()  # 2700 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 372.99
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
