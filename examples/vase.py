"""

name: vase.py
by:   Gumyr
date: July 15th 2022

desc:

    This example demonstrates revolving a sketch, shelling and selecting edges
    by position range and type for fillets.

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

from cadquery import Vector
from build123d import common as bc, generic as bg, part as bp, sketch as bs, line as bl


with bp.BuildPart() as vase:
    with bs.BuildSketch() as profile:
        with bl.BuildLine() as outline:
            l1 = bl.Line((0, 0), (12, 0))
            l2 = bl.RadiusArc(l1 @ 1, (15, 20), 50)
            l3 = bl.Spline(l2 @ 1, (22, 40), (20, 50), tangents=(l2 % 1, (-0.75, 1)))
            l4 = bl.RadiusArc(l3 @ 1, l3 @ 1 + Vector(0, 5), 5)
            l5 = bl.Spline(
                l4 @ 1,
                l4 @ 1 + Vector(2.5, 2.5),
                l4 @ 1 + Vector(0, 5),
                tangents=(l4 % 1, (-1, 0)),
            )
            bl.Polyline(
                l5 @ 1,
                l5 @ 1 + Vector(0, 1),
                (0, (l5 @ 1).y + 1),
                l1 @ 0,
            )
        bs.BuildFace()
    bp.Revolve()
    bp.Shell(vase.faces().filter_by_axis(bg.Axis.Y)[-1], thickness=-1)
    top_edges = (
        vase.edges().filter_by_position(bg.Axis.Y, 60, 62).filter_by_type(bc.Type.CIRCLE)
    )
    # debug(top_edges)
    bg.Fillet(*top_edges, radius=0.25)
    bg.Fillet(vase.edges().sort_by(bc.SortBy.Y)[0], radius=0.5)


if "show_object" in locals():
    # show_object(outline.line, name="outline")
    # show_object(profile.sketch, name="profile")
    show_object(vase.part, name="vase")
