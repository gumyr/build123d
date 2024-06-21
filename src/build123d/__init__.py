"""build123d import definitions"""

from build123d.build_common import *
from build123d.build_enums import *
from build123d.build_line import *
from build123d.build_part import *
from build123d.build_sketch import *
from build123d.exporters import *
from build123d.geometry import *
from build123d.importers import *
from build123d.joints import *
from build123d.mesher import *
from build123d.objects_curve import *
from build123d.objects_part import *
from build123d.objects_sketch import *
from build123d.operations_generic import *
from build123d.operations_part import *
from build123d.operations_sketch import *
from build123d.pack import *
from build123d.topology import *
from build123d.drafting import *
from build123d.persistence import modify_copyreg
from build123d.exporters3d import *

from .version import version as __version__

modify_copyreg()

__all__ = [
    # Length Constants
    "MM",
    "CM",
    "M",
    "IN",
    "FT",
    # Unit Conversions
    "UNITS_PER_METER",
    # Mass Constants
    "G",
    "KG",
    "LB",
    # Enums
    "Align",
    "ApproxOption",
    "AngularDirection",
    "CenterOf",
    "Extrinsic",
    "FontStyle",
    "FrameMethod",
    "GeomType",
    "HeadType",
    "Intrinsic",
    "Keep",
    "Kind",
    "LengthMode",
    "MeshType",
    "Mode",
    "NumberDisplay",
    "PageSize",
    "PositionMode",
    "Select",
    "Side",
    "SortBy",
    "Transition",
    "Unit",
    "Until",
    # Builders,
    "HexLocations",
    "PolarLocations",
    "Locations",
    "GridLocations",
    "BuildLine",
    "BuildPart",
    "BuildSketch",
    # 1D Curve Objects
    "BaseLineObject",
    "Bezier",
    "CenterArc",
    "DoubleTangentArc",
    "EllipticalCenterArc",
    "EllipticalStartArc",
    "FilletPolyline",
    "Helix",
    "IntersectingLine",
    "Line",
    "PolarLine",
    "Polyline",
    "RadiusArc",
    "SagittaArc",
    "Spline",
    "TangentArc",
    "JernArc",
    "ThreePointArc",
    # 2D Sketch Objects
    "ArrowHead",
    "Arrow",
    "BaseSketchObject",
    "Circle",
    "Draft",
    "DimensionLine",
    "Ellipse",
    "ExtensionLine",
    "Polygon",
    "Rectangle",
    "RectangleRounded",
    "RegularPolygon",
    "SlotArc",
    "SlotCenterPoint",
    "SlotCenterToCenter",
    "SlotOverall",
    "Text",
    "TechnicalDrawing",
    "Trapezoid",
    "Triangle",
    # 3D Part Objects
    "BasePartObject",
    "CounterBoreHole",
    "CounterSinkHole",
    "Hole",
    "Box",
    "Cone",
    "Cylinder",
    "Sphere",
    "Torus",
    "Wedge",
    # Direct API Classes
    "BoundBox",
    "Rotation",
    "Rot",
    "Pos",
    "RotationLike",
    "ShapeList",
    "Axis",
    "Color",
    "Curve",
    "Vector",
    "VectorLike",
    "Vertex",
    "Edge",
    "Wire",
    "Face",
    "Matrix",
    "Solid",
    "Shell",
    "Part",
    "Plane",
    "Compound",
    "Location",
    "LocationEncoder",
    "Joint",
    "RigidJoint",
    "RevoluteJoint",
    "Sketch",
    "LinearJoint",
    "CylindricalJoint",
    "BallJoint",
    # Exporter classes
    "Export2D",
    "ExportDXF",
    "ExportSVG",
    "LineType",
    "DotLength",
    "Mesher",
    # Importer functions
    "import_brep",
    "import_step",
    "import_stl",
    "import_svg",
    "import_svg_as_buildline_code",
    # Other functions
    "delta",
    "edges_to_wires",
    "new_edges",
    "pack",
    "polar",
    # Context aware selectors
    "solids",
    "faces",
    "wires",
    "edges",
    "vertices",
    "solid",
    "face",
    "wire",
    "edge",
    "vertex",
    # Operations
    "add",
    "bounding_box",
    "chamfer",
    "extrude",
    "fillet",
    "full_round",
    "loft",
    "make_brake_formed",
    "make_face",
    "make_hull",
    "mirror",
    "offset",
    "project",
    # "project_points",
    "project_workplane",
    "revolve",
    "scale",
    "section",
    "split",
    "sweep",
    "thicken",
    "trace",
    # Topology Exploration
    "topo_explore_connected_edges",
    "topo_explore_common_vertex",
    # 3D Exporters
    "export_step",
    "export_gltf",
    "export_stl",
    "export_brep",
]
