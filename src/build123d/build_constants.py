"""
build123d Constants

name: build_constants.py
by:   Gumyr
date: April 9th, 2026

desc:
    This is a Python code defining a class hierarchy for building CAD
    models. The code defines an abstract base class Builder with three
    concrete subclasses BuildLine, BuildPart, and BuildSketch in separate
    modules.

    The Builder class has several methods for adding and retrieving
    geometric shapes such as vertices, edges, faces, and solids. It also
    has a method _add_to_pending for adding shapes to a pending list that
    will be integrated into the final model later. The class has a
    _get_context method for retrieving the current Builder instance and a
    validate_inputs method for validating input shapes.

    The code also defines a validate_inputs function that takes a Builder
    instance and validates the input shapes.

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

from build123d.build_enums import Unit

#
# CONSTANTS
#

# LENGTH CONSTANTS
MC = 0.001
MM = 1
CM = 10 * MM
M = 1000 * MM
IN = 25.4 * MM
FT = 12 * IN
THOU = IN / 1000

# UNIT CONVERSIONS
UNITS_PER_METER = {
    Unit.IN: M / IN,
    Unit.FT: M / FT,
    Unit.MC: M / MC,
    Unit.MM: M / MM,
    Unit.CM: M / CM,
    Unit.M: 1,
}

# MASS CONSTANTS
G = 1
KG = 1000 * G
G_PER_LB = 453.59237
LB = G_PER_LB * G

# UNIT CONVERSIONS
UNITS_PER_KILOGRAM = {
    Unit.G: KG / G,
    Unit.KG: 1,
    Unit.LB: KG / LB,
}
