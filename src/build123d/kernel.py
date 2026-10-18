"""
build123d

name: kernel.py
by:   Gumyr
date: September 10, 2026

desc:
    Stand-ins for the kernel binding, with no dependency on the rest of
    build123d so that any module can import them.

    This module is temporary: it carries build123d over to the calling
    conventions of the nanocct binding while the OCP binding is still in use.
    Once build123d runs on nanocct, each class below is the binding's own,
    ``list_shapes`` is ``list``, and this module goes away.

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

import io

from OCP.BinTools import BinTools as _BinTools
from OCP.BRep import BRep_Tool as _BRep_Tool
from OCP.BRepTools import BRepTools as _BRepTools
from OCP.collections import List_TopoDS_Shape
from OCP.Geom import Geom_Curve, Geom_Surface
from OCP.Geom2d import Geom2d_Curve
from OCP.STEPCAFControl import STEPCAFControl_Writer as _STEPCAFControl_Writer
from OCP.StlAPI import StlAPI_Writer as _StlAPI_Writer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Edge, TopoDS_Face, TopoDS_Shape


class BRep_Tool(_BRep_Tool):
    """OCP's ``BRep_Tool`` with nanocct's calling convention for the statics
    that have out-parameters.

    OCP keeps a C++ ``double&`` out-parameter as a dummy argument and returns
    only the handle; nanocct drops the argument and returns the value as part
    of a tuple, result first. The three methods below take the nanocct form
    so their call sites are already written for it. Every other static is
    inherited from OCP unchanged.
    """

    # the methods carry OCCT's names on purpose
    # pylint: disable=invalid-name

    @staticmethod
    def Curve_s(  # type: ignore[override]
        edge: TopoDS_Edge,
    ) -> tuple[Geom_Curve, float, float]:
        """The 3D curve of an edge and its parameter range."""
        first, last = _BRep_Tool.Range_s(edge)
        return _BRep_Tool.Curve_s(edge, first, last), first, last

    @staticmethod
    def CurveOnSurface_s(  # type: ignore[override]
        edge: TopoDS_Edge, face: TopoDS_Face
    ) -> tuple[Geom2d_Curve, float, float]:
        """The 2D curve of an edge on a face's surface and its parameter range."""
        first, last = _BRep_Tool.Range_s(edge, face)
        return _BRep_Tool.CurveOnSurface_s(edge, face, first, last), first, last

    @staticmethod
    def CurveOnPlane_s(  # type: ignore[override]
        edge: TopoDS_Edge, surface: Geom_Surface, location: TopLoc_Location
    ) -> tuple[Geom2d_Curve, float, float]:
        """The 2D curve of an edge projected on a plane and its parameter range."""
        first, last = _BRep_Tool.Range_s(edge)
        return (
            _BRep_Tool.CurveOnPlane_s(edge, surface, location, first, last),
            first,
            last,
        )


class BinTools(_BinTools):
    """OCP's ``BinTools`` with nanocct's calling convention for writing to
    memory.

    OCP writes a shape into a binary file-like object; nanocct returns the
    binary BREP as ``bytes`` when no file or stream is given. Every other
    form, a path or a stream, is OCP's own.
    """

    # the method carries OCCT's name on purpose
    # pylint: disable=invalid-name

    @staticmethod
    def Write_s(shape: TopoDS_Shape, *args, **kwargs):  # type: ignore[override]
        """The binary BREP of a shape as ``bytes``, or OCP's write to a path
        or stream when one is given."""
        if args or kwargs:
            return _BinTools.Write_s(shape, *args, **kwargs)
        stream = io.BytesIO()
        _BinTools.Write_s(shape, stream)
        return stream.getvalue()


class BRepTools(_BRepTools):
    """OCP's ``BRepTools`` with nanocct's calling convention for writing to
    memory.

    OCP writes a shape's text BREP into a binary file-like object; nanocct
    returns it as ``str`` when no file or stream is given. Every other form,
    a path or a stream, is OCP's own.
    """

    # the method carries OCCT's name on purpose
    # pylint: disable=invalid-name

    @staticmethod
    def Write_s(shape: TopoDS_Shape, *args, **kwargs):  # type: ignore[override]
        """The text BREP of a shape as ``str``, or OCP's write to a path or
        stream when one is given."""
        if args or kwargs:
            return _BRepTools.Write_s(shape, *args, **kwargs)
        stream = io.BytesIO()
        _BRepTools.Write_s(shape, stream)
        return stream.getvalue().decode()


class STEPCAFControl_Writer(_STEPCAFControl_Writer):
    """OCP's ``STEPCAFControl_Writer`` with nanocct's calling convention for
    writing to memory.

    OCP writes the STEP text into a binary file-like object and returns the
    status; nanocct takes no stream and returns the status and the text.
    """

    # the method carries OCCT's name on purpose
    # pylint: disable=invalid-name

    def WriteStream(self, *args, **kwargs):  # type: ignore[override]
        """The write status and the STEP text as ``str``, or OCP's write to
        a stream when one is given."""
        if args or kwargs:
            return super().WriteStream(*args, **kwargs)
        stream = io.BytesIO()
        status = super().WriteStream(stream)
        return status, stream.getvalue().decode()


class StlAPI_Writer(_StlAPI_Writer):
    """OCP's ``StlAPI_Writer`` with nanocct's setter for the ASCII mode.

    OCCT exposes the mode as a mutable reference, which OCP binds as the
    ``ASCIIMode`` property and nanocct as a ``SetASCIIMode`` method.
    """

    # the method carries OCCT's name on purpose
    # pylint: disable=invalid-name

    def SetASCIIMode(self, ascii_mode: bool) -> None:
        """Write ASCII rather than binary STL."""
        self.ASCIIMode = ascii_mode  # pylint: disable=attribute-defined-outside-init


def list_shapes(shapes: List_TopoDS_Shape) -> list[TopoDS_Shape]:
    """A kernel list as a Python list.

    Iterating a ``List_TopoDS_Shape`` through its Python protocol costs
    over a millisecond per list, even an empty one; popping a copy of it
    from the front costs microseconds.
    """
    found: list[TopoDS_Shape] = []
    remaining = List_TopoDS_Shape()
    remaining.Assign(shapes)
    while not remaining.IsEmpty():
        found.append(remaining.First())
        remaining.RemoveFirst()
    return found
