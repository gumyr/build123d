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

from enum import Enum

import OCP.TopAbs as ta
from anytree import PreOrderIter
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.IGESControl import IGESControl_Controller
from OCP.Interface import Interface_Static
from OCP.STEPCAFControl import STEPCAFControl_Controller, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_Controller, STEPControl_StepModelType
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopExp import TopExp_Explorer
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool
from OCP.XSControl import XSControl_WorkSession

from build123d import Compound, Curve, Part, Shape, Sketch, Unit


class PrecisionMode(Enum):
    """
    When you export a model to a STEP file, the precision of the geometric data
    (such as the coordinates of points, the definitions of curves and surfaces, etc.)
    can significantly impact the file size and the fidelity of the model when it is
    imported into another CAD system. Higher precision means that the geometric
    data is described with more detail, which can improve the accuracy of the model
    in the target system but can also increase the file size.
    """

    SESSION = 2
    GREATEST = 1
    AVERAGE = 0
    LEAST = -1

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


def export_step_with_color_label(
    to_export: Shape,
    path: str,
    unit: Unit = Unit.MM,
    write_pcurves: bool = True,
    precision_mode: PrecisionMode = PrecisionMode.AVERAGE,
) -> bool:
    """export_step

    Export a build123d Shape or assembly with color and label attributes.
    Note that if the color of a node in an assembly isn't set, it will be
    assigned the color of its nearest ancestor.

    Args:
        to_export (Shape): object or assembly
        path (str): step file path
        unit (Unit, optional): shape units. Defaults to Unit.MM.
        write_pcurves (bool, optional): write parametric curves to the STEP file.
            Defaults to True.
        precision_mode (bool, optional): geometric data precision.
            Defaults to PrecisionMode.AVERAGE.

    Raises:
        RuntimeError: Unknown Compound type

    Returns:
        bool: success
    """
    # Create the XCAF document
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))

    # Initialize the XCAF application
    application = XCAFApp_Application.GetApplication_s()

    # Create and initialize a new document
    application.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    application.InitDocument(doc)

    # Set units
    UNITS_PER_METER = {
        Unit.IN: 100 / 2.54,
        Unit.FT: 100 / (12 * 2.54),
        Unit.MC: 1_000_000,
        Unit.MM: 1000,
        Unit.CM: 100,
        Unit.M: 1,
    }
    XCAFDoc_DocumentTool.SetLengthUnit_s(doc, 1 / UNITS_PER_METER[unit])

    # Get the tools for handling shapes & colors section of the XCAF document.
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    # Add all the shapes in the b3d object either as a single object or assembly
    is_assembly = isinstance(to_export, Compound) and len(to_export.children) > 0
    root_label = shape_tool.AddShape(to_export.wrapped, is_assembly)

    # Add names and color info
    node: Shape
    for node in PreOrderIter(to_export):
        if not node.label and node.color is None:
            continue  # skip if there is nothing to set

        node_label: TDF_Label = shape_tool.FindShape(node.wrapped, findInstance=False)

        # For Part, Sketch and Curve objects color needs to be applied to the wrapped
        # object not just the Compound wrapper
        sub_node_labels = []
        if isinstance(node, Compound) and not node.children:
            sub_nodes = []
            if isinstance(node, Part):
                explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_SOLID)
            elif isinstance(node, Sketch):
                explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_FACE)
            elif isinstance(node, Curve):
                explorer = TopExp_Explorer(node.wrapped, ta.TopAbs_EDGE)
            else:
                raise RuntimeError("Unknown Compound type")

            while explorer.More():
                current_shape = explorer.Current()
                sub_nodes.append(current_shape)
                explorer.Next()

            sub_node_labels = [
                shape_tool.FindShape(sub_node, findInstance=False)
                for sub_node in sub_nodes
            ]
        if node.label:
            TDataStd_Name.Set_s(node_label, TCollection_ExtendedString(node.label))

        # Find the correct color for this node
        if node.color is None:
            # Find parent color
            current_node = node
            while current_node is not None:
                parent_color = current_node.color
                if parent_color is not None:
                    break
                current_node = current_node.parent
            node_color = parent_color
        else:
            node_color = node.color

        if node_color is not None:
            for label in [node_label] + sub_node_labels:
                color_tool.SetColor(
                    label, node_color.wrapped, XCAFDoc_ColorType.XCAFDoc_ColorSurf
                )

    shape_tool.UpdateAssemblies()
    # print(f"Is document valid: {XCAFDoc_DocumentTool.IsXCAFDocument_s(doc)}")

    session = XSControl_WorkSession()
    writer = STEPCAFControl_Writer(session, False)
    writer.SetColorMode(True)
    writer.SetLayerMode(True)
    writer.SetNameMode(True)

    # APIHeaderSection doesn't seem to be supported by OCP - TBD
    # APIHeaderSection_MakeHeader makeHeader(writer.Writer().Model())

    # Handle(TCollection_HAsciiString) headerFileName = new TCollection_HAsciiString("filename");
    # Handle(TCollection_HAsciiString) headerAuthor = new TCollection_HAsciiString("Volker");
    # Handle(TCollection_HAsciiString) headerOrganization = new TCollection_HAsciiString("myCompanyName");
    # Handle(TCollection_HAsciiString) headerOriginatingSystem = new TCollection_HAsciiString("myApplicationName");
    # Handle(TCollection_HAsciiString) fileDescription = new TCollection_HAsciiString("myApplication Model");

    # makeHeader.SetName(TCollection_HAsciiString(path))
    # makeHeader.SetAuthorValue (1, headerAuthor);
    # makeHeader.SetOrganizationValue (1, headerOrganization);
    # makeHeader.SetOriginatingSystem(headerOriginatingSystem);
    # makeHeader.SetDescriptionValue(1, fileDescription);

    STEPCAFControl_Controller.Init_s()
    STEPControl_Controller.Init_s()
    IGESControl_Controller.Init_s()
    Interface_Static.SetIVal_s("write.surfacecurve.mode", int(write_pcurves))
    Interface_Static.SetIVal_s("write.precision.mode", precision_mode.value)
    writer.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)

    status = writer.Write(path)

    return status == IFSelect_ReturnStatus.IFSelect_RetDone
