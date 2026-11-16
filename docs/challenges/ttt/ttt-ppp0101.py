"""
Too Tall Toby Party Pack 01-01 Bearing Bracket
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_vscode import show

with BuildPart() as bracket:
    # The base plate, with its slot
    with BuildSketch() as base:
        Rectangle(115, 50)
        with Locations((5 / 2, 0)):
            SlotOverall(90, 12, mode=Mode.SUBTRACT)
    extrude(amount=15)

    # One upright: a slot on end, of which the half above the plate is kept
    with BuildSketch(Plane.XZ.offset(50 / 2)) as upright_profile:
        with Locations((-115 / 2 + 26, 15)):
            SlotOverall(42 + 2 * 26 + 12, 2 * 26, rotation=90)
    upright = extrude(amount=-12)
    split(bisect_by=Plane.XY)

    # Blend the upright into the plate
    fillet(bracket.edges().filter_by(Axis.Y).group_by(Axis.X)[-2], 9)

    # The bearing seat, on the outer face of the upright
    with Locations(upright.faces().sort_by(Axis.Y)[0]):
        with Locations((42 / 2 + 6, 0)):
            CounterBoreHole(24 / 2, 34 / 2, 4)

    # The other upright
    mirror(about=Plane.XZ)

    # Round the four upright corners of the part. A fillet of these edges
    # would run on round the tops of the uprights, which are tangent to them,
    # so the part is intersected with a rounded outline instead.
    with BuildSketch() as outline:
        RectangleRounded(115, 50, 6)
    extrude(amount=80, mode=Mode.INTERSECT)

    # The V groove along the underside
    with BuildSketch(Plane.YZ) as groove:
        with BuildLine():
            l1 = Line((0, 0), (18 / 2, 0))
            l2 = PolarLine(l1 @ 1, 8, 60, length_mode=LengthMode.VERTICAL)
            l3 = Line(l2 @ 1, (0, 8))
            mirror(about=Plane.YZ)
        make_face()
    extrude(amount=115 / 2, both=True, mode=Mode.SUBTRACT)

part = bracket.part
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 797.15
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
