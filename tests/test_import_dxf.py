"""
Tests for the DXF importer

name: test_import_dxf.py
by:   Gumyr
date: May 7 2026

desc:
    This python module tests the dxf importer.

license:

    Copyright 2026 Gumyr

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

from __future__ import annotations

import importlib
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from build123d import import_dxf
from build123d.build_enums import TextAlign
from build123d.objects_curve import (
    BSpline,
    CenterArc,
    EllipticalCenterArc,
    Line,
    SagittaArc,
)
from build123d.objects_sketch import Polygon, Text
from build123d.topology import Edge, Vertex, Wire


@pytest.fixture(scope="module")
def tests_dir() -> Path:
    """Reference the main tests directory."""
    return Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def dxf_dir(tests_dir: Path) -> Path:
    """Reference DXF fixtures stored under the tests directory."""
    return tests_dir / "dxf"


@pytest.fixture(scope="module")
def import_dxf_module():
    """Load the importer module so helper functions can be tested directly."""
    return importlib.import_module("build123d.import_dxf")


# Input contract


def test_import_empty(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "empty.dxf"))
    assert len(result) == 0


def test_import_empty_from_text_stream(dxf_dir: Path):
    dxf_text = (dxf_dir / "empty.dxf").read_text(encoding="latin1")
    result = import_dxf(StringIO(dxf_text))
    assert len(result) == 0


def test_import_empty_from_binary_stream(dxf_dir: Path):
    dxf_bytes = (dxf_dir / "empty.dxf").read_bytes()
    result = import_dxf(BytesIO(dxf_bytes))
    assert len(result) == 0


def test_import_unsupported_input_type():
    with pytest.raises(TypeError, match="Unsupported DXF input type"):
        import_dxf(1.23)  # type: ignore[arg-type]


def test_import_invalid_dxf_raises_value_error():
    with pytest.raises(ValueError, match="Failed to read"):
        import_dxf(StringIO("not a dxf"))


# Core entity fixtures


def test_import_lines(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "lines.dxf"))
    assert len(result) == 11
    assert all(isinstance(obj, Line) for obj in result)


def test_import_points(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "points.dxf"))
    assert len(result) == 2
    assert all(isinstance(obj, Vertex) for obj in result)
    assert tuple(result[0]) == (10.0, 20.0, 0.0)
    assert tuple(result[1]) == (30.0, 10.0, 0.0)


def test_import_lwpolylines(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "lwpolylines.dxf"))
    assert len(result) == 2
    assert all(isinstance(obj, Wire) for obj in result)

    assert result[0].is_closed
    assert len(result[0].edges()) == 4

    assert not result[1].is_closed
    assert len(result[1].edges()) == 6


def test_import_circles_ellipses_arcs(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "circlesellipsesarcs.dxf"))
    assert len(result) == 5
    assert sum(isinstance(obj, EllipticalCenterArc) for obj in result) == 2
    assert sum(isinstance(obj, CenterArc) for obj in result) == 2
    assert sum(type(obj) is Edge for obj in result) == 1


def test_import_single_spline(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "splineA.dxf"))
    assert len(result) == 1
    assert isinstance(result[0], BSpline)


def test_import_multiple_splines(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "splines.dxf"))
    assert len(result) == 2
    assert all(isinstance(obj, BSpline) for obj in result)


def test_import_polylines(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "polylines.dxf"))
    assert len(result) == 2
    assert all(isinstance(obj, Wire) for obj in result)
    assert all(obj.is_closed for obj in result)
    assert [len(obj.edges()) for obj in result] == [8, 8]


def test_import_rectangle_polyline(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "rectangle.dxf"))
    assert len(result) == 1
    assert isinstance(result[0], Wire)
    assert result[0].is_closed
    assert len(result[0].edges()) == 4


def test_import_square_and_circle(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "squareandcircle.dxf"))
    assert len(result) == 2
    assert sum(type(obj) is Edge for obj in result) == 1
    assert sum(isinstance(obj, Wire) for obj in result) == 1


def test_import_hatch_perimeter(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "hatches.dxf"))
    assert len(result.wires()) == 1


def test_import_mtext(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "texts.dxf"))
    assert len(result) == 2
    assert all(isinstance(obj, Text) for obj in result)
    assert result[0].text_align == (TextAlign.LEFT, TextAlign.TOPFIRSTLINE)
    assert result[1].text_align == (TextAlign.LEFT, TextAlign.BOTTOM)


# Regression fixtures


def test_import_blocks(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "blocks1.dxf"))
    assert len(result) == 10
    assert all(hasattr(obj, "bounding_box") for obj in result)


def test_import_closed_lwpolyline_block(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "closedlwpolylinebug.dxf"))
    assert len(result) == 1
    bbox = result[0].bounding_box()
    assert round(bbox.min.X, 5) == 30.0
    assert round(bbox.min.Y, 5) == 40.0
    assert round(bbox.max.X, 5) == 50.0
    assert round(bbox.max.Y, 5) == 70.0


def test_import_text_and_block_mtext(dxf_dir: Path):
    result = import_dxf(str(dxf_dir / "blocks2.dxf"))
    assert len(result) == 14
    assert sum(isinstance(obj, Text) for obj in result) == 1
    assert sum(type(obj).__name__ in {"Text", "Sketch"} for obj in result) == 3


# Unit branch coverage


def test_process_line_degenerate(import_dxf_module):
    entity = SimpleNamespace(dxf=SimpleNamespace(start=(0, 0, 0), end=(0, 0, 0)))
    with pytest.warns(UserWarning, match="Skipping degenerate LINE"):
        assert import_dxf_module.process_line(entity) is None


def test_process_lwpolyline_degenerate(import_dxf_module):
    entity = SimpleNamespace(
        dxf=SimpleNamespace(elevation=0.0),
        get_points=lambda _: [(0.0, 0.0, 0.0)],
    )
    with pytest.warns(UserWarning, match="Skipping degenerate LWPOLYLINE"):
        assert import_dxf_module.process_lwpolyline(entity) is None


def test_process_polyline_bad_mode(import_dxf_module):
    entity = SimpleNamespace(get_mode=lambda: "AcDb3dPolyline")
    with pytest.raises(ValueError, match="Unsupported POLYLINE mode"):
        import_dxf_module.process_polyline(entity)


def test_process_polyline_degenerate(import_dxf_module):
    vertex = SimpleNamespace(
        dxf=SimpleNamespace(location=SimpleNamespace(x=0, y=0, z=0))
    )
    entity = SimpleNamespace(
        get_mode=lambda: "AcDb2dPolyline",
        vertices=[vertex],
    )
    with pytest.warns(UserWarning, match="Skipping degenerate POLYLINE"):
        assert import_dxf_module.process_polyline(entity) is None


def test_convert_bulge_polyline_single_edge(import_dxf_module):
    edge = import_dxf_module._convert_bulge_polyline(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)], False, 0.0, "TEST"
    )
    assert isinstance(edge, Line)


def test_convert_bulge_polyline_sagitta_arc(import_dxf_module):
    edge = import_dxf_module._convert_bulge_polyline(
        [(0.0, 0.0, 1.0), (2.0, 0.0, 0.0)], False, 0.0, "TEST"
    )
    assert isinstance(edge, SagittaArc)


def test_convert_bulge_polyline_degenerate(import_dxf_module):
    with pytest.warns(UserWarning, match="Skipping degenerate TEST"):
        result = import_dxf_module._convert_bulge_polyline(
            [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)], False, 0.0, "TEST"
        )
    assert result is None


def test_process_spline_fit_points_fallback(import_dxf_module):
    entity = SimpleNamespace(
        control_points=[],
        fit_points=[(0, 0, 0), (1, 1, 0), (2, 0, 0)],
        knots=[],
        weights=[],
        dxf=SimpleNamespace(
            degree=3,
            flags=0,
            get=lambda key: (1, 0, 0) if key == "start_tangent" else (-1, 0, 0),
        ),
    )
    result = import_dxf_module.process_spline(entity)
    assert result.geom_type.name == "BSPLINE"
    assert tuple(result.start_point()) == (0.0, 0.0, 0.0)
    assert tuple(result.end_point()) == (2.0, 0.0, 0.0)


def test_process_spline_invalid(import_dxf_module):
    entity = SimpleNamespace(
        control_points=[],
        fit_points=[],
        knots=[],
        weights=[],
        dxf=SimpleNamespace(degree=3, flags=0, get=lambda _key: None),
    )
    with pytest.raises(ValueError, match="Unsupported SPLINE entity"):
        import_dxf_module.process_spline(entity)


def test_process_text_uses_align_point(import_dxf_module):
    entity = SimpleNamespace(
        dxf=SimpleNamespace(
            text="Aligned",
            height=2.0,
            halign=1,
            valign=3,
            insert=(0.0, 0.0, 0.0),
            align_point=(5.0, 6.0, 0.0),
            get=lambda key, default=0: 0 if key == "rotation" else default,
            hasattr=lambda key: key == "align_point",
        )
    )
    result = import_dxf_module.process_text(entity)
    assert isinstance(result, Text)
    assert tuple(result.location.position) == (5.0, 6.0, 0.0)
    assert result.text_align == (TextAlign.CENTER, TextAlign.TOP)


def test_process_hatch_unsupported_path_warning(import_dxf_module):
    unsupported_path = object()
    entity = SimpleNamespace(
        dxf=SimpleNamespace(elevation=0.0, hatch_style=0),
        paths=SimpleNamespace(rendering_paths=lambda _style: [unsupported_path]),
    )
    with pytest.warns(UserWarning, match="Unsupported HATCH boundary path"):
        result = import_dxf_module.process_hatch(entity)
    assert len(result) == 0


def test_process_hatch_edgepath_single_line(import_dxf_module, monkeypatch):
    class FakeLineEdge:
        pass

    class FakeEdgePath:
        pass

    monkeypatch.setattr(import_dxf_module, "LineEdge", FakeLineEdge)
    monkeypatch.setattr(import_dxf_module, "EdgePath", FakeEdgePath)

    line_edge = FakeLineEdge()
    line_edge.start = SimpleNamespace(x=0.0, y=0.0)
    line_edge.end = SimpleNamespace(x=1.0, y=0.0)
    edge_path = FakeEdgePath()
    edge_path.edges = [line_edge]
    entity = SimpleNamespace(
        dxf=SimpleNamespace(elevation=0.0, hatch_style=0),
        paths=SimpleNamespace(rendering_paths=lambda _style: [edge_path]),
    )
    result = import_dxf_module.process_hatch(entity)
    assert len(result) == 1
    assert isinstance(result[0], Line)


def test_process_hatch_polyline_path(import_dxf_module, monkeypatch):
    class FakePolylinePath:
        def __init__(self):
            self.vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]
            self.is_closed = False

    monkeypatch.setattr(import_dxf_module, "PolylinePath", FakePolylinePath)

    entity = SimpleNamespace(
        dxf=SimpleNamespace(elevation=0.0, hatch_style=0),
        paths=SimpleNamespace(rendering_paths=lambda _style: [FakePolylinePath()]),
    )
    result = import_dxf_module.process_hatch(entity)
    assert len(result) == 1
    assert isinstance(result[0], Wire)


def test_process_hatch_edgepath_empty(import_dxf_module, monkeypatch):
    class FakeEdgePath:
        def __init__(self):
            self.edges = []

    monkeypatch.setattr(import_dxf_module, "EdgePath", FakeEdgePath)

    entity = SimpleNamespace(
        dxf=SimpleNamespace(elevation=0.0, hatch_style=0),
        paths=SimpleNamespace(rendering_paths=lambda _style: [FakeEdgePath()]),
    )
    result = import_dxf_module.process_hatch(entity)
    assert len(result) == 0


def test_convert_hatch_edge_arc(import_dxf_module, monkeypatch):
    class FakeArcEdge:
        pass

    monkeypatch.setattr(import_dxf_module, "ArcEdge", FakeArcEdge)

    edge = FakeArcEdge()
    edge.center = SimpleNamespace(x=1.0, y=2.0)
    edge.radius = 3.0
    edge.start_angle = 10.0
    edge.end_angle = 70.0
    edge.ccw = True

    result = import_dxf_module._convert_hatch_edge(edge, 0.0)
    assert isinstance(result, CenterArc)
    assert tuple(result.arc_center) == (1.0, 2.0, 0.0)


def test_convert_hatch_edge_arc_clockwise(import_dxf_module, monkeypatch):
    class FakeArcEdge:
        pass

    monkeypatch.setattr(import_dxf_module, "ArcEdge", FakeArcEdge)

    edge = FakeArcEdge()
    edge.center = SimpleNamespace(x=1.0, y=2.0)
    edge.radius = 3.0
    edge.start_angle = 10.0
    edge.end_angle = 70.0
    edge.ccw = False

    result = import_dxf_module._convert_hatch_edge(edge, 0.0)
    assert isinstance(result, CenterArc)
    assert tuple(result.arc_center) == (1.0, 2.0, 0.0)
    assert result.length > 0


def test_convert_hatch_edge_ellipse(import_dxf_module, monkeypatch):
    class FakeEllipseEdge:
        pass

    monkeypatch.setattr(import_dxf_module, "EllipseEdge", FakeEllipseEdge)

    edge = FakeEllipseEdge()
    edge.center = SimpleNamespace(x=1.0, y=2.0)
    edge.major_axis = SimpleNamespace(x=4.0, y=0.0)
    edge.ratio = 0.5
    edge.start_angle = 0.0
    edge.end_angle = 90.0
    edge.ccw = True

    result = import_dxf_module._convert_hatch_edge(edge, 0.0)
    assert isinstance(result, EllipticalCenterArc)
    assert tuple(result.arc_center) == (1.0, 2.0, 0.0)


def test_convert_hatch_edge_ellipse_clockwise(import_dxf_module, monkeypatch):
    class FakeEllipseEdge:
        pass

    monkeypatch.setattr(import_dxf_module, "EllipseEdge", FakeEllipseEdge)

    edge = FakeEllipseEdge()
    edge.center = SimpleNamespace(x=1.0, y=2.0)
    edge.major_axis = SimpleNamespace(x=4.0, y=0.0)
    edge.ratio = 0.5
    edge.start_angle = 0.0
    edge.end_angle = 90.0
    edge.ccw = False

    result = import_dxf_module._convert_hatch_edge(edge, 0.0)
    assert isinstance(result, EllipticalCenterArc)
    assert tuple(result.arc_center) == (1.0, 2.0, 0.0)
    assert result.length > 0


def test_convert_hatch_edge_spline(import_dxf_module, monkeypatch):
    class FakeSplineEdge:
        pass

    monkeypatch.setattr(import_dxf_module, "SplineEdge", FakeSplineEdge)

    edge = FakeSplineEdge()
    edge.control_points = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]
    edge.knot_values = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
    edge.degree = 2
    edge.weights = []
    edge.periodic = 0

    result = import_dxf_module._convert_hatch_edge(edge, 0.0)
    assert isinstance(result, BSpline)


def test_convert_hatch_edge_unsupported(import_dxf_module):
    with pytest.raises(ValueError, match="Unsupported HATCH edge type"):
        import_dxf_module._convert_hatch_edge(object(), 0.0)


def test_process_solid_trace_3dface(import_dxf_module):
    vertices = {
        "v0": SimpleNamespace(x=0.0, y=0.0, z=0.0),
        "v1": SimpleNamespace(x=1.0, y=0.0, z=0.0),
        "v2": SimpleNamespace(x=1.0, y=1.0, z=0.0),
        "v3": SimpleNamespace(x=0.0, y=1.0, z=0.0),
    }
    entity = SimpleNamespace(dxf=SimpleNamespace(get=lambda key: vertices[key]))
    result = import_dxf_module.process_solid_trace_3dface(entity)
    assert isinstance(result, Polygon)
    assert len(result.vertices()) == 4


def test_process_solid_trace_3dface_three_vertices(import_dxf_module):
    vertices = {
        "v0": SimpleNamespace(x=0.0, y=0.0, z=0.0),
        "v1": SimpleNamespace(x=1.0, y=0.0, z=0.0),
        "v2": SimpleNamespace(x=0.0, y=1.0, z=0.0),
    }

    def get_vertex(key):
        if key not in vertices:
            raise AttributeError
        return vertices[key]

    entity = SimpleNamespace(dxf=SimpleNamespace(get=get_vertex))
    result = import_dxf_module.process_solid_trace_3dface(entity)
    assert isinstance(result, Polygon)
    assert len(result.vertices()) == 3


def test_process_mtext_text_fallback(import_dxf_module):
    entity = SimpleNamespace(
        text="Fallback",
        dxf=SimpleNamespace(
            char_height=2.0,
            attachment_point=7,
            insert=(1.0, 2.0, 0.0),
            get=lambda key, default=0: 0 if key == "rotation" else default,
        ),
    )
    result = import_dxf_module.process_mtext(entity)
    assert isinstance(result, Text)
    assert result.txt == "Fallback"


def test_flatten_import_result(import_dxf_module):
    assert import_dxf_module._flatten_import_result(None) == []
    assert len(import_dxf_module._flatten_import_result([None, Vertex(0, 0, 0)])) == 1
    assert (
        len(
            import_dxf_module._flatten_import_result(
                import_dxf_module.ShapeList([Vertex(0, 0, 0)])
            )
        )
        == 1
    )


def test_process_entity_unsupported_warning(import_dxf_module):
    entity = SimpleNamespace(dxftype=lambda: "NOPE")
    with pytest.warns(UserWarning, match="Unable to convert NOPE"):
        result = import_dxf_module._process_entity(entity, doc=None)
    assert result == []


# Integration fixtures


@pytest.mark.parametrize(
    "filename",
    [
        "dxf/test-conic-section.dxf",
        "dxf/test-circle-rotation.dxf",
        "dxf/test-sketch.dxf",
        "dxf/test-drawing.dxf",
        "dxf/test-angled-section.dxf",
        "dxf/test-ellipse-rotation.dxf",
        "dxf/diamond.dxf",
        "dxf/test_export.dxf",
        "dxf/accumulatortest.dxf",
        "dxf/shaft_simple.dxf",
        "dxf/layers.dxf",
        "dxf/bridge.dxf",
        "dxf/output.dxf",
        "dxf/ellipticalarcs.dxf",
        "dxf/ellipticalarcs2.dxf",
        "dxf/cube.dxf",
    ],
)
def test_import_integration_fixtures(filename: str, tests_dir: Path):
    result = import_dxf(str(tests_dir / filename))
    assert len(result) > 0
