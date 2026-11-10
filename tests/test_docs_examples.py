"""
build123d docs example tests

name: test_docs_examples.py
by:   jdegenstein
date: July 16 2026

desc: Unit tests for the build123d examples in the docs subfolder.
"""

from pathlib import Path

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_docs_dir = Path(os.path.abspath(os.path.dirname(__file__))).parent / "docs"

_MOCK_OCP_VSCODE_CONTENTS = """
import sys
from unittest.mock import MagicMock

mock_ocp = MagicMock()
# Explicitly add properties so `from ocp_vscode import *` pulls them in
for attr in [
    "show", "show_object", "show_all", "save_screenshot", 
    "set_port", "set_defaults", "Camera", "ColorMap", "reset_show"
]:
    setattr(mock_ocp, attr, MagicMock())

sys.modules["ocp_vscode"] = mock_ocp

# Mock heavy optional dependencies so they don't crash the CI runner
mock_bd = MagicMock()
sys.modules["tcv_screenshots"] = mock_bd
"""

# fmt: off
IGNORE_FILES = {
    "conf.py",
    "build123d_lexer.py",
    "rigid_joints_pipe.py",  # ignored due to bd_warehouse dependency
    "technical_drawing.py",  # ^
    "rod_end.py",            # ^
}  # fmt: on

# skip "ttt" as that is covered by test_examples.py
IGNORE_DIRS = {"ttt", "_build", ".venv", "_static"}


def generate_docs_example_test(path: Path):
    name = path.stem

    def assert_example_does_not_raise(self):
        with tempfile.TemporaryDirectory(
            prefix=f"build123d_test_docs_{name}"
        ) as tmpdir:

            # Mirror the docs layout in the temp directory so that an example,
            # run from the copy of its own folder, finds the files it reads
            # and the folders it writes to at the same relative paths:
            # every "assets" folder, plus the data files beside the example.
            for assets_dir in _docs_dir.rglob("assets"):
                rel_assets = assets_dir.relative_to(_docs_dir)
                if assets_dir.is_dir() and not any(
                    part in IGNORE_DIRS and part != "ttt" for part in rel_assets.parts
                ):
                    shutil.copytree(
                        assets_dir, Path(tmpdir) / rel_assets, dirs_exist_ok=True
                    )

            run_dir = Path(tmpdir) / path.parent.relative_to(_docs_dir)
            run_dir.mkdir(parents=True, exist_ok=True)
            for file_obj in path.parent.glob("*.*"):
                if file_obj.is_file() and file_obj.suffix not in [".py", ".rst", ".md"]:
                    shutil.copy(file_obj, run_dir / file_obj.name)
            # ------------------------------------------------------------------------

            mock_ocp_vscode = Path(tmpdir) / "_mock_ocp_vscode.py"
            with open(mock_ocp_vscode, "w", encoding="utf-8") as f:
                f.write(_MOCK_OCP_VSCODE_CONTENTS)

            cmd = (
                f"exec(open(r'{mock_ocp_vscode}', encoding='utf-8').read()); "
                f"__file__ = r'{path}'; "
                f"exec(open(r'{path}', encoding='utf-8').read())"
            )

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            got = subprocess.run(
                [sys.executable, "-c", cmd],
                capture_output=True,
                cwd=run_dir,
                check=False,
                text=True,
                encoding="utf-8",
                env=env,
            )

            self.assertEqual(
                0,
                got.returncode,
                f"Example {path.name} failed!\nSTDOUT:\n{got.stdout}\nSTDERR:\n{got.stderr}",
            )

    return assert_example_does_not_raise


class TestDocsExamples(unittest.TestCase):
    """Tests build123d docs examples."""


# Recursively find all python files in the docs directory
for example in _docs_dir.rglob("*.py"):
    # Filter against ignore sets and underscore prefixes
    if example.name in IGNORE_FILES or example.name.startswith("_"):
        continue

    if any(part in IGNORE_DIRS for part in example.relative_to(_docs_dir).parts):
        continue

    # Create a safe test method name (e.g., test_topology_selection_examples_filter_geomtype)
    rel_path = example.relative_to(_docs_dir)
    test_name = (
        f"test_{str(rel_path.with_suffix('')).replace(os.sep, '_').replace('.', '_')}"
    )

    setattr(
        TestDocsExamples,
        test_name,
        generate_docs_example_test(example),
    )

if __name__ == "__main__":
    unittest.main()
