"""
An oval flanged bearing unit with tapered sides created with the draft operation.

name: cast_bearing_unit.py
by:   Gumyr
date: May 25, 2025

desc:

    This example demonstrates the creation of a castable flanged bearing housing
    using the `draft` operation to add appropriate draft angles for mold release.

    ### Highlights:

    - **Component Integration**: The design incorporates a press-fit bore for a
    `SingleRowAngularContactBallBearing` and mounting holes for
    `SocketHeadCapScrew` fasteners.
    - **Draft Angle Application**: Vertical side faces are identified and modified
    with a 4-degree draft angle using the `draft()` function. This simulates the
    taper needed for cast parts to be removed cleanly from a mold.
    - **Filleting**: All edges are filleted to reflect casting-friendly geometry and
    improve aesthetics.
    - **Parametric Design**: Dimensions such as bolt spacing, bearing size, and
    housing depth are parameterized for reuse and adaptation to other sizes.

    The result is a realistic, fabrication-aware model that can be used for
    documentation, simulation, or manufacturing workflows. The final assembly
    includes the housing, inserted bearing, and positioned screws, rendered with
    appropriate coloring for clarity.

license:

    Copyright 2025 Gumyr

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
from ocp_vscode import show

A, A1, Db2, H, J = 26, 11, 57, 98.5, 76.5
with BuildPart() as oval_flanged_bearing_unit:
    with BuildSketch() as plan:
        housing = Circle(Db2 / 2)
        with GridLocations(J, 0, 2, 1) as bolt_centers:
            Circle((H - J) / 2)
        make_hull()
    extrude(amount=A1)
    extrude(housing, amount=A)
    drafted_faces = oval_flanged_bearing_unit.faces().filter_by(Axis.Z, reverse=True)
    draft(drafted_faces, Plane.XY, 4)
    fillet(oval_flanged_bearing_unit.edges(), 1)
    with Locations(oval_flanged_bearing_unit.faces().sort_by(Axis.Z)[-1]):
        CounterBoreHole(14 / 2, 47 / 2, 14)
    with Locations(*bolt_centers):
        Hole(5)

oval_flanged_bearing_unit.part.color = Color(0x4C6377)

show(oval_flanged_bearing_unit)
# [End]
