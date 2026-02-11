from build123d import *
from tcv_screenshots import save_model


with BuildSketch() as along_wire:
    Rectangle(48, 16, align=Align.MIN)
    Rectangle(16, 48, align=Align.MIN)
    Rectangle(32, 32, align=Align.MIN)

    for i, v in enumerate(along_wire.vertices()):
        fillet(v, i + 1)

save_model(along_wire, "sort_not_along_wire")


with BuildSketch() as along_wire:
    Rectangle(48, 16, align=Align.MIN)
    Rectangle(16, 48, align=Align.MIN)
    Rectangle(32, 32, align=Align.MIN)

    sorted_verts = along_wire.vertices().sort_by(along_wire.wire())
    for i, v in enumerate(sorted_verts):
        fillet(v, i + 1)

save_model(along_wire, "sort_along_wire")