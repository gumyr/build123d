"""
build123d exporters

name: exporters.py
by:   JRMobley
date: March 19th, 2023

desc:
    This python module contains exporters for SVG and DXF file formats.

license:

    Copyright 2023 JRMobley

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
# pylint: disable=too-many-lines

import math
import xml.etree.ElementTree as ET
from enum import Enum, auto
from typing import Callable, Iterable, Optional, Union, List, Tuple
from copy import copy

import ezdxf
import svgpathtools as PT
from ezdxf import zoom
from ezdxf.colors import RGB, aci2rgb
from ezdxf.math import Vec2
from OCP.BRepLib import BRepLib  # type: ignore
from OCP.BRepTools import BRepTools_WireExplorer  # type: ignore
from OCP.Geom import Geom_BezierCurve  # type: ignore
from OCP.GeomConvert import GeomConvert  # type: ignore
from OCP.GeomConvert import GeomConvert_BSplineCurveToBezierCurve  # type: ignore
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec, gp_XYZ  # type: ignore
from OCP.HLRAlgo import HLRAlgo_Projector  # type: ignore
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape  # type: ignore
from OCP.TopAbs import TopAbs_Orientation, TopAbs_ShapeEnum  # type: ignore
from OCP.TopExp import TopExp_Explorer  # type: ignore
from typing_extensions import Self

from build123d.build_enums import Unit
from build123d.geometry import TOLERANCE, Color
from build123d.topology import (
    BoundBox,
    Compound,
    Edge,
    Wire,
    GeomType,
    Shape,
    Vector,
    VectorLike,
)
from build123d.build_common import UNITS_PER_METER

PathSegment = Union[PT.Line, PT.Arc, PT.QuadraticBezier, PT.CubicBezier]

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class Drawing:
    """A base drawing object"""

    def __init__(
        self,
        shape: Shape,
        *,
        look_at: VectorLike = None,
        look_from: VectorLike = (1, -1, 1),
        look_up: VectorLike = (0, 0, 1),
        with_hidden: bool = True,
        focus: Union[float, None] = None,
    ):
        # pylint: disable=too-many-locals
        hlr = HLRBRep_Algo()
        hlr.Add(shape.wrapped)

        projection_origin = Vector(look_at) if look_at else shape.center()
        projection_dir = Vector(look_from).normalized()
        projection_x = Vector(look_up).normalized().cross(projection_dir)
        coordinate_system = gp_Ax2(
            projection_origin.to_pnt(), projection_dir.to_dir(), projection_x.to_dir()
        )

        if focus is not None:
            projector = HLRAlgo_Projector(coordinate_system, focus)
        else:
            projector = HLRAlgo_Projector(coordinate_system)

        hlr.Projector(projector)
        hlr.Update()
        hlr.Hide()

        hlr_shapes = HLRBRep_HLRToShape(hlr)

        visible = []

        visible_sharp_edges = hlr_shapes.VCompound()
        if not visible_sharp_edges.IsNull():
            visible.append(visible_sharp_edges)

        visible_smooth_edges = hlr_shapes.Rg1LineVCompound()
        if not visible_smooth_edges.IsNull():
            visible.append(visible_smooth_edges)

        visible_contour_edges = hlr_shapes.OutLineVCompound()
        if not visible_contour_edges.IsNull():
            visible.append(visible_contour_edges)

        hidden = []
        if with_hidden:
            hidden_sharp_edges = hlr_shapes.HCompound()
            if not hidden_sharp_edges.IsNull():
                hidden.append(hidden_sharp_edges)

            hidden_contour_edges = hlr_shapes.OutLineHCompound()
            if not hidden_contour_edges.IsNull():
                hidden.append(hidden_contour_edges)

        # Fix the underlying geometry - otherwise we will get segfaults
        for el in visible:
            BRepLib.BuildCurves3d_s(el, TOLERANCE)
        for el in hidden:
            BRepLib.BuildCurves3d_s(el, TOLERANCE)

        # Convert and store the results.
        self.visible_lines = Compound(map(Shape, visible))
        self.hidden_lines = Compound(map(Shape, hidden))


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class AutoNameEnum(Enum):
    """An enum class that automatically sets members' value to their name."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name


class LineType(AutoNameEnum):
    """Line Types"""

    CONTINUOUS = auto()

    BORDER = auto()
    BORDER2 = auto()
    BORDERX2 = auto()
    CENTER = auto()
    CENTER2 = auto()
    CENTERX2 = auto()
    DASHDOT = auto()
    DASHDOT2 = auto()
    DASHDOTX2 = auto()
    DASHED = auto()
    DASHED2 = auto()
    DASHEDX2 = auto()
    DIVIDE = auto()
    DIVIDE2 = auto()
    DIVIDEX2 = auto()
    DOT = auto()
    DOT2 = auto()
    DOTX2 = auto()
    HIDDEN = auto()
    HIDDEN2 = auto()
    HIDDENX2 = auto()
    PHANTOM = auto()
    PHANTOM2 = auto()
    PHANTOMX2 = auto()

    ISO_DASH = "ACAD_ISO02W100"  # __ __ __ __ __ __ __ __ __ __ __ __ __
    ISO_DASH_SPACE = "ACAD_ISO03W100"  # __    __    __    __    __    __
    ISO_LONG_DASH_DOT = "ACAD_ISO04W100"  # ____ . ____ . ____ . ____ . _
    ISO_LONG_DASH_DOUBLE_DOT = "ACAD_ISO05W100"  # ____ .. ____ .. ____ .
    ISO_LONG_DASH_TRIPLE_DOT = "ACAD_ISO06W100"  # ____ ... ____ ... ____
    ISO_DOT = "ACAD_ISO07W100"  # . . . . . . . . . . . . . . . . . . . .
    ISO_LONG_DASH_SHORT_DASH = "ACAD_ISO08W100"  # ____ __ ____ __ ____ _
    ISO_LONG_DASH_DOUBLE_SHORT_DASH = "ACAD_ISO09W100"  # ____ __ __ ____
    ISO_DASH_DOT = "ACAD_ISO10W100"  # __ . __ . __ . __ . __ . __ . __ .
    ISO_DOUBLE_DASH_DOT = "ACAD_ISO11W100"  # __ __ . __ __ . __ __ . __ _
    ISO_DASH_DOUBLE_DOT = "ACAD_ISO12W100"  # __ . . __ . . __ . . __ . .
    ISO_DOUBLE_DASH_DOUBLE_DOT = "ACAD_ISO13W100"  # __ __ . . __ __ . . _
    ISO_DASH_TRIPLE_DOT = "ACAD_ISO14W100"  # __ . . . __ . . . __ . . . _
    ISO_DOUBLE_DASH_TRIPLE_DOT = "ACAD_ISO15W100"  # __ __ . . . __ __ . .


class ColorIndex(Enum):
    """Colors"""

    RED = 1
    YELLOW = 2
    GREEN = 3
    CYAN = 4
    BLUE = 5
    MAGENTA = 6
    BLACK = 7
    GRAY = 8
    LIGHT_GRAY = 9


class DotLength(Enum):
    """Line type dash pattern dot widths, expressed in tenths of an inch."""

    TRUE_DOT = 0.0
    """A true, circular dot which renders properly in web browsers."""

    INKSCAPE_COMPAT = 0.01
    """A very, very short segment which will render in Inkscape but still
    look like a circle."""

    QCAD_IMPERIAL = 0.2
    """A visibly elongated dot which will match QCAD rendering of
    documents that use the imperial measurement system."""


def ansi_pattern(*args):
    """Prepare an ANSI line pattern for ezdxf usage.
    Input pattern is specified in inches.
    Output is given in tenths of an inch, and the total pattern length
    is prepended to the list."""
    abs_args = [abs(l) for l in args]
    result = [(l * 10) for l in [sum(abs_args), *args]]
    return result


def iso_pattern(*args):
    """Prepare an ISO line pattern for ezdxf usage.
    Input pattern is specified in millimeters.
    Output is given in tenths of an inch, and the total pattern length
    is prepended to the list."""
    abs_args = [abs(l) for l in args]
    result = [(l / 2.54) for l in [sum(abs_args), *args]]
    return result


def unit_conversion_scale(from_unit: Unit, to_unit: Unit) -> float:
    """Return the multiplicative conversion factor to go from from_unit to to_unit."""
    result = UNITS_PER_METER[to_unit] / UNITS_PER_METER[from_unit]
    return result


# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------


class Export2D:
    """Base class for 2D exporters (DXF, SVG)."""

    # When specifying a parametric interval [u1, u2] on a spline,
    # OCCT considers two parameters to be equal if
    # abs(u1-u2) < tolerance, and generally raises an exception in
    # this case.
    PARAMETRIC_TOLERANCE = 1e-9

    DEFAULT_COLOR_INDEX = ColorIndex.BLACK
    DEFAULT_LINE_WEIGHT = 0.09
    DEFAULT_LINE_TYPE = LineType.CONTINUOUS

    # Define the line types.
    LINETYPE_DEFS = {
        LineType.CONTINUOUS.value: ("Solid", [0.0]),
        LineType.BORDER.value: (
            "Border __ __ . __ __ . __ __ . __ __ . __ __ .",
            ansi_pattern(0.5, -0.25, 0.5, -0.25, 0, -0.25),
        ),
        LineType.BORDER2.value: (
            "Border (.5x) __.__.__.__.__.__.__.__.__.__.__.",
            ansi_pattern(0.25, -0.125, 0.25, -0.125, 0, -0.125),
        ),
        LineType.BORDERX2.value: (
            "Border (2x) ____  ____  .  ____  ____  .  ___",
            ansi_pattern(1.0, -0.5, 1.0, -0.5, 0, -0.5),
        ),
        LineType.CENTER.value: (
            "Center ____ _ ____ _ ____ _ ____ _ ____ _ ____",
            ansi_pattern(1.25, -0.25, 0.25, -0.25),
        ),
        LineType.CENTER2.value: (
            "Center (.5x) ___ _ ___ _ ___ _ ___ _ ___ _ ___",
            ansi_pattern(0.75, -0.125, 0.125, -0.125),
        ),
        LineType.CENTERX2.value: (
            "Center (2x) ________  __  ________  __  _____",
            ansi_pattern(2.5, -0.5, 0.5, -0.5),
        ),
        LineType.DASHDOT.value: (
            "Dash dot __ . __ . __ . __ . __ . __ . __ . __",
            ansi_pattern(0.5, -0.25, 0, -0.25),
        ),
        LineType.DASHDOT2.value: (
            "Dash dot (.5x) _._._._._._._._._._._._._._._.",
            ansi_pattern(0.25, -0.125, 0, -0.125),
        ),
        LineType.DASHDOTX2.value: (
            "Dash dot (2x) ____  .  ____  .  ____  .  ___",
            ansi_pattern(1.0, -0.5, 0, -0.5),
        ),
        LineType.DASHED.value: (
            "Dashed __ __ __ __ __ __ __ __ __ __ __ __ __ _",
            ansi_pattern(0.5, -0.25),
        ),
        LineType.DASHED2.value: (
            "Dashed (.5x) _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ",
            ansi_pattern(0.25, -0.125),
        ),
        LineType.DASHEDX2.value: (
            "Dashed (2x) ____  ____  ____  ____  ____  ___",
            ansi_pattern(1.0, -0.5),
        ),
        LineType.DIVIDE.value: (
            "Divide ____ . . ____ . . ____ . . ____ . . ____",
            ansi_pattern(0.5, -0.25, 0, -0.25, 0, -0.25),
        ),
        LineType.DIVIDE2.value: (
            "Divide (.5x) __..__..__..__..__..__..__..__.._",
            ansi_pattern(0.25, -0.125, 0, -0.125, 0, -0.125),
        ),
        LineType.DIVIDEX2.value: (
            "Divide (2x) ________  .  .  ________  .  .  _",
            ansi_pattern(1.0, -0.5, 0, -0.5, 0, -0.5),
        ),
        LineType.DOT.value: (
            "Dot . . . . . . . . . . . . . . . . . . . . . . . .",
            ansi_pattern(0, -0.25),
        ),
        LineType.DOT2.value: (
            "Dot (.5x) ........................................",
            ansi_pattern(0, -0.125),
        ),
        LineType.DOTX2.value: (
            "Dot (2x) .  .  .  .  .  .  .  .  .  .  .  .  .  .",
            ansi_pattern(0, -0.5),
        ),
        LineType.HIDDEN.value: (
            "Hidden __ __ __ __ __ __ __ __ __ __ __ __ __ __",
            ansi_pattern(0.25, -0.125),
        ),
        LineType.HIDDEN2.value: (
            "Hidden (.5x) _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ",
            ansi_pattern(0.125, -0.0625),
        ),
        LineType.HIDDENX2.value: (
            "Hidden (2x) ____ ____ ____ ____ ____ ____ ____ ",
            ansi_pattern(0.5, -0.25),
        ),
        LineType.PHANTOM.value: (
            "Phantom ______  __  __  ______  __  __  ______ ",
            ansi_pattern(1.25, -0.25, 0.25, -0.25, 0.25, -0.25),
        ),
        LineType.PHANTOM2.value: (
            "Phantom (.5x) ___ _ _ ___ _ _ ___ _ _ ___ _ _",
            ansi_pattern(0.625, -0.125, 0.125, -0.125, 0.125, -0.125),
        ),
        LineType.PHANTOMX2.value: (
            "Phantom (2x) ____________    ____    ____   _",
            ansi_pattern(2.5, -0.5, 0.5, -0.5, 0.5, -0.5),
        ),
        LineType.ISO_DASH.value: (
            "ISO dash __ __ __ __ __ __ __ __ __ __ __ __ __",
            iso_pattern(12, -3),
        ),
        LineType.ISO_DASH_SPACE.value: (
            "ISO dash space __    __    __    __    __    __",
            iso_pattern(12, -18),
        ),
        LineType.ISO_LONG_DASH_DOT.value: (
            "ISO long-dash dot ____ . ____ . ____ . ____ . _",
            iso_pattern(24, -3, 0, -3),
        ),
        LineType.ISO_LONG_DASH_DOUBLE_DOT.value: (
            "ISO long-dash double-dot ____ .. ____ .. ____ . ",
            iso_pattern(24, -3, 0, -3, 0, -3),
        ),
        LineType.ISO_LONG_DASH_TRIPLE_DOT.value: (
            "ISO long-dash triple-dot ____ ... ____ ... ____",
            iso_pattern(24, -3, 0, -3, 0, -3, 0, -3),
        ),
        LineType.ISO_DOT.value: (
            "ISO dot . . . . . . . . . . . . . . . . . . . . ",
            iso_pattern(0, -3),
        ),
        LineType.ISO_LONG_DASH_SHORT_DASH.value: (
            "ISO long-dash short-dash ____ __ ____ __ ____ _",
            iso_pattern(24, -3, 6, -3),
        ),
        LineType.ISO_LONG_DASH_DOUBLE_SHORT_DASH.value: (
            "ISO long-dash double-short-dash ____ __ __ ____",
            iso_pattern(24, -3, 6, -3, 6, -3),
        ),
        LineType.ISO_DASH_DOT.value: (
            "ISO dash dot __ . __ . __ . __ . __ . __ . __ . ",
            iso_pattern(12, -3, 0, -3),
        ),
        LineType.ISO_DOUBLE_DASH_DOT.value: (
            "ISO double-dash dot __ __ . __ __ . __ __ . __ _",
            iso_pattern(12, -3, 12, -3, 0, -3),
        ),
        LineType.ISO_DASH_DOUBLE_DOT.value: (
            "ISO dash double-dot __ . . __ . . __ . . __ . . ",
            iso_pattern(12, -3, 0, -3, 0, -3),
        ),
        LineType.ISO_DOUBLE_DASH_DOUBLE_DOT.value: (
            "ISO double-dash double-dot __ __ . . __ __ . . _",
            iso_pattern(12, -3, 12, -3, 0, -3, 0, -3),
        ),
        LineType.ISO_DASH_TRIPLE_DOT.value: (
            "ISO dash triple-dot __ . . . __ . . . __ . . . _",
            iso_pattern(12, -3, 0, -3, 0, -3, 0, -3),
        ),
        LineType.ISO_DOUBLE_DASH_TRIPLE_DOT.value: (
            "ISO double-dash triple-dot __ __ . . . __ __ . .",
            iso_pattern(12, -3, 12, -3, 0, -3, 0, -3, 0, -3),
        ),
    }

    # Scale factor to convert from linetype units (1/10 inch).
    LTYPE_SCALE = {
        Unit.IN: 0.1,
        Unit.FT: 0.1 / 12,
        Unit.MM: 2.54,
        Unit.CM: 0.254,
        Unit.M: 0.00254,
    }


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class ExportDXF(Export2D):
    """
    The ExportDXF class provides functionality for exporting 2D shapes to DXF
    (Drawing Exchange Format) format. DXF is a widely used file format for
    exchanging CAD (Computer-Aided Design) data between different software
    applications.


    Args:
        version (str, optional): The DXF version to use for the output file.
            Defaults to ezdxf.DXF2013.
        unit (Unit, optional): The unit used for the exported DXF. It should be
            one of the Unit enums: Unit.MC, Unit.MM, Unit.CM,
            Unit.M, Unit.IN, or Unit.FT. Defaults to Unit.MM.
        color (Optional[ColorIndex], optional): The default color index for shapes.
            It can be specified as a ColorIndex enum or None.. Defaults to None.
        line_weight (Optional[float], optional): The default line weight
            (stroke width) for shapes, in millimeters. . Defaults to None.
        line_type (Optional[LineType], optional): e default line type for shapes.
            It should be a LineType enum or None.. Defaults to None.


    Example:

        .. code-block:: python

            exporter = ExportDXF(unit=Unit.MM, line_weight=0.5)
            exporter.add_layer("Layer 1", color=ColorIndex.RED, line_type=LineType.DASHED)
            exporter.add_shape(shape_object, layer="Layer 1")
            exporter.write("output.dxf")

    Raises:
        ValueError: unit not supported

    """

    # A dictionary that maps Unit enums to their corresponding DXF unit
    # constants used by the ezdxf library for conversion.
    _UNITS_LOOKUP = {
        Unit.MC: 13,
        Unit.MM: ezdxf.units.MM,
        Unit.CM: ezdxf.units.CM,
        Unit.M: ezdxf.units.M,
        Unit.IN: ezdxf.units.IN,
        Unit.FT: ezdxf.units.FT,
    }

    #  A set containing the Unit enums that represent metric units
    # (millimeter, centimeter, and meter).
    METRIC_UNITS = {
        Unit.MM,
        Unit.CM,
        Unit.M,
    }

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def __init__(
        self,
        version: str = ezdxf.DXF2013,
        unit: Unit = Unit.MM,
        color: Optional[ColorIndex] = None,
        line_weight: Optional[float] = None,
        line_type: Optional[LineType] = None,
    ):
        self._non_planar_point_count = 0
        if unit not in self._UNITS_LOOKUP:
            raise ValueError(f"unit `{unit.name}` not supported.")
        if unit in ExportDXF.METRIC_UNITS:
            self._linetype_scale = Export2D.LTYPE_SCALE[Unit.MM]
        else:
            self._linetype_scale = 1
        self._document = ezdxf.new(
            dxfversion=version,
            units=self._UNITS_LOOKUP[unit],
            setup=False,
        )
        self._modelspace = self._document.modelspace()

        default_layer = self._document.layers.get("0")
        if color is not None:
            default_layer.color = color.value
        if line_weight is not None:
            default_layer.dxf.lineweight = round(line_weight * 100)
        if line_type is not None:
            default_layer.dxf.linetype = self._linetype(line_type)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def add_layer(
        self,
        name: str,
        *,
        color: Optional[ColorIndex] = None,
        line_weight: Optional[float] = None,
        line_type: Optional[LineType] = None,
    ) -> Self:
        """add_layer

        Adds a new layer to the DXF export with the given properties.

        Args:
            name (str): The name of the layer definition. Must be unique among all layers.
            color (Optional[ColorIndex], optional): The color index for shapes on this layer.
                It can be specified as a ColorIndex enum or None. Defaults to None.
            line_weight (Optional[float], optional): The line weight (stroke width) for shapes
                on this layer, in millimeters. Defaults to None.
            line_type (Optional[LineType], optional): The line type for shapes on this layer.
                It should be a LineType enum or None. Defaults to None.

        Returns:
            Self: DXF document with additional layer
        """
        # ezdxf :doc:`line type <ezdxf-stable:concepts/linetypes>`.

        kwargs = {}

        if line_type is not None:
            linetype = self._linetype(line_type)
            kwargs["linetype"] = linetype

        if color is not None:
            kwargs["color"] = color.value

        if line_weight is not None:
            kwargs["lineweight"] = round(line_weight * 100)

        self._document.layers.add(name, **kwargs)
        return self

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _linetype(self, line_type: LineType) -> str:
        """Ensure that the specified LineType has been defined in the document,
        and return its string name."""
        linetype = line_type.value
        if linetype not in self._document.linetypes:
            # The linetype is not in the doc yet.
            # Add it from our available definitions.
            if linetype in Export2D.LINETYPE_DEFS:
                desc, pattern = Export2D.LINETYPE_DEFS.get(linetype)
                self._document.linetypes.add(
                    name=linetype,
                    pattern=[self._linetype_scale * v for v in pattern],
                    description=desc,
                )
            else:
                raise ValueError("Unknown linetype `{linetype}`.")
        return linetype

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def add_shape(self, shape: Union[Shape, Iterable[Shape]], layer: str = "") -> Self:
        """add_shape

        Adds a shape to the specified layer.

        Args:
            shape (Union[Shape, Iterable[Shape]]): The shape or collection of shapes to be
                  added. It can be a single Shape object or an iterable of Shape objects.
            layer (str, optional): The name of the layer where the shape will be
                added. If not specified, the default layer will be used. Defaults to "".

        Returns:
            Self: Document with additional shape
        """
        if isinstance(shape, Shape):
            self._add_single_shape(shape, layer)
        else:
            for s in shape:
                self._add_single_shape(s, layer)
        if self._non_planar_point_count > 0:
            print("WARNING, exporting non-planar shape to 2D format.")
            print("  This is probably not what you want.")
            print(
                f"  {self._non_planar_point_count} points found outside the XY plane."
            )
        return self

    def _add_single_shape(self, shape: Shape, layer: str = ""):
        attributes = {}
        if layer:
            attributes["layer"] = layer
        for edge in shape.edges():
            self._convert_edge(edge, attributes)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def write(self, file_name: str):
        """write

        Writes the DXF data to the specified file name.

        Args:
            file_name (str): The file name (including path) where the DXF data will
                be written.
        """
        # Reset the main CAD viewport of the model space to the
        # extents of its entities.
        # https://github.com/gumyr/build123d/issues/382 tracks
        # exposing viewport control to the user.
        zoom.extents(self._modelspace)

        self._document.saveas(file_name)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_point(self, pt: Union[gp_XYZ, gp_Pnt, gp_Vec, Vector]) -> Vec2:
        """Create a Vec2 from a gp_Pnt or Vector.
        This method also checks for points z != 0."""
        if isinstance(pt, (gp_XYZ, gp_Pnt, gp_Vec)):
            (x, y, z) = (pt.X(), pt.Y(), pt.Z())
        elif isinstance(pt, Vector):
            (x, y, z) = tuple(pt)
        else:
            raise TypeError(
                f"Expected `gp_Pnt`, `gp_XYZ`, `gp_Vec`, or `Vector`.  Got `{type(pt).__name__}`."
            )
        if abs(z) > 1e-6:
            self._non_planar_point_count += 1
        return Vec2(x, y)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_line(self, edge: Edge, attribs: dict):
        """Converts a Line object into a DXF line entity."""
        self._modelspace.add_line(
            self._convert_point(edge.start_point()),
            self._convert_point(edge.end_point()),
            attribs,
        )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_circle(self, edge: Edge, attribs: dict):
        """Converts a Circle object into a DXF circle entity."""
        curve = edge._geom_adaptor()
        circle = curve.Circle()
        center = self._convert_point(circle.Location())
        radius = circle.Radius()

        if curve.IsClosed():
            self._modelspace.add_circle(center, radius, attribs)

        else:
            x_axis = circle.XAxis().Direction()
            z_axis = circle.Axis().Direction()
            phi = gp_Dir(1, 0, 0).AngleWithRef(x_axis, gp_Dir(0, 0, 1))
            u1 = curve.FirstParameter()
            u2 = curve.LastParameter()
            if z_axis.Z() > 0:
                angle1 = math.degrees(phi + u1)
                angle2 = math.degrees(phi + u2)
                ccw = True
            else:
                angle1 = math.degrees(phi - u1)
                angle2 = math.degrees(phi - u2)
                ccw = False
            self._modelspace.add_arc(center, radius, angle1, angle2, ccw, attribs)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_ellipse(self, edge: Edge, attribs: dict):
        """Converts an Ellipse object into a DXF ellipse entity."""
        geom = edge._geom_adaptor()
        ellipse = geom.Ellipse()
        minor_radius = ellipse.MinorRadius()
        major_radius = ellipse.MajorRadius()
        center = ellipse.Location()
        major_axis = major_radius * gp_Vec(ellipse.XAxis().Direction())
        main_dir = ellipse.Axis().Direction()
        if main_dir.Z() > 0:
            start = geom.FirstParameter()
            end = geom.LastParameter()
        else:
            start = -geom.LastParameter()
            end = -geom.FirstParameter()
        self._modelspace.add_ellipse(
            self._convert_point(center),
            self._convert_point(major_axis),
            minor_radius / major_radius,
            start,
            end,
            attribs,
        )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_bspline(self, edge: Edge, attribs):
        """Converts a BSpline object into a DXF spline entity."""
        # This reduces the B-Spline to degree 3, generally adding
        # poles and knots to approximate the original.
        # This also will convert basically any edge into a B-Spline.
        edge = edge.to_splines()

        # This pulls the underlying Geom_BSplineCurve out of the Edge.
        # The adaptor also supplies a parameter range for the curve.
        adaptor = edge._geom_adaptor()
        curve = adaptor.Curve().Curve()
        u1 = adaptor.FirstParameter()
        u2 = adaptor.LastParameter()

        # Extract the relevant segment of the curve.
        spline = GeomConvert.SplitBSplineCurve_s(
            curve,
            u1,
            u2,
            Export2D.PARAMETRIC_TOLERANCE,
        )

        # need to apply the transform on the geometry level
        t = edge.location.wrapped.Transformation()
        spline.Transform(t)

        order = spline.Degree() + 1
        knots = list(spline.KnotSequence())
        poles = [self._convert_point(p) for p in spline.Poles()]
        weights = (
            [spline.Weight(i) for i in range(1, spline.NbPoles() + 1)]
            if spline.IsRational()
            else None
        )

        if spline.IsPeriodic():
            pad = spline.NbKnots() - spline.LastUKnotIndex()
            poles += poles[:pad]

        dxf_spline = ezdxf.math.BSpline(poles, order, knots, weights)

        self._modelspace.add_spline(dxfattribs=attribs).apply_construction_tool(
            dxf_spline
        )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_other(self, edge: Edge, attribs: dict):
        """Converts any other type of Edge object into a DXF entity."""
        self._convert_bspline(edge, attribs)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # A dictionary that maps geometry types (e.g., LINE, CIRCLE, ELLIPSE, BSPLINE)
    # to their corresponding conversion methods.
    _CONVERTER_LOOKUP = {
        GeomType.LINE: _convert_line,
        GeomType.CIRCLE: _convert_circle,
        GeomType.ELLIPSE: _convert_ellipse,
        GeomType.BSPLINE: _convert_bspline,
    }

    def _convert_edge(self, edge: Edge, attribs: dict):
        geom_type = edge.geom_type
        convert = self._CONVERTER_LOOKUP.get(geom_type, ExportDXF._convert_other)
        convert(self, edge, attribs)


# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------


class ExportSVG(Export2D):
    """ExportSVG

    SVG file export functionality.

    The ExportSVG class provides functionality for exporting 2D shapes to SVG
    (Scalable Vector Graphics) format. SVG is a widely used vector graphics format
    that is supported by web browsers and various graphic editors.

    Args:
        unit (Unit, optional): The unit used for the exported SVG. It should be one of
            the Unit enums: Unit.MM, Unit.CM, or Unit.IN. Defaults to
            Unit.MM.
        scale (float, optional): The scaling factor applied to the exported SVG.
            Defaults to 1.
        margin (float, optional): The margin added around the exported shapes.
            Defaults to 0.
        fit_to_stroke (bool, optional): A boolean indicating whether the SVG view box
            should fit the strokes of the shapes. Defaults to True.
        precision (int, optional): The number of decimal places used for rounding
            coordinates in the SVG. Defaults to 6.
        fill_color (Union[ColorIndex, RGB, None], optional): The default fill color
            for shapes. It can be specified as a ColorIndex, an RGB tuple, or None.
            Defaults to None.
        line_color (Union[ColorIndex, RGB, None], optional): The default line color for
            shapes. It can be specified as a ColorIndex or an RGB tuple, or None.
            Defaults to Export2D.DEFAULT_COLOR_INDEX.
        line_weight (float, optional): The default line weight (stroke width) for
            shapes, in millimeters. Defaults to Export2D.DEFAULT_LINE_WEIGHT.
        line_type (LineType, optional): The default line type for shapes. It should be
            a LineType enum. Defaults to Export2D.DEFAULT_LINE_TYPE.
        dot_length (Union[DotLength, float], optional): The width of rendered dots in a
            Can be either a DotLength enum or a float value in tenths of an inch.
            Defaults to DotLength.INKSCAPE_COMPAT.


    Example:

        .. code-block:: python

            exporter = ExportSVG(unit=Unit.MM, line_weight=0.5)
            exporter.add_layer("Layer 1", fill_color=(255, 0, 0), line_color=(0, 0, 255))
            exporter.add_shape(shape_object, layer="Layer 1")
            exporter.write("output.svg")

    Raises:
        ValueError: Invalid unit.

    """

    # pylint: disable=too-many-instance-attributes
    _Converter = Callable[[Edge], ET.Element]

    # These are the units which are available in the Unit enum *and*
    # are valid units in SVG.
    _UNIT_STRING = {
        Unit.MM: "mm",
        Unit.CM: "cm",
        Unit.IN: "in",
    }

    class _Layer:
        def __init__(
            self,
            name: str,
            fill_color: Union[ColorIndex, RGB, Color, None],
            line_color: Union[ColorIndex, RGB, Color, None],
            line_weight: float,
            line_type: LineType,
        ):
            def convert_color(
                c: Union[ColorIndex, RGB, Color, None]
            ) -> Union[Color, None]:
                if isinstance(c, ColorIndex):
                    # The easydxf color indices BLACK and WHITE have the same
                    # value (7), and are both mapped to (255,255,255) by the
                    # aci2rgb() function.  We prefer (0,0,0).
                    if c == ColorIndex.BLACK:
                        c = RGB(0, 0, 0)
                    else:
                        c = aci2rgb(c.value)
                elif isinstance(c, tuple):
                    c = RGB(*c)
                if isinstance(c, RGB):
                    c = Color(*c.to_floats(), 1)
                return c

            self.name = name
            self.fill_color = convert_color(fill_color)
            self.line_color = convert_color(line_color)
            self.line_weight = line_weight
            self.line_type = line_type
            self.elements: list[ET.Element] = []

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def __init__(
        self,
        unit: Unit = Unit.MM,
        scale: float = 1,
        margin: float = 0,
        fit_to_stroke: bool = True,
        precision: int = 6,
        fill_color: Union[ColorIndex, RGB, Color, None] = None,
        line_color: Union[ColorIndex, RGB, Color, None] = Export2D.DEFAULT_COLOR_INDEX,
        line_weight: float = Export2D.DEFAULT_LINE_WEIGHT,  # in millimeters
        line_type: LineType = Export2D.DEFAULT_LINE_TYPE,
        dot_length: Union[DotLength, float] = DotLength.INKSCAPE_COMPAT,
    ):
        if unit not in ExportSVG._UNIT_STRING:
            raise ValueError(
                "Invalid unit.  Supported units are "
                f"{', '.join(ExportSVG._UNIT_STRING.values())}."
            )
        self.unit = unit
        self.scale = scale
        self.margin = margin
        self.fit_to_stroke = fit_to_stroke
        self.precision = precision
        self.dot_length = dot_length
        self._non_planar_point_count = 0
        self._layers: dict[str, ExportSVG._Layer] = {}
        self._bounds: BoundBox = None

        # Add the default layer.
        self.add_layer(
            name="",
            fill_color=fill_color,
            line_color=line_color,
            line_weight=line_weight,
            line_type=line_type,
        )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def add_layer(
        self,
        name: str,
        *,
        fill_color: Union[ColorIndex, RGB, Color, None] = None,
        line_color: Union[ColorIndex, RGB, Color, None] = Export2D.DEFAULT_COLOR_INDEX,
        line_weight: float = Export2D.DEFAULT_LINE_WEIGHT,  # in millimeters
        line_type: LineType = Export2D.DEFAULT_LINE_TYPE,
    ) -> Self:
        """add_layer

        Adds a new layer to the SVG export with the given properties.

        Args:
            name (str): The name of the layer. Must be unique among all layers.
            fill_color (Union[ColorIndex, RGB, Color, None], optional): The fill color for shapes
                on this layer. It can be specified as a ColorIndex, an RGB tuple,
                a Color, or None.  Defaults to None.
            line_color (Union[ColorIndex, RGB, Color, None], optional): The line color for shapes on
                this layer. It can be specified as a ColorIndex or an RGB tuple,
                a Color, or None.  Defaults to Export2D.DEFAULT_COLOR_INDEX.
            line_weight (float, optional): The line weight (stroke width) for shapes on
                this layer, in millimeters. Defaults to Export2D.DEFAULT_LINE_WEIGHT.
            line_type (LineType, optional): The line type for shapes on this layer.
                It should be a LineType enum. Defaults to Export2D.DEFAULT_LINE_TYPE.

        Raises:
            ValueError: Duplicate layer name
            ValueError: Unknown linetype

        Returns:
            Self: Drawing with an additional layer
        """
        if name in self._layers:
            raise ValueError(f"Duplicate layer name '{name}'.")
        if line_type.value not in Export2D.LINETYPE_DEFS:
            raise ValueError(f"Unknown linetype `{line_type.value}`.")
        layer = ExportSVG._Layer(
            name=name,
            fill_color=fill_color,
            line_color=line_color,
            line_weight=line_weight,
            line_type=line_type,
        )
        self._layers[name] = layer
        return self

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def add_shape(
        self,
        shape: Union[Shape, Iterable[Shape]],
        layer: str = "",
        reverse_wires: bool = False,
    ):
        """add_shape

        Adds a shape or a collection of shapes to the specified layer.

        Args:
            shape (Union[Shape, Iterable[Shape]]): The shape or collection of shapes to be
                  added. It can be a single Shape object or an iterable of Shape objects.
            layer (str, optional): The name of the layer where the shape(s) will be added.
                Defaults to "".
            reverse_wires (bool, optional): A boolean indicating whether the wires of the
                shape(s) should be in reversed direction. Defaults to False.

        Raises:
            ValueError: Undefined layer
        """
        if layer not in self._layers:
            raise ValueError(f"Undefined layer: {layer}.")
        layer = self._layers[layer]
        if isinstance(shape, Shape):
            self._add_single_shape(shape, layer, reverse_wires)
        else:
            for s in shape:
                self._add_single_shape(s, layer, reverse_wires)

    def _add_single_shape(self, shape: Shape, layer: _Layer, reverse_wires: bool):
        # pylint: disable=too-many-locals
        self._non_planar_point_count = 0
        bb = shape.bounding_box()
        self._bounds = self._bounds.add(bb) if self._bounds else bb
        elements = []

        # Process Faces.
        faces = shape.faces()
        # print(f"{len(faces)} faces")
        for face in faces:
            outer = face.outer_wire()
            inner = face.inner_wires()
            if 0 == len(inner):
                # Faces without inner wires can be processed as bare wires.
                # This allows circles and ellipses to be preserved in the
                # output as primitives.
                face_element = self._wire_element(outer, reverse_wires)
            else:
                # Faces with inner wires are converted into a single SVG
                # path element with the inner and outer wires, so that faces
                # with holes will render correctly with a fill color.
                face_segments = self._wire_segments(outer, reverse_wires)
                for i in inner:
                    segments = self._wire_segments(i, reverse_wires)
                    face_segments.extend(segments)
                face_path = PT.Path(*face_segments)
                face_element = ET.Element("path", {"d": face_path.d()})
            elements.append(face_element)

        # Process Wires that are not part of Faces.
        # Each wire is converted to a single SVG element.
        # Circles and ellipses are preserved, everything else will
        # be output as an SVG path element.
        loose_wires = []
        explorer = TopExp_Explorer(
            shape.wrapped,
            ToFind=TopAbs_ShapeEnum.TopAbs_WIRE,
            ToAvoid=TopAbs_ShapeEnum.TopAbs_FACE,
        )
        while explorer.More():
            topo_wire = explorer.Current()
            loose_wires.append(Wire(topo_wire))
            explorer.Next()
        # print(f"{len(loose_wires)} loose wires")
        for wire in loose_wires:
            elements.append(self._wire_element(wire, reverse_wires))

        # Process Edges that are not part of Wires.
        # Each edge is output as an SVG element.
        # Closed circular or elliptical edges are output as
        # circle or ellipse primitives.  Everything else is output
        # as an SVG path element.
        loose_edges = []
        explorer = TopExp_Explorer(
            shape.wrapped,
            ToFind=TopAbs_ShapeEnum.TopAbs_EDGE,
            ToAvoid=TopAbs_ShapeEnum.TopAbs_WIRE,
        )
        while explorer.More():
            topo_edge = explorer.Current()
            loose_edges.append(Edge(topo_edge))
            explorer.Next()
        # print(f"{len(loose_edges)} loose edges")
        loose_edge_elements = [self._edge_element(edge) for edge in loose_edges]
        elements.extend(loose_edge_elements)

        layer.elements.extend(elements)
        if self._non_planar_point_count > 0:
            print("WARNING, exporting non-planar shape to 2D format.")
            print("  This is probably not what you want.")
            print(
                f"  {self._non_planar_point_count} points found outside the XY plane."
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _wire_edges(wire: Wire, reverse: bool) -> List[Edge]:
        edges = []
        explorer = BRepTools_WireExplorer(wire.wrapped)
        while explorer.More():
            topo_edge = explorer.Current()
            edges.append(Edge(topo_edge))
            explorer.Next()
        if reverse:
            edges.reverse()
        return edges

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _wire_segments(self, wire: Wire, reverse: bool) -> list[PathSegment]:
        edges = ExportSVG._wire_edges(wire, reverse)
        wire_segments: list[PathSegment] = []
        for edge in edges:
            edge_segments = self._edge_segments(edge, reverse)
            wire_segments.extend(edge_segments)
        return wire_segments

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _wire_element(self, wire: Wire, reverse: bool) -> ET.Element:
        edges = ExportSVG._wire_edges(wire, reverse)
        if len(edges) == 1:
            wire_element = self._edge_element(edges[0])
        else:
            wire_segments: list[PathSegment] = []
            for edge in edges:
                edge_segments = self._edge_segments(edge, reverse)
                wire_segments.extend(edge_segments)
            wire_path = PT.Path(*wire_segments)
            wire_element = ET.Element("path", {"d": wire_path.d()})
        return wire_element

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _path_point(self, pt: Union[gp_Pnt, Vector]) -> complex:
        """Create a complex point from a gp_Pnt or Vector.
        We are using complex because that is what svgpathtools wants.
        This method also checks for points z != 0."""
        if isinstance(pt, gp_Pnt):
            xyz = pt.X(), pt.Y(), pt.Z()
        elif isinstance(pt, Vector):
            xyz = pt.X, pt.Y, pt.Z
        else:
            raise TypeError(
                f"Expected `gp_Pnt` or `Vector`.  Got `{type(pt).__name__}`."
            )
        x, y, z = tuple(round(v, self.precision) for v in xyz)
        if z != 0:
            self._non_planar_point_count += 1
        return complex(x, y)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _line_segment(self, edge: Edge, reverse: bool) -> PT.Line:
        curve = edge._geom_adaptor()
        fp = curve.FirstParameter()
        lp = curve.LastParameter()
        (u0, u1) = (lp, fp) if reverse else (fp, lp)
        p0 = self._path_point(curve.Value(u0))
        p1 = self._path_point(curve.Value(u1))
        result = PT.Line(p0, p1)
        return result

    def _line_segments(self, edge: Edge, reverse: bool) -> list[PathSegment]:
        return [self._line_segment(edge, reverse)]

    def _line_element(self, edge: Edge) -> ET.Element:
        """Converts a Line object into an SVG line element."""
        segment = self._line_segment(edge, reverse=False)
        result = ET.Element(
            "line",
            {
                "x1": str(segment.start.real),
                "y1": str(segment.start.imag),
                "x2": str(segment.end.real),
                "y2": str(segment.end.imag),
            },
        )
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _circle_segments(self, edge: Edge, reverse: bool) -> list[PathSegment]:
        # pylint: disable=too-many-locals
        curve = edge._geom_adaptor()
        circle = curve.Circle()
        radius = circle.Radius()
        x_axis = circle.XAxis().Direction()
        z_axis = circle.Axis().Direction()
        fp = curve.FirstParameter()
        lp = curve.LastParameter()
        du = lp - fp
        large_arc = (du < -math.pi) or (du > math.pi)
        sweep = (z_axis.Z() > 0) ^ reverse
        (u0, u1) = (lp, fp) if reverse else (fp, lp)
        start = self._path_point(curve.Value(u0))
        end = self._path_point(curve.Value(u1))
        radius = complex(radius, radius)
        rotation = math.degrees(gp_Dir(1, 0, 0).AngleWithRef(x_axis, gp_Dir(0, 0, 1)))
        if curve.IsClosed():
            midway = self._path_point(curve.Value((u0 + u1) / 2))
            result = [
                PT.Arc(start, radius, rotation, False, sweep, midway),
                PT.Arc(midway, radius, rotation, False, sweep, end),
            ]
        else:
            result = [PT.Arc(start, radius, rotation, large_arc, sweep, end)]
        return result

    def _circle_element(self, edge: Edge) -> ET.Element:
        """Converts a Circle object into an SVG circle element."""
        if edge.is_closed:
            curve = edge._geom_adaptor()
            circle = curve.Circle()
            radius = circle.Radius()
            center = circle.Location()
            c = self._path_point(center)
            result = ET.Element(
                "circle", {"cx": str(c.real), "cy": str(c.imag), "r": str(radius)}
            )
        else:
            arcs = self._circle_segments(edge, reverse=False)
            path = PT.Path(*arcs)
            result = ET.Element("path", {"d": path.d()})
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _ellipse_segments(self, edge: Edge, reverse: bool) -> list[PathSegment]:
        # pylint: disable=too-many-locals
        curve = edge._geom_adaptor()
        ellipse = curve.Ellipse()
        minor_radius = ellipse.MinorRadius()
        major_radius = ellipse.MajorRadius()
        x_axis = ellipse.XAxis().Direction()
        z_axis = ellipse.Axis().Direction()
        fp = curve.FirstParameter()
        lp = curve.LastParameter()
        du = lp - fp
        large_arc = (du < -math.pi) or (du > math.pi)
        sweep = (z_axis.Z() > 0) ^ reverse
        (u0, u1) = (lp, fp) if reverse else (fp, lp)
        start = self._path_point(curve.Value(u0))
        end = self._path_point(curve.Value(u1))
        radius = complex(major_radius, minor_radius)
        rotation = math.degrees(gp_Dir(1, 0, 0).AngleWithRef(x_axis, gp_Dir(0, 0, 1)))
        if curve.IsClosed():
            midway = self._path_point(curve.Value((u0 + u1) / 2))
            result = [
                PT.Arc(start, radius, rotation, False, sweep, midway),
                PT.Arc(midway, radius, rotation, False, sweep, end),
            ]
        else:
            result = [PT.Arc(start, radius, rotation, large_arc, sweep, end)]
        return result

    def _ellipse_element(self, edge: Edge) -> ET.Element:
        """Converts an Ellipse object into an SVG ellipse element."""
        arcs = self._ellipse_segments(edge, reverse=False)
        path = PT.Path(*arcs)
        result = ET.Element("path", {"d": path.d()})
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _bspline_segments(self, edge: Edge, reverse: bool) -> list[PathSegment]:
        # This reduces the B-Spline to degree 3, generally adding
        # poles and knots to approximate the original.
        # This also will convert basically any edge into a B-Spline.
        edge = edge.to_splines()

        # This pulls the underlying Geom_BSplineCurve out of the Edge.
        # The adaptor also supplies a parameter range for the curve.
        adaptor = edge._geom_adaptor()
        spline = adaptor.Curve().Curve()
        u1 = adaptor.FirstParameter()
        u2 = adaptor.LastParameter()

        # Apply the shape location to the geometry.
        t = edge.location.wrapped.Transformation()
        spline.Transform(t)
        # describe_bspline(spline)

        # Convert the B-Spline to Bezier curves.
        # According to the OCCT 7.6.0 documentation,
        # "ParametricTolerance is not used."
        converter = GeomConvert_BSplineCurveToBezierCurve(
            spline, u1, u2, Export2D.PARAMETRIC_TOLERANCE
        )

        def make_segment(bezier: Geom_BezierCurve, reverse: bool) -> PathSegment:
            p = [self._path_point(p) for p in bezier.Poles()]
            if reverse:
                p.reverse()
            if len(p) == 2:
                result = PT.Line(start=p[0], end=p[1])
            elif len(p) == 3:
                result = PT.QuadraticBezier(start=p[0], control=p[1], end=p[2])
            elif len(p) == 4:
                result = PT.CubicBezier(
                    start=p[0], control1=p[1], control2=p[2], end=p[3]
                )
            else:
                raise ValueError(f"Surprising Bézier of degree {bezier.Degree()}!")
            return result

        result = [
            make_segment(converter.Arc(i), reverse)
            for i in range(1, converter.NbArcs() + 1)
        ]
        if reverse:
            result.reverse()
        return result

    def _bspline_element(self, edge: Edge) -> ET.Element:
        """Converts a BSpline object into an SVG path element representing a Bézier curve."""
        segments = self._bspline_segments(edge, reverse=False)
        path = PT.Path(*segments)
        result = ET.Element("path", {"d": path.d()})
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _other_segments(self, edge: Edge, reverse: bool):
        # _bspline_segments can actually handle basically anything
        # because it calls Edge.to_splines() first thing.
        return self._bspline_segments(edge, reverse)

    def _other_element(self, edge: Edge) -> ET.Element:
        # _bspline_element can actually handle basically anything
        # because it calls Edge.to_splines() first thing.
        return self._bspline_element(edge)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    _SEGMENT_LOOKUP = {
        GeomType.LINE: _line_segments,
        GeomType.CIRCLE: _circle_segments,
        GeomType.ELLIPSE: _ellipse_segments,
        GeomType.BSPLINE: _bspline_segments,
    }

    def _edge_segments(self, edge: Edge, reverse: bool) -> list[PathSegment]:
        edge_reversed = edge.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        geom_type = edge.geom_type
        segments = self._SEGMENT_LOOKUP.get(geom_type, ExportSVG._other_segments)
        result = segments(self, edge, reverse ^ edge_reversed)
        return result

    _ELEMENT_LOOKUP = {
        GeomType.LINE: _line_element,
        GeomType.CIRCLE: _circle_element,
        GeomType.ELLIPSE: _ellipse_element,
        GeomType.BSPLINE: _bspline_element,
    }

    def _edge_element(self, edge: Edge) -> ET.Element:
        geom_type = edge.geom_type
        element = self._ELEMENT_LOOKUP.get(geom_type, ExportSVG._other_element)
        result = element(self, edge)
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _stroke_dasharray(self, layer: _Layer):
        ltname = layer.line_type.value
        _, pattern = Export2D.LINETYPE_DEFS[ltname]

        d = (
            self.dot_length.value
            if isinstance(self.dot_length, DotLength)
            else self.dot_length
        )
        pattern = copy(pattern)
        plen = len(pattern)
        for i in range(0, plen):
            if pattern[i] == 0:
                pattern[i] = d
                pattern[i - 1] -= d / 2
                pattern[(i + 1) % plen] -= d / 2

        ltscale = ExportSVG.LTYPE_SCALE[self.unit] * layer.line_weight / self.scale
        result = [f"{round(ltscale * abs(e), self.precision)}" for e in pattern[1:]]
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _group_for_layer(self, layer: _Layer, attribs: dict = None) -> ET.Element:

        def _color_attribs(c: Color) -> Tuple[str, str]:
            if c:
                (r, g, b, a) = tuple(c)
                (r, g, b, a) = (int(r * 255), int(g * 255), int(b * 255), round(a, 3))
                rgb = f"rgb({r},{g},{b})"
                opacity = f"{a}" if a < 1 else None
                return (rgb, opacity)
            return ("none", None)

        if attribs is None:
            attribs = {}
        (fill, fill_opacity) = _color_attribs(layer.fill_color)
        attribs["fill"] = fill
        if fill_opacity:
            attribs["fill-opacity"] = fill_opacity
        (stroke, stroke_opacity) = _color_attribs(layer.line_color)
        attribs["stroke"] = stroke
        if stroke_opacity:
            attribs["stroke-opacity"] = stroke_opacity
        lwscale = unit_conversion_scale(Unit.MM, self.unit) / self.scale
        stroke_width = layer.line_weight * lwscale
        attribs["stroke-width"] = f"{stroke_width}"
        result = ET.Element("g", attribs)
        if layer.name:
            result.set("id", layer.name)

        if layer.line_type is not LineType.CONTINUOUS:
            dash_array = self._stroke_dasharray(layer)
            result.set("stroke-dasharray", " ".join(dash_array))

        for element in layer.elements:
            result.append(element)

        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def write(self, path: str):
        """write

        Writes the SVG data to the specified file path.

        Args:
            path (str): The file path where the SVG data will be written.
        """
        # pylint: disable=too-many-locals
        bb = self._bounds
        doc_margin = self.margin
        if self.fit_to_stroke:
            max_line_weight = max(l.line_weight for l in self._layers.values())
            doc_margin += max_line_weight / 2
        view_margin = doc_margin / self.scale
        view_left = round(+bb.min.X - view_margin, self.precision)
        view_top = round(-bb.max.Y - view_margin, self.precision)
        view_width = round(bb.size.X + 2 * view_margin, self.precision)
        view_height = round(bb.size.Y + 2 * view_margin, self.precision)
        view_box = [str(f) for f in [view_left, view_top, view_width, view_height]]
        doc_width = round(view_width * self.scale, self.precision)
        doc_height = round(view_height * self.scale, self.precision)
        doc_unit = self._UNIT_STRING.get(self.unit, "")
        svg = ET.Element(
            "svg",
            {
                "width": f"{doc_width}{doc_unit}",
                "height": f"{doc_height}{doc_unit}",
                "viewBox": " ".join(view_box),
                "version": "1.1",
                "xmlns": "http://www.w3.org/2000/svg",
            },
        )

        container_group = ET.Element(
            "g",
            {
                "transform": "scale(1,-1)",
                "stroke-linecap": "round",
            },
        )
        svg.append(container_group)

        for _, layer in self._layers.items():
            if layer.elements:
                layer_group = self._group_for_layer(layer)
                container_group.append(layer_group)

        xml = ET.ElementTree(svg)
        ET.indent(xml, "  ")
        xml.write(path, encoding="utf-8", xml_declaration=True, default_namespace=False)
