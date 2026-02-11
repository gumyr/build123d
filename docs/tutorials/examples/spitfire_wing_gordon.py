"""
Supermarine Spitfire Wing
"""

# [Code]

from build123d import *
from ocp_vscode import show

wing_span = 36 * FT + 10 * IN
wing_leading = 2.5 * FT
wing_trailing = wing_span / 4 - wing_leading
wing_leading_fraction = wing_leading / (wing_leading + wing_trailing)
wing_tip_section = wing_span / 2 - 1 * IN  # distance from root to last section

# Create leading and trailing edges
leading_edge = EllipticalCenterArc(
    (0, 0), wing_span / 2, wing_leading, start_angle=270, end_angle=360
)
trailing_edge = EllipticalCenterArc(
    (0, 0), wing_span / 2, wing_trailing, start_angle=0, end_angle=90
)

# [AirfoilSizes]
# Calculate the airfoil sizes from the leading/trailing edges
airfoil_sizes = []
for i in [0, 1]:
    tip_axis = Axis(i * (wing_tip_section, 0, 0), (0, 1, 0))
    leading_pnt = leading_edge.intersect(tip_axis)[0]
    trailing_pnt = trailing_edge.intersect(tip_axis)[0]
    airfoil_sizes.append(trailing_pnt.Y - leading_pnt.Y)

# [Airfoils]
# Create the root and tip airfoils - note that they are different NACA profiles
airfoil_root = Plane.YZ * scale(
    Airfoil("2213").translate((-wing_leading_fraction, 0, 0)), airfoil_sizes[0]
)
airfoil_tip = (
    Plane.YZ
    * Pos(Z=wing_tip_section)
    * scale(Airfoil("2205").translate((-wing_leading_fraction, 0, 0)), airfoil_sizes[1])
)

# [Profiles]
# Create the Gordon surface profiles and guides
profiles = airfoil_root.edges() + airfoil_tip.edges()
profiles.append(leading_edge @ 1)  # wing tip
guides = [leading_edge, trailing_edge]
# Create the wing surface as a Gordon Surface
wing_surface = -Face.make_gordon_surface(profiles, guides)
# Create the root of the wing
wing_root = -Face(Wire(wing_surface.edges().filter_by(Edge.is_closed)))

# [Solid]
# Create the wing Solid
wing = Solid(Shell([wing_surface, wing_root]))
wing.color = 0x99A3B9  # Azure Blue

show(wing)
# [End]
# Documentation artifact generation
# wing_control_edges = Curve(
#     [airfoil_root, airfoil_tip, Vertex(leading_edge @ 1), leading_edge, trailing_edge]
# )
# visible, _ = wing_control_edges.project_to_viewport((50 * FT, -50 * FT, 50 * FT))
# max_dimension = max(*Compound(children=visible).bounding_box().size)
# svg = ExportSVG(scale=100 / max_dimension)
# svg.add_shape(visible)
# svg.write("assets/surface_modeling/spitfire_wing_profiles_guides.svg")

# export_gltf(
#     wing,
#     "assets/surface_modeling/spitfire_wing.glb",
#     binary=True,
#     linear_deflection=0.1,
#     angular_deflection=1,
# )
