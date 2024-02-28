import unittest
import math
from typing import Union, Iterable
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
    BuildPart,
    Part,
    Cone,
    extrude,
    add,
    mirror,
    section,
)
from build123d.exporters import ExportSVG, ExportDXF, Drawing, LineType


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
            add(ExportersTestCase.create_test_sketch())
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
        white = (255, 255, 255)
        black = (0, 0, 0)
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

if __name__ == "__main__":
    unittest.main()
