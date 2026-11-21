"""
Too Tall Toby Party Pack 01-02 Post Cap
"""

from build123d import *
from bd_materials.materials.plastics import abs_
from ocp_viewer import show

# The outside: a cylinder with an elliptical dome, revolved from half its
# cross section
outside = Rectangle(49, 48 - 8, align=(Align.CENTER, Align.MIN))
outside += Rectangle(9, 48, align=(Align.CENTER, Align.MIN))
outside += Pos(9 / 2, 40) * Ellipse(20, 8)
outside = split(outside, bisect_by=Plane.YZ)
post_cap = revolve(Plane.XZ * outside, axis=Axis.Z)

# The handle: an ellipse swept along an arc
handle_path = Plane.XZ * CenterArc((-15, 40 / 2), 17, 90, 180)
handle_section = Plane.YZ.offset(-15) * Pos(0, 40 / 2 - 17) * Ellipse(10 / 2, 4 / 2)
post_cap += sweep(handle_section, path=handle_path)

# Round the two edges where the handle meets the body
post_cap = fillet(
    post_cap.edges().filter_by(GeomType.CIRCLE, reverse=True).group_by(Axis.X)[0], 1
)

# The inside: a tapered hole, with the wall leaning in at 4 degrees
wall = PolarLine((42 / 2, 0), 37, 94, length_mode=LengthMode.VERTICAL)
inside = make_face([wall, Polyline(wall @ 1, (0, (wall @ 1).Y), (0, 0), wall @ 0)])
inside = fillet(inside.vertices().group_by(Axis.X)[1], 3)
post_cap -= revolve(Plane.XZ * inside, axis=Axis.Z)

part = post_cap
part.material = abs_(density=1020)  # 1020 kg/m^3, as on the drawing

show(part)

got_mass = part.mass()
want_mass = 43.09
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} g")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
