import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "assets", "topology_selection")

with BuildPart() as part:
    Box(5, 5, 1)
    Cylinder(2, 5)
    edges = part.edges().filter_by(lambda a: a.length == 1)
    fillet(edges, 1)

box = Box(5, 5, 5).move(Location((-6, -6)))
sphere = Sphere(5 / 2).move(Location((6, 6)))
solids = ShapeList([part.part, box, sphere])

part.wires().sort_by(Wire.length)[:4]
part.wires().group_by(Wire.length)[0]

part.vertices().sort_by_distance((0, 0, 0))[-2:]
part.vertices().group_by(Vertex(0, 0, 0).distance_to)[-1]


show(part, part.wires().sort_by(Wire.length)[:4])
save_screenshot(os.path.join(filedir, "sort_edge_length.png"))

# show(part, part.faces().sort_by(Face.area)[-2:])
# save_screenshot(os.path.join(filedir, "sort_face_area.png"))

# solid = solids.sort_by(Solid.volume)[-1]
# solid.color = "violet"
# show([part, box, sphere], solid)
# save_screenshot(os.path.join(filedir, "sort_solid_volume.png"))

# show(part, part.edges().filter_by(GeomType.CIRCLE).sort_by(Edge.radius)[-4:])
# save_screenshot(os.path.join(filedir, "sort_edge_radius.png"))

show(part, part.vertices().sort_by_distance((0, 0, 0))[-2:])
save_screenshot(os.path.join(filedir, "sort_by_distance.png"))
