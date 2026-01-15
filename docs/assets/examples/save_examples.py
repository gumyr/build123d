from tcv_screenshots import save_model
from build123d import Color, Compound, Rot, Pos

import benchy
import bicycle_tire
import bracelet
import build123d_logo
import canadian_flag
import cast_bearing_unit
import circuit_board
import clock
import fast_grid_holes
import handle
import heat_exchanger
import key_cap
import loft
import maker_coin
import pegboard_j_hook
import platonic_solids
import playing_cards
import stud_wall
import tea_cup
import toy_truck
import vase

save_model([benchy.benchy], "benchy")
save_model([benchy.benchy], "benchy_front", {"reset_camera": "front"})
save_model([benchy.benchy], "benchy_right", {"reset_camera": "right"})
save_model([bicycle_tire.tire, bicycle_tire.tread], "bicycle_tire", {"cadWidth": 2000, "height": 2000})
size = bicycle_tire.tire.bounding_box().size.Y
tire_config = {"zoom": 4, "position": (size / 2, -size, size), "target": (0, -size / 2, size / 2),}
save_model([bicycle_tire.tire, bicycle_tire.tread], "bicycle_tire_detail", tire_config)
save_model([Rot(Z=-90) * bracelet.bracelet], "bracelet")
save_model([build123d_logo.one, build123d_logo.two, build123d_logo.three_d, build123d_logo.extension_lines, build123d_logo.build], "build123d_logo")
save_model([Rot(Z=-45) * Rot(90) * canadian_flag.canadian_flag], "canadian_flag", {"reset_camera": "front", "ortho": False})
save_model([canadian_flag.canadian_flag], "canadian_flag_iso", {"ortho": False})
save_model([Rot(30, 0, 30) * canadian_flag.canadian_flag], "canadian_flag_detail", {"reset_camera": "front", "ortho": False})
save_model([cast_bearing_unit.oval_flanged_bearing_unit], "cast_bearing_unit", {"render_edges": False})
save_model([circuit_board.pcb], "circuit_board")
save_model([circuit_board.pcb], "circuit_board_top", {"reset_camera": "top"})
save_model([clock.clock_face], "clock_face", {"reset_camera": "top"})
save_model([fast_grid_holes.grid], "fast_grid_holes")
handle.handle.color = Color("goldenrod", .6)
save_model([handle.handle, handle.handle_center_line, handle.sections], "handle")
save_model([heat_exchanger.heat_exchanger], "heat_exchanger" , {"cadWidth": 2000, "height": 2000})
size = heat_exchanger.heat_exchanger.part.bounding_box().size.Z
exchanger_config = {"zoom": 2, "position": (size / 2, -size, size), "target": (0, 0, size / 2)}
save_model([heat_exchanger.heat_exchanger], "heat_exchanger_detail", exchanger_config)
key_cap.key_cap.color = Color("goldenrod", .3)
save_model([key_cap.key_cap], "key_cap")
save_model([loft.art], "loft")
save_model([maker_coin.maker_coin], "maker_coin")
save_model([Rot(Y=-90) * pegboard_j_hook.mainp.part], "peg_board_hook")
save_model([Rot(Z=90) * Compound(platonic_solids.solids)], "platonic_solids")
playing_cards.lid_builder.part.color = Color("goldenrod", .7)
save_model([Pos(-20, 40) * playing_cards.hand, playing_cards.box_builder, Pos(0, 0, (playing_cards.wall + playing_cards.deck) / 2) * playing_cards.lid_builder.part], "playing_cards")
save_model([Rot(15, 0, -30) * Compound([stud_wall.x_wall, stud_wall.y_wall])], "stud_wall", {"reset_camera": "front"})
tea_cup.tea_cup.color = "goldenrod"
save_model([tea_cup.tea_cup], "tea_cup")
save_model([Rot(15, 0, -120) * Compound([toy_truck.body.part, toy_truck.cab.part], color=toy_truck.truck_color)], "toy_truck", {"reset_camera": "front", "render_edges": False})
save_model([Rot(90, 0, 0) * vase.vase.part], "vase")
