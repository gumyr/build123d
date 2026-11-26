"""
Importing and exporting documentation examples

name: import_export.py
by:   Gumyr
date: November 15th 2026

desc:
    Every tested code example of the "Importing and exporting" how-to guide
    lives here, between pairs of ``# [name]`` markers that the page includes
    with ``literalinclude``. The files are written to a scratch directory
    and read back, so that what the page says each format keeps is checked,
    and nothing is left behind.

license:

    Copyright 2026 Gumyr

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

# pylint: disable=redefined-outer-name, wildcard-import, unused-wildcard-import

import os
import tempfile

from build123d import *

home = os.getcwd()
scratch = tempfile.TemporaryDirectory()
os.chdir(scratch.name)

# ---------------------------------------------------------------------------
# the model the examples save: a plate and a knob, labelled and coloured
# ---------------------------------------------------------------------------

# [model]
plate = Box(60, 40, 5) - Cylinder(8, 5)
plate.label = "plate"
plate.color = Color("steelblue")

knob = Pos(0, 0, 7.5) * Cylinder(6, 10)
knob.label = "knob"
knob.color = Color("orange")

panel = Compound(label="panel", children=[plate, knob])
# [model]

# ---------------------------------------------------------------------------
# STEP: exact geometry, with labels, colours and the assembly tree
# ---------------------------------------------------------------------------

# [step]
export_step(panel, "panel.step")

again = import_step("panel.step")
# [step]

assert again.label == "panel"
assert [child.label for child in again.children] == ["plate", "knob"]
assert again.children[0].color == Color("steelblue")
assert again.children[1].color == Color("orange")
assert abs(again.children[0].volume - plate.volume) < 1e-6
# exact geometry: the hole is still a cylinder, not facets
assert GeomType.CYLINDER in {face.geom_type for face in again.faces()}

# [step_units]
export_step(panel, "panel_inches.step", unit=Unit.IN)
# [step_units]

# the same numbers, declared as inches, come back 25.4 times the size in mm
inches = import_step("panel_inches.step")
assert abs(inches.bounding_box().size.X - 60 * 25.4) < 1e-6

# ---------------------------------------------------------------------------
# BREP: exact geometry and nothing else
# ---------------------------------------------------------------------------

# [brep]
export_brep(panel, "panel.brep")

shape = import_brep("panel.brep")
# [brep]

assert len(shape.solids()) == 2 and not shape.label and not shape.children
assert (
    abs(sum(solid.volume for solid in shape.solids()) - plate.volume - knob.volume)
    < 1e-6
)

# ---------------------------------------------------------------------------
# STL: triangles
# ---------------------------------------------------------------------------

# [stl]
export_stl(plate, "plate.stl")
export_stl(plate, "plate_fine.stl", tolerance=1e-4, angular_tolerance=0.02)
# [stl]

assert os.path.getsize("plate_fine.stl") > 2 * os.path.getsize("plate.stl")

# [stl_import]
mesh = import_stl("plate.stl")
# [stl_import]

# one faceted face: no label, no colour, no curved surfaces
assert isinstance(mesh, Face) and not mesh.label and mesh.color is None
assert abs(mesh.area - plate.area) < 0.01 * plate.area
# an STL has no units; they are given when it is read
assert (
    abs(import_stl("plate.stl", model_unit=Unit.IN).bounding_box().size.X - 1524) < 1e-3
)

# ---------------------------------------------------------------------------
# 3MF: meshes, with labels, colours, units and metadata
# ---------------------------------------------------------------------------

# [threemf]
exporter = Mesher()
exporter.add_shape(plate, part_number="plate-0001")
exporter.add_shape(knob)
exporter.add_meta_data(
    name_space="custom",
    name="note",
    value="hello world",
    metadata_type="str",
    must_preserve=False,
)
exporter.write("panel.3mf")
# [threemf]

# [threemf_import]
importer = Mesher()
plate_mesh, knob_mesh = importer.read("panel.3mf")

importer.model_unit  # Unit.MM
importer.mesh_count  # 2
plate_mesh.label, plate_mesh.color  # "plate", steel blue
# [threemf_import]

assert importer.model_unit == Unit.MM and importer.mesh_count == 2
assert (plate_mesh.label, knob_mesh.label) == ("plate", "knob")
assert plate_mesh.color == Color("steelblue")
# a mesh of the plate: close to its volume, not equal to it
assert 0 < abs(plate_mesh.volume - plate.volume) < 0.001 * plate.volume
assert any(item["value"] == "hello world" for item in importer.get_meta_data())

# ---------------------------------------------------------------------------
# 3MF for a printer with more than one filament: an inlay in a second colour
# ---------------------------------------------------------------------------

# [two_colour]
# a tile with a ring and a disc inlaid flush with its top
motif = Circle(9) - Circle(6) + Circle(3)

field = extrude(Rectangle(40, 24) - motif, amount=1)
field.label = "field"
field.color = Color(0x234E70)  # teal

inlay = extrude(motif, amount=1)
inlay.label = "inlay"
inlay.color = Color(0xFAF8BF)  # pale gold

exporter = Mesher()
exporter.add_shape([field, inlay])
exporter.write("tile.3mf")
# [two_colour]

# the two bodies fill the tile between them and share no volume
assert abs(field.volume + inlay.volume - 40 * 24) < 1e-6
assert not (field & inlay)
tile_meshes = Mesher().read("tile.3mf")
assert [mesh.label for mesh in tile_meshes] == ["field", "inlay"]
assert [mesh.color for mesh in tile_meshes] == [Color(0x234E70), Color(0xFAF8BF)]

# ---------------------------------------------------------------------------
# glTF and OBJ: meshes for viewers and renderers
# ---------------------------------------------------------------------------

# [gltf]
export_gltf(panel, "panel.glb", binary=True)
# [gltf]

assert os.path.getsize("panel.glb") > 0

# [obj]
export_obj(plate, "plate.obj", atlas_gutter=0.002)
# [obj]

assert os.path.getsize("plate.obj") > 0

# ---------------------------------------------------------------------------
# a 2D drawing: SVG and DXF
# ---------------------------------------------------------------------------

# [svg]
visible, hidden = panel.drawing_view((100, -80, 60))
max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)

drawing = ExportSVG(scale=100 / max_dimension)
drawing.add_layer("Visible")
drawing.add_layer("Hidden", line_color=0x636363, line_type=LineType.ISO_DOT)
drawing.add_shape(visible, layer="Visible")
drawing.add_shape(hidden, layer="Hidden")
drawing.write("panel.svg")
# [svg]

assert os.path.getsize("panel.svg") > 0

# [dxf]
outline = section(plate, section_by=Plane.XY)  # the plate cut through its middle

drawing = ExportDXF(unit=Unit.MM)
drawing.add_layer("Cut", color="red")
drawing.add_shape(outline, layer="Cut")
drawing.write("plate.dxf")
# [dxf]

assert abs(outline.area - (60 * 40 - Circle(8).area)) < 1e-6

# ---------------------------------------------------------------------------
# bring a drawing in
# ---------------------------------------------------------------------------

# [dxf_import]
edges = import_dxf("plate.dxf")
# [dxf_import]

# the lines and the circle of the outline, as separate edges
assert len(edges) == 5
assert {edge.geom_type for item in edges for edge in item.edges()} == {
    GeomType.LINE,
    GeomType.CIRCLE,
}

# an SVG to read back: the same outline, once as lines and once filled
lines = ExportSVG()
lines.add_shape(outline)
lines.write("plate_lines.svg")
filled = ExportSVG()
filled.add_layer("Filled", fill_color="steelblue", line_color="black")
filled.add_shape(outline, layer="Filled")
filled.write("plate_filled.svg")

# [svg_import]
wires = import_svg("plate_lines.svg")  # outlines come in as wires
faces = import_svg("plate_filled.svg")  # filled shapes come in as faces
# [svg_import]

assert [type(item) for item in wires] == [Wire, Wire]
assert [type(item) for item in faces] == [Face]
# to the precision the SVG was written with
assert abs(faces[0].area - outline.area) < 0.01 and faces[0].color is not None

# [svg_code]
code, builder_name = import_svg_as_buildline_code("plate_lines.svg")
# [svg_code]

assert "with BuildLine() as" in code and "Line(" in code and "RadiusArc(" in code

os.chdir(home)
scratch.cleanup()
