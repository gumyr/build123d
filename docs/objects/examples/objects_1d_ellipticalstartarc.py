# [Setup]
from build123d import *
from math import atan2, degrees
from tools.svg import write_svg, make_points

e_dir = Vector(0.2, 1)
with BuildLine() as arcs:
    a = EllipticalStartArc((1, 1), (0, 1), 3, 1, 160, major_axis_dir=e_dir)
    d = PolarLine(a.arc_center, 1, direction=e_dir)

layers = {
    "visible": {"shapes": a},
    "dashed": {"shapes": [PolarLine((1, 1), 1, 90), d, ArrowHead(0.2, rotation=degrees(atan2(e_dir.Y, e_dir.X))).moved(Pos(d @ 1))], "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([(1, 1)], a)}
}
write_svg("elliptical_start_arc_example", layers)