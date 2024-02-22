"""

build123d enum tests

name: test_build_enums.py
by:   Gumyr
date: Feb 2nd 2023

desc: Unit tests for the build123d enums

license:

    Copyright 2023 Gumyr

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
from build123d import *


class TestEnumRepr(unittest.TestCase):
    def test_repr(self):
        enums = [
            Align,
            AngularDirection,
            ApproxOption,
            CenterOf,
            Extrinsic,
            FontStyle,
            FrameMethod,
            GeomType,
            HeadType,
            Intrinsic,
            Keep,
            Kind,
            LengthMode,
            MeshType,
            Mode,
            NumberDisplay,
            PositionMode,
            PageSize,
            Select,
            Side,
            SortBy,
            Transition,
            Unit,
            Until,
        ]
        for enum in enums:
            for member in enum:
                self.assertEqual(repr(member), f"<{enum.__name__}.{member._name_}>")


if __name__ == "__main__":
    unittest.main()
