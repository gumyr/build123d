"""
Maker Coin

name: maker_coin.py
by:   Gumyr
date: Febrary 27, 2024

desc:
    This example creates the maker coin as defined by Angus on the Maker's Muse
    YouTube channel. There are two key features:
    1) the use of DoubleTangentArc to create a smooth transition from the
       central dish to the external arc.
    2) embossing the text into the top of the coin not just as a simple
       extrude but from a projection which results in text with even depth.

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
from ocp_vscode import *

# [Code]
# Coin Parameters
diameter, thickness = 50 * MM, 10 * MM

with BuildPart() as maker_coin:
    # On XZ plane draw the profile of half the coin
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine() as outline:
            l1 = Polyline((0, thickness * 0.6), (0, 0), ((diameter - thickness) / 2, 0))
            l2 = JernArc(
                start=l1 @ 1, tangent=l1 % 1, radius=thickness / 2, arc_size=300
            )  # extend the arc beyond the intersection but not closed
            l3 = DoubleTangentArc(l1 @ 0, tangent=(1, 0), other=l2)
        make_face()  # make it a 2D shape
    revolve()  # revolve 360°

    # Pattern the detents around the coin
    with BuildSketch() as detents:
        with PolarLocations(radius=(diameter + 5) / 2, count=8):
            Circle(thickness * 1.4 / 2)
    extrude(amount=thickness, mode=Mode.SUBTRACT)  # cut away the detents

    fillet(maker_coin.edges(Select.NEW), 2)  # fillet the cut edges

    # Add an embossed label
    with BuildSketch(Plane.XY.offset(thickness)) as label:  # above coin
        Text("OS", font_size=15)
    project()  # label on top of coin
    extrude(amount=-thickness / 5, mode=Mode.SUBTRACT)  # emboss label

show(maker_coin)
# [End]
