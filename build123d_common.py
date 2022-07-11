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
import logging
from functools import partial
from math import pi, sin, cos, radians, sqrt
from pstats import SortKey
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
from OCP.gp import gp_Vec, gp_Pnt, gp_Ax1, gp_Dir, gp_Trsf
import cq_warehouse.extensions


class Rotation(Location):
    def __init__(self, about_x: float = 0, about_y: float = 0, about_z: float = 0):
        self.about_x = about_x
        self.about_y = about_y
        self.about_z = about_z

        # Compute rotation matrix.
        rx = gp_Trsf()
        rx.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), radians(about_x))
        ry = gp_Trsf()
        ry.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), radians(about_y))
        rz = gp_Trsf()
        rz.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), radians(about_z))
        super().__init__(Location(rx * ry * rz).wrapped)


RotationLike = Union[tuple[float, float, float], Rotation]

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


class Kind(Enum):
    ARC = auto()
    INTERSECTION = auto()
    TANGENT = auto()

class Keep(Enum):
    TOP = auto()
    BOTTOM = auto()

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


class SortBy(Enum):
    X = auto()
    Y = auto()
    Z = auto()
    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()


class ShapeList(list):
    axis_map = {
        Axis.X: ((1, 0, 0), (-1, 0, 0)),
        Axis.Y: ((0, 1, 0), (0, -1, 0)),
        Axis.Z: ((0, 0, 1), (0, 0, -1)),
    }

    def __init_subclass__(cls) -> None:
        return super().__init_subclass__()

    def filter_by_normal(self, axis: Axis):
        return ShapeList(
            filter(
                lambda o: o.normalAt(o.Center()) == Vector(*ShapeList.axis_map[axis][0])
                or o.normalAt(o.Center()) == Vector(*ShapeList.axis_map[axis][1]),
                self,
            )
        )

    def filter_by_position(
        self,
        axis: Axis,
        min: float,
        max: float,
        inclusive: tuple[bool, bool] = (True, True),
    ):
        if axis == Axis.X:
            if inclusive == (True, True):
                result = filter(lambda o: min <= o.Center().x <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda o: min <= o.Center().x < max, self)
            elif inclusive == (False, True):
                result = filter(lambda o: min < o.Center().x <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda o: min < o.Center().x < max, self)
        elif axis == Axis.Y:
            if inclusive == (True, True):
                result = filter(lambda o: min <= o.Center().y <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda o: min <= o.Center().y < max, self)
            elif inclusive == (False, True):
                result = filter(lambda o: min < o.Center().y <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda o: min < o.Center().y < max, self)
        elif axis == Axis.Z:
            if inclusive == (True, True):
                result = filter(lambda o: min <= o.Center().z <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda o: min <= o.Center().z < max, self)
            elif inclusive == (False, True):
                result = filter(lambda o: min < o.Center().z <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda o: min < o.Center().z < max, self)

        return ShapeList(result)

    def sort_by(self, sort_by: SortBy = SortBy.Z, reverse: bool = False):

        if sort_by == SortBy.X:
            obj = sorted(
                self,
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            obj = sorted(
                self,
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            obj = sorted(
                self,
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.LENGTH:
            obj = sorted(
                self,
                key=lambda obj: obj.Length(),
                reverse=reverse,
            )
        elif sort_by == SortBy.RADIUS:
            obj = sorted(
                self,
                key=lambda obj: obj.radius(),
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            obj = sorted(
                self,
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        elif sort_by == SortBy.AREA:
            obj = sorted(
                self,
                key=lambda obj: obj.Area(),
                reverse=reverse,
            )
        elif sort_by == SortBy.VOLUME:
            obj = sorted(
                self,
                key=lambda obj: obj.Volume(),
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort shapes by {sort_by}")

        return ShapeList(obj)


class VertexList(list):
    def __init_subclass__(cls) -> None:
        return super().__init_subclass__()

    def filter_by_position(
        self,
        axis: Axis,
        min: float,
        max: float,
        inclusive: tuple[bool, bool] = (True, True),
    ):
        if axis == Axis.X:
            if inclusive == (True, True):
                result = filter(lambda v: min <= v.X <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda v: min <= v.X < max, self)
            elif inclusive == (False, True):
                result = filter(lambda v: min < v.X <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda v: min < v.X < max, self)
        elif axis == Axis.Y:
            if inclusive == (True, True):
                result = filter(lambda v: min <= v.Y <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda v: min <= v.Y < max, self)
            elif inclusive == (False, True):
                result = filter(lambda v: min < v.Y <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda v: min < v.Y < max, self)
        elif axis == Axis.Z:
            if inclusive == (True, True):
                result = filter(lambda v: min <= v.Z <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda v: min <= v.Z < max, self)
            elif inclusive == (False, True):
                result = filter(lambda v: min < v.Z <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda v: min < v.Z < max, self)
        return VertexList(result)

    def sort_by(self, sort_by: SortBy = SortBy.Z, reverse: bool = False):

        if sort_by == SortBy.X:
            vertices = sorted(
                self,
                key=lambda obj: obj.X,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            vertices = sorted(
                self,
                key=lambda obj: obj.Y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            vertices = sorted(
                self,
                key=lambda obj: obj.Z,
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            vertices = sorted(
                self,
                key=lambda obj: obj.toVector().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort vertices by {sort_by}")

        return VertexList(vertices)
