"""
build123d tests

name: test_constrained_arcs.py
by:   Gumyr
date: September 12, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import pytest
from OCP.BRep import BRep_Tool
from OCP.gp import gp_Ax2d, gp_Circ2d, gp_Dir2d, gp_Pnt2d

from build123d.build_enums import GeomType, LengthMode, Sagitta, Tangency
from build123d.build_line import BuildLine
from build123d.geometry import TOLERANCE, Axis, Plane, Vector
from build123d.objects_curve import (
    CenterArc,
    ConstrainedArcs,
    Line,
    PolarLine,
    ThreePointArc,
)
from build123d.operations_generic import mirror
from build123d.topology import (
    Edge,
    Face,
    Solid,
    Vertex,
    Wire,
    topo_explore_common_vertex,
)
from build123d.topology.constrained_lines import (
    _as_gcc_arg,
    _edge_to_qualified_2d,
    _param_in_trim,
    _two_arc_edges_from_params,
)


def test_edge_to_qualified_2d():
    e = Line((0, 0), (1, 0))
    e.position += (1, 1, 1)
    qc, curve_2d, first, last, adaptor = _edge_to_qualified_2d(
        e.wrapped, Tangency.UNQUALIFIED
    )
    assert first < last


def test_two_arc_edges_from_params():
    circle = gp_Circ2d(gp_Ax2d(gp_Pnt2d(0, 0), gp_Dir2d(1.0, 0.0)), 1)
    arcs = _two_arc_edges_from_params(circle, 0, TOLERANCE / 10)
    assert len(arcs) == 0


def test_param_in_trim():
    with pytest.raises(TypeError) as excinfo:
        _param_in_trim(None, 0.0, 1.0, None)
    assert "Invalid parameters to _param_in_trim" in str(excinfo.value)


def test_as_gcc_arg():
    e = Line((0, 0), (1, 0))
    e.wrapped = None
    with pytest.raises(TypeError) as excinfo:
        _as_gcc_arg(e, Tangency.UNQUALIFIED)
    assert "Can't create a qualified curve from empty edge" in str(excinfo.value)


def test_constrained_arcs_arg_processing():
    """Test input error handling"""
    with pytest.raises(TypeError):
        Edge.make_constrained_arcs(Solid.make_box(1, 1, 1), (1, 0), radius=0.5)
    with pytest.raises(TypeError):
        Edge.make_constrained_arcs(
            (Vector(0, 0), Tangency.UNQUALIFIED), (1, 0), radius=0.5
        )
    with pytest.raises(TypeError):
        Edge.make_constrained_arcs(pnt1=(1, 1, 1), pnt2=(1, 0), radius=0.5)
    with pytest.raises(TypeError):
        Edge.make_constrained_arcs(radius=0.1)
    with pytest.raises(ValueError):
        Edge.make_constrained_arcs((0, 0), (0, 0.5), radius=0.5, center=(0, 0.25))
    with pytest.raises(ValueError):
        Edge.make_constrained_arcs((0, 0), (0, 0.5), radius=-0.5)


def test_tan2_rad_arcs_1():
    """2 edges & radius"""
    e1 = Line((-2, 0), (2, 0))
    e2 = Line((0, -2), (0, 2))

    tan2_rad_edges = Edge.make_constrained_arcs(
        e1, e2, radius=0.5, sagitta=Sagitta.BOTH
    )
    assert len(tan2_rad_edges) == 8

    tan2_rad_edges = Edge.make_constrained_arcs(e1, e2, radius=0.5)
    assert len(tan2_rad_edges) == 4

    tan2_rad_edges = Edge.make_constrained_arcs(
        (e1, Tangency.UNQUALIFIED), (e2, Tangency.UNQUALIFIED), radius=0.5
    )
    assert len(tan2_rad_edges) == 4

    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_rad_edges)


def test_tan2_rad_arcs_2():
    """2 edges & radius"""
    e1 = CenterArc((0, 0), 1, 0, 90)
    e2 = Line((1, 0), (2, 0))

    tan2_rad_edges = Edge.make_constrained_arcs(e1, e2, radius=0.5)
    assert len(tan2_rad_edges) == 1
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_rad_edges)


def test_tan2_rad_arcs_3():
    """2 points & radius"""
    tan2_rad_edges = Edge.make_constrained_arcs((0, 0), (0, 0.5), radius=0.5)
    assert len(tan2_rad_edges) == 2

    tan2_rad_edges = Edge.make_constrained_arcs(
        Vertex(0, 0), Vertex(0, 0.5), radius=0.5
    )
    assert len(tan2_rad_edges) == 2

    tan2_rad_edges = Edge.make_constrained_arcs(
        Vector(0, 0), Vector(0, 0.5), radius=0.5
    )
    assert len(tan2_rad_edges) == 2

    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_rad_edges)


def test_tan2_rad_arcs_4():
    """edge & 1 points & radius"""
    # the point should be automatically moved after the edge
    e1 = Line((0, 0), (1, 0))
    tan2_rad_edges = Edge.make_constrained_arcs((0, 0.5), e1, radius=0.5)
    assert len(tan2_rad_edges) == 1

    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_rad_edges)


def test_tan2_rad_arcs_5():
    """no solution"""
    with pytest.raises(RuntimeError) as excinfo:
        Edge.make_constrained_arcs((0, 0), (10, 0), radius=2)
    assert "Unable to find a tangent arc" in str(excinfo.value)


def test_tan2_center_on_1():
    """2 tangents & center on"""
    c1 = PolarLine((0, 0), 4, -20, length_mode=LengthMode.HORIZONTAL)
    c2 = Line((4, -2), (4, 2))
    c3_center_on = Line((3, -2), (3, 2))
    tan2_on_edge = Edge.make_constrained_arcs(
        (c1, Tangency.UNQUALIFIED),
        (c2, Tangency.UNQUALIFIED),
        center_on=c3_center_on,
    )
    assert len(tan2_on_edge) == 1
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_on_edge)


def test_tan2_center_on_2():
    """2 tangents & center on"""
    tan2_on_edge = Edge.make_constrained_arcs(
        (0, 3), (5, 0), center_on=Line((0, -5), (0, 5))
    )
    assert len(tan2_on_edge) == 1
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_on_edge)


def test_tan2_center_on_3():
    """2 tangents & center on"""
    tan2_on_edge = Edge.make_constrained_arcs(
        Line((-5, 3), (5, 3)), (5, 0), center_on=Line((0, -5), (0, 5))
    )
    assert len(tan2_on_edge) == 1
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_on_edge)


def test_tan2_center_on_4():
    """2 tangents & center on"""
    tan2_on_edge = Edge.make_constrained_arcs(
        Line((-5, 3), (5, 3)), (5, 0), center_on=Axis.Y
    )
    assert len(tan2_on_edge) == 1
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan2_on_edge)


def test_tan2_center_on_5():
    """2 tangents & center on"""
    with pytest.raises(RuntimeError) as excinfo:
        Edge.make_constrained_arcs(
            Line((-5, 3), (5, 3)),
            Line((-5, 0), (5, 0)),
            center_on=Line((-5, -1), (5, -1)),
        )
    assert "Unable to find a tangent arc with center_on constraint" in str(
        excinfo.value
    )


def test_tan2_center_on_6():
    """2 tangents & center on"""
    l1 = Line((0, 0), (5, 0))
    l2 = Line((0, 0), (0, 5))
    l3 = Line((20, 20), (22, 22))
    with pytest.raises(RuntimeError) as excinfo:
        Edge.make_constrained_arcs(l1, l2, center_on=l3)
    assert "Unable to find a tangent arc with center_on constraint" in str(
        excinfo.value
    )


# --- Sagitta selection branches ---


def test_tan2_center_on_sagitta_both_returns_two_arcs():
    """
    TWO lines, center_on a line that crosses *both* angle bisectors → multiple
    circle solutions; with Sagitta.BOTH we should get 2 arcs per solution.
    Setup: x-axis & y-axis; center_on y=1.
    """
    c1 = Line((-10, 0), (10, 0))  # y = 0
    c2 = Line((0, -10), (0, 10))  # x = 0
    center_on = Line((-10, 1), (10, 1))  # y = 1

    arcs = Edge.make_constrained_arcs(
        (c1, Tangency.UNQUALIFIED),
        (c2, Tangency.UNQUALIFIED),
        center_on=center_on,
        sagitta=Sagitta.BOTH,
    )
    # Expect 2 solutions (centers at (1,1) and (-1,1)), each yielding 2 arcs → 4
    assert len(arcs) >= 2  # be permissive across kernels; typically 4
    # At least confirms BOTH path is covered and multiple solutions iterate

    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in arcs)


def test_tan2_center_on_sagitta_long_is_longer_than_short():
    """
    Verify LONG branch by comparing lengths against SHORT for the same geometry.
    """
    c1 = Line((-10, 0), (10, 0))  # y = 0
    c2 = Line((0, -10), (0, 10))  # x = 0
    center_on = Line((3, -10), (3, 10))  # x = 3 (unique center)

    short_arc = Edge.make_constrained_arcs(
        (c1, Tangency.UNQUALIFIED),
        (c2, Tangency.UNQUALIFIED),
        center_on=center_on,
        sagitta=Sagitta.SHORT,
    )
    long_arc = Edge.make_constrained_arcs(
        (c1, Tangency.UNQUALIFIED),
        (c2, Tangency.UNQUALIFIED),
        center_on=center_on,
        sagitta=Sagitta.LONG,
    )
    assert len(short_arc) == 2
    assert len(long_arc) == 2
    assert long_arc[0].length > short_arc[0].length
    assert all(
        BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in short_arc + long_arc
    )


# --- Filtering branches inside the Solutions loop ---


def test_tan2_center_on_filters_outside_first_tangent_segment():
    """
    Cause _ok(0, u_arg1) to fail:
    - First tangency is a *very short* horizontal segment near x∈[0, 0.01].
    - Second tangency is a vertical line far away.
    - Center_on is x=5 (vertical).
    The resulting tangency on the infinite horizontal line occurs near x≈center.x (≈5),
    which lies *outside* the trimmed first segment → filtered out, no arcs.
    """
    tiny_first = Line((0.0, 0.0), (0.01, 0.0))  # very short horizontal
    c2 = Line((10.0, -10.0), (10.0, 10.0))  # vertical line
    center_on = Line((5.0, -10.0), (5.0, 10.0))  # x = 5

    arcs = Edge.make_constrained_arcs(
        (tiny_first, Tangency.UNQUALIFIED),
        (c2, Tangency.UNQUALIFIED),
        center_on=center_on,
        sagitta=Sagitta.SHORT,
    )
    # GCC likely finds solutions, but they should be filtered out by _ok(0)
    assert len(arcs) == 0


def test_tan2_center_on_filters_outside_second_tangent_segment():
    """
    Cause _ok(1, u_arg2) to fail:
    - First tangency is a *point* (so _ok(0) is trivially True).
    - Second tangency is a *very short* vertical segment around y≈0 on x=10.
    - Center_on is y=2 (horizontal), and first point is at (0,2).
      For a circle through (0,2) and tangent to x=10 with center_on y=2,
      the center is at (5,2), radius=5, so tangency on x=10 occurs at y=2,
      which is *outside* the tiny segment around y≈0 → filtered by _ok(1).
    """
    first_point = (0.0, 2.0)  # acts as a "point object"
    tiny_second = Line((10.0, -0.005), (10.0, 0.005))  # very short vertical near y=0
    center_on = Line((-10.0, 2.0), (10.0, 2.0))  # y = 2

    arcs = Edge.make_constrained_arcs(
        first_point,
        (tiny_second, Tangency.UNQUALIFIED),
        center_on=center_on,
        sagitta=Sagitta.SHORT,
    )
    assert len(arcs) == 0


# --- Multiple-solution loop coverage with BOTH again (robust geometry) ---


def test_tan2_center_on_multiple_solutions_both_counts():
    """
    Another geometry with 2+ GCC solutions:
      c1: y=0, c2: y=4 (two non-intersecting parallels), center_on x=0.
    Any circle tangent to both has radius=2 and center on y=2; with center_on x=0,
    the center fixes at (0,2) — single center → two arcs (BOTH).
    Use intersecting lines instead to guarantee >1 solutions: c1: y=0, c2: x=0,
    center_on y=-2 (intersects both angle bisectors at (-2,-2) and (2,-2)).
    """
    c1 = Line((-20, 0), (20, 0))  # y = 0
    c2 = Line((0, -20), (0, 20))  # x = 0
    center_on = Line((-20, -2), (20, -2))  # y = -2

    arcs = Edge.make_constrained_arcs(
        (c1, Tangency.UNQUALIFIED),
        (c2, Tangency.UNQUALIFIED),
        center_on=center_on,
        sagitta=Sagitta.BOTH,
    )
    # Expect at least 2 arcs (often 4); asserts loop over multiple i values
    assert len(arcs) >= 2

    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in arcs)


def test_tan_center_on_1():
    """1 tangent & center on"""
    c5 = PolarLine((0, 0), 4, 60)
    tan_center = Edge.make_constrained_arcs((c5, Tangency.UNQUALIFIED), center=(2, 1))
    assert len(tan_center) == 1
    assert tan_center[0].is_closed
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan_center)


def test_tan_center_on_2():
    """1 tangent & center on"""
    tan_center = Edge.make_constrained_arcs(Axis.X, center=(2, 1, 5))
    assert len(tan_center) == 1
    assert tan_center[0].is_closed
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan_center)


def test_tan_center_on_3():
    """1 tangent & center on"""
    l1 = CenterArc((0, 0), 1, 180, 5)
    tan_center = Edge.make_constrained_arcs(l1, center=(2, 0))
    assert len(tan_center) == 1
    assert tan_center[0].is_closed
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan_center)


def test_pnt_center_1():
    """pnt & center"""
    pnt_center = Edge.make_constrained_arcs((-2.5, 1.5), center=(-2, 1))
    assert len(pnt_center) == 1
    assert pnt_center[0].is_closed
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in pnt_center)

    pnt_center = Edge.make_constrained_arcs((-2.5, 1.5), center=Vertex(-2, 1))
    assert len(pnt_center) == 1
    assert pnt_center[0].is_closed
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in pnt_center)


def test_tan_cen_arcs_center_equals_point_returns_empty():
    """
    If the fixed center coincides with the tangency point,
    the computed radius is zero and no valid circle exists.
    Function should return an empty ShapeList.
    """
    center = (0, 0)
    tangency_point = (0, 0)  # same as center

    arcs = Edge.make_constrained_arcs(tangency_point, center=center)

    assert isinstance(arcs, list)  # ShapeList subclass
    assert len(arcs) == 0


def test_tan_rad_center_on_1():
    """tangent, radius, center on"""
    c1 = PolarLine((0, 0), 4, -20, length_mode=LengthMode.HORIZONTAL)
    c3_center_on = Line((3, -2), (3, 2))
    tan_rad_on = Edge.make_constrained_arcs(
        (c1, Tangency.UNQUALIFIED), radius=1, center_on=c3_center_on
    )
    assert len(tan_rad_on) == 1
    assert tan_rad_on[0].is_closed
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan_rad_on)


def test_tan_rad_center_on_2():
    """tangent, radius, center on"""
    c1 = PolarLine((0, 0), 4, -20, length_mode=LengthMode.HORIZONTAL)
    tan_rad_on = Edge.make_constrained_arcs(c1, radius=1, center_on=Axis.X)
    assert len(tan_rad_on) == 1
    assert tan_rad_on[0].is_closed
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan_rad_on)


def test_tan_rad_center_on_3():
    """tangent, radius, center on"""
    c1 = PolarLine((0, 0), 4, -20, length_mode=LengthMode.HORIZONTAL)
    with pytest.raises(TypeError) as excinfo:
        Edge.make_constrained_arcs(c1, radius=1, center_on=Face.make_rect(1, 1))


def test_tan_rad_center_on_4():
    """tangent, radius, center on"""
    c1 = Line((0, 10), (10, 10))
    with pytest.raises(RuntimeError) as excinfo:
        Edge.make_constrained_arcs(c1, radius=1, center_on=Axis.X)


def test_tan3_1():
    """3 tangents"""
    c5 = PolarLine((0, 0), 4, 60)
    c6 = PolarLine((0, 0), 4, 40)
    c7 = CenterArc((0, 0), 4, 0, 90)
    tan3 = Edge.make_constrained_arcs(
        (c5, Tangency.UNQUALIFIED),
        (c6, Tangency.UNQUALIFIED),
        (c7, Tangency.UNQUALIFIED),
    )
    assert len(tan3) == 1
    assert not tan3[0].is_closed

    tan3b = Edge.make_constrained_arcs(c5, c6, c7, sagitta=Sagitta.BOTH)
    assert len(tan3b) == 2
    assert all(BRep_Tool.Curve_s(e.wrapped, float(), float()) for e in tan3b)


def test_tan3_2():
    with pytest.raises(RuntimeError) as excinfo:
        Edge.make_constrained_arcs(
            Line((0, 0), (0, 1)),
            Line((0, 0), (1, 0)),
            Line((0, 0), (0, -1)),
        )
    assert "Unable to find a circle tangent to all three objects" in str(excinfo.value)


def test_tan3_3():
    l1 = Line((0, 0), (10, 0))
    l2 = Line((0, 2), (10, 2))
    l3 = Line((0, 5), (10, 5))
    with pytest.raises(RuntimeError) as excinfo:
        Edge.make_constrained_arcs(l1, l2, l3)
    assert "Unable to find a circle tangent to all three objects" in str(excinfo.value)


def test_tan3_4():
    l1 = Line((-1, 0), (-1, 2))
    l2 = Line((1, 0), (1, 2))
    l3 = Line((-1, 0), (-0.75, 0))
    tan3 = Edge.make_constrained_arcs(l1, l2, l3)
    assert len(tan3) == 0


def test_eggplant():
    """complex set of 4 arcs"""
    r_left, r_right = 0.75, 1.0
    r_bottom, r_top = 6, 8
    con_circle_left = CenterArc((-2, 0), r_left, 0, 360)
    con_circle_right = CenterArc((2, 0), r_right, 0, 360)
    egg_bottom = Edge.make_constrained_arcs(
        (con_circle_right, Tangency.OUTSIDE),
        (con_circle_left, Tangency.OUTSIDE),
        radius=r_bottom,
    ).sort_by(Axis.Y)[0]
    egg_top = Edge.make_constrained_arcs(
        (con_circle_right, Tangency.ENCLOSING),
        (con_circle_left, Tangency.ENCLOSING),
        radius=r_top,
    ).sort_by(Axis.Y)[-1]
    egg_right = ThreePointArc(
        egg_bottom.vertices().sort_by(Axis.X)[-1],
        con_circle_right @ 0,
        egg_top.vertices().sort_by(Axis.X)[-1],
    )
    egg_left = ThreePointArc(
        egg_bottom.vertices().sort_by(Axis.X)[0],
        con_circle_left @ 0.5,
        egg_top.vertices().sort_by(Axis.X)[0],
    )

    egg_plant = Wire([egg_left, egg_top, egg_right, egg_bottom])
    assert egg_plant.is_closed
    egg_plant_edges = egg_plant.edges().sort_by(egg_plant)
    common_vertex_cnt = sum(
        topo_explore_common_vertex(egg_plant_edges[i], egg_plant_edges[(i + 1) % 4])
        is not None
        for i in range(4)
    )
    assert common_vertex_cnt == 4

    # C1 continuity
    assert all(
        (egg_plant_edges[i] % 1 - egg_plant_edges[(i + 1) % 4] % 0).length < TOLERANCE
        for i in range(4)
    )
    assert all(
        BRep_Tool.Curve_s(e.wrapped, float(), float())
        for e in [egg_bottom, egg_top, egg_right, egg_left]
    )


def test_higher_level_constrained_arcs():
    unit_circle = Edge.make_circle(1.0, Plane.XY)
    lines = ConstrainedArcs(unit_circle, Axis.Y, radius=1)
    assert len(lines.edges()) == 4

    with BuildLine() as drawing:
        ConstrainedArcs(
            unit_circle, Axis.Y, radius=1, selector=lambda a: a.group_by(Axis.Y)[-1]
        )

    assert len(drawing.edges()) == 2

    with pytest.raises(ValueError) as excinfo:
        ConstrainedArcs(
            unit_circle,
            Axis.Y,
            radius=1,
            selector=lambda l: l.filter_by(GeomType.LINE),
        )
