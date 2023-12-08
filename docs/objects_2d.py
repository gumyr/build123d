# [Setup]
from build123d import *

dot = Circle(0.05)

# [Setup]
svg_opts1 = {"pixel_scale": 100, "show_axes": False, "show_hidden": False}
svg_opts2 = {"pixel_scale": 300, "show_axes": True, "show_hidden": False}
svg_opts3 = {"pixel_scale": 2, "show_axes": False, "show_hidden": False}
svg_opts4 = {"pixel_scale": 5, "show_axes": False, "show_hidden": False}

# [Ex. 1]
with BuildSketch() as example_1:
    Circle(1)
# [Ex. 1]
s = 100 / max(*example_1.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_1.sketch)
svg.write("assets/circle_example.svg")

# [Ex. 2]
with BuildSketch() as example_2:
    Ellipse(1.5, 1)
# [Ex. 2]
s = 100 / max(*example_2.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_2.sketch)
svg.write("assets/ellipse_example.svg")

# [Ex. 3]
with BuildSketch() as example_3:
    inner = PolarLocations(0.5, 5, 0).local_locations
    outer = PolarLocations(1.5, 5, 36).local_locations
    points = [p.position for pair in zip(inner, outer) for p in pair]
    Polygon(*points)
# [Ex. 3]
s = 100 / max(*example_3.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_3.sketch)
svg.write("assets/polygon_example.svg")

# [Ex. 4]
with BuildSketch() as example_4:
    Rectangle(2, 1)
# [Ex. 4]
s = 100 / max(*example_4.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_4.sketch)
svg.write("assets/rectangle_example.svg")

# [Ex. 5]
with BuildSketch() as example_5:
    RectangleRounded(2, 1, 0.25)
# [Ex. 5]
s = 100 / max(*example_5.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_5.sketch)
svg.write("assets/rectangle_rounded_example.svg")

# [Ex. 6]
with BuildSketch() as example_6:
    RegularPolygon(1, 6)
# [Ex. 6]
s = 100 / max(*example_6.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_6.sketch)
svg.write("assets/regular_polygon_example.svg")

# [Ex. 7]
with BuildSketch() as example_7:
    arc = Edge.make_circle(1, start_angle=0, end_angle=45)
    SlotArc(arc, 0.25)
# [Ex. 7]
s = 100 / max(*example_7.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.DASHED)
svg.add_shape(example_7.sketch)
svg.add_shape(arc, "dashed")
svg.write("assets/slot_arc_example.svg")

# [Ex. 8]
with BuildSketch() as example_8:
    c = (0, 0)
    p = (0, 1)
    SlotCenterPoint(c, p, 0.25)
# [Ex. 8]
s = 100 / max(*example_8.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.DASHED)
svg.add_shape(example_8.sketch)
svg.add_shape(dot.moved(Location(c)), "dashed")
svg.add_shape(dot.moved(Location(p)), "dashed")
svg.write("assets/slot_center_point_example.svg")

# [Ex. 9]
with BuildSketch() as example_9:
    SlotCenterToCenter(1, 0.25, rotation=90)
# [Ex. 9]
s = 100 / max(*example_9.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_9.sketch)
svg.write("assets/slot_center_to_center_example.svg")

# [Ex. 10]
with BuildSketch() as example_10:
    SlotOverall(1, 0.25)
# [Ex. 10]
s = 100 / max(*example_10.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_10.sketch)
svg.write("assets/slot_overall_example.svg")

# [Ex. 11]
with BuildSketch() as example_11:
    Text("text", 1)
# [Ex. 11]
s = 100 / max(*example_11.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(example_11.sketch)
svg.write("assets/text_example.svg")

# [Ex. 12]
with BuildSketch() as example_12:
    t = Trapezoid(2, 1, 80)
    with Locations((-0.6, -0.3)):
        Text("80°", 0.3, mode=Mode.SUBTRACT)
# [Ex. 12]
s = 100 / max(*example_12.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.DASHED)
svg.add_shape(
    Edge.make_circle(
        0.75,
        Plane(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[0].to_tuple()),
        start_angle=0,
        end_angle=80,
    ),
    "dashed",
)
svg.add_shape(example_12.sketch)
svg.write("assets/trapezoid_example.svg")

# [Ex. 13]
length, radius = 40.0, 60.0

with BuildSketch() as circle_with_hole:
    Circle(radius=radius)
    Rectangle(width=length, height=length, mode=Mode.SUBTRACT)
# [Ex. 13]
s = 100 / max(*circle_with_hole.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(circle_with_hole.sketch)
svg.write("assets/circle_with_hole.svg")

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
visible, hidden = controller.part.project_to_viewport((70, -50, 120))
max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
exporter = ExportSVG(scale=100 / max_dimension)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
exporter.add_shape(visible, layer="Visible")
exporter.add_shape(hidden, layer="Hidden")
exporter.write(f"assets/controller.svg")

d = Draft(line_width=0.1)
# [Ex. 15]
with BuildSketch() as isosceles_triangle:
    t = Triangle(a=30, b=40, c=40)
    # [Ex. 15]
    ExtensionLine(t.edges().sort_by(Axis.Y)[0], 6, d, label="a")
    ExtensionLine(t.edges().sort_by(Axis.X)[-1], 6, d, label="b")
    ExtensionLine(t.edges().sort_by(SortBy.LENGTH)[-1], 6, d, label="c")
a1 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[0], 5, 0, t.B)
a2 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[-1], 5, 180 - t.C, t.C)
a3 = CenterArc(t.vertices().sort_by(Axis.Y)[-1], 5, 270 - t.A / 2, t.A)
p1 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[0], 8, 0, t.B)
p2 = CenterArc(t.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[-1], 8, 180 - t.C, t.C)
p3 = CenterArc(t.vertices().sort_by(Axis.Y)[-1], 8, 270 - t.A / 2, t.A)
t1 = Text("B", font_size=d.font_size).moved(Pos(p1 @ 0.5))
t2 = Text("C", font_size=d.font_size).moved(Pos(p2 @ 0.5))
t3 = Text("A", font_size=d.font_size).moved(Pos(p3 @ 0.5))

s = 100 / max(*isosceles_triangle.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_layer("dashed", line_type=LineType.DASHED)
svg.add_shape([a1, a2, a3], "dashed")
svg.add_shape(isosceles_triangle.sketch)
svg.add_shape([t1, t2, t3])
svg.write("assets/triangle_example.svg")


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
        Text("MIN\nMIN", font="FreeSerif", font_size=0.07)
    # Top Center: (CENTER, MIN)
    with Locations((0.0, 0.75 + 0.07 / 2)):
        Text("CENTER", font="FreeSerif", font_size=0.07)
    with Locations((0.0, 0.75 - 0.07 / 2)):
        Text("MIN", font="FreeSerif", font_size=0.07)
    # Top Left: (MAX, MIN)
    with Locations((-0.75, 0.75 + 0.07 / 2)):
        Text("MAX", font="FreeSerif", font_size=0.07)
    with Locations((-0.75, 0.75 - 0.07 / 2)):
        Text("MIN", font="FreeSerif", font_size=0.07)
    # Center Right: (MIN, CENTER)
    with Locations((0.75, 0.07 / 2)):
        Text("MIN", font="FreeSerif", font_size=0.07)
    with Locations((0.75, -0.07 / 2)):
        Text("CENTER", font="FreeSerif", font_size=0.07)
    # Center: (CENTER, CENTER)
    with Locations((0, 0)):
        Text("CENTER\nCENTER", font="FreeSerif", font_size=0.07)
    # Center Left: (MAX, CENTER)
    with Locations((-0.75, 0.07 / 2)):
        Text("MAX", font="FreeSerif", font_size=0.07)
    with Locations((-0.75, -0.07 / 2)):
        Text("CENTER", font="FreeSerif", font_size=0.07)
    # Bottom Right: (MIN, MAX)
    with Locations((0.75, -0.75 + 0.07 / 2)):
        Text("MIN", font="FreeSerif", font_size=0.07)
    with Locations((0.75, -0.75 - 0.07 / 2)):
        Text("MAX", font="FreeSerif", font_size=0.07)
    # Bottom Center: (CENTER, MAX)
    with Locations((0.0, -0.75 + 0.07 / 2)):
        Text("MAX", font="FreeSerif", font_size=0.07)
    with Locations((0.0, -0.75 - 0.07 / 2)):
        Text("CENTER", font="FreeSerif", font_size=0.07)
    # Bottom Left: (MAx, MAX)
    with Locations((-0.75, -0.75)):
        Text("MAX\nMAX", font="FreeSerif", font_size=0.07)

s = 100 / max(*align.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(align.sketch)
svg.write("assets/align.svg")

# [DimensionLine]
std = Draft()
with BuildSketch() as d_line:
    Rectangle(100, 100)
    c = Circle(45, mode=Mode.SUBTRACT)
    DimensionLine([c.edge() @ 0, c.edge() @ 0.5], draft=std)
s = 100 / max(*d_line.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(d_line.sketch)
svg.write("assets/d_line.svg")

# [ExtensionLine]
with BuildSketch() as e_line:
    with BuildLine():
        l1 = Polyline((20, 40), (-40, 40), (-40, -40), (20, -40))
        RadiusArc(l1 @ 0, l1 @ 1, 50)
    make_face()
    ExtensionLine(border=e_line.edges().sort_by(Axis.X)[0], offset=10, draft=std)
    outside_curve = e_line.edges().sort_by(Axis.X)[-1]
    ExtensionLine(border=outside_curve, offset=10, label_angle=True, draft=std)
s = 100 / max(*e_line.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(e_line.sketch)
svg.write("assets/e_line.svg")

# [TechnicalDrawing]
with BuildSketch() as tech_drawing:
    with Locations((0, 20)):
        add(e_line)
    TechnicalDrawing()
s = 100 / max(*tech_drawing.sketch.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(tech_drawing.sketch)
svg.write("assets/tech_drawing.svg")

# [ArrowHead]
arrow_head_types = [HeadType.CURVED, HeadType.STRAIGHT, HeadType.FILLETED]
arrow_heads = [ArrowHead(50, a_type) for a_type in arrow_head_types]
s = 100 / max(*arrow_heads[0].bounding_box().size)
svg = ExportSVG(scale=s)
for i, arrow_head in enumerate(arrow_heads):
    svg.add_shape(arrow_head.moved(Location((0, -i * 40))))
    svg.add_shape(Text(arrow_head_types[i].name, 5).moved(Location((-25, -i * 40))))
svg.write("assets/arrow_head.svg")

# [Arrow]
arrow = Arrow(
    10, shaft_path=Edge.make_circle(100, start_angle=0, end_angle=10), shaft_width=1
)
s = 100 / max(*arrow.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(arrow)
svg.write("assets/arrow.svg")
