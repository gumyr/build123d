from typing import Union
from build123d import *
from ocp_vscode import show


class Club(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, tuple[Align, Align]] = None,
    ):
        l0 = Line((0, -188), (76, -188))
        b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
        b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
        b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
        b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
        club = l0 + b0 + b1 + b2 + b3
        club += mirror(club, Plane.YZ)
        club = make_face(club)
        club = scale(club, height / club.bounding_box().size.Y)

        super().__init__(club.wrapped)
        # self._align(align)


class Spade(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, tuple[Align, Align]] = None,
    ):
        b0 = Bezier((0, 198), (6, 190), (41, 127), (112, 61))
        b1 = Bezier(b0 @ 1, (242, -72), (114, -168), (11, -105))
        b2 = Bezier(b1 @ 1, (31, -174), (42, -179), (53, -198))
        l0 = Line(b2 @ 1, (0, -198))
        spade = l0 + b0 + b1 + b2
        spade += mirror(spade, Plane.YZ)
        spade = make_face(spade)
        spade = scale(spade, height / spade.bounding_box().size.Y)

        super().__init__(spade.wrapped)
        # self._align(align)


class Heart(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, tuple[Align, Align]] = None,
    ):
        b1 = Bezier((0, 146), (20, 169), (67, 198), (97, 198))
        b2 = Bezier(b1 @ 1, (125, 198), (151, 186), (168, 167))
        b3 = Bezier(b2 @ 1, (197, 133), (194, 88), (158, 31))
        b4 = Bezier(b3 @ 1, (126, -13), (94, -48), (62, -95))
        b5 = Bezier(b4 @ 1, (40, -128), (0, -198))
        heart = b1 + b2 + b3 + b4 + b5
        heart += mirror(heart, Plane.YZ)
        heart = make_face(heart)
        heart = scale(heart, height / heart.bounding_box().size.Y)

        super().__init__(heart.wrapped)
        # self._align(align)


class Diamond(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, tuple[Align, Align]] = None,
    ):
        diamond = Bezier((135, 0), (94, 69), (47, 134), (0, 198))
        diamond += mirror(diamond, Plane.XZ)
        diamond += mirror(diamond, Plane.YZ)
        diamond = make_face(diamond)
        diamond = scale(diamond, height / diamond.bounding_box().size.Y)

        super().__init__(diamond.wrapped)
        # self._align(align)


# The inside of the box fits 2.5x3.5" playing card deck with a small gap
pocket_w = 2.5 * IN + 2 * MM
pocket_l = 3.5 * IN + 2 * MM
pocket_t = 0.5 * IN + 2 * MM
wall_t = 3 * MM  # Wall thickness
bottom_t = wall_t / 2  # Top and bottom thickness
lid_gap = 0.5 * MM  # Spacing between base and lid
lip_t = wall_t / 2 - lid_gap / 2  # Lip thickness


box_plan = RectangleRounded(pocket_w + 2 * wall_t, pocket_l + 2 * wall_t, pocket_w / 15)
box = extrude(box_plan, amount=bottom_t + pocket_t / 2)
base_top = box.faces().sort_by(Axis.Z).last
walls = Plane(base_top) * offset(box_plan, -lip_t)
box += extrude(walls, amount=pocket_t / 2)
top = Plane.XY.offset(wall_t / 2) * offset(box_plan, -wall_t)
box -= extrude(top, amount=pocket_t)


pocket = extrude(box_plan, amount=pocket_t / 2 + bottom_t)
lid_bottom = offset(box_plan, -(wall_t - lip_t))
pocket -= extrude(lid_bottom, amount=pocket_t / 2)
pocket = Pos(0, 0, (wall_t + pocket_t) / 2) * pocket

plane = Plane(pocket.faces().sort_by().last)
suites = Pos(-0.3 * pocket_w, 0.3 * pocket_l) * Heart(pocket_l / 5)
suites += Pos(-0.3 * pocket_w, -0.3 * pocket_l) * Diamond(pocket_l / 5)
suites += Pos(0.3 * pocket_w, 0.3 * pocket_l) * Spade(pocket_l / 5)
suites += Pos(0.3 * pocket_w, -0.3 * pocket_l) * Club(pocket_l / 5)
suites = plane * suites

lid = pocket - extrude(suites, dir=(0, 0, 1), amount=-wall_t)

show(box, lid, names=["box", "lid"], alphas=[1.0, 0.6])
