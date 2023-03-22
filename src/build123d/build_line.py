"""
BuildLine

name: build_line.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build lines in three dimensional space.

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

from typing import Union

from build123d.build_common import Builder, WorkplaneList, logger
from build123d.build_enums import Mode, Select
from build123d.build_sketch import BuildSketch
from build123d.geometry import Location, Plane
from build123d.topology import Compound, Curve, Edge, Face, ShapeList, Wire


class BuildLine(Builder):
    """BuildLine

    Create lines (objects with length but not area or volume) from edges or wires.

    BuildLine only works with a single workplane which is used to convert tuples
    as inputs to global coordinates. For example:

    .. code::

        with BuildLine(Plane.YZ) as radius_arc:
            RadiusArc((1, 2), (2, 1), 1)

    creates an arc from global points (0, 1, 2) to (0, 2, 1). Note that points
    entered as Vector(x, y, z) are considered global and are not localized.

    The workplane is also used to define planes parallel to the workplane that
    arcs are created on.

    Args:
        workplane (Union[Face, Plane, Location], optional): plane used when local
            coordinates are used and when creating arcs. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    @staticmethod
    def _tag() -> str:
        return BuildLine

    @property
    def _obj(self):
        return self.line

    @property
    def _obj_name(self):
        return "line"

    def __init__(
        self,
        workplane: Union[Face, Plane, Location] = Plane.XY,
        mode: Mode = Mode.ADD,
    ):
        self.initial_plane = workplane
        self.mode = mode
        self.line: Curve = None
        super().__init__(workplane, mode=mode)

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)

        if self.builder_parent is not None and self.mode != Mode.PRIVATE:
            logger.debug(
                "Transferring object(s) to %s", type(self.builder_parent).__name__
            )
            if (
                isinstance(self.builder_parent, BuildSketch)
                and self.initial_plane != Plane.XY
            ):
                logger.debug(
                    "Realigning object(s) to Plane.XY for transfer to BuildSketch"
                )
                realigned = self.initial_plane.to_local_coords(self.line)
                self.builder_parent._add_to_context(realigned, mode=self.mode)
            else:
                self.builder_parent._add_to_context(self.line, mode=self.mode)

        self.exit_workplanes = WorkplaneList._get_context().workplanes

        # Now that the object has been transferred, it's save to remove any (non-default)
        # workplanes that were created then exit
        if self.workplanes:
            self.workplanes_context.__exit__(None, None, None)

        logger.info("Exiting %s", type(self).__name__)

    def faces(self, *args):
        """faces() not implemented"""
        raise NotImplementedError("faces() doesn't apply to BuildLine")

    def solids(self, *args):
        """solids() not implemented"""
        raise NotImplementedError("solids() doesn't apply to BuildLine")

    def wires(self, select: Select = Select.ALL) -> ShapeList[Wire]:
        """Return Wires from Line

        Return a list of wires created from the edges in either all or those created
        during the last operation.

        Args:
            select (Select, optional): Wire selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Wire]: Wires extracted
        """
        if select == Select.ALL:
            wire_list = Wire.combine(self.line.edges())
        elif select == Select.LAST:
            wire_list = Wire.combine(self.last_edges)
        return ShapeList(wire_list)

    def _add_to_context(self, *objects: Union[Edge, Wire], mode: Mode = Mode.ADD):
        """Add objects to BuildSketch instance

        Core method to interface with BuildLine instance. Input sequence of edges are
        combined with current line.

        Each operation generates a list of vertices and edges that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            objects (Edge): sequence of edges to add
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.
        """
        if mode != Mode.PRIVATE:
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            new_wires = [obj for obj in objects if isinstance(obj, Wire)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_edges.extend(compound.get_type(Edge))
                new_wires.extend(compound.get_type(Wire))
            for wire in new_wires:
                new_edges.extend(wire.edges())
            if new_edges:
                logger.debug(
                    "Add %d Edge(s) into line with Mode=%s", len(new_edges), mode
                )

            if mode == Mode.ADD:
                if self.line:
                    self.line = self.line.fuse(*new_edges)
                else:
                    self.line = Compound.make_compound(new_edges)
            elif mode == Mode.SUBTRACT:
                if self.line is None:
                    raise RuntimeError("No line to subtract from")
                self.line = self.line.cut(*new_edges)
            elif mode == Mode.INTERSECT:
                if self.line is None:
                    raise RuntimeError("No line to intersect with")
                self.line = self.line.intersect(*new_edges)
            elif mode == Mode.REPLACE:
                self.line = Compound.make_compound(new_edges)

            if self.line is not None:
                if isinstance(self.line, Compound):
                    self.line = Curve(self.line.wrapped)
                else:
                    self.line = Curve(Compound.make_compound(self.line.edges()).wrapped)

            self.last_edges = ShapeList(new_edges)
            self.last_vertices = ShapeList(
                set(v for e in self.last_edges for v in e.vertices())
            )
