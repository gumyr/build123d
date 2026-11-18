# [Code]
from build123d import *
from ocp_viewer import show

A, A1, Db2, H, J = 26, 11, 57, 98.5, 76.5

housing = Circle(Db2 / 2)
bolt_centers = GridLocations(J, 0, 2, 1)
plan = make_hull((housing + bolt_centers * Circle((H - J) / 2)).edges())

oval_flanged_bearing_unit = extrude(plan, A1) + extrude(housing, A)
drafted_faces = oval_flanged_bearing_unit.faces().filter_by(Axis.Z, reverse=True)
oval_flanged_bearing_unit = draft(drafted_faces, Plane.XY, 4)
oval_flanged_bearing_unit = fillet(oval_flanged_bearing_unit.edges(), 1)

top = oval_flanged_bearing_unit.faces().sort_by(Axis.Z)[-1]
oval_flanged_bearing_unit -= Plane(top) * CounterBoreHole(14 / 2, 47 / 2, 14, depth=A)
oval_flanged_bearing_unit -= bolt_centers * Hole(5, depth=A1)

oval_flanged_bearing_unit.color = Color(0x4C6377)

show(oval_flanged_bearing_unit)
# [End]
