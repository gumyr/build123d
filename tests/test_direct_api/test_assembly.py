"""
build123d imports

name: test_assembly.py
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

import re
import unittest

from build123d.topology import Compound, Solid


class TestAssembly(unittest.TestCase):
    @staticmethod
    def create_test_assembly() -> Compound:
        box = Solid.make_box(1, 1, 1)
        box.orientation = (45, 45, 0)
        box.label = "box"
        sphere = Solid.make_sphere(1)
        sphere.label = "sphere"
        sphere.position = (1, 2, 3)
        assembly = Compound(label="assembly", children=[box])
        sphere.parent = assembly
        return assembly

    def assertTopoEqual(self, actual_topo: str, expected_topo_lines: list[str]):
        actual_topo_lines = actual_topo.splitlines()
        self.assertEqual(len(actual_topo_lines), len(expected_topo_lines))
        for actual_line, expected_line in zip(actual_topo_lines, expected_topo_lines):
            start, end = re.split(r"at 0x[0-9a-f]+,", expected_line, maxsplit=2, flags=re.I)
            self.assertTrue(actual_line.startswith(start))
            self.assertTrue(actual_line.endswith(end))

    def test_attributes(self):
        box = Solid.make_box(1, 1, 1)
        box.label = "box"
        sphere = Solid.make_sphere(1)
        sphere.label = "sphere"
        assembly = Compound(label="assembly", children=[box])
        sphere.parent = assembly

        self.assertEqual(len(box.children), 0)
        self.assertEqual(box.label, "box")
        self.assertEqual(box.parent, assembly)
        self.assertEqual(sphere.parent, assembly)
        self.assertEqual(len(assembly.children), 2)

    def test_show_topology_compound(self):
        assembly = TestAssembly.create_test_assembly()
        expected = [
            "assembly   Compound at 0x7fced0fd1b50, Location(p=(0.00, 0.00, 0.00), o=(-0.00, 0.00, -0.00))",
            "├── box    Solid    at 0x7fced102d3a0, Location(p=(0.00, 0.00, 0.00), o=(45.00, 45.00, -0.00))",
            "└── sphere Solid    at 0x7fced0fd1f10, Location(p=(1.00, 2.00, 3.00), o=(-0.00, 0.00, -0.00))",
        ]
        self.assertTopoEqual(assembly.show_topology("Solid"), expected)

    def test_show_topology_shape_location(self):
        assembly = TestAssembly.create_test_assembly()
        expected = [
            "Solid        at 0x7f3754501530, Position(1.0, 2.0, 3.0)",
            "└── Shell    at 0x7f3754501a70, Position(1.0, 2.0, 3.0)",
            "    └── Face at 0x7f3754501030, Position(1.0, 2.0, 3.0)",
        ]
        self.assertTopoEqual(
            assembly.children[1].show_topology("Face", show_center=False), expected
        )

    def test_show_topology_shape(self):
        assembly = TestAssembly.create_test_assembly()
        expected = [
            "Solid        at 0x7f6279043ab0, Center(1.0, 2.0, 3.0)",
            "└── Shell    at 0x7f62790438f0, Center(1.0, 2.0, 3.0)",
            "    └── Face at 0x7f62790439f0, Center(1.0, 2.0, 3.0)",
        ]
        self.assertTopoEqual(assembly.children[1].show_topology("Face"), expected)

    def test_remove_child(self):
        assembly = TestAssembly.create_test_assembly()
        self.assertEqual(len(assembly.children), 2)
        assembly.children = list(assembly.children)[1:]
        self.assertEqual(len(assembly.children), 1)

    def test_do_children_intersect(self):
        (
            overlap,
            pair,
            distance,
        ) = TestAssembly.create_test_assembly().do_children_intersect()
        self.assertFalse(overlap)
        box = Solid.make_box(1, 1, 1)
        box.orientation = (45, 45, 0)
        box.label = "box"
        sphere = Solid.make_sphere(1)
        sphere.label = "sphere"
        sphere.position = (0, 0, 0)
        assembly = Compound(label="assembly", children=[box])
        sphere.parent = assembly
        overlap, pair, distance = assembly.do_children_intersect()
        self.assertTrue(overlap)


if __name__ == "__main__":
    unittest.main()
