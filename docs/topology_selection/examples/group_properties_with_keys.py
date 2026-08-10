import os
from copy import copy

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

with BuildPart() as part:
    with BuildSketch(Plane.XZ) as sketch:
        with BuildLine():
            CenterArc((-6, 12), 10, 0, 360)
            Line((-16, 0), (16, 0))
        make_hull()
        Rectangle(50, 5, align=(Align.CENTER, Align.MAX))

    extrude(amount=12)

    Box(38, 6, 22, align=(Align.CENTER, Align.MAX, Align.MIN), mode=Mode.SUBTRACT)

    circle = part.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Y)[0]
    with Locations(Plane(circle.arc_center, z_dir=circle.normal())):
        CounterBoreHole(13 / 2, 16 / 2, 4)

    mirror(about=Plane.XZ)

    before_fillet = copy(part)

    length_groups = part.edges().group_by(Edge.length)
    fillet(length_groups.group(6) + length_groups.group(5), 4)

    after_fillet = copy(part)

    with BuildSketch() as pins:
        with Locations((-21, 0)):
            Circle(3 / 2)
        with Locations((21, 0)):
            SlotCenterToCenter(1, 3)
    extrude(amount=-12, mode=Mode.SUBTRACT)

    with GridLocations(42, 16, 2, 2):
        CounterBoreHole(3.5 / 2, 3.5, 0)

    after_holes = copy(part)

    radius_groups = part.edges().filter_by(GeomType.CIRCLE).group_by(Edge.radius)
    bearing_edges = radius_groups.group(8).group_by(SortBy.DISTANCE)[-1]
    pin_edges = radius_groups.group(1.5).filter_by_position(Axis.Z, -5, -5)
    chamfer([pin_edges, bearing_edges], .5)

location = Location((-20, -20))
items = [before_fillet.part] + length_groups.group(6) + length_groups.group(5)
before = Compound(items).move(location)
show(before, after_fillet.part.move(Location((20, 20))))
save_screenshot(os.path.join(filedir, "group_length_key.png"))

location = Location((-20, -20), (180, 0, 0))
after = Compound([after_holes.part] + pin_edges + bearing_edges).move(location)
show(after, part.part.move(Location((20, 20), (180, 0, 0))))
save_screenshot(os.path.join(filedir, "group_radius_key.png"))