"""
Too Tall Toby's sm_hanger — BuildSheet edition

name: ttt_sm_hanger_buildsheet.py
by:   Gabriel Jesus
date: July 22nd 2026

desc:
    The same sheet metal part as ttt-23-02-02-sm_hanger.py, built with the
    BuildSheet API: one flat base sketch and flange folds. Every dimension
    below comes straight off the TTT drawing — no manual bend-allowance
    constants (the original needs 1.526 * sheet_thickness and
    PolarLine(..., 20.371288916) to pre-compensate the bends).

license:

    Copyright 2026 Gabriel Jesus

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

from math import atan, degrees, radians, sin, tan

from build123d import *
from ocp_vscode import *

thickness = 4 * MM
outer_radius = 7 * MM  # every bend fillet on the TTT drawing
inner_radius = outer_radius - thickness

# drawing dimensions
top_z = 65 * MM  # top surface height
overall_half_x = 170 / 2 * MM  # to the outside of the sloped legs
plate_width = 80 * MM  # top plate span in Y
leg_angle = 60  # slope from horizontal
leg_width = 112.52 * MM  # legs widen to this across the slope
wing_angle = 75
wing_span_x = 110 * MM
tab_hole_z = 80 * MM


# tangent trim at a bend: the flat region ends where the outer-radius arc
# starts, r * tan(bend_angle / 2) before the sharp-corner intersection
def trim(bend_angle: float) -> float:
    return outer_radius * tan(radians(bend_angle / 2))


plate_half_x = overall_half_x - trim(leg_angle)
slope_flat = 65 / sin(radians(leg_angle)) - trim(leg_angle) - trim(120)
foot_flat = 65 / tan(radians(leg_angle)) - trim(120)
taper_miter = -degrees(atan(((leg_width - plate_width) / 2) / slope_flat))
wing_half_y = (plate_width / 2 + 46.104 - 40) - trim(wing_angle)
wing_flat = 20.371288916 - trim(wing_angle)  # == 15.0 exactly
tab_flat_end_x = 28 - trim(90)  # tab bends up to a face at x = +/-28
tab_leg = 88 - (top_z - thickness) - outer_radius

with BuildSheet(thickness=thickness, bend_radius=inner_radius) as sm_hanger:
    with BuildSketch(Plane.XY.offset(top_z - thickness)) as base:
        Rectangle(2 * plate_half_x, plate_width)
        Rectangle(wing_span_x, 2 * wing_half_y)
        # central cutouts with rounded outer corners, one strip left for
        # each tab
        with Locations((20, 0)):
            Rectangle(30, 30, align=(Align.MIN, Align.CENTER), mode=Mode.SUBTRACT)
        with Locations((-20, 0)):
            Rectangle(30, 30, align=(Align.MAX, Align.CENTER), mode=Mode.SUBTRACT)
        fillet(
            base.vertices().filter_by(
                lambda v: abs(abs(v.X) - 50) < 1e-6 and abs(abs(v.Y) - 15) < 1e-6
            ),
            7,
        )
        with Locations((20, 0)):
            Rectangle(tab_flat_end_x - 20, 16, align=(Align.MIN, Align.CENTER))
        with Locations((-20, 0)):
            Rectangle(tab_flat_end_x - 20, 16, align=(Align.MAX, Align.CENTER))

    # NOTE: every flange REPLACES the sheet, so edges must be re-selected
    # from sm_hanger immediately before each call — never reuse a face or
    # edge captured before a previous flange (stale topology).

    # sloped legs, widening 80 -> 112.52 across the slope (negative miters)
    top_face = sm_hanger.faces().sort_by(Axis.Z)[-1]
    leg_edges = top_face.edges().filter_by(Axis.Y).sort_by(Axis.X)
    flange(
        [leg_edges[0], leg_edges[-1]],
        length=slope_flat,
        angle=leg_angle,
        miter_angle1=taper_miter,
        miter_angle2=taper_miter,
    )
    # feet: fold a further 120 degrees back to horizontal, tucking inward
    # under the legs. Each slope wall's free end has two leg_width-long
    # edges; the upper one (inner surface) folds the foot inward.
    foot_edges = (
        sm_hanger.edges()
        .filter_by(GeomType.LINE)
        .filter_by(lambda e: abs(e.length - leg_width) < 0.1)
        .group_by(Axis.Z)[1]
    )
    flange(foot_edges, length=foot_flat, angle=120)

    # wings at 75 degrees
    top_face = sm_hanger.faces().sort_by(Axis.Z)[-1]
    wing_edges = top_face.edges().filter_by(Axis.X).sort_by(Axis.Y)
    flange([wing_edges[0], wing_edges[-1]], length=wing_flat, angle=wing_angle)

    # tabs fold up from the strip ends. Select the plate-bottom (z = top_z
    # - thickness) thickness edge at each strip end so the fold goes up.
    tab_edges = sm_hanger.edges().filter_by(Axis.Y).filter_by(
        lambda e: abs(abs(e.center().X) - tab_flat_end_x) < 1e-6
        and abs(e.center().Z - (top_z - thickness)) < 1e-6
    )
    flange(tab_edges, length=tab_leg, angle=90)

    # corner rounds on foot / wing / tab tips (drawing R7, tab R5)
    fillet(sm_hanger.edges().filter_by(Axis.Z).group_by(Axis.Z)[0], 7)
    fillet(sm_hanger.edges().filter_by(Axis.X).group_by(Axis.Z)[-1], 5)

    # slot cutouts pierce the folded legs — prism cuts across bends
    with BuildSketch(Plane.XY.offset(top_z), mode=Mode.PRIVATE) as top_slots:
        SlotCenterPoint((154, 0), (154 / 2, 0), 20)
        SlotCenterPoint((-154, 0), (-154 / 2, 0), 20)
    extrude(top_slots.sketch, amount=-40, mode=Mode.SUBTRACT)
    with BuildSketch(Plane.XY, mode=Mode.PRIVATE) as bottom_slots:
        SlotCenterPoint((206, 0), (206 / 2, 0), 20)
        SlotCenterPoint((-206, 0), (-206 / 2, 0), 20)
    extrude(bottom_slots.sketch, amount=40, mode=Mode.SUBTRACT)
    # tab holes: one prism cut along X through both tabs
    with BuildSketch(Plane.YZ.offset(-50), mode=Mode.PRIVATE) as tab_hole:
        with Locations((0, tab_hole_z)):
            Circle(5)
    extrude(tab_hole.sketch, amount=100, mode=Mode.SUBTRACT)

got_mass = sm_hanger.sheet.volume * 7800 * 1e-6
want_mass = 1028
print(f"Mass: {got_mass:0.1f} g")
assert abs(got_mass - want_mass) < 10, f"{got_mass=}, {want_mass=}"

show(sm_hanger)
