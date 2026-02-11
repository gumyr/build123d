from copy import copy

from build123d import *
from tcv_screenshots import save_model


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

save_model(without, "group_axis_without")
save_model(part, "group_axis_with")