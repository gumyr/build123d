import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

with BuildPart() as part:
    Box(5, 5, 1)
    Cylinder(2, 5)
    edges = part.edges().filter_by(lambda a: a.length == 1)
    fillet(edges, 1)

part.edges().filter_by(GeomType.LINE)

part.faces().filter_by(GeomType.CYLINDER)

show(part, part.edges().filter_by(GeomType.LINE))
save_screenshot(os.path.join(filedir, "filter_geomtype_line.png"))

show(part, part.faces().filter_by(GeomType.CYLINDER))
save_screenshot(os.path.join(filedir, "filter_geomtype_cylinder.png"))