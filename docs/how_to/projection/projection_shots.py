"""
Rendered pictures for the projection how-to guides

name: projection_shots.py
by:   Gumyr
date: November 15th 2026

desc:
    Makes the rendered pictures of the Projection section with
    tcv_screenshots, which drives OCP CAD Viewer in a headless browser. It is
    not part of the guides. Run it from this directory, after
    ``pip install tcv_screenshots``:

        tcv_screenshots -f projection_shots.py -o ../assets/projection

    The line drawings of the section are made by ``projection_examples.py``.
    The pictures here are the ones a line drawing cannot make clear: a
    projection passes through a part, and what it lands on is easier to see
    on shaded surfaces with the projected sketch and its path drawn in.

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

import re
from pathlib import Path


def example(name: str) -> dict:
    """Run one marked example of projection_examples.py and return what it
    defines, so the pictures show exactly what the page's code makes."""
    source = Path(__file__).with_name("projection_examples.py").read_text()
    marker = re.escape(f"# [{name}]")
    block = re.search(f"{marker}\\n(.*?){marker}", source, re.DOTALL).group(1)
    made: dict = {}
    exec("from build123d import *\n" + block, made)  # pylint: disable=exec-used
    return made


def main():
    """Request the screenshots; tcv_screenshots renders what this returns."""
    from tcv_screenshots import get_screenshots, screenshot

    from build123d import Hit, Pos, Vector, extrude, project_to_shape

    made = example("shape_hits_algebra")
    stepped, label = made["stepped"], made["label"]

    # the sketch being projected, and the path it takes: straight down,
    # through the part and out the other side
    sheet = label.face()
    beam = extrude(label, amount=-40)

    grey, blue, light, orange = "#9aa3ad", "#1e4fa3", "#6fa8ff", "#f08c00"
    size = dict(ortho=True, tools=False, glass=True, cad_width=560, height=520)
    view = dict(position=(95, -125, 62), target=(0, 0, 8), zoom=1.15)

    for hit in (Hit.ALL, Hit.NEAREST, Hit.FARTHEST, Hit.VISIBLE):
        kept = project_to_shape(label, target=stepped, direction=(0, 0, -1), hit=hit)
        # The projected faces lie exactly in the surface of the part, where
        # the two would flicker against each other when drawn. Each is lifted
        # a hair off the surface, to the side that is outside the part.
        landed = []
        for face in kept.faces():
            above = face.center() + Vector(0, 0, 0.1)
            lift = -0.04 if stepped.is_inside(above) else 0.04
            lifted = face.moved(Pos(0, 0, lift))
            # the viewer shades the back of a face darkly, so each is turned
            # to face the camera, which looks down from above
            landed.append(lifted if lifted.normal_at().Z > 0 else -lifted)
        screenshot(
            stepped,
            beam,
            sheet,
            *landed,
            name=f"shape_hits_{hit.name.lower()}",
            colors=[grey, light, blue] + [orange] * len(landed),
            alphas=[0.45, 0.18, 1.0] + [1.0] * len(landed),
            **size,
            **view,
        )

    return get_screenshots()
