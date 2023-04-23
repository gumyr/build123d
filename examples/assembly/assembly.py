import copy
import anytree
from build123d import *


def reference(obj, label=None, color=None, location=None):
    new_obj = copy.copy(obj)
    if label is not None:
        new_obj.label = label
    if color is not None:
        new_obj.color = color
    if location is None:
        return new_obj
    else:
        return new_obj.move(location)


class Assembly(Compound):
    def __init__(self, label, children, location=None):
        super().__init__(label=label, children=children)
        # The assembly layer will not contain a part, it only needs a location
        self.location = Location() if location is None else location
        self.resolver = anytree.Resolver("label")

    def find_object(self, path):
        name, _, rest = path.strip("/").partition("/")
        if name != self.label:
            raise ValueError(f"Path '{path}' not valid")
        elif rest == "":
            return self

        return self.resolver.get(self, rest)

    def joint_location(self, obj, joint, **kwargs):
        if isinstance(joint, RevoluteJoint):
            loc = obj.location * joint.relative_axis.to_location()
        elif isinstance(joint, RigidJoint):
            loc = obj.location * joint.relative_location
        else:
            raise NotImplementedError()

        if kwargs.get("angle") is not None:
            loc = loc * Rot(0, 0, kwargs["angle"])

        return loc

    def assemble(
        self, path, joint_name, to_path, to_joint_name, animate=False, **kwargs
    ):
        def _relocate(obj, loc):
            if not isinstance(obj, Assembly):
                obj.location = loc.inverse() * obj.location
            for child in obj.children:
                _relocate(child, loc)

        obj = self.find_object(path)
        joint = obj.joints[joint_name]
        loc = self.joint_location(obj, joint, **kwargs)

        to_obj = self.find_object(to_path)
        to_joint = to_obj.joints[to_joint_name]
        to_loc = self.joint_location(to_obj, to_joint, **kwargs)

        if kwargs.get("angle") is not None:
            to_loc = to_loc * Rot(0, 0, kwargs["angle"])

        if animate:
            # relocate to ensure that the joint is used as origin for the animation
            _relocate(obj, loc)

            # Get the parent Assembly layer
            parent_path, _, _ = path.rpartition("/")

            # For sub assemblies, the location gets pushed one level up to the assembly layer
            parent_obj = self.find_object(parent_path)
            parent_obj.location = to_loc
        else:
            # else just use connect_to for flat assemblies
            to_joint.connect_to(joint, **kwargs)
