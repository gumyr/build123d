"""

name: boxes_on_faces.py
by:   Gumyr
date: March 6th 2023

desc: Demo adding features to multiple faces in one operation.

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
# [Imports]
import build123d as bd
from ocp_vscode import *

# [Code]
with bd.BuildPart() as bp:
    bd.Box(3, 3, 3)
    with bd.BuildSketch(*bp.faces()):
        bd.Rectangle(1, 2, rotation=45)
    bd.extrude(amount=0.1)

assert abs(bp.part.volume - (3**3 + 6 * (1 * 2 * 0.1)) < 1e-3)

if "show_object" in locals():
    show_object(bp.part.wrapped, name="box on faces")
# [End]