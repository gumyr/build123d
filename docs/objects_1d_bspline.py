from build123d import *

# from ocp_vscode import show_all

dot = Circle(0.05)

control_points = [(0, 0), (1, 2), (3, 2), (4, 0), (5, 1)]
knots = [0.0, 0.0, 0.0, 0.0, 1.0, 2.0, 2.0, 2.0, 2.0]
spline = BSpline(control_points, knots, degree=3)

s = 100 / max(*spline.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(spline)
for p in control_points:
    svg.add_shape(Pos(*p) * dot.scale(1))
svg.write("assets/example_bspline.svg")
# show_all()
