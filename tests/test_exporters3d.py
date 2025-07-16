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
import unittest
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pytest

from build123d.build_common import GridLocations
from build123d.build_enums import Unit
from build123d.build_line import BuildLine
from build123d.build_sketch import BuildSketch
from build123d.exporters3d import export_brep, export_gltf, export_step, export_stl
from build123d.geometry import Color, Pos, Vector, VectorLike
from build123d.objects_curve import Line
from build123d.objects_part import Box, Sphere
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
        self.assertEqual(len(re.findall("[(,]25.4[,)]", step_data)), 45)
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
        double_compound = Compound(Sphere(1).wrapped)
        double_compound.color = Color("blue")
        with self.assertWarns(UserWarning):
            export_step(double_compound, "double_compound.step")
        os.remove("double_compound.step")

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


def test_export_brep_in_memory():
    buffer = io.BytesIO()
    box = Box(1, 1, 1).locate(Pos(-1, -2, -3))
    export_brep(box, buffer)


if __name__ == "__main__":
    unittest.main()
