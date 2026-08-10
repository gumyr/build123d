"""
Create line type examples

name: line_types.py
by:   Gumyr
date: July 25th 2023

desc:
    This python module generates sample of all the available line types.

license:

    Copyright 2023 Gumyr

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

exporter = ExportSVG(scale=1)
exporter.add_layer(name="Text", fill_color=(0, 0, 0))
line_types = [l for l in LineType.__members__]
text_locs = Pos((100, 0, 0)) * GridLocations(0, 6, 1, len(line_types)).locations
line_locs = Pos((105, 0, 0)) * GridLocations(0, 6, 1, len(line_types)).locations
for line_type, text_loc, line_loc in zip(line_types, text_locs, line_locs):
    exporter.add_layer(name=line_type, line_type=getattr(LineType, line_type))
    exporter.add_shape(
        Compound.make_text(
            "LineType." + line_type,
            font_size=5,
            align=(Align.MAX, Align.CENTER),
        ).locate(text_loc),
        layer="Text",
    )
    exporter.add_shape(
        Edge.make_line((0, 0), (100, 0)).locate(line_loc), layer=line_type
    )
exporter.write("assets/line_types.svg")
