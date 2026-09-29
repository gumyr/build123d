"""
Create the sheet metal reference surface diagram

name: sheet_surfaces.py
by:   Gumyr
date: September 10th 2026

desc:
    This python module generates a section through a bent sheet for each of
    the four SheetSurface choices, showing where the material lies relative
    to the reference surface the shell represents and to its normal.

license:

    Copyright 2026 Gumyr

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
from build123d.sheet_utils import material_offsets

THICKNESS, RADIUS, K_FACTOR = 6, 6, 0.4
BASE, WALL, PANEL = 36, 26, 70  # base length, wall height, panel pitch

svg = ExportSVG(margin=5)
svg.add_layer("material", fill_color=Color(0.85, 0.85, 0.85), line_color="black")
svg.add_layer("reference", line_color=Color(0.8, 0.1, 0.1), line_weight=0.9)
svg.add_layer(
    "normal", fill_color=Color(0.1, 0.3, 0.8), line_color=Color(0.1, 0.3, 0.8)
)
svg.add_layer("text", fill_color="black", line_color=None)


def bent_path(center: Vector, radius: float, x0: float, y1: float) -> Curve:
    """A base line, a quarter turn about center, and a wall line up to y1."""
    return Curve(
        [
            Line((x0, center.Y - radius), (center.X, center.Y - radius)),
            CenterArc(center, radius, 270, 90),
            Line((center.X + radius, center.Y), (center.X + radius, y1)),
        ]
    )


for index, surface in enumerate(SheetSurface):
    left = index * PANEL
    parameters = SheetMetalParameters(
        thickness=THICKNESS,
        bend_radius=RADIUS,
        k_factor=K_FACTOR,
        sheet_surface=surface,
    )
    # the drawn face is y = 0; the material spans these offsets from it, the
    # inside face of a bend toward the normal being the upper one
    inside, outside = material_offsets(parameters)
    center = Vector(left + BASE, inside + RADIUS)
    section = make_face(
        Wire(
            bent_path(center, RADIUS, left, WALL).edges()
            + [Line((center.X + RADIUS, WALL), (center.X + RADIUS + THICKNESS, WALL))]
            + bent_path(center, RADIUS + THICKNESS, left, WALL).edges()
            + [Line((left, inside - THICKNESS), (left, inside))]
        )
    )
    svg.add_shape(section, "material")
    svg.add_shape(bent_path(center, RADIUS + inside, left, WALL), "reference")

    arrow_foot = Vector(left + 12, 0)
    svg.add_shape(Line(arrow_foot, arrow_foot + (0, 10)), "normal")
    svg.add_shape(
        Pos(arrow_foot + (0, 10))
        * Triangle(a=3, b=3, c=3, align=(Align.CENTER, Align.MIN)),
        "normal",
    )
    svg.add_shape(
        Pos(left + BASE / 2 + 4, WALL + 6) * Text(f"SheetSurface.{surface.name}", 4),
        "text",
    )
    svg.add_shape(
        Pos(left + 16, 5) * Text("normal", 3, align=(Align.MIN, Align.CENTER)), "text"
    )

# legend
svg.add_shape(Line((0, -14), (12, -14)), "reference")
svg.add_shape(
    Pos(15, -14)
    * Text(
        "reference surface, the shell BuildSheet builds",
        3,
        align=(Align.MIN, Align.CENTER),
    ),
    "text",
)
svg.add_shape(Pos(6, -22) * Rectangle(12, 4), "material")
svg.add_shape(
    Pos(15, -22) * Text("material", 3, align=(Align.MIN, Align.CENTER)), "text"
)

svg.write("assets/sheet_surfaces.svg")
