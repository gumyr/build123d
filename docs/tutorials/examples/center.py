from build123d import *
from ocp_vscode import *
from tools.svg import write_svg

size = 50
#
# Symbols
#
bbox_symbol = Rectangle(4, 4)
geom_symbol = RegularPolygon(2, 3)
mass_symbol = Circle(2)

#
# 2D Center Options
#
triangle = RegularPolygon(size / 1.866, 3, rotation=90)
layers = {
    "visible": {"shapes": [
        triangle,
        Pos(triangle.center(CenterOf.BOUNDING_BOX)) * bbox_symbol,
        Pos(triangle.center(CenterOf.MASS)) * mass_symbol
        ]},
    "bbox": {"shapes": bounding_box(triangle), "line_type": LineType.DASHED},
}
write_svg("center", layers, margin=5)

#
# 1D Center Options
#
line = TangentArc((0, 0), (size, size), tangent=(1, 0))
layers = {
    "visible": {"shapes": [
        line,
        Pos(line.center(CenterOf.BOUNDING_BOX)) * bbox_symbol,
        Pos(line.center(CenterOf.MASS)) * mass_symbol,
        Pos(line.center(CenterOf.GEOMETRY)) * geom_symbol,
        ]},
    "bbox": {"shapes": Polyline((0, 0), (size, 0), (size, size), (0, size), (0, 0)), "line_type": LineType.DASHED},
}
write_svg("one_d_center", layers, margin=5)
