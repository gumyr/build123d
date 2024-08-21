from io import StringIO
import os
import unittest
import urllib.request
import tempfile
from build123d import BuildLine, Color, Line, Bezier, RadiusArc, Solid, Compound
from build123d.importers import (
    import_svg_as_buildline_code,
    import_brep,
    import_svg,
    import_step,
)
from build123d.geometry import Pos
from build123d.exporters import ExportSVG
from build123d.exporters3d import export_step
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
            "</svg>"
        )
        svg = import_svg(svg_file)
        self.assertEqual(len(svg), 3)
        self.assertEqual(str(svg[0].color), str(Color(0, 0, 1, 1)))
        self.assertEqual(str(svg[1].color), str(Color(1, 0, 0, 1)))
        self.assertEqual(str(svg[2].color), str(Color(0, 0, 0, 1)))


class ImportBREP(unittest.TestCase):
    def test_bad_filename(self):
        with self.assertRaises(ValueError):
            import_brep("test.brep")


class ImportSTEP(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """setUpClass is a class method that is executed once for the entire test
        class before any of the test methods in the class are executed. It's intended
        for setting up expensive resources or doing tasks that are required by all
        tests in the class, such as downloading a large file, establishing a database
        connection, or starting a server.
        """
        url = "https://raw.githubusercontent.com/tpaviot/pythonocc-demos/master/assets/models/as1-oc-214.stp"
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "as1-oc-214.stp")
        if not os.path.exists(file_path):
            urllib.request.urlretrieve(url, file_path)
        cls.large_step_file_path = file_path

    def test_single_object(self):
        export_step(Solid.make_box(1, 1, 1), "test.step")
        box = import_step("test.step")
        self.assertTrue(isinstance(box, Solid))

    def test_move_single_object(self):
        export_step(Solid.make_box(1, 1, 1), "test.step")
        box = import_step("test.step")
        box_moved = Pos(X=1) * box
        self.assertEqual(tuple(box_moved.location.position), (1, 0, 0))

    def test_single_label_color(self):
        box_to_export = Solid.make_box(1, 1, 1)
        box_to_export.label = "box"
        box_to_export.color = Color("blue")
        export_step(box_to_export, "test.step")
        imported_box = import_step("test.step")
        self.assertTrue(isinstance(imported_box, Solid))
        self.assertEqual(imported_box.label, "box")
        self.assertEqual(tuple(imported_box.color), (0, 0, 1, 1))

    def test_single_label_color(self):
        a = Solid.make_sphere(1)
        a.color = Color("red")
        a.label = "sphere"
        b = Solid.make_box(1, 1, 1).locate(Pos(-1, -2, -3))
        b.color = Color("blue")
        b.label = "box"
        assembly = Compound(children=[a, b])
        assembly.label = "assembly"
        assembly.color = Color("green")
        export_step(assembly, "test.step")

        imported_assembly = import_step("test.step")
        self.assertTrue(isinstance(imported_assembly, Compound))
        self.assertTrue(isinstance(imported_assembly.children[0], Solid))
        self.assertTrue(isinstance(imported_assembly.children[1], Solid))
        self.assertEqual(imported_assembly.label, "assembly")
        self.assertEqual(imported_assembly.children[0].label, "sphere")
        self.assertEqual(tuple(imported_assembly.children[0].color), (1, 0, 0, 1))
        self.assertEqual(imported_assembly.children[1].label, "box")
        self.assertEqual(tuple(imported_assembly.children[1].color), (0, 0, 1, 1))

    def test_assembly_with_oriented_parts(self):
        assembly = import_step(self.large_step_file_path)
        fused = Solid.fuse(*assembly.solids())
        # If the parts where placed correctly they all touch and can be fused
        self.assertEqual(len(fused.solids()), 1)


if __name__ == "__main__":
    unittest.main()
