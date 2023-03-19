# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error

from build123d import *
from build123d import Shape
from OCP.GeomConvert import GeomConvert_BSplineCurveToBezierCurve #type: ignore
from OCP.Geom import Geom_BSplineCurve #type: ignore
from OCP.gp import gp_Dir, gp_Pnt #type: ignore
from math import degrees
from typing import Callable, List, Any
from typing_extensions import Self
from svgpathtools import CubicBezier, Path
from xml.etree.ElementTree import Element, ElementTree, indent
from enum import Enum, auto
import ezdxf

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class Drawing(object):

    def __init__(self):
        pass
    
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

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class Exporter2D(object):
    """Base class for 2D exporters (DXF, SVG)."""

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class SVG(Exporter2D):
    """SVG file export functionality."""

    Converter = Callable[[Edge], Element]

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
        self._elements: List[SVG.Element] = []
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
        color: int = 7,
        linetype: str = "CONTINUOUS"
    ) -> Self:
        pass

    def add_shape(self, shape: Shape):
        bb = shape.bounding_box()
        self._bounds = self._bounds.add(bb) if self._bounds else bb
        for edge in shape.edges():
            convert = self._get_converter(edge)
            element = convert(edge)
            self._elements.append(element)
        if self._non_planar_point_count > 0:
            print(f"WARNING, exporting non-planar shape to 2D format.")
            print("  This is probably not what you want.")
            print(f"  {self._non_planar_point_count} points found outside the XY plane.")

    def path_point(self, gp_pnt: gp_Pnt) -> complex:
        """Create a complex point from a gp_Pnt.
        We are using complex because that is what svgpathtools wants.
        This method also checks for points z != 0."""
        x = round(gp_pnt.X(), self.precision)
        y = round(gp_pnt.Y(), self.precision)
        z = round(gp_pnt.Z(), self.precision)
        if z != 0:
            self._non_planar_point_count += 1
        return complex(x, y)

    def _get_converter(self, edge: Edge) -> Converter:
        key = edge.geom_type()
        result = self._CONVERTER_LOOKUP.get(key, self._convert_other)
        return result

    def _convert_line(self, edge: Edge) -> Element:
        p0 = self.path_point(edge @ 0)
        p1 = self.path_point(edge @ 1)
        result = Element('line', {
            'x1': str(p0.real), 'y1': str(p0.imag),
            'x2': str(p1.real), 'y2': str(p1.imag)
        })
        return result

    def _convert_circle(self, edge: Edge) -> Element:
        geom = edge._geom_adaptor()
        circle = geom.Circle()
        radius = circle.Radius()
        center = circle.Location()

        if edge.is_closed():
            c = self.path_point(center)
            result = Element('circle', {
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
            path = Path()
            result = ('path', {'d': path.d()})
        return result

    def _convert_bspline(self, edge: Edge) -> Element:

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
        # It also possibly converts other shapes to B-Spline?
        # Probably, yes.  I tried it with circles, and it produced splines.
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
        
        path_parts = [
            [self.path_point(p) for p in converter.Arc(i).Poles()]
            for i in range(1, converter.NbArcs() + 1)
        ]
        segments = [
            CubicBezier(start=p[0], control1=p[1], control2=p[2], end=p[3])
            for p in path_parts
        ]
        path = Path(*segments)
        result = Element('path', {'d': path.d()})
        return result


    def _convert_other(self, edge: Edge) -> Element:
        return self._convert_bspline(edge)

    def write(self, path: str):

        bb = self._bounds
        margin = self.margin
        view_left   = round(+bb.min.X - margin, self.precision)
        view_top    = round(-bb.max.Y - margin, self.precision)
        view_width  = round(bb.size.X + 2 * margin, self.precision)
        view_height = round(bb.size.Y + 2 * margin, self.precision)
        view_box = [str(f) for f in [view_left, view_top, view_width, view_height]]
        doc_width = round(bb.size.X * self.scale, self.precision)
        doc_height = round(bb.size.Y * self.scale, self.precision)
        doc_unit = self._UNIT_STRING.get(self.unit, '')
        svg = Element('svg', {
            'width'  : f"{doc_width}{doc_unit}",
            'height' : f"{doc_height}{doc_unit}",
            'viewBox': " ".join(view_box),
            'version': "1.1",
            'xmlns'  : "http://www.w3.org/2000/svg",
        })
        group = Element('g', {
            'transform'   : f"scale(1,-1) translate({margin},{margin})",
            'stroke'      : "black",
            'stroke-width': "1px",
            'fill'        : "none",
        })
        svg.append(group)
        for element in self._elements:
            group.append(element)        
        xml = ElementTree(svg)
        indent(xml, '  ')
        xml.write(
            path,
            encoding='utf-8',
            xml_declaration=True,
            default_namespace=False
        )



