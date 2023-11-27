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

from math import cos, pi, radians, sin, tan
from typing import Union

from build123d.build_common import LocationList, validate_inputs
from build123d.build_enums import Align, FontStyle, Mode
from build123d.build_sketch import BuildSketch
from build123d.geometry import Axis, Location, Rotation, Vector, VectorLike
from build123d.topology import Compound, Edge, Face, ShapeList, Sketch, Wire, tuplify


class BaseSketchObject(Sketch):
    """BaseSketchObject

    Base class for all BuildSketch objects

    Args:
        face (Face): face to create
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        obj: Union[Compound, Face],
        rotation: float = 0,
        align: Union[Align, tuple[Align, Align]] = None,
        mode: Mode = Mode.ADD,
    ):
        if align is not None:
            align = tuplify(align, 2)
            obj.move(Location(Vector(*obj.bounding_box().to_align_offset(align))))

        context: BuildSketch = BuildSketch._get_context(self, log=False)
        if context is None:
            new_faces = obj.moved(Rotation(0, 0, rotation)).faces()

        else:
            self.rotation = rotation
            self.mode = mode

            obj = obj.moved(Rotation(0, 0, rotation))

            new_faces = [
                face.moved(location)
                for face in obj.faces()
                for location in LocationList._get_context().local_locations
            ]
            if isinstance(context, BuildSketch):
                context._add_to_context(*new_faces, mode=mode)

        super().__init__(Compound.make_compound(new_faces).wrapped)


class Circle(BaseSketchObject):
    """Sketch Object: Circle

    Add circle(s) to the sketch.

    Args:
        radius (float): circle size
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        radius: float,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.radius = radius
        self.align = tuplify(align, 2)

        face = Face.make_from_wires(Wire.make_circle(radius))
        super().__init__(face, 0, self.align, mode)


class Ellipse(BaseSketchObject):
    """Sketch Object: Ellipse

    Add ellipse(s) to sketch.

    Args:
        x_radius (float): horizontal radius
        y_radius (float): vertical radius
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        x_radius: float,
        y_radius: float,
        rotation: float = 0,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.x_radius = x_radius
        self.y_radius = y_radius
        self.align = tuplify(align, 2)

        face = Face.make_from_wires(Wire.make_ellipse(x_radius, y_radius))
        super().__init__(face, rotation, self.align, mode)


class Polygon(BaseSketchObject):
    """Sketch Object: Polygon

    Add polygon(s) defined by given sequence of points to sketch.

    Args:
        pts (VectorLike): sequence of points with a counter-clockwise winding order that define the polygon's vertices
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        *pts: VectorLike,
        rotation: float = 0,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.pts = pts
        self.align = tuplify(align, 2)

        poly_pts = [Vector(p) for p in pts]
        face = Face.make_from_wires(Wire.make_polygon(poly_pts))
        super().__init__(face, rotation, self.align, mode)


class Rectangle(BaseSketchObject):
    """Sketch Object: Rectangle

    Add rectangle(s) to sketch.

    Args:
        width (float): horizontal size
        height (float): vertical size
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.width = width
        self.rectangle_height = height
        self.align = tuplify(align, 2)

        face = Face.make_rect(height, width)
        super().__init__(face, rotation, self.align, mode)


class RectangleRounded(BaseSketchObject):
    """Sketch Object: RectangleRounded

    Add rectangle(s) with filleted corners to sketch.

    Args:
        width (float): horizontal size
        height (float): vertical size
        radius (float): fillet radius
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        radius: float,
        rotation: float = 0,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        if width <= 2 * radius or height <= 2 * radius:
            raise ValueError("width and height must be > 2*radius")
        self.width = width
        self.rectangle_height = height
        self.radius = radius
        self.align = tuplify(align, 2)

        face = Face.make_rect(height, width)
        face = face.fillet_2d(radius, face.vertices())
        super().__init__(face, rotation, align, mode)


class RegularPolygon(BaseSketchObject):
    """Sketch Object: Regular Polygon

    Add regular polygon(s) to sketch.

    Args:
        radius (float): distance from origin to vertices (major), or
            optionally from the origin to side (minor) with major_radius = False
        side_count (int): number of polygon sides
        major_radius (bool): If True the radius is the major radius, else the
            radius is the minor radius (also known as inscribed radius).
            Defaults to True.
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
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
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        if side_count < 3:
            raise ValueError(
                f"RegularPolygon must have at least three sides, not {side_count}"
            )

        if major_radius:
            rad = radius
        else:
            rad = radius / cos(pi / side_count)

        self.radius = rad
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

        if align is not None:
            align = tuplify(align, 2)
            align_offset = []
            for i in range(2):
                if align[i] == Align.MIN:
                    align_offset.append(-mins[i])
                elif align[i] == Align.CENTER:
                    align_offset.append(0)
                elif align[i] == Align.MAX:
                    align_offset.append(-maxs[i])
        else:
            align_offset = [0, 0]
        pts = [point + Vector(*align_offset) for point in pts]

        face = Face.make_from_wires(Wire.make_polygon(pts))
        super().__init__(face, rotation=0, align=None, mode=mode)


class SlotArc(BaseSketchObject):
    """Sketch Object: Arc Slot

    Add slot(s) following an arc to sketch.

    Args:
        arc (Union[Edge, Wire]): center line of slot
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        arc: Union[Edge, Wire],
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.arc = arc
        self.slot_height = height

        arc = arc if isinstance(arc, Wire) else Wire.make_wire([arc])
        face = Face.make_from_wires(arc.offset_2d(height / 2)).rotate(Axis.Z, rotation)
        super().__init__(face, rotation, None, mode)


class SlotCenterPoint(BaseSketchObject):
    """Sketch Object: Center Point Slot

    Add a slot(s) defined by the center of the slot and the center of one of the
    circular arcs at the end. The other end will be generated to create a symmetric
    slot.

    Args:
        center (VectorLike): slot center point
        point (VectorLike): slot center of arc point
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
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
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        center_v = Vector(center)
        point_v = Vector(point)
        self.slot_center = center_v
        self.point = point_v
        self.slot_height = height

        half_line = point_v - center_v
        face = Face.make_from_wires(
            Wire.combine(
                [
                    Edge.make_line(point_v, center_v),
                    Edge.make_line(center_v, center_v - half_line),
                ]
            )[0].offset_2d(height / 2)
        )
        super().__init__(face, rotation, None, mode)


class SlotCenterToCenter(BaseSketchObject):
    """Sketch Object: Center to Center points Slot

    Add slot(s) defined by the distance between the center of the two
    end arcs.

    Args:
        center_separation (float): distance between two arc centers
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        center_separation: float,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.center_separation = center_separation
        self.slot_height = height

        face = Face.make_from_wires(
            Wire.make_wire(
                [
                    Edge.make_line(Vector(-center_separation / 2, 0, 0), Vector()),
                    Edge.make_line(Vector(), Vector(+center_separation / 2, 0, 0)),
                ]
            ).offset_2d(height / 2)
        )
        super().__init__(face, rotation, None, mode)


class SlotOverall(BaseSketchObject):
    """Sketch Object: Center to Center points Slot

    Add slot(s) defined by the overall with of the slot.

    Args:
        width (float): overall width of the slot
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.width = width
        self.slot_height = height

        if width != height:
            face = Face.make_from_wires(
                Wire.make_wire(
                    [
                        Edge.make_line(Vector(-width / 2 + height / 2, 0, 0), Vector()),
                        Edge.make_line(Vector(), Vector(+width / 2 - height / 2, 0, 0)),
                    ]
                ).offset_2d(height / 2)
            )
        else:
            face = Circle(width/2, mode=mode).face()
        super().__init__(face, rotation, align, mode)


class Text(BaseSketchObject):
    """Sketch Object: Text

    Add text(s) to the sketch.

    Args:
        txt (str): text to be rendered
        font_size (float): size of the font in model units
        font (str, optional): font name. Defaults to "Arial".
        font_path (str, optional): system path to font library. Defaults to None.
        font_style (Font_Style, optional): style. Defaults to Font_Style.REGULAR.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        path (Union[Edge, Wire], optional): path for text to follow. Defaults to None.
        position_on_path (float, optional): the relative location on path to position the
            text, values must be between 0.0 and 1.0. Defaults to 0.0.
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """
    # pylint: disable=too-many-instance-attributes
    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        txt: str,
        font_size: float,
        font: str = "Arial",
        font_path: str = None,
        font_style: FontStyle = FontStyle.REGULAR,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        path: Union[Edge, Wire] = None,
        position_on_path: float = 0.0,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ) -> Compound:
        context = BuildSketch._get_context(self)
        validate_inputs(context, self)

        self.txt = txt
        self.font_size = font_size
        self.font = font
        self.font_path = font_path
        self.font_style = font_style
        self.align = align
        self.text_path = path
        self.position_on_path = position_on_path
        self.rotation = rotation
        self.mode = mode

        text_string = Compound.make_text(
            txt=txt,
            font_size=font_size,
            font=font,
            font_path=font_path,
            font_style=font_style,
            align=tuplify(align, 2),
            position_on_path=position_on_path,
            text_path=path,
        )
        super().__init__(text_string, rotation, None, mode)


class Trapezoid(BaseSketchObject):
    """Sketch Object: Trapezoid

    Add trapezoid(s) to the sketch.

    Args:
        width (float): horizontal width
        height (float): vertical height
        left_side_angle (float): bottom left interior angle
        right_side_angle (float, optional): bottom right interior angle. If not provided,
            the trapezoid will be symmetric. Defaults to None.
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (Union[Align, tuple[Align, Align]], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Give angles result in an invalid trapezoid
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        width: float,
        height: float,
        left_side_angle: float,
        right_side_angle: float = None,
        rotation: float = 0,
        align: Union[Align, tuple[Align, Align]] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        context = BuildSketch._get_context(self)
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
        if reduction_left + reduction_right >= width:
            raise ValueError("Trapezoid top invalid - change angles")
        pts = []
        pts.append(Vector(-width / 2, -height / 2))
        pts.append(Vector(width / 2, -height / 2))
        pts.append(Vector(width / 2 - reduction_right, height / 2))
        pts.append(Vector(-width / 2 + reduction_left, height / 2))
        pts.append(pts[0])
        face = Face.make_from_wires(Wire.make_polygon(pts))
        super().__init__(face, rotation, self.align, mode)
