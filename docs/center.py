from build123d import *

svg_opts = {"pixel_scale": 2, "show_axes": False, "show_hidden": False}

line_width = 2
with BuildSketch() as isosceles_triangle:
    # Make Bounding Box frame
    with BuildLine():
        Polyline((-100, 0), (100, 0), (100, 200), (-100, 200), close=True)
        offset(amount=line_width)
    make_face()
    Rectangle(200, 200, align=(Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    # Make triangle
    with BuildLine():
        Polyline((-100, 0), (100, 0), (0, 200), close=True)
    triangle = make_face()
    triangle_face: Face = triangle.faces()[0]
    center_of_bbox = triangle_face.center(CenterOf.BOUNDING_BOX)
    center_of_geom = triangle_face.center(CenterOf.GEOMETRY)
    center_of_mass = triangle_face.center(CenterOf.MASS)
    with Locations(center_of_bbox):
        Circle(line_width, mode=Mode.SUBTRACT)
    with Locations(center_of_geom):
        RegularPolygon(line_width, 4, mode=Mode.SUBTRACT)
    with Locations(center_of_bbox + Vector(line_width, line_width)):
        Text(
            "center of\nbounding\nbox",
            # font="FreeSerif",
            font_size=3 * line_width,
            align=Align.MIN,
            mode=Mode.SUBTRACT,
        )
    with Locations(center_of_geom + Vector(line_width, line_width)):
        Text(
            "center of\ngeometry",
            # font="FreeSerif",
            font_size=3 * line_width,
            align=Align.MIN,
            mode=Mode.SUBTRACT,
        )

isosceles_triangle.sketch.export_svg(
    "assets/center.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts
)


line = Edge.make_tangent_arc((0, 0), (100, 0), (100, 100))
line_center_geom = Location(line.center(CenterOf.GEOMETRY)) * RegularPolygon(
    line_width, 4
)
line_center_bbox = Location(line.center(CenterOf.BOUNDING_BOX)) * Circle(line_width)
line_center_mass = Location(line.center(CenterOf.MASS)) * RegularPolygon(line_width, 3)
# one_d_diagram = Compound().make_compound(
#     # [line, line_center_bbox, line_center_geom, line_center_mass]
#     [line_center_bbox, line_center_geom, line_center_mass]
# )
# svg = ExportSVG(margin=5, line_weight=0.13)
svg = ExportSVG(margin=5, line_weight=0.1)
svg.add_shape(line)
svg.add_shape(line_center_geom)
svg.add_shape(line_center_bbox)
svg.add_shape(line_center_mass)

# svg.add_layer("hidden", color=ColorIndex.LIGHT_GRAY, line_weight=0.09, line_type=LineType.ISO_DASH_SPACE)
# svg.add_shape(dwg.hidden_lines, layer="hidden")
svg.write("assets/one_d_center.svg")

# one_d_diagram.export_svg(
#     "assets/one_d_center.svg", (0, 0, 100), (0, 1, 0), svg_opts=svg_opts
# )
# show_object(one_d_diagram)
show_object(isosceles_triangle.sketch)
