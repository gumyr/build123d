"""
Too Tall Toby Party Pack 01-05 Paste Sleeve
"""

from build123d import *
from ocp_vscode import *

densa = 7800 / 1e6  # carbon steel density g/mm^3
densb = 2700 / 1e6  # aluminum alloy
densc = 1020 / 1e6  # ABS

with BuildPart() as p:
    with BuildSketch() as s:
        SlotOverall(45, 38)
        offset(amount=3)
    with BuildSketch(Plane.XY.offset(133 - 30)) as s2:
        SlotOverall(60, 4)
        offset(amount=3)
    loft()

    with BuildSketch() as s3:
        SlotOverall(45, 38)
    with BuildSketch(Plane.XY.offset(133 - 30)) as s4:
        SlotOverall(60, 4)
    loft(mode=Mode.SUBTRACT)

    extrude(p.part.faces().sort_by(Axis.Z)[0], amount=30)

show(p)
print(f"\npart mass = {p.part.volume*densc:0.2f}")
