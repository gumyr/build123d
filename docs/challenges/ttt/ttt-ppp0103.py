"""
Too Tall Toby Party Pack 01-03 C Clamp Base
"""

from build123d import *
from bd_materials.materials.metals import aluminum
from ocp_viewer import show

with BuildPart() as clamp:
    # The C-shaped frame: a rounded rectangle with a rounded window, less
    # the half to one side of the centre line
    with BuildSketch() as frame:
        RectangleRounded(34 * 2, 95, 18)
        with Locations((0, -2)):
            RectangleRounded((34 - 16) * 2, 95 - 18 - 14, 7, mode=Mode.SUBTRACT)
        with Locations((-34 / 2, 0)):
            Rectangle(34, 95, mode=Mode.SUBTRACT)
    extrude(amount=16)

    # A round boss on each jaw, lying along Y at half the height of the frame
    with BuildSketch(Plane.XZ.offset(-95 / 2)) as fixed_boss:
        with Locations((0, 16 / 2)):
            Circle(16 / 2)
    extrude(amount=18)
    with BuildSketch(Plane.XZ.offset(95 / 2 - 14)) as screw_boss:
        with Locations((0, 16 / 2)):
            Circle(16 / 2)
    extrude(amount=23)

    # The countersunk hole, through the screw boss and on through the other jaw
    with Locations(Plane.XZ.offset(95 / 2 + 9)):
        with Locations((0, 16 / 2)):
            CounterSinkHole(5.5 / 2, 11.2 / 2, counter_sink_angle=90)

part = clamp.part
part.material = aluminum()  # 2700 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 96.13
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
