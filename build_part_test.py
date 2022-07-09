"""
TODO:
- vertices, edges, faces, solids return subclass with custom sort methods

"""
from build_part import *
from build_sketch import *

# inside_vertices = list(
#     filter(
#         lambda v: 7.5 > v.Y > 0 and -17.5 < v.X < 17.5,
#         din.vertices(),
#     )
# )

# with BuildPart(workplane=Plane.named("XZ")) as rail:
#     with BuildSketch() as din:
#         PushPoints((0, 0.5))
#         Rectangle(35, 1)
#         PushPoints((0, 7.5 / 2))
#         Rectangle(27, 7.5)
#         PushPoints((0, 6.5 / 2))
#         Rectangle(25, 6.5, mode=Mode.SUBTRACTION)
#         inside_vertices = (
#             din.vertices()
#             .filter_by_position(Axis.Y, 0.1, 7.4)
#             .filter_by_position(Axis.X, -17.4, 17.4)
#         )
#         FilletSketch(*inside_vertices, radius=0.8)
#         outside_vertices = list(
#             filter(
#                 lambda v: (v.Y == 0.0 or v.Y == 7.5) and -17.5 < v.X < 17.5,
#                 din.vertices(),
#             )
#         )
#         FilletSketch(*outside_vertices, radius=1.8)
#     Extrude(1000)
#     top = rail.faces().filter_by_normal(Axis.Z).sort_by(SortBy.Z)[-1]
#     rail.faces_to_workplanes(top, replace=True)
#     with BuildSketch() as slots:
#         RectangularArray(0, 25, 1, 39)
#         SlotOverall(15, 6.2, 90)
#     slot_holes = Extrude(-20, mode=Mode.SUBTRACTION)

with BuildPart() as cube:
    PushPointsPart((-5, -5, -5))
    Box(10, 10, 10)
    cube.faces_to_workplanes(*cube.faces(), replace=True)
    with BuildSketch() as pipe:
        Circle(4)
    Extrude(-5, mode=Mode.SUBTRACTION)
    # print(cube.workplane_count)
    with BuildSketch() as pipe:
        Circle(4.5)
        Circle(4, mode=Mode.SUBTRACTION)
    Extrude(10)
    FilletPart(*cube.edges(Select.LAST), radius=0.2)


if "show_object" in locals():
    # show_object(rail.part, name="rail")
    # show_object(slots.sketch, name="slots")
    # show_object(slot_holes, name="slot_holes")
    show_object(cube.part, name="cube")
