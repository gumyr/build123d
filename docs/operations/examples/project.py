from build123d import *
from ocp_vscode import *
from tcv_screenshots import save_model

sphere = Sphere(5)
text = Rot(90) * Text("Flat #1", 2.5)
projection = [t.project_to_shape(sphere, (0, -1)) for t in text.faces()]
save_model([sphere, text, projection], "project_to_shape", {"alphas": [.2, .5]})


cyl = Plane.XZ.shift_origin((0, 0, 9)) * Cylinder(10, 15)
path = split(sphere, cyl.faces().filter_by(GeomType.CYLINDER)[0]).edges().sort_by(SortBy.LENGTH)[-1]
text = Text("project_faces - The quick brown fox jumped over the lazy dog", 1.15)
projection = sphere.project_faces(text, Rot(Z=-90) * path)
save_model([sphere, text, projection], "project_faces", {"alphas": [.2, .5]})
