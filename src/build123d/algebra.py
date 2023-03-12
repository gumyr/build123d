import copy
from typing import Any, List, Union
from build123d.build_enums import *
from build123d.topology import Location, Wire, Plane, Vertex, Vector


class SkipClean:
    """Skip clean context for use in operator driven code where clean=False wouldn't work"""

    clean = True

    def __enter__(self):
        SkipClean.clean = False

    def __exit__(self, exception_type, exception_value, traceback):
        SkipClean.clean = True


def listify(arg: Any) -> List:
    if isinstance(arg, (tuple, list)):
        return list(arg)
    else:
        return [arg]


def is_algcompound(object):
    return hasattr(object, "wrapped") and hasattr(object, "_dim")


class Pos(Location):
    def __init__(self, x: Union[float, Vertex, Vector] = 0, y: float = 0, z: float = 0):
        if isinstance(x, (Vertex, Vector)):
            super().__init__(x.to_tuple())
        else:
            super().__init__((x, y, z))


class Rot(Location):
    def __init__(self, x: float = 0, y: float = 0, z: float = 0):
        super().__init__((0, 0, 0), (x, y, z))


class AlgebraMixin:
    def _place(self, mode: Mode, *objs: Any):
        # TODO error handling for non algcompound objects

        objs = [o for o in objs if is_algcompound(o)]
        if len(objs) == 0:
            raise RuntimeError("No Algebra compound received")

        if not (objs[0]._dim == 0 or self._dim == 0 or self._dim == objs[0]._dim):
            raise RuntimeError(
                f"Cannot combine objects of different dimensionality: {self._dim} and {objs[0]._dim}"
            )

        if self._dim == 0:  # Cover addition of empty BuildPart with another object
            if mode == Mode.ADD:
                if len(objs) == 1:
                    compound = copy.deepcopy(objs[0])
                else:
                    compound = copy.deepcopy(objs.pop()).fuse(*objs)
            else:
                raise RuntimeError("Can only add to an empty BuildPart object")
        elif objs[0]._dim == 0:  # Cover operation with empty BuildPart object
            compound = self
        else:
            if mode == Mode.ADD:
                compound = self.fuse(*objs)

            elif self._dim == 1:
                raise RuntimeError("Lines can only be added")

            else:
                if mode == Mode.SUBTRACT:
                    compound = self.cut(*objs)
                elif mode == Mode.INTERSECT:
                    compound = self.intersect(*objs)

        if SkipClean.clean:
            compound = compound.clean()

        compound._dim = self._dim

        return compound

    # TODO: How to use typing here
    def __add__(self, other: Union[Any, List[Any]]):
        return self._place(Mode.ADD, *listify(other))

    # TODO: How to use typing here
    def __sub__(self, other: Union[Any, List[Any]]):
        return self._place(Mode.SUBTRACT, *listify(other))

    # TODO: How to use typing here
    def __and__(self, other: Union[Any, List[Any]]):
        return self._place(Mode.INTERSECT, *listify(other))

    def __mul__(self, loc: Location):
        if self._dim == 3:
            return copy.copy(self).move(loc)
        else:
            return self.moved(loc)

    def __matmul__(self, obj: Union[float, Location, Plane]):
        if isinstance(obj, (int, float)):
            if self._dim == 1:
                return Wire.make_wire(self.edges()).position_at(obj)
            else:
                raise TypeError("Only lines can access positions")

        elif isinstance(obj, Location):
            loc = obj

        elif isinstance(obj, Plane):
            loc = obj.to_location()

        else:
            raise ValueError(f"Cannot multiply with {obj}")

        if self._dim == 3:
            return copy.copy(self).locate(loc)
        else:
            return self.located(loc)

    def __mod__(self, position):
        if self._dim == 1:
            return Wire.make_wire(self.edges()).tangent_at(position)
        else:
            raise TypeError(f"unsupported operand type(s)")
