from build123d import *
from build123d.exporters import ColorIndex
from ocp_vscode import show, show_all, ImageFace

# 2D Axes
axes2 = Compound.make_triad(2).edges().group_by(Axis.Z)[0]


#
# BlendCurve
#
m1 = CenterArc((-2, 0.6), 1, -10, 200).reversed()
m2 = Spline((0.4, -0.6), (1, -1.6), (2, 0))
connector = BlendCurve(m1, m2, tangent_scalars=(2, 1), continuity=ContinuityLevel.C2)
comb = Curve(Wire([m1, connector, m2]).curvature_comb(200))

s = 120 / max(*Curve(axes2 + [m1, m2]).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("m1", line_color=(214, 40, 40), line_type=LineType.ISO_DASH_SPACE)
svg.add_layer("m2", line_color=(252, 191, 73), line_type=LineType.ISO_DASH_SPACE)
svg.add_layer("connector", line_color=(247, 127, 0))
svg.add_layer("comb", line_color=(172, 172, 172))
svg.add_shape(axes2)
svg.add_shape(m1, "m1")
svg.add_shape(m2, "m2")
svg.add_shape(connector, "connector")
svg.add_shape(comb, "comb")
svg.write("assets/blend_curve_ex.svg")


#
# Coincident
#
with BuildLine() as coincident_ex:
    l1 = Line((0, 0), (1, 2))
    l2 = Line(l1 @ 1, l1 @ 1 + (1, 0))

s = 50 / max(*Curve(axes2 + coincident_ex.edges()).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(l1, "dashed")
svg.add_shape(l2)
svg.write("assets/coincident_ex.svg")

#
# Tangent
#
with BuildLine() as tangent_ex:
    l1 = Line((0, 0), (1, 1))
    l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=1, arc_size=70)

s = 50 / max(*Curve(axes2 + tangent_ex.edges()).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(l1, "dashed")
svg.add_shape(l2)
svg.write("assets/tangent_ex.svg")

#
# Perpendicular
#
with BuildLine() as perpendicular_ex:
    l1 = CenterArc((0, 0), 1.5, 0, 45)
    l2 = PolarLine(
        start=l1 @ 1, length=1, direction=l1.tangent_at(1).rotate(Axis.Z, -90)
    )

s = 50 / max(*Curve(axes2 + perpendicular_ex.edges()).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(l1, "dashed")
svg.add_shape(l2)
svg.write("assets/perpendicular_ex.svg")

#
# Intersection
#
with BuildLine() as intersect_ex:
    c_l1 = EllipticalCenterArc((0, 0), 1.2, 1.8, 0, 90, mode=Mode.PRIVATE)
    l1 = IntersectingLine(
        start=(0, 0), direction=Vector(1, 0).rotate(Axis.Z, 10), other=c_l1
    )
    l2 = IntersectingLine(
        start=(0, 0), direction=Vector(1, 0).rotate(Axis.Z, 80), other=c_l1
    )
    l3 = add(c_l1.trim(l1 @ 1, l2 @ 1))

s = 50 / max(*Curve(axes2 + intersect_ex.edges()).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(c_l1, "dashed")
svg.add_shape(l1)
svg.add_shape(l2)
svg.add_shape(l3)
svg.write("assets/intersect_ex.svg")

#
# Offset
#
inside = FilletPolyline((1.5, 0), (1.5, 1), (-1.5, 1), (-1.5, 0), radius=0.2)
inside.color = "Grey"
perimeter = offset(inside, amount=0.2, side=Side.RIGHT)

s = 100 / max(*Curve(axes2 + [inside, perimeter]).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(perimeter)
svg.add_shape(inside, "dashed")
svg.write("assets/offset_ex.svg")

#
# Tangency Outside/Enclosing
#
with BuildLine() as egg_plant:
    # Construction Geometry
    c_l1 = CenterArc((-2, 0), 0.75, 80, 240, mode=Mode.PRIVATE)
    c_l4 = CenterArc((2, 0), 1, 220, 250, mode=Mode.PRIVATE)

    # egg_plant perimeter
    l1 = ConstrainedArcs((c_l4, Tangency.OUTSIDE), (c_l1, Tangency.OUTSIDE), radius=6)
    l2 = ConstrainedArcs(
        (c_l4, Tangency.ENCLOSING),
        (c_l1, Tangency.ENCLOSING),
        radius=8,
        selector=lambda a: a.sort_by(Axis.Y)[-1],
    )
    l3 = add(c_l1.trim(l1 @ 1, l2 @ 1))
    l5 = add(c_l4.trim(l1 @ 0, l2 @ 0))

s = 100 / max(*Curve(axes2 + egg_plant.edges()).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape([l1, l2, l3, l5])
svg.add_shape([c_l1, c_l4], "dashed")
svg.write("assets/enclosing_ex.svg")

#
# Complex Sketch
#
image = ImageFace(
    "assets/complex_sketch.png",
    scale=29 / 264,
    origin_pixels=(297, 390),
    location=Location((0, 0, -0.1)),
)
axes5 = Compound.make_triad(5).edges().group_by(Axis.Z)[0]

with BuildSketch() as sketch:
    with BuildLine() as perimeter:
        c_l1 = PolarLine((0, 32 - 14), 50, -10, mode=Mode.PRIVATE)
        a19 = ConstrainedArcs(c_l1, (-14 + 81 - 29, -14 - 19 + 57), radius=19)
        l2 = Polyline(a19 @ 1, a19 @ 1 + (29 - 5, 0), a19 @ 1 + (29, -5), (-14 + 81, 0))
        l3 = Line(l2 @ 1, (-14 + 81 - 29, (-14 - 19)))
        c_l4 = Line((-14, -14), (-14 + 81, -14), mode=Mode.PRIVATE)
        c_a29_arc_center = l3.intersect(c_l4)[0]
        c_a29 = CenterArc(c_a29_arc_center, 29, 180, 50, mode=Mode.PRIVATE)
        l5 = IntersectingLine(l3 @ 1, (-1, 0), c_a29)
        a5 = ConstrainedArcs(
            c_a29, c_l4, radius=5, selector=lambda a: a.sort_by(Axis.X)[0]
        )
        a29 = add(c_a29.trim(l5 @ 1, a5 @ 0))
        l6 = Polyline(
            a5 @ 1,
            (-14 + 7, -14),
            (-14, -14 + 7),
            (-14, -14 + 32 - 7),
            (-14 + 7, -14 + 32),
            (0, -14 + 32),
            a19 @ 0,
        )
    make_face()
    a14 = Circle(14 / 2, mode=Mode.SUBTRACT)

s = 150 / max(*Curve(axes5 + perimeter.edges()).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes5)
svg.add_shape(perimeter.edges() + [a14.edge()])
svg.add_shape([c_l1, c_l4, c_a29], "dashed")
svg.write("assets/complex_ex.svg")

#
# Tangent Circles
#
a1 = CenterArc((-7, 0), 10, 0, 360)
a2 = CenterArc((7, 0), 10, 0, 360)
tangents = ConstrainedArcs(a1, a2, radius=2).edges()
tangent_circles = [CenterArc(e.arc_center, 2, 0, 360) for e in tangents]

s = 100 / max(*Curve([a1, a2] + tangent_circles).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(tangent_circles)
svg.add_shape([a1, a2], "dashed")
svg.write("assets/tangent_circles.svg")

#
# ConstrainedArcs - two constraints & radius
#
e1 = Line((0, 1), (2, 1))
e2 = Line((1, 0), (1, 2))
tan2_rad_edges = ConstrainedArcs(e1, e2, radius=0.75).edges()

s = 50 / max(*Curve([e1, e2] + axes2 + tan2_rad_edges).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(tan2_rad_edges)
svg.add_shape([e1, e2], "dashed")
svg.write("assets/tan2_rad_ex.svg")

#
# ConstrainedArcs - two constraints & center-on
#
# c1 = PolarLine((0, 0), 4, -20, length_mode=LengthMode.HORIZONTAL)
c1 = PolarLine((0, 0), 2, 40, length_mode=LengthMode.HORIZONTAL)
c2 = Line((1.8, 0), (1.8, 2))
c3_center_on = Line((1, -0.5), (1, 2.5))
tan2_on_edge = ConstrainedArcs(
    c1, c2, center_on=c3_center_on, sagitta=Sagitta.BOTH
).edges()

s = 50 / max(*Curve([c1, c2, c3_center_on] + axes2 + tan2_on_edge).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(tan2_on_edge)
svg.add_shape([c1, c2, c3_center_on], "dashed")
svg.write("assets/tan2_on_ex.svg")

#
# ConstrainedArcs - three constraints
#
c5 = PolarLine((0, 0), 1.8, 60)
c6 = PolarLine((0, 0), 1.8, 40)
c7 = CenterArc((0, 0), 1.8, 0, 90)
tan3 = ConstrainedArcs(c5, c6, c7).edge()

s = 50 / max(*Curve([c5, c6, c7, tan3] + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(tan3)
svg.add_shape([c5, c6, c7], "dashed")
svg.write("assets/tan3_ex.svg")

#
# ConstrainedArcs - one constraint + center
#
pnt = CenterArc((1.5, 1.5), 0.05, 0, 360)
center_pnt = CenterArc((1, 1), 0.05, 0, 360)
pnt_center = ConstrainedArcs(pnt.arc_center, center=center_pnt.arc_center).edge()

s = 50 / max(*Curve([pnt, center_pnt, pnt_center] + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(axes2)
svg.add_shape([pnt, center_pnt, pnt_center])
svg.write("assets/pnt_center_ex.svg")

#
# ConstrainedArcs - One constraint + radius + center_on
#
tan_rad_on = ConstrainedArcs(c1, radius=0.5, center_on=c3_center_on).edges()

s = 50 / max(*Curve([c1, c3_center_on] + tan_rad_on + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(tan_rad_on)
svg.add_shape([c1, c3_center_on], "dashed")
svg.write("assets/tan_rad_on_ex.svg")

#
# ConstrainedLines - two constraints
#
a1 = CenterArc((-1, 1), 1, 0, 360)
a2 = CenterArc((1, 1), 0.5, 0, 360)
l1 = Line((0, 0), (2, 2))
lines_tan2_ex = ConstrainedLines(a1, a2).edges()

s = 50 / max(*Curve([a1, a1] + lines_tan2_ex + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(lines_tan2_ex)
svg.add_shape([a1, a2], "dashed")
svg.write("assets/lines_tan2_ex.svg")


pnt_line = CenterArc((1, 1), 0.05, 0, 360)
lines_tan_pnt = ConstrainedLines(a1, pnt_line.arc_center).edges()

s = 50 / max(*Curve([pnt_line, a1] + lines_tan_pnt + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(lines_tan_pnt)
svg.add_shape(pnt_line)
svg.add_shape([a1], "dashed")
svg.write("assets/lines_tan_pnt_ex.svg")

y_axis = Line((0, 0), (0, 2.5))
lines_angle = ConstrainedLines(a2, Axis.Y, angle=55).edges()

s = 50 / max(*Curve([y_axis, a2] + lines_angle + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(lines_angle)
svg.add_shape([y_axis, a2], "dashed")
svg.write("assets/lines_angle_ex.svg")

show_all()
