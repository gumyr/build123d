"""
Drafting Objects

name: drafting.py
by:   Gumyr
date: September 16th 2023

desc:
    This python module contains objects using in building technical drawings as Sketches.

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

from dataclasses import dataclass
from datetime import date
from math import copysign, floor, gcd, log2, pi
from typing import ClassVar, Iterable, Optional, Union

from build123d.build_common import IN, MM
from build123d.build_enums import (
    Align,
    FontStyle,
    GeomType,
    HeadType,
    Mode,
    NumberDisplay,
    PageSize,
    Side,
    Unit,
)
from build123d.build_line import BuildLine
from build123d.build_sketch import BuildSketch
from build123d.geometry import Axis, Location, Plane, Pos, Vector, VectorLike
from build123d.objects_curve import Line, TangentArc
from build123d.objects_sketch import BaseSketchObject, Polygon, Text
from build123d.operations_generic import fillet, mirror, sweep
from build123d.operations_sketch import make_face, trace
from build123d.topology import Compound, Edge, Sketch, Vertex, Wire


class ArrowHead(BaseSketchObject):
    """Sketch Object: ArrowHead

    Args:
        size (float): tip to tail length
        head_type (HeadType, optional): arrow head shape. Defaults to HeadType.CURVED.
        rotation (float, optional): rotation in degrees. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        size: float,
        head_type: HeadType = HeadType.CURVED,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        with BuildSketch() as arrow_head:
            if head_type == HeadType.CURVED:
                with BuildLine():
                    side = TangentArc(
                        (0, 0), (-size, size / 3), tangent=(-size, size / 6)
                    )
                    Line(side @ 1, (-7 * size / 8, 0))
                    mirror(about=Plane.XZ)
                make_face()
            elif head_type == HeadType.STRAIGHT:
                Polygon((-size, size / 3), (-size, -size / 3), (0, 0), align=None)
            elif head_type == HeadType.FILLETED:
                ArrowHead(size, head_type=HeadType.CURVED)
                fillet(
                    arrow_head.vertices().filter_by_position(
                        Axis.X, -2 * size, -size / 5
                    ),
                    radius=size / 20,
                )

        super().__init__(arrow_head.sketch, rotation=rotation, align=None, mode=mode)


class Arrow(BaseSketchObject):
    """Sketch Object: Arrow with shaft

    Args:
        arrow_size (float): arrow head tip to tail length
        shaft_path (Union[Edge, Wire]): line describing the shaft shape
        shaft_width (float): line width of shaft
        head_at_start (bool, optional): Defaults to True.
        head_type (HeadType, optional): arrow head shape. Defaults to HeadType.CURVED.
        mode (Mode, optional): _description_. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag]

    def __init__(
        self,
        arrow_size: float,
        shaft_path: Union[Edge, Wire],
        shaft_width: float,
        head_at_start: bool = True,
        head_type: HeadType = HeadType.CURVED,
        mode: Mode = Mode.ADD,
    ):
        angle = (
            shaft_path.tangent_angle_at(0) + 180
            if head_at_start
            else shaft_path.tangent_angle_at(1)
        )
        # Create the arrow head
        arrow_head = ArrowHead(
            size=arrow_size, rotation=angle, head_type=head_type, mode=Mode.PRIVATE
        ).moved(Location(shaft_path.position_at(int(not head_at_start))))

        # Trim the path so the tip of the arrow isn't lost
        trim_amount = (arrow_size / 2) / shaft_path.length
        if head_at_start:
            shaft_path = shaft_path.trim(trim_amount, 1.0)
        else:
            shaft_path = shaft_path.trim(0.0, 1.0 - trim_amount)

        # Create a perpendicular line to sweep the tail path
        shaft_pen = shaft_path.perpendicular_line(shaft_width, 0)
        shaft = sweep(shaft_pen, shaft_path, mode=Mode.PRIVATE)

        arrow = arrow_head.fuse(shaft).clean()

        super().__init__(arrow, rotation=0, align=None, mode=mode)


PathDescriptor = Union[
    Wire,
    Edge,
    list[Union[Vector, Vertex, tuple[float, float, float]]],
]
PointLike = Union[Vector, Vertex, tuple[float, float, float]]


@dataclass
class Draft:
    """Draft

    Documenting build123d designs with dimension and extension lines as well as callouts.


    Args:
        font_size (float): size of the text in dimension lines and callouts. Defaults to 5.0.
        font (str): font to use for text. Defaults to "Arial".
        font_style: text style. Defaults to FontStyle.REGULAR.
        head_type (HeadType, optional): arrow head shape. Defaults to HeadType.CURVED.
        arrow_length (float): arrow head length. Defaults to 3.0.
        line_width (float): thickness of all lines. Defaults to 0.5.
        pad_around_text (float): amount of padding around text. Defaults to 2.0.
        unit (Unit): measurement unit. Defaults to Unit.MM.
        number_display (NumberDisplay): numbers as decimal or fractions.
            Default to NumberDisplay.DECIMAL.
        display_units (bool): control the display of units with numbers. Defaults to True.
        decimal_precision (int): number of decimal places when displaying numbers. Defaults to 2.
        fractional_precision (int): maximum fraction denominator - must be a factor of 2.
            Defaults to 64.
        extension_gap (float): gap between the point and start of extension line in extension_line.
            Defaults to 2.0.

    """

    # pylint: disable=too-many-instance-attributes

    # Class Attributes
    unit_LUT: ClassVar[dict] = {True: "mm", False: '"'}

    font_size: float = 5.0
    font: str = "Arial"
    font_style: FontStyle = FontStyle.REGULAR
    head_type: HeadType = HeadType.CURVED
    arrow_length: float = 3.0
    line_width: float = 0.5
    pad_around_text: float = 2.0
    unit: Unit = Unit.MM
    number_display: NumberDisplay = NumberDisplay.DECIMAL
    display_units: bool = True
    decimal_precision: int = 2
    fractional_precision: int = 64
    extension_gap: float = 2.0

    @property
    def is_metric(self) -> bool:
        """Are metric units being used"""
        return self.unit in [Unit.MM, Unit.CM, Unit.M, Unit.MC]

    def __post_init__(self):
        """Validate inputs"""
        if not log2(self.fractional_precision).is_integer():
            raise ValueError(
                f"fractional_precision values must be a factor of 2 not {self.fractional_precision}"
            )

    def _round_to_str(self, number: float) -> str:
        """Round a float but remove decimal if appropriate and convert to str"""
        return (
            f"{round(number, self.decimal_precision):.{self.decimal_precision}f}"
            if self.decimal_precision > 0
            else str(int(round(number, self.decimal_precision)))
        )

    def _number_with_units(
        self,
        number: float,
        tolerance: Union[float, tuple[float, float]] = None,
        display_units: Optional[bool] = None,
    ) -> str:
        """Convert a raw number to a unit of measurement string based on the class settings"""

        def simplify_fraction(numerator: int, denominator: int) -> tuple[int, int]:
            """Mathematically simplify a fraction given a numerator and demoninator"""
            greatest_common_demoninator = gcd(numerator, denominator)
            return (
                int(numerator / greatest_common_demoninator),
                int(denominator / greatest_common_demoninator),
            )

        if display_units is None:
            if tolerance is None:
                qualified_display_units = self.display_units
            else:
                qualified_display_units = False
        else:
            qualified_display_units = display_units

        unit_str = Draft.unit_LUT[self.is_metric] if qualified_display_units else ""
        if tolerance is None:
            tolerance_str = ""
        elif isinstance(tolerance, float):
            tolerance_str = f" ±{self._number_with_units(tolerance)}"
        else:
            tolerance_str = (
                f" +{self._number_with_units(tolerance[0],display_units=False)}"
                f" -{self._number_with_units(tolerance[1])}"
            )
        if self.is_metric or self.number_display == NumberDisplay.DECIMAL:
            unit_lut = {True: MM, False: IN}
            measurement = self._round_to_str(number / unit_lut[self.is_metric])
            return_value = f"{measurement}{unit_str}{tolerance_str}"
        else:
            whole_part = floor(number / IN)
            (numerator, demoninator) = simplify_fraction(
                round((number / IN - whole_part) * self.fractional_precision),
                self.fractional_precision,
            )
            if whole_part == 0:
                return_value = f"{numerator}/{demoninator}{unit_str}{tolerance_str}"
            else:
                return_value = (
                    f"{whole_part} {numerator}/{demoninator}{unit_str}{tolerance_str}"
                )

        return return_value

    @staticmethod
    def _process_path(path: PathDescriptor) -> Union[Edge, Wire]:
        """Convert a PathDescriptor into a Edge/Wire"""
        if isinstance(path, (Edge, Wire)):
            processed_path = path
        elif isinstance(path, Iterable):
            pnts = [
                Vector(p.to_tuple()) if isinstance(p, Vertex) else Vector(p)
                for p in path
            ]
            if len(pnts) == 2:
                processed_path = Edge.make_line(*pnts)
            else:
                processed_path = Wire.make_polygon(pnts, close=False)
        else:
            raise ValueError("Unsupported patch descriptor")
        # processed_path = Plane.XY.to_local_coords(processed_path)

        return processed_path

    def _label_to_str(
        self,
        label: str,
        line_wire: Wire,
        label_angle: bool,
        tolerance: Optional[Union[float, tuple[float, float]]],
    ) -> str:
        """Create the str to use as the label text"""
        line_length = line_wire.length
        if label is not None:
            label_str = label
        elif label_angle:
            arc_edges = line_wire.edges().filter_by(GeomType.CIRCLE)
            if len(arc_edges) == 0:
                raise ValueError(
                    "label_angle requested but the path is not part of a circle"
                )
            arc_edge = arc_edges[0]
            arc_size = 360 * line_length / (2 * pi * arc_edge.radius)
            label_str = f"{self._round_to_str(arc_size)}°"
        else:
            label_str = self._number_with_units(line_length, tolerance)
        return label_str

    @staticmethod
    def _sketch_location(
        path: Union[Edge, Wire], u_value: float, flip: bool = False
    ) -> Location:
        """Given a path on Plane.XY, determine the Location for object placement"""
        angle = path.tangent_angle_at(u_value) + int(flip) * 180
        return Location(path.position_at(u_value), (0, 0, 1), angle)


class DimensionLine(BaseSketchObject):
    """Sketch Object: DimensionLine

    Create a dimension line typically for internal measurements.
    Typically used for (but not restricted to) inside dimensions, a dimension line often
    as arrows on either side of a dimension or label.

    There are three options depending on the size of the text and length
    of the dimension line:
    Type 1) The label and arrows fit within the length of the path
    Type 2) The text fit within the path and the arrows go outside
    Type 3) Neither the text nor the arrows fit within the path

    Args:
        path (PathDescriptor): a very general type of input used to describe the path the
            dimension line will follow.
        draft (Draft): instance of Draft dataclass
        sketch (Sketch): the Sketch being created to check for possible overlaps. In builder
            mode the active Sketch will be used if None is provided.
        label (str, optional): a text string which will replace the length (or
            arc length) that would otherwise be extracted from the provided path. Providing
            a label is useful when illustrating a parameterized input where the name of an
            argument is desired not an actual measurement. Defaults to None.
        arrows (tuple[bool, bool], optional): a pair of boolean values controlling the placement
            of the start and end arrows. Defaults to (True, True).
        tolerance (Union[float, tuple[float, float]], optional): an optional tolerance
            value to add to the extracted length value. If a single tolerance value is provided
            it is shown as ± the provided value while a pair of values are shown as
            separate + and - values. Defaults to None.
        label_angle (bool, optional): a flag indicating that instead of an extracted length value,
            the size of the circular arc extracted from the path should be displayed in degrees.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Only 2 points allowed for dimension lines
        ValueError: No output - no arrows selected

    """

    def __init__(
        self,
        path: PathDescriptor,
        draft: Draft = None,
        sketch: Sketch = None,
        label: str = None,
        arrows: tuple[bool, bool] = (True, True),
        tolerance: Union[float, tuple[float, float]] = None,
        label_angle: bool = False,
        mode: Mode = Mode.ADD,
    ) -> Sketch:
        # pylint: disable=too-many-locals

        context = BuildSketch._get_context(self)
        if sketch is None and not (context is None or context.sketch is None):
            sketch = context.sketch

        # Create a wire modelling the path of the dimension lines from a variety of input types
        if isinstance(path, Iterable) and len(path) > 2:
            raise ValueError("Only two points are allowed for dimension lines")
        path_obj = Draft._process_path(path)  # Edge or Wire
        path_length = path_obj.length

        self.dimension = path_length  #: length of the dimension

        # Generate the label
        label_str = draft._label_to_str(label, path_obj, label_angle, tolerance)
        label_shape = Text(
            txt=label_str,
            font_size=draft.font_size,
            font=draft.font,
            font_style=draft.font_style,
            align=Align.CENTER,
            mode=Mode.PRIVATE,
        )
        label_length = label_shape.bounding_box().size.X

        # Calculate the arrow shaft length for up to three types
        if arrows.count(True) == 0:
            raise ValueError("No output - no arrows selected")
        if label_length + arrows.count(True) * draft.arrow_length < path_length:
            shaft_length = (path_length - label_length) / 2 - draft.pad_around_text
            shaft_pair = [
                path_obj.trim(0.0, shaft_length / path_length),
                path_obj.trim(1.0 - shaft_length / path_length, 1.0),
            ]
        else:
            shaft_length = 2 * draft.arrow_length
            shaft_pair = [
                Edge.make_line(
                    path_obj @ 0,
                    path_obj @ 0 - (path_obj % 0) * 2 * draft.arrow_length,
                ),
                Edge.make_line(
                    path_obj @ 1 + (path_obj % 1) * 2 * draft.arrow_length,
                    path_obj @ 1,
                ),
            ]

        arrow_shapes = []
        for i, shaft in enumerate(shaft_pair):
            flip_head = (shaft.position_at(i) != path_obj.position_at(i)) == bool(i)
            arrow_shapes.append(
                Arrow(
                    draft.arrow_length,
                    shaft,
                    draft.line_width,
                    flip_head,
                    draft.head_type,
                    mode=Mode.PRIVATE,
                )
            )
        # Calculate the possible locations for the label
        overage = shaft_length + draft.pad_around_text + label_length / 2
        label_u_values = [0.5, -overage / path_length, 1 + overage / path_length]

        # d_lines = Sketch(children=arrows[0])
        d_lines = {}
        # for arrow_pair in arrow_shapes:
        for u_value in label_u_values:
            d_line = Sketch()
            for add_arrow, arrow_shape in zip(arrows, arrow_shapes):
                if add_arrow:
                    d_line += arrow_shape
            flip_label = path_obj.tangent_at(u_value).get_angle(Vector(1, 0, 0)) >= 180
            loc = Draft._sketch_location(path_obj, u_value, flip_label)
            placed_label = label_shape.located(loc)
            self_intersection = d_line.intersect(placed_label).area
            d_line += placed_label
            bbox_size = d_line.bounding_box().size

            # Minimize size while avoiding intersections
            common_area = 0.0 if sketch is None else d_line.intersect(sketch).area
            common_area += self_intersection
            score = (d_line.area - 10 * common_area) / bbox_size.X
            d_lines[d_line] = score

        # Sort by score to find the best option
        d_lines = sorted(d_lines.items(), key=lambda x: x[1])

        super().__init__(obj=d_lines[-1][0], rotation=0, align=None, mode=mode)


class ExtensionLine(BaseSketchObject):
    """Sketch Object: Extension Line

    Create a dimension line with two lines extending outward from the part to dimension.
    Typically used for (but not restricted to) outside dimensions, with a pair of lines
    extending from the edge of a part to a dimension line.

    Args:
        border (PathDescriptor): a very general type of input defining the object to
            be dimensioned. Typically this value would be extracted from the part but is
            not restricted to this use.
        offset (float): a distance to displace the dimension line from the edge of the object
        draft (Draft): instance of Draft dataclass
        label (str, optional): a text string which will replace the length (or arc length)
            that would otherwise be extracted from the provided path. Providing a label is
            useful when illustrating a parameterized input where the name of an argument
            is desired not an actual measurement. Defaults to None.
        arrows (tuple[bool, bool], optional): a pair of boolean values controlling the placement
            of the start and end arrows. Defaults to (True, True).
        tolerance (Union[float, tuple[float, float]], optional): an optional tolerance
            value to add to the extracted length value. If a single tolerance value is provided
            it is shown as ± the provided value while a pair of values are shown as
            separate + and - values. Defaults to None.
        label_angle (bool, optional): a flag indicating that instead of an extracted length
            value, the size of the circular arc extracted from the path should be displayed
            in degrees. Defaults to False.
        project_line (Vector, optional): Vector line which to project dimension against.
            Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    """

    def __init__(
        self,
        border: PathDescriptor,
        offset: float,
        draft: Draft,
        sketch: Sketch = None,
        label: str = None,
        arrows: tuple[bool, bool] = (True, True),
        tolerance: Union[float, tuple[float, float]] = None,
        label_angle: bool = False,
        project_line: VectorLike = None,
        mode: Mode = Mode.ADD,
    ):
        # pylint: disable=too-many-locals

        context = BuildSketch._get_context(self)
        if sketch is None and not (context is None or context.sketch is None):
            sketch = context.sketch
        if project_line is not None:
            raise NotImplementedError("project_line is currently unsupported")

        # Create a wire modelling the path of the dimension lines from a variety of input types
        object_to_measure = Draft._process_path(border)

        side_lut = {1: Side.RIGHT, -1: Side.LEFT}

        if offset == 0:
            raise ValueError("A dimension line should be used if offset is 0")
        dimension_path = object_to_measure.offset_2d(
            distance=offset, side=side_lut[copysign(1, offset)], closed=False
        )

        extension_lines = [
            Edge.make_line(
                object_to_measure.position_at(e), dimension_path.position_at(e)
            )
            for e in [0, 1]
        ]
        # If the dimension path was created backwards, flip the extension lines
        if abs(extension_lines[0].length - abs(offset)) > 1e-4:
            extension_lines = [
                Edge.make_line(
                    object_to_measure.position_at(e), dimension_path.position_at(1 - e)
                )
                for e in [0, 1]
            ]

        # Move the extension lines away from the object
        extension_lines = [
            extension_line.moved(
                Location(extension_line.tangent_at(0) * draft.extension_gap)
            )
            for extension_line in extension_lines
        ]

        # Build the extension line sketch
        e_lines = []
        for extension_line in extension_lines:
            line_pen = extension_line.perpendicular_line(draft.line_width, 0)
            e_line_shape = sweep(line_pen, extension_line, mode=Mode.PRIVATE)
            e_lines.append(e_line_shape)
        d_line = DimensionLine(
            dimension_path,
            draft,
            sketch,
            label,
            arrows,
            tolerance,
            label_angle,
            mode=Mode.PRIVATE,
        )
        self.dimension = d_line.dimension  #: length of the dimension

        e_line_sketch = Sketch(children=e_lines + d_line.faces())

        super().__init__(obj=e_line_sketch, rotation=0, align=None, mode=mode)


class TechnicalDrawing(BaseSketchObject):
    """Sketch Object: TechnicalDrawing

    The border of a technical drawing with external frame and text box.

    Args:
        designed_by (str, optional): Defaults to "build123d".
        design_date (date, optional): Defaults to date.today().
        page_size (PageSize, optional): Defaults to PageSize.A4.
        title (str, optional): drawing title. Defaults to "Title".
        sub_title (str, optional): drawing sub title. Defaults to "Sub Title".
        drawing_number (str, optional): Defaults to "B3D-1".
        sheet_number (int, optional): Defaults to None.
        drawing_scale (float, optional): displays as 1:value. Defaults to 1.0.
        nominal_text_size (float, optional): size of title text. Defaults to 10.0.
        line_width (float, optional): Defaults to 0.5.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    page_sizes = {
        PageSize.A0: (1189 * MM, 841 * MM),
        PageSize.A1: (841 * MM, 594 * MM),
        PageSize.A2: (594 * MM, 420 * MM),
        PageSize.A3: (420 * MM, 297 * MM),
        PageSize.A4: (297 * MM, 210 * MM),
        PageSize.A5: (210 * MM, 148.5 * MM),
        PageSize.A6: (148.5 * MM, 105 * MM),
        PageSize.A7: (105 * MM, 74 * MM),
        PageSize.A8: (74 * MM, 52 * MM),
        PageSize.A9: (52 * MM, 37 * MM),
        PageSize.A10: (37 * MM, 26 * MM),
        PageSize.LETTER: (11 * IN, 8.5 * IN),
        PageSize.LEGAL: (14 * IN, 8.5 * IN),
        PageSize.LEDGER: (17 * IN, 11 * IN),
    }
    margin = 5 * MM

    def __init__(
        self,
        designed_by: str = "build123d",
        design_date: date = date.today(),
        page_size: PageSize = PageSize.A4,
        title: str = "Title",
        sub_title: str = "Sub Title",
        drawing_number: str = "B3D-1",
        sheet_number: int = None,
        drawing_scale: float = 1.0,
        nominal_text_size: float = 10.0,
        line_width: float = 0.5,
        mode: Mode = Mode.ADD,
    ):
        # pylint: disable=too-many-locals

        page_dim = TechnicalDrawing.page_sizes[page_size]
        # Frame
        frame_width = page_dim[0] - 2 * TechnicalDrawing.margin - 2 * nominal_text_size
        frame_height = 2 * frame_width / 3
        frame_wire = Wire.make_polygon(
            [
                (-frame_width / 2, frame_height / 2),
                (frame_width / 2, frame_height / 2),
                (frame_width / 2, -frame_height / 2),
                (-frame_width / 2, -frame_height / 2),
            ],
        )
        frame = trace(frame_wire, line_width, mode=Mode.PRIVATE)
        # Ticks
        tick_lines = []
        for i in range(20):
            if i in [0, 6, 10, 16]:  # corners
                continue
            u_value = i / 20
            pos = frame_wire.position_at(u_value)
            tick_lines.append(
                Edge.make_line(
                    pos,
                    pos
                    + Vector(nominal_text_size, 0).rotate(
                        Axis.Z, frame_wire.tangent_angle_at(u_value) + 90
                    ),
                )
            )
        ticks = trace(tick_lines, line_width, mode=Mode.PRIVATE)
        # Numbers
        grid_labels = Sketch()
        y_centers = {0: -3 / 8, 1: -1 / 8, 2: 1 / 8, 3: 3 / 8}
        for label in range(4):
            for x_index in [-0.5, 0.5]:
                grid_labels += Pos(
                    x_index * (frame_width + 1.5 * nominal_text_size),
                    y_centers[label] * frame_height,
                ) * Sketch(
                    Compound.make_text(str(label + 1), nominal_text_size).wrapped
                )

        # Letters
        x_centers = {
            0: -5 / 12,
            1: -3 / 12,
            2: -1 / 12,
            3: 1 / 12,
            4: 3 / 12,
            5: 5 / 12,
        }
        for i, label in enumerate(["F", "E", "D", "C", "B", "A"]):
            for y_index in [-0.5, 0.5]:
                grid_labels += Pos(
                    x_centers[i] * frame_width,
                    y_index * (frame_height + 1.5 * nominal_text_size),
                ) * Sketch(Compound.make_text(label, nominal_text_size).wrapped)

        # Text Box Frame
        bf_pnt1 = frame_wire.edges().sort_by(Axis.Y)[0] @ 0.5
        bf_pnt2 = frame_wire.edges().sort_by(Axis.X)[-1] @ 0.75
        box_frame_curve = Wire.make_polygon(
            [bf_pnt1, (bf_pnt1.X, bf_pnt2.Y), bf_pnt2], close=False
        )
        bf_pnt3 = box_frame_curve.edges().sort_by(Axis.X)[0] @ (1 / 3)
        bf_pnt4 = box_frame_curve.edges().sort_by(Axis.X)[0] @ (2 / 3)
        box_frame_curve += Edge.make_line(bf_pnt3, (bf_pnt2.X, bf_pnt3.Y))
        box_frame_curve += Edge.make_line(bf_pnt4, (bf_pnt2.X, bf_pnt4.Y))
        bf_pnt5 = box_frame_curve.edges().sort_by(Axis.Y)[-1] @ (1 / 3)
        bf_pnt6 = box_frame_curve.edges().sort_by(Axis.Y)[-1] @ (2 / 3)
        box_frame_curve += Edge.make_line(bf_pnt5, (bf_pnt5.X, bf_pnt1.Y))
        start = Vector(bf_pnt6.X, bf_pnt1.Y)
        box_frame_curve += Edge.make_line(
            start, start + Vector(0, (bf_pnt2.Y - bf_pnt1.Y) / 3)
        )
        box_frame = trace(box_frame_curve, line_width, mode=Mode.PRIVATE)
        # Text
        labels = Sketch()
        t_base_line1 = Edge.make_line(bf_pnt1, (bf_pnt1.X, bf_pnt2.Y)).moved(
            Location((nominal_text_size / 5, 0))
        )
        t_base_line2 = t_base_line1.moved(Location((frame_width / 6, 0)))
        t_base_line3 = t_base_line1.moved(Location((2 * frame_width / 6, 0)))
        labels += Pos(t_base_line1 @ (11 / 12)) * Sketch(
            Compound.make_text(
                "DESIGNED BY:", nominal_text_size / 3, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        labels += Pos(t_base_line1 @ (9 / 12)) * Sketch(
            Compound.make_text(
                designed_by, nominal_text_size / 2, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        labels += Pos(t_base_line1 @ (7 / 12)) * Sketch(
            Compound.make_text(
                "DATE:", nominal_text_size / 3, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        labels += Pos(t_base_line1 @ (5 / 12)) * Sketch(
            Compound.make_text(
                design_date.isoformat(),
                nominal_text_size / 2,
                align=(Align.MIN, Align.CENTER),
            ).wrapped
        )
        labels += Pos(t_base_line1 @ (3 / 12)) * Sketch(
            Compound.make_text(
                "SCALE:", nominal_text_size / 3, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        labels += Pos(t_base_line1 @ (1 / 12)) * Sketch(
            Compound.make_text(
                "1:" + str(drawing_scale),
                nominal_text_size / 2,
                align=(Align.MIN, Align.CENTER),
            ).wrapped
        )
        labels += Pos(t_base_line2 @ (10 / 12)) * Sketch(
            Compound.make_text(
                title, nominal_text_size, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        labels += Pos(t_base_line2 @ (6 / 12)) * Sketch(
            Compound.make_text(
                sub_title, nominal_text_size, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        labels += Pos(t_base_line2 @ (3 / 12)) * Sketch(
            Compound.make_text(
                "DRAWING NUMBER:",
                nominal_text_size / 3,
                align=(Align.MIN, Align.CENTER),
            ).wrapped
        )
        labels += Pos(t_base_line2 @ (1 / 12)) * Sketch(
            Compound.make_text(
                drawing_number, nominal_text_size / 2, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        labels += Pos(t_base_line3 @ (3 / 12)) * Sketch(
            Compound.make_text(
                "SHEET:", nominal_text_size / 3, align=(Align.MIN, Align.CENTER)
            ).wrapped
        )
        if sheet_number is not None:
            labels += Pos(t_base_line3 @ (1 / 12)) * Sketch(
                Compound.make_text(
                    str(sheet_number),
                    nominal_text_size / 2,
                    align=(Align.MIN, Align.CENTER),
                ).wrapped
            )

        technical_drawing = Compound(
            children=[frame, ticks, grid_labels, box_frame, labels]
        )

        super().__init__(obj=technical_drawing, rotation=0, align=None, mode=mode)
