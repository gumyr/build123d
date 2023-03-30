from build123d import *

height, width, thickness, padding = 60, 80, 10, 12
screw_shaft_radius, screw_head_radius, screw_head_height = 1.5, 3, 3
bearing_axle_radius, bearing_radius, bearing_thickness = 4, 11, 7

# Build pillow block as an extruded sketch with counter bore holes
plan = Rectangle(width, height)
plan = fillet(plan.vertices(), radius=5)
pillow_block = extrude(plan, thickness)

plane = Plane(pillow_block.faces().sort_by().last)

pillow_block -= plane * CounterBoreHole(
    bearing_axle_radius, bearing_radius, bearing_thickness, height
)
locs = GridLocations(width - 2 * padding, height - 2 * padding, 2, 2)
pillow_block -= (
    plane
    * locs
    * CounterBoreHole(screw_shaft_radius, screw_head_radius, screw_head_height, height)
)

# Render the part
if "show_object" in locals():
    show_object(pillow_block)
