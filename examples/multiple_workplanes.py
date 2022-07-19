from build123d.build123d_common import *
from build123d.build_part import *

with BuildPart() as obj:
    Box(5, 5, 1)
    WorkplanesFromFaces(*obj.faces().filter_by_axis(Axis.Z))
    Sphere(1.8, mode=Mode.SUBTRACT)

if "show_object" in locals():
    show_object(obj.part)

