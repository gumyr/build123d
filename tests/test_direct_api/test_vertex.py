"""
build123d imports

name: test_vertex.py
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

import unittest

from build123d.build_enums import Align, GeomType
from build123d.geometry import Axis, Location, Plane, Pos, Vector
from build123d.objects_sketch import Rectangle
from build123d.topology import Edge, Face, Solid, Vertex, Wire


class TestVertex(unittest.TestCase):
    """Test the extensions to the cadquery Vertex class"""

    def test_basic_vertex(self):
        v = Vertex()
        self.assertEqual(0, v.X)

        v = Vertex(1, 1, 1)
        self.assertEqual(1, v.X)
        self.assertEqual(Vector, type(v.center()))

        self.assertAlmostEqual(Vector(Vertex(Vector(1, 2, 3))), (1, 2, 3), 7)
        self.assertAlmostEqual(Vector(Vertex((4, 5, 6))), (4, 5, 6), 7)
        self.assertAlmostEqual(Vector(Vertex((7,))), (7, 0, 0), 7)
        self.assertAlmostEqual(Vector(Vertex((8, 9))), (8, 9, 0), 7)

    def test_coordinates_include_location(self):
        """Vertex coordinates include the placement applied to the vertex."""
        vertex = Vertex(1, 0, 0).moved(Location((1, 2, 3)))

        self.assertEqual((2.0, 2.0, 3.0), (vertex.X, vertex.Y, vertex.Z))

    def test_vertex_volume(self):
        v = Vertex(1, 1, 1)
        self.assertAlmostEqual(v.volume, 0, 5)

    def test_vertex_mass(self):
        v = Vertex(1, 1, 1)
        self.assertAlmostEqual(v.mass(), 0, 5)

    def test_vertex_add(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertAlmostEqual(Vector(test_vertex + (100, -40, 10)), (100, -40, 10), 7)
        self.assertAlmostEqual(
            Vector(test_vertex + Vector(100, -40, 10)), (100, -40, 10), 7
        )
        self.assertAlmostEqual(
            Vector(test_vertex + Vertex(100, -40, 10)),
            (100, -40, 10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex + [1, 2, 3]

    def test_vertex_sub(self):
        test_vertex = Vertex(0, 0, 0)
        self.assertAlmostEqual(Vector(test_vertex - (100, -40, 10)), (-100, 40, -10), 7)
        self.assertAlmostEqual(
            Vector(test_vertex - Vector(100, -40, 10)), (-100, 40, -10), 7
        )
        self.assertAlmostEqual(
            Vector(test_vertex - Vertex(100, -40, 10)),
            (-100, 40, -10),
            7,
        )
        with self.assertRaises(TypeError):
            test_vertex - [1, 2, 3]

    def test_vertex_str(self):
        self.assertEqual(str(Vertex(0, 0, 0)), "Vertex(0.0, 0.0, 0.0)")

    def test_vertex_to_vector(self):
        self.assertIsInstance(Vector(Vertex(0, 0, 0)), Vector)
        self.assertAlmostEqual(Vector(Vertex(0, 0, 0)), (0.0, 0.0, 0.0), 7)

    def test_vertex_init_error(self):
        with self.assertRaises(TypeError):
            Vertex(Axis.Z)
        with self.assertRaises(ValueError):
            Vertex(x=1)
        with self.assertRaises(TypeError):
            Vertex((Axis.X, Axis.Y, Axis.Z))

    def test_no_intersect(self):
        with self.assertRaises(NotImplementedError):
            Vertex(1, 2, 3) & Vertex(5, 6, 7)


class TestVertexCorners(unittest.TestCase):
    """Classifying a corner of the face a vertex was selected through."""

    @staticmethod
    def kinds(face: Face) -> list[str]:
        """Every corner of a face, sorted by position."""
        ordered = sorted(
            face.vertices(), key=lambda v: (round(v.X, 6), round(v.Y, 6), round(v.Z, 6))
        )
        return [
            "interior" if v.is_interior else "exterior" if v.is_exterior else "smooth"
            for v in ordered
        ]

    @staticmethod
    def ell() -> Face:
        """A square with a bite out of one corner, so one corner is interior."""
        outline = Rectangle(10, 10, align=(Align.MIN, Align.MIN)) - Pos(
            5, 5
        ) * Rectangle(5, 5, align=(Align.MIN, Align.MIN))
        return Face(Plane.XY * outline.wire())

    def test_the_reflex_corner_of_an_ell(self):
        self.assertEqual(self.kinds(self.ell()).count("interior"), 1)
        self.assertEqual(self.kinds(self.ell()).count("exterior"), 5)
        inner = [v for v in self.ell().vertices() if v.is_interior]
        self.assertAlmostEqual(inner[0].X, 5.0, 6)
        self.assertAlmostEqual(inner[0].Y, 5.0, 6)

    def test_a_hole_turns_the_corners_the_other_way(self):
        """An inner wire bounds the same material from the other side, so its
        corners are interior where the outline's are exterior."""
        plate = Face(Plane.XY * Rectangle(20, 20).wire())
        holed = plate.cut(Solid.make_box(4, 4, 4, Plane((-2, -2, -2)))).faces()[0]
        self.assertEqual(self.kinds(holed).count("interior"), 4)
        self.assertEqual(self.kinds(holed).count("exterior"), 4)

    def test_a_corner_on_a_curved_face(self):
        """The boundary is followed in the face's own parameters, so a curved
        face classifies the same way a flat one does."""
        tube = Solid.make_cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        bitten = tube.cut(Solid.make_box(4, 4, 4, Plane((3, -2, 8)))).faces()[0]
        self.assertEqual(self.kinds(bitten).count("interior"), 2)
        for vertex in bitten.vertices():
            if vertex.is_interior:
                self.assertAlmostEqual(vertex.Z, 8.0, 6)

    def test_a_straight_boundary_is_neither(self):
        """Where two edges meet in line there is no corner, so a vertex there
        is neither kind rather than arbitrarily one of them."""
        corners = [(0, 0, 0), (5, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)]
        face = Face(
            Wire(
                [
                    Edge.make_line(corners[i], corners[(i + 1) % len(corners)])
                    for i in range(len(corners))
                ]
            )
        )
        midpoint = min(
            face.vertices(), key=lambda v: (Vector(v) - Vector(5, 0, 0)).length
        )
        self.assertFalse(midpoint.is_interior)
        self.assertFalse(midpoint.is_exterior)
        self.assertEqual(self.kinds(face).count("exterior"), 4)

    def test_the_face_comes_from_the_selection(self):
        """A vertex belongs to every face meeting there, so the route it was
        selected by is what says which one is meant."""
        box = Solid.make_box(10, 10, 10)
        face = box.faces().sort_by(Axis.Z)[-1]
        self.assertTrue(face.vertices()[0].is_exterior)
        self.assertTrue(face.edges()[0].vertices()[0].is_exterior)
        with self.assertRaisesRegex(ValueError, "not selected through a face"):
            box.vertices()[0].is_interior

    def test_a_vertex_that_is_not_a_corner_is_reported(self):
        """A seam vertex has no single corner in the face's parameters."""
        tube = Solid.make_cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        seam = tube.vertices().sort_by(Axis.Z)[-1]
        with self.assertRaisesRegex(ValueError, "expected 2"):
            seam.is_interior


if __name__ == "__main__":
    unittest.main()
