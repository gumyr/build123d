from itertools import product
from tcv_screenshots import save_model
from build123d import *

# from-origin-algebra
from ocp_vscode import ColorMap, show

boxes = ShapeList(
    Box(1, 1, 1).scale(0.75 if (i, j) == (1, 2) else 0.25).translate((i, j, 0))
    for i, j in product(range(-3, 4), repeat=2)
)

boxes = boxes.sort_by_distance(Vertex())
show(*boxes, colors=ColorMap.listed(len(boxes)))
# from-origin-algebra-end

for b, c in zip(boxes, ColorMap.listed(len(boxes))):
    b.color = c
save_model([*boxes], "sort_distance_from_origin")

# from-largest-algebra
boxes = boxes.sort_by_distance(boxes.sort_by(Solid.volume).last)
show(*boxes, colors=ColorMap.listed(len(boxes)))
# from-largest-algebra-end

for b, c in zip(boxes, ColorMap.listed(len(boxes))):
    b.color = c
save_model([*boxes], "sort_distance_from_largest")