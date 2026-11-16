"""
Checks of the "Surface modeling" page

name: surface_modeling_checks.py
by:   Gumyr
date: November 16th 2026

desc:
    The "Surface modeling" page describes how faces become a shell and a
    solid without showing code. This script checks each of those
    statements, so that the page cannot drift from the library unnoticed.
    It shows no code on the page and draws no pictures.

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

CORNERS = [
    (0, 0, 0),
    (1, 0, 0),
    (1, 1, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 0, 1),
    (1, 1, 1),
    (0, 1, 1),
]
SIDES = [
    (0, 3, 2, 1),
    (4, 5, 6, 7),
    (0, 1, 5, 4),
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
]


def cube_faces(gap: float = 0.0) -> list[Face]:
    """The six faces of a unit cube, each made from four edges of its own,
    so that no two faces have an edge object in common. The gap lifts the
    lid off the sides."""
    faces = []
    for index, side in enumerate(SIDES):
        lift = Vector(0, 0, gap) if index == 1 else Vector()
        corners = [Vector(*CORNERS[corner]) + lift for corner in side]
        faces.append(Face(Wire(Polyline(*corners, close=True).edges())))
    return faces


# ---------------------------------------------------------------------------
# Shell sews: edges that coincide are merged, whoever made them
# ---------------------------------------------------------------------------

separate = cube_faces()
assert sum(len(face.edges()) for face in separate) == 24
shell = Shell(separate)
assert len(shell.edges()) == 12 and shell.is_manifold
cube = Solid(shell)
assert cube.is_valid and abs(cube.volume - 1) < 1e-9

# within the default tolerance of one millionth
assert Shell(cube_faces(1e-7)).is_manifold

# further apart, the faces are refused, not returned with a gap
for gap in (1e-5, 1e-3):
    try:
        Shell(cube_faces(gap))
        raise AssertionError("faces this far apart should not sew")
    except ValueError:
        pass

# unless the tolerance is raised above the gap
joined = Shell(cube_faces(1e-3), tolerance=0.01)
assert joined.is_manifold and Solid(joined).is_valid

# ---------------------------------------------------------------------------
# Checking the result
# ---------------------------------------------------------------------------

open_box = Shell(cube_faces()[:5])
assert not open_box.is_manifold
# an open shell is not refused, and the solid made from it is not valid
assert not Solid(open_box).is_valid

# ---------------------------------------------------------------------------
# Ways to make a surface: each method the page lists gives a face or shell
# ---------------------------------------------------------------------------

arc = ThreePointArc((0, 0, 0), (1, 1, 0), (2, 0, 0)).edge()
bend = Wire(Polyline((1, 0, 0), (2, 0, 1), (2, 0, 2)).edges())
path = Line((0, 0, 0), (0, 0, 3))

# the Face method takes one edge and gives one face
for face in (
    Face.extrude(arc, (0, 0, 1)),
    Face.revolve(bend.edges()[0], 90, Axis.Z),
    Face.sweep(arc, path),
):
    assert isinstance(face, Face)

# the Shell method takes a wire and gives a face for each of its edges
for shell in (
    Shell.extrude(bend, (0, 1, 0)),
    Shell.revolve(bend, 90, Axis.Z),
    Shell.sweep(bend, Line((1, 0, 0), (1, 3, 0))),
):
    assert isinstance(shell, Shell) and len(shell.faces()) == 2

# a wire of several edges is refused by the Face method
try:
    Face.sweep(bend, Line((1, 0, 0), (1, 3, 0)))
    raise AssertionError("Face.sweep is expected to refuse a wire of two edges")
except ValueError:
    pass

# the loft operation makes the solid directly from flat sections
lofted = loft([Circle(1), Pos(0, 0, 2) * Circle(2)])
assert len(lofted.solids()) == 1 and lofted.is_valid

boundary = Wire([arc, Line((2, 0, 0), (0, 0, 0)).edge()])
dome = Face.make_surface(boundary, surface_points=[(1, 0.4, 0.3)])
assert isinstance(dome, Face) and not dome.is_planar
# the dome passes through the point it was given
assert dome.distance_to(Vertex(1, 0.4, 0.3)) < 1e-4
ruled = Face.make_surface_from_curves(
    arc, Pos(0, 0, 2) * Line((0, 0, 0), (2, 0, 0)).edge()
)
assert isinstance(ruled, Face)
grid = [[(x, y, 0.2 * x * y) for y in range(3)] for x in range(3)]
assert isinstance(Face.make_bezier_surface(grid), Face)
assert isinstance(Face.make_surface_from_array_of_points(grid), Face)
for method in ("make_surface_patch", "make_gordon_surface"):
    assert callable(getattr(Face, method))

# a face and its mirror image share their boundary, and close into a solid
lens = Shell([dome, dome.mirror(Plane.XY)])
assert lens.is_manifold and Solid(lens).is_valid and Solid(lens).volume > 0
