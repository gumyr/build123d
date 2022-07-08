from build_part import *
from build_sketch import *

with BuildPart(workplane=Plane.named("XZ")) as rail:
    with BuildSketch() as din:
        PushPoints((0, 0.5))
        Rectangle(35, 1)
        PushPoints((0, 7.5 / 2))
        Rectangle(27, 7.5)
        PushPoints((0, 6.5 / 2))
        Rectangle(25, 6.5, mode=Mode.SUBTRACTION)
        inside_vertices = list(
            filter(
                lambda v: 7.5 > v.Y > 0 and -17.5 < v.X < 17.5,
                din.vertices(),
            )
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
    xy_faces = list(
        filter(lambda f: f.normalAt(f.Center()) == Vector(0, 0, 1), rail.faces())
    )
    top = sorted(xy_faces, key=lambda f: f.Center().z)[-1]
    rail.faces_to_workplanes(top, replace=True)
    with BuildSketch() as slots:
        RectangularArray(0, 25, 1, 39)
        SlotOverall(15, 6.2, 90)
    slot_holes = Extrude(-20, mode=Mode.SUBTRACTION)


if "show_object" in locals():
    show_object(rail.part, name="rail")
    show_object(slots.sketch, name="slots")
    show_object(slot_holes, name="slot_holes")
