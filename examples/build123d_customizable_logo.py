"""

name: build123d_customizable_logo.py
by:   Gumyr and modified by jdegenstein
date: December 19th 2022

desc:

    This example creates the build123d customizable logo.

license:

    Copyright 2022 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
from build123d import *

with BuildSketch() as logo_text:
    Text("123d", fontsize=10, align=(Align.MIN, Align.MIN))
    font_height = logo_text.vertices().sort_by(Axis.Y)[-1].Y

with BuildSketch() as build_text:
    Text("build", fontsize=5, align=(Align.CENTER, Align.CENTER))
    build_bb = BoundingBox(build_text.sketch, mode=Mode.PRIVATE)
    build_vertices = build_bb.vertices().sort_by(Axis.X)
    build_width = build_vertices[-1].X - build_vertices[0].X

with BuildSketch() as cust_text:
    Text(
        "customizable",
        fontsize=2.9,
        align=(Align.CENTER, Align.CENTER),
        font_style=FontStyle.BOLD,
    )
    cust_bb = BoundingBox(cust_text.sketch, mode=Mode.PRIVATE)
    cust_vertices = cust_text.vertices().sort_by(Axis.X)
    cust_width = cust_vertices[-1].X - cust_vertices[0].X

with BuildLine() as one:
    l1 = Line((font_height * 0.3, 0), (font_height * 0.3, font_height))
    TangentArc(l1 @ 1, (0, font_height * 0.7), tangent=(l1 % 1) * -1)

with BuildSketch() as two:
    with Locations((font_height * 0.35, 0)):
        Text("2", fontsize=10, align=(Align.MIN, Align.MIN))

with BuildPart() as three_d:
    with Locations((font_height * 1.1, 0)):
        with BuildSketch():
            Text("3d", fontsize=10, align=(Align.MIN, Align.MIN))
        Extrude(amount=font_height * 0.3)
        logo_width = three_d.vertices().sort_by(Axis.X)[-1].X

with BuildLine() as arrow_left:
    t1 = TangentArc((0, 0), (1, 0.75), tangent=(1, 0))
    Mirror(t1, about=Plane.XZ)

ext_line_length = font_height * 0.5
dim_line_length = (logo_width - build_width - 2 * font_height * 0.05) / 2
with BuildLine() as extension_lines:
    l1 = Line((0, -font_height * 0.1), (0, -ext_line_length - font_height * 0.1))
    l2 = Line(
        (logo_width, -font_height * 0.1),
        (logo_width, -ext_line_length - font_height * 0.1),
    )
    with Locations(l1 @ 0.5):
        Add(*arrow_left.line)
    with Locations(l2 @ 0.5):
        Add(*arrow_left.line, rotation=180.0)
    Line(l1 @ 0.5, l1 @ 0.5 + Vector(dim_line_length, 0))
    Line(l2 @ 0.5, l2 @ 0.5 - Vector(dim_line_length, 0))

# Precisely center the build Faces
with BuildSketch() as build:
    with Locations(
        (l1 @ 0.5 + l2 @ 0.5) / 2
        - Vector((build_vertices[-1].X + build_vertices[0].X) / 2, 0)
    ):
        Add(build_text.sketch)
    # add the customizable text to the build text sketch
    with Locations(
        (l1 @ 1 + l2 @ 1) / 2
        - Vector((cust_vertices[-1].X + cust_vertices[0].X - 1.2), 1.4)
    ):
        Add(cust_text.sketch)

cmpd = Compound.make_compound(
    [three_d.part, two.sketch, one.line, build.sketch, extension_lines.line]
)

cmpd.export_svg(
    "cmpd.svg",
    (-10, 10, 60),
    (0, 0, 1),
    svg_opts={
        "pixel_scale": 20,
        "show_axes": False,
        "show_hidden": False,
    },
)

if "show_object" in locals():
    show_object(cmpd, name="compound")
    # show_object(one.line.wrapped, name="one")
    # show_object(two.sketch.wrapped, name="two")
    # show_object(three_d.part.wrapped, name="three_d")
    # show_object(extension_lines.line.wrapped, name="extension_lines")
    # show_object(build.sketch.wrapped, name="build")
