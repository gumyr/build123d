
import unittest
import math
from typing import Any
from build123d import (
    Mode, Shape, Plane, Locations,
    BuildLine, Line, Bezier, RadiusArc,
    BuildSketch, Sketch, make_face, RegularPolygon, Circle,
    BuildPart, Part, Cone, extrude, add,
    section
)
from build123d.exporters import (
    ExportSVG, Drawing, LineType
)

class ExportersTestCase(unittest.TestCase):

    @staticmethod
    def create_test_sketch() -> Sketch:
        with BuildSketch() as sketchy:
            with BuildLine():
                Line((0, 0), (16, 0))
                Bezier((16,0), (16,8), (16,8), (8,8))
                RadiusArc((8,8), (0,0), -8, short_sagitta=True)
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
    def basic_svg_export(shape: Shape, filename: str, reverse: bool = False):
        svg = ExportSVG()
        svg.add_shape(shape, reverse_wires=reverse)
        svg.write(filename)

    def test_sketch_svg(self):
        sketch = ExportersTestCase.create_test_sketch()
        ExportersTestCase.basic_svg_export(sketch, "test-sketch.svg")

    def test_drawing_svg(self):
        part = ExportersTestCase.create_test_part()
        drawing = Drawing(part)
        svg = ExportSVG(line_weight=0.11)
        svg.add_layer("hidden", line_type=LineType.ISO_DOT)
        svg.add_shape(drawing.visible_lines)
        svg.add_shape(drawing.hidden_lines, layer='hidden')
        svg.write("test-drawing.svg")

    def test_back_section_svg(self):
        """Export a section through the bottom face.
        This produces back facing wires to test the handling of
        winding order."""
        part = ExportersTestCase.create_test_part()
        test_section = section(part, Plane.XY, height=0)
        ExportersTestCase.basic_svg_export(test_section, "test-back-section.svg", reverse=True)

    def test_angled_section_svg(self):
        """Export an angled section.
        This tests more slightly more complex geometry."""
        part = ExportersTestCase.create_test_part()
        angle = math.degrees(math.atan2(4, 8))
        section_plane = Plane.XY.rotated((angle, 0, 0))
        angled_section = section_plane.to_local_coords(section(part, section_plane))
        ExportersTestCase.basic_svg_export(angled_section, "test-angled-section.svg")

    def test_cam_section_svg(self):
        """ Export a section through the top face, with a simple
        CAM oriented layer setup."""
        part = ExportersTestCase.create_test_part()
        section_plane = Plane.XY.offset(4)
        cam_section = section_plane.to_local_coords(section(part, section_plane))
        svg = ExportSVG()
        white = (255,255,255)
        black = (0,0,0)
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
        ExportersTestCase.basic_svg_export(conic_section, "test-conic-section.svg")

