"""
Rendered pictures for the key cap tutorial

name: key_cap_shots.py
by:   Gumyr
date: November 14th 2026

desc:
    Makes the pictures of the "A key cap" tutorial with tcv_screenshots,
    which drives OCP CAD Viewer in a headless browser. It is not part of the
    tutorial. Run it from this directory, after
    ``pip install tcv_screenshots``:

        tcv_screenshots -f key_cap_shots.py -o assets/key_cap

    It runs ``key_cap.py`` and photographs what each step of that script
    makes, so the pictures always show what the tutorial builds.

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
        made = runpy.run_path(str(Path(__file__).with_name("key_cap.py")))
    block, drafted, solid_cap, hollowed, shell, ribbed, key_cap = (
        made[name]
        for name in "block drafted solid_cap hollowed shell ribbed key_cap".split()
    )

    cream = "#e8e0cf"
    size = dict(ortho=False, tools=False, glass=True, cad_width=900, height=600)
    above = dict(position=(32, -48, 36), target=(0, 0, 4))
    below = dict(position=(30, -44, -30), target=(0, 0, 4))

    def shot(name, *shapes, view, colors=None, alphas=None, zoom=1.0):
        colors = colors or [cream] * len(shapes)
        kwargs = dict(alphas=alphas) if alphas else {}
        screenshot(
            *shapes, name=name, colors=colors, zoom=zoom, **size, **view, **kwargs
        )

    shot("keycap_block", block, view=above)
    shot("keycap_draft", drafted, view=above)
    shot("keycap_dish", solid_cap, view=above)
    shot("keycap_hollow", hollowed, view=below)
    shot("keycap_round", shell, view=above)
    shot("keycap_ribs", ribbed, view=below)
    shot("keycap_socket", key_cap, view=below)
    shot("keycap_finished", key_cap, view=above, alphas=[0.45])

    return get_screenshots()
