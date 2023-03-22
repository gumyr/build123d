from build123d import *

try:
    from ocp_vscode import show_object, show
except:
    ...
# %%

with BuildPart() as bp:
    x = Box(1, 2, 1)

if "show" in locals():
    show(bp)

# %%

b = Box(1, 2, 3)
c = Cylinder(0.1, 4)
d = b - [
    Plane.XZ * Pos(y=1) * c,
    Plane.XZ * Pos(y=-1) * c,
    Plane.YZ * c,
]

if "show" in locals():
    show(d, transparent=True)

# %%

with BuildPart() as bp:
    Box(1, 2, 3)
    with Locations(Plane.XZ):
        with Locations(Location((0, 1, 0)), Location((0, -1, 0))):
            Cylinder(0.1, 4, mode=Mode.SUBTRACT)
    with Locations(Plane.YZ):
        Cylinder(0.1, 4, mode=Mode.SUBTRACT)

if "show" in locals():
    show(bp)

# %%

with BuildPart() as bp2:
    Box(1, 2, 3) + Box(0.5, 0.5, 4)

if "show" in locals():
    show(bp2)

# %%

b = Box(1, 2, 3)
with BuildPart() as bp:
    b

# bp.part is None
if "show" in locals():
    show(bp)

# %%

b = Box(1, 2, 3)
with BuildPart() as bp:
    Add(b)

if "show" in locals():
    show(bp)

# %%

b = Box(1, 2, 3) + Cylinder(0.75, 2.5)

with BuildPart() as bp:
    Add(b)
    Cylinder(0.4, 6, mode=Mode.SUBTRACT)

c = bp.part - Plane.YZ * Cylinder(0.2, 6)

if "show" in locals():
    show(c)

# %%
