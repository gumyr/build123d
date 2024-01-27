"""
name: "build_123d_logo.py"
title: "Former build123d Logo"
authors: "Gumyr"
license: "http://www.apache.org/licenses/LICENSE-2.0"
created: "2022-08-05"
modified: "2023-07-31"

description: | 
    This example creates the former build123d logo (new logo was created in the end of 2023).

    Using text and lines to create the first build123d logo. 
    The builder mode example also generates the SVG file `logo.svg`.

has_builder_mode: true
has_algebra_mode: true
image_files:
    - "example_build123d_logo_01.png"
"""
# [Imports]
from build123d import *
from build123d import Shape
from ocp_vscode import *

# [Parameters]
# - none

# [Code]
with BuildSketch() as logo_text:
    Text("123d", font_size=10, align=(Align.MIN, Align.MIN))
    font_height = logo_text.vertices().sort_by(Axis.Y)[-1].Y

with BuildSketch() as build_text:
    Text("build", font_size=5, align=(Align.CENTER, Align.CENTER))
    build_bb = bounding_box(build_text.sketch, mode=Mode.PRIVATE)
    build_vertices = build_bb.vertices().sort_by(Axis.X)
    build_width = build_vertices[-1].X - build_vertices[0].X

with BuildLine() as one:
    l1 = Line((font_height * 0.3, 0), (font_height * 0.3, font_height))
    TangentArc(l1 @ 1, (0, font_height * 0.7), tangent=(l1 % 1) * -1)

with BuildSketch() as two:
    with Locations((font_height * 0.35, 0)):
        Text("2", font_size=10, align=(Align.MIN, Align.MIN))

with BuildPart() as three_d:
    with BuildSketch(Plane((font_height * 1.1, 0))):
        Text("3d", font_size=10, align=(Align.MIN, Align.MIN))
    extrude(amount=font_height * 0.3)
    logo_width = three_d.vertices().sort_by(Axis.X)[-1].X

with BuildLine() as arrow_left:
    t1 = TangentArc((0, 0), (1, 0.75), tangent=(1, 0))
    mirror(t1, Plane.XZ)

ext_line_length = font_height * 0.5
dim_line_length = (logo_width - build_width - 2 * font_height * 0.05) / 2
with BuildLine() as extension_lines:
    l1 = Line((0, -font_height * 0.1), (0, -ext_line_length - font_height * 0.1))
    l2 = Line(
        (logo_width, -font_height * 0.1),
        (logo_width, -ext_line_length - font_height * 0.1),
    )
    with Locations(l1 @ 0.5):
        add(arrow_left.line)
    with Locations(l2 @ 0.5):
        add(arrow_left.line, rotation=180.0)
    Line(l1 @ 0.5, l1 @ 0.5 + Vector(dim_line_length, 0))
    Line(l2 @ 0.5, l2 @ 0.5 - Vector(dim_line_length, 0))

# Precisely center the build Faces
with BuildSketch() as build:
    with Locations(
        (l1 @ 0.5 + l2 @ 0.5) / 2
        - Vector((build_vertices[-1].X + build_vertices[0].X) / 2, 0)
    ):
        add(build_text.sketch)


if True:
    logo = Compound(
        children=[
            one.line,
            two.sketch,
            three_d.part,
            extension_lines.line,
            build.sketch,
        ]
    )

    # logo.export_step("logo.step")
    def add_svg_shape(svg: ExportSVG, shape: Shape, color: tuple[float, float, float]):
        global counter
        try:
            counter += 1
        except:
            counter = 1

        visible, _hidden = shape.project_to_viewport(
            (-5, 1, 10), viewport_up=(0, 1, 0), look_at=(0, 0, 0)
        )
        if color is not None:
            svg.add_layer(str(counter), fill_color=color, line_weight=1)
        else:
            svg.add_layer(str(counter), line_weight=1)
        svg.add_shape(visible, layer=str(counter))

    svg = ExportSVG(scale=20)
    add_svg_shape(svg, logo, None)
    # add_svg_shape(svg, Compound(children=[one.line, extension_lines.line]), None)
    # add_svg_shape(svg, Compound(children=[two.sketch, build.sketch]), (170, 204, 255))
    # add_svg_shape(svg, three_d.part, (85, 153, 255))
    svg.write("logo.svg")

show_object(one, name="one")
show_object(two, name="two")
show_object(three_d, name="three_d")
show_object(extension_lines, name="extension_lines")
show_object(build, name="build")
# [End]