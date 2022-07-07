"""
OK, fwiw, the reason translate() creates a copy is because the use of copy=True in Shape._apply_transform(): https://github.com/CadQuery/cadquery/blob/c9d3f1e693d8d3b59054c8f10027c46a55342b22/cadquery/occ_impl/shapes.py#L846.  I tried setting it to False and my original example passes.
Thanks.  Playing around a bit more, it seems like translate() makes the underlying TShapes unequal, but Shape.moved() preserves TShape.  This returns true, which could be useful:

x1 = cq.Workplane().box(3,4,5)
x2 = cq.Workplane(x1.findSolid().moved(cq.Location(cq.Vector(1,2,3),cq.Vector(4,5,6),7)))

f1 = x1.faces(">Z").val()
f2 = x2.faces(">Z").val()

f1.wrapped.TShape() == f2.wrapped.TShape()   <=== TRUE

@fpq473 - cadquery newbie
Thanks.  Playing around a bit more, it seems like translate() makes the underlying TShapes unequal, but Shape.moved() preserves TShape.  This returns true, which could be useful: x1 = cq.Workplane().box(3,4,5) x2 = cq.Workplane(x1.findSolid().moved(cq.Location(cq.Vector(1,2,3),cq.Vector(4,5,6),7)))  f1 = x1.faces(">Z").val() f2 = x2.faces(">Z").val()  f1.wrapped.TShape() == f2.wrapped.TShape()   <=== TRUE

"""

from errno import E2BIG
from math import pi, sin, cos, radians, sqrt
from typing import Union, Iterable, Sequence, Callable
import builtins
from enum import Enum, auto
import cadquery as cq
from cadquery.hull import find_hull
from cadquery import (
    Edge,
    Face,
    Wire,
    Vector,
    Shape,
    Location,
    Vertex,
    Compound,
    Solid,
    Plane,
)
from cadquery.occ_impl.shapes import VectorLike, Real
import cq_warehouse.extensions

cq.Wire.makeHelix

z_axis = (Vector(0, 0, 0), Vector(0, 0, 1))

_context_stack = []


def __matmul__custom(e: Union[Edge, Wire], p: float):
    return e.positionAt(p)


def __mod__custom(e: Union[Edge, Wire], p: float):
    return e.tangentAt(p)


Edge.__matmul__ = __matmul__custom
Edge.__mod__ = __mod__custom
Wire.__matmul__ = __matmul__custom
Wire.__mod__ = __mod__custom
line = Edge.makeLine(Vector(0, 0, 0), Vector(10, 0, 0))
# print(f"position of line at 1/2: {line @ 0.5=}")
# print(f"tangent of line at 1/2: {line % 0.5=}")

context_stack = []


def by_x(obj: Shape) -> float:
    return obj.Center().x


def _by_x_shape(self) -> float:
    return self.Center().x


Shape.by_x = _by_x_shape


def by_y(obj: Shape) -> float:
    return obj.Center().y


def _by_y_shape(self) -> float:
    return self.Center().y


Shape.by_y = _by_y_shape


def by_z(obj: Shape) -> float:
    return obj.Center().z


def _by_z_shape(self) -> float:
    return self.Center().z


Shape.by_z = _by_z_shape


def by_length(obj: Union[Edge, Wire]) -> float:
    return obj.Length()


def _by_length_edge_or_wire(self) -> float:
    return self.Length()


Edge.by_length = _by_length_edge_or_wire
Wire.by_length = _by_length_edge_or_wire


def by_radius(obj: Union[Edge, Wire]) -> float:
    return obj.radius()


def _by_radius_edge_or_wire(self) -> float:
    return self.radius()


Edge.by_radius = _by_radius_edge_or_wire
Wire.by_radius = _by_radius_edge_or_wire


def by_area(obj: cq.Shape) -> float:
    return obj.Area()


def _by_area_shape(self) -> float:
    return self.Area()


Shape.by_area = _by_area_shape


class Select(Enum):
    ALL = auto()
    LAST = auto()


class SortBy(Enum):
    NONE = auto()
    X = auto()
    Y = auto()
    Z = auto()
    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()


class Kind(Enum):
    ARC = auto()
    INTERSECTION = auto()
    TANGENT = auto()


class FilterBy(Enum):
    LAST_OPERATION = auto()


class Mode(Enum):
    """Combination Mode"""

    ADDITION = auto()
    SUBTRACTION = auto()
    INTERSECTION = auto()
    CONSTRUCTION = auto()
    PRIVATE = auto()


class Transition(Enum):
    RIGHT = auto()
    ROUND = auto()
    TRANSFORMED = auto()


class Font_Style(Enum):
    """Text Font Styles"""

    REGULAR = auto()
    BOLD = auto()
    ITALIC = auto()


class Halign(Enum):
    """Horizontal Alignment"""

    CENTER = auto()
    LEFT = auto()
    RIGHT = auto()

class Valign(Enum):
    """Vertical Alignment"""

    CENTER = auto()
    TOP = auto()
    BOTTOM = auto()

class Until(Enum):
    NEXT = auto()
    LAST = auto()


class Axis(Enum):
    X = auto()
    Y = auto()
    Z = auto()


class CqObject(Enum):
    EDGE = auto()
    FACE = auto()
    VERTEX = auto()


class BuildAssembly:
    def add(self):
        pass


def _null(self):
    return self


Solid.null = _null
Compound.null = _null


def pts_to_locations(*pts: Union[Vector, Location]) -> list[Location]:
    if pts:
        locations = [
            pt if isinstance(pt, Location) else Location(Vector(pt)) for pt in pts
        ]
    else:
        locations = [Location(Vector())]
    return locations


class EdgeList(list):
    def __init__(self, *edges: Edge):
        self.edges = list(edges)
        super().__init__(edges)

    def sort_edges(self, sort_by: SortBy = SortBy.NONE, reverse: bool = False):

        if sort_by == SortBy.NONE:
            edges = self
        elif sort_by == SortBy.X:
            edges = sorted(
                self,
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            edges = sorted(
                self,
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            edges = sorted(
                self,
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.LENGTH:
            edges = sorted(
                self,
                key=lambda obj: obj.Length(),
                reverse=reverse,
            )
        elif sort_by == SortBy.RADIUS:
            edges = sorted(
                self,
                key=lambda obj: obj.radius(),
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            edges = sorted(
                self,
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")

        return edges


# builtins.list = EdgeList
