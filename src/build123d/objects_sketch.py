"""
Sketch Objects

name: objects_sketch.py
by:   Gumyr
date: March 22nd 2023

desc:
    This python module contains objects (classes) that create 2D Sketches.

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

import trianglesolver

from math import cos, degrees, pi, radians, sin, tan
from typing import cast
from os import PathLike

from collections.abc import Iterable

from build123d.build_common import LocationList, flatten_sequence, validate_inputs
from build123d.build_enums import Align, FontStyle, Mode, TextAlign
from build123d.build_sketch import BuildSketch
from build123d.geometry import (
    Axis,
    Location,
    Rotation,
    Vector,
    VectorLike,
    to_align_offset,
    TOLERANCE,
)
from build123d.topology import (
    Compound,
    Edge,
    Face,
    ShapeList,
    Sketch,
    Vertex,
    Wire,
    tuplify,
    topo_explore_common_vertex,
)


class BaseSketchObject(Sketch):
    """BaseSketchObject

    Base class for all BuildSketch objects

    Args:
        face (Face): face to create
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        obj: Compound | Face,
        rotation: float = 0,
        align: Align | tuple[Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if align is not None:
            align = tuplify(align, 2)
            obj.move(Location(obj.bounding_box().to_align_offset(align)))

        context: BuildSketch | None = BuildSketch._get_context(self, log=False)
        if context is None:
            new_faces = (
                obj.moved(Rotation(0, 0, rotation)).faces()
                if rotation != 0
                else obj.faces()
            )

        else:
            self.rotation = rotation
            self.mode = mode

            obj = obj.moved(Rotation(0, 0, rotation)) if rotation != 0 else obj

            new_faces = ShapeList(
                face.moved(location) if location != Location() else face
                for face in obj.faces()
                for location in LocationList._get_context().local_locations
            )
            if isinstance(context, BuildSketch):
                context._add_to_context(*new_faces, mode=mode)

        super().__init__(Compound(new_faces).wrapped)


class Circle(BaseSketchObject):
    """Sketch Object: Circle

    Create a circle defined by radius.

    Args:
        radius (float): circle radius
        arc_size (float, optional): angular size of sector. Defaults to 360.
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.CENTER, Align.CENTER)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        radius: float,
        arc_size: float = 360.0,
        align: Align | tuple[Align, Align] | None = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.radius = radius
        self.arc_size = arc_size
        self.align = tuplify(align, 2)

        face = (
            Face(Wire.make_circle(radius))
            if arc_size == 360.0
            else Face.revolve(Edge.make_line((radius, 0), (0, 0)), arc_size, Axis.Z)
        )
        super().__init__(face, 0, self.align, mode)


class Ellipse(BaseSketchObject):
    """Sketch Object: Ellipse

    Create an ellipse defined by x- and y- radii.

    Args:
        x_radius (float): x radius of the ellipse (along the x-axis of plane)
        y_radius (float): y radius of the ellipse (along the y-axis of plane)
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.CENTER, Align.CENTER)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        x_radius: float,
        y_radius: float,
        rotation: float = 0,
        align: Align | tuple[Align, Align] | None = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.x_radius = x_radius
        self.y_radius = y_radius
        self.align = tuplify(align, 2)

        face = Face(Wire.make_ellipse(x_radius, y_radius))
        super().__init__(face, rotation, self.align, mode)


class Polygon(BaseSketchObject):
    """Sketch Object: Polygon

    Create a polygon defined by given sequence of points.

    Note: the order of the points defines the resulting normal of the Face in Algebra
    mode, where counter-clockwise order creates an upward normal while clockwise order
    a downward normal. In Builder mode, the Face is added with an upward normal.

    Args:
        pts (VectorLike | Iterable[VectorLike]): sequence of points defining the
            vertices of the polygon
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.NONE, Align.NONE)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        *pts: VectorLike | Iterable[VectorLike],
        rotation: float = 0,
        align: Align | tuple[Align, Align] | None = (Align.NONE, Align.NONE),
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        flattened_pts = flatten_sequence(*pts)
        self.pts = flattened_pts
        self.align = tuplify(align, 2)

        poly_pts = [Vector(p) for p in self.pts]
        face = Face(Wire.make_polygon(poly_pts))
        super().__init__(face, rotation, self.align, mode)


class Rectangle(BaseSketchObject):
    """Sketch Object: Rectangle

    Create a rectangle defined by width and height.

    Args:
        width (float): rectangle width
        height (float): rectangle height
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.CENTER, Align.CENTER)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        align: Align | tuple[Align, Align] | None = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.width = width
        self.rectangle_height = height
        self.align = tuplify(align, 2)

        face = Face.make_rect(width, height)
        super().__init__(face, rotation, self.align, mode)


class RectangleRounded(BaseSketchObject):
    """Sketch Object: Rectangle Rounded

    Create a rectangle defined by width and height with filleted corners.

    Args:
        width (float): rectangle width
        height (float): rectangle height
        radius (float): fillet radius
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.CENTER, Align.CENTER)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        radius: float,
        rotation: float = 0,
        align: Align | tuple[Align, Align] | None = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        if width <= 2 * radius or height <= 2 * radius:
            raise ValueError("width and height must be > 2*radius")
        self.width = width
        self.rectangle_height = height
        self.radius = radius
        self.align = tuplify(align, 2)

        face = Face.make_rect(width, height)
        face = face.fillet_2d(radius, face.vertices())
        super().__init__(face, rotation, align, mode)


class RegularPolygon(BaseSketchObject):
    """Sketch Object: Regular Polygon

    Create a regular polygon defined by radius and side count. Use major_radius to define whether
    the polygon circumscribes (along the vertices) or inscribes (along the sides) the radius circle.

    Args:
        radius (float): construction radius
        side_count (int): number of sides
        major_radius (bool): If True the radius is the major radius (circumscribed circle),
            else the radius is the minor radius (inscribed circle). Defaults to True
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.CENTER, Align.CENTER)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        radius: float,
        side_count: int,
        major_radius: bool = True,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        # pylint: disable=too-many-locals
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        if side_count < 3:
            raise ValueError(
                f"RegularPolygon must have at least three sides, not {side_count}"
            )

        if major_radius:
            rad = radius
        else:
            rad = radius / cos(pi / side_count)

        self.radius: float = rad  #: radius of the circumscribed circle or major radius
        self.apothem: float = rad * cos(
            pi / side_count
        )  #: radius of the inscribed circle or minor radius

        self.side_count = side_count
        self.align = align

        pts = ShapeList(
            [
                Vector(
                    rad * cos(i * 2 * pi / side_count + radians(rotation)),
                    rad * sin(i * 2 * pi / side_count + radians(rotation)),
                )
                for i in range(side_count + 1)
            ]
        )
        pts_sorted = [pts.sort_by(Axis.X), pts.sort_by(Axis.Y)]
        # pylint doesn't recognize that a ShapeList of Vector is valid
        # pylint: disable=no-member
        mins = [pts_sorted[0][0].X, pts_sorted[1][0].Y]
        maxs = [pts_sorted[0][-1].X, pts_sorted[1][-1].Y]

        align_offset = to_align_offset(mins, maxs, align, center=(0, 0))
        pts_ao = [point + align_offset for point in pts]

        face = Face(Wire.make_polygon(pts_ao))
        super().__init__(face, rotation=0, align=None, mode=mode)


class SlotArc(BaseSketchObject):
    """Sketch Object: Slot Arc

    Create a slot defined by a line and height. May be an arc, stright line, spline, etc.

    Args:
        arc (Edge | Wire): center line of slot
        height (float): diameter of end arcs
        rotation (float, optional): angle to rotate object. Defaults to 0
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        arc: Edge | Wire,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.arc = arc
        self.slot_height = height

        arc = arc if isinstance(arc, Wire) else Wire([arc])
        face = Face(arc.offset_2d(height / 2))
        super().__init__(face, rotation, None, mode)


class SlotCenterPoint(BaseSketchObject):
    """Sketch Object: Slot Center Point

    Create a slot defined by the center of the slot and the center of one end arc.
    The slot will be symmetric about the center point.

    Args:
        center (VectorLike): center point
        point (VectorLike): center of arc point
        height (float): diameter of end arcs
        rotation (float, optional): angle to rotate object. Defaults to 0
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        center: VectorLike,
        point: VectorLike,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        center_v = Vector(center)
        point_v = Vector(point)
        self.slot_center = center_v
        self.point = point_v
        self.slot_height = height

        half_line = point_v - center_v

        if half_line.length <= 0:
            raise ValueError(
                "Distance between center and point must be greater than 0 "
                f"Got: distance = {half_line.length} (computed)"
            )

        face = Face(
            Wire.combine(
                [
                    Edge.make_line(point_v, center_v),
                    Edge.make_line(center_v, center_v - half_line),
                ]
            )[0].offset_2d(height / 2)
        )
        super().__init__(face, rotation, None, mode)


class SlotCenterToCenter(BaseSketchObject):
    """Sketch Object: Slot Center To Center

    Create a slot defined by the distance between the centers of the two end arcs.

    Args:
        center_separation (float): distance between arc centers
        height (float): diameter of end arcs
        rotation (float, optional): angle to rotate object. Defaults to 0
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        center_separation: float,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        if center_separation < 0:
            raise ValueError(
                f"Requires center_separation > 0. Got: {center_separation=}"
            )

        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.center_separation = center_separation
        self.slot_height = height

        if center_separation > 0:
            face = Face(
                Wire(
                    [
                        Edge.make_line(Vector(-center_separation / 2, 0, 0), Vector()),
                        Edge.make_line(Vector(), Vector(+center_separation / 2, 0, 0)),
                    ]
                ).offset_2d(height / 2)
            )
        else:
            face = cast(Face, Circle(height / 2, mode=mode).face())

        super().__init__(face, rotation, None, mode)


class SlotOverall(BaseSketchObject):
    """Sketch Object: Slot Overall

    Create a slot defined by the overall width and height.

    Args:
        width (float): overall width of slot
        height (float): diameter of end arcs
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.CENTER, Align.CENTER)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        align: Align | tuple[Align, Align] | None = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        if width < height:
            raise ValueError(
                f"Slot requires that width > height. Got: {width=}, {height=}"
            )

        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.width = width
        self.slot_height = height

        if width > height:
            face = Face(
                Wire(
                    [
                        Edge.make_line(Vector(-width / 2 + height / 2, 0, 0), Vector()),
                        Edge.make_line(Vector(), Vector(+width / 2 - height / 2, 0, 0)),
                    ]
                ).offset_2d(height / 2)
            )
        else:
            face = cast(Face, Circle(width / 2, mode=mode).face())

        super().__init__(face, rotation, align, mode)


class Text(BaseSketchObject):
    """Sketch Object: Text

    Create text defined by text string and font size.

    Fonts installed to the system can be specified by name and FontStyle. Fonts with
    subfamilies not in FontStyle should be specified with the subfamily name, e.g.
    "Arial Black". Alternatively, a specific font file can be specified with font_path.

    Use `available_fonts()` to list available font names for `font` and FontStyles.
    Note: on Windows, fonts must be installed with "Install for all users" to be found
    by name.

    Not all fonts have every FontStyle available, however ITALIC and BOLDITALIC will
    still italicize the font if the respective font file is not available.

    text_align specifies alignment of text inside the bounding box, while align the
    aligns the bounding box itself.

    Optionally, the Text can be positioned on a non-linear edge or wire with a path and
    position_on_path.

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
        path (Edge | Wire, optional): path for text to follow. Defaults to None
        position_on_path (float, optional): the relative location on path to position
            the text, values must be between 0.0 and 1.0. Defaults to 0.0
        single_line_width (float, optional): width of outlined single line font.
            Defaults to 4% of font_size
        rotation (float, optional): angle to rotate object. Defaults to 0
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    # pylint: disable=too-many-instance-attributes
    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        txt: str,
        font_size: float,
        font: str = "Arial",
        font_path: PathLike[str] | str | None = None,
        font_style: FontStyle = FontStyle.REGULAR,
        text_align: tuple[TextAlign, TextAlign] = (TextAlign.CENTER, TextAlign.CENTER),
        align: Align | tuple[Align, Align] | None = None,
        path: Edge | Wire | None = None,
        position_on_path: float = 0.0,
        single_line_width: float | None = None,
        rotation: float = 0.0,
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        if single_line_width is None:
            # Ensure line width is passed for single line fonts to convert to faces
            # Default is 4% of font_size
            single_line_width = 0.04 * font_size
        elif single_line_width <= 0.0:
            raise ValueError(
                f"single_line_width ({single_line_width}) must be greater than 0"
            )

        self.txt = txt
        self.font_size = font_size
        self.font = font
        self.font_path = font_path
        self.font_style = font_style
        self.text_align = text_align
        self.align = align
        self.text_path = path
        self.position_on_path = position_on_path
        self.single_line_width = single_line_width
        self.rotation = rotation
        self.mode = mode

        text_string = Compound.make_text(
            txt=txt,
            font_size=font_size,
            font=font,
            font_path=font_path,
            font_style=font_style,
            text_align=text_align,
            align=align,
            position_on_path=position_on_path,
            text_path=path,
            single_line_width=single_line_width,
        )
        super().__init__(text_string, rotation, None, mode)


class Trapezoid(BaseSketchObject):
    """Sketch Object: Trapezoid

    Create a trapezoid defined by major width, height, and interior angle(s).

    Args:
        width (float): trapezoid major width
        height (float): trapezoid height
        left_side_angle (float): bottom left interior angle
        right_side_angle (float, optional): bottom right interior angle. If not provided,
            the trapezoid will be symmetric. Defaults to None
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to (Align.CENTER, Align.CENTER)
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: Give angles result in an invalid trapezoid
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        left_side_angle: float,
        right_side_angle: float | None = None,
        rotation: float = 0,
        align: Align | tuple[Align, Align] | None = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        right_side_angle = left_side_angle if not right_side_angle else right_side_angle

        self.width = width
        self.trapezoid_height = height
        self.left_side_angle = left_side_angle
        self.right_side_angle = right_side_angle
        self.align = tuplify(align, 2)

        # Calculate the reduction of the top on both sides
        reduction_left = (
            0 if left_side_angle == 90 else height / tan(radians(left_side_angle))
        )
        reduction_right = (
            0 if right_side_angle == 90 else height / tan(radians(right_side_angle))
        )

        top_width_left = width / 2
        top_width_right = width / 2
        bot_width_left = width / 2
        bot_width_right = width / 2

        if reduction_left > 0:
            top_width_left -= reduction_left
        else:
            bot_width_left += reduction_left

        if reduction_right > 0:
            top_width_right -= reduction_right
        else:
            bot_width_right += reduction_right

        if (bot_width_left + bot_width_right) < 0:
            raise ValueError("Trapezoid bottom invalid - change angles")
        if (top_width_left + top_width_right) < 0:
            raise ValueError("Trapezoid top invalid - change angles")

        pts = []
        pts.append(Vector(-bot_width_left, -height / 2))
        pts.append(Vector(bot_width_right, -height / 2))
        pts.append(Vector(top_width_right, height / 2))
        pts.append(Vector(-top_width_left, height / 2))
        pts.append(pts[0])
        face = Face(Wire.make_polygon(pts))
        super().__init__(face, rotation, self.align, mode)


class Triangle(BaseSketchObject):
    """Sketch Object: Triangle

    Create a triangle defined by one side length and any of two other side lengths or interior
    angles. The interior angles are opposite the side with the same designation
    (i.e. side 'a' is opposite angle 'A'). Side 'a' is the bottom side, followed by 'b'
    on the right, going counter-clockwise.

    Args:
        a (float, optional): side 'a' length. Defaults to None
        b (float, optional): side 'b' length. Defaults to None
        c (float, optional): side 'c' length. Defaults to None
        A (float, optional): interior angle 'A'. Defaults to None
        B (float, optional): interior angle 'B'. Defaults to None
        C (float, optional): interior angle 'C'. Defaults to None
        rotation (float, optional): angle to rotate object. Defaults to 0
        align (Align | tuple[Align, Align], optional): align MIN, CENTER, or MAX of object.
            Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.ADD

    Raises:
        ValueError: One length and two other values were not provided
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        *,
        a: float | None = None,
        b: float | None = None,
        c: float | None = None,
        A: float | None = None,
        B: float | None = None,
        C: float | None = None,
        align: Align | tuple[Align, Align] | None = None,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch | None = BuildSketch._get_context(self)
        validate_inputs(context, self)

        if [v is None for v in [a, b, c]].count(True) == 3 or [
            v is None for v in [a, b, c, A, B, C]
        ].count(True) != 3:
            raise ValueError("One length and two other values must be provided")

        A, B, C = (radians(angle) if angle is not None else None for angle in [A, B, C])
        ar, br, cr, Ar, Br, Cr = trianglesolver.solve(a, b, c, A, B, C)
        self.a = ar  #: length of side 'a'
        self.b = br  #: length of side 'b'
        self.c = cr  #: length of side 'c'
        self.A = degrees(Ar)  #: interior angle 'A' in degrees
        self.B = degrees(Br)  #: interior angle 'B' in degrees
        self.C = degrees(Cr)  #: interior angle 'C' in degrees
        triangle = Face(
            Wire.make_polygon(
                [Vector(0, 0), Vector(ar, 0), Vector(cr, 0).rotate(Axis.Z, self.B)]
            )
        )
        center_of_geometry = (
            sum((Vector(v) for v in triangle.vertices()), Vector(0, 0, 0)) / 3
        )
        triangle.move(Location(-center_of_geometry))
        alignment = None if align is None else tuplify(align, 2)
        super().__init__(obj=triangle, rotation=rotation, align=alignment, mode=mode)
        self.edge_a = self.edges().filter_by(lambda e: abs(e.length - ar) < TOLERANCE)[
            0
        ]  #: edge 'a'
        self.edge_b = self.edges().filter_by(
            lambda e: abs(e.length - br) < TOLERANCE and e not in [self.edge_a]
        )[
            0
        ]  #: edge 'b'
        self.edge_c = self.edges().filter_by(
            lambda e: e not in [self.edge_a, self.edge_b]
        )[
            0
        ]  #: edge 'c'
        self.vertex_A = topo_explore_common_vertex(
            self.edge_b, self.edge_c
        )  #: vertex 'A'
        assert isinstance(self.vertex_A, Vertex)
        self.vertex_A.topo_parent = self
        self.vertex_B = topo_explore_common_vertex(
            self.edge_a, self.edge_c
        )  #: vertex 'B'
        assert isinstance(self.vertex_B, Vertex)
        self.vertex_B.topo_parent = self
        self.vertex_C = topo_explore_common_vertex(
            self.edge_a, self.edge_b
        )  #: vertex 'C'
        assert isinstance(self.vertex_C, Vertex)
        self.vertex_C.topo_parent = self
