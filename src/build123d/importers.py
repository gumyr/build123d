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
import re
import unicodedata
import warnings
from os import PathLike, fsdecode
from pathlib import Path
from typing import Literal, TextIO, overload

import svgpathtools
from typing_extensions import deprecated
from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Builder
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepTools import BRepTools
from OCP.gp import gp_Trsf
from OCP.Quantity import Quantity_ColorRGBA
from OCP.RWStl import RWStl
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import (
    TopoDS_Compound,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Vertex,
    TopoDS_Wire,
)
from OCP.XCAFDoc import (
    XCAFDoc_ColorCurv,
    XCAFDoc_ColorGen,
    XCAFDoc_ColorSurf,
    XCAFDoc_ColorTool,
    XCAFDoc_DocumentTool,
)
from ocpsvg import ColorAndLabel, import_svg_document

from build123d.build_common import CM, FT, IN, MC, MM, M
from build123d.build_enums import Align, Unit
from build123d.geometry import (
    TOL_DIGITS,
    TOLERANCE,
    Color,
    Location,
    Vector,
    to_align_offset,
)
from build123d.topology import (
    Compound,
    Edge,
    Face,
    Shape,
    ShapeList,
    Shell,
    Solid,
    Vertex,
    Wire,
    downcast,
)

topods_lut = {
    TopoDS_Compound: Compound,
    TopoDS_Edge: Edge,
    TopoDS_Face: Face,
    TopoDS_Shell: Shell,
    TopoDS_Solid: Solid,
    TopoDS_Vertex: Vertex,
    TopoDS_Wire: Wire,
}


def import_brep(file_name: PathLike | str | bytes) -> Shape:
    """Import shape from a BREP file

    Args:
        file_name (Union[PathLike, str, bytes]): brep file

    Raises:
        ValueError: file not found

    Returns:
        Shape: build123d object
    """
    shape = TopoDS_Shape()
    builder = BRep_Builder()

    file_name_str = fsdecode(file_name)
    BRepTools.Read_s(shape, file_name_str, builder)

    if shape.IsNull():
        raise ValueError(f"Could not import {file_name_str}")

    return Compound.cast(shape)


def import_step(filename: PathLike | str | bytes) -> Compound:
    """import_step

    Extract shapes from a STEP file and return them as a Compound object.

    Args:
        file_name (Union[PathLike, str, bytes]): file path of STEP file to import

    Raises:
        ValueError: can't open file

    Returns:
        Compound: contents of STEP file
    """

    def get_name(label: TDF_Label) -> str:
        """Extract name and format"""
        name = ""
        std_name = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), std_name):
            name = TCollection_AsciiString(std_name.Get()).ToCString()
        # Remove characters that cause ocp_vscode to fail
        clean_name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
        return clean_name.translate(str.maketrans(" .()", "____"))

    def get_shape_color_from_cache(obj: TopoDS_Shape) -> Quantity_ColorRGBA | None:
        """Get the color of a shape from a cache"""
        key = hash(obj.TShape())
        if key in _color_cache:
            return _color_cache[key]

        col = Quantity_ColorRGBA()
        has_color = (
            color_tool.GetColor(obj, XCAFDoc_ColorCurv, col)
            or color_tool.GetColor(obj, XCAFDoc_ColorGen, col)
            or color_tool.GetColor(obj, XCAFDoc_ColorSurf, col)
        )
        _color_cache[key] = col if has_color else None
        return _color_cache[key]

    def get_color(shape: TopoDS_Shape) -> Quantity_ColorRGBA | None:
        """Get the color - take that of the largest Face if multiple"""
        shape_color = get_shape_color_from_cache(shape)
        if shape_color is not None:
            return shape_color

        max_extent = -1.0
        winner = None
        exp = TopExp_Explorer(shape, TopAbs_FACE)
        while exp.More():
            face = exp.Current()
            col = get_shape_color_from_cache(face)
            if col is not None:
                box = Bnd_Box()
                BRepBndLib.Add_s(face, box)
                extent = box.SquareExtent()
                if extent > max_extent:
                    max_extent = extent
                    winner = col
            exp.Next()
        return winner

    def get_label_color(label: TDF_Label) -> Quantity_ColorRGBA | None:
        """Get color directly from an XDE label."""
        col = Quantity_ColorRGBA()
        if (
            XCAFDoc_ColorTool.GetColor_s(label, XCAFDoc_ColorCurv, col)
            or XCAFDoc_ColorTool.GetColor_s(label, XCAFDoc_ColorGen, col)
            or XCAFDoc_ColorTool.GetColor_s(label, XCAFDoc_ColorSurf, col)
        ):
            return col
        return None

    def build_assembly(parent_tdf_label: TDF_Label | None = None) -> list[Shape]:
        """Recursively extract object into an assembly"""
        sub_tdf_labels = TDF_LabelSequence()
        if parent_tdf_label is None:
            shape_tool.GetFreeShapes(sub_tdf_labels)
        else:
            shape_tool.GetComponents_s(parent_tdf_label, sub_tdf_labels)

        sub_shapes: list[Shape] = []
        for i in range(sub_tdf_labels.Length()):
            sub_tdf_label = sub_tdf_labels.Value(i + 1)
            if shape_tool.IsReference_s(sub_tdf_label):
                ref_tdf_label = TDF_Label()
                shape_tool.GetReferredShape_s(sub_tdf_label, ref_tdf_label)
            else:
                ref_tdf_label = sub_tdf_label

            sub_topo_shape = downcast(shape_tool.GetShape_s(ref_tdf_label))
            if shape_tool.IsAssembly_s(ref_tdf_label):
                sub_shape = Compound()
                sub_shape.children = build_assembly(ref_tdf_label)
            else:
                sub_shape = topods_lut[type(sub_topo_shape)](sub_topo_shape)

            # Priority: instance/component label -> referred shape label -> geometric fallback
            instance_color = get_label_color(sub_tdf_label)
            referred_color = get_label_color(ref_tdf_label)
            shape_fallback_color = get_color(sub_topo_shape)
            sub_shape.color = instance_color or referred_color or shape_fallback_color

            sub_shape.label = get_name(ref_tdf_label)
            sub_shape.move(Location(shape_tool.GetLocation_s(sub_tdf_label)))

            sub_shapes.append(sub_shape)
        return sub_shapes

    if not os.path.exists(filename):
        raise FileNotFoundError(filename)

    # Retrieving color info is expensive so cache the lookups
    _color_cache: dict[int, Quantity_ColorRGBA | None] = {}

    fmt = TCollection_ExtendedString("XCAF")
    doc = TDocStd_Document(fmt)
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    reader.SetLayerMode(True)
    reader.ReadFile(fsdecode(filename))
    reader.Transfer(doc)

    root = Compound()
    root.children = build_assembly()
    # Remove empty Compound wrapper if single free object
    if len(root.children) == 1:
        root = root.children[0]

    return root


def import_stl(file_name: PathLike | str | bytes, model_unit: Unit = Unit.MM) -> Face:
    """import_stl

    Extract shape from an STL file and return it as a Face reference object.

    Note that importing with this method and creating a reference is very fast while
    creating an editable model (with Mesher) may take minutes depending on the size
    of the STL file.

    Args:
        file_name (Union[PathLike, str, bytes]): file path of STL file to import
        model_unit (Unit, optional): the default unit used when creating the model. For
            example, Blender defaults to Unit.M. Defaults to Unit.MM.

    Raises:
        ValueError: Could not import file
        ValueError: Invalid model_unit

    Returns:
        Face: STL model
    """
    # Read STL file
    reader = RWStl.ReadFile_s(fsdecode(file_name))

    # Check for any required scaling
    if model_unit == Unit.MM:
        pass
    else:
        conversion_factor = {
            Unit.MC: MC,  # MICRO
            Unit.MM: MM,  # MILLIMETER
            Unit.CM: CM,  # CENTIMETER
            Unit.M: M,  # METER
            Unit.IN: IN,  # INCH
            Unit.FT: FT,  # FOOT
        }
        try:
            scale_factor = conversion_factor[model_unit]
        except KeyError as exc:
            raise ValueError(
                f"model_scale must be one of: {[unit.name for unit in Unit]}"
            ) from exc
        transformation = gp_Trsf()
        transformation.SetScaleFactor(scale_factor)

        for i in range(1, reader.NbNodes() + 1):
            p = reader.Node(i)
            p.Transform(transformation)
            reader.SetNode(i, p)

    face = TopoDS_Face()
    BRep_Builder().MakeFace(face, reader)
    return Face.cast(face)


def import_svg_as_buildline_code(
    file_name: PathLike | str | bytes,
    precision: int = TOL_DIGITS,
) -> tuple[str, str]:
    """translate_to_buildline_code

    Translate the contents of the given svg file into executable build123d/BuildLine code.

    Args:
        file_name (PathLike | str | bytes]): svg file name
        precision (int): # digits to round values to. Defaults to # digits in TOLERANCE

    Returns:
        tuple[str, str]: code, builder instance name
    """

    def fmt_value(value) -> str:
        if isinstance(value, complex):
            return f"({value.real:0.{precision}g}, {value.imag:0.{precision}g})"
        return f"{value:0.{precision}g}"

    def arc_to_code(curve: svgpathtools.Arc) -> str:
        center = curve.center
        start = curve.start
        end = curve.end
        x_radius = abs(curve.radius.real)
        y_radius = abs(curve.radius.imag)
        start_angle = float(curve.theta)
        arc_size = float(curve.delta)
        rotation = float(curve.rotation)

        if abs(x_radius - y_radius) <= TOLERANCE:
            return (
                "RadiusArc("
                f"({start.real:0.{precision}g}, {start.imag:0.{precision}g}), "
                f"({end.real:0.{precision}g}, {end.imag:0.{precision}g}), "
                f"{x_radius:0.{precision}g}, "
                f"{not curve.large_arc})"
            )

        return (
            "EllipticalCenterArc("
            f"({center.real:0.{precision}g}, {center.imag:0.{precision}g}), "
            f"{x_radius:0.{precision}g}, "
            f"{y_radius:0.{precision}g}, "
            f"start_angle={start_angle:0.{precision}g}, "
            f"arc_size={arc_size:0.{precision}g}, "
            f"rotation={rotation:0.{precision}g})"
        )

    translator = {
        "Line": ["Line", "start", "end"],
        "CubicBezier": ["Bezier", "start", "control1", "control2", "end"],
        "QuadraticBezier": ["Bezier", "start", "control", "end"],
    }
    file_name = fsdecode(file_name)
    paths, _path_attributes = svgpathtools.svg2paths(file_name)
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
                buildline_code.append(f"    {arc_to_code(curve)}")
                continue
            values = [curve.__dict__[parm] for parm in translator[class_name][1:]]
            values_str = ",".join(fmt_value(v) for v in values)
            buildline_code.append(f"    {translator[class_name][0]}({values_str})")

    return ("\n".join(buildline_code), builder_name)


@overload
def import_svg(
    svg_file: str | Path | TextIO,
    *,
    flip_y: bool = True,
    align: Align | tuple[Align, Align] | None = Align.MIN,
    ignore_visibility: bool = False,
    label_by: Literal["id", "class", "inkscape:label"] | str = "id",
) -> ShapeList[Wire | Face]: ...


@overload
@deprecated(
    "The 'is_inkscape_label' parameter is deprecated and will be removed in "
    "build123d 1.0. Use 'label_by=\"inkscape:label\"' instead."
)
def import_svg(
    svg_file: str | Path | TextIO,
    *,
    flip_y: bool = True,
    align: Align | tuple[Align, Align] | None = Align.MIN,
    ignore_visibility: bool = False,
    label_by: Literal["id", "class", "inkscape:label"] | str = "id",
    is_inkscape_label: bool | None = None,
) -> ShapeList[Wire | Face]: ...


def import_svg(
    svg_file: str | Path | TextIO,
    *,
    flip_y: bool = True,
    align: Align | tuple[Align, Align] | None = Align.MIN,
    ignore_visibility: bool = False,
    label_by: Literal["id", "class", "inkscape:label"] | str = "id",
    is_inkscape_label: bool | None = None,
) -> ShapeList[Wire | Face]:
    """import_svg

    Args:
        svg_file (Union[str, Path, TextIO]): svg file
        flip_y (bool, optional): flip objects to compensate for svg orientation. Defaults to True.
        align (Align | tuple[Align, Align] | None, optional): alignment of the SVG's viewbox,
            if None, the viewbox's origin will be at `(0,0,0)`. Defaults to Align.MIN.
        ignore_visibility (bool, optional): Defaults to False.
        label_by (str, optional): XML attribute to use for imported shapes' `label` property.
            Defaults to "id".
            Use `inkscape:label` to read labels set from Inkscape's "Layers and Objects" panel.

    Raises:
        ValueError: unexpected shape type

    Returns:
        ShapeList[Union[Wire, Face]]: objects contained in svg
    """
    if is_inkscape_label is not None:
        msg = "`is_inkscape_label` parameter is deprecated"
        if is_inkscape_label:
            label_by = "inkscape:" + label_by
            msg += f", use `label_by={label_by!r}` instead"
        warnings.warn(msg, stacklevel=2)

    shapes = []
    label_by = re.sub(
        r"^inkscape:(.+)", r"{http://www.inkscape.org/namespaces/inkscape}\1", label_by
    )
    imported = import_svg_document(
        svg_file,
        flip_y=flip_y,
        ignore_visibility=ignore_visibility,
        metadata=ColorAndLabel.Label_by(label_by),
    )

    doc_xy = Vector(imported.viewbox.x, imported.viewbox.y)
    doc_wh = Vector(imported.viewbox.width, imported.viewbox.height)
    offset = to_align_offset(doc_xy, doc_xy + doc_wh, align)

    for face_or_wire, color_and_label in imported:
        if isinstance(face_or_wire, TopoDS_Wire):
            shape = Wire(face_or_wire)
        elif isinstance(face_or_wire, TopoDS_Face):
            shape = Face(face_or_wire)
        else:  # should not happen
            raise ValueError(f"unexpected shape type: {type(face_or_wire).__name__}")

        if offset.X != 0 or offset.Y != 0:  # avoid copying if we don't need to
            shape = shape.translate(offset)

        if shape.wrapped:
            shape.color = Color(*color_and_label.color_for(shape.wrapped))
        shape.label = color_and_label.label
        shapes.append(shape)

    return ShapeList(shapes)
