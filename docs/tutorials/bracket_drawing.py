"""
A technical drawing tutorial

name: bracket_drawing.py
by:   Gumyr
date: November 12th 2026

desc:
    Every code example in the "A technical drawing" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also writes the SVG pictures the page
    embeds. The tutorial draws the bracket of "Designing a Part", so this
    script first runs ``tutorial_design.py``, which sits beside it, and takes
    the bracket from it. Run it from its own directory; the pictures are
    written to ``assets/bracket_drawing``.

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

import contextlib
import io
import runpy
import types
from pathlib import Path

# Carry on from the end of "Designing a Part": run its script and take the
# bracket and its dimensions from it.
with contextlib.redirect_stdout(io.StringIO()):
    design = runpy.run_path(str(Path(__file__).with_name("tutorial_design.py")))
globals().update({k: v for k, v in design.items() if not k.startswith("_")})
length, width, height = design["length"], design["width"], design["height"]

OUTPUT = Path("assets/bracket_drawing")
OUTPUT.mkdir(parents=True, exist_ok=True)

# In builder mode the tutorial's ``bracket`` is the BuildPart, in algebra mode
# it is the part itself. Both of the one-line versions of step 1 are run.
bracket = types.SimpleNamespace(part=design["builder_result"])
# [part_builder]
from datetime import date

part = bracket.part
# [part_builder]
builder_part = part

bracket = design["bracket"]
# [part_algebra]
from datetime import date

part = bracket
# [part_algebra]
assert abs(builder_part.volume - part.volume) < 1e-6


def render(name, visible=(), hidden=(), notes=()):
    """Write the sheet as it stands at one step of the tutorial."""
    step = ExportSVG(unit=Unit.MM, margin=5)
    step.add_layer("Sheet", fill_color="black", line_weight=0.1)
    step.add_layer("Visible", line_weight=0.35)
    step.add_layer(
        "Hidden",
        line_color="gray",
        line_type=LineType.ISO_DOT,
        line_weight=0.18,
    )
    step.add_shape(sheet, layer="Sheet")
    if notes:
        step.add_shape(list(notes), layer="Sheet")
    if visible:
        step.add_shape(list(visible), layer="Visible")
    if hidden:
        step.add_shape(list(hidden), layer="Hidden")
    step.write(OUTPUT / f"sheet_{name}.svg")


# ---------------------------------------------------------------------------
# Step 2: the sheet
# ---------------------------------------------------------------------------
# [sheet]
sheet = TechnicalDrawing(
    designed_by="build123d",
    design_date=date(2026, 11, 12),
    page_size=PageSize.A5,
    title="Bracket",
    sub_title="Units: mm",
    drawing_number="BD-1",
    sheet_number=1,
    drawing_scale=1,
    nominal_text_size=6,
    line_width=0.25,
)
# [sheet]
render("blank")

# ---------------------------------------------------------------------------
# Step 3: a view
# ---------------------------------------------------------------------------
# [view]
center = part.bounding_box().center()
visible, hidden = part.drawing_view(center + (0, -1000, 0), look_at=center)
# [view]
assert all(isinstance(edge, Edge) for edge in visible + hidden)
view_size = Curve(visible).bounding_box().size
assert abs(view_size.X - length) < 1e-5 and abs(view_size.Y - width) < 1e-5
render("view", visible, hidden)


# ---------------------------------------------------------------------------
# Step 4: put the view in its place
# ---------------------------------------------------------------------------
# [place]
def view(direction, position, up=(0, 0, 1)):
    """The visible and the hidden edges of the part, seen from a direction
    and moved to a position on the sheet"""
    viewpoint = center + Vector(direction) * 1000
    visible, hidden = part.drawing_view(viewpoint, up, look_at=center)
    place = Pos(*position)
    return (
        ShapeList(place * edge for edge in visible),
        ShapeList(place * edge for edge in hidden),
    )


front, front_hidden = view((0, -1, 0), position=(-50, -8))
# [place]
render("front", front, front_hidden)

# ---------------------------------------------------------------------------
# Step 5: the other views
# ---------------------------------------------------------------------------
# [views]
top, top_hidden = view((0, 0, 1), position=(-50, 34), up=(0, 1, 0))
right, right_hidden = view((1, 0, 0), position=(12, -8))
iso, iso_hidden = view((1, -1, 1), position=(58, 34))
# [views]
outlines = front + top + right + iso
hidden_lines = front_hidden + top_hidden + right_hidden
render("views", outlines, hidden_lines)

# The views line up: top above front, right beside it.
front_box, top_box = Curve(front).bounding_box(), Curve(top).bounding_box()
right_box = Curve(right).bounding_box()
assert abs(front_box.center().X - top_box.center().X) < 1e-5
assert abs(front_box.center().Y - right_box.center().Y) < 1e-5
assert abs(right_box.size.X - height) < 1e-5 and abs(top_box.size.Y - height) < 1e-5

# ---------------------------------------------------------------------------
# Step 6: dimensions
# ---------------------------------------------------------------------------
# [dimensions]
draft = Draft(
    font_size=3,
    decimal_precision=0,
    display_units=False,
    arrow_length=2,
    extension_gap=1,
    line_width=0.25,
)

front_box = Curve(front).bounding_box()
top_box = Curve(top).bounding_box()

length_dimension = ExtensionLine(
    [front_box.min, (front_box.max.X, front_box.min.Y)], offset=(0, -8), draft=draft
)
width_dimension = ExtensionLine(
    [front_box.min, (front_box.min.X, front_box.max.Y)], offset=(-8, 0), draft=draft
)
height_dimension = ExtensionLine(
    [(top_box.max.X, top_box.min.Y), top_box.max], offset=(8, 0), draft=draft
)
dimensions = [length_dimension, width_dimension, height_dimension]
# [dimensions]
assert [d.label_str for d in dimensions] == [str(length), str(width), str(height)]
render("dimensions", outlines, hidden_lines, dimensions)

# ---------------------------------------------------------------------------
# Step 7: labels
# ---------------------------------------------------------------------------
# [labels]
right_box = Curve(right).bounding_box()

labels = [
    Pos(box.center().X, box.max.Y + 4) * Text(name, 3.5)
    for name, box in (("Front", front_box), ("Top", top_box), ("Right", right_box))
]
# [labels]
render("labels", outlines, hidden_lines, dimensions + labels)

# ---------------------------------------------------------------------------
# Step 8: export
# ---------------------------------------------------------------------------
# [export]
exporter = ExportSVG(unit=Unit.MM, margin=5)
exporter.add_layer("Sheet", fill_color="black", line_weight=0.1)
exporter.add_layer("Visible", line_weight=0.35)
exporter.add_layer(
    "Hidden", line_color="gray", line_type=LineType.ISO_DOT, line_weight=0.18
)

exporter.add_shape(sheet, layer="Sheet")
exporter.add_shape(dimensions + labels, layer="Sheet")
exporter.add_shape(front + top + right + iso, layer="Visible")
exporter.add_shape(front_hidden + top_hidden + right_hidden, layer="Hidden")
exporter.write("bracket_drawing.svg")
# [export]

# Keep the finished sheet with the other pictures of the page.
Path("bracket_drawing.svg").replace(OUTPUT / "sheet_finished.svg")
