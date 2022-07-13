from build_sketch import *
from build_part import *

height, width, thickness, padding = 60, 80, 10, 12
screw_shaft_radius, screw_head_radius, screw_head_height = 1.5, 3, 3
bearing_axle_radius, bearing_radius, bearing_thickness = 4, 11, 7

# Build pillow block as an extruded sketch with counter bore holes
with BuildPart() as pillow_block:
    with BuildSketch() as plan:
        Rectangle(width, height)
        FilletSketch(*plan.vertices(), radius=5)
    Extrude(thickness)
    WorkplanesFromFaces(pillow_block.faces().filter_by_normal(Axis.Z)[-1])
    CounterBoreHole(bearing_axle_radius, bearing_radius, bearing_thickness)
    RectangularArrayToPart(width - 2 * padding, height - 2 * padding, 2, 2)
    CounterBoreHole(screw_shaft_radius, screw_head_radius, screw_head_height)

# Render the part
if "show_object" in locals():
    show_object(pillow_block.part)
