"""
A parametric part tutorial

name: parametric_part.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "A parametric part" tutorial lives here,
    between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. Each step is written twice, once in builder mode and once in
    algebra mode, and the two are checked against each other so that the tabs
    on the page cannot drift apart. Run it from its own directory; the images
    are written to ``assets/parametric_part``.

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

from pathlib import Path

from build123d.topology import Shape

# [setup]
from build123d import *
from bd_materials import FinishedMaterial, metals

length = 300  # mm
load = 200  # N
max_deflection = 1  # mm
width = 20  # mm
material = metals.aluminum()
# [setup]

OUTPUT = Path("assets/parametric_part")
OUTPUT.mkdir(parents=True, exist_ok=True)
VIEW_FROM = Vector(230, -330, 200)  # relative to the middle of the part


def render_part(part: Shape, name: str, selected: list[Shape] | None = None) -> None:
    """Write a part as an SVG line drawing, with any selected sketches drawn
    over it in colour."""
    look_at = part.bounding_box().center()
    viewpoint = look_at + VIEW_FROM
    visible, hidden = part.drawing_view(viewpoint, look_at=look_at)
    size = Compound(children=visible + hidden).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0x969696, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Selected", line_color=0xCC0000, line_weight=1.1)
    exporter.add_shape(hidden, layer="Hidden")
    exporter.add_shape(visible, layer="Visible")
    if selected:
        chosen = Compound(children=selected).drawing_view(viewpoint, look_at=look_at)
        exporter.add_shape(chosen.visible + chosen.hidden, layer="Selected")
    exporter.write(OUTPUT / f"beam_{name}.svg")


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 2: from the requirement to a dimension
# ---------------------------------------------------------------------------

# [sizing]
modulus = material.material.modulus_of_elasticity.min * 1000  # GPa to MPa
section_depth = (4 * load * length**3 / (modulus * width * max_deflection)) ** (1 / 3)
print(section_depth)
# [sizing]

# the beam this gives does bend by max_deflection under the load
second_moment = width * section_depth**3 / 12
assert abs(load * length**3 / (3 * modulus * second_moment) - max_deflection) < 1e-9

# ---------------------------------------------------------------------------
# Step 3: draw it
# ---------------------------------------------------------------------------

# [draw_builder]
with BuildPart() as beam:
    with BuildSketch(Plane.YZ) as cross_section:
        Rectangle(width, section_depth)
    extrude(amount=length)
# [draw_builder]
builder_result = beam.part

# [draw_algebra]
cross_section = Plane.YZ * Rectangle(width, section_depth)
beam = extrude(cross_section, amount=length)
# [draw_algebra]

assert same(builder_result, beam)
assert len(beam.solids()) == 1 and beam.is_valid
size = beam.bounding_box().size
assert abs(size.X - length) < 1e-6 and abs(size.Y - width) < 1e-6
assert abs(size.Z - section_depth) < 1e-6
render_part(beam, "drawn", selected=[cross_section])
drawn = beam

# ---------------------------------------------------------------------------
# Step 4: make it an object
# ---------------------------------------------------------------------------


# [object_builder]
class Beam(BasePartObject):
    """A beam fixed at one end, deep enough that a load on its free end
    bends it by no more than max_deflection"""

    def __init__(
        self,
        length: float,
        load: float,
        max_deflection: float,
        material: FinishedMaterial,
        width: float = 20,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        modulus = material.material.modulus_of_elasticity.min * 1000
        section_depth = (
            4 * load * length**3 / (modulus * width * max_deflection)
        ) ** (1 / 3)

        with BuildPart() as beam:
            with BuildSketch(Plane.YZ) as cross_section:
                Rectangle(width, section_depth)
            extrude(amount=length)

        super().__init__(part=beam.part, rotation=rotation, align=align, mode=mode)
        self.section_depth = section_depth
        self.material = material
        self.label = f"{material.material.name} Beam"


beam = Beam(length, load, max_deflection, material)
# [object_builder]
BuilderBeam = Beam
builder_result = beam


# [object_algebra]
class Beam(BasePartObject):
    """A beam fixed at one end, deep enough that a load on its free end
    bends it by no more than max_deflection"""

    def __init__(
        self,
        length: float,
        load: float,
        max_deflection: float,
        material: FinishedMaterial,
        width: float = 20,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        modulus = material.material.modulus_of_elasticity.min * 1000
        section_depth = (
            4 * load * length**3 / (modulus * width * max_deflection)
        ) ** (1 / 3)

        cross_section = Plane.YZ * Rectangle(width, section_depth)
        beam = extrude(cross_section, amount=length)

        super().__init__(part=beam, rotation=rotation, align=align, mode=mode)
        self.section_depth = section_depth
        self.material = material
        self.label = f"{material.material.name} Beam"


beam = Beam(length, load, max_deflection, material)
# [object_algebra]

assert same(builder_result, beam) and same(beam, drawn)
assert isinstance(beam, Beam) and isinstance(beam, Part)
assert beam.label == builder_result.label == "Alu_G6061_T6 Beam"
assert abs(beam.section_depth - section_depth) < 1e-9
assert abs(builder_result.section_depth - section_depth) < 1e-9

# ---------------------------------------------------------------------------
# Step 5: use it like a built-in object
# ---------------------------------------------------------------------------

# [use_builder]
wall_thickness, wall_width, wall_height = 15, 140, 80
spacing = 80

with BuildPart() as bracket:
    Box(
        wall_thickness,
        wall_width,
        wall_height,
        align=(Align.MAX, Align.CENTER, Align.CENTER),
    )
    with Locations((0, -spacing / 2, 0), (0, spacing / 2, 0)):
        Beam(length, load, max_deflection, material)
# [use_builder]
builder_result = bracket.part
with BuildPart() as check:
    Box(
        wall_thickness,
        wall_width,
        wall_height,
        align=(Align.MAX, Align.CENTER, Align.CENTER),
    )
    with Locations((0, -spacing / 2, 0), (0, spacing / 2, 0)):
        BuilderBeam(length, load, max_deflection, material)
assert same(check.part, builder_result)

# [use_algebra]
wall_thickness, wall_width, wall_height = 15, 140, 80
spacing = 80

wall = Box(
    wall_thickness,
    wall_width,
    wall_height,
    align=(Align.MAX, Align.CENTER, Align.CENTER),
)
arms = Locations((0, -spacing / 2, 0), (0, spacing / 2, 0)) * Beam(
    length, load, max_deflection, material
)
bracket = wall + arms
# [use_algebra]

assert same(builder_result, bracket)
assert len(bracket.solids()) == 1 and bracket.is_valid
assert abs(bracket.bounding_box().size.X - (length + wall_thickness)) < 1e-6
render_part(bracket, "bracket")

# rotation, align and mode behave as they do on a built-in object
upright = Beam(length, load, max_deflection, material, rotation=(0, -90, 0))
assert abs(upright.bounding_box().size.Z - length) < 1e-6
on_floor = Beam(
    length,
    load,
    max_deflection,
    material,
    align=(Align.MIN, Align.CENTER, Align.MIN),
)
assert abs(on_floor.bounding_box().min.Z) < 1e-6
with BuildPart() as socket:
    Box(40, 60, 60)
    Beam(length, load, max_deflection, material, mode=Mode.SUBTRACT)
assert socket.part.volume < 40 * 60 * 60 - 1

# ---------------------------------------------------------------------------
# Step 6: change the requirement
# ---------------------------------------------------------------------------

# [materials]
for material in (metals.aluminum(), metals.mild_steel(), metals.titanium()):
    beam = Beam(length, load, max_deflection, material)
    print(f"{beam.label}: {beam.section_depth:.1f} mm deep, {beam.mass():.0f} g")
# [materials]

family = [
    Beam(length, load, max_deflection, choice)
    for choice in (metals.aluminum(), metals.mild_steel(), metals.titanium())
]
assert family[1].section_depth < family[2].section_depth < family[0].section_depth
row = [Pos(Y=-60 * index) * beam for index, beam in enumerate(family)]
render_part(Compound(children=row), "materials")

# a heavier load, or a tighter limit, gives a deeper beam
heavy = Beam(length, 4 * load, max_deflection, metals.aluminum())
stiff = Beam(length, load, max_deflection / 4, metals.aluminum())
assert heavy.section_depth > family[0].section_depth
assert abs(heavy.section_depth - stiff.section_depth) < 1e-9
