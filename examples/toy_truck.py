"""

name: toy_truck.py
by:   Gumyr
date: April 4th 2025

desc:

    This example demonstrates how to design a toy truck using BuildPart and
    BuildSketch in Builder mode. The model includes a detailed body, cab, grill,
    and bumper, showcasing techniques like sketch reuse, symmetry, tapered
    extrusions, selective filleting, and the use of joints for part assembly.
    Ideal for learning complex part construction and hierarchical modeling in
    build123d.

license:

    Copyright 2025 Gumyr

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

# [Code]
from build123d import *
from ocp_vscode import show

# Toy Truck Blue
truck_color = Color(0x4683CE)

# Create the main truck body — from bumper to bed, excluding the cab
with BuildPart() as body:
    # The body has two axes of symmetry, so we start with a centered sketch.
    # The default workplane is Plane.XY.
    with BuildSketch() as body_skt:
        Rectangle(20, 35)
        # Fillet all the corners of the sketch.
        # Alternatively, you could use RectangleRounded.
        fillet(body_skt.vertices(), 1)

    # Extrude the body shape upward
    extrude(amount=10, taper=4)
    # Reuse the sketch by accessing it explicitly
    extrude(body_skt.sketch, amount=8, taper=2)

    # Create symmetric fenders on Plane.YZ
    with BuildSketch(Plane.YZ) as fender:
        # The trapezoid has asymmetric angles (80°, 88°)
        Trapezoid(18, 6, 80, 88, align=Align.MIN)
        # Fillet top edge vertices (Y-direction highest group)
        fillet(fender.vertices().group_by(Axis.Y)[-1], 1.5)

    # Extrude the fender in both directions
    extrude(amount=10.5, both=True)

    # Create wheel wells with a shifted sketch on Plane.YZ
    with BuildSketch(Plane.YZ.shift_origin((0, 3.5, 0))) as wheel_well:
        Trapezoid(12, 4, 70, 85, align=Align.MIN)
        fillet(wheel_well.vertices().group_by(Axis.Y)[-1], 2)

    # Subtract the wheel well geometry
    extrude(amount=10.5, both=True, mode=Mode.SUBTRACT)

    # Fillet the top edges of the body
    fillet(body.edges().group_by(Axis.Z)[-1], 1)

    # Isolate a set of body edges and preview before filleting
    body_edges = body.edges().group_by(Axis.Z)[-6]
    fillet(body_edges, 0.1)

    # Combine edge groups from both sides of the fender and fillet them
    fender_edges = body.edges().group_by(Axis.X)[0] + body.edges().group_by(Axis.X)[-1]
    fender_edges = fender_edges.group_by(Axis.Z)[1:]
    fillet(fender_edges, 0.4)

    # Create a sketch on the front of the truck for the grill
    with BuildSketch(
        Plane.XZ.offset(-body.vertices().sort_by(Axis.Y)[-1].Y - 0.5)
    ) as grill:
        Rectangle(16, 8.5, align=(Align.CENTER, Align.MIN))
        fillet(grill.vertices().group_by(Axis.Y)[-1], 1)

        # Add headlights (subtractive circles)
        with Locations((0, 6.5)):
            with GridLocations(12, 0, 2, 1):
                Circle(1, mode=Mode.SUBTRACT)

        # Add air vents (subtractive slots)
        with Locations((0, 3)):
            with GridLocations(0, 0.8, 1, 4):
                SlotOverall(10, 0.5, mode=Mode.SUBTRACT)

    # Extrude the grill forward
    extrude(amount=2)

    # Fillet only the outer grill edges (exclude headlight/vent cuts)
    grill_perimeter = body.faces().sort_by(Axis.Y)[-1].outer_wire()
    fillet(grill_perimeter.edges(), 0.2)

    # Create the bumper as a separate part inside the body
    with BuildPart() as bumper:
        # Find the midpoint of a front edge and shift slightly to position the bumper
        front_cnt = body.edges().group_by(Axis.Z)[0].sort_by(Axis.Y)[-1] @ 0.5 - (0, 3)

        with BuildSketch() as bumper_plan:
            # Use BuildLine to draw an elliptical arc and offset
            with BuildLine():
                EllipticalCenterArc(front_cnt, 20, 4, start_angle=60, end_angle=120)
                offset(amount=1)
            make_face()

        # Extrude the bumper symmetrically
        extrude(amount=1, both=True)
        fillet(bumper.edges(), 0.25)

    # Define a joint on top of the body to connect the cab later
    RigidJoint("body_top", joint_location=Location((0, -7.5, 10)))
    body.part.color = truck_color

# Create the cab as an independent part to mount on the body
with BuildPart() as cab:
    with BuildSketch() as cab_plan:
        RectangleRounded(16, 16, 1)
        # Split the sketch to work on one symmetric half
        split(bisect_by=Plane.YZ)

    # Extrude the cab forward and upward at an angle
    extrude(amount=7, dir=(0, 0.15, 1))
    fillet(cab.edges().group_by(Axis.Z)[-1].group_by(Axis.X)[1:], 1)

    # Rear window
    with BuildSketch(Plane.XZ.shift_origin((0, 0, 3))) as rear_window:
        RectangleRounded(8, 4, 0.75)
    extrude(amount=10, mode=Mode.SUBTRACT)

    # Front window
    with BuildSketch(Plane.XZ) as front_window:
        RectangleRounded(15.2, 11, 0.75)
    extrude(amount=-10, mode=Mode.SUBTRACT)

    # Side windows
    with BuildSketch(Plane.YZ) as side_window:
        with Locations((3.5, 0)):
            with GridLocations(10, 0, 2, 1):
                Trapezoid(9, 5.5, 80, 100, align=(Align.CENTER, Align.MIN))
                fillet(side_window.vertices().group_by(Axis.Y)[-1], 0.5)
    extrude(amount=12, both=True, mode=Mode.SUBTRACT)

    # Mirror to complete the cab
    mirror(about=Plane.YZ)

    # Define joint on cab base
    RigidJoint("cab_base", joint_location=Location((0, 0, 0)))
    cab.part.color = truck_color

# Attach the cab to the truck body using joints
body.joints["body_top"].connect_to(cab.joints["cab_base"])

# Show the result
show(body.part, cab.part)
# [End]
