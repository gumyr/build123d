from tcv_screenshots import save_model
from build123d import Color, Compound, Rot, Pos

from rigid_joints_pipe import pipe_builder, flange_inlet, flange_outlet
from slide_latch import latch, slide
from rod_end import rod_end, ball, s2

pipe_builder.part.color = Color("goldenrod", .5)
flange_inlet.color = Color("goldenrod", .5)
flange_outlet.color = Color("goldenrod", .5)
save_model([pipe_builder, flange_inlet, flange_outlet, *[joint.symbol for joint in pipe_builder.part.joints.values()]], "rigid_joints_pipe", {"render_joints": True})
latch = latch.part
latch.color = Color("goldenrod", .5)
slide = slide.part
slide.color = Color("goldenrod", .5)
save_model([latch, slide, *[joint.symbol for joint in [*latch.joints.values(), *slide.joints.values()]]], "joint-latch-slide", {"render_joints": True})
save_model([latch, *[joint.symbol for joint in latch.joints.values()]], "joint-latch", {"render_joints": True})
save_model([slide, *[joint.symbol for joint in slide.joints.values()]], "joint-slide", {"render_joints": True})
save_model([rod_end.part, ball.part], "rod_end", {"render_joints": True})