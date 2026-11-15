"""
Assemblies documentation examples

name: assemblies.py
by:   Gumyr
date: November 15th 2026

desc:
    Every tested code example of the "Assemblies" how-to guide lives
    here, between pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``. It draws no pictures.

license:

    Copyright 2026 Gumyr

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

# pylint: disable=redefined-outer-name, wildcard-import, unused-wildcard-import

import copy

from build123d import *

# ---------------------------------------------------------------------------
# label the parts and group them
# ---------------------------------------------------------------------------

# [group]
base = Box(60, 40, 10)
base.label = "base"

lid = Pos(0, 0, 15) * Box(60, 40, 5)
lid.label = "lid"

enclosure = Compound(label="enclosure", children=[base, lid])
# [group]

assert [child.label for child in enclosure.children] == ["base", "lid"]
assert base.parent is enclosure and enclosure.is_root

# [tree]
print(enclosure.show_topology())
# [tree]

# ---------------------------------------------------------------------------
# many copies of one part
# ---------------------------------------------------------------------------

# [copies]
post = Cylinder(3, 7.5)
post.label = "post"

corners = [Pos(x, y, 8.75) for x in (-25, 25) for y in (-15, 15)]
posts = [copy.copy(post).locate(corner) for corner in corners]
# [copies]

# shallow copies share one piece of geometry; a deep copy has its own
assert all(one.wrapped.IsPartner(post.wrapped) for one in posts)
assert not copy.deepcopy(post).wrapped.IsPartner(post.wrapped)

# ---------------------------------------------------------------------------
# add and remove parts
# ---------------------------------------------------------------------------

# [add]
for one in posts:
    one.parent = enclosure
# [add]

assert len(enclosure.children) == 6

# [remove]
lid.parent = None
# [remove]

assert len(enclosure.children) == 5 and lid.is_root

# [replace]
enclosure.children = [*enclosure.children, lid]
# [replace]

assert len(enclosure.children) == 6 and lid.parent is enclosure

# ---------------------------------------------------------------------------
# move the assembly, and find where a part is
# ---------------------------------------------------------------------------

# [locations]
enclosure.location = Location((100, 0, 0))

lid.location.position  # (0, 0, 15): where the lid is in the enclosure
lid.global_location.position  # (100, 0, 15): where it is in the world
# [locations]

assert (lid.location.position - Vector(0, 0, 15)).length < 1e-9
assert (lid.global_location.position - Vector(100, 0, 15)).length < 1e-9

# [moved]
second = Pos(0, 60, 0) * enclosure
# [moved]

# a moved copy of the whole tree; the original is where it was
assert len(second.children) == 6 and second.label == "enclosure"
assert (second.children[0].global_location.position - Vector(100, 60, 0)).length < 1e-9
assert (base.global_location.position - Vector(100, 0, 0)).length < 1e-9

# ---------------------------------------------------------------------------
# walk the tree
# ---------------------------------------------------------------------------

# [walk]
for part in enclosure.children:
    print(part.label, part.global_location.position)

lid.parent  # the enclosure
lid.root  # the top of the tree, also the enclosure here
lid.siblings  # the base and the four posts
enclosure.leaves  # every part that has no children of its own
# [walk]

assert lid.root is enclosure and len(lid.siblings) == 5 and len(enclosure.leaves) == 6

# ---------------------------------------------------------------------------
# measure the whole assembly
# ---------------------------------------------------------------------------

# [measure]
solids = enclosure.solids()  # every solid, however deeply it is nested
total_volume = sum(solid.volume for solid in solids)
size = enclosure.bounding_box().size
# [measure]

assert len(solids) == 6
assert abs(total_volume - (60 * 40 * 10 + 60 * 40 * 5 + 4 * post.volume)) < 1e-6
assert (size - Vector(60, 40, 22.5)).length < 1e-6

# ---------------------------------------------------------------------------
# check for parts that run into each other
# ---------------------------------------------------------------------------

# [interference]
clash, parts, volume = enclosure.do_children_intersect()
# [interference]

# the posts stand between the base and the lid and touch both, which is not a clash
assert not clash

# [interference_found]
too_long = copy.copy(post).locate(Pos(0, 0, 6))
too_long.label = "post that is too low"
too_long.parent = enclosure

clash, parts, volume = enclosure.do_children_intersect()
# clash is True, parts are the base and the post, volume is what they share
# [interference_found]

assert clash and {part.label for part in parts} == {"base", "post that is too low"}
assert volume > 0
too_long.parent = None
