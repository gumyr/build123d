"""

name: roller_coaster.py
by:   Gumyr
date: July 19th 2022

desc:

    This example demonstrates building complex 3D lines by "snapping"
    features to existing objects.

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
from ocp_vscode import show_object

with BuildLine() as roller_coaster:
    powerup = Spline(
        (0, 0, 0),
        (50, 0, 50),
        (100, 0, 0),
        tangents=((1, 0, 0), (1, 0, 0)),
        tangent_scalars=(0.5, 2),
    )
    corner = RadiusArc(powerup @ 1, (100, 60, 0), -30)
    screw = Helix(75, 150, 15, center=(75, 40, 15), direction=(-1, 0, 0))
    Spline(corner @ 1, screw @ 0, tangents=(corner % 1, screw % 0))
    Spline(screw @ 1, (-100, 30, 10), powerup @ 0, tangents=(screw % 1, powerup % 0))

show_object(roller_coaster, name="roller_coaster")
