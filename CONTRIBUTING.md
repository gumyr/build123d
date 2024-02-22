When writing code for inclusion in build123d please add docs and
tests, ensure they build and pass, and ensure that `pylint` and `mypy`
are happy with your code.

- Install `pip` following their [documentation](https://pip.pypa.io/en/stable/installation/).
- Install development dependencies: `pip install pylint pytest mypy sphinx black`
- Install docs dependencies: `pip install -r docs/requirements.txt` (might need to comment out the build123d line in that file)
- Install `build123d` in editable mode from current dir:  `pip install -e .`
- Run tests with: `python -m pytest`
- Build docs with: `cd docs && make html`
- Check added files' style with: `pylint <path/to/file.py>` 
- Check added files' type annotations with: `mypy <path/to/file.py>`
- Run black formatter against files' changed: `black --config pyproject.toml <path/to/file.py>` (where the pyproject.toml is from this project's repository)
