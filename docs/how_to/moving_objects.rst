.. _moving_objects:

############################
Moving and rotating objects
############################

Every object is made at the origin, facing the way it was designed, and is
then put where it belongs. Moving it is rarely the hard part. Turning it
is, because a rotation always raises two questions that a move does not:
*about what*, and *in what order*. This guide shows how to get the move
or the turn you want.

In builder mode an object is placed as it is made, with a ``with
Locations(...)`` block or its own ``rotation``. In algebra mode it is
multiplied by a location, ``location * object``.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - move an object
      - ``Locations((x, y, z))`` or ``Pos(x, y, z) *``
    * - turn it where it stands
      - ``rotation=`` or ``Pos(...) * Rot(...) *``
    * - turn it about an axis somewhere else
      - ``shape.rotate(axis, angle)``
    * - swing it round the origin
      - ``Rot(...) * Pos(...) *``
    * - give it a position and a rotation together
      - ``Location((x, y, z), (rx, ry, rz))``
    * - put an object on vertices of the part
      - ``Locations(*vertices)`` or ``Pos(vertex) *``
    * - make copies round the Z axis
      - ``PolarLocations(radius, count)``
    * - mirror it in a face of the part
      - ``mirror(about=Plane(face))``
    * - turn something that is already in place
      - ``Rot(...) *``, about a world axis

In the pictures the three grey lines are the world X, Y and Z axes,
drawn from the origin: X toward the lower right, Y toward the upper right
and Z upward. The object is shown in grey as it was made and in blue
where it ends up.

******************
Move an object
******************

.. image:: /how_to/assets/moving_objects/move.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [move]
            :end-before: [move]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [move_algebra]
            :end-before: [move_algebra]

``Pos`` is a position, and multiplying an object by it moves the object
there. Only the axes that matter need be given: ``Pos(X=20)`` or
``Pos(Z=5)``. In builder mode the places are named first, and every
object made inside the ``with`` block is made at each of them.

The object is not changed and nothing is copied point by point. Every
shape carries a location, and moving the shape changes that.

***************************
Turn it where it stands
***************************

.. image:: /how_to/assets/moving_objects/turn.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [turn]
            :end-before: [turn]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [turn_algebra]
            :end-before: [turn_algebra]

Angles are in degrees. ``Rot(Z=30)`` turns an object 30 degrees about the
Z axis, anticlockwise seen from above.

An object's ``rotation`` turns it about its own origin before it is put
in place, so the bar turns where it stands. The algebra line says the
same thing and is read from right to left: make the bar, turn it, then
move it.

*************************************
Turn then move, or move then turn
*************************************

The order matters. A rotation is always about the origin, so an object
that has already been moved away from the origin is swung round it:

.. image:: /how_to/assets/moving_objects/order.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [order]
            :end-before: [order]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [order_algebra]
            :end-before: [order_algebra]

Read each line from the right. In the first the bar is turned while it is
still at the origin, and then moved: it turns where it stands. In the
second it is moved 40 along X and then turned, and the turn carries it
round the Z axis to a new place.

Both are useful. Turn first to set which way an object faces; move first
to swing it round the origin on an arm.

****************************************
Turn it about an axis somewhere else
****************************************

A hinge, a pivot or an axle is rarely at the origin. ``rotate`` turns a
shape about any axis.

.. image:: /how_to/assets/moving_objects/hinge.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [hinge]
            :end-before: [hinge]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [hinge_algebra]
            :end-before: [hinge_algebra]

An :class:`~geometry.Axis` is a point and a direction. This one passes
through the origin along Y, which is the edge of the lid, and the lid is
lifted 40 degrees about it. The angle is positive anticlockwise seen
looking back along the axis toward its start, which is why lifting this
lid takes a negative one. ``rotate`` returns a new shape and leaves the
lid as it was.

An axis can also be taken from the model: ``Axis(edge)`` runs along a
straight edge, and ``Axis(shape.center(), (0, 0, 1))`` stands upright
through the middle of a shape.

************************
Three angles at once
************************

.. image:: /how_to/assets/moving_objects/angles.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [angles]
            :end-before: [angles]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [angles_algebra]
            :end-before: [angles_algebra]

``Rot`` and ``rotation`` take up to three angles, about X, Y and Z. When
more than one is given, their order matters as it does for any two
rotations, and it is fixed:

.. literalinclude:: /how_to/moving_objects.py
    :language: build123d
    :start-after: [angles_chain]
    :end-before: [angles_chain]

These two are the same. Read from the right as before, the object is
turned about Z, then about Y, then about X, each about the world axis.
If that is not the order needed, write the steps out as a chain in the
order that is: it is longer, and it says what it does.

*************************
At a rotated location
*************************

A :class:`~geometry.Location` is a position and a rotation in one. It can
be kept in a variable, put in a list and used wherever a place is wanted.

.. image:: /how_to/assets/moving_objects/location.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [location]
            :end-before: [location]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [location_algebra]
            :end-before: [location_algebra]

``Location((20, 30, 0), (0, 0, 30))`` is the same place as
``Pos(20, 30, 0) * Rot(Z=30)``: turned where it stands, then moved.
``Locations`` accepts locations as well as points, and so does a builder,
which then places everything it makes there:
``with BuildPart(Location((20, 30, 0), (0, 0, 30))):``.

*******************************
At the vertices of the part
*******************************

A place does not have to be worked out from dimensions. A vertex of the
part is a point, and can be used as one.

.. image:: /how_to/assets/moving_objects/vertices.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [vertices]
            :end-before: [vertices]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [vertices_algebra]
            :end-before: [vertices_algebra]

``top.vertices()`` is the four corners of the top face. ``Locations``
takes vertices as it takes points, and ``Pos(vertex)`` is the position
of one. Move the corners, by changing the size of the plate, and the
posts go with them. :ref:`selectors` covers picking out the vertices
wanted.

This is for objects placed in the part. Inside a sketch that is drawn
on a plane, places are measured in the sketch, not in space;
:ref:`placing_sketches` shows how to use a vertex there.

************************
Copies round an axis
************************

.. image:: /how_to/assets/moving_objects/polar.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [polar]
            :end-before: [polar]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [polar_algebra]
            :end-before: [polar_algebra]

:class:`~build_common.PolarLocations` is a ring of places about the Z
axis, here six of them at a radius of 25. Each place is turned to face
outward, so the spokes point along their own radius; ``rotate=False``
leaves them all facing the same way. :ref:`tutorial_placing_features`
covers this and the other patterns.

**********************
Mirrored in a face
**********************

:func:`~operations_generic.mirror` reflects an object in a plane, and the
plane can be taken from the part: ``Plane(face)`` is the plane a flat
face lies in.

.. image:: /how_to/assets/moving_objects/mirror.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [mirror]
            :end-before: [mirror]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [mirror_algebra]
            :end-before: [mirror_algebra]

``side`` is the face of the pentagon furthest toward ``-Y``. Mirrored in
that face, the copy meets the original on it, and the two make one part.
In builder mode ``mirror`` reflects what the part holds so far and adds
the reflection; in algebra mode it returns the reflection, to be added.

The standard planes work the same way, and are the usual choice for a
part designed about the origin: ``mirror(about=Plane.YZ)``.

**************************************
Something that is already in place
**************************************

Everything above places an object that was made at the origin. An object
that is already where it belongs, because it was built there or placed
earlier, needs only to be turned. Here a tooth stands 20 above the X
axis, and five more are wanted round that axis.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [placed]
            :end-before: [placed]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/moving_objects.py
            :language: build123d
            :start-after: [placed_algebra]
            :end-before: [placed_algebra]

``Rot(X=angle)`` turns about the world X axis. The tooth is away from
that axis, so each turn swings it round, which is what is wanted here.

A list of places on a plane looks as though it would do the same job,
and does not:

.. literalinclude:: /how_to/moving_objects.py
    :language: build123d
    :start-after: [placed_wrong]
    :end-before: [placed_wrong]

.. image:: /how_to/assets/moving_objects/placed.svg
    :align: center

A place on a plane is for something made at the origin: it stands the
object on the plane as well as turning it. The tooth was already
standing, and is laid over, so all six end up in a small ring out along
X. Use places on a plane for new objects, and ``Rot`` or ``rotate`` for
objects that are already placed.

To turn a placed object where it stands, turn it about an axis through
its own centre:

.. literalinclude:: /how_to/moving_objects.py
    :language: build123d
    :start-after: [spin]
    :end-before: [spin]

*******************************
Changing an object directly
*******************************

A shape's location can also be read and set after it is made. These are
most use in a script that adjusts an existing model.

.. list-table::
    :header-rows: 1
    :widths: 40 60

    * - Code
      - Effect
    * - ``shape.position = (x, y, z)``
      - puts the shape at a position; ``+=`` and ``-=`` shift it
    * - ``shape.orientation = (rx, ry, rz)``
      - sets its three rotation angles
    * - ``shape.move(location)``
      - moves the shape by a location, relative to where it is
    * - ``shape.moved(location)``
      - the same, on a copy
    * - ``shape.locate(location)``
      - puts the shape at a location, wherever it was
    * - ``shape.located(location)``
      - the same, on a copy
    * - ``shape.translate((x, y, z))``
      - a copy shifted by a vector
    * - ``shape.rotate(axis, angle)``
      - a copy turned about an axis

************
See also
************

* :ref:`placing_sketches` covers choosing the plane a sketch is drawn on.
* :ref:`location_arithmetics` explains how locations and planes combine
  in algebra mode.
* :ref:`tutorial_placing_features` introduces ``Locations`` and the
  pattern locations step by step.
