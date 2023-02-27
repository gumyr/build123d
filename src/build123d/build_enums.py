"""
build123d ENUMs

name: build_enums.py
by:   Gumyr
date: Oct 11th 2022

desc:
    A collection of enums used throughout build123d.

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
from __future__ import annotations
from enum import Enum, auto


class Align(Enum):
    """Align object about Axis"""

    MIN = auto()
    CENTER = auto()
    MAX = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class ApproxOption(Enum):
    """DXF export spline approximation strategy"""

    ARC = auto()
    NONE = auto()
    SPLINE = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class AngularDirection(Enum):
    """Angular rotation direction"""

    CLOCKWISE = auto()
    COUNTER_CLOCKWISE = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class CenterOf(Enum):
    """Center Options"""

    GEOMETRY = auto()
    MASS = auto()
    BOUNDING_BOX = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class FrameMethod(Enum):
    """Moving frame calculation method"""

    FRENET = auto()
    CORRECTED = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class GeomType(Enum):
    """CAD geometry object type"""

    PLANE = auto()
    CYLINDER = auto()
    CONE = auto()
    SPHERE = auto()
    TORUS = auto()
    BEZIER = auto()
    BSPLINE = auto()
    REVOLUTION = auto()
    EXTRUSION = auto()
    OFFSET = auto()
    LINE = auto()
    CIRCLE = auto()
    ELLIPSE = auto()
    HYPERBOLA = auto()
    PARABOLA = auto()
    OTHER = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Keep(Enum):
    """Split options"""

    TOP = auto()
    BOTTOM = auto()
    BOTH = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Kind(Enum):
    """Offset corner transition"""

    ARC = auto()
    INTERSECTION = auto()
    TANGENT = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Mode(Enum):
    """Combination Mode"""

    ADD = auto()
    SUBTRACT = auto()
    INTERSECT = auto()
    REPLACE = auto()
    PRIVATE = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class FontStyle(Enum):
    """Text Font Styles"""

    REGULAR = auto()
    BOLD = auto()
    ITALIC = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class LengthMode(Enum):
    """Method of specifying length along PolarLine"""

    DIAGONAL = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class PositionMode(Enum):
    """Position along curve mode"""

    LENGTH = auto()
    PARAMETER = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Select(Enum):
    """Selector scope - all or last operation"""

    ALL = auto()
    LAST = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class SortBy(Enum):
    """Sorting criteria"""

    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Transition(Enum):
    """Sweep discontinuity handling option"""

    RIGHT = auto()
    ROUND = auto()
    TRANSFORMED = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


class Until(Enum):
    """Extrude limit"""

    NEXT = auto()
    LAST = auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"
