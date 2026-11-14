"""
An embossed chalice tutorial

name: projection_chalice.py
by:   Gumyr
date: November 14th 2026

desc:
    Every code example in the "An embossed chalice" projection tutorial lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. Each step is written twice, in builder and in algebra
    mode, and shows the whole part as it stands at that point; the two are
    checked against each other. The rendered pictures on the page are made
    from this script by ``projection_chalice_shots.py``.

license:

    Copyright 2026 Gumyr

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

from build123d.topology import Shape

# [setup]
from build123d import *

wall = 2  # thickness of the rim
scallops = 10  # how many scallops go round the bowl
inset = 3  # how far the band sits inside the outline of the chalice
band_width = 2
relief = 1  # how far the band stands out from the bowl
# [setup]


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a step make the same shape?"""
    box_1, box_2 = first.bounding_box(), second.bounding_box()
    return (
        abs(first.volume - second.volume) < 1e-6
        and abs(first.area - second.area) < 1e-6
        and (box_1.min - box_2.min).length < 1e-6
        and (box_1.max - box_2.max).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


# ---------------------------------------------------------------------------
# Step 2: the profile
# ---------------------------------------------------------------------------

# [profile_builder]
with BuildPart() as chalice:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            outside = Spline(
                (30, -40),
                (15, -30),
                (15, 20),
                (40, 40),
                (50, 60),
                (50, 80),
                tangents=((0, 1), (-0.3, 1)),
                tangent_scalars=(0.5, 1),
            )
            rim = Line(outside @ 1, outside @ 1 - (wall, 0))
            inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
            axis = Line(inside @ 1, (0, -40))
            Line(axis @ 1, outside @ 0)
        make_face()
# [profile_builder]
builder_result = profile.sketch

# [profile_algebra]
outside = Spline(
    (30, -40),
    (15, -30),
    (15, 20),
    (40, 40),
    (50, 60),
    (50, 80),
    tangents=((0, 1), (-0.3, 1)),
    tangent_scalars=(0.5, 1),
)
rim = Line(outside @ 1, outside @ 1 - (wall, 0))
inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
axis = Line(inside @ 1, (0, -40))
foot = Line(axis @ 1, outside @ 0)
profile = Plane.XZ * make_face([outside, rim, inside, axis, foot])
# [profile_algebra]

assert same(builder_result, profile)
assert profile.is_valid and abs(profile.area - 1285.3) < 0.1
assert abs((inside @ 1).X) < 1e-6

# ---------------------------------------------------------------------------
# Step 3: the cup
# ---------------------------------------------------------------------------

# [cup_builder]
with BuildPart() as chalice:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            outside = Spline(
                (30, -40),
                (15, -30),
                (15, 20),
                (40, 40),
                (50, 60),
                (50, 80),
                tangents=((0, 1), (-0.3, 1)),
                tangent_scalars=(0.5, 1),
            )
            rim = Line(outside @ 1, outside @ 1 - (wall, 0))
            inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
            axis = Line(inside @ 1, (0, -40))
            Line(axis @ 1, outside @ 0)
        make_face()
    revolve(axis=Axis.Z)
# [cup_builder]
builder_result = chalice.part

# [cup_algebra]
outside = Spline(
    (30, -40),
    (15, -30),
    (15, 20),
    (40, 40),
    (50, 60),
    (50, 80),
    tangents=((0, 1), (-0.3, 1)),
    tangent_scalars=(0.5, 1),
)
rim = Line(outside @ 1, outside @ 1 - (wall, 0))
inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
axis = Line(inside @ 1, (0, -40))
foot = Line(axis @ 1, outside @ 0)
profile = Plane.XZ * make_face([outside, rim, inside, axis, foot])
chalice = revolve(profile, axis=Axis.Z)
# [cup_algebra]

assert same(builder_result, chalice)
assert chalice.is_valid and len(chalice.solids()) == 1
assert abs(chalice.bounding_box().min.Z + 40) < 1e-3
assert abs(chalice.bounding_box().max.Z - 80) < 1e-3
cup = chalice  # the chalice before it is decorated, for the pictures

# ---------------------------------------------------------------------------
# Step 4: the footprint
# ---------------------------------------------------------------------------

# [footprint_builder]
with BuildPart() as chalice:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            outside = Spline(
                (30, -40),
                (15, -30),
                (15, 20),
                (40, 40),
                (50, 60),
                (50, 80),
                tangents=((0, 1), (-0.3, 1)),
                tangent_scalars=(0.5, 1),
            )
            rim = Line(outside @ 1, outside @ 1 - (wall, 0))
            inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
            axis = Line(inside @ 1, (0, -40))
            Line(axis @ 1, outside @ 0)
        make_face()
    revolve(axis=Axis.Z)

    with BuildSketch() as band:
        footprint = project_to_plane()
# [footprint_builder]
builder_result = band.sketch  # the footprint is the whole of the sketch so far

# [footprint_algebra]
outside = Spline(
    (30, -40),
    (15, -30),
    (15, 20),
    (40, 40),
    (50, 60),
    (50, 80),
    tangents=((0, 1), (-0.3, 1)),
    tangent_scalars=(0.5, 1),
)
rim = Line(outside @ 1, outside @ 1 - (wall, 0))
inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
axis = Line(inside @ 1, (0, -40))
foot = Line(axis @ 1, outside @ 0)
profile = Plane.XZ * make_face([outside, rim, inside, axis, foot])
chalice = revolve(profile, axis=Axis.Z)

footprint = project_to_plane(chalice, Plane.XY)
# [footprint_algebra]

assert same(builder_result, footprint)
assert len(footprint.edges()) == 1
assert footprint.edge().geom_type == GeomType.CIRCLE
assert abs(footprint.edge().radius - 51.3127) < 1e-3
assert abs(footprint.face().center().Z) < 1e-6  # flat on Plane.XY

# ---------------------------------------------------------------------------
# Step 5: the band
# ---------------------------------------------------------------------------

# [band_builder]
with BuildPart() as chalice:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            outside = Spline(
                (30, -40),
                (15, -30),
                (15, 20),
                (40, 40),
                (50, 60),
                (50, 80),
                tangents=((0, 1), (-0.3, 1)),
                tangent_scalars=(0.5, 1),
            )
            rim = Line(outside @ 1, outside @ 1 - (wall, 0))
            inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
            axis = Line(inside @ 1, (0, -40))
            Line(axis @ 1, outside @ 0)
        make_face()
    revolve(axis=Axis.Z)

    with BuildSketch() as band:
        footprint = project_to_plane()
        guide = offset(amount=-inset).wire()
        start, end = guide.positions([0, 1 / scallops])
        with BuildLine():
            with PolarLocations(0, scallops):
                RadiusArc(start, end, (end - start).length * 1.2)
        make_face(mode=Mode.REPLACE)
        inner = band.sketch
        offset(amount=band_width, kind=Kind.INTERSECTION)
        insert(inner, mode=Mode.SUBTRACT)
# [band_builder]
builder_result = band.sketch

# [band_algebra]
outside = Spline(
    (30, -40),
    (15, -30),
    (15, 20),
    (40, 40),
    (50, 60),
    (50, 80),
    tangents=((0, 1), (-0.3, 1)),
    tangent_scalars=(0.5, 1),
)
rim = Line(outside @ 1, outside @ 1 - (wall, 0))
inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
axis = Line(inside @ 1, (0, -40))
foot = Line(axis @ 1, outside @ 0)
profile = Plane.XZ * make_face([outside, rim, inside, axis, foot])
chalice = revolve(profile, axis=Axis.Z)

footprint = project_to_plane(chalice, Plane.XY)
guide = offset(footprint, amount=-inset).wire()
start, end = guide.positions([0, 1 / scallops])
scallop = RadiusArc(start, end, (end - start).length * 1.2)
inner = make_face(PolarLocations(0, scallops) * scallop)
band = offset(inner, amount=band_width, kind=Kind.INTERSECTION) - inner
# [band_algebra]

assert same(builder_result, band)
assert len(band.faces()) == 1 and len(band.face().inner_wires()) == 1
assert abs(band.area - 636.2) < 0.1
# the band stays inside the footprint, or part of it would miss the cup
assert max(Vector(v).length for v in band.vertices()) < footprint.edge().radius

# ---------------------------------------------------------------------------
# Step 6: onto the cup
# ---------------------------------------------------------------------------

# [project_builder]
with BuildPart() as chalice:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            outside = Spline(
                (30, -40),
                (15, -30),
                (15, 20),
                (40, 40),
                (50, 60),
                (50, 80),
                tangents=((0, 1), (-0.3, 1)),
                tangent_scalars=(0.5, 1),
            )
            rim = Line(outside @ 1, outside @ 1 - (wall, 0))
            inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
            axis = Line(inside @ 1, (0, -40))
            Line(axis @ 1, outside @ 0)
        make_face()
    revolve(axis=Axis.Z)

    with BuildSketch() as band:
        footprint = project_to_plane()
        guide = offset(amount=-inset).wire()
        start, end = guide.positions([0, 1 / scallops])
        with BuildLine():
            with PolarLocations(0, scallops):
                RadiusArc(start, end, (end - start).length * 1.2)
        make_face(mode=Mode.REPLACE)
        inner = band.sketch
        offset(amount=band_width, kind=Kind.INTERSECTION)
        insert(inner, mode=Mode.SUBTRACT)
    project_to_shape(direction=(0, 0, 1), hit=Hit.NEAREST)
# [project_builder]
builder_result = Sketch(chalice.pending_faces)
assert same(chalice.part, cup)  # the part itself is unchanged

# [project_algebra]
outside = Spline(
    (30, -40),
    (15, -30),
    (15, 20),
    (40, 40),
    (50, 60),
    (50, 80),
    tangents=((0, 1), (-0.3, 1)),
    tangent_scalars=(0.5, 1),
)
rim = Line(outside @ 1, outside @ 1 - (wall, 0))
inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
axis = Line(inside @ 1, (0, -40))
foot = Line(axis @ 1, outside @ 0)
profile = Plane.XZ * make_face([outside, rim, inside, axis, foot])
chalice = revolve(profile, axis=Axis.Z)

footprint = project_to_plane(chalice, Plane.XY)
guide = offset(footprint, amount=-inset).wire()
start, end = guide.positions([0, 1 / scallops])
scallop = RadiusArc(start, end, (end - start).length * 1.2)
inner = make_face(PolarLocations(0, scallops) * scallop)
band = offset(inner, amount=band_width, kind=Kind.INTERSECTION) - inner

on_cup = project_to_shape(band, chalice, direction=(0, 0, 1), hit=Hit.NEAREST)
# [project_algebra]

assert same(builder_result, on_cup)
assert len(on_cup.faces()) == 1
assert on_cup.face().geom_type != GeomType.PLANE
assert abs(on_cup.area - 1474.9) < 0.5
# without hit, every surface in the band's path comes back, nearest first
everything = project_to_shape(band, chalice, direction=(0, 0, 1))
assert len(everything.faces()) == 32
assert abs(everything.faces()[0].area - on_cup.area) < 1e-6

# ---------------------------------------------------------------------------
# Step 7: the relief
# ---------------------------------------------------------------------------

# [relief_builder]
with BuildPart() as chalice:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            outside = Spline(
                (30, -40),
                (15, -30),
                (15, 20),
                (40, 40),
                (50, 60),
                (50, 80),
                tangents=((0, 1), (-0.3, 1)),
                tangent_scalars=(0.5, 1),
            )
            rim = Line(outside @ 1, outside @ 1 - (wall, 0))
            inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
            axis = Line(inside @ 1, (0, -40))
            Line(axis @ 1, outside @ 0)
        make_face()
    revolve(axis=Axis.Z)

    with BuildSketch() as band:
        footprint = project_to_plane()
        guide = offset(amount=-inset).wire()
        start, end = guide.positions([0, 1 / scallops])
        with BuildLine():
            with PolarLocations(0, scallops):
                RadiusArc(start, end, (end - start).length * 1.2)
        make_face(mode=Mode.REPLACE)
        inner = band.sketch
        offset(amount=band_width, kind=Kind.INTERSECTION)
        insert(inner, mode=Mode.SUBTRACT)
    project_to_shape(direction=(0, 0, 1), hit=Hit.NEAREST)
    thicken(amount=relief)
# [relief_builder]
builder_result = chalice.part

# [relief_algebra]
outside = Spline(
    (30, -40),
    (15, -30),
    (15, 20),
    (40, 40),
    (50, 60),
    (50, 80),
    tangents=((0, 1), (-0.3, 1)),
    tangent_scalars=(0.5, 1),
)
rim = Line(outside @ 1, outside @ 1 - (wall, 0))
inside = JernArc(rim @ 1, (0, -1), (rim @ 1).X, -90)
axis = Line(inside @ 1, (0, -40))
foot = Line(axis @ 1, outside @ 0)
profile = Plane.XZ * make_face([outside, rim, inside, axis, foot])
chalice = revolve(profile, axis=Axis.Z)

footprint = project_to_plane(chalice, Plane.XY)
guide = offset(footprint, amount=-inset).wire()
start, end = guide.positions([0, 1 / scallops])
scallop = RadiusArc(start, end, (end - start).length * 1.2)
inner = make_face(PolarLocations(0, scallops) * scallop)
band = offset(inner, amount=band_width, kind=Kind.INTERSECTION) - inner

on_cup = project_to_shape(band, chalice, direction=(0, 0, 1), hit=Hit.NEAREST)
chalice += thicken(on_cup, amount=relief)
# [relief_algebra]

assert same(builder_result, chalice)
assert chalice.is_valid and len(chalice.solids()) == 1
assert abs((chalice.volume - cup.volume) - 1461.2) < 0.5
