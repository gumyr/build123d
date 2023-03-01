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
import inspect
import contextvars
from itertools import product
from abc import ABC, abstractmethod
from math import sqrt
from typing import Iterable, Union
import logging
from build123d.build_enums import (
    Align,
    Select,
    Mode,
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
THOU = IN / 1000


class Builder(ABC):
    """Builder

    Base class for the build123d Builders.

    Args:
        workplanes: sequence of Union[Face, Plane, Location]: set plane(s) to work on
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
        self._python_frame = inspect.currentframe().f_back.f_back
        self.builder_parent = None
        self.last_vertices: ShapeList[Vertex] = ShapeList()
        self.last_edges: ShapeList[Edge] = ShapeList()
        self.last_faces: ShapeList[Face] = ShapeList()
        self.last_solids: ShapeList[Solid] = ShapeList()
        self.workplanes_context = None
        self.exit_workplanes = None

    def __enter__(self):
        """Upon entering record the parent and a token to restore contextvars"""

        # Only set parents from the same scope. Note inspect.currentframe() is supported
        # by CPython in Linux, Window & MacOS but may not be supported in other python
        # implementations.  Support outside of these OS's is outside the scope of this
        # project.
        same_scope = (
            Builder._get_context()._python_frame == inspect.currentframe().f_back
            if Builder._get_context()
            else False
        )

        if same_scope:
            self.builder_parent = Builder._get_context()
        else:
            self.builder_parent = None
            self.workplanes = self.workplanes if self.workplanes else [Plane.XY]

        self._reset_tok = self._current.set(self)

        logger.info(
            "Entering %s with mode=%s which is in %s scope as parent",
            type(self).__name__,
            self.mode,
            "same" if same_scope else "different",
        )

        # If there are no workplanes, create a default XY plane
        if not self.workplanes and not WorkplaneList._get_context():
            self.workplanes_context = Workplanes(Plane.XY).__enter__()
        elif self.workplanes:
            self.workplanes_context = Workplanes(*self.workplanes).__enter__()

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)

        if self.builder_parent is not None and self.mode != Mode.PRIVATE:
            logger.debug(
                "Transferring object(s) to %s", type(self.builder_parent).__name__
            )
            self.builder_parent._add_to_context(self._obj, mode=self.mode)

        self.exit_workplanes = WorkplaneList._get_context().workplanes

        # Now that the object has been transferred, it's save to remove any (non-default)
        # workplanes that were created then exit
        if self.workplanes:
            self.workplanes_context.__exit__(None, None, None)

        logger.info("Exiting %s", type(self).__name__)

    @staticmethod
    @abstractmethod
    def _tag() -> str:
        """Class (possibly subclass) name"""
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def _obj(self) -> Shape:
        """Object to pass to parent"""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def _obj_name(self) -> str:
        """Name of object to pass to parent"""
        raise NotImplementedError  # pragma: no cover

    @property
    def max_dimension(self) -> float:
        """Maximum size of object in all directions"""
        return self._obj.bounding_box().diagonal if self._obj else 0.0

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

        logger.info(
            "Context requested by %s",
            type(inspect.currentframe().f_back.f_locals["self"]).__name__,
        )

        if caller is not None and result is None:
            if hasattr(caller, "_applies_to"):
                raise RuntimeError(
                    f"No valid context found, use one of {caller._applies_to}"
                )
            raise RuntimeError("No valid context found-common")

        return result

    def vertices(self, select: Select = Select.ALL) -> ShapeList[Vertex]:
        """Return Vertices

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            VertexList[Vertex]: Vertices extracted
        """
        vertex_list: list[Vertex] = []
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

    def solids(self, select: Select = Select.ALL) -> ShapeList[Solid]:
        """Return Solids

        Return either all or the solids created during the last operation.

        Args:
            select (Select, optional): Solid selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Solid]: Solids extracted
        """
        if select == Select.ALL:
            solid_list = self._obj.solids()
        elif select == Select.LAST:
            solid_list = self.last_solids
        return ShapeList(solid_list)

    def validate_inputs(self, validating_class, objects: Iterable[Shape] = None):
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
        if self.location_index >= len(self.locations):
            raise StopIteration
        result = self.locations[self.location_index]
        self.location_index += 1
        return result

    @classmethod
    def _get_context(cls):
        """Return the instance of the current LocationList"""
        return cls._current.get(None)


class HexLocations(LocationList):
    """Location Context: Hex Array

    Creates a context of hexagon array of locations for Part or Sketch. When creating
    hex locations for an array of circles, set `apothem` to the radius of the circle
    plus one half the spacing between the circles.

    Args:
        apothem: radius of the inscribed circle
        xCount: number of points ( > 0 )
        yCount: number of points ( > 0 )
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).

    Raises:
        ValueError: Spacing and count must be > 0
    """

    def __init__(
        self,
        apothem: float,
        x_count: int,
        y_count: int,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
    ):
        diagonal = 4 * apothem / sqrt(3)
        x_spacing = 3 * diagonal / 4
        y_spacing = diagonal * sqrt(3) / 2
        if x_spacing <= 0 or y_spacing <= 0 or x_count < 1 or y_count < 1:
            raise ValueError("Spacing and count must be > 0 ")

        self.apothem = apothem
        self.diagonal = diagonal
        self.x_count = x_count
        self.y_count = y_count
        self.align = align

        # Generate the raw coordinates relative to bottom left point
        points = ShapeList[Vector]()
        for x_val in range(0, x_count, 2):
            for y_val in range(y_count):
                points.append(
                    Vector(x_spacing * x_val, y_spacing * y_val + y_spacing / 2)
                )
        for x_val in range(1, x_count, 2):
            for y_val in range(y_count):
                points.append(Vector(x_spacing * x_val, y_spacing * y_val + y_spacing))

        # Determine the minimum point and size of the array
        sorted_points = [points.sort_by(Axis.X), points.sort_by(Axis.Y)]
        # pylint: disable=no-member
        size = [
            sorted_points[0][-1].X - sorted_points[0][0].X,
            sorted_points[1][-1].Y - sorted_points[1][0].Y,
        ]
        min_corner = Vector(sorted_points[0][0].X, sorted_points[1][0].Y)

        # Calculate the amount to offset the array to align it
        align_offset = []
        for i in range(2):
            if align[i] == Align.MIN:
                align_offset.append(0)
            elif align[i] == Align.CENTER:
                align_offset.append(-size[i] / 2)
            elif align[i] == Align.MAX:
                align_offset.append(-size[i])

        # Align the points
        points = ShapeList(
            [point + Vector(*align_offset) - min_corner for point in points]
        )

        # Convert to locations and store the reference plane
        local_locations = [Location(point) for point in points]

        self.local_locations = Locations._move_to_existing(local_locations)

        super().__init__(self.local_locations)


class PolarLocations(LocationList):
    """Location Context: Polar Array

    Creates a context of polar array of locations for Part or Sketch

    Args:
        radius (float): array radius
        count (int): Number of points to push
        start_angle (float, optional): angle to first point from +ve X axis. Defaults to 0.0.
        angular_range (float, optional): magnitude of array from start angle. Defaults to 360.0.
        rotate (bool, optional): Align locations with arc tangents. Defaults to True.

    Raises:
        ValueError: Count must be greater than or equal to 1
    """

    def __init__(
        self,
        radius: float,
        count: int,
        start_angle: float = 0.0,
        angular_range: float = 360.0,
        rotate: bool = True,
    ):
        if count < 1:
            raise ValueError(f"At least 1 elements required, requested {count}")

        angle_step = angular_range / count

        # Note: rotate==False==0 so the location orientation doesn't change
        local_locations = []
        for i in range(count):
            local_locations.append(
                Location(
                    Vector(radius, 0).rotate(Axis.Z, start_angle + angle_step * i),
                    Vector(0, 0, 1),
                    rotate * (angle_step * i + start_angle),
                )
            )

        self.local_locations = Locations._move_to_existing(local_locations)

        super().__init__(self.local_locations)


class Locations(LocationList):
    """Location Context: Push Points

    Creates a context of locations for Part or Sketch

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
        location_group = []
        if LocationList._get_context():
            local_vertex_compound = Compound.make_compound(
                [Face.make_rect(1, 1).locate(l) for l in local_locations]
            )
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

    Creates a context of rectangular array of locations for Part or Sketch

    Args:
        x_spacing (float): horizontal spacing
        y_spacing (float): vertical spacing
        x_count (int): number of horizontal points
        y_count (int): number of vertical points
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).

    Raises:
        ValueError: Either x or y count must be greater than or equal to one.
    """

    def __init__(
        self,
        x_spacing: float,
        y_spacing: float,
        x_count: int,
        y_count: int,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
    ):
        if x_count < 1 or y_count < 1:
            raise ValueError(
                f"At least 1 elements required, requested {x_count}, {y_count}"
            )
        self.x_spacing = x_spacing
        self.y_spacing = y_spacing
        self.x_count = x_count
        self.y_count = y_count
        self.align = align

        size = [x_spacing * (x_count - 1), y_spacing * (y_count - 1)]
        align_offset = []
        for i in range(2):
            if align[i] == Align.MIN:
                align_offset.append(0.0)
            elif align[i] == Align.CENTER:
                align_offset.append(-size[i] / 2)
            elif align[i] == Align.MAX:
                align_offset.append(-size[i])

        # Create the list of local locations
        local_locations = []
        for i, j in product(range(x_count), range(y_count)):
            local_locations.append(
                Location(
                    Vector(
                        i * x_spacing + align_offset[0],
                        j * y_spacing + align_offset[1],
                    )
                )
            )

        self.local_locations = Locations._move_to_existing(local_locations)
        self.planes: list[Plane] = []
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
        logger.info(
            "%s is pushing %d workplanes: %s",
            type(self).__name__,
            len(self.workplanes),
            self.workplanes,
        )
        self.locations_context = LocationList([Location(Vector())]).__enter__()
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
        if self.plane_index >= len(self.workplanes):
            raise StopIteration
        result = self.workplanes[self.plane_index]
        self.plane_index += 1
        return result

    @classmethod
    def _get_context(cls):
        """Return the instance of the current ContextList"""
        return cls._current.get(None)

    @classmethod
    def localize(cls, *points: VectorLike) -> Union[list[Vector], Vector]:
        """Localize a sequence of points to the active workplane
        (only used by BuildLine where there is only one active workplane)

        The return value is conditional:
        - 1 point -> Vector
        - >1 points -> list[Vector]
        """
        points_per_workplane = []
        workplane = WorkplaneList._get_context().workplanes[0]
        localized_pts = [
            workplane.from_local_coords(pt) if isinstance(pt, tuple) else pt
            for pt in points
        ]
        if len(localized_pts) == 1:
            points_per_workplane.append(localized_pts[0])
        else:
            points_per_workplane.extend(localized_pts)

        if len(points_per_workplane) == 1:
            result = points_per_workplane[0]
        else:
            result = points_per_workplane
        return result


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


#
# To avoid import loops, Vector add & sub are monkey-patched
def _vector_add(self: Vector, vec: VectorLike) -> Vector:
    """Mathematical addition function where tuples are localized if workplane exists"""
    if isinstance(vec, Vector):
        result = Vector(self.wrapped.Added(vec.wrapped))
    elif isinstance(vec, tuple) and WorkplaneList._get_context():
        result = Vector(self.wrapped.Added(WorkplaneList.localize(vec).wrapped))  # type: ignore[union-attr]
    elif isinstance(vec, tuple):
        result = Vector(self.wrapped.Added(Vector(vec).wrapped))
    else:
        raise ValueError("Only Vectors or tuples can be added to Vectors")

    return result


def _vector_sub(self: Vector, vec: VectorLike) -> Vector:
    """Mathematical subtraction function where tuples are localized if workplane exists"""
    if isinstance(vec, Vector):
        result = Vector(self.wrapped.Subtracted(vec.wrapped))
    elif isinstance(vec, tuple) and WorkplaneList._get_context():
        result = Vector(self.wrapped.Subtracted(WorkplaneList.localize(vec).wrapped))  # type: ignore[union-attr]
    elif isinstance(vec, tuple):
        result = Vector(self.wrapped.Subtracted(Vector(vec).wrapped))
    else:
        raise ValueError("Only Vectors or tuples can be subtracted from Vectors")

    return result


Vector.add = _vector_add  # type: ignore[assignment]
Vector.sub = _vector_sub  # type: ignore[assignment]
