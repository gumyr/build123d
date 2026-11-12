"""
A heart token tutorial

name: surface_heart_token.py
by:   Gumyr
date: November 12th 2026

desc:
    Every code example in the "A heart token" surface modelling tutorial
    lives here, between pairs of ``# [name]`` markers that the page includes
    with ``literalinclude``. The surfaces are made with the direct API and
    are the same in both modes; the frame of the last step is written twice,
    in builder and in algebra mode, and the two are checked against each
    other. The rendered pictures on the page are made from this script by
    ``surface_heart_token_shots.py``.

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

# [setup]
from build123d import *

edge_height = 1
crown_height = 1.5
frame_width, frame_height = 2, 4
# [setup]

# ---------------------------------------------------------------------------
# Step 2: half of the outline
# ---------------------------------------------------------------------------
# [outline]
side = JernArc((0, 0), (1, 1.4), 40, -17)
lobe = JernArc(side @ 1, side % 1, 4.5, 175)
center_line = Line((0, 0), (0, 20))
dip = PolarLine(lobe @ 1, length=center_line, direction=lobe % 1)
# [outline]
assert abs((dip @ 1).X) < 1e-6 and (dip @ 1).Y > 0

# ---------------------------------------------------------------------------
# Step 3: the ridge down the middle
# ---------------------------------------------------------------------------
# [ridge]
middle = (dip @ 1 + side @ 0) / 2
ridge = ThreePointArc(dip @ 1, middle + (0, 0, crown_height), side @ 0)
boundary = Wire([side, lobe, dip, ridge])
# [ridge]
assert boundary.is_closed

# ---------------------------------------------------------------------------
# Step 4: a surface
# ---------------------------------------------------------------------------
# [surface]
crown = lobe.arc_center + (0, 0, crown_height)
top_right = Pos(Z=edge_height / 2) * -Face.make_surface(boundary, [crown])
# [surface]
assert top_right.geom_type != GeomType.PLANE
assert top_right.normal_at(top_right.center()).Z > 0

# ---------------------------------------------------------------------------
# Step 5: mirror it
# ---------------------------------------------------------------------------
# [mirror]
top_left = top_right.mirror(Plane.YZ)
bottom_right = top_right.mirror(Plane.XY)
bottom_left = -top_left.mirror(Plane.XY)
# [mirror]

# ---------------------------------------------------------------------------
# Step 6: the sides
# ---------------------------------------------------------------------------
# [sides]
rim = Wire([dip, lobe, side])
left_side = Pos(Z=-edge_height / 2) * Shell.extrude(rim, (0, 0, edge_height))
right_side = left_side.mirror(Plane.YZ)
# [sides]

# ---------------------------------------------------------------------------
# Step 7: from faces to a solid
# ---------------------------------------------------------------------------
# [solid]
skin = Shell([top_right, top_left, bottom_right, bottom_left, left_side, right_side])
heart = Solid(skin)

print(heart.is_valid, heart.volume)
# [solid]
assert heart.is_valid and abs(heart.volume - 555.82) < 0.01

# ---------------------------------------------------------------------------
# Step 8: a frame
# ---------------------------------------------------------------------------
# [frame_builder]
with BuildPart() as token:
    with BuildSketch() as plan:
        with BuildLine():
            insert(side)
            insert(lobe)
            insert(dip)
            Line(dip @ 1, side @ 0)
        make_face()
        mirror(about=Plane.YZ)
        heart_outline = plan.sketch
        offset(amount=frame_width, kind=Kind.INTERSECTION)
        insert(heart_outline, mode=Mode.SUBTRACT)
    extrude(amount=frame_height / 2, both=True)
    insert(heart)
token.part.color = "Red"
# [frame_builder]
builder_result = token.part

# [frame_algebra]
heart_outline = make_face([side, lobe, dip, Line(dip @ 1, side @ 0)])
heart_outline += mirror(heart_outline, about=Plane.YZ)
ring = offset(heart_outline, amount=frame_width, kind=Kind.INTERSECTION)
ring -= heart_outline

token = extrude(ring, amount=frame_height / 2, both=True) + heart
token.color = "Red"
# [frame_algebra]

assert abs(builder_result.volume - token.volume) < 1e-6
assert len(builder_result.faces()) == len(token.faces())
assert token.is_valid and len(token.solids()) == 1
assert abs(token.volume - 1080.97) < 0.01  # as the token this tutorial replaces
