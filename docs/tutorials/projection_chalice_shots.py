"""
Rendered pictures for the embossed chalice tutorial

name: projection_chalice_shots.py
by:   Gumyr
date: November 14th 2026

desc:
    Makes the pictures of the "An embossed chalice" tutorial with
    tcv_screenshots, which drives OCP CAD Viewer in a headless browser. It is
    not part of the tutorial. Run it from this directory, after
    ``pip install tcv_screenshots``:

        tcv_screenshots -f projection_chalice_shots.py -o assets/projection_chalice

    It runs ``projection_chalice.py`` and photographs what each step of that
    script makes, so the pictures always show what the tutorial builds.

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

    from build123d import Plane

    with contextlib.redirect_stdout(io.StringIO()):
        made = runpy.run_path(str(Path(__file__).with_name("projection_chalice.py")))
    outside, rim, inside, axis, foot, profile = (
        made[name] for name in "outside rim inside axis foot profile".split()
    )
    cup, footprint, band, on_cup, chalice = (
        made[name] for name in "cup footprint band on_cup chalice".split()
    )

    gold, red, grey = "#c9a227", "#c0392b", "#5d6d7e"
    size = dict(ortho=False, tools=False, glass=True, cad_width=900, height=600)
    front = dict(position=(25, -300, 20), target=(25, 0, 20))
    plan = dict(position=(0, 0, 300), target=(0, 0, 0), up="Y")
    above = dict(position=(160, -260, 190), target=(0, 0, 15))
    below = dict(position=(170, -280, -90), target=(0, 0, 30))

    def shot(name, *shapes, view, zoom=1.0, **kwargs):
        screenshot(*shapes, name=name, zoom=zoom, **size, **view, **kwargs)

    # the lines are drawn flat; the profile made from them stands on Plane.XZ
    lines = [Plane.XZ * line for line in (outside, rim, inside, axis, foot)]
    shot(
        "chalice_profile",
        profile,
        *lines,
        colors=[gold] + ["black"] * 5,
        alphas=[0.5] + [1] * 5,
        view=front,
        zoom=0.85,
    )
    shot("chalice_cup", cup, colors=[gold], view=above, zoom=1.1)
    shot(
        "chalice_footprint",
        cup,
        footprint,
        colors=[gold, grey],
        alphas=[0.35, 1],
        view=above,
        zoom=1.1,
    )
    shot(
        "chalice_band",
        footprint,
        band,
        colors=[grey, red],
        alphas=[0.4, 1],
        view=plan,
    )
    shot(
        "chalice_project",
        cup,
        band,
        on_cup,
        colors=[gold, grey, red],
        alphas=[0.5, 1, 1],
        view=below,
        zoom=1.1,
    )
    shot("chalice_finished", chalice, colors=[gold], view=below, zoom=1.1)

    return get_screenshots()
