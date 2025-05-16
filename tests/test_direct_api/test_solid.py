"""
build123d imports

name: test_solid.py
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

import math
import unittest

from build123d.build_enums import GeomType, Kind, Until
from build123d.geometry import (
    Axis,
    BoundBox,
    Location,
    OrientedBoundBox,
    Plane,
    Pos,
    Vector,
)
from build123d.objects_curve import Spline
from build123d.objects_sketch import Circle, Rectangle
from build123d.topology import Compound, Edge, Face, Shell, Solid, Vertex, Wire


class TestSolid(unittest.TestCase):
    def test_make_solid(self):
        box_faces = Solid.make_box(1, 1, 1).faces()
        box_shell = Shell(box_faces)
        box = Solid(box_shell)
        self.assertAlmostEqual(box.area, 6, 5)
        self.assertAlmostEqual(box.volume, 1, 5)
        self.assertTrue(box.is_valid())

    def test_extrude(self):
        v = Edge.extrude(Vertex(1, 1, 1), (0, 0, 1))
        self.assertAlmostEqual(v.length, 1, 5)

        e = Face.extrude(Edge.make_line((2, 1), (2, 0)), (0, 0, 1))
        self.assertAlmostEqual(e.area, 1, 5)

        w = Shell.extrude(
            Wire([Edge.make_line((1, 1), (0, 2)), Edge.make_line((1, 1), (1, 0))]),
            (0, 0, 1),
        )
        self.assertAlmostEqual(w.area, 1 + math.sqrt(2), 5)

        f = Solid.extrude(Face.make_rect(1, 1), (0, 0, 1))
        self.assertAlmostEqual(f.volume, 1, 5)

        s = Compound.extrude(
            Shell(
                Solid.make_box(1, 1, 1)
                .locate(Location((-2, 1, 0)))
                .faces()
                .sort_by(Axis((0, 0, 0), (1, 1, 1)))[-2:]
            ),
            (0.1, 0.1, 0.1),
        )
        self.assertAlmostEqual(s.volume, 0.2, 5)

        with self.assertRaises(ValueError):
            Solid.extrude(Solid.make_box(1, 1, 1), (0, 0, 1))

    def test_extrude_taper(self):
        a = 1
        rect = Face.make_rect(a, a)
        flipped = -rect
        for direction in [Vector(0, 0, 2), Vector(0, 0, -2)]:
            for taper in [10, -10]:
                offset_amt = -direction.length * math.tan(math.radians(taper))
                for face in [rect, flipped]:
                    with self.subTest(
                        f"{direction=}, {taper=}, flipped={face==flipped}"
                    ):
                        taper_solid = Solid.extrude_taper(face, direction, taper)
                        # V = 1/3 × h × (a² + b² + ab)
                        h = Vector(direction).length
                        b = a + 2 * offset_amt
                        v = h * (a**2 + b**2 + a * b) / 3
                        self.assertAlmostEqual(taper_solid.volume, v, 5)
                        bbox = taper_solid.bounding_box()
                        size = max(1, b) / 2
                        if direction.Z > 0:
                            self.assertAlmostEqual(bbox.min, (-size, -size, 0), 1)
                            self.assertAlmostEqual(bbox.max, (size, size, h), 1)
                        else:
                            self.assertAlmostEqual(bbox.min, (-size, -size, -h), 1)
                            self.assertAlmostEqual(bbox.max, (size, size, 0), 1)

    def test_extrude_taper_with_hole(self):
        rect_hole = Face.make_rect(1, 1).make_holes([Wire.make_circle(0.25)])
        direction = Vector(0, 0, 0.5)
        taper = 10
        taper_solid = Solid.extrude_taper(rect_hole, direction, taper)
        offset_amt = -direction.length * math.tan(math.radians(taper))
        hole = taper_solid.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
        self.assertAlmostEqual(hole.radius, 0.25 - offset_amt, 5)

    def test_extrude_taper_with_hole_flipped(self):
        rect_hole = Face.make_rect(1, 1).make_holes([Wire.make_circle(0.25)])
        direction = Vector(0, 0, 1)
        taper = 10
        taper_solid_t = Solid.extrude_taper(rect_hole, direction, taper, True)
        taper_solid_f = Solid.extrude_taper(rect_hole, direction, taper, False)
        hole_t = taper_solid_t.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
        hole_f = taper_solid_f.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
        self.assertGreater(hole_t.radius, hole_f.radius)

    def test_extrude_taper_oblique(self):
        rect = Face.make_rect(2, 1)
        rect_hole = rect.make_holes([Wire.make_circle(0.25)])
        o_rect_hole = rect_hole.moved(Location(Plane.isometric))
        taper0 = Solid.extrude_taper(rect_hole, (0, 0, 1), 5)
        taper1 = Solid.extrude_taper(o_rect_hole, o_rect_hole.normal_at(), 5)
        self.assertAlmostEqual(taper0.volume, taper1.volume, 5)

    def test_extrude_linear_with_rotation(self):
        # Face
        base = Face.make_rect(1, 1)
        twist = Solid.extrude_linear_with_rotation(
            base, center=(0, 0, 0), normal=(0, 0, 1), angle=45
        )
        self.assertAlmostEqual(twist.volume, 1, 5)
        top = twist.faces().sort_by(Axis.Z)[-1].rotate(Axis.Z, 45)
        bottom = twist.faces().sort_by(Axis.Z)[0]
        self.assertAlmostEqual(top.translate((0, 0, -1)).intersect(bottom).area, 1, 5)
        # Wire
        base = Wire.make_rect(1, 1)
        twist = Solid.extrude_linear_with_rotation(
            base, center=(0, 0, 0), normal=(0, 0, 1), angle=45
        )
        self.assertAlmostEqual(twist.volume, 1, 5)
        top = twist.faces().sort_by(Axis.Z)[-1].rotate(Axis.Z, 45)
        bottom = twist.faces().sort_by(Axis.Z)[0]
        self.assertAlmostEqual(top.translate((0, 0, -1)).intersect(bottom).area, 1, 5)

    def test_make_loft(self):
        loft = Solid.make_loft(
            [Wire.make_rect(2, 2), Wire.make_circle(1, Plane((0, 0, 1)))]
        )
        self.assertAlmostEqual(loft.volume, (4 + math.pi) / 2, 1)

        with self.assertRaises(ValueError):
            Solid.make_loft([Wire.make_rect(1, 1)])

    def test_make_loft_with_vertices(self):
        loft = Solid.make_loft(
            [Vertex(0, 0, -1), Wire.make_rect(1, 1.5), Vertex(0, 0, 1)], True
        )
        self.assertAlmostEqual(loft.volume, 1, 5)

        with self.assertRaises(ValueError):
            Solid.make_loft(
                [Wire.make_rect(1, 1), Vertex(0, 0, 1), Wire.make_rect(1, 1)]
            )

        with self.assertRaises(ValueError):
            Solid.make_loft([Vertex(0, 0, 1), Vertex(0, 0, 2)])

        with self.assertRaises(ValueError):
            Solid.make_loft(
                [
                    Vertex(0, 0, 1),
                    Wire.make_rect(1, 1),
                    Vertex(0, 0, 2),
                    Vertex(0, 0, 3),
                ]
            )

    def test_extrude_until(self):
        square = Face.make_rect(1, 1)
        box = Solid.make_box(4, 4, 1, Plane((-2, -2, 3)))
        extrusion = Solid.extrude_until(square, box, (0, 0, 1), Until.LAST)
        self.assertAlmostEqual(extrusion.volume, 4, 5)

        square = Face.make_rect(1, 1)
        box = Solid.make_box(4, 4, 1, Plane((-2, -2, -3)))
        extrusion = Solid.extrude_until(square, box, (0, 0, 1), Until.PREVIOUS)
        self.assertAlmostEqual(extrusion.volume, 2, 5)

    def test_sweep(self):
        path = Edge.make_spline([(0, 0), (3, 5), (7, -2)])
        section = Wire.make_circle(1, Plane(path @ 0, z_dir=path % 0))
        area = Face(section).area
        swept = Solid.sweep(section, path)
        self.assertAlmostEqual(swept.volume, path.length * area, 0)

    def test_hollow_sweep(self):
        path = Edge.make_line((0, 0, 0), (0, 0, 5))
        section = (Rectangle(1, 1) - Rectangle(0.1, 0.1)).faces()[0]
        swept = Solid.sweep(section, path)
        self.assertAlmostEqual(swept.volume, 5 * (1 - 0.1**2), 5)

    def test_sweep_multi(self):
        f0 = Face.make_rect(1, 1)
        f1 = Pos(X=10) * Circle(1).face()
        path = Spline((0, 0), (10, 0), tangents=((0, 0, 1), (0, 0, -1)))
        binormal = Edge.make_line((0, 1), (10, 1))
        swept = Solid.sweep_multi([f0, f1], path, is_frenet=True, binormal=binormal)
        self.assertAlmostEqual(swept.volume, 23.78, 2)

        path = Spline((0, 0), (10, 0), tangents=((0, 0, 1), (1, 0, 0)))
        swept = Solid.sweep_multi(
            [f0, f1], path, is_frenet=True, binormal=Vector(5, 0, 1)
        )
        self.assertAlmostEqual(swept.volume, 20.75, 2)

    def test_constructor(self):
        with self.assertRaises(TypeError):
            Solid(foo="bar")

    def test_offset_3d(self):
        with self.assertRaises(ValueError):
            Solid.make_box(1, 1, 1).offset_3d(None, 0.1, kind=Kind.TANGENT)

    def test_revolve(self):
        r = Solid.revolve(
            Face.make_rect(1, 1, Plane((10, 0, 0))).wire(), 180, axis=Axis.Y
        )
        self.assertEqual(len(r.faces()), 6)

    def test_from_bounding_box(self):
        cyl = Solid.make_cylinder(0.001, 10).locate(Location(Plane.isometric))
        cyl2 = Solid.make_cylinder(1, 10).locate(Location(Plane.isometric))

        rbb = Solid.from_bounding_box(cyl.bounding_box())
        obb = Solid.from_bounding_box(cyl.oriented_bounding_box())
        obb2 = Solid.from_bounding_box(cyl2.oriented_bounding_box())

        self.assertAlmostEqual(rbb.volume, (10**3) * (3**0.5) / 9, 0)
        self.assertTrue(rbb.volume > obb.volume)
        self.assertAlmostEqual(obb2.volume, 40, 4)


if __name__ == "__main__":
    unittest.main()
