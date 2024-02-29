"""

Projection Examples

name: projection.py
by:   Gumyr
date: January 4th 2023

desc: Projection examples.

license:

    Copyright 2023 Gumyr

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

from build123d import *
from ocp_vscode import show_object

# A sphere used as a projection target
sphere = Solid.make_sphere(50, angle1=-90)

"""Example 1 - Mapping A Face on Sphere"""
projection_direction = Vector(0, 1, 0)

square = Face.make_rect(20, 20, Plane.ZX.offset(-80))
square_projected = square.project_to_shape(sphere, projection_direction)
square_solids = Compound([f.thicken(2) for f in square_projected])
projection_beams = [
    Solid.make_loft(
        [
            square.outer_wire(),
            square.outer_wire().translate(Vector(0, 160, 0)),
        ]
    )
]

"""Example 2 - Flat Projection of Text on Sphere"""
projection_direction = Vector(0, -1, 0)
flat_planar_text_faces = (
    Compound.make_text("Flat", font_size=30).rotate(Axis.X, 90).faces()
)
flat_projected_text_faces = Compound(
    [
        f.project_to_shape(sphere, projection_direction)[0]
        for f in flat_planar_text_faces
    ]
).moved(Location((-100, -100)))
flat_projection_beams = Compound(
    [Solid.extrude(f, projection_direction * 80) for f in flat_planar_text_faces]
).moved(Location((-100, -100)))


"""Example 3 - Project a text string along a path onto a shape"""
arch_path: Edge = (
    sphere.cut(Solid.make_cylinder(80, 100, Plane.YZ).locate(Location((-50, 0, -70))))
    .edges()
    .sort_by(Axis.Z)[0]
)
arch_path_start = Vertex(arch_path.position_at(0))
text = Compound.make_text(
    txt="'the quick brown fox jumped over the lazy dog'",
    font_size=15,
    align=(Align.MIN, Align.CENTER),
)
projected_text = sphere.project_faces(text, path=arch_path)

# Example 1
show_object(sphere, name="sphere_solid", options={"alpha": 0.8})
show_object(square, name="square")
show_object(square_solids, name="square_solids")
show_object(
    Compound(projection_beams),
    name="projection_beams",
    options={"alpha": 0.9, "color": (170 / 255, 170 / 255, 255 / 255)},
)

# Example 2
show_object(
    sphere.moved(Location((-100, -100))),
    name="sphere_solid for text",
    options={"alpha": 0.8},
)
show_object(flat_projected_text_faces, name="flat_projected_text_faces")
show_object(
    flat_projection_beams,
    name="flat_projection_beams",
    options={"alpha": 0.95, "color": (170 / 255, 170 / 255, 255 / 255)},
)

# Example 3
show_object(
    sphere.moved(Location((100, 100))),
    name="sphere_solid for text on path",
    options={"alpha": 0.8},
)
show_object(projected_text.moved(Location((100, 100))), name="projected_text on path")
