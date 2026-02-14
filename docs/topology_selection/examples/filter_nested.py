from copy import copy
from build123d import *
from tcv_screenshots import save_model

# setup-builder
with BuildPart() as part:
    Cylinder(15, 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildSketch():
        RectangleRounded(10, 10, 2.5)
    extrude(amount=15)

    with BuildSketch():
        Circle(2.5)
        Rectangle(4, 5, mode=Mode.INTERSECT)
    extrude(amount=15, mode=Mode.SUBTRACT)

    with GridLocations(20, 0, 2, 1):
        Hole(3.5 / 2)
    # setup-builder-end

    before = copy(part)

    # nested-builder
    faces = part.faces().filter_by(
        lambda f: len(f.inner_wires().edges().filter_by(GeomType.LINE)) == 2
    )
    wires = faces.wires().filter_by(
        lambda w: any(e.geom_type == GeomType.LINE for e in w.edges())
    )
    chamfer(wires.edges(), 0.5)
    # nested-builder-end

location = Location((-25, -25))
b = before.part.moved(location)
f = [f.moved(location) for f in faces]

save_model([b, *f, part], "filter_nested")