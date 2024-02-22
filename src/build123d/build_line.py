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
from build123d.build_enums import Mode
from build123d.geometry import Location, Plane
from build123d.topology import Curve, Edge, Face


class BuildLine(Builder):
    """BuildLine

    The BuildLine class is a subclass of Builder for building lines (objects
    with length but not area or volume). It has an _obj property that returns
    the current line being built. The class overrides the faces and solids methods
    of Builder since they don't apply to lines.

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

    _tag = "BuildLine"  # Alternate for __class__.__name__
    _obj_name = "line"  # Name of primary instance variable
    _shape = Edge  # Type of shapes being constructed
    _sub_class = Curve  # Class of line/_obj

    @property
    def _obj(self) -> Curve:
        return self.line

    @_obj.setter
    def _obj(self, value: Curve) -> None:
        self.line = value

    def __init__(
        self,
        workplane: Union[Face, Plane, Location] = Plane.XY,
        mode: Mode = Mode.ADD,
    ):
        self.line: Curve = None
        super().__init__(workplane, mode=mode)
        if len(self.workplanes) > 1:
            raise ValueError("BuildLine only accepts one workplane")

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting restore context and send object to parent"""
        self._current.reset(self._reset_tok)

        if (
            self.builder_parent is not None
            and self.mode != Mode.PRIVATE
            and self.line is not None
        ):
            logger.debug(
                "Transferring object(s) to %s", type(self.builder_parent).__name__
            )
            self.builder_parent._add_to_context(self.line, mode=self.mode)

        self.exit_workplanes = WorkplaneList._get_context().workplanes

        # Now that the object has been transferred, it's safe to remove any (non-default)
        # workplanes that were created then exit
        if self.workplanes:
            self.workplanes_context.__exit__(None, None, None)

        logger.info("Exiting %s", type(self).__name__)

    def faces(self, *args):
        """faces() not implemented"""
        raise NotImplementedError("faces() doesn't apply to BuildLine")

    def face(self, *args):
        """face() not implemented"""
        raise NotImplementedError("face() doesn't apply to BuildLine")

    def solids(self, *args):
        """solids() not implemented"""
        raise NotImplementedError("solids() doesn't apply to BuildLine")

    def solid(self, *args):
        """solid() not implemented"""
        raise NotImplementedError("solid() doesn't apply to BuildLine")

    def _add_to_pending(self, *objects: Union[Edge, Face], face_plane: Plane = None):
        """_add_to_pending not implemented"""
        raise NotImplementedError("_add_to_pending doesn't apply to BuildLine")
