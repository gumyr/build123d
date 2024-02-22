"""
BuildSketch

name: build_sketch.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build planar sketches.

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
from build123d.topology import Compound, Edge, Face, ShapeList, Sketch, Wire, Vertex


class BuildSketch(Builder):
    """BuildSketch

    The BuildSketch class is a subclass of Builder for building planar 2D
    sketches (objects with area but not volume) from faces or lines.
    It has an _obj property that returns the current sketch being built.
    The sketch property consists of the sketch(es) applied to the input
    workplanes while the sketch_local attribute is the sketch constructed
    on Plane.XY. The class overrides the solids method of Builder since
    they don't apply to lines.

    Note that all sketch construction is done within sketch_local on Plane.XY.
    When objects are added to the sketch they must be coplanar to Plane.XY,
    usually handled automatically but may need user input for Edges and Wires
    since their construction plane isn't alway able to be determined.

    Args:
        workplanes (Union[Face, Plane, Location], optional): objects converted to
            plane(s) to place the sketch on. Defaults to Plane.XY.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _tag = "BuildSketch"  # Alternate for __class__.__name__
    _obj_name = "sketch"  # Name of primary instance variable
    _shape = Face  # Type of shapes being constructed
    _sub_class = Sketch  # Class of sketch/_obj

    @property
    def _obj(self) -> Sketch:
        """The builder's object"""
        return self.sketch_local

    @_obj.setter
    def _obj(self, value: Sketch) -> None:
        self.sketch_local = value

    @property
    def sketch(self):
        """The global version of the sketch - may contain multiple sketches"""
        workplanes = (
            self.exit_workplanes
            if self.exit_workplanes
            else WorkplaneList._get_context().workplanes
        )
        global_objs = []
        for plane in workplanes:
            global_objs.append(plane.from_local_coords(self._obj))
        return Sketch(Compound(global_objs).wrapped)

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.mode = mode
        self.sketch_local: Sketch = None
        self.pending_edges: ShapeList[Edge] = ShapeList()
        super().__init__(*workplanes, mode=mode)

    def solids(self, *args):
        """solids() not implemented"""
        raise NotImplementedError("solids() doesn't apply to BuildSketch")

    def solid(self, *args):
        """solid() not implemented"""
        raise NotImplementedError("solid() doesn't apply to BuildSketch")

    def consolidate_edges(self) -> Union[Wire, list[Wire]]:
        """Unify pending edges into one or more Wires"""
        wires = Wire.combine(self.pending_edges)
        return wires if len(wires) > 1 else wires[0]

    def _add_to_pending(self, *objects: Edge, face_plane: Plane = None):
        """Integrate a sequence of objects into existing builder object"""
        if face_plane:
            raise NotImplementedError("face_plane arg not supported for this method")
        self.pending_edges.extend(objects)
