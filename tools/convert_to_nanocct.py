#!/usr/bin/env python
"""
name: convert_to_nanocct.py
by:   Gumyr
date: October 17th 2026

desc:

    Convert build123d from the OCP binding of Open CASCADE to nanocct.

    The two bindings expose the same OCCT packages, classes and methods, so
    most of the conversion is renaming imports. What differs is listed in
    nanocct's docs/Porting.md, and the preparation on the nanocct_prep branch
    already wrote build123d's own call sites in nanocct's form, behind the
    stand-ins in src/build123d/kernel.py. This script does the rest:

    1. Imports: ``from OCP.X import`` and ``import OCP.X as`` become
       ``nanocct``. The ``TopoDS`` namespace is a module in nanocct, so
       ``TopoDS`` leaves the ``from`` list and becomes
       ``import nanocct.TopoDS as TopoDS``. ``ShapeUpgrade_UnifySameDomain``
       comes from ``nanocct.AddOns.ShapeClean`` while OCCT #1541 is open.
    2. Collections: OCP's ``List_TopoDS_Shape`` and friends become nanocct's
       generics, ``NCollection_List[TopoDS_Shape]``, with the imports the
       element types need.
    3. The kernel stand-ins: ``build123d.kernel`` imports become the
       binding's own classes, ``list_shapes(x)`` becomes ``list(x)``, and
       ``src/build123d/kernel.py`` is deleted.
    4. Out-parameters: a method OCP binds with the C++ out-parameters as
       arguments is rewritten from the OUT_PARAMS table. A variable passed as
       an out-parameter becomes an assignment target,
       ``found = label.FindAttribute(guid, attr)`` ->
       ``found, attr = label.FindAttribute(guid)``, and a dummy such as the
       ``float()`` in ``BRep_Tool.Curve_s(e, float(), float())`` is dropped
       with ``[0]`` selecting the result. A call that passes a variable from
       an expression (an ``if`` test, say) cannot be rewritten and is
       reported: move it into a statement of its own. ``ParOnEdgeS1(n)[0]``
       loses its ``[0]``, the other way round.

    Configuration (pyproject.toml, the CI workflows, .pylintrc, the README
    badge) is not edited: the script lists every line in those files that
    still names OCP so they can be changed by hand.

    Dry run by default; nothing is written without --apply. The script is
    idempotent: a second run finds nothing to do.

    Examples:
        python tools/convert_to_nanocct.py
        python tools/convert_to_nanocct.py --apply
        python tools/convert_to_nanocct.py --root ../bd_warehouse src/bd_warehouse

license:

    Copyright 2026 Gumyr

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

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

#: OCP's collection class name prefixes, with the number of element types
#: each takes (a hasher may follow).
COLLECTION_KINDS = {
    "Array1": 1,
    "Array2": 1,
    "HArray1": 1,
    "HArray2": 1,
    "List": 1,
    "Sequence": 1,
    "HSequence": 1,
    "Map": 1,
    "IndexedMap": 1,
    "DataMap": 2,
    "IndexedDataMap": 2,
    "DoubleMap": 2,
    "DynamicArray": 1,
}

#: Element type tokens in OCP's collection names -> (nanocct spelling, the
#: nanocct module that provides it, or None for a Python builtin).
ELEMENT_TYPES = {
    "double": ("float", None),
    "int": ("int", None),
    "bool": ("bool", None),
    "TopoDS_Shape": ("TopoDS_Shape", "nanocct.TopoDS"),
    "TopoDS_Vertex": ("TopoDS_Vertex", "nanocct.TopoDS"),
    "TopoDS_Edge": ("TopoDS_Edge", "nanocct.TopoDS"),
    "TopoDS_Wire": ("TopoDS_Wire", "nanocct.TopoDS"),
    "TopoDS_Face": ("TopoDS_Face", "nanocct.TopoDS"),
    "TopoDS_Shell": ("TopoDS_Shell", "nanocct.TopoDS"),
    "TopoDS_Solid": ("TopoDS_Solid", "nanocct.TopoDS"),
    "TopoDS_Compound": ("TopoDS_Compound", "nanocct.TopoDS"),
    "gp_Pnt": ("gp_Pnt", "nanocct.gp"),
    "gp_Pnt2d": ("gp_Pnt2d", "nanocct.gp"),
    "gp_Vec": ("gp_Vec", "nanocct.gp"),
    "gp_Vec2d": ("gp_Vec2d", "nanocct.gp"),
    "gp_Dir": ("gp_Dir", "nanocct.gp"),
    "gp_XYZ": ("gp_XYZ", "nanocct.gp"),
    "gp_Trsf": ("gp_Trsf", "nanocct.gp"),
    "TDF_Label": ("TDF_Label", "nanocct.TDF"),
    "TCollection_AsciiString": ("TCollection_AsciiString", "nanocct.TCollection"),
    "TCollection_ExtendedString": ("TCollection_ExtendedString", "nanocct.TCollection"),
    "TCollection_HAsciiString": ("TCollection_HAsciiString", "nanocct.TCollection"),
}

#: Hasher tokens that may end a map's name.
HASHERS = {
    "TopTools_ShapeMapHasher": ("TopTools_ShapeMapHasher", "nanocct.TopTools"),
}

#: The kernel stand-ins and what replaces each after the conversion.
KERNEL_REPLACEMENTS = {
    "BRep_Tool": "from nanocct.BRep import BRep_Tool",
    "BRepTools": "from nanocct.BRepTools import BRepTools",
    "BinTools": "from nanocct.BinTools import BinTools",
    "STEPCAFControl_Writer": "from nanocct.STEPCAFControl import STEPCAFControl_Writer",
    "StlAPI_Writer": "from nanocct.StlAPI import StlAPI_Writer",
    "list_shapes": None,  # calls become list(...)
}


@dataclass(frozen=True)
class OutParams:
    """How nanocct returns what OCP takes as out-parameter arguments."""

    #: OCP argument count -> the leading arguments nanocct keeps
    keep: dict[int, int]
    #: values nanocct returns, OCP's result first; a tuple when more than one
    results: int
    #: nanocct's name when an overload collision gives it a suffix
    rename: str | None = None


#: Methods matched by name and argument count, whichever class they are on.
OUT_PARAMS = {
    "Curve_s": OutParams({3: 1, 4: 2}, 3),
    "CurveOnSurface_s": OutParams({4: 2}, 3),
    "CurveOnPlane_s": OutParams({5: 3}, 3),
    "FindAttribute": OutParams({2: 1}, 2),
    "FindFont": OutParams({2: 2}, 2),  # the aspect is in/out: still passed
    "NewDocument": OutParams({2: 1}, 1, rename="NewDocument__TDocStd_Document"),
}

#: Methods that return a 1-tuple in OCP and a value in nanocct.
ONE_TUPLE_METHODS = {"ParOnEdgeS1", "ParOnEdgeS2", "ParOnFaceS1", "ParOnFaceS2"}

ADDON_COMMENT = (
    "# OCCT #1541 workaround; back to nanocct.ShapeUpgrade once OCCT is fixed"
)

#: Files whose remaining OCP mentions are listed for manual attention.
CONFIG_FILES = [
    "pyproject.toml",
    ".pylintrc",
    "mypy.ini",
    "README.md",
    ".readthedocs.yaml",
    ".github/workflows/test.yml",
    ".github/workflows/lint.yml",
    ".github/workflows/type.yml",
    ".github/actions/setup/action.yml",
]
CONFIG_PATTERN = re.compile(r"cadquery[-_]ocp|\bOCP\b|3\.11|py311")


# ---------------------------------------------------------------------------
# Collection names
# ---------------------------------------------------------------------------


@dataclass
class Needs:
    """Imports a rewrite needs: nanocct module -> names."""

    by_module: dict[str, set[str]] = field(default_factory=dict)

    def add(self, module: str | None, name: str) -> None:
        """Need ``name`` from ``module``; a builtin (module None) needs nothing."""
        if module is not None:
            self.by_module.setdefault(module, set()).add(name)

    def update(self, other: Needs) -> None:
        """Add everything ``other`` needs."""
        for module, names in other.by_module.items():
            self.by_module.setdefault(module, set()).update(names)


def parse_collection(name: str) -> tuple[str, Needs] | None:
    """nanocct's generic spelling of an OCP collection class name, with the
    imports it needs, or None when the name is not one."""
    rest = _parse_collection_rest(name)
    if rest is None or rest[1] != "":
        return None
    (expr, needs), _ = rest
    return expr, needs


def _parse_collection_rest(text: str) -> tuple[tuple[str, Needs], str] | None:
    """Parse one collection from the start of text; return it and the rest."""
    for kind, arity in sorted(COLLECTION_KINDS.items(), key=lambda k: -len(k[0])):
        prefix = kind + "_"
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix) :]
        needs = Needs()
        needs.add("nanocct.NCollection", f"NCollection_{kind}")
        args: list[str] = []
        for _ in range(arity):
            parsed = _parse_element(rest)
            if parsed is None:
                return None
            (expr, element_needs), rest = parsed
            needs.update(element_needs)
            args.append(expr)
            rest = rest[1:] if rest.startswith("_") else rest
        for token, (spelling, module) in HASHERS.items():
            # only the map kinds take a hasher; a nested list must leave it
            # to the map that holds it
            if "Map" in kind and (rest == token or rest.startswith(token + "_")):
                args.append(spelling)
                needs.add(module, spelling)
                rest = rest[len(token) :]
                rest = rest[1:] if rest.startswith("_") else rest
        return (f"NCollection_{kind}[{', '.join(args)}]", needs), rest
    return None


def _parse_element(text: str) -> tuple[tuple[str, Needs], str] | None:
    """Parse one element type, a nested collection or a known type token."""
    nested = _parse_collection_rest(text)
    if nested is not None:
        return nested
    for token, (spelling, module) in sorted(
        ELEMENT_TYPES.items(), key=lambda t: -len(t[0])
    ):
        if text == token or text.startswith(token + "_"):
            needs = Needs()
            needs.add(module, spelling)
            return (spelling, needs), text[len(token) :]
    return None


# ---------------------------------------------------------------------------
# One file
# ---------------------------------------------------------------------------


@dataclass
class Edit:
    """A replacement of the source between two character offsets."""

    start: int
    end: int
    text: str


@dataclass
class Report:
    """What a run changed, patched and left for a person to do."""

    changed: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    manual: list[str] = field(default_factory=list)


class FileConverter:
    """Collect and apply the edits for one Python file."""

    def __init__(self, path: Path, source: str, report: Report):
        self.path = path
        self.source = source
        self.report = report
        self.tree = ast.parse(source)
        self.line_offsets = [0]
        for line in source.splitlines(keepends=True):
            self.line_offsets.append(self.line_offsets[-1] + len(line))
        self.edits: list[Edit] = []
        self.needs = Needs()
        self.imported = self._imported_names()
        self.last_import_end = 0
        # the end of the last module-level OCP import that stays a statement:
        # where the kernel stand-ins' replacements go, among the binding's
        # other imports rather than in the first-party block
        self.last_binding_import_end = 0
        self.kernel_lines: list[str] = []
        # names the generated imports provide, per scope: the module, or a run
        # of consecutive import statements inside one function
        self.provided: dict[tuple[int, int], set[str]] = {}
        self._last_local = (0, 0, 0)  # column, end line, block start line
        # calls a statement rule rewrote, or that are in nanocct's form
        # already, which the expression rule must leave alone
        self.handled: set[int] = set()

    def scope_key(self, node: ast.stmt) -> tuple[int, int]:
        """(column, block start line) of the import scope a statement is in;
        module-level statements share (0, 0)."""
        if node.col_offset == 0:
            return (0, 0)
        column, end_line, block = self._last_local
        assert node.end_lineno is not None
        if column != node.col_offset or node.lineno > end_line + 1:
            block = node.lineno
        self._last_local = (node.col_offset, node.end_lineno, block)
        return (node.col_offset, block)

    # -- positions ---------------------------------------------------------

    def offset(self, line: int, col: int) -> int:
        """Character offset of a (1-based line, column) position."""
        return self.line_offsets[line - 1] + col

    def span(self, node: ast.stmt | ast.expr) -> tuple[int, int]:
        """The node's start and end offsets in the source."""
        assert node.end_lineno is not None and node.end_col_offset is not None
        return (
            self.offset(node.lineno, node.col_offset),
            self.offset(node.end_lineno, node.end_col_offset),
        )

    def segment(self, node: ast.stmt | ast.expr) -> str:
        """The node's source text."""
        start, end = self.span(node)
        return self.source[start:end]

    def replace(self, node: ast.stmt | ast.expr, text: str) -> None:
        """Queue the replacement of the node's source text; an empty
        replacement removes the statement's whole lines."""
        start, end = self.span(node)
        if text == "":
            start = self.offset(node.lineno, 0)
            if end < len(self.source) and self.source[end] == "\n":
                end += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)) and node.col_offset == 0:
            self.last_binding_import_end = max(self.last_binding_import_end, end)
        self.edits.append(Edit(start, end, text))

    def _imported_names(self) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
        return names

    # -- the rules ---------------------------------------------------------

    def convert(self) -> str | None:
        """The converted source, or None when nothing changes."""
        for node in ast.walk(self.tree):  # parents before children
            if isinstance(node, ast.ImportFrom):
                self.import_from(node)
            elif isinstance(node, ast.Import):
                self.import_(node)
            elif isinstance(node, (ast.Assign, ast.Expr)):
                self.statement(node)
            elif isinstance(node, ast.Name):
                self.name(node)
            elif isinstance(node, ast.Call):
                self.call(node)
            elif isinstance(node, ast.Subscript):
                self.subscript(node)
        self.add_needed_imports()
        if not self.edits:
            return None
        return self.apply()

    def import_from(self, node: ast.ImportFrom) -> None:
        """``from OCP.X import`` and ``from build123d.kernel import``."""
        module = node.module or ""
        if node.col_offset == 0:
            self.last_import_end = max(self.last_import_end, self.span(node)[1])
        if module == "OCP.collections":
            self.collections_import(node)
            return
        names = [alias.name for alias in node.names]
        if module == "build123d.kernel":
            # the stand-ins become binding imports, placed with the others
            self.kernel_lines.extend(
                replacement
                for name in names
                if (replacement := KERNEL_REPLACEMENTS.get(name)) is not None
            )
            self.replace(node, "")
            return
        if module == "OCP.TopoDS" and "TopoDS" in names:
            others = [n for n in names if n != "TopoDS"]
            lines = []
            if others:
                lines.append(self.from_import("nanocct.TopoDS", others))
            lines.append("import nanocct.TopoDS as TopoDS")
            self.replace(node, "\n".join(lines))
            return
        if module == "OCP.ShapeUpgrade" and "ShapeUpgrade_UnifySameDomain" in names:
            others = [n for n in names if n != "ShapeUpgrade_UnifySameDomain"]
            lines = []
            if others:
                lines.append(self.from_import("nanocct.ShapeUpgrade", others))
            lines.append(ADDON_COMMENT)
            lines.append(
                "from nanocct.AddOns.ShapeClean import ShapeUpgrade_UnifySameDomain"
            )
            self.replace(node, "\n".join(lines))
            return
        if module == "OCP" or module.startswith("OCP."):
            text = self.segment(node)
            self.replace(node, text.replace("from OCP", "from nanocct", 1))

    def import_(self, node: ast.Import) -> None:
        """``import OCP.X as y``."""
        if node.col_offset == 0:
            self.last_import_end = max(self.last_import_end, self.span(node)[1])
        if any(a.name == "OCP" or a.name.startswith("OCP.") for a in node.names):
            text = self.segment(node)
            self.replace(node, re.sub(r"\bOCP\b", "nanocct", text))

    def name(self, node: ast.Name) -> None:
        """An OCP collection class name -> nanocct's generic spelling."""
        parsed = parse_collection(node.id)
        if parsed is None:
            return
        expr, needs = parsed
        self.replace(node, expr)
        self.needs.update(needs)

    def out_param_call(self, node: ast.Call) -> tuple[str, list[str | None]] | None:
        """For a call of an OUT_PARAMS method in OCP's form: nanocct's call
        text and the dropped arguments, each a variable name or None for a
        dummy value."""
        func = node.func
        if (
            not isinstance(func, ast.Attribute)
            or func.attr not in OUT_PARAMS
            or node.keywords
        ):
            return None
        spec = OUT_PARAMS[func.attr]
        keep = spec.keep.get(len(node.args))
        if keep is None:
            return None
        dropped = [a.id if isinstance(a, ast.Name) else None for a in node.args[keep:]]
        args = ", ".join(self.segment(a) for a in node.args[:keep])
        name = spec.rename or func.attr
        return f"{self.segment(func.value)}.{name}({args})", dropped

    def statement(self, node: ast.Assign | ast.Expr) -> None:
        """A statement whose value is an out-parameter call: the variables
        passed as out-parameters become targets of the call's results."""
        value = node.value
        if not isinstance(value, ast.Call):
            return
        parsed = self.out_param_call(value)
        if parsed is None:
            return
        call, dropped = parsed
        func = value.func
        assert isinstance(func, ast.Attribute)
        results = OUT_PARAMS[func.attr].results
        has_return = results > len(dropped)
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                self.handled.add(id(value))  # a tuple target: nanocct's form
                return
            if not any(dropped) and results == 1:
                return  # the expression rule rewrites the call
            targets = [node.targets[0].id] + [n or "_" for n in dropped]
            targets += ["_"] * (results - len(targets))
        else:
            if not any(dropped):
                return
            targets = (["_"] if has_return else []) + [n or "_" for n in dropped]
        self.handled.add(id(value))
        self.replace(node, f"{', '.join(targets)} = {call}")

    def call(self, node: ast.Call) -> None:
        """``list_shapes`` and out-parameter calls used as expressions."""
        func = node.func
        # list_shapes(x) -> list(x)
        if isinstance(func, ast.Name) and func.id == "list_shapes":
            self.replace(func, "list")
            return
        if id(node) in self.handled:
            return
        parsed = self.out_param_call(node)
        if parsed is None:
            return
        call, dropped = parsed
        assert isinstance(func, ast.Attribute)
        if any(dropped):
            self.report.manual.append(
                f"{self.path}:{node.lineno}: {func.attr} fills "
                f"{', '.join(n for n in dropped if n)} from an expression; "
                "move the call into a statement of its own"
            )
            return
        # BRep_Tool.Curve_s(e, float(), float()) -> BRep_Tool.Curve_s(e)[0]
        index = "[0]" if OUT_PARAMS[func.attr].results > 1 else ""
        self.replace(node, call + index)

    def subscript(self, node: ast.Subscript) -> None:
        """``[0]`` on a call: dropped when the method returns a 1-tuple in
        OCP and the value in nanocct; kept, and the call left alone, when it
        selects an out-parameter method's result already."""
        value = node.value
        if (
            not isinstance(value, ast.Call)
            or not isinstance(value.func, ast.Attribute)
            or not isinstance(node.slice, ast.Constant)
            or not isinstance(node.slice.value, int)
        ):
            return
        if value.func.attr in OUT_PARAMS:
            self.handled.add(id(value))
        # extrema.ParOnEdgeS2(1)[0] -> extrema.ParOnEdgeS2(1)
        elif value.func.attr in ONE_TUPLE_METHODS and node.slice.value == 0:
            self.replace(node, self.segment(value))

    # -- imports the rewrites need ------------------------------------------

    def from_import(self, module: str, names: list[str]) -> str:
        """A ``from module import ...`` statement, parenthesized when long."""
        names = sorted(set(names))
        if len(names) == 1:
            return f"from {module} import {names[0]}"
        body = "".join(f"    {n},\n" for n in names)
        return f"from {module} import (\n{body})"

    def import_lines(self, needs: Needs, scope: tuple[int, int]) -> str:
        """The nanocct imports ``needs`` still lacks in ``scope``: what the
        module imports already, or an earlier generated statement of the
        same scope provides, is left out."""
        provided = self.provided.setdefault(scope, set())
        lines = []
        for module in sorted(needs.by_module):
            names = [
                n
                for n in sorted(needs.by_module[module])
                if n not in self.imported and n not in provided
            ]
            if names:
                lines.append(self.from_import(module, names))
                provided.update(names)
                if scope == (0, 0):
                    self.imported.update(names)
        return "\n".join(lines)

    def collections_import(self, node: ast.ImportFrom) -> None:
        """Replace ``from OCP.collections import ...`` by the nanocct imports
        its names need; a statement inside a function gets its own."""
        needs = Needs()
        for alias in node.names:
            parsed = parse_collection(alias.name)
            if parsed is None:
                self.report.manual.append(
                    f"{self.path}:{node.lineno}: unknown collection {alias.name}"
                )
                continue
            needs.update(parsed[1])
        self.replace(node, self.import_lines(needs, self.scope_key(node)))

    def add_needed_imports(self) -> None:
        """The kernel stand-ins' replacements after the module's last binding
        import, and imports for collection names used without an
        OCP.collections statement of their own after the last import."""
        if self.kernel_lines:
            at = self.last_binding_import_end or self.last_import_end
            self.edits.append(Edit(at, at, "\n" + "\n".join(self.kernel_lines)))
        text = self.import_lines(self.needs, (0, 0))
        if text:
            self.edits.append(
                Edit(self.last_import_end, self.last_import_end, "\n" + text)
            )

    # -- apply ---------------------------------------------------------------

    def apply(self) -> str:
        """The source with every queued edit applied, last to first."""
        source = self.source
        for edit in sorted(self.edits, key=lambda e: (e.start, e.end), reverse=True):
            source = source[: edit.start] + edit.text + source[edit.end :]
        # a removed statement leaves an empty line behind; drop it
        return (
            re.sub(r"\n[ \t]*\n(?=\n)", "\n", source)
            if source != self.source
            else source
        )


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


SKIP_DIRS = {"__pycache__", "site-packages", "build", "dist"}


def python_files(root: Path, paths: list[str]) -> list[Path]:
    """The .py files under each path, skipping hidden, cache and environment
    directories (a stray .venv under src/ must not be converted)."""
    found: list[Path] = []
    for rel in paths:
        base = root / rel
        if base.is_file():
            found.append(base)
            continue
        for path in sorted(base.rglob("*.py")):
            parts = path.relative_to(base).parts[:-1]
            if any(p.startswith(".") or p in SKIP_DIRS for p in parts):
                continue
            found.append(path)
    return found


def config_checklist(root: Path, report: Report) -> None:
    """List the configuration lines that still name OCP or Python 3.11."""
    for rel in CONFIG_FILES:
        path = root / rel
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if CONFIG_PATTERN.search(line):
                report.manual.append(f"{rel}:{number}: {line.strip()}")


def run_black(paths: list[Path]) -> None:
    """Format the changed files when black is on the path."""
    if not paths or shutil.which("black") is None:
        return
    subprocess.run(["black", "-q", *map(str, paths)], check=False)


def main() -> int:
    """Parse the arguments and run the conversion."""
    parser = argparse.ArgumentParser(
        description="Convert build123d (or a package built on it) from OCP to nanocct."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["src/build123d", "tests"],
        help="files or directories under --root to convert (default: src/build123d tests)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: the parent of tools/)",
    )
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--verbose", action="store_true", help="list every edited file")
    args = parser.parse_args()
    root: Path = args.root.resolve()

    report = Report()
    for path in python_files(root, args.paths):
        if path.name == "kernel.py" and path.parent == root / "src" / "build123d":
            continue
        source = path.read_text(encoding="utf-8")
        converter = FileConverter(path.relative_to(root), source, report)
        converted = converter.convert()
        if converted is None:
            continue
        report.changed.append(path)
        if args.apply:
            path.write_text(converted, encoding="utf-8")

    kernel = root / "src" / "build123d" / "kernel.py"
    if kernel.exists():
        report.notes.append("src/build123d/kernel.py: deleted")
        if args.apply:
            kernel.unlink()

    if args.apply:
        run_black([p for p in report.changed if p.exists()])

    config_checklist(root, report)

    mode = "applied" if args.apply else "dry run"
    changed = sorted(set(report.changed))
    print(f"{mode}: {len(changed)} file(s) to change")
    if args.verbose or not args.apply:
        for path in changed:
            print(f"  {path.relative_to(root)}")
    if report.notes:
        print("notes:")
        for note in report.notes:
            print(f"  {note}")
    if report.manual:
        print("by hand:")
        for item in report.manual:
            print(f"  {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
