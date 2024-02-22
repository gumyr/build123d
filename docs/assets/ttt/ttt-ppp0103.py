"""
Too Tall Toby Party Pack 01-03 C Clamp Base
"""

from build123d import *
from ocp_vscode import *

densa = 7800 / 1e6  # carbon steel density g/mm^3
densb = 2700 / 1e6  # aluminum alloy
densc = 1020 / 1e6  # ABS


with BuildPart() as ppp0103:
    with BuildSketch() as sk1:
        RectangleRounded(34 * 2, 95, 18)
        with Locations((0, -2)):
            RectangleRounded((34 - 16) * 2, 95 - 18 - 14, 7, mode=Mode.SUBTRACT)
        with Locations((-34 / 2, 0)):
            Rectangle(34, 95, 0, mode=Mode.SUBTRACT)
    extrude(amount=16)
    with BuildSketch(Plane.XZ.offset(-95 / 2)) as cyl1:
        with Locations((0, 16 / 2)):
            Circle(16 / 2)
    extrude(amount=18)
    with BuildSketch(Plane.XZ.offset(95 / 2 - 14)) as cyl2:
        with Locations((0, 16 / 2)):
            Circle(16 / 2)
    extrude(amount=23)
    with Locations(Plane.XZ.offset(95 / 2 + 9)):
        with Locations((0, 16 / 2)):
            CounterSinkHole(5.5 / 2, 11.2 / 2, None, 90)

show(ppp0103)
print(f"\npart mass = {ppp0103.part.volume*densb:0.2f}")
