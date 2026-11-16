"""
Too Tall Toby Party Pack 01-09 Corner Tie
"""

from math import sqrt

from build123d import *
from bd_materials.materials.metals import aluminum
from ocp_viewer import show

with BuildPart() as corner_tie:
    # The base plate, rounded at one end, with a counterbored hole at the
    # centre of each rounded corner
    with BuildSketch() as plate:
        Rectangle(69, 75, align=(Align.MAX, Align.CENTER))
        fillet(plate.vertices().group_by(Axis.X)[0], 17)
    extrude(amount=13)
    centers = [
        arc.arc_center
        for arc in corner_tie.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[-1]
    ]
    with Locations(*centers):
        CounterBoreHole(radius=8 / 2, counter_bore_radius=15 / 2, counter_bore_depth=4)

    # The upright: an eye, with sides that leave it at a tangent and run
    # down to the full width of the plate
    with BuildSketch(Plane.YZ) as upright:
        with Locations((0, 45)):
            Circle(15)
        eye = upright.edge()
        with BuildLine():
            side = Axis((75 / 2, 0), (0, 1))  # the edge of the plate
            u = eye.find_tangent(75 / 2 + 90)[0]  # where the eye has that slope
            l1 = PolarLine(eye.position_at(u), side, direction=-eye.tangent_at(u))
            Line(l1 @ 0, (0, 45))
            Polyline((0, 0), (75 / 2, 0), l1 @ 1)
            mirror(about=Plane.YZ)
        make_face()
        with Locations((0, 45)):
            Circle(12 / 2, mode=Mode.SUBTRACT)
    extrude(amount=-13)

    # The brace, on a plane at 45 degrees through the corner
    with BuildSketch(Plane((0, 0, 0), x_dir=(1, 0, 0), z_dir=(1, 0, 1))) as brace:
        Rectangle(45 * 2 / sqrt(2) - 37.5, 75, align=(Align.MIN, Align.CENTER))
        with Locations(brace.edges().sort_by(Axis.X)[-1].center()):
            Circle(37.5)
            Circle(33 / 2, mode=Mode.SUBTRACT)
        split(bisect_by=Plane.YZ)
    extrude(amount=6)

    # Carry the underside of the brace on to meet the plate and the upright
    underside = corner_tie.faces().filter_by(Axis((0, 0, 0), (-1, 0, 1)))[0]
    extrude(underside, until=Until.NEXT)
    fillet(corner_tie.edges().filter_by(Axis.Y).sort_by(Axis.Z)[2], 16)

part = corner_tie.part
part.material = aluminum()  # 2700 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 307.23
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
