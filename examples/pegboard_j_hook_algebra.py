# [Code]

from build123d import *
from ocp_vscode import show

pegd = 6.35 + 0.1  # mm ~0.25inch
c2c = 25.4  # mm 1.0inch
arcd = 7.2
both = 10
topx = 6
midx = 8
maind = 0.82 * pegd
midd = 1.0 * pegd
hookd = 23
hookx = 10
splitz = maind / 2 - 0.1
topangs = 70

l1 = Line((-both, 0), (c2c - arcd / 2 - 0.5, 0))
l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=arcd / 2, arc_size=topangs)
l3 = PolarLine(
    start=l2 @ 1,
    length=topx,
    direction=l2 % 1,
)
l4 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=arcd / 2, arc_size=-topangs)
l5 = PolarLine(
    start=l4 @ 1,
    length=topx,
    direction=l4 % 1,
)
l6 = JernArc(start=l1 @ 0, tangent=(l1 % 0).reverse(), radius=hookd / 2, arc_size=170)
l7 = PolarLine(
    start=l6 @ 1,
    length=hookx,
    direction=l6 % 1,
)
sprof = Curve() + (l1, l2, l3, l4, l5, l6, l7)
wire = Wire(sprof.edges())  #  TODO sprof.wires() fails
mainp = sweep(Plane.YZ * Circle(radius=maind / 2), path=wire)

stub = Line((0, 0), (0, midx + maind / 2))
mainp += sweep(Plane.XZ * Circle(radius=midd / 2), path=stub)


# splits help keep the object 3d printable by reducing overhang
mainp = split(mainp, Plane(origin=(0, 0, -splitz)))
mainp = split(mainp, Plane(origin=(0, 0, splitz)), keep=Keep.BOTTOM)

show(mainp)
# [End]
