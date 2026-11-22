"""
Checks of the algebraic definition page

name: algebra_definition.py
by:   Gumyr
date: November 16th 2026

desc:
    The "Algebraic definition" page states the sets build123d's algebra
    works on and the laws its operators obey. This script checks each of
    those statements on concrete shapes and locations, so that the page
    cannot drift from the library unnoticed. It shows no code on the page
    and draws no pictures.

    Equality of shapes is tested by size and extent, to the kernel's
    tolerance, which is the sense in which the laws hold.

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

import re
from pathlib import Path

import build123d
from build123d import *


def measure(shape) -> float:
    """Volume, area or length, by dimension"""
    if shape._dim == 3:
        return shape.volume
    if shape._dim == 2:
        return shape.area
    return sum(edge.length for edge in shape.edges())


def covers(first, second) -> bool:
    """Does every edge of the second curve lie on the first?"""
    return all(
        first.distance_to(Vertex(*(edge @ along))) < 1e-6
        for edge in second.edges()
        for along in (0, 0.25, 0.5, 0.75, 1)
    )


def equal(first, second) -> bool:
    """The same point set, to tolerance.

    Solids and faces are compared by measure and extent. Curves are compared
    point by point, because adding curves that overlap can leave coincident
    edges in the result, which hold the same points with a greater length."""
    if not first and not second:
        return True
    if bool(first) != bool(second):
        return False
    if first._dim == 1 and second._dim == 1:
        return covers(first, second) and covers(second, first)
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(measure(first) - measure(second)) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


# three overlapping shapes of each dimension, and the zero of each set
samples = {
    3: (Box(4, 4, 4), Pos(2, 0, 0) * Box(4, 4, 4), Pos(0, 2, 0) * Box(4, 4, 4), Part()),
    2: (
        Rectangle(4, 4),
        Pos(2, 0) * Rectangle(4, 4),
        Pos(0, 2) * Rectangle(4, 4),
        Sketch(),
    ),
    1: (Line((0, 0), (4, 0)), Line((2, 0), (6, 0)), Line((1, 0), (3, 0)), Curve()),
}

# ---------------------------------------------------------------------------
# the sets: every member has the dimension of its set
# ---------------------------------------------------------------------------

for dimension, (a, b, c, zero) in samples.items():
    assert a._dim == b._dim == c._dim == zero._dim == dimension
    assert zero.is_empty

# the basic shapes the page lists all have the dimension of their set
page = Path(__file__).with_name("algebra_definition.rst").read_text(encoding="utf-8")
for dimension in (1, 2, 3):
    listed = re.search(rf"B\^{dimension} := \\lbrace`(.*?):math:`\\rbrace`", page, re.S)
    assert listed is not None, dimension
    names = re.findall(r"``(\w+)``", listed.group(1))
    assert len(names) == len(set(names)) > 5, names
    for name in names:
        assert getattr(build123d, name)._dim.fget(None) == dimension, name

# a Shell has dimension 2 but is not a member of C2: adding to one sews
shell = Shell(Rectangle(4, 4).face())
assert shell._dim == 2 and isinstance(shell + Pos(4, 0) * Rectangle(4, 4), Shell)

# ---------------------------------------------------------------------------
# the operations stay in their set, and the zeros behave as zeros
# ---------------------------------------------------------------------------

for dimension, (a, b, c, zero) in samples.items():
    for result in (a + b, a - b, a & b):
        assert result._dim == dimension
    assert equal(a + zero, a) and equal(zero + a, a)
    assert (zero - a).is_empty and (a & zero).is_empty and (a - a).is_empty
    # a - a is the zero of its own set
    assert type(a - a) is type(zero)

# two parts that do not touch: still dimension 3, though not of class Part
apart = Box(1, 1, 1) + Pos(5, 0, 0) * Box(1, 1, 1)
assert apart._dim == 3

# adding curves that overlap and share an end keeps both, as a wire that
# doubles back: the same points, counted twice in the length
doubled = Line((0, 0), (4, 0)) + Line((2, 0), (4, 0))
assert equal(doubled, Line((0, 0), (4, 0)))
assert abs(sum(edge.length for edge in doubled.edges()) - 6) < 1e-6

# what shapes that only touch have in common: nothing in 3D, and the
# contact one dimension down in 2D and 1D
cube = Box(2, 2, 2)
for offset in ((2, 0, 0), (2, 2, 0), (2, 2, 2)):  # sharing a face, an edge, a corner
    assert (cube & Pos(*offset) * Box(2, 2, 2)).is_empty
square = Rectangle(2, 2)
shared_edge = square & Pos(2, 0) * Rectangle(2, 2)
assert isinstance(shared_edge, Curve) and shared_edge._dim == 1
crossing = Line((0, 0), (4, 0)) & Line((2, -1), (2, 1))
assert isinstance(crossing, Vertex)

# ---------------------------------------------------------------------------
# the laws
# ---------------------------------------------------------------------------

for dimension, (a, b, c, zero) in samples.items():
    # + and & are commutative, associative and idempotent
    assert equal(a + b, b + a) and equal(a & b, b & a)
    assert equal((a + b) + c, a + (b + c)) and equal((a & b) & c, a & (b & c))
    assert equal(a + a, a) and equal(a & a, a)
    # each absorbs the other, and each distributes over the other
    assert equal(a + (a & b), a) and equal(a & (a + b), a)
    assert equal(a & (b + c), (a & b) + (a & c))
    assert equal(a + (b & c), (a + b) & (a + c))
    # a - b is the complement of b within a: nothing of this dimension is
    # common to the two, though faces or curves that touch share their contact
    contact = (a - b) & b
    assert contact.is_empty or contact._dim < dimension
    assert equal((a - b) + (a & b), a)
    # the intersection written with + and - alone
    assert equal(a & b, (a + b) - (a - b) - (b - a))
    # - is neither commutative nor associative
    assert not equal(a - b, b - a)
    assert not equal(a - (b - c), (a - b) - c)
    # and it is not the inverse of +, so this is not a group
    assert not equal((b - a) + a, b)
    # it does have the two properties the page gives
    assert equal(a - (b + c), (a - b) - c) and equal(a - (b - c), (a - b) + (a & c))

# there is no negative shape
for shape in (Box(1, 1, 1), Rectangle(1, 1), Line((0, 0), (1, 0))):
    try:
        -shape  # pylint: disable=invalid-unary-operand-type, expression-not-assigned
        raise AssertionError("a unary minus is not expected on this shape")
    except TypeError:
        pass

# ---------------------------------------------------------------------------
# mixed dimensions
# ---------------------------------------------------------------------------

sketch, solid, line = Rectangle(6, 6), Box(4, 4, 4), Line((-5, 0), (5, 0))
assert (sketch - solid)._dim == 2 and abs((sketch - solid).area - 20) < 1e-6
assert (sketch & solid)._dim == (solid & sketch)._dim == 2
assert (line & solid)._dim == (solid & line)._dim == 1
for refused in (lambda: solid - sketch, lambda: solid + sketch, lambda: line + sketch):
    try:
        refused()
        raise AssertionError("this combination of dimensions should be refused")
    except ValueError:
        pass

# ---------------------------------------------------------------------------
# locations
# ---------------------------------------------------------------------------


def same_place(first: Location, second: Location) -> bool:
    """The same position and orientation"""
    difference = first.inverse() * second
    return (
        difference.position.length < 1e-9
        and Vector(*difference.orientation).length < 1e-6
    )


l1 = Location((1, 2, 3), (10, 20, 30))
l2 = Location((4, 5, 6), (40, 50, 60))
l3 = Location((7, 8, 9), (5, 15, 25))
identity = Location()

# a group: identity, inverse, associative; and not commutative
assert same_place(l1 * identity, l1) and same_place(identity * l1, l1)
assert same_place(l1 * l1.inverse(), identity) and same_place(
    l1.inverse() * l1, identity
)
assert same_place((l1 * l2) * l3, l1 * (l2 * l3))
assert not same_place(l1 * l2, l2 * l1)

# a plane times a location is a location
plane = Plane.XZ
assert isinstance(plane * l1, Location)
assert same_place(plane * l1, plane.location * l1)
# a plane's directions are perpendicular
tilted = Plane((0, 0, 0), x_dir=(1, 0, 0), z_dir=(1, 0, 1))
assert abs(tilted.x_dir.dot(tilted.z_dir)) < 1e-9
assert abs(tilted.x_dir.length - 1) < 1e-9 and abs(tilted.z_dir.length - 1) < 1e-9

# placing objects, and that placement composes
box = Box(1, 2, 3)
assert equal(plane * box, box.moved(plane.location))
assert equal(l1 * box, box.moved(l1))
assert equal((l1 * l2) * box, l1 * (l2 * box))
assert equal(identity * box, box)
assert equal((plane * l1) * box, plane * (l1 * box))
for dimension, (a, b, c, zero) in samples.items():
    assert (l1 * a)._dim == (plane * a)._dim == dimension
