"""
build123d imports

name: test_shape_list.py
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

# Always equal to any other object, to test that __eq__ cooperation is working
import io
import math
import re
import unittest

from IPython.lib import pretty
from build123d.build_common import GridLocations, PolarLocations
from build123d.build_enums import GeomType, SortBy
from build123d.build_part import BuildPart
from build123d.geometry import Axis, Plane, Vector
from build123d.objects_part import Box, Cylinder
from build123d.objects_sketch import RegularPolygon
from build123d.topology import (
    Compound,
    Edge,
    Face,
    ShapeList,
    Shell,
    Solid,
    Vertex,
    Wire,
)


class AlwaysEqual:
    def __eq__(self, other):
        return True


class TestShapeList(unittest.TestCase):
    """Test ShapeList functionality"""

    def assertDunderStrEqual(self, actual: str, expected_lines: list[str]):
        actual_lines = actual.splitlines()
        self.assertEqual(len(actual_lines), len(expected_lines))
        for actual_line, expected_line in zip(actual_lines, expected_lines):
            start, end = re.split(
                r"at 0x[0-9a-f]+", expected_line, maxsplit=2, flags=re.I
            )
            self.assertTrue(actual_line.startswith(start))
            self.assertTrue(actual_line.endswith(end))

    def assertDunderReprEqual(self, actual: str, expected: str):
        splitter = r"at 0x[0-9a-f]+"
        actual_split_list = re.split(splitter, actual, maxsplit=0, flags=re.I)
        expected_split_list = re.split(splitter, expected, maxsplit=0, flags=re.I)
        for actual_split, expected_split in zip(actual_split_list, expected_split_list):
            self.assertEqual(actual_split, expected_split)

    def test_sort_by(self):
        faces = Solid.make_box(1, 2, 3).faces() < SortBy.AREA
        self.assertAlmostEqual(faces[-1].area, 2, 5)

    def test_sort_by_lambda(self):
        c = Solid.make_cone(2, 1, 2)
        flat_faces = c.faces().filter_by(GeomType.PLANE)
        sorted_flat_faces = flat_faces.sort_by(lambda f: f.area)
        smallest = sorted_flat_faces[0]
        largest = sorted_flat_faces[-1]

        self.assertAlmostEqual(smallest.area, math.pi * 1**2, 5)
        self.assertAlmostEqual(largest.area, math.pi * 2**2, 5)

    def test_sort_by_property(self):
        box1 = Box(1, 1, 1)
        box2 = Box(2, 2, 2)
        box3 = Box(3, 3, 3)
        unsorted_boxes = ShapeList([box2, box3, box1])
        assert unsorted_boxes.sort_by(Solid.volume) == [box1, box2, box3]
        assert unsorted_boxes.sort_by(Solid.volume, reverse=True) == [box3, box2, box1]

    def test_sort_by_invalid(self):
        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).faces().sort_by(">Z")

    def test_filter_by_geomtype(self):
        non_planar_faces = (
            Solid.make_cylinder(1, 1).faces().filter_by(GeomType.PLANE, reverse=True)
        )
        self.assertEqual(len(non_planar_faces), 1)
        self.assertAlmostEqual(non_planar_faces[0].area, 2 * math.pi, 5)

        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).faces().filter_by("True")

    def test_filter_by_axis(self):
        box = Solid.make_box(1, 1, 1)
        self.assertEqual(len(box.faces().filter_by(Axis.X)), 2)
        self.assertEqual(len(box.edges().filter_by(Axis.X)), 4)
        self.assertEqual(len(box.vertices().filter_by(Axis.X)), 0)

    def test_filter_by_callable_predicate(self):
        boxes = [Solid.make_box(1, 1, 1) for _ in range(3)]
        boxes[0].label = "A"
        boxes[1].label = "A"
        boxes[2].label = "B"
        shapelist = ShapeList(boxes)

        self.assertEqual(len(shapelist.filter_by(lambda s: s.label == "A")), 2)
        self.assertEqual(len(shapelist.filter_by(lambda s: s.label == "B")), 1)

    def test_filter_by_property(self):
        box1 = Box(2, 2, 2)
        box2 = Box(2, 2, 2).translate((1, 1, 1))
        assert len((box1 + box2).edges().filter_by(Edge.is_interior)) == 6
        assert len((box1 - box2).edges().filter_by(Edge.is_interior)) == 3

    def test_first_last(self):
        vertices = (
            Solid.make_box(1, 1, 1).vertices().sort_by(Axis((0, 0, 0), (1, 1, 1)))
        )
        self.assertAlmostEqual(Vector(vertices.last), (1, 1, 1), 5)
        self.assertAlmostEqual(Vector(vertices.first), (0, 0, 0), 5)

    def test_group_by(self):
        vertices = Solid.make_box(1, 1, 1).vertices().group_by(Axis.Z)
        self.assertEqual(len(vertices[0]), 4)

        edges = Solid.make_box(1, 1, 1).edges().group_by(SortBy.LENGTH)
        self.assertEqual(len(edges[0]), 12)

        edges = (
            Solid.make_cone(2, 1, 2)
            .edges()
            .filter_by(GeomType.CIRCLE)
            .group_by(SortBy.RADIUS)
        )
        self.assertEqual(len(edges[0]), 1)

        edges = (Solid.make_cone(2, 1, 2).edges() | GeomType.CIRCLE) << SortBy.RADIUS
        self.assertAlmostEqual(edges[0].length, 2 * math.pi, 5)

        vertices = Solid.make_box(1, 1, 1).vertices().group_by(SortBy.DISTANCE)
        self.assertAlmostEqual(Vector(vertices[-1][0]), (1, 1, 1), 5)

        box = Solid.make_box(1, 1, 2)
        self.assertEqual(len(box.faces().group_by(SortBy.AREA)[0]), 2)
        self.assertEqual(len(box.faces().group_by(SortBy.AREA)[1]), 4)

        line = Edge.make_line((0, 0, 0), (1, 1, 2))
        vertices_by_line = box.vertices().group_by(line)
        self.assertEqual(len(vertices_by_line[0]), 1)
        self.assertEqual(len(vertices_by_line[1]), 2)
        self.assertEqual(len(vertices_by_line[2]), 1)
        self.assertEqual(len(vertices_by_line[3]), 1)
        self.assertEqual(len(vertices_by_line[4]), 2)
        self.assertEqual(len(vertices_by_line[5]), 1)
        self.assertAlmostEqual(Vector(vertices_by_line[0][0]), (0, 0, 0), 5)
        self.assertAlmostEqual(Vector(vertices_by_line[-1][0]), (1, 1, 2), 5)

        with BuildPart() as boxes:
            with GridLocations(10, 10, 3, 3):
                Box(1, 1, 1)
            with PolarLocations(100, 10):
                Box(1, 1, 2)
        self.assertEqual(len(boxes.solids().group_by(SortBy.VOLUME)[-1]), 10)
        self.assertEqual(len((boxes.solids()) << SortBy.VOLUME), 9)

        with self.assertRaises(ValueError):
            boxes.solids().group_by("AREA")

    def test_group_by_callable_predicate(self):
        boxesA = [Solid.make_box(1, 1, 1) for _ in range(3)]
        boxesB = [Solid.make_box(1, 1, 1) for _ in range(2)]
        for box in boxesA:
            box.label = "A"
        for box in boxesB:
            box.label = "B"
        boxNoLabel = Solid.make_box(1, 1, 1)

        shapelist = ShapeList(boxesA + boxesB + [boxNoLabel])
        result = shapelist.group_by(lambda shape: shape.label)

        self.assertEqual([len(group) for group in result], [1, 3, 2])

    def test_group_by_property(self):
        box1 = Box(2, 2, 2)
        box2 = Box(2, 2, 2).translate((1, 1, 1))
        g1 = (box1 + box2).edges().group_by(Edge.is_interior)
        assert len(g1.group(True)) == 6
        assert len(g1.group(False)) == 24

        g2 = (box1 - box2).edges().group_by(Edge.is_interior)
        assert len(g2.group(True)) == 3
        assert len(g2.group(False)) == 18

    def test_group_by_retrieve_groups(self):
        boxesA = [Solid.make_box(1, 1, 1) for _ in range(3)]
        boxesB = [Solid.make_box(1, 1, 1) for _ in range(2)]
        for box in boxesA:
            box.label = "A"
        for box in boxesB:
            box.label = "B"
        boxNoLabel = Solid.make_box(1, 1, 1)

        shapelist = ShapeList(boxesA + boxesB + [boxNoLabel])
        result = shapelist.group_by(lambda shape: shape.label)

        self.assertEqual(len(result.group("")), 1)
        self.assertEqual(len(result.group("A")), 3)
        self.assertEqual(len(result.group("B")), 2)
        self.assertEqual(result.group(""), result[0])
        self.assertEqual(result.group("A"), result[1])
        self.assertEqual(result.group("B"), result[2])
        self.assertEqual(result.group_for(boxesA[0]), result.group_for(boxesA[0]))
        self.assertNotEqual(result.group_for(boxesA[0]), result.group_for(boxesB[0]))
        with self.assertRaises(KeyError):
            result.group("C")

    def test_group_by_str_repr(self):
        nonagon = RegularPolygon(5, 9)

        expected = [
            "[[<build123d.topology.one_d.Edge at 0x1277f6e1cd0>],",
            " [<build123d.topology.one_d.Edge at 0x1277f6e1c10>,",
            "  <build123d.topology.one_d.Edge at 0x1277fd8a090>],",
            " [<build123d.topology.one_d.Edge at 0x1277f75d690>,",
            "  <build123d.topology.one_d.Edge at 0x127760d9310>],",
            " [<build123d.topology.one_d.Edge at 0x12777261f90>,",
            "  <build123d.topology.one_d.Edge at 0x1277f6bd2d0>],",
            " [<build123d.topology.one_d.Edge at 0x1276fbb0590>,",
            "  <build123d.topology.one_d.Edge at 0x1277fec6d90>]]",
        ]
        self.assertDunderStrEqual(str(nonagon.edges().group_by(Axis.X)), expected)

        expected_repr = (
            "[[<build123d.topology.one_d.Edge object at 0x000001277FEC6D90>],"
            " [<build123d.topology.one_d.Edge object at 0x000001277F6BCC10>,"
            " <build123d.topology.one_d.Edge object at 0x000001277EC3D5D0>],"
            " [<build123d.topology.one_d.Edge object at 0x000001277F6BEA90>,"
            " <build123d.topology.one_d.Edge object at 0x000001276FCB2310>],"
            " [<build123d.topology.one_d.Edge object at 0x000001277F6D10D0>,"
            " <build123d.topology.one_d.Edge object at 0x000001276FBAAD10>],"
            " [<build123d.topology.one_d.Edge object at 0x000001277FC86F90>,"
            " <build123d.topology.one_d.Edge object at 0x000001277F6E1CD0>]]"
        )
        self.assertDunderReprEqual(
            repr(nonagon.edges().group_by(Axis.X)), expected_repr
        )

        f = io.StringIO()
        p = pretty.PrettyPrinter(f)
        nonagon.edges().group_by(Axis.X)._repr_pretty_(p, cycle=True)
        self.assertEqual(f.getvalue(), "(...)")

    def test_distance(self):
        with BuildPart() as box:
            Box(1, 2, 3)
        obj = (-0.2, 0.1, 0.5)
        edges = box.edges().sort_by_distance(obj)
        distances = [Vertex(*obj).distance_to(edge) for edge in edges]
        self.assertTrue(
            all([distances[i] >= distances[i - 1] for i in range(1, len(edges))])
        )

    def test_distance_reverse(self):
        with BuildPart() as box:
            Box(1, 2, 3)
        obj = (-0.2, 0.1, 0.5)
        edges = box.edges().sort_by_distance(obj, reverse=True)
        distances = [Vertex(*obj).distance_to(edge) for edge in edges]
        self.assertTrue(
            all([distances[i] <= distances[i - 1] for i in range(1, len(edges))])
        )

    def test_distance_equal(self):
        with BuildPart() as box:
            Box(1, 1, 1)
        self.assertEqual(len(box.edges().sort_by_distance((0, 0, 0))), 12)

    def test_vertices(self):
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        self.assertEqual(len(sl.vertices()), 8)

    def test_vertex(self):
        sl = ShapeList([Edge.make_circle(1)])
        self.assertAlmostEqual(tuple(sl.vertex()), (1, 0, 0), 5)
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        with self.assertWarns(UserWarning):
            sl.vertex()
        self.assertEqual(len(Edge().vertices()), 0)

    def test_edges(self):
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        self.assertEqual(len(sl.edges()), 8)
        self.assertEqual(len(Edge().edges()), 0)

    def test_edge(self):
        sl = ShapeList([Edge.make_circle(1)])
        self.assertAlmostEqual(sl.edge().length, 2 * 1 * math.pi, 5)
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        with self.assertWarns(UserWarning):
            sl.edge()

    def test_wires(self):
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        self.assertEqual(len(sl.wires()), 2)
        self.assertEqual(len(Wire().wires()), 0)

    def test_wire(self):
        sl = ShapeList([Wire.make_circle(1)])
        self.assertAlmostEqual(sl.wire().length, 2 * 1 * math.pi, 5)
        sl = ShapeList([Face.make_rect(1, 1), Face.make_rect(1, 1, Plane((4, 4)))])
        with self.assertWarns(UserWarning):
            sl.wire()

    def test_faces(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        self.assertEqual(len(sl.faces()), 9)
        self.assertEqual(len(Face().faces()), 0)

    def test_face(self):
        sl = ShapeList(
            [Vertex(1, 1, 1), Edge.make_line((0, 0), (1, 1)), Face.make_rect(2, 1)]
        )
        self.assertAlmostEqual(sl.face().area, 2 * 1, 5)
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.face()

    def test_shells(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        self.assertEqual(len(sl.shells()), 2)
        self.assertEqual(len(Shell().shells()), 0)

    def test_shell(self):
        sl = ShapeList([Vertex(1, 1, 1), Solid.make_box(1, 1, 1)])
        self.assertAlmostEqual(sl.shell().area, 6 * 1 * 1, 5)
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.shell()

    def test_solids(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        self.assertEqual(len(sl.solids()), 2)
        self.assertEqual(len(Solid().solids()), 0)

    def test_solid(self):
        sl = ShapeList([Solid.make_box(1, 1, 1), Solid.make_cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.solid()
        sl = ShapeList([Solid.make_box(1, 2, 3), Vertex(1, 1, 1)])
        self.assertAlmostEqual(sl.solid().volume, 1 * 2 * 3, 5)

    def test_compounds(self):
        sl = ShapeList([Box(1, 1, 1), Cylinder(1, 1)])
        self.assertEqual(len(sl.compounds()), 2)
        self.assertEqual(len(Compound().compounds()), 0)

    def test_compound(self):
        sl = ShapeList([Box(1, 1, 1), Cylinder(1, 1)])
        with self.assertWarns(UserWarning):
            sl.compound()
        sl = ShapeList([Box(1, 2, 3), Vertex(1, 1, 1)])
        self.assertAlmostEqual(sl.compound().volume, 1 * 2 * 3, 5)

    def test_equal(self):
        box = Box(1, 1, 1)
        cyl = Cylinder(1, 1)
        sl = ShapeList([box, cyl])
        same = ShapeList([cyl, box])
        self.assertEqual(sl, same)
        self.assertEqual(sl, AlwaysEqual())

    def test_not_equal(self):
        sl = ShapeList([Box(1, 1, 1), Cylinder(1, 1)])
        diff = ShapeList([Box(1, 1, 1), Box(1, 2, 3)])
        self.assertNotEqual(sl, diff)
        self.assertNotEqual(sl, object())

    def test_center(self):
        self.assertEqual(tuple(ShapeList().center()), (0, 0, 0))
        self.assertEqual(
            tuple(ShapeList(Vertex(i, 0, 0) for i in range(3)).center()), (1, 0, 0)
        )


class TestShapeListAddition(unittest.TestCase):
    def setUp(self):
        # Create distinct faces to test with
        self.face1 = Box(1, 1, 1).faces().sort_by(Axis.Z)[0]  # bottom face
        self.face2 = Box(1, 1, 1).faces().sort_by(Axis.Z)[-1]  # top face
        self.face3 = Box(1, 1, 1).faces().sort_by(Axis.X)[0]  # side face

    def test_add_single_shape(self):
        sl = ShapeList([self.face1])
        result = sl + self.face2
        self.assertIsInstance(result, ShapeList)
        self.assertEqual(len(result), 2)
        self.assertIn(self.face1, result)
        self.assertIn(self.face2, result)

    def test_add_shape_list(self):
        sl1 = ShapeList([self.face1])
        sl2 = ShapeList([self.face2, self.face3])
        result = sl1 + sl2
        self.assertIsInstance(result, ShapeList)
        self.assertEqual(len(result), 3)
        self.assertListEqual(result, [self.face1, self.face2, self.face3])

    def test_iadd_single_shape(self):
        sl = ShapeList([self.face1])
        sl_id_before = id(sl)
        sl += self.face2
        self.assertEqual(id(sl), sl_id_before)  # in-place mutation
        self.assertEqual(len(sl), 2)
        self.assertListEqual(sl, [self.face1, self.face2])

    def test_iadd_shape_list(self):
        sl = ShapeList([self.face1])
        sl += ShapeList([self.face2, self.face3])
        self.assertEqual(len(sl), 3)
        self.assertListEqual(sl, [self.face1, self.face2, self.face3])

    def test_add_vector(self):
        vector = Vector(1, 2, 3)
        sl = ShapeList([vector])
        sl += Vector(4, 5, 6)
        self.assertEqual(len(sl), 2)
        self.assertIsInstance(sl[0], Vector)
        self.assertIsInstance(sl[1], Vector)

    def test_add_invalid_type(self):
        sl = ShapeList([self.face1])
        with self.assertRaises(TypeError):
            _ = sl + 123  # type: ignore

        with self.assertRaises(TypeError):
            sl += "not a shape"  # type: ignore


if __name__ == "__main__":
    unittest.main()
