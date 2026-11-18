"""
Rendered pictures for the Spitfire wing tutorial

name: surface_spitfire_wing_shots.py
by:   Gumyr
date: November 12th 2026

desc:
    Makes the pictures of the "A Spitfire wing" tutorial with
    tcv_screenshots, which drives OCP CAD Viewer in a headless browser. It
    is not part of the tutorial. Run it from this directory, after
    ``pip install tcv_screenshots``:

        tcv_screenshots -f surface_spitfire_wing_shots.py -o assets/surface_spitfire_wing

    It runs ``surface_spitfire_wing.py`` and photographs what each step of
    that script makes, so the pictures always show what the tutorial builds.

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

    script = Path(__file__).with_name("surface_spitfire_wing.py")
    with contextlib.redirect_stdout(io.StringIO()):
        made = runpy.run_path(str(script))
    leading_edge, trailing_edge = made["leading_edge"], made["trailing_edge"]
    airfoil_root, airfoil_tip = made["airfoil_root"], made["airfoil_tip"]
    wing_surface, wing_root, wing = (
        made["wing_surface"],
        made["wing_root"],
        made["wing"],
    )

    blue, red = "#99a3b9", "#c0392b"
    view = dict(
        position=(-4500, -7000, 4500),
        target=(2600, 300, 0),
        zoom=1.3,
        ortho=False,
        tools=False,
        glass=True,
        cad_width=1000,
        height=560,
    )

    def shot(name, *shapes, colors):
        screenshot(*shapes, name=name, colors=colors, **view)

    guides = [leading_edge, trailing_edge]
    shot("wing_guides", *guides, colors=["black"] * 2)
    shot(
        "wing_airfoils",
        *guides,
        airfoil_root,
        airfoil_tip,
        colors=["black"] * 2 + [red] * 2,
    )
    shot("wing_surface", wing_surface, colors=[blue])
    shot("wing_root", wing_surface, wing_root, colors=[blue, red])
    shot("wing_finished", wing, colors=[blue])

    # The rotating viewer at the top of the page shows docs/_static/spitfire_wing.glb.
    # That file is kept in the repository and is not rewritten here, because
    # every new copy of a binary file stays in the history. If the shape of
    # the wing changes, regenerate it once with:
    # export_gltf(wing, "../_static/spitfire_wing.glb", binary=True,
    #             linear_deflection=0.1, angular_deflection=1)

    return get_screenshots()
