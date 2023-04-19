"""

Projection Examples: Canadian Flag in the Wind

name: canadian_flag.py
by:   Gumyr
date: February 23th 2023

desc: A Canadian Flag blowing in the wind created by projecting planar
      faces onto a non-planar face (the_wind).

      This example also demonstrates building complex lines that snap to
      existing features.

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
from math import sin, cos, pi
from build123d import *

# Canadian Flags have a 2:1 aspect ratio
height = 50
width = 2 * height
wave_amplitude = 3


def surface(amplitude, u, v):
    """Calculate the surface displacement of the flag at a given position"""
    return v * amplitude / 20 * cos(3.5 * pi * u) + amplitude / 10 * v * sin(
        1.1 * pi * v
    )


# Note that the surface to project on must be a little larger than the faces
# being projected onto it to create valid projected faces
the_wind = Face.make_surface_from_array_of_points(
    [
        [
            Vector(
                width * (v * 1.1 / 40 - 0.05),
                height * (u * 1.2 / 40 - 0.1),
                height * surface(wave_amplitude, u / 40, v / 40) / 2,
            )
            for u in range(41)
        ]
        for v in range(41)
    ]
)
with BuildSketch(Plane.XY.offset(10)) as west_field_builder:
    Rectangle(width / 4, height, align=(Align.MIN, Align.MIN))
west_field_planar = west_field_builder.sketch.faces()[0]
east_field_planar = west_field_planar.mirror(Plane.YZ.offset(width / 2))

with BuildSketch(Plane((width / 2, 0, 10))) as center_field_builder:
    Rectangle(width / 2, height, align=(Align.CENTER, Align.MIN))
    with BuildSketch(mode=Mode.SUBTRACT) as maple_leaf_builder:
        with BuildLine() as outline:
            l1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
            l2 = Polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
            RadiusArc(l1 @ 1, l2 @ 0, 0.0271)
            l3 = Polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
            TangentArc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
            l4 = Polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
            SagittaArc(l3 @ 1, l4 @ 0, 0.003)
            l5 = Polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
            ThreePointArc(
                l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0
            )
            l6 = Polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
            Spline(
                l5 @ 1,
                l6 @ 0,
                tangents=(l5 % 1, l6 % 0),
                tangent_scalars=(2, 2),
            )
            l7 = Line((0.0692, 0.7808), (0.0000, 0.9167))
            TangentArc(l6 @ 1, l7 @ 0, tangent=l6 % 1)
            mirror(outline.edges(), Plane.YZ)
        make_face()
        scale(by=height)
maple_leaf_planar = maple_leaf_builder.sketch.faces()[0]
center_field_planar = center_field_builder.sketch.faces()[0]

west_field = west_field_planar.project_to_shape(the_wind, (0, 0, -1))[0]
east_field = east_field_planar.project_to_shape(the_wind, (0, 0, -1))[0]
center_field = center_field_planar.project_to_shape(the_wind, (0, 0, -1))[0]
maple_leaf = maple_leaf_planar.project_to_shape(the_wind, (0, 0, -1))[0]

if "show_object" in locals():
    # show_object(
    #     the_wind,
    #     name="the_wind",
    #     options={"alpha": 0.8, "color": (170 / 255, 85 / 255, 255 / 255)},
    # )
    show_object(west_field, name="west", options={"color": (255, 0, 0)})
    show_object(east_field, name="east", options={"color": (255, 0, 0)})
    show_object(center_field, name="center", options={"color": (255, 255, 255)})
    show_object(maple_leaf, name="maple", options={"color": (255, 0, 0)})
