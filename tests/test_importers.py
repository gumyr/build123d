from io import BytesIO, StringIO
import os
from os import fsencode, fsdecode
import unittest
import urllib.request
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Callable
from unittest.mock import MagicMock, patch

import pytest
from OCP.TopoDS import TopoDS_Edge

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
from build123d.geometry import Location, Pos, Vector
from build123d.exporters import ExportSVG
from build123d.exporters3d import export_brep, export_step
from build123d.build_constants import UNITS_PER_METER
from build123d.build_enums import Align, GeomType, Unit


def download(url: str) -> bytes:
    """Return the content at url."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "build123d test suite"}
    )
    with urllib.request.urlopen(request) as response:
        return response.read()


def fetch_once(destination: Path, fetch: Callable[[], bytes]) -> Path:
    """Store the result of fetch() at destination unless it is already there.

    Parallel test workers may call this for the same destination at the same time,
    so the content is written to a unique temporary file beside it and moved into
    place atomically: a reader only ever sees a complete file.
    """
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = fetch()
        handle, temp_name = tempfile.mkstemp(
            dir=destination.parent, prefix=f".{destination.name}."
        )
        with os.fdopen(handle, "wb") as file:
            file.write(data)
        os.replace(temp_name, destination)
    return destination


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
        svg.write(self.tmp_path / "test.svg")

        # Read the svg as code
        buildline_code, builder_name = import_svg_as_buildline_code(
            self.tmp_path / "test.svg"
        )
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

    def test_import_svg_as_buildline_code_invalid_name(self):
        # Create svg file
        with BuildLine() as test_obj:
            l1 = Bezier((0, 0), (0.25, -0.1), (0.5, -0.15), (1, 0))
            l2 = Line(l1 @ 1, (1, 1))
            l3 = RadiusArc(l2 @ 1, (0, 1), 2)
            l4 = Line(l3 @ 1, l1 @ 0)
        svg = ExportSVG()
        svg.add_shape(test_obj.wires()[0], "")
        svg.write(self.tmp_path / "test!.svg")

        # Read the svg as code
        buildline_code, builder_name = import_svg_as_buildline_code(
            self.tmp_path / "test!.svg"
        )

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
        cls.large_step_file_path = fetch_once(
            Path(tempfile.gettempdir()) / "as1-oc-214.stp", lambda: download(url)
        )

    def test_single_object(self):
        export_step(Solid.make_box(1, 1, 1), self.tmp_path / "test.step")
        box = import_step(self.tmp_path / "test.step")
        self.assertTrue(isinstance(box, Solid))

    def test_move_single_object(self):
        export_step(Solid.make_box(1, 1, 1), self.tmp_path / "test.step")
        box = import_step(self.tmp_path / "test.step")
        box_moved = Pos(X=1) * box
        self.assertEqual(tuple(box_moved.location.position), (1, 0, 0))

    def test_single_label_color(self):
        box_to_export = Solid.make_box(1, 1, 1)
        box_to_export.label = "box"
        box_to_export.color = Color("blue")
        export_step(box_to_export, self.tmp_path / "test.step")
        imported_box = import_step(self.tmp_path / "test.step")
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
        export_step(assembly, self.tmp_path / "test.step")

        imported_assembly = import_step(self.tmp_path / "test.step")
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

    def test_unnamed_component(self):
        file_name = "nist_ctc_02_asme1_ap242-e2.stp"
        url = "https://www.nist.gov/system/files/documents/noindex/2024/06/19/NIST-PMI-STEP-Files.zip"

        def fetch_from_archive() -> bytes:
            with zipfile.ZipFile(BytesIO(download(url))) as archive:
                return archive.read(f"NIST-PMI-STEP-Files/{file_name}")

        file_path = fetch_once(
            Path(tempfile.gettempdir()) / "NIST-PMI-STEP-Files" / file_name,
            fetch_from_archive,
        )
        imported = import_step(file_path)

        self.assertIsInstance(imported, Compound)
        self.assertIn("", [child.label for child in imported.children])

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
        export_step(root, self.tmp_path / "test.step")
        imported = import_step(self.tmp_path / "test.step")

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
        export_step(assy, self.tmp_path / "test.step")
        imported = import_step(self.tmp_path / "test.step")

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

        export_step(assy, self.tmp_path / "test.step")
        imported = import_step(self.tmp_path / "test.step")

        by_label = {c.label: c for c in imported.children}
        p = by_label["moved"].location.position
        self.assertAlmostEqual(p.X, -1.0, 6)
        self.assertAlmostEqual(p.Y, -2.0, 6)
        self.assertAlmostEqual(p.Z, -3.0, 6)

    def test_located_shape_round_trip(self):
        """Issue #1014: a shape with a location comes back as the shape,
        with its label, color and location, as an unmoved shape does."""
        box = Solid.make_box(1, 2, 3)
        box.label = "box"
        box.color = Color(0, 0, 1)
        placement = Location((-10, 0, 0), (0, 0, 30))

        with tempfile.TemporaryDirectory() as tmp_dir:
            step_file = os.path.join(tmp_dir, "located.step")
            for name, shape in (("unmoved", box), ("moved", placement * box)):
                with self.subTest(name):
                    export_step(shape, step_file)
                    imported = import_step(step_file)
                    self.assertIsInstance(imported, Solid)
                    self.assertIsNone(imported.parent)
                    self.assertEqual(imported.label, "box")
                    self.assertAlmostEqual(tuple(imported.color), (0, 0, 1, 1), 5)
                    self.assertAlmostEqual(imported.volume, 6, 5)
                    self.assertAlmostEqual(
                        imported.location.position, shape.location.position, 5
                    )
                    self.assertAlmostEqual(
                        imported.location.orientation, shape.location.orientation, 5
                    )

            # a shape without a label is unwrapped as well
            export_step(placement * Solid.make_box(1, 2, 3), step_file)
            imported = import_step(step_file)
            self.assertIsInstance(imported, Solid)
            self.assertAlmostEqual(imported.location.position, (-10, 0, 0), 5)
            self.assertAlmostEqual(imported.location.orientation, (0, 0, 30), 5)

            # while an unlabeled assembly of one part stays an assembly
            export_step(Compound(children=[Solid.make_box(1, 1, 1)]), step_file)
            imported = import_step(step_file)
            self.assertIsInstance(imported, Compound)
            self.assertEqual(len(imported.children), 1)

            # an assembly with one part of another name is still an assembly
            part = Solid.make_box(1, 1, 1)
            part.label = "part"
            assembly = Compound(children=[Pos(5, 0, 0) * part])
            assembly.label = "assembly"
            export_step(assembly, step_file)
            imported = import_step(step_file)
            self.assertEqual(imported.label, "assembly")
            self.assertEqual([child.label for child in imported.children], ["part"])

    def test_reexport_imported_assembly(self):
        """import_step's result must be exportable again: the single-free-
        shape unwrap has to detach the root from its temporary wrapper
        (a stale parent made export_step build an empty document)."""
        leaf = Solid.make_box(1, 1, 1)
        leaf.label = "leaf"
        leaf.color = Color(0, 0, 1)
        sub = Compound(children=[leaf])
        sub.label = "sub"
        root = Compound(children=[Pos(10, 0, 0) * sub])
        root.label = "root"
        export_step(root, self.tmp_path / "test.step")
        imported = import_step(self.tmp_path / "test.step")

        self.assertIsNone(imported.parent)

        export_step(imported, self.tmp_path / "test.step")  # raised RuntimeError before
        reimported = import_step(self.tmp_path / "test.step")

        # geometry round-trips at the correct world position
        bb = reimported.bounding_box()
        self.assertAlmostEqual(bb.min.X, 10.0, 6)
        self.assertAlmostEqual(bb.max.X, 11.0, 6)
        leaf2 = reimported.children[0].children[0]
        self.assertEqual(leaf2.label, "leaf")
        self.assertEqual(tuple(leaf2.color), (0, 0, 1, 1))


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


class ImportSVGValidation(unittest.TestCase):
    def test_unexpected_shape_type(self):
        """The SVG document only ever yields wires and faces; the guard is a
        defensive check on that contract."""

        class _FakeDocument:
            viewbox = SimpleNamespace(x=0, y=0, width=10, height=10)

            def __iter__(self):
                yield (TopoDS_Edge(), MagicMock())

        with patch(
            "build123d.importers.import_svg_document", return_value=_FakeDocument()
        ):
            with self.assertRaisesRegex(ValueError, "unexpected shape type"):
                import_svg("unused.svg")


@pytest.mark.parametrize("placed", [False, True])
@pytest.mark.parametrize("named", [False, True])
def test_step_shared_occurrence_metadata(tmp_path, placed, named):
    from copy import copy

    leaf = Solid.make_box(1, 2, 3)
    leg = Compound(children=[leaf, Pos(3, 0, 0) * leaf])
    branches = []
    for index, name in enumerate(("a", "b", "c")):
        branch = copy(leg)
        branch.label = name
        branch.color = Color((1, 0, 0) if index == 0 else (0, 0, 1))
        if named:
            branch.children[0].label = f"upper-{name}"
            branch.children[1].label = f"lower-{name}"
        branch.children[1].color = Color("green")
        if placed:
            branch.location = Location((0, index * 5, 0), (0, 0, index * 30))
        branches.append(branch)
    assembly = Compound(label="assembly", children=branches)
    if placed:
        assembly.location = Location((10, 20, 30), (10, 20, 30))
    originals = [child for branch in branches for child in branch.children]
    nodes = [assembly, *branches, *originals]
    snapshots = [(node.wrapped, node.label, node.color) for node in nodes]
    assert originals[0].wrapped.IsPartner(originals[2].wrapped)
    path = tmp_path / "shared.step"
    export_step(assembly, path)
    imported = import_step(path)
    if placed:
        assert len(imported.children) == 1
        imported = imported.children[0]

    assert [branch.label for branch in imported.children] == [
        name if named else f"{name}-0" for name in ("a", "b", "c")
    ]
    for source, result in zip(branches, imported.children):
        assert len(result.children) == 2
        assert [child.label for child in result.children] == (
            [f"upper-{source.label}", f"lower-{source.label}"]
            if named
            else [f"{source.label}-1", f"{source.label}-2"]
        )
        for before, after in zip(source.children, result.children):
            assert tuple(after.color) == pytest.approx(tuple(before.color), abs=1e-6)
            assert after.volume == pytest.approx(before.volume)
            expected = before.located(before.global_location)
            actual = after.located(after.global_location)
            assert tuple(actual.center()) == pytest.approx(tuple(expected.center()))
    for node, (wrapped, label, color) in zip(nodes, snapshots):
        assert node.wrapped.IsEqual(wrapped)
        assert node.label == label
        assert node.color == color
    assert originals[0].wrapped.IsPartner(originals[2].wrapped)


if __name__ == "__main__":
    unittest.main()
