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


from build123d.build_common import BaseObject, Builder
from build123d.build_enums import GeomType, Mode, Select, SheetSurface
from build123d.geometry import Location, Plane
from build123d.sheet_utils import SheetMetalParameters
from build123d.topology import (
    Compound,
    Edge,
    Face,
    Shape,
    ShapeHistory,
    ShapeList,
    Shell,
    Solid,
    Wire,
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
    def sheet(self) -> Shell | Compound | None:
        """Get the placed reference shell, or None before anything is built.

        A single placement returns the Shell itself; multiple placements return
        a Compound holding one Shell per placement, matching how the other
        Builders publish placed output.
        """
        return self._output_obj()

    @sheet.setter
    def sheet(self, value: Shell) -> None:
        """Set the local reference shell."""
        self._sheet = value

    @property
    def sheet_local(self) -> Shell:
        """Get the reference shell in local construction coordinates.

        This is the shell the operations work on, so it is a Shell throughout -
        an empty one until the first face is added.
        """
        return self._sheet

    @property
    def _obj(self) -> Shell | None:
        """Alias the Builder object to the local reference shell.

        A shell with nothing in it reads as None, which is how the Builder
        machinery - and every other Builder's published output - says that
        nothing has been built.
        """
        return self._sheet if self._sheet else None

    @_obj.setter
    def _obj(self, value: Shell) -> None:
        self._sheet = value

    @property
    def pending_edges_as_wire(self) -> Wire | None:
        """Return pending edges as a wire, if present."""
        return Wire.combine(self.pending_edges)[0] if self.pending_edges else None

    def bends(self, select: Select = Select.ALL) -> ShapeList[Face]:
        """Return the bends of the sheet.

        The cylindrical faces of the reference shell, which is what every bend
        in it is - whether it came from a flange, a hem or a fold.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Face]: the sheet's bends
        """
        return self.faces(select).filter_by(GeomType.CYLINDER)

    def flats(self, select: Select = Select.ALL) -> ShapeList[Face]:
        """Return the flats of the sheet.

        The planar faces of the reference shell - the base, the walls, and
        anything else the bends join up.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Face]: the sheet's flat faces
        """
        return self.faces(select).filter_by(GeomType.PLANE)

    def fold_lines(self, select: Select = Select.ALL) -> ShapeList[Edge]:
        """Return the fold lines of the sheet.

        Straight edges shared by two coplanar flats - see
        :meth:`~topology.Shell.fold_lines`. To fold one, take it through the
        flat that stays: ``flats()[i].fold_lines()``.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: the sheet's fold lines
        """
        return self._sheet_edges(self.sheet_local.fold_lines(), select)

    def rims(self, select: Select = Select.ALL) -> ShapeList[Edge]:
        """Return the rims of the sheet.

        The free edges of its flats, what ``flange`` and ``hem`` consume - see
        :meth:`~topology.Shell.rims`.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: the sheet's rims
        """
        return self._sheet_edges(self.sheet_local.rims(), select)

    def _sheet_edges(self, edges: ShapeList[Edge], select: Select) -> ShapeList[Edge]:
        """Narrow a selection of the sheet's edges by what the last operation did."""
        if select == Select.ALL:
            return edges
        chosen = self.edges(select)
        return ShapeList(edge for edge in edges if any(edge.is_same(c) for c in chosen))

    def _publication_product(self) -> Shell:
        """Return the shell published to the parent Builder.

        The sheet parameters travel to the parent through
        ``Builder._accept_publication``, not on the Shell itself.
        """
        return self._sheet

    def _add_to_pending(self, *objects: Edge | Face, face_plane: Plane | None = None):
        """Store edges supplied by line builders."""
        self.pending_edges.extend(obj for obj in objects if isinstance(obj, Edge))

    def _accept_publication(
        self, build_product: Shape, source: Builder | None, mode: Mode
    ) -> None:
        """Receive a nested Builder's product, or an object drawn in this context.

        A sketch object drawn in a ``BuildSheet`` is a cutter, and only that:
        with ``Mode.SUBTRACT`` its faces trim the sheet faces they lie on, as a
        face published by a nested ``BuildSketch`` does, and a face lying on no
        sheet face is refused. Sheet material is drawn in a nested
        ``BuildSketch``, so any other mode is refused rather than letting the
        sheet accumulate 2D pieces the way a sketch does.
        """
        if (
            source is None
            and isinstance(build_product, BaseObject)
            and build_product._dim == 2
            and mode != Mode.SUBTRACT
        ):
            raise ValueError(
                "BuildSheet takes a sketch object only as a cutter, with "
                "Mode.SUBTRACT - draw sheet material in a nested BuildSketch"
            )
        self._add_to_context(build_product, mode=mode)

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
        incoming_shells: list[Shell] = []
        for obj in objects:
            if obj is None:
                continue
            if isinstance(obj, Face):
                incoming_faces.append(obj)
            elif isinstance(obj, Shell):
                incoming_shells.append(obj)
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
        before = [self._sheet.wrapped] if self._sheet else []

        # The sheet invariant - flats and bends sewn into one manifold shell -
        # lives on Shell; the builder only decides what goes in. Material
        # arriving in pieces is joined up; a replacement is a shell an
        # operation has already settled, so its coplanar seams are deliberate
        if mode == Mode.ADD:
            new_shell = Shell.make_sheet(
                existing_faces + incoming_faces, merge_coplanar=incoming_faces
            )
        elif mode == Mode.SUBTRACT:
            if not existing_faces:
                raise RuntimeError("Nothing to subtract from")
            new_shell = self._sheet.cut_sheet(*incoming_solids, *incoming_faces)
        elif mode == Mode.REPLACE:
            # an operation hands over the sheet it has already sewn, record and
            # all; anything else is sewn here
            if (
                len(incoming_shells) == 1
                and len(objects) == 1
                and incoming_shells[0]._history is not None
            ):
                new_shell = incoming_shells[0]
            else:
                new_shell = Shell.make_sheet(incoming_faces)
        elif mode == Mode.INTERSECT:
            raise ValueError("BuildSheet does not yet support Mode.INTERSECT")
        else:  # pragma: no cover - defensive for future Mode values
            raise ValueError(f"Unsupported BuildSheet mode {mode}")

        self._sheet = new_shell
        # the shell's record says what became of each face; the builder says
        # which faces were there before and which the operation brought in. A
        # replacement carries the faces it left alone, and the ones the record
        # traces back to a face that was there, along with the ones it made;
        # only the last are brought in
        record = (
            new_shell._history if new_shell._history is not None else ShapeHistory()
        )
        if mode == Mode.REPLACE:
            carried = [e.wrapped for e in existing_faces]
            carried += [m for e in existing_faces for m in record.modified(e.wrapped)]
            # a face the operation moved shares its shape with the one that was
            # there, but not its place, and is brought in like a new one
            brought = [
                f.wrapped
                for f in incoming_faces
                if not any(f.wrapped.IsSame(c) for c in carried)
            ]
        else:
            brought = [f.wrapped for f in incoming_faces]
        new_shell._made_by(record.with_inputs(before, brought))
