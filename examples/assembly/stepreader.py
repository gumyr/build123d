import os
import time
import unicodedata

from build123d import *

import sys

sys.path.append("examples/assembly")
from assembly import reference, Assembly
from ocp_vscode import *

from OCP.Quantity import Quantity_ColorRGBA
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_ChildIterator, TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_COMPOUND, TopAbs_COMPSOLID, TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import (
    XCAFDoc_ColorCurv,
    XCAFDoc_ColorGen,
    XCAFDoc_ColorSurf,
    XCAFDoc_DocumentTool,
)

from ocp_tessellate.utils import warn

DEFAULT_COLOR = (0.8, 0.8, 0.8, 1)


def clean_string(s):
    return (
        "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")
        .replace(" ", "_")
        .replace(".", "_")
        .replace("(", "_")
        .replace(")", "_")
    )


class StepReader:
    def __init__(self, analyse_faces=True, split_compounds=True, use_colors=True):
        self.analyse_faces = analyse_faces
        self.split_compounds = split_compounds
        self.use_colors = use_colors
        self.shape_tool = None
        self.color_tool = None
        self.assemblies = None

    def _create_assembly_object(
        self, name, loc=None, color=None, shape=None, children=None
    ):
        """
        Create a new object
        :param name: object name
        :param loc: object location (TopLoc_Location)
        :param color: 4 tuple (RGBA) with values 0<=x<=1
        :param shape: object shape (TopoDS_Shape)
        :param children: list of AssemblyObject objects
        :return: AssemblyObject
        """
        return {
            "name": name,
            "loc": loc,
            "color": color,
            "shape": shape,
            "shapes": children,
        }

    def get_name(self, label):
        """
        Get name of a TDF_Label object
        :param label: TDF_label of a STEP file
        :return: str
        """
        t = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), t):
            name = TCollection_AsciiString(t.Get()).ToCString()
            return clean_string(name)
        else:
            return "Component"

    def get_color(self, shape):
        """
        Get color of a TDF_Label object:
        - if self.use_color is False, return DEFAULT_COLOR, else analyse colors
        - if self.analyse_faces, get all colors of all faces. if all faces have the same color, return it, else return the shape color
        Note: This is BEST EFFORT only. Jupyter-CadQuery does not support different colors for the faces of a solid/compound.
              So for many STEP files with colored faces, the result will not be correct and depend on the structure of the STEP labels
        :param label: TDF_label or TopoDS_Shape of a STEP file
        :return: str
        """

        def to_list(c):
            return (c.GetRGB().Red(), c.GetRGB().Green(), c.GetRGB().Blue(), c.Alpha())

        def get_col(obj):
            col = Quantity_ColorRGBA()
            if (
                self.color_tool.GetColor(obj, XCAFDoc_ColorGen, col)
                or self.color_tool.GetColor(obj, XCAFDoc_ColorSurf, col)
                or self.color_tool.GetColor(obj, XCAFDoc_ColorCurv, col)
            ):
                return to_list(col)

        if not self.use_colors:
            return DEFAULT_COLOR

        shape_color = get_col(shape)

        colors = []
        if self.analyse_faces:

            # Find all face colors
            exp = TopExp_Explorer(shape, TopAbs_FACE)
            while exp.More():
                color = get_col(exp.Current())
                if color is not None:
                    colors.append(color)
                exp.Next()

            colors = list(set(colors))

        # If all faces have the same color, use this as shape color
        if len(colors) == 1:
            return colors[0]
        else:
            return DEFAULT_COLOR if shape_color is None else shape_color

    def get_location(self, label):
        """
        Get location of a TDF_Label object
        :param label: TDF_label of a STEP file
        :return: TopLoc_Location
        """
        return self.shape_tool.GetLocation_s(label)

    def get_shape(self, label):
        """
        Get shape of a TDF_Label object
        :param label: TDF_label of a STEP file
        :return: TopoDS_Shape
        """
        return self.shape_tool.GetShape_s(label)

    def get_shape_details(self, label, name, loc):
        """
        Get shape details of a TopAbs_COMPOUND or TopAbs_COMPSOLID
        :param label: TDF_label of a STEP file
        :param name: object name
        :param loc: object location (TopLoc_Location)
        :return: list of TopAbs_SOLID
        """
        it = TDF_ChildIterator()
        it.Initialize(label)
        i = 0
        shapes = []
        while it.More():
            shape = self.get_shape(it.Value())
            if shape.ShapeType() == TopAbs_SOLID:
                s_name = f"{name}_{i+1}"
                color = self.get_color(shape)
                sub_shape = self._create_assembly_object(s_name, loc, color, shape)
                shapes.append(sub_shape)
                i += 1

            elif shape.ShapeType == TopAbs_COMPSOLID:
                warn(f"Nested compsolids not supported yet: {name}")

            it.Next()

        return shapes

    def get_subshapes(self, label=None, loc=None):
        """
        Get sub shapes of STEP assemblies
        :param label: TDF_label of a STEP file
        :param loc: object location (TopLoc_Location)
        :return: list of AssemblyObjects
        """
        labels = TDF_LabelSequence()
        if label is None:
            # Get all non referenced top level labels
            self.shape_tool.GetFreeShapes(labels)
        else:
            # get all sub-components of the label
            self.shape_tool.GetComponents_s(label, labels)

        result = []

        for i in range(labels.Length()):
            sub_label = labels.Value(i + 1)

            if self.shape_tool.IsReference_s(sub_label):
                ref_label = TDF_Label()
                self.shape_tool.GetReferredShape_s(sub_label, ref_label)
            else:
                ref_label = sub_label

            is_assembly = self.shape_tool.IsAssembly_s(ref_label)

            # Get location from the sub_label and everything else from the referenced label
            loc = self.get_location(sub_label)
            name = self.get_name(ref_label)
            shape = self.get_shape(ref_label)

            sub_shape = self._create_assembly_object(name, loc)

            if is_assembly:
                sub_shape["shapes"] = self.get_subshapes(ref_label)

            elif (
                self.split_compounds
                and shape.ShapeType() in [TopAbs_COMPOUND, TopAbs_COMPSOLID]
                and ref_label.HasChild()
            ):
                sub_shapes = self.get_shape_details(ref_label, name, TopLoc_Location())
                if len(sub_shapes) == 0:
                    sub_shape["shape"] = shape
                    sub_shape["color"] = self.get_color(shape)
                else:
                    sub_shape["shapes"] = sub_shapes

            else:
                sub_shape["shape"] = shape
                sub_shape["color"] = self.get_color(shape)

            result.append(sub_shape)

        return result

    def load(self, filename, cache_name=None, clear_cache=False):
        """
        Load a STEP file
        The result will be stores as a list of AssemblyObjects in self.assemblies and
        for faster reload saved in a pickle format with binary BRep buffers
        :param filename: name of the STEP file
        :param cache_name: name of the binary cache object
        :param clear_cache: clear cache before loading to force analysis of STEP file
        """
        start = time.time()
        if cache_name is not None:
            cache_filename = f"{cache_name}.jq"
            if os.path.exists(cache_filename):
                if clear_cache:
                    os.unlink(cache_filename)
                    print("Cache cleared")
                else:
                    print("Loading from cache ... ", flush=True, end="")
                    self.load_assembly(cache_filename)
                    print("done")
                    print(f"duration: {time.time() - start:5.1f} s")
                    return

        if not os.path.exists(filename):
            raise FileNotFoundError(filename)

        print("Reading STEP file ... ", flush=True, end="")
        time.sleep(0.01)  # ensure output is shown

        fmt = TCollection_ExtendedString("CadQuery-XCAF")
        doc = TDocStd_Document(fmt)

        self.shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        self.color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

        reader = STEPCAFControl_Reader()
        reader.SetNameMode(True)
        reader.SetColorMode(True)
        reader.SetLayerMode(True)

        reader.ReadFile(filename)
        reader.Transfer(doc)

        print("parsing Assembly ... ", flush=True, end="")

        self.assemblies = self.get_subshapes()

        print("done")
        print(f"duration: {time.time() - start:5.1f} s")

        if cache_name is not None:
            print("Saving to cache ... ", flush=True, end="")
            self.save_assembly(cache_filename)
            print("done")

    def to_build123d(self):
        """
        Convert internal AssemblyObjects format to build123d Assemblies
        :return: buiild123d assembly
        """

        def walk(objs, label=None, loc=None):
            a = []
            names = {}
            for obj in objs:
                label = obj["name"]

                # Create a unique name by postfixing the enumerator index if needed
                if names.get(label) is None:
                    names[label] = 0
                else:
                    names[label] += 1
                label = f"{obj['name']}_{names[label]}"

                a.append(
                    reference(
                        Compound(obj["shape"])
                        if obj["shapes"] is None
                        else walk(obj["shapes"]),
                        label=label,
                        color=None if obj["color"] is None else Color(*obj["color"]),
                        location=Location(obj.get("loc")),
                    )
                )
            return Assembly(label=label, children=a, location=loc)

        if len(self.assemblies) == 0 or (
            self.assemblies[0]["shapes"] is not None
            and len(self.assemblies[0]["shapes"]) == 0
        ):
            raise ValueError("Empty assembly list")

        if len(self.assemblies) == 1:
            assembly = self.assemblies[0]
            return walk(assembly["shapes"], assembly["name"], Location(assembly["loc"]))
        else:
            children = []
            for assembly in self.assemblies:
                children.append(
                    walk(
                        assembly["shapes"],
                        assembly["name"],
                        Location(assembly["loc"]),
                    )
                )
            result = Assembly(label="Group", children=children)

        return result


# %%

sr = StepReader()
sr.load("examples/assembly/RC_Buggy_2_front_suspension.stp")

# %%

a = sr.to_build123d()
show(a, up="Y", parallel=True)
# %%
