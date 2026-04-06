# [Setup]
from build123d import *

# from ocp_vscode import *

dot = Circle(0.05)

with BuildLine() as arcs:
    c1 = CenterArc((4, 0), 2, 0, 360)
    c2 = CenterArc((0, 2), 1.5, 0, 360)
    a1 = ConstrainedArcs(c1, c2, radius=6)

s = 100 / max(*arcs.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(c1, "dashed")
svg.add_shape(c2, "dashed")
svg.add_shape(a1)
svg.write("assets/constrained_arcs_example.svg")


with BuildLine() as lines:
    c1 = CenterArc((4, 0), 2, 0, 360)
    c2 = CenterArc((0, 2), 1.5, 0, 360)
    l1 = ConstrainedLines(c1, c2)

s = 100 / max(*lines.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(c1, "dashed")
svg.add_shape(c2, "dashed")
svg.add_shape(l1)
svg.write("assets/constrained_lines_example.svg")

# show_all()
