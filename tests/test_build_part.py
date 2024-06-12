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


class TestMakeBrakeFormed(unittest.TestCase):
    def test_make_brake_formed(self):
        # TODO: Fix so this test doesn't raise a DeprecationWarning from NumPy
        with BuildPart() as bp:
            with BuildLine() as bl:
                Polyline((0, 0), (5, 6), (10, 1))
                fillet(bl.vertices(), 1)
            make_brake_formed(thickness=0.5, station_widths=[1, 2, 3, 4])
        self.assertTrue(bp.part.volume > 0)
        self.assertAlmostEqual(bp.part.bounding_box().max.Z, 4, 2)
        self.assertEqual(len(bp.faces().filter_by(GeomType.PLANE, reverse=True)), 3)

        outline = FilletPolyline((0, 0), (5, 6), (10, 1), radius=1)
        sheet_metal = make_brake_formed(thickness=0.5, station_widths=1, line=outline)
        self.assertAlmostEqual(sheet_metal.bounding_box().max.Z, 1, 2)


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
            with BuildSketch(test.faces().filter_by(Axis.Z)[-1]):
                Rectangle(5, 5)
            extrude(amount=5)
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
            with BuildSketch(*test.faces()):
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
                extrude(amount=1)

    def test_extrude_with_face_input(self):
        with BuildPart() as test:
            with BuildSketch() as f:
                Rectangle(5, 5)
            extrude(*f.sketch.faces(), amount=2.5, both=True)
        self.assertAlmostEqual(test.part.volume, 125, 5)

    def test_extrude_both(self):
        with BuildPart() as test:
            with BuildSketch():
                Rectangle(5, 5)
            extrude(amount=2.5, both=True)
        self.assertAlmostEqual(test.part.volume, 125, 5)

    def test_extrude_until(self):
        with BuildPart() as test:
            Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
            scale(by=(0.8, 0.8, 0.8), mode=Mode.SUBTRACT)
            with BuildSketch():
                Rectangle(1, 1)
            extrude(until=Until.NEXT)
        self.assertAlmostEqual(test.part.volume, 10**3 - 8**3 + 1**2 * 8, 5)

    def test_extrude_face(self):
        with BuildPart(Plane.XZ) as box:
            with BuildSketch(Plane.XZ, mode=Mode.PRIVATE) as square:
                Rectangle(10, 10, align=(Align.CENTER, Align.MIN))
            extrude(square.sketch, amount=10)
        self.assertAlmostEqual(box.part.volume, 10**3, 5)

    def test_extrude_non_planar_face(self):
        cyl = Cylinder(1, 2)
        npf = cyl.split(Plane.XZ).faces().filter_by(GeomType.PLANE, reverse=True)[0]
        test_solid = extrude(npf, amount=3, dir=(0, 1, 0))
        self.assertAlmostEqual(test_solid.volume, 2 * 2 * 3, 5)


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
                with BuildSketch(Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))):
                    Circle(10 * sin(i * pi / slice_count) + 5)
            loft()
        self.assertLess(test.part.volume, 225 * pi * 30, 5)
        self.assertGreater(test.part.volume, 25 * pi * 30, 5)

        sections = [
            Face(
                Wire(
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
            loft(sections)
        self.assertLess(test.part.volume, 225 * pi * 30, 5)
        self.assertGreater(test.part.volume, 25 * pi * 30, 5)

    def test_loft_vertex(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, 3)
            with BuildSketch() as s:
                Rectangle(1, 1)
            loft(sections=[s.sketch, v1], ruled=True)
        self.assertAlmostEqual(test.part.volume, 1, 5)

    def test_loft_vertices(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, 3)
            v2 = Vertex(0, 0, -3)
            with BuildSketch() as s:
                Rectangle(1, 1)
            loft(sections=[v2, s.sketch, v1], ruled=True)
        self.assertAlmostEqual(test.part.volume, 2, 5)

    def test_loft_vertex_face(self):
        v1 = Vertex(0, 0, 3)
        r = Rectangle(1, 1)
        test = loft(sections=[r.face(), v1], ruled=True)
        self.assertAlmostEqual(test.volume, 1, 5)

    def test_loft_no_sections_assert(self):
        with BuildPart() as test:
            with self.assertRaises(ValueError):
                loft(sections=[None])

    def test_loft_all_vertices_assert(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, -1)
            v2 = Vertex(0, 0, 2)
            with self.assertRaises(ValueError):
                loft(sections=[v1, v2])

    def test_loft_vertex_middle_assert(self):
        with BuildPart() as test:
            v1 = Vertex(0, 0, -1)
            v2 = Vertex(0, 0, 2)
            with BuildSketch() as s:
                Circle(1)
            with self.assertRaises(ValueError):
                loft(sections=[v1, v2, s.sketch])


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
                make_face()
            revolve(axis=Axis.Y)
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
                make_face()
            revolve(axis=Axis.X)
        self.assertLess(test.part.volume, 244 * pi * 20, 5)
        self.assertGreater(test.part.volume, 100 * pi * 20, 5)

    # Invalid test
    # def test_invalid_axis_origin(self):
    #     with BuildPart():
    #         with BuildSketch():
    #             Rectangle(1, 1, align=(Align.MIN, Align.MIN))
    #         with self.assertRaises(ValueError):
    #             revolve(axis=Axis((1, 1, 1), (0, 1, 0)))

    # Invalid test
    # def test_invalid_axis_direction(self):
    #     with BuildPart():
    #         with BuildSketch():
    #             Rectangle(1, 1, align=(Align.MIN, Align.MIN))
    #         with self.assertRaises(ValueError):
    #             revolve(axis=Axis.Z)


class TestSection(unittest.TestCase):
    def test_circle(self):
        with BuildPart() as test:
            Sphere(10)
            s = section()
        self.assertAlmostEqual(s.area, 100 * pi, 5)

    def test_custom_plane(self):
        with BuildPart() as test:
            Sphere(10)
            s = section(section_by=Plane.XZ)
        self.assertAlmostEqual(s.area, 100 * pi, 5)


class TestSplit(unittest.TestCase):
    def test_split(self):
        with BuildPart() as test:
            Sphere(10)
            split(keep=Keep.TOP)
        self.assertAlmostEqual(test.part.volume, (2 / 3) * 1000 * pi, 5)

    def test_split_both(self):
        with BuildPart() as test:
            Sphere(10)
            split(keep=Keep.BOTH)
        self.assertEqual(len(test.solids()), 2)

    def test_custom_plane(self):
        with BuildPart() as test:
            Sphere(10)
            split(bisect_by=Plane.YZ, keep=Keep.TOP)
        self.assertAlmostEqual(test.part.volume, (2 / 3) * 1000 * pi, 5)


class TestThicken(unittest.TestCase):
    def test_thicken(self):
        with BuildPart() as bp:
            with BuildSketch():
                RectangleRounded(10, 10, 1)
            thicken(amount=1)
        self.assertAlmostEqual(bp.part.bounding_box().max.Z, 1, 5)

        non_planar = Sphere(1).faces()[0]
        outer_sphere = thicken(non_planar, amount=0.1)
        self.assertAlmostEqual(outer_sphere.volume, (4 / 3) * pi * (1.1**3 - 1**3), 5)


class TestTorus(unittest.TestCase):
    def test_simple_torus(self):
        with BuildPart() as test:
            Torus(100, 10)
        self.assertAlmostEqual(test.part.volume, pi * 100 * 2 * pi * 100, 5)


class TestWedge(unittest.TestCase):
    def test_simple_wedge(self):
        wedge = Wedge(1, 1, 1, 0, 0, 2, 5)
        self.assertAlmostEqual(wedge.volume, 4.833333333333334, 5)

    def test_invalid_wedge(self):
        with self.assertRaises(ValueError):
            Wedge(0, 1, 1, 0, 0, 2, 5)

        with self.assertRaises(ValueError):
            Wedge(1, 0, 1, 0, 0, 2, 5)

        with self.assertRaises(ValueError):
            Wedge(1, 1, 0, 0, 0, 2, 5)


if __name__ == "__main__":
    unittest.main()
