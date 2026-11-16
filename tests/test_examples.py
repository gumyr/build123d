"""
build123d Example tests

name: test_examples.py
by:   fischman
date: February 21 2025

desc: Unit tests for the build123d examples, ensuring they don't raise.
      Examples written in both builder and algebra mode are run, and the two
      versions compared, by test_example_modes.py instead.
"""

from pathlib import Path

import os
import subprocess
import sys
import tempfile
import unittest

_examples_dir = Path(os.path.abspath(os.path.dirname(__file__))).parent / "examples"
_ttt_dir = (
    Path(os.path.abspath(os.path.dirname(__file__))).parent / "docs/challenges/ttt"
)

_MOCK_OCP_VSCODE_CONTENTS = """
from pathlib import Path

import re
import sys
from unittest.mock import Mock
mock_module = Mock()
mock_module.show = Mock()
mock_module.show_object = Mock()
mock_module.show_all = Mock()
sys.modules["ocp_viewer"] = mock_module
sys.modules["ocp_vscode"] = mock_module
"""


def generate_example_test(path: Path):
    """Generate and return a function to test the example at `path`."""
    name = path.name

    def assert_example_does_not_raise(self):
        with tempfile.TemporaryDirectory(
            prefix=f"build123d_test_examples_{name}"
        ) as tmpdir:
            # More examples emit output files than read input files,
            # so default to running with a temporary directory to
            # avoid cluttering the git working directory.  For
            # examples that want to read assets from the examples
            # directory, use that.  If an example is added in the
            # future that wants to both read assets from the examples
            # directory and write output files, deal with it then.
            cwd = tmpdir if "benchy" not in path.name else _examples_dir
            mock_ocp_vscode = Path(tmpdir) / "_mock_ocp_vscode.py"
            with open(mock_ocp_vscode, "w", encoding="utf-8") as f:
                f.write(_MOCK_OCP_VSCODE_CONTENTS)
            cmd = (
                f"exec(open(r'{mock_ocp_vscode}', encoding='utf-8').read()); "
                f"exec(open(r'{path}', encoding='utf-8').read())"
            )
            got = subprocess.run(
                [sys.executable, "-c", cmd],
                capture_output=True,
                cwd=cwd,
                check=False,
            )
            self.assertEqual(
                0, got.returncode, f"stdout/stderr: {got.stdout} / {got.stderr}"
            )

    return assert_example_does_not_raise


class TestExamples(unittest.TestCase):
    """Tests build123d examples."""


def _is_paired(path: Path) -> bool:
    """True for a script with both a builder and an algebra version"""
    stem = path.name[: -len(".py")]
    if stem.endswith("_algebra"):
        return (path.parent / f"{stem[: -len('_algebra')]}.py").exists()
    return (path.parent / f"{stem}_algebra.py").exists()


for example in sorted(list(_examples_dir.iterdir()) + list(_ttt_dir.iterdir())):
    if example.name.startswith("_") or not example.name.endswith(".py"):
        continue
    if _is_paired(example):
        # test_example_modes.py runs both versions of a pair and compares them
        continue
    setattr(
        TestExamples,
        f"test_{example.name.replace('.', '_')}",
        generate_example_test(example),
    )

if __name__ == "__main__":
    unittest.main()
