# [Setup]
from build123d import *
from docs.tools.svg import write_svg, make_points

dot = Circle(0.05)

with BuildLine() as parabolic_center_arc:
    ParabolicCenterArc((0, 0), 0.25, -60, 60)

layers = {
    "visible": {"shapes": parabolic_center_arc.line},
    "points": {"shapes": make_points([(0, 0)], parabolic_center_arc.line)}
}
write_svg("parabolic_center_arc_example", layers)

with BuildLine() as hyperbolic_center_arc:
    HyperbolicCenterArc((0, 0), 0.5, 1, 0, 180)

layers = {
    "visible": {"shapes": hyperbolic_center_arc.line},
    "points": {"shapes": make_points([(0, 0)], hyperbolic_center_arc.line)}
}
write_svg("hyperbolic_center_arc_example", layers)
