# [Setup]
from build123d import *

# [Setup]


def write_svg(filename: str, view_port_origin=(-100, -50, 30)):
    """Save an image of the BuildPart object as SVG"""
    builder: BuildPart = BuildPart._get_context()

    visible, hidden = builder.part.project_to_viewport(view_port_origin)
    max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
    exporter = ExportSVG(scale=100 / max_dimension)
    exporter.add_layer("Visible")
    exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(f"assets/{filename}.svg")


# [Ex. 1]
with BuildPart() as example_1:
    Box(3, 2, 1)
    # [Ex. 1]
    write_svg("box_example")

# [Ex. 2]
with BuildPart() as example_2:
    Cone(2, 1, 2)
    # [Ex. 2]
    write_svg("cone_example")

# [Ex. 3]
with BuildPart() as example_3:
    Box(3, 2, 1)
    with Locations(example_3.faces().sort_by(Axis.Z)[-1]):
        CounterBoreHole(0.2, 0.4, 0.5, 0.9)
    # [Ex. 3]
    write_svg("counter_bore_hole_example")


# [Ex. 4]
with BuildPart() as example_4:
    Box(3, 2, 1)
    with Locations(example_3.faces().sort_by(Axis.Z)[-1]):
        CounterSinkHole(0.2, 0.4, 0.9)
    # [Ex. 4]
    write_svg("counter_sink_hole_example")

# [Ex. 5]
with BuildPart() as example_5:
    Cylinder(1, 2)
    # [Ex. 5]
    write_svg("cylinder_example")

# [Ex. 6]
with BuildPart() as example_6:
    Box(3, 2, 1)
    Hole(0.4)
    # [Ex. 6]
    write_svg("hole_example")

# [Ex. 7]
with BuildPart() as example_7:
    Sphere(1, 0)
    # [Ex. 7]
    write_svg("sphere_example")

# [Ex. 8]
with BuildPart() as example_8:
    Torus(1, 0.2)
    # [Ex. 8]
    write_svg("torus_example")

# [Ex. 9]
with BuildPart() as example_9:
    Wedge(1, 1, 1, 0, 0, 0.5, 0.5)
    # [Ex. 9]
    write_svg("wedge_example")
