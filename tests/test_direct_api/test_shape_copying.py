"""
build123d tests

name: test_shape_copying.py
by:   Gumyr
date: October 28, 2026

desc:
    Copies of shapes: what a deep copy, a pickle, a transform and an
    operation carry over, and how an assembly's children follow.

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

import copy
import pickle
import unittest

from build123d.build_enums import GeomType, Keep
from build123d.geometry import Axis, Color, Location, Matrix, Plane, Pos, Vector
from build123d.joints import RigidJoint
from build123d.objects_part import Box, Cylinder
from build123d.topology import Compound, Edge, Face, Shape, Solid


def _assembly() -> Compound:
    small = Box(1, 1, 1)
    small.label = "small"
    large = Pos(5, 0, 0) * Box(2, 2, 2)
    large.label = "large"
    return Compound(children=[small, large], label="pair")


def _shares_geometry(assembly: Compound) -> bool:
    """Do the assembly's compound and its children hold the same geometry?"""
    return all(
        any(face.wrapped.IsPartner(child_face.wrapped) for face in assembly.faces())
        for child in assembly.children
        for child_face in child.faces()
    )


class TestOperationsKeepAttributes(unittest.TestCase):
    def test_add_keeps_label_colour_and_joints(self):
        part = Box(1, 1, 1)
        part.label = "part"
        part.color = Color("red")
        RigidJoint("top", part, Location((0, 0, 0.5)))
        for name, result in (
            ("add", part + Pos(0, 0, 1) * Box(1, 1, 1)),
            ("subtract", part - Pos(0, 0, 0.5) * Box(0.2, 0.2, 2)),
            ("intersect", part & Pos(0, 0, 0.5) * Box(2, 2, 2)),
            ("fuse", part.fuse(Pos(0, 0, 1) * Box(1, 1, 1))),
        ):
            with self.subTest(operation=name):
                self.assertEqual(result.label, "part")
                self.assertEqual(tuple(result.color), tuple(part.color))
                self.assertIs(result.joints["top"].parent, result)
                self.assertIs(part.joints["top"].parent, part)

    def test_attribute_copy_does_not_join_an_assembly(self):
        assembly = _assembly()
        child = assembly.children[0]
        target = Box(1, 1, 1)
        target.parent = assembly
        target.parent = None  # leaves the attribute behind, set to None
        child.copy_attributes_to(target, ["wrapped"])
        self.assertIsNone(target.parent)
        self.assertEqual(len(assembly.children), 2)


class TestTransformsCarryChildren(unittest.TestCase):
    def assertChildrenFollow(self, transformed: Compound, expected: list[Shape]):
        self.assertEqual(len(transformed.children), len(expected))
        for child, expectation in zip(transformed.children, expected):
            self.assertIs(child.parent, transformed)
            self.assertAlmostEqual(child.volume, expectation.volume, 5)
            self.assertAlmostEqual((child.center() - expectation.center()).length, 0, 5)
        self.assertTrue(_shares_geometry(transformed))
        self.assertAlmostEqual(transformed.volume, sum(e.volume for e in expected), 5)

    def test_scale_mirror_rotate_and_transform(self):
        """Each child is transformed as the assembly is: about the assembly's
        location, not its own"""
        assembly = _assembly()
        originals = list(assembly.children)
        about = assembly.location.position
        self.assertChildrenFollow(
            assembly.scale(2), [child.scale(2, about=about) for child in originals]
        )
        self.assertChildrenFollow(
            assembly.scale((2, 1, 1)),
            [child.scale((2, 1, 1), about=about) for child in originals],
        )
        self.assertChildrenFollow(
            assembly.mirror(Plane.YZ), [child.mirror(Plane.YZ) for child in originals]
        )
        self.assertChildrenFollow(
            assembly.rotate(Axis.Z, 90, transform=True),
            [child.rotate(Axis.Z, 90) for child in originals],
        )
        shift = Matrix([[1, 0, 0, 0], [0, 1, 0, 3], [0, 0, 1, 0], [0, 0, 0, 1]])
        shifted = [child.moved(Location((0, 3, 0))) for child in originals]
        self.assertChildrenFollow(assembly.transform_shape(shift), shifted)
        self.assertChildrenFollow(assembly.transform_geometry(shift), shifted)

    def test_a_placed_assembly_is_transformed_where_it_is(self):
        """The children are relative to the assembly, so they are transformed
        where the assembly puts them, not where they are in its frame"""
        assembly = _assembly().moved(Pos(10, 0, 0))
        # scaled about the assembly's location, where the small child sits
        scaled = assembly.scale(2)
        self.assertAlmostEqual(scaled.children[0].center().X, 10, 5)
        self.assertAlmostEqual(scaled.children[1].center().X, 20, 5)
        self.assertAlmostEqual(scaled.volume, assembly.volume * 8, 5)
        # scaled about the origin, everything moves away
        scaled = assembly.scale(2, about=(0, 0, 0))
        self.assertAlmostEqual(scaled.children[0].center().X, 20, 5)
        self.assertAlmostEqual(scaled.children[1].center().X, 30, 5)
        self.assertTrue(_shares_geometry(scaled))

    def test_the_original_is_untouched(self):
        assembly = _assembly()
        before = [child.center() for child in assembly.children]
        assembly.scale(3)
        self.assertEqual([child.center() for child in assembly.children], before)
        self.assertTrue(all(child.parent is assembly for child in assembly.children))


class TestDeepCopiesAndPickles(unittest.TestCase):
    def copiers(self):
        return (
            ("deepcopy", copy.deepcopy),
            ("pickle", lambda shape: pickle.loads(pickle.dumps(shape))),
        )

    def test_a_copied_member_stands_outside_its_assembly(self):
        assembly = _assembly()
        child = assembly.children[0]
        for name, copier in self.copiers():
            with self.subTest(copy=name):
                copied = copier(child)
                self.assertIsNone(copied.parent)
                self.assertEqual(copied.label, "small")
                self.assertAlmostEqual(copied.volume, 1, 5)
        self.assertIs(child.parent, assembly)
        self.assertEqual(len(assembly.children), 2)

    def test_a_copied_assembly_shares_geometry_with_its_children(self):
        assembly = _assembly().moved(Pos(0, 0, 7))
        for name, copier in self.copiers():
            with self.subTest(copy=name):
                copied = copier(assembly)
                self.assertEqual([c.label for c in copied.children], ["small", "large"])
                self.assertTrue(all(c.parent is copied for c in copied.children))
                self.assertTrue(_shares_geometry(copied))
                self.assertAlmostEqual(copied.volume, assembly.volume, 5)
                self.assertAlmostEqual(copied.center().Z, assembly.center().Z, 5)
                for child, source in zip(copied.children, assembly.children):
                    self.assertFalse(child.wrapped.IsPartner(source.wrapped))

    def test_connections_stay_within_the_copy(self):
        block = Solid.make_box(2, 2, 2)
        cap = Solid.make_box(1, 1, 1).moved(Location((0, 0, 2)))
        RigidJoint("top", block, Location((0, 0, 2)))
        RigidJoint("seat", cap)
        block.joints["top"].connect_to(cap.joints["seat"])
        original = Compound(children=[block, cap])
        for name, copier in self.copiers():
            with self.subTest(copy=name):
                copied_block, copied_cap = copier(original).children
                self.assertIs(
                    copied_block.joints["top"].connected_to, copied_cap.joints["seat"]
                )
                self.assertIs(copied_cap.joints["seat"].parent, copied_cap)

    def test_a_copy_keeps_what_the_children_shared(self):
        """The halves of a split share the vertices, edges and face on the cut
        plane. Their deep copies share the copies of those, so the copy counts
        the same vertices as the original, and none of the original's. (A
        pickle writes each node's shape on its own and loses the sharing.)"""
        halves = Solid.make_box(10, 10, 10).split(
            Plane((0, 5, 0), z_dir=(0, 1, 0)), keep=Keep.ALL
        )
        original = Compound(children=[Compound(h.wrapped) for h in halves])
        self.assertEqual(len(original.vertices()), 12)
        copied = copy.deepcopy(original)
        self.assertEqual([len(c.vertices()) for c in copied.children], [8, 8])
        self.assertEqual(len(copied.vertices()), 12)
        self.assertEqual(len(set(original.vertices() + copied.vertices())), 24)
        self.assertFalse(
            any(
                a.wrapped.IsPartner(b.wrapped)
                for a in original.vertices()
                for b in copied.vertices()
            )
        )


class TestCopiesAroundNewGeometry(unittest.TestCase):
    """The copies that an operation on a face or edge returns"""

    def test_face_copies_keep_attributes(self):
        face = (Box(2, 2, 2) - Cylinder(0.5, 3)).faces().sort_by(Axis.Z)[-1]
        face.label = "top"
        face.color = Color("blue")
        for name, result in (
            ("negated", -face),
            ("without holes", face.without_holes()),
            ("offset by nothing", face.offset(0)),
        ):
            with self.subTest(operation=name):
                self.assertEqual(result.label, "top")
                self.assertEqual(tuple(result.color), tuple(face.color))
                self.assertIsNone(result.parent)
        self.assertEqual(len(face.without_holes().inner_wires()), 0)
        self.assertEqual(len(face.inner_wires()), 1)
        self.assertAlmostEqual((-face).normal_at().Z, -face.normal_at().Z, 5)

    def test_edge_copies_keep_attributes(self):
        edge = Edge.make_line((0, 0, 0), (1, 0, 0))
        edge.label = "line"
        for reconstruct in (False, True):
            with self.subTest(reconstruct=reconstruct):
                reversed_edge = edge.reversed(reconstruct)
                self.assertEqual(reversed_edge.label, "line")
                self.assertEqual(reversed_edge.position_at(0), Vector(1, 0, 0))
        self.assertEqual(edge.position_at(0), Vector(0, 0, 0))

    def test_fix_keeps_attributes_and_children(self):
        # a valid shape is returned as is; an invalid one is copied and fixed
        box = Box(1, 1, 1)
        self.assertIs(box.fix(), box)
        twisted = Face.make_rect(1, 1)
        twisted.label = "patch"
        self.assertEqual(twisted.fix().label, "patch")


if __name__ == "__main__":
    unittest.main()
