from build123d import *
from tcv_screenshots import save_model


def location_symbol(location: Location, scale: float = 1) -> Compound:
    return Compound.make_triad(axes_scale=scale).locate(location)

def plane_symbol(plane: Plane, scale: float = 1) -> Compound:
    triad = Compound.make_triad(axes_scale=scale)
    circle = Circle(scale * .8).edge()
    return (triad + circle).locate(plane.location)


loc = Location((0.1, 0.2, 0.3), (10, 20, 30 ))
face = loc * Rectangle(1, 2)
save_model([face, location_symbol(loc)], "location-example-01", {"axes": True, "axes0": True, "reset_camera": "dimetric"})


plane = Plane.XZ
face = plane * Rectangle(1, 2)
save_model([face, plane_symbol(plane)], "location-example-07", {"axes": True, "axes0": True, "reset_camera": "dimetric"})


loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
face = loc * Rectangle(1,2)
box = Plane(loc) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
# box = Plane(face.location) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
# box = loc * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
save_model([face, location_symbol(loc), box], "location-example-02", {"axes": True, "axes0": True, "reset_camera": "dimetric"})
from ocp_vscode import show
show([face, location_symbol(loc), box])

loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
face = loc * Rectangle(1,2)
box = Plane(loc) * Rot(Z=80) * Box(0.2, 0.2, 0.2)
save_model([face, location_symbol(loc), box], "location-example-03", {"axes": True, "axes0": True, "reset_camera": "dimetric"})


loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
face = loc * Rectangle(1,2)
box = loc * Rot(20, 40, 80) * Box(0.2, 0.2, 0.2)
save_model([face, location_symbol(loc), box], "location-example-04", {"axes": True, "axes0": True, "reset_camera": "dimetric"})


loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
face = loc * Rectangle(1, 2)
box = loc * Rot(20, 40, 80) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
local_loc = location_symbol(loc * Rot(20, 40, 80), 0.5)
local_loc.color = (0, 1, 1)
save_model([face, location_symbol(loc), box, local_loc], "location-example-05", {"axes": True, "axes0": True, "reset_camera": "dimetric"})


loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
face = loc * Rectangle(1,2)
box = loc * Pos(0.2, 0.4, 0.1) * Rot(20, 40, 80) * Box(0.2, 0.2, 0.2)
local_loc = location_symbol(loc * Pos(0.2, 0.4, 0.1), 0.5)
local_loc.color = (0, 1, 1)
save_model([face, location_symbol(loc), box, local_loc], "location-example-06", {"axes": True, "axes0": True, "reset_camera": "dimetric"})