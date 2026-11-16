"""
Too Tall Toby 24-SPO-06 Buffer Stand
"""

from build123d import *
from bd_materials.materials.metals import mild_steel
from ocp_vscode import show

# The plan: a block with one side bowed out
bow = ThreePointArc((5 / 2, -1.25), (5.5 / 2, 0), (5 / 2, 1.25))
plan = make_face([bow, Polyline(bow @ 0, (0, -1.25), (0, 1.25), bow @ 1)])
stand = extrude(plan, amount=4)

# The end view: sides leaning in at 6 degrees to a fully rounded top
end_view = Trapezoid(2.5, 4, 90 - 6, align=(Align.CENTER, Align.MIN))
end_view = full_round(end_view.edges().sort_by(Edge.length)[0])
top_arc = end_view.edges().filter_by(GeomType.CIRCLE)[0]
arc_center = top_arc.arc_center
arc_radius = top_arc.radius
stand &= extrude(Plane.YZ * end_view, amount=10)

# What is removed from inside. To avoid OCCT problems, the top arc is not
# extended; the material beside it is removed instead.
top = stand.edges().filter_by(Axis.X).sort_by(Axis.Z)[-1].center().Z
shoulders = Trapezoid(2.5, top, 90 - 6, align=(Align.CENTER, Align.MIN))
shoulders -= Pos(arc_center) * Circle(arc_radius)
internals = extrude(Plane.YZ.offset(4.25 / 2) * shoulders, amount=-(4.25 - 3.5) / 2)
cavity = Trapezoid(2.5, 4, 90 - 6, align=(Align.CENTER, Align.MIN))
internals += extrude(Plane.YZ.offset(3.5 / 2) * cavity, amount=-3.5 / 2)
side_view = Pos(0, 4) * RectangleRounded(4.25, 7.5, 0.5)
internals &= extrude(Plane.XZ.offset(-2) * side_view, amount=4)
stand -= internals

# The mounting hole, in the highest flat face of the part
seat = stand.faces().filter_by(GeomType.PLANE).sort_by(Axis.Z)[-1]
stand -= Plane(seat) * CounterBoreHole(0.625 / 2, 1.25 / 2, 0.5, depth=1)

# The rib
rib = Pos(0, 0.25) * Trapezoid(0.5, 1, 90 - 8, align=(Align.CENTER, Align.MIN))
rib = full_round(rib.edges().sort_by(Edge.length)[0])
stand += extrude(Plane.YZ * rib, amount=4.25 / 2)

# The other half
stand += mirror(stand, about=Plane.YZ)

# The model is drawn in inches, as the drawing is dimensioned
part = scale(stand, IN)
part.material = mild_steel()  # 7800 kg/m^3, as on the drawing

show(part)

got_mass = part.mass(Unit.LB)
want_mass = 3.923
tolerance = 0.02
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.2f} lbs")
assert delta < tolerance, f"{got_mass=}, {want_mass=}, {delta=}, {tolerance=}"
