from build123d import export_gltf

import spitfire_wing_gordon as wing
import heart_token as heart
import tea_cup

export_gltf(
    wing.wing,
    "spitfire_wing.glb",
    binary=True,
    linear_deflection=0.1,
    angular_deflection=1,
)
export_gltf(heart.heart_token.part, "heart_token.glb", binary=True)
export_gltf(
    tea_cup.tea_cup.part,
    "tea_cup.glb",
    binary=True,
    linear_deflection=0.1,
    angular_deflection=1,
)