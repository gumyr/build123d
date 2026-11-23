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

from build123d.build_enums import GeomType, Kind
from build123d.geometry import Axis, Plane, Pos, Rot
from build123d.objects_curve import Polyline
from build123d.objects_part import Box, Cone, Cylinder
from build123d.objects_sketch import Circle, Ellipse, Rectangle
from build123d.operations_generic import offset
from build123d.topology import Edge, Face, Solid, Vertex, Wire

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
        # a narrow rim 0.7 from the apex leaves no room beside a face that
        # goes round, grown or shrunk
        blunt = self.side(Cone(5, 0.3, 10))
        for amount in (0.5, -0.5):
            with self.assertRaisesRegex(ValueError, "too near the apex"):
                blunt.offset_2d(amount)
        patch = blunt.wrap(Rectangle(1, 1).face(), blunt.location_at(0.25, 0.9))
        (grown,) = patch.offset_2d(0.3)
        self.assertAlmostEqual(grown.area, 1 + 4 * 0.3 + math.pi * 0.09, 3)
        with self.assertRaisesRegex(ValueError, "reaches the apex of the cone"):
            patch.offset_2d(3)

    def test_a_cone_too_nearly_flat(self):
        """Within ten degrees of flat, a face that goes round leaves almost
        none of the circle about the apex to lay its neighbours out in"""
        nearly_flat = self.side(Cone(10, 1, 1.6))
        (slightly,) = nearly_flat.offset_2d(-0.01)
        self.assertAlmostEqual(slightly.area, self.frustum_area(10, 1, 1.6, -0.01), 4)
        with self.assertRaisesRegex(ValueError, "too nearly flat"):
            nearly_flat.offset_2d(-0.05)
        # a patch needs no neighbours
        patch = nearly_flat.wrap(
            Rectangle(3, 1.5).face(), nearly_flat.location_at(0.25, 0.5)
        )
        (grown,) = patch.offset_2d(0.3)
        self.assertAlmostEqual(grown.area, 4.5 + 9 * 0.3 + math.pi * 0.09, 3)


if __name__ == "__main__":
    unittest.main()
