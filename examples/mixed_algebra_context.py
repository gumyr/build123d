from build123d import *
from ocp_vscode import show_object

# Mix context and algebra api for parts

b = Box(1, 2, 3) + Cylinder(0.75, 2.5)

with BuildPart() as bp:
    add(b)
    Cylinder(0.4, 6, mode=Mode.SUBTRACT)

c = bp.part - Plane.YZ * Cylinder(0.2, 6)

# Mix context and algebra api for sketches

r = Rectangle(1, 2) + Circle(0.75)

with BuildSketch() as bs:
    add(r)
    Circle(0.4, mode=Mode.SUBTRACT)

d = bs.sketch - Pos(0, 1) * Circle(0.2)

# Mix context and algebra api for sketches

l1 = Line((-1, 0), (1, 1)) + Line((1, 1), (2, 4))

with BuildLine() as bl:
    add(l1)
    Line((2, 4), (-1, 1))

e = bl.line + ThreePointArc((-1, 0), (-1.5, 0.5), (-1, 1))

show_object(Pos(0, -2, 0) * c, "part")
show_object(Pos(0, 2, 0) * d, "sketch")
show_object(Pos(0, 0, 2) * e, "curve")
