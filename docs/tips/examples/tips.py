from build123d import *
from tcv_screenshots import save_model

from tools.svg import write_svg, project_shapes

with BuildSketch(Plane.XZ) as vertical_sketch:
    Rectangle(1, 1)
    with Locations(vertices().group_by(Axis.X)[-1].sort_by(Axis.Z)[-1]):
        Circle(0.2)

with BuildSketch(Plane.YZ.rotated((123, 45, 6))) as custom_plane:
    Rectangle(1, 1, align=Align.MIN)
    with Locations(vertices().group_by(Axis.X)[-1].sort_by(Axis.Y)[-1]):
        Circle(0.2)

save_model(vertical_sketch.sketch, "vertical_sketch", {"axes": True, "axes0": True,})
save_model(custom_plane, "sketch_on_custom_plane", {"axes": True, "axes0": True,})

length, width, thickness = 80.0, 60.0, 10.0
hole_dia = 6.0

with BuildPart() as plate:
    Box(length, width, thickness)
    with GridLocations(length - 20, width - 20, 2, 2):
        Hole(radius=hole_dia / 2)
    top_face: Face = plate.faces().sort_by(Axis.Z)[-1]
    hole_edges = top_face.edges().filter_by(GeomType.CIRCLE)
    chamfer(hole_edges, length=1)

write_svg("plate", project_shapes(plate.part))
