"""

name: lego.py
by:   Gumyr
date: September 12th 2022

desc:

    This example creates a model of a double wide lego block with a
    parametric length (pip_count).

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
from cadquery import Plane

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

with BuildPart() as lego:
    # Draw the bottom of the block
    with BuildSketch():
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(block_length, block_width)
        # Subtract an offset to create the block walls
        Offset(
            perimeter,
            amount=-wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(0, lego_unit_size, 1, 2):
            Rectangle(block_length, ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
            Rectangle(ridge_width, block_width)
        # Substract a rectangle leaving ribs on the block walls
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        # Add a row of hollow circles to the center
        with GridLocations(lego_unit_size, 0, pip_count - 1, 1):
            Circle(support_outer_diameter / 2)
            Circle(support_inner_diameter / 2, mode=Mode.SUBTRACT)
    # Extrude this base sketch to the height of the walls
    Extrude(amount=base_height - wall_thickness)
    # Create a workplane on the top of the walls
    with Workplanes(
        Plane(origin=(0, 0, base_height - wall_thickness), normal=(0, 0, 1))
    ):
        # Create the top of the block
        Box(
            block_length,
            block_width,
            wall_thickness,
            centered=(True, True, False),
        )
    # Create a workplane on the top of the block
    with Workplanes(lego.faces().sort_by(SortBy.Z)[-1]):
        # Create a grid of pips
        with GridLocations(lego_unit_size, lego_unit_size, pip_count, 2):
            Cylinder(
                radius=pip_diameter / 2, height=pip_height, centered=(True, True, False)
            )


if "show_object" in locals():
    show_object(lego.part, name="lego")
