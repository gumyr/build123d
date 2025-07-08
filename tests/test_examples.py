"""
build123d Example tests

name: test_examples.py
by:   fischman
date: February 21 2025

desc: Unit tests for the build123d examples, ensuring they don't raise.
"""

from pathlib import Path

import os
import sys
import tempfile
import unittest
import codecs


_examples_dir = Path(os.path.abspath(os.path.dirname(__file__))).parent / "examples"
_ttt_dir = Path(os.path.abspath(os.path.dirname(__file__))).parent / "docs/assets/ttt"

_MOCK_OCP_VSCODE_CONTENTS = """
from pathlib import Path
import sys
from unittest.mock import Mock
mock_module = Mock()
mock_module.show = Mock()
mock_module.show_object = Mock()
mock_module.show_all = Mock()
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
            cwd = tmpdir if 'benchy' not in path.name else _examples_dir
            oldwd = os.getcwd()
            try:
                os.chdir(cwd)
                with codecs.open(path, 'r', 'utf-8') as f:
                    example_source = f.read()
                exec(_MOCK_OCP_VSCODE_CONTENTS + example_source, {})
            finally: # Best-effort restore to previous state (examples should be safe)
                os.chdir(oldwd)
                sys.modules.pop("ocp_vscode", None)


    return assert_example_does_not_raise


class TestExamples(unittest.TestCase):
    """Tests build123d examples."""

for example in sorted(list(_examples_dir.iterdir()) + list(_ttt_dir.iterdir())):
    if example.name.startswith("_") or not example.name.endswith(".py"):
        continue
    setattr(
        TestExamples,
        f"test_{example.name.replace('.', '_')}",
        generate_example_test(example),
    )

if __name__ == "__main__":
    unittest.main()
