"""
Part Objects

name: objects_part.py
by:   Gumyr
date: March 22nd 2023

desc:
    This python module contains objects (classes) that create 3D Parts.

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

from __future__ import annotations

from math import radians, tan

from build123d.build_common import LocationList, validate_inputs
from build123d.build_enums import Align, Mode
from build123d.build_part import BuildPart
from build123d.geometry import Location, Plane, Rotation, RotationLike
from build123d.topology import Compound, Part, ShapeList, Solid, tuplify


class BasePartObject(Part):
    """BasePartObject

    Base class for all BuildPart objects & operations

    Args:
        solid (Solid): object to create
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        part: Part | Solid,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if align is not None:
            align = tuplify(align, 3)
            bbox = part.bounding_box()
            offset = bbox.to_align_offset(align)
            part.move(Location(offset))

        context: BuildPart | None = BuildPart._get_context(self, log=False)
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        self.rotation = rotate
        if context is None:
            new_solids = [part.moved(rotate)]
        else:
            self.mode = mode

            if not LocationList._get_context():
                raise RuntimeError("No valid context found")
            new_solids = [
                part.moved(location * rotate)
                for location in LocationList._get_context().locations
            ]
            if isinstance(context, BuildPart):
                context._add_to_context(*new_solids, mode=mode)

        if len(new_solids) > 1:
            new_part = Compound(new_solids).wrapped
        elif isinstance(new_solids[0], Compound):  # Don't add extra layers
            new_part = new_solids[0].wrapped
        else:
            new_part = Compound(new_solids).wrapped

        super().__init__(
            obj=new_part,
            # obj=Compound(new_solids).wrapped,
            label=part.label,
            material=part.material,
            joints=part.joints,
            parent=part.parent,
            children=part.children,
        )


class Box(BasePartObject):
    """Part Object: Box

    Create a box defined by length, width, and height.

    Args:
        length (float): box length
        width (float): box width
        height (float): box height
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to (Align.CENTER, Align.CENTER, Align.CENTER)
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.length = length
        self.width = width
        self.box_height = height

        solid = Solid.make_box(length, width, height)

        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )


class Cone(BasePartObject):
    """Part Object: Cone

    Create a cone defined by bottom radius, top radius, and height.

    Args:
        bottom_radius (float): bottom radius
        top_radius (float): top radius, may be zero
        height (float): cone height
        arc_size (float, optional): angular size of cone. Defaults to 360
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to (Align.CENTER, Align.CENTER, Align.CENTER)
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        bottom_radius: float,
        top_radius: float,
        height: float,
        arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.bottom_radius = bottom_radius
        self.top_radius = top_radius
        self.cone_height = height
        self.arc_size = arc_size
        self.align = align

        solid = Solid.make_cone(
            bottom_radius,
            top_radius,
            height,
            angle=arc_size,
        )

        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )


class CounterBoreHole(BasePartObject):
    """Part Operation: Counter Bore Hole

    Create a counter bore hole defined by radius, counter bore radius, counter bore and depth.

    Args:
        radius (float): hole radius
        counter_bore_radius (float): counter bore radius
        counter_bore_depth (float): counter bore depth
        depth (float, optional): hole depth, through part if None. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        radius: float,
        counter_bore_radius: float,
        counter_bore_depth: float,
        depth: float | None = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.radius = radius
        self.counter_bore_radius = counter_bore_radius
        self.counter_bore_depth = counter_bore_depth
        if depth is not None:
            self.hole_depth = depth
        elif depth is None and context is not None:
            self.hole_depth = context.max_dimension
        else:
            raise ValueError("No depth provided")
        self.mode = mode

        fused = Solid.make_cylinder(
            radius, self.hole_depth, Plane(origin=(0, 0, 0), z_dir=(0, 0, -1))
        ).fuse(
            Solid.make_cylinder(
                counter_bore_radius,
                counter_bore_depth + self.hole_depth,
                Plane((0, 0, -counter_bore_depth)),
            )
        )
        if isinstance(fused, ShapeList):
            solid = Part(fused)
        else:
            solid = fused
        super().__init__(part=solid, rotation=(0, 0, 0), mode=mode)


class CounterSinkHole(BasePartObject):
    """Part Operation: Counter Sink Hole

    Create a countersink hole defined by radius, countersink radius, countersink
    angle, and depth.

    Args:
        radius (float): hole radius
        counter_sink_radius (float): countersink radius
        depth (float, optional): hole depth, through part if None. Defaults to None
        counter_sink_angle (float, optional): cone angle. Defaults to 82
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        radius: float,
        counter_sink_radius: float,
        depth: float | None = None,
        counter_sink_angle: float = 82,  # Common tip angle
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.radius = radius
        self.counter_sink_radius = counter_sink_radius
        if depth is not None:
            self.hole_depth = depth
        elif depth is None and context is not None:
            self.hole_depth = context.max_dimension
        else:
            raise ValueError("No depth provided")
        self.counter_sink_angle = counter_sink_angle
        self.mode = mode
        cone_height = counter_sink_radius / tan(radians(counter_sink_angle / 2.0))

        fused = Solid.make_cylinder(
            radius, self.hole_depth, Plane(origin=(0, 0, 0), z_dir=(0, 0, -1))
        ).fuse(
            Solid.make_cone(
                counter_sink_radius,
                0.0,
                cone_height,
                Plane(origin=(0, 0, 0), z_dir=(0, 0, -1)),
            ),
            Solid.make_cylinder(counter_sink_radius, self.hole_depth),
        )
        if isinstance(fused, ShapeList):
            solid = Part(fused)
        else:
            solid = fused

        super().__init__(part=solid, rotation=(0, 0, 0), mode=mode)


class Cylinder(BasePartObject):
    """Part Object: Cylinder

    Create a cylinder defined by radius and height.

    Args:
        radius (float): cylinder radius
        height (float): cylinder height
        arc_size (float, optional): angular size of cone. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to (Align.CENTER, Align.CENTER, Align.CENTER)
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        radius: float,
        height: float,
        arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.radius = radius
        self.cylinder_height = height
        self.arc_size = arc_size
        self.align = align

        solid = Solid.make_cylinder(
            radius,
            height,
            angle=arc_size,
        )
        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )


class Hole(BasePartObject):
    """Part Operation: Hole

    Create a hole defined by radius and depth.

    Args:
        radius (float): hole radius
        depth (float, optional): hole depth, through part if None. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        radius: float,
        depth: float | None = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.radius = radius
        if depth is not None:
            self.hole_depth = 2 * depth
        elif depth is None and context is not None:
            self.hole_depth = 2 * context.max_dimension
        else:
            raise ValueError("No depth provided")
        self.mode = mode

        # To ensure the hole will go all the way through the part when
        # no depth is specified, calculate depth based on the part and
        # hole location. In this case start the hole above the part
        # and go all the way through.
        hole_start = (0, 0, self.hole_depth / 2) if depth is None else (0, 0, 0)
        solid = Solid.make_cylinder(
            radius, self.hole_depth, Plane(origin=hole_start, z_dir=(0, 0, -1))
        )
        super().__init__(
            part=solid,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            rotation=(0, 0, 0),
            mode=mode,
        )


class Sphere(BasePartObject):
    """Part Object: Sphere

    Create a sphere defined by a radius.

    Args:
        radius (float): sphere radius
        arc_size1 (float, optional): angular size of bottom hemisphere. Defaults to -90.
        arc_size2 (float, optional): angular size of top hemisphere. Defaults to 90.
        arc_size3 (float, optional): angular revolution about pole. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to (Align.CENTER, Align.CENTER, Align.CENTER)
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        radius: float,
        arc_size1: float = -90,
        arc_size2: float = 90,
        arc_size3: float = 360,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.radius = radius
        self.arc_size1 = arc_size1
        self.arc_size2 = arc_size2
        self.arc_size3 = arc_size3
        self.align = align

        solid = Solid.make_sphere(
            radius,
            angle1=arc_size1,
            angle2=arc_size2,
            angle3=arc_size3,
        )
        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )


class Torus(BasePartObject):
    """Part Object: Torus

    Create a torus defined by major and minor radii.

    Args:
        major_radius (float): major torus radius
        minor_radius (float): minor torus radius
        minor_start_angle (float, optional): angle to start minor arc. Defaults to 0
        minor_end_angle (float, optional): angle to end minor arc. Defaults to 360
        major_angle (float, optional): angle to revolve minor arc. Defaults to 360
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to (Align.CENTER, Align.CENTER, Align.CENTER)
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        major_radius: float,
        minor_radius: float,
        minor_start_angle: float = 0,
        minor_end_angle: float = 360,
        major_angle: float = 360,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        self.major_radius = major_radius
        self.minor_radius = minor_radius
        self.minor_start_angle = minor_start_angle
        self.minor_end_angle = minor_end_angle
        self.major_angle = major_angle
        self.align = align

        solid = Solid.make_torus(
            major_radius,
            minor_radius,
            start_angle=minor_start_angle,
            end_angle=minor_end_angle,
            major_angle=major_angle,
        )
        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )


class Wedge(BasePartObject):
    """Part Object: Wedge

    Create a wedge with a near face defined by xsize and z size, a far face defined by
    xmin to xmax and zmin to zmax, and a depth of ysize.

    Args:
        xsize (float): length of near face along x-axis
        ysize (float): length of part along y-axis
        zsize (float): length of near face z-axis
        xmin (float): minimum position far face along x-axis
        zmin (float): minimum position far face along z-axis
        xmax (float): maximum position far face along x-axis
        zmax (float): maximum position far face along z-axis
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to (Align.CENTER, Align.CENTER, Align.CENTER)
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        xsize: float,
        ysize: float,
        zsize: float,
        xmin: float,
        zmin: float,
        xmax: float,
        zmax: float,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ):
        context: BuildPart | None = BuildPart._get_context(self)
        validate_inputs(context, self)

        if any([value <= 0 for value in [xsize, ysize, zsize]]):
            raise ValueError("xsize, ysize & zsize must all be greater than zero")

        self.xsize = xsize
        self.ysize = ysize
        self.zsize = zsize
        self.xmin = xmin
        self.zmin = zmin
        self.xmax = xmax
        self.zmax = zmax
        self.align = align

        solid = Solid.make_wedge(xsize, ysize, zsize, xmin, zmin, xmax, zmax)
        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )
