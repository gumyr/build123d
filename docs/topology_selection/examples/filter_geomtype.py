from build123d import *
from tcv_screenshots import save_model


with BuildPart() as part:
    Box(5, 5, 1)
    Cylinder(2, 5)
    edges = part.edges().filter_by(lambda a: a.length == 1)
    fillet(edges, 1)

part.edges().filter_by(GeomType.LINE)

part.faces().filter_by(GeomType.CYLINDER)

save_model([part, *part.edges().filter_by(GeomType.LINE)], "filter_geomtype_line")
save_model([part, *part.faces().filter_by(GeomType.CYLINDER)], "filter_geomtype_cylinder")