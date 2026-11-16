from build123d import *
from build123d.exporters import ColorIndex
from ocp_vscode import show_all

# 2D Axes
axes2 = Compound.make_triad(2).edges().group_by(Axis.Z)[0]


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
svg.write("assets/constraints/tangent_circles.svg")

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
svg.write("assets/constraints/tan2_rad_ex.svg")

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
svg.write("assets/constraints/tan2_on_ex.svg")

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
svg.write("assets/constraints/tan3_ex.svg")

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
svg.write("assets/constraints/pnt_center_ex.svg")

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
svg.write("assets/constraints/tan_rad_on_ex.svg")

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
svg.write("assets/constraints/lines_tan2_ex.svg")


pnt_line = CenterArc((1, 1), 0.05, 0, 360)
lines_tan_pnt = ConstrainedLines(a1, pnt_line.arc_center).edges()

s = 50 / max(*Curve([pnt_line, a1] + lines_tan_pnt + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(lines_tan_pnt)
svg.add_shape(pnt_line)
svg.add_shape([a1], "dashed")
svg.write("assets/constraints/lines_tan_pnt_ex.svg")

y_axis = Line((0, 0), (0, 2.5))
lines_angle = ConstrainedLines(a2, Axis.Y, angle=55).edges()

s = 50 / max(*Curve([y_axis, a2] + lines_angle + axes2).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(axes2)
svg.add_shape(lines_angle)
svg.add_shape([y_axis, a2], "dashed")
svg.write("assets/constraints/lines_angle_ex.svg")

show_all()
