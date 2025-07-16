"""

name: technical_drawing.py
by:   gumyr
date: May 23, 2025

desc:

    Generate a multi-view technical drawing of a part, including isometric and
    orthographic projections.

    This module demonstrates how to create a standard technical drawing using
    `build123d`. It includes:
    - Projection of a 3D part to 2D views (plan, front, side, isometric)
    - Drawing borders and dimensioning using extension lines
    - SVG export of visible and hidden geometry
    - Example part: Nema 23 stepper motor from `bd_warehouse.open_builds`

    The following standard views are generated:
    - Plan View (Top)
    - Front Elevation
    - Side Elevation (Right Side)
    - Isometric Projection

    The resulting drawing is exported as an SVG and can be previewed using
    the `ocp_vscode` viewer.

license:

    Copyright 2025 gumyr

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

# [code]
from datetime import date

from bd_warehouse.open_builds import StepperMotor
from build123d import *
from ocp_vscode import show


def project_to_2d(
    part: Part,
    viewport_origin: VectorLike,
    viewport_up: VectorLike,
    page_origin: VectorLike,
    scale_factor: float = 1.0,
) -> tuple[ShapeList[Edge], ShapeList[Edge]]:
    """project_to_2d

    Helper function to generate 2d views translated on the 2d page.

    Args:
        part (Part): 3d object
        viewport_origin (VectorLike): location of viewport
        viewport_up (VectorLike): direction of the viewport Y axis
        page_origin (VectorLike): center of 2d object on page
        scale_factor (float, optional): part scalar. Defaults to 1.0.

    Returns:
        tuple[ShapeList[Edge], ShapeList[Edge]]: visible & hidden edges
    """
    scaled_part = part if scale_factor == 1.0 else scale(part, scale_factor)
    visible, hidden = scaled_part.project_to_viewport(
        viewport_origin, viewport_up, look_at=(0, 0, 0)
    )
    visible = [Pos(*page_origin) * e for e in visible]
    hidden = [Pos(*page_origin) * e for e in hidden]

    return ShapeList(visible), ShapeList(hidden)


# The object that appearing in the drawing
stepper: Part = StepperMotor("Nema23")

# Create a standard technical drawing border on A4 paper
border = TechnicalDrawing(
    designed_by="build123d",
    design_date=date.fromisoformat("2025-05-23"),
    page_size=PageSize.A4,
    title="Nema 23 Stepper",
    sub_title="Units: mm",
    drawing_number="BD-1",
    sheet_number=1,
    drawing_scale=1,
)
page_size = border.bounding_box().size

# Specify the drafting options for extension lines
drafting_options = Draft(font_size=3.5, decimal_precision=1, display_units=False)

# Lists used to store the 2d visible and hidden lines
visible_lines, hidden_lines = [], []

# Isometric Projection - A 3D view where the part is rotated to reveal three
# dimensions equally.
iso_v, iso_h = project_to_2d(
    stepper,
    (100, 100, 100),
    (0, 0, 1),
    page_size * 0.3,
    0.75,
)
visible_lines.extend(iso_v)
hidden_lines.extend(iso_h)

# Plan View (Top) - The view from directly above the part (looking down along
# the Z-axis).
vis, _ = project_to_2d(
    stepper,
    (0, 0, 100),
    (0, 1, 0),
    (page_size.X * -0.3, page_size.Y * 0.25),
)
visible_lines.extend(vis)

# Dimension the top of the stepper
top_bbox = Curve(vis).bounding_box()
perimeter = Pos(*top_bbox.center()) * Rectangle(top_bbox.size.X, top_bbox.size.Y)
d1 = ExtensionLine(
    border=perimeter.edges().sort_by(Axis.X)[-1], offset=1 * CM, draft=drafting_options
)
d2 = ExtensionLine(
    border=perimeter.edges().sort_by(Axis.Y)[0], offset=1 * CM, draft=drafting_options
)
# Add a label
l1 = Text("Plan View", 6)
l1.position = vis.sort_by(Axis.Y)[-1].center() + (0, 5 * MM)

# Front Elevation - The primary view, typically looking along the Y-axis,
# showing the height.
vis, _ = project_to_2d(
    stepper,
    (0, -100, 0),
    (0, 0, 1),
    (page_size.X * -0.3, page_size.Y * -0.125),
)
visible_lines.extend(vis)
d3 = ExtensionLine(
    border=vis.sort_by(Axis.Y)[-1], offset=-5 * MM, draft=drafting_options
)
l2 = Text("Front Elevation", 6)
l2.position = vis.group_by(Axis.Y)[0].sort_by(Edge.length)[-1].center() + (0, -5 * MM)

# Side Elevation - Often refers to the Right Side View, looking along the X-axis.
vis, _ = project_to_2d(
    stepper,
    (100, 0, 0),
    (0, 0, 1),
    (0, page_size.Y * 0.15),
)
visible_lines.extend(vis)
side_bbox = Curve(vis).bounding_box()
perimeter = Pos(*side_bbox.center()) * Rectangle(side_bbox.size.X, side_bbox.size.Y)
d4 = ExtensionLine(
    border=perimeter.edges().sort_by(Axis.X)[-1], offset=1 * CM, draft=drafting_options
)
l3 = Text("Side Elevation", 6)
l3.position = vis.group_by(Axis.Y)[0].sort_by(Edge.length)[-1].center() + (0, -5 * MM)


# Initialize the SVG exporter
exporter = ExportSVG(unit=Unit.MM)
# Define visible and hidden line layers
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
# Add the objects to the appropriate layer
exporter.add_shape(visible_lines, layer="Visible")
exporter.add_shape(hidden_lines, layer="Hidden")
exporter.add_shape(border, layer="Visible")
exporter.add_shape([d1, d2, d3, d4], layer="Visible")
exporter.add_shape([l1, l2, l3], layer="Visible")
# Write the file
exporter.write(f"assets/stepper_drawing.svg")

show(border, visible_lines, d1, d2, d3, d4, l1, l2, l3)
# [end]
