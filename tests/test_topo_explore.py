from typing import Optional
import unittest

from build123d.build_enums import SortBy

from build123d.objects_part import Box
from build123d.geometry import (
    Axis,
    Vector,
    VectorLike,
)
from build123d.topology import (
    Edge,
    Face,
    Wire,
    topo_explore_connected_edges,
    topo_explore_common_vertex,
)


class DirectApiTestCase(unittest.TestCase):
    def assertTupleAlmostEquals(
        self,
        first: tuple[float, ...],
        second: tuple[float, ...],
        places: int,
        msg: Optional[str] = None,
    ):
        """Check Tuples"""
        self.assertEqual(len(second), len(first))
        for i, j in zip(second, first):
            self.assertAlmostEqual(i, j, places, msg=msg)

    def assertVectorAlmostEquals(
        self, first: Vector, second: VectorLike, places: int, msg: Optional[str] = None
    ):
        second_vector = Vector(second)
        self.assertAlmostEqual(first.X, second_vector.X, places, msg=msg)
        self.assertAlmostEqual(first.Y, second_vector.Y, places, msg=msg)
        self.assertAlmostEqual(first.Z, second_vector.Z, places, msg=msg)


class TestTopoExplore(DirectApiTestCase):

    def test_topo_explore_connected_edges(self):
        # 2D
        triangle = Face(
            Wire(
                [
                    Edge.make_line((0, 0), (2.5, 0)),
                    Edge.make_line((2.5, 0), (4.0)),
                    Edge.make_line((4, 0), (0, 3)),
                    Edge.make_line((0, 3), (0, 1.25)),
                    Edge.make_line((0, 1.25), (0, 0)),
                ]
            )
        )

        hypotenuse = triangle.edges().sort_by(SortBy.LENGTH)[-1]
        connected_edges = topo_explore_connected_edges(hypotenuse).sort_by(
            SortBy.LENGTH
        )
        self.assertAlmostEqual(connected_edges[0].length, 1.5, 5)
        self.assertAlmostEqual(connected_edges[1].length, 1.75, 5)

        # 3D
        box = Box(1, 1, 1)
        first_edge = box.edges()[0]
        connected_edges = topo_explore_connected_edges(first_edge)
        self.assertEqual(len(connected_edges), 4)

        self.assertEqual(len(topo_explore_connected_edges(hypotenuse, parent=box)), 0)

        # 2 Edges
        l1 = Edge.make_spline([(-1, 0), (1, 0)], tangents=((0, -8), (0, 8)), scale=True)
        l2 = Edge.make_line(l1 @ 0, l1 @ 1)
        face = Face(Wire([l1, l2]))
        connected_edges = topo_explore_connected_edges(face.edges()[0])
        self.assertEqual(len(connected_edges), 1)

    def test_topo_explore_common_vertex(self):
        triangle = Face(
            Wire(
                [
                    Edge.make_line((0, 0), (4, 0)),
                    Edge.make_line((4, 0), (0, 3)),
                    Edge.make_line((0, 3), (0, 0)),
                ]
            )
        )
        hypotenuse = triangle.edges().sort_by(SortBy.LENGTH)[-1]
        base = triangle.edges().sort_by(Axis.Y)[0]
        common_vertex = topo_explore_common_vertex(hypotenuse, base)
        self.assertIsNotNone(common_vertex)
        self.assertVectorAlmostEquals(Vector(common_vertex), (4, 0, 0), 5)
        self.assertIsNone(
            topo_explore_common_vertex(hypotenuse, Edge.make_line((0, 0), (4, 0)))
        )


if __name__ == "__main__":
    unittest.main()
