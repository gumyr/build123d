# [Setup]
from build123d import *
from ocp_vscode import *

dot = Circle(0.05)

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
svg.write("../how_to/assets/build_line/buildline_example_6.svg")


pts = [(0, 0), (2 / 3, 2 / 3), (0, 4 / 3), (-4 / 3, 0), (0, -2), (4, 0), (0, 3)]
wts = [1.0, 1.0, 2.0, 3.0, 4.0, 2.0, 1.0]
with BuildLine() as bezier_curve:
    Bezier(*pts, weights=wts)

s = 100 / max(*bezier_curve.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(bezier_curve.line)
for pt in pts:
    svg.add_shape(dot.moved(Location(Vector(pt))))
svg.write("assets/objects/bezier_curve_example.svg")

with BuildLine() as center_arc:
    CenterArc((0, 0), 3, 0, 90)
s = 100 / max(*center_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(center_arc.line)
svg.add_shape(dot.moved(Location(Vector((0, 0)))))
svg.write("assets/objects/center_arc_example.svg")

with BuildLine() as elliptical_center_arc:
    EllipticalCenterArc((0, 0), 2, 3, 0, arc_size=90)
s = 100 / max(*elliptical_center_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(elliptical_center_arc.line)
svg.add_shape(dot.moved(Location(Vector((0, 0)))))
svg.write("assets/objects/elliptical_center_arc_example.svg")


with BuildLine() as helix:
    Helix(1, 3, 1)
scene = Compound(helix.line) + Compound.make_triad(0.5)
visible, _hidden = scene.drawing_view((1, 1, 1))
s = 100 / max(*Compound(children=visible).bounding_box().size)
exporter = ExportSVG(scale=s)
exporter.add_layer("Visible")
exporter.add_shape(visible, layer="Visible")
exporter.write("assets/objects/helix_example.svg")

with BuildLine() as jern_arc:
    JernArc((1, 1), (1, 0.5), 2, 100)
s = 100 / max(*jern_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(jern_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(PolarLine((1, 1), 0.5, direction=(1, 0.5)), "dashed")
svg.write("assets/objects/jern_arc_example.svg")

with BuildLine() as line:
    Line((1, 1), (3, 3))
s = 100 / max(*line.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(line.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/objects/line_example.svg")

with BuildLine() as polar_line:
    PolarLine((1, 1), 2.5, 60)
s = 100 / max(*polar_line.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(polar_line.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(PolarLine((1, 1), 4, angle=60), "dashed")
svg.write("assets/objects/polar_line_example.svg")

with BuildLine() as polyline:
    Polyline((1, 1), (1.5, 2.5), (3, 3))
s = 100 / max(*polyline.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(polyline.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((1.5, 2.5)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/objects/polyline_example.svg")

with BuildLine(Plane.YZ) as filletpolyline:
    FilletPolyline((0, 0, 0), (0, 10, 2), (0, 10, 10), (5, 20, 10), radius=2)
scene = Compound(filletpolyline.line) + Compound.make_triad(2)
visible, _hidden = scene.drawing_view((0, 0, 1), (0, 1, 0))
s = 100 / max(*Compound(children=visible).bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(visible)
svg.write("assets/objects/filletpolyline_example.svg")

with BuildLine() as radius_arc:
    RadiusArc((1, 1), (3, 3), 2)
s = 100 / max(*radius_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(radius_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/objects/radius_arc_example.svg")

with BuildLine() as sagitta_arc:
    SagittaArc((1, 1), (3, 1), 1)
s = 100 / max(*sagitta_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(sagitta_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 1)))))
svg.write("assets/objects/sagitta_arc_example.svg")

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
svg.write("assets/objects/spline_example.svg")

with BuildLine() as tangent_arc:
    TangentArc((1, 1), (3, 3), tangent=(1, 0))
s = 100 / max(*tangent_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(tangent_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.add_shape(PolarLine((1, 1), 1, direction=(1, 0)), "dashed")
svg.write("assets/objects/tangent_arc_example.svg")

with BuildLine() as three_point_arc:
    ThreePointArc((1, 1), (1.5, 2), (3, 3))
s = 100 / max(*three_point_arc.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(three_point_arc.line)
svg.add_shape(dot.moved(Location(Vector((1, 1)))))
svg.add_shape(dot.moved(Location(Vector((1.5, 2)))))
svg.add_shape(dot.moved(Location(Vector((3, 3)))))
svg.write("assets/objects/three_point_arc_example.svg")

with BuildLine() as intersecting_line:
    other = Line((2, 0), (2, 2), mode=Mode.PRIVATE)
    IntersectingLine((1, 0), (1, 1), other)
s = 100 / max(*intersecting_line.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(other, "dashed")
svg.add_shape(intersecting_line.line)
svg.add_shape(dot.moved(Location(Vector((1, 0)))))
svg.write("assets/objects/intersecting_line_example.svg")

with BuildLine() as double_tangent:
    p1 = (6, 0)
    d1 = (0, 1)
    l2 = Spline((0, 10), (3, 8), (7, 7), (10, 10))
    show_object([p1, l2])
    l3 = DoubleTangentArc(p1, tangent=d1, other=l2)
s = 100 / max(*double_tangent.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.ISO_DASH_SPACE)
svg.add_shape(l2, "dashed")
svg.add_shape(l3)
svg.add_shape(dot.scale(5).moved(Pos(p1)))
svg.add_shape(PolarLine(p1, 1, direction=d1), "dashed")
svg.write("assets/objects/double_tangent_line_example.svg")
