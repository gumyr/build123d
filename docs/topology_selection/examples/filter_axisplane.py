from build123d import *
from tcv_screenshots import save_model


models = []

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
        models.extend([b, res, axis_rep])

    with Locations((1, 1, 0)):
        b = Box(1, 1, 1)
        f = b.faces()
        res = f.filter_by(plane)
        models.extend([b, res, plane_rep])

    save_model(models, "filter_axisplane")
    models = []

    with Locations((-1, -1, 0)):
        b = Box(1, 1, 1)
        f = b.faces()
        res = f.filter_by(lambda f: abs(f.normal_at().dot(axis.direction)) < 1e-6)
        models.extend([b, res, axis_rep])

    with Locations((1, 1, 0)):
        b = Box(1, 1, 1)
        f = b.faces()
        res = f.filter_by(lambda f: abs(f.normal_at().dot(plane.z_dir)) < 1e-6)
        models.extend([b, res, plane_rep])

    save_model(models, "filter_dot_axisplane")