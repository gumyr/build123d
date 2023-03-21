#
# TEMPORARY FOR MIGRATION ONLY
#
import copy
from build123d import *
from build123d.topology import class_LUT

from typing import Union, List


class Hole:
    def __init__(self):
        raise NotImplemented


class CounterSinkHole:
    def __init__(self):
        raise NotImplemented


class CounterBoreHole:
    def __init__(self):
        raise NotImplemented


def chamfer(
    obj: Union[Part, Sketch],
    objects: Union[List[Union[Edge, Vertex]], Edge, Vertex],
    length: float,
    length2: float = None,
):
    if isinstance(obj, Part):
        compound = Compound.make_compound(
            [obj.solids()[0].chamfer(length, length2, list(objects))]
        )
    else:
        new_faces = []
        for face in obj.faces():
            vertices_in_face = [v for v in face.vertices() if v in objects]
            if vertices_in_face:
                new_faces.append(face.chamfer_2d(length, vertices_in_face))
            else:
                new_faces.append(face)
        compound = Compound.make_compound(new_faces)
    compound._dim = obj._dim
    return compound


def fillet(
    obj: Union[Part, Sketch],
    objects: Union[List[Union[Edge, Vertex]], Edge, Vertex],
    radius: float,
):
    if isinstance(obj, Part):
        compound = Compound.make_compound(
            [obj.solids()[0].fillet(radius, list(objects))]
        )
    else:
        new_faces = []
        for face in obj.faces():
            vertices_in_face = [v for v in face.vertices() if v in objects]
            if vertices_in_face:
                new_faces.append(face.fillet_2d(radius, vertices_in_face))
            else:
                new_faces.append(face)
        compound = Compound.make_compound(new_faces)
    compound._dim = obj._dim
    return compound


def mirror(
    *objects: Union[Part, Sketch, Curve],
    about: Plane = Plane.XZ,
):
    mirrored = [copy.deepcopy(o).mirror(about) for o in objects]
    compound = Compound.make_compound(mirrored)
    dim = objects[0]._dim if isinstance(objects, (list, tuple)) else objects._dim
    return class_LUT[dim](compound.wrapped)


def make_face(objs: Union[Sketch, List[Edge]]):
    if isinstance(objs, Sketch) and objs._dim == 1:
        edges = objs.edges()
    elif isinstance(objs, (tuple, list)):
        edges = objs
    else:
        edges = [objs]

    return Sketch.make_compound([Face.make_from_wires(*Wire.combine(edges))])
