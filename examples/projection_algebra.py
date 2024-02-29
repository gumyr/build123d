from build123d import *
from ocp_vscode import show_object

# A sphere used as a projection target
sphere = Sphere(50)

"""Example 1 - Mapping A Face on Sphere"""
projection_direction = Vector(0, 1, 0)

square = Plane.ZX.offset(-80) * Rectangle(20, 20)
square_projected = square.faces()[0].project_to_shape(sphere, projection_direction)
square_solids = Part() + [f.thicken(2) for f in square_projected]
face = square.faces()[0]
projection_beams = loft([face, Pos(0, 160, 0) * face])


"""Example 2 - Flat Projection of Text on Sphere"""
projection_direction = Vector(0, -1, 0)

flat_planar_text = Rot(90, 0, 0) * Text("Flat", font_size=30)
flat_projected_text_faces = Sketch() + [
    f.project_to_shape(sphere, projection_direction)[0]
    for f in flat_planar_text.faces()
]
flat_projection_beams = Part() + [
    extrude(f, dir=projection_direction, amount=80) for f in flat_planar_text.faces()
]


"""Example 3 - Project a text string along a path onto a shape"""
cyl = Plane.YZ * Cylinder(80, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
obj = sphere - Pos(-50, 0, -70) * cyl

arch_path: Edge = obj.edges().sort_by().first

arch_path_start = Vertex(arch_path.position_at(0))
text = Text(
    "'the quick brown fox jumped over the lazy dog'",
    font_size=15,
    align=(Align.MIN, Align.CENTER),
)
projected_text = sphere.project_faces(text.faces(), path=arch_path)

# Example 1
show_object(sphere, name="sphere_solid", options={"alpha": 0.8})
show_object(square, name="square")
show_object(square_solids, name="square_solids")
show_object(
    Compound(projection_beams),
    name="projection_beams",
    options={"alpha": 0.9, "color": (170 / 255, 170 / 255, 255 / 255)},
)

# Example 2
show_object(
    Pos(-100, -100) * sphere,
    name="sphere_solid for text",
    options={"alpha": 0.8},
)
show_object(
    Pos(-100, -100) * flat_projected_text_faces, name="flat_projected_text_faces"
)
show_object(
    Pos(-100, -100) * flat_projection_beams,
    name="flat_projection_beams",
    options={"alpha": 0.95, "color": (170 / 255, 170 / 255, 255 / 255)},
)

# Example 3
show_object(
    sphere.moved(Location((100, 100))),
    name="sphere_solid for text on path",
    options={"alpha": 0.8},
)
show_object(projected_text.moved(Location((100, 100))), name="projected_text on path")
