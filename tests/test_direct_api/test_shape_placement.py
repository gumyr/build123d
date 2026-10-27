"""
build123d imports

name: test_shape_placement.py
by:   Gumyr
date: October 25, 2026

desc:
    Placement invariants that every kind of shape must satisfy under every
    way of copying or relocating it.

    A shape is a kernel geometry record plus a Location. Copying, pickling,
    ``located``, ``moved`` and the ``*`` placement operator all go through the
    same few methods on Shape, so a quirk in one of them, such as the kernel
    copy folding a Vertex's location into its point, shows up in several
    operations at once. These tests hold the invariants across the matrix of
    shape kinds and operations rather than checking one example of each.

license:

    Copyright 2026 Gumyr

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

import copy
import pickle
import unittest
from collections.abc import Callable

from build123d.geometry import Axis, Color, Location, Plane, Pos
from build123d.joints import RigidJoint
from build123d.objects_curve import Line
from build123d.objects_part import Box
from build123d.objects_sketch import Rectangle
from build123d.operations_part import extrude
from build123d.topology import Compound, Edge, Face, Shape, Solid, Vertex, Wire

# Where every shape under test is built, and where it is sent
PLACED = Location((10, 20, 30), (0, 0, 90))
ELSEWHERE = Location((-5, 1, 2), (90, 0, 0))


def _labelled_solid(location: Location) -> Solid:
    solid = Solid.make_box(1, 2, 3).moved(location)
    solid.label = "brick"
    return solid


def _assembly(location: Location) -> Compound:
    assembly = Compound(children=[Box(1, 1, 1), Pos(4, 0, 0) * Box(1, 1, 1)])
    assembly.location = location
    return assembly


# Each kind builds a fresh shape at the given location, so a shape made at
# one location can be compared with the same shape relocated to another
KINDS: dict[str, Callable[[Location], Shape]] = {
    "vertex": lambda loc: Vertex(1, 2, 3).moved(loc),
    "vertex of a moved wire": lambda loc: (
        Wire.make_polygon([(0, 0, 0), (1, 0, 0), (1, 1, 0)], close=False)
        .moved(loc)
        .vertices()[1]
    ),
    "edge": lambda loc: Edge.make_line((0, 0, 0), (1, 0, 0)).moved(loc),
    "edge of a moved face": lambda loc: Face.make_rect(2, 1).moved(loc).edges()[0],
    "wire": lambda loc: Wire.make_polygon([(0, 0, 0), (1, 0, 0), (1, 1, 0)]).moved(loc),
    "face": lambda loc: Face.make_rect(2, 1).moved(loc),
    "face with a hole": lambda loc: (
        Face.make_rect(4, 4).make_holes([Wire.make_circle(1)]).moved(loc)
    ),
    "shell": lambda loc: Solid.make_box(1, 2, 3).shells()[0].moved(loc),
    "solid": lambda loc: Solid.make_box(1, 2, 3).moved(loc),
    "labelled solid": _labelled_solid,
    "compound": lambda loc: Compound(
        [Solid.make_box(1, 1, 1), Solid.make_sphere(0.5).moved(Pos(3, 0, 0))]
    ).moved(loc),
    "assembly": _assembly,
    "part": lambda loc: loc * Box(1, 2, 3),
    "sketch": lambda loc: loc * Rectangle(1, 2),
    "curve": lambda loc: loc * Line((0, 0, 0), (1, 0, 0)),
}

# Operations applied after a copy, which must act on the copy as on the original
FOLLOW_UPS: dict[str, Callable[[Shape], Shape]] = {
    "scale": lambda shape: shape.scale(2),
    "mirror": lambda shape: shape.mirror(Plane.YZ),
    "rotate": lambda shape: shape.rotate(Axis.Z, 30),
    "translate": lambda shape: shape.translate((1, 2, 3)),
    "set location": lambda shape: shape.located(ELSEWHERE),
}


def _rounded(values) -> tuple:
    return tuple(round(value, 4) for value in values)


def placement(shape: Shape) -> tuple:
    """Everything about where a shape is: location, extent, vertices, children"""
    bbox = shape.bounding_box()
    return (
        shape.location,
        _rounded(bbox.min),
        _rounded(bbox.max),
        sorted(_rounded(vertex) for vertex in shape.vertices()),
        tuple(
            _rounded(child.global_location.position)
            for child in getattr(shape, "children", [])
        ),
    )


class TestShapePlacement(unittest.TestCase):
    """Copies and relocations of every kind of shape keep it where it belongs"""

    def assertPlacedLike(self, shape: Shape, reference: Shape):
        self.assertEqual(placement(shape), placement(reference))

    def assertSharesGeometry(self, shape: Shape, original: Shape):
        """The copy holds the original's geometry; an assembly's children do"""
        if original.children:
            for child, source in zip(shape.children, original.children):
                self.assertTrue(child.wrapped.IsPartner(source.wrapped))
        else:
            self.assertTrue(shape.wrapped.IsPartner(original.wrapped))

    def assertAttributesCopied(self, shape: Shape, original: Shape):
        self.assertEqual(shape.label, original.label)
        self.assertEqual(type(shape), type(original))

    def test_kinds_are_placed(self):
        """Every kind reports the location it was built at"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                self.assertEqual(make(PLACED).location, PLACED)
                self.assertNotEqual(placement(make(PLACED)), placement(make(ELSEWHERE)))

    def test_shallow_copy(self):
        """copy.copy shares the geometry and keeps the location"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                original = make(PLACED)
                before = placement(original)
                reference = copy.copy(original)
                self.assertPlacedLike(reference, original)
                self.assertAttributesCopied(reference, original)
                self.assertSharesGeometry(reference, original)
                # the shared geometry doesn't tie the copy's location to the original
                reference.move(ELSEWHERE)
                self.assertEqual(placement(original), before)

    def test_deep_copy(self):
        """copy.deepcopy duplicates the geometry and keeps the location"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                original = make(PLACED)
                before = placement(original)
                duplicate = copy.deepcopy(original)
                self.assertPlacedLike(duplicate, original)
                self.assertAttributesCopied(duplicate, original)
                self.assertFalse(duplicate.wrapped.IsPartner(original.wrapped))
                duplicate.location = ELSEWHERE
                self.assertPlacedLike(duplicate, make(ELSEWHERE))
                self.assertEqual(placement(original), before)

    def test_pickle(self):
        """A pickled and restored shape is where the original was"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                original = make(PLACED)
                restored = pickle.loads(pickle.dumps(original))
                self.assertPlacedLike(restored, original)
                self.assertAttributesCopied(restored, original)

    def test_located(self):
        """located replaces the location on a copy that shares the geometry"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                original = make(PLACED)
                before = placement(original)
                relocated = original.located(ELSEWHERE)
                self.assertEqual(relocated.location, ELSEWHERE)
                self.assertPlacedLike(relocated, make(ELSEWHERE))
                self.assertSharesGeometry(relocated, original)
                self.assertEqual(placement(original), before)

    def test_moved(self):
        """moved composes the location on a copy that shares the geometry"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                original = make(PLACED)
                before = placement(original)
                moved = original.moved(ELSEWHERE)
                self.assertEqual(moved.location, ELSEWHERE * PLACED)
                self.assertPlacedLike(moved, make(ELSEWHERE * PLACED))
                self.assertSharesGeometry(moved, original)
                self.assertEqual(placement(original), before)

    def test_relocated_copies_keep_their_provenance(self):
        """Sharing the geometry keeps a relocated copy's place in its topology"""
        cross = (Rectangle(8, 2) + Rectangle(2, 8)).face()
        solid = extrude(cross, 2).solid()
        for name, relocated in (
            ("located", solid.located(ELSEWHERE)),
            ("moved", solid.moved(ELSEWHERE)),
        ):
            with self.subTest(copy=name):
                interior = relocated.edges().filter_by(Edge.is_interior)
                self.assertEqual(len(interior), 4)

    def test_placement_operator(self):
        """Location * shape is moved"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                original = make(PLACED)
                before = placement(original)
                self.assertPlacedLike(ELSEWHERE * original, make(ELSEWHERE * PLACED))
                self.assertEqual(placement(original), before)

    def test_move(self):
        """move composes the location in place"""
        for name, make in KINDS.items():
            with self.subTest(kind=name):
                original = make(PLACED)
                self.assertIs(original.move(ELSEWHERE), original)
                self.assertPlacedLike(original, make(ELSEWHERE * PLACED))

    def test_relocated_copies_stand_outside_the_assembly(self):
        """A copy of an assembly's member is not a member; the assembly is untouched"""
        assembly = _assembly(PLACED)
        child = assembly.children[0]
        for name, relocated in (
            ("located", child.located(ELSEWHERE)),
            ("moved", child.moved(ELSEWHERE)),
            ("operator", ELSEWHERE * child),
            ("copy", copy.copy(child)),
        ):
            with self.subTest(copy=name):
                self.assertIsNone(relocated.parent)
                self.assertEqual(len(assembly.children), 2)
                self.assertIs(child.parent, assembly)
                self.assertEqual(assembly.location, PLACED)

    def test_relocated_assembly_keeps_its_tree(self):
        """A copy of an assembly has its own children, sharing the originals' geometry"""
        original = _assembly(PLACED)
        for name, relocated in (
            ("located", original.located(ELSEWHERE)),
            ("moved", original.moved(ELSEWHERE)),
            ("copy", copy.copy(original)),
        ):
            with self.subTest(copy=name):
                self.assertEqual(len(relocated.children), 2)
                for child, source in zip(relocated.children, original.children):
                    self.assertIs(child.parent, relocated)
                    self.assertIsNot(child, source)
                    self.assertTrue(child.wrapped.IsPartner(source.wrapped))
                    self.assertEqual(child.location, source.location)
                    self.assertIs(source.parent, original)
                # the copy's compound was rebuilt from its children at its location
                self.assertEqual(
                    _rounded(relocated.bounding_box().max),
                    _rounded(_assembly(relocated.location).bounding_box().max),
                )

    def test_relocated_copies_get_their_own_joints(self):
        """A relocated copy's joints belong to it; the original keeps its own"""
        original = Solid.make_box(1, 2, 3).moved(PLACED)
        RigidJoint("top", original, Location((0, 0, 1.5)))
        for name, relocated in (
            ("located", original.located(ELSEWHERE)),
            ("moved", original.moved(ELSEWHERE)),
            ("copy", copy.copy(original)),
        ):
            with self.subTest(copy=name):
                self.assertIs(relocated.joints["top"].parent, relocated)
                self.assertIsNot(relocated.joints["top"], original.joints["top"])
                self.assertIs(original.joints["top"].parent, original)

    def test_copies_keep_the_colour(self):
        """A copied shape keeps its colour (a coloured shape can't be pickled)"""
        original = Solid.make_box(1, 2, 3).moved(PLACED)
        original.color = Color("red")
        for copier_name, copier in (("copy", copy.copy), ("deepcopy", copy.deepcopy)):
            with self.subTest(copy=copier_name):
                self.assertEqual(tuple(copier(original).color), tuple(original.color))

    def test_copies_follow_the_original(self):
        """An operation on a copy gives what it gives on the original"""
        copiers: dict[str, Callable[[Shape], Shape]] = {
            "copy": copy.copy,
            "deepcopy": copy.deepcopy,
            "pickle": lambda shape: pickle.loads(pickle.dumps(shape)),
        }
        for name, make in KINDS.items():
            for copier_name, copier in copiers.items():
                for op_name, operation in FOLLOW_UPS.items():
                    with self.subTest(kind=name, copy=copier_name, operation=op_name):
                        self.assertPlacedLike(
                            operation(copier(make(PLACED))), operation(make(PLACED))
                        )


if __name__ == "__main__":
    unittest.main()
