"""

name: vase.py
by:   Gumyr
date: July 15th 2022

desc:

    This example demonstrates the build123d techniques involving the creation of a vase. 
    Specifically, it showcases the processes of revolving a sketch, shelling 
    (creating a hollow object by removing material from its interior), and 
    selecting edges by position range and type for the application of fillets 
    (rounding off the edges).

    - Sketching: Drawing a 2D profile or outline that represents the side view of 
      the vase.
    - Revolving: Rotating the sketch around an axis to create a 3D object. This 
      step transforms the 2D profile into a 3D vase shape.
    - Offset/Shelling: Removing material from the interior of the solid vase to 
      create a hollow space, making it resemble a real vase more closely.
    - Edge Filleting: Selecting specific edges of the vase for filleting, which 
      involves rounding those edges. The edges are selected based on their position
      and type.

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

# [Code]

from build123d import *
from ocp_vscode import show_object

with BuildPart() as vase:
    with BuildSketch() as profile:
        with BuildLine() as outline:
            l1 = Line((0, 0), (12, 0))
            l2 = RadiusArc(l1 @ 1, (15, 20), 50)
            l3 = Spline(l2 @ 1, (22, 40), (20, 50), tangents=(l2 % 1, (-0.75, 1)))
            l4 = RadiusArc(l3 @ 1, l3 @ 1 + Vector(0, 5), 5)
            l5 = Spline(
                l4 @ 1,
                l4 @ 1 + Vector(2.5, 2.5),
                l4 @ 1 + Vector(0, 5),
                tangents=(l4 % 1, (-1, 0)),
            )
            Polyline(
                l5 @ 1,
                l5 @ 1 + Vector(0, 1),
                (0, (l5 @ 1).Y + 1),
                l1 @ 0,
            )
        make_face()
    revolve(axis=Axis.Y)
    offset(openings=vase.faces().filter_by(Axis.Y)[-1], amount=-1)
    top_edges = (
        vase.edges().filter_by_position(Axis.Y, 60, 62).filter_by(GeomType.CIRCLE)
    )
    fillet(top_edges, radius=0.25)
    fillet(vase.edges().sort_by(Axis.Y)[0], radius=0.5)


show_object(Rot(90, 0, 0) * vase.part, name="vase")
# [End]
