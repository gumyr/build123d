# [Setup]
from build123d import *
from tools.svg import write_svg
# from ocp_vscode import *

dot = Circle(0.05)

with BuildLine() as arcs:
    c1 = CenterArc((4, 0), 2, 0, 360)
    c2 = CenterArc((0, 2), 1.5, 0, 360)
    a1 = ConstrainedArcs(c1, c2, radius=6)

layers = {
    "visible": {"shapes": a1},
    "dashed": {"shapes": [c1,c2], "line_type": LineType.DASHED2},
}
write_svg("constrained_arcs_example", layers)

with BuildLine() as lines:
    c1 = CenterArc((4, 0), 2, 0, 360)
    c2 = CenterArc((0, 2), 1.5, 0, 360)
    l1 = ConstrainedLines(c1, c2)

layers = {
    "visible": {"shapes": l1},
    "dashed": {"shapes": [c1,c2], "line_type": LineType.DASHED2},
}
write_svg("constrained_lines_example", layers)

# show_all()
