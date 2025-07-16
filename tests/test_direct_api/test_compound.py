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

from build123d.build_common import GridLocations, PolarLocations
from build123d.build_enums import Align, CenterOf
from build123d.geometry import Location, Plane
from build123d.objects_part import Box
from build123d.objects_sketch import Circle
from build123d.topology import Compound, Edge, Face, ShapeList, Solid, Sketch


class TestCompound(unittest.TestCase):
    def test_make_text(self):
        arc = Edge.make_three_point_arc((-50, 0, 0), (0, 20, 0), (50, 0, 0))
        text = Compound.make_text("test", 10, text_path=arc)
        self.assertEqual(len(text.faces()), 4)
        text = Compound.make_text(
            "test", 10, align=(Align.MAX, Align.MAX), text_path=arc
        )
        self.assertEqual(len(text.faces()), 4)

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


if __name__ == "__main__":
    unittest.main()
