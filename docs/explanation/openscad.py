"""
Coming from OpenSCAD documentation examples

name: openscad.py
by:   Gumyr
date: November 15th 2026

desc:
    The build123d examples of the "Coming from OpenSCAD" page, between pairs
    of ``# [name]`` markers that the page includes with ``literalinclude``.
    Each is written in builder and in algebra mode and the two are checked
    against each other.

license:

    Copyright 2026 Gumyr

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

# pylint: disable=redefined-outer-name, wildcard-import, unused-wildcard-import

from build123d import *

# ---------------------------------------------------------------------------
# the angle iron
# ---------------------------------------------------------------------------

# [angle_iron]
with BuildPart() as angle_iron:
    with BuildSketch() as profile:
        Rectangle(3 * CM, 4 * MM, align=Align.MIN)
        Rectangle(4 * MM, 3 * CM, align=Align.MIN)
    extrude(amount=10 * CM)
    fillet(angle_iron.edges().filter_by(Convexity.CONCAVE), 5 * MM)
# [angle_iron]

builder_result = angle_iron.part

# [angle_iron_algebra]
profile = Rectangle(3 * CM, 4 * MM, align=Align.MIN)
profile += Rectangle(4 * MM, 3 * CM, align=Align.MIN)
angle_iron = extrude(profile, 10 * CM)
angle_iron = fillet(angle_iron.edges().filter_by(Convexity.CONCAVE), 5 * MM)
# [angle_iron_algebra]

assert abs(builder_result.volume - angle_iron.volume) < 1e-6
assert (angle_iron.bounding_box().size - Vector(30, 30, 100)).length < 1e-6
# the fillet is a true cylinder, not facets
assert len(angle_iron.faces().filter_by(GeomType.CYLINDER)) == 1
# and adds material in the corner: more than the two plain legs
assert angle_iron.volume > (30 * 4 + 26 * 4) * 100

# ---------------------------------------------------------------------------
# the same part the OpenSCAD way: solids added and taken away
# ---------------------------------------------------------------------------

# [csg]
with BuildPart() as angle_iron_csg:
    Box(30, 100, 30, align=Align.MIN)
    with Locations((4, 0, 4)):
        Box(26, 100, 26, align=Align.MIN, mode=Mode.SUBTRACT)
# [csg]

builder_result = angle_iron_csg.part

# [csg_algebra]
angle_iron_csg = Box(30, 100, 30, align=Align.MIN)
angle_iron_csg -= Pos(4, 0, 4) * Box(26, 100, 26, align=Align.MIN)
# [csg_algebra]

assert abs(builder_result.volume - angle_iron_csg.volume) < 1e-6
assert abs(angle_iron_csg.volume - (30 * 4 + 26 * 4) * 100) < 1e-6
