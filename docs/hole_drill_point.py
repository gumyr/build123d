"""
Section drawing of a blind hole with a drill point, dimensioned with the
arguments of Hole that set it, for the documentation of point_angle.
"""

from math import radians, tan

from build123d import *

radius, depth, point_angle = 5, 12, 118
point_height = radius / tan(radians(point_angle / 2))

with BuildPart() as block:
    Box(40, 40, 30, align=(Align.CENTER, Align.CENTER, Align.MAX))
    Hole(radius, depth, point_angle=point_angle)

# Half section on the XZ plane, laid flat on the page: X right, Z up
section = Plane.XZ.to_local_coords(block.part & Plane.XZ * Rectangle(80, 80))
outline = section.edges()

drafting_options = Draft(
    font_size=1.4, arrow_length=1.2, line_width=0.1, pad_around_text=0.6
)
diameter_line = ExtensionLine(
    border=((-radius, 0), (radius, 0)),
    offset=(0, 4),
    draft=drafting_options,
    label="2 × radius",
)
depth_line = ExtensionLine(
    border=((-radius, 0), (-radius, -depth)),
    offset=(-6, 0),
    draft=drafting_options,
    label="depth",
)
point_line = ExtensionLine(
    border=((radius, -depth), (0, -depth - point_height)),
    offset=(6, 0),
    draft=drafting_options,
    label="h",
)
# The angle is shown opposite the tip, between the cone generatrices extended
tip = Vector(0, -depth - point_height)
arc_radius = 9
angle_arc = CenterArc(tip, arc_radius, 270 - point_angle / 2, point_angle)
angle_line = DimensionLine(angle_arc, draft=drafting_options, label="point_angle")
generatrices = [
    Line(tip, tip + Vector(side * radius, -point_height) * (arc_radius + 1) / radius)
    for side in (-1, 1)
]
axis = Line((0, 6), (0, -depth - point_height - arc_radius - 2))
shoulder = Line((-radius, -depth), (radius, -depth))
note = Pos(0, -33) * Text("h = radius / tan(point_angle / 2)", 1.6)

exporter = ExportSVG(unit=Unit.MM, scale=4)
exporter.add_layer("Visible", line_weight=0.35)
exporter.add_layer("Hatch", fill_color=(220, 220, 220), line_weight=0)
exporter.add_layer("Dimensions", line_weight=0.12, fill_color=(0, 0, 0))
exporter.add_layer("Center", line_type=LineType.ISO_DASH_DOT, line_weight=0.15)
exporter.add_shape(section, layer="Hatch")
exporter.add_shape(outline, layer="Visible")
exporter.add_shape(
    [diameter_line, depth_line, point_line, angle_line, note], layer="Dimensions"
)
exporter.add_shape([axis, shoulder, *generatrices], layer="Center")
exporter.write("assets/hole_drill_point.svg")
