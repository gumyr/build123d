# [Imports]
from build123d import *
from ocp_vscode import *

# [Parameters]
# - none

# [Code]
# Import the benchy as a Solid model
importer = Mesher()
benchy = importer.read("low_poly_benchy.stl")[0]

# Determine the plane that defines the top of the roof
vertices = benchy.vertices()
roof_vertices = vertices.filter_by_position(Axis.Z, 38, 42)
roof_plane_vertices = [
    roof_vertices.group_by(Axis.Y, tol_digits=2)[-1].sort_by(Axis.X)[0],
    roof_vertices.sort_by(Axis.Z)[0],
    roof_vertices.group_by(Axis.Y, tol_digits=2)[0].sort_by(Axis.X)[0],
]
roof_plane = Plane(Face(Wire.make_polygon([tuple(v) for v in roof_plane_vertices])))

# Determine the position and size of the smoke stack
smoke_stack_vertices = vertices.group_by(Axis.Z, tol_digits=0)[-1]
smoke_stack_center = sum(
    [Vector(v.X, v.Y, v.Z) for v in smoke_stack_vertices], Vector()
) * (1 / len(smoke_stack_vertices))
smoke_stack_radius = max(
    [(Vector(*tuple(v)) - smoke_stack_center).length for v in smoke_stack_vertices]
)

# Remove the faceted smoke stack
benchy = split(benchy, bisect_by=roof_plane, keep=Keep.BOTTOM)

# Create the new smoke stack
stack_plane = Plane(smoke_stack_center)
rim = stack_plane * (Circle(smoke_stack_radius) - Circle(smoke_stack_radius - 2 * MM))
benchy += extrude(rim, amount=-3 * MM)
pipe = stack_plane * (
    Circle(smoke_stack_radius - 0.5 * MM) - Circle(smoke_stack_radius - 2 * MM)
)
benchy += extrude(pipe, amount=roof_plane_vertices[1].Z - smoke_stack_center.Z)

show(benchy)
# [End]
