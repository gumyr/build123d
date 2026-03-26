import importlib
from tcv_screenshots import save_model
from build123d import Color, Compound, Rot

import key_cap
import toy_truck
ttt230202 = importlib.import_module("ttt-23-02-02-sm_hanger")

key_cap.key_cap.part.color = Color("goldenrod", .3)
save_model([key_cap.key_cap.part], "key_cap")
save_model([Rot(15, 0, -120) * Compound([toy_truck.body.part, toy_truck.cab.part], color=toy_truck.truck_color)], "toy_truck", {"reset_camera": "front", "render_edges": False})
save_model([ttt230202.sm_hanger], "ttt-23-02-02-sm_hanger")
