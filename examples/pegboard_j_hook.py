"""
name: pegboard_j_hook.py
by:   jdegenstein
date: November 17th 2022
desc:
    This example creates a model of j-shaped pegboard hook commonly used
    for organization of tools in garages.

license:
    Copyright 2022 jdegenstein
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

pegd = 6.35 + 0.1  # mm ~0.25inch
c2c = 25.4  # mm 1.0inch
arcd = 7.2
both = 10
topx = 6
midx = 8
maind = 0.82 * pegd
midd = 1.0 * pegd
hookd = 23
hookx = 10
splitz = maind / 2 - 0.1
topangs = 70

with BuildPart() as mainp:
    with BuildLine(mode=Mode.PRIVATE) as sprof:
        l1 = Line((-both, 0), (c2c - arcd / 2 - 0.5, 0))
        l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=arcd / 2, arc_size=topangs)
        l3 = PolarLine(
            start=l2 @ 1,
            length=topx,
            direction=l2 % 1,
        )
        l4 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=arcd / 2, arc_size=-topangs)
        l5 = PolarLine(
            start=l4 @ 1,
            length=topx,
            direction=l4 % 1,
        )
        l6 = JernArc(
            start=l1 @ 0, tangent=(l1 % 0).reverse(), radius=hookd / 2, arc_size=170
        )
        l7 = PolarLine(
            start=l6 @ 1,
            length=hookx,
            direction=l6 % 1,
        )
    with BuildSketch(Plane.YZ):
        Circle(radius=maind / 2)
    sweep(path=sprof.wires()[0])
    with BuildLine(mode=Mode.PRIVATE) as stub:
        l7 = Line((0, 0), (0, midx + maind / 2))
    with BuildSketch(Plane.XZ):
        Circle(radius=midd / 2)
    sweep(path=stub.wires()[0])
    # splits help keep the object 3d printable by reducing overhang
    split(bisect_by=Plane(origin=(0, 0, -splitz)))
    split(bisect_by=Plane(origin=(0, 0, splitz)), keep=Keep.BOTTOM)

show(mainp)
# [End]
