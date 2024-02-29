"""

name: intersecting_pipes.py
by:   Gumyr
date: July 14th 2022

desc:

    This example demonstrates working on multiple planes created from object
    faces and using a Select.LAST selector to return edges to be filleted.

license:

    Copyright 2022 Gumyr

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

import logging
from build123d import *
from ocp_vscode import show

# logging.basicConfig(
#     filename="intersecting_pipes.log",
#     level=logging.DEBUG,
#     format="%(name)s-%(levelname)5s %(asctime)s - [%(filename)s:%(lineno)s - %(funcName)20s() ] - %(message)s",
# )
# logging.info("Starting pipes test")

with BuildPart() as pipes:
    box = Box(10, 10, 10, rotation=(10, 20, 30))
    with BuildSketch(*box.faces()) as pipe:
        Circle(4)
    extrude(amount=-5, mode=Mode.SUBTRACT)
    with BuildSketch(*box.faces()) as pipe:
        Circle(4.5)
        Circle(4, mode=Mode.SUBTRACT)
    extrude(amount=10)
    fillet(pipes.edges(Select.LAST), 0.2)

assert abs(pipes.part.volume - 1015.939005681509) < 1e-3

show(pipes, names=["intersecting pipes"])
