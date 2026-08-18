"""
build123d imports

name: test_import_export.py
by:   Gumyr
date: January 22, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import os
import tempfile
import unittest

from anytree import PreOrderIter

from build123d.exporters3d import export_brep, export_step
from build123d.importers import import_brep, import_step, import_stl
from build123d.geometry import Location
from build123d.mesher import Mesher
from build123d.topology import Compound, Shape, Solid


class TestImportExport(unittest.TestCase):
    def test_import_export(self):
        original_box = Solid.make_box(1, 1, 1)
        export_step(original_box, "test_box.step")
        step_box = import_step("test_box.step")
        self.assertTrue(step_box.is_valid)
        self.assertAlmostEqual(step_box.volume, 1, 5)
        export_brep(step_box, "test_box.brep")
        brep_box = import_brep("test_box.brep")
        self.assertTrue(brep_box.is_valid)
        self.assertAlmostEqual(brep_box.volume, 1, 5)
        os.remove("test_box.step")
        os.remove("test_box.brep")
        with self.assertRaises(FileNotFoundError):
            step_box = import_step("test_box.step")

    def test_import_stl(self):
        # export solid
        original_box = Solid.make_box(1, 2, 3)
        exporter = Mesher()
        exporter.add_shape(original_box)
        exporter.write("test.stl")

        # import as face
        stl_box = import_stl("test.stl")
        self.assertAlmostEqual(stl_box.position, (0, 0, 0), 5)

    def test_step_round_trip_preserves_assembly_child_locations(self):
        def labeled_node(root: Shape, label: str) -> Shape:
            return next(iter(PreOrderIter(root, filter_=lambda n: n.label == label)))

        box_a = Solid.make_box(1, 1, 1)
        box_a.label = "box_a"
        box_a.move(Location((10, 0, 0)))

        box_b = Solid.make_box(1, 1, 1)
        box_b.label = "box_b"
        box_b.move(Location((0, 15, 0), (0, 0, 45)))

        cylinder = Solid.make_cylinder(0.5, 2)
        cylinder.label = "cylinder"
        cylinder.move(Location((0, 0, 5), (90, 0, 0)))

        sub_assembly = Compound(label="sub_assembly", children=[box_a, cylinder])
        sub_assembly.move(Location((0, 0, 30), (0, 90, 0)))

        root_assembly = Compound(label="root_assembly", children=[sub_assembly, box_b])
        root_assembly.move(Location((3, 6, 9), (0, 0, 90)))

        expected_locations = {
            label: labeled_node(root_assembly, label).global_location
            for label in ("box_a", "box_b", "cylinder")
        }

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp_step:
            step_path = tmp_step.name
        try:
            export_step(root_assembly, step_path)
            reloaded = import_step(step_path)

            for label, expected in expected_locations.items():
                reloaded_node = labeled_node(reloaded, label)
                self.assertAlmostEqual(
                    reloaded_node.global_location.position,
                    expected.position,
                    places=5,
                )
                self.assertAlmostEqual(
                    reloaded_node.global_location.orientation,
                    expected.orientation,
                    places=5,
                )
        finally:
            os.remove(step_path)


if __name__ == "__main__":
    unittest.main()
