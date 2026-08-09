import os

from build123d import *
from ocp_vscode import *

working_path = os.path.dirname(os.path.abspath(__file__))
filedir = os.path.join(working_path, "..", "..", "assets", "topology_selection")

axis = Axis.Z
plane = Plane.XY
with BuildPart() as part:
    with BuildSketch(Plane.XY.shift_origin((1, 1))) as plane_rep:
        Rectangle(2, 2)
        with Locations((-.9, -.9)):
            Text("Plane.XY", .2, align=(Align.MIN, Align.MIN), mode=Mode.SUBTRACT)
    plane_rep = plane_rep.sketch
    plane_rep.color = Color(0, .55, .55, .1)

    with Locations((-1, -1, 0)):
        b = Box(1, 1, 1)
        f = b.faces()
        res = f.filter_by(axis)
        axis_rep = [Axis(f.center(), f.normal_at()) for f in res]
        show_object([b, res, axis_rep])

    with Locations((1, 1, 0)):
        b = Box(1, 1, 1)
        f = b.faces()
        res = f.filter_by(plane)
        show_object([b, res, plane_rep])

    save_screenshot(os.path.join(filedir, "filter_axisplane.png"))
    reset_show()

    with Locations((-1, -1, 0)):
        b = Box(1, 1, 1)
        f = b.faces()
        res = f.filter_by(lambda f: abs(f.normal_at().dot(axis.direction)) < 1e-6)
        show_object([b, res, axis_rep])

    with Locations((1, 1, 0)):
        b = Box(1, 1, 1)
        f = b.faces()
        res = f.filter_by(lambda f: abs(f.normal_at().dot(plane.z_dir)) < 1e-6)
        show_object([b, res, plane_rep])

    save_screenshot(os.path.join(filedir, "filter_dot_axisplane.png"))