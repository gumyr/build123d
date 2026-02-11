# [Setup]
from build123d import *

# from ocp_vscode import *

dot = Circle(0.05)

with BuildLine() as parabolic_center_arc:
    ParabolicCenterArc((0, 0), 0.25, -60, 60)
s = 100 / max(*parabolic_center_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(parabolic_center_arc.line)
svg.add_shape(dot.moved(Location(Vector((0, 0)))))
svg.write("assets/parabolic_center_arc_example.svg")

with BuildLine() as hyperbolic_center_arc:
    HyperbolicCenterArc((0, 0), 0.5, 1, 0, 180)
s = 100 / max(*hyperbolic_center_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(hyperbolic_center_arc.line)
svg.add_shape(dot.moved(Location(Vector((0, 0)))))
svg.write("assets/hyperbolic_center_arc_example.svg")

# show_all()
