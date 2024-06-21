import unittest, uuid
from build123d.build_enums import MeshType, Unit
from build123d.build_part import BuildPart
from build123d.build_sketch import BuildSketch
from build123d.exporters3d import export_stl
from build123d.objects_part import Box, Cylinder
from build123d.objects_sketch import Rectangle
from build123d.operations_part import extrude
from build123d.topology import Compound, Solid
from build123d.geometry import Axis, Color, Location, Vector, VectorLike
from build123d.mesher import Mesher


class DirectApiTestCase(unittest.TestCase):
    def assertTupleAlmostEquals(
        self,
        first: tuple[float, ...],
        second: tuple[float, ...],
        places: int,
        msg: str = None,
    ):
        """Check Tuples"""
        self.assertEqual(len(second), len(first))
        for i, j in zip(second, first):
            self.assertAlmostEqual(i, j, places, msg=msg)

    def assertVectorAlmostEquals(
        self, first: Vector, second: VectorLike, places: int, msg: str = None
    ):
        second_vector = Vector(second)
        self.assertAlmostEqual(first.X, second_vector.X, places, msg=msg)
        self.assertAlmostEqual(first.Y, second_vector.Y, places, msg=msg)
        self.assertAlmostEqual(first.Z, second_vector.Z, places, msg=msg)


class TestProperties(unittest.TestCase):
    def test_version(self):
        exporter = Mesher()
        self.assertEqual(exporter.library_version, "2.3.1")

    def test_units(self):
        for unit in Unit:
            exporter = Mesher(unit=unit)
            exporter.add_shape(Solid.make_box(1, 1, 1))
            exporter.write("test.3mf")
            importer = Mesher()
            _shape = importer.read("test.3mf")
            self.assertEqual(unit, importer.model_unit)

    def test_vertex_and_triangle_counts(self):
        exporter = Mesher()
        exporter.add_shape(Solid.make_box(1, 1, 1))
        self.assertEqual(exporter.vertex_counts[0], 8)
        self.assertEqual(exporter.triangle_counts[0], 12)

    def test_mesh_counts(self):
        exporter = Mesher()
        exporter.add_shape(Solid.make_box(1, 1, 1))
        exporter.add_shape(Solid.make_cone(1, 0, 2))
        self.assertEqual(exporter.mesh_count, 2)


class TestMetaData(unittest.TestCase):
    def test_add_meta_data(self):
        exporter = Mesher()
        exporter.add_shape(Solid.make_box(1, 1, 1))
        exporter.add_meta_data("test_space", "test0", "some data", "str", True)
        exporter.add_meta_data("test_space", "test1", "more data", "str", True)
        exporter.write("test.3mf")
        importer = Mesher()
        _shape = importer.read("test.3mf")
        imported_meta_data: list[dict] = importer.get_meta_data()
        self.assertEqual(imported_meta_data[0]["name_space"], "test_space")
        self.assertEqual(imported_meta_data[0]["name"], "test0")
        self.assertEqual(imported_meta_data[0]["value"], "some data")
        self.assertEqual(imported_meta_data[0]["type"], "str")
        self.assertEqual(imported_meta_data[1]["name_space"], "test_space")
        self.assertEqual(imported_meta_data[1]["name"], "test1")
        self.assertEqual(imported_meta_data[1]["value"], "more data")
        self.assertEqual(imported_meta_data[1]["type"], "str")

    def test_add_code(self):
        exporter = Mesher()
        exporter.add_shape(Solid.make_box(1, 1, 1))
        exporter.add_code_to_metadata()
        exporter.write("test.3mf")
        importer = Mesher()
        _shape = importer.read("test.3mf")
        source_code = importer.get_meta_data_by_key("build123d", "test_mesher.py")
        self.assertEqual(len(source_code), 2)
        self.assertEqual(source_code["type"], "python")
        self.assertGreater(len(source_code["value"]), 10)


class TestMeshProperties(unittest.TestCase):
    def test_properties(self):
        # Note: MeshType.OTHER can't be used with a Solid shape
        for mesh_type in [MeshType.MODEL, MeshType.SUPPORT, MeshType.SOLIDSUPPORT]:
            with self.subTest("MeshTYpe", mesh_type=mesh_type):
                exporter = Mesher()
                if mesh_type != MeshType.SUPPORT:
                    test_uuid = uuid.uuid1()
                else:
                    test_uuid = None
                name = "test" + mesh_type.name
                shape = Solid.make_box(1, 1, 1)
                shape.label = name
                exporter.add_shape(
                    shape,
                    mesh_type=mesh_type,
                    part_number=str(mesh_type.value),
                    uuid_value=test_uuid,
                )
                exporter.write("test.3mf")
                importer = Mesher()
                shape = importer.read("test.3mf")
                self.assertEqual(shape[0].label, name)
                self.assertEqual(importer.mesh_count, 1)
                properties = importer.get_mesh_properties()
                self.assertEqual(properties[0]["name"], name)
                self.assertEqual(properties[0]["part_number"], str(mesh_type.value))
                self.assertEqual(properties[0]["type"], mesh_type.name)
                if mesh_type != MeshType.SUPPORT:
                    self.assertEqual(properties[0]["uuid"], str(test_uuid))


class TestAddShape(DirectApiTestCase):
    def test_add_shape(self):
        exporter = Mesher()
        blue_shape = Solid.make_box(1, 1, 1)
        blue_shape.color = Color("blue")
        blue_shape.label = "blue"
        red_shape = Solid.make_cone(1, 0, 2).locate(Location((0, -1, 0)))
        red_shape.color = Color("red")
        red_shape.label = "red"
        exporter.add_shape([blue_shape, red_shape])
        exporter.write("test.3mf")
        importer = Mesher()
        box, cone = importer.read("test.3mf")
        self.assertVectorAlmostEquals(box.bounding_box().size, (1, 1, 1), 2)
        self.assertVectorAlmostEquals(box.bounding_box().size, (1, 1, 1), 2)
        self.assertEqual(len(box.clean().faces()), 6)
        self.assertEqual(box.label, "blue")
        self.assertEqual(cone.label, "red")
        self.assertTupleAlmostEquals(tuple(box.color), (0, 0, 1, 1), 5)
        self.assertTupleAlmostEquals(tuple(cone.color), (1, 0, 0, 1), 5)

    def test_add_compound(self):
        exporter = Mesher()
        box = Solid.make_box(1, 1, 1)
        cone = Solid.make_cone(1, 0, 2).locate(Location((0, -1, 0)))
        shape_assembly = Compound([box, cone])
        exporter.add_shape(shape_assembly)
        exporter.write("test.3mf")
        importer = Mesher()
        shapes = importer.read("test.3mf")
        self.assertEqual(importer.mesh_count, 2)


class TestErrorChecking(unittest.TestCase):
    def test_read_invalid_file(self):
        with self.assertRaises(ValueError):
            importer = Mesher()
            importer.read("unknown_file.type")

    def test_write_invalid_file(self):
        exporter = Mesher()
        exporter.add_shape(Solid.make_box(1, 1, 1))
        with self.assertRaises(ValueError):
            exporter.write("unknown_file.type")


class TestDuplicateVertices(unittest.TestCase):
    def test_duplicate_vertices(self):
        with BuildPart() as funky_box:
            Box(3, 3, 3)
            with BuildSketch(funky_box.faces().sort_by(Axis.Z)[-1]):
                Rectangle(1, 2, rotation=45)
            extrude(amount=1)

        exporter = Mesher(unit=Unit.CM)
        exporter.add_shape(funky_box.part)  # dual vertices raise exception here


class TestHollowImport(unittest.TestCase):
    def test_hollow_import(self):
        test_shape = Cylinder(5, 10) - Box(5, 5, 5)
        export_stl(test_shape, "test.stl")
        importer = Mesher()
        stl = importer.read("test.stl")
        self.assertTrue(stl[0].is_valid())


class TestImportDegenerateTriangles(unittest.TestCase):
    def test_degenerate_import(self):
        """Some STLs may contain 'triangles' where all three points are on a line"""
        importer = Mesher()
        try:
            stl = importer.read("tests/cyl_w_rect_hole.stl")[0]
        except:
            stl = importer.read("cyl_w_rect_hole.stl")[0]
        self.assertEqual(type(stl), Solid)
        self.assertTrue(stl.is_manifold)
        self.assertTrue(stl.is_valid())
        self.assertEqual(sum(f.area == 0 for f in stl.faces()), 0)


if __name__ == "__main__":
    unittest.main()
