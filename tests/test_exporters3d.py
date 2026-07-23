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
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest
import requests

from build123d.build_common import GridLocations
from build123d.build_enums import Unit
from build123d.build_line import BuildLine
from build123d.build_sketch import BuildSketch
from build123d.exporters3d import (
    export_brep,
    export_gltf,
    export_step,
    export_stl,
    export_to_pcbway,
)
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

    @unittest.skipIf(os.name == "posix" and os.getuid() == 0, "root ignores file permission bits")
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


class TestExportToPcbWay(DirectApiTestCase):
    def _mock_response(self, payload=None, json_error=None, http_error=None):
        response = Mock()
        response.text = "response body"
        if http_error is None:
            response.raise_for_status.return_value = None
        else:
            response.raise_for_status.side_effect = http_error
        if json_error is None:
            response.json.return_value = payload
        else:
            response.json.side_effect = json_error
        return response

    def _post_side_effect(self, response, uploaded_paths):
        def post(_url, files, timeout):
            uploaded_paths.append(Path(files["file"][1].name))
            return response

        return post

    @patch("build123d.exporters3d.webbrowser.open", return_value=True)
    @patch("build123d.exporters3d.export_step")
    @patch("build123d.exporters3d.requests.post")
    def test_export_to_pcbway_success(
        self,
        mock_post,
        mock_export_step,
        mock_browser_open,
    ):
        redirect_url = "https://www.pcbway.com/rapid-prototyping/manufacture/test"
        response = self._mock_response({"state": "SUCCESS", "redirect": redirect_url})
        uploaded_paths = []
        mock_post.side_effect = self._post_side_effect(response, uploaded_paths)

        result = export_to_pcbway(Box(1, 1, 1))

        self.assertEqual(result, redirect_url)
        mock_export_step.assert_called_once()
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.kwargs["timeout"], (10, 120))
        mock_browser_open.assert_called_once_with(redirect_url, new=2)
        self.assertEqual(len(uploaded_paths), 1)
        self.assertFalse(uploaded_paths[0].exists())

    @patch("build123d.exporters3d.webbrowser.open")
    @patch("build123d.exporters3d.export_step")
    @patch("build123d.exporters3d.requests.post")
    def test_export_to_pcbway_http_error_removes_temp_file(
        self,
        mock_post,
        _mock_export_step,
        mock_browser_open,
    ):
        response = self._mock_response(http_error=requests.HTTPError("bad status"))
        uploaded_paths = []
        mock_post.side_effect = self._post_side_effect(response, uploaded_paths)

        with self.assertRaises(requests.HTTPError):
            export_to_pcbway(Box(1, 1, 1))

        mock_browser_open.assert_not_called()
        self.assertEqual(len(uploaded_paths), 1)
        self.assertFalse(uploaded_paths[0].exists())

    @patch("build123d.exporters3d.webbrowser.open")
    @patch("build123d.exporters3d.export_step")
    @patch("build123d.exporters3d.requests.post")
    def test_export_to_pcbway_non_json_response_removes_temp_file(
        self,
        mock_post,
        _mock_export_step,
        mock_browser_open,
    ):
        response = self._mock_response(json_error=ValueError("not json"))
        uploaded_paths = []
        mock_post.side_effect = self._post_side_effect(response, uploaded_paths)

        with self.assertRaisesRegex(RuntimeError, "non-JSON response"):
            export_to_pcbway(Box(1, 1, 1))

        mock_browser_open.assert_not_called()
        self.assertEqual(len(uploaded_paths), 1)
        self.assertFalse(uploaded_paths[0].exists())

    @patch("build123d.exporters3d.webbrowser.open")
    @patch("build123d.exporters3d.export_step")
    @patch("build123d.exporters3d.requests.post")
    def test_export_to_pcbway_failure_response_removes_temp_file(
        self,
        mock_post,
        _mock_export_step,
        mock_browser_open,
    ):
        response = self._mock_response({"state": "FAILED", "message": "no file"})
        uploaded_paths = []
        mock_post.side_effect = self._post_side_effect(response, uploaded_paths)

        with self.assertRaisesRegex(RuntimeError, "returned no redirect"):
            export_to_pcbway(Box(1, 1, 1))

        mock_browser_open.assert_not_called()
        self.assertEqual(len(uploaded_paths), 1)
        self.assertFalse(uploaded_paths[0].exists())

    @patch("build123d.exporters3d.webbrowser.open", return_value=False)
    @patch("build123d.exporters3d.export_step")
    @patch("build123d.exporters3d.requests.post")
    def test_export_to_pcbway_browser_warning(
        self,
        mock_post,
        _mock_export_step,
        _mock_browser_open,
    ):
        redirect_url = "https://www.pcbway.com/rapid-prototyping/manufacture/test"
        response = self._mock_response({"state": "SUCCESS", "redirect": redirect_url})
        uploaded_paths = []
        mock_post.side_effect = self._post_side_effect(response, uploaded_paths)

        with self.assertWarnsRegex(Warning, "webbrowser failed"):
            result = export_to_pcbway(Box(1, 1, 1))

        self.assertEqual(result, redirect_url)
        self.assertEqual(len(uploaded_paths), 1)
        self.assertFalse(uploaded_paths[0].exists())


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


if __name__ == "__main__":
    unittest.main()
