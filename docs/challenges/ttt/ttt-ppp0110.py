"""
Too Tall Toby Party Pack 01-10 Light Cap
"""

from build123d import *
from bd_materials.materials.plastics import abs_
from ocp_vscode import show

# Half of the cross section, drawn in a sketch of its own so that it can be
# used twice: revolved for the rounded ends and extruded for the middle
with BuildSketch() as half_section:
    # The wall: the side is the tangent from the edge of the base to the
    # R40 dome, whose centre is 6 above the base, and the wall is 8 thick
    with BuildLine():
        dome = CenterArc((0, 6), 40, 0, 360, mode=Mode.PRIVATE)
        tangent = ConstrainedLines(
            dome,
            (-84 / 2, 0),
            selector=lambda lines: lines.sort_by(Axis.Y)[-1],
            mode=Mode.PRIVATE,
        )
        l1 = Line((-84 / 2, 0), tangent @ 0)
        l2 = TangentArc(l1 @ 1, (0, 46), tangent=l1 % 1)
        l3 = offset(amount=-8, side=Side.RIGHT, closed=False, mode=Mode.ADD)
        l4 = Line(l1 @ 0, l3 @ 1)
        l5 = Line(l3 @ 0, l2 @ 1)
    make_face()
    # The crown: solid from the flat ceiling, 16 below the top, up to the dome
    with BuildLine():
        l6 = Line(l2 @ 1, (0, 46 - 16))
        l7 = PolarLine(l6 @ 1, l3, direction=(-1, 0))
        l8 = TangentArc(l7 @ 1, l2 @ 1, tangent=(-1, 0), tangent_from_first=False)
    make_face()
    # The wall is square to the side, so its foot dips below the base
    Rectangle(1000, 1000, align=(Align.CENTER, Align.MIN), mode=Mode.INTERSECT)

with BuildPart() as light_cap:
    # One rounded end: the half section revolved, and the half of that
    # which lies beyond the end of the middle section
    with BuildSketch(Plane.XZ):
        insert(half_section.sketch)
    revolve(axis=Axis.Z)
    split(bisect_by=Plane.XZ, keep=Keep.BOTTOM)

    # Half of the middle section: the whole cross section, extruded
    with BuildSketch(Plane.XZ):
        insert(half_section.sketch)
        mirror(about=Plane.YZ)
    extrude(amount=50)

    # The other half
    mirror(about=Plane.XZ.offset(50))

    # Round the two straight edges where the ceiling meets the walls
    fillet(
        light_cap.edges()
        .filter_by(GeomType.LINE)
        .filter_by(Axis.Y)
        .group_by(Axis.Z)[-1],
        radius=8,
    )

part = light_cap.part
part.material = abs_(density=1020)  # 1020 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 211.30
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
