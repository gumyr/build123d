from build123d import *
from build123d.part_operations import *
import alg123d as ad

l1 = Line((0, 0), (12, 0))
l2 = ad.RadiusArc(l1 @ 1, (15, 20), 50)
l3 = Spline(l2 @ 1, (22, 40), (20, 50), tangents=(l2 % 1, (-0.75, 1)))
l4 = ad.RadiusArc(l3 @ 1, l3 @ 1 + Vector(0, 5), 5)
l5 = Spline(
    l4 @ 1,
    l4 @ 1 + Vector(2.5, 2.5),
    l4 @ 1 + Vector(0, 5),
    tangents=(l4 % 1, (-1, 0)),
)
outline = l1 + l2 + l3 + l4 + l5
outline += Polyline(
    l5 @ 1,
    l5 @ 1 + Vector(0, 1),
    (0, (l5 @ 1).Y + 1),
    l1 @ 0,
)
profile = ad.make_face(outline)
vase = revolve(profile, axis=Axis.Y)
vase = ad.shell(vase, openings=vase.faces().max(Axis.Y), amount=-1)

top_edges = vase.edges(GeomType.CIRCLE).filter_by_position(Axis.Y, 60, 62)
vase = ad.fillet(vase, top_edges, radius=0.25)

vase = ad.fillet(vase, vase.edges().sort_by(Axis.Y)[0], radius=0.5)

if "show_object" in locals():
    show_object(vase, name="vase")
