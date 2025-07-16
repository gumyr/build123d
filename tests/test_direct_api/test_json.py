"""
build123d tests

name: test_json.py
by:   Gumyr
date: February 24, 2025

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

import json
import unittest
from build123d.geometry import (
    Axis,
    Color,
    GeomEncoder,
    Location,
    LocationEncoder,
    Matrix,
    Plane,
    Rotation,
    Vector,
)


class TestGeomEncode(unittest.TestCase):

    def test_as_json(self):

        a_json = json.dumps(Axis.Y, cls=GeomEncoder)
        axis = json.loads(a_json, object_hook=GeomEncoder.geometry_hook)
        self.assertEqual(Axis.Y, axis)

        c_json = json.dumps(Color("red"), cls=GeomEncoder)
        color = json.loads(c_json, object_hook=GeomEncoder.geometry_hook)
        self.assertEqual(tuple(Color("red")), tuple(color))

        loc = Location((0, 1, 2), (4, 8, 16))
        l_json = json.dumps(loc, cls=GeomEncoder)
        loc_json = json.loads(l_json, object_hook=GeomEncoder.geometry_hook)
        self.assertAlmostEqual(loc.position, loc_json.position, 5)
        self.assertAlmostEqual(loc.orientation, loc_json.orientation, 5)

        with self.assertWarnsRegex(DeprecationWarning, "Use GeomEncoder instead"):
            loc_legacy = json.loads(l_json, object_hook=LocationEncoder.location_hook)
        self.assertAlmostEqual(loc.position, loc_legacy.position, 5)
        self.assertAlmostEqual(loc.orientation, loc_legacy.orientation, 5)

        p_json = json.dumps(Plane.XZ, cls=GeomEncoder)
        plane = json.loads(p_json, object_hook=GeomEncoder.geometry_hook)
        self.assertEqual(Plane.XZ, plane)

        rot = Rotation((0, 1, 4))
        r_json = json.dumps(rot, cls=GeomEncoder)
        rotation = json.loads(r_json, object_hook=GeomEncoder.geometry_hook)
        self.assertAlmostEqual(rot.position, rotation.position, 5)
        self.assertAlmostEqual(rot.orientation, rotation.orientation, 5)

        v_json = json.dumps(Vector(1, 2, 4), cls=GeomEncoder)
        vector = json.loads(v_json, object_hook=GeomEncoder.geometry_hook)
        self.assertEqual(Vector(1, 2, 4), vector)

    def test_as_json_error(self):
        with self.assertRaises(TypeError):
            json.dumps(Matrix(), cls=GeomEncoder)

        v_json = '{"Vector": [1.0, 2.0, 4.0], "Color": [0, 0, 0, 0]}'
        with self.assertRaises(ValueError):
            json.loads(v_json, object_hook=GeomEncoder.geometry_hook)


if __name__ == "__main__":
    unittest.main()
