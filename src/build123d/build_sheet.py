"""
BuildSheet

name: build_sheet.py
by:   Gumyr & Gabriel Jesus
date: July 21st 2026

desc:
    This python module defines the surface-native sheet metal Builder.

license:

    Copyright 2026 Gumyr & Gabriel Jesus

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

from collections.abc import Iterable

from build123d.build_common import Builder
from build123d.build_enums import GeomType, Mode, SheetSurface
from build123d.geometry import TOLERANCE, Location, Plane
from build123d.sheet_utils import SheetMetalParameters
from build123d.topology import (
    Compound,
    Edge,
    Face,
    Shape,
    ShapeList,
    Shell,
    Solid,
    Vertex,
    Wire,
    topo_explore_connected_faces,
)


class BuildSheet(Builder[Shell]):
    """BuildSheet

    Builder context for constant-thickness sheet-metal parts. Construction is
    performed on a connected reference ``Shell`` containing planar and
    cylindrical faces. When nested in ``BuildPart``, the shell and its sheet
    parameters are published as pending input for the ``thicken`` operation.

    Args:
        placements (Plane, optional): output placement(s). Defaults to Plane.XY.
        thickness (float): sheet material thickness.
        bend_radius (float, optional): default physical inside bend radius.
            Defaults to ``thickness``.
        k_factor (float, optional): neutral-axis position from the locally
            concave material surface, from 0 to 1. Defaults to 0.5.
        sheet_surface (SheetSurface, optional): reference surface represented
            by the shell. Defaults to SheetSurface.INSIDE.
        mode (Mode, optional): publication combination mode. Defaults to Mode.ADD.
    """

    _tag = "BuildSheet"
    _obj_name = "sheet"
    _shape = Face
    _sub_class = Shell

    def __init__(
        self,
        *placements: Face | Plane | Location,
        thickness: float,
        bend_radius: float | None = None,
        k_factor: float = 0.5,
        sheet_surface: SheetSurface = SheetSurface.INSIDE,
        mode: Mode = Mode.ADD,
    ):
        self._sheet_parameters = SheetMetalParameters(
            thickness=thickness,
            bend_radius=bend_radius,
            k_factor=k_factor,
            sheet_surface=sheet_surface,
        )
        self._sheet = Shell()
        self.pending_edges: ShapeList[Edge] = ShapeList()
        super().__init__(*placements, mode=mode)

    @property
    def sheet_parameters(self) -> SheetMetalParameters:
        """Parameters relating the reference shell to its material."""
        return self._sheet_parameters

    @property
    def thickness(self) -> float:
        """Sheet material thickness."""
        return self._sheet_parameters.thickness

    @property
    def bend_radius(self) -> float:
        """Default physical inside bend radius."""
        return self._sheet_parameters.resolved_bend_radius

    @property
    def k_factor(self) -> float:
        """Neutral-axis position from the locally concave material surface."""
        return self._sheet_parameters.k_factor

    @property
    def sheet_surface(self) -> SheetSurface:
        """Reference surface represented by the shell."""
        return self._sheet_parameters.sheet_surface

    @property
    def sheet(self) -> Shell | Compound:
        """Get the placed reference shell.

        A single placement returns the Shell itself; multiple placements return
        a Compound holding one Shell per placement, matching how the other
        Builders publish placed output.
        """
        sheet = self._output_obj()
        assert isinstance(sheet, (Shell, Compound))
        return sheet

    @sheet.setter
    def sheet(self, value: Shell) -> None:
        """Set the local reference shell."""
        self._sheet = value

    @property
    def sheet_local(self) -> Shell:
        """Get the reference shell in local construction coordinates."""
        return self._sheet

    @property
    def _obj(self) -> Shell:
        """Alias the Builder object to the local reference shell."""
        return self._sheet

    @_obj.setter
    def _obj(self, value: Shell) -> None:
        self._sheet = value

    @property
    def pending_edges_as_wire(self) -> Wire | None:
        """Return pending edges as a wire, if present."""
        return Wire.combine(self.pending_edges)[0] if self.pending_edges else None

    def _publication_product(self) -> Shell:
        """Return the shell published to the parent Builder.

        The sheet parameters travel to the parent through
        ``Builder._accept_publication``, not on the Shell itself.
        """
        return self._sheet

    @staticmethod
    def _result_faces(result: Shape | Iterable[Shape]) -> list[Face]:
        """Extract faces from a surface boolean result."""
        if isinstance(result, Face):
            return [result]
        if isinstance(result, Shape):
            return list(result.faces())
        return [face for shape in result for face in shape.faces()]

    @staticmethod
    def _merge_coplanar_faces(faces: list[Face]) -> list[Face]:
        """Union touching coplanar faces while preserving other faces."""
        merged = list(faces)
        changed = True
        while changed:
            changed = False
            for i, first in enumerate(merged):
                if first.geom_type != GeomType.PLANE:
                    continue
                for j in range(i + 1, len(merged)):
                    second = merged[j]
                    if (
                        second.geom_type != GeomType.PLANE
                        or not first.is_coplanar(Plane(second))
                        or first.distance_to(second) > TOLERANCE
                    ):
                        continue
                    fused = first.fuse(second)
                    if isinstance(fused, Face):
                        merged[i] = fused
                        merged.pop(j)
                        changed = True
                        break
                if changed:
                    break
        return merged

    @classmethod
    def _cut_with_solids(cls, faces: list[Face], solids: list[Solid]) -> list[Face]:
        """Trim sheet faces with solid cutters.

        A Solid cuts every face it passes through, planar and cylindrical
        alike, so a cutout may cross a bend. Trimming changes the boundary of
        a face without changing its supporting surface, so the sheet keeps its
        planar and cylindrical geometry.

        The cutter must reach the reference surface, which for
        ``SheetSurface.INSIDE`` or ``OUTSIDE`` is one side of the material
        rather than the middle.
        """
        remaining: list[Face] = []
        for face in faces:
            remaining.extend(cls._result_faces(face.cut(*solids)))
        return remaining

    @classmethod
    def _cut_with_faces(cls, faces: list[Face], cutters: list[Face]) -> list[Face]:
        """Trim planar sheet faces with coplanar planar cutters.

        A Face only removes area from the sheet where the two are coplanar, so
        a cutter that matches no sheet face is rejected rather than silently
        ignored.
        """
        remaining: list[Face] = []
        used: set[int] = set()
        for face in faces:
            matching = [
                cutter
                for cutter in cutters
                if face.geom_type == GeomType.PLANE
                and cutter.geom_type == GeomType.PLANE
                and face.is_coplanar(Plane(cutter))
            ]
            used.update(id(cutter) for cutter in matching)
            remaining.extend(
                cls._result_faces(face.cut(*matching)) if matching else [face]
            )

        if len(used) != len({id(cutter) for cutter in cutters}):
            raise ValueError(
                "A Face cutter must be coplanar with a planar sheet face - use "
                "a Solid to cut across bends or curved faces"
            )
        return remaining

    @classmethod
    def _validated_shell(cls, faces: list[Face]) -> Shell:
        """Sew and validate candidate sheet faces."""
        if not faces:
            return Shell()

        for face in faces:
            if face.geom_type not in (GeomType.PLANE, GeomType.CYLINDER):
                raise ValueError(
                    "BuildSheet only supports planar and cylindrical faces"
                )
            if face.geom_type == GeomType.CYLINDER and (
                face.radius is None or face.radius <= 0
            ):
                raise ValueError("BuildSheet cylindrical faces need a positive radius")

        try:
            shell = Shell(cls._merge_coplanar_faces(faces))
        except (TypeError, ValueError) as exc:
            raise ValueError("Sheet faces must sew into one connected shell") from exc

        if not shell.is_valid:
            raise ValueError("Sheet faces produced an invalid shell")
        if any(
            len(topo_explore_connected_faces(edge, shell)) > 2 for edge in shell.edges()
        ):
            raise ValueError("Sheet faces produced non-manifold topology")
        return shell

    def _add_to_pending(self, *objects: Edge | Face, face_plane: Plane | None = None):
        """Store edges supplied by line builders."""
        self.pending_edges.extend(obj for obj in objects if isinstance(obj, Edge))

    def _add_to_context(
        self,
        *objects: Edge | Wire | Face | Shell | Solid | Compound,
        faces_to_pending: bool = True,
        clean: bool = True,
        mode: Mode = Mode.ADD,
    ):
        """Integrate faces into the continuously sewn reference shell."""
        del faces_to_pending, clean
        if mode == Mode.PRIVATE or not objects:
            return

        incoming_faces: list[Face] = []
        incoming_edges: list[Edge] = []
        incoming_solids: list[Solid] = []
        for obj in objects:
            if obj is None:
                continue
            if isinstance(obj, Face):
                incoming_faces.append(obj)
            elif isinstance(obj, Shell):
                incoming_faces.extend(obj.faces())
            elif isinstance(obj, (Edge, Wire)):
                incoming_edges.extend(obj.edges())
            elif isinstance(obj, Solid):
                incoming_solids.append(obj)
            elif isinstance(obj, Compound):
                if obj.solids():
                    incoming_solids.extend(obj.solids())
                else:
                    incoming_faces.extend(obj.faces())
                    incoming_edges.extend(obj.edges() if not obj.faces() else [])
            else:
                raise ValueError(
                    "BuildSheet only accepts Face, Sketch, Shell, or Solid inputs"
                )

        if incoming_solids and mode != Mode.SUBTRACT:
            raise ValueError(
                "BuildSheet accepts Solids only as cutters with Mode.SUBTRACT"
            )

        if incoming_edges:
            self._add_to_pending(*incoming_edges)
        if not incoming_faces and not incoming_solids:
            return

        self.obj_before = self._sheet
        self.to_combine = list(incoming_faces)
        existing_faces = list(self._sheet.faces()) if self._sheet else []

        if mode == Mode.ADD:
            candidate_faces = existing_faces + incoming_faces
        elif mode == Mode.SUBTRACT:
            if not existing_faces:
                raise RuntimeError("Nothing to subtract from")
            candidate_faces = existing_faces
            if incoming_solids:
                candidate_faces = self._cut_with_solids(
                    candidate_faces, incoming_solids
                )
            if incoming_faces:
                candidate_faces = self._cut_with_faces(candidate_faces, incoming_faces)
        elif mode == Mode.REPLACE:
            candidate_faces = incoming_faces
        elif mode == Mode.INTERSECT:
            raise ValueError("BuildSheet does not yet support Mode.INTERSECT")
        else:  # pragma: no cover - defensive for future Mode values
            raise ValueError(f"Unsupported BuildSheet mode {mode}")

        new_shell = self._validated_shell(candidate_faces)
        pre_faces = set(existing_faces)
        pre_edges = set(self._sheet.edges()) if self._sheet else set()
        self._sheet = new_shell
        self.lasts[Face] = ShapeList(set(new_shell.faces()) - pre_faces)
        self.lasts[Edge] = ShapeList(set(new_shell.edges()) - pre_edges)
        self.lasts[Vertex] = ShapeList()
        self.lasts[Solid] = ShapeList()
