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

import copy
import os
from math import degrees, sqrt
from pathlib import Path
from typing import TextIO, Union, Optional

import OCP.IFSelect
from OCP.BRep import BRep_Builder
from OCP.BRepGProp import BRepGProp
from OCP.BRepTools import BRepTools
from OCP.GProp import GProp_GProps
from OCP.Quantity import Quantity_ColorRGBA
from OCP.RWStl import RWStl
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.STEPControl import STEPControl_Reader
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
    XCAFDoc_DocumentTool,
)
from ocpsvg import ColorAndLabel, import_svg_document
import svgpathtools as svg
import unicodedata

from build123d.build_enums import CenterOf, Mode, AngularDirection
from build123d.build_line import BuildLine
from build123d.geometry import Color, Location
from build123d.objects_curve import Line, EllipticalCenterArc
from build123d.operations_generic import add, offset, mirror
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


def import_step(filename: str) -> Compound:
    """import_step

    Extract shapes from a STEP file and return them as a Compound object.

    Args:
        file_name (str): file path of STEP file to import

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

    def get_color(shape: TopoDS_Shape) -> Quantity_ColorRGBA:
        """Get the color - take that of the largest Face if multiple"""

        def get_col(obj: TopoDS_Shape) -> Quantity_ColorRGBA:
            col = Quantity_ColorRGBA()
            if (
                color_tool.GetColor(obj, XCAFDoc_ColorCurv, col)
                or color_tool.GetColor(obj, XCAFDoc_ColorGen, col)
                or color_tool.GetColor(obj, XCAFDoc_ColorSurf, col)
            ):
                return col

        shape_color = get_col(shape)

        colors = {}
        face_explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while face_explorer.More():
            current_face = face_explorer.Current()
            properties = GProp_GProps()
            BRepGProp.SurfaceProperties_s(current_face, properties)
            area = properties.Mass()
            color = get_col(current_face)
            if color is not None:
                colors[area] = color
            face_explorer.Next()

        # If there are multiple colors, return the one from the largest face
        if colors:
            shape_color = sorted(colors.items())[-1][1]

        return shape_color

    def build_assembly(parent_tdf_label: Optional[TDF_Label] = None) -> list[Shape]:
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

            sub_shape.color = Color(get_color(sub_topo_shape))
            sub_shape.label = get_name(ref_tdf_label)
            sub_shape.move(Location(shape_tool.GetLocation_s(sub_tdf_label)))

            sub_shapes.append(sub_shape)
        return sub_shapes

    if not os.path.exists(filename):
        raise FileNotFoundError(filename)

    fmt = TCollection_ExtendedString("XCAF")
    doc = TDocStd_Document(fmt)
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    reader.SetLayerMode(True)
    reader.ReadFile(filename)
    reader.Transfer(doc)

    root = Compound()
    root.for_construction = None
    root.children = build_assembly()
    # Remove empty Compound wrapper if single free object
    if len(root.children) == 1:
        root = root.children[0]

    return root


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
    paths_info = svg.svg2paths(file_name)
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


def import_svg_as_forced_outline(
    svg_file: Union[str, Path, TextIO],
    reorient: bool = True,
    tolerance: float = 0.01,
    extra_cleaning=False,
) -> Wire:
    """Import an SVG and apply cleaning operations to return a closed wire outline, if possible. Useful for SVG outlines that are actually made of thin shapes or slightly disconnected paths. May fail on more complex shapes.

    * Removes duplicate lines, including ones that are reverses of the other, within a tolerance level (useful for 'outlines' that are actually very thin shapes)
    * Sorts paths such that they are end to start in order of distance, flipping them if needed to line up start to end
    * Goes through each path and creates the next one such that it starts at the end of the last one
    * Ensures the last and first paths are connected


    Args:
        svg_file (Union[str, Path, TextIO]): svg file
        reorient (bool, optional): Center result on origin by bounding box, and
        flip objects to compensate for svg orientation (so the resulting wire
        is the same way up as it looks when opened in an SVG viewer). Defaults
        to True.
        tolerance (float, optional): Amount of tolerance to use for comparing paths. Defaults to 0.01.
        extra_clean (bool, optional): Do some extra cleaning, mainly skipping tiny paths. Defaults to False.

    Raises:
        ValueError: If an unknown path type is encountered.
        FileNotFoundError: the input file cannot be found.

    Returns:
        Wire: Forcefully connected SVG paths as a wire.
    """

    def point(path_point):
        return (path_point.real, path_point.imag)

    paths = svg.svg2paths(svg_file)[0]
    curves = []
    for p in paths:
        curves.extend(p)
    curves = _remove_duplicate_paths(curves, tolerance=tolerance)
    curves = _sort_curves(curves)
    first_line = curves[0]
    with BuildLine() as bd_l:
        line_start = point(first_line.start)
        for i, p in enumerate(curves):
            if extra_cleaning and p.length() < tolerance:
                # Filter out tiny edges that may cause issues with OCCT ops
                continue
            line_end = point(p.end)
            if i == len(curves) - 1:
                # Forcefully reconnect the end to the start.
                # Note: This won't quite work if the last path is an arc,
                # but make_face should still sort it out. Once
                # EllipticalStartArc is released in build123d, this can be
                # fixed.
                line_end = point(first_line.start)
            else:
                if (
                    extra_cleaning
                    and Vertex(line_end).distance(Vertex(line_start)) < tolerance
                ):
                    # Skip this path if it's really short, just go straight
                    # to the next one.
                    continue
            if isinstance(p, svg.Line):
                edge = Line(line_start, line_end)
            elif isinstance(p, svg.Arc):
                start, end = sorted(
                    [
                        p.theta,
                        p.theta + p.delta,
                    ]
                )
                if p.delta < 0.0:
                    dir_ = AngularDirection.CLOCKWISE
                else:
                    dir_ = AngularDirection.COUNTER_CLOCKWISE
                edge = EllipticalCenterArc(
                    center=point(p.center),
                    x_radius=p.radius.real,
                    y_radius=p.radius.imag,
                    start_angle=start,
                    end_angle=end,
                    rotation=degrees(p.phi),
                    angular_direction=dir_,
                    mode=Mode.PRIVATE,
                )
                add(edge.move(Location(line_start - edge @ 0)))

            else:
                print("Unknown path type for ", p)
                raise ValueError
            line_start = edge @ 1

    wire = bd_l.wire()
    if reorient:
        wire = wire.move(Location(-wire.center(center_of=CenterOf.BOUNDING_BOX)))
        wire = mirror(wire)

    return wire


def _sort_curves(curves):
    """Return list of paths sorted and flipped so that they are connected end to end as the list iterates."""
    if not curves:
        return []

    def euclidean_distance(p1, p2):
        return sqrt((p1.real - p2.real) ** 2 + (p1.imag - p2.imag) ** 2)

    # Start with the first curve
    sorted_curves = [curves.pop(0)]

    while curves:
        last_curve = sorted_curves[-1]
        last_end = last_curve.end

        # Find the closest curve to the previous end point.
        closest_curve, closest_distance, flip = None, float("inf"), False
        for curve in curves:
            dist_start = euclidean_distance(last_end, curve.start)
            dist_end = euclidean_distance(last_end, curve.end)
            # If end is closer than start, flip the curve right way around.
            if dist_start < closest_distance:
                closest_curve, closest_distance, flip = curve, dist_start, False
            if dist_end < closest_distance:
                closest_curve, closest_distance, flip = curve, dist_end, True

        # Flip the curve if necessary
        if flip:
            flipped = _reverse_svg_curve(closest_curve)
            sorted_curves.append(flipped)
        else:
            sorted_curves.append(closest_curve)
        curves.remove(closest_curve)

    return sorted_curves


def _remove_duplicate_paths(paths, tolerance=0.01):
    """Remove paths that are identical to within the given positional and
    parameter tolerance limit, including similar but reversed paths."""
    cleaned_paths = []

    for path in paths:
        # Check if a similar path already exists in the cleaned list (either
        # forward or reversed)
        flipped = _reverse_svg_curve(path)
        if any(
            _are_paths_similar(path, cleaned_path, tolerance)
            or _are_paths_similar(flipped, cleaned_path, tolerance)
            for cleaned_path in cleaned_paths
        ):
            # Skip this path if a similar one is already in the list
            continue
        cleaned_paths.append(path)

    return cleaned_paths


def _are_paths_similar(path1, path2, tolerance=0.01):
    """Compares two SVG paths, based on type, start/end points, length, and Arc attributes."""

    if type(path1) != type(path2):
        return False

    def lengths_are_close(p1, p2):
        return (
            abs(p1.length() - p2.length()) / max(p1.length(), p2.length()) < tolerance
        )

    if not lengths_are_close(path1, path2):
        return False

    def points_are_close(p1, p2):
        return abs(p1.real - p2.real) < tolerance and abs(p1.imag - p2.imag) < tolerance

    # Handle reversed paths by checking both normal and reversed orientation
    if not points_are_close(path1.start, path2.start) and points_are_close(
            path1.end, path2.end
        ):
        return False

    # Additional checks for arcs (to handle radius, rotation, etc.)
    if isinstance(path1, svg.Arc) and isinstance(path2, svg.Arc):
        arc_attributes = [
            "radius",
            "phi",
            "theta",
            "delta",
            "rotation",
            "center",
            "large_arc",
            "sweep",
        ]

        for attr in arc_attributes:
            try:
                if abs(vars(path1)[attr] - vars(path2)[attr]) > tolerance:
                    return False
            except KeyError:
                continue

    return True


def _reverse_svg_curve(c):
    c = copy.deepcopy(c)
    t = c.start
    c.start = c.end
    c.end = t
    if isinstance(c, svg.Arc):
        # Flipping ElipticalArcs is a bit more complicated.
        # Calculate the new theta as the original end angle.
        new_theta = c.theta + c.delta
        # Reverse the delta.
        c.delta = -c.delta
        # Set theta to the new start angle.
        c.theta = new_theta
    return c


if "__file__" in globals():
    script_dir = Path(__file__).parent
else:
    script_dir = Path(os.getcwd())


# For debugging/viewing in cq-editor or vscode's ocp_vscode plugin.
if __name__ not in ["__cq_main__", "temp"]:
    show_object = lambda *_, **__: None
    log = lambda x: print(x)
    # show_object = lambda *_, **__: None

    if __name__ == "__main__":
        import ocp_vscode as ocp
        from ocp_vscode import show

        ocp.set_port(3939)
        ocp.set_defaults(reset_camera=ocp.Camera.KEEP)
        show_object = lambda *args, **__: ocp.show(args)

p = Path(
    "~/src/keyboard_design/maizeless/pcb/build/maizeless-Edge_Cuts gerber.svg"
).expanduser()
# p = script_dir / "build/outline.svg"
# p = Path("~/src/keeb_snakeskin/manual_outlines/ferris-base-0.1.svg").expanduser()

import build123d as bd
base_face = bd.make_face(import_svg_as_forced_outline(p))
show_object(base_face, name="base_face")
