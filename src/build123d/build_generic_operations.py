from build123d.build123d_common import *
from build123d.build_line import BuildLine
from build123d.build_sketch import BuildSketch
from build123d.build_part import BuildPart
from cadquery import Shape, Vertex


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
        current_context = Builder._get_context()
        if isinstance(current_context, BuildPart):
            rotation_value = (0, 0, 0) if rotation is None else rotation
            rotate = (
                Rotation(*rotation) if isinstance(rotation_value, tuple) else rotation
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
            current_context._add_to_pending(*new_faces)
            current_context._add_to_pending(*new_objects)

            # Can't use get_and_clear_locations because the solid needs to be
            # oriented to the workplane after being moved to a local location
            new_objects = [
                workplane.fromLocalCoords(solid.moved(location))
                for solid in new_solids
                for workplane in BuildPart._get_context().workplanes
                for location in BuildPart._get_context().locations
            ]
            current_context.locations = [Location(Vector())]
            current_context._add_to_context(*new_objects, mode=mode)
        elif isinstance(current_context, BuildSketch):
            rotation_angle = rotation if isinstance(rotation, float) else 0.0
            new_objects = []
            for obj in objects:
                new_objects.extend(
                    [
                        obj.rotate(
                            Vector(0, 0, 0), Vector(0, 0, 1), rotation_angle
                        ).moved(location)
                        for location in current_context.locations
                    ]
                )
            current_context._add_to_context(*new_objects, mode=mode)
            current_context.locations = [Location(Vector())]
        elif isinstance(current_context, BuildLine):
            new_objects = [obj for obj in objects if isinstance(obj, Edge)]
            for new_wires in filter(lambda o: isinstance(o, Wire), objects):
                new_objects.extend(new_wires.Edges())
            current_context._add_to_context(*new_objects, mode=mode)
        else:
            raise RuntimeError(
                f"Add does not support builder {current_context.__class__.__name__}"
            )
        super().__init__(Compound.makeCompound(new_objects).wrapped)


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
        current_context = Builder._get_context()
        if isinstance(current_context, BuildPart):
            new_objects = []
            for obj in objects:
                if isinstance(obj, Vertex):
                    continue
                bounding_box = obj.BoundingBox()
                bottom = Face.makePlane(
                    bounding_box.xlen,
                    bounding_box.ylen,
                    basePnt=(bounding_box.xmin, bounding_box.ymin, bounding_box.zmin),
                )
                new_objects.append(
                    Solid.extrudeLinear(bottom, (0, 0, bounding_box.zlen))
                )
            current_context._add_to_context(*new_objects, mode=mode)
            super().__init__(Compound.makeCompound(new_objects).wrapped)

        elif isinstance(current_context, BuildSketch):
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
                current_context._add_to_context(face, mode=mode)
            super().__init__(Compound.makeCompound(new_faces).wrapped)

        else:
            raise RuntimeError(
                f"BoundingBox does not support builder {current_context.__class__.__name__}"
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
        current_context = Builder._get_context()
        if isinstance(current_context, BuildPart):
            new_part = current_context.part.chamfer(length, length2, list(objects))
            current_context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(current_context, BuildSketch):
            new_faces = []
            for face in current_context.faces():
                vertices_in_face = filter(lambda v: v in face.Vertices(), objects)
                if vertices_in_face:
                    new_faces.append(face.chamfer2D(length, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            current_context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Chamfer does not support builder {current_context.__class__.__name__}"
            )


class Fillet(Compound):
    """Generic Operation: Fillet for Part and Sketch

    Fillet the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to fillet
        radius (float): fillet size - must be less than 1/2 local width
    """

    def __init__(self, *objects: Union[Edge, Vertex], radius: float):
        current_context = Builder._get_context()
        if isinstance(current_context, BuildPart):
            new_part = current_context.part.fillet(radius, list(objects))
            current_context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(current_context, BuildSketch):
            new_faces = []
            for face in current_context.faces():
                vertices_in_face = filter(lambda v: v in face.Vertices(), objects)
                if vertices_in_face:
                    new_faces.append(face.fillet2D(radius, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            current_context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Fillet does not support builder {current_context.__class__.__name__}"
            )
