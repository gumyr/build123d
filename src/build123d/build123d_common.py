"""
Build123D Common

name: build123d_common.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build 3D parts.

TODO:
- Update Vector so it can be initialized with a Vertex or Location
- Update VectorLike to include a Vertex and Location

license:

    Copyright 2022 Gumyr

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
import contextvars
from abc import ABC, abstractmethod
from math import radians
from typing import Iterable, Union
from enum import Enum, auto
from cadquery import Edge, Wire, Vector, Location, Face, Solid, Compound, Vertex
from OCP.gp import gp_Pnt, gp_Ax1, gp_Dir, gp_Trsf
import cq_warehouse.extensions


z_axis = (Vector(0, 0, 0), Vector(0, 0, 1))

#
# Operators
#
def __matmul__custom(e: Union[Edge, Wire], p: float):
    return e.positionAt(p)


def __mod__custom(e: Union[Edge, Wire], p: float):
    return e.tangentAt(p)


Edge.__matmul__ = __matmul__custom
Edge.__mod__ = __mod__custom
Wire.__matmul__ = __matmul__custom
Wire.__mod__ = __mod__custom

context_stack = []

#
# ENUMs
#
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
    BOTH = auto()


class Mode(Enum):
    """Combination Mode"""

    ADD = auto()
    SUBTRACT = auto()
    INTERSECT = auto()
    REPLACE = auto()
    PRIVATE = auto()


class Transition(Enum):
    RIGHT = auto()
    ROUND = auto()
    TRANSFORMED = auto()


class FontStyle(Enum):
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


class SortBy(Enum):
    X = auto()
    Y = auto()
    Z = auto()
    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()


class Type(Enum):
    PLANE = auto()
    CYLINDER = auto()
    CONE = auto()
    SPHERE = auto()
    TORUS = auto()
    BEZIER = auto()
    BSPLINE = auto()
    REVOLUTION = auto()
    EXTRUSION = auto()
    OFFSET = auto()
    LINE = auto()
    CIRCLE = auto()
    ELLIPSE = auto()
    HYPERBOLA = auto()
    PARABOLA = auto()
    OTHER = auto()


#
# DirectAPI Classes
#
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


class ShapeList(list):
    axis_map = {
        Axis.X: ((1, 0, 0), (-1, 0, 0)),
        Axis.Y: ((0, 1, 0), (0, -1, 0)),
        Axis.Z: ((0, 0, 1), (0, 0, -1)),
    }

    def __init_subclass__(cls) -> None:
        return super().__init_subclass__()

    def filter_by_axis(self, axis: Axis, tolerance=1e-5):

        planar_faces = filter(
            lambda o: isinstance(o, Face) and o.geomType() == "PLANE", self
        )
        linear_edges = filter(
            lambda o: isinstance(o, Edge) and o.geomType() == "LINE", self
        )

        result = []

        result = list(
            filter(
                lambda o: (
                    o.normalAt(None) - Vector(*ShapeList.axis_map[axis][0])
                ).Length
                <= tolerance
                or (o.normalAt(None) - Vector(*ShapeList.axis_map[axis][1])).Length
                <= tolerance,
                planar_faces,
            )
        )
        result.extend(
            list(
                filter(
                    lambda o: (
                        o.tangentAt(None) - Vector(*ShapeList.axis_map[axis][0])
                    ).Length
                    <= tolerance
                    or (
                        o.tangentAt(o.Center()) - Vector(*ShapeList.axis_map[axis][1])
                    ).Length
                    <= tolerance,
                    linear_edges,
                )
            )
        )
        if axis == Axis.X:
            result = sorted(result, key=lambda obj: obj.Center().x)
        elif axis == Axis.Y:
            result = sorted(result, key=lambda obj: obj.Center().y)
        elif axis == Axis.Z:
            result = sorted(result, key=lambda obj: obj.Center().z)

        return ShapeList(result)

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

    def filter_by_type(
        self,
        type: Type,
    ):
        result = filter(lambda o: o.geomType() == type.name, self)
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


class Builder(ABC):
    """Builder

    Base class for the build123d Builders.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    """Context variable used to by Objects and Operations to link to current builder instance"""
    _current: contextvars.ContextVar["Builder"] = contextvars.ContextVar(
        "Builder._current"
    )

    def __init__(self, mode: Mode = Mode.ADD):
        self.mode = mode
        self._reset_tok = None
        self._parent = None
        self.last_vertices = []
        self.last_edges = []

    def __enter__(self):
        """Upon entering record the parent and a token to restore contextvars"""
        self._parent = Builder._get_context()
        self._reset_tok = self._current.set(self)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)
        if self._parent is not None:
            if isinstance(self._obj, Iterable):
                self._parent._add_to_context(*self._obj, mode=self.mode)
            else:
                self._parent._add_to_context(self._obj, mode=self.mode)

    @abstractmethod
    def _obj(self):
        """Object to pass to parent"""
        return NotImplementedError

    @abstractmethod
    def _add_to_context(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        mode: Mode = Mode.ADD,
    ):
        """Integrate a sequence of objects into existing builder object"""
        return NotImplementedError

    @classmethod
    def _get_context(cls):
        """Return the instance of the current builder

        Note: each derived class can override this class to return the class
        type to keep IDEs happy. In Python 3.11 the return type should be set to Self
        here to avoid having to recreate this method.
        """
        return cls._current.get(None)
