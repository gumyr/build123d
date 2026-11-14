"""
A Spitfire wing tutorial

name: surface_spitfire_wing.py
by:   Gumyr
date: November 12th 2026

desc:
    Every code example in the "A Spitfire wing" surface modelling tutorial
    lives here, between pairs of ``# [name]`` markers that the page includes
    with ``literalinclude``. It uses the direct API and is the same in
    builder and algebra mode. The rendered pictures on the page are made
    from this script by ``surface_spitfire_wing_shots.py``.

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

from pathlib import Path

# [setup]
from build123d import *

wing_span = 36 * FT + 10 * IN
wing_leading = 2.5 * FT
wing_trailing = wing_span / 4 - wing_leading
wing_leading_fraction = wing_leading / (wing_leading + wing_trailing)
wing_tip_section = wing_span / 2 - 1 * IN
# [setup]

# ---------------------------------------------------------------------------
# Step 2: the leading and trailing edges
# ---------------------------------------------------------------------------
# [guides]
leading_edge = EllipticalCenterArc(
    (0, 0), wing_span / 2, wing_leading, start_angle=270, arc_size=90
)
trailing_edge = EllipticalCenterArc(
    (0, 0), wing_span / 2, wing_trailing, start_angle=0, arc_size=90
)
# [guides]
assert (leading_edge @ 1 - trailing_edge @ 0).length < 1e-6  # they meet at the tip

# ---------------------------------------------------------------------------
# Step 3: how wide is the wing?
# ---------------------------------------------------------------------------
# [chords]
chords = []
for station in (0, wing_tip_section):
    across = Axis((station, 0, 0), (0, 1, 0))
    leading_point = leading_edge.intersect(across)[0]
    trailing_point = trailing_edge.intersect(across)[0]
    chords.append(trailing_point.Y - leading_point.Y)
root_chord, tip_chord = chords

print(f"{root_chord:.0f} mm at the root, {tip_chord:.0f} mm near the tip")
# [chords]
assert (
    abs(root_chord - (wing_leading + wing_trailing)) < 1e-6
    and 0 < tip_chord < root_chord
)

# ---------------------------------------------------------------------------
# Step 4: the airfoils
# ---------------------------------------------------------------------------
# [airfoils]
airfoil_root = Plane.YZ * scale(
    Airfoil("2213").move(Pos(-wing_leading_fraction, 0, 0)),
    root_chord,
    about=(0, 0, 0),
)
airfoil_tip = (
    Plane.YZ
    * Pos(Z=wing_tip_section)
    * scale(
        Airfoil("2205").move(Pos(-wing_leading_fraction, 0, 0)),
        tip_chord,
        about=(0, 0, 0),
    )
)
# [airfoils]

# ---------------------------------------------------------------------------
# Step 5: the Gordon surface
# ---------------------------------------------------------------------------
# [surface]
profiles = airfoil_root.edges() + airfoil_tip.edges()
profiles.append(leading_edge @ 1)
guides = [leading_edge, trailing_edge]

wing_surface = -Face.make_gordon_surface(profiles, guides)
# [surface]


def draw_grid() -> None:
    """Write the picture of the grid of step 5: the guides, the profiles and
    a label for each, seen from above and in front of the wing."""
    look_at = Vector(wing_span / 4, 0, 0)
    camera = look_at + (-4500, -7000, 4500)

    def flat(*shapes):
        """Edges as the camera sees them. Nothing hides a curve, so the
        visible and the hidden edges are both wanted."""
        visible, hidden = Curve(list(shapes)).drawing_view(camera, look_at=look_at)
        return visible + hidden

    def spot(point):
        """Where a point of the model falls in the picture."""
        return flat(Edge.make_line(point, Vector(point) + (0, 0, 0.001)))[0] @ 0

    def note(text, anchor, offset):
        """A label, and a thin line from it to what it names."""
        at = anchor + Vector(offset)
        side = Align.MIN if Vector(offset).X > 0 else Align.MAX
        label = Pos(at.X, at.Y) * Text(text, 130, align=(side, Align.CENTER))
        gap = Vector(60 if side == Align.MIN else -60, 0)
        return label, Edge.make_line(anchor, at - gap)

    tip = leading_edge @ 1
    notes = [
        note("guide: leading edge", spot(leading_edge @ 0.45), (300, -550)),
        note("guide: trailing edge", spot(trailing_edge @ 0.55), (-300, 500)),
        note(
            "profile: root airfoil", spot(airfoil_root.edges()[0] @ 0.5), (-400, -500)
        ),
        note("profile: tip airfoil", spot(airfoil_tip.edges()[0] @ 0.5), (350, -450)),
        note("profile: the tip, a point", spot(tip), (350, 250)),
    ]
    dot = Pos(*spot(tip)) * Circle(35)

    shown = flat(*guides) + flat(airfoil_root, airfoil_tip)
    size = Curve(shown + [edge for _, edge in notes]).bounding_box().size
    exporter = ExportSVG(scale=160 / size.X, margin=4)
    exporter.add_layer("Guides", line_color="steelblue", line_weight=0.6)
    exporter.add_layer("Profiles", line_color="firebrick", line_weight=0.6)
    exporter.add_layer("Dot", fill_color="firebrick", line_color="firebrick")
    exporter.add_layer("Text", fill_color="black", line_weight=0.05)
    exporter.add_layer("Leaders", line_color="gray", line_weight=0.15)
    exporter.add_shape(flat(*guides), layer="Guides")
    exporter.add_shape(flat(airfoil_root, airfoil_tip), layer="Profiles")
    exporter.add_shape(dot, layer="Dot")
    exporter.add_shape([label for label, _ in notes], layer="Text")
    exporter.add_shape([edge for _, edge in notes], layer="Leaders")
    output = Path("assets/surface_spitfire_wing")
    output.mkdir(parents=True, exist_ok=True)
    exporter.write(output / "wing_grid.svg")


draw_grid()

# ---------------------------------------------------------------------------
# Step 6: close the root and make a solid
# ---------------------------------------------------------------------------
# [solid]
root_outline = Wire(wing_surface.edges().filter_by(Edge.is_closed))
wing_root = -Face(root_outline)

wing = Solid(Shell([wing_surface, wing_root]))
wing.color = 0x99A3B9

print(wing.is_valid, f"{wing.volume / 1e9:.2f} cubic metres")
# [solid]
assert wing.is_valid
assert (
    abs(wing.volume / 1e9 - 1.9879945989) < 1e-6
)  # as the wing this tutorial replaces
