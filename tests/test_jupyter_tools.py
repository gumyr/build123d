import unittest

from build123d.topology import Solid, Vector
from build123d.jupyter_tools import display, to_vtkpoly_string


class TestJupyter(unittest.TestCase):
    def test_vtk_javascript(self):
        shape = Solid.make_box(1, 1, 1)

        # Test no exception on rendering to js
        js1 = display(shape)._repr_javascript_()
        assert "function render" in js1

    def test_display_error(self):
        with self.assertRaises(ValueError):
            display(Vector())
