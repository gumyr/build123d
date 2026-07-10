"""
build123d import dxf

name: import_dxf.py
by:   Gumyr
date: November 10th, 2024

desc:
    This python module imports a DXF file as build123d objects.

license:

    Copyright 2024 Gumyr

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

import math
import warnings
from io import BytesIO, StringIO, TextIOBase
from os import PathLike
from typing import BinaryIO, Callable, TextIO, cast

import ezdxf
from ezdxf.entities import DXFGraphic
from ezdxf.entities.boundary_paths import (
    ArcEdge,
    EdgePath,
    EllipseEdge,
    LineEdge,
    PolylinePath,
    SplineEdge,
)

from build123d.build_enums import TextAlign
from build123d.geometry import TOLERANCE, Axis, Pos, Vector, VectorLike
from build123d.objects_curve import (
    BSpline,
    CenterArc,
    EllipticalCenterArc,
    Line,
    SagittaArc,
    Spline,
)
from build123d.objects_sketch import Circle, Polygon, Text
from build123d.operations_generic import scale
from build123d.topology import Edge, Shape, ShapeList, Vertex, Wire

# Unfortunately exdxf is not fully typed
# mypy: disable-error-code="attr-defined"


def process_arc(entity: DXFGraphic) -> CenterArc:
    """Convert ARC"""
    start, _, end = entity.angles(3)
    arc_size = (end - start + 360.0) % 360.0
    return CenterArc(entity.dxf.center, entity.dxf.radius, start, arc_size)


def process_circle(entity: DXFGraphic) -> Circle:
    """Convert CIRCLE"""
    return Circle(entity.dxf.radius).edge().moved(Pos(*entity.dxf.center))


def process_ellipse(entity: DXFGraphic) -> EllipticalCenterArc:
    """Convert ELLIPSE"""
    center = entity.dxf.center
    major_axis = entity.dxf.major_axis
    x_radius = (major_axis[0] ** 2 + major_axis[1] ** 2) ** 0.5
    y_radius = x_radius * entity.dxf.ratio
    rotation = math.degrees(math.atan2(major_axis[1], major_axis[0]))
    start_angle = math.degrees(entity.dxf.start_param)
    arc_size = math.degrees(entity.dxf.end_param - entity.dxf.start_param)
    arc_size = (arc_size + 360.0) % 360.0

    return EllipticalCenterArc(
        center=center,
        x_radius=x_radius,
        y_radius=y_radius,
        start_angle=start_angle,
        arc_size=arc_size,
        rotation=rotation,
    )


def process_insert(entity, doc):
    """Process INSERT by referencing block definition and applying transformations."""
    block_name = entity.dxf.name
    insert_point = Vector(entity.dxf.insert)
    scale_factors = (
        entity.dxf.xscale,
        entity.dxf.yscale,
        entity.dxf.zscale if entity.dxf.zscale != 0 else 1.0,
    )
    rotation_angle = entity.dxf.rotation
    column_count = entity.dxf.column_count
    row_count = entity.dxf.row_count
    column_spacing = entity.dxf.column_spacing
    row_spacing = entity.dxf.row_spacing

    # Retrieve the block definition
    block = doc.blocks.get(block_name)
    block_base_point = Vector(block.block.dxf.base_point)
    transformed_entities = []

    # Process each entity in the block definition
    for block_entity in block:
        for entity_object in _process_entity(block_entity, doc):
            for row_index in range(row_count):
                for column_index in range(column_count):
                    array_offset = Vector(
                        column_index * column_spacing,
                        row_index * row_spacing,
                        0,
                    )
                    array_offset = Vector(
                        array_offset.X * scale_factors[0],
                        array_offset.Y * scale_factors[1],
                        array_offset.Z * scale_factors[2],
                    ).rotate(Axis.Z, rotation_angle)
                    # INSERT places the block definition base point at insert_point.
                    # Normalize block geometry to that local origin before scaling/rotation.
                    transformed_entity = entity_object.translate(-block_base_point)
                    transformed_entity = scale(transformed_entity, scale_factors)
                    transformed_entity = transformed_entity.rotate(
                        Axis.Z, rotation_angle
                    )
                    transformed_entity = transformed_entity.translate(
                        insert_point + array_offset
                    )
                    transformed_entities.append(transformed_entity)

    return ShapeList(transformed_entities)


def process_line(entity: DXFGraphic) -> Line | None:
    """Convert LINE"""
    start, end = Vector(*entity.dxf.start), Vector(*entity.dxf.end)
    if (start - end).length < TOLERANCE:
        warnings.warn("Skipping degenerate LINE", stacklevel=3)
        return None
    return Line(start, end)


def process_lwpolyline(entity: DXFGraphic) -> Edge | Wire | None:
    """Convert LWPOLYLINE"""
    elevation = entity.dxf.elevation
    # elevation could be a vector or just a single value
    try:
        z_value = elevation.z
    except AttributeError:
        z_value = elevation

    points = entity.get_points("xyb")
    if len(points) < 2:
        warnings.warn("Skipping degenerate LWPOLYLINE", stacklevel=3)
        return None
    return _convert_bulge_polyline(points, entity.closed, z_value, "LWPOLYLINE")


def process_point(entity: DXFGraphic) -> Vertex:
    """Convert POINT"""
    point = entity.dxf.location
    return Vertex(point[0], point[1], point[2])


def process_polyline(entity: DXFGraphic) -> Edge | Wire | None:
    """Convert 2D POLYLINE - a collection of LINE and ARC segments."""
    if entity.get_mode() != "AcDb2dPolyline":
        raise ValueError(f"Unsupported POLYLINE mode: {entity.get_mode()}")

    vertices = list(entity.vertices)
    if len(vertices) < 2:
        warnings.warn("Skipping degenerate POLYLINE", stacklevel=3)
        return None
    # Note: the bulge data is not a z value - processed by _convert_bulge_polyline
    points = [
        (
            cast(float, vertex.dxf.location.x),
            cast(float, vertex.dxf.location.y),
            cast(float, vertex.dxf.get("bulge", 0)),
        )
        for vertex in vertices
    ]
    z_value = vertices[0].dxf.location.z
    return _convert_bulge_polyline(points, entity.is_closed, z_value, "POLYLINE")


def _convert_bulge_polyline(
    points: list[tuple[float, float, float]], closed: bool, z_value: float, label: str
) -> Edge | Wire | None:
    """Convert a 2D polyline described by vertices with optional bulge values."""
    edges = []
    segment_count = len(points) if closed else len(points) - 1

    for i in range(segment_count):
        start_data = points[i]
        end_data = points[(i + 1) % len(points)]
        start_point = (start_data[0], start_data[1], z_value)
        end_point = (end_data[0], end_data[1], z_value)
        bulge = start_data[2] if len(start_data) > 2 else 0

        if math.dist(start_point, end_point) < TOLERANCE:
            continue

        if abs(bulge) < TOLERANCE:
            edge = Line(start_point, end_point)
        else:
            sagitta = bulge * math.dist(start_point, end_point) / 2
            edge = SagittaArc(start_point, end_point, sagitta)
        edges.append(edge)

    if not edges:
        warnings.warn(f"Skipping degenerate {label}", stacklevel=3)
        return None
    if len(edges) == 1:
        return edges[0]
    return Wire(edges=edges)


def _convert_hatch_edge(edge, z_value: float) -> Edge:
    """Convert a hatch edge-path edge into build123d geometry."""
    if isinstance(edge, LineEdge):
        return Line(
            (edge.start.x, edge.start.y, z_value), (edge.end.x, edge.end.y, z_value)
        )
    if isinstance(edge, ArcEdge):
        arc_size = edge.end_angle - edge.start_angle
        if not edge.ccw:
            arc_size = -arc_size
        return CenterArc(
            (edge.center.x, edge.center.y, z_value),
            edge.radius,
            start_angle=edge.start_angle,
            arc_size=arc_size,
        )
    if isinstance(edge, EllipseEdge):
        major_axis = Vector(edge.major_axis.x, edge.major_axis.y, 0)
        x_radius = major_axis.length
        rotation = math.degrees(math.atan2(major_axis.Y, major_axis.X))
        arc_size = edge.end_angle - edge.start_angle
        if not edge.ccw:
            arc_size = -arc_size
        return EllipticalCenterArc(
            center=(edge.center.x, edge.center.y, z_value),
            x_radius=x_radius,
            y_radius=x_radius * edge.ratio,
            start_angle=edge.start_angle,
            arc_size=arc_size,
            rotation=rotation,
        )
    if isinstance(edge, SplineEdge):
        return BSpline(
            control_points=[(p[0], p[1], z_value) for p in edge.control_points],
            knots=edge.knot_values,
            degree=edge.degree,
            weights=edge.weights if edge.weights else None,
            periodic=bool(edge.periodic),
        )
    raise ValueError(f"Unsupported HATCH edge type: {type(edge).__name__}")


def process_hatch(entity: DXFGraphic) -> ShapeList[Edge | Wire]:
    """Convert HATCH by importing only its perimeter boundary paths."""
    elevation = entity.dxf.elevation
    try:
        z_value = elevation.z
    except AttributeError:
        z_value = elevation

    boundaries: ShapeList[Edge | Wire] = ShapeList()
    for path in entity.paths.rendering_paths(entity.dxf.hatch_style):
        if isinstance(path, PolylinePath):
            boundary = _convert_bulge_polyline(
                path.vertices, path.is_closed, z_value, "HATCH"
            )
        elif isinstance(path, EdgePath):
            edges = [_convert_hatch_edge(edge, z_value) for edge in path.edges]
            if not edges:
                continue
            boundary = edges[0] if len(edges) == 1 else Wire(edges=edges)
        else:
            warnings.warn(
                f"Unsupported HATCH boundary path: {type(path).__name__}", stacklevel=3
            )
            continue

        if boundary is not None:
            boundaries.append(boundary)

    return boundaries


def process_solid_trace_3dface(entity: DXFGraphic):
    """Convert filled objects - i.e. Faces"""
    # Gather vertices as a list of (x, y, z) tuples
    vertices = []
    for i in range(4):
        # Some entities like SOLID or TRACE may define only 3 vertices, repeating the last one
        # if the fourth vertex is not defined.
        try:
            vertex = entity.dxf.get(f"v{i}")
            vertices.append((vertex.x, vertex.y, vertex.z))
        except AttributeError:
            break

    # Create the Polygon object
    polygon_obj = Polygon(*vertices)
    return polygon_obj


def process_spline(entity: DXFGraphic) -> Edge:
    """Convert SPLINE"""
    control_points = list(entity.control_points)
    fit_points = list(entity.fit_points)
    knots = list(entity.knots)
    weights = list(entity.weights)
    degree = entity.dxf.degree
    periodic = bool(entity.dxf.flags & 2)

    if control_points and knots:
        return BSpline(
            control_points=control_points,
            knots=knots,
            degree=degree,
            weights=weights if weights else None,
            periodic=periodic,
        )

    start_tangent = entity.dxf.get("start_tangent")
    end_tangent = entity.dxf.get("end_tangent")
    if fit_points:
        tangents: tuple[VectorLike, ...] = ()
        if start_tangent is not None and end_tangent is not None:
            tangents = (start_tangent, end_tangent)
        return Spline(*fit_points, tangents=tangents)

    raise ValueError("Unsupported SPLINE entity: missing control points and knots")


def process_text(entity: DXFGraphic) -> Text:
    """Convert TEXT."""
    v_alignment = {
        0: TextAlign.BOTTOM,  # baseline approximation
        1: TextAlign.BOTTOM,
        2: TextAlign.CENTER,
        3: TextAlign.TOP,
    }
    h_alignment = {
        0: TextAlign.LEFT,
        1: TextAlign.CENTER,
        2: TextAlign.RIGHT,
        3: TextAlign.LEFT,  # aligned
        4: TextAlign.CENTER,  # middle
        5: TextAlign.LEFT,  # fit
    }

    position = entity.dxf.insert
    if (entity.dxf.halign != 0 or entity.dxf.valign != 0) and entity.dxf.hasattr(
        "align_point"
    ):
        position = entity.dxf.align_point

    return Text(
        entity.dxf.text,
        font_size=entity.dxf.height,
        rotation=entity.dxf.get("rotation", 0),
        text_align=(
            h_alignment.get(entity.dxf.halign, TextAlign.LEFT),
            v_alignment.get(entity.dxf.valign, TextAlign.BOTTOM),
        ),
    ).moved(Pos(*position))


def process_mtext(entity: DXFGraphic) -> Text:
    """Convert MTEXT."""
    attachment_align = {
        1: (TextAlign.LEFT, TextAlign.TOPFIRSTLINE),
        2: (TextAlign.CENTER, TextAlign.TOPFIRSTLINE),
        3: (TextAlign.RIGHT, TextAlign.TOPFIRSTLINE),
        4: (TextAlign.LEFT, TextAlign.CENTER),
        5: (TextAlign.CENTER, TextAlign.CENTER),
        6: (TextAlign.RIGHT, TextAlign.CENTER),
        7: (TextAlign.LEFT, TextAlign.BOTTOM),
        8: (TextAlign.CENTER, TextAlign.BOTTOM),
        9: (TextAlign.RIGHT, TextAlign.BOTTOM),
    }

    if hasattr(entity, "plain_text"):
        content = entity.plain_text()
    else:
        content = entity.text

    return Text(
        content,
        font_size=entity.dxf.char_height,
        rotation=entity.dxf.get("rotation", 0),
        text_align=attachment_align.get(
            entity.dxf.attachment_point,
            (TextAlign.LEFT, TextAlign.TOPFIRSTLINE),
        ),
    ).moved(Pos(*entity.dxf.insert))


# Dispatch dictionary mapping entity types to processing functions
entity_dispatch: dict[str, Callable] = {
    "3DFACE": process_solid_trace_3dface,
    "ARC": process_arc,
    "CIRCLE": process_circle,
    "ELLIPSE": process_ellipse,
    "HATCH": process_hatch,
    "INSERT": process_insert,
    "LINE": process_line,
    "LWPOLYLINE": process_lwpolyline,
    "MTEXT": process_mtext,
    "POINT": process_point,
    "POLYLINE": process_polyline,
    "SOLID": process_solid_trace_3dface,
    "SPLINE": process_spline,
    "TEXT": process_text,
    "TRACE": process_solid_trace_3dface,
}


def _flatten_import_result(new_object) -> list[Shape]:
    """Normalize handler results into a flat list of shapes."""
    if new_object is None:
        return []
    if isinstance(new_object, ShapeList):
        return [obj for obj in new_object if obj is not None]
    if isinstance(new_object, list):
        return [obj for obj in new_object if obj is not None]
    return [new_object]


def _process_entity(entity, doc) -> list[Shape]:
    """Convert a single DXF entity into zero or more build123d shapes."""
    dxftype = entity.dxftype()
    if dxftype not in entity_dispatch:
        warnings.warn(f"Unable to convert {dxftype}", stacklevel=3)
        return []

    if dxftype == "INSERT":
        new_object = entity_dispatch[dxftype](entity, doc)
    else:
        new_object = entity_dispatch[dxftype](entity)
    return _flatten_import_result(new_object)


def import_dxf(dxf_file: str | PathLike | TextIO | BinaryIO) -> ShapeList:
    """Import shapes from a DXF file

    Args:
        dxf_file (str | PathLike | TextIO | BinaryIO): dxf file path or readable stream

    Raises:
        DXFStructureError: file not found

    Returns:
        ShapeList: build123d objects
    """
    try:
        if isinstance(dxf_file, (str, PathLike)):
            doc = ezdxf.readfile(dxf_file)
        elif isinstance(dxf_file, TextIOBase):
            doc = ezdxf.read(dxf_file)
        elif isinstance(dxf_file, BytesIO) or hasattr(dxf_file, "read"):
            data = dxf_file.read()
            text = data.decode("latin1") if isinstance(data, bytes) else data
            doc = ezdxf.read(StringIO(text))
        else:
            raise TypeError(f"Unsupported DXF input type: {type(dxf_file).__name__}")
    except ezdxf.DXFStructureError as exc:
        raise ValueError(f"Failed to read {dxf_file}") from exc
    build123d_objects = []

    # Iterate over all entities in the model space
    for entity in doc.modelspace():
        build123d_objects.extend(_process_entity(entity, doc))

    return ShapeList(build123d_objects)
