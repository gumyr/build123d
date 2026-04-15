"""
End-to-end example: build123d + py-materials + ocp_vscode.

Demonstrates the proposed `Shape.material` integration with
`pymat.Material` (from `py-materials`) carrying both physics
properties (density, molar mass, thermal) AND rich PBR rendering
via `threejs-materials`. When `material` is set to a `pymat.Material`
instance, `ocp_vscode` reads it for PBR rendering; the same object
also answers physics queries.

This example is part of the ongoing collaboration tracked in
[MorePET/mat#3](https://github.com/MorePET/mat/issues/3) — see the
issue for the full design discussion.

Requirements:
    pip install build123d[materials,ocp_vscode]

Run (headless):
    python examples/pbr_material_pymat.py

Run (with live render in VS Code's OCP CAD Viewer):
    python examples/pbr_material_pymat.py --visual

The headless mode prints the Three.js `MeshPhysicalMaterial` dict and
physics properties to stdout. The visual mode additionally calls
`ocp_vscode.show()` to render the part in the viewer.
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
    """A simple machined flange — box with a cylindrical hole."""
    body = Box(60, 40, 10)
    hole = Pos(0, 0, 0) * Cylinder(8, 12)
    return Part() + body - hole


def build_material() -> Material:
    """
    Build a stainless steel `pymat.Material` carrying physics values
    AND a rich PBR rendering source.

    When the `[pbr]` extra is installed (via `build123d[materials]`),
    the material downloads a MaterialX "Stainless Steel Brushed"
    texture set from matlib.gpuopen.com on first run and caches it.
    Without the extra, falls back to the lite in-tree PBR dataclass
    (scalar values only, no texture maps).
    """
    base = Material(
        name="Stainless Steel 304",
        density=8.0,
        formula="Fe",
        mechanical={"youngs_modulus": 193, "yield_strength": 170},
        thermal={"melting_point": 1450, "thermal_conductivity": 15.1},
        # Lite PBR — used when rich backend unavailable.
        pbr={
            "base_color": (0.75, 0.75, 0.77, 1.0),
            "metallic": 1.0,
            "roughness": 0.35,
        },
    )
    if RICH_PBR_AVAILABLE:
        # Upgrade to the rich backend for proper MaterialX textures.
        # This is the canonical pattern from ADR-0002 in py-materials:
        # Material carries both physics AND a PbrSource, rendering
        # code calls `to_three_js_material_dict()` and gets the
        # right output regardless of which backend is behind it.
        base.pbr_source = PbrProperties.from_gpuopen("Stainless Steel Brushed")
    return base


def main() -> int:
    part = build_part()
    steel = build_material()

    # The point of the integration: a single assignment lets the
    # part carry both the physics + rendering story.
    part.material = steel

    print("=== Physics properties (via py-materials) ===")
    print(f"  name:         {steel.name}")
    print(f"  density:      {steel.density} g/cm³")
    print(f"  formula:      {steel.formula}")
    print(f"  molar mass:   {steel.molar_mass} g/mol")

    # Computed from build123d geometry + pymat density.
    volume_cm3 = part.volume / 1000  # mm³ → cm³
    mass_g = volume_cm3 * (steel.density or 0.0)
    print(f"  part volume:  {volume_cm3:.2f} cm³")
    print(f"  part mass:    {mass_g:.2f} g")

    print("\n=== PBR rendering (Three.js MeshPhysicalMaterial dict) ===")
    three_js = steel.to_three_js_material_dict()
    print(json.dumps(three_js, indent=2, sort_keys=True))

    print("\n=== Backend summary ===")
    print(f"  rich PBR available:    {RICH_PBR_AVAILABLE}")
    print(f"  rich backend in use:   {steel.pbr_source is not None}")
    print("  (rich backend requires `pip install build123d[materials]`)")

    if "--visual" in sys.argv:
        try:
            from ocp_vscode import show
        except ImportError as e:
            print(
                "\n--visual requires build123d[ocp_vscode]: "
                f"pip install build123d[ocp_vscode,materials]\n({e})"
            )
            return 1
        print("\nRendering in ocp_vscode... "
              "(requires VS Code with OCP CAD Viewer extension)")
        show(part)

    return 0


if __name__ == "__main__":
    sys.exit(main())
