from build123d import *
from tcv_screenshots import save_model

# setup-builder
with BuildPart() as part:
    Box(5, 5, 1)
    Cylinder(2, 5)
    edges = part.edges().filter_by(lambda a: a.length == 1)
    fillet(edges, 1)
# setup-builder-end

box = Box(5, 5, 5).move(Location((-6, -6)))
sphere = Sphere(5 / 2).move(Location((6, 6)))
solids = ShapeList([part.part, box, sphere])

# length-builder
part.wires().sort_by(SortBy.LENGTH)[:4]

# alternatively
part.wires().sort_by(Wire.length)[:4]
part.wires().group_by(SortBy.LENGTH)[0]
# length-builder-end

# distance-builder
part.vertices().sort_by(SortBy.DISTANCE)[-2:]

# alternatively
part.vertices().sort_by_distance(Vertex())[-2:]
part.vertices().group_by(Vertex().distance)[-1]
# distance-builder-end

save_model([part, *part.wires().sort_by(SortBy.LENGTH)[:4]], "sort_sortby_length")
save_model([part, *part.vertices().sort_by(SortBy.DISTANCE)[-2:]], "sort_sortby_distance")