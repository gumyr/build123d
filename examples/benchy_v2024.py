"""
name: "benchy.py"
title: "Low Poly Benchy"
authors: "Gumyr"
license: "http://www.apache.org/licenses/LICENSE-2.0"
created: "2023-07-09"
modified: "2024-01-09"

description: | 
    STL import and edit example.

    The Benchy examples shows hot to import a STL model as a `Solid` object and change it.

    .. note::

        *Attribution:*
        The low-poly-benchy used in this example is by `reddaugherty`, see
        https://www.printables.com/model/151134-low-poly-benchy.


    .. dropdown:: Info

        - uses file `low_poly_benchy.stl`
        - uses `class Mesher`
        - uses `group_by` and `sort_by`
        - uses `make_polygon`
        - uses `split`     

has_builder_mode: true
has_algebra_mode: false
image_files:
    - "example_benchy_01.png"
    - "example_benchy_02.png"
    - "example_benchy_03.png"
"""

# [Imports]
from build123d import *
from ocp_vscode import *

# [Parameters]
# - none

# [Code]
# Import the benchy as a Solid model
importer = Mesher()
benchy_stl = importer.read("low_poly_benchy.stl")[0]

with BuildPart() as benchy:
    add(benchy_stl)

    # Determine the plane that defines the top of the roof
    vertices = benchy.vertices()
    roof_vertices = vertices.filter_by_position(Axis.Z, 38, 42)
    roof_plane_vertices = [
        roof_vertices.group_by(Axis.Y, tol_digits=2)[-1].sort_by(Axis.X)[0],
        roof_vertices.sort_by(Axis.Z)[0],
        roof_vertices.group_by(Axis.Y, tol_digits=2)[0].sort_by(Axis.X)[0],
    ]
    roof_plane = Plane(
        Face(Wire.make_polygon([v.to_tuple() for v in roof_plane_vertices]))
    )
    # Remove the faceted smoke stack
    split(bisect_by=roof_plane, keep=Keep.BOTTOM)

    # Determine the position and size of the smoke stack
    smoke_stack_vertices = vertices.group_by(Axis.Z, tol_digits=0)[-1]
    smoke_stack_center = sum(
        [Vector(v.X, v.Y, v.Z) for v in smoke_stack_vertices], Vector()
    ) * (1 / len(smoke_stack_vertices))
    smoke_stack_radius = max(
        [
            (Vector(*v.to_tuple()) - smoke_stack_center).length
            for v in smoke_stack_vertices
        ]
    )

    # Create the new smoke stack
    with BuildSketch(Plane(smoke_stack_center)):
        Circle(smoke_stack_radius)
        Circle(smoke_stack_radius - 2 * MM, mode=Mode.SUBTRACT)
    extrude(amount=-3 * MM)
    with BuildSketch(Plane(smoke_stack_center)):
        Circle(smoke_stack_radius - 0.5 * MM)
        Circle(smoke_stack_radius - 2 * MM, mode=Mode.SUBTRACT)
    extrude(amount=roof_plane_vertices[1].Z - smoke_stack_center.Z)

show(benchy)
# [End]
