from build123d import *
from ocp_vscode import show


class Shamrock(BaseSketchObject):
    """Sketch Object: Shamrock

    Adds a four leaf clover

    Args:
        height (float): y axis dimension
        rotation (float, optional): angle in degrees. Defaults to 0.
        align (tuple[Align, Align], optional): alignment. Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch() as shamrock:
            with BuildLine():
                b0 = Bezier((240, 310), (112, 325), (162, 438), (252, 470))
                b1 = Bezier(b0 @ 1, (136, 431), (73, 589), (179, 643))
                b2 = Bezier(b1 @ 1, (151, 747), (293, 770), (360, 679))
                b3 = Bezier(b2 @ 1, (358, 736), (366, 789), (392, 840))
                l0 = Line(b3 @ 1, (420, 820))
                b4 = Bezier(l0 @ 1, (366, 781), (374, 670), (380, 670))
                b5 = Bezier(b4 @ 1, (400, 794), (506, 789), (528, 727))
                b6 = Bezier(b5 @ 1, (636, 733), (638, 578), (507, 541))
                b7 = Bezier(b6 @ 1, (628, 559), (651, 380), (575, 365))
                b8 = Bezier(b7 @ 1, (592, 269), (420, 268), (417, 361))
                b9 = Bezier(b8 @ 1, (410, 253), (262, 222), b0 @ 0)
                mirror(about=Plane.XZ, mode=Mode.REPLACE)
            make_face()
            scale(by=height / shamrock.sketch.bounding_box().size.Y)
        super().__init__(
            obj=shamrock.sketch.translate(
                -shamrock.sketch.center(CenterOf.BOUNDING_BOX)
            ),
            rotation=rotation,
            align=align,
            mode=mode,
        )


with BuildSketch() as shamrock_example:
    Shamrock(10)

show(shamrock_example)
