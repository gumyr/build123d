from tcv_screenshots import save_model
from build123d import Color, Compound, Rot, Pos
from docs.tools.svg import write_svg, project_shapes

import benchy
import bicycle_tire
import boxes_on_faces
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
import lego
import loft
import maker_coin
import packed_boxes
import pegboard_j_hook
import platonic_solids
import playing_cards
import stud_wall
import tea_cup
import toy_truck
import vase

save_model([benchy.benchy.part], "benchy")
save_model([benchy.benchy.part], "benchy_front", {"reset_camera": "front"})
save_model([benchy.benchy.part], "benchy_right", {"reset_camera": "right"})
# save_model([bicycle_tire.tire, bicycle_tire.tread], "bicycle_tire", {"cadWidth": 2000, "height": 2000})
size = bicycle_tire.tire.bounding_box().size.Y
tire_config = {"zoom": 4, "position": (size / 2, -size, size), "target": (0, -size / 2, size / 2),}
# save_model([bicycle_tire.tire, bicycle_tire.tread], "bicycle_tire_detail", tire_config)
save_model([Rot(Z=-90) * bracelet.bracelet], "bracelet")
save_model([build123d_logo.one.line, build123d_logo.two.sketch, build123d_logo.three_d.part, build123d_logo.extension_lines.line, build123d_logo.build.sketch], "build123d_logo")
save_model([Rot(Z=-45) * Rot(90) * canadian_flag.canadian_flag], "canadian_flag", {"reset_camera": "front", "ortho": False})
save_model([canadian_flag.canadian_flag], "canadian_flag_iso", {"ortho": False})
save_model([Rot(30, 0, 30) * canadian_flag.canadian_flag], "canadian_flag_detail", {"reset_camera": "front", "ortho": False})
save_model([cast_bearing_unit.oval_flanged_bearing_unit.part], "cast_bearing_unit", {"render_edges": False})
save_model([circuit_board.pcb.part], "circuit_board")
save_model([circuit_board.pcb.part], "circuit_board_top", {"reset_camera": "top"})
save_model([clock.clock_face.sketch], "clock_face", {"reset_camera": "top"})
save_model([fast_grid_holes.grid], "fast_grid_holes")
handle.handle.part.color = Color("goldenrod", .6)
save_model([handle.handle.part, handle.handle_center_line, handle.sections], "handle")
# save_model([heat_exchanger.heat_exchanger.part], "heat_exchanger" , {"cadWidth": 2000, "height": 2000})
size = heat_exchanger.heat_exchanger.part.bounding_box().size.Z
exchanger_config = {"zoom": 2, "position": (size / 2, -size, size), "target": (0, 0, size / 2)}
# save_model([heat_exchanger.heat_exchanger.part], "heat_exchanger_detail", exchanger_config)
key_cap.key_cap.part.color = Color("goldenrod", .3)
save_model([key_cap.key_cap.part], "key_cap")
save_model([loft.art.part], "loft")
save_model([maker_coin.maker_coin], "maker_coin")
save_model([Rot(Y=-90) * pegboard_j_hook.mainp.part], "peg_board_hook")
save_model([Rot(Z=90) * Compound(platonic_solids.solids)], "platonic_solids")
playing_cards.lid_builder.part.color = Color("goldenrod", .7)
save_model([Pos(-20, 40) * playing_cards.hand, playing_cards.box_builder, Pos(0, 0, (playing_cards.wall + playing_cards.deck) / 2) * playing_cards.lid_builder.part], "playing_cards")
save_model([Rot(15, 0, -30) * Compound([stud_wall.x_wall, stud_wall.y_wall])], "stud_wall", {"reset_camera": "front"})
tea_cup.tea_cup.part.color = "goldenrod"
save_model([tea_cup.tea_cup.part], "tea_cup")
save_model([Rot(15, 0, -120) * Compound([toy_truck.body.part, toy_truck.cab.part], color=toy_truck.truck_color)], "toy_truck", {"reset_camera": "front", "render_edges": False})
save_model([Rot(90, 0, 0) * vase.vase.part], "vase")

write_svg("boxes_on_faces", project_shapes(boxes_on_faces.bp.part, show_hidden=False))
write_svg("card_box", project_shapes(playing_cards.box))
write_svg("lego_step4", project_shapes(lego.step4, "top"))
write_svg("lego_step5", project_shapes(lego.step5, "top"))
write_svg("lego_step6", project_shapes(lego.step6, "top"))
write_svg("lego_step7", project_shapes(lego.step7, "top"))
write_svg("lego_step8", project_shapes(lego.step8, "top"))
write_svg("lego_step9", project_shapes(lego.step9, "dimetric"))
write_svg("lego_step10", project_shapes(lego.step10, "dimetric"))
write_svg("lego", project_shapes(lego.lego.part, "dimetric"))
write_svg("packed_boxes_input", project_shapes(packed_boxes.test_boxes, "top"))
write_svg("packed_boxes_output", project_shapes(packed_boxes.packed, "top"))
