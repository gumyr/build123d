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

from typing import Any
import warnings

from OCP.Aspect import Aspect_TOL_SOLID
from OCP.Prs3d import Prs3d_IsoAspect
from OCP.Quantity import Quantity_Color

HAS_VTK = True
try:
    from OCP.IVtkOCC import IVtkOCC_Shape, IVtkOCC_ShapeMesher
    from OCP.IVtkVTK import IVtkVTK_ShapeData
    from vtkmodules.vtkCommonDataModel import vtkPolyData
    from vtkmodules.vtkFiltersCore import vtkPolyDataNormals, vtkTriangleFilter
    from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter
except ImportError:
    HAS_VTK = False


def to_vtk_poly_data(
    obj,
    tolerance: float | None = None,
    angular_tolerance: float | None = None,
    normals: bool = False,
) -> "vtkPolyData":
    """Convert shape to vtkPolyData

    Args:
        tolerance: float:
        angular_tolerance: float:  (Default value = 0.1)
        normals: bool:  (Default value = True)

    Returns: data object in VTK consisting of points, vertices, lines, and polygons
    """
    if not HAS_VTK:
        warnings.warn("VTK not supported", stacklevel=2)

    if obj.wrapped is None:
        raise ValueError("Cannot convert an empty shape")

    vtk_shape = IVtkOCC_Shape(obj.wrapped)
    shape_data = IVtkVTK_ShapeData()
    shape_mesher = IVtkOCC_ShapeMesher()

    drawer = vtk_shape.Attributes()
    drawer.SetUIsoAspect(Prs3d_IsoAspect(Quantity_Color(), Aspect_TOL_SOLID, 1, 0))
    drawer.SetVIsoAspect(Prs3d_IsoAspect(Quantity_Color(), Aspect_TOL_SOLID, 1, 0))

    if tolerance:
        drawer.SetDeviationCoefficient(tolerance)

    if angular_tolerance:
        drawer.SetDeviationAngle(angular_tolerance)

    shape_mesher.Build(vtk_shape, shape_data)

    vtk_poly_data = shape_data.getVtkPolyData()

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
) -> str:
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
    if not hasattr(shape, "wrapped"):
        raise ValueError(f"Type {type(shape)} is not supported")

    writer = vtkXMLPolyDataWriter()
    writer.SetWriteToOutputString(True)
    writer.SetInputData(to_vtk_poly_data(shape, tolerance, angular_tolerance, True))
    writer.Write()

    return writer.GetOutputString()
