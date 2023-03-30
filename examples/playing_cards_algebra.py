from typing import Tuple, Union, Literal
from build123d import *


class Club(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, Tuple[Align, Align]] = None,
    ):
        l0 = Line((0, -188), (76, -188))
        b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
        b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
        b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
        b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
        club = l0 + b0 + b1 + b2 + b3
        club += mirror(objects=club, about=Plane.YZ)
        club = make_face(club)
        club = scale(objects=club, by=height / club.bounding_box().size.Y)

        super().__init__(club.wrapped)
        # self._align(align)


class Spade(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, Tuple[Align, Align]] = None,
    ):
        b0 = Bezier((0, 198), (6, 190), (41, 127), (112, 61))
        b1 = Bezier(b0 @ 1, (242, -72), (114, -168), (11, -105))
        b2 = Bezier(b1 @ 1, (31, -174), (42, -179), (53, -198))
        l0 = Line(b2 @ 1, (0, -198))
        spade = l0 + b0 + b1 + b2
        spade += mirror(objects=spade, about=Plane.YZ)
        spade = make_face(spade)
        spade = scale(objects=spade, by=height / spade.bounding_box().size.Y)

        super().__init__(spade.wrapped)
        # self._align(align)


class Heart(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, Tuple[Align, Align]] = None,
    ):
        b1 = Bezier((0, 146), (20, 169), (67, 198), (97, 198))
        b2 = Bezier(b1 @ 1, (125, 198), (151, 186), (168, 167))
        b3 = Bezier(b2 @ 1, (197, 133), (194, 88), (158, 31))
        b4 = Bezier(b3 @ 1, (126, -13), (94, -48), (62, -95))
        b5 = Bezier(b4 @ 1, (40, -128), (0, -198))
        heart = b1 + b2 + b3 + b4 + b5
        heart += mirror(objects=heart, about=Plane.YZ)
        heart = make_face(heart)
        heart = scale(objects=heart, by=height / heart.bounding_box().size.Y)

        super().__init__(heart.wrapped)
        # self._align(align)


class Diamond(Sketch):
    def __init__(
        self,
        height: float,
        align: Union[Align, Tuple[Align, Align]] = None,
    ):
        diamond = Bezier((135, 0), (94, 69), (47, 134), (0, 198))
        diamond += mirror(objects=diamond, about=Plane.XZ)
        diamond += mirror(objects=diamond, about=Plane.YZ)
        diamond = make_face(diamond)
        diamond = scale(objects=diamond, by=height / diamond.bounding_box().size.Y)

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
walls = Plane(base_top) * offset(objects=box_plan, amount=-lip_t)
box += extrude(walls, amount=pocket_t / 2)
top = Plane.XY.offset(wall_t / 2) * offset(objects=box_plan, amount=-wall_t)
box -= extrude(top, amount=pocket_t)


pocket = extrude(box_plan, amount=pocket_t / 2 + bottom_t)
lid_bottom = offset(objects=box_plan, amount=-(wall_t - lip_t))
pocket -= extrude(lid_bottom, amount=pocket_t / 2)
pocket = Pos(0, 0, (wall_t + pocket_t) / 2) * pocket

plane = Plane(pocket.faces().sort_by().last)
suites = Pos(-0.3 * pocket_w, 0.3 * pocket_l) * Heart(pocket_l / 5)
suites += Pos(-0.3 * pocket_w, -0.3 * pocket_l) * Diamond(pocket_l / 5)
suites += Pos(0.3 * pocket_w, 0.3 * pocket_l) * Spade(pocket_l / 5)
suites += Pos(0.3 * pocket_w, -0.3 * pocket_l) * Club(pocket_l / 5)
suites = plane * suites

lid = pocket - extrude(suites, dir=(0, 0, 1), amount=-wall_t)


class PlayingCard(Compound):
    """PlayingCard

    A standard playing card modelled as a Face.

    Args:
        rank (Literal['A', '2' .. '9', 'J', 'Q', 'K']): card rank
        suit (Literal['Clubs', 'Spades', 'Hearts', 'Diamonds']): card suit
    """

    width = 2.5 * IN
    height = 3.5 * IN
    suits = {"Clubs": Club, "Spades": Spade, "Hearts": Heart, "Diamonds": Diamond}
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "J", "Q", "K"]

    def __init__(
        self,
        rank: Literal["A", "2", "3", "4", "5", "6", "7", "8", "9", "J", "Q", "K"],
        suit: Literal["Clubs", "Spades", "Hearts", "Diamonds"],
    ):
        w = PlayingCard.width
        h = PlayingCard.height
        playing_card = Rectangle(w, h, align=Align.MIN)
        if "show" in locals():
            show(playing_card)
        playing_card = fillet(playing_card.vertices(), radius=w / 15)
        if "show" in locals():
            show(playing_card)
        playing_card -= Pos(w / 7, 8 * h / 9) * Text(
            txt=rank,
            font_size=w / 7,
        )
        if "show" in locals():
            show(playing_card)
        playing_card -= Pos(w / 7, 7 * h / 9,) * PlayingCard.suits[
            suit
        ](height=w / 12)
        if "show" in locals():
            show(playing_card)

        playing_card -= (
            Pos((6 * w / 7, 1 * h / 9))
            * Rot(0, 0, 180)
            * Text(txt=rank, font_size=w / 7)
        )
        if "show" in locals():
            show(playing_card)

        playing_card -= (
            Pos((6 * w / 7, 2 * h / 9))
            * Rot(0, 0, 180)
            * PlayingCard.suits[suit](height=w / 12)
        )
        if "show" in locals():
            show(playing_card)
        rank_int = PlayingCard.ranks.index(rank) + 1
        rank_int = rank_int if rank_int < 10 else 1

        center_radius = 0 if rank_int == 1 else w / 3.5
        suit_rotation = 0 if rank_int == 1 else -90
        suit_height = (0.00159 * rank_int**2 - 0.0380 * rank_int + 0.37) * w

        playing_card -= (
            Pos(w / 2, h / 2)
            * Pos(
                radius=center_radius,
                count=rank_int,
                start_angle=90 if rank_int > 1 else 0,
            )
            * Rot(0, 0, suit_rotation)
            * PlayingCard.suits[suit](
                height=suit_height,
            )
        )
        super().__init__(playing_card.wrapped)


playing_card = PlayingCard(rank="A", suit="Spades")

if "show_object" in locals():
    show_object(playing_card)
    # show_object(outer_box_builder.part, "outer")
    # show_object(b, name="b", options={"alpha": 0.8})
    show_object(box, "box")
    show_object(lid, "lid", options={"alpha": 0.7})
    # show_object(walls.sketch, "walls")
    # show_object(o, "o")
    # show_object(half_club.line)
    # show_object(spade_outline.line)
    # show_object(b0, "b0")
    # show_object(b1, "b1")
    # show_object(b2, "b2")
    # show_object(b3, "b3")
    # show_object(b4, "b4")
    # show_object(b5, "b5")
    # show_object(l0, "l0")
    # show_object(l0, "l0")
