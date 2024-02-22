"""
Too Tall Toby Party Pack 01-02 Post Cap
"""

from build123d import *
from ocp_vscode import *

densa = 7800 / 1e6  # carbon steel density g/mm^3
densb = 2700 / 1e6  # aluminum alloy
densc = 1020 / 1e6  # ABS


# TTT Party Pack 01: PPP0102, mass(abs) = 43.09g
with BuildPart() as p:
    with BuildSketch(Plane.XZ) as sk1:
        Rectangle(49, 48 - 8, align=(Align.CENTER, Align.MIN))
        Rectangle(9, 48, align=(Align.CENTER, Align.MIN))
        with Locations((9 / 2, 40)):
            Ellipse(20, 8)
        split(bisect_by=Plane.YZ)
    revolve(axis=Axis.Z)

    with BuildSketch(Plane.YZ.offset(-15)) as xc1:
        with Locations((0, 40 / 2 - 17)):
            Ellipse(10 / 2, 4 / 2)
        with BuildLine(Plane.XZ) as l1:
            CenterArc((-15, 40 / 2), 17, 90, 180)
    sweep(path=l1)

    fillet(p.edges().filter_by(GeomType.CIRCLE, reverse=True).group_by(Axis.X)[0], 1)

    with BuildLine(mode=Mode.PRIVATE) as lc1:
        PolarLine(
            (42 / 2, 0), 37, 94, length_mode=LengthMode.VERTICAL
        )  # construction line

    pts = [
        (0, 0),
        (42 / 2, 0),
        ((lc1.line @ 1).X, (lc1.line @ 1).Y),
        (0, (lc1.line @ 1).Y),
    ]
    with BuildSketch(Plane.XZ) as sk2:
        Polygon(*pts, align=None)
        fillet(sk2.vertices().group_by(Axis.X)[1], 3)
    revolve(axis=Axis.Z, mode=Mode.SUBTRACT)

show(p)
print(f"\npart mass = {p.part.volume*densa:0.2f}")
