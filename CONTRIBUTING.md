# Contributing

When writing code for inclusion in build123d please add docstrings and
tests, ensure they build and pass, and ensure that `pylint` and `mypy`
are happy with your code.

## Setup

Ensure `pip` is installed and [up-to-date](https://pip.pypa.io/en/stable/installation/#upgrading-pip).
Clone the build123d repo and install in editable mode:

```
git clone https://github.com/gumyr/build123d.git
cd build123d
pip install -e .
```

Install development and docs dependencies:

```
pip install -e ".[development]"
pip install -e ".[docs]"
```

## Before submitting a PR

- Run tests with: `python -m pytest -n auto`
- Check added files' style with: `pylint <path/to/file.py>`
- Check added files' type annotations with: `mypy <path/to/file.py>`
- Run black formatter against files' changed: `black <path/to/file.py>`

To verify documentation changes build docs with:
- Linux/macOS: `./docs/make html`
- Windows: `./docs/make.bat html`
