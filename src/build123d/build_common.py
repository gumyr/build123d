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
from __future__ import annotations
import contextvars
from itertools import product
from abc import ABC, abstractmethod
from math import radians, sqrt, pi
from typing import Iterable, Union
from enum import Enum, auto
import logging
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
    Shell,
)
from cadquery.occ_impl.shapes import VectorLike
from OCP.gp import gp_Pnt, gp_Ax1, gp_Dir, gp_Trsf
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopoDS import TopoDS_Iterator
import cq_warehouse.extensions

# Create a build123d logger to distinguish these logs from application logs.
# If the user doesn't configure logging, all build123d logs will be discarded.
logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")

# The recommended user log configuration is as follows:
# logging.basicConfig(
#     filename="myapp.log",
#     level=logging.INFO,
#     format="%(name)s-%(levelname)s %(asctime)s - [%(filename)s:%(lineno)s - \
#     %(funcName)20s() ] - %(message)s",
# )
# Where using %(name)s in the log format will distinguish between user and build123d library logs


# Monkey patch Vector to give it the X,Y, and Z property
def _vector_x(self: Vector):
    return self.x


def _vector_y(self: Vector):
    return self.y


def _vector_z(self: Vector):
    return self.z


Vector.X = property(_vector_x)
Vector.Y = property(_vector_y)
Vector.Z = property(_vector_z)


def vertex_eq_(self: Vertex, other: Vertex) -> bool:
    """True if the distance between the two vertices is lower than their tolerance"""
    return BRepTools.Compare_s(self.wrapped, other.wrapped)


Vertex.__eq__ = vertex_eq_


#
# Operators
#
def __matmul__custom(wire_edge: Union[Edge, Wire], position: float):
    return wire_edge.positionAt(position)


def __mod__custom(wire_edge: Union[Edge, Wire], position: float):
    return wire_edge.tangentAt(position)


Edge.__matmul__ = __matmul__custom
Edge.__mod__ = __mod__custom
Wire.__matmul__ = __matmul__custom
Wire.__mod__ = __mod__custom


def compound_get_type(
    self: Compound, obj_type: Union[Edge, Wire, Face, Solid]
) -> list[Union[Edge, Wire, Face, Solid]]:
    """get_type

    Extract the objects of the given type from a Compound. Note that this
    isn't the same as Faces() etc. which will extract Faces from Solids.

    Args:
        obj_type (Union[Edge, Face, Solid]): Object types to extract

    Returns:
        list[Union[Edge, Face, Solid]]: Extracted objects
    """
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

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Kind(Enum):
    """Offset corner transition"""

    ARC = auto()
    INTERSECTION = auto()
    TANGENT = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Keep(Enum):
    """Split options"""

    TOP = auto()
    BOTTOM = auto()
    BOTH = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Mode(Enum):
    """Combination Mode"""

    ADD = auto()
    SUBTRACT = auto()
    INTERSECT = auto()
    REPLACE = auto()
    PRIVATE = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Transition(Enum):
    """Sweep discontinuity handling option"""

    RIGHT = auto()
    ROUND = auto()
    TRANSFORMED = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class FontStyle(Enum):
    """Text Font Styles"""

    REGULAR = auto()
    BOLD = auto()
    ITALIC = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Halign(Enum):
    """Text Horizontal Alignment"""

    CENTER = auto()
    LEFT = auto()
    RIGHT = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Valign(Enum):
    """Text Vertical Alignment"""

    CENTER = auto()
    TOP = auto()
    BOTTOM = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Until(Enum):
    """Extrude limit"""

    NEXT = auto()
    LAST = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class SortBy(Enum):
    """Sorting criteria"""

    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class GeomType(Enum):
    """CAD geometry object type"""

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

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


def validate_inputs(validating_class, builder_context, objects: Shape = None):
    """Validate that objects/operations and parameters apply"""

    if not objects:
        objects = []

    # Check for builder / object matches
    if not builder_context:
        builder_dict = {
            "build123d.build_line": "BuildLine()",
            "build123d.build_sketch": "BuildSketch()",
            "build123d.build_part": "BuildPart()",
            "build123d.build_generic": "BuildLine() | BuildSketch() | BuildPart()",
        }
        raise RuntimeError(
            f"{validating_class.__class__.__name__} doesn't have an active builder, "
            f"did you miss a with {builder_dict[validating_class.__module__]}:"
        )
    if not (
        validating_class.__module__
        in [builder_context.__module__, "build123d.build_generic"]
    ):
        raise RuntimeError(
            f"{builder_context.__class__.__name__} doesn't have a "
            f"{validating_class.__class__.__name__} object or operation"
        )
    # Check for valid object inputs
    for obj in objects:
        if obj is None:
            pass
        elif isinstance(obj, Builder):
            raise RuntimeError(
                f"{validating_class.__class__.__name__} doesn't accept Builders as input,"
                f" did you intend <{obj.__class__.__name__}>.{obj._obj_name}?"
            )
        elif isinstance(obj, list):
            raise RuntimeError(
                f"{validating_class.__class__.__name__} doesn't accept {type(obj).__name__},"
                f" did you intend *{obj}?"
            )
        elif not isinstance(obj, Shape):
            raise RuntimeError(
                f"{validating_class.__class__.__name__} doesn't accept {type(obj).__name__},"
                f" did you intend <keyword>={obj}?"
            )


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
        rot_x = gp_Trsf()
        rot_x.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), radians(about_x))
        rot_y = gp_Trsf()
        rot_y.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), radians(about_y))
        rot_z = gp_Trsf()
        rot_z.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), radians(about_z))
        super().__init__(Location(rot_x * rot_y * rot_z).wrapped)


#:TypeVar("RotationLike"): Three tuple of angles about x, y, z or Rotation
RotationLike = Union[tuple[float, float, float], Rotation]

#:TypeVar("PlaneLike"): Named Plane (e.g. "XY") or Plane
PlaneLike = Union[str, Plane]


class Axis:
    """Axis

    Axis defined by point and direction

    Args:
        origin (VectorLike): start point
        direction (VectorLike): direction
    """

    @classmethod
    @property
    def X(cls) -> Axis:
        """X Axis"""
        return Axis((0, 0, 0), (1, 0, 0))

    @classmethod
    @property
    def Y(cls) -> Axis:
        """Y Axis"""
        return Axis((0, 0, 0), (0, 1, 0))

    @classmethod
    @property
    def Z(cls) -> Axis:
        """Z Axis"""
        return Axis((0, 0, 0), (0, 0, 1))

    def __init__(self, origin: VectorLike, direction: VectorLike):
        self.wrapped = gp_Ax1(
            Vector(origin).toPnt(), gp_Dir(*Vector(direction).normalized().toTuple())
        )
        self.position = Vector(
            self.wrapped.Location().X(),
            self.wrapped.Location().Y(),
            self.wrapped.Location().Z(),
        )
        self.direction = Vector(
            self.wrapped.Direction().X(),
            self.wrapped.Direction().Y(),
            self.wrapped.Direction().Z(),
        )

    @classmethod
    def from_occt(cls, axis: gp_Ax1) -> Axis:
        """Create an Axis instance from the occt object"""
        position = (
            axis.Location().X(),
            axis.Location().Y(),
            axis.Location().Z(),
        )
        direction = (
            axis.Direction().X(),
            axis.Direction().Y(),
            axis.Direction().Z(),
        )
        return Axis(position, direction)

    def __repr__(self) -> str:
        return f"({self.position.toTuple()},{self.direction.toTuple()})"

    def __str__(self) -> str:
        return f"Axis: ({self.position.toTuple()},{self.direction.toTuple()})"

    def copy(self) -> Axis:
        """Return copy of self"""
        # Doesn't support sub-classing
        return Axis(self.position, self.direction)

    def to_location(self) -> Location:
        """Return self as Location"""
        return Location(Plane(origin=self.position, normal=self.direction))

    def to_plane(self) -> Plane:
        """Return self as Plane"""
        return Plane(origin=self.position, normal=self.direction)

    def is_coaxial(
        self,
        other: Axis,
        angular_tolerance: float = 1e-5,
        linear_tolerance: float = 1e-5,
    ) -> bool:
        """are axes coaxial

        True if the angle between self and other is lower or equal to angular_tolerance and
        the distance between self and other is lower or equal to linear_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.
            linear_tolerance (float, optional): max linear deviation. Defaults to 1e-5.

        Returns:
            bool: axes are coaxial
        """
        return self.wrapped.IsCoaxial(
            other.wrapped, angular_tolerance * (pi / 180), linear_tolerance
        )

    def is_normal(self, other: Axis, angular_tolerance: float = 1e-5) -> bool:
        """are axes normal

        Returns True if the direction of this and another axis are normal to each other. That is,
        if the angle between the two axes is equal to 90° within the angular_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.

        Returns:
            bool: axes are normal
        """
        return self.wrapped.IsNormal(other.wrapped, angular_tolerance * (pi / 180))

    def is_opposite(self, other: Axis, angular_tolerance: float = 1e-5) -> bool:
        """are axes opposite

        Returns True if the direction of this and another axis are parallel with
        opposite orientation. That is, if the angle between the two axes is equal
        to 180° within the angular_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.

        Returns:
            bool: axes are opposite
        """
        return self.wrapped.IsOpposite(other.wrapped, angular_tolerance * (pi / 180))

    def is_parallel(self, other: Axis, angular_tolerance: float = 1e-5) -> bool:
        """are axes parallel

        Returns True if the direction of this and another axis are parallel with same
        orientation or opposite orientation. That is, if the angle between the two axes is
        equal to 0° or 180° within the angular_tolerance.

        Args:
            other (Axis): axis to compare to
            angular_tolerance (float, optional): max angular deviation. Defaults to 1e-5.

        Returns:
            bool: axes are parallel
        """
        return self.wrapped.IsParallel(other.wrapped, angular_tolerance * (pi / 180))

    def angle_between(self, other: Axis) -> float:
        """calculate angle between axes

        Computes the angular value, in degrees, between the direction of self and other
        between 0° and 360°.

        Args:
            other (Axis): axis to compare to

        Returns:
            float: angle between axes
        """
        return self.wrapped.Angle(other.wrapped) * 180 / pi

    def reversed(self) -> Axis:
        """Return a copy of self with the direction reversed"""
        return Axis.from_occt(self.wrapped.Reversed())


class ShapeList(list):
    """Subclass of list with custom filter and sort methods appropriate to CAD"""

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

        result = list(
            filter(
                lambda o: axis.is_parallel(
                    Axis(o.Center(), o.normalAt(None)), tolerance
                ),
                planar_faces,
            )
        )
        result.extend(
            list(
                filter(
                    lambda o: axis.is_parallel(
                        Axis(o.positionAt(0), o.tangentAt(0)), tolerance
                    ),
                    linear_edges,
                )
            )
        )

        return ShapeList(result).sort_by(axis)

    def filter_by_position(
        self,
        axis: Axis,
        minimum: float,
        maximum: float,
        inclusive: tuple[bool, bool] = (True, True),
    ):
        """filter by position

        Filter and sort objects by the position of their centers along given axis.
        min and max values can be inclusive or exclusive depending on the inclusive tuple.

        Args:
            axis (Axis): axis to sort by
            minimum (float): minimum value
            maximum (float): maximum value
            inclusive (tuple[bool, bool], optional): include min,max values.
                Defaults to (True, True).

        Returns:
            ShapeList: filtered object list
        """
        if inclusive == (True, True):
            objects = filter(
                lambda o: minimum
                <= axis.to_plane().toLocalCoords(o).Center().z
                <= maximum,
                self,
            )
        elif inclusive == (True, False):
            objects = filter(
                lambda o: minimum
                <= axis.to_plane().toLocalCoords(o).Center().z
                < maximum,
                self,
            )
        elif inclusive == (False, True):
            objects = filter(
                lambda o: minimum
                < axis.to_plane().toLocalCoords(o).Center().z
                <= maximum,
                self,
            )
        elif inclusive == (False, False):
            objects = filter(
                lambda o: minimum
                < axis.to_plane().toLocalCoords(o).Center().z
                < maximum,
                self,
            )

        return ShapeList(objects).sort_by(axis)

    def filter_by_type(
        self,
        geom_type: GeomType,
    ):
        """filter by type

        Filter the objects by the provided type. Note that not all types apply to all
        objects.

        Args:
            type (Type): type to sort by

        Returns:
            ShapeList: filtered list of objects
        """
        result = filter(lambda o: o.geomType() == geom_type.name, self)
        return ShapeList(result)

    def sort_by(self, sort_by: Union[Axis, SortBy] = Axis.Z, reverse: bool = False):
        """sort by

        Sort objects by provided criteria. Note that not all sort_by criteria apply to all
        objects.

        Args:
            sort_by (SortBy, optional): sort criteria. Defaults to SortBy.Z.
            reverse (bool, optional): flip order of sort. Defaults to False.

        Returns:
            ShapeList: sorted list of objects
        """
        if isinstance(sort_by, Axis):
            objects = sorted(
                self,
                key=lambda o: sort_by.to_plane().toLocalCoords(o).Center().z,
                reverse=reverse,
            )

        elif isinstance(sort_by, SortBy):
            if sort_by == SortBy.LENGTH:
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
        else:
            raise ValueError(f"Sort by {type(sort_by)} unsupported")

        return ShapeList(objects)

    def __gt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort operator"""
        return self.sort_by(sort_by)

    def __lt__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Reverse sort operator"""
        return self.sort_by(sort_by, reverse=True)

    def __rshift__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort and select largest element operator"""
        return self.sort_by(sort_by)[-1]

    def __lshift__(self, sort_by: Union[Axis, SortBy] = Axis.Z):
        """Sort and select smallest element operator"""
        return self.sort_by(sort_by)[0]

    def __or__(self, axis: Axis = Axis.Z):
        """Filter by axis operator"""
        return self.filter_by_axis(axis)

    def __mod__(self, geom_type: GeomType):
        """Filter by geometry type operator"""
        return self.filter_by_type(geom_type)

    def __getitem__(self, key):
        """Return slices of ShapeList as ShapeList"""
        if isinstance(key, slice):
            return ShapeList(list(self).__getitem__(key))
        else:
            return list(self).__getitem__(key)


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

    # Context variable used to by Objects and Operations to link to current builder instance
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
        self.workplane_generator = None

    def __enter__(self):
        """Upon entering record the parent and a token to restore contextvars"""

        self._parent = Builder._get_context()
        self._reset_tok = self._current.set(self)

        # Push an initial plane and point
        self.workplane_generator = Workplanes(self.initial_plane).__enter__()

        logger.info("Entering %s with mode=%s", type(self).__name__, self.mode)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)
        logger.info("Exiting %s", type(self).__name__)

        # Pop the initial plane and point
        self.workplane_generator.__exit__(None, None, None)

        if self._parent is not None:
            logger.debug("Transferring line to %s", type(self._parent).__name__)
            if isinstance(self._obj, Iterable):
                self._parent._add_to_context(*self._obj, mode=self.mode)
            else:
                self._parent._add_to_context(self._obj, mode=self.mode)

    @abstractmethod
    def _obj(self):
        """Object to pass to parent"""
        return NotImplementedError  # pragma: no cover

    @abstractmethod
    def _obj_name(self):
        """Name of object to pass to parent"""
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

    def vertices(self, select: Select = Select.ALL) -> ShapeList[Vertex]:
        """Return Vertices from Part

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            VertexList[Vertex]: Vertices extracted
        """
        vertex_list = []
        if select == Select.ALL:
            for edge in self._obj.Edges():
                vertex_list.extend(edge.Vertices())
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return ShapeList(set(vertex_list))

    def edges(self, select: Select = Select.ALL) -> ShapeList[Edge]:
        """Return Edges from Part

        Return either all or the edges created during the last operation.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: Edges extracted
        """
        if select == Select.ALL:
            edge_list = self._obj.Edges()
        elif select == Select.LAST:
            edge_list = self.last_edges
        return ShapeList(edge_list)

    def faces(self, select: Select = Select.ALL) -> ShapeList[Face]:
        """Return Faces from Sketch

        Return either all or the faces created during the last operation.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Face]: Faces extracted
        """
        if select == Select.ALL:
            face_list = self._obj.Faces()
        elif select == Select.LAST:
            face_list = self.last_faces
        return ShapeList(face_list)


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
        logger.info("%s is pushing %d points", type(self).__name__, len(self.locations))
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context"""
        self._current.reset(self._reset_tok)
        logger.info("%s is popping %d points", type(self).__name__, len(self.locations))

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
        x_count: int,
        y_count: int,
        centered: tuple[bool, bool] = (True, True),
    ):
        x_spacing = 3 * diagonal / 4
        y_spacing = diagonal * sqrt(3) / 2
        if x_spacing <= 0 or y_spacing <= 0 or x_count < 1 or y_count < 1:
            raise ValueError("Spacing and count must be > 0 ")

        points = []  # coordinates relative to bottom left point
        for x_val in range(0, x_count, 2):
            for y_val in range(y_count):
                points.append(
                    Vector(x_spacing * x_val, y_spacing * y_val + y_spacing / 2)
                )
        for x_val in range(1, x_count, 2):
            for y_val in range(y_count):
                points.append(Vector(x_spacing * x_val, y_spacing * y_val + y_spacing))

        # shift points down and left relative to origin if requested
        offset = Vector()
        if centered[0]:
            offset += Vector(-x_spacing * (x_count - 1) * 0.5, 0)
        if centered[1]:
            offset += Vector(0, -y_spacing * y_count * 0.5)
        points = [x + offset for x in points]

        # convert to locations and store the reference plane
        self.locations = []
        self.planes = []
        for plane in WorkplaneList._get_context().workplanes:
            for point in points:
                self.locations.append(Location(plane) * Location(point))
                self.planes.append(plane)

        super().__init__(self.locations, self.planes)


class PolarLocations(LocationList):
    """Location Generator: Polar Array

    Push a polar array of locations to Part or Sketch

    Args:
        radius (float): array radius
        count (int): Number of points to push
        start_angle (float, optional): angle to first point from +ve X axis. Deaults to 0.0.
        stop_angle (float, optional): angle to last point from +ve X axis. Defaults to 360.0.
        rotate (bool, optional): Align locations with arc tangents. Defaults to True.

    Raises:
        ValueError: Count must be greater than or equal to 1
    """

    def __init__(
        self,
        radius: float,
        count: int,
        start_angle: float = 0.0,
        stop_angle: float = 360.0,
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
            for point in pts:
                if isinstance(point, Location):
                    self.locations.append(Location(plane) * point)
                elif isinstance(point, Vector):
                    self.locations.append(Location(plane) * Location(point))
                elif isinstance(point, Vertex):
                    self.locations.append(
                        Location(plane) * Location(Vector(point.toTuple()))
                    )
                elif isinstance(point, tuple):
                    self.locations.append(Location(plane) * Location(Vector(point)))
                else:
                    raise ValueError(f"Locations doesn't accept type {type(point)}")
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
        centered: specify centering along each axis.

    Raises:
        ValueError: Either x or y count must be greater than or equal to one.
    """

    def __init__(
        self,
        x_spacing: float,
        y_spacing: float,
        x_count: int,
        y_count: int,
        centered: tuple[bool, bool] = (True, True),
    ):
        if x_count < 1 or y_count < 1:
            raise ValueError(
                f"At least 1 elements required, requested {x_count}, {y_count}"
            )
        self.x_spacing = x_spacing
        self.y_spacing = y_spacing
        self.x_count = x_count
        self.y_count = y_count
        self.centered = centered

        center_x_offset = x_spacing * (x_count - 1) / 2 if centered[0] else 0
        center_y_offset = y_spacing * (y_count - 1) / 2 if centered[1] else 0

        self.locations = []
        self.planes = []
        for plane in WorkplaneList._get_context().workplanes:
            for i, j in product(range(x_count), range(y_count)):
                self.locations.append(
                    Location(plane)
                    * Location(
                        Vector(
                            i * x_spacing - center_x_offset,
                            j * y_spacing - center_y_offset,
                        )
                    )
                )
                self.planes.append(plane)
        super().__init__(self.locations, self.planes)


class WorkplaneList:

    """Context variable used to link to WorkplaneList instance"""

    _current: contextvars.ContextVar["WorkplaneList"] = contextvars.ContextVar(
        "WorkplaneList._current"
    )

    def __init__(self, planes: list[Plane]):
        self._reset_tok = None
        self.workplanes = planes
        self.point_generator = None

    def __enter__(self):
        """Upon entering create a token to restore contextvars"""
        self._reset_tok = self._current.set(self)
        self.point_generator = Locations((0, 0, 0)).__enter__()
        logger.info(
            "%s is pushing %d workplanes", type(self).__name__, len(self.workplanes)
        )
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context"""
        self._current.reset(self._reset_tok)
        self.point_generator.__exit__(None, None, None)
        logger.info(
            "%s is popping %d workplanes", type(self).__name__, len(self.workplanes)
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

    def __init__(self, *objs: Union[Face, PlaneLike, Location]):
        self.workplanes = []
        for obj in objs:
            if isinstance(obj, Plane):
                self.workplanes.append(obj)
            elif isinstance(obj, Location):
                plane_face = Face.makePlane(1, 1).move(obj)
                self.workplanes.append(
                    Plane(
                        origin=plane_face.Center(),
                        normal=plane_face.normalAt(plane_face.Center()),
                    )
                )
            elif isinstance(obj, str):
                self.workplanes.append(Plane.named(obj))
            elif isinstance(obj, Face):
                self.workplanes.append(
                    Plane(origin=obj.Center(), normal=obj.normalAt(obj.Center()))
                )
            else:
                raise ValueError(f"Workplanes does not accept {type(obj)}")
        super().__init__(self.workplanes)
