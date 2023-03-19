# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error

from build123d import *
from build123d import Shape
from OCP.GeomConvert import GeomConvert_BSplineCurveToBezierCurve #type: ignore
from OCP.Geom import Geom_BSplineCurve, Geom_BezierCurve #type: ignore
from OCP.gp import gp_Dir, gp_Pnt, gp_Ax2 #type: ignore
from OCP.BRepLib import BRepLib #type: ignore
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape #type: ignore
from OCP.HLRAlgo import HLRAlgo_Projector #type: ignore
from math import degrees
from typing import Callable, List, Union, Tuple, Dict
from typing_extensions import Self
import svgpathtools as PT
import xml.etree.ElementTree as ET
from enum import Enum, auto
from ezdxf.colors import aci2rgb
from ezdxf.tools.standards import ANSI_LINE_TYPES, ISO_LTYPE_FACTOR

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class Drawing(object):

    def __init__(
        self,
        shape: Shape,
        *,
        projection_dir: VectorLike = (-1.75, 1.1, 5),
        width: float = 297, # landscape A4 width in mm
        height: float = 210, # landscape A4 height in mm
        margins: Union[None, float, Tuple[float, float, float, float]] = None,
        show_axes: bool = True,
        stroke_width: float = None,
        stroke_color: Color = Color('black'),
        hidden_color: Color = Color('gray'),
        show_hidden: bool = True,
        focus: Union[float, None] = None,
    ):

        # need to guess the scale and the coordinate center
        uom = 'mm'

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
        if show_hidden:

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
        all_lines = [self.visible_lines, self.hidden_lines]
        # get bounding box -- these are all in 2D space
        bb = Compound.make_compound(all_lines).bounding_box()


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

class ColorIndex(Enum):
    RED = 1
    YELLOW = 2
    GREEN = 3
    CYAN = 4
    BLUE = 5
    MAGENTA = 6
    BLACK = 7
    DARK_GRAY = 8
    LIGHT_GRAY = 9

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class Exporter2D(object):
    """Base class for 2D exporters (DXF, SVG)."""

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class SVG(Exporter2D):
    """SVG file export functionality."""

    Converter = Callable[[Edge], ET.Element]
    DEFAULT_COLOR_INDEX = ColorIndex.BLACK
    DEFAULT_LINE_WEIGHT = 0.09
    DEFAULT_LINE_TYPE = LineType.CONTINUOUS

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
        self._layers: Dict[str, SVG.Layer] = {}
        self._default_layer = SVG.Layer(
            name="default",
            color=SVG.DEFAULT_COLOR_INDEX,
            line_weight=SVG.DEFAULT_LINE_WEIGHT,
            line_type=SVG.DEFAULT_LINE_TYPE,
        )
        self._bounds: BoundingBox = None
        self._CONVERTER_LOOKUP = {
            GeomType.LINE.name: self._convert_line,
            GeomType.CIRCLE.name: self._convert_circle,
            GeomType.BSPLINE.name: self._convert_bspline,
        }
        self._UNIT_STRING = {
            Unit.CENTIMETER: 'cm',
            Unit.MILLIMETER: 'mm',
        }

    def add_layer(
        self,
        name: str,
        *,
        color: ColorIndex = DEFAULT_COLOR_INDEX,
        line_weight: float = DEFAULT_LINE_WEIGHT,
        line_type: LineType = DEFAULT_LINE_TYPE,
    ) -> Self:
        if name in self._layers:
            raise ValueError(f"Duplicate layer name '{name}'.")
        layer = SVG.Layer(
            name = name,
            color = color,
            line_weight = line_weight,
            line_type = line_type,
        )
        self._layers[name] = layer

    def add_shape(self, shape: Shape, layer: str = None):
        if layer is not None and layer not in self._layers:
            raise ValueError(f"Undefined layer: {layer}.")
        layer = self._layers.get(layer, self._default_layer)
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

    def _convert_edge(self, edge: Edge) -> ET.Element:
        convert = self._CONVERTER_LOOKUP.get(edge.geom_type(), self._convert_other)
        result = convert(edge)
        return result

    def _convert_line(self, edge: Edge) -> ET.Element:
        p0 = self.path_point(edge @ 0)
        p1 = self.path_point(edge @ 1)
        result = ET.Element('line', {
            'x1': str(p0.real), 'y1': str(p0.imag),
            'x2': str(p1.real), 'y2': str(p1.imag)
        })
        return result

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

    def _convert_bspline(self, edge: Edge) -> ET.Element:

        def describe_bspline(bspline: Geom_BSplineCurve):
            degree = bspline.Degree()
            distribution = bspline.KnotDistribution()
            rational = "Rational" if bspline.IsRational() else "Non-rational"
            pole_z = [
                abs(round(p.Z(), 6)) != 0
                for p in spline.Poles()
            ]
            planar = "non-planar" if any(pole_z) else "planar"
            print(f"\n{distribution} {rational} {planar} B-Spline of degree {degree}")
        
        # This reduces the degree of the B-Spline to 3.
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
        # > The Tolerance criterion is ParametricTolerance.
        # > Raised if Abs (U2 - U1) <= ParametricTolerance. 
        # So, I think the parameter is not used, but *if* it were used,
        # it would need to be no smaller than Abs(U2-U1).
        converter = GeomConvert_BSplineCurveToBezierCurve(
            spline, u1, u2, abs(u2-u1)
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


    def _convert_other(self, edge: Edge) -> ET.Element:
        # _convert_bspline can actually handle basically anything
        # because it calls Edge.to_splines() first thing.
        return self._convert_bspline(edge)

    def _group_for_layer(self, layer: Layer, attribs: Dict = {}) -> ET.Element:
        (r, g, b) = (
            (0, 0, 0) if layer.color == ColorIndex.BLACK
            else aci2rgb(layer.color.value)
        )
        stroke_width = layer.line_weight
        result = ET.Element('g', attribs | {
            'stroke'      : f"rgb({r},{g},{b})",
            'stroke-width': f"{stroke_width}mm",
            'fill'        : "none",
        })
        if layer.name:
            result.set('id', layer.name)

        # Search the ezdxf standard line types.
        # The line type records are tuples of
        #   (name:str, description:str, pattern:List[float]).
        if layer.line_type is not LineType.CONTINUOUS:
            line_type = layer.line_type.name
            ansi_line_type = next(filter(lambda lt: lt[0] == line_type, ANSI_LINE_TYPES))
            pattern_elements = ansi_line_type[2]
            pattern_length = pattern_elements[0]
            dash_array = [
                f"{round(ISO_LTYPE_FACTOR * abs(e), self.precision)}mm"
                for e in pattern_elements[1:]
            ]
            result.set('stroke-dasharray', ' '.join(dash_array))
        
        for element in layer.elements:
            result.append(element)

        return result

    def write(self, path: str):

        bb = self._bounds
        margin = self.margin
        if self.fit_to_stroke:
            max_line_weight = max(
                l.line_weight
                for l in [self._default_layer, *(self._layers.values())]
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

        container_attributes = {
            'transform'     : f"scale(1,-1)",
            'stroke-linecap': "round",
        }
        if self._layers:
            # Has named layers, put default layer and named layers
            # inside container group.
            container_group = ET.Element('g', container_attributes)
            default_layer_group = self._group_for_layer(self._default_layer)
            container_group.append(default_layer_group)
        else:
            # No named layers, use default layer as container group.
            default_layer_group = self._group_for_layer(self._default_layer, container_attributes)
            container_group = default_layer_group

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



