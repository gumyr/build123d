.. _location_arithmetic:

#######################
How placements combine
#######################

Every object in build123d is made at the origin and then put where it
belongs. A single placement is easy to follow, but designs are built from
several, one on top of another: a hole on a face of a bracket that sits on a
plate. This page explains how placements combine, which is the same in algebra
mode, where they are written as a chain of ``*``, and in builder mode, where
they are nested ``with`` blocks.

:ref:`moving_objects` is the practical guide to placing things, and this page
is the reasoning behind it.

In the pictures the grey lines marked X, Y and Z are the axes of the world.
A frame is drawn as three lines marked x, y and z.

**************************
A location is a frame
**************************

A :class:`~geometry.Location` is a position and an orientation. It is most
useful to picture it as a *frame*: a set of axes of its own, standing
somewhere in space and turned some way.

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [frame]
    :end-before: [frame]

.. image:: /explanation/assets/location_arithmetic/frame.svg
    :align: center
    :width: 55%

``loc`` is 0.1, 0.2 and 0.3 from the origin and turned 10, 20 and 30
degrees about X, Y and Z. Multiplying the rectangle by it puts the
rectangle in that frame: its centre on the frame's origin, lying in the
frame's xy plane, facing along its z.

A :class:`~geometry.Plane` is the same thing seen as a place to draw: it has
an origin, an x direction and a normal, and that is a frame.

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [plane]
    :end-before: [plane]

.. image:: /explanation/assets/location_arithmetic/plane.svg
    :align: center
    :width: 50%

``Plane.XZ`` has its x along the world's X, its y along the world's Z and
its normal along ``-Y``, so the rectangle's width of 1 runs along world X and
its height of 2 along world Z. ``Plane.XY`` is the frame of the world itself,
which is why ``Plane.XY *`` changes nothing.

*****************
The rule
*****************

**Each term in a chain is measured in the frame made by everything to its
left.**

A position
==========

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [position]
    :end-before: [position]

.. image:: /explanation/assets/location_arithmetic/position.svg
    :align: center
    :width: 55%

``Pos(0.2, 0.4, 0.1)`` is not 0.2 along the world's X but 0.2 along the x of
``loc``, 0.4 along its y and 0.1 along its z, off the face.

A rotation
==========

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [rotation]
    :end-before: [rotation]

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [rotation_general]
    :end-before: [rotation_general]

.. image:: /explanation/assets/location_arithmetic/rotation.svg
    :align: center
    :width: 85%

``Rot(Z=80)`` turns the box about the z of ``loc``, not the Z of the world:
the box stays flat on the face. ``Rot(20, 40, 80)`` turns it about all three
axes of ``loc``. In both, the box stays on the frame's origin, because a
rotation is about the origin of the frame it is measured in.

Both, in either order
=====================

The rule applies term by term, so with two terms the order matters.

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [turn_then_move]
    :end-before: [turn_then_move]

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [move_then_turn]
    :end-before: [move_then_turn]

.. image:: /explanation/assets/location_arithmetic/order.svg
    :align: center
    :width: 85%

The orange frame is the one the last term is measured in.

* **Turn, then move.** ``loc * Rot(20, 40, 80)`` is a frame at the origin of
  ``loc``, turned. The position is measured along *its* axes, so the box is
  carried off in a tilted direction.
* **Move, then turn.** ``loc * Pos(0.2, 0.4, 0.1)`` is a frame moved across
  the face and not turned. The rotation is about *its* origin, so the box
  turns where it stands.

The second is usually what is wanted, and it has a shorter spelling. A
``Location`` with a position and three angles is that position followed by
that rotation:

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [one_location]
    :end-before: [one_location]

****************************
Two ways to read a chain
****************************

:ref:`moving_objects` and :ref:`how_algebra_mode_works` say to read a chain
from the right, while this page has been reading from the left. Both are
correct, and they always agree.

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [readings]
    :end-before: [readings]

.. image:: /explanation/assets/location_arithmetic/readings.svg
    :align: center
    :width: 85%

* **From the right, in the world.** Start with the object and apply each
  placement to it in turn, every one measured in the world's axes. The
  block is moved 2 along world X (grey), and then turned 90 degrees about
  world Z, which swings it round to the Y axis.
* **From the left, in frames.** Start with the world's frame and let each
  term move the frame, every one measured in the frame so far. The frame is
  turned 90 degrees (blue), so its x now points along world Y. Then it goes
  2 along its own x (orange). The block is made in the frame that results.

The block ends up at ``(0, 2, 0)`` with its long side along Y either way.
The two readings agree because the multiplication of placements is
associative: ``(a * b) * shape`` is the same as ``a * (b * shape)``, so it
does not matter where the brackets are imagined.

Which to use is a matter of what is being worked out. Reading from the
right suits a single object that is turned and moved. Reading from the left
suits a design built up of places within places, because each term can be
understood knowing only the frame it sits in.

What is not free is the order of the terms. Placements do not commute:
``Rot(Z=90) * Pos(2, 0, 0)`` and ``Pos(2, 0, 0) * Rot(Z=90)`` are different
placements, as the two boxes above show.

**********************
Planes in a chain
**********************

A plane at the head of a chain acts as its frame, exactly as a location
does. ``Plane(loc)`` is the plane of the frame ``loc``, and the first two
lines here give the same box:

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [planes]
    :end-before: [planes]

The third takes its frame from the model: ``Plane(face)`` is the plane a
flat face lies in. It has the face's centre as its origin and the face's
normal as its z, so the box stands 0.1 off the face as before. Its x
direction is chosen by the face, and need not be the x of the location that
put the face there; give ``Plane(face, x_dir=...)`` to choose it.
:ref:`placing_sketches` covers this.

A plane times a location is a location, the frame reached by taking that
step from the plane: ``Plane.XZ * Pos(1, 2, 3)`` is at ``(1, -3, 2)`` in
the world.

***************************
The same in builder mode
***************************

Builder mode has no chain to read, but it composes placements by the same
rule. Each ``with Locations(...)`` is measured in the frame of the blocks
around it, and an object's ``rotation`` is the last term, applied where the
object stands.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /explanation/location_arithmetic.py
            :language: build123d
            :start-after: [builder]
            :end-before: [builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /explanation/location_arithmetic.py
            :language: build123d
            :start-after: [builder_algebra]
            :end-before: [builder_algebra]

The nesting from the outside in is the chain from left to right. A builder
given a plane starts in that plane's frame, so this is the same part again:

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [builder_plane]
    :end-before: [builder_plane]

***********************************
Undoing and comparing placements
***********************************

Every location has an inverse, the placement that undoes it.

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [inverse]
    :end-before: [inverse]

The inverse also answers the question "where is this, seen from there?".
If two things are placed in the world, ``a.inverse() * b`` is the location
of ``b`` in the frame of ``a``:

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [relative]
    :end-before: [relative]

The hole is 1.414 along the bracket's own x, and not turned relative to
it. Multiplying back, ``bracket * hole_on_bracket``, gives ``hole`` again.

For single points, a plane converts between the world and its own frame:

.. literalinclude:: /explanation/location_arithmetic.py
    :language: build123d
    :start-after: [coordinates]
    :end-before: [coordinates]

************
See also
************

* :ref:`moving_objects` for the practical guide to moving and turning.
* :ref:`placing_sketches` for taking a frame from a face of the model.
* :ref:`how_algebra_mode_works` for the ``*`` operator among the others.
* :ref:`algebra_definition` for the formal statement: locations form a
  group under ``*``, which is not commutative.
