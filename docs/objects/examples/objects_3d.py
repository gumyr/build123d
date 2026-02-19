# [Setup]
from build123d import *

# [Setup]
from docs.tools.svg import write_svg, project_shapes


# [Ex. 1]
with BuildPart() as example_1:
    Box(3, 2, 1)
    # [Ex. 1]
write_svg("box_example", project_shapes(example_1.part))

# [Ex. 2]
with BuildPart() as example_2:
    Cone(2, 1, 2)
    # [Ex. 2]
write_svg("cone_example", project_shapes(example_2.part))

# [Ex. 3]
with BuildPart() as example_3:
    Box(3, 2, 1)
    with Locations(example_3.faces().sort_by(Axis.Z)[-1]):
        CounterBoreHole(0.2, 0.4, 0.5, 0.9)
    # [Ex. 3]
write_svg("counter_bore_hole_example", project_shapes(example_3.part))


# [Ex. 4]
with BuildPart() as example_4:
    Box(3, 2, 1)
    with Locations(example_3.faces().sort_by(Axis.Z)[-1]):
        CounterSinkHole(0.2, 0.4, 0.9)
    # [Ex. 4]
write_svg("counter_sink_hole_example", project_shapes(example_4.part))

# [Ex. 5]
with BuildPart() as example_5:
    Cylinder(1, 2)
    # [Ex. 5]
write_svg("cylinder_example", project_shapes(example_5.part))

# [Ex. 6]
with BuildPart() as example_6:
    Box(3, 2, 1)
    Hole(0.4)
    # [Ex. 6]
write_svg("hole_example", project_shapes(example_6.part))

# [Ex. 7]
with BuildPart() as example_7:
    Sphere(1, 0)
    # [Ex. 7]
write_svg("sphere_example", project_shapes(example_7.part))

# [Ex. 8]
with BuildPart() as example_8:
    Torus(1, 0.2)
    # [Ex. 8]
write_svg("torus_example", project_shapes(example_8.part))

# [Ex. 9]
with BuildPart() as example_9:
    Wedge(1, 1, 1, 0, 0, 0.5, 0.5)
    # [Ex. 9]
write_svg("wedge_example", project_shapes(example_9.part))

# [Ex. 10]
with BuildPart() as example_10:
    Box(30, 20, 20)
    Box(20, 30, 20)
    Box(20, 20, 30)
    with Locations((-10, 0, 0)):
        Box(40, 23, 23)
    ConvexPolyhedron(example_10.vertices())
    # [Ex. 10]
write_svg("convex_polyhedron_example", project_shapes(example_10.part))
