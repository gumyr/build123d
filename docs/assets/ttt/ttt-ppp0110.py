"""
Too Tall Toby Party Pack 01-10 Light Cap
"""

from build123d import *
from ocp_vscode import *

densa = 7800 / 1e6  # carbon steel density g/mm^3
densb = 2700 / 1e6  # aluminum alloy
densc = 1020 / 1e6  # ABS

with BuildPart() as p:
    with BuildSketch(Plane.YZ.rotated((90, 0, 0))) as s:
        with BuildLine() as l:
            n2 = JernArc((0, 46), (1, 0), 40, -90)
            n3 = Line(n2 @ 1, n2 @ 0)
        make_face()

        with BuildLine() as l2:
            m1 = Line((0, 0), (42, 0))
            m2 = Line((0, 0.01), (42, 0.01))
            m3 = Line(m1 @ 0, m2 @ 0)
            m4 = Line(m1 @ 1, m2 @ 1)
        make_face()
        make_hull()
    extrude(amount=100 / 2)
    revolve(s.sketch, axis=Axis.Y.reverse(), revolution_arc=-90)
    mirror(about=Plane(p.part.faces().sort_by(Axis.X)[-1]))
    mirror(about=Plane.XY)

with BuildPart() as p2:
    add(p.part)
    offset(amount=-8)

with BuildPart() as pzzz:
    add(p2.part)
    split(bisect_by=Plane.XZ.offset(46 - 16), keep=Keep.BOTTOM)
    fillet(pzzz.part.faces().filter_by(Axis.Y).sort_by(Axis.Y)[0].edges(), 12)

with BuildPart() as p3:
    with BuildSketch(Plane.XZ) as s2:
        add(p.part.faces().sort_by(Axis.Y)[-1])
        offset(amount=-8)
    loft([p2.part.faces().sort_by(Axis.Y)[-5], s2.sketch.faces()[0]])

with BuildPart() as ppp0110:
    add(p.part)
    add(pzzz.part, mode=Mode.SUBTRACT)
    add(p3.part, mode=Mode.SUBTRACT)

show(ppp0110)
print(f"\npart mass = {ppp0110.part.volume*densc:0.2f}")
