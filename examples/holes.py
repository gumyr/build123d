"""

name: holes.py
by:   Gumyr
date: September 26th 2022

desc:

    This example demonstrates multiple hole types.

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

from build123d import *
from ocp_vscode import show_object

# Simple through hole
with BuildPart() as thru_hole:
    Cylinder(radius=3, height=2)
    Hole(radius=1)

# Recessed counter bore hole (hole location @ (0,0,0))
with BuildPart() as recessed_counter_bore:
    with Locations((10, 0)):
        Cylinder(radius=3, height=2)
        CounterBoreHole(radius=1, counter_bore_radius=1.5, counter_bore_depth=0.5)

# Recessed counter sink hole (hole location @ (0,0,0))
with BuildPart() as recessed_counter_sink:
    with Locations((0, 10)):
        Cylinder(radius=3, height=2)
        CounterSinkHole(radius=1, counter_sink_radius=1.5)

# Flush counter sink hole (hole location @ (0,0,2))
with BuildPart() as flush_counter_sink:
    with Locations((10, 10)):
        Cylinder(radius=3, height=2)
        with Locations(
            (0, 0, flush_counter_sink.part.faces().sort_by(Axis.Z)[-1].center().Z)
        ):
            CounterSinkHole(radius=1, counter_sink_radius=1.5)

show_object(thru_hole.part.wrapped, name="though hole")
show_object(recessed_counter_bore.part.wrapped, name="recessed counter bore")
show_object(recessed_counter_sink.part.wrapped, name="recessed counter sink")
show_object(flush_counter_sink.part.wrapped, name="flush counter sink")
