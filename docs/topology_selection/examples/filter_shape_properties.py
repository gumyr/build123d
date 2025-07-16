import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

with BuildPart() as open_box_builder:
    Box(20, 20, 5)
    offset(amount=-2, openings=open_box_builder.faces().sort_by(Axis.Z)[-1])
    inside_edges = open_box_builder.edges().filter_by(Edge.is_interior)
    fillet(inside_edges, 1.5)
    outside_edges = open_box_builder.edges().filter_by(Edge.is_interior, reverse=True)
    fillet(outside_edges, 0.5)

open_box = open_box_builder.part
open_box.color = Color(0xEDAE49)
outside_fillets = Compound(open_box.faces().filter_by(Face.is_circular_convex))
outside_fillets.color = Color(0xD1495B)
inside_fillets = Compound(open_box.faces().filter_by(Face.is_circular_concave))
inside_fillets.color = Color(0x00798C)

show(open_box, inside_fillets, outside_fillets)
save_screenshot(os.path.join(filedir, "filter_shape_properties.png"))