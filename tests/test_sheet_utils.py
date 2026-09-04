import unittest
from unittest.mock import patch

import OCP.TopAbs as ta
from OCP.BRep import BRep_Builder
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Shell

from build123d import Box, Edge, Face, GeomType, Pos, Shell, Solid, Vector
from build123d.sheet_utils import (
    SheetMetalParameters,
    _DevelopedFace,
    _edge_position,
    _make_shell,
    _move_developed_face,
    _ordered_developed_edge_points,
    _place_adjacent_developed_face,
    _unfold_shell,
    _uv_topods_edge,
    _uv_topods_face_with_map,
    neutral_radius,
)


class TestSheetUtils(unittest.TestCase):
    def test_non_positive_neutral_radius(self):
        parameters = SheetMetalParameters(thickness=2, k_factor=1)
        with self.assertRaisesRegex(ValueError, "non-positive neutral radius"):
            neutral_radius(1, parameters, positive_bend=False)

    def test_raw_uv_edge_preserves_orientation(self):
        face = Face.make_rect(2, 1)
        source = face.edges()[0]
        developed = _uv_topods_edge(face.wrapped, source.wrapped)
        reversed_developed = _uv_topods_edge(
            face.wrapped, TopoDS.Edge(source.wrapped.Reversed())
        )

        self.assertLess(
            (
                _edge_position(developed, 0) - _edge_position(reversed_developed, 1)
            ).length,
            1e-6,
        )
        self.assertLess(
            (
                _edge_position(developed, 1) - _edge_position(reversed_developed, 0)
            ).length,
            1e-6,
        )

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
        shell = _make_shell([face.wrapped])
        self.assertTrue(Shell(shell).is_valid)
        self.assertEqual(len(Shell(shell).faces()), 1)

        separated = Pos(5, 0) * face
        with self.assertRaisesRegex(ValueError, "one connected Shell"):
            _make_shell([face.wrapped, separated.wrapped])

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
