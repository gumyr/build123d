"""
build123d imports

name: test_compound.py
by:   Gumyr
date: January 22, 2025

desc:
    This python module contains tests for the build123d project.

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

import itertools
import unittest
from pathlib import Path

from build123d.build_common import GridLocations, PolarLocations
from build123d.build_enums import Align, CenterOf
from build123d.geometry import Location, Plane
from build123d.objects_part import Box
from build123d.objects_sketch import Circle
from build123d.text import FontManager
from build123d.build_line import BuildLine
from build123d.objects_curve import Polyline
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    Part,
    ShapeList,
    Solid,
    Sketch,
)


class TestCompound(unittest.TestCase):
    def test_make_text(self):
        arc = Edge.make_three_point_arc((-50, 0, 0), (0, 20, 0), (50, 0, 0))
        text = Compound.make_text("test", 10, text_path=arc)
        self.assertEqual(len(text.faces()), 4)
        text = Compound.make_text(
            "test", 10, align=(Align.MAX, Align.MAX), text_path=arc
        )
        self.assertEqual(len(text.faces()), 4)

        singleline = Compound.make_text("test", 10, "singleline", text_path=arc)
        outline = Compound.make_text(
            "test", 10, "singleline", text_path=arc, single_line_width=0.2
        )
        self.assertEqual(len(singleline.faces()), 0)
        self.assertGreaterEqual(len(singleline.wires()), 4)
        self.assertEqual(len(outline.faces()), 4)

    def test_fuse(self):
        box1 = Solid.make_box(1, 1, 1)
        box2 = Solid.make_box(1, 1, 1, Plane((1, 0, 0)))
        combined = Compound([box1]).fuse(box2, glue=True)
        self.assertTrue(combined.is_valid)
        self.assertAlmostEqual(combined.volume, 2, 5)
        fuzzy = Compound([box1]).fuse(box2, tol=1e-6)
        self.assertTrue(fuzzy.is_valid)
        self.assertAlmostEqual(fuzzy.volume, 2, 5)

    def test_remove(self):
        box1 = Solid.make_box(1, 1, 1)
        box2 = Solid.make_box(1, 1, 1, Plane((2, 0, 0)))
        combined = Compound([box1, box2])
        self.assertTrue(len(combined._remove(box2).solids()), 1)

    def test_repr(self):
        simple = Compound([Solid.make_box(1, 1, 1)])
        simple_str = repr(simple).split("0x")[0] + repr(simple).split(", ")[1]
        self.assertEqual(simple_str, "Compound at label()")

        assembly = Compound([Solid.make_box(1, 1, 1)])
        assembly.children = [Solid.make_box(1, 1, 1)]
        assembly.label = "test"
        assembly_str = repr(assembly).split("0x")[0] + repr(assembly).split(", l")[1]
        self.assertEqual(assembly_str, "Compound at abel(test), #children(1)")

    def test_center(self):
        test_compound = Compound(
            [
                Solid.make_box(2, 2, 2).locate(Location((-1, -1, -1))),
                Solid.make_box(1, 1, 1).locate(Location((8.5, -0.5, -0.5))),
            ]
        )
        self.assertAlmostEqual(test_compound.center(CenterOf.MASS), (1, 0, 0), 5)
        self.assertAlmostEqual(
            test_compound.center(CenterOf.BOUNDING_BOX), (4.25, 0, 0), 5
        )
        with self.assertRaises(ValueError):
            test_compound.center(CenterOf.GEOMETRY)

    def test_triad(self):
        triad = Compound.make_triad(10)
        bbox = triad.bounding_box()
        self.assertGreater(bbox.min.X, -10 / 8)
        self.assertLess(bbox.min.X, 0)
        self.assertGreater(bbox.min.Y, -10 / 8)
        self.assertLess(bbox.min.Y, 0)
        self.assertGreater(bbox.min.Y, -10 / 8)
        self.assertAlmostEqual(bbox.min.Z, 0, 4)
        self.assertLess(bbox.size.Z, 12.5)
        self.assertEqual(triad.volume, 0)

    def test_volume(self):
        e = Edge.make_line((0, 0), (1, 1))
        self.assertAlmostEqual(e.volume, 0, 5)

        f = Face.make_rect(1, 1)
        self.assertAlmostEqual(f.volume, 0, 5)

        b = Solid.make_box(1, 1, 1)
        self.assertAlmostEqual(b.volume, 1, 5)

        bb = Box(1, 1, 1)
        self.assertAlmostEqual(bb.volume, 1, 5)

        c = Compound(children=[e, f, b, bb, b.translate((0, 5, 0))])
        self.assertAlmostEqual(c.volume, 3, 5)
        # N.B. b and bb overlap but still add to Compound volume

    def test_constructor(self):
        with self.assertRaises(TypeError):
            Compound(foo="bar")

    def test_len(self):
        self.assertEqual(len(Compound()), 0)
        skt = Sketch() + GridLocations(10, 10, 2, 2) * Circle(1)
        self.assertEqual(len(skt), 4)

    def test_iteration(self):
        skt = Sketch() + GridLocations(10, 10, 2, 2) * Circle(1)
        for c1, c2 in itertools.combinations(skt, 2):
            self.assertGreaterEqual((c1.position - c2.position).length, 10)

    def test_unwrap(self):
        skt = Sketch() + GridLocations(10, 10, 2, 2) * Circle(1)
        skt2 = Compound(children=[skt])
        self.assertEqual(len(skt2), 1)
        skt3 = skt2.unwrap(fully=False)
        self.assertEqual(len(skt3), 4)

        comp1 = Compound().unwrap()
        self.assertEqual(len(comp1), 0)
        comp2 = Compound(children=[Face.make_rect(1, 1)])
        comp3 = Compound(children=[comp2])
        self.assertEqual(len(comp3), 1)
        self.assertTrue(isinstance(next(iter(comp3)), Compound))
        comp4 = comp3.unwrap(fully=True)
        self.assertTrue(isinstance(comp4, Face))

    def test_get_top_level_shapes(self):
        base_shapes = Compound(children=PolarLocations(15, 20) * Box(4, 4, 4))
        fls = base_shapes.get_top_level_shapes()
        self.assertTrue(isinstance(fls, ShapeList))
        self.assertEqual(len(fls), 20)
        self.assertTrue(all(isinstance(s, Solid) for s in fls))

        b1 = Box(1, 1, 1).solid()
        self.assertEqual(b1.get_top_level_shapes()[0], b1)


class TestCompoundAlgebra(unittest.TestCase):
    """Compound's operators, which Part/Sketch/Curve inherit."""

    def test_add_none_returns_self(self):
        part = Part(Solid.make_box(1, 1, 1).wrapped)
        self.assertIs(part + None, part)

    def test_adding_1d_content_that_fuses_to_one_edge(self):
        """Compound holds the 1D branch; Curve inherits Mixin1D.__add__ instead."""
        collinear = Compound([Edge.make_line((0, 0), (1, 0))])
        result = collinear + Edge.make_line((1, 0), (2, 0))

        self.assertIsInstance(result, Curve)
        self.assertEqual(len(result.edges()), 1)
        self.assertAlmostEqual(result.edges()[0].length, 2, 5)

    def test_adding_1d_content_that_stays_apart(self):
        separate = Compound([Edge.make_line((0, 0), (1, 0))])
        result = separate + Edge.make_line((5, 5), (6, 5))
        self.assertEqual(len(result.edges()), 2)

    def test_intersection_with_no_overlap_is_empty(self):
        left = Compound([Solid.make_box(1, 1, 1)])
        right = Compound([Solid.make_box(1, 1, 1, Plane((10, 0, 0)))])
        result = left & right

        self.assertIsInstance(result, Compound)
        self.assertFalse(result)


class TestCompoundAccessors(unittest.TestCase):
    def test_compound_and_compounds(self):
        wrapped = Compound([Solid.make_box(1, 1, 1)])
        self.assertEqual(len(wrapped.compounds()), 1)
        self.assertIsInstance(wrapped.compound(), Compound)

    def test_no_compounds_when_not_wrapping_one(self):
        """A Part can wrap a bare Solid rather than a TopoDS_Compound."""
        part = Part(Solid.make_box(1, 1, 1).wrapped)
        self.assertEqual(part.compounds(), ShapeList())
        with self.assertRaisesRegex(ValueError, "found 0"):
            part.compound()


class TestDoChildrenIntersect(unittest.TestCase):
    def test_overlapping_children(self):
        overlapping = Compound(
            label="asm",
            children=[
                Solid.make_box(1, 1, 1),
                Solid.make_box(1, 1, 1, Plane((0.5, 0, 0))),
            ],
        )
        intersects, _pair, volume = overlapping.do_children_intersect()
        self.assertTrue(intersects)
        self.assertGreater(volume, 0)

    def test_children_that_stay_apart(self):
        apart = Compound(
            label="asm",
            children=[
                Solid.make_box(1, 1, 1),
                Solid.make_box(1, 1, 1, Plane((5, 0, 0))),
            ],
        )
        self.assertFalse(apart.do_children_intersect()[0])

    def test_only_one_pair_of_several_overlaps(self):
        """Three children: the first pair is clear, the second is not."""
        assembly = Compound(
            label="asm",
            children=[
                Solid.make_box(1, 1, 1),
                Solid.make_box(1, 1, 1, Plane((5, 0, 0))),
                Solid.make_box(1, 1, 1, Plane((5.5, 0, 0))),
            ],
        )
        intersects, pair, _volume = assembly.do_children_intersect()
        self.assertTrue(intersects)
        self.assertNotIn(assembly, pair)

    def test_including_the_parent(self):
        """The parent's own geometry contains its children, so including it
        always reports an intersection - between parent and child."""
        assembly = Compound(
            label="asm",
            children=[
                Solid.make_box(1, 1, 1),
                Solid.make_box(1, 1, 1, Plane((5, 0, 0))),
            ],
        )
        self.assertFalse(assembly.do_children_intersect()[0])

        intersects, pair, _volume = assembly.do_children_intersect(include_parent=True)
        self.assertTrue(intersects)
        self.assertIn(assembly, pair)


class TestCurveOperators(unittest.TestCase):
    """@ and % were covered; ^ was not."""

    def setUp(self):
        with BuildLine() as builder:
            Polyline((0, 0), (5, 0), (5, 5))
        self.curve = builder.line

    def test_location_operator(self):
        location = self.curve ^ 0.5
        self.assertIsInstance(location, Location)
        self.assertAlmostEqual(location.position, (5, 0, 0), 5)

    def test_matches_position_and_tangent(self):
        self.assertAlmostEqual((self.curve ^ 0.5).position, self.curve @ 0.5, 5)
        self.assertAlmostEqual((self.curve ^ 0.5).z_axis.direction, self.curve % 0.5, 5)


class TestCompoundTreeValidation(unittest.TestCase):
    def test_parent_must_be_a_compound(self):
        with self.assertRaisesRegex(ValueError, "must be of type Compound"):
            Compound()._pre_attach(Solid.make_box(1, 1, 1))

    def test_children_must_be_shapes(self):
        with self.assertRaisesRegex(ValueError, "must be of type Shape"):
            Compound()._pre_attach_children([1, 2])


if __name__ == "__main__":
    unittest.main()
