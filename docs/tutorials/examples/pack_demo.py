"""

name: pack_demo.py
by: roman-dvorak <romandvorak@mlab.cz>
date: June 3rd 2024

desc:
    
    This example shows ability of pack function to pack objects.

"""



# [import]
from build123d import *
from ocp_vscode import *


# [initial space]
b1 = Box(100, 100, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
b2 = Box(54, 54, 54, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
b3 = Box(34, 34, 34, align=(Align.MIN, Align.MIN, Align.CENTER), mode=Mode.SUBTRACT)
b4 = Box(24, 24, 24, align=(Align.MAX, Align.MAX, Align.CENTER), mode=Mode.SUBTRACT)




# [Export SVG files]
def write_svg(part, filename: str, view_port_origin=(-100, 100, 150)):
    """Save an image of the BuildPart object as SVG"""
    visible, hidden = part.project_to_viewport(view_port_origin)
    max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
    exporter = ExportSVG(scale=100 / max_dimension)
    exporter.add_layer("Visible", line_weight=0.2)
    exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(f"assets/{filename}.svg")




write_svg(
    Compound(
        [b1, b2, b3, b4,],
        "pack_demo_initial_state"
    ),
    "pack_demo_initial_state.svg",
    (50, 0, 100),
)

# [pack 2D]

xy_pack = pack(
    [b1, b2, b3, b4],
    padding=5,
    align_z=False
)

write_svg(Compound(xy_pack), "pack_demo_packed_xy.svg", (50, 0, 100))


# [Pack and align_z]


z_pack = pack(
    [b1, b2, b3, b4],
    padding=5,
    align_z=True
)

write_svg(Compound(z_pack), "pack_demo_packed_z.svg", (50, 0, 100))


# [bounding box]
print(Compound(xy_pack).bounding_box())
print(Compound(z_pack).bounding_box())