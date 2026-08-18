"""Tests for Edge.geom_equal and Wire.geom_equal methods."""

import pytest
from build123d import (
    Vertex,
    Edge,
    Wire,
    Spline,
    Rectangle,
    Circle,
    Ellipse,
    Bezier,
    GeomType,
    Location,
    Plane,
)


class TestEdgeGeomEqualLine:
    """Tests for Edge.geom_equal with LINE type."""

    def test_same_line(self):
        e1 = Edge.make_line((0, 0, 0), (1, 1, 1))
        e2 = Edge.make_line((0, 0, 0), (1, 1, 1))
        assert e1.geom_type == GeomType.LINE
        assert e1.geom_equal(e2)

    def test_different_line(self):
        e1 = Edge.make_line((0, 0, 0), (1, 1, 1))
        e2 = Edge.make_line((0, 0, 0), (1, 1, 2))
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualCircle:
    """Tests for Edge.geom_equal with CIRCLE type."""

    def test_same_circle(self):
        c1 = Circle(10)
        c2 = Circle(10)
        e1 = c1.edge()
        e2 = c2.edge()
        assert e1.geom_type == GeomType.CIRCLE
        assert e1.geom_equal(e2)

    def test_different_radius(self):
        c1 = Circle(10)
        c2 = Circle(11)
        e1 = c1.edge()
        e2 = c2.edge()
        assert not e1.geom_equal(e2)

    def test_same_arc(self):
        e1 = Edge.make_circle(10, start_angle=0, end_angle=90)
        e2 = Edge.make_circle(10, start_angle=0, end_angle=90)
        assert e1.geom_equal(e2)

    def test_different_arc_angle(self):
        e1 = Edge.make_circle(10, start_angle=0, end_angle=90)
        e2 = Edge.make_circle(10, start_angle=0, end_angle=180)
        assert not e1.geom_equal(e2)

    def test_different_circle_from_revolve(self):
        """Two circles with same radius/endpoints but different center/axis."""
        from build123d import Axis, Line, RadiusArc, make_face, revolve

        f1 = make_face(RadiusArc((5, 0), (-5, 0), 15) + Line((5, 0), (-5, 0)))
        p1 = revolve(f1, Axis.X, 90)
        value1, value2 = p1.edges().filter_by(GeomType.CIRCLE)
        value2 = value2.reversed()
        # These circles have same endpoints after reversal but different center/axis
        assert not value1.geom_equal(value2)

    def test_different_location(self):
        """Circles with same radius but different center location."""
        e1 = Edge.make_circle(10)
        e2 = Edge.make_circle(10).locate(Location((5, 0, 0)))
        assert not e1.geom_equal(e2)

    def test_same_location(self):
        """Circles with same radius and same non-origin location."""
        e1 = Edge.make_circle(10).locate(Location((5, 5, 0)))
        e2 = Edge.make_circle(10).locate(Location((5, 5, 0)))
        assert e1.geom_equal(e2)

    def test_different_axis(self):
        """Circles with same radius but different axis direction."""
        e1 = Edge.make_circle(10, plane=Plane.XY)
        e2 = Edge.make_circle(10, plane=Plane.XZ)
        assert not e1.geom_equal(e2)

    def test_same_axis(self):
        """Circles with same radius and same non-default axis."""
        e1 = Edge.make_circle(10, plane=Plane.YZ)
        e2 = Edge.make_circle(10, plane=Plane.YZ)
        assert e1.geom_equal(e2)


class TestEdgeGeomEqualEllipse:
    """Tests for Edge.geom_equal with ELLIPSE type."""

    def test_same_ellipse(self):
        el1 = Ellipse(10, 5)
        el2 = Ellipse(10, 5)
        e1 = el1.edge()
        e2 = el2.edge()
        assert e1.geom_type == GeomType.ELLIPSE
        assert e1.geom_equal(e2)

    def test_different_major_radius(self):
        el1 = Ellipse(10, 5)
        el2 = Ellipse(11, 5)
        e1 = el1.edge()
        e2 = el2.edge()
        assert not e1.geom_equal(e2)

    def test_different_minor_radius(self):
        el1 = Ellipse(10, 5)
        el2 = Ellipse(10, 6)
        e1 = el1.edge()
        e2 = el2.edge()
        assert not e1.geom_equal(e2)

    def test_different_location(self):
        """Ellipses with same radii but different center location."""
        e1 = Edge.make_ellipse(10, 5)
        e2 = Edge.make_ellipse(10, 5).locate(Location((5, 0, 0)))
        assert not e1.geom_equal(e2)

    def test_same_location(self):
        """Ellipses with same radii and same non-origin location."""
        e1 = Edge.make_ellipse(10, 5).locate(Location((5, 5, 0)))
        e2 = Edge.make_ellipse(10, 5).locate(Location((5, 5, 0)))
        assert e1.geom_equal(e2)

    def test_different_axis(self):
        """Ellipses with same radii but different axis direction."""
        e1 = Edge.make_ellipse(10, 5, plane=Plane.XY)
        e2 = Edge.make_ellipse(10, 5, plane=Plane.XZ)
        assert not e1.geom_equal(e2)

    def test_same_axis(self):
        """Ellipses with same radii and same non-default axis."""
        e1 = Edge.make_ellipse(10, 5, plane=Plane.YZ)
        e2 = Edge.make_ellipse(10, 5, plane=Plane.YZ)
        assert e1.geom_equal(e2)


class TestEdgeGeomEqualHyperbola:
    """Tests for Edge.geom_equal with HYPERBOLA type."""

    def test_same_hyperbola(self):
        e1 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45)
        e2 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45)
        assert e1.geom_type == GeomType.HYPERBOLA
        assert e1.geom_equal(e2)

    def test_different_x_radius(self):
        e1 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45)
        e2 = Edge.make_hyperbola(11, 5, start_angle=-45, end_angle=45)
        assert not e1.geom_equal(e2)

    def test_different_y_radius(self):
        e1 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45)
        e2 = Edge.make_hyperbola(10, 6, start_angle=-45, end_angle=45)
        assert not e1.geom_equal(e2)

    def test_different_location(self):
        """Hyperbolas with same radii but different center location."""
        e1 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45)
        e2 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45).locate(
            Location((5, 0, 0))
        )
        assert not e1.geom_equal(e2)

    def test_same_location(self):
        """Hyperbolas with same radii and same non-origin location."""
        e1 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45).locate(
            Location((5, 5, 0))
        )
        e2 = Edge.make_hyperbola(10, 5, start_angle=-45, end_angle=45).locate(
            Location((5, 5, 0))
        )
        assert e1.geom_equal(e2)

    def test_different_axis(self):
        """Hyperbolas with same radii but different axis direction."""
        e1 = Edge.make_hyperbola(10, 5, plane=Plane.XY, start_angle=-45, end_angle=45)
        e2 = Edge.make_hyperbola(10, 5, plane=Plane.XZ, start_angle=-45, end_angle=45)
        assert not e1.geom_equal(e2)

    def test_same_axis(self):
        """Hyperbolas with same radii and same non-default axis."""
        e1 = Edge.make_hyperbola(10, 5, plane=Plane.YZ, start_angle=-45, end_angle=45)
        e2 = Edge.make_hyperbola(10, 5, plane=Plane.YZ, start_angle=-45, end_angle=45)
        assert e1.geom_equal(e2)


class TestEdgeGeomEqualParabola:
    """Tests for Edge.geom_equal with PARABOLA type."""

    def test_same_parabola(self):
        e1 = Edge.make_parabola(5, start_angle=0, end_angle=60)
        e2 = Edge.make_parabola(5, start_angle=0, end_angle=60)
        assert e1.geom_type == GeomType.PARABOLA
        assert e1.geom_equal(e2)

    def test_different_focal_length(self):
        e1 = Edge.make_parabola(5, start_angle=0, end_angle=60)
        e2 = Edge.make_parabola(6, start_angle=0, end_angle=60)
        assert not e1.geom_equal(e2)

    def test_different_location(self):
        """Parabolas with same focal length but different vertex location."""
        e1 = Edge.make_parabola(5, start_angle=0, end_angle=60)
        e2 = Edge.make_parabola(5, start_angle=0, end_angle=60).locate(
            Location((5, 0, 0))
        )
        assert not e1.geom_equal(e2)

    def test_same_location(self):
        """Parabolas with same focal length and same non-origin location."""
        e1 = Edge.make_parabola(5, start_angle=0, end_angle=60).locate(
            Location((5, 5, 0))
        )
        e2 = Edge.make_parabola(5, start_angle=0, end_angle=60).locate(
            Location((5, 5, 0))
        )
        assert e1.geom_equal(e2)

    def test_different_axis(self):
        """Parabolas with same focal length but different axis direction."""
        e1 = Edge.make_parabola(5, plane=Plane.XY, start_angle=0, end_angle=60)
        e2 = Edge.make_parabola(5, plane=Plane.XZ, start_angle=0, end_angle=60)
        assert not e1.geom_equal(e2)

    def test_same_axis(self):
        """Parabolas with same focal length and same non-default axis."""
        e1 = Edge.make_parabola(5, plane=Plane.YZ, start_angle=0, end_angle=60)
        e2 = Edge.make_parabola(5, plane=Plane.YZ, start_angle=0, end_angle=60)
        assert e1.geom_equal(e2)


class TestEdgeGeomEqualBezier:
    """Tests for Edge.geom_equal with BEZIER type."""

    def test_same_bezier(self):
        pts = [(0, 0), (1, 1), (2, 0)]
        b1 = Bezier(*pts)
        b2 = Bezier(*pts)
        e1 = b1.edge()
        e2 = b2.edge()
        assert e1.geom_type == GeomType.BEZIER
        assert e1.geom_equal(e2)

    def test_different_bezier(self):
        b1 = Bezier((0, 0), (1, 1), (2, 0))
        b2 = Bezier((0, 0), (1, 2), (2, 0))
        e1 = b1.edge()
        e2 = b2.edge()
        assert not e1.geom_equal(e2)

    def test_different_degree(self):
        """Bezier curves with different degrees (different number of control points)."""
        # Quadratic (degree 2, 3 points)
        b1 = Bezier((0, 0), (1, 1), (2, 0))
        # Cubic (degree 3, 4 points) - adjusted to have same endpoints
        b2 = Bezier((0, 0), (0.5, 1), (1.5, 1), (2, 0))
        e1 = b1.edge()
        e2 = b2.edge()
        assert e1.geom_type == GeomType.BEZIER
        assert e2.geom_type == GeomType.BEZIER
        assert not e1.geom_equal(e2)

    def test_rational_bezier_different_weights(self):
        """Rational Bezier curves with different weights."""
        pts = [(0, 0, 0), (1, 1, 0), (2, 0, 0)]

        # Create rational Bezier with weights [1, 2, 1]
        e1 = Edge.make_bezier(*pts, weights=[1.0, 2.0, 1.0])

        # Create rational Bezier with weights [1, 3, 1]
        e2 = Edge.make_bezier(*pts, weights=[1.0, 3.0, 1.0])

        assert e1.geom_type == GeomType.BEZIER
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualBSpline:
    """Tests for Edge.geom_equal with BSPLINE type."""

    def test_same_spline(self):
        v = [Vertex(p) for p in ((-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0))]
        s1 = Spline(*v)
        s2 = Spline(*v)
        e1 = s1.edge()
        e2 = s2.edge()
        assert e1.geom_type == GeomType.BSPLINE
        assert e1.geom_equal(e2)

    def test_different_spline(self):
        v1 = [Vertex(p) for p in ((-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0))]
        v2 = [Vertex(p) for p in ((-2, 0), (-1, 1), (0, 0), (1, 0), (2, 0))]
        s1 = Spline(*v1)
        s2 = Spline(*v2)
        e1 = s1.edge()
        e2 = s2.edge()
        assert not e1.geom_equal(e2)

    def test_complex_spline(self):
        v = [
            Vertex(p)
            for p in (
                (-2, 0),
                (-1, 0),
                (0, 0),
                (1, 0),
                (2, 0),
                (3, 0.1),
                (4, 1),
                (5, 2.2),
                (6, 3),
                (7, 2),
                (8, -1),
            )
        ]
        s1 = Spline(*v)
        s2 = Spline(*v)
        e1 = s1.edge()
        e2 = s2.edge()
        assert e1.geom_equal(e2)

    def test_different_periodicity(self):
        """BSplines with different periodicity (periodic vs non-periodic)."""
        # Same control points, different periodicity
        pts = [(0, 0), (1, 1), (2, 0), (1, -1)]

        e1 = Edge.make_spline(pts, periodic=False)
        e2 = Edge.make_spline(pts, periodic=True)

        assert e1.geom_type == GeomType.BSPLINE
        assert e2.geom_type == GeomType.BSPLINE
        # Different periodicity means not equal
        assert not e1.geom_equal(e2)

    def test_different_pole_count(self):
        """BSplines with different number of poles."""
        # 5 points
        v1 = [Vertex(p) for p in ((0, 0), (1, 1), (2, 0), (3, 1), (4, 0))]
        # 6 points with same endpoints
        v2 = [
            Vertex(p)
            for p in ((0, 0), (0.8, 0.8), (1.6, 0.2), (2.4, 0.8), (3.2, 0.2), (4, 0))
        ]
        s1 = Spline(*v1)
        s2 = Spline(*v2)
        e1 = s1.edge()
        e2 = s2.edge()
        assert e1.geom_type == GeomType.BSPLINE
        assert e2.geom_type == GeomType.BSPLINE
        assert not e1.geom_equal(e2)

    def test_different_knot_values(self):
        """BSplines with different internal knot positions have different shapes."""
        from OCP.Geom import Geom_BSplineCurve
        from OCP.TColgp import TColgp_Array1OfPnt
        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
        from OCP.gp import gp_Pnt
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge

        # 5 poles for degree 3 with one internal knot
        poles = TColgp_Array1OfPnt(1, 5)
        poles.SetValue(1, gp_Pnt(0, 0, 0))
        poles.SetValue(2, gp_Pnt(1, 2, 0))
        poles.SetValue(3, gp_Pnt(2, 2, 0))
        poles.SetValue(4, gp_Pnt(3, 2, 0))
        poles.SetValue(5, gp_Pnt(4, 0, 0))

        mults = TColStd_Array1OfInteger(1, 3)
        mults.SetValue(1, 4)
        mults.SetValue(2, 1)  # Internal knot
        mults.SetValue(3, 4)

        # Internal knot at 0.5
        knots1 = TColStd_Array1OfReal(1, 3)
        knots1.SetValue(1, 0.0)
        knots1.SetValue(2, 0.5)
        knots1.SetValue(3, 1.0)
        curve1 = Geom_BSplineCurve(poles, knots1, mults, 3, False)
        e1 = Edge(BRepBuilderAPI_MakeEdge(curve1).Edge())

        # Internal knot at 0.3 - different position changes shape!
        knots2 = TColStd_Array1OfReal(1, 3)
        knots2.SetValue(1, 0.0)
        knots2.SetValue(2, 0.3)
        knots2.SetValue(3, 1.0)
        curve2 = Geom_BSplineCurve(poles, knots2, mults, 3, False)
        e2 = Edge(BRepBuilderAPI_MakeEdge(curve2).Edge())

        assert e1.geom_type == GeomType.BSPLINE
        # Different internal knot position = different geometric shape
        assert (e1 @ 0.5) != (e2 @ 0.5)
        assert not e1.geom_equal(e2)

    def test_different_multiplicities(self):
        """BSplines with same poles/knots but different multiplicities have different shapes."""
        from OCP.Geom import Geom_BSplineCurve
        from OCP.TColgp import TColgp_Array1OfPnt
        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
        from OCP.gp import gp_Pnt
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge

        # Same 7 poles for both curves
        poles = TColgp_Array1OfPnt(1, 7)
        poles.SetValue(1, gp_Pnt(0, 0, 0))
        poles.SetValue(2, gp_Pnt(1, 2, 0))
        poles.SetValue(3, gp_Pnt(2, 1, 0))
        poles.SetValue(4, gp_Pnt(3, 2, 0))
        poles.SetValue(5, gp_Pnt(4, 1, 0))
        poles.SetValue(6, gp_Pnt(5, 2, 0))
        poles.SetValue(7, gp_Pnt(6, 0, 0))

        # Same 4 knots for both curves
        knots = TColStd_Array1OfReal(1, 4)
        knots.SetValue(1, 0.0)
        knots.SetValue(2, 0.33)
        knots.SetValue(3, 0.67)
        knots.SetValue(4, 1.0)

        # Multiplicities [4, 1, 2, 4] - sum = 11 = 7 + 3 + 1
        mults1 = TColStd_Array1OfInteger(1, 4)
        mults1.SetValue(1, 4)
        mults1.SetValue(2, 1)
        mults1.SetValue(3, 2)
        mults1.SetValue(4, 4)
        curve1 = Geom_BSplineCurve(poles, knots, mults1, 3, False)
        e1 = Edge(BRepBuilderAPI_MakeEdge(curve1).Edge())

        # Multiplicities [4, 2, 1, 4] - same sum, swapped internal mults
        mults2 = TColStd_Array1OfInteger(1, 4)
        mults2.SetValue(1, 4)
        mults2.SetValue(2, 2)
        mults2.SetValue(3, 1)
        mults2.SetValue(4, 4)
        curve2 = Geom_BSplineCurve(poles, knots, mults2, 3, False)
        e2 = Edge(BRepBuilderAPI_MakeEdge(curve2).Edge())

        assert e1.geom_type == GeomType.BSPLINE
        assert e2.geom_type == GeomType.BSPLINE
        # Same poles, same knots, different multiplicities = different shape
        assert (e1 @ 0.5) != (e2 @ 0.5)
        assert not e1.geom_equal(e2)

    def test_rational_bspline_different_weights(self):
        """Rational BSplines with different weights."""
        from OCP.Geom import Geom_BSplineCurve
        from OCP.TColgp import TColgp_Array1OfPnt
        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
        from OCP.gp import gp_Pnt
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge

        poles = TColgp_Array1OfPnt(1, 4)
        poles.SetValue(1, gp_Pnt(0, 0, 0))
        poles.SetValue(2, gp_Pnt(1, 1, 0))
        poles.SetValue(3, gp_Pnt(2, 1, 0))
        poles.SetValue(4, gp_Pnt(3, 0, 0))

        knots = TColStd_Array1OfReal(1, 2)
        knots.SetValue(1, 0.0)
        knots.SetValue(2, 1.0)
        mults = TColStd_Array1OfInteger(1, 2)
        mults.SetValue(1, 4)
        mults.SetValue(2, 4)

        # Weights [1, 2, 2, 1]
        weights1 = TColStd_Array1OfReal(1, 4)
        weights1.SetValue(1, 1.0)
        weights1.SetValue(2, 2.0)
        weights1.SetValue(3, 2.0)
        weights1.SetValue(4, 1.0)
        curve1 = Geom_BSplineCurve(poles, weights1, knots, mults, 3, False)
        e1 = Edge(BRepBuilderAPI_MakeEdge(curve1).Edge())

        # Weights [1, 3, 3, 1]
        weights2 = TColStd_Array1OfReal(1, 4)
        weights2.SetValue(1, 1.0)
        weights2.SetValue(2, 3.0)
        weights2.SetValue(3, 3.0)
        weights2.SetValue(4, 1.0)
        curve2 = Geom_BSplineCurve(poles, weights2, knots, mults, 3, False)
        e2 = Edge(BRepBuilderAPI_MakeEdge(curve2).Edge())

        assert e1.geom_type == GeomType.BSPLINE
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualOffset:
    """Tests for Edge.geom_equal with OFFSET type."""

    def test_same_offset(self):
        v = [Vertex(p) for p in ((0, 0), (1, 1), (2, 0), (3, 1))]
        s = Spline(*v)
        w = Wire([s.edge()])
        offset_wire1 = w.offset_2d(0.1)
        offset_wire2 = w.offset_2d(0.1)

        offset_edges1 = [
            e for e in offset_wire1.edges() if e.geom_type == GeomType.OFFSET
        ]
        offset_edges2 = [
            e for e in offset_wire2.edges() if e.geom_type == GeomType.OFFSET
        ]

        assert len(offset_edges1) > 0
        assert offset_edges1[0].geom_equal(offset_edges2[0])

    def test_different_offset_value(self):
        v = [Vertex(p) for p in ((0, 0), (1, 1), (2, 0), (3, 1))]
        s = Spline(*v)
        w = Wire([s.edge()])
        offset_wire1 = w.offset_2d(0.1)
        offset_wire2 = w.offset_2d(0.2)

        offset_edges1 = [
            e for e in offset_wire1.edges() if e.geom_type == GeomType.OFFSET
        ]
        offset_edges2 = [
            e for e in offset_wire2.edges() if e.geom_type == GeomType.OFFSET
        ]

        assert not offset_edges1[0].geom_equal(offset_edges2[0])

    def test_different_offset_direction(self):
        """Offset curves with different offset directions (on different planes)."""
        from build123d import Axis

        v = [Vertex(p) for p in ((0, 0), (1, 1), (2, 0), (3, 1))]
        s = Spline(*v)
        w = Wire([s.edge()])

        # Offset on XY plane (Z direction)
        offset_wire1 = w.offset_2d(0.1)
        offset_edges1 = [
            e for e in offset_wire1.edges() if e.geom_type == GeomType.OFFSET
        ]

        # Rotate wire 90 degrees around X axis to put it on XZ plane
        w_rotated = w.rotate(Axis.X, 90)
        offset_wire2 = w_rotated.offset_2d(0.1)
        offset_edges2 = [
            e for e in offset_wire2.edges() if e.geom_type == GeomType.OFFSET
        ]

        if len(offset_edges1) > 0 and len(offset_edges2) > 0:
            # Different directions means not equal
            assert not offset_edges1[0].geom_equal(offset_edges2[0])


class TestEdgeGeomEqualTolerance:
    """Tests for tolerance behavior in Edge.geom_equal."""

    def test_circle_radius_within_tolerance(self):
        """Circle radii differing by less than tolerance are equal."""
        e1 = Edge.make_circle(10.0)
        e2 = Edge.make_circle(10.0 + 1e-7)  # Within default tol=1e-6
        assert e1.geom_equal(e2)

    def test_circle_radius_outside_tolerance(self):
        """Circle radii differing by more than tolerance are not equal."""
        e1 = Edge.make_circle(10.0)
        e2 = Edge.make_circle(10.0 + 1e-5)  # Outside default tol=1e-6
        assert not e1.geom_equal(e2)

    def test_tol_parameter_accepted(self):
        """The tol parameter is accepted by geom_equal.

        Note: The tol parameter affects property comparisons (radius, focal length,
        weights, knots, offset values) but endpoint comparison always uses Vector's
        built-in TOLERANCE (1e-6). Since most geometric differences also change
        endpoints, the custom tol has limited practical effect.
        """
        e1 = Edge.make_line((0, 0), (1, 1))
        e2 = Edge.make_line((0, 0), (1, 1))
        # Parameter is accepted
        assert e1.geom_equal(e2, tol=1e-9)
        assert e1.geom_equal(e2, tol=0.1)

    def test_line_endpoint_within_tolerance(self):
        """Line endpoints differing by less than tolerance are equal."""
        e1 = Edge.make_line((0, 0, 0), (1, 1, 1))
        e2 = Edge.make_line((0, 0, 0), (1 + 1e-7, 1, 1))
        assert e1.geom_equal(e2)

    def test_line_endpoint_outside_tolerance(self):
        """Line endpoints differing by more than tolerance are not equal."""
        e1 = Edge.make_line((0, 0, 0), (1, 1, 1))
        e2 = Edge.make_line((0, 0, 0), (1.001, 1, 1))
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualReversed:
    """Tests for reversed edge comparison."""

    def test_line_reversed_not_equal(self):
        """Reversed line is not equal (different direction)."""
        e1 = Edge.make_line((0, 0), (1, 1))
        e2 = Edge.make_line((1, 1), (0, 0))
        assert not e1.geom_equal(e2)

    def test_arc_reversed_not_equal(self):
        """Reversed arc is not equal."""
        e1 = Edge.make_circle(10, start_angle=0, end_angle=90)
        e2 = Edge.make_circle(10, start_angle=0, end_angle=90).reversed()
        # Reversed edge has swapped start/end points
        assert not e1.geom_equal(e2)

    def test_spline_reversed_not_equal(self):
        """Reversed spline is not equal."""
        pts = [(0, 0), (1, 1), (2, 0), (3, 1)]
        s = Spline(*[Vertex(p) for p in pts])
        e1 = s.edge()
        e2 = e1.reversed()
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualArcVariations:
    """Tests for arc edge cases."""

    def test_full_circle_equal(self):
        """Two full circles are equal."""
        e1 = Edge.make_circle(10)
        e2 = Edge.make_circle(10)
        assert e1.geom_equal(e2)

    def test_arc_different_start_same_sweep(self):
        """Arcs with different start angles but same sweep are not equal."""
        e1 = Edge.make_circle(10, start_angle=0, end_angle=90)
        e2 = Edge.make_circle(10, start_angle=90, end_angle=180)
        # Same radius and sweep angle, but different positions
        assert not e1.geom_equal(e2)

    def test_arc_same_endpoints_different_direction(self):
        """Arcs with same endpoints but opposite sweep direction."""
        from build123d import AngularDirection

        e1 = Edge.make_circle(
            10,
            start_angle=0,
            end_angle=90,
            angular_direction=AngularDirection.COUNTER_CLOCKWISE,
        )
        e2 = Edge.make_circle(
            10,
            start_angle=90,
            end_angle=0,
            angular_direction=AngularDirection.CLOCKWISE,
        )
        # These trace different paths (short arc vs long arc)
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualNumerical:
    """Tests for numerical edge cases."""

    def test_very_small_edge(self):
        """Very small edges can be compared."""
        e1 = Edge.make_line((0, 0), (1e-6, 1e-6))
        e2 = Edge.make_line((0, 0), (1e-6, 1e-6))
        assert e1.geom_equal(e2)

    def test_very_large_coordinates(self):
        """Edges with large coordinates can be compared."""
        e1 = Edge.make_line((1e6, 1e6), (1e6 + 1, 1e6 + 1))
        e2 = Edge.make_line((1e6, 1e6), (1e6 + 1, 1e6 + 1))
        assert e1.geom_equal(e2)

    def test_large_coordinates_small_difference(self):
        """Small differences at large coordinates."""
        e1 = Edge.make_line((1e6, 1e6), (1e6 + 1, 1e6 + 1))
        e2 = Edge.make_line((1e6, 1e6), (1e6 + 1 + 1e-5, 1e6 + 1))
        # Difference is above tolerance
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqual3DPositioning:
    """Tests for 3D positioning edge cases."""

    def test_same_shape_different_z(self):
        """Same 2D shape at different Z levels are not equal."""
        e1 = Edge.make_circle(10)
        e2 = Edge.make_circle(10).locate(Location((0, 0, 5)))
        assert not e1.geom_equal(e2)

    def test_line_in_3d(self):
        """3D lines with same geometry are equal."""
        e1 = Edge.make_line((0, 0, 0), (1, 2, 3))
        e2 = Edge.make_line((0, 0, 0), (1, 2, 3))
        assert e1.geom_equal(e2)

    def test_line_in_3d_different(self):
        """3D lines with different Z are not equal."""
        e1 = Edge.make_line((0, 0, 0), (1, 1, 0))
        e2 = Edge.make_line((0, 0, 0), (1, 1, 1))
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualSplineVariations:
    """Tests for BSpline edge cases."""

    def test_spline_control_point_within_tolerance(self):
        """Splines with control points within tolerance are equal."""
        pts1 = [(0, 0), (1, 1), (2, 0)]
        pts2 = [(0, 0), (1 + 1e-7, 1), (2, 0)]
        e1 = Spline(*[Vertex(p) for p in pts1]).edge()
        e2 = Spline(*[Vertex(p) for p in pts2]).edge()
        assert e1.geom_equal(e2)

    def test_spline_control_point_outside_tolerance(self):
        """Splines with control points outside tolerance are not equal."""
        pts1 = [(0, 0), (1, 1), (2, 0)]
        pts2 = [(0, 0), (1.001, 1), (2, 0)]
        e1 = Spline(*[Vertex(p) for p in pts1]).edge()
        e2 = Spline(*[Vertex(p) for p in pts2]).edge()
        assert not e1.geom_equal(e2)

    def test_spline_different_point_count(self):
        """Splines with different number of control points are not equal."""
        pts1 = [(0, 0), (1, 1), (2, 0)]
        pts2 = [(0, 0), (0.5, 0.5), (1, 1), (2, 0)]
        e1 = Spline(*[Vertex(p) for p in pts1]).edge()
        e2 = Spline(*[Vertex(p) for p in pts2]).edge()
        # Different number of poles
        assert not e1.geom_equal(e2)


class TestEdgeGeomEqualUnknownType:
    """Tests for the fallback case (OTHER/unknown geom types)."""

    def test_interpolation_points_used(self):
        """For unknown types, sample points are compared."""
        # Create edges that would use the fallback path
        # Most common types are handled, but we can test the parameter
        e1 = Edge.make_line((0, 0), (1, 1))
        e2 = Edge.make_line((0, 0), (1, 1))
        # Even with different num_interpolation_points, these should be equal
        assert e1.geom_equal(e2, num_interpolation_points=3)
        assert e1.geom_equal(e2, num_interpolation_points=10)


class TestWireGeomEqual:
    """Tests for Wire.geom_equal method."""

    def test_same_rectangle_wire(self):
        r1 = Rectangle(10, 5)
        r2 = Rectangle(10, 5)
        assert r1.wire().geom_equal(r2.wire())

    def test_different_rectangle_wire(self):
        r1 = Rectangle(10, 5)
        r2 = Rectangle(10, 6)
        assert not r1.wire().geom_equal(r2.wire())

    def test_same_spline_wire(self):
        v = [Vertex(p) for p in ((0, 0), (1, 1), (2, 0), (3, 1))]
        s1 = Spline(*v)
        s2 = Spline(*v)
        w1 = Wire([s1.edge()])
        w2 = Wire([s2.edge()])
        assert w1.geom_equal(w2)

    def test_different_edge_count(self):
        r1 = Rectangle(10, 5)
        e = Edge.make_line((0, 0), (10, 0))
        w1 = r1.wire()
        w2 = Wire([e])
        assert not w1.geom_equal(w2)

    def test_identical_edge_objects(self):
        """Two wires sharing the same edge objects."""
        e1 = Edge.make_line((0, 0), (1, 0))
        e2 = Edge.make_line((1, 0), (1, 1))
        e3 = Edge.make_line((1, 1), (0, 0))
        w1 = Wire([e1, e2, e3])
        w2 = Wire([e1, e2, e3])  # Same edge objects
        assert w1.geom_equal(w2)

    def test_geometrically_equal_edges(self):
        """Two wires with geometrically equal but distinct edge objects."""
        # Wire 1
        e1a = Edge.make_line((0, 0), (1, 0))
        e2a = Edge.make_line((1, 0), (1, 1))
        e3a = Edge.make_line((1, 1), (0, 0))
        w1 = Wire([e1a, e2a, e3a])
        # Wire 2 - same geometry, different objects
        e1b = Edge.make_line((0, 0), (1, 0))
        e2b = Edge.make_line((1, 0), (1, 1))
        e3b = Edge.make_line((1, 1), (0, 0))
        w2 = Wire([e1b, e2b, e3b])
        assert w1.geom_equal(w2)

    def test_edges_different_start_point(self):
        """Two closed wires with same geometry but different starting vertex are not equal."""
        # Wire 1: starts at (0,0)
        e1a = Edge.make_line((0, 0), (1, 0))
        e2a = Edge.make_line((1, 0), (1, 1))
        e3a = Edge.make_line((1, 1), (0, 0))
        w1 = Wire([e1a, e2a, e3a])
        # Wire 2: starts at (1,1) due to different edge order in constructor
        e3b = Edge.make_line((1, 1), (0, 0))
        e1b = Edge.make_line((0, 0), (1, 0))
        e2b = Edge.make_line((1, 0), (1, 1))
        w2 = Wire([e3b, e1b, e2b])
        # Different starting point means not equal
        assert not w1.geom_equal(w2)

    def test_one_edge_reversed(self):
        """Two wires where one has an edge with reversed direction."""
        # Wire 1: all edges in forward direction
        e1a = Edge.make_line((0, 0), (1, 0))
        e2a = Edge.make_line((1, 0), (1, 1))
        e3a = Edge.make_line((1, 1), (0, 0))
        w1 = Wire([e1a, e2a, e3a])
        # Wire 2: middle edge is reversed (direction (1,1) -> (1,0) instead of (1,0) -> (1,1))
        e1b = Edge.make_line((0, 0), (1, 0))
        e2b = Edge.make_line((1, 1), (1, 0))  # Reversed!
        e3b = Edge.make_line((1, 1), (0, 0))
        w2 = Wire([e1b, e2b, e3b])
        # order_edges should correct the orientation
        assert w1.geom_equal(w2)

    def test_closed_wire(self):
        """Two closed wires with same geometry."""
        w1 = Wire(
            [
                Edge.make_line((0, 0), (2, 0)),
                Edge.make_line((2, 0), (2, 2)),
                Edge.make_line((2, 2), (0, 2)),
                Edge.make_line((0, 2), (0, 0)),
            ]
        )
        w2 = Wire(
            [
                Edge.make_line((0, 0), (2, 0)),
                Edge.make_line((2, 0), (2, 2)),
                Edge.make_line((2, 2), (0, 2)),
                Edge.make_line((0, 2), (0, 0)),
            ]
        )
        assert w1.is_closed
        assert w2.is_closed
        assert w1.geom_equal(w2)

    def test_mixed_edge_types(self):
        """Wires with mixed edge types (lines and arcs)."""
        # Wire with line + arc + line
        e1a = Edge.make_line((0, 0), (1, 0))
        e2a = Edge.make_circle(0.5, start_angle=0, end_angle=180).locate(
            Location((1.5, 0, 0))
        )
        e3a = Edge.make_line((2, 0), (3, 0))
        w1 = Wire([e1a, e2a, e3a])

        e1b = Edge.make_line((0, 0), (1, 0))
        e2b = Edge.make_circle(0.5, start_angle=0, end_angle=180).locate(
            Location((1.5, 0, 0))
        )
        e3b = Edge.make_line((2, 0), (3, 0))
        w2 = Wire([e1b, e2b, e3b])

        assert w1.geom_equal(w2)

    def test_mixed_edge_types_different(self):
        """Wires with mixed edge types that differ."""
        # Wire 1: line + arc
        e1a = Edge.make_line((0, 0), (1, 0))
        e2a = Edge.make_circle(0.5, start_angle=0, end_angle=180).locate(
            Location((1.5, 0, 0))
        )
        w1 = Wire([e1a, e2a])

        # Wire 2: line + different arc (different radius)
        e1b = Edge.make_line((0, 0), (1, 0))
        e2b = Edge.make_circle(0.6, start_angle=0, end_angle=180).locate(
            Location((1.6, 0, 0))
        )
        w2 = Wire([e1b, e2b])

        assert not w1.geom_equal(w2)

    def test_all_edges_reversed_not_equal(self):
        """Wire traced in opposite direction is not equal."""
        # Wire 1: (0,0) -> (3,0)
        e1a = Edge.make_line((0, 0), (1, 0))
        e2a = Edge.make_line((1, 0), (2, 1))
        e3a = Edge.make_line((2, 1), (3, 0))
        w1 = Wire([e1a, e2a, e3a])

        # Wire 2: (3,0) -> (0,0) - same path but opposite direction
        e1b = Edge.make_line((1, 0), (0, 0))
        e2b = Edge.make_line((2, 1), (1, 0))
        e3b = Edge.make_line((3, 0), (2, 1))
        w2 = Wire([e3b, e2b, e1b])

        assert not w1.geom_equal(w2)

    def test_open_wire_different_start(self):
        """Open wires with same edges but different starting edge - should not match."""
        # For open wires, the start matters
        e1 = Edge.make_line((0, 0), (1, 0))
        e2 = Edge.make_line((1, 0), (2, 1))
        e3 = Edge.make_line((2, 1), (3, 0))
        w1 = Wire([e1, e2, e3])

        # Different edges entirely (shifted)
        e4 = Edge.make_line((1, 0), (2, 0))
        e5 = Edge.make_line((2, 0), (3, 1))
        e6 = Edge.make_line((3, 1), (4, 0))
        w2 = Wire([e4, e5, e6])

        assert not w1.geom_equal(w2)

    def test_wire_with_spline_edges(self):
        """Wires containing spline edges."""
        pts1 = [(0, 0), (1, 1), (2, 0), (3, 1), (4, 0)]
        pts2 = [(4, 0), (5, 1), (6, 0)]

        s1a = Spline(*[Vertex(p) for p in pts1])
        s2a = Spline(*[Vertex(p) for p in pts2])
        w1 = Wire([s1a.edge(), s2a.edge()])

        s1b = Spline(*[Vertex(p) for p in pts1])
        s2b = Spline(*[Vertex(p) for p in pts2])
        w2 = Wire([s1b.edge(), s2b.edge()])

        assert w1.geom_equal(w2)

    def test_single_edge_wire(self):
        """Wires with single edge."""
        w1 = Wire([Edge.make_line((0, 0), (5, 5))])
        w2 = Wire([Edge.make_line((0, 0), (5, 5))])
        assert w1.geom_equal(w2)

    def test_single_edge_wire_reversed_not_equal(self):
        """Single edge wire vs reversed single edge wire are not equal."""
        w1 = Wire([Edge.make_line((0, 0), (5, 5))])
        w2 = Wire([Edge.make_line((5, 5), (0, 0))])
        # Opposite direction means not equal
        assert not w1.geom_equal(w2)


class TestGeomEqualTypeMismatch:
    """Tests for type mismatch cases."""

    def test_edge_vs_non_edge(self):
        e = Edge.make_line((0, 0), (1, 1))
        w = Wire([e])
        # Edge.geom_equal should return False for non-Edge
        assert not e.geom_equal(w)

    def test_wire_vs_non_wire(self):
        e = Edge.make_line((0, 0), (1, 1))
        w = Wire([e])
        # Wire.geom_equal should return False for non-Wire
        assert not w.geom_equal(e)

    def test_different_geom_types(self):
        line = Edge.make_line((0, 0, 0), (1, 1, 1))
        circle = Circle(10).edge()
        assert not line.geom_equal(circle)
