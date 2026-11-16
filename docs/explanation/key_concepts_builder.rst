.. _how_builder_mode_works:

######################
How builder mode works
######################

In builder mode a model is made inside ``with`` blocks, and each object
adds itself to the model as it is created. :ref:`builder_and_algebra`
introduces the two modes and compares them.

This page explains what is going on in builder mode: what a builder is,
how an object knows which builder it belongs to, and when things are
combined and placed. Knowing this explains the handful of surprises that
builder mode has in store.

***************************************
A builder is a tool, not the object
***************************************

A builder works like adding up a column of figures. It keeps a running
total, the model so far, and every object and operation written inside its
block changes that total. When the block ends, the total is the result.

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [tool]
    :end-before: [tool]

There are four builders, one for each kind of thing that can be built:

.. list-table::
    :header-rows: 1
    :widths: 25 35 40

    * - Builder
      - Builds
      - Result
    * - ``BuildLine``
      - lines and curves
      - ``.line``, a ``Curve``
    * - ``BuildSketch``
      - flat shapes
      - ``.sketch``, a ``Sketch``
    * - ``BuildPart``
      - solids
      - ``.part``, a ``Part``
    * - ``BuildSheet``
      - sheet metal
      - ``.sheet``, a ``Shell``

``example`` above is the builder. The part it built is ``example.part``.
It is the part, not the builder, that is exported, measured or put in an
assembly. :ref:`key_concepts` describes ``Part``, ``Sketch`` and ``Curve``.

******************************
Objects find their builder
******************************

Nothing in ``Box(10, 10, 10)`` says which builder the box is for. An object
or an operation looks for the builder whose block it was written in, and
acts on that one:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [scope]
    :end-before: [scope]

This is what keeps builder code short. It also has a consequence that
catches everyone once: **an object is added to its builder at the moment it
is created**, not when the line finishes and not when the block ends.

.. _builder_objects_combine_at_once:

Changing an object after it is made
===================================

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [moved_wrong]
    :end-before: [moved_wrong]

This does not move the cylinder. The line does three things, in this
order:

#. ``Cylinder(1, 2)`` creates the cylinder.
#. The cylinder adds itself to the ``BuildPart`` at once, at the origin.
#. ``.moved(...)`` is applied to the Python object that ``Cylinder``
   returned, and makes a moved copy of it.

By the time the third step runs, the cylinder is already in the part.
Nothing keeps the moved copy, so it is thrown away, and the part never sees
it.

A builder is a Python *context manager*, the same thing as the ``with
open(...)`` block used to write a file, and the same mistake can be made
there:

.. literalinclude:: /explanation/builder_mode.py
    :language: python
    :start-after: [file_analogy]
    :end-before: [file_analogy]
    :dedent:

``f.write("text")`` writes the text to the file and returns 4, the number
of characters written. ``.to_bytes(1, "big")`` is then called on that 4 and
produces ``b"\x04"``, which is discarded. The file still holds only
``text``: the second operation happened after the write, to what the write
returned, and has nothing to do with the file.

Builder mode behaves the same way. Once an object has been added to its
builder, changing the Python object that was returned does not change what
was added.

So in builder mode, where an object goes has to be said before the object
is made. That is what ``Locations`` is for:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [moved_right]
    :end-before: [moved_right]

Using algebra inside a builder
==============================

The same thing happens, less obviously, when the algebra operators are used
inside a builder:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [algebra_wrong]
    :end-before: [algebra_wrong]

This looks like a ring. The variable ``ring`` is a ring. But each ``Circle``
added itself to the sketch as it was created, so the sketch holds both
circles joined together: a solid disc. The subtraction was done on the side,
and its result was never given to the builder.

Objects are combined with their builder as soon as they are created,
unless they are made with ``mode=Mode.PRIVATE``. A private object is made
and returned, and the builder is not told. Algebra inside a builder
therefore works when its ingredients are private and the finished result is
handed over with ``insert``:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [algebra_private]
    :end-before: [algebra_private]

Usually it is simpler to let the builder do the combining, which is what
the modes are for:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [algebra_builder]
    :end-before: [algebra_builder]

*********
Modes
*********

Every object and almost every operation has a ``mode``, which says how it
is combined with the running total:

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Mode
      - Effect on the model so far
    * - ``Mode.ADD``
      - the new object is joined to it. This is the usual default.
    * - ``Mode.SUBTRACT``
      - the new object is cut out of it
    * - ``Mode.INTERSECT``
      - only what the two have in common is kept
    * - ``Mode.REPLACE``
      - the new object takes its place
    * - ``Mode.PRIVATE``
      - nothing. The object is made and returned, and the model is left
        alone.

On the column of figures, ``ADD`` and ``SUBTRACT`` are the plus and minus
signs.

The default is not always ``ADD``. A ``Hole`` exists to remove material and
defaults to ``SUBTRACT``. Operations that reshape what is there, such as
``fillet`` and ``offset``, replace it.

Builders have modes too
=======================

A builder is given a ``mode`` in the same way, and it says how the
builder's *finished* result is combined with the builder it is nested in.
Everything inside the inner block is built first, on its own, and the whole
of it is then added, subtracted or intersected in one step.

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [builder_mode_sketch]
    :end-before: [builder_mode_sketch]

The window is a rectangle joined to a circle. It is built as one shape, and
that shape is then cut from the plate. Written as two separate objects with
``Mode.SUBTRACT`` the result here would be the same, but a nested builder
can hold any amount of construction, fillets, mirrors and all, and still
combine as a single thing.

It works the same way for parts:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [builder_mode_part]
    :end-before: [builder_mode_part]

The plug, a cone on a peg, is built whole and then subtracted from the
block to leave a cavity. Afterwards ``plug.part`` still holds the plug.

``Mode.PRIVATE`` on a builder keeps its result out of the parent
altogether, which is how a sketch can be made inside a part purely to
measure or select from:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [builder_mode_private]
    :end-before: [builder_mode_private]

*********************************
Built locally, placed on exit
*********************************

A builder can be given one or more *placements*, planes, faces or
locations, as its first arguments. They say where the finished result is
to go.

They do not change where things are drawn. Every builder constructs in its
own coordinates, as if on ``Plane.XY`` at the origin, and the placement is
applied once, to the completed result, when the block ends. Inside the
block, positions and selections are in the builder's own coordinates.

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [placement]
    :end-before: [placement]

Both versions are kept: ``sketch`` and ``sketch_local``, and likewise
``part`` and ``part_local``, ``line`` and ``line_local``, ``sheet`` and
``sheet_local``.

Given several placements, the result is put on all of them. Here one
rectangle is drawn once and lands on each of the six faces of a box:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [six_faces]
    :end-before: [six_faces]

.. image:: /explanation/assets/key_concepts_builder/boxes_on_faces.svg
    :align: center

A builder does not inherit a placement from the builder it is nested in.
The sketch above is drawn flat, whatever the part round it is doing.
``BuildLine`` takes a single placement; the others take any number.

.. _location_context_link:

Locations inside a builder, and round one
=========================================

``Locations`` and the pattern contexts, ``GridLocations``,
``PolarLocations`` and ``HexLocations``, make a set of places active for
everything in their block. Inside a builder, each object is made once at
every active place:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [locations_inside]
    :end-before: [locations_inside]

Two boxes, two cylinders, and a grid of four spheres at each of the two
places. Contexts nest, and an inner one is measured from each place of the
outer one.

Put *round* a builder, the same contexts act on the builder's finished
result, exactly as a placement does:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [locations_around]
    :end-before: [locations_around]

The circle is drawn once: ``holes.sketch_local`` has one face. It is placed
twice: ``holes.sketch`` has two, and ``extrude`` makes two posts. The same
goes for a whole part:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [locations_part]
    :end-before: [locations_part]

A builder made inside a function is the exception. It is not part of the
build that called the function, so it is not added to that build when it
ends, and the caller's active locations are not applied to it. It is
returned like any object, and the caller places it, usually with
``insert``:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [function]
    :end-before: [function]

Each call returns a builder holding a row of boxes, and ``insert`` puts
that row at the active location: three rows of one, two and three boxes.

*******************
Pending objects
*******************

When a builder inside another builder finishes, its result has to go
somewhere. A sketch finished inside a ``BuildPart`` is not a solid and
cannot be added to the part. It is handed to the part to hold, as a
*pending* face, until an operation comes along that wants one:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [pending]
    :end-before: [pending]

``extrude`` was given no sketch. It took the pending one, and used it up.
``loft`` and ``revolve`` take pending faces in the same way, ``sweep``
takes a pending face and a pending line, and ``make_face`` in a sketch
takes the pending lines of a ``BuildLine``.

This is why a builder-mode model reads as a sequence of sketch, operation,
sketch, operation, with nothing passed between them. :ref:`building_parts`
shows how to take control of it when the automatic choice is not the one
wanted.

***********************
When the block ends
***********************

When its block ends, a builder finalises its result and, if it is nested,
hands it to its parent. Anything about the result that is set on the
*builder* has to be set before then. A builder's ``label``, ``color`` and
``material`` are applied to the result as the block closes:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [exit]
    :end-before: [exit]

Changing the builder afterwards does nothing to a part that is already
made. Change the part:

.. literalinclude:: /explanation/builder_mode.py
    :language: build123d
    :start-after: [exit_late]
    :end-before: [exit_late]

************
See also
************

* :ref:`building_parts`, :ref:`sketching` and
  :ref:`drawing_lines_and_curves` are the guides to using each builder.
* :ref:`moving_objects` covers locations and rotations.
* :ref:`tutorial_sketch_then_extrude` starts the tutorials, which build
  every model in both modes side by side.
