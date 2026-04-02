from build123d import Curve, Vertex
from tcv_screenshots import save_model

from tools.svg import write_svg, project_shapes

import spitfire_wing_gordon as wing
import heart_token as heart

save_model(wing.wing, "spitfire_wing")
wing_control_edges = Curve(
    [wing.airfoil_root, wing.airfoil_tip, Vertex(wing.leading_edge @ 1), wing.leading_edge, wing.trailing_edge]
)
write_svg("spitfire_wing_profiles_guides", project_shapes(wing_control_edges, show_hidden=False))

save_model(heart.heart_token, "heart_token", {})
save_model(heart.heart, "token_heart_solid", {"axes": True, "axes0": True, "reset_camera": (45, -30)})
save_model(heart.heart_half, "token_heart_perimeter", {"axes": True, "axes0": True, "reset_camera": (45, -30)})
save_model(heart.top_right_surface, "token_half_surface", {"axes": True, "axes0": True, "reset_camera": (45, -30)})
save_model([heart.left_wire, heart.left_side, heart.right_side], "token_sides", {"axes": True, "axes0": True, "reset_camera": (45, -30)})