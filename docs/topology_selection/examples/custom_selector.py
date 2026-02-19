from build123d import *
from tcv_screenshots import save_model

obj = Box(1, 1, 1) - Cylinder(0.2, 1)
faces_with_holes = obj.faces().filter_by(lambda f: f.inner_wires())

obj.color = Color("goldenrod", .5)
faces_with_holes.color = Color("violet", .5)
save_model([obj, faces_with_holes], "custom_selector", {"alphas": [.5, .5], "axes": True, "axes0": True, "reset_camera": "dimetric"})