import unittest

from build123d.build_enums import SheetSurface
from math import pi
from unittest.mock import patch

import OCP.TopAbs as ta
from OCP.BRep import BRep_Builder
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Shell

from build123d import (
    Axis,
    Box,
    BuildSheet,
    BuildSketch,
    Edge,
    Face,
    GeomType,
    Keep,
    Plane,
    Pos,
    Rectangle,
    Shell,
    Solid,
    Vector,
    Wire,
    flange,
)
from build123d.topology.utils import _make_topods_shell, _topods_material_side
from build123d.sheet_utils import (
    SheetMetalParameters,
    _DevelopedFace,
    _move_developed_face,
    _ordered_developed_edge_points,
    _place_adjacent_developed_face,
    _unfold_shell,
    _uv_topods_edge,
    _uv_topods_face_with_map,
    bend_allowance,
    neutral_radius,
    reference_radius,
    surface_arc,
    surface_offset,
)


class TestSheetUtils(unittest.TestCase):
    def test_non_positive_neutral_radius(self):
        # an OUTSIDE reference face of radius 1 on a 2 thick sheet puts the
        # inside of the bend at radius -1
        parameters = SheetMetalParameters(
            thickness=2, k_factor=0.25, sheet_surface=SheetSurface.OUTSIDE
        )
        with self.assertRaisesRegex(ValueError, "non-positive neutral radius"):
            neutral_radius(1, parameters, positive_bend=True)

    def test_surface_offset_is_measured_from_the_inside_of_the_bend(self):
        """The reference surface is a fixed layer of the sheet; the inside of
        the bend changes side with the bend direction."""
        expected = {
            SheetSurface.INSIDE: (0.0, 3.0),
            SheetSurface.OUTSIDE: (3.0, 0.0),
            SheetSurface.MID: (1.5, 1.5),
            SheetSurface.NEUTRAL: (0.99, 2.01),
        }
        for surface, (up, down) in expected.items():
            parameters = SheetMetalParameters(
                thickness=3, k_factor=0.33, sheet_surface=surface
            )
            with self.subTest(surface=surface):
                self.assertAlmostEqual(surface_offset(parameters, True), up, 9)
                self.assertAlmostEqual(surface_offset(parameters, False), down, 9)

    def test_neutral_radius_is_the_same_for_both_bend_directions(self):
        """From any reference surface, bent either way, the neutral fibre of a
        bend of inside radius 2 on a 3 thick sheet with k = 0.33 is at 2.99."""
        for surface in SheetSurface:
            parameters = SheetMetalParameters(
                thickness=3, k_factor=0.33, sheet_surface=surface
            )
            for positive in (True, False):
                with self.subTest(surface=surface, positive=positive):
                    shell_radius = reference_radius(
                        2, parameters, 90 if positive else -90
                    )
                    self.assertAlmostEqual(
                        neutral_radius(shell_radius, parameters, positive), 2.99, 9
                    )

    def test_bend_allowance_and_surface_arc(self):
        parameters = SheetMetalParameters(
            thickness=3, k_factor=0.33, sheet_surface=SheetSurface.OUTSIDE
        )
        # the allowance is the neutral arc, whatever the surface and direction
        self.assertAlmostEqual(bend_allowance(2, 90, parameters), 2.99 * pi / 2, 9)
        self.assertAlmostEqual(bend_allowance(2, -90, parameters), 2.99 * pi / 2, 9)
        # the arc on the reference surface is what the shell carries
        self.assertAlmostEqual(surface_arc(2, 90, parameters), 5 * pi / 2, 9)
        self.assertAlmostEqual(surface_arc(2, -90, parameters), 2 * pi / 2, 9)

    def test_raw_uv_edge_preserves_orientation(self):
        face = Face.make_rect(2, 1)
        source = face.edges()[0]
        developed = _uv_topods_edge(face.wrapped, source.wrapped)
        reversed_developed = _uv_topods_edge(
            face.wrapped, TopoDS.Edge(source.wrapped.Reversed())
        )

        forward, backward = Edge(developed), Edge(reversed_developed)
        self.assertLess((forward @ 0 - backward @ 1).length, 1e-6)
        self.assertLess((forward @ 1 - backward @ 0).length, 1e-6)

    def test_raw_uv_face_edge_provenance(self):
        face = Solid.make_cylinder(2, 3).faces().filter_by(GeomType.CYLINDER)[0]
        developed, edge_map = _uv_topods_face_with_map(face.wrapped)
        developed_edges: list[TopoDS_Edge] = []
        explorer = TopExp_Explorer(developed, ta.TopAbs_EDGE)
        while explorer.More():
            developed_edges.append(TopoDS.Edge(explorer.Current()))
            explorer.Next()

        self.assertEqual(len(edge_map), len(face.edges()))
        for source_key, (source_edge, developed_edge) in edge_map.items():
            self.assertEqual(source_key, hash(source_edge))
            self.assertTrue(
                any(developed_edge.IsSame(edge) for edge in developed_edges)
            )

    def test_uv_face_reports_missing_edge_provenance(self):
        with patch("build123d.sheet_utils._edges_match", return_value=False):
            with self.assertRaisesRegex(ValueError, "assembled UV edge"):
                _uv_topods_face_with_map(Face.make_rect(2, 1).wrapped)

    def test_ordered_edge_points(self):
        reference = Edge.make_line((0, 0), (1, 0))
        developed = Edge.make_line((10, 0), (11, 0))
        reversed_source = TopoDS.Edge(reference.wrapped.Reversed())

        start, end = _ordered_developed_edge_points(
            (reversed_source, developed.wrapped), reference.wrapped
        )
        self.assertEqual(start, Vector(11, 0, 0))
        self.assertEqual(end, Vector(10, 0, 0))

        unrelated = Edge.make_line((0, 1), (1, 1))
        with self.assertRaisesRegex(ValueError, "associate shared-edge endpoints"):
            _ordered_developed_edge_points(
                (unrelated.wrapped, developed.wrapped), reference.wrapped
            )

    def test_moved_developed_face_uses_locations(self):
        source = Face.make_rect(2, 1)
        face, edge_map = _uv_topods_face_with_map(source.wrapped)
        developed = _DevelopedFace(face, edge_map)
        moved = _move_developed_face(developed, Pos(5, 2))

        self.assertAlmostEqual(Face(moved.face).center().X, Face(face).center().X + 5)
        self.assertAlmostEqual(Face(moved.face).center().Y, Face(face).center().Y + 2)
        self.assertTrue(Face(moved.face).is_valid)
        self.assertEqual(set(moved.edges), set(developed.edges))

    def test_missing_shared_edge_provenance(self):
        face = Face.make_rect(2, 1).wrapped
        edge = Face(face).edges()[0].wrapped
        developed = _DevelopedFace(face, {})
        with self.assertRaisesRegex(ValueError, "missing from a developed-face map"):
            _place_adjacent_developed_face(developed, developed, edge)

    def test_single_and_disconnected_shell_construction(self):
        face = Face.make_rect(2, 1)
        shell = _make_topods_shell([face.wrapped])
        self.assertTrue(Shell(shell).is_valid)
        self.assertEqual(len(Shell(shell).faces()), 1)

        separated = Pos(5, 0) * face
        with self.assertRaisesRegex(ValueError, "one connected shell"):
            _make_topods_shell([face.wrapped, separated.wrapped])
        with self.assertRaisesRegex(ValueError, "at least one face"):
            _make_topods_shell([])

    def test_raw_unfold_validation(self):
        with self.assertRaisesRegex(ValueError, "non-empty Shell"):
            _unfold_shell(TopoDS_Shell(), None)

        cylinder = Solid.make_cylinder(2, 3)
        cylindrical_face = cylinder.faces().filter_by(GeomType.CYLINDER)[0]
        with self.assertRaisesRegex(ValueError, "at least one planar face"):
            _unfold_shell(Shell(cylindrical_face).wrapped, None)

        disconnected = TopoDS_Shell()
        builder = BRep_Builder()
        builder.MakeShell(disconnected)
        builder.Add(disconnected, Face.make_rect(1, 1).wrapped)
        builder.Add(disconnected, (Pos(5, 0) * Face.make_rect(1, 1)).wrapped)
        with self.assertRaisesRegex(ValueError, "disconnected face groups"):
            _unfold_shell(disconnected, None)

    def test_material_side_reads_the_face_not_the_edge_given(self):
        """The side the material is on is fixed by how the face walks its
        edge, so a reversed or moved copy of the edge gives the same answer,
        and an edge of some other shape is refused"""
        face = Face.make_rect(20, 10)
        right = face.edges().sort_by(Axis.X)[-1]
        inward = Vector(-1, 0, 0)
        for candidate in (
            right,
            right.reversed(),
            face.moved(Pos(7, 0)).edges().sort_by(Axis.X)[-1],
        ):
            self.assertAlmostEqual(
                _topods_material_side(face.wrapped, candidate.wrapped), inward, 6
            )
        # a hole's edges run the other way, and the material is outside them
        holed = Face.make_rect(20, 10).make_holes([Wire.make_circle(2)])
        hole_edge = holed.inner_wires()[0].edges()[0]
        side = _topods_material_side(holed.wrapped, hole_edge.wrapped)
        self.assertGreater(side.dot(hole_edge.position_at(0.5)), 0)
        with self.assertRaisesRegex(ValueError, "not an edge of the face"):
            _topods_material_side(face.wrapped, Edge.make_line((0, 0), (1, 0)).wrapped)

    def test_faces_sharing_a_curved_edge_are_placed(self):
        """Which side of a shared edge a face lies on is read from the face's
        own traversal of it, so the edge need not be straight: a flat split
        along an arc unfolds in one piece with its bend"""
        with BuildSheet(thickness=1, bend_radius=2) as builder:
            with BuildSketch():
                Rectangle(40, 30)
            flange(builder.rims().sort_by(Axis.X)[-1], length=10)
        sheet = builder.sheet
        base = sheet.flats().sort_by(Axis.Z)[0]
        arc = (
            Solid.make_cylinder(8, 5, Plane.XY.offset(-2))
            .faces()
            .filter_by(GeomType.CYLINDER)[0]
        )
        pieces = [f for f in base.split(arc, keep=Keep.BOTH) if isinstance(f, Face)]
        self.assertEqual(len(pieces), 2)
        others = [f for f in sheet.faces() if not f.is_same(base)]
        split = Shell(Face.sew_faces(pieces + others)[0])
        self.assertEqual(len(split.faces()), 4)

        flat = Shell(_unfold_shell(split.wrapped, builder.sheet_parameters))
        self.assertTrue(flat.is_valid)
        self.assertEqual(len(flat.faces()), 4)
        whole = Shell(_unfold_shell(sheet.wrapped, builder.sheet_parameters))
        self.assertAlmostEqual(flat.area, whole.area, 6)

    def test_closed_shell_requires_a_cut(self):
        with self.assertRaisesRegex(ValueError, "requires a cut"):
            _unfold_shell(Box(1, 1, 1).shell().wrapped, None)

    def test_invalid_unfold_result_is_rejected(self):
        shell = Shell(Face.make_rect(2, 1)).wrapped
        with patch("build123d.sheet_utils.BRepCheck_Analyzer") as analyzer:
            analyzer.return_value.IsValid.return_value = False
            with self.assertRaisesRegex(ValueError, "invalid flat Shell"):
                _unfold_shell(shell, None)


if __name__ == "__main__":
    unittest.main()
