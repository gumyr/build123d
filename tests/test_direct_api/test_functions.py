"""
build123d imports

name: test_functions.py
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

import math
import unittest

from build123d.geometry import Plane, Vector
from build123d.objects_part import Box
from build123d.topology import (
    Compound,
    Face,
    Solid,
    edges_to_wires,
    polar,
    new_edges,
    delta,
    unwrap_topods_compound,
)


class TestFunctions(unittest.TestCase):
    def test_edges_to_wires(self):
        square_edges = Face.make_rect(1, 1).edges()
        rectangle_edges = Face.make_rect(2, 1, Plane((5, 0))).edges()
        wires = edges_to_wires(square_edges + rectangle_edges)
        self.assertEqual(len(wires), 2)
        self.assertAlmostEqual(wires[0].length, 4, 5)
        self.assertAlmostEqual(wires[1].length, 6, 5)

    def test_polar(self):
        pnt = polar(1, 30)
        self.assertAlmostEqual(pnt[0], math.sqrt(3) / 2, 5)
        self.assertAlmostEqual(pnt[1], 0.5, 5)

    def test_new_edges(self):
        c = Solid.make_cylinder(1, 5)
        s = Solid.make_sphere(2)
        s_minus_c = s - c
        seams = new_edges(c, s, combined=s_minus_c)
        self.assertEqual(len(seams), 1)
        self.assertAlmostEqual(seams[0].radius, 1, 5)

    def test_delta(self):
        cyl = Solid.make_cylinder(1, 5)
        sph = Solid.make_sphere(2)
        con = Solid.make_cone(2, 1, 2)
        plug = delta([cyl, sph, con], [sph, con])
        self.assertEqual(len(plug), 1)
        self.assertEqual(plug[0], cyl)

    def test_parse_intersect_args(self):

        with self.assertRaises(TypeError):
            Vector(1, 1, 1) & ("x", "y", "z")

    def test_unwrap_topods_compound(self):
        # Complex Compound
        b1 = Box(1, 1, 1).solid()
        b2 = Box(2, 2, 2).solid()
        c1 = Compound([b1, b2])
        c2 = Compound([b1, c1])
        c3 = Compound([c2])
        c4 = Compound([c3])
        self.assertEqual(c4.wrapped.NbChildren(), 1)
        c5 = Compound(unwrap_topods_compound(c4.wrapped, False))
        self.assertEqual(c5.wrapped.NbChildren(), 2)

        # unwrap fully
        c0 = Compound([b1])
        c1 = Compound([c0])
        result = Compound.cast(unwrap_topods_compound(c1.wrapped, True))
        self.assertTrue(isinstance(result, Solid))

        # unwrap not fully
        result = Compound.cast(unwrap_topods_compound(c1.wrapped, False))
        self.assertTrue(isinstance(result, Compound))


if __name__ == "__main__":
    unittest.main()
