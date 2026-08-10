# write me the test for testing the persistence module with unittest

import unittest
from build123d.persistence import (
    serialize_shape,
    deserialize_shape,
    serialize_location,
    deserialize_location,
)
from build123d import *
import pickle


class TestPersistence(unittest.TestCase):
    def test_serialize_shape(self):
        edge = Edge.make_line((10, 5, 0), (10, 5, 2))
        wire = Wire.make_circle(10)
        face = Face.make_rect(10, 5)
        solid = Solid.make_box(10, 5, 2)
        compound = Compound([edge, wire, face, solid])

        buffer = serialize_shape(edge.wrapped)
        retrived_edge = deserialize_shape(buffer)
        self.assertAlmostEqual(edge.length, Edge(retrived_edge).length)

        buffer = serialize_shape(wire.wrapped)
        retrived_wire = deserialize_shape(buffer)
        self.assertAlmostEqual(len(wire.edges()), len(Wire(retrived_wire).edges()))

        buffer = serialize_shape(face.wrapped)
        retrived_face = deserialize_shape(buffer)
        self.assertAlmostEqual(face.area, Face(retrived_face).area)

        buffer = serialize_shape(solid.wrapped)
        retrived_solid = deserialize_shape(buffer)
        self.assertAlmostEqual(solid.volume, Solid(retrived_solid).volume)

        buffer = serialize_shape(compound.wrapped)
        retrived_comp = deserialize_shape(buffer)
        self.assertEqual(len(compound.solids()), len(Compound(retrived_comp).solids()))

    def test_serialize_location(self):
        loc = Location((10, 5, 0), (16, 1, 1)).wrapped
        transfo = loc.Transformation()

        buffer = serialize_location(loc)
        retrived_loc = deserialize_location(buffer)
        retrived_transfo = retrived_loc.Transformation()
        self.assertAlmostEqual(
            retrived_transfo.TranslationPart().X(), transfo.TranslationPart().X()
        )
        self.assertAlmostEqual(
            retrived_transfo.TranslationPart().Y(), transfo.TranslationPart().Y()
        )
        self.assertAlmostEqual(
            retrived_transfo.TranslationPart().Z(), transfo.TranslationPart().Z()
        )
        self.assertAlmostEqual(
            retrived_transfo.GetRotation().X(), transfo.GetRotation().X()
        )
        self.assertAlmostEqual(
            retrived_transfo.GetRotation().Y(), transfo.GetRotation().Y()
        )
        self.assertAlmostEqual(
            retrived_transfo.GetRotation().Z(), transfo.GetRotation().Z()
        )
        self.assertAlmostEqual(
            retrived_transfo.GetRotation().W(), transfo.GetRotation().W()
        )

    def test_serialize_obj(self):
        # The pickle test tests the serialization of toplevel objects (OCP Shapes and OCP Locs are also tested this way)
        line = Line((10, 5, 0), (0, 5, 2))
        face = Circle(50)
        solid = Box(10, 5, 2)

        dumped_line = pickle.dumps(line)
        retrived_line = pickle.loads(dumped_line)
        self.assertAlmostEqual(line.length, retrived_line.length)

        dumped_face = pickle.dumps(face)
        retrived_face = pickle.loads(dumped_face)
        self.assertAlmostEqual(face.area, retrived_face.area)

        dumped_solid = pickle.dumps(solid)
        retrived_solid = pickle.loads(dumped_solid)
        self.assertAlmostEqual(solid.volume, retrived_solid.volume)


if __name__ == "__main__":
    unittest.main()
