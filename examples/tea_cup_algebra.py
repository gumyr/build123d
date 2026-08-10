# [Code]

from build123d import *
from ocp_vscode import show

wall_thickness = 3 * MM
fillet_radius = wall_thickness * 0.49

# Create the bowl of the cup as a revolved cross section

# Start & end points with control tangents
s = Spline(
    (30 * MM, 10 * MM),
    (69 * MM, 105 * MM),
    tangents=((1, 0.5), (0.7, 1)),
    tangent_scalars=(1.75, 1),
)
# Lines to finish creating ½ the bowl shape
s += Polyline(s @ 0, s @ 0 + (10 * MM, -10 * MM), (0, 0), (0, (s @ 1).Y), s @ 1)
bowl_section = Plane.XZ * make_face(s)  # Create a filled 2D shape
tea_cup = revolve(bowl_section, axis=Axis.Z)

# Hollow out the bowl with openings on the top and bottom
tea_cup = offset(
    tea_cup, -wall_thickness, openings=tea_cup.faces().filter_by(GeomType.PLANE)
)

# Add a bottom to the bowl
tea_cup += Pos(0, 0, (s @ 0).Y) * Cylinder(radius=(s @ 0).X, height=wall_thickness)

# Smooth out all the edges
tea_cup = fillet(tea_cup.edges(), radius=fillet_radius)

# Determine where the handle contacts the bowl
handle_intersections = [
    tea_cup.find_intersection_points(
        Axis(origin=(0, 0, vertical_offset), direction=(1, 0, 0))
    )[-1][0]
    for vertical_offset in [35 * MM, 80 * MM]
]

# Create a path for handle creation
path_spline = Spline(
    handle_intersections[0] - (wall_thickness / 2, 0, 0),
    handle_intersections[0] + (35 * MM, 0, 30 * MM),
    handle_intersections[0] + (40 * MM, 0, 60 * MM),
    handle_intersections[1] - (wall_thickness / 2, 0, 0),
    tangents=((1, 0, 1.25), (-0.2, 0, -1)),
)

# Align the cross section to the beginning of the path
location = path_spline ^ 0
handle_cross_section = location * RectangleRounded(wall_thickness, 8 * MM, fillet_radius)

# Sweep handle cross section along path
tea_cup += sweep(handle_cross_section, path=path_spline)

# assert abs(tea_cup.part.volume - 130326.77052487945) < 1e-3

show(tea_cup, names=["tea cup"])
# [End]
