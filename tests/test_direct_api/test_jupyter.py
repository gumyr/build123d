"""
build123d imports

name: test_jupyter.py
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

import unittest

from build123d.geometry import Vector
from build123d.jupyter_tools import shape_to_html
from build123d.vtk_tools import to_vtkpoly_string
from build123d.topology import Solid


class TestJupyter(unittest.TestCase):
    def test_repr_html(self):
        shape = Solid.make_box(1, 1, 1)

        # Test no exception on rendering to html
        html1 = shape._repr_html_()

        assert "function render" in html1

    def test_display_error(self):
        with self.assertRaises(TypeError):
            shape_to_html(Vector())

        with self.assertRaises(ValueError):
            to_vtkpoly_string("invalid")

        with self.assertRaises(ValueError):
            shape_to_html("invalid")


if __name__ == "__main__":
    unittest.main()
