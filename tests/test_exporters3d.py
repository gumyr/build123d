"""
3D Exporter Tests

name: test_exporters3d.py
by:   Gumyr
date: March 19th 2024

desc: Test the build123d 3D exporters.

license:

    Copyright 2024 Gumyr

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

import io
import json
import os
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryFile
from typing import Optional
from zoneinfo import ZoneInfo

import pytest

from build123d.build_common import GridLocations
from build123d.build_enums import Unit
from build123d.build_line import BuildLine
from build123d.build_sketch import BuildSketch
from build123d.exporters3d import export_brep, export_gltf, export_obj, export_step, export_stl
from build123d.geometry import Color, Pos, Vector, VectorLike
from build123d.objects_curve import Line
from build123d.objects_part import Box, Cone, Cylinder, Sphere
from build123d.objects_sketch import Circle, Rectangle
from build123d.topology import Compound


class DirectApiTestCase(unittest.TestCase):
    def assertTupleAlmostEquals(
        self,
        first: tuple[float, ...],
        second: tuple[float, ...],
        places: int,
        msg: Optional[str] = None,
    ):
        """Check Tuples"""
        self.assertEqual(len(second), len(first))
        for i, j in zip(second, first):
            self.assertAlmostEqual(i, j, places, msg=msg)

    def assertVectorAlmostEquals(
        self, first: Vector, second: VectorLike, places: int, msg: Optional[str] = None
    ):
        second_vector = Vector(second)
        self.assertAlmostEqual(first.X, second_vector.X, places, msg=msg)
        self.assertAlmostEqual(first.Y, second_vector.Y, places, msg=msg)
        self.assertAlmostEqual(first.Z, second_vector.Z, places, msg=msg)


class TestExportStep(DirectApiTestCase):
    def test_export_step_solid(self):
        b = Box(1, 1, 1).locate(Pos(-1, -2, -3))
        self.assertTrue(export_step(b, "box.step"))
        with open("box.step", "r") as file:
            step_data = file.read()
        os.remove("box.step")
        self.assertEqual(step_data.count("VERTEX_POINT"), len(b.vertices()))

    def test_export_step_assembly(self):
        a = Sphere(1).solid()
        a.label = "sphere"
        b = Box(1, 1, 1).locate(Pos(-1, -2, -3))
        b.color = Color(0, 0, 1)
        b.label = "box"
        assembly = Compound(children=[a, b])
        assembly.label = "assembly"
        assembly.color = Color(1, 0, 0)
        self.assertTrue(export_step(assembly, "assembly.step", unit=Unit.IN))
        with open("assembly.step", "r") as file:
            step_data = file.read()
        os.remove("assembly.step")
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('red')"), -1)
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('blue')"), -1)
        # Check for inches
        self.assertGreater(len(re.findall(r"[(,]25\.4[,)]", step_data)), 0)

        self.assertNotEqual(step_data.find("PRODUCT('sphere',"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('box',"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('assembly',"), -1)

    def test_export_step_sketch(self):
        with BuildSketch() as test:
            with GridLocations(2, 2, 2, 2):
                Rectangle(1, 1)
            Circle(1)
        test_sketch = test.sketch
        test_sketch.label = "sketch"
        test_sketch.color = Color("red")
        self.assertTrue(export_step(test_sketch, "sketch.step"))
        with open("sketch.step", "r") as file:
            step_data = file.read()
        os.remove("sketch.step")
        self.assertEqual(step_data.count("VERTEX_POINT"), len(test.vertices()))
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('red')"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('sketch',"), -1)

    def test_export_step_curve(self):
        with BuildLine() as test:
            l1 = Line((0, 0), (1, 0))
            l2 = Line(l1 @ 1, (1, 1))
        test_line = test.line
        test_line.label = "curve"
        test_line.color = Color("red")
        self.assertTrue(export_step(test_line, "curve.step"))
        with open("curve.step", "r") as file:
            step_data = file.read()
        os.remove("curve.step")
        self.assertEqual(step_data.count("LINE"), len(test.edges()))
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('red')"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('curve',"), -1)

    def test_export_step_unknown(self):
        box = Box(1, 1, 1)
        self.assertTrue(export_step(box, "box_read_only.step"))
        os.chmod("box_read_only.step", 0o444)  # Make the file read only
        with self.assertRaises(RuntimeError):
            export_step(box, "box_read_only.step")
        os.chmod("box_read_only.step", 0o777)  # Make the file read/write
        os.remove("box_read_only.step")

    def test_export_step_timestamp_datetime(self):
        b = Box(1, 1, 1)
        t = datetime(2025, 5, 6, 21, 30, 25)
        self.assertTrue(export_step(b, "box.step", timestamp=t))
        with open("box.step", "r") as file:
            step_data = file.read()
        os.remove("box.step")
        self.assertEqual(
            re.findall("FILE_NAME\\('[^']*','([^']*)'", step_data),
            ["2025-05-06T21:30:25"],
        )

    def test_export_step_timestamp_str(self):
        b = Box(1, 1, 1)
        self.assertTrue(export_step(b, "box.step", timestamp="0000-00-00T00:00:00"))
        with open("box.step", "r") as file:
            step_data = file.read()
        os.remove("box.step")
        self.assertEqual(
            re.findall("FILE_NAME\\('[^']*','([^']*)'", step_data),
            ["0000-00-00T00:00:00"],
        )

    def test_export_step_nested_assembly_labels_and_colors(self):
        root = Box(0.5, 0.5, 0.5)
        root.label = "level1"
        root.color = Color(0, 1, 0)  # green

        a = Sphere(1).solid()
        a.label = "sphere_a"
        a.color = Color("red")

        b = Box(1, 2, 3).locate(Pos(10, 0, 0))
        b.label = "box_b"
        b.color = Color("blue")

        sub = Compound(children=[a, b])
        sub.label = "subasm"

        assy = Compound(children=[root, sub])
        assy.label = "assy"

        self.assertTrue(export_step(assy, "nested.step"))
        with open("nested.step", "r") as file:
            step_data = file.read()
        os.remove("nested.step")

        self.assertNotEqual(step_data.find("PRODUCT('assy',"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('level1',"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('subasm',"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('sphere_a',"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('box_b',"), -1)
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('red')"), -1)
        self.assertNotEqual(
            step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('green')"), -1
        )
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('blue')"), -1)

    def test_export_step_component_override_parent_color(self):
        c1 = Sphere(1).solid()
        c1.label = "child_red"
        c1.color = Color("red")

        c2 = Box(1, 1, 1)
        c2.label = "child_blue"
        c2.color = Color("blue")

        assy = Compound(children=[c1, c2])
        assy.label = "assy"
        assy.color = Color(0, 1, 0)  # Green

        self.assertTrue(export_step(assy, "override.step"))
        with open("override.step", "r") as file:
            step_data = file.read()
        os.remove("override.step")

        self.assertNotEqual(step_data.find("PRODUCT('child_red',"), -1)
        self.assertNotEqual(step_data.find("PRODUCT('child_blue',"), -1)
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('red')"), -1)
        self.assertNotEqual(step_data.find("DRAUGHTING_PRE_DEFINED_COLOUR('blue')"), -1)


class TestExportGltf(DirectApiTestCase):
    def test_export_gltf(self):
        box = Box(1, 1, 1).locate(Pos(-1, -2, -3))
        box.color = Color(0, 0, 1)
        box.label = "box"
        self.assertTrue(export_gltf(box, "box.gltf", binary=False))
        with open("box.gltf", "r") as file:
            gltf_json_str = file.read()
        gltf_json = json.loads(gltf_json_str)
        self.assertEqual(gltf_json["meshes"][0]["name"], box.label)
        self.assertEqual(gltf_json["nodes"][0]["name"], box.label)
        os.remove("box.gltf")
        os.remove("box.bin")

    # def test_export_gltf_error(self):
    #     box = Box(1, 1, 1).locate(Pos(-1, -2, -3))
    #     export_gltf(box, "box.gltf")
    #     os.chmod("box.gltf", 0o444)  # Make the file read only
    #     with self.assertRaises(RuntimeError):
    #         export_gltf(box, "box.gltf")
    #     os.chmod("box.gltf", 0o777)  # Make the file read/write
    #     os.remove("box.gltf")
    #     os.remove("box.bin")


@pytest.mark.parametrize(
    "format", (Path, os.fsencode, os.fsdecode), ids=["path", "bytes", "str"]
)
@pytest.mark.parametrize(
    "exporter", (export_gltf, export_stl, export_step, export_brep)
)
def test_pathlike_exporters(tmp_path, format, exporter):
    path = format(tmp_path / "file")
    box = Box(1, 1, 1).locate(Pos(-1, -2, -3))
    exporter(box, path)


@pytest.mark.parametrize("exporter", (export_step, export_brep))
def test_exporters_in_memory(exporter):
    buffer = io.BytesIO()
    box = Box(1, 1, 1).locate(Pos(-1, -2, -3))
    exporter(box, buffer)


@pytest.mark.parametrize("exporter", (export_step, export_brep))
def test_exporters_to_binary_fileobj(exporter):
    box = Box(1, 1, 1).locate(Pos(-1, -2, -3))
    with TemporaryFile("wb") as f:
        exporter(box, f)


@pytest.mark.parametrize("exporter", (export_step, export_brep))
def test_exporters_to_stdout(exporter):
    box = Box(1, 1, 1).locate(Pos(-1, -2, -3))
    exporter(box, sys.stdout.buffer)


class TestTessellateWithUVs(DirectApiTestCase):
    """Tests for Shape.tessellate_with_uvs()"""

    def test_box_basic(self):
        """All output arrays have matching lengths for a box."""
        box = Box(10, 20, 30)
        verts, tris, normals, uvs = box.tessellate_with_uvs(0.1)
        self.assertEqual(len(verts), len(normals))
        self.assertEqual(len(verts), len(uvs))
        self.assertGreater(len(tris), 0)

    def test_atlas_packed_uvs_in_range(self):
        """Atlas-packed UVs should be in [0, 1]."""
        box = Box(10, 20, 30)
        _, _, _, uvs = box.tessellate_with_uvs(0.1, atlas_packing=True)
        for u, v in uvs:
            self.assertGreaterEqual(u, -1e-9)
            self.assertLessEqual(u, 1.0 + 1e-9)
            self.assertGreaterEqual(v, -1e-9)
            self.assertLessEqual(v, 1.0 + 1e-9)

    def test_no_atlas_uvs_in_range(self):
        """Per-face normalized UVs span [0, 1]."""
        box = Box(10, 20, 30)
        _, _, _, uvs = box.tessellate_with_uvs(0.1, atlas_packing=False)
        for u, v in uvs:
            self.assertGreaterEqual(u, -1e-9)
            self.assertLessEqual(u, 1.0 + 1e-9)
            self.assertGreaterEqual(v, -1e-9)
            self.assertLessEqual(v, 1.0 + 1e-9)

    def test_cylinder(self):
        """Curved surfaces produce valid UV coordinates."""
        cyl = Cylinder(10, 20)
        verts, tris, normals, uvs = cyl.tessellate_with_uvs(0.1)
        self.assertEqual(len(verts), len(uvs))
        self.assertGreater(len(tris), 0)

    def test_sphere(self):
        """Sphere tessellation returns matching arrays."""
        sph = Sphere(15)
        verts, tris, normals, uvs = sph.tessellate_with_uvs(0.1)
        self.assertEqual(len(verts), len(uvs))
        self.assertEqual(len(verts), len(normals))

    def test_triangle_indices_valid(self):
        """All triangle indices reference valid vertices."""
        box = Box(5, 5, 5)
        verts, tris, _, _ = box.tessellate_with_uvs(0.1)
        n = len(verts)
        for i0, i1, i2 in tris:
            self.assertGreaterEqual(min(i0, i1, i2), 0)
            self.assertLess(max(i0, i1, i2), n)

    def test_cone_with_atlas(self):
        """Cone (varying-radius surface) packs correctly with atlas."""
        cone = Cone(10, 3, 15)
        verts, tris, normals, uvs = cone.tessellate_with_uvs(0.1)
        self.assertEqual(len(verts), len(uvs))
        self.assertGreater(len(tris), 0)
        for u, v in uvs:
            self.assertGreaterEqual(u, -1e-9)
            self.assertLessEqual(u, 1.0 + 1e-9)
            self.assertGreaterEqual(v, -1e-9)
            self.assertLessEqual(v, 1.0 + 1e-9)


class TestExportObj(DirectApiTestCase):
    """Tests for export_obj()"""

    def test_export_obj_box(self):
        """Box exports valid OBJ with matching vertex/UV/normal counts."""
        box = Box(10, 20, 30)
        path = "test_box.obj"
        try:
            self.assertTrue(export_obj(box, path))
            with open(path) as f:
                lines = f.readlines()
            v = sum(1 for l in lines if l.startswith("v "))
            vt = sum(1 for l in lines if l.startswith("vt "))
            vn = sum(1 for l in lines if l.startswith("vn "))
            faces = sum(1 for l in lines if l.startswith("f "))
            self.assertEqual(v, vt)
            self.assertEqual(v, vn)
            self.assertGreater(faces, 0)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_obj_indices_valid(self):
        """All face indices in OBJ are within bounds."""
        cyl = Cylinder(5, 15)
        path = "test_cyl.obj"
        try:
            export_obj(cyl, path)
            with open(path) as f:
                lines = f.readlines()
            nv = sum(1 for l in lines if l.startswith("v "))
            for line in lines:
                if not line.startswith("f "):
                    continue
                for part in line.strip().split()[1:]:
                    vi, ti, ni = (int(x) for x in part.split("/"))
                    self.assertGreaterEqual(vi, 1)
                    self.assertLessEqual(vi, nv)
                    self.assertGreaterEqual(ti, 1)
                    self.assertLessEqual(ti, nv)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_obj_no_atlas(self):
        """OBJ export works with atlas_packing=False."""
        box = Box(5, 5, 5)
        path = "test_no_atlas.obj"
        try:
            self.assertTrue(export_obj(box, path, atlas_packing=False))
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_obj_without_uvs(self):
        """OBJ export without UVs omits vt/vn records and uses plain face indices."""
        box = Box(5, 5, 5)
        path = "test_no_uvs.obj"
        try:
            self.assertTrue(export_obj(box, path, include_uvs=False))
            with open(path) as f:
                lines = f.readlines()
            vt = sum(1 for l in lines if l.startswith("vt "))
            vn = sum(1 for l in lines if l.startswith("vn "))
            face_lines = [l.strip() for l in lines if l.startswith("f ")]
            self.assertEqual(vt, 0)
            self.assertEqual(vn, 0)
            self.assertGreater(len(face_lines), 0)
            for line in face_lines:
                self.assertNotIn("/", line)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_obj_to_bytesio(self):
        """OBJ export to BytesIO produces valid content."""
        box = Box(10, 20, 30)
        buf = io.BytesIO()
        self.assertTrue(export_obj(box, buf))
        content = buf.getvalue().decode("utf-8")
        lines = content.splitlines()
        v_count = sum(1 for l in lines if l.startswith("v "))
        vt_count = sum(1 for l in lines if l.startswith("vt "))
        f_count = sum(1 for l in lines if l.startswith("f "))
        self.assertGreater(v_count, 0)
        self.assertEqual(v_count, vt_count)
        self.assertGreater(f_count, 0)


class TestExportGltfUVs(DirectApiTestCase):
    """Tests for glTF UV export via include_uvs parameter."""

    def test_gltf_with_uvs_has_texcoord(self):
        """glTF with include_uvs=True contains TEXCOORD_0."""
        box = Box(10, 20, 30)
        path = "test_uvs.gltf"
        try:
            export_gltf(box, path, binary=False, include_uvs=True)
            with open(path) as f:
                gltf = json.load(f)
            attrs = [
                p.get("attributes", {})
                for m in gltf.get("meshes", [])
                for p in m.get("primitives", [])
            ]
            has_texcoord = any("TEXCOORD_0" in a for a in attrs)
            self.assertTrue(has_texcoord)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_gltf_without_uvs_no_texcoord(self):
        """glTF with include_uvs=False strips TEXCOORD_0."""
        box = Box(10, 20, 30)
        path = "test_no_uvs.gltf"
        try:
            export_gltf(box, path, binary=False, include_uvs=False)
            with open(path) as f:
                gltf = json.load(f)
            attrs = [
                p.get("attributes", {})
                for m in gltf.get("meshes", [])
                for p in m.get("primitives", [])
            ]
            has_texcoord = any("TEXCOORD_0" in a for a in attrs)
            self.assertFalse(has_texcoord)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
