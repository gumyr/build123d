from build123d import *

# from ocp_vscode import show_all, set_defaults, Camera

# set_defaults(reset_camera=Camera.KEEP)

with BuildLine() as blend_curve:
    l1 = CenterArc((0, 0), 5, 135, -135)
    l2 = Spline((0, -5), (-3, -8), (0, -11))
    l3 = BlendCurve(l1, l2, tangent_scalars=(2, 5))
s = 100 / max(*blend_curve.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(l1, "dashed")
svg.add_shape(l2, "dashed")
svg.add_shape(l3)
svg.write("assets/example_blend_curve.svg")
# show_all()
