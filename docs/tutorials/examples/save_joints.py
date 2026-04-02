from tcv_screenshots import save_model
from build123d import Color, Compound, Rot, Pos

from rigid_joints_pipe import pipe_builder, flange_inlet, flange_outlet
from slide_latch import latch, slide
from rod_end import rod_end, ball

pipe_builder.part.color = Color("goldenrod", .3)
flange_inlet.color = Color("goldenrod", .3)
flange_outlet.color = Color("goldenrod", .3)
joints = [joint.symbol for joint in [*pipe_builder.part.joints.values(), *flange_inlet.joints.values(), *flange_outlet.joints.values()]]
save_model([pipe_builder, flange_inlet, flange_outlet, *joints], "rigid_joints_pipe", {"render_joints": True})
latch = latch.part
latch.color = Color("goldenrod", .3)
latch_joints = [joint.symbol for joint in latch.joints.values()]
slide = slide.part
slide.color = Color("goldenrod", .3)
slide_joints = [joint.symbol for joint in slide.joints.values()]
save_model([latch, slide, *latch_joints, *slide_joints], "joint-latch-slide", {"render_joints": True})
save_model([latch, *latch_joints], "joint-latch", {"render_joints": True})
save_model([slide, *slide_joints], "joint-slide", {"render_joints": True})
save_model([rod_end.part, ball.part], "rod_end", {"render_joints": True})