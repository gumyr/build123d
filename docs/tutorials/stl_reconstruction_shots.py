"""
Rendered pictures for the STL reconstruction tutorial

name: stl_reconstruction_shots.py
by:   Gumyr
date: November 12th 2026

desc:
    Makes the pictures of the "Rebuilding a part from an STL" tutorial with
    tcv_screenshots, which drives OCP CAD Viewer in a headless browser. It
    is not part of the tutorial. Run it from this directory, after
    ``pip install tcv_screenshots``:

        tcv_screenshots -f stl_reconstruction_shots.py -o assets/stl_reconstruction

    It runs ``stl_reconstruction.py`` and photographs what each step of that
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
    from build123d import Compound, GeomType, thicken
    from tcv_screenshots import get_screenshots, screenshot

    script = Path(__file__).with_name("stl_reconstruction.py")
    with contextlib.redirect_stdout(io.StringIO()):
        made = runpy.run_path(str(script))
    mesh, quarter, rebuilt = made["mesh"], made["quarter"], made["rebuilt"]
    primitives, leftovers = made["primitives"], made["leftovers"]

    grey, blue, orange, red = "#b8c0c8", "#5b8fc7", "#e8a13a", "#c0392b"
    view = dict(
        position=(90, -110, 80),
        target=(0, 12, 0),
        ortho=False,
        tools=False,
        glass=True,
        cad_width=900,
        height=600,
    )
    close = dict(view, position=(70, -80, 70), target=(12, 12, 6))

    screenshot(mesh, name="stl_mesh", colors=[grey], zoom=1.0, **view)
    screenshot(quarter, name="stl_quarter", colors=[grey], zoom=1.0, **close)

    def both_sides(faces):
        """The viewer colours only the front of a face and shows its back in
        grey, so for the pictures each face is given a hair of thickness."""
        return Compound([thicken(face, amount=0.03, both=True) for face in faces])

    planes = both_sides(f for f in primitives if f.geom_type == GeomType.PLANE)
    cylinders = both_sides(f for f in primitives if f.geom_type == GeomType.CYLINDER)
    screenshot(
        planes,
        cylinders,
        name="stl_primitives",
        colors=[blue, orange],
        zoom=1.0,
        **close,
    )
    screenshot(
        planes,
        cylinders,
        both_sides(leftovers),
        name="stl_leftovers",
        colors=[blue, orange, red],
        alphas=[0.25, 0.25, 1.0],
        zoom=1.0,
        **close,
    )
    screenshot(rebuilt, name="stl_rebuilt", colors=[blue], zoom=1.0, **view)

    return get_screenshots()
