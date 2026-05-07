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
import warnings
from collections.abc import Iterable, Iterator, Sequence
from itertools import combinations
from os import PathLike, fspath
from typing import overload
from typing_extensions import Self

import OCP.TopAbs as ta
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse, BRepAlgoAPI_Section
from OCP.gp import gp_Ax3
from OCP.Graphic3d import (
    Graphic3d_HTA_LEFT,
    Graphic3d_HTA_CENTER,
    Graphic3d_HTA_RIGHT,
    Graphic3d_VTA_BOTTOM,
    Graphic3d_VTA_CENTER,
    Graphic3d_VTA_TOP,
    Graphic3d_VTA_TOPFIRSTLINE,
)
from OCP.GProp import GProp_GProps
from OCP.NCollection import NCollection_Utf8String
from OCP.StdPrs import StdPrs_BRepTextBuilder as Font_BRepTextBuilder, StdPrs_BRepFont
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopoDS import (
    TopoDS,
    TopoDS_Builder,
    TopoDS_Compound,
    TopoDS_Iterator,
    TopoDS_Shape,
)
from anytree import PreOrderIter
from build123d.build_enums import Align, CenterOf, FontStyle, TextAlign
from build123d.geometry import (
    TOLERANCE,
    Axis,
    Color,
    Location,
    Plane,
    Vector,
    VectorLike,
    logger,
)
from build123d.text import FONT_ASPECT, FontManager

from .one_d import Edge, Wire, Mixin1D
from .shape_core import (
    Shape,
    ShapeList,
    SkipClean,
    Joint,
    downcast,
    shapetype,
    topods_dim,
    _make_topods_compound_from_shapes,
)
from .three_d import Mixin3D, Solid
from .two_d import Face, Shell
from .utils import (
    _extrude_topods_shape,
    tuplify,
    unwrapped_shapetype,
)
from .zero_d import Vertex


class Compound(Mixin3D[TopoDS_Compound]):
    """A Compound in build123d is a topological entity representing a collection of
    geometric shapes grouped together within a single structure. It serves as a
    container for organizing diverse shapes like edges, faces, or solids. This
    hierarchical arrangement facilitates the construction of complex models by
    combining simpler shapes. Compound plays a pivotal role in managing the
    composition and structure of intricate 3D models in computer-aided design
    (CAD) applications, allowing engineers and designers to work with assemblies
    of shapes as unified entities for efficient modeling and analysis."""

    order = 4.0

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
        topods_compound: TopoDS_Compound | None
        if isinstance(obj, Iterable):
            topods_compound = _make_topods_compound_from_shapes(
                [s.wrapped for s in obj]
            )
        else:
            topods_compound = obj

        super().__init__(
            obj=topods_compound,
            label=label,
            color=color,
            parent=parent,
        )
        self.material = "" if material is None else material
        self.joints = {} if joints is None else joints
        self.children = [] if children is None else children

    # ---- Properties ----

    @property
    def _dim(self) -> int | None:
        """The dimension of the shapes within the Compound - None if inconsistent"""
        return topods_dim(self.wrapped)

    @property
    def volume(self) -> float:
        """volume - the volume of this Compound"""
        # when density == 1, mass == volume
        return sum(i.volume for i in [*self.get_type(Solid), *self.get_type(Shell)])

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
        return Compound(TopoDS.Compound(_extrude_topods_shape(obj.wrapped, direction)))

    @classmethod
    def make_text(
        cls,
        txt: str,
        font_size: float,
        font: str = "Arial",
        font_path: PathLike[str] | str | None = None,
        font_style: FontStyle = FontStyle.REGULAR,
        text_align: tuple[TextAlign, TextAlign] = (TextAlign.CENTER, TextAlign.CENTER),
        align: Align | tuple[Align, Align] | None = None,
        position_on_path: float = 0.0,
        text_path: Edge | Wire | None = None,
        single_line_width: float = 0.0,
    ) -> Compound:
        """Text that optionally follows a path.

        The text that is created can be combined as with other sketch features by specifying
        a mode or rotated by the given angle. In addition, edges have been previously created
        with arc or segment, the text will follow the path defined by these edges. The start
        parameter can be used to shift the text along the path to achieve precise positioning.

        Args:
            txt (str): text to render
            font_size (float): size of the font in model units
            font (str, optional): font name. Defaults to "Arial"
            font_path (PathLike | str, optional): system path to font file. Defaults to None
            font_style (Font_Style, optional): font style, REGULAR, BOLD, BOLDITALIC, or
                ITALIC. Defaults to Font_Style.REGULAR
            text_align (tuple[TextAlign, TextAlign], optional): horizontal text align
                LEFT, CENTER, or RIGHT. Vertical text align BOTTOM, CENTER, TOP, or
                TOPFIRSTLINE. Defaults to (TextAlign.CENTER, TextAlign.CENTER)
            align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of
                object. Defaults to None
            position_on_path (float, optional): the relative location on path to position
                the text, values must be between 0.0 and 1.0. Defaults to 0.0
            text_path: (Edge | Wire, optional): path for text to follow. Defaults to None
                Compound object containing multiple Shapes representing the text
            single_line_width (float): width of outlined single line font.
                Defaults to 0.0

        Examples::

            fox = Compound.make_text(
                txt="The quick brown fox jumped over the lazy dog",
                font_size=10,
                position_on_path=0.1,
                text_path=jump_edge,
            )

        """
        # pylint: disable=too-many-locals

        def position_glyph(glyph: Shape, path: Edge | Wire, position: float) -> Shape:
            """Reposition a glyph shape on provided path

            Local coordinates are used to calculate the position of the shape
            relative to the path. Global coordinates to position the shape.
            """

            bbox = glyph.bounding_box()
            face_bottom_center = Vector((bbox.min.X + bbox.max.X) / 2, 0, 0)
            relative_position_on_wire = position + face_bottom_center.X / path.length
            wire_tangent = path.tangent_at(relative_position_on_wire)
            wire_angle = Vector(1, 0, 0).get_signed_angle(wire_tangent)
            wire_position = path.position_at(relative_position_on_wire)

            return glyph.translate(wire_position - face_bottom_center).rotate(
                Axis(wire_position, (0, 0, 1)),
                -wire_angle,
            )

        font_path_str = fspath(font_path) if font_path is not None else None

        manager = FontManager()
        if font_path_str and manager.check_font(font_path_str):  # pragma: no cover
            face_names = manager.register_font(font_path_str, True, False)
            # Check if font (name) is in face names and not bad or default (Arial)
            font_name = font if font in face_names else face_names[0]
            system_font = manager.find_font(font_name, font_style)
        else:
            system_font = manager.find_font(font, font_style)

        # Validate TextAlign parameters
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

        logger.info(
            "Creating text with font %s located at %s",
            system_font.FontName().ToCString(),
            system_font.FontPath(FONT_ASPECT[font_style]).ToCString(),
        )

        # Write text to shape
        builder = Font_BRepTextBuilder()
        brep_font = StdPrs_BRepFont(
            NCollection_Utf8String(system_font.FontName().ToCString()),
            FONT_ASPECT[font_style],
            float(font_size),
        )

        if system_font.IsSingleStrokeFont():
            brep_font.SetCompositeCurveMode(False)

        text_flat = Compound(
            TopoDS.Compound(
                builder.Perform(
                    brep_font,
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

        # Place text on path
        if text_path:
            glyphs = text_flat.get_top_level_shapes()
            text_flat = Compound(
                [position_glyph(g, text_path, position_on_path) for g in glyphs]
            )

        def _make_face(edges: Iterable[Edge]) -> Face:
            face = Face(Wire.combine(edges)[0])
            if face.normal_at().Z < 0:  # flip up-side-down faces
                face = -face  # pylint: disable=E1130
            return face

        # Outline single line text
        # offset_2d distance is radius, treat single_line_width as diameter/overall height
        if system_font.IsSingleStrokeFont() and single_line_width > 0:
            outline = [e.offset_2d(single_line_width / 2) for e in text_flat.edges()]
            outline = [_make_face(o.edges()) for o in outline]
            text_flat = Compound([]) + outline
            if any([not f.is_valid for f in text_flat.get_top_level_shapes()]):
                raise ValueError(
                    "single_line_width "
                    f"({single_line_width}) is too large for the text and "
                    "produces invalid faces. Try a smaller width"
                )

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
                "X", axes_scale / 4, "singleline", align=(Align.MIN, Align.CENTER)
            )
            .move(Location(x_axis @ 1))
            .edges()
        )
        y_label = (
            Compound.make_text(
                "Y", axes_scale / 4, "singleline", align=(Align.MIN, Align.CENTER)
            )
            .rotate(Axis.Z, 90)
            .move(Location(y_axis @ 1))
            .edges()
        )
        z_label = (
            Compound.make_text(
                "Z", axes_scale / 4, "singleline", align=(Align.CENTER, Align.MIN)
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

    def __add__(self, other: None | Shape | Iterable[Shape]) -> Compound | Wire:
        """Combine other to self `+` operator

        Note that if all of the objects are connected Edges/Wires the result
        will be a Wire, otherwise a Shape.
        """
        if self._dim == 1:
            curve = Curve() if self._wrapped is None else Curve(self.wrapped)
            sum1d = curve + other
            if isinstance(sum1d, Edge):
                result1d = Curve([sum1d])
            else:
                result1d = sum1d
            self.copy_attributes_to(result1d, ["wrapped", "_NodeMixin__children"])
            return result1d

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
            result = self._bool_op(summands[:1], summands[1:], fuse_op)

        if SkipClean.clean:
            result = result.clean()

        return result

    def __and__(self, other: Shape | Iterable[Shape]) -> Compound:
        """Intersect other to self `&` operator"""
        intersection = Shape.__and__(self, other)
        if intersection is None:
            return Compound()
        if isinstance(intersection, list):
            intersection = Compound(intersection)
        elif not isinstance(intersection, Compound):
            intersection = Compound([intersection])
        self.copy_attributes_to(intersection, ["wrapped", "_NodeMixin__children"])
        return intersection

    def __bool__(self) -> bool:
        """
        Check if empty.
        """

        return self._wrapped is not None and TopoDS_Iterator(self.wrapped).More()

    def __iter__(self) -> Iterator[Shape]:
        """
        Iterate over subshapes.

        """

        iterator = TopoDS_Iterator(self.wrapped)

        while iterator.More():
            yield Compound.cast(iterator.Value())
            iterator.Next()

    def __len__(self) -> int:
        """Return the number of subshapes"""
        count = 0
        if self._wrapped is not None:
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
        if not isinstance(difference, Compound):
            difference = Compound([difference])
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
        else:  # center_of == CenterOf.BOUNDING_BOX:
            middle = self.bounding_box().center()
        return middle

    def compound(self) -> Compound:
        """Return the Compound"""
        shape_list = self.compounds()
        entity_count = len(shape_list)
        if entity_count != 1:
            raise ValueError(f"Expected exactly one compound, found {entity_count}")
        return shape_list[0]

    def compounds(self) -> ShapeList[Compound]:
        """compounds - all the compounds in this Shape"""
        if self._wrapped is None:
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
                    common_volume = sum(s.volume for s in obj_intersection.solids())
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
            iterator = TopoDS_Iterator()
            iterator.Initialize(comp.wrapped)
            while iterator.More():
                child = iterator.Value()
                if child.ShapeType() == type_map[obj_type]:
                    results.append(obj_type(downcast(child)))  # type: ignore
                iterator.Next()

        return results

    def _intersect(
        self,
        other: Shape | Vector | Location | Axis | Plane,
        tolerance: float = 1e-6,
        include_touched: bool = False,
    ) -> ShapeList | None:
        """Single-object intersection for Compound (OR semantics).

        Distributes intersection over elements, collecting all results:
            Compound([a, b]).intersect(s) = (a ∩ s) ∪ (b ∩ s)
            Compound([a, b]).intersect(Compound([c, d])) = (a ∩ c) ∪ (a ∩ d) ∪ (b ∩ c) ∪ (b ∩ d)

        Handles both build123d assemblies (children) and OCCT Compounds (list()).
        Nested Compounds are handled by recursion.

        Args:
            other: Shape or geometry object to intersect with
            tolerance: tolerance for intersection detection
            include_touched: if True, include boundary contacts
                (only relevant when Solids are involved)
        """
        # Convert geometry objects
        if isinstance(other, Vector):
            other = Vertex(other)
        elif isinstance(other, Location):
            other = Vertex(other.position)
        elif isinstance(other, Axis):
            other = Edge(other)
        elif isinstance(other, Plane):
            other = Face(other)

        # Get self elements: assembly children or OCCT direct children
        self_elements = self.children if self.children else list(self)

        if not self_elements:
            return None

        results: ShapeList = ShapeList()

        # Distribute over elements (OR semantics for Compound arguments)
        if isinstance(other, Compound):
            other_elements = other.children if other.children else list(other)
        else:
            other_elements = [other]

        for self_elem in self_elements:
            for other_elem in other_elements:
                intersection = self_elem._intersect(
                    other_elem, tolerance, include_touched
                )
                if intersection:
                    results.extend(intersection)

        # Remove duplicates using Shape's __hash__
        unique = ShapeList(set(results))

        return unique if unique else None

    def touch(
        self, other: Shape, tolerance: float = 1e-6
    ) -> ShapeList[Vertex | Edge | Face]:
        """Distribute touch over compound elements.

        Iterates over elements and collects touch results. Only Solid and
        Face elements produce boundary contacts; other shapes return empty.

        Args:
            other: Shape to check boundary contacts with
            tolerance: tolerance for contact detection

        Returns:
            ShapeList of boundary contact geometry (empty if no contact)
        """
        results: ShapeList = ShapeList()

        # Get elements: assembly children or OCCT direct children
        elements = self.children if self.children else list(self)

        for elem in elements:
            results.extend(elem.touch(other, tolerance))

        return ShapeList(set(results))

    def project_to_viewport(
        self,
        viewport_origin: VectorLike,
        viewport_up: VectorLike = (0, 0, 1),
        look_at: VectorLike | None = None,
        focus: float | None = None,
    ) -> tuple[ShapeList[Edge], ShapeList[Edge]]:
        """project_to_viewport

        Project a shape onto a viewport returning visible and hidden Edges.

        Args:
            viewport_origin (VectorLike): location of viewport
            viewport_up (VectorLike, optional): direction of the viewport y axis.
                Defaults to (0, 0, 1).
            look_at (VectorLike, optional): point to look at.
                Defaults to None (center of shape).
            focus (float, optional): the focal length for perspective projection
                Defaults to None (orthographic projection)

        Returns:
            tuple[ShapeList[Edge],ShapeList[Edge]]: visible & hidden Edges
        """
        return Mixin1D.project_to_viewport(
            self, viewport_origin, viewport_up, look_at, focus
        )

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

    def _post_attach(self, parent: Compound):
        """Method call after attaching to `parent`."""
        logger.debug("Updated parent of %s to %s", self.label, parent.label)
        parent.wrapped = _make_topods_compound_from_shapes(
            [c.wrapped for c in parent.children]
        )

    def _post_attach_children(self, children: Iterable[Shape]):
        """Method call after attaching `children`."""
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Adding children %s to %s", kids, self.label)
            self.wrapped = _make_topods_compound_from_shapes(
                [c.wrapped for c in self.children]
            )
        # else:
        #     logger.debug("Adding no children to %s", self.label)

    def _post_detach(self, parent: Compound):
        """Method call after detaching from `parent`."""
        logger.debug("Removing parent of %s (%s)", self.label, parent.label)
        if parent.children:
            parent.wrapped = _make_topods_compound_from_shapes(
                [c.wrapped for c in parent.children]
            )
        # else:
        #     parent.wrapped = None

    def _post_detach_children(self, children):
        """Method call before detaching `children`."""
        if children:
            kids = ",".join([child.label for child in children])
            logger.debug("Removing children %s from %s", kids, self.label)
            self.wrapped = _make_topods_compound_from_shapes(
                [c.wrapped for c in self.children]
            )
        # else:
        #     logger.debug("Removing no children from %s", self.label)

    def _pre_attach(self, parent: Compound):
        """Method call before attaching to `parent`."""
        if not isinstance(parent, Compound):
            raise ValueError("`parent` must be of type Compound")

    def _pre_attach_children(self, children):
        """Method call before attaching `children`."""
        if not all(isinstance(child, Shape) for child in children):
            raise ValueError("Each child must be of type Shape")

    def _remove(self, shape: Shape) -> Compound:
        """Return self with the specified shape removed.

        Args:
          shape: Shape:
        """
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

    def __iadd__(self, other: None | Shape | Iterable[Shape]) -> Sketch:
        return self + other


class Part(Compound):
    """A Compound containing 3D objects - aka Solids"""

    # ---- Properties ----

    @property
    def _dim(self) -> int:
        return 3

    def __iadd__(self, other: None | Shape | Iterable[Shape]) -> Part:
        return self + other


Shape.register_composite_factory(None, Compound)
Shape.register_composite_factory(1, Curve)
Shape.register_composite_factory(2, Sketch)
Shape.register_composite_factory(3, Part)
