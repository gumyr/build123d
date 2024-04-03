"""
Mini Nuke Example

name: mini_nuke.py
by:   Gumyr
date: April 3rd, 2024

desc:
    This example demonstrates the creation of a container featuring a screw top designed 
    after the "Mini Nuke" from the Fallout video game series. It showcases the process 
    of constructing intricate non-planar objects and leverages the bd_warehouse thread 
    and fastener library to create customize threads and Clearance Holes to match a variety
    of fasteners. The holes are positioned in locations that do not align with any primary 
    axes, illustrating advanced techniques in 3D object design.
    
license:

    Copyright 2024 Gumyr

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

import copy
from airfoils import Airfoil
from build123d import *
from bd_warehouse.fastener import ClearanceHole, CounterSunkScrew
from bd_warehouse.thread import IsoThread
from ocp_vscode import show, set_defaults, Camera

set_defaults(reset_camera=Camera.CENTER)

DIAMETER = 10 * CM
THICKNESS = 2
MULTIPART_FINS = True

#
# -------- Core Nuke Shape --------
#
airfoil = Airfoil.NACA4("0045")
aero_pnts = [Vector(p) for p in zip(airfoil._x_upper, airfoil._y_upper)]
aero_pnts_max_y = max(p.Y for p in aero_pnts)
aero_pnts_scaled = [p * (DIAMETER / 2) / aero_pnts_max_y for p in aero_pnts]

with BuildPart() as nuke_core:
    with BuildSketch(
        Plane((0, 0, 1.87 * DIAMETER), x_dir=(0, 0, -1), z_dir=(0, 1, 0))
    ) as nuke_profile:
        with BuildLine() as nuke_outline:
            aero = Spline(*aero_pnts_scaled[12:80])  # 200 points total
            nose = Spline(
                (-4.4, 0),
                aero @ 0,
                tangents=[(0, 1), aero % 0],
                tangent_scalars=(0.6, 1),
            )
            tail = Spline(
                aero @ 1,
                (1.54 * DIAMETER, 0),
                tangents=[aero % 1, (0, -1)],
                tangent_scalars=(1.25, 0.80),
            )
            mirror(about=Plane.XZ)
        make_face()
        offset(amount=-2 * MM, mode=Mode.SUBTRACT)  # Hollow it out
        split(bisect_by=Plane.XZ, keep=Keep.BOTTOM)

        with Locations(aero @ 0.6, aero @ 0.95):
            Circle(1 * MM)
        for line, param in [(nose, 1), (aero, 0.05), (aero, 0.3), (aero, 0.55)]:
            with Locations(line @ param):
                Rectangle(
                    2 * MM,
                    THICKNESS,
                    rotation=line.tangent_angle_at(param),
                    mode=Mode.SUBTRACT,
                )
        with Locations(tail @ 0.45):
            Rectangle(
                5 * MM,
                THICKNESS,
                rotation=tail.tangent_angle_at(0.45),
            )
    revolve()
    e_nose = nuke_core.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-2]
    nose_cone_limits = ((e_nose @ 0).Z, nuke_core.vertices().sort_by(Axis.Z)[-1].Z)
    e_body = nuke_core.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-4]
    nuke_body_limits = (nuke_core.vertices().sort_by(Axis.Z)[0].Z, (e_body @ 0).Z)
    # Used to position features below
    nuke_core_faces = nuke_core.faces().sort_by(Axis.Z)

#
# -------- Warning Ring --------
#
warning_ring_face = nuke_core_faces[-15]
warning_ring = thicken(warning_ring_face, -1 * MM)
warning_ring.color = Color("Gold")
warning_ring.label = "warning ring"

#
# -------- Fins --------
#

# Screws and screw heads
fin_screw = CounterSunkScrew(size="M1.4-0.3", length=3 * MM, fastener_type="iso2009")
# fin_screw_head = split(fin_screw, Plane.XY.offset(-fin_screw.head_height))
fin_screw.color = Color(0xC0C0C0)  # Silver
fin_screw.label = "fin screw"

with BuildPart() as fins:

    with BuildPart() as fin_outer_ring:
        with BuildSketch() as bs0:
            Circle(DIAMETER / 2)
            Circle(DIAMETER / 2 - THICKNESS, mode=Mode.SUBTRACT)
            # Only want 1/4 of the ring
            Rectangle(
                2 * DIAMETER,
                2 * DIAMETER,
                align=Align.MIN,
                rotation=45,
                mode=Mode.INTERSECT,
            )
        extrude(amount=28)
        with BuildSketch(Plane.XZ) as bs1:
            Trapezoid(
                DIAMETER / 2,
                DIAMETER * 0.19,
                84,
                align=(Align.CENTER, Align.MIN),
            )
            fillet(bs1.vertices().group_by(Axis.Y)[-1], DIAMETER * 0.04)
        projection = project(mode=Mode.PRIVATE).faces().sort_by(Axis.Y)[1]
        thicken(projection, amount=-THICKNESS, mode=Mode.SUBTRACT)
        # Replace to create the full ring
        with PolarLocations(0, 3, start_angle=90, angular_range=270):
            add(fin_outer_ring.part)

    # Used to position featues below
    outer_ring_face = fin_outer_ring.faces().sort_by(SortBy.AREA)[-1]

    with BuildPart() as fin_inner_ring:
        with BuildSketch(Plane.XY.offset(DIAMETER * 0.055)):
            Circle(DIAMETER * 0.18)
            Circle(DIAMETER * 0.18 - THICKNESS, mode=Mode.SUBTRACT)
        extrude(amount=DIAMETER * 0.15)

    with BuildPart() as fin_supports:
        with BuildSketch(Plane.XY.offset(10)) as fin_support_plan:
            Rectangle(DIAMETER + 2 * THICKNESS, THICKNESS, rotation=-45)
            Rectangle(DIAMETER + 2 * THICKNESS, THICKNESS, rotation=45)
            Circle(DIAMETER / 2 - THICKNESS, mode=Mode.INTERSECT)
            Circle(DIAMETER * 0.18, mode=Mode.SUBTRACT)
        extrude(until=Until.NEXT, target=nuke_core.part)
        with BuildSketch(Plane.XZ) as support_trim:
            Trapezoid(
                DIAMETER * 1.76, DIAMETER * 0.57, 45, align=(Align.CENTER, Align.MIN)
            )
            split(bisect_by=Plane.YZ)
        revolve(mode=Mode.INTERSECT)
        fin_contacts = fin_supports.faces().group_by(Axis.Z)[-2]
        fin_tabs = extrude(fin_contacts, amount=THICKNESS / 2, dir=(0, 0, 1))

    support_fillet_edges = (
        fins.edges().filter_by(Axis.Z).filter_by_position(Axis.Z, 0.0, DIAMETER * 0.275)
    )
    fillet(support_fillet_edges, DIAMETER * 0.06)
    if MULTIPART_FINS:
        fin_plan = section(section_by=Plane.XY.offset(DIAMETER * (0.28 + 0.10)))
        red_fins = extrude(fin_plan, amount=-DIAMETER * 0.28, mode=Mode.SUBTRACT)
        red_fins.color = Color("FireBrick")
        red_fins.label = "red fins"

    screw_uv_values = [(0.015, 0.15), (0.015, 0.55), (0.985, 0.15), (0.985, 0.55)]
    fin_screw_locs = []
    for angle in range(0, 360, 90):
        for u, v in screw_uv_values:
            position = outer_ring_face.position_at(u, v)
            normal = outer_ring_face.normal_at(position)
            fin_screw_locs.append(
                Rot(0, 0, angle) * Location(Plane(position, z_dir=normal))
            )

    with Locations(fin_screw_locs):
        ClearanceHole(fin_screw, depth=THICKNESS * 1.5, counter_sunk=True, fit="Close")

fins.part.color = Color("OliveDrab")
fins.part.label = "fins"

#
# -------- Nose --------
#

# Screws and screw heads
nose_screw = CounterSunkScrew(size="M3-0.5", length=10 * MM, fastener_type="iso14582")
nose_screw_head = split(nose_screw, Plane.XY.offset(-nose_screw.head_height))
nose_screw_head.color = Color(0xC0C0C0)  # Silver
nose_screw_head.label = "nose screw"

with BuildPart() as nose:
    add(nuke_core.part)
    split(bisect_by=Plane.XY.offset(nose_cone_limits[0]))
    bottom_inside_edge, bottom_edge = (
        nose.edges().group_by(Axis.Z)[0].sort_by(SortBy.LENGTH)
    )
    nose_face = nose.faces().sort_by(SortBy.AREA)[-1]
    # The edge isn't of type CIRCLE (even though it is) so calculate radius
    bottom_inside_edge_radius = bottom_inside_edge.bounding_box().size.X / 2

    # Thread
    with Locations((0, 0, bottom_edge.center().Z - (DIAMETER * 0.06 + 1 * MM))):
        nose_thread = IsoThread(
            major_diameter=2 * (bottom_edge.radius - 1 * MM),
            pitch=2 * MM,
            length=DIAMETER * 0.06,
            external=True,
            end_finishes=("fade", "square"),
        )
    with BuildSketch(Plane.XY.offset(bottom_edge.center().Z)):
        Circle(bottom_inside_edge_radius)
        Circle(nose_thread.min_radius - THICKNESS, mode=Mode.SUBTRACT)
    extrude(until=Until.NEXT)
    with BuildSketch(Plane.XY.offset(bottom_edge.center().Z)):
        Circle(bottom_edge.radius)
    cap = extrude(amount=-1 * MM, taper=45)
    with BuildSketch(cap.faces().sort_by(Axis.Z)[0]):
        Circle(nose_thread.min_radius - THICKNESS)
    extrude(amount=-1 * MM, mode=Mode.SUBTRACT)
    with BuildSketch(cap.faces().sort_by(Axis.Z)[0]):
        Circle(nose_thread.min_radius)
        Circle(nose_thread.min_radius - THICKNESS, mode=Mode.SUBTRACT)
    extrude(amount=DIAMETER * 0.06)

    # Nose cone screws
    nose_screw_ref_pnt = nose_face.position_at(0.0, 0.3)
    nose_screw_ref_nrm = nose_face.normal_at(nose_screw_ref_pnt)
    nose_screw_locs = [
        Rot(0, 0, angle) * Location(Plane(nose_screw_ref_pnt, z_dir=nose_screw_ref_nrm))
        for angle in range(0, 360, 45)
    ]
    with Locations(nose_screw_locs):
        ClearanceHole(nose_screw, fit="Close")

nose.part.color = Color("FireBrick")
nose.part.label = "nose"

#
# -------- Final Nuke Shape --------
#
top_screw = CounterSunkScrew(size="M4-0.7", length=10 * MM, fastener_type="iso14582")
top_screw_head = split(top_screw, Plane.XY.offset(-top_screw.head_height))
top_screw_head.color = Color(0xC0C0C0)  # Silver
top_screw_head.label = "top screw"

middle_screw = CounterSunkScrew(size="M6-1", length=10 * MM, fastener_type="iso14582")
middle_screw_head = split(middle_screw, Plane.XY.offset(-middle_screw.head_height))
middle_screw_head.color = Color(0xC0C0C0)  # Silver
middle_screw_head.label = "middle screw"

# Internal thread
nose_thread = IsoThread(
    major_diameter=2 * (bottom_edge.radius - 1 * MM),
    pitch=2 * MM,
    length=DIAMETER * 0.06,
    external=False,
    end_finishes=("square", "fade"),
)

with BuildPart() as nuke:
    add(nuke_core.part)
    split(bisect_by=Plane.XY.offset(nuke_body_limits[1]), keep=Keep.BOTTOM)

    # Create the thread
    top_edge = (
        nuke.edges()
        .filter_by(GeomType.CIRCLE)
        .group_by(Axis.Z)[-1]
        .sort_by(SortBy.LENGTH)[-1]
    )
    with BuildSketch(Plane.XY.offset(top_edge.center().Z)):
        Circle(top_edge.radius)
    extrude(amount=-DIAMETER * 0.06, taper=150)
    with BuildSketch(Plane.XY.offset(top_edge.center().Z)):
        Circle(nose_thread.major_diameter / 2 - 0.02 * MM)  # small fudge required
    extrude(amount=-DIAMETER * 0.06, mode=Mode.SUBTRACT)
    with Locations((0, 0, nuke_body_limits[1] - DIAMETER * 0.06)):
        add(nose_thread)

    # Create sockets for the fins
    offset(fin_tabs, amount=0.2 * MM, mode=Mode.SUBTRACT)

    # Top screws
    top_face = nuke_core_faces[-11]
    top_face_screw_ref_pnt = top_face.position_at(0.0, 0.5)
    top_face_screw_ref_nrm = top_face.normal_at(0.0, 0.5)
    top_face_screw_locs = [
        Rot(0, 0, a + 22.5)
        * Location(Plane(top_face_screw_ref_pnt, z_dir=top_face_screw_ref_nrm))
        for a in range(0, 360, 45)
    ]
    with Locations(top_face_screw_locs):
        ClearanceHole(top_screw, depth=1 * CM, fit="Close")

    # Middle screws
    middle_face = nuke_core_faces[-21]
    middle_face_screw_ref_pnt = middle_face.position_at(0.0, 0.5)
    middle_face_screw_ref_nrm = middle_face.normal_at(0.0, 0.5)
    middle_face_screw_locs = [
        Rot(0, 0, a)
        * Location(Plane(middle_face_screw_ref_pnt, z_dir=middle_face_screw_ref_nrm))
        for a in range(0, 360, 60)
    ]
    with Locations(middle_face_screw_locs):
        ClearanceHole(middle_screw, depth=1 * CM, fit="Close")

    # Remove the warning ring as it's a separate piece
    add(warning_ring, mode=Mode.SUBTRACT)

    # Add whistles
    whistle_ring_face = nuke_core_faces[-26]
    whistle_uv = (0.0625, 0.5)
    normal = whistle_ring_face.normal_at(*whistle_uv)
    origin = whistle_ring_face.position_at(*whistle_uv)
    pln = Plane(
        origin=origin + Vector(normal.X, normal.Y, -0.5) * DIAMETER * 0.02,
        z_dir=normal + Vector(0, 0, 0.6),
    )
    with BuildSketch(pln):
        RectangleRounded(DIAMETER * 0.08, DIAMETER * 0.08, DIAMETER * 0.01)
        Rectangle(DIAMETER * 0.06, DIAMETER * 0.06, mode=Mode.SUBTRACT)
    whistle = extrude(until=Until.PREVIOUS, dir=normal + Vector(0, 0, 1))
    whistle_flipped = mirror(whistle, about=Plane.XZ)
    mirror(whistle, about=Plane.YZ.rotated((0, 0, 22.5)))
    mirror(whistle_flipped, about=Plane.YZ.rotated((0, 0, -22.5)))

nuke.part.color = Color("OliveDrab")
nuke.part.label = "nuke"

#
# -------- Final Assembly --------
#
components = (
    [nuke.part, warning_ring, fins.part, nose.part]
    + [copy.copy(nose_screw_head).locate(l) for l in nose_screw_locs]
    + [copy.copy(top_screw_head).locate(l) for l in top_face_screw_locs]
    + [copy.copy(middle_screw_head).locate(l) for l in middle_face_screw_locs]
    + [copy.copy(fin_screw).locate(l) for l in fin_screw_locs]
)
if MULTIPART_FINS:
    components.append(red_fins)

nuke_assembly = Compound(children=components)

show(nuke_assembly, center_grid=True, names=["nuke_assembly"])
