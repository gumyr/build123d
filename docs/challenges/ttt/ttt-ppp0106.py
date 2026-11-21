"""
Too Tall Toby Party Pack 01-06 Bearing Jig
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_viewer import show

r1, r2, r3, r4, r5 = 30 / 2, 13 / 2, 12 / 2, 10, 6  # radii used
x1 = 44  # lengths used
y1, y2, y3, y4, y_tot = 36, 36 - 22 / 2, 22 / 2, 42, 69  # widths used

# The outline of the part seen from above, with its holes and keyway
with BuildSketch(Location((0, -r1, y3))) as outline:
    with BuildLine():
        limit = Axis((r1, 0), (0, 1))  # the upright side lies on this line
        m1 = Line((0, y_tot), (x1 / 2, y_tot))
        m2 = JernArc(m1 @ 1, m1 % 1, r4, -90 - 45)
        m3 = PolarLine(m2 @ 1, limit, direction=m2 % 1)  # on, as far as the limit
        m4 = Line(m3 @ 1, (r1, r1))
        m5 = JernArc(m4 @ 1, m4 % 1, r1, -90)
        mirror(about=Plane.YZ)
    make_face()
    # Round the two corners where the slanted sides meet the upright ones
    elbow = (m3 @ 1).Y
    fillet(outline.vertices().filter_by_position(Axis.Y, elbow - 1, elbow + 1), 12)
    with Locations((x1 / 2, y_tot - 10), (-x1 / 2, y_tot - 10)):
        Circle(r2, mode=Mode.SUBTRACT)
    # Keyway
    with Locations((0, r1)):
        Circle(r3, mode=Mode.SUBTRACT)
        Rectangle(4, 3 + 6, align=(Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)

with BuildPart() as jig:
    Box(200, 200, 22)  # Oversized plate
    # Cylinder underneath
    Cylinder(r1, y2, align=(Align.CENTER, Align.CENTER, Align.MAX))
    fillet(jig.edges(Select.NEW), r5)  # Weld together
    extrude(outline.sketch, amount=-y1, mode=Mode.INTERSECT)  # Cut to shape
    # Remove slot
    with Locations((0, y_tot - r1 - y4, 0)):
        Box(
            y_tot,
            y_tot,
            10,
            align=(Align.CENTER, Align.MIN, Align.CENTER),
            mode=Mode.SUBTRACT,
        )

part = jig.part
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 328.02
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
