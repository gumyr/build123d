"""User-visible behavior of tags on sub-shapes."""

from copy import copy, deepcopy
import pickle
import unittest

from build123d import (
    Axis,
    Box,
    BuildPart,
    Face,
    Mode,
    Plane,
    Pos,
    Solid,
    insert,
    fillet,
    extrude,
)


class TestSubshapeTags(unittest.TestCase):
    def setUp(self):
        self.plate = Solid.make_box(12, 10, 4)
        self.top = self.plate.faces().sort_by(Axis.Z)[-1]
        self.plate.tag(self.top, datum="top")

    def test_split_and_removed(self):
        slot = Solid.make_box(2, 12, 6, Plane((5, -1, -1)))
        result = self.plate.cut(slot)
        self.assertEqual([round(s.area) for s in result.tagged("datum")], [50, 50])
        result.tag(result.tagged("datum")[0], finish="grind")
        self.assertEqual(len(result.tagged("finish")), 1)
        self.assertFalse(self.plate.tagged("finish"))
        pin = Solid.make_cylinder(1, 3, Plane((2, 2, 4)))
        pin.tag(pin.faces().sort_by(Axis.Z)[0], contact=True)
        self.assertFalse(self.plate.fuse(pin).tagged("contact"))

    def test_ordered_merge_and_relocated_occurrences(self):
        cap = Solid.make_box(12, 10, 2, Plane((0, 0, 4)))
        self.plate.tag(self.plate.faces().sort_by(Axis.X)[0], operation="mill")
        cap.tag(cap.faces().sort_by(Axis.X)[0], operation="grind", tolerance=0.1)
        joined = self.plate.fuse(cap)
        (face,) = joined.tagged("tolerance")
        self.assertEqual(
            joined.tags(face),
            {
                "operation": "mill",
                "tolerance": 0.1,
                "_conflicts": {"operation": ["grind"]},
            },
        )
        moved = Pos(20, 0, 5) * self.plate
        (top,) = moved.tagged("datum")
        self.assertTrue(top.is_same(moved.faces().sort_by(Axis.Z)[-1]))
        self.assertFalse(moved.tags(self.top))
        moved.tag(top, datum="changed")
        self.assertEqual(self.plate.tags(self.top), {"datum": "top"})

    def test_copies_and_other_operations(self):
        for shape in (
            copy(self.plate),
            deepcopy(self.plate),
            self.plate.mirror(Plane.YZ),
            self.plate.scale(1.5),
            self.plate.scale((1.0, 1.5, 2.0)),
            pickle.loads(pickle.dumps(self.plate)),
        ):
            with self.subTest(shape=shape):
                (face,) = shape.tagged("datum")
                self.assertIn(face, shape.faces())
                self.assertEqual(shape.tags(face), {"datum": "top"})
        rounded = self.plate.fillet(0.5, [self.plate.edges().sort_by(Axis.Z)[0]])
        self.assertEqual(len(rounded.tagged("datum")), 1)

    def test_generated_faces_require_opt_in(self):
        profile = Face.make_rect(10, 12)
        left, right = profile.edges().sort_by(Axis.X)[::3]
        profile.tag(left, process="hone", _inherit=True)
        profile.tag(right, datum="ordinary")
        solid = Solid.extrude(profile, (0, 0, 5))
        self.assertTrue(any(isinstance(s, Face) for s in solid.tagged("process")))
        self.assertFalse(any(isinstance(s, Face) for s in solid.tagged("datum")))

    def test_builder_and_boolean_algebra(self):
        with BuildPart() as build:
            insert(self.plate)
            build.tag(build.faces().sort_by(Axis.Z)[-1], side="upper")
            Box(2, 25, 12, mode=Mode.SUBTRACT)
        self.assertTrue(build.part.tagged("datum"))
        self.assertTrue(build.part.tagged("side"))
        cut = self.plate - Solid.make_box(2, 12, 6, Plane((5, -1, -1)))
        self.assertEqual(len(cut.tagged("datum")), 2)

    def test_public_fillet_and_extrude(self):
        block = Box(12, 10, 4)
        block.tag(block.faces().sort_by(Axis.Z)[-1], datum="top")
        rounded = fillet(block.edges().sort_by(Axis.Z)[0], radius=0.3)
        (top,) = rounded.tagged("datum")
        self.assertIn(top, rounded.faces())

        profile = Face.make_rect(12, 10)
        profile.tag(profile.edges()[0], finish="grind", _inherit=True)
        prism = extrude(profile, amount=3)
        self.assertTrue(any(isinstance(s, Face) for s in prism.tagged("finish")))

    def test_repeated_occurrences_keep_independent_tags(self):
        from build123d import Compound

        other = Pos(20, 0, 0) * self.plate
        other.tag(other.tagged("datum")[0], datum="second")
        assembly = Compound([self.plate, other])
        self.assertEqual(
            [
                assembly.tags(s)["datum"]
                for s in assembly.tagged("datum").sort_by(Axis.X)
            ],
            ["top", "second"],
        )

    def test_tag_on_assembly_is_transformed_and_drops_with_its_child(self):
        from build123d import Compound

        small = Box(1, 2, 3)
        other = Pos(5, 0, 0) * Box(2, 2, 2)
        assembly = Compound(children=[small, other])
        assembly.tag(small.faces().sort_by(Axis.Z)[-1], datum="top")
        placed = Pos(10, 7, 4) * assembly
        duplicate = deepcopy(placed)
        (kept,) = duplicate.tagged("datum")
        self.assertIn(kept, duplicate.faces())
        self.assertEqual(kept.center(), placed.tagged("datum")[0].center())
        mirrored = assembly.mirror(Plane.XZ)
        (face,) = mirrored.tagged("datum")
        self.assertIn(face, mirrored.faces())
        assembly.children = [other]
        self.assertFalse(assembly.tagged("datum"))

    def test_unrelated_shapes_and_atomic_tagging(self):
        other = Solid.make_box(1, 1, 1).faces()[0]
        with self.assertRaises(ValueError):
            self.plate.tag([self.top, other], missing=True)
        self.assertFalse(self.plate.tagged("missing"))
