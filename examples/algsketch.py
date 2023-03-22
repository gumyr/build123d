from build123d import *

try:
    from ocp_vscode import show_object, show
except:
    ...

# %%

with BuildSketch() as sk:
    x = Rectangle(1, 2)

if "show" in locals():
    show(sk)

# %%

b = Rectangle(1, 2)
c = Circle(0.1)
d = b - [
    Pos(y=0.6) * c,
    Pos(y=-0.6) * c,
]

if "show" in locals():
    show(d, transparent=True)

# %%

with BuildSketch() as sk:
    Rectangle(1, 2)
    with Locations(Location((0, 0.6, 0)), Location((0, -0.6, 0))):
        Circle(0.1, mode=Mode.SUBTRACT)
        Circle(0.1, mode=Mode.SUBTRACT)

if "show" in locals():
    show(sk)

# %%

with BuildSketch() as sk2:
    Rectangle(1, 2) + Rectangle(0.5, 5)

if "show" in locals():
    show(sk2)

# %%

b = Rectangle(1, 2)
with BuildSketch() as sk:
    b

# bp.part is None
if "show" in locals():
    show(sk)

# %%

b = Rectangle(1, 2) + Circle(0.75)

with BuildSketch() as sk:
    Add(b)
    Circle(0.1, mode=Mode.SUBTRACT)

c = sk.sketch - Pos(0, 0.5) * Circle(0.2)

if "show" in locals():
    show(c)

# %%

b = Rectangle(1, 2)
c = Circle(0.1)
d = Plane.XZ * b - [
    Plane.XZ * Pos(y=0.6) * c,
    Plane.XZ * Pos(y=-0.6) * c,
    Plane.XZ * c,
]

if "show" in locals():
    show(d, transparent=True)

# %%

b = Plane.XZ * Rectangle(1, 2)
c = Plane.XZ * Circle(0.1)
d = b - [
    Pos(z=0.6) * c,  # note c is on XZ plane, but this is relative
    Pos(z=-0.6) * c,  # to XY plane, i.e. c @ Plane.XY * Pos(z=0.6)
    c,
]

if "show" in locals():
    show(d, axes=True, axes0=True)


0  # %%

b = Plane.ZX * Pos(1, 2, 3) * Rectangle(1, 2)
c = Plane.ZX * Pos(1, 2, 3) * Circle(0.1)
d = b - [
    Pos(x=0.6) * c,
    Pos(x=-0.6) * c,
    c,
]

if "show" in locals():
    show(d, axes=True, axes0=True)


# %%
