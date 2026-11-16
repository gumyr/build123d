"""
A fast way to make many holes.

name: fast_grid_holes.py
by:   Gumyr
date: May 31, 2025

desc:

    This example demonstrates an efficient approach to creating a large number of holes
    (625 in this case) in a planar part using build123d.

    Instead of modeling and subtracting 3D solids for each hole—which is computationally
    expensive—this method constructs a 2D Face from an outer perimeter wire and a list of
    hole wires. The entire face is then extruded in a single operation to form the final
    3D object. This approach significantly reduces modeling time and complexity.

    The hexagonal hole pattern is generated using HexLocations, and each location is
    populated with a hexagonal wire. These wires are passed directly to the Face constructor
    as holes. On a typical Linux laptop, this script completes in approximately 1.02 seconds,
    compared to substantially longer runtimes for boolean subtraction of individual holes in 3D.

license:

    Copyright 2025 Gumyr

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
import timeit
from build123d import *
from ocp_vscode import show

start_time = timeit.default_timer()

# Calculate the locations of 625 holes
major_r = 10
hole_locs = HexLocations(major_r, 25, 25)

# Create wires for both the perimeter and all the holes
face_perimeter = Rectangle(500, 600).wire()
hex_hole = RegularPolygon(major_r - 1, 6, major_radius=True).wire()
holes = hole_locs * hex_hole

# Create a new Face from the perimeter and hole wires
grid_pattern = Face(face_perimeter, holes)

# Extrude to a 3D part
grid = extrude(grid_pattern, 1)

print(f"Time: {timeit.default_timer() - start_time:0.3f}s")
show(grid)
# [End]
