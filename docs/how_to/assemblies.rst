.. _assembly:

##########
Assemblies
##########

Most designs are more than one part. An assembly gathers the parts into a
tree, so that they can be named, moved, inspected and exported as one thing
while each stays a part in its own right.

In build123d an assembly is a :class:`~topology.Compound` with children.
Every shape can have a ``label``, a ``parent`` and ``children``, and the tree
is made by setting them. This guide shows how to build one and work with it.
Assemblies are made from finished parts, so everything here is the same
whichever mode the parts were built in.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - name a part
      - ``part.label = "..."``
    * - group parts into an assembly
      - ``Compound(label=..., children=[...])``
    * - see the tree
      - ``assembly.show_topology()``
    * - use one part many times
      - ``copy.copy(part)``
    * - add or remove a part
      - ``part.parent = ...``, ``assembly.children = ...``
    * - move the assembly, or find where a part is
      - ``location``, ``global_location``
    * - visit the parts
      - ``children``, ``descendants``, ``leaves``
    * - measure the whole assembly
      - ``solids()``, ``bounding_box()``
    * - check for parts that collide
      - ``do_children_intersect()``
    * - position parts against each other
      - see :ref:`joints`

The examples build a small enclosure: a base, a lid, and four posts between
them. :ref:`joint_tutorial` assembles a hinged box with its hinge and screws
in the same way.

*********************************
Name the parts and group them
*********************************

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [group]
    :end-before: [group]

A ``label`` is any string, and labels do not have to be unique. The
assembly is a ``Compound`` given its own label and its ``children``. Each
child's ``parent`` is set for it, and the tree is in place.

A shape has one parent. Putting a part into a second assembly takes it out
of the first, so use a copy when the same part belongs in two places.

****************
See the tree
****************

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [tree]
    :end-before: [tree]

.. code-block:: text

    enclosure Compound at 0x105e79910, Location((0, 0, 0), (0, 0, 0))
    ├── base  Box      at 0x105e798e0, Location((0, 0, 0), (0, 0, 0))
    └── lid   Box      at 0x11c04dd30, Location((0, 0, 15), (0, 0, 0))

:meth:`~topology.Shape.show_topology` gives each node's label, type and
location. The location is the node's own, relative to its parent.

.. _shallow_copy:

***************************
Use one part many times
***************************

An assembly often holds many copies of one part: screws, posts, feet. Make
them with ``copy.copy``.

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [copies]
    :end-before: [copies]

``copy.copy`` makes a new shape that shares the geometry of the original,
so each post costs almost nothing, and ``locate`` puts each at its own
place. ``copy.deepcopy`` duplicates the geometry too, and is for a copy
that is going to be changed into something different.

The difference shows when the assembly is saved. Consider this example where 100 screws are added to an assembly:

.. image:: /how_to/assets/assemblies/reference_assembly.svg
    :align: center

.. code::

    screw = import_step("M6-1x12-countersunk-screw.step")
    locs = HexLocations(6, 10, 10).local_locations

    screw_copies = [copy.deepcopy(screw).locate(loc) for loc in locs]
    copy_assembly = Compound(children=screw_copies)
    export_step(copy_assembly, "copy_assembly.step")

which takes about 5 seconds to run (on an older computer) and produces
a file of size 51938 KB. However, if a shallow copy is used instead:

.. code::

    screw = import_step("M6-1x12-countersunk-screw.step")
    locs = HexLocations(6, 10, 10).local_locations

    screw_references = [copy.copy(screw).locate(loc) for loc in locs]
    reference_assembly = Compound(children=screw_references)
    export_step(reference_assembly, "reference_assembly.step")

this takes about ¼ second and produces a file of size 550 KB - just over
1% of the size of the ``deepcopy()`` version and only 12% larger than the
screw's step file.

Using ``copy.copy()`` to create references to the original CAD object
for assemblies can substantially reduce the time and resources used
to create and store that assembly.

************************
Add and remove parts
************************

Setting a part's ``parent`` adds it to that assembly:

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [add]
    :end-before: [add]

and setting it to ``None`` takes it out again:

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [remove]
    :end-before: [remove]

The ``children`` of an assembly can be read as a tuple and assigned as a
whole, which is the way to add several parts at once or to reorder them. It
cannot be appended to in place:

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [replace]
    :end-before: [replace]

.. _assembly_locations:

***********************************************
Move the assembly, and find where a part is
***********************************************

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [locations]
    :end-before: [locations]

Each shape's :attr:`~topology.Shape.location` is relative to its parent.
Moving the enclosure therefore moves everything in it, and the lid's own
location does not change. :attr:`~topology.Shape.global_location` adds up
the locations from the top of the tree down and gives the part's place in
the world.

An assembly can also be moved like any shape, which gives a moved copy of
the whole tree and leaves the original where it was:

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [moved]
    :end-before: [moved]

*******************
Visit the parts
*******************

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [walk]
    :end-before: [walk]

The tree comes from the `anytree <https://anytree.readthedocs.io/en/latest/>`_
package, which gives every shape these attributes:

* ``parent`` - the node above; setting it moves the node to a new parent.
* ``children`` - a tuple of the nodes directly below.
* ``ancestors`` - the parent, its parent, and so on up.
* ``descendants`` - every node below, at any depth.
* ``root`` - the top of the tree.
* ``siblings`` - the other nodes with the same parent.
* ``leaves`` - every node below that has no children.
* ``is_leaf``, ``is_root`` - whether the node is at the bottom or the top.
* ``depth`` - how many steps the node is from the root.
* ``height`` - how many steps it is from its furthest leaf.
* ``path`` - the nodes from the root down to this one.

******************************
Measure the whole assembly
******************************

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [measure]
    :end-before: [measure]

The selectors of an assembly reach all the way down the tree, so
``solids()`` gives every solid in every sub-assembly, and a total is a sum
over them. ``bounding_box()`` covers the whole assembly.

********************************
Check for parts that collide
********************************

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [interference]
    :end-before: [interference]

:meth:`~topology.Compound.do_children_intersect` compares the parts of an
assembly with one another, where they stand, and reports the first pair
that share a volume. It returns three things: whether there is a clash,
the two parts, and the volume they have in common. The posts here touch
the base and the lid without entering them, and that is not a clash.

A post placed too low is caught:

.. literalinclude:: /how_to/assemblies.py
    :language: build123d
    :start-after: [interference_found]
    :end-before: [interference_found]

************
See also
************

* :ref:`joints` position parts against one another before they go into an
  assembly.
* :ref:`joint_tutorial` builds and assembles a hinged box step by step.
* :ref:`moving_objects` covers locations and rotations.
* :ref:`import_export` covers saving an assembly as STEP, where
  shared copies are saved once.
