"""
The Platonic solids as custom Part objects.

name: platonic_solids.py
by:   Gumyr
date: February 17, 2024

desc:
    This example creates a custom Part object PlatonicSolid.

    Platonic solids are five three-dimensional shapes that are highly symmetrical, 
    known since antiquity and named after the ancient Greek philosopher Plato. 
    These solids are unique because their faces are congruent regular polygons, 
    with the same number of faces meeting at each vertex. The five Platonic solids 
    are the tetrahedron (4 triangular faces), cube (6 square faces), octahedron 
    (8 triangular faces), dodecahedron (12 pentagonal faces), and icosahedron 
    (20 triangular faces). Each solid represents a unique way in which identical 
    polygons can be arranged in three dimensions to form a convex polyhedron, 
    embodying ideals of symmetry and balance.

license:

    Copyright 2024 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

# [Code]
from build123d import *
from math import sqrt
from typing import Union, Literal
from scipy.spatial import ConvexHull

from ocp_vscode import show

PHI = (1 + sqrt(5)) / 2  # The Golden Ratio


class PlatonicSolid(BasePartObject):
    """Part Object: Platonic Solid

    Create one of the five convex Platonic solids.

    Args:
        face_count (Literal[4,6,8,12,20]): number of faces
        diameter (float): double distance to vertices, i.e. maximum size
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        align (Union[None, Align, tuple[Align, Align, Align]], optional): align min, center,
            or max of object. Defaults to None.
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    tetrahedron_vertices = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]

    cube_vertices = [(i, j, k) for i in [-1, 1] for j in [-1, 1] for k in [-1, 1]]

    octahedron_vertices = (
        [(i, 0, 0) for i in [-1, 1]]
        + [(0, i, 0) for i in [-1, 1]]
        + [(0, 0, i) for i in [-1, 1]]
    )

    dodecahedron_vertices = (
        [(i, j, k) for i in [-1, 1] for j in [-1, 1] for k in [-1, 1]]
        + [(0, i / PHI, j * PHI) for i in [-1, 1] for j in [-1, 1]]
        + [(i / PHI, j * PHI, 0) for i in [-1, 1] for j in [-1, 1]]
        + [(i * PHI, 0, j / PHI) for i in [-1, 1] for j in [-1, 1]]
    )

    icosahedron_vertices = (
        [(0, i, j * PHI) for i in [-1, 1] for j in [-1, 1]]
        + [(i, j * PHI, 0) for i in [-1, 1] for j in [-1, 1]]
        + [(i * PHI, 0, j) for i in [-1, 1] for j in [-1, 1]]
    )

    vertices_lookup = {
        4: tetrahedron_vertices,
        6: cube_vertices,
        8: octahedron_vertices,
        12: dodecahedron_vertices,
        20: icosahedron_vertices,
    }
    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        face_count: Literal[4, 6, 8, 12, 20],
        diameter: float = 1.0,
        rotation: RotationLike = (0, 0, 0),
        align: Union[None, Align, tuple[Align, Align, Align]] = None,
        mode: Mode = Mode.ADD,
    ):
        try:
            platonic_vertices = PlatonicSolid.vertices_lookup[face_count]
        except KeyError:
            raise ValueError(
                f"face_count must be one of 4, 6, 8, 12, or 20 not {face_count}"
            )

        # Create a convex hull from the vertices
        hull = ConvexHull(platonic_vertices).simplices.tolist()

        # Create faces from the vertex indices
        platonic_faces = []
        for face_vertex_indices in hull:
            corner_vertices = [platonic_vertices[i] for i in face_vertex_indices]
            platonic_faces.append(Face(Wire.make_polygon(corner_vertices)))

        # Create the solid from the Faces
        platonic_solid = Solid.make_solid(Shell.make_shell(platonic_faces)).clean()

        # By definition, all vertices are the same distance from the origin so
        # scale proportionally to this distance
        platonic_solid = platonic_solid.scale(
            (diameter / 2) / Vector(platonic_solid.vertices()[0]).length
        )

        super().__init__(part=platonic_solid, rotation=rotation, align=align, mode=mode)


solids = [
    Rot(0, 0, 72 * i) * Pos(1, 0, 0) * PlatonicSolid(faces)
    for i, faces in enumerate([4, 6, 8, 12, 20])
]
show(solids)

# [End]
