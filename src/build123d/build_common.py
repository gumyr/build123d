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
from cadquery import Edge, Wire, Vector, Location, Face, Solid, Compound, Shape, Vertex
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

# context_stack = []

#
# ENUMs
#
class Select(Enum):
    """Selector scope - all or last operation"""

    ALL = auto()
    LAST = auto()


class Kind(Enum):
    """Offset corner transition"""

    ARC = auto()
    INTERSECTION = auto()
    TANGENT = auto()


class Keep(Enum):
    """Split options"""

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
    """Sweep discontinuity handling option"""

    RIGHT = auto()
    ROUND = auto()
    TRANSFORMED = auto()


class FontStyle(Enum):
    """Text Font Styles"""

    REGULAR = auto()
    BOLD = auto()
    ITALIC = auto()


class Halign(Enum):
    """Text Horizontal Alignment"""

    CENTER = auto()
    LEFT = auto()
    RIGHT = auto()


class Valign(Enum):
    """Text Vertical Alignment"""

    CENTER = auto()
    TOP = auto()
    BOTTOM = auto()


class Until(Enum):
    """Extude limit"""

    NEXT = auto()
    LAST = auto()


class Axis(Enum):
    """One of the three dimensions"""

    X = auto()
    Y = auto()
    Z = auto()


class SortBy(Enum):
    """Sorting criteria"""

    X = auto()
    Y = auto()
    Z = auto()
    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()


class Type(Enum):
    """CAD object type"""

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
    """Subclass of Location used only for object rotation"""

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


#:TypeVar("RotationLike"): Three tuple of angles about x, y, z or Rotation
RotationLike = Union[tuple[float, float, float], Rotation]


class ShapeList(list):
    """Subclass of list with custom filter and sort methods appropriate to CAD"""

    axis_map = {
        Axis.X: ((1, 0, 0), (-1, 0, 0)),
        Axis.Y: ((0, 1, 0), (0, -1, 0)),
        Axis.Z: ((0, 0, 1), (0, 0, -1)),
    }

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()

    def filter_by_axis(self, axis: Axis, tolerance=1e-5):
        """filter by axis

        Filter objects of type planar Face or linear Edge by their normal or tangent
        (respectively) and sort the results by the given axis.

        Args:
            axis (Axis): axis to filter and sort by
            tolerance (_type_, optional): maximum deviation from axis. Defaults to 1e-5.

        Returns:
            ShapeList: sublist of Faces or Edges
        """

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
                        o.tangentAt(0) - Vector(*ShapeList.axis_map[axis][0])
                    ).Length
                    <= tolerance
                    or (o.tangentAt(0) - Vector(*ShapeList.axis_map[axis][1])).Length
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
        """filter by position

        Filter and sort objects by the position of their centers along given axis.
        min and max values can be inclusive or exclusive depending on the inclusive tuple.

        Args:
            axis (Axis): axis to sort by
            min (float): minimum value
            max (float): maximum value
            inclusive (tuple[bool, bool], optional): include min,max values. Defaults to (True, True).

        Returns:
            ShapeList: filtered object list
        """
        if axis == Axis.X:
            if inclusive == (True, True):
                result = filter(lambda o: min <= o.Center().x <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda o: min <= o.Center().x < max, self)
            elif inclusive == (False, True):
                result = filter(lambda o: min < o.Center().x <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda o: min < o.Center().x < max, self)
            result = sorted(result, key=lambda obj: obj.Center().x)
        elif axis == Axis.Y:
            if inclusive == (True, True):
                result = filter(lambda o: min <= o.Center().y <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda o: min <= o.Center().y < max, self)
            elif inclusive == (False, True):
                result = filter(lambda o: min < o.Center().y <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda o: min < o.Center().y < max, self)
            result = sorted(result, key=lambda obj: obj.Center().y)
        elif axis == Axis.Z:
            if inclusive == (True, True):
                result = filter(lambda o: min <= o.Center().z <= max, self)
            elif inclusive == (True, False):
                result = filter(lambda o: min <= o.Center().z < max, self)
            elif inclusive == (False, True):
                result = filter(lambda o: min < o.Center().z <= max, self)
            elif inclusive == (False, False):
                result = filter(lambda o: min < o.Center().z < max, self)
            result = sorted(result, key=lambda obj: obj.Center().z)

        return ShapeList(result)

    def filter_by_type(
        self,
        type: Type,
    ):
        """filter by type

        Filter the objects by the provided type. Note that not all types apply to all
        objects.

        Args:
            type (Type): type to sort by

        Returns:
            ShapeList: filtered list of objects
        """
        result = filter(lambda o: o.geomType() == type.name, self)
        return ShapeList(result)

    def sort_by(self, sort_by: SortBy = SortBy.Z, reverse: bool = False):
        """sort by

        Sort objects by provided criteria. Note that not all sort_by criteria apply to all
        objects.

        Args:
            sort_by (SortBy, optional): sort criteria. Defaults to SortBy.Z.
            reverse (bool, optional): flip order of sort. Defaults to False.

        Returns:
            ShapeList: sorted list of objects
        """
        if sort_by == SortBy.X:
            objects = sorted(
                self,
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            objects = sorted(
                self,
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            objects = sorted(
                self,
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.LENGTH:
            objects = sorted(
                self,
                key=lambda obj: obj.Length(),
                reverse=reverse,
            )
        elif sort_by == SortBy.RADIUS:
            objects = sorted(
                self,
                key=lambda obj: obj.radius(),
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            objects = sorted(
                self,
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        elif sort_by == SortBy.AREA:
            objects = sorted(
                self,
                key=lambda obj: obj.Area(),
                reverse=reverse,
            )
        elif sort_by == SortBy.VOLUME:
            objects = sorted(
                self,
                key=lambda obj: obj.Volume(),
                reverse=reverse,
            )

        return ShapeList(objects)


def _vertices(self: Shape) -> ShapeList[Vertex]:
    """Return ShapeList of Vertex in self"""
    return ShapeList(self.Vertices())


def _edges(self: Shape) -> ShapeList[Edge]:
    """Return ShapeList of Edge in self"""
    return ShapeList(self.Edges())


def _wires(self: Shape) -> ShapeList[Wire]:
    """Return ShapeList of Wire in self"""
    return ShapeList(self.Wires())


def _faces(self: Shape) -> ShapeList[Face]:
    """Return ShapeList of Face in self"""
    return ShapeList(self.Faces())


def _compounds(self: Shape) -> ShapeList[Compound]:
    """Return ShapeList of Compound in self"""
    return ShapeList(self.Compounds())


def _solids(self: Shape) -> ShapeList[Solid]:
    """Return ShapeList of Solid in self"""
    return ShapeList(self.Solids())


# Monkey patch ShapeList methods
Shape.vertices = _vertices
Shape.edges = _edges
Shape.wires = _wires
Shape.faces = _faces
Shape.compounds = _compounds
Shape.solids = _solids


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
