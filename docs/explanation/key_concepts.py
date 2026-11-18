"""
Key concepts documentation examples

name: key_concepts.py
by:   Gumyr
date: November 15th 2026

desc:
    The code of the "Key concepts" page, between pairs of ``# [name]``
    markers that the page includes with ``literalinclude``, with checks of
    what the page says about each.

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

from build123d import *

# ---------------------------------------------------------------------------
# shapes are made of shapes
# ---------------------------------------------------------------------------

# [hierarchy]
box = Box(2, 3, 4)

len(box.solids())  # 1
len(box.shells())  # 1
len(box.faces())  # 6
len(box.wires())  # 6, one round each face
len(box.edges())  # 12
len(box.vertices())  # 8
# [hierarchy]

counts = [
    len(found)
    for found in (
        box.solids(),
        box.shells(),
        box.faces(),
        box.wires(),
        box.edges(),
        box.vertices(),
    )
]
assert counts == [1, 1, 6, 6, 12, 8]

# [topology]
top = box.faces().sort_by(Axis.Z)[-1]
print(top.show_topology())
# [topology]

assert (
    top.show_topology().count("Edge") == 4 and top.show_topology().count("Vertex") == 8
)

# a shell need not be closed
open_shell = Shell(box.faces().sort_by(Axis.Z)[1:])
assert len(open_shell.faces()) == 5 and open_shell.is_valid

# ---------------------------------------------------------------------------
# topology and geometry
# ---------------------------------------------------------------------------

# [geometry]
can = Cylinder(1, 2)

{face.geom_type for face in can.faces()}  # PLANE and CYLINDER
{edge.geom_type for edge in can.edges()}  # CIRCLE and LINE
# [geometry]

assert {face.geom_type for face in can.faces()} == {GeomType.PLANE, GeomType.CYLINDER}
assert {edge.geom_type for edge in can.edges()} == {GeomType.CIRCLE, GeomType.LINE}

# ---------------------------------------------------------------------------
# parts, sketches and curves
# ---------------------------------------------------------------------------

# [kinds]
isinstance(Box(1, 1, 1), Part)  # True: a Box is a Part
isinstance(Rectangle(1, 1), Sketch)  # True: a Rectangle is a Sketch
isinstance(Part(), Compound)  # True: all three are Compounds

type(Box(1, 1, 1) + Sphere(1))  # Part
type(Rectangle(1, 1) - Circle(0.3))  # Sketch
# [kinds]

assert isinstance(Box(1, 1, 1), Part) and isinstance(Rectangle(1, 1), Sketch)
assert all(isinstance(kind(), Compound) for kind in (Part, Sketch, Curve))
assert type(Box(1, 1, 1) + Sphere(1)) is Part
assert type(Rectangle(1, 1) - Circle(0.3)) is Sketch
# lines are single edges and wires until a builder gathers them into a Curve
assert isinstance(Line((0, 0), (1, 0)), Edge)
assert isinstance(Polyline((0, 0), (1, 0), (1, 1)), Wire)
with BuildLine() as outline:
    Line((0, 0), (1, 0))
    Line((1, 0), (1, 1))
with BuildSketch() as profile:
    Rectangle(1, 1)
with BuildPart() as block:
    Box(1, 1, 1)
assert type(outline.line) is Curve
assert type(profile.sketch) is Sketch and type(block.part) is Part

# ---------------------------------------------------------------------------
# vectors, axes, planes and locations
# ---------------------------------------------------------------------------

# [places]
point = Vector(1, 2, 3)
axle = Axis((0, 0, 5), (0, 0, 1))  # through a point, in a direction
shelf = Plane.XY.offset(5)  # an origin, an X direction and a normal
place = Location((0, 0, 5), (0, 0, 30))  # a position and three rotation angles
# [places]

assert (axle.position - Vector(0, 0, 5)).length < 1e-9
assert (shelf.origin - Vector(0, 0, 5)).length < 1e-9
assert (place.position - Vector(0, 0, 5)).length < 1e-9

# [conversions]
shelf.location  # the plane as a location
Plane(place)  # the location as a plane
place.z_axis  # the axis a location's Z direction lies along

Plane(box.faces().sort_by(Axis.Z)[-1])  # the plane a flat face lies in
Axis(box.edges().filter_by(Axis.Z)[0])  # the axis a straight edge lies along
# [conversions]

assert repr(shelf.location) == "Location((0, 0, 5), (0, 0, 0))"
assert (Plane(place).origin - Vector(0, 0, 5)).length < 1e-9
assert abs(Plane(place).x_dir.X - 0.866025) < 1e-5
assert (place.z_axis.direction - Vector(0, 0, 1)).length < 1e-9
assert (Plane(box.faces().sort_by(Axis.Z)[-1]).origin - Vector(0, 0, 2)).length < 1e-9
assert (
    Axis(box.edges().filter_by(Axis.Z)[0]).direction - Vector(0, 0, 1)
).length < 1e-9

# ---------------------------------------------------------------------------
# a shape has a location
# ---------------------------------------------------------------------------

# [location]
first = Box(1, 1, 1)
second = first.moved(Pos(5, 0, 0))  # a new shape at a new place

first.location  # still at the origin
second.location  # at (5, 0, 0)
# [location]

assert first.location.position.length < 1e-9
assert (second.location.position - Vector(5, 0, 0)).length < 1e-9
# the two share one piece of geometry
assert second.wrapped.IsPartner(first.wrapped)
