from build_part import *
from build_sketch import *

with BuildPart() as pipes:
    Box(10, 10, 10, rotation=(10, 20, 30))
    WorkplanesFromFaces(*pipes.faces(), replace=True)
    with BuildSketch() as pipe:
        Circle(4)
    Extrude(-5, mode=Mode.SUBTRACTION)
    with BuildSketch() as pipe:
        Circle(4.5)
        Circle(4, mode=Mode.SUBTRACTION)
    Extrude(10)
    FilletPart(*pipes.edges(Select.LAST), radius=0.2)

if "show_object" in locals():
    show_object(pipes.part, name="intersecting pipes")
