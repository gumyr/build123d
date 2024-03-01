"""

build123d BuildGeneric tests

name: test_build_generic.py
by:   Gumyr
date: July 30th 2022

desc: Unit tests for the build123d build_generic module

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
from math import pi, sqrt
from build123d import *
from build123d import Builder, LocationList


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class _TestBuilder(Builder):
    @property
    def _obj(self):
        return self.line

    @property
    def _obj_name(self):
        return "test"

    def __init__(self, mode: Mode = Mode.ADD):
        self.test = "test"
        super().__init__(mode=mode)

    def _add_to_context(self):
        pass

    def _add_to_pending(self):
        pass

    @classmethod
    def _get_context(cls) -> "BuildLine":
        return cls._current.get(None)


class AddTests(unittest.TestCase):
    """Test adding objects"""

    def test_add_to_line(self):
        # Add Edge
        with BuildLine() as test:
            add(Edge.make_line((0, 0, 0), (1, 1, 1)))
        self.assertTupleAlmostEquals((test.wires()[0] @ 1).to_tuple(), (1, 1, 1), 5)
        # Add Wire
        with BuildLine() as wire:
            Polyline((0, 0, 0), (1, 1, 1), (2, 0, 0), (3, 1, 1))
        with BuildLine() as test:
            add(wire.wires()[0])
        self.assertEqual(len(test.line.edges()), 3)

    def test_add_to_sketch(self):
        with BuildSketch() as test:
            add(Face.make_rect(10, 10))
        self.assertAlmostEqual(test.sketch.area, 100, 5)

    def test_add_to_part(self):
        # Add Solid
        with BuildPart() as test:
            add(Solid.make_box(10, 10, 10))
        self.assertAlmostEqual(test.part.volume, 1000, 5)
        with BuildPart() as test:
            add(Solid.make_box(10, 10, 10), rotation=(0, 0, 45))
        self.assertAlmostEqual(test.part.volume, 1000, 5)
        self.assertTupleAlmostEquals(
            (
                test.part.edges()
                .group_by(Axis.Z)[-1]
                .group_by(Axis.X)[-1]
                .sort_by(Axis.Y)[0]
                % 1
            ).to_tuple(),
            (sqrt(2) / 2, sqrt(2) / 2, 0),
            5,
        )

        # Add Compound
        with BuildPart() as test:
            add(
                Compound(
                    [
                        Solid.make_box(10, 10, 10),
                        Solid.make_box(5, 5, 5, Plane((20, 20, 20))),
                    ]
                )
            )
        self.assertAlmostEqual(test.part.volume, 1125, 5)
        with BuildPart() as test:
            add(Compound([Edge.make_line((0, 0), (1, 1))]))
        self.assertEqual(len(test.pending_edges), 1)

        # Add Wire
        with BuildLine() as wire:
            Polyline((0, 0, 0), (1, 1, 1), (2, 0, 0), (3, 1, 1))
        with BuildPart() as test:
            add(wire.wires()[0])
        self.assertEqual(len(test.pending_edges), 3)

    def test_errors(self):
        with self.assertRaises(RuntimeError):
            add(Edge.make_line((0, 0, 0), (1, 1, 1)))

        with BuildPart() as test:
            with self.assertRaises(ValueError):
                add(Box(1, 1, 1), rotation=90)

    def test_unsupported_builder(self):
        with self.assertRaises(RuntimeError):
            with _TestBuilder():
                add(Edge.make_line((0, 0, 0), (1, 1, 1)))

    def test_local_global_locations(self):
        """Check that add is using a local location list"""
        with BuildSketch() as vertwalls:
            Rectangle(40, 90)

        with BuildPart() as mainp:
            with BuildSketch() as main_sk:
                Rectangle(50, 100)
            extrude(amount=10)
            topf = mainp.faces().sort_by(Axis.Z)[-1]
            with BuildSketch(topf):
                add(vertwalls.sketch)
            extrude(amount=15)

        self.assertEqual(len(mainp.solids()), 1)

    def test_multiple_faces(self):
        faces = [
            Face.make_rect(x, x).locate(Location(Vector(x, x))) for x in range(1, 3)
        ]
        with BuildPart(Plane.XY, Plane.YZ) as multiple:
            with Locations((1, 1), (-1, -1)) as locs:
                add(faces)
            self.assertEqual(len(multiple.pending_faces), 16)

    def test_add_builder(self):
        with BuildSketch() as s1:
            Rectangle(1, 1)

        with BuildSketch() as s2:
            with Locations((1, 0)):
                Rectangle(1, 1)
            add(s1)

        self.assertAlmostEqual(s2.sketch.area, 2, 5)


class BoundingBoxTests(unittest.TestCase):
    def test_boundingbox_to_sketch(self):
        """Test using bounding box to locate objects"""
        with BuildSketch() as mickey:
            Circle(10)
            with BuildSketch(mode=Mode.PRIVATE) as bb:
                bounding_box(mickey.faces(), mode=Mode.ADD)
                ears = (bb.vertices() > Axis.Y)[:-2]
            with Locations(*ears):
                Circle(7)
        self.assertAlmostEqual(mickey.sketch.area, 586.1521145312807, 5)
        """Test Vertices"""
        with BuildSketch() as test:
            Rectangle(10, 10)
            bounding_box(test.vertices())
        self.assertEqual(len(test.faces()), 1)

    def test_boundingbox_to_part(self):
        with BuildPart() as test:
            Sphere(1)
            bounding_box(test.solids(), mode=Mode.ADD)
        self.assertAlmostEqual(test.part.volume, 8, 5)
        with BuildPart() as test:
            Sphere(1)
            bounding_box(test.vertices())
        self.assertAlmostEqual(test.part.volume, (4 / 3) * pi, 5)

    def test_errors(self):
        with self.assertRaises(ValueError):
            with BuildLine():
                bounding_box()


class ChamferTests(unittest.TestCase):
    def test_part_chamfer(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            chamfer(test.edges(), length=1)
        self.assertLess(test.part.volume, 1000)

    def test_part_chamfer_asym_length(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            chamfer(test.edges().filter_by(Axis.Z), length=1, length2=sqrt(3))
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 0.5 * 10 * sqrt(3), 5)

    def test_part_chamfer_asym_angle(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            chamfer(test.edges().filter_by(Axis.Z), length=1, angle=60)
        self.assertAlmostEqual(test.part.volume, 1000 - 4 * 0.5 * 10 * sqrt(3), 5)

    def test_part_chamfer_asym_length_reference(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            face = test.faces().sort_by(Axis.Z)[-1]
            chamfer(face.edges()[0], length=1, length2=sqrt(3), reference=face)
        self.assertAlmostEqual(test.part.volume, 1000 - 1 * 0.5 * 10 * sqrt(3), 5)

    def test_part_chamfer_asym_angle_reference(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            face = test.faces().sort_by(Axis.Z)[-1]
            chamfer(face.edges()[0], length=1, angle=60, reference=face)
        self.assertAlmostEqual(test.part.volume, 1000 - 1 * 0.5 * 10 * sqrt(3), 5)

    def test_sketch_chamfer(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            chamfer(test.vertices(), length=1)
        self.assertAlmostEqual(test.sketch.area, 100 - 4 * 0.5, 5)

        with BuildSketch() as test:
            with Locations((-10, 0), (10, 0)):
                Rectangle(10, 10)
            chamfer(
                test.vertices().filter_by_position(Axis.X, minimum=0, maximum=20),
                length=1,
            )
        self.assertAlmostEqual(test.sketch.area, 200 - 4 * 0.5, 5)

    def test_sketch_chamfer_asym_length(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            chamfer(test.vertices(), length=1, length2=sqrt(3))
        self.assertAlmostEqual(test.sketch.area, 100 - 4 * 0.5 * sqrt(3), 5)

    def test_sketch_chamfer_asym_angle(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            chamfer(test.vertices(), length=1, angle=60)
        self.assertAlmostEqual(test.sketch.area, 100 - 4 * 0.5 * sqrt(3), 5)

    def test_sketch_chamfer_asym_angle_reference(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            edge = test.edges().sort_by(Axis.Y)[0]
            vertex = edge.vertices()[0]
            chamfer(vertex, length=1, angle=60, reference=edge)
        self.assertAlmostEqual(test.sketch.area, 100 - 0.5 * sqrt(3), 5)

    def test_sketch_chamfer_asym_length_reference(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            edge = test.edges().sort_by(Axis.Y)[0]
            vertex = edge.vertices()[0]
            chamfer(vertex, length=1, length2=sqrt(3), reference=edge)
        self.assertAlmostEqual(test.sketch.area, 100 - 0.5 * sqrt(3), 5)
        self.assertAlmostEqual(test.edges().sort_by(Axis.Y)[0].length, 9)

    def test_wire_chamfer(self):
        with BuildLine() as test:
            Polyline((0, 0), (10, 0), (10, 10))
            chamfer(objects=test.vertices(), length=1)

        self.assertAlmostEqual(test.wire().length, 9 + 9 + sqrt(2))

    def test_wire_chamfer_length2(self):
        with BuildLine() as test:
            Polyline((0, 0), (10, 0), (10, 10))
            chamfer(objects=test.vertices(), length=1, length2=2)

        self.assertAlmostEqual(test.wire().length, 9 + 8 + sqrt(1**1 + 2**2))

    def test_wire_chamfer_length2_edge(self):
        with BuildLine() as test:
            Polyline((0, 0), (10, 0), (10, 10))
            edge = test.edges().sort_by(Axis.Y)[0]
            chamfer(objects=test.vertices(), length=1, length2=2, reference=edge)

        self.assertAlmostEqual(test.edges().sort_by(Axis.Y)[0].length, 9)

    def test_errors(self):
        with self.assertRaises(TypeError):
            with BuildLine():
                chamfer(length=1)

        with self.assertRaises(ValueError):
            with BuildPart() as box:
                Box(1, 1, 1)
                chamfer(box.vertices(), length=1)

        with self.assertRaises(ValueError):
            with BuildSketch() as square:
                Rectangle(1, 1)
                chamfer(square.edges(), length=1)

        with self.assertRaises(ValueError):
            with BuildSketch() as square:
                Rectangle(10, 10)
                chamfer(square.edges(), length=1, length2=sqrt(3), angle=60)

        with self.assertRaises(ValueError):
            chamfer(None, length=1)

        with self.assertRaises(ValueError):
            with BuildPart() as test:
                Box(10, 10, 10)
                face = test.faces().sort_by(Axis.Z)[-1]
                chamfer(face.edges()[0], length=1, reference=face)

        with self.assertRaises(ValueError):
            with BuildLine() as test:
                Polyline((0, 0), (10, 0), (10, 10))
                chamfer(test.edges()[0], length=1)


class FilletTests(unittest.TestCase):
    def test_part_chamfer(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            fillet(test.edges(), radius=1)
        self.assertLess(test.part.volume, 1000)

    def test_sketch_chamfer(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            fillet(test.vertices(), radius=1)
        self.assertAlmostEqual(test.sketch.area, 100 - 4 + pi, 5)

        with BuildSketch() as test:
            with Locations((-10, 0), (10, 0)):
                Rectangle(10, 10)
            fillet(
                test.vertices().filter_by_position(Axis.X, minimum=0, maximum=20),
                radius=1,
            )
        self.assertAlmostEqual(test.sketch.area, 200 - 4 + pi, 5)

    def test_errors(self):
        with self.assertRaises(TypeError):
            with BuildLine():
                fillet(radius=1)

        with self.assertRaises(ValueError):
            with BuildPart() as box:
                Box(1, 1, 1)
                fillet(box.vertices(), radius=1)

        with self.assertRaises(ValueError):
            with BuildSketch() as square:
                Rectangle(1, 1)
                fillet(square.edges(), radius=1)


class HexArrayTests(unittest.TestCase):
    def test_hexarray_in_sketch(self):
        with BuildSketch() as test:
            Rectangle(70, 70)
            with HexLocations(7, 4, 3, align=(Align.CENTER, Align.CENTER)):
                Circle(5, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(test.sketch.area, 70**2 - 12 * 25 * pi, 5)

    def test_error(self):
        with self.assertRaises(ValueError):
            with BuildSketch():
                with HexLocations(20, 0, 3, align=(Align.CENTER, Align.CENTER)):
                    pass
            with BuildSketch():
                with HexLocations(20, 1, -3, align=(Align.CENTER, Align.CENTER)):
                    pass


class LocationsTests(unittest.TestCase):
    def test_push_locations(self):
        with BuildPart():
            with Locations(Location(Vector())):
                self.assertTupleAlmostEquals(
                    LocationList._get_context().locations[0].to_tuple()[0], (0, 0, 0), 5
                )

    def test_errors(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                with Locations(Edge.make_line((1, 0), (2, 0))):
                    pass


class MirrorTests(unittest.TestCase):
    def test_mirror_line(self):
        edge = Edge.make_line((1, 0, 0), (2, 0, 0))
        wire = Wire.make_circle(1, Plane((5, 0, 0)))
        with BuildLine() as test:
            mirror([edge, wire], Plane.YZ)
        self.assertEqual(
            len(test.edges().filter_by_position(Axis.X, minimum=0, maximum=10)), 0
        )
        self.assertEqual(
            len(test.edges().filter_by_position(Axis.X, minimum=-10, maximum=0)), 2
        )
        with BuildLine() as test:
            Line((1, 0), (2, 0))
            mirror(about=Plane.YZ)
        self.assertEqual(len(test.edges()), 2)

    def test_mirror_sketch(self):
        edge = Edge.make_line((1, 0), (2, 0))
        wire = Wire.make_circle(1, Plane((5, 0, 0)))
        face = Face.make_rect(2, 2, Plane((8, 0)))
        compound = Compound(
            [
                Face.make_rect(2, 2, Plane((8, 8))),
                Face.make_rect(2, 2, Plane((8, -8))),
            ]
        )
        with BuildSketch() as test:
            mirror([edge, wire, face, compound], Plane.YZ)
        self.assertEqual(
            len(test.pending_edges.filter_by_position(Axis.X, minimum=0, maximum=10)), 0
        )
        self.assertEqual(
            len(test.faces().filter_by_position(Axis.X, minimum=0, maximum=10)), 0
        )
        self.assertEqual(
            len(test.pending_edges.filter_by_position(Axis.X, minimum=-10, maximum=0)),
            2,
        )
        self.assertEqual(
            len(test.faces().filter_by_position(Axis.X, minimum=-10, maximum=0)), 3
        )

    def test_mirror_part(self):
        cone = Solid.make_cone(2, 1, 2, Plane((5, 4, 0)))
        with BuildPart() as test:
            mirror(cone, Plane.YZ)
        self.assertEqual(
            len(test.solids().filter_by_position(Axis.X, minimum=-10, maximum=0)), 1
        )

    def test_changing_object_type(self):
        """Using gp_GTrsf for the mirror operation may change the nature of the object"""
        ring_r, ring_t = 9, 2
        wheel_r, wheel_t = 10, 6

        with BuildPart() as p:
            with BuildSketch(Plane.XZ) as side:
                Trapezoid(wheel_r, wheel_t / 2, 90, 45, align=(Align.MIN, Align.MIN))
                with Locations((ring_r, ring_t / 2)):
                    Circle(
                        ring_t / 2,
                        align=(Align.CENTER, Align.CENTER),
                        mode=Mode.SUBTRACT,
                    )
                with Locations((wheel_r, ring_t / 2)):
                    Rectangle(
                        2, 2, align=(Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT
                    )
            revolve(axis=Axis.Z)
            mirror(about=Plane.XY)
            construction_face = p.faces().sort_by(Axis.Z)[0]
            self.assertEqual(construction_face.geom_type, GeomType.PLANE)


class OffsetTests(unittest.TestCase):
    def test_single_line_offset(self):
        with BuildLine() as test:
            Line((0, 0), (1, 0))
            offset(amount=1)
        self.assertAlmostEqual(test.wires()[0].length, 2 + 2 * pi, 5)

    def test_line_offset(self):
        with BuildSketch() as test:
            with BuildLine():
                l = Line((0, 0), (1, 0))
                Line(l @ 1, (1, 1))
                offset(amount=1)
            make_face()
        self.assertAlmostEqual(test.sketch.area, pi * 1.25 + 3, 5)

    def test_line_offset(self):
        with BuildSketch() as test:
            with BuildLine() as line:
                l = Line((0, 0), (1, 0))
                Line(l @ 1, (1, 1))
                offset(line.line.edges(), 1)
            make_face()
        self.assertAlmostEqual(test.sketch.area, pi * 1.25 + 3, 5)

    def test_face_offset(self):
        with BuildSketch() as test:
            Rectangle(1, 1)
            offset(amount=1, kind=Kind.INTERSECTION)
        self.assertAlmostEqual(test.sketch.area, 9, 5)

    def test_box_offset(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            offset(amount=-1, kind=Kind.INTERSECTION, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(test.part.volume, 10**3 - 8**3, 5)

    def test_box_offset_with_opening(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            offset(
                amount=-1,
                openings=test.faces() >> Axis.Z,
                kind=Kind.INTERSECTION,
            )
        self.assertAlmostEqual(test.part.volume, 10**3 - 8**2 * 9, 5)

        with BuildPart() as test:
            Box(10, 10, 10)
            offset(
                amount=-1,
                openings=test.faces().sort_by(Axis.Z)[-1],
                kind=Kind.INTERSECTION,
            )
        self.assertAlmostEqual(test.part.volume, 10**3 - 8**2 * 9, 5)

    def test_box_offset_combinations(self):
        with BuildPart() as o1:
            Box(4, 4, 4)
            offset(amount=-1, kind=Kind.INTERSECTION, mode=Mode.REPLACE)
            self.assertAlmostEqual(o1.part.volume, 2**3, 5)

        with BuildPart() as o2:
            Box(4, 4, 4)
            offset(amount=1, kind=Kind.INTERSECTION, mode=Mode.REPLACE)
            self.assertAlmostEqual(o2.part.volume, 6**3, 5)

        with BuildPart() as o3:
            Box(4, 4, 4)
            offset(amount=-1, kind=Kind.INTERSECTION, mode=Mode.SUBTRACT)
            self.assertAlmostEqual(o3.part.volume, 4**3 - 2**3, 5)

        with BuildPart() as o4:
            Box(4, 4, 4)
            offset(amount=1, kind=Kind.INTERSECTION, mode=Mode.ADD)
            self.assertAlmostEqual(o4.part.volume, 6**3, 5)

        with BuildPart() as o5:
            Box(4, 4, 4)
            offset(amount=-1, kind=Kind.INTERSECTION, mode=Mode.ADD)
            self.assertAlmostEqual(o5.part.volume, 4**3, 5)

        with BuildPart() as o6:
            Box(4, 4, 4)
            offset(amount=1, kind=Kind.INTERSECTION, mode=Mode.SUBTRACT)
            self.assertAlmostEqual(o6.part.volume, 0, 5)

    def test_offset_algebra_wire(self):
        pts = [
            (11.421, 10.15),
            (11.421, 84.582),
            (19.213, 118.618),
            (17.543, 127.548),
            (-10.675, 127.548),
            (-10.675, 118.618),
            (-19.313, 118.618),
        ]
        line = FilletPolyline(*pts, radius=3.177)
        self.assertEqual(len(line.edges()), 11)
        o_line = offset(line, amount=3.177)
        self.assertEqual(len(o_line.edges()), 19)

    def test_offset_face_with_inner_wire(self):
        # offset amount causes the inner wire to have zero length
        b = Rectangle(1, 1)
        b -= RegularPolygon(0.25, 3)
        b = offset(b, amount=0.125)
        self.assertAlmostEqual(b.area, 1**2 + 2 * 0.125 * 2 + pi * 0.125**2, 5)
        self.assertEqual(len(b.face().inner_wires()), 0)

    def test_offset_face_with_min_length(self):
        c = Circle(0.5)
        c = offset(c, amount=0.125, min_edge_length=0.1)
        self.assertAlmostEqual(c.area, pi * (0.5 + 0.125) ** 2, 5)

    def test_offset_face_with_min_length_and_inner(self):
        # offset amount causes the inner wire to have zero length
        c = Circle(0.5)
        c -= RegularPolygon(0.25, 3)
        c = offset(c, amount=0.125, min_edge_length=0.1)
        self.assertAlmostEqual(c.area, pi * (0.5 + 0.125) ** 2, 5)
        self.assertEqual(len(c.face().inner_wires()), 0)

    def test_offset_bad_type(self):
        with self.assertRaises(TypeError):
            offset(Vertex(), amount=1)

    def test_offset_failure(self):
        with BuildPart() as cup:
            with BuildSketch():
                Circle(35)
            extrude(amount=50, taper=-3)
            topf = cup.faces().sort_by(Axis.Z)[-1]
            with self.assertRaises(RuntimeError):
                offset(amount=-2, openings=topf)

    def test_flipped_faces(self):
        box = Box(10, 10, 10)
        original_faces = box.faces()
        offset_faces = [offset(face, amount=-3).face() for face in original_faces]

        for original_face, offset_face in zip(original_faces, offset_faces):
            self.assertTupleAlmostEquals(
                tuple(original_face.normal_at()), tuple(offset_face.normal_at()), 3
            )


class PolarLocationsTests(unittest.TestCase):
    def test_errors(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                with PolarLocations(10, 0, 360, 0):
                    pass


class ProjectionTests(unittest.TestCase):
    def test_project_to_sketch1(self):
        with BuildPart() as loaf_s:
            with BuildSketch(Plane.YZ) as profile:
                Rectangle(10, 15)
                fillet(profile.vertices().group_by(Axis.Y)[-1], 2)
            extrude(amount=15, both=True)
            ref_s_pnts = loaf_s.vertices().group_by(Axis.X)[-1].group_by(Axis.Z)[0]
            origin = (Vector(ref_s_pnts[0]) + Vector(ref_s_pnts[1])) / 2
            x_dir = ref_s_pnts.sort_by(Axis.Y)[-1] - ref_s_pnts.sort_by(Axis.Y)[0]
            workplane_s = project_workplane(origin, x_dir, (1, 0, 1), 30)
            with BuildSketch(workplane_s) as projection_s:
                project(loaf_s.part.faces().sort_by(Axis.X)[-1])

        self.assertAlmostEqual(projection_s.sketch.area, 104.85204601097809, 5)
        self.assertEqual(len(projection_s.edges()), 6)

    def test_project_to_sketch2(self):
        with BuildPart() as test2:
            Box(4, 4, 1)
            with BuildSketch(Plane.XY.offset(0.1)) as c:
                Rectangle(1, 1)
            project()
            extrude(amount=1)
        self.assertAlmostEqual(test2.part.volume, 4 * 4 * 1 + 1 * 1 * 1, 5)

    def test_project_point(self):
        pnt: Vector = project(Vector(1, 2, 3), Plane.XY)[0]
        self.assertTupleAlmostEquals(pnt.to_tuple(), (1, 2, 0), 5)
        pnt: Vector = project(Vertex(1, 2, 3), Plane.XZ)[0]
        self.assertTupleAlmostEquals(pnt.to_tuple(), (1, 3, 0), 5)
        with BuildSketch(Plane.YZ) as s1:
            pnt = project(Vertex(1, 2, 3), mode=Mode.PRIVATE)[0]
            self.assertTupleAlmostEquals(pnt.to_tuple(), (2, 3, 0), 5)

    def test_multiple_results(self):
        with BuildLine() as l1:
            project(
                [
                    Edge.make_line((0, 1, 2), (3, 4, 5)),
                    Edge.make_line((-1, 2, 3), (-4, 5, -6)),
                ]
            )
            self.assertEqual(len(l1.edges()), 2)

    def test_project_errors(self):
        with self.assertRaises(ValueError):
            project(Vertex(1, 2, 3))

        with self.assertRaises(ValueError):
            project(workplane=Plane.XY, target=Box(1, 1, 1))

        with self.assertRaises(ValueError):
            project(
                Box(1, 1, 1).vertices().group_by(Axis.Z),
                workplane=Plane.XY,
                target=Box(1, 1, 1),
            )
        with self.assertRaises(ValueError):
            project(
                Box(1, 1, 1).vertices().group_by(Axis.Z),
                target=Box(1, 1, 1),
            )

        with self.assertRaises(ValueError):
            with BuildPart():
                pnt = project(Vertex(1, 2, 3))[0]

        with self.assertRaises(ValueError):
            with BuildSketch(Plane.YZ):
                pnt = project(Vertex(1, 2, 3))[0]

        with self.assertRaises(ValueError):
            with BuildLine():
                pnt = project(Vertex(1, 2, 3))[0]


class RectangularArrayTests(unittest.TestCase):
    def test_errors(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                with GridLocations(5, 5, 0, 1):
                    pass


class ScaleTests(unittest.TestCase):
    def test_line(self):
        with BuildLine() as test:
            Line((0, 0), (1, 0))
            scale(by=2, mode=Mode.REPLACE)
        self.assertAlmostEqual(test.edges()[0].length, 2.0, 5)

    def test_sketch(self):
        with BuildSketch() as test:
            Rectangle(1, 1)
            scale(by=2, mode=Mode.REPLACE)
        self.assertAlmostEqual(test.sketch.area, 4.0, 5)

    def test_part(self):
        with BuildPart() as test:
            Box(1, 1, 1)
            scale(by=(2, 2, 2), mode=Mode.REPLACE)
        self.assertAlmostEqual(test.part.volume, 8.0, 5)

    def test_external_object(self):
        line = Edge.make_line((0, 0), (1, 0))
        with BuildLine() as test:
            scale(line, 2)
        self.assertAlmostEqual(test.edges()[0].length, 2.0, 5)

    def test_error_checking(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                Box(1, 1, 1)
                scale(by="a")


class TestSweep(unittest.TestCase):
    def test_single_section(self):
        with BuildPart() as test:
            with BuildLine():
                Line((0, 0, 0), (0, 0, 10))
            with BuildSketch():
                Rectangle(2, 2)
            sweep()
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
                with BuildSketch(
                    Plane(
                        origin=handle_path @ (i / segment_count),
                        z_dir=handle_path % (i / segment_count),
                    )
                ) as section:
                    if i % segment_count == 0:
                        Circle(1)
                    else:
                        Rectangle(1, 2)
                        fillet(section.vertices(), radius=0.2)
            # Create the handle by sweeping along the path
            sweep(multisection=True)
        self.assertAlmostEqual(handle.part.volume, 54.11246334691092, 5)

    def test_passed_parameters(self):
        with BuildLine() as path:
            Line((0, 0, 0), (0, 0, 10))
        with BuildSketch() as section:
            Rectangle(2, 2)
        with BuildPart() as test:
            sweep(section.faces(), path=path.wires()[0])
        self.assertAlmostEqual(test.part.volume, 40, 5)

    def test_binormal(self):
        with BuildPart() as sweep_binormal:
            with BuildLine() as path:
                Spline((0, 0, 0), (-12, 8, 10), tangents=[(0, 0, 1), (-1, 0, 0)])
            with BuildLine(mode=Mode.PRIVATE) as binormal:
                Line((-5, 5), (-8, 10))
            with BuildSketch() as section:
                Rectangle(4, 6)
            sweep(binormal=binormal.edges()[0])

        end_face: Face = (
            sweep_binormal.faces().filter_by(GeomType.PLANE).sort_by(Axis.X)[0]
        )
        face_binormal_axis = Axis(
            end_face.center(), binormal.edges()[0] @ 1 - end_face.center()
        )
        face_normal_axis = Axis(end_face.center(), end_face.normal_at())
        self.assertTrue(face_normal_axis.is_normal(face_binormal_axis))

    def test_sweep_edge(self):
        arc = PolarLine((1, 0), 2, 135)
        arc_path = PolarLine(arc @ 1, 10, 45)
        swept = sweep(sections=arc, path=arc_path)
        self.assertTrue(isinstance(swept, Sketch))
        self.assertAlmostEqual(swept.area, 2 * 10, 5)

    def test_sweep_edge_along_wire(self):
        spine = Polyline((0, 0), (1, 10), (10, 10))
        with BuildSketch() as bs:
            sect = spine.wire().perpendicular_line(2, 0)
            sweep(sect, spine, transition=Transition.RIGHT)
        self.assertGreater(bs.sketch.area, 38)

    def test_no_path(self):
        with self.assertRaises(ValueError):
            sweep(PolarLine((1, 0), 2, 135))

    def test_no_sections(self):
        with self.assertRaises(ValueError):
            sweep(path=PolarLine((1, 0), 2, 135))

    def test_path_from_edges(self):
        d = 8.5
        h = 4.65
        lip = 0.5

        with BuildPart() as p:
            with BuildSketch() as sk:
                Rectangle(d * 3, d)
                fillet(sk.vertices().group_by(Axis.X)[0], d / 2)
            extrude(amount=4.65)
            topedgs = (
                p.part.edges().group_by(Axis.Z)[2].sort_by(Axis.X)[0:3].sort_by(Axis.Y)
            )
            with BuildSketch(Plane.ZY.offset(-d * 3 / 2)) as sk2:
                with Locations((h, -d / 2)):
                    Rectangle(2 * lip, 2 * lip, align=(Align.CENTER, Align.CENTER))
            sweep(sections=sk2.sketch, path=topedgs, mode=Mode.SUBTRACT)

        self.assertTrue(p.part.is_valid())

    def test_path_error(self):
        e1 = Edge.make_line((0, 0), (1, 0))
        e2 = Edge.make_line((2, 0), (3, 0))
        with self.assertRaises(ValueError):
            sweep(sections=Edge.make_line((0, 0), (0, 1)), path=ShapeList([e1, e2]))


if __name__ == "__main__":
    unittest.main()
