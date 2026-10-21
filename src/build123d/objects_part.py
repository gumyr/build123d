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

from collections.abc import Iterable
from math import radians, tan
from scipy.spatial import ConvexHull

from build123d.build_common import BaseObject
from build123d.build_enums import Align, Mode
from build123d.build_part import BuildPart
from build123d.build_sheet import BuildSheet
from build123d.geometry import (
    Location,
    Plane,
    Rotation,
    RotationLike,
    Vector,
    VectorLike,
)
from build123d.topology import (
    Compound,
    Face,
    Part,
    ShapeList,
    Shell,
    Solid,
    Wire,
    tuplify,
)


class BasePartObject(Part, BaseObject):
    """BasePartObject

    Base class for all BuildPart objects & operations

    Args:
        solid (Solid): object to create
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag, BuildSheet._tag]

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

        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        self.rotation = rotate
        self.mode = mode
        transformed_part = part.moved(rotate) if rotate != Rotation() else part
        new_solids = [transformed_part]

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
            joints=transformed_part.joints,
            parent=part.parent,
            children=part.children,
        )
        for joint in self.joints.values():
            joint._reparent(self)


class Box(BasePartObject):
    """Part Object: Box

    Create a box defined by length, width, and height.

    The names follow the 3D CAD convention: ``length`` is the size along the X
    axis, ``width`` along Y and ``height`` along Z. Note that this differs from
    :class:`~objects_sketch.Rectangle`, where ``height`` is the Y size:
    ``Box(length=l, width=w, height=h)`` has the footprint of
    ``Rectangle(width=l, height=w)``.

    Args:
        length (float): box length, the size along the X axis
        width (float): box width, the size along the Y axis
        height (float): box height, the size along the Z axis
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to (Align.CENTER, Align.CENTER, Align.CENTER)
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag, BuildSheet._tag]

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

    _applies_to = [BuildPart._tag, BuildSheet._tag]

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


class ConvexPolyhedron(BasePartObject):
    """Part Object: ConvexPolyhedron

    Create a convex solid from the convex hull of the provided points.

    Args:
        points (Iterable[VectorLike]): vertices of the polyhedron
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0)
        align (Align | tuple[Align, Align, Align] | None, optional): align MIN, CENTER,
            or MAX of object. Defaults to Align.NONE
        mode (Mode, optional): combine mode. Defaults to Mode.ADD
    """

    _applies_to = [BuildPart._tag, BuildSheet._tag]

    def __init__(
        self,
        points: Iterable[VectorLike],
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = Align.NONE,
        mode: Mode = Mode.ADD,
    ):

        pnts: list[tuple] = [tuple(Vector(p)) for p in points]

        # Create a convex hull from the vertices
        convex_hull = ConvexHull(pnts).simplices.tolist()

        # Create faces from the vertex indices
        polyhedron_faces = []
        for face_vertex_indices in convex_hull:
            corner_vertices = [pnts[i] for i in face_vertex_indices]
            polyhedron_faces.append(Face(Wire.make_polygon(corner_vertices)))

        # Create the solid from the Faces
        polyhedron = Solid(Shell(polyhedron_faces)).clean()

        super().__init__(
            part=polyhedron, rotation=rotation, align=tuplify(align, 3), mode=mode
        )


class _BaseHole(BasePartObject):
    """Shared functionality for hole-style part operations."""

    def _through_hole_depth(self) -> float:
        """Calculate a conservative depth from the target and hole origins.

        Uses the Builder's current object so a hole passes through a BuildSheet
        reference shell as well as a BuildPart part.
        """
        context = self._get_builder_context()
        # An empty Builder object is falsy but not None, so test the object
        # itself: a BuildSheet starts with an empty Shell
        if context is None or not context._obj:
            raise ValueError("No depth provided")

        part_origin = context._obj.bounding_box().center()
        origin_distance = max(
            (part_origin - location.position).length
            for location in self._get_object_locations()
        )
        return context.max_dimension + origin_distance

    @staticmethod
    def _check_point_angle(point_angle: float | None, depth: float | None):
        """Raise if a drill point is asked for a through hole or with an impossible angle"""
        if point_angle is None:
            return
        if depth is None:
            raise ValueError("A drill point needs a blind hole: provide a depth")
        if not 0 < point_angle < 180:
            raise ValueError(
                f"point_angle must be between 0 and 180 degrees, not {point_angle}"
            )

    @staticmethod
    def _drill_point(radius: float, depth: float, point_angle: float) -> Solid:
        """The cone a drill point leaves below the full diameter of a blind hole"""
        return Solid.make_cone(
            radius,
            0.0,
            radius / tan(radians(point_angle / 2.0)),
            Plane(origin=(0, 0, -depth), z_dir=(0, 0, -1)),
        )


class CounterBoreHole(_BaseHole):
    """Part Operation: Counter Bore Hole

    Create a counter bore hole defined by radius, counter bore radius, counter bore and depth.

    Args:
        radius (float): hole radius
        counter_bore_radius (float): counter bore radius
        counter_bore_depth (float): counter bore depth
        depth (float, optional): hole depth, through part if None. Defaults to None
        point_angle (float, optional): included angle of the drill point at the bottom
            of a blind hole, whose depth is then measured to the end of the full
            diameter; flat bottom if None. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT
    """

    _applies_to = [BuildPart._tag, BuildSheet._tag]

    def __init__(
        self,
        radius: float,
        counter_bore_radius: float,
        counter_bore_depth: float,
        depth: float | None = None,
        point_angle: float | None = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        self._check_point_angle(point_angle, depth)
        self.radius = radius
        self.counter_bore_radius = counter_bore_radius
        self.counter_bore_depth = counter_bore_depth
        self.point_angle = point_angle
        if depth is not None:
            self.hole_depth = depth
        else:
            self.hole_depth = self._through_hole_depth()
        self.mode = mode

        cutters = [
            Solid.make_cylinder(
                counter_bore_radius,
                counter_bore_depth + self.hole_depth,
                Plane((0, 0, -counter_bore_depth)),
            )
        ]
        if point_angle is not None:
            cutters.append(self._drill_point(radius, self.hole_depth, point_angle))
        fused = Solid.make_cylinder(
            radius, self.hole_depth, Plane(origin=(0, 0, 0), z_dir=(0, 0, -1))
        ).fuse(*cutters)
        if isinstance(fused, ShapeList):
            solid = Part(fused)
        else:
            solid = fused
        super().__init__(part=solid, rotation=(0, 0, 0), mode=mode)


class CounterDrillHole(_BaseHole):
    """Part Operation: Counter Drill Hole

    Create a counter drill hole: a counter bore whose step down to the hole is the
    cone left by the point of the larger drill instead of a flat shoulder.

    Args:
        radius (float): hole radius
        counter_drill_radius (float): counter drill radius
        counter_drill_depth (float): counter drill depth, measured to the end of its
            full diameter
        depth (float, optional): hole depth, through part if None. Defaults to None
        counter_drill_angle (float, optional): included angle of the step between the
            two diameters. Defaults to 118
        point_angle (float, optional): included angle of the drill point at the bottom
            of a blind hole, whose depth is then measured to the end of the full
            diameter; flat bottom if None. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT

    Raises:
        ValueError: counter drill radius not larger than the hole radius
        ValueError: blind hole that ends before the counter drill's step
    """

    _applies_to = [BuildPart._tag, BuildSheet._tag]

    def __init__(
        self,
        radius: float,
        counter_drill_radius: float,
        counter_drill_depth: float,
        depth: float | None = None,
        counter_drill_angle: float = 118,  # Common drill point angle
        point_angle: float | None = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        self._check_point_angle(point_angle, depth)
        if counter_drill_radius <= radius:
            raise ValueError("counter_drill_radius must be larger than radius")
        if not 0 < counter_drill_angle < 180:
            raise ValueError(
                "counter_drill_angle must be between 0 and 180 degrees, "
                f"not {counter_drill_angle}"
            )
        self.radius = radius
        self.counter_drill_radius = counter_drill_radius
        self.counter_drill_depth = counter_drill_depth
        self.counter_drill_angle = counter_drill_angle
        self.point_angle = point_angle
        step_height = (counter_drill_radius - radius) / tan(
            radians(counter_drill_angle / 2.0)
        )
        if depth is not None:
            if depth <= counter_drill_depth + step_height:
                raise ValueError("depth must reach past the counter drill's step")
            self.hole_depth = depth
        else:
            self.hole_depth = self._through_hole_depth()
        self.mode = mode

        cutters = [
            Solid.make_cylinder(
                counter_drill_radius,
                counter_drill_depth + self.hole_depth,
                Plane((0, 0, -counter_drill_depth)),
            ),
            Solid.make_cone(
                counter_drill_radius,
                radius,
                step_height,
                Plane(origin=(0, 0, -counter_drill_depth), z_dir=(0, 0, -1)),
            ),
        ]
        if point_angle is not None:
            cutters.append(self._drill_point(radius, self.hole_depth, point_angle))
        fused = Solid.make_cylinder(
            radius, self.hole_depth, Plane(origin=(0, 0, 0), z_dir=(0, 0, -1))
        ).fuse(*cutters)
        if isinstance(fused, ShapeList):
            solid = Part(fused)
        else:
            solid = fused
        super().__init__(part=solid, rotation=(0, 0, 0), mode=mode)


class CounterSinkHole(_BaseHole):
    """Part Operation: Counter Sink Hole

    Create a countersink hole defined by radius, countersink radius, countersink
    angle, and depth.

    Args:
        radius (float): hole radius
        counter_sink_radius (float): countersink radius
        depth (float, optional): hole depth, through part if None. Defaults to None
        counter_sink_angle (float, optional): cone angle. Defaults to 82
        point_angle (float, optional): included angle of the drill point at the bottom
            of a blind hole, whose depth is then measured to the end of the full
            diameter; flat bottom if None. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT
    """

    _applies_to = [BuildPart._tag, BuildSheet._tag]

    def __init__(
        self,
        radius: float,
        counter_sink_radius: float,
        depth: float | None = None,
        counter_sink_angle: float = 82,  # Common tip angle
        point_angle: float | None = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        self._check_point_angle(point_angle, depth)
        self.radius = radius
        self.counter_sink_radius = counter_sink_radius
        if depth is not None:
            self.hole_depth = depth
        else:
            self.hole_depth = self._through_hole_depth()
        self.counter_sink_angle = counter_sink_angle
        self.point_angle = point_angle
        self.mode = mode
        cone_height = counter_sink_radius / tan(radians(counter_sink_angle / 2.0))

        cutters = [
            Solid.make_cone(
                counter_sink_radius,
                0.0,
                cone_height,
                Plane(origin=(0, 0, 0), z_dir=(0, 0, -1)),
            ),
            Solid.make_cylinder(counter_sink_radius, self.hole_depth),
        ]
        if point_angle is not None:
            cutters.append(self._drill_point(radius, self.hole_depth, point_angle))
        fused = Solid.make_cylinder(
            radius, self.hole_depth, Plane(origin=(0, 0, 0), z_dir=(0, 0, -1))
        ).fuse(*cutters)
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

    _applies_to = [BuildPart._tag, BuildSheet._tag]

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


class Hole(_BaseHole):
    """Part Operation: Hole

    Create a hole defined by radius and depth.

    Args:
        radius (float): hole radius
        depth (float, optional): hole depth, through part if None. Defaults to None
        point_angle (float, optional): included angle of the drill point at the bottom
            of a blind hole, whose depth is then measured to the end of the full
            diameter; flat bottom if None. Defaults to None
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACT
    """

    _applies_to = [BuildPart._tag, BuildSheet._tag]

    def __init__(
        self,
        radius: float,
        depth: float | None = None,
        point_angle: float | None = None,
        mode: Mode = Mode.SUBTRACT,
    ):
        self._check_point_angle(point_angle, depth)
        self.radius = radius
        self.point_angle = point_angle
        if depth is not None:
            self.hole_depth = 2 * depth
        else:
            self.hole_depth = 2 * self._through_hole_depth()
        self.mode = mode

        # To ensure the hole will go all the way through the part when
        # no depth is specified, calculate depth based on the part and
        # hole location. In this case start the hole above the part
        # and go all the way through.
        hole_start = (0, 0, self.hole_depth / 2) if depth is None else (0, 0, 0)
        solid = Solid.make_cylinder(
            radius, self.hole_depth, Plane(origin=hole_start, z_dir=(0, 0, -1))
        )
        align: tuple[Align, Align, Align] | None = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        )
        if point_angle is not None:
            # Centring would move the cone's tip into the middle, so place the
            # cylinder where centring leaves it, depth above and below
            half_depth = self.hole_depth / 2
            solid = Solid.make_cylinder(
                radius,
                self.hole_depth,
                Plane(origin=(0, 0, half_depth), z_dir=(0, 0, -1)),
            ).fuse(self._drill_point(radius, half_depth, point_angle))
            align = None
        super().__init__(
            part=solid,
            align=align,
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

    _applies_to = [BuildPart._tag, BuildSheet._tag]

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

    _applies_to = [BuildPart._tag, BuildSheet._tag]

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

    _applies_to = [BuildPart._tag, BuildSheet._tag]

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
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
