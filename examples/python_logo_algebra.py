"""
Python Logo

name: python_logo_algebra.py
by:   Gumyr
date: October 2nd 2023

desc:
    The Python logo as a custom sketch object, drawn from the Bezier curves
    of the logo's outline, with each snake given its colour.

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

# [Code]

from build123d import *
from ocp_viewer import show


class PythonLogo(BaseSketchObject):
    """Sketch Object: Python Logo

    The two snakes of the Python logo, each a face of its own.

    Args:
        size (float): height of the logo, its larger dimension
        rotation (float, optional): angle in degrees. Defaults to 0.
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX
            of object. Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        size: float,
        rotation: float = 0,
        align: Align | tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        # The outline is in the units of the drawing it was traced from, with
        # the centre of the logo here and the y axis pointing down
        center = Vector(55.5806770629664, 56.194501214517224)
        eye = Vector(40.418785, 13.3290442)

        l1 = Bezier(
            (54.918785, 0.00091927389),
            (50.335132, 0.02221727),
            (45.957846, 0.41313697),
            (42.106285, 1.0946693),
        )
        l2 = Bezier(
            l1 @ 1,
            (30.760069, 3.0991731),
            (28.700036, 7.2947714),
            (28.700035, 15.032169),
        )
        l3 = Polyline(
            l2 @ 1,
            (28.700035, 25.250919),
            (55.512535, 25.250919),
            (55.512535, 28.657169),
            (28.700035, 28.657169),
            (18.637535, 28.657169),
        )
        l4 = Bezier(
            l3 @ 1,
            (10.845076, 28.657169),
            (4.0217762, 33.340886),
            (1.8875352, 42.250919),
        )
        l5 = Bezier(
            l4 @ 1,
            (-0.57428478, 52.463885),
            (-0.68347988, 58.836942),
            (1.8875352, 69.500919),
        )
        l6 = Bezier(
            l5 @ 1,
            (3.7934635, 77.438771),
            (8.3450784, 83.094667),
            (16.137535, 83.094669),
        )
        l7 = Polyline(l6 @ 1, (25.356285, 83.094669), (25.356285, 70.844669))
        l8 = Bezier(
            l7 @ 1,
            (25.356285, 61.994767),
            (33.013429, 54.188421),
            (42.106285, 54.188419),
        )
        l9 = Line(l8 @ 1, (68.887535, 54.188419))
        l10 = Bezier(
            l9 @ 1,
            (76.342486, 54.188419),
            (82.293788, 48.050255),
            (82.293785, 40.563419),
        )
        l11 = Line(l10 @ 1, (82.293785, 15.032169))
        l12 = Bezier(
            l11 @ 1,
            (82.293785, 7.7658304),
            (76.163805, 2.3073919),
            (68.887535, 1.0946693),
        )
        l13 = Bezier(
            l12 @ 1,
            (64.281548, 0.32794397),
            (59.502438, -0.02037903),
            (54.918785, 0.00091927389),
        )
        outline = Curve([l1, l2, l3, l4, l5, l6, l7, l8, l9, l10, l11, l12, l13])

        # Moving the outline puts the centre of the logo at the origin
        snake = make_face(Pos(-center) * outline)
        snake -= Pos(eye - center) * Ellipse(10.0625002 / 2, 10.2187498 / 2)
        snake = mirror(snake, about=Plane.XZ)  # y axis up
        snake = scale(snake, by=size / (2 * snake.bounding_box().max.Y))

        # The second snake is the first turned half way round the centre
        upper = snake.face()
        logo = Sketch([upper, upper.rotate(Axis.Z, 180)])
        super().__init__(obj=logo, rotation=rotation, align=align, mode=mode)


logo = PythonLogo(10)

# Each snake is a face, and is given its colour from the logo
blue, yellow = logo.faces().sort_by(Axis.Y, reverse=True)
blue.color = Color(0x306998)
yellow.color = Color(0xFFD43B)

show(blue, yellow)
# [End]
