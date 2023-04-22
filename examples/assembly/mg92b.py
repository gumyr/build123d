import sys

sys.path.insert(0, "examples/assembly")

from build123d import *
from assembly import reference, Assembly
from ocp_vscode import show

body_height = 14
body_length = 22.8
body_width = 12.00

overall_length = 31.3
top_length = 15.6
hole_distance = 27.8
hole_diameter = 2

spline_radius1 = 2.1
spline_radius2 = 2.4
spline_height1 = 1.2
spline_height2 = 2.8

bottom_height = 2.8

top_cable_side_height = 1
top_height = 2.2
wing_height = 2.1
top_height_under_wing = 3.9

gap = 0.25

motor_height1 = 4.6
motor_height2 = 0.5
motor_diameter = 11.5
gear_diameter = 6

cable_diameter = 1
cable_depth = 2
f = 0.3


def create_bottom(label="bottom"):
    # create a box that is not centered in z direction
    b = Box(
        body_length,
        body_width,
        bottom_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    # before filleting, caclulate the location for the cable inset
    cable_loc = b.faces().sort_by(Axis.X).last.center_location
    cable_loc *= Pos(X=-(bottom_height - cable_diameter) / 2)

    b = fillet(b.edges().filter_by(Axis.Z), f)
    b = fillet(b.edges().sort_by().first, f)

    #  extrude the rectangle in minus direction and subtract it from the object
    r = cable_loc * Rectangle(cable_diameter, 5 * cable_diameter)
    b -= extrude(r, -cable_depth)

    b.label = label

    RigidJoint("j_top", b, b.faces().sort_by().last.center_location * Rot(0, 180, 0))
    RigidJoint(
        "j_cables", b, b.faces().filter_by(Axis.X).sort_by(Axis.X)[1].center_location
    )
    return b


def create_cable(label="cable"):
    # create one cable of length 5 there
    cable = extrude(Circle(0.5), 5)

    # cable = Pos(Y=-cable_diameter) * cable + cable + Pos(Y=cable_diameter) * cable
    cable.label = label

    RigidJoint(
        "j_cable",
        cable,
        cable.faces().sort_by(Axis.Z).last.center_location,
    )
    return cable


def create_body(label="body"):
    # create a box, not centered in z direction on this plane
    b = Box(
        body_length,
        body_width,
        body_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    body = fillet(b.edges().filter_by(Axis.Z), f)
    body.label = label

    RigidJoint("j_bottom", body, body.faces().sort_by().first.center_location)
    RigidJoint("j_top", body, body.faces().sort_by().last.center_location)

    return body


def create_top(label="top"):
    polygon = (
        (-body_length / 2, 0.0),
        (body_length / 2, 0.0),
        (body_length / 2, top_height_under_wing),
        (overall_length / 2, top_height_under_wing),
        (overall_length / 2, top_height_under_wing + wing_height),
        (body_length / 2, top_height_under_wing + wing_height),
        (body_length / 2, top_height_under_wing + wing_height + top_height),
        (
            body_length / 2 - top_length,
            top_height_under_wing + wing_height + top_height,
        ),
        (-body_length / 2, top_height_under_wing + wing_height + top_cable_side_height),
        (-body_length / 2, top_height_under_wing + wing_height),
        (-overall_length / 2, top_height_under_wing + wing_height),
        (-overall_length / 2, top_height_under_wing),
        (-body_length / 2, top_height_under_wing),
        (-body_length / 2, 0.0),
    )
    # create the polygon, extrude it and rotate it upwards to the XZ plane
    top = Plane.XZ * extrude(Polygon(*polygon), -body_width)

    # center top
    top.move(Pos(0, -body_width / 2))

    # create the holes in the wings.
    hole_locs = [
        Pos(-hole_distance / 2, 0),
        Pos(hole_distance / 2, 0),
    ]
    for loc in hole_locs:
        top -= loc * Hole(hole_diameter / 2, top_height)

    # Finally get the circles of all new edges and select the two lowest
    fix_holes = top.edges().filter_by(GeomType.CIRCLE).group_by()[0].sort_by(Axis.X)

    # and fillet the z-axis edges
    edges = top.edges().filter_by(Axis.Z).group_by(Axis.Y)
    top = fillet(edges[0] + edges[-1], f)

    # Get the height of the overall servo by now
    offset = top.faces().sort_by().last.center_location.position.Z
    # and set x to be the right center for the motor
    loc = Pos((body_length - body_width) / 2, 0, offset)

    # create the motor housing
    motor = loc * extrude(Circle(motor_diameter / 2), motor_height1)
    motor = fillet(motor.edges().sort_by().last, f)

    # get the max face of the motor in z direction
    plane = Plane(motor.faces().sort_by().last)
    # and add the second cylinder on top of the motor
    motor += plane * extrude(Circle(3.65), motor_height2)

    # add the motor to the top
    top += motor

    # shift the location in x for the center of the gear box
    loc.position -= Vector(motor_diameter / 2, 0, 0)

    # create the gear at this location
    gear = loc * extrude(Circle(gear_diameter / 2), motor_height1)
    gear = fillet(gear.edges().sort_by().last, f)

    # add the geat to the top
    top += gear
    top.label = label

    RigidJoint(
        "j_bottom", top, top.faces().sort_by().first.center_location * Rot(0, 180, 0)
    )
    RigidJoint("j_top", top, top.faces().sort_by().last.center_location)

    RigidJoint(
        "j_fix_hole",
        top,
        make_face(fix_holes[0]).faces()[0].center_location * Rot(0, 180, 0),
    )
    RigidJoint(
        "j_fix_hole_cable",
        top,
        make_face(fix_holes[1]).faces()[0].center_location * Rot(0, 180, 0),
    )

    return top


def create_spline(label="spline"):
    # get the top plane of the body
    # plane = Plane(self.top().faces().sort_by().last)

    # create the spline axis as cylinder on top of the result
    spline = extrude(Circle(spline_radius1), spline_height1)

    # create the spline gear as cylinder on top of the new result
    plane = Plane(spline.faces().sort_by().last)
    spline += plane * extrude(Circle(spline_radius2), spline_height2)

    # select the spline gear top face
    spline_hole = spline.edges().filter_by(GeomType.CIRCLE).sort_by().last

    # and drill a hole into it
    spline -= Plane(spline.faces().sort_by().last) * Hole(1, spline_height2)

    spline = chamfer(spline.edges().sort_by().last, 0.3)

    spline.label = label

    RigidJoint(
        "j_bottom",
        spline,
        spline.faces().sort_by().first.center_location * Rot(0, 180, 0),
    )
    RevoluteJoint("j_top", spline, spline.faces().sort_by().last.center_location.z_axis)

    return spline


bottom = create_bottom()
body = create_body()
top = create_top()
cable = create_cable()
spline = create_spline()

cables = Assembly(
    children=[
        reference(Pos(Y=cable_diameter) * cable, label="brown", color=(108, 86, 83)),
        reference(cable, label="red", color=(228, 57, 48)),
        reference(Pos(Y=-cable_diameter) * cable, label="amber", color=(237, 152, 93)),
    ],
    label="cables",
)
RigidJoint(
    "j_cables", cables, cable.faces().sort_by().last.center_location * Rot(0, 180, 0)
)

mg92b = Assembly(
    children=[
        reference(bottom, label="bottom", color="black"),
        reference(body, label="body", color=(48, 112, 216)),
        reference(top, label="top", color="black"),
        reference(spline, label="spline", color=(165, 156, 148)),
        cables,
    ],
    label="mg92b",
)
mg92b.assemble("/mg92b/body", "j_bottom", "/mg92b/bottom", "j_top")
mg92b.assemble("/mg92b/top", "j_bottom", "/mg92b/body", "j_top")
mg92b.assemble("/mg92b/spline", "j_bottom", "/mg92b/top", "j_top")
mg92b.assemble("/mg92b/cables", "j_cables", "/mg92b/bottom", "j_cables")

show(mg92b, render_joints=True)

# %%
