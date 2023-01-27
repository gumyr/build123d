"""

name: clock.py
by:   Gumyr
date: July 15th 2022

desc:

    This example demonstrates using polar coordinates in a sketch.

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

clock_radius = 10
with BuildSketch() as minute_indicator:
    with BuildLine() as outline:
        l1 = CenterArc((0, 0), clock_radius * 0.975, 0.75, 4.5)
        l2 = CenterArc((0, 0), clock_radius * 0.925, 0.75, 4.5)
        Line(l1 @ 0, l2 @ 0)
        Line(l1 @ 1, l2 @ 1)
    MakeFace()
    Fillet(*minute_indicator.vertices(), radius=clock_radius * 0.01)

with BuildSketch() as clock_face:
    Circle(clock_radius)
    with PolarLocations(0, 60):
        Add(minute_indicator.sketch, mode=Mode.SUBTRACT)
    with PolarLocations(clock_radius * 0.875, 12):
        SlotOverall(clock_radius * 0.05, clock_radius * 0.025, mode=Mode.SUBTRACT)
    for hour in range(1, 13):
        with PolarLocations(clock_radius * 0.75, 1, -hour * 30 + 90, 360, rotate=False):
            Text(
                str(hour),
                fontsize=clock_radius * 0.175,
                font_style=FontStyle.BOLD,
                mode=Mode.SUBTRACT,
            )

if "show_object" in locals():
    show_object(clock_face.sketch.wrapped, name="clock_face")
