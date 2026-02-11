from build123d import *
from ocp_vscode import *

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
svg = ExportSVG(margin=5)
svg.add_layer("bbox", line_type=LineType.DASHED)
svg.add_shape(bounding_box(triangle), "bbox")
svg.add_shape(triangle)
svg.add_shape(bbox_symbol.located(Location(triangle.center(CenterOf.BOUNDING_BOX))))
svg.add_shape(mass_symbol.located(Location(triangle.center(CenterOf.MASS))))
svg.write("assets/center.svg")

#
# 1D Center Options
#
line = TangentArc((0, 0), (size, size), tangent=(1, 0))
svg = ExportSVG(margin=5)
svg.add_layer("bbox", line_type=LineType.DASHED)
svg.add_shape(line)
svg.add_shape(Polyline((0, 0), (size, 0), (size, size), (0, size), (0, 0)), "bbox")
svg.add_shape(bbox_symbol.located(Location(line.center(CenterOf.BOUNDING_BOX))))
svg.add_shape(mass_symbol.located(Location(line.center(CenterOf.MASS))))
svg.add_shape(geom_symbol.located(Location(line.center(CenterOf.GEOMETRY))))
svg.write("assets/one_d_center.svg")
