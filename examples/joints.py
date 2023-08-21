"""
Experimental Joint development file
"""
from build123d import *
from ocp_vscode import *


class JointBox(Solid):
    """A filleted box with joints

    A box of the given dimensions with all of the edges filleted.

    Args:
        length (float): box length
        width (float): box width
        height (float): box height
        radius (float): edge radius
        taper (float): vertical taper in degrees
    """

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        radius: float = 0.0,
        taper: float = 0.0,
    ):
        # Create the object
        with BuildPart() as obj:
            with BuildSketch():
                Rectangle(length, width)
            extrude(amount=height, taper=taper)
            if radius != 0.0:
                fillet(obj.part.edges(), radius=radius)
            Cylinder(width / 4, length, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
        # Initialize the Solid class with the new OCCT object
        super().__init__(obj.part.wrapped)


#
# Base Object
#
# base = JointBox(10, 10, 10)
# base = JointBox(10, 10, 10).locate(Location(Vector(1, 1, 1)))
# base = JointBox(10, 10, 10).locate(Location(Vector(1, 1, 1), (1, 0, 0), 5))
base: JointBox = JointBox(10, 10, 10, taper=3).locate(
    Location(Vector(1, 1, 1), (1, 1, 1), 30)
)
base_top_edges: ShapeList[Edge] = (
    base.edges().filter_by(Axis.X, tolerance=30).sort_by(Axis.Z)[-2:]
)
#
# Rigid Joint
#
fixed_arm = JointBox(1, 1, 5, 0.2)
j1 = RigidJoint("side", base, Plane(base.faces().sort_by(Axis.X)[-1]).location)
j2 = RigidJoint(
    "top", fixed_arm, (-Plane(fixed_arm.faces().sort_by(Axis.Z)[-1])).location
)
base.joints["side"].connect_to(fixed_arm.joints["top"])
# or
# j1.connect_to(j2)

#
# Hinge
#
hinge_arm = JointBox(2, 1, 10, taper=1)
swing_arm_hinge_edge: Edge = (
    hinge_arm.edges()
    .group_by(SortBy.LENGTH)[-1]
    .sort_by(Axis.X)[-2:]
    .sort_by(Axis.Y)[0]
)
swing_arm_hinge_axis = swing_arm_hinge_edge.to_axis()
base_corner_edge = base.edges().sort_by(Axis((0, 0, 0), (1, 1, 0)))[-1]
base_hinge_axis = base_corner_edge.to_axis()
j3 = RevoluteJoint("hinge", base, axis=base_hinge_axis, angular_range=(0, 180))
j4 = RigidJoint("corner", hinge_arm, swing_arm_hinge_axis.location)
base.joints["hinge"].connect_to(hinge_arm.joints["corner"], angle=90)

#
# Slider
#
slider_arm = JointBox(4, 1, 2, 0.2)
s1 = LinearJoint(
    "slide",
    base,
    axis=Edge.make_mid_way(*base_top_edges, 0.67).to_axis(),
    linear_range=(0, base_top_edges[0].length),
)
s2 = RigidJoint("slide", slider_arm, Location(Vector(0, 0, 0)))
base.joints["slide"].connect_to(slider_arm.joints["slide"], position=8)
# s1.connect_to(s2,8)

#
# Cylindrical
#
hole_axis = Axis(
    base.faces().sort_by(Axis.Y)[0].center(),
    -base.faces().sort_by(Axis.Y)[0].normal_at(),
)
screw_arm = JointBox(1, 1, 10, 0.49)
j5 = CylindricalJoint("hole", base, hole_axis, linear_range=(-10, 10))
j6 = RigidJoint("screw", screw_arm, screw_arm.faces().sort_by(Axis.Z)[-1].location)
j5.connect_to(j6, position=-1, angle=90)

#
# PinSlotJoint
#
j7 = LinearJoint(
    "slot",
    base,
    axis=Edge.make_mid_way(*base_top_edges, 0.33).to_axis(),
    linear_range=(0, base_top_edges[0].length),
)
pin_arm = JointBox(2, 1, 2)
j8 = RevoluteJoint("pin", pin_arm, axis=Axis.Z, angular_range=(0, 360))
j7.connect_to(j8, position=6, angle=60)

#
# BallJoint
#
j9 = BallJoint("socket", base, Plane(base.faces().sort_by(Axis.X)[0]).location)
ball = JointBox(2, 2, 2, 0.99)
j10 = RigidJoint("ball", ball, Location(Vector(0, 0, 1)))
j9.connect_to(j10, angles=(10, 20, 30))

show_all(render_joints=True, transparent=True)
