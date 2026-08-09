<h1 align="center">
    <img alt="build123d logo" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/build123d_logo/logo-banner.svg">
</h1>

[![Documentation Status](https://readthedocs.org/projects/build123d/badge/?version=latest)](https://build123d.readthedocs.io/en/latest/?badge=latest)
[![tests](https://github.com/gumyr/build123d/actions/workflows/test.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/test.yml)
[![pylint](https://github.com/gumyr/build123d/actions/workflows/lint.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/lint.yml)
[![mypy](https://github.com/gumyr/build123d/actions/workflows/mypy.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/mypy.yml)
[![codecov](https://codecov.io/gh/gumyr/build123d/branch/dev/graph/badge.svg)](https://codecov.io/gh/gumyr/build123d)

![Python Versions](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13%20|%203.14-blue)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[![PyPI version](https://img.shields.io/pypi/v/build123d.svg)](https://pypi.org/project/build123d/)
[![Downloads](https://pepy.tech/badge/build123d)](https://pepy.tech/project/build123d)
[![Downloads/month](https://pepy.tech/badge/build123d/month)](https://pepy.tech/project/build123d)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/build123d.svg)](https://pypi.org/project/build123d/)
[![DOI](https://zenodo.org/badge/510925389.svg)](https://zenodo.org/badge/latestdoi/510925389)

[Documentation](https://build123d.readthedocs.io/en/latest/index.html) |
[Cheat Sheet](https://build123d.readthedocs.io/en/latest/cheat_sheet.html) |
[Discord](https://discord.com/invite/Bj9AQPsCfx) |
[Discussions](https://github.com/gumyr/build123d/discussions) |
[Issues](https://github.com/gumyr/build123d/issues ) |
[Contributing](#contributing)

build123d is a Python-based, parametric [boundary representation (BREP)][BREP] modeling framework for 2D and 3D CAD. Built on the [Open Cascade] geometric kernel, it provides a clean, fully Pythonic interface for creating precise models suitable for 3D printing, CNC machining, laser cutting, and other manufacturing processes.

<div align="left">
    <img style="height:200px" alt="bracket" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/examples/toy_truck.png">
    <img style="height:200px" alt="key cap" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/examples/key_cap.png">
    <img style="height:200px" alt="hangar" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/ttt/ttt-23-02-02-sm_hanger_object.png">
</div>

## Features

Designed for modern, maintainable CAD-as-code, build123d combines clear architecture with expressive, algebraic modeling. It offers:
- Minimal or no internal state depending on mode,
- Explicit 1D, 2D, and 3D geometry classes with well-defined operations,
- Extensibility through subclassing and functional composition—no monkey patching,
- Standards-compliant code (PEP 8, mypy, pylint) with rich pylance type hints,
- Deep Python integration—selectors as lists, locations as iterables, and natural conversions (`Solid(shell)`, `tuple(Vector)`),
- Operator-driven modeling (`obj += sub_obj`, `Plane.XZ * Pos(X=5) * Rectangle(1, 1)`) for algebraic, readable, and composable design logic,
- Export formats to popular CAD tools such as [FreeCAD] and SolidWorks.

## Usage

Although wildcard imports are generally bad practice, build123d scripts are usually self contained and importing the large number of objects and methods into the namespace is common:

```py
from build123d import *
```

### Constructing a 1D Shape

Edges, Wires (multiple connected Edges), and Curves (a Compound of Edges and Wires) are the 1D Shapes available in build123d. A single Edge can be created from a Line object with two vector-like positions:

```py
line = Line((0, -3), (6, -3))
```

Additional Edges and Wires may be added to (or subtracted from) the initial line. These objects can reference coordinates along another line through the position (`@`) and tangent (`%`) operators to specify input Vectors:

```py
line += JernArc(line @ 1, line % 1, radius=3, arc_size=180)
line += PolarLine(line @ 1, 6, direction=line % 1)
```

<div align="left">
    <img style="max-height:150px" alt="create 1d" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/readme/create_1d.png">
</div>

### Upgrading to 2D and 3D

Faces, Shells (multiple connected Faces), and Sketches (a Compound of Faces and Shells) are the 2D Shapes available in build123d. The previous line is sufficiently defined to close the Wire and create a Face with `make_hull`:

```py
sketch = make_hull(line.edges())
```

A Circle face is translated with `Pos`, a Location object like `Rot` for transforming Shapes, and subtracted from the sketch. This sketch face is then extruded into a Solid part:

```py
sketch -= Pos(6, 0, 0) * Circle(2)
part = extrude(sketch, amount= 2)
```

<div align="left">
    <img style="max-height:150px" alt="upgrade 2D" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/readme/upgrade_2d.png">
</div>

### Adding to and modifying part

Solids and Parts (a Compound of Solids) are the 1D Shapes available in build123d. A second part can be created from an additional Face. Planes can also be used for positioning and orienting Shape objects. Many objects offer an affordance for alignment relative to the object origin:

```py
plate_sketch = Plane.YZ * RectangleRounded(16, 6, 1.5, align=(Align.CENTER, Align.MIN))
plate = extrude(plate_sketch, amount=-2)
```

Shape topology can be extracted from Shapes with selectors which return ShapeLists. ShapeLists offer methods for sorting, grouping, and filtering Shapes by Shape properties, such as finding a Face by area and selecting position along an Axis and specifying a target with a list slice. A Plane is created from the specified Face to locate an iterable of Locations to place multiple objects on the second part before it is added to the main part:

```py
plate_face = plate.faces().group_by(Face.area)[-1].sort_by(Axis.X)[-1]
plate -= Plane(plate_face) *  GridLocations(13, 3, 2, 2) * CounterSinkHole(.5, 1, 2)

part += plate
```

ShapeList selectors and operators offer powerful methods for specifying Shape features through properties such as length/area/volume, orientation relative to an Axis or Plane, and geometry type:

```py
part = fillet(part.edges().filter_by(lambda e: e.length == 2).filter_by(Axis.Z), 1)
bore = part.faces().filter_by(GeomType.CYLINDER).filter_by(lambda f: f.radius == 2)
part = chamfer(bore.edges(), .2)
```

<div align="left">
    <img style="max-height:150px" alt="modify part" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/readme/add_part.png">
</div>

### Builder Mode

The previous construction is through the **Algebra Mode** interface, which follows a stateless paradigm where each object is explicitly tracked and mutated by algebraic operators.

**Builder Mode** is an alternative build123d interface where state is tracked and structured in a design history-like way where each dimension is distinct. Operations are aware pending faces and edges from Build contexts and location transformations are applied to all child objects in Build and Locations contexts. While each Build context tracks state, operations like `extrude` can still optionally take explicit Shape input instead of implicitly using pending Shapes. Builder mode also introduces the `mode` affordance to objects to specify how new Shapes are combined with the context:

```py
with BuildPart() as part_context:
    with BuildSketch() as sketch:
        with BuildLine() as line:
            l1 = Line((0, -3), (6, -3))
            l2 = JernArc(l1 @ 1, l1 % 1, radius=3, arc_size=180)
            l3 = PolarLine(l2 @ 1, 6, direction=l2 % 1)
            l4 = Line(l1 @ 0, l3 @ 1)
        make_face()

        with Locations((6, 0, 0)):
            Circle(2, mode=Mode.SUBTRACT)

    extrude(amount=2)

    with BuildSketch(Plane.YZ) as plate_sketch:
        RectangleRounded(16, 6, 1.5, align=(Align.CENTER, Align.MIN))

    plate = extrude(amount=-2)

    with Locations(plate.faces().group_by(Face.area)[-1].sort_by(Axis.X)[-1]):
        with GridLocations(13, 3, 2, 2):
            CounterSinkHole(.5, 1)

    fillet(edges().filter_by(lambda e: e.length == 2).filter_by(Axis.Z), 1)
    bore = faces().filter_by(GeomType.CYLINDER).filter_by(lambda f: f.radius == 2)
    chamfer(bore.edges(), .2)
```

### Extending objects

New objects may be created for parametric reusability from base object classes:

```py
class Punch(BaseSketchObject):
    def __init__(
        self,
        radius: float,
        size: float,
        blobs: float,
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch() as punch:
            if blobs == 1:
                Circle(size)
            else:
                with PolarLocations(radius, blobs):
                    Circle(size)

            if len(faces()) > 1:
                raise RuntimeError("radius is too large for number and size of blobs")

            add(Face(faces()[0].outer_wire()), mode=Mode.REPLACE)

        super().__init__(obj=punch.sketch, mode=mode)

tape = Rectangle(20, 5)
for i, location in enumerate(GridLocations(5, 0, 4, 1)):
    tape -= location * Punch(.8, 1, i + 1)
```

<div align="left">
    <img style="max-height:150px" alt="extend" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/readme/extend.png">
</div>

### Data interchange

build123d can import and export a number data formats for interchange with 2D and 3D design tools, 3D printing slicers, and traditional CAM:

```py
svg = import_svg("spade.svg")
step = import_step("nema-17-bracket.step")

export_stl(part, "bracket.stl")
export_step(part_context.part, "bracket.step")
```

### Further reading

More [Examples](https://build123d.readthedocs.io/en/latest/introductory_examples.html) and [Tutorials](https://build123d.readthedocs.io/en/latest/tutorials.html) are found in the documentation.

## Installation

For additional installation options see [Installation](https://build123d.readthedocs.io/en/latest/installation.html)

### Current release

Installing build123d from `pip` is recommended for most users:

```
pip install build123d
```

If you receive errors about conflicting dependencies, retry the installation after upgrading pip to the latest version:

```
pip install --upgrade pip
```

### Pre-release

build123d is under active development and up-to-date features are found in the
development branch:

```
pip install git+https://github.com/gumyr/build123d
```

### Viewers

build123d is best used with a viewer. The most popular viewer is [ocp_vscode](https://github.com/bernhard-42/vscode-ocp-cad-viewer), a Python package with a standalone viewer and VS Code extension. Other [Editors & Viewers](https://build123d.readthedocs.io/en/latest/external.html#external) are found in the documentation.

## Contributing

build123d is a rapidly growing project and we welcome all contributions. Whether you want to share ideas, report bugs, or implement new features, your contribution is welcome! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) file to get started.

## Attribution

build123d is derived from portions of [CadQuery], but is extensively refactored and restructured into an independent framework over [Open Cascade].

## License

This project is licensed under the [Apache License 2.0](LICENSE).

[BREP]: https://en.wikipedia.org/wiki/Boundary_representation
[CadQuery]: https://cadquery.readthedocs.io/en/latest/index.html
[FreeCAD]: https://www.freecad.org/
[Open Cascade]: https://dev.opencascade.org/