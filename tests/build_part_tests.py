"""

build123d BuildPart tests

name: build_part_tests.py
by:   Gumyr
date: July 28th 2022

desc: Unit tests for the build123d build_part module

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
from math import pi, sin
from build123d import *
from cadquery import Compound, Plane, Vector, Edge, Location, Face, Wire


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class BuildPartTests(unittest.TestCase):
    """Test the BuildPart Builder derived class"""

    def test_select_vertices(self):
        """Test vertices()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.vertices()), 8)
            Box(5, 5, 20, centered=(True, True, False))
        self.assertEqual(len(test.vertices(Select.LAST)), 8)

    def test_select_edges(self):
        """Test edges()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.edges()), 12)
            Box(5, 5, 20, centered=(True, True, False))
        self.assertEqual(len(test.edges(Select.LAST)), 12)

    def test_select_faces(self):
        """Test faces()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.faces()), 6)
            WorkplanesFromFaces(test.faces().filter_by_axis(Axis.Z)[-1])
            with BuildSketch():
                Rectangle(5, 5)
            Extrude(5)
        self.assertEqual(len(test.faces()), 11)
        self.assertEqual(len(test.faces(Select.LAST)), 6)

    def test_select_solids(self):
        """Test faces()"""
        with BuildPart() as test:
            for i in [5, 10]:
                PushPoints((3 * i, 0, 0))
                Box(10, 10, i)
            Box(20, 5, 5)
        self.assertEqual(len(test.solids()), 2)
        self.assertEqual(len(test.solids(Select.LAST)), 1)

    def test_mode_add_multiple(self):
        with BuildPart() as test:
            PolarArray(30, 0, 360, 5)
            Box(20, 20, 20)
        self.assertAlmostEqual(len(test.solids()), 5)

    def test_mode_subtract(self):
        with BuildPart() as test:
            Box(20, 20, 20)
            Sphere(10, mode=Mode.SUBTRACT)
        self.assertTrue(isinstance(test._obj, Compound))
        self.assertAlmostEqual(test.part.Volume(), 8000 - (4000 / 3) * pi, 5)

    def test_mode_intersect(self):
        """Note that a negative volume is created"""
        with BuildPart() as test:
            Box(20, 20, 20)
            Sphere(10, mode=Mode.INTERSECT)
        self.assertAlmostEqual(abs(test.part.Volume()), (4000 / 3) * pi, 5)

    def test_mode_replace(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            Sphere(10, mode=Mode.REPLACE)
        self.assertAlmostEqual(test.part.Volume(), (4000 / 3) * pi, 5)

    def test_add_pending_faces(self):
        with BuildPart() as test:
            Box(100, 100, 100)
            WorkplanesFromFaces(*test.faces())
            with BuildSketch():
                PolarArray(10, 0, 360, 5)
                Circle(2)
        self.assertEqual(test.workplane_count, 6)
        self.assertEqual(test.pending_faces_count, 30)

    def test_add_pending_edges(self):
        with BuildPart() as test:
            Box(100, 100, 100)
            WorkplanesFromFaces(*test.faces())
            with BuildLine():
                CenterArc((0, 0), 5, 0, 180)
        self.assertEqual(test.pending_edges_count, 6)

    def test_add_pending_location_count(self):
        with BuildPart() as test:
            PolarArray(30, 0, 360, 5)
        self.assertEqual(test.pending_location_count, 5)


class BuildPartExceptions(unittest.TestCase):
    """Test exception handling"""

    def test_invalid_subtract(self):
        with self.assertRaises(RuntimeError):
            with BuildPart():
                Sphere(10, mode=Mode.SUBTRACT)

    def test_invalid_intersect(self):
        with self.assertRaises(RuntimeError):
            with BuildPart():
                Sphere(10, mode=Mode.INTERSECT)


class TestCounterBoreHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            PushPoints(test.faces().filter_by_axis(Axis.Z)[-1].Center())
            CounterBoreHole(2, 3, 1, 5)
        self.assertAlmostEqual(test.part.Volume(), 1000 - 4 * 4 * pi - 9 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            PushPoints(test.faces().filter_by_axis(Axis.Z)[-1].Center())
            CounterBoreHole(2, 3, 1)
        self.assertAlmostEqual(test.part.Volume(), 1000 - 4 * 9 * pi - 9 * pi, 5)


class TestCounterSinkHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            PushPoints(test.faces().filter_by_axis(Axis.Z)[-1].Center())
            CounterSinkHole(2, 4, 5)
        self.assertLess(test.part.Volume(), 1000, 5)
        self.assertGreater(test.part.Volume(), 1000 - 16 * 5 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            PushPoints(test.faces().filter_by_axis(Axis.Z)[-1].Center())
            CounterSinkHole(2, 4)
        self.assertLess(test.part.Volume(), 1000, 5)
        self.assertGreater(test.part.Volume(), 1000 - 16 * 10 * pi, 5)


class TestExtrude(unittest.TestCase):
    def test_extrude_both(self):
        with BuildPart() as test:
            with BuildSketch():
                Rectangle(5, 5)
            Extrude(2.5, both=True)
        self.assertAlmostEqual(test.part.Volume(), 125, 5)


class TestHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            PushPoints(test.faces().filter_by_axis(Axis.Z)[-1].Center())
            Hole(2, 5)
        self.assertAlmostEqual(test.part.Volume(), 1000 - 4 * 5 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            PushPoints(test.faces().filter_by_axis(Axis.Z)[-1].Center())
            Hole(2)
        self.assertAlmostEqual(test.part.Volume(), 1000 - 4 * 10 * pi, 5)


class TestLoft(unittest.TestCase):
    def test_simple_loft(self):
        with BuildPart() as test:
            slice_count = 10
            for i in range(slice_count + 1):
                Workplanes(Plane(origin=(0, 0, i * 3), normal=(0, 0, 1)))
                with BuildSketch():
                    Circle(10 * sin(i * pi / slice_count) + 5)
            Loft()
        self.assertLess(test.part.Volume(), 225 * pi * 30, 5)
        self.assertGreater(test.part.Volume(), 25 * pi * 30, 5)

        sections = [
            Face.makeFromWires(
                Wire.assembleEdges(
                    [
                        Edge.makeCircle(10 * sin(i * pi / slice_count) + 5).moved(
                            Location(Vector(0, 0, i * 3))
                        )
                    ]
                )
            )
            for i in range(slice_count + 1)
        ]
        with BuildPart() as test:
            Loft(*sections)
        self.assertLess(test.part.Volume(), 225 * pi * 30, 5)
        self.assertGreater(test.part.Volume(), 25 * pi * 30, 5)


class TestRevolve(unittest.TestCase):
    def test_simple_revolve(self):
        with BuildPart() as test:
            with BuildSketch():
                with BuildLine():
                    l1 = Line((0, 0), (12, 0))
                    l2 = RadiusArc(l1 @ 1, (15, 20), 50)
                    l3 = Spline(
                        l2 @ 1, (22, 40), (20, 50), tangents=(l2 % 1, (-0.75, 1))
                    )
                    l4 = RadiusArc(l3 @ 1, l3 @ 1 + Vector(0, 5), 5)
                    l5 = Spline(
                        l4 @ 1,
                        l4 @ 1 + Vector(2.5, 2.5),
                        l4 @ 1 + Vector(0, 5),
                        tangents=(l4 % 1, (-1, 0)),
                    )
                    Polyline(
                        l5 @ 1,
                        l5 @ 1 + Vector(0, 1),
                        (0, (l5 @ 1).y + 1),
                        l1 @ 0,
                    )
                BuildFace()
            Revolve()
        self.assertLess(test.part.Volume(), 22**2 * pi * 50, 5)
        self.assertGreater(test.part.Volume(), 144 * pi * 50, 5)

    def test_revolve_with_axis(self):
        with BuildPart() as test:
            with BuildSketch():
                with BuildLine():
                    l1 = Line((0, 0), (0, 12))
                    l2 = RadiusArc(l1 @ 1, (20, 10), 50)
                    l3 = Line(l2 @ 1, (20, 0))
                    l4 = Line(l3 @ 1, l1 @ 0)
                BuildFace()
            Revolve(axis_start=(0, 0, 0), axis_end=(1, 0, 0))
        self.assertLess(test.part.Volume(), 244 * pi * 20, 5)
        self.assertGreater(test.part.Volume(), 100 * pi * 20, 5)


class TestSection(unittest.TestCase):
    def test_circle(self):
        with BuildPart() as test:
            Sphere(10)
            Section()
        self.assertAlmostEqual(test.faces()[-1].Area(), 100 * pi, 5)

    # def test_custom_plane(self):
    #     with BuildPart() as test:
    #         Sphere(10)
    #         Section(Plane.named("XZ"))
    #     self.assertAlmostEqual(
    #         test.faces().filter_by_axis(Axis.Y)[-1].Area(), 100 * pi, 5
    #     )


class TestShell(unittest.TestCase):
    def test_box_shell(self):
        with BuildPart() as test:
            Cylinder(10, 10)
            Shell(thickness=1, kind=Kind.INTERSECTION)
        self.assertAlmostEqual(
            test.part.Volume(), 11**2 * pi * 12 - 10**2 * pi * 10, 5
        )


class TestSplit(unittest.TestCase):
    def test_split(self):
        with BuildPart() as test:
            Sphere(10)
            Split(keep=Keep.TOP)
        self.assertAlmostEqual(test.part.Volume(), (2 / 3) * 1000 * pi, 5)

    def test_split_both(self):
        with BuildPart() as test:
            Sphere(10)
            Split(keep=Keep.BOTH)
        self.assertEqual(len(test.solids()), 2)


class TestSweep(unittest.TestCase):
    def test_single_section(self):
        with BuildPart() as test:
            with BuildLine():
                Line((0, 0, 0), (0, 0, 10))
            with BuildSketch():
                Rectangle(2, 2)
            Sweep()
        self.assertAlmostEqual(test.part.Volume(), 40, 5)

    def test_multi_section(self):
        segment_count = 6
        with BuildPart() as handle:
            with BuildLine() as handle_center_line:
                Spline(
                    (-10, 0, 0),
                    (0, 0, 5),
                    (10, 0, 0),
                    tangents=((0, 0, 1), (0, 0, -1)),
                    tangent_scalars=(1.5, 1.5),
                )
            handle_path = handle_center_line.line_as_wire
            for i in range(segment_count + 1):
                Workplanes(
                    Plane(
                        origin=handle_path @ (i / segment_count),
                        normal=handle_path % (i / segment_count),
                    )
                )
                with BuildSketch() as section:
                    if i % segment_count == 0:
                        Circle(1)
                    else:
                        Rectangle(1, 2)
                        Fillet(*section.vertices(), radius=0.2)
            # Create the handle by sweeping along the path
            Sweep(multisection=True)
        self.assertAlmostEqual(handle.part.Volume(), 54.11246334691092, 5)

    def test_passed_parameters(self):
        with BuildLine() as path:
            Line((0, 0, 0), (0, 0, 10))
        with BuildSketch() as section:
            Rectangle(2, 2)
        with BuildPart() as test:
            Sweep(*section.faces(), path=path.line_as_wire)
        self.assertAlmostEqual(test.part.Volume(), 40, 5)


class TestTorus(unittest.TestCase):
    def test_simple_torus(self):
        with BuildPart() as test:
            Torus(100, 10)
        self.assertAlmostEqual(test.part.Volume(), pi * 100 * 2 * pi * 100, 5)


if __name__ == "__main__":
    unittest.main()
