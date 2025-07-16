from copy import copy
import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

with BuildPart() as part:
    Cylinder(10, 30, rotation=(90, 0, 0))
    Cylinder(8, 40, rotation=(90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MAX))
    Cylinder(8, 23, rotation=(90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    Cylinder(5, 40, rotation=(90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildSketch(Plane.XY.offset(8)) as s:
        SlotCenterPoint((0, 38), (0, 48), 5)
    extrude(amount=2.5, both=True, mode=Mode.SUBTRACT)

    before = copy(part)

    faces = part.faces().group_by(
        lambda f: Face(f.inner_wires()[0]).area if f.inner_wires() else 0
    )
    chamfer([f.outer_wire().edges() for f in faces[-1]], 0.5)

show(
    before,
    [f.translate(f.normal_at() * 0.01) for f in faces],
    part.part.translate((40, 40)),
)
save_screenshot(os.path.join(filedir, "group_hole_area.png"))
