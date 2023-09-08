import platform
import tempfile
from OCP.BinTools import BinTools
from OCP.TopoDS import TopoDS_Shape, TopoDS_Compound, TopoDS_CompSolid, TopoDS_Solid, TopoDS_Shell, TopoDS_Face, TopoDS_Wire, TopoDS_Edge, TopoDS_Vertex
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf
import io
import copyreg
from build123d.topology import downcast

def serialize_shape(shape : TopoDS_Shape):
    """
    Serialize a OCP shape, this method can be used to provide a custom serialization algo for pickle
    """
    if shape is None:
        return None

    if platform.system() == "Darwin":
        with tempfile.NamedTemporaryFile() as tf:
            BinTools.Write_s(shape, tf.name)
            with open(tf.name, "rb") as fd:
                buffer = fd.read()
    else:
        bio = io.BytesIO()
        BinTools.Write_s(shape, bio)
        buffer = bio.getvalue()
    return buffer


def deserialize_shape(buffer : bytes):
    """
    This does the opposite as serialize, it construct a TopoDS_Shape from bytes.
    """
    if buffer is None:
        return None

    shape = TopoDS_Shape()
    if platform.system() == "Darwin":
        with tempfile.NamedTemporaryFile() as tf:
            with open(tf.name, "wb") as fd:
                fd.write(buffer)
            BinTools.Read_s(shape, tf.name)
    else:
        bio = io.BytesIO(buffer)
        BinTools.Read_s(shape, bio)
    return downcast(shape)

def serialize_loc(loc : TopLoc_Location):
    """
    Serialize a OCP TopLoc_Location, this method can be used to provide a custom serialization algo for pickle
    """
    bio = io.BytesIO()
    loc.Transformation().DumpJson(bio)
    buffer = bio.getvalue()
    return buffer

def deserialize_loc(buffer : bytes):
    """
    This does the opposite as serialize, it construct a TopLoc_Location from bytes.
    """
    if buffer is None:
        return None
    t = gp_Trsf()
    gp_Trsf()
    sio = buffer.decode()
    t.InitFromJson(sio,0)
    loc = TopLoc_Location(t)
    
    return loc

def reduce_shape(shape : TopoDS_Shape):
    """Special function used by pickle to serialize or deserialize OCP Shapes objects"""
    return (deserialize_shape, (serialize_shape(shape),))

def reduce_loc(loc: TopLoc_Location):
    return (deserialize_loc, (serialize_loc(loc),))

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
    copyreg.pickle(TopLoc_Location, reduce_loc)

if __name__ == "__main__":
    from build123d import *
    import pickle
    a = Box(1,2,3)
    c = pickle.dumps(a)
    b = pickle.loads(c)
    b