"""
build123d 3D Exporters

name: exporters3d.py
by:   Gumyr
date: March 6th, 2024

desc:
    Exporters for 3D models such as STEP.

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

# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error

from datetime import datetime
import warnings
from io import BytesIO
from os import PathLike, fsdecode, fspath
from typing import BinaryIO, cast

import OCP.TopAbs as ta
from anytree import PreOrderIter
from OCP.APIHeaderSection import APIHeaderSection_MakeHeader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.IGESControl import IGESControl_Controller
from OCP.Interface import Interface_Static
from OCP.Message import Message, Message_Gravity, Message_ProgressRange
from OCP.RWGltf import RWGltf_CafWriter
from OCP.STEPCAFControl import STEPCAFControl_Controller, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_Controller, STEPControl_StepModelType
from OCP.StlAPI import StlAPI_Writer
from OCP.TCollection import (
    TCollection_AsciiString,
    TCollection_ExtendedString,
    TCollection_HAsciiString,
)
from OCP.TColStd import TColStd_IndexedDataMapOfStringString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopExp import TopExp_Explorer
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.XSControl import XSControl_WorkSession

from build123d.build_common import UNITS_PER_METER
from build123d.build_enums import PrecisionMode, Unit
from build123d.geometry import Location
from build123d.topology import Compound, Curve, Part, Shape, Sketch


def _create_xde(
    to_export: Shape, unit: Unit = Unit.MM, auto_naming: bool = False
) -> TDocStd_Document:
    """create_xde

    An OpenCASCADE Technology (OCCT) XDE (eXtended Data Exchange) document is a
    sophisticated framework designed for comprehensive CAD data management,
    facilitating not just the geometric modeling of shapes but also the handling
    of associated metadata, such as material properties, color, layering, and
    annotations. This integrated environment supports the organization and
    manipulation of complex assemblies and parts, enabling users to navigate,
    edit, and query both the structure and attributes of CAD models. XDE's
    architecture is particularly beneficial for applications requiring detailed
    interoperability between different CAD systems, offering robust tools for
    data exchange, visualization, and modification while preserving the integrity
    and attributes of the CAD data across various stages of product development.

    Args:
        to_export (Shape): object or assembly
        unit (Unit, optional): shape units. Defaults to Unit.MM.
        auto_naming (bool, optional): whether to use ShapeTool AutoNaming.
            Defaults to False.

    Returns:
        TDocStd_Document: XDE document
    """
    # Create the XCAF document
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))

    # Initialize the XCAF application
    application = XCAFApp_Application.GetApplication_s()

    # Create and initialize a new document
    application.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    application.InitDocument(doc)

    XCAFDoc_DocumentTool.SetLengthUnit_s(doc, 1 / UNITS_PER_METER[unit])

    # Get the tools for handling shapes & colors section of the XCAF document.
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    # Auto Naming names shapes and links. Enabling it for glTF's prevents user defined
    # labels from ending up on nodes which is undesirable. Enabling it for STEP files
    # does not seem to affect user labels.
    shape_tool.SetAutoNaming_s(auto_naming)

    # Create a label map to find the appropriate label for all shapes
    label_map: dict[Shape, TDF_Label] = {}

    def resolve_component_parent_label(label: TDF_Label) -> TDF_Label:
        """Return a label suitable for assembly operations.

        If `label` is a reference/component label, this resolves and returns
        the referred shape label. Otherwise returns `label` unchanged.
        Null labels are returned as-is.
        """
        if label.IsNull():
            return label
        if XCAFDoc_ShapeTool.IsReference_s(label):
            referred = TDF_Label()
            if (
                XCAFDoc_ShapeTool.GetReferredShape_s(label, referred)
                and not referred.IsNull()
            ):
                return referred
        return label

    def set_name_and_color(node: Shape, node_label: TDF_Label) -> None:
        """Assign label/color metadata for one XDE node label.

        Behavior:
        - Sets `TDataStd_Name` on the instance label and, when applicable,
          also on the referred shape label so STEP PRODUCT names persist.
        - Sets generic color on the instance label and referred label.
        - For leaf `Compound` wrappers (`Part`, `Sketch`, `Curve`), propagates
          color to relevant sub-shapes (solid/face/edge) using appropriate
          XCAF color channels.
        """
        if node_label.IsNull():
            return

        if node.label:
            TDataStd_Name.Set_s(node_label, TCollection_ExtendedString(node.label))
            if XCAFDoc_ShapeTool.IsReference_s(node_label):
                referred = TDF_Label()
                if (
                    XCAFDoc_ShapeTool.GetReferredShape_s(node_label, referred)
                    and not referred.IsNull()
                ):
                    TDataStd_Name.Set_s(
                        referred, TCollection_ExtendedString(node.label)
                    )

        if node.color is not None:
            node_color_type = XCAFDoc_ColorType.XCAFDoc_ColorGen
            color_tool.SetColor(node_label, node.color.wrapped, node_color_type)

            if XCAFDoc_ShapeTool.IsReference_s(node_label):
                referred = TDF_Label()
                if (
                    XCAFDoc_ShapeTool.GetReferredShape_s(node_label, referred)
                    and not referred.IsNull()
                ):
                    color_tool.SetColor(referred, node.color.wrapped, node_color_type)

            # Sub-shape color handling for leaf Compound wrappers
            if isinstance(node, Compound) and not node.children:
                if isinstance(node, Part):
                    explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_SOLID)
                    sub_color_type = XCAFDoc_ColorType.XCAFDoc_ColorSurf
                elif isinstance(node, Sketch):
                    explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_FACE)
                    sub_color_type = XCAFDoc_ColorType.XCAFDoc_ColorSurf
                elif isinstance(node, Curve):
                    explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_EDGE)
                    sub_color_type = XCAFDoc_ColorType.XCAFDoc_ColorCurv
                else:
                    explorer = TopExp_Explorer()
                    sub_color_type = XCAFDoc_ColorType.XCAFDoc_ColorGen

                shape_label_for_sub = resolve_component_parent_label(node_label)
                while explorer.More():
                    sub_node = explorer.Current()
                    sub_label = shape_tool.AddSubShape(shape_label_for_sub, sub_node)
                    if not sub_label.IsNull():
                        color_tool.SetColor(
                            sub_label, node.color.wrapped, sub_color_type
                        )
                    explorer.Next()

    # Single preorder pass: parent labels are created before children, so we can
    # build label_map and assign metadata without a second traversal.
    for node in PreOrderIter(to_export):
        if node.wrapped is None:
            continue

        parent = getattr(node, "parent", None)
        if parent is None:
            node_label = shape_tool.AddShape(node.wrapped, False)
        else:
            parent_label = label_map.get(parent, TDF_Label())
            parent_label = resolve_component_parent_label(parent_label)
            if parent_label.IsNull():
                continue
            node_label = shape_tool.AddComponent(parent_label, node.wrapped)

        if node_label.IsNull():
            continue

        label_map[node] = node_label
        if node.label or node.color is not None:
            set_name_and_color(node, node_label)

    shape_tool.UpdateAssemblies()

    # print(f"Is document valid: {XCAFDoc_DocumentTool.IsXCAFDocument_s(doc)}")

    return doc


def export_brep(
    to_export: Shape,
    file_path: PathLike | str | bytes | BytesIO | BinaryIO,
) -> bool:
    """Export this shape to a BREP file

    Args:
        to_export (Shape): object or assembly
        file_path: Union[PathLike, str, bytes, BytesIO]: brep file path or memory buffer

    Returns:
        bool: write status
    """
    if isinstance(file_path, (PathLike | str | bytes)):
        file_path = fsdecode(file_path)
    else:
        file_path = cast(BytesIO, file_path)
    return_value = BRepTools.Write_s(to_export.wrapped, file_path)

    return True if return_value is None else return_value


def export_gltf(
    to_export: Shape,
    file_path: PathLike | str | bytes,
    unit: Unit = Unit.MM,
    binary: bool = False,
    linear_deflection: float = 0.001,
    angular_deflection: float = 0.1,
) -> bool:
    """export_gltf

    The glTF (GL Transmission Format) specification primarily focuses on the efficient
    transmission and loading of 3D models as a compact, binary format that is directly
    renderable by graphics APIs like WebGL, OpenGL, and Vulkan. It's designed to store
    detailed 3D model data, including meshes (vertices, normals, textures, etc.),
    animations, materials, and scene hierarchy, among other aspects.

    Args:
        to_export (Shape): object or assembly
        file_path (Union[PathLike, str, bytes]): glTF file path
        unit (Unit, optional): shape units. Defaults to Unit.MM.
        binary (bool, optional): output format. Defaults to False.
        linear_deflection (float, optional): A linear deflection setting which limits
            the distance between a curve and its tessellation. Setting this value too
            low will result in large meshes that can consume computing resources. Setting
            the value too high can result in meshes with a level of detail that is too
            low. The default is a good starting point for a range of cases.
            Defaults to 1e-3.
        angular_deflection (float, optional): Angular deflection setting which limits
            the angle between subsequent segments in a polyline. Defaults to 0.1.

    Raises:
        RuntimeError: Failed to write glTF file

    Returns:
        bool: write status
    """

    # Map from OCCT's right-handed +Z up coordinate system to glTF's right-handed +Y
    # up coordinate system
    # https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units
    if to_export.location is None:
        raise ValueError("Shape must have a location to export to glTF")
    original_location = to_export.location
    to_export.location *= Location((0, 0, 0), (1, 0, 0), -90)

    # Tessellate the object(s)
    node: Shape
    for node in PreOrderIter(to_export):
        if node.wrapped is not None:
            node.mesh(linear_deflection, angular_deflection)

    # Create the XCAF document
    doc: TDocStd_Document = _create_xde(to_export, unit, auto_naming=False)

    # Write the glTF file
    writer = RWGltf_CafWriter(
        theFile=TCollection_AsciiString(fsdecode(file_path)), theIsBinary=binary
    )
    writer.SetParallel(True)
    index_map = TColStd_IndexedDataMapOfStringString()
    progress = Message_ProgressRange()

    messenger = Message.DefaultMessenger_s()
    for printer in messenger.Printers():
        printer.SetTraceLevel(Message_Gravity.Message_Fail)

    status = writer.Perform(doc, index_map, progress)

    # Reset tessellation
    BRepTools.Clean_s(to_export.wrapped)

    # Reset original orientation
    to_export.location = original_location

    # if not status:
    #     raise RuntimeError("Failed to write glTF file")

    return status


def export_step(
    to_export: Shape,
    file_path: PathLike | str | bytes | BytesIO | BinaryIO,
    unit: Unit = Unit.MM,
    write_pcurves: bool = True,
    precision_mode: PrecisionMode = PrecisionMode.AVERAGE,
    *,  # Too many positional arguments
    timestamp: str | datetime | None = None,
) -> bool:
    """export_step

    Export a build123d Shape or assembly with color and label attributes.
    Note that if the color of a node in an assembly isn't set, it will be
    assigned the color of its nearest ancestor.

    Args:
        to_export (Shape): object or assembly
        file_path (Union[PathLike, str, bytes, BytesIO]): step file path
        unit (Unit, optional): shape units. Defaults to Unit.MM.
        write_pcurves (bool, optional): write parametric curves to the STEP file.
            Defaults to True.
        precision_mode (PrecisionMode, optional): geometric data precision.
            Defaults to PrecisionMode.AVERAGE.

    Raises:
        RuntimeError: Unknown Compound type

    Returns:
        bool: success
    """

    # Create the XCAF document
    doc = _create_xde(to_export, unit, auto_naming=True)

    # Disable writing OCCT info to console
    messenger = Message.DefaultMessenger_s()
    for printer in messenger.Printers():
        printer.SetTraceLevel(Message_Gravity.Message_Fail)

    session = XSControl_WorkSession()
    writer = STEPCAFControl_Writer(session, False)
    writer.SetColorMode(True)
    writer.SetLayerMode(True)
    writer.SetNameMode(True)

    header = APIHeaderSection_MakeHeader(writer.Writer().Model())

    if not header.IsDone():  # As in OCCT 7.9.x
        # Create an empty consistent header, i.e. IsDone() return True
        header = APIHeaderSection_MakeHeader(0)
        header.Apply(writer.Writer().Model())

    if to_export.label:
        header.SetName(TCollection_HAsciiString(to_export.label))
    if timestamp is not None:
        if isinstance(timestamp, datetime):
            header.SetTimeStamp(TCollection_HAsciiString(timestamp.isoformat()))
        else:
            header.SetTimeStamp(TCollection_HAsciiString(timestamp))
    # consider using e.g. the non *Value versions instead
    # header.SetAuthorValue(1, TCollection_HAsciiString("Volker"));
    # header.SetOrganizationValue(1, TCollection_HAsciiString("myCompanyName"));
    header.SetOriginatingSystem(TCollection_HAsciiString("build123d"))
    # header.SetDescriptionValue(1, TCollection_HAsciiString("myApplication Model"));

    STEPCAFControl_Controller.Init_s()
    STEPControl_Controller.Init_s()
    IGESControl_Controller.Init_s()
    Interface_Static.SetIVal_s("write.surfacecurve.mode", int(write_pcurves))
    Interface_Static.SetIVal_s("write.precision.mode", precision_mode.value)
    writer.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)

    if isinstance(file_path, (PathLike, str, bytes)):
        status = writer.Write(fsdecode(file_path))
    else:
        # need to cast for type checker because BinaryIO is OK but OCP doesn't know
        status = writer.WriteStream(cast(BytesIO, file_path))

    success = status == IFSelect_ReturnStatus.IFSelect_RetDone
    if not success:
        raise RuntimeError("Failed to write STEP file")

    return success


def export_stl(
    to_export: Shape,
    file_path: PathLike | str | bytes,
    tolerance: float = 1e-3,
    angular_tolerance: float = 0.1,
    ascii_format: bool = False,
) -> bool:
    """Export STL

    Exports a shape to a specified STL file.

    Args:
        to_export (Shape): object or assembly
        file_path (Union[PathLike, str, bytes]): The path and file name to write the STL output to.
        tolerance (float, optional): A linear deflection setting which limits the distance
            between a curve and its tessellation. Setting this value too low will result in
            large meshes that can consume computing resources. Setting the value too high can
            result in meshes with a level of detail that is too low. The default is a good
            starting point for a range of cases. Defaults to 1e-3.
        angular_tolerance (float, optional): Angular deflection setting which limits the angle
            between subsequent segments in a polyline. Defaults to 0.1.
        ascii_format (bool, optional): Export the file as ASCII (True) or binary (False)
            STL format. Defaults to False (binary).

    Returns:
        bool: Success
    """
    mesh = BRepMesh_IncrementalMesh(
        to_export.wrapped, tolerance, True, angular_tolerance, True
    )
    mesh.Perform()

    writer = StlAPI_Writer()

    writer.ASCIIMode = ascii_format
    return writer.Write(to_export.wrapped, fsdecode(file_path))
