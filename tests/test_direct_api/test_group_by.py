"""
build123d imports

name: test_group_by.py
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

import pprint
import unittest

from build123d.geometry import Axis
from build123d.topology import Solid


class TestGroupBy(unittest.TestCase):

    def setUp(self):
        # Ensure the class variable is in its default state before each test
        self.v = Solid.make_box(1, 1, 1).vertices().group_by(Axis.Z)

    def test_str(self):
        self.assertEqual(
            str(self.v),
            f"""[[Vertex(0.0, 0.0, 0.0),
  Vertex(0.0, 1.0, 0.0),
  Vertex(1.0, 0.0, 0.0),
  Vertex(1.0, 1.0, 0.0)],
 [Vertex(0.0, 0.0, 1.0),
  Vertex(0.0, 1.0, 1.0),
  Vertex(1.0, 0.0, 1.0),
  Vertex(1.0, 1.0, 1.0)]]""",
        )

    def test_repr(self):
        self.assertEqual(
            repr(self.v),
            "[[Vertex(0.0, 0.0, 0.0), Vertex(0.0, 1.0, 0.0), Vertex(1.0, 0.0, 0.0), Vertex(1.0, 1.0, 0.0)], [Vertex(0.0, 0.0, 1.0), Vertex(0.0, 1.0, 1.0), Vertex(1.0, 0.0, 1.0), Vertex(1.0, 1.0, 1.0)]]",
        )

    def test_pp(self):
        self.assertEqual(
            pprint.pformat(self.v),
            "[[Vertex(0.0, 0.0, 0.0), Vertex(0.0, 1.0, 0.0), Vertex(1.0, 0.0, 0.0), Vertex(1.0, 1.0, 0.0)], [Vertex(0.0, 0.0, 1.0), Vertex(0.0, 1.0, 1.0), Vertex(1.0, 0.0, 1.0), Vertex(1.0, 1.0, 1.0)]]",
        )


if __name__ == "__main__":
    unittest.main()
