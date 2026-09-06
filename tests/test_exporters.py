from io import BytesIO
from os import fsdecode, fsencode
from typing import Union, Iterable
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import PropertyMock, patch

import pytest

from build123d import (
    Color,
    Mode,
    Shape,
    Plane,
    Locations,
    BuildLine,
    Line,
    Bezier,
    RadiusArc,
    BuildSketch,
    Sketch,
    make_face,
    RegularPolygon,
    Circle,
    PolarLocations,
    Rectangle,
    BuildPart,
    Edge,
    Face,
    Part,
    Cone,
    extrude,
    insert,
    mirror,
    section,
    Pos,
    Rot,
    Spline,
    ThreePointArc,
    Unit,
    Wire,
)
from build123d.exporters import ColorIndex, ExportSVG, ExportDXF, Drawing, LineType
from ezdxf.colors import RGB


class ExportersTestCase(unittest.TestCase):
    @staticmethod
    def create_test_sketch() -> Sketch:
        with BuildSketch() as sketchy:
            with BuildLine():
                Line((0, 0), (16, 0))
                Bezier((16, 0), (16, 8), (16, 8), (8, 8))
                RadiusArc((8, 8), (0, 0), -8, short_sagitta=True)
            make_face()
            with Locations((5, 4)):
                RegularPolygon(2, 4, mode=Mode.SUBTRACT)
            with Locations((11, 4)):
                Circle(2, mode=Mode.SUBTRACT)
        return sketchy.sketch

    @staticmethod
    def create_test_part() -> Part:
        with BuildPart() as party:
            insert(ExportersTestCase.create_test_sketch())
            extrude(amount=4)
        return party.part

    @staticmethod
    def basic_svg_export(
        shape: Union[Shape, Iterable[Shape]], filename: str, reverse: bool = False
    ):
        svg = ExportSVG()
        svg.add_shape(shape, reverse_wires=reverse)
        svg.write(filename)

    @staticmethod
    def basic_dxf_export(shape: Union[Shape, Iterable[Shape]], filename: str):
        dxf = ExportDXF()
        dxf.add_shape(shape)
        dxf.write(filename)

    @staticmethod
    def basic_combo_export(shape: Shape, filebase: str, reverse: bool = False):
        ExportersTestCase.basic_svg_export(shape, filebase + ".svg", reverse)
        ExportersTestCase.basic_dxf_export(shape, filebase + ".dxf")

    @staticmethod
    def drawing_combo_export(dwg: Drawing, filebase: str):
        svg = ExportSVG(line_weight=0.13)
        svg.add_layer("hidden", line_weight=0.09, line_type=LineType.HIDDEN)
        svg.add_shape(dwg.visible_lines)
        svg.add_shape(dwg.hidden_lines, layer="hidden")
        svg.write(filebase + ".svg")
        dxf = ExportDXF(line_weight=0.13)
        dxf.add_layer("hidden", line_weight=0.09, line_type=LineType.HIDDEN)
        dxf.add_shape(dwg.visible_lines)
        dxf.add_shape(dwg.hidden_lines, layer="hidden")
        dxf.write(filebase + ".dxf")

    def test_sketch(self):
        sketch = ExportersTestCase.create_test_sketch()
        ExportersTestCase.basic_combo_export(sketch, "test-sketch")

    def test_drawing(self):
        part = ExportersTestCase.create_test_part()
        drawing = Drawing(part)
        ExportersTestCase.drawing_combo_export(drawing, "test-drawing")

    def test_back_section_svg(self):
        """Export a section through the bottom face.
        This produces back facing wires to test the handling of
        winding order."""
        part = ExportersTestCase.create_test_part()
        test_section = section(part, Plane.XY, height=0)
        ExportersTestCase.basic_svg_export(
            test_section, "test-back-section.svg", reverse=True
        )

    def test_angled_section(self):
        """Export an angled section.
        This tests more slightly more complex geometry."""
        part = ExportersTestCase.create_test_part()
        angle = math.degrees(math.atan2(4, 8))
        section_plane = Plane.XY.rotated((angle, 0, 0))
        angled_section = section_plane.to_local_coords(section(part, section_plane))
        ExportersTestCase.basic_combo_export(angled_section, "test-angled-section")

    def test_cam_section_svg(self):
        """Export a section through the top face, with a simple
        CAM oriented layer setup."""
        part = ExportersTestCase.create_test_part()
        section_plane = Plane.XY.offset(4)
        cam_section = section_plane.to_local_coords(section(part, section_plane))
        svg = ExportSVG()
        white = "white"
        black = "black"
        svg.add_layer("exterior", line_color=black, fill_color=black)
        svg.add_layer("interior", line_color=black, fill_color=white)
        for f in cam_section.faces():
            svg.add_shape(f.outer_wire(), "exterior")
            svg.add_shape(f.inner_wires(), "interior")
        svg.write("test-cam-section.svg")

    def test_conic_section(self):
        """Export a conic section.  This tests a more "exotic" geometry
        type."""
        cone = Cone(8, 0, 16, align=None)
        section_plane = Plane.XZ.offset(4)
        conic_section = section_plane.to_local_coords(section(cone, section_plane))
        ExportersTestCase.basic_combo_export(conic_section, "test-conic-section")

    def test_circle_rotation(self):
        """Export faces with circular arcs in various orientations."""
        with BuildSketch() as sketch:
            Circle(20)
            Circle(8, mode=Mode.SUBTRACT)
            with PolarLocations(20, 5, 90):
                Circle(4, mode=Mode.SUBTRACT)
            mirror(about=Plane.XZ.offset(25))
        ExportersTestCase.basic_combo_export(sketch.faces(), "test-circle-rotation")

    def test_ellipse_rotation(self):
        """Export drawing with elliptical arcs in various orientations."""
        with BuildPart() as part:
            with BuildSketch(Plane.ZX):
                Circle(20)
                Circle(8, mode=Mode.SUBTRACT)
                with PolarLocations(20, 5, 90):
                    Circle(4, mode=Mode.SUBTRACT)
            extrude(amount=20, both=True)
            mirror(about=Plane.YZ.offset(25))
        drawing = Drawing(part.part)
        ExportersTestCase.drawing_combo_export(drawing, "test-ellipse-rotation")

    def test_color(self):
        """Export SVG with alpha transparency."""
        sketch = ExportersTestCase.create_test_sketch()
        svg = ExportSVG(
            line_weight=0.13,
            fill_color=Color("blue", 0.5),
            line_color=Color(0, 0, 0, 0.8),
        )
        svg.add_shape(sketch)
        svg.write("test-colors.svg")

    def test_svg_color_like(self):
        """ExportSVG accepts and normalizes the standard ColorLike interface."""
        svg = ExportSVG(fill_color="#ff000080", line_color=0x0000FF)
        layer = svg._layers[""]
        self.assertEqual(tuple(layer.fill_color), (1.0, 0.0, 0.0, 0.5019608))
        self.assertEqual(tuple(layer.line_color), (0.0, 0.0, 1.0, 1.0))

    def test_svg_shape_colors(self):
        """Face colors become fills and Edge/Wire colors become strokes."""
        face = Face.make_rect(2, 2)
        face.color = Color("red", 0.5)
        wire = Wire.make_circle(1)
        wire.color = "green"
        edge = Edge.make_line((0, 0), (1, 1))
        edge.color = "blue"

        svg = ExportSVG()
        svg.add_shape((face, wire, edge))
        face_element, wire_element, edge_element = svg._layers[""].elements

        self.assertEqual(face_element.get("fill"), "rgb(255,0,0)")
        self.assertEqual(face_element.get("fill-opacity"), "0.5")
        self.assertEqual(wire_element.get("stroke"), "rgb(0,128,0)")
        self.assertEqual(edge_element.get("stroke"), "rgb(0,0,255)")

    def test_svg_layer_colors_override_shape_colors(self):
        """Explicit SVG colors, including None, override shape colors."""
        face = Face.make_rect(2, 2)
        face.color = "red"
        edge = Edge.make_line((0, 0), (1, 1))
        edge.color = "blue"

        svg = ExportSVG(fill_color="yellow", line_color=None)
        svg.add_shape((face, edge))
        layer = svg._layers[""]
        self.assertNotIn("fill", layer.elements[0].attrib)
        self.assertNotIn("stroke", layer.elements[1].attrib)
        layer_group = svg._group_for_layer(layer)
        self.assertEqual(layer_group.get("fill"), "rgb(255,255,0)")
        self.assertEqual(layer_group.get("stroke"), "none")

    def test_svg_legacy_colors_are_deprecated(self):
        """Legacy SVG color inputs still convert while warning users."""
        with self.assertWarns(DeprecationWarning):
            indexed = ExportSVG(line_color=ColorIndex.RED)
        with self.assertWarns(DeprecationWarning):
            rgb = ExportSVG(line_color=RGB(0, 255, 0))
        with self.assertWarns(DeprecationWarning):
            tuple_rgb = ExportSVG(line_color=(0, 0, 255))

        self.assertEqual(tuple(indexed._layers[""].line_color), (1.0, 0.0, 0.0, 1.0))
        self.assertEqual(tuple(rgb._layers[""].line_color), (0.0, 1.0, 0.0, 1.0))
        self.assertEqual(tuple(tuple_rgb._layers[""].line_color), (0.0, 0.0, 1.0, 1.0))

    def test_svg_small_arc(self):
        pnts = ((0, 0), (0, 0.000001), (0.000001, 0))
        small_arc = ThreePointArc(pnts).scale(0.01)
        with self.assertWarns(UserWarning):
            svg_exporter = ExportSVG()
            segments = svg_exporter._circle_segments(small_arc.edges()[0], False)
            self.assertEqual(len(segments), 0, "Small arc should produce no segments")

    def test_svg_small_ellipse(self):
        pnts = ((0, 0), (0, 0.000001), (0.000002, 0))
        small_ellipse = ThreePointArc(pnts).scale(0.01)
        with self.assertWarns(UserWarning):
            svg_exporter = ExportSVG()
            segments = svg_exporter._ellipse_segments(small_ellipse.edges()[0], False)
            self.assertEqual(
                len(segments), 0, "Small ellipse should produce no segments"
            )


class ExportersValidationTestCase(unittest.TestCase):
    """Guards on the 2D exporters that reject unusable input."""

    def test_dxf_unsupported_unit(self):
        with self.assertRaisesRegex(ValueError, "unit `G` not supported"):
            ExportDXF(unit=Unit.G)

    def test_svg_unsupported_unit(self):
        with self.assertRaisesRegex(ValueError, "Invalid unit"):
            ExportSVG(unit=Unit.M)

    def test_dxf_unknown_linetype(self):
        dxf = ExportDXF()
        with self.assertRaisesRegex(ValueError, "Unknown linetype `NOT_A_LINETYPE`"):
            dxf._linetype(SimpleNamespace(value="NOT_A_LINETYPE"))

    def test_svg_unknown_linetype(self):
        svg = ExportSVG()
        with self.assertRaisesRegex(ValueError, "Unknown linetype `NOT_A_LINETYPE`"):
            svg.add_layer("dashes", line_type=SimpleNamespace(value="NOT_A_LINETYPE"))

    def test_svg_duplicate_layer(self):
        svg = ExportSVG()
        with self.assertRaisesRegex(ValueError, "Duplicate layer name"):
            svg.add_layer("")

    def test_svg_undefined_layer(self):
        svg = ExportSVG()
        with self.assertRaisesRegex(ValueError, "Undefined layer: missing"):
            svg.add_shape(Circle(1), layer="missing")

    def test_dxf_convert_point_bad_type(self):
        dxf = ExportDXF()
        with self.assertRaisesRegex(TypeError, "Got `tuple`"):
            dxf._convert_point((0, 0, 0))

    def test_svg_path_point_bad_type(self):
        svg = ExportSVG()
        with self.assertRaisesRegex(TypeError, "Got `tuple`"):
            svg._path_point((0, 0, 0))

    def test_svg_empty_edge(self):
        svg = ExportSVG()
        with self.assertRaisesRegex(ValueError, "Edge is empty"):
            svg._edge_segments(Edge(), False)

    def test_non_planar_shape_warns(self):
        """Both exporters flatten to 2D, so points off the XY plane are lost."""
        tilted = Pos(Z=5) * Rot(X=30) * Rectangle(10, 10)
        for exporter in (ExportDXF(), ExportSVG()):
            with self.subTest(exporter=type(exporter).__name__):
                with self.assertWarnsRegex(UserWarning, "non-planar shape"):
                    exporter.add_shape(tilted)

    def test_svg_nothing_to_export(self):
        with self.assertRaisesRegex(ValueError, "No shapes to export"):
            ExportSVG().write(BytesIO())

    def test_dxf_bspline_without_location(self):
        spline = Spline((0, 0), (5, 6), (10, 1)).edge()
        with patch.object(
            Edge, "location", new_callable=PropertyMock, return_value=None
        ):
            with self.assertRaisesRegex(ValueError, "Edge is empty"):
                ExportDXF()._convert_bspline(spline, {})

    def test_svg_bspline_without_location(self):
        spline = Spline((0, 0), (5, 6), (10, 1)).edge()
        with patch.object(
            Edge, "location", new_callable=PropertyMock, return_value=None
        ):
            with self.assertRaisesRegex(ValueError, "Edge is empty"):
                ExportSVG()._bspline_segments(spline, False)

    def test_svg_bspline_high_degree(self):
        """Edge.to_splines() normally reduces the curve to degree 3; without
        that reduction the Bézier conversion produces unusable segments."""
        edge = Edge.make_spline_approx(
            [(i, (i % 3) * 2.0) for i in range(12)], min_deg=5, max_deg=5
        )
        with patch.object(Edge, "to_splines", lambda self, **kwargs: self):
            with self.assertRaisesRegex(ValueError, "Surprising Bézier of degree 5"):
                ExportSVG()._bspline_segments(edge, False)


@pytest.mark.parametrize(
    "format",
    (Path, fsencode, fsdecode),
    ids=["path", "bytes", "str"],
)
@pytest.mark.parametrize("Exporter", (ExportSVG, ExportDXF))
def test_pathlike_exporters(tmp_path, format, Exporter):
    path = format(tmp_path / "file")
    sketch = ExportersTestCase.create_test_sketch()
    exporter = Exporter()
    exporter.add_shape(sketch)
    exporter.write(path)


@pytest.mark.parametrize("Exporter", (ExportSVG, ExportDXF))
def test_exporters_in_memory(Exporter):
    buffer = BytesIO()
    sketch = ExportersTestCase.create_test_sketch()
    exporter = Exporter()
    exporter.add_shape(sketch)
    exporter.write(buffer)


def test_dxf_in_memory_defaults_to_ascii():
    buffer = BytesIO()
    sketch = ExportersTestCase.create_test_sketch()
    exporter = ExportDXF()
    exporter.add_shape(sketch)
    exporter.write(buffer)

    data = buffer.getvalue()
    assert b"SECTION" in data
    assert not data.startswith(b"AutoCAD Binary DXF")


def test_dxf_in_memory_can_write_binary():
    buffer = BytesIO()
    sketch = ExportersTestCase.create_test_sketch()
    exporter = ExportDXF()
    exporter.add_shape(sketch)
    exporter.write(buffer, ascii_format=False)

    assert buffer.getvalue().startswith(b"AutoCAD Binary DXF")


if __name__ == "__main__":
    unittest.main()
