"""
build123d direct api tests

name: test_direct_api_test_case.py
by:   Gumyr
date: January 21, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

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
from typing import Optional

from build123d.geometry import Vector, VectorLike


class DirectApiTestCase(unittest.TestCase):
    def assertTupleAlmostEquals(
        self,
        first: tuple[float, ...],
        second: tuple[float, ...],
        places: int,
        msg: str | None = None,
    ):
        """Check Tuples"""
        self.assertEqual(len(second), len(first))
        for i, j in zip(second, first):
            self.assertAlmostEqual(i, j, places, msg=msg)

    def assertVectorAlmostEquals(
        self, first: Vector, second: VectorLike, places: int, msg: str | None = None
    ):
        second_vector = Vector(second)
        self.assertAlmostEqual(first.X, second_vector.X, places, msg=msg)
        self.assertAlmostEqual(first.Y, second_vector.Y, places, msg=msg)
        self.assertAlmostEqual(first.Z, second_vector.Z, places, msg=msg)


if __name__ == "__main__":
    import unittest

    unittest.main()
