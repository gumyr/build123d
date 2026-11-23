"""
build123d tests

name: test_uv_offset.py
by:   Gumyr
date: November 23, 2026

desc:
    Tests of Face.offset_2d: a face grown or shrunk within its own surface.

license:

    Copyright 2026 Gumyr

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

import math
import unittest

from build123d.build_enums import Align, GeomType, Kind
from build123d.geometry import Axis, Plane, Pos, Rot
from build123d.objects_curve import Polyline
from build123d.objects_part import Box, Cone, Cylinder, Sphere, Torus
from build123d.objects_sketch import Circle, Ellipse, Rectangle, RectangleRounded
from build123d.operations_generic import offset
from build123d.topology import Edge, Face, Solid, UVFrame, Vertex, Wire

from OCP.BRep import BRep_Tool


def flat_area(planar: Face, amount: float, kind: Kind = Kind.ARC) -> float:
    """The area the planar offset operation gives, the reference for a
    surface that unrolls without distortion"""
    return sum(face.area for face in offset(planar, amount, kind=kind).faces())


def seam_edges(face: Face) -> int:
    """How many of a face's edges are seam edges"""
    return sum(
        BRep_Tool.IsClosed_s(edge.wrapped, face.wrapped) for edge in face.edges()
    )


def dumbbell() -> Face:
    """Two discs joined by a bar too thin to survive a shrink of 0.4"""
    return (
        Pos(-3, 0) * Circle(1.5) + Rectangle(6, 0.6) + Pos(3, 0) * Circle(1.5)
    ).face()


class TestPlaneOffset2d(unittest.TestCase):
    def test_grows_and_shrinks_with_each_kind(self):
        rect = Rectangle(6, 3).face()
        (rounded,) = rect.offset_2d(0.5)
        self.assertAlmostEqual(rounded.area, 18 + 9 + math.pi * 0.25, 6)
        for kind in (Kind.INTERSECTION, Kind.TANGENT):
            with self.subTest(kind=kind):
                (square,) = rect.offset_2d(0.5, kind)
                self.assertAlmostEqual(square.area, 7 * 4, 6)
        (shrunk,) = rect.offset_2d(-0.5)
        self.assertAlmostEqual(shrunk.area, 5 * 2, 6)
        self.assertEqual(rect.offset_2d(0), [rect])

    def test_agrees_with_the_offset_operation(self):
        holed = (Rectangle(8, 5) - Circle(1)).face()
        for amount in (0.4, -0.3):
            for kind in (Kind.ARC, Kind.INTERSECTION):
                with self.subTest(amount=amount, kind=kind):
                    (result,) = holed.offset_2d(amount, kind)
                    self.assertTrue(result.is_valid)
                    self.assertAlmostEqual(
                        result.area, flat_area(holed, amount, kind), 6
                    )

    def test_stays_in_its_plane_facing_the_same_way(self):
        """Wherever the plane is, and whichever way the face faces"""
        lid = Plane.XZ.offset(3) * Rot(Z=30) * Rectangle(6, 3).face()
        underside = Box(6, 3, 2).faces().sort_by()[0]  # its normal is -Z
        for face in (lid, underside):
            (grown,) = face.offset_2d(0.5, Kind.INTERSECTION)
            self.assertAlmostEqual(grown.area, 7 * 4, 6)
            self.assertAlmostEqual((grown.normal_at() - face.normal_at()).length, 0, 6)
            self.assertAlmostEqual((grown.center() - face.center()).length, 0, 6)

    def test_parts_closes_holes_and_vanishes(self):
        parts = dumbbell().offset_2d(-0.4)
        self.assertEqual(len(parts), 2)  # the planar offset operation fails here
        self.assertAlmostEqual(parts[0].area, parts[1].area, 5)
        holed = (Rectangle(8, 5) - Circle(1)).face()
        (closed,) = holed.offset_2d(1.2)
        self.assertEqual(len(closed.inner_wires()), 0)
        # a hole grown through the sides of what is left cuts it in two
        self.assertEqual(len(holed.offset_2d(-1.0)), 2)
        with self.assertRaisesRegex(ValueError, "nothing is left"):
            holed.offset_2d(-3)
        with self.assertRaisesRegex(ValueError, "nothing is left"):
            Circle(2).face().offset_2d(-2.5)

    def test_an_outline_that_closes_on_itself(self):
        """A C grown until its ends meet is a ring, with the gap in its middle
        left open; the kernel loses that gap when the corners are not arcs,
        which is refused rather than passed on as a disc"""

        def on_circle(radius: float, degrees: float) -> tuple[float, float]:
            angle = math.radians(degrees)
            return (radius * math.cos(angle), radius * math.sin(angle))

        letter_c = Face(
            Wire(
                [
                    Edge.make_circle(5, start_angle=10, end_angle=350),
                    Edge.make_line(on_circle(5, 350), on_circle(3, 350)),
                    Edge.make_circle(3, start_angle=10, end_angle=350),
                    Edge.make_line(on_circle(3, 10), on_circle(5, 10)),
                ]
            )
        )
        (still_open,) = letter_c.offset_2d(0.2)
        self.assertEqual(len(still_open.inner_wires()), 0)
        (ring,) = letter_c.offset_2d(0.6)
        self.assertEqual(len(ring.inner_wires()), 1)
        whole_ring = math.pi * (5.6**2 - 2.4**2)
        self.assertLess(ring.area, whole_ring)  # a notch where the ends met
        self.assertGreater(ring.area, whole_ring - 1.5)
        with self.assertRaisesRegex(RuntimeError, "loses the gap"):
            letter_c.offset_2d(0.6, Kind.INTERSECTION)

    def test_refuses_an_empty_face(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            Face().offset_2d(1)


class TestCylinderOffset2d(unittest.TestCase):
    """A cylinder unrolls without distortion, so a face on one offsets as its
    flat pattern does"""

    def setUp(self):
        self.solid = Cylinder(5, 10)
        self.surface = self.solid.faces().filter_by(GeomType.CYLINDER)[0]
        self.turn = 10 * math.pi
        self.places = {
            "clear of the seam": self.surface.location_at(0.25, 0.5),
            "across the seam": self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0)),
        }

    def assert_on_the_surface(self, face: Face):
        """Valid, on the cylinder, and facing as the cylinder does"""
        self.assertTrue(face.is_valid)
        middle = face.position_at(0.5, 0.5)
        self.assertAlmostEqual(math.hypot(middle.X, middle.Y), 5, 6)
        for vertex in face.vertices():
            self.assertAlmostEqual(math.hypot(vertex.X, vertex.Y), 5, 6)
        normal = face.normal_at(middle)
        self.assertAlmostEqual((normal - self.surface.normal_at(middle)).length, 0, 6)

    def test_a_patch_offsets_as_its_flat_pattern(self):
        patterns = {
            "plain": Rectangle(6, 3).face(),
            "holed": (Rectangle(8, 5) - Circle(1)).face(),
            "cross": (Rectangle(6, 1) + Rectangle(1, 6)).face(),
        }
        for place, location in self.places.items():
            for name, pattern in patterns.items():
                patch = self.surface.wrap(pattern, location)
                for amount in (0.4, -0.3):
                    for kind in (Kind.ARC, Kind.INTERSECTION):
                        with self.subTest(
                            place=place, pattern=name, amount=amount, kind=kind
                        ):
                            (result,) = patch.offset_2d(amount, kind)
                            self.assert_on_the_surface(result)
                            self.assertEqual(seam_edges(result), 0)
                            self.assertAlmostEqual(
                                result.area, flat_area(pattern, amount, kind), 5
                            )

    def test_parts_and_closes_holes(self):
        for place, location in self.places.items():
            with self.subTest(place=place):
                parts = self.surface.wrap(dumbbell(), location).offset_2d(-0.4)
                self.assertEqual(len(parts), 2)
                for part in parts:
                    self.assert_on_the_surface(part)
                holed = self.surface.wrap(
                    (Rectangle(8, 5) - Circle(1)).face(), location
                )
                (closed,) = holed.offset_2d(1.2)
                self.assertEqual(len(closed.inner_wires()), 0)
                with self.assertRaisesRegex(ValueError, "nothing is left"):
                    holed.offset_2d(-3)

    def test_all_the_way_round_stays_so(self):
        """The seam of a face that goes round the cylinder is not part of its
        boundary: only its rims move, and it comes back with a seam edge"""
        for amount in (-1, 1):  # grown, it passes the ends of the solid
            with self.subTest(face="the cylinder's own", amount=amount):
                (result,) = self.surface.offset_2d(amount)
                self.assertTrue(result.is_valid)
                self.assertEqual(seam_edges(result), 1)
                self.assertAlmostEqual(result.area, self.turn * (10 + 2 * amount), 5)
        # a band written round the cylinder, its sides on the seam or away
        # from it, with a hole in the middle and one where its sides meet
        notched = (
            Rectangle(self.turn, 4)
            - Pos(self.turn / 2, 0) * Circle(1)
            - Pos(-self.turn / 2, 0) * Circle(1)
            - Circle(0.8)
        ).face()
        for where in (0.5, 0.2):
            frame = self.surface.uv_frame(
                self.surface.location_at(where, 0.5, x_dir=(1, 0, 0))
            )
            (band,) = frame.write_face(notched)
            for amount in (-0.3, 0.3):
                with self.subTest(face="a written band", where=where, amount=amount):
                    (result,) = band.offset_2d(amount)
                    self.assert_on_the_surface(result)
                    self.assertGreaterEqual(seam_edges(result), 1)
                    self.assertAlmostEqual(
                        result.area,
                        self.turn * (4 + 2 * amount)
                        - math.pi * ((1 - amount) ** 2 + (0.8 - amount) ** 2),
                        5,
                    )

    def test_grown_until_it_meets_itself(self):
        """A band that stops 2 short of going round closes when it is grown by
        more than 1, and is then one face all the way round"""
        band = self.surface.wrap(
            Rectangle(self.turn - 2, 3).face(), self.places["clear of the seam"]
        )
        (still_open,) = band.offset_2d(0.9, Kind.INTERSECTION)
        self.assertEqual(seam_edges(still_open), 0)
        self.assertAlmostEqual(still_open.area, (self.turn - 0.2) * 4.8, 5)
        (closed,) = band.offset_2d(1.5, Kind.INTERSECTION)
        self.assert_on_the_surface(closed)
        self.assertEqual(seam_edges(closed), 1)
        self.assertAlmostEqual(closed.area, self.turn * 6, 5)
        # rounded corners leave a notch in each rim where the ends meet
        (notched,) = band.offset_2d(1.5)
        self.assertEqual(seam_edges(notched), 1)
        self.assertLess(notched.area, self.turn * 6)
        self.assertGreater(notched.area, self.turn * 6 - 1)

    def test_walls_and_moved_cylinders(self):
        """The wall of a hole faces the other way, and a face keeps its
        place wherever its solid has been moved to"""
        tube = Pos(3, -2, 4) * Rot(20, 30, 40) * (Cylinder(5, 10) - Cylinder(3, 10))
        for wall in tube.faces().filter_by(GeomType.CYLINDER):
            with self.subTest(radius=wall.radius):
                patch = wall.wrap(Rectangle(6, 3).face(), wall.location_at(0.3, 0.5))
                (grown,) = patch.offset_2d(0.5)
                self.assertTrue(grown.is_valid)
                self.assertAlmostEqual(grown.area, 18 + 9 + math.pi * 0.25, 5)
                middle = grown.position_at(0.5, 0.5)
                self.assertLess(wall.distance_to(Vertex(middle)), 1e-6)
                self.assertAlmostEqual(
                    (grown.normal_at(middle) - wall.normal_at(middle)).length, 0, 6
                )

    def test_the_result_cuts_into_the_cylinder(self):
        holed = self.surface.wrap(
            (Rectangle(8, 5) - Circle(1)).face(), self.places["across the seam"]
        )
        (grown,) = holed.offset_2d(0.4)
        (rim,) = self.surface.offset_2d(-1)
        for face in (grown, rim):
            sunk = self.solid.cut(Solid.thicken(face, -0.5))
            self.assertTrue(sunk.is_valid)
            self.assertAlmostEqual(
                sunk.volume,
                self.solid.volume - face.area * (5**2 - 4.5**2) / 10,
                delta=0.01,
            )

    def test_a_corner_the_kernel_cannot_mitre(self):
        """One piece of a helical band is a sliver whose mitred corners the
        kernel's planar offset fails on, here as on the plane"""
        helix = Face(Polyline((0, 0), (3, 0), (43, 4), (40, 4), close=True))
        piece = self.surface.wrap(helix, self.places["clear of the seam"]).faces()[0]
        (rounded,) = piece.offset_2d(0.2)
        self.assertTrue(rounded.is_valid)
        with self.assertRaisesRegex(RuntimeError, "2D offset failed"):
            piece.offset_2d(0.2, Kind.INTERSECTION)


class TestConeOffset2d(unittest.TestCase):
    """A cone unrolls without distortion into a sector about its apex, so a
    face on one offsets as its flat pattern does too"""

    def setUp(self):
        self.solid = Cone(5, 2, 10)
        self.surface = self.solid.faces().filter_by(GeomType.CONE)[0]
        self.slant = math.hypot(10, 5 - 2)
        self.places = {
            "clear of the seam": self.surface.location_at(0.25, 0.5),
            "across the seam": self.surface.location_at(0.0, 0.5, x_dir=(0, 1, 0)),
        }

    @staticmethod
    def side(solid: Solid) -> Face:
        return solid.faces().filter_by(GeomType.CONE)[0]

    @staticmethod
    def frustum_area(wide: float, narrow: float, height: float, amount: float) -> float:
        """The side of a frustum with both rims moved along its slant"""
        slant = math.hypot(height, wide - narrow)
        return math.pi * (wide + narrow) * (slant + 2 * amount)

    def assert_on(self, surface: Face, face: Face):
        """Valid, on the surface, and facing as the surface does"""
        self.assertTrue(face.is_valid)
        middle = face.position_at(0.5, 0.5)
        self.assertLess(surface.distance_to(middle), 1e-6)
        normal = face.normal_at(middle)
        self.assertAlmostEqual((normal - surface.normal_at(middle)).length, 0, 5)

    def test_a_patch_offsets_as_its_flat_pattern(self):
        """Straight sides and round holes stay lines and arcs unrolled, so the
        corners can be mitred as well as rounded"""
        patterns = {
            "plain": Rectangle(3, 1.5).face(),
            "holed": (Rectangle(4, 2.5) - Circle(0.5)).face(),
        }
        for place, location in self.places.items():
            for name, pattern in patterns.items():
                patch = self.surface.wrap(pattern, location)
                for amount in (0.2, -0.2):
                    for kind in (Kind.ARC, Kind.INTERSECTION):
                        with self.subTest(
                            place=place, pattern=name, amount=amount, kind=kind
                        ):
                            (result,) = patch.offset_2d(amount, kind)
                            self.assert_on(self.surface, result)
                            self.assertEqual(seam_edges(result), 0)
                            self.assertAlmostEqual(
                                result.area, flat_area(pattern, amount, kind), 3
                            )

    def test_a_curved_outline_unrolls_into_splines(self):
        """Neither lines nor arcs: within the tolerance of the flat pattern's
        own offset, the hole shrunk past its tightest curve included"""
        pattern = (
            Rectangle(3, 2) + Pos(1.5, 0) * Ellipse(1.2, 1) - Ellipse(0.6, 0.3)
        ).face()
        for place, location in self.places.items():
            patch = self.surface.wrap(pattern, location)
            for amount in (0.2, -0.2):
                with self.subTest(place=place, amount=amount):
                    (result,) = patch.offset_2d(amount)
                    self.assert_on(self.surface, result)
                    self.assertEqual(len(result.inner_wires()), 1)
                    self.assertAlmostEqual(
                        result.area, flat_area(pattern, amount), delta=5e-3
                    )

    def test_parts(self):
        bar = (
            Pos(-1.5, 0) * Circle(0.75) + Rectangle(3, 0.3) + Pos(1.5, 0) * Circle(0.75)
        )
        for place, location in self.places.items():
            with self.subTest(place=place):
                parts = self.surface.wrap(bar.face(), location).offset_2d(-0.2)
                self.assertEqual(len(parts), 2)
                for part in parts:
                    self.assert_on(self.surface, part)

    def test_all_the_way_round_stays_so(self):
        """Only the rims of a face that goes round the cone move, whatever
        shape the cone is: narrowing or widening along its axis, as wide as
        a countersink or wider, or a needle a few degrees across"""
        cones = {
            "ordinary": (5, 2, 10),
            "narrowing": (2, 5, 10),
            "countersink": (8, 2, 6),
            "sixty degrees": (12, 1.6, 6),
            "needle": (2, 1.5, 10),
        }
        for name, sizes in cones.items():
            surface = self.side(Cone(*sizes))
            for amount in (-0.4, 0.4):
                with self.subTest(cone=name, amount=amount):
                    (result,) = surface.offset_2d(amount)
                    self.assertTrue(result.is_valid)
                    self.assertEqual(seam_edges(result), 1)
                    self.assertAlmostEqual(
                        result.area, self.frustum_area(*sizes, amount), 4
                    )

    def test_a_large_cone(self):
        """A hundred times the size, where the kernel's offset fails on the
        flat pattern as it is and manages it scaled to an ordinary size"""
        surface = self.side(Cone(500, 200, 1000))
        (result,) = surface.offset_2d(-5, Kind.INTERSECTION)
        self.assertTrue(result.is_valid)
        self.assertEqual(seam_edges(result), 1)
        expected = self.frustum_area(500, 200, 1000, -5)
        self.assertAlmostEqual(result.area / expected, 1, 7)

    def test_grown_until_it_meets_itself(self):
        """All but ten degrees of the cone's side: its ends meet first at the
        narrow rim, where the gap is smallest, and then all the way along"""
        partial = Face.revolve(Edge.make_line((5, 0, 0), (2, 0, 10)), 350, Axis.Z)
        (shrunk,) = partial.offset_2d(-0.3)
        self.assertEqual(seam_edges(shrunk), 0)
        (slotted,) = partial.offset_2d(0.2)  # the gap is 0.35 at the narrow rim
        self.assertTrue(slotted.is_valid)
        self.assertEqual(seam_edges(slotted), 1)
        self.assertLess(slotted.area, self.frustum_area(5, 2, 10, 0.2))
        (closed,) = partial.offset_2d(1.6, Kind.INTERSECTION)  # and 0.87 at the wide
        self.assertTrue(closed.is_valid)
        self.assertEqual(seam_edges(closed), 1)
        self.assertAlmostEqual(closed.area, self.frustum_area(5, 2, 10, 1.6), 4)

    def test_walls_and_moved_cones(self):
        """The wall of a countersink faces inwards, in a block that has been
        moved and turned"""
        block = Pos(3, -2, 4) * Rot(20, 30, 40) * (Box(20, 20, 6) - Cone(2, 6, 6))
        wall = self.side(block)
        (rim,) = wall.offset_2d(-0.3)
        self.assert_on(wall, rim)
        self.assertAlmostEqual(rim.area, self.frustum_area(2, 6, 6, -0.3), 4)
        patch = wall.wrap(Rectangle(3, 1.5).face(), wall.location_at(0.3, 0.5))
        (grown,) = patch.offset_2d(0.3)
        self.assert_on(wall, grown)
        self.assertAlmostEqual(grown.area, 4.5 + 9 * 0.3 + math.pi * 0.09, 3)

    def test_the_result_cuts_into_the_cone(self):
        (rim,) = self.surface.offset_2d(-0.4)
        sunk = self.solid.cut(Solid.thicken(rim, -0.2))
        self.assertTrue(sunk.is_valid)
        # a layer 0.2 deep under a cone is a little less than area by depth
        removed = self.solid.volume - sunk.volume
        self.assertLess(removed, rim.area * 0.2)
        self.assertGreater(removed, rim.area * 0.2 * 0.95)

    def test_the_apex_is_out_of_reach(self):
        with self.assertRaisesRegex(ValueError, "reaches the apex of its cone"):
            self.side(Cone(5, 0, 10)).offset_2d(-0.5)
        patch_cone = self.side(Cone(5, 0.3, 10))
        patch = patch_cone.wrap(
            Rectangle(1, 1).face(), patch_cone.location_at(0.25, 0.9)
        )
        (grown,) = patch.offset_2d(0.3)
        self.assertAlmostEqual(grown.area, 1 + 4 * 0.3 + math.pi * 0.09, 3)
        with self.assertRaisesRegex(ValueError, "reaches the apex of the cone"):
            patch.offset_2d(3)

    def test_no_room_to_lay_the_cone_out(self):
        """A face that goes round a cone needs some of the turns beside it
        laid out flat, and about the apex there is not always the room: with
        a narrow rim 0.7 from the apex, or a cone within ten degrees of flat.
        The face is then offset along geodesics, as on any surface, which
        rounds its corners; mitred ones are refused"""
        for sizes, amounts in (
            ((5, 0.3, 10), (0.5, -0.5)),
            ((10, 1, 1.6), (0.3, -0.05)),
        ):
            surface = self.side(Cone(*sizes))
            for amount in amounts:
                with self.subTest(cone=sizes, amount=amount):
                    (result,) = surface.offset_2d(amount)
                    self.assertTrue(result.is_valid)
                    self.assertEqual(seam_edges(result), 1)
                    self.assertAlmostEqual(
                        result.area, self.frustum_area(*sizes, amount), 4
                    )
                    with self.assertRaisesRegex(ValueError, "apex|nearly flat"):
                        surface.offset_2d(amount, Kind.INTERSECTION)
        # past the apex is refused either way
        with self.assertRaisesRegex(ValueError, "reaches the apex of the cone"):
            self.side(Cone(5, 0.3, 10)).offset_2d(1.2)
        # a little way off flat there is room, and a patch needs none
        nearly_flat = self.side(Cone(10, 1, 1.6))
        (mitred,) = nearly_flat.offset_2d(-0.01, Kind.INTERSECTION)
        self.assertAlmostEqual(mitred.area, self.frustum_area(10, 1, 1.6, -0.01), 4)
        patch = nearly_flat.wrap(
            Rectangle(3, 1.5).face(), nearly_flat.location_at(0.25, 0.5)
        )
        (grown,) = patch.offset_2d(0.3, Kind.INTERSECTION)
        self.assertAlmostEqual(grown.area, (3 + 0.6) * (1.5 + 0.6), 3)


def wavy() -> Face:
    """A spline surface 12 square, with gentle hills"""
    return Face.make_surface_from_array_of_points(
        [
            [(x, y, 0.6 * math.sin(x / 2) * math.cos(y / 2)) for y in range(-6, 7, 2)]
            for x in range(-6, 7, 2)
        ]
    )


def vase() -> Face:
    """A surface of revolution with a waist"""
    profile = Edge.make_spline([(4, 0, 0), (6, 0, 3), (3, 0, 7), (5, 0, 10)])
    return Face.revolve(profile, 360, Axis.Z)


class TestGeodesicOffset2d(unittest.TestCase):
    """A surface that does not unroll: the boundary is moved along the
    geodesics that leave it square to itself, and its corners are rounded"""

    def setUp(self):
        self.ball = Sphere(5).face()

    @staticmethod
    def cap(reach: float) -> float:
        """The area of a radius 5 sphere within ``reach`` of a point of it"""
        return 2 * math.pi * 25 * (1 - math.cos(reach / 5))

    @staticmethod
    def zone(latitude: float) -> float:
        """The area of a radius 5 sphere between a latitude and its opposite"""
        return 4 * math.pi * 25 * math.sin(latitude)

    def assert_on(self, surface: Face, face: Face):
        """Valid, on the surface, and facing as the surface does"""
        self.assertTrue(face.is_valid)
        middle = face.position_at(0.5, 0.5)
        self.assertLess(surface.distance_to(middle), 1e-6)
        normal = face.normal_at(middle)
        self.assertAlmostEqual((normal - surface.normal_at(middle)).length, 0, 4)

    def assert_moved(self, result: Face, original: Face, amount: float):
        """Every point of the result's outline is the amount from the
        original's, measured straight across, which over so short a way is
        within a part in a hundred of the way along the surface"""
        outline = original.outer_wire()
        distances = [
            outline.distance_to(edge.position_at(i / 8))
            for edge in result.outer_wire().edges()
            for i in range(8)
        ]
        self.assertAlmostEqual(min(distances), abs(amount), delta=0.01 * abs(amount))
        self.assertAlmostEqual(max(distances), abs(amount), delta=0.01 * abs(amount))

    def test_a_disc_on_a_sphere_stays_a_disc(self):
        """Wherever it is: clear of the seam, across it, or far up the sphere
        where a degree of longitude is short"""
        places = {
            "clear of the seam": self.ball.location_at(0.25, 0.5),
            "across the seam": self.ball.location_at(0.0, 0.5, x_dir=(0, 1, 0)),
            "far up": self.ball.location_at(0.3, 0.8),
        }
        for place, location in places.items():
            disc = self.ball.wrap(Circle(2).face(), location)
            for amount in (0.5, -0.5):
                with self.subTest(place=place, amount=amount):
                    (result,) = disc.offset_2d(amount)
                    self.assert_on(self.ball, result)
                    self.assertAlmostEqual(result.area / self.cap(2 + amount), 1, 4)
        with self.assertRaisesRegex(ValueError, "nothing is left"):
            disc.offset_2d(-2.5)

    def test_a_band_round_a_sphere(self):
        """All the way round the equator: only its rims move, and it comes
        back with its seam edge"""
        equator = Rectangle(10 * math.pi, 3, align=(Align.MIN, Align.CENTER)).face()
        (band,) = UVFrame(self.ball, lambda x, y: (x / 5 + 1.0, y / 5)).write_face(
            equator
        )
        self.assertAlmostEqual(band.area, self.zone(0.3), 5)
        for amount in (0.5, -0.5):
            with self.subTest(amount=amount):
                (result,) = band.offset_2d(amount)
                self.assertTrue(result.is_valid)
                self.assertEqual(seam_edges(result), 1)
                self.assertAlmostEqual(result.area, self.zone(0.3 + amount / 5), 4)
        with self.assertRaisesRegex(ValueError, "nothing is left"):
            band.offset_2d(-1.6)
        with self.assertRaisesRegex(ValueError, "pole"):
            band.offset_2d(8)  # the poles are 7.1 from its rims

    def test_a_patch_on_each_kind_of_surface(self):
        surfaces = {
            "sphere": (self.ball, self.ball.location_at(0.25, 0.5)),
            "torus": (Torus(10, 3).face(), None),
            "spline": (wavy(), None),
            "revolution": (vase(), None),
        }
        for name, (surface, location) in surfaces.items():
            if name == "torus":
                location = surface.location_at(0.3, 0.0, x_dir=(0, 0, 1))
            elif location is None:
                location = surface.location_at(0.3, 0.5)
            patch = surface.wrap(Rectangle(4, 3).face(), location)
            for amount in (0.4, -0.4):
                with self.subTest(surface=name, amount=amount):
                    (result,) = patch.offset_2d(amount)
                    self.assert_on(surface, result)
                    self.assert_moved(result, patch, amount)

    def test_holes_parts_and_tight_corners(self):
        location = self.ball.location_at(0.25, 0.5)
        holed = self.ball.wrap((Rectangle(5, 4) - Circle(1)).face(), location)
        (closed,) = holed.offset_2d(1.2)  # past the middle of the hole
        self.assert_on(self.ball, closed)
        self.assertEqual(len(closed.inner_wires()), 0)
        (open_still,) = holed.offset_2d(0.3)
        self.assertEqual(len(open_still.inner_wires()), 1)
        # shrunk by more than the radius of its corners, whose offsets turn
        # back on themselves
        rounded = self.ball.wrap(RectangleRounded(5, 3, 0.4).face(), location)
        (shrunk,) = rounded.offset_2d(-0.6)
        self.assert_on(self.ball, shrunk)
        self.assert_moved(shrunk, rounded, -0.6)
        bar = (
            Pos(-1.5, 0) * Circle(0.75) + Rectangle(3, 0.3) + Pos(1.5, 0) * Circle(0.75)
        )
        parts = self.ball.wrap(bar.face(), location).offset_2d(-0.2)
        self.assertEqual(len(parts), 2)
        for part in parts:
            self.assert_on(self.ball, part)

    def test_a_surface_without_a_boundary_is_left_alone(self):
        for whole in (self.ball, Torus(10, 3).face()):
            self.assertEqual(whole.offset_2d(1), [whole])

    def test_only_rounded_corners(self):
        patch = self.ball.wrap(Rectangle(4, 3).face(), self.ball.location_at(0.25, 0.5))
        for kind in (Kind.INTERSECTION, Kind.TANGENT):
            with self.assertRaisesRegex(ValueError, "Kind.ARC"):
                patch.offset_2d(0.5, kind)

    def test_the_poles_are_out_of_reach(self):
        hemisphere = Sphere(5).split(Plane.XY).faces().filter_by(GeomType.SPHERE)[0]
        with self.assertRaisesRegex(ValueError, "reaches a pole of its surface"):
            hemisphere.offset_2d(-1)
        near = self.ball.wrap(Circle(1.5).face(), self.ball.location_at(0.3, 0.85))
        (short,) = near.offset_2d(0.5)  # the pole is 2.4 from its middle
        self.assertAlmostEqual(short.area / self.cap(2), 1, 4)
        with self.assertRaisesRegex(ValueError, "pole"):
            near.offset_2d(2)

    def test_the_end_of_a_spline_surface(self):
        """A face grown past the edge of its surface ends there"""
        surface = wavy()
        (whole,) = surface.offset_2d(1)
        self.assertTrue(whole.is_valid)
        self.assertAlmostEqual(whole.area, surface.area, 4)
        (inset,) = surface.offset_2d(-1)
        self.assert_moved(inset, surface, -1)
        by_the_edge = surface.wrap(
            Rectangle(4, 3).face(), surface.location_at(0.85, 0.5)
        )
        (clipped,) = by_the_edge.offset_2d(1)
        self.assertTrue(clipped.is_valid)
        self.assertLess(clipped.bounding_box().max.X, 6 + 1e-6)
        self.assertGreater(clipped.area, by_the_edge.area)

    def test_bands_round_a_torus(self):
        """The long way round and the short: a seam edge either way"""
        ring = Torus(10, 3).face()
        long_way = Rectangle(26 * math.pi, 3, align=(Align.MIN, Align.CENTER)).face()
        short_way = Rectangle(4, 6 * math.pi, align=(Align.CENTER, Align.MIN)).face()
        bands = {
            "long": (lambda x, y: (x / 13 + 0.7, y / 3 + 2.0), long_way),
            "short": (lambda x, y: (x / 13 + 2.0, y / 3 + 0.7), short_way),
        }
        for name, (mapping, planar) in bands.items():
            (band,) = UVFrame(ring, mapping).write_face(planar)
            for amount in (0.5, -0.5):
                with self.subTest(way=name, amount=amount):
                    (result,) = band.offset_2d(amount)
                    self.assertTrue(result.is_valid)
                    self.assertEqual(seam_edges(result), 1)
                    self.assertGreater(result.area * amount, band.area * amount)

    def test_walls_and_moved_spheres(self):
        """The inside of a hollow ball faces inwards, in a ball that has been
        moved and turned"""
        hollow = Pos(3, -2, 4) * Rot(20, 30, 40) * (Sphere(6) - Sphere(5))
        for wall in hollow.faces():
            with self.subTest(radius=wall.radius):
                patch = wall.wrap(Rectangle(4, 3).face(), wall.location_at(0.3, 0.5))
                (grown,) = patch.offset_2d(0.4)
                self.assert_on(wall, grown)
                self.assert_moved(grown, patch, 0.4)

    def test_the_result_cuts_into_the_sphere(self):
        solid = Sphere(5)
        disc = self.ball.wrap(Circle(2).face(), self.ball.location_at(0.25, 0.5))
        (grown,) = disc.offset_2d(0.5)
        sunk = solid.cut(Solid.thicken(grown, -0.5))
        self.assertTrue(sunk.is_valid)
        # a layer 0.5 deep under a sphere narrows towards the centre
        removed = solid.volume - sunk.volume
        self.assertLess(removed, grown.area * 0.5)
        self.assertGreater(removed, grown.area * 0.5 * 0.85)


if __name__ == "__main__":
    unittest.main()
