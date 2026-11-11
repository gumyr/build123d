.. _tutorial_drawing_outlines:

################
Drawing outlines
################

Ready-made shapes such as rectangles and slots only go so far. When a part
has an outline of its own, you draw that outline from lines and arcs, turn it
into a sketch, and carry on as before. In this tutorial you will draw the
outline of this wall hook and extrude it:

.. image:: /tutorials/assets/drawing_outlines/hook_extrude.svg
    :align: center
    :width: 60%

Along the way you will:

* draw lines and arcs and give each one a name,
* start each piece where the last one ended, instead of typing coordinates,
* make an arc leave in the direction the previous piece arrived,
* close an outline into a sketch with ``make_face``, and
* use the same technique to draw a path and ``sweep`` a shape along it.

It takes about twenty minutes and follows on from
:ref:`tutorial_sketch_then_extrude`, which introduces sketches, ``extrude``,
and how the builder and algebra tabs on this page work.

*************
Step 1: Setup
*************

Start a new Python file with the import and the dimensions of the hook, in
millimetres: the ``width`` of the strip it is cut from, the ``reach`` of its
opening measured as the radius of the inside curve, and the heights of its
back and its tip.

.. literalinclude:: /tutorials/drawing_outlines.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

As before, each step below shows the whole of the rest of the file as it
stands at that point.

***************************
Step 2: Lines with names
***************************

Begin with the back of the hook: up the left side, across the top and down
again. A :class:`~objects_curve.Line` is drawn from one point to another, and
each is assigned to a variable so that it can be referred to later.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [named_builder]
            :end-before: [named_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [named_algebra]
            :end-before: [named_algebra]

.. image:: /tutorials/assets/drawing_outlines/hook_named.svg
    :align: center
    :width: 25%

The lines are the same objects in both modes. In builder mode they are
created inside a ``with BuildLine()`` block, which collects them; in algebra
mode they stand on their own.

This works, and it has a weakness. Every corner is typed twice - ``(0, 50)``
ends ``l1`` and starts ``l2`` - and the numbers 50 and 14 are the height and
width of the hook, written out by hand. Change one and miss another and the
lines no longer meet.

*******************************
Step 3: Connect by position
*******************************

The lines have names, so one line can ask another where it is. The ``@``
operator gives a position along a line or arc: ``l1 @ 0`` is where ``l1``
starts, ``l1 @ 1`` is where it ends, and ``l1 @ 0.5`` is halfway.

So ``l2`` can start at ``l1 @ 1``, wherever that turns out to be, and end a
distance of ``width`` to the right of it:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [connected_builder]
            :end-before: [connected_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [connected_algebra]
            :end-before: [connected_algebra]

These are exactly the three lines of step 2, and the picture is unchanged.
But only the first point, ``(0, 0)``, is now a coordinate. Everything else
is "from the end of the last piece, this far in this direction", using the
dimensions by name. The lines cannot come apart, and changing
``back_height`` moves all three.

This is build123d's answer to the sketch constraints of a traditional CAD
program: a line is an ordinary Python value, and the next line is computed
from it.

*****************************************************
Step 4: Arcs that leave in the right direction
*****************************************************

The bottom of the hook is a half circle that carries on smoothly from the
side above it. To do that an arc needs to know not only where the last piece
ended but which way it was heading. The ``%`` operator gives that direction:
``l3 % 1`` is the direction of ``l3`` at its end.

A :class:`~objects_curve.JernArc` is defined in exactly these terms: where it
starts, the direction it sets off in, its radius, and how far round it goes
in degrees - positive to turn left, negative to turn right.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [arcs_builder]
            :end-before: [arcs_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [arcs_algebra]
            :end-before: [arcs_algebra]

.. image:: /tutorials/assets/drawing_outlines/hook_arcs.svg
    :align: center
    :width: 40%

Reading round the outline: ``a1`` starts where ``l3`` ends, sets off in the
direction ``l3`` was going, and turns left through 180 degrees to form the
inside of the hook. ``l4``, ``l5`` and ``l6`` draw the tip. ``a2`` then turns
right through 180 degrees, on a radius larger than ``a1`` by the width of
the strip, and arrives back at the start of ``l1``.

Nothing in those eight lines is a coordinate except the starting point.

**********************************
Step 5: Close it into a face
**********************************

An outline is only lines until :func:`~operations_sketch.make_face` fills it
in. The result is a sketch, the same kind of object the ready-made shapes
gave you in the first tutorial, so everything that worked there works here:
the fixing hole is a ``Circle`` subtracted from it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [face_builder]
            :end-before: [face_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [face_algebra]
            :end-before: [face_algebra]

.. image:: /tutorials/assets/drawing_outlines/hook_face.svg
    :align: center
    :width: 40%

In builder mode the ``BuildLine`` block moves inside a ``BuildSketch``, and
``make_face`` with no argument uses the lines just drawn. In algebra mode
``make_face`` is given the lines.

``make_face`` needs a closed outline. If the last piece does not end where
the first began it stops with *Face can only be created with closed wires*.
Here ``a2`` closes the outline because its radius is ``reach + width``; an
outline built from named dimensions closes for every value of them, which
one built from typed coordinates will not.

*********************
Step 6: Extrude it
*********************

From here it is the first tutorial again: extrude the sketch.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [extrude_builder]
            :end-before: [extrude_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [extrude_algebra]
            :end-before: [extrude_algebra]

.. image:: /tutorials/assets/drawing_outlines/hook_extrude.svg
    :align: center
    :width: 60%

Try a ``reach`` of 20 or a ``width`` of 8 at the top of the file. The curve,
the tip and the fixing hole all follow, because every piece of the outline
was drawn from the piece before it.

**********************************************
Step 7: The same idea draws a path
**********************************************

Lines and arcs do not have to close. Left open they make a *path*, and
:func:`~operations_generic.sweep` carries a sketch along a path to make a
solid. This is the same hook bent from round wire: its path is a line, a
half circle that continues from it, and a short line for the tip, drawn
exactly as in step 4.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [sweep_builder]
            :end-before: [sweep_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/drawing_outlines.py
            :language: build123d
            :start-after: [sweep_algebra]
            :end-before: [sweep_algebra]

.. image:: /tutorials/assets/drawing_outlines/hook_path.svg
    :align: center
    :width: 30%

The sketch being swept is a circle, and it has to face along the start of
the path. The path sets off from the origin along -Y, and ``Plane.XZ`` is the
plane that faces that way, so the circle is drawn there. Planes are the
subject of a later tutorial.

In builder mode ``sweep`` with no arguments takes the sketch and the path
that were just made. In algebra mode the three pieces are joined into one
path with ``+`` and both are passed to ``sweep``.

.. image:: /tutorials/assets/drawing_outlines/hook_sweep.svg
    :align: center
    :width: 60%

*****************
What you learned
*****************

* Lines and arcs are objects with **names**, and the name is how the next
  piece finds the last one.
* ``@`` gives a **position** along a line or arc, from 0 at its start to 1
  at its end, and ``%`` gives its **direction** there.
* An outline drawn from the piece before it has one coordinate, its
  starting point, and holds together when a dimension changes.
* :func:`~operations_sketch.make_face` turns a closed outline into a sketch;
  :func:`~operations_generic.sweep` carries a sketch along an open path.
* :class:`~objects_curve.Line` and :class:`~objects_curve.JernArc` are two
  of many 1D objects. ``Polyline`` draws a run of straight lines from a list
  of points, and ``Spline`` and ``Bezier`` draw free curves; all of them
  answer ``@`` and ``%`` in the same way. :ref:`cheat_sheet` lists them.
