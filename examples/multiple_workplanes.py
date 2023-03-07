from build123d import *

with BuildPart() as obj:
    Box(5, 5, 1)
    with BuildPart(*obj.faces().filter_by(Axis.Z), mode=Mode.SUBTRACT):
        Sphere(1.8)

assert abs(obj.part.volume - 15.083039190168236) < 1e-3

if "show_object" in locals():
    show_object(obj.part)
