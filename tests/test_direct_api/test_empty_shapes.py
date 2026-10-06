"""
Empty shapes

The zero of each shape class: what it is, and the laws it follows.

name: test_empty_shapes.py
by:   Gumyr
date: October 5, 2026

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

from OCP.TopoDS import TopoDS_Compound

from build123d.build_enums import Mode
from build123d.build_line import BuildLine
from build123d.build_part import BuildPart
from build123d.build_sketch import BuildSketch
from build123d.geometry import Axis, Location, Plane, Pos, Vector
from build123d.objects_part import Box
from build123d.objects_sketch import Rectangle
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    Part,
    Shape,
    Shell,
    Sketch,
    Solid,
    Vertex,
    Wire,
)

CLASSES = [Vertex, Edge, Wire, Face, Shell, Solid, Compound, Part, Sketch, Curve]
DIMENSIONS = {
    Vertex: 0,
    Edge: 1,
    Wire: 1,
    Curve: 1,
    Face: 2,
    Shell: 2,
    Sketch: 2,
    Solid: 3,
    Part: 3,
    Compound: None,
}


class TestEmptyShapeDefinition(unittest.TestCase):
    """The no-argument constructor of every class is its zero"""

    def test_what_a_zero_is(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                zero = cls()
                self.assertIsInstance(zero, cls)
                self.assertTrue(zero.is_empty)
                self.assertFalse(zero)
                self.assertIsInstance(zero.wrapped, TopoDS_Compound)
                self.assertEqual(zero._dim, DIMENSIONS[cls])

    def test_shape_type_is_the_class(self):
        self.assertEqual(Solid().shape_type, "Solid")
        self.assertEqual(Face().shape_type, "Face")
        self.assertEqual(Vertex().shape_type, "Vertex")
        self.assertEqual(Part().shape_type, "Compound")

    def test_vertex_zero_is_not_the_origin(self):
        self.assertTrue(Vertex().is_empty)
        self.assertFalse(Vertex(0, 0, 0).is_empty)
        self.assertEqual(Vertex(0, 0, 0).X, 0)

    def test_a_kernel_empty_is_the_zero_of_any_class(self):
        empty = (Solid.make_box(1, 1, 1) - Solid.make_box(1, 1, 1)).wrapped
        self.assertTrue(Face(empty).is_empty)
        self.assertTrue(Solid.cast(empty).is_empty)
        self.assertIsInstance(Solid.cast(empty), Solid)
        self.assertIsInstance(Shape.cast(empty), Compound)

    def test_setting_wrapped_to_none_empties(self):
        box = Solid.make_box(1, 1, 1)
        box.wrapped = None
        self.assertTrue(box.is_empty)

    def test_is_null_is_deprecated(self):
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(Solid().is_null)


class TestEmptyShapeEquality(unittest.TestCase):
    def test_zeros_of_one_class_are_equal(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                self.assertEqual(cls(), cls())
                self.assertEqual(hash(cls()), hash(cls()))

    def test_zeros_of_different_classes_are_not(self):
        self.assertNotEqual(Solid(), Face())
        self.assertNotEqual(Part(), Compound())

    def test_a_zero_is_not_a_shape(self):
        box = Solid.make_box(1, 1, 1)
        self.assertNotEqual(Solid(), box)
        self.assertNotEqual(box, Solid())


class TestEmptyShapeCopying(unittest.TestCase):
    def test_copies_are_the_zero(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                zero = cls()
                self.assertEqual(copy.copy(zero), zero)
                self.assertEqual(copy.deepcopy(zero), zero)
                self.assertEqual(pickle.loads(pickle.dumps(zero)), zero)
                self.assertIsInstance(copy.copy(zero), cls)


class TestEmptyShapePlacement(unittest.TestCase):
    """Nothing is nothing wherever it is put"""

    def test_moving_keeps_the_zero(self):
        loc = Location((1, 2, 3), (10, 20, 30))
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                zero = cls()
                for placed in (
                    zero.moved(loc),
                    zero.located(loc),
                    loc * zero,
                    Plane.XZ * zero,
                    zero.rotate(Axis.Z, 30),
                    zero.translate((1, 2, 3)),
                    zero.mirror(Plane.XY),
                    zero.scale(2),
                ):
                    self.assertTrue(placed.is_empty)
                    self.assertIsInstance(placed, cls)
                self.assertIs(zero.move(loc), zero)
                self.assertIs(zero.locate(loc), zero)

    def test_a_zero_has_no_place(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                with self.assertRaisesRegex(ValueError, "no location"):
                    cls().location
                with self.assertRaisesRegex(ValueError, "no position"):
                    cls().position
                with self.assertRaisesRegex(ValueError, "no orientation"):
                    cls().orientation
                with self.assertRaisesRegex(ValueError, "no center"):
                    cls().center()


class TestEmptyShapeQueries(unittest.TestCase):
    def test_selectors_find_nothing(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                zero = cls()
                for found in (
                    zero.vertices(),
                    zero.edges(),
                    zero.wires(),
                    zero.faces(),
                    zero.shells(),
                    zero.solids(),
                    zero.get_top_level_shapes(),
                ):
                    self.assertEqual(len(found), 0)

    def test_amounts_are_zero(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                zero = cls()
                self.assertEqual(zero.volume, 0)
                self.assertEqual(zero.area, 0)
                self.assertEqual(zero.static_moments, (0.0, 0.0, 0.0))
                self.assertEqual(zero.matrix_of_inertia, [[0.0] * 3] * 3)

    def test_directions_raise(self):
        with self.assertRaisesRegex(ValueError, "no principal axes"):
            Solid().principal_properties
        with self.assertRaisesRegex(ValueError, "no radius of gyration"):
            Solid().radius_of_gyration(Axis.Z)

    def test_bounding_box_is_empty(self):
        box = Solid.make_box(1, 1, 1).bounding_box()
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                empty = cls().bounding_box()
                self.assertTrue(empty.is_empty)
                self.assertEqual(tuple(empty.size), (0, 0, 0))
                # the bounding box of nothing adds nothing
                self.assertEqual(tuple(box.add(empty).size), (1, 1, 1))
                self.assertEqual(tuple(empty.add(box).size), (1, 1, 1))
        self.assertFalse(box.is_empty)

    def test_validity(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(cls().is_valid)
                self.assertTrue(cls().clean().is_empty)
                self.assertTrue(cls().fix().is_empty)


class TestEmptyShapeAlgebra(unittest.TestCase):
    """The zero is the identity for + and absorbs - and &"""

    def others(self):
        return [
            (Vertex, Vertex(1, 2, 3)),
            (Edge, Edge.make_line((0, 0, 0), (1, 0, 0))),
            (Wire, Wire.make_rect(1, 1)),
            (Face, Face.make_rect(1, 1)),
            (Solid, Solid.make_box(1, 1, 1)),
            (Part, Box(1, 1, 1)),
            (Sketch, Rectangle(1, 1)),
            (Curve, Curve() + Edge.make_line((0, 0, 0), (1, 0, 0))),
        ]

    @staticmethod
    def size(shape):
        return (shape.volume, shape.area, sum(e.length for e in shape.edges()))

    def test_identity_for_addition(self):
        for cls, other in self.others():
            if cls is Vertex:
                continue  # Vertex + is vector arithmetic
            with self.subTest(cls=cls.__name__):
                # adding nothing gives the shape itself back
                self.assertIs(other + cls(), other)
                self.assertIs(other - cls(), other)
                # nothing plus the shape is the shape's geometry, in a shape
                # of the same dimension
                total = cls() + other
                self.assertEqual(total._dim, cls()._dim)
                self.assertEqual(self.size(total), self.size(other))
                self.assertTrue((cls() + cls()).is_empty)

    def test_absorption(self):
        for cls, other in self.others():
            if cls is Vertex:
                continue  # Vertex - and & are not boolean operations
            with self.subTest(cls=cls.__name__):
                for result in (cls() - other, cls() & other, other & cls()):
                    self.assertTrue(result.is_empty)
                    self.assertIsInstance(result, cls)

    def test_an_untyped_empty_compound_is_the_identity_for_anything(self):
        box = Box(1, 1, 1)
        self.assertEqual(self.size(Compound() + box), self.size(box))
        self.assertEqual(
            self.size(Compound() + Rectangle(1, 1)), self.size(Rectangle(1, 1))
        )
        self.assertTrue((Compound() - box).is_empty)
        self.assertTrue((Compound() & box).is_empty)

    def test_a_boolean_that_leaves_nothing_returns_a_typed_zero(self):
        box = Box(1, 1, 1)
        apart = Pos(5, 0, 0) * Box(1, 1, 1)
        for result, cls in (
            (box - box, Part),
            (box & apart, Part),
            (Solid.make_box(1, 1, 1) - Solid.make_box(1, 1, 1), Part),
            (Rectangle(1, 1) - Rectangle(1, 1), Sketch),
            (Face.make_rect(1, 1) & Pos(5, 0, 0) * Face.make_rect(1, 1), Face),
        ):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(result.is_empty)
                self.assertIsInstance(result, cls)
                self.assertEqual(result._dim, cls()._dim)
        # and the zero carries on through the next operation
        self.assertTrue(((box - box) - apart).is_empty)
        self.assertTrue(((box - box) & apart).is_empty)
        self.assertAlmostEqual(((box - box) + apart).volume, 1, 5)

    def test_intersect_finds_nothing_as_an_empty_list(self):
        box = Solid.make_box(1, 1, 1)
        apart = Pos(5, 0, 0) * Solid.make_box(1, 1, 1)
        self.assertEqual(box.intersect(apart), [])
        self.assertEqual(box.intersect(Solid()), [])
        self.assertEqual(Solid().intersect(box), [])
        self.assertEqual(box.intersect(), [])
        self.assertEqual(len(box.intersect(box)), 1)

    def test_fuse_cut_and_intersect_methods(self):
        box = Solid.make_box(1, 1, 1)
        self.assertEqual(box.fuse(Solid()), box)
        self.assertEqual(box.cut(Solid()), box)
        self.assertEqual(Solid().fuse(box), box)
        self.assertTrue(Solid().cut(box).is_empty)


class TestEmptyShapeGeometryQueries(unittest.TestCase):
    """What needs real geometry says so; what asks about its kind says None"""

    def test_vertex_has_no_coordinates(self):
        for coordinate in ("X", "Y", "Z"):
            with self.assertRaisesRegex(ValueError, "empty Vertex has no position"):
                getattr(Vertex(), coordinate)
        with self.assertRaisesRegex(ValueError, "empty Vertex has no position"):
            Vertex() + (1, 2, 3)

    def test_face_without_a_surface(self):
        for asked in ("geom_adaptor", "outer_wire", "normal_at"):
            with self.assertRaisesRegex(ValueError, "An empty Face has no"):
                getattr(Face(), asked)()
        with self.assertRaisesRegex(ValueError, "An empty Face has no surface"):
            Face().uv_face
        with self.assertRaisesRegex(ValueError, "An empty Face has no center"):
            Face().center_location
        self.assertEqual(len(Face().inner_wires()), 0)

    def test_probes_of_a_kind_answer_none(self):
        empty = Face()
        for probe in ("geometry", "is_planar", "length", "width", "radius"):
            self.assertIsNone(getattr(empty, probe))
        self.assertIsNone(empty.axis_of_rotation)
        self.assertIsNone(Edge().common_plane())
        self.assertIsNone(Wire().common_plane())

    def test_nothing_meets_nothing(self):
        line = Edge.make_line((0, 0, 0), (1, 0, 0))
        for cls in (Edge, Wire, Face, Shell):
            with self.subTest(cls=cls.__name__):
                self.assertEqual(cls().intersect(line), [])
                self.assertEqual(line.intersect(cls()), [])

    def test_oriented_bounding_box_of_nothing(self):
        box = Solid().oriented_bounding_box()
        self.assertTrue(box.is_empty)
        self.assertEqual(tuple(box.size), (0, 0, 0))
        self.assertEqual(box.plane, Plane.XY)
        self.assertFalse(Solid.make_box(1, 1, 1).oriented_bounding_box().is_empty)


class TestEmptyShapeBuilders(unittest.TestCase):
    """A builder starts from the zero of what it builds"""

    def test_an_empty_builder_gives_the_zero(self):
        with BuildPart() as part_builder:
            self.assertTrue(part_builder.part.is_empty)
            self.assertIsInstance(part_builder.part, Part)
            self.assertEqual(len(part_builder.faces()), 0)
        self.assertTrue(part_builder.part.is_empty)
        with BuildSketch() as sketch_builder:
            pass
        self.assertIsInstance(sketch_builder.sketch, Sketch)
        self.assertTrue(sketch_builder.sketch.is_empty)
        with BuildLine() as line_builder:
            pass
        self.assertIsInstance(line_builder.line, Curve)
        self.assertTrue(line_builder.line.is_empty)

    def test_subtracting_everything_leaves_the_zero(self):
        with BuildPart() as builder:
            Box(1, 1, 1)
            Box(2, 2, 2, mode=Mode.SUBTRACT)
        self.assertTrue(builder.part.is_empty)
        self.assertIsInstance(builder.part, Part)

    def test_a_first_removal_is_still_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "Nothing to subtract from"):
            with BuildPart():
                Box(1, 1, 1, mode=Mode.SUBTRACT)
        with self.assertRaisesRegex(RuntimeError, "Nothing to intersect with"):
            with BuildPart():
                Box(1, 1, 1, mode=Mode.INTERSECT)

    def test_a_nested_builder_that_made_nothing_warns_and_adds_nothing(self):
        with BuildPart() as outer:
            Box(1, 1, 1)
            with self.assertWarnsRegex(UserWarning, "BuildSketch created nothing"):
                with BuildSketch():
                    pass
        self.assertAlmostEqual(outer.part.volume, 1, 5)


class TestEmptyShapeContainers(unittest.TestCase):
    def test_a_compound_of_nothing_is_nothing(self):
        self.assertTrue(Compound([]).is_empty)
        self.assertTrue(Compound([Solid(), Face()]).is_empty)
        self.assertTrue(Compound(children=[]).is_empty)

    def test_zeros_add_nothing_to_a_compound(self):
        box = Solid.make_box(1, 1, 1)
        mixed = Compound([Solid(), box, Face()])
        self.assertFalse(mixed.is_empty)
        self.assertEqual(len(mixed.solids()), 1)
        self.assertAlmostEqual(mixed.volume, 1, 5)


if __name__ == "__main__":
    unittest.main()
