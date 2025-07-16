import os
from itertools import product

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

boxes = ShapeList(
    Box(1, 1, 1).scale(0.75 if (i, j) == (1, 2) else 0.25).translate((i, j, 0))
    for i, j in product(range(-3, 4), repeat=2)
)

boxes = boxes.sort_by_distance(Vertex())
show(*boxes, colors=ColorMap.listed(len(boxes)))
save_screenshot(os.path.join(filedir, "sort_distance_from_origin.png"))

boxes = boxes.sort_by_distance(boxes.sort_by(Solid.volume).last)
show(*boxes, colors=ColorMap.listed(len(boxes)))
save_screenshot(os.path.join(filedir, "sort_distance_from_largest.png"))