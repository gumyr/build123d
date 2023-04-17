# [Setup]
from build123d import *

# [Setup]
svg_opts1 = {"pixel_scale": 100, "show_axes": False, "show_hidden": False}
svg_opts2 = {"pixel_scale": 300, "show_axes": True, "show_hidden": False}

# [Ex. 1]
with BuildSketch() as example_1:
    Circle(1)
# [Ex. 1]
example_1.sketch.export_svg(
    "assets/circle_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)
# [Ex. 2]
with BuildSketch() as example_2:
    Ellipse(1.5, 1)
# [Ex. 2]
example_2.sketch.export_svg(
    "assets/ellipse_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 3]
with BuildSketch() as example_3:
    inner = PolarLocations(0.5, 5, 0).local_locations
    outer = PolarLocations(1.5, 5, 36).local_locations
    points = [p.position for pair in zip(inner, outer) for p in pair]
    Polygon(*points)
# [Ex. 3]
example_3.sketch.export_svg(
    "assets/polygon_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 4]
with BuildSketch() as example_4:
    Rectangle(2, 1)
# [Ex. 4]
example_4.sketch.export_svg(
    "assets/rectangle_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 5]
with BuildSketch() as example_5:
    RectangleRounded(2, 1, 0.25)
# [Ex. 5]
example_5.sketch.export_svg(
    "assets/rectangle_rounded_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 6]
with BuildSketch() as example_6:
    RegularPolygon(1, 6)
# [Ex. 6]
example_6.sketch.export_svg(
    "assets/regular_polygon_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 7]
with BuildSketch() as example_7:
    arc = Edge.make_circle(1, start_angle=0, end_angle=45)
    SlotArc(arc, 0.25)
    SlotArc(arc, 0.01, mode=Mode.SUBTRACT)
# [Ex. 7]
example_7.sketch.export_svg(
    "assets/slot_arc_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 8]
with BuildSketch() as example_8:
    c = (0, 0)
    p = (1, 0)
    SlotCenterPoint(c, p, 0.25)
    with Locations(c):
        Circle(0.02, mode=Mode.SUBTRACT)
    with Locations(p):
        Circle(0.02, mode=Mode.SUBTRACT)
# [Ex. 8]
example_8.sketch.export_svg(
    "assets/slot_center_point_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 9]
with BuildSketch() as example_9:
    SlotCenterToCenter(1, 0.25)
# [Ex. 9]
example_9.sketch.export_svg(
    "assets/slot_center_to_center_example.svg",
    (0, 0, 100),
    (0, 1, 0),
    svg_opts=svg_opts1,
)

# [Ex. 10]
with BuildSketch() as example_10:
    SlotOverall(1, 0.25)
# [Ex. 10]
example_10.sketch.export_svg(
    "assets/slot_overall_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 11]
with BuildSketch() as example_11:
    Text("text", 1)
# [Ex. 11]
example_11.sketch.export_svg(
    "assets/text_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

# [Ex. 12]
with BuildSketch() as example_12:
    Trapezoid(2, 1, 80)
    with Locations((-0.75, -0.35)):
        Text("80", 0.2, mode=Mode.SUBTRACT)
# [Ex. 12]
example_12.sketch.export_svg(
    "assets/trapezoid_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
)

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

align.sketch.export_svg("assets/align.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts2)

if "show_object" in locals():
    # show_object(example_1.sketch, name="Ex. 1")
    # show_object(example_2.sketch, name="Ex. 2")
    # show_object(example_3.sketch, name="Ex. 3")
    # show_object(example_4.sketch, name="Ex. 4")
    # show_object(example_5.sketch, name="Ex. 5")
    # show_object(example_6.sketch, name="Ex. 6")
    # show_object(example_7.sketch, name="Ex. 7")
    # show_object(example_8.sketch, name="Ex. 8")
    # show_object(example_9.sketch, name="Ex. 9")
    # show_object(example_10.sketch, name="Ex. 10")
    # show_object(example_11.sketch, name="Ex. 11")
    # show_object(example_12.sketch, name="Ex. 12")
    show_object(align.sketch, name="align")
