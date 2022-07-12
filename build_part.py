"""
TODO:
- add TwistExtrude, ProjectText
- add centered to wedge
- check centered on non XY plane - probably not correct, need to localize offset
"""
from math import radians, tan
from typing import Union
from cadquery import (
    Edge,
    Face,
    Wire,
    Vector,
    Location,
    Vertex,
    Compound,
    Solid,
    Plane,
)
from cadquery.occ_impl.shapes import VectorLike
import cq_warehouse.extensions
from build123d_common import *

# logging.basicConfig(
#     filename="build123D.log",
#     encoding="utf-8",
#     level=logging.DEBUG,
#     # level=logging.CRITICAL,
#     format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)s - %(funcName)20s() ] - %(message)s",
# )


class BuildPart:
    """BuildPart

    Create 3D parts (objects with the property of volume) from sketches or 3D objects.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
        workplane (Plane, optional): initial plane to work on. Defaults to Plane.named("XY").
    """

    @property
    def workplane_count(self) -> int:
        """Number of active workplanes"""
        return len(self.workplanes)

    @property
    def pending_faces_count(self) -> int:
        """Number of pending faces"""
        return len(self.pending_faces.values())

    @property
    def pending_edges_count(self) -> int:
        """Number of pending edges"""
        return len(self.pending_edges.values())

    @property
    def pending_location_count(self) -> int:
        """Number of current locations"""
        return len(self.locations)

    def __init__(
        self,
        mode: Mode = Mode.ADDITION,
        workplane: Plane = Plane.named("XY"),
    ):
        self.part: Compound = None
        self.workplanes: list[Plane] = [workplane]
        self.locations: list[Location] = [Location(workplane.origin)]
        self.pending_faces: dict[int : list[Face]] = {0: []}
        self.pending_edges: dict[int : list[Edge]] = {0: []}
        self.mode = mode
        self.last_vertices = []
        self.last_edges = []
        self.last_faces = []
        self.last_solids = []

    def __enter__(self):
        """Upon entering BuildPart, add current BuildPart instance to context stack"""
        context_stack.append(self)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Upon exiting BuildPart - do nothing"""

    def workplane(self, *workplanes: Plane, replace=True):
        """Create Workplane(s)

        Add a sequence of planes as workplanes possibly replacing existing workplanes.

        Args:
            workplanes (Plane): a sequence of planes to add as workplanes
            replace (bool, optional): replace existing workplanes. Defaults to True.
        """
        if replace:
            self.workplanes = []
        for plane in workplanes:
            self.workplanes.append(plane)

    def vertices(self, select: Select = Select.ALL) -> VertexList[Vertex]:
        """Return Vertices from Part

        Return either all or the vertices created during the last operation.

        Args:
            select (Select, optional): Vertex selector. Defaults to Select.ALL.

        Returns:
            VertexList[Vertex]: Vertices extracted
        """
        vertex_list = []
        if select == Select.ALL:
            for edge in self.part.Edges():
                vertex_list.extend(edge.Vertices())
        elif select == Select.LAST:
            vertex_list = self.last_vertices
        return VertexList(set(vertex_list))

    def edges(self, select: Select = Select.ALL) -> ShapeList[Edge]:
        """Return Edges from Part

        Return either all or the edges created during the last operation.

        Args:
            select (Select, optional): Edge selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Edge]: Edges extracted
        """
        if select == Select.ALL:
            edge_list = self.part.Edges()
        elif select == Select.LAST:
            edge_list = self.last_edges
        return ShapeList(edge_list)

    def faces(self, select: Select = Select.ALL) -> ShapeList[Face]:
        """Return Faces from Part

        Return either all or the faces created during the last operation.

        Args:
            select (Select, optional): Face selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Face]: Faces extracted
        """
        if select == Select.ALL:
            face_list = self.part.Faces()
        elif select == Select.LAST:
            face_list = self.last_edges
        return ShapeList(face_list)

    def solids(self, select: Select = Select.ALL) -> ShapeList[Solid]:
        """Return Solids from Part

        Return either all or the solids created during the last operation.

        Args:
            select (Select, optional): Solid selector. Defaults to Select.ALL.

        Returns:
            ShapeList[Solid]: Solids extracted
        """
        if select == Select.ALL:
            solid_list = self.part.Solids()
        elif select == Select.LAST:
            solid_list = self.last_solids
        return ShapeList(solid_list)

    @staticmethod
    def get_context() -> "BuildPart":
        """Return the current BuildPart instance. Used by Object and Operation
        classes to refer to the current context."""
        return context_stack[-1]

    def add_to_pending(self, *objects: Union[Edge, Face]):
        """Add objects to BuildPart pending lists

        Args:
            objects (Union[Edge, Face]): sequence of objects to add
        """
        for obj in objects:
            for i, workplane in enumerate(self.workplanes):
                for loc in self.locations:
                    localized_obj = workplane.fromLocalCoords(obj.moved(loc))
                    if i in self.pending_faces:
                        if isinstance(obj, Face):
                            self.pending_faces[i].append(localized_obj)
                        else:
                            self.pending_edges[i].append(localized_obj)
                    else:
                        if isinstance(obj, Face):
                            self.pending_faces[i] = [localized_obj]
                        else:
                            self.pending_edges[i] = [localized_obj]

    def add_to_context(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        mode: Mode = Mode.ADDITION,
    ):
        """Add objects to BuildPart instance

        Core method to interface with BuildPart instance. Input sequence of objects is
        parsed into lists of edges, faces, and solids. Edges and faces are added to pending
        lists. Solids are combined with current part.

        Each operation generates a list of vertices, edges, faces, and solids that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can element these objects.

        Args:
            objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of objects to add
            mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.

        Raises:
            ValueError: Nothing to subtract from
            ValueError: Nothing to intersect with
            ValueError: Invalid mode
        """
        if context_stack and mode != Mode.PRIVATE:
            # Sort the provided objects into edges, faces and solids
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_solids = [obj for obj in objects if isinstance(obj, Solid)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(compound.Faces())
                new_solids.extend(compound.Solids())
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            for compound in filter(lambda o: isinstance(o, Wire), objects):
                new_edges.extend(compound.Edges())

            pre_vertices = set() if self.part is None else set(self.part.Vertices())
            pre_edges = set() if self.part is None else set(self.part.Edges())
            pre_faces = set() if self.part is None else set(self.part.Faces())
            pre_solids = set() if self.part is None else set(self.part.Solids())

            if new_solids:
                if mode == Mode.ADDITION:
                    if self.part is None:
                        if len(new_solids) == 1:
                            self.part = new_solids[0]
                        else:
                            self.part = new_solids.pop().fuse(*new_solids)
                    else:
                        self.part = self.part.fuse(*new_solids).clean()
                elif mode == Mode.SUBTRACTION:
                    if self.part is None:
                        raise ValueError("Nothing to subtract from")
                    self.part = self.part.cut(*new_solids).clean()
                elif mode == Mode.INTERSECTION:
                    if self.part is None:
                        raise ValueError("Nothing to intersect with")
                    self.part = self.part.intersect(*new_solids).clean()
                elif mode == Mode.CONSTRUCTION:
                    pass
                else:
                    raise ValueError(f"Invalid mode: {mode}")

            post_vertices = set() if self.part is None else set(self.part.Vertices())
            post_edges = set() if self.part is None else set(self.part.Edges())
            post_faces = set() if self.part is None else set(self.part.Faces())
            post_solids = set() if self.part is None else set(self.part.Solids())
            self.last_vertices = list(post_vertices - pre_vertices)
            self.last_edges = list(post_edges - pre_edges)
            self.last_faces = list(post_faces - pre_faces)
            self.last_solids = list(post_solids - pre_solids)

            self.add_to_pending(*new_edges)
            self.add_to_pending(*new_faces)

    def get_and_clear_locations(self) -> list:
        """Return position and planes from current points and workplanes and clear locations."""
        location_planes = []
        for workplane in self.workplanes:
            location_planes.extend(
                [
                    ((Location(workplane) * location), workplane)
                    for location in self.locations
                ]
            )
        self.locations = [Location(Vector())]
        return location_planes


#
# Operations
#


class ChamferPart(Compound):
    """Part Operation: Chamfer

    Chamfer the given sequence of edges.

    Args:
        edges (Edge): sequence of edges to chamfer
        length1 (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.
    """

    def __init__(self, *edges: Edge, length1: float, length2: float = None):
        new_part = BuildPart.get_context().part.chamfer(length1, length2, list(edges))
        BuildPart.get_context().part = new_part
        super().__init__(new_part.wrapped)


class CounterBoreHole(Compound):
    """Part Operation: Counter Bore Hole

    Create a counter bore hole in part.

    Args:
        radius (float): hole size
        counter_bore_radius (float): counter bore size
        counter_bore_depth (float): counter bore depth
        depth (float, optional): hole depth - None implies through part. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACTION.
    """

    def __init__(
        self,
        radius: float,
        counter_bore_radius: float,
        counter_bore_depth: float,
        depth: float = None,
        mode: Mode = Mode.SUBTRACTION,
    ):
        hole_depth = (
            BuildPart.get_context().part.BoundingBox().DiagonalLength
            if depth is None
            else depth
        )
        location_planes = BuildPart.get_context().get_and_clear_locations()
        new_solids = [
            Solid.makeCylinder(radius, hole_depth, loc.position(), plane.zDir * -1.0).fuse(
                Solid.makeCylinder(
                    counter_bore_radius, counter_bore_depth, loc.position(), plane.zDir * -1.0
                )
            )
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class CounterSinkHole(Compound):
    """Part Operation: Counter Sink Hole

    Create a counter sink hole in part.

    Args:
        radius (float): hole size
        counter_sink_radius (float): counter sink size
        depth (float, optional): hole depth - None implies through part. Defaults to None.
        counter_sink_angle (float, optional): cone angle. Defaults to 82.
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACTION.
    """

    def __init__(
        self,
        radius: float,
        counter_sink_radius: float,
        depth: float = None,
        counter_sink_angle: float = 82,  # Common tip angle
        mode: Mode = Mode.SUBTRACTION,
    ):
        hole_depth = (
            BuildPart.get_context().part.BoundingBox().DiagonalLength
            if depth is None
            else depth
        )
        cone_height = counter_sink_radius / tan(radians(counter_sink_angle / 2.0))
        location_planes = BuildPart.get_context().get_and_clear_locations()
        new_solids = [
            Solid.makeCylinder(radius, hole_depth, loc.position(), plane.zDir * -1.0).fuse(
                Solid.makeCone(
                    counter_sink_radius,
                    0.0,
                    cone_height,
                    loc,
                    plane.zDir * -1.0,
                )
            )
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Extrude(Compound):
    """Part Operation: Extrude

    Extrude a sketch/face and combine with part.

    Args:
        until (Union[float, Until, Face]): depth of extrude or extrude limit
        both (bool, optional): extrude in both directions. Defaults to False.
        taper (float, optional): taper during extrusion. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        until: Union[float, Until, Face],
        both: bool = False,
        taper: float = None,
        mode: Mode = Mode.ADDITION,
    ):
        new_solids: list[Solid] = []
        for plane_index, faces in BuildPart.get_context().pending_faces.items():
            for face in faces:
                new_solids.append(
                    Solid.extrudeLinear(
                        face,
                        BuildPart.get_context().workplanes[plane_index].zDir * until,
                        0,
                    )
                )
                if both:
                    new_solids.append(
                        Solid.extrudeLinear(
                            face,
                            BuildPart.get_context().workplanes[plane_index].zDir
                            * until
                            * -1.0,
                            0,
                        )
                    )

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class FilletPart(Compound):
    """Part Operation: Fillet

    Fillet the given sequence of edges.

    Args:
        edges (Edge): sequence of edges to fillet
        radius (float): fillet size - must be less than 1/2 local width
    """

    def __init__(self, *edges: Edge, radius: float):
        new_part = BuildPart.get_context().part.fillet(radius, list(edges))
        BuildPart.get_context().part = new_part
        super().__init__(new_part.wrapped)


class Hole(Compound):
    """Part Operation: Hole

    Create a hole in part.

    Args:
        radius (float): hole size
        depth (float, optional): hole depth - None implies through part. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.SUBTRACTION.
    """

    def __init__(
        self,
        radius: float,
        depth: float = None,
        mode: Mode = Mode.SUBTRACTION,
    ):
        hole_depth = (
            BuildPart.get_context().part.BoundingBox().DiagonalLength
            if depth is None
            else depth
        )
        location_planes = BuildPart.get_context().get_and_clear_locations()
        new_solids = [
            Solid.makeCylinder(radius, hole_depth, loc.position(), plane.zDir * -1.0, 360)
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Loft(Solid):
    """Part Operation: Loft

    Loft the pending sketches/faces, across all workplanes, into a solid.

    Args:
        ruled (bool, optional): discontiguous layer tangents. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(self, ruled: bool = False, mode: Mode = Mode.ADDITION):

        loft_wires = []
        for i in range(len(BuildPart.get_context().workplanes)):
            for face in BuildPart.get_context().pending_faces[i]:
                loft_wires.append(face.outerWire())
        new_solid = Solid.makeLoft(loft_wires, ruled)

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(new_solid, mode=mode)
        super().__init__(new_solid.wrapped)


class PushPointsToPart:
    """Part Operation: Push Points

    Push the sequence of tuples, Vectors or Locations to builder internal structure,
    replacing existing locations.

    Args:
        pts (Union[VectorLike, Location]): sequence of points
    """

    def __init__(self, *pts: Union[VectorLike, Location]):
        new_locations = [
            pt if isinstance(pt, Location) else Location(Vector(pt)) for pt in pts
        ]
        BuildPart.get_context().locations = new_locations


class Revolve(Compound):
    """Part Operation: Revolve

    Revolve the pending sketches/faces about the given local axis.

    Args:
        revolution_arc (float, optional): angular size of revolution. Defaults to 360.0.
        axis_start (VectorLike, optional): axis start in local coordinates. Defaults to None.
        axis_end (VectorLike, optional): axis end in local coordinates. Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        revolution_arc: float = 360.0,
        axis_start: VectorLike = None,
        axis_end: VectorLike = None,
        mode: Mode = Mode.ADDITION,
    ):
        # Make sure we account for users specifying angles larger than 360 degrees, and
        # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
        angle = revolution_arc % 360.0
        angle = 360.0 if angle == 0 else angle

        new_solids = []
        for i, workplane in enumerate(BuildPart.get_context().workplanes):
            axis = []
            if axis_start is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 0, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_start)))

            if axis_end is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 1, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_end)))

            for face in BuildPart.get_context().pending_faces[i]:
                new_solids.append(Solid.revolve(face, angle, *axis))

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Shell(Compound):
    """Part Operation: Shell

    Create a hollow shell from part with provided open faces.

    Args:
        faces (Face): sequence of faces to open
        thickness (float): thickness of shell - positive values shell outwards, negative inwards.
        kind (Kind, optional): edge construction option. Defaults to Kind.ARC.
    """

    def __init__(
        self,
        *faces: Face,
        thickness: float,
        kind: Kind = Kind.ARC,
    ):
        new_part = BuildPart.get_context().part.shell(
            faces, thickness, kind=kind.name.lower()
        )
        BuildPart.get_context().part = new_part
        super().__init__(new_part.wrapped)


class Split(Compound):
    """Part Operation: Split

    Bisect part with plane and keep either top or bottom. Does not change part.

    Args:
        bisect_by (Plane, optional): plane to segment part. Defaults to Plane.named("XZ").
        keep (Keep, optional): selector for which segment to keep. Defaults to Keep.TOP.
    """

    def __init__(self, bisect_by: Plane = Plane.named("XZ"), keep: Keep = Keep.TOP):
        max_size = BuildPart.get_context().BoundingBox().DiagonalLength
        cutter_center = (
            Vector(-max_size, -max_size, 0)
            if keep == Keep.TOP
            else Vector(-max_size, -max_size, -2 * max_size)
        )
        cutter = bisect_by.fromLocalCoords(
            Solid.makeBox(2 * max_size, 2 * max_size, 2 * max_size).moved(
                Location(cutter_center)
            )
        )
        split_object = BuildPart.get_context().part.intersect(cutter)
        super().__init__(split_object.wrapped)


class Sweep(Compound):
    """Part Operation: Sweep

    Sweep pending sketches/faces along path.

    Args:
        path (Union[Edge, Wire]): path to follow
        multisection (bool, optional): sweep multiple on path. Defaults to False.
        make_solid (bool, optional): create solid instead of face. Defaults to True.
        is_frenet (bool, optional): use freenet algorithm. Defaults to False.
        transition (Transition, optional): discontinuity handling option.
            Defaults to Transition.RIGHT.
        normal (VectorLike, optional): fixed normal. Defaults to None.
        binormal (Union[Edge, Wire], optional): guide rotation along path. Defaults to None.
        mode (Mode, optional): combination. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        path: Union[Edge, Wire],
        multisection: bool = False,
        make_solid: bool = True,
        is_frenet: bool = False,
        transition: Transition = Transition.RIGHT,
        normal: VectorLike = None,
        binormal: Union[Edge, Wire] = None,
        mode: Mode = Mode.ADDITION,
    ):
        path_wire = Wire.assembleEdges([path]) if isinstance(path, Edge) else path
        if binormal is None:
            binormal_mode = Vector(normal)
        elif isinstance(binormal, Edge):
            binormal_mode = Wire.assembleEdges([binormal])
        else:
            binormal_mode = binormal

        new_solids = []
        for i in range(BuildPart.get_context().workplane_count):
            if not multisection:
                for face in BuildPart.get_context().pending_faces[i]:
                    new_solids.append(
                        Solid.sweep(
                            face,
                            path_wire,
                            make_solid,
                            is_frenet,
                            binormal_mode,
                            transition,
                        )
                    )
            else:
                sections = [
                    face.outerWire()
                    for face in BuildPart.get_context().pending_faces[i]
                ]
                new_solids.append(
                    Solid.sweep_multi(
                        sections, path_wire, make_solid, is_frenet, binormal_mode
                    )
                )

        BuildPart.get_context().pending_faces = {0: []}
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class WorkplanesFromFaces:
    """Part Operation: Workplanes from Faces

    Create workplanes from the given sequence of faces, optionally replacing existing
    workplanes. The workplane origin is aligned to the center of the face.

    Args:
        faces (Face): sequence of faces to convert to workplanes.
        replace (bool, optional): replace existing workplanes. Defaults to True.
    """

    def __init__(self, *faces: Face, replace=True):
        new_planes = [
            Plane(origin=face.Center(), normal=face.normalAt(face.Center()))
            for face in faces
        ]
        BuildPart.get_context().workplane(*new_planes, replace=replace)


#
# Objects
#


class AddToPart(Compound):
    """Part Object: Add Object to Builder

    Add an object to the builder. Edges and Wires are added to pending_edges.
    Compounds of Face are added to pending_faces. Solids or Compounds of Solid are
    combined into the part.

    Args:
        objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of object to add
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        mode (Mode, optional): combine mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        rotation: RotationLike = (0, 0, 0),
        mode: Mode = Mode.ADDITION,
    ):
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        new_faces = [obj for obj in objects if isinstance(obj, Face)]
        new_solids = [obj.moved(rotate) for obj in objects if isinstance(obj, Solid)]
        for compound in filter(lambda o: isinstance(o, Compound), objects):
            new_faces.extend(compound.Faces())
            new_solids.extend(compound.Solids())
        new_edges = [obj for obj in objects if isinstance(obj, Edge)]
        for compound in filter(lambda o: isinstance(o, Wire), objects):
            new_edges.extend(compound.Edges())

        # Add to pending faces and edges
        BuildPart.get_context().add_to_pending(new_faces)
        BuildPart.get_context().add_to_pending(new_edges)

        # Can't use get_and_clear_locations because the solid needs to be
        # oriented to the workplane after being moved to a local location
        located_solids = [
            workplane.fromLocalCoords(solid.moved(location))
            for solid in new_solids
            for workplane in BuildPart.get_context().workplanes
            for location in BuildPart.get_context().locations
        ]
        BuildPart.get_context().locations = [Location(Vector())]
        BuildPart.get_context().add_to_context(*located_solids, mode=mode)
        super().__init__(Compound.makeCompound(located_solids).wrapped)


class Box(Compound):
    """Part Object: Box

    Create a box(es) and combine with part.

    Args:
        length (float): box size
        width (float): box size
        height (float): box size
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADDITION,
    ):
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart.get_context().get_and_clear_locations()
        center_offset = Vector(
            -length / 2 if centered[0] else 0,
            -width / 2 if centered[1] else 0,
            -height / 2 if centered[2] else 0,
        )
        new_solids = [
            Solid.makeBox(length, width, height, loc.position() + center_offset, plane.zDir).moved(
                rotate
            )
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Cone(Compound):
    """Part Object: Cone

    Create a cone(s) and combine with part.

    Args:
        bottom_radius (float): cone size
        top_radius (float): top size, could be zero
        height (float): cone size
        arc_size (float, optional): angular size of cone. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        bottom_radius: float,
        top_radius: float,
        height: float,
        arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADDITION,
    ):
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart.get_context().get_and_clear_locations()
        center_offset = Vector(
            0 if centered[0] else max(bottom_radius, top_radius),
            0 if centered[1] else max(bottom_radius, top_radius),
            -height / 2 if centered[2] else 0,
        )
        new_solids = [
            Solid.makeCone(
                bottom_radius,
                top_radius,
                height,
                loc.position() + center_offset,
                plane.zDir,
                arc_size,
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Cylinder(Compound):
    """Part Object: Cylinder

    Create a cylinder(s) and combine with part.

    Args:
        radius (float): cylinder size
        height (float): cylinder size
        arc_size (float, optional): angular size of cone. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        radius: float,
        height: float,
        arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADDITION,
    ):
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart.get_context().get_and_clear_locations()
        center_offset = Vector(
            0 if centered[0] else radius,
            0 if centered[1] else radius,
            -height / 2 if centered[2] else 0,
        )
        new_solids = [
            Solid.makeCylinder(
                radius, height, loc.position() + center_offset, plane.zDir, arc_size
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Sphere(Compound):
    """Part Object: Sphere

    Create a sphere(s) and combine with part.

    Args:
        radius (float): sphere size
        arc_size1 (float, optional): angular size of sphere. Defaults to -90.
        arc_size2 (float, optional): angular size of sphere. Defaults to 90.
        arc_size3 (float, optional): angular size of sphere. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        radius: float,
        arc_size1: float = -90,
        arc_size2: float = 90,
        arc_size3: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADDITION,
    ):
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart.get_context().get_and_clear_locations()
        center_offset = Vector(
            0 if centered[0] else radius,
            0 if centered[1] else radius,
            0 if centered[2] else radius,
        )
        new_solids = [
            Solid.makeSphere(
                radius, loc.position() + center_offset, plane.zDir, arc_size1, arc_size2, arc_size3
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Torus(Compound):
    """Part Object: Torus

    Create a torus(es) and combine with part.


    Args:
        major_radius (float): torus size
        minor_radius (float): torus size
        major_arc_size (float, optional): angular size or torus. Defaults to 0.
        minor_arc_size (float, optional): angular size or torus. Defaults to 360.
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        centered (tuple[bool, bool, bool], optional): center about axes.
            Defaults to (True, True, True).
        mode (Mode, optional): combine mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        major_radius: float,
        minor_radius: float,
        major_arc_size: float = 0,
        minor_arc_size: float = 360,
        rotation: RotationLike = (0, 0, 0),
        centered: tuple[bool, bool, bool] = (True, True, True),
        mode: Mode = Mode.ADDITION,
    ):
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart.get_context().get_and_clear_locations()
        center_offset = Vector(
            0 if centered[0] else major_radius,
            0 if centered[1] else major_radius,
            0 if centered[2] else minor_radius,
        )
        new_solids = [
            Solid.makeTorus(
                major_radius,
                minor_radius,
                loc.position() + center_offset,
                plane.zDir,
                major_arc_size,
                minor_arc_size,
            ).moved(rotate)
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)


class Wedge(Compound):
    """Part Object: Wedge

    Create a wedge(s) and combine with part.

    Args:
        dx (float): distance along the X axis
        dy (float): distance along the Y axis
        dz (float): distance along the Z axis
        xmin (float): minimum X location
        zmin (float): minimum Z location
        xmax (float): maximum X location
        zmax (float): maximum Z location
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        mode (Mode, optional): combine mode. Defaults to Mode.ADDITION.
    """

    def __init__(
        self,
        dx: float,
        dy: float,
        dz: float,
        xmin: float,
        zmin: float,
        xmax: float,
        zmax: float,
        rotation: RotationLike = (0, 0, 0),
        mode: Mode = Mode.ADDITION,
    ):
        rotate = Rotation(*rotation) if isinstance(rotation, tuple) else rotation
        location_planes = BuildPart.get_context().get_and_clear_locations()
        new_solids = [
            Solid.makeWedge(dx, dy, dz, xmin, zmin, xmax, zmax, loc.position(), plane.zDir).moved(
                rotate
            )
            for loc, plane in location_planes
        ]
        BuildPart.get_context().add_to_context(*new_solids, mode=mode)
        super().__init__(Compound.makeCompound(new_solids).wrapped)
