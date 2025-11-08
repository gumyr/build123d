<p align="center">
    <img alt="build123d logo" src="https://github.com/gumyr/build123d/raw/dev/docs/assets/build123d_logo/logo-banner.svg">
</p>

[![Documentation Status](https://readthedocs.org/projects/build123d/badge/?version=latest)](https://build123d.readthedocs.io/en/latest/?badge=latest)
[![tests](https://github.com/gumyr/build123d/actions/workflows/test.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/test.yml)
[![pylint](https://github.com/gumyr/build123d/actions/workflows/lint.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/lint.yml)
[![mypy](https://github.com/gumyr/build123d/actions/workflows/mypy.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/mypy.yml)
[![codecov](https://codecov.io/gh/gumyr/build123d/branch/dev/graph/badge.svg)](https://codecov.io/gh/gumyr/build123d)

![Python Versions](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13-blue)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[![PyPI version](https://img.shields.io/pypi/v/build123d.svg)](https://pypi.org/project/build123d/)
[![Downloads](https://pepy.tech/badge/build123d)](https://pepy.tech/project/build123d)
[![Downloads/month](https://pepy.tech/badge/build123d/month)](https://pepy.tech/project/build123d)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/build123d.svg)](https://pypi.org/project/build123d/)
[![DOI](https://zenodo.org/badge/510925389.svg)](https://doi.org/10.5281/zenodo.14872322)


Build123d is a Python-based, parametric [boundary representation (BREP)][BREP] modeling framework for 2D and 3D CAD. Built on the [Open Cascade] geometric kernel, it provides a clean, fully Pythonic interface for creating precise models suitable for 3D printing, CNC machining, laser cutting, and other manufacturing processes. Models can be exported to popular CAD tools such as [FreeCAD] and SolidWorks.

Designed for modern, maintainable CAD-as-code, build123d combines clear architecture with expressive, algebraic modeling. It offers:
- Minimal or no internal state depending on mode,
- Explicit 1D, 2D, and 3D geometry classes with well-defined operations,
- Extensibility through subclassing and functional composition—no monkey patching,
- Standards-compliant code (PEP 8, mypy, pylint) with rich pylance type hints,
- Deep Python integration—selectors as lists, locations as iterables, and natural conversions (Solid(shell), tuple(Vector)),
- Operator-driven modeling (obj += sub_obj, Plane.XZ * Pos(X=5) * Rectangle(1, 1)) for algebraic, readable, and composable design logic.

The result is a framework that feels native to Python while providing the full power of OpenCascade geometry underneath.

The documentation for **build123d** can be found at [readthedocs](https://build123d.readthedocs.io/en/latest/index.html).

There is a [***Discord***](https://discord.com/invite/Bj9AQPsCfx) server (shared with [CadQuery]) where you can ask for help in the build123d channel.

The recommended method for most users to install **build123d** is:

```
pip install build123d
```

To get the latest non-released version of **build123d** one can install from GitHub using one of the following two commands:

Linux/MacOS:

```
python3 -m pip install git+https://github.com/gumyr/build123d
```

Windows:

```
python -m pip install git+https://github.com/gumyr/build123d
```

If you receive errors about conflicting dependencies, you can retry the installation after having upgraded pip to the latest version with the following command:
```
python3 -m pip install --upgrade pip
```

Development install:

```
git clone https://github.com/gumyr/build123d.git
cd build123d
python3 -m pip install -e .
```

Further installation instructions are available (e.g. Poetry) see the [installation section on readthedocs](https://build123d.readthedocs.io/en/latest/installation.html).

Attribution:

Build123d was originally derived from portions of the [CadQuery] codebase but has since been extensively refactored and restructured into an independent system.

[BREP]: https://en.wikipedia.org/wiki/Boundary_representation
[CadQuery]: https://cadquery.readthedocs.io/en/latest/index.html
[FreeCAD]: https://www.freecad.org/
[Open Cascade]: https://dev.opencascade.org/
