"""
build123d tests

name: test_history.py
by:   Gumyr
date: September 10, 2026

desc:
    Unit tests for ShapeHistory, the record of what an operation did to the
    sub-shapes of its inputs.

license:

    Copyright 2026 Gumyr

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

import unittest

from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.TopTools import TopTools_ListOfShape
from OCP.gp import gp_Vec

from build123d.build_enums import Align, GeomType, Select
from build123d.geometry import Axis, Plane, Pos
from build123d.objects_curve import Line
from build123d.objects_part import Box, Cylinder, Sphere
from build123d.objects_sketch import Rectangle
from build123d.operations_generic import fillet
from build123d.topology import Curve, Edge, Face, ShapeHistory, Solid
from build123d.topology.history import tracked_subshapes
from build123d.topology.kernel import list_shapes


class TestShapeHistory(unittest.TestCase):
    def setUp(self):
        self.box = Solid.make_box(10, 10, 10)
        self.top = self.box.faces().sort_by(Axis.Z)[-1]

    def test_boolean_records_untouched_modified_removed_and_generated(self):
        """A cylinder standing on the box: the top is rebuilt around the
        cylinder's own bottom circle, the cylinder's bottom cap is removed,
        everything else is left alone and nothing is generated."""
        cylinder = Solid.make_cylinder(2, 5, Plane((5, 5, 10)))
        fused = self.box.fuse(cylinder)
        history = fused._history
        self.assertIsInstance(history, ShapeHistory)
        self.assertEqual(len(history.modified(self.top.wrapped)), 1)
        for side in self.box.faces().filter_by(Axis.Z, reverse=True):
            self.assertEqual(history.modified(side.wrapped), [])
            self.assertFalse(history.is_removed(side.wrapped))
        bottom_cap = cylinder.faces().sort_by(Axis.Z)[0]
        self.assertTrue(history.is_removed(bottom_cap.wrapped))
        self.assertEqual(history.generated(self.top.wrapped), [])

        # A cylinder through the box: the circles where it pierces the top and
        # bottom are generated from those faces
        through = self.box.fuse(Solid.make_cylinder(2, 20, Plane((5, 5, -5))))
        history = through._history
        self.assertGreaterEqual(len(history.generated(self.top.wrapped)), 1)
        self.assertEqual(len(history.modified(self.top.wrapped)), 1)

    def test_clean_history_is_merged_into_the_boolean(self):
        """After a fuse and a clean the original face still maps to one face."""
        slab = Solid.make_box(10, 10, 5, Plane((0, 0, 10)))
        fused = self.box.fuse(slab)  # coplanar sides are unified by the clean
        history = fused._history
        side = self.box.faces().sort_by(Axis.X)[0]
        merged = history.modified(side.wrapped)
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(Face(merged[0]).area, 150, 5)

    def test_trace_answers_from_the_result_side(self):
        cylinder = Solid.make_cylinder(2, 20, Plane((5, 5, -5)))
        fused = self.box.fuse(cylinder)
        trace = fused._history.trace([self.box.wrapped])
        kinds = {"untouched": 0, "modified": 0, "generated": 0, "other": 0}
        for face in fused.faces():
            if trace.is_untouched(face.wrapped):
                kinds["untouched"] += 1
            elif trace.is_modified(face.wrapped):
                kinds["modified"] += 1
            elif trace.is_generated(face.wrapped):
                kinds["generated"] += 1
            else:
                kinds["other"] += 1
        # four box sides untouched, top and bottom rebuilt, and the cylinder's
        # faces are not the box's at all
        self.assertEqual(
            kinds, {"untouched": 4, "modified": 2, "generated": 0, "other": 4}
        )
        circles = [e for e in fused.edges() if trace.is_generated(e.wrapped)]
        self.assertGreaterEqual(len(circles), 2)
        self.assertTrue(all(e.geom_type.name == "CIRCLE" for e in circles))

    def test_algorithm_history_from_a_fillet(self):
        rounded = self.box.fillet(1, self.box.edges().filter_by(Axis.Z))
        trace = rounded._history.trace([self.box.wrapped])
        faces = rounded.faces()
        self.assertEqual(sum(trace.is_modified(f.wrapped) for f in faces), 6)
        self.assertEqual(sum(trace.is_generated(f.wrapped) for f in faces), 4)
        self.assertEqual(sum(trace.is_descendant(f.wrapped) for f in faces), 10)
        # the filleted edges are gone and the fillet faces came from them
        for edge in self.box.edges().filter_by(Axis.Z):
            self.assertTrue(rounded._history.is_removed(edge.wrapped))
            self.assertEqual(len(rounded._history.generated(edge.wrapped)), 1)

    def test_algorithm_history_from_a_prism(self):
        """An extrusion generates faces from edges and edges from vertices."""
        square = Face.make_rect(4, 4)
        prism = BRepPrimAPI_MakePrism(square.wrapped, gp_Vec(0, 0, 5))
        prism.Build()
        history = ShapeHistory.from_algorithm(prism, [square.wrapped], prism.Shape())
        for edge in square.edges():
            self.assertEqual(len(history.generated(edge.wrapped)), 1)
        for vertex in square.vertices():
            self.assertEqual(len(history.generated(vertex.wrapped)), 1)
        self.assertFalse(history.is_removed(square.wrapped))

    def test_sewing_history(self):
        """Sewing rebuilds both faces and merges the shared edge."""
        left = Face.make_rect(4, 4)
        right = Face.make_rect(4, 4, Plane(origin=(4, 0, 0)))
        sewing = BRepBuilderAPI_Sewing(1e-6)
        sewing.Add(left.wrapped)
        sewing.Add(right.wrapped)
        sewing.Perform()
        history = ShapeHistory.from_sewing(sewing, [left.wrapped, right.wrapped])
        for face in (left, right):
            self.assertEqual(len(history.modified(face.wrapped)), 1)
        # the two coincident edges were merged into one edge of the shell
        left_edge = left.edges().sort_by(Axis.X)[-1]
        right_edge = right.edges().sort_by(Axis.X)[0]
        merged_left = history.modified(left_edge.wrapped)
        merged_right = history.modified(right_edge.wrapped)
        self.assertEqual(len(merged_left), 1)
        self.assertTrue(merged_left[0].IsSame(merged_right[0]))

    def test_relocation_history(self):
        moved = self.box.moved(Plane((1, 2, 3)).location)
        history = ShapeHistory.from_relocation(self.box.wrapped, moved.wrapped)
        for face in self.box.faces():
            placed = history.modified(face.wrapped)
            self.assertEqual(len(placed), 1)
            self.assertTrue(placed[0].IsPartner(face.wrapped))
            self.assertFalse(placed[0].IsSame(face.wrapped))
        # nothing moved, nothing recorded
        self.assertFalse(
            ShapeHistory.from_relocation(
                self.box.wrapped, self.box.wrapped
            ).wrapped.HasModified()
        )

    def test_merge_returns_self_and_tolerates_none(self):
        history = ShapeHistory()
        self.assertIs(history.merge(None), history)
        self.assertIs(history.merge(ShapeHistory()), history)

    def test_unsupported_types_are_not_tracked(self):
        history = ShapeHistory()
        wire = self.top.outer_wire()
        self.assertEqual(history.modified(wire.wrapped), [])
        self.assertEqual(history.generated(wire.wrapped), [])
        self.assertFalse(history.is_removed(wire.wrapped))

    def test_helpers(self):
        subs = tracked_subshapes([self.box.wrapped, None])
        self.assertEqual(len(subs), 8 + 12 + 6 + 1)
        kernel_list = TopTools_ListOfShape()
        for face in self.box.faces():
            kernel_list.Append(face.wrapped)
        self.assertEqual(len(list_shapes(kernel_list)), 6)
        self.assertEqual(kernel_list.Extent(), 6)  # the source is not consumed


class TestAlgebraSelect(unittest.TestCase):
    """Select.LAST and Select.NEW on the result of an Algebra operation."""

    def test_fused_sketch(self):
        cross = Rectangle(8, 2)
        cross += Rectangle(2, 8)
        # the four points where the arms cross are new; the second rectangle's
        # corners and the arms' surviving edges are last
        self.assertEqual(len(cross.vertices(Select.NEW)), 4)
        self.assertEqual(len(cross.vertices(Select.LAST)), 8)
        self.assertEqual(len(cross.edges(Select.NEW)), 0)
        self.assertEqual(len(cross.edges(Select.LAST)), 6)
        self.assertTrue(
            all(abs(v.X) == 1 and abs(v.Y) == 1 for v in cross.vertices(Select.NEW))
        )

    def test_fused_part(self):
        part = Box(10, 10, 10) + Pos(Z=5) * Cylinder(
            2, 5, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        last = part.faces(Select.LAST)
        self.assertEqual(len(last), 2)
        self.assertTrue(all(f.center().Z > 5 for f in last))
        self.assertEqual(len(part.solids(Select.NEW)), 1)

    def test_cut_and_intersected_parts(self):
        holed = Box(10, 10, 10) - Cylinder(1, 20)
        self.assertEqual(len(holed.faces(Select.LAST)), 1)
        self.assertEqual(holed.faces(Select.LAST)[0].geom_type, GeomType.CYLINDER)
        self.assertEqual(len(holed.edges(Select.NEW)), 2)
        bar = Box(10, 10, 10) & Box(30, 2, 2)
        self.assertEqual(len(bar.faces(Select.LAST)), 4)
        self.assertEqual(len(bar.faces(Select.NEW)), 0)

    def test_chained_operations_report_the_last_one(self):
        three = (
            Box(10, 10, 10)
            + Pos(Z=5) * Cylinder(1, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
            + Pos(X=5) * Sphere(1)
        )
        self.assertEqual(len(three.faces(Select.LAST)), 1)
        self.assertEqual(three.faces(Select.LAST)[0].geom_type, GeomType.SPHERE)

    def test_everything_of_self_was_there_before(self):
        """A multi-piece left operand: none of its untouched pieces is last."""
        two = Rectangle(2, 2) + Pos(X=5) * Rectangle(2, 2)
        plus = two + Pos(X=5) * Rectangle(1, 4)
        self.assertEqual(len(plus.faces()), 2)
        self.assertEqual(len(plus.faces(Select.LAST)), 1)

    def test_operations_other_than_booleans(self):
        rounded = fillet(Box(10, 10, 10).edges().filter_by(Axis.Z), 1)
        self.assertEqual(len(rounded.faces(Select.LAST)), 4)
        self.assertEqual(len(rounded.edges(Select.NEW)), 16)

    def test_joined_lines(self):
        """Connected edges are joined without a boolean; the join records too."""
        bent = Line((0, 0), (1, 0)) + Line((1, 0), (1, 1))
        self.assertEqual(len(bent.edges()), 2)
        self.assertEqual(len(bent.edges(Select.LAST)), 1)
        self.assertEqual(len(bent.edges(Select.NEW)), 0)
        # both ends of the new line, including the one it shares with the old
        self.assertEqual(len(bent.vertices(Select.LAST)), 2)
        self.assertEqual(len(bent.vertices(Select.NEW)), 0)
        # collinear lines are cleaned into one edge, which still carries the record
        straight = Line((0, 0), (1, 0)) + Line((1, 0), (2, 0))
        self.assertIsInstance(straight, Edge)
        self.assertEqual(len(straight.edges(Select.LAST)), 1)
        self.assertEqual(len(straight.vertices(Select.NEW)), 0)
        # three edges joined into an empty curve: everything was brought in
        chain = Curve() + [
            Line((0, 0), (1, 0)),
            Line((1, 0), (1, 1)),
            Line((1, 1), (0, 1)),
        ]
        self.assertEqual(len(chain.edges(Select.LAST)), 3)

    def test_a_shape_with_no_record_cannot_answer(self):
        with self.assertRaisesRegex(ValueError, "no record"):
            Rectangle(8, 2).vertices(Select.NEW)
        self.assertEqual(len(Rectangle(8, 2).vertices(Select.ALL)), 4)


if __name__ == "__main__":
    unittest.main()
