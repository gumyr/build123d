from copy import copy

from build123d import *
from tcv_screenshots import save_model


models = []

selectors = [solids, vertices, edges, faces]
line = Line((-9, -9), (9, 9))
for i, selector in enumerate(selectors):
    u = i / (len(selectors) - 1)
    with BuildPart() as part:
        with Locations(line @ u):
            Box(5, 5, 1)
            Cylinder(2, 5)
            models.extend([part, *selector()])

save_model(models, "selectors_select_all")
models = []

for i, selector in enumerate(selectors[1:4]):
    u = i / (len(selectors) - 1)
    with BuildPart() as part:
        with Locations(line @ u):
            Box(5, 5, 1)
            Cylinder(2, 5)
            models.extend([part, *selector(Select.LAST)])

save_model(models, "selectors_select_last")
models = []

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

    save_model([part_copy, *edges, b, c], "selectors_select_new", {"alphas": [.5, 1, .5, 1]})

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

    save_model([part_copy, *edges, b, c], "selectors_select_new_none", {"alphas": [.5, 1, .5, 1]})

with BuildPart() as part:
    with Locations(line @ 1/3):
        Box(5, 5, 1)
        Cylinder(2, 5)
        edges = part.edges().filter_by(lambda a: a.length == 1)
        fillet(edges, 1)
        models.extend([part, *part.edges(Select.NEW)])

with BuildPart() as part:
    with Locations(line @ 2/3):
        Box(5, 5, 1)
        Cylinder(2, 5)
        edges = part.edges().filter_by(lambda a: a.length == 1)
        fillet(edges, 1)
        models.extend([part, *part.edges(Select.LAST)])

save_model(models, "selectors_select_new_fillet")
save_model([part, *part.vertices().sort_by(Axis.X)[-4:]], "operators_sort_x")
save_model([part, *part.faces().group_by(SortBy.AREA)[0].edges()], "operators_group_area")

faces = part.faces().filter_by(lambda f: f.normal_at() == Vector(0, 0, 1))
save_model([part, *[f.translate(f.normal_at() * 0.01) for f in faces]], "operators_filter_z_normal")

box = Box(5, 5, 1)
circle = Cylinder(2, 5)
part = box + circle
edges = new_edges(box, circle, combined=part)
save_model([part, *edges], "selectors_new_edges")