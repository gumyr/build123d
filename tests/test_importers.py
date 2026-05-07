from io import StringIO
import os
from os import fsencode, fsdecode
import unittest
import urllib.request
import tempfile
from pathlib import Path

import pytest

from build123d import (
    BuildLine,
    Color,
    Line,
    Bezier,
    EllipticalStartArc,
    RadiusArc,
    Solid,
    Compound,
)
from build123d.importers import (
    import_svg_as_buildline_code,
    import_brep,
    import_svg,
    import_step,
    import_stl,
)
from build123d.geometry import Pos, Vector
from build123d.exporters import ExportSVG
from build123d.exporters3d import export_brep, export_step
from build123d.build_common import UNITS_PER_METER
from build123d.build_enums import Align, GeomType, Unit


class ImportSVG(unittest.TestCase):
    def test_import_svg_as_buildline_code(self):
        # Create svg file
        with BuildLine() as test_obj:
            l1 = Bezier((0, 0), (0.25, -0.1), (0.5, -0.15), (1, 0))
            l2 = Line(l1 @ 1, (1, 1))
            l3 = RadiusArc(l2 @ 1, (0, 1), 2)
            l4 = EllipticalStartArc(l3 @ 1, (-1, 0), 0.5, 1, 180, start_angle=0)
        svg = ExportSVG()
        svg.add_shape(test_obj.wires()[0], "")
        svg.write("test.svg")

        # Read the svg as code
        buildline_code, builder_name = import_svg_as_buildline_code("test.svg")
        # Execute it and convert to Edges
        ex_locals = {}
        exec(buildline_code, None, ex_locals)
        test_obj: BuildLine = ex_locals[builder_name]
        self.assertEqual(
            sum(e.geom_type == GeomType.BEZIER for e in test_obj.edges()), 1
        )
        self.assertEqual(sum(e.geom_type == GeomType.LINE for e in test_obj.edges()), 1)
        self.assertEqual(
            sum(e.geom_type == GeomType.CIRCLE for e in test_obj.edges()), 1
        )
        self.assertEqual(
            sum(e.geom_type == GeomType.ELLIPSE for e in test_obj.edges()), 1
        )
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
        for tag in ["id", "inkscape:label"]:
            # Import the svg object as a ShapeList
            svg = import_svg(svg_file, label_by=tag)

            # Exact the shape of the plate & holes
            base_faces = svg.filter_by(lambda f: "base" in f.label)
            hole_faces = svg.filter_by(lambda f: "hole" in f.label)
            test_wires = svg.filter_by(lambda f: "wire" in f.label)

            self.assertEqual(len(list(base_faces)), 1)
            self.assertEqual(len(list(hole_faces)), 2)
            self.assertEqual(len(list(test_wires)), 1)

    def test_import_svg_deprecated_param(self):  # TODO remove for `1.0` release
        svg_file = Path(__file__).parent / "../tests/svg_import_test.svg"

        with self.assertWarns(UserWarning):
            svg = import_svg(svg_file, label_by="label", is_inkscape_label=True)

            # Exact the shape of the plate & holes
            base_faces = svg.filter_by(lambda f: "base" in f.label)
            hole_faces = svg.filter_by(lambda f: "hole" in f.label)
            test_wires = svg.filter_by(lambda f: "wire" in f.label)

            self.assertEqual(len(list(base_faces)), 1)
            self.assertEqual(len(list(hole_faces)), 2)
            self.assertEqual(len(list(test_wires)), 1)

        with self.assertWarns(UserWarning):
            svg = import_svg(svg_file, is_inkscape_label=False)

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

    def test_import_svg_origin(self):
        svg_src = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="1 1 6 8" width="6" height="8">'
            '<circle r="1" cx="2" cy="3"/>'
            "</svg>"
        )

        svg = import_svg(StringIO(svg_src), align=None, flip_y=False)
        self.assertAlmostEqual(svg[0].bounding_box().center(), Vector(2.0, +3.0))

        svg = import_svg(StringIO(svg_src), align=None, flip_y=True)
        self.assertAlmostEqual(svg[0].bounding_box().center(), Vector(2.0, -3.0))

    def test_import_svg_align(self):
        svg_src = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="1 1 6 8" width="6" height="8">'
            '<rect x="1" y="1" width="6" height="8"/>'
            "</svg>"
        )

        svg = import_svg(StringIO(svg_src), align=Align.MIN, flip_y=False)
        self.assertAlmostEqual(svg[0].bounding_box().min, Vector(0.0, 0.0))

        svg = import_svg(StringIO(svg_src), align=Align.MIN, flip_y=True)
        self.assertAlmostEqual(svg[0].bounding_box().min, Vector(0, 0))

        svg = import_svg(StringIO(svg_src), align=Align.MAX, flip_y=False)
        self.assertAlmostEqual(svg[0].bounding_box().max, Vector(0.0, 0.0))

        svg = import_svg(StringIO(svg_src), align=Align.MAX, flip_y=True)
        self.assertAlmostEqual(svg[0].bounding_box().max, Vector(0, 0))


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

    def test_roundtrip_nested_labels_colors(self):
        a = Solid.make_sphere(1)
        a.label = "sphere"
        a.color = Color(1, 0, 0)

        b = Solid.make_box(1, 1, 1).locate(Pos(-1, -2, -3))
        b.label = "box"
        b.color = Color(0, 0, 1)

        sub = Compound(children=[a, b])
        sub.label = "subasm"

        root = Compound(children=[sub])
        root.label = "assembly"
        root.color = Color(0, 1, 0)
        export_step(root, "test.step")
        imported = import_step("test.step")
        os.remove("test.step")

        self.assertTrue(isinstance(imported, Compound))
        self.assertEqual(imported.label, "assembly")
        self.assertEqual(len(imported.children), 1)
        self.assertEqual(imported.children[0].label, "subasm")
        self.assertEqual(len(imported.children[0].children), 2)

        by_label = {c.label: c for c in imported.children[0].children}
        self.assertEqual(tuple(by_label["sphere"].color), (1, 0, 0, 1))
        self.assertEqual(tuple(by_label["box"].color), (0, 0, 1, 1))

    def test_roundtrip_component_color_overrides_parent(self):
        c1 = Solid.make_sphere(1)
        c1.label = "c1"
        c1.color = Color(1, 0, 0)

        c2 = Solid.make_box(1, 1, 1).locate(Pos(4, 5, 6))
        c2.label = "c2"
        c2.color = Color(0, 0, 1)

        assy = Compound(children=[c1, c2])
        assy.label = "assy"
        assy.color = Color(0, 1, 0)
        export_step(assy, "test.step")
        imported = import_step("test.step")
        os.remove("test.step")

        by_label = {c.label: c for c in imported.children}
        self.assertEqual(tuple(by_label["c1"].color), (1, 0, 0, 1))
        self.assertEqual(tuple(by_label["c2"].color), (0, 0, 1, 1))
        self.assertEqual(len(assy.children), len(imported.children))

    def test_roundtrip_preserves_component_location(self):
        moved = Solid.make_box(1, 1, 1).locate(Pos(-1, -2, -3))
        moved.label = "moved"
        moved.color = Color("blue")

        fixed = Solid.make_sphere(1)
        fixed.label = "fixed"
        fixed.color = Color("red")

        assy = Compound(children=[fixed, moved])
        assy.label = "assy"

        export_step(assy, "test.step")
        imported = import_step("test.step")
        os.remove("test.step")

        by_label = {c.label: c for c in imported.children}
        p = by_label["moved"].location.position
        self.assertAlmostEqual(p.X, -1.0, 6)
        self.assertAlmostEqual(p.Y, -2.0, 6)
        self.assertAlmostEqual(p.Z, -3.0, 6)


@pytest.mark.parametrize(
    "format", (Path, fsencode, fsdecode), ids=["path", "bytes", "str"]
)
@pytest.mark.parametrize(
    "importer,file",
    [
        (import_svg, Path(__file__).parent / "svg_import_test.svg"),
        (import_svg_as_buildline_code, Path(__file__).parent / "svg_import_test.svg"),
        (import_stl, Path(__file__).parent / "cyl_w_rect_hole.stl"),
    ],
    ids=["svg", "svg_code", "stl"],
)
def test_pathlike_import(format, importer, file):
    file = format(file)
    importer(file)


@pytest.mark.parametrize(
    "format", (Path, fsencode, fsdecode), ids=["path", "bytes", "str"]
)
def test_pathlike_step(format, tmp_path):
    step_file = format(tmp_path / "test.step")
    export_step(Solid.make_box(1, 1, 1), step_file)
    import_step(step_file)


@pytest.mark.parametrize(
    "format", (Path, fsencode, fsdecode), ids=["path", "bytes", "str"]
)
def test_pathlike_brep(format, tmp_path):
    brep_file = format(tmp_path / "test.brep")
    export_brep(Solid.make_box(1, 1, 1), brep_file)
    import_brep(brep_file)


@pytest.mark.parametrize(
    "unit",
    (Unit.MM, Unit.MC, Unit.CM, Unit.M, Unit.IN, Unit.FT),
    ids=["MM", "MC", "CM", "M", "IN", "FT"],
)
def test_stl_import_rescale_units(unit):
    stl_file = Path(__file__).parent / "cyl_w_rect_hole.stl"
    importer = import_stl(stl_file, unit)
    mm_bbox_diag_length = 69.28203925644141
    m_conv_factor = UNITS_PER_METER[unit]
    expected_diag_length = mm_bbox_diag_length / m_conv_factor * 1000
    assert importer.bounding_box().size.length == pytest.approx(
        expected_diag_length, rel=1e-6, abs=1e-6
    )


def test_stl_import_rescale_units_invalid(unit="invalid"):
    stl_file = Path(__file__).parent / "cyl_w_rect_hole.stl"
    with pytest.raises(ValueError):
        importer = import_stl(stl_file, unit)


if __name__ == "__main__":
    unittest.main()
