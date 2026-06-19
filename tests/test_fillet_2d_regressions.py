"""
build123d imports

name: test_fillet_2d_regressions.py
by:   Gumyr
date: June 29, 2026

desc:
    This python module contains tests for the build123d project related to issue #1296.

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

from build123d import (
    Align,
    Axis,
    BuildLine,
    BuildSketch,
    CenterArc,
    ConstrainedArcs,
    ConstrainedLines,
    Ellipse,
    JernArc,
    Line,
    Locations,
    Mode,
    Plane,
    RadiusArc,
    Rectangle,
    Sagitta,
    Spline,
    fillet,
    make_face,
)

RADIUS = 5  # fillet radius
EDGE_RADIUS = 5.0001  # arc/spline/ellipse 'radius'


def _assert_valid_fillet(sk, number_of_edges: int = 4):
    assert len(sk.edges()) == number_of_edges


def test_fillet_line_full_edge_consumed():
    """Fillet consuming an entire Line edge between two circle arcs.
    Regresses ChFi2d_FilletAlgo failure producing open wire.
    """
    for all_verts in (False, True):
        with BuildSketch() as sk:
            with BuildLine():
                ln1 = JernArc((0, 0), (1, 0), 20, 90)
                ln2 = JernArc((0, 10), (1, 0), 10, 90)
                Line(ln1 @ 1, ln2 @ 1)
                Line(ln1 @ 0, ln2 @ 0)
            make_face()
            vrts = sk.vertices() if all_verts else sk.vertices().sort_by(Axis.Y)[-2:]
            fillet(vrts, RADIUS)

        _assert_valid_fillet(sk)


def test_fillet_line_full_edge_consumed_all_verts():
    """Fillet consuming an entire Line edge between two circle arcs.
    Regresses ChFi2d_FilletAlgo failure producing `ValueError: Could not
    find shared vertex on wire`.
    """
    # all_verts=False: only top two vertices
    with BuildSketch() as sk:
        with BuildLine():
            ln1 = JernArc((0, 0), (1, 0), 20, 90)
            ln2 = JernArc((0, 10), (1, 0), 10, 90)
            Line(ln1 @ 1, ln2 @ 1)
            Line(ln1 @ 0, ln2 @ 0)
        make_face()
        vrts = sk.vertices()
        fillet(vrts, RADIUS)

    _assert_valid_fillet(sk)


def test_fillet_line_all_edges_consumed():
    """Fillet where all edges of the sketch are consumed.
    Regresses 'Face can only be created with closed wires'.
    """
    with BuildSketch() as sk:
        with BuildLine():
            ln1 = JernArc((0, 0), (1, 0), 20, 90)
            ln2 = JernArc((0, 10), (1, 0), 10, 90)
            Line(ln1 @ 1, ln2 @ 1)
            Line(ln1 @ 0, ln2 @ 0)
        make_face()
        with BuildLine():
            cr1 = CenterArc(
                (14.142135623730951, 14.999999999999996, 0.0),
                RADIUS,
                0,
                360,
                mode=Mode.PRIVATE,
            )
            cn1 = ConstrainedLines(
                cr1.edge(),
                (0, 20),
                mode=Mode.PRIVATE,
                selector=lambda lines: lines[1],
            ).edge()
        with Locations(Plane(origin=cn1 @ 0, x_dir=cn1 % 1)):
            Rectangle(20, 20, align=(Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        vrts = sk.vertices()
        fillet(vrts, RADIUS)

    _assert_valid_fillet(sk, 1)


def test_fillet_arc_cutout_all_edges_consumed():
    """all_verts=False fixed by main solver switch;
    all_verts=True required the additional precision fix in _norm_on_period.
    """
    for all_verts in (False, True):
        with BuildSketch() as sk:
            with BuildLine():
                ln1 = JernArc((0, 0), (1, 0), 20, 90)
                ln2 = JernArc((0, 10), (1, 0), 10, 90)
                ln3 = RadiusArc(ln1 @ 1, ln2 @ 1, EDGE_RADIUS)
                Line(ln1 @ 0, ln2 @ 0)
            make_face()
            with BuildLine():
                arc3tan = ConstrainedArcs(
                    ln1,
                    ln2,
                    ln3,
                    sagitta=Sagitta.BOTH,
                    selector=lambda arcs: arcs.sort_by(Axis.Y)[0],
                    mode=Mode.PRIVATE,
                )
                arctancen = ConstrainedArcs(
                    tangency_one=arc3tan.edge(),
                    center=ln1 @ 0,
                    mode=Mode.PRIVATE,
                )
            make_face(arctancen.edge(), mode=Mode.SUBTRACT)
            vrts = sk.vertices() if all_verts else sk.vertices().sort_by(Axis.Y)[-2:]
            fillet(vrts, RADIUS)

        egds = 1 if all_verts else 4
        _assert_valid_fillet(sk, egds)


def test_fillet_spline_full_edge_consumed():
    """Fillet consuming an entire Spline edge between two circle arcs.
    Regresses ChFi2d_FilletAlgo failure producing open wire for certain splines.
    """
    # all_verts=False: only top two vertices
    with BuildSketch() as sk:
        with BuildLine():
            ln1 = JernArc((0, 0), (1, 0), 20, 90)
            ln2 = JernArc((0, 10), (1, 0), 10, 90)
            cln3 = RadiusArc(ln1 @ 1, ln2 @ 1, EDGE_RADIUS, mode=Mode.PRIVATE)
            Spline(cln3 @ 0, cln3 @ 0.5, cln3 @ 1)
            Line(ln1 @ 0, ln2 @ 0)
        make_face()
        vrts = sk.vertices()
        fillet(vrts, RADIUS)

    _assert_valid_fillet(sk)


def test_fillet_ellipse_cutout():
    """Fillet on a sketch with an ellipse cutout — previously produced
    open wire due to small length dangling edge. To solve this example with
    _solve_wire_fillet_corner_geom2dgcc_circ2d2tanrad the changes in _make_2tan_rad_arcs are needed.
    """
    with BuildSketch() as sk:
        with BuildLine():
            ln1 = JernArc((0, 0), (1, 0), 20, 90)
            ln2 = JernArc((0, 10), (1, 0), 10, 90)
            Line(ln1 @ 1, ln2 @ 1)
            Line(ln1 @ 0, ln2 @ 0)
        make_face()
        with Locations((15, 20)):
            Ellipse(10, EDGE_RADIUS, mode=Mode.SUBTRACT)
        vrts = sk.vertices().sort_by(Axis.Y)[-2:]
        fillet(vrts, RADIUS)

    _assert_valid_fillet(sk)
