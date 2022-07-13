from cadquery import Vector
from build123d_common import *
from build_line import *
from build_sketch import *

with BuildSketch() as leaf:
    with BuildLine() as outline:
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
        MirrorToLine(*outline.edges(), axis=Axis.Y)
    BuildFace(*leaf.pending_edges)

with BuildSketch() as west_field:
    PushPointsToSketch((-1, 0))
    Rectangle(0.5, 1, centered=(False, False))

with BuildSketch() as east_field:
    MirrorToSketch(west_field.sketch, axis=Axis.Y)

with BuildSketch() as centre_field:
    Rectangle(1, 1, centered=(True, False))
    AddToSketch(leaf.sketch, mode=Mode.SUBTRACTION)

if "show_object" in locals():
    show_object(
        [west_field.sketch, east_field.sketch, leaf.sketch],
        name="flag_red_parts",
        options={"color": (255, 0, 0)},
    )
    show_object(
        centre_field.sketch,
        name="flag_white_part",
        options={"color": (255, 255, 255)},
    )
