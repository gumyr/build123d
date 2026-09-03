"""
build123d tests for the workarounds of OpenCascade (OCCT) defects

name: test_occt_workarounds.py
by:   build123d contributors
date: September 2nd 2026

desc:
    Regression tests for the build123d-side mitigations of the OCCT defects
    tracked in the `occt` labelled issues: seam-related UnifySameDomain
    failures (#1428, #590, #1271, #1363, #1123), the UnifySameDomain crash on
    mirrored geometry (#902), tapered extrusion direction (#987) and collapse
    (#567), 2D chamfer of faces with holes (#1216), non-manifold wire edge
    enumeration (#1205), STEP export of offset curves (#745), thick solids from
    lofts (#1351) and the silent empty cut (#1332).

license:

    Copyright 2026 build123d contributors

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

import math
import warnings

import pytest
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.Geom import Geom_Circle, Geom_Line, Geom_OffsetCurve
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopTools import TopTools_ListOfShape

from build123d import (
    IN,
    Align,
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    CenterArc,
    Circle,
    Compound,
    Cylinder,
    Edge,
    Face,
    Helix,
    JernArc,
    Keep,
    LengthMode,
    Line,
    Mode,
    Plane,
    PolarLine,
    Polyline,
    Pos,
    Rectangle,
    RectangleRounded,
    Rot,
    Side,
    Solid,
    Sphere,
    Vector,
    Wire,
    chamfer,
    export_step,
    extrude,
    fillet,
    import_step,
    insert,
    loft,
    make_face,
    make_hull,
    mirror,
    offset,
    revolve,
    split,
    sweep,
)
from build123d.exporters3d import _exact_offset_curve
from build123d.topology.shape_core import (
    _has_mirrored_same_domain_faces,
    _periodic_surfaces,
    unify_same_domain,
)


def raw_boolean(operation, argument, tool):
    """Run an OCCT boolean without build123d's clean()"""
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(argument.wrapped)
    tools.Append(tool.wrapped)
    operation.SetArguments(args)
    operation.SetTools(tools)
    operation.Build()
    return operation.Shape()


class TestUnifySameDomainSeams:
    """UnifySameDomain destroys faces split along the seam of periodic surfaces"""

    def test_sphere_minus_box_keeps_all_caps(self):
        # build123d #1428: the cap crossed by the sphere seam used to vanish
        caps = Sphere(5) - Box(8, 8, 8)
        cap_volume = math.pi * 1**2 * (3 * 5 - 1) / 3
        assert caps.is_valid
        assert len(caps.solids()) == 6
        assert caps.volume == pytest.approx(6 * cap_volume, rel=1e-6)
        assert all(s.volume > 1 for s in caps.solids())

    def test_sphere_plus_box_conserves_volume(self):
        fused = Sphere(5) + Box(8, 8, 8)
        assert fused.is_valid
        assert fused.volume == pytest.approx(599.9646, abs=1e-3)

    def test_box_minus_sphere_dimple(self):
        # build123d #590
        dimpled = Box(2, 2, 2) - Pos(-1.5) * Sphere(1)
        assert dimpled.is_valid
        assert dimpled.volume == pytest.approx(8 - math.pi * 0.5**2 * (3 - 0.5) / 3)

    def test_sphere_bump_fuse(self):
        # build123d #1271: bump whose seam crosses the big sphere
        lat, lon = math.radians(80), math.radians(12.4)
        bump = Pos(
            39 * math.sin(lat) * math.cos(lon),
            39 * math.sin(lat) * math.sin(lon),
            39 * math.cos(lat),
        ) * Sphere(3)
        fused = Sphere(40) + bump
        assert fused.is_valid
        assert fused.volume > Sphere(40).volume
        assert fused.volume == pytest.approx(268113.18, abs=0.1)

    def test_radial_hole_through_revolved_body(self):
        # build123d #1363: result was invalid for some tool seam orientations
        base = revolve(Plane.XZ * Rectangle(6, 20, align=Align.MIN), axis=Axis.Z)
        outer = revolve(
            Plane.XZ * Pos(0, 1) * Rectangle(9, 18, align=Align.MIN), axis=Axis.Z
        )
        inner = revolve(
            Plane.XZ * Pos(6, 1) * Rectangle(3, 18, align=Align.MIN),
            axis=Axis((-25, 0, 0), (0, 0, 1)),
        )
        model = base + (outer - inner)
        for seam_rotation in (-90, 0, 90):
            tool = (
                Pos(0, 0, 10)
                * Rot(X=seam_rotation, Y=90)
                * extrude(Circle(radius=2), amount=10)
            )
            drilled = model - tool
            assert drilled.is_valid, f"invalid for tool rotation {seam_rotation}"
            assert model.volume - drilled.volume == pytest.approx(75.2, abs=0.05)

    def test_hole_through_cylindrical_shell(self):
        # build123d #1123
        arc1 = CenterArc((0, 0), 50, -30, 60)
        arc2 = CenterArc((0, 0), 60, -30, 60)
        face = make_face(
            [arc1, arc2, Line(arc1 @ 0, arc2 @ 0), Line(arc1 @ 1, arc2 @ 1)]
        )
        shell = extrude(face, amount=50)
        tool = Pos(50, 0, 25) * Rot(0, 90, 0) * Cylinder(10, 100)
        holed = shell - tool
        assert holed.is_valid
        assert shell.volume - holed.volume == pytest.approx(3154.8, abs=1)

    def test_unify_same_domain_falls_back_to_no_edge_unification(self):
        raw_cut = raw_boolean(BRepAlgoAPI_Cut(), Sphere(5), Box(8, 8, 8))
        # unguarded OCCT call reproduces the defect
        upgrader = ShapeUpgrade_UnifySameDomain(raw_cut, True, True, True)
        upgrader.Build()
        assert not BRepCheck_Analyzer(upgrader.Shape()).IsValid()
        # guarded call does not
        unified = unify_same_domain(raw_cut)
        assert BRepCheck_Analyzer(unified).IsValid()
        assert Compound.cast(unified).volume == pytest.approx(87.9646, abs=1e-3)

    def test_unify_same_domain_still_simplifies(self):
        # two boxes fused share coplanar faces that must still be merged
        fused = raw_boolean(
            BRepAlgoAPI_Fuse(), Box(1, 1, 1), Pos(1, 0, 0) * Box(1, 1, 1)
        )
        assert len(Compound.cast(fused).faces()) > 6
        assert len(Compound.cast(unify_same_domain(fused)).faces()) == 6


class TestUnifySameDomainMirroredGeometry:
    """UnifySameDomain crash on same-domain sphere/torus faces with different frames"""

    def test_conflicting_frame_detection(self):
        half = split(Sphere(20), Plane.XZ, keep=Keep.TOP)
        mirrored_pair = raw_boolean(BRepAlgoAPI_Fuse(), half, half.mirror(Plane.XZ))
        assert _has_mirrored_same_domain_faces(_periodic_surfaces(mirrored_pair))
        # seam-split faces of ONE sphere are not conflicting
        seam_split = raw_boolean(BRepAlgoAPI_Cut(), Sphere(5), Box(8, 8, 8))
        assert not _has_mirrored_same_domain_faces(_periodic_surfaces(seam_split))
        # separate spheres are not conflicting
        two_spheres = raw_boolean(
            BRepAlgoAPI_Fuse(), Sphere(5), Pos(7, 0, 0) * Sphere(5)
        )
        assert not _has_mirrored_same_domain_faces(_periodic_surfaces(two_spheres))

    def test_half_sphere_fused_with_mirror(self):
        # build123d #902 minimal trigger: crashed OCCT 7.9.x, invalid on 8.0.x
        half = split(Sphere(20), Plane.XZ, keep=Keep.TOP)
        fused = half + half.mirror(Plane.XZ)
        assert fused.is_valid
        assert fused.volume == pytest.approx(Sphere(20).volume, rel=1e-6)

    def test_mirror_operation_of_revolved_part(self):
        # build123d #902 (reduced): revolve then mirror twice
        with BuildPart() as part:
            with BuildSketch(Plane.YZ) as sketch:
                with BuildLine():
                    JernArc((0, 0), (1, 0), 40, 90)
                    Line((0, 46), (42, 46))
                make_hull()
            with BuildSketch(Plane.YZ) as sketch2:
                arc = sketch.edges().sort_by(Axis.Y)[:-1].sort_by(Axis.X)[1:]
                make_face(offset(arc, amount=8, side=Side.LEFT))
                Rectangle(46, 16, align=Align.MIN)
                insert(sketch, mode=Mode.INTERSECT)
            extrude(sketch2.sketch, amount=50)
            fillet(
                part.faces()
                .filter_by(Plane.XY)
                .sort_by(Axis.Y)[0]
                .edges()
                .sort_by(Axis.Y)[-1],
                8,
            )
            revolve(part.faces().sort_by(Axis.X)[0], axis=Axis.Z, revolution_arc=90)
            quarter_volume = part.part.volume
            mirror(about=Plane.YZ.offset(50))
            mirror(about=Plane.XZ)
        assert part.part.is_valid
        assert part.part.volume == pytest.approx(4 * quarter_volume, rel=1e-6)


class TestTaperedExtrude:
    def test_reversed_profile_face_extrudes_along_normal(self):
        # build123d #987
        with BuildSketch() as sketch:
            with BuildLine():
                right = Line((0, 0), (0, -20))
                bottom = PolarLine(start=right @ 1, length=10, angle=184)
                left = PolarLine(
                    start=bottom @ 1,
                    length=(right @ 0).Y - (bottom @ 1).Y,
                    angle=94,
                    length_mode=LengthMode.VERTICAL,
                )
                Line(left @ 1, right @ 0)
            make_face()
        face = sketch.sketch.face()
        assert face.normal_at() == Vector(0, 0, 1)
        straight = extrude(face, amount=5)
        tapered = extrude(face, amount=5, taper=1)
        assert tapered.bounding_box().min.Z == pytest.approx(0, abs=1e-6)
        assert tapered.bounding_box().max.Z == pytest.approx(5, abs=1e-6)
        assert 0 < straight.volume - tapered.volume < 20

    def test_collapsing_taper_raises(self):
        # build123d #567: OCCT returns an open shell without error
        cross = (Rectangle(10, 1) + Rectangle(1, 10)).face()
        assert extrude(cross, amount=2, taper=10).is_valid
        with pytest.raises(ValueError, match="collapses"):
            extrude(cross, amount=2, taper=15)


class TestChamfer2dWithHoles:
    def test_face_chamfer_keeps_hole(self):
        # build123d #1216
        hole_face = Face.make_rect(20, 20) - Face.make_rect(5, 5)
        corner = hole_face.vertices().group_by(Axis.Y)[-1].sort_by(Axis.X)[0]
        chamfered = hole_face.chamfer_2d(2, 2, [corner])
        assert chamfered.is_valid
        assert len(chamfered.inner_wires()) == 1
        assert chamfered.area == pytest.approx(375 - 2)

    def test_sketch_chamfer_keeps_hole(self):
        with BuildSketch() as sketch:
            Rectangle(20, 20)
            Rectangle(5, 5, mode=Mode.SUBTRACT)
            chamfer(sketch.vertices().group_by(Axis.Y)[-1], length=2)
        face = sketch.sketch.face()
        assert face.is_valid
        assert len(face.inner_wires()) == 1
        assert face.area == pytest.approx(375 - 2 * 2)


class TestNonManifoldWireEdges:
    def test_branching_wire_reports_all_edges(self):
        # build123d #1205
        line = Line((0, 0), (30, 0))
        star = line + Rot(Z=-120) * line + Rot(Z=120) * line
        assert isinstance(star, Wire)
        assert len(star.edges()) == 3
        assert star.length == pytest.approx(90)
        both = star + Rot(Z=60) * star
        assert len(both.edges()) == 6
        assert both.length == pytest.approx(180)

    def test_ordinary_wire_unchanged(self):
        wire = Wire.make_polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        edges = wire.edges()
        assert len(edges) == 4
        # connection order preserved
        for first, second in zip(edges, edges[1:]):
            assert first.end_point() == second.start_point()


class TestStepExportOffsetCurves:
    def test_offset_curve_prism_round_trips(self, tmp_path):
        # build123d #745
        unit = IN
        sketch = Compound(
            children=[
                Pos(Z=0) * Rectangle(6 * unit, 4 * unit),
                Pos(Z=1 * unit) * Rectangle(5 * unit, 3 * unit),
            ]
        )
        solid = loft(sketch.faces(), ruled=True)
        shell = offset(solid, amount=-unit / 16, openings=solid.faces().sort_by()[0])
        face = shell.faces().sort_by()[-2]
        boss = extrude(offset(-face, amount=-0.25 * unit), -0.5 * unit)
        assert any(e.geom_type.name == "OFFSET" for e in boss.edges())
        step_file = tmp_path / "boss.step"
        export_step(boss, step_file)
        imported = import_step(step_file)
        assert len(imported.solids()) == 1
        assert imported.volume == pytest.approx(boss.volume, rel=1e-6)
        # the exported object itself is untouched
        assert any(e.geom_type.name == "OFFSET" for e in boss.edges())

    def test_analytic_offset_curves_stay_analytic(self, tmp_path):
        # an offset of a circle is a circle and must not become a B-spline
        circle = Geom_Circle(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 5)
        arc = Edge(
            BRepBuilderAPI_MakeEdge(
                Geom_OffsetCurve(circle, 2.0, gp_Dir(0, 0, 1)), 0, math.pi / 2
            ).Edge()
        )
        assert arc.geom_type.name == "OFFSET"
        profile = Face(Wire([arc, Line((0, 7), (0, 0)), Line((0, 0), (7, 0))]))
        solid = Pos(10, 5, 1) * Rot(0, 0, 30) * extrude(profile, amount=3)
        step_file = tmp_path / "arc.step"
        export_step(solid, step_file)
        imported = import_step(step_file)
        assert imported.volume == pytest.approx(solid.volume, rel=1e-6)
        assert imported.bounding_box().min == solid.bounding_box().min
        assert {e.geom_type.name for e in imported.edges()} == {"CIRCLE", "LINE"}


class TestLoftThickSolid:
    def test_loft_to_offset_can_be_hollowed(self):
        # build123d #1351
        profile = RectangleRounded(73.2, 41.2, 7)
        lofted = loft([offset(profile, -1).face(), (Pos(Z=40) * profile).face()])
        assert lofted.is_valid
        assert all(e.geom_type.name != "BEZIER" for e in lofted.edges())
        hollow = offset(lofted, -1, openings=lofted.faces().filter_by(Axis.Z))
        assert hollow.is_valid
        assert 0 < hollow.volume < lofted.volume


class TestSuspiciousEmptyCut:
    def test_helical_groove_cut_warns(self):
        # build123d #1332: OCCT returns an empty shape without error
        pitch, height, radius, depth = 2.0, 10.0, 8.0, 1.0
        path = Helix(
            pitch=pitch, height=height + 2 * pitch, radius=radius, center=(0, 0, -pitch)
        )
        start, tangent = path @ 0, path % 0
        section_plane = Plane(
            origin=start, x_dir=Vector(start.X, start.Y, 0).normalized(), z_dir=tangent
        )
        half_width = pitch * 0.25
        profile = section_plane * make_face(
            Polyline([(0.05, -half_width), (0.05, half_width), (-depth, 0)], close=True)
        )
        tool = sweep(profile, path=path, is_frenet=True)
        cylinder = Cylinder(
            radius, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        with pytest.warns(UserWarning, match="empty shape"):
            result = cylinder - tool
        if result.volume == 0:  # the OCCT defect is present
            assert len(result.faces()) == 0

    def test_legitimate_empty_cut_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = Box(1, 1, 1) - Box(3, 3, 3)
        assert result.volume == 0


class TestExactOffsetCurves:
    def test_offset_of_line_exports_as_line(self, tmp_path):
        line = Geom_Line(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0))
        edge = Edge(
            BRepBuilderAPI_MakeEdge(
                Geom_OffsetCurve(line, 2.0, gp_Dir(0, 0, 1)), 0, 5
            ).Edge()
        )
        assert edge.geom_type.name == "OFFSET"
        profile = Face(
            Wire(
                [
                    edge,
                    Line((5, -2), (5, 3)),
                    Line((5, 3), (0, 3)),
                    Line((0, 3), (0, -2)),
                ]
            )
        )
        solid = extrude(profile, amount=2)
        step_file = tmp_path / "line.step"
        export_step(solid, step_file)
        imported = import_step(step_file)
        assert imported.volume == pytest.approx(solid.volume)
        assert {e.geom_type.name for e in imported.edges()} == {"LINE"}

    def test_non_analytic_cases_are_not_converted_exactly(self):
        circle = Geom_Circle(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 5)
        assert _exact_offset_curve(circle) is None
        tilted = Geom_OffsetCurve(circle, 1.0, gp_Dir(1, 0, 1))
        assert _exact_offset_curve(tilted) is None
        vanishing = Geom_OffsetCurve(circle, -5.0, gp_Dir(0, 0, 1))
        assert _exact_offset_curve(vanishing) is None
        line = Geom_Line(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0))
        degenerate = Geom_OffsetCurve(line, 1.0, gp_Dir(1, 0, 0))
        assert _exact_offset_curve(degenerate) is None


class TestUnifySameDomainFallbacks:
    def test_all_variants_invalid_keeps_input(self, monkeypatch):
        import build123d.topology.shape_core as shape_core

        raw_cut = raw_boolean(BRepAlgoAPI_Cut(), Sphere(5), Box(8, 8, 8))
        upgrader = ShapeUpgrade_UnifySameDomain(raw_cut, True, True, True)
        upgrader.Build()
        invalid = upgrader.Shape()
        monkeypatch.setattr(shape_core, "_unify_same_domain", lambda *_: invalid)
        with pytest.warns(UserWarning, match="Unable to simplify"):
            assert unify_same_domain(raw_cut).IsSame(raw_cut)

    def test_exception_in_fallback_keeps_input(self, monkeypatch):
        import build123d.topology.shape_core as shape_core

        raw_cut = raw_boolean(BRepAlgoAPI_Cut(), Sphere(5), Box(8, 8, 8))
        original = shape_core._unify_same_domain

        def failing_fallback(shape, unify_edges, unify_faces):
            if not unify_edges:
                raise RuntimeError("simulated OCCT failure")
            return original(shape, unify_edges, unify_faces)

        monkeypatch.setattr(shape_core, "_unify_same_domain", failing_fallback)
        with pytest.warns(UserWarning, match="Unable to simplify"):
            assert unify_same_domain(raw_cut).IsSame(raw_cut)

    def test_boolean_warns_when_clean_raises(self, monkeypatch):
        import build123d.topology.shape_core as shape_core

        def failing(_shape):
            raise RuntimeError("simulated OCCT failure")

        monkeypatch.setattr(shape_core, "unify_same_domain", failing)
        with pytest.warns(UserWarning, match="unable to clean"):
            assert (Box(2, 2, 2) - Box(1, 1, 1)).volume == pytest.approx(7)

    def test_suspicious_cut_check_tolerates_bad_shapes(self, monkeypatch):
        from build123d.topology.shape_core import _is_suspicious_empty_cut

        def failing_volume(_self):
            raise RuntimeError("simulated OCCT failure")

        monkeypatch.setattr(Solid, "volume", property(failing_volume))
        empty = raw_boolean(BRepAlgoAPI_Cut(), Box(1, 1, 1), Box(3, 3, 3))
        assert not _is_suspicious_empty_cut(empty, [Box(1, 1, 1)], [Box(2, 2, 2)])


class TestChamfer2dEdgeCases:
    def test_no_vertices_returns_face(self):
        face = Face.make_rect(20, 20)
        assert face.chamfer_2d(2, 2, []) is face

    def test_reversed_face_keeps_its_normal(self):
        hole_face = -(Face.make_rect(20, 20) - Face.make_rect(5, 5))
        corner = hole_face.vertices().group_by(Axis.Y)[-1].sort_by(Axis.X)[0]
        chamfered = hole_face.chamfer_2d(2, 2, [corner])
        assert chamfered.normal_at() == hole_face.normal_at()
        assert chamfered.area == pytest.approx(375 - 2)


class TestOffsetNoOp:
    def test_unhollowed_offset_raises(self):
        from build123d import Kind, SlotOverall

        lofted = loft([SlotOverall(10, 6).face(), Pos(Z=4) * SlotOverall(6, 4).face()])
        top = lofted.faces().sort_by(Axis.Z)[-1]
        try:
            hollow = offset(lofted, -0.5, openings=top, kind=Kind.ARC)
        except RuntimeError as err:  # OpenCascade returned the input unchanged
            assert "not hollowed" in str(err)
        else:  # or OpenCascade got it right
            assert hollow.is_valid and hollow.volume < lofted.volume / 2
