# [Code]
from build123d import *
from ocp_viewer import show

# Toy Truck Blue
truck_color = Color(0x4683CE)

# Create the main truck body — from bumper to bed, excluding the cab

# The body has two axes of symmetry, so we start with a centered sketch
# and fillet all its corners. Alternatively, you could use RectangleRounded.
body_skt = Rectangle(20, 35)
body_skt = fillet(body_skt.vertices(), 1)

# Extrude the body shape upward, then reuse the sketch for the upper part
body = extrude(body_skt, amount=10, taper=4)
body += extrude(body_skt, amount=8, taper=2)

# Create symmetric fenders on Plane.YZ
# The trapezoid has asymmetric angles (80°, 88°)
fender = Trapezoid(18, 6, 80, 88, align=Align.MIN)
# Fillet top edge vertices (Y-direction highest group)
fender = fillet(fender.vertices().group_by(Axis.Y)[-1], 1.5)
# Extrude the fender in both directions
body += extrude(Plane.YZ * fender, amount=10.5, both=True)

# Create wheel wells with a shifted sketch on Plane.YZ
wheel_well = Trapezoid(12, 4, 70, 85, align=Align.MIN)
wheel_well = fillet(wheel_well.vertices().group_by(Axis.Y)[-1], 2)
# Subtract the wheel well geometry
body -= extrude(Plane.YZ.shift_origin((0, 3.5, 0)) * wheel_well, amount=10.5, both=True)

# Fillet the top edges of the body
body = fillet(body.edges().group_by(Axis.Z)[-1], 1)

# Isolate a set of body edges and fillet them
body_edges = body.edges().group_by(Axis.Z)[-6]
body = fillet(body_edges, 0.1)

# Combine edge groups from both sides of the fender and fillet them
fender_edges = body.edges().group_by(Axis.X)[0] + body.edges().group_by(Axis.X)[-1]
fender_edges = fender_edges.group_by(Axis.Z)[1:]
body = fillet(fender_edges, 0.4)

# Create a sketch for the grill
grill = Rectangle(16, 8.5, align=(Align.CENTER, Align.MIN))
grill = fillet(grill.vertices().group_by(Axis.Y)[-1], 1)
# Add headlights (subtractive circles)
grill -= [Pos(x, 6.5) * Circle(1) for x in (-6, 6)]
# Add air vents (subtractive slots)
grill -= [Pos(0, 3) * loc * SlotOverall(10, 0.5) for loc in GridLocations(0, 0.8, 1, 4)]

# Place the grill on the front of the truck and extrude it forward
grill_plane = Plane.XZ.offset(-body.vertices().sort_by(Axis.Y)[-1].Y - 0.5)
body += extrude(grill_plane * grill, amount=2)

# Fillet only the outer grill edges (exclude headlight/vent cuts)
grill_perimeter = body.faces().sort_by(Axis.Y)[-1].outer_wire()
body = fillet(grill_perimeter.edges(), 0.2)

# Create the bumper as a separate part and add it to the body
# Find the midpoint of a front edge and shift slightly to position the bumper
front_cnt = body.edges().group_by(Axis.Z)[0].sort_by(Axis.Y)[-1] @ 0.5 - (0, 3)
# Draw an elliptical arc and offset it to make the outline
bumper_arc = EllipticalCenterArc(front_cnt, 20, 4, start_angle=60, arc_size=60)
bumper_plan = make_face(offset(bumper_arc, amount=1))
# Extrude the bumper symmetrically
bumper = extrude(bumper_plan, amount=1, both=True)
bumper = fillet(bumper.edges(), 0.25)
body += bumper

# Define a joint on top of the body to connect the cab later
RigidJoint("body_top", body, joint_location=Location((0, -7.5, 10)))
body.color = truck_color

# Create the cab as an independent part to mount on the body

# Split the sketch to work on one symmetric half
cab_plan = split(RectangleRounded(16, 16, 1), bisect_by=Plane.YZ)
# Extrude the cab forward and upward at an angle
cab = extrude(cab_plan, amount=7, dir=(0, 0.15, 1))
cab = fillet(cab.edges().group_by(Axis.Z)[-1].group_by(Axis.X)[1:], 1)

# Rear window
rear_window = Plane.XZ.shift_origin((0, 0, 3)) * RectangleRounded(8, 4, 0.75)
cab -= extrude(rear_window, amount=10)

# Front window
front_window = Plane.XZ * RectangleRounded(15.2, 11, 0.75)
cab -= extrude(front_window, amount=-10)

# Side windows
side_window = Trapezoid(9, 5.5, 80, 100, align=(Align.CENTER, Align.MIN))
side_window = fillet(side_window.vertices().group_by(Axis.Y)[-1], 0.5)
side_windows = Sketch() + [Pos(y, 0) * side_window for y in (-1.5, 8.5)]
cab -= extrude(Plane.YZ * side_windows, amount=12, both=True)

# Mirror to complete the cab
cab += mirror(cab, about=Plane.YZ)

# Define joint on cab base
RigidJoint("cab_base", cab, joint_location=Location((0, 0, 0)))
cab.color = truck_color

# Attach the cab to the truck body using joints
body.joints["body_top"].attach(cab.joints["cab_base"])

# Show the result
show(body, cab)
# [End]
