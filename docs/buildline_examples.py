# [Setup]
from build123d import *

# [Setup]
svg_opts1 = {"pixel_scale": 100, "show_axes": False, "show_hidden": False}
svg_opts2 = {"pixel_scale": 50, "show_axes": True, "show_hidden": False}

# [Ex. 1]
with BuildLine() as example_1:
    Line((0, 0), (2, 0))
    ThreePointArc((0, 0), (1, 1), (2, 0))
# [Ex. 1]
example_1.line.export_svg(
    "assets/buildline_example_1.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)
# [Ex. 2]
with BuildLine() as example_2:
    l1 = Line((0, 0), (2, 0))
    l2 = ThreePointArc(l1 @ 0, (1, 1), l1 @ 1)
# [Ex. 2]

# [Ex. 3]
with BuildLine() as example_3:
    l1 = Line((0, 0), (2, 0))
    l2 = ThreePointArc(l1 @ 0, l1 @ 0.5 + (0, 1), l1 @ 1)
# [Ex. 3]

# [Ex. 4]
with BuildLine() as example_4:
    l1 = Line((0, 0), (2, 0))
    l2 = ThreePointArc(l1 @ 0, l1 @ 0.5 + (0, l1.length / 2), l1 @ 1)
# [Ex. 4]

# [Ex. 5]
with BuildLine() as example_5:
    l1 = Line((0, 0), (5, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
    l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
    l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
# [Ex. 5]
example_5.line.export_svg(
    "assets/buildline_example_5.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts2
)


# [Ex. 6]
with BuildSketch() as example_6:
    with BuildLine() as club_outline:
        l0 = Line((0, -188), (76, -188))
        b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
        b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
        b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
        b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
        Mirror(about=Plane.YZ)
    MakeFace()
    # [Ex. 6]
    Scale(by=2 / example_6.sketch.bounding_box().size.Y)
example_6.sketch.export_svg(
    "assets/buildline_example_6.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 7]
with BuildPart() as example_7:
    with BuildLine() as example_7_path:
        l1 = RadiusArc((0, 0), (1, 1), 2)
        l2 = Spline(l1 @ 1, (2, 3), (3, 3), tangents=(l1 % 1, (0, -1)))
        l3 = Line(l2 @ 1, (3, 0))
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as example_7_section:
        Circle(0.1)
    Sweep()
# [Ex. 7]
example_7.part.export_svg(
    "assets/buildline_example_7.svg", (100, -50, 100), (0, 0, 1), svg_opts=svg_opts1
)

# [Ex. 8]
with BuildLine(Plane.YZ) as example_8:
    l1 = Line((0, 0), (5, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
    l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
    l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
# [Ex. 8]
example_8.line.export_svg(
    "assets/buildline_example_8.svg", (100, -50, 100), (0, 0, 1), svg_opts=svg_opts2
)

pts = [(0, 0), (2 / 3, 2 / 3), (0, 4 / 3), (-4 / 3, 0), (0, -2), (4, 0), (0, 3)]
wts = [1.0, 1.0, 2.0, 3.0, 4.0, 2.0, 1.0]
with BuildLine() as bezier_curve:
    Bezier(*pts, weights=wts)
bezier_curve.line.export_svg(
    "assets/bezier_curve_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as center_arc:
    CenterArc((0, 0), 3, 0, 90)
center_arc.line.export_svg(
    "assets/center_arc_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as elliptical_center_arc:
    EllipticalCenterArc((0, 0), 2, 3, 0, 90)
elliptical_center_arc.line.export_svg(
    "assets/elliptical_center_arc_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as helix:
    Helix(1, 3, 1)
helix.line.export_svg(
    "assets/helix_example.svg", (1, -1, 1), (0, 0, 1), svg_opts=svg_opts2
)

with BuildLine() as jern_arc:
    JernArc((1, 1), (1, 0.5), 2, 100)
jern_arc.line.export_svg(
    "assets/jern_arc_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as line:
    Line((1, 1), (3, 3))
line.line.export_svg(
    "assets/line_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as polar_line:
    PolarLine((1, 1), 2.5, 60)
polar_line.line.export_svg(
    "assets/polar_line_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as polyline:
    Polyline((1, 1), (1.5, 2.5), (3, 3))
polyline.line.export_svg(
    "assets/polyline_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as radius_arc:
    RadiusArc((1, 1), (3, 3), 2)
radius_arc.line.export_svg(
    "assets/radius_arc_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as sagitta_arc:
    SagittaArc((1, 1), (3, 1), 1)
sagitta_arc.line.export_svg(
    "assets/sagitta_arc_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as spline:
    Spline((1, 1), (2, 1.5), (1, 2), (2, 2.5), (1, 3))
spline.line.export_svg(
    "assets/spline_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as tangent_arc:
    TangentArc((1, 1), (3, 3), tangent=(1, 0))
tangent_arc.line.export_svg(
    "assets/tangent_arc_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

with BuildLine() as three_point_arc:
    ThreePointArc((1, 1), (1.5, 2), (3, 3))
three_point_arc.line.export_svg(
    "assets/three_point_arc_example.svg", (0, 0, 1), (0, 1, 0), svg_opts=svg_opts2
)

if "show_object" in locals():
    # show_object(example_1.line, name="Ex. 1")
    # show_object(example_2.line, name="Ex. 2")
    # show_object(example_3.line, name="Ex. 3")
    # show_object(example_4.line, name="Ex. 4")
    # show_object(example_5.line, name="Ex. 5")
    # show_object(example_6.line, name="Ex. 6")
    show_object(example_8_path.line, name="Ex. 8 path")
    show_object(example_8.part, name="Ex. 8")
