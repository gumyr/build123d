from build123d import *
from build123d.algebra import Rot, Pos

try:
    from ocp_vscode import show_object, show
except:
    ...

# %%

with BuildSketch() as sk:
    x = Rectangle(1, 2)

show(sk)

# %%

b = Rectangle(1, 2)
c = Circle(0.1)
d = b - [
    c @ Pos(y=0.6),
    c @ Pos(y=-0.6),
]

show(d, transparent=True)

# %%

with BuildSketch() as sk:
    Rectangle(1, 2)
    with Locations(Location((0, 0.6, 0)), Location((0, -0.6, 0))):
        Circle(0.1, mode=Mode.SUBTRACT)
        Circle(0.1, mode=Mode.SUBTRACT)

show(sk)

# %%

with BuildSketch() as sk2:
    Rectangle(1, 2) + Rectangle(0.5, 5)

show(sk2)

# %%

b = Rectangle(1, 2)
with BuildSketch() as sk:
    b

# bp.part is None
show(sk)

# %%

b = Rectangle(1, 2) + Circle(0.75)

with BuildSketch() as sk:
    Add(b)
    Circle(0.1, mode=Mode.SUBTRACT)

c = sk.sketch - Circle(0.2) @ Pos(0, 0.5)

show(c)

# %%

b = Rectangle(1, 2)
c = Circle(0.1)
d = b @ Plane.XZ - [
    c @ (Plane.XZ * Pos(y=0.6)),
    c @ (Plane.XZ * Pos(y=-0.6)),
    c @ Plane.XZ,
]

show(d, transparent=True)

# %%

b = Rectangle(1, 2) @ Plane.XZ
c = Circle(0.1) @ Plane.XZ
d = b - [
    c * Pos(z=0.6),  # note c is on XZ plane, but this is relative
    c * Pos(z=-0.6),  # to XY plane, i.e. c @ Plane.XY * Pos(z=0.6)
    c,
]

show(d, axes=True, axes0=True)


0  # %%

b = Rectangle(1, 2) @ (Plane.ZX * Pos(1, 2, 3))
c = Circle(0.1) @ (Plane.ZX * Pos(1, 2, 3))
d = b - [
    c * Pos(x=0.6),
    c * Pos(x=-0.6),
    c,
]

show(d, axes=True, axes0=True)


# %%
