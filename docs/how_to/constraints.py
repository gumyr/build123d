"""
Drawing with constraints documentation examples

name: constraints.py
by:   Gumyr
date: November 15th 2026

desc:
    Every code example of the "Drawing with constraints" how-to guide lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each example is written in builder and in algebra mode and the
    two are checked against each other. Run it from its own directory; the
    images are written to ``assets/constraints``.

license:

    Copyright 2026 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

# pylint: disable=redefined-outer-name, wildcard-import, unused-wildcard-import

from pathlib import Path

from build123d import *
from build123d.topology import Shape

OUTPUT = Path("assets/constraints")
OUTPUT.mkdir(parents=True, exist_ok=True)


def draw(
    name: str,
    given: list[Shape],
    made: list[Shape],
    construction: list[Shape] | None = None,
    marks: list[Vector] | None = None,
) -> None:
    """Write a picture: what the example starts from in black, what the
    constraint makes in blue, construction geometry dashed, and a small
    circle at each marked point."""
    construction = construction or []
    everything = Compound(children=[*given, *made, *construction])
    size = max(everything.bounding_box().size.X, everything.bounding_box().size.Y)
    svg = ExportSVG(scale=100 / size, margin=5)
    svg.add_layer("Given")
    svg.add_layer("Made", line_color=0x1E4FA3, line_weight=0.7)
    svg.add_layer("Construction", line_color=0x636363, line_type=LineType.ISO_DASH)
    svg.add_layer("Marks", line_color=0x636363)
    for layer, shapes in (
        ("Construction", construction),
        ("Given", given),
        ("Made", made),
    ):
        if shapes:
            svg.add_shape(shapes, layer)
    for point in marks or []:
        svg.add_shape(Pos(point) * Circle(size / 80).edge(), "Marks")
    svg.write(OUTPUT / f"{name}.svg")


def total(shape: Shape) -> float:
    """The length of all the edges of a shape."""
    return sum(edge.length for edge in shape.edges())


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of an example make the same lines?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        len(first.edges()) == len(second.edges())
        and abs(total(first) - total(second)) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


# ---------------------------------------------------------------------------
# start where another object ends
# ---------------------------------------------------------------------------

# [ends]
with BuildLine() as arch:
    l1 = Line((0, 0), (2, 0))
    l2 = ThreePointArc(l1 @ 0, (1, 1), l1 @ 1)
# [ends]

builder_result = arch.line

# [ends_algebra]
l1 = Line((0, 0), (2, 0))
l2 = ThreePointArc(l1 @ 0, (1, 1), l1 @ 1)
arch = l1 + l2
# [ends_algebra]

assert same(builder_result, arch)
assert (l2 @ 0 - l1 @ 0).length < 1e-6 and (l2 @ 1 - l1 @ 1).length < 1e-6
draw("ends", [l1], [l2], marks=[l1 @ 0, l1 @ 1])

# ---------------------------------------------------------------------------
# measure from another object
# ---------------------------------------------------------------------------

# [measure]
with BuildLine() as arch:
    l1 = Line((0, 0), (3, 1))
    l2 = ThreePointArc(l1 @ 0, l1 @ 0.5 + (0, l1.length / 2), l1 @ 1)
# [measure]

builder_result = arch.line

# [measure_algebra]
l1 = Line((0, 0), (3, 1))
l2 = ThreePointArc(l1 @ 0, l1 @ 0.5 + (0, l1.length / 2), l1 @ 1)
arch = l1 + l2
# [measure_algebra]

assert same(builder_result, arch)
assert (l2 @ 0 - l1 @ 0).length < 1e-6 and (l2 @ 1 - l1 @ 1).length < 1e-6
draw("measure", [l1], [l2], marks=[l1 @ 0, l1 @ 0.5, l1 @ 1])

# ---------------------------------------------------------------------------
# leave along a tangent
# ---------------------------------------------------------------------------

# [tangent]
with BuildLine() as corner:
    l1 = Line((0, 0), (5, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
    l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
    l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
# [tangent]

builder_result = corner.line

# [tangent_algebra]
l1 = Line((0, 0), (5, 0))
l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
corner = l1 + l2 + l3 + l4
# [tangent_algebra]

assert same(builder_result, corner)
# the arc leaves the line without a kink, and the last line leaves the arc the same way
assert (l3 % 0 - l2 % 1).length < 1e-6 and (l4 % 0 - l3 % 1).length < 1e-6
draw(
    "tangent",
    [l1, l2, l4],
    [l3],
    construction=[PolarLine(l2 @ 1, 0.8, direction=l2 % 1)],
    marks=[l2 @ 1, l3 @ 1],
)

# ---------------------------------------------------------------------------
# leave at a right angle
# ---------------------------------------------------------------------------

# [perpendicular]
with BuildLine() as spur:
    l1 = CenterArc((0, 0), 1.5, 0, 45)
    l2 = PolarLine(start=l1 @ 1, length=1, direction=(l1 % 1).rotate(Axis.Z, -90))
# [perpendicular]

builder_result = spur.line

# [perpendicular_algebra]
l1 = CenterArc((0, 0), 1.5, 0, 45)
l2 = PolarLine(start=l1 @ 1, length=1, direction=(l1 % 1).rotate(Axis.Z, -90))
spur = l1 + l2
# [perpendicular_algebra]

assert same(builder_result, spur)
assert abs((l1 % 1).dot(l2 % 0)) < 1e-6
draw("perpendicular", [l1], [l2], marks=[l1 @ 1])

# ---------------------------------------------------------------------------
# run until it meets another object
# ---------------------------------------------------------------------------

# [until]
with BuildLine() as fan:
    c1 = EllipticalCenterArc((0, 0), 1.2, 1.8, 0, arc_size=120, mode=Mode.PRIVATE)
    l1 = PolarLine(start=(-0.2, 0.1), length=c1, angle=10)
    l2 = PolarLine(start=(-0.2, 0.1), length=c1, angle=70)
    l3 = insert(c1.trim(l1 @ 1, l2 @ 1))
# [until]

builder_result = fan.line

# [until_algebra]
c1 = EllipticalCenterArc((0, 0), 1.2, 1.8, 0, arc_size=120)
l1 = PolarLine(start=(-0.2, 0.1), length=c1, angle=10)
l2 = PolarLine(start=(-0.2, 0.1), length=c1, angle=70)
l3 = c1.trim(l1 @ 1, l2 @ 1)
fan = l1 + l2 + l3
# [until_algebra]

assert same(builder_result, fan)
# both lines end on the ellipse
assert c1.distance_to(l1 @ 1) < 1e-6 and c1.distance_to(l2 @ 1) < 1e-6
draw("until", [l3], [l1, l2], construction=[c1], marks=[l1 @ 1, l2 @ 1])

# [until_arcs]
p1 = ParabolicCenterArc((0, 0), 0.5, 0, arc_size=Line((0, 1), (5, 1)))
h1 = HyperbolicCenterArc((0, 0), 2, 1, 0, arc_size=Axis((0, 1), (1, 0)))
# [until_arcs]

assert abs((p1 @ 1).Y - 1) < 1e-6 and abs((h1 @ 1).Y - 1) < 1e-6

# ---------------------------------------------------------------------------
# keep a constant distance
# ---------------------------------------------------------------------------

# [distance]
with BuildLine() as channel:
    inside = FilletPolyline((1.5, 0), (1.5, 1), (-1.5, 1), (-1.5, 0), radius=0.2)
    offset(amount=0.2, side=Side.RIGHT)
# [distance]

builder_result = channel.line

# [distance_algebra]
inside = FilletPolyline((1.5, 0), (1.5, 1), (-1.5, 1), (-1.5, 0), radius=0.2)
channel = offset(inside, amount=0.2, side=Side.RIGHT)
# [distance_algebra]

assert same(builder_result, channel)
# the result is a closed outline: the line, its offset and the two ends
assert Wire(channel.edges()).is_closed
# and nowhere is it further than the offset from the line it was made from
assert all(inside.distance_to(edge @ 0.5) < 0.2 + 1e-6 for edge in channel.edges())
assert abs(max(inside.distance_to(edge @ 0.5) for edge in channel.edges()) - 0.2) < 1e-6
added = [edge for edge in channel.edges() if inside.distance_to(edge @ 0.5) > 1e-6]
draw("distance", [inside], added)

# ---------------------------------------------------------------------------
# join two curves smoothly
# ---------------------------------------------------------------------------

# [blend]
with BuildLine() as joined:
    m1 = CenterArc((-2, 0.6), 1, -10, 200).reversed()
    m2 = Spline((0.4, -0.6), (1, -1.6), (2, 0))
    connector = BlendCurve(
        m1, m2, tangent_scalars=(2, 1), continuity=ContinuityLevel.C2
    )
# [blend]

builder_result = connector

# [blend_algebra]
m1 = CenterArc((-2, 0.6), 1, -10, 200).reversed()
m2 = Spline((0.4, -0.6), (1, -1.6), (2, 0))
connector = BlendCurve(m1, m2, tangent_scalars=(2, 1), continuity=ContinuityLevel.C2)
joined = m1 + connector + m2
# [blend_algebra]

assert same(builder_result, connector)
# the connector starts where one curve ends and ends where the other starts,
# heading the same way as each
assert (connector @ 0 - m1 @ 1).length < 1e-6 and (connector @ 1 - m2 @ 0).length < 1e-6
assert (connector % 0 - m1 % 1).length < 1e-6 and (connector % 1 - m2 % 0).length < 1e-6

# [blend_comb]
comb = Curve(Wire([m1, connector, m2]).curvature_comb(200))
# [blend_comb]

draw("blend", [m1, m2], [connector], construction=list(comb.edges()))

# ---------------------------------------------------------------------------
# tangent to other lines and arcs
# ---------------------------------------------------------------------------

# [tangent_to]
with BuildLine() as egg_plant:
    # construction geometry: the two ends
    c1 = CenterArc((-2, 0), 0.75, 80, 240, mode=Mode.PRIVATE)
    c2 = CenterArc((2, 0), 1, 220, 250, mode=Mode.PRIVATE)

    # the two sides, each tangent to both ends
    l1 = ConstrainedArcs((c2, Tangency.OUTSIDE), (c1, Tangency.OUTSIDE), radius=6)
    l2 = ConstrainedArcs(
        (c2, Tangency.ENCLOSING),
        (c1, Tangency.ENCLOSING),
        radius=8,
        selector=lambda arcs: arcs.sort_by(Axis.Y)[-1],
    )

    # the parts of the ends that lie between the sides
    l3 = insert(c1.trim(l1 @ 1, l2 @ 1))
    l4 = insert(c2.trim(l1 @ 0, l2 @ 0))
# [tangent_to]

builder_result = egg_plant.line

# [tangent_to_algebra]
# construction geometry: the two ends
c1 = CenterArc((-2, 0), 0.75, 80, 240)
c2 = CenterArc((2, 0), 1, 220, 250)

# the two sides, each tangent to both ends
l1 = ConstrainedArcs((c2, Tangency.OUTSIDE), (c1, Tangency.OUTSIDE), radius=6)
l2 = ConstrainedArcs((c2, Tangency.ENCLOSING), (c1, Tangency.ENCLOSING), radius=8)
l2 = l2.edges().sort_by(Axis.Y)[-1]

# the parts of the ends that lie between the sides
l3 = c1.trim(l1 @ 1, l2 @ 1)
l4 = c2.trim(l1 @ 0, l2 @ 0)
egg_plant = l1 + l2 + l3 + l4
# [tangent_to_algebra]

assert same(builder_result, egg_plant)
# a closed outline
assert Wire(egg_plant.edges()).is_closed
draw("tangent_to", [l3, l4], [l1, l2], construction=[c1, c2])

# ---------------------------------------------------------------------------
# arcs fixed only by what they touch
# ---------------------------------------------------------------------------

# [touching]
with BuildLine() as profile:
    # construction lines: a slope falling at 8 degrees, and a flat
    slope = PolarLine((27.5, 50), 100, -8, mode=Mode.PRIVATE)
    flat = Line((0, 32), (125, 32), mode=Mode.PRIVATE)

    # a circle of radius 30, tangent to the slope from below, with its
    # centre somewhere on the line X = 49.5
    circle_30 = ConstrainedArcs(
        slope,
        radius=30,
        center_on=Axis((49.5, 0), (0, 1)),
        selector=lambda arcs: arcs.sort_by(Axis.Y)[0],
        mode=Mode.PRIVATE,
    ).edge()

    # an arc of radius 66, tangent to that circle and to the flat, from above
    l3 = ConstrainedArcs(
        circle_30, flat, radius=66, selector=lambda arcs: arcs.sort_by(Axis.Y)[-1]
    )

    # the slope as far as it touches the circle, and the arc that joins them
    touch = circle_30.arc_center + Vector(0, 0, 1).cross(slope % 0) * 30
    l1 = Line(slope @ 0, touch)
    l2 = RadiusArc(l1 @ 1, l3 @ 0, 30)
# [touching]

builder_result = profile.line

# [touching_algebra]
# construction lines: a slope falling at 8 degrees, and a flat
slope = PolarLine((27.5, 50), 100, -8)
flat = Line((0, 32), (125, 32))

# a circle of radius 30, tangent to the slope from below, with its centre
# somewhere on the line X = 49.5
circle_30 = ConstrainedArcs(
    slope,
    radius=30,
    center_on=Axis((49.5, 0), (0, 1)),
    selector=lambda arcs: arcs.sort_by(Axis.Y)[0],
).edge()

# an arc of radius 66, tangent to that circle and to the flat, from above
l3 = ConstrainedArcs(
    circle_30, flat, radius=66, selector=lambda arcs: arcs.sort_by(Axis.Y)[-1]
)

# the slope as far as it touches the circle, and the arc that joins them
touch = circle_30.arc_center + Vector(0, 0, 1).cross(slope % 0) * 30
l1 = Line(slope @ 0, touch)
l2 = RadiusArc(l1 @ 1, l3 @ 0, 30)
profile = l1 + l2 + l3
# [touching_algebra]

assert same(builder_result, profile)
# the three pieces run on smoothly from one to the next
assert (l1 % 1 - l2 % 0).length < 1e-6 and (l2 % 1 - l3 % 0).length < 1e-6
# the last arc lands on the flat, travelling along it
assert abs((l3 @ 1).Y - 32) < 1e-6 and (l3 % 1 - Vector(1, 0, 0)).length < 1e-6
# the values the four simultaneous equations of this problem give
assert (circle_30.arc_center - Vector(49.5, 16.6133)).length < 1e-3
assert (l3.edge().arc_center - Vector(100.4137, 98)).length < 1e-3
assert (touch - Vector(53.6752, 46.3213)).length < 1e-3
assert (l3 @ 0 - Vector(65.4105, 42.0466)).length < 1e-3
draw(
    "touching",
    [],
    [l1, l2, l3],
    construction=[slope, flat, circle_30],
    marks=[circle_30.arc_center, l3.edge().arc_center],
)
