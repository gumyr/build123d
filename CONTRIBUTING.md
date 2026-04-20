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
- Verify documentation changes by building locally (see more below): `./docs/make html`

## Documentation

To verify documentation changes, build Sphinx docs with:
- Linux/macOS: `./docs/make html`
- Windows: `./docs/make.bat html`

Preview documentation locally by opening `./docs/_build/html/index.html` in a browser.

If necessary, remove locally built documentation with `./docs/make(.bat) clean`.
Clean only built images from destination (rather than entire Sphinx cache) with `py ./docs/build_artifacts.py --clean`

### Adding artifacts (images, exports)

Most documentation images (`png`, `svg`) and exports (`glb`, `stl`) are created during the Sphinx build rather than stored in repository. By default, artifacts are built to `./docs/_build/assets/<section-label>` and referenced in Sphinx `rst` files.

Please respect `.gitignore` and avoid committing build artifacts to the repo except as required.

### Example scripts

All artifacts should be reproducible from an example script. `tcv_screenshots` produces raster images (`png`) and and internal `write_svg` built on `ExportSVG` produces vector images (`svg`).

A basic example script which produces two images:

```py
# ./docs/demo/examples/demo_examples.py

from build123d import *
from tcv_screenshots import save_model
from tools.svg import write_svg, project_shapes

with BuildPart() as part:
    with BuildSketch() as sketch:
        ...

# Save models (any build123d Shape) to tcv_screenshots queue as "demo_part.png"
save_model([part.part], "demo_part")

# Create svg layers "visible" and "hidden" projected to "top" orientation from part.part
layers = project_shapes(part.part, "top", show_hidden=True)
# Add additional layer fo with sketch.sketch, specifying a line_color
layers.update(
    {"sketch": {"shapes": [sketch.sketch], "line_color": (214, 40, 40)}}
    )
# Write layers to "demo_sketch.svg"
write_svg("demo_sketch", layers)
```

`ocp_vscode` or another viewer can be used for inital image development, but to test a script with the build tools with `py .\docs\build_artifacts.py -s ./docs/demo/examples/demo_examples.py` and find output in `./docs/_build/assets/demo_examples`.

### Build from config

`./docs/make html` runs `py .\docs\build_artifacts.py -c asset_conf.json` to build all runtime artifacts. To include artifacts from `demo_examples.py`, add a label group `demo` to `./docs/asset_conf.json` configured for this example:

```json
// ./docs/asset_conf.json

[
    ...
    {
        // destination for group of artifacts
        "label": "demo",
        // sources for example scripts relative to ./docs
        "sources": [
            "demo/examples"
        ],
        // reference resources to copy from sources required to build examples (not used here)
        "resources": [
            "low_poly_benchy.stl"
        ],
        // scripts in sources to build from
        "build": [
            "demo_examples",
            "demo_tutorial"
        ],
        // create square thumbnails from pngs for galleries (not used here)
        "thumbnails": [
            {
                "source": "benchy.png"
            }
            {
                "source": "bicycle_tire_detail.png",
                "label": "bicycle_tire",
            },
        ...
        ]
    },
    ...
]
```

After the first time building `asset_conf.json`, subsequent builds only update label groups with either changes to examples or the group config, however changes to build123d in `./src` do not trigger an change. In this case and others, use `py .\docs\build_artifacts.py -c asset_conf.json -l demo --force` to force an artifact rebuild for a specific label.

### Static artifacts

Some built artifacts must live in the repo such as readme artifacts or very complex objects which are prudent to prebuild as a courtesy to other contributors due to build time.

For example, to update readme images add examples to `readme` in `./docs/static_confg.json` and run `py docs/build_artifacts.py -c static_config.json -l readme -d _static/assets`. Remember to explicitly `git` add and commit new images.

Add assets which cannot be built, such as part drawings, references, or imported geometry, to `./_static/assets/<section-label>`
