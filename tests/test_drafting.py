"""
drafting unittests

name: test_drafting.py
by:   Gumyr
date: September 17th, 2023

desc:
    This python module contains the unittests for the drafting functionality.

license:

    Copyright 2023 Gumyr

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

import math
import unittest
from datetime import date

import pytest

from build123d import (
    IN,
    Axis,
    BuildLine,
    BuildSketch,
    CenterOf,
    Color,
    Compound,
    Edge,
    Face,
    FontStyle,
    GeomType,
    HeadType,
    Mode,
    NumberDisplay,
    Polyline,
    RadiusArc,
    Rectangle,
    Sketch,
    Text,
    Unit,
    Vector,
    insert,
    make_face,
    offset,
)
from build123d.drafting import (
    ArrowHead,
    DimensionLine,
    Draft,
    ExtensionLine,
    TechnicalDrawing,
)

metric = Draft(
    font_size=3.0,
    font="Arial",
    font_style=FontStyle.REGULAR,
    head_type=HeadType.CURVED,
    arrow_length=3.0,
    line_width=0.25,
    unit=Unit.MM,
    number_display=NumberDisplay.DECIMAL,
    display_units=True,
    decimal_precision=2,
    fractional_precision=64,
    extension_gap=2.0,
)
imperial = Draft(
    font_size=5.0,
    font="Arial",
    font_style=FontStyle.REGULAR,
    head_type=HeadType.CURVED,
    arrow_length=3.0,
    line_width=0.25,
    unit=Unit.IN,
    number_display=NumberDisplay.FRACTION,
    display_units=True,
    decimal_precision=2,
    fractional_precision=64,
    extension_gap=2.0,
)


def create_test_sketch() -> tuple[Sketch, Sketch, Sketch]:
    with BuildSketch() as sketchy:
        with BuildLine():
            l1 = Polyline((10, 20), (-20, 20), (-20, -20), (10, -20))
            RadiusArc(l1 @ 0, l1 @ 1, 25)
        make_face()
        outside = sketchy.sketch
        inside = offset(amount=-0.5, mode=Mode.SUBTRACT)
    return (sketchy.sketch, outside, inside)


class TestClassInstantiation(unittest.TestCase):
    """Test Draft class instantiation"""

    def test_draft_instantiation(self):
        """Parameter parsing"""
        with self.assertRaises(ValueError):
            Draft(fractional_precision=37)


class TestDraftFunctionality(unittest.TestCase):
    """Test core drafting functionality"""

    def test_number_with_units(self):
        metric_drawing = Draft(decimal_precision=2)
        self.assertEqual(metric_drawing._number_with_units(3.141), "3.14mm")
        self.assertEqual(metric_drawing._number_with_units(3.149), "3.15mm")
        self.assertEqual(metric_drawing._number_with_units(0), "0.00mm")
        self.assertEqual(
            metric_drawing._number_with_units(3.14, tolerance=0.01), "3.14 ±0.01mm"
        )
        self.assertEqual(
            metric_drawing._number_with_units(3.14, tolerance=(0.01, 0)),
            "3.14 +0.01 -0.00mm",
        )
        whole_number_drawing = Draft(decimal_precision=-1)
        self.assertEqual(whole_number_drawing._number_with_units(314.1), "310mm")

        imperial_drawing = Draft(unit=Unit.IN)
        self.assertEqual(imperial_drawing._number_with_units((5 / 8) * IN), '0.62"')
        imperial_fractional_drawing = Draft(
            unit=Unit.IN, number_display=NumberDisplay.FRACTION, fractional_precision=64
        )
        self.assertEqual(
            imperial_fractional_drawing._number_with_units((5 / 8) * IN), '5/8"'
        )
        self.assertEqual(
            imperial_fractional_drawing._number_with_units(math.pi * IN), '3 9/64"'
        )
        imperial_fractional_drawing.fractional_precision = 16
        self.assertEqual(
            imperial_fractional_drawing._number_with_units(math.pi * IN), '3 1/8"'
        )

    def test_label_to_str(self):
        metric_drawing = Draft(decimal_precision=0)
        line = Edge.make_line((0, 0, 0), (100, 0, 0))
        with self.assertRaises(ValueError):
            metric_drawing._label_to_str(
                label=None,
                line_wire=line,
                label_angle=True,
                tolerance=0,
            )
        arc1 = Edge.make_circle(100, start_angle=0, end_angle=30)
        angle_str = metric_drawing._label_to_str(
            label=None,
            line_wire=arc1,
            label_angle=True,
            tolerance=0,
        )
        self.assertEqual(angle_str, "30°")


class ArrowHeadTests(unittest.TestCase):
    def test_arrowhead_types(self):
        arrow = ArrowHead(10, HeadType.CURVED)
        bbox = arrow.bounding_box()
        self.assertEqual(len(arrow.edges().filter_by(GeomType.CIRCLE)), 2)
        self.assertAlmostEqual(bbox.size.X, 10, 5)

        arrow = ArrowHead(10, HeadType.FILLETED)
        bbox = arrow.bounding_box()
        self.assertEqual(len(arrow.edges().filter_by(GeomType.CIRCLE)), 5)
        self.assertLess(bbox.size.X, 10)

        arrow = ArrowHead(10, HeadType.STRAIGHT)
        self.assertEqual(len(arrow.edges().filter_by(GeomType.CIRCLE)), 0)
        bbox = arrow.bounding_box()
        self.assertAlmostEqual(bbox.size.X, 10, 5)


class DimensionLineTestCase(unittest.TestCase):
    def test_two_points(self):
        d_line = DimensionLine([(0, 0, 0), (100, 0, 0)], draft=metric)
        bbox = d_line.bounding_box()
        self.assertAlmostEqual(bbox.max.X, 100, 5)
        self.assertAlmostEqual(d_line.dimension, 100, 5)
        self.assertEqual(len(d_line.faces()), 10)

    def test_three_points(self):
        with self.assertRaises(ValueError):
            DimensionLine([(0, 0, 0), (50, 0, 0), (50, 50, 0)], draft=metric)

    def test_edge(self):
        d_line = DimensionLine(Edge.make_line((0, 0), (100, 0)), draft=metric)
        bbox = d_line.bounding_box()
        self.assertAlmostEqual(bbox.max.X, 100, 5)
        self.assertEqual(len(d_line.faces()), 10)

    def test_vertices(self):
        d_line = DimensionLine(
            Edge.make_line((0, 0), (100, 0)).vertices(), draft=metric
        )
        bbox = d_line.bounding_box()
        self.assertAlmostEqual(bbox.max.X, 100, 5)
        self.assertEqual(len(d_line.faces()), 10)

    def test_label(self):
        d_line = DimensionLine([(0, 0, 0), (100, 0, 0)], label="Test", draft=metric)
        bbox = d_line.bounding_box()
        self.assertAlmostEqual(bbox.max.X, 100, 5)
        self.assertEqual(len(d_line.faces()), 6)

    def test_face(self):
        with self.assertRaises(ValueError):
            DimensionLine(Face.make_rect(100, 100), draft=metric)

    def test_builder_mode(self):
        with BuildSketch() as s1:
            Rectangle(100, 100)
            hole = offset(amount=-5, mode=Mode.SUBTRACT)
            d_line = DimensionLine(
                [
                    hole.vertices().group_by(Axis.Y)[-1].sort_by(Axis.X)[-1],
                    hole.vertices().group_by(Axis.Y)[0].sort_by(Axis.X)[0],
                ],
                draft=metric,
            )
        area = sum(f.area for f in hole.intersect(d_line).faces())
        self.assertGreater(area, 0)

    def test_outside_arrows(self):
        d_line = DimensionLine([(0, 0, 0), (15, 0, 0)], draft=metric)
        bbox = d_line.bounding_box()
        self.assertAlmostEqual(bbox.size.X, 15 + 4 * metric.arrow_length, 5)
        self.assertAlmostEqual(d_line.dimension, 15, 5)
        self.assertEqual(len(d_line.faces()), 9)

    def test_outside_label(self):
        d_line = DimensionLine([(0, 0, 0), (5, 0, 0)], draft=metric)
        bbox = d_line.bounding_box()
        self.assertGreater(bbox.size.X, 5 + 4 * metric.arrow_length)
        self.assertAlmostEqual(d_line.dimension, 5, 5)
        self.assertEqual(len(d_line.faces()), 8)

    def test_single_outside_label(self):
        d_line = DimensionLine(
            [(0, 0, 0), (5, 0, 0)], draft=metric, arrows=(False, True)
        )
        bbox = d_line.bounding_box()
        self.assertAlmostEqual(bbox.min.X, 5, 5)
        self.assertAlmostEqual(d_line.dimension, 5, 5)
        self.assertEqual(len(d_line.faces()), 7)

    def test_no_arrows(self):
        with self.assertRaises(ValueError):
            DimensionLine([(0, 0, 0), (5, 0, 0)], draft=metric, arrows=(False, False))

    def test_vertical(self):
        d_line = DimensionLine([(0, 0), (0, 100)], Draft())
        bbox = d_line.bounding_box()
        self.assertAlmostEqual(bbox.size.Y, 100, 5)  # numbers within

    def test_padding_consumes_available_shaft_does_not_crash(self):
        """Padding must not create an empty shaft for a single arrow."""
        label = "Test"
        label_length = (
            Text(
                label,
                font_size=metric.font_size,
                font=metric.font,
                font_style=metric.font_style,
            )
            .bounding_box()
            .size.X
        )
        path_length = label_length + 2 * metric.pad_around_text
        d_line = DimensionLine(
            Edge.make_line((0, 0), (path_length, 0)),
            draft=metric,
            label=label,
            arrows=(False, True),
        )
        self.assertGreater(len(d_line.edges()), 0)

    def test_minimum_internal_shaft_does_not_crash(self):
        """An arrow must not consume the entire internal shaft."""
        label = "Test"
        label_length = (
            Text(
                label,
                font_size=metric.font_size,
                font=metric.font,
                font_style=metric.font_style,
            )
            .bounding_box()
            .size.X
        )
        path_length = label_length + 2 * metric.pad_around_text + metric.arrow_length
        d_line = DimensionLine(
            Edge.make_line((0, 0), (path_length, 0)), draft=metric, label=label
        )
        self.assertGreater(len(d_line.edges()), 0)


class ExtensionLineTestCase(unittest.TestCase):
    def test_min_x(self):
        shape, outer, inner = create_test_sketch()
        e_line = ExtensionLine(
            outer.edges().sort_by(Axis.X)[0], offset=10, draft=metric
        )
        bbox = e_line.bounding_box()
        self.assertAlmostEqual(bbox.size.Y, 40 + metric.line_width, 5)
        self.assertAlmostEqual(bbox.size.X, 10, 5)

        with self.assertRaises(ValueError):
            ExtensionLine(outer.edges().sort_by(Axis.X)[0], offset=0, draft=metric)

    def test_builder_mode(self):
        shape, outer, inner = create_test_sketch()
        with BuildSketch() as test:
            insert(shape)
            e_line = ExtensionLine(
                outer.edges().sort_by(Axis.Y)[0], offset=10, draft=metric
            )

        bbox = e_line.bounding_box()
        self.assertAlmostEqual(bbox.size.X, 30 + metric.line_width, 5)
        self.assertAlmostEqual(bbox.size.Y, 10, 5)

    def test_vectorlike_in_extension_function(self):
        diagonal_line = Edge.make_line((100, 100), (200, 200))
        ext = ExtensionLine(
            border=diagonal_line,
            offset=-10,
            draft=metric,
            measurement_direction=(0, 1, 0),
        )
        self.assertIsNotNone(ext)

    def test_vertical_projection_with_dim_outside_shape(self):
        diagonal_line = Edge.make_line((100, 100), (200, 200))
        ext = ExtensionLine(
            border=diagonal_line,
            offset=-10,
            draft=metric,
            measurement_direction=Vector(0, 1, 0),
        )
        self.assertIsNotNone(ext)
        self.assertGreater(
            Compound(children=[diagonal_line, ext]).bounding_box().size.X,
            diagonal_line.bounding_box().size.X,
        )  # dimension should be outside shape.
        self.assertEqual(
            diagonal_line.bounding_box().size.Y + 0.25,  # plus line_width
            ext.bounding_box().size.Y,
        )
        self.assertEqual(
            diagonal_line.center(CenterOf.BOUNDING_BOX).Y,
            ext.center(CenterOf.BOUNDING_BOX).Y,
        )
        self.assertEqual(ext.dimension, 100)

    def test_vertical_projection_with_dim_inside_shape(self):
        diagonal_line = Edge.make_line((100, 100), (200, 200))
        ext = ExtensionLine(
            border=diagonal_line,
            offset=10,
            draft=metric,
            measurement_direction=Vector(0, 1, 0),
        )
        self.assertIsNotNone(ext)
        self.assertEqual(
            Compound(children=[diagonal_line, ext]).bounding_box().size.Y,
            diagonal_line.bounding_box().size.Y + 0.25,
        )  # plus line_width
        self.assertEqual(
            diagonal_line.center(CenterOf.BOUNDING_BOX).Y,
            ext.center(CenterOf.BOUNDING_BOX).Y,
        )
        self.assertEqual(ext.dimension, 100)

    def test_vertical_projection_with_dim_otherside(self):
        diagonal_line = Edge.make_line((100, 100), (200, 200))
        x_size = diagonal_line.bounding_box().size.X
        ext = ExtensionLine(
            border=diagonal_line,
            offset=x_size + 10,
            draft=metric,
            measurement_direction=Vector(0, 1, 0),
        )
        self.assertIsNotNone(ext)
        self.assertGreater(
            Compound(children=[diagonal_line, ext]).bounding_box().size.Y,
            diagonal_line.bounding_box().size.Y,
        )  # plus line_width
        self.assertEqual(
            diagonal_line.center(CenterOf.BOUNDING_BOX).Y,
            ext.center(CenterOf.BOUNDING_BOX).Y,
        )
        self.assertEqual(ext.dimension, 100)

    def test_vertical_projection_with_vertical_line(self):
        diagonal_line = Edge.make_line((100, 100), (100, 200))
        ext = ExtensionLine(
            border=diagonal_line,
            offset=10,
            draft=metric,
            measurement_direction=Vector(0, 1, 0),
        )
        self.assertIsNotNone(ext)
        self.assertEqual(
            diagonal_line.center(CenterOf.BOUNDING_BOX).Y,
            ext.center(CenterOf.BOUNDING_BOX).Y,
        )
        self.assertEqual(ext.dimension, 100)

    def test_horizontal_projection_with_dim_outside_shape(self):
        diagonal_line = Edge.make_line((100, 100), (200, 200))
        ext = ExtensionLine(
            border=diagonal_line,
            offset=10,
            draft=metric,
            measurement_direction=Vector(1, 0, 0),
        )
        self.assertIsNotNone(ext)
        self.assertGreater(
            Compound(children=[diagonal_line, ext]).bounding_box().size.Y,
            diagonal_line.bounding_box().size.Y,
        )  # dimension should be outside shape.
        self.assertEqual(
            diagonal_line.bounding_box().size.X + 0.25,  # plus line_width
            ext.bounding_box().size.X,
        )
        self.assertEqual(
            diagonal_line.center(CenterOf.BOUNDING_BOX).X,
            ext.center(CenterOf.BOUNDING_BOX).X,
        )
        self.assertEqual(ext.dimension, 100)

    def test_angled_projection(self):
        diagonal_line = Edge.make_line((100, 100), (200, 200))
        ext = ExtensionLine(
            border=diagonal_line,
            offset=10,
            draft=metric,
            measurement_direction=Vector(1, 1, 0),
        )
        self.assertIsNotNone(ext)
        self.assertAlmostEqual(ext.dimension, 141.421, places=2)

    def test_half_circle(self):
        half_circle = Edge.make_circle(50, start_angle=0, end_angle=180)
        ext = ExtensionLine(
            border=half_circle,
            offset=-10,
            draft=metric,
            measurement_direction=Vector(1, 0, 0),
        )
        self.assertIsNotNone(ext)
        self.assertEqual(ext.dimension, 100)
        self.assertGreater(
            Compound(children=[half_circle, ext]).bounding_box().size.Y,
            half_circle.bounding_box().size.Y,
        )  # dimension should be outside shape.

    def test_full_circle(self):
        half_circle = Edge.make_circle(50)
        with pytest.raises(ValueError):
            ExtensionLine(
                border=half_circle,
                offset=10,
                draft=metric,
                measurement_direction=Vector(0, 1, 0),
            )

    def test_vector_offset_above_horizontal_edge(self):
        """A vector offset places the dimension on the side it points to."""
        edge = Edge.make_line((0, 0), (40, 0))
        above = ExtensionLine(border=edge, offset=(0, 10), draft=metric)
        below = ExtensionLine(border=edge, offset=(0, -10), draft=metric)
        self.assertGreater(above.center(CenterOf.BOUNDING_BOX).Y, 0)
        self.assertLess(below.center(CenterOf.BOUNDING_BOX).Y, 0)

    def test_vector_offset_left_right_of_vertical_edge(self):
        """A vector offset on a vertical edge chooses left/right by direction."""
        edge = Edge.make_line((0, 0), (0, 40))
        right = ExtensionLine(border=edge, offset=(10, 0), draft=metric)
        left = ExtensionLine(border=edge, offset=(-10, 0), draft=metric)
        self.assertGreater(right.center(CenterOf.BOUNDING_BOX).X, 0)
        self.assertLess(left.center(CenterOf.BOUNDING_BOX).X, 0)

    def test_vector_offset_magnitude_matches_scalar(self):
        """A vector offset matches the equivalent signed-scalar offset.

        On a horizontal edge, offset=(0, 10) (up) is equivalent to scalar offset=-10.
        """
        edge = Edge.make_line((0, 0), (40, 0))
        by_vector = ExtensionLine(border=edge, offset=(0, 10), draft=metric)
        by_scalar = ExtensionLine(border=edge, offset=-10, draft=metric)
        vbb, sbb = by_vector.bounding_box(), by_scalar.bounding_box()
        self.assertAlmostEqual(vbb.min.Y, sbb.min.Y, places=4)
        self.assertAlmostEqual(vbb.max.Y, sbb.max.Y, places=4)
        self.assertAlmostEqual(by_vector.dimension, by_scalar.dimension, places=4)

    def test_vector_offset_infers_measurement_direction(self):
        """With no measurement_direction the dimension runs perpendicular to the offset:
        a vertical offset on a diagonal border measures the horizontal extent."""
        diagonal = Edge.make_line((0, 0), (10, 10))
        ext = ExtensionLine(border=diagonal, offset=(0, 5), draft=metric)
        self.assertAlmostEqual(ext.dimension, 10, places=4)
        self.assertGreater(ext.center(CenterOf.BOUNDING_BOX).Y, 0)

    def test_vector_offset_perpendicular_to_measurement_direction(self):
        """A vector offset perpendicular to an explicit measurement_direction works."""
        diagonal = Edge.make_line((0, 0), (10, 10))
        ext = ExtensionLine(
            border=diagonal,
            offset=(0, 5),
            draft=metric,
            measurement_direction=Vector(1, 0, 0),
        )
        self.assertAlmostEqual(ext.dimension, 10, places=4)

    def test_vector_offset_parallel_to_measurement_direction_raises(self):
        """A vector offset parallel to measurement_direction is rejected."""
        diagonal = Edge.make_line((0, 0), (10, 10))
        with self.assertRaises(ValueError):
            ExtensionLine(
                border=diagonal,
                offset=(5, 0),
                draft=metric,
                measurement_direction=Vector(1, 0, 0),
            )

    def test_zero_vector_offset_raises(self):
        """A zero-length vector offset is rejected with a clear error."""
        edge = Edge.make_line((0, 0), (40, 0))
        with self.assertRaises(ValueError):
            ExtensionLine(border=edge, offset=(0, 0, 0), draft=metric)

    def test_out_of_plane_vector_offset_raises(self):
        """A vector offset outside Plane.XY is rejected."""
        edge = Edge.make_line((0, 0), (40, 0))
        with self.assertRaises(ValueError):
            ExtensionLine(border=edge, offset=(0, 10, 0.1), draft=metric)

    def test_out_of_plane_measurement_direction_raises(self):
        """A measurement direction outside Plane.XY is rejected."""
        edge = Edge.make_line((0, 0), (40, 40))
        with self.assertRaises(ValueError):
            ExtensionLine(
                border=edge,
                offset=(0, 10),
                draft=metric,
                measurement_direction=(1, 0, 0.1),
            )

    def test_zero_measurement_direction_raises(self):
        """A zero-length measurement_direction is rejected with a clear error."""
        edge = Edge.make_line((0, 0), (40, 0))
        with self.assertRaises(ValueError):
            ExtensionLine(
                border=edge,
                offset=(0, 10),
                draft=metric,
                measurement_direction=Vector(0, 0, 0),
            )

    def test_degenerate_projection_raises(self):
        """An offset whose inferred measurement direction has no border extent
        (e.g. a vertical offset on a vertical border) is rejected, not crashed."""
        vertical = Edge.make_line((0, 0), (0, 40))
        with self.assertRaises(ValueError):
            ExtensionLine(border=vertical, offset=(0, 5), draft=metric)


@pytest.mark.parametrize("design_date", [date(2023, 9, 17), None])
def test_basic_drawing(design_date):
    drawing = TechnicalDrawing(design_date=design_date, sheet_number=1)
    bbox = drawing.bounding_box()
    assert bbox.size.X > 280
    assert bbox.size.Y > 195
    assert len(drawing.faces()) > 110


if __name__ == "__main__":
    unittest.main()
