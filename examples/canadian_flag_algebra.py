"""
for details see `canadian_flag.py`
"""

# [Imports]
from math import sin, cos, pi
from build123d import *
from ocp_vscode import show

# [Parameters]
# Canadian Flags have a 2:1 aspect ratio
height = 50
width = 2 * height
wave_amplitude = 3


# [Code]
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

field_planar = Plane.XY.offset(10) * Rectangle(width / 4, height, align=Align.MIN)
west_field_planar = field_planar.faces()[0]
east_field_planar = mirror(west_field_planar, Plane.YZ.offset(width / 2))

l1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
l2 = Polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
r1 = RadiusArc(l1 @ 1, l2 @ 0, 0.0271)
l3 = Polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
r2 = TangentArc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
l4 = Polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
r3 = SagittaArc(l3 @ 1, l4 @ 0, 0.003)
l5 = Polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
r4 = ThreePointArc(l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0)
l6 = Polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
s = Spline(
    l5 @ 1,
    l6 @ 0,
    tangents=(l5 % 1, l6 % 0),
    tangent_scalars=(2, 2),
)
l7 = Line((0.0692, 0.7808), (0.0000, 0.9167))
r5 = TangentArc(l6 @ 1, l7 @ 0, tangent=l6 % 1)

outline = l1 + [l2, r1, l3, r2, l4, r3, l5, r4, l6, s, l7, r5]
outline += mirror(outline, Plane.YZ)

maple_leaf_planar = make_face(outline)

center_field_planar = (
    Rectangle(1, 1, align=(Align.CENTER, Align.MIN)) - maple_leaf_planar
)


def scale_move(obj):
    return Plane((width / 2, 0, 10)) * scale(obj, height)


def project(obj):
    return obj.faces()[0].project_to_shape(the_wind, (0, 0, -1))[0]


maple_leaf_planar = scale_move(maple_leaf_planar)
center_field_planar = scale_move(center_field_planar)

west_field = project(west_field_planar)
west_field.color = Color("red")
east_field = project(east_field_planar)
east_field.color = Color("red")
center_field = project(center_field_planar)
center_field.color = Color("white")
maple_leaf = project(maple_leaf_planar)
maple_leaf.color = Color("red")

canadian_flag = Compound(children=[west_field, east_field, center_field, maple_leaf])
show(Rot(90, 0, 0) * canadian_flag)
# [End]
