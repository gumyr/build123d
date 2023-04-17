# [Setup]
from build123d import *

# [Setup]
svg_opts1 = {"pixel_scale": 100, "show_axes": False, "show_hidden": True}
svg_opts2 = {"pixel_scale": 50, "show_axes": True, "show_hidden": False}

# [Ex. 1]
with BuildPart() as example_1:
    Box(3, 2, 1)
# [Ex. 1]
example_1.part.export_svg(
    "assets/box_example.svg", (-100, -50, 30), (0, 0, 1), svg_opts=svg_opts1
)
# [Ex. 2]
with BuildPart() as example_2:
    Cone(2, 1, 2)
# [Ex. 2]
example_2.part.export_svg(
    "assets/cone_example.svg", (-100, -50, 30), (0, 0, 1), svg_opts=svg_opts1
)

# [Ex. 3]
with BuildPart() as example_3:
    Box(3, 2, 1)
    with Locations(example_3.faces().sort_by(Axis.Z)[-1]):
        CounterBoreHole(0.2, 0.4, 0.5, 0.9)
# [Ex. 3]
example_3.part.export_svg(
    "assets/counter_bore_hole_example.svg",
    (-100, -50, 30),
    (0, 0, 1),
    svg_opts=svg_opts1,
)

# [Ex. 4]
with BuildPart() as example_4:
    Box(3, 2, 1)
    with Locations(example_3.faces().sort_by(Axis.Z)[-1]):
        CounterSinkHole(0.2, 0.4, 0.9)
# [Ex. 4]
example_4.part.export_svg(
    "assets/counter_sink_hole_example.svg",
    (-100, -50, 30),
    (0, 0, 1),
    svg_opts=svg_opts1,
)
# [Ex. 5]
with BuildPart() as example_5:
    Cylinder(1, 2)
# [Ex. 5]
example_5.part.export_svg(
    "assets/cylinder_example.svg", (-100, -50, 30), (0, 0, 1), svg_opts=svg_opts1
)
# [Ex. 6]
with BuildPart() as example_6:
    Box(3, 2, 1)
    Hole(0.4)
# [Ex. 6]
example_6.part.export_svg(
    "assets/hole_example.svg", (-100, -50, 30), (0, 0, 1), svg_opts=svg_opts1
)
# [Ex. 7]
with BuildPart() as example_7:
    Sphere(1, 0)
# [Ex. 7]
example_7.part.export_svg(
    "assets/sphere_example.svg", (-100, -50, 30), (0, 0, 1), svg_opts=svg_opts1
)
# [Ex. 8]
with BuildPart() as example_8:
    Torus(1, 0.2)
# [Ex. 8]
example_8.part.export_svg(
    "assets/torus_example.svg", (-100, -50, 30), (0, 0, 1), svg_opts=svg_opts1
)
# [Ex. 9]
with BuildPart() as example_9:
    Wedge(1, 1, 1, 0, 0, 0.5, 0.5)
# [Ex. 9]
example_9.part.export_svg(
    "assets/wedge_example.svg", (-100, -50, 30), (0, 0, 1), svg_opts=svg_opts1
)

# # [Ex. 4]
# with BuildPart() as example_4:
#     Rectangle(2, 1)
# # [Ex. 4]
# example_4.part.export_svg(
#     "assets/rectangle_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

# # [Ex. 5]
# with BuildPart() as example_5:
#     RectangleRounded(2, 1, 0.25)
# # [Ex. 5]
# example_5.part.export_svg(
#     "assets/rectangle_rounded_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

# # [Ex. 6]
# with BuildPart() as example_6:
#     RegularPolygon(1, 6)
# # [Ex. 6]
# example_6.part.export_svg(
#     "assets/regular_polygon_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

# # [Ex. 7]
# with BuildPart() as example_7:
#     arc = Edge.make_circle(1, start_angle=0, end_angle=45)
#     SlotArc(arc, 0.25)
#     SlotArc(arc, 0.01, mode=Mode.SUBTRACT)
# # [Ex. 7]
# example_7.part.export_svg(
#     "assets/slot_arc_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

# # [Ex. 8]
# with BuildPart() as example_8:
#     c = (0, 0)
#     p = (1, 0)
#     SlotCenterPoint(c, p, 0.25)
#     with Locations(c):
#         Circle(0.02, mode=Mode.SUBTRACT)
#     with Locations(p):
#         Circle(0.02, mode=Mode.SUBTRACT)
# # [Ex. 8]
# example_8.part.export_svg(
#     "assets/slot_center_point_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

# # [Ex. 9]
# with BuildPart() as example_9:
#     SlotCenterToCenter(1, 0.25)
# # [Ex. 9]
# example_9.part.export_svg(
#     "assets/slot_center_to_center_example.svg",
#     (0, 0, 100),
#     (0, 1, 0),
#     svg_opts=svg_opts1,
# )

# # [Ex. 10]
# with BuildPart() as example_10:
#     SlotOverall(1, 0.25)
# # [Ex. 10]
# example_10.part.export_svg(
#     "assets/slot_overall_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

# # [Ex. 11]
# with BuildPart() as example_11:
#     Text("text", 1)
# # [Ex. 11]
# example_11.part.export_svg(
#     "assets/text_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

# # [Ex. 12]
# with BuildPart() as example_12:
#     Trapezoid(2, 1, 80)
#     with Locations((-0.75, -0.35)):
#         Text("80", 0.2, mode=Mode.SUBTRACT)
# # [Ex. 12]
# example_12.part.export_svg(
#     "assets/trapezoid_example.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts1
# )

if "show_object" in locals():
    show_object(example_1.part, name="Ex. 1")
    # show_object(example_2.part, name="Ex. 2")
    # show_object(example_3.part, name="Ex. 3")
    # show_object(example_4.part, name="Ex. 4")
    # show_object(example_5.part, name="Ex. 5")
    # show_object(example_6.part, name="Ex. 6")
    # show_object(example_7.part, name="Ex. 7")
    # show_object(example_8.part, name="Ex. 8")
    # show_object(example_9.part, name="Ex. 9")
    # show_object(example_10.part, name="Ex. 10")
    # show_object(example_11.part, name="Ex. 11")
    # show_object(example_12.part, name="Ex. 12")
