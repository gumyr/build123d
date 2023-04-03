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

    Create planar 2D sketches (objects with area but not volume) from faces or lines.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _tag = "BuildSketch"
    _obj_name = "sketch"
    _shape = Face
    _sub_class = Sketch

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
            for face in self._obj.faces():
                global_objs.append(plane.from_local_coords(face))
        return Sketch(Compound.make_compound(global_objs).wrapped)

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.workplanes = workplanes
        self.mode = mode
        self.sketch_local: Compound = None
        self.pending_edges: ShapeList[Edge] = ShapeList()
        super().__init__(*workplanes, mode=mode)

    def solids(self, *args):
        """solids() not implemented"""
        raise NotImplementedError("solids() doesn't apply to BuildSketch")

    def consolidate_edges(self) -> Union[Wire, list[Wire]]:
        """Unify pending edges into one or more Wires"""
        wires = Wire.combine(self.pending_edges)
        return wires if len(wires) > 1 else wires[0]

    def _add_to_pending(self, *objects: Edge):
        """Integrate a sequence of objects into existing builder object"""
        self.pending_edges.extend(objects)

    def _localize(
        self, objects: list[Union[Edge, Face, Wire]]
    ) -> list[Union[Edge, Face, Wire]]:
        """Align objects with Plane.XY"""

        aligned = []
        for obj in objects:
            if isinstance(obj, Face):
                plane = None if obj.is_coplanar(Plane.XY) else Plane(obj)
            elif isinstance(obj, Wire):
                try:
                    plane = Plane(Face.make_from_wires(obj.close()))
                except:
                    plane = None
            elif isinstance(obj, Edge):
                try:
                    plane = Plane(Face.make_from_wires(Wire.make_wire([obj]).close()))
                except:
                    plane = None
            else:
                raise ValueError(f"{obj} of type {type(obj).__name__} is unsupported")
            if plane is not None:
                aligned.append(plane.from_local_coords(obj))
                logger.info("%s realigned to Sketch's Plane", type(obj).__name__)

        return aligned
