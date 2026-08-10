"""

name: custom_sketch_objects.py
by:   Gumyr
date: Jan 21st 2023

desc:

    This example demonstrates the creation of a Playing Card storage box with
    user generated custom BuildSketch objects. Four new BuildSketch objects are
    created: Club, Spade, Heart, and Diamond, which are then used to punch
    holes into the top of the box's lid.

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

from build123d import *
from ocp_vscode import show


class Club(BaseSketchObject):
    """Sketch Object: Club

    The club suit symbol from a playing card.

    Args:
        height (float): size along the Y-axis
        rotation (float, optional): angle from X-axis. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        # Create the club shape
        # Note: The workplane and mode must be set here to avoid interactions with
        #       builders in difference scopes.
        with BuildSketch(Plane.XY, mode=Mode.PRIVATE) as club:
            with BuildLine():
                l0 = Line((0, -188), (76, -188))
                b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
                b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
                b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
                b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / club.sketch.bounding_box().size.Y)

        # Pass the shape to the BaseSketchObject class to create a new Club object
        super().__init__(obj=club.sketch, rotation=rotation, align=align, mode=mode)


class Spade(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch(Plane.XY, mode=Mode.PRIVATE) as spade:
            with BuildLine():
                b0 = Bezier((0, 198), (6, 190), (41, 127), (112, 61))
                b1 = Bezier(b0 @ 1, (242, -72), (114, -168), (11, -105))
                b2 = Bezier(b1 @ 1, (31, -174), (42, -179), (53, -198))
                l0 = Line(b2 @ 1, (0, -198))
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / spade.sketch.bounding_box().size.Y)
        super().__init__(obj=spade.sketch, rotation=rotation, align=align, mode=mode)


class Heart(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch(Plane.XY, mode=Mode.PRIVATE) as heart:
            with BuildLine():
                b1 = Bezier((0, 146), (20, 169), (67, 198), (97, 198))
                b2 = Bezier(b1 @ 1, (125, 198), (151, 186), (168, 167))
                b3 = Bezier(b2 @ 1, (197, 133), (194, 88), (158, 31))
                b4 = Bezier(b3 @ 1, (126, -13), (94, -48), (62, -95))
                b5 = Bezier(b4 @ 1, (40, -128), (0, -198))
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / heart.sketch.bounding_box().size.Y)
        super().__init__(obj=heart.sketch, rotation=rotation, align=align, mode=mode)


class Diamond(BaseSketchObject):
    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch(Plane.XY, mode=Mode.PRIVATE) as diamond:
            with BuildLine():
                Bezier((135, 0), (94, 69), (47, 134), (0, 198))
                mirror(about=Plane.XZ)
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / diamond.sketch.bounding_box().size.Y)
        super().__init__(obj=diamond.sketch, rotation=rotation, align=align, mode=mode)


# The inside of the box fits 2.5x3.5" playing card deck with a small gap
pocket_w = 2.5 * IN + 2 * MM
pocket_l = 3.5 * IN + 2 * MM
pocket_t = 0.5 * IN + 2 * MM
wall_t = 3 * MM  # Wall thickness
bottom_t = wall_t / 2  # Top and bottom thickness
lid_gap = 0.5 * MM  # Spacing between base and lid
lip_t = wall_t / 2 - lid_gap / 2  # Lip thickness


with BuildPart() as box_builder:
    with BuildSketch() as box_plan:
        RectangleRounded(pocket_w + 2 * wall_t, pocket_l + 2 * wall_t, pocket_w / 15)
    extrude(amount=bottom_t + pocket_t / 2)
    base_top = box_builder.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(base_top) as walls:
        offset(box_plan.sketch, amount=-lip_t, mode=Mode.ADD)
    extrude(amount=pocket_t / 2)
    with BuildSketch(Plane.XY.offset(wall_t / 2)):
        offset(box_plan.sketch, amount=-wall_t, mode=Mode.ADD)
    extrude(amount=pocket_t, mode=Mode.SUBTRACT)
box = box_builder.part

with BuildPart() as lid_builder:
    add(box_plan.sketch)
    extrude(amount=pocket_t / 2 + bottom_t)
    with BuildSketch() as pocket:
        offset(box_plan.sketch, amount=-(wall_t - lip_t), mode=Mode.ADD)
    extrude(amount=pocket_t / 2, mode=Mode.SUBTRACT)

    with BuildSketch(lid_builder.faces().sort_by(Axis.Z)[-1]) as suits:
        with Locations((-0.3 * pocket_w, 0.3 * pocket_l)):
            Heart(pocket_l / 5)
        with Locations((-0.3 * pocket_w, -0.3 * pocket_l)):
            Diamond(pocket_l / 5)
        with Locations((0.3 * pocket_w, 0.3 * pocket_l)):
            Spade(pocket_l / 5)
        with Locations((0.3 * pocket_w, -0.3 * pocket_l)):
            Club(pocket_l / 5)
    extrude(amount=-wall_t, mode=Mode.SUBTRACT)
lid = lid_builder.part.moved(Location((0, 0, (wall_t + pocket_t) / 2)))

show(box, lid, names=["box", "lid"], alphas=[1.0, 0.6])
