"""
build123d topology

name: history.py
by:   Gumyr
date: September 10, 2026

desc:
    What an operation did to the sub-shapes of its inputs, as the kernel
    reports it: which sub-shapes it left alone, which it rebuilt (modified),
    which it created from another (generated) and which it removed. Wraps
    OCCT's BRepTools_History so the record from one operation can be merged
    with the next and the chain read from the original inputs to the final
    result.

    The builders use this to answer Select.LAST and Select.NEW without
    comparing shapes before and after: a face the operation only trimmed is
    a modified face, not a new one.

license:

    Copyright 2026 Gumyr

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

from collections.abc import Callable, Iterable
from typing import Protocol

import OCP.TopAbs as ta
from OCP.BRepAlgoAPI import BRepAlgoAPI_BuilderAlgo
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.BRepTools import BRepTools_History
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.Standard import Standard_Failure
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape
from OCP.TopTools import (
    TopTools_DataMapOfShapeShape,
    TopTools_IndexedMapOfShape,
    TopTools_ListOfShape,
    TopTools_MapOfShape,
)
from typing_extensions import Self

from .kernel import list_shapes

# The sub-shape types BRepTools_History records; wires, shells and compounds
# are containers and are not tracked
TRACKED_TYPES = (ta.TopAbs_VERTEX, ta.TopAbs_EDGE, ta.TopAbs_FACE, ta.TopAbs_SOLID)


class MakeShapeLike(Protocol):
    """The history interface every BRepBuilderAPI_MakeShape descendant has."""

    # pylint: disable=invalid-name,missing-function-docstring
    def Generated(self, shape: TopoDS_Shape, /) -> TopTools_ListOfShape: ...
    def Modified(self, shape: TopoDS_Shape, /) -> TopTools_ListOfShape: ...


def _answers(
    query: Callable[[TopoDS_Shape], TopTools_ListOfShape], shape: TopoDS_Shape
) -> list[TopoDS_Shape]:
    """What an algorithm says about one sub-shape, or nothing if it will not say."""
    try:
        return list_shapes(query(shape))
    except Standard_Failure:
        return []


def tracked_subshapes(shapes: Iterable[TopoDS_Shape]) -> list[TopoDS_Shape]:
    """Every distinct vertex, edge, face and solid of the given shapes."""
    found = TopTools_IndexedMapOfShape()
    for shape in shapes:
        if shape is None or shape.IsNull():
            continue
        for shape_type in TRACKED_TYPES:
            TopExp.MapShapes_s(shape, shape_type, found)
    return [found(i + 1) for i in range(found.Extent())]


class ShapeHistory:
    """The record of what an operation did to its inputs' sub-shapes.

    Each tracked sub-shape of an input ends up in one of four states in the
    result: untouched (it is still there, unchanged), modified (rebuilt into
    one or more sub-shapes of the same kind), generating (a sub-shape of
    another kind was made from it, as a face is made from an edge by an
    extrusion) or removed. Booleans and ``ShapeUpgrade_UnifySameDomain``
    hand over a complete record; other algorithms answer per sub-shape and
    :meth:`from_algorithm` collects those answers.

    Records chain with :meth:`merge`, so that after a fuse and a clean a face
    of the original input still maps to the face it became.

    A record also knows which inputs were already there (``before``) and which
    the operation brought in (``brought``): for ``a + b`` the argument and the
    tool. That is what lets a sub-shape of the result be classified as last or
    new, see :meth:`is_last` and :meth:`is_new`.
    """

    def __init__(
        self,
        history: BRepTools_History | None = None,
        before: Iterable[TopoDS_Shape] = (),
        brought: Iterable[TopoDS_Shape] = (),
    ):
        self.wrapped = BRepTools_History() if history is None else history
        self.before: list[TopoDS_Shape] = list(before)
        self.brought: list[TopoDS_Shape] = list(brought)
        self._traces: tuple[Trace, Trace] | None = None

    # ---- Constructors ----

    @classmethod
    def from_boolean(
        cls,
        operation: BRepAlgoAPI_BuilderAlgo,
        before: Iterable[TopoDS_Shape] = (),
        brought: Iterable[TopoDS_Shape] = (),
    ) -> ShapeHistory:
        """The record a boolean operation (or splitter) kept while building."""
        return cls(operation.History(), before, brought)

    @classmethod
    def from_unify(cls, upgrader: ShapeUpgrade_UnifySameDomain) -> ShapeHistory:
        """The record of a ``clean``."""
        return cls(upgrader.History())

    @classmethod
    def from_algorithm(
        cls,
        algorithm: MakeShapeLike,
        inputs: Iterable[TopoDS_Shape],
        result: TopoDS_Shape,
    ) -> ShapeHistory:
        """Collect the per-sub-shape answers of a ``BRepBuilderAPI_MakeShape``.

        ``IsDeleted`` is not consulted: several algorithms answer it for the
        sub-shape kinds they track and guess for the rest, so a sub-shape is
        removed when it is neither still in ``result`` nor modified into
        something that is. An algorithm that raises when asked about a kind it
        does not track (``BRepFilletAPI_MakeFillet2d`` only answers for edges)
        is taken to have no answer for it.
        """
        inputs = list(inputs)
        history = cls(before=inputs)
        present = TopTools_MapOfShape()
        for sub in tracked_subshapes([result]):
            present.Add(sub)
        for sub in tracked_subshapes(inputs):
            modified = _answers(algorithm.Modified, sub)
            for shape in modified:
                history.wrapped.AddModified(sub, shape)
            for shape in _answers(algorithm.Generated, sub):
                if BRepTools_History.IsSupportedType_s(shape):
                    history.wrapped.AddGenerated(sub, shape)
            if not modified and not present.Contains(sub):
                history.wrapped.Remove(sub)
        return history

    @classmethod
    def from_sewing(
        cls, sewing: BRepBuilderAPI_Sewing, inputs: Iterable[TopoDS_Shape]
    ) -> ShapeHistory:
        """The record of sewing faces into a shell.

        Sewing reports faces it rebuilt through ``Modified`` and the edges and
        vertices it merged through ``ModifiedSubShape``; a face it dropped as a
        duplicate is neither, and is recorded as removed.
        """
        inputs = list(inputs)
        history = cls(before=inputs)
        present = TopTools_MapOfShape()
        for sub in tracked_subshapes([sewing.SewedShape()]):
            present.Add(sub)
        for sub in tracked_subshapes(inputs):
            if sub.ShapeType() == ta.TopAbs_FACE:
                if sewing.IsModified(sub):
                    history.wrapped.AddModified(sub, sewing.Modified(sub))
                elif not present.Contains(sub):
                    history.wrapped.Remove(sub)
            elif sewing.IsModifiedSubShape(sub):
                history.wrapped.AddModified(sub, sewing.ModifiedSubShape(sub))
            elif not present.Contains(sub):
                history.wrapped.Remove(sub)
        return history

    @classmethod
    def from_relocation(cls, before: TopoDS_Shape, after: TopoDS_Shape) -> ShapeHistory:
        """The record of moving a shape: each sub-shape modified into its moved self.

        A move keeps every TShape and changes only Locations, so the pairing is
        by TShape. Sub-shapes whose Location did not change are left untouched.
        """
        history = cls(before=[before])
        identity = TopLoc_Location()
        placed = TopTools_DataMapOfShapeShape()
        for sub in tracked_subshapes([after]):
            placed.Bind(sub.Located(identity), sub)
        for sub in tracked_subshapes([before]):
            key = sub.Located(identity)
            if placed.IsBound(key):
                moved = placed.Find(key)
                if not moved.IsSame(sub):
                    history.wrapped.AddModified(sub, moved)
        return history

    @classmethod
    def of(cls, *shapes: object) -> ShapeHistory | None:
        """The records the given shapes carry from the operations that made them,
        merged into one, or None if none of them carries one.

        A ``Shape`` made by an operation that records holds the record as
        ``_history``; anything else, including a list of shapes, is looked
        through for shapes that do.
        """
        found: list[ShapeHistory] = []
        for shape in shapes:
            if isinstance(shape, (list, tuple)):
                nested = cls.of(*shape)
                if nested is not None:
                    found.append(nested)
            else:
                history = getattr(shape, "_history", None)
                if isinstance(history, ShapeHistory):
                    found.append(history)
        if not found:
            return None
        if len(found) == 1:
            return found[0]
        merged = cls(
            before=[s for h in found for s in h.before],
            brought=[s for h in found for s in h.brought],
        )
        for history in found:
            merged.merge(history)
        return merged

    # ---- Instance Methods ----

    def add_modified(self, before: TopoDS_Shape, after: TopoDS_Shape) -> Self:
        """Record that ``before`` was rebuilt into ``after``.

        For what an algorithm did but does not say: ``BRepFilletAPI_MakeFillet2d``
        rebuilds the face it works on without reporting it.
        """
        if BRepTools_History.IsSupportedType_s(before):
            self.wrapped.AddModified(before, after)
        return self

    def merge(self, later: ShapeHistory | None) -> Self:
        """Extend this record with the operation that came after it."""
        if later is not None:
            self.wrapped.Merge(later.wrapped)
            self._traces = None
        return self

    def with_inputs(
        self, before: Iterable[TopoDS_Shape], brought: Iterable[TopoDS_Shape]
    ) -> Self:
        """Say which inputs were already there and which were brought in."""
        self.before = list(before)
        self.brought = list(brought)
        self._traces = None
        return self

    def _from(self) -> tuple[Trace, Trace]:
        """The record read from the result's side, for each set of inputs."""
        if self._traces is None:
            self._traces = (Trace(self, self.before), Trace(self, self.brought))
        return self._traces

    def is_last(self, shape: TopoDS_Shape) -> bool:
        """Did the operation bring this sub-shape of the result in, or create it?

        A sub-shape that descends from something brought in, untouched or
        rebuilt, is last, including one that also descends from what was there
        before, such as the vertex a new edge shares with an old one. One that
        descends only from what was there before is not. One the record cannot
        attribute to any input is new, and so last.
        """
        from_before, from_brought = self._from()
        if from_brought.is_untouched(shape) or from_brought.is_modified(shape):
            return True
        return not (from_before.is_untouched(shape) or from_before.is_modified(shape))

    def is_new(self, shape: TopoDS_Shape) -> bool:
        """Did this sub-shape of the result exist in no input, in any form?"""
        from_before, from_brought = self._from()
        for trace in (from_brought, from_before):
            if trace.is_untouched(shape) or trace.is_modified(shape):
                return False
        return True

    def modified(self, shape: TopoDS_Shape) -> list[TopoDS_Shape]:
        """What an input sub-shape was rebuilt into, if anything."""
        if not BRepTools_History.IsSupportedType_s(shape):
            return []
        return list_shapes(self.wrapped.Modified(shape))

    def generated(self, shape: TopoDS_Shape) -> list[TopoDS_Shape]:
        """What was made from an input sub-shape, if anything."""
        if not BRepTools_History.IsSupportedType_s(shape):
            return []
        return list_shapes(self.wrapped.Generated(shape))

    def is_removed(self, shape: TopoDS_Shape) -> bool:
        """Was an input sub-shape removed by the operation?"""
        return BRepTools_History.IsSupportedType_s(shape) and self.wrapped.IsRemoved(
            shape
        )

    def trace(self, inputs: Iterable[TopoDS_Shape]) -> Trace:
        """Index the record from the result's side for the given inputs."""
        return Trace(self, inputs)


class Trace:
    """The record of a :class:`ShapeHistory` read from the result's side.

    Built for a set of inputs, it answers for any sub-shape of the result
    whether it was one of those inputs' sub-shapes left untouched, was
    modified from one, or was generated from one.
    """

    def __init__(self, history: ShapeHistory, inputs: Iterable[TopoDS_Shape]):
        self.untouched = TopTools_MapOfShape()
        self.modified_from = TopTools_DataMapOfShapeShape()
        self.generated_from = TopTools_DataMapOfShapeShape()
        for sub in tracked_subshapes(inputs):
            self.untouched.Add(sub)
            for shape in history.modified(sub):
                self.modified_from.Bind(shape, sub)
            for shape in history.generated(sub):
                self.generated_from.Bind(shape, sub)

    def is_untouched(self, shape: TopoDS_Shape) -> bool:
        """Was this result sub-shape an input sub-shape, unchanged?"""
        return self.untouched.Contains(shape)

    def is_modified(self, shape: TopoDS_Shape) -> bool:
        """Was this result sub-shape rebuilt from an input sub-shape?"""
        return self.modified_from.IsBound(shape)

    def is_generated(self, shape: TopoDS_Shape) -> bool:
        """Was this result sub-shape made from an input sub-shape of another kind?"""
        return self.generated_from.IsBound(shape)

    def is_descendant(self, shape: TopoDS_Shape) -> bool:
        """Did this result sub-shape come from the inputs in any way?"""
        return (
            self.is_untouched(shape)
            or self.is_modified(shape)
            or self.is_generated(shape)
        )
