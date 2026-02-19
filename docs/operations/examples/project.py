from build123d import *
from ocp_vscode import *
from tcv_screenshots import save_model

sphere = Sphere(5)
text = Rot(90) * Text("Text", 2.5)
projection = [t.project_to_shape(sphere, (0, -1)) for t in text.faces()]
sphere.color = Color("goldenrod", .2)
text.color = Color("violet", .5)
save_model([sphere, text, projection], "project_to_shape", {"alphas": [.2, .5]})


cyl = Plane.XZ.shift_origin((0, 0, 9)) * Cylinder(10, 15)
path = split(sphere, cyl.faces().filter_by(GeomType.CYLINDER)[0]).edges().sort_by(SortBy.LENGTH)[-1]
text = Text("project_faces - The quick brown fox jumped over the lazy dog", 1.15)
projection = sphere.project_faces(text, Rot(Z=-90) * path)
sphere.color = Color("goldenrod", .2)
save_model([sphere, projection], "project_faces", {"alphas": [.2]})

n, h = 6, 10
cyl = Rot(Z=180) * Cylinder(5, h)
surface = cyl.faces().filter_by(GeomType.CYLINDER)[0]
path = Pos(Z=5) * surface.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[0]
w = path.length / n / 4
slot = ShapeList(GridLocations(2 * w, 0, n, 1) * SlotOverall(h - 2, w, rotation=90))
wrap = surface.wrap_faces(slot.faces(), path, .5)
surface_holes = surface.make_holes(wrap.wires())
save_model(surface_holes, "slotted_cylinder")
