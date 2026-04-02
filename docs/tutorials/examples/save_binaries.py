from build123d import export_gltf

import spitfire_wing_gordon as wing
import heart_token as heart

export_gltf(
    wing.wing,
    "spitfire_wing.glb",
    binary=True,
    linear_deflection=0.1,
    angular_deflection=1,
)
export_gltf(heart.heart_token.part, "heart_token.glb", binary=True)