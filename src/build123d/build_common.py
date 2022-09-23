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
from itertools import product
from abc import ABC, abstractmethod
from math import radians, sqrt
from typing import Iterable, Union
from enum import Enum, auto
from cadquery import (
    Edge,
    Wire,
    Vector,
    Location,
    Face,
    Solid,
    Compound,
    Shape,
    Vertex,
    Plane,
    Matrix,
)
from cadquery.occ_impl.shapes import VectorLike
from OCP.gp import gp_Pnt, gp_Ax1, gp_Dir, gp_Trsf
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopoDS import TopoDS_Iterator
import cq_warehouse.extensions
import logging

# Create a build123d logger to distinguish these logs from application logs.
# If the user doesn't configure logging, all build123d logs will be discarded.
logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")

# The recommended user log configuration is as follows:
# logging.basicConfig(
#     filename="myapp.log",
#     level=logging.INFO,
#     format="%(name)s-%(levelname)s %(asctime)s - [%(filename)s:%(lineno)s - %(funcName)20s() ] - %(message)s",
# )
# Where using %(name)s in the log format will distinguish between user and build123d library logs


# Monkey patch Vertex to give it the x,y, and z property
def _vertex_x(self: Vertex):
    return self.X


def _vertex_y(self: Vertex):
    return self.Y


def _vertex_z(self: Vertex):
    return self.Z


Vertex.x = property(_vertex_x)
Vertex.y = property(_vertex_y)
Vertex.z = property(_vertex_z)

# Monkey patch Vector to give it the X,Y, and Z property
def _vector_x(self: Vector):
    return self.x


def _vector_y(self: Vector):
    return self.x


def _vector_z(self: Vector):
    return self.x


Vector.X = property(_vector_x)
Vector.Y = property(_vector_y)
Vector.Z = property(_vector_z)

z_axis = (Vector(0, 0, 0), Vector(0, 0, 1))


def vertex_eq_(self: Vertex, other: Vertex) -> bool:
    """True if the distance between the two vertices is lower than their tolerance"""
    return BRepTools.Compare_s(self.wrapped, other.wrapped)


Vertex.__eq__ = vertex_eq_


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


def compound_get_type(
    self: Compound, obj_type: Union[Edge, Face, Solid]
) -> list[Union[Edge, Face, Solid]]:
    iterator = TopoDS_Iterator()
    iterator.Initialize(self.wrapped)

    type_map = {
        Edge: TopAbs_ShapeEnum.TopAbs_EDGE,
        Wire: TopAbs_ShapeEnum.TopAbs_WIRE,
        Face: TopAbs_ShapeEnum.TopAbs_FACE,
        Solid: TopAbs_ShapeEnum.TopAbs_SOLID,
    }
    results = []
    while iterator.More():
        child = iterator.Value()
        if child.ShapeType() == type_map[obj_type]:
            results.append(obj_type(child))
        iterator.Next()

    return results


Compound.get_type = compound_get_type

#
# CONSTANTS
#
MM = 1
CM = 10 * MM
M = 1000 * MM
IN = 25.4 * MM
FT = 12 * IN


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
    """Extrude limit"""

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

#:TypeVar("PlaneLike"): Named Plane (e.g. "XY") or Plane
PlaneLike = Union[str, Plane]


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

    def __init__(self, mode: Mode = Mode.ADD, initial_plane: Plane = Plane.named("XY")):
        self.mode = mode
        self.initial_plane = initial_plane
        self._reset_tok = None
        self._parent = None
        self.last_vertices = []
        self.last_edges = []

    def __enter__(self):
        """Upon entering record the parent and a token to restore contextvars"""

        self._parent = Builder._get_context()
        self._reset_tok = self._current.set(self)

        # Push an initial plane and point
        self.workplane_generator = Workplanes(self.initial_plane).__enter__()

        logger.info(f"Entering {type(self).__name__} with mode={self.mode}")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)
        logger.info(f"Exiting {type(self).__name__}")

        # Pop the initial plane and point
        self.workplane_generator.__exit__(None, None, None)

        if self._parent is not None:
            logger.debug(
                f"Transferring {len([o for o in self._obj])} to {type(self._parent).__name__}"
            )
            if isinstance(self._obj, Iterable):
                self._parent._add_to_context(*self._obj, mode=self.mode)
            else:
                self._parent._add_to_context(self._obj, mode=self.mode)

    @abstractmethod
    def _obj(self):
        """Object to pass to parent"""
        return NotImplementedError  # pragma: no cover

    @abstractmethod
    def _add_to_context(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        mode: Mode = Mode.ADD,
    ):
        """Integrate a sequence of objects into existing builder object"""
        return NotImplementedError  # pragma: no cover

    @classmethod
    def _get_context(cls):
        """Return the instance of the current builder

        Note: each derived class can override this class to return the class
        type to keep IDEs happy. In Python 3.11 the return type should be set to Self
        here to avoid having to recreate this method.
        """
        return cls._current.get(None)


class LocationList:

    """Context variable used to link to LocationList instance"""

    _current: contextvars.ContextVar["LocationList"] = contextvars.ContextVar(
        "ContextList._current"
    )

    def __init__(self, locations: list[Location], planes: list[Plane]):
        self._reset_tok = None
        self.locations = locations
        self.planes = planes

    def __enter__(self):
        """Upon entering create a token to restore contextvars"""
        self._reset_tok = self._current.set(self)
        logger.info(f"{type(self).__name__} is pushing {len(self.locations)} points")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context"""
        self._current.reset(self._reset_tok)
        logger.info(f"{type(self).__name__} is popping {len(self.locations)} points")

    @classmethod
    def _get_context(cls):
        """Return the instance of the current LocationList"""
        return cls._current.get(None)


class HexLocations(LocationList):
    """Location Generator: Hex Array

    Creates a context of hexagon array of points.

    Args:
        diagonal: tip to tip size of hexagon ( must be > 0)
        xCount: number of points ( > 0 )
        yCount: number of points ( > 0 )
        centered: specify centering along each axis.

    Raises:
        ValueError: Spacing and count must be > 0
    """

    def __init__(
        self,
        diagonal: float,
        xCount: int,
        yCount: int,
        centered: tuple[bool, bool] = (True, True),
    ):
        xSpacing = 3 * diagonal / 4
        ySpacing = diagonal * sqrt(3) / 2
        if xSpacing <= 0 or ySpacing <= 0 or xCount < 1 or yCount < 1:
            raise ValueError("Spacing and count must be > 0 ")

        points = []  # coordinates relative to bottom left point
        for x in range(0, xCount, 2):
            for y in range(yCount):
                points.append(Vector(xSpacing * x, ySpacing * y + ySpacing / 2))
        for x in range(1, xCount, 2):
            for y in range(yCount):
                points.append(Vector(xSpacing * x, ySpacing * y + ySpacing))

        # shift points down and left relative to origin if requested
        offset = Vector()
        if centered[0]:
            offset += Vector(-xSpacing * (xCount - 1) * 0.5, 0)
        if centered[1]:
            offset += Vector(0, -ySpacing * yCount * 0.5)
        points = [x + offset for x in points]

        # convert to locations and store the reference plane
        self.locations = []
        self.planes = []
        for plane in WorkplaneList._get_context().workplanes:
            for pt in points:
                self.locations.append(Location(plane) * Location(pt))
                self.planes.append(plane)

        super().__init__(self.locations, self.planes)


class PolarLocations(LocationList):
    """Location Generator: Polar Array

    Push a polar array of locations to Part or Sketch

    Args:
        radius (float): array radius
        start_angle (float): angle to first point from +ve X axis
        stop_angle (float): angle to last point from +ve X axis
        count (int): Number of points to push
        rotate (bool, optional): Align locations with arc tangents. Defaults to True.

    Raises:
        ValueError: Count must be greater than or equal to 1
    """

    def __init__(
        self,
        radius: float,
        start_angle: float,
        stop_angle: float,
        count: int,
        rotate: bool = True,
    ):
        if count < 1:
            raise ValueError(f"At least 1 elements required, requested {count}")

        angle_step = (stop_angle - start_angle) / count

        # Note: rotate==False==0 so the location orientation doesn't change
        self.locations = []
        self.planes = []
        for plane in WorkplaneList._get_context().workplanes:
            for i in range(count):
                self.locations.append(
                    Location(plane)
                    * Location(
                        Vector(radius, 0).rotateZ(start_angle + angle_step * i),
                        Vector(0, 0, 1),
                        rotate * angle_step * i,
                    )
                )
            self.planes.append(plane)
        super().__init__(self.locations, self.planes)


class Locations(LocationList):
    """Location Generator: Push Points

    Push sequence of locations to Part or Sketch

    Args:
        pts (Union[VectorLike, Vertex, Location]): sequence of points to push
    """

    def __init__(self, *pts: Union[VectorLike, Vertex, Location]):
        self.locations = []
        self.planes = []
        for plane in WorkplaneList._get_context().workplanes:
            for pt in pts:
                if isinstance(pt, Location):
                    self.locations.append(Location(plane) * pt)
                elif isinstance(pt, Vector):
                    self.locations.append(Location(plane) * Location(pt))
                elif isinstance(pt, Vertex):
                    self.locations.append(
                        Location(plane) * Location(Vector(pt.toTuple()))
                    )
                elif isinstance(pt, tuple):
                    self.locations.append(Location(plane) * Location(Vector(pt)))
                else:
                    raise ValueError(f"Locations doesn't accept type {type(pt)}")
                self.planes.append(plane)
        super().__init__(self.locations, self.planes)


class GridLocations(LocationList):
    """Location Generator: Rectangular Array

    Push a rectangular array of locations to Part or Sketch

    Args:
        x_spacing (float): horizontal spacing
        y_spacing (float): vertical spacing
        x_count (int): number of horizontal points
        y_count (int): number of vertical points

    Raises:
        ValueError: Either x or y count must be greater than or equal to one.
    """

    def __init__(self, x_spacing: float, y_spacing: float, x_count: int, y_count: int):
        if x_count < 1 or y_count < 1:
            raise ValueError(
                f"At least 1 elements required, requested {x_count}, {y_count}"
            )

        self.locations = []
        self.planes = []
        for plane in WorkplaneList._get_context().workplanes:
            offset = Vector((x_count - 1) * x_spacing, (y_count - 1) * y_spacing) * 0.5
            for i, j in product(range(x_count), range(y_count)):
                self.locations.append(
                    Location(plane)
                    * Location(Vector(i * x_spacing, j * y_spacing) - offset)
                )
                self.planes.append(plane)
        super().__init__(self.locations, self.planes)


class WorkplaneList:

    """Context variable used to link to WorkplaneList instance"""

    _current: contextvars.ContextVar["WorkplaneList"] = contextvars.ContextVar(
        "WorkplaneList._current"
    )

    def __init__(self, workplanes: list):
        self._reset_tok = None
        self.workplanes = workplanes

    def __enter__(self):
        """Upon entering create a token to restore contextvars"""
        self._reset_tok = self._current.set(self)
        self.point_generator = Locations((0, 0, 0)).__enter__()
        logger.info(
            f"{type(self).__name__} is pushing {len(self.workplanes)} workplanes"
        )
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context"""
        self._current.reset(self._reset_tok)
        self.point_generator.__exit__(None, None, None)
        logger.info(
            f"{type(self).__name__} is popping {len(self.workplanes)} workplanes"
        )

    @classmethod
    def _get_context(cls):
        """Return the instance of the current ContextList"""
        return cls._current.get(None)


class Workplanes(WorkplaneList):
    """Workplane Generator: Workplanes

    Create workplanes from the given sequence of planes.

    Args:
        objs (Union[Face,PlaneLike]): sequence of faces or planes to use
            as workplanes.
    Raises:
        ValueError: invalid input
    """

    def __init__(self, *objs: Union[Face, PlaneLike]):
        self.workplanes = []
        for obj in objs:
            if isinstance(obj, Plane):
                self.workplanes.append(obj)
            elif isinstance(obj, str):
                self.workplanes.append(Plane.named(obj))
            elif isinstance(obj, Face):
                self.workplanes.append(
                    Plane(origin=obj.Center(), normal=obj.normalAt(obj.Center()))
                )
            else:
                raise ValueError(f"Workplanes does not accept {type(obj)}")
        super().__init__(self.workplanes)
