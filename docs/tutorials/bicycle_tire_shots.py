"""
Rendered pictures for the bicycle tire tutorial

name: bicycle_tire_shots.py
by:   Gumyr
date: November 14th 2026

desc:
    Makes the pictures of the "A bicycle tire" tutorial with tcv_screenshots,
    which drives OCP CAD Viewer in a headless browser. It is not part of the
    tutorial. Run it from this directory, after
    ``pip install tcv_screenshots``:

        tcv_screenshots -f bicycle_tire_shots.py -o assets/bicycle_tire

    It runs ``bicycle_tire.py`` and photographs what each step of that script
    makes, so the pictures always show what the tutorial builds. The tread
    and the letters are small beside the wheel, so most pictures show a
    short length of the tire, cut out with a box.

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
from pathlib import Path


def main():
    """Request the screenshots; tcv_screenshots renders what this returns."""
    from tcv_screenshots import get_screenshots, screenshot

    from build123d import Box, Plane, Pos, Rot, thicken

    with contextlib.redirect_stdout(io.StringIO()):
        made = runpy.run_path(str(Path(__file__).with_name("bicycle_tire.py")))
    names = "smooth_tire tread_pattern wrapped_pattern tread path label letters"
    smooth_tire, tread_pattern, wrapped_pattern, tread, path, label, letters = (
        made[name] for name in names.split()
    )
    embossed_label = made["embossed_label"]
    top = made["wheel_diameter"] / 2

    # The lettering is an eighth of a turn from the top of the wheel. The
    # pictures of it are taken with everything turned to bring it to the top.
    turn = Rot(X=45)
    crop = Pos(0, 0, top - 22) * Box(80, 250, 60)
    tire_top = (turn * smooth_tire) & crop
    blocks = [block for unit in tread for block in unit.solids()]
    tread_top = [
        block for block in (turn * b for b in blocks) if crop.is_inside(block.center())
    ]
    label_top, letters_top, embossed_top = (
        turn * shape for shape in (label, letters, embossed_label)
    )
    path_top = turn * (Plane.ZY.offset(made["label_offset"]) * path)

    # a short length of the tire where the tread unit is wrapped on
    first = wrapped_pattern[0].center()
    low = Pos(0, first.Y + 22, first.Z + 4) * Box(60, 60, 60)
    tire_low = smooth_tire & low
    tread_low = [block for block in blocks if low.is_inside(block.center())]
    # the wrapped faces lie in the surface; a thin solid of each shows up better
    wrapped = [thicken(face, amount=0.3) for face in wrapped_pattern]

    rubber, red, pale = "#7d838c", "#c0392b", "#e6e8eb"
    size = dict(ortho=False, tools=False, glass=True, cad_width=900, height=600)
    spot = tread_pattern.bounding_box().center()
    plan = dict(position=(spot.X, spot.Y, 300), target=tuple(spot), up="Y")
    wheel = dict(position=(900, -700, 500), target=(0, 0, 0))
    road = dict(
        position=(90, first.Y - 150, first.Z + 70), target=(0, first.Y + 6, first.Z + 2)
    )
    beside = dict(position=(-230, 110, top + 60), target=(-10, 0, top - 22))
    sidewall = dict(position=(-200, 60, top + 40), target=(-18, 0, top - 22))
    both = dict(position=(-190, 120, top + 140), target=(-6, 0, top - 16))
    zooms = {
        id(plan): 0.8,
        id(wheel): 1.3,
        id(road): 10.0,
        id(beside): 4.0,
        id(sidewall): 4.4,
        id(both): 4.2,
    }

    def shot(name, *shapes, view, colors):
        screenshot(
            *shapes, name=name, colors=colors, zoom=zooms[id(view)], **size, **view
        )

    shot("tire_whole", smooth_tire, view=wheel, colors=[rubber])
    shot("tire_pattern", tread_pattern, view=plan, colors=["black"])
    shot(
        "tire_wrapped",
        tire_low,
        *wrapped,
        view=road,
        colors=[rubber] + [red] * len(wrapped),
    )
    shot(
        "tire_tread",
        tire_low,
        *tread_low,
        view=road,
        colors=[rubber] * (1 + len(tread_low)),
    )
    shot(
        "tire_label",
        tire_top,
        label_top,
        path_top,
        view=beside,
        colors=[rubber, red, "black"],
    )
    shot(
        "tire_projected",
        tire_top,
        label_top,
        letters_top,
        view=beside,
        colors=[rubber, "#d9a8a1", red],
    )
    shot(
        "tire_embossed",
        tire_top,
        embossed_top,
        view=sidewall,
        colors=[rubber, red],
    )
    shot(
        "tire_finished",
        tire_top,
        embossed_top,
        *tread_top,
        view=both,
        colors=[rubber, pale] + [rubber] * len(tread_top),
    )

    return get_screenshots()
