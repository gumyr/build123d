"""

name: general_examples.py
by:   jdegenstein
date: December 29th 2022

desc:

    This is the build123d general examples python script. It generates the SVGs
    when run as a script, and is pulled into sphinx docs by
    tutorial_general.rst.

license:

    Copyright 2022 jdegenstein

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
from build123d import *

svg_opts = {
    "width": 500,
    "height": 300,
    "pixel_scale": 4,
    "margin_left": 10,
    "margin_top": 10,
    "show_axes": False,
    "show_hidden": True,
}


def svgout(ex_counter):
    exec(
        f"""
ex{ex_counter}.part.export_svg(
    f"assets/general_ex{ex_counter}.svg",
    (-100, -100, 70),
    (0, 0, 1),
    svg_opts=svg_opts,
)
"""
    )


ex_counter = 1
##########################################
# Simple Rectangular Plate
# [Ex. 1]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex1:
    Box(length, width, thickness)
# [Ex. 1]

svgout(ex_counter)

ex_counter += 1

# show_object(ex1.part)


##########################################
# Plane with Hole
# [Ex. 2]
length, width, thickness = 80.0, 60.0, 10.0
center_hole_dia = 22.0

with BuildPart() as ex2:
    Box(length, width, thickness)
    Cylinder(radius=center_hole_dia / 2, height=thickness, mode=Mode.SUBTRACT)
# [Ex. 2]

svgout(ex_counter)

ex_counter += 1
# show_object(ex2.part)

##########################################
# 3. An extruded prismatic solid
# [Ex. 3]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex3:
    with BuildSketch() as ex3_sk:
        Circle(width)
        Rectangle(length / 2, width / 2, mode=Mode.SUBTRACT)
    Extrude(amount=2 * thickness)
# [Ex. 3]

svgout(ex_counter)

ex_counter += 1
# show_object(ex3.part)

##########################################
# Building Profiles using lines and arcs
# [Ex. 4]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex4:
    with BuildSketch() as ex4_sk:
        with BuildLine() as ex4_ln:
            l1 = Line((0, 0), (length, 0))
            l2 = Line((length, 0), (length, width))
            l3 = ThreePointArc((length, width), (width, width * 1.5), (0.0, width))
            l4 = Line((0.0, width), (0, 0))
        MakeFace()
    Extrude(amount=thickness)
# [Ex. 4]

svgout(ex_counter)

ex_counter += 1
# show_object(ex4.part)

##########################################
# Moving The Current working point
# [Ex. 5]
a, b, c, d = 90, 45, 15, 7.5

with BuildPart() as ex5:
    with BuildSketch() as ex5_sk:
        Circle(a)
        with Locations((b, 0.0)):
            Rectangle(c, c, mode=Mode.SUBTRACT)
        with Locations((0, b)):
            Circle(d, mode=Mode.SUBTRACT)
    Extrude(amount=c)
# [Ex. 5]

svgout(ex_counter)

ex_counter += 1

# show_object(ex5.part)

##########################################
# Using Point Lists
# [Ex. 6]
a, b, c = 80, 60, 10

with BuildPart() as ex6:
    with BuildSketch() as ex6_sk:
        Circle(a)
        with Locations((b, 0), (0, b), (-b, 0), (0, -b)):
            Circle(c, mode=Mode.SUBTRACT)
    Extrude(amount=c)
# [Ex. 6]

svgout(ex_counter)

ex_counter += 1

# show_object(ex6.part)
##########################################
# Polygons
# [Ex. 7]
a, b, c = 60, 80, 5

with BuildPart() as ex7:
    with BuildSketch() as ex7_sk:
        Rectangle(a, b, c)
        with Locations((0, 3 * c), (0, -3 * c)):
            RegularPolygon(radius=2 * c, side_count=6, mode=Mode.SUBTRACT)
    Extrude(amount=c)
# [Ex. 7]

svgout(ex_counter)

ex_counter += 1

# show_object(ex7.part)

##########################################
# 8. Polylines
# [Ex. 8]
(L, H, W, t) = (100.0, 20.0, 20.0, 1.0)
pts = [
    (0, H / 2.0),
    (W / 2.0, H / 2.0),
    (W / 2.0, (H / 2.0 - t)),
    (t / 2.0, (H / 2.0 - t)),
    (t / 2.0, (t - H / 2.0)),
    (W / 2.0, (t - H / 2.0)),
    (W / 2.0, H / -2.0),
    (0, H / -2.0),
]

with BuildPart() as ex8:
    with BuildSketch() as ex8_sk:
        with BuildLine() as ex8_ln:
            Polyline(*pts)
            Mirror(ex8_ln.line, about=Plane.YZ)
        MakeFace()
    Extrude(amount=L / 2)
# [Ex. 8]

svgout(ex_counter)

ex_counter += 1

# show_object(ex8.part)

##########################################
# 9. Selectors, Fillets, and Chamfers
# [Ex. 9]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex9:
    Box(length, width, thickness)
    Chamfer(*ex9.edges().group_by(Axis.Z)[-1], length=4)
    Fillet(*ex9.edges().filter_by(Axis.Z), radius=5)
# [Ex. 9]

svgout(ex_counter)

ex_counter += 1

# show_object(ex9.part)

##########################################
# 10. Select Last and Hole
# [Ex. 10]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex10:
    Box(length, width, thickness)
    Chamfer(*ex10.edges().group_by(Axis.Z)[-1], length=4)
    Fillet(*ex10.edges().filter_by(Axis.Z), radius=5)
    Hole(radius=width / 4)
    Fillet(ex10.edges(Select.LAST).sort_by(Axis.Z)[-1], radius=2)
# [Ex. 10]

svgout(ex_counter)

ex_counter += 1

# show_object(ex10.part)

##########################################
# 11. Use a face as workplane for BuildSketch and introduce GridLocations
# [Ex. 11]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex11:
    Box(length, width, thickness)
    Chamfer(*ex11.edges().group_by(Axis.Z)[-1], length=4)
    Fillet(*ex11.edges().filter_by(Axis.Z), radius=5)
    Hole(radius=width / 4)
    Fillet(ex11.edges(Select.LAST).sort_by(Axis.Z)[-1], radius=2)
    with BuildSketch(ex11.faces().sort_by(Axis.Z)[-1]) as ex11_sk:
        with GridLocations(length / 2, width / 2, 2, 2):
            RegularPolygon(radius=5, side_count=5)
    Extrude(amount=-thickness, mode=Mode.SUBTRACT)
# [Ex. 11]

svgout(ex_counter)

ex_counter += 1

# show_object(ex11)

##########################################
# 12. Defining an Edge with a Spline
# [Ex. 12]
sPnts = [
    (55, 30),
    (50, 35),
    (40, 30),
    (30, 20),
    (20, 25),
    (10, 20),
    (0, 20),
]

with BuildPart() as ex12:
    with BuildSketch() as ex12_sk:
        with BuildLine() as ex12_ln:
            l1 = Spline(*sPnts)
            l2 = Line(l1 @ 0, (60, 0))
            l3 = Line(l2 @ 1, (0, 0))
            l4 = Line(l3 @ 1, l1 @ 1)
        MakeFace()
    Extrude(amount=10)
# [Ex. 12]

svgout(ex_counter)

ex_counter += 1

# show_object(ex12.part)


##########################################
# 13. CounterBoreHoles, CounterSinkHoles and PolarLocations
# [Ex. 13]
a, b = 40, 4
with BuildPart() as ex13:
    Cylinder(radius=50, height=10)
    with Workplanes(ex13.faces().sort_by(Axis.Z)[-1]):
        with PolarLocations(radius=a, count=4):
            CounterSinkHole(radius=b, counter_sink_radius=2 * b)
        with PolarLocations(radius=a, count=4, start_angle=45, stop_angle=360 + 45):
            CounterBoreHole(radius=b, counter_bore_radius=2 * b, counter_bore_depth=b)
# [Ex. 13]

svgout(ex_counter)

ex_counter += 1

# show_object(ex13.part)

##########################################
# 14. Position on a line with '@', '%' and introduce Sweep
# [Ex. 14]
a, b = 40, 20

with BuildPart() as ex14:
    with BuildLine() as ex14_ln:
        l1 = JernArc(start=(0, 0), tangent=(0, 1), radius=a, arc_size=180)
        l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=a, arc_size=-90)
        l3 = Line(l2 @ 1, l2 @ 1 + Vector(-a, a))
    with BuildSketch(Plane.XZ) as ex14_sk:
        Rectangle(b, b)
    Sweep(path=ex14_ln.wires()[0])
# [Ex. 14]

svgout(ex_counter)

ex_counter += 1

# show_object(ex14.part)


##########################################
# 15. Mirroring Symmetric Geometry
# [Ex. 15]
a, b, c = 80, 40, 20

with BuildPart() as ex15:
    with BuildSketch() as ex15_sk:
        with BuildLine() as ex15_ln:
            l1 = Line((0, 0), (a, 0))
            l2 = Line(l1 @ 1, l1 @ 1 + Vector(0, b))
            l3 = Line(l2 @ 1, l2 @ 1 + Vector(-c, 0))
            l4 = Line(l3 @ 1, l3 @ 1 + Vector(0, -c))
            l5 = Line(l4 @ 1, Vector(0, (l4 @ 1).Y))
            Mirror(ex15_ln.line, about=Plane.YZ)
        MakeFace()
    Extrude(amount=c)
# [Ex. 15]

svgout(ex_counter)

ex_counter += 1

# show_object(ex15.part)

##########################################
# 16. Mirroring 3D Objects
# same concept as CQ docs, but different object
# [Ex. 16]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex16_single:
    with BuildSketch(Plane.XZ) as ex16_sk:
        Rectangle(length, width)
        Fillet(*ex16_sk.vertices(), radius=length / 10)
        with GridLocations(x_spacing=length / 4, y_spacing=0, x_count=3, y_count=1):
            Circle(length / 12, mode=Mode.SUBTRACT)
        Rectangle(length, width, centered=(False, False), mode=Mode.SUBTRACT)
    Extrude(amount=length)

with BuildPart() as ex16:
    Add(ex16_single.part)
    Mirror(ex16_single.part, about=Plane.XY.offset(width))
    Mirror(ex16_single.part, about=Plane.YX.offset(width))
    Mirror(ex16_single.part, about=Plane.YZ.offset(width))
    Mirror(ex16_single.part, about=Plane.YZ.offset(-width))
# [Ex. 16]

svgout(ex_counter)

ex_counter += 1

# show_object(ex16_mirrors.part)

##########################################
# 17. Mirroring From Faces
# [Ex. 17]
a, b = 30, 20

with BuildPart() as ex17:
    with BuildSketch() as ex17_sk:
        RegularPolygon(radius=a, side_count=5)
    Extrude(amount=b)
    Mirror(ex17.part, about=Plane((ex17.faces().group_by(Axis.Y)[0])[0]))
# [Ex. 17]

svgout(ex_counter)

ex_counter += 1

# show_object(ex17.part)

##########################################
# 18. Creating Workplanes on Faces
# based on Ex. 9
# [Ex. 18]
length, width, thickness = 80.0, 60.0, 10.0
a, b = 4, 5

with BuildPart() as ex18:
    Box(length, width, thickness)
    Chamfer(*ex18.edges().group_by(Axis.Z)[-1], length=a)
    Fillet(*ex18.edges().filter_by(Axis.Z), radius=b)
    with BuildSketch(ex18.faces().sort_by(Axis.Z)[-1]):
        Rectangle(2 * b, 2 * b)
    Extrude(amount=-thickness, mode=Mode.SUBTRACT)
# [Ex. 18]

svgout(ex_counter)

ex_counter += 1

# show_object(ex18.part)

##########################################
# 19. Locating a Workplane on a vertex
# [Ex. 19]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex19:
    Box(length, width, thickness)
    topf = ex19.faces().sort_by(Axis.Z)[-1]
    with Workplanes(topf):
        vtx = topf.vertices().sort_by(Axis.X and Axis.Y)[1]
        with Locations((vtx.X, vtx.Y)):
            with BuildSketch() as ex19_sk:
                Circle(radius=width / 4)
    Extrude(amount=-thickness, mode=Mode.SUBTRACT)
# [Ex. 19]

svgout(ex_counter)

ex_counter += 1

# show_object(ex19.part)

##########################################
# 20. Offset Sketch Workplane
# [Ex. 20]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex20:
    Box(length, width, thickness)
    pln = Plane((ex20.faces().group_by(Axis.X))[0][0])
    with BuildSketch(pln.offset(thickness)):
        Circle(width / 2)
    Extrude(amount=thickness)
# [Ex. 20]

svgout(ex_counter)

ex_counter += 1

# show_object(ex20.part)

##########################################
# 21. Copying Workplanes
# [Ex. 21]
width, length = 10.0, 60.0

with BuildPart() as ex21:
    with BuildSketch() as ex21_sk:
        Circle(width / 2)
    Extrude(amount=length)
    with BuildSketch(Plane(origin=ex21.part.center(), z_dir=(-1, 0, 0))):
        Circle(width / 2)
    Extrude(amount=length)
# [Ex. 21]

svgout(ex_counter)

ex_counter += 1

# show_object(ex21.part)

##########################################
# 22. Rotated Workplanes
# [Ex. 22]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex22:
    Box(length, width, thickness)
    pln = Plane((ex22.faces().group_by(Axis.Z)[0])[0]).rotated((0, 50, 0))
    with BuildSketch(pln) as ex22_sk:
        with GridLocations(length / 4, width / 4, 2, 2):
            Circle(thickness / 4)
    Extrude(amount=-100, both=True, mode=Mode.SUBTRACT)
# [Ex. 22]

svgout(ex_counter)

ex_counter += 1

# show_object(ex22.part)

##########################################
# 23. Revolve
# [Ex. 23]
pts = [
    (-25, 35),
    (-25, 0),
    (-20, 0),
    (-20, 5),
    (-15, 10),
    (-15, 35),
]

with BuildPart() as ex23:
    with BuildSketch(Plane.XZ) as ex23_sk:
        with BuildLine() as ex23_ln:
            l1 = Polyline(*pts)
            l2 = Line(l1 @ 1, l1 @ 0)
        MakeFace()
        with Locations((0, 35)):
            Circle(25)
        Split(bisect_by=Plane.ZY)
    Revolve(axis=Axis.Z)
# [Ex. 23]

svgout(ex_counter)

ex_counter += 1

# show_object(ex23.part)

##########################################
# 24. Lofts
# [Ex. 24]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex24:
    Box(length, length, thickness)
    with BuildSketch((ex24.faces().group_by(Axis.Z)[0])[0]) as ex24_sk:
        Circle(length / 3)
    with BuildSketch(ex24_sk.faces()[0].offset(length / 2)) as ex24_sk2:
        Rectangle(length / 6, width / 6)
    Loft()
# [Ex. 24]

svgout(ex_counter)

ex_counter += 1

# show_object(ex24.part)

##########################################
# 25. Offset Sketch
# [Ex. 25]
rad, offs = 50, 10

with BuildPart() as ex25:
    with BuildSketch() as ex25_sk1:
        RegularPolygon(radius=rad, side_count=5)
    with BuildSketch(Plane.XY.offset(15)) as ex25_sk2:
        RegularPolygon(radius=rad, side_count=5)
        Offset(amount=offs)
    with BuildSketch(Plane.XY.offset(30)) as ex25_sk3:
        RegularPolygon(radius=rad, side_count=5)
        Offset(amount=offs, kind=Kind.INTERSECTION)
    Extrude(amount=1)
# [Ex. 25]

svgout(ex_counter)

ex_counter += 1

# show_object(ex25.part)

##########################################
# 26. Offset Part To Create Thin features
# [Ex. 26]
length, width, thickness, wall = 80.0, 60.0, 10.0, 2.0

with BuildPart() as ex26:
    Box(length, width, thickness)
    topf = ex26.faces().sort_by(Axis.Z)[-1]
    Offset(amount=-wall, openings=topf)

# [Ex. 26]

svgout(ex_counter)

ex_counter += 1

# show_object(ex26.part)

##########################################
# 27. Splitting an Object
# [Ex. 27]
length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex27:
    Box(length, width, thickness)
    with BuildSketch(ex27.faces().sort_by(Axis.Z)[0]) as ex27_sk:
        Circle(width / 4)
    Extrude(amount=-thickness, mode=Mode.SUBTRACT)
    Split(bisect_by=Plane(ex27.faces().sort_by(Axis.Y)[-1]).offset(-width / 2))
# [Ex. 27]

svgout(ex_counter)

ex_counter += 1

# show_object(ex27.part)

##########################################
# 28. Locating features based on Faces
# [Ex. 28]
width, thickness = 80.0, 10.0

with BuildPart() as ex28:
    with BuildSketch() as ex28_sk:
        RegularPolygon(radius=width / 4, side_count=3)
    ex28_ex = Extrude(amount=thickness, mode=Mode.PRIVATE)
    midfaces = ex28_ex.faces().group_by(Axis.Z)[1]
    Sphere(radius=width / 2)
    with Workplanes(*midfaces):
        Hole(thickness / 2)
# [Ex. 28]

svgout(ex_counter)

ex_counter += 1

# show_object(ex28.part)

##########################################
# 29. The Classic OCC Bottle
# [Ex. 29]
L, w, t, b, h, n = 60.0, 18.0, 9.0, 0.9, 90.0, 6.0

with BuildPart() as ex29:
    with BuildSketch(Plane.XY.offset(-b)) as ex29_ow_sk:
        with BuildLine() as ex29_ow_ln:
            l1 = Line((0, 0), (0, w / 2))
            l2 = ThreePointArc(l1 @ 1, (L / 2.0, w / 2.0 + t), (L, w / 2.0))
            l3 = Line(l2 @ 1, Vector((l2 @ 1).X, 0, 0))
            Mirror(ex29_ow_ln.line)
        MakeFace()
    Extrude(amount=h + b)
    with BuildSketch(ex29.faces().sort_by(Axis.Z)[-1]):
        Circle(t)
    Extrude(amount=n)
    necktopf = ex29.faces().sort_by(Axis.Z)[-1]
    Offset(ex29.solids()[0], amount=-b, openings=necktopf)
# [Ex. 29]

svgout(ex_counter)

ex_counter += 1

# show_object(ex29.part)

##########################################
# 30. Splitting an Object
# [Ex. 30]

# [Ex. 30]

# svgout(ex_counter)

# ex_counter += 1

# show_object(ex30.part)
