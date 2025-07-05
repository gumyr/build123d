"""
build123d topology

name: composite.py
by:   Gumyr
date: January 07, 2025

desc:

This module defines advanced composite geometric entities for the build123d CAD system. It
introduces the `Compound` class as a central concept for managing groups of shapes, alongside
specialized subclasses such as `Curve`, `Sketch`, and `Part` for 1D, 2D, and 3D objects,
respectively. These classes streamline the construction and manipulation of complex geometric
assemblies.

Key Features:
- **Compound Class**:
  - Represents a collection of geometric shapes (e.g., vertices, edges, faces, solids) grouped
    hierarchically.
  - Supports operations like adding, removing, and combining shapes, as well as querying volumes,
    centers, and intersections.
  - Provides utility methods for unwrapping nested compounds and generating 3D text or coordinate
    system triads.

- **Specialized Subclasses**:
  - `Curve`: Handles 1D objects like edges and wires.
  - `Sketch`: Focused on 2D objects, such as faces.
  - `Part`: Manages 3D solids and assemblies.

- **Advanced Features**:
  - Includes Boolean operations, hierarchy traversal, and bounding box-based intersection detection.
  - Supports transformations, child-parent relationships, and dynamic updates.

This module leverages OpenCascade for robust geometric operations while offering a Pythonic
interface for efficient and extensible CAD modeling workflows.

license:

    Copyright 2025 Gumyr

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

import copy
import os
import re
import sys
import warnings
from collections.abc import Iterable, Iterator, Sequence
from itertools import combinations
from typing import cast as tcast

from OCP.TopLoc import TopLoc_Location
from OCP.TopAbs import TopAbs_Orientation
import OCP.TopAbs as ta
from anytree import NodeMixin, PreOrderIter, RenderTree, search
from OCP.Bnd import Bnd_Box
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.Font import (
    Font_FA_Bold,
    Font_FA_BoldItalic,
    Font_FA_Italic,
    Font_FA_Regular,
    Font_FontMgr,
    Font_SystemFont,
)
from OCP.gp import gp_Ax3
from OCP.GProp import GProp_GProps
from OCP.Graphic3d import (
    Graphic3d_HTA_CENTER,
    Graphic3d_HTA_LEFT,
    Graphic3d_HTA_RIGHT,
    Graphic3d_VTA_BOTTOM,
    Graphic3d_VTA_CENTER,
    Graphic3d_VTA_TOP,
    Graphic3d_VTA_TOPFIRSTLINE,
)
from OCP.NCollection import NCollection_Utf8String
from OCP.StdPrs import StdPrs_BRepFont
from OCP.StdPrs import StdPrs_BRepTextBuilder as Font_BRepTextBuilder
from OCP.TCollection import TCollection_AsciiString
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Builder,
    TopoDS_Compound,
    TopoDS_Iterator,
    TopoDS_Shape,
)
from typing_extensions import Self

from build123d.build_enums import Align, CenterOf, FontStyle, TextAlign
from build123d.geometry import (
    TOLERANCE,
    Axis,
    BoundBox,
    Color,
    Location,
    Plane,
    Vector,
    VectorLike,
    logger,
)

from .one_d import Edge, Mixin1D, Wire
from .shape_core import (
    Joint,
    Shape,
    ShapeList,
    SkipClean,
    downcast,
    shapetype,
    topods_dim,
)
from .three_d import Mixin3D, Solid
from .two_d import Face, Shell
from .utils import (
    _extrude_topods_shape,
    _make_topods_compound_from_shapes,
    tuplify,
    unwrapped_shapetype,
)
from .zero_d import Vertex

import inspect


def where_am_i_called_from(stack_levels: int = 2):
    # inspect.stack()[0] is this frame; [2] is the caller
    caller_frame_info = inspect.stack()[stack_levels]
    filename = caller_frame_info.filename
    lineno = caller_frame_info.lineno
    code_line = caller_frame_info.code_context[0].strip()
    print(f"Called from {filename}:{lineno} -> {code_line}")


class MixinComposite(NodeMixin):

    @property
    def volume(self) -> float:
        """volume - the volume of this Assembly/Compound"""
        # when density == 1, mass == volume
        obj = Compound(self) if isinstance(self, Assembly) else self
        return sum(i.volume for i in [*obj.get_type(Solid), *obj.get_type(Shell)])

    def _rebuild_tree(self):
        """
        Rebuild the OCCT Compound tree hierarchy from the root exactly mirroring the
        anytree structure.
        """

        def _rebuild(node: Shape, indent="") -> TopoDS_Shape:
            # List of shapes to add to current node's compound
            topods_shapes: list[TopoDS_Shape] = []

            logger.debug("%sRebuilding node: %s", indent, node.label)
            # If this is a leaf node or has been rebuilt, return it
            if not isinstance(node, (Assembly, Compound)):
                logger.debug(
                    "%sFinished node: %s, total shapes: %i",
                    indent,
                    node.label,
                    len(topods_shapes),
                )
                return node.wrapped

            # Save original location and orientation
            original_location = (
                node.wrapped.Location() if node.wrapped else TopLoc_Location()
            )
            original_orientation = (
                node.wrapped.Orientation()
                if node.wrapped is not None
                else TopAbs_Orientation.TopAbs_FORWARD
            )

            # Include node's own geometry if available
            if hasattr(node, "_base_wrapped") and node._base_wrapped is not None:
                logger.debug("%snode: %s has base shapes", indent, node.label)
                # Get base TopoDS_Shapes
                base_shapes = []
                iterator = TopoDS_Iterator(node._base_wrapped)
                while iterator.More():
                    base_shapes.append(iterator.Value())
                    iterator.Next()
                topods_shapes.extend(base_shapes)

            # Recurse into children and rebuild them
            if node.children:
                kids = [kid.label for kid in node.children]
                logger.debug(
                    "%snode: %s has %i children %s",
                    indent,
                    node.label,
                    len(node.children),
                    kids,
                )
                children = [_rebuild(child, indent + "  ") for child in node.children]
                topods_shapes.extend(children)

            # Wrap current node into a compound to preserve hierarchy if it has children
            if not topods_shapes:
                node.wrapped = None
            else:
                node.wrapped = _make_topods_compound_from_shapes(topods_shapes)

            # Restore original location/orientation
            if node.wrapped is not None:
                node.wrapped.Location(original_location)
                node.wrapped.Orientation(original_orientation)

            logger.debug(
                "%sFinished node: %s, total shapes: %i",
                indent,
                node.label,
                len(topods_shapes),
            )
            return node.wrapped

        _rebuild(self.root)

    def _post_attach(self, parent: MixinComposite):
        logger.debug(
            "Updated parent of %s to %s", self.label, parent.label, stacklevel=4
        )
        self._rebuild_tree()

    def _post_attach_children(self, children: tuple[Assembly | Shape]):
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Adding children %s to %s", kids, self.label, stacklevel=5)
            self._rebuild_tree()

    def _post_detach(self, parent: MixinComposite):
        logger.debug("Removing parent of %s (%s)", self.label, parent.label)
        self._rebuild_tree()

    def _post_detach_children(self, children: tuple[Assembly | Shape]):
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Removing children %s from %s", kids, self.label)
            self._rebuild_tree()

    def _pre_attach(self, parent: Assembly | Compound):
        """Method call before attaching to `parent`."""
        if not isinstance(parent, (Assembly, Compound)):
            raise ValueError("`parent` must be of type Compound")

    def _pre_attach_children(self, children: tuple[Assembly | Shape]):
        """Method call before attaching `children`."""
        if not all(isinstance(child, (Assembly | Shape)) for child in children):
            raise ValueError("Each child must be of type Assembly or Shape")


class Assembly(MixinComposite):
    """
    The Assembly class in build123d represents a hierarchical grouping of geometric
    shapes and subassemblies. Assembly supports metadata such as labels, materials,
    joints, and parent-child relationships, enabling users to build structured, semantic
    models. Each Assembly can contain one or more Shape or Assembly instances,
    allowing for deeply nested assemblies that reflect real-world part hierarchies.

    The class leverages anytree to manage the tree structure and provides intuitive
    access through label-based indexing (__getitem__, __contains__) and iteration.
    While assemblies are immutable from a geometric modeling perspective, their
    structure can be manipulated programmatically—shapes can be added, searched, or
    replaced with control over how changes affect the overall model.

    Assemblies maintain a .wrapped attribute (a TopoDS_Compound) representing the
    combined geometry of all children, allowing export or visualization through
    OpenCascade. This makes Assembly a powerful tool for managing complex designs,
    modular CAD components, and downstream operations like exploded views, BOM
    generation, or simulation boundary conditions.
    """

    @property
    def _dim(self) -> int | None:
        """The dimension of the shapes within the Assembly - None if inconsistent"""
        return topods_dim(self.wrapped)

    def __init__(
        self,
        objs: Assembly | Shape | Iterable[Assembly | Shape] | None = None,
        label: str | None = "",
        color: Color | None = None,
        material: str | None = "",
        joints: dict[str, Joint] | None = None,
        parent: Assembly | None = None,
        location: Location | None = None,
    ):
        """Assembly Constructor

        Args:
            objs (Assembly | Shape | Iterable[Assembly  |  Shape] | None, optional): Shapes
                or Assemblies initially populate this assembly. Defaults to None.
            label (str, optional): Defaults to ''.
            color ('Color', optional): Defaults to None.
            material (str, optional): tag for external tools. Defaults to ''.
            joints (dict[str, Joint], optional): names joints. Defaults to None.
            parent (Assembly, optional): assembly parent. Defaults to None.
        """
        self.label = label
        self._color = color
        self.material = "" if material is None else material
        self.joints = {} if joints is None else joints
        self.location_relative_to_parent = None
        self.wrapped = _make_topods_compound_from_shapes([])
        self._base_wrapped = self.wrapped

        if isinstance(objs, Shape):
            self.children = [objs]  # this calls _post_attach_children
        elif isinstance(objs, Iterable):
            self.children = list(objs)  # this calls _post_attach_children

        if parent is not None:
            self.parent = parent  # this calls _post_attach

        # if location is not None:
        #     self.location = location.inverse() * self.location

    @property
    def color(self) -> None | Color:
        """Get the assembly's color.  If it's None, get the color of the nearest
        ancestor, assign it to this Shape and return this value."""
        # Find the correct color for this node
        if self._color is None:
            # Find parent color
            current_node: Assembly | Shape | None = self
            while current_node is not None:
                parent_color = current_node._color
                if parent_color is not None:
                    break
                current_node = current_node.parent
            node_color = parent_color
        else:
            node_color = self._color
        self._color = node_color  # Set the node's color for next time
        return node_color

    @color.setter
    def color(self, value):
        """Set the shape's color"""
        self._color = value

    @property
    def location(self) -> Location:
        """Get this Shape's Location"""
        return Location(self.wrapped.Location())

    @location.setter
    def location(self, value: Location):
        """Set Shape's Location to value"""
        self.wrapped.Location(value.wrapped)

    @property
    def position(self) -> Vector:
        """Get the position component of this Shape's Location"""
        return self.location.position

    @position.setter
    def position(self, value: VectorLike):
        """Set the position component of this Shape's Location to value"""
        loc = self.location
        loc.position = value
        self.location = loc

    @property
    def orientation(self) -> Vector:
        """Get the orientation component of this Shape's Location"""
        return self.location.orientation

    @orientation.setter
    def orientation(self, rotations: VectorLike):
        """Set the orientation component of this Shape's Location to rotations"""
        loc = self.location
        loc.orientation = rotations
        self.location = loc

    @property
    def root(self) -> Assembly:
        """Return the top-most Assembly in this tree."""
        return super().root  # type: ignore[return-value]

    def __repr__(self) -> str:
        """Return a tree-style representation of the assembly"""
        lines = []
        for pre, _, node in RenderTree(self):
            label = getattr(node, "label", "")
            shape_type = type(node).__name__
            summary = f"{shape_type}({label})" if label else shape_type
            if hasattr(node, "wrapped") and node.wrapped is not None:
                try:
                    node_center = node.center()
                    summary += f", Center({node_center.X:.2f}, {node_center.Y:.2f}, {node_center.Z:.2f})"
                    summary += f", Volume({node.volume:.2f})"
                except Exception:
                    pass
            lines.append(f"{pre}{summary}")
        return "\n".join(lines)

    def __add__(self, part: Shape):
        self.children = list(self.children) + [part]
        return self

    def __getitem__(self, label: str) -> Assembly | Shape | tuple[Assembly | Shape]:
        """Retrieve a part by its label or a slash-separated path with optional indexing.

        Examples:
            a["bracket"]             # Returns first node with label 'bracket'
            a["bracket/bolt"]        # Returns first 'bolt' under 'bracket'
            a["bracket/bolt[1]"]     # Returns second 'bolt' under 'bracket'
        """

        def _parse_label_index(segment: str) -> tuple[str, int | None]:
            match = re.fullmatch(r"([^[]+)(?:\[(\d+)\])?", segment)
            if not match:
                raise KeyError(f"Invalid segment syntax: '{segment}'")
            label = match.group(1)
            index = int(match.group(2)) if match.group(2) is not None else None
            return label, index

        def _get_node_by_path(root: NodeMixin, path: str, sep: str = "/") -> NodeMixin:
            node = root
            for segment in path.strip(sep).split(sep):
                label, index = _parse_label_index(segment)
                matches = [
                    child
                    for child in node.children
                    if getattr(child, "label", None) == label
                ]
                if not matches:
                    raise KeyError(f"No node with label '{label}' under '{node.label}'")
                if index is None:
                    node = matches[0]
                elif index < len(matches):
                    node = matches[index]
                else:
                    raise IndexError(
                        f"Index [{index}] out of range for '{label}' under '{node.label}'"
                    )
            return node

        if "/" in label:
            return _get_node_by_path(self, label)
        else:
            label_name, index = _parse_label_index(label)
            matches = search.findall(
                self, filter_=lambda node: node.label == label_name
            )
            if not matches:
                raise KeyError(f"No node found with label: {label_name}")
            if index is None:
                return matches[0] if len(matches) == 1 else matches
            if index < len(matches):
                return matches[index]
            else:
                raise IndexError(
                    f"Index [{index}] out of range for label '{label_name}'"
                )

    def __contains__(self, label) -> bool:
        """Check if a part exists in the assembly by its label."""
        result = search.findall(self, filter_=lambda node: node.label == label)
        return len(result) != 0

    def __iter__(self) -> Iterator[Shape]:
        """Iterate over all nodes in the assembly tree (including self)"""
        return iter(PreOrderIter(self))

    def __len__(self) -> int:
        """Return the number of subshapes"""
        count = 0
        if self.wrapped is not None:
            for _ in self:
                count += 1
        return count

    def __bool__(self) -> bool:
        """Check if empty."""
        return TopoDS_Iterator(self.wrapped).More()

    def __copy__(self) -> Self:
        """Return shallow copy or reference of self

        Create an copy of this Assembly that shares the underlying TopoDS_TShape.

        Used when there is a need for many objects with the same CAD structure but at
        different Locations, etc. - for examples fasteners in a larger assembly. By
        sharing the TopoDS_TShape, the memory size of such assemblies can be greatly reduced.

        Changes to the CAD structure of the base object will be reflected in all instances.
        """
        reference = copy.deepcopy(self)
        if self.wrapped is not None:
            assert (
                reference.wrapped is not None
            )  # Ensure mypy knows reference.wrapped is not None
            reference.wrapped.TShape(self.wrapped.TShape())
        return reference

    def __deepcopy__(self, memo) -> Self:
        """Return deepcopy of self"""
        # The wrapped object is a OCCT TopoDS_Shape which can't be pickled or copied
        # with the standard python copy/deepcopy, so create a deepcopy 'memo' with this
        # value already copied which causes deepcopy to skip it.
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        if self.wrapped is not None:
            memo[id(self.wrapped)] = downcast(BRepBuilderAPI_Copy(self.wrapped).Shape())
        for key, value in self.__dict__.items():
            if key == "topo_parent":
                result.topo_parent = value
            else:
                setattr(result, key, copy.deepcopy(value, memo))
            if key == "joints":
                for joint in result.joints.values():
                    joint.parent = result
        return result

    # def _post_attach(self, parent: Assembly):
    #     parent.wrapped = parent._update_wrapped(nested_children=False)
    #     node: Assembly | Compound = parent.parent
    #     while node is not None:
    #         node.wrapped = node._update_wrapped(nested_children=False)
    #         node = node.parent

    # def _post_attach_children(self, children: Iterable[Shape]):
    #     if children:
    #         self.wrapped = self._update_wrapped(nested_children=False)
    #         node: Assembly | Compound = self.parent
    #         while node is not None:
    #             node.wrapped = node._update_wrapped(nested_children=False)
    #             node = node.parent

    # def _post_attach(self, parent: Assembly):
    #     """Method call after attaching to `parent`."""
    #     logger.debug(
    #         "Updated parent of %s to %s", self.label, parent.label, stacklevel=4
    #     )
    #     base = getattr(parent, "_base_wrapped", None)
    #     shapes = ([base] if base else []) + [c.wrapped for c in parent.children]
    #     parent.wrapped = _make_topods_compound_from_shapes(shapes)

    #     # now walk up and rebuild every ancestor
    #     node = parent.parent
    #     while node is not None:
    #         base = getattr(node, "_base_wrapped", None)
    #         shapes = ([base] if base else []) + [c.wrapped for c in node.children]
    #         node.wrapped = _make_topods_compound_from_shapes(shapes)
    #         node = node.parent

    # def _post_attach_children(self, children: Iterable[Shape]):
    #     """Method call after attaching `children`."""
    #     if children:
    #         kids = ",".join([child.label for child in children])
    #         logger.debug("Adding children %s to %s", kids, self.label, stacklevel=5)
    #         # self.wrapped = self._update_wrapped()
    #         # self.wrapped = _make_topods_compound_from_shapes(
    #         #     [self._base_wrapped, *[c.wrapped for c in children]]
    #         # )
    #         base = getattr(self, "_base_wrapped", None)
    #         shapes = ([base] if base else []) + [c.wrapped for c in self.children]
    #         self.wrapped = _make_topods_compound_from_shapes(shapes)

    #         # now walk up and rebuild every ancestor
    #         node = self.parent
    #         while node is not None:
    #             base = getattr(node, "_base_wrapped", None)
    #             shapes = ([base] if base else []) + [c.wrapped for c in node.children]
    #             node.wrapped = _make_topods_compound_from_shapes(shapes)
    #             node = node.parent

    #     # else:
    #     #     logger.debug("Adding no children to %s", self.label)

    # def _post_detach(self, parent: Assembly):
    #     """Method call after detaching from `parent`."""
    #     logger.debug("Removing parent of %s (%s)", self.label, parent.label)
    #     if parent.children:
    #         # parent.wrapped = _make_topods_compound_from_shapes(
    #         #     [c.wrapped for c in parent.children]
    #         # )
    #         parent.wrapped = _make_topods_compound_from_shapes(
    #             [parent.wrapped, *[c.wrapped for c in parent.children]]
    #         )
    #     else:
    #         parent.wrapped = None

    # def _post_detach_children(self, children):
    #     """Method call before detaching `children`."""
    #     if children:
    #         kids = ",".join([child.label for child in children])
    #         logger.debug("Removing children %s from %s", kids, self.label)
    #         self.wrapped = _make_topods_compound_from_shapes(
    #             [c.wrapped for c in self.children]
    #         )
    #     # else:
    #     #     logger.debug("Removing no children from %s", self.label)

    # def _pre_attach(self, parent: Assembly):
    #     """Method call before attaching to `parent`."""
    #     if not isinstance(parent, Assembly):
    #         raise ValueError("`parent` must be of type Compound")

    # def _pre_attach_children(self, children):
    #     """Method call before attaching `children`."""
    #     if not all(isinstance(child, (Assembly | Shape)) for child in children):
    #         raise ValueError("Each child must be of type Assembly or Shape")

    # def _update_wrapped(self, *, nested_children: bool = False) -> Compound:
    #     """Rebuild the OCCT compound, optionally nesting children in a sub-compound.

    #     Args:
    #         nested_children (bool): If True, group children in a sub-compound.
    #                                 If False, all shapes are added at the same level.
    #     """
    #     builder = TopoDS_Builder()
    #     compound = TopoDS_Compound()
    #     builder.MakeCompound(compound)

    #     # Add children
    #     if self.children:
    #         if nested_children:
    #             child_compound = _make_topods_compound_from_shapes(
    #                 [child.wrapped for child in self.children]
    #             )
    #             builder.Add(compound, child_compound)
    #         else:
    #             for child in self.children:
    #                 if child.wrapped:
    #                     builder.Add(compound, child.wrapped)

    #     # self.wrapped = compound
    #     return compound

    def bounding_box(
        self, tolerance: float = TOLERANCE, optimal: bool = True
    ) -> BoundBox:
        """Create a bounding box for this Assembly.

        Args:
            tolerance (float, optional): Defaults to TOLERANCE.

        Returns:
            BoundBox: A box sized to contain this Shape
        """
        if self.wrapped is None:
            return BoundBox(Bnd_Box())
        return BoundBox.from_topo_ds(self.wrapped, tolerance=tolerance, optimal=optimal)

    def clone(
        self,
        label: str | None = None,
        color: Color | None = None,
        material: str | None = None,
        parent: Assembly | None = None,
        location: Location | None = None,
    ):
        """clone

        Create a shallow copy of an Assembly with new attributes. If an attribute
        is not assigned a new value the value from self will be used.

        Args:
            label (str | None, optional): new label. Defaults to None.
            color (Color | None, optional): new color. Defaults to None.
            material (str | None, optional): new material. Defaults to None.
            parent (Assembly | None, optional): new parent. Defaults to None.
            location (Location | None, optional): new location. Defaults to None.

        Returns:
            Assembly: copy with potentially new attributes
        """
        new_assembly = copy.copy(self)

        if label is not None:
            new_assembly.label = label

        if color is not None:
            new_assembly.color = color

        if material is not None:
            new_assembly.material = material

        if parent is not None:
            new_assembly.parent = parent

        if location is not None:
            new_assembly.location = location.inverse() * new_assembly.location

        return new_assembly

    def locate(self, loc: Location) -> Self:
        """Apply a location in absolute sense to self

        Args:
          loc: Location:

        Returns:

        """
        if self.wrapped is None:
            raise ValueError("Cannot locate an empty Assembly")
        if loc.wrapped is None:
            raise ValueError("Cannot locate a Assembly at an empty location")
        self.wrapped.Location(loc.wrapped)

        return self

    def located(self, loc: Location) -> Self:
        """located

        Apply a location in absolute sense to a copy of self

        Args:
            loc (Location): new absolute location

        Returns:
            Assembly: copy of Assembly at location
        """
        if self.wrapped is None:
            raise ValueError("Cannot locate an empty Assembly")
        if loc.wrapped is None:
            raise ValueError("Cannot locate a Assembly at an empty location")
        assembly_copy: Shape = copy.deepcopy(self, None)
        assembly_copy.wrapped.Location(loc.wrapped)  # type: ignore
        return assembly_copy

    def move(self, loc: Location) -> Self:
        """Apply a location in relative sense (i.e. update current location) to self

        Args:
          loc: Location:

        Returns:

        """
        if self.wrapped is None:
            raise ValueError("Cannot move an empty shAssemblyape")
        if loc.wrapped is None:
            raise ValueError("Cannot move a Assembly at an empty location")

        self.wrapped.Move(loc.wrapped)

        return self

    def moved(self, loc: Location) -> Self:
        """moved

        Apply a location in relative sense (i.e. update current location) to a copy of self

        Args:
            loc (Location): new location relative to current location

        Returns:
            Assembly: copy of Assembly moved to relative location
        """
        if self.wrapped is None:
            raise ValueError("Cannot move an empty shape")
        if loc.wrapped is None:
            raise ValueError("Cannot move a shape at an empty location")
        shape_copy: Shape = copy.deepcopy(self, None)
        shape_copy.wrapped = tcast(
            TopoDS_Shape, downcast(self.wrapped.Moved(loc.wrapped))
        )
        return shape_copy

    def remove(self, label: str, *, all_matches: bool = False):
        """Remove child node(s) by label."""
        matches = search.findall(self, filter_=lambda n: n.label == label)
        if not matches:
            raise KeyError(f"No child with label '{label}'")
        if not all_matches and len(matches) > 1:
            raise ValueError(
                f"Multiple nodes with label '{label}'; use all_matches=True"
            )
        for node in matches:
            node.parent = None


class Compound(Mixin3D, MixinComposite, Shape[TopoDS_Compound]):
    """A Compound in build123d is a topological entity representing a collection of
    geometric shapes grouped together within a single structure. It serves as a
    container for organizing diverse shapes like edges, faces, or solids. This
    hierarchical arrangement facilitates the construction of complex models by
    combining simpler shapes. Compound plays a pivotal role in managing the
    composition and structure of intricate 3D models in computer-aided design
    (CAD) applications, allowing engineers and designers to work with assemblies
    of shapes as unified entities for efficient modeling and analysis."""

    order = 4.0

    project_to_viewport = Mixin1D.project_to_viewport
    # ---- Constructor ----

    def __init__(
        self,
        obj: TopoDS_Compound | Iterable[Shape] | None = None,
        label: str = "",
        color: Color | None = None,
        material: str = "",
        joints: dict[str, Joint] | None = None,
        parent: Compound | None = None,
        children: Sequence[Shape] | None = None,
    ):
        """Build a Compound from Shapes

        Args:
            obj (TopoDS_Compound | Iterable[Shape], optional): OCCT Compound or shapes
            label (str, optional): Defaults to ''.
            color (Color, optional): Defaults to None.
            material (str, optional): tag for external tools. Defaults to ''.
            joints (dict[str, Joint], optional): names joints. Defaults to None.
            parent (Compound, optional): assembly parent. Defaults to None.
            children (Sequence[Shape], optional): assembly children. Defaults to None.
        """
        if isinstance(obj, TopoDS_Shape):
            # TODO: consider using Compound.cast(obj) to check if obj is really a
            # TopoDS_Compound or another type of TopoDS_Shape
            topods_compound = downcast(obj)
        elif isinstance(obj, Iterable):
            topods_compound = _make_topods_compound_from_shapes(
                [s.wrapped for s in obj]
            )
        elif obj is None:
            # When used in a Part/Sketch etc. context an empty Compound must
            # have a wrapped attribute of None
            topods_compound = None
        elif isinstance(obj, Assembly):
            topods_compound = obj.wrapped
        else:
            raise ValueError(f"Invalid obj of type {type(obj)}")

        super().__init__(
            obj=topods_compound,
            label=label,
            color=color,
            parent=parent,
        )
        # When used in an assembly context the base shape must be a valid
        # compound in order to add children or set a parent
        self._base_wrapped = (
            _make_topods_compound_from_shapes([])
            if topods_compound is None
            else topods_compound
        )

        self.material = "" if material is None else material
        self.joints = {} if joints is None else joints

        # Note that NodeMixin initialized children to ()
        if children:
            self.children = children  # invokes _post_attach_children

    # ---- Properties ----

    @property
    def _dim(self) -> int | None:
        """The dimension of the shapes within the Compound - None if inconsistent"""
        if self.wrapped is None:
            return None
        return topods_dim(self.wrapped)

    @property
    def root(self) -> Compound | Assembly:
        """Return the top-most node (Assembly or Compound) in this hierarchy."""
        return super().root  # type: ignore[return-value]

    # ---- Class Methods ----

    @classmethod
    def cast(
        cls, obj: TopoDS_Shape
    ) -> Vertex | Edge | Wire | Face | Shell | Solid | Compound:
        "Returns the right type of wrapper, given a OCCT object"

        # define the shape lookup table for casting
        constructor_lut = {
            ta.TopAbs_VERTEX: Vertex,
            ta.TopAbs_EDGE: Edge,
            ta.TopAbs_WIRE: Wire,
            ta.TopAbs_FACE: Face,
            ta.TopAbs_SHELL: Shell,
            ta.TopAbs_SOLID: Solid,
            ta.TopAbs_COMPOUND: Compound,
            ta.TopAbs_COMPSOLID: Compound,
        }

        shape_type = shapetype(obj)
        # NB downcast is needed to handle TopoDS_Shape types
        return constructor_lut[shape_type](downcast(obj))

    @classmethod
    def extrude(cls, obj: Shell, direction: VectorLike) -> Compound:
        """extrude

        Extrude a Shell into a Compound.

        Args:
            direction (VectorLike): direction and magnitude of extrusion

        Raises:
            ValueError: Unsupported class
            RuntimeError: Generated invalid result

        Returns:
            Edge: extruded shape
        """
        if obj.wrapped is None:
            return Compound()
        return Compound(
            TopoDS.Compound_s(_extrude_topods_shape(obj.wrapped, direction))
        )

    @classmethod
    def make_text(
        cls,
        txt: str,
        font_size: float,
        font: str = "Arial",
        font_path: str | None = None,
        font_style: FontStyle = FontStyle.REGULAR,
        text_align: tuple[TextAlign, TextAlign] = (TextAlign.CENTER, TextAlign.CENTER),
        align: Align | tuple[Align, Align] | None = None,
        position_on_path: float = 0.0,
        text_path: Edge | Wire | None = None,
    ) -> Compound:
        """2D Text that optionally follows a path.

        The text that is created can be combined as with other sketch features by specifying
        a mode or rotated by the given angle.  In addition, edges have been previously created
        with arc or segment, the text will follow the path defined by these edges. The start
        parameter can be used to shift the text along the path to achieve precise positioning.

        Args:
            txt: text to be rendered
            font_size: size of the font in model units
            font: font name
            font_path: path to font file
            font_style: text style. Defaults to FontStyle.REGULAR
            text_align (tuple[TextAlign, TextAlign], optional): horizontal text align
                LEFT, CENTER, or RIGHT. Vertical text align BOTTOM, CENTER, TOP, or
                TOPFIRSTLINE. Defaults to (TextAlign.CENTER, TextAlign.CENTER)
            align (Union[Align, tuple[Align, Align]], optional): align min, center, or max
                of object. Defaults to None
            position_on_path: the relative location on path to position the text,
                between 0.0 and 1.0. Defaults to 0.0
            text_path: a path for the text to follows. Defaults to None (linear text)

        Returns:
            a Compound object containing multiple Faces representing the text

        Examples::

            fox = Compound.make_text(
                txt="The quick brown fox jumped over the lazy dog",
                font_size=10,
                position_on_path=0.1,
                text_path=jump_edge,
            )

        """
        # pylint: disable=too-many-locals

        def position_face(orig_face: Face) -> Face:
            """
            Reposition a face to the provided path

            Local coordinates are used to calculate the position of the face
            relative to the path. Global coordinates to position the face.
            """
            assert text_path is not None
            bbox = orig_face.bounding_box()
            face_bottom_center = Vector((bbox.min.X + bbox.max.X) / 2, 0, 0)
            relative_position_on_wire = (
                position_on_path + face_bottom_center.X / path_length
            )
            wire_tangent = text_path.tangent_at(relative_position_on_wire)
            wire_angle = Vector(1, 0, 0).get_signed_angle(wire_tangent)
            wire_position = text_path.position_at(relative_position_on_wire)

            return orig_face.translate(wire_position - face_bottom_center).rotate(
                Axis(wire_position, (0, 0, 1)),
                -wire_angle,
            )

        if sys.platform.startswith("linux"):
            os.environ["FONTCONFIG_FILE"] = "/etc/fonts/fonts.conf"
            os.environ["FONTCONFIG_PATH"] = "/etc/fonts/"

        font_kind = {
            FontStyle.REGULAR: Font_FA_Regular,
            FontStyle.BOLD: Font_FA_Bold,
            FontStyle.ITALIC: Font_FA_Italic,
            FontStyle.BOLDITALIC: Font_FA_BoldItalic,
        }[font_style]

        if text_align[0] not in [TextAlign.LEFT, TextAlign.CENTER, TextAlign.RIGHT]:
            raise ValueError(
                "Horizontal TextAlign must be LEFT, CENTER, or RIGHT. "
                f"Got {text_align[0]}"
            )

        if text_align[1] not in [
            TextAlign.BOTTOM,
            TextAlign.CENTER,
            TextAlign.TOP,
            TextAlign.TOPFIRSTLINE,
        ]:
            raise ValueError(
                "Vertical TextAlign must be BOTTOM, CENTER, TOP, or TOPFIRSTLINE. "
                f"Got {text_align[1]}"
            )

        horiz_align = {
            TextAlign.LEFT: Graphic3d_HTA_LEFT,
            TextAlign.CENTER: Graphic3d_HTA_CENTER,
            TextAlign.RIGHT: Graphic3d_HTA_RIGHT,
        }[text_align[0]]

        vert_align = {
            TextAlign.BOTTOM: Graphic3d_VTA_BOTTOM,
            TextAlign.CENTER: Graphic3d_VTA_CENTER,
            TextAlign.TOP: Graphic3d_VTA_TOP,
            TextAlign.TOPFIRSTLINE: Graphic3d_VTA_TOPFIRSTLINE,
        }[text_align[1]]

        mgr = Font_FontMgr.GetInstance_s()

        if font_path and mgr.CheckFont(TCollection_AsciiString(font_path).ToCString()):
            font_t = Font_SystemFont(TCollection_AsciiString(font_path))
            font_t.SetFontPath(font_kind, TCollection_AsciiString(font_path))
            mgr.RegisterFont(font_t, True)

        else:
            font_t = mgr.FindFont(TCollection_AsciiString(font), font_kind)

        logger.info(
            "Creating text with font %s located at %s",
            font_t.FontName().ToCString(),
            font_t.FontPath(font_kind).ToCString(),
        )

        builder = Font_BRepTextBuilder()
        font_i = StdPrs_BRepFont(
            NCollection_Utf8String(font_t.FontName().ToCString()),
            font_kind,
            float(font_size),
        )

        text_flat = Compound(
            downcast(
                builder.Perform(
                    font_i,
                    NCollection_Utf8String(txt),
                    gp_Ax3(),
                    horiz_align,
                    vert_align,
                )
            )
        )

        # Align the text from the bounding box
        align_text = tuplify(align, 2)
        text_flat = text_flat.translate(
            Vector(*text_flat.bounding_box().to_align_offset(align_text))
        )

        if text_path is not None:
            path_length = text_path.length
            text_flat = Compound([position_face(f) for f in text_flat.faces()])

        return text_flat

    @classmethod
    def make_triad(cls, axes_scale: float) -> Compound:
        """The coordinate system triad (X, Y, Z axes)"""
        x_axis = Edge.make_line((0, 0, 0), (axes_scale, 0, 0))
        y_axis = Edge.make_line((0, 0, 0), (0, axes_scale, 0))
        z_axis = Edge.make_line((0, 0, 0), (0, 0, axes_scale))
        arrow_arc = Edge.make_spline(
            [(0, 0, 0), (-axes_scale / 20, axes_scale / 30, 0)],
            [(-1, 0, 0), (-1, 1.5, 0)],
        )
        arrow = Wire([arrow_arc, copy.copy(arrow_arc).mirror(Plane.XZ)])
        x_label = (
            Compound.make_text(
                "X", font_size=axes_scale / 4, align=(Align.MIN, Align.CENTER)
            )
            .move(Location(x_axis @ 1))
            .edges()
        )
        y_label = (
            Compound.make_text(
                "Y", font_size=axes_scale / 4, align=(Align.MIN, Align.CENTER)
            )
            .rotate(Axis.Z, 90)
            .move(Location(y_axis @ 1))
            .edges()
        )
        z_label = (
            Compound.make_text(
                "Z", font_size=axes_scale / 4, align=(Align.CENTER, Align.MIN)
            )
            .rotate(Axis.Y, 90)
            .rotate(Axis.X, 90)
            .move(Location(z_axis @ 1))
            .edges()
        )
        triad = Curve(
            [
                x_axis,
                y_axis,
                z_axis,
                arrow.moved(Location(x_axis @ 1)),
                arrow.rotate(Axis.Z, 90).moved(Location(y_axis @ 1)),
                arrow.rotate(Axis.Y, -90).moved(Location(z_axis @ 1)),
                *x_label,
                *y_label,
                *z_label,
            ]
        )

        return triad

    # ---- Instance Methods ----

    def __add__(self, other: None | Shape | Iterable[Shape]) -> Compound:
        """Combine other to self `+` operator

        Note that if all of the objects are connected Edges/Wires the result
        will be a Wire, otherwise a Shape.
        """
        if self._dim == 1:
            curve = Curve() if self.wrapped is None else Curve(self.wrapped)
            self.copy_attributes_to(curve, ["wrapped", "_NodeMixin__children"])
            return curve + other

        summands: ShapeList[Shape]
        if other is None:
            summands = ShapeList()
        else:
            summands = ShapeList(
                shape
                for o in ([other] if isinstance(other, Shape) else other)
                if o is not None
                for shape in o.get_top_level_shapes()
            )
        # If there is nothing to add return the original object
        if not summands:
            return self

        summands = ShapeList(
            s for s in self.get_top_level_shapes() + summands if s is not None
        )

        # Only fuse the parts if necessary
        if len(summands) <= 1:
            result: Shape = Compound(summands[0:1])
        else:
            fuse_op = BRepAlgoAPI_Fuse()
            fuse_op.SetFuzzyValue(TOLERANCE)
            self.copy_attributes_to(summands[0], ["wrapped", "_NodeMixin__children"])
            bool_result = self._bool_op(summands[:1], summands[1:], fuse_op)
            if isinstance(bool_result, list):
                result = Compound(bool_result)
                self.copy_attributes_to(result, ["wrapped", "_NodeMixin__children"])
            else:
                result = bool_result

        if SkipClean.clean:
            result = result.clean()

        return result

    def __and__(self, other: Shape | Iterable[Shape]) -> Compound:
        """Intersect other to self `&` operator"""
        and_result = Shape.__and__(self, other)
        if and_result is None:
            intersection = Compound()
        else:
            intersection = Compound(
                and_result if isinstance(and_result, list) else [and_result]
            )
        self.copy_attributes_to(intersection, ["wrapped", "_NodeMixin__children"])
        return intersection

    def __bool__(self) -> bool:
        """
        Check if empty.
        """
        if self.wrapped is None:
            return False
        return TopoDS_Iterator(self.wrapped).More()

    def __iter__(self) -> Iterator[Shape]:
        """
        Iterate over subshapes.

        """
        if self.wrapped is None:
            yield from ()
        else:
            iterator = TopoDS_Iterator(self.wrapped)

            while iterator.More():
                yield Compound.cast(iterator.Value())
                iterator.Next()

    def __len__(self) -> int:
        """Return the number of subshapes"""
        count = 0
        if self.wrapped is not None:
            for _ in self:
                count += 1
        return count

    def __repr__(self):
        """Return Compound info as string"""
        if hasattr(self, "label") and hasattr(self, "children"):
            result = (
                f"{self.__class__.__name__} at {id(self):#x}, label({self.label}), "
                + f"#children({len(self.children)})"
            )
        else:
            result = f"{self.__class__.__name__} at {id(self):#x}"
        return result

    def __sub__(self, other: None | Shape | Iterable[Shape]) -> Compound:
        """Cut other to self `-` operator"""
        difference = Shape.__sub__(self, other)
        difference = Compound(
            difference if isinstance(difference, list) else [difference]
        )
        self.copy_attributes_to(difference, ["wrapped", "_NodeMixin__children"])

        return difference

    def center(self, center_of: CenterOf = CenterOf.MASS) -> Vector:
        """Return center of object

        Find center of object

        Args:
            center_of (CenterOf, optional): center option. Defaults to CenterOf.MASS.

        Raises:
            ValueError: Center of GEOMETRY is not supported for this object
            NotImplementedError: Unable to calculate center of mass of this object

        Returns:
            Vector: center
        """
        if self.wrapped is None:
            raise ValueError("Unable to find the center of an empty object")
        if center_of == CenterOf.GEOMETRY:
            raise ValueError("Center of GEOMETRY is not supported for this object")
        if center_of == CenterOf.MASS:
            properties = GProp_GProps()
            calc_function = Shape.shape_properties_LUT[unwrapped_shapetype(self)]
            if calc_function:
                calc_function(self.wrapped, properties)
                middle = Vector(properties.CentreOfMass())
            else:
                raise NotImplementedError
        elif center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    def compound(self) -> Compound | None:
        """Return the Compound"""
        shape_list = self.compounds()
        entity_count = len(shape_list)
        if entity_count != 1:
            warnings.warn(
                f"Found {entity_count} compounds, returning first",
                stacklevel=2,
            )
        return shape_list[0] if shape_list else None

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this Shape"""
        if self.wrapped is None:
            return ShapeList()
        if isinstance(self.wrapped, TopoDS_Compound):
            # pylint: disable=not-an-iterable
            sub_compounds = [c for c in self if isinstance(c.wrapped, TopoDS_Compound)]
            sub_compounds.append(self)
        else:
            sub_compounds = []
        return ShapeList(sub_compounds)

    def do_children_intersect(
        self, include_parent: bool = False, tolerance: float = 1e-5
    ) -> tuple[bool, tuple[Shape | None, Shape | None], float]:
        """Do Children Intersect

        Determine if any of the child objects within a Compound/assembly intersect by
        intersecting each of the shapes with each other and checking for
        a common volume.

        Args:
            include_parent (bool, optional): check parent for intersections. Defaults to False.
            tolerance (float, optional): maximum allowable volume difference. Defaults to 1e-5.

        Returns:
            tuple[bool, tuple[Shape, Shape], float]:
                do the object intersect, intersecting objects, volume of intersection
        """
        children: list[Shape] = list(PreOrderIter(self))
        if not include_parent:
            children.pop(0)  # remove parent
        # children_bbox = [child.bounding_box().to_solid() for child in children]
        children_bbox = [
            Solid.from_bounding_box(child.bounding_box()) for child in children
        ]
        child_index_pairs = [
            tuple(map(int, comb))
            for comb in combinations(list(range(len(children))), 2)
        ]
        for child_index_pair in child_index_pairs:
            # First check for bounding box intersections ..
            # .. then confirm with actual object intersections which could be complex
            bbox_intersection = children_bbox[child_index_pair[0]].intersect(
                children_bbox[child_index_pair[1]]
            )
            if bbox_intersection is not None:
                obj_intersection = children[child_index_pair[0]].intersect(
                    children[child_index_pair[1]]
                )
                if obj_intersection is not None:
                    common_volume = (
                        0.0
                        if isinstance(obj_intersection, list)
                        else obj_intersection.volume
                    )
                    if common_volume > tolerance:
                        return (
                            True,
                            (
                                children[child_index_pair[0]],
                                children[child_index_pair[1]],
                            ),
                            common_volume,
                        )
        return (False, (None, None), 0.0)

    def get_type(
        self,
        obj_type: (
            type[Vertex]
            | type[Edge]
            | type[Face]
            | type[Shell]
            | type[Solid]
            | type[Wire]
        ),
    ) -> list[Vertex | Edge | Face | Shell | Solid | Wire]:
        """get_type

        Extract the objects of the given type from a Compound. Note that this
        isn't the same as Faces() etc. which will extract Faces from Solids.

        Args:
            obj_type (Union[Vertex, Edge, Face, Shell, Solid, Wire]): Object types to extract

        Returns:
            list[Union[Vertex, Edge, Face, Shell, Solid, Wire]]: Extracted objects
        """
        if self.wrapped is None:
            return []

        type_map = {
            Vertex: TopAbs_ShapeEnum.TopAbs_VERTEX,
            Edge: TopAbs_ShapeEnum.TopAbs_EDGE,
            Face: TopAbs_ShapeEnum.TopAbs_FACE,
            Shell: TopAbs_ShapeEnum.TopAbs_SHELL,
            Solid: TopAbs_ShapeEnum.TopAbs_SOLID,
            Wire: TopAbs_ShapeEnum.TopAbs_WIRE,
            Compound: TopAbs_ShapeEnum.TopAbs_COMPOUND,
        }
        results = []
        for comp in self.compounds():
            if comp.wrapped is None:
                continue
            iterator = TopoDS_Iterator()
            iterator.Initialize(comp.wrapped)
            while iterator.More():
                child = iterator.Value()
                if child.ShapeType() == type_map[obj_type]:
                    results.append(obj_type(downcast(child)))  # type: ignore[call-overload,arg-type]
                iterator.Next()

        return results

    def unwrap(self, fully: bool = True) -> Self | Shape:
        """Strip unnecessary Compound wrappers

        Args:
            fully (bool, optional): return base shape without any Compound
                wrappers (otherwise one Compound is left). Defaults to True.

        Returns:
            Union[Self, Shape]: base shape
        """
        if len(self) == 1:
            single_element = next(iter(self))
            self.copy_attributes_to(single_element, ["wrapped", "_NodeMixin__children"])

            # If the single element is another Compound, unwrap it recursively
            if isinstance(single_element, Compound):
                # Unwrap recursively and copy attributes down
                unwrapped = single_element.unwrap(fully)
                if not fully:
                    unwrapped = type(self)(unwrapped.wrapped)
                self.copy_attributes_to(unwrapped, ["wrapped", "_NodeMixin__children"])
                return unwrapped

            return single_element if fully else self

        # If there are no elements or more than one element, return self
        return self

    # def _post_attach(self, parent: Compound):
    #     """Method call after attaching to `parent`."""
    #     logger.debug(
    #         "Updated parent of %s to %s", self.label, parent.label, stacklevel=5
    #     )
    #     base = getattr(parent, "_base_wrapped", None)
    #     shapes = ([base] if base else []) + [c.wrapped for c in parent.children]
    #     parent.wrapped = _make_topods_compound_from_shapes(shapes)
    #     # now walk up and rebuild every ancestor
    #     node = parent.parent
    #     while node is not None:
    #         base = getattr(node, "_base_wrapped", None)
    #         shapes = ([base] if base else []) + [c.wrapped for c in node.children]
    #         node.wrapped = _make_topods_compound_from_shapes(shapes)
    #         node = node.parent

    # def _post_attach_children(self, children: Iterable[Shape]):
    #     """Method call after attaching `children`."""
    #     if children:
    #         kids = ",".join([child.label for child in children])
    #         logger.debug("Adding children %s to %s", kids, self.label, stacklevel=5)
    #         # self.wrapped = _make_topods_compound_from_shapes(
    #         #     [self._base_wrapped, *[c.wrapped for c in children]]
    #         # )
    #         base = getattr(self, "_base_wrapped", None)
    #         shapes = ([base] if base else []) + [c.wrapped for c in self.children]
    #         self.wrapped = _make_topods_compound_from_shapes(shapes)

    #         # now walk up and rebuild every ancestor
    #         node = self.parent
    #         while node is not None:
    #             base = getattr(node, "_base_wrapped", None)
    #             shapes = ([base] if base else []) + [c.wrapped for c in node.children]
    #             node.wrapped = _make_topods_compound_from_shapes(shapes)
    #             node = node.parent

    #     # else:
    #     #     logger.debug("Adding no children to %s", self.label)

    # def _post_detach(self, parent: Compound):
    #     """Method call after detaching from `parent`."""
    #     logger.debug("Removing parent of %s (%s)", self.label, parent.label)
    #     if parent.children:
    #         # parent.wrapped = _make_topods_compound_from_shapes(
    #         #     [c.wrapped for c in parent.children]
    #         # )
    #         parent.wrapped = _make_topods_compound_from_shapes(
    #             [parent.wrapped, *[c.wrapped for c in parent.children]]
    #         )
    #     else:
    #         parent.wrapped = None

    # def _post_detach_children(self, children):
    #     """Method call before detaching `children`."""
    #     if children:
    #         kids = ",".join([child.label for child in children])
    #         logger.debug("Removing children %s from %s", kids, self.label)
    #         # self.wrapped = _make_topods_compound_from_shapes(
    #         #     [c.wrapped for c in self.children]
    #         # )
    #         self.wrapped = _make_topods_compound_from_shapes(
    #             [self.wrapped, *[c.wrapped for c in self.children]]
    #         )

    #     # else:
    #     #     logger.debug("Removing no children from %s", self.label)

    # def _pre_attach(self, parent: Assembly | Compound):
    #     """Method call before attaching to `parent`."""
    #     if not isinstance(parent, (Assembly | Compound)):
    #         raise ValueError("`parent` must be of type Assembly or Compound")

    # def _pre_attach_children(self, children):
    #     """Method call before attaching `children`."""
    #     if not all(isinstance(child, Shape) for child in children):
    #         raise ValueError("Each child must be of type Shape")

    def _remove(self, shape: Shape) -> Compound:
        """Return self with the specified shape removed.

        Args:
          shape: Shape:
        """
        if self.wrapped is None or shape.wrapped is None:
            return self
        comp_builder = TopoDS_Builder()
        comp_builder.Remove(self.wrapped, shape.wrapped)
        return self


class Curve(Compound):
    """A Compound containing 1D objects - aka Edges"""

    __add__ = Mixin1D.__add__  # type: ignore
    # ---- Properties ----

    @property
    def _dim(self) -> int:
        return 1

    # ---- Instance Methods ----

    def __matmul__(self, position: float) -> Vector:
        """Position on curve operator @ - only works if continuous"""
        return Wire(self.edges()).position_at(position)

    def __mod__(self, position: float) -> Vector:
        """Tangent on wire operator % - only works if continuous"""
        return Wire(self.edges()).tangent_at(position)

    def __xor__(self, position: float) -> Location:
        """Location on wire operator ^ - only works if continuous"""
        return Wire(self.edges()).location_at(position)

    def wires(self) -> ShapeList[Wire]:  # type: ignore
        """A list of wires created from the edges"""
        return Wire.combine(self.edges())


class Sketch(Compound):
    """A Compound containing 2D objects - aka Faces"""

    # ---- Properties ----

    @property
    def _dim(self) -> int:
        return 2


class Part(Compound):
    """A Compound containing 3D objects - aka Solids"""

    # ---- Properties ----

    @property
    def _dim(self) -> int:
        return 3


from ocp_vscode import show
