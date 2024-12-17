import unittest

from build123d.topology import Solid
from build123d.jupyter_tools import display, to_vtkpoly_string


class TestJupyter(unittest.TestCase):
    def test_vtk_javascript(self):
        shape = Solid.make_box(1, 1, 1)

        # Test no exception on rendering to js
        js1 = to_vtkpoly_string(shape)
        assert "function render" in js1

    def test_display_error(self):
        with self.assertRaises(AttributeError):
            display(Vector())
