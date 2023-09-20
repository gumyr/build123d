import os
import unittest
from build123d import (
    BuildLine,
    Line,
    Bezier,
    RadiusArc,
)
from build123d.importers import import_svg_as_buildline_code, import_brep
from build123d.exporters import ExportSVG


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
            if edge.geom_type() == "BEZIER":
                found += 1
            elif edge.geom_type() == "LINE":
                found += 1
            elif edge.geom_type() == "ELLIPSE":
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

    # def test_import_svg_as_buildline_code_ccw(self):
    #     # Create svg file
    #     with BuildLine() as test_obj:
    #         l3 = RadiusArc((0, 1), (0, 0), 1.5)
    #     show(test_obj)
    #     svg = ExportSVG()
    #     svg.add_shape(test_obj.wires()[0], "")
    #     svg.write("test.svg")

    #     # Read the svg as code
    #     buildline_code, builder_name = import_svg_as_buildline_code("test.svg")

    #     # Execute it and convert to Edges
    #     ex_locals = {}
    #     exec(buildline_code, None, ex_locals)
    #     test_obj: BuildLine = ex_locals[builder_name]
    #     os.remove("test.svg")

    #     self.assertEqual(test_obj.edges()[0].geom_type(), "ELLIPSE")


class ImportBREP(unittest.TestCase):
    def test_bad_filename(self):
        with self.assertRaises(ValueError):
            import_brep("test.brep")


if __name__ == "__main__":
    unittest.main()
