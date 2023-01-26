"""

name: canadian_flag.py
by:   Gumyr
date: July 14th 2022

desc:

    This example demonstrates building complex lines that snap to
    existing features.

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

with BuildSketch() as leaf:
    with BuildLine() as outline:
        l1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
        l2 = Polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
        RadiusArc(l1 @ 1, l2 @ 0, 0.0271)
        l3 = Polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
        TangentArc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
        l4 = Polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
        SagittaArc(l3 @ 1, l4 @ 0, 0.003)
        l5 = Polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
        ThreePointArc(l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0)
        l6 = Polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
        Spline(l5 @ 1, l6 @ 0, tangents=(l5 % 1, l6 % 0), tangent_scalars=(2, 2))
        l7 = Line((0.0692, 0.7808), (0.0000, 0.9167))
        TangentArc(l6 @ 1, l7 @ 0, tangent=l6 % 1)
        Mirror(*outline.edges(), about=Plane.YZ)
    MakeFace(*leaf.pending_edges)

with BuildSketch() as west_field:
    with Locations((-1, 0)):
        Rectangle(0.5, 1, align=(Align.MIN, Align.MIN))

with BuildSketch() as east_field:
    Mirror(west_field.sketch, about=Plane.YZ)

with BuildSketch() as centre_field:
    Rectangle(1, 1, align=(Align.CENTER, Align.MIN))
    Add(leaf.sketch, mode=Mode.SUBTRACT)

if "show_object" in locals():
    show_object(
        [west_field.sketch.wrapped, east_field.sketch.wrapped, leaf.sketch.wrapped],
        name="flag_red_parts",
        options={"color": (255, 0, 0)},
    )
    show_object(
        centre_field.sketch.wrapped,
        name="flag_white_part",
        options={"color": (255, 255, 255)},
    )
