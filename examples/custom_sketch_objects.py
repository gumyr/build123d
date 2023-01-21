"""

name: custom_sketch_objects.py
by:   Gumyr
date: Jan 21st 2023

desc:

    This example demonstrates user generated custom BuildSketch objects.

license:

    Copyright 2023 Gumyr

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


class MyRectangle(BaseSketchObject):
    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
        face = Face.make_rect(height, width)
        super().__init__(face, rotation, centered, mode)


class MyHole(BaseSketchObject):
    def __init__(
        self,
        radius: float,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.SUBTRACT,
    ):
        face = Face.make_from_wires(Wire.make_circle(radius))
        super().__init__(face, rotation, centered, mode)


with BuildSketch() as builder:
    MyRectangle(width=20, height=15, centered=(True, True), rotation=45)
    MyHole(radius=3)


if "show_object" in locals():
    show_object(builder.sketch.wrapped)
