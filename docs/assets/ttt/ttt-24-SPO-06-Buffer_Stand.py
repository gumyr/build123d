from build123d import *
from ocp_vscode import show

with BuildPart() as p:
    with BuildSketch() as xy:
        with BuildLine():
            l1 = ThreePointArc((5 / 2, -1.25), (5.5 / 2, 0), (5 / 2, 1.25))
            Polyline(l1 @ 0, (0, -1.25), (0, 1.25), l1 @ 1)
        make_face()
    extrude(amount=4)

    with BuildSketch(Plane.YZ) as yz:
        Trapezoid(2.5, 4, 90 - 6, align=(Align.CENTER, Align.MIN))
        _, arc_center, arc_radius = full_round(yz.edges().sort_by(SortBy.LENGTH)[0])
    extrude(amount=10, mode=Mode.INTERSECT)

    # To avoid OCCT problems, don't attempt to extend the top arc, remove instead
    with BuildPart(mode=Mode.SUBTRACT) as internals:
        y = p.edges().filter_by(Axis.X).sort_by(Axis.Z)[-1].center().Z

        with BuildSketch(Plane.YZ.offset(4.25 / 2)) as yz:
            Trapezoid(2.5, y, 90 - 6, align=(Align.CENTER, Align.MIN))
            with Locations(arc_center):
                Circle(arc_radius, mode=Mode.SUBTRACT)
        extrude(amount=-(4.25 - 3.5) / 2)

        with BuildSketch(Plane.YZ.offset(3.5 / 2)) as yz:
            Trapezoid(2.5, 4, 90 - 6, align=(Align.CENTER, Align.MIN))
        extrude(amount=-3.5 / 2)

        with BuildSketch(Plane.XZ.offset(-2)) as xz:
            with Locations((0, 4)):
                RectangleRounded(4.25, 7.5, 0.5)
        extrude(amount=4, mode=Mode.INTERSECT)

    with Locations(p.faces(Select.LAST).filter_by(GeomType.PLANE).sort_by(Axis.Z)[-1]):
        CounterBoreHole(0.625 / 2, 1.25 / 2, 0.5)

    with BuildSketch(Plane.YZ) as rib:
        with Locations((0, 0.25)):
            Trapezoid(0.5, 1, 90 - 8, align=(Align.CENTER, Align.MIN))
        full_round(rib.edges().sort_by(SortBy.LENGTH)[0])
    extrude(amount=4.25 / 2)

    mirror(about=Plane.YZ)

part = scale(p.part, IN)
print(f"\npart weight = {part.volume*7800e-6/LB:0.2f} lbs")

show(p)
