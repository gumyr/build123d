from itertools import product
from math import sqrt
from typing import Union
from build123d import (
    BuildLine,
    BuildSketch,
    BuildPart,
    Mode,
    RotationLike,
    Rotation,
    Axis,
    Builder,
)
from cadquery import (
    Shape,
    Vertex,
    Plane,
    Compound,
    Edge,
    Wire,
    Face,
    Solid,
    Location,
    Vector,
)
from cadquery.occ_impl.shapes import VectorLike

#
# Objects
#


class Add(Compound):
    """Generic Object: Add Object to Part or Sketch

    Add an object to the builder.

    if BuildPart:
        Edges and Wires are added to pending_edges. Compounds of Face are added to
        pending_faces. Solids or Compounds of Solid are combined into the part.
    elif BuildSketch:
        Edges and Wires are added to pending_edges. Compounds of Face are added to sketch.
    elif BuildLine:
        Edges and Wires are added to line.

    Args:
        objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of objects to add
        rotation (Union[float, RotationLike], optional): rotation angle for sketch,
            rotation about each axis for part. Defaults to None.
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        rotation: Union[float, RotationLike] = None,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            rotation_value = (0, 0, 0) if rotation is None else rotation
            rotate = (
                Rotation(*rotation_value)
                if isinstance(rotation_value, tuple)
                else rotation
            )
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_solids = [
                obj.moved(rotate) for obj in objects if isinstance(obj, Solid)
            ]
            for new_wires in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(new_wires.Faces())
                new_solids.extend(new_wires.Solids())
            new_objects = [obj for obj in objects if isinstance(obj, Edge)]
            for new_wires in filter(lambda o: isinstance(o, Wire), objects):
                new_objects.extend(new_wires.Edges())

            # Add to pending faces and edges
            context._add_to_pending(*new_faces)
            context._add_to_pending(*new_objects)

            # Can't use get_and_clear_locations because the solid needs to be
            # oriented to the workplane after being moved to a local location
            new_objects = [
                workplane.fromLocalCoords(solid.moved(location))
                for solid in new_solids
                for workplane in context.workplanes
                for location in context.locations
            ]
            context.locations = [Location(Vector())]
            context._add_to_context(*new_objects, mode=mode)
        elif isinstance(context, (BuildLine, BuildSketch)):
            rotation_angle = rotation if isinstance(rotation, (int, float)) else 0.0
            new_objects = []
            for obj in objects:
                new_objects.extend(
                    [
                        obj.rotate(
                            Vector(0, 0, 0), Vector(0, 0, 1), rotation_angle
                        ).moved(location)
                        for location in context.locations
                    ]
                )
            context._add_to_context(*new_objects, mode=mode)
            context.locations = [Location(Vector())]
        # elif isinstance(context, BuildLine):
        #     new_objects = [obj for obj in objects if isinstance(obj, Edge)]
        #     for new_wires in filter(lambda o: isinstance(o, Wire), objects):
        #         new_objects.extend(new_wires.Edges())
        #     context._add_to_context(*new_objects, mode=mode)
        else:
            raise RuntimeError(
                f"Add does not support builder {context.__class__.__name__}"
            )
        super().__init__(Compound.makeCompound(new_objects).wrapped)


#
# Operations
#


class BoundingBox(Compound):
    """Generic Operation: Add Bounding Box to Part or Sketch

    Add the 2D or 3D bounding boxes of the object sequence

    Args:
        objects (Shape): sequence of objects
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Shape,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            new_objects = []
            for obj in objects:
                if isinstance(obj, Vertex):
                    continue
                bounding_box = obj.BoundingBox()
                new_objects.append(
                    Solid.makeBox(
                        bounding_box.xlen,
                        bounding_box.ylen,
                        bounding_box.zlen,
                        pnt=(bounding_box.xmin, bounding_box.ymin, bounding_box.zmin),
                    )
                )
            context._add_to_context(*new_objects, mode=mode)
            super().__init__(Compound.makeCompound(new_objects).wrapped)

        elif isinstance(context, BuildSketch):
            new_faces = []
            for obj in objects:
                if isinstance(obj, Vertex):
                    continue
                bounding_box = obj.BoundingBox()
                vertices = [
                    (bounding_box.xmin, bounding_box.ymin),
                    (bounding_box.xmin, bounding_box.ymax),
                    (bounding_box.xmax, bounding_box.ymax),
                    (bounding_box.xmax, bounding_box.ymin),
                    (bounding_box.xmin, bounding_box.ymin),
                ]
                new_faces.append(
                    Face.makeFromWires(Wire.makePolygon([Vector(v) for v in vertices]))
                )
            for face in new_faces:
                context._add_to_context(face, mode=mode)
            super().__init__(Compound.makeCompound(new_faces).wrapped)

        else:
            raise RuntimeError(
                f"BoundingBox does not support builder {context.__class__.__name__}"
            )


class Chamfer(Compound):
    """Generic Operation: Chamfer for Part and Sketch

    Chamfer the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to chamfer
        length (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.
    """

    def __init__(
        self, *objects: Union[Edge, Vertex], length: float, length2: float = None
    ):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            new_part = context.part.chamfer(length, length2, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.Vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.chamfer2D(length, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Chamfer does not support builder {context.__class__.__name__}"
            )


class Fillet(Compound):
    """Generic Operation: Fillet for Part and Sketch

    Fillet the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to fillet
        radius (float): fillet size - must be less than 1/2 local width
    """

    def __init__(self, *objects: Union[Edge, Vertex], radius: float):
        context: Builder = Builder._get_context()
        if isinstance(context, BuildPart):
            new_part = context.part.fillet(radius, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.Vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.fillet2D(radius, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Fillet does not support builder {context.__class__.__name__}"
            )


class HexArray:
    """Generic Operation: Hex Array

    Creates a hexagon array of points and pushes them to Part or Sketch locations.

    Args:
        diagonal: tip to tip size of hexagon ( must be > 0)
        xCount: number of points ( > 0 )
        yCount: number of points ( > 0 )
        centered: specify centering along each axis.

    Raises:
        ValueError: Spacing and count must be > 0
    """

    def __init__(
        self,
        diagonal: float,
        xCount: int,
        yCount: int,
        centered: tuple[bool, bool] = (True, True),
    ):
        context: Builder = Builder._get_context()
        xSpacing = 3 * diagonal / 4
        ySpacing = diagonal * sqrt(3) / 2
        if xSpacing <= 0 or ySpacing <= 0 or xCount < 1 or yCount < 1:
            raise ValueError("Spacing and count must be > 0 ")

        lpoints = []  # coordinates relative to bottom left point
        for x in range(0, xCount, 2):
            for y in range(yCount):
                lpoints.append(Vector(xSpacing * x, ySpacing * y + ySpacing / 2))
        for x in range(1, xCount, 2):
            for y in range(yCount):
                lpoints.append(Vector(xSpacing * x, ySpacing * y + ySpacing))

        # shift points down and left relative to origin if requested
        offset = Vector()
        if centered[0]:
            offset += Vector(-xSpacing * (xCount - 1) * 0.5, 0)
        if centered[1]:
            offset += Vector(0, -ySpacing * yCount * 0.5)
        lpoints = [x + offset for x in lpoints]

        # convert to locations
        new_locations = [Location(pt) for pt in lpoints]

        context.locations = new_locations


class Mirror(Compound):
    """Generic Operation: Mirror

    Add the mirror of the provided sequence of faces about the given axis to Line or Sketch.

    Args:
        objects (Union[Edge, Face,Compound]): sequence of edges or faces to mirror
        axis (Axis, optional): axis to mirror about. Defaults to Axis.X.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Compound],
        axis: Axis = Axis.X,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()
        new_edges = [obj for obj in objects if isinstance(obj, Edge)]
        new_wires = [obj for obj in objects if isinstance(obj, Wire)]
        new_faces = [obj for obj in objects if isinstance(obj, Face)]
        # new_solids = [obj for obj in objects if isinstance(obj, Solid)]
        for compound in filter(lambda o: isinstance(o, Compound), objects):
            new_faces.extend(compound.Faces())
            # new_solids.extend(compound.Solids())

        mirrored_edges = Plane.named("XY").mirrorInPlane(new_edges, axis=axis.name)
        mirrored_wires = Plane.named("XY").mirrorInPlane(new_wires, axis=axis.name)
        mirrored_faces = Plane.named("XY").mirrorInPlane(new_faces, axis=axis.name)
        # mirrored_solids = Plane.named("XY").mirrorInPlane(new_solids, axis=axis.name)

        if isinstance(context, BuildLine):
            context._add_to_context(*mirrored_edges, mode=mode)
            context._add_to_context(*mirrored_wires, mode=mode)
        elif isinstance(context, BuildSketch):
            context._add_to_context(*mirrored_edges, mode=mode)
            context._add_to_context(*mirrored_wires, mode=mode)
            context._add_to_context(*mirrored_faces, mode=mode)
        # elif isinstance(context, BuildPart):
        #     context._add_to_context(*mirrored_edges, mode=mode)
        #     context._add_to_context(*mirrored_wires, mode=mode)
        #     context._add_to_context(*mirrored_faces, mode=mode)
        #     context._add_to_context(*mirrored_solids, mode=mode)
        else:
            raise RuntimeError(
                f"Mirror does not support builder {context.__class__.__name__}"
            )
        super().__init__(
            Compound.makeCompound(
                mirrored_edges + mirrored_wires + mirrored_faces
            ).wrapped
        )


class PolarArray:
    """Generic Operation: Polar Array

    Push a polar array of locations to Part or Sketch

    Args:
        radius (float): array radius
        start_angle (float): angle to first point from +ve X axis
        stop_angle (float): angle to last point from +ve X axis
        count (int): Number of points to push
        rotate (bool, optional): Align locations with arc tangents. Defaults to True.

    Raises:
        ValueError: Count must be greater than or equal to 1
    """

    def __init__(
        self,
        radius: float,
        start_angle: float,
        stop_angle: float,
        count: int,
        rotate: bool = True,
    ):
        context: Builder = Builder._get_context()
        if count < 1:
            raise ValueError(f"At least 1 elements required, requested {count}")

        angle_step = (stop_angle - start_angle) / count

        # Note: rotate==False==0 so the location orientation doesn't change
        new_locations = [
            Location(
                Vector(radius, 0).rotateZ(start_angle + angle_step * i),
                Vector(0, 0, 1),
                rotate * angle_step * i,
            )
            for i in range(count)
        ]

        context.locations = new_locations


class PushPoints:
    """Generic Operation: Push Points

    Push sequence of locations to Part or Sketch

    Args:
        pts (Union[VectorLike, Vertex, Location]): sequence of points to push
    """

    def __init__(self, *pts: Union[VectorLike, Vertex, Location]):
        context: Builder = Builder._get_context()
        new_locations = []
        for pt in pts:
            if isinstance(pt, Location):
                new_locations.append(pt)
            elif isinstance(pt, Vector):
                new_locations.append(Location(pt))
            elif isinstance(pt, Vertex):
                new_locations.append(Location(Vector(pt.toTuple())))
            elif isinstance(pt, tuple):
                new_locations.append(Location(Vector(pt)))
            else:
                raise ValueError(f"PushPoints doesn't accept type {type(pt)}")
        context.locations = new_locations


class RectangularArray:
    """Generic Operation: Rectangular Array

    Push a rectangular array of locations to Part or Sketch

    Args:
        x_spacing (float): horizontal spacing
        y_spacing (float): vertical spacing
        x_count (int): number of horizontal points
        y_count (int): number of vertical points

    Raises:
        ValueError: Either x or y count must be greater than or equal to one.
    """

    def __init__(self, x_spacing: float, y_spacing: float, x_count: int, y_count: int):
        context: Builder = Builder._get_context()
        if x_count < 1 or y_count < 1:
            raise ValueError(
                f"At least 1 elements required, requested {x_count}, {y_count}"
            )

        new_locations = []
        offset = Vector((x_count - 1) * x_spacing, (y_count - 1) * y_spacing) * 0.5
        for i, j in product(range(x_count), range(y_count)):
            new_locations.append(
                Location(Vector(i * x_spacing, j * y_spacing) - offset)
            )

        context.locations = new_locations
