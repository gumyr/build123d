"""

name: circuit_board.py
by:   Gumyr
date: September 1st 2022

desc:

    This example demonstrates placing holes around a part.

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

with BuildPart() as pcb:
    with BuildSketch():
        Rectangle(70, 30)
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
    extrude(amount=3)

if "show_object" in locals():
    show_object(pcb.part.wrapped)
