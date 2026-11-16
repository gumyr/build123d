"""
How placements combine documentation examples

name: location_arithmetic.py
by:   Gumyr
date: November 16th 2026

desc:
    Every code example of the "How placements combine" page lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. Each statement the page makes about an example is
    checked, and this script also renders the SVG images the page embeds.
    Run it from its own directory; the images are written to
    ``assets/location_arithmetic``.

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

OUTPUT = Path("assets/location_arithmetic")
OUTPUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Rendering helpers: parallel projections written as SVG line drawings. The
# world axes are grey, a frame is three labelled lines in one colour, and a
# face is a tinted outline.
# ---------------------------------------------------------------------------

CAMERA = Vector(2, -0.7, 1.1) * 100
BLUE, ORANGE, GREY = 0x1E4FA3, 0xC05A00, 0x9A9A9A


def _on_page(point: Vector) -> Vector:
    """Where the camera sees a point, found by projecting a very short edge"""
    stub = Edge.make_line(point, point + Vector(1e-4, 1e-4, 1e-4))
    visible = stub.drawing_view(CAMERA, (0, 0, 1), look_at=(0, 0, 0)).visible
    return visible[0].center()


# the projection is parallel, so four points fix it
_O = _on_page(Vector(0, 0, 0))
_EX, _EY, _EZ = (
    _on_page(Vector(*axis)) - _O for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))
)


def on_page(point) -> Vector:
    """A point in space, in the plane of the page"""
    point = Vector(point)
    return _O + _EX * point.X + _EY * point.Y + _EZ * point.Z


Scene = dict[str, list[Shape]]


def frame(
    location: Location,
    size: float,
    layer: str,
    labels: str = "xyz",
    text: float = 0.16,
) -> Scene:
    """Three labelled lines along the axes of a location"""
    origin = location.position
    drawn: Scene = {layer: [], layer + " text": []}
    for direction, label in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), labels):
        tip = (location * Pos(*(Vector(direction) * size))).position
        drawn[layer].append(Edge.make_line(on_page(origin), on_page(tip)))
        beyond = on_page(origin + (tip - origin) * 1.13)
        drawn[layer + " text"].append(Pos(beyond.X, beyond.Y) * Text(label, text))
    return drawn


def tinted(face: Face) -> Scene:
    """A flat face as a tinted outline"""
    corners = [on_page(vertex) for vertex in face.outer_wire().vertices()]
    outline = Wire(
        [
            Edge.make_line(on_page(edge @ 0), on_page(edge @ 1))
            for edge in face.outer_wire().edges()
        ]
    )
    assert len(corners) == 4
    return {"Face": [Face(outline)]}


def solid(part: Shape, layer: str = "Object") -> Scene:
    """The visible edges of a part"""
    visible = part.drawing_view(CAMERA, (0, 0, 1), look_at=(0, 0, 0)).visible
    return {layer: list(visible)}


def write(
    name: str, *panels: tuple[str | None, list[Scene]], text: float = 0.17
) -> None:
    """Lay labelled panels out side by side and write the SVG"""
    layers: Scene = {}
    cursor = 0.0
    for label, scenes in panels:
        merged: Scene = {}
        for scene in scenes:
            for layer, shapes in scene.items():
                merged.setdefault(layer, []).extend(shapes)
        box = Compound(children=[s for shapes in merged.values() for s in shapes])
        extent = box.bounding_box()
        shift = Pos(cursor - extent.min.X, 0, 0)
        for layer, shapes in merged.items():
            layers.setdefault(layer, []).extend(shift * shape for shape in shapes)
        if label:
            layers.setdefault("World text", []).append(
                Pos(cursor + extent.size.X / 2, extent.min.Y - 2 * text)
                * Text(label, text)
            )
        cursor += extent.size.X + 3 * text

    svg = ExportSVG(scale=42, margin=4)
    svg.add_layer("Face", fill_color=0xD6E0F0, line_color=0x7F93B5)
    svg.add_layer("World", line_color=GREY, line_weight=0.25)
    svg.add_layer("World text", fill_color=0x787878, line_color=None)
    svg.add_layer("Start", line_color=GREY, line_weight=0.3)
    svg.add_layer("Frame", line_color=BLUE, line_weight=0.6)
    svg.add_layer("Frame text", fill_color=BLUE, line_color=None)
    svg.add_layer("Local", line_color=ORANGE, line_weight=0.6)
    svg.add_layer("Local text", fill_color=ORANGE, line_color=None)
    svg.add_layer("Object", line_weight=0.45)
    for layer in (
        "Face",
        "World",
        "World text",
        "Start",
        "Frame",
        "Frame text",
        "Local",
        "Local text",
        "Object",
    ):
        if layers.get(layer):
            svg.add_shape(layers[layer], layer)
    svg.write(OUTPUT / f"{name}.svg")


WORLD = frame(Location(), 1.5, "World", "XYZ")


def same_place(first: Shape, second: Shape) -> bool:
    """Do two shapes occupy the same box in space?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (box_1.min - box_2.min).length < 1e-9 and (
        box_1.max - box_2.max
    ).length < 1e-9


# ---------------------------------------------------------------------------
# A location is a frame
# ---------------------------------------------------------------------------

# [frame]
loc = Location((0.1, 0.2, 0.3), (10, 20, 30))

face = loc * Rectangle(1, 2)
# [frame]

assert (face.center() - loc.position).length < 1e-9
assert (face.face().normal_at() - Plane(loc).z_dir).length < 1e-9
write("frame", (None, [tinted(face.face()), WORLD, frame(loc, 1, "Frame")]))

# [plane]
plane = Plane.XZ

face_on_plane = plane * Rectangle(1, 2)
# [plane]

# the rectangle's 1 lies along world X and its 2 along world Z
assert (face_on_plane.bounding_box().size - Vector(1, 0, 2)).length < 1e-9
assert plane.x_dir == Vector(1, 0, 0) and plane.y_dir == Vector(0, 0, 1)
assert plane.z_dir == Vector(0, -1, 0)
assert same_place(face_on_plane, plane.location * Rectangle(1, 2))
write(
    "plane",
    (None, [tinted(face_on_plane.face()), WORLD, frame(plane.location, 1, "Frame")]),
)

# ---------------------------------------------------------------------------
# Each term is expressed in the frame to its left
# ---------------------------------------------------------------------------

# [position]
box = loc * Pos(0.2, 0.4, 0.1) * Box(0.4, 0.2, 0.1)
# [position]

# measured in the frame of loc, the box is at (0.2, 0.4, 0.1)
assert (Plane(loc).to_local_coords(box.center()) - Vector(0.2, 0.4, 0.1)).length < 1e-9
assert (box.center() - Vector(0.2, 0.4, 0.1)).length > 0.1
write(
    "position",
    (None, [tinted(face.face()), WORLD, frame(loc, 1, "Frame"), solid(box)]),
)

# [rotation]
turned = loc * Rot(Z=80) * Box(0.4, 0.2, 0.1)
# [rotation]

# the turn is about the z of the frame: the box stays on the frame's origin
# and its top still faces along the frame's z
assert (turned.center() - loc.position).length < 1e-9
top = turned.faces().sort_by(Axis(loc.position, Plane(loc).z_dir))[-1]
assert (top.normal_at() - Plane(loc).z_dir).length < 1e-9

# [rotation_general]
tumbled = loc * Rot(20, 40, 80) * Box(0.4, 0.2, 0.1)
# [rotation_general]

assert (tumbled.center() - loc.position).length < 1e-9
write(
    "rotation",
    ("Rot(Z=80)", [tinted(face.face()), frame(loc, 1, "Frame"), solid(turned)]),
    (
        "Rot(20, 40, 80)",
        [tinted(face.face()), frame(loc, 1, "Frame"), solid(tumbled)],
    ),
)

# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

# [turn_then_move]
box_1 = loc * Rot(20, 40, 80) * Pos(0.2, 0.4, 0.1) * Box(0.4, 0.2, 0.1)
# [turn_then_move]

# [move_then_turn]
box_2 = loc * Pos(0.2, 0.4, 0.1) * Rot(20, 40, 80) * Box(0.4, 0.2, 0.1)
# [move_then_turn]

# [one_location]
box_3 = loc * Location((0.2, 0.4, 0.1), (20, 40, 80)) * Box(0.4, 0.2, 0.1)
# [one_location]

assert not same_place(box_1, box_2)
assert same_place(box_2, box_3)
# in the first the position is along the axes of the turned frame; in the
# second it is along the axes of loc, and the box turns where it stands
local_1 = loc * Rot(20, 40, 80)
local_2 = loc * Pos(0.2, 0.4, 0.1)
assert (
    Plane(local_1).to_local_coords(box_1.center()) - Vector(0.2, 0.4, 0.1)
).length < 1e-9
assert (box_2.center() - local_2.position).length < 1e-9
write(
    "order",
    (
        "turn, then move",
        [
            tinted(face.face()),
            frame(loc, 1, "Frame"),
            frame(local_1, 0.5, "Local"),
            solid(box_1),
        ],
    ),
    (
        "move, then turn",
        [
            tinted(face.face()),
            frame(loc, 1, "Frame"),
            frame(local_2, 0.5, "Local"),
            solid(box_2),
        ],
    ),
)

# ---------------------------------------------------------------------------
# Two ways to read a chain
# ---------------------------------------------------------------------------

# [readings]
block = Rot(Z=90) * Pos(2, 0, 0) * Box(1, 0.6, 0.4)
# [readings]

# from the right, in the world: move 2 along X, then turn about world Z
moved = Pos(2, 0, 0) * Box(1, 0.6, 0.4)
from_the_right = Rot(Z=90) * moved
# from the left, in frames: turn the frame, then go 2 along its own x
turned_frame = Rot(Z=90)
assert (Plane(turned_frame).x_dir - Vector(0, 1, 0)).length < 1e-9
arrived = turned_frame * Pos(2, 0, 0)
assert same_place(block, from_the_right)
assert (block.center() - arrived.position).length < 1e-9
assert (block.center() - Vector(0, 2, 0)).length < 1e-9
# the long side of the block lies along the frame's x, which is world Y
assert (block.bounding_box().size - Vector(0.6, 1, 0.4)).length < 1e-9
write(
    "readings",
    (
        "from the right, in the world",
        [
            frame(Location(), 3, "World", "XYZ", text=0.3),
            solid(moved, "Start"),
            solid(block),
        ],
    ),
    (
        "from the left, in frames",
        [
            frame(Location(), 3, "World", "XYZ", text=0.3),
            frame(turned_frame, 0.9, "Frame", text=0.3),
            frame(arrived, 0.9, "Local", text=0.3),
            solid(block),
        ],
    ),
    text=0.3,
)

# ---------------------------------------------------------------------------
# Planes in a chain
# ---------------------------------------------------------------------------

# [planes]
on_location = loc * Pos(0.2, 0.4, 0.1) * Box(0.4, 0.2, 0.1)
on_plane = Plane(loc) * Pos(0.2, 0.4, 0.1) * Box(0.4, 0.2, 0.1)
on_face = Plane(face.face()) * Pos(0.2, 0.4, 0.1) * Box(0.4, 0.2, 0.1)
# [planes]

assert same_place(on_location, on_plane)
# the plane of the face has the same origin and normal as loc, so the box is
# the same distance above it, though its x direction is the plane's choice
assert abs(Plane(loc).to_local_coords(on_face.center()).Z - 0.1) < 1e-9
assert isinstance(Plane.XZ * Pos(1, 2, 3), Location)
assert isinstance(Pos(1, 2, 3) * Plane.XZ, Plane)
assert (Plane.XZ * Pos(1, 2, 3)).position == Vector(1, -3, 2)

# ---------------------------------------------------------------------------
# The same in builder mode
# ---------------------------------------------------------------------------

# [builder]
with BuildPart() as nested:
    with Locations(loc):
        with Locations((0.2, 0.4, 0.1)):
            Box(0.4, 0.2, 0.1, rotation=(20, 40, 80))
# [builder]

# [builder_algebra]
chained = loc * Pos(0.2, 0.4, 0.1) * Rot(20, 40, 80) * Box(0.4, 0.2, 0.1)
# [builder_algebra]

assert same_place(nested.part, chained)

# [builder_plane]
with BuildPart(Plane(loc)) as on_a_plane:
    with Locations((0.2, 0.4, 0.1)):
        Box(0.4, 0.2, 0.1, rotation=(20, 40, 80))
# [builder_plane]

assert same_place(on_a_plane.part, chained)

# ---------------------------------------------------------------------------
# Undoing and comparing placements
# ---------------------------------------------------------------------------

# [inverse]
home = loc.inverse() * face  # back at the origin, flat on the XY plane
# [inverse]

assert same_place(home, Rectangle(1, 2))

# [relative]
bracket = Location((5, 0, 2), (0, 0, 45))
hole = Location((6, 1, 2), (0, 0, 45))

hole_on_bracket = bracket.inverse() * hole  # where the hole is, seen from the bracket
# [relative]

assert (hole_on_bracket.position - Vector(2**0.5, 0, 0)).length < 1e-9
assert Vector(*hole_on_bracket.orientation).length < 1e-6
back = bracket * hole_on_bracket
assert (back.position - hole.position).length < 1e-9

# [coordinates]
workplane = Plane(loc)

inside = workplane.to_local_coords(Vector(1, 1, 1))  # a world point, in the frame
outside = workplane.from_local_coords(inside)  # and back again
# [coordinates]

assert (outside - Vector(1, 1, 1)).length < 1e-9
assert (inside - Vector(1, 1, 1)).length > 0.1
