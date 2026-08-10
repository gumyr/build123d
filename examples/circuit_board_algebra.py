"""
for details see `circuit_board.py`
"""
# [Imports]
from itertools import product
from build123d import *
from ocp_vscode import show

# [Parameters]
pcb_length = 70 * MM
pcb_width = 30 * MM
pcb_height = 3 * MM

# [Code]
x_coords = product(range(65 // 5), (-15, -10, 10, 15))
y_coords = product((30, 35), range(30 // 5 - 1))

pcb = Rectangle(pcb_length, pcb_width)
pcb -= [Pos(i * 5 - 30, y) * Circle(1) for i, y in x_coords]
pcb -= [Pos(x, i * 5 - 10) * Circle(1) for x, i in y_coords]
pcb -= [loc * Circle(2) for loc in GridLocations(60, 20, 2, 2)]

pcb = extrude(pcb, pcb_height)

show(pcb)
# [End]