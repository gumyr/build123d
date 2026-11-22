"""
How algebra mode works documentation examples

name: algebra_mode.py
by:   Gumyr
date: November 16th 2026

desc:
    The code of the "How algebra mode works" page, between pairs of
    ``# [name]`` markers that the page includes with ``literalinclude``,
    with checks of what the page says about each.

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
# pylint: disable=pointless-statement, expression-not-assigned

from build123d import *
from build123d.build_common import LocationList


def same(first, second) -> bool:
    """Are two shapes the same size and in the same place?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
    )


# ---------------------------------------------------------------------------
# objects are values
# ---------------------------------------------------------------------------

# [values]
block = Box(20, 20, 10)
peg = Cylinder(4, 30)

joined = block + peg  # a new part; block and peg are as they were
drilled = block - peg  # another new part, made from the same two
# [values]

assert (
    abs(block.volume - 20 * 20 * 10) < 1e-6
    and abs(peg.volume - Cylinder(4, 30).volume) < 1e-6
)
assert joined.volume > block.volume > drilled.volume

# [rebind]
plate = Box(20, 20, 10)
plate -= Cylinder(4, 30)  # the same as: plate = plate - Cylinder(4, 30)
# [rebind]

assert same(plate, drilled)

# ---------------------------------------------------------------------------
# combining
# ---------------------------------------------------------------------------

# [combine]
box = Box(1, 2, 3)
rod = Cylinder(0.2, 5)

box + rod  # everything in either
box - rod  # the box, less what the rod occupies
box & rod  # only what is in both
# [combine]

assert abs((box + rod).volume + (box & rod).volume - box.volume - rod.volume) < 1e-6
assert abs((box - rod).volume + (box & rod).volume - box.volume) < 1e-6
assert all(isinstance(result, Part) for result in (box + rod, box - rod, box & rod))
assert isinstance(Rectangle(4, 4) + Pos(3, 0) * Circle(2), Sketch)

# [mixed_dimensions]
sketch = Rectangle(6, 6)
solid = Box(4, 4, 4)

sketch - solid  # a Sketch: the rectangle with a square hole where the box is
solid & sketch  # a Sketch: the square of the rectangle that is inside the box
# [mixed_dimensions]

assert isinstance(sketch - solid, Sketch) and abs((sketch - solid).area - 20) < 1e-6
assert isinstance(solid & sketch, Sketch) and abs((solid & sketch).area - 16) < 1e-6
for forbidden in (
    lambda: solid - sketch,
    lambda: solid + sketch,
    lambda: sketch + solid,
):
    try:
        forbidden()
        raise AssertionError("this combination of dimensions should be refused")
    except ValueError:
        pass

# [many]
holes = [Pos(x, y, 0) * Cylinder(1, 2) for x in (-5, 5) for y in (-5, 5)]
plate = Box(20, 20, 2) - holes  # all four cut in one step
# [many]

assert isinstance(plate, Part)
assert len(plate.faces().filter_by(GeomType.CYLINDER)) == 4

# pieces that do not touch come back grouped in a plain Compound
apart = Box(1, 1, 1) + Pos(5, 0, 0) * Box(1, 1, 1)
assert type(apart) is Compound and len(apart.solids()) == 2

# ---------------------------------------------------------------------------
# many objects at once is much faster
# ---------------------------------------------------------------------------

diameter = 80
tile = Rectangle(2, 2)


def on_the_disc(place: Location) -> bool:
    """Is this place well inside the disc?"""
    return place.position.X**2 + place.position.Y**2 < (diameter / 2 - 1.8) ** 2


# a small grid here, so that the slow way does not slow the docs tests
places = [place for place in GridLocations(4, 4, 6, 6) if on_the_disc(place)]

# [slow]
holes = Sketch()
for place in places:
    holes += place * tile  # one fuse for every tile
grille = Circle(diameter / 2) - holes
# [slow]

slow_grille = grille

# [fast]
holes = [place * tile for place in places]
grille = Circle(diameter / 2) - holes  # one cut for all of them
# [fast]

assert abs(slow_grille.area - grille.area) < 1e-6
assert len(grille.face().inner_wires()) == len(places) == 36

# [vectorized]
pattern = GridLocations(40, 30, 2, 2) * RegularPolygon(radius=5, side_count=5)
plate = Rectangle(70, 60) - pattern
# [vectorized]

assert isinstance(pattern, list) and len(pattern) == 4
assert len(plate.face().inner_wires()) == 4

# ---------------------------------------------------------------------------
# sewing sheet surfaces
# ---------------------------------------------------------------------------

# [sew]
base = Shell(Rectangle(20, 20).face())
wall = Plane(origin=(10, 0, 5), z_dir=(1, 0, 0), x_dir=(0, 1, 0)) * Rectangle(20, 10)
sheet = base + wall
# [sew]

assert isinstance(sheet, Shell) and len(sheet.faces()) == 2

# [sew_more]
sheet += Plane(origin=(-10, 0, 5), z_dir=(1, 0, 0), x_dir=(0, 1, 0)) * Rectangle(20, 10)
# [sew_more]

assert isinstance(sheet, Shell) and len(sheet.faces()) == 3

# ---------------------------------------------------------------------------
# placing
# ---------------------------------------------------------------------------

# [place]
Pos(0, 1, 0) * Box(1, 2, 3)  # moved 1 along Y
Rot(Z=45) * Box(1, 2, 3)  # turned 45 degrees about Z
Plane.XZ * Box(1, 2, 3)  # stood on the XZ plane
# [place]

assert (Pos(0, 1, 0) * Box(1, 2, 3)).center() == Vector(0, 1, 0)
assert same(Plane.XY * Box(1, 2, 3), Box(1, 2, 3))

# [chain]
Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3)
# [chain]

# a Location is a Pos and a Rot in one
assert same(
    Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3),
    Plane.XZ * Location((1, 2, 3), (0, 100, 45)) * Box(1, 2, 3),
)
# and the plane matters: without it the box is somewhere else
assert not same(
    Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3),
    Location((1, 2, 3), (0, 100, 45)) * Box(1, 2, 3),
)
# the position is measured in the plane: its Y is the world's Z
assert (
    (Plane.XZ * Pos(1, 2, 3) * Box(1, 1, 1)).center() - Vector(1, -3, 2)
).length < 1e-9

# [place_many]
feet = GridLocations(40, 30, 2, 2) * Cylinder(3, 5)  # a list of four cylinders

pairs = GridLocations(4, 4, 2, 1) * GridLocations(1, 1, 2, 2)  # eight places
# [place_many]

assert isinstance(feet, list) and len(feet) == 4
assert isinstance(pairs, LocationList) and len(pairs) == 8
assert isinstance(Plane.XZ * GridLocations(1, 1, 2, 2), LocationList)
assert isinstance(pairs[:2], LocationList) and isinstance(pairs + pairs, LocationList)

# [precedence]
bracket = Plane.XZ * Rot(X=30) * Box(1, 2, 3) + Plane.YZ * Pos(X=-1) * Cylinder(0.2, 5)
# [precedence]

assert isinstance(bracket, Part)

# ---------------------------------------------------------------------------
# operations take and return
# ---------------------------------------------------------------------------

# [operations]
perimeter = Polyline((0, 0), (20, 0), (20, 10), (0, 10), close=True)
profile = make_face(perimeter)  # a Sketch
block = extrude(profile, amount=5)  # a Part
block = fillet(block.edges().filter_by(Axis.Z), radius=2)  # a Part again
# [operations]

assert isinstance(profile, Sketch) and isinstance(block, Part)
assert len(block.faces().filter_by(GeomType.CYLINDER)) == 4

# ---------------------------------------------------------------------------
# selecting from a result
# ---------------------------------------------------------------------------

# [select]
tray = Box(20, 20, 5) - Pos(Z=1.5) * Box(16, 16, 5)

pocket_faces = tray.faces(Select.LAST)  # the five faces the cut brought in
rim = tray.edges(Select.NEW)  # the four edges that did not exist before
tray = fillet(rim, 1)
# [select]

assert len(pocket_faces) == 5 and len(rim) == 4 and tray.is_valid

# ---------------------------------------------------------------------------
# mixing with builders
# ---------------------------------------------------------------------------

# [mix]
with BuildPart() as base:
    Box(80, 60, 10)

result = base.part - Cylinder(11, 10)  # the part, not the builder
# [mix]

assert isinstance(result, Part) and result.volume < 80 * 60 * 10
