from build123d import *
from ocp_vscode import *

with BuildPart() as latch:
    # Basic box shape to start with filleted corners
    Box(70, 30, 14)
    end = latch.faces().sort_by(Axis.X)[-1]  # save the end with the hole
    fillet(latch.edges().filter_by(Axis.Z), 2)
    fillet(latch.edges().sort_by(Axis.Z)[-1], 1)
    # Make screw tabs
    with BuildSketch(latch.faces().sort_by(Axis.Z)[0]) as l4:
        with Locations((-30, 0), (30, 0)):
            SlotOverall(50, 10, rotation=90)
        Rectangle(50, 30)
        fillet(l4.vertices(Select.LAST), radius=2)
    extrude(amount=-2)
    with GridLocations(60, 40, 2, 2):
        Hole(2)
    # Create the hole from the end saved previously
    with BuildSketch(end) as slide_hole:
        add(end)
        offset(amount=-2)
        fillet(slide_hole.vertices(), 1)
    extrude(amount=-68, mode=Mode.SUBTRACT)
    # Slot for the handle to slide in
    with BuildSketch(latch.faces().sort_by(Axis.Z)[-1]):
        SlotOverall(32, 8)
    extrude(amount=-2, mode=Mode.SUBTRACT)
    # The slider will move align the x axis 12mm in each direction
    LinearJoint("latch", axis=Axis.X, linear_range=(-12, 12))

with BuildPart() as slide:
    # The slide will be a little smaller than the hole
    with BuildSketch() as s1:
        add(slide_hole.sketch)
        offset(amount=-0.25)
    # The extrusions aren't symmetric
    extrude(amount=46)
    extrude(slide.faces().sort_by(Axis.Z)[0], amount=20)
    # Round off the ends
    fillet(slide.edges().group_by(Axis.Z)[0], 1)
    fillet(slide.edges().group_by(Axis.Z)[-1], 1)
    # Create the knob
    with BuildSketch() as s2:
        with Locations((12, 0)):
            SlotOverall(15, 4, rotation=90)
        Rectangle(12, 7, align=(Align.MIN, Align.CENTER))
        fillet(s2.vertices(Select.LAST), 1)
        split(bisect_by=Plane.XZ)
    revolve(axis=Axis.X)
    # Align the joint to Plane.ZY flipped
    RigidJoint("slide", joint_location=Location(-Plane.ZY))

# Position the slide in the latch: -12 >= position <= 12
latch.part.joints["latch"].connect_to(slide.part.joints["slide"], position=12)

# show(latch.part, render_joints=True)
# show(slide.part, render_joints=True)
show(latch.part, slide.part, render_joints=True)
