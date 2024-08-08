"""
build123d Common

name: build_common.py
by:   Gumyr
date: July 12th 2022

desc:
    This is a Python code defining a class hierarchy for building CAD
    models. The code defines an abstract base class Builder with three
    concrete subclasses BuildLine, BuildPart, and BuildSketch in separate
    modules.

    The Builder class has several methods for adding and retrieving
    geometric shapes such as vertices, edges, faces, and solids. It also
    has a method _add_to_pending for adding shapes to a pending list that
    will be integrated into the final model later. The class has a
    _get_context method for retrieving the current Builder instance and a
    validate_inputs method for validating input shapes.

    The code also defines a validate_inputs function that takes a Builder
    instance and validates the input shapes.

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
import inspect
import logging
import sys
import warnings
import functools
from abc import ABC, abstractmethod
from itertools import product
from math import sqrt, cos, pi
from typing import Any, Callable, Iterable, Optional, Union, TypeVar
from typing_extensions import Self, ParamSpec, Concatenate

from build123d.build_enums import Align, Mode, Select, Unit
from build123d.geometry import Axis, Location, Plane, Vector, VectorLike
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    Part,
    Shape,
    ShapeList,
    Sketch,
    Solid,
    Vertex,
    Wire,
    tuplify,
    new_edges,
)

# pylint: disable=too-many-lines

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

# LENGTH CONSTANTS
MC = 0.001
MM = 1
CM = 10 * MM
M = 1000 * MM
IN = 25.4 * MM
FT = 12 * IN
THOU = IN / 1000

# UNIT CONVERSIONS
UNITS_PER_METER = {
    Unit.IN: M / IN,
    Unit.FT: M / FT,
    Unit.MC: M / MC,
    Unit.MM: M / MM,
    Unit.CM: M / CM,
    Unit.M: 1,
}

# MASS CONSTANTS
G = 1
KG = 1000 * G
LB = 453.59237 * G


def _is_point(obj):
    """Identify points as tuples of numbers"""
    return isinstance(obj, tuple) and all(
        isinstance(item, (int, float)) for item in obj
    )


T = TypeVar("T", Any, list[Any])


def flatten_sequence(*obj: T) -> list[Any]:
    """Convert a sequence of object potentially containing iterables into a flat list"""

    flat_list = []
    for item in obj:
        # Note: an Iterable can't be used here as it will match with Vector & Vertex
        # and break them into a list of floats.
        if isinstance(item, (list, tuple, filter, set)) and not _is_point(item):
            flat_list.extend(flatten_sequence(*item))
        else:
            flat_list.append(item)

    return flat_list


operations_apply_to = {
    "add": ["BuildPart", "BuildSketch", "BuildLine"],
    "bounding_box": ["BuildPart", "BuildSketch", "BuildLine"],
    "chamfer": ["BuildPart", "BuildSketch", "BuildLine"],
    "extrude": ["BuildPart"],
    "fillet": ["BuildPart", "BuildSketch", "BuildLine"],
    "full_round": ["BuildSketch"],
    "loft": ["BuildPart"],
    "make_brake_formed": ["BuildPart"],
    "make_face": ["BuildSketch"],
    "make_hull": ["BuildSketch"],
    "mirror": ["BuildPart", "BuildSketch", "BuildLine"],
    "offset": ["BuildPart", "BuildSketch", "BuildLine"],
    "project": ["BuildPart", "BuildSketch", "BuildLine"],
    "project_workplane": ["BuildPart"],
    "revolve": ["BuildPart"],
    "scale": ["BuildPart", "BuildSketch", "BuildLine"],
    "section": ["BuildPart"],
    "split": ["BuildPart", "BuildSketch", "BuildLine"],
    "sweep": ["BuildPart", "BuildSketch"],
    "thicken": ["BuildPart"],
}


class Builder(ABC):
    """Builder

    Base class for the build123d Builders.

    Args:
        workplanes: sequence of Union[Face, Plane, Location]: set plane(s) to work on
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Attributes:
        mode (Mode): builder's combination mode
        workplanes (list[Plane]): active workplanes
        builder_parent (Builder): build to pass objects to on exit

    """

    # pylint: disable=too-many-instance-attributes

    # Context variable used to by Objects and Operations to link to current builder instance
    _current: contextvars.ContextVar["Builder"] = contextvars.ContextVar(
        "Builder._current"
    )

    # Abstract class variables
    _tag = "Builder"
    _obj_name = "None"
    _shape = None
    _sub_class = None

    @property
    @abstractmethod
    def _obj(self) -> Shape:
        """Object to pass to parent"""
        raise NotImplementedError  # pragma: no cover

    @property
    def max_dimension(self) -> float:
        """Maximum size of object in all directions"""
        return self._obj.bounding_box().diagonal if self._obj else 0.0

    @property
    def new_edges(self) -> ShapeList[Edge]:
        """Edges that changed during last operation"""
        before_list = [] if self.obj_before is None else [self.obj_before]
        return new_edges(*(before_list + self.to_combine), combined=self._obj)

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.mode = mode
        planes = WorkplaneList._convert_to_planes(workplanes)
        self.workplanes = planes if planes else [Plane.XY]
        self._reset_tok = None
        current_frame = inspect.currentframe()
        assert current_frame is not None
        assert current_frame.f_back is not None
        self._python_frame = current_frame.f_back.f_back
        self.builder_parent = None
        self.lasts: dict = {Vertex: [], Edge: [], Face: [], Solid: []}
        self.workplanes_context = None
        self.exit_workplanes = None
        self.obj_before: Optional[Shape] = None
        self.to_combine: list[Shape] = []

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

        self._reset_tok = self._current.set(self)

        logger.info(
            "Entering %s with mode=%s which is in %s scope as parent",
            type(self).__name__,
            self.mode,
            "same" if same_scope else "different",
        )

        # If there are no workplanes, create a default XY plane
        if self.workplanes:
            self.workplanes_context = WorkplaneList(*self.workplanes).__enter__()
        else:
            self.workplanes_context = WorkplaneList(Plane.XY).__enter__()

        return self

    def _exit_extras(self):
        """Any builder specific exit actions"""

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)

        self._exit_extras()  # custom builder exit code

        if self.builder_parent is not None and self.mode != Mode.PRIVATE:
            logger.debug(
                "Transferring object(s) to %s", type(self.builder_parent).__name__
            )
            if self._obj is None and not sys.exc_info()[1]:
                raise RuntimeError(
                    f"{self._obj_name} is None - {self._tag} didn't create anything"
                )
            self.builder_parent._add_to_context(self._obj, mode=self.mode)

        self.exit_workplanes = WorkplaneList._get_context().workplanes

        # Now that the object has been transferred, it's save to remove any (non-default)
        # workplanes that were created then exit
        if self.workplanes:
            self.workplanes_context.__exit__(None, None, None)

        logger.info("Exiting %s", type(self).__name__)

    @abstractmethod
    def _add_to_pending(self, *objects: Union[Edge, Face], face_plane: Plane = None):
        """Integrate a sequence of objects into existing builder object"""
        return NotImplementedError  # pragma: no cover

    @classmethod
    def _get_context(cls, caller: Union[Builder, str] = None, log: bool = True) -> Self:
        """Return the instance of the current builder"""
        result = cls._current.get(None)
        context_name = "None" if result is None else type(result).__name__

        if log:
            if isinstance(caller, (Part, Sketch, Curve, Wire)):
                caller_name = caller.__class__.__name__
            elif isinstance(caller, str):
                caller_name = caller
            else:
                caller_name = "None"
            logger.info("%s context requested by %s", context_name, caller_name)

        return result

    def _add_to_context(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        faces_to_pending: bool = True,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        """Add objects to Builder instance

        Core method to interface with Builder instance. Input sequence of objects is
        parsed into lists of edges, faces, and solids. Edges and faces are added to pending
        lists. Solids are combined with current part.

        Each operation generates a list of vertices, edges, faces, and solids that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of objects to add
            faces_to_pending (bool, optional): add faces to pending_faces. Default to True.
            clean (bool, optional): Remove extraneous internal structure. Defaults to True.
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Raises:
            ValueError: Invalid input
            ValueError: Nothing to intersect with
            ValueError: Nothing to intersect with
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements

        self.obj_before = self._obj
        self.to_combine = list(objects)
        if mode != Mode.PRIVATE and len(objects) > 0:
            # Categorize the input objects by type
            typed = {}
            for cls in [Edge, Wire, Face, Solid, Compound]:
                typed[cls] = [obj for obj in objects if isinstance(obj, cls)]

            # Check for invalid inputs
            num_stored = sum(len(t) for t in typed.values())
            # Generate an exception if not processing exceptions
            if len(objects) != num_stored and not sys.exc_info()[1]:
                unsupported = set(objects) - set(v for l in typed.values() for v in l)
                raise ValueError(f"{self._tag} doesn't accept {unsupported}")

            # Extract base objects from Compounds
            compound: Compound
            for compound in typed[Compound]:
                for obj_types in [Edge, Wire, Face, Solid]:
                    typed[obj_types].extend(compound.get_type(obj_types))

            # Align sketch planar faces with Plane.XY
            if self._tag == "BuildSketch":
                aligned = []
                new_face: Face
                for new_face in typed[Face]:
                    if not new_face.is_coplanar(Plane.XY):
                        # Try to keep the x direction, if not allow it to be assigned automatically
                        try:
                            plane = Plane(
                                origin=(0, 0, 0),
                                x_dir=(1, 0, 0),
                                z_dir=new_face.normal_at(),
                            )
                        except:
                            plane = Plane(origin=(0, 0, 0), z_dir=new_face.normal_at())

                        new_face = plane.to_local_coords(new_face)
                        new_face.move(Location((0, 0, -new_face.center().Z)))
                    if new_face.normal_at().Z > 0:  # Flip the face if up-side-down
                        aligned.append(new_face)
                    else:
                        aligned.append(-new_face)
                typed[Face] = aligned

            # Convert wires to edges
            new_wire: Wire
            for new_wire in typed[Wire]:
                typed[Edge].extend(new_wire.edges())

            # Allow faces to be combined with solids for section operations
            if not faces_to_pending:
                typed[Solid].extend(typed[Face])
                typed[Face] = []

            # Store the objects pre integration
            pre = {}
            for cls in [Vertex, Edge, Face, Solid]:
                pre[cls] = set() if self._obj is None else set(self._shapes(cls))

            if typed[self._shape]:
                logger.debug(
                    "Attempting to integrate %d object(s) into part with Mode=%s",
                    len(typed[self._shape]),
                    mode,
                )

                if mode == Mode.ADD:
                    if self._obj is None:
                        if len(typed[self._shape]) == 1:
                            self._obj = typed[self._shape][0]
                        else:
                            self._obj = (
                                typed[self._shape].pop().fuse(*typed[self._shape])
                            )
                    else:
                        self._obj = self._obj.fuse(*typed[self._shape])
                elif mode == Mode.SUBTRACT:
                    if self._obj is None:
                        raise RuntimeError("Nothing to subtract from")
                    self._obj = self._obj.cut(*typed[self._shape])
                elif mode == Mode.INTERSECT:
                    if self._obj is None:
                        raise RuntimeError("Nothing to intersect with")
                    self._obj = self._obj.intersect(*typed[self._shape])
                elif mode == Mode.REPLACE:
                    self._obj = Compound(list(typed[self._shape]))

                if self._obj is not None and clean:
                    self._obj = self._obj.clean()

                logger.info(
                    "Completed integrating %d object(s) into part with Mode=%s",
                    len(typed[self._shape]),
                    mode,
                )

            # Determine the last object
            # Note that when determining the Select.LAST values for the core shape type of a builder
            # the answer is just the categorized inputs to this method.  I.e.
            # Buildline.edges(Select.LAST) just returns the typed[Edge] values as that's what
            # just was added - no need for the set math.
            for cls in [Vertex, Edge, Face, Solid]:
                post = set() if self._obj is None else set(self._shapes(cls))
                self.lasts[cls] = (
                    ShapeList(typed[cls])
                    if self._shape == cls
                    else ShapeList(post - pre[cls])
                )

            # Cast to appropriate base types (Curve, Sketch or Part)
            # _sub_class is an abstract class variable assigned in the sub classes
            # pylint: disable=not-callable
            if self._obj is not None:
                if isinstance(self._obj, Compound):
                    self._obj = self._sub_class(self._obj.wrapped)
                else:
                    self._obj = self._sub_class(Compound(self._shapes()).wrapped)

            # Add to pending
            if self._tag == "BuildPart":
                self._add_to_pending(*typed[Edge])
                for plane in WorkplaneList._get_context().workplanes:
                    global_faces = [plane.from_local_coords(f) for f in typed[Face]]
                    self._add_to_pending(*global_faces, face_plane=plane)
            elif self._tag == "BuildSketch":
                self._add_to_pending(*typed[Edge])

    # Known pylint issue with Enums
    # pylint: disable=no-member
    def vertices(self, select: Select = Select.ALL) -> ShapeList[Vertex]:
        """Return Vertices

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Vertex]: Vertices extracted
        """
        vertex_list: list[Vertex] = []
        if select == Select.ALL:
            for obj_edge in self._obj.edges():
                vertex_list.extend(obj_edge.vertices())
        elif select == Select.LAST:
            vertex_list = self.lasts[Vertex]
        elif select == Select.NEW:
            raise ValueError("Select.NEW only valid for edges")
        else:
            raise ValueError(
                f"Invalid input, must be one of Select.{Select._member_names_}"
            )
        return ShapeList(set(vertex_list))

    def vertex(self, select: Select = Select.ALL) -> Vertex:
        """Return Vertex

        Return a vertex.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            Vertex: Vertex extracted
        """
        all_vertices = self.vertices(select)
        vertex_count = len(all_vertices)
        if vertex_count != 1:
            warnings.warn(f"Found {vertex_count} vertices, returning first")
        return all_vertices[0]

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
            edge_list = self.lasts[Edge]
        elif select == Select.NEW:
            edge_list = self.new_edges
        else:
            raise ValueError(
                f"Invalid input, must be one of Select.{Select._member_names_}"
            )
        return ShapeList(edge_list)

    def edge(self, select: Select = Select.ALL) -> Edge:
        """Return Edge

        Return an edge.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            Edge: Edge extracted
        """
        all_edges = self.edges(select)
        edge_count = len(all_edges)
        if edge_count != 1:
            warnings.warn(f"Found {edge_count} edges, returning first")
        return all_edges[0]

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
            wire_list = Wire.combine(self.lasts[Edge])
        elif select == Select.NEW:
            raise ValueError("Select.NEW only valid for edges")
        else:
            raise ValueError(
                f"Invalid input, must be one of Select.{Select._member_names_}"
            )
        return ShapeList(wire_list)

    def wire(self, select: Select = Select.ALL) -> Wire:
        """Return Wire

        Return a wire.

        Args:
            select (Select, optional): Wire selector. Defaults to Select.ALL.

        Returns:
            Wire: Wire extracted
        """
        all_wires = self.wires(select)
        wire_count = len(all_wires)
        if wire_count != 1:
            warnings.warn(f"Found {wire_count} wires, returning first")
        return all_wires[0]

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
            face_list = self.lasts[Face]
        elif select == Select.NEW:
            raise ValueError("Select.NEW only valid for edges")
        else:
            raise ValueError(
                f"Invalid input, must be one of Select.{Select._member_names_}"
            )
        return ShapeList(face_list)

    def face(self, select: Select = Select.ALL) -> Face:
        """Return Face

        Return a face.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            Face: Face extracted
        """
        all_faces = self.faces(select)
        face_count = len(all_faces)
        if face_count != 1:
            warnings.warn(f"Found {face_count} faces, returning first")
        return all_faces[0]

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
            solid_list = self.lasts[Solid]
        elif select == Select.NEW:
            raise ValueError("Select.NEW only valid for edges")
        else:
            raise ValueError(
                f"Invalid input, must be one of Select.{Select._member_names_}"
            )
        return ShapeList(solid_list)

    def solid(self, select: Select = Select.ALL) -> Solid:
        """Return Solid

        Return a solid.

        Args:
            select (Select, optional): Solid selector. Defaults to Select.ALL.

        Returns:
            Solid: Solid extracted
        """
        all_solids = self.solids(select)
        solid_count = len(all_solids)
        if solid_count != 1:
            warnings.warn(f"Found {solid_count} solids, returning first")
        return all_solids[0]

    def _shapes(self, obj_type: Union[Vertex, Edge, Face, Solid] = None) -> ShapeList:
        """Extract Shapes"""
        obj_type = self._shape if obj_type is None else obj_type
        if obj_type == Vertex:
            result = self._obj.vertices()
        elif obj_type == Edge:
            result = self._obj.edges()
        elif obj_type == Face:
            result = self._obj.faces()
        elif obj_type == Solid:
            result = self._obj.solids()
        else:
            result = None
        return result

    def validate_inputs(
        self, validating_class, objects: Union[Shape, Iterable[Shape]] = None
    ):
        """Validate that objects/operations and parameters apply"""

        if not objects:
            objects = []
        elif not isinstance(objects, Iterable):
            objects = [objects]

        if (
            isinstance(validating_class, (Part, Sketch, Curve, Wire))
            and self._tag not in validating_class._applies_to
        ):
            raise RuntimeError(
                f"{self.__class__.__name__} doesn't have a "
                f"{validating_class.__class__.__name__} object or operation "
                f"({validating_class.__class__.__name__} applies to {validating_class._applies_to})"
            )
        if (
            isinstance(validating_class, str)
            and self.__class__.__name__ not in operations_apply_to[validating_class]
        ):
            raise RuntimeError(
                f"({validating_class} doesn't apply to {operations_apply_to[validating_class]})"
            )
        # Check for valid object inputs
        for obj in objects:
            operation = (
                validating_class
                if isinstance(validating_class, str)
                else validating_class.__class__.__name__
            )
            if obj is None:
                pass
            elif not isinstance(obj, Shape):
                raise RuntimeError(
                    f"{operation} doesn't accept {type(obj).__name__},"
                    f" did you intend <keyword>={obj}?"
                )

    def _invalid_combine(self):
        """Raise an error for invalid boolean combine operations"""
        raise RuntimeError(
            f"{self.__class__.__name__} is a builder of Shapes and can't be "
            f"combined. The object being constructed is accessible via the "
            f"'{self._obj_name}' attribute."
        )

    def __add__(self, _other) -> Self:
        """Invalid add"""
        self._invalid_combine()

    def __sub__(self, _other) -> Self:
        """Invalid sub"""
        self._invalid_combine()

    def __and__(self, _other) -> Self:
        """Invalid and"""
        self._invalid_combine()

    def __getattr__(self, name):
        """The user is likely trying to reference the builder's object"""
        raise AttributeError(
            f"'{self.__class__.__name__}' has no attribute '{name}'. "
            f"Did you intend '<{self.__class__.__name__}>.{self._obj_name}.{name}'?"
        )


def validate_inputs(
    context: Builder, validating_class, objects: Iterable[Shape] = None
):
    """A function to wrap the method when used outside of a Builder context"""
    if context is None:
        pass
    else:
        context.validate_inputs(validating_class, objects)


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
        context = WorkplaneList._get_context()
        workplanes = context.workplanes if context else [Plane.XY]
        global_locations = [
            plane.location * local_location
            for plane in workplanes
            for local_location in self.local_locations
        ]
        return global_locations

    def __init__(self, locations: list[Location]):
        self._reset_tok = None
        self.local_locations = locations
        self.location_index = 0
        self.plane_index = 0
        self.iter_loc = None

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
        self.iter_loc = self.locations
        return self

    def __next__(self):
        """While not through all the locations, return the next one"""
        if self.location_index >= len(self.iter_loc):
            raise StopIteration
        result = self.iter_loc[self.location_index]
        self.location_index += 1
        return result

    def __mul__(self, shape: Shape) -> list[Shape]:
        """Vectorized application of locations to a shape"""
        if not isinstance(shape, Shape):
            raise ValueError("Location list can only be multiplied with shapes")
        return [loc * shape for loc in self.locations]

    @classmethod
    def _get_context(cls):
        """Return the instance of the current LocationList"""
        return cls._current.get(None)


class HexLocations(LocationList):
    """Location Context: Hex Array

    Creates a context of hexagon array of locations for Part or Sketch. When creating
    hex locations for an array of circles, set `radius` to the radius of the circle
    plus one half the spacing between the circles.

    Args:
        radius (float): distance from origin to vertices (major), or
            optionally from the origin to side (minor or apothem)
            with major_radius = False
        x_count (int): number of points ( > 0 )
        y_count (int): number of points ( > 0 )
        major_radius (bool): If True the radius is the major radius, else the
            radius is the minor radius (also known as inscribed radius).
            Defaults to False.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).

    Attributes:
        radius (float): distance from origin to vertices (major), or
            optionally from the origin to side (minor or apothem)
            with major_radius = False
        apothem (float): radius of the inscribed circle, also known as minor radius
        x_count (int): number of points ( > 0 )
        y_count (int): number of points ( > 0 )
        major_radius (bool): If True the radius is the major radius, else the
            radius is the minor radius (also known as inscribed radius).
        align (Union[Align, tuple[Align, Align]]): align min, center, or max of object.
        diagonal (float): major radius
        local_locations (list{Location}): locations relative to workplane

    Raises:
        ValueError: Spacing and count must be > 0
    """

    def __init__(
        self,
        radius: float,
        x_count: int,
        y_count: int,
        major_radius: bool = False,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
    ):
        # pylint: disable=too-many-locals

        if major_radius:
            diagonal = 2 * radius
            apothem = radius * cos(pi / 6)
        else:
            diagonal = 4 * radius / sqrt(3)
            apothem = radius

        x_spacing = 3 * diagonal / 4
        y_spacing = diagonal * sqrt(3) / 2
        if x_spacing <= 0 or y_spacing <= 0 or x_count < 1 or y_count < 1:
            raise ValueError("Spacing and count must be > 0 ")

        self.radius = radius
        self.apothem = apothem
        self.diagonal = diagonal
        self.x_count = x_count
        self.y_count = y_count
        self.major_radius = major_radius
        self.align = tuplify(align, 2)

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
        # pylint doesn't recognize that a ShapeList of Vector is valid
        # pylint: disable=no-member
        size = [
            sorted_points[0][-1].X - sorted_points[0][0].X,
            sorted_points[1][-1].Y - sorted_points[1][0].Y,
        ]
        min_corner = Vector(sorted_points[0][0].X, sorted_points[1][0].Y)

        # Calculate the amount to offset the array to align it
        align_offset = []
        for i in range(2):
            if self.align[i] == Align.MIN:
                align_offset.append(0)
            elif self.align[i] == Align.CENTER:
                align_offset.append(-size[i] / 2)
            elif self.align[i] == Align.MAX:
                align_offset.append(-size[i])

        # Align the points
        points = ShapeList(
            [point + Vector(*align_offset) - min_corner for point in points]
        )

        # Convert to locations and store the reference plane
        local_locations = [Location(point) for point in points]

        self.local_locations = Locations._move_to_existing(
            local_locations
        )  #: values independent of workplanes

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
        endpoint (bool, optional): If True, `start_angle` + `angular_range` is the last sample.
            Otherwise, it is not included. Defaults to False.

    Attributes:
        local_locations (list{Location}): locations relative to workplane

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
        endpoint: bool = False,
    ):
        if count < 1:
            raise ValueError(f"At least 1 elements required, requested {count}")
        if count == 1:
            angle_step = 0
        else:
            angle_step = angular_range / (count - int(endpoint))

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

        self.local_locations = Locations._move_to_existing(
            local_locations
        )  #: values independent of workplanes

        super().__init__(self.local_locations)


class Locations(LocationList):
    """Location Context: Push Points

    Creates a context of locations for Part or Sketch

    Args:
        pts (Union[VectorLike, Vertex, Location, Face, Plane, Axis] or iterable of same):
            sequence of points to push

    Attributes:
        local_locations (list{Location}): locations relative to workplane

    """

    def __init__(
        self,
        *pts: Union[
            VectorLike,
            Vertex,
            Location,
            Face,
            Plane,
            Axis,
            Iterable[VectorLike, Vertex, Location, Face, Plane, Axis],
        ],
    ):
        local_locations = []
        for point in flatten_sequence(*pts):
            if isinstance(point, Location):
                local_locations.append(point)
            elif isinstance(point, Vector):
                local_locations.append(Location(point))
            elif isinstance(point, Vertex):
                local_locations.append(Location(Vector(point.to_tuple())))
            elif isinstance(point, tuple):
                local_locations.append(Location(Vector(point)))
            elif isinstance(point, Plane):
                local_locations.append(Location(point))
            elif isinstance(point, Axis):
                local_locations.append(point.location)
            elif isinstance(point, Face):
                local_locations.append(Location(Plane(point)))
            else:
                raise ValueError(f"Locations doesn't accept type {type(point)}")

        self.local_locations = Locations._move_to_existing(
            local_locations
        )  #: values independent of workplanes
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
        if LocationList._get_context() is not None:
            for group_center in LocationList._get_context().local_locations:
                location_group.extend([group_center * l for l in local_locations])
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
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).


    Attributes:
        x_spacing (float): horizontal spacing
        y_spacing (float): vertical spacing
        x_count (int): number of horizontal points
        y_count (int): number of vertical points
        align (Union[Align, tuple[Align, Align]]): align min, center, or max of object.
        local_locations (list{Location}): locations relative to workplane

    Raises:
        ValueError: Either x or y count must be greater than or equal to one.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        x_spacing: float,
        y_spacing: float,
        x_count: int,
        y_count: int,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
    ):
        if x_count < 1 or y_count < 1:
            raise ValueError(
                f"At least 1 elements required, requested {x_count}, {y_count}"
            )
        self.x_spacing = x_spacing
        self.y_spacing = y_spacing
        self.x_count = x_count
        self.y_count = y_count
        self.align = tuplify(align, 2)

        size = [x_spacing * (x_count - 1), y_spacing * (y_count - 1)]
        self.size = Vector(*size)  #: size of the grid

        align_offset = []
        for i in range(2):
            if self.align[i] == Align.MIN:
                align_offset.append(0.0)
            elif self.align[i] == Align.CENTER:
                align_offset.append(-size[i] / 2)
            elif self.align[i] == Align.MAX:
                align_offset.append(-size[i])

        self.min = Vector(*align_offset)  #: bottom left corner
        self.max = self.min + self.size  #: top right corner

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

        self.local_locations = Locations._move_to_existing(
            local_locations
        )  #: values independent of workplanes
        self.planes: list[Plane] = []
        super().__init__(self.local_locations)


class WorkplaneList:
    """Workplane Context

    A stateful context of active workplanes. At least one must be active
    at all time.

    Args:
        workplanes (sequence of Union[Face, Plane, Location]): objects to become planes

    Attributes:
        workplanes (list[Plane]): list of workplanes

    """

    # Context variable used to link to WorkplaneList instance
    _current: contextvars.ContextVar["WorkplaneList"] = contextvars.ContextVar(
        "WorkplaneList._current"
    )

    def __init__(self, *workplanes: Union[Face, Plane, Location]):
        self._reset_tok = None
        self.workplanes = WorkplaneList._convert_to_planes(workplanes)
        self.locations_context = None
        self.plane_index = 0

    @staticmethod
    def _convert_to_planes(objs: Iterable[Union[Face, Plane, Location]]) -> list[Plane]:
        """Translate objects to planes"""
        objs = flatten_sequence(*objs)
        planes = []
        for obj in objs:
            if isinstance(obj, Plane):
                planes.append(obj)
            elif isinstance(obj, (Location, Face)):
                planes.append(Plane(obj))
            else:
                raise ValueError(f"WorkplaneList does not accept {type(obj)}")
        return planes

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
        if WorkplaneList._get_context() is None:
            points_per_workplane = [Vector(p) for p in points]
        else:
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


P = ParamSpec("P")
T2 = TypeVar("T2")


def __gen_context_component_getter(
    func: Callable[Concatenate[Builder, P], T2]
) -> Callable[P, T2]:
    @functools.wraps(func)
    def getter(select: Select = Select.ALL):
        context = Builder._get_context(func.__name__)
        if not context:
            raise RuntimeError(
                f"{func.__name__}() requires a Builder context to be in scope"
            )
        return func(context, select)

    return getter


vertices = __gen_context_component_getter(Builder.vertices)
edges = __gen_context_component_getter(Builder.edges)
wires = __gen_context_component_getter(Builder.wires)
faces = __gen_context_component_getter(Builder.faces)
solids = __gen_context_component_getter(Builder.solids)

vertex = __gen_context_component_getter(Builder.vertex)
edge = __gen_context_component_getter(Builder.edge)
wire = __gen_context_component_getter(Builder.wire)
face = __gen_context_component_getter(Builder.face)
solid = __gen_context_component_getter(Builder.solid)


#
# To avoid import loops, Vector add & sub are monkey-patched


def _vector_add_sub_wrapper(original_op: Callable[[Vector, VectorLike], Vector]):
    def wrapper(self: Vector, vec: VectorLike):
        if isinstance(vec, tuple):
            try:
                # Relative adds must take into consideration planes with non-zero origins
                origin = WorkplaneList._get_context().workplanes[0].origin
                vec = WorkplaneList.localize(vec) - origin  # type: ignore[union-attr]
            except AttributeError:
                # raised from `WorkplaneList._get_context().workplanes[0]` when context is `None`
                pass
        return original_op(self, vec)

    return wrapper


logger.debug("monkey-patching `Vector.add` and `Vector.sub`")
Vector.add = _vector_add_sub_wrapper(Vector.add)  # type: ignore
Vector.sub = _vector_add_sub_wrapper(Vector.sub)  # type: ignore
