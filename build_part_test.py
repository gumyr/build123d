"""
TODO:

"""
from build_part import *
from build_sketch import *

with BuildPart(workplane=Plane.named("XZ")) as rail:
    with BuildSketch() as din:
        PushPointsToSketch((0, 0.5))
        Rectangle(35, 1)
        PushPointsToSketch((0, 7.5 / 2))
        Rectangle(27, 7.5)
        PushPointsToSketch((0, 6.5 / 2))
        Rectangle(25, 6.5, mode=Mode.SUBTRACTION)
        inside_vertices = (
            din.vertices()
            .filter_by_position(Axis.Y, 0.0, 7.5, inclusive=(False, False))
            .filter_by_position(Axis.X, -17.5, 17.5, inclusive=(False, False))
        )
        FilletSketch(*inside_vertices, radius=0.8)
        outside_vertices = list(
            filter(
                lambda v: (v.Y == 0.0 or v.Y == 7.5) and -17.5 < v.X < 17.5,
                din.vertices(),
            )
        )
        FilletSketch(*outside_vertices, radius=1.8)
    Extrude(1000)
    top = rail.faces().filter_by_normal(Axis.Z).sort_by(SortBy.Z)[-1]
    FacesToWorkplanes(top, replace=True)
    with BuildSketch() as slots:
        RectangularArrayToSketch(0, 25, 1, 39)
        SlotOverall(15, 6.2, rotation=90)
    slot_holes = Extrude(-20, mode=Mode.SUBTRACTION)

with BuildPart() as cube:
    PushPointsToPart((-5, -5, -5))
    Box(10, 10, 10, rotation=(10, 20, 30))
    FacesToWorkplanes(*cube.faces(), replace=True)
    with BuildSketch() as pipe:
        Circle(4)
    Extrude(-5, mode=Mode.SUBTRACTION)
    with BuildSketch() as pipe:
        Circle(4.5)
        Circle(4, mode=Mode.SUBTRACTION)
    Extrude(10)
    FilletPart(*cube.edges(Select.LAST), radius=0.2)

with BuildPart() as s:
    Sphere(5)
with BuildPart() as c:
    Cone(20, 10, 20)
with BuildPart() as cyl:
    Cylinder(10, 30)
with BuildPart() as t:
    Torus(50, 10)
with BuildPart() as w:
    Wedge(10, 10, 10, 5, 5, 20, 20)

if "show_object" in locals():
    show_object(rail.part, name="rail")
    show_object(cube.part, name="cube")
    show_object(s.part, name="sphere")
    show_object(c.part, name="cone")
    show_object(cyl.part, name="cylinder")
    show_object(t.part, name="torus")
    show_object(w.part, name="wedge")
