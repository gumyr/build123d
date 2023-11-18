"""

name: packed_boxes.py
by:   fischman
date: November 9th 2023

desc: Demo packing a bunch of boxes in 2D.

"""
import functools
import operator
import random
import build123d as bd

random.seed(123456)
test_boxes = [bd.Box(random.randint(1, 20), random.randint(1, 20), random.randint(1, 5))
              for _ in range(50)]
packed = bd.pack(test_boxes, 3)

# Lifted from https://build123d.readthedocs.io/en/latest/import_export.html#d-to-2d-projection
def export_svg(parts, name):
    part = functools.reduce(operator.add, parts, bd.Part())
    view_port_origin=(0, 0, 150)
    visible, hidden = part.project_to_viewport(view_port_origin)
    max_dimension = max(*bd.Compound(children=visible + hidden).bounding_box().size)
    exporter = bd.ExportSVG(scale=100 / max_dimension)
    exporter.add_layer("Visible")
    exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=bd.LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(f"../docs/assets/{name}.svg")

export_svg(test_boxes, "packed_boxes_input")
export_svg(packed, "packed_boxes_output")
