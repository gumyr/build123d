from cadquery import Vector
from build123d_common import *
import build1d as b


with b.Build1D() as ml:
    l1 = b.Polyline(ml, (0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569)).object
    l2 = b.Polyline(ml, (0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125)).object
    b.RadiusArc(ml, l1 @ 1, l2 @ 0, 0.0271)
    l3 = b.Polyline(ml, (0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071)).object
    b.TangentArc(ml, l2 @ 1, l3 @ 0, tangent=l2 % 1)
    l4 = b.Polyline(ml, (0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188)).object
    b.SagittaArc(ml, l3 @ 1, l4 @ 0, 0.003)
    l5 = b.Polyline(ml, (0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835)).object
    b.ThreePointArc(
        ml, l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0
    )
    l6 = b.Polyline(ml, (0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752)).object
    b.Spline(ml, l5 @ 1, l6 @ 0, tangents=(l5 % 1, l6 % 0), tangent_scalars=(2, 2))
    l7 = b.Polyline(ml, (0.0692, 0.7808), (0.0000, 0.9167)).object
    b.TangentArc(ml, l6 @ 1, l7 @ 0, tangent=l6 % 1)
    b.MirrorY(ml, *ml.edges())

if "show_object" in locals():
    show_object(ml.edge_list, "maple leaf")
