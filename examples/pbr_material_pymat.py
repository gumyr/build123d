"""
Hot-wired proof of concept: build123d + py-materials + ocp_vscode.

A single `pymat.Material` instance can be assigned to
`shape.material` and carries BOTH the materials-science story
(density, molar mass, formula, thermal properties) AND a rich
MaterialX-backed PBR rendering source (from `threejs-materials`,
which loads from matlib.gpuopen.com / ambientcg / polyhaven /
physicallybased.info). `ocp_vscode.show()` then renders the part
with full textured PBR while the same object still answers
physics queries.

Tracked in [MorePET/mat#3](https://github.com/MorePET/mat/issues/3).
This example is the exploratory "here's what it could look like"
demo — not yet merged upstream in any of the three repos.

-----------------------------------------------------------------
Three draft PRs make up the integration stack
-----------------------------------------------------------------

- [MorePET/mat#30](https://github.com/MorePET/mat/pull/30) —
  py-materials: `Material.pbr_source` field + `pymat.pbr` Protocol
  + `[pbr]` optional extra + ADR-0002
- [gumyr/build123d#1276](https://github.com/gumyr/build123d/pull/1276) —
  build123d: `Compound.material` / `Solid.material` type widened
  from `str` to `str | pymat.Material | None`
- [bernhard-42/vscode-ocp-cad-viewer#228](https://github.com/bernhard-42/vscode-ocp-cad-viewer/pull/228) —
  ocp_vscode: `_extract_materials_from_node` prefers the rich
  `pbr_source` instead of the lossy field-by-field copy

This example runs against all three PRs at once via exact-SHA git
pins in `pyproject.toml`'s `[materials]` extra and
`[tool.uv.sources]` override.

-----------------------------------------------------------------
Try it yourself
-----------------------------------------------------------------

Requires **`uv`** (the `[tool.uv.sources]` override is
uv-specific; `pip` / `poetry` users need to install the
`ocp_vscode` fork manually — see the note in `pyproject.toml`).

```bash
git clone -b feature/pymat-material-integration \\
    https://github.com/gerchowl/build123d.git
cd build123d
uv sync --extra materials --extra ocp_vscode
uv run python examples/pbr_material_pymat.py --material wood --visual
```

That single `uv sync` resolves the whole dependency chain:

```
gerchowl/build123d @ feature/pymat-material-integration    (local clone)
  ↓ [materials] extra
MorePET/mat          @ 8c7729c (feature/3-pbr-protocol-integration)
  ↓ [pbr] sub-extra
threejs-materials[materialx] 1.0.4                         (PyPI)
  ↓ via tool.uv.sources override
gerchowl/vscode-ocp-cad-viewer @ 94cecc7 (fix/pymat-pbr-source-bypass)
```

-----------------------------------------------------------------
Running the example
-----------------------------------------------------------------

```bash
# headless — prints physics + Three.js dict
uv run python examples/pbr_material_pymat.py

# pick a MaterialX preset (wood, steel, bricks, tiles, gold, bronze)
uv run python examples/pbr_material_pymat.py --material wood

# open VS Code with the OCP CAD Viewer extension, then:
uv run python examples/pbr_material_pymat.py --material wood --visual
```

Before hitting `--visual`, make sure you have the **OCP CAD Viewer**
extension installed in VS Code (`Cmd+Shift+P` → "Extensions: Install
Extensions" → "OCP CAD Viewer"). When the viewer panel opens,
click the **Material** tab in its toolbar and ensure **Studio**
mode is selected (the `--visual` mode passes the right studio kwargs
to `show()`, but the viewer's panel can override them).

Each preset downloads its MaterialX set from matlib.gpuopen.com on
first run (cached under `~/.cache/threejs-materials/` afterwards).
Wood grain is the most unambiguous "is this working?" signal —
if you see wood grain on a 200×200 mm plate, every layer of the
three-repo integration is working end-to-end.
"""

from __future__ import annotations

import json
import sys

from build123d import Box, Cylinder, Part, Pos

try:
    from pymat import Material
except ImportError as e:
    sys.stderr.write(
        "This example requires py-materials with the [pbr] extra.\n"
        "Install via:\n"
        "    pip install build123d[materials]\n"
        f"\n(underlying error: {e})\n"
    )
    sys.exit(2)

try:
    from pymat.pbr import PbrProperties  # noqa: F401  # re-exported when [pbr]
    RICH_PBR_AVAILABLE = True
except ImportError:
    RICH_PBR_AVAILABLE = False


def build_part() -> Part:
    """A 200 mm square plate with a central hole.

    Sized deliberately large (200 × 200 × 20 mm) so PBR textures
    are visible at a reasonable tile rate. Brushed/grained textures
    can look washed out on small faces if the UV scale doesn't match
    the geometry — a bigger plate gives the texture room to breathe.
    """
    body = Box(200, 200, 20)
    hole = Pos(0, 0, 0) * Cylinder(30, 25)
    return Part() + body - hole


# Preset materials from matlib.gpuopen.com. Each is visually
# distinctive so it's obvious when the PBR pipeline is working.
# These are lifted from Bernhard's own `material-object.py` demo in
# `bernhard-42/vscode-ocp-cad-viewer`, which confirms they render
# correctly in ocp_vscode's studio mode.
PRESETS = {
    "wood": {
        "name": "Ivory Walnut Solid Wood",
        "density": 0.65,  # g/cm³, typical for walnut
        "formula": None,
        "gpuopen_name": "Ivory Walnut Solid Wood",
    },
    "steel": {
        "name": "Stainless Steel Brushed",
        "density": 8.0,
        "formula": "Fe",
        "gpuopen_name": "Stainless Steel Brushed",
    },
    "bricks": {
        "name": "TH Large Red Bricks",
        "density": 1.92,  # g/cm³, typical clay brick
        "formula": None,
        "gpuopen_name": "TH Large Red Bricks",
    },
    "tiles": {
        "name": "Iberian Blue Ceramic Tiles",
        "density": 2.4,  # g/cm³, typical ceramic
        "formula": None,
        "gpuopen_name": "Iberian Blue Ceramic Tiles",
    },
    "gold": {
        "name": "Gold",
        "density": 19.3,
        "formula": "Au",
        "gpuopen_name": "Gold",
    },
    "bronze": {
        "name": "Bronze Oxydized",
        "density": 8.8,
        "formula": None,
        "gpuopen_name": "Bronze Oxydized",
    },
}


def build_material(preset: str = "wood") -> Material:
    """
    Build a `pymat.Material` carrying physics values AND a rich PBR
    source, from one of the visually distinctive presets defined in
    `PRESETS`. Default is ``wood`` — its grain pattern is the most
    unambiguous texture to spot, which makes it the best "is the PBR
    pipeline working?" test case.

    When the `[pbr]` extra is installed (via `build123d[materials]`),
    the material downloads the requested MaterialX texture set from
    matlib.gpuopen.com on first run and caches it under the user's
    threejs-materials cache directory for reuse.
    """
    if preset not in PRESETS:
        raise ValueError(
            f"Unknown preset {preset!r}. Available: {sorted(PRESETS)}"
        )
    spec = PRESETS[preset]
    base = Material(
        name=spec["name"],
        density=spec["density"],
        formula=spec["formula"],
        # Lite PBR fallback (used when rich backend unavailable —
        # intentionally neutral so the fallback is obviously worse
        # than the rich path).
        pbr={
            "base_color": (0.7, 0.7, 0.7, 1.0),
            "metallic": 0.0,
            "roughness": 0.5,
        },
    )
    if RICH_PBR_AVAILABLE:
        base.pbr_source = PbrProperties.from_gpuopen(spec["gpuopen_name"])
    return base


def _parse_material_arg() -> str:
    """Parse `--material NAME` from argv, default to `wood`."""
    if "--material" in sys.argv:
        i = sys.argv.index("--material")
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return "wood"


def main() -> int:
    preset = _parse_material_arg()
    part = build_part()
    mat = build_material(preset)

    # The point of the integration: a single assignment lets the
    # part carry both the physics + rendering story.
    part.material = mat

    print(f"=== Physics properties (via py-materials, preset={preset!r}) ===")
    print(f"  name:         {mat.name}")
    print(f"  density:      {mat.density} g/cm³")
    print(f"  formula:      {mat.formula}")
    print(f"  molar mass:   {mat.molar_mass} g/mol")

    # Computed from build123d geometry + pymat density.
    volume_cm3 = part.volume / 1000  # mm³ → cm³
    mass_g = volume_cm3 * (mat.density or 0.0)
    print(f"  part volume:  {volume_cm3:.2f} cm³")
    print(f"  part mass:    {mass_g:.2f} g")

    print("\n=== PBR rendering (Three.js MeshPhysicalMaterial dict) ===")
    three_js = mat.to_three_js_material_dict()
    # Abbreviate data URIs so the dump is readable.
    def _abbrev(obj):
        if isinstance(obj, str) and obj.startswith("data:"):
            return f"data:...;base64,...({len(obj)} chars)"
        if isinstance(obj, dict):
            return {k: _abbrev(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_abbrev(v) for v in obj]
        return obj
    print(json.dumps(_abbrev(three_js), indent=2, sort_keys=True))

    print("\n=== Backend summary ===")
    print(f"  rich PBR available:    {RICH_PBR_AVAILABLE}")
    print(f"  rich backend in use:   {mat.pbr_source is not None}")
    print(f"  available presets:     {sorted(PRESETS.keys())}")
    print(f"  current preset:        {preset!r}  (change via `--material NAME`)")

    if "--visual" in sys.argv:
        try:
            from ocp_vscode import show, StudioEnvironment, StudioTextureMapping
        except ImportError as e:
            print(
                "\n--visual requires build123d[ocp_vscode]: "
                f"pip install build123d[ocp_vscode,materials]\n({e})"
            )
            return 1
        print("\nRendering in ocp_vscode... "
              "(requires VS Code with OCP CAD Viewer extension)")
        # Studio mode + an HDR environment map activate PBR texture
        # sampling in three-cad-viewer. Without these, the viewer
        # falls back to CAD mode (flat interpolated color — renders
        # yellow/mustard as the ocp_vscode default). PROCEDURAL_STUDIO
        # is the default procedural env map (no HDR download needed);
        # PARAMETRIC mapping uses the UVs baked into threejs-materials'
        # texture output.
        show(
            part,
            studio_environment=StudioEnvironment.PROCEDURAL_STUDIO,
            studio_texture_mapping=StudioTextureMapping.PARAMETRIC,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
