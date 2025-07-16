"""

name: refactor_test_direct_api.py
by:   Gumyr
date: January 22, 2025

Description:
    This script automates the process of splitting a large test file into smaller, 
    more manageable test files based on class definitions. Each generated test file 
    includes necessary imports, an optional header with project and license information, 
    and the appropriate class definitions. Additionally, the script dynamically injects 
    shared utilities like the `AlwaysEqual` class only into files where they are needed.

Features:
    - Splits a large test file into separate files by test class.
    - Adds a standardized header with project details and an Apache 2.0 license.
    - Dynamically includes shared utilities like `AlwaysEqual` where required.
    - Supports `unittest` compatibility by adding a `unittest.main()` block for direct execution.
    - Ensures imports are cleaned and Python syntax is upgraded to modern standards using 
      `rope` and `pyupgrade`.

Usage:
    Run the script with the input file and output directory as arguments:
        python refactor_test_direct_api.py

Dependencies:
    - libcst: For parsing and analyzing the test file structure.
    - rope: For organizing and pruning unused imports.
    - pyupgrade: For upgrading Python syntax to the latest standards.

License:
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

from pathlib import Path
import libcst as cst
from libcst.metadata import PositionProvider, MetadataWrapper
import os
from rope.base.project import Project
from rope.refactor.importutils import ImportOrganizer
import subprocess
from datetime import datetime


class TestFileSplitter(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, module_content, output_dir):
        self.module_content = module_content
        self.output_dir = output_dir
        self.current_class = None
        self.current_class_code = []
        self.global_imports = []

    def visit_Import(self, node: cst.Import):
        # Capture global import statements
        self.global_imports.append(self._extract_code(node))

    def visit_ImportFrom(self, node: cst.ImportFrom):
        # Capture global import statements
        self.global_imports.append(self._extract_code(node))

    def visit_ClassDef(self, node: cst.ClassDef):
        if self.current_class:
            # Write the previous class to a file
            self._write_class_file()

        # Start collecting for the new class
        self.current_class = node.name.value

        # Get the start and end positions of the node
        position = self.get_metadata(PositionProvider, node)
        start = self._calculate_offset(position.start.line, position.start.column)
        end = self._calculate_offset(position.end.line, position.end.column)

        # Extract the source code for the class
        class_code = self.module_content[start:end]
        self.current_class_code = [class_code]

    def leave_Module(self, original_node: cst.Module):
        # Write the last class to a file
        if self.current_class:
            self._write_class_file()

    def _write_class_file(self):
        """
        Write the current class to a file, including a header, ensuring no redundant 'test_' prefix,
        and make the file executable when run directly.
        """
        # Determine the file name by converting the class name to snake_case
        snake_case_name = self._convert_to_snake_case(self.current_class)

        # Avoid redundant 'test_' prefix if it already exists
        if snake_case_name.startswith("test_"):
            filename = f"{snake_case_name}.py"
        else:
            filename = f"test_{snake_case_name}.py"

        filepath = os.path.join(self.output_dir, filename)

        # Generate the header with the current date and year
        current_date = datetime.now().strftime("%B %d, %Y")
        current_year = datetime.now().year
        header = f'''
"""
build123d direct api tests

name: {filename}
by:   Gumyr
date: {current_date}

desc:
    This python module contains tests for the build123d project.

license:

    Copyright {current_year} Gumyr

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
'''
        # Define imports for base class and shared utilities
        base_class_import = "from ..base_test import AlwaysEqual"

        # Add the main block to run tests
        main_block = """
if __name__ == "__main__":
    unittest.main()
"""

        # Write the header, imports, class definition, and main block
        with open(filepath, "w") as f:
            # Combine all parts into the file
            f.write(header + "\n\n")
            f.write("\n".join(self.global_imports) + "\n\n")
            f.write(base_class_import + "\n\n")
            f.write("\n".join(self.current_class_code) + "\n\n")
            f.write(main_block)

        # Prune unused imports and upgrade the code
        self._prune_unused_imports(filepath)

    def _write_class_file(self):
        """
        Write the current class to a file, including a header, ensuring no redundant 'test_' prefix,
        and dynamically inject the AlwaysEqual class if used.
        """
        # Determine the file name by converting the class name to snake_case
        snake_case_name = self._convert_to_snake_case(self.current_class)

        # Avoid redundant 'test_' prefix if it already exists
        if snake_case_name.startswith("test_"):
            filename = f"{snake_case_name}.py"
        else:
            filename = f"test_{snake_case_name}.py"

        filepath = os.path.join(self.output_dir, filename)

        # Check if the current class code references AlwaysEqual
        needs_always_equal = (
            any("AlwaysEqual" in line for line in self.current_class_code)
            and not filename == "test_always_equal.py"
        )

        # Generate the header with the current date and year
        current_date = datetime.now().strftime("%B %d, %Y")
        current_year = datetime.now().year
        header = f'''
"""
build123d imports

name: {filename}
by:   Gumyr
date: {current_date}

desc:
    This python module contains tests for the build123d project.

license:

    Copyright {current_year} Gumyr

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
'''

        # Define the AlwaysEqual class if needed
        always_equal_definition = (
            """
# Always equal to any other object, to test that __eq__ cooperation is working
class AlwaysEqual:
    def __eq__(self, other):
        return True
"""
            if needs_always_equal
            else ""
        )

        # Add the main block to run tests
        main_block = """
if __name__ == "__main__":
    unittest.main()
"""

        # Write the header, AlwaysEqual (if needed), imports, class definition, and main block
        with open(filepath, "w") as f:
            # Combine all parts into the file
            f.write(header + "\n\n")
            f.write(always_equal_definition + "\n\n")
            f.write("\n".join(self.global_imports) + "\n\n")
            f.write("\n".join(self.current_class_code) + "\n\n")
            f.write(main_block)

        # Prune unused imports and upgrade the code
        self._prune_unused_imports(filepath)

    def _convert_to_snake_case(self, name: str) -> str:
        """
        Convert a PascalCase or camelCase name to snake_case.
        """
        import re

        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        return name

    def _extract_code(self, node: cst.CSTNode) -> str:
        """
        Extract the source code of a given node using PositionProvider.
        """
        position = self.get_metadata(PositionProvider, node)
        start = self._calculate_offset(position.start.line, position.start.column)
        end = self._calculate_offset(position.end.line, position.end.column)
        return self.module_content[start:end]

    def _calculate_offset(self, line: int, column: int) -> int:
        """
        Calculate the byte offset in the source content based on line and column numbers.
        """
        lines = self.module_content.splitlines(keepends=True)
        offset = sum(len(lines[i]) for i in range(line - 1)) + column
        return offset

    def _prune_unused_imports(self, filepath):
        """
        Wrapper for remove_unused_imports to clean unused imports in a file and upgrade the code.
        """
        # Initialize the Rope project
        project = Project(self.output_dir)

        # Use the shared function to remove unused imports
        remove_unused_imports(Path(filepath), project)

        # Run pyupgrade on the file to modernize the Python syntax
        print(f"Upgrading Python syntax in {filepath} with pyupgrade...")
        subprocess.run(["pyupgrade", "--py310-plus", str(filepath)])


def remove_unused_imports(file_path: Path, project: Project) -> None:
    """Remove unused imports from a Python file using Rope.

    Args:
        file_path: Path to the Python file to clean imports
        project: Rope project instance to refresh and use for cleaning
    """
    # Get the relative file path from the project root
    relative_path = file_path.relative_to(project.address)

    # Refresh the project to recognize new files
    project.validate()

    # Get the resource (file) to work on
    resource = project.get_resource(str(relative_path))

    # Create import organizer
    import_organizer = ImportOrganizer(project)

    # Get and apply the changes
    changes = import_organizer.organize_imports(resource)
    if changes:
        changes.do()
        print(f"Cleaned imports in {file_path}")
        subprocess.run(["black", str(file_path)])
    else:
        print(f"No unused imports found in {file_path}")


def split_test_file(input_file, output_dir):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Read the input file
    with open(input_file, "r") as f:
        content = f.read()

    # Parse the file and wrap it with metadata
    module = cst.parse_module(content)
    wrapper = MetadataWrapper(module)

    # Process the file
    splitter = TestFileSplitter(module_content=content, output_dir=output_dir)
    wrapper.visit(splitter)


# Define paths
script_dir = Path(__file__).parent
test_direct_api_file = script_dir / ".." / "tests" / "test_direct_api.py"
output_dir = script_dir / ".." / "tests" / "test_direct_api"
test_direct_api_file = test_direct_api_file.resolve()
output_dir = output_dir.resolve()

split_test_file(test_direct_api_file, output_dir)
