<p align="center">
    <img alt="build123d logo" src="docs/assets/build123d_logo/logo-banner.svg">
</p>

[![Documentation Status](https://readthedocs.org/projects/build123d/badge/?version=latest)](https://build123d.readthedocs.io/en/latest/?badge=latest)
[![tests](https://github.com/gumyr/build123d/actions/workflows/test.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/test.yml)
[![pylint](https://github.com/gumyr/build123d/actions/workflows/lint.yml/badge.svg)](https://github.com/gumyr/build123d/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/gumyr/build123d/branch/dev/graph/badge.svg)](https://codecov.io/gh/gumyr/build123d)

Build123d is a python-based, parametric, boundary representation (BREP) modeling framework for 2D and 3D CAD. It's built on the Open Cascade geometric kernel and allows for the creation of complex models using a simple and intuitive python syntax. Build123d can be used to create models for 3D printing, CNC machining, laser cutting, and other manufacturing processes.  Models can be exported to a wide variety of popular CAD tools such as FreeCAD and SolidWorks.

Build123d could be considered as an evolution of [CadQuery](https://cadquery.readthedocs.io/en/latest/index.html) where the somewhat restrictive Fluent API (method chaining) is replaced with stateful context managers - e.g. `with` blocks - thus enabling the full python toolbox: for loops, references to objects, object sorting and filtering, etc.

The documentation for **build123d** can found at [readthedocs](https://build123d.readthedocs.io/en/latest/index.html).

There is a [***Discord***](https://discord.com/invite/Bj9AQPsCfx) server (shared with CadQuery) where you can ask for help in the build123d channel.

The recommended method for most users is to install **build123d** is:
```
pip install build123d
```

To get the latest non-released version of **build123d*** one can install from GitHub using one of the following two commands:

In Linux/MacOS, use the following command:
```
python3 -m pip install git+https://github.com/gumyr/build123d
```
In Windows, use the following command:
```
python -m pip install git+https://github.com/gumyr/build123d
```

If you receive errors about conflicting dependencies, you can retry the installation after having upgraded pip to the latest version with the following command:
```
python3 -m pip install --upgrade pip
```

Development install
```
git clone https://github.com/gumyr/build123d.git
cd build123d
python3 -m pip install -e .
```

Further installation instructions are available (e.g. Poetry, Apple Silicon) see the [installation section on readthedocs](https://build123d.readthedocs.io/en/latest/installation.html).
