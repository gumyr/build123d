# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error

from build123d import *
from build123d import Shape
from OCP.GeomConvert import GeomConvert_BSplineCurveToBezierCurve #type: ignore
from OCP.GeomConvert import GeomConvert #type: ignore
from OCP.Geom import Geom_BSplineCurve, Geom_BezierCurve #type: ignore
from OCP.gp import gp_XYZ, gp_Pnt, gp_Vec, gp_Dir, gp_Ax2 #type: ignore
from OCP.BRepLib import BRepLib #type: ignore
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape #type: ignore
from OCP.HLRAlgo import HLRAlgo_Projector #type: ignore
from math import degrees
from typing import Callable, List, Union, Tuple, Dict, Optional
from typing_extensions import Self
import svgpathtools as PT
import xml.etree.ElementTree as ET
from enum import Enum, auto
import ezdxf
from ezdxf import zoom
from ezdxf.math import Vec2
from ezdxf.colors import aci2rgb
from ezdxf.tools.standards import (
    ISO_LTYPE_FACTOR, linetypes as ezdxf_linetypes
)
import copy

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class Drawing(object):

    def __init__(
        self,
        shape: Shape,
        *,
        projection_dir: VectorLike = (-1.75, 1.1, 5),
        axes: Optional[float] = None,
        with_hidden: bool = True,
        focus: Union[float, None] = None,
    ):

        hlr = HLRBRep_Algo()
        hlr.Add(shape.wrapped)

        coordinate_system = gp_Ax2(gp_Pnt(), gp_Dir(*projection_dir))

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

        # magic number from CQ
        # TODO: figure out the proper source of this value.
        tolerance = 1e-6

        # Fix the underlying geometry - otherwise we will get segfaults
        for el in visible:
            BRepLib.BuildCurves3d_s(el, tolerance)
        for el in hidden:
            BRepLib.BuildCurves3d_s(el, tolerance)

        # Convert and store the results.
        self.visible_lines = Compound.make_compound(map(Shape, visible))
        self.hidden_lines = Compound.make_compound(map(Shape, hidden))

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class AutoNameEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name
    
class LineType(AutoNameEnum):
    CONTINUOUS = auto()
    CENTERX2 = auto()
    CENTER2 = auto()
    DASHED = auto()
    DASHEDX2 = auto()
    DASHED2 = auto()
    PHANTOM = auto()
    PHANTOMX2 = auto()
    PHANTOM2 = auto()
    DASHDOT = auto()
    DASHDOTX2 = auto()
    DASHDOT2 = auto()
    DOT = auto()
    DOTX2 = auto()
    DOT2 = auto()
    DIVIDE = auto()
    DIVIDEX2 = auto()
    DIVIDE2 = auto()
    ISO_DASH_SPACE = "ACAD_ISO03W100"

class ColorIndex(Enum):
    RED = 1
    YELLOW = 2
    GREEN = 3
    CYAN = 4
    BLUE = 5
    MAGENTA = 6
    BLACK = 7
    GRAY = 8
    LIGHT_GRAY = 9

# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------

class Export2D(object):
    """Base class for 2D exporters (DXF, SVG)."""

    @staticmethod
    def describe_bspline(bspline: Geom_BSplineCurve):
        degree = bspline.Degree()
        distribution = bspline.KnotDistribution()
        rational = "Rational" if bspline.IsRational() else "Non-rational"
        pole_z = [
            abs(round(p.Z(), 6)) != 0
            for p in bspline.Poles()
        ]
        planar = "non-planar" if any(pole_z) else "planar"
        print(f"\n{distribution} {rational} {planar} B-Spline of degree {degree}")
    
    # When specifying a parametric interval [u1, u2] on a spline,
    # OCCT considers two parameters to be equal if
    # abs(u1-u2) < tolerance, and generally raises an exception in
    # this case.
    PARAMETRIC_TOLERANCE = 1e-9

    DEFAULT_COLOR_INDEX = ColorIndex.BLACK
    DEFAULT_LINE_WEIGHT = 0.09
    DEFAULT_LINE_TYPE = LineType.CONTINUOUS

    # Pull default (ANSI) linetypes out of ezdxf for more convenient
    # lookup and add some ISO linetypes.  Units are imperial.
    # The first number in the pattern is the total length of the pattern.
    # Positive numbers are dashes, negative numbers are spaces, zero is a dot.
    # As far as I can tell:
    # Imperial ($MEASURENT 0) linetypes are defined in tenths of an inch.
    # When used in $MEASUREMENT 1 (metric) DXF files,
    # these values are converted to millimeters (multiplied by 2.54).
    # (When used in an SVG file, values are converted to the drawing
    # units of the file.)
    LINETYPE_DEFS = {
        name: (desc, pattern)
        for name, desc, pattern in ezdxf_linetypes()
    } | {
        LineType.ISO_DASH_SPACE.value: (
            "ISO dash space __    __    __    __    __    __",
            [3/2.54, 1.2/2.54, -1.8/2.54],
        ),
    }

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class ExportDXF(Export2D):

    UNITS_LOOKUP = {
        Unit.MILLIMETER: ezdxf.units.MM,
        Unit.CENTIMETER: ezdxf.units.CM,
        Unit.INCH      : ezdxf.units.IN,
        Unit.FOOT      : ezdxf.units.FT,
    }

    METRIC_UNITS = {
        Unit.MILLIMETER,
        Unit.CENTIMETER,
        Unit.METER,
    }

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def __init__(
        self,
        unit: Unit = Unit.MILLIMETER,
    ):
        if unit not in self.UNITS_LOOKUP:
            raise ValueError(f"unit `{unit.name}` not supported.")
        self._linetype_scale = ISO_LTYPE_FACTOR if unit in ExportDXF.METRIC_UNITS else 1
        self._dxf = ezdxf.new(
            units = self.UNITS_LOOKUP[unit],
            setup = False,
        )
        self._msp = self._dxf.modelspace()

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    
    def add_layer(
        self,
        name: str,
        *,
        color: Optional[ColorIndex] = None,
        line_weight: Optional[float] = None,
        line_type: Optional[LineType] = None,
    ) -> Self:
        """Create a layer definition

        Refer to :ref:`ezdxf layers <ezdxf-stable:layer_concept>` and
        :doc:`ezdxf layer tutorial <ezdxf-stable:tutorials/layers>`.

        :param name: layer definition name
        :param color: color index.
        :param linetype: ezdxf :doc:`line type <ezdxf-stable:concepts/linetypes>`
        """

        kwargs = {}
        
        if line_type is not None:
            linetype = line_type.value
            if linetype not in self._dxf.linetypes:
                # The linetype is not in the doc yet.
                # Add it from our available definitions.
                if linetype in Export2D.LINETYPE_DEFS:
                    desc, pattern = Export2D.LINETYPE_DEFS.get(linetype)
                    self._dxf.linetypes.add(
                        name=linetype,
                        pattern=[self._linetype_scale * v for v in pattern],
                        description=desc,
                    )
                else:
                    raise ValueError("Unknown linetype `{linetype}`.")
            kwargs['linetype'] = linetype

        if color is not None:
            kwargs['color'] = color.value
        
        if line_weight is not None:
            kwargs.set['lineweight'] = round(line_weight * 100)
        
        self._dxf.layers.add(name, **kwargs)
        return self

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def add_shape(self, shape: Shape, layer: str = "") -> Self:
        self._non_planar_point_count = 0
        attributes = {}
        if layer:
            attributes["layer"] = layer
        for edge in shape.edges():
            self._convert_edge(edge, attributes)
        if self._non_planar_point_count > 0:
            print(f"WARNING, exporting non-planar shape to 2D format.")
            print("  This is probably not what you want.")
            print(f"  {self._non_planar_point_count} points found outside the XY plane.")
        return self

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def write(self, file_name: str):

        # Reset the main CAD viewport of the model space to the
        # extents of its entities.
        # TODO: Expose viewport control to the user.
        # Do the same for ExportSVG.
        zoom.extents(self._msp)

        self._dxf.saveas(file_name)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_point(self, pt: Union[gp_XYZ, gp_Pnt, gp_Vec, Vector]) -> Vec2:
        """Create a Vec2 from a gp_Pnt or Vector.
        This method also checks for points z != 0."""
        if isinstance(pt, (gp_XYZ, gp_Pnt, gp_Vec)):
            (x, y, z) = (pt.X(), pt.Y(), pt.Z())
        elif isinstance(pt, Vector):
            (x, y, z) = pt.to_tuple()
        else:
            raise TypeError(f"Expected `gp_Pnt`, `gp_XYZ`, `gp_Vec`, or `Vector`.  Got `{type(pt).__name__}`.")
        if abs(z) > 1e-6:
            self._non_planar_point_count += 1
        return Vec2(x, y)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_line(self, edge: Edge, attribs: dict):
        self._msp.add_line(
            self._convert_point(edge.start_point()),
            self._convert_point(edge.end_point()),
            attribs,
        )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_circle(self, edge: Edge, attribs: dict):
        geom = edge._geom_adaptor()
        circ = geom.Circle()
        radius = circ.Radius()
        center_location = circ.Location()

        circle_direction_y = circ.YAxis().Direction()
        circle_direction_z = circ.Axis().Direction()

        phi = circle_direction_y.AngleWithRef(gp_Dir(0, 1, 0), circle_direction_z)

        if circle_direction_z.XYZ().Z() > 0:
            angle1 = degrees(geom.FirstParameter() - phi)
            angle2 = degrees(geom.LastParameter() - phi)
        else:
            angle1 = -degrees(geom.LastParameter() - phi) + 180
            angle2 = -degrees(geom.FirstParameter() - phi) + 180

        c = self._convert_point(center_location)
        if edge.is_closed():
            self._msp.add_circle(c, radius, attribs)
        else:
            self._msp.add_arc(c, radius, angle1, angle2, attribs)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_ellipse(self, edge: Edge, attribs: dict):
        geom = edge._geom_adaptor()
        ellipse = geom.Ellipse()
        minor_radius = ellipse.MinorRadius()
        major_radius = ellipse.MajorRadius()
        center = ellipse.Location()
        major_axis = major_radius * gp_Vec(ellipse.XAxis().Direction())
        main_dir = ellipse.Axis().Direction()
        if main_dir.Z() > 0:
            start = geom.FirstParameter()
            end   = geom.LastParameter()
        else:
            start = -geom.LastParameter()
            end   = -geom.FirstParameter()
        self._msp.add_ellipse(
            self._convert_point(center),
            self._convert_point(major_axis),
            minor_radius / major_radius,
            start,
            end,
            attribs,
        )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_bspline(self, edge: Edge, attribs):

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
            curve, u1, u2,
            Export2D.PARAMETRIC_TOLERANCE,
        )

        # need to apply the transform on the geometry level
        t = edge.location.wrapped.Transformation()
        spline.Transform(t)

        order = spline.Degree() + 1
        knots = list(spline.KnotSequence())
        poles = [
            self._convert_point(p)
            for p in spline.Poles()
        ]
        weights = (
            [spline.Weight(i) for i in range(1, spline.NbPoles() + 1)]
            if spline.IsRational()
            else None
        )

        if spline.IsPeriodic():
            pad = spline.NbKnots() - spline.LastUKnotIndex()
            poles += poles[:pad]

        dxf_spline = ezdxf.math.BSpline(poles, order, knots, weights)

        self._msp.add_spline(dxfattribs=attribs).apply_construction_tool(dxf_spline)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_other(self, edge: Edge, attribs: dict):
        self._convert_bspline(edge, attribs)
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    _CONVERTER_LOOKUP = {
        GeomType.LINE.name: _convert_line,
        GeomType.CIRCLE.name: _convert_circle,
        GeomType.ELLIPSE.name: _convert_ellipse,
        GeomType.BSPLINE.name: _convert_bspline,
    }

    def _convert_edge(self, edge: Edge, attribs: dict):
        geom_type = edge.geom_type()
        if False and geom_type not in self._CONVERTER_LOOKUP:
            article = "an" if geom_type[0] in "AEIOU" else "a"
            print(f"Hey neat, {article} {geom_type}!")
        convert = self._CONVERTER_LOOKUP.get(geom_type, ExportDXF._convert_other)
        convert(self, edge, attribs)
    
# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------

class ExportSVG(Export2D):
    """SVG file export functionality."""

    Converter = Callable[[Edge], ET.Element]

    # Scale factor to convert from linetype units (1/10 inch).
    LTYPE_SCALE = {
        Unit.INCH: 0.1,
        Unit.FOOT: 0.1/12,
        Unit.MILLIMETER: 2.54,
        Unit.CENTIMETER: 0.254,
        Unit.METER: 0.00254,
    }

    class Layer(object):
        def __init__(
            self,
            name: str,
            color: ColorIndex,
            line_weight: float,
            line_type: LineType,
        ):
            self.name = name
            self.color = color
            self.line_weight = line_weight
            self.line_type = line_type
            self.elements: List[ET.Element] = []
        
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def __init__(
        self,
        unit: Unit = Unit.MILLIMETER,
        scale: float = 1,
        margin: float = 0,
        fit_to_stroke: bool = False,
        precision: int = 6,
    ):
        self.unit = unit
        self.scale = scale
        self.margin = margin
        self.fit_to_stroke = fit_to_stroke
        self.precision = precision
        self._non_planar_point_count = 0
        self._layers: Dict[str, ExportSVG.Layer] = {}
        self._bounds: BoundingBox = None
        self._UNIT_STRING = {
            Unit.CENTIMETER: 'cm',
            Unit.MILLIMETER: 'mm',
        }

        # Add the default layer.
        self.add_layer("")

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def add_layer(
        self,
        name: str,
        *,
        color: ColorIndex = Export2D.DEFAULT_COLOR_INDEX,
        line_weight: float = Export2D.DEFAULT_LINE_WEIGHT,
        line_type: LineType = Export2D.DEFAULT_LINE_TYPE,
    ) -> Self:
        if name in self._layers:
            raise ValueError(f"Duplicate layer name '{name}'.")
        if line_type.value not in Export2D.LINETYPE_DEFS:
            raise ValueError(f"Unknow linetype `{line_type.value}`.")
        layer = ExportSVG.Layer(
            name = name,
            color = color,
            line_weight = line_weight,
            line_type = line_type,
        )
        self._layers[name] = layer
        return self

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def add_shape(self, shape: Shape, layer: str = ''):
        self._non_planar_point_count = 0
        if layer not in self._layers:
            raise ValueError(f"Undefined layer: {layer}.")
        layer = self._layers[layer]
        bb = shape.bounding_box()
        self._bounds = self._bounds.add(bb) if self._bounds else bb
        elements = [
            self._convert_edge(edge)
            for edge in shape.edges()
        ]
        layer.elements.extend(elements)
        if self._non_planar_point_count > 0:
            print(f"WARNING, exporting non-planar shape to 2D format.")
            print("  This is probably not what you want.")
            print(f"  {self._non_planar_point_count} points found outside the XY plane.")

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def path_point(self, pt: Union[gp_Pnt, Vector]) -> complex:
        """Create a complex point from a gp_Pnt or Vector.
        We are using complex because that is what svgpathtools wants.
        This method also checks for points z != 0."""
        if isinstance(pt, gp_Pnt):
            xyz = pt.X(), pt.Y(), pt.Z()
        elif isinstance(pt, Vector):
            xyz = pt.X, pt.Y, pt.Z
        else:
            raise TypeError(f"Expected `gp_Pnt` or `Vector`.  Got `{type(pt).__name__}`.")
        x, y, z = tuple(round(v, self.precision) for v in xyz)
        if z != 0:
            self._non_planar_point_count += 1
        return complex(x, y)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_line(self, edge: Edge) -> ET.Element:
        p0 = self.path_point(edge @ 0)
        p1 = self.path_point(edge @ 1)
        result = ET.Element('line', {
            'x1': str(p0.real), 'y1': str(p0.imag),
            'x2': str(p1.real), 'y2': str(p1.imag)
        })
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_circle(self, edge: Edge) -> ET.Element:
        geom = edge._geom_adaptor()
        circle = geom.Circle()
        radius = circle.Radius()
        center = circle.Location()

        if edge.is_closed():
            c = self.path_point(center)
            result = ET.Element('circle', {
                'cx': str(c.real), 'cy': str(c.imag),
                'r': str(radius)
            })
        else:
            circle_direction_y = circle.YAxis().Direction()
            circle_direction_z = circle.Axis().Direction()
            phi = circle_direction_y.AngleWithRef(gp_Dir(0, 1, 0), circle_direction_z)
            u0 = geom.FirstParameter()
            u1 = geom.LastParameter()
            ccw = circle_direction_z.XYZ().Z() > 0
            if ccw:
                angle1 = degrees(u0 - phi)
                angle2 = degrees(u1 - phi)
            else:
                angle1 = -degrees(u1 - phi) + 180
                angle2 = -degrees(u0 - phi) + 180
            start = geom.Value(u0)
            end = geom.Value(u1)

            # TODO: make a path with an Arc segment.
            # TODO later: collect all the edges of a wire into a single path.
            path = PT.Path()
            result = ('path', {'d': path.d()})
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_bspline(self, edge: Edge) -> ET.Element:

        # This reduces the B-Spline to degree 3, generally adding
        # poles and knots to approximate the original.
        # This also will convert basically any edge into a B-Spline.
        edge = edge.to_splines()

        # This pulls the underlying Geom_BSplineCurve out of the Edge.
        # The adaptor also supplies a parameter range for the curve.
        # TODO: I need to understand better the what and why here.
        adaptor = edge._geom_adaptor()
        spline = adaptor.Curve().Curve()
        u1 = adaptor.FirstParameter()
        u2 = adaptor.LastParameter()

        # Apply the shape location to the geometry.
        t = edge.location.wrapped.Transformation()
        spline.Transform(t)
        # describe_bspline(spline)

        # Convert the B-Spline to Bezier curves.
        # From the OCCT 7.6.0 documentation:
        # > Note: ParametricTolerance is not used.
        converter = GeomConvert_BSplineCurveToBezierCurve(
            spline, u1, u2, Export2D.PARAMETRIC_TOLERANCE
        )

        def make_segment(bezier: Geom_BezierCurve) -> Union[PT.Line, PT.QuadraticBezier, PT.CubicBezier]:
            p = [self.path_point(p) for p in bezier.Poles()]
            if len(p) == 2:
                result = PT.Line(start=p[0], end=p[1])
            elif len(p) == 3:
                result = PT.QuadraticBezier(start=p[0], control=p[1], end=p[2])
            elif len(p) == 4:
                result = PT.CubicBezier(start=p[0], control1=p[1], control2=p[2], end=p[3])
            else:
                raise ValueError(f"Surprising Bézier of degree {bezier.Degree()}!")
            return result

        segments = [
            make_segment(converter.Arc(i))
            for i in range(1, converter.NbArcs() + 1)
        ]
        path = PT.Path(*segments)
        result = ET.Element('path', {'d': path.d()})
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _convert_other(self, edge: Edge) -> ET.Element:
        # _convert_bspline can actually handle basically anything
        # because it calls Edge.to_splines() first thing.
        return self._convert_bspline(edge)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    _CONVERTER_LOOKUP = {
        GeomType.LINE.name: _convert_line,
        GeomType.CIRCLE.name: _convert_circle,
        GeomType.BSPLINE.name: _convert_bspline,
    }

    def _convert_edge(self, edge: Edge) -> ET.Element:
        geom_type = edge.geom_type()
        if False and geom_type not in self._CONVERTER_LOOKUP:
            article = "an" if geom_type[0] in "AEIOU" else "a"
            print(f"Hey neat, {article} {geom_type}!")
        convert = self._CONVERTER_LOOKUP.get(geom_type, ExportSVG._convert_other)
        result = convert(self, edge)
        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def _group_for_layer(self, layer: Layer, attribs: Dict = {}) -> ET.Element:
        (r, g, b) = (
            (0, 0, 0) if layer.color == ColorIndex.BLACK
            else aci2rgb(layer.color.value)
        )
        stroke_width = layer.line_weight
        result = ET.Element('g', attribs | {
            'stroke'      : f"rgb({r},{g},{b})",
            'stroke-width': f"{stroke_width}",
            'fill'        : "none",
        })
        if layer.name:
            result.set('id', layer.name)

        if layer.line_type is not LineType.CONTINUOUS:
            ltname = layer.line_type.value
            _, pattern = Export2D.LINETYPE_DEFS[ltname]
            scale = ExportSVG.LTYPE_SCALE[self.unit]
            dash_array = [
                f"{round(scale * abs(e), self.precision)}"
                for e in pattern[1:]
            ]
            result.set('stroke-dasharray', ' '.join(dash_array))
        
        for element in layer.elements:
            result.append(element)

        return result

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def write(self, path: str):

        bb = self._bounds
        margin = self.margin
        if self.fit_to_stroke:
            max_line_weight = max(
                l.line_weight
                for l in self._layers.values()
            )
            margin += max_line_weight / 2
        view_left   = round(+bb.min.X - margin, self.precision)
        view_top    = round(-bb.max.Y - margin, self.precision)
        view_width  = round(bb.size.X + 2 * margin, self.precision)
        view_height = round(bb.size.Y + 2 * margin, self.precision)
        view_box = [str(f) for f in [view_left, view_top, view_width, view_height]]
        doc_width = round(view_width * self.scale, self.precision)
        doc_height = round(view_height * self.scale, self.precision)
        doc_unit = self._UNIT_STRING.get(self.unit, '')
        svg = ET.Element('svg', {
            'width'  : f"{doc_width}{doc_unit}",
            'height' : f"{doc_height}{doc_unit}",
            'viewBox': " ".join(view_box),
            'version': "1.1",
            'xmlns'  : "http://www.w3.org/2000/svg",
        })

        container_group = ET.Element('g', {
            'transform'     : f"scale(1,-1)",
            'stroke-linecap': "round",
        })
        svg.append(container_group)
        
        for _, layer in self._layers.items():
            layer_group = self._group_for_layer(layer)
            container_group.append(layer_group)

        xml = ET.ElementTree(svg)
        ET.indent(xml, '  ')
        xml.write(
            path,
            encoding='utf-8',
            xml_declaration=True,
            default_namespace=False
        )
