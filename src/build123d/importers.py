"""
build123d imports

name: importers.py
by:   Gumyr
date: March 1st, 2023

desc:
    This python module contains importers from multiple file formats.

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
# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error

import os
from math import degrees
from pathlib import Path
from typing import TextIO, Union

import OCP.IFSelect
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.RWStl import RWStl
from OCP.STEPControl import STEPControl_Reader
from OCP.TopoDS import TopoDS_Face, TopoDS_Shape, TopoDS_Wire
from ocpsvg import ColorAndLabel, import_svg_document
from svgpathtools import svg2paths

from build123d.geometry import Color
from build123d.topology import Compound, Face, Shape, ShapeList, Wire

def import_brep(file_name: str) -> Shape:
    """Import shape from a BREP file

    Args:
        file_name (str): brep file

    Raises:
        ValueError: file not found

    Returns:
        Shape: build123d object
    """
    shape = TopoDS_Shape()
    builder = BRep_Builder()

    BRepTools.Read_s(shape, file_name, builder)

    if shape.IsNull():
        raise ValueError(f"Could not import {file_name}")

    return Shape.cast(shape)


def import_step(file_name: str) -> Compound:
    """import_step

    Extract shapes from a STEP file and return them as a Compound object.

    Args:
        file_name (str): file path of STEP file to import

    Raises:
        ValueError: can't open file

    Returns:
        Compound: contents of STEP file
    """
    # Now read and return the shape
    reader = STEPControl_Reader()
    read_status = reader.ReadFile(file_name)
    # pylint fails to understand OCP's module here, so suppress on the next line.
    if read_status != OCP.IFSelect.IFSelect_RetDone: # pylint: disable=no-member
        raise ValueError(f"STEP File {file_name} could not be loaded")
    for i in range(reader.NbRootsForTransfer()):
        reader.TransferRoot(i + 1)

    occ_shapes = []
    for i in range(reader.NbShapes()):
        occ_shapes.append(reader.Shape(i + 1))

    # Make sure that we extract all the solids
    solids = []
    for shape in occ_shapes:
        solids.append(Shape.cast(shape))

    return Compound.make_compound(solids)


def import_stl(file_name: str) -> Face:
    """import_stl

    Extract shape from an STL file and return it as a Face reference object.

    Note that importing with this method and creating a reference is very fast while
    creating an editable model (with Mesher) may take minutes depending on the size
    of the STL file.

    Args:
        file_name (str): file path of STL file to import

    Raises:
        ValueError: Could not import file

    Returns:
        Face: STL model
    """
    # Read and return the shape
    reader = RWStl.ReadFile_s(file_name)
    face = TopoDS_Face()
    BRep_Builder().MakeFace(face, reader)
    stl_obj = Face.cast(face)
    return stl_obj


def import_svg_as_buildline_code(file_name: str) -> tuple[str, str]:
    """translate_to_buildline_code

    Translate the contents of the given svg file into executable build123d/BuildLine code.

    Args:
        file_name (str): svg file name

    Returns:
        tuple[str, str]: code, builder instance name
    """

    translator = {
        "Line": ["Line", "start", "end"],
        "CubicBezier": ["Bezier", "start", "control1", "control2", "end"],
        "QuadraticBezier": ["Bezier", "start", "control", "end"],
        "Arc": [
            "EllipticalCenterArc",
            # "EllipticalStartArc",
            "start",
            "end",
            "radius",
            "rotation",
            "large_arc",
            "sweep",
        ],
    }
    paths_info = svg2paths(file_name)
    paths, _path_attributes = paths_info[0], paths_info[1]
    builder_name = os.path.basename(file_name).split(".")[0]
    builder_name = builder_name if builder_name.isidentifier() else "builder"
    buildline_code = [
        "from build123d import *",
        f"with BuildLine() as {builder_name}:",
    ]
    for path in paths:
        for curve in path:
            class_name = type(curve).__name__
            if class_name == "Arc":
                values = [
                    (curve.__dict__["center"].real, curve.__dict__["center"].imag)
                ]
                values.append(curve.__dict__["radius"].real)
                values.append(curve.__dict__["radius"].imag)
                start, end = sorted(
                    [
                        curve.__dict__["theta"],
                        curve.__dict__["theta"] + curve.__dict__["delta"],
                    ]
                )
                values.append(start)
                values.append(end)
                values.append(degrees(curve.__dict__["phi"]))
                if curve.__dict__["delta"] < 0.0:
                    values.append("AngularDirection.CLOCKWISE")
                else:
                    values.append("AngularDirection.COUNTER_CLOCKWISE")

                # EllipticalStartArc implementation
                # values = [p.__dict__[parm] for parm in translator[class_name][1:3]]
                # values.append(p.__dict__["radius"].real)
                # values.append(p.__dict__["radius"].imag)
                # values.extend([p.__dict__[parm] for parm in translator[class_name][4:]])
            else:
                values = [curve.__dict__[parm] for parm in translator[class_name][1:]]
            values_str = ",".join(
                [
                    f"({v.real}, {v.imag})" if isinstance(v, complex) else str(v)
                    for v in values
                ]
            )
            buildline_code.append(f"    {translator[class_name][0]}({values_str})")

    return ("\n".join(buildline_code), builder_name)


def import_svg(
    svg_file: Union[str, Path, TextIO],
    *,
    flip_y: bool = True,
    ignore_visibility: bool = False,
    label_by: str = "id",
    is_inkscape_label: bool = False,
) -> ShapeList[Union[Wire, Face]]:
    """import_svg

    Args:
        svg_file (Union[str, Path, TextIO]): svg file
        flip_y (bool, optional): flip objects to compensate for svg orientation. Defaults to True.
        ignore_visibility (bool, optional): Defaults to False.
        label_by (str, optional): xml attribute. Defaults to "id".
        is_inkscape_label (bool, optional): flag to indicate that the attribute
            is an Inkscape label like `inkscape:label` - label_by would be set to
            `label` in this case. Defaults to False.

    Raises:
        ValueError: unexpected shape type

    Returns:
        ShapeList[Union[Wire, Face]]: objects contained in svg
    """
    shapes = []
    label_by = (
        "{http://www.inkscape.org/namespaces/inkscape}" + label_by
        if is_inkscape_label
        else label_by
    )
    for face_or_wire, color_and_label in import_svg_document(
        svg_file,
        flip_y=flip_y,
        ignore_visibility=ignore_visibility,
        metadata=ColorAndLabel.Label_by(label_by),
    ):
        if isinstance(face_or_wire, TopoDS_Wire):
            shape = Wire(face_or_wire)
        elif isinstance(face_or_wire, TopoDS_Face):
            shape = Face(face_or_wire)
        else:  # should not happen
            raise ValueError(f"unexpected shape type: {type(face_or_wire).__name__}")

        if shape.wrapped:
            shape.color = Color(*color_and_label.color_for(shape.wrapped))
        shape.label = color_and_label.label
        shapes.append(shape)

    return ShapeList(shapes)
