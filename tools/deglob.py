#!/usr/bin/env python
"""
name: deglob.py
by:   Gumyr
date: April 12th 2025

desc:

    A command-line script (deglob.py) that scans a Python file for references to
    symbols from the build123d library and outputs a 'from build123d import ...'
    line listing only the symbols that are actually used by that file.

    This is useful to replace wildcard imports like 'from build123d import *'
    with a more explicit import statement. By relying on Python's AST, this
    script can detect which build123d names are referenced, then generate
    an import statement listing only those names. This practice can help
    prevent polluting the global namespace and improve clarity.

    Examples:
        python deglob.py my_build123d_script.py
        python deglob.py -h

    Usage:
        deglob.py [-h] [--write] [--verbose] build123d_file
        Find all the build123d symbols in module.

        positional arguments:
        build123d_file  Path to the build123d file

        options:
        -h, --help      show this help message and exit
        --write         Overwrite glob import in input file, defaults to read-only and
                        printed to stdout
        --verbose       Increase verbosity when write is enabled, defaults to silent

    After parsing my_build123d_script.py, the script optionally prints a line such as:
        from build123d import Workplane, Solid

    Which you can then paste back into the file to replace the glob import.

    Module Contents:
        - parse_args(): Parse the command-line argument for the input file path.
        - count_glob_imports(): Count the number of occurences of a glob import.
        - find_used_symbols(): Parse Python source code to find referenced names.
        - main(): Orchestrates reading the file, analyzing symbols, and printing
        the replacement import line.


license:

    Copyright 2025 Gumyr

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

import argparse
import ast
import sys
from pathlib import Path
import re

import build123d


def parse_args():
    """
    Parse command-line arguments for the deglob tool.

    Returns:
        argparse.Namespace: An object containing the parsed command-line arguments:
        - build123d_file (Path): Path to the input build123d file.
    """
    parser = argparse.ArgumentParser(
        description="Find all the build123d symbols in module."
    )

    # Required positional argument
    parser.add_argument("build123d_file", type=Path, help="Path to the build123d file")
    parser.add_argument(
        "--write",
        help="Overwrite glob import in input file, defaults to read-only and printed to stdout",
        action="store_true",
    )
    parser.add_argument(
        "--verbose",
        help="Increase verbosity when write is enabled, defaults to silent",
        action="store_true",
    )

    args = parser.parse_args()

    return args


def count_glob_imports(source_code: str) -> int:
    """count_glob_imports

    Count the number of occurences of a glob import e.g. (from build123d import *)

    Args:
        source_code (str): contents of build123d program

    Returns:
        int: build123d glob import occurence count
    """
    tree = ast.parse(source_code)

    # count instances of glob usage
    glob_count = list(
        isinstance(node, ast.ImportFrom)
        and node.module == "build123d"
        and any(alias.name == "*" for alias in node.names)
        for node in ast.walk(tree)
    ).count(True)

    return glob_count


def find_used_symbols(source_code: str) -> set[str]:
    """find_used_symbols

    Extract all of the symbols from the source code into a set of strings.

    Args:
        source_code (str): contents of build123d program

    Returns:
        set[str]: extracted symbols
    """
    tree = ast.parse(source_code)

    symbols = set()

    # Create a custom version of visit_Name that records the symbol
    class SymbolFinder(ast.NodeVisitor):
        def visit_Name(self, node):
            # node.id is the variable name or symbol
            symbols.add(node.id)
            self.generic_visit(node)

    SymbolFinder().visit(tree)
    return symbols


def main():
    """
    Main entry point for the deglob script.

    Steps:
        1. Parse and validate command-line arguments for the target Python file.
        2. Read the file's source code.
        3. Use an AST-based check to confirm whether there is at least one
           'from build123d import *' statement in the code.
        4. Collect all referenced symbol names from the file's abstract syntax tree.
        5. Intersect these names with those found in build123d.__all__ to identify
           which build123d symbols are actually used.
        6A. Optionally print an import statement that explicitly imports only the used symbols.
        6B. Or optionally write the glob import replacement back to file

    Behavior:
        - If no 'from build123d import *' import is found, the script prints
          a message and exits.
        - If multiple glob imports appear, only a single explicit import line
          is generated regardless of the number of glob imports in the file.
        - Pre-existing non-glob imports are left unchanged in the user's code;
          they may result in redundant imports if the user chooses to keep them.

    Raises:
        SystemExit: If the file does not exist or if a glob import statement
                    isn't found.
    """
    # Get the command line arguments
    args = parse_args()

    # Check that the build123d file is valid
    if not args.build123d_file.exists():
        print(f"Error: file not found - {args.build123d_file}", file=sys.stderr)
        sys.exit(1)

    # Read the code
    with open(args.build123d_file, "r", encoding="utf-8") as f:
        code = f.read()

    # Get the glob import count
    glob_count = count_glob_imports(code)

    # Exit if no glob import was found
    if not glob_count:
        print("Glob import from build123d not found")
        sys.exit(0)

    # Extract the symbols
    used_symbols = find_used_symbols(code)

    # Find the imported build123d symbols
    actual_imports = sorted(used_symbols.intersection(set(build123d.__all__)))

    # Create the import statement to replace the glob import
    import_line = f"from build123d import {', '.join(actual_imports)}"

    if args.write:
        # Replace only the first instance
        updated_code = re.sub(r"from build123d import\s*\*", import_line, code, count=1)

        # Try to write code back to target file
        try:
            with open(args.build123d_file, "w", encoding="utf-8") as f:
                f.write(updated_code)
        except (PermissionError, OSError) as e:
            print(f"Error: Unable to write to file '{args.build123d_file}'. {e}")
            sys.exit(1)

        if glob_count and args.verbose:
            print(f"Replaced build123d glob import with '{import_line}'")

        if glob_count > 1:
            # NOTE: always prints warning if more than one glob import is found
            print(
                "Warning: more than one instance of glob import was detected "
                f"(count: {glob_count}), only the first instance was replaced"
            )
    else:
        print(import_line)


if __name__ == "__main__":
    main()
