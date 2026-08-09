import os
from copy import copy

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

with BuildPart() as fins:
    with GridLocations(4, 6, 4, 4):
        Box(2, 3, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))

with BuildPart() as part:
    Box(34, 48, 5, align=(Align.CENTER, Align.CENTER, Align.MAX))
    with GridLocations(20, 27, 2, 2):
        add(fins)

    without = copy(part)

    target = part.edges().group_by(Axis.Z)[-1].group_by(Edge.length)[-1]
    fillet(target, .75)

show(without)
save_screenshot(os.path.join(filedir, "group_axis_without.png"))

show(part)
save_screenshot(os.path.join(filedir, "group_axis_with.png"))