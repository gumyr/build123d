"""
BuildSketch

name: build_sketch.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library used to build planar sketches.

Instead of existing constraints how about constraints that return locations
on objects:
- two circles: c1, c2
- "line tangent to c1 & c2" : 4 locations on each circle
  - these would be construction geometry
  - user sorts to select the ones they want
  - uses these points to build geometry
  - how many constraints are currently implemented?

license:

    Copyright 2022 Gumyr

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
import inspect
from math import pi, sin, cos, tan, radians
from typing import Union
from build123d.build_enums import Align, FontStyle, Mode
from build123d.geometry import (
    Axis,
    Location,
    Plane,
    Vector,
    VectorLike,
)
from build123d.topology import (
    Compound,
    Edge,
    Face,
    ShapeList,
    Wire,
)

from build123d.build_common import (
    Builder,
    logger,
    LocationList,
    WorkplaneList,
)


class BuildSketch(Builder):
    """BuildSketch

    Create planar 2D sketches (objects with area but not volume) from faces or lines.

    Args:
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    @staticmethod
    def _tag() -> str:
        """The name of the builder"""
        return "BuildSketch"

    @property
    def _obj(self) -> Compound:
        """The builder's object"""
        return self.sketch_local

    @property
    def _obj_name(self):
        """The name of the builder's object"""
        return "sketch"

    @property
    def sketch(self):
        """The global version of the sketch - may contain multiple sketches"""
        workplanes = (
            self.exit_workplanes
            if self.exit_workplanes
            else WorkplaneList._get_context().workplanes
        )
        global_objs = []
        for plane in workplanes:
            for face in self.sketch_local.faces():
                global_objs.append(plane.from_local_coords(face))
        return Compound.make_compound(global_objs)

    def __init__(
        self,
        *workplanes: Union[Face, Plane, Location],
        mode: Mode = Mode.ADD,
    ):
        self.workplanes = workplanes
        self.mode = mode
        self.sketch_local: Compound = None
        self.pending_edges: ShapeList[Edge] = ShapeList()
        self.last_faces: ShapeList[Face] = ShapeList()
        super().__init__(*workplanes, mode=mode)

    def solids(self, *args):
        """solids() not implemented"""
        raise NotImplementedError("solids() doesn't apply to BuildSketch")

    def consolidate_edges(self) -> Union[Wire, list[Wire]]:
        """Unify pending edges into one or more Wires"""
        wires = Wire.combine(self.pending_edges)
        return wires if len(wires) > 1 else wires[0]

    def _add_to_context(
        self, *objects: Union[Edge, Wire, Face, Compound], mode: Mode = Mode.ADD
    ):
        """Add objects to BuildSketch instance

        Core method to interface with BuildSketch instance. Input sequence of objects is
        parsed into lists of edges and faces. Edges are added to pending
        lists. Faces are combined with current sketch.

        Each operation generates a list of vertices, edges, and faces that have
        changed during this operation. These lists are only guaranteed to be valid up until
        the next operation as subsequent operations can eliminate these objects.

        Args:
            objects (Union[Edge, Wire, Face, Compound]): sequence of objects to add
            mode (Mode, optional): combination mode. Defaults to Mode.ADD.

        Raises:
            ValueError: Nothing to subtract from
            ValueError: Nothing to intersect with
            ValueError: Invalid mode
        """
        if mode != Mode.PRIVATE:
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_edges = [obj for obj in objects if isinstance(obj, Edge)]
            new_wires = [obj for obj in objects if isinstance(obj, Wire)]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(compound.get_type(Face))
                new_edges.extend(compound.get_type(Edge))
                new_wires.extend(compound.get_type(Wire))

            pre_vertices = (
                set()
                if self.sketch_local is None
                else set(self.sketch_local.vertices())
            )
            pre_edges = (
                set() if self.sketch_local is None else set(self.sketch_local.edges())
            )
            pre_faces = (
                set() if self.sketch_local is None else set(self.sketch_local.faces())
            )
            if new_faces:
                logger.debug(
                    "Attempting to integrate %d Face(s) into sketch with Mode=%s",
                    len(new_faces),
                    mode,
                )
                if mode == Mode.ADD:
                    if self.sketch_local is None:
                        self.sketch_local = Compound.make_compound(new_faces)
                    else:
                        self.sketch_local = self.sketch_local.fuse(*new_faces).clean()
                elif mode == Mode.SUBTRACT:
                    if self.sketch_local is None:
                        raise RuntimeError("No sketch to subtract from")
                    self.sketch_local = self.sketch_local.cut(*new_faces).clean()
                elif mode == Mode.INTERSECT:
                    if self.sketch_local is None:
                        raise RuntimeError("No sketch to intersect with")
                    self.sketch_local = self.sketch_local.intersect(*new_faces).clean()
                elif mode == Mode.REPLACE:
                    self.sketch_local = Compound.make_compound(new_faces).clean()

                logger.debug(
                    "Completed integrating %d Face(s) into sketch with Mode=%s",
                    len(new_faces),
                    mode,
                )

            post_vertices = (
                set()
                if self.sketch_local is None
                else set(self.sketch_local.vertices())
            )
            post_edges = (
                set() if self.sketch_local is None else set(self.sketch_local.edges())
            )
            post_faces = (
                set() if self.sketch_local is None else set(self.sketch_local.faces())
            )
            self.last_vertices = ShapeList(post_vertices - pre_vertices)
            self.last_edges = ShapeList(post_edges - pre_edges)
            self.last_faces = ShapeList(post_faces - pre_faces)

            self.pending_edges.extend(
                new_edges + [e for w in new_wires for e in w.edges()]
            )

    @classmethod
    def _get_context(cls, caller=None) -> "BuildSketch":
        """Return the instance of the current builder"""
        logger.info(
            "Context requested by %s",
            type(inspect.currentframe().f_back.f_locals["self"]).__name__,
        )

        result = cls._current.get(None)
        if caller is not None and result is None:
            if hasattr(caller, "_applies_to"):
                raise RuntimeError(
                    f"No valid context found, use one of {caller._applies_to}"
                )
            raise RuntimeError("No valid context found")

        return result


#
# Operations
#


class MakeFace(Face):
    """Sketch Operation: Make Face

    Create a face from the given perimeter edges

    Args:
        edges (Edge): sequence of perimeter edges
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(self, *edges: Edge, mode: Mode = Mode.ADD):
        context: BuildSketch = BuildSketch._get_context(self)
        context.validate_inputs(self, edges)

        self.edges = edges
        self.mode = mode

        outer_edges = edges if edges else context.pending_edges
        pending_face = Face.make_from_wires(Wire.combine(outer_edges)[0])
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()
        super().__init__(pending_face.wrapped)


class MakeHull(Face):
    """Sketch Operation: Make Hull

    Create a face from the convex hull of the given edges

    Args:
        edges (Edge, optional): sequence of edges to hull. Defaults to all
            pending and sketch edges.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(self, *edges: Edge, mode: Mode = Mode.ADD):
        context: BuildSketch = BuildSketch._get_context(self)
        context.validate_inputs(self, edges)

        if not (edges or context.pending_edges or context.sketch_local):
            raise ValueError("No objects to create a convex hull")

        self.edges = edges
        self.mode = mode

        hull_edges = list(edges) if edges else context.pending_edges
        if context.sketch_local:
            hull_edges.extend(context.sketch_local.edges())
        pending_face = Face.make_from_wires(Wire.make_convex_hull(hull_edges))
        context._add_to_context(pending_face, mode=mode)
        context.pending_edges = ShapeList()
        super().__init__(pending_face.wrapped)


#
# Objects
#
class BaseSketchObject(Compound):
    """BaseSketchObject

    Base class for all BuildSketch objects

    Args:
        face (Face): face to create
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to None.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        obj: Union[Compound, Face],
        rotation: float = 0,
        align: tuple[Align, Align] = None,
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch = BuildSketch._get_context(self)
        self.rotation = rotation
        self.mode = mode

        if align:
            bbox = obj.bounding_box()
            align_offset = []
            for i in range(2):
                if align[i] == Align.MIN:
                    align_offset.append(-bbox.min.to_tuple()[i])
                elif align[i] == Align.CENTER:
                    align_offset.append(
                        -(bbox.min.to_tuple()[i] + bbox.max.to_tuple()[i]) / 2
                    )
                elif align[i] == Align.MAX:
                    align_offset.append(-bbox.max.to_tuple()[i])
        else:
            align_offset = [0, 0]

        obj = obj.locate(
            Location((0, 0, 0), (0, 0, 1), rotation) * Location(Vector(*align_offset))
        )

        new_faces = [
            face.moved(location)
            for face in obj.faces()
            for location in LocationList._get_context().local_locations
        ]
        context._add_to_context(*new_faces, mode=mode)

        Compound.__init__(self, Compound.make_compound(new_faces).wrapped)


class Circle(BaseSketchObject):
    """Sketch Object: Circle

    Add circle(s) to the sketch.

    Args:
        radius (float): circle size
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        radius: float,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        self.radius = radius
        self.align = align

        face = Face.make_from_wires(Wire.make_circle(radius))
        super().__init__(face, 0, align, mode)


class Ellipse(BaseSketchObject):
    """Sketch Object: Ellipse

    Add ellipse(s) to sketch.

    Args:
        x_radius (float): horizontal radius
        y_radius (float): vertical radius
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        x_radius: float,
        y_radius: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        self.x_radius = x_radius
        self.y_radius = y_radius
        self.align = align

        face = Face.make_from_wires(Wire.make_ellipse(x_radius, y_radius))
        super().__init__(face, rotation, align, mode)


class Polygon(BaseSketchObject):
    """Sketch Object: Polygon

    Add polygon(s) defined by given sequence of points to sketch.

    Args:
        pts (VectorLike): sequence of points defining the vertices of polygon
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        *pts: VectorLike,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        self.pts = pts
        self.align = align

        poly_pts = [Vector(p) for p in pts]
        face = Face.make_from_wires(Wire.make_polygon(poly_pts))
        super().__init__(face, rotation, align, mode)


class Rectangle(BaseSketchObject):
    """Sketch Object: Rectangle

    Add rectangle(s) to sketch.

    Args:
        width (float): horizontal size
        height (float): vertical size
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        self.width = width
        self.rectangle_height = height
        self.align = align

        face = Face.make_rect(height, width)
        super().__init__(face, rotation, align, mode)


class RectangleRounded(BaseSketchObject):
    """Sketch Object: RectangleRounded

    Add rectangle(s) with filleted corners to sketch.

    Args:
        width (float): horizontal size
        height (float): vertical size
        radius (float): fillet radius
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        width: float,
        height: float,
        radius: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        if width <= 2 * radius or height <= 2 * radius:
            raise ValueError("width and height must be > 2*radius")
        self.width = width
        self.rectangle_height = height
        self.radius = radius
        self.align = align

        face = Face.make_rect(height, width)
        face = face.fillet_2d(radius, face.vertices())
        super().__init__(face, rotation, align, mode)


class RegularPolygon(BaseSketchObject):
    """Sketch Object: Regular Polygon

    Add regular polygon(s) to sketch.

    Args:
        radius (float): distance from origin to vertices
        side_count (int): number of polygon sides
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        radius: float,
        side_count: int,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        if side_count < 3:
            raise ValueError(
                f"RegularPolygon must have at least three sides, not {side_count}"
            )
        self.radius = radius
        self.side_count = side_count
        self.align = align

        pts = ShapeList(
            [
                Vector(
                    radius * cos(i * 2 * pi / side_count + radians(rotation)),
                    radius * sin(i * 2 * pi / side_count + radians(rotation)),
                )
                for i in range(side_count + 1)
            ]
        )
        pts_sorted = [pts.sort_by(Axis.X), pts.sort_by(Axis.Y)]
        # pylint doesn't recognize that a ShapeList of Vector is valid
        # pylint: disable=no-member
        mins = [pts_sorted[0][0].X, pts_sorted[1][0].Y]
        maxs = [pts_sorted[0][-1].X, pts_sorted[1][-1].Y]

        if align:
            align_offset = []
            for i in range(2):
                if align[i] == Align.MIN:
                    align_offset.append(-mins[i])
                elif align[i] == Align.CENTER:
                    align_offset.append(0)
                elif align[i] == Align.MAX:
                    align_offset.append(-maxs[i])
        else:
            align_offset = [0, 0]
        pts = [point + Vector(*align_offset) for point in pts]

        face = Face.make_from_wires(Wire.make_polygon(pts))
        super().__init__(face, rotation=0, align=None, mode=mode)


class SlotArc(BaseSketchObject):
    """Sketch Object: Arc Slot

    Add slot(s) following an arc to sketch.

    Args:
        arc (Union[Edge, Wire]): center line of slot
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        arc: Union[Edge, Wire],
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        self.arc = arc
        self.slot_height = height

        arc = arc if isinstance(arc, Wire) else Wire.make_wire([arc])
        face = Face.make_from_wires(arc.offset_2d(height / 2)[0]).rotate(
            Axis.Z, rotation
        )
        super().__init__(face, rotation, None, mode)


class SlotCenterPoint(BaseSketchObject):
    """Sketch Object: Center Point Slot

    Add a slot(s) defined by the center of the slot and the center of one of the
    circular arcs at the end. The other end will be generated to create a symmetric
    slot.

    Args:
        center (VectorLike): slot center point
        point (VectorLike): slot center of arc point
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        center: VectorLike,
        point: VectorLike,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        center_v = Vector(center)
        point_v = Vector(point)
        self.slot_center = center_v
        self.point = point_v
        self.slot_height = height

        half_line = point_v - center_v
        face = Face.make_from_wires(
            Wire.combine(
                [
                    Edge.make_line(point_v, center_v),
                    Edge.make_line(center_v, center_v - half_line),
                ]
            )[0].offset_2d(height / 2)[0]
        )
        super().__init__(face, rotation, None, mode)


class SlotCenterToCenter(BaseSketchObject):
    """Sketch Object: Center to Center points Slot

    Add slot(s) defined by the distance between the center of the two
    end arcs.

    Args:
        center_separation (float): distance between two arc centers
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        center_separation: float,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        self.center_separation = center_separation
        self.slot_height = height

        face = Face.make_from_wires(
            Wire.make_wire(
                [
                    Edge.make_line(Vector(-center_separation / 2, 0, 0), Vector()),
                    Edge.make_line(Vector(), Vector(+center_separation / 2, 0, 0)),
                ]
            ).offset_2d(height / 2)[0]
        )
        super().__init__(face, rotation, None, mode)


class SlotOverall(BaseSketchObject):
    """Sketch Object: Center to Center points Slot

    Add slot(s) defined by the overall with of the slot.

    Args:
        width (float): overall width of the slot
        height (float): diameter of end circles
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        width: float,
        height: float,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        self.width = width
        self.slot_height = height

        face = Face.make_from_wires(
            Wire.make_wire(
                [
                    Edge.make_line(Vector(-width / 2 + height / 2, 0, 0), Vector()),
                    Edge.make_line(Vector(), Vector(+width / 2 - height / 2, 0, 0)),
                ]
            ).offset_2d(height / 2)[0]
        )
        super().__init__(face, rotation, None, mode)


class Text(BaseSketchObject):
    """Sketch Object: Text

    Add text(s) to the sketch.

    Args:
        txt (str): text to be rendered
        font_size (float): size of the font in model units
        font (str, optional): font name. Defaults to "Arial".
        font_path (str, optional): system path to font library. Defaults to None.
        font_style (Font_Style, optional): style. Defaults to Font_Style.REGULAR.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        path (Union[Edge, Wire], optional): path for text to follow. Defaults to None.
        position_on_path (float, optional): the relative location on path to position the
            text, values must be between 0.0 and 1.0. Defaults to 0.0.
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        txt: str,
        font_size: float,
        font: str = "Arial",
        font_path: str = None,
        font_style: FontStyle = FontStyle.REGULAR,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        path: Union[Edge, Wire] = None,
        position_on_path: float = 0.0,
        rotation: float = 0,
        mode: Mode = Mode.ADD,
    ) -> Compound:
        context: BuildSketch = BuildSketch._get_context(self)
        context.validate_inputs(self)

        self.txt = txt
        self.font_size = font_size
        self.font = font
        self.font_path = font_path
        self.font_style = font_style
        self.align = align
        self.text_path = path
        self.position_on_path = position_on_path
        self.rotation = rotation
        self.mode = mode

        text_string = Compound.make_text(
            txt=txt,
            font_size=font_size,
            font=font,
            font_path=font_path,
            font_style=font_style,
            align=align,
            position_on_path=position_on_path,
            text_path=path,
        )
        super().__init__(text_string, rotation, None, mode)


class Trapezoid(BaseSketchObject):
    """Sketch Object: Trapezoid

    Add trapezoid(s) to the sketch.

    Args:
        width (float): horizontal width
        height (float): vertical height
        left_side_angle (float): bottom left interior angle
        right_side_angle (float, optional): bottom right interior angle. If not provided,
            the trapezoid will be symmetric. Defaults to None.
        rotation (float, optional): angles to rotate objects. Defaults to 0.
        align (tuple[Align, Align], optional): align min, center, or max of object.
            Defaults to (Align.CENTER, Align.CENTER).
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Give angles result in an invalid trapezoid
    """

    _applies_to = [BuildSketch._tag()]

    def __init__(
        self,
        width: float,
        height: float,
        left_side_angle: float,
        right_side_angle: float = None,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
        BuildSketch._get_context(self).validate_inputs(self)
        right_side_angle = left_side_angle if not right_side_angle else right_side_angle

        self.width = width
        self.trapezoid_height = height
        self.left_side_angle = left_side_angle
        self.right_side_angle = right_side_angle
        self.align = align

        # Calculate the reduction of the top on both sides
        reduction_left = (
            0 if left_side_angle == 90 else height / tan(radians(left_side_angle))
        )
        reduction_right = (
            0 if right_side_angle == 90 else height / tan(radians(right_side_angle))
        )
        if reduction_left + reduction_right >= width:
            raise ValueError("Trapezoid top invalid - change angles")
        pts = []
        pts.append(Vector(-width / 2, -height / 2))
        pts.append(Vector(width / 2, -height / 2))
        pts.append(Vector(width / 2 - reduction_right, height / 2))
        pts.append(Vector(-width / 2 + reduction_left, height / 2))
        pts.append(pts[0])
        face = Face.make_from_wires(Wire.make_polygon(pts))
        super().__init__(face, rotation, align, mode)
