from build123d import *


with BuildPart() as blocks:
    with Locations((-1, -1, 0)):
        Box(1, 2, 1, align=(Align.CENTER, Align.MIN, Align.MIN))
    Box(1, 1, 2, align=(Align.CENTER, Align.MIN, Align.MIN))
    with Locations((1, -1, 0)):
        Box(1, 2, 1, align=(Align.CENTER, Align.MIN, Align.MIN))
    bottom_edges = blocks.edges().filter_by_position(
        Axis.Z, 0, 1, inclusive=(True, False)
    )
    Chamfer(*bottom_edges, length=0.1)
    top_edges = blocks.edges().filter_by_position(Axis.Z, 1, 2, inclusive=(False, True))
    Chamfer(*top_edges, length=0.1)


if "show_object" in locals():
    show_object(blocks.part.wrapped)
