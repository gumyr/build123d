"""

name: custom_sketch_objects.py
by:   Gumyr
date: Jan 21st 2023

desc:

    This example demonstrates user generated custom BuildSketch objects.

license:

    Copyright 2023 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
from typing import Literal
from build123d import *


class Club(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch(mode=Mode.PRIVATE) as club:
            with BuildLine():
                l0 = Line((0, -188), (76, -188))
                b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
                b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
                b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
                b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
                Mirror(about=Plane.YZ)
            MakeFace()
            Scale(by=height / club.sketch.bounding_box().size.Y)
        super().__init__(obj=club.sketch, rotation=rotation, align=align, mode=mode)


class Spade(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch(mode=Mode.PRIVATE) as spade:
            with BuildLine():
                b0 = Bezier((0, 198), (6, 190), (41, 127), (112, 61))
                b1 = Bezier(b0 @ 1, (242, -72), (114, -168), (11, -105))
                b2 = Bezier(b1 @ 1, (31, -174), (42, -179), (53, -198))
                l0 = Line(b2 @ 1, (0, -198))
                Mirror(about=Plane.YZ)
            MakeFace()
            Scale(by=height / spade.sketch.bounding_box().size.Y)
        super().__init__(obj=spade.sketch, rotation=rotation, align=align, mode=mode)


class Heart(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch(mode=Mode.PRIVATE) as heart:
            with BuildLine():
                b1 = Bezier((0, 146), (20, 169), (67, 198), (97, 198))
                b2 = Bezier(b1 @ 1, (125, 198), (151, 186), (168, 167))
                b3 = Bezier(b2 @ 1, (197, 133), (194, 88), (158, 31))
                b4 = Bezier(b3 @ 1, (126, -13), (94, -48), (62, -95))
                b5 = Bezier(b4 @ 1, (40, -128), (0, -198))
                Mirror(about=Plane.YZ)
            MakeFace()
            Scale(by=height / heart.sketch.bounding_box().size.Y)
        super().__init__(obj=heart.sketch, rotation=rotation, align=align, mode=mode)


class Diamond(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch(mode=Mode.PRIVATE) as diamond:
            with BuildLine():
                Bezier((135, 0), (94, 69), (47, 134), (0, 198))
                Mirror(about=Plane.XZ)
                Mirror(about=Plane.YZ)
            MakeFace()
            Scale(by=height / diamond.sketch.bounding_box().size.Y)
        super().__init__(obj=diamond.sketch, rotation=rotation, align=align, mode=mode)


card_width = 2.5 * IN
card_length = 3.5 * IN
deck = 0.5 * IN
wall = 4 * MM
gap = 0.5 * MM

with BuildPart() as box_builder:
    with BuildSketch() as plan:
        Rectangle(card_width + 2 * wall, card_length + 2 * wall)
        Fillet(*plan.vertices(), radius=card_width / 15)
    Extrude(amount=wall / 2)
    with BuildSketch(box_builder.faces().sort_by(Axis.Z)[-1]) as walls:
        Add(plan.sketch)
        Offset(plan.sketch, amount=-wall, mode=Mode.SUBTRACT)
    Extrude(amount=deck / 2)
    with BuildSketch(box_builder.faces().sort_by(Axis.Z)[-1]) as inset_walls:
        Offset(plan.sketch, amount=-(wall + gap) / 2, mode=Mode.ADD)
        Offset(plan.sketch, amount=-wall, mode=Mode.SUBTRACT)
    Extrude(amount=deck / 2)

with BuildPart() as lid_builder:
    with BuildSketch() as outset_walls:
        Add(plan.sketch)
        Offset(plan.sketch, amount=-(wall - gap) / 2, mode=Mode.SUBTRACT)
    Extrude(amount=deck / 2)
    with BuildSketch(lid_builder.faces().sort_by(Axis.Z)[-1]) as top:
        Add(plan.sketch)
    Extrude(amount=wall / 2)
    with BuildSketch(lid_builder.faces().sort_by(Axis.Z)[-1]):
        holes = GridLocations(
            3 * card_width / 5, 3 * card_length / 5, 2, 2
        ).local_locations
        for i, hole in enumerate(holes):
            with Locations(hole) as hole_loc:
                if i == 0:
                    Heart(card_length / 5)
                elif i == 1:
                    Diamond(card_length / 5)
                elif i == 2:
                    Spade(card_length / 5)
                elif i == 3:
                    Club(card_length / 5)
    Extrude(amount=-wall, mode=Mode.SUBTRACT)


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
        with BuildSketch() as playing_card:
            Rectangle(
                PlayingCard.width, PlayingCard.height, align=(Align.MIN, Align.MIN)
            )
            Fillet(*playing_card.vertices(), radius=PlayingCard.width / 15)
            with Locations(
                (
                    PlayingCard.width / 7,
                    8 * PlayingCard.height / 9,
                )
            ):
                Text(
                    txt=rank,
                    font_size=PlayingCard.width / 7,
                    mode=Mode.SUBTRACT,
                )
            with Locations(
                (
                    PlayingCard.width / 7,
                    7 * PlayingCard.height / 9,
                )
            ):
                PlayingCard.suits[suit](
                    height=PlayingCard.width / 12, mode=Mode.SUBTRACT
                )
            with Locations(
                (
                    6 * PlayingCard.width / 7,
                    1 * PlayingCard.height / 9,
                )
            ):
                Text(
                    txt=rank,
                    font_size=PlayingCard.width / 7,
                    rotation=180,
                    mode=Mode.SUBTRACT,
                )
            with Locations(
                (
                    6 * PlayingCard.width / 7,
                    2 * PlayingCard.height / 9,
                )
            ):
                PlayingCard.suits[suit](
                    height=PlayingCard.width / 12, rotation=180, mode=Mode.SUBTRACT
                )
            rank_int = PlayingCard.ranks.index(rank) + 1
            rank_int = rank_int if rank_int < 10 else 1
            with Locations((PlayingCard.width / 2, PlayingCard.height / 2)):
                center_radius = 0 if rank_int == 1 else PlayingCard.width / 3.5
                suit_rotation = 0 if rank_int == 1 else -90
                suit_height = (
                    0.00159 * rank_int**2 - 0.0380 * rank_int + 0.37
                ) * PlayingCard.width
                with PolarLocations(
                    radius=center_radius,
                    count=rank_int,
                    start_angle=90 if rank_int > 1 else 0,
                ):
                    PlayingCard.suits[suit](
                        height=suit_height,
                        rotation=suit_rotation,
                        mode=Mode.SUBTRACT,
                    )
        super().__init__(playing_card.sketch.wrapped)


playing_card = PlayingCard(rank="A", suit="Spades")

if "show_object" in locals():
    show_object(playing_card)
    # show_object(outer_box_builder.part, "outer")
    # show_object(b, name="b", options={"alpha": 0.8})
    show_object(box_builder.part, "box_builder")
    show_object(
        lid_builder.part.moved(Location((0, 0, (wall + deck) / 2))),
        "lid_builder",
        options={"alpha": 0.7},
    )
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
