from io import StringIO
import os
import unittest
from build123d import (
    BuildLine,
    Color,
    Line,
    Bezier,
    RadiusArc,
)
from build123d.importers import import_svg_as_buildline_code, import_brep, import_svg
from build123d.exporters import ExportSVG
from build123d.build_enums import GeomType
from pathlib import Path


class ImportSVG(unittest.TestCase):
    def test_import_svg_as_buildline_code(self):
        # Create svg file
        with BuildLine() as test_obj:
            l1 = Bezier((0, 0), (0.25, -0.1), (0.5, -0.15), (1, 0))
            l2 = Line(l1 @ 1, (1, 1))
            l3 = RadiusArc(l2 @ 1, (0, 1), 2)
            l4 = Line(l3 @ 1, l1 @ 0)
        svg = ExportSVG()
        svg.add_shape(test_obj.wires()[0], "")
        svg.write("test.svg")

        # Read the svg as code
        buildline_code, builder_name = import_svg_as_buildline_code("test.svg")

        # Execute it and convert to Edges
        ex_locals = {}
        exec(buildline_code, None, ex_locals)
        test_obj: BuildLine = ex_locals[builder_name]
        found = 0
        for edge in test_obj.edges():
            if edge.geom_type == GeomType.BEZIER:
                found += 1
            elif edge.geom_type == GeomType.LINE:
                found += 1
            elif edge.geom_type == GeomType.ELLIPSE:
                found += 1
        self.assertEqual(found, 4)
        os.remove("test.svg")

    def test_import_svg_as_buildline_code_invalid_name(self):
        # Create svg file
        with BuildLine() as test_obj:
            l1 = Bezier((0, 0), (0.25, -0.1), (0.5, -0.15), (1, 0))
            l2 = Line(l1 @ 1, (1, 1))
            l3 = RadiusArc(l2 @ 1, (0, 1), 2)
            l4 = Line(l3 @ 1, l1 @ 0)
        svg = ExportSVG()
        svg.add_shape(test_obj.wires()[0], "")
        svg.write("test!.svg")

        # Read the svg as code
        buildline_code, builder_name = import_svg_as_buildline_code("test!.svg")
        os.remove("test!.svg")

        self.assertEqual(builder_name, "builder")

    def test_import_svg(self):
        svg_file = Path(__file__).parent / "../tests/svg_import_test.svg"
        for tag in ["id", "label"]:
            # Import the svg object as a ShapeList
            svg = import_svg(
                svg_file,
                label_by=tag,
                is_inkscape_label=tag == "label",
            )

            # Exact the shape of the plate & holes
            base_faces = svg.filter_by(lambda f: "base" in f.label)
            hole_faces = svg.filter_by(lambda f: "hole" in f.label)
            test_wires = svg.filter_by(lambda f: "wire" in f.label)

            self.assertEqual(len(list(base_faces)), 1)
            self.assertEqual(len(list(hole_faces)), 2)
            self.assertEqual(len(list(test_wires)), 1)

    def test_import_svg_colors(self):
        svg_file = StringIO(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect width="5" height="10" class="blue" fill="none" stroke="#0000ff"/>'
            '<rect width="8" height="4" class="red" fill="#ff0000"/>'
            '<rect width="12" height="3"/>'
            '<path d="M0,0 H10" fill="red" stroke="blue"/>'
            "</svg>"
        )
        svg = import_svg(svg_file)
        self.assertEqual(len(svg), 4)
        self.assertEqual(str(svg[0].color), str(Color(0, 0, 1, 1)))
        self.assertEqual(str(svg[1].color), str(Color(1, 0, 0, 1)))
        self.assertEqual(str(svg[2].color), str(Color(0, 0, 0, 1)))
        self.assertEqual(str(svg[3].color), str(Color(0, 0, 1, 1)))


class ImportBREP(unittest.TestCase):
    def test_bad_filename(self):
        with self.assertRaises(ValueError):
            import_brep("test.brep")


if __name__ == "__main__":
    unittest.main()
