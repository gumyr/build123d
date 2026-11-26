.. _placing_sketches:

################
Placing sketches
################

A sketch is always drawn the same way, flat, in its own X and Y. Where it
ends up in the model is a separate choice: a *plane*, which gives the
sketch an origin, an X direction and a direction to face. This guide shows
how to get the plane you want.

In builder mode the plane is passed to ``BuildSketch``. In algebra mode
the sketch is multiplied by it, ``plane * sketch``. Everything about
planes below is the same in both.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To put a sketch
      - use
    * - on one of the standard planes
      - ``Plane.XZ``
    * - at a height
      - ``Plane.XY.offset(10)``
    * - on a face of the part
      - the face, or ``Plane(face)``
    * - on a face, the right way round
      - ``Plane(face, x_dir=...)``
    * - with its origin at a corner
      - ``plane.shift_origin(vertex)``
    * - with features at vertices of a face
      - ``plane.to_local_coords(vertex)``
    * - at an angle
      - ``plane.rotated((0, 25, 0))``
    * - across the start of a path
      - ``path ^ 0``
    * - in several places at once
      - several planes or faces

In the pictures the placed sketch is drawn in blue.

***********************
On a standard plane
***********************

.. image:: /how_to/assets/placing_sketches/standard.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [standard]
            :end-before: [standard]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [standard_algebra]
            :end-before: [standard_algebra]

The sketch's X and Y become the plane's X and Y directions. On
``Plane.XZ`` those are world X and world Z, so the trapezoid stands
upright, and ``extrude`` goes along the plane's normal, here along Y.

``Plane.XY``, ``Plane.XZ`` and ``Plane.YZ`` all pass through the origin.
Each has a twin that faces the other way, ``Plane.YX``, ``Plane.ZX`` and
``Plane.ZY``, and six more named by the view they give, such as
``Plane.front`` and ``Plane.top``. They are listed with
:class:`~geometry.Plane`.

*********************
Raised or lowered
*********************

.. image:: /how_to/assets/placing_sketches/offset.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [offset]
            :end-before: [offset]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [offset_algebra]
            :end-before: [offset_algebra]

``offset`` moves a plane along its own normal, so ``Plane.XY.offset(10)``
is 10 above ``Plane.XY`` and a negative amount is below it. The origin
stays over the old one.

This needs a number: the 10 here is half the height of the box, worked
out by hand. When the part already has a face where the sketch should go,
use the face, as in the next section, and the sketch will follow it if
the part changes.

*************************
On a face of the part
*************************

.. image:: /how_to/assets/placing_sketches/face.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [face]
            :end-before: [face]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [face_algebra]
            :end-before: [face_algebra]

Select the face and sketch on it: in builder mode ``BuildSketch`` takes
the face as it is, while in algebra mode ``Plane(face)`` makes a plane from
it.

The origin of that plane is the centre of the face, and it faces the way
the face does, outward from the part. A positive ``extrude`` therefore
adds material outside the part and a negative one cuts into it. How to
select a face is covered in :ref:`selectors`.

****************************
Which way is X on a face
****************************

A face has a centre and a normal, but nothing in it says which way is
"along". ``Plane(face)`` has to choose an X direction, and its choice is
not always the one wanted. Here the same slot is sketched on the sloping
face twice:

.. image:: /how_to/assets/placing_sketches/x_dir.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [x_dir]
            :end-before: [x_dir]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [x_dir_algebra]
            :end-before: [x_dir_algebra]

``x_dir`` settles it: the sketch's X will point that way. A direction
that leans out of the face is laid flat onto it, so a world direction
such as ``(0, 1, 0)`` will usually do; only one that points straight out
of the face cannot be used.

Give ``x_dir`` whenever the sketch is not the same all the way round: a
circle does not care which way X is, but a slot, a rectangle or text does.

*******************************
With its origin at a corner
*******************************

The centre of a face is not always the convenient place to measure from.
When it is not, ``shift_origin`` moves the origin of a plane to another
point on it and leaves its directions alone.

.. image:: /how_to/assets/placing_sketches/origin.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [origin]
            :end-before: [origin]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [origin_algebra]
            :end-before: [origin_algebra]

``corner`` is the vertex of the top face at the lowest X and Y. With the
origin there and ``x_dir`` given, the sketch's coordinates are measured
from that corner along the edges of the block, and
``Rectangle(15, 10, align=Align.MIN)`` starts exactly at it.

``shift_origin`` accepts the new origin in four forms:

.. literalinclude:: /how_to/placing_sketches.py
    :language: build123d
    :start-after: [origin_forms]
    :end-before: [origin_forms]

A point given in space must already lie on the plane, and a vertex
likewise; ``shift_origin`` moves the origin within the plane and never
moves the plane.

.. note::

    To move one feature within a sketch, leave the plane alone and place
    the feature: ``Locations`` in builder mode, ``Pos(x, y) *`` in algebra
    mode. Move the origin when the whole sketch is measured from somewhere
    else.

*******************************************
With features at the vertices of a face
*******************************************

``shift_origin`` moves the whole sketch to one vertex. To put a feature
on each of several vertices, keep the plane where it is and turn the
vertices into places in the sketch.

.. image:: /how_to/assets/placing_sketches/vertices.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [vertices]
            :end-before: [vertices]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [vertices_algebra]
            :end-before: [vertices_algebra]

A vertex is a point in space, and the places inside a sketch are
measured in the sketch's own X and Y. ``to_local_coords`` converts one
to the other: it gives the vertex as the plane sees it. Here the two
lower corners of the sloping face each get a circle, which is then cut
into the part.

.. note::

    The conversion is needed even in builder mode. ``Locations`` inside a
    sketch reads a vertex's coordinates as sketch coordinates, without
    converting them. On a face that lies square to ``Plane.XY`` with its
    centre over the origin, such as the top of a centred box, the two
    happen to agree and the vertex can be passed as it is. On any other
    face it cannot.

**********
Tilted
**********

.. image:: /how_to/assets/placing_sketches/tilted.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [tilted]
            :end-before: [tilted]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [tilted_algebra]
            :end-before: [tilted_algebra]

``rotated`` turns a plane about its own X, Y and Z directions, by the
three angles given in degrees, and leaves its origin where it was.
``(0, 25, 0)`` leans ``Plane.XY`` by 25 degrees about its Y direction, so
the peg extruded from it leans toward X.

The angles are about the plane's own directions, not the world's.
``Plane.XZ.rotated((0, 0, 90))`` spins ``Plane.XZ`` about its normal and
it is still the XZ plane, with its X now along world Z. Turning a plane
about its normal like this is another way to set which way a sketch's X
points.

The steps chain: ``Plane.XY.offset(10).rotated((0, 25, 0))`` is a plane
raised and then leaned.

****************************
At a point along an edge
****************************

A profile to be swept has to stand across the start of its path.
``path ^ 0`` gives that place: a location at the start of the path, with
its Z direction along the path.

.. image:: /how_to/assets/placing_sketches/along.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [along]
            :end-before: [along]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [along_algebra]
            :end-before: [along_algebra]

The caret operator (``^``) takes a position along the edge or wire from 0 to 1,
so ``rail ^ 0.5`` is a place halfway along, facing along the path there. It
is short for :meth:`~topology.Mixin1D.location_at`, which has more
control over how the place is turned about the path. A location serves
wherever a plane does: ``BuildSketch`` accepts it, and a sketch can be
multiplied by it.

*****************************
In several places at once
*****************************

.. image:: /how_to/assets/placing_sketches/several.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [several]
            :end-before: [several]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/placing_sketches.py
            :language: build123d
            :start-after: [several_algebra]
            :end-before: [several_algebra]

``BuildSketch`` accepts any number of planes, faces and locations, and
the finished sketch is placed on every one of them, although what is drawn
inside is drawn only once. Here it lands on the two faces that face along
Y, and one ``extrude`` raises a boss on each.

In algebra mode the same thing is a list: one placed sketch for each
plane, and one extrusion for each sketch.

************
See also
************

* :ref:`tutorial_placing_features` and
  :ref:`tutorial_selecting_and_finishing` introduce sketching on planes
  and on selected faces step by step.
* :ref:`sketching_on_other_planes` describes how a sketch drawn flat is
  carried to its plane, and the difference between ``sketch`` and
  ``sketch_local``.
* :class:`~geometry.Plane` lists every way to make a plane.
