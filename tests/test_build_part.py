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
from build123d import LocationList, WorkplaneList


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class TestAlign(unittest.TestCase):
    def test_align(self):
        with BuildPart() as max:
            Box(1, 1, 1, align=(Align.MIN, Align.CENTER, Align.MAX))
        bbox = max.part.bounding_box()
        self.assertGreaterEqual(bbox.min.X, 0)
        self.assertLessEqual(bbox.max.X, 1)
        self.assertGreaterEqual(bbox.min.Y, -0.5)
        self.assertLessEqual(bbox.max.Y, 0.5)
        self.assertGreaterEqual(bbox.min.Z, -1)
        self.assertLessEqual(bbox.max.Z, 0)


class TestBuildPart(unittest.TestCase):
    """Test the BuildPart Builder derived class"""

    def test_obj_name(self):
        with BuildPart() as test:
            pass
        self.assertEqual(test._obj_name, "part")

    def test_invalid_add_to_context_input(self):
        with self.assertRaises(ValueError):
            with BuildPart() as test:
                test._add_to_context(*[4, 4])

    def test_select_vertices(self):
        """Test vertices()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.vertices()), 8)
            Box(5, 5, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        self.assertEqual(len(test.vertices(Select.LAST)), 8)

    def test_select_edges(self):
        """Test edges()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.edges()), 12)
            Box(5, 5, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        self.assertEqual(len(test.edges(Select.LAST)), 12)

    def test_select_faces(self):
        """Test faces()"""
        with BuildPart() as test:
            Box(10, 10, 10)
            self.assertEqual(len(test.faces()), 6)
            with Workplanes(test.faces().filter_by(Axis.Z)[-1]):
                with BuildSketch():
                    Rectangle(5, 5)
            Extrude(amount=5)
        self.assertEqual(len(test.faces()), 11)
        self.assertEqual(len(test.faces(Select.LAST)), 6)

    def test_select_solids(self):
        """Test faces()"""
        with BuildPart() as test:
            for i in [5, 10]:
                with Locations((3 * i, 0, 0)):
                    Box(10, 10, i)
            Box(20, 5, 5)
        self.assertEqual(len(test.solids()), 2)
        self.assertEqual(len(test.solids(Select.LAST)), 1)

    def test_mode_add_multiple(self):
        with BuildPart() as test:
            with PolarLocations(30, 5):
                Box(20, 20, 20)
        self.assertAlmostEqual(len(test.solids()), 5)

    def test_mode_subtract(self):
        with BuildPart() as test:
            Box(20, 20, 20)
            Sphere(10, mode=Mode.SUBTRACT)
        self.assertTrue(isinstance(test._obj, Compound))
        self.assertAlmostEqual(test.part.volume, 8000 - (4000 / 3) * pi, 5)

    def test_mode_intersect(self):
        """Note that a negative volume is created"""
        with BuildPart() as test:
            Box(20, 20, 20)
            Sphere(10, mode=Mode.INTERSECT)
        self.assertAlmostEqual(abs(test.part.volume), (4000 / 3) * pi, 5)

    def test_mode_replace(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            Sphere(10, mode=Mode.REPLACE)
        self.assertAlmostEqual(test.part.volume, (4000 / 3) * pi, 5)

    def test_add_pending_faces(self):
        with BuildPart() as test:
            Box(100, 100, 100)
            with Workplanes(*test.faces()):
                with BuildSketch():
                    with PolarLocations(10, 5):
                        Circle(2)
        self.assertEqual(len(test.pending_faces), 30)
        # self.assertEqual(sum([len(s.faces()) for s in test.pending_faces]), 30)

    def test_add_pending_edges(self):
        with BuildPart() as test:
            Box(100, 100, 100)
            with BuildLine():
                CenterArc((0, 0), 5, 0, 180)
        self.assertEqual(len(test.pending_edges), 1)

    def test_add_pending_location_count(self):
        with BuildPart() as test:
            with PolarLocations(30, 5):
                self.assertEqual(len(LocationList._get_context().locations), 5)

    def test_named_plane(self):
        with BuildPart(Plane.YZ) as test:
            self.assertTupleAlmostEquals(
                WorkplaneList._get_context().workplanes[0].z_dir.to_tuple(),
                (1, 0, 0),
                5,
            )

    def test_part_transfer_on_exit(self):
        with BuildPart(Plane.XY) as test:
            Box(1, 1, 1)
            with BuildPart(Plane.XY.offset(1)):
                Box(1, 1, 1)
        self.assertAlmostEqual(test.part.volume, 2, 5)


class TestBuildPartExceptions(unittest.TestCase):
    """Test exception handling"""

    def test_invalid_subtract(self):
        with self.assertRaises(RuntimeError):
            with BuildPart():
                Sphere(10, mode=Mode.SUBTRACT)

    def test_invalid_intersect(self):
        with self.assertRaises(RuntimeError):
            with BuildPart():
                Sphere(10, mode=Mode.INTERSECT)

    def test_no_applies_to(self):
        with self.assertRaises(RuntimeError):
            BuildPart._get_context(
                Compound.make_compound([Face.make_rect(1, 1)]).wrapped
            )
        with self.assertRaises(RuntimeError):
            Box(1, 1, 1)


class TestCounterBoreHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterBoreHole(2, 3, 1, 5)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 4 * pi - 9 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterBoreHole(2, 3, 1)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 9 * pi - 9 * pi, 5)


class TestCounterSinkHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterSinkHole(2, 4, 5)
        self.assertLess(test.part.volume, 1000, 5)
        self.assertGreater(test.part.volume, 1000 - 16 * 5 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                CounterSinkHole(2, 4)
        self.assertLess(test.part.volume, 1000, 5)
        self.assertGreater(test.part.volume, 1000 - 16 * 10 * pi, 5)


class TestCylinder(unittest.TestCase):
    def test_simple_torus(self):
        with BuildPart() as test:
            Cylinder(2, 10)
        self.assertAlmostEqual(test.part.volume, pi * 2**2 * 10, 5)


class TestExtrude(unittest.TestCase):
    def test_no_faces(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                Extrude(amount=1)

    def test_extrude_with_face_input(self):
        with BuildPart() as test:
            with BuildSketch() as f:
                Rectangle(5, 5)
            Extrude(*f.sketch.faces(), amount=2.5, both=True)
        self.assertAlmostEqual(test.part.volume, 125, 5)

    def test_extrude_both(self):
        with BuildPart() as test:
            with BuildSketch():
                Rectangle(5, 5)
            Extrude(amount=2.5, both=True)
        self.assertAlmostEqual(test.part.volume, 125, 5)

    def test_extrude_until(self):
        with BuildPart() as test:
            Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
            Scale(by=(0.8, 0.8, 0.8), mode=Mode.SUBTRACT)
            with BuildSketch():
                Rectangle(1, 1)
            Extrude(until=Until.NEXT)
        self.assertAlmostEqual(test.part.volume, 10**3 - 8**3 + 1**2 * 8, 5)

    def test_extrude_face(self):
        with BuildPart(Plane.XZ) as box:
            with BuildSketch(Plane.XZ, mode=Mode.PRIVATE) as square:
                Rectangle(10, 10, align=(Align.CENTER, Align.MIN))
            Extrude(square.sketch, amount=10)
        self.assertAlmostEqual(box.part.volume, 10**3, 5)


class TestHole(unittest.TestCase):
    def test_fixed_depth(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                Hole(2, 5)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 5 * pi, 5)

    def test_through_hole(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            with Locations(test.faces().filter_by(Axis.Z)[-1].center()):
                Hole(2)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 10 * pi, 5)


class TestLoft(unittest.TestCase):
    def test_simple_loft(self):
        with BuildPart() as test:
            slice_count = 10
            for i in range(slice_count + 1):
                with Workplanes(Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))):
                    with BuildSketch():
                        Circle(10 * sin(i * pi / slice_count) + 5)
            Loft()
        self.assertLess(test.part.volume, 225 * pi * 30, 5)
        self.assertGreater(test.part.volume, 25 * pi * 30, 5)

        sections = [
            Face.make_from_wires(
                Wire.make_wire(
                    [
                        Edge.make_circle(10 * sin(i * pi / slice_count) + 5).moved(
                            Location(Vector(0, 0, i * 3))
                        )
                    ]
                )
            )
            for i in range(slice_count + 1)
        ]
        with BuildPart() as test:
            Loft(*sections)
        self.assertLess(test.part.volume, 225 * pi * 30, 5)
        self.assertGreater(test.part.volume, 25 * pi * 30, 5)


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
                        (0, (l5 @ 1).Y + 1),
                        l1 @ 0,
                    )
                MakeFace()
            Revolve(axis=Axis.Y)
        self.assertLess(test.part.volume, 22**2 * pi * 50, 5)
        self.assertGreater(test.part.volume, 144 * pi * 50, 5)

    def test_revolve_with_axis(self):
        with BuildPart() as test:
            with BuildSketch():
                with BuildLine():
                    l1 = Line((0, 0), (0, 12))
                    l2 = RadiusArc(l1 @ 1, (20, 10), 50)
                    l3 = Line(l2 @ 1, (20, 0))
                    l4 = Line(l3 @ 1, l1 @ 0)
                MakeFace()
            Revolve(axis=Axis.X)
        self.assertLess(test.part.volume, 244 * pi * 20, 5)
        self.assertGreater(test.part.volume, 100 * pi * 20, 5)

    def test_invalid_axis_origin(self):
        with BuildPart():
            with BuildSketch():
                Rectangle(1, 1, align=(Align.MIN, Align.MIN))
            with self.assertRaises(ValueError):
                Revolve(axis=Axis((1, 1, 1), (0, 1, 0)))

    def test_invalid_axis_direction(self):
        with BuildPart():
            with BuildSketch():
                Rectangle(1, 1, align=(Align.MIN, Align.MIN))
            with self.assertRaises(ValueError):
                Revolve(axis=Axis.Z)


class TestSection(unittest.TestCase):
    def test_circle(self):
        with BuildPart() as test:
            Sphere(10)
            Section()
        self.assertAlmostEqual(test.faces()[-1].area, 100 * pi, 5)

    def test_custom_plane(self):
        with BuildPart() as test:
            Sphere(10)
            Section(Plane.XZ)
        self.assertAlmostEqual(test.faces().filter_by(Axis.Y)[-1].area, 100 * pi, 5)


class TestSplit(unittest.TestCase):
    def test_split(self):
        with BuildPart() as test:
            Sphere(10)
            Split(keep=Keep.TOP)
        self.assertAlmostEqual(test.part.volume, (2 / 3) * 1000 * pi, 5)

    def test_split_both(self):
        with BuildPart() as test:
            Sphere(10)
            Split(keep=Keep.BOTH)
        self.assertEqual(len(test.solids()), 2)

    def test_custom_plane(self):
        with BuildPart() as test:
            Sphere(10)
            Split(bisect_by=Plane.YZ, keep=Keep.TOP)
        self.assertAlmostEqual(test.part.volume, (2 / 3) * 1000 * pi, 5)


class TestSweep(unittest.TestCase):
    def test_single_section(self):
        with BuildPart() as test:
            with BuildLine():
                Line((0, 0, 0), (0, 0, 10))
            with BuildSketch():
                Rectangle(2, 2)
            Sweep()
        self.assertAlmostEqual(test.part.volume, 40, 5)

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
            handle_path = handle_center_line.wires()[0]
            for i in range(segment_count + 1):
                with Workplanes(
                    Plane(
                        origin=handle_path @ (i / segment_count),
                        z_dir=handle_path % (i / segment_count),
                    )
                ):
                    with BuildSketch() as section:
                        if i % segment_count == 0:
                            Circle(1)
                        else:
                            Rectangle(1, 2)
                            Fillet(*section.vertices(), radius=0.2)
            # Create the handle by sweeping along the path
            Sweep(multisection=True)
        self.assertAlmostEqual(handle.part.volume, 54.11246334691092, 5)

    def test_passed_parameters(self):
        with BuildLine() as path:
            Line((0, 0, 0), (0, 0, 10))
        with BuildSketch() as section:
            Rectangle(2, 2)
        with BuildPart() as test:
            Sweep(*section.faces(), path=path.wires()[0])
        self.assertAlmostEqual(test.part.volume, 40, 5)

    def test_binormal(self):
        with BuildPart() as sweep_binormal:
            with BuildLine() as path:
                Spline((0, 0, 0), (-12, 8, 10), tangents=[(0, 0, 1), (-1, 0, 0)])
            with BuildLine(mode=Mode.PRIVATE) as binormal:
                Line((-5, 5), (-8, 10))
            with BuildSketch() as section:
                Rectangle(4, 6)
            Sweep(binormal=binormal.edges()[0])

        end_face: Face = (
            sweep_binormal.faces().filter_by(GeomType.PLANE).sort_by(Axis.X)[0]
        )
        face_binormal_axis = Axis(
            end_face.center(), binormal.edges()[0] @ 1 - end_face.center()
        )
        face_normal_axis = Axis(end_face.center(), end_face.normal_at())
        self.assertTrue(face_normal_axis.is_normal(face_binormal_axis))


class TestTorus(unittest.TestCase):
    def test_simple_torus(self):
        with BuildPart() as test:
            Torus(100, 10)
        self.assertAlmostEqual(test.part.volume, pi * 100 * 2 * pi * 100, 5)


if __name__ == "__main__":
    unittest.main()
