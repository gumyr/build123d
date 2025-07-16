import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

with BuildPart() as part:
    with BuildSketch() as s:
        Rectangle(115, 50)
        with Locations((5 / 2, 0)):
            SlotOverall(90, 12, mode=Mode.SUBTRACT)
    extrude(amount=15)

    with BuildSketch(Plane.XZ.offset(50 / 2)) as s3:
        with Locations((-115 / 2 + 26, 15)):
            SlotOverall(42 + 2 * 26 + 12, 2 * 26, rotation=90)
    zz = extrude(amount=-12)
    split(bisect_by=Plane.XY)
    edgs = part.part.edges().filter_by(Axis.Y).group_by(Axis.X)[-2]
    fillet(edgs, 9)

    with Locations(zz.faces().sort_by(Axis.Y)[0]):
        with Locations((42 / 2 + 6, 0)):
            CounterBoreHole(24 / 2, 34 / 2, 4)
    mirror(about=Plane.XZ)

    with BuildSketch() as s4:
        RectangleRounded(115, 50, 6)
    extrude(amount=80, mode=Mode.INTERSECT)
    # fillet does not work right, mode intersect is safer

    with BuildSketch(Plane.YZ) as s4:
        with BuildLine() as bl:
            l1 = Line((0, 0), (18 / 2, 0))
            l2 = PolarLine(l1 @ 1, 8, 60, length_mode=LengthMode.VERTICAL)
            l3 = Line(l2 @ 1, (0, 8))
            mirror(about=Plane.YZ)
        make_face()
    extrude(amount=115 / 2, both=True, mode=Mode.SUBTRACT)

    faces = part.faces().filter_by(
        lambda f: all(e.geom_type == GeomType.CIRCLE for e in f.edges())
    )
    for i, f in enumerate(faces):
        RigidJoint(f"bearing_bore_{i}", joint_location=f.center_location)

show(part, [f.translate(f.normal_at() * 0.01) for f in faces], render_joints=True)
save_screenshot(os.path.join(filedir, "filter_all_edges_circle.png"))
