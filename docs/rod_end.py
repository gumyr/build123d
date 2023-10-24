from build123d import *
from bd_warehouse.thread import IsoThread
from ocp_vscode import *

# Create the thread so the min radius is available below
thread = IsoThread(
    major_diameter=8, pitch=1.25, length=20, end_finishes=("fade", "raw")
)
inner_radius = 15.89 / 2
inner_gap = 0.2

with BuildPart() as rod_end:
    # Create the outer shape
    with BuildSketch():
        Circle(22.25 / 2)
        with Locations((0, -12)):
            Rectangle(8, 1)
        make_hull()
        split(bisect_by=Plane.YZ)
    revolve(axis=Axis.Y)
    # Refine the shape
    with BuildSketch(Plane.YZ) as s2:
        Rectangle(25, 8, align=(Align.MIN, Align.CENTER))
        Rectangle(9, 10, align=(Align.MIN, Align.CENTER))
        chamfer(s2.vertices(), 0.5)
    revolve(axis=Axis.Z, mode=Mode.INTERSECT)
    # Add the screw shaft
    Cylinder(
        thread.min_radius,
        30,
        rotation=(90, 0, 0),
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    # Cutout the ball socket
    Sphere(inner_radius, mode=Mode.SUBTRACT)
    # Add thread
    with Locations((0, -30, 0)):
        add(thread, rotation=(-90, 0, 0))
    # Create the ball joint
    BallJoint(
        "socket",
        joint_location=Location(),
        angular_range=((-14, 14), (-14, 14), (0, 360)),
    )

with BuildPart() as ball:
    Sphere(inner_radius - inner_gap)
    Box(50, 50, 13, mode=Mode.INTERSECT)
    Hole(4)
    ball.part.color = Color("aliceblue")
    RigidJoint("ball", joint_location=Location())

rod_end.part.joints["socket"].connect_to(ball.part.joints["ball"], angles=(5, 10, 0))

show(rod_end.part, ball.part)
