import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

with BuildSketch() as along_wire:
    Rectangle(48, 16, align=Align.MIN)
    Rectangle(16, 48, align=Align.MIN)
    Rectangle(32, 32, align=Align.MIN)

    for i, v in enumerate(along_wire.vertices()):
        fillet(v, i + 1)

show(along_wire)
save_screenshot(os.path.join(filedir, "sort_not_along_wire.png"))


with BuildSketch() as along_wire:
    Rectangle(48, 16, align=Align.MIN)
    Rectangle(16, 48, align=Align.MIN)
    Rectangle(32, 32, align=Align.MIN)

    sorted_verts = along_wire.vertices().sort_by(along_wire.wire())
    for i, v in enumerate(sorted_verts):
        fillet(v, i + 1)

show(along_wire)
save_screenshot(os.path.join(filedir, "sort_along_wire.png"))