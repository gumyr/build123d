from build123d import *

with BuildPart() as simple_washer:
    Cylinder(3, 2)
    Hole(1)

with BuildPart() as washer:
    with Locations((10, 0)):
        Cylinder(3, 2)
        with Workplanes(washer.faces().sort_by(SortBy.Z)[-1]):
            Hole(1)


if "show_object" in locals():
    show_object(simple_washer.part, name="simple_washer")
    show_object(washer.part, name="washer")
