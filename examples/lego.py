"""

name: lego.py
by:   Gumyr
date: September 12th 2022

desc:

    This example creates a model of a double wide lego block with a
    parametric length (pip_count).
    *** Don't edit this file without checking the lego tutorial ***

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

pip_count = 6

lego_unit_size = 8
pip_height = 1.8
pip_diameter = 4.8
block_length = lego_unit_size * pip_count
block_width = 16
base_height = 9.6
block_height = base_height + pip_height
support_outer_diameter = 6.5
support_inner_diameter = 4.8
ridge_width = 0.6
ridge_depth = 0.3
wall_thickness = 1.2

svg_opts = {
    "pixel_scale": 20,
    "show_axes": False,
    "show_hidden": False,
}

with BuildPart() as lego:
    # Draw the bottom of the block
    with BuildSketch() as plan:
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        plan.sketch.export_svg(
            "tutorial_step4.svg", (0, 0, 10), (0, 1, 0), svg_opts=svg_opts
        )
        # Subtract an offset to create the block walls
        offset(
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        plan.sketch.export_svg(
            "tutorial_step5.svg", (0, 0, 10), (0, 1, 0), svg_opts=svg_opts
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
            Rectangle(width=block_length, height=ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
            Rectangle(width=ridge_width, height=block_width)
        plan.sketch.export_svg(
            "tutorial_step6.svg", (0, 0, 10), (0, 1, 0), svg_opts=svg_opts
        )
        # Substract a rectangle leaving ribs on the block walls
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        plan.sketch.export_svg(
            "tutorial_step7.svg", (0, 0, 10), (0, 1, 0), svg_opts=svg_opts
        )
        # Add a row of hollow circles to the center
        with GridLocations(
            x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
        ):
            Circle(radius=support_outer_diameter / 2)
            Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
        plan.sketch.export_svg(
            "tutorial_step8.svg", (0, 0, 10), (0, 1, 0), svg_opts=svg_opts
        )
    # Extrude this base sketch to the height of the walls
    extrude(amount=base_height - wall_thickness)
    lego.part.export_svg(
        "tutorial_step9.svg", (-5, -30, 50), (0, 0, 1), svg_opts=svg_opts
    )
    # Create a box on the top of the walls
    with Locations((0, 0, lego.vertices().sort_by(Axis.Z)[-1].Z)):
        # Create the top of the block
        Box(
            length=block_length,
            width=block_width,
            height=wall_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    lego.part.export_svg(
        "tutorial_step10.svg",
        (-5, -30, 50),
        (0, 0, 1),
        svg_opts={
            "pixel_scale": 20,
            "show_axes": False,
            "show_hidden": True,
        },
    )
    # Create a workplane on the top of the block
    with BuildPart(lego.faces().sort_by(Axis.Z)[-1]):
        # Create a grid of pips
        with GridLocations(lego_unit_size, lego_unit_size, pip_count, 2):
            Cylinder(
                radius=pip_diameter / 2,
                height=pip_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
    lego.part.export_svg(
        "tutorial_step11.svg", (-100, -100, 50), (0, 0, 1), svg_opts=svg_opts
    )
    lego.part.export_svg(
        "tutorial_lego.svg",
        (-100, -100, 50),
        (0, 0, 1),
        svg_opts={
            "pixel_scale": 20,
            "show_axes": False,
            "show_hidden": True,
        },
    )

assert abs(lego.part.volume - 3212.187337781355) < 1e-3

if "show_object" in locals():
    show_object(lego.part.wrapped, name="lego")
