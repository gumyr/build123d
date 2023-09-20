import copy
from build123d import *
from bd_warehouse.flange import WeldNeckFlange
from bd_warehouse.pipe import PipeSection
from ocp_vscode import *

flange_inlet = WeldNeckFlange(nps="10", flange_class=300)
flange_outlet = copy.copy(flange_inlet)

with BuildPart() as pipe_builder:
    # Create the pipe
    with BuildLine():
        path = TangentArc((0, 0, 0), (2 * FT, 0, 1 * FT), tangent=(1, 0, 0))
    with BuildSketch(Plane(origin=path @ 0, z_dir=path % 0)):
        PipeSection("10", material="stainless", identifier="40S")
    sweep()

    # Add the joints
    RigidJoint(label="inlet", joint_location=-path.location_at(0))
    RigidJoint(label="outlet", joint_location=path.location_at(1))

# Place the flanges at the ends of the pipe
pipe_builder.part.joints["inlet"].connect_to(flange_inlet.joints["pipe"])
pipe_builder.part.joints["outlet"].connect_to(flange_outlet.joints["pipe"])

show(pipe_builder, flange_inlet, flange_outlet, render_joints=True)
