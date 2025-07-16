"""
refactor topology

name: refactor_topology.py
by:   Gumyr
date: Dec 05, 2024

desc:
    This python script refactors the very large topology.py module into several
    files based on the topological hierarchical order:
    + shape_core.py - base classes Shape, ShapeList
    + utils.py - utility classes & functions
    + zero_d.py - Vertex
    + one_d.py - Mixin1D, Edge, Wire
    + two_d.py - Mixin2D, Face, Shell
    + three_d.py - Mixin3D, Solid
    + composite.py - Compound
    Each of these modules import lower order modules to avoid import loops. They
    also may contain functions used both by end users and higher order modules.

license:

    Copyright 2024 Gumyr

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
import libcst.matchers as m
from typing import List, Set, Dict
from rope.base.project import Project
from rope.refactor.importutils import ImportOrganizer
import subprocess
from datetime import datetime

module_descriptions = {
    "shape_core": """
This module defines the foundational classes and methods for the build123d CAD library, enabling
detailed geometric operations and 3D modeling capabilities. It provides a hierarchy of classes
representing various geometric entities like vertices, edges, wires, faces, shells, solids, and
compounds. These classes are designed to work seamlessly with the OpenCascade Python bindings,
leveraging its robust CAD kernel.

Key Features:
- **Shape Base Class:** Implements core functionalities such as transformations (rotation,
  translation, scaling), geometric queries, and boolean operations (cut, fuse, intersect).
- **Custom Utilities:** Includes helper classes like `ShapeList` for advanced filtering, sorting,
  and grouping of shapes, and `GroupBy` for organizing shapes by specific criteria.
- **Type Safety:** Extensive use of Python typing features ensures clarity and correctness in type
  handling.
- **Advanced Geometry:** Supports operations like finding intersections, computing bounding boxes,
  projecting faces, and generating triangulated meshes.

The module is designed for extensibility, enabling developers to build complex 3D assemblies and
perform detailed CAD operations programmatically while maintaining a clean and structured API.
""",
    "utils": """
This module provides utility functions and helper classes for the build123d CAD library, enabling
advanced geometric operations and facilitating the use of the OpenCascade CAD kernel. It complements
the core library by offering reusable and modular tools for manipulating shapes, performing Boolean
operations, and validating geometry.

Key Features:
- **Geometric Utilities**:
  - `polar`: Converts polar coordinates to Cartesian.
  - `tuplify`: Normalizes inputs into consistent tuples.
  - `find_max_dimension`: Computes the maximum bounding dimension of shapes.

- **Shape Creation**:
  - `_make_loft`: Creates lofted shapes from wires and vertices.
  - `_make_topods_compound_from_shapes`: Constructs compounds from multiple shapes.
  - `_make_topods_face_from_wires`: Generates planar faces with optional holes.

- **Boolean Operations**:
  - `_topods_bool_op`: Generic Boolean operations for TopoDS_Shapes.
  - `new_edges`: Identifies newly created edges from combined shapes.

- **Enhanced Math**:
  - `isclose_b`: Overrides `math.isclose` with a stricter absolute tolerance.

This module is a critical component of build123d, supporting complex CAD workflows and geometric
transformations while maintaining a clean, extensible API.
""",
    "zero_d": """
This module provides the foundational implementation for zero-dimensional geometry in the build123d
CAD system, focusing on the `Vertex` class and its related operations. A `Vertex` represents a
single point in 3D space, serving as the cornerstone for more complex geometric structures such as
edges, wires, and faces. It is directly integrated with the OpenCascade kernel, enabling precise
modeling and manipulation of 3D objects.

Key Features:
- **Vertex Class**:
  - Supports multiple constructors, including Cartesian coordinates, iterable inputs, and
    OpenCascade `TopoDS_Vertex` objects.
  - Offers robust arithmetic operations such as addition and subtraction with other vertices,
    vectors, or tuples.
  - Provides utility methods for transforming vertices, converting to tuples, and iterating over
    coordinate components.

- **Intersection Utilities**:
  - Includes `topo_explore_common_vertex`, a utility to identify shared vertices between edges,
    facilitating advanced topological queries.

- **Integration with Shape Hierarchy**:
  - Extends the `Shape` base class, inheriting essential features such as transformation matrices
    and bounding box computations.

This module plays a critical role in defining precise geometric points and their interactions,
serving as the building block for complex 3D models in the build123d library.
""",
    "one_d": """
This module defines the classes and methods for one-dimensional geometric entities in the build123d
CAD library. It focuses on `Edge` and `Wire`, representing essential topological elements like
curves and connected sequences of curves within a 3D model. These entities are pivotal for
constructing complex shapes, boundaries, and paths in CAD applications.

Key Features:
- **Edge Class**:
  - Represents curves such as lines, arcs, splines, and circles.
  - Supports advanced operations like trimming, offsetting, splitting, and projecting onto shapes.
  - Includes methods for geometric queries like finding tangent angles, normals, and intersection
    points.

- **Wire Class**:
  - Represents a connected sequence of edges forming a continuous path.
  - Supports operations such as closure, projection, and edge manipulation.

- **Mixin1D**:
  - Shared functionality for both `Edge` and `Wire` classes, enabling splitting, extrusion, and
    1D-specific operations.

This module integrates deeply with OpenCascade, leveraging its robust geometric and topological
operations. It provides utility functions to create, manipulate, and query 1D geometric entities,
ensuring precise and efficient workflows in 3D modeling tasks.
""",
    "two_d": """
This module provides classes and methods for two-dimensional geometric entities in the build123d CAD
library, focusing on the `Face` and `Shell` classes. These entities form the building blocks for
creating and manipulating complex 2D surfaces and 3D shells, enabling precise modeling for CAD
applications.

Key Features:
- **Mixin2D**:
  - Adds shared functionality to `Face` and `Shell` classes, such as splitting, extrusion, and
    projection operations.

- **Face Class**:
  - Represents a 3D bounded surface with advanced features like trimming, offsetting, and Boolean
    operations.
  - Provides utilities for creating faces from wires, arrays of points, Bézier surfaces, and ruled
    surfaces.
  - Enables geometry queries like normal vectors, surface centers, and planarity checks.

- **Shell Class**:
  - Represents a collection of connected faces forming a closed surface.
  - Supports operations like lofting and sweeping profiles along paths.

- **Utilities**:
  - Includes methods for sorting wires into buildable faces and creating holes within faces
    efficiently.

The module integrates deeply with OpenCascade to leverage its powerful CAD kernel, offering robust
and extensible tools for surface and shell creation, manipulation, and analysis.
""",
    "three_d": """
This module defines the `Solid` class and associated methods for creating, manipulating, and
querying three-dimensional solid geometries in the build123d CAD system. It provides powerful tools
for constructing complex 3D models, including operations such as extrusion, sweeping, filleting,
chamfering, and Boolean operations. The module integrates with OpenCascade to leverage its robust
geometric kernel for precise 3D modeling.

Key Features:
- **Solid Class**:
  - Represents closed, bounded 3D shapes with methods for volume calculation, bounding box
    computation, and validity checks.
  - Includes constructors for primitive solids (e.g., box, cylinder, cone, torus) and advanced
    operations like lofting, revolving, and sweeping profiles along paths.

- **Mixin3D**:
  - Adds shared methods for operations like filleting, chamfering, splitting, and hollowing solids.
  - Supports advanced workflows such as finding maximum fillet radii and extruding with rotation or
    taper.

- **Boolean Operations**:
  - Provides utilities for union, subtraction, and intersection of solids.

- **Thickening and Offsetting**:
  - Allows transformation of faces or shells into solids through thickening.

This module is essential for generating and manipulating complex 3D geometries in the build123d
library, offering a comprehensive API for CAD modeling.
""",
    "composite": """
This module defines advanced composite geometric entities for the build123d CAD system. It
introduces the `Compound` class as a central concept for managing groups of shapes, alongside
specialized subclasses such as `Curve`, `Sketch`, and `Part` for 1D, 2D, and 3D objects,
respectively. These classes streamline the construction and manipulation of complex geometric
assemblies.

Key Features:
- **Compound Class**:
  - Represents a collection of geometric shapes (e.g., vertices, edges, faces, solids) grouped
    hierarchically.
  - Supports operations like adding, removing, and combining shapes, as well as querying volumes,
    centers, and intersections.
  - Provides utility methods for unwrapping nested compounds and generating 3D text or coordinate
    system triads.

- **Specialized Subclasses**:
  - `Curve`: Handles 1D objects like edges and wires.
  - `Sketch`: Focused on 2D objects, such as faces.
  - `Part`: Manages 3D solids and assemblies.

- **Advanced Features**:
  - Includes Boolean operations, hierarchy traversal, and bounding box-based intersection detection.
  - Supports transformations, child-parent relationships, and dynamic updates.

This module leverages OpenCascade for robust geometric operations while offering a Pythonic
interface for efficient and extensible CAD modeling workflows.
""",
}


def sort_class_methods_by_convention(class_def: cst.ClassDef) -> cst.ClassDef:
    """Sort methods and properties in a class according to Python conventions."""
    methods, properties = extract_methods_and_properties(class_def)
    sorted_body = order_methods_by_convention(methods, properties)

    other_statements = [
        stmt for stmt in class_def.body.body if not isinstance(stmt, cst.FunctionDef)
    ]
    final_body = cst.IndentedBlock(body=other_statements + sorted_body)
    return class_def.with_changes(body=final_body)


def extract_methods_and_properties(
    class_def: cst.ClassDef,
) -> tuple[List[cst.FunctionDef], List[List[cst.FunctionDef]]]:
    """
    Extract methods and properties (with setters grouped together) from a class.

    Returns:
        - methods: Regular methods in the class.
        - properties: List of grouped properties, where each group contains a getter
          and its associated setter, if present.
    """
    methods = []
    properties = {}

    for stmt in class_def.body.body:
        if isinstance(stmt, cst.FunctionDef):
            for decorator in stmt.decorators:
                # Handle @property
                if (
                    isinstance(decorator.decorator, cst.Name)
                    and decorator.decorator.value == "property"
                ):
                    properties[stmt.name.value] = [stmt]  # Initialize with getter
                # Handle @property.setter
                elif (
                    isinstance(decorator.decorator, cst.Attribute)
                    and decorator.decorator.attr.value == "setter"
                ):
                    base_name = decorator.decorator.value.value  # Extract base name
                    if base_name in properties:
                        properties[base_name].append(
                            stmt
                        )  # Add setter to the property group
                    else:
                        # Setter appears before the getter
                        properties[base_name] = [None, stmt]

            # Add non-property methods
            if not any(
                isinstance(decorator.decorator, cst.Name)
                and decorator.decorator.value == "property"
                or isinstance(decorator.decorator, cst.Attribute)
                and decorator.decorator.attr.value == "setter"
                for decorator in stmt.decorators
            ):
                methods.append(stmt)

    # Convert property dictionary into a sorted list of grouped properties
    sorted_properties = [group for _, group in sorted(properties.items())]

    return methods, sorted_properties


def order_methods_by_convention(
    methods: List[cst.FunctionDef], properties: List[List[cst.FunctionDef]]
) -> List[cst.BaseStatement]:
    """
    Order methods and properties in a class by Python's conventional order with section headers.

    Sections:
    - Constructor
    - Properties (grouped by getter and setter)
    - Class Methods
    - Static Methods
    - Public and Private Instance Methods
    """

    def method_key(method: cst.FunctionDef) -> tuple[int, str]:
        name = method.name.value
        decorators = {
            decorator.decorator.value
            for decorator in method.decorators
            if isinstance(decorator.decorator, cst.Name)
        }

        if name == "__init__":
            return (0, name)  # Constructor always comes first
        elif name.startswith("__") and name.endswith("__"):
            return (1, name)  # Dunder methods follow
        elif any(
            decorator == "property" or decorator.endswith(".setter")
            for decorator in decorators
        ):
            return (2, name)  # Properties and setters follow dunder methods
        elif "classmethod" in decorators:
            return (3, name)  # Class methods follow properties
        elif "staticmethod" in decorators:
            return (4, name)  # Static methods follow class methods
        elif not name.startswith("_"):
            return (5, name)  # Public instance methods
        else:
            return (6, name)  # Private methods last

    # Flatten properties into a single sorted list
    flattened_properties = [
        prop for group in properties for prop in group if prop is not None
    ]

    # Separate __init__, class methods, static methods, and instance methods
    init_methods = [m for m in methods if m.name.value == "__init__"]
    class_methods = [
        m
        for m in methods
        if any(decorator.decorator.value == "classmethod" for decorator in m.decorators)
    ]
    static_methods = [
        m
        for m in methods
        if any(
            decorator.decorator.value == "staticmethod" for decorator in m.decorators
        )
    ]
    instance_methods = [
        m
        for m in methods
        if m.name.value != "__init__"
        and not any(
            decorator.decorator.value in {"classmethod", "staticmethod"}
            for decorator in m.decorators
        )
    ]

    # Sort properties and each method group alphabetically
    sorted_properties = sorted(flattened_properties, key=lambda prop: prop.name.value)
    sorted_class_methods = sorted(class_methods, key=lambda m: m.name.value)
    sorted_static_methods = sorted(static_methods, key=lambda m: m.name.value)
    sorted_instance_methods = sorted(instance_methods, key=lambda m: method_key(m))

    # Combine all sections with headers
    ordered_sections: List[cst.BaseStatement] = []

    if init_methods:
        ordered_sections.append(
            cst.SimpleStatementLine([cst.Expr(cst.Comment("# ---- Constructor ----"))])
        )
        ordered_sections.extend(init_methods)

    if sorted_properties:
        ordered_sections.append(
            cst.SimpleStatementLine([cst.Expr(cst.Comment("# ---- Properties ----"))])
        )
        ordered_sections.extend(sorted_properties)

    if sorted_class_methods:
        ordered_sections.append(
            cst.SimpleStatementLine(
                [cst.Expr(cst.Comment("# ---- Class Methods ----"))]
            )
        )
        ordered_sections.extend(sorted_class_methods)

    if sorted_static_methods:
        ordered_sections.append(
            cst.SimpleStatementLine(
                [cst.Expr(cst.Comment("# ---- Static Methods ----"))]
            )
        )
        ordered_sections.extend(sorted_static_methods)

    if sorted_instance_methods:
        ordered_sections.append(
            cst.SimpleStatementLine(
                [cst.Expr(cst.Comment("# ---- Instance Methods ----"))]
            )
        )
        ordered_sections.extend(sorted_instance_methods)

    return ordered_sections


class ImportCollector(cst.CSTVisitor):
    def __init__(self):
        self.imports: Set[str] = set()

    def visit_Import(self, node: cst.Import) -> None:
        for name in node.names:
            # Create a proper statement line
            stmt = cst.SimpleStatementLine([node])
            self.imports.add(cst.Module([stmt]).code)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        # Create a proper statement line
        stmt = cst.SimpleStatementLine([node])
        self.imports.add(cst.Module([stmt]).code)


class ClassExtractor(cst.CSTVisitor):
    def __init__(self, class_names_to_extract: List[str]):
        self.class_names = class_names_to_extract
        self.extracted_classes: Dict[str, cst.ClassDef] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if node.name.value in self.class_names:
            self.extracted_classes[node.name.value] = node


class ClassMethodExtractor(cst.CSTVisitor):
    def __init__(self):
        self.class_methods: Dict[str, List[cst.FunctionDef]] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        class_name = node.name.value
        self.class_methods[class_name] = []

        for statement in node.body.body:
            if isinstance(statement, cst.FunctionDef):
                self.class_methods[class_name].append(statement)

        # Sort methods alphabetically by name
        self.class_methods[class_name].sort(key=lambda method: method.name.value)


class MixinClassExtractor(cst.CSTVisitor):
    def __init__(self):
        self.extracted_classes: Dict[str, cst.ClassDef] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if "Mixin" in node.name.value:
            self.extracted_classes[node.name.value] = node


class StandaloneFunctionAndVariableCollector(cst.CSTVisitor):
    def __init__(self):
        self.functions: List[cst.FunctionDef] = []
        self.current_scope_level = 0  # Track nesting level

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        # Entering a new class scope, increase nesting level
        self.current_scope_level += 1

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        if self.current_scope_level > 0:
            self.current_scope_level -= 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if self.current_scope_level == 0:
            self.functions.append(node)

    def get_sorted_functions(self) -> List[cst.FunctionDef]:
        return sorted(self.functions, key=lambda func: func.name.value)


class GlobalVariableExtractor(cst.CSTVisitor):
    def __init__(self):
        # Store the global variable assignments
        self.global_variables: List[cst.Assign] = []

    def visit_Module(self, node: cst.Module) -> None:
        # Visit all assignments at the module level
        for statement in node.body:
            if isinstance(statement, cst.SimpleStatementLine):
                for assign in statement.body:
                    if isinstance(assign, cst.Assign):
                        self.global_variables.append(assign)


class ClassMethodExtractor(cst.CSTVisitor):
    def __init__(self, methods_to_convert: List[str]):
        self.methods_to_convert = methods_to_convert
        self.extracted_methods: List[cst.FunctionDef] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        # Extract the class name to append it to the function name
        self.current_class_name = node.name.value
        self.generic_visit(node)  # Continue to visit child nodes

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        # Clear the current class name after leaving the class
        self.current_class_name = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        # Check if the function should be converted
        if node.name.value in self.methods_to_convert and self.current_class_name:
            # Rename the method by appending the class name to avoid conflicts
            new_name = f"{node.name.value}_{self.current_class_name.lower()}"
            renamed_node = node.with_changes(name=cst.Name(new_name))
            # Remove `self` from parameters since it's now a standalone function
            if renamed_node.params.params:
                renamed_node = renamed_node.with_changes(
                    params=renamed_node.params.with_changes(
                        params=renamed_node.params.params[1:]
                    )
                )
            self.extracted_methods.append(renamed_node)


def write_topo_class_files(
    source_tree: cst.Module,
    extracted_classes: Dict[str, cst.ClassDef],
    imports: Set[str],
    output_dir: Path,
) -> None:
    """Write files for each group of classes:"""
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sort imports for consistency
    imports_code = "\n".join(imports)

    # Describe where the functions should go
    function_source = {
        "shape_core": [
            "downcast",
            "fix",
            "get_top_level_topods_shapes",
            "_sew_topods_faces",
            "shapetype",
            "topods_dim",
            "_topods_entities",
            "_topods_face_normal_at",
            "apply_ocp_monkey_patches",
            "unwrap_topods_compound",
        ],
        "utils": [
            "delta",
            "_extrude_topods_shape",
            "find_max_dimension",
            "isclose_b",
            "_make_loft",
            "_make_topods_compound_from_shapes",
            "_make_topods_face_from_wires",
            "new_edges",
            "polar",
            "_topods_bool_op",
            "tuplify",
            "unwrapped_shapetype",
        ],
        "zero_d": [
            "topo_explore_common_vertex",
        ],
        "one_d": [
            "edges_to_wires",
            "topo_explore_connected_edges",
        ],
        "two_d": ["sort_wires_by_build_order"],
    }

    # Define class groupings based on layers
    class_groups = {
        "shape_core": [
            "Shape",
            "Comparable",
            "ShapePredicate",
            "GroupBy",
            "ShapeList",
            "Joint",
            "SkipClean",
            "BoundBox",
        ],
        "zero_d": ["Vertex"],
        "one_d": ["Mixin1D", "Edge", "Wire"],
        "two_d": ["Mixin2D", "Face", "Shell"],
        "three_d": ["Mixin3D", "Solid"],
        "composite": ["Compound", "Curve", "Sketch", "Part"],
        "utils": [],
    }

    for group_name, class_names in class_groups.items():

        module_docstring = f"""
build123d topology

name: {group_name}.py
by:   Gumyr
date: {datetime.now().strftime('%B %d, %Y')}

desc:
{module_descriptions[group_name]}
license:

    Copyright {datetime.now().strftime('%Y')} Gumyr

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
        header = [
            cst.SimpleStatementLine(
                [cst.Expr(cst.SimpleString(f'"""{module_docstring}"""'))]
            )
        ]

        if group_name in ["utils", "shape_core"]:
            function_collector = StandaloneFunctionAndVariableCollector()
            source_tree.visit(function_collector)

            variable_collector = GlobalVariableExtractor()
            source_tree.visit(variable_collector)

        group_classes = [
            sort_class_methods_by_convention(extracted_classes[name])
            for name in class_names
            if name in extracted_classes
        ]
        # Add imports for base classes based on layer dependencies
        additional_imports = []
        if group_name != "shape_core":
            additional_imports.append(
                "from .shape_core import Shape, ShapeList, BoundBox, SkipClean, TrimmingTool, Joint"
            )
        if group_name not in ["shape_core", "vertex"]:
            for sub_group_name in function_source.keys():
                additional_imports.append(
                    f"from .{sub_group_name} import "
                    + ",".join(function_source[sub_group_name])
                )
        if group_name not in ["shape_core", "utils", "vertex"]:
            additional_imports.append("from .zero_d import Vertex")
        if group_name in ["two_d"]:
            additional_imports.append("from .one_d import Mixin1D")

        if group_name in ["two_d", "three_d", "composite"]:
            additional_imports.append("from .one_d import Edge, Wire")
        if group_name in ["three_d", "composite"]:
            additional_imports.append("from .one_d import Mixin1D")

            additional_imports.append("from .two_d import Mixin2D, Face, Shell")
        if group_name == "composite":
            additional_imports.append("from .one_d import Mixin1D")
            additional_imports.append("from .three_d import Mixin3D, Solid")

        # Add TYPE_CHECKING imports
        if group_name not in ["composite"]:
            additional_imports.append("if TYPE_CHECKING: # pragma: no cover")
        if group_name in ["shape_core", "utils"]:
            additional_imports.append(
                "    from .zero_d import Vertex # pylint: disable=R0801"
            )
        if group_name in ["shape_core", "utils", "zero_d"]:
            additional_imports.append(
                "    from .one_d import Edge, Wire # pylint: disable=R0801"
            )
        if group_name in ["shape_core", "utils", "one_d"]:
            additional_imports.append(
                "    from .two_d import Face, Shell # pylint: disable=R0801"
            )
        if group_name in ["shape_core", "utils", "one_d", "two_d"]:
            additional_imports.append(
                "    from .three_d import Solid # pylint: disable=R0801"
            )
        if group_name in ["shape_core", "utils", "one_d", "two_d", "three_d"]:
            additional_imports.append(
                "    from .composite import Compound, Curve, Sketch, Part # pylint: disable=R0801"
            )
        # Create class file (e.g., two_d.py)
        class_file = output_dir / f"{group_name}.py"
        all_imports_code = "\n".join([imports_code, *additional_imports])

        # if group_name in ["shape_core", "utils"]:
        if group_name in function_source.keys():
            body = [*cst.parse_module(all_imports_code).body]
            if group_name == "shape_core":
                for var in variable_collector.global_variables:
                    # Check the name of the assigned variable(s)
                    for target in var.targets:
                        if isinstance(target.target, cst.Name):
                            var_name = target.target.value
                            # Check if the variable name is in the exclusion list
                            if var_name not in ["T", "K"]:
                                body.append(var)
                                body.append(cst.EmptyLine(indent=False))

            # Add classes and inject variables after a specific class
            for class_def in group_classes:
                body.append(class_def)

                # Inject variables after the specified class
                if class_def.name.value == "Comparable":
                    body.append(
                        cst.Comment(
                            "# This TypeVar allows IDEs to see the type of objects within the ShapeList"
                        )
                    )
                    body.append(cst.EmptyLine(indent=False))
                    for var in variable_collector.global_variables:
                        # Check the name of the assigned variable(s)
                        for target in var.targets:
                            if isinstance(target.target, cst.Name):
                                var_name = target.target.value
                                # Check if the variable name is in the inclusion list
                                if var_name in ["T", "K"]:
                                    body.append(var)
                                    body.append(cst.EmptyLine(indent=False))

            for func in function_collector.get_sorted_functions():
                if func.name.value in function_source[group_name]:
                    body.append(func)
            class_module = cst.Module(body=body, header=header)
        else:
            class_module = cst.Module(
                body=[*cst.parse_module(all_imports_code).body, *group_classes],
                header=header,
            )
        class_file.write_text(class_module.code)

        print(f"Created {class_file}")

    # Create __init__.py to make it a proper package
    init_file = output_dir / "__init__.py"
    init_content = f'''
"""
build123d.topology package

name: __init__.py
by:   Gumyr
date: {datetime.now().strftime('%B %d, %Y')}

desc: 
    This package contains modules for representing and manipulating 3D geometric shapes,
    including operations on vertices, edges, faces, solids, and composites.
    The package provides foundational classes to work with 3D objects, and methods to
    manipulate and analyze those objects.

license:

    Copyright {datetime.now().strftime('%Y')} Gumyr

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

from .shape_core import (
    Shape,
    Comparable,
    ShapePredicate,
    GroupBy,
    ShapeList,
    Joint,
    SkipClean,
    BoundBox,
    downcast,
    fix,
    unwrap_topods_compound,
)
from .utils import (
    tuplify,
    isclose_b,
    polar,
    delta,
    new_edges,
    find_max_dimension,
)
from .zero_d import Vertex, topo_explore_common_vertex
from .one_d import Edge, Wire, edges_to_wires, topo_explore_connected_edges
from .two_d import Face, Shell, sort_wires_by_build_order
from .three_d import Solid
from .composite import Compound, Curve, Sketch, Part

__all__ = [
    "Shape",
    "Comparable",
    "ShapePredicate",
    "GroupBy",
    "ShapeList",
    "Joint",
    "SkipClean",
    "BoundBox",
    "downcast",
    "fix",
    "unwrap_topods_compound",
    "tuplify",
    "isclose_b",
    "polar",
    "delta",
    "new_edges",
    "find_max_dimension",
    "Vertex",
    "topo_explore_common_vertex",
    "Edge",
    "Wire",
    "edges_to_wires",
    "topo_explore_connected_edges",
    "Face",
    "Shell",
    "sort_wires_by_build_order",
    "Solid",
    "Compound",
    "Curve",
    "Sketch",
    "Part",
]
'''
    init_file.write_text(init_content)
    print(f"Created {init_file}")


def remove_unused_imports(file_path: Path, project: Project) -> None:
    """Remove unused imports from a Python file using rope.

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
        subprocess.run(["black", file_path])

    else:
        print(f"No unused imports found in {file_path}")


class UnionToPipeTransformer(cst.CSTTransformer):
    def leave_Annotation(
        self, original_node: cst.Annotation, updated_node: cst.Annotation
    ) -> cst.Annotation:
        # Check if the annotation is using a Union
        if m.matches(updated_node.annotation, m.Subscript(value=m.Name("Union"))):
            subscript = updated_node.annotation
            if isinstance(subscript, cst.Subscript):
                elements = [elt.slice.value for elt in subscript.slice]
                # Build new binary operator nodes using | for each type in the Union
                new_annotation = elements[0]
                for element in elements[1:]:
                    new_annotation = cst.BinaryOperation(
                        left=new_annotation, operator=cst.BitOr(), right=element
                    )
                return updated_node.with_changes(annotation=new_annotation)
        return updated_node


class OptionalToPipeTransformer(cst.CSTTransformer):
    def leave_Annotation(
        self, original_node: cst.Annotation, updated_node: cst.Annotation
    ) -> cst.Annotation:
        # Match Optional[...] annotations
        if m.matches(updated_node.annotation, m.Subscript(value=m.Name("Optional"))):
            subscript = updated_node.annotation
            if isinstance(subscript, cst.Subscript) and subscript.slice:
                # Extract the inner type of Optional
                inner_type = subscript.slice[0].slice.value
                # Replace Optional[X] with X | None
                new_annotation = cst.BinaryOperation(
                    left=inner_type, operator=cst.BitOr(), right=cst.Name("None")
                )
                return updated_node.with_changes(annotation=new_annotation)
        return updated_node


def main():
    # Define paths
    script_dir = Path(__file__).parent
    topo_file = script_dir / ".." / "src" / "build123d" / "topology_old.py"
    output_dir = script_dir / ".." / "src" / "build123d" / "topology"
    topo_file = topo_file.resolve()
    output_dir = output_dir.resolve()

    # Define classes to extract
    class_names = [
        "BoundBox",
        "Shape",
        "Compound",
        "Solid",
        "Shell",
        "Face",
        "Wire",
        "Edge",
        "Vertex",
        "Curve",
        "Sketch",
        "Part",
        "Mixin1D",
        "Mixin2D",
        "Mixin3D",
        "Comparable",
        "ShapePredicate",
        "SkipClean",
        "ShapeList",
        "GroupBy",
        "Joint",
    ]

    # Parse source file and collect imports
    source_tree = cst.parse_module(topo_file.read_text())
    source_tree = source_tree.visit(UnionToPipeTransformer())
    source_tree = source_tree.visit(OptionalToPipeTransformer())
    # transformed_module = source_tree.visit(UnionToPipeTransformer())
    # print(transformed_module.code)

    collector = ImportCollector()
    source_tree.visit(collector)

    # Extract classes
    extractor = ClassExtractor(class_names)
    source_tree.visit(extractor)

    # Extract mixin classes
    mixin_extractor = MixinClassExtractor()
    source_tree.visit(mixin_extractor)

    # Extract functions
    function_collector = StandaloneFunctionAndVariableCollector()
    source_tree.visit(function_collector)
    # for f in function_collector.functions:
    #     print(f.name.value)

    # Write the class files
    write_topo_class_files(
        source_tree=source_tree,
        extracted_classes=extractor.extracted_classes,
        imports=collector.imports,
        output_dir=output_dir,
    )

    # Create a Rope project instance
    # project = Project(str(script_dir))
    project = Project(str(output_dir))

    # Clean up imports
    for file in output_dir.glob("*.py"):
        if file.name == "__init__.py":
            continue
        remove_unused_imports(file, project)


if __name__ == "__main__":
    main()
