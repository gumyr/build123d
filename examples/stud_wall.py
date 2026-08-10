"""
Stud Wall creation using RigidJoints to position components.

name: stud_wall.py
by:   Gumyr
date: February 17, 2024

desc:
    This example builds stud walls from dimensional lumber as an assembly
    with the parts positioned with RigidJoints.

license:

    Copyright 2024 Gumyr

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
from typing import Union
import copy


# [Code]
class Stud(BasePartObject):
    """Part Object: Stud

    Create a dimensional framing stud.

    Args:
        length (float): stud size
        width (float): stud size
        thickness (float): stud size
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        align (Union[Align, tuple[Align, Align, Align]], optional): align min, center,
            or max of object. Defaults to (Align.CENTER, Align.CENTER, Align.MIN).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        length: float = 8 * FT,
        width: float = 3.5 * IN,
        thickness: float = 1.5 * IN,
        rotation: RotationLike = (0, 0, 0),
        align: Union[None, Align, tuple[Align, Align, Align]] = (
            Align.CENTER,
            Align.CENTER,
            Align.MIN,
        ),
        mode: Mode = Mode.ADD,
    ):
        self.length = length
        self.width = width
        self.thickness = thickness

        # Create the basic shape
        with BuildPart() as stud:
            with BuildSketch():
                RectangleRounded(thickness, width, 0.25 * IN)
            extrude(amount=length)

        # Create a Part object with appropriate alignment and rotation
        super().__init__(part=stud.part, rotation=rotation, align=align, mode=mode)

        # Add joints to the ends of the stud
        RigidJoint("end0", self, Location())
        RigidJoint("end1", self, Location((0, 0, length), (1, 0, 0), 180))


class StudWall(Compound):
    """StudWall

    A simple stud wall assembly with top and sole plates.

    Args:
        length (float): wall length
        depth (float, optional): stud width. Defaults to 3.5*IN.
        height (float, optional): wall height. Defaults to 8*FT.
        stud_spacing (float, optional): center-to-center. Defaults to 16*IN.
        stud_thickness (float, optional): Defaults to 1.5*IN.
    """

    def __init__(
        self,
        length: float,
        depth: float = 3.5 * IN,
        height: float = 8 * FT,
        stud_spacing: float = 16 * IN,
        stud_thickness: float = 1.5 * IN,
    ):
        # Create the object that will be used for top and sole plates
        plate = Stud(
            length,
            depth,
            rotation=(0, -90, 0),
            align=(Align.MIN, Align.CENTER, Align.MAX),
        )
        # Define where studs will go on the plates
        stud_locations = Pos(stud_thickness / 2, 0, stud_thickness) * GridLocations(
            stud_spacing, 0, int(length / stud_spacing) + 1, 1, align=Align.MIN
        )
        stud_locations.append(Pos(length - stud_thickness / 2, 0, stud_thickness))

        # Create a single stud that will be copied for efficiency
        stud = Stud(height - 2 * stud_thickness, depth, stud_thickness)

        # For efficiency studs in the walls are copies with their own position
        studs = []
        for i, loc in enumerate(stud_locations):
            stud_joint = RigidJoint(f"stud{i}", plate, loc)
            stud_copy = copy.copy(stud)
            stud_joint.connect_to(stud_copy.joints["end0"])
            studs.append(stud_copy)
        top_plate = copy.copy(plate)
        sole_plate = copy.copy(plate)

        # Position the top plate relative to the top of the first stud
        studs[0].joints["end1"].connect_to(top_plate.joints["stud0"])

        # Build the assembly of parts
        super().__init__(children=[top_plate, sole_plate] + studs)

        # Add joints to the wall
        RigidJoint("inside0", self, Location((depth / 2, depth / 2, 0), (0, 0, 1), 90))
        RigidJoint("end0", self, Location())


x_wall = StudWall(13 * FT)
y_wall = StudWall(9 * FT)
x_wall.joints["inside0"].connect_to(y_wall.joints["end0"])

show(x_wall, y_wall, render_joints=False)
# [End]
