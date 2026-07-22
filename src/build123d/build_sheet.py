"""
BuildSheet

name: build_sheet.py
by:   Gabriel Jesus
date: July 21st 2026

desc:
    This python module is a library used to build sheet metal parts.

license:

    Copyright 2026 Gabriel Jesus

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

from build123d.build_common import Builder, WorkplaneList
from build123d.build_enums import Mode
from build123d.geometry import Location, Plane
from build123d.topology import Compound, Edge, Face, Part, Solid, SkipClean, Wire


class BuildSheet(Builder[Part]):
    """BuildSheet

    Builder context for sheet metal parts of constant thickness. Closed
    sketch regions exiting into this context are automatically padded by
    ``thickness`` to form the base sheet. Sheet metal operations such as
    :func:`~operations_sheet.flange` and :func:`~operations_sheet.hem`
    fold walls from selected edges while preserving the bend topology.

    Note: the faces of sheet metal parts are deliberately NOT unified
    (cleaned) so that each bend keeps its own cylindrical and fan-shaped
    faces — required by future unfolding tools. Do not call ``clean()``
    on the resulting part.

    Args:
        workplanes (Plane, optional): initial plane to work on. Defaults to Plane.XY.
        thickness (float): sheet material thickness.
        bend_radius (float, optional): default inner bend radius for operations.
            Defaults to ``thickness``.
        k_factor (float, optional): neutral-axis position for future unfold
            calculations, 0 to 1. Defaults to 0.5.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _tag = "BuildSheet"
    _obj_name = "sheet"
    _shape = Solid
    _sub_class = Part

    def __init__(
        self,
        *workplanes: Face | Plane | Location,
        thickness: float,
        bend_radius: float | None = None,
        k_factor: float = 0.5,
        mode: Mode = Mode.ADD,
    ):
        if thickness <= 0:
            raise ValueError("thickness must be positive")
        if not 0.0 <= k_factor <= 1.0:
            raise ValueError("k_factor must be between 0 and 1")
        self.thickness = thickness
        self.bend_radius = thickness if bend_radius is None else bend_radius
        if self.bend_radius < 0:
            raise ValueError("bend_radius can't be negative")
        self.k_factor = k_factor
        self._sheet: Part | None = None
        self.pending_edges: list[Edge] = []
        self.pending_faces: list[Face] = []
        self.pending_face_planes: list[Plane] = []
        super().__init__(*workplanes, mode=mode)

    @property
    def sheet(self) -> Part | None:
        """Get the current sheet"""
        return self._sheet

    @sheet.setter
    def sheet(self, value: Part) -> None:
        """Set the current sheet"""
        self._sheet = value

    @property
    def _obj(self) -> Part | None:
        """Alias _obj to sheet"""
        return self._sheet

    @_obj.setter
    def _obj(self, value: Part) -> None:
        self._sheet = value

    @property
    def pending_edges_as_wire(self):
        """Return a wire representation of the pending edges"""
        return Wire.combine(self.pending_edges)[0]

    def _add_to_pending(self, *objects: Edge | Face, face_plane: Plane | None = None):
        """Store pending edges (for open profile operations)"""
        self.pending_edges.extend(o for o in objects if isinstance(o, Edge))

    def _add_to_context(
        self,
        *objects: Edge | Face | Solid | Compound,
        faces_to_pending: bool = True,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        """Add objects to the sheet.

        Faces (typically sketch regions, provided in local workplane
        coordinates) are padded by the sheet thickness into base solids.
        All boolean operations skip face unification to preserve bend
        topology.
        """
        faces: list[Face] = []
        others: list = []
        for obj in objects:
            if obj is None:
                continue
            if isinstance(obj, Face):
                faces.append(obj)
            elif isinstance(obj, Compound) and not obj.solids() and obj.faces():
                faces.extend(obj.faces())
            elif isinstance(obj, Compound) and not obj.solids() and not obj.faces():
                others.extend(obj.edges())
            else:
                others.append(obj)

        pads: list[Solid] = []
        if faces:
            for plane in WorkplaneList._get_context().workplanes:
                for face in faces:
                    global_face = plane.from_local_coords(face)
                    pads.append(
                        Solid.extrude(global_face, plane.z_dir * self.thickness)
                    )

        edges = [o for o in others if isinstance(o, Edge)]
        non_edges = [o for o in others if not isinstance(o, Edge)]
        with SkipClean():
            super()._add_to_context(
                *non_edges,
                *pads,
                faces_to_pending=faces_to_pending,
                clean=False,
                mode=mode,
            )
        if edges:
            self._add_to_pending(*edges)
