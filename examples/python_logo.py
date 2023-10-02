"""
Python Logo

name: python_logo.py
by:   Gumyr
date: October 2nd 2023

desc:
    This python module creates the Python logo as a Sketch object.

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


class PythonLogo(BaseSketchObject):
    """PythonLogo

    Args:
        size (float): max size (Y direction - although the logo is almost square)
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]
    _logo_colors = {
        "Cyan-Blue Azure": Color(75 / 255, 139 / 255, 190 / 255),
        "Lapis Lazuli": Color(48 / 255, 105 / 255, 152 / 255),
        "Shandy": Color(255 / 255, 232 / 255, 115 / 255),
        "Sunglow": Color(255 / 255, 212 / 255, 59 / 255),
        "Granite Gray": Color(100 / 255, 100 / 255, 100 / 255),
    }

    def __init__(
        self,
        size: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        center = Vector(55.5806770629664, 56.194501214517224)

        with BuildSketch() as logo:
            with BuildLine(mode=Mode.PRIVATE) as snake:
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

            with Locations(-center):
                add(snake)
            make_face()
            with Locations(Vector(40.418785, 13.3290442) - center):
                Ellipse(10.0625002 / 2, 10.2187498 / 2, mode=Mode.SUBTRACT)
            add(logo.sketch, rotation=180)
            mirror(about=Plane.YZ, mode=Mode.REPLACE)
            current_size = max(*logo.sketch.bounding_box().size.to_tuple())
            scale(by=size / current_size)

        super().__init__(obj=logo.sketch, rotation=rotation, align=align, mode=mode)


if __name__ == "__main__":
    show(PythonLogo(10))
