from build123d import *

powerup = Spline(
    (0, 0, 0),
    (50, 0, 50),
    (100, 0, 0),
    tangents=((1, 0, 0), (1, 0, 0)),
    tangent_scalars=(0.5, 2),
)
corner = RadiusArc(powerup @ 1, (100, 60, 0), -30)
screw = Helix(75, 150, 15, center=(75, 40, 15), direction=(-1, 0, 0))

roller_coaster = powerup + corner + screw
roller_coaster += Spline(corner @ 1, screw @ 0, tangents=(corner % 1, screw % 0))
roller_coaster += Spline(
    screw @ 1, (-100, 30, 10), powerup @ 0, tangents=(screw % 1, powerup % 0)
)

if "show_object" in locals():
    show_object(roller_coaster)
