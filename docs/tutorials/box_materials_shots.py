"""
Rendered pictures for the hinged box materials tutorial

name: box_materials_shots.py
by:   Gumyr
date: November 12th 2026

desc:
    Makes the rendered pictures of the "Materials for the hinged box"
    tutorial with tcv_screenshots, which drives OCP CAD Viewer's Studio mode
    in a headless browser. It is not part of the tutorial. Run it from this
    directory, after ``pip install tcv_screenshots``:

        tcv_screenshots -f box_materials_shots.py -o assets/box_materials

    It runs ``box_materials.py`` and photographs the box that script ends
    with, so the pictures always show what the tutorial builds.

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
    from tcv_screenshots import StudioBackground, UiTab, get_screenshots, screenshot

    with contextlib.redirect_stdout(io.StringIO()):
        tutorial = runpy.run_path(str(Path(__file__).with_name("box_materials.py")))
    hinged_box = tutorial["hinged_box"]

    studio = dict(
        tab=UiTab.STUDIO,
        studio_background=StudioBackground.GRADIENT,
        ortho=False,
        tools=False,
        glass=True,
        cad_width=1000,
        height=750,
    )
    screenshot(
        hinged_box,
        name="materials_box",
        position=(-620, -520, 470),
        target=(-20, 0, 80),
        **studio,
    )
    screenshot(
        hinged_box,
        name="materials_hinge",
        position=(-380, -170, 260),
        target=(-150, 0, 110),
        zoom=4.6,
        **studio,
    )
    return get_screenshots()
