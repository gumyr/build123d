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

from build123d.build_enums import Align, Convexity, GeomType
from build123d.geometry import Axis, Location, Plane, Pos, Vector
from build123d.objects_part import Box
from build123d.objects_sketch import Rectangle
from build123d.operations_part import extrude
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


class TestVertexConvexity(unittest.TestCase):
    """Classifying a vertex against the shape it was selected from."""

    @staticmethod
    def kinds(shape) -> list[str]:
        """Every vertex of a shape, sorted by position."""
        ordered = sorted(
            shape.vertices(),
            key=lambda v: (round(v.X, 6), round(v.Y, 6), round(v.Z, 6)),
        )
        return [v.convexity.name for v in ordered]

    @staticmethod
    def ell() -> Face:
        """A square with a bite out of one corner, so one corner is concave."""
        outline = Rectangle(10, 10, align=(Align.MIN, Align.MIN)) - Pos(
            5, 5
        ) * Rectangle(5, 5, align=(Align.MIN, Align.MIN))
        return Face(Plane.XY * outline.wire())

    # -- corners of a face --

    def test_the_reflex_corner_of_an_ell(self):
        self.assertEqual(self.kinds(self.ell()).count("CONCAVE"), 1)
        self.assertEqual(self.kinds(self.ell()).count("CONVEX"), 5)
        inner = self.ell().vertices().filter_by(Convexity.CONCAVE)
        self.assertAlmostEqual(inner[0].X, 5.0, 6)
        self.assertAlmostEqual(inner[0].Y, 5.0, 6)

    def test_a_hole_turns_the_corners_the_other_way(self):
        """An inner wire bounds the same material from the other side, so its
        corners are concave where the outline's are convex."""
        plate = Face(Plane.XY * Rectangle(20, 20).wire())
        holed = plate.cut(Solid.make_box(4, 4, 4, Plane((-2, -2, -2)))).faces()[0]
        self.assertEqual(self.kinds(holed).count("CONCAVE"), 4)
        self.assertEqual(self.kinds(holed).count("CONVEX"), 4)

    def test_a_corner_on_a_curved_face(self):
        """The boundary is followed in the face's own parameters, so a curved
        face classifies the same way a flat one does."""
        tube = Solid.make_cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        bitten = tube.cut(Solid.make_box(4, 4, 4, Plane((3, -2, 8)))).faces()[0]
        self.assertEqual(self.kinds(bitten).count("CONCAVE"), 2)
        for vertex in bitten.vertices().filter_by(Convexity.CONCAVE):
            self.assertAlmostEqual(vertex.Z, 8.0, 6)

    def test_a_straight_boundary_is_smooth(self):
        """Where two edges meet in line there is no corner."""
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
        self.assertEqual(midpoint.convexity, Convexity.SMOOTH)
        self.assertEqual(self.kinds(face).count("CONVEX"), 4)

    def test_a_vertex_that_is_not_a_corner_is_reported(self):
        """A seam vertex has no single corner in the face's parameters."""
        tube = Solid.make_cylinder(5, 10).faces().filter_by(GeomType.CYLINDER)[0]
        seam = tube.vertices().sort_by(Axis.Z)[-1]
        with self.assertRaisesRegex(ValueError, "expected 2"):
            seam.convexity

    # -- vertices of a solid --

    def test_the_route_decides_the_question(self):
        """Through a face the vertex is a corner of that face; straight off the
        solid it is classified by the creases meeting there."""
        box = Solid.make_box(10, 10, 10)
        face = box.faces().sort_by(Axis.Z)[-1]
        self.assertEqual(face.vertices()[0].convexity, Convexity.CONVEX)
        self.assertEqual(face.edges()[0].vertices()[0].convexity, Convexity.CONVEX)
        self.assertTrue(all(v.convexity == Convexity.CONVEX for v in box.vertices()))

    def test_a_pocket_has_every_kind_of_vertex(self):
        pocket = Box(20, 20, 10) - Pos(Z=5) * Box(10, 10, 10)
        kinds = self.kinds(pocket)
        self.assertEqual(kinds.count("CONVEX"), 8)  # the outer box
        self.assertEqual(kinds.count("CONCAVE"), 4)  # the pocket floor
        self.assertEqual(kinds.count("SADDLE"), 4)  # the pocket rim
        rim = pocket.vertices().filter_by(Convexity.SADDLE)
        self.assertTrue(all(v.Z == 5 for v in rim))

    def test_a_saddle_where_convex_and_concave_creases_meet(self):
        """The inner corner of a cross is concave in plan and convex in
        elevation, so the vertex is neither."""
        cross = extrude((Rectangle(8, 2) + Rectangle(2, 8)).face(), 2)
        kinds = self.kinds(cross)
        self.assertEqual(kinds.count("CONVEX"), 16)
        self.assertEqual(kinds.count("SADDLE"), 8)
        # but on the top face alone those same corners are concave
        top = cross.faces().sort_by(Axis.Z)[-1]
        self.assertEqual(self.kinds(top).count("CONCAVE"), 4)
        # and a moved copy classifies through its unmoved parent
        moved = Pos(X=10) * cross.solid()
        self.assertEqual(self.kinds(moved).count("SADDLE"), 8)

    def test_a_lone_vertex_has_nothing_to_classify_against(self):
        with self.assertRaisesRegex(ValueError, "not selected from a shape"):
            Vertex(1, 2, 3).convexity


if __name__ == "__main__":
    unittest.main()
