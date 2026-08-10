# [Code]

from build123d import *
from ocp_vscode import show

exchanger_diameter = 10 * CM
exchanger_length = 30 * CM
plate_thickness = 5 * MM
# 149 tubes
tube_diameter = 5 * MM
tube_spacing = 2 * MM
tube_wall_thickness = 0.5 * MM
tube_extension = 3 * MM
bundle_diameter = exchanger_diameter - 2 * tube_diameter
fillet_radius = tube_spacing / 3
assert tube_extension > fillet_radius

# Build the heat exchanger
tube_locations = [
    l
    for l in HexLocations(
        radius=(tube_diameter + tube_spacing) / 2,
        x_count=exchanger_diameter // tube_diameter,
        y_count=exchanger_diameter // tube_diameter,
    )
    if l.position.length < bundle_diameter / 2
]

ring = Circle(tube_diameter / 2) - Circle(tube_diameter / 2 - tube_wall_thickness)
tube_plan = Sketch() + tube_locations * ring

heat_exchanger = extrude(tube_plan, exchanger_length / 2)

plate_plane = Plane(
    origin=(0, 0, exchanger_length / 2 - tube_extension - plate_thickness),
    z_dir=(0, 0, 1),
)
plate = Circle(radius=exchanger_diameter / 2) - tube_locations * Circle(
    radius=tube_diameter / 2 - tube_wall_thickness
)

heat_exchanger += extrude(plate_plane * plate, plate_thickness)
edges = (
    heat_exchanger.edges()
    .filter_by(GeomType.CIRCLE)
    .group_by(SortBy.RADIUS)[1]
    .group_by()[2]
)
half_volume_before_fillet = heat_exchanger.volume
heat_exchanger = fillet(edges, radius=fillet_radius)
half_volume_after_fillet = heat_exchanger.volume
heat_exchanger += mirror(heat_exchanger, Plane.XY)

fillet_volume = 2 * (half_volume_after_fillet - half_volume_before_fillet)
assert abs(fillet_volume - 469.88331045553787) < 1e-3

show(heat_exchanger)
# [End]
