from itertools import product
from build123d import *
from build123d.part_operations import *

x_coords = product(range(65 // 5), (-15, -10, 10, 15))
y_coords = product((30, 35), range(30 // 5 - 1))

pcb = Rectangle(70, 30)
pcb -= [Pos(i * 5 - 30, y) * Circle(1) for i, y in x_coords]
pcb -= [Pos(x, i * 5 - 10) * Circle(1) for x, i in y_coords]
pcb -= [loc * Circle(2) for loc in GridLocations(60, 20, 2, 2)]

pcb = extrude(pcb, 3)

if "show_object" in locals():
    show(pcb)
