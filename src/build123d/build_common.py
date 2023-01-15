"""
build123d Common

name: build_common.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build 3D parts.

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
from abc import ABC, abstractmethod, abstractstaticmethod
from math import sqrt, pi
from typing import Iterable, Union
import logging
from build123d.build_enums import (
    Select,
    Kind,
    Keep,
    Mode,
    Transition,
    FontStyle,
    Halign,
    Valign,
    Until,
    SortBy,
    GeomType,
)

from build123d.direct_api import (
    Axis,
    Edge,
    Wire,
    Vector,
    VectorLike,
    Location,
    Face,
    Solid,
    Compound,
    Shape,
    Vertex,
    Plane,
    Shell,
    ShapeList,
)

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

#
# CONSTANTS
#
MM = 1
CM = 10 * MM
M = 1000 * MM
IN = 25.4 * MM
FT = 12 * IN


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

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.mode = mode
        self.workplanes = workplanes
        self._reset_tok = None
        self._parent = None
        self.last_vertices = []
        self.last_edges = []
        self.workplanes_context = None
        self.active: bool = False  # is the builder context active
        self.exit_workplanes = None

    def __enter__(self):
        """Upon entering record the parent and a token to restore contextvars"""

        self._parent = Builder._get_context()
        self._reset_tok = self._current.set(self)
        # If there are no workplanes, create a default XY plane
        if not self.workplanes and not WorkplaneList._get_context():
            self.workplanes_context = Workplanes(Plane.XY).__enter__()
        elif self.workplanes:
            self.workplanes_context = Workplanes(*self.workplanes).__enter__()

        self.active = True
        logger.info("Entering %s with mode=%s", type(self).__name__, self.mode)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)

        if self._parent is not None:
            logger.debug("Transferring object(s) to %s", type(self._parent).__name__)
            if isinstance(self._obj, Iterable):
                self._parent._add_to_context(*self._obj, mode=self.mode)
            else:
                self._parent._add_to_context(self._obj, mode=self.mode)

        self.exit_workplanes = WorkplaneList._get_context().workplanes

        # Now that the object has been transferred, it's save to remove any (non-default)
        # workplanes that were created then exit
        if self.workplanes:
            self.workplanes_context.__exit__(None, None, None)

        self.active = False

        logger.info("Exiting %s", type(self).__name__)

    @abstractstaticmethod
    def _tag() -> str:
        """Class (possibly subclass) name"""
        return NotImplementedError  # pragma: no cover

    @abstractmethod
    def _obj(self) -> Shape:
        """Object to pass to parent"""
        return NotImplementedError  # pragma: no cover

    @abstractmethod
    def _obj_name(self) -> str:
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
    def _get_context(cls, caller=None):
        """Return the instance of the current builder

        Note: each derived class can override this class to return the class
        type to keep IDEs happy. In Python 3.11 the return type should be set to Self
        here to avoid having to recreate this method.
        """
        result = cls._current.get(None)
        if caller is not None and result is None:
            if hasattr(caller, "_applies_to"):
                raise RuntimeError(
                    f"No valid context found, use one of {caller._applies_to}"
                )
            else:
                raise RuntimeError(f"No valid context found")

        return result

    def vertices(self, select: Select = Select.ALL) -> ShapeList[Vertex]:
        """Return Vertices

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            VertexList[Vertex]: Vertices extracted
        """
        vertex_list = []
        if select == Select.ALL:
            for edge in self._obj.edges():
                vertex_list.extend(edge.vertices())
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return ShapeList(set(vertex_list))

    def edges(self, select: Select = Select.ALL) -> ShapeList[Edge]:
        """Return Edges

        Return either all or the edges created during the last operation.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: Edges extracted
        """
        if select == Select.ALL:
            edge_list = self._obj.edges()
        elif select == Select.LAST:
            edge_list = self.last_edges
        return ShapeList(edge_list)

    def wires(self, select: Select = Select.ALL) -> ShapeList[Wire]:
        """Return Wires

        Return either all or the wires created during the last operation.

        Args:
            select (Select, optional): Wire selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Wire]: Wires extracted
        """
        if select == Select.ALL:
            wire_list = self._obj.wires()
        elif select == Select.LAST:
            wire_list = Wire.combine(self.last_edges)
        return ShapeList(wire_list)

    def faces(self, select: Select = Select.ALL) -> ShapeList[Face]:
        """Return Faces

        Return either all or the faces created during the last operation.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Face]: Faces extracted
        """
        if select == Select.ALL:
            face_list = self._obj.faces()
        elif select == Select.LAST:
            face_list = self.last_faces
        return ShapeList(face_list)

    def validate_inputs(self, validating_class, objects: Shape = None):
        """Validate that objects/operations and parameters apply"""

        if not objects:
            objects = []

        if not self._tag() in validating_class._applies_to:
            raise RuntimeError(
                f"{self.__class__.__name__} doesn't have a "
                f"{validating_class.__class__.__name__} object or operation "
                f"({validating_class.__class__.__name__} applies to {validating_class._applies_to})"
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


class LocationList:
    """Location Context

    A stateful context of active locations. At least one must be active
    at all time. Note that local locations are stored and global locations
    are returned as a property of the local locations and the currently
    active workplanes.

    Args:
        locations (list[Location]): list of locations to add to the context

    """

    # Context variable used to link to LocationList instance
    _current: contextvars.ContextVar["LocationList"] = contextvars.ContextVar(
        "ContextList._current"
    )

    @property
    def locations(self) -> list[Location]:
        """Current local locations globalized with current workplanes"""
        global_locations = [
            plane.to_location() * local_location
            for plane in WorkplaneList._get_context().workplanes
            for local_location in self.local_locations
        ]
        return global_locations

    def __init__(self, locations: list[Location]):
        self._reset_tok = None
        self.local_locations = locations
        self.location_index = 0
        self.plane_index = 0

    def __enter__(self):
        """Upon entering create a token to restore contextvars"""
        self._reset_tok = self._current.set(self)
        logger.info(
            "%s is pushing %d points: %s",
            type(self).__name__,
            len(self.local_locations),
            self.local_locations,
        )
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context"""
        self._current.reset(self._reset_tok)
        logger.info(
            "%s is popping %d points", type(self).__name__, len(self.local_locations)
        )

    def __iter__(self):
        """Initialize to beginning"""
        self.location_index = 0
        return self

    def __next__(self):
        """While not through all the locations, return the next one"""
        if self.location_index < len(self.locations):
            result = self.locations[self.location_index]
            self.location_index += 1
            return result
        else:
            raise StopIteration

    @classmethod
    def _get_context(cls):
        """Return the instance of the current LocationList"""
        return cls._current.get(None)


class HexLocations(LocationList):
    """Location Context: Hex Array

    Creates a context of hexagon array of points.

    Args:
        diagonal: tip to tip size of hexagon ( must be > 0)
        xCount: number of points ( > 0 )
        yCount: number of points ( > 0 )
        centered: specify centering along each axis.
        offset (VectorLike): offset to apply to all locations. Defaults to (0,0).

    Raises:
        ValueError: Spacing and count must be > 0
    """

    def __init__(
        self,
        diagonal: float,
        x_count: int,
        y_count: int,
        centered: tuple[bool, bool] = (True, True),
        offset: VectorLike = (0, 0),
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
        offset = Vector(offset)
        if centered[0]:
            offset += Vector(-x_spacing * (x_count - 1) * 0.5, 0)
        if centered[1]:
            offset += Vector(0, -y_spacing * y_count * 0.5)
        points = [x + offset for x in points]

        # convert to locations and store the reference plane
        local_locations = [Location(point) for point in points]

        self.local_locations = Locations._move_to_existing(local_locations)

        super().__init__(self.local_locations)

    @staticmethod
    def calc_diagonal(radius: float, spacing: float) -> float:
        """Calculate the size of the hex grid filled with circles at the given spacing"""
        return 2 * (2 * radius + spacing) / sqrt(3)


class PolarLocations(LocationList):
    """Location Context: Polar Array

    Push a polar array of locations to Part or Sketch

    Args:
        radius (float): array radius
        count (int): Number of points to push
        start_angle (float, optional): angle to first point from +ve X axis. Defaults to 0.0.
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
        local_locations = []
        for i in range(count):
            local_locations.append(
                Location(
                    Vector(radius, 0).rotate(Axis.Z, start_angle + angle_step * i),
                    Vector(0, 0, 1),
                    rotate * angle_step * i,
                )
            )

        self.local_locations = Locations._move_to_existing(local_locations)

        super().__init__(self.local_locations)


class Locations(LocationList):
    """Location Context: Push Points

    Push sequence of locations to Part or Sketch

    Args:
        pts (Union[VectorLike, Vertex, Location]): sequence of points to push
    """

    def __init__(self, *pts: Union[VectorLike, Vertex, Location]):
        local_locations = []
        for point in pts:
            if isinstance(point, Location):
                local_locations.append(point)
            elif isinstance(point, Vector):
                local_locations.append(Location(point))
            elif isinstance(point, Vertex):
                local_locations.append(Location(Vector(point.to_tuple())))
            elif isinstance(point, tuple):
                local_locations.append(Location(Vector(point)))
            else:
                raise ValueError(f"Locations doesn't accept type {type(point)}")

        self.local_locations = Locations._move_to_existing(local_locations)
        super().__init__(self.local_locations)

    @staticmethod
    def _move_to_existing(local_locations: list[Location]) -> list[Location]:
        """_move_to_existing

        Move as a group the local locations to any existing locations  Note that existing
        polar locations may be rotated so this rotates the group not the individuals.

        Args:
            local_locations (list[Location]): location group to move to existing locations

        Returns:
            list[Location]: group of locations moved to existing locations as a group
        """
        local_vertex_compound = Compound.make_compound(
            [Face.make_rect(1, 1).locate(l) for l in local_locations]
        )
        location_group = []
        if LocationList._get_context():
            for group_center in LocationList._get_context().local_locations:
                location_group.extend(
                    [
                        v.location
                        for v in local_vertex_compound.moved(group_center).faces()
                    ]
                )
        else:
            location_group = local_locations
        return location_group


class GridLocations(LocationList):
    """Location Context: Rectangular Array

    Push a rectangular array of locations to Part or Sketch

    Args:
        x_spacing (float): horizontal spacing
        y_spacing (float): vertical spacing
        x_count (int): number of horizontal points
        y_count (int): number of vertical points
        centered: specify centering along each axis.
        offset (VectorLike): offset to apply to all locations. Defaults to (0,0).

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
        offset: VectorLike = (0, 0),
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
        self.offset = Vector(offset)

        center_x_offset = (
            x_spacing * (x_count - 1) / 2 if centered[0] else 0 + self.offset.X
        )
        center_y_offset = (
            y_spacing * (y_count - 1) / 2 if centered[1] else 0 + self.offset.Y
        )

        # Create the list of local locations
        local_locations = []
        for i, j in product(range(x_count), range(y_count)):
            local_locations.append(
                Location(
                    Vector(
                        i * x_spacing - center_x_offset,
                        j * y_spacing - center_y_offset,
                    )
                )
            )

        self.local_locations = Locations._move_to_existing(local_locations)
        self.planes = []
        super().__init__(self.local_locations)


class WorkplaneList:
    """Workplane Context

    A stateful context of active workplanes. At least one must be active
    at all time.

    Args:
        planes (list[Plane]): list of planes

    """

    # Context variable used to link to WorkplaneList instance
    _current: contextvars.ContextVar["WorkplaneList"] = contextvars.ContextVar(
        "WorkplaneList._current"
    )

    def __init__(self, planes: list[Plane]):
        self._reset_tok = None
        self.workplanes = planes
        self.locations_context = None
        self.plane_index = 0

    def __enter__(self):
        """Upon entering create a token to restore contextvars"""
        self._reset_tok = self._current.set(self)
        self.locations_context = Locations((0, 0, 0)).__enter__()
        logger.info(
            "%s is pushing %d workplanes: %s",
            type(self).__name__,
            len(self.workplanes),
            self.workplanes,
        )
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context"""
        self._current.reset(self._reset_tok)
        self.locations_context.__exit__(None, None, None)
        logger.info(
            "%s is popping %d workplanes", type(self).__name__, len(self.workplanes)
        )

    def __iter__(self):
        """Initialize to beginning"""
        self.plane_index = 0
        return self

    def __next__(self):
        """While not through all the workplanes, return the next one"""
        if self.plane_index < len(self.workplanes):
            result = self.workplanes[self.plane_index]
            self.plane_index += 1
            return result
        else:
            raise StopIteration

    @classmethod
    def _get_context(cls):
        """Return the instance of the current ContextList"""
        return cls._current.get(None)


class Workplanes(WorkplaneList):
    """Workplane Context: Workplanes

    Create workplanes from the given sequence of planes.

    Args:
        objs (Union[Face, Plane, Location]): sequence of faces, planes, or
            locations to use to define workplanes.
    Raises:
        ValueError: invalid input
    """

    def __init__(self, *objs: Union[Face, Plane, Location]):
        self.workplanes = []
        for obj in objs:
            if isinstance(obj, Plane):
                self.workplanes.append(obj)
            elif isinstance(obj, (Location, Face)):
                self.workplanes.append(Plane(obj))
            else:
                raise ValueError(f"Workplanes does not accept {type(obj)}")
        super().__init__(self.workplanes)
