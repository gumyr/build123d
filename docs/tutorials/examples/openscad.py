from build123d import *
from tcv_screenshots import save_model

with BuildPart() as angle_iron:
    with BuildSketch() as profile:
        Rectangle(3 * CM, 4 * MM, align=Align.MIN)
        Rectangle(4 * MM, 3 * CM, align=Align.MIN)
    extrude(amount=10 * CM)
    fillet(angle_iron.edges().filter_by(lambda e: e.is_interior), 5 * MM)

profile = Rectangle(3 * CM, 4 * MM, align=Align.MIN)
profile += Rectangle(4 * MM, 3 * CM, align=Align.MIN)
angle_iron = extrude(profile, 10 * CM)
angle_iron = fillet(angle_iron.edges().filter_by(lambda e: e.is_interior), 5 * MM)

save_model(Plane.XZ * angle_iron, "angle_iron")