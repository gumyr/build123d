from copy import copy
import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

selectors = [solids, vertices, edges, faces]
line = Line((-9, -9), (9, 9))
for i, selector in enumerate(selectors):
    u = i / (len(selectors) - 1)
    with BuildPart() as part:
        with Locations(line @ u):
            Box(5, 5, 1)
            Cylinder(2, 5)
            show_object([part, selector()])

save_screenshot(os.path.join(filedir, "selectors_select_all.png"))
reset_show()

for i, selector in enumerate(selectors[1:4]):
    u = i / (len(selectors) - 1)
    with BuildPart() as part:
        with Locations(line @ u):
            Box(5, 5, 1)
            Cylinder(2, 5)
            show_object([part, selector(Select.LAST)])

save_screenshot(os.path.join(filedir, "selectors_select_last.png"))
reset_show()

with BuildPart() as part:
    with Locations(line @ 1/3):
        Box(5, 5, 1)
        Cylinder(2, 5)
        edges = part.edges(Select.NEW)
        part_copy = copy(part)

    with Locations(line @ 2/3):
        b = Box(5, 5, 1)
        c = Cylinder(2, 5)
        c.color = Color("DarkTurquoise")

    show(part_copy, edges, b, c, alphas=[.5, 1, .5, 1])

save_screenshot(os.path.join(filedir, "selectors_select_new.png"))
reset_show()

with BuildPart() as part:
    with Locations(line @ 1/3):
        Box(5, 5, 1, align=(Align.CENTER, Align.CENTER, Align.MAX))
        Cylinder(2, 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        edges = part.edges(Select.NEW)
        part_copy = copy(part)

    with Locations(line @ 2/3):
        b = Box(5, 5, 1, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.PRIVATE)
        c = Cylinder(2, 2, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.PRIVATE)
        c.color = Color("DarkTurquoise")
    show(part_copy, edges, b, c, alphas=[.5, 1, .5, 1])

save_screenshot(os.path.join(filedir, "selectors_select_new_none.png"))
reset_show()

with BuildPart() as part:
    with Locations(line @ 1/3):
        Box(5, 5, 1)
        Cylinder(2, 5)
        edges = part.edges().filter_by(lambda a: a.length == 1)
        fillet(edges, 1)
        show_object([part, part.edges(Select.NEW)])

with BuildPart() as part:
    with Locations(line @ 2/3):
        Box(5, 5, 1)
        Cylinder(2, 5)
        edges = part.edges().filter_by(lambda a: a.length == 1)
        fillet(edges, 1)
        show_object([part, part.edges(Select.LAST)])

save_screenshot(os.path.join(filedir, "selectors_select_new_fillet.png"))

show(part, part.vertices().sort_by(Axis.X)[-4:])
save_screenshot(os.path.join(filedir, "operators_sort_x.png"))

show(part, part.faces().group_by(SortBy.AREA)[0].edges())
save_screenshot(os.path.join(filedir, "operators_group_area.png"))

faces = part.faces().filter_by(lambda f: f.normal_at() == Vector(0, 0, 1))
show(part, [f.translate(f.normal_at() * 0.01) for f in faces])
save_screenshot(os.path.join(filedir, "operators_filter_z_normal.png"))

box = Box(5, 5, 1)
circle = Cylinder(2, 5)
part = box + circle
edges = new_edges(box, circle, combined=part)
show(part, edges)
save_screenshot(os.path.join(filedir, "selectors_new_edges.png"))