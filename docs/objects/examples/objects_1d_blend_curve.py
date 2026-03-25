from build123d import *
from tools.svg import write_svg

with BuildLine() as blend_curve:
    l1 = CenterArc((0, 0), 5, 135, -135)
    l2 = Spline((0, -5), (-3, -8), (0, -11))
    l3 = BlendCurve(l1, l2, tangent_scalars=(2, 5))

layers = {
    "visible": {"shapes": l3},
    "dashed": {"shapes": [l1, l2], "line_type": LineType.DASHED2}
}
write_svg("example_blend_curve", layers)
