"""
Too Tall Toby Party Pack 01-10 Light Cap
"""

from math import sqrt, asin, pi
from build123d import *
from ocp_vscode import *

densa = 7800 / 1e6  # carbon steel density g/mm^3
densb = 2700 / 1e6  # aluminum alloy
densc = 1020 / 1e6  # ABS

# The smaller cross-section is defined as having R40, height 46,
# and base width 84, so clearly it's not entirely a half-circle or
# similar; the base's extreme points need to connect via tangents
# to the R40 arc centered 6mm above the baseline.
#
# Compute the angle of the tangent line (working with the
# left/negativeX side, given symmetry) by observing the tangent
# point (T), the circle's center (O), and the baseline's edge (P)
# form a right triangle, so:

OT=40
OP=sqrt((-84/2)**2+(-6)**2)
TP=sqrt(OP**2-40**2)
OPT_degrees = asin(OT/OP) * 180/pi
# Correct for the fact that OP isn't horizontal.
OP_to_X_axis_degrees = asin(6/OP) * 180/pi
left_tangent_degrees = OPT_degrees + OP_to_X_axis_degrees
left_tangent_length = TP
with BuildPart() as outer:
    with BuildSketch(Plane.XZ) as sk:
        with BuildLine():
            l1 = PolarLine(start=(-84/2, 0), length=left_tangent_length, angle=left_tangent_degrees)
            l2 = TangentArc(l1@1, (0, 46), tangent=l1%1)
            l3 = offset(amount=-8, side=Side.RIGHT, closed=False, mode=Mode.ADD)
            l4 = Line(l1@0, l3@1)
            l5 = Line(l3@0, l2@1)
            l6 = Line(l3@0, (0, 46-16))
            l7 = IntersectingLine(start=l6@1, direction=(-1,0), other=l3)
        make_face()
    revolve(axis=Axis.Z)
sk = sk.sketch & Plane.XZ*Rectangle(1000, 1000, align=[Align.CENTER, Align.MIN])
positive_Z = Box(100, 100, 100, align=[Align.CENTER, Align.MIN, Align.MIN])
p = outer.part & positive_Z
cross_section = sk + mirror(sk, about=Plane.YZ)
p += extrude(cross_section, amount=50)
p += mirror(p, about=Plane.XZ.offset(50))
p += fillet(p.edges().filter_by(GeomType.LINE).filter_by(Axis.Y).group_by(Axis.Z)[-1], radius=8)
ppp0110 = p

got_mass = ppp0110.volume*densc
want_mass = 211.30
tolerance = 1
delta = abs(got_mass - want_mass)
print(f"Mass: {got_mass:0.1f} g")
assert delta < tolerance, f'{got_mass=}, {want_mass=}, {delta=}, {tolerance=}'

show(ppp0110)
