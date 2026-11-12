"""
Rendered pictures for the heart token tutorial

name: surface_heart_token_shots.py
by:   Gumyr
date: November 12th 2026

desc:
    Makes the pictures of the "A heart token" tutorial with tcv_screenshots,
    which drives OCP CAD Viewer in a headless browser. It is not part of the tutorial. Run it from this
    directory, after ``pip install tcv_screenshots``:

        tcv_screenshots -f surface_heart_token_shots.py -o assets/surface_heart_token

    It runs ``surface_heart_token.py`` and photographs what each step of that
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

    with contextlib.redirect_stdout(io.StringIO()):
        made = runpy.run_path(str(Path(__file__).with_name("surface_heart_token.py")))
    names = (
        "side lobe dip ridge top_right top_left bottom_right bottom_left "
        "left_side right_side heart token"
    )
    side, lobe, dip, ridge, top_right, top_left, bottom_right, bottom_left = (
        made[name] for name in names.split()[:8]
    )
    left_side, right_side, heart, token = (made[name] for name in names.split()[8:])

    red, grey = "#c0392b", "#9aa5b1"
    view = dict(
        position=(10, -32, 30),
        target=(0, 7, 0),
        ortho=False,
        tools=False,
        glass=True,
        cad_width=900,
        height=600,
    )

    def shot(name, *shapes, colors, zoom=1.4):
        screenshot(*shapes, name=name, colors=colors, zoom=zoom, **view)

    shot("heart_outline", side, lobe, dip, colors=["black"] * 3, zoom=0.9)
    shot("heart_ridge", side, lobe, dip, ridge, colors=["black"] * 3 + [red], zoom=0.9)
    shot("heart_surface", top_right, colors=[red], zoom=0.9)
    tops_and_bottoms = [top_right, top_left, bottom_right, bottom_left]
    shot("heart_mirror", *tops_and_bottoms, colors=[red] * 4)
    shot("heart_sides", left_side, right_side, colors=[grey] * 2)
    shot("heart_solid", heart, colors=[red])
    shot("heart_finished", token, colors=[red])

    # The rotating viewer at the top of the page shows docs/_static/heart_token.glb.
    # That file is kept in the repository and is not rewritten here, because
    # every new copy of a binary file stays in the history. If the shape of
    # the token changes, regenerate it once with:
    # export_gltf(token, "../_static/heart_token.glb", binary=True)

    return get_screenshots()
