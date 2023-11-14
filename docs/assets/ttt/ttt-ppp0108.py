"""
Too Tall Toby Party Pack 01-08 Tie Plate
"""
from build123d import *
from ocp_vscode import *

densa = 7800 / 1e6  # carbon steel density g/mm^3
densb = 2700 / 1e6  # aluminum alloy
densc = 1020 / 1e6  # ABS

with BuildPart() as p2:
    with BuildSketch() as s:
        with BuildLine() as l:
            l1 = Line((50, 0), (50, 7 / 2))
            l2 = PolarLine(l1 @ 1, 40 + 32, 10, length_mode=LengthMode.HORIZONTAL)
            l3 = Line(l2 @ 1, l2 @ 1 + (0, -20))
            mirror(about=Plane.XZ)
        make_face()
    extrude(amount=-20)
    extrude(to_extrude=s.sketch, amount=-12)

    with BuildSketch(Plane.XZ) as s2:
        with Locations((244 / 2, -20)):
            Rectangle(32, 32, align=(Align.MAX, Align.MIN))
            with Locations((-40 - 32, 20)):
                Rectangle(0.001, 0.001)
        make_hull()
        with Locations((244 / 2, -20)):
            with Locations((-12, 14)):
                Circle(14 / 2, mode=Mode.SUBTRACT)
    extrude(amount=20, both=True, mode=Mode.INTERSECT)
    mirror(about=Plane.YZ)

with BuildSketch() as s3:
    with Locations((-186 / 2 + 33, 0), (186 / 2 - 33, 0)):
        SlotOverall(190, 66, rotation=90)

with BuildPart() as p:
    with BuildSketch() as s4:
        Rectangle(186 - 33 * 2, 162)
        add(s3.sketch)
    extrude(amount=30)

    with BuildSketch(Plane.XZ) as s5:
        with BuildLine(Plane.XZ) as l2:
            m1 = Line((0, 0), (186 / 2, 0))
            m2 = Line(m1 @ 1, m1 @ 1 + (0, 16))
            m3 = RadiusArc(m2 @ 1, (-186 / 2, 16), -420)
            mirror(about=Plane.YZ)
        make_face()
    extrude(amount=100, both=True, mode=Mode.INTERSECT)

    with BuildSketch() as s6:
        with GridLocations(186 - 33 * 2, 190 - 33 * 2, 2, 2):
            Circle(30 / 2)
        Circle(69 / 2)
    extrude(amount=40, mode=Mode.SUBTRACT)
    add(p2.part)


# https://www.youtube.com/watch?v=QwEAeYLZAQo&t=2451s

show(p)
print(f"\npart mass = {p.part.volume*densa:0.2f}")
