"""

name: pack_demo.py
by: roman-dvorak <romandvorak@mlab.cz>
date: June 3rd 2024

desc:
    
    This example shows ability of pack function to pack objects.

"""

from tools.svg import write_svg, project_shapes

# [import]
from build123d import *
from ocp_vscode import *


# [initial space]
b1 = Box(100, 100, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
b2 = Box(54, 54, 54, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
b3 = Box(34, 34, 34, align=(Align.MIN, Align.MIN, Align.CENTER), mode=Mode.SUBTRACT)
b4 = Box(24, 24, 24, align=(Align.MAX, Align.MAX, Align.CENTER), mode=Mode.SUBTRACT)




# [Export SVG files]
write_svg(
    "pack_demo_initial_state",
    project_shapes(Compound(
        [b1, b2, b3, b4,],
        "pack_demo_initial_state"
    ))
)

# [pack 2D]

xy_pack = pack(
    [b1, b2, b3, b4],
    padding=5,
    align_z=False
)

write_svg("pack_demo_packed_xy", project_shapes(Compound(xy_pack)))


# [Pack and align_z]


z_pack = pack(
    [b1, b2, b3, b4],
    padding=5,
    align_z=True
)

write_svg("pack_demo_packed_z", project_shapes(Compound(z_pack)))


# [bounding box]
print(Compound(xy_pack).bounding_box())
print(Compound(z_pack).bounding_box())