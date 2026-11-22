"""
Rendered pictures for the joints how-to guide

name: joints_shots.py
by:   Gumyr
date: November 15th 2026

desc:
    Makes the pictures of the pipe and rod end examples of the "Joints"
    how-to guide with tcv_screenshots, which drives OCP CAD Viewer in a
    headless browser. It is not part of the guide. Run it from this
    directory, after ``pip install tcv_screenshots``:

        tcv_screenshots -f joints_shots.py -o assets/joints

    It runs ``rigid_joints_pipe.py`` and ``rod_end.py`` and photographs what
    they make, with the joints drawn, so the pictures always show what the
    page's code builds.

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

import runpy
from pathlib import Path


def main():
    """Request the screenshots; tcv_screenshots renders what this returns."""
    from tcv_screenshots import get_screenshots, screenshot

    here = Path(__file__).parent
    size = dict(ortho=False, tools=False, glass=True, cad_width=900, height=600)

    made = runpy.run_path(str(here / "rigid_joints_pipe.py"))
    screenshot(
        made["pipe"],
        made["flange_inlet"],
        made["flange_outlet"],
        name="rigid_joints_pipe",
        colors=["#9aa3ad", "#c9a227", "#c9a227"],
        render_joints=True,
        position=(250, -900, 520),
        target=(300, 0, 150),
        zoom=1.35,
        **size,
    )

    made = runpy.run_path(str(here / "rod_end.py"))
    screenshot(
        made["rod_end"],
        made["ball"],
        name="rod_end",
        colors=["#9aa3ad", "#a9c8ea"],
        position=(45, -60, 45),
        target=(0, -8, 0),
        zoom=1.5,
        **size,
    )

    return get_screenshots()
