from build123d import *
from tcv_screenshots import save_model

# setup-algebra
bracket = import_step("nema-17-bracket.step")
faces = bracket.faces()

motor_mounts = faces.filter_by(GeomType.CYLINDER).filter_by(lambda f: f.radius == 3.3/2)
for i, f in enumerate(motor_mounts):
    location = f.axis_of_rotation.location
    RigidJoint(f"motor_m3_{i}", bracket, joint_location=location)
# setup-algebra-end

# inner-wire-algebra
motor_face = faces.filter_by(lambda f: len(f.inner_wires()) == 5).sort_by(Axis.X)[-1]
motor_bore = motor_face.inner_wires().edges().filter_by(lambda e: e.radius == 16).edge()
location = Location(motor_bore.arc_center, motor_bore.normal() * 90, Intrinsic.YXZ)
RigidJoint(f"motor", bracket, joint_location=location)
# inner-wire-algebra-end

save_model([bracket, *[joint.symbol for joint in bracket.joints.values()]], "filter_inner_wire_count", {"render_joints": True})

# linear-algebra
mount_face = faces.filter_by(lambda f: len(f.inner_wires()) == 6).sort_by(Axis.Z)[-1]
mount_slots = mount_face.inner_wires().edges().filter_by(GeomType.CIRCLE)
joint_edges = [
    Line(mount_slots[i].arc_center, mount_slots[i + 1].arc_center)
    for i in range(0, len(mount_slots), 2)
]
for i, e in enumerate(joint_edges):
    LinearJoint(f"mount_m4_{i}", bracket, axis=Axis(e), linear_range=(0, e.length / 2))
# linear-algebra-end

save_model([bracket, *[joint.symbol for joint in bracket.joints.values()]], "filter_inner_wire_count_linear", {"render_joints": True})