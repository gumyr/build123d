"""

build123d common tests

name: test_build_common.py
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
from build123d import Builder, WorkplaneList, LocationList


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class TestCommonOperations(unittest.TestCase):
    """Test custom operators"""

    def test_matmul(self):
        self.assertTupleAlmostEquals(
            (Edge.make_line((0, 0, 0), (1, 1, 1)) @ 0.5).to_tuple(), (0.5, 0.5, 0.5), 5
        )

    def test_mod(self):
        self.assertTupleAlmostEquals(
            (Wire.make_circle(10) % 0.5).to_tuple(), (0, -1, 0), 5
        )


class TestProperties(unittest.TestCase):
    def test_vector_properties(self):
        v = Vector(1, 2, 3)
        self.assertTupleAlmostEquals((v.X, v.Y, v.Z), (1, 2, 3), 5)


class TestRotation(unittest.TestCase):
    """Test the Rotation derived class of Location"""

    def test_init(self):
        thirty_by_three = Rotation(30, 30, 30)
        box_vertices = Solid.make_box(1, 1, 1).moved(thirty_by_three).vertices()
        self.assertTupleAlmostEquals(
            box_vertices[0].to_tuple(), (0.5, -0.4330127, 0.75), 5
        )
        self.assertTupleAlmostEquals(box_vertices[1].to_tuple(), (0.0, 0.0, 0.0), 7)
        self.assertTupleAlmostEquals(
            box_vertices[2].to_tuple(), (0.0669872, 0.191987, 1.399519), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[3].to_tuple(), (-0.4330127, 0.625, 0.6495190), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[4].to_tuple(), (1.25, 0.2165063, 0.625), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[5].to_tuple(), (0.75, 0.649519, -0.125), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[6].to_tuple(), (0.816987, 0.841506, 1.274519), 5
        )
        self.assertTupleAlmostEquals(
            box_vertices[7].to_tuple(), (0.3169872, 1.2745190, 0.52451905), 5
        )


class TestShapeList(unittest.TestCase):
    """Test the ShapeList derived class"""

    def test_filter_by(self):
        """test the filter and sorting of Faces and Edges by axis, and
        test the filter and sorting by type"""
        # test by axis
        with BuildPart() as test:
            Box(1, 1, 1)
            for axis in [Axis.X, Axis.Y, Axis.Z]:
                with self.subTest(axis=axis):
                    faces = test.faces().filter_by(axis)
                    edges = test.edges().filter_by(axis)
                    self.assertTrue(isinstance(faces, list))
                    self.assertTrue(isinstance(faces, ShapeList))
                    self.assertEqual(len(faces), 2)
                    self.assertTrue(isinstance(edges, list))
                    self.assertTrue(isinstance(edges, ShapeList))
                    self.assertEqual(len(edges), 4)
                    if axis == Axis.X:
                        self.assertLessEqual(faces[0].center().x, faces[1].center().x)
                        self.assertLessEqual(edges[0].center().x, edges[-1].center().x)
                    elif axis == Axis.Y:
                        self.assertLessEqual(faces[0].center().y, faces[1].center().y)
                        self.assertLessEqual(edges[0].center().y, edges[-1].center().y)
                    elif axis == Axis.Z:
                        self.assertLessEqual(faces[0].center().z, faces[1].center().z)
                        self.assertLessEqual(edges[0].center().z, edges[-1].center().z)

        # test filter by type
        with BuildPart() as test:
            Box(2, 2, 2)
            objects = test.faces()
            objects.extend(test.edges())
        self.assertEqual(len(objects.filter_by(GeomType.PLANE)), 6)
        self.assertEqual(len(objects.filter_by(GeomType.LINE)), 12)

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
                                faces[0].center().x, faces[-1].center().x
                            )
                            self.assertLessEqual(
                                edges[0].center().x, edges[-1].center().x
                            )
                        elif axis == Axis.Y:
                            self.assertLessEqual(
                                faces[0].center().y, faces[-1].center().y
                            )
                            self.assertLessEqual(
                                edges[0].center().y, edges[-1].center().y
                            )
                        elif axis == Axis.Z:
                            self.assertLessEqual(
                                faces[0].center().z, faces[-1].center().z
                            )
                            self.assertLessEqual(
                                edges[0].center().z, edges[-1].center().z
                            )

    def test_sort_by_type(self):
        """test sorting by different attributes"""
        with self.subTest(sort_by=SortBy.AREA):
            with BuildPart() as test:
                Wedge(1, 1, 1, 0, 0, 0.5, 0.5)
                faces = test.faces().sort_by(SortBy.AREA)
            self.assertEqual(faces[0].area, 0.25)
            self.assertEqual(faces[-1].area, 1)

        with self.subTest(sort_by=SortBy.LENGTH):
            with BuildPart() as test:
                Wedge(1, 1, 1, 0, 0, 0.5, 0.5)
                edges = test.edges().sort_by(SortBy.LENGTH)
            self.assertEqual(edges[0].length, 0.5)
            self.assertAlmostEqual(edges[-1].length, 1.2247448713915892, 7)

        with self.subTest(sort_by=SortBy.DISTANCE):
            with BuildPart() as test:
                Box(1, 1, 1, align=(Align.MIN, Align.CENTER, Align.CENTER))
                faces = test.faces().sort_by(SortBy.DISTANCE)
            self.assertAlmostEqual(faces[0].center().length, 0, 7)
            self.assertAlmostEqual(faces[-1].center().length, 1, 7)

        with self.subTest(sort_by=SortBy.VOLUME):
            with BuildPart() as test:
                Box(1, 1, 1)
                with Locations((0, 0, 10)):
                    Box(2, 2, 2)
                solids = test.solids().sort_by(SortBy.VOLUME)
            self.assertAlmostEqual(solids[0].volume, 1, 7)
            self.assertAlmostEqual(solids[-1].volume, 8, 7)

        with self.subTest(sort_by=SortBy.RADIUS):
            with BuildPart() as test:
                Cone(1, 0.5, 2)
                edges = test.edges().filter_by(GeomType.CIRCLE).sort_by(SortBy.RADIUS)
            self.assertEqual(edges[0].radius, 0.5)
            self.assertEqual(edges[-1].radius, 1)

        with self.subTest(sort_by="X"):
            with BuildPart() as test:
                Box(1, 1, 1)
                edges = test.edges() > Axis.X
            self.assertEqual(edges[0].center().X, -0.5)
            self.assertEqual(edges[-1].center().X, 0.5)

        with self.subTest(sort_by="Y"):
            with BuildPart() as test:
                Box(1, 1, 1)
                edges = test.edges() > Axis.Y
            self.assertEqual(edges[0].center().Y, -0.5)
            self.assertEqual(edges[-1].center().Y, 0.5)

        with self.subTest(sort_by="Z"):
            with BuildPart() as test:
                Box(1, 1, 1)
                edges = test.edges() > Axis.Z
            self.assertEqual(edges[0].center().Z, -0.5)
            self.assertEqual(edges[-1].center().Z, 0.5)

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
        self.assertEqual(len(test.wires()), 6)
        self.assertTrue(isinstance(test.wires(), ShapeList))

    def test_wires_last(self):
        with BuildPart() as test:
            Box(1, 1, 1)
            Hole(radius=0.1)
        # Note the wire includes top, bottom and joiner edges
        self.assertEqual(len(test.wires(Select.LAST)), 1)

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
                MakeFace()
            self.assertEqual(len(outer.pending_faces), 2)

    def test_no_applies_to(self):
        class _Bad(Builder):
            pass

        with self.assertRaises(RuntimeError):
            _Bad._get_context(Compound.make_compound([Face.make_rect(1, 1)]).wrapped)


class TestWorkplanes(unittest.TestCase):
    def test_named(self):
        with Workplanes(Plane.XY) as test:
            self.assertTupleAlmostEquals(
                test.workplanes[0].origin.to_tuple(), (0, 0, 0), 5
            )
            self.assertTupleAlmostEquals(
                test.workplanes[0].z_dir.to_tuple(), (0, 0, 1), 5
            )

    def test_locations(self):
        with Workplanes(Plane.XY):
            with Locations((0, 0, 1), (0, 0, 2)) as l:
                with Workplanes(*l.locations) as w:
                    origins = [p.origin.to_tuple() for p in w.workplanes]
            self.assertTupleAlmostEquals(origins[0], (0, 0, 1), 5)
            self.assertTupleAlmostEquals(origins[1], (0, 0, 2), 5)
            self.assertEqual(len(origins), 2)

    def test_grid_locations(self):
        with Workplanes(Plane(origin=(1, 2, 3))):
            locs = GridLocations(4, 6, 2, 2).locations
            self.assertTupleAlmostEquals(locs[0].position.to_tuple(), (-1, -1, 3), 5)
            self.assertTupleAlmostEquals(locs[1].position.to_tuple(), (-1, 5, 3), 5)
            self.assertTupleAlmostEquals(locs[2].position.to_tuple(), (3, -1, 3), 5)
            self.assertTupleAlmostEquals(locs[3].position.to_tuple(), (3, 5, 3), 5)

    def test_conversions(self):
        loc = Location((1, 2, 3), (23, 45, 67))
        loc2 = Workplanes(loc).workplanes[0].to_location()
        self.assertTupleAlmostEquals(loc.to_tuple()[0], loc2.to_tuple()[0], 6)
        self.assertTupleAlmostEquals(loc.to_tuple()[1], loc2.to_tuple()[1], 6)

        loc = Location((-10, -2, 30), (-123, 145, 267))
        face = Face.make_rect(1, 1).move(loc)
        loc2 = Workplanes(face).workplanes[0].to_location()
        face2 = Face.make_rect(1, 1).move(loc2)
        self.assertTupleAlmostEquals(
            face.center().to_tuple(), face2.center().to_tuple(), 6
        )
        self.assertTupleAlmostEquals(
            face.normal_at(face.center()).to_tuple(),
            face2.normal_at(face2.center()).to_tuple(),
            6,
        )

    def test_bad_plane(self):
        with self.assertRaises(ValueError):
            with Workplanes(4):
                pass

    def test_locations_after_new_workplane(self):
        with Workplanes(Plane.XY):
            with Locations((0, 1, 2), (3, 4, 5)):
                with Workplanes(Plane.XY.offset(2)):
                    self.assertTupleAlmostEquals(
                        LocationList._get_context().locations[0].position.to_tuple(),
                        (0, 0, 2),
                        5,
                    )


class TestWorkplaneList(unittest.TestCase):
    def test_iter(self):
        for i, plane in enumerate(WorkplaneList([Plane.XY, Plane.YZ])):
            if i == 0:
                self.assertTrue(plane == Plane.XY)
            elif i == 1:
                self.assertTrue(plane == Plane.YZ)

    def test_localize(self):
        with Workplanes(Plane.YZ):
            pnts = Workplanes._get_context().localize((1, 2), (2, 3))
        self.assertTupleAlmostEquals(pnts[0].to_tuple(), (0, 1, 2), 5)
        self.assertTupleAlmostEquals(pnts[1].to_tuple(), (0, 2, 3), 5)


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
    def test_polar_locations(self):
        locs = PolarLocations(1, 5, 45, 90, False).local_locations
        for i, angle in enumerate(range(45, 135, 18)):
            self.assertTupleAlmostEquals(
                locs[i].position.to_tuple(),
                Vector(1, 0).rotate(Axis.Z, angle).to_tuple(),
                5,
            )
            self.assertTupleAlmostEquals(locs[i].orientation.to_tuple(), (0, 0, 0), 5)

    def test_no_centering(self):
        with BuildSketch():
            with GridLocations(4, 4, 2, 2, align=(Align.MIN, Align.MIN)) as l:
                pts = [loc.to_tuple()[0] for loc in l.locations]
        self.assertTupleAlmostEquals(pts[0], (0, 0, 0), 5)
        self.assertTupleAlmostEquals(pts[1], (0, 4, 0), 5)
        self.assertTupleAlmostEquals(pts[2], (4, 0, 0), 5)
        self.assertTupleAlmostEquals(pts[3], (4, 4, 0), 5)
        positions = [
            l.position
            for l in GridLocations(
                1, 1, 2, 2, align=(Align.MIN, Align.MIN)
            ).local_locations
        ]
        for position in positions:
            self.assertTrue(position.X >= 0 and position.Y >= 0)
        positions = [
            l.position
            for l in GridLocations(
                1, 1, 2, 2, align=(Align.MAX, Align.MAX)
            ).local_locations
        ]
        for position in positions:
            self.assertTrue(position.X <= 0 and position.Y <= 0)

    def test_hex_no_centering(self):
        positions = [
            l.position
            for l in HexLocations(1, 2, 2, align=(Align.MIN, Align.MIN)).local_locations
        ]
        for position in positions:
            self.assertTrue(position.X >= 0 and position.Y >= 0)
        positions = [
            l.position
            for l in HexLocations(1, 2, 2, align=(Align.MAX, Align.MAX)).local_locations
        ]
        for position in positions:
            self.assertTrue(position.X <= 0 and position.Y <= 0)

    def test_centering(self):
        with BuildSketch():
            with GridLocations(4, 4, 2, 2, align=(Align.CENTER, Align.CENTER)) as l:
                pts = [loc.to_tuple()[0] for loc in l.locations]
        self.assertTupleAlmostEquals(pts[0], (-2, -2, 0), 5)
        self.assertTupleAlmostEquals(pts[1], (-2, 2, 0), 5)
        self.assertTupleAlmostEquals(pts[2], (2, -2, 0), 5)
        self.assertTupleAlmostEquals(pts[3], (2, 2, 0), 5)

    def test_nesting(self):
        with BuildSketch():
            with Locations((-2, -2), (2, 2)):
                with GridLocations(1, 1, 2, 2) as nested_grid:
                    pts = [loc.to_tuple()[0] for loc in nested_grid.local_locations]
        self.assertTupleAlmostEquals(pts[0], (-2.50, -2.50, 0.00), 5)
        self.assertTupleAlmostEquals(pts[1], (-2.50, -1.50, 0.00), 5)
        self.assertTupleAlmostEquals(pts[2], (-1.50, -2.50, 0.00), 5)
        self.assertTupleAlmostEquals(pts[3], (-1.50, -1.50, 0.00), 5)
        self.assertTupleAlmostEquals(pts[4], (1.50, 1.50, 0.00), 5)
        self.assertTupleAlmostEquals(pts[5], (1.50, 2.50, 0.00), 5)
        self.assertTupleAlmostEquals(pts[6], (2.50, 1.50, 0.00), 5)
        self.assertTupleAlmostEquals(pts[7], (2.50, 2.50, 0.00), 5)

    def test_polar_nesting(self):
        with BuildSketch():
            with PolarLocations(6, 3):
                with GridLocations(1, 1, 2, 2) as polar_grid:
                    pts = [loc.to_tuple()[0] for loc in polar_grid.local_locations]
                    ort = [loc.to_tuple()[1] for loc in polar_grid.local_locations]

        self.assertTupleAlmostEquals(pts[0], (5.50, -0.50, 0.00), 2)
        self.assertTupleAlmostEquals(pts[1], (5.50, 0.50, 0.00), 2)
        self.assertTupleAlmostEquals(pts[2], (6.50, -0.50, 0.00), 2)
        self.assertTupleAlmostEquals(pts[3], (6.50, 0.50, 0.00), 2)
        self.assertTupleAlmostEquals(pts[4], (-2.32, 5.01, 0.00), 2)
        self.assertTupleAlmostEquals(pts[5], (-3.18, 4.51, 0.00), 2)
        self.assertTupleAlmostEquals(pts[6], (-2.82, 5.88, 0.00), 2)
        self.assertTupleAlmostEquals(pts[7], (-3.68, 5.38, 0.00), 2)
        self.assertTupleAlmostEquals(pts[8], (-3.18, -4.51, 0.00), 2)
        self.assertTupleAlmostEquals(pts[9], (-2.32, -5.01, 0.00), 2)
        self.assertTupleAlmostEquals(pts[10], (-3.68, -5.38, 0.00), 2)
        self.assertTupleAlmostEquals(pts[11], (-2.82, -5.88, 0.00), 2)

        self.assertTupleAlmostEquals(ort[0], (-0.00, 0.00, -0.00), 2)
        self.assertTupleAlmostEquals(ort[1], (-0.00, 0.00, -0.00), 2)
        self.assertTupleAlmostEquals(ort[2], (-0.00, 0.00, -0.00), 2)
        self.assertTupleAlmostEquals(ort[3], (-0.00, 0.00, -0.00), 2)
        self.assertTupleAlmostEquals(ort[4], (-0.00, 0.00, 120.00), 2)
        self.assertTupleAlmostEquals(ort[5], (-0.00, 0.00, 120.00), 2)
        self.assertTupleAlmostEquals(ort[6], (-0.00, 0.00, 120.00), 2)
        self.assertTupleAlmostEquals(ort[7], (-0.00, 0.00, 120.00), 2)
        self.assertTupleAlmostEquals(ort[8], (-0.00, 0.00, -120.00), 2)
        self.assertTupleAlmostEquals(ort[9], (-0.00, 0.00, -120.00), 2)
        self.assertTupleAlmostEquals(ort[10], (-0.00, 0.00, -120.00), 2)
        self.assertTupleAlmostEquals(ort[11], (-0.00, 0.00, -120.00), 2)


class TestVectorExtensions(unittest.TestCase):
    def test_vector_localization(self):
        self.assertTupleAlmostEquals(
            (Vector(1, 1, 1) + (1, 2)).to_tuple(),
            (2, 3, 1),
            5,
        )
        self.assertTupleAlmostEquals(
            (Vector(3, 3, 3) - (1, 2)).to_tuple(),
            (2, 1, 3),
            5,
        )
        with self.assertRaises(ValueError):
            Vector(1, 2, 3) + "four"
        with self.assertRaises(ValueError):
            Vector(1, 2, 3) - "four"

        with BuildLine(Plane.YZ):
            self.assertTupleAlmostEquals(
                WorkplaneList.localize((1, 2)).to_tuple(), (0, 1, 2), 5
            )
            self.assertTupleAlmostEquals(
                WorkplaneList.localize(Vector(1, 1, 1) + (1, 2)).to_tuple(),
                (1, 2, 3),
                5,
            )
            self.assertTupleAlmostEquals(
                WorkplaneList.localize(Vector(3, 3, 3) - (1, 2)).to_tuple(),
                (3, 2, 1),
                5,
            )


if __name__ == "__main__":
    unittest.main()
