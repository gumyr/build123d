# [Code]

from build123d import *
from ocp_vscode import *

# Taper Extrude and Extrude to "next" while creating a Cherry MX key cap
# See: https://www.cherrymx.de/en/dev.html

plan = Rectangle(18 * MM, 18 * MM)
key_cap = extrude(plan, amount=10 * MM, taper=15)

# Create a dished top
key_cap -= Location((0, -3 * MM, 47 * MM), (90, 0, 0)) * Sphere(40 * MM)

# Fillet all the edges except the bottom
key_cap = fillet(
    key_cap.edges().filter_by_position(Axis.Z, 0, 30 * MM, inclusive=(False, True)),
    radius=1 * MM,
)

# Hollow out the key by subtracting a scaled version
key_cap -= scale(key_cap, (0.925, 0.925, 0.85))


# Add supporting ribs while leaving room for switch activation
# First find the size of the internal cavity at 4*MM
key_cap_section = section(key_cap, Plane.XY.offset(4 * MM)).face()
key_cap_internal_size = key_cap_section.inner_wires()[0].bounding_box().size
# Use this size to ensure the ribs fit within the keycap cavity
ribs = Rectangle(key_cap_internal_size.X, 0.5 * MM)
ribs += Rectangle(0.5 * MM, key_cap_internal_size.Y)
ribs += Circle(radius=5.51 * MM / 2)

# Extrude the mount and ribs to the key cap underside
key_cap += extrude(Pos(0, 0, 4 * MM) * ribs, until=Until.NEXT, target=key_cap)

# Add the switch socket
socket = Circle(radius=5.5 * MM / 2)
socket -= Rectangle(4.1 * MM, 1.17 * MM)
socket -= Rectangle(1.17 * MM, 4.1 * MM)
key_cap += extrude(Plane.XY.offset(4 * MM) * socket, amount=-3.5 * MM)

show(key_cap, alphas=[0.3])
# [End]
