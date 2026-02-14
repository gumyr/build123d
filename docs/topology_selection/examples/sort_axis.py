from copy import copy
from tcv_screenshots import save_model
from build123d import *

# setup-builder
with BuildPart() as part:
    with BuildSketch(Plane.YZ) as profile:
        with BuildLine():
            l1 = FilletPolyline((16, 0), (32, 0), (32, 25), radius=12)
            l2 = FilletPolyline((16, 4), (28, 4), (28, 15), radius=8)
            Line(l1 @ 0, l2 @ 0)
            Polyline(l1 @ 1, l1 @ 1 - Vector(2, 0), l2 @ 1 + Vector(2, 0), l2 @ 1)
        make_face()
    extrude(amount=34)
    # setup-builder-end

    before = copy(part).part

    # sort-axis-builder
    face = part.faces().sort_by(Axis.X)[-1]
    edge = face.edges().sort_by(Axis.Y)[0]
    revolve(face, -Axis(edge), 90)
    # sort-axis-builder-end

f = face.translate(face.normal_at() * 0.01)
save_model([before, f, edge, part.part.translate((25, 33))], "sort_axis")
