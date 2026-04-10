from build123d import *
from tools.svg import write_svg

# 2D Axes
axes2 = Compound.make_triad(2).edges().group_by(Axis.Z)[0]

#
# BlendCurve
#
m1 = CenterArc((-2, 0.6), 1, -10, 200).reversed()
m2 = Spline((0.4, -0.6), (1, -1.6), (2, 0))
connector = BlendCurve(m1, m2, tangent_scalars=(2, 1), continuity=ContinuityLevel.C2)
comb = Curve(Wire([m1, connector, m2]).curvature_comb(200))

layers = {
    "axes2": {"shapes": axes2},
    "connector": {"shapes": connector, "line_color": (247, 127, 0)},
    "comb": {"shapes": comb, "line_color": (172, 172, 172)},
    "m1": {"shapes": m1, "line_type": LineType.DASHED, "line_color": (214, 40, 40)},
    "m2": {"shapes": m2, "line_type": LineType.DASHED, "line_color": (252, 191, 73)},
}
write_svg("blend_curve_ex", layers)

#
# Coincident
#
with BuildLine() as coincident_ex:
    l1 = Line((0, 0), (1, 2))
    l2 = Line(l1 @ 1, l1 @ 1 + (1, 0))

layers = {
    "normal": {"shapes": [*axes2, l2]},
    "dashed": {"shapes": [l1], "line_type": LineType.DASHED},
}
write_svg("coincident_ex", layers)

#
# Tangent
#
with BuildLine() as tangent_ex:
    l1 = Line((0, 0), (1, 1))
    l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=1, arc_size=70)

layers = {
    "normal": {"shapes": [*axes2, l2]},
    "dashed": {"shapes": [l1], "line_type": LineType.DASHED},
}
write_svg("tangent_ex", layers)

#
# Perpendicular
#
with BuildLine() as perpendicular_ex:
    l1 = CenterArc((0, 0), 1.5, 0, 45)
    l2 = PolarLine(
        start=l1 @ 1, length=1, direction=l1.tangent_at(1).rotate(Axis.Z, -90)
    )

layers = {
    "normal": {"shapes": [*axes2, l2]},
    "dashed": {"shapes": [l1], "line_type": LineType.DASHED},
}
write_svg("perpendicular_ex", layers)

#
# Intersection
#
with BuildLine() as intersect_ex:
    c_l1 = EllipticalCenterArc((0, 0), 1.2, 1.8, 0, arc_size=90, mode=Mode.PRIVATE)
    l1 = IntersectingLine(
        start=(0, 0), direction=Vector(1, 0).rotate(Axis.Z, 10), other=c_l1
    )
    l2 = IntersectingLine(
        start=(0, 0), direction=Vector(1, 0).rotate(Axis.Z, 80), other=c_l1
    )
    l3 = add(c_l1.trim(l1 @ 1, l2 @ 1))

layers = {
    "normal": {"shapes": [*axes2, l1, l2, l3]},
    "dashed": {"shapes": [c_l1], "line_type": LineType.DASHED},
}
write_svg("intersect_ex", layers)

#
# Offset
#
inside = FilletPolyline((1.5, 0), (1.5, 1), (-1.5, 1), (-1.5, 0), radius=0.2)
inside.color = "Grey"
perimeter = offset(inside, amount=0.2, side=Side.RIGHT) - inside

layers = {
    "normal": {"shapes": [*axes2, perimeter]},
    "dashed": {"shapes": [inside], "line_type": LineType.DASHED},
}
write_svg("offset_ex", layers)

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

layers = {
    "normal": {"shapes": [*axes2, l1, l2, l3, l5]},
    "dashed": {"shapes": [c_l1, c_l4], "line_type": LineType.DASHED},
}
write_svg("enclosing_ex", layers)

#
# Complex Sketch
#
# image = ImageFace(
#     "complex_sketch.png",
#     scale=29 / 264,
#     origin_pixels=(297, 390),
#     location=Location((0, 0, -0.1)),
# )
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

layers = {
    "normal": {"shapes": axes5 + perimeter.edges() + [a14.edge()]},
    "dashed": {"shapes": [c_l1, c_l4, c_a29], "line_type": LineType.DASHED},
}
write_svg("complex_ex", layers)

#
# Tangent Circles
#
a1 = CenterArc((-7, 0), 10, 0, 360)
a2 = CenterArc((7, 0), 10, 0, 360)
tangents = ConstrainedArcs(a1, a2, radius=2).edges()
tangent_circles = [CenterArc(e.arc_center, 2, 0, 360) for e in tangents]

layers = {
    "normal": {"shapes": tangent_circles},
    "dashed": {"shapes": [a1, a2], "line_type": LineType.DASHED},
}
write_svg("tangent_circles", layers)

#
# ConstrainedArcs - two constraints & radius
#
e1 = Line((0, 1), (2, 1))
e2 = Line((1, 0), (1, 2))
tan2_rad_edges = ConstrainedArcs(e1, e2, radius=0.75).edges()

layers = {
    "normal": {"shapes": axes2 + tan2_rad_edges},
    "dashed": {"shapes": [e1, e2], "line_type": LineType.DASHED},
}
write_svg("tan2_rad_ex", layers)

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

layers = {
    "normal": {"shapes": axes2 + tan2_on_edge},
    "dashed": {"shapes": [c1, c2, c3_center_on], "line_type": LineType.DASHED},
}
write_svg("tan2_on_ex", layers)

#
# ConstrainedArcs - three constraints
#
c5 = PolarLine((0, 0), 1.8, 60)
c6 = PolarLine((0, 0), 1.8, 40)
c7 = CenterArc((0, 0), 1.8, 0, 90)
tan3 = ConstrainedArcs(c5, c6, c7).edge()

layers = {
    "normal": {"shapes": axes2 + tan3},
    "dashed": {"shapes": [c5, c6, c7], "line_type": LineType.DASHED},
}
write_svg("tan3_ex", layers)

#
# ConstrainedArcs - one constraint + center
#
pnt = CenterArc((1.5, 1.5), 0.05, 0, 360)
center_pnt = CenterArc((1, 1), 0.05, 0, 360)
pnt_center = ConstrainedArcs(pnt.arc_center, center=center_pnt.arc_center).edge()

layers = {
    "normal": {"shapes": [*axes2, pnt, center_pnt, pnt_center]},
}
write_svg("pnt_center_ex", layers)

#
# ConstrainedArcs - One constraint + radius + center_on
#
tan_rad_on = ConstrainedArcs(c1, radius=0.5, center_on=c3_center_on).edges()

layers = {
    "normal": {"shapes": axes2 + tan_rad_on},
    "dashed": {"shapes": [c1, c3_center_on], "line_type": LineType.DASHED},
}
write_svg("tan_rad_on_ex", layers)

#
# ConstrainedLines - two constraints
#
a1 = CenterArc((-1, 1), 1, 0, 360)
a2 = CenterArc((1, 1), 0.5, 0, 360)
l1 = Line((0, 0), (2, 2))
lines_tan2_ex = ConstrainedLines(a1, a2).edges()

layers = {
    "normal": {"shapes": axes2 + lines_tan2_ex},
    "dashed": {"shapes": [a1, a2], "line_type": LineType.DASHED},
}
write_svg("lines_tan2_ex", layers)


pnt_line = CenterArc((1, 1), 0.05, 0, 360)
lines_tan_pnt = ConstrainedLines(a1, pnt_line.arc_center).edges()

layers = {
    "normal": {"shapes": axes2 + lines_tan_pnt + [pnt_line]},
    "dashed": {"shapes": [a1], "line_type": LineType.DASHED},
}
write_svg("lines_tan_pnt_ex", layers)

y_axis = Line((0, 0), (0, 2.5))
lines_angle = ConstrainedLines(a2, Axis.Y, angle=55).edges()

layers = {
    "normal": {"shapes": axes2 + lines_angle},
    "dashed": {"shapes": [y_axis, a2], "line_type": LineType.DASHED},
}
write_svg("lines_angle_ex", layers)
