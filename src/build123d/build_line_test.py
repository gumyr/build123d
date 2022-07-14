from cadquery import Vector
from build123d_common import *
from build_line import *


with BuildLine() as ml:
    l1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
    l2 = Polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
    RadiusArc(l1 @ 1, l2 @ 0, 0.0271)
    l3 = Polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
    TangentArc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
    l4 = Polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
    SagittaArc(l3 @ 1, l4 @ 0, 0.003)
    l5 = Polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
    ThreePointArc(l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0)
    l6 = Polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
    Spline(l5 @ 1, l6 @ 0, tangents=(l5 % 1, l6 % 0), tangent_scalars=(2, 2))
    l7 = Line((0.0692, 0.7808), (0.0000, 0.9167))
    TangentArc(l6 @ 1, l7 @ 0, tangent=l6 % 1)
    MirrorToLine(*ml.edges(), axis=Axis.Y)

with BuildLine() as mirror_example:
    MirrorToLine(
        Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569)), axis=Axis.Y
    )

with BuildLine() as mirror_example2:
    edge1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
    MirrorToLine(edge1, axis=Axis.Y)

with BuildLine() as private_example:
    MirrorToLine(
        Polyline(
            (0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569), mode=Mode.PRIVATE
        ),
        axis=Axis.Y,
    )

with BuildLine() as roller_coaster:
    powerup = Spline(
        (0, 0, 0),
        (50, 0, 50),
        (100, 0, 0),
        tangents=((1, 0, 0), (1, 0, 0)),
        tangent_scalars=(0.5, 2),
    )
    corner = RadiusArc(powerup @ 1, (100, 60, 0), -30)
    screw = Helix(75, 150, 15, center=(75, 40, 15), direction=(-1, 0, 0))
    Spline(corner @ 1, screw @ 0, tangents=(corner % 1, screw % 0))
    Spline(screw @ 1, (-100, 30, 10), powerup @ 0, tangents=(screw % 1, powerup % 0))

with BuildLine() as locs:
    inside_locations = Helix(10, 40, 5, mode=Mode.PRIVATE).distributeLocations(100)
    outside_locations = Helix(10, 40, 7, mode=Mode.PRIVATE).distributeLocations(100)
    for i, o in zip(inside_locations, outside_locations):
        Line(i.position(), o.position())

if "show_object" in locals():
    show_object(ml.line, "maple leaf")
    show_object(mirror_example.line, "mirror_example")
    show_object(mirror_example2.line, "mirror_example2")
    show_object(private_example.line, "private_example")
    show_object(roller_coaster.line, "roller coaster")
    show_object(locs.line, "helix")
