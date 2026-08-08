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

from typing import ClassVar

from build123d.build_common import Builder
from build123d.build_enums import Mode
from build123d.geometry import Location, Plane
from build123d.topology import Curve, Edge, Face


class BuildLine(Builder[Curve]):
    """BuildLine

    The BuildLine class is a subclass of Builder for building lines (objects
    with length but not area or volume). It has an _obj property that returns
    the current line being built. The class overrides the faces and solids methods
    of Builder since they don't apply to lines.

    BuildLine constructs geometry on local Plane.XY and publishes the completed
    curve to a single placement. For example:

    .. code::

        with BuildLine(Plane.YZ) as radius_arc:
            RadiusArc((1, 2), (2, 1), 1)

    constructs an arc from local points (1, 2, 0) to (2, 1, 0), then publishes
    it to Plane.YZ.

    Args:
        placement (Union[Face, Plane, Location], optional): output placement.
            Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    build123d_type: ClassVar[str] = "BuildLine"
    _tag = "BuildLine"  # Alternate for __class__.__name__
    _obj_name = "line"  # Name of primary instance variable
    _shape = Edge  # Type of shapes being constructed
    _sub_class = Curve  # Class of line/_obj

    def __init__(
        self,
        placement: Face | Plane | Location = Plane.XY,
        mode: Mode = Mode.ADD,
    ):
        self._line: Curve | None = None
        super().__init__(placement, mode=mode)
        if len(self.output_placements) > 1:
            raise ValueError("BuildLine only accepts one placement")

    @property
    def line(self) -> Curve | None:
        """Get the placed line."""
        return self._output_obj()

    @line.setter
    def line(self, value: Curve) -> None:
        """Set the current line"""
        self._line = value

    @property
    def line_local(self) -> Curve | None:
        """Get the line in the Builder's local construction coordinates."""
        return self._line

    @property
    def _obj(self) -> Curve | None:
        """Alias _obj to line"""
        return self._line

    @_obj.setter
    def _obj(self, value: Curve) -> None:
        """Set the current line"""
        self._line = value

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

    def _add_to_pending(self, *objects: Edge | Face, face_plane: Plane | None = None):
        """_add_to_pending not implemented"""
        raise NotImplementedError("_add_to_pending doesn't apply to BuildLine")
