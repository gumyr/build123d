import os
from copy import copy

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))

with BuildPart() as part_context:
    with BuildSketch() as sketch:
        with BuildLine() as line:
            l1 = Line((0, -3), (6, -3))
            l2 = JernArc(l1 @ 1, l1 % 1, radius=3, arc_size=180)
            l3 = PolarLine(l2 @ 1, 6, direction=l2 % 1)
            l4 = Line(l1 @ 0, l3 @ 1)
        make_face()

        with Locations((6, 0, 0)):
            Circle(2, mode=Mode.SUBTRACT)

    extrude(amount=2)

    with BuildSketch(Plane.YZ) as plate_sketch:
        RectangleRounded(16, 6, 1.5, align=(Align.CENTER, Align.MIN))

    plate = extrude(amount=-2)

    with Locations(plate.faces().group_by(Face.area)[-1].sort_by(Axis.X)[-1]):
        with GridLocations(13, 3, 2, 2):
            CounterSinkHole(.5, 1)

    fillet(edges().filter_by(lambda e: e.length == 2).filter_by(Axis.Z), 1)
    bore = faces().filter_by(GeomType.CYLINDER).filter_by(lambda f: f.radius == 2)
    chamfer(bore.edges(), .2)

line = Line((0, -3), (6, -3))
line += JernArc(line @ 1, line % 1, radius=3, arc_size=180)
line += PolarLine(line @ 1, 6, direction=line % 1)

sketch = make_hull(line.edges())
sketch -= Pos(6, 0, 0) * Circle(2)
part = extrude(sketch, amount= 2)
part_before = copy(part)

plate_sketch = Plane.YZ * RectangleRounded(16, 6, 1.5, align=(Align.CENTER, Align.MIN))
plate = extrude(plate_sketch, amount=-2)
plate_face = plate.faces().group_by(Face.area)[-1].sort_by(Axis.X)[-1]
plate -= Plane(plate_face) *  GridLocations(13, 3, 2, 2) * CounterSinkHole(.5, 1, 2)

part += plate
part_before2 = copy(part)

part = fillet(part.edges().filter_by(lambda e: e.length == 2).filter_by(Axis.Z), 1)
bore = part.faces().filter_by(GeomType.CYLINDER).filter_by(lambda f: f.radius == 2)
part = chamfer(bore.edges(), .2)

class Punch(BaseSketchObject):
    def __init__(
        self,
        radius: float,
        size: float,
        blobs: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch() as punch:
            if blobs == 1:
                Circle(size)
            else:
                with PolarLocations(radius, blobs):
                    Circle(size)

            if len(faces()) > 1:
                raise RuntimeError("radius is too large for number and size of blobs")

            add(Face(faces()[0].outer_wire()), mode=Mode.REPLACE)

        super().__init__(obj=punch.sketch, rotation=rotation, mode=mode)

tape = Rectangle(20, 5)
for i, location in enumerate(GridLocations(5, 0, 4, 1)):
    tape -= location * Punch(.8, 1, i + 1)

set_defaults(reset_camera=Camera.RESET)
show(line)
save_screenshot(os.path.join(working_path, "create_1d.png"))

show(sketch, Pos(10, 10) * part_before)
save_screenshot(os.path.join(working_path, "upgrade_2d.png"))

show(plate, Pos(12, 12) * part_before2, Pos(24, 24) * part)
save_screenshot(os.path.join(working_path, "add_part.png"))

show(tape)
save_screenshot(os.path.join(working_path, "extend.png"))