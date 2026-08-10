"""
build123d topology

name: vtk_tools.py
by:   Gumyr
date: January 07, 2025

desc:

This module defines the foundational classes and methods for the build123d CAD library, enabling
detailed geometric operations and 3D modeling capabilities. It provides a hierarchy of classes
representing various geometric entities like vertices, edges, wires, faces, shells, solids, and
compounds. These classes are designed to work seamlessly with the OpenCascade Python bindings,
leveraging its robust CAD kernel.

Key Features:
- **Shape Base Class:** Implements core functionalities such as transformations (rotation,
  translation, scaling), geometric queries, and boolean operations (cut, fuse, intersect).
- **Custom Utilities:** Includes helper classes like `ShapeList` for advanced filtering, sorting,
  and grouping of shapes, and `GroupBy` for organizing shapes by specific criteria.
- **Type Safety:** Extensive use of Python typing features ensures clarity and correctness in type
  handling.
- **Advanced Geometry:** Supports operations like finding intersections, computing bounding boxes,
  projecting faces, and generating triangulated meshes.

The module is designed for extensibility, enabling developers to build complex 3D assemblies and
perform detailed CAD operations programmatically while maintaining a clean and structured API.

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

from typing import Any, TYPE_CHECKING
import warnings

# Optional Jupyter/VTK display support depends on Mesher for triangulation.
# This import is part of a known lazy-import cycle in the temporary notebook
# integration path and is safe at runtime because the display code is only
# exercised after package initialization is complete.
from build123d.mesher import Mesher  # pylint: disable=cyclic-import

if TYPE_CHECKING:
    from build123d.topology.shape_core import Shape

has_vtk = True
try:
    from vtkmodules.vtkCommonCore import vtkPoints, vtkFloatArray
    from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkCellArray
    from vtkmodules.vtkFiltersCore import vtkPolyDataNormals, vtkTriangleFilter
    from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter
except ImportError:
    has_vtk = False


if has_vtk:

    class VtkShape:
        """Wrapper for VTK shape display data."""

        def __init__(
            self,
            shape: "Shape",
            tolerance: float | None = None,
            angular_tolerance: float | None = None,
            normals: bool = False,
        ):
            self.obj = shape
            self.deviation_coefficient = tolerance if tolerance else 1e-3
            self.deviation_angle = angular_tolerance if angular_tolerance else 0.1
            self.normals = normals
            self.width = 1
            self.vtk_poly_data = None

        def build_mesh(self):
            """Build triangular mesh from Shape using Mesher"""
            # Use Mesher to triangulate the shape
            vertices, triangles = Mesher._mesh_shape(
                self.obj, self.deviation_coefficient, self.deviation_angle
            )

            # Create VTK data structures
            points = vtkPoints()
            for x, y, z in vertices:
                points.InsertNextPoint(x, y, z)

            triangle_cells = vtkCellArray()
            for tri in triangles:
                triangle_cells.InsertNextCell(3)
                for idx in tri:
                    triangle_cells.InsertCellPoint(idx)

            # Create vtkPolyData
            self.vtk_poly_data = vtkPolyData()
            self.vtk_poly_data.SetPoints(points)
            self.vtk_poly_data.SetPolys(triangle_cells)

            # Add line width as field data
            if self.width != 1:
                line_width = vtkFloatArray()
                line_width.SetName("LineWidth")
                line_width.InsertNextValue(self.width)
                self.vtk_poly_data.GetFieldData().AddArray(line_width)

        def get_vtk_poly_data(self):
            """Return the vtkPolyData"""
            return self.vtk_poly_data


def to_vtk_poly_data(
    obj,
    tolerance: float | None = None,
    angular_tolerance: float | None = None,
    normals: bool = False,
) -> "vtkPolyData | None":
    """Convert shape to vtkPolyData

    Args:
        tolerance: float:
        angular_tolerance: float:  (Default value = 0.1)
        normals: bool:  (Default value = True)

    Returns: data object in VTK consisting of points, vertices, lines, and polygons
    """
    if not has_vtk:
        warnings.warn("VTK is not installed", stacklevel=2)
        return None

    if not obj:
        raise ValueError("Cannot convert an empty shape")

    # pylint: disable=possibly-used-before-assignment
    vtk_shape = VtkShape(obj, tolerance, angular_tolerance, normals)
    vtk_shape.build_mesh()
    vtk_poly_data = vtk_shape.get_vtk_poly_data()

    # convert to triangles and split edges
    t_filter = vtkTriangleFilter()
    t_filter.SetInputData(vtk_poly_data)
    t_filter.Update()

    return_value = t_filter.GetOutput()

    # compute normals
    if normals:
        n_filter = vtkPolyDataNormals()
        n_filter.SetComputePointNormals(True)
        n_filter.SetComputeCellNormals(True)
        n_filter.SetFeatureAngle(360)
        n_filter.SetInputData(return_value)
        n_filter.Update()

        return_value = n_filter.GetOutput()

    return return_value


def to_vtkpoly_string(
    shape: Any, tolerance: float = 1e-3, angular_tolerance: float = 0.1
) -> str | None:
    """to_vtkpoly_string

    Args:
        shape (Shape): object to convert
        tolerance (float, optional): Defaults to 1e-3.
        angular_tolerance (float, optional): Defaults to 0.1.

    Raises:
        ValueError: not a valid Shape

    Returns:
        str: vtkpoly str
    """
    if not has_vtk:
        warnings.warn("VTK is not installed", stacklevel=2)
        return None

    if not hasattr(shape, "wrapped"):
        raise ValueError(f"Type {type(shape)} is not supported")

    writer = vtkXMLPolyDataWriter()
    writer.SetWriteToOutputString(True)
    writer.SetInputData(to_vtk_poly_data(shape, tolerance, angular_tolerance, True))
    writer.Write()

    return writer.GetOutputString()
