"""
Geometry and topology documentation examples

name: geometry_and_topology.py
by:   Gumyr
date: November 27th 2026

desc:
    Every code example of the "Geometry and topology" page lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. Each statement the page makes is checked, and this
    script also renders the SVG images the page embeds. Run it from its own
    directory; the images are written to ``assets/geometry_and_topology``.

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

from math import pi, sin
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

from build123d import *
from build123d.topology import Shape

OUTPUT = Path("assets/geometry_and_topology")
OUTPUT.mkdir(parents=True, exist_ok=True)

VIEW = Vector(1, -1, 0.7).normalized()

# ---------------------------------------------------------------------------
# Rendering helpers: line drawings written as SVG, one layer per meaning
# ---------------------------------------------------------------------------

Layers = dict[str, list[Shape]]


def new_layers() -> Layers:
    """The layers every image is made of, empty."""
    return {
        name: []
        for name in ("Outline", "Hidden", "Beyond", "Seam", "Pole", "Hole", "Text")
    }


def seen(
    shape: Shape, shift: float = 0.0, view: Vector = VIEW
) -> tuple[list[Edge], list[Edge]]:
    """The visible and hidden lines of a shape from the page's viewpoint,
    moved ``shift`` across the page."""
    visible, hidden = shape.drawing_view(view * 1000, look_at=(0, 0, 0))
    move = Pos(shift, 0, 0)
    return [move * edge for edge in visible], [move * edge for edge in hidden]


def label(text: str, x: float, y: float, size: float) -> Shape:
    """A piece of text centred on a point of the page."""
    return Pos(x, y) * Text(text, size)


def drawing_order(shapes: list[Shape]) -> list[Shape]:
    """Shapes sorted by where they lie, so the SVG comes out the same every
    run; text is taken apart into its faces so they can be ordered too."""

    def key(shape: Shape) -> tuple:
        if isinstance(shape, Edge):
            ends = sorted(
                (round(shape.position_at(t).X, 4), round(shape.position_at(t).Y, 4))
                for t in (0.0, 1.0)
            )
            middle = shape.position_at(0.5)
            return (*ends, round(middle.X, 4), round(middle.Y, 4))
        centre = shape.center()
        return (round(centre.X, 4), round(centre.Y, 4), round(shape.area, 6))

    pieces = [
        piece
        for shape in shapes
        for piece in (shape.faces() if isinstance(shape, Compound) else [shape])
    ]
    return sorted(pieces, key=key)


def write(layers: Layers, name: str) -> None:
    """Write the layers as one SVG, 120 wide."""
    scene = Compound(children=[s for shapes in layers.values() for s in shapes])
    svg = ExportSVG(scale=120 / scene.bounding_box().size.X, margin=4)
    svg.add_layer("Outline", line_weight=0.4)
    svg.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
    svg.add_layer("Beyond", line_color=0x636363, line_type=LineType.DASHED)
    svg.add_layer("Seam", line_color=0x1E4FA3, line_weight=0.9)
    svg.add_layer("Pole", line_color=0xC0392B, line_weight=0.9)
    svg.add_layer("Hole", line_color=0x1E8449, line_weight=0.7)
    svg.add_layer("Text", fill_color="black", line_color=None)
    for layer, shapes in layers.items():
        if shapes:
            svg.add_shape(drawing_order(shapes), layer)
    svg.write(OUTPUT / f"{name}.svg")


def frame_of(
    flat_view: Face, shift: float, scale: tuple[float, float]
) -> tuple[list[Edge], list[Edge]]:
    """The outline and the holes of a (u, v) picture, stretched to suit the
    page, centred, and moved ``shift`` across it."""
    box = flat_view.bounding_box()
    stretch = Matrix(
        [[scale[0], 0, 0, 0], [0, scale[1], 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    move = Pos(
        shift - scale[0] * (box.min.X + box.max.X) / 2,
        -scale[1] * (box.min.Y + box.max.Y) / 2,
    )

    def placed(wire: Wire) -> list[Edge]:
        return [move * edge.transform_geometry(stretch) for edge in wire.edges()]

    holes = [edge for wire in flat_view.inner_wires() for edge in placed(wire)]
    return placed(flat_view.outer_wire()), holes


def upright(edge: Edge) -> bool:
    """Does an edge of a (u, v) picture run up the page?"""
    return abs((edge @ 0).X - (edge @ 1).X) < 1e-6


def raw_edges(face: Face) -> tuple[int, int]:
    """How many edge uses the kernel holds for a face, and how many of them
    are degenerate."""
    explorer = TopExp_Explorer(face.wrapped, TopAbs_ShapeEnum.TopAbs_EDGE)
    total = degenerate = 0
    while explorer.More():
        total += 1
        degenerate += BRep_Tool.Degenerated_s(TopoDS.Edge(explorer.Current()))
        explorer.Next()
    return total, degenerate


def near(first: float, second: float, tolerance: float = 1e-4) -> bool:
    """Are two numbers the same?"""
    return abs(first - second) < tolerance


# ---------------------------------------------------------------------------
# Limitless and limited
# ---------------------------------------------------------------------------

# [limits]
plate = Rectangle(40, 20).face()
rod = Edge.make_line((0, 0), (30, 0))

Plane(plate)  # the plane the face is a piece of: an origin and directions
Axis(rod)  # the line the edge is a piece of: a position and a direction

plate.area  # 800: a face has a size
rod.length  # 30: so has an edge
# [limits]

assert Plane(plate).z_dir == Vector(0, 0, 1)
assert Axis(rod).direction == Vector(1, 0, 0)
assert near(plate.area, 800) and near(rod.length, 30)
assert not hasattr(Plane.XY, "area") and not hasattr(Axis.X, "length")

# [surface]
wall = Cylinder(3, 10).faces().filter_by(GeomType.CYLINDER)[0]

wall.geom_type  # GeomType.CYLINDER: the surface underneath
wall.radius  # 3: all the surface needs, besides where its axis is
wall.area  # 188.5: the face is ten units of it
# [surface]

assert wall.geom_type == GeomType.CYLINDER
assert near(wall.radius, 3) and near(wall.area, 2 * pi * 3 * 10)

layers = new_layers()
sheet = Rectangle(40, 20).face()
layers["Outline"] += seen(sheet)[0]
layers["Beyond"] += seen(Rectangle(64, 40).face())[0]
tube_visible, tube_hidden = seen(wall, 70)
layers["Outline"] += tube_visible
layers["Hidden"] += tube_hidden
beyond = Cylinder(3, 34).faces().filter_by(GeomType.CYLINDER)[0]
layers["Beyond"] += [
    edge
    for edge in seen(beyond, 70)[0]
    if edge.geom_type == GeomType.LINE and edge.length > 20
]
layers["Text"] += [
    label("a Face on a Plane", 0, -22, 3),
    label("a Face on a cylinder", 70, -22, 3),
]
write(layers, "limits")

# ---------------------------------------------------------------------------
# Every edge of a face lives twice, and the seam
# ---------------------------------------------------------------------------

# [two_views]
wall = Cylinder(3, 10).faces().filter_by(GeomType.CYLINDER)[0]
flat_view = wall.uv_face  # the boundary as the surface's parameters see it

len(wall.edges())  # 3: two circles and the seam between them
len(flat_view.edges())  # 4: a rectangle, with the seam as two of its sides
wall.seams  # the one edge that is used twice
# [two_views]

assert len(wall.edges()) == 3 and len(flat_view.edges()) == 4
assert len(wall.seams) == 1 and wall.seams[0].geom_type == GeomType.LINE
uv_box = flat_view.bounding_box()
assert near(uv_box.size.X, 2 * pi) and near(uv_box.size.Y, 10)
assert raw_edges(wall) == (4, 0)

layers = new_layers()
visible, hidden = seen(wall)
layers["Outline"] += visible
layers["Hidden"] += hidden
layers["Seam"] += seen(wall.seams[0])[0]
u_scale = 1.6  # a radian of u drawn 1.6 wide, so the rectangle reads well
for side in frame_of(flat_view, 24, (u_scale, 1))[0]:
    layers["Seam" if upright(side) else "Outline"].append(side)
half = pi * u_scale
layers["Text"] += [
    label("the face", 0, -9, 1.3),
    label("its (u, v) picture", 24, -9, 1.3),
    label("u", 24, -6.3, 1.1),
    label("v", 24 + half + 1.2, 0, 1.1),
    label("seam", 24 - half, 5.9, 1.1),
    label("seam", 24 + half, 5.9, 1.1),
    label("seam", 4.6, 3.2, 1.1),
]
write(layers, "cylinder_uv")

# ---------------------------------------------------------------------------
# Degenerate edges
# ---------------------------------------------------------------------------

# [sphere]
ball = Sphere(3).faces()[0]

len(ball.edges())  # 1: the seam, half a circle from pole to pole
len(ball.uv_face.edges())  # 4: the seam twice, and a side for each pole
# [sphere]

assert len(ball.edges()) == 1 and ball.edges()[0] == ball.seams[0]
assert near(ball.edges()[0].length, pi * 3)
assert len(ball.uv_face.edges()) == 4
assert raw_edges(ball) == (4, 2)
uv_box = ball.uv_face.bounding_box()
assert near(uv_box.size.X, 2 * pi) and near(uv_box.size.Y, pi)

# a cone has one: its apex
cone_wall = Cone(3, 0, 5).faces().filter_by(GeomType.CONE)[0]
assert raw_edges(cone_wall) == (4, 1) and len(cone_wall.edges()) == 2

# the kernel's sweep cannot take such a boundary, so it is refused
try:
    sweep(ball, Edge.make_line((0, 0, 0), (0, 0, 10)))
    raise AssertionError("a sphere face is not expected to sweep")
except ValueError:
    pass

layers = new_layers()
visible, hidden = seen(ball)
layers["Outline"] += [e for e in visible if e.length > 10]  # the silhouette
layers["Seam"] += seen(ball.seams[0])[0]
for pole in (Vertex(0, 0, 3), Vertex(0, 0, -3)):
    spot = Edge.make_line(pole.center(), pole.center() + (0, 0, 1e-3))
    centre = seen(spot)[0][0] @ 0
    layers["Pole"].append(Pos(centre.X, centre.Y) * Circle(0.12).edge())
for side in frame_of(ball.uv_face, 13, (1, 1))[0]:
    layers["Seam" if upright(side) else "Pole"].append(side)
layers["Text"] += [
    label("the face", 0, -4.6, 0.75),
    label("its (u, v) picture", 13, -4.6, 0.75),
    label("pole", 13, 2.1, 0.62),
    label("pole", 13, -2.1, 0.62),
    label("seam", 13 - pi - 1.3, 0, 0.62),
    label("seam", 13 + pi + 1.3, 0, 0.62),
]
write(layers, "sphere_uv")

# ---------------------------------------------------------------------------
# Writing in the flat
# ---------------------------------------------------------------------------

# [write]
wall = Cylinder(3, 10).faces().filter_by(GeomType.CYLINDER)[0]
frame = wall.uv_frame(wall.location_at(0.25, 0.5))  # flat origin, mid face

(disc,) = frame.write_face(Circle(2).face())  # a face on the cylinder
punched, *_ = frame.punch(Circle(2).face())  # the wall with a hole

disc.area  # 12.566: the area of the flat circle, kept
disc.edge().length  # 12.566: so is its circumference
# [write]

assert disc.geom_type == GeomType.CYLINDER
assert near(disc.area, pi * 4) and near(disc.edge().length, 4 * pi)
assert near(punched.area, wall.area - pi * 4)
# written, not approximated: the outline lies on the cylinder itself
assert all(
    near(Vector((disc.edge() @ t).X, (disc.edge() @ t).Y).length, 3, 1e-6)
    for t in (0, 0.13, 0.5, 0.77)
)
# the hole's picture in (u, v) is not a circle: u is an angle
hole_uv = punched.uv_face.inner_wires()[0].bounding_box()
assert near(hole_uv.size.X, 4 / 3) and near(hole_uv.size.Y, 4)

layers = new_layers()
layers["Hole"].append(Circle(2).edge())
layers["Beyond"] += Rectangle(7, 7).edges()
turned = Rot(0, 0, -135) * punched  # bring the hole round to face the viewer
level = Vector(1, -1, 0.3).normalized()  # nearer side on, so the hole reads
layers["Outline"] += seen(Rot(0, 0, -135) * wall, 13, level)[0]
layers["Hole"] += [
    line
    for edge in turned.inner_wires()[0].edges()
    for line in seen(edge, 13, level)[0]
]
outline, holes = frame_of(punched.uv_face, 30, (u_scale, 1))
layers["Outline"] += outline
layers["Hole"] += holes
layers["Text"] += [
    label("drawn flat", 0, -8, 1.2),
    label("written on the face", 13, -8, 1.2),
    label("in (u, v)", 30, -8, 1.2),
]
write(layers, "written")

# [stretch]
ball = Sphere(3).faces()[0]
frame = ball.uv_frame(ball.location_at(0.25, 0.5))

(cap,) = frame.write_face(Circle(2).face())

cap.edge().length  # 11.656, where the flat circle measures 12.566
# [stretch]

# distances from the origin are true, so the cap is a circle of the sphere
# two units from its centre along the surface, and that circle is shorter
assert near(cap.edge().length, 2 * pi * 3 * sin(2 / 3), 1e-3)
assert cap.edge().length < 4 * pi - 0.9

# a cone unrolls exactly, as a cylinder does
slope = Cone(6, 3, 8).faces().filter_by(GeomType.CONE)[0]
(patch,) = slope.uv_frame(slope.location_at(0.25, 0.5)).write_face(Circle(2).face())
assert near(patch.area, pi * 4, 1e-3) and near(patch.edge().length, 4 * pi, 1e-3)

# ---------------------------------------------------------------------------
# The sheet metal case
# ---------------------------------------------------------------------------

# [sheet]
with BuildSheet(thickness=1, bend_radius=3) as bracket:
    with BuildSketch():
        Rectangle(60, 30)
        with Locations((6, 0)):
            Circle(5, mode=Mode.SUBTRACT)  # drilled while the sheet is flat
    # a fold line at x = 0: split the blank into two coplanar flats
    split(bracket.flats()[0], bisect_by=Plane.YZ, keep=Keep.BOTH)
    fold_line = bracket.flats().sort_by(Axis.X)[0].fold_lines()[0]
    bend(fold_line, angle=90)  # the hole rolls into the bend
    flat, face_map = unfold()  # and comes back a circle
# [sheet]

builder_sheet = bracket.sheet

# [sheet_algebra]
parameters = SheetMetalParameters(thickness=1, bend_radius=3)
drilled = Rectangle(60, 30) - Pos(6, 0) * Circle(5)  # drilled while flat
# a fold line at x = 0: two coplanar flats joined into one sheet
halves = split(drilled, bisect_by=Plane.YZ, keep=Keep.BOTH)
blank = Shell(halves.faces())
fold_line = blank.flats().sort_by(Axis.X)[0].fold_lines()[0]
sheet = bend(fold_line, angle=90, sheet_parameters=parameters)
flat, face_map = sheet.unfold(parameters)  # the hole comes back a circle
# [sheet_algebra]

assert near(builder_sheet.area, sheet.area, 1e-6)
assert len(builder_sheet.faces()) == len(sheet.faces()) == 3


def hole_edges_of(pattern: Shell, centre: Vector, radius: float) -> list[Edge]:
    """The edges of a flat pattern lying on a circle."""
    return [
        edge
        for edge in pattern.edges()
        if all(near((edge @ t - centre).length, radius, 1e-3) for t in (0, 0.3, 0.7, 1))
    ]


for pattern in (bracket.sheet.unfold(bracket.sheet_parameters).flat, flat):
    # every edge of the hole lies on the drilled circle, all the way round
    rim = hole_edges_of(pattern, Vector(6, 0), 5)
    assert near(sum(edge.length for edge in rim), 2 * pi * 5, 1e-2)
    assert near(pattern.area, 60 * 30 - pi * 25, 0.05)

# in the folded part the hole is partly on the bend, where it is no circle
bend_face = sheet.faces().filter_by(GeomType.CYLINDER)[0]
on_bend = [e for e in bend_face.edges() if e.geom_type == GeomType.BSPLINE]
assert len(on_bend) == 1
# and no flat curve either: it leaves the plane through three of its points
points = [on_bend[0] @ t for t in (0, 0.2, 0.5, 0.8)]
normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
assert abs((points[3] - points[0]).dot(normal)) > 0.1

layers = new_layers()
solid = thicken(sheet, sheet_parameters=parameters)
visible, hidden = seen(Pos(10, 0, -12) * solid)
layers["Outline"] += visible
flat_edges = [Pos(62, -4) * edge for edge in flat.edges()]
rim_edges = hole_edges_of(Shell((Pos(62, -4) * flat).faces()), Vector(68, -4), 5)
layers["Outline"] += [
    e
    for e in flat_edges
    if not any(near((e @ 0.5 - r @ 0.5).length, 0) for r in rim_edges)
]
layers["Hole"] += rim_edges
layers["Text"] += [
    label("folded", 2, -27, 3),
    label("unfolded", 62, -27, 3),
]
write(layers, "sheet_hole")
