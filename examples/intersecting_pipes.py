from build123d.build123d_common import *
from build123d.build_sketch import *
from build123d.build_part import *

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
