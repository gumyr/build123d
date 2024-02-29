from build123d import *
from ocp_vscode import show_object

# Extrude pending face by amount
simple = extrude(Text("O", font_size=10), amount=5)

# Extrude pending face in both directions by amount
both = extrude(Text("O", font_size=10), amount=5, both=True)

# Extrude multiple pending faces on multiple faces
multiple = Box(10, 10, 10)
faces = [
    Plane(face) * loc * Text("Ω", font_size=3)
    for face in multiple.faces()
    for loc in GridLocations(5, 5, 2, 2)
]
multiple += [extrude(face, amount=1) for face in faces]

# Non-planar surface
non_planar = Rot(90, 0, 0) * Cylinder(
    10, 20, align=(Align.CENTER, Align.MIN, Align.CENTER)
)
non_planar &= Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
non_planar = extrude(non_planar.faces().sort_by(Axis.Z).first, amount=2, dir=(0, 0, 1))
rad, rev = 3, 25

# Extrude last
circle = Pos(0, rev) * Circle(rad)
ex26_target = revolve(circle, Axis.X, revolution_arc=90)
ex26_target = ex26_target + mirror(ex26_target, Plane.XZ)

rect = Rectangle(rad, rev)

ex26 = extrude(rect, until=Until.LAST, target=ex26_target, clean=False)

# Extrude next
circle = Pos(0, rev) * Circle(rad)
ex27 = revolve(circle, Axis.X, revolution_arc=90)

circle2 = Plane.XZ * Pos(0, rev) * Circle(rad)
ex27 += revolve(circle2, Axis.X, revolution_arc=150)
rect = Plane.XY.offset(-60) * Rectangle(rad, rev + 25)
extrusion27 = extrude(rect, until=Until.NEXT, target=ex27, mode=Mode.ADD)


# Extrude next both
# ex28 = Rot(0, 90, 0) * Torus(25, 5)
# rect = Rectangle(rad, rev)
# extrusion28 = extrude(rect, until=Until.NEXT, target=ex28, both=True, clean=False)

show_object(simple.translate((-15, 0, 0)), name="simple pending extrude")
show_object(both.translate((20, 10, 0)), name="simple both")
show_object(multiple.translate((0, -20, 0)), name="multiple pending extrude")
show_object(non_planar.translate((20, -10, 0)), name="non planar")
show_object(
    ex26_target.translate((-40, 0, 0)),
    name="extrude until last target",
    options={"alpha": 0.8},
)
show_object(
    ex26.translate((-40, 0, 0)),
    name="extrude until last",
)
show_object(
    ex27.rotate(Axis.Z, 90).translate((0, 50, 0)),
    name="extrude until next target",
    options={"alpha": 0.8},
)
show_object(
    extrusion27.rotate(Axis.Z, 90).translate((0, 50, 0)),
    name="extrude until next",
)
# show_object(
#     ex28.rotate(Axis.Z, -90).translate((0, -50, 0)),
#     name="extrude until next both target",
#     options={"alpha": 0.8},
# )
# show_object(
#     extrusion28.rotate(Axis.Z, -90).translate((0, -50, 0)),
#     name="extrude until next both",
# )
