from alg123d import *

clock_radius = 10

l1 = CenterArc((0, 0), clock_radius * 0.975, 0.75, 4.5)
l2 = CenterArc((0, 0), clock_radius * 0.925, 0.75, 4.5)
l3 = Line(l1 @ 0, l2 @ 0)
l4 = Line(l1 @ 1, l2 @ 1)
minute_indicator = make_face([l1, l3, l2, l4])
minute_indicator = fillet(
    minute_indicator, minute_indicator.vertices(), radius=clock_radius * 0.01
)

clock_face = Circle(clock_radius)
clock_face -= [loc * minute_indicator for loc in PolarLocations(0, 60)]


clock_face -= [
    loc * SlotOverall(clock_radius * 0.05, clock_radius * 0.025)
    for loc in PolarLocations(clock_radius * 0.875, 12)
]

clock_face -= [
    loc
    * Text(
        str(hour + 1),
        font_size=clock_radius * 0.175,
        font_style=FontStyle.BOLD,
        align=Align.CENTER,
    )
    for hour, loc in enumerate(
        PolarLocations(clock_radius * 0.75, 12, 60, -360, rotate=False)
    )
]

if "show_object" in locals():
    show_object(clock_face)
