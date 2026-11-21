"""
The centre of a shape documentation examples

name: center.py
by:   Gumyr
date: November 16th 2026

desc:
    Every code example of the "The centre of a shape" page lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. Each statement the page makes is checked, and this
    script also renders the two SVG images the page embeds. Run it from its
    own directory; the images are written to ``assets/center``.

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

OUTPUT = Path("assets/center")
OUTPUT.mkdir(parents=True, exist_ok=True)


def near(first, second, tolerance: float = 1e-6) -> bool:
    """Are two points the same?"""
    return (Vector(first) - Vector(second)).length < tolerance


def picture(shape: Shape, centers: dict[CenterOf, Vector], name: str) -> None:
    """The shape, its bounding box dashed, and a symbol at each centre, with
    a legend beneath: a square for the bounding box, a triangle for the
    geometry and a circle for the mass."""
    box = shape.bounding_box()
    unit = max(box.size.X, box.size.Y) / 50
    symbols = {
        CenterOf.BOUNDING_BOX: (Rectangle(4 * unit, 4 * unit), "BOUNDING_BOX"),
        CenterOf.GEOMETRY: (RegularPolygon(2.6 * unit, 3, rotation=90), "GEOMETRY"),
        CenterOf.MASS: (Circle(2 * unit), "MASS"),
    }
    outline = Polyline(
        (box.min.X, box.min.Y),
        (box.max.X, box.min.Y),
        (box.max.X, box.max.Y),
        (box.min.X, box.max.Y),
        close=True,
    )
    svg = ExportSVG(scale=100 / max(box.size.X, box.size.Y), margin=5)
    svg.add_layer("bbox", line_type=LineType.DASHED, line_color=0x787878)
    svg.add_layer("symbol", line_color=0x1E4FA3, line_weight=0.5)
    svg.add_layer("text", fill_color="black", line_color=None)
    svg.add_shape(outline, "bbox")
    svg.add_layer("shape", line_weight=0.45)
    svg.add_shape(shape.edges(), "shape")
    row = box.min.Y - 6 * unit
    for column, (center_of, (symbol, label)) in enumerate(symbols.items()):
        if center_of in centers:
            place = centers[center_of]
            svg.add_shape(Pos(place.X, place.Y) * symbol, "symbol")
        left = box.min.X + (0, 24, 43)[column] * unit
        svg.add_shape(Pos(left + 2 * unit, row) * symbol, "symbol")
        svg.add_shape(
            Pos(left + 5 * unit, row)
            * Text(label, 2.2 * unit, align=(Align.MIN, Align.CENTER)),
            "text",
        )
    svg.write(OUTPUT / f"{name}.svg")


# ---------------------------------------------------------------------------
# Three centres
# ---------------------------------------------------------------------------

# [curve]
arc = TangentArc((0, 0), (50, 50), tangent=(1, 0))

arc.center(CenterOf.BOUNDING_BOX)  # (25, 25, 0)
arc.center(CenterOf.GEOMETRY)  # (35.36, 14.64, 0), halfway along the arc
arc.center(CenterOf.MASS)  # (31.83, 18.17, 0)
# [curve]

assert near(arc.center(CenterOf.BOUNDING_BOX), (25, 25, 0))
assert near(arc.center(CenterOf.GEOMETRY), (35.3553, 14.6447, 0), 1e-3)
assert near(arc.center(CenterOf.GEOMETRY), arc @ 0.5)
assert near(arc.center(CenterOf.MASS), (31.831, 18.169, 0), 1e-3)
# only the middle of the arc is a point of the arc
assert arc.distance_to(Vertex(*arc.center(CenterOf.GEOMETRY))) < 1e-6
assert arc.distance_to(Vertex(*arc.center(CenterOf.MASS))) > 1
assert arc.distance_to(Vertex(*arc.center(CenterOf.BOUNDING_BOX))) > 1
picture(arc, {c: arc.center(c) for c in CenterOf}, "one_d_center")

# [face]
angle = make_face(
    Polyline((0, 0), (10, 0), (10, 4), (4, 4), (4, 10), (0, 10), close=True)
).face()

angle.center(CenterOf.BOUNDING_BOX)  # (5, 5, 0), in the notch, off the face
angle.center(CenterOf.MASS)  # (3.875, 3.875, 0), on the face
angle.center(CenterOf.GEOMETRY)  # the same as MASS, for a flat face
# [face]

assert near(angle.center(CenterOf.BOUNDING_BOX), (5, 5, 0))
assert near(angle.center(CenterOf.MASS), (3.875, 3.875, 0))
assert near(angle.center(CenterOf.GEOMETRY), angle.center(CenterOf.MASS))
assert angle.is_inside(angle.center(CenterOf.MASS))
assert not angle.is_inside(angle.center(CenterOf.BOUNDING_BOX))
picture(
    angle,
    {c: angle.center(c) for c in CenterOf},
    "center",
)

# two solids of different size: the mass is drawn toward the larger
pair = Compound([Box(1, 1, 1).solid(), (Pos(10, 0, 0) * Box(3, 3, 3)).solid()])
assert near(pair.center(CenterOf.BOUNDING_BOX), (5.5, 0, 0))
assert near(pair.center(CenterOf.MASS), (270 / 28, 0, 0))

# ---------------------------------------------------------------------------
# Which shapes accept which, and the defaults
# ---------------------------------------------------------------------------

# [defaults]
side = Cylinder(3, 10).faces().filter_by(GeomType.CYLINDER)[0]

side.center()  # (-3, 0, 0): a Face gives GEOMETRY, a point on the wall
Sketch(side.wrapped).center()  # (0, 0, 0): a Sketch gives MASS, on the axis
# [defaults]

assert near(side.center(), side.center(CenterOf.GEOMETRY))
assert near(side.center(), (-3, 0, 0))
assert near(Sketch(side.wrapped).center(), (0, 0, 0))
assert near(Sketch(side.wrapped).center(), side.center(CenterOf.MASS))

edge, wire = arc.edge(), Polyline((0, 0), (10, 0), (10, 4))
assert near(edge.center(), edge.center(CenterOf.GEOMETRY))
assert near(wire.center(), wire.center(CenterOf.GEOMETRY))
assert near(wire.center(), wire @ 0.5) and near(wire.center(), (7, 0, 0))
cone = Cone(5, 0, 10)
for three_d in (cone, cone.solid(), pair, Rectangle(4, 2)):
    assert near(three_d.center(), three_d.center(CenterOf.MASS))

# [geometry_error]
plate = Rectangle(10, 4)

plate.face().center(CenterOf.GEOMETRY)  # a Face: (0, 0, 0)
# plate.center(CenterOf.GEOMETRY)       # a Sketch: raises ValueError
# [geometry_error]

for refused in (plate, cone, cone.solid(), pair):
    try:
        refused.center(CenterOf.GEOMETRY)
        raise AssertionError("GEOMETRY is not expected to be accepted here")
    except ValueError:
        pass
# a vertex and a shell have one centre and take no option
assert near(Vertex(1, 2, 3).center(), (1, 2, 3))
assert near(Box(2, 4, 6).shell().center(), (0, 0, 0))
for single in (Vertex(1, 2, 3), Box(2, 4, 6).shell()):
    try:
        single.center(CenterOf.MASS)  # type: ignore[call-arg]
        raise AssertionError("no option is expected to be accepted here")
    except TypeError:
        pass

# ---------------------------------------------------------------------------
# What GEOMETRY means on a curved face
# ---------------------------------------------------------------------------

# [curved]
wall = (
    (Cylinder(3, 10) & Box(3, 3, 10, align=(Align.MIN, Align.MIN, Align.CENTER)))
    .faces()
    .filter_by(GeomType.CYLINDER)[0]
)

wall.center(CenterOf.GEOMETRY)  # (2.12, 2.12, 0), on the wall
wall.center(CenterOf.MASS)  # (1.91, 1.91, 0), 0.3 inside it
wall.center(CenterOf.BOUNDING_BOX)  # (1.5, 1.5, 0)
# [curved]

assert wall.distance_to(Vertex(*wall.center(CenterOf.GEOMETRY))) < 1e-6
assert abs(wall.distance_to(Vertex(*wall.center(CenterOf.MASS))) - 0.299) < 1e-3
assert near(wall.center(CenterOf.GEOMETRY), wall.position_at(0.5, 0.5))
assert near(wall.center(CenterOf.BOUNDING_BOX), (1.5, 1.5, 0))

# ---------------------------------------------------------------------------
# Which centre the library uses
# ---------------------------------------------------------------------------

# [align]
cone = Cone(5, 0, 10)

cone.center(CenterOf.BOUNDING_BOX)  # (0, 0, 0): Align.CENTER centred this
cone.center()  # (0, 0, -2.5): the centre of mass is lower
# [align]

assert near(cone.center(CenterOf.BOUNDING_BOX), (0, 0, 0))
assert near(cone.center(), (0, 0, -2.5))

# sorting uses each shape's default centre
faces = cone.faces()
assert list(faces.sort_by(Axis.Z)) == sorted(faces, key=lambda f: f.center().Z)
# the base, a flat face at Z = -5, comes before the slope, whose GEOMETRY
# centre is halfway up it
base, slope = faces.sort_by(Axis.Z)
assert base.is_planar and near(base.center(), (0, 0, -5))
assert abs(slope.center().Z) < 1e-6

# [plane]
workplane = Plane(angle)

workplane.origin  # (3.875, 3.875, 0), the face's default centre
# [plane]

assert near(workplane.origin, angle.center())
with BuildSketch() as on_face:
    with Locations(angle):
        Circle(1)
assert near(on_face.sketch.center(), angle.center())
# center_location is the middle of the face's parameter range instead
assert near(angle.center_location.position, (5, 5, 0))
assert near(wall.center_location.position, wall.center())

# ---------------------------------------------------------------------------
# What a centre is not
# ---------------------------------------------------------------------------

# [position]
plate = Rectangle(10, 4, align=Align.MIN)

plate.position  # (0, 0, 0): where its location is
plate.center()  # (5, 2, 0): where the material is
# [position]

assert near(plate.position, (0, 0, 0)) and near(plate.center(), (5, 2, 0))

# [arc_center]
arc.edge().arc_center  # (0, 50, 0): the centre of the circle the arc is part of
# [arc_center]

assert near(arc.edge().arc_center, (0, 50, 0))
assert all(not near(arc.center(c), (0, 50, 0)) for c in CenterOf)
