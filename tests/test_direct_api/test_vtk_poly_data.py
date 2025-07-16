"""
build123d imports

name: test_v_t_k_poly_data.py
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

from build123d.topology import Solid
from build123d.vtk_tools import to_vtk_poly_data
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersCore import vtkTriangleFilter


class TestVTKPolyData(unittest.TestCase):
    def setUp(self):
        # Create a simple test object (e.g., a cylinder)
        self.object_under_test = Solid.make_cylinder(1, 2)

    def test_to_vtk_poly_data(self):
        # Generate VTK data
        vtk_data = to_vtk_poly_data(
            self.object_under_test, tolerance=0.1, angular_tolerance=0.2, normals=True
        )

        # Verify the result is of type vtkPolyData
        self.assertIsInstance(vtk_data, vtkPolyData)

        # Further verification can include:
        # - Checking the number of points, polygons, or cells
        self.assertGreater(
            vtk_data.GetNumberOfPoints(), 0, "VTK data should have points."
        )
        self.assertGreater(
            vtk_data.GetNumberOfCells(), 0, "VTK data should have cells."
        )

        # Optionally, compare the output with a known reference object
        # (if available) by exporting or analyzing the VTK data
        known_filter = vtkTriangleFilter()
        known_filter.SetInputData(vtk_data)
        known_filter.Update()
        known_output = known_filter.GetOutput()

        self.assertEqual(
            vtk_data.GetNumberOfPoints(),
            known_output.GetNumberOfPoints(),
            "Number of points in VTK data does not match the expected output.",
        )
        self.assertEqual(
            vtk_data.GetNumberOfCells(),
            known_output.GetNumberOfCells(),
            "Number of cells in VTK data does not match the expected output.",
        )

    def test_empty_shape(self):
        # Test handling of empty shape
        empty_object = Solid()  # Create an empty object
        with self.assertRaises(ValueError) as context:
            to_vtk_poly_data(empty_object)

        self.assertEqual(str(context.exception), "Cannot convert an empty shape")


if __name__ == "__main__":
    unittest.main()
