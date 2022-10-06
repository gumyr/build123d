"""

build123d common tests

name: build_common_tests.py
by:   Gumyr
date: July 25th 2022

desc: Unit tests for the build123d common module

license:

    Copyright 2022 Gumyr

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
from build123d import *


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class TestCommonOperations(unittest.TestCase):
    """Test custom operators"""

    def test_matmul(self):
        self.assertTupleAlmostEquals(
            (Edge.makeLine((0, 0, 0), (1, 1, 1)) @ 0.5).toTuple(), (0.5, 0.5, 0.5), 5
        )

    def test_mod(self):
        self.assertTupleAlmostEquals(
            (Wire.makeCircle(10, (0, 0, 0), (0, 0, 1)) % 0.5).toTuple(), (0, -1, 0), 5
        )


class TestProperties(unittest.TestCase):
    def test_vector_properties(self):
        v = Vector(1, 2, 3)
        self.assertTupleAlmostEquals((v.X, v.Y, v.Z), (1, 2, 3), 5)


class TestRotation(unittest.TestCase):
    """Test the Rotation derived class of Location"""

    def test_init(self):
        thirty_by_three = Rotation(30, 30, 30)
        box_vertices = Solid.makeBox(1, 1, 1).moved(thirty_by_three).Vertices()
        self.assertTupleAlmostEquals(
            box_vertices[0].toTuple(), (0.5, -0.4330127, 0.75), 5
        )
        self.assertTupleAlmostEquals(box_vertices[1].toTuple(), (0.0, 0.0, 0.0), 7)
        self.assertTupleAlmostEquals(
            box_vertices[2].toTuple(), (0.0669872, 0.191987, 1.399519), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[3].toTuple(), (-0.4330127, 0.625, 0.6495190), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[4].toTuple(), (1.25, 0.2165063, 0.625), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[5].toTuple(), (0.75, 0.649519, -0.125), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[6].toTuple(), (0.816987, 0.841506, 1.274519), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[7].toTuple(), (0.3169872, 1.2745190, 0.52451905), 5
        )


class TestShapeList(unittest.TestCase):
    """Test the ShapeList derived class"""

    def test_filter_by_axis(self):
        """test the filter and sorting of Faces and Edges by axis"""
        with BuildPart() as test:
            Box(1, 1, 1)
            for axis in [Axis.X, Axis.Y, Axis.Z]:
                with self.subTest(axis=axis):
                    faces = test.faces().filter_by_axis(axis)
                    edges = test.edges().filter_by_axis(axis)
                    self.assertTrue(isinstance(faces, list))
                    self.assertTrue(isinstance(faces, ShapeList))
                    self.assertEqual(len(faces), 2)
                    self.assertTrue(isinstance(edges, list))
                    self.assertTrue(isinstance(edges, ShapeList))
                    self.assertEqual(len(edges), 4)
                    if axis == Axis.X:
                        self.assertLessEqual(faces[0].Center().x, faces[1].Center().x)
                        self.assertLessEqual(edges[0].Center().x, edges[-1].Center().x)
                    elif axis == Axis.Y:
                        self.assertLessEqual(faces[0].Center().y, faces[1].Center().y)
                        self.assertLessEqual(edges[0].Center().y, edges[-1].Center().y)
                    elif axis == Axis.Z:
                        self.assertLessEqual(faces[0].Center().z, faces[1].Center().z)
                        self.assertLessEqual(edges[0].Center().z, edges[-1].Center().z)

    def test_filter_by_position(self):
        """test the filter and sorting of Faces and Edges by position"""
        with BuildPart() as test:
            Box(2, 2, 2)
            for axis in [Axis.X, Axis.Y, Axis.Z]:
                for inclusive in [
                    (True, True),
                    (True, False),
                    (False, True),
                    (False, False),
                ]:
                    with self.subTest(axis=axis, inclusive=inclusive):

                        faces = test.faces().filter_by_position(axis, -1, 1, inclusive)
                        edges = test.edges().filter_by_position(axis, -1, 1, inclusive)
                        self.assertTrue(isinstance(faces, list))
                        self.assertTrue(isinstance(faces, ShapeList))
                        self.assertEqual(len(faces), sum(inclusive) + 4)
                        self.assertTrue(isinstance(edges, list))
                        self.assertTrue(isinstance(edges, ShapeList))
                        self.assertEqual(len(edges), 4 * sum(inclusive) + 4)
                        if axis == Axis.X:
                            self.assertLessEqual(
                                faces[0].Center().x, faces[-1].Center().x
                            )
                            self.assertLessEqual(
                                edges[0].Center().x, edges[-1].Center().x
                            )
                        elif axis == Axis.Y:
                            self.assertLessEqual(
                                faces[0].Center().y, faces[-1].Center().y
                            )
                            self.assertLessEqual(
                                edges[0].Center().y, edges[-1].Center().y
                            )
                        elif axis == Axis.Z:
                            self.assertLessEqual(
                                faces[0].Center().z, faces[-1].Center().z
                            )
                            self.assertLessEqual(
                                edges[0].Center().z, edges[-1].Center().z
                            )

    def test_filter_by_type(self):
        """test the filter and sorting by type"""
        with BuildPart() as test:
            Box(2, 2, 2)
            objects = test.faces()
            objects.extend(test.edges())
        self.assertEqual(len(objects.filter_by_type(GeomType.PLANE)), 6)
        self.assertEqual(len(objects.filter_by_type(GeomType.LINE)), 12)

    def test_sort_by_type(self):
        """test sorting by different attributes"""
        with self.subTest(sort_by=SortBy.AREA):
            with BuildPart() as test:
                Wedge(1, 1, 1, 0, 0, 0.5, 0.5)
                faces = test.faces().sort_by(SortBy.AREA)
            self.assertEqual(faces[0].Area(), 0.25)
            self.assertEqual(faces[-1].Area(), 1)

        with self.subTest(sort_by=SortBy.LENGTH):
            with BuildPart() as test:
                Wedge(1, 1, 1, 0, 0, 0.5, 0.5)
                edges = test.edges().sort_by(SortBy.LENGTH)
            self.assertEqual(edges[0].Length(), 0.5)
            self.assertAlmostEqual(edges[-1].Length(), 1.2247448713915892, 7)

        with self.subTest(sort_by=SortBy.DISTANCE):
            with BuildPart() as test:
                Box(1, 1, 1, centered=(False, True, True))
                faces = test.faces().sort_by(SortBy.DISTANCE)
            self.assertAlmostEqual(faces[0].Center().Length, 0, 7)
            self.assertAlmostEqual(faces[-1].Center().Length, 1, 7)

        with self.subTest(sort_by=SortBy.VOLUME):
            with BuildPart() as test:
                Box(1, 1, 1)
                with Locations((0, 0, 10)):
                    Box(2, 2, 2)
                solids = test.solids().sort_by(SortBy.VOLUME)
            self.assertAlmostEqual(solids[0].Volume(), 1, 7)
            self.assertAlmostEqual(solids[-1].Volume(), 8, 7)

        with self.subTest(sort_by=SortBy.RADIUS):
            with BuildPart() as test:
                Cone(1, 0.5, 2)
                edges = (
                    test.edges().filter_by_type(GeomType.CIRCLE).sort_by(SortBy.RADIUS)
                )
            self.assertEqual(edges[0].radius(), 0.5)
            self.assertEqual(edges[-1].radius(), 1)

        with self.subTest(sort_by="X"):
            with BuildPart() as test:
                Box(1, 1, 1)
                edges = test.edges() > Axis.X
            self.assertEqual(edges[0].Center().x, -0.5)
            self.assertEqual(edges[-1].Center().x, 0.5)

        with self.subTest(sort_by="Y"):
            with BuildPart() as test:
                Box(1, 1, 1)
                edges = test.edges() > Axis.Y
            self.assertEqual(edges[0].Center().y, -0.5)
            self.assertEqual(edges[-1].Center().y, 0.5)

        with self.subTest(sort_by="Z"):
            with BuildPart() as test:
                Box(1, 1, 1)
                edges = test.edges() > Axis.Z
            self.assertEqual(edges[0].Center().z, -0.5)
            self.assertEqual(edges[-1].Center().z, 0.5)

    def test_vertices(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.vertices()), 8)
        self.assertTrue(isinstance(test.part.vertices(), ShapeList))

    def test_edges(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.edges()), 12)
        self.assertTrue(isinstance(test.part.edges(), ShapeList))

    def test_wires(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.wires()), 6)
        self.assertTrue(isinstance(test.part.wires(), ShapeList))

    def test_faces(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.faces()), 6)
        self.assertTrue(isinstance(test.part.faces(), ShapeList))

    def test_solids(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.solids()), 1)
        self.assertTrue(isinstance(test.part.solids(), ShapeList))

    def test_compounds(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.compounds()), 0)
        self.assertTrue(isinstance(test.part.compounds(), ShapeList))


class TestBuilder(unittest.TestCase):
    """Test the Builder base class"""

    def test_exit(self):
        """test transferring objects to parent"""
        with BuildPart() as outer:
            with BuildSketch() as inner:
                Circle(1)
            self.assertEqual(len(outer.pending_faces), 1)
            with BuildSketch() as inner:
                with BuildLine():
                    CenterArc((0, 0), 1, 0, 360)
                BuildFace()
            self.assertEqual(len(outer.pending_faces), 2)


class TestWorkplanes(unittest.TestCase):
    def test_named(self):
        with Workplanes("XY") as test:
            self.assertTupleAlmostEquals(
                test.workplanes[0].origin.toTuple(), (0, 0, 0), 5
            )
            self.assertTupleAlmostEquals(
                test.workplanes[0].zDir.toTuple(), (0, 0, 1), 5
            )

    def test_locations(self):
        with Workplanes("XY"):
            with Locations((0, 0, 1), (0, 0, 2)) as l:
                with Workplanes(*l.locations) as w:
                    origins = [p.origin.toTuple() for p in w.workplanes]
            self.assertTupleAlmostEquals(origins[0], (0, 0, 1), 5)
            self.assertTupleAlmostEquals(origins[1], (0, 0, 2), 5)
            self.assertEqual(len(origins), 2)

    def test_bad_plane(self):
        with self.assertRaises(ValueError):
            with Workplanes(4):
                pass


class TestValidateInputs(unittest.TestCase):
    def test_no_builder(self):
        with self.assertRaises(RuntimeError):
            Circle(1)

    def test_wrong_builder(self):
        with self.assertRaises(RuntimeError):
            with BuildPart():
                Circle(1)

    def test_bad_builder_input(self):
        with self.assertRaises(RuntimeError):
            with BuildPart() as p:
                Box(1, 1, 1)
            with BuildSketch():
                Add(p)

    def test_no_sequence(self):
        with self.assertRaises(RuntimeError):
            with BuildPart() as p:
                Box(1, 1, 1)
                Fillet([None, None], radius=1)

    def test_wrong_type(self):
        with self.assertRaises(RuntimeError):
            with BuildPart() as p:
                Box(1, 1, 1)
                Fillet(4, radius=1)


class TestBuilderExit(unittest.TestCase):
    def test_multiple(self):
        with BuildPart() as test:
            with BuildLine() as l:
                Line((0, 0), (1, 0))
                Line((0, 0), (0, 1))
        self.assertEqual(len(test.pending_edges), 2)


class TestLocations(unittest.TestCase):
    def test_no_centering(self):
        with BuildSketch():
            with GridLocations(4, 4, 2, 2, centered=(False, False)) as l:
                pts = [loc.toTuple()[0] for loc in l.locations]
        self.assertTupleAlmostEquals(pts[0], (0, 0, 0), 5)
        self.assertTupleAlmostEquals(pts[1], (0, 4, 0), 5)
        self.assertTupleAlmostEquals(pts[2], (4, 0, 0), 5)
        self.assertTupleAlmostEquals(pts[3], (4, 4, 0), 5)

    def test_centering(self):
        with BuildSketch():
            with GridLocations(4, 4, 2, 2, centered=(True, True)) as l:
                pts = [loc.toTuple()[0] for loc in l.locations]
        self.assertTupleAlmostEquals(pts[0], (-2, -2, 0), 5)
        self.assertTupleAlmostEquals(pts[1], (-2, 2, 0), 5)
        self.assertTupleAlmostEquals(pts[2], (2, -2, 0), 5)
        self.assertTupleAlmostEquals(pts[3], (2, 2, 0), 5)


if __name__ == "__main__":
    unittest.main()
