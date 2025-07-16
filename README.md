<p align="center">
    <img alt="build123d logo" src="docs/assets/build123d_logo/logo-banner.svg">
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


Build123d is a python-based, parametric, [boundary representation (BREP)][BREP] modeling framework for 2D and 3D CAD. It's built on the [Open Cascade] geometric kernel and allows for the creation of complex models using a simple and intuitive python syntax. Build123d can be used to create models for 3D printing, CNC machining, laser cutting, and other manufacturing processes.  Models can be exported to a wide variety of popular CAD tools such as [FreeCAD] and SolidWorks.

Build123d could be considered as an evolution of [CadQuery] where the somewhat restrictive Fluent API (method chaining) is replaced with stateful context managers - e.g. `with` blocks - thus enabling the full python toolbox: for loops, references to objects, object sorting and filtering, etc.

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

[BREP]: https://en.wikipedia.org/wiki/Boundary_representation
[CadQuery]: https://cadquery.readthedocs.io/en/latest/index.html
[FreeCAD]: https://www.freecad.org/
[Open Cascade]: https://dev.opencascade.org/
