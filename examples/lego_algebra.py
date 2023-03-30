from build123d import *

pip_count = 6

lego_unit_size = 8
pip_height = 1.8
pip_diameter = 4.8
block_length = lego_unit_size * pip_count
block_width = 16
base_height = 9.6
block_height = base_height + pip_height
support_outer_diameter = 6.5
support_inner_diameter = 4.8
ridge_width = 0.6
ridge_depth = 0.3
wall_thickness = 1.2


# Draw the bottom of the block

# Start with a Rectangle the size of the block
plan = Rectangle(width=block_length, height=block_width)

# Subtract an offset to create the block walls
plan -= offset(
    plan,
    -wall_thickness,
    kind=Kind.INTERSECTION,
)
# Add a grid of lengthwise and widthwise bars
locs = GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2)
plan += locs * Rectangle(width=block_length, height=ridge_width)

locs = GridLocations(lego_unit_size, 0, pip_count, 1)
plan += locs * Rectangle(width=ridge_width, height=block_width)

# Substract a rectangle leaving ribs on the block walls
plan -= Rectangle(
    block_length - 2 * (wall_thickness + ridge_depth),
    block_width - 2 * (wall_thickness + ridge_depth),
)

# Add a row of hollow circles to the center
locs = GridLocations(
    x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
)
ring = Circle(support_outer_diameter / 2) - Circle(support_inner_diameter / 2)
plan += locs * ring

# Extrude this base sketch to the height of the walls
lego = extrude(plan, amount=base_height - wall_thickness)

# Create a box on the top of the walls and the top of the block
lego += Pos(0, 0, lego.vertices().sort_by().last.Z) * Box(
    length=block_length,
    width=block_width,
    height=wall_thickness,
    align=(Align.CENTER, Align.CENTER, Align.MIN),
)

# Create a workplane on the top of the block
plane = Plane(lego.faces().sort_by().last)

# Create a grid of pips

locs = GridLocations(lego_unit_size, lego_unit_size, pip_count, 2)
lego += (
    plane
    * locs
    * Cylinder(
        radius=pip_diameter / 2,
        height=pip_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
)

if "show_object" in locals():
    show_object(lego, name="lego")
