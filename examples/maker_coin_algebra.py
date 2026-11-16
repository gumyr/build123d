# [Code]
from build123d import *
from ocp_vscode import *

# Coin Parameters
diameter, thickness = 50 * MM, 10 * MM

# On XZ plane draw the profile of half the coin
l1 = Polyline((0, thickness * 0.6), (0, 0), ((diameter - thickness) / 2, 0))
l2 = JernArc(
    start=l1 @ 1, tangent=l1 % 1, radius=thickness / 2, arc_size=300
)  # extend the arc beyond the intersection but not closed
l3 = DoubleTangentArc(l1 @ 0, tangent=(1, 0), other=l2)
l2 = l2.trim(0, l2.param_at_point(l3 @ 1))  # keep the arc up to where l3 meets it
profile = Plane.XZ * make_face([l1, l2, l3])  # make it a 2D shape
blank = revolve(profile, Axis.Z)  # revolve 360°

# Pattern the detents around the coin
detents = Sketch() + PolarLocations(radius=(diameter + 5) / 2, count=8) * Circle(
    thickness * 1.4 / 2
)
maker_coin = blank - extrude(detents, amount=thickness)  # cut away the detents

# fillet the edges the cut made
maker_coin = fillet(new_edges(blank, combined=maker_coin), 2)

# Add an embossed label
label = Plane.XY.offset(thickness) * Text("OS", font_size=15)  # above coin
on_coin = project_to_shape(
    label, maker_coin, direction=(0, 0, -1), hit=Hit.NEAREST
)  # label on top of coin
maker_coin -= extrude(on_coin, amount=-thickness / 5, dir=(0, 0, 1))  # emboss label

show(maker_coin)
# [End]
