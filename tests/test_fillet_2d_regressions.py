# tests/test_fillet_2d_regressions.py

import pytest
from build123d import *
from ocp_vscode import show_object

r = 5  # fillet radius
tr = 5.0001  # arc/spline/ellipse 'radius'
# TOLERANCE = 1e-6


def _assert_valid_fillet(sk, number_of_edges:int = 4):
    assert len(sk.edges()) == number_of_edges
    # assert sk.area > 0
    # assert all(e.length > TOLERANCE for e in sk.edges())


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
            fillet(vrts, r)

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
        fillet(vrts, r)

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
                r, 0, 360, mode=Mode.PRIVATE,
            )
            cn1 = ConstrainedLines(
                cr1.edge(), (0, 20), mode=Mode.PRIVATE,
                selector=lambda lines: lines[1],
            ).edge()
        with Locations(Plane(origin=cn1 @ 0, x_dir=cn1 % 1)):
            Rectangle(20, 20, align=(Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        vrts = sk.vertices()
        fillet(vrts, r)

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
                ln3 = RadiusArc(ln1 @ 1, ln2 @ 1, tr)
                Line(ln1 @ 0, ln2 @ 0)
            make_face()
            with BuildLine():
                arc3tan = ConstrainedArcs(
                    ln1, ln2, ln3,
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
            fillet(vrts, r)

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
            cln3 = RadiusArc(ln1 @ 1, ln2 @ 1, 5.001, mode=Mode.PRIVATE)
            ln3 = Spline(cln3 @ 0, cln3 @ 0.5, cln3 @ 1)
            Line(ln1 @ 0, ln2 @ 0)
        make_face()
        vrts = sk.vertices()
        fillet(vrts, r)

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
            Ellipse(10, 5, mode=Mode.SUBTRACT)
        vrts = sk.vertices().sort_by(Axis.Y)[-2:]
        fillet(vrts, r)

    _assert_valid_fillet(sk)
