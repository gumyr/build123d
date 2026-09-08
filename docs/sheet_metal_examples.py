"""

name: sheet_metal_examples.py
by:   Gabriel Jesus
date: July 21st 2026

desc:

    This is the build123d sheet metal tutorial python script. It is pulled
    into sphinx docs by tutorial_sheet_metal.rst, and is run as part of the
    docs example test suite to keep the tutorial code truthful.

license:

    Copyright 2026 Gabriel Jesus

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

from build123d import *

with BuildSheet(thickness=1, bend_radius=2) as box:
    with BuildSketch():
        Rectangle(100, 60)

    bottom = box.faces().sort_by(Axis.Z)[0]
    flange(
        bottom.edges().filter_by(GeomType.LINE),
        length=20,
        gap1=3.1,
        gap2=3.1,
    )

    long_walls = box.faces().filter_by(Axis.Y).sort_by(Axis.Y)
    rims = [
        long_walls[0].edges().sort_by(Axis.Z)[-1],
        long_walls[-1].edges().sort_by(Axis.Z)[-1],
    ]
    hem(rims, hem_type=HemType.OPEN, width=6, opening=2)

assert box.sheet.is_valid
