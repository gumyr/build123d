"""
Section drawings for the Holes page: the four kinds of hole side by side in one
plate, then each one alone, dimensioned with the arguments that set it, then a
blind hole with a drill point.
"""

from math import radians, sin, tan

from build123d import *

drafting_options = Draft(
    font_size=1.4, arrow_length=1.2, line_width=0.1, pad_around_text=0.6
)


def section(part: Part) -> tuple[Face | Compound, ShapeList[Edge]]:
    """The cut face on Plane.XZ and the edges seen beyond it, laid flat: X right,
    Z up"""
    cut = Plane.XZ.to_local_coords(part & Plane.XZ * Rectangle(1000, 1000))
    # Seen from the cut, the half beyond it shows the far side of each hole: the
    # circles where one diameter steps to the next, drawn as lines across the hole
    far_half = part & Box(
        1000, 1000, 1000, align=(Align.CENTER, Align.MIN, Align.CENTER)
    )
    visible, _ = far_half.project_to_viewport((0, -1000, 0), look_at=(0, 0, 0))
    return cut, visible


def write_section(name: str, part: Part, dimensions=(), centers=(), scale=4):
    """Save a section of part, with its dimensions and center lines, as SVG"""
    cut, visible = section(part)
    exporter = ExportSVG(unit=Unit.MM, scale=scale, margin=2)
    exporter.add_layer("Hatch", fill_color=(0.86, 0.86, 0.86), line_weight=0)
    exporter.add_layer("Visible", line_weight=0.35)
    exporter.add_layer("Dimensions", line_weight=0.12, fill_color="black")
    exporter.add_layer("Center", line_type=LineType.ISO_DASH_DOT, line_weight=0.15)
    exporter.add_shape(cut, layer="Hatch")
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(list(dimensions), layer="Dimensions")
    exporter.add_shape(list(centers), layer="Center")
    exporter.write(f"assets/{name}.svg")


def width(x: float, y: float, offset: float, label: str) -> ExtensionLine:
    """Dimension from -x to x at height y, drawn offset above it"""
    return ExtensionLine(
        border=((-x, y), (x, y)),
        offset=(0, offset),
        draft=drafting_options,
        label=label,
    )


def height(x: float, y0: float, y1: float, offset: float, label: str):
    """Dimension from y0 to y1 at x, drawn offset to the right of it"""
    return ExtensionLine(
        border=((x, y0), (x, y1)),
        offset=(offset, 0),
        draft=drafting_options,
        label=label,
    )


def cone_angle(tip: Vector, angle: float, arc_radius: float, label: str, down=False):
    """Included angle of a cone whose tip is on the axis, opening up (or down)"""
    start = (270 if down else 90) - angle / 2
    return DimensionLine(
        CenterArc(tip, arc_radius, start, angle), draft=drafting_options, label=label
    )


def axis(top: float, bottom: float, x: float = 0) -> Edge:
    """Center line of a hole, a little past both ends"""
    return Line((x, top + 3), (x, bottom - 3))


# [Hole types]
with BuildPart() as plate:
    Box(100, 20, 12, align=(Align.CENTER, Align.CENTER, Align.MAX))
    with Locations((-37.5, 0)):
        Hole(radius=3)
    with Locations((-12.5, 0)):
        CounterSinkHole(radius=3, counter_sink_radius=6)
    with Locations((12.5, 0)):
        CounterBoreHole(radius=3, counter_bore_radius=6, counter_bore_depth=5)
    with Locations((37.5, 0)):
        CounterDrillHole(radius=3, counter_drill_radius=6, counter_drill_depth=4)
# [Hole types]
hole_x = (-37.5, -12.5, 12.5, 37.5)
names = ("Hole", "CounterSinkHole", "CounterBoreHole", "CounterDrillHole")
write_section(
    "hole_types",
    plate.part,
    dimensions=[Pos(x, 6) * Text(name, 2.6) for x, name in zip(hole_x, names)],
    centers=[axis(0, -12, x) for x in hole_x],
    scale=3,
)

# Each kind alone in a block, blind so that depth has a bottom to point at. The
# dimensions stand outside the block, at x = ±outside
radius, counter_radius, depth = 5, 10, 32
outside = 35

# [Hole]
with BuildPart() as hole:
    Box(60, 60, 42, align=(Align.CENTER, Align.CENTER, Align.MAX))
    Hole(radius=5, depth=32)
# [Hole]
write_section(
    "hole_section",
    hole.part,
    dimensions=[
        width(radius, 0, 5, "2 × radius"),
        height(-radius, 0, -depth, radius - outside, "depth"),
    ],
    centers=[axis(0, -depth)],
)

# [CounterSinkHole]
with BuildPart() as counter_sink:
    Box(60, 60, 42, align=(Align.CENTER, Align.CENTER, Align.MAX))
    CounterSinkHole(radius=5, counter_sink_radius=10, depth=32, counter_sink_angle=82)
# [CounterSinkHole]
sink_angle = 82
sink_height = counter_radius / tan(radians(sink_angle / 2))
sink_tip = Vector(0, -sink_height)
# The angle is shown above the part, between the cone's generatrices extended
sink_arc = 1.3 * counter_radius / sin(radians(sink_angle / 2))
write_section(
    "counter_sink_hole_section",
    counter_sink.part,
    dimensions=[
        width(counter_radius, 0, sink_arc - sink_height + 5, "2 × counter_sink_radius"),
        width(radius, -depth, 4, "2 × radius"),
        height(-radius, 0, -depth, radius - outside, "depth"),
        cone_angle(sink_tip, sink_angle, sink_arc, "counter_sink_angle"),
    ],
    centers=[
        axis(0, -depth),
        *[
            Line(
                sink_tip + Vector(side * radius, radius / counter_radius * sink_height),
                sink_tip + Vector(side * counter_radius, sink_height) * 1.4,
            )
            for side in (-1, 1)
        ],
    ],
)

# [CounterBoreHole]
with BuildPart() as counter_bore:
    Box(60, 60, 42, align=(Align.CENTER, Align.CENTER, Align.MAX))
    CounterBoreHole(radius=5, counter_bore_radius=10, counter_bore_depth=16, depth=32)
# [CounterBoreHole]
bore_depth = 16
write_section(
    "counter_bore_hole_section",
    counter_bore.part,
    dimensions=[
        width(counter_radius, 0, 5, "2 × counter_bore_radius"),
        width(radius, -depth, 4, "2 × radius"),
        height(
            counter_radius,
            0,
            -bore_depth,
            outside - counter_radius,
            "counter_bore_depth",
        ),
        height(-counter_radius, 0, -depth, counter_radius - outside, "depth"),
    ],
    centers=[axis(0, -depth)],
)

# [CounterDrillHole]
with BuildPart() as counter_drill:
    Box(60, 60, 42, align=(Align.CENTER, Align.CENTER, Align.MAX))
    CounterDrillHole(
        radius=5,
        counter_drill_radius=10,
        counter_drill_depth=16,
        depth=32,
        counter_drill_angle=118,
    )
# [CounterDrillHole]
drill_depth, drill_angle = 16, 118
drill_tip = Vector(0, -drill_depth - counter_radius / tan(radians(drill_angle / 2)))
# The angle spans the step itself: the arc's ends lie on the cone, across the hole
drill_arc = 0.8 * counter_radius / sin(radians(drill_angle / 2))
write_section(
    "counter_drill_hole_section",
    counter_drill.part,
    dimensions=[
        width(counter_radius, 0, 5, "2 × counter_drill_radius"),
        width(radius, -depth, 4, "2 × radius"),
        height(
            counter_radius,
            0,
            -drill_depth,
            outside - counter_radius,
            "counter_drill_depth",
        ),
        height(-counter_radius, 0, -depth, counter_radius - outside, "depth"),
        cone_angle(drill_tip, drill_angle, drill_arc, "counter_drill_angle"),
    ],
    centers=[axis(0, -depth)],
)

# [Drill point]
with BuildPart() as drilled:
    Box(40, 40, 30, align=(Align.CENTER, Align.CENTER, Align.MAX))
    Hole(radius=5, depth=12, point_angle=118)
# [Drill point]
point_radius, point_depth, point_angle = 5, 12, 118
point_height = point_radius / tan(radians(point_angle / 2))
point_tip = Vector(0, -point_depth - point_height)
# The angle is shown below the tip, between the cone's generatrices extended
point_arc = 9
write_section(
    "hole_drill_point",
    drilled.part,
    dimensions=[
        width(point_radius, 0, 4, "2 × radius"),
        height(-point_radius, 0, -point_depth, -6, "depth"),
        ExtensionLine(
            border=((point_radius, -point_depth), point_tip),
            offset=(6, 0),
            draft=drafting_options,
            label="h",
        ),
        cone_angle(point_tip, point_angle, point_arc, "point_angle", down=True),
        Pos(0, -33) * Text("h = radius / tan(point_angle / 2)", 1.6),
    ],
    centers=[
        axis(0, point_tip.Y - point_arc),
        *[
            Line(
                point_tip,
                point_tip
                + Vector(side * point_radius, -point_height)
                * (point_arc + 1)
                / point_radius,
            )
            for side in (-1, 1)
        ],
    ],
)
