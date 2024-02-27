# [Setup]
from build123d import *
from ocp_vscode import *

dot = Circle(0.05)

# [Ex. 1]
with BuildLine() as example_1:
    Line((0, 0), (2, 0))
    ThreePointArc((0, 0), (1, 1), (2, 0))
# [Ex. 1]
s = 100 / max(*example_1.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_1.line)
svg.write("assets/buildline_example_1.svg")
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
s = 100 / max(*example_5.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(example_5.line)
svg.add_shape(dot.moved(Location(l1 @ 1)))
svg.add_shape(dot.moved(Location(l2 @ 1)))
svg.add_shape(dot.moved(Location(l3 @ 1)))
svg.add_shape(PolarLine(l2 @ 1, 0.5, direction=l2 % 1), "dashed")
svg.write("assets/buildline_example_5.svg")
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
s = 100 / max(*example_6.sketch.bounding_box().size)
svg = ExportSVG(scale=s, margin=5)
svg.add_shape(example_6.sketch)
svg.write("assets/buildline_example_6.svg")

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
visible, hidden = example_7.part.project_to_viewport((100, -50, 100))
s = 100 / max(*Compound(children=visible + hidden).bounding_box().size)
exporter = ExportSVG(scale=s)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
exporter.add_shape(visible, layer="Visible")
exporter.add_shape(hidden, layer="Hidden")
exporter.write("assets/buildline_example_7.svg")
# [Ex. 8]
with BuildLine(Plane.YZ) as example_8:
    l1 = Line((0, 0), (5, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
    l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
    l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
# [Ex. 8]
scene = Compound(example_8.line) + Compound.make_triad(2)
visible, _hidden = scene.project_to_viewport((100, -50, 100))
s = 100 / max(*Compound(children=visible + hidden).bounding_box().size)
exporter = ExportSVG(scale=s)
exporter.add_layer("Visible")
exporter.add_shape(visible, layer="Visible")
exporter.write("assets/buildline_example_8.svg")


pts = [(0, 0), (2 / 3, 2 / 3), (0, 4 / 3), (-4 / 3, 0), (0, -2), (4, 0), (0, 3)]
wts = [1.0, 1.0, 2.0, 3.0, 4.0, 2.0, 1.0]
with BuildLine() as bezier_curve:
    Bezier(*pts, weights=wts)

s = 100 / max(*bezier_curve.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(bezier_curve.line)
for pt in pts:
    svg.add_shape(dot.moved(Location(Vector(pt))))
svg.write("assets/bezier_curve_example.svg")

with BuildLine() as center_arc:
    CenterArc((0, 0), 3, 0, 90)
s = 100 / max(*center_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(center_arc.line)
svg.add_shape(dot.moved(Location(Vector((0, 0)))))
svg.write("assets/center_arc_example.svg")

with BuildLine() as elliptical_center_arc:
    EllipticalCenterArc((0, 0), 2, 3, 0, 90)
s = 100 / max(*elliptical_center_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(elliptical_center_arc.line)
svg.add_shape(dot.moved(Location(Vector((0, 0)))))
svg.write("assets/elliptical_center_arc_example.svg")

with BuildLine() as helix:
    Helix(1, 3, 1)
scene = Compound(helix.line) + Compound.make_triad(0.5)
visible, _hidden = scene.project_to_viewport((1, 1, 1))
s = 100 / max(*Compound(children=visible).bounding_box().size)
exporter = ExportSVG(scale=s)
exporter.add_layer("Visible")
exporter.add_shape(visible, layer="Visible")
exporter.write("assets/helix_example.svg")

with BuildLine() as jern_arc:
    JernArc((1, 1), (1, 0.5), 2, 100)
s = 100 / max(*jern_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(jern_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(PolarLine((1, 1), 0.5, direction=(1, 0.5)), "dashed")
svg.write("assets/jern_arc_example.svg")

with BuildLine() as line:
    Line((1, 1), (3, 3))
s = 100 / max(*line.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(line.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/line_example.svg")

with BuildLine() as polar_line:
    PolarLine((1, 1), 2.5, 60)
s = 100 / max(*polar_line.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(polar_line.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(PolarLine((1, 1), 4, angle=60), "dashed")
svg.write("assets/polar_line_example.svg")

with BuildLine() as polyline:
    Polyline((1, 1), (1.5, 2.5), (3, 3))
s = 100 / max(*polyline.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(polyline.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((1.5, 2.5)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/polyline_example.svg")

with BuildLine(Plane.YZ) as filletpolyline:
    FilletPolyline((0, 0, 0), (0, 10, 2), (0, 10, 10), (5, 20, 10), radius=2)
show(filletpolyline)
scene = Compound(filletpolyline.line) + Compound.make_triad(2)
visible, _hidden = scene.project_to_viewport((0, 0, 1), (0, 1, 0))
s = 100 / max(*Compound(children=visible).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(visible)
svg.write("assets/filletpolyline_example.svg")

with BuildLine() as radius_arc:
    RadiusArc((1, 1), (3, 3), 2)
s = 100 / max(*radius_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(radius_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/radius_arc_example.svg")

with BuildLine() as sagitta_arc:
    SagittaArc((1, 1), (3, 1), 1)
s = 100 / max(*sagitta_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(sagitta_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 1)))))
svg.write("assets/sagitta_arc_example.svg")

with BuildLine() as spline:
    Spline((1, 1), (2, 1.5), (1, 2), (2, 2.5), (1, 3))
s = 100 / max(*spline.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(spline.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((2, 1.5)))))
svg.add_shape(dot.moved(Location(Vector((1, 2)))))
svg.add_shape(dot.moved(Location(Vector((2, 2.5)))))
svg.add_shape(dot.moved(Location(Vector((1, 3)))))
svg.write("assets/spline_example.svg")

with BuildLine() as tangent_arc:
    TangentArc((1, 1), (3, 3), tangent=(1, 0))
s = 100 / max(*tangent_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(tangent_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.add_shape(PolarLine((1, 1), 1, direction=(1, 0)), "dashed")
svg.write("assets/tangent_arc_example.svg")

with BuildLine() as three_point_arc:
    ThreePointArc((1, 1), (1.5, 2), (3, 3))
s = 100 / max(*three_point_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(three_point_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((1.5, 2)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/three_point_arc_example.svg")

with BuildLine() as intersecting_line:
    other = Line((2, 0), (2, 2), mode=Mode.PRIVATE)
    IntersectingLine((1, 0), (1, 1), other)
s = 100 / max(*intersecting_line.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(other, "dashed")
svg.add_shape(intersecting_line.line)
svg.add_shape(dot.moved(Location(Vector((1, 0)))))
svg.write("assets/intersecting_line_example.svg")

with BuildLine() as double_tangent:
    l2 = JernArc(start=(0, 20), tangent=(0, 1), radius=5, arc_size=-300)
    l3 = DoubleTangentArc((6, 0), tangent=(0, 1), other=l2)
s = 100 / max(*double_tangent.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(l2, "dashed")
svg.add_shape(l3)
svg.add_shape(dot.scale(5).moved(Pos(6, 0)))
svg.add_shape(Edge.make_line((6, 0), (6, 5)), "dashed")
svg.write("assets/double_tangent_line_example.svg")

# show_object(example_1.line, name="Ex. 1")
# show_object(example_2.line, name="Ex. 2")
# show_object(example_3.line, name="Ex. 3")
# show_object(example_4.line, name="Ex. 4")
# show_object(example_5.line, name="Ex. 5")
# show_object(example_6.line, name="Ex. 6")
# show_object(example_7_path.line, name="Ex. 7 path")
# show_object(example_8.line, name="Ex. 8")
