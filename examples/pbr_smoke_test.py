"""
Smoke test: bypass pymat entirely, assign threejs_materials.PbrProperties
directly to part.material. If this renders with textures in
ocp_vscode.show(), the ocp_vscode <-> threejs-materials pipeline is
working and our pymat integration is the only thing to fix.

If this ALSO renders white, there's a deeper pipeline problem
independent of our integration.

Run:
    python examples/pbr_smoke_test.py           # headless, prints dict
    python examples/pbr_smoke_test.py --visual  # sends to ocp_vscode
"""

from __future__ import annotations

import sys

from build123d import Box, Cylinder, Part, Pos
from threejs_materials import PbrProperties


def main() -> int:
    body = Box(200, 200, 20)
    hole = Pos(0, 0, 0) * Cylinder(30, 25)
    part = Part() + body - hole

    # Directly assign the rich backend — NO pymat wrapper, NO
    # backfill. This is the path Bernhard's example uses
    # (material-object.py in vscode-ocp-cad-viewer) and the path
    # his adapter handles via `isinstance(node.material, PbrProperties)`.
    wood = PbrProperties.from_gpuopen("Ivory Walnut Solid Wood")
    part.material = wood

    print(f"material type: {type(part.material).__name__}")
    print(f"material name: {wood.name}")
    print(f"texture maps:  {list(wood.maps.to_dict().keys())}")

    if "--visual" in sys.argv:
        from ocp_vscode import StudioEnvironment, StudioTextureMapping, show

        print("\nRendering in ocp_vscode (bypass: direct PbrProperties)...")
        show(
            part,
            studio_environment=StudioEnvironment.PROCEDURAL_STUDIO,
            studio_texture_mapping=StudioTextureMapping.PARAMETRIC,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
