"""
build123d example mode tests

name: test_example_modes.py
by:   Gumyr
date: November 16th 2026

desc:
    The examples and the challenge solutions are each written twice:
    ``name.py`` in builder mode and ``name_algebra.py`` in algebra mode.
    test_examples.py checks that every script runs. This checks that the two
    versions of each still make the same model, so that a change to one that
    is not made to the other is caught.

    Each script is run on its own and the shapes it leaves in its globals
    under a name the other version also uses are measured. The result of a
    pair is taken to be the largest of them, and the two must agree in kind
    (solid, face or line), in size (volume, area or length) and in extent.

    A script that fails to run fails its pair, so test_examples.py leaves
    the paired scripts to this file and each is run once.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_root = Path(os.path.abspath(os.path.dirname(__file__))).parent
_examples_dir = _root / "examples"
_ttt_dir = _root / "docs/challenges/ttt"

# How closely the two versions must agree, as a fraction. The same model
# built by a different sequence of operations differs in the last few digits,
# and by more where a fillet or draft is involved.
TOLERANCE = 1e-3

# Pairs that are not expected to agree, each with the reason. Both versions are
# still run. None of them is shown on the Examples page.
KNOWN_DIFFERENCES = {
    "boxes_on_faces": "the two versions give their result different names",
    "build123d_customizable_logo": "the two versions lay the logo out differently",
    "extrude": "the two versions number their examples differently",
    "intersecting_chamfers": "the algebra version's result is blocks2, not blocks",
}

# Pairs held to a looser tolerance, each with the reason.
LOOSER = {
    # A builder cleans the text it is given and algebra mode does not, and
    # cleaning moves the outline of some fonts' glyphs: by 0.02% of the area
    # in Arial, 0.27% in Courier, 0.28% in the font the Linux runners use.
    "build123d_logo": 1e-2,
}

# Runs one script with the viewer mocked, then prints what it made under the
# names it was asked about.
_MEASURE = r"""
import json, sys
from unittest.mock import MagicMock

_viewer = MagicMock()
for _name in (
    "show", "show_object", "show_all", "save_screenshot", "set_port",
    "set_defaults", "Camera", "ColorMap", "reset_show", "ImageFace",
):
    setattr(_viewer, _name, MagicMock())
sys.modules["ocp_viewer"] = _viewer
sys.modules["ocp_vscode"] = _viewer

_scope = {"__name__": "__main__"}
with open(sys.argv[1], encoding="utf-8") as _source:
    exec(compile(_source.read(), sys.argv[1], "exec"), _scope)

from build123d import Compound, Shape
from build123d.build_common import Builder


def _shapes(value):
    if isinstance(value, Builder):
        value = value._obj
    if isinstance(value, Shape):
        return [value]
    if isinstance(value, (list, tuple)) and value:
        if all(isinstance(item, Shape) for item in value):
            return list(value)
    return []


_found = {}
for _name in sys.argv[2:]:
    _value = _scope.get(_name)
    _made = [shape for shape in _shapes(_value) if not shape.is_empty]
    if not _made:
        continue
    try:
        _whole = _made[0] if len(_made) == 1 else Compound(children=list(_made))
        _box = _whole.bounding_box()
        _solids = [solid for shape in _made for solid in shape.solids()]
        _faces = [] if _solids else [f for shape in _made for f in shape.faces()]
        if _solids:
            _kind, _measure = 3, sum(solid.volume for solid in _solids)
        elif _faces:
            _kind, _measure = 2, sum(face.area for face in _faces)
        else:
            _edges = [edge for shape in _made for edge in shape.edges()]
            _kind, _measure = 1, sum(edge.length for edge in _edges)
    except Exception:  # a shape that cannot be measured is not the result
        continue
    _found[_name] = {
        "kind": _kind,
        "measure": _measure,
        "size": [_box.size.X, _box.size.Y, _box.size.Z],
        "diagonal": _box.diagonal,
    }
print("MEASURED " + json.dumps(_found))
"""


def _names(path: Path) -> set[str]:
    """The names a script assigns, found without running it"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Store)
        and not node.id.startswith("_")
    }


def _measure(path: Path, names: list[str]) -> dict:
    """Run a script and return what it left behind under the given names"""
    with tempfile.TemporaryDirectory(prefix=f"build123d_test_modes_{path.stem}") as tmp:
        # as in test_examples.py: scripts write files, so run them elsewhere,
        # except the one that reads a file from its own folder
        cwd = tmp if "benchy" not in path.name else str(path.parent)
        got = subprocess.run(
            [sys.executable, "-c", _MEASURE, str(path), *names],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
    for line in reversed(got.stdout.splitlines()):
        if line.startswith("MEASURED "):
            return json.loads(line[len("MEASURED ") :])
    raise AssertionError(f"{path.name} did not run: {got.stderr[-2000:]}")


def generate_mode_test(
    builder_path: Path,
    algebra_path: Path,
    tolerance: float = TOLERANCE,
    compare: bool = True,
):
    """Generate and return a function to compare the two versions of an example."""

    def assert_modes_agree(self):
        names = sorted(_names(builder_path) & _names(algebra_path)) if compare else []
        builder = _measure(builder_path, names)
        algebra = _measure(algebra_path, names)
        if not compare:  # a known difference: it is enough that both ran
            return

        common = [name for name in builder if name in algebra]
        self.assertTrue(
            common,
            f"{builder_path.name} and {algebra_path.name} have no result of the "
            f"same name to compare: {sorted(builder)} / {sorted(algebra)}",
        )
        # the result: the largest thing both versions call by the same name
        name = max(
            common,
            key=lambda n: (
                builder[n]["kind"],
                round(builder[n]["diagonal"], 3),
                builder[n]["measure"],
            ),
        )
        ours, theirs = builder[name], algebra[name]
        where = f"'{name}' in {builder_path.name} and {algebra_path.name}"

        self.assertEqual(ours["kind"], theirs["kind"], f"dimension of {where}")
        self.assertLess(
            abs(ours["measure"] - theirs["measure"]),
            tolerance * abs(ours["measure"]),
            f"volume, area or length of {where}: "
            f"{ours['measure']} / {theirs['measure']}",
        )
        for mine, yours in zip(ours["size"], theirs["size"]):
            self.assertLess(
                abs(mine - yours),
                tolerance * max(ours["size"]),
                f"extent of {where}: {ours['size']} / {theirs['size']}",
            )

    return assert_modes_agree


class TestExampleModes(unittest.TestCase):
    """Tests that the builder and algebra versions of each example agree."""


for directory in (_examples_dir, _ttt_dir):
    for algebra_version in sorted(directory.glob("*_algebra.py")):
        stem = algebra_version.name[: -len("_algebra.py")]
        builder_version = directory / f"{stem}.py"
        if not builder_version.exists():
            continue
        mode_check = generate_mode_test(
            builder_version,
            algebra_version,
            LOOSER.get(stem, TOLERANCE),
            compare=stem not in KNOWN_DIFFERENCES,
        )
        setattr(
            TestExampleModes,
            f"test_{stem.replace('-', '_').replace('.', '_')}",
            mode_check,
        )

if __name__ == "__main__":
    unittest.main()
