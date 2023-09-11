from OCP.BinTools import BinTools
from OCP.TopoDS import (
    TopoDS_Shape,
    TopoDS_Compound,
    TopoDS_CompSolid,
    TopoDS_Solid,
    TopoDS_Shell,
    TopoDS_Face,
    TopoDS_Wire,
    TopoDS_Edge,
    TopoDS_Vertex,
)
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Quaternion, gp_Vec
import io
import copyreg
from build123d.topology import downcast
import struct


def serialize_shape(shape: TopoDS_Shape):
    """
    Serialize a OCP shape, this method can be used to provide a custom serialization algo for pickle
    """
    if shape is None:
        return None

    bio = io.BytesIO()
    BinTools.Write_s(shape, bio)
    buffer = bio.getvalue()
    return buffer


def deserialize_shape(buffer: bytes):
    """
    This does the opposite as serialize, it construct a TopoDS_Shape from bytes.
    """
    if buffer is None:
        return None

    shape = TopoDS_Shape()
    bio = io.BytesIO(buffer)
    BinTools.Read_s(shape, bio)
    return downcast(shape)


def serialize_location(location: TopLoc_Location):
    """
    Serialize a OCP location, this method can be used to provide a custom serialization algo for pickle
    """
    if location is None:
        return None
    transfo = location.Transformation()
    translation = transfo.TranslationPart()
    rotation = transfo.GetRotation()
    # convert floats in bytes
    translation_bytes = bytearray()
    for i in range(1, 4):
        translation_bytes.extend(struct.pack("f", translation.Coord(i)))
    rotation_bytes = bytearray()
    rotation_bytes.extend(struct.pack("f", rotation.X()))
    rotation_bytes.extend(struct.pack("f", rotation.Y()))
    rotation_bytes.extend(struct.pack("f", rotation.Z()))
    rotation_bytes.extend(struct.pack("f", rotation.W()))

    buffer = bytearray()
    buffer.extend(translation_bytes)
    buffer.extend(rotation_bytes)
    return buffer


def deserialize_location(buffer: bytes):
    """
    This does the opposite as serialize, it construct a TopLoc_Location from bytes.
    """
    if buffer is None:
        return None

    # Makes 4 bytes chunks (floats are 4 bytes long)
    chunks = iter(struct.iter_unpack("f", buffer))
    translation = gp_Vec(
        next(chunks)[0],
        next(chunks)[0],
        next(chunks)[0],
    )

    # Read the rotation bytes
    rotation = gp_Quaternion(
        next(chunks)[0],
        next(chunks)[0],
        next(chunks)[0],
        next(chunks)[0],
    )

    # Create the TopLoc_Location object
    transfo = gp_Trsf()
    transfo.SetTransformation(rotation, translation)

    return TopLoc_Location(transfo)


def reduce_shape(shape: TopoDS_Shape):
    """Special function used by pickle to serialize or deserialize OCP Shapes objects"""
    return (deserialize_shape, (serialize_shape(shape),))


def reduce_location(location: TopLoc_Location):
    """Special function used by pickle to serialize or deserialize OCP Location objects"""
    return (deserialize_location, (serialize_location(location),))


def modify_copyreg():
    """Modify the copyreg so that pickle knows what to look for when it tries to pickle an OCP Shape"""
    copyreg.pickle(TopoDS_Shape, reduce_shape)
    copyreg.pickle(TopoDS_Compound, reduce_shape)
    copyreg.pickle(TopoDS_CompSolid, reduce_shape)
    copyreg.pickle(TopoDS_Solid, reduce_shape)
    copyreg.pickle(TopoDS_Shell, reduce_shape)
    copyreg.pickle(TopoDS_Face, reduce_shape)
    copyreg.pickle(TopoDS_Wire, reduce_shape)
    copyreg.pickle(TopoDS_Edge, reduce_shape)
    copyreg.pickle(TopoDS_Vertex, reduce_shape)
    copyreg.pickle(TopLoc_Location, reduce_location)
