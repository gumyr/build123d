"""
Too Tall Toby Party Pack 01-08 Tie Plate
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_viewer import show

with BuildPart() as tie_plate:
    # The plate: half of it drawn and mirrored, then the holes
    with BuildSketch() as plate:
        Rectangle(188 / 2 - 33, 162, align=(Align.MIN, Align.CENTER))
        with Locations((188 / 2 - 33, 0)):
            SlotOverall(190, 33 * 2, rotation=90)
        mirror(about=Plane.YZ)
        with GridLocations(188 - 2 * 33, 190 - 2 * 33, 2, 2):
            Circle(29 / 2, mode=Mode.SUBTRACT)
        Circle(84 / 2, mode=Mode.SUBTRACT)
    extrude(amount=16)

    # The two lugs. One is made as a part of its own, from its side view
    # intersected with its plan view, and mirrored; it joins the plate when
    # its builder closes.
    with BuildPart() as lugs:
        with BuildSketch(Plane.XZ) as side_view:
            with BuildLine():
                side = Polyline(
                    (222 / 2 + 14 - 40 - 40, 0),
                    (222 / 2 + 14 - 40, -35 + 16),
                    (222 / 2 + 14, -35 + 16),
                    (222 / 2 + 14, -35 + 16 + 30),
                    (222 / 2 + 14 - 40 - 40, -35 + 16 + 30),
                    close=True,
                )
            make_face()
            with Locations((222 / 2, -35 + 16 + 14)):
                Circle(11 / 2, mode=Mode.SUBTRACT)
        extrude(amount=20 / 2, both=True)
        with BuildSketch() as plan_view:
            with Locations(side @ 0):
                Rectangle(40 + 40, 8, align=(Align.MIN, Align.CENTER))
                with Locations((40, 0)):
                    Rectangle(40, 20, align=(Align.MIN, Align.CENTER))
        extrude(amount=30, both=True, mode=Mode.INTERSECT)
        mirror(about=Plane.YZ)

part = tie_plate.part
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 3387.06
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
