from build123d import *
from build123d.part_operations import *
import build123d.alg_compat as COMPAT

# 35x7.5mm DIN Rail Dimensions
overall_width, top_width, height, thickness, fillet_radius = 35, 27, 7.5, 1, 0.8
rail_length = 1000
slot_width, slot_length, slot_pitch = 6.2, 15, 25

din = Rectangle(overall_width, thickness, align=(Align.CENTER, Align.MIN))
din += Rectangle(top_width, height, align=(Align.CENTER, Align.MIN))
din -= Rectangle(
    top_width - 2 * thickness,
    height - thickness,
    align=(Align.CENTER, Align.MIN),
)

inside_vertices = (
    din.vertices()
    .filter_by_position(Axis.Y, 0.0, height, inclusive=(False, False))
    .filter_by_position(
        Axis.X,
        -overall_width / 2,
        overall_width / 2,
        inclusive=(False, False),
    )
)

din = COMPAT.fillet(din, inside_vertices, radius=fillet_radius)

outside_vertices = filter(
    lambda v: (v.Y == 0.0 or v.Y == height)
    and -overall_width / 2 < v.X < overall_width / 2,
    din.vertices(),
)
din = COMPAT.fillet(din, outside_vertices, radius=fillet_radius + thickness)

rail = extrude(din, rail_length)

plane = Plane(rail.faces().sort_by(Axis.Y).last)

slot_faces = [
    (plane * loc * SlotOverall(slot_length, slot_width)).faces()[0]
    for loc in GridLocations(0, slot_pitch, 1, rail_length // slot_pitch - 1)
]

rail -= extrude(slot_faces, -height)
rail = Plane.XZ * rail

if "show_object" in locals():
    show_object(rail, name="rail")
