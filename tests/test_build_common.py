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
from math import pi
from build123d import *
from build123d import WorkplaneList, flatten_sequence


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class TestFlattenSequence(unittest.TestCase):
    """Test the flatten_sequence helper function"""

    def test_single_object(self):
        self.assertListEqual(flatten_sequence("a"), ["a"])

    def test_sequence(self):
        self.assertListEqual(flatten_sequence("a", "b", "c"), ["a", "b", "c"])

    def test_list(self):
        self.assertListEqual(flatten_sequence(["a", "b", "c"]), ["a", "b", "c"])

    def test_list_sequence(self):
        self.assertListEqual(
            flatten_sequence(["a", "b", "c"], "d"), ["a", "b", "c", "d"]
        )

    def test_sequence_tuple(self):
        self.assertListEqual(
            flatten_sequence("a", ("b", "c", "d"), "e"), ["a", "b", "c", "d", "e"]
        )

    def test_points(self):
        self.assertListEqual(
            flatten_sequence("a", (1, 2, 3), "e"), ["a", (1, 2, 3), "e"]
        )

        self.assertListEqual(
            flatten_sequence("a", (1.0, 2.0, 3.0), "e"), ["a", (1.0, 2.0, 3.0), "e"]
        )

    def test_group_slice(self):
        with BuildSketch() as s3:
            Circle(55 / 2 + 3)
            Rectangle(23 + 6, 42, align=(Align.CENTER, Align.MIN))
            Circle(55 / 2, mode=Mode.SUBTRACT)
            Rectangle(23, 42, mode=Mode.SUBTRACT, align=(Align.CENTER, Align.MIN))
            vertex_groups = s3.vertices().group_by(Axis.Y)[0:2]

        self.assertListEqual(
            flatten_sequence(vertex_groups),
            [
                vertex_groups[0][0],
                vertex_groups[0][1],
                vertex_groups[1][0],
                vertex_groups[1][1],
            ],
        )


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
                make_face()
            self.assertEqual(len(outer.pending_faces), 2)

    def test_plane_with_no_x(self):
        with BuildPart() as p:
            Box(1, 1, 1)
            front = p.faces().sort_by(Axis.X)[-1]
            with BuildSketch(front):
                offset(front, amount=-0.1)
            extrude(amount=0.1)
        self.assertAlmostEqual(p.part.volume, 1**3 + 0.1 * (1 - 2 * 0.1) ** 2, 4)

    def test_no_workplane(self):
        with BuildSketch() as s:
            Circle(1)

    def test_vertex(self):
        with BuildLine() as l:
            CenterArc((0, 0), 1, 0, 360)
            v = l.vertex()
        self.assertTrue(isinstance(v, Vertex))

        with BuildLine() as l:
            CenterArc((0, 0), 1, 0, 90)
            with self.assertWarns(UserWarning):
                l.vertex()

    def test_edge(self):
        with BuildLine() as l:
            CenterArc((0, 0), 1, 0, 90)
            e = l.edge()
        self.assertTrue(isinstance(e, Edge))

        with BuildSketch() as s:
            Rectangle(1, 1)
            with self.assertWarns(UserWarning):
                s.edge()

    def test_wire(self):
        with BuildSketch() as s:
            Rectangle(1, 1)
            w = s.wire()
        self.assertTrue(isinstance(w, Wire))

        with BuildPart() as p:
            Box(1, 1, 1)
            with self.assertWarns(UserWarning):
                p.wire()

    def test_face(self):
        with BuildSketch() as s:
            Rectangle(1, 1)
            f = s.face()
        self.assertTrue(isinstance(f, Face))

        with BuildPart() as p:
            Box(1, 1, 1)
            with self.assertWarns(UserWarning):
                p.face()

    def test_solid(self):
        s = Box(1, 1, 1).solid()
        self.assertTrue(isinstance(s, Solid))

        with BuildPart() as p:
            with BuildSketch():
                Text("Two", 10)
            extrude(amount=5)
            with self.assertWarns(UserWarning):
                p.solid()

    def test_workplanes_as_list(self):
        with BuildPart() as p:
            Box(1, 1, 1)
            with BuildSketch(p.faces() >> Axis.Z):
                Rectangle(0.25, 0.25)
            extrude(amount=0.25)
        self.assertAlmostEqual(p.part.volume, 1**3 + 0.25**3, 5)

        with self.assertRaises(ValueError):
            with BuildLine([Plane.XY, Plane.XZ]):
                Line((0, 0), (1, 1))

    def test_invalid_boolean_operations(self):
        with BuildPart() as a:
            Box(1, 1, 1)

        with BuildPart() as b:
            Cylinder(1, 1)

        with self.assertRaises(RuntimeError):
            c = a + b

        with self.assertRaises(RuntimeError):
            c = a - b

        with self.assertRaises(RuntimeError):
            c = a & b

    def test_invalid_methods(self):
        with BuildPart() as a:
            Box(1, 1, 1)

        with self.assertRaises(AttributeError):
            a.export_stl("invalid.stl")


class TestBuilderExit(unittest.TestCase):
    def test_multiple(self):
        with BuildPart() as test:
            with BuildLine() as l:
                Line((0, 0), (1, 0))
                Line((0, 0), (0, 1))
        self.assertEqual(len(test.pending_edges), 2)

    def test_workplane_popping(self):
        # If BuildSketch pushes and pops its workplanes correctly, the order shouldn't matter
        with BuildPart(Plane.XZ) as a:
            with BuildSketch():
                Circle(1)
            Cylinder(1, 5)

        with BuildPart(Plane.XZ) as b:
            Cylinder(1, 5)
            with BuildSketch():
                Circle(1)
        self.assertAlmostEqual(a.part.volume, (a.part & b.part).volume, 4)


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

    def test_xor(self):
        helix_loc = Edge.make_helix(2 * pi, 1, 1) ^ 0
        self.assertTupleAlmostEquals(helix_loc.position.to_tuple(), (1, 0, 0), 5)
        self.assertTupleAlmostEquals(helix_loc.orientation.to_tuple(), (-45, 0, 180), 5)


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

    def test_polar_endpoint(self):
        locs = PolarLocations(
            1, count=3, start_angle=45, angular_range=45, endpoint=False
        )
        for loc, angle in zip(locs, [45, 60, 75]):
            self.assertAlmostEqual(loc.orientation.Z, angle, 5)
        locs = PolarLocations(
            1, count=3, start_angle=45, angular_range=45, endpoint=True
        )
        for loc, angle in zip(locs, [45, 67.5, 90]):
            self.assertAlmostEqual(loc.orientation.Z, angle, 5)

    def test_polar_single_point(self):
        locs = PolarLocations(
            1, count=1, start_angle=45, angular_range=45, endpoint=False
        ).locations
        self.assertEqual(len(locs), 1)
        self.assertAlmostEqual(locs[0].orientation.Z, 45, 5)

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

    def test_hex_major_radius(self):
        hex = RegularPolygon(1, 6)
        with BuildSketch() as s:
            with HexLocations(1, 3, 3, major_radius=True) as hloc:
                add(hex)
        self.assertAlmostEqual(s.sketch.face().area, hex.area * 9, 7)
        self.assertAlmostEqual(hloc.radius, 1, 7)
        self.assertAlmostEqual(hloc.diagonal, 2, 7)
        self.assertAlmostEqual(hloc.apothem, 3**0.5 / 2, 7)
    
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

    def test_from_face(self):
        square = Face.make_rect(1, 1, Plane.XZ)
        with BuildPart():
            loc = Locations(square).locations[0]
        self.assertTupleAlmostEquals(
            loc.position.to_tuple(), Location(Plane.XZ).position.to_tuple(), 5
        )
        self.assertTupleAlmostEquals(
            loc.orientation.to_tuple(), Location(Plane.XZ).orientation.to_tuple(), 5
        )

    def test_from_plane(self):
        with BuildPart():
            loc = Locations(Plane.XY.offset(1)).locations[0]
        self.assertTupleAlmostEquals(loc.position.to_tuple(), (0, 0, 1), 5)

    def test_from_axis(self):
        with BuildPart():
            loc = Locations(Axis((1, 1, 1), (0, 0, 1))).locations[0]
        self.assertTupleAlmostEquals(loc.position.to_tuple(), (1, 1, 1), 5)

    def test_multiplication(self):
        circles = GridLocations(2, 2, 2, 2) * Circle(1)
        self.assertEqual(len(circles), 4)

        with self.assertRaises(ValueError):
            GridLocations(2, 2, 2, 2) * "error"

    def test_grid_attributes(self):
        grid = GridLocations(5, 10, 3, 4)
        self.assertTupleAlmostEquals(grid.size.to_tuple(), (10, 30, 0), 5)
        self.assertTupleAlmostEquals(grid.min.to_tuple(), (-5, -15, 0), 5)
        self.assertTupleAlmostEquals(grid.max.to_tuple(), (5, 15, 0), 5)

    def test_mixed_sequence_list(self):
        locs = Locations((0, 1), [(2, 3), (4, 5)], (6, 7))
        self.assertEqual(len(locs.locations), 4)
        self.assertTupleAlmostEquals(
            locs.locations[0].position.to_tuple(), (0, 1, 0), 5
        )
        self.assertTupleAlmostEquals(
            locs.locations[1].position.to_tuple(), (2, 3, 0), 5
        )
        self.assertTupleAlmostEquals(
            locs.locations[2].position.to_tuple(), (4, 5, 0), 5
        )
        self.assertTupleAlmostEquals(
            locs.locations[3].position.to_tuple(), (6, 7, 0), 5
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
                        self.assertLessEqual(faces[0].center().X, faces[1].center().X)
                        self.assertLessEqual(edges[0].center().X, edges[-1].center().X)
                    elif axis == Axis.Y:
                        self.assertLessEqual(faces[0].center().Y, faces[1].center().Y)
                        self.assertLessEqual(edges[0].center().Y, edges[-1].center().Y)
                    elif axis == Axis.Z:
                        self.assertLessEqual(faces[0].center().Z, faces[1].center().Z)
                        self.assertLessEqual(edges[0].center().Z, edges[-1].center().Z)
            for plane in [Plane.XY, Plane.XZ, Plane.YX, Plane.YZ, Plane.ZX, Plane.ZY]:
                with self.subTest(plane=plane):
                    faces = test.faces().filter_by(plane)
                    edges = test.edges().filter_by(plane)
                    self.assertTrue(isinstance(faces, list))
                    self.assertTrue(isinstance(faces, ShapeList))
                    self.assertEqual(len(faces), 2)
                    self.assertTrue(isinstance(edges, list))
                    self.assertTrue(isinstance(edges, ShapeList))
                    self.assertEqual(len(edges), 8)
                    self.assertAlmostEqual(
                        abs((faces[1].center() - faces[0].center()).dot(plane.z_dir)), 1
                    )
                    axis_index = list(map(int, map(abs, plane.z_dir))).index(1)
                    self.assertTrue(
                        all(abs(list(e.center())[axis_index]) > 0.1 for e in edges)
                    )
                    if plane == Plane.XY:
                        with BuildLine():
                            line = Line((0, 0, 0), (10, 0, 0)).edge()
                            bezier2d = Bezier((0, 0, 0), (5, 3, 0), (10, 0, 0)).edge()
                            bezier3d = Bezier(
                                (0, 0, 0), (3, 3, 0), (7, 1, 3), (10, 0, 0)
                            ).edge()
                        edges = ShapeList([line, bezier2d, bezier3d]) | plane
                        self.assertIn(line, edges)
                        self.assertIn(bezier2d, edges)
                        self.assertNotIn(bezier3d, edges)

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
                                faces[0].center().X, faces[-1].center().X
                            )
                            self.assertLessEqual(
                                edges[0].center().X, edges[-1].center().X
                            )
                        elif axis == Axis.Y:
                            self.assertLessEqual(
                                faces[0].center().Y, faces[-1].center().Y
                            )
                            self.assertLessEqual(
                                edges[0].center().Y, edges[-1].center().Y
                            )
                        elif axis == Axis.Z:
                            self.assertLessEqual(
                                faces[0].center().Z, faces[-1].center().Z
                            )
                            self.assertLessEqual(
                                edges[0].center().Z, edges[-1].center().Z
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
        with self.assertRaises(ValueError):
            with BuildPart() as test:
                Box(1, 1, 1)
                v = test.vertices("ALL")

    def test_edges(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.edges()), 12)
        self.assertTrue(isinstance(test.part.edges(), ShapeList))
        with self.assertRaises(ValueError):
            with BuildPart() as test:
                Box(1, 1, 1)
                v = test.edges("ALL")

    def test_wires(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.wires()), 6)
        self.assertTrue(isinstance(test.wires(), ShapeList))
        with self.assertRaises(ValueError):
            with BuildPart() as test:
                Box(1, 1, 1)
                v = test.wires("ALL")

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
        with self.assertRaises(ValueError):
            with BuildPart() as test:
                Box(1, 1, 1)
                v = test.faces("ALL")

    def test_solids(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.solids()), 1)
        self.assertTrue(isinstance(test.part.solids(), ShapeList))
        with self.assertRaises(ValueError):
            with BuildPart() as test:
                Box(1, 1, 1)
                v = test.solids("ALL")

    def test_compounds(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(len(test.part.compounds()), 1)
        self.assertTrue(isinstance(test.part.compounds(), ShapeList))

    def test_shapes(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertIsNone(test._shapes(Compound))

    def test_operators(self):
        with BuildPart() as test:
            Box(1, 1, 1)
        self.assertEqual(
            (test.faces() | Axis.Z).edges() & (test.faces() | Axis.Y).edges(),
            (test.edges() | Axis.X),
        )


class TestValidateInputs(unittest.TestCase):
    def test_wrong_builder(self):
        with self.assertRaises(RuntimeError) as rte:
            with BuildPart():
                Circle(1)
        self.assertEqual(
            "BuildPart doesn't have a Circle object or operation (Circle applies to ['BuildSketch'])",
            str(rte.exception),
        )

    def test_no_sequence(self):
        with self.assertRaises(ValueError) as rte:
            with BuildPart() as p:
                Box(1, 1, 1)
                fillet([None, None], radius=1)
        self.assertEqual("3D fillet operation takes only Edges", str(rte.exception))

    def test_wrong_type(self):
        with self.assertRaises(RuntimeError) as rte:
            with BuildPart() as p:
                Box(1, 1, 1)
                fillet(4, radius=1)


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

    def test_relative_addition_with_non_zero_origin(self):
        pln = Plane.XZ
        pln.origin = (0, 0, -35)

        with BuildLine(pln):
            n3 = Line((-50, -40), (0, 0))
            n4 = Line(n3 @ 1, n3 @ 1 + (0, 10))
            self.assertTupleAlmostEquals((n4 @ 1).to_tuple(), (0, 0, -25), 5)


class TestWorkplaneList(unittest.TestCase):
    def test_iter(self):
        for i, plane in enumerate(WorkplaneList(Plane.XY, Plane.YZ)):
            if i == 0:
                self.assertTrue(plane == Plane.XY)
            elif i == 1:
                self.assertTrue(plane == Plane.YZ)

    def test_localize(self):
        with BuildLine(Plane.YZ):
            pnts = WorkplaneList.localize((1, 2), (2, 3))
        self.assertTupleAlmostEquals(pnts[0].to_tuple(), (0, 1, 2), 5)
        self.assertTupleAlmostEquals(pnts[1].to_tuple(), (0, 2, 3), 5)

    def test_invalid_workplane(self):
        with self.assertRaises(ValueError):
            WorkplaneList(Vector(1, 1, 1))


class TestWorkplaneStorage(unittest.TestCase):
    def test_store_workplanes(self):
        with BuildPart(Face.make_rect(5, 5, Plane.XZ)) as p1:
            Box(1, 1, 1)
            with BuildSketch(*p1.faces()) as s1:
                with BuildLine(Location()) as l1:
                    CenterArc((0, 0), 0.2, 0, 360)
                    self.assertEqual(len(l1.workplanes), 1)
                    self.assertTrue(l1.workplanes[0] == Plane.XY)
                make_face()
                # Circle(0.2)
                self.assertEqual(len(s1.workplanes), 6)
                self.assertTrue(all([isinstance(p, Plane) for p in s1.workplanes]))
            extrude(amount=0.1)
        self.assertTrue(p1.workplanes[0] == Plane.XZ)


class TestContextAwareSelectors(unittest.TestCase):
    def test_context_aware_selectors(self):
        with BuildPart() as p:
            Box(1, 1, 1)
            self.assertEqual(solids(), p.solids())
            self.assertEqual(faces(), p.faces())
            self.assertEqual(wires(), p.wires())
            self.assertEqual(edges(), p.edges())
            self.assertEqual(vertices(), p.vertices())
        with BuildSketch() as p:
            Rectangle(1, 1)
            self.assertEqual(faces(), p.faces())
            self.assertEqual(wires(), p.wires())
            self.assertEqual(edges(), p.edges())
            self.assertEqual(vertices(), p.vertices())
        with BuildLine() as p:
            Line((0, 0), (1, 0))
            self.assertEqual(edges(), p.edges())
            self.assertEqual(vertices(), p.vertices())
        with BuildSketch() as p:
            with GridLocations(2, 0, 2, 1):
                Circle(0.5)
                self.assertEqual(wires(), p.wires())


if __name__ == "__main__":
    unittest.main()
