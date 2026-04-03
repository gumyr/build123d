# [Setup]
from build123d import *
from ocp_vscode import *
from tools.svg import write_svg, make_points, project_shapes

dot = Circle(0.05)

# [Ex. 1]
with BuildLine() as example_1:
    Line((0, 0), (2, 0))
    ThreePointArc((0, 0), (1, 1), (2, 0))
# [Ex. 1]
layers = {
    "visible": {"shapes": example_1.line},
}
write_svg("buildline_example_1", layers)
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
layers = {
    "visible": {"shapes": example_5.line},
    "dashed": {"shapes": PolarLine(l2 @ 1, 0.5, direction=l2 % 1), "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([l1 @ 1, l2 @ 1, l3 @ 1], example_5.line)}
}
write_svg("buildline_example_5", layers)

# [Ex. 6]
with BuildSketch() as example_6:
    with BuildLine() as club_outline:
        l0 = Line((0, -188), (76, -188))
        b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
        b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
        b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
        b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
        mirror(about=Plane.YZ)
    make_face()
    # [Ex. 6]
layers = {
    "visible": {"shapes": example_6.sketch},
}
write_svg("buildline_example_6", layers)

# [Ex. 7]
with BuildPart() as example_7:
    with BuildLine() as example_7_path:
        l1 = RadiusArc((0, 0), (1, 1), 2)
        l2 = Spline(l1 @ 1, (2, 3), (3, 3), tangents=(l1 % 1, (0, -1)))
        l3 = Line(l2 @ 1, (3, 0))
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as example_7_section:
        Circle(0.1)
    sweep()
# [Ex. 7]
layers = project_shapes(example_7.part)
write_svg("buildline_example_7", layers)

# [Ex. 8]
with BuildLine(Plane.YZ) as example_8:
    l1 = Line((0, 0), (5, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
    l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
    l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
# [Ex. 8]
scene = Compound(example_8.line) + Compound.make_triad(2)
layers = project_shapes(scene, show_hidden=False)
write_svg("buildline_example_8", layers)


pts = [(0, 0), (2 / 3, 2 / 3), (0, 4 / 3), (-4 / 3, 0), (0, -2), (4, 0), (0, 3)]
wts = [1.0, 1.0, 2.0, 3.0, 4.0, 2.0, 1.0]
with BuildLine() as bezier_curve:
    Bezier(*pts, weights=wts)

layers = {
    "visible": {"shapes": bezier_curve.line},
    "points": {"shapes": make_points(pts, bezier_curve.line)},
}
write_svg("bezier_curve_example", layers)


with BuildLine() as center_arc:
    CenterArc((0, 0), 3, 0, 90)

layers = {
    "visible": {"shapes": center_arc.line},
    "points": {"shapes": make_points([(0, 0)], center_arc.line)}
}
write_svg("center_arc_example", layers)


with BuildLine() as elliptical_center_arc:
    EllipticalCenterArc((0, 0), 2, 3, 0, 90)

layers = {
    "visible": {"shapes": elliptical_center_arc.line},
    "points": {"shapes": make_points([(0, 0)], elliptical_center_arc.line)}
}
write_svg("elliptical_center_arc_example", layers)


with BuildLine() as parabolic_center_arc:
    ParabolicCenterArc((0, 0), 0.5, 60, 0)

layers = {
    "visible": {"shapes": parabolic_center_arc.line},
    "points": {"shapes": make_points([(0, 0)], parabolic_center_arc.line)}
}
write_svg("parabolic_center_arc_example", layers)


with BuildLine() as hyperbolic_center_arc:
    HyperbolicCenterArc((0, 0), 0.5, 1, 45, 90)

layers = {
    "visible": {"shapes": hyperbolic_center_arc.line},
    "points": {"shapes": make_points([(0, 0)], hyperbolic_center_arc.line)}
}
write_svg("hyperbolic_center_arc_example", layers)


with BuildLine() as helix:
    Helix(1, 3, 1)

scene = Compound(helix.line) + Compound.make_triad(0.5)
layers = project_shapes(scene)
write_svg("helix_example", layers)


with BuildLine() as jern_arc:
    JernArc((1, 1), (1, 0.5), 2, 100)

layers = {
    "visible": {"shapes": jern_arc.line},
    "dashed": {"shapes": PolarLine((1, 1), 1, direction=(1, 0.5)), "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([(1, 1)], jern_arc.line)}
}
write_svg("jern_arc_example", layers)


with BuildLine() as line:
    Line((1, 1), (3, 3))

layers = {
    "visible": {"shapes": line.line},
    "points": {"shapes": make_points([(1, 1), (3, 3)], line.line)}
}
write_svg("line_example", layers)


with BuildLine() as polar_line:
    PolarLine((1, 1), 2.5, 60)

layers = {
    "visible": {"shapes": polar_line.line},
    "dashed": {"shapes": PolarLine((1, 1), 4, angle=60), "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([(1, 1)], polar_line.line)}
}
write_svg("polar_line_example", layers)


with BuildLine() as polyline:
    Polyline((1, 1), (1.5, 2.5), (3, 3))

layers = {
    "visible": {"shapes": polyline.line},
    "points": {"shapes": make_points([(1, 1), (1.5, 2.5), (3, 3)], polyline.line)}
}
write_svg("polyline_example", layers)

with BuildLine(Plane.YZ) as filletpolyline:
    FilletPolyline((0, 0, 0), (0, 10, 2), (0, 10, 10), (5, 20, 10), radius=2)

scene = Compound(filletpolyline.line) + Compound.make_triad(2)
layers = project_shapes(scene)
write_svg("filletpolyline_example", layers)


with BuildLine() as radius_arc:
    RadiusArc((1, 1), (3, 3), 2)

layers = {
    "visible": {"shapes": radius_arc.line},
    "points": {"shapes": make_points([(1, 1), (3, 3)], radius_arc.line)}
}
write_svg("radius_arc_example", layers)


with BuildLine() as sagitta_arc:
    SagittaArc((1, 1), (3, 1), 1)

layers = {
    "visible": {"shapes": sagitta_arc.line},
    "points": {"shapes": make_points([(1, 1), (3, 1)], sagitta_arc.line)}
}
write_svg("sagitta_arc_example", layers)


with BuildLine() as spline:
    Spline((1, 1), (2, 1.5), (1, 2), (2, 2.5), (1, 3))

layers = {
    "visible": {"shapes": spline.line},
    "points": {"shapes": make_points([(1, 1), (2, 1.5), (1, 2), (2, 2.5), (1, 3)], spline.line)}
}
write_svg("spline_example", layers)


with BuildLine() as tangent_arc:
    TangentArc((1, 1), (3, 3), tangent=(1, 0))

layers = {
    "visible": {"shapes": tangent_arc.line},
    "dashed": {"shapes": PolarLine((1, 1), 1, direction=(1, 0)), "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([(1, 1), (3, 3)], tangent_arc.line)}
}
write_svg("tangent_arc_example", layers)


with BuildLine() as three_point_arc:
    ThreePointArc((1, 1), (1.5, 2), (3, 3))

layers = {
    "visible": {"shapes": three_point_arc.line},
    "points": {"shapes": make_points([(1, 1), (1.5, 2), (3, 3)], three_point_arc.line)}
}
write_svg("three_point_arc_example", layers)


with BuildLine() as intersecting_line:
    other = Line((2, 0), (2, 2), mode=Mode.PRIVATE)
    IntersectingLine((1, 0), (1, 1), other)

layers = {
    "visible": {"shapes": intersecting_line.line},
    "dashed": {"shapes": other, "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([(1, 0)], [intersecting_line.line, other])}
}
write_svg("intersecting_line_example", layers)


with BuildLine() as double_tangent:
    p1 = (6, 0)
    d1 = (0, 1)
    l2 = Spline((0, 10), (3, 8), (7, 7), (10, 10))
    l3 = DoubleTangentArc(p1, tangent=d1, other=l2)

layers = {
    "visible": {"shapes": l3},
    "dashed": {"shapes": [PolarLine(p1, 1, direction=d1), l2], "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([p1], l3)}
}
write_svg("double_tangent_line_example", layers)


with BuildLine() as point_arc_tangent_line:
    p1 = (10, 3)
    l1 = CenterArc((0, 5), 5, -90, 180)
    l2 = PointArcTangentLine(p1, l1, Side.RIGHT)

layers = {
    "visible": {"shapes": l2},
    "dashed": {"shapes": l1, "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([p1], [l1, l2])}
}
write_svg("example_point_arc_tangent_line", layers)


with BuildLine() as point_arc_tangent_arc:
    p1 = (10, 3)
    d1 = (-3, 1)
    l1 = CenterArc((0, 5), 5, -90, 180)
    l2 = PointArcTangentArc(p1, d1, l1, Side.RIGHT)

layers = {
    "visible": {"shapes": l2},
    "dashed": {"shapes": l1, "line_type": LineType.DASHED2},
    "points": {"shapes": make_points([p1], [l1, l2])}
}
write_svg("example_point_arc_tangent_arc", layers)


with BuildLine() as arc_arc_tangent_line:
    l1 = CenterArc((7, 3), 3, 0, 360)
    l2 = CenterArc((0, 8), 2, -90, 180)
    l3 = ArcArcTangentLine(l1, l2, Side.RIGHT, Keep.OUTSIDE)

layers = {
    "visible": {"shapes": l3},
    "dashed": {"shapes": [l1, l2], "line_type": LineType.DASHED2},
}
write_svg("example_arc_arc_tangent_line", layers)


with BuildLine() as arc_arc_tangent_arc:
    l1 = CenterArc((7, 3), 3, 0, 360)
    l2 = CenterArc((0, 8), 2, -90, 180)
    radius = 12
    l3 = ArcArcTangentArc(l1, l2, radius, Side.LEFT, (Keep.INSIDE, Keep.OUTSIDE))

layers = {
    "visible": {"shapes": l3},
    "dashed": {"shapes": [l1, l2], "line_type": LineType.DASHED2},
}
write_svg("example_arc_arc_tangent_arc", layers)


with BuildLine() as airfoil:
    Airfoil(2142)

layers = {
    "visible": {"shapes": airfoil.line},
}
write_svg("example_airfoil", layers)
