"""

name: handle.py
by:   Gumyr
date: July 29th 2022

desc:

    This example demonstrates multisection sweep creating a drawer handle.

license:

    Copyright 2022 Gumyr

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

# [Code]

from build123d import *
from ocp_vscode import show_object

segment_count = 6

with BuildPart() as handle:
    # Create a path for the sweep along the handle - added to pending_edges
    with BuildLine() as handle_center_line:
        Spline(
            (-10, 0, 0),
            (0, 0, 5),
            (10, 0, 0),
            tangents=((0, 0, 1), (0, 0, -1)),
            tangent_scalars=(1.5, 1.5),
        )

    # Create the cross sections - added to pending_faces
    for i in range(segment_count + 1):
        with BuildSketch(handle_center_line.line ^ (i / segment_count)) as section:
            if i % segment_count == 0:
                Circle(1)
            else:
                Rectangle(1.25, 3)
                fillet(section.vertices(), radius=0.2)
    # Record the sections for display
    sections = handle.pending_faces

    # Create the handle by sweeping along the path
    sweep(multisection=True)

assert abs(handle.part.volume - 94.77361455046953) < 1e-3

show_object(handle_center_line.line, name="handle_center_line")
for i, section in enumerate(sections):
    show_object(section, name="section" + str(i))
show_object(handle.part, name="handle", options=dict(alpha=0.6))
# [End]
