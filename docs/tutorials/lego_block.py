"""
A Lego block tutorial

name: lego_block.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "A Lego block" tutorial lives here, between
    pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/lego_block``.

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

import dis
from pathlib import Path

from build123d.topology import Shape

# [setup]
from build123d import *

studs_wide, studs_long, plates = 2, 6, 3

unit_size, plate_height = 8, 3.2
wall_thickness = 1.2
stud_diameter, stud_height = 4.8, 1.8
tube_outer_diameter, tube_inner_diameter = 6.5, 4.8
post_diameter = 3.2
ridge_width, ridge_depth = 0.6, 0.3

block_length, block_width = unit_size * studs_long, unit_size * studs_wide
base_height = plate_height * plates
# [setup]

OUTPUT = Path("assets/lego_block")
OUTPUT.mkdir(parents=True, exist_ok=True)


def render_sketch(sketch: Shape, name: str, previous: Shape | None = None) -> None:
    """Write a sketch, seen from above, as a filled SVG drawing.

    What the step added to ``previous`` is filled in a stronger colour.
    """
    exporter = ExportSVG(scale=5, margin=4)
    exporter.add_layer("Sketch", fill_color=0xC4D6E8, line_weight=0.3)
    exporter.add_layer("Added", fill_color=0xE58A8A, line_weight=0.3)
    exporter.add_shape(sketch.faces(), layer="Sketch")
    if previous is not None:
        added = sketch - previous
        if added is not None and added.faces():
            exporter.add_shape(added.faces(), layer="Added")
    exporter.write(OUTPUT / f"brick_{name}.svg")


def render_part(part: Shape, name: str, viewpoint=(-60, -90, 80)) -> None:
    """Write a part as an SVG line drawing, seen from ``viewpoint``."""
    look_at = part.bounding_box().center()
    visible, hidden = part.drawing_view(Vector(viewpoint) + look_at, look_at=look_at)
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0xB0B0B0, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_shape(hidden, layer="Hidden")
    exporter.add_shape(visible, layer="Visible")
    exporter.write(OUTPUT / f"brick_{name}.svg")


def size_of(shape: Shape) -> float:
    """A shape's volume, or its area."""
    return shape.volume if shape.solids() else shape.area


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    return (
        abs(size_of(first) - size_of(second)) < 1e-6
        and (first.bounding_box().size - second.bounding_box().size).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 2: the outline and its walls
# ---------------------------------------------------------------------------
# [walls_builder]
with BuildSketch() as plan:
    Rectangle(block_length, block_width)
    offset(amount=-wall_thickness, mode=Mode.SUBTRACT)
# [walls_builder]
builder_result = plan.sketch

# [walls_algebra]
plan = Rectangle(block_length, block_width)
plan -= offset(plan, amount=-wall_thickness)
# [walls_algebra]

assert same(builder_result, plan)
render_sketch(plan, "walls", None)
previous = plan

# ---------------------------------------------------------------------------
# Step 3: bars across the block
# ---------------------------------------------------------------------------
# [bars_builder]
with BuildSketch() as plan:
    Rectangle(block_length, block_width)
    offset(amount=-wall_thickness, mode=Mode.SUBTRACT)
    with GridLocations(0, unit_size, 1, studs_wide):
        Rectangle(block_length, ridge_width)
    with GridLocations(unit_size, 0, studs_long, 1):
        Rectangle(ridge_width, block_width)
# [bars_builder]
builder_result = plan.sketch

# [bars_algebra]
plan = Rectangle(block_length, block_width)
plan -= offset(plan, amount=-wall_thickness)
plan += GridLocations(0, unit_size, 1, studs_wide) * Rectangle(
    block_length, ridge_width
)
plan += GridLocations(unit_size, 0, studs_long, 1) * Rectangle(ridge_width, block_width)
# [bars_algebra]

assert same(builder_result, plan)
render_sketch(plan, "bars", previous)
previous = plan

# ---------------------------------------------------------------------------
# Step 4: cut the bars back to ridges
# ---------------------------------------------------------------------------
# [ridges_builder]
with BuildSketch() as plan:
    Rectangle(block_length, block_width)
    offset(amount=-wall_thickness, mode=Mode.SUBTRACT)
    with GridLocations(0, unit_size, 1, studs_wide):
        Rectangle(block_length, ridge_width)
    with GridLocations(unit_size, 0, studs_long, 1):
        Rectangle(ridge_width, block_width)
    Rectangle(
        block_length - 2 * (wall_thickness + ridge_depth),
        block_width - 2 * (wall_thickness + ridge_depth),
        mode=Mode.SUBTRACT,
    )
# [ridges_builder]
builder_result = plan.sketch

# [ridges_algebra]
plan = Rectangle(block_length, block_width)
plan -= offset(plan, amount=-wall_thickness)
plan += GridLocations(0, unit_size, 1, studs_wide) * Rectangle(
    block_length, ridge_width
)
plan += GridLocations(unit_size, 0, studs_long, 1) * Rectangle(ridge_width, block_width)
plan -= Rectangle(
    block_length - 2 * (wall_thickness + ridge_depth),
    block_width - 2 * (wall_thickness + ridge_depth),
)
# [ridges_algebra]

assert same(builder_result, plan)
render_sketch(plan, "ridges", previous)
previous = plan

# ---------------------------------------------------------------------------
# Step 5: tubes, or posts
# ---------------------------------------------------------------------------
# [supports_builder]
with BuildSketch() as plan:
    Rectangle(block_length, block_width)
    offset(amount=-wall_thickness, mode=Mode.SUBTRACT)
    with GridLocations(0, unit_size, 1, studs_wide):
        Rectangle(block_length, ridge_width)
    with GridLocations(unit_size, 0, studs_long, 1):
        Rectangle(ridge_width, block_width)
    Rectangle(
        block_length - 2 * (wall_thickness + ridge_depth),
        block_width - 2 * (wall_thickness + ridge_depth),
        mode=Mode.SUBTRACT,
    )
    if studs_wide > 1:
        with GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1):
            Circle(tube_outer_diameter / 2)
            Circle(tube_inner_diameter / 2, mode=Mode.SUBTRACT)
    elif studs_long > 1:
        with GridLocations(unit_size, 0, studs_long - 1, 1):
            Circle(post_diameter / 2)
# [supports_builder]
builder_result = plan.sketch

# [supports_algebra]
plan = Rectangle(block_length, block_width)
plan -= offset(plan, amount=-wall_thickness)
plan += GridLocations(0, unit_size, 1, studs_wide) * Rectangle(
    block_length, ridge_width
)
plan += GridLocations(unit_size, 0, studs_long, 1) * Rectangle(ridge_width, block_width)
plan -= Rectangle(
    block_length - 2 * (wall_thickness + ridge_depth),
    block_width - 2 * (wall_thickness + ridge_depth),
)
if studs_wide > 1:
    tubes = GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1)
    plan += tubes * Circle(tube_outer_diameter / 2)
    plan -= tubes * Circle(tube_inner_diameter / 2)
elif studs_long > 1:
    posts = GridLocations(unit_size, 0, studs_long - 1, 1)
    plan += posts * Circle(post_diameter / 2)
# [supports_algebra]

assert same(builder_result, plan)
render_sketch(plan, "supports", previous)
previous = plan

# ---------------------------------------------------------------------------
# Step 6: extrude the plan
# ---------------------------------------------------------------------------
# [extrude_builder]
with BuildPart() as brick:
    with BuildSketch() as plan:
        Rectangle(block_length, block_width)
        offset(amount=-wall_thickness, mode=Mode.SUBTRACT)
        with GridLocations(0, unit_size, 1, studs_wide):
            Rectangle(block_length, ridge_width)
        with GridLocations(unit_size, 0, studs_long, 1):
            Rectangle(ridge_width, block_width)
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        if studs_wide > 1:
            with GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1):
                Circle(tube_outer_diameter / 2)
                Circle(tube_inner_diameter / 2, mode=Mode.SUBTRACT)
        elif studs_long > 1:
            with GridLocations(unit_size, 0, studs_long - 1, 1):
                Circle(post_diameter / 2)
    extrude(amount=base_height - wall_thickness)
# [extrude_builder]
builder_result = brick.part

# [extrude_algebra]
plan = Rectangle(block_length, block_width)
plan -= offset(plan, amount=-wall_thickness)
plan += GridLocations(0, unit_size, 1, studs_wide) * Rectangle(
    block_length, ridge_width
)
plan += GridLocations(unit_size, 0, studs_long, 1) * Rectangle(ridge_width, block_width)
plan -= Rectangle(
    block_length - 2 * (wall_thickness + ridge_depth),
    block_width - 2 * (wall_thickness + ridge_depth),
)
if studs_wide > 1:
    tubes = GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1)
    plan += tubes * Circle(tube_outer_diameter / 2)
    plan -= tubes * Circle(tube_inner_diameter / 2)
elif studs_long > 1:
    posts = GridLocations(unit_size, 0, studs_long - 1, 1)
    plan += posts * Circle(post_diameter / 2)
brick = extrude(plan, amount=base_height - wall_thickness)
# [extrude_algebra]

assert same(builder_result, brick)
render_part(brick, "extrude")

# ---------------------------------------------------------------------------
# Step 7: close the top
# ---------------------------------------------------------------------------
# [lid_builder]
with BuildPart() as brick:
    with BuildSketch() as plan:
        Rectangle(block_length, block_width)
        offset(amount=-wall_thickness, mode=Mode.SUBTRACT)
        with GridLocations(0, unit_size, 1, studs_wide):
            Rectangle(block_length, ridge_width)
        with GridLocations(unit_size, 0, studs_long, 1):
            Rectangle(ridge_width, block_width)
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        if studs_wide > 1:
            with GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1):
                Circle(tube_outer_diameter / 2)
                Circle(tube_inner_diameter / 2, mode=Mode.SUBTRACT)
        elif studs_long > 1:
            with GridLocations(unit_size, 0, studs_long - 1, 1):
                Circle(post_diameter / 2)
    extrude(amount=base_height - wall_thickness)
    with BuildSketch(Plane.XY.offset(base_height - wall_thickness)) as lid:
        Rectangle(block_length, block_width)
    extrude(amount=wall_thickness)
# [lid_builder]
builder_result = brick.part

# [lid_algebra]
plan = Rectangle(block_length, block_width)
plan -= offset(plan, amount=-wall_thickness)
plan += GridLocations(0, unit_size, 1, studs_wide) * Rectangle(
    block_length, ridge_width
)
plan += GridLocations(unit_size, 0, studs_long, 1) * Rectangle(ridge_width, block_width)
plan -= Rectangle(
    block_length - 2 * (wall_thickness + ridge_depth),
    block_width - 2 * (wall_thickness + ridge_depth),
)
if studs_wide > 1:
    tubes = GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1)
    plan += tubes * Circle(tube_outer_diameter / 2)
    plan -= tubes * Circle(tube_inner_diameter / 2)
elif studs_long > 1:
    posts = GridLocations(unit_size, 0, studs_long - 1, 1)
    plan += posts * Circle(post_diameter / 2)
brick = extrude(plan, amount=base_height - wall_thickness)
lid = Plane.XY.offset(base_height - wall_thickness) * Rectangle(
    block_length, block_width
)
brick += extrude(lid, amount=wall_thickness)
# [lid_algebra]

assert same(builder_result, brick)
render_part(brick, "lid")

# ---------------------------------------------------------------------------
# Step 8: the studs
# ---------------------------------------------------------------------------
# [studs_builder]
with BuildPart() as brick:
    with BuildSketch() as plan:
        Rectangle(block_length, block_width)
        offset(amount=-wall_thickness, mode=Mode.SUBTRACT)
        with GridLocations(0, unit_size, 1, studs_wide):
            Rectangle(block_length, ridge_width)
        with GridLocations(unit_size, 0, studs_long, 1):
            Rectangle(ridge_width, block_width)
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        if studs_wide > 1:
            with GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1):
                Circle(tube_outer_diameter / 2)
                Circle(tube_inner_diameter / 2, mode=Mode.SUBTRACT)
        elif studs_long > 1:
            with GridLocations(unit_size, 0, studs_long - 1, 1):
                Circle(post_diameter / 2)
    extrude(amount=base_height - wall_thickness)
    with BuildSketch(Plane.XY.offset(base_height - wall_thickness)) as lid:
        Rectangle(block_length, block_width)
    extrude(amount=wall_thickness)
    top = brick.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(top) as studs:
        with GridLocations(unit_size, unit_size, studs_long, studs_wide):
            Circle(stud_diameter / 2)
    extrude(amount=stud_height)
# [studs_builder]
builder_result = brick.part

# [studs_algebra]
plan = Rectangle(block_length, block_width)
plan -= offset(plan, amount=-wall_thickness)
plan += GridLocations(0, unit_size, 1, studs_wide) * Rectangle(
    block_length, ridge_width
)
plan += GridLocations(unit_size, 0, studs_long, 1) * Rectangle(ridge_width, block_width)
plan -= Rectangle(
    block_length - 2 * (wall_thickness + ridge_depth),
    block_width - 2 * (wall_thickness + ridge_depth),
)
if studs_wide > 1:
    tubes = GridLocations(unit_size, unit_size, studs_long - 1, studs_wide - 1)
    plan += tubes * Circle(tube_outer_diameter / 2)
    plan -= tubes * Circle(tube_inner_diameter / 2)
elif studs_long > 1:
    posts = GridLocations(unit_size, 0, studs_long - 1, 1)
    plan += posts * Circle(post_diameter / 2)
brick = extrude(plan, amount=base_height - wall_thickness)
lid = Plane.XY.offset(base_height - wall_thickness) * Rectangle(
    block_length, block_width
)
brick += extrude(lid, amount=wall_thickness)
top = brick.faces().sort_by(Axis.Z)[-1]
studs = Sketch(
    Plane(top)
    * GridLocations(unit_size, unit_size, studs_long, studs_wide)
    * Circle(stud_diameter / 2)
)
brick += extrude(studs, amount=stud_height)
# [studs_algebra]

assert same(builder_result, brick)
assert abs(brick.volume - 3212.187337781355) < 1e-3  # as examples/lego.py
render_part(brick, "finished")
render_part(brick, "underside", viewpoint=(-60, -90, -80))


# ---------------------------------------------------------------------------
# Step 9: make it an object
# ---------------------------------------------------------------------------
# [object_builder]
class LegoBlock(BasePartObject):
    """A Lego block, such as a 2x4 brick or a 1x8 plate"""

    unit_size, plate_height = 8, 3.2
    wall_thickness = 1.2
    stud_diameter, stud_height = 4.8, 1.8
    tube_outer_diameter, tube_inner_diameter = 6.5, 4.8
    post_diameter = 3.2
    ridge_width, ridge_depth = 0.6, 0.3

    def __init__(
        self,
        studs_wide: int,
        studs_long: int,
        plates: int = 3,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if not 1 <= studs_wide <= studs_long:
            raise ValueError("Give the smaller number of studs first, as in 2x4")

        block_length = self.unit_size * studs_long
        block_width = self.unit_size * studs_wide
        base_height = self.plate_height * plates

        with BuildPart() as brick:
            with BuildSketch() as plan:
                Rectangle(block_length, block_width)
                offset(amount=-self.wall_thickness, mode=Mode.SUBTRACT)
                with GridLocations(0, self.unit_size, 1, studs_wide):
                    Rectangle(block_length, self.ridge_width)
                with GridLocations(self.unit_size, 0, studs_long, 1):
                    Rectangle(self.ridge_width, block_width)
                Rectangle(
                    block_length - 2 * (self.wall_thickness + self.ridge_depth),
                    block_width - 2 * (self.wall_thickness + self.ridge_depth),
                    mode=Mode.SUBTRACT,
                )
                if studs_wide > 1:
                    with GridLocations(
                        self.unit_size, self.unit_size, studs_long - 1, studs_wide - 1
                    ):
                        Circle(self.tube_outer_diameter / 2)
                        Circle(self.tube_inner_diameter / 2, mode=Mode.SUBTRACT)
                elif studs_long > 1:
                    with GridLocations(self.unit_size, 0, studs_long - 1, 1):
                        Circle(self.post_diameter / 2)
            extrude(amount=base_height - self.wall_thickness)
            with BuildSketch(Plane.XY.offset(base_height - self.wall_thickness)) as lid:
                Rectangle(block_length, block_width)
            extrude(amount=self.wall_thickness)
            top = brick.faces().sort_by(Axis.Z)[-1]
            with BuildSketch(top) as studs:
                with GridLocations(
                    self.unit_size, self.unit_size, studs_long, studs_wide
                ):
                    Circle(self.stud_diameter / 2)
            extrude(amount=self.stud_height)

        super().__init__(part=brick.part, rotation=rotation, align=align, mode=mode)
        self.studs_wide, self.studs_long, self.plates = studs_wide, studs_long, plates
        self.base_height = base_height
        kind = "plate" if plates == 1 else "brick"
        self.label = f"Lego {kind} {studs_wide}x{studs_long}"


brick = LegoBlock(2, 6)
# [object_builder]
BuilderLegoBlock = LegoBlock
builder_result = brick


# [object_algebra]
class LegoBlock(BasePartObject):
    """A Lego block, such as a 2x4 brick or a 1x8 plate"""

    unit_size, plate_height = 8, 3.2
    wall_thickness = 1.2
    stud_diameter, stud_height = 4.8, 1.8
    tube_outer_diameter, tube_inner_diameter = 6.5, 4.8
    post_diameter = 3.2
    ridge_width, ridge_depth = 0.6, 0.3

    def __init__(
        self,
        studs_wide: int,
        studs_long: int,
        plates: int = 3,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if not 1 <= studs_wide <= studs_long:
            raise ValueError("Give the smaller number of studs first, as in 2x4")

        block_length = self.unit_size * studs_long
        block_width = self.unit_size * studs_wide
        base_height = self.plate_height * plates

        plan = Rectangle(block_length, block_width)
        plan -= offset(plan, amount=-self.wall_thickness)
        plan += GridLocations(0, self.unit_size, 1, studs_wide) * Rectangle(
            block_length, self.ridge_width
        )
        plan += GridLocations(self.unit_size, 0, studs_long, 1) * Rectangle(
            self.ridge_width, block_width
        )
        plan -= Rectangle(
            block_length - 2 * (self.wall_thickness + self.ridge_depth),
            block_width - 2 * (self.wall_thickness + self.ridge_depth),
        )
        if studs_wide > 1:
            tubes = GridLocations(
                self.unit_size, self.unit_size, studs_long - 1, studs_wide - 1
            )
            plan += tubes * Circle(self.tube_outer_diameter / 2)
            plan -= tubes * Circle(self.tube_inner_diameter / 2)
        elif studs_long > 1:
            posts = GridLocations(self.unit_size, 0, studs_long - 1, 1)
            plan += posts * Circle(self.post_diameter / 2)
        brick = extrude(plan, amount=base_height - self.wall_thickness)
        lid = Plane.XY.offset(base_height - self.wall_thickness) * Rectangle(
            block_length, block_width
        )
        brick += extrude(lid, amount=self.wall_thickness)
        top = brick.faces().sort_by(Axis.Z)[-1]
        studs = Sketch(
            Plane(top)
            * GridLocations(self.unit_size, self.unit_size, studs_long, studs_wide)
            * Circle(self.stud_diameter / 2)
        )
        brick += extrude(studs, amount=self.stud_height)

        super().__init__(part=brick, rotation=rotation, align=align, mode=mode)
        self.studs_wide, self.studs_long, self.plates = studs_wide, studs_long, plates
        self.base_height = base_height
        kind = "plate" if plates == 1 else "brick"
        self.label = f"Lego {kind} {studs_wide}x{studs_long}"


brick = LegoBlock(2, 6)
# [object_algebra]

assert isinstance(brick, LegoBlock) and isinstance(builder_result, BuilderLegoBlock)
assert same(builder_result, brick)
assert abs(brick.volume - 3212.187337781355) < 1e-3
# Neither class may lean on the names of step 1, which the page says can be
# deleted once the class is written.
STEP_1_NAMES = {
    "studs_wide",
    "studs_long",
    "plates",
    "unit_size",
    "plate_height",
    "wall_thickness",
    "stud_diameter",
    "stud_height",
    "tube_outer_diameter",
    "tube_inner_diameter",
    "post_diameter",
    "ridge_width",
    "ridge_depth",
    "block_length",
    "block_width",
    "base_height",
}
for block_class in (BuilderLegoBlock, LegoBlock):
    loaded = {
        i.argval
        for i in dis.get_instructions(block_class.__init__)
        if i.opname == "LOAD_GLOBAL"
    }
    assert not loaded & STEP_1_NAMES
# Both classes agree, and make one solid, across the range of sizes.
for size in [(1, 1), (1, 2), (1, 8), (2, 2), (2, 4), (3, 5), (4, 4)]:
    for height in (1, 3):
        first, second = (c(*size, plates=height) for c in (BuilderLegoBlock, LegoBlock))
        assert same(first, second) and len(first.solids()) == 1
        assert abs(first.bounding_box().size.Z - (3.2 * height + 1.8)) < 1e-6
for block_class in (BuilderLegoBlock, LegoBlock):
    try:
        block_class(4, 2)
        raise AssertionError("4x2 should be refused")
    except ValueError:
        pass
    with BuildPart() as row:
        with Locations((0, 0, 0), (0, 20, 0)):
            block_class(1, 3)
    assert len(row.solids()) == 2

# ---------------------------------------------------------------------------
# Step 10: use it
# ---------------------------------------------------------------------------
# [stack]
unit = LegoBlock.unit_size

base = LegoBlock(2, 6)
plate = Pos(unit, 0, base.base_height) * LegoBlock(2, 4, plates=1)
rail = Pos(unit, unit / 2, base.base_height + plate.base_height) * LegoBlock(1, 4)
stack = Compound(children=[base, plate, rail])

for block in stack.children:
    print(block.label)
# [stack]

assert [b.label for b in stack.children] == [
    "Lego brick 2x6",
    "Lego plate 2x4",
    "Lego brick 1x4",
]
for first, second in ((base, plate), (plate, rail), (base, rail)):
    overlap = first.intersect(second)
    assert overlap is None or sum(s.volume for s in overlap.solids()) < 1e-6
render_part(stack, "stack")
render_part(LegoBlock(1, 4), "posts", viewpoint=(-60, -90, -80))


# [subclass]
class BigBlock(LegoBlock):
    """A block twice the size in every direction"""

    unit_size, plate_height = 16, 6.4
    wall_thickness = 2.4
    stud_diameter, stud_height = 9.6, 3.6
    tube_outer_diameter, tube_inner_diameter = 13, 9.6
    post_diameter = 6.4
    ridge_width, ridge_depth = 1.2, 0.6


big = BigBlock(2, 4)
# [subclass]

assert abs(big.volume - 8 * LegoBlock(2, 4).volume) < 1e-3
