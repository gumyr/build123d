"""

name: pack_demo.py
by: roman-dvorak <romandvorak@mlab.cz>
date: June 3rd 2024

desc:

    This example shows ability of pack function to pack objects.

"""

# [import]
from build123d import *

# [initial space]
# four boxes, all made at the origin, where they overlap
b1 = Box(100, 100, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
b2 = Box(54, 54, 54, align=(Align.CENTER, Align.CENTER, Align.MAX))
b3 = Box(34, 34, 34, align=(Align.MIN, Align.MIN, Align.CENTER))
b4 = Box(24, 24, 24, align=(Align.MAX, Align.MAX, Align.CENTER))
# [initial space]


def write_svg(part, filename: str, view_port_origin=(-100, 100, 150)):
    """Save an image of the part as SVG"""
    visible, hidden = part.drawing_view(view_port_origin)
    max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
    exporter = ExportSVG(scale=100 / max_dimension)
    exporter.add_layer("Visible", line_weight=0.2)
    exporter.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(f"assets/assemblies/{filename}")


write_svg(Compound([b1, b2, b3, b4]), "pack_demo_initial_state.svg", (50, 0, 100))

# [pack 2D]
xy_pack = pack([b1, b2, b3, b4], padding=5, align_z=False)
# [pack 2D]

write_svg(Compound(xy_pack), "pack_demo_packed_xy.svg", (50, 0, 100))

# [pack and align_z]
z_pack = pack([b1, b2, b3, b4], padding=5, align_z=True)
# [pack and align_z]

write_svg(Compound(z_pack), "pack_demo_packed_z.svg", (50, 0, 100))

# [bounding box]
print(Compound(xy_pack).bounding_box())
# bbox: 0.0 <= x <= 159.0, 0.0 <= y <= 129.0, -54.0 <= z <= 100.0

print(Compound(z_pack).bounding_box())
# bbox: 0.0 <= x <= 159.0, 0.0 <= y <= 129.0, 0.0 <= z <= 100.0
# [bounding box]

xy_box, z_box = Compound(xy_pack).bounding_box(), Compound(z_pack).bounding_box()
assert (xy_box.size - Vector(159, 129, 154)).length < 1e-6 and abs(
    xy_box.min.Z + 54
) < 1e-6
assert (z_box.size - Vector(159, 129, 100)).length < 1e-6 and abs(z_box.min.Z) < 1e-6
# the originals are not moved
assert abs(b2.bounding_box().max.Z) < 1e-6
