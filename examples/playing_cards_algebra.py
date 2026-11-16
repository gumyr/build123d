# [Code]

from typing import Literal
from build123d import *
from ocp_vscode import show_object


# [Club]
class Club(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        l0 = Line((0, -188), (76, -188))
        b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
        b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
        b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
        b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
        half = [l0, b0, b1, b2, b3]
        club = make_face(half + [mirror(edge, Plane.YZ) for edge in half])
        club = scale(club, by=height / club.bounding_box().size.Y)
        super().__init__(obj=club, rotation=rotation, align=align, mode=mode)


# [Club]


class Spade(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        b0 = Bezier((0, 198), (6, 190), (41, 127), (112, 61))
        b1 = Bezier(b0 @ 1, (242, -72), (114, -168), (11, -105))
        b2 = Bezier(b1 @ 1, (31, -174), (42, -179), (53, -198))
        l0 = Line(b2 @ 1, (0, -198))
        half = [b0, b1, b2, l0]
        spade = make_face(half + [mirror(edge, Plane.YZ) for edge in half])
        spade = scale(spade, by=height / spade.bounding_box().size.Y)
        super().__init__(obj=spade, rotation=rotation, align=align, mode=mode)


class Heart(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        b1 = Bezier((0, 146), (20, 169), (67, 198), (97, 198))
        b2 = Bezier(b1 @ 1, (125, 198), (151, 186), (168, 167))
        b3 = Bezier(b2 @ 1, (197, 133), (194, 88), (158, 31))
        b4 = Bezier(b3 @ 1, (126, -13), (94, -48), (62, -95))
        b5 = Bezier(b4 @ 1, (40, -128), (0, -198))
        half = [b1, b2, b3, b4, b5]
        heart = make_face(half + [mirror(edge, Plane.YZ) for edge in half])
        heart = scale(heart, by=height / heart.bounding_box().size.Y)
        super().__init__(obj=heart, rotation=rotation, align=align, mode=mode)


class Diamond(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        quarter = Bezier((135, 0), (94, 69), (47, 134), (0, 198))
        half = [quarter, mirror(quarter, Plane.XZ)]
        diamond = make_face(half + [mirror(edge, Plane.YZ) for edge in half])
        diamond = scale(diamond, by=height / diamond.bounding_box().size.Y)
        super().__init__(obj=diamond, rotation=rotation, align=align, mode=mode)


card_width = 2.5 * IN
card_length = 3.5 * IN
deck = 0.5 * IN
wall = 4 * MM
gap = 0.5 * MM

plan = Rectangle(card_width + 2 * wall, card_length + 2 * wall)
plan = fillet(plan.vertices(), radius=card_width / 15)

box_part = extrude(plan, amount=wall / 2)
walls = plan - offset(plan, amount=-wall)
box_part += extrude(
    Plane(box_part.faces().sort_by(Axis.Z)[-1]) * walls, amount=deck / 2
)
inset_walls = offset(plan, amount=-(wall + gap) / 2) - offset(plan, amount=-wall)
box_part += extrude(
    Plane(box_part.faces().sort_by(Axis.Z)[-1]) * inset_walls, amount=deck / 2
)

outset_walls = plan - offset(plan, amount=-(wall - gap) / 2)
lid_part = extrude(outset_walls, amount=deck / 2)
lid_part += extrude(Plane(lid_part.faces().sort_by(Axis.Z)[-1]) * plan, amount=wall / 2)
holes = GridLocations(3 * card_width / 5, 3 * card_length / 5, 2, 2)
suits = (Heart, Diamond, Spade, Club)
cutouts = Sketch() + [hole * suit(card_length / 5) for hole, suit in zip(holes, suits)]
lid_part -= extrude(Plane(lid_part.faces().sort_by(Axis.Z)[-1]) * cutouts, amount=-wall)

box = Compound([box_part, lid_part.moved(Location((0, 0, (wall + deck) / 2)))])
visible, hidden = box.drawing_view((70, -50, 120))
max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
exporter = ExportSVG(scale=100 / max_dimension)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
exporter.add_shape(visible, layer="Visible")
exporter.add_shape(hidden, layer="Hidden")
# exporter.write(f"assets/card_box.svg")


class PlayingCard(BaseSketchObject):
    """PlayingCard

    A standard playing card modelled as a Face.

    Args:
        rank (Literal['A', '2' .. '10', 'J', 'Q', 'K']): card rank
        suit (Literal['Clubs', 'Spades', 'Hearts', 'Diamonds']): card suit
    """

    width = 2.5 * IN
    height = 3.5 * IN
    suits = {"Clubs": Club, "Spades": Spade, "Hearts": Heart, "Diamonds": Diamond}
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

    def __init__(
        self,
        rank: Literal["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"],
        suit: Literal["Clubs", "Spades", "Hearts", "Diamonds"],
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        width, height = PlayingCard.width, PlayingCard.height
        pip = PlayingCard.suits[suit]

        playing_card = Rectangle(width, height, align=(Align.MIN, Align.MIN))
        playing_card = fillet(playing_card.vertices(), radius=width / 15)

        # the rank and suit in one corner, and upside down in the opposite one
        playing_card -= Pos(width / 7, 8 * height / 9) * Text(
            txt=rank, font_size=width / 7
        )
        playing_card -= Pos(width / 7, 7 * height / 9) * pip(height=width / 12)
        playing_card -= Pos(6 * width / 7, 1 * height / 9) * Text(
            txt=rank, font_size=width / 7, rotation=180
        )
        playing_card -= Pos(6 * width / 7, 2 * height / 9) * pip(
            height=width / 12, rotation=180
        )

        # the pips in the middle: one for an ace or a face card
        rank_int = PlayingCard.ranks.index(rank) + 1
        rank_int = rank_int if rank_int < 10 else 1
        center_radius = 0 if rank_int == 1 else width / 3.5
        suit_rotation = 0 if rank_int == 1 else -90
        suit_height = (0.00159 * rank_int**2 - 0.0380 * rank_int + 0.37) * width
        middle = Pos(width / 2, height / 2)
        playing_card -= [
            middle * place * pip(height=suit_height, rotation=suit_rotation)
            for place in PolarLocations(
                radius=center_radius,
                count=rank_int,
                start_angle=90 if rank_int > 1 else 0,
            )
        ]
        super().__init__(obj=playing_card, rotation=rotation, align=align, mode=mode)


ace_spades = PlayingCard(rank="A", suit="Spades", align=Align.MIN)
ace_spades.color = Color("white")
king_hearts = PlayingCard(rank="K", suit="Hearts", align=Align.MIN)
king_hearts.color = Color("white")
queen_clubs = PlayingCard(rank="Q", suit="Clubs", align=Align.MIN)
queen_clubs.color = Color("white")
jack_diamonds = PlayingCard(rank="J", suit="Diamonds", align=Align.MIN)
jack_diamonds.color = Color("white")
ten_spades = PlayingCard(rank="10", suit="Spades", align=Align.MIN)
ten_spades.color = Color("white")

hand = Compound(
    children=[
        Rot(0, 0, -20) * Pos(0, 0, 0) * ace_spades,
        Rot(0, 0, -10) * Pos(0, 0, -1) * king_hearts,
        Rot(0, 0, 0) * Pos(0, 0, -2) * queen_clubs,
        Rot(0, 0, 10) * Pos(0, 0, -3) * jack_diamonds,
        Rot(0, 0, 20) * Pos(0, 0, -4) * ten_spades,
    ]
)

show_object(Pos(-20, 40) * hand)
show_object(box_part, "box")
show_object(
    Pos(0, 0, (wall + deck) / 2) * lid_part,
    "lid",
    options={"alpha": 0.7},
)
# [End]
