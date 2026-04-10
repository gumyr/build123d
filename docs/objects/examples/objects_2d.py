# [Setup]
from build123d import *
from tools.svg import write_svg, make_points, project_shapes

# [Ex. 1]
with BuildSketch() as example_1:
    Circle(1)
# [Ex. 1]
layers = {
    "visible": {"shapes": example_1.sketch},
}
write_svg("circle_example", layers)


# [Ex. 2]
with BuildSketch() as example_2:
    Ellipse(1.5, 1)
# [Ex. 2]
layers = {
    "visible": {"shapes": example_2.sketch},
}
write_svg("ellipse_example", layers)


# [Ex. 3]
with BuildSketch() as example_3:
    inner = PolarLocations(0.5, 5, 0).local_locations
    outer = PolarLocations(1.5, 5, 36).local_locations
    points = [p.position for pair in zip(inner, outer) for p in pair]
    Polygon(*points)
# [Ex. 3]
layers = {
    "visible": {"shapes": example_3.sketch},
}
write_svg("polygon_example", layers)


# [Ex. 4]
with BuildSketch() as example_4:
    Rectangle(2, 1)
# [Ex. 4]
layers = {
    "visible": {"shapes": example_4.sketch},
}
write_svg("rectangle_example", layers)


# [Ex. 5]
with BuildSketch() as example_5:
    RectangleRounded(2, 1, 0.25)
# [Ex. 5]
layers = {
    "visible": {"shapes": example_5.sketch},
}
write_svg("rectangle_rounded_example", layers)


# [Ex. 6]
with BuildSketch() as example_6:
    RegularPolygon(1, 6)
# [Ex. 6]
layers = {
    "visible": {"shapes": example_6.sketch},
}
write_svg("regular_polygon_example", layers)


# [Ex. 7]
with BuildSketch() as example_7:
    arc = Edge.make_circle(1, start_angle=0, end_angle=45)
    SlotArc(arc, 0.25)
# [Ex. 7]
layers = {
    "visible": {"shapes": example_7.sketch},
    "dashed": {"shapes": arc, "line_type": LineType.DASHED2},
}
write_svg("slot_arc_example", layers)


# [Ex. 8]
with BuildSketch() as example_8:
    c = (0, 0)
    p = (.125, 0)
    SlotCenterPoint(c, p, 0.25)
# [Ex. 8]
layers = {
    "visible": {"shapes": example_8.sketch},
    "points": {"shapes": make_points([c, p], example_8.sketch, fraction=10)}
}
write_svg("slot_center_point_example", layers)


# [Ex. 9]
with BuildSketch() as example_9:
    SlotCenterToCenter(.25, 0.25)
# [Ex. 9]
l1 = Curve(Line((0, .05), (0, -.05)).edges() + Line((.05, 0), (-.05, 0)).edges())
layers = {
    "visible": {"shapes": example_9.sketch},
    "labels": {"shapes": [Pos(-.25 / 2) * l1, Pos(.25 / 2) * l1], "line_type": LineType.DASHED2},
}
write_svg("slot_center_to_center_example", layers)


# [Ex. 10]
with BuildSketch() as example_10:
    SlotOverall(.5, 0.25)
# [Ex. 10]
l1 = Line((0, .25 / 2), (0, -.25 / 2))
layers = {
    "visible": {"shapes": example_10.sketch},
    "dashed": {"shapes": [Pos(-.25) * l1, Pos(.25) * l1], "line_type": LineType.DASHED2},
}
write_svg("slot_overall_example", layers)


# [Ex. 11]
with BuildSketch() as example_11:
    Text("text", 1)
# [Ex. 11]
layers = {
    "visible": {"shapes": example_11.sketch},
}
write_svg("text_example", layers)


# [Ex. 12]
with BuildSketch() as example_12:
    t = Trapezoid(2, 1, 80)
    with Locations((-0.6, -0.3)):
        Text("80°", 0.3, mode=Mode.SUBTRACT)
# [Ex. 12]
angle = Edge.make_circle(
        0.75,
        Plane(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[0].to_tuple()),
        start_angle=0,
        end_angle=80,
    )
layers = {
    "visible": {"shapes": example_12.sketch},
    "dashed": {"shapes": angle, "line_type": LineType.DASHED2},
}
write_svg("trapezoid_example", layers)


# [Ex. 13]
length, radius = 40.0, 60.0

with BuildSketch() as circle_with_hole:
    Circle(radius=radius)
    Rectangle(width=length, height=length, mode=Mode.SUBTRACT)
# [Ex. 13]
layers = {
    "visible": {"shapes": circle_with_hole.sketch},
}
write_svg("circle_with_hole", layers)


# [Ex. 14]
with BuildPart() as controller:
    # Create the side view of the controller
    with BuildSketch(Plane.YZ) as profile:
        with BuildLine():
            Polyline((0, 0), (0, 40), (20, 80), (40, 80), (40, 0), (0, 0))
        # Create a filled face from the perimeter drawing
        make_face()
    # Extrude to create the basis controller shape
    extrude(amount=30, both=True)
    # Round off all the edges
    fillet(controller.edges(), radius=3)
    # Hollow out the controller
    offset(amount=-1, mode=Mode.SUBTRACT)
    # Extract the face that will house the display
    display_face = (
        controller.faces()
        .filter_by(GeomType.PLANE)
        .filter_by_position(Axis.Z, 50, 70)[0]
    )
    # Create a workplane from the face
    display_workplane = Plane(
        origin=display_face.center(), x_dir=(1, 0, 0), z_dir=display_face.normal_at()
    )
    # Place the sketch directly on the controller
    with BuildSketch(display_workplane) as display:
        RectangleRounded(40, 30, 2)
        with GridLocations(45, 35, 2, 2):
            Circle(1)
    # Cut the display sketch through the controller
    extrude(amount=-1, mode=Mode.SUBTRACT)
# [Ex. 14]
layers = project_shapes(controller.part)
write_svg("controller", layers)


d = Draft(line_width=0.1)
# [Ex. 15]
with BuildSketch() as isosceles_triangle:
    t = Triangle(a=30, b=40, c=40)
    # [Ex. 15]
e1 = ExtensionLine(t.edges().sort_by(Axis.Y)[0], 6, d, label="a")
e2 = ExtensionLine(t.edges().sort_by(Axis.X)[-1], 6, d, label="b")
e3 = ExtensionLine(t.edges().sort_by(Axis.X)[0], 6, d, label="c")
a1 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[0], 5, 0, t.B)
a2 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[-1], 5, 180 - t.C, t.C)
a3 = CenterArc(t.vertices().sort_by(Axis.Y)[-1], 5, 270 - t.A / 2, t.A)
p1 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[0], 8, 0, t.B)
p2 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[-1], 8, 180 - t.C, t.C)
p3 = CenterArc(t.vertices().sort_by(Axis.Y)[-1], 8, 270 - t.A / 2, t.A)
t1 = Text("B", font_size=d.font_size).moved(Pos(p1 @ 0.5))
t2 = Text("C", font_size=d.font_size).moved(Pos(p2 @ 0.5))
t3 = Text("A", font_size=d.font_size).moved(Pos(p3 @ 0.5))

layers = {
    "visible": {"shapes": [isosceles_triangle.sketch]},
    "dashed": {"shapes": [a1, a2, a3], "line_type": LineType.ISO_DOUBLE_DASH_DOT},
    "labels": {"shapes": [t1, t2, t3, e1, e2, e3]}
}
write_svg("triangle_example", layers)


# [Align]
with BuildSketch() as align:
    with GridLocations(1, 1, 2, 2):
        Circle(0.5)
        Circle(0.49, mode=Mode.SUBTRACT)
    with GridLocations(1, 1, 1, 2):
        Circle(0.5)
        Circle(0.49, mode=Mode.SUBTRACT)
    with GridLocations(1, 1, 2, 1):
        Circle(0.5)
        Circle(0.49, mode=Mode.SUBTRACT)
    with Locations((0, 0)):
        Circle(0.5)
        Circle(0.49, mode=Mode.SUBTRACT)

    # Top Right: (MIN, MIN)
    with Locations((0.75, 0.75)):
        Text("MIN\nMIN", font_size=0.07)
    # Top Center: (CENTER, MIN)
    with Locations((0.0, 0.75 + 0.07 / 2)):
        Text("CENTER", font_size=0.07)
    with Locations((0.0, 0.75 - 0.07 / 2)):
        Text("MIN", font_size=0.07)
    # Top Left: (MAX, MIN)
    with Locations((-0.75, 0.75 + 0.07 / 2)):
        Text("MAX", font_size=0.07)
    with Locations((-0.75, 0.75 - 0.07 / 2)):
        Text("MIN", font_size=0.07)
    # Center Right: (MIN, CENTER)
    with Locations((0.75, 0.07 / 2)):
        Text("MIN", font_size=0.07)
    with Locations((0.75, -0.07 / 2)):
        Text("CENTER", font_size=0.07)
    # Center: (CENTER, CENTER)
    with Locations((0, 0)):
        Text("CENTER\nCENTER", font_size=0.07)
    # Center Left: (MAX, CENTER)
    with Locations((-0.75, 0.07 / 2)):
        Text("MAX", font_size=0.07)
    with Locations((-0.75, -0.07 / 2)):
        Text("CENTER", font_size=0.07)
    # Bottom Right: (MIN, MAX)
    with Locations((0.75, -0.75 + 0.07 / 2)):
        Text("MIN", font_size=0.07)
    with Locations((0.75, -0.75 - 0.07 / 2)):
        Text("MAX", font_size=0.07)
    # Bottom Center: (CENTER, MAX)
    with Locations((0.0, -0.75 + 0.07 / 2)):
        Text("CENTER", font_size=0.07)
    with Locations((0.0, -0.75 - 0.07 / 2)):
        Text("MAX", font_size=0.07)
    # Bottom Left: (MAx, MAX)
    with Locations((-0.75, -0.75)):
        Text("MAX\nMAX", font_size=0.07)

layers = {
    "labels": {"shapes": align.sketch, "fill_color": (0, 0, 0), "line_weight": 0},
}
write_svg("align", layers)


# [DimensionLine]
std = Draft()
with BuildSketch() as d_line:
    Rectangle(100, 100)
    c = Circle(45, mode=Mode.SUBTRACT)
d1 = DimensionLine([c.edge() @ 0, c.edge() @ 0.5], draft=std)

layers = {
    "visible": {"shapes": d_line.sketch},
    "labels": {"shapes": [d1]},
}
write_svg("d_line", layers)


# [ExtensionLine]
with BuildSketch() as e_line:
    with BuildLine():
        l1 = Polyline((20, 40), (-40, 40), (-40, -40), (20, -40))
        RadiusArc(l1 @ 0, l1 @ 1, 50)
    make_face()
    outside_curve = e_line.edges().sort_by(Axis.X)[-1]
e1 = ExtensionLine(border=e_line.edges().sort_by(Axis.X)[0], offset=10, draft=std)
e2 = ExtensionLine(border=outside_curve, offset=10, label_angle=True, draft=std)

layers = {
    "visible": {"shapes": e_line.sketch},
    "labels": {"shapes": [e1, e2]},
}
write_svg("e_line", layers)


# [TechnicalDrawing]
with BuildSketch() as tech_drawing:
    with Locations((0, 20)):
        add(e_line)
    TechnicalDrawing()

layers = {
    "labels": {"shapes": tech_drawing.sketch},
}
write_svg("tech_drawing", layers)


# [ArrowHead]
arrow_head_types = [HeadType.CURVED, HeadType.STRAIGHT, HeadType.FILLETED]
arrow_heads = [ArrowHead(50, a_type) for a_type in arrow_head_types]

shapes = []
labels = []
for i, arrow_head in enumerate(arrow_heads):
    shapes.append(arrow_head.moved(Location((0, -i * 40))))
    labels.append(Text(arrow_head_types[i].name, 5).moved(Location((-25, -i * 40))))
layers = {
    "visible": {"shapes": shapes},
    "labels": {"shapes": labels},
}
write_svg("arrow_head", layers)


# [Arrow]
arrow = Arrow(
    10, shaft_path=Edge.make_circle(100, start_angle=0, end_angle=10), shaft_width=1
)

layers = {
    "visible": {"shapes": arrow},
}
write_svg("arrow", layers)

