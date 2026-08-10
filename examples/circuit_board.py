"""
name: "circuit_board.py"
title: "Circuit Board With Holes"
authors: "Gumyr"
license: "http://www.apache.org/licenses/LICENSE-2.0"
created: "2022-09-01"
modified: "2024-01-27"

description: | 
    This example demonstrates placing holes around a part.
    
    - Builder mode uses `Locations` context to place the positions.
    - Algebra mode uses `product` and `range` to calculate the positions.

has_builder_mode: true
has_algebra_mode: true
image_files:
    - "example_circuit_board_01.png"
    - "example_circuit_board_02.png"
"""

# [Imports]
from build123d import *
from ocp_vscode import *

# [Parameters]
pcb_length = 70 * MM
pcb_width = 30 * MM
pcb_height = 3 * MM

# [Code]
with BuildPart() as pcb:
    with BuildSketch():
        Rectangle(pcb_length, pcb_width)

        for i in range(65 // 5):
            x = i * 5 - 30
            with Locations((x, -15), (x, -10), (x, 10), (x, 15)):
                Circle(1, mode=Mode.SUBTRACT)
        for i in range(30 // 5 - 1):
            y = i * 5 - 10
            with Locations((30, y), (35, y)):
                Circle(1, mode=Mode.SUBTRACT)
        with GridLocations(60, 20, 2, 2):
            Circle(2, mode=Mode.SUBTRACT)
    extrude(amount=pcb_height)

show_object(pcb.part.wrapped)
# [End]