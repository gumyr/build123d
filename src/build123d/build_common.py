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
import functools
import inspect
import logging
import sys
import warnings
from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field as dataclass_field
from itertools import product
from math import cos, pi, sqrt
from typing import Any, Generic, Type, TypeVar, cast

from OCP.Standard import Standard_ConstructionError
from typing_extensions import Self

from build123d.build_enums import Align, Mode, Select

# Compatibility import, so that existing code can import constants from build_common
from build123d.build_constants import (  # pylint: disable=unused-import
    CM,
    FT,
    G,
    G_PER_LB,
    IN,
    KG,
    LB,
    M,
    MC,
    MM,
    THOU,
    UNITS_PER_KILOGRAM,
    UNITS_PER_METER,
)
from build123d.geometry import (
    Axis,
    Location,
    Plane,
    Vector,
    VectorLike,
    to_align_offset,
)
from build123d.topology import (
    Compound,
    Curve,
    Edge,
    Face,
    Joint,
    Part,
    Shape,
    ShapeList,
    Sketch,
    Solid,
    Vertex,
    Wire,
    new_edges,
    tuplify,
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


def _is_point(obj):
    """Identify points as tuples of numbers"""
    return isinstance(obj, tuple) and all(
        isinstance(item, (int, float)) for item in obj
    )


T = TypeVar("T", Any, list[Any])


def flatten_sequence(*obj: T) -> ShapeList[Any]:
    """Convert a sequence of object potentially containing iterables into a flat list"""

    flat_list: ShapeList[Any] = ShapeList()
    for item in obj:
        # Note: an Iterable can't be used here as it will match with Vector & Vertex
        # and break them into a list of floats. Iterators are safe to consume.
        if isinstance(item, (list, tuple, set, Iterator)) and not _is_point(item):
            flat_list.extend(flatten_sequence(*item))
        else:
            flat_list.append(item)

    return flat_list


operations_apply_to = {
    "add": ["BuildPart", "BuildSketch", "BuildLine"],
    "bounding_box": ["BuildPart", "BuildSketch", "BuildLine"],
    "chamfer": ["BuildPart", "BuildSketch", "BuildLine"],
    "draft": ["BuildPart"],
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

B = TypeVar("B", bound="Builder")
"""Builder type hint"""

ShapeT = TypeVar("ShapeT", bound=Shape)
"""Builder's are generic shape creators"""


def _normalize_placements(
    placements: Iterable[Face | Plane | Location],
) -> tuple[Location, ...]:
    """Convert Builder placement inputs to immutable Location values."""
    normalized: list[Location] = []
    for placement in flatten_sequence(*placements):
        if isinstance(placement, Location):
            normalized.append(placement)
        elif isinstance(placement, Plane):
            normalized.append(placement.location)
        elif isinstance(placement, Face):
            normalized.append(Plane(placement).location)
        else:
            raise ValueError(f"Builder does not accept placement {type(placement)}")
    return tuple(normalized) if normalized else (Location(),)


class Builder(ABC, Generic[ShapeT]):
    """Builder

    Base class for the build123d Builders.

    Args:
        placements: sequence of Union[Face, Plane, Location]: output placement(s)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Attributes:
        mode (Mode): builder's combination mode
        placements (tuple[Location, ...]): output placement(s)
        builder_parent (Builder): build to pass objects to on exit

    """

    # pylint: disable=too-many-instance-attributes

    # Abstract class variables
    _tag = "Builder"
    _obj_name = "None"
    # _shape: Shape  # The type of the shape the builder creates
    # _sub_class: Curve | Sketch | Part  # The class of the shape the builder creates

    def __init__(
        self,
        *placements: Face | Plane | Location,
        mode: Mode = Mode.ADD,
    ):
        self.mode = mode
        self.output_placements = _normalize_placements(placements)
        self.placements = self.output_placements
        self._scope_context: AbstractContextManager[BuildScope] | None = None
        self._placed_obj: Shape | None = None
        current_frame = inspect.currentframe()
        assert current_frame is not None
        assert current_frame.f_back is not None
        self._python_frame = current_frame.f_back.f_back
        self.parent_frame = None
        self.builder_parent: Builder | None = None
        self.lasts: dict = {Vertex: [], Edge: [], Face: [], Solid: []}
        self.obj_before: Shape | None = None
        self.to_combine: list[Shape] = []

    @property
    @abstractmethod
    def _obj(self) -> Shape | None:
        """Object to pass to parent"""
        raise NotImplementedError  # pragma: no cover

    @_obj.setter
    @abstractmethod
    def _obj(self, value: Part) -> None:
        raise NotImplementedError  # pragma: no cover

    @property
    def max_dimension(self) -> float:
        """Maximum size of object in all directions"""
        return self._obj.bounding_box().diagonal if self._obj else 0.0

    @property
    def new_edges(self) -> ShapeList[Edge]:
        """Edges that changed during last operation"""
        if self._obj is None:
            return ShapeList()
        before_list = [] if self.obj_before is None else [self.obj_before]
        return new_edges(*(before_list + self.to_combine), combined=self._obj)

    def __enter__(self) -> Self:
        """Upon entering record the parent and a token to restore contextvars"""

        # Only set parents from the same scope. Note inspect.currentframe() is supported
        # by CPython in Linux, Window & MacOS but may not be supported in other python
        # implementations.  Support outside of these OS's is outside the scope of this
        # project.
        builder_context: Builder | None = Builder._get_context()
        current_frame = inspect.currentframe()
        same_scope = (
            builder_context._python_frame == current_frame.f_back
            if builder_context and current_frame
            else False
        )

        if same_scope:
            self.builder_parent = builder_context
        else:
            self.builder_parent = None

        logger.info(
            "Entering %s with mode=%s which is in %s scope as parent",
            type(self).__name__,
            self.mode,
            "same" if same_scope else "different",
        )

        parent_scope = _get_build_scope()
        location_context = LocationList._get_context()
        publication_locations = (
            tuple(location_context.locations)
            if location_context is not None
            else _identity_locations()
        )
        local_locations = LocationList([Location()])
        scope = BuildScope(
            parent=parent_scope,
            builder=self,
            operation_locations=_identity_locations(),
            publication_locations=publication_locations,
            output_placements=self.output_placements,
            owner=self,
            publication_target=self.builder_parent,
            location_context=local_locations,
            object_context=(
                _object_scope_for(parent_scope)
            ),
        )
        self._scope_context = _build_scope_context(scope)
        self._scope_context.__enter__()

        return self

    def _exit_extras(self):
        """Any builder specific exit actions"""

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        scope = _get_build_scope()
        assert scope is not None and scope.owner is self
        try:
            self._exit_extras()  # custom builder exit code
        finally:
            assert self._scope_context is not None
            self._scope_context.__exit__(
                exception_type, exception_value, traceback
            )

        try:
            local_product = self._obj
        except AttributeError:
            local_product = None
        if self.builder_parent is not None and self.mode != Mode.PRIVATE:
            logger.debug(
                "Transferring object(s) to %s", type(self.builder_parent).__name__
            )
            if local_product is None and not sys.exc_info()[1]:
                warnings.warn(
                    f"{self._obj_name} is None - {self._tag} didn't create anything",
                    stacklevel=2,
                )
        self._placed_obj = _PublicationService.publish(
            local_product,
            scope,
            self.mode,
            result_type=getattr(type(self), "_sub_class", None),
        )

        logger.info("Exiting %s", type(self).__name__)

    def _place_output(self) -> Shape | None:
        """Apply publication locations and output placements to the local product."""
        scope = _get_build_scope()
        assert scope is not None and scope.owner is self
        try:
            local_product = self._obj
        except AttributeError:
            return None
        return _PublicationService.place(
            local_product, scope, result_type=self._sub_class
        )

    def _output_obj(self) -> Shape | None:
        """Return placed output during and after Builder construction."""
        if self._placed_obj is not None:
            return self._placed_obj
        scope = _get_build_scope()
        if scope is not None and scope.owner is self:
            return self._place_output()
        return self._obj

    @abstractmethod
    def _add_to_pending(self, *objects: Edge | Face, face_plane: Plane | None = None):
        """Integrate a sequence of objects into existing builder object"""
        return NotImplementedError  # pragma: no cover

    @classmethod
    def _get_context(
        cls: Type[B],
        caller: Builder | Shape | Joint | str | None = None,
        log: bool = True,
    ) -> B | None:
        """Return the instance of the current builder"""
        scope = _get_build_scope()
        result = scope.builder if scope is not None else None
        object_scope = BaseObjectMeta._get_context()
        if (
            result is None
            and object_scope is not None
            and isinstance(object_scope.owner, _BaseObjectScopeOwner)
            and caller is object_scope.owner.root
        ):
            result = cast(B, object_scope.publication_target)
        context_name = "None" if result is None else type(result).__name__

        if log:
            if isinstance(caller, (Part, Sketch, Curve, Wire)):
                caller_name = caller.__class__.__name__
            elif isinstance(caller, str):
                caller_name = caller
            else:
                caller_name = "None"
            logger.info("%s context requested by %s", context_name, caller_name)

        return cast(B, result)

    def _add_to_context(
        self,
        *objects: Edge | Wire | Face | Solid | Compound,
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
            # Typed dictionary: keys are classes, values are lists of instances of those classes
            typed: dict[
                Type[Edge | Wire | Face | Solid | Compound],
                list[Edge | Wire | Face | Solid | Compound],
            ] = {cls: [] for cls in [Edge, Wire, Face, Solid, Compound]}
            for cls in [Edge, Wire, Face, Solid, Compound]:
                typed[cls] = [obj for obj in objects if isinstance(obj, cls)]

            # Check for invalid inputs
            num_stored = sum(len(t) for t in typed.values())
            # Generate an exception if not processing exceptions
            if len(objects) != num_stored and not sys.exc_info()[1]:
                unsupported = set(objects) - {v for l in typed.values() for v in l}
                if unsupported != {None}:
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
                        except (TypeError, ValueError, Standard_ConstructionError):
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
                combined: Shape | list[Shape] | None
                needs_clean = clean
                if mode == Mode.ADD:
                    if self._obj is None:
                        if len(typed[self._shape]) == 1:
                            combined = typed[self._shape][0]
                        else:
                            combined = (
                                typed[self._shape].pop().fuse(*typed[self._shape])
                            )
                            needs_clean = False
                    else:
                        combined = self._obj.fuse(*typed[self._shape])
                        needs_clean = False
                elif mode == Mode.SUBTRACT:
                    if self._obj is None:
                        raise RuntimeError("Nothing to subtract from")
                    combined = self._obj.cut(*typed[self._shape])
                    needs_clean = False
                elif mode == Mode.INTERSECT:
                    if self._obj is None:
                        raise RuntimeError("Nothing to intersect with")
                    combined = self._obj.intersect(Compound(typed[self._shape]))
                    needs_clean = False
                elif mode == Mode.REPLACE:
                    combined = self._sub_class(list(typed[self._shape]))

                if combined is None:  # empty intersection result
                    self._obj = self._sub_class()
                elif isinstance(
                    combined, list
                ):  # If the boolean operation created a list, convert back
                    self._obj = self._sub_class(combined)
                else:
                    self._obj = combined
                # If the boolean operation created a list, convert back
                # self._obj = (
                #     self._sub_class(combined)
                #     if isinstance(combined, list)
                #     else combined
                # )

                if self._obj is not None and needs_clean:
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
                for pending_face in typed[Face]:
                    pending_plane: Plane | None
                    try:
                        pending_plane = Plane(pending_face)
                    except ValueError:
                        pending_plane = Plane.XY
                    self._add_to_pending(
                        pending_face, face_plane=pending_plane
                    )
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
            obj_edges = [] if self._obj is None else self._obj.edges()
            for obj_edge in obj_edges:
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
            raise ValueError(f"Expected exactly one vertex, found {vertex_count}")
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
            edge_list = ShapeList() if self._obj is None else self._obj.edges()
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
            raise ValueError(f"Expected exactly one edge, found {edge_count}")
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
            wire_list = ShapeList() if self._obj is None else self._obj.wires()
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
            raise ValueError(f"Expected exactly one wire, found {wire_count}")
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
            face_list = ShapeList() if self._obj is None else self._obj.faces()
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
            raise ValueError(f"Expected exactly one face, found {face_count}")
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
            solid_list = ShapeList() if self._obj is None else self._obj.solids()
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
            raise ValueError(f"Expected exactly one solid, found {solid_count}")
        return all_solids[0]

    def _shapes(
        self,
        obj_type: Type[Vertex] | Type[Edge] | Type[Face] | Type[Solid] | None = None,
    ) -> ShapeList:
        """Extract Shapes"""
        obj_type = self._shape if obj_type is None else obj_type
        if self._obj is None:
            return ShapeList()

        if obj_type == Vertex:
            return self._obj.vertices()
        if obj_type == Edge:
            return self._obj.edges()
        if obj_type == Face:
            return self._obj.faces()
        if obj_type == Solid:
            return self._obj.solids()
        return ShapeList()

    def validate_inputs(
        self, validating_class, objects: Shape | Iterable[Shape] | None = None
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
        return self._invalid_combine()

    def __sub__(self, _other) -> Self:
        """Invalid sub"""
        return self._invalid_combine()

    def __and__(self, _other) -> Self:
        """Invalid and"""
        return self._invalid_combine()

    def __getattr__(self, name):
        """The user is likely trying to reference the builder's object"""
        raise AttributeError(
            f"'{self.__class__.__name__}' has no attribute '{name}'. "
            f"Did you intend '<{self.__class__.__name__}>.{self._obj_name}.{name}'?"
        )


def validate_inputs(
    context: Builder | None, validating_class, objects: Iterable[Shape] | None = None
):
    """A function to wrap the method when used outside of a Builder context"""
    if context is None:
        pass
    else:
        context.validate_inputs(validating_class, objects)


class LocationList:
    """Location Context

    A stateful context of active locations. At least one must be active
    at all times. Locations are expressed in the Builder's local Plane.XY
    construction coordinates. Consequently, ordinary ``Vector`` and tuple
    arithmetic is already local and no workplane-aware Vector monkeypatch is
    required; output placements are applied only when the product is published.

    Args:
        locations (list[Location]): list of locations to add to the context

    """

    @property
    def locations(self) -> list[Location]:
        """Current locations in local construction coordinates."""
        return self.local_locations

    def __init__(self, locations: list[Location]):
        self._scope_context: AbstractContextManager[BuildScope] | None = None
        self.local_locations = locations

    def __enter__(self):
        """Upon entering create a token to restore contextvars"""
        active_scope = _get_build_scope()
        if active_scope is not None:
            location_scope = active_scope.derive(
                operation_locations=tuple(self.locations),
                owner=self,
                location_context=self,
                object_context=_object_scope_for(active_scope),
            )
        else:
            location_scope = BuildScope(
                operation_locations=tuple(self.locations),
                owner=self,
                location_context=self,
            )
        self._scope_context = _build_scope_context(location_scope)
        self._scope_context.__enter__()

        logger.info(
            "%s is pushing %d points: %s",
            type(self).__name__,
            len(self.local_locations),
            self.local_locations,
        )
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context"""
        assert self._scope_context is not None
        self._scope_context.__exit__(exception_type, exception_value, traceback)
        logger.info(
            "%s is popping %d points", type(self).__name__, len(self.local_locations)
        )

    def __iter__(self):
        return iter(self.locations)

    @classmethod
    def _get_context(cls):
        """Return the LocationList held by the authoritative BuildScope.

        LocationList previously owned a class-level ContextVar. Delegating to
        the unified scope ensures Builder, location, and BaseObject state are
        pushed and restored together instead of through independent stacks.
        """
        scope = _get_build_scope()
        return scope.location_context if scope is not None else None


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
        align: Align | tuple[Align, Align] = (Align.CENTER, Align.CENTER),
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
        align_offset = to_align_offset((0, 0), size, align)

        # Align the points
        points = ShapeList(
            [point + Vector(*align_offset) - min_corner for point in points]
        )

        # Convert to locations and store the reference plane
        local_locations = [Location(point) for point in points]

        self.local_locations = Locations._move_to_existing(
            local_locations
        )  #: values in local construction coordinates

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
            angle_step = 0.0
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
        *pts: (
            VectorLike
            | Vertex
            | Location
            | Face
            | Plane
            | Axis
            | Iterable[VectorLike | Vertex | Location | Face | Plane | Axis]
        ),
    ):
        local_locations = []
        for point in flatten_sequence(*pts):
            if isinstance(point, Location):
                local_locations.append(point)
            elif isinstance(point, Vector):
                local_locations.append(Location(point))
            elif isinstance(point, Vertex):
                local_locations.append(Location(Vector(point)))
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
        align: Align | tuple[Align, Align] = (Align.CENTER, Align.CENTER),
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

        align_offset = to_align_offset((0, 0), size, align)

        self.min = align_offset  #: bottom left corner
        self.max = self.min + self.size  #: top right corner

        # Create the list of local locations
        local_locations = [
            Location(
                align_offset
                + Vector(
                    i * x_spacing,
                    j * y_spacing,
                )
            )
            for i, j in product(range(x_count), range(y_count))
        ]

        self.local_locations = Locations._move_to_existing(
            local_locations
        )  #: values independent of workplanes
        self.planes: list[Plane] = []
        super().__init__(self.local_locations)


class _InheritedScopeValue:
    """Sentinel identifying an omitted ``BuildScope.derive()`` argument.

    A nullable scope field needs three instructions when deriving a child:
    inherit the parent value, replace it, or explicitly clear it with ``None``.
    The sentinel represents inheritance without making ``None`` ambiguous.
    It is only an argument state; it is never stored in a ``BuildScope`` field.
    """


_INHERITED_SCOPE_VALUE = _InheritedScopeValue()
_ScopeValueT = TypeVar("_ScopeValueT")


def _scope_value(
    value: _ScopeValueT | _InheritedScopeValue, inherited: _ScopeValueT
) -> _ScopeValueT:
    """Resolve a derive argument while preserving the field's static type."""
    return (
        inherited
        if value is _INHERITED_SCOPE_VALUE
        else cast(_ScopeValueT, value)
    )


def _identity_locations() -> tuple[Location, ...]:
    """Return identity placement state owned by one scope.

    ``Location`` is mutable, even though the containing tuple is not. A default
    factory prevents otherwise independent scopes from sharing one mutable
    identity ``Location`` created at class-definition time.
    """
    return (Location(),)


@dataclass(frozen=True, slots=True)
class BuildScope:
    """Immutable context state shared by Builders and BaseObjects.

    One scope groups Builder construction, publication, location, and BaseObject
    isolation state so a context transition replaces all related state atomically.
    Earlier implementations used independent ``ContextVar`` stacks for Builder,
    LocationList, WorkplaneList, and BaseObject; those stacks could temporarily
    disagree and made firewall restoration dependent on reset ordering.
    """

    parent: BuildScope | None = None
    builder: Builder | None = None
    operation_locations: tuple[Location, ...] = dataclass_field(
        default_factory=_identity_locations
    )
    publication_locations: tuple[Location, ...] = dataclass_field(
        default_factory=_identity_locations
    )
    output_placements: tuple[Location, ...] = dataclass_field(
        default_factory=_identity_locations
    )
    owner: object | None = None
    publication_target: Builder | None = None
    isolated: bool = False
    location_context: LocationList | None = None
    object_context: BuildScope | None = None
    object_local_locations: tuple[Location, ...] = dataclass_field(
        default_factory=_identity_locations
    )
    object_placements: tuple[Location, ...] = dataclass_field(
        default_factory=_identity_locations
    )

    def __post_init__(self):
        """Reject empty transform sets that would silently produce no geometry.

        Internal factories normally guarantee this invariant, but ``derive()``
        can be called directly with an empty tuple. Publication and operation
        code use Cartesian products over these fields, so an empty value would
        discard a valid product rather than fail near the source of the error.
        """
        for name in (
            "operation_locations",
            "publication_locations",
            "output_placements",
            "object_local_locations",
            "object_placements",
        ):
            if not getattr(self, name):
                raise ValueError(f"BuildScope.{name} cannot be empty")

    # pylint: disable=too-many-arguments
    def derive(
        self,
        *,
        builder: Builder | None | _InheritedScopeValue = _INHERITED_SCOPE_VALUE,
        operation_locations: (
            tuple[Location, ...] | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
        publication_locations: (
            tuple[Location, ...] | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
        output_placements: (
            tuple[Location, ...] | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
        owner: object | _InheritedScopeValue = _INHERITED_SCOPE_VALUE,
        publication_target: (
            Builder | None | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
        isolated: bool | _InheritedScopeValue = _INHERITED_SCOPE_VALUE,
        location_context: (
            LocationList | None | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
        object_context: (
            BuildScope | None | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
        object_local_locations: (
            tuple[Location, ...] | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
        object_placements: (
            tuple[Location, ...] | _InheritedScopeValue
        ) = _INHERITED_SCOPE_VALUE,
    ) -> BuildScope:
        """Create a child scope, inheriting arguments that were omitted.

        For nullable fields such as ``builder``, omission inherits the parent,
        ``None`` explicitly clears the field, and an object replaces it. The
        private sentinel distinguishes omission from the meaningful ``None``.
        """
        return BuildScope(
            parent=self,
            builder=_scope_value(builder, self.builder),
            operation_locations=_scope_value(
                operation_locations, self.operation_locations
            ),
            publication_locations=_scope_value(
                publication_locations, self.publication_locations
            ),
            output_placements=_scope_value(
                output_placements, self.output_placements
            ),
            owner=_scope_value(owner, self.owner),
            publication_target=_scope_value(
                publication_target, self.publication_target
            ),
            isolated=_scope_value(isolated, self.isolated),
            location_context=_scope_value(
                location_context, self.location_context
            ),
            object_context=_scope_value(object_context, self.object_context),
            object_local_locations=_scope_value(
                object_local_locations, self.object_local_locations
            ),
            object_placements=_scope_value(
                object_placements, self.object_placements
            ),
        )


# This is the single authoritative context stack. ContextVar gives each thread
# or asynchronous task its own active scope, while token reset restores nested
# scopes safely. It is module state rather than a BuildScope ClassVar because
# BuildScope is only the immutable value being stored; activating that value is
# a separate runtime responsibility.
_build_scope: contextvars.ContextVar[BuildScope | None] = contextvars.ContextVar(
    "BuildScope.current", default=None
)


def _get_build_scope() -> BuildScope | None:
    """Return the active unified build scope."""
    return _build_scope.get()


def _push_build_scope(scope: BuildScope) -> contextvars.Token[BuildScope | None]:
    """Push a BuildScope and return the token required to restore its parent."""
    logger.debug(
        "Pushing BuildScope owner=%s isolated=%s",
        type(scope.owner).__name__ if scope.owner is not None else "None",
        scope.isolated,
    )
    return _build_scope.set(scope)


def _pop_build_scope(token: contextvars.Token[BuildScope | None]) -> None:
    """Restore the BuildScope associated with a previous push token."""
    _build_scope.reset(token)
    scope = _build_scope.get()
    logger.debug(
        "Restored BuildScope owner=%s",
        type(scope.owner).__name__ if scope and scope.owner is not None else "None",
    )


@contextmanager
def _build_scope_context(scope: BuildScope) -> Iterator[BuildScope]:
    """Activate a BuildScope for the duration of a context manager."""
    token = _push_build_scope(scope)
    try:
        yield scope
    finally:
        _pop_build_scope(token)


@dataclass(slots=True)
class _BaseObjectScopeOwner:
    """Mutable lifecycle state for an otherwise immutable object scope."""

    root: BaseObject | None = None


def _object_scope_for(scope: BuildScope | None) -> BuildScope | None:
    """Return the nearest BaseObject scope represented by ``scope``."""
    if scope is None:
        return None
    if scope.isolated and isinstance(scope.owner, _BaseObjectScopeOwner):
        return scope
    return scope.object_context


class BaseObjectMeta(ABCMeta):
    """Isolate BaseObject internals from their caller's implicit contexts."""

    @classmethod
    def _get_context(mcs) -> BuildScope | None:
        """Return the active object construction compatibility context."""
        scope = _get_build_scope()
        return _object_scope_for(scope) if scope is not None else None

    @staticmethod
    def _validate_builder(object_type: type, builder: Builder | None) -> None:
        """Validate a declared object-to-Builder restriction before construction.

        Base object classes provide ``_applies_to`` and custom subclasses inherit
        that declaration automatically. A class without the attribute has not
        declared a restriction, so it remains compatible with custom object
        implementations written before this centralized validation existed.
        """
        applies_to = getattr(object_type, "_applies_to", None)
        if (
            builder is not None
            and applies_to is not None
            and builder._tag not in applies_to
        ):
            raise RuntimeError(
                f"{builder.__class__.__name__} doesn't have a "
                f"{object_type.__name__} object or operation "
                f"({object_type.__name__} applies to {applies_to})"
            )

    def __call__(cls, *args, **kwargs):
        """Construct the outer object behind a Builder and placement firewall."""
        if _get_build_scope() is None:
            return super().__call__(*args, **kwargs)

        parent_object_scope = BaseObjectMeta._get_context()
        location_context = LocationList._get_context()
        publication_target = Builder._get_context(log=False)
        BaseObjectMeta._validate_builder(cls, publication_target)
        parent_scope = _get_build_scope()
        publication_locations = (
            tuple(location_context.locations)
            if location_context is not None
            else _identity_locations()
        )
        object_local_locations = (
            tuple(location_context.local_locations)
            if location_context is not None
            else _identity_locations()
        )
        owner = _BaseObjectScopeOwner()
        isolated_scope = BuildScope(
            parent=parent_scope,
            builder=None,
            operation_locations=_identity_locations(),
            publication_locations=publication_locations,
            owner=owner,
            publication_target=publication_target,
            isolated=True,
            location_context=LocationList([Location()]),
            object_context=parent_object_scope,
            object_local_locations=object_local_locations,
            object_placements=(
                parent_scope.output_placements
                if parent_scope is not None
                else _identity_locations()
            ),
        )
        with _build_scope_context(isolated_scope):
            instance = super().__call__(*args, **kwargs)
        instance._publish_to_context(isolated_scope)
        return instance


class _PublicationService:
    """Place completed products and publish them to captured Builders."""

    @staticmethod
    def _topology_copy(build_product: Shape) -> Shape:
        """Copy topology without deepcopying arbitrary custom-object state."""
        if isinstance(build_product, Edge):
            result = Edge(build_product.wrapped)
        elif isinstance(build_product, Wire):
            result = Wire(build_product.wrapped)
        elif isinstance(build_product, Part):
            result = Part(build_product.wrapped)
        elif isinstance(build_product, Sketch):
            result = Sketch(build_product.wrapped)
        elif isinstance(build_product, Curve):
            result = Curve(build_product.wrapped)
        elif isinstance(build_product, Compound):
            result = Compound(build_product.wrapped)
        else:
            result = build_product
        return result

    @staticmethod
    def _can_adopt_placement(build_product: Shape, placed: Shape) -> bool:
        """Return whether placed topology can be adopted by the original object."""
        return isinstance(build_product, Compound) or (
            build_product.__class__ is placed.__class__
        )

    @staticmethod
    def place(
        build_product: Shape | None,
        scope: BuildScope,
        *,
        result_type: Type[Shape] | None = None,
    ) -> Shape | None:
        """Apply every publication/output placement combination exactly once."""
        if build_product is None or getattr(build_product, "_wrapped", None) is None:
            return None
        if (
            scope.publication_locations == (Location(),)
            and scope.output_placements == (Location(),)
        ):
            return build_product

        placement_source = _PublicationService._topology_copy(build_product)
        placed = [
            publication * output * placement_source
            for publication in scope.publication_locations
            for output in scope.output_placements
        ]
        if not all(isinstance(placed_product, Shape) for placed_product in placed):
            return build_product
        if len(placed) == 1:
            result = placed[0]
        else:
            if result_type is None:
                result_type = (
                    {1: Curve, 2: Sketch, 3: Part}.get(
                        build_product._dim, Compound
                    )
                    if build_product._dim is not None
                    else Compound
                )
            result = result_type(Compound(placed).wrapped)
        build_product.copy_attributes_to(
            result,
            exceptions=("wrapped", "_NodeMixin__children"),
        )
        return result

    @classmethod
    def publish(
        cls,
        build_product: Shape | None,
        scope: BuildScope,
        mode: Mode,
        *,
        result_type: Type[Shape] | None = None,
        place: bool = True,
        preserve_identity: bool = False,
    ) -> Shape | None:
        """Place a product and dispatch it once to its publication target."""
        placed = (
            cls.place(build_product, scope, result_type=result_type)
            if place
            else build_product
        )
        if (
            preserve_identity
            and build_product is not None
            and placed is not None
            and placed is not build_product
            and cls._can_adopt_placement(build_product, placed)
        ):
            build_product.wrapped = placed.wrapped
            placed = build_product
        target = scope.publication_target
        if placed is None or target is None or mode == Mode.PRIVATE:
            return placed

        if target._tag not in {"BuildPart", "BuildSketch", "BuildLine"}:
            raise RuntimeError(f"Unsupported publication target {type(target).__name__}")

        target._add_to_context(placed, mode=mode)
        return placed


class BaseObject(metaclass=BaseObjectMeta):
    """Common context-isolation behavior for builder-aware objects."""

    __slots__ = ()

    def __new__(cls, *_args, **_kwargs):
        instance = super().__new__(cls)
        object_scope = BaseObjectMeta._get_context()
        if (
            object_scope is not None
            and isinstance(object_scope.owner, _BaseObjectScopeOwner)
            and object_scope.owner.root is None
        ):
            object_scope.owner.root = instance
        return instance

    @staticmethod
    def _get_object_context() -> BuildScope | None:
        """Return the active isolated object-construction context."""
        return BaseObjectMeta._get_context()

    @staticmethod
    def _get_builder_context() -> Builder | None:
        """Return the caller Builder captured for the active construction."""
        object_scope = BaseObjectMeta._get_context()
        return (
            object_scope.publication_target
            if object_scope is not None
            else None
        )

    @staticmethod
    def _get_object_locations() -> tuple[Location, ...]:
        """Return the caller locations captured for the active construction."""
        object_scope = BaseObjectMeta._get_context()
        return (
            object_scope.publication_locations
            if object_scope is not None
            else ()
        )

    @staticmethod
    def _get_object_local_locations() -> tuple[Location, ...]:
        """Return the caller local locations captured for the active construction."""
        object_scope = BaseObjectMeta._get_context()
        return (
            object_scope.object_local_locations
            if object_scope is not None
            else ()
        )

    @staticmethod
    def _get_object_placements() -> tuple[Location, ...]:
        """Return the caller Builder output placements captured for construction."""
        object_scope = BaseObjectMeta._get_context()
        return (
            object_scope.object_placements
            if object_scope is not None
            else ()
        )

    def _publish_to_context(self, object_scope: BuildScope):
        """Publish a completed object to its caller's captured context."""
        if not isinstance(self, Shape):
            return
        _PublicationService.publish(
            self,
            object_scope,
            getattr(self, "mode", Mode.ADD),
            preserve_identity=True,
        )


# Type variable representing the return type of the wrapped function
T2 = TypeVar("T2")


def __gen_context_component_getter(
    func: Callable[[Builder, Select], T2],
) -> Callable[[Select], T2]:
    """
    Wraps a Builder method to automatically provide the Builder context.

    This function creates a wrapper around the provided Builder method (`func`) that
    automatically retrieves the current Builder context and passes it as the first
    argument to the method. This allows the method to be called without explicitly
    providing the Builder context.

    Args:
        func (Callable[[Builder, Select], T2]): The Builder method to be wrapped.
            - The method must take a `Builder` instance as its first argument and
              a `Select` instance as its second argument.

    Returns:
        Callable[T2]: A callable that takes only a `Select` argument and
        internally retrieves the Builder context to call the original method.

    Raises:
        RuntimeError: If no Builder context is available when the returned function
        is called.
    """

    @functools.wraps(func)
    def getter(select: Select = Select.ALL) -> T2:
        # Retrieve the current Builder context based on the method name
        context: Builder | None = Builder._get_context(func.__name__)
        if context is None:
            raise RuntimeError(
                f"{func.__name__}() requires a Builder context to be in scope"
            )
        # Call the original method with the retrieved context and provided select
        return func(context, select)

    return getter


# The following functions are used to get the shapes from the builder in context
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
