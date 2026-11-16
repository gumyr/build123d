.. _how_algebra_mode_works:
.. _key_concepts_algebra:

######################
How algebra mode works
######################

In algebra mode a model is made by combining shapes with operators, in the
way numbers are combined in arithmetic. :ref:`builder_and_algebra`
introduces the two modes and compares them.

This page explains what is going on in algebra mode: what the operators
do, what comes back from them, and how shapes are put in place. It rests
on two ideas, *object arithmetic* and *placement arithmetic*, and on one
underneath both: a shape is a value.

**********************
Objects are values
**********************

A number is a value. ``3 + 4`` does not change the 3 or the 4; it makes a
7. Shapes in algebra mode behave the same way:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [values]
    :end-before: [values]

Each operator takes shapes and gives back a new shape. Nothing is altered
and nothing is collected behind the scenes, so the same ``block`` and
``peg`` can be used again for something else. A design is a sequence of
such lines, each making a new value from earlier ones and keeping it in a
variable.

A model is usually built up under one name, and Python's shorthand for
that reads naturally:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [rebind]
    :end-before: [rebind]

This does not modify the plate. It makes a new part and gives it the old
name.

This is the opposite of builder mode, where a builder holds a model that
each line changes. :ref:`how_builder_mode_works` describes that.

*********************
Object arithmetic
*********************

Three operators combine shapes:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [combine]
    :end-before: [combine]

Most often the two shapes are of the same kind, parts with parts or
sketches with sketches, and the result is of that kind too: two parts make
a ``Part`` and two sketches a ``Sketch``. The kinds can be mixed where it
makes sense to:

.. list-table::
    :header-rows: 1
    :widths: 12 44 44

    * - Operator
      - Dimensions allowed
      - Example
    * - ``+``
      - the same on both sides
      - ``Rectangle + Circle``
    * - ``-``
      - what is taken away must be of the same or a higher dimension
      - ``Rectangle - Box``: the sketch, less where the box passes through
        it
    * - ``&``
      - any
      - ``Box & Rectangle``: the part of the rectangle inside the box

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [mixed_dimensions]
    :end-before: [mixed_dimensions]

Subtracting never raises the dimension of what it is taken from, and an
intersection has the lower dimension of the two. A lower dimension cannot
be taken from a higher one: a solid less a sketch would be the same solid.
Nor can different dimensions be added. A sketch is turned into a part by an
operation such as ``extrude``, not by arithmetic.

When the pieces being added do not touch, there is nothing to join them
into one. They come back grouped in a plain ``Compound``, which holds both
and can be selected from and measured like any shape.

The operators also accept a list, and apply it in one step:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [many]
    :end-before: [many]

A mathematically formal account of this arithmetic is in
:ref:`algebra_definition`.

.. _algebra_performance:

Many objects at once
====================

Using a list is more than a convenience. Every ``+`` or ``-`` is a boolean
operation on the whole shape so far, followed by a tidying pass, and both
take longer as the shape grows. Combining shapes one at a time in a loop
therefore gets slower with every turn:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [slow]
    :end-before: [slow]

Collecting the shapes first and combining them once does the same work in
a single operation:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [fast]
    :end-before: [fast]

The result is identical. On a grid of a few hundred holes the second form
is around ten times faster, and the gap widens as the number grows.

When the same shape goes at every place, the places can be multiplied by
the shape directly, which gives the list without a loop:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [vectorized]
    :end-before: [vectorized]

Use a loop or a comprehension when each place needs something different,
or some places are to be left out, as with the round grille above.

.. _algebra_sewing:

Sewing sheet surfaces
=====================

``Shell`` objects are sheet surfaces rather than solids, so ``+`` sews
their faces together along shared edges instead of fusing them. A fuse
would leave the faces side by side; sewing produces one connected surface,
which is what sheet metal parts are built from.

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [sew]
    :end-before: [sew]

Sewing applies whenever a ``Shell`` takes part in the addition, ``Shell +
Face``, ``Face + Shell`` and ``Shell + Shell``, and any 2D operand
contributes its faces, so sketch objects can be added directly:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [sew_more]
    :end-before: [sew_more]

* Adding to a ``Shell`` always returns a ``Shell``. Faces that cannot be
  sewn into one connected shell, disjoint pieces or three faces meeting on
  a single edge, raise a ``ValueError`` rather than silently returning a
  ``Compound``, so the result type never depends on the geometry.
* The result is cleaned, so faces that are coplanar with their neighbours
  merge into one face. Use the ``SkipClean`` context manager to keep the
  seam.
* A ``Sketch`` on the left keeps sketch semantics: ``sketch + shell`` fuses
  as before. Put the ``Shell`` first to sew.

************************
Placement arithmetic
************************

A shape is made at the origin. It is put in place with a fourth operator,
``*``, which takes a location or a plane on its left and a shape on its
right, and gives back the shape moved:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [place]
    :end-before: [place]

``Pos`` is a position, ``Rot`` a rotation, and a plane stands for the
placement that carries ``Plane.XY`` onto it. ``Plane.XY *`` therefore
changes nothing and can always be left out.

Placements chain, and a chain is read from the right, each step acting on
everything to its right:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [chain]
    :end-before: [chain]

The box is turned, then moved, then stood on ``Plane.XZ``. Because the
plane comes last, the position before it is measured in the plane's own
directions and not the world's: ``Pos(1, 2, 3)`` here is 1 along the
plane's X, 2 along its Y, which is the world's Z, and 3 along its normal.

``Pos(...) * Rot(...)`` can be written as one ``Location`` with a position
and three angles. :ref:`moving_objects` covers placement in practice, and
:ref:`location_arithmetics` goes through the composition of locations and
planes in detail.

A set of places can be multiplied by a shape, which gives a list with one
copy of the shape at each place. Sets of places can be multiplied together
too:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [place_many]
    :end-before: [place_many]

A location list is a Python list of locations. It can be indexed, sliced
and joined with ``+``, and the result is still a location list, as is a
plane or a location times one.

The two kinds of arithmetic combine in one expression. ``*`` binds more
tightly than ``+``, ``-`` and ``&``, as in ordinary arithmetic, so each
shape is placed before the shapes are combined and no brackets are needed:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [precedence]
    :end-before: [precedence]

******************************
Operations take and return
******************************

The operations of build123d, ``extrude``, ``fillet``, ``make_face`` and
the rest, are the same functions in both modes. In algebra mode each is
given what it is to work on and hands back the result:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [operations]
    :end-before: [operations]

Each step turns one kind of object into the next: lines into a sketch, a
sketch into a part. In builder mode the same functions can be given their
input in the same way. The difference there is that the input may be left
out, in which case the operation uses what is waiting in the builder it is
written in, and that the result goes into that builder.

***************************
Selecting from a result
***************************

A result carries a record of the operation that made it, so it can be
asked not only for its faces and edges but for the ones that operation is
responsible for. ``Select.LAST`` gives the features the right-hand operand
brought in or the operation created, and ``Select.NEW`` only those that
existed in neither operand:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [select]
    :end-before: [select]

:ref:`selecting_features` describes this under :ref:`when`.

************************
Mixing with builders
************************

A builder is not a shape and cannot be used with the operators, but what
it built can. Take the result out with ``.part``, ``.sketch`` or ``.line``
and it is a value like any other:

.. literalinclude:: /explanation/algebra_mode.py
    :language: build123d
    :start-after: [mix]
    :end-before: [mix]

Going the other way, using the operators inside a builder's block, has a
catch that is described under :ref:`builder_objects_combine_at_once`.

************
See also
************

* :ref:`key_concepts` describes ``Part``, ``Sketch`` and ``Curve``, and
  locations and planes.
* :ref:`algebra_definition` gives the formal definition of the arithmetic.
* :ref:`location_arithmetics` works through placement on planes.
* :ref:`tutorial_sketch_then_extrude` starts the tutorials, which build
  every model in both modes side by side.
