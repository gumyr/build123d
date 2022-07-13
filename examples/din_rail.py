from ..build_part import *
from ..build_sketch import *

# 35x7.5mm DIN Rail Dimensions
overall_width, top_width, height, thickness, fillet = 35, 27, 7.5, 1, 0.8
rail_length = 1000
slot_width, slot_length, slot_pitch = 6.2, 15, 25

with BuildPart(workplane=Plane.named("XZ")) as rail:
    with BuildSketch() as din:
        Rectangle(overall_width, thickness, centered=(True, False))
        Rectangle(top_width, height, centered=(True, False))
        Rectangle(
            top_width - 2 * thickness,
            height - thickness,
            centered=(True, False),
            mode=Mode.SUBTRACTION,
        )
        inside_vertices = (
            din.vertices()
            .filter_by_position(Axis.Y, 0.0, height, inclusive=(False, False))
            .filter_by_position(
                Axis.X,
                -overall_width / 2,
                overall_width / 2,
                inclusive=(False, False),
            )
        )
        FilletSketch(*inside_vertices, radius=fillet)
        outside_vertices = list(
            filter(
                lambda v: (v.Y == 0.0 or v.Y == height)
                and -overall_width / 2 < v.X < overall_width / 2,
                din.vertices(),
            )
        )
        FilletSketch(*outside_vertices, radius=fillet + thickness)
    Extrude(rail_length)
    WorkplanesFromFaces(rail.faces().filter_by_normal(Axis.Z)[-1], replace=True)
    with BuildSketch() as slots:
        RectangularArrayToSketch(0, slot_pitch, 1, rail_length // slot_pitch - 1)
        SlotOverall(slot_length, slot_width, rotation=90)
    slot_holes = Extrude(-height, mode=Mode.SUBTRACTION)

if "show_object" in locals():
    show_object(rail.part, name="rail")
