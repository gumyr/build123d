from tcv_screenshots import save_model

from build123d import *
from ocp_vscode import show_all, show

thickness = 3 * MM
width = 25 * MM
length = 50 * MM
height = 25 * MM
hole_diameter = 5 * MM
bend_radius = 5 * MM
fillet_radius = 2 * MM

with BuildPart() as bracket:
    with BuildSketch() as sketch:
        with BuildLine() as profile:
            FilletPolyline(
                (0, 0), (length / 2, 0), (length / 2, height), radius=bend_radius
            )
            offset(amount=thickness, side=Side.LEFT)
        make_face()
        mirror(about=Plane.YZ)
    extrude(amount=width / 2)
    mirror(about=Plane.XY)
    corners = bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[-1]
    fillet(corners, fillet_radius)
    with Locations(bracket.faces().sort_by(Axis.X)[-1]):
        Hole(hole_diameter / 2)
    with BuildSketch(bracket.faces().sort_by(Axis.Y)[0]):
        SlotOverall(20 * MM, hole_diameter)
    extrude(amount=-thickness, mode=Mode.SUBTRACT)

show_all()

save_model(bracket, "bracket")
save_model(sketch.sketch, "bracket_sketch", {"reset_camera": "top", "axes": True})
size = 2 * bracket.part.bounding_box().size
planexy = Pos(bracket.part.center(CenterOf.BOUNDING_BOX)) * Rectangle(size.X, size.Y)
planexy.color = "#fff8"
planeyz = Plane.YZ.shift_origin(bracket.part.center(CenterOf.BOUNDING_BOX)) * Rectangle(size.Y, size.Z)
planeyz.color = "#fff8"
save_model([bracket, planexy, planeyz], "bracket_with_symmetry")
save_model([bracket, planexy, planeyz], "bracket_with_origin", {"axes": True})
