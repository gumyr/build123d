"""
Checks of the "Constraints without a solver" page

name: constraints_checks.py
by:   Gumyr
date: November 16th 2026

desc:
    The "Constraints without a solver" page describes how build123d's
    constrained objects behave without showing code. This script checks
    each of those statements, so that the page cannot drift from the
    library unnoticed. It shows no code on the page and draws no pictures.

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

import inspect

from OCP.BRep import BRep_Tool

from build123d import *

# ---------------------------------------------------------------------------
# Extent: the objects the page lists accept a limit in place of a size
# ---------------------------------------------------------------------------

for extent_object, parameter in (
    (PolarLine, "length"),
    (CenterArc, "arc_size"),
    (EllipticalCenterArc, "arc_size"),
    (EllipticalStartArc, "arc_size"),
    (JernArc, "arc_size"),
    (ParabolicCenterArc, "arc_size"),
    (HyperbolicCenterArc, "arc_size"),
):
    accepted = str(inspect.signature(extent_object.__init__).parameters[parameter])
    for limit in ("float", "Shape", "Axis", "Location", "Plane", "VectorLike"):
        assert limit in accepted, (extent_object.__name__, limit)

# trimmed at the limit
wall = Line((10, -5), (10, 20))
to_wall = PolarLine((0, 0), wall, 30)
assert abs((to_wall @ 1).X - 10) < 1e-6 and abs(to_wall.length - 11.547) < 1e-3
to_axis = CenterArc((0, 0), 5, 0, Axis((0, 0), (1, 1)))
assert abs(to_axis.length - 5 * 3.14159265 / 4) < 1e-6
# the shortest valid result from the start, when the limit is met twice
through = PolarLine((-20, 0), Circle(8).edge(), 0)
assert abs(through.length - 12) < 1e-6
# and a ValueError when it is not met at all
try:
    PolarLine((0, 0), Line((-10, -5), (-10, -1)), 30)
    raise AssertionError("a limit that is never met should be refused")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# Tangency: one arc from a point and a direction to another curve
# ---------------------------------------------------------------------------

target = Pos(6, 4) * CenterArc((0, 0), 2, 0, 360)
arrival = DoubleTangentArc((0, 0), (1, 0), target).edge()
assert (arrival @ 0).length < 1e-6 and (arrival % 0 - Vector(1, 0, 0)).length < 1e-6
# it ends on the circle, travelling along it
assert abs((arrival @ 1 - Vector(6, 4, 0)).length - 2) < 1e-6
radial = (arrival @ 1 - Vector(6, 4, 0)).normalized()
assert abs(radial.dot(arrival % 1)) < 1e-6

# ---------------------------------------------------------------------------
# Continuity: a line, a cubic Bezier and a quintic Bezier
# ---------------------------------------------------------------------------

first, second = Line((0, 0), (5, 0)), Line((8, 3), (8, 8))
degrees = {}
for level in ContinuityLevel:
    blend = BlendCurve(first, second, continuity=level).edge()
    # the ends always meet
    assert (blend @ 0 - first @ 1).length < 1e-6
    assert (blend @ 1 - second @ 0).length < 1e-6
    if level == ContinuityLevel.C0:
        assert blend.geom_type == GeomType.LINE
    else:
        # the directions match as well
        assert (blend % 0 - first % 1).length < 1e-6
        assert (blend % 1 - second % 0).length < 1e-6
        assert blend.geom_type == GeomType.BEZIER
        degrees[level] = BRep_Tool.Curve_s(blend.wrapped, 0, 1).Degree()
assert degrees == {ContinuityLevel.C1: 3, ContinuityLevel.C2: 5}

# ---------------------------------------------------------------------------
# Analytical: a triangle needs one side, and a description that fits one
# ---------------------------------------------------------------------------

solved = Triangle(a=3, b=4, c=5)
assert abs(solved.C - 90) < 1e-6
assert abs(Triangle(a=3, b=4, C=90).c - 5) < 1e-6
assert abs(Triangle(a=3, B=53.130102, C=90).c - 5) < 1e-4
for refused in ({"A": 30, "B": 60, "C": 90}, {"a": 3, "b": 4, "A": 36.87}):
    try:
        Triangle(**refused)
        raise AssertionError("this description should be refused")
    except ValueError:
        pass

# ---------------------------------------------------------------------------
# Enclosure
# ---------------------------------------------------------------------------

features = (Circle(3) + Pos(10, 0) * Circle(1)).edges()
hull = make_hull(features)
assert hull.area > Circle(3).area + Circle(1).area
# it holds everything it was made round, and has no hollows
everything = Compound(children=list(features)).bounding_box()
assert (hull.bounding_box().size - everything.size).length < 1e-6
assert abs(make_hull(hull.edges()).area - hull.area) < 1e-3 * hull.area

# ---------------------------------------------------------------------------
# More than one right answer
# ---------------------------------------------------------------------------

circle_1 = CenterArc((0, 0), 5, 0, 360)
circle_2 = CenterArc((6, 0), 5, 0, 360)

# up to eight circles of a given radius tangent to two crossing circles
assert len(ConstrainedArcs(circle_1, circle_2, radius=1).edges()) == 8
assert len(ConstrainedArcs(circle_1, circle_2, radius=3).edges()) == 4

# qualification narrows the search, and may still leave more than one
outside = ConstrainedArcs(
    (circle_1, Tangency.OUTSIDE), (circle_2, Tangency.OUTSIDE), radius=2
)
assert len(outside.edges()) == 2

# selection picks from what remains
chosen = ConstrainedArcs(
    circle_1, circle_2, radius=2, selector=lambda arcs: arcs.sort_by(Axis.Y)[-1]
)
assert len(chosen.edges()) == 1

# for a curve that is not a circle the inside is its left-hand side, so
# reversing it exchanges the answers that qualify
forward = Line((-10, -8), (10, -8))
reverse = Line((10, -8), (-10, -8))


def centers(arcs) -> list[tuple[float, float]]:
    """Where the arcs are drawn about"""
    return sorted(
        (round(arc.arc_center.X, 3), round(arc.arc_center.Y, 3)) for arc in arcs.edges()
    )


enclosed = ConstrainedArcs((forward, Tangency.ENCLOSED), (0, -5), radius=2)
outside = ConstrainedArcs((reverse, Tangency.OUTSIDE), (0, -5), radius=2)
assert centers(enclosed) == centers(outside) and len(centers(enclosed)) == 2
# both lie to the left of the forward line, which is above it
assert all(y > -8 for _, y in centers(enclosed))
for line, qualifier in ((forward, Tangency.OUTSIDE), (reverse, Tangency.ENCLOSED)):
    try:
        ConstrainedArcs((line, qualifier), (0, -5), radius=2)
        raise AssertionError("no arc is expected on this side of the line")
    except RuntimeError:
        pass
