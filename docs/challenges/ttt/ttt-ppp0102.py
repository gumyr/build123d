"""
Too Tall Toby Party Pack 01-02 Post Cap
"""

from build123d import *
from bd_materials.materials.plastics import abs_
from ocp_vscode import show

with BuildPart() as post_cap:
    # The outside: a cylinder with an elliptical dome, revolved from half
    # its cross section
    with BuildSketch(Plane.XZ) as outside:
        Rectangle(49, 48 - 8, align=(Align.CENTER, Align.MIN))
        Rectangle(9, 48, align=(Align.CENTER, Align.MIN))
        with Locations((9 / 2, 40)):
            Ellipse(20, 8)
        split(bisect_by=Plane.YZ)
    revolve(axis=Axis.Z)

    # The handle: an ellipse swept along an arc
    with BuildLine(Plane.XZ) as handle_path:
        CenterArc((-15, 40 / 2), 17, 90, 180)
    with BuildSketch(Plane.YZ.offset(-15)) as handle_section:
        with Locations((0, 40 / 2 - 17)):
            Ellipse(10 / 2, 4 / 2)
    sweep(path=handle_path.line)

    # Round the two edges where the handle meets the body
    fillet(
        post_cap.edges().filter_by(GeomType.CIRCLE, reverse=True).group_by(Axis.X)[0],
        1,
    )

    # The inside: a tapered hole, with the wall leaning in at 4 degrees
    with BuildSketch(Plane.XZ) as inside:
        with BuildLine():
            wall = PolarLine((42 / 2, 0), 37, 94, length_mode=LengthMode.VERTICAL)
            Polyline(wall @ 1, (0, (wall @ 1).Y), (0, 0), wall @ 0)
        make_face()
        fillet(inside.vertices().group_by(Axis.X)[1], 3)
    revolve(axis=Axis.Z, mode=Mode.SUBTRACT)

part = post_cap.part
part.material = abs_(density=1020)  # 1020 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 43.09
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
