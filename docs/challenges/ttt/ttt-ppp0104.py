"""
Too Tall Toby Party Pack 01-04 Angle Bracket
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_viewer import show

d1, d2, d3 = 38, 26, 16
h1, h2, h3, h4 = 20, 8, 7, 23
w1, w2, w3 = 80, 10, 5
f1, f2, f3 = 4, 10, 5
sloth1, sloth2 = 18, 12
slotw1, slotw2 = 17, 14

with BuildPart() as bracket:
    # The boss: two cylinders, one on the other
    with BuildSketch() as boss:
        Circle(d1 / 2)
    extrude(amount=h1)
    with BuildSketch(Plane.XY.offset(h1)) as neck:
        Circle(d2 / 2)
    extrude(amount=h2)

    # The arm. It is as wide as the boss, so its sides are tangent to the
    # boss and the edge between them cannot be filleted as it stands. The
    # arm is made wider, the fillet is applied, and the extra width is then
    # cut away.
    with BuildSketch(Plane.YZ) as wide_arm:
        Rectangle(d1 + 15, h3, align=(Align.CENTER, Align.MIN))
    extrude(amount=w1 - d1 / 2)
    fillet(bracket.edges().group_by(Axis.Z)[2].filter_by(GeomType.CIRCLE), f1)
    with BuildSketch(Plane.YZ) as extra_width:
        Rectangle(d1 + 15, 15, align=(Align.CENTER, Align.MIN))
        Rectangle(d1, 15, mode=Mode.SUBTRACT, align=(Align.CENTER, Align.MIN))
    extrude(amount=w1 - d1 / 2, mode=Mode.SUBTRACT)

    # The bore
    with BuildSketch() as bore:
        Circle(d3 / 2)
    extrude(amount=h1 + h2, mode=Mode.SUBTRACT)

    # The leg at the end of the arm, turned down
    with BuildSketch() as leg:
        with Locations((w1 - d1 / 2 - w2 / 2, 0)):
            Rectangle(w2, d1)
    extrude(amount=-h4)
    fillet(bracket.edges().group_by(Axis.X)[-1].sort_by(Axis.Z)[-1], f2)
    fillet(bracket.edges().group_by(Axis.X)[-4].sort_by(Axis.Z)[-2], f3)

    # The stepped slot in the leg
    end_plane = Plane.YZ.offset(w1 - d1 / 2)
    with BuildSketch(end_plane) as wide_slot:
        with Locations((0, -h4)):
            SlotOverall(slotw1 * 2, sloth1, 90)
    extrude(amount=-w3, mode=Mode.SUBTRACT)
    with BuildSketch(end_plane) as narrow_slot:
        with Locations((0, -h4)):
            SlotOverall(slotw2 * 2, sloth2, 90)
    extrude(amount=-w2, mode=Mode.SUBTRACT)

part = bracket.part
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 310
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
