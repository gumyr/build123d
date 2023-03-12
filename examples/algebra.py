from build123d import *
from build123d.algebra import Rot, Pos

try:
    from ocp_vscode import show_object, show
except:
    ...

# %%

b = Box(1, 2, 3)
c = Cylinder(0.1, 4)
d = b - [
    c @ (Plane.XZ * Pos(y=1)),
    c @ (Plane.XZ * Pos(y=-1)),
    c @ Plane.YZ,
]

show(d, transparent=True)

# %%

with BuildPart() as bp:
    Box(1, 2, 3)
    with Locations(Plane.XZ):
        with Locations(Location((0, 1, 0)), Location((0, -1, 0))):
            Cylinder(0.1, 4, mode=Mode.SUBTRACT)
    with Locations(Plane.YZ):
        Cylinder(0.1, 4, mode=Mode.SUBTRACT)

show(bp, transparent=True)

# %%
