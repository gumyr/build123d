"""
NGSolve Interop Tests

name: test_ngsolve_interop.py
by:   build123d contributors
date: March 30th, 2026

desc: Test the build123d NGSolve/Netgen interoperability module.
      These tests verify behavior *without* ngsolve/netgen installed.

license:

    Copyright 2026 build123d contributors

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

import sys
import unittest
from unittest.mock import patch

from build123d import Cylinder, to_ngsolve_mesh


class TestNgsolveInteropImport(unittest.TestCase):
    """Tests that work without ngsolve/netgen installed."""

    def test_import_succeeds(self):
        """to_ngsolve_mesh should be importable without ngsolve installed."""
        self.assertTrue(callable(to_ngsolve_mesh))

    def test_missing_netgen_raises_helpful_error(self):
        """Calling to_ngsolve_mesh without netgen should raise ImportError."""
        part = Cylinder(5, 10)
        with patch.dict(sys.modules, {"netgen": None, "netgen.occ": None}):
            with self.assertRaises(ImportError) as ctx:
                to_ngsolve_mesh(part)
            self.assertIn("netgen", str(ctx.exception))
            self.assertIn("pip install", str(ctx.exception))

    def test_missing_ngsolve_raises_helpful_error(self):
        """Calling to_ngsolve_mesh without ngsolve should raise ImportError."""
        part = Cylinder(5, 10)
        with patch.dict(sys.modules, {"ngsolve": None}):
            with self.assertRaises(ImportError):
                to_ngsolve_mesh(part)


if __name__ == "__main__":
    unittest.main()
