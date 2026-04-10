# [Setup]
from build123d import *
from math import atan2, degrees
from ocp_vscode import *

dot = Circle(0.05)

e_dir = Vector(0.2, 1)
with BuildLine() as arcs:
    a = EllipticalStartArc((1, 1), (0, 1), 3, 1, e_dir, 160)
    d = PolarLine(a.arc_center, 0.5, direction=e_dir)


print(a.arc_center)
s = 100 / max(*arcs.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(Pos(1, 1) * dot.scale(1), "dashed")
svg.add_shape(PolarLine((1, 1), 0.5, 90), "dashed")
svg.add_shape(d, "dashed")
svg.add_shape(
    ArrowHead(0.2, rotation=degrees(atan2(e_dir.Y, e_dir.X))).moved(Pos(d @ 1)),
    "dashed",
)
svg.add_shape(a)
svg.write("assets/elliptical_start_arc_example.svg")


show_all()
